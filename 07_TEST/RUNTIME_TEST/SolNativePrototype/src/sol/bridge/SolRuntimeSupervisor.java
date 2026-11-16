package sol.bridge;

import java.lang.ref.WeakReference;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.atomic.AtomicLong;

import zombie.MainThread;
import zombie.MovingObjectUpdateScheduler;
import zombie.characters.IsoPlayer;
import zombie.characters.IsoZombie;
import zombie.core.skinnedmodel.ModelManager;
import zombie.iso.IsoCell;
import zombie.iso.IsoGridSquare;
import zombie.iso.IsoMovingObject;
import zombie.iso.IsoWorld;

/** Single lifecycle owner for the isolated native-shell test backend. */
public final class SolRuntimeSupervisor {
    public static final String PROTOCOL = "sol-native-prototype-3";
    private static final long CLEANUP_RETRY_MILLIS = 1000L;
    private static final long REGISTRATION_TIMEOUT_MILLIS = 15000L;
    private static final AtomicLong NEXT_REQUEST = new AtomicLong(1L);
    private static final ExecutorService HANDOFF = Executors.newSingleThreadExecutor(task -> {
        Thread thread = new Thread(task, "SolRuntimeSupervisor-handoff");
        thread.setDaemon(true);
        return thread;
    });

    private enum State {
        COLD, BOOTSTRAPPING, WAITING_LUA, BRIDGE_READY, WAITING_WORLD,
        SPAWN_PENDING, REGISTERING, ACTIVE, SUSPENDED_ENV, REMOVING,
        CLEANUP_PENDING, DESTROYED, BLOCKED_LEGACY_ACTOR,
        BLOCKED_STALE_ACTOR, FAILED
    }

    private static volatile State state = State.COLD;
    private static volatile String lastError = "";
    private static volatile String lastTransition = "class-load";
    private static volatile String cleanupStage = "none";
    private static volatile String cleanupFailures = "";
    private static volatile long runtimeGeneration;
    private static volatile long worldGeneration;
    private static volatile long environmentGeneration;
    private static volatile long actorGeneration;
    private static volatile long pendingRequestId = -1L;
    private static volatile long actorRequestId = -1L;
    private static volatile long spawnCount;
    private static volatile long removeCount;
    private static volatile long cleanupAttemptCount;
    private static volatile long lastCleanupAttemptAt;
    private static volatile long registrationStartedAt;
    private static volatile int lastLegacyZombieCount = -1;
    private static volatile int lastNativeShellCount = -1;
    private static volatile boolean bridgeProtocolValid;
    private static volatile long exposureCount;
    private static volatile int bridgeEnvironmentId;
    private static volatile int bridgeExposerId;
    private static volatile WeakReference<Object> observedEnvironment = new WeakReference<>(null);
    private static volatile IsoCell observedCell;
    private static volatile IsoCell actorCell;
    private static volatile SolIsoPlayerShell actor;
    private static volatile WeakReference<SolIsoPlayerShell> lastRetiredActor = new WeakReference<>(null);
    private static volatile long retiredUpdateCount = -1L;
    private static volatile int retiredStableSamples;

    private SolRuntimeSupervisor() {}

    public static synchronized void bootstrapStarted() {
        if (runtimeGeneration == 0L) runtimeGeneration = 1L;
        if (state == State.COLD) transition(State.BOOTSTRAPPING, "bootstrap-start");
        if (!bridgeProtocolValid && actor == null) transition(State.WAITING_LUA, "await-lua");
    }

    public static synchronized void observeEnvironment(
            Object environment, Object exposer, boolean valid, long exposures, String detail) {
        Object previous = observedEnvironment.get();
        if (environment != previous) {
            environmentGeneration++;
            observedEnvironment = new WeakReference<>(environment);
            bridgeEnvironmentId = environment == null ? 0 : System.identityHashCode(environment);
            bridgeExposerId = exposer == null ? 0 : System.identityHashCode(exposer);
            bridgeProtocolValid = false;
            if (actor != null && state == State.ACTIVE) {
                transition(State.SUSPENDED_ENV, "lua-environment-changed");
            }
        } else if (exposer != null) {
            bridgeExposerId = System.identityHashCode(exposer);
        }

        exposureCount = Math.max(exposureCount, exposures);
        bridgeProtocolValid = valid;
        if (!valid && detail != null && !detail.isEmpty()) lastError = detail;
        if (valid) {
            lastError = "";
            if (actor != null && actorCell == observedCell && actorCell != null
                    && state == State.SUSPENDED_ENV && validateActor(actor, actorCell, true)) {
                transition(State.ACTIVE, "bridge-revalidated");
            } else if (observedCell != null && actor == null) {
                transition(State.WAITING_WORLD, "bridge-ready");
            } else if (actor == null) {
                transition(State.BRIDGE_READY, "bridge-ready");
            }
        } else if (actor != null) {
            transition(State.SUSPENDED_ENV, "bridge-invalid");
        } else {
            transition(State.WAITING_LUA, "bridge-invalid");
        }
    }

    /** Called only by the existing 500 ms bootstrap handoff on the game thread. */
    public static void pollLifecycle() {
        if (Thread.currentThread() != MainThread.mainThread) return;
        try {
            IsoCell liveCell = currentWorldCell();
            if (liveCell != observedCell) onWorldCellChanged(liveCell);

            if (state == State.CLEANUP_PENDING
                    && System.currentTimeMillis() - lastCleanupAttemptAt >= CLEANUP_RETRY_MILLIS) {
                retryCleanupOnMainThread("scheduled-cleanup-retry");
            }
            if (state == State.REGISTERING) pollRegistration();
            sampleRetiredActor();
            sampleCurrentMemberships();
        } catch (Throwable failure) {
            recordFailure("poll", failure);
        }
    }

    public static long requestSpawn(Object square) {
        final long requestId;
        final long reservedRuntime;
        final long reservedWorld;
        final long reservedActor;
        synchronized (SolRuntimeSupervisor.class) {
            if (!"NATIVE_SHELL".equals(getBackend())) {
                fail("unsupported backend selected: " + getBackend());
                return -1L;
            }
            if (!bridgeProtocolValid) {
                fail("bridge protocol is not validated for the active Lua environment");
                return -1L;
            }
            if (actor != null) {
                if (state == State.ACTIVE || state == State.REGISTERING) return actorRequestId;
                if (state == State.CLEANUP_PENDING || state == State.REMOVING) {
                    fail("owned actor cleanup is pending; refusing duplicate spawn");
                    return -1L;
                }
                fail("owned actor exists in non-spawnable state " + state);
                return -1L;
            }
            if (pendingRequestId >= 0L && state == State.SPAWN_PENDING) return pendingRequestId;
            if (Thread.currentThread() != MainThread.mainThread) {
                fail("spawn request must be reserved on the game main thread");
                return -1L;
            }
            if (!(square instanceof IsoGridSquare targetSquare)) {
                fail("spawn target is not an IsoGridSquare");
                return -1L;
            }
            IsoCell targetCell = targetSquare.getCell();
            if (targetCell == null || targetCell != observedCell || targetSquare.getChunk() == null) {
                fail("spawn target does not belong to the observed loaded world cell");
                return -1L;
            }

            int legacyCount = countLegacySolZombies(targetCell);
            int shellCount = countNativeShells(targetCell);
            lastLegacyZombieCount = legacyCount;
            lastNativeShellCount = shellCount;
            if (legacyCount != 0) {
                transition(State.BLOCKED_LEGACY_ACTOR, "legacy-sol-zombie-detected");
                fail("legacy Sol zombie count=" + legacyCount + "; no actor was removed");
                return -1L;
            }
            if (shellCount != 0) {
                transition(State.BLOCKED_STALE_ACTOR, "unowned-native-shell-detected");
                fail("native shell count=" + shellCount + " with no supervisor-owned actor; no actor was removed");
                return -1L;
            }

            requestId = NEXT_REQUEST.getAndIncrement();
            pendingRequestId = requestId;
            reservedRuntime = runtimeGeneration;
            reservedWorld = worldGeneration;
            reservedActor = ++actorGeneration;
            actorRequestId = requestId;
            transition(State.SPAWN_PENDING, "spawn-request-" + requestId);
            lastError = "";
        }

        try {
            HANDOFF.execute(() -> MainThread.queueInvokeOnMainThread(
                    () -> completeSpawn(requestId, reservedRuntime, reservedWorld, reservedActor, square)));
            return requestId;
        } catch (RuntimeException failure) {
            synchronized (SolRuntimeSupervisor.class) {
                if (pendingRequestId == requestId) pendingRequestId = -1L;
                recordFailure("spawn-handoff", failure);
                transition(State.FAILED, "spawn-handoff-failed");
            }
            return -1L;
        }
    }

    private static void completeSpawn(long requestId, long expectedRuntime,
            long expectedWorld, long expectedActorGeneration, Object square) {
        if (Thread.currentThread() != MainThread.mainThread) {
            recordFailure("spawn-main-thread", new IllegalStateException("completion is off main thread"));
            return;
        }
        synchronized (SolRuntimeSupervisor.class) {
            if (pendingRequestId != requestId || state != State.SPAWN_PENDING) return;
            if (expectedRuntime != runtimeGeneration || expectedWorld != worldGeneration
                    || expectedActorGeneration != actorGeneration || observedCell == null) {
                pendingRequestId = -1L;
                transition(observedCell == null ? State.WAITING_WORLD : State.DESTROYED,
                        "stale-spawn-completion-rejected");
                lastError = "stale spawn completion fenced by runtime/world/actor generation";
                return;
            }
        }

        SolBridge.ShellCreation creation = null;
        try {
            if (!(square instanceof IsoGridSquare targetSquare) || targetSquare.getCell() != observedCell) {
                throw new IllegalStateException("spawn square changed cell before completion");
            }
            int legacyCount = countLegacySolZombies(targetSquare.getCell());
            if (legacyCount != 0) {
                synchronized (SolRuntimeSupervisor.class) {
                    pendingRequestId = -1L;
                    lastLegacyZombieCount = legacyCount;
                    transition(State.BLOCKED_LEGACY_ACTOR, "legacy-sol-zombie-before-construction");
                    lastError = "legacy Sol zombie count=" + legacyCount + "; no actor was removed";
                }
                return;
            }

            creation = SolBridge.constructShell(targetSquare);
            synchronized (SolRuntimeSupervisor.class) {
                actor = creation.body;
                actorCell = creation.cell;
                pendingRequestId = -1L;
                registrationStartedAt = System.currentTimeMillis();
                transition(State.REGISTERING, "actor-constructed");
            }

            if (expectedRuntime != runtimeGeneration || expectedWorld != worldGeneration
                    || creation.cell != observedCell) {
                throw new IllegalStateException("world/runtime generation changed during actor construction");
            }
            SolBridge.attachShell(creation);
            synchronized (SolRuntimeSupervisor.class) {
                spawnCount++;
                lastError = "";
                attemptRenderRegistration();
                pollRegistration();
            }
        } catch (Throwable failure) {
            synchronized (SolRuntimeSupervisor.class) {
                if (pendingRequestId == requestId) pendingRequestId = -1L;
                recordFailure("spawn-register", failure);
                if (creation != null && actor == null) {
                    actor = creation.body;
                    actorCell = creation.cell;
                    actorRequestId = requestId;
                }
                if (actor != null) {
                    transition(State.REMOVING, "failed-spawn-cleanup");
                    removeActorOnMainThread("failed-spawn", actor, actorCell);
                } else {
                    transition(State.FAILED, "spawn-failed-before-ownership");
                }
            }
        }
    }

    public static long requestRemove(String reason) {
        final long requestId;
        final SolIsoPlayerShell target;
        final IsoCell cell;
        synchronized (SolRuntimeSupervisor.class) {
            if (actor == null) {
                if (pendingRequestId >= 0L) {
                    pendingRequestId = -1L;
                    actorGeneration++;
                }
                transition(State.DESTROYED, "remove-empty");
                return 0L;
            }
            if (state == State.REMOVING) return actorRequestId;
            target = actor;
            cell = actorCell;
            requestId = NEXT_REQUEST.getAndIncrement();
            actorRequestId = requestId;
            transition(State.REMOVING, reason == null ? "remove-request" : reason);
        }
        try {
            HANDOFF.execute(() -> MainThread.queueInvokeOnMainThread(() -> {
                synchronized (SolRuntimeSupervisor.class) {
                    if (actor != target) return;
                    removeActorOnMainThread(reason == null ? "explicit-remove" : reason, target, cell);
                }
            }));
            return requestId;
        } catch (RuntimeException failure) {
            synchronized (SolRuntimeSupervisor.class) {
                recordFailure("remove-handoff", failure);
                transition(State.CLEANUP_PENDING, "remove-handoff-failed");
            }
            return -1L;
        }
    }

    public static synchronized void retryCleanup() {
        if (Thread.currentThread() != MainThread.mainThread) {
            fail("cleanup retry requires the game main thread");
            return;
        }
        retryCleanupOnMainThread("explicit-retry");
    }

    private static void retryCleanupOnMainThread(String reason) {
        if (actor == null) {
            transition(State.DESTROYED, reason + "-already-empty");
            return;
        }
        transition(State.REMOVING, reason);
        removeActorOnMainThread(reason, actor, actorCell);
    }

    private static void removeActorOnMainThread(String reason, SolIsoPlayerShell target, IsoCell cell) {
        cleanupAttemptCount++;
        lastCleanupAttemptAt = System.currentTimeMillis();
        cleanupStage = "model-manager";
        ArrayList<String> failures = new ArrayList<>();

        runStage("model-manager", failures, () -> SolBridge.removeModel(target));
        cleanupStage = "world-scheduler";
        runStage("world-scheduler", failures, () -> {
            if (target.getCell() != null && target.isExistInTheWorld()) {
                target.removeFromWorld();
            } else {
                MovingObjectUpdateScheduler.instance.removeObject(target);
            }
        });
        runStage("cell-membership", failures, () -> {
            if (cell != null && cell.getObjectList() != null) cell.getObjectList().remove(target);
            if (cell != null && cell.getObjectList() != null && cell.getObjectList().contains(target)) {
                throw new IllegalStateException("actor remains in IsoCell objectList");
            }
        });
        cleanupStage = "square-membership";
        runStage("square-membership", failures, target::removeFromSquare);

        String remaining = membershipSummary(target, cell);
        boolean noMemberships = noOwnedMembershipsRemain(target, cell);
        cleanupFailures = String.join(" | ", failures);
        if (noMemberships && failures.isEmpty()) {
            lastRetiredActor = new WeakReference<>(target);
            retiredUpdateCount = target.getSolUpdateCount();
            retiredStableSamples = 0;
            actor = null;
            actorCell = null;
            pendingRequestId = -1L;
            cleanupStage = "verified-absent";
            removeCount++;
            lastError = "";
            transition(State.DESTROYED, reason + "-verified");
            System.out.println("[SolRuntimeSupervisor] DESTROYED identity="
                    + System.identityHashCode(target) + " generation=" + actorGeneration
                    + " removeCount=" + removeCount);
        } else {
            cleanupStage = "retry-required";
            lastError = "cleanup incomplete; remaining=" + remaining
                    + (cleanupFailures.isEmpty() ? "" : "; failures=" + cleanupFailures);
            transition(State.CLEANUP_PENDING, reason + "-cleanup-incomplete");
            System.err.println("[SolRuntimeSupervisor] CLEANUP_PENDING identity="
                    + System.identityHashCode(target) + " generation=" + actorGeneration
                    + " attempt=" + cleanupAttemptCount + " remaining=" + remaining
                    + " failures=" + cleanupFailures);
        }
    }

    private static void pollRegistration() {
        SolIsoPlayerShell current = actor;
        if (current == null) {
            transition(State.FAILED, "registration-lost-actor-reference");
            lastError = "registration lost actor ownership reference";
            return;
        }
        if (System.currentTimeMillis() - registrationStartedAt > REGISTRATION_TIMEOUT_MILLIS) {
            recordFailure("model-registration-timeout",
                    new IllegalStateException(membershipSummary(current, actorCell)));
            transition(State.REMOVING, "registration-timeout");
            removeActorOnMainThread("registration-timeout", current, actorCell);
            return;
        }
        attemptRenderRegistration();
        if (validateActor(current, actorCell, true)) {
            lastError = "";
            transition(State.ACTIVE, "registration-postconditions-passed");
            System.out.println("[SolRuntimeSupervisor] ACTIVE identity="
                    + System.identityHashCode(current) + " actorGeneration=" + actorGeneration
                    + " worldGeneration=" + worldGeneration + " " + membershipSummary(current, actorCell));
        }
    }

    private static void attemptRenderRegistration() {
        SolIsoPlayerShell current = actor;
        if (current == null || actorCell == null) return;
        try {
            if (!ModelManager.instance.ContainsChar(current)) ModelManager.instance.Add(current);
        } catch (Throwable failure) {
            recordFailure("model-manager-add", failure);
        }
    }

    private static void onWorldCellChanged(IsoCell nextCell) {
        IsoCell previous = observedCell;
        worldGeneration++;
        observedCell = nextCell;
        if (pendingRequestId >= 0L) {
            pendingRequestId = -1L;
            actorGeneration++;
            lastError = "pending spawn cancelled by world generation change";
        }
        if (actor != null) {
            transition(State.REMOVING, "world-cell-changed");
            removeActorOnMainThread("world-cell-changed", actor, actorCell == null ? previous : actorCell);
        }
        if (actor == null) {
            transition(nextCell == null ? State.WAITING_WORLD
                    : bridgeProtocolValid ? State.WAITING_WORLD : State.WAITING_LUA,
                    nextCell == null ? "world-unavailable" : "new-world-cell");
        }
        System.out.println("[SolRuntimeSupervisor] WORLD generation=" + worldGeneration
                + " cellId=" + (nextCell == null ? 0 : System.identityHashCode(nextCell)));
    }

    private static void sampleCurrentMemberships() {
        IsoCell cell = observedCell;
        if (cell == null) {
            lastLegacyZombieCount = 0;
            lastNativeShellCount = 0;
            return;
        }
        lastLegacyZombieCount = countLegacySolZombies(cell);
        lastNativeShellCount = countNativeShells(cell);
        if (actor == null && lastNativeShellCount > 0
                && state != State.CLEANUP_PENDING && state != State.REMOVING) {
            transition(State.BLOCKED_STALE_ACTOR, "unowned-native-shell-detected-during-poll");
            lastError = "unowned native shell count=" + lastNativeShellCount;
        }
        if (actor != null && lastLegacyZombieCount > 0 && state == State.ACTIVE) {
            transition(State.BLOCKED_LEGACY_ACTOR, "legacy-zombie-coexistence-detected");
            lastError = "legacy Sol zombie count=" + lastLegacyZombieCount + "; no actor was removed";
        }
        if (actor != null && state == State.ACTIVE && lastNativeShellCount != 1) {
            transition(State.BLOCKED_STALE_ACTOR, "native-shell-count-invariant-failed");
            lastError = "native shell count=" + lastNativeShellCount + "; expected exactly one";
        }
    }

    private static boolean validateActor(SolIsoPlayerShell current, IsoCell cell, boolean includeModel) {
        if (current == null || cell == null || cell != observedCell || current.isDead()) return false;
        try {
            IsoGridSquare square = current.getCurrentSquare();
            if (square == null || square.getCell() != cell || square.getChunk() == null) return false;
            if (!current.isExistInTheWorld()) return false;
            if (!square.getMovingObjects().contains(current)) return false;
            if (!cell.getObjectList().contains(current)) return false;
            if (current.isLocalPlayer()) return false;
            if (inLocalPlayerSlots(current)) return false;
            if (IsoPlayerSingleton.isActorInstance(current)) return false;
            if (countLegacySolZombies(cell) != 0 || countNativeShells(cell) != 1) return false;
            if (includeModel && (!ModelManager.instance.ContainsChar(current)
                    || !current.isAddedToModelManager() || !current.hasActiveModel())) return false;
            return true;
        } catch (Throwable failure) {
            recordFailure("actor-validation", failure);
            return false;
        }
    }

    private static int countNativeShells(IsoCell cell) {
        try {
            Set<IsoMovingObject> objects = cell == null ? null : cell.getObjectList();
            if (objects == null) return 0;
            int count = 0;
            for (IsoMovingObject object : objects) if (object instanceof SolIsoPlayerShell) count++;
            return count;
        } catch (Throwable failure) {
            recordFailure("native-shell-count", failure);
            return -1;
        }
    }

    private static int countLegacySolZombies(IsoCell cell) {
        try {
            if (cell == null || cell.getZombieList() == null) return 0;
            int count = 0;
            for (IsoZombie zombie : cell.getZombieList()) {
                Object modData = zombie.getModData();
                Method rawget = modData.getClass().getMethod("rawget", Object.class);
                Object marker = rawget.invoke(modData, "solEmbodied");
                if (Boolean.TRUE.equals(marker)) count++;
            }
            return count;
        } catch (Throwable failure) {
            recordFailure("legacy-zombie-scan", failure);
            return -1;
        }
    }

    private static boolean noOwnedMembershipsRemain(SolIsoPlayerShell target, IsoCell cell) {
        try {
            boolean cellAbsent = cell == null || cell.getObjectList() == null
                    || !cell.getObjectList().contains(target);
            boolean worldAbsent = !target.isExistInTheWorld();
            IsoGridSquare current = target.getCurrentSquare();
            IsoGridSquare moving = target.getMovingSquare();
            boolean squareAbsent = current == null && moving == null;
            if (current != null && current.getMovingObjects().contains(target)) squareAbsent = false;
            if (moving != null && moving.getMovingObjects().contains(target)) squareAbsent = false;
            boolean rendererAbsent = !ModelManager.instance.ContainsChar(target)
                    && !target.isAddedToModelManager() && !target.hasActiveModel();
            return cellAbsent && worldAbsent && squareAbsent && rendererAbsent;
        } catch (Throwable failure) {
            recordFailure("cleanup-postcondition-read", failure);
            return false;
        }
    }

    private static String membershipSummary(SolIsoPlayerShell target, IsoCell cell) {
        if (target == null) return "actor=nil";
        try {
            IsoGridSquare square = target.getCurrentSquare();
            return "world=" + target.isExistInTheWorld()
                    + ",cell=" + (cell != null && cell.getObjectList() != null && cell.getObjectList().contains(target))
                    + ",square=" + (square != null && square.getMovingObjects().contains(target))
                    + ",model=" + ModelManager.instance.ContainsChar(target)
                    + ",modelAdded=" + target.isAddedToModelManager()
                    + ",activeModel=" + target.hasActiveModel()
                    + ",currentSquare=" + (square == null ? "nil" : square.getX() + "," + square.getY() + "," + square.getZ());
        } catch (Throwable failure) {
            return "membership-unavailable=" + failure.getClass().getSimpleName();
        }
    }

    private static void sampleRetiredActor() {
        SolIsoPlayerShell retired = lastRetiredActor.get();
        if (retired == null) return;
        long count = retired.getSolUpdateCount();
        if (count == retiredUpdateCount) retiredStableSamples++;
        else {
            retiredUpdateCount = count;
            retiredStableSamples = 0;
        }
    }

    private static IsoCell currentWorldCell() {
        IsoWorld world = IsoWorld.instance;
        return world == null ? null : world.getCell();
    }

    private static boolean inLocalPlayerSlots(SolIsoPlayerShell target) throws Exception {
        Object slots = IsoPlayer.class.getField("players").get(null);
        int length = java.lang.reflect.Array.getLength(slots);
        for (int i = 0; i < length; i++) {
            if (java.lang.reflect.Array.get(slots, i) == target) return true;
        }
        return false;
    }

    private static void runStage(String name, ArrayList<String> failures, ThrowingAction action) {
        cleanupStage = name;
        try {
            action.run();
        } catch (Throwable failure) {
            failures.add(name + ":" + failure.getClass().getSimpleName() + ":" + clean(failure.getMessage()));
        }
    }

    private static synchronized void fail(String reason) {
        lastError = reason == null ? "unknown failure" : reason;
    }

    private static synchronized void recordFailure(String stage, Throwable failure) {
        lastError = stage + ":" + failure.getClass().getSimpleName() + ":" + clean(failure.getMessage());
    }

    private static void transition(State next, String reason) {
        if (next == null) return;
        if (state != next || !reason.equals(lastTransition)) {
            System.out.println("[SolRuntimeSupervisor] STATE " + state + "->" + next + " reason=" + reason
                    + " runtime=" + runtimeGeneration + " world=" + worldGeneration
                    + " env=" + environmentGeneration + " actor=" + actorGeneration);
        }
        state = next;
        lastTransition = reason;
    }

    public static String getBackend() {
        String selected = System.getProperty("sol.backend", "NATIVE_SHELL");
        return selected == null ? "NATIVE_SHELL" : selected.trim().toUpperCase(java.util.Locale.ROOT);
    }

    public static String getProtocol() { return PROTOCOL; }
    public static SolIsoPlayerShell actor() { return actor; }
    public static synchronized boolean actorReady() { return actor != null && state == State.ACTIVE; }
    public static synchronized String getState() { return state.name().toLowerCase(java.util.Locale.ROOT); }
    public static synchronized String getFailure() { return lastError; }
    public static synchronized long requestId() { return actorRequestId; }
    public static synchronized void noteError(String stage, Throwable failure) { recordFailure(stage, failure); }

    public static synchronized String describe() {
        SolIsoPlayerShell current = actor;
        IsoCell cell = current == null ? observedCell : actorCell;
        int nativeCount = cell == null ? 0 : countNativeShells(cell);
        int legacyCount = cell == null ? 0 : countLegacySolZombies(cell);
        lastNativeShellCount = nativeCount;
        lastLegacyZombieCount = legacyCount;
        int localSlot = -1;
        int serverSlot = -1;
        boolean local = false;
        boolean inSlots = false;
        boolean globalInstance = false;
        String square = "unknown";
        String worldMember = "unknown";
        String cellMember = "unknown";
        String squareMember = "unknown";
        String modelMember = "unknown";
        String activeModel = "unknown";
        long updates = -1L;
        int actorIdentity = 0;
        if (current != null) {
            actorIdentity = System.identityHashCode(current);
            try {
                local = current.isLocalPlayer();
                localSlot = IsoPlayer.class.getField("playerIndex").getInt(current);
                serverSlot = IsoPlayer.class.getField("serverPlayerIndex").getInt(current);
                inSlots = inLocalPlayerSlots(current);
                globalInstance = IsoPlayer.getInstance() == current;
                updates = current.getSolUpdateCount();
                IsoGridSquare currentSquare = current.getCurrentSquare();
                square = currentSquare == null ? "nil" : currentSquare.getX() + "," + currentSquare.getY() + "," + currentSquare.getZ();
                worldMember = Boolean.toString(current.isExistInTheWorld());
                cellMember = Boolean.toString(actorCell != null && actorCell.getObjectList() != null && actorCell.getObjectList().contains(current));
                squareMember = Boolean.toString(currentSquare != null && currentSquare.getMovingObjects().contains(current));
                modelMember = Boolean.toString(ModelManager.instance.ContainsChar(current) && current.isAddedToModelManager());
                activeModel = Boolean.toString(current.hasActiveModel());
            } catch (Throwable failure) {
                recordFailure("diagnostics", failure);
            }
        }
        SolIsoPlayerShell retired = lastRetiredActor.get();
        return "supervisorState=" + state
                + " runtimeGeneration=" + runtimeGeneration
                + " worldGeneration=" + worldGeneration
                + " luaEnvironmentGeneration=" + environmentGeneration
                + " backend=" + getBackend()
                + " actorExists=" + (current != null)
                + " actorIdentity=" + actorIdentity
                + " actorGeneration=" + actorGeneration
                + " actorClass=" + (current == null ? "nil" : current.getClass().getName())
                + " nativeShellCount=" + nativeCount
                + " legacyZombieCount=" + legacyCount
                + " localPlayer=" + local
                + " inLocalSlots=" + inSlots
                + " globalInstance=" + globalInstance
                + " playerIndex=" + localSlot
                + " serverPlayerIndex=" + serverSlot
                + " square=" + square
                + " worldMembership=" + worldMember
                + " cellMembership=" + cellMember
                + " squareMembership=" + squareMember
                + " modelManager=" + modelMember
                + " activeModel=" + activeModel
                + " updateOwner=Vanilla-IsoCell-MovingObjectUpdateScheduler"
                + " updateCount=" + updates
                + " directSupervisorUpdateCount=0"
                + " spawnCount=" + spawnCount
                + " removeCount=" + removeCount
                + " cleanupStage=" + cleanupStage
                + " cleanupAttemptCount=" + cleanupAttemptCount
                + " cleanupFailures=" + clean(cleanupFailures)
                + " staleActor=" + Math.max(0, nativeCount - (current == null ? 0 : 1))
                + " bridgeProtocolValid=" + bridgeProtocolValid
                + " bridgeGeneration=" + environmentGeneration
                + " bridgeEnvId=" + bridgeEnvironmentId
                + " bridgeExposerId=" + bridgeExposerId
                + " exposureCount=" + exposureCount
                + " retiredActorIdentity=" + (retired == null ? 0 : System.identityHashCode(retired))
                + " retiredUpdateCount=" + (retired == null ? -1 : retired.getSolUpdateCount())
                + " retiredStableSamples=" + retiredStableSamples
                + " lastTransition=" + clean(lastTransition)
                + " lastLifecycleError=" + clean(lastError);
    }

    private static String clean(String value) {
        return value == null ? "" : value.replace('\n', ' ').replace('\r', ' ');
    }

    private static final class IsoPlayerSingleton {
        private static boolean isActorInstance(SolIsoPlayerShell candidate) {
            return zombie.characters.IsoPlayer.getInstance() == candidate;
        }
    }

    @FunctionalInterface
    private interface ThrowingAction { void run() throws Throwable; }
}

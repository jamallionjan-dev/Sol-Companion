package sol.bridge;

import java.lang.reflect.Array;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;
import se.krka.kahlua.vm.KahluaTable;
import zombie.MainThread;
import zombie.characters.IsoPlayer;
import zombie.characters.IsoZombie;
import zombie.characters.SurvivorDesc;
import zombie.iso.IsoCell;
import zombie.iso.IsoWorld;

public final class SolBridge {
    public static final String PROTOCOL = SolRuntimeSupervisor.PROTOCOL;
    private static final ExecutorService HANDOFF = Executors.newSingleThreadExecutor(task -> {
        Thread thread = new Thread(task, "SolNativeShell-handoff");
        thread.setDaemon(true);
        return thread;
    });
    private static final AtomicLong NEXT_OPERATION = new AtomicLong(1L);

    private SolBridge() {}

    public static String ping() { return "SOL_NATIVE_PONG"; }
    public static String status() { return SolBootstrap.getStatus() + ";" + SolRuntimeSupervisor.getState(); }
    public static String getProtocol() { return SolRuntimeSupervisor.getProtocol(); }
    public static String getBackend() { return SolRuntimeSupervisor.getBackend(); }
    public static String getSupervisorStatus() { return SolRuntimeSupervisor.describe(); }
    public static long requestTestShellSpawn(Object square) { return SolRuntimeSupervisor.requestSpawn(square); }
    /** Read-only handle to the single supervisor-owned test actor, if present. */
    public static SolIsoPlayerShell getTestShellActor() { return SolRuntimeSupervisor.actor(); }
    public static long retryTestShellCleanup() { SolRuntimeSupervisor.retryCleanup(); return SolRuntimeSupervisor.requestId(); }
    public static String getTestShellState() { return SolRuntimeSupervisor.getState(); }
    public static String getTestShellFailure() { return SolRuntimeSupervisor.getFailure(); }

    /**
     * Copies a bounded, point-in-time zombie roster into the caller-owned Lua table.
     * Numeric keys contain actor,id,x,y,z quintuples. This reads only and must
     * execute on the game main thread. Missing world/list and invalid records
     * are unavailable (-1), while capacity overflow (-2) publishes no prefix.
     */
    public static int fillZombieSnapshot(KahluaTable out, int maximum) {
        if (Thread.currentThread() != MainThread.mainThread || out == null
                || maximum < 0 || maximum > 8192) {
            return -1;
        }
        try {
            out.wipe();
            IsoWorld world = IsoWorld.instance;
            IsoCell cell = world == null ? null : world.getCell();
            ArrayList<IsoZombie> zombies = cell == null ? null : cell.getZombieList();
            if (zombies == null) return -1;
            int count = zombies.size();
            if (count > maximum) {
                putLuaValue(out, "requiredCount", count);
                return -2;
            }
            int output = 1;
            for (int index = 0; index < count; index++) {
                IsoZombie zombie = zombies.get(index);
                if (zombie == null) {
                    out.wipe();
                    return -1;
                }
                float x = zombie.getX();
                float y = zombie.getY();
                float z = zombie.getZ();
                if (!Float.isFinite(x) || !Float.isFinite(y) || !Float.isFinite(z)) {
                    out.wipe();
                    return -1;
                }
                putLuaValue(out, output++, zombie);
                putLuaValue(out, output++, zombie.getID());
                putLuaValue(out, output++, x);
                putLuaValue(out, output++, y);
                putLuaValue(out, output++, z);
            }
            putLuaValue(out, "count", count);
            return count;
        } catch (RuntimeException | LinkageError failure) {
            try { out.wipe(); } catch (RuntimeException ignored) {}
            return -1;
        }
    }

    private static void putLuaValue(KahluaTable table, int key, Object value) {
        Object normalized = value instanceof Number number
                ? Double.valueOf(number.doubleValue()) : value;
        table.rawset(key, normalized);
    }

    private static void putLuaValue(KahluaTable table, String key, Object value) {
        Object normalized = value instanceof Number number
                ? Double.valueOf(number.doubleValue()) : value;
        table.rawset(key, normalized);
    }

    public static String describeTestShell() {
        SolIsoPlayerShell body = SolRuntimeSupervisor.actor();
        if (body == null) return "state=" + SolRuntimeSupervisor.getState()
                + " failure=" + SolRuntimeSupervisor.getFailure()
                + " supervisor=[" + SolRuntimeSupervisor.describe() + "]";
        try {
            Class<?> playerClass = Class.forName("zombie.characters.IsoPlayer", false, body.getClass().getClassLoader());
            int index = playerClass.getField("playerIndex").getInt(body);
            int serverIndex = playerClass.getField("serverPlayerIndex").getInt(body);
            boolean remote = playerClass.getField("remote").getBoolean(body);
            Object instance = playerClass.getMethod("getInstance").invoke(null);
            boolean inLocalSlots = isInLocalPlayerSlots(body, playerClass);
            Object currentSquare = invoke0(body, "getCurrentSquare");
            Object model = invoke0(body, "getModelInstance");
            Object added = invoke0(body, "isAddedToModelManager");
            Object active = invoke0(body, "hasActiveModel");
            Object alpha = invoke(body, "getAlpha", new Class<?>[] { int.class }, 0);
            Object targetAlpha = invoke(body, "getTargetAlpha", new Class<?>[] { int.class }, 0);
            return "state=" + SolRuntimeSupervisor.getState()
                + " class=" + body.getClass().getName()
                + " playerIndex=" + index
                + " serverPlayerIndex=" + serverIndex
                + " remote=" + remote
                + " local=" + body.isLocalPlayer()
                + " inLocalSlots=" + inLocalSlots
                + " isGlobalInstance=" + (instance == body)
                + " square=" + currentSquare
                + " addedToModelManager=" + added
                + " activeModel=" + active
                + " model=" + model
                + " alpha0=" + alpha
                + " targetAlpha0=" + targetAlpha
                + " supervisor=[" + SolRuntimeSupervisor.describe() + "]";
        } catch (Throwable failure) {
            return "describe-error=" + failure.getClass().getSimpleName() + ":" + clean(failure.getMessage());
        }
    }


    public static String describeTestShellVisibility() {
        SolIsoPlayerShell body = SolRuntimeSupervisor.actor();
        if (body == null) return "state=" + SolRuntimeSupervisor.getState() + " body=nil";
        try {
            ClassLoader loader = body.getClass().getClassLoader();
            Class<?> playerClass = Class.forName("zombie.characters.IsoPlayer", false, loader);
            Class<?> characterClass = Class.forName("zombie.characters.IsoGameCharacter", false, loader);
            Object local = playerClass.getMethod("getInstance").invoke(null);
            if (local == null) return "state=" + SolRuntimeSupervisor.getState() + " local=nil";
            int localIndex = playerClass.getField("playerIndex").getInt(local);
            int shellIndex = playerClass.getField("playerIndex").getInt(body);
            Object localSquare = invoke0(local, "getCurrentSquare");
            Object shellSquare = invoke0(body, "getCurrentSquare");
            Object localX = invoke0(local, "getX");
            Object localY = invoke0(local, "getY");
            Object shellX = invoke0(body, "getX");
            Object shellY = invoke0(body, "getY");
            float dx = ((Number) shellX).floatValue() - ((Number) localX).floatValue();
            float dy = ((Number) shellY).floatValue() - ((Number) localY).floatValue();
            double distance = Math.sqrt(dx * dx + dy * dy);
            Object isCanSee = shellSquare == null ? null : invoke(shellSquare, "isCanSee", new Class<?>[] { int.class }, localIndex);
            Object isCouldSee = shellSquare == null ? null : invoke(shellSquare, "isCouldSee", new Class<?>[] { int.class }, localIndex);
            Object getCanSee = shellSquare == null ? null : invoke(shellSquare, "getCanSee", new Class<?>[] { int.class }, localIndex);
            boolean[] visible = (boolean[]) characterClass.getField("isVisibleToPlayer").get(body);
            boolean visibleToLocal = localIndex >= 0 && localIndex < visible.length && visible[localIndex];
            Object alpha = invoke(body, "getAlpha", new Class<?>[] { int.class }, localIndex);
            Object targetAlpha = invoke(body, "getTargetAlpha", new Class<?>[] { int.class }, localIndex);
            boolean gameClient = Class.forName("zombie.network.GameClient", false, loader).getField("client").getBoolean(null);
            boolean gameServer = Class.forName("zombie.network.GameServer", false, loader).getField("server").getBoolean(null);
            return "state=" + SolRuntimeSupervisor.getState()
                + " gameClient=" + gameClient
                + " gameServer=" + gameServer
                + " localIndex=" + localIndex
                + " shellIndex=" + shellIndex
                + " localPos=" + localX + "," + localY
                + " shellPos=" + shellX + "," + shellY
                + " distance=" + distance
                + " localSquare=" + localSquare
                + " shellSquare=" + shellSquare
                + " isCanSee=" + isCanSee
                + " isCouldSee=" + isCouldSee
                + " getCanSee=" + getCanSee
                + " isVisibleToPlayer=" + visibleToLocal
                + " alpha=" + alpha
                + " targetAlpha=" + targetAlpha;
        } catch (Throwable failure) {
            return "visibility-describe-error=" + failure.getClass().getSimpleName() + ":" + clean(failure.getMessage());
        }
    }

    public static synchronized long requestTestShellMove(float x, float y, float z) {
        SolIsoPlayerShell body = SolRuntimeSupervisor.actor();
        if (body == null || !SolRuntimeSupervisor.actorReady()) return -1L;
        long id = NEXT_OPERATION.getAndIncrement();
        HANDOFF.execute(() -> MainThread.queueInvokeOnMainThread(() -> {
            try {
                body.pathToLocationF(x, y, z);
                System.out.println("[SolNativeShell] MOVE_REQUEST id=" + id + " target=" + x + "," + y + "," + z);
            } catch (Throwable failure) {
                SolRuntimeSupervisor.noteError("movement-command", failure);
                System.err.println("[SolNativeShell] MOVE_FAILED " + SolRuntimeSupervisor.getFailure());
            }
        }));
        return id;
    }

    public static boolean stopTestShellMovement() {
        SolIsoPlayerShell body = SolRuntimeSupervisor.actor();
        if (body == null) return false;
        try {
            Object behavior = invoke0(body, "getPathFindBehavior2");
            if (behavior != null) invoke0(behavior, "cancel");
            Class<?> pathClass = Class.forName("zombie.pathfind.Path", false, body.getClass().getClassLoader());
            invoke(body, "setPath2", new Class<?>[] { pathClass }, new Object[] { null });
 body.stopSolPathOwnership();
            return true;
        } catch (Throwable failure) {
            SolRuntimeSupervisor.noteError("movement-stop", failure);
            return false;
        }
    }

    public static String describeTestShellMovement() {
        SolIsoPlayerShell body = SolRuntimeSupervisor.actor();
        if (body == null) return "state=" + SolRuntimeSupervisor.getState() + " body=nil";
        try {
            Object behavior = invoke0(body, "getPathFindBehavior2");
            Object x = invoke0(body, "getX");
            Object y = invoke0(body, "getY");
            Object z = invoke0(body, "getZ");
            Object moving = invoke0(body, "isMoving");
            Object playerMoving = invoke0(body, "isPlayerMoving");
            Object bPathfind = invoke(body, "getVariableBoolean", new Class<?>[] { String.class }, "bPathfind");
            Object should = behavior == null ? null : invoke0(behavior, "shouldBeMoving");
            Object using = behavior == null ? null : invoke0(behavior, "isMovingUsingPathFind");
            Object started = behavior == null ? null : invoke0(behavior, "hasStartedMoving");
            Object path = invoke0(body, "getPath2");
            Object finder = invoke0(body, "getFinder");
            Object progress = null;
            if (finder != null) {
                java.lang.reflect.Field progressField = finder.getClass().getField("progress");
                progress = progressField.get(finder);
            }
            Object cancelled = behavior == null ? null : invoke0(behavior, "getIsCancelled");
            Object targetX = behavior == null ? null : invoke0(behavior, "getTargetX");
            Object targetY = behavior == null ? null : invoke0(behavior, "getTargetY");
            Object targetZ = behavior == null ? null : invoke0(behavior, "getTargetZ");
            Object pathLength = behavior == null ? null : invoke0(behavior, "getPathLength");
            Object updateCount = invoke0(body, "getSolUpdateCount");
            Object pathExecAttempts = invoke0(body, "getSolPathExecuteAttempts");
            Object pathExecSuccesses = invoke0(body, "getSolPathExecuteSuccesses");
            Object pathExecSkippedCurrentState = invoke0(body, "getSolPathExecuteSkippedCurrentState");
            Object pathTraceBefore = invoke0(body, "getSolPathExecuteTraceBefore");
            Object pathTraceAfter = invoke0(body, "getSolPathExecuteTraceAfter");
            return "state=" + SolRuntimeSupervisor.getState()
                + " pos=" + x + "," + y + "," + z
                + " moving=" + moving
                + " playerMoving=" + playerMoving
                + " bPathfind=" + bPathfind
                + " shouldBeMoving=" + should
                + " usingPath=" + using
                + " started=" + started
                + " pathAttached=" + (path != null) + " progress=" + progress + " cancelled=" + cancelled + " target=" + targetX + "," + targetY + "," + targetZ + " pathLength=" + pathLength + " updateCount=" + updateCount + " pathExecAttempts=" + pathExecAttempts + " pathExecSuccesses=" + pathExecSuccesses + " pathExecSkippedCurrentState=" + pathExecSkippedCurrentState
                + " pathExecTraceBefore=[" + pathTraceBefore + "] pathExecTraceAfter=[" + pathTraceAfter + "]";
        } catch (Throwable failure) {
            return "movement-describe-error=" + failure.getClass().getSimpleName() + ":" + clean(failure.getMessage());
        }
    }

    public static long requestTestShellRemove() {
        return SolRuntimeSupervisor.requestRemove("lua-request");
    }

    static final class ShellCreation {
        final SolIsoPlayerShell body;
        final IsoCell cell;
        final Object square;
        final Object[] slotsBefore;
        final Object expectedInstance;

        ShellCreation(SolIsoPlayerShell body, IsoCell cell, Object square,
                Object[] slotsBefore, Object expectedInstance) {
            this.body = body;
            this.cell = cell;
            this.square = square;
            this.slotsBefore = slotsBefore;
            this.expectedInstance = expectedInstance;
        }
    }

    static ShellCreation constructShell(Object square) throws Exception {
        if (Thread.currentThread() != MainThread.mainThread) {
            throw new IllegalStateException("shell construction must run on the game main thread");
        }
        ClassLoader loader = SolBridge.class.getClassLoader();
        Class<?> playerClass = Class.forName("zombie.characters.IsoPlayer", false, loader);
        Object[] slotsBefore = snapshotLocalPlayers(playerClass);
        Object instanceBefore = playerClass.getMethod("getInstance").invoke(null);
        Object expectedInstance = slotsBefore.length > 0 && slotsBefore[0] != null
                ? slotsBefore[0] : instanceBefore;
        Object cellObject = invoke0(square, "getCell");
        int x = ((Number) invoke0(square, "getX")).intValue();
        int y = ((Number) invoke0(square, "getY")).intValue();
        int z = ((Number) invoke0(square, "getZ")).intValue();
        Class<?> survivorFactory = Class.forName("zombie.characters.SurvivorFactory", false, loader);
        Object descriptorObject = survivorFactory.getMethod("CreateSurvivor").invoke(null);
        applyCanonicalTestAppearance(descriptorObject, loader);
        SolIsoPlayerShell body;
        try {
            body = new SolIsoPlayerShell((IsoCell) cellObject,
                    (SurvivorDesc) descriptorObject, x, y, z, false);
        } finally {
            playerClass.getMethod("setInstance", playerClass).invoke(null, expectedInstance);
        }
        return new ShellCreation(body, (IsoCell) cellObject, square, slotsBefore, expectedInstance);
    }

    /**
     * Gives the test-only shell a stable appearance before IsoPlayer builds its model.
     * Keep the SurvivorFactory's existing type selection and change only appearance.
     */
    private static void applyCanonicalTestAppearance(Object descriptor, ClassLoader loader) throws Exception {
        Class<?> descriptorClass = Class.forName("zombie.characters.SurvivorDesc", false, loader);
        descriptorClass.getMethod("setFemale", boolean.class).invoke(descriptor, true);

        Class<?> immutableColorClass = Class.forName("zombie.core.ImmutableColor", false, loader);
        Object white = immutableColorClass.getField("white").get(null);
        Object red = immutableColorClass.getConstructor(
                float.class, float.class, float.class, float.class)
                .newInstance(0.78f, 0.08f, 0.10f, 1.0f);

        Object humanVisual = invoke0(descriptor, "getHumanVisual");
        Class<?> humanVisualClass = Class.forName(
                "zombie.core.skinnedmodel.visual.HumanVisual", false, loader);
        humanVisualClass.getMethod("setSkinTextureIndex", int.class).invoke(humanVisual, 0);
        humanVisualClass.getMethod("setSkinColor", immutableColorClass).invoke(humanVisual, white);
        humanVisualClass.getMethod("setHairModel", String.class).invoke(humanVisual, "PonyTail");
        humanVisualClass.getMethod("setHairColor", immutableColorClass).invoke(humanVisual, red);
        humanVisualClass.getMethod("setNaturalHairColor", immutableColorClass).invoke(humanVisual, red);

        Object wornItems = invoke0(descriptor, "getWornItems");
        invoke0(wornItems, "clear");

        addCanonicalTestClothing(loader, descriptor, "Base.Dress_Long", "LONG_DRESS", red);
        addCanonicalTestClothing(loader, descriptor, "Base.Socks_Ankle_White", "SOCKS", null);
        addCanonicalTestClothing(loader, descriptor, "Base.Shoes_Fancy", "SHOES", null);
    }

    private static void addCanonicalTestClothing(
            ClassLoader loader, Object descriptor, String itemType, String bodyLocationField,
            Object tint) throws Exception {
        Class<?> itemFactoryClass = Class.forName("zombie.inventory.InventoryItemFactory", false, loader);
        Object item = itemFactoryClass.getMethod("CreateItem", String.class).invoke(null, itemType);
        if (item == null) {
            throw new IllegalStateException("canonical test appearance item unavailable: " + itemType);
        }

        if (tint != null) {
            Object itemVisual = invoke0(item, "getVisual");
            if (itemVisual == null) {
                throw new IllegalStateException("canonical test appearance item has no visual: " + itemType);
            }
            Class<?> immutableColorClass = Class.forName("zombie.core.ImmutableColor", false, loader);
            Class<?> itemVisualClass = Class.forName(
                    "zombie.core.skinnedmodel.visual.ItemVisual", false, loader);
            itemVisualClass.getMethod("setTint", immutableColorClass).invoke(itemVisual, tint);
            item.getClass().getMethod("synchWithVisual").invoke(item);
        }

        Class<?> bodyLocationClass = Class.forName("zombie.scripting.objects.ItemBodyLocation", false, loader);
        Object bodyLocation = bodyLocationClass.getField(bodyLocationField).get(null);
        Class<?> inventoryItemClass = Class.forName("zombie.inventory.InventoryItem", false, loader);
        Class<?> descriptorClass = Class.forName("zombie.characters.SurvivorDesc", false, loader);
        descriptorClass.getMethod("setWornItem", bodyLocationClass, inventoryItemClass)
                .invoke(descriptor, bodyLocation, item);
    }

    static void attachShell(ShellCreation creation) throws Exception {
        SolIsoPlayerShell body = creation.body;
        Class<?> loaderClass = body.getClass();
        ClassLoader loader = loaderClass.getClassLoader();
        Class<?> playerClass = Class.forName("zombie.characters.IsoPlayer", false, loader);
        int x = ((Number) invoke0(creation.square, "getX")).intValue();
        int y = ((Number) invoke0(creation.square, "getY")).intValue();
        int z = ((Number) invoke0(creation.square, "getZ")).intValue();
        int offSlot = allocateOffSlotPlayerIndex(playerClass);
        playerClass.getMethod("setNpc", boolean.class).invoke(body, true);
        playerClass.getField("remote").setBoolean(body, false);
        playerClass.getField("playerIndex").setInt(body, offSlot);
        playerClass.getField("serverPlayerIndex").setInt(body, -1);
        playerClass.getMethod("setOnlineID", short.class).invoke(body, (short) -1);
        playerClass.getMethod("setUsername", String.class).invoke(body, "Sol Native Test");
        invoke(body, "setGhostMode", new Class<?>[] { boolean.class }, false);
        invoke(body, "setX", new Class<?>[] { float.class }, x + 0.5f);
        invoke(body, "setY", new Class<?>[] { float.class }, y + 0.5f);
        invoke(body, "setZ", new Class<?>[] { float.class }, (float) z);

        Class<?> squareClass = Class.forName("zombie.iso.IsoGridSquare", false, loader);
        invoke(body, "setCurrentSquare", new Class<?>[] { squareClass }, creation.square);
        invoke(body, "setSquare", new Class<?>[] { squareClass }, creation.square);
        invoke(body, "setMovingSquare", new Class<?>[] { squareClass }, creation.square);
        invoke(body, "setAlphaAndTarget", new Class<?>[] { float.class }, 1.0f);
        invoke(body, "setSceneCulled", new Class<?>[] { boolean.class }, false);
        invoke0(body, "addToWorld");

        Object movingObjects = invoke0(creation.square, "getMovingObjects");
        if (!(movingObjects instanceof java.util.List<?> movingList)) {
            throw new IllegalStateException("IsoGridSquare moving-object list unavailable");
        }
        @SuppressWarnings("unchecked")
        java.util.List<Object> writableMovingList = (java.util.List<Object>) movingList;
        if (!writableMovingList.contains(body)) writableMovingList.add(body);

        Object objectList = invoke0(creation.cell, "getObjectList");
        if (!(objectList instanceof java.util.Set<?> set)) {
            throw new IllegalStateException("IsoCell object list unavailable");
        }
        @SuppressWarnings("unchecked")
        java.util.Set<Object> writableObjectList = (java.util.Set<Object>) set;
        if (!writableObjectList.contains(body)) writableObjectList.add(body);

        Class<?> managerClass = Class.forName("zombie.core.skinnedmodel.ModelManager", false, loader);
        Object manager = managerClass.getField("instance").get(null);
        Class<?> characterClass = Class.forName("zombie.characters.IsoGameCharacter", false, loader);
        if (!(Boolean) invoke(manager, "ContainsChar", new Class<?>[] { characterClass }, body)) {
            invoke(manager, "Add", new Class<?>[] { characterClass }, body);
        }
        if (!sameSlots(creation.slotsBefore, snapshotLocalPlayers(playerClass))) {
            throw new IllegalStateException("local-player slots changed during shell registration");
        }
        Object instanceAfter = playerClass.getMethod("getInstance").invoke(null);
        if (instanceAfter != creation.expectedInstance) {
            playerClass.getMethod("setInstance", playerClass).invoke(null, creation.expectedInstance);
            throw new IllegalStateException("global IsoPlayer.instance changed during shell registration");
        }
        if (!writableMovingList.contains(body) || !writableObjectList.contains(body)) {
            throw new IllegalStateException("shell registration membership readback failed");
        }
    }

    static void removeModel(SolIsoPlayerShell body) throws Exception {
        ClassLoader loader = body.getClass().getClassLoader();
        Class<?> managerClass = Class.forName("zombie.core.skinnedmodel.ModelManager", false, loader);
        Object manager = managerClass.getField("instance").get(null);
        Class<?> characterClass = Class.forName("zombie.characters.IsoGameCharacter", false, loader);
        if ((Boolean) invoke(manager, "ContainsChar", new Class<?>[] { characterClass }, body)) {
            invoke(manager, "Remove", new Class<?>[] { characterClass }, body);
        }
    }

    private static int allocateOffSlotPlayerIndex(Class<?> playerClass) throws Exception {
        Object players = playerClass.getField("players").get(null);
        int length = Array.getLength(players);
        for (int i = 1; i < length; i++) {
            if (Array.get(players, i) == null) return i;
        }
        throw new IllegalStateException("no free non-local player index");
    }

    private static Object[] snapshotLocalPlayers(Class<?> playerClass) throws Exception {
        Object players = playerClass.getField("players").get(null);
        int length = Array.getLength(players);
        Object[] result = new Object[length];
        for (int i = 0; i < length; i++) result[i] = Array.get(players, i);
        return result;
    }

    private static boolean sameSlots(Object[] first, Object[] second) {
        if (first.length != second.length) return false;
        for (int i = 0; i < first.length; i++) {
            if (first[i] != second[i]) return false;
        }
        return true;
    }

    private static boolean isInLocalPlayerSlots(Object body, Class<?> playerClass) throws Exception {
        for (Object player : snapshotLocalPlayers(playerClass)) {
            if (player == body) return true;
        }
        return false;
    }

    private static Object invoke0(Object target, String name) throws Exception {
        Method method = target.getClass().getMethod(name);
        return method.invoke(target);
    }

    private static Object invoke(Object target, String name, Class<?>[] types, Object... args) throws Exception {
        Method method = target.getClass().getMethod(name, types);
        return method.invoke(target, args);
    }

    private static String clean(String value) {
        if (value == null) return "";
        return value.replace((char) 10, ' ').replace((char) 13, ' ');
    }
}

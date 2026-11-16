package sol.bridge;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

import zombie.characters.IsoGameCharacter;
import zombie.characters.IsoPlayer;
import zombie.characters.SurvivorDesc;
import zombie.iso.IsoCell;

public final class SolIsoPlayerShell extends IsoPlayer {
    private static final Method GENERIC_CHARACTER_UPDATE = resolveGenericCharacterUpdate();

    private boolean solPathActive = false;
    private long solUpdateCount = 0L;
    private long solPathExecuteAttempts = 0L;
    private long solPathExecuteSuccesses = 0L;
    private long solPathExecuteSkippedCurrentState = 0L;
    private volatile String solPathExecuteTraceBefore = "not_sampled";
    private volatile String solPathExecuteTraceAfter = "not_sampled";

    private static Method resolveGenericCharacterUpdate() {
        try {
            Method method = IsoGameCharacter.class.getDeclaredMethod("updateInternal");
 method.setAccessible(true);
 return method;
 } catch (ReflectiveOperationException | RuntimeException failure) {
 return null;
 }
 }

 private void updateGenericCharacter() {
 if (GENERIC_CHARACTER_UPDATE == null) {
            throw new IllegalStateException("generic IsoGameCharacter update is unavailable");
 }
 try {
 GENERIC_CHARACTER_UPDATE.invoke(this);
 } catch (IllegalAccessException failure) {
            throw new IllegalStateException("generic IsoGameCharacter update is inaccessible", failure);
 } catch (InvocationTargetException failure) {
 Throwable cause = failure.getCause();
 if (cause instanceof RuntimeException) throw (RuntimeException) cause;
 if (cause instanceof Error) throw (Error) cause;
            throw new IllegalStateException("generic IsoGameCharacter update failed", cause);
 }
 }

    private void advanceSolPath() {
        if (!solPathActive) return;
        try {
            Class<?> pathFindStateClass = Class.forName("zombie.ai.states.PathFindState");
            Object state = pathFindStateClass.getMethod("instance").invoke(null);
            Method getStateMachine = getClass().getMethod("getStateMachine");
            Object stateMachine = getStateMachine.invoke(this);
            Object currentState = null;
            if (stateMachine != null) {
                Method getCurrent = stateMachine.getClass().getMethod("getCurrent");
                currentState = getCurrent.invoke(stateMachine);
            }
            if (currentState == state) {
                solPathExecuteSkippedCurrentState++;
                return;
            }
            Method execute = pathFindStateClass.getMethod("execute", IsoGameCharacter.class);
            solPathExecuteAttempts++;
            long attempt = solPathExecuteAttempts;
            boolean beforePathfind = getVariableBoolean("bPathfind");
            float beforeX = getX();
            float beforeY = getY();
            String beforeBasic = "attempt=" + attempt + ",pos=" + beforeX + "," + beforeY
                + ",bPathfind=" + beforePathfind + ",moving=" + isMoving()
                + ",owner=" + solPathActive;
            boolean sample = attempt <= 10L || attempt % 30L == 0L;
            String beforeFull = sample ? snapshotPathExecution() : null;
            execute.invoke(state, this);
            solPathExecuteSuccesses++;
            boolean afterPathfind = getVariableBoolean("bPathfind");
            float afterX = getX();
            float afterY = getY();
            boolean firstObservableDivergence = beforePathfind && !afterPathfind
                || beforeX != afterX || beforeY != afterY;
            if (sample || firstObservableDivergence) {
                solPathExecuteTraceBefore = (beforeFull == null ? beforeBasic : beforeFull);
                solPathExecuteTraceAfter = snapshotPathExecution();
            }
        } catch (ReflectiveOperationException failure) {
            throw new IllegalStateException("reflective PathFindState execute failed", failure);
        }
    }

    private String snapshotPathExecution() {
        Object behavior = optionalCall(this, "getPathFindBehavior2");
        Object stateMachine = optionalCall(this, "getStateMachine");
        Object currentState = optionalCall(stateMachine, "getCurrent");
        Object previousState = optionalCall(stateMachine, "getPrevious");
        Object path = optionalCall(this, "getPath2");
        return "pos=" + getX() + "," + getY() + "," + getZ()
            + ",owner=" + solPathActive
            + ",moving=" + isMoving()
            + ",playerMoving=" + isPlayerMoving()
            + ",bPathfind=" + getVariableBoolean("bPathfind")
            + ",bMoving=" + getVariableBoolean("bMoving")
            + ",state=" + optionalString(currentState, "getName")
            + ",previousState=" + optionalString(previousState, "getName")
            + ",pathAttached=" + (path != null)
            + ",shouldBeMoving=" + optionalString(behavior, "shouldBeMoving")
            + ",hasStartedMoving=" + optionalString(behavior, "hasStartedMoving")
            + ",movingUsingPathFind=" + optionalString(behavior, "isMovingUsingPathFind")
            + ",turningToObstacle=" + optionalString(behavior, "isTurningToObstacle")
            + ",cancelled=" + optionalString(behavior, "getIsCancelled")
            + ",target=" + optionalString(behavior, "getTargetX") + ","
            + optionalString(behavior, "getTargetY") + ","
            + optionalString(behavior, "getTargetZ")
            + ",pathLength=" + optionalString(behavior, "getPathLength")
            + ",pathNext=" + optionalField(behavior, "pathNextIsSet") + ","
            + optionalField(behavior, "pathNextX") + ","
            + optionalField(behavior, "pathNextY")
            + ",WalkSpeed=" + optionalString(this, "GetVariable", "WalkSpeed")
            + ",RunSpeed=" + optionalString(this, "GetVariable", "RunSpeed")
            + ",IdleSpeed=" + optionalString(this, "GetVariable", "IdleSpeed");
    }

    private static Object optionalCall(Object target, String methodName) {
        if (target == null) return null;
        try {
            return target.getClass().getMethod(methodName).invoke(target);
        } catch (ReflectiveOperationException | RuntimeException ignored) {
            return null;
        }
    }

    private static String optionalString(Object target, String methodName) {
        Object value = optionalCall(target, methodName);
        return value == null ? "n/a" : String.valueOf(value);
    }

    private static String optionalString(Object target, String methodName, String argument) {
        if (target == null) return "n/a";
        try {
            Object value = target.getClass().getMethod(methodName, String.class).invoke(target, argument);
            return value == null ? "n/a" : String.valueOf(value);
        } catch (ReflectiveOperationException | RuntimeException ignored) {
            return "n/a";
        }
    }

    private static String optionalField(Object target, String fieldName) {
        if (target == null) return "n/a";
        try {
            return String.valueOf(target.getClass().getField(fieldName).get(target));
        } catch (ReflectiveOperationException | RuntimeException ignored) {
            return "n/a";
        }
    }

    public String getSolPathExecuteTraceBefore() {
        return solPathExecuteTraceBefore;
    }

    public String getSolPathExecuteTraceAfter() {
        return solPathExecuteTraceAfter;
    }

    private void reconcileSolPathState() {
        if (!solPathActive) return;
        try {
            Method getBehavior = getClass().getMethod("getPathFindBehavior2");
            Object behavior = getBehavior.invoke(this);
            Method getVarBool = getClass().getMethod("getVariableBoolean", String.class);
            boolean requested = Boolean.TRUE.equals(getVarBool.invoke(this, "bPathfind"));
            boolean cancelled = false;
            if (behavior != null) {
                Method cancelledMethod = behavior.getClass().getMethod("getIsCancelled");
                Object value = cancelledMethod.invoke(behavior);
                cancelled = Boolean.TRUE.equals(value);
            }
            if (!requested || cancelled) {
                solPathActive = false;
                super.setMoving(false);
            }
        } catch (ReflectiveOperationException failure) {
            throw new IllegalStateException("path terminal reconciliation failed", failure);
        }
    }

    public long getSolUpdateCount() {
        return solUpdateCount;
    }

    public long getSolPathExecuteAttempts() {
        return solPathExecuteAttempts;
    }

    public long getSolPathExecuteSuccesses() {
        return solPathExecuteSuccesses;
    }

    public long getSolPathExecuteSkippedCurrentState() {
        return solPathExecuteSkippedCurrentState;
    }

    public SolIsoPlayerShell(IsoCell cell, SurvivorDesc descriptor, int x, int y, int z, boolean remote) {
        super(cell, descriptor, x, y, z, remote);
    }

    @Override
    public boolean isLocalPlayer() {
        return false;
    }

    @Override
    public void updateLOS() {
        // Non-local companions must never own or write a local-player LOS channel.
    }

    @Override
    public void setTargetAlpha(int playerIndex, float targetAlpha) {
        // Keep Sol's render opacity actor-local when the local player's LOS pass requests a fade.
        super.setTargetAlpha(playerIndex, 1.0f);
    }

    @Override
    public boolean isPlayerMoving() {
        return solPathActive;
    }

    @Override
    public void setMoving(boolean moving) {
        super.setMoving(moving);
    }

    public void stopSolPathOwnership() {
        solPathActive = false;
        try { setVariable("bPathfind", false); } catch (RuntimeException ignored) {}
 super.setMoving(false);
 }

    private void forceSolPathOwner() {
        solPathActive = true;
        setVariable("bPathfind", true);
        super.setMoving(false);
    }

    @Override
    public void pathToLocationF(float x, float y, float z) {
        super.pathToLocationF(x, y, z);
        forceSolPathOwner();
    }

    @Override
    public void pathToLocation(int x, int y, int z) {
        super.pathToLocation(x, y, z);
        forceSolPathOwner();
    }

    @Override
    public void pathToCharacter(IsoGameCharacter target) {
        super.pathToCharacter(target);
        if (target != null) forceSolPathOwner();
    }

    private void synchronizeSolLocomotion() {
        super.setMoving(solPathActive);
        try {
            Class<?> type = getClass();
            while (type != null) {
                try {
                    Method method = type.getDeclaredMethod("updateMovementRates");
 method.setAccessible(true);
 method.invoke(this);
 return;
 } catch (NoSuchMethodException missing) {
 type = type.getSuperclass();
 }
 }
 throw new NoSuchMethodException("updateMovementRates");
 } catch (ReflectiveOperationException failure) {
 throw new IllegalStateException("reflective updateMovementRates failed", failure);
 }
 }

    @Override
    public void update() {
        solUpdateCount++;
        IsoPlayer local = IsoPlayer.getInstance();
        try {
            synchronizeSolLocomotion();
            updateGenericCharacter();
            setAlphaAndTarget(1.0f);
            advanceSolPath();
            reconcileSolPathState();
        } finally {
            IsoPlayer.setInstance(local);
        }
    }
}




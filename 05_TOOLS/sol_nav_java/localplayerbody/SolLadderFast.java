package localplayerbody;

import me.zed_0xff.zombie_buddy.Exposer;
import me.zed_0xff.zombie_buddy.Patch;
import se.krka.kahlua.integration.annotations.LuaMethod;
import zombie.GameTime;
import zombie.ai.states.ClimbState;
import zombie.characters.IsoGameCharacter;
import zombie.characters.IsoPlayer;
import zombie.input.GameKeyboard;

/** Switch ladder_fast_slide: holding Run on a ladder moves him, and Sol with him, faster in both directions.
 *  The game's own state keeps climbing and is the one that ends the climb: this only adds height inside it, and stops short of the
 *  height the state aims for. A ladder climb never runs the game's fall check, so going faster cannot start a fall. */
@Exposer.LuaClass
public final class SolLadderFast {
    private static final float EXTRA = 2f, GAME_STEP = 0.07f / 10f, GAP = 0.02f;
    private static final long HOLD_MS = 250L;
    private static volatile boolean enabled;
    private static long heldSince;

    private SolLadderFast() {}

    @LuaMethod(name = "solLadderFastSet", global = true)
    public static void setEnabled(boolean on) { enabled = on; }

    private static boolean runHeld() {
        if (!GameKeyboard.isKeyDown("Run")) { heldSince = 0L; return false; }
        long now = System.currentTimeMillis();
        if (heldSince == 0L) heldSince = now;
        return now - heldSince >= HOLD_MS;
    }

    private static boolean wantsFast(IsoGameCharacter c) {
        IsoPlayer me = IsoPlayer.getInstance();
        boolean held = runHeld();
        if (c == me) return held;
        return held || (me != null && (me.isRunning() || me.isSprinting()));
    }

    /** The next height: past the game's step, never past where the game stops. */
    static float nextZ(float z, float target, float multiplier, boolean down) {
        float extra = EXTRA * GAME_STEP * multiplier;
        float next = down ? Math.max(z - extra, target + GAP) : Math.min(z + extra, target - GAP);
        return (down ? next < z : next > z) ? next : z;
    }

    /** Public: the patch body is copied into the game's class, so everything it calls must be reachable from there. */
    public static void step(IsoGameCharacter c, boolean down) {
        if (!enabled || c == null) return;
        if (!(down ? c.isClimbingDownLadder() : c.isClimbingLadder())) return;
        if (!c.getVariableBoolean("climbLadderLoop") || !wantsFast(c)) return;
        ClimbState.ClimbData data = c.getClimbData();
        if (data == null) return;
        float z = c.getZ(), next = nextZ(z, data.targetClimbHeight, GameTime.instance.getMultiplier(), down);
        if (next != z) c.setZ(next);
    }

    @Patch(className = "zombie.ai.states.ClimbDownState", methodName = "execute")
    public static final class Down {
        @Patch.OnExit
        public static void exit(@Patch.Argument(0) IsoGameCharacter c) { SolLadderFast.step(c, true); }
    }

    @Patch(className = "zombie.ai.states.ClimbState", methodName = "execute")
    public static final class Up {
        @Patch.OnExit
        public static void exit(@Patch.Argument(0) IsoGameCharacter c) { SolLadderFast.step(c, false); }
    }
}

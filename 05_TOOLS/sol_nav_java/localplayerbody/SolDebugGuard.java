package localplayerbody;

import me.zed_0xff.zombie_buddy.Exposer;
import me.zed_0xff.zombie_buddy.Patch;
import se.krka.kahlua.integration.annotations.LuaMethod;
import zombie.network.GameClient;

/** Switch debug_ctrl_a_guard. In debug mode, Ctrl+A makes the game send an "add animal" request to a multiplayer server.
 *  In single player there is no server connection, so that request throws and the game drops to the main menu
 *  (log: NullPointerException in GameClient.sendClientCommand from NetworkPlayerAI.checkDebugInput). Ctrl+A is also "select all" in a text box,
 *  such as Sol's chat. With no connection the check is skipped; in multiplayer it runs as before. */
@Exposer.LuaClass
public final class SolDebugGuard {
    private static volatile boolean enabled = true;

    private SolDebugGuard() {}

    @LuaMethod(name = "solDebugGuardSet", global = true)
    public static void setEnabled(boolean on) { enabled = on; }

    /** Public: the patch body is copied into the game's class. True means: skip the game's check this frame. */
    public static boolean skip() { return enabled && GameClient.connection == null; }

    @Patch(className = "zombie.characters.NetworkPlayerAI", methodName = "checkDebugInput")
    public static final class Guard {
        @Patch.OnEnter(skipOn = true)
        public static boolean enter() { return SolDebugGuard.skip(); }
    }
}

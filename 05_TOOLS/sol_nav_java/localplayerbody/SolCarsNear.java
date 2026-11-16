package localplayerbody;

import java.lang.reflect.Field;
import java.sql.Connection;

import gnu.trove.set.hash.TIntHashSet;
import me.zed_0xff.zombie_buddy.Exposer;
import se.krka.kahlua.integration.annotations.LuaMethod;
import zombie.vehicles.VehiclesDB2;

/**
 * Read only: which vehicles are saved within a radius of a point (switch far_car). The read runs on the world streamer thread, the thread
 * that owns the vehicles table, from the same hook as SolCarMove; Lua asks, then reads the answer a moment later. Never blocks the main thread.
 * States: idle | queued | ok | db_error:... ; the result is SolCarsNearCore's line format.
 */
@Exposer.LuaClass
public final class SolCarsNear {
    private static final class Request {
        final double x, y, r;
        Request(double x, double y, double r) { this.x = x; this.y = y; this.r = r; }
    }
    private static volatile Request pending;
    private static volatile String state = "idle";
    private static volatile String result = "";
    private static volatile double atX = Double.NaN, atY = Double.NaN;

    private SolCarsNear() {}

    @LuaMethod(name = "solCarsNearRequest", global = true)
    public static boolean request(double x, double y, double radius) {
        if (pending != null) return false;
        state = "queued";
        pending = new Request(x, y, radius);
        return true;
    }

    @LuaMethod(name = "solCarsNearState", global = true)
    public static String state() { return state; }

    /** "x,y|<cars>": the point the list is for, then the cars. */
    @LuaMethod(name = "solCarsNearResult", global = true)
    public static String result() { return Math.round(atX) + "," + Math.round(atY) + "|" + result; }

    private static Object field(Object owner, Class<?> type, String name) throws ReflectiveOperationException {
        Field f = type.getDeclaredField(name);
        f.setAccessible(true);
        return f.get(owner);
    }

    /** public: called from SolCarMove.onStreamer, which ZombieBuddy inlines into VehiclesDB2. */
    public static void onStreamer() {
        Request r = pending;
        if (r == null) return;
        pending = null;
        try {
            Object main = field(VehiclesDB2.instance, VehiclesDB2.class, "main");
            TIntHashSet loaded = (TIntHashSet) field(main, main.getClass(), "loadedIds");
            Object streamer = field(VehiclesDB2.instance, VehiclesDB2.class, "worldStreamer");
            Object store = field(streamer, streamer.getClass(), "store");
            Connection conn = (Connection) field(store, store.getClass(), "conn");
            if (conn == null) { state = "db_error:no_connection"; return; }
            result = SolCarsNearCore.join(SolCarsNearCore.scan(conn, r.x, r.y, r.r, id -> { synchronized (loaded) { return loaded.contains(id); } }));
            atX = r.x;
            atY = r.y;
            state = "ok";
        } catch (Throwable t) {
            state = "db_error:" + t;
        }
    }
}

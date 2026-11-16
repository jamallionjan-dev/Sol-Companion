package localplayerbody;

import java.lang.reflect.Field;
import java.sql.Connection;

import gnu.trove.set.hash.TIntHashSet;
import me.zed_0xff.zombie_buddy.Exposer;
import me.zed_0xff.zombie_buddy.Patch;
import se.krka.kahlua.integration.annotations.LuaMethod;
import zombie.iso.IsoCell;
import zombie.iso.IsoChunkMap;
import zombie.iso.IsoWorld;
import zombie.vehicles.VehiclesDB2;

/**
 * Her car, parked in a part of the world that is not loaded, is moved to just outside what is loaded around the player, by changing where
 * its row says it is. It runs on the world streamer thread, the thread that reads and writes those rows, between its own steps, so no chunk load is
 * halfway through a row. The chunk then loads it the normal way when the player gets close. Refused if the car or the target chunk is loaded.
 * States: idle | queued | ok | loaded | target_loaded | not_in_db | in_meta | blob_mismatch | spot_taken | db_error:...
 */
@Exposer.LuaClass
public final class SolCarMove {
    private static final class Request {
        final int id; final float x, y;
        Request(int id, float x, float y) { this.id = id; this.x = x; this.y = y; }
    }
    private static volatile Request pending;
    private static volatile String state = "idle";

    private SolCarMove() {}

    /** Lua gave up waiting: the car must not move after it has been told it did not. */
    @LuaMethod(name = "solCarMoveCancel", global = true)
    public static boolean cancel() {
        boolean had = pending != null;
        pending = null;
        if (had) state = "cancelled";
        return had;
    }

    @LuaMethod(name = "solCarMoveRequest", global = true)
    public static boolean request(double id, double x, double y) {
        if (pending != null) return false;
        // a chunk never seen fills itself with vehicles without looking at what the table already holds: this one is seen from now on
        VehiclesDB2.instance.setChunkSeen((int) Math.floor(x / SolCarMoveCore.CHUNK_TILES), (int) Math.floor(y / SolCarMoveCore.CHUNK_TILES));
        state = "queued";
        pending = new Request((int) id, (float) x, (float) y);
        return true;
    }

    @LuaMethod(name = "solCarMoveState", global = true)
    public static String state() { return state; }

    /** Chunks from the player's chunk to the edge of what is loaded. */
    @LuaMethod(name = "solCarMoveRing", global = true)
    public static double ring() { return IsoChunkMap.chunkGridWidth / 2; }

    private static Object field(Object owner, Class<?> type, String name) throws ReflectiveOperationException {
        Field f = type.getDeclaredField(name);
        f.setAccessible(true);
        return f.get(owner);
    }

    private static String perform(Request r) throws ReflectiveOperationException {
        Object main = field(VehiclesDB2.instance, VehiclesDB2.class, "main");
        TIntHashSet loaded = (TIntHashSet) field(main, main.getClass(), "loadedIds");
        if (loaded.contains(r.id)) return "loaded";
        IsoCell cell = IsoWorld.instance == null ? null : IsoWorld.instance.getCell();
        if (cell == null) return "db_error:no_world";
        int wx = (int) Math.floor(r.x / SolCarMoveCore.CHUNK_TILES), wy = (int) Math.floor(r.y / SolCarMoveCore.CHUNK_TILES);
        if (cell.getChunk(wx, wy) != null) return "target_loaded";
        Object streamer = field(VehiclesDB2.instance, VehiclesDB2.class, "worldStreamer");
        Object store = field(streamer, streamer.getClass(), "store");
        Connection conn = (Connection) field(store, store.getClass(), "conn");
        if (conn == null) return "db_error:no_connection";
        return SolCarMoveCore.move(conn, r.id, r.x, r.y);
    }

    /** public: ZombieBuddy inlines the hook into VehiclesDB2, so this is called from that class. */
    public static void onStreamer() {
        SolCarsNear.onStreamer();                                                // the read-only list of cars near a point (far_car)
        SolCarArrive.onStreamer();                                               // far_arrival: a row re-pointed into the loaded area
        Request r = pending;
        if (r == null) return;
        pending = null;
        try {
            state = perform(r);
        } catch (Throwable t) {
            state = "db_error:" + t;
        }
        System.out.println("[SolCarMove] " + r.id + " -> " + state);
    }

    @Patch(className = "zombie.vehicles.VehiclesDB2", methodName = "updateWorldStreamer")
    public static final class StreamerHook {
        @Patch.OnEnter
        public static void enter() { SolCarMove.onStreamer(); }
    }
}

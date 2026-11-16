package localplayerbody;

import java.lang.reflect.Field;
import java.nio.ByteBuffer;
import java.sql.Connection;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import gnu.trove.set.hash.TIntHashSet;
import me.zed_0xff.zombie_buddy.Exposer;
import se.krka.kahlua.integration.annotations.LuaMethod;
import zombie.iso.IsoCell;
import zombie.iso.IsoChunk;
import zombie.iso.IsoGridSquare;
import zombie.iso.IsoObject;
import zombie.iso.IsoWorld;
import zombie.vehicles.BaseVehicle;
import zombie.vehicles.VehiclesDB2;
import zombie.vehicles.VirtualVehicle;
import zombie.vehicles.VirtualVehicleManager;

/**
 * far_arrival: her car comes into the LOADED world at a road spot just out of his view, as one unit with her (Lua seats her the same tick).
 *   1 main thread  solCarArriveRequest(id, x, y): refused when the car is loaded already, or the spot's chunk is not loaded.
 *   2 streamer     (SolCarMove.onStreamer, the thread that owns the vehicles table) SolCarArriveCore.stage: the row moves in one transaction
 *                  and the patched blob comes back.
 *   3 main thread  solCarArriveMain(): the game's own sequence for a vehicle read from a row (VehiclesDB2$WorldStreamerThread.vehicleLoaded,
 *                  VehiclesDB2.java:675-695: new BaseVehicle(cell), setSquare, setCurrent, load(bb, worldVersion), sqlId, chunk,
 *                  chunk.vehicles.add) and then what IsoChunk.doLoadGridsquare does for it (IsoChunk.java:3935-3960: addToWorld, which
 *                  calls VehiclesDB2.setVehicleLoaded, createPhysics and PathfindNative.addVehicle).
 *   If the chunk unloaded between 2 and 3 (he moved): "deferred", the row is already there and the chunk's own load brings it later.
 *   The bytes go to BaseVehicle.load exactly as the game hands them over (SolCarArriveCore.gameReadBuffer: SQLStore.loadChunk reads the
 *   serialise flag and the class id, two bytes, before vehicleLoaded calls load; 20:44:59 live run: load from byte 0 threw
 *   "newLimit > capacity: (19781 > 6264)").
 *   If bringing it in fails (any throwable after the stage): "load_failed", and BEFORE the answer goes back to Lua the streamer puts the row
 *   back where and what it was (SolCarArriveCore.rollback, one transaction, only if the row is still what the stage wrote and the game has
 *   not loaded the vehicle itself); the main thread waits for that up to ROLLBACK_WAIT_MS, then answers "load_failed:<rollback result>".
 *   far_meta: a vehicle kept "in meta" (left with its engine running, alarm or siren on; the Bradley in his save) has no live object in a
 *   chunk but a VirtualVehicle in VirtualVehicleManager. Step 1 notes (main thread) whether that VirtualVehicle is there; step 2 stages
 *   such a row only then; step 3 brings it in only if the VirtualVehicle is still there, so that addToWorld's own
 *   VirtualVehicleManager.removeFromMeta hands the live parts over and drops the kept copy (as when the game loads its chunk), and then
 *   queues the game's own save of the live vehicle (VehiclesDB2.updateVehicle), which the streamer runs after any save the kept copy
 *   queued before: the one row ends at the spot with the live state. If the VirtualVehicle went away in between: "meta_changed", nothing
 *   is created and the game's own queued save decides where the row ends.
 * States: idle | queued | staged | arrived | deferred | loaded | target_unloaded | load_failed | not_in_db | in_meta | meta_changed | meta_deferred |
 *         blob_mismatch | spot_taken | busy | db_error:...
 */
@Exposer.LuaClass
public final class SolCarArrive {
    private static final class Request {
        final int id; final float x, y; final boolean virtual;
        Request(int id, float x, float y, boolean virtual) { this.id = id; this.x = x; this.y = y; this.virtual = virtual; }
    }
    private static volatile Request pending;
    private static volatile Request stagedFor;
    private static volatile SolCarArriveCore.Staged staged;
    private static volatile String state = "idle";
    private static final long ROLLBACK_WAIT_MS = 2000;
    private static final class Rollback {
        final int id; final SolCarArriveCore.Staged s; final CountDownLatch done = new CountDownLatch(1); volatile String result = "rollback_pending";
        Rollback(int id, SolCarArriveCore.Staged s) { this.id = id; this.s = s; }
    }
    private static volatile Rollback rollback;

    private SolCarArrive() {}

    private static Object field(Object owner, Class<?> type, String name) throws ReflectiveOperationException {
        Field f = type.getDeclaredField(name);
        f.setAccessible(true);
        return f.get(owner);
    }
    private static TIntHashSet loadedIds() throws ReflectiveOperationException {
        Object main = field(VehiclesDB2.instance, VehiclesDB2.class, "main");
        return (TIntHashSet) field(main, main.getClass(), "loadedIds");
    }
    /** far_meta, main thread only: is this vehicle kept in meta right now (a VirtualVehicle with its sqlId)? */
    @SuppressWarnings("unchecked")
    static boolean keptInMeta(int id) throws ReflectiveOperationException {
        VirtualVehicleManager m = VirtualVehicleManager.getInstance();
        List<VirtualVehicle> list = (List<VirtualVehicle>) field(m, VirtualVehicleManager.class, "vehicles");
        for (int i = 0; i < list.size(); i++) if (list.get(i).getSqlId() == id) return true;
        return false;
    }
    private static IsoChunk chunkAt(float x, float y) {
        IsoCell cell = IsoWorld.instance == null ? null : IsoWorld.instance.getCell();
        if (cell == null) return null;
        return cell.getChunk((int) Math.floor(x / SolCarMoveCore.CHUNK_TILES), (int) Math.floor(y / SolCarMoveCore.CHUNK_TILES));
    }

    @LuaMethod(name = "solCarArriveRequest", global = true)
    public static boolean request(double id, double x, double y) {
        if (pending != null || staged != null || rollback != null) { state = "busy"; return false; }
        boolean virtual;
        try {
            if (loadedIds().contains((int) id)) { state = "loaded"; return false; }
            virtual = keptInMeta((int) id);                                     // far_meta
        } catch (ReflectiveOperationException e) { state = "db_error:" + e; return false; }
        if (chunkAt((float) x, (float) y) == null) { state = "target_unloaded"; return false; }
        state = "queued";
        pending = new Request((int) id, (float) x, (float) y, virtual);
        return true;
    }

    @LuaMethod(name = "solCarArriveState", global = true)
    public static String state() { return state; }

    @LuaMethod(name = "solCarArriveCancel", global = true)
    public static boolean cancel() {
        boolean had = pending != null;                                          // only before the streamer took it: a staged row is never undone
        pending = null;
        if (had) state = "cancelled";
        return had;
    }

    /** Called from SolCarMove.onStreamer, on the world streamer thread. */
    static void onStreamer() {
        Rollback rb = rollback;
        if (rb != null) {
            try {
                if (loadedIds().contains(rb.id)) rb.result = "rollback_skipped:loaded";          // the game has it live: its own saves decide
                else {
                    Object streamer = field(VehiclesDB2.instance, VehiclesDB2.class, "worldStreamer");
                    Object store = field(streamer, streamer.getClass(), "store");
                    Connection conn = (Connection) field(store, store.getClass(), "conn");
                    rb.result = conn == null ? "db_error:no_connection" : SolCarArriveCore.rollback(conn, rb.id, rb.s);
                }
            } catch (Throwable t) {
                rb.result = "db_error:" + t;
            }
            if ("rolled_back".equals(rb.result)) System.out.println("[SolCarArrive] " + rb.id + " rolled back to " + rb.s.fromX + "," + rb.s.fromY);
            else System.out.println("[SolCarArrive] " + rb.id + " not rolled back (" + rb.result + "), its row stays at " + rb.s.toX + "," + rb.s.toY);
            rollback = null;
            rb.done.countDown();
        }
        Request r = pending;
        if (r == null) return;
        pending = null;
        try {
            if (loadedIds().contains(r.id)) { state = "loaded"; return; }
            if (chunkAt(r.x, r.y) == null) { state = "target_unloaded"; return; }   // he moved: nothing written
            Object streamer = field(VehiclesDB2.instance, VehiclesDB2.class, "worldStreamer");
            Object store = field(streamer, streamer.getClass(), "store");
            Connection conn = (Connection) field(store, store.getClass(), "conn");
            if (conn == null) { state = "db_error:no_connection"; return; }
            SolCarArriveCore.Staged s = SolCarArriveCore.stage(conn, r.id, r.x, r.y, r.virtual);     // far_meta: a kept row only with its VirtualVehicle
            if (!"ok".equals(s.state)) { state = s.state; return; }
            stagedFor = r;
            staged = s;
            state = "staged";
        } catch (Throwable t) {
            state = "db_error:" + t;
        }
        System.out.println("[SolCarArrive] " + r.id + (r.virtual ? " (kept in meta)" : "") + " -> " + state);
    }

    /** Lua calls this every tick while the state is "staged"; it runs on the main thread. */
    @LuaMethod(name = "solCarArriveMain", global = true)
    public static String main() {
        SolCarArriveCore.Staged s = staged;
        Request r = stagedFor;
        if (s == null || r == null) return state;
        staged = null;
        stagedFor = null;
        BaseVehicle attached = null;
        IsoChunk attachedTo = null;
        try {
            boolean loaded = loadedIds().contains(r.id);
            boolean virtualNow = s.inMeta && !loaded && keptInMeta(r.id);
            IsoChunk ch = chunkAt(r.x, r.y);
            attachedTo = ch;
            IsoCell cell = IsoWorld.instance.getCell();
            IsoGridSquare sq = ch == null ? null : cell.getGridSquare((int) Math.floor(r.x), (int) Math.floor(r.y), 0);
            String choice = SolCarArriveCore.mainChoice(loaded, s.inMeta, virtualNow, ch != null && sq != null);
            if (!"spawn".equals(choice)) {                                       // loaded: the game brought it in itself; deferred: the row is
                state = choice;                                                  // there and the chunk's own load brings it; meta_changed: see above
                if (s.inMeta) System.out.println("[SolCarArrive] " + r.id + " (kept in meta) -> " + state);
                return state;
            }
            ByteBuffer bb = SolCarArriveCore.gameReadBuffer(s.data, IsoObject.getFactoryVehicle().getClassID());   // position 2, as the game
            if (bb == null) throw new IllegalStateException("not a vehicle row the game would read");
            BaseVehicle v = new BaseVehicle(cell);
            v.setSquare(sq);
            v.setCurrent(sq);
            v.load(bb, s.worldVersion);
            v.sqlId = r.id;
            v.chunk = ch;
            attached = v;
            ch.vehicles.add(v);
            v.addToWorld();                                                      // a kept one: removeFromMeta hands its live parts over
            attached = null;
            if (s.inMeta) {
                boolean stillKept = keptInMeta(r.id);
                if (stillKept) VirtualVehicleManager.getInstance().removeFromMeta(v);    // the same call addToWorld makes in single player
                VehiclesDB2.instance.updateVehicle(v);                           // the game's own save of the live vehicle, after any queued one
                System.out.println("[SolCarArrive] " + r.id + " (kept in meta) taken over from the kept copy: " + (stillKept ? "only by the second call" : "yes") + ", saved at the spot");
            }
            state = "arrived";
        } catch (Throwable t) {
            System.out.println("[SolCarArrive] " + r.id + " load failed at " + r.x + "," + r.y + ": " + t);
            t.printStackTrace(System.out);
            if (attached != null) {                                              // half in the world: take it out the game's way first
                try { attached.removeFromWorld(); } catch (Throwable u) { System.out.println("[SolCarArrive] " + r.id + " removeFromWorld: " + u); }
                try { if (attachedTo != null) attachedTo.vehicles.remove(attached); } catch (Throwable u) { }
            }
            Rollback rb = new Rollback(r.id, s);
            rollback = rb;                                                       // the streamer owns the connection: it runs the rollback
            boolean done = false;
            try { done = rb.done.await(ROLLBACK_WAIT_MS, TimeUnit.MILLISECONDS); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            state = "load_failed:" + (done ? rb.result : "rollback_pending");
            return state;
        }
        System.out.println("[SolCarArrive] " + r.id + " -> arrived at " + r.x + "," + r.y);
        return state;
    }
}

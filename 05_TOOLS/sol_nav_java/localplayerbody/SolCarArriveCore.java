package localplayerbody;

import java.nio.ByteBuffer;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

/**
 * far_arrival, the database half: one vehicle row is re-pointed at a spot inside the loaded area, in ONE transaction (same id, same data
 * apart from its position: x, y, wx, wy and the x/y floats in the blob), and the patched blob and its worldversion are handed back so the
 * main thread can bring the vehicle into the live world from exactly the bytes the table now holds.
 * Crash safety: SQLite commits the row update atomically (the game opens the store with PRAGMA JOURNAL_MODE=TRUNCATE). A crash before the
 * commit leaves the row where it was; a crash after it leaves it at the new spot, where the game's own chunk load
 * (VehiclesDB2$WorldStreamerThread.vehicleLoaded, VehiclesDB2.java:675-695) brings it in. There is only ever one row, so never a copy.
 * Answers: ok | not_in_db | in_meta | blob_mismatch | spot_taken | db_error:<message>.
 * far_meta: a row kept "in meta" (inMeta = 1: the game keeps that vehicle alive in VirtualVehicleManager because it was left with its
 * engine running, its alarm or its siren on; VehicleBuffer.set writes inMeta = BaseVehicle.shouldUpdateInMeta()) is staged only when the
 * main thread saw its VirtualVehicle (allowMeta). Its inMeta column is left as the game wrote it; only the position moves, exactly as for
 * any other row. The main thread then brings it in with the game's own sequence, whose addToWorld calls VirtualVehicleManager.removeFromMeta:
 * the live parts (fuel, battery, conditions) of the kept copy go into the vehicle and the kept copy is dropped, as when its chunk loads.
 */
public final class SolCarArriveCore {
    public static final class Staged {
        public String state = "db_error:unset";
        public byte[] data;
        public int worldVersion;
        public float fromX, fromY;
        public boolean inMeta;                 // far_meta: the row was kept in meta when it was staged
        public float toX, toY;                 // where the stage put it (the rollback's guard)
        public int fromWx, fromWy;             // the row's own wx, wy before the stage
        public byte[] fromData;                // the row's own bytes before the stage (the rollback writes them back)
    }

    /**
     * The game's read of a row (VehiclesDB2$SQLStore.loadChunk, javap 42.22.2, line 223-232): data comes in through
     * VehicleBuffer.setBytes(InputStream) (a buffer at position 0, limit = the blob's length), then TWO bytes are read before the vehicle
     * sees it: serialise = bb.get() != 0, classID = bb.get(); the row is skipped unless classID == IsoObject.getFactoryVehicle().getClassID()
     * (33, "Vehicle", IsoObject.initFactory) and serialise; only then vehicleLoaded calls BaseVehicle.load(bb, worldVersion) from position 2.
     * IsoMovingObject.load then reads two floats and x (byte 10), y (14), z (18): BLOB_X / BLOB_Y are offsets in that same frame.
     */
    public static final int VEHICLE_CLASS_ID = 33, HEADER_BYTES = 2;
    public static ByteBuffer gameReadBuffer(byte[] data, int vehicleClassId) {
        if (data == null || data.length < SolCarMoveCore.BLOB_Y + 4) return null;
        ByteBuffer bb = ByteBuffer.allocate(Math.max(32768, data.length));     // VehicleBuffer: 32768 at first, grown as needed
        bb.put(data);
        bb.flip();                                                               // ByteBufferOutputStream.flip: position 0, limit = length
        boolean serialise = bb.get() != 0;
        byte classId = bb.get();
        if (!serialise || classId != (byte) vehicleClassId) return null;         // the game would skip this row
        return bb;
    }

    private SolCarArriveCore() {}

    public static Staged stage(Connection c, int id, float toX, float toY) { return stage(c, id, toX, toY, false); }

    /** allowMeta: the main thread saw this vehicle's VirtualVehicle (far_meta); without it a row kept in meta is refused (in_meta). */
    public static Staged stage(Connection c, int id, float toX, float toY, boolean allowMeta) {
        Staged s = new Staged();
        boolean auto = true;
        try {
            auto = c.getAutoCommit();
            c.setAutoCommit(false);
            s.state = stageInTransaction(c, id, toX, toY, s, allowMeta);
            if ("ok".equals(s.state)) c.commit(); else { c.rollback(); s.data = null; }
        } catch (SQLException e) {
            try { c.rollback(); } catch (SQLException ignored) { }
            s.state = "db_error:" + e.getMessage();
            s.data = null;
        } finally {
            try { c.setAutoCommit(auto); } catch (SQLException ignored) { }
        }
        return s;
    }

    static String stageInTransaction(Connection c, int id, float toX, float toY, Staged s) throws SQLException {
        return stageInTransaction(c, id, toX, toY, s, false);
    }

    static String stageInTransaction(Connection c, int id, float toX, float toY, Staged s, boolean allowMeta) throws SQLException {
        float x, y;
        byte[] data;
        int wv;
        boolean meta;
        int wx0, wy0;
        try (PreparedStatement q = c.prepareStatement("SELECT x, y, inMeta, data, worldversion, wx, wy FROM vehicles WHERE id = ?")) {
            q.setInt(1, id);
            try (ResultSet r = q.executeQuery()) {
                if (!r.next()) return "not_in_db";
                meta = r.getBoolean(3);
                if (meta && !allowMeta) return "in_meta";
                x = r.getFloat(1);
                y = r.getFloat(2);
                data = r.getBytes(4);
                wv = r.getInt(5);
                wx0 = r.getInt(6);
                wy0 = r.getInt(7);
            }
        }
        if (gameReadBuffer(data, VEHICLE_CLASS_ID) == null) return "blob_mismatch";    // not a row the game's chunk load would read
        byte[] original = data.clone();
        ByteBuffer b = ByteBuffer.wrap(data);                                    // big-endian, as BaseVehicle.save writes it
        if (Math.abs(b.getFloat(SolCarMoveCore.BLOB_X) - x) > SolCarMoveCore.MATCH || Math.abs(b.getFloat(SolCarMoveCore.BLOB_Y) - y) > SolCarMoveCore.MATCH) return "blob_mismatch";
        int toWx = (int) Math.floor(toX / SolCarMoveCore.CHUNK_TILES), toWy = (int) Math.floor(toY / SolCarMoveCore.CHUNK_TILES);
        try (PreparedStatement near = c.prepareStatement("SELECT x, y FROM vehicles WHERE id <> ? AND wx BETWEEN ? AND ? AND wy BETWEEN ? AND ?")) {
            near.setInt(1, id);
            near.setInt(2, toWx - 2);
            near.setInt(3, toWx + 2);
            near.setInt(4, toWy - 2);
            near.setInt(5, toWy + 2);
            try (ResultSet r = near.executeQuery()) {
                while (r.next()) if (Math.hypot(r.getFloat(1) - toX, r.getFloat(2) - toY) < SolCarMoveCore.CLEARANCE) return "spot_taken";
            }
        }
        b.putFloat(SolCarMoveCore.BLOB_X, toX);
        b.putFloat(SolCarMoveCore.BLOB_Y, toY);
        try (PreparedStatement u = c.prepareStatement("UPDATE vehicles SET wx = ?, wy = ?, x = ?, y = ?, data = ? WHERE id = ? AND x = ? AND y = ?")) {
            u.setInt(1, toWx);
            u.setInt(2, toWy);
            u.setFloat(3, toX);
            u.setFloat(4, toY);
            u.setBytes(5, data);
            u.setInt(6, id);
            u.setFloat(7, x);
            u.setFloat(8, y);
            if (u.executeUpdate() != 1) return "not_in_db";
        }
        s.data = data;
        s.worldVersion = wv;
        s.fromX = x;
        s.fromY = y;
        s.inMeta = meta;
        s.toX = toX;
        s.toY = toY;
        s.fromWx = wx0;
        s.fromWy = wy0;
        s.fromData = original;
        return "ok";
    }

    /**
     * The live load failed after the stage: the row goes back to exactly where and what it was (wx, wy, x, y and its own bytes), in ONE
     * transaction, and only if it is still exactly what the stage wrote (same place, same bytes): if the game rewrote it since (a kept copy's
     * save, a live vehicle's save) the game's row stands. Either way it is one UPDATE of one id: never a second row.
     * Answers: rolled_back | rollback_skipped | db_error:<message>.
     */
    public static String rollback(Connection c, int id, Staged s) {
        if (s == null || s.fromData == null || s.data == null) return "rollback_skipped";
        boolean auto = true;
        try {
            auto = c.getAutoCommit();
            c.setAutoCommit(false);
            int n = rollbackInTransaction(c, id, s);
            if (n == 1) { c.commit(); return "rolled_back"; }
            c.rollback();
            return "rollback_skipped";
        } catch (SQLException e) {
            try { c.rollback(); } catch (SQLException ignored) { }
            return "db_error:" + e.getMessage();
        } finally {
            try { c.setAutoCommit(auto); } catch (SQLException ignored) { }
        }
    }

    static int rollbackInTransaction(Connection c, int id, Staged s) throws SQLException {
        try (PreparedStatement u = c.prepareStatement("UPDATE vehicles SET wx = ?, wy = ?, x = ?, y = ?, data = ? WHERE id = ? AND x = ? AND y = ? AND data = ?")) {
            u.setInt(1, s.fromWx);
            u.setInt(2, s.fromWy);
            u.setFloat(3, s.fromX);
            u.setFloat(4, s.fromY);
            u.setBytes(5, s.fromData);
            u.setInt(6, id);
            u.setFloat(7, s.toX);
            u.setFloat(8, s.toY);
            u.setBytes(9, s.data);
            return u.executeUpdate();
        }
    }

    /**
     * far_meta, the main thread's choice once the row is staged (pure, so it is tested offline):
     *   loaded       the game brought it in itself: nothing to do
     *   meta_changed the row was kept in meta but its VirtualVehicle is gone now: the game stopped keeping it (engine off, alarm over:
     *                VirtualVehicle.stopUpdatingInMeta, which queues its own save of the row at its old place) or brought it in elsewhere.
     *                Nothing is created; the game's own queued save decides where the one row ends. She walks.
     *   deferred     the spot's chunk or square is not loaded (he moved): the row is there; the chunk's own load brings it
     *   meta_deferred the same for a row kept in meta: the kept copy still holds its old place and may write it back at the next save,
     *                so where the one row ends is the game's; she walks instead of waiting for it
     *   spawn        the game's own row-to-world sequence
     */
    public static String mainChoice(boolean loaded, boolean stagedInMeta, boolean virtualNow, boolean squareLoaded) {
        if (loaded) return "loaded";
        if (stagedInMeta && !virtualNow) return "meta_changed";
        if (!squareLoaded) return stagedInMeta ? "meta_deferred" : "deferred";
        return "spawn";
    }
}

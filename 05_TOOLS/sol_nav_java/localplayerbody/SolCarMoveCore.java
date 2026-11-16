package localplayerbody;

import java.nio.ByteBuffer;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

/**
 * Moves one vehicle's row in the game's vehicles table: one transaction, same id, same data apart from its position, so there is never a second
 * copy and nothing else about the vehicle changes. The caller makes sure the vehicle is not loaded and the target chunk is not loaded.
 * Answers: ok | not_in_db | in_meta | blob_mismatch | spot_taken | db_error:<message>.
 */
public final class SolCarMoveCore {
    static final int CHUNK_TILES = 8, BLOB_X = 10, BLOB_Y = 14;
    static final float MATCH = 0.01f;
    static final double CLEARANCE = 8.0;

    private SolCarMoveCore() {}

    public static String move(Connection c, int id, float toX, float toY) {
        boolean auto = true;
        try {
            auto = c.getAutoCommit();
            c.setAutoCommit(false);
            String result = moveInTransaction(c, id, toX, toY);
            if ("ok".equals(result)) c.commit(); else c.rollback();
            return result;
        } catch (SQLException e) {
            try { c.rollback(); } catch (SQLException ignored) { }
            return "db_error:" + e.getMessage();
        } finally {
            try { c.setAutoCommit(auto); } catch (SQLException ignored) { }
        }
    }

    private static String moveInTransaction(Connection c, int id, float toX, float toY) throws SQLException {
        float x, y;
        byte[] data;
        try (PreparedStatement q = c.prepareStatement("SELECT x, y, inMeta, data FROM vehicles WHERE id = ?")) {
            q.setInt(1, id);
            try (ResultSet r = q.executeQuery()) {
                if (!r.next()) return "not_in_db";
                if (r.getBoolean(3)) return "in_meta";
                x = r.getFloat(1);
                y = r.getFloat(2);
                data = r.getBytes(4);
            }
        }
        if (data == null || data.length < BLOB_Y + 4) return "blob_mismatch";
        ByteBuffer b = ByteBuffer.wrap(data);                                    // big-endian, as BaseVehicle.save writes it
        if (Math.abs(b.getFloat(BLOB_X) - x) > MATCH || Math.abs(b.getFloat(BLOB_Y) - y) > MATCH) return "blob_mismatch";
        int toWx = (int) Math.floor(toX / CHUNK_TILES), toWy = (int) Math.floor(toY / CHUNK_TILES);
        try (PreparedStatement near = c.prepareStatement("SELECT x, y FROM vehicles WHERE id <> ? AND wx BETWEEN ? AND ? AND wy BETWEEN ? AND ?")) {
            near.setInt(1, id);
            near.setInt(2, toWx - 2);
            near.setInt(3, toWx + 2);
            near.setInt(4, toWy - 2);
            near.setInt(5, toWy + 2);
            try (ResultSet r = near.executeQuery()) {
                while (r.next()) if (Math.hypot(r.getFloat(1) - toX, r.getFloat(2) - toY) < CLEARANCE) return "spot_taken";
            }
        }
        b.putFloat(BLOB_X, toX);
        b.putFloat(BLOB_Y, toY);
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
        return "ok";
    }
}

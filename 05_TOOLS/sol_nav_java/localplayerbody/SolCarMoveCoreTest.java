package localplayerbody;

import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Against copies of real vehicles.db files. Usage: SolCarMoveCoreTest <vehicles.db copy>... */
public final class SolCarMoveCoreTest {
    private static int failed;
    private static void ck(String name, boolean ok, Object detail) {
        System.out.println((ok ? "PASS " : "FAIL ") + name + (ok ? "" : " : " + detail));
        if (!ok) failed++;
    }
    private static final class Row { int id, wx, wy; float x, y; byte[] data; }
    private static List<Row> rows(Connection c) throws Exception {
        List<Row> out = new ArrayList<>();
        try (Statement s = c.createStatement(); ResultSet r = s.executeQuery("SELECT id, wx, wy, x, y, data FROM vehicles ORDER BY id")) {
            while (r.next()) { Row a = new Row(); a.id = r.getInt(1); a.wx = r.getInt(2); a.wy = r.getInt(3); a.x = r.getFloat(4); a.y = r.getFloat(5); a.data = r.getBytes(6); out.add(a); }
        }
        return out;
    }
    private static Row byId(List<Row> l, int id) { for (Row r : l) if (r.id == id) return r; return null; }

    public static void main(String[] args) throws Exception {
        Class.forName("org.sqlite.JDBC");
        for (String source : args) {
            Path tmp = Files.createTempFile("sol_car_move", ".db");
            Files.copy(Path.of(source), tmp, StandardCopyOption.REPLACE_EXISTING);
            try (Connection c = DriverManager.getConnection("jdbc:sqlite:" + tmp)) {
                List<Row> before = rows(c);
                ck("real rows to work on", before.size() >= 2, before.size());
                Row car = before.get(0);
                float toX = 20000.5f, toY = 20000.25f;
                ck("moved", "ok".equals(SolCarMoveCore.move(c, car.id, toX, toY)), "");
                List<Row> after = rows(c);
                Row moved = byId(after, car.id);
                ck("no second copy, none lost", after.size() == before.size(), after.size());
                ck("same id, new columns", moved != null && moved.x == toX && moved.y == toY, moved == null ? null : moved.x);
                ck("the chunk it will be loaded with", moved != null && moved.wx == 2500 && moved.wy == 2500, moved == null ? null : moved.wx);
                ByteBuffer b = ByteBuffer.wrap(moved.data);
                ck("the blob agrees", b.getFloat(10) == toX && b.getFloat(14) == toY, b.getFloat(10));
                byte[] expect = car.data.clone();
                ByteBuffer.wrap(expect).putFloat(10, toX).putFloat(14, toY);
                ck("nothing else in the vehicle changed", Arrays.equals(expect, moved.data), "");
                boolean othersSame = true;
                for (Row r : before) if (r.id != car.id) { Row a = byId(after, r.id); othersSame &= a != null && a.x == r.x && a.y == r.y && Arrays.equals(a.data, r.data); }
                ck("no other vehicle touched", othersSame, "");
                ck("the old chunk no longer has it", noneAt(c, car.id, car.wx, car.wy), "");

                Row second = before.get(1);
                ck("a spot next to another vehicle is refused", "spot_taken".equals(SolCarMoveCore.move(c, second.id, toX + 3, toY)), "");
                ck("refused: nothing moved", byId(rows(c), second.id).x == second.x, "");
                ck("the same vehicle can move again", "ok".equals(SolCarMoveCore.move(c, car.id, toX + 3, toY)), "");
                ck("unknown id", "not_in_db".equals(SolCarMoveCore.move(c, 99999999, 1, 1)), "");
                try (Statement s = c.createStatement()) { s.executeUpdate("UPDATE vehicles SET inMeta = 1 WHERE id = " + second.id); }
                ck("a vehicle kept in meta is refused", "in_meta".equals(SolCarMoveCore.move(c, second.id, 15000, 15000)), "");
                try (Statement s = c.createStatement()) { s.executeUpdate("UPDATE vehicles SET inMeta = 0, x = x + 40 WHERE id = " + second.id); }
                ck("column and blob disagree (a game update): refused", "blob_mismatch".equals(SolCarMoveCore.move(c, second.id, 15000, 15000)), "");
                ck("autocommit is left as it was", c.getAutoCommit(), "");
            } finally {
                Files.deleteIfExists(tmp);
            }
        }
        System.out.println("SUMMARY " + (failed == 0 ? "ALL PASS" : "FAILED " + failed));
        System.exit(failed == 0 ? 0 : 1);
    }
    private static boolean noneAt(Connection c, int id, int wx, int wy) throws Exception {
        try (Statement s = c.createStatement(); ResultSet r = s.executeQuery("SELECT count(*) FROM vehicles WHERE id = " + id + " AND wx = " + wx + " AND wy = " + wy)) { return r.next() && r.getInt(1) == 0; }
    }
}

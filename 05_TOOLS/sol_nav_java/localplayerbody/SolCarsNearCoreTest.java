package localplayerbody;

import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Offline: the nearby-car list (radius, every direction, ties, eligibility, read only) and the car move's failure paths (nothing lost,
 * nothing doubled, rolled back). Rows come from a COPY of a real vehicles.db. Usage: SolCarsNearCoreTest <vehicles.db copy>
 * Prints one DUMP line per real row so the decode can be compared with 05_TOOLS/sol_kahlua/decode_vehicles.py.
 */
public final class SolCarsNearCoreTest {
    private static int failed;
    private static void ck(String name, boolean ok, Object detail) {
        System.out.println((ok ? "PASS " : "FAIL ") + name + (ok ? "" : " : " + detail));
        if (!ok) failed++;
    }
    private static byte[] sha(Path p) throws Exception { return MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(p)); }

    private static final String SCHEMA = "CREATE TABLE vehicles (id INTEGER PRIMARY KEY NOT NULL,wx INTEGER,wy INTEGER,x FLOAT,y FLOAT,inMeta BOOLEAN NULL DEFAULT FALSE,worldversion INTEGER,data BLOB)";

    private static void put(Connection c, int id, float x, float y, byte[] template) throws Exception {
        byte[] data = template.clone();
        ByteBuffer.wrap(data).putFloat(10, x).putFloat(14, y);
        try (PreparedStatement p = c.prepareStatement("INSERT INTO vehicles(id,wx,wy,x,y,inMeta,worldversion,data) VALUES(?,?,?,?,?,0,251,?)")) {
            p.setInt(1, id); p.setInt(2, (int) Math.floor(x / 8)); p.setInt(3, (int) Math.floor(y / 8)); p.setFloat(4, x); p.setFloat(5, y); p.setBytes(6, data);
            p.executeUpdate();
        }
    }
    private static List<Integer> ids(List<SolCarsNearCore.Car> l) { List<Integer> o = new ArrayList<>(); for (SolCarsNearCore.Car c : l) o.add(c.id); return o; }
    private static int count(Connection c) throws Exception { try (Statement s = c.createStatement(); ResultSet r = s.executeQuery("SELECT count(*) FROM vehicles")) { r.next(); return r.getInt(1); } }
    private static Set<Integer> allIds(Connection c) throws Exception {
        Set<Integer> o = new HashSet<>();
        try (Statement s = c.createStatement(); ResultSet r = s.executeQuery("SELECT id FROM vehicles")) { while (r.next()) o.add(r.getInt(1)); }
        return o;
    }
    private static float[] xy(Connection c, int id) throws Exception {
        try (Statement s = c.createStatement(); ResultSet r = s.executeQuery("SELECT x, y, data FROM vehicles WHERE id = " + id)) {
            if (!r.next()) return null;
            return new float[] { r.getFloat(1), r.getFloat(2), Arrays.hashCode(r.getBytes(3)) };
        }
    }

    public static void main(String[] args) throws Exception {
        Class.forName("org.sqlite.JDBC");
        Path source = Path.of(args[0]);
        byte[] before = sha(source);
        List<byte[]> blobs = new ArrayList<>();
        java.util.Map<Integer, byte[]> real = new java.util.TreeMap<>();
        int walked = 0;
        byte[] good = null;
        // ---- the real rows, read only
        try (Connection c = DriverManager.getConnection("jdbc:sqlite:file:" + source.toString().replace('\\', '/') + "?mode=ro")) {
            int n = count(c), scripts = 0, fuels = 0, engines = 0, doors = 0, tires = 0;
            try (Statement s = c.createStatement(); ResultSet r = s.executeQuery("SELECT id, x, y, inMeta, data FROM vehicles ORDER BY id")) {
                while (r.next()) {
                    SolCarsNearCore.Car car = new SolCarsNearCore.Car();
                    car.id = r.getInt(1); car.x = r.getFloat(2); car.y = r.getFloat(3); car.inMeta = r.getBoolean(4);
                    byte[] d = r.getBytes(5);
                    blobs.add(d);
                    real.put(car.id, d);
                    SolCarsNearCore.decode(d, car);
                    car.verdict = SolCarsNearCore.verdict(car);
                    System.out.println("DUMP " + car.line() + " tires=" + car.tires);
                    if (car.tires >= 0) tires++;
                    if (car.script != null) scripts++;
                    if (!Float.isNaN(car.fuel)) fuels++;
                    if (car.engine >= 0) engines++;
                    if (car.locked >= 0) doors++;
                    if (car.ignition >= 0 && car.hot >= 0 && car.keyInCar >= 0) walked++;
                    if (good == null && "ok".equals(car.verdict)) good = d;
                }
            }
            System.out.println("STATS rows=" + n + " script=" + scripts + " fuel=" + fuels + " engine=" + engines + " door=" + doors + " tires=" + tires);
            ck("every real row's type is read", scripts == n, scripts + "/" + n);
            ck("most real rows' fuel is read", fuels * 10 >= n * 7, fuels + "/" + n);
            System.out.println("STATS walked to the ignition key: " + walked + "/" + n);
            ck("every real row with parts is walked to its ignition key", walked >= n - 2, walked + "/" + n);
            List<SolCarsNearCore.Car> near = SolCarsNearCore.scan(c, 7282.5, 8343.0, 25, id -> false);
            ck("a real query near the first car finds it first", !near.isEmpty() && near.get(0).dist < 0.01, SolCarsNearCore.join(near));
            boolean sorted = true;
            for (int i = 1; i < near.size(); i++) sorted &= near.get(i - 1).dist <= near.get(i).dist;
            ck("real query: nearest first, all within 25", sorted && (near.isEmpty() || near.get(near.size() - 1).dist <= 25), SolCarsNearCore.join(near));
        }
        ck("the real file was only read", Arrays.equals(before, sha(source)), "");
        if (good == null) good = blobs.get(0);
        startTests(real);
        byte[] template = good;

        // ---- synthetic layouts from a real blob
        try (Connection c = DriverManager.getConnection("jdbc:sqlite::memory:")) {
            try (Statement s = c.createStatement()) { s.executeUpdate(SCHEMA); s.executeUpdate("CREATE INDEX ivwx ON vehicles (wx)"); s.executeUpdate("CREATE INDEX ivwy ON vehicles (wy)"); }
            float cx = 10003.5f, cy = 10003.5f;                                  // on chunk corners: the query crosses chunk lines on every side
            int id = 1;
            float[][] dirs = { {1, 0}, {-1, 0}, {0, 1}, {0, -1}, {0.7071f, 0.7071f}, {-0.7071f, 0.7071f}, {0.7071f, -0.7071f}, {-0.7071f, -0.7071f} };
            for (float[] v : dirs) put(c, id++, cx + v[0] * 20, cy + v[1] * 20, template);   // ids 1..8, all 20 tiles away
            put(c, 20, cx + 24.9f, cy, template);
            put(c, 21, cx - 25.2f, cy, template);
            put(c, 22, cx, cy + 40, template);
            put(c, 23, cx + 3, cy + 4, template);                                 // 5 tiles
            List<SolCarsNearCore.Car> l = SolCarsNearCore.scan(c, cx, cy, 25, i -> false);
            List<Integer> got = ids(l);
            ck("nearest first", !got.isEmpty() && got.get(0) == 23, got);
            ck("every direction at the same distance is found", got.containsAll(List.of(1, 2, 3, 4, 5, 6, 7, 8)), got);
            ck("ties: lower id first", got.subList(1, 9).equals(List.of(1, 2, 3, 4, 5, 6, 7, 8)), got);
            ck("24.9 tiles is in", got.contains(20) && got.get(got.size() - 1) == 20, got);
            ck("25.2 and 40 tiles are out", !got.contains(21) && !got.contains(22), got);
            ck("asking for more than 25 is held to 25", !ids(SolCarsNearCore.scan(c, cx, cy, 100, i -> false)).contains(21), "");
            ck("radius 6 keeps only the near one", ids(SolCarsNearCore.scan(c, cx, cy, 6, i -> false)).equals(List.of(23)), "");
            List<SolCarsNearCore.Car> lo = SolCarsNearCore.scan(c, cx, cy, 25, i -> i == 23);
            ck("a loaded car is listed as loaded, never ok", "loaded".equals(lo.get(0).verdict) && lo.get(0).loaded, lo.get(0).line());
            try (Statement s = c.createStatement()) { s.executeUpdate("UPDATE vehicles SET inMeta = 1 WHERE id = 1"); }
            SolCarsNearCore.Car m1 = null;
            for (SolCarsNearCore.Car k : SolCarsNearCore.scan(c, cx, cy, 25, i -> false)) if (k.id == 1) m1 = k;
            ck("a car kept in meta is not ok", m1 != null && "in_meta".equals(m1.verdict), m1 == null ? null : m1.line());
            ck("far_meta: a car kept in meta has a 16th field, its row's own verdict", m1 != null && m1.line().split(",").length == 16 && m1.line().endsWith("," + SolCarsNearCore.verdictOfRow(m1)) && SolCarsNearCore.verdictOfRow(m1).equals(m1.metaVerdict), m1 == null ? null : m1.line());
            SolCarsNearCore.Car n2 = null;
            for (SolCarsNearCore.Car k : SolCarsNearCore.scan(c, cx, cy, 25, i -> false)) if (k.id == 2) n2 = k;
            ck("far_meta: any other car keeps 15 fields and no meta verdict", n2 != null && n2.line().split(",").length == 15 && n2.metaVerdict == null, n2 == null ? null : n2.line());
            try (Statement s = c.createStatement()) { s.executeUpdate("UPDATE vehicles SET inMeta = 0 WHERE id = 1"); }
            ck("a junk blob: unknown, no crash", junk(c, cx, cy), "");
            ck("the line format has 15 fields", l.get(0).line().split(",").length == 15, l.get(0).line());

            // ---- verdicts
            SolCarsNearCore.Car v = new SolCarsNearCore.Car();
            v.script = "Base.CarNormal"; v.fuel = 10; v.engine = 80; v.locked = 0; v.ignition = 1; v.hot = 0; v.keyInCar = 0;
            ck("verdict ok", "ok".equals(SolCarsNearCore.verdict(v)), SolCarsNearCore.verdict(v));
            v.fuel = 0.2f; ck("verdict no_fuel", "no_fuel".equals(SolCarsNearCore.verdict(v)), "");
            v.fuel = Float.NaN; ck("verdict fuel_unknown", "fuel_unknown".equals(SolCarsNearCore.verdict(v)), "");
            v.fuel = 10; v.locked = 1; ck("verdict locked", "locked".equals(SolCarsNearCore.verdict(v)), "");
            v.locked = -1; ck("door unknown: refused (lock_unknown)", "lock_unknown".equals(SolCarsNearCore.verdict(v)), SolCarsNearCore.verdict(v));
            v.locked = 0; v.ignition = 0; ck("no key anywhere: no_key", "no_key".equals(SolCarsNearCore.verdict(v)), "");
            v.hot = 1; ck("hotwired: ok", "ok".equals(SolCarsNearCore.verdict(v)), "");
            v.hot = 0; v.keyInCar = 1; ck("a key inside: ok", "ok".equals(SolCarsNearCore.verdict(v)), "");
            v.keyInCar = -1; ck("a key inside unknown, nothing else: start_unknown", "start_unknown".equals(SolCarsNearCore.verdict(v)), "");
            v.ignition = 1; v.locked = 1; ck("locked even with a key in the ignition: locked", "locked".equals(SolCarsNearCore.verdict(v)), "");
            v.locked = 0; v.keyInCar = 0;
            v.engine = 0; ck("verdict no_engine", "no_engine".equals(SolCarsNearCore.verdict(v)), "");
            v.engine = 50; v.tires = 0; ck("verdict no_tires", "no_tires".equals(SolCarsNearCore.verdict(v)), "");
            v.tires = -1; ck("tyres unknown is not a refusal", "ok".equals(SolCarsNearCore.verdict(v)), "");
            v.script = "Base.TrailerCover"; ck("verdict trailer", "trailer".equals(SolCarsNearCore.verdict(v)), "");
            v.script = "Base.CarNormalBurnt"; ck("verdict wreck", "wreck".equals(SolCarsNearCore.verdict(v)), "");
            v.script = null; ck("verdict unknown_type", "unknown_type".equals(SolCarsNearCore.verdict(v)), "");

            // ---- the move of the chosen car: nothing lost, nothing doubled, rolled back on failure
            int total = count(c);
            Set<Integer> idsBefore = allIds(c);
            int chosen = SolCarsNearCore.scan(c, cx, cy, 25, i -> false).get(0).id;
            ck("move the nearest: ok", "ok".equals(SolCarMoveCore.move(c, chosen, 30000.5f, 30000.5f)), "");
            ck("after a move: same count, same ids", count(c) == total && allIds(c).equals(idsBefore), count(c));
            ck("it is no longer near her", !ids(SolCarsNearCore.scan(c, cx, cy, 25, i -> false)).contains(chosen), "");
            float[] b2 = xy(c, 2);
            ck("spot taken: refused", "spot_taken".equals(SolCarMoveCore.move(c, 2, 30001.5f, 30000.5f)), "");
            ck("spot taken: row untouched, count same", Arrays.equals(b2, xy(c, 2)) && count(c) == total, "");
            try (Statement s = c.createStatement()) { s.executeUpdate("CREATE TRIGGER boom BEFORE UPDATE ON vehicles BEGIN SELECT RAISE(ABORT, 'disk full'); END"); }
            float[] b3 = xy(c, 3);
            String r = SolCarMoveCore.move(c, 3, 31000.5f, 31000.5f);
            ck("a failing write: db_error", r.startsWith("db_error:"), r);
            ck("a failing write: rolled back, row as it was", Arrays.equals(b3, xy(c, 3)), "");
            ck("a failing write: same count, same ids", count(c) == total && allIds(c).equals(idsBefore), "");
            ck("a failing write: autocommit restored", c.getAutoCommit(), "");
            try (Statement s = c.createStatement()) { s.executeUpdate("DROP TRIGGER boom"); }
            ck("after the failure it still moves", "ok".equals(SolCarMoveCore.move(c, 3, 31000.5f, 31000.5f)) && count(c) == total, "");
            ck("unknown id: not_in_db, nothing created", "not_in_db".equals(SolCarMoveCore.move(c, 999, 1, 1)) && count(c) == total, "");
        }
        System.out.println("SUMMARY " + (failed == 0 ? "ALL PASS" : "FAILED " + failed));
        System.exit(failed == 0 ? 0 : 1);
    }

    private static SolCarsNearCore.Car dec(byte[] d) {
        SolCarsNearCore.Car c = new SolCarsNearCore.Car();
        SolCarsNearCore.decode(d, c);
        c.verdict = SolCarsNearCore.verdict(c);
        return c;
    }
    private static SolCarBlob.Result walk(byte[] d) {
        int p = SolCarsNearCore.scriptAt(d);
        int q = p + 2 + (((d[p] & 0xff) << 8) | (d[p + 1] & 0xff));
        int parts = ((d[q + 40] & 0xff) << 8) | (d[q + 41] & 0xff);
        int keyId = ByteBuffer.wrap(d).getInt(q + 29);
        return SolCarBlob.parse(d, q + 42, parts, keyId);
    }

    /** The owner's rule on real records from the copy, and on copies of them changed in memory (never the file). */
    private static void startTests(java.util.Map<Integer, byte[]> real) {
        Integer ign = null, glove = null, locked = null, noKey = null, plain = null;
        for (java.util.Map.Entry<Integer, byte[]> e : real.entrySet()) {
            SolCarsNearCore.Car c = dec(e.getValue());
            SolCarBlob.Result b = walk(e.getValue());
            if (!b.ok) continue;
            if (ign == null && c.ignition == 1) ign = e.getKey();
            if (glove == null && c.keyInCar == 1) glove = e.getKey();
            if (locked == null && c.locked == 1 && c.ignition == 0 && c.hot == 0 && c.keyInCar == 0) locked = e.getKey();
            if (noKey == null && "no_key".equals(c.verdict)) noKey = e.getKey();
            if (plain == null && c.locked == 0 && c.ignition == 0 && c.hot == 0 && c.keyInCar == 0 && !b.items.isEmpty()) plain = e.getKey();
        }
        System.out.println("REAL ignition=" + ign + " glovebox=" + glove + " locked=" + locked + " noKey=" + noKey + " plain=" + plain);
        ck("real: a car with its key in the ignition is found and read as such", ign != null && dec(real.get(ign)).ignition == 1, ign);
        if (ign != null) {
            byte[] d = real.get(ign);
            SolCarBlob.Result b = walk(d);
            ck("real: the ignition flag is set in that record", b.keysInIgnition == 1 && b.ignitionItemAt > 0, b.keysInIgnition);
            SolCarsNearCore.Car c = dec(d);
            ck("real: key in the ignition, unlocked: startable", c.locked == 1 || (c.ignition == 1 && !"no_key".equals(c.verdict) && !"start_unknown".equals(c.verdict)), c.line());
            byte[] m = d.clone();
            int size = ByteBuffer.wrap(m).getInt(b.ignitionItemAt - 4);
            ByteBuffer.wrap(m).putInt(b.ignitionItemAt + size - 5, 12345);       // the key's own keyId, at the end of Key.save
            SolCarsNearCore.Car w = dec(m);
            ck("changed copy: another car's key in the ignition is not this car's", w.ignition == 0, w.line());
            byte[] off = d.clone();
            off[b.tailAt + 3] = 0;                                               // keysInIgnition off, the key item still saved
            ck("changed copy: ignition flag off: not counted", dec(off).ignition == 0, dec(off).line());
        }
        ck("real: a car with its key in a container (glovebox) is found", glove != null && dec(real.get(glove)).keyInCar == 1, glove);
        if (glove != null) {
            SolCarBlob.Result b = walk(real.get(glove));
            boolean inGlove = false;
            int gk = dec(real.get(glove)).keyId;
            for (SolCarBlob.Item it : b.items) if (SolCarBlob.keyMatch(real.get(glove), it.at, it.len, gk) == SolCarBlob.YES) inGlove |= it.part.equals("GloveBox");
            ck("real: that key is in the GloveBox part", inGlove, "");
        }
        ck("real: a locked car with no key is refused as locked", locked != null && "locked".equals(dec(real.get(locked)).verdict), locked);
        ck("real: an unlocked car with no key anywhere is no_key", noKey != null && "no_key".equals(dec(real.get(noKey)).verdict), noKey);
        Integer base = noKey != null ? noKey : plain;
        if (base != null) {
            byte[] d = real.get(base);
            SolCarBlob.Result b = walk(d);
            byte[] h = d.clone(); h[b.tailAt + 1] = 1;                           // hotwired
            SolCarsNearCore.Car hc = dec(h);
            ck("changed copy: hotwired: startable", hc.hot == 1 && (!"no_key".equals(hc.verdict) && !"start_unknown".equals(hc.verdict)), hc.line());
            byte[] hb = h.clone(); hb[b.tailAt + 2] = 1;                         // and the wires broken
            ck("changed copy: hotwired with broken wires: not startable", dec(hb).hot == 0 && "no_key".equals(dec(hb).verdict), dec(hb).line());
            byte[] bad = d.clone(); bad[b.tailAt + 1] = 7;                       // a flag that is not 0/1: the walk stops, nothing known
            SolCarsNearCore.Car bc = dec(bad);
            ck("changed copy: a broken record: start unknown, not ok", bc.ignition < 0 && bc.hot < 0 && bc.keyInCar < 0 && !"ok".equals(bc.verdict), bc.line());
            if (!b.items.isEmpty()) {
                SolCarBlob.Item it = b.items.get(0);
                int keyId = dec(d).keyId;
                byte[] u = d.clone(); ByteBuffer.wrap(u).putInt(it.at + it.len / 2, keyId);   // the car's key id inside an item that is not a key
                SolCarsNearCore.Car uc = dec(u);
                ck("changed copy: its key id inside some other item: unknown, never ok", uc.keyInCar == -1 && "start_unknown".equals(uc.verdict), uc.line());
            }
        }
        ck("the base for the changed copies exists", base != null, "");
    }

    private static boolean junk(Connection c, float cx, float cy) throws Exception {
        try (PreparedStatement p = c.prepareStatement("INSERT INTO vehicles(id,wx,wy,x,y,inMeta,worldversion,data) VALUES(77,?,?,?,?,0,251,?)")) {
            p.setInt(1, (int) Math.floor(cx / 8)); p.setInt(2, (int) Math.floor(cy / 8)); p.setFloat(3, cx + 1); p.setFloat(4, cy); p.setBytes(5, new byte[] { 1, 2, 3, 0, 9, 'G', 'a', 's' });
            p.executeUpdate();
        }
        SolCarsNearCore.Car j = null;
        for (SolCarsNearCore.Car k : SolCarsNearCore.scan(c, cx, cy, 25, i -> false)) if (k.id == 77) j = k;
        try (Statement s = c.createStatement()) { s.executeUpdate("DELETE FROM vehicles WHERE id = 77"); }
        return j != null && "unknown_type".equals(j.verdict) && j.script == null && Float.isNaN(j.fuel);
    }
}

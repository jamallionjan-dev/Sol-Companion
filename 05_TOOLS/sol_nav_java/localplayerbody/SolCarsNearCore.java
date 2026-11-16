package localplayerbody;

import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.function.IntPredicate;

/**
 * Read only: the vehicles whose saved row lies within a radius of a point, nearest first (ties: lower id first), with what can be read
 * safely from each row. Nothing is written. Field order is BaseVehicle.save / VehiclePart.save / KahluaTableImpl.save of 42.22.2
 * (javap, 2026-11-10). Anything that does not parse exactly is "?" (unknown), never a guess.
 * Line per car: id,x,y,dist,script,fuel,engine,locked,quality,keyId,loaded,verdict,ignition,hotwired,keyInCar ; cars joined by ';'.
 * far_meta: a car kept "in meta" (VirtualVehicleManager: it was left with its engine running, its alarm or its siren on) keeps the
 * verdict in_meta and gets a 16th field, the verdict it would have otherwise (its saved row, which the game rewrites at each save).
 * Only the arrival inside the loaded area (SolCarArrive) may bring such a car; the 15-field line of every other car is unchanged.
 * Starting it (SolCarBlob): a key for it in the ignition, hotwired (wires not broken), or a key for it inside it. Her own keys: Lua.
 */
public final class SolCarsNearCore {
    public static final double MAX_RADIUS = 25.0;
    public static final float MIN_FUEL = 0.5f;
    static final int CHUNK_TILES = 8;

    private SolCarsNearCore() {}

    public static final class Car {
        public int id;
        public float x, y;
        public double dist;
        public String script;                 // null: unknown
        public float fuel = Float.NaN;        // NaN: unknown
        public int engine = -1;               // engine part condition, -1 unknown
        public int locked = -1;               // driver door: 1 locked, 0 not, -1 unknown
        public int quality = -1, keyId = Integer.MIN_VALUE;
        public int tires = -1;                // the worst of the four tyres: condition, 0 when one is missing; -1 unknown (or not four)
        public int ignition = -1, hot = -1, keyInCar = -1;   // 1 yes, 0 no, -1 unknown
        public boolean loaded, inMeta;
        public String verdict;
        public String metaVerdict;            // far_meta: only for a car kept in meta, the verdict without that

        public String line() {
            return id + "," + r1(x) + "," + r1(y) + "," + r1((float) dist) + "," + (script == null ? "?" : script) + ","
                + (Float.isNaN(fuel) ? "?" : r2(fuel)) + "," + (engine < 0 ? "?" : engine) + "," + (locked < 0 ? "?" : locked) + ","
                + (quality < 0 ? "?" : quality) + "," + (keyId == Integer.MIN_VALUE ? "?" : keyId) + "," + (loaded ? 1 : 0) + "," + verdict
                + "," + q(ignition) + "," + q(hot) + "," + q(keyInCar) + (inMeta && metaVerdict != null ? "," + metaVerdict : "");
        }
        private static String q(int v) { return v < 0 ? "?" : String.valueOf(v); }
        private static String r1(float v) { return String.valueOf(Math.round(v * 10f) / 10f); }
        private static String r2(float v) { return String.valueOf(Math.round(v * 100f) / 100f); }
    }

    public static String join(List<Car> cars) {
        StringBuilder b = new StringBuilder();
        for (Car c : cars) { if (b.length() > 0) b.append(';'); b.append(c.line()); }
        return b.toString();
    }

    public static List<Car> scan(Connection c, double x, double y, double radius, IntPredicate loaded) throws SQLException {
        double r = Math.max(0, Math.min(MAX_RADIUS, radius));
        List<Car> out = new ArrayList<>();
        int wx0 = (int) Math.floor((x - r) / CHUNK_TILES), wx1 = (int) Math.floor((x + r) / CHUNK_TILES);
        int wy0 = (int) Math.floor((y - r) / CHUNK_TILES), wy1 = (int) Math.floor((y + r) / CHUNK_TILES);
        try (PreparedStatement q = c.prepareStatement("SELECT id, x, y, inMeta, data FROM vehicles WHERE wx BETWEEN ? AND ? AND wy BETWEEN ? AND ?")) {
            q.setInt(1, wx0); q.setInt(2, wx1); q.setInt(3, wy0); q.setInt(4, wy1);
            try (ResultSet rs = q.executeQuery()) {
                while (rs.next()) {
                    Car car = new Car();
                    car.id = rs.getInt(1);
                    car.x = rs.getFloat(2);
                    car.y = rs.getFloat(3);
                    car.dist = Math.hypot(car.x - x, car.y - y);
                    if (!(car.dist <= r)) continue;
                    car.inMeta = rs.getBoolean(4);
                    car.loaded = loaded != null && loaded.test(car.id);
                    decode(rs.getBytes(5), car);
                    car.verdict = verdict(car);
                    if (car.inMeta && !car.loaded) car.metaVerdict = verdictOfRow(car);     // far_meta
                    out.add(car);
                }
            }
        }
        out.sort(Comparator.comparingLong((Car a) -> Math.round(a.dist * 100)).thenComparingInt(a -> a.id));   // a hundredth of a tile is a tie
        return out;
    }

    public static String verdict(Car c) {
        if (c.loaded) return "loaded";
        if (c.inMeta) return "in_meta";
        return verdictOfRow(c);
    }

    /** The verdict from the saved row alone, whether or not the car is kept in meta (far_meta). */
    public static String verdictOfRow(Car c) {
        if (c.script == null) return "unknown_type";
        String s = c.script.toLowerCase();
        if (s.contains("trailer")) return "trailer";
        if (s.contains("burnt") || s.contains("smashed") || s.contains("wreck")) return "wreck";
        if (c.engine == 0) return "no_engine";
        if (c.tires == 0) return "no_tires";
        if (Float.isNaN(c.fuel)) return "fuel_unknown";
        if (c.fuel < MIN_FUEL) return "no_fuel";
        if (c.locked < 0) return "lock_unknown";                              // unlocked must be known: never a guess
        if (c.locked == 1) return "locked";
        if (c.ignition == 1 || c.hot == 1 || c.keyInCar == 1) return "ok";
        if (c.ignition == 0 && c.hot == 0 && c.keyInCar == 0) return "no_key";   // Lua still checks the keys she carries
        return "start_unknown";
    }

    // ------------------------------------------------------------------ the row's blob, big-endian
    private static int u8(byte[] d, int p) { return d[p] & 0xff; }
    private static int u16(byte[] d, int p) { return ((d[p] & 0xff) << 8) | (d[p + 1] & 0xff); }
    private static int i32(byte[] d, int p) { return ((d[p] & 0xff) << 24) | ((d[p + 1] & 0xff) << 16) | ((d[p + 2] & 0xff) << 8) | (d[p + 3] & 0xff); }
    private static float f32(byte[] d, int p) { return Float.intBitsToFloat(i32(d, p)); }
    private static double f64(byte[] d, int p) { return Double.longBitsToDouble(((long) i32(d, p) << 32) | (i32(d, p + 4) & 0xffffffffL)); }

    private static boolean nameChar(int ch) { return (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9') || ch == '_' || ch == '-'; }

    /** Offset of the script name's length, or -1: a Module.Name string right after a unit quaternion (the saved rotation). */
    static int scriptAt(byte[] d) {
        for (int p = 20; p + 2 < d.length && p < 4096; p++) {
            int len = u16(d, p);
            if (len < 3 || len > 64 || p + 2 + len > d.length) continue;
            int dots = 0;
            boolean ok = true;
            for (int k = 0; k < len && ok; k++) {
                int ch = u8(d, p + 2 + k);
                if (ch == '.') dots++; else ok = nameChar(ch);
            }
            if (!ok || dots != 1 || d[p + 2] == '.' || d[p + 1 + len] == '.') continue;
            double n = 0;
            for (int k = 0; k < 4; k++) { float q = f32(d, p - 16 + 4 * k); if (!Float.isFinite(q)) { n = -1; break; } n += q * q; }
            if (n >= 0.98 && n <= 1.02) return p;
        }
        return -1;
    }

    static void decode(byte[] d, Car car) {
        if (d == null) return;
        try {
            int p = scriptAt(d);
            if (p < 0) return;
            int len = u16(d, p);
            String script = new String(d, p + 2, len, StandardCharsets.US_ASCII);
            int q = p + 2 + len;
            if (q + 42 > d.length) return;
            int running = u8(d, q + 4);
            int quality = i32(d, q + 5 + 20);
            int keyId = i32(d, q + 5 + 24);
            int parts = u16(d, q + 40);
            if (running > 1 || quality < 0 || quality > 100 || parts < 0 || parts > 200) return;
            car.script = script;
            car.quality = quality;
            car.keyId = keyId;
            int partsAt = q + 42;
            if (parts == 0) return;                                              // a burnt shell: no parts at all
            Part gas = only(d, partsAt, "GasTank");
            if (gas != null) car.fuel = gas.hasItem ? (float) (Double.isNaN(gas.content) ? 0 : gas.content) : 0f;
            Part engine = only(d, partsAt, "Engine");
            if (engine != null) car.engine = engine.condition;
            Part door = only(d, partsAt, "DoorFrontLeft");
            if (door != null && door.locked >= 0) car.locked = door.locked;
            int worst = 101;
            for (String tire : TIRES) {
                Part t = only(d, partsAt, tire);
                if (t == null) { worst = -1; break; }
                worst = Math.min(worst, t.hasItem ? t.condition : 0);
            }
            car.tires = worst;
            SolCarBlob.Result blob = SolCarBlob.parse(d, partsAt, parts, keyId);
            if (blob.ok) { car.ignition = blob.ignitionKey; car.hot = blob.hot(); car.keyInCar = blob.keyInCar; }
        } catch (RuntimeException e) {
            car.script = null; car.fuel = Float.NaN; car.engine = -1; car.tires = -1; car.ignition = -1; car.hot = -1; car.keyInCar = -1; car.locked = -1; car.quality = -1; car.keyId = Integer.MIN_VALUE;
        }
    }

    static final String[] TIRES = { "TireFrontLeft", "TireFrontRight", "TireRearLeft", "TireRearRight" };

    static final class Part { boolean hasItem; double content = Double.NaN; int locked = -1; int condition; }

    /** The part saved under this id, when exactly one place in the blob parses as it, field by field. */
    static Part only(byte[] d, int from, String id) {
        byte[] name = id.getBytes(StandardCharsets.US_ASCII);
        Part found = null;
        int hits = 0;
        for (int p = from; p + 2 + name.length <= d.length; p++) {
            if (u16(d, p) != name.length) continue;
            boolean same = true;
            for (int k = 0; k < name.length && same; k++) same = d[p + 2 + k] == name[k];
            if (!same) continue;
            Part part = part(d, p + 2 + name.length);
            if (part != null) { found = part; hits++; }
        }
        return hits == 1 ? found : null;
    }

    private static Part part(byte[] d, int r) {
        try {
            Part out = new Part();
            if (u8(d, r) > 1) return null;                                       // created
            if (!Float.isFinite(f32(d, r + 1))) return null;                     // lastUpdated
            r += 5;
            int hasItem = u8(d, r++);
            if (hasItem > 1) return null;
            if (hasItem == 1) {
                int size = i32(d, r);
                if (size < 0 || r + 4 + size > d.length) return null;
                r += 4 + size;
            }
            out.hasItem = hasItem == 1;
            int hasContainer = u8(d, r++);
            if (hasContainer != 0) return null;                                  // an item container has no size in front of it: not readable
            int hasMod = u8(d, r++);
            if (hasMod > 1) return null;
            if (hasMod == 1) {
                double[] content = { Double.NaN };
                r = table(d, r, 0, content);
                if (r < 0) return null;
                out.content = content[0];
            }
            if (u8(d, r++) != 0) return null;                                    // a radio's device data: not readable
            int hasLight = u8(d, r++);
            if (hasLight > 1) return null;
            if (hasLight == 1) { if (u8(d, r) > 1) return null; r += 21; }
            int hasDoor = u8(d, r++);
            if (hasDoor > 1) return null;
            if (hasDoor == 1) {
                if (u8(d, r) > 1 || u8(d, r + 1) > 1 || u8(d, r + 2) > 1) return null;
                out.locked = u8(d, r + 1);
                r += 3;
            }
            int hasWindow = u8(d, r++);
            if (hasWindow > 1) return null;
            if (hasWindow == 1) { if (u8(d, r + 1) > 1) return null; r += 2; }
            int condition = i32(d, r);
            if (condition < 0 || condition > 100) return null;
            if (!Float.isFinite(f32(d, r + 4))) return null;
            int skill = i32(d, r + 8);
            if (skill < 0 || skill > 100) return null;
            if (!Float.isFinite(f32(d, r + 12)) || !Float.isFinite(f32(d, r + 16))) return null;
            if (u8(d, r + 20) > 1) return null;
            out.condition = condition;
            return out;
        } catch (ArrayIndexOutOfBoundsException e) {
            return null;
        }
    }

    /** A saved Kahlua table; the end offset, or -1. A top-level numeric "contentAmount" is kept. */
    private static int table(byte[] d, int r, int depth, double[] content) {
        if (depth > 16) return -1;
        int n = i32(d, r);
        r += 4;
        if (n < 0 || n > 100000) return -1;
        for (int i = 0; i < n; i++) {
            int kt = u8(d, r++);
            String key = null;
            if (kt == 0) { int l = u16(d, r); if (r + 2 + l > d.length) return -1; key = new String(d, r + 2, l, StandardCharsets.UTF_8); r += 2 + l; }
            else if (kt == 1) r += 8;
            else return -1;
            int vt = u8(d, r++);
            if (vt == 0) { int l = u16(d, r); if (r + 2 + l > d.length) return -1; r += 2 + l; }
            else if (vt == 1) { double v = f64(d, r); r += 8; if (depth == 0 && "contentAmount".equals(key)) { if (!Double.isFinite(v)) return -1; content[0] = v; } }
            else if (vt == 3) { if (u8(d, r) > 1) return -1; r += 1; }
            else if (vt == 2) { r = table(d, r, depth + 1, new double[1]); if (r < 0) return -1; }
            else return -1;
            if (r > d.length) return -1;
        }
        return r;
    }
}

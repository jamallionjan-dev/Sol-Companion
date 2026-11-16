package localplayerbody;

import java.util.ArrayList;
import java.util.List;

/**
 * Read only: walks a saved vehicle record from its first part to the ignition key, field by field, exactly as 42.22.2 writes it
 * (javap 2026-11-10): VehiclePart.save, ItemContainer.save + CompressIdenticalItems.save (each item behind its size), DeviceData.save,
 * VehicleLight/VehicleDoor/VehicleWindow.save, then BaseVehicle.save's keyIsOnDoor, hotwired, hotwiredBroken, keysInIgnition, rust, colour,
 * enginePower, vehicleId, mechanicalId, alarm, siren, currentKey. Any field that is not what it must be ends the walk: everything unknown.
 * A key for the car: see keyMatch. An item is surely not one only when the car's keyId bytes appear nowhere inside it; else unknown.
 */
public final class SolCarBlob {
    public static final int YES = 1, NO = 0, UNKNOWN = -1;

    private SolCarBlob() {}

    public static final class Item { public final int at, len; public final String part; Item(int at, int len, String part) { this.at = at; this.len = len; this.part = part; } }

    public static final class Result {
        public boolean ok;
        public int keyOnDoor = UNKNOWN, hotwired = UNKNOWN, hotwiredBroken = UNKNOWN, keysInIgnition = UNKNOWN;
        public int ignitionKey = UNKNOWN;     // the key in the ignition is this car's: YES / NO / UNKNOWN
        public int keyInCar = UNKNOWN;        // a key for this car in one of its containers
        public int tailAt = -1, ignitionItemAt = -1;
        public final List<Item> items = new ArrayList<>();
        /** hotwired and the wires not broken */
        public int hot() { return hotwired < 0 || hotwiredBroken < 0 ? UNKNOWN : (hotwired == 1 && hotwiredBroken == 0 ? YES : NO); }
    }

    private static final class Bad extends RuntimeException { Bad() { super(null, null, false, false); } }
    private static final class R {
        final byte[] d; int p;
        R(byte[] d, int p) { this.d = d; this.p = p; }
        void need(int n) { if (n < 0 || p + n > d.length) throw new Bad(); }
        int u8() { need(1); return d[p++] & 0xff; }
        int b01() { int v = u8(); if (v > 1) throw new Bad(); return v; }
        int u16() { need(2); int v = ((d[p] & 0xff) << 8) | (d[p + 1] & 0xff); p += 2; return v; }
        int i32() { need(4); int v = ((d[p] & 0xff) << 24) | ((d[p + 1] & 0xff) << 16) | ((d[p + 2] & 0xff) << 8) | (d[p + 3] & 0xff); p += 4; return v; }
        int i32(int lo, int hi) { int v = i32(); if (v < lo || v > hi) throw new Bad(); return v; }
        float f32() { float v = Float.intBitsToFloat(i32()); if (!Float.isFinite(v)) throw new Bad(); return v; }
        float f01() { float v = f32(); if (v < -0.0001f || v > 1.0001f) throw new Bad(); return v; }
        double f64() { need(8); long hi = i32() & 0xffffffffL, lo = i32() & 0xffffffffL; double v = Double.longBitsToDouble((hi << 32) | lo); if (Double.isNaN(v)) throw new Bad(); return v; }
        String str(int max) { int l = u16(); if (l > max) throw new Bad(); need(l); String s = new String(d, p, l, java.nio.charset.StandardCharsets.UTF_8); p += l; return s; }
        void skip(int n) { need(n); p += n; }
    }

    public static Result parse(byte[] d, int partsAt, int partCount, int carKeyId) {
        Result out = new Result();
        try {
            R r = new R(d, partsAt);
            for (int i = 0; i < partCount; i++) part(r, out);
            out.tailAt = r.p;
            int keyOnDoor = r.b01(), hotwired = r.b01(), broken = r.b01(), inIgnition = r.b01();
            r.f01(); r.f01(); r.f01(); r.f01();                                  // rust, colour hue / saturation / value
            r.i32(0, 1000000);                                                   // engine power
            r.u16();                                                             // vehicleId
            r.i32();                                                             // mechanicalId
            r.b01();                                                             // alarmed
            r.f64();                                                             // alarm start
            r.str(256);                                                          // alarm sound
            r.f64();                                                             // siren start
            int hasKey = r.b01();
            int ignition = NO;
            if (hasKey == 1) {
                int size = r.i32(0, d.length);
                r.need(size);
                out.ignitionItemAt = r.p;
                ignition = keyMatch(d, r.p, size, carKeyId);
                r.p += size;
            }
            out.keyOnDoor = keyOnDoor; out.hotwired = hotwired; out.hotwiredBroken = broken; out.keysInIgnition = inIgnition;
            out.ignitionKey = inIgnition == 1 ? ignition : NO;
            int inCar = NO;
            for (Item it : out.items) {
                int m = keyMatch(d, it.at, it.len, carKeyId);
                if (m == YES) { inCar = YES; break; }
                if (m == UNKNOWN) inCar = UNKNOWN;
            }
            out.keyInCar = inCar;
            out.ok = true;
        } catch (Bad | ArrayIndexOutOfBoundsException e) {
            Result unknown = new Result();
            return unknown;
        }
        return out;
    }

    private static void part(R r, Result out) {
        String id = r.str(64);
        r.b01();                                                                 // created
        r.f32();                                                                 // lastUpdated
        if (r.b01() == 1) { int size = r.i32(0, r.d.length); r.skip(size); }   // the installed part, behind its size
        if (r.b01() == 1) container(r, out, id);
        if (r.b01() == 1) table(r, 0);
        if (r.b01() == 1) device(r);
        if (r.b01() == 1) { r.b01(); r.skip(20); }                               // light: active, offset x/y, intensity, dist, focusing
        if (r.b01() == 1) { r.b01(); r.b01(); r.b01(); }                         // door: open, locked, lockBroken
        if (r.b01() == 1) { r.u8(); r.b01(); }                                   // window: condition, open
        r.i32(0, 100);                                                           // condition
        r.f32();                                                                 // wheelFriction
        r.i32(0, 100);                                                           // mechanicSkillInstaller
        r.f32(); r.f32();                                                        // suspension
        if (r.b01() != 0) throw new Bad();                                       // an entity save: not readable here
    }

    private static void container(R r, Result out, String part) {
        r.str(256);                                                              // container type
        r.b01();                                                                 // explored
        int groups = r.u16();
        if (groups > 20000) throw new Bad();
        for (int g = 0; g < groups; g++) {
            int count = r.i32(1, 100000);
            int size = r.i32(7, r.d.length);
            r.need(size);
            out.items.add(new Item(r.p, size, part));
            r.p += size;
            r.skip(4 * (count - 1));                                             // ids of the identical copies
        }
        r.b01();                                                                 // looted
        r.i32(0, 1000000);                                                       // capacity
    }

    private static void device(R r) {
        r.str(256);
        r.b01(); r.i32(); r.i32(); r.b01(); r.f32(); r.f32(); r.b01(); r.b01(); r.b01(); r.b01();
        r.i32(); r.i32(); r.i32(); r.b01(); r.b01(); r.f32(); r.f32(); r.i32();
        if (r.b01() == 1) { r.i32(); int n = r.i32(0, 10000); for (int i = 0; i < n; i++) { r.str(1024); r.i32(); } }
        r.u16(); r.u8();
        if (r.b01() == 1) r.str(1024);
        r.b01();
    }

    private static void table(R r, int depth) {
        if (depth > 16) throw new Bad();
        int n = r.i32(0, 100000);
        for (int i = 0; i < n; i++) {
            int kt = r.u8();
            if (kt == 0) r.str(65535); else if (kt == 1) r.skip(8); else throw new Bad();
            int vt = r.u8();
            if (vt == 0) r.str(65535);
            else if (vt == 1) r.skip(8);
            else if (vt == 3) r.b01();
            else if (vt == 2) table(r, depth + 1);
            else throw new Bad();
        }
    }

    static boolean contains(byte[] d, int at, int len, int v) {
        byte a = (byte) (v >>> 24), b = (byte) (v >>> 16), c = (byte) (v >>> 8), e = (byte) v;
        for (int i = at; i + 4 <= at + len; i++) if (d[i] == a && d[i + 1] == b && d[i + 2] == c && d[i + 3] == e) return true;
        return false;
    }

    /**
     * YES: this item is the car's key. zombie.inventory.types.Key.save writes InventoryItem.save, then keyId (int), then numberOfKey (byte),
     * so a key's last five bytes are its keyId and a small count; and its record names a key type (Base.CarKey). All three must hold.
     * NO: the car's keyId bytes are nowhere in the item. UNKNOWN: anything between (e.g. the id elsewhere inside a bag).
     */
    static int keyMatch(byte[] d, int at, int len, int carKeyId) {
        if (carKeyId == -1) return NO;                                           // a car without a key id has no key
        if (!contains(d, at, len, carKeyId)) return NO;
        int end = at + len;
        if (len >= 12 && i32(d, end - 5) == carKeyId && (d[end - 1] & 0xff) <= 16 && namesKey(d, at, len)) return YES;
        return UNKNOWN;
    }

    private static int i32(byte[] d, int p) { return ((d[p] & 0xff) << 24) | ((d[p + 1] & 0xff) << 16) | ((d[p + 2] & 0xff) << 8) | (d[p + 3] & 0xff); }

    /** a saved string Module.Name whose name has "Key" in it */
    static boolean namesKey(byte[] d, int at, int len) {
        for (int p = at; p + 2 < at + len; p++) {
            int l = ((d[p] & 0xff) << 8) | (d[p + 1] & 0xff);
            if (l < 5 || l > 64 || p + 2 + l > at + len) continue;
            String s = new String(d, p + 2, l, java.nio.charset.StandardCharsets.ISO_8859_1);
            if (s.matches("[A-Za-z0-9_]+[.][A-Za-z0-9_]*Key[A-Za-z0-9_]*")) return true;
        }
        return false;
    }
}

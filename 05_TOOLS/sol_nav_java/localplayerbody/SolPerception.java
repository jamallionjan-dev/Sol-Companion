package localplayerbody;

import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

import me.zed_0xff.zombie_buddy.Exposer;
import se.krka.kahlua.integration.annotations.LuaMethod;
import zombie.core.properties.PropertyContainer;
import zombie.iso.IsoCell;
import zombie.iso.IsoGridSquare;
import zombie.iso.IsoObject;
import zombie.iso.IsoWorld;
import zombie.iso.SpriteDetails.IsoFlagType;
import zombie.iso.sprite.IsoSprite;
import zombie.pathfind.VehiclePoly;
import zombie.vehicles.BaseVehicle;

/** Stage 1: records what a car can hit around a point. Reads on the main thread in slices of at most 0.4 ms; draws and writes on a worker thread. */
@Exposer.LuaClass
public final class SolPerception {
    public static final int NONE = 0, SOLID = 1, POST = 2, EDGE_N = 4, EDGE_W = 8, OFF_ROAD = 16;
    static final int CELLS_PER_TILE = 10;
    private static final SolNavCost COST = new SolNavCost("perception", 250_000L);  //                     // one square can run past the check: keeps the worst frame under 0.5 ms
    private static final long MIN_GAP_MS = 20_000L;

    private static final class Capture {
        int cx, cy, z, radius, nextY, nextX;
        String reason;
        int[] shapes;
        final List<String> notes = new ArrayList<>();
        final List<float[]> cars = new ArrayList<>();
        boolean carsDone;
        int frames;
        long totalNanos, maxNanos;
    }

    private static Capture current;
    private static long lastStart = -MIN_GAP_MS;

    private SolPerception() {}

    /** Begins a capture; returns false while one is running, within 20 s of the last one, or when the world is not there. */
    @LuaMethod(name = "solPerceptionStart", global = true)
    public static boolean start(double x, double y, double radius, String reason) {
        long now = System.currentTimeMillis();
        if (current != null || now - lastStart < MIN_GAP_MS || IsoWorld.instance == null || IsoWorld.instance.getCell() == null) return false;
        int r = Math.max(5, Math.min(40, (int) radius));
        Capture c = new Capture();
        c.cx = (int) Math.floor(x);
        c.cy = (int) Math.floor(y);
        c.radius = r;
        c.reason = reason == null ? "" : reason;
        c.shapes = new int[(2 * r + 1) * (2 * r + 1)];
        c.nextY = 0;
        c.nextX = 0;
        lastStart = now;
        current = c;
        return true;
    }

    /** One sliver of the capture. Does nothing when idle. */
    @LuaMethod(name = "solPerceptionStep", global = true)
    public static void step() {
        Capture c = current;
        if (c == null) return;
        long t0 = System.nanoTime();
        try {
            IsoCell cell = IsoWorld.instance.getCell();
            int size = 2 * c.radius + 1;
            if (!c.carsDone) {
                readCars(cell, c);
                c.carsDone = true;
            } else {
                while (c.nextY < size) {
                    readSquare(cell, c, c.nextX, c.nextY);
                    if (++c.nextX >= size) { c.nextX = 0; c.nextY++; }
                    if (System.nanoTime() - t0 >= COST.slice()) break;
                }
            }
        } catch (RuntimeException e) {
            c.notes.add("capture stopped: " + e);
            c.nextY = 2 * c.radius + 1;
            c.carsDone = true;
        }
        long spent = System.nanoTime() - t0;
        COST.note(spent);
        c.frames++;
        c.totalNanos += spent;
        c.maxNanos = Math.max(c.maxNanos, spent);
        if (c.carsDone && c.nextY >= 2 * c.radius + 1) {
            current = null;
            Thread worker = new Thread(() -> write(c), "SolPerception");
            worker.setDaemon(true);
            worker.start();
        }
    }

    private static void readCars(IsoCell cell, Capture c) {
        for (BaseVehicle v : cell.getVehicles()) {
            if (Math.abs(v.getX() - c.cx) > c.radius + 6 || Math.abs(v.getY() - c.cy) > c.radius + 6) continue;
            VehiclePoly p = v.getPoly();
            if (p != null) c.cars.add(new float[] { p.x1, p.y1, p.x2, p.y2, p.x3, p.y3, p.x4, p.y4 });
        }
    }

    private static void readSquare(IsoCell cell, Capture c, int ix, int iy) {
        int size = 2 * c.radius + 1;
        int wx = c.cx - c.radius + ix, wy = c.cy - c.radius + iy;
        IsoGridSquare sq = cell.getGridSquare(wx, wy, c.z);
        if (sq == null) { c.shapes[iy * size + ix] = -1; return; }
        String[] src = new String[1];
        int shape = shapeOf(sq, src);
        c.shapes[iy * size + ix] = shape;
        if (shape != NONE) c.notes.add(wx + "," + wy + "," + shape + "," + src[0]);
    }

    /** For driving: as below, and also water, buildings and bare squares count as shut; unpaved ground is marked. */
    static int navShapeOf(IsoGridSquare sq) {
        int s = shapeOf(sq, null);
        PropertyContainer p = sq.getProperties();
        IsoObject floor = sq.getFloor();
        if (floor == null || sq.isInARoom() || sq.hasWater() || (p != null && p.has(IsoFlagType.water))) return s | SOLID;
        IsoSprite sprite = floor.getSprite();
        String name = sprite == null ? null : sprite.getName();
        if (name == null || !(name.contains("street") || name.contains("tilesandstone"))) s |= OFF_ROAD;
        return s;
    }

    /** What a car can hit on this square. source[0], if given, names what was found. */
    static int shapeOf(IsoGridSquare sq, String[] out) {
        int shape = NONE;
        String source = null;
        if (sq.isSolid() || sq.isSolidTrans()) { shape |= SOLID; source = "square"; }
        PropertyContainer sp = sq.getProperties();
        if (sp != null) {
            if (sp.has(IsoFlagType.collideN)) shape |= EDGE_N;
            if (sp.has(IsoFlagType.collideW)) shape |= EDGE_W;
        }
        java.util.List<IsoObject> objects = sq.getObjects();          // its iterator throws UnsupportedOperationException
        for (int oi = 0, on = objects.size(); oi < on; oi++) {
            IsoObject o = objects.get(oi);
            IsoSprite s = o.getSprite();
            String name = s == null ? null : s.getName();
            PropertyContainer p = o.getProperties();
            String ps = p == null ? null : p.get("PhysicsShape");
            boolean mesh = p != null && p.has("PhysicsMesh");
            if (name != null && (name.contains("lighting_outdoor_") || name.equals("recreational_sports_01_21")
                    || name.equals("recreational_sports_01_19") || name.equals("recreational_sports_01_32"))) { shape |= POST; source = name; }
            if ("Tree".equals(ps)) { shape |= POST; source = name; }
            if ("Solid".equals(ps) || mesh) { shape |= SOLID; source = name; }
            if ("WallN".equals(ps)) { shape |= EDGE_N; source = name; }
            if ("WallW".equals(ps)) { shape |= EDGE_W; source = name; }
            if (o instanceof zombie.iso.objects.IsoTree) { shape |= POST; source = name; }
            if (p != null && (p.has(IsoFlagType.solid) || p.has(IsoFlagType.solidtrans))) { shape |= SOLID; source = name; }
        }
        if (out != null) out[0] = source;
        return shape;
    }

    /** Is this point of a tile (0..1 each way) inside what stands on it? The same shapes as the picture. */
    static boolean pointBlocked(int s, double fx, double fy) {
        if (s < 0 || (s & SOLID) != 0) return true;
        if ((s & POST) != 0 && (fx - 0.5) * (fx - 0.5) + (fy - 0.5) * (fy - 0.5) <= 0.1225) return true;
        return (s & EDGE_N) != 0 && fy < 0.13 || (s & EDGE_W) != 0 && fx < 0.13;
    }

    /** Draws the 10 cm picture. Pure: no game objects. 0 open, 255 not loaded, 200 solid, 140 post, 90 thin edge, 40 car. */
    static byte[] rasterize(int[] shapes, int size, List<float[]> cars, int originX, int originY) {
        int n = size * CELLS_PER_TILE;
        byte[] img = new byte[n * n];
        for (int py = 0; py < n; py++) {
            for (int px = 0; px < n; px++) {
                int tx = px / CELLS_PER_TILE, ty = py / CELLS_PER_TILE;
                int s = shapes[ty * size + tx];
                double fx = (px % CELLS_PER_TILE + 0.5) / CELLS_PER_TILE, fy = (py % CELLS_PER_TILE + 0.5) / CELLS_PER_TILE;
                int v = 0;
                if (s < 0) v = 255;
                else if ((s & SOLID) != 0) v = 200;
                else if ((s & POST) != 0 && (fx - 0.5) * (fx - 0.5) + (fy - 0.5) * (fy - 0.5) <= 0.1225) v = 140;
                else if ((s & EDGE_N) != 0 && fy < 0.13) v = 90;
                else if ((s & EDGE_W) != 0 && fx < 0.13) v = 90;
                if (v == 0 || v == 90) {
                    double wx = originX + (px + 0.5) / CELLS_PER_TILE, wy = originY + (py + 0.5) / CELLS_PER_TILE;
                    for (float[] car : cars) if (inside(car, wx, wy)) { v = 40; break; }
                }
                img[py * n + px] = (byte) v;
            }
        }
        return img;
    }

    static boolean inside(float[] q, double x, double y) {
        boolean in = false;
        for (int i = 0, j = 3; i < 4; j = i++) {
            double xi = q[2 * i], yi = q[2 * i + 1], xj = q[2 * j], yj = q[2 * j + 1];
            if ((yi > y) != (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) in = !in;
        }
        return in;
    }

    private static void write(Capture c) {
        int size = 2 * c.radius + 1;
        int originX = c.cx - c.radius, originY = c.cy - c.radius;
        String stem = System.getProperty("user.home") + File.separator + "Zomboid" + File.separator + "Lua" + File.separator + "SolPerception_" + System.currentTimeMillis();
        try (PrintWriter out = new PrintWriter(stem + ".txt", StandardCharsets.UTF_8)) {
            out.println("# reason=" + c.reason + " centre=" + c.cx + "," + c.cy + " radius=" + c.radius + " origin=" + originX + "," + originY + " cellsPerTile=" + CELLS_PER_TILE);
            out.println("# x,y,shape(1 solid,2 post,4 edgeN,8 edgeW),source");
            for (String n : c.notes) out.println(n);
            for (float[] q : c.cars) out.println(String.format(Locale.ROOT, "car %.2f,%.2f %.2f,%.2f %.2f,%.2f %.2f,%.2f", q[0], q[1], q[2], q[3], q[4], q[5], q[6], q[7]));
            out.println(String.format(Locale.ROOT, "# main-thread frames=%d meanMs=%.3f maxMs=%.3f", c.frames, c.totalNanos / 1e6 / Math.max(1, c.frames), c.maxNanos / 1e6));
        } catch (IOException e) {
            System.out.println("[SolPerception] could not write: " + e);
            return;
        }
        byte[] img = rasterize(c.shapes, size, c.cars, originX, originY);
        int n = size * CELLS_PER_TILE;
        try (BufferedOutputStream out = new BufferedOutputStream(new FileOutputStream(stem + ".pgm"))) {
            out.write(("P5\n" + n + " " + n + "\n255\n").getBytes(StandardCharsets.US_ASCII));
            out.write(img);
        } catch (IOException e) {
            System.out.println("[SolPerception] could not write the picture: " + e);
            return;
        }
        System.out.println(String.format(Locale.ROOT, "[SolPerception] wrote %s (%s): frames=%d meanMs=%.3f maxMs=%.3f", stem, c.reason, c.frames, c.totalNanos / 1e6 / Math.max(1, c.frames), c.maxNanos / 1e6));
    }
}

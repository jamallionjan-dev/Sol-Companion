package localplayerbody;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import me.zed_0xff.zombie_buddy.Exposer;
import se.krka.kahlua.integration.annotations.LuaMethod;
import zombie.core.Core;
import zombie.iso.IsoCell;
import zombie.iso.IsoGridSquare;
import zombie.iso.IsoObject;
import zombie.iso.IsoWorld;
import zombie.iso.sprite.IsoSprite;

/**
 * Remembers every fuel pump seen near the player or Sol. The game's own test for a pump is getPipedFuelAmount() > 0.
 * Sweeps in slices of at most 0.15 ms, one sweep every 3 s; the file is read and written on a worker thread.
 */
@Exposer.LuaClass
public final class SolStations {
    private static final long SWEEP_GAP_MS = 3_000L;
    private static final SolNavCost COST = new SolNavCost("stations", 150_000L);
    private static final int RADIUS = 30, SAME_STATION = 15;

    static final class Pump {
        final int x, y; int fuel; String brand;
        Pump(int x, int y, int fuel, String brand) { this.x = x; this.y = y; this.fuel = fuel; this.brand = brand; }
    }

    private static final Map<Long, Pump> PUMPS = new HashMap<>();
    private static final Map<Long, int[]> GARDENS = new HashMap<>();
    private static final int GARDEN_BIN = 8, MAX_GARDENS = 3000;
    private static volatile List<int[]> pendingGardens;
    private static volatile List<Pump> pendingLoad;
    private static String save;
    private static boolean sweeping, dirty, otherTurn;
    private static int originX, originY, nextX, nextY;
    private static double playerX = Double.NaN, playerY, solX = Double.NaN, solY;
    private static long nextSweep;

    private SolStations() {}

    private static long key(int x, int y) { return ((long) x << 32) | (y & 0xffffffffL); }

    static String brandOf(String sprite) {
        if (sprite == null || !sprite.startsWith("location_shop_")) return "";
        int from = "location_shop_".length(), to = sprite.indexOf('_', from);
        return to > from ? sprite.substring(from, to) : "";
    }

    private static File file(String world) {
        String safe = world.replaceAll("[^A-Za-z0-9_-]", "_");
        return new File(System.getProperty("user.home") + File.separator + "Zomboid" + File.separator + "Lua" + File.separator + "SolStations_" + safe + ".txt");
    }

    private static void beginWorld(String world) {
        save = world;
        PUMPS.clear();
        GARDENS.clear();
        sweeping = false;
        File f = file(world);
        Thread t = new Thread(() -> pendingLoad = read(f), "SolStations-load");
        t.setDaemon(true);
        t.start();
    }

    static List<Pump> read(File f) {
        List<Pump> out = new ArrayList<>();
        List<int[]> gardens = new ArrayList<>();
        if (!f.isFile()) return out;
        try (BufferedReader r = new BufferedReader(new FileReader(f, StandardCharsets.UTF_8))) {
            for (String s = r.readLine(); s != null; s = r.readLine()) {
                String[] a = s.split(",", -1);
                if (a.length == 3 && "G".equals(a[0])) {
                    try { gardens.add(new int[] { Integer.parseInt(a[1]), Integer.parseInt(a[2]) }); }
                    catch (NumberFormatException e) { /* a damaged line costs only that garden */ }
                    continue;
                }
                if (a.length < 4) continue;
                try { out.add(new Pump(Integer.parseInt(a[0]), Integer.parseInt(a[1]), Integer.parseInt(a[2]), a[3])); }
                catch (NumberFormatException e) { /* a damaged line costs only that pump */ }
            }
        } catch (IOException e) {
            System.out.println("[SolStations] could not read: " + e);
        }
        pendingGardens = gardens;
        return out;
    }

    private static void saveNow() {
        dirty = false;
        StringBuilder b = new StringBuilder();
        for (Pump p : PUMPS.values()) b.append(p.x).append(',').append(p.y).append(',').append(p.fuel).append(',').append(p.brand).append('\n');
        for (int[] g : GARDENS.values()) b.append("G,").append(g[0]).append(',').append(g[1]).append('\n');
        String text = b.toString();
        File f = file(save);
        Thread t = new Thread(() -> {
            try (PrintWriter o = new PrintWriter(f, StandardCharsets.UTF_8)) { o.print(text); }
            catch (IOException e) { System.out.println("[SolStations] could not write: " + e); }
        }, "SolStations-save");
        t.setDaemon(true);
        t.start();
    }

    /** Where to look: the player, and Sol when she is elsewhere. Pass NaN for someone who is not there. */
    @LuaMethod(name = "solStationsCentre", global = true)
    public static void centre(double px, double py, double sx, double sy) { playerX = px; playerY = py; solX = sx; solY = sy; }

    /** One sliver of a sweep. Does next to nothing between sweeps. */
    @LuaMethod(name = "solStationsStep", global = true)
    public static void step() {
        if (IsoWorld.instance == null || IsoWorld.instance.getCell() == null) return;
        String world = Core.gameSaveWorld;
        if (world == null || world.isEmpty()) return;
        if (!world.equals(save)) beginWorld(world);
        List<Pump> loaded = pendingLoad;
        if (loaded != null) {
            pendingLoad = null;
            for (Pump p : loaded) PUMPS.putIfAbsent(key(p.x, p.y), p);
        }
        List<int[]> grown = pendingGardens;
        if (grown != null) {
            pendingGardens = null;
            for (int[] g : grown) GARDENS.putIfAbsent(key(g[0] >> 3, g[1] >> 3), g);
        }
        long t0 = System.nanoTime();
        if (!sweeping) {
            long now = System.currentTimeMillis();
            if (now < nextSweep) return;
            boolean useSol = otherTurn && !Double.isNaN(solX);
            otherTurn = !otherTurn;
            double cx = useSol ? solX : playerX, cy = useSol ? solY : playerY;
            if (Double.isNaN(cx)) { nextSweep = now + SWEEP_GAP_MS; return; }
            originX = (int) Math.floor(cx) - RADIUS; originY = (int) Math.floor(cy) - RADIUS;
            nextX = 0; nextY = 0; sweeping = true;
        }
        IsoCell cell = IsoWorld.instance.getCell();
        int size = 2 * RADIUS + 1;
        try {
            while (nextY < size) {
                visit(cell.getGridSquare(originX + nextX, originY + nextY, 0), originX + nextX, originY + nextY);
                if (++nextX >= size) { nextX = 0; nextY++; }
                if (System.nanoTime() - t0 >= COST.slice()) break;
            }
        } catch (RuntimeException e) {
            System.out.println("[SolStations] sweep stopped: " + e);
            nextY = size;
        }
        COST.note(System.nanoTime() - t0);
        if (nextY >= size) {
            sweeping = false;
            nextSweep = System.currentTimeMillis() + SWEEP_GAP_MS;
            if (dirty) saveNow();
        }
    }

    private static void visit(IsoGridSquare sq, int x, int y) {
        if (sq == null) return;
        java.util.List<IsoObject> objects = sq.getObjects();          // its iterator throws UnsupportedOperationException
        Pump known = PUMPS.isEmpty() ? null : PUMPS.get(key(x, y));
        boolean found = false;
        for (int i = 0, n = objects.size(); i < n; i++) {
            IsoObject o = objects.get(i);
            IsoSprite look = o.getSprite();
            if (look != null && isGardenSprite(look.getName())) noteGarden(x, y);
            int fuel = o.getPipedFuelAmount();
            if (fuel <= 0) continue;
            found = true;
            IsoSprite s = o.getSprite();
            String brand = brandOf(s == null ? null : s.getName());
            if (known == null) { PUMPS.put(key(x, y), new Pump(x, y, fuel, brand)); dirty = true; }
            else if (known.fuel != fuel) { known.fuel = fuel; dirty = true; }
            break;
        }
        if (!found && known != null && known.fuel != 0) { known.fuel = 0; dirty = true; }     // pumped dry or gone
    }

    /** Crops and vegetable beds, as the game's own tile names call them. */
    static boolean isGardenSprite(String name) { return name != null && (name.startsWith("vegetation_farm") || name.startsWith("vegetation_gardening")); }

    static void noteGarden(int x, int y) {
        if (GARDENS.size() >= MAX_GARDENS || GARDENS.containsKey(key(x >> 3, y >> 3))) return;
        GARDENS.put(key(x >> 3, y >> 3), new int[] { x, y });
        dirty = true;
    }

    /** Gardens and crop fields she has been near, nearest first: "x,y;x,y". */
    @LuaMethod(name = "solStationsGardens", global = true)
    public static String gardens(double x, double y, double n) {
        List<int[]> all = new ArrayList<>(GARDENS.values());
        all.sort((a, b) -> Double.compare((a[0] - x) * (a[0] - x) + (a[1] - y) * (a[1] - y), (b[0] - x) * (b[0] - x) + (b[1] - y) * (b[1] - y)));
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < Math.min(all.size(), (int) n); i++) { if (i > 0) out.append(';'); out.append(all.get(i)[0]).append(',').append(all.get(i)[1]); }
        return out.toString();
    }

    /** For tests. */
    static void remember(int x, int y, int fuel, String brand) { PUMPS.put(key(x, y), new Pump(x, y, fuel, brand)); }

    /** Every pump with fuel at the station around this point, as {x, y}. Game thread. */
    static List<double[]> pumpsOfStation(double x, double y) {
        List<double[]> out = new ArrayList<>();
        for (Pump p : PUMPS.values()) if (p.fuel > 0 && Math.abs(p.x - x) <= SAME_STATION && Math.abs(p.y - y) <= SAME_STATION) out.add(new double[] { p.x, p.y });
        return out;
    }

    /** The nearest remembered pump with fuel: "x,y,fuel,brand", or "" when none is known. */
    @LuaMethod(name = "solStationsNearest", global = true)
    public static String nearest(double x, double y) {
        Pump best = null;
        double bd = Double.MAX_VALUE;
        for (Pump p : PUMPS.values()) {
            if (p.fuel <= 0) continue;
            double d = (p.x - x) * (p.x - x) + (p.y - y) * (p.y - y);
            if (d < bd) { bd = d; best = p; }
        }
        if (best == null) return "";
        String brand = best.brand;
        if (brand.isEmpty()) for (Pump p : PUMPS.values()) if (!p.brand.isEmpty() && Math.abs(p.x - best.x) <= SAME_STATION && Math.abs(p.y - best.y) <= SAME_STATION) { brand = p.brand; break; }
        return best.x + "," + best.y + "," + best.fuel + "," + brand;
    }

    /** The closest stations with fuel, one entry per station: "x,y,fuel,brand;..." where x,y is that station's nearest working pump. Pumps within 15 tiles are one station. */
    @LuaMethod(name = "solStationsTop", global = true)
    public static String top(double x, double y, double n) {
        List<Pump> working = new ArrayList<>();
        for (Pump p : PUMPS.values()) if (p.fuel > 0) working.add(p);
        working.sort((a, b) -> Double.compare((a.x - x) * (a.x - x) + (a.y - y) * (a.y - y), (b.x - x) * (b.x - x) + (b.y - y) * (b.y - y)));
        List<Pump> stations = new ArrayList<>();
        StringBuilder out = new StringBuilder();
        for (Pump p : working) {
            boolean seen = false;
            for (Pump s : stations) if (Math.abs(s.x - p.x) <= SAME_STATION && Math.abs(s.y - p.y) <= SAME_STATION) { seen = true; break; }
            if (seen) continue;
            stations.add(p);
            String brand = p.brand;
            if (brand.isEmpty()) for (Pump q : PUMPS.values()) if (!q.brand.isEmpty() && Math.abs(q.x - p.x) <= SAME_STATION && Math.abs(q.y - p.y) <= SAME_STATION) { brand = q.brand; break; }
            if (out.length() > 0) out.append(';');
            out.append(p.x).append(',').append(p.y).append(',').append(p.fuel).append(',').append(brand);
            if (stations.size() >= (int) n) break;
        }
        return out.toString();
    }

    /** Her memory of every station, gone: what dying costs her. */
    @LuaMethod(name = "solStationsForget", global = true)
    public static void forget() {
        PUMPS.clear();
        GARDENS.clear();
        sweeping = false;
        if (save != null) saveNow();
    }

    /** How many pumps are remembered in this world. */
    @LuaMethod(name = "solStationsCount", global = true)
    public static double count() { return PUMPS.size(); }

    /** The live pump object nearest this point within the radius, or null. Looks only at remembered pumps. */
    @LuaMethod(name = "solStationsPumpAt", global = true)
    public static IsoObject pumpAt(double x, double y, double radius) {
        if (IsoWorld.instance == null || IsoWorld.instance.getCell() == null) return null;
        IsoCell cell = IsoWorld.instance.getCell();
        IsoObject best = null;
        double bd = radius * radius;
        for (Pump p : PUMPS.values()) {
            double d = (p.x + 0.5 - x) * (p.x + 0.5 - x) + (p.y + 0.5 - y) * (p.y + 0.5 - y);
            if (d > bd) continue;
            IsoGridSquare sq = cell.getGridSquare(p.x, p.y, 0);
            if (sq == null) continue;
            java.util.List<IsoObject> objects = sq.getObjects();
            for (int i = 0, n = objects.size(); i < n; i++) {
                IsoObject o = objects.get(i);
                if (o.getPipedFuelAmount() > 0) { best = o; bd = d; break; }
            }
        }
        return best;
    }
}

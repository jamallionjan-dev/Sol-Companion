package localplayerbody;

import java.util.ArrayList;
import java.util.List;

/** Parking at made-up stations: one to four pumps, in a row or on islands, some taken by parked cars, with vehicles whose fuel cap is on either side or at the back. */
public final class SolNavParkTest {
    static final int TILES = 60;
    static int fails, runs;

    static void box(boolean[] o, double x0, double y0, double x1, double y1) {
        int n = TILES * 10;
        for (int y = (int) Math.round(y0 * 10); y < Math.round(y1 * 10); y++) for (int x = (int) Math.round(x0 * 10); x < Math.round(x1 * 10); x++) o[y * n + x] = true;
    }

    static final class Vehicle {
        final String name; final double hl, hw, wb, a, b;
        Vehicle(String name, double hl, double hw, double wb, double a, double b) { this.name = name; this.hl = hl; this.hw = hw; this.wb = wb; this.a = a; this.b = b; }
        SolNavPlanner.Car car() { return new SolNavPlanner.Car(hl, hw, wb, 1 / 4.8 * 0.7, 0.05); }
    }

    static final class Layout {
        final String name; final List<double[]> pumps = new ArrayList<>(); final List<double[]> parked = new ArrayList<>(); boolean island;
        Layout(String name) { this.name = name; }
        Layout pump(double x, double y) { pumps.add(new double[] { x, y }); return this; }
        Layout car(double cx, double cy) { parked.add(new double[] { cx, cy }); return this; }
        Layout onIslands() { island = true; return this; }
    }

    static float[] poly(double cx, double cy) { float x0 = (float) (cx - 0.9), x1 = (float) (cx + 0.9), y0 = (float) (cy - 2.3), y1 = (float) (cy + 2.3); return new float[] { x0, y0, x1, y0, x1, y1, x0, y1 }; }

    static boolean[] world(Layout l) {
        boolean[] o = new boolean[TILES * 10 * TILES * 10];
        for (double[] p : l.pumps) { if (l.island) box(o, p[0] - 1, p[1], p[0] + 2, p[1] + 1); else box(o, p[0], p[1], p[0] + 1, p[1] + 1); }
        for (double[] c : l.parked) box(o, c[0] - 0.9, c[1] - 2.3, c[0] + 0.9, c[1] + 2.3);
        return o;
    }

    static void check(String name, boolean ok, String detail) {
        runs++;
        if (!ok) fails++;
        System.out.printf("%s %-62s %s%n", ok ? "PASS" : "FAIL", name, detail);
    }

    static void scene(Layout l, Vehicle v, double sx, double sy, double sth) {
        boolean[] o = world(l);
        SolNavPlanner.Grid g = new SolNavPlanner.Grid(TILES * 10, TILES * 10, 0, 0, o);
        SolNavPlanner.Car car = v.car();
        List<float[]> cars = new ArrayList<>();
        for (double[] c : l.parked) cars.add(poly(c[0], c[1]));
        List<SolNavPark.Spot> spots = SolNavPark.stationSpots(g, car, v.hl, v.hw, v.wb, l.pumps, cars, Double.NaN, Double.NaN, v.a, v.b, sx, sy, sth);
        String name = l.name + " / " + v.name;
        boolean anyFree = false;
        for (double[] p : l.pumps) if (!SolNavPark.occupied(p[0], p[1], cars, Double.NaN, Double.NaN)) anyFree = true;
        SolNavPlanner.Result r = SolNavPark.plan(g, car, spots, v.wb, sx, sy, sth);
        if (r.path == null) { check(name, false, spots.size() + " spots, no plan: " + r.why); return; }
        SolNavPlanner.Pose end = r.path.get(r.path.size() - 1);
        double c = Math.cos(end.th), s = Math.sin(end.th), cx = end.x + c * v.wb / 2, cy = end.y + s * v.wb / 2;
        double capX = cx + c * v.a - s * v.b, capY = cy + s * v.a + c * v.b;
        double[] used = null;
        for (double[] p : l.pumps) if (Math.abs(Math.floor(capX) - p[0]) <= 2 && Math.abs(Math.floor(capY) - p[1]) <= 2) { if (used == null || Math.hypot(capX - p[0] - .5, capY - p[1] - .5) < Math.hypot(capX - used[0] - .5, capY - used[1] - .5)) used = p; }
        boolean valid = SolNavPlanner.validate(g, car, r.path);
        if (!valid) for (int i = 0; i < r.path.size(); i++) { List<SolNavPlanner.Pose> one = new ArrayList<>(); one.add(r.path.get(i)); if (!SolNavPlanner.validate(g, car, one)) { SolNavPlanner.Pose q = r.path.get(i); System.out.printf("     first pose in contact: %d of %d, %.2f,%.2f th %.0f dir %d%n", i, r.path.size(), q.x, q.y, Math.toDegrees(q.th), q.dir); break; } }
        boolean free = used != null && !SolNavPark.occupied(used[0], used[1], cars, Double.NaN, Double.NaN);
        double[] nearest = null;
        for (double[] p : l.pumps) if (!SolNavPark.occupied(p[0], p[1], cars, Double.NaN, Double.NaN) && (nearest == null || Math.hypot(p[0] + .5 - sx, p[1] + .5 - sy) < Math.hypot(nearest[0] + .5 - sx, nearest[1] + .5 - sy))) nearest = p;
        boolean nearestFree = nearest == null || (used != null && used[0] == nearest[0] && used[1] == nearest[1]);
        check(name, valid && used != null && (free || !anyFree) && nearestFree, used == null ? "fuel cap is not within the game's two squares of a pump" : String.format(java.util.Locale.ROOT, "pump %d,%d%s, cap %.1f from it, heading %.0f, valid=%s, %.0f ms", (int) used[0], (int) used[1], free ? "" : " (all taken)", Math.hypot(capX - used[0] - .5, capY - used[1] - .5), Math.toDegrees(end.th), valid, r.ms));
    }

    public static void main(String[] a) {
        Vehicle[] vehicles = {
            new Vehicle("van, cap on the right", 2.12, 0.845, 2.56, -1.2, -1.1),
            new Vehicle("van, cap on the left", 2.12, 0.845, 2.56, -1.2, 1.1),
            new Vehicle("sedan, cap on the left, forward of the axle", 1.9, 0.8, 2.4, 0.4, 1.05),
            new Vehicle("pickup, cap at the back", 2.4, 0.9, 2.9, -2.65, 0.0),
        };
        List<Layout> layouts = new ArrayList<>();
        layouts.add(new Layout("1 pump").pump(30, 30));
        layouts.add(new Layout("1 pump on an island").pump(30, 30).onIslands());
        layouts.add(new Layout("2 pumps in a row").pump(26, 30).pump(34, 30));
        layouts.add(new Layout("2 pumps, nearest taken").pump(26, 24).pump(34, 36).car(23.5, 24));
        layouts.add(new Layout("4 pumps, two islands").pump(24, 28).pump(24, 36).pump(36, 28).pump(36, 36).onIslands());
        layouts.add(new Layout("4 pumps, two taken").pump(24, 28).pump(24, 40).pump(38, 28).pump(38, 40).onIslands().car(21, 28).car(41, 28));
        layouts.add(new Layout("4 pumps, three taken").pump(24, 28).pump(24, 40).pump(38, 28).pump(38, 40).onIslands().car(21, 28).car(41, 28).car(21, 40));
        layouts.add(new Layout("1 pump, car on its far side, all taken").pump(30, 30).car(33, 30));
        for (Layout l : layouts) for (Vehicle v : vehicles) scene(l, v, 30, 8, Math.PI / 2);
        for (Vehicle v : vehicles) scene(new Layout("2 pumps, coming from the other end").pump(26, 30).pump(34, 30), v, 30, 52, -Math.PI / 2);
        for (Vehicle v : vehicles) scene(new Layout("2 pumps, arriving side-on").pump(26, 30).pump(26, 40), v, 50, 34, Math.PI);

        // every pump keeps a stop on its far side
        boolean[] open = new boolean[TILES * 10 * TILES * 10];
        SolNavPlanner.Grid og = new SolNavPlanner.Grid(TILES * 10, TILES * 10, 0, 0, open);
        Vehicle van = vehicles[0];
        List<double[]> single = new ArrayList<>(); single.add(new double[] { 30, 30 });
        List<SolNavPark.Spot> around = SolNavPark.stationSpots(og, van.car(), van.hl, van.hw, van.wb, single, new ArrayList<>(), Double.NaN, Double.NaN, van.a, van.b, 30, 8, Math.PI / 2);
        boolean opposite = false;
        for (SolNavPark.Spot q : around) if (Math.abs(Math.atan2(Math.sin(q.th - around.get(0).th), Math.cos(q.th - around.get(0).th))) > Math.toRadians(170)) opposite = true;
        check("the far side of a pump is always among the stops", opposite, around.size() + " stops");

        // the choice alone
        List<float[]> one = new ArrayList<>(); one.add(poly(23.5, 24));
        boolean[] o = new boolean[TILES * 10 * TILES * 10];
        SolNavPlanner.Grid g = new SolNavPlanner.Grid(TILES * 10, TILES * 10, 0, 0, o);
        Vehicle v = vehicles[0];
        List<double[]> two = new ArrayList<>(); two.add(new double[] { 26, 24 }); two.add(new double[] { 34, 36 });
        List<SolNavPark.Spot> sp = SolNavPark.stationSpots(g, v.car(), v.hl, v.hw, v.wb, two, one, Double.NaN, Double.NaN, v.a, v.b, 26, 10, Math.PI / 2);
        check("taken pump comes after a free one, though it is nearer", !sp.isEmpty() && sp.get(0).px == 34, sp.isEmpty() ? "none" : "first pump x=" + sp.get(0).px);
        sp = SolNavPark.stationSpots(g, v.car(), v.hl, v.hw, v.wb, two, new ArrayList<>(), Double.NaN, Double.NaN, v.a, v.b, 26, 10, Math.PI / 2);
        check("with both free the nearer one is first", !sp.isEmpty() && sp.get(0).px == 26, sp.isEmpty() ? "none" : "first pump x=" + sp.get(0).px);
        sp = SolNavPark.stationSpots(g, v.car(), v.hl, v.hw, v.wb, two, new ArrayList<>(), 27, 25, v.a, v.b, 26, 10, Math.PI / 2);
        check("a pump the player is standing at counts as taken", !sp.isEmpty() && sp.get(0).px == 34, sp.isEmpty() ? "none" : "first pump x=" + sp.get(0).px);
        check("a car three tiles off the pump's side takes it", SolNavPark.occupied(26, 24, one, Double.NaN, Double.NaN), "");
        List<float[]> far = new ArrayList<>(); far.add(poly(40, 40));
        check("a car across the forecourt does not", !SolNavPark.occupied(26, 24, far, Double.NaN, Double.NaN), "");
        for (Vehicle w : vehicles) for (SolNavPark.Spot q : SolNavPark.stationSpots(g, w.car(), w.hl, w.hw, w.wb, two, new ArrayList<>(), Double.NaN, Double.NaN, w.a, w.b, 26, 10, Math.PI / 2)) {
            double c = Math.cos(q.th), s = Math.sin(q.th), capX = q.cx + c * w.a - s * w.b, capY = q.cy + s * w.a + c * w.b;
            if (Math.abs(Math.floor(capX) - q.px) > 2 || Math.abs(Math.floor(capY) - q.py) > 2) { check("every spot puts the cap within the game's reach: " + w.name, false, capX + "," + capY); break; }
        }
        System.out.println("SUMMARY " + (fails == 0 ? "ALL PASS" : "FAILED " + fails) + " of " + runs);
        System.exit(fails == 0 ? 0 : 1);
    }
}

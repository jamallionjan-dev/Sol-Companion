package localplayerbody;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * s95b evidence: replays the three solNavPlan calls of the 10:26 lab run (SolStationSurvey poses 1-3) through the
 * shipped planner exactly as SolNav.plan/submit set them up (centre -> rear axle, capture square, PAD 0.05, kFull*0.93*0.7,
 * planSafe with mayTurnBack false, 2 s budget), on the forecourt read from the lab's perception dumps:
 *   args: dumpA dumpB [mode]   (dumpA = SolPerception_1794389185383.txt, the car standing where the plans started;
 *                               dumpB = SolPerception_1794389223475.txt, the forecourt right after)
 * The own car (first poly of dumpA, the one the dump is centred on) is left out as SolNav does.
 * Start: the car's centre and heading from its poly (it came north up the road from y 8234 to 8179: the 10:26:05 dump).
 * mode "old": the 10:26 handoff (planSafe, forward-arc limit).  mode "turnback": the same with mayTurnBack (solNavMayTurnBack).
 * mode "twoleg": approach points beside each pose's lane end, then the pose.  mode "serve": legs from stdin, for test_s95b.
 * Not modelled: the game's off-road soft cost and navShapeOf's extra solids (no floor, rooms), which the dump does not keep.
 * Build: javac -d OUT SolNavPlanner.java SolNavTrack.java S95bPlanReplay.java  (sources in 05_TOOLS/sol_nav_java/localplayerbody)
 */
public final class S95bPlanReplay {
    static final Map<Long, Integer> SHAPES = new HashMap<>();
    static final List<float[]> CARS = new ArrayList<>();
    static float[] own;

    static long k(int x, int y) { return ((long) x << 32) ^ (y & 0xffffffffL); }

    static void read(String file, boolean first) throws Exception {
        try (BufferedReader r = new BufferedReader(new FileReader(file))) {
            String line; boolean ownTaken = false;
            while ((line = r.readLine()) != null) {
                if (line.startsWith("#")) continue;
                if (line.startsWith("car ")) {
                    String[] p = line.substring(4).trim().split("[ ,]");
                    float[] q = new float[8];
                    for (int i = 0; i < 8; i++) q[i] = Float.parseFloat(p[i]);
                    if (first && !ownTaken) { own = q; ownTaken = true; continue; }
                    if (!first) {
                        boolean dup = Math.abs(q[0] - own[0]) < 0.3 && Math.abs(q[1] - own[1]) < 0.3;
                        for (float[] c : CARS) if (Math.abs(c[0] - q[0]) < 0.3 && Math.abs(c[1] - q[1]) < 0.3) dup = true;
                        if (!dup) CARS.add(q);
                    } else CARS.add(q);
                    continue;
                }
                String[] f = line.split(",");
                if (f.length < 3) continue;
                try { SHAPES.merge(k(Integer.parseInt(f[0]), Integer.parseInt(f[1])), Integer.parseInt(f[2]), (a, b) -> a | b); } catch (NumberFormatException e) { }
            }
        }
    }

    /** SolPerception.rasterize, copied (that class needs the game on the classpath). */
    static boolean inside(float[] q, double x, double y) {
        boolean in = false;
        for (int i = 0, j = 3; i < 4; j = i++) {
            double xi = q[2 * i], yi = q[2 * i + 1], xj = q[2 * j], yj = q[2 * j + 1];
            if ((yi > y) != (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) in = !in;
        }
        return in;
    }
    static boolean[] raster(int[] shapes, int size, int ox, int oy) {
        int n = size * 10;
        boolean[] occ = new boolean[n * n];
        for (int py = 0; py < n; py++) for (int px = 0; px < n; px++) {
            int s = shapes[(py / 10) * size + px / 10];
            double fx = (px % 10 + 0.5) / 10, fy = (py % 10 + 0.5) / 10;
            boolean v = s < 0 || (s & 1) != 0 || ((s & 2) != 0 && (fx - 0.5) * (fx - 0.5) + (fy - 0.5) * (fy - 0.5) <= 0.1225)
                || ((s & 4) != 0 && fy < 0.13) || ((s & 8) != 0 && fx < 0.13);
            if (!v) { double wx = ox + (px + 0.5) / 10, wy = oy + (py + 0.5) / 10; for (float[] c : CARS) if (inside(c, wx, wy)) { v = true; break; } }
            occ[py * n + px] = v;
        }
        return occ;
    }

    /** SolNav.plan + submit, offline. Returns the planner's why, or "found". */
    public static String replay(double sx, double sy, double hx, double hy, double gx, double gy, double ghx, double ghy, double wb, double kFullLock, double length, double width, boolean mayTurnBack) {
        int radius = (int) Math.ceil(Math.max(Math.abs(gx - sx), Math.abs(gy - sy)) / 2) + 12;
        if (radius > 35) return "goal_too_far";
        int mx = (int) Math.floor((sx + gx) / 2), my = (int) Math.floor((sy + gy) / 2);
        int ox = mx - radius, oy = my - radius, size = 2 * radius + 1;
        int[] shapes = new int[size * size];
        for (int y = 0; y < size; y++) for (int x = 0; x < size; x++) shapes[y * size + x] = SHAPES.getOrDefault(k(ox + x, oy + y), 0);
        double half = wb / 2, n = Math.hypot(hx, hy), gn = Math.hypot(ghx, ghy);
        double csx = sx - hx / n * half, csy = sy - hy / n * half, sth = Math.atan2(hy, hx);
        double cgx = gx - ghx / gn * half, cgy = gy - ghy / gn * half, gth = Math.atan2(ghy, ghx);
        double kFull = kFullLock * 0.93;
        SolNavPlanner.Grid grid = new SolNavPlanner.Grid(size * 10, size * 10, ox, oy, raster(shapes, size, ox, oy));
        SolNavPlanner.Car car = new SolNavPlanner.Car(length / 2, width / 2, wb, kFull * 0.7, 0.05);
        SolNavPlanner.Result r = SolNavPlanner.planSafe(grid, car, csx, csy, sth, cgx, cgy, gth, 2_000_000_000L, mayTurnBack);
        return r.path != null ? String.format(Locale.ROOT, "found (%d poses, %d nodes, %.0f ms, reverse %.1f m)", r.path.size(), r.nodes, r.ms, reverse(r.path)) : r.why + String.format(Locale.ROOT, " (%d nodes, %.0f ms)", r.nodes, r.ms);
    }
    static double reverse(List<SolNavPlanner.Pose> p) { double m = 0; for (int i = 1; i < p.size(); i++) if (p.get(i).dir < 0) m += Math.hypot(p.get(i).x - p.get(i - 1).x, p.get(i).y - p.get(i - 1).y); return m; }

    public static void main(String[] a) throws Exception {
        read(a[0], true);
        read(a[1], false);
        String mode = a.length > 2 ? a[2] : "old";
        double cx = (own[0] + own[2] + own[4] + own[6]) / 4, cy = (own[1] + own[3] + own[5] + own[7]) / 4;
        double length = Math.hypot(own[4] - own[2], own[5] - own[3]), width = Math.hypot(own[2] - own[0], own[3] - own[1]);
        double wb = 1.94, kmax = Math.tan(0.86) / 1.94;                  // "[SolBypass] measured the car: ... wheelbase 1.94, steering lock 0.86"
        // came north up the road (y 8234 at 10:26:05, 8179 at 10:26:25): the front is the poly's low-y end (p1, p2)
        double hx = (own[0] + own[2] - own[4] - own[6]) / 2, hy = (own[1] + own[3] - own[5] - own[7]) / 2, hn = Math.hypot(hx, hy);
        hx /= hn; hy /= hn;
        if (mode.equals("serve")) {                                      // for the Lua test: one leg per stdin line "sx sy hx hy gx gy ghx ghy turnBack" -> "found ..." / why
            BufferedReader in = new BufferedReader(new java.io.InputStreamReader(System.in));
            String line;
            while ((line = in.readLine()) != null) {
                String[] f = line.trim().split("\\s+");
                if (f.length < 9) { System.out.println("bad_line"); System.out.flush(); continue; }
                double[] v = new double[8];
                for (int i = 0; i < 8; i++) v[i] = Double.parseDouble(f[i]);
                System.out.println(replay(v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], wb, kmax, length, width, f[8].equals("1")));
                System.out.flush();
            }
            return;
        }
        if (a.length > 4) { double[] st = java.util.Arrays.stream(a[4].split(",")).mapToDouble(Double::parseDouble).toArray(); cx = st[0]; cy = st[1]; hx = st[2]; hy = st[3]; }
        // the three poses as SolStationSurvey logged them (pose: centre, facing)
        double[][] poses = { { 7307.3, 8181.0, -1, 0 }, { 7315.3, 8181.0, -1, 0 }, { 7311.0, 8180.7, 0, 1 } };
        if (a.length > 3 && !a[3].equals("-")) poses = new double[][] { java.util.Arrays.stream(a[3].split(",")).mapToDouble(Double::parseDouble).toArray() };
        System.out.printf(Locale.ROOT, "car centre %.2f,%.2f heading %.3f,%.3f,%.2f x %.2f, %d other cars, mode %s%n", cx, cy, hx, hy, length, width, CARS.size(), mode);
        if (mode.equals("twoleg")) {                                     // the s95b handoff: an approach point first, then the pose
            for (int i = 0; i < poses.length; i++) {
                double[] p = poses[i];
                double ll = Math.min(length / 2, 3.0);
                for (double back : new double[] { length / 2 + ll, -(length / 2 + ll) }) for (double s : new double[] { 2.5, -2.5, 4, -4, 0 }) {
                    double ax = p[0] - p[2] * back - p[3] * s, ay = p[1] - p[3] * back + p[2] * s;      // l = (-fy, fx)
                    double dx = ax - cx, dy = ay - cy, dn = Math.hypot(dx, dy);
                    String l1 = replay(cx, cy, hx, hy, ax, ay, dx / dn, dy / dn, wb, kmax, length, width, false);
                    String l2 = l1.startsWith("found") ? replay(ax, ay, dx / dn, dy / dn, p[0], p[1], p[2], p[3], wb, kmax, length, width, back < 0) : "-";
                    System.out.printf(Locale.ROOT, "pose %d %s via %.1f,%.1f facing %.2f,%.2f (side %+.1f): leg1 %s | leg2 %s%n", i + 1, back > 0 ? "behind" : "ahead", ax, ay, dx / dn, dy / dn, s, l1, l2);
                }
            }
            return;
        }
        for (int i = 0; i < poses.length; i++) {
            double[] p = poses[i];
            String why = replay(cx, cy, hx, hy, p[0], p[1], p[2], p[3], wb, kmax, length, width, mode.equals("turnback"));
            System.out.printf(Locale.ROOT, "pose %d: centre %.1f,%.1f facing %.0f,%.0f -> %s%n", i + 1, p[0], p[1], p[2], p[3], why);
        }
    }
}

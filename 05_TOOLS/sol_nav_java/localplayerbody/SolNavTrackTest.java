package localplayerbody;

import java.nio.file.*;
import java.util.*;

/** Plans, then drives the plan frame by frame on a car model with steering lag and a turning circle wider than the tracker assumes. args: [real-dir] */
public final class SolNavTrackTest {
    static final int TILES = 60;
    static final double WB = 2.56, KFULL = 0.40, UP = Math.PI / 2;
    static final SolNavPlanner.Car VAN = new SolNavPlanner.Car(2.12, 0.845, WB, KFULL * 0.7, 0.05);
    static final SolNavPlanner.Car BODY = new SolNavPlanner.Car(2.12, 0.845, WB, KFULL * 0.7, 0.0);
    static int fails;
    static int WORLD_SIGN = 1;
    static double IGNORE_FIRST = 0, START_STEER = 0;

    static boolean[] blank() { return new boolean[TILES * 10 * TILES * 10]; }
    static void box(boolean[] o, int x0, int y0, int x1, int y1) { for (int y = y0 * 10; y < y1 * 10; y++) for (int x = x0 * 10; x < x1 * 10; x++) o[y * TILES * 10 + x] = true; }

    static void drive(String name, SolNavPlanner.Grid g, double sx, double sy, double sth, double gx, double gy, double gth, boolean printAll) {
        SolNavPlanner.Result r = SolNavPlanner.plan(g, VAN, sx, sy, sth, gx, gy, gth, 5_000_000_000L);
        if (r.path == null) { fails++; System.out.printf("FAIL %-44s no plan: %s%n", name, r.why); return; }
        run(name, g, SolNavPlanner.smooth(g, VAN, r.path), sx, sy, sth, gx, gy, 0, 0);
    }

    /** startKmh and behind: the car is rolling and short of where the path begins. */
    static void run(String name, SolNavPlanner.Grid g, List<SolNavPlanner.Pose> p, double sx, double sy, double sth, double gx, double gy, double startKmh, double behind) {
        boolean wasClear = false;
        sx -= Math.cos(sth) * behind; sy -= Math.sin(sth) * behind;
        if (System.getProperty("dbg", "").length() > 0 && name.contains(System.getProperty("dbg"))) { StringBuilder b = new StringBuilder("   path dir changes:"); for (int k = 1; k < p.size(); k++) if (p.get(k).dir != p.get(k-1).dir) b.append(" ").append(k); b.append(" first ").append(String.format("%.2f,%.2f,%.1f dir %d", p.get(0).x, p.get(0).y, Math.toDegrees(p.get(0).th), p.get(0).dir)); System.out.println(b); }
        SolNavTrack t = new SolNavTrack(p, SolNavPlanner.speeds(g, VAN, p), WB, KFULL);
        SolNavTrack.Out o = new SolNavTrack.Out();
        double x = sx, y = sy, th = sth, kmh = startKmh, steer = START_STEER, dt = 1 / 30.0, minGap = 1e9, maxLat = 0, driven = 0, topSpeed = 0, worst = 0;
        long now = 1000;
        String end = null;
        double[] dtTrack = new double[1];
        long cost = 0, costMax = 0; int frames = 0;
        for (int f = 0; f < 30 * 240 && end == null; f++) {
            double hx = Math.cos(th), hy = Math.sin(th);
            long t0 = System.nanoTime();
            t.update(x + hx * WB / 2, y + hy * WB / 2, hx, hy, kmh, now, o);
            long c = System.nanoTime() - t0; if (f > 300) { cost += c; costMax = Math.max(costMax, c); frames++; }
            end = o.end;
            double want = o.steering, rate = 2.5 * dt;
            steer += Math.max(-rate, Math.min(rate, want - steer));
            if (o.brake) kmh -= Math.signum(kmh) * Math.min(Math.abs(kmh), 25 * dt);
            else if (o.forward) kmh += 8 * dt;
            else if (o.backward) kmh -= 6 * dt;
            else kmh -= Math.signum(kmh) * Math.min(Math.abs(kmh), 3 * dt);
            double s = Math.abs(kmh), factor = s < 10 ? 1 : s < 20 ? 0.91 : s < 35 ? 0.76 : 0.4;
            double ds = kmh / 3.6 * dt, kappa = WORLD_SIGN * KFULL * 0.92 * factor * steer;                       // the real car turns a little less than the tracker thinks
            x += Math.cos(th + kappa * ds / 2) * ds; y += Math.sin(th + kappa * ds / 2) * ds; th += kappa * ds;
            driven += Math.abs(ds); topSpeed = Math.max(topSpeed, s); now += 33;
            double near = 1e9;
            for (SolNavPlanner.Pose q : p) near = Math.min(near, Math.hypot(q.x - x, q.y - y));
            maxLat = Math.max(maxLat, near);
            SolNavPlanner mp = null;
            double gapNow = SolNavPlanner.gapAt(g, BODY, x, y, th);
            if (gapNow > 0) wasClear = true;                                     // a car that starts touching something is judged from the moment it is clear of it
            if (driven >= IGNORE_FIRST && wasClear) minGap = Math.min(minGap, gapNow);
            if (System.getProperty("dbg", "").length() > 0 && name.contains(System.getProperty("dbg")) && f % 12 == 0) System.out.printf("   f%d x %.2f y %.2f th %.1f kmh %.1f cmd %.2f steer %.2f fwd %b back %b brake %b nearPath %.2f gap %.2f%n", f, x, y, Math.toDegrees(th), kmh, o.steering, steer, o.forward, o.backward, o.brake, near, SolNavPlanner.gapAt(g, BODY, x, y, th));
        }
        boolean ok = "done".equals(end) && minGap > 0 && Math.hypot(x - gx, y - gy) < 2.5;
        if (!ok) fails++;
        System.out.printf("%s %-44s end=%s, off goal %.2f, off path max %.0f cm, smallest gap %.0f cm, driven %.1f of %d poses, top %.0f km/h, tracker mean %.1f us max %.0f us%n", ok ? "PASS" : "FAIL", name, end, Math.hypot(x - gx, y - gy), maxLat * 100, minGap * 100, driven, p.size(), topSpeed, frames == 0 ? 0 : cost / 1e3 / frames, costMax / 1e3);
    }

    /** expect: 0 a spot must be found and reached; -1 no spot may be offered. */
    static void park(String name, boolean[] o, double sx, double sy, int px, int py, int expect) {
        for (int y = py * 10; y < (py + 1) * 10; y++) for (int x = px * 10; x < (px + 1) * 10; x++) o[y * 600 + x] = true;
        SolNavPlanner.Grid g = grid(o);
        double capAlong = -1.2, capSide = 1;
        List<SolNavPark.Spot> spots = SolNavPark.spots(g, VAN, 2.12, 0.845, WB, px, py, capAlong, capSide, sx, sy, 0);
        if (expect < 0) {
            int reachable = 0;
            for (SolNavPark.Spot s : spots) if (SolNavPlanner.plan(g, VAN, sx, sy, 0, s.cx - Math.cos(s.th) * WB / 2, s.cy - Math.sin(s.th) * WB / 2, s.th, 800_000_000L).path != null) reachable++;
            if (reachable != 0) fails++;
            System.out.printf("%s %-44s offered %d spots, reachable %d%n", reachable == 0 ? "PASS" : "FAIL", name, spots.size(), reachable);
            return;
        }
        for (SolNavPark.Spot s : spots) {
            double c = Math.cos(s.th), k = Math.sin(s.th), rx = s.cx - c * WB / 2, ry = s.cy - k * WB / 2;
            SolNavPlanner.Result r = SolNavPlanner.plan(g, VAN, sx, sy, 0, rx, ry, s.th, 800_000_000L);
            if (r.path == null) continue;
            double capX = s.cx + c * capAlong - k * capSide * 1.3, capY = s.cy + k * capAlong + c * capSide * 1.3;       // the game's refuel area sits about half a tile off the side
            boolean inReach = Math.abs(Math.floor(capX) - px) <= 2 && Math.abs(Math.floor(capY) - py) <= 2;
            double side = Math.abs(-(px + .5 - s.cx) * k + (py + .5 - s.cy) * c) - 0.845 - 0.5;
            boolean ok = inReach && side >= SolNavPark.GAP_MIN - 1e-6;
            if (!ok) fails++;
            System.out.printf("%s %-44s heading %.0f, walking gap %.2f tiles, cap within reach %b, %d spots offered%n", ok ? "PASS" : "FAIL", name, Math.toDegrees(s.th), side, inReach, spots.size());
            drive("  drives to it: " + name, g, sx, sy, 0, rx, ry, s.th, false);
            return;
        }
        fails++;
        System.out.printf("FAIL %-44s no reachable spot (%d offered)%n", name, spots.size());
    }

    /** The clip at 7136,8212 from the third live test. */
    static void barricadeReplay() {
        int ox = 7110, oy = 8190;
        boolean[] o = blank();
        box(o, 7133 - ox, 8212 - oy, 7134 - ox, 8213 - oy); box(o, 7136 - ox, 8212 - oy, 7137 - ox, 8213 - oy); box(o, 7141 - ox, 8207 - oy, 7142 - ox, 8208 - oy); box(o, 7137 - ox, 8214 - oy, 7138 - ox, 8215 - oy);
        SolNavPlanner.Grid g = new SolNavPlanner.Grid(600, 600, ox, oy, o);
        // from the pose she started the turn, past the barricades
        double th = Math.toRadians(106), rx = 7134.6 - Math.cos(th) * WB / 2 - ox, ry = 8207.1 - Math.sin(th) * WB / 2 - oy;
        double gth = UP, gx = 7135 - ox, gy = 8232 - oy - WB / 2;
        SolNavPlanner.Grid g0 = new SolNavPlanner.Grid(600, 600, 0, 0, o);
        SolNavPlanner.Result r = SolNavPlanner.planSafe(g0, VAN, rx, ry, th, gx, gy, gth, 5_000_000_000L);
        if (r.path == null) { fails++; System.out.println("FAIL barricade replay: no plan " + r.why); }
        else run("replay of the clipped turn", g0, SolNavPlanner.smooth(g0, VAN, r.path), rx, ry, th, gx, gy, 0, 0);
        // standing where she stopped, touching it
        double sth = Math.toRadians(52), sx = 7135.93 - Math.cos(sth) * WB / 2 - ox, sy = 8209.87 - Math.sin(sth) * WB / 2 - oy;
        boolean touching = !SolNavPlanner.freeAt(g0, BODY, sx, sy, sth);
        SolNavPlanner.Result e = SolNavPlanner.planSafe(g0, VAN, sx, sy, sth, gx, gy, gth, 5_000_000_000L);
        boolean escaped = touching && e.path != null && e.path.get(0).dir < 0;
        if (!escaped) fails++;
        System.out.printf("%s touching the barricade: backs out and plans (touching %b, %s)%n", escaped ? "PASS" : "FAIL", touching, e.path == null ? e.why : "planned");
        IGNORE_FIRST = 0.6;                                                    // it starts out touching: judged from when it has left the contact
        if (e.path != null) run("backs out of the contact and passes", g0, SolNavPlanner.smooth(g0, VAN, e.path), sx, sy, sth, gx, gy, 0, 0);
        IGNORE_FIRST = 0;
        // the margin: wide where there is room, thin only in the gap that needs it
        boolean[] open = blank(); box(open, 28, 25, 29, 26);
        SolNavPlanner.Grid gw = grid(open);
        SolNavPlanner.Result w = SolNavPlanner.planSafe(gw, VAN, 30, 15, UP, 30, 35, UP, 3_000_000_000L);
        double c = w.path == null ? -1 : SolNavPlanner.minBodyClear(gw, VAN, w.path);
        boolean wideOk = c >= 0.15;
        if (!wideOk) fails++;
        System.out.printf("%s room to spare: keeps %.0f cm%n", wideOk ? "PASS" : "FAIL", c * 100);
        boolean[] tight = blank(); box(tight, 0, 30, 29, 31); box(tight, 31, 30, 60, 31);
        SolNavPlanner.Result t = SolNavPlanner.planSafe(grid(tight), VAN, 30, 18, UP, 30, 42, UP, 3_000_000_000L);
        if (t.path == null) fails++;
        System.out.printf("%s 2-tile gap still passes on the thin margin%n", t.path != null ? "PASS" : "FAIL");
        // pushing into something
        SolNavPlanner.Grid gp = grid(blank());
        SolNavPlanner.Result s = SolNavPlanner.plan(gp, VAN, 30, 10, UP, 30, 40, UP, 3_000_000_000L);
        SolNavTrack tr = new SolNavTrack(SolNavPlanner.smooth(gp, VAN, s.path), SolNavPlanner.speeds(gp, VAN, SolNavPlanner.smooth(gp, VAN, s.path)), WB, KFULL);
        SolNavTrack.Out out = new SolNavTrack.Out();
        long now = 1000; double y = 10 + WB / 2;
        for (int f = 0; f < 120; f++) { tr.update(30, y, 0, 1, Math.min(8, f * 0.2), now, out); y += Math.min(8, f * 0.2) / 3.6 / 30; now += 33; }
        ck("rolling normally: no alarm", out.end == null, out.end);
        long hit = now; String end = null;
        while (now - hit < 3000 && end == null) { tr.update(30, y, 0, 1, 0, now, out); end = out.end; now += 33; }
        ck("hit something: stops pushing in about a second (" + (now - hit) + " ms)", "stalled".equals(end) && now - hit < 1500, end);
        ck("and brakes", out.brake && !out.forward, out.forward);
    }

    static void ck(String n, boolean c, Object d) { if (!c) fails++; System.out.println((c ? "PASS " : "FAIL ") + n + (c ? "" : " : " + d)); }

    /** The part of a big recorded map the game would capture for a plan between these points: SolNav never plans on more. */
    static SolNavPlanner.Grid window(int w, int h, double ox, double oy, boolean[] occ, double ax, double ay, double bx, double by) {
        int radius = (int) Math.min(35, Math.ceil(Math.max(Math.abs(ax - bx), Math.abs(ay - by)) / 2) + 14);
        int mx = (int) Math.floor((ax + bx) / 2), my = (int) Math.floor((ay + by) / 2), n = (2 * radius + 1) * 10;
        int x0 = (int) Math.round((mx - radius - ox) * 10), y0 = (int) Math.round((my - radius - oy) * 10);
        boolean[] part = new boolean[n * n];
        for (int j = 0; j < n; j++) for (int i = 0; i < n; i++) {
            int xi = x0 + i, yi = y0 + j;
            part[j * n + i] = xi >= 0 && yi >= 0 && xi < w && yi < h && occ[yi * w + xi];
        }
        return new SolNavPlanner.Grid(n, n, mx - radius, my - radius, part);
    }

    /** Drives stage by stage to a point off the road on the map he recorded. */
    static void offRoad(Path dir) throws Exception {
        String[] m = Files.readString(dir.resolve("grid.txt")).trim().split("\\s+");
        int w = Integer.parseInt(m[0]), h = Integer.parseInt(m[1]);
        byte[] bits = Files.readAllBytes(dir.resolve("grid.bin"));
        boolean[] occ = new boolean[w * h];
        for (int i = 0; i < occ.length; i++) occ[i] = (bits[i >> 3] >> (i & 7) & 1) != 0;
        double mapX = Double.parseDouble(m[2]), mapY = Double.parseDouble(m[3]);
        SolNavPlanner.Grid whole = new SolNavPlanner.Grid(w, h, mapX, mapY, occ);
        double[][] trips = { { 7135, 8190, 90, 7146, 8197 }, { 7135, 8195, 0, 7150, 8203 }, { 7279, 8176, 0, 7300, 8186 }, { 7170, 8208, 180, 7143, 8195 }, { 7135, 8165, 90, 7160, 8198 } };
        for (double[] t : trips) {
            double th = Math.toRadians(t[2]), rx = t[0] - Math.cos(th) * WB / 2, ry = t[1] - Math.sin(th) * WB / 2;
            String name = String.format("off the road: %.0f,%.0f to %.0f,%.0f", t[0], t[1], t[3], t[4]);
            if (!SolNavPlanner.freeAt(whole, VAN, rx, ry, th)) { System.out.printf("     %s: start not free on the recorded map, skipped%n", name); continue; }
            int stages = 0; boolean arrived = false;
            while (stages < 8) {
                stages++;
                double cxNow = rx + Math.cos(th) * WB / 2, cyNow = ry + Math.sin(th) * WB / 2, toGo = Math.hypot(t[3] - cxNow, t[4] - cyNow), reach = Math.min(1, SolNavLegPlan.chunkLength(toGo) / Math.max(1e-3, toGo));
                SolNavPlanner.Grid g = window(w, h, mapX, mapY, occ, cxNow, cyNow, cxNow + (t[3] - cxNow) * reach, cyNow + (t[4] - cyNow) * reach);
                SolNavPlanner.Result r = SolNavLegPlan.plan(g, VAN, WB, rx, ry, th, t[3], t[4]);
                if (r.path == null) { System.out.printf("     stage %d: no plan (%s)%n", stages, r.why); break; }
                List<SolNavPlanner.Pose> p = SolNavPlanner.smooth(g, VAN, r.path);
                SolNavPlanner.Pose e = p.get(p.size() - 1);
                run(name + " stage " + stages, g, p, rx, ry, th, e.x, e.y, 0, 0);
                rx = e.x; ry = e.y; th = e.th;
                if (Math.hypot(rx + Math.cos(th) * WB / 2 - t[3], ry + Math.sin(th) * WB / 2 - t[4]) <= 3.5) { arrived = true; break; }
            }
            if (!arrived) fails++;
            System.out.printf("%s %s: %d stages%n", arrived ? "PASS" : "FAIL", name, stages);
        }
    }

    /** The stop that failed in the game: from where the GPS left her, 29 tiles from the pumps, on the map he recorded. */
    static void realPump(Path dir) throws Exception {
        String[] m = Files.readString(dir.resolve("grid.txt")).trim().split("\\s+");
        int w = Integer.parseInt(m[0]), h = Integer.parseInt(m[1]), ox = Integer.parseInt(m[2]), oy = Integer.parseInt(m[3]);
        byte[] bits = Files.readAllBytes(dir.resolve("grid.bin"));
        int cx = 7293, cy = 8177, radius = 29, n = (2 * radius + 1) * 10, x0 = (cx - radius - ox) * 10, y0 = (cy - radius - oy) * 10;
        boolean[] occ = new boolean[n * n];
        for (int j = 0; j < n; j++) for (int i = 0; i < n; i++) { int k = (y0 + j) * w + x0 + i; occ[j * n + i] = (bits[k >> 3] >> (k & 7) & 1) != 0; }
        SolNavPlanner.Grid g = new SolNavPlanner.Grid(n, n, cx - radius, cy - radius, occ);
        int px = 7307, py = 8178, solved = 0, tried = 0;
        for (double start : new double[] { 0, 107, -60, 180 }) for (int side = -1; side <= 1; side += 2) {
            double th = Math.toRadians(start), rx = 7279 - Math.cos(th) * WB / 2, ry = 8176 - Math.sin(th) * WB / 2;
            if (!SolNavPlanner.freeAt(g, VAN, rx, ry, th)) { System.out.printf("     start heading %.0f is not free on the recorded map%n", start); continue; }
            tried++;
            List<SolNavPark.Spot> spots = SolNavPark.spots(g, VAN, 2.12, 0.845, WB, px, py, -1.2, side, rx, ry, th);
            long t0 = System.nanoTime();
            SolNavPlanner.Result r = SolNavPark.plan(g, VAN, spots, WB, rx, ry, th);
            double wall = (System.nanoTime() - t0) / 1e6;
            System.out.printf("     heading %.0f, cap side %d: %d spots, %s, %d nodes, worker %.0f ms%n", start, side, spots.size(), r.path == null ? "no plan: " + r.why : "planned", r.nodes, wall);
            if (r.path == null) continue;
            solved++;
            SolNavPlanner.Pose last = r.path.get(r.path.size() - 1);
            run(String.format("real pump, heading %.0f, cap %d", start, side), g, SolNavPlanner.smooth(g, VAN, r.path), rx, ry, th, last.x, last.y, 0, 0);          // as the game side does
        }
        boolean ok = tried > 0 && solved >= tried - 1;                       // one awkward start may end in "could not park", which she says aloud; contact is failed above
        if (!ok) fails++;
        System.out.printf("%s real pump from where the GPS stopped: %d of %d starts planned%n", ok ? "PASS" : "FAIL", solved, tried);
    }

    /** The same recorded map with a car standing at the nearer pump: she goes to the other one. A comparison on his map, not a target. */
    static void realStationTaken(Path dir) throws Exception {
        String[] m = Files.readString(dir.resolve("grid.txt")).trim().split("\\s+");
        int w = Integer.parseInt(m[0]), h = Integer.parseInt(m[1]), ox = Integer.parseInt(m[2]), oy = Integer.parseInt(m[3]);
        byte[] bits = Files.readAllBytes(dir.resolve("grid.bin"));
        int cx = 7300, cy = 8177, radius = 29, n = (2 * radius + 1) * 10, x0 = (cx - radius - ox) * 10, y0 = (cy - radius - oy) * 10;
        boolean[] occ = new boolean[n * n];
        for (int j = 0; j < n; j++) for (int i = 0; i < n; i++) { int k = (y0 + j) * w + x0 + i; occ[j * n + i] = k >= 0 && (k >> 3) < bits.length && (bits[k >> 3] >> (k & 7) & 1) != 0; }
        int near = 7307, far = 7316, py = 8178;
        double th = 0, rx = 7285 - WB / 2, ry = 8176;
        float bx = near - 2.8f, by = py - 1.8f;
        float[] white = { bx, by, bx + 1.8f, by, bx + 1.8f, by + 4.6f, bx, by + 4.6f };
        for (int j = 0; j < n; j++) for (int i = 0; i < n; i++) { double x = cx - radius + (i + .5) / 10, y = cy - radius + (j + .5) / 10; if (x >= bx && x <= bx + 1.8 && y >= by && y <= by + 4.6) occ[j * n + i] = true; }
        SolNavPlanner.Grid g = new SolNavPlanner.Grid(n, n, cx - radius, cy - radius, occ);
        java.util.List<double[]> pumps = new java.util.ArrayList<>(); pumps.add(new double[] { near, py }); pumps.add(new double[] { far, py });
        java.util.List<float[]> cars = new java.util.ArrayList<>(); cars.add(white);
        List<SolNavPark.Spot> spots = SolNavPark.stationSpots(g, VAN, 2.12, 0.845, WB, pumps, cars, Double.NaN, Double.NaN, -1.2, -1.1, rx, ry, th);
        boolean first = !spots.isEmpty() && spots.get(0).px == far;
        SolNavPlanner.Result r = spots.isEmpty() ? null : SolNavPark.plan(g, VAN, spots, WB, rx, ry, th);
        boolean ok = first && r != null && r.path != null;
        if (!ok) fails++;
        System.out.printf("%s his station with a car at the nearer pump: goes to the free one (%d spots, first pump x=%d, %s)%n", ok ? "PASS" : "FAIL", spots.size(), spots.isEmpty() ? 0 : spots.get(0).px, r == null || r.path == null ? "no plan" : "planned");
    }

    static SolNavPlanner.Grid grid(boolean[] o) { return new SolNavPlanner.Grid(TILES * 10, TILES * 10, 0, 0, o); }

    public static void main(String[] a) throws Exception {
        boolean[] gap = blank(); box(gap, 0, 30, 29, 31); box(gap, 31, 30, 60, 31);
        drive("gap lined up", grid(gap.clone()), 30, 18, UP, 30, 42, UP, true);
        drive("gap, offset 1.5, 12 deg", grid(gap.clone()), 31.5, 18, UP - Math.toRadians(12), 30, 42, UP, true);
        drive("gap, offset -2, -15 deg", grid(gap.clone()), 28, 16, UP + Math.toRadians(15), 30, 42, UP, true);
        drive("nose-on at the right barricade", grid(gap.clone()), 31.7, 26.3, UP, 30, 42, UP, true);
        drive("nose-on at the left barricade", grid(gap.clone()), 28.3, 26.3, UP, 30, 42, UP, true);
        boolean[] wreck = blank();
        for (int y = 300; y < 345; y++) for (int x = 280; x < 330; x++) { double u = (x - 305) * Math.cos(.5) + (y - 322) * Math.sin(.5), v = -(x - 305) * Math.sin(.5) + (y - 322) * Math.cos(.5); if (Math.abs(u) < 21 && Math.abs(v) < 9) wreck[y * 600 + x] = true; }
        drive("overturned car at 30 deg", grid(wreck.clone()), 30, 18, UP, 30, 42, UP, true);
        boolean[] fence = blank(); box(fence, 0, 30, 24, 31); box(fence, 26, 30, 29, 31); box(fence, 31, 30, 34, 31); box(fence, 36, 30, 60, 31);
        for (int y = 255; y < 265; y++) for (int x = 240; x < 250; x++) fence[y * 600 + x] = true;
        drive("fence, barricades, thin post", grid(fence.clone()), 30, 18, UP, 30, 42, UP, true);
        boolean[] wall = blank(); box(wall, 0, 30, 40, 33);
        drive("wall across, open verge", grid(wall.clone()), 30, 20, UP, 30, 42, UP, true);
        // the case that broke it in the game: leaving a turn at speed, wheels still over, when the plan takes the wheel
        for (double lock : new double[] { 0.8, -0.8 }) {
            SolNavPlanner.Grid g = grid(blank());
            SolNavPlanner.Result r = SolNavPlanner.plan(g, VAN, 30, 16, UP, 30, 42, UP, 5_000_000_000L);
            START_STEER = lock;
            run("rolling out of a turn, wheels " + lock, g, SolNavPlanner.smooth(g, VAN, r.path), 30, 16, UP, 30, 42, 20, 0);
            START_STEER = 0;
        }
        // something appears behind while reversing
        {
            SolNavPlanner.Grid g = grid(gap.clone());
            SolNavPlanner.Result r = SolNavPlanner.plan(g, VAN, 31.7, 26.3, UP, 30, 42, UP, 5_000_000_000L);
            SolNavTrack t = new SolNavTrack(SolNavPlanner.smooth(g, VAN, r.path), SolNavPlanner.speeds(g, VAN, SolNavPlanner.smooth(g, VAN, r.path)), WB, KFULL);
            SolNavTrack.Out o = new SolNavTrack.Out();
            t.update(31.7, 26.3 + WB / 2, 0, 1, 0, 1000, o);
            boolean wasBack = t.reversing();
            t.rearBlocked();
            t.update(31.7, 26.3 + WB / 2, 0, 1, 0, 1100, o);
            SolNavTrack fresh = new SolNavTrack(SolNavPlanner.smooth(g, VAN, r.path), SolNavPlanner.speeds(g, VAN, SolNavPlanner.smooth(g, VAN, r.path)), WB, KFULL);
            boolean leftOk = fresh.reverseLeft() > 0.2 && fresh.reverseLeft() < 3.5;
            if (!leftOk) System.out.println("FAIL reverse left " + fresh.reverseLeft());
            boolean ok = leftOk && wasBack && "rear_blocked".equals(o.end) && o.brake && !o.backward;
            if (!ok) fails++;
            System.out.printf("%s rear check stops her at once (%s)%n", ok ? "PASS" : "FAIL", o.end);
        }
        // a place that failed is kept out of the next plan
        {
            boolean[] two = blank(); box(two, 0, 30, 20, 31); box(two, 22, 30, 27, 31); box(two, 30, 30, 60, 31);
            boolean[] banned = two.clone();
            SolNavPlanner.ban(banned, 600, 600, 0, 0, 21, 30.5, 1.2);
            SolNavPlanner.Grid g = grid(banned);
            SolNavPlanner.Result r = SolNavPlanner.plan(g, VAN, 21, 18, UP, 21, 42, UP, 5_000_000_000L);
            boolean other = r.path != null;
            double xAtWall = 0;
            if (other) for (SolNavPlanner.Pose q : r.path) if (Math.abs(q.y + 1.28 - 30.5) < 0.2) xAtWall = q.x;
            boolean ok = other && Math.abs(xAtWall - 28.5) < 1.5;
            if (!ok) fails++;
            System.out.printf("%s banned gap: goes through the other one (x %.1f, %s)%n", ok ? "PASS" : "FAIL", xAtWall, r.why);
        }
        // the cost guard
        {
            SolNavCost c = new SolNavCost("test", 250_000);
            for (int i = 0; i < 50; i++) c.note(300_000);
            boolean calm = c.slice() == 250_000;
            for (int i = 0; i < 50; i++) c.note(600_000);
            boolean halved = c.slice() < 250_000 && c.slice() >= 60_000;
            for (int i = 0; i < 500; i++) c.note(900_000);
            boolean floor = c.slice() == 60_000;
            boolean ok = calm && halved && floor;
            if (!ok) fails++;
            System.out.printf("%s cost guard: calm %b, halves %b, has a floor %b%n", ok ? "PASS" : "FAIL", calm, halved, floor);
        }
        // parking at a pump
        park("pump in the open", blank(), 8, 20, 20, 30, 0);
        { boolean[] w = blank(); box(w, 0, 33, 60, 34); park("pump against a wall", w, 8, 20, 30, 32, 0); }
        { boolean[] w = blank(); box(w, 27, 26, 28, 35); box(w, 33, 26, 34, 35); box(w, 27, 26, 34, 27); box(w, 27, 34, 34, 35); park("pump walled in on every side", w, 8, 20, 30, 30, -1); }
        { boolean[] w = blank(); box(w, 24, 28, 29, 33); box(w, 31, 28, 36, 33); park("pump in a slot between two cars: no spot", w, 8, 20, 30, 30, -1); }
        { boolean[] w = blank(); box(w, 21, 28, 26, 33); box(w, 34, 28, 39, 33); park("cars either side, room to walk", w, 8, 20, 30, 30, 0); }
        // rolling at 27 km/h, 2.4 tiles short of where the plan begins: the case that failed in the game
        {
            SolNavPlanner.Grid g = grid(gap.clone());
            SolNavPlanner.Result r = SolNavPlanner.plan(g, VAN, 30, 16, UP, 30, 42, UP, 5_000_000_000L);
            run("rolling up to the start of the path", g, SolNavPlanner.smooth(g, VAN, r.path), 30, 16, UP, 30, 42, 27, 2.4);
        }
        if (a.length > 0) {
            Path dir = Paths.get(a[0]);
            String[] m = Files.readString(dir.resolve("grid.txt")).trim().split("\\s+");
            int w = Integer.parseInt(m[0]), h = Integer.parseInt(m[1]);
            byte[] bits = Files.readAllBytes(dir.resolve("grid.bin"));
            boolean[] occ = new boolean[w * h];
            for (int i = 0; i < occ.length; i++) occ[i] = (bits[i >> 3] >> (i & 7) & 1) != 0;
            double mapX = Double.parseDouble(m[2]), mapY = Double.parseDouble(m[3]);
            for (String ln : Files.readAllLines(dir.resolve("scenes.txt"))) {
                if (ln.isBlank()) continue;
                String[] s = ln.trim().split("\\|"), v = s[1].trim().split("\\s+");
                double[] d = new double[6];
                for (int i = 0; i < 6; i++) d[i] = Double.parseDouble(v[i]);
                // recorded poses use a 2.56 wheelbase, the same as this test's van
                SolNavPlanner.Grid near = window(w, h, mapX, mapY, occ, d[0], d[1], d[3], d[4]);
                if (!SolNavPlanner.freeAt(near, VAN, d[3], d[4], d[5])) { System.out.printf("     %s: the recorded end is not free on the map (it changed after he drove there), skipped%n", s[0]); continue; }
                drive(s[0], near, d[0], d[1], d[2], d[3], d[4], d[5], false);
            }
        }
        barricadeReplay();
        if (a.length > 0) offRoad(Paths.get(a[0]));
        if (a.length > 0) { realPump(Paths.get(a[0])); realStationTaken(Paths.get(a[0])); }
        {
            // grass costs more: she keeps to the paved strip when it's barely longer, and not when it would be a long way round
            boolean[] open = blank();
            float[] soft = new float[600 * 600];
            for (int y = 0; y < 600; y++) for (int x = 0; x < 600; x++) if (x < 275 || x >= 325) soft[y * 600 + x] = 0.25f;
            SolNavPlanner.Grid g = grid(open.clone()); g.soft = soft;
            SolNavPlanner.Result r = SolNavPlanner.plan(g, VAN, 33.8, 16, UP, 26.2, 44, UP, 5_000_000_000L);
            double onPaved = 0; for (SolNavPlanner.Pose q : r.path) if (q.x >= 27.5 && q.x < 32.5) onPaved++;
            boolean ok = r.path != null && onPaved / r.path.size() > 0.5;
            if (!ok) fails++;
            System.out.printf("%s prefers paving: %.0f%% of the way on it%n", ok ? "PASS" : "FAIL", 100 * onPaved / r.path.size());
        }
        System.out.println(fails == 0 ? "SUMMARY ALL PASS" : "SUMMARY FAILED " + fails);
        System.exit(fails == 0 ? 0 : 1);
    }
}

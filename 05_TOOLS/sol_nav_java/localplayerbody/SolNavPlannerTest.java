package localplayerbody;

import java.util.List;

/** Offline scenes for the planner, drawn from his screenshots. Real barricade squares and heading are still to come from a valid perception dump. */
public final class SolNavPlannerTest {
    static final int TILES = 60;
    static final SolNavPlanner.Car VAN = new SolNavPlanner.Car(2.12, 0.845, 2.56, 1 / 4.8, 0.05);
    static int fails;

    static boolean[] blank() { return new boolean[TILES * 10 * TILES * 10]; }
    static void box(boolean[] o, double x0, double y0, double x1, double y1) {
        int n = TILES * 10;
        for (int y = (int) Math.round(y0 * 10); y < Math.round(y1 * 10); y++) for (int x = (int) Math.round(x0 * 10); x < Math.round(x1 * 10); x++) if (x >= 0 && y >= 0 && x < n && y < n) o[y * n + x] = true;
    }
    static void post(boolean[] o, double cx, double cy, double r) {
        int n = TILES * 10;
        for (int y = 0; y < n; y++) for (int x = 0; x < n; x++) if (Math.hypot((x + .5) / 10 - cx, (y + .5) / 10 - cy) <= r) o[y * n + x] = true;
    }
    static void orientedBox(boolean[] o, double cx, double cy, double angle, double hl, double hw) {
        int n = TILES * 10;
        double c = Math.cos(angle), s = Math.sin(angle);
        for (int y = 0; y < n; y++) for (int x = 0; x < n; x++) {
            double dx = (x + .5) / 10 - cx, dy = (y + .5) / 10 - cy;
            if (Math.abs(dx * c + dy * s) <= hl && Math.abs(-dx * s + dy * c) <= hw) o[y * n + x] = true;
        }
    }

    static double totalTurn(List<SolNavPlanner.Pose> p) {
        double total = 0;
        for (int i = 1; i < p.size(); i++) {
            double a = p.get(i).th - p.get(i - 1).th;
            while (a > Math.PI) a -= 2 * Math.PI;
            while (a < -Math.PI) a += 2 * Math.PI;
            total += Math.abs(a);
        }
        return total;
    }

    static void scene(String name, boolean[] o, double sx, double sy, double sth, double gx, double gy, double gth, boolean wantPath, Integer needReverseMax, Double maxPeakTurn) {
        SolNavPlanner.Grid g = new SolNavPlanner.Grid(TILES * 10, TILES * 10, 0, 0, o);
        SolNavPlanner.Result r = SolNavPlanner.plan(g, VAN, sx, sy, sth, gx, gy, gth, 5_000_000_000L);
        if (r.path == null) {
            boolean ok = !wantPath;
            System.out.printf("%s %-46s no path (%s), %d nodes, %.0f ms%n", ok ? "PASS" : "FAIL", name, r.why, r.nodes, r.ms);
            if (!ok) fails++;
            return;
        }
        double rough = totalTurn(r.path);
        List<SolNavPlanner.Pose> p = SolNavPlanner.smooth(g, VAN, r.path);
        System.out.printf("     smoothing: total turn %.0f -> %.0f deg, smallest gap to the body %.0f cm%n", Math.toDegrees(rough), Math.toDegrees(totalTurn(p)), SolNavPlanner.minBodyClear(g, VAN, p) * 100);
        double len = 0, back = 0, totalTurn = 0, minClear = 1e9;
        int switches = 0;
        for (int i = 1; i < p.size(); i++) {
            double d = Math.hypot(p.get(i).x - p.get(i - 1).x, p.get(i).y - p.get(i - 1).y);
            len += d;
            if (p.get(i).dir < 0) back += d;
            if (p.get(i).dir != p.get(i - 1).dir) switches++;
            double a = p.get(i).th - p.get(i - 1).th;
            while (a > Math.PI) a -= 2 * Math.PI;
            while (a < -Math.PI) a += 2 * Math.PI;
            totalTurn += Math.abs(a);
        }
        boolean valid = SolNavPlanner.validate(g, VAN, p);
        boolean ok = wantPath && valid && (needReverseMax == null || back <= needReverseMax) && (maxPeakTurn == null || totalTurn <= maxPeakTurn);
        System.out.printf("%s %-46s %.1f tiles, reverse %.1f, gear changes %d, total turn %.0f deg, %d nodes, %.0f ms, shot=%s, valid=%s%n", ok ? "PASS" : "FAIL", name, len, back, switches, Math.toDegrees(totalTurn), r.nodes, r.ms, r.byShot, valid);
        if (!ok) fails++;
    }

    static void verdict(String name, boolean ok, String detail) {
        System.out.printf("%s %-46s %s%n", ok ? "PASS" : "FAIL", name, detail);
        if (!ok) fails++;
    }

    /** The plan a real drive gets: reverses at most maxBack, never points back the way she came, ends going forward. */
    static void forward(String name, boolean[] o, double sx, double sy, double sth, double gx, double gy, double gth, double maxBack) {
        SolNavPlanner.Grid g = new SolNavPlanner.Grid(TILES * 10, TILES * 10, 0, 0, o);
        SolNavPlanner.Result r = SolNavPlanner.planSafe(g, VAN, sx, sy, sth, gx, gy, gth, 2_000_000_000L);
        if (r.path == null) { verdict(name, false, "no plan: " + r.why); return; }
        List<SolNavPlanner.Pose> p = SolNavPlanner.smooth(g, VAN, r.path);
        double back = 0, worst = 0;
        for (int i = 1; i < p.size(); i++) {
            if (p.get(i).dir < 0) back += Math.hypot(p.get(i).x - p.get(i - 1).x, p.get(i).y - p.get(i - 1).y);
            double a = p.get(i).th - gth;
            while (a > Math.PI) a -= 2 * Math.PI;
            while (a < -Math.PI) a += 2 * Math.PI;
            worst = Math.max(worst, Math.abs(a));
        }
        boolean ok = SolNavPlanner.validate(g, VAN, p) && back <= maxBack + 0.05 && worst <= Math.toRadians(120) && p.get(p.size() - 1).dir > 0;
        verdict(name, ok, String.format(java.util.Locale.ROOT, "reverse %.1f (limit %.1f), widest heading off the road %.0f deg, gap %.0f cm, %.0f ms", back, maxBack, Math.toDegrees(worst), SolNavPlanner.minBodyClear(g, VAN, p) * 100, r.ms));
    }

    public static void main(String[] a) {
        double up = Math.PI / 2;
        // two whole-tile barricades leaving a 2-tile gap: about 0.155 of a tile each side for the van's 1.69 width
        boolean[] gap = blank();
        box(gap, 26, 30, 29, 31);
        box(gap, 31, 30, 34, 31);
        scene("gap 2 tiles, lined up", gap.clone(), 30, 18, up, 30, 42, up, true, null, Math.toRadians(30));
        scene("gap 2 tiles, offset 1.5 and 12 deg off", gap.clone(), 28.5, 18, up + Math.toRadians(12), 30, 42, up, true, 0, Math.toRadians(90));
        scene("gap 2 tiles, offset -2 and -15 deg off", gap.clone(), 32, 16, up - Math.toRadians(15), 30, 42, up, true, 0, Math.toRadians(90));
        // nose against the right barricade: short reverse, then a gentle left
        boolean[] nose = gap.clone();
        scene("nose-on at right barricade", nose, 32.5, 25.2, up, 30, 42, up, true, 4, Math.toRadians(200));
        // overturned car across the lane at 30 degrees
        boolean[] wreck = blank();
        orientedBox(wreck, 30, 30, Math.toRadians(30), 2.5, 1.1);
        scene("overturned car at 30 deg", wreck.clone(), 30, 18, up, 30, 42, up, true, 0, Math.toRadians(180));
        // fence line (thin) and a lamp post (thin) with a barricade
        boolean[] fence = blank();
        box(fence, 36, 5, 36.13, 55);
        box(fence, 22, 30, 29, 31);
        box(fence, 31, 30, 36, 31);
        post(fence, 24, 26, 0.35);
        scene("fence, barricades, thin post", fence.clone(), 30, 18, up, 30, 42, up, true, null, null);
        // wall right across with the verge open
        boolean[] wall = blank();
        box(wall, 0, 30, 40, 33);
        scene("wall across, open verge", wall.clone(), 30, 20, up, 30, 42, up, true, 4, Math.toRadians(300));   // the least a right-left-right drive can turn here is about 276 deg (scratch search over the turn angles), so 300 is 10% over it
        // standing 3 cm from a wall, inside the safety margin: must still get out
        boolean[] tight = blank();
        box(tight, 20, 30, 40, 33);
        scene("3 cm from a wall, inside the margin", tight.clone(), 30, 26.57, up, 45, 42, up, true, null, null);
        // really shut
        boolean[] shut = blank();
        box(shut, 0, 30, 60, 33);
        scene("road shut everywhere", shut.clone(), 30, 20, up, 30, 42, up, false, null, null);
        // gap narrower than the van
        boolean[] narrow = blank();
        box(narrow, 0, 30, 29.3, 31);
        box(narrow, 30.8, 30, 60, 31);
        scene("1.5-wide gap, van cannot fit", narrow.clone(), 30, 20, up, 30, 42, up, false, null, null);
        // his rule: a simple obstacle costs a short back-up, then forward
        double noseGap = 3.4 + 0.1;
        boolean[] pole = blank(); post(pole, 30, 30, 0.35);
        forward("pole dead ahead, seen from far", pole.clone(), 30, 18, up, 30, 42, up, 0);
        forward("pole, nose almost on it", pole.clone(), 30, 30 - 0.35 - noseGap, up, 30, 42, up, 2.0);
        boolean[] barrier = blank(); box(barrier, 28, 30, 32, 31);
        forward("one barrier, seen from far", barrier.clone(), 30, 18, up, 30, 42, up, 0);
        forward("one barrier, nose-on", barrier.clone(), 30, 30 - noseGap, up, 30, 42, up, 2.0);
        boolean[] parked = blank(); orientedBox(parked, 30, 30, up, 2.4, 0.9);
        forward("parked car, seen from far", parked.clone(), 30, 18, up, 30, 42, up, 0);
        forward("parked car, nose-on", parked.clone(), 30, 30 - 2.4 - noseGap, up, 30, 42, up, 2.0);
        boolean[] touching = blank(); box(touching, 28, 30, 32, 31);
        forward("barrier, already touching it", touching.clone(), 30, 30 - 3.4 + 0.02, up, 30, 42, up, 2.0);
        boolean[] pocket = blank(); box(pocket, 25, 30, 35, 31); box(pocket, 25, 21, 26, 31); box(pocket, 34, 21, 35, 31);
        SolNavPlanner.Grid pg = new SolNavPlanner.Grid(TILES * 10, TILES * 10, 0, 0, pocket);
        SolNavPlanner.Result held = SolNavPlanner.planSafe(pg, VAN, 30, 25.5, up, 30, 42, up, 2_000_000_000L);
        verdict("blind pocket: forward tries find no way, no turning back", held.path == null, "why=" + held.why);
        SolNavPlanner.Result freed = SolNavPlanner.planSafe(pg, VAN, 30, 25.5, up, 30, 42, up, 2_000_000_000L, true);
        verdict("blind pocket: allowed to turn back, it gets out", freed.path != null && SolNavPlanner.validate(pg, VAN, freed.path), "why=" + freed.why + " nodes=" + freed.nodes);
        SolNavPlanner.Result shutHeld = SolNavPlanner.planSafe(new SolNavPlanner.Grid(TILES * 10, TILES * 10, 0, 0, shut), VAN, 30, 20, up, 30, 42, up, 2_000_000_000L);
        SolNavPlanner.Result shutFreed = SolNavPlanner.planSafe(new SolNavPlanner.Grid(TILES * 10, TILES * 10, 0, 0, shut), VAN, 30, 20, up, 30, 42, up, 2_000_000_000L, true);
        verdict("road truly shut: no plan either way", shutHeld.path == null && shutFreed.path == null, shutHeld.why + " / " + shutFreed.why);
        // the worker: submit returns at once, poll never blocks
        boolean[] snap = wall.clone();
        SolNavWorker.warmUp();
        long t0 = System.nanoTime();
        boolean accepted = SolNavWorker.submit(TILES * 10, TILES * 10, 0, 0, snap, VAN, 30, 20, up, 30, 42, up, 3_000_000_000L);
        double submitMs = (System.nanoTime() - t0) / 1e6;
        boolean second = SolNavWorker.submit(TILES * 10, TILES * 10, 0, 0, snap, VAN, 30, 20, up, 30, 42, up, 3_000_000_000L);
        double worstPoll = 0;
        SolNavPlanner.Result wr = null;
        long end = System.currentTimeMillis() + 8000;
        while (wr == null && System.currentTimeMillis() < end) {
            long p0 = System.nanoTime();
            wr = SolNavWorker.poll();
            worstPoll = Math.max(worstPoll, (System.nanoTime() - p0) / 1e6);
            try { Thread.sleep(1); } catch (InterruptedException e) { break; }
        }
        boolean wok = accepted && !second && wr != null && wr.path != null && worstPoll < 0.5 && submitMs < 0.5;
        System.out.printf("%s worker: submit %.3f ms, worst poll %.3f ms, refused a second job=%s, got a path=%s%n", wok ? "PASS" : "FAIL", submitMs, worstPoll, !second, wr != null && wr.path != null);
        if (!wok) fails++;
        System.out.println(fails == 0 ? "SUMMARY ALL PASS" : "SUMMARY FAILED " + fails);
        System.exit(fails == 0 ? 0 : 1);
    }
}

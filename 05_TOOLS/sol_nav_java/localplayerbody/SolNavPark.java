package localplayerbody;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Where to stop at a fuel pump: the fuel cap beside the pump, a gap wide enough to walk in, and a walking way from a door to that gap.
 * Pure Java over the planner's grid. Poses are car centres; cap is the fuel cap in the car's frame (along = forward, side = + towards heading angle + 90).
 */
public final class SolNavPark {
    public static final double GAP_MIN = 1.0, GAP_MAX = 1.4, PERSON = 0.28, STEP = 0.2;

    public static final class Spot { public double cx, cy, th, gap; double cost; public int px, py; public boolean taken; }

    /** A pump is taken when a car stands within this of it, or a person within PERSON_NEAR. */
    private static final double CAR_NEAR = 2.5, PERSON_NEAR = 1.5;
    private static final int SPOTS_PER_PUMP = 4;

    public static boolean occupied(double px, double py, List<float[]> cars, double personX, double personY) {
        double x = px + 0.5, y = py + 0.5;
        if (!Double.isNaN(personX) && Math.hypot(personX - x, personY - y) <= PERSON_NEAR) return true;
        for (float[] c : cars) for (int i = 0; i < 4; i++) {
            int j = (i + 1) % 4;
            if (toSegment(x, y, c[2 * i], c[2 * i + 1], c[2 * j], c[2 * j + 1]) <= CAR_NEAR) return true;
        }
        return false;
    }

    private static double toSegment(double x, double y, double ax, double ay, double bx, double by) {
        double dx = bx - ax, dy = by - ay, len = dx * dx + dy * dy;
        double t = len < 1e-9 ? 0 : Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / len));
        return Math.hypot(x - ax - t * dx, y - ay - t * dy);
    }

    /** The cheapest stop for each way of facing, and always the far side of the best one: a side that is blocked on the way in must not leave nothing to try. */
    private static List<Spot> aroundThePump(List<Spot> sorted) {
        Spot[] byHeading = new Spot[8];
        List<Spot> distinct = new ArrayList<>();
        for (Spot s : sorted) {
            int k = headingIndex(s.th);
            if (byHeading[k] == null) { byHeading[k] = s; distinct.add(s); }
        }
        List<Spot> out = new ArrayList<>(distinct.subList(0, Math.min(SPOTS_PER_PUMP - 1, distinct.size())));
        if (!out.isEmpty()) {
            Spot far = byHeading[(headingIndex(out.get(0).th) + 4) % 8];
            if (far != null && !out.contains(far)) out.add(far);
            else if (distinct.size() >= SPOTS_PER_PUMP) out.add(distinct.get(SPOTS_PER_PUMP - 1));
        }
        return out;
    }

    private static int headingIndex(double th) { return Math.floorMod((int) Math.round(th / (Math.PI / 4)), 8); }

    /** The whole station, free pumps first and nearest first; a taken pump only comes after every free one. */
    public static List<Spot> stationSpots(SolNavPlanner.Grid g, SolNavPlanner.Car car, double halfLength, double halfWidth, double wheelbase, List<double[]> pumps, List<float[]> cars, double personX, double personY, double capAlong, double capSide, double sx, double sy, double sth) {
        List<double[]> order = new ArrayList<>(pumps);
        order.sort(Comparator.comparingDouble((double[] p) -> occupied(p[0], p[1], cars, personX, personY) ? 1 : 0).thenComparingDouble(p -> Math.hypot(p[0] + 0.5 - sx, p[1] + 0.5 - sy)));
        List<Spot> out = new ArrayList<>();
        for (double[] p : order) {
            boolean taken = occupied(p[0], p[1], cars, personX, personY);
            for (Spot s : aroundThePump(spots(g, car, halfLength, halfWidth, wheelbase, p[0], p[1], capAlong, capSide, sx, sy, sth))) { s.taken = taken; out.add(s); }
        }
        return out;
    }

    private SolNavPark() {}

    /** Every acceptable stopping pose, best first. px, py is the pump square's corner. */
    public static List<Spot> spots(SolNavPlanner.Grid g, SolNavPlanner.Car car, double halfLength, double halfWidth, double wheelbase, double px, double py, double capAlong, double capSide, double sx, double sy, double sth) {
        List<Spot> out = new ArrayList<>();
        double pumpX = px + 0.5, pumpY = py + 0.5, side = capSide >= 0 ? 1 : -1, end = capAlong >= 0 ? 1 : -1;
        boolean onEnd = Math.abs(capAlong) - halfLength > Math.abs(capSide) - halfWidth;       // the face of the body the cap is on
        for (double gap = GAP_MIN + 0.1; gap <= GAP_MAX + 1e-9; gap += 0.3) {
            for (int k = 0; k < 8; k++) {
                double th = k * Math.PI / 4, c = Math.cos(th), s = Math.sin(th);
                double along = onEnd ? end * (0.5 + gap + halfLength) : capAlong, lateral = onEnd ? capSide : side * (0.5 + gap + halfWidth);
                double cx = pumpX - (c * along - s * lateral), cy = pumpY - (s * along + c * lateral);
                double rx = cx - c * wheelbase / 2, ry = cy - s * wheelbase / 2;
                double capX = cx + c * capAlong - s * capSide, capY = cy + s * capAlong + c * capSide;
                if (Math.abs(Math.floor(capX) - Math.floor(px)) > 2 || Math.abs(Math.floor(capY) - Math.floor(py)) > 2) continue;   // the game's own reach
                if (!SolNavPlanner.freeAt(g, car, rx, ry, th)) continue;
                if (!walkable(g, cx, cy, c, s, halfLength, halfWidth, capAlong, capSide, onEnd)) continue;
                Spot p = new Spot();
                p.cx = cx; p.cy = cy; p.th = th; p.gap = gap; p.px = (int) Math.floor(px); p.py = (int) Math.floor(py);
                double turn = Math.abs(Math.atan2(Math.sin(th - sth), Math.cos(th - sth)));
                p.cost = Math.hypot(cx - sx, cy - sy) + 4 * turn;
                out.add(p);
            }
        }
        out.sort(Comparator.comparingDouble(q -> q.cost));
        return out;
    }

    private static final double FAR = 10, APPROACH = 7;
    private static final int MAX_SPOTS = 16;
    private static final long LEG_NANOS = 1_500_000_000L, ALL_NANOS = 14_000_000_000L;

    /** Tries the best spots in turn. From far off it plans in two short searches, through a pose lined up a few tiles out, then the stop itself. Worker thread only. */
    public static SolNavPlanner.Result plan(SolNavPlanner.Grid g, SolNavPlanner.Car car, List<Spot> spots, double wheelbase, double sx, double sy, double sth) {
        SolNavPlanner.Result last = new SolNavPlanner.Result();
        last.why = "no_parking_spot";
        int tried = 0, nodes = 0;
        double ms = 0;
        long t0 = System.nanoTime();
        for (Spot s : spots) {
            if (++tried > MAX_SPOTS || System.nanoTime() - t0 > ALL_NANOS) break;
            double c = Math.cos(s.th), k = Math.sin(s.th), gx = s.cx - c * wheelbase / 2, gy = s.cy - k * wheelbase / 2;
            double ax = gx - c * APPROACH, ay = gy - k * APPROACH;
            SolNavPlanner.Result r = null;
            if (Math.hypot(gx - sx, gy - sy) > FAR && SolNavPlanner.freeAt(g, car, ax, ay, s.th)) {
                SolNavPlanner.Result a = SolNavPlanner.planSafe(g, car, sx, sy, sth, ax, ay, s.th, LEG_NANOS, true);
                nodes += a.nodes; ms += a.ms;
                if (a.path != null) {
                    SolNavPlanner.Result b = SolNavPlanner.planSafe(g, car, ax, ay, s.th, gx, gy, s.th, LEG_NANOS, true);
                    nodes += b.nodes; ms += b.ms;
                    if (b.path != null) { r = a; r.path = new ArrayList<>(a.path); r.path.addAll(b.path); }
                    else last.why = b.why;
                } else last.why = a.why;
            }
            if (r == null) {
                SolNavPlanner.Result d = SolNavPlanner.planSafe(g, car, sx, sy, sth, gx, gy, s.th, LEG_NANOS, true);
                nodes += d.nodes; ms += d.ms;
                if (d.path != null) r = d; else last.why = d.why;
            }
            if (r != null) { r.nodes = nodes; r.ms = ms; return r; }
        }
        last.nodes = nodes; last.ms = ms;
        return last;
    }

    /** With the car parked here, can someone get from either door to the spot beside the fuel cap, and is the pump's side of it open? */
    static boolean walkable(SolNavPlanner.Grid g, double cx, double cy, double c, double s, double halfLength, double halfWidth, double capAlong, double capSide, boolean onEnd) {
        double out = halfWidth + 0.45;
        double spotAlong = onEnd ? (capAlong >= 0 ? 1 : -1) * (halfLength + 0.45) : capAlong, spotSide = onEnd ? capSide : (capSide >= 0 ? 1 : -1) * out;
        double spotX = cx + c * spotAlong - s * spotSide, spotY = cy + s * spotAlong + c * spotSide;
        if (!open(g, spotX, spotY, cx, cy, c, s, halfLength, halfWidth)) return false;
        double doorAlong = halfLength * 0.3;
        return reach(g, spotX, spotY, cx + c * doorAlong - s * out, cy + s * doorAlong + c * out, cx, cy, c, s, halfLength, halfWidth)
            || reach(g, spotX, spotY, cx + c * doorAlong + s * out, cy + s * doorAlong - c * out, cx, cy, c, s, halfLength, halfWidth);
    }

    private static boolean open(SolNavPlanner.Grid g, double x, double y, double cx, double cy, double c, double s, double halfLength, double halfWidth) {
        if (g.clearance(x, y) < PERSON) return false;
        double dx = x - cx, dy = y - cy;
        return Math.abs(dx * c + dy * s) > halfLength + PERSON || Math.abs(-dx * s + dy * c) > halfWidth + PERSON;
    }

    private static boolean reach(SolNavPlanner.Grid g, double ax, double ay, double bx, double by, double cx, double cy, double c, double s, double halfLength, double halfWidth) {
        if (!open(g, bx, by, cx, cy, c, s, halfLength, halfWidth)) return false;
        int size = 121;                                                     // 24 tiles square around the car is plenty for a walk round it
        boolean[] seen = new boolean[size * size];
        ArrayDeque<int[]> q = new ArrayDeque<>();
        int ai = size / 2 + (int) Math.round((ax - cx) / STEP), aj = size / 2 + (int) Math.round((ay - cy) / STEP);
        int bi = size / 2 + (int) Math.round((bx - cx) / STEP), bj = size / 2 + (int) Math.round((by - cy) / STEP);
        if (ai < 0 || aj < 0 || ai >= size || aj >= size) return false;
        seen[aj * size + ai] = true;
        q.add(new int[] { ai, aj });
        int[][] n = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } };
        while (!q.isEmpty()) {
            int[] e = q.poll();
            if (Math.abs(e[0] - bi) <= 1 && Math.abs(e[1] - bj) <= 1) return true;
            for (int[] d : n) {
                int i = e[0] + d[0], j = e[1] + d[1];
                if (i < 0 || j < 0 || i >= size || j >= size || seen[j * size + i]) continue;
                seen[j * size + i] = true;
                if (open(g, cx + (i - size / 2) * STEP, cy + (j - size / 2) * STEP, cx, cy, c, s, halfLength, halfWidth)) q.add(new int[] { i, j });
            }
        }
        return false;
    }
}

package localplayerbody;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;

/**
 * Stage 2 core: hybrid A* over a 10 cm occupancy grid. Pure Java with no game types, so it runs on a worker thread from a snapshot.
 * Continuous pose per cell, 72 heading bins, forward and reverse arcs, two heuristics, an analytic shot to the goal, a clearance cost.
 * The analytic shot uses Dubins curves driven forward or entirely in reverse: a subset of full Reeds-Shepp, which also allows gear changes inside one shot.
 * Poses are at the rear axle.
 */
public final class SolNavPlanner {
    public static final double RES = 0.1;
    private static final double CELL = 0.25, ARC = 0.5, SAMPLE = 0.1;
    private static final int FLOW_STEP = 3;                                  // the flow grid is 30 cm: 3 cells of the 10 cm grid
    private static final double FLOW_CELL = FLOW_STEP * RES;
    private static final int BINS = 72, SHOT_EVERY = 8;
    private static final double SHOT_MAX_REVERSE = 5.0;
    private static final int MAX_NODES = 60000, SHORTCUT_STRIDE = 5;
    private static final double WIDE_PAD = 0.18, BACK_OUT = 3.0;
    private static final double SHORT_REVERSE = 2.0, FORWARD_ARC = Math.toRadians(120), NO_LIMIT = 10;
    private static final long WIDE_BUDGET_NANOS = 1_000_000_000L;
    private static final long SMOOTH_NANOS = 150_000_000L;
    private static final double REVERSE_COST = 1.6, SWITCH_COST = 3.0, STEER_COST = 0.15, CLEAR_WANTED = 0.5, CLEAR_COST = 0.3, H_WEIGHT = 1.2, TURN_COST = 2.0;
    private static final int KEEP_LOOKING = 3000;                            // nodes spent looking for something better once a path is in hand

    public static final class Car {
        final double halfLength, halfWidth, axleToCentre, kmax, pad;
        public Car(double halfLength, double halfWidth, double wheelbase, double kmax, double pad) {
            this.halfLength = halfLength; this.halfWidth = halfWidth; this.axleToCentre = wheelbase / 2; this.kmax = kmax; this.pad = pad;
        }
    }

    public static final class Grid {
        final int w, h; final double ox, oy; final boolean[] occ; final float[] dist;
        /** Extra cost per tile for ground she would rather not cross; null means everywhere the same. */
        public float[] soft;
        public Grid(int w, int h, double ox, double oy, boolean[] occ) {
            this.w = w; this.h = h; this.ox = ox; this.oy = oy; this.occ = occ; this.dist = new float[w * h];
            Arrays.fill(dist, 1e6f);
            for (int i = 0; i < w * h; i++) if (occ[i]) dist[i] = 0;
            float a = (float) RES, b = (float) (RES * Math.sqrt(2));
            for (int y = 0; y < h; y++) for (int x = 0; x < w; x++) {
                int i = y * w + x;
                if (x > 0) relax(i, i - 1, a);
                if (y > 0) { relax(i, i - w, a); if (x > 0) relax(i, i - w - 1, b); if (x < w - 1) relax(i, i - w + 1, b); }
            }
            for (int y = h - 1; y >= 0; y--) for (int x = w - 1; x >= 0; x--) {
                int i = y * w + x;
                if (x < w - 1) relax(i, i + 1, a);
                if (y < h - 1) { relax(i, i + w, a); if (x < w - 1) relax(i, i + w + 1, b); if (x > 0) relax(i, i + w - 1, b); }
            }
        }
        private void relax(int i, int j, float c) { if (dist[j] + c < dist[i]) dist[i] = dist[j] + c; }
        boolean occupied(double x, double y) {
            int ix = (int) Math.floor((x - ox) / RES), iy = (int) Math.floor((y - oy) / RES);
            return ix < 0 || iy < 0 || ix >= w || iy >= h || occ[iy * w + ix];
        }
        double softAt(double x, double y) {
            if (soft == null) return 0;
            int ix = (int) Math.floor((x - ox) / RES), iy = (int) Math.floor((y - oy) / RES);
            return ix < 0 || iy < 0 || ix >= w || iy >= h ? 0 : soft[iy * w + ix];
        }
        double clearance(double x, double y) {
            int ix = (int) Math.floor((x - ox) / RES), iy = (int) Math.floor((y - oy) / RES);
            return ix < 0 || iy < 0 || ix >= w || iy >= h ? 0 : dist[iy * w + ix];
        }
    }

    public static final class Pose {
        public final double x, y, th; public final int dir;
        Pose(double x, double y, double th, int dir) { this.x = x; this.y = y; this.th = th; this.dir = dir; }
    }

    public static final class Result {
        public List<Pose> path; public int nodes; public double ms; public String why = ""; public boolean byShot; public SolNavTrack track;
    }

    private static final class Node implements Comparable<Node> {
        double rev;
        double x, y, th, g, f, kappa; int dir; Node parent; List<Pose> arc;
        public int compareTo(Node o) { return Double.compare(f, o.f); }
    }

    private final Grid grid; private final Car car; private final double gx, gy, gth, goalR = 0.3, goalA = Math.toRadians(10);
    private double[] flow; private int fw, fh;

    private SolNavPlanner(Grid grid, Car car, double gx, double gy, double gth) { this.grid = grid; this.car = car; this.gx = gx; this.gy = gy; this.gth = gth; }

    /** Body at this rear-axle pose: circles against the distance map first, then the exact box on the 10 cm grid near contact. */
    boolean free(double x, double y, double th) {
        double c = Math.cos(th), s = Math.sin(th);
        double cx = x + c * car.axleToCentre, cy = y + s * car.axleToCentre;
        double L = car.halfLength + car.pad, W = car.halfWidth + car.pad;
        double r = Math.sqrt(W * W + (L / 3) * (L / 3));
        boolean sure = true;
        for (int k = -1; k <= 1; k++) {
            double d = grid.clearance(cx + c * k * (2 * L / 3), cy + s * k * (2 * L / 3));
            if (d < r + RES * 1.5) { sure = false; break; }
        }
        if (sure) return true;
        for (double a = -L; a <= L + 1e-9; a += RES / 2) {
            if (grid.occupied(cx + c * a - s * W, cy + s * a + c * W) || grid.occupied(cx + c * a + s * W, cy + s * a - c * W)) return false;
        }
        for (double b = -W; b <= W + 1e-9; b += RES / 2) {
            if (grid.occupied(cx + c * L - s * b, cy + s * L + c * b) || grid.occupied(cx - c * L - s * b, cy - s * L + c * b)) return false;
        }
        return true;
    }

    /** Gap between the body's sides and the nearest obstacle, from three circles inscribed along the body. Below zero means touching. */
    double bodyClear(double x, double y, double th) {
        double c = Math.cos(th), s = Math.sin(th), W = car.halfWidth, off = Math.max(0, car.halfLength - W);
        double cx = x + c * car.axleToCentre, cy = y + s * car.axleToCentre, best = 1e9;
        for (int k = -1; k <= 1; k++) best = Math.min(best, grid.clearance(cx + c * k * off, cy + s * k * off) - W);
        return best;
    }

    private static double wrap(double a) { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; }
    private static long key(double x, double y, double th) {
        long ix = (long) Math.floor(x / CELL) + (1L << 20), iy = (long) Math.floor(y / CELL) + (1L << 20);
        double t = th % (2 * Math.PI); if (t < 0) t += 2 * Math.PI;
        long b = (long) (t / (2 * Math.PI) * BINS) % BINS;
        return (ix << 28) | (iy << 7) | b;
    }

    /** Distance to the goal around obstacles, by the car's half width, on a 30 cm grid: the holonomic heuristic. */
    private void buildFlow() {
        int step = FLOW_STEP;
        fw = grid.w / step + 1; fh = grid.h / step + 1;
        flow = new double[fw * fh];
        Arrays.fill(flow, 1e9);
        boolean[] blocked = new boolean[fw * fh];
        for (int y = 0; y < fh; y++) for (int x = 0; x < fw; x++) {
            int gxi = Math.min(grid.w - 1, x * step), gyi = Math.min(grid.h - 1, y * step);
            // no point of a real corridor is further than a quarter-cell from a sampled point, so this never closes a gap the car fits
            blocked[y * fw + x] = grid.dist[gyi * grid.w + gxi] < car.halfWidth - FLOW_CELL * 0.75;
        }
        int sx = Math.max(0, Math.min(fw - 1, (int) ((gx - grid.ox) / FLOW_CELL))), sy = Math.max(0, Math.min(fh - 1, (int) ((gy - grid.oy) / FLOW_CELL)));
        PriorityQueue<double[]> q = new PriorityQueue<>((a, b) -> Double.compare(a[0], b[0]));
        flow[sy * fw + sx] = 0;
        q.add(new double[] { 0, sx, sy });
        int[][] n = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 }, { 1, 1 }, { 1, -1 }, { -1, 1 }, { -1, -1 } };
        while (!q.isEmpty()) {
            double[] e = q.poll();
            int x = (int) e[1], y = (int) e[2];
            if (e[0] > flow[y * fw + x]) continue;
            for (int[] d : n) {
                int nx = x + d[0], ny = y + d[1];
                if (nx < 0 || ny < 0 || nx >= fw || ny >= fh || blocked[ny * fw + nx]) continue;
                double v = e[0] + FLOW_CELL * Math.hypot(d[0], d[1]);
                if (v < flow[ny * fw + nx]) { flow[ny * fw + nx] = v; q.add(new double[] { v, nx, ny }); }
            }
        }
    }

    private double heuristic(double x, double y, double th) {
        int fx = Math.max(0, Math.min(fw - 1, (int) ((x - grid.ox) / FLOW_CELL))), fy = Math.max(0, Math.min(fh - 1, (int) ((y - grid.oy) / FLOW_CELL)));
        double around = flow[fy * fw + fx];
        double turn = Math.abs(wrap(gth - th)) / car.kmax * 0.5;
        return Math.max(around >= 1e9 ? 1e6 : around, Math.hypot(gx - x, gy - y) + turn);
    }

    /** Shortest Dubins word: returns (type, t, p, q) in units of the turning radius, or null. Types 0 LSL, 1 RSR, 2 LSR, 3 RSL. */
    private static List<double[]> dubins(double d, double a, double b) {
        List<double[]> out = new ArrayList<>();
        double sa = Math.sin(a), sb = Math.sin(b), ca = Math.cos(a), cb = Math.cos(b), cab = Math.cos(a - b);
        double two = 2 * Math.PI;
        double p2 = 2 + d * d - 2 * cab + 2 * d * (sa - sb);
        if (p2 >= 0) { double t0 = Math.atan2(cb - ca, d + sa - sb); out.add(new double[] { 0, mod(-a + t0, two), Math.sqrt(p2), mod(b - t0, two) }); }
        p2 = 2 + d * d - 2 * cab + 2 * d * (sb - sa);
        if (p2 >= 0) { double t0 = Math.atan2(ca - cb, d - sa + sb); out.add(new double[] { 1, mod(a - t0, two), Math.sqrt(p2), mod(-b + t0, two) }); }
        p2 = -2 + d * d + 2 * cab + 2 * d * (sa + sb);
        if (p2 >= 0) { double p = Math.sqrt(p2), t0 = Math.atan2(-ca - cb, d + sa + sb) - Math.atan2(-2.0, p); out.add(new double[] { 2, mod(-a + t0, two), p, mod(-b + t0, two) }); }
        p2 = -2 + d * d + 2 * cab - 2 * d * (sa + sb);
        if (p2 >= 0) { double p = Math.sqrt(p2), t0 = Math.atan2(ca + cb, d - sa - sb) - Math.atan2(2.0, p); out.add(new double[] { 3, mod(a - t0, two), p, mod(b - t0, two) }); }
        return out;
    }
    private static double mod(double v, double m) { v %= m; return v < 0 ? v + m : v; }

    /** Samples one word from (x,y,th); returns null at the first pose that is not free. */
    private List<Pose> sample(double[] w, double x, double y, double th, double R, boolean reverse) {
        int[][] kinds = { { 1, 0, 1 }, { -1, 0, -1 }, { 1, 0, -1 }, { -1, 0, 1 } };
        int[] k = kinds[(int) w[0]];
        double[] lens = { w[1] * R, w[2] * R, w[3] * R };
        List<Pose> out = new ArrayList<>();
        for (int seg = 0; seg < 3; seg++) {
            int n = (int) Math.ceil(lens[seg] / SAMPLE);
            double ds = n == 0 ? 0 : lens[seg] / n, kap = k[seg] / R;
            for (int i = 0; i < n; i++) {
                x += Math.cos(th + kap * ds / 2) * ds;
                y += Math.sin(th + kap * ds / 2) * ds;
                th += kap * ds;
                double real = reverse ? th + Math.PI : th;
                if (!free(x, y, real)) return null;
                out.add(new Pose(x, y, wrap(real), reverse ? -1 : 1));
            }
        }
        return out;
    }

    /** The best collision-free analytic path to the goal from this pose, forward or all in reverse, or null. */
    private double shotCost;

    private double maxReverse = Double.MAX_VALUE, maxOff = NO_LIMIT, startTh, usedReverse;

    private SolNavPlanner limits(double reverse, double off, double th) { maxReverse = reverse; maxOff = off; startTh = th; return this; }

    /** Pointing back the way she came: away from both where she was heading and where the road goes. */
    private boolean turnedBack(double th) { return maxOff < NO_LIMIT && Math.abs(wrap(th - gth)) > maxOff && Math.abs(wrap(th - startTh)) > maxOff; }

    private List<Pose> shot(double x, double y, double th, double reversed) {
        double R = 1.0 / car.kmax;
        List<Pose> best = null;
        double bestLen = 1e18, heuristicNow = heuristic(x, y, th);
        for (int rev = 0; rev < 2; rev++) {
            boolean r = rev == 1;
            double t0 = r ? th + Math.PI : th, t1 = r ? gth + Math.PI : gth;
            double dx = gx - x, dy = gy - y, D = Math.hypot(dx, dy) / R, phi = Math.atan2(dy, dx);
            for (double[] w : dubins(D, mod(t0 - phi, 2 * Math.PI), mod(t1 - phi, 2 * Math.PI))) {
                double raw = (w[1] + w[2] + w[3]) * R, turning = w[1] + w[3];
                // a shot is a finishing move: short in reverse, never a loop, never much longer than the way round
                if (turning > Math.toRadians(170) || (r && (raw > SHOT_MAX_REVERSE || reversed + raw > maxReverse)) || raw > 1.3 * heuristicNow + 3) continue;
                double len = raw * (r ? REVERSE_COST : 1) + TURN_COST * turning;
                if (len >= bestLen) continue;
                List<Pose> p = sample(w, x, y, t0, R, r);
                if (p == null) continue;
                boolean away = false;
                for (Pose q : p) if (turnedBack(q.th)) { away = true; break; }
                if (away) continue;
                for (Pose q : p) {
                    double m = bodyClear(q.x, q.y, q.th);
                    if (m < CLEAR_WANTED) len += SAMPLE * CLEAR_COST * (CLEAR_WANTED - m) / CLEAR_WANTED;
                    len += SAMPLE * grid.softAt(q.x, q.y);
                }
                if (len < bestLen) { best = p; bestLen = len; }
            }
        }
        shotCost = bestLen;
        return best;
    }

    private double arcCost(Node n, double kappa, int dir, double ds, double minClear) {
        double c = ds * (dir < 0 ? REVERSE_COST : 1) + STEER_COST * Math.abs(kappa - n.kappa) / car.kmax + TURN_COST * ds * Math.abs(kappa);
        if (n.dir != 0 && n.dir != dir) c += SWITCH_COST;
        if (minClear < CLEAR_WANTED) c += ds * CLEAR_COST * (CLEAR_WANTED - minClear) / CLEAR_WANTED;
        return c;
    }

    public static Result plan(Grid grid, Car car, double sx, double sy, double sth, double gx, double gy, double gth, long budgetNanos) {
        return plan(grid, car, sx, sy, sth, gx, gy, gth, budgetNanos, Double.MAX_VALUE, NO_LIMIT);
    }

    /** maxReverse: metres of reverse the whole plan may use. maxOff: how far from the way she is going it may point. */
    public static Result plan(Grid grid, Car car, double sx, double sy, double sth, double gx, double gy, double gth, long budgetNanos, double maxReverse, double maxOff) {
        long t0 = System.nanoTime();
        SolNavPlanner p = new SolNavPlanner(grid, car, gx, gy, gth).limits(maxReverse, maxOff, sth);
        List<Pose> escape = null;
        if (!p.free(sx, sy, sth)) {                                         // the safety margin must not trap a car already standing inside it
            p = new SolNavPlanner(grid, new Car(car.halfLength, car.halfWidth, car.axleToCentre * 2, car.kmax, 0), gx, gy, gth).limits(maxReverse, maxOff, sth);
            if (!p.free(sx, sy, sth)) {                                     // touching something: straight back out of it first, or forward if it's behind
                escape = p.backOut(sx, sy, sth);
                if (escape == null) { Result r = new Result(); r.why = "start_not_free"; r.ms = (System.nanoTime() - t0) / 1e6; return r; }
                Pose e = escape.get(escape.size() - 1);
                sx = e.x; sy = e.y;
                double backed = e.dir < 0 ? escape.size() * 0.1 : 0;
                SolNavPlanner full = new SolNavPlanner(grid, car, gx, gy, gth).limits(maxReverse, maxOff, sth);
                if (p.free(sx, sy, sth) && full.free(sx, sy, sth)) p = full;
                p.usedReverse = backed;
            }
        }
        Result r = p.search(sx, sy, sth, t0, budgetNanos);
        if (escape != null && r.path != null) { List<Pose> all = new ArrayList<>(escape); all.addAll(r.path); r.path = all; }
        r.ms = (System.nanoTime() - t0) / 1e6;
        return r;
    }

    private Result search(double sx, double sy, double sth, long t0, long budget) {
        Result r = new Result();
        if (!free(gx, gy, gth)) { r.why = "goal_not_free"; return r; }
        buildFlow();
        if (heuristic(sx, sy, sth) >= 1e6) { r.why = "no_corridor_wide_enough"; return r; }
        double[] fr = { 0, 0.25, -0.25, 0.55, -0.55, 1.0, -1.0 };
        PriorityQueue<Node> open = new PriorityQueue<>();
        Map<Long, Double> best = new HashMap<>();
        Node start = new Node();
        start.x = sx; start.y = sy; start.th = sth; start.rev = usedReverse; start.f = H_WEIGHT * heuristic(sx, sy, sth);
        open.add(start);
        best.put(key(sx, sy, sth), 0.0);
        int n = 0, stopAt = Integer.MAX_VALUE;
        double bestCost = 1e18;
        while (!open.isEmpty()) {
            if (r.path != null && (n >= stopAt || open.peek().f >= bestCost)) { r.nodes = n; return r; }
            if (System.nanoTime() - t0 > budget) { r.nodes = n; if (r.path == null) r.why = "out_of_time"; return r; }
            if (n >= MAX_NODES) { r.nodes = n; if (r.path == null) r.why = "no_path_found"; return r; }
            Node c = open.poll();
            Double seen = best.get(key(c.x, c.y, c.th));
            if (seen != null && c.g > seen + 1e-9) continue;
            n++;
            if (Math.hypot(c.x - gx, c.y - gy) < goalR && Math.abs(wrap(c.th - gth)) < goalA) {
                if (c.g < bestCost) { bestCost = c.g; r.path = unwind(c, null); r.byShot = false; stopAt = Math.min(stopAt, n + KEEP_LOOKING); }
                continue;
            }
            if (n % SHOT_EVERY == 1 || Math.hypot(c.x - gx, c.y - gy) < 8) {
                List<Pose> shot = shot(c.x, c.y, c.th, c.rev);
                if (shot != null) {
                    double total = c.g + shotCost + (c.dir != 0 && c.dir != shot.get(0).dir ? SWITCH_COST : 0);
                    if (total < bestCost) { bestCost = total; r.path = unwind(c, shot); r.byShot = true; stopAt = Math.min(stopAt, n + KEEP_LOOKING); }
                }
            }
            for (int dir : new int[] { 1, -1 }) for (double f : fr) {
                if (dir < 0 && c.rev + ARC > maxReverse) continue;
                double kappa = f * car.kmax, x = c.x, y = c.y, th = c.th, minClear = 1e9;
                int steps = (int) Math.round(ARC / SAMPLE);
                double ds = ARC / steps;
                boolean ok = true;
                List<Pose> arc = new ArrayList<>(steps);
                for (int i = 0; i < steps; i++) {
                    x += dir * Math.cos(th + dir * kappa * ds / 2) * ds;
                    y += dir * Math.sin(th + dir * kappa * ds / 2) * ds;
                    th += dir * kappa * ds;
                    if (!free(x, y, th) || turnedBack(th)) { ok = false; break; }
                    minClear = Math.min(minClear, bodyClear(x, y, th));
                    arc.add(new Pose(x, y, wrap(th), dir));
                }
                if (!ok) continue;
                double g = c.g + arcCost(c, kappa, dir, ARC, minClear) + ARC * grid.softAt(x, y);
                long k = key(x, y, th);
                Double b = best.get(k);
                if (b != null && b <= g) continue;
                double h = heuristic(x, y, th);
                if (h >= 1e6) continue;
                best.put(k, g);
                Node m = new Node();
                m.x = x; m.y = y; m.th = th; m.g = g; m.kappa = kappa; m.dir = dir; m.rev = c.rev + (dir < 0 ? ARC : 0); m.parent = c; m.arc = arc; m.f = g + H_WEIGHT * h;
                open.add(m);
            }
        }
        if (r.path == null) r.why = "no_path";
        r.nodes = n;
        return r;
    }

    private static List<Pose> unwind(Node end, List<Pose> tail) {
        List<List<Pose>> parts = new ArrayList<>();
        for (Node n = end; n != null && n.arc != null; n = n.parent) parts.add(0, n.arc);
        List<Pose> out = new ArrayList<>();
        for (List<Pose> a : parts) out.addAll(a);
        if (tail != null) out.addAll(tail);
        return out;
    }

    /** Replaces stretches of one gear with a single Dubins curve when that turns less and keeps at least the clearance the stretch had. Ends and gear changes stay put; time-boxed. */
    public static List<Pose> smooth(Grid grid, Car car, List<Pose> in) {
        int n = in.size();
        if (n < 5) return in;
        SolNavPlanner p = new SolNavPlanner(grid, car, 0, 0, 0);
        long deadline = System.nanoTime() + SMOOTH_NANOS;
        double[] turn = new double[n];
        for (int i = 1; i < n; i++) turn[i] = turn[i - 1] + Math.abs(wrap(in.get(i).th - in.get(i - 1).th));
        List<Pose> out = new ArrayList<>(n);
        out.add(in.get(0));
        for (int a = 0; a < n - 1; ) {
            int b = a + 1;
            while (b + 1 < n && in.get(b + 1).dir == in.get(a + 1).dir) b++;
            p.shortcutRun(in, a, b, turn, deadline, out);
            a = b;
        }
        for (Pose q : out) if (!p.free(q.x, q.y, q.th)) return in;      // a line the car cannot follow is worse than a rough one
        return out;
    }

    private void shortcutRun(List<Pose> in, int a, int b, double[] turn, long deadline, List<Pose> out) {
        double[] floor = new double[b + 1];
        for (int i = a; i < b; ) {
            int jump = -1;
            List<Pose> via = null;
            if (System.nanoTime() < deadline && b - i >= SHORTCUT_STRIDE) {
                double m = 1e9;
                for (int j = i; j <= b; j++) { Pose q = in.get(j); m = Math.min(m, bodyClear(q.x, q.y, q.th)); floor[j] = m; }
                int top = i + (b - i) / SHORTCUT_STRIDE * SHORTCUT_STRIDE;
                for (int j = b; j >= i + SHORTCUT_STRIDE && via == null; j = j > top ? top : j - SHORTCUT_STRIDE) {
                    via = connect(in.get(i), in.get(j), (turn[j] - turn[i]) * 0.95, (j - i) * SAMPLE * 1.05, Math.min(floor[j], CLEAR_WANTED) - RES);
                    if (via != null) jump = j;
                }
            }
            if (via != null) { out.addAll(via); i = jump; }
            else { out.add(in.get(i + 1)); i++; }
        }
    }

    /** The Dubins curve from a to b in b's gear that turns least, under the limits, or null. */
    private List<Pose> connect(Pose a, Pose b, double maxTurn, double maxLen, double minClear) {
        double R = 1.0 / car.kmax;
        boolean r = b.dir < 0;
        double t0 = r ? a.th + Math.PI : a.th, t1 = r ? b.th + Math.PI : b.th;
        double dx = b.x - a.x, dy = b.y - a.y, D = Math.hypot(dx, dy) / R, phi = Math.atan2(dy, dx);
        List<Pose> best = null;
        double least = maxTurn;
        for (double[] w : dubins(D, mod(t0 - phi, 2 * Math.PI), mod(t1 - phi, 2 * Math.PI))) {
            double turning = w[1] + w[3];
            if (turning >= least || (w[1] + w[2] + w[3]) * R > maxLen) continue;
            List<Pose> p = sample(w, a.x, a.y, t0, R, r);
            if (p == null) continue;
            boolean ok = true;
            for (Pose q : p) if (bodyClear(q.x, q.y, q.th) < minClear) { ok = false; break; }
            if (ok) { best = p; least = turning; }
        }
        return best;
    }

    /** Target speed at each pose, km/h: slow in gaps and bends, slower still in reverse and coming up to a stop. */
    public static double[] speeds(Grid grid, Car car, List<Pose> path) {
        SolNavPlanner p = new SolNavPlanner(grid, car, 0, 0, 0);
        int n = path.size();
        double[] v = new double[n];
        for (int i = 0; i < n; i++) {
            Pose q = path.get(i);
            double c = p.bodyClear(q.x, q.y, q.th);
            double s = c < 0.25 ? 6 : c < 0.5 ? 10 : c < 1.0 ? 15 : 22;
            int a = Math.max(0, i - 5), b = Math.min(n - 1, i + 5);
            double kap = Math.abs(wrap(path.get(b).th - path.get(a).th)) / Math.max(0.1, (b - a) * SAMPLE);
            if (kap > 0.12) s = Math.min(s, 8);
            if (q.dir < 0) s = Math.min(s, 5);
            v[i] = s;
        }
        for (int i = n - 2; i >= 0; i--) {                              // come down to a walk before a stop or a gear change
            boolean stopNext = i + 1 == n - 1 || path.get(i + 1).dir != path.get(i + 2 < n ? i + 2 : i + 1).dir;
            if (stopNext) v[i + 1] = Math.min(v[i + 1], 3);
            v[i] = Math.min(v[i], v[i + 1] + 0.35);
        }
        return v;
    }

    /** Does the body fit at this rear-axle pose? */
    static boolean freeAt(Grid grid, Car car, double x, double y, double th) { return new SolNavPlanner(grid, car, 0, 0, 0).free(x, y, th); }

    /** The first plan keeps a hand's width from everything. Only a gap that needs it gets the thin margin. */
    public static Result planSafe(Grid grid, Car car, double sx, double sy, double sth, double gx, double gy, double gth, long budgetNanos) {
        return planSafe(grid, car, sx, sy, sth, gx, gy, gth, budgetNanos, false);
    }

    /** A plan keeps going her way and backs up only a little: a short reverse first, a longer one only if that finds nothing. mayTurnBack lifts both, once forward tries have failed. */
    public static Result planSafe(Grid grid, Car car, double sx, double sy, double sth, double gx, double gy, double gth, long budgetNanos, boolean mayTurnBack) {
        long t0 = System.nanoTime();
        double reverse = mayTurnBack ? Double.MAX_VALUE : SHORT_REVERSE, off = mayTurnBack ? NO_LIMIT : FORWARD_ARC;
        Car wide = new Car(car.halfLength, car.halfWidth, car.axleToCentre * 2, car.kmax, WIDE_PAD);
        if (car.pad < WIDE_PAD && freeAt(grid, wide, sx, sy, sth)) {                    // starting inside the wide margin: the wide plan has nothing to offer
            Result r = plan(grid, wide, sx, sy, sth, gx, gy, gth, Math.min(budgetNanos / 3, WIDE_BUDGET_NANOS), reverse, off);
            if (r.path != null) return r;
        }
        long left = budgetNanos - (System.nanoTime() - t0);
        return plan(grid, car, sx, sy, sth, gx, gy, gth, Math.max(1, left), reverse, off);
    }

    private List<Pose> backOut(double sx, double sy, double sth) {
        double c = Math.cos(sth), s = Math.sin(sth);
        for (int dir : new int[] { -1, 1 }) {
            for (double d = 0.2; d <= Math.min(BACK_OUT, maxReverse) + 1e-9; d += 0.1) {
                if (!free(sx + dir * c * d, sy + dir * s * d, sth)) continue;
                List<Pose> out = new ArrayList<>();
                for (double q = 0.1; q <= d + 0.3 + 1e-9; q += 0.1) out.add(new Pose(sx + dir * c * q, sy + dir * s * q, sth, dir));
                return out;
            }
        }
        return null;
    }

    /** Marks a circle as occupied: a place that has already failed, kept out of the next plan. */
    public static void ban(boolean[] occ, int w, int h, double ox, double oy, double x, double y, double radius) {
        int x0 = (int) Math.floor((x - radius - ox) / RES), x1 = (int) Math.ceil((x + radius - ox) / RES), y0 = (int) Math.floor((y - radius - oy) / RES), y1 = (int) Math.ceil((y + radius - oy) / RES);
        for (int j = Math.max(0, y0); j <= Math.min(h - 1, y1); j++) for (int i = Math.max(0, x0); i <= Math.min(w - 1, x1); i++) {
            double dx = ox + (i + .5) * RES - x, dy = oy + (j + .5) * RES - y;
            if (dx * dx + dy * dy <= radius * radius) occ[j * w + i] = true;
        }
    }

    /** The gap between the body and anything at one rear-axle pose; for simulation. */
    static double gapAt(Grid grid, Car car, double x, double y, double th) { return new SolNavPlanner(grid, car, 0, 0, 0).exactGap(x, y, th); }

    private double exactGap(double x, double y, double th) {
        double c = Math.cos(th), s = Math.sin(th), cx = x + c * car.axleToCentre, cy = y + s * car.axleToCentre, m = 1e9;
        for (double a = -car.halfLength; a <= car.halfLength + 1e-9; a += RES / 2) for (int sd = -1; sd <= 1; sd += 2) m = Math.min(m, grid.clearance(cx + c * a - s * sd * car.halfWidth, cy + s * a + c * sd * car.halfWidth));
        for (double b = -car.halfWidth; b <= car.halfWidth + 1e-9; b += RES / 2) for (int sd = -1; sd <= 1; sd += 2) m = Math.min(m, grid.clearance(cx + c * sd * car.halfLength - s * b, cy + s * sd * car.halfLength + c * b));
        return m;
    }

    /** The smallest gap between the body and anything along a path. */
    public static double minBodyClear(Grid grid, Car car, List<Pose> path) {
        SolNavPlanner p = new SolNavPlanner(grid, car, 0, 0, 0);
        double m = 1e9;
        for (Pose q : path) m = Math.min(m, p.bodyClear(q.x, q.y, q.th));
        return m;
    }

    /** For tests and for re-validating a plan against a newer snapshot. */
    public static boolean validate(Grid grid, Car car, List<Pose> path) {
        SolNavPlanner p = new SolNavPlanner(grid, car, 0, 0, 0);
        for (Pose q : path) if (!p.free(q.x, q.y, q.th)) return false;
        return true;
    }
}

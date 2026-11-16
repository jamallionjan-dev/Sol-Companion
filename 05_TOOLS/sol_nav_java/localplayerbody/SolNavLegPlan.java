package localplayerbody;

/**
 * The drive beyond the road: toward a point the road network does not reach, one short search at a time.
 * Each call plans a chunk of at most 30 tiles toward the destination, sliding sideways if the ideal end of the chunk is not free. Worker thread only.
 */
public final class SolNavLegPlan {
    private static final double CHUNK = 30, ARRIVED = 3;
    private static final double[] REACH = { 1.0, 0.8, 0.6, 0.4 }, SIDE = { 0, 2, -2, 4, -4, 6, -6 };
    private static final long SEARCH_NANOS = 1_200_000_000L;
    private static final int MAX_SEARCHES = 6;

    private SolNavLegPlan() {}

    public static double chunkLength(double dist) { return Math.min(dist, CHUNK); }

    /** sx, sy, sth at the rear axle; dx, dy the car centre's destination. */
    public static SolNavPlanner.Result plan(SolNavPlanner.Grid g, SolNavPlanner.Car car, double wheelbase, double sx, double sy, double sth, double dx, double dy) {
        double cx = sx + Math.cos(sth) * wheelbase / 2, cy = sy + Math.sin(sth) * wheelbase / 2;
        double dist = Math.hypot(dx - cx, dy - cy), bearing = Math.atan2(dy - cy, dx - cx), step = chunkLength(dist);
        double c = Math.cos(bearing), s = Math.sin(bearing);
        SolNavPlanner.Result last = new SolNavPlanner.Result();
        last.why = "no_free_end";
        int searches = 0;
        for (double f : REACH) for (double side : SIDE) {
            double reach = step * f;
            if (reach < ARRIVED) continue;
            double gx = cx + c * reach - s * side, gy = cy + s * reach + c * side;
            double rx = gx - c * wheelbase / 2, ry = gy - s * wheelbase / 2;
            if (!SolNavPlanner.freeAt(g, car, rx, ry, bearing)) continue;
            if (++searches > MAX_SEARCHES) return last;
            SolNavPlanner.Result r = SolNavPlanner.planSafe(g, car, sx, sy, sth, rx, ry, bearing, SEARCH_NANOS, true);
            if (r.path != null) return r;
            last = r;
        }
        return last;
    }
}

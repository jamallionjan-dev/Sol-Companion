package localplayerbody;

import java.util.List;

/**
 * Stage 3: follows a planned path, one frame at a time. Pure Java with no game types, so it can be simulated.
 * Forward legs use a Stanley controller on the front axle, reverse legs a pure pursuit on the rear axle.
 * Steering sign is the game's input sign: positive turns the heading angle upward (atan2 of the world y over x).
 */
public final class SolNavTrack {
    private static final double STANLEY_GAIN = 1.6, REVERSE_HEADING = 1.2, REVERSE_LATERAL = 0.6, ARRIVE = 0.45, ARRIVE_GEAR = 0.15, OFF_PATH = 1.2, JOIN_BEHIND = 8, JOIN_SIDE = 0.8;
    private static final int SEARCH = 40, SPEED_LOOK = 30;
    private static final long STALL_MS = 2500, PUSHING_MS = 1000, MAX_MS = 180000, SETTLE_MS = 700;
    private static final double ROLLING_KMH = 3, STOPPED_KMH = 0.7;

    public static final class Out {
        public float steering; public boolean forward, backward, brake; public String end, note;
    }

    private final double[] x, y, th, v;
    private final int[] dir;
    private final double wheelbase, kFull;
    private int i, legEnd;
    private long startMs = -1, movedMs, settleUntil;
    private boolean rearBlocked, wasRolling, driving;
    private long stoppedSince = -1;
    public boolean reversing() { return dir[Math.min(i, dir.length - 1)] < 0; }
    /** Tiles left to drive in this reverse leg: anything further back than this is not in her way. */
    public double reverseLeft() {
        double run = 0;
        for (int k = i; k < legEnd; k++) run += Math.hypot(x[k + 1] - x[k], y[k + 1] - y[k]);
        return run;
    }
    /** Something has appeared behind the car: called from the game side, never more often than every 100 ms. */
    public void rearBlocked() { rearBlocked = true; }
    private int progressI;

    /** Poses at the rear axle. kFull is the curvature at full steering lock at walking speed, per tile. */
    public SolNavTrack(List<SolNavPlanner.Pose> path, double[] speeds, double wheelbase, double kFull) {
        int n = path.size();
        x = new double[n]; y = new double[n]; th = new double[n]; dir = new int[n]; v = speeds;
        for (int k = 0; k < n; k++) { SolNavPlanner.Pose p = path.get(k); x[k] = p.x; y[k] = p.y; th[k] = p.th; dir[k] = p.dir; }
        this.wheelbase = wheelbase; this.kFull = kFull;
        legEnd = endOfLeg(0);
    }

    private int endOfLeg(int from) {
        int e = from;
        while (e + 1 < dir.length && dir[e + 1] == dir[from]) e++;
        return e;
    }
    private static double wrap(double a) { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; }

    /** The game turns less at speed: measured from recorded driving. */
    private double fullLockCurvature(double kmh) {
        double s = Math.abs(kmh);
        return kFull * (s < 10 ? 1.0 : s < 20 ? 0.91 : s < 35 ? 0.76 : 0.4);
    }

    /** cx, cy is the car's centre; hx, hy its unit forward vector; kmh is negative in reverse. */
    public void update(double cx, double cy, double hx, double hy, double kmh, long now, Out o) {
        o.end = null; o.note = null;
        if (startMs < 0) { startMs = now; movedMs = now; if (Math.abs(kmh) < 1) settleUntil = now + SETTLE_MS; }
        if (i > progressI) { progressI = i; movedMs = now; }                  // getting along the path is the only thing that counts: turning on the spot does not
        int gear = dir[Math.min(i, dir.length - 1)];
        double half = wheelbase / 2, rx = cx - hx * half, ry = cy - hy * half, heading = Math.atan2(hy, hx);
        double best = 1e18;
        int bi = i;
        for (int k = i, top = Math.min(legEnd, i + SEARCH); k <= top; k++) {
            double d = (x[k] - rx) * (x[k] - rx) + (y[k] - ry) * (y[k] - ry);
            if (d < best) { best = d; bi = k; }
        }
        i = bi;
        double toEnd = Math.hypot(x[legEnd] - rx, y[legEnd] - ry);
        boolean last = legEnd >= dir.length - 1;
        if (i >= legEnd - 1 && toEnd < (last ? ARRIVE : ARRIVE_GEAR) || i >= legEnd) {
            if (last) { stop(o); o.end = "done"; return; }
            if (Math.abs(kmh) > 1.0) { stop(o); return; }                  // change gear only at a standstill
            i = legEnd + 1; legEnd = endOfLeg(i); movedMs = now; gear = dir[i]; settleUntil = now + SETTLE_MS; wasRolling = false;
        }
        if (now - startMs > MAX_MS) { stop(o); o.end = "timeout"; return; }
        if (now - movedMs > STALL_MS) { stop(o); o.end = "stalled"; return; }
        if (Math.abs(kmh) >= ROLLING_KMH) wasRolling = true;
        if (wasRolling && driving && Math.abs(kmh) < STOPPED_KMH) {            // it was moving, the pedal is down and now it isn't: it has hit something
            if (stoppedSince < 0) stoppedSince = now;
            if (now - stoppedSince > PUSHING_MS) { stop(o); o.end = "stalled"; return; }
        } else stoppedSince = -1;
        double c0 = Math.cos(th[0]), s0 = Math.sin(th[0]), along0 = (rx - x[0]) * c0 + (ry - y[0]) * s0, side0 = -(rx - x[0]) * s0 + (ry - y[0]) * c0;
        boolean joining = i == 0 && along0 < 0 && along0 > -JOIN_BEHIND && Math.abs(side0) < JOIN_SIDE;   // still rolling up to where the path begins
        if (Math.sqrt(best) > OFF_PATH && !joining) { stop(o); o.end = "off_path"; return; }
        if (rearBlocked && gear < 0) { stop(o); o.end = "rear_blocked"; return; }
        rearBlocked = false;

        double kappa;
        if (gear > 0) {
            int p0 = i, p1 = Math.min(legEnd, i + 2);
            while (p0 > 0 && p0 > i - 2 && dir[p0 - 1] == gear) p0--;
            double f0x = x[p0] + Math.cos(th[p0]) * wheelbase, f0y = y[p0] + Math.sin(th[p0]) * wheelbase, f1x = x[p1] + Math.cos(th[p1]) * wheelbase, f1y = y[p1] + Math.sin(th[p1]) * wheelbase;
            double tangent = p1 > p0 ? Math.atan2(f1y - f0y, f1x - f0x) : th[i];
            double c = Math.cos(tangent), s = Math.sin(tangent);
            double fx = rx + hx * wheelbase - (x[i] + Math.cos(th[i]) * wheelbase), fy = ry + hy * wheelbase - (y[i] + Math.sin(th[i]) * wheelbase);
            double e = -s * fx + c * fy;                                   // positive: the nose is to the positive-angle side of the path
            double delta = wrap(tangent - heading) - Math.atan2(STANLEY_GAIN * e, Math.abs(kmh) / 3.6 + 1.0);
            kappa = Math.tan(clampAngle(delta)) / wheelbase;
        } else {
            int a = Math.min(i + 3, legEnd);
            double ds = Math.max(1e-3, Math.hypot(x[a] - x[i], y[a] - y[i]));
            double feedForward = a > i ? wrap(th[a] - th[i]) / ds : 0;           // in the direction of travel, the mirror image of a car driving forward
            double along = th[i] + Math.PI, em = -Math.sin(along) * (rx - x[i]) + Math.cos(along) * (ry - y[i]);
            kappa = -(feedForward + REVERSE_HEADING * wrap(th[i] - heading) - REVERSE_LATERAL * em);
        }
        double lock = fullLockCurvature(kmh);
        o.steering = (float) Math.max(-1, Math.min(1, kappa / lock));

        if (now < settleUntil) { movedMs = now; o.forward = false; o.backward = false; o.brake = true; return; }   // the wheels swing to the new line first
        double target = 99;
        for (int k = i, top = Math.min(legEnd, i + SPEED_LOOK); k <= top; k++) target = Math.min(target, v[k]);
        double speed = gear > 0 ? kmh : -kmh;
        boolean wrongWay = speed < -0.8;
        o.brake = wrongWay || speed > target + 1.5;
        boolean drive = !o.brake && speed < target;
        o.forward = drive && gear > 0;
        o.backward = drive && gear < 0;
        driving = drive;
    }

    private static double clampAngle(double a) { return Math.max(-1.2, Math.min(1.2, a)); }
    private static void stop(Out o) { o.steering = 0; o.forward = false; o.backward = false; o.brake = true; }
}

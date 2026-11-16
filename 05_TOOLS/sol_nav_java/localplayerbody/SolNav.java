package localplayerbody;

import java.util.ArrayList;
import java.util.List;

import me.zed_0xff.zombie_buddy.Exposer;
import me.zed_0xff.zombie_buddy.Patch;
import se.krka.kahlua.integration.annotations.LuaMethod;
import zombie.characters.IsoGameCharacter;
import zombie.characters.IsoPlayer;
import zombie.core.physics.CarController;
import zombie.iso.IsoCell;
import zombie.iso.IsoGridSquare;
import zombie.iso.IsoWorld;
import zombie.pathfind.VehiclePoly;
import zombie.vehicles.BaseVehicle;

/**
 * Stage 3: the game side of Sol's navigation. Reads the ground in slices of at most 0.25 ms, plans on the worker,
 * then steers the car every frame from inside CarController.update. A heartbeat from Lua keeps it alive:
 * if the driving job goes away, control is handed straight back.
 */
@Exposer.LuaClass
public final class SolNav {
    private static final long BEAT_MS = 1200L, PLAN_BUDGET_NANOS = 2_000_000_000L, REAR_CHECK_MS = 100L;
    private static final SolNavCost COST = new SolNavCost("plan capture", 250_000L);
    private static final double BAN_RADIUS = 0.8;
    private static final float SOFT_OFF_ROAD = 0.25f, SOFT_OFF_ROAD_NEAR_ROAD = 1.0f;
    private static final List<double[]> BANS = new ArrayList<>();
    private static final List<double[]> CORRIDOR = new ArrayList<>();
    private static double corridorRadius;
    private static final double CORRIDOR_KEEP = 6;
    private static long nextRear;
    private static double trackHalfLength, trackHalfWidth;
    private static final int MAX_RADIUS = 35;
    private static final double PAD = 0.05;

    private static final class Capture {
        BaseVehicle car; int originX, originY, size, nx, ny; int[] shapes; final List<float[]> cars = new ArrayList<>(); boolean carsDone;
        double sx, sy, sth, gx, gy, gth, wheelbase, kFull, halfLength, halfWidth;
        boolean park, leg, mayTurnBack; List<double[]> pumps = new ArrayList<>(); double personX = Double.NaN, personY = Double.NaN; double pumpX, pumpY, capAlong, capSide, destX, destY;
        final List<double[]> bans = new ArrayList<>();
        final List<double[]> corridor = new ArrayList<>(); double corridorRadius;
    }

    private static Capture capture;
    private static boolean turnBackNext;
    private static String state = "idle";
    private static SolNavTrack ready;
    private static BaseVehicle readyCar;
    private static double readyWheelbase;

    private static volatile SolNavTrack track;
    private static volatile BaseVehicle trackCar;
    private static volatile long lastBeat;
    private static volatile String trackEnd;
    private static final SolNavTrack.Out OUT = new SolNavTrack.Out();
    private static final org.joml.Vector3f FWD = new org.joml.Vector3f();

    private SolNav() {}

    /** Once at game start, so the first plan does not pay for thread start and class loading. */
    @LuaMethod(name = "solNavWarmUp", global = true)
    public static void warmUp() { SolNavWorker.warmUp(); }

    /** Starts a plan for this car from its pose to a centre position and heading. False while another is running. kmax is the game's full-lock curvature. */
    @LuaMethod(name = "solNavPlan", global = true)
    public static boolean plan(BaseVehicle car, double sx, double sy, double hx, double hy, double gx, double gy, double ghx, double ghy, double wheelbase, double kFullLock) {
        trackEnd = null;
        if (capture != null || SolNavWorker.busy() || car == null || IsoWorld.instance == null || IsoWorld.instance.getCell() == null) return false;
        VehiclePoly p = car.getPoly();
        if (p == null) { state = "failed:no_measure"; return false; }
        double width = Math.hypot(p.x2 - p.x1, p.y2 - p.y1), length = Math.hypot(p.x3 - p.x2, p.y3 - p.y2);
        if (width < 0.5 || length < 1 || width > 6 || length > 16 || wheelbase < 0.5 || kFullLock <= 0) { state = "failed:no_measure"; return false; }
        Capture c = new Capture();
        int radius = (int) Math.ceil(Math.max(Math.abs(gx - sx), Math.abs(gy - sy)) / 2) + 12;
        if (radius > MAX_RADIUS) { state = "failed:goal_too_far"; return false; }
        int mx = (int) Math.floor((sx + gx) / 2), my = (int) Math.floor((sy + gy) / 2);
        c.car = car; c.originX = mx - radius; c.originY = my - radius; c.size = 2 * radius + 1; c.shapes = new int[c.size * c.size];
        double half = wheelbase / 2, n = Math.hypot(hx, hy), gn = Math.hypot(ghx, ghy);
        if (n < 1e-3 || gn < 1e-3) { state = "failed:no_heading"; return false; }
        c.sx = sx - hx / n * half; c.sy = sy - hy / n * half; c.sth = Math.atan2(hy, hx);
        c.gx = gx - ghx / gn * half; c.gy = gy - ghy / gn * half; c.gth = Math.atan2(ghy, ghx);
        c.wheelbase = wheelbase; c.kFull = kFullLock * 0.93; c.halfLength = length / 2; c.halfWidth = width / 2;
        c.bans.addAll(BANS);
        c.corridor.addAll(CORRIDOR); c.corridorRadius = corridorRadius;
        c.mayTurnBack = turnBackNext; turnBackNext = false;
        capture = c; state = "capturing"; ready = null;
        return true;
    }

    /** One stage of the drive beyond the road, toward a point it does not reach. */
    @LuaMethod(name = "solNavLeg", global = true)
    public static boolean leg(BaseVehicle car, double sx, double sy, double hx, double hy, double destX, double destY, double wheelbase, double kFullLock) {
        trackEnd = null;
        if (capture != null || SolNavWorker.busy() || car == null || IsoWorld.instance == null || IsoWorld.instance.getCell() == null) return false;
        VehiclePoly p = car.getPoly();
        double n = Math.hypot(hx, hy);
        if (p == null || n < 1e-3 || wheelbase < 0.5 || kFullLock <= 0) { state = "failed:no_measure"; return false; }
        double width = Math.hypot(p.x2 - p.x1, p.y2 - p.y1), length = Math.hypot(p.x3 - p.x2, p.y3 - p.y2);
        if (width < 0.5 || length < 1 || width > 6 || length > 16) { state = "failed:no_measure"; return false; }
        double dist = Math.hypot(destX - sx, destY - sy), step = SolNavLegPlan.chunkLength(dist);
        double midX = sx + (destX - sx) / Math.max(1e-3, dist) * step / 2, midY = sy + (destY - sy) / Math.max(1e-3, dist) * step / 2;
        int radius = (int) Math.ceil(step / 2) + 14;
        if (radius > MAX_RADIUS) radius = MAX_RADIUS;
        Capture c = new Capture();
        c.car = car; c.originX = (int) Math.floor(midX) - radius; c.originY = (int) Math.floor(midY) - radius; c.size = 2 * radius + 1; c.shapes = new int[c.size * c.size];
        c.sx = sx - hx / n * wheelbase / 2; c.sy = sy - hy / n * wheelbase / 2; c.sth = Math.atan2(hy, hx);
        c.wheelbase = wheelbase; c.kFull = kFullLock * 0.93; c.halfLength = length / 2; c.halfWidth = width / 2;
        c.leg = true; c.destX = destX; c.destY = destY;
        capture = c; state = "capturing"; ready = null;
        return true;
    }

    /** The next plan may turn back or reverse far: only once forward tries have found nothing. */
    @LuaMethod(name = "solNavMayTurnBack", global = true)
    public static void mayTurnBack() { turnBackNext = true; }

    /** Places that failed: the next plan will not go through them. */
    @LuaMethod(name = "solNavCorridorClear", global = true)
    public static void corridorClear() { CORRIDOR.clear(); }

    @LuaMethod(name = "solNavCorridorPoint", global = true)
    public static void corridorPoint(double x, double y) { CORRIDOR.add(new double[] { x, y }); }

    @LuaMethod(name = "solNavCorridorRadius", global = true)
    public static void corridorRadius(double r) { corridorRadius = r; }

    @LuaMethod(name = "solNavBanClear", global = true)
    public static void banClear() { BANS.clear(); }
    @LuaMethod(name = "solNavBan", global = true)
    public static void ban(double x, double y) { BANS.add(new double[] { x, y }); }

    /** Plans to a stop beside this pump: fuel cap towards it, a walkable gap, and a way from her door to the cap. */
    @LuaMethod(name = "solNavPark", global = true)
    public static boolean park(BaseVehicle car, double sx, double sy, double hx, double hy, double pumpX, double pumpY, double capAlong, double capSide, double wheelbase, double kFullLock) {
        trackEnd = null;
        if (capture != null || SolNavWorker.busy() || car == null || IsoWorld.instance == null || IsoWorld.instance.getCell() == null) return false;
        VehiclePoly p = car.getPoly();
        double n = Math.hypot(hx, hy);
        if (p == null || n < 1e-3 || wheelbase < 0.5 || kFullLock <= 0) { state = "failed:no_measure"; return false; }
        double width = Math.hypot(p.x2 - p.x1, p.y2 - p.y1), length = Math.hypot(p.x3 - p.x2, p.y3 - p.y2);
        if (width < 0.5 || length < 1 || width > 6 || length > 16) { state = "failed:no_measure"; return false; }
        int radius = (int) Math.ceil(Math.max(Math.abs(pumpX - sx), Math.abs(pumpY - sy)) / 2) + 14;
        if (radius > MAX_RADIUS) { state = "failed:goal_too_far"; return false; }
        Capture c = new Capture();
        int mx = (int) Math.floor((sx + pumpX) / 2), my = (int) Math.floor((sy + pumpY) / 2);
        c.car = car; c.originX = mx - radius; c.originY = my - radius; c.size = 2 * radius + 1; c.shapes = new int[c.size * c.size];
        c.sx = sx - hx / n * wheelbase / 2; c.sy = sy - hy / n * wheelbase / 2; c.sth = Math.atan2(hy, hx);
        c.wheelbase = wheelbase; c.kFull = kFullLock * 0.93; c.halfLength = length / 2; c.halfWidth = width / 2;
        c.park = true; c.pumpX = pumpX; c.pumpY = pumpY; c.capAlong = capAlong; c.capSide = capSide;
        c.pumps = SolStations.pumpsOfStation(pumpX, pumpY);
        if (c.pumps.isEmpty()) c.pumps.add(new double[] { pumpX, pumpY });
        IsoPlayer me = IsoPlayer.getInstance();
        if (me != null && me.getVehicle() == null) { c.personX = me.getX(); c.personY = me.getY(); }
        capture = c; state = "capturing"; ready = null;
        return true;
    }

    /** Called every frame: one sliver of reading, then the worker's answer. */
    @LuaMethod(name = "solNavStep", global = true)
    public static void step() {
        Capture c = capture;
        if (c != null) {
            long t0 = System.nanoTime();
            try {
                IsoCell cell = IsoWorld.instance == null ? null : IsoWorld.instance.getCell();
                if (cell == null) { capture = null; state = "failed:no_world"; return; }
                if (!c.carsDone) {
                    for (BaseVehicle v : cell.getVehicles()) {
                        if (v == c.car || v == c.car.getVehicleTowing() || v == c.car.getVehicleTowedBy()) continue;
                        VehiclePoly p = v.getPoly();
                        if (p != null && v.getX() > c.originX - 6 && v.getX() < c.originX + c.size + 6 && v.getY() > c.originY - 6 && v.getY() < c.originY + c.size + 6)
                            c.cars.add(new float[] { p.x1, p.y1, p.x2, p.y2, p.x3, p.y3, p.x4, p.y4 });
                    }
                    c.carsDone = true;
                } else {
                    while (c.ny < c.size) {
                        IsoGridSquare sq = cell.getGridSquare(c.originX + c.nx, c.originY + c.ny, 0);
                        c.shapes[c.ny * c.size + c.nx] = sq == null ? -1 : SolPerception.navShapeOf(sq);
                        if (++c.nx >= c.size) { c.nx = 0; c.ny++; }
                        if (System.nanoTime() - t0 >= COST.slice()) break;
                    }
                    if (c.ny >= c.size) { capture = null; submit(c); }
                }
            } catch (RuntimeException e) {
                capture = null; state = "failed:capture";
                System.out.println("[SolNav] capture stopped: " + e);
            }
            COST.note(System.nanoTime() - t0);
            return;
        }
        if ("planning".equals(state)) {
            SolNavPlanner.Result r = SolNavWorker.poll();
            if (r == null) return;
            if (r.path == null || r.track == null) { state = "failed:" + r.why; return; }
            ready = r.track; state = "ready";
        }
    }

    private static void submit(Capture c) {
        readyCar = c.car; readyWheelbase = c.wheelbase; trackHalfLength = c.halfLength; trackHalfWidth = c.halfWidth;
        boolean ok = SolNavWorker.submitTask(() -> {
            int size = c.size * 10;
            boolean[] occ = occupancy(c);
            SolNavPlanner.Grid grid = new SolNavPlanner.Grid(size, size, c.originX, c.originY, occ);
            grid.soft = softCost(c);
            SolNavPlanner.Car car = new SolNavPlanner.Car(c.halfLength, c.halfWidth, c.wheelbase, c.kFull * 0.7, PAD);
            SolNavPlanner.Result r = c.leg ? SolNavLegPlan.plan(grid, car, c.wheelbase, c.sx, c.sy, c.sth, c.destX, c.destY) : c.park ? parkPlan(c, grid, car) : SolNavPlanner.planSafe(grid, car, c.sx, c.sy, c.sth, c.gx, c.gy, c.gth, PLAN_BUDGET_NANOS, c.mayTurnBack);
            if (r.path != null) {
                r.path = SolNavPlanner.smooth(grid, car, r.path);
                r.track = new SolNavTrack(r.path, SolNavPlanner.speeds(grid, car, r.path), c.wheelbase, c.kFull);
                System.out.println(String.format(java.util.Locale.ROOT, "[SolNav] planned %d poses, %d nodes, %.0f ms", r.path.size(), r.nodes, r.ms));
            } else System.out.println("[SolNav] no plan: " + r.why);
            return r;
        });
        state = ok ? "planning" : "failed:busy";
    }

    private static SolNavPlanner.Result parkPlan(Capture c, SolNavPlanner.Grid grid, SolNavPlanner.Car car) {
        List<double[]> inside = new ArrayList<>();
        for (double[] p : c.pumps) if (p[0] > c.originX + 3 && p[0] < c.originX + c.size - 3 && p[1] > c.originY + 3 && p[1] < c.originY + c.size - 3) inside.add(p);
        System.out.println("[SolNav] station: " + inside.size() + " pumps looked at");
        return SolNavPark.plan(grid, car, SolNavPark.stationSpots(grid, car, c.halfLength, c.halfWidth, c.wheelbase, inside, c.cars, c.personX, c.personY, c.capAlong, c.capSide, c.sx, c.sy, c.sth), c.wheelbase, c.sx, c.sy, c.sth);
    }

    /** Runs on the worker: unpaved ground costs a little more, so she keeps to paving when it is no real detour. */
    static float[] softCost(Capture c) {
        int n = c.size * 10;
        float[] soft = new float[n * n];
        for (int ty = 0; ty < c.size; ty++) for (int tx = 0; tx < c.size; tx++) {
            int s = c.shapes[ty * c.size + tx];
            if (s < 0 || (s & SolPerception.OFF_ROAD) == 0) continue;
            float cost = c.corridor.isEmpty() ? SOFT_OFF_ROAD : SOFT_OFF_ROAD_NEAR_ROAD;                    // going round something on the road: keep to the paving and shoulder while there is room
            for (int j = 0; j < 10; j++) java.util.Arrays.fill(soft, (ty * 10 + j) * n + tx * 10, (ty * 10 + j) * n + tx * 10 + 10, cost);
        }
        return soft;
    }

    /** Runs on the worker. The same shapes as the perception picture, plus every other car; squares not loaded count as shut. */
    static boolean[] occupancy(Capture c) {
        byte[] img = SolPerception.rasterize(c.shapes, c.size, c.cars, c.originX, c.originY);
        boolean[] occ = new boolean[img.length];
        for (int i = 0; i < img.length; i++) occ[i] = img[i] != 0;
        int n = c.size * 10;
        for (double[] b : c.bans) SolNavPlanner.ban(occ, n, n, c.originX, c.originY, b[0], b[1], BAN_RADIUS);
        if (!c.leg && !c.park && !c.corridor.isEmpty()) applyCorridor(occ, c.size, c.originX, c.originY, c.corridor, c.corridorRadius, c.sx, c.sy, c.gx, c.gy);
        return occ;
    }

    /** A way round may only use ground near the road. The car's own start and goal stay open, so she can always leave and rejoin. */
    static void applyCorridor(boolean[] occ, int size, int ox, int oy, List<double[]> pts, double radius, double sx, double sy, double gx, double gy) {
        int n = size * 10;
        double r2 = radius * radius, keep2 = CORRIDOR_KEEP * CORRIDOR_KEEP;
        for (int ty = 0; ty < size; ty++) for (int tx = 0; tx < size; tx++) {
            double cx = ox + tx + 0.5, cy = oy + ty + 0.5;
            if ((cx - sx) * (cx - sx) + (cy - sy) * (cy - sy) <= keep2 || (cx - gx) * (cx - gx) + (cy - gy) * (cy - gy) <= keep2) continue;
            boolean near = false;
            for (int i = 0; i < pts.size() && !near; i++) {
                double[] a = pts.get(i), b = pts.get(Math.min(i + 1, pts.size() - 1));
                double dx = b[0] - a[0], dy = b[1] - a[1], len2 = dx * dx + dy * dy;
                double u = len2 > 0 ? Math.max(0, Math.min(1, ((cx - a[0]) * dx + (cy - a[1]) * dy) / len2)) : 0;
                double px = a[0] + dx * u - cx, py = a[1] + dy * u - cy;
                near = px * px + py * py <= r2;
            }
            if (near) continue;
            for (int j = 0; j < 10; j++) java.util.Arrays.fill(occ, (ty * 10 + j) * n + tx * 10, (ty * 10 + j) * n + tx * 10 + 10, true);
        }
    }

    @LuaMethod(name = "solNavState", global = true)
    public static String state() {
        if (track != null) return "following";
        if (trackEnd != null) return trackEnd;
        return state;
    }

    /** Takes over the wheel on the ready path. */
    @LuaMethod(name = "solNavFollow", global = true)
    public static boolean follow() {
        if (ready == null || readyCar == null) return false;
        trackEnd = null; lastBeat = System.currentTimeMillis();
        trackCar = readyCar; track = ready;
        ready = null; state = "idle";
        return true;
    }

    /** Lua's heartbeat while the driving job is alive. */
    @LuaMethod(name = "solNavBeat", global = true)
    public static void beat() { lastBeat = System.currentTimeMillis(); }

    @LuaMethod(name = "solNavStop", global = true)
    public static void stop() { track = null; trackCar = null; trackEnd = null; capture = null; ready = null; state = "idle"; }

    /** Inside CarController.update: the last moment before the game reads the controls. */
    public static void applyControls(CarController cc) {
        SolNavTrack t = track;
        if (t == null || cc.vehicleObject != trackCar) return;
        BaseVehicle car = trackCar;
        long now = System.currentTimeMillis();
        if (now - lastBeat > BEAT_MS) { end("failed:job_gone"); return; }
        IsoGameCharacter d = car.getDriver();
        if (d == null || (d instanceof IsoPlayer && ((IsoPlayer) d).isLocalPlayer())) { end("failed:driver_changed"); return; }
        car.getForwardVector(FWD);
        double n = Math.hypot(FWD.x, FWD.z);
        if (n < 1e-3) return;
        double fx = FWD.x / n, fz = FWD.z / n;
        if (t.reversing() && now >= nextRear) { nextRear = now + REAR_CHECK_MS; if (rearBlocked(car, fx, fz, t.reverseLeft())) t.rearBlocked(); }
        t.update(car.getX(), car.getY(), fx, fz, car.getCurrentSpeedKmHour(), now, OUT);
        if (OUT.note != null) System.out.println("[SolNav] " + OUT.note);
        CarController.ClientControls c = cc.clientControls;
        c.steering = OUT.steering; c.forward = OUT.forward; c.backward = OUT.backward; c.brake = OUT.brake; c.shift = false;
        if (OUT.end != null) end("done".equals(OUT.end) ? "done" : "failed:" + OUT.end);
    }

    /** Just behind the rear bumper: a wall, a car or ground not loaded. The plan cleared this when it was drawn, so anything here is new. */
    private static boolean rearBlocked(BaseVehicle car, double hx, double hy, double left) {
        IsoCell cell = IsoWorld.instance == null ? null : IsoWorld.instance.getCell();
        if (cell == null) return true;
        double cx = car.getX(), cy = car.getY();
        for (double back = 0.3; back <= 0.61 && back <= left; back += 0.3) for (int k = -1; k <= 1; k++) {
            double a = trackHalfLength + back, b = k * trackHalfWidth;
            double x = cx - hx * a - hy * b, y = cy - hy * a + hx * b;
            int tx = (int) Math.floor(x), ty = (int) Math.floor(y);
            IsoGridSquare sq = cell.getGridSquare(tx, ty, 0);
            if (sq == null || SolPerception.pointBlocked(SolPerception.shapeOf(sq, null), x - tx, y - ty)) return true;
            for (BaseVehicle v : cell.getVehicles()) {
                if (v == car || v == car.getVehicleTowing() || v == car.getVehicleTowedBy()) continue;
                VehiclePoly p = v.getPoly();
                if (p != null && SolPerception.inside(new float[] { p.x1, p.y1, p.x2, p.y2, p.x3, p.y3, p.x4, p.y4 }, x, y)) return true;
            }
        }
        return false;
    }

    private static void end(String how) { track = null; trackCar = null; trackEnd = how; System.out.println("[SolNav] " + how); }

    @Patch(className = "zombie.core.physics.CarController", methodName = "update")
    public static final class ControlHook {
        @Patch.OnEnter
        public static void enter(@Patch.This CarController self) { SolNav.applyControls(self); SolSteerAdapt.apply(self); }
    }
}

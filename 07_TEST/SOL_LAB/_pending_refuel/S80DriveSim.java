package survivorcompanion.bridge;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;

/**
 * s80 speed_levels: drives a scene through the driving code the lab ships (SCRoadFollower, SCTurnAround, SCLaneScan,
 * SCDriveControl from a COPY of SolCombined.jar, the s80 one for 65 km/h), per frame as SCCompanionDriver.driveRoute does
 * (05_TOOLS/sol_drive_sim/DriveSim.java, extended). Added: a car body per vehicle (half sizes, wheelbase, steering lock),
 * a brake deceleration, acceleration and top speed, a sideways grip limit (a car cannot turn tighter than v^2 / grip),
 * and the Lua governor on stdin/stdout: every 0.3 s it prints "G t x y speed cruise mode" and reads "-" or
 * "S kmh route", which re-issues the route as SCBridge.driveFollow -> SCCompanionDriver.follow does (a new follower).
 * Scene lines: car x y hx hy halfW halfL wheelbase lock | phys brake accel maxKmh grip | cruise kmh | route text |
 * solid x1 y1 x2 y2 | mark x y | gov on
 * Output: one line "R result=... t=... vmax=... marks=v@d,... maxlat=(widest off the route centre line) x y".
 */
final class S80DriveSim {
    private static final float DT = 1.0f / 60.0f;
    private static final float BLOCK_REPORT_MS = 400f;

    public static void main(String[] args) throws Exception {
        List<String> lines = Files.readAllLines(Path.of(args[0]));
        float limitS = args.length > 1 ? Float.parseFloat(args[1]) : 120f;
        float x = 0, y = 0, hx = 1, hy = 0, halfW = 0.85f, halfL = 2.1f, wheelbase = 2.5f, lock = 0.6f, cruise = 20;
        float brake = 3f, accel = 15f, maxKmh = 90f, grip = 5f;
        boolean gov = false;
        String routeText = "";
        HashSet<Long> solid = new HashSet<>();
        java.util.ArrayList<float[]> marks = new java.util.ArrayList<>();
        for (String line : lines) {
            String[] p = line.trim().split("\\s+");
            switch (p[0]) {
                case "car" -> { x = f(p[1]); y = f(p[2]); hx = f(p[3]); hy = f(p[4]); halfW = f(p[5]); halfL = f(p[6]); wheelbase = f(p[7]); lock = f(p[8]); }
                case "phys" -> { brake = f(p[1]); accel = f(p[2]); maxKmh = f(p[3]); grip = f(p[4]); }
                case "cruise" -> cruise = f(p[1]);
                case "route" -> routeText = p[1];
                case "gov" -> gov = p[1].equals("on");
                case "mark" -> marks.add(new float[] { f(p[1]), f(p[2]), 1e9f, -1f });
                case "solid" -> {
                    for (int a = (int) f(p[1]); a <= (int) f(p[3]); a++)
                        for (int b = (int) f(p[2]); b <= (int) f(p[4]); b++) solid.add(key(a, b));
                }
                default -> { }
            }
        }
        SCLaneScan.World world = new SCLaneScan.World() {
            @Override public int squareKind(int a, int b, int z) { return solid.contains(key(a, b)) ? SCLaneScan.SOLID : SCLaneScan.CLEAR; }
            @Override public boolean edgeBlocked(int a, int b, int c, int d, int z) { return false; }
        };
        SCDrivePath path = SCDrivePath.parse(routeText);
        if (path == null) { System.out.println("R result=bad_route"); return; }
        SCRoadFollower follower = new SCRoadFollower(path, cruise, true, false, 1.0f);
        SCDrivePath.Projection pj = new SCDrivePath.Projection();
        float maxLat = 0;
        SCRoadFollower.Command command = new SCRoadFollower.Command();
        SCLaneScan.Result lastScan = new SCLaneScan.Result(), lastRear = new SCLaneScan.Result();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        float speed = 0, stuckMs = 0, t = 0, nextScan = 0, nextGov = 0, vmax = 0, minFront = 1e9f;
        int reissues = 0, safetyFrames = 0;
        String state = "", result = "timeout";
        while (t < limitS) {
            float len = (float) Math.hypot(hx, hy);
            hx /= len; hy /= len;
            if (gov && t >= nextGov) {
                nextGov = t + 0.3f;
                String mode = follower.mode() == SCRoadFollower.Mode.FOLLOW
                        ? (Math.abs(follower.offset() - follower.laneOffset()) > 0.25f ? "avoiding" : "follow")
                        : follower.mode().name().toLowerCase(Locale.ROOT);
                if (state.equals("safety_blocked")) mode = "blocked";
                System.out.printf(Locale.ROOT, "G %d %.3f %.3f %.3f %.3f %s%n", (long) (t * 1000), x, y, speed, follower.cruiseKmh(), mode);
                System.out.flush();
                String reply = in.readLine();
                if (reply != null && reply.startsWith("S ")) {
                    String[] q = reply.split(" ");
                    SCDrivePath np = SCDrivePath.parse(q[2]);
                    if (np != null) { follower = new SCRoadFollower(np, Float.parseFloat(q[1]), true, false, 1.0f); reissues++; }
                }
            }
            if (t >= nextScan) {
                nextScan = t + 0.1f;
                lastScan.copyFrom(SCLaneScan.scan(world, x, y, 0, hx, hy, halfW, halfL + 0.1f, SCCompanionDriver.lookAheadFor(follower.cruiseKmh())));
                lastRear.copyFrom(SCLaneScan.scan(world, x, y, 0, -hx, -hy, halfW, halfL + 0.1f, 4.0f));
            }
            float front = lastScan.blocked ? lastScan.distance : -1f;
            float rear = lastRear.blocked ? lastRear.distance : -1f;
            if (front >= 0 && front < minFront) minFront = front;
            follower.update(world, x, y, 0, hx, hy, speed, halfW, halfL, front, rear, (long) (t * 1000), command);
            SCDriveControl.Input input = command.targetKmh < 0f
                    ? SCDriveControl.reverse(speed, -command.targetKmh, command.steering, rear)
                    : SCDriveControl.cruise(speed, command.targetKmh, command.steering, front, command.maneuver ? 1.0f : 3.0f);
            SCRoadFollower.Mode mode = follower.mode();
            if (mode == SCRoadFollower.Mode.FOLLOW) {
                float gap = command.maneuver ? 1.0f : 3.0f;
                if (command.targetKmh > 0f && SCDriveControl.mustStop(speed, front, gap)) { state = "safety_blocked"; safetyFrames++; }
                else state = "following";
            } else state = mode.name().toLowerCase(Locale.ROOT);
            if (mode == SCRoadFollower.Mode.ARRIVED) { result = "arrived"; break; }
            if (mode == SCRoadFollower.Mode.TURN_FAILED) { result = "turn_failed"; break; }
            boolean blockedNow = mode == SCRoadFollower.Mode.BLOCKED || state.equals("safety_blocked");
            stuckMs = blockedNow && Math.abs(speed) <= 0.6f ? stuckMs + DT * 1000 : 0;
            if (stuckMs >= BLOCK_REPORT_MS) { result = "blocked"; break; }
            if (input.brake()) speed = approach(speed, 0, brake * 3.6f * DT);
            else if (input.forward()) speed = Math.min(speed + accel * DT, maxKmh);
            else if (input.backward()) speed = Math.max(speed - 10 * DT, -8);
            else speed = approach(speed, 0, 4 * DT);
            vmax = Math.max(vmax, speed);
            float v = speed / 3.6f, step = v * DT;
            float k = (float) Math.tan(input.steering() * lock) / wheelbase;
            if (Math.abs(v) > 1f) { float kmax = grip / (v * v); k = Math.max(-kmax, Math.min(kmax, k)); }
            float heading = (float) Math.atan2(hy, hx) + step * k;
            hx = (float) Math.cos(heading); hy = (float) Math.sin(heading);
            x += hx * step; y += hy * step;
            for (float[] m : marks) {
                float d = (float) Math.hypot(x - m[0], y - m[1]);
                if (d < m[2]) { m[2] = d; m[3] = speed; }
            }
            path.project(x, y, -1, pj);
            maxLat = Math.max(maxLat, Math.abs(pj.lateral));
            if (hits(solid, x, y, hx, hy, halfW, halfL)) { result = "crash"; break; }
            t += DT;
        }
        StringBuilder ms = new StringBuilder();
        for (float[] m : marks) ms.append(ms.length() > 0 ? "," : "").append(String.format(Locale.ROOT, "%.0f@%.1f", m[3], m[2]));
        System.out.printf(Locale.ROOT, "R result=%s t=%.1f vmax=%.1f marks=%s reissues=%d safety=%d minfront=%.1f maxlat=%.1f x=%.1f y=%.1f%n",
                result, t, vmax, ms, reissues, safetyFrames, minFront, maxLat, x, y);
        System.out.flush();
    }

    private static float f(String s) { return Float.parseFloat(s); }
    private static long key(int a, int b) { return ((long) a << 32) ^ (b & 0xffffffffL); }
    private static float approach(float v, float to, float by) { return v > to ? Math.max(to, v - by) : Math.min(to, v + by); }

    private static boolean hits(HashSet<Long> solid, float x, float y, float hx, float hy, float halfW, float halfL) {
        for (float a = -halfL; a <= halfL + 0.01f; a += 0.4f)
            for (float b = -halfW; b <= halfW + 0.01f; b += 0.4f) {
                int sx = (int) Math.floor(x + hx * a - hy * b), sy = (int) Math.floor(y + hy * a + hx * b);
                if (solid.contains(key(sx, sy))) return true;
            }
        return false;
    }
}

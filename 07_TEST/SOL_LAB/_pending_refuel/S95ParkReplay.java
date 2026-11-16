package localplayerbody;

import java.util.ArrayList;
import java.util.List;

/**
 * s95 evidence: the shipped Java park (SolNavPark.stationSpots + plan) on the real gas2go forecourt read from
 * SolPerception_1794354139165.txt (2026-11-11 00:42, lab), the small car Sol drove (3.36 x 1.38, wheelbase 1.94, from
 * "[SolBypass] measured the car"), fuel cap from its vehicle script area GasTank (-0.5989, -0.6703) x scale 1.82.
 * Prints how many stops the old planner finds and why the others were dropped. Offline evidence, not a game run.
 * Build: javac -d <out> SolNavPlanner.java SolNavPark.java (+ deps) S95ParkReplay.java ; java -cp <out> localplayerbody.S95ParkReplay
 */
public final class S95ParkReplay {
    static final int OX = 7286, OY = 8158, TILES = 50, N = TILES * 10;

    static void fill(boolean[] o, double x0, double y0, double x1, double y1) {
        for (int y = (int) Math.floor((y0 - OY) * 10); y < Math.ceil((y1 - OY) * 10); y++)
            for (int x = (int) Math.floor((x0 - OX) * 10); x < Math.ceil((x1 - OX) * 10); x++)
                if (x >= 0 && y >= 0 && x < N && y < N) o[y * N + x] = true;
    }
    static void poly(boolean[] o, float[] p) {
        for (int y = 0; y < N; y++) for (int x = 0; x < N; x++) {
            double px = OX + (x + 0.5) / 10.0, py = OY + (y + 0.5) / 10.0;
            boolean in = false;
            for (int i = 0, j = 3; i < 4; j = i++) {
                double xi = p[2 * i], yi = p[2 * i + 1], xj = p[2 * j], yj = p[2 * j + 1];
                if ((yi > py) != (yj > py) && px < (xj - xi) * (py - yi) / (yj - yi) + xi) in = !in;
            }
            if (in) o[y * N + x] = true;
        }
    }

    public static void main(String[] a) {
        String[] tiles = a.length > 0 ? a[0].split(" ") : new String[0];
        boolean[] occ = new boolean[N * N];
        for (String t : tiles) {
            String[] f = t.split(",");
            if (f.length < 3) continue;
            int x = Integer.parseInt(f[0]), y = Integer.parseInt(f[1]), s = Integer.parseInt(f[2]);
            if ((s & 1) != 0) fill(occ, x, y, x + 1, y + 1);
            if ((s & 2) != 0) fill(occ, x + 0.3, y + 0.3, x + 0.7, y + 0.7);
            if ((s & 4) != 0) fill(occ, x, y, x + 1, y + 0.1);
            if ((s & 8) != 0) fill(occ, x, y, x + 0.1, y + 1);
        }
        List<float[]> cars = new ArrayList<>();
        cars.add(new float[] { 7310.50f, 8177.30f, 7310.50f, 8175.70f, 7306.48f, 8175.70f, 7306.48f, 8177.30f });
        cars.add(new float[] { 7319.43f, 8177.32f, 7319.42f, 8175.68f, 7314.58f, 8175.68f, 7314.59f, 8177.32f });
        cars.add(new float[] { 7316.65f, 8203.50f, 7318.35f, 8203.50f, 7318.35f, 8199.26f, 7316.65f, 8199.26f });
        if (a.length > 1 && a[1].equals("south")) cars.add(new float[] { 7305.91f, 8179.72f, 7305.90f, 8181.10f, 7309.26f, 8181.13f, 7309.27f, 8179.75f });   // the 00:40 stop, left there
        for (float[] c : cars) poly(occ, c);
        SolNavPlanner.Grid g = new SolNavPlanner.Grid(N, N, OX, OY, occ);
        double hl = 1.68, hw = 0.69, wb = 1.94;
        SolNavPlanner.Car car = new SolNavPlanner.Car(hl, hw, wb, 0.5 * 0.93 * 0.7, 0.05);
        List<double[]> pumps = new ArrayList<>();
        pumps.add(new double[] { 7308, 8178 });
        pumps.add(new double[] { 7316, 8178 });
        double[][] starts = { { 7290.0, 8180.5, 0 }, { 7313.0, 8186.0, -Math.PI / 2 }, { 7325.0, 8181.0, Math.PI } };
        for (double side : new double[] { 1.09, -1.09 }) {
            for (double[] s : starts) {
                List<SolNavPark.Spot> spots = SolNavPark.stationSpots(g, car, hl, hw, wb, pumps, cars, Double.NaN, Double.NaN, -1.22, side, s[0] - Math.cos(s[2]) * wb / 2, s[1] - Math.sin(s[2]) * wb / 2, s[2]);
                int raw = 0, reach = 0, free = 0, walk = 0;
                for (double[] p : pumps) {
                    double pumpX = p[0] + 0.5, pumpY = p[1] + 0.5, sd = side >= 0 ? 1 : -1;
                    for (double gap = SolNavPark.GAP_MIN + 0.1; gap <= SolNavPark.GAP_MAX + 1e-9; gap += 0.3) for (int k = 0; k < 8; k++) {
                        raw++;
                        double th = k * Math.PI / 4, c = Math.cos(th), sn = Math.sin(th);
                        double along = -1.22, lateral = sd * (0.5 + gap + hw);
                        double cx = pumpX - (c * along - sn * lateral), cy = pumpY - (sn * along + c * lateral);
                        double rx = cx - c * wb / 2, ry = cy - sn * wb / 2;
                        double capX = cx + c * along - sn * side, capY = cy + sn * along + c * side;
                        if (Math.abs(Math.floor(capX) - Math.floor(p[0])) > 2 || Math.abs(Math.floor(capY) - Math.floor(p[1])) > 2) { reach++; continue; }
                        if (!SolNavPlanner.freeAt(g, car, rx, ry, th)) { free++; continue; }
                        if (!SolNavPark.walkable(g, cx, cy, c, sn, hl, hw, along, side, false)) { walk++; continue; }
                    }
                }
                SolNavPlanner.Result r = SolNavPark.plan(g, car, spots, wb, s[0] - Math.cos(s[2]) * wb / 2, s[1] - Math.sin(s[2]) * wb / 2, s[2]);
                System.out.printf(java.util.Locale.ROOT, (a.length > 1 ? "[" + a[1] + "] " : "") + "cap side %+.2f, start %.0f,%.0f heading %.0f: %d stops (of %d: %d out of the game's reach, %d body hits something, %d no walk to the cap); plan: %s%n",
                    side, s[0], s[1], Math.toDegrees(s[2]), spots.size(), raw, reach, free, walk, r.path != null ? "found" : r.why);
            }
        }
    }
}

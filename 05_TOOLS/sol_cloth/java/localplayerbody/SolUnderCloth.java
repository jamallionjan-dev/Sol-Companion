package localplayerbody;

import java.io.DataInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;

/**
 * Sol: the chest shape UNDER painted clothing (s159, 2026-11-16).
 *
 * Jamal accepted one shape (05_TOOLS/sol_cloth, chest_preview6 column 3): the bust keeps its two mounds, the tips are
 * gone, it is held a little up and in, and the cloth bridges the valley and the fold underneath only partly. Bare, she
 * must stay exactly as she is.
 *
 * The body patch already keeps two chest shapes per body: BraGeometry.bare and BraGeometry.fitted, per-vertex offsets
 * in the body's canonical space that BraGeometry.apply(positions, bra) ADDS to the positions; which one is used follows
 * Physics.capFit (a bra is worn / an audited garment covers the chest) and, in preview windows, PreviewSupport.bra.
 * This class changes two things and nothing else:
 *   refit   called at the end of the BraGeometry constructor: for the large body the "fitted" offsets become the
 *           accepted shape (and the bare offsets everywhere else), so "fitted" = bare + under-cloth chest.
 *   holds   Physics.bra / PreviewSupport.bra also say yes for a painted top over the chest (a clothing item without a
 *           mesh of its own), so the fitted shape is used under a T-shirt as it is with a bra.
 * The bare shape (BraGeometry.bare) is never written.
 *
 * Switch: the line under_cloth=on in SolFixes_LAB.txt, else in SolFixes_MAIN.txt, read once per game session; anything
 * else is off (a stale lab file in the main profile must not turn it on). Off: both hooks return at once and the body patch behaves as before.
 * Any failure (data missing, body not recognised) leaves the original arrays untouched and logs one line.
 */
public final class SolUnderCloth {
    static final String FILE_VERSION = "undercloth-1";
    private static final String[] TOPS = {"tshirt", "shirt", "tanktop", "sweater", "jersey", "dress", "fullsuit", "boilersuit",
        "bathrobe", "fulltop", "torsoextra", "vest"};
    private static Boolean enabled;
    private static boolean said;

    private SolUnderCloth() {}

    static synchronized boolean enabled() {
        if (enabled != null) return enabled;
        boolean on = false;
        try {
            String dir = zombie.ZomboidFileSystem.instance.getCacheDir();
            Path lab = Path.of(dir, "Lua", "SolFixes_LAB.txt"), main = Path.of(dir, "Lua", "SolFixes_MAIN.txt");
            String v = Files.isRegularFile(lab) ? value(lab) : null;
            if (v == null && Files.isRegularFile(main)) v = value(main);
            on = "on".equals(v);                                   // only an explicit under_cloth=on turns it on
        } catch (Throwable t) {
            on = false;
        }
        enabled = on;
        System.out.println("[SolUnderCloth] switch under_cloth " + (on ? "ON" : "OFF"));
        return on;
    }

    private static String value(Path file) throws Exception {
        List<String> lines = Files.readAllLines(file);
        String found = null;
        for (String line : lines) {
            String s = line.trim();
            if (s.startsWith("under_cloth=")) found = s.substring("under_cloth=".length()).trim().toLowerCase(Locale.ROOT);
        }
        return found;
    }

    // ------------------------------------------------------------------ the shape

    /** End of BraGeometry.<init>(canonical, elements, size): fitted/bare are that object's own arrays. */
    static void refit(double[][] canonical, int[] elements, String size, double[][] fitted, double[][] bare, String version) {
        try {
            if (!enabled() || canonical == null || fitted == null || bare == null) return;
            String sz = size == null || size.isEmpty() ? "L" : size.toUpperCase(Locale.ROOT);
            float[][] data = load(sz);
            if (data == null) { say("no under-cloth shape for size " + sz + "; that size keeps the patch's own shape"); return; }
            double[][] out = compute(canonical, fitted, bare, data[0], data[1]);
            if (out == null) return;
            for (int i = 0; i < fitted.length && i < out.length; i++) {
                fitted[i][0] = out[i][0]; fitted[i][1] = out[i][1]; fitted[i][2] = out[i][2];
            }
        } catch (Throwable t) {
            say("left the patch's own shape: " + t);
        }
    }

    private static float[][] load(String size) throws Exception {
        try (InputStream in = SolUnderCloth.class.getResourceAsStream("undercloth-" + size + ".bin")) {
            if (in == null) return null;
            DataInputStream d = new DataInputStream(new java.io.BufferedInputStream(in));
            int n = d.readInt();
            if (n <= 0 || n > 200000) return null;
            float[] pos = new float[n * 3], off = new float[n * 3];
            for (int i = 0; i < pos.length; i++) pos[i] = d.readFloat();
            for (int i = 0; i < off.length; i++) off[i] = d.readFloat();
            return new float[][] {pos, off};
        }
    }

    /**
     * pos/off: the body file's control points and their under-cloth offsets, in the file's units and axes.
     * canonical: the same body as the patch holds it (other units, maybe other axes, vertices split at seams).
     * The axes and the scale are found by matching the two bounding boxes (48 axis orders and signs tried, the one whose
     * points fall on each other wins); every canonical vertex then takes the offset of the control point it lies on.
     * Returns the new "fitted" offsets, or null when the body is not this file's body.
     */
    static double[][] compute(double[][] canonical, double[][] fitted, double[][] bare, float[] pos, float[] off) {
        int n = canonical.length, m = pos.length / 3;
        double[] cmin = {1e300, 1e300, 1e300}, cmax = {-1e300, -1e300, -1e300}, fmin = {1e300, 1e300, 1e300}, fmax = {-1e300, -1e300, -1e300};
        for (double[] p : canonical) for (int k = 0; k < 3; k++) { cmin[k] = Math.min(cmin[k], p[k]); cmax[k] = Math.max(cmax[k], p[k]); }
        for (int j = 0; j < m; j++) for (int k = 0; k < 3; k++) { fmin[k] = Math.min(fmin[k], pos[j * 3 + k]); fmax[k] = Math.max(fmax[k], pos[j * 3 + k]); }
        int[][] perms = {{0, 1, 2}, {0, 2, 1}, {1, 0, 2}, {1, 2, 0}, {2, 0, 1}, {2, 1, 0}};
        double height = Math.max(cmax[0] - cmin[0], Math.max(cmax[1] - cmin[1], cmax[2] - cmin[2]));
        int step = Math.max(1, m / 240);
        double best = 1e300; int[] bp = null; double[] bs = null, bt = null;
        for (int[] pm : perms) {
            for (int sg = 0; sg < 8; sg++) {
                double[] s = new double[3], t = new double[3];
                boolean ok = true;
                for (int k = 0; k < 3; k++) {
                    double fe = fmax[pm[k]] - fmin[pm[k]], ce = cmax[k] - cmin[k];
                    if (fe < 1e-12 || ce < 1e-12) { ok = false; break; }
                    double sign = ((sg >> k) & 1) == 0 ? 1 : -1;
                    s[k] = sign * ce / fe;
                    t[k] = sign > 0 ? cmin[k] - s[k] * fmin[pm[k]] : cmin[k] - s[k] * fmax[pm[k]];
                }
                if (!ok) continue;
                double a = Math.abs(s[0]), b = Math.abs(s[1]), c = Math.abs(s[2]);
                if (Math.max(a, Math.max(b, c)) / Math.min(a, Math.min(b, c)) > 1.03) continue;     // not the same shape
                double err = 0; int cnt = 0;
                for (int j = 0; j < m; j += step) {
                    double x = s[0] * pos[j * 3 + pm[0]] + t[0], y = s[1] * pos[j * 3 + pm[1]] + t[1], z = s[2] * pos[j * 3 + pm[2]] + t[2];
                    double d = 1e300;
                    for (double[] p : canonical) {
                        double dx = p[0] - x, dy = p[1] - y, dz = p[2] - z, q = dx * dx + dy * dy + dz * dz;
                        if (q < d) d = q;
                    }
                    err += Math.sqrt(d); cnt++;
                }
                err /= Math.max(1, cnt);
                if (err < best) { best = err; bp = pm; bs = s; bt = t; }
            }
        }
        if (bp == null || best > height * 2e-3) {
            say("body not recognised (fit " + best + " of height " + height + "); the patch's own shape stays");
            return null;
        }
        // control points in canonical space, and which of them move
        double[][] cp = new double[m][3]; double[][] co = new double[m][3]; boolean[] mv = new boolean[m];
        double[] rmin = {1e300, 1e300, 1e300}, rmax = {-1e300, -1e300, -1e300};
        for (int j = 0; j < m; j++) {
            double len = 0;
            for (int k = 0; k < 3; k++) {
                cp[j][k] = bs[k] * pos[j * 3 + bp[k]] + bt[k];
                co[j][k] = bs[k] * off[j * 3 + bp[k]];
                len += co[j][k] * co[j][k];
            }
            mv[j] = len > height * height * 1e-12;
            if (mv[j]) for (int k = 0; k < 3; k++) { rmin[k] = Math.min(rmin[k], cp[j][k]); rmax[k] = Math.max(rmax[k], cp[j][k]); }
        }
        double tol = height * 1.5e-3, tol2 = tol * tol, pad = height * 0.01;
        double[][] out = new double[n][3];
        int moved = 0, unmatched = 0;
        for (int i = 0; i < n; i++) {
            double[] p = canonical[i];
            out[i][0] = bare[i][0]; out[i][1] = bare[i][1]; out[i][2] = bare[i][2];      // under cloth = bare, except the chest
            if (p[0] < rmin[0] - pad || p[0] > rmax[0] + pad || p[1] < rmin[1] - pad || p[1] > rmax[1] + pad || p[2] < rmin[2] - pad || p[2] > rmax[2] + pad) continue;
            int bj = -1; double bd = 1e300;
            for (int j = 0; j < m; j++) {
                double dx = cp[j][0] - p[0], dy = cp[j][1] - p[1], dz = cp[j][2] - p[2], q = dx * dx + dy * dy + dz * dz;
                if (q < bd) { bd = q; bj = j; }
            }
            if (bj < 0 || bd > tol2) { unmatched++; continue; }
            if (mv[bj]) { out[i][0] = co[bj][0]; out[i][1] = co[bj][1]; out[i][2] = co[bj][2]; moved++; }
        }
        if (moved == 0) { say("no chest vertex matched; the patch's own shape stays"); return null; }
        say("under-cloth chest on " + moved + " vertices (fit " + String.format(Locale.ROOT, "%.2e", best / height) + " of height, "
            + unmatched + " near vertices without a match)");
        return out;
    }

    // ------------------------------------------------------------------ when the shape is used

    /** r: what the patch's own bra test said. item: a Clothing, a script Item or an ItemVisual. */
    static boolean holds(boolean r, Object item) {
        if (r) return true;
        try {
            if (item == null || !enabled()) return false;
            Object location; zombie.core.skinnedmodel.population.ClothingItem ci;
            if (item instanceof zombie.inventory.types.Clothing c) {
                if (c.isCosmetic()) return false;
                location = c.getBodyLocation(); ci = c.getClothingItem();
            } else if (item instanceof zombie.scripting.objects.Item s) {
                location = s.getBodyLocation(); ci = s.getClothingItemAsset();
            } else if (item instanceof zombie.core.skinnedmodel.visual.ItemVisual v) {
                zombie.scripting.objects.Item s = v.getScriptItem();
                location = s == null ? null : s.getBodyLocation(); ci = v.getClothingItem();
            } else return false;
            if (location == null || ci == null) return false;
            String model = ci.getModel(true);
            if (model != null && !model.isBlank()) return false;                  // it has a mesh of its own: not painted
            String loc = String.valueOf(location).toLowerCase(Locale.ROOT);
            int colon = loc.lastIndexOf(':');
            if (colon >= 0) loc = loc.substring(colon + 1);
            loc = loc.replace("_", "");
            if (loc.contains("underwear")) return false;
            for (String t : TOPS) if (loc.contains(t)) return true;
            return false;
        } catch (Throwable t) {
            return false;
        }
    }

    private static synchronized void say(String m) {
        System.out.println("[SolUnderCloth] " + m);
        said = true;
    }
}

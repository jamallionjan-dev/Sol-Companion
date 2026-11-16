package localplayerbody;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Random;

/**
 * Offline test of SolUnderCloth on the PATCHED jar (not shipped). The game is not running.
 *  1 the patched classes load and verify (BraGeometry, Physics, PreviewSupport)
 *  2 compute(): a body as the patch would hold it - the file's points in other units, axes swapped and mirrored,
 *    vertices doubled at seams and shuffled - gets exactly the file's under-cloth offsets, and bare offsets elsewhere
 *  3 a different body (another shape) is refused and nothing is written
 *  4 refit() with the switch unreadable (no game) leaves the arrays untouched
 * Writes the resulting under-cloth positions back in file space for the Python renderer.
 */
public final class UnderClothTest {
    static int fail = 0;
    static void ck(String n, boolean ok, String d) { System.out.println((ok ? "PASS " : "FAIL ") + n + (ok ? "" : " : " + d)); if (!ok) fail++; }

    public static void main(String[] a) throws Exception {
        for (String c : new String[] {"localplayerbody.BraGeometry", "localplayerbody.PreviewSupport", "localplayerbody.SolUnderCloth"}) {
            try { Class.forName(c, false, UnderClothTest.class.getClassLoader()).getDeclaredMethods(); ck("loads " + c, true, ""); }
            catch (Throwable t) { ck("loads " + c, false, t.toString()); }
        }
        float[] pos, off; int m;
        try (DataInputStream d = new DataInputStream(new java.io.BufferedInputStream(Files.newInputStream(Path.of(a[0]))))) {
            m = d.readInt(); pos = new float[m * 3]; off = new float[m * 3];
            for (int i = 0; i < pos.length; i++) pos[i] = d.readFloat();
            for (int i = 0; i < off.length; i++) off[i] = d.readFloat();
        }
        // the patch's view of the body: x' = -37.4 * z, y' = 37.4 * x, z' = -37.4 * y (+ shift), some vertices doubled, order shuffled
        Random rnd = new Random(7);
        int n = m + m / 3;
        int[] src = new int[n];
        for (int i = 0; i < n; i++) src[i] = i < m ? i : rnd.nextInt(m);
        for (int i = n - 1; i > 0; i--) { int j = rnd.nextInt(i + 1); int t = src[i]; src[i] = src[j]; src[j] = t; }
        double s = 37.4; double[] shift = {0.3, -1.1, 2.0};
        double[][] canon = new double[n][3], bare = new double[n][3], fitted = new double[n][3], expect = new double[n][3];
        int movedExpected = 0;
        for (int i = 0; i < n; i++) {
            int j = src[i];
            double x = pos[j * 3], y = pos[j * 3 + 1], z = pos[j * 3 + 2], ox = off[j * 3], oy = off[j * 3 + 1], oz = off[j * 3 + 2];
            canon[i] = new double[] {-s * z + shift[0], s * x + shift[1], -s * y + shift[2]};
            bare[i] = new double[] {rnd.nextInt(50) == 0 ? 0.001 : 0, 0, 0};
            fitted[i] = new double[] {9, 9, 9};
            boolean mv = ox * ox + oy * oy + oz * oz > 1e-14;
            expect[i] = mv ? new double[] {-s * oz, s * ox, -s * oy} : bare[i].clone();
            if (mv) movedExpected++;
        }
        double[][] out = SolUnderCloth.compute(canon, fitted, bare, pos, off);
        ck("compute returns a shape", out != null, "null");
        if (out != null) {
            double worst = 0; int wrong = 0;
            for (int i = 0; i < n; i++) {
                double e = 0; for (int k = 0; k < 3; k++) e = Math.max(e, Math.abs(out[i][k] - expect[i][k]));
                worst = Math.max(worst, e); if (e > 2e-5) wrong++;                 // 2e-5 canonical units is under a micrometre
            }
            ck("every vertex has the file's offset (or its bare offset), whatever the axes, units and order (" + movedExpected + " moved)", wrong == 0, wrong + " wrong, worst " + worst);
            boolean untouched = true; for (double[] f : fitted) if (f[0] != 9) untouched = false;
            ck("compute does not write the patch's arrays itself", untouched, "");
            // back to file space for the renderer: file = inverse of the transform above
            try (DataOutputStream o = new DataOutputStream(new java.io.BufferedOutputStream(Files.newOutputStream(Path.of(a[1]))))) {
                double[][] back = new double[m][3]; boolean[] seen = new boolean[m];
                for (int i = 0; i < n; i++) {
                    int j = src[i]; if (seen[j]) continue; seen[j] = true;
                    double cx = canon[i][0] + out[i][0] - shift[0], cy = canon[i][1] + out[i][1] - shift[1], cz = canon[i][2] + out[i][2] - shift[2];
                    back[j] = new double[] {cy / s, -cz / s, -cx / s};
                }
                o.writeInt(m);
                for (double[] p : back) for (double v : p) o.writeFloat((float) v);
            }
        }
        // another body: same points squashed along one axis -> must be refused
        double[][] other = new double[n][3];
        for (int i = 0; i < n; i++) other[i] = new double[] {canon[i][0], canon[i][1] * 1.3, canon[i][2]};
        ck("a different body is refused", SolUnderCloth.compute(other, fitted, bare, pos, off) == null, "accepted");
        // and one with the right box but other points
        double[][] noise = new double[n][3];
        for (int i = 0; i < n; i++) noise[i] = new double[] {canon[i][0] + (rnd.nextDouble() - 0.5) * 0.4, canon[i][1], canon[i][2]};
        ck("a body whose points do not coincide is refused", SolUnderCloth.compute(noise, fitted, bare, pos, off) == null, "accepted");
        double[][] f2 = new double[n][3]; for (double[] f : f2) f[0] = 5;
        SolUnderCloth.refit(canon, new int[0], "L", f2, bare, "undercloth-1");
        boolean same = true; for (double[] f : f2) if (f[0] != 5) same = false;
        ck("switch not readable (no game): the patch's own shape is left alone", same, "");
        ck("holds: the patch's own yes stays yes; nothing held without the switch", SolUnderCloth.holds(true, null) && !SolUnderCloth.holds(false, new Object()), "");
        System.out.println("SUMMARY pass/fail: fail=" + fail);
        if (fail > 0) System.exit(1);
    }
}

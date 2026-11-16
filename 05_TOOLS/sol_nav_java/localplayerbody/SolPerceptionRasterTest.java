package localplayerbody;

import java.util.ArrayList;
import java.util.List;

/** Offline check of the 10 cm drawing. Not shipped. */
public final class SolPerceptionRasterTest {
    static int fails;

    static void ck(String name, boolean ok) {
        System.out.println((ok ? "PASS " : "FAIL ") + name);
        if (!ok) fails++;
    }

    static int at(byte[] img, int n, double tx, double ty) {
        return img[(int) (ty * 10) * n + (int) (tx * 10)] & 255;
    }

    public static void main(String[] a) {
        int size = 5, n = size * 10;
        int[] s = new int[size * size];
        s[0] = SolPerception.SOLID;
        s[1] = SolPerception.POST;
        s[2] = SolPerception.EDGE_N;
        s[3] = SolPerception.EDGE_W;
        s[4] = -1;
        List<float[]> cars = new ArrayList<>();
        cars.add(new float[] { 101.0f, 203.0f, 103.5f, 203.0f, 103.5f, 204.5f, 101.0f, 204.5f });
        byte[] img = SolPerception.rasterize(s, size, cars, 100, 200);
        ck("solid fills its square", at(img, n, 0.05, 0.05) == 200 && at(img, n, 0.95, 0.95) == 200);
        ck("post only at the centre", at(img, n, 1.5, 0.5) == 140 && at(img, n, 1.05, 0.05) == 0);
        ck("north edge only along the top", at(img, n, 2.5, 0.05) == 90 && at(img, n, 2.5, 0.5) == 0);
        ck("west edge only along the left", at(img, n, 3.05, 0.5) == 90 && at(img, n, 3.5, 0.5) == 0);
        ck("not loaded is marked", at(img, n, 4.5, 0.5) == 255);
        ck("a car's box is exact", at(img, n, 1.1, 3.1) == 40 && at(img, n, 3.4, 4.4) == 40 && at(img, n, 0.9, 3.1) == 0 && at(img, n, 3.6, 3.1) == 0);
        ck("rotated box", SolPerception.inside(new float[] { 0, -2, 2, 0, 0, 2, -2, 0 }, 0.5, 0.5) && !SolPerception.inside(new float[] { 0, -2, 2, 0, 0, 2, -2, 0 }, 1.8, 1.8));
        System.out.println(fails == 0 ? "SUMMARY ALL PASS" : "SUMMARY FAILED " + fails);
        System.exit(fails == 0 ? 0 : 1);
    }
}

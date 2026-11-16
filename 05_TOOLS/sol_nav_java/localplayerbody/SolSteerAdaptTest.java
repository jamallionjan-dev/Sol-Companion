package localplayerbody;

/** Offline checks for SolSteerAdapt's decision rules. Run: java -cp <classes;game;zb> localplayerbody.SolSteerAdaptTest */
public final class SolSteerAdaptTest {
    static int pass, fail;
    static void check(String name, boolean ok) { if (ok) pass++; else fail++; System.out.println((ok ? "PASS " : "FAIL ") + name); }

    /** Feed samples of a vehicle whose yaw answers steering with sign `answer`, through the adapter's own mirror. */
    static boolean run(int answer, int reference, int samples, double kmh) {
        int ev = 0; boolean flip = false;
        for (int i = 0; i < samples; i++) {
            double want = (i % 2 == 0) ? 0.6 : -0.4;                 // what her tracker asks for
            double applied = flip ? -want : want;                     // what the game applies
            double yaw = answer * Math.signum(applied) * Math.signum(kmh) * 0.4;
            ev = SolSteerAdapt.learn(ev, yaw, applied, kmh);
            flip = SolSteerAdapt.decide(flip, ev, reference);
        }
        return flip;
    }

    public static void main(String[] a) {
        check("ordinary car is never mirrored", !run(1, 1, 50, 20));
        check("reversed vehicle is mirrored", run(-1, 1, 50, 20));
        check("reversed vehicle stays mirrored after the mirror (no flapping)", run(-1, 1, 500, 20));
        check("reversed vehicle backing up is still mirrored", run(-1, 1, 50, -8));
        check("needs 6 clear samples first", !run(-1, 1, 5, 20));
        check("too slow says nothing", !run(-1, 1, 50, 1));
        check("reference measured the other way: an answering-plus vehicle is mirrored", run(1, -1, 50, 20));
        check("small steering says nothing", SolSteerAdapt.learn(0, 0.5, 0.05, 20) == 0);
        check("no turn says nothing (track mod drops turns while steering eases)", SolSteerAdapt.learn(0, 0.0, 0.6, 20) == 0);
        check("evidence capped", SolSteerAdapt.learn(10, 0.5, 0.6, 20) == 10);
        check("wrap", Math.abs(SolSteerAdapt.wrap(3 * Math.PI) - Math.PI) < 1e-9 || Math.abs(SolSteerAdapt.wrap(3 * Math.PI) + Math.PI) < 1e-9);
        System.out.println("RESULT " + pass + "/" + (pass + fail));
        if (fail > 0) System.exit(1);
    }
}

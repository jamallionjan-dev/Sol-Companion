package localplayerbody;

/** Keeps a per-frame job from ever building up to a stutter: if the rolling cost rises above 0.4 ms, the slice is halved. */
public final class SolNavCost {
    private static final long LIMIT_NANOS = 400_000L, MIN_SLICE = 60_000L;
    private final String name;
    private long slice;
    private double average;

    public SolNavCost(String name, long sliceNanos) { this.name = name; this.slice = sliceNanos; }

    public long slice() { return slice; }

    public void note(long spentNanos) {
        average = average == 0 ? spentNanos : average * 0.9 + spentNanos * 0.1;
        if (average > LIMIT_NANOS && slice > MIN_SLICE) {
            slice = Math.max(MIN_SLICE, slice / 2);
            average = 0;
            System.out.println("[SolNav] " + name + " slice halved to " + slice / 1000 + " us");
        }
    }
}

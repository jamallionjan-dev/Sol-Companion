package localplayerbody;

import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

/** One planning job at a time on a daemon thread. The main thread only submits a snapshot and polls; it never waits. */
public final class SolNavWorker {
    private static final ExecutorService POOL = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "SolNav");
        t.setDaemon(true);
        t.setPriority(Thread.MIN_PRIORITY);
        return t;
    });
    private static Future<SolNavPlanner.Result> running;

    private SolNavWorker() {}

    /** Runs one tiny real plan through submit, so thread start and class and call-site linking happen at game start, not on a frame that matters. */
    public static void warmUp() {
        SolNavPlanner.Car car = new SolNavPlanner.Car(0.5, 0.3, 0.6, 0.3, 0.05);
        submit(120, 60, 0, 0, new boolean[120 * 60], car, 2, 3, 0, 10, 3, 0, 500_000_000L);
        long end = System.currentTimeMillis() + 2000;
        while (busy() && System.currentTimeMillis() < end) Thread.onSpinWait();
        poll();
    }

    /** Takes an occupancy snapshot the caller will not touch again. The distance map is built on the worker. False when a plan is already being made. */
    public static synchronized boolean submit(int w, int h, double ox, double oy, boolean[] occ, SolNavPlanner.Car car, double sx, double sy, double sth, double gx, double gy, double gth, long budgetNanos) {
        if (running != null && !running.isDone()) return false;
        running = POOL.submit(() -> {
            SolNavPlanner.Grid grid = new SolNavPlanner.Grid(w, h, ox, oy, occ);
            SolNavPlanner.Result r = SolNavPlanner.plan(grid, car, sx, sy, sth, gx, gy, gth, budgetNanos);
            if (r.path != null) r.path = SolNavPlanner.smooth(grid, car, r.path);
            return r;
        });
        return true;
    }

    /** Any planning job that builds its own map on the worker. False when one is already running. */
    public static synchronized boolean submitTask(java.util.concurrent.Callable<SolNavPlanner.Result> task) {
        if (running != null && !running.isDone()) return false;
        running = POOL.submit(task);
        return true;
    }

    /** The finished result once, or null while thinking or idle. Never blocks. */
    public static synchronized SolNavPlanner.Result poll() {
        if (running == null || !running.isDone()) return null;
        try {
            SolNavPlanner.Result r = running.get();
            running = null;
            return r;
        } catch (Exception e) {
            running = null;
            SolNavPlanner.Result r = new SolNavPlanner.Result();
            r.why = "worker_error:" + e;
            return r;
        }
    }

    public static synchronized boolean busy() { return running != null && !running.isDone(); }
}

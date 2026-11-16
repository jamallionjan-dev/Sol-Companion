package sol.bridge;

import zombie.MainThread;
import java.util.concurrent.atomic.AtomicBoolean;

public final class SolBootstrap {
    private static volatile boolean started;
    private static volatile boolean ready;
    private static volatile String status = "not started";
    private static volatile Thread worker;
    private static final AtomicBoolean exposureQueued = new AtomicBoolean();
    private static final long CHECK_INTERVAL_MILLIS = 500L;

    private SolBootstrap() {}

    public static synchronized void start() {
        if (started && worker != null && worker.isAlive()) {
            SolRuntimeSupervisor.bootstrapStarted();
            return;
        }
        SolRuntimeSupervisor.bootstrapStarted();
        started = true;
        status = "waiting for LuaManager";
        Thread thread = new Thread(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    if (MainThread.isRunning() && exposureQueued.compareAndSet(false, true)) {
                        try {
                            MainThread.queueInvokeOnMainThread(() -> {
                                try {
                                    boolean wasReady = ready;
                                    boolean exposed = SolExposure.exposeNow();
                                    ready = exposed;
                                    status = exposed
                                        ? SolExposure.getDiagnosticStatus()
                                        : "waiting for initialized LuaManager environment";
                                    if (exposed && !wasReady) {
                                        System.out.println("[SolNativeBridge] READY " + status);
                                    }
                                } catch (Throwable failure) {
                                    ready = false;
                                    status = "exposure failed: " + failure.getClass().getSimpleName();
                                    System.err.println("[SolNativeBridge] " + status);
                                } finally {
                                    SolRuntimeSupervisor.pollLifecycle();
                                    exposureQueued.set(false);
                                }
                            });
                        } catch (Throwable queueFailure) {
                            exposureQueued.set(false);
                            status = "main-thread queue failed: " + queueFailure.getClass().getSimpleName();
                        }
                    }
                    Thread.sleep(CHECK_INTERVAL_MILLIS);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                } catch (Throwable monitorFailure) {
                    status = "monitor failed: " + monitorFailure.getClass().getSimpleName();
                    System.err.println("[SolNativeBridge] " + status);
                    try {
                        Thread.sleep(CHECK_INTERVAL_MILLIS);
                    } catch (InterruptedException interrupted) {
                        Thread.currentThread().interrupt();
                    }
                }
            }
            ready = false;
            started = false;
            status = "bootstrap worker stopped";
            SolRuntimeSupervisor.noteError("bootstrap-worker", new IllegalStateException(status));
        }, "SolNativeBridge-bootstrap");
        thread.setDaemon(true);
        worker = thread;
        thread.start();
    }

    public static boolean isReady() { return ready; }
    public static String getStatus() { return status; }
}

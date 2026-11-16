package zombie;

public final class MainThread {
    public static Thread mainThread;
    private MainThread() {}
    public static void queueInvokeOnMainThread(Runnable task) {}
    public static boolean isRunning() { return true; }
}

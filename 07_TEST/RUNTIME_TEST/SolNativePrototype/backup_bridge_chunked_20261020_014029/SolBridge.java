package sol.bridge;

public final class SolBridge {
    public static final String PROTOCOL = "sol-native-prototype-1";
    private SolBridge() {}
    public static String ping() { return "SOL_NATIVE_PONG"; }
    public static String status() { return SolBootstrap.getStatus(); }
}

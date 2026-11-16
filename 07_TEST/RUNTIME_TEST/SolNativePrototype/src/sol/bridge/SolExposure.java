package sol.bridge;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.ref.WeakReference;
import java.util.Map;
import zombie.MainThread;

final class SolExposure {
    private static WeakReference<Object> lastEnvironment = new WeakReference<>(null);
    private static int lastEnvironmentId;
    private static Object cachedBridgeGlobal;
    private static long exposureCount;
    private static long restoreCount;
    private static boolean lastEnvironmentHadBridge;

    private SolExposure() {}

    static synchronized boolean exposeNow() throws ReflectiveOperationException {
        if (Thread.currentThread() != MainThread.mainThread) {
            throw new IllegalStateException("not main thread");
        }

        ClassLoader loader = SolExposure.class.getClassLoader();
        Class<?> manager = Class.forName("zombie.Lua.LuaManager", false, loader);
        Field envField = manager.getField("env");
        Field exposerField = manager.getField("exposer");
        Object environment = envField.get(null);
        Object exposer = exposerField.get(null);
        if (environment == null || exposer == null) {
            SolRuntimeSupervisor.observeEnvironment(environment, exposer, false,
                    exposureCount, "Lua environment or exposer unavailable");
            return false;
        }

        Class<?> tableClass = Class.forName("se.krka.kahlua.vm.KahluaTable", false, loader);
        Method rawget = tableClass.getMethod("rawget", Object.class);
        Object bridgeGlobal = rawget.invoke(environment, "SolBridge");
        int environmentId = System.identityHashCode(environment);
        boolean environmentChanged = lastEnvironment.get() != environment;
        int previousEnvironmentId = lastEnvironmentId;

        if (environmentChanged) {
            System.out.println("[SolNativeBridge] ENVIRONMENT oldId=" + previousEnvironmentId
                + " newId=" + environmentId + " bridgePresent=" + (bridgeGlobal != null));
            lastEnvironment = new WeakReference<>(environment);
            lastEnvironmentId = environmentId;
            lastEnvironmentHadBridge = bridgeGlobal != null;
        } else if (bridgeGlobal == null && lastEnvironmentHadBridge) {
            System.out.println("[SolNativeBridge] GLOBAL_MISSING envId=" + environmentId);
            lastEnvironmentHadBridge = false;
        }

        if (bridgeGlobal != null && validateBridgeGlobal(bridgeGlobal, tableClass, manager)) {
            cachedBridgeGlobal = bridgeGlobal;
            lastEnvironmentHadBridge = true;
            SolRuntimeSupervisor.observeEnvironment(environment, exposer, true,
                    exposureCount, "");
            return true;
        }

        if (!environmentChanged && cachedBridgeGlobal != null) {
            Method rawset = tableClass.getMethod("rawset", Object.class, Object.class);
            rawset.invoke(environment, "SolBridge", cachedBridgeGlobal);
            bridgeGlobal = rawget.invoke(environment, "SolBridge");
            if (bridgeGlobal != null && validateBridgeGlobal(bridgeGlobal, tableClass, manager)) {
                restoreCount++;
                lastEnvironmentHadBridge = true;
                System.out.println("[SolNativeBridge] RESTORED envId=" + environmentId
                    + " restoreCount=" + restoreCount + " bridgePresent=true");
                SolRuntimeSupervisor.observeEnvironment(environment, exposer, true,
                        exposureCount, "");
                return true;
            }
        }

        Field typeMapField = exposer.getClass().getField("typeMap");
        Object typeMapValue = typeMapField.get(exposer);
        boolean initialized = typeMapValue instanceof Map<?, ?> typeMap
            && typeMap.containsKey("function")
            && typeMap.containsKey("table")
            && rawget.invoke(environment, "IsoPlayer") != null;
        if (!initialized) {
            SolRuntimeSupervisor.observeEnvironment(environment, exposer, false,
                    exposureCount, "Lua exposer initialization sentinels unavailable");
            return false;
        }

        Method setExposed = exposer.getClass().getMethod("setExposed", Class.class);
        Method expose = exposer.getClass().getMethod("exposeLikeJava", Class.class, tableClass);
        setExposed.invoke(exposer, SolBridge.class);
        expose.invoke(exposer, SolBridge.class, environment);
        bridgeGlobal = rawget.invoke(environment, "SolBridge");
        if (bridgeGlobal == null || !validateBridgeGlobal(bridgeGlobal, tableClass, manager)) {
            lastEnvironmentHadBridge = false;
            SolRuntimeSupervisor.observeEnvironment(environment, exposer, false,
                    exposureCount, "exposed SolBridge failed protocol/API validation");
            return false;
        }

        cachedBridgeGlobal = bridgeGlobal;
        lastEnvironmentHadBridge = true;
        exposureCount++;
        System.out.println("[SolNativeBridge] EXPOSED envId=" + environmentId
            + " previousEnvId=" + previousEnvironmentId
            + " exposureCount=" + exposureCount
            + " restoreCount=" + restoreCount
            + " bridgePresent=true");
        SolRuntimeSupervisor.observeEnvironment(environment, exposer, true,
                exposureCount, "");
        return true;
    }

    private static boolean validateBridgeGlobal(Object bridgeGlobal, Class<?> tableClass,
            Class<?> managerClass) {
        try {
            Method rawget = tableClass.getMethod("rawget", Object.class);
            String[] required = {
                "ping", "status", "getProtocol", "getBackend", "getSupervisorStatus",
                "requestTestShellSpawn", "getTestShellActor", "requestTestShellRemove", "retryTestShellCleanup",
                "getTestShellState", "getTestShellFailure", "describeTestShell",
                "describeTestShellVisibility", "describeTestShellMovement",
                "requestTestShellMove", "stopTestShellMovement", "fillZombieSnapshot"
            };
            for (String name : required) {
                if (rawget.invoke(bridgeGlobal, name) == null) return false;
            }

            Object protocolFunction = rawget.invoke(bridgeGlobal, "getProtocol");
            Object backendFunction = rawget.invoke(bridgeGlobal, "getBackend");
            Object thread = managerClass.getField("thread").get(null);
            if (thread == null) return false;
            Method call = thread.getClass().getMethod("call", Object.class, Object[].class);
            Object protocol = call.invoke(thread, protocolFunction, new Object[0]);
            Object backend = call.invoke(thread, backendFunction, new Object[0]);
            return SolRuntimeSupervisor.PROTOCOL.equals(protocol)
                    && "NATIVE_SHELL".equals(backend);
        } catch (Throwable failure) {
            return false;
        }
    }

    static synchronized String getDiagnosticStatus() {
        return "envId=" + lastEnvironmentId
            + " exposures=" + exposureCount
            + " restores=" + restoreCount
            + " bridgePresent=" + lastEnvironmentHadBridge;
    }
}

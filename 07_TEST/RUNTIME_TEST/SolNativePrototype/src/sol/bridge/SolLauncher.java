package sol.bridge;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

public final class SolLauncher {
    private SolLauncher() {}
    public static void main(String[] args) throws Throwable {
        SolBootstrap.start();
        Class<?> mainScreen = Class.forName("zombie.gameStates.MainScreenState");
        Method main = mainScreen.getMethod("main", String[].class);
        try {
            main.invoke(null, (Object) args);
        } catch (InvocationTargetException e) {
            throw e.getCause();
        }
    }
}

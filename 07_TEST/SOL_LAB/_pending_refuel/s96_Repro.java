import se.krka.kahlua.integration.expose.*;
import se.krka.kahlua.converter.*;
import se.krka.kahlua.vm.*;
import se.krka.kahlua.j2se.*;
import java.lang.reflect.*;
import java.util.*;

public class Repro {
    public static class Box {
        public String over(String s) { return "s:" + s; }
        public String over(Box b) { return "b"; }
        public String one(String s) { return "one:" + s; }
        public static KahluaThread T; public static Object CB;
        public String each(Object fn) { for (int i=0;i<3;i++) T.call(CB, new Object[]{"x"}); return "each done"; }
    }
    static int poolDupes() throws Exception {
        Field f = MethodArguments.class.getDeclaredField("Pools");
        f.setAccessible(true);
        ArrayList<?>[] pools = (ArrayList<?>[]) f.get(null);
        int d = 0;
        for (ArrayList<?> p : pools) {
            if (p == null) continue;
            Set<Object> s = Collections.newSetFromMap(new IdentityHashMap<>());
            for (Object o : p) if (!s.add(o)) d++;
        }
        return d;
    }
    public static void main(String[] a) throws Exception {
        J2SEPlatform plat = new J2SEPlatform();
        KahluaTable env = plat.newTable();
        KahluaConverterManager cm = new KahluaConverterManager();
        KahluaThread t = new KahluaThread(plat, env); Field ot = KahluaThread.class.getDeclaredField("debugOwnerThread"); ot.setAccessible(true); ot.set(t, Thread.currentThread());
        LuaJavaClassExposer ex = new LuaJavaClassExposer(cm, plat, env);
        Box box = new Box();
        KahluaTable g = plat.newTable();
        for (Method m : Box.class.getMethods()) if (m.getDeclaringClass() == Box.class) ex.exposeGlobalObjectFunction(g, box, m);
        Object over = g.rawget("over"), one = g.rawget("one");
        System.out.println("over=" + over.getClass().getSimpleName() + " one=" + one.getClass().getSimpleName());
        Object[][] cases = {
            {"one('x')", one, new Object[]{"x"}},
            {"one(1.0)", one, new Object[]{1.0}},
            {"over('x')", over, new Object[]{"x"}},
            {"over(5.0)  [no overload matches]", over, new Object[]{5.0}},
            {"over(5.0)  again", over, new Object[]{5.0}},
            {"over(table)", over, new Object[]{plat.newTable()}},
        };
        Box.T = t; Box.CB = over;
        Object each = g.rawget("each");
        Object[] r0 = t.pcall(each, new Object[]{"fn"});
        System.out.println("BEFORE poisoning: each(fn) with nested over('x') callbacks -> ok=" + r0[0] + " " + (r0.length>1? String.valueOf(r0[1]).split("\n")[0]:""));
        for (Object[] c : cases) {
            int before = poolDupes();
            Object[] r = t.pcall(c[1], (Object[]) c[2]);
            System.out.println(c[0] + " -> ok=" + r[0] + " " + (r.length > 1 ? String.valueOf(r[1]).split("\n")[0] : "") + " | duplicate pooled MethodArguments " + before + " -> " + poolDupes());
        }
        for (int k = 0; k < 4; k++) {
            int before = poolDupes();
            Object[] r1 = t.pcall(each, new Object[]{"fn"});
            System.out.println("AFTER poisoning: each(fn) nested -> ok=" + r1[0] + " " + (r1.length>1? String.valueOf(r1[1]).split("\n")[0]:"") + " | duplicates " + before + " -> " + poolDupes());
        }
    }
}

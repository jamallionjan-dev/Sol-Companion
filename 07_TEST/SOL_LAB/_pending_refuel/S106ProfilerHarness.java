// s106 lua_profiler: runs SolLuaProfiler.lua on the game's OWN Kahlua and the game's OWN zombie.Lua.Event (projectzomboid.jar
// 42.22.2, read only). What is real here: KahluaThread, the compiler (Prototype.filename set through FuncState.currentfullFile
// exactly as LuaManager.RunLuaInternal does), LuaCaller.protectedCallVoid, LuaJavaClassExposer (ArrayList/Field methods called
// from Lua through the same invokers as in game), Event/Event$Add/Event$Remove, and Event.trigger's callback loop.
// What is copied: the GlobalObject reflection helpers (same bytecode semantics, minus the -debug check) and getTimestampMs.
// Prints "CHECK <name> PASS|FAIL [detail]" and "MEASURE <name> <value>" lines; test_s106_lua_profiler.py reads them.
// Build/run: javac -cp projectzomboid.jar S106ProfilerHarness.java ; java -cp projectzomboid.jar;. S106ProfilerHarness <profiler.lua>
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import se.krka.kahlua.converter.KahluaConverterManager;
import se.krka.kahlua.integration.LuaCaller;
import se.krka.kahlua.integration.annotations.LuaMethod;
import se.krka.kahlua.integration.expose.LuaJavaClassExposer;
import se.krka.kahlua.j2se.J2SEPlatform;
import se.krka.kahlua.luaj.compiler.LuaCompiler;
import se.krka.kahlua.vm.*;
import org.luaj.kahluafork.compiler.FuncState;
import zombie.Lua.Event;
import zombie.Lua.KahluaNumberConverter;

public class S106ProfilerHarness {
    static int fails = 0;
    static void check(String n, boolean ok, String d) { System.out.println("CHECK " + n + " " + (ok ? "PASS" : "FAIL " + d)); if (!ok) fails++; }
    static void measure(String n, String v) { System.out.println("MEASURE " + n + " " + v); }

    public static class Globals {
        @LuaMethod(name = "getNumClassFields", global = true)
        public static int getNumClassFields(Object o) { return o.getClass().getDeclaredFields().length; }
        @LuaMethod(name = "getClassField", global = true)
        public static Field getClassField(Object o, int i) { Field f = o.getClass().getDeclaredFields()[i]; try { f.setAccessible(true); } catch (RuntimeException e) { } return f; }
        @LuaMethod(name = "getClassFieldVal", global = true)
        public static Object getClassFieldVal(Object o, Field f) { try { return f.get(o); } catch (Exception e) { return "<private>"; } }
        @LuaMethod(name = "getFilenameOfClosure", global = true)
        public static String getFilenameOfClosure(LuaClosure c) { return c == null ? null : c.prototype.filename; }
        @LuaMethod(name = "getFirstLineOfClosure", global = true)
        public static int getFirstLineOfClosure(LuaClosure c) { return c.prototype.lines != null && c.prototype.lines.length > 0 ? c.prototype.lines[0] : 0; }
        @LuaMethod(name = "getTimestampMs", global = true)
        public static long getTimestampMs() { return System.currentTimeMillis(); }
        @LuaMethod(name = "harnessNanos", global = true)
        public static double harnessNanos() { return (double) System.nanoTime(); }
    }

    static J2SEPlatform pl; static KahluaTable env; static KahluaThread th; static LuaCaller caller; static KahluaTable events;
    static Map<String, Event> evs = new LinkedHashMap<>();
    static boolean realTrigger = true;

    static Object run(String path, String src) throws Exception {
        FuncState.currentFile = path.substring(path.lastIndexOf('/') + 1);
        FuncState.currentfullFile = path;
        LuaClosure f = LuaCompiler.loadstring(src, path, env);
        Object[] r = th.pcall(f, new Object[0]);
        if (r.length > 0 && Boolean.FALSE.equals(r[0])) throw new RuntimeException("lua failed " + path + ": " + Arrays.toString(r));
        return r.length > 1 ? r[1] : null;
    }
    static Object lua(String src) throws Exception { return run("C:/harness/media/lua/client/harness.lua", src); }
    static boolean luaTrue(String expr) throws Exception { return Boolean.TRUE.equals(lua("return " + expr)); }
    static double luaNum(String expr) throws Exception { Object o = lua("return " + expr); return o instanceof Double ? (Double) o : Double.NaN; }

    static void trigger(String name, Object... args) {
        Event e = evs.get(name);
        if (realTrigger) {
            try { e.trigger(env, caller, args); return; }
            catch (Throwable t) { realTrigger = false; System.out.println("NOTE Event.trigger needs game statics (" + t + "); using the same loop as its non-debug branch"); }
        }
        for (int i = 0; i < e.callbacks.size(); i++) {             // Event.trigger, non-debug branch, without GameProfiler
            LuaClosure c = e.callbacks.get(i);
            try { caller.protectedCallVoid(th, c, args); } catch (Exception x) { System.out.println("callback error " + x); }
            if (!e.callbacks.contains(c)) i--;
        }
    }
    static void frame(int zombies) {
        trigger("OnTick", 1.0);
        trigger("OnPlayerUpdate", "player");
        for (int z = 0; z < zombies; z++) trigger("OnZombieUpdate", "zombie");
        trigger("OnRenderTick");
    }

    public static void main(String[] a) throws Exception {
        String profiler = new String(Files.readAllBytes(Paths.get(a[0])), StandardCharsets.UTF_8);
        pl = new J2SEPlatform(); env = pl.newEnvironment(); th = new KahluaThread(System.out, pl, env); th.debugOwnerThread = Thread.currentThread();
        KahluaConverterManager cm = new KahluaConverterManager(); KahluaNumberConverter.install(cm);
        caller = new LuaCaller(cm);
        zombie.Lua.LuaManager.thread = th; zombie.Lua.LuaManager.env = env;   // Event.trigger calls through LuaManager.thread
        LuaJavaClassExposer ex = new LuaJavaClassExposer(cm, pl, env) { @Override public boolean shouldExpose(Class<?> c) { return c == ArrayList.class || c == Field.class; } };   // LuaManager$Exposer overrides shouldExpose with its setExposed set
        ex.exposeLikeJavaRecursively(ArrayList.class, env); ex.exposeLikeJavaRecursively(Field.class, env);   // as LuaManager$Exposer does for its exposed classes
        ex.exposeGlobalFunctions(new Globals());
        events = pl.newTable(); env.rawset("Events", events);
        String[] names = { "OnTick", "OnPlayerUpdate", "OnRenderTick", "OnZombieUpdate" };
        for (int i = 0; i < names.length; i++) { Event e = new Event(names[i], i); e.register(pl, events); evs.put(names[i], e); }

        // switch + busy work + counters, then three "mods" registering BEFORE the profiler loads (worst case for load order)
        lua("SW = { lua_profiler = false }\nSolAuthority = { on = function(n) return SW[n] == true end }\n"
          + "CALLS = {}\nfunction busy(us) local t = harnessNanos() + us * 1000; local x = 0; while harnessNanos() < t do x = x + 1 end; return x end\n"
          + "function count(k) CALLS[k] = (CALLS[k] or 0) + 1 end\n");
        if (System.getenv("S106_PROBE") != null) lua(new String(Files.readAllBytes(Paths.get(System.getenv("S106_PROBE"))), StandardCharsets.UTF_8));
        String modA = "C:/Program Files (x86)/Steam/steamapps/workshop/content/108600/111/mods/HeavyMod/42/media/lua/client/Heavy/Tick.lua";
        String modB = "C:/Users/x/Zomboid/mods/LightMod/42/media/lua/client/light.lua";
        String modC = "C:/Program Files (x86)/Steam/steamapps/workshop/content/108600/222/mods/ZedMod/common/media/lua/shared/zed.lua";
        String vanilla = "C:/Program Files (x86)/Steam/steamapps/common/ProjectZomboid/media/lua/client/ISUI/ISFoo.lua";
        run(modA, "HeavyTick = function(n) count('A'); busy(400) end\nEvents.OnTick.Add(HeavyTick)\n"
                + "HeavyRender = function() count('AR'); busy(150) end\nEvents.OnRenderTick.Add(HeavyRender)\n");
        run(modB, "LightTick = function(n) count('B'); busy(20) end\nEvents.OnTick.Add(LightTick)\n"
                + "LightPlayer = function(p) count('BP'); busy(30) end\nEvents.OnPlayerUpdate.Add(LightPlayer)\n"
                + "RemoveMeLater = function(n) count('R') end\nEvents.OnTick.Add(RemoveMeLater)\n"
                + "SelfRemove = function(n) count('S'); Events.OnTick.Remove(SelfRemove) end\n");
        run(modC, "ZedUpd = function(z) count('Z'); busy(10) end\nEvents.OnZombieUpdate.Add(ZedUpd)\n");
        run(vanilla, "VanTick = function(n) count('V') end\nEvents.OnTick.Add(VanTick)\n");
        LuaClosure[] before = evs.get("OnTick").callbacks.toArray(new LuaClosure[0]);
        Object addJava = events.rawget("OnTick") instanceof KahluaTable ? ((KahluaTable) events.rawget("OnTick")).rawget("Add") : null;

        check("Event$Add is the Java object before", addJava != null && addJava.getClass().getName().equals("zombie.Lua.Event$Add"), String.valueOf(addJava));
        check("getFilenameOfClosure gives the full path", modA.equals(Globals.getFilenameOfClosure(before[0])), Globals.getFilenameOfClosure(before[0]));

        run("C:/Users/x/Zomboid/mods/Sol_LAB/42/media/lua/client/SolLuaProfiler.lua", profiler);
        check("keyOf workshop", luaTrue("SolLuaProfiler.keyOf('" + modA + "') == 'HeavyMod/client/Heavy/Tick.lua'"), String.valueOf(lua("return SolLuaProfiler.keyOf('" + modA + "')")));
        check("keyOf common dir", luaTrue("SolLuaProfiler.keyOf('" + modC + "') == 'ZedMod/shared/zed.lua'"), "");
        check("keyOf vanilla", luaTrue("SolLuaProfiler.keyOf('" + vanilla + "') == 'vanilla/client/ISUI/ISFoo.lua'"), "");
        check("keyOf backslashes, lowercase", luaTrue("SolLuaProfiler.keyOf('c:\\\\x\\\\mods\\\\efz\\\\42\\\\media\\\\lua\\\\client\\\\a.lua') == 'efz/client/a.lua'"), String.valueOf(lua("return SolLuaProfiler.keyOf('c:\\\\x\\\\mods\\\\efz\\\\42\\\\media\\\\lua\\\\client\\\\a.lua')")));
        lua("SolLuaProfiler.WINDOW_MS = 3000; SolLuaProfiler.CHECK_MS = 0");

        // ---- switch off: nothing changes
        for (int i = 0; i < 120; i++) frame(5);
        LuaClosure[] offList = evs.get("OnTick").callbacks.toArray(new LuaClosure[0]);
        boolean same = offList.length == before.length + 1;   // + the profiler's own tick
        for (int i = 0; same && i < before.length; i++) same = offList[i] == before[i];
        check("switch off: callbacks untouched", same, Arrays.toString(offList));
        check("switch off: Add is still Java", ((KahluaTable) events.rawget("OnTick")).rawget("Add") == addJava, "");
        check("switch off: not active", luaTrue("SolLuaProfiler.active == false"), "");

        // ---- overhead baseline (switch off), wall time per frame by System.nanoTime
        int FR = 3000, Z = 40;
        lua("busy = function(us) end");   // handlers become near-empty: what is left is call overhead
        for (int i = 0; i < FR; i++) frame(Z);   // warm the interpreter
        long t0 = System.nanoTime(); for (int i = 0; i < FR; i++) frame(Z); long offNs = System.nanoTime() - t0;
        long t0b = System.nanoTime(); for (int i = 0; i < FR; i++) frame(0); long off0Ns = System.nanoTime() - t0b;

        // ---- switch on
        lua("SW.lua_profiler = true");
        for (int i = 0; i < 31; i++) frame(0);   // the profiler checks the switch every 30 frames
        check("switch on: active", luaTrue("SolLuaProfiler.active == true"), "");
        int wrapped = 0, own = 0; LuaClosure[] onList = evs.get("OnTick").callbacks.toArray(new LuaClosure[0]);
        for (LuaClosure c : onList) { if (c.prototype.filename.endsWith("SolLuaProfiler.lua")) wrapped++; }
        check("switch on: pre-registered OnTick handlers wrapped in place", wrapped == onList.length && onList.length == offList.length, wrapped + "/" + onList.length);
        check("switch on: Add/Remove are Lua now", ((KahluaTable) events.rawget("OnTick")).rawget("Add") instanceof LuaClosure, "");
        check("switch on: OnZombieUpdate wrapped", evs.get("OnZombieUpdate").callbacks.get(0).prototype.filename.endsWith("SolLuaProfiler.lua"), "");

        for (int i = 0; i < FR; i++) frame(Z);
        long t1 = System.nanoTime(); for (int i = 0; i < FR; i++) frame(Z); long onNs = System.nanoTime() - t1;
        long t1b = System.nanoTime(); for (int i = 0; i < FR; i++) frame(0); long on0Ns = System.nanoTime() - t1b;
        measure("overhead_us_per_timed_call", String.format("%.3f", (on0Ns - off0Ns) / 1e3 / FR / 6));
        measure("overhead_us_per_strided_zombie_call", String.format("%.3f", ((onNs - on0Ns) - (offNs - off0Ns)) / 1e3 / FR / Z));
        double handlerCallsPerFrame = 6 + Z;   // OnTick 4 (A,B,R,V) + OnPlayerUpdate 1 + OnRenderTick 1 + OnZombieUpdate Z (stride 4)
        measure("frame_us_off", String.format("%.2f", offNs / 1e3 / FR));
        measure("frame_us_on", String.format("%.2f", onNs / 1e3 / FR));
        measure("overhead_us_per_handler_call", String.format("%.3f", (onNs - offNs) / 1e3 / FR / handlerCallsPerFrame));
        measure("calibration_timed_us", String.format("%.3f", luaNum("SolLuaProfiler.cost.timedUs")));
        measure("calibration_untimed_us", String.format("%.3f", luaNum("SolLuaProfiler.cost.untimedUs")));
        measure("clock_step_ms", String.format("%.1f", luaNum("SolLuaProfiler.cost.stepMs")));

        // ---- behaviour with the profiler on
        lua("busy = function(us) local t = harnessNanos() + us * 1000; local x = 0; while harnessNanos() < t do x = x + 1 end; return x end; CALLS = {}");
        lua("Events.OnTick.Add(SelfRemove)");
        frame(0); frame(0);
        check("self-removing handler runs once and is gone", luaTrue("CALLS.S == 1"), String.valueOf(lua("return CALLS.S")));
        check("self-remove keeps the others running (A twice)", luaTrue("CALLS.A == 2 and CALLS.B == 2 and CALLS.V == 2"), "");
        lua("Events.OnTick.Remove(RemoveMeLater)");
        int sizeAfterRemove = evs.get("OnTick").callbacks.size();
        frame(0);
        check("Remove(original) while on removes its wrapper", sizeAfterRemove == offList.length - 1 && luaTrue("CALLS.R == 2"), sizeAfterRemove + " " + lua("return CALLS.R"));
        lua("LateTick = function() count('L'); busy(100) end; Events.OnTick.Add(LateTick)");
        check("handler added while on is wrapped", evs.get("OnTick").callbacks.get(evs.get("OnTick").callbacks.size() - 1).prototype.filename.endsWith("SolLuaProfiler.lua"), "");
        // raw add through the Java Add (a path that skips our Lua Add): the next sweep wraps it
        Event$AddCall.call(addJava, th, "VanTick2");

        // ---- a window: true cost by Java vs reported
        lua("CALLS = {}; SolLuaProfiler.resetWindow()");
        long w0 = System.nanoTime(); int frames = 0;
        while (System.nanoTime() - w0 < 3_400_000_000L) { frame(10); frames++; }
        double secs = (System.nanoTime() - w0) / 1e9;
        double aCalls = luaNum("CALLS.A");
        measure("window_frames", String.valueOf(frames));
        measure("heavy_true_ms_per_s", String.format("%.1f", aCalls * 0.400 / secs));
        System.out.flush();
        Object v2 = env.rawget("VanTick2");
        check("raw Java Add (bypassing our Add) is wrapped by the next sweep", !evs.get("OnTick").callbacks.contains(v2) && luaTrue("CALLS.V2 ~= nil and CALLS.V2 > 0"), String.valueOf(evs.get("OnTick").callbacks.contains(v2)));

        // ---- switch off: everything back
        lua("SW.lua_profiler = false");
        for (int i = 0; i < 31; i++) frame(0);
        check("switch off again: not active", luaTrue("SolLuaProfiler.active == false"), "");
        check("switch off again: Add/Remove are the Java functions again", ((KahluaTable) events.rawget("OnTick")).rawget("Add") == addJava, "");
        int stillWrapped = 0;
        for (String n : names) for (LuaClosure c : evs.get(n).callbacks) if (c.prototype.filename.endsWith("SolLuaProfiler.lua") && !isOwnTick(c)) stillWrapped++;
        check("switch off again: every original closure back in its slot", stillWrapped == 0, stillWrapped + " still wrapped");
        check("switch off again: original identity (HeavyTick first)", evs.get("OnTick").callbacks.get(0) == before[0], "");
        lua("busy = function(us) end");
        for (int i = 0; i < FR; i++) frame(Z);
        long t2 = System.nanoTime(); for (int i = 0; i < FR; i++) frame(Z); long off2Ns = System.nanoTime() - t2;
        measure("frame_us_off_after", String.format("%.2f", off2Ns / 1e3 / FR));
        measure("overhead_us_per_handler_call_vs_after", String.format("%.3f", (onNs - off2Ns) / 1e3 / FR / (6 + Z)));
        check("switch off again: Remove works on originals", luaTrue("(function() Events.OnTick.Remove(LateTick); return true end)()") && !containsFile(evs.get("OnTick"), "LateTick"), "");
        System.out.println("SUMMARY harness fails=" + fails);
        System.exit(fails == 0 ? 0 : 1);
    }
    static boolean isOwnTick(LuaClosure c) { Object m = env.rawget("SolLuaProfiler"); return m instanceof KahluaTable && ((KahluaTable) m).rawget("tick") == c; }
    static boolean containsFile(Event e, String fnGlobal) { Object f = env.rawget(fnGlobal); return e.callbacks.contains(f); }

    // calls the Java Event$Add directly with a global function (what a mod that cached Events.OnTick.Add before us would do)
    static class Event$AddCall {
        static void call(Object add, KahluaThread t, String global) throws Exception {
            lua(global + " = function() count('V2') end");
            Object fn = env.rawget(global);
            caller.protectedCallVoid(t, add, new Object[] { fn });
        }
    }
}

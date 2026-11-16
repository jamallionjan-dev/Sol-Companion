"""s96 kahlua_overload_guard: SolKahluaGuard.lua under the game's Lua rules (kahlua_env) with Java-like userdata (Python objects),
the tonumber gate, and the installer (idempotent, on a temporary copy). Nothing live is touched.
The pool fault itself is reproduced on the real jar by s96_Repro.java; this checks the Lua side only.
Run: set PYTHONIOENCODING=utf-8 & python test_s96_kahlua_overload_guard.py [client dir]"""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
SRC = open(os.path.join(HERE, "SolKahluaGuard.lua"), encoding="ascii").read()
ERR = "java.lang.RuntimeException: No implementation found for function: over(class java.lang.Double 5.0)) in over"

class Box:            # a Java object: overloaded 'over' fails for a number the way MultiLuaJavaInvoker does
    calls = 0
    def over(self, *a):
        Box.calls += 1
        if a and isinstance(a[0], (int, float)): raise RuntimeError(ERR)
        return "ok"
    def plain(self, *a):
        Box.calls += 1
        raise RuntimeError("some other error")

def fresh(switch=True):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute("""
        LOG = {}
        print = function(s) LOG[#LOG + 1] = tostring(s) end
        SW = %s
        SolAuthority = { on = function(f) return f == "kahlua_overload_guard" and SW end }
        Events = { OnGameStart = { Add = function(f) START = f end } }
        local MT = {}
        local rawgm = getmetatable
        getmetatable = function(v) if type(v) == "userdata" then return MT end return rawgm(v) end
        SurvivorCompanion = { Call = {
            value = function(o, name, ...) local f = o[name]; local ok, a = pcall(f, o, ...); if not ok then return nil, false, tostring(a) end; return a, true end,
            method = function(o, name, ...) return pcall(o[name], o, ...) end,
            static = function(o, name, ...) return pcall(o[name], ...) end } }
    """ % ("true" if switch else "false"))
    L.execute(SRC)
    L.execute("START()")
    return L

L = fresh(True)
box = Box()
L.globals().box = box
ck("install: global pcall is the guard's pass-through", L.eval("pcall == SolKahluaGuard.pcall"))
ck("install: SC.Call guarded", L.eval("SurvivorCompanion.Call._solKahluaGuard == true"))
ck("pass-through: every return value kept, nils included", L.eval("select('#', pcall(function() return 1, nil, 3 end)) == 4"))
ck("pass-through: a normal error unchanged and not noted",
   L.eval("(function() local ok, e = pcall(error, 'boom'); return ok == false and tostring(e):find('boom') ~= nil end)()") and L.eval("SolKahluaGuard.stats.seen") == 0)
L.execute("ok1, e1 = pcall(box.over, box, 5)")
ck("detect: a no-overload failure through pcall is noted", L.eval("SolKahluaGuard.stats.seen") == 1 and L.eval("ok1") is False)
logs = list(L.eval("LOG").values())
ck("detect: logged with the signature", any("No implementation found" in s for s in logs), logs)
before = Box.calls
r = L.eval("{SurvivorCompanion.Call.value(box, 'over', 5)}")
ck("SC.Call.value: first bad call reaches Java and fails (nil,false,msg)", Box.calls == before + 1 and r[2] is False, r)
r = L.eval("{SurvivorCompanion.Call.value(box, 'over', 7)}")
ck("SC.Call.value: the same signature again does NOT reach Java", Box.calls == before + 1 and r[2] is False and "No implementation" in str(r[3]), (Box.calls - before, dict(r)))
r = L.eval("{SurvivorCompanion.Call.value(box, 'over', 'x')}")
ck("SC.Call.value: another signature (string) still reaches Java and works", Box.calls == before + 2 and r[1] == "ok", dict(r))
r = L.eval("{SurvivorCompanion.Call.method(box, 'over', 9)}")
ck("SC.Call.method: blocked signature answers false, msg", r[1] is False and Box.calls == before + 2, dict(r))
L.execute("SurvivorCompanion.Call.value(box, 'plain', 1)"); L.execute("SurvivorCompanion.Call.value(box, 'plain', 1)")
ck("other errors are never blocked", Box.calls == before + 4 and L.eval("SolKahluaGuard.stats.blocked") == 2, (Box.calls - before, L.eval("SolKahluaGuard.stats.blocked")))
r = L.eval("{SolKahluaGuard.call(box, 'over', 3)}")
ck("SolKahluaGuard.call: blocked like SC.Call (no Java call, the old message)", r[1] is False and "No implementation" in str(r[2]) and Box.calls == before + 4, dict(r))
r = L.eval("{SolKahluaGuard.call(box, 'over', 'y')}")
ck("SolKahluaGuard.call: good call returns true, value", r[1] is True and r[2] == "ok", dict(r))
L.execute("SW = false")
n0 = Box.calls
L.execute("SurvivorCompanion.Call.value(box, 'over', 5)")
ck("switch off: the call goes to Java again (pass-through)", Box.calls == n0 + 1)
seen = L.eval("SolKahluaGuard.stats.seen")
L.execute("pcall(box.over, box, 5)")
ck("switch off: pcall notes nothing", L.eval("SolKahluaGuard.stats.seen") == seen)
L.execute("SolKahluaGuard.install(); SolKahluaGuard.install()")
ck("install twice: no double wrap", L.eval("pcall == SolKahluaGuard.pcall and SolKahluaGuard.rawPcall ~= SolKahluaGuard.pcall"))

gate = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py")
if os.path.exists(gate):
    p = subprocess.run([sys.executable, gate, os.path.join(HERE, "SolKahluaGuard.lua")], capture_output=True, text=True)
    ck("tonumber gate", p.returncode == 0, p.stdout + p.stderr)

tmp = tempfile.mkdtemp()
try:
    cl = os.path.join(tmp, "p", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(cl)
    for f in ("SolSort.lua", "SolInventory.lua", "SolAuthority.lua"): shutil.copy(os.path.join(CL, f), cl)
    fx = os.path.normpath(os.path.join(cl, "..", "..", "..", "..", "..", "..", "Lua")); os.makedirs(fx, exist_ok=True)
    open(os.path.join(fx, "SolFixes_LAB.txt"), "w", newline="").write("x=on\r\n")
    ap = os.path.join(HERE, "apply_s96_kahlua_overload_guard.py")
    a1 = subprocess.run([sys.executable, ap, cl], capture_output=True, text=True)
    snap = {f: open(os.path.join(cl, f), encoding="utf-8", newline="").read() for f in os.listdir(cl)}
    a2 = subprocess.run([sys.executable, ap, cl], capture_output=True, text=True)
    snap2 = {f: open(os.path.join(cl, f), encoding="utf-8", newline="").read() for f in os.listdir(cl)}
    ck("installer runs", a1.returncode == 0, a1.stderr)
    ck("installer idempotent", a2.returncode == 0 and snap == snap2, a2.stderr)
    ck("installer: guard copied", "SolKahluaGuard.lua" in snap)
    ck("installer: SolSort + SolInventory route through the guard",
       snap.get("SolSort.lua", "").count("KG_.check(o, name, ...)") == 1 and snap.get("SolInventory.lua", "").count("KG_.check(o, name, ...)") == 1)
    ck("installer: switch in A.FIXES", '"kahlua_overload_guard",' in snap.get("SolAuthority.lua", ""))
    ck("installer: switch in SolFixes_LAB.txt once", open(os.path.join(fx, "SolFixes_LAB.txt")).read().count("kahlua_overload_guard=on") == 1)
    R = lua51.LuaRuntime()
    ls = R.eval("loadstring")
    for f in ("SolSort.lua", "SolInventory.lua", "SolAuthority.lua", "SolKahluaGuard.lua"):
        res = ls(snap[f])
        ok = (res[0] if isinstance(res, tuple) else res) is not None
        ck("syntax (lua 5.1 loadstring): " + f, ok, res)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("%d passed, %d failed" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)

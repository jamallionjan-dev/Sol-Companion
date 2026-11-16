"""s106 lua_profiler offline.
Part 1 (kahlua_env / lupa): compiles, ASCII, switch off = Events untouched, no -debug = nothing changes and no retry loop,
  the report format, the key of a file path, installer twice = no change (and lua_profiler=off written once, CRLF kept).
Part 2 (the game's OWN Kahlua and zombie.Lua.Event from projectzomboid.jar, read only): S106ProfilerHarness.java runs
  SolLuaProfiler.lua with handlers registered BEFORE it loads, real Event.trigger, real ArrayList calls from Lua; checks
  wrap in place / self-remove / Remove(original) / late Add / raw Java Add / full restore, the accuracy of the reported ms/s
  against System.nanoTime truth, and measures the profiler's own cost per handler call.
Part 3: tonumber and jarcall gates on a patched copy of the client.
Run: python test_s106_lua_profiler.py [client dir]"""
import os, sys, shutil, subprocess, tempfile, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from kahlua_env import lua51
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
GAME_D = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid"
GAME = GAME_D + r"\projectzomboid.jar"
JDK = r"C:\Program Files\Eclipse Adoptium\jdk-25.0.4.101-hotspot\bin"
FAIL, P = [], []
def ck(n, c, d=""): print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else "")); (P if c else FAIL).append(n)

# ---- installer on a copy laid out like the lab (client + Lua\SolFixes_LAB.txt)
tmp = tempfile.mkdtemp(prefix="s106lp_")
cl = os.path.join(tmp, "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(cl)
os.makedirs(os.path.join(tmp, "Zomboid", "Lua"))
fixf = os.path.join(tmp, "Zomboid", "Lua", "SolFixes_LAB.txt")
open(fixf, "w", newline="").write("edge_api=on\r\nkit_bare=on\r\n")
for f in os.listdir(CL):
    if f.endswith(".lua"): shutil.copy(os.path.join(CL, f), cl)
r1 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s106_lua_profiler.py"), cl], capture_output=True, text=True)
r2 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s106_lua_profiler.py"), cl], capture_output=True, text=True)
ck("installer runs", r1.returncode == 0 and "applied" in r1.stdout, r1.stdout + r1.stderr)
ck("installer second run changes nothing", r2.returncode == 0 and "edited" not in r2.stdout and "copied" not in r2.stdout and "added" not in r2.stdout, r2.stdout + r2.stderr)
body = open(fixf, newline="").read()
ck("SolFixes_LAB.txt gets lua_profiler=off once, CRLF", body.count("lua_profiler=off\r\n") == 1 and "\n" not in body.replace("\r\n", ""), repr(body))
ck("SolAuthority lists lua_profiler", '"lua_profiler"' in open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read())
src = open(os.path.join(cl, "SolLuaProfiler.lua"), encoding="utf-8").read()
ck("ascii SolLuaProfiler.lua", all(ord(c) < 128 for c in src))
ck("no Field method call (Field may be unexposed)", ":getName(" not in src)

# ---- part 1: lupa
L = lua51.LuaRuntime()
ok, err = L.eval("function(s) local f, e = loadstring(s); return f ~= nil, e end")(src)
ck("compiles", ok, err)
L.execute('''
SW = {}
SolAuthority = { on = function(n) return SW[n] == true end }
NOW = 0; getTimestampMs = function() NOW = NOW + 1; return NOW end
LOG = {}; print = function(s) LOG[#LOG + 1] = tostring(s) end
ADDS = {}
local function ev(name) local t = {}; t.Add = function(f) ADDS[#ADDS + 1] = name end; t.Remove = function(f) end; return t end
Events = { OnTick = ev("OnTick"), OnPlayerUpdate = ev("OnPlayerUpdate"), OnRenderTick = ev("OnRenderTick"), OnZombieUpdate = ev("OnZombieUpdate") }
ORIG = {}; for k, t in pairs(Events) do ORIG[k] = { t.Add, t.Remove } end
REFLECT = 0
getNumClassFields = function(o) REFLECT = REFLECT + 1; error("Not in debug") end
getClassField = function() error("Not in debug") end
getClassFieldVal = function() error("Not in debug") end
''')
L.execute(src)
ev = L.eval
ck("loads and registers its own tick once", ev('type(SolLuaProfiler) == "table" and #ADDS == 1 and ADDS[1] == "OnTick"'))
ck("switch off: 600 ticks touch nothing", ev('''(function() for i = 1, 600 do SolLuaProfiler.tick() end
    for k, t in pairs(Events) do if t.Add ~= ORIG[k][1] or t.Remove ~= ORIG[k][2] then return false end end
    return SolLuaProfiler.active == false and REFLECT == 0 end)()'''))
ck("no SolAuthority = off", ev('(function() local a = SolAuthority; SolAuthority = nil; local r = SolLuaProfiler.on(); SolAuthority = a; return r == false end)()'))
ck("switch on without -debug: NOT STARTED, Events untouched, no calibration", ev('''(function() SolLuaProfiler.CHECK_MS = 0; SW.lua_profiler = true; LOG = {}
    for i = 1, 30 do SolLuaProfiler.tick() end
    for k, t in pairs(Events) do if t.Add ~= ORIG[k][1] or t.Remove ~= ORIG[k][2] then return false end end
    local ns, cal = 0, 0; for _, l in ipairs(LOG) do if string.find(l, "NOT STARTED", 1, true) then ns = ns + 1 end; if string.find(l, "calibration", 1, true) then cal = cal + 1 end end
    return SolLuaProfiler.active == false and ns == 1 and cal == 0 end)()'''))
ck("without -debug: not retried every second", ev('''(function() local r0 = REFLECT
    for i = 1, 3000 do SolLuaProfiler.tick() end
    return REFLECT == r0 end)()'''))
ck("off then on again: tries once more", ev('''(function() local r0 = REFLECT
    SW.lua_profiler = false; for i = 1, 60 do SolLuaProfiler.tick() end
    SW.lua_profiler = true; for i = 1, 60 do SolLuaProfiler.tick() end
    SW.lua_profiler = false; return REFLECT > r0 end)()'''))
ck("keyOf: workshop / local / common / vanilla / no media path", ev('''(function() local k = SolLuaProfiler.keyOf
    return k("C:/S/steamapps/workshop/content/108600/3365052400/mods/EscapeFromZomboidFirearms/42/media/lua/client/TW/Core.lua") == "EscapeFromZomboidFirearms/client/TW/Core.lua"
       and k("C:/Users/JAMAL/Desktop/Sol/07_TEST/SOL_LAB/profile/Zomboid/mods/Sol_LAB/42/media/lua/client/SCDecision.lua") == "Sol_LAB/client/SCDecision.lua"
       and k("c:/x/mods/cleanhotbar/common/media/lua/client/hotbar/a.lua") == "cleanhotbar/client/hotbar/a.lua"
       and k("C:/Program Files (x86)/Steam/steamapps/common/ProjectZomboid/media/lua/shared/luautils.lua") == "vanilla/shared/luautils.lua"
       and k("media/lua/client/ISUI/ISPanel.lua") == "vanilla/client/ISUI/ISPanel.lua"
       and k("C:\\\\x\\\\mods\\\\M\\\\media\\\\lua\\\\server\\\\s.lua") == "M/server/s.lua"
       and k(nil) == "?" and k("weird") == "weird" end)()'''), ev('SolLuaProfiler.keyOf("media/lua/client/ISUI/ISPanel.lua")'))
ck("report: top files sorted, ms/s, overhead, mods line", ev('''(function() LOG = {}
    SolLuaProfiler.cost = { timedUs = 1, untimedUs = 0.5, stepMs = 1 }
    SolLuaProfiler.hooks.OnTick = { name = "OnTick", live = true, recs = {
        { key = "A/client/a.lua", line = 10, ms = 300, n = 900, u = 0 }, { key = "B/client/b.lua", line = 5, ms = 1500, n = 900, u = 0 },
        { key = "A/client/a.lua", line = 99, ms = 600, n = 900, u = 0 }, { key = "C/client/c.lua", line = 1, ms = 0, n = 0, u = 0 } } }
    SolLuaProfiler.report(15000, 900)
    local h, one, two, mods = LOG[1], LOG[2], LOG[3], LOG[#LOG]
    SolLuaProfiler.hooks.OnTick = nil
    return string.find(h, "OnTick 15.0s 900 frames: 160.00 ms/s (2.67 ms/frame), 3 handlers, 180 calls/s, profiler overhead ~0.18 ms/s", 1, true) ~= nil
       and string.find(one, "OnTick #1 100.00 ms/s  B/client/b.lua (fn@L5)  60 calls/s", 1, true) ~= nil
       and string.find(two, "OnTick #2 60.00 ms/s  A/client/a.lua (fn@L99)", 1, true) ~= nil
       and #LOG == 4 and string.find(mods, "B 100.00 | A 60.00", 1, true) ~= nil end)()'''), "\n".join(list(L.eval("LOG").values())))

# ---- part 2: the game's own Kahlua
if not os.path.exists(GAME): ck("game jar present", False, GAME)
else:
    hb = os.path.join(tmp, "harness"); os.makedirs(hb)
    rc = subprocess.run([JDK + r"\javac.exe", "-nowarn", "-encoding", "UTF-8", "-cp", GAME, "-d", hb, os.path.join(HERE, "S106ProfilerHarness.java")], capture_output=True, text=True)
    ck("harness compiles against projectzomboid.jar", rc.returncode == 0, rc.stderr[-800:])
    if rc.returncode == 0:
        rr = subprocess.run([JDK + r"\java.exe", "-cp", GAME + ";" + hb, "S106ProfilerHarness", os.path.join(cl, "SolLuaProfiler.lua")],
                            capture_output=True, text=True, cwd=GAME_D, timeout=300)     # cwd: Kahlua reads stdlib.lua from the game folder
        out = rr.stdout
        for line in out.splitlines():
            if line.startswith("CHECK "):
                m = re.match(r"CHECK (.*) (PASS|FAIL)(.*)$", line); ck("kahlua: " + m.group(1), m.group(2) == "PASS", m.group(3).strip())
            elif line.startswith("MEASURE ") or line.startswith("[SolLuaProfiler]"): print("  " + line)
        ck("kahlua harness finished", "SUMMARY harness fails=0" in out, (out + rr.stderr)[-1500:])
        meas = dict(re.findall(r"^MEASURE (\S+) (\S+)", out, re.M))
        rep = re.search(r"OnTick #1 ([\d.]+) ms/s  HeavyMod/client/Heavy/Tick\.lua", out)
        truth = float(meas.get("heavy_true_ms_per_s", "nan"))
        ck("heaviest file named first: HeavyMod/client/Heavy/Tick.lua", rep is not None, out[-1500:])
        if rep: ck("its ms/s within 10% of nanoTime truth", abs(float(rep.group(1)) - truth) <= 0.10 * truth, "%s vs %s" % (rep.group(1), truth))
        ov = float(meas.get("overhead_us_per_handler_call", "99"))
        ck("measured overhead under 2 us per handler call", ov < 2.0, ov)

# ---- part 3: gates
Gt = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua")
r = subprocess.run([sys.executable, "-I", os.path.join(Gt, "tonumber_check.py"), cl], capture_output=True, text=True); ck("tonumber gate", r.returncode == 0, r.stdout[-300:])
r = subprocess.run([sys.executable, "-I", os.path.join(Gt, "jarcall_check.py"), cl], capture_output=True, text=True); ck("jarcall gate", r.returncode == 0, r.stdout[-400:])
print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(P), len(FAIL))); sys.exit(1 if FAIL else 0)

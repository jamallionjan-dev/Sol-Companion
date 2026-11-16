"""s81 stall_ladder: the installer on copies, SolStallLadder unit tests (watchdog, goals, rung order, bounds), and a replay of the
live 2026-11-10 sequences through the REAL patched SCDriving.lua + SolStallLadder.lua + SolRoadFirst.lua under the game's Lua rules
(kahlua_env), on a mocked bridge / Java planner / world:
  A  22:04:30-22:06:59  two goal_not_free, a drawn path, stalled at 10591.5,11156.4 -> (old) parked for minutes
  B  22:08:15-22:08:31  three goal_not_free at 10603.9,10676.2, at the same spot, every restart -> (old) parked
With the switch off the replay must reproduce the live stop (that is the harness proving the root cause); with it on: never
more than ~3 s without a next step, goals never repeated, all rungs failed -> one line + another road, bounded.
Run: set PYTHONIOENCODING=utf-8 & python test_s81_stall_ladder.py [client dir]   (default: the lab client, read only)
Nothing live is touched: temporary copies only. Offline PASS is not Runtime PASS."""
import hashlib, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LAB_CL = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client"))
GATE = os.path.join(ROOT, "05_TOOLS", "sol_kahlua", "tonumber_check.py")
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, script)] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
def digest(d, names): return {n: hashlib.md5(open(os.path.join(d, n), "rb").read()).hexdigest() for n in names}
def read(p): return open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
TMP = tempfile.mkdtemp(prefix="sol_s81_")

# ================================================================ 1. the installer on copies
def client_copy(name):
    d = os.path.join(TMP, name, "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
    shutil.copytree(LAB_CL, d)
    lua = os.path.join(TMP, name, "Zomboid", "Lua"); os.makedirs(lua)
    with open(os.path.join(lua, "SolFixes_LAB.txt"), "w", newline="") as h: h.write("road_first=on\r\njava_nav=on\r\n")
    return d, os.path.join(lua, "SolFixes_LAB.txt")
FILES = ["SolAuthority.lua", "SCDriving.lua"]
live = digest(LAB_CL, FILES)
CL, FIXFILE = client_copy("main")
b0 = digest(CL, FILES)
q1 = run("apply_s81_stall_ladder.py", CL); a1 = digest(CL, FILES + ["SolStallLadder.lua"]); f1 = open(FIXFILE).read()
q2 = run("apply_s81_stall_ladder.py", CL); a2 = digest(CL, FILES + ["SolStallLadder.lua"])
ck("installer: applies", q1.returncode == 0 and "s81_stall_ladder applied" in q1.stdout, q1.stdout[-400:] + q1.stderr[-600:])
ck("installer: changes SCDriving.lua and SolAuthority.lua", all(b0[n] != a1[n] for n in FILES))
ck("installer: idempotent (second run all kept)", q2.returncode == 0 and a1 == a2 and "edited" not in q2.stdout, q2.stdout[-300:])
ck("installer: SolFixes_LAB.txt gets stall_ladder=on once", f1.count("stall_ladder=on") == 1 and open(FIXFILE).read().count("stall_ladder=on") == 1, f1)
ck("installer: the installed files are untouched", digest(LAB_CL, FILES) == live)
for order in (("apply_s79_horn_hold_lua.py", "apply_s80_speed_levels.py", "apply_s81_stall_ladder.py"),
              ("apply_s81_stall_ladder.py", "apply_s80_speed_levels.py", "apply_s79_horn_hold_lua.py"),
              ("apply_s80_speed_levels.py", "apply_s81_stall_ladder.py")):
    have = [s for s in order if os.path.exists(os.path.join(HERE, s))]
    d, _ = client_copy("order_" + "_".join(s[6:9] for s in have))
    rs = [run(s, d) for s in have]
    au, dv = read(os.path.join(d, "SolAuthority.lua")), read(os.path.join(d, "SCDriving.lua"))
    ok = all(r.returncode == 0 for r in rs) and '"stall_ladder"' in au and "local slFired = false" in dv
    if "apply_s80_speed_levels.py" in have: ok = ok and '"speed_levels"' in au and 'rawget(_G, "SolSpeedGov")' in dv
    if "apply_s79_horn_hold_lua.py" in have: ok = ok and '"horn_hold"' in au
    ck("installer: with the other staged installers, order " + " -> ".join(s[6:9] for s in have), ok, " | ".join(r.stdout[-200:] + r.stderr[-300:] for r in rs))
g = subprocess.run([sys.executable, GATE, os.path.join(CL, "SCDriving.lua"), os.path.join(CL, "SolStallLadder.lua")], capture_output=True, text=True, encoding="utf-8", errors="replace")
ck("lua: tonumber gate passes on the patched files", g.returncode == 0, (g.stdout + g.stderr)[-400:])
L0 = lua51.LuaRuntime()
for n in ("SCDriving.lua", "SolStallLadder.lua", "SolAuthority.lua"):
    e = L0.eval("function(s) local f, e = loadstring(s); return e end")(read(os.path.join(CL, n)))
    ck("lua: %s compiles" % n, e is None, e)
SL_SRC = read(os.path.join(CL, "SolStallLadder.lua"))
ck("lua: SolStallLadder.lua is pure ASCII", all(ord(c) < 128 for c in SL_SRC))
LINE = "علقت هون، رح جرّب من طريق تاني."
ESC = "".join(c if ord(c) < 128 else "\\u%04X" % ord(c) for c in LINE)

# ================================================================ 2. SolStallLadder alone
UNIT = r"""
print = function() end
SW = { stall_ladder = true }
SolAuthority = { on = function(n) return SW[n] == true end }
"""
def unit():
    L = lua51.LuaRuntime(unpack_returned_tuples=True); L.execute(UNIT); L.execute(SL_SRC); return L
L = unit()
ck("unit: the spoken line is the agreed one", L.eval("SolStallLadder.LINE") == ESC, L.eval("SolStallLadder.LINE"))
ck("unit: the line has no technical words or numbers", not any(ch.isascii() and ch.isalnum() for ch in LINE))
L.execute("PTS = {}; for i = 0, 30 do PTS[#PTS + 1] = { x = 100, y = 500 - i * 4 } end; C = SolStallLadder.candidates(PTS, 100.2, 499, 0, -1)")
keys = [L.eval("C[%d].key" % i) for i in range(1, L.eval("#C") + 1)]
ck("goals: five distances x three sides along the road", len(keys) == 15, keys)
ck("goals: never the same goal twice", len(set(keys)) == len(keys), keys)
ck("goals: the first is 12 tiles on, on the road", L.eval("C[1].x") == 100 and abs(L.eval("C[1].y") - 488) < 0.01, (L.eval("C[1].x"), L.eval("C[1].y")))
ck("goals: both sides of the lane", L.eval("C[2].x") != 100 and L.eval("C[3].x") != 100 and L.eval("C[2].x") + L.eval("C[3].x") == 200)
ck("goals: all within the planner's reach", all(L.eval("(C[%d].x-100.2)^2+(C[%d].y-499)^2 <= 44*44" % (i, i)) for i in range(1, len(keys) + 1)))
L.execute("C2 = SolStallLadder.candidates(nil, 0, 0, 1, 0)")
ck("goals: no route: straight ahead", L.eval("#C2") == 15 and L.eval("C2[1].x") == 12)
L.execute("C3 = SolStallLadder.candidates({ {x=0,y=0}, {x=0,y=-15} }, 0, 0, 0, -1)")
ck("goals: a short route gives its end, once", L.eval("#C3") == 6, L.eval("#C3"))
W = "WORLD = { kind = function(x, y) return KIND end, open = function() return OPEN end, cars = function() return CARS end }; KIND, OPEN, CARS = nil, true, {}"
L.execute(W)
ck("room: an empty road", L.eval("SolStallLadder.spotFree(WORLD, 10, 10, 0, -1, 2.4, 1.1, ME)") is True)
L.execute("CARS = { { v = {}, x = 10, y = 11, fx = 0, fy = -1 } }")
ck("room: a parked car there", L.eval("SolStallLadder.spotFree(WORLD, 10, 10, 0, -1, 2.4, 1.1, ME)") is False)
L.execute("CARS = { { v = {}, x = 14, y = 10, fx = 0, fy = -1 } }")
ck("room: a parked car the other side of the lane", L.eval("SolStallLadder.spotFree(WORLD, 10, 10, 0, -1, 2.4, 1.1, ME)") is True)
L.execute("ME = {}; CARS = { { v = ME, x = 10, y = 10, fx = 0, fy = -1 } }")
ck("room: her own car does not count", L.eval("SolStallLadder.spotFree(WORLD, 10, 10, 0, -1, 2.4, 1.1, ME)") is True)
L.execute("CARS = {}; KIND = 'solid'")
ck("room: a wall", L.eval("SolStallLadder.spotFree(WORLD, 10, 10, 0, -1, 2.4, 1.1, ME)") is False)
L.execute("KIND = nil; OPEN = false")
ck("room: ground a car cannot stand on", L.eval("SolStallLadder.spotFree(WORLD, 10, 10, 0, -1, 2.4, 1.1, ME)") is False)

FAKE = r"""
CALLS, LOGS, SAID, PARKED = {}, {}, {}, nil
POS = { 100, 500, 0, -1 }
PLAN_OK, NUDGE_OK, REROUTE_OK, FREE = false, false, true, nil
OPS = {
    log = function(job, t) LOGS[#LOGS + 1] = t end,
    pose = function(job) return POS[1], POS[2], POS[3], POS[4] end,
    size = function(job) return { wheelbase = 2.6, kmax = 0.2, halfLength = 2.4, halfWidth = 1.1 } end,
    points = function(job) local p = {}; for i = 0, 40 do p[#p + 1] = { x = 100, y = 500 - i * 4 } end; return p end,
    free = function() return FREE end,
    plan = function(job, sx, sy, hx, hy, gx, gy, ghx, ghy, size, kind, wide) CALLS[#CALLS + 1] = kind .. "@" .. math.floor(gx + 0.5) .. ":" .. math.floor(gy + 0.5); if PLAN_OK then job.jnav = { sl = kind } end; return PLAN_OK end,
    nudge = function(job) CALLS[#CALLS + 1] = "nudge"; if NUDGE_OK then job.steer = {} end; return NUDGE_OK end,
    reroute = function(job, st) CALLS[#CALLS + 1] = "reroute"; return REROUTE_OK end,
    park = function(job, why) PARKED = why; job.parked = true; CALLS[#CALLS + 1] = "park:" .. why; return true end,
    say = function(job, line) SAID[#SAID + 1] = line; return true end,
}
J = { managed = true, phase = "bypassing" }
"""
L = unit(); L.execute(FAKE)
L.execute("R = SolStallLadder.onFail(J, 'stalled', {}, 1000, OPS)")
calls = [L.eval("CALLS[%d]" % i) for i in range(1, L.eval("#CALLS") + 1)]
kinds = [c.split("@")[0] for c in calls]
ck("rungs: every rung fails at once: replan x3, nudge, reverse x2, replan_wide x3, another road - in that order, in one tick",
   kinds == ["replan"] * 3 + ["nudge"] + ["reverse"] * 2 + ["replan_wide"] * 3 + ["reroute"], calls)
ck("rungs: one goal per try, so a refusing planner is asked at most 8 times", len([c for c in calls if "@" in c]) == 8, calls)
ck("rungs: the replan goals are all different", len(set(c for c in calls if c.startswith("replan"))) == 6, calls)
ck("rungs: back up 3.5 then 2.5 tiles", calls[4] == "reverse@100:504" and calls[5] == "reverse@100:503", calls[4:6])
ck("rungs: all failed -> another road and the one line", L.eval("R") == "started" and L.eval("#SAID") == 1 and L.eval("SAID[1]") == ESC)
ck("rungs: the new road starts the ladder over", L.eval("J.sl.rung") == 1 and L.eval("J.slDrive.reroutes") == 1)
L.execute("CALLS = {}; R = SolStallLadder.onFail(J, 'goal_not_free', {}, 5000, OPS)")
ck("speech: the line is not repeated within two minutes", L.eval("#SAID") == 1 and L.eval("J.slDrive.reroutes") == 2)
L.execute("CALLS = {}; R = SolStallLadder.onFail(J, 'goal_not_free', {}, 200000, OPS)")
ck("speech: a third road, minutes later, may say it again", L.eval("#SAID") == 2 and L.eval("J.slDrive.reroutes") == 3)
L.execute("CALLS = {}; R = SolStallLadder.onFail(J, 'goal_not_free', {}, 210000, OPS)")
ck("bounded: after three other roads the drive ends (route_blocked), no fourth road", L.eval("R") == "parked" and L.eval("PARKED") == "route_blocked" and L.eval("J.slDrive.reroutes") == 3)
L = unit(); L.execute(FAKE); L.execute("REROUTE_OK = false; R = SolStallLadder.onFail(J, 'stalled', {}, 1000, OPS)")
ck("bounded: no other road at all -> the drive ends, and she does not promise one", L.eval("R") == "parked" and L.eval("PARKED") == "route_blocked" and L.eval("#SAID") == 0)
L = unit(); L.execute(FAKE); L.execute("PLAN_OK = true; R = SolStallLadder.onFail(J, 'stalled', {}, 1000, OPS)")
ck("rungs: the first replan that starts ends the step (nothing else runs)", L.eval("R") == "started" and L.eval("#CALLS") == 1 and L.eval("J.jnav.sl") == "replan")
L.execute("J.jnav = nil; R = SolStallLadder.onFail(J, 'goal_not_free', {}, 1300, OPS)")
ck("rungs: goal_not_free -> a different goal, not the same one", L.eval("CALLS[2]") != L.eval("CALLS[1]") and L.eval("J.sl.tries") == 2, (L.eval("CALLS[1]"), L.eval("CALLS[2]")))
L.execute("J.jnav = nil; SolStallLadder.onFail(J, 'goal_not_free', {}, 1600, OPS); J.jnav = nil; SolStallLadder.onFail(J, 'goal_not_free', {}, 1900, OPS)")
ck("rungs: after three replans the nudge", L.eval("CALLS[#CALLS]").startswith("reverse") or L.eval("CALLS[#CALLS]") == "nudge", L.eval("CALLS[#CALLS]"))
L = unit(); L.execute(FAKE); L.execute("FREE = false; R = SolStallLadder.onFail(J, 'stalled', {}, 1000, OPS)")
c = [L.eval("CALLS[%d]" % i) for i in range(1, L.eval("#CALLS") + 1)]
ck("rungs: goals with no room are not even sent to the planner", not any(x.startswith("replan") or x.startswith("reverse") for x in c) and "reroute" in c, c)
L = unit(); L.execute(FAKE); L.execute("PLAN_OK = true; J.sl = { x = 100, y = 500, rung = 3, tries = 0, tried = {} }; J.jnav = nil; SolStallLadder.next(J, 1000, OPS); J.jnav = nil; DONE = SolStallLadder.onDone(J, 'reverse', {}, 3000, OPS)")
ck("rungs: backed up -> replan from there, free to back up", L.eval("DONE") is True and L.eval("J.jnav.sl") == "replan_wide")
L.execute("SolStallLadder.onDone(J, 'replan', {}, 4000, OPS)")
ck("rungs: past it -> the next obstacle starts at the first rung", L.eval("J.sl") is None)
L = unit(); L.execute(FAKE); L.execute("SolStallLadder.MAX_TOTAL = 5; R = SolStallLadder.onFail(J, 'stalled', {}, 1000, OPS)")
ck("bounded: the per-drive try cap ends the drive", L.eval("R") == "parked" and L.eval("PARKED") == "route_blocked" and L.eval("#CALLS") == 6)
L = unit(); L.execute(FAKE); L.execute("POS = { 100, 500, 0, -1 }; SolStallLadder.onFail(J, 'stalled', {}, 1000, OPS); A = J.sl; POS = { 100, 470, 0, -1 }; CALLS = {}; SolStallLadder.onBlocked(J, {}, 9000, OPS)")
ck("rungs: stuck somewhere else (30 tiles on) -> a fresh ladder there", L.eval("J.sl ~= A") and L.eval("J.sl.y") == 470)

# ---- the watchdog
L = unit(); L.execute(FAKE)
W0 = "J = { managed = true, phase = 'following', bypass = true }; POS = { 100, 500, 0, -1 }; CALLS = {}"
def watch(t, state="manual", cruise=0):
    return L.eval("SolStallLadder.watch(J, '%s', { cruiseKmh = %s }, %d, OPS)" % (state, cruise, t))
L.execute(W0)
r = [watch(t) for t in (0, 1000, 2000, 2900)]
ck("watchdog: quiet for the first 3 s", r == [False] * 4)
ck("watchdog: 3 s standing still in a way-round episode -> the next rung", watch(3000) is True and L.eval("#CALLS") >= 1)
L.execute(W0 + "; J.bypass = nil")
ck("watchdog: no episode (a plain drive): never", not any(watch(t) for t in range(0, 10001, 500)))
L.execute(W0)
ck("watchdog: the road follower's own check owns follow with speed asked", not any(watch(t, "follow", 20) for t in range(0, 10001, 500)))
L.execute(W0)
ck("watchdog: blocked belongs to tryBypass (the ladder's onBlocked)", not any(watch(t, "blocked") for t in range(0, 10001, 500)))
L.execute(W0 + "; J.jnav = {}")
ck("watchdog: a Java plan running owns its own clock", not any(watch(t) for t in range(0, 10001, 500)))
L.execute(W0 + "; J.parked = true")
ck("watchdog: a finished drive is left alone", not any(watch(t) for t in range(0, 10001, 500)))
L.execute(W0)
def moving(t):
    L.execute("POS[2] = 500 - %f" % (t / 1000.0)); return watch(t)
ck("watchdog: moving half a tile a second never fires", not any(moving(t) for t in range(0, 10001, 500)))

# ================================================================ 3. the live sequences through the real SCDriving.lua
DRV_SRC = read(os.path.join(CL, "SCDriving.lua"))
RF_SRC = read(os.path.join(CL, "SolRoadFirst.lua"))
WORLD = r"""
NOW = 0
LOG = {}
print = function(s) LOG[#LOG + 1] = { t = NOW, s = tostring(s) } end
SW = { stall_ladder = true, java_nav = true, road_bypass = true, road_first = true }
SolAuthority = { on = function(n) return SW[n] == true end }
Vector3f = { new = function() return {} end }
POS = { x = 0, y = 0, hx = 0, hy = -1 }
PARKEDCARS = {}
ACTOR = {}
CAR = {}
ACTOR.getVehicle = function() return CAR end
CAR.getDriver = function() return ACTOR end
CAR.getX = function() return POS.x end
CAR.getY = function() return POS.y end
CAR.getZ = function() return 0 end
CAR.isKeysInIgnition = function() return true end
CAR.isEngineRunning = function() return true end
CAR.getForwardVector = function() return { x = function() return POS.hx end, z = function() return POS.hy end } end
SAID = {}
SurvivorCompanion = {
    Call = {
        static = function(api, name, ...) local f = api[name]; if f == nil then return false, "no " .. name end; return true, f(...) end,
        method = function(o, name, ...) if o == nil or o[name] == nil then return false, nil end; return true, o[name](o, ...) end,
    },
    ActionSupervisor = {
        Priority = { TRAVEL = 1 },
        begin = function(actor, spec) SUP = spec; return "tok" end,
        transition = function() return true end,
        isCurrent = function(t) return t == "tok" and not CANCELLED end,
        cancel = function(actor, reason) CANCELLED = true; local ok = SUP.onCancel(nil, reason); return ok end,
    },
    Dialogue = { emitResolved = function(actor, topic, line) SAID[#SAID + 1] = { t = NOW, topic = topic, line = line }; return true, line end },
}
-- the native bridge
NAT = { active = true, mode = "manual", cruise = 0, route = nil, ri = 1 }
SCBridge = {
    getLastFailure = function() return "" end,
    driveStart = function() NAT.active = true; return true end,
    driveStop = function() NAT.mode, NAT.cruise = "stopped", 0; return true end,
    driveSet = function(a, steer, kmh) NAT.mode, NAT.cruise, NAT.route, NAT.bx, NAT.by = "manual", kmh, nil, nil, nil; return true end,   -- by hand: no lane follower, no blocked point
    driveFollow = function(a, text, kmh)
        local pts = {}
        for x, y in string.gmatch(text, "([%-%d%.]+),([%-%d%.]+),[%-%d%.]+") do pts[#pts + 1] = { x = tonumber(x), y = tonumber(y) } end
        NAT.route, NAT.ri, NAT.mode, NAT.cruise = pts, 2, "follow", kmh
        FOLLOWS = (FOLLOWS or 0) + 1
        return true
    end,
    driveTurnAround = function() return false end,
    driveStatus = function(a, out)
        out.active = NAT.active; out.engineRunning = true; out.cruiseKmh = NAT.cruise; out.speedKmh = NAT.speed or 0
        out.mode = NAT.mode; out.state = "driving"
        if NAT.mode == "follow" and NAT.bx then out.mode, out.blockedX, out.blockedY = "blocked", NAT.bx, NAT.by end
        return true
    end,
}
-- the road planner: straight north from the car; with a place to avoid, a parallel street 25 tiles east
ROUTES = 0
REROUTE_OK = true
SurvivorCompanion.ExpeditionRoute = { planAvoidingAll = function(actor, goal, circles)
    ROUTES = ROUTES + 1
    local pts = { { x = POS.x, y = POS.y, width = 6 } }
    if #circles > 0 then
        if not REROUTE_OK then return nil, "no_route" end
        DETOURS = (DETOURS or 0) + 1
        pts[#pts + 1] = { x = POS.x + 25, y = POS.y, width = 6 }
        for i = 1, 200 do pts[#pts + 1] = { x = POS.x + 25, y = POS.y - i * 4, width = 6 } end
    else
        for i = 1, 200 do pts[#pts + 1] = { x = POS.x, y = POS.y - i * 4, width = 6 } end
    end
    return { points = pts, roadLength = 240 }
end }
-- what the world holds
local function carAt(px, py, c) return math.abs(px - c.x) <= 1.4 and math.abs(py - c.y) <= 2.7 end   -- parked north-south
SolBypass = {
    world = {
        kind = function() return nil end,
        open = function() return true end,
        cars = function(x, y, r) local out = {}; for _, c in ipairs(PARKEDCARS) do if (c.x - x) ^ 2 + (c.y - y) ^ 2 <= r * r then out[#out + 1] = { v = c, x = c.x, y = c.y, fx = 0, fy = -1, halfL = 2.3, halfW = 1.0 } end end; return out end,
    },
    measure = function() return { wheelbase = 2.6, kmax = 0.2, halfLength = 2.4, halfWidth = 1.05 } end,
    plan = function() return nil, "no_way_round" end,
    nudge = function(cx, cy, hx, hy) NUDGES = (NUDGES or 0) + 1; if NUDGE_ROOM then return { { x = cx, y = cy }, { x = cx + 3, y = cy - 3 } } end; return nil end,
    aheadClear = function() return true end,
    steerStep = function(s) return 0.5, 5 end,     -- she steers, the car does not move (boxed in)
    scanAhead = function() return nil end,
    noteStuck = function() end,
}
-- the Java planner (SolNav): scripted first plans, then a rule
JS = { state = "idle" }
PLANS = {}
SCRIPT = {}
function RULE(p) return { fail = "goal_not_free" } end
function solNavPlan(v, sx, sy, hx, hy, gx, gy, ghx, ghy)
    if JS.state == "capturing" or JS.state == "planning" then return false end
    local p = { t = NOW, sx = sx, sy = sy, gx = gx, gy = gy, ghx = ghx, ghy = ghy, turn = TURN == true }
    TURN = false
    PLANS[#PLANS + 1] = p
    local o = SCRIPT[#PLANS] or RULE(p)
    JS.plan, JS.out, JS.at, JS.state = p, o, NOW, "planning"
    return true
end
function solNavState() return JS.state end
function solNavBeat() end
function solNavFollow() JS.state, JS.at = "following", NOW; JS.from = { x = POS.x, y = POS.y }; return true end
function solNavStop() if JS.state ~= "idle" then JS.state = "idle" end end
function solNavMayTurnBack() TURN = true end
function solNavBanClear() end
function solNavBan() end
function solNavCorridorClear() end
function solNavCorridorPoint() end
function solNavCorridorRadius() end
function STEP(dt)
    NOW = NOW + dt
    if JS.state == "planning" and NOW - JS.at >= 200 then
        if JS.out.fail then JS.state = "failed:" .. JS.out.fail else JS.state = "ready" end
    elseif JS.state == "following" then
        local o, f = JS.out, JS.from
        local to = o.to or { x = JS.plan.gx, y = JS.plan.gy }
        local k = math.min(1, (NOW - JS.at) / (o.ms or 3000))
        POS.x, POS.y = f.x + (to.x - f.x) * k, f.y + (to.y - f.y) * k
        if k >= 1 then JS.state = o.finish == "stalled" and "failed:stalled" or "done" end
    end
    if NAT.mode == "follow" and NAT.route and JS.state ~= "following" then        -- the road follower: 3 tiles a second, stops for a parked car ahead
        local p = NAT.route[NAT.ri]
        if p == nil then NAT.mode, NAT.speed = "arrived", 0 else
            local dx, dy = p.x - POS.x, p.y - POS.y
            local d = math.sqrt(dx * dx + dy * dy)
            local hx, hy = d > 0.01 and dx / d or POS.hx, d > 0.01 and dy / d or POS.hy
            local blocked = nil
            for _, c in ipairs(PARKEDCARS) do
                local ax, ay = c.x - POS.x, c.y - POS.y
                local along, across = ax * hx + ay * hy, math.abs(-ax * hy + ay * hx)
                if along > 0 and along < 6.5 and across < 2.2 then blocked = c end
            end
            if blocked then NAT.speed, NAT.bx, NAT.by = 0, blocked.x, blocked.y
            else
                local step = 3 * dt / 1000
                NAT.speed, NAT.bx, NAT.by = 10, nil, nil
                POS.hx, POS.hy = hx, hy
                if d <= step then POS.x, POS.y, NAT.ri = p.x, p.y, NAT.ri + 1 else POS.x, POS.y = POS.x + hx * step, POS.y + hy * step end
            end
        end
    else NAT.speed = 0 end
end
"""
def replay(name, sw_on, start, heading, cars, script, rule, until_ms, nudge_room=False, reroute_ok=True, restarts=()):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(WORLD)
    L.execute(RF_SRC); L.execute(SL_SRC); L.execute(DRV_SRC)
    L.execute("SW.stall_ladder = %s; NUDGE_ROOM = %s; REROUTE_OK = %s" % ("true" if sw_on else "false", "true" if nudge_room else "false", "true" if reroute_ok else "false"))
    L.execute("POS.x, POS.y, POS.hx, POS.hy = %f, %f, %f, %f" % (start[0], start[1], heading[0], heading[1]))
    for c in cars: L.execute("PARKEDCARS[#PARKEDCARS + 1] = { x = %f, y = %f }" % c)
    for i, s in enumerate(script): L.execute("SCRIPT[%d] = %s" % (i + 1, s))
    if rule: L.execute("function RULE(p) " + rule + " end")
    G = L.globals()
    assert L.eval("SurvivorCompanion.Driving.drive(ACTOR, { x = 10840, y = 10120, z = 0 }, { speedKmh = 30, blockWaitMs = 2500 })")
    t, track, last = 0, [], None
    while t < until_ms:
        if t in restarts:                                   # Jamal presses drive again
            L.execute("CANCELLED = false; SurvivorCompanion.Driving.stop(ACTOR, 'new_destination'); CANCELLED = false; JS.state = 'idle'; NAT.mode = 'manual'")
            L.execute("print('[SolDrive] stop(new_destination) -> true cancelled.')")
            L.eval("SurvivorCompanion.Driving.drive(ACTOR, { x = 10840, y = 10120, z = 0 }, { speedKmh = 30, blockWaitMs = 2500 })")
        G.STEP(100); t += 100
        G.SurvivorCompanion.Driving.tick(t)
        track.append((t, L.eval("POS.x"), L.eval("POS.y")))
    js = L.eval("SurvivorCompanion.Driving.jobStatus(ACTOR)")
    logs = [(L.eval("LOG[%d].t" % i), L.eval("LOG[%d].s" % i)) for i in range(1, L.eval("#LOG") + 1)]
    plans = [dict(t=L.eval("PLANS[%d].t" % i), gx=L.eval("PLANS[%d].gx" % i), gy=L.eval("PLANS[%d].gy" % i), turn=L.eval("PLANS[%d].turn" % i)) for i in range(1, L.eval("#PLANS") + 1)]
    said = [L.eval("SAID[%d].line" % i) for i in range(1, L.eval("#SAID") + 1)]
    res = dict(L=L, logs=logs, plans=plans, said=said, track=track, parked=js and js["parked"], result=js and js["result"], reason=js and js["reason"],
               detours=L.eval("DETOURS or 0"), nudges=L.eval("NUDGES or 0"))
    # the longest stretch with the car still and nothing new in the log, while the drive is not over
    events = sorted(set([lt for lt, _ in logs] + [tt for (tt, x, y), (_, x0, y0) in zip(track[1:], track[:-1]) if (x - x0) ** 2 + (y - y0) ** 2 > 1e-6]))
    end = until_ms
    for lt, s in logs:
        if "the drive ends here" in s: end = min(end, lt)
    gaps, prev = [], 0
    for e in events + [end]:
        if e > end: break
        gaps.append((e - prev, prev)); prev = e
    res["idle"] = max(gaps) if gaps else (0, 0)
    res["moved"] = ((track[-1][1] - start[0]) ** 2 + (track[-1][2] - start[1]) ** 2) ** 0.5
    return res

def show(r, n=60):
    return " || ".join("%d %s" % (t, s.replace("[SolDrive] ladder ", "")[:90]) for t, s in r["logs"][-n:])

# ---- A: 22:04:30 at 10592.02,11172.76, heading north; the live order: goal_not_free, goal_not_free, a drawn path that stalls at 10591.5,11156.4
A_START, NORTH = (10592.0234375, 11172.7578125), (0.0, -1.0)
A_CARS = [(10592.6, 11166.0), (10592.4, 11150.0), (10592.6, 11144.5), (10592.4, 11139.0), (10569.3, 11205.5)]
A_SCRIPT = ['{ fail = "goal_not_free" }', '{ fail = "goal_not_free" }', '{ to = { x = 10591.5078125, y = 11156.4296875 }, ms = 9800, finish = "stalled" }']
ALL_FAIL = 'return { fail = "goal_not_free" }'

r = replay("A old", False, A_START, NORTH, A_CARS, A_SCRIPT, ALL_FAIL, 140000)
ck("replay A, switch off: reproduces the live stop (parked failed no_way_round after the stall)",
   r["parked"] and r["result"] == "failed" and r["reason"] == "no_way_round", (r["result"], r["reason"], show(r, 12)))
ck("replay A, switch off: SolRoadFirst refused the other street ('nothing real blocks')", any("nothing real blocks the road" in s for _, s in r["logs"]))
ck("replay A, switch off: she then stands still for minutes (live: 22:04:42 -> 22:06:41)", r["idle"][0] >= 120000, r["idle"])

r = replay("A1 new, all fail", True, A_START, NORTH, A_CARS, A_SCRIPT, ALL_FAIL, 140000)
fails = [t for t, s in r["logs"] if "Java way round failed" in s or "steering stalled" in s or "standing still" in s]
acts = [t for t, s in r["logs"] if "drawing the way round in Java" in s or "steering the way round" in s or "another road" in s or "drive ends here" in s]
late = [f for f in fails if not any(f <= a <= f + 3000 for a in acts)]
stall = [t for t, s in r["logs"] if "Java way round failed: stalled at 10591.5078125,11156.4296875" in s]
ck("replay A1: the 22:04:42 stall is followed by the next rung within 3 s (every failure is)", stall and fails and not late, (stall, late, show(r, 30)))
ck("replay A1: never more than ~3 s standing with nothing new", r["idle"][0] <= 3500, (r["idle"], show(r, 30)))
ck("replay A1: every rung ran: replans, back-up tries, replans free to back up", sum(1 for p in r["plans"] if p["turn"]) >= 2 and len(r["plans"]) >= 6, [(round(p["gx"], 1), round(p["gy"], 1), p["turn"]) for p in r["plans"]])
spot = [p for p in r["plans"][3:] if abs(p["gy"] - 11156) < 50]
goals = [(round(p["gx"], 1), round(p["gy"], 1)) for p in spot]
ck("replay A1: no goal is tried twice at the stuck place", len(goals) == len(set(goals)), goals)
ck("replay A1: all rungs failed -> she says the one line, once", r["said"] == [ESC], r["said"])
ck("replay A1: ... and the drive takes another road (planAvoidingAll with the place avoided) and moves on", r["detours"] >= 1 and r["moved"] > 30 and not r["parked"], (r["detours"], r["moved"], r["result"], r["reason"]))
ck("replay A1: bounded (a handful of plans, not a loop)", len(r["plans"]) <= 20, len(r["plans"]))

r = replay("A2 new, no other road", True, A_START, NORTH, A_CARS, A_SCRIPT, ALL_FAIL, 140000, reroute_ok=False)
ck("replay A2: no other road either -> the drive ends (route_blocked), bounded, no false promise", r["parked"] and r["reason"] in ("route_blocked", "no_route") and r["said"] == [] and len(r["plans"]) <= 20, (r["result"], r["reason"], r["said"], len(r["plans"])))
ck("replay A2: up to the end she never stood more than ~3 s", r["idle"][0] <= 3500, r["idle"])

r = replay("A3 new, nudge room but boxed in", True, A_START, NORTH, A_CARS, A_SCRIPT, ALL_FAIL, 140000, nudge_room=True)
ck("replay A3: the nudge is tried, its 3 s stall feeds the next rung", r["nudges"] >= 1 and any("steering stalled" in s for _, s in r["logs"]) and r["idle"][0] <= 3500, (r["idle"], show(r, 20)))
ck("replay A3: ends on another road with the one line", r["said"] == [ESC] and r["detours"] >= 1)

BACK_WORKS = r'''
if p.gy > POS.y + 1 then return { ms = 2500 } end                                   -- backing up: there is room behind
if p.turn and math.abs(p.gx - 10592) > 2 then return { ms = 5000 } end              -- from there, past them on the other side of the lane
return { fail = "goal_not_free" }'''
r = replay("A4 new, back up then past", True, A_START, NORTH, A_CARS, A_SCRIPT, BACK_WORKS, 60000)
ck("replay A4: replans fail -> backs up -> the replan from there gets past, no other road needed",
   any(p["gy"] > 11157 for p in r["plans"]) and r["detours"] == 0 and r["said"] == [] and not r["parked"] and any("past it" in s for t, s in r["logs"] if t > 10000),
   [(round(p["gx"], 1), round(p["gy"], 1), p["turn"]) for p in r["plans"]])
ck("replay A4: never more than ~3 s standing", r["idle"][0] <= 3500, r["idle"])

# ---- B: 22:08:15 at 10603.875,10676.18: three goal_not_free at the same place, every restart the same
B_START = (10603.875, 10676.1796875)
B_CARS = [(10604.9, 10676.18 - a) for a in (8.0, 13.5, 19.0, 24.5, 30.0, 35.5)]   # a row parked in her lane, a little to the right
JAVA_FREE = r'''
for _, c in ipairs(PARKEDCARS) do if (c.x - p.gx) ^ 2 + (c.y - p.gy) ^ 2 < 9 then return { fail = "goal_not_free" } end end
return { ms = 6000 }'''
r = replay("B old", False, B_START, NORTH, B_CARS, [], JAVA_FREE, 17000, restarts=(6400, 12000))
ck("replay B, switch off: reproduces 22:08:15 - three goal_not_free, then parked, again on every restart",
   r["parked"] and r["reason"] == "no_way_round" and sum(1 for _, s in r["logs"] if "goal_not_free" in s) >= 9, (r["reason"], show(r, 12)))
ck("replay B, switch off: the goals were the road's centre line only", all(abs(p["gx"] - 10603.875) < 0.5 for p in r["plans"]), [(round(p["gx"], 1), round(p["gy"], 1)) for p in r["plans"]])
r = replay("B new", True, B_START, NORTH, B_CARS, [], JAVA_FREE, 40000)
ck("replay B: the ladder picks a goal beside the row (other side of the lane), not the same one again",
   r["plans"] and abs(r["plans"][0]["gx"] - 10603.875) > 2 and not r["parked"], [(round(p["gx"], 1), round(p["gy"], 1)) for p in r["plans"]])
ck("replay B: she gets past without another road and without a word", any("past it" in s for _, s in r["logs"]) and r["detours"] == 0 and r["said"] == [] and r["moved"] > 20, (r["moved"], show(r, 12)))
ck("replay B: never more than ~3 s standing", r["idle"][0] <= 3500, r["idle"])
r = replay("B2 new, nothing beside it either", True, B_START, NORTH, B_CARS, [], ALL_FAIL, 60000)
ck("replay B2: same rungs as the stall: back-up tries, replans, then the line and another road",
   any(p["turn"] for p in r["plans"]) and r["said"] == [ESC] and r["detours"] >= 1 and r["moved"] > 20 and r["idle"][0] <= 3500, (r["idle"], r["said"], show(r, 20)))
goals = [(round(p["gx"], 1), round(p["gy"], 1)) for p in r["plans"] if p["gy"] < 10680 and abs(p["gx"] - 10604) < 10]
ck("replay B2: no goal tried twice", len(goals) == len(set(goals)), goals)

r = replay("C switch on, a plain drive", True, (10603.875, 10900.0), NORTH, [], [], ALL_FAIL, 20000)
ck("plain drive, switch on: nothing changes (no ladder, no line, she drives)", r["plans"] == [] and r["said"] == [] and r["moved"] > 50 and not any("stall_ladder" in s for _, s in r["logs"]))

shutil.rmtree(TMP, ignore_errors=True)
print("ALL PASS" if not FAIL else "FAILED: %d" % len(FAIL))
sys.exit(1 if FAIL else 0)

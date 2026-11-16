"""s87: apply_s87_lua.py + apply_s87_mind.py on temporary copies (idempotent); SolSmartPark.lua (smart_park) and SolMoveCheck.lua
(move_check) under the game's Lua rules with a mocked world; the Mind's park flow with mocks; the card (card_check.py on the
patched copy, its own budget numbers) and test_s82_route_eval.py --as-is. Nothing live is touched.
Run: set PYTHONIOENCODING=utf-8 & python test_s87.py [sol_mind dir] [client dir]   (defaults: 05_TOOLS/sol_mind, the lab client; read only)
Offline PASS is not Runtime PASS."""
import hashlib, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, HERE)
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)


# ================================================================ child: the patched Mind with mocks
def mind_child(mind):
    sys.path.insert(0, mind)
    import time as T
    import chat_service as CS, model_router as MR
    ck("child: the patched copy is what got imported", os.path.dirname(os.path.abspath(CS.__file__)) == os.path.abspath(mind))
    ck("card: park says the garage or the nearest free spot", "أقرب مكان فاضي" in MR.COMMANDS["park"][0] and MR.COMMANDS["park"][1] == "صفي السيارة", MR.COMMANDS["park"])
    W = CS.smart_park_wanted
    near = {"solParking": {"x": 100, "y": 100}, "sol": {"x": 110, "y": 105}}
    far = {"solParking": {"x": 100, "y": 100}, "sol": {"x": 300, "y": 105}}
    ck("wanted: no marked parking -> the nearest free spot", W({"sol": {"x": 1, "y": 1}}, "صفي السيارة") is True)
    ck("wanted: her car within 40 tiles of his marked area -> the garage park", W(near, "صفي السيارة") is False)
    ck("wanted: far from it -> the nearest free spot", W(far, "صفيها هون") is True)
    ck("wanted: far, but he names the garage -> the garage park", W(far, "صفي السيارة بالكراج") is False and W(far, "حطي السيارة بالموقف") is False)

    FLAGS, CALLS, LATER, LOG = {"smart_park": True}, [], [], []
    GAME = {"find": {"ok": True, "reason": "spot:121.5,102.5,120,100,122,104,stall,3"}, "settle": {"ok": True, "reason": "approaching"},
            "status": {"ok": True, "reason": "inside"}}
    CS.fix_on = lambda d, n: FLAGS.get(n, False)
    def fake_run(d, action, option=None, wait=3.0):
        CALLS.append((action, option)); return dict(GAME.get(option) or {"ok": True, "reason": ""})
    CS.run_action = fake_run
    GPS = []
    CS.gps_request = lambda d, f: GPS.append(f) or "rid1"
    DRIVE = {"v": {"ok": True, "reason": ""}}
    CS._drive_outcome = lambda d, rid, base: dict(base, **DRIVE["v"])
    CS._park_car_s86 = lambda self, snap: CALLS.append(("garage", None))
    CS._park_watch_s86 = lambda self: None
    GS = {"v": {}}
    def chat():
        c = CS.Chat.__new__(CS.Chat)
        c.dir, c.log, c._forced = "x", LOG.append, None
        c._say_later = LATER.append
        c.gps_state = lambda: GS["v"]
        return c
    def park(snap, said="صفي السيارة"):
        del CALLS[:], GPS[:], LATER[:]
        c = chat(); c._park_said_s87 = said
        CS.Chat._park_car(c, snap)
        return c
    FLAGS["smart_park"] = False
    c = park(far)
    ck("park, switch off: the garage park as before", CALLS == [("garage", None)], CALLS)
    FLAGS["smart_park"] = True
    c = park(near)
    ck("park, at home: the garage park as before", CALLS == [("garage", None)], CALLS)
    c = park(far)
    ck("park, away: the game picks the spot, she drives there slowly", CALLS == [("sol_smart_park", "find")] and GPS and GPS[0]["x"] == 121 and GPS[0]["y"] == 102 and GPS[0]["speed"] == "slow", (CALLS, GPS))
    ck("park, away: 'رايحة صفها بأقرب مكان فاضي.' and the watch is armed", c._forced == CS.SMART_PARK_LINES["start"] and c._smart_park_waiting["phase"] == "drive", (c._forced, getattr(c, "_smart_park_waiting", None)))
    ck("park, away: the garage watch is not armed too", getattr(c, "_park_waiting", "x") is None)
    for reason, key in (("no_spot", "no_spot"), ("no_car", "no_car"), ("not_loaded", "not_loaded")):
        GAME["find"] = {"ok": False, "reason": reason}
        c = park(far)
        ck("park, away: find %s -> '%s', no drive" % (reason, CS.SMART_PARK_LINES[key]), c._forced == CS.SMART_PARK_LINES[key] and not GPS and c._smart_park_waiting is None, c._forced)
    GAME["find"] = {"ok": None, "reason": "sent; the game did not confirm yet"}
    c = park(far)
    ck("park, away: the game did not answer -> a plain line, no drive", c._forced == CS.SMART_PARK_LINES["no_answer"] and not GPS, c._forced)
    GAME["find"] = {"ok": True, "reason": "already:120,100,122,104"}
    c = park(far)
    ck("park, away: already inside a free spot -> 'هي مصفوفة بمكان صف.', no drive", c._forced == CS.SMART_PARK_LINES["already"] and not GPS, c._forced)
    GAME["find"] = {"ok": True, "reason": "spot:121.5,102.5,120,100,122,104,open,40"}
    DRIVE["v"] = {"ok": False, "reason": "no_usable_car"}
    c = park(far)
    ck("park, away: the drive refused -> its reason, nothing armed", c._forced == CS.drive_reply({"ok": False, "reason": "no_usable_car"}) and c._smart_park_waiting is None, c._forced)
    DRIVE["v"] = {"ok": True, "reason": "walking_to_door"}
    c = park(far)
    ck("park, away: walking to the wheel first counts as started", c._smart_park_waiting is not None)

    # the watch
    def watch(c): del CALLS[:]; CS.Chat._park_watch(c)
    GS["v"] = {"result": "driving", "reason": ""}
    watch(c)
    ck("watch: driving -> nothing", CALLS == [] and LATER == [] and c._smart_park_waiting["phase"] == "drive")
    GS["v"] = {"result": "arrived", "reason": "arrived"}
    watch(c)
    ck("watch: arrived -> the last metres (settle)", CALLS == [("sol_smart_park", "settle")] and c._smart_park_waiting["phase"] == "settle", (CALLS, c._smart_park_waiting))
    GAME["status"] = {"ok": True, "reason": "working"}
    watch(c)
    ck("watch: working -> nothing said", LATER == [] and c._smart_park_waiting is not None)
    for status, key in (("inside", "inside"), ("outside:2", "outside")):
        GAME["status"] = {"ok": True, "reason": status}
        c._smart_park_waiting = {"t": T.time(), "phase": "settle", "since": T.time()}; del LATER[:]
        watch(c)
        ck("watch: %s -> '%s' once" % (status, CS.SMART_PARK_LINES[key]), LATER == [CS.SMART_PARK_LINES[key]] and c._smart_park_waiting is None, LATER)
    GAME["status"] = {"ok": False, "reason": "parking_approach_out_of_range"}
    c._smart_park_waiting = {"t": T.time(), "phase": "settle", "since": T.time()}; del LATER[:]
    watch(c)
    ck("watch: the last metres failed -> 'ما قدرت صفها جوا المكان.'", LATER == [CS.SMART_PARK_LINES["failed"]], LATER)
    GAME["status"] = {"ok": True, "reason": "working"}
    c._smart_park_waiting = {"t": T.time(), "phase": "settle", "since": T.time() - 61}; del LATER[:]
    watch(c)
    ck("watch: still working after %d s -> failed, said once" % CS.SMART_PARK_SETTLE_S, LATER == [CS.SMART_PARK_LINES["failed"]] and c._smart_park_waiting is None, LATER)
    GAME["settle"] = {"ok": False, "reason": "parking_requires_arrived_drive"}
    GS["v"] = {"result": "arrived", "reason": "arrived"}
    c._smart_park_waiting = {"t": T.time(), "phase": "drive"}; del LATER[:]
    watch(c)
    ck("watch: arrived but LF refuses the last metres -> 'near_only' line", LATER == [CS.SMART_PARK_LINES["near_only"]] and c._smart_park_waiting is None, LATER)
    GS["v"] = {"result": "failed", "reason": "no_way_round"}
    c._smart_park_waiting = {"t": T.time(), "phase": "drive"}; del LATER[:]
    watch(c)
    ck("watch: the drive failed -> its reason", LATER == [CS.drive_reply({"ok": False, "reason": "no_way_round"})], LATER)
    c._smart_park_waiting = {"t": T.time() - 700, "phase": "drive"}; del LATER[:]
    GS["v"] = {"result": "driving"}
    watch(c)
    ck("watch: after %d s the Mind stops asking" % CS.SMART_PARK_DRIVE_S, c._smart_park_waiting is None and LATER == [])

    # his real words reach the park decision (the model routes "park" with the phrase; "said" is what he wrote)
    CS._pre_intents_s86 = lambda self, h, s, m: ["ran"]
    c = chat()
    r = CS.Chat._pre_intents(c, [{"role": "user", "text": "صفي السيارة", "said": "صفيها بالكراج"}], {}, None)
    ck("pre_intents: his own words kept for the park decision", r == ["ran"] and c._park_said_s87 == "صفيها بالكراج", getattr(c, "_park_said_s87", None))
    lines = list(CS.SMART_PARK_LINES.values())
    ck("lines: nothing technical (no latin, no digits, no meta words)", all(not re.search(r"[A-Za-z0-9_]|لاعب", l) for l in lines), lines)
    return FAIL


if len(sys.argv) > 2 and sys.argv[1] == "--mind-child":
    mind_child(sys.argv[2])
    sys.exit(1 if FAIL else 0)

from kahlua_env import lua51
SRC = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind"))
LAB_CL = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client"))
LAB_LUA = os.path.abspath(os.path.join(HERE, "..", "profile", "Zomboid", "Lua"))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
GATE = os.path.join(ROOT, "05_TOOLS", "sol_kahlua", "tonumber_check.py")
CARD_CHECK = os.path.join(ROOT, "05_TOOLS", "sol_kahlua", "card_check.py")
EVAL = os.path.join(HERE, "test_s82_route_eval.py")
def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, script)] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
def digest(d, names): return {n: hashlib.md5(open(os.path.join(d, n), "rb").read()).hexdigest() for n in names if os.path.exists(os.path.join(d, n))}
def read(p): return open(p, encoding="utf-8", newline="").read()
TMP = tempfile.mkdtemp(prefix="sol_s87_")
ENVP = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")

# ================================================================ 1. the Lua installer on copies
ZB = os.path.join(TMP, "Zomboid")
CL = os.path.join(ZB, "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(CL)
os.makedirs(os.path.join(ZB, "Lua"))
FIXF = os.path.join(ZB, "Lua", "SolFixes_LAB.txt")
open(FIXF, "w", encoding="utf-8", newline="").write("retry_reset=on\r\nmove_check=off\r\n")
LFILES = ["SolAuthority.lua", "SCNavigation.lua"]
NEW = ["SolSmartPark.lua", "SolMoveCheck.lua"]
for f in LFILES: shutil.copy(os.path.join(LAB_CL, f), CL)
live_l = digest(LAB_CL, LFILES + NEW)
q1 = run("apply_s87_lua.py", CL); a1 = digest(CL, LFILES + NEW); f1 = read(FIXF)
q2 = run("apply_s87_lua.py", CL); a2 = digest(CL, LFILES + NEW); f2 = read(FIXF)
ck("lua installer: applies", q1.returncode == 0 and "applied" in q1.stdout, (q1.stdout + q1.stderr)[-500:])
ck("lua installer: idempotent (files and switch file)", q2.returncode == 0 and a1 == a2 and f1 == f2, q2.stdout[-300:])
auth = read(os.path.join(CL, "SolAuthority.lua"))
ck("lua installer: smart_park and move_check in A.FIXES once each", auth.count('"smart_park"') == 1 and auth.count('"move_check"') == 1)
ck("lua installer: smart_park=on added; his move_check=off kept", f1 == "retry_reset=on\r\nmove_check=off\r\nsmart_park=on\r\n", repr(f1))
ck("lua installer: SCNavigation.lua untouched", digest(CL, ["SCNavigation.lua"]) == digest(LAB_CL, ["SCNavigation.lua"]))
ck("lua installer: the installed files are untouched", digest(LAB_CL, LFILES + NEW) == live_l)
q = run("apply_s87_lua.py", os.path.join(TMP, "nowhere"))
ck("lua installer: refuses a folder that is not a Sol client", q.returncode != 0)
SP, MC = read(os.path.join(CL, "SolSmartPark.lua")), read(os.path.join(CL, "SolMoveCheck.lua"))
for n, body in (("SolSmartPark.lua", SP), ("SolMoveCheck.lua", MC)):
    ck("lua: %s is pure ASCII" % n, all(ord(ch) < 128 for ch in body))
    g = subprocess.run([sys.executable, GATE, os.path.join(CL, n)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    ck("lua: %s tonumber gate passes" % n, g.returncode == 0, (g.stdout + g.stderr)[-400:])
    e = lua51.LuaRuntime().eval("function(s) local f, e = loadstring(s); return e end")(body)
    ck("lua: %s compiles" % n, e is None, e)
    ck("lua: %s names no vehicle or place" % n, not re.search(r"(?i)bradley|ki5|muldraugh|riverside|westpoint|rosewood|louisville|march ridge", body))
SR = read(os.path.join(LAB_CL, "SolStaticRoads.lua"))
ck("lua: SolStaticRoads' grid is what SolSmartPark reads (CELL 64, key cx * 4096 + cy)",
   re.search(r"\bCELL\b[^\n]*=[^\n]*\b64\b", SR) is not None and "return cx * 4096 + cy" in SR and "M.ROAD_CELL, M.ROAD_KEY = 64, 4096" in SP)
ck("lua: SolStaticRoads.load hands back NX/NY/EA/EB/EW/GRID", all(k in SR for k in ("G = { NX = NX, NY = NY, EA = EA, EB = EB, EW = EW", "GRID = GRID")))

# ================================================================ 2. SolSmartPark under the game's Lua rules, a mocked world
PARK_ENV = r"""
print = function(m) LOGS[#LOGS + 1] = tostring(m) end
LOGS = {}
require = function() end
NOW, SWITCH = 1000000, true
function getTimestampMs() return NOW end
SolAuthority = { on = function(f) return f == "smart_park" and SWITCH end }
Events = { OnGameStart = { Add = function(f) START = f end } }
SQ = {}
local function list(t) return { size = function() return #t end, get = function(self, i) return t[i + 1] end } end
function square(x, y)
    local s = { objs = {}, solid = false, room = nil }
    s.isSolid = function(self) return self.solid end
    s.isSolidTrans = function(self) return false end
    s.getRoom = function(self) return self.room end
    s.getObjects = function(self) return list(self.objs) end
    SQ[x .. "," .. y] = s
    return s
end
function load(x0, y0, x1, y1) for x = x0, x1 do for y = y0, y1 do square(x, y) end end end
CELL = { getGridSquare = function(self, x, y, z) if z ~= 0 then return nil end return SQ[x .. "," .. y] end }
function getCell() return CELL end
function instanceof(o, cls) return type(o) == "table" and o.cls == cls end
ZONES = {}
function zone(name, x, y, w, h)
    local z = { getName = function() return name end, getType = function() return "ParkingStall" end,
        getX = function() return x end, getY = function() return y end, getWidth = function() return w end, getHeight = function() return h end }
    ZONES[#ZONES + 1] = { x = x, y = y, w = w, h = h, obj = z }
end
function getVehicleZoneAt(x, y, z)
    for _, zn in ipairs(ZONES) do if x >= zn.x and x < zn.x + zn.w and y >= zn.y and y < zn.y + zn.h then return zn.obj end end
    return nil
end
function car(x, y, long, wide, fx, fy)
    local c = { x = x, y = y, fx = fx or 0, fy = fy or 1 }
    local ext = { z = function() return long end, x = function() return wide end }
    local script = { getExtents = function() return ext end }
    c.getX = function(self) return self.x end
    c.getY = function(self) return self.y end
    c.getScript = function() return script end
    c.getForwardDirectionX = function(self) return self.fx end
    c.getForwardDirectionY = function(self) return self.fy end
    return c
end
CARS = {}
SOL = { getVehicle = function(self) return self.car end, getX = function() return 100 end, getY = function() return 100 end }
JOB = { result = "driving" }
APPROACH = {}
SurvivorCompanion = {
    Vehicle = { loadedVehicles = function() return CARS end },
    Driving = { approach = function(a, t, s) APPROACH[#APPROACH + 1] = t; return APPROACH_OK, APPROACH_WHY end,
                jobStatus = function(a) return JOB end },
}
APPROACH_OK = true
SolUI = { solActor = function() return SOL end, runAction = function(id, o) return true, "base:" .. tostring(id) end }
ROADG = nil
function road(ax, ay, bx, by, width)
    ROADG = ROADG or { NX = {}, NY = {}, EA = {}, EB = {}, EW = {}, GRID = {} }
    local n = #ROADG.NX
    ROADG.NX[n + 1], ROADG.NY[n + 1], ROADG.NX[n + 2], ROADG.NY[n + 2] = ax, ay, bx, by
    local e = #ROADG.EA + 1
    ROADG.EA[e], ROADG.EB[e], ROADG.EW[e] = n + 1, n + 2, width
    for cx = math.floor(math.min(ax, bx) / 64), math.floor(math.max(ax, bx) / 64) do
        for cy = math.floor(math.min(ay, by) / 64), math.floor(math.max(ay, by) / 64) do
            local k = cx * 4096 + cy
            ROADG.GRID[k] = ROADG.GRID[k] or {}
            table.insert(ROADG.GRID[k], e)
        end
    end
end
SolStaticRoads = { load = function() return ROADG end }
function run(id, o) return SolUI.runAction(id, o) end
"""
def park_world(setup):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(PARK_ENV); L.execute(setup); L.execute(SP); L.execute("START()")
    return L, L.globals()
R = lambda g, i, o=None: tuple(g.run(i, o))
SEDAN = "SOL.car = car(100.5, 100.5, 4.6, 1.9); CARS = { SOL.car }; load(60, 60, 145, 145)"

L, g = park_world(SEDAN)
B = g.SolSmartPark
def bays(*a): return [(b.x1, b.y1, b.x2, b.y2) for b in B.baysOf(*a).values()]
ck("bays: a 3x5 stall holds a sedan lengthwise (one bay)", bays(10, 20, 3, 5, 4.6, 1.9, "stall") == [(10, 20, 12, 24)], bays(10, 20, 3, 5, 4.6, 1.9, "stall"))
ck("bays: a 5x3 stall the other way", bays(10, 20, 5, 3, 4.6, 1.9, "stall") == [(10, 20, 14, 22)])
ck("bays: a 5x18 row -> 6 bays 5 long, 3 wide, cars across the row", bays(10, 20, 5, 18, 4.6, 1.9, "stall") == [(10, 20 + 3 * i, 14, 22 + 3 * i) for i in range(6)], bays(10, 20, 5, 18, 4.6, 1.9, "stall"))
ck("bays: a 2x5 strip holds nothing", bays(10, 20, 2, 5, 4.6, 1.9, "stall") == [])
ck("bays: a long truck does not fit a 3x5 stall", bays(10, 20, 3, 5, 8.0, 2.6, "stall") == [])
ck("bays: a 9x12 lot holds a long truck, 4 bays", len(bays(130, 100, 9, 12, 8.0, 2.6, "stall")) == 4, bays(130, 100, 9, 12, 8.0, 2.6, "stall"))

L, g = park_world(SEDAN + "; zone('', 110, 100, 3, 5); zone('', 120, 100, 3, 5); CARS[2] = car(111.5, 102.5, 4.6, 1.9)")
r = R(g, "sol_smart_park", "find")
ck("find: the nearest stall has a car in it -> the next free one", r[0] is True and r[1].startswith("spot:121.5,102.5,120,100,122,104,stall,"), r)
ck("find: the choice is logged with what was looked at and why (taken=1)", any("[SolSmartPark] spot stall 120,100-122,104" in l and "taken=1" in l for l in L.eval("LOGS").values()), list(L.eval("LOGS").values()))
L, g = park_world(SEDAN + "; zone('', 110, 100, 3, 5); zone('', 120, 100, 3, 5); SQ['113,101'].objs = { { cls = 'IsoDoor' } }")
r = R(g, "sol_smart_park", "find")
ck("find: a door next to the nearest stall -> the next one", r[0] is True and ",120,100,122,104,stall," in r[1], r)
L, g = park_world(SEDAN + "; zone('', 110, 100, 3, 5); zone('', 120, 100, 3, 5); SQ['111,103'].objs = { { cls = 'IsoThumpable', isDoor = function() return true end } }")
r = R(g, "sol_smart_park", "find")
ck("find: a built door on the stall -> the next one", r[0] is True and ",120,100,122,104,stall," in r[1], r)
L, g = park_world(SEDAN + "; zone('', 110, 100, 3, 5); zone('', 120, 100, 3, 5); SQ['110,104'].solid = true")
r = R(g, "sol_smart_park", "find")
ck("find: something solid in the nearest stall -> the next one", r[0] is True and ",120,100,122,104,stall," in r[1], r)
L, g = park_world(SEDAN + "; zone('trafficjamn', 103, 90, 3, 25); zone('', 120, 100, 3, 5)")
r = R(g, "sol_smart_park", "find")
ck("find: a traffic-jam zone (on the road) is never a spot", r[0] is True and ",120,100,122,104,stall," in r[1], r)
L, g = park_world(SEDAN + "; zone('', 110, 100, 3, 5); SQ['111,102'].room = {}")
r = R(g, "sol_smart_park", "find")
ck("find: a stall inside a building is no spot; no road map -> no open ground either -> no_spot", r == (False, "no_spot"), r)
L, g = park_world(SEDAN + "; zone('', 150, 100, 3, 5)")
r = R(g, "sol_smart_park", "find")
ck("find: a stall outside the loaded squares is skipped", r == (False, "no_spot"), r)
L, g = park_world(SEDAN + "; road(100, 0, 100, 200, 8)")
r = R(g, "sol_smart_park", "find")
m = re.match(r"spot:([\d.]+),([\d.]+),(\d+),(\d+),(\d+),(\d+),open,", r[1]) if r[0] else None
ck("find: no stall -> open ground, off the road (half width 4 + margin)", m is not None and (int(m.group(3)) >= 105 or int(m.group(5)) <= 94), r)
L, g = park_world(SEDAN + "; road(100, 0, 100, 200, 8); for y = 60, 145 do for x = 60, 145 do if x < 94 or x > 106 then SQ[x .. ',' .. y].solid = true end end end")
r = R(g, "sol_smart_park", "find")
ck("find: only road and solid ground around -> no_spot", r == (False, "no_spot"), r)
L, g = park_world("SOL.car = car(111.5, 102.5, 4.6, 1.9); CARS = { SOL.car }; load(60, 60, 145, 145); zone('', 110, 100, 3, 5); zone('', 120, 100, 3, 5)")
r = R(g, "sol_smart_park", "find")
ck("find: the car already stands inside a free stall -> already", r == (True, "already:110,100,112,104"), r)
L, g = park_world("SOL.car = car(100.5, 100.5, 8.0, 2.6); CARS = { SOL.car }; load(60, 60, 145, 145); zone('', 110, 100, 3, 5); zone('', 130, 100, 9, 12)")
r = R(g, "sol_smart_park", "find")
ck("find: a long truck skips the small stall for the lot it fits", r[0] is True and ",130,100,138,102,stall," in r[1], r)
L, g = park_world("load(60, 60, 145, 145); SOL.car = nil; CARS = {}")
ck("find: no car near her -> no_car", R(g, "sol_smart_park", "find") == (False, "no_car"))
L, g = park_world("load(60, 60, 145, 145); SOL.car = nil; CARS = { car(104.5, 100.5, 4.6, 1.9) }; zone('', 120, 100, 3, 5)")
r = R(g, "sol_smart_park", "find")
ck("find: on foot -> her car is the nearest one within 10 tiles", r[0] is True and ",120,100,122,104,stall," in r[1], r)

# settle and status
L, g = park_world(SEDAN + "; zone('', 120, 100, 3, 5)")
R(g, "sol_smart_park", "find")
r = R(g, "sol_smart_park", "settle")
ck("settle: LF's precise last metres to the middle of the spot", r == (True, "approaching") and g.APPROACH[1].x == 121.5 and g.APPROACH[1].y == 102.5 and g.APPROACH[1].z == 0, (r, dict(g.APPROACH[1]) if g.APPROACH[1] else None))
ck("status: LF still driving -> working", R(g, "sol_smart_park", "status") == (True, "working"))
L.execute("JOB = { result = 'arrived' }; SOL.car.x, SOL.car.y = 121.5, 102.5")
ck("status: arrived, the whole car inside -> inside", R(g, "sol_smart_park", "status") == (True, "inside"))
L, g = park_world(SEDAN + "; zone('', 120, 100, 3, 5)")
R(g, "sol_smart_park", "find"); R(g, "sol_smart_park", "settle")
L.execute("JOB = { result = 'arrived' }; SOL.car.x, SOL.car.y, SOL.car.fx, SOL.car.fy = 121.5, 102.5, 1, 0")
ck("status: arrived crosswise -> outside:4 (said, not hidden)", R(g, "sol_smart_park", "status") == (True, "outside:4"))
L, g = park_world(SEDAN + "; zone('', 120, 100, 3, 5)")
R(g, "sol_smart_park", "find"); R(g, "sol_smart_park", "settle")
L.execute("JOB = { result = 'failed', reason = 'parking_approach_blocked' }")
ck("status: LF failed -> its reason", R(g, "sol_smart_park", "status") == (False, "parking_approach_blocked"))
L, g = park_world(SEDAN + "; zone('', 120, 100, 3, 5); APPROACH_OK, APPROACH_WHY = false, 'parking_requires_arrived_drive'")
R(g, "sol_smart_park", "find")
ck("settle: LF refuses -> its reason", R(g, "sol_smart_park", "settle") == (False, "parking_requires_arrived_drive"))
L, g = park_world(SEDAN)
ck("settle before find -> no_spot", R(g, "sol_smart_park", "settle") == (False, "no_spot"))
ck("verbs: an unknown option -> unknown_option", R(g, "sol_smart_park", "fly") == (False, "unknown_option"))
ck("verbs: other actions go on unchanged", R(g, "sol_engine", "on") == (True, "base:sol_engine"))
L.execute("SWITCH = false")
ck("switch off: the verb answers fix_off, nothing else changes", R(g, "sol_smart_park", "find") == (False, "fix_off") and R(g, "sol_horn", "once") == (True, "base:sol_horn"))

# ================================================================ 3. SolMoveCheck under the game's Lua rules
MOVE_ENV = r"""
print = function(m) LOGS[#LOGS + 1] = tostring(m) end
LOGS = {}
require = function() end
NOW, SWITCH = 1000000, true
function getTimestampMs() return NOW end
SolAuthority = { on = function(f) return f == "move_check" and SWITCH end }
Events = { OnGameStart = { Add = function(f) START = f end } }
local function actor(x, y)
    local a = { x = x, y = y, z = 0, state = "" }
    a.getX = function(self) return self.x end
    a.getY = function(self) return self.y end
    a.getZ = function(self) return self.z end
    a.getActionStateName = function(self) return self.state end
    a.getVehicle = function(self) return nil end
    return a
end
SOL, PLAYER, OTHER = actor(0, 0), actor(50, 50), actor(10, 10)
function getSpecificPlayer(i) return PLAYER end
SolUI = { solActor = function() return SOL end }
NAV = { calls = {}, cancels = 0, phase = "moving" }
SurvivorCompanion = { Navigation = {
    request = function(a, t, m, i) NAV.calls[#NAV.calls + 1] = { a = a, m = m }; return true, "moving" end,
    cancel = function(a, why) NAV.cancels = NAV.cancels + 1; NAV.why = why; return true end,
    status = function(a) return { phase = NAV.phase } end } }
ORDER = { action = "ordered_move" }
function req(a, tx, ty, mode, intent, tz) return SurvivorCompanion.Navigation.request(a, { x = tx, y = ty, z = tz or 0 }, mode or "walk", intent or ORDER) end
function last() return NAV.calls[#NAV.calls] end
"""
def move_world(setup=""):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(MOVE_ENV); L.execute(setup); L.execute(MC); L.execute("START()")
    return L, L.globals()
L, g = move_world()
ck("move: wrapped at start", g.SolMoveCheck._wrapped is True and g.SurvivorCompanion.Navigation._solMoveCheck is True)
g.SolMoveCheck.wrap()
L.execute("req(SOL, 30, 0)")
ck("move: wrapping twice does not wrap twice (one call reaches LF)", len(g.NAV.calls) == 1)
L, g = move_world()
L.execute("req(OTHER, 40, 10, 'walk')")
ck("move: another actor -> LF's request, mode unchanged", L.eval("last().a == OTHER") is True and g.last().m == "walk")
L.execute("req(SOL, 40, 0, 'walk', { action = 'follow' })")
ck("move: not an order of his (follow) -> unchanged", g.last().m == "walk")
L.execute("req(SOL, 20, 0, 'walk')")
ck("move: 20 tiles to go -> jog", g.last().m == "jog")
L.execute("SOL.x = 13; req(SOL, 20, 0, 'walk')")
ck("move: 7 tiles to go after jogging -> still jog (no flapping)", g.last().m == "jog")
L.execute("SOL.x = 17; req(SOL, 20, 0, 'jog')")
ck("move: 3 tiles to go -> walk", g.last().m == "walk")
L.execute("SOL.x = 14; req(SOL, 20, 0, 'jog')")
ck("move: 6 tiles to go after walking -> still walk", g.last().m == "walk")
L.execute("SOL.x = 0; req(SOL, 30, 0, 'sneak')")
ck("move: a sneak order stays a sneak", g.last().m == "sneak")

# did not move
L, g = move_world()
def at(ms, x=None):
    L.execute("NOW = NOW + %d" % ms + ("; SOL.x = %s" % x if x is not None else "") + "; req(SOL, 30, 0, 'walk')")
at(0); at(300); at(310)
ck("stuck: 610 ms without moving -> one fresh path (LF's state dropped)", g.NAV.cancels == 1 and g.NAV.why == "sol_move_check", g.NAV.cancels)
ck("stuck: ... and the same request still goes to LF", len(g.NAV.calls) == 3)
at(300); at(300); at(300)
ck("stuck: 1.2 s pause between two fresh paths", g.NAV.cancels == 1, g.NAV.cancels)
at(400); at(700)
ck("stuck: after the pause a new 600 ms window -> the next fresh path", g.NAV.cancels == 2, g.NAV.cancels)
for _ in range(40): at(700)
ck("stuck: at most 8 fresh paths for one target, then LF's own recovery", g.NAV.cancels == 8, g.NAV.cancels)
ck("stuck: giving up is logged once", sum(1 for l in L.eval("LOGS").values() if "LF's own recovery" in l) == 1)
L, g = move_world()
x = 0.0
for _ in range(10):
    x += 0.3; at(650, x)
ck("moving: 0.3 tiles per window -> never a fresh path", g.NAV.cancels == 0, g.NAV.cancels)
L, g = move_world("NAV.phase = 'planning'")
for _ in range(6): at(700)
ck("quiet: while LF's path search runs -> no fresh path", g.NAV.cancels == 0)
L, g = move_world("SOL.state = 'climbfence'")
for _ in range(6): at(700)
ck("quiet: while she climbs a fence -> no fresh path", g.NAV.cancels == 0)
L.execute("SOL.state = ''")
for _ in range(3): at(700)
ck("quiet: climbing over, stuck again -> fresh path", g.NAV.cancels == 1, g.NAV.cancels)
L, g = move_world()
at(0); L.execute("NOW = NOW + 700; req(SOL, 31, 0, 'walk')")
ck("stuck: a new target starts a new count (no kick on the first sample)", g.NAV.cancels == 0)

# to him: 1.5 tiles
L, g = move_world("SOL.x, SOL.y = 51.2, 50.5")
r = tuple(L.eval("{ req(SOL, 51, 50, 'walk') }").values())
ck("near him: target by him, she 1.3 tiles from him -> arrived, LF not asked, her motion stopped", r == (True, "arrived") and len(g.NAV.calls) == 0 and g.NAV.cancels == 1, (r, len(g.NAV.calls), g.NAV.cancels))
L, g = move_world("SOL.x, SOL.y = 53, 50")
L.execute("req(SOL, 51, 50, 'walk')")
ck("near him: 3 tiles away -> she keeps walking", len(g.NAV.calls) == 1 and g.NAV.cancels == 0)
L, g = move_world("SOL.x, SOL.y = 51.2, 50.5; SOL.z = 1")
L.execute("req(SOL, 51, 50, 'walk', nil, 1)")
ck("near him: another floor -> she keeps walking", len(g.NAV.calls) == 1)
L, g = move_world("SOL.x, SOL.y = 51.2, 50.5")
L.execute("req(SOL, 60, 50, 'walk')")
ck("near him: passing by him on the way elsewhere -> she keeps walking", len(g.NAV.calls) == 1 and g.NAV.cancels == 0)
L, g = move_world("SWITCH = false; SOL.x, SOL.y = 51.2, 50.5")
L.execute("req(SOL, 51, 50, 'walk'); NOW = NOW + 5000; req(SOL, 51, 50, 'walk'); req(SOL, 90, 50, 'walk')")
ck("switch off: LF's own request, untouched (mode, no stop, no fresh path)", len(g.NAV.calls) == 3 and g.NAV.cancels == 0 and g.last().m == "walk")
L, g = move_world("SOL.x, SOL.y = 0, 0")
L.execute("SurvivorCompanion.Navigation.request(SOL, { getX = function() return 30 end, getY = function() return 0 end, getZ = function() return 0 end }, 'walk', ORDER)")
ck("move: a square target (getX/getY) works like a table", g.last().m == "jog")

# ================================================================ 4. the Mind installer on copies
MFILES = ["model_router.py", "chat_service.py"]
live_m = digest(SRC, MFILES)
M = os.path.join(TMP, "mind"); os.makedirs(M)
for f in os.listdir(SRC):
    if f.endswith((".py", ".json.gz")): shutil.copy(os.path.join(SRC, f), M)
q1 = run("apply_s87_mind.py", M); m1 = digest(M, MFILES)
q2 = run("apply_s87_mind.py", M); m2 = digest(M, MFILES)
ck("mind installer: applies", q1.returncode == 0 and "applied" in q1.stdout, (q1.stdout + q1.stderr)[-600:])
ck("mind installer: idempotent", q2.returncode == 0 and m1 == m2 and q2.stdout.count("kept") == 2, q2.stdout)
for n in MFILES:
    ck("mind installer: line endings kept in %s" % n, (b"\r\n" in open(os.path.join(SRC, n), "rb").read()) == (b"\r\n" in open(os.path.join(M, n), "rb").read()))
imp = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import chat_service, model_router, memory_answers", M], capture_output=True, text=True, env=ENVP)
ck("mind: imports", imp.returncode == 0, imp.stderr[-600:])
NO85 = os.path.join(TMP, "no85"); os.makedirs(NO85)
for n in MFILES: open(os.path.join(NO85, n), "w", encoding="utf-8").write("x = 1\n")
q = run("apply_s87_mind.py", NO85)
ck("mind installer: refuses a Mind without s85", q.returncode != 0 and "s85 is not installed" in q.stderr, q.stderr[-200:])

# ---- 5. the card: card_check's own numbers on the patched copy (doc section written to a temp copy), route eval as-is
DOC = os.path.join(TMP, "SOL_MODEL_CARD.md")
shutil.copy(os.path.join(ROOT, "DOCS", "SOL_MODEL_CARD.md"), DOC)
subprocess.run([sys.executable, CARD_CHECK, M, "--lua", LAB_CL, "--lua-profile", LAB_LUA, "--doc", DOC, "--write-doc", "--no-eval"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
cc = subprocess.run([sys.executable, CARD_CHECK, M, "--lua", LAB_CL, "--lua-profile", LAB_LUA, "--doc", DOC], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
tail = cc.stdout.strip().splitlines()[-1] if cc.stdout.strip() else cc.stderr[-300:]
print("card_check:", tail)
size = re.search(r"card (\d+)/(\d+) chars", tail)
ck("card_check: PASS on the patched Mind (route eval included)", cc.returncode == 0 and "CARD_CHECK: PASS" in tail, [l for l in cc.stdout.splitlines() if l.startswith("FAIL")] or tail)
ck("card_check: within the budget", size is not None and int(size.group(1)) <= int(size.group(2)), tail)
ev = subprocess.run([sys.executable, EVAL, "--as-is", M], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
ck("test_s82_route_eval.py --as-is passes on the patched Mind", ev.returncode == 0 and "ALL PASS" in ev.stdout, ev.stdout[-600:] + ev.stderr[-300:])

# ---- 6. the chat, mocked
c = subprocess.run([sys.executable, os.path.abspath(__file__), "--mind-child", M], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
for l in c.stdout.strip().splitlines(): print("  [mind] " + l)
ck("mind: the chat checks pass", c.returncode == 0 and not any(l.startswith("FAIL") for l in c.stdout.splitlines()), c.stderr[-1200:])
ck("mind installer: the live Mind is untouched", digest(SRC, MFILES) == live_m)

shutil.rmtree(TMP, ignore_errors=True)
print("\n%d FAIL" % len(FAIL) if FAIL else "\nALL PASS")
sys.exit(1 if FAIL else 0)

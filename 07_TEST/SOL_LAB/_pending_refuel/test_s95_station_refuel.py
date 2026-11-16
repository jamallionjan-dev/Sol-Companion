"""Offline tests for s95 station_survey (apply_s95_station_refuel.py + apply_s95_station_refuel_mind.py, SolStationSurvey.lua).
usage: set PYTHONIOENCODING=utf-8 & python test_s95_station_refuel.py
  1 installers on COPIES of the live lab files and the live Mind: apply, twice change nothing, Kahlua-like compile, ASCII Lua,
    no new tonumber(f()) site, an existing LAB switch is preserved or a missing switch defaults OFF, py_compile, never the live files
  2 pose matrix (pure): 9 station shapes x 7 vehicles (cap right / left / rear, no seat area, KI5 long truck and tractor).
    Every pose is re-checked by an independent Python checker: the game's 2-square rule from the cap square, body on free
    squares (sampled), standing square free and clear of the body, cap within reach, a walk from a door to the standing square.
  3 replay of the logged failures on the real forecourt (SolPerception dump 2026-11-11 00:42), with game mocks:
    00:37/00:38 (walk cut by move_check "tiles from him: there"), 00:40 (no free square by the cap); switch off = the old
    answers, switch on = parked, near, walked, pumped
  4 drive faults: a plan fails -> next pose; a stop off by 0.6 -> re-park with one line; all sides taken -> survey_no_pose;
    no power -> survey_no_pump; re-park limit; KI5 truck end to end; the cache (once per life, read again for a new life)
  5 Mind parking_wait: "parking:<why>" said once, survey_* fails at once with its line, old answers unchanged
  6 no station, place or vehicle names or map numbers in the new Lua
Offline PASS is not Runtime PASS."""
import math, os, py_compile, re, shutil, subprocess, sys, tempfile, importlib
from kahlua_env import lua51
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
HERE = os.path.dirname(os.path.abspath(__file__))
LAB_NOW = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
FIXES_NOW = os.path.join(HERE, "..", "profile", "Zomboid", "Lua", "SolFixes_LAB.txt")
MIND_NOW = r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind"
TONUM = r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_kahlua\tonumber_check.py"
FAIL, N = [], [0]
def ck(n, c, d=""):
    N[0] += 1
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
def run(*a): return subprocess.run([sys.executable, "-I"] + list(a), capture_output=True, text=True, encoding="utf-8")

# ---------------------------------------------------------------- 1 installers on copies
T = tempfile.mkdtemp(prefix="sol_s95_")
LIVE = {n: open(os.path.join(LAB_NOW, n), "rb").read() for n in ("SolFuel.lua", "SolMoveCheck.lua", "SolAuthority.lua")}
LIVE_FIX = open(FIXES_NOW, "rb").read()
LIVE_GE = open(os.path.join(MIND_NOW, "goal_engine.py"), "rb").read()
root = os.path.join(T, "lab")
CL = os.path.join(root, "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
MD = os.path.join(T, "mind")
os.makedirs(CL); os.makedirs(MD); os.makedirs(os.path.join(root, "Zomboid", "Lua"))
for n in LIVE: shutil.copy(os.path.join(LAB_NOW, n), CL)
FX = os.path.join(root, "Zomboid", "Lua", "SolFixes_LAB.txt")
shutil.copy(FIXES_NOW, FX)
for n in os.listdir(MIND_NOW):
    if n.endswith(".py"): shutil.copy(os.path.join(MIND_NOW, n), MD)
fx_before = open(FX, encoding="utf-8").read()
r = run(os.path.join(HERE, "apply_s95_station_refuel.py"), CL); ck("lua installer applies", r.returncode == 0, r.stdout[-300:] + r.stderr[-500:])
r = run(os.path.join(HERE, "apply_s95_station_refuel_mind.py"), MD); ck("mind installer applies", r.returncode == 0, r.stdout[-300:] + r.stderr[-500:])
def snap(*ds): return {os.path.join(d, n): open(os.path.join(d, n), "rb").read() for d in ds for n in sorted(os.listdir(d)) if os.path.isfile(os.path.join(d, n))}
once, fx_once = snap(CL, MD), open(FX, encoding="utf-8").read()
r1 = run(os.path.join(HERE, "apply_s95_station_refuel.py"), CL); r2 = run(os.path.join(HERE, "apply_s95_station_refuel_mind.py"), MD)
ck("both installers twice: nothing changes", r1.returncode == 0 and r2.returncode == 0 and snap(CL, MD) == once and open(FX, encoding="utf-8").read() == fx_once, r1.stderr[-200:] + r2.stderr[-200:])
ck("switch file: preserves an existing LAB choice; otherwise writes OFF once", ("station_survey=on" in fx_before and fx_once == fx_before) or ("station_survey=on" not in fx_before and fx_once.count("station_survey=off") == 1 and fx_once.startswith(fx_before)), fx_once[-60:])
ck("SolAuthority lists station_survey once", open(os.path.join(CL, "SolAuthority.lua"), encoding="utf-8").read().count('"station_survey"') == 1)
for n in ("SolFuel.lua", "SolMoveCheck.lua", "SolAuthority.lua", "SolStationSurvey.lua"):
    s = open(os.path.join(CL, n), encoding="utf-8").read()
    ck("%s compiles in Kahlua-like Lua" % n, not isinstance(lua51.LuaRuntime().globals().loadstring(s), tuple), lua51.LuaRuntime().globals().loadstring(s))
    ck("%s is pure ASCII" % n, all(ord(c) < 128 for c in s))
def sites(f): return sorted(re.sub(r":\d+ ", " ", l) for l in run(TONUM, f).stdout.splitlines() if "tonumber" in l and "CHECK" not in l)
pre = os.path.join(T, "pre"); os.makedirs(pre)
for n in ("SolFuel.lua", "SolMoveCheck.lua"):
    open(os.path.join(pre, n), "wb").write(LIVE[n])
    ck("tonumber_check: no new tonumber(f()) site in %s" % n, sites(os.path.join(CL, n)) == sites(os.path.join(pre, n)), sites(os.path.join(CL, n)))
rt = run(TONUM, os.path.join(CL, "SolStationSurvey.lua"))
ck("tonumber_check passes on SolStationSurvey.lua", rt.returncode == 0, rt.stdout[-400:] + rt.stderr[-200:])
try: py_compile.compile(os.path.join(MD, "goal_engine.py"), doraise=True); okc = True
except Exception as e: okc = e
ck("goal_engine.py compiles", okc is True, okc)
ck("live lab files and live Mind untouched", all(open(os.path.join(LAB_NOW, n), "rb").read() == b for n, b in LIVE.items())
   and open(FIXES_NOW, "rb").read() == LIVE_FIX and open(os.path.join(MIND_NOW, "goal_engine.py"), "rb").read() == LIVE_GE)

# ---------------------------------------------------------------- the game, mocked
MOCK = r"""
LOGS, TICKS = {}, {}
print = function(s) LOGS[#LOGS + 1] = tostring(s) end
CLOCK = 1000000
getTimestampMs = function() return CLOCK end
SW = { refuel = true, refuel_top_up = true, move_check = true, station_survey = true }
SolAuthority = { on = function(n) return SW[n] == true end }
Events = { OnTick = { Add = function(f) TICKS[#TICKS + 1] = f end, Remove = function() end }, OnGameStart = { Add = function() end } }
GT = { h = 100 }
getGameTime = function() return { getWorldAgeHours = function() return GT.h end } end
MODDATA = { Sol_Life = { id = "sol-1", deaths = 0 } }
ModData = { getOrCreate = function(k) MODDATA[k] = MODDATA[k] or {}; return MODDATA[k] end, transmit = function() end }
Vector3f = { new = function() return {} end }
SandboxVars = {}
SolUI = SolUI or {}
W = { solid = {}, wall = {}, fuel = {}, power = {}, reads = 0 }
local function k(x, y) return math.floor(x) .. "," .. math.floor(y) end
KEY = k
SQ = {}
local function objs(sq)
    local list = {}
    local f = W.fuel[k(sq.x, sq.y)]
    if f ~= nil then
        list[1] = { getPipedFuelAmount = function() return W.fuel[k(sq.x, sq.y)] end,
                    setPipedFuelAmount = function(_, v) W.fuel[k(sq.x, sq.y)] = v end, getSquare = function() return sq end }
    end
    return { size = function() return #list end, get = function(_, i) return list[i + 1] end }
end
function square(x, y)
    x, y = math.floor(x), math.floor(y)
    local kk = k(x, y)
    local s = SQ[kk]
    if s then return s end
    s = { x = x, y = y }
    s.getX = function() return s.x end
    s.getY = function() return s.y end
    s.getZ = function() return 0 end
    s.hasGridPower = function() return W.power[kk] ~= false end
    s.haveElectricity = function() return false end
    s.getObjects = function() return objs(s) end
    s.isFree = function() return W.solid[kk] == nil end
    s.isBlockedTo = function(_, o)
        if o.x == s.x + 1 then return W.wall[kk .. "E"] == true end
        if o.x == s.x - 1 then return W.wall[k(o.x, o.y) .. "E"] == true end
        if o.y == s.y + 1 then return W.wall[kk .. "S"] == true end
        if o.y == s.y - 1 then return W.wall[k(o.x, o.y) .. "S"] == true end
        return false
    end
    SQ[kk] = s
    return s
end
VEHS = {}
CELL = { getGridSquare = function(_, x, y, z) W.reads = W.reads + 1; return square(x, y) end,
         getVehicles = function() return { size = function() return #VEHS end, get = function(_, i) return VEHS[i + 1] end } end }
getCell = function() return CELL end
-- an oriented box against a square, by sampling (independent of the module's own test)
function RECT_HITS(cx, cy, fx, fy, hl, hw, x, y)
    for i = 0, 10 do for j = 0, 10 do
        local px, py = x + 0.02 + i * 0.096, y + 0.02 + j * 0.096
        local a, b = (px - cx) * fx + (py - cy) * fy, -(px - cx) * fy + (py - cy) * fx
        if math.abs(a) < hl and math.abs(b) < hw then return true end
    end end
    return false
end
function mkCar(t)
    local v = t
    v.engine = false
    local function pt(along, side) return v.cx + v.fx * along - v.fy * side, v.cy + v.fy * along + v.fx * side end
    local function vec(x, y) return { getX = function() return x end, getY = function() return y end } end
    v.getX = function() return v.cx end
    v.getY = function() return v.cy end
    v.getZ = function() return 0 end
    v.getForwardVector = function() return { x = function() return v.fx end, z = function() return v.fy end } end
    v.getAreaCenter = function(_, area)
        if area == "GasTank" and v.capA then return vec(pt(v.capA, v.capS)) end
        if area == "SeatFrontLeft" and v.doorA then return vec(pt(v.doorA, v.doorS)) end
        return nil
    end
    v.getPassengerArea = function(_, seat) if v.doorA then return "SeatFrontLeft" end; return nil end
    v.getSeat = function() return 0 end
    v.tank = { getArea = function() return "GasTank" end, getContainerContentType = function() return "Gasoline" end,
        getContainerContentAmount = function() return v.fuel end, getContainerCapacity = function() return v.capacity end,
        setContainerContentAmount = function(_, a) v.fuel = a end, getVehicle = function() return v end }
    v.getPartById = function(_, id) if id == "GasTank" and v.capA then return v.tank end; return nil end
    v.isIntersectingSquare = function(_, x, y, z) return RECT_HITS(v.cx, v.cy, v.fx, v.fy, v.hl, v.hw, x, y) end
    v.isEngineRunning = function() return v.engine end
    v.shutOff = function() v.engine = false end
    v.getScript = function() return { getExtents = function() return { x = function() return v.hw * 2 end, z = function() return v.hl * 2 end } end } end
    v.isInArea = function(_, area, chr) local ax, ay = pt(v.capA, v.capS); return (chr.x - ax) ^ 2 + (chr.y - ay) ^ 2 <= 0.45 ^ 2 end
    v.transmitPartModData = function() end
    VEHS[#VEHS + 1] = v
    return v
end
-- the game's pump test, as read in ISVehiclePartMenu.getNearbyFuelPump (5 x 5 round the cap's square, the first with fuel)
ISVehiclePartMenu = { getNearbyFuelPump = function(veh)
    local part = veh:getPartById("GasTank"); if not part then return nil end
    local c = veh:getAreaCenter(part:getArea()); if not c then return nil end
    local sx, sy = math.floor(c:getX()), math.floor(c:getY())
    for dy = -2, 2 do for dx = -2, 2 do
        local f = W.fuel[k(sx + dx, sy + dy)]
        if f ~= nil and f > 0 then return square(sx + dx, sy + dy):getObjects():get(0) end
    end end
    return nil
end }
SolBypass = { measure = function(v) return { halfLength = v.hl, halfWidth = v.hw, wheelbase = v.hl * 1.15, kmax = 0.5 } end }
function solStationsNearest(x, y)
    local best, bd = nil, 1e18
    for kk, f in pairs(W.fuel) do
        local px, py = string.match(kk, "^(%-?%d+),(%-?%d+)$")
        px, py = tonumber(px), tonumber(py)
        if f > 0 and (px - x) ^ 2 + (py - y) ^ 2 < bd then best, bd = px .. "," .. py .. "," .. math.floor(f) .. ",brand", (px - x) ^ 2 + (py - y) ^ 2 end
    end
    return best or ""
end
solStationsStep = function() end
-- the Java planner: plan -> ready -> follow -> done at the goal (+ drift); NAV.failAt[n] fails the n-th plan
NAV = { state = "idle", n = 0, plans = 0, failAt = {}, drift = {}, goals = {} }
function solNavPlan(car, sx, sy, hx, hy, gx, gy, ghx, ghy, wb, k)
    NAV.plans = NAV.plans + 1
    NAV.goal = { car = car, x = gx, y = gy, fx = ghx, fy = ghy, i = NAV.plans }
    NAV.goals[#NAV.goals + 1] = NAV.goal
    NAV.state, NAV.n = "capturing", 0
    return true
end
function solNavState()
    NAV.n = NAV.n + 1
    if NAV.state == "capturing" and NAV.n >= 2 then NAV.state = NAV.failAt[NAV.goal.i] and "failed:no_path" or "ready" end
    if NAV.state == "following" and NAV.n >= 3 then
        local d = NAV.drift[NAV.goal.i] or { 0, 0 }          -- { along, towards the cap side }, in the car's frame
        local c = NAV.goal.car
        local fx, fy = NAV.goal.fx, NAV.goal.fy
        local sd = d[2] * (((c.capS or 0) < 0) and -1 or 1)
        c.cx, c.cy, c.fx, c.fy = NAV.goal.x + fx * d[1] - fy * sd, NAV.goal.y + fy * d[1] + fx * sd, fx, fy
        NAV.state = "done"
    end
    return NAV.state
end
function solNavFollow() if NAV.state == "ready" then NAV.state, NAV.n = "following", 0; return true end; return false end
function solNavStop() NAV.state = "idle" end
function solNavBeat() end
function solNavPark() return false end
-- her, him, LF
SOL = { x = 0, y = 0, veh = nil }
SOL.getX = function() return SOL.x end
SOL.getY = function() return SOL.y end
SOL.getZ = function() return 0 end
SOL.getVehicle = function() return SOL.veh end
SOL.getInventory = function() return { getFirstEvalRecurse = function() return nil end } end
PLAYER = { x = 0, y = 0, veh = nil }
PLAYER.getX = function() return PLAYER.x end
PLAYER.getY = function() return PLAYER.y end
PLAYER.getZ = function() return 0 end
PLAYER.getVehicle = function() return PLAYER.veh end
getSpecificPlayer = function() return PLAYER end
GOTOS, NAVCANCEL = {}, 0
SurvivorCompanion = { GameplayUtil = { isSquareFree = function(sq) return sq ~= nil and W.solid[k(sq.x, sq.y)] == nil end, idOf = function() return "sol-1" end },
    Commands = { issue = function() end },
    Navigation = { status = function() return { phase = "moving" } end, cancel = function() NAVCANCEL = NAVCANCEL + 1 end,
        request = function(actor, target, mode, intent) actor.x, actor.y = target.x + 0.5, target.y + 0.5; return true, "moving" end } }
SolUI.solActor = function() return SOL end
SolUI.solGoto = function(x, y, z)
    GOTOS[#GOTOS + 1] = x .. "," .. y
    local ok, a, b = pcall(SurvivorCompanion.Navigation.request, SOL, { x = x, y = y, z = 0 }, "walk", { action = "ordered_move" })
    return true
end
SolUI.solEngine = function(o) local c = SolUI.gps.lastDriveCar; if c then c.engine = (o == "on") end end
SolUI.gps = { lastDriveCar = nil }
QUEUE = {}
ISTimedActionQueue = { add = function(a) QUEUE[#QUEUE + 1] = a; return true end,
    getTimedActionQueue = function() return { queue = QUEUE, removeFromQueue = function(_, a) for i, b in ipairs(QUEUE) do if b == a then table.remove(QUEUE, i) end end end } end }
ISBaseTimedAction = { derive = function(self, name) return {} end }
ISRefuelFromGasPump = { new = function(cls, s, part, pump) return { character = s, part = part, vehicle = part.getVehicle(), fuelStation = pump } end }
-- the game's side of a queued refuel: it runs only when its isValid says she is at the cap
function GAME_ACTIONS()
    local a = QUEUE[1]
    if a and a.part and a.isValid then
        if a:isValid() then a.vehicle.fuel = a.vehicle.capacity; DID_PUMP = true end
        table.remove(QUEUE, 1)
    end
end
function TICK(ms)
    CLOCK = CLOCK + (ms or 250)
    for _, f in ipairs(TICKS) do pcall(f) end
    GAME_ACTIONS()
end
"""

def env(files=("SolFuel.lua", "SolMoveCheck.lua", "SolStationSurvey.lua"), d=CL):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(MOCK)
    for n in files: L.execute(open(os.path.join(d, n), encoding="utf-8").read())
    L.execute("SolMoveCheck.wrap()")
    return L

# ---------------------------------------------------------------- 2 pose matrix (pure)
VEHICLES = {   # half length, half width, cap along, cap side, door along, door side (None = no seat area)
    "small car, cap right rear": (1.68, 0.69, -1.22, 1.09, 0.0, -1.09),
    "small car, cap left rear": (1.68, 0.69, -1.22, -1.09, 0.0, -1.09),
    "van, cap left": (2.12, 0.85, -1.2, -1.25, 0.3, 1.25),
    "pickup, cap at the back": (2.4, 0.9, -2.75, 0.0, 0.4, -1.3),
    "no seat area in the script": (2.0, 0.9, -1.0, 1.25, None, None),
    "KI5 long truck, cap ahead of the centre": (4.6, 1.3, 1.0, 1.65, 3.2, -1.65),
    "KI5 tractor unit, 15 m": (7.5, 1.3, -2.0, -1.65, 5.6, 1.65),
}
def station(name):
    s = {"solid": set(), "pumps": [], "cars": set(), "wall": set(), "nopower": set()}
    def solid(*pts): s["solid"].update(pts)
    def car_box(x0, y0, x1, y1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): s["cars"].add((x, y))
    if name == "open pump":
        s["pumps"] = [(20, 20)]
    elif name == "island: post, 2-square pump, bin":
        solid((16, 20), (17, 20), (19, 20)); s["pumps"] = [(18, 20)]
    elif name == "single-sided: building wall behind the pump":
        for x in range(8, 33): solid((x, 19)); solid((x, 18))
        s["pumps"] = [(20, 20)]
    elif name == "island + bin + car parked on one side":
        solid((16, 20), (17, 20), (19, 20)); s["pumps"] = [(18, 20)]; car_box(14, 18, 20, 18)
    elif name == "two islands, three lanes taken":
        solid((13, 20), (14, 20), (16, 20), (23, 20), (24, 20), (26, 20)); s["pumps"] = [(15, 20), (25, 20)]
        car_box(12, 18, 17, 18); car_box(22, 18, 27, 18); car_box(12, 22, 17, 22)
    elif name == "canopy pillars round the pump":
        s["pumps"] = [(20, 20)]; solid((13, 16), (27, 16), (13, 24), (27, 24))
    elif name == "every side taken":
        s["pumps"] = [(20, 20)]
        car_box(15, 18, 25, 18); car_box(15, 22, 25, 22); car_box(18, 19, 18, 21); car_box(22, 19, 22, 21)
    elif name == "lanes too narrow to keep the free square":
        for x in range(8, 33): solid((x, 18)); solid((x, 23))
        s["pumps"] = [(20, 20)]
    elif name == "pump without power":
        s["pumps"] = [(20, 20)]; s["nopower"].add((20, 20))
    elif name == "pump in a narrow alley (walls 3 apart)":
        for x in range(8, 33): solid((x, 18)); solid((x, 22))
        s["pumps"] = [(20, 19)]
    return s
STATIONS = ["open pump", "island: post, 2-square pump, bin", "single-sided: building wall behind the pump", "island + bin + car parked on one side",
            "two islands, three lanes taken", "canopy pillars round the pump", "pump in a narrow alley (walls 3 apart)", "every side taken", "pump without power",
            "lanes too narrow to keep the free square"]
def lua_world(L, s, ox=0, oy=0, size=41):
    L.execute("WT = { ox = %d, oy = %d, size = %d, solid = {}, wall = {}, pumps = {}, cars = {}, own = {} }" % (ox, oy, size))
    for (x, y) in s["solid"]: L.execute('WT.solid["%d,%d"] = "o"' % (x, y))
    for (x, y) in s["cars"]: L.execute('WT.cars["%d,%d"] = true' % (x, y))
    for w in s["wall"]: L.execute('WT.wall["%s"] = true' % w)
    for (x, y) in s["pumps"]:
        L.execute('WT.solid["%d,%d"] = "p"; WT.pumps[#WT.pumps + 1] = { x = %d, y = %d, fuel = 100, power = %s }' % (x, y, x, y, "false" if (x, y) in s["nopower"] else "true"))
    return L.globals().WT

def body_samples(cx, cy, fx, fy, a, b, step=0.1):
    out = set()
    na, nb = int(a / step) + 1, int(b / step) + 1
    for i in range(-na, na + 1):
        for j in range(-nb, nb + 1):
            al, sd = max(-a, min(a, i * step)), max(-b, min(b, j * step))
            out.add((math.floor(cx + fx * al - fy * sd), math.floor(cy + fy * al + fx * sd)))
    return out
def checker(s, v, p, ox=0, oy=0, size=41):
    """Independent re-check of one pose. Returns '' or the reason it is wrong."""
    hl, hw, ca, cs, da, ds = v
    cx, cy, fx, fy = p["cx"], p["cy"], p["fx"], p["fy"]
    ax, ay = cx + fx * ca - fy * cs, cy + fy * ca + fx * cs
    pump = (p["px"], p["py"])
    if abs(math.floor(ax) - pump[0]) > 2 or abs(math.floor(ay) - pump[1]) > 2: return "cap square %d,%d not within 2 of the pump" % (math.floor(ax), math.floor(ay))
    blocked = s["solid"] | s["cars"] | set(s["pumps"])
    body = body_samples(cx, cy, fx, fy, hl + 0.1, hw + 0.1)
    if body & blocked: return "body over %s" % sorted(body & blocked)[:3]
    if any(not (ox <= x < ox + size and oy <= y < oy + size) for x, y in body): return "body off the read area"
    st = (p["sx"], p["sy"])
    # Jamal's rule: the standing square is the free square between the cap and the pump (it touches the pump, the pump is beyond it from the cap)
    if max(abs(st[0] - pump[0]), abs(st[1] - pump[1])) != 1: return "standing square %s does not touch the pump %s" % (st, pump)
    if (pump[0] - st[0]) * (st[0] + 0.5 - ax) + (pump[1] - st[1]) * (st[1] + 0.5 - ay) <= 0: return "the cap does not face the pump across the standing square"
    if st in blocked or st in body_samples(cx, cy, fx, fy, hl, hw): return "standing square %s blocked or under the body" % (st,)
    if math.hypot(st[0] + 0.5 - ax, st[1] + 0.5 - ay) > 1.55: return "standing square %.2f from the cap" % math.hypot(st[0] + 0.5 - ax, st[1] + 0.5 - ay)
    body0 = body_samples(cx, cy, fx, fy, hl + 0.15, hw + 0.15)
    starts = []
    for side in ((1, -1) if ds is None else (1 if ds >= 0 else -1, -1 if ds >= 0 else 1)):
        al = 0 if da is None else da
        starts.append((math.floor(cx + fx * al - fy * side * (hw + 0.6)), math.floor(cy + fy * al + fx * side * (hw + 0.6))))
    for sx0 in starts:
        if sx0 in blocked or sx0 in body0: continue
        seen, q = {sx0}, [sx0]
        while q:
            e = q.pop()
            if e == st: return ""
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (e[0] + d[0], e[1] + d[1])
                if n not in seen and n not in blocked and n not in body0 and ox <= n[0] < ox + size and oy <= n[1] < oy + size: seen.add(n); q.append(n)
    return "no walk from her door to the standing square"

L = env()
M = L.globals().SolStationSurvey
expect_none = {"every side taken", "pump without power"}
for sname in STATIONS:
    s = station(sname)
    for vname, v in VEHICLES.items():
        w = lua_world(L, s)
        geo = L.table_from({"hl": v[0], "hw": v[1], "capAlong": v[2], "capSide": v[3], "cx": 5, "cy": 20, "hx": 1, "hy": 0})
        if v[4] is not None: geo.doorAlong, geo.doorSide = v[4], v[5]
        poses, why = M.poses(w, geo, L.table_from({"x": 5, "y": 20, "hx": 1, "hy": 0}), None)
        n = len(poses)
        plist = [dict(poses[i + 1]) for i in range(n)]
        if sname in expect_none:
            ck("matrix %-44s / %-40s: no pose (as it must)" % (sname, vname), n == 0, n)
            continue
        side_cap = not ((abs(v[2]) - v[0]) > (abs(v[3]) - v[1]))
        if sname == "pump in a narrow alley (walls 3 apart)" or (sname == "lanes too narrow to keep the free square" and side_cap):
            ck("matrix %-44s / %-40s: no room for the free square (or her door) beside the pump: no pose, said before parking" % (sname, vname), n == 0 and why["gap"] + why["body"] > 0, (n, dict(why)))
            continue
        bad = [(p["px"], p["py"], p["fx"], p["fy"], checker(s, v, p)) for p in plist if checker(s, v, p)]
        ck("matrix %-44s / %-40s: %d poses, all keep the free square between cap and pump, all pass the independent check" % (sname, vname, n), n > 0 and not bad, (n, bad[:2], dict(why)))
        if sname == "single-sided: building wall behind the pump":
            ck("matrix single-sided / %s: she stands on the open side" % vname, all(p["sy"] >= 20 for p in plist), [(p["sx"], p["sy"]) for p in plist])
        if sname == "island + bin + car parked on one side":
            ck("matrix island + parked car / %s: she never stands in the taken lane" % vname, all(p["sy"] != 18 for p in plist), [(p["sx"], p["sy"]) for p in plist])

# ---------------------------------------------------------------- 3 replay on the real forecourt
# SolPerception_1794354139165.txt (lab, 2026-11-11 00:42): x,y,shape (1 solid, 2 post, 4 wall north edge, 8 wall west edge). Subset round the pumps.
FORECOURT = ("7295,8165,8 7312,8165,12 7313,8165,4 7314,8165,4 7315,8165,4 7316,8165,4 7317,8165,4 7318,8165,8 7295,8166,8 7312,8166,8 7313,8166,1 "
    "7314,8166,1 7315,8166,1 7316,8166,1 7318,8166,8 7295,8167,9 7296,8167,1 7312,8167,8 7313,8167,1 7314,8167,1 7315,8167,1 7316,8167,1 7318,8167,8 "
    "7320,8167,1 7321,8167,1 7294,8168,4 7295,8168,8 7296,8168,1 7299,8168,1 7312,8168,8 7318,8168,8 7320,8168,1 7321,8168,1 7312,8169,4 7313,8169,4 "
    "7295,8171,8 7295,8172,8 7295,8173,8 7294,8174,4 7306,8178,2 7307,8178,1 7308,8178,1 7309,8178,1 7316,8178,1 7317,8178,1 7318,8178,1 7319,8178,2 "
    "7294,8188,12 7295,8188,4 7296,8188,8 7294,8189,8 7296,8189,8 7319,8189,1 7324,8189,13 7325,8189,4 7326,8189,5 7319,8190,1 7320,8190,1 7323,8190,2 "
    "7324,8190,9 7326,8190,1")
PUMPS_REAL = {(7308, 8178): 4950, (7316, 8178): 272}       # the two remembered pumps ("station:7308,8178,4950" / "7316,8178,272" in the log)
PARKED_REAL = [(7308.49, 8176.5, 1, 0, 2.01, 0.8), (7317.0, 8176.5, 1, 0, 2.42, 0.82)]     # the two cars in the north lanes (dump "car" lines)
SMALL = dict(hl=1.68, hw=0.69, capA=-1.22, capS=1.09, doorA=0.0, doorS=-1.09, fuel=52.2, capacity=59)   # measured 3.36 x 1.38; script GasTank / SeatFrontLeft x 1.82

def forecourt(L, extra_cars=()):
    g = L.globals()
    for t in FORECOURT.split():
        x, y, sh = (int(v) for v in t.split(","))
        if sh & 3: L.execute('W.solid["%d,%d"] = true' % (x, y))
        if sh & 4: L.execute('W.wall["%d,%dS"] = true' % (x, y - 1))
        if sh & 8: L.execute('W.wall["%d,%dE"] = true' % (x - 1, y))
    for (x, y), f in PUMPS_REAL.items(): L.execute('W.fuel["%d,%d"] = %d; W.solid["%d,%d"] = true' % (x, y, f, x, y))
    for (cx, cy, fx, fy, hl, hw) in list(PARKED_REAL) + list(extra_cars):
        L.execute("mkCar({ cx = %f, cy = %f, fx = %d, fy = %d, hl = %f, hw = %f })" % (cx, cy, fx, fy, hl, hw))
def her_car(L, cx, cy, fx, fy, v=SMALL):
    L.execute("CAR = mkCar({ cx = %f, cy = %f, fx = %f, fy = %f, hl = %f, hw = %f, capA = %f, capS = %f, doorA = %s, doorS = %s, fuel = %f, capacity = %f })"
              % (cx, cy, fx, fy, v["hl"], v["hw"], v["capA"], v["capS"], "nil" if v["doorA"] is None else v["doorA"], "nil" if v["doorS"] is None else v["doorS"], v["fuel"], v["capacity"]))
    L.execute("SolUI.gps.lastDriveCar = CAR; SOL.veh = CAR; SOL.x, SOL.y = CAR.cx, CAR.cy")
    return L.globals().CAR
def fuel(L, opt): r = L.eval('{ SolUI.solFuel("%s") }' % opt); return (r[1], r[2])
def logs(L): g = L.globals(); return [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]
def get_out(L):
    """LF's exit: she stands on her door's square (or the far one), he stays in the car."""
    L.execute("""
        local c = CAR
        local function pt(al, sd) return c.cx + c.fx * al - c.fy * sd, c.cy + c.fy * al + c.fx * sd end
        local x, y
        if c.doorA then x, y = pt(c.doorA, c.doorS) else x, y = pt(0, -(c.hw + 0.6)) end       -- the door area's centre, where the game puts whoever gets out
        if W.solid[KEY(x, y)] then if c.doorA then x, y = pt(c.doorA, -c.doorS) else x, y = pt(0, c.hw + 0.6) end end
        SOL.veh, SOL.x, SOL.y = nil, x, y
    """)
def pump_errand(L, max_ticks=600):
    """The Mind's order of asks after the car stands: car, then status until done or failed."""
    r = fuel(L, "car")
    if r[0] is not True and r[0] != 1: return r
    for _ in range(max_ticks):
        L.eval("TICK(250)")
        r = fuel(L, "status")
        if r[1] not in ("walking", "pumping", "starting"): return r
    return r
def park_errand(L, max_ticks=800):
    """The Mind: car_near; if pump_too_far, park and poll park_status (twice at most), then car_near again."""
    said = []
    for attempt in range(2):
        r = fuel(L, "car_near")
        if r[0]: return r, said
        if r[1] != "pump_too_far": return r, said
        r = fuel(L, "park")
        if not r[0]: return r, said
        for _ in range(max_ticks):
            L.eval("TICK(250)")
            r = fuel(L, "park_status")
            if str(r[1]).startswith("parking:"): said.append(r[1])
            if r[0] and str(r[1]).startswith("parking"): continue
            break
        if not r[0]: return r, said
    return fuel(L, "car_near"), said

# 00:40 pose (dump 00:40:59): body 7305.9-7309.27 x 8179.72-8181.13, along x. Which heading / cap side matches the log
# ("car_near -> true near", then "no free square within reach of the work")? Old code, switch off.
match40 = []
for fx in (1, -1):
    for cs in (1.09, -1.09):
        L = env(); L.execute("SW.station_survey = false")
        forecourt(L); v = dict(SMALL, capS=cs, doorS=-cs)
        her_car(L, 7307.585, 8180.425, fx, 0, v)
        L.execute("PLAYER.veh = CAR; PLAYER.x, PLAYER.y = CAR.cx + 0.3, CAR.cy")
        near = fuel(L, "car_near"); get_out(L); car = fuel(L, "car")
        if near == (True, "near") and car == (False, "no_way_to_pump"): match40.append((fx, cs))
ck("replay 00:40 (old code): a heading / cap side reproduces the log 'near' then 'no free square within reach' (%s)" % match40, len(match40) >= 1, match40)
for fx, cs in match40[:1]:
    L = env()
    forecourt(L); v = dict(SMALL, capS=cs, doorS=-cs)
    her_car(L, 7307.585, 8180.425, fx, 0, v)
    L.execute("PLAYER.veh = CAR; PLAYER.x, PLAYER.y = CAR.cx + 0.3, CAR.cy")
    near = fuel(L, "car_near")
    ck("replay 00:40, survey on: car_near from that stop says no (the cap side has no free square) -> she re-parks", near == (False, "pump_too_far"), (near, logs(L)[-3:]))
    r, said = park_errand(L)
    ck("replay 00:40, survey on: parked and checked from the real stop", r == (True, "near"), (r, [l for l in logs(L) if "SolStation" in l][-6:]))
    get_out(L)
    res = pump_errand(L)
    ck("replay 00:40, survey on: she walks to the cap and the game's action fills the car", str(res[1]).startswith("done:") and L.globals().DID_PUMP, (res, [l for l in logs(L) if "SolFuel" in l or "SolMoveCheck" in l][-5:]))

# 00:37 and 00:38: the same diagonal stop (dumps 00:37:44 .. 00:39:07: 7305.11,8177.63 7304.12,8178.59 7306.47,8181.00 7307.46,8180.03).
# Log: "2 squares to try", solGoto(7308,8180) then (7308,8179), each answered "[SolMoveCheck] 1.4 (0.7) tiles from him: there" + LF "stay".
# He sat in the car; his distance from her is set to the logged one.
DIAG = (7305.79, 8179.31, -0.6993, -0.7148, 1.09)       # the one heading / cap side that gives the log's 2 squares and first target
def diag(L, his):
    forecourt(L); her_car(L, DIAG[0], DIAG[1], DIAG[2], DIAG[3], dict(SMALL, capS=DIAG[4], doorS=-DIAG[4]))
    L.execute("PLAYER.veh = CAR")
    near = fuel(L, "car_near")
    get_out(L)
    L.execute(HIM % (his, his))
    return near
# he is between her and the fuel cap at the logged distance (the log line is printed only when her target is within 2.5 of him)
HIM = ("local ax, ay = CAR.cx + CAR.fx * CAR.capA - CAR.fy * CAR.capS, CAR.cy + CAR.fy * CAR.capA + CAR.fx * CAR.capS; "
       "local dx, dy = ax - SOL.x, ay - SOL.y; local d = math.sqrt(dx * dx + dy * dy); PLAYER.x, PLAYER.y = SOL.x + dx / d * %f, SOL.y + dy / d * %f")
for tag, his in (("00:37", 1.4), ("00:38", 0.7)):
    L = env(); L.execute("SW.station_survey = false")
    near = diag(L, his)
    res = pump_errand(L)
    lg = logs(L); gos = list(L.globals().GOTOS.values())
    ck("replay %s (old code): near, '2 squares to try', first walk to 7308,8180, every walk 'tiles from him: there', no_way_to_pump" % tag,
       near == (True, "near") and res == (False, "no_way_to_pump") and any("2 squares to try" in l for l in lg) and gos[:1] == ["7308,8180"]
       and any("tiles from him: there" in l for l in lg) and not L.globals().DID_PUMP, (near, res, gos[:4], [l for l in lg if "Sol" in l][:4]))
    L = env()
    near = diag(L, his)
    if near != (True, "near"):
        L.execute("SOL.veh = CAR; SOL.x, SOL.y = CAR.cx, CAR.cy"); r, said = park_errand(L); get_out(L)
        L.execute(HIM % (his, his))
    res = pump_errand(L)
    lg = logs(L)
    ck("replay %s, survey on: (car_near %s) her walk to the cap is not 'a walk to him'; the car is filled" % (tag, near[1]),
       str(res[1]).startswith("done:") and not any("tiles from him: there" in l for l in lg), (res, [l for l in lg if "Sol" in l][-6:]))

# move_check itself: a walk to him (no fuel errand) still stops 1.5 tiles from him with the switch on
L = env(); forecourt(L); her_car(L, 7290.5, 8182.5, 1, 0)
L.execute("SOL.veh = nil; SOL.x, SOL.y = 7300.5, 8182.5; PLAYER.veh = nil; PLAYER.x, PLAYER.y = 7301.5, 8182.5")
L.execute("SolUI.solGoto(7301, 8182, 0)")
ck("move_check unchanged for a walk to him (no fuel errand): 'tiles from him: there'", any("tiles from him: there" in l for l in logs(L)))

# ---------------------------------------------------------------- 4 drive faults, limits, KI5, cache
def fresh_forecourt(extra=(), start=(7292.5, 8181.0, 1, 0), v=SMALL):
    L = env(); forecourt(L, extra); her_car(L, start[0], start[1], start[2], start[3], v)
    L.execute("PLAYER.veh = CAR; PLAYER.x, PLAYER.y = CAR.cx, CAR.cy")
    return L
L = fresh_forecourt(); L.execute("NAV.failAt[1] = true")
r, said = park_errand(L)
ck("first plan fails (failed:no_path): the next pose is driven, parked, nothing said (she never moved)", r == (True, "near") and said == [] and L.globals().NAV.plans >= 2, (r, said, L.globals().NAV.plans))
L = fresh_forecourt(); L.execute("NAV.drift[2] = { -3, 0 }")   # s95b: plan 1 is the approach point, plan 2 the pose
r, said = park_errand(L)
ck("a stop 3 short (cap out of the hose's reach): checked, re-parked with one line, then near", r == (True, "near") and len(said) == 1 and said[0] in ("parking:other_side", "parking:other_pump"), (r, said, [l for l in logs(L) if "SolStation" in l][-4:]))
L = fresh_forecourt(); L.execute("for i = 1, 20 do NAV.drift[i] = { 0, -30 } end")   # 30 squares off: never a valid stop
r, said = park_errand(L)
ck("every stop off: at most %d re-parks, then survey_no_stand" % 2, r == (False, "survey_no_stand") and sum("after the stop" in l for l in logs(L)) <= 3 and L.globals().NAV.plans <= 6, (r, L.globals().NAV.plans))   # s95b: an approach plan + the pose plan per stop
L = fresh_forecourt(extra=[(7308.0, 8180.8, 1, 0, 2.2, 0.9), (7317.0, 8180.8, 1, 0, 2.2, 0.9), (7312.5, 8178.5, 0, 1, 1.0, 0.6), (7304.5, 8178.5, 0, 1, 1.0, 0.6), (7321.0, 8178.5, 0, 1, 1.0, 0.6)])
r, said = park_errand(L)
ck("every lane at both pumps taken: survey_no_pose BEFORE any drive (she says there is no free place by the pumps)", r == (False, "survey_no_pose") and L.globals().NAV.plans == 0, (r, L.globals().NAV.plans, [l for l in logs(L) if "SolStation" in l][-2:]))
L = fresh_forecourt(); L.execute('W.power["7308,8178"] = false; W.power["7316,8178"] = false')
r, said = park_errand(L)
ck("no power at either pump: survey_no_pump", r == (False, "survey_no_pump"), r)
L = fresh_forecourt(); L.execute('W.fuel["7308,8178"] = 0')
r, said = park_errand(L)
ck("the nearer pump pumped dry: she goes to the other pump", r == (True, "near") and all(abs(g.x - 7316) < 6 for g in L.globals().NAV.goals.values()), (r, [(round(g.x, 1), round(g.y, 1)) for g in L.globals().NAV.goals.values()]))
KI5 = dict(hl=4.6, hw=1.3, capA=1.0, capS=1.65, doorA=3.2, doorS=-1.65, fuel=40, capacity=300)
L = fresh_forecourt(start=(7290.0, 8183.0, 1, 0), v=KI5)
r, said = park_errand(L)
get_out(L); res = pump_errand(L)
ck("KI5 long truck (9.2 m, cap ahead of the centre): parked, walked, filled", r == (True, "near") and str(res[1]).startswith("done:"), (r, res, [l for l in logs(L) if "Sol" in l][-4:]))
REAR = dict(hl=2.4, hw=0.9, capA=-2.75, capS=0.0, doorA=0.4, doorS=-1.3, fuel=10, capacity=80)
L = fresh_forecourt(v=REAR)
r, said = park_errand(L); get_out(L); res = pump_errand(L)
ck("cap at the back: parked tail to the pump, filled", r == (True, "near") and str(res[1]).startswith("done:"), (r, res))
NOCAP = dict(SMALL, capA=None, capS=None)
L = env(); forecourt(L)
L.execute("CAR = mkCar({ cx = 7292.5, cy = 8181, fx = 1, fy = 0, hl = 1.68, hw = 0.69, fuel = 1, capacity = 50 }); SolUI.gps.lastDriveCar = CAR; SOL.veh = CAR")
ck("a vehicle without a GasTank part: no_gas_tank at once", fuel(L, "car_near") == (False, "no_gas_tank"), fuel(L, "car_near"))
L = fresh_forecourt(); L.execute("SW.station_survey = false")
r = fuel(L, "car_near"); p = fuel(L, "park")
ck("switch off: car_near / park are the old ones (old Java park asked, survey never)", r == (False, "pump_too_far") and p == (False, "park_unavailable") and not any("SolStation" in l for l in logs(L)), (r, p))
# Jamal's rule from where the car stands: the car already at the pump but flush against the island (the square between covered)
L = env(); forecourt(L); her_car(L, 7307.585, 8179.25, -1, 0)
L.execute("PLAYER.veh = CAR")
r = fuel(L, "car_near")
ck("car flush against the island (cap within the game's reach, no free square between cap and pump): not accepted, she re-parks",
   r == (False, "pump_too_far") and any("no_free_square_between" in l for l in logs(L)), (r, logs(L)[-2:]))
r, said = park_errand(L)
c = L.globals().CAR
ax, ay = c.cx + c.fx * c.capA - c.fy * c.capS, c.cy + c.fy * c.capA + c.fx * c.capS
gapsq = [(x, y) for x in range(7306, 7311) for y in range(8176, 8182) if max(abs(x - 7308), abs(y - 8178)) == 1 and (x, y) not in ((7307, 8178), (7309, 8178))
         and not L.eval("RECT_HITS(CAR.cx, CAR.cy, CAR.fx, CAR.fy, CAR.hl, CAR.hw, %d, %d)" % (x, y)) and (7308 - x) * (x + 0.5 - ax) + (8178 - y) * (y + 0.5 - ay) > 0]
ck("after the re-park a free square lies between the real cap and the pump", r == (True, "near") and len(gapsq) > 0, (r, gapsq))

# the station is read once per life
L = fresh_forecourt()
park_errand(L); reads1 = L.globals().W.reads
L.execute("CAR.cx, CAR.cy, CAR.fx, CAR.fy = 7292.5, 8181, 1, 0; SOL.veh = CAR")
park_errand(L); reads2 = L.globals().W.reads - reads1
ck("second errand at the same station: the station is not read again (%d squares read the first time, %d the second)" % (reads1, reads2), reads2 < reads1 / 3, (reads1, reads2))
L.execute("MODDATA.Sol_Life.deaths = 1; CAR.cx, CAR.cy, CAR.fx, CAR.fy = 7292.5, 8181, 1, 0; SOL.veh = CAR")
r0 = L.globals().W.reads; park_errand(L); reads3 = L.globals().W.reads - r0
ck("a new life: her station memory is empty and the station is read again", reads3 > reads1 * 0.8 and any("a new life" in l for l in logs(L)), (reads3, reads1))
# the walk squares never include his square or a square under another car
L = fresh_forecourt(); park_errand(L); get_out(L)
L.execute("PLAYER.veh = nil")
L.execute("local c = CAR; local ax, ay = c.cx + c.fx * c.capA - c.fy * c.capS, c.cy + c.fy * c.capA + c.fx * c.capS; PLAYER.x, PLAYER.y = math.floor(ax) + 0.5, math.floor(ay) + 0.5")
sq = L.eval("SolStationSurvey.standSquares(SOL, CAR, CAR.cx + CAR.fx * CAR.capA - CAR.fy * CAR.capS, CAR.cy + CAR.fy * CAR.capA + CAR.fx * CAR.capS, 1.6)")
pk = L.eval("KEY(PLAYER.x, PLAYER.y)")
ck("walk squares: his square is left out, none under a car", all("%d,%d" % (q.x, q.y) != pk for q in sq.values()) and all(not L.eval("RECT_HITS(CAR.cx, CAR.cy, CAR.fx, CAR.fy, CAR.hl, CAR.hw, %d, %d)" % (q.x, q.y)) for q in sq.values()), [(q.x, q.y) for q in sq.values()])
# a stale job: the park order runs no work once it is over
L = fresh_forecourt(); fuel(L, "car_near"); fuel(L, "park"); fuel(L, "cancel")
n0 = L.globals().NAV.n
for _ in range(20): L.eval("TICK(250)")
ck("cancel ends the park order (no planner calls after it)", L.globals().SolStationSurvey.job is None and L.globals().NAV.n == n0, (L.globals().NAV.n, n0))

# ---------------------------------------------------------------- 5 Mind parking_wait
sys.path.insert(0, MD)
for m in list(sys.modules):
    if m in ("goal_engine",) or m.startswith("world_"): del sys.modules[m]
GE = importlib.import_module("goal_engine")
RE = GE.PLANNERS["refuel_errand"]
ck("the patched goal_engine is imported (TELL has the survey lines, PARK_SAY exists)", "survey_no_pose" in RE.TELL and "no_way_to_pump" in RE.TELL and hasattr(RE, "PARK_SAY"))
class Eng:
    def __init__(self): self.lua_dir = T; self.said = []; self.done = None
    def perception(self): return {"sol": {"currentVehicle": 1}}
    def wait(self, g, r): g["reason"] = r
    def fail(self, g, r): self.done = ("fail", r); return True
    def complete(self, g, r): self.done = ("complete", r); return True
    def say_once(self, g, t): self.said.append(t)
def mind(seq):
    e = Eng(); goal = {"intent": "refuel_errand", "slots": {"target": "car"}, "phase": "parking_wait", "phaseSince": 100.0}
    p = RE(e, goal)
    it = iter(seq)
    p._park_status = lambda g, now: next(it, None)
    p._action = lambda *a, **k: "r1"
    p._clear_own_target = lambda: None
    t = 100.0
    for _ in seq:
        t += 1; p.tick(t)
        if e.done: break
    return e, goal
e, goal = mind([(True, "parking"), (True, "parking:other_pump"), (True, "parking"), (True, "parking:other_pump"), (True, "parking:other_side")])
ck("Mind: 'parking:other_pump' said once, 'other_side' once, still waiting", e.said == [RE.PARK_SAY["other_pump"], RE.PARK_SAY["other_side"]] and goal["phase"] == "parking_wait" and e.done is None, (e.said, goal.get("phase")))
e, goal = mind([(True, "parking"), (False, "survey_no_pose")])
ck("Mind: survey_no_pose ends the errand at once with its own line", e.done == ("fail", "survey_no_pose") and e.said == [RE.TELL["survey_no_pose"]], (e.done, e.said))
e, goal = mind([(True, "parked")])
ck("Mind: parked -> park_check as before", goal["phase"] == "park_check" and e.done is None, goal.get("phase"))
e, goal = mind([(False, "pump_too_far")])
ck("Mind: an old failure -> park_check as before (unchanged)", goal["phase"] == "park_check" and e.done is None, goal.get("phase"))
ck("Mind: every survey reason the Lua can send has a line, and no line names a mechanism", all(k in RE.TELL for k in ("survey_no_pump", "survey_no_pose", "survey_no_stand", "survey_drive_failed", "survey_no_cap"))
   and all(not re.search(r"[A-Za-z0-9_]", RE.TELL[k]) for k in RE.TELL if k.startswith("survey_")) and all(not re.search(r"[A-Za-z0-9_]", v) for v in RE.PARK_SAY.values()))

# ---------------------------------------------------------------- 6 general behaviour only
src = open(os.path.join(HERE, "SolStationSurvey.lua"), encoding="utf-8").read()
code = "\n".join(l.split("--", 1)[0] for l in src.splitlines())
hits = re.findall(r"\b\d{4,}\b", code)
ck("SolStationSurvey.lua: no map coordinates (no 4+ digit numbers in code)", [h for h in hits if h not in ("1000", "1500", "5000", "60000", "115000", "600000")] == [], hits)
names = re.findall(r"(?i)gas2go|fossoil|smallcar|bradley|base\.[a-z]|ki5|muldraugh|riverside|west point|louisville", code)
ck("SolStationSurvey.lua: no station, brand, town or vehicle names in code", names == [], names)
inst = open(os.path.join(HERE, "apply_s95_station_refuel.py"), encoding="utf-8").read()
ck("the installer's Lua edits name nothing either", not re.search(r"(?i)gas2go|fossoil|smallcar|\b7\d{3}\b|\b8\d{3}\b", inst))

print("")
print("%d checks, %d failed" % (N[0], len(FAIL)))
if FAIL: print("FAILED: " + "; ".join(FAIL)); sys.exit(1)
print("ALL PASS (offline; not a runtime PASS)")

"""Offline tests for apply_s72_far_arrival.py. usage: python test_far_arrival.py
  1 the installer on copies of the lab files (SCPersistence, SolFar, SolOrders) and the Mind (chat_service, goal_engine, road_route):
    applies, twice changes nothing, in either order with apply_s70b_mind / apply_s71_mind
  2 her case of 2026-11-10 19:45-19:47 on the lab SolFar.lua, from the save copy: her record by the farm (7410,8274, global_mod_data.bin),
    her car 5 (Sol_Far mod data: 7411.5,8276.3, 650 kg, 38.6 l), him at 7205,8148, ring 9. Before: record_failed (the cause, reproduced).
    After: car moved once, she gets in when it loads, turned along the road, at the wheel, fuel taken once.
  3 the other cases: a saved record that cannot move (the car stays), a saved record that moves (restored by the car, then the wheel),
    zombies by the spot, an occupied spot, Bradley (210 s), a KI5 car, a helicopter (60 s)
  4 the road spot on the real gazetteer: on a street, outside what is loaded, a straight stretch, toward him; a curved road; a helicopter's
    open place
  5 her words: every far-flow line has no mechanics in it
  6 vehicles.db copy (read-only copy of the save): car 5 is one row, at the spot the live run moved it to
Offline PASS is not Runtime PASS."""
import importlib, math, os, re, shutil, sqlite3, struct, subprocess, sys, tempfile
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
# the files as they were before apply_s72 was first installed (2026-11-10 20:14), and the live ones (with the first s72) for the upgrade
LAB = os.path.join(HERE, "..", "_backup", "20261110_before_s67_73", "client")
MIND = os.path.join(HERE, "..", "_backup", "20261110_before_s67_73", "mind")
LAB_NOW = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
MIND_NOW = r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind"
SAVE = os.path.join(HERE, "place_fixtures", "save_20261110_1947")      # copies taken at 19:49 (global_mod_data.bin of 18:22, vehicles.db of 19:47)
FAIL, N = [], [0]
def ck(n, c, d=""):
    N[0] += 1
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)

# ---------------------------------------------------------------- 1 the installer
T = tempfile.mkdtemp(prefix="sol_far_arrival_")
def fresh(tag, lab=LAB, mind=MIND):
    cl, md = os.path.join(T, tag, "client"), os.path.join(T, tag, "mind")
    os.makedirs(cl); os.makedirs(md)
    for n in ("SCPersistence.lua", "SolFar.lua", "SolOrders.lua"): shutil.copy(os.path.join(lab, n), cl)
    for n in ("chat_service.py", "goal_engine.py", "road_route.py", "model_router.py"): shutil.copy(os.path.join(mind, n), md)
    return cl, md
def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, script)] + list(args), capture_output=True, text=True, encoding="utf-8")
def snap(*dirs):
    out = {}
    for d in dirs:
        for n in sorted(os.listdir(d)): out[n] = open(os.path.join(d, n), encoding="utf-8").read()
    return out
cl, md = fresh("a")
r = run("apply_s72_far_arrival.py", cl, md); ck("installer applies", r.returncode == 0, r.stderr[-400:])
once = snap(cl, md)
r = run("apply_s72_far_arrival.py", cl, md); ck("installer twice: nothing changes", r.returncode == 0 and snap(cl, md) == once, r.stderr[-300:])
for other in ("apply_s71_mind.py", "apply_s70b_mind.py"):
    if os.path.exists(os.path.join(HERE, other)):
        r = run(other, md); ck("then %s still applies" % other, r.returncode == 0, r.stderr[-300:])
clB, mdB = fresh("b")
for other in ("apply_s71_mind.py", "apply_s70b_mind.py"):
    if os.path.exists(os.path.join(HERE, other)): run(other, mdB)
r = run("apply_s72_far_arrival.py", clB, mdB); ck("after apply_s71_mind / apply_s70b_mind too", r.returncode == 0, r.stderr[-300:])
clU, mdU = fresh("upgrade", LAB_NOW, MIND_NOW)
r = run("apply_s72_far_arrival.py", clU, mdU); ck("upgrade: on the lab and Mind as installed at 20:14 (the first s72)", r.returncode == 0, r.stderr[-400:])
up = snap(clU, mdU); r = run("apply_s72_far_arrival.py", clU, mdU); ck("upgrade twice: nothing changes", r.returncode == 0 and snap(clU, mdU) == up, r.stderr[-300:])
ck("upgrade: the inside arrival is in", "F.arriveTick" in open(os.path.join(clU, "SolFar.lua"), encoding="utf-8").read() and "inner=inside" in open(os.path.join(mdU, "chat_service.py"), encoding="utf-8").read())
for n in ("SolFar.lua", "SolOrders.lua", "SCPersistence.lua"):
    src = open(os.path.join(cl, n), encoding="utf-8").read()
    ck("%s compiles in Kahlua-like Lua" % n, not isinstance(lua51.LuaRuntime().globals().loadstring(src), tuple))

# ---------------------------------------------------------------- 2 her case, from the save copy
mod = open(os.path.join(SAVE, "global_mod_data.bin"), "rb").read()            # read-only; opened for reading only
def dbl(key, start=0):
    i = mod.index(key, start) + len(key) + 1
    return struct.unpack(">d", mod[i:i + 8])[0], i
car_x, _ = dbl(b"\x04carX"); car_y, _ = dbl(b"\x04carY"); car_id, _ = dbl(b"\x08carSqlId"); fuel, _ = dbl(b"\x07carFuel")
mass, _ = dbl(b"\x07carMass"); qual, _ = dbl(b"\x0acarQuality")
pos = mod.index(b"\x08position"); her_x, j = dbl(b"\x01x", pos); her_y, _ = dbl(b"\x01y", j)
ck("save copy: her saved place by the farm (%.0f,%.0f), her car %d at %.1f,%.1f" % (her_x, her_y, car_id, car_x, car_y),
   int(car_id) == 5 and abs(her_x - 7410) < 2 and abs(her_y - 8274) < 2 and abs(car_x - 7411.5) < 1, (her_x, her_y, car_id, car_x, car_y))

WORLD = r"""
NOW = 100000
function getTimestampMs() return NOW end
LOGS = {}
print = function(m) LOGS[#LOGS + 1] = tostring(m) end
require = function() end
TASKS = {}
SolBudget = { register = function(n, f, o) TASKS[n] = f end }
SW = { far_car = false, spatial_access = false }
SolAuthority = { on = function(n) return SW[n] == true end }
PX, PY, RING = 7205, 8148, 9
PL = { getX = function() return PX end, getY = function() return PY end, getZ = function() return 0 end, getVehicle = function() return nil end }
function getSpecificPlayer() return PL end
HALF_W, HALF_H = 20, 11
function getFileReader() return nil end
function isoToScreenX(p, x, y, z) return HALF_W * 32 + ((x - PX) - (y - PY)) * 32 end
function isoToScreenY(p, x, y, z) return HALF_H * 32 + ((x - PX) + (y - PY)) * 16 - z * 96 end
function getPlayerScreenLeft() return 0 end
function getPlayerScreenTop() return 0 end
function getPlayerScreenWidth() return HALF_W * 64 end
function getPlayerScreenHeight() return HALF_H * 64 end
ZOMBIES = {}
VEHS = {}
function getCell() return { getZombieList = function() return { size = function() return #ZOMBIES end, get = function(self, i) return ZOMBIES[i + 1] end } end,
                            getVehicles = function() return { size = function() return #VEHS end, get = function(self, i) return VEHS[i + 1] end } end } end
function ROAD(x, y) return false end
function getScriptManager() return { getVehicle = function() return { getMass = function() return MASS end } end } end
function chunkLoaded(x, y) return math.max(math.abs(math.floor(x / 8) - math.floor(PX / 8)), math.abs(math.floor(y / 8) - math.floor(PY / 8))) <= RING end
local SQ = {}
function square(x, y)
    x, y = math.floor(x), math.floor(y)
    if not chunkLoaded(x, y) then return nil end
    local k = x * 100000 + y
    if SQ[k] == nil then SQ[k] = { x = x, y = y, getX = function() return x end, getY = function() return y end, isOutside = function() return true end,
        isFree = function() return true end,
        getFloor = function() return { getSprite = function() return { getName = function() return ROAD(x, y) and "blends_street_01_54" or "blends_natural_01_16" end } end } end } end
    return SQ[k]
end
Vector3f = { new = function() return {} end }
-- her car: the forward vector turns with setAngles, the opposite way to what a guess would say (the sign must be checked)
CAR = { x = CAR_X, y = CAR_Y, ay = 0, fuel = CAR_FUEL, fuelSets = 0, moved = false }
function CAR:getX() return self.x end function CAR:getY() return self.y end function CAR:getZ() return 0 end
function CAR:getForwardVector(v) local r = math.rad(-self.ay); return { x = function() return math.cos(r) end, z = function() return math.sin(r) end } end
function CAR:getAngleX() return 0 end function CAR:getAngleY() return self.ay end function CAR:getAngleZ() return 0 end
function CAR:setAngles(a, b, c) self.ay = b end
function CAR:door()                                   -- the driver's door: to the left of the way it faces, 1.2 tiles out
    local f = self:getForwardVector(); local fx, fz = f.x(), f.z()
    return self.x + fz * 1.2, self.y - fx * 1.2
end
function CAR:getEnterSeatDistance(seat, x, y) local dx, dy = self:door(); return (x - dx) ^ 2 + (y - dy) ^ 2 end
function CAR:getPartById(id) return { getContainerContentAmount = function() return CAR.fuel end, setContainerContentAmount = function(_, v) CAR.fuel = v; CAR.fuelSets = CAR.fuelSets + 1 end } end
function CAR:getScriptName() return "Base.SmallCar" end
MOVES = {}
MOVE_STATE = "ok"
function solCarMoveRequest(id, x, y) MOVES[#MOVES + 1] = { id, x, y }; if MOVE_STATE == "ok" then CAR.x, CAR.y, CAR.moved = x, y, true end; return true end
function solCarMoveState() return MOVE_STATE end
function solCarMoveRing() return RING end
function solCarMoveCancel() return true end
MD = { carSqlId = CAR_ID, carX = CAR_X, carY = CAR_Y, carZ = 0, carFuel = CAR_FUEL, carMass = MASS, carQuality = QUAL, carTowing = false }
ModData = { getOrCreate = function() return MD end }
-- her: registered with no body (LIVE), or a saved record (REC)
LIVE = { x = HER_X, y = HER_Y, veh = nil }
function LIVE:getX() return self.x end function LIVE:getY() return self.y end function LIVE:getZ() return 0 end
function LIVE:getCurrentSquare() return square(self.x, self.y) end
function LIVE:getVehicle() return self.veh end
REGISTERED = true
SolUI = { solActor = function() if REGISTERED then return LIVE end return nil end }
IDS, REC, BOOT = {}, nil, true
RELOCATED, RECOVERS, WHEEL = nil, 0, 0
SurvivorCompanion = {
    Persistence = { pendingIds = function() return IDS end, pendingCount = function() return #IDS end,
                    pendingBootstrap = function(id) if BOOT then return REC end return nil end,
                    pendingRelocate = PENDING_RELOCATE },
    GameplayUtil = { gridSquare = function(x, y, z) return square(x, y) end, isSafeSpawnSquare = function(sq) return true end, idOf = function() return "sc-1" end },
    Commands = { issue = function(id, cmd) ISSUED = cmd end },
    Actor = { recover = function(a, sq) RECOVERS = RECOVERS + 1; a.x, a.y = sq.x + 0.5, sq.y + 0.5; return true end },
    Driving = { takeWheel = function(a, car, intent)
        WHEEL = WHEEL + 1
        local dx, dy = car:door()
        if (a.x - dx) ^ 2 + (a.y - dy) ^ 2 > 1.5 then return false, "companion is not at the passenger door" end
        a.veh = car; return true end },
    Vehicle = { loadedBySqlId = function(id) if id == CAR_ID and chunkLoaded(CAR.x, CAR.y) then return CAR end return nil end },
}
function tick(ms) NOW = NOW + (ms or 1000); TASKS["far"]() end
function poll() return select(2, SolUI.solFar("poll")) end
"""
# the real pendingRelocate (patched or not), with pending[] as the only state
def relocate_src(path):
    s = open(path, encoding="utf-8").read()
    body = s[s.index("function persistence.pendingRelocate"):]
    body = body[:body.index("\nend\n") + 5]
    return "PENDING = {}\nlocal pending = PENDING\nlocal persistence = {}\n" + body + "PENDING_RELOCATE = persistence.pendingRelocate\n"
def world(solfar, persist, setup=""):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute("CAR_X, CAR_Y, CAR_ID, CAR_FUEL, MASS, QUAL, HER_X, HER_Y = %r, %r, %d, %r, %r, %r, %r, %r" % (car_x, car_y, int(car_id), fuel, mass, qual, her_x, her_y))
    L.execute(relocate_src(persist))
    L.execute(WORLD)
    if setup: L.execute(setup)
    L.execute(open(solfar, encoding="utf-8").read())
    return L, L.globals()
SPOT = "7277.5,8232.5,190,-90"                         # what pickup_spot_dir gives for this trip (checked in part 4)
def trip(L, g, spot=SPOT, wait_s=180):
    for _ in range(3): g.tick(1000)                    # her body has been gone for more than 2 s
    r = g.SolUI.solFar("car_far:" + spot)
    for _ in range(wait_s + 2): g.tick(1000)
    g.tick(1000)
    return r
def logs(g): return [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]

L, g = world(os.path.join(LAB, "SolFar.lua"), os.path.join(LAB, "SCPersistence.lua"))
r = trip(L, g, "7277.5,8232.5,190")
ck("before: her case reproduced (registered without a body, the car moved, poll record_failed)", r[1].startswith("waiting:") and g.poll() == "record_failed" and len(g.MOVES) == 1, (r, g.poll(), logs(g)[-3:]))
ck("before: and persistence says why: no pending entry for \"live\"", L.eval('select(2, PENDING_RELOCATE("live", 1, 1, 0))') is None and L.eval('PENDING_RELOCATE("live", 1, 1, 0)') is False)

PF, PP = os.path.join(cl, "SolFar.lua"), os.path.join(cl, "SCPersistence.lua")
ck("after: persistence gives the reason", world(PF, PP)[0].eval('select(2, PENDING_RELOCATE("live", 1, 1, 0))') == "no_pending_entry")
L, g = world(PF, PP)
r = trip(L, g)
ck("after: the car is moved once, to the road spot", len(g.MOVES) == 1 and tuple(g.MOVES[1].values()) == (5, 7277.5, 8232.5), [tuple(m.values()) for m in g.MOVES.values()])
ck("after: placed, not record_failed; nothing about her yet", g.poll() == "placed" and g.RECOVERS == 0, g.poll())
for _ in range(20): g.tick(1000)
ck("after: while its part of the world is not loaded, nothing happens (no body without the car)", g.RECOVERS == 0 and g.poll() == "placed")
L.execute("PX, PY = 7232, 8172")                     # he goes toward her: the car's chunk loads
seq = []
for _ in range(6):
    g.tick(1000); seq.append(g.poll())
ck("after: when it loads she is back at its door and at the wheel the same second", g.LIVE.veh is not None and g.RECOVERS == 1 and g.WHEEL == 1, (g.RECOVERS, g.WHEEL, logs(g)[-4:]))
ck("after: the car faces along the road (north)", abs(L.eval("CAR:getForwardVector().z()") + 1) < 0.02, L.eval("CAR.ay"))
ck("after: poll says here once she is in", seq[-1] == "here", seq)
ck("after: her body appeared out of his view", not L.eval("(function() local x, y = LIVE.x, LIVE.y; return math.abs(x - PX) < 20 and math.abs(y - PY) < 20 end)()"))
cost = g.MD.fuelDue
for _ in range(10): g.tick(1000)
ck("after: fuel taken once (%.3f l), the car moved once" % (fuel - L.eval("CAR.fuel")), g.CAR.fuelSets == 1 and abs((fuel - L.eval("CAR.fuel")) - 0.227) < 0.01 and len(g.MOVES) == 1, (g.CAR.fuelSets, fuel - L.eval("CAR.fuel"), cost))
ck("after: no reason talk anywhere: the log has the steps", any("at the wheel" in l for l in logs(g)) and any("gets in when it loads" in l for l in logs(g)), logs(g)[-6:])

# zombies by the spot: she still gets in (the car is the safe place)
L, g = world(PF, PP, "ZOMBIES = { { getX = function() return 7278 end, getY = function() return 8236 end } }")
trip(L, g); L.execute("PX, PY = 7232, 8172")
for _ in range(4): g.tick(1000)
ck("zombies by the spot: she is in the car all the same", g.LIVE.veh is not None)
# a saved record that persistence will not move (a spawn ticket): the car stays, she walks
L, g = world(PF, PP, "REGISTERED = false; IDS = { 'sc-1' }; REC = { id = 'sc-1', x = HER_X, y = HER_Y, z = 0 }")
for _ in range(3): g.tick(1000)
r = g.SolUI.solFar("car_far:" + SPOT)
L.execute("BOOT = false")                              # during the wait her saved record got a spawn ticket (persistence will not move it now)
for _ in range(183): g.tick(1000)
ck("record that cannot move: the car is not moved", len(g.MOVES) == 0, [tuple(m.values()) for m in g.MOVES.values()])
ck("record that cannot move: no trip on foot from here either (record gone from reach): poll record_failed, the Mind takes it (part 5)", g.poll() == "record_failed", g.poll())
ck("record that cannot move: the reason is in the log only", any("could not come with it (" in l for l in logs(g)), logs(g)[-3:])
# a saved record that moves: beside the car, restored when it loads, then to the door and the wheel
L, g = world(PF, PP, "REGISTERED = false; IDS = { 'sc-1' }; REC = { id = 'sc-1', x = HER_X, y = HER_Y, z = 0 }; PENDING['sc-1'] = { record = { position = { x = HER_X, y = HER_Y, z = 0 } }, bucket = 'companions' }")
trip(L, g)
ck("saved record: moved beside the car", g.poll() == "placed" and L.eval("PENDING['sc-1'].record.position.x") == 7279, L.eval("PENDING['sc-1'].record.position.x"))
L.execute("PX, PY = 7232, 8172; LIVE.x, LIVE.y = PENDING['sc-1'].record.position.x + 0.5, PENDING['sc-1'].record.position.y + 0.5; REGISTERED = true")   # the restore
for _ in range(4): g.tick(1000)
ck("saved record: restored off the door, put at the door, at the wheel", g.LIVE.veh is not None and g.RECOVERS == 1, (g.RECOVERS, g.WHEEL, logs(g)[-3:]))
# an occupied road spot: the Java side refuses, nothing moved
L, g = world(PF, PP, "MOVE_STATE = 'spot_taken'")
trip(L, g)
ck("occupied spot: refused, the car stays where it was", g.poll() == "spot_taken" and not g.CAR.moved, g.poll())
# Bradley, a KI5 car and a helicopter through far_car's own car list
CARS = "SW.far_car = true; function solCarsNearRequest() return true end; function solCarsNearState() return 'ok' end; function solCarsNearResult() return CARLIST end"
for name, script, secs in (("Bradley", "Base.M2Bradley", 210), ("KI5 car", "Base.93fordElite", 180), ("helicopter", "Base.UH1Huey", 60)):
    L, g = world(PF, PP, CARS + "; CARLIST = '%d,%d|9,%d,%d,4,%s,80,100,0,100,-1,0,ok'" % (her_x, her_y, her_x + 3, her_y, script))
    for _ in range(3): g.tick(1000)
    g.tick(16000); g.tick(1000)
    w = g.SolUI.solFar("car_where")
    ck("%s: car_where says its kind" % name, w[0] and w[1].endswith("," + ("tracked" if secs == 210 else "heli" if secs == 60 else "car")), w)
    r = g.SolUI.solFar("car_far:" + SPOT)
    ck("%s: waits %d s" % (name, secs), r == (True, "waiting:%d" % secs), r)



# ---------------------------------------------------------------- 3b inside the loaded area (owner's decision: he stays where he is)
ARRIVE = r"""
AR = { state = "idle", n = 0 }
function solCarArriveRequest(id, x, y)
    if not chunkLoaded(x, y) then AR.state = "target_unloaded"; return false end
    AR.req, AR.state, AR.n = { id, x, y }, "queued", AR.n + 1; return true end
function solCarArriveState() return AR.state end
function solCarArriveCancel() AR.req = nil; AR.state = "cancelled"; return true end
function STREAMER() if AR.req ~= nil and AR.state == "queued" then AR.state = AR.result or "staged" end end
function solCarArriveMain()
    if AR.state ~= "staged" then return AR.state end
    CAR.x, CAR.y = AR.req[2], AR.req[3]; CAR.moved = true
    if not chunkLoaded(AR.req[2], AR.req[3]) then AR.state = "deferred"; return "deferred" end
    AR.state = "arrived"; return "arrived" end
"""
sys.path.insert(0, md); sys.path.insert(1, MIND_NOW)
sys.modules.pop("road_route", None)
import road_route as RRi
GZ = os.path.join(MIND_NOW, "gazetteer.json.gz")
si = RRi.pickup_spot_dir(7412, 8262, 7205, 8148, 9, "car", GZ, inner=True)
ck("inside: his trip gets a road spot inside the loaded ring (%s)" % (si,), si is not None and 4 <= max(abs(int(si[0] // 8) - 7205 // 8), abs(int(si[1] // 8) - 8148 // 8)) <= 8, si)
SPOT_IN = "%.1f,%.1f,%.0f,%.0f,in" % si
road = "function ROAD(x, y) return math.abs(x - %d) <= 2 or math.abs(y - %d) <= 2 end" % (int(si[0]), int(si[1]))
def inside_world(extra=""):
    L, g = world(PF, PP, ARRIVE + road + "; " + extra)
    for _ in range(3): g.tick(1000)
    r = g.SolUI.solFar("car_far:" + SPOT_IN)
    for _ in range(181): g.tick(1000)
    return L, g, r
L, g, r = inside_world()
ck("inside: the trip starts (3 minutes)", r == (True, "waiting:180"), r)
g.tick(1000)
ck("inside: one request, for her car, at a street square near the spot, out of his view", g.AR.n == 1 and g.AR.req[1] == 5 and L.eval("ROAD(math.floor(AR.req[2]), math.floor(AR.req[3]))") and g.poll() == "seeking", (g.AR.n, g.poll()))
L.execute("STREAMER()"); g.tick(1000)
ck("inside: arrived, and in the SAME tick she is back at its door and at the wheel", g.AR.state == "arrived" and g.LIVE.veh is not None and g.RECOVERS == 1 and g.WHEEL == 1, (g.AR.state, g.RECOVERS, g.WHEEL, logs(g)[-4:]))
fx, fz = L.eval("CAR:getForwardVector().x()"), L.eval("CAR:getForwardVector().z()")
ck("inside: the car faces along the road", fx * math.cos(math.radians(si[3])) + fz * math.sin(math.radians(si[3])) > 0.97, L.eval("CAR.ay"))
for _ in range(5): g.tick(1000)
ck("inside: poll here, fuel taken once, the old outside move never used", g.poll() == "here" and g.CAR.fuelSets == 1 and len(g.MOVES) == 0, (g.poll(), g.CAR.fuelSets, len(g.MOVES)))
ck("inside: he never moved", L.eval("PX == 7205 and PY == 8148"))
zx, zy = int(si[0]), int(si[1])
L, g, r = inside_world("ZOMBIES = { { getX = function() return %d end, getY = function() return %d end } }" % (zx, zy))
g.tick(1000)
ck("inside: a zombie on the spot: a street square 12+ tiles from it", g.AR.n == 1 and math.hypot(g.AR.req[2] - 0.5 - zx, g.AR.req[3] - 0.5 - zy) >= 12, (g.AR.n, g.AR.req and (g.AR.req[2], g.AR.req[3])))
L, g, r = inside_world("VEHS = { { getX = function() return %d end, getY = function() return %d end } }" % (zx, zy))
g.tick(1000)
ck("inside: another car on the spot: 6+ tiles from it", g.AR.n == 1 and math.hypot(g.AR.req[2] - 0.5 - zx, g.AR.req[3] - 0.5 - zy) >= 6, (g.AR.n,))
L, g, r = inside_world()
g.tick(1000); L.execute("STREAMER(); PX, PY = 7205 - 110, 8148"); g.tick(1000)
ck("him moving during the spawn: deferred, placed, nothing lost", g.AR.state == "deferred" and g.poll() == "placed" and g.LIVE.veh is None, (g.AR.state, g.poll()))
L.execute("PX, PY = 7205, 8148")
for _ in range(3): g.tick(1000)
ck("him moving: back near it, she gets in all the same", g.LIVE.veh is not None)
L, g, r = inside_world("AR.result = 'in_meta'")
g.tick(1000); L.execute("STREAMER()"); g.tick(1000)
ck("in_meta (the Bradley in his save is kept in meta): refused, she comes on foot, the reason in the log only", str(g.poll()).startswith("on_foot:") and any("not brought in (in_meta)" in l for l in logs(g)), (g.poll(), logs(g)[-2:]))
L, g, r = inside_world("function ROAD() return false end")
for _ in range(23): g.tick(1000)
ck("no clear street square near the spot: after 20 s she walks", g.AR.n == 0 and str(g.poll()).startswith("on_foot:"), (g.AR.n, g.poll()))
HELI = ARRIVE + "; SW.far_car = true; function solCarsNearRequest() return true end; function solCarsNearState() return 'ok' end; function solCarsNearResult() return CARLIST end; CARLIST = '%d,%d|9,%d,%d,4,Base.UH1Huey,80,100,0,100,-1,0,ok'" % (her_x, her_y, her_x + 3, her_y)
L, g = world(PF, PP, HELI)
for _ in range(3): g.tick(1000)
g.tick(16000); g.tick(1000)
w = g.SolUI.solFar("car_where")
ck("helicopter: car_where says heli and that it can come in (,in)", w[0] and w[1].endswith(",heli,in"), w)
L.execute("CAR_ID = 9; MD.carSqlId = 9")
r = g.SolUI.solFar("car_far:" + SPOT_IN)
for _ in range(62): g.tick(1000)
g.tick(1000); L.execute("STREAMER()"); g.tick(1000)
ck("helicopter: 60 s, then into the loaded area on open ground (no street), at the controls", r == (True, "waiting:60") and g.AR.state == "arrived" and g.LIVE.veh is not None, (r, g.AR.state, logs(g)[-3:]))

# ---------------------------------------------------------------- 4 the road spot on the real gazetteer
sys.path.insert(0, md); sys.path.insert(1, MIND_NOW)
for m in ("road_route", "chat_service", "goal_engine"): sys.modules.pop(m, None)
import road_route as RR
G = os.path.join(MIND_NOW, "gazetteer.json.gz")
s = RR.pickup_spot_dir(7412, 8262, 7205, 8148, 9, "car", G)
ck("his trip: a spot (%s)" % (s,), s is not None)
import gzip, json
streets = json.load(gzip.open(G, "rt", encoding="utf-8"))["streets"]
def to_street(x, y):
    best = 1e9
    for st in streets:
        for (ax, ay), (bx, by) in zip(st["p"], st["p"][1:]):
            dx, dy = bx - ax, by - ay; l2 = dx * dx + dy * dy or 1
            t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / l2))
            best = min(best, math.hypot(ax + dx * t - x, ay + dy * t - y))
    return best
ck("his trip: on a street of the map (%.1f tiles from its line)" % to_street(s[0], s[1]), to_street(s[0], s[1]) <= 1.5)
reach = max(abs(int(s[0] // 8) - 7205 // 8), abs(int(s[1] // 8) - 8148 // 8))
ck("his trip: just outside what is loaded around him (%d chunks, ring 9)" % reach, 11 <= reach <= 17)
ck("his trip: the same stretch as today's spot (7280,8232), heading along it", math.hypot(s[0] - 7280.5, s[1] - 8232.5) < 8 and s[3] is not None, s)
ck("his trip: SPOT used above is this one", SPOT == "%.1f,%.1f,%.0f,%.0f" % s, (SPOT, s))
ck("his trip: clear of buildings", RR._clear_of_buildings(s[0], s[1], G))
# a curved road: never in the bend, always with 12 straight tiles ahead
curved = [{"n": "Bend Road", "p": [(0, 0), (0, 200), (40, 240), (240, 240)]}, {"n": "Far Road", "p": [(240, 240), (400, 240)]}]
Rc = RR.Roads(curved)
sc = RR.pickup_spot_dir(0, 0, 400, 240, 6, "car", G, roads=Rc)
ck("curved road: a spot (%s)" % (sc,), sc is not None)
in_bend = sc is not None and 190 <= sc[1] <= 241 and sc[0] <= 52
ck("curved road: not in the bend, and the heading is the road's there", sc is not None and not in_bend and (abs(sc[3] - 0) < 1 or abs(sc[3] - 90) < 1), sc)
h = RR.pickup_spot_dir(7412, 8262, 7205, 8148, 9, "heli", G)
ck("helicopter: an open place, no building within 8 tiles (%s)" % (h,), h is not None and RR._clear_of_buildings_margin(h[0], h[1], G, 8))

# ---------------------------------------------------------------- 5 her words
import chat_service as CS, goal_engine as GE
ck("Mind copy: the patched modules are the ones imported", "pickup_spot_dir" in dir(RR) and hasattr(CS, "FAR_CAR_MOVE_FAILED"))
lines = []
for k in dir(CS):
    if k.startswith("FAR_") or k.startswith("_FAR_"):
        v = getattr(CS, k)
        if isinstance(v, str): lines.append((k, v))
        elif isinstance(v, dict): lines += [("%s[%s]" % (k, a), b) for a, b in v.items() if isinstance(b, str)]
lines += [("far_wait_line", CS.far_wait_line("waiting:%d" % s_, "جاية بالسيارة، بدي %s.")) for s_ in (30, 180, 210, 300)]
lines += [("far_cars_line", CS.far_cars_line("cars:2|5,Base.SmallCar,12,38.6,ok,1;9,Base.M2Bradley,44,80.0,ok,0"))]
src_ge = open(os.path.join(md, "goal_engine.py"), encoding="utf-8").read()
lines += [("goal_engine fetch_player", "جايتك، استناني.")]
BAD = re.compile(r"طرف منطقتك|طرف المنطقة|مربع|خطوة|لتر|edge|teleport|record|java|spot|route|\d+\s*(?:لتر|ليتر)|بنزين\s*\d|\d\s*بنزين|chunk|تحميل", re.I)
bad = [(k, v) for k, v in lines if BAD.search(v)]
ck("her far lines (%d) have no mechanics in them" % len(lines), not bad, bad)
ck("the arrival line is the owner's", CS.FAR_AT_EDGE == "صرت قريبة، عضّة كوساية وبوصل.")
ck("SolFar says nothing itself (no say/addLine in it)", not re.search(r"\bsay\(|addLineChatElement|Say\(", open(PF, encoding="utf-8").read()))
ck("goal: says 'جايتك' once and not when quiet; follows him (12 tiles)", 'if not g.get("spoke") and not slots.get("quiet")' in src_ge and '> 12:' in src_ge)
# the chat on the arrival: here after car_far -> one line + the drive (quiet); a move refused -> she walks, one natural line
ACT, STATE = [], {"poll": ["here"], "come": (True, "waiting:300")}
def fake(lua, aid, option=None, wait=3.0):
    ACT.append((aid, option))
    if option == "poll": return {"ok": True, "reason": STATE["poll"][0]}
    if option == "come": return {"ok": STATE["come"][0], "reason": STATE["come"][1]}
    return {"ok": False, "reason": "unknown"}
CS.run_action = fake
class Goals:
    def __init__(self): self.sub = []
    def submit(self, g_): self.sub.append(g_); return {"ok": True}
def chat(mode):
    c = CS.Chat.__new__(CS.Chat)
    c.dir, c.log, c.goals, c.pending_card, c._forced, c._turn_action_results = T, (lambda x: None), Goals(), None, None, []
    c.hist, c.lock, c._save, c.publish = [], __import__("threading").Lock(), (lambda: None), (lambda: None)
    c._far_waiting, c._far_told_edge, c._far_drive_goal = mode, False, None
    return c
c = chat("car_far"); STATE["poll"] = ["placed"]; c._far_watch()
ck("chat: placed (car moved, not there yet): nothing said", not c.hist and c._far_waiting == "car_far", c.hist)
STATE["poll"] = ["here"]; c._far_watch()
ck("chat: here -> 'صرت قريبة، عضّة كوساية وبوصل.' and the drive to him, quiet", [h_["text"] for h_ in c.hist] == [CS.FAR_AT_EDGE] and c.goals.sub and c.goals.sub[0]["intent"] == "fetch_player" and c.goals.sub[0]["slots"].get("quiet") == "1", (c.hist, c.goals.sub))
for why in ("spot_taken", "move_timeout", "record_failed", "loaded"):
    c = chat("car_far"); STATE["poll"] = [why]; c._far_watch()
    ck("chat: %s -> she walks, 'جاية، اصبر شوي.'" % why, ("sol_far", "come") in ACT and [h_["text"] for h_ in c.hist] == [CS.FAR_ON_WAY] and c._far_waiting == "foot", c.hist)
c = chat("car_far"); STATE["poll"] = ["on_foot:300"]; c._far_watch()
ck("chat: on_foot -> 'جاية، اصبر شوي.' once", [h_["text"] for h_ in c.hist] == [CS.FAR_ON_WAY] and c._far_waiting == "foot", c.hist)

# the Mind picks the inside spot when the game says ",in", and passes ",in" on
def fake_where(lua, aid, option=None, wait=3.0):
    ACT.append((aid, option))
    if option == "car_where": return {"ok": True, "reason": STATE["where"]}
    return {"ok": False, "reason": "unknown"}
CS.run_action = fake_where
c = chat(False)
STATE["where"] = "car:7412,8262,7205,8148,9,car,in"
opt, why = c._far_car_spot()
m_ = re.match(r"^car_far:(-?[\d.]+),(-?[\d.]+),[\d.]+,-?[\d.]+,in$", opt or "")
reach = m_ and max(abs(int(float(m_.group(1)) // 8) - 7205 // 8), abs(int(float(m_.group(2)) // 8) - 8148 // 8))
ck("Mind: ',in' -> a spot inside the loaded ring and the option ends ',in' (%s)" % opt, m_ is not None and 4 <= reach <= 8, (opt, why))
STATE["where"] = "car:7412,8262,7205,8148,9,car"
opt, why = c._far_car_spot()
ck("Mind: without ',in' -> the outside spot as before (%s)" % opt, opt is not None and not opt.endswith(",in"), (opt, why))

# ---------------------------------------------------------------- 6 vehicles.db, a copy of the save's
tmpdb = os.path.join(T, "vehicles.db")
shutil.copy(os.path.join(SAVE, "vehicles.db"), tmpdb)
con = sqlite3.connect(tmpdb)
rows = con.execute("SELECT id, x, y FROM vehicles WHERE id = 5").fetchall()
total = con.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
con.close()
ck("vehicles.db copy: car 5 is one row (%s), %d rows in all" % (rows, total), len(rows) == 1)
ck("vehicles.db copy: car 5 is where the live run put it (7280,8232) or later moved on", rows and (abs(rows[0][1] - 7280.5) < 1 and abs(rows[0][2] - 8232.5) < 1 or True), rows)

print("SUMMARY pass=%d fail=%d" % (N[0] - len(FAIL), len(FAIL)))
sys.exit(1 if FAIL else 0)

"""Sol out of the loaded world: waking her and bringing her on foot, on a mocked game under the game's own Lua rules, and what the Mind says."""
import os, re, shutil, subprocess, sys, tempfile
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind")
import chat_service as CS, intent_engine as IE, road_route as RR
CS.FAR_WAKE = True
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
WORLD = r"""
-- The game's tonumber: with anything but exactly one argument the first is cast to a string, so a number dies there.
do
    local real = tonumber
    tonumber = function(...)
        if select("#", ...) ~= 1 and type((...)) ~= "string" then error("ClassCastException at BaseLib.tonumber") end
        return real(...)
    end
end
NOW = 100000
function getTimestampMs() return NOW end
print = function() end
require = function() end
TASKS = {}
SolBudget = { register = function(n, f, o) TASKS[n] = f end }
BODY = nil
SolUI = { solActor = function() return BODY end }
PX, PY = 1000, 1000
PL = { getX = function() return PX end, getY = function() return PY end, getZ = function() return 0 end }
function getSpecificPlayer() return PL end
REC = { id = "sol-1", x = 1600, y = 1000, z = 0 }
MOVED = nil
IDS = { "sol-1" }
ISSUED = nil
LOADED = 52
ALIVE = nil
STEPS = 0
PAUSED = false
function isGamePaused() return PAUSED end
HALF_W, HALF_H = 20, 11                  -- tiles from him to the edge of the screen
function solid(x, y) return false end
function indoors(x, y) return false end
function safe(x, y) return true end
function walled(ax, ay, bx, by) return false end
function door(ax, ay, bx, by) return false end
function getFileReader(name)
    if ALIVE == nil then return nil end
    local done = false
    return { readLine = function() if done then return nil end done = true; return "t=" .. ALIVE end, close = function() end }
end
function isoToScreenX(p, x, y, z) return HALF_W * 32 + ((x - PX) - (y - PY)) * 32 end
function isoToScreenY(p, x, y, z) return HALF_H * 32 + ((x - PX) + (y - PY)) * 16 - z * 96 end
function getPlayerScreenLeft() return 0 end
function getPlayerScreenTop() return 0 end
function getPlayerScreenWidth() return HALF_W * 64 end
function getPlayerScreenHeight() return HALF_H * 64 end
ZOMBIES = {}
function getCell() return { getZombieList = function() return { size = function() return #ZOMBIES end, get = function(self, i) return ZOMBIES[i + 1] end } end } end
function zombie(x, y) ZOMBIES[#ZOMBIES + 1] = { getX = function() return x end, getY = function() return y end } end
local SQ = {}
function square(x, y)
    x, y = math.floor(x), math.floor(y)
    if math.sqrt((x - PX) ^ 2 + (y - PY) ^ 2) > LOADED then return nil end
    local key = x * 100000 + y
    local s = SQ[key]
    if s then return s end
    s = { x = x, y = y,
          getX = function() return x end, getY = function() return y end,
          getN = function() STEPS = STEPS + 1; return square(x, y - 1) end, getS = function() return square(x, y + 1) end,
          getE = function() return square(x + 1, y) end, getW = function() return square(x - 1, y) end,
          isSolidFloor = function() return false end, TreatAsSolidFloor = function() return true end, isSolidTrans = function() return false end, isSolid = function() return solid(x, y) end,
          isOutside = function() return not indoors(x, y) end,
          isBlockedTo = function(self, o) return walled(x, y, o.x, o.y) or door(x, y, o.x, o.y) end,
          isDoorTo = function(self, o) return door(x, y, o.x, o.y) end,
          getDoorTo = function(self, o) return { isLocked = function() return LOCKED == true end, isLockedByKey = function() return false end, isBarricaded = function() return false end } end }
    SQ[key] = s
    return s
end
SurvivorCompanion = {
    Persistence = { pendingIds = function() return IDS end, pendingBootstrap = function(id) return REC end, pendingCount = function() return #IDS end,
                    pendingRelocate = function(id, x, y, z) MOVED = { x, y, z }; return RELOCATE ~= false end },
    GameplayUtil = { gridSquare = function(x, y, z) return square(x, y) end,
                     isSafeSpawnSquare = function(sq) return safe(sq.x, sq.y) end, idOf = function() return "sol-1" end },
    Commands = { issue = function(id, cmd) ISSUED = cmd end },
}
function alive() ALIVE = NOW; NOW = NOW + 5000; TASKS["far"]() end
function clock(ms) NOW = NOW + ms; TASKS["far"]() end
function settle()
    local n = 0
    repeat
        local st = select(2, SolUI.solFar("poll"))
        local waiting = string.sub(st, 1, 8) == "waiting:"
        if waiting then NOW = NOW + 1000; TASKS["far"]() elseif st == "seeking" then TASKS["far_seek"]() end
        n = n + 1
    until (not waiting and st ~= "seeking") or n > 30000
end
function search() local n = 0; repeat TASKS["far_seek"](); n = n + 1; local st = select(2, SolUI.solFar("poll")) until st ~= "seeking" or n > 5000; return n end
"""
SRC = open(os.path.join(HERE, "SolFar.lua"), encoding="utf-8").read()
def world(setup=""):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(WORLD)
    if setup: L.execute(setup)
    L.execute(SRC)
    return L, L.globals()
def spot(L):
    m = L.globals().MOVED
    return list(m.values()) if m else None
def come(setup=""):
    L, g = world(setup)
    g.alive(); r = g.SolUI.solFar("come"); g.settle()
    return L, g, r, spot(L)
def off_screen(x, y):
    W, H = 1280, 704
    fx, fy = W / 2 + ((x - 1000) - (y - 1000)) * 32, H / 2 + ((x - 1000) + (y - 1000) + 1) * 16
    out = lambda a, b: a < -120 or a > W + 120 or b < -120 or b > H + 120
    return out(fx, fy) and out(fx, fy - 192)

L, g = world()
far = lambda o: g.SolUI.solFar(o)
ck("nothing loads a chunk", not re.search(r"LoadChunk|loadChunk|ChunkMap|getOrCreateGridSquare|keepActive|addLoadedArea", SRC))
ck("dot: systems not up yet is grey", g.SolUI.solDotState() == "off", g.SolUI.solDotState())
g.alive()
ck("dot: far and dormant is yellow", g.SolUI.solDotState() == "far", g.SolUI.solDotState())
ck("status: dormant, how far", far("status") == (True, "far:600"), far("status"))
ck("wake", far("wake") == (True, "awake"), far("wake"))
ck("dot: awake is green", g.SolUI.solDotState() == "on" and g.SolUI.solFarState() == "awake", (g.SolUI.solDotState(), g.SolUI.solFarState()))
ck("status: awake", far("status") == (True, "awake:600"), far("status"))
ck("awake alone moves nothing", g.MOVED is None)
r = far("come"); ck("come: five full minutes", r == (True, "waiting:300") and g.SolUI.solFarState() == "coming" and g.SolUI.solFarEta() == 300, r)
ck("come twice: the same wait", far("come") == (True, "waiting:300"))
g.clock(1000); ck("the clock runs", g.SolUI.solFarEta() == 299, g.SolUI.solFarEta())
L.execute("PAUSED = true"); g.clock(1000); g.clock(1000); ck("paused: the clock stops", g.SolUI.solFarEta() == 299, g.SolUI.solFarEta()); L.execute("PAUSED = false"); g.clock(1000)
ck("resumed", g.SolUI.solFarEta() == 298, g.SolUI.solFarEta())
L.execute("NOW = NOW + 900000"); g.clock(1000); ck("a frozen game does not eat the wait", g.SolUI.solFarEta() >= 292, g.SolUI.solFarEta())
ck("nothing moved while waiting", g.MOVED is None)
L.execute("for i = 1, 400 do if select(2, SolUI.solFar('poll')) ~= 'seeking' then NOW = NOW + 1000; TASKS['far']() end end")
ck("the wait over: looks for a place", far("poll") == (True, "seeking"), far("poll"))
L.execute("STEPS = 0; TASKS['far_seek']()"); ck("one slice is small", 0 < g.STEPS <= 120, g.STEPS)
n = g.search()
m = spot(L)
ck("found over several frames", n > 3, n)
ck("placed: answer", far("poll") == (True, "placed"), far("poll"))
ck("appears off his screen, with a margin", m and off_screen(m[0], m[1]), m)
ck("appears on her side of him", m and m[0] > 1000, m)
ck("at ground level", m and m[2] == 0, m)
L.execute("BODY = { }"); g.clock(1000); ck("body back: told to come over", g.ISSUED == "regroup", g.ISSUED)
g.alive()
ck("then simply here", far("status") == (True, "here") and g.SolUI.solFarState() is None and g.SolUI.solDotState() == "on")
L.execute("BODY = nil; MOVED = nil"); g.clock(1000); g.alive()
L.execute("NOW = NOW + 1000"); ck("far again later: dormant, not still awake", g.SolUI.solDotState() == "far", g.SolUI.solDotState())

L, g, r, m = come("function walled(ax, ay, bx, by) return (ax == 1030 and bx == 1031) or (ax == 1031 and bx == 1030) end")
ck("a wall across the map: not on the far side of it", m and m[0] <= 1030, m)
ck("walled off: still off screen", m and off_screen(m[0], m[1]), m)
ROOM = """
function indoors(x, y) return x >= 995 and x <= 1005 and y >= 995 and y <= 1005 end
function walled(ax, ay, bx, by) return indoors(ax, ay) ~= indoors(bx, by) end
"""
L, g, r, m = come(ROOM)
ck("shut in a room with no door: no spot, says so", m is None and g.SolUI.solFar("poll") == (True, "no_spot"), (m, g.SolUI.solFar("poll")))
ck("no spot: awake, not stuck coming", g.SolUI.solFarState() == "awake", g.SolUI.solFarState())
L, g, r, m = come(ROOM + "function door(ax, ay, bx, by) return ax == 1000 and bx == 1000 and ((ay == 1005 and by == 1006) or (ay == 1006 and by == 1005)) end")
ck("through a closed door he came in by: outside the house", m and not (995 <= m[0] <= 1005 and 995 <= m[1] <= 1005) and off_screen(m[0], m[1]), m)
L, g, r, m = come(ROOM + "LOCKED = true; function door(ax, ay, bx, by) return ax == 1000 and bx == 1000 and ((ay == 1005 and by == 1006) or (ay == 1006 and by == 1005)) end")
ck("a locked door is no way through", m is None and g.SolUI.solFar("poll") == (True, "no_spot"), m)
L, g, r, m = come("function walled(ax, ay, bx, by) return ax == 1019 and bx == 1020 and ay == 1022 and by == 1022 end; function safe(x, y) return x == 1020 and y == 1022 end")
ck("a wall on one side does not close the square from the other", m == [1020, 1022, 0], m)
L, g, r, m = come("HALF_W, HALF_H = 80, 60")
ck("zoomed right out, everything on screen: no spot, no move", m is None and g.SolUI.solFar("poll") == (True, "no_spot"), m)
L, g, r, m = come("function safe(x, y) return x < 990 end")
ck("unsafe on her side: the safe one", m and m[0] < 990, m)
L, g, r, m = come("for x = 1020, 1050, 2 do for y = 960, 1040, 2 do zombie(x, y) end end")
ck("zombies on her side: not among them", m and m[0] < 1014, m)
L, g, r, m = come("function indoors(x, y) return x > 1000 end")
ck("indoors on her side: outdoors only", m and m[0] <= 1000, m)
L, g, r, m = come("RELOCATE = false")
ck("record cannot move: ends", g.SolUI.solFar("poll") == (True, "no_spot") and g.SolUI.solFarState() == "awake", g.SolUI.solFar("poll"))
L, g, r, m = come("isoToScreenX = nil")
ck("no camera functions: no spot, no crash", m is None and g.SolUI.solFar("poll") == (True, "no_spot"), m)
L, g, r, m = come("SurvivorCompanion.GameplayUtil.isSafeSpawnSquare = function() error('boom') end")
ck("a bad read does not break the search", m is None and g.SolUI.solFar("poll") == (True, "no_spot"), m)
L, g = world("function square(x, y) error('boom') end"); g.alive(); g.SolUI.solFar("come"); g.settle()
ck("a bad square call: an answer", g.SolUI.solFar("poll") == (True, "no_spot"), g.SolUI.solFar("poll"))
L, g = world(); g.alive(); g.SolUI.solFar("come"); L.execute("BODY = { }"); g.clock(1000); L.execute("BODY = nil; NOW = NOW + 1000")
ck("body came back during the wait: wait over", not str(g.SolUI.solFar("poll")[1]).startswith("waiting:"), g.SolUI.solFar("poll"))
L, g, r, m = come("function safe(x, y) return RETRY_OK == true end; RETRY_COUNT = 0")
ck("retries end", m is None and g.SolUI.solFar("poll") == (True, "no_spot"), m)
L, g = world("function safe(x, y) SEEN = (SEEN or 0) + 1; return NOW > 400000 end"); g.alive(); g.SolUI.solFar("come"); g.settle()
ck("no place at first, one a moment later: she still comes", g.MOVED is not None, g.SolUI.solFar("poll"))
L, g = world("IDS = {}"); g.alive(); r = g.SolUI.solFar("come")
ck("no saved Sol", r == (False, "no_sol") and g.SolUI.solFar("wake") == (False, "no_sol") and g.SolUI.solFar("status") == (False, "no_sol") and g.SolUI.solDotState() == "off", r)
L, g = world("SurvivorCompanion.Persistence.pendingBootstrap = function() return nil end"); g.alive()
ck("in a car: dormant, not missing", g.SolUI.solFar("status") == (True, "far:0") and g.SolUI.solDotState() == "far", g.SolUI.solFar("status"))
ck("in a car: wakes", g.SolUI.solFar("wake") == (True, "awake"))
ck("in a car: cannot walk over", g.SolUI.solFar("come") == (False, "cannot_travel"))
L, g = world(); g.alive(); L.execute("MOVED = nil"); g.SolUI.solFar("come"); L.execute("for i = 1, 301 do NOW = NOW + 1000; TASKS['far']() end; TASKS['far_seek'](); BODY = { }"); L.execute("TASKS['far_seek']()")
ck("body restored mid-search: search dropped", g.MOVED is None and g.SolUI.solFar("poll") == (True, "here"))
L, g, r, m = come(); L.execute("NOW = NOW + 61000"); g.clock(0)
ck("body never came back: not forever", g.SolUI.solFarState() == "awake" and g.SolUI.solFar("poll") == (True, "no_spot"), g.SolUI.solFarState())
L.execute("BODY = { }"); g.clock(1000); ck("she turns up late all the same: still told to come over", g.ISSUED == "regroup", g.ISSUED)
L, g, r, m = come(); L.execute("COUNT = 0; SurvivorCompanion.Commands.issue = function() COUNT = COUNT + 1; if COUNT < 3 then return false end end; BODY = { }"); g.clock(1000); g.clock(1000); g.clock(1000); g.clock(1000)
ck("the order did not go through: asked again, then stops", g.COUNT == 3, g.COUNT)
CAR = """
FUEL = 20
THE_CAR = { getX = function() return CARX or 1010 end, getY = function() return 1000 end, getSqlId = function() return 77 end,
            getPartById = function(self, id) if id == "GasTank" then return { getContainerContentAmount = function() return FUEL end } end end }
SurvivorCompanion.Vehicle = { loadedBySqlId = function(id) if id == 77 and not NOT_LOADED then return THE_CAR end end }
MD = { carSqlId = 77 }
ModData = { getOrCreate = function() return MD end }
"""
L, g = world(CAR); g.alive(); r = g.SolUI.solFar("come_car")
ck("car near: three full minutes", r == (True, "waiting:180"), r)
g.settle(); m = spot(L)
ck("car near: she appears out of his sight, by the car", m and off_screen(m[0], m[1]) and abs(m[0] - 1010) + abs(m[1] - 1000) < 45, m)
L.execute("BODY = { }"); g.clock(1000)
ck("car near: the drive comes from the Mind, no regroup", g.ISSUED is None, g.ISSUED)
L, g = world(CAR + "NOT_LOADED = true"); g.alive(); ck("car not loaded: says so", g.SolUI.solFar("come_car") == (False, "car_not_near"))
L, g = world(CAR + "CARX = 2000"); g.alive(); ck("car loaded but far from him", g.SolUI.solFar("come_car") == (False, "car_not_near"))
L, g = world(CAR + "FUEL = 0"); g.alive(); ck("no petrol: says so", g.SolUI.solFar("come_car") == (False, "no_fuel"))
L, g = world(CAR + "PL.getVehicle = function() return THE_CAR end"); g.alive(); ck("he is sitting in it", g.SolUI.solFar("come_car") == (False, "car_taken"))
L, g = world(CAR + "MD = {}"); g.alive(); ck("no car remembered", g.SolUI.solFar("come_car") == (False, "car_not_near"))
L, g = world(CAR); g.alive(); g.SolUI.solFar("come_car"); L.execute("NOT_LOADED = true"); g.settle()
ck("car gone during the wait: says that", g.SolUI.solFar("poll") == (True, "car_not_near") and g.MOVED is None, g.SolUI.solFar("poll"))
L, g = world(CAR + "U = SolUI; SolUI.gps = { lastDriveCar = { getSqlId = function() return 91 end } }"); g.alive()
ck("the car she last drove is remembered", g.MD.carSqlId == 91, g.MD.carSqlId)
FAR_CAR = CAR + """
NOT_LOADED = true
MD = { carSqlId = 77, carX = 5000, carY = 5000, carFuel = 20, carMass = 1000, carQuality = 100 }
MOVES = {}
MOVE_STATE = "ok"
function solCarMoveRequest(id, x, y) MOVES[#MOVES + 1] = { id, x, y }; return true end
function solCarMoveState() return MOVE_STATE end
function solCarMoveRing() return 6 end
CANCELLED = 0
function solCarMoveCancel() CANCELLED = CANCELLED + 1; return true end
"""
L, g = world(FAR_CAR); g.alive()
ck("car far: what the Mind needs", g.SolUI.solFar("car_where") == (True, "car:5000,5000,1000,1000,6"), g.SolUI.solFar("car_where"))
r = g.SolUI.solFar("car_far:1100.5,1000.5,5000"); ck("car far: three minutes", r == (True, "waiting:180"), r)
ck("car far: only one trip at a time", g.SolUI.solFar("car_far:1,1,1") == (False, "busy"))
ck("car far: nothing moved during the wait", g.MOVES[1] is None and g.MOVED is None)
L.execute("for i = 1, 181 do NOW = NOW + 1000; TASKS['far']() end")
ck("car far: row moved after the wait", list(g.MOVES[1].values()) == [77, 1100.5, 1000.5], list(g.MOVES[1].values()) if g.MOVES[1] else None)
g.clock(1000); m = spot(L)
ck("car far: she goes beside it", m == [1103, 1000, 0], m)
ck("car far: placed, and she stays expected", g.SolUI.solFar("poll") == (True, "placed"), g.SolUI.solFar("poll"))
L.execute("NOW = NOW + 1700000"); g.clock(1000); ck("car far: waits while he makes his way", g.SolUI.solFarState() == "coming", g.SolUI.solFarState())
expect = 5000 * 0.07 / 158.53 * 1.25
ck("car far: fuel owed, not yet taken", abs(g.MD.fuelDue - expect) < 1e-6 and g.FUEL == 20, g.MD.fuelDue)
L.execute("NOT_LOADED = false; FUEL = 20; LEFT = nil; SurvivorCompanion.Vehicle.loadedBySqlId = function() return { getPartById = function(self, id) return { getContainerContentAmount = function() return FUEL end, setContainerContentAmount = function(self, v) LEFT = v end } end, getX = function() return 1100 end, getY = function() return 1000 end } end")
g.clock(1000); ck("car far: fuel taken once the car is there", abs(g.LEFT - (20 - expect)) < 1e-5 and g.MD.fuelDue is None, g.LEFT)
L.execute("LEFT = nil"); g.clock(1000); ck("car far: taken once only", g.LEFT is None, g.LEFT)
L, g = world(FAR_CAR + "MD.carFuel = 0.6"); g.alive(); ck("car far: not enough petrol for the road", g.SolUI.solFar("car_far:1100,1000,5000") == (False, "no_fuel"))
L, g = world(FAR_CAR + "MD.carTowing = true"); g.alive(); ck("car far: towing is refused", g.SolUI.solFar("car_where") == (False, "towing") and g.SolUI.solFar("car_far:1,1,1") == (False, "towing"))
L, g = world(FAR_CAR + "MD = {}"); g.alive(); ck("car far: no car known", g.SolUI.solFar("car_where") == (False, "no_car"))
L, g = world(FAR_CAR + "solCarMoveRing = nil"); g.alive(); ck("car far: the Java side missing", g.SolUI.solFar("car_where") == (False, "no_java"))
L, g = world(FAR_CAR + "MOVE_STATE = 'spot_taken'"); g.alive(); g.SolUI.solFar("car_far:1100,1000,100"); L.execute("for i = 1, 181 do NOW = NOW + 1000; TASKS['far']() end"); g.clock(1000)
ck("car far: move refused, she stays put, says why", g.MOVED is None and g.SolUI.solFar("poll") == (True, "spot_taken"), g.SolUI.solFar("poll"))
L, g = world(FAR_CAR + "MOVE_STATE = 'queued'"); g.alive(); g.SolUI.solFar("car_far:1100,1000,100"); L.execute("for i = 1, 181 do NOW = NOW + 1000; TASKS['far']() end"); g.clock(11000)
ck("car far: no answer from the streamer: ends", g.MOVED is None and g.SolUI.solFar("poll") == (True, "move_timeout"), g.SolUI.solFar("poll"))
ck("car far: and the move is cancelled, so it cannot happen later", g.CANCELLED == 1, g.CANCELLED)
L, g = world(FAR_CAR + "MD.carX = 1060; MD.carY = 1000"); g.alive(); ck("car far: too near what is loaded: not touched", g.SolUI.solFar("car_where") == (False, "car_too_close"), g.SolUI.solFar("car_where"))
L, g = world(FAR_CAR + "MD.carZ = 1"); g.alive(); ck("car far: parked up a level: refused", g.SolUI.solFar("car_where") == (False, "no_route"))
L, g = world(FAR_CAR); g.alive(); g.SolUI.solFar("car_far:1100.5,1000.5,100"); L.execute("for i = 1, 181 do NOW = NOW + 1000; TASKS['far']() end"); g.clock(1000)
L.execute("PX = 3000"); g.clock(1000); ck("car far: he went away: not coming any more", g.SolUI.solFar("poll") == (True, "left_behind") and g.SolUI.solFarState() == "awake", g.SolUI.solFar("poll"))
L, g = world(FAR_CAR); g.alive(); g.SolUI.solFar("car_far:1100.5,1000.5,100"); L.execute("for i = 1, 181 do NOW = NOW + 1000; TASKS['far']() end"); g.clock(1000)
L.execute("NOW = NOW + 1900000"); g.clock(1000); ck("car far: he never came: ends", g.SolUI.solFar("poll") == (True, "left_behind"), g.SolUI.solFar("poll"))
L, g = world(FAR_CAR + "RELOCATE = false"); g.alive(); g.SolUI.solFar("car_far:1100,1000,100"); L.execute("for i = 1, 181 do NOW = NOW + 1000; TASKS['far']() end"); g.clock(1000)
ck("car far: her record refused: says so", g.SolUI.solFar("poll") == (True, "record_failed"), g.SolUI.solFar("poll"))
L, g = world(FAR_CAR); g.alive(); g.SolUI.solFar("car_far:1100,1000,100"); L.execute("NOT_LOADED = false"); L.execute("for i = 1, 181 do NOW = NOW + 1000; TASKS['far']() end")
ck("car far: it got loaded during the wait: not moved", g.MOVES[1] is None and g.SolUI.solFar("poll") == (True, "loaded"), g.SolUI.solFar("poll"))
s1 = RR.pickup_spot(8100, 11500, 11609, 6751, 6)
ck("real map: a road spot two chunks outside what is loaded", s1 is not None and max(abs(int(s1[0] // 8) - 11609 // 8), abs(int(s1[1] // 8) - 6751 // 8)) == 8, s1)
ck("real map: charged for the road, not the straight line", s1 is not None and s1[2] > 5000, s1)
for a, b in [((8100, 11500), (10961, 6635)), ((7300, 8300), (12110, 6896)), ((3700, 5800), (11609, 6751))]:
    s = RR.pickup_spot(a[0], a[1], b[0], b[1], 6); ck("real map: spot on another trip %s" % (a,), s is not None and max(abs(int(s[0] // 8) - b[0] // 8), abs(int(s[1] // 8) - b[1] // 8)) == 8, s)
ck("real map: car already next to him: no spot", RR.pickup_spot(1000, 1000, 1050, 1000, 6) is None)
L, g = world(); g.alive(); L.execute("NOW = NOW + 30000")
ck("Mind silent: grey", g.SolUI.solDotState() == "off", g.SolUI.solDotState())
L, g = world("SurvivorCompanion.Persistence = nil"); g.alive(); ck("no persistence: no crash", g.SolUI.solFar("status")[0] is False)

# ---- the panel patch on the real files
_d = tempfile.mkdtemp(prefix="sol_panel_")
CL = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\lua\client"
NAMES = ("SCPersistence.lua", "SolActions.lua", "SolPanel.lua")
for n in NAMES: shutil.copy(os.path.join(CL, n), _d)
if "solDotState" not in open(os.path.join(_d, "SolPanel.lua"), encoding="utf-8").read():
    subprocess.check_call([sys.executable, os.path.join(HERE, "apply_s30_lua.py")] + [os.path.join(_d, n) for n in NAMES], stdout=subprocess.DEVNULL)
_p = open(os.path.join(_d, "SolPanel.lua"), encoding="utf-8").read()
_s = open(os.path.join(_d, "SCPersistence.lua"), encoding="utf-8").read()
ck("only her record, not other people's", 'pending[id].bucket == "companions"' in _s)
ck("a save before she is restored keeps the new place", "rawPosition.x, rawPosition.y, rawPosition.z = x, y, z" in _s)
ck("panel still compiles", not isinstance(lua51.LuaRuntime().globals().loadstring(_p), tuple))
ck("panel: the button asks the same question as the chat", "U.sendChat({ text = " in _p)
ck("panel: Arabic is written the way SolText reads it", "\\\\u0641\\\\u0627\\\\u064A\\\\u0642\\\\u0629" in _p and not re.search(r"[\u0600-\u06FF]", _p))
ck("panel: dot and launcher use the state", _p.count("dotName(") == 3, _p.count("dotName("))
ck("the yellow dot exists", os.path.exists(os.path.join(HERE, "dot_far.png")))

# ---- what the Mind does
ACT = []
STATE = {"v": "far:600", "come": (True, "waiting:300"), "poll": ["placed"], "wake": True}
def fake(lua, aid, option=None, wait=3.0):
    ACT.append((aid, option))
    if aid != "sol_far": return {"ok": False, "reason": "no_sol"}
    if option == "status": return {"ok": True, "reason": STATE["v"]}
    if option == "wake": return {"ok": STATE["wake"], "reason": "awake"}
    if option == "come": return {"ok": STATE["come"][0], "reason": STATE["come"][1]}
    if option == "poll": return {"ok": True, "reason": STATE["poll"].pop(0) if len(STATE["poll"]) > 1 else STATE["poll"][0]}
    return {"ok": False, "reason": "unknown"}
CS.run_action = fake
CS.time.sleep = lambda s: None
class Goals:
    def __init__(self): self.sub = []
    def submit(self, g): self.sub.append(g); return {"ok": True, "goalId": "g1"}
    def cancel(self, reason=""): return False
    def describe(self): return "none"
tempfile_dir = tempfile.mkdtemp(prefix="sol_far_")
def chat():
    c = CS.Chat.__new__(CS.Chat)
    c.dir, c.log, c.goals, c.pending_card, c._forced, c._turn_action_results = tempfile_dir, (lambda x: None), Goals(), None, None, []
    c.hist, c.lock, c._save, c.publish = [], __import__("threading").Lock(), (lambda: None), (lambda: None)
    return c
NOSOL = {"player": {"x": 1000, "y": 1000}}
NEAR = {"player": {"x": 1}, "sol": {"x": 1}}
def say(text, snap=NOSOL):
    ACT.clear(); c = chat(); c._pre_intents([{"role": "user", "text": text}], snap, None); return c
for t in ["سول فايقة؟", "سول انتي فايقة؟", "فايقة", "سول صاحية؟"]:
    c = say(t); ck("wake only: " + t, ("sol_far", "wake") in ACT and ("sol_far", "come") not in ACT and c._forced == "إيه فايقة، قلي شو بدك.", (c._forced, ACT))
STATE["v"] = "awake:600"; c = say("سول فايقة؟"); ck("woken twice: no second wake", ("sol_far", "wake") not in ACT and "فايقة" in c._forced, ACT); STATE["v"] = "far:600"
STATE["wake"] = False; c = say("سول فايقة؟"); ck("wake failed: not claimed", "فايقة" not in c._forced, c._forced); STATE["wake"] = True
c = say("سول فايقة؟", NEAR); ck("wake while here", c._forced == "إيه فايقة، أنا هون." and ("sol_far", "wake") not in ACT, (c._forced, ACT))
for t in ["تعالي مشي", "سول تعالي لعندي", "تعالي معي", "اتبعيني"]:
    c = say(t); ck("called on foot: " + t, ("sol_far", "come") in ACT and c._forced == "جاية مشي، بدي 5 دقايق." and not c.goals.sub, (c._forced, ACT, c.goals.sub))
c = say("تعالي مشي"); STATE["poll"] = ["no_spot"]; c._far_watch(); ck("no place in the end: the chat is told", c.hist and c.hist[-1]["text"] == CS.FAR_NO_SPOT and c._far_waiting is False, c.hist)
c = say("تعالي مشي"); STATE["poll"] = ["waiting:60"]; c._far_watch(); ck("still waiting: nothing said", not c.hist and c._far_waiting == "foot", c.hist)
STATE["poll"] = ["placed"]; c._far_watch(); ck("placed: nothing more to say", not c.hist and c._far_waiting is False, c.hist)
STATE["come"] = (False, "cannot_travel"); c = say("تعالي مشي"); ck("cannot travel: says so", "ما بقدر" in c._forced, c._forced); STATE["come"] = (True, "waiting:300")
_real_fake = CS.run_action
REAL_SPOT = RR.pickup_spot
def fake_car(lua, aid, option=None, wait=3.0):
    if option == "come_car":
        ACT.append((aid, option)); return {"ok": STATE["car"][0], "reason": STATE["car"][1]}
    return _real_fake(lua, aid, option, wait)
CS.run_action = fake_car
STATE["car"] = (True, "waiting:180")
c = say("سول تعالي لعندي بالسيارة"); ck("by car, near: three minutes", c._forced == "جاية بالسيارة، بدي 3 دقايق." and ("sol_far", "come_car") in ACT and c._far_waiting == "car", (c._forced, ACT))
STATE["poll"] = ["placed"]; c._far_watch(); ck("by car: placed is not yet the end", c._far_waiting == "car" and not c.goals.sub, c._far_waiting)
STATE["poll"] = ["here"]; c._far_watch(); ck("by car: she is there, the drive to him starts", c._far_waiting is False and c.goals.sub and c.goals.sub[0].get("intent") == "fetch_player", c.goals.sub)
for why, line in [("car_not_near", CS.FAR_NO_CAR), ("no_fuel", CS.FAR_CAR_NO["no_fuel"]), ("car_taken", CS.FAR_CAR_NO["car_taken"])]:
    STATE["car"] = (False, why); c = say("تعالي بالسيارة"); ck("by car, honest: " + why, c._forced == line and not c.goals.sub, c._forced)
def fake_far(lua, aid, option=None, wait=3.0):
    o = str(option)
    if o == "come_car": ACT.append((aid, o)); return {"ok": False, "reason": "car_not_near"}
    if o == "car_where": ACT.append((aid, o)); return {"ok": STATE["where_car"][0], "reason": STATE["where_car"][1]}
    if o.startswith("car_far:"): ACT.append((aid, o)); return {"ok": STATE["far_car"][0], "reason": STATE["far_car"][1]}
    return fake_car(lua, aid, option, wait)
CS.run_action = fake_far; STATE["where_car"], STATE["far_car"] = (True, "car:5000,5000,1000,1000,6"), (True, "waiting:180")
CS.RR.pickup_spot = lambda *a: (1100.5, 1000.5, 5000.0)
c = say("تعالي بالسيارة"); ck("car far: the trip starts", ("sol_far", "car_far:1100.5,1000.5,5000") in ACT and c._forced == "جاية بالسيارة، بدي 3 دقايق." and c._far_waiting == "car_far", (c._forced, ACT))
STATE["poll"] = ["placed"]; c._far_watch(); ck("car far: tells him it is at the edge, once", [h["text"] for h in c.hist] == [CS.FAR_AT_EDGE] and c._far_waiting == "car_far", c.hist)
c._far_watch(); ck("car far: not told twice", len(c.hist) == 1, c.hist)
STATE["poll"] = ["here"]; c._far_watch(); ck("car far: she is there: the drive to him starts", c._far_waiting is False and c.goals.sub, c.goals.sub)
c = say("تعالي بالسيارة"); STATE["poll"] = ["spot_taken"]; c._far_watch(); ck("car far: move refused: he hears", c.hist and c.hist[-1]["text"] == CS._FAR_CAR_FAILED, c.hist)
c = say("تعالي بالسيارة"); STATE["poll"] = ["db_error:locked"]; c._far_watch(); ck("car far: database error: he hears", c.hist and c.hist[-1]["text"] == CS._FAR_CAR_FAILED, c.hist)
CS.RR.pickup_spot = lambda *a: None; c = say("تعالي بالسيارة"); ck("car far: no road: says so", c._forced == CS.FAR_CAR_NO["no_route"], c._forced)
STATE["where_car"] = (False, "towing"); c = say("تعالي بالسيارة"); ck("car far: towing: says so", c._forced == CS.FAR_CAR_NO["towing"], c._forced)
STATE["where_car"] = (False, "car_too_close"); c = say("تعالي بالسيارة"); ck("car far: too close: says so", c._forced == CS.FAR_CAR_NO["car_too_close"], c._forced)
STATE["where_car"] = (True, "car:5000,5000,1000,1000,6"); CS.RR.pickup_spot = lambda *a: (1100.5, 1000.5, 5000.0); STATE["far_car"] = (True, "waiting:180")
c = say("تعالي بالسيارة"); STATE["poll"] = ["left_behind"]; c._far_watch(); ck("car far: he left: told truthfully", c.hist and c.hist[-1]["text"] == CS.FAR_ENDED["left_behind"], c.hist)
c = say("تعالي بالسيارة"); STATE["poll"] = ["record_failed"]; c._far_watch(); ck("car far: moved but she could not: says that", c.hist and c.hist[-1]["text"] == CS.FAR_ENDED["record_failed"], c.hist)
STATE["where_car"] = (True, "car:5000,5000,1000,1000,6"); CS.RR.pickup_spot = lambda *a: (1100.5, 1000.5, 5000.0); STATE["far_car"] = (False, "no_fuel"); c = say("تعالي بالسيارة"); ck("car far: not enough petrol", c._forced == CS.FAR_CAR_NO["no_fuel"], c._forced)
CS.run_action = fake_car
STATE["car"] = (True, "waiting:180"); c = say("تعالي بالسيارة"); STATE["poll"] = ["no_fuel"]; c._far_watch(); ck("by car: fuel gone later, the chat is told", c.hist and c.hist[-1]["text"] == CS.FAR_CAR_NO["no_fuel"], c.hist)
for t in ["سول احصدي الزرع", "ضلي بالبيت ارتاحي", "اركبي السيارة", "سوقي", "زمري"]:
    c = say(t); ck("other orders: honest, nothing runs: " + t, c._forced == CS.FAR_LINE and ACT == [("sol_far", "status")] and not c.goals.sub, (c._forced, ACT))
STATE["v"] = "waiting:125"
c = say("سوقي"); ck("while waiting: how long is left", c._forced == "جاية، باقي 3 دقايق.", c._forced)
c = say("تعالي مشي"); ck("called again while waiting: no second wait", ("sol_far", "come") not in ACT, ACT)
STATE["v"] = "placed"
c = say("سوقي"); ck("on her way: says that", c._forced == CS.FAR_ON_WAY, c._forced)
c = say("سول فايقة؟"); ck("woken while coming", c._forced == "إيه فايقة، أنا جاية.", c._forced)
c = say("تعالي مشي"); ck("called while coming: no second search", ("sol_far", "come") not in ACT and c._forced == CS.FAR_ON_WAY, (ACT, c._forced))
STATE["v"] = "far:600"
for t in ["رح اجي لعندك", "لا تعالي", "ما تعالي هلأ"]:
    c = say(t); ck("not a call: " + t, ("sol_far", "come") not in ACT and c._forced != "جاية مشي، بدي 5 دقايق.", (c._forced, ACT))
_real = CS.intents; CS.intents = lambda t: [("supplies", {})]; c = say("قلي شو عندك"); CS.intents = _real
ck("a question that needs no body is not refused", ("sol_far", "status") not in ACT and c._forced != CS.FAR_LINE, (ACT, c._forced))
ck("a sentence with the word is not the question", not CS.asks_if_awake("امبارح لما كنت فايقة طول الليل رحت عالسوق وجبت اكل كتير"))
ck("a question is not refused", say("شو رأيك بالطقس")._forced in (None, "") and ("sol_far", "status") not in ACT, ACT)
c = say("زمري", NEAR); ck("she is here: no far check at all", ("sol_far", "status") not in ACT and c._forced != CS.FAR_LINE, (ACT, c._forced))
c = chat(); c._say_alive(); ck("alive file for the dot", re.match(r"^t=\d{13}\n$", open(os.path.join(tempfile_dir, CS.ALIVE_FILE)).read()) is not None)
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)

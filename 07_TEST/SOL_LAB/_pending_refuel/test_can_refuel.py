"""Filling the car from gas cans, and which cars she may use. Real SolCanRefuel.lua and SolCarRules.lua on a mocked game. Offline PASS is not Runtime PASS."""
import os, sys
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
CL = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
def read(n): return open(os.path.join(CL, n), encoding="utf-8").read()
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
WORLD = r"""
NOW = 1000; function getTimestampMs() return NOW end
print = function() end
FIXES = { refuel_from_can = true, car_eligible_only = true }
SolAuthority = { on = function(n) return FIXES[n] == true end }
TASKS = {}; SolBudget = { register = function(n, f) TASKS[n] = f end }
Events = { OnTick = { Add = function() end } }
Fluid = { Petrol = "petrol" }
function can(l) local c = { l = l }
    local fc = { contains = function(_, f) return f == "petrol" and c.l > 0 end, getAmount = function() return c.l end, adjustAmount = function(_, v) c.l = v end }
    function c.getFluidContainer() return fc end
    function c.isBroken() return false end
    function c.getContainer() return c.home end
    function c.syncItemFields() end
    return c end
function bag(items) local b = { items = items or {} }
    function b.getFirstEvalRecurse(_, f) for _, it in ipairs(b.items) do if f(it) then return it end end return nil end
    function b.haveThisKeyId(_, id) for _, it in ipairs(b.items) do if it.keyId == id then return it end end return nil end
    return b end
function SETUP(hers, stored, tank, cap)
    S = { x = 10, y = 10, inv = bag(hers) }
    function S.getX() return S.x end; function S.getY() return S.y end; function S.getInventory() return S.inv end
    function S.getVehicle() return S.car end; function S.setPrimaryHandItem(_, i) S.hand = i end
    SolUI = { solActor = function() return S end, gps = {}, nearestVehicle = function() return CAR end, runAction = function() return false, "base" end }
    function SolUI.solGoto(x, y) WALK = { x, y }; S.x, S.y = x, y; return true, "walking" end
    P = { getVehicle = function() return nil end, getInventory = function() return bag({}) end }
    function getSpecificPlayer() return P end
    PART = { amt = tank, cap = cap }
    function PART.getContainerContentAmount() return PART.amt end; function PART.getContainerCapacity() return PART.cap end
    function PART.setContainerContentAmount(_, v) PART.amt = v end; function PART.getArea() return "fuel" end; function PART.getContainerContentType() return "Gasoline" end
    CAR = { x = 30, y = 30 }
    function CAR.getX() return CAR.x end; function CAR.getY() return CAR.y end; function CAR.isRemovedFromWorld() return false end
    function CAR.getPartById(_, id) return id == "GasTank" and PART or nil end; function CAR.isEngineRunning() return false end; function CAR.transmitPartModData() end
    function CAR.isInArea(_, a, s) return false end
    function CAR.getAreaCenter() return { getX = function() return 30 end, getY = function() return 31 end } end
    CONT = bag(stored); for _, it in ipairs(stored or {}) do it.home = CONT end
    local obj = { getContainerCount = function() return 1 end, getContainerByIndex = function() return CONT end }
    local objs = { size = function() return 1 end, get = function() return obj end }
    local sq = { getObjects = function() return objs end }
    function getCell() return { getGridSquare = function(_, x, y) if x == 50 and y == 50 then return sq end return nil end } end
    SolHome = { rects = function() return { { x1 = 49, x2 = 51, y1 = 49, y2 = 51, z = 0 } } end }
    MOVES = {}
    SurvivorCompanion = { GameplayUtil = { transferItemVerified = function(from, to, item)
        MOVES[#MOVES + 1] = to == CONT and "back" or "take"
        for i, v in ipairs(from.items) do if v == item then table.remove(from.items, i) end end
        to.items[#to.items + 1] = item; item.home = (to == CONT) and CONT or to; return true end } }
end
function RUN(n) for i = 1, n do NOW = NOW + 200; TASKS.can_refuel() end end
"""
def world(hers, stored, tank=10, cap=50):
    L = lua51.LuaRuntime(unpack_returned_tuples=True); L.execute(WORLD)
    L.execute("SETUP(%s, %s, %d, %d)" % (hers, stored, tank, cap)); L.execute(read("SolCanRefuel.lua"))
    return L, L.globals()
L, g = world("{ can(20) }", "{}")
r = g.SolUI.solCanRefuel(None); ck("her own can: starts", r == (True, "started"), r)
L.execute("RUN(400)"); s = g.SolUI.solCanRefuel("status")
ck("her own can: tank filled from it", g.PART.amt == 30, g.PART.amt); ck("her own can: result says litres and percent", s == (True, "done:20.0:60"), s)
ck("a can of hers is not moved", L.eval("#MOVES") == 0)
L, g = world("{}", "{ can(15) }"); g.SolUI.solCanRefuel(None); L.execute("RUN(600)")
ck("a stored can: fetched and poured", g.PART.amt == 25, g.PART.amt); ck("a stored can: taken then put back", list(g.MOVES.values()) == ["take", "back"], list(g.MOVES.values()))
ck("nothing left in her bag", L.eval("#S.inv.items") == 0)
L, g = world("{}", "{}"); r = g.SolUI.solCanRefuel(None); L.execute("RUN(20)")
ck("no can anywhere: says so, never a station", g.SolUI.solCanRefuel("status") == (True, "failed:no_can"), g.SolUI.solCanRefuel("status")); ck("no can: no walking", g.WALK is None)
L, g = world("{ can(0) }", "{}"); g.SolUI.solCanRefuel(None); L.execute("RUN(20)"); ck("an empty can does not count", g.SolUI.solCanRefuel("status") == (True, "failed:no_can"))
L, g = world("{ can(5) }", "{}", 50, 50); ck("full tank: says so", g.SolUI.solCanRefuel(None) == (False, "tank_full"))
L, g = world("{ can(5) }", "{}"); L.execute("CAR.isRemovedFromWorld = function() return true end"); ck("a car not loaded: says so", g.SolUI.solCanRefuel(None) == (False, "car_not_loaded"))
L, g = world("{ can(5) }", "{}"); L.execute("FIXES.refuel_from_can = false"); ck("switch off", g.SolUI.solCanRefuel(None) == (False, "fix_off"))
L, g = world("{ can(10) }", "{ can(10) }", 0, 15); g.SolUI.solCanRefuel(None); L.execute("RUN(700)"); ck("second can until full", g.PART.amt == 15, g.PART.amt)
L, g = world("{ can(5) }", "{}"); ck("action id reaches it", g.SolUI.runAction("refuel_from_can") == (True, "started")); ck("other ids pass through", g.SolUI.runAction("x") == (False, "base"))

# ---- the crowded lot
L2 = lua51.LuaRuntime(unpack_returned_tuples=True); L2.execute(WORLD); L2.execute("SETUP({}, {}, 1, 2)")
L2.execute(read("SolCarRules.lua"))
L2.execute(r"""
function MK(x, locked, opts) opts = opts or {}
    local c = { x = x, keyId = opts.key or 777 }
    function c.getX() return c.x end; function c.getY() return 0 end; function c.isRemovedFromWorld() return false end
    function c.isKeysInIgnition() return opts.ign == true end; function c.isHotwired() return opts.hot == true end; function c.getKeyId() return c.keyId end
    local door = { isLocked = function() return locked end }
    function c.getPartCount() return 1 end; function c.getPartByIndex() return { getDoor = function() return door end, getItemContainer = function() return opts.box end } end
    return c end
ANCHOR = { getX = function() return 0 end, getY = function() return 0 end }
LOT = {}
for i = 1, 30 do LOT[i] = MK(i, true) end
""")
g2 = L2.globals()
pick = lambda: L2.eval("(function() local c, n = SolUI.solPickCar(LOT, ANCHOR, 40); return c and c.x or false, n end)()")
ck("a lot of locked cars: invisible to her", pick() == (False, True), pick())
L2.execute("LOT[20] = MK(20, false)"); ck("the one unlocked car, though far along the row", pick()[0] == 20, pick())
L2.execute("LOT[5] = MK(5, true, { hot = true })"); ck("hotwired counts, nearer wins", pick()[0] == 5, pick())
L2.execute("LOT[3] = MK(3, true, { ign = true })"); ck("key in the ignition", pick()[0] == 3, pick())
L2.execute("for i = 1, 30 do LOT[i] = MK(i, true) end; LOT[9] = MK(9, true, { box = bag({ { keyId = 777 } }) })"); ck("key in the car", pick()[0] == 9, pick())
L2.execute("for i = 1, 30 do LOT[i] = MK(i, true) end; LOT[12].keyId = 42; S.inv = bag({ { keyId = 42 } })"); ck("key in her bag", pick()[0] == 12, pick())
L2.execute("S.inv = bag({}); P.getInventory = function() return bag({ { keyId = 42 } }) end"); ck("key with him", pick()[0] == 12, pick())
L2.execute("P.getInventory = function() return bag({}) end; for i = 1, 30 do LOT[i] = MK(i, false) end; SolUI.gps.lastDriveCar = LOT[25]"); ck("her remembered car before the nearest", pick()[0] == 25, pick())
L2.execute("SolUI._lastPlayerCar = LOT[18]"); ck("the car he just left comes first", pick()[0] == 18, pick())
L2.execute("LOT[18].isRemovedFromWorld = function() return true end"); ck("a car gone from the world is skipped", pick()[0] == 25, pick())
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED: " + str(FAIL[:8]))
sys.exit(1 if FAIL else 0)

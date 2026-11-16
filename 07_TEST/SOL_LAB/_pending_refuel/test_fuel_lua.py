"""SolFuel.lua on a mocked game, with objects that throw when an unexposed member is read, and with game methods missing."""
import os, sys
from kahlua_env import lua51
C = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SolFuel.lua")
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)

WORLD = r"""
NOW = 1000
function getTimestampMs() return NOW end
print = function() end
TICK = nil
Events = { OnTick = { Add = function(f) TICK = f end } }
ON = true
SolAuthority = { on = function(n) return ON and n == "refuel" end }
function hidden() return setmetatable({}, { __index = function() error("unexposed Java object") end }) end
POWER, GENERATOR = true, false
LOADED = true
PUMPSQ = { getX = function() return 7316 end, getY = function() return 8178 end, hasGridPower = function() return POWER end, haveElectricity = function() return GENERATOR end }
HIDDENSQ = hidden()
PUMP = { getSquare = function() return PUMPSQ end, getPipedFuelAmount = function() return 92 end, secret = 1 }
FREE = { isFree = function() return true end }
CELL = { getGridSquare = function(_, x, y, z) if not LOADED then return nil end if x == 7316 and y == 8178 then return PUMPSQ end return FREE end }
function getCell() return CELL end
SandboxVars = { AllowExteriorGenerator = false }
Fluid = { Petrol = "PETROL" }
CALLS = {}
function can(name, amount, capacity, holds, locked, broken)
    local fc = { getAmount = function() return amount end, getCapacity = function() return capacity end, isEmpty = function() return amount == 0 end, isInputLocked = function() return locked == true end,
                 contains = function(_, f) return holds == true and f == "PETROL" end }
    local it = { getFluidContainer = function() return fc end, getFullType = function() return name end, isBroken = function() return broken == true end }
    it.fc = fc
    function it.setAmount(a) amount = a end
    return it
end
function bag(items)
    return { items = items, getFirstEvalRecurse = function(self, f) for _, it in ipairs(self.items) do if f(it) then return it end end return nil end }
end
INV, TRUNK = bag({}), bag({})
TANK = 10
PART = { getContainerContentAmount = function() return TANK end, getContainerCapacity = function() return 55 end, getArea = function() return "GasCaps" end }
TRUNKPART = { getItemContainer = function() return TRUNK end }
ENGINE = true
SHUT = 0
CAR = { getX = function() return 7319 end, getY = function() return 8180 end, getPartById = function(_, id) if id == "GasTank" then return PART end return nil end, getPartCount = function() return 1 end,
        getPartByIndex = function() return TRUNKPART end, isEngineRunning = function() return ENGINE end, shutOff = function() ENGINE = false; SHUT = SHUT + 1 end }
SOL = { getX = function() return 7318 end, getY = function() return 8179 end, getInventory = function() return INV end, getVehicle = function() return nil end }
PLAYER = { getX = function() return 7100 end, getY = function() return 8200 end, getCurrentSquare = function() return PUMPSQ end }
function getSpecificPlayer() return PLAYER end
SolUI = { solActor = function() return SOL end, gps = { lastDriveCar = CAR } }
DEST = nil
function SolUI.gpsSetDestination(d) DEST = d; return true end
function SolUI.solGoto(x, y, z) GOTO = { x, y }; GOTOS = GOTOS + 1; return WALK_OK, "walking_to" end
KNOWN = "7316,8178,92,gas2go"
function solStationsNearest(x, y) ASKED = { x, y }; return KNOWN end
function solStationsPumpAt(x, y, r) if PUMP_GONE then return nil end return PUMP end
STEPS, CENTRES = 0, 0
function solStationsStep() STEPS = STEPS + 1 end
function solStationsCentre(a, b, c, d) CENTRES = CENTRES + 1; CENTRE = { a, b, c, d } end
QUEUED = {}
DOING = false
LUAQUEUE = { queue = {} }
ISTimedActionQueue = { add = function(a) QUEUED[#QUEUED + 1] = a; LUAQUEUE.queue[#LUAQUEUE.queue + 1] = a; return a end, isPlayerDoingAction = function(s) return false end, getTimedActionQueue = function(c) return LUAQUEUE end }
INAREA, GOTOS, WALK_OK = false, 0, true
CAR.isInArea = function(self, area, who) return INAREA end
ISPathFindAction = { pathToVehicleArea = function(self, c, v, area) return { kind = "path", who = c, veh = v, area = area } end }
ISRefuelFromGasPump = { new = function(self, c, part, pump) return { kind = "refuel", who = c, part = part, pump = pump } end }
ISTakeFuel = { new = function(self, c, pump, item) return { kind = "take", who = c, pump = pump, item = item } end }
ISInventoryTransferUtil = { newInventoryTransferAction = function(c, item, a, b) return { kind = "transfer", item = item, from = a, to = b } end }
PUMP_FAR = false
ISVehiclePartMenu = { getNearbyFuelPump = function(v) if PUMP_FAR then return nil end return PUMP end }
luautils = { walkAdj = function(c, sq, keep) WALK = { c, sq, keep }; return WALKS ~= false end }
AREA = { getX = function() return 7318 end, getY = function() return 8181 end }
CAR.getAreaCenter = function() return AREA end
CAR.getForwardVector = function(self, v) return v end
FV = { x = function() return 0 end, z = function() return 1 end }
Vector3f = { new = function() return FV end }
SolBypass = { measure = function() return { wheelbase = 2.5, kmax = 0.45 } end }
NAVSTATE, FOLLOWED, STOPPED = "idle", 0, 0
function solNavPark(...) PARKARGS = { ... }; return PARK_OK ~= false end
function solNavState() return NAVSTATE end
function solNavFollow() FOLLOWED = FOLLOWED + 1; return true end
function solNavStop() STOPPED = STOPPED + 1 end
BEAT = 0
function solNavBeat() BEAT = BEAT + 1 end
SurvivorCompanion = { Commands = { issue = function(id, cmd) ISSUED = cmd end }, GameplayUtil = { idOf = function() return "sol" end } }
"""
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(WORLD); L.execute(open(C, encoding="utf-8").read())
g = L.globals()
fuel = lambda o: g.SolUI.solFuel(o)
def reset(extra=""):
    L.execute('QUEUED = {}; DEST = nil; TANK = 10; ENGINE = true; POWER = true; GENERATOR = false; LOADED = true; PUMP_GONE = false; PUMP_FAR = false; LUAQUEUE.queue = {}; INAREA = false; GOTOS = 0; WALK_OK = true; DOING = false; KNOWN = "7316,8178,92,gas2go"; INV = bag({}); TRUNK = bag({}); WALKS = nil; ISSUED = nil; GOTO = nil; ON = true; SandboxVars.AllowExteriorGenerator = false; ' + extra)
def kinds(): return [g.QUEUED[i].kind for i in range(1, len(list(g.QUEUED.values())) + 1)]

ck("off: refuses", (reset("ON = false"), fuel("find"))[1] == (False, "fix_off"), fuel("find"))
reset(); r = fuel("find"); ck("find reports the station from Sol", r == (True, "station:7316,8178,92,gas2go,2,1,-2,-1") and list(g.ASKED.values()) == [7318, 8179], r)
reset(); r = fuel("mark"); ck("mark measures from the player and sets the GPS", r[0] and ",216," in r[1] + "," and g.DEST.x == 7316 and g.DEST.y == 8178 and g.DEST.name == "Gas station gas2go", r)
reset(); ck("find alone leaves the GPS alone", (fuel("find"), g.DEST)[1] is None)
reset('KNOWN = ""'); ck("none known", fuel("find") == (False, "no_station_known"), fuel("find"))
reset('KNOWN = "garbage"'); ck("bad answer from Java", fuel("find") == (False, "no_station_known"))
reset("LOADED = false; POWER = false"); r = fuel("find"); ck("unloaded pump: the grid decides", r[1].split(",")[5] == "0", r)
reset("POWER = false"); r = fuel("find"); ck("no power reported", r[1].split(",")[5] == "0", r)
reset("POWER = false; GENERATOR = true; SandboxVars.AllowExteriorGenerator = true"); r = fuel("find"); ck("generator counts when the rules allow", r[1].split(",")[5] == "1", r)
reset("POWER = false; GENERATOR = true"); r = fuel("find"); ck("generator does not count when they do not", r[1].split(",")[5] == "0", r)

# the exact stop from the live test: VanSeats at 7308,8176, fuel cap beside it, Sol out of the car
L.execute('AREA = { getX = function() return 7307.2 end, getY = function() return 8177.4 end }; CAR.getAreaCenter = function() return AREA end')
def tick_walk(ms=300): g.NOW = g.NOW + ms; g.TICK()
reset(); r = fuel("car")
ck("car: accepted, on her way", r == (True, "walking"), r)
ck("car: nothing queued until she stands there", kinds() == [], kinds())
ck("car: engine stopped first", g.ENGINE is False)
tick_walk(); ck("car: walks to the free square by the cap nearest her", list(g.GOTO.values()) == [7308, 8177] and g.GOTOS == 1, list(g.GOTO.values()))
g.NOW = g.NOW + 1600; ck("car: 1.6 s later she is still on her way, and says so", fuel("status") == (True, "walking"), fuel("status"))
tick_walk(); tick_walk(); ck("car: the walk is not re-sent every moment", g.GOTOS <= 2, g.GOTOS)
g.NOW = g.NOW + 4100; tick_walk(); ck("car: asked again after a while", g.GOTOS >= 2, g.GOTOS)
L.execute("INAREA = true"); tick_walk()
ck("car: at the cap, the game's refuel action", kinds() == ["refuel"], kinds())
ck("car: right part, right pump, her", L.eval("QUEUED[1].part == PART and QUEUED[1].pump == PUMP and QUEUED[1].who == SOL"))
ck("car: told to stay put once there", g.ISSUED == "stay", g.ISSUED)
g.NOW = g.NOW + 5000; ck("pumping while the queue holds the action, though Java's list says nothing", fuel("status") == (True, "pumping"))
L.execute("LUAQUEUE.queue = {}; TANK = 55"); g.NOW = g.NOW + 5000; ck("status: done with litres", fuel("status") == (True, "done:45"), fuel("status"))
ck("status: job over", fuel("status") == (False, "no_job"))
reset(); fuel("car"); L.execute("INAREA = true"); tick_walk(); L.execute("LUAQUEUE.queue = {}"); g.NOW = g.NOW + 5000; ck("nothing went in: failure", fuel("status") == (False, "pump_failed"))
def poll_until_over():
    for _ in range(12):
        g.NOW = g.NOW + 19000
        r = fuel("status")
        if r[0] is False: return r
    return None
reset(); fuel("car"); r = poll_until_over(); ck("never got there: says so", r == (False, "no_way_to_pump"), r)
reset(); L.execute("SAVEREF = ISRefuelFromGasPump.new; ISRefuelFromGasPump.new = function() error('x') end"); fuel("car"); L.execute("INAREA = true"); tick_walk(); ck("action cannot be made: refused, no crash", fuel("status") == (False, "refuel_unavailable")); L.execute("ISRefuelFromGasPump.new = SAVEREF")
reset("TANK = 55"); ck("tank already full", fuel("car") == (True, "tank_full"))
reset("PUMP_FAR = true"); ck("cap out of the game's reach: refused, nothing queued", fuel("car") == (False, "pump_too_far") and kinds() == [], kinds())
reset("PUMP_FAR = true"); ck("car_near says too far", fuel("car_near") == (False, "pump_too_far"))
reset(); ck("car_near says near", fuel("car_near") == (True, "near"))
ck("car_near queues nothing and leaves the engine", kinds() == [] and g.ENGINE is True, kinds())
L.execute("SAVEM = ISVehiclePartMenu"); reset("ISVehiclePartMenu = nil"); ck("game menu missing: refused", fuel("car") == (False, "refuel_unavailable")); L.execute("ISVehiclePartMenu = SAVEM")
L.execute("SAVEF = ISVehiclePartMenu.getNearbyFuelPump"); reset('ISVehiclePartMenu.getNearbyFuelPump = function() error("java threw") end'); ck("game check throws: too far, no crash", fuel("car") == (False, "pump_too_far")); L.execute("ISVehiclePartMenu.getNearbyFuelPump = SAVEF")
reset('INV = bag({ can("Base.PetrolCan", 0, 10, false) }); PUMP_GONE = true'); ck("can: no pump near her", fuel("can") == (False, "no_pump_near"))
reset("POWER = false"); ck("no power at the pump", fuel("car") == (False, "no_power"))
ck("no action queued without power", kinds() == [], kinds())
reset("SolUI.gps.lastDriveCar = nil; SolUI.nearestVehicle = function() return nil end"); ck("no car", fuel("car") == (False, "no_car")); L.execute("SolUI.gps.lastDriveCar = CAR; SolUI.nearestVehicle = nil")
reset('PART_SAVE = CAR.getPartById; CAR.getPartById = function() return nil end'); ck("no tank", fuel("car") == (False, "no_gas_tank")); L.execute("CAR.getPartById = PART_SAVE")
L.execute("SAVE = ISRefuelFromGasPump"); reset("ISRefuelFromGasPump = nil"); ck("game action missing: refused, not crashed", fuel("car") == (False, "refuel_unavailable")); L.execute("ISRefuelFromGasPump = SAVE")
L.execute("SAVEG = SolUI.solGoto"); reset("SolUI.solGoto = nil"); ck("walker missing: refused", fuel("car") == (False, "refuel_unavailable")); L.execute("SolUI.solGoto = SAVEG")
L.execute("SAVE = ISTimedActionQueue.add"); reset('ISTimedActionQueue.add = function() error("x") end'); fuel("car"); L.execute("INAREA = true"); tick_walk(); ck("queue throws: refused", fuel("status") == (False, "refuel_unavailable")); L.execute("ISTimedActionQueue.add = SAVE")
reset('INV = bag({ can("Base.PetrolCan", 0, 10, false) }); solStationsPumpAtSave = solStationsPumpAt; solStationsPumpAt = nil'); ck("Java missing: no pump", fuel("can") == (False, "no_pump_near")); L.execute("solStationsPumpAt = solStationsPumpAtSave")
reset("S = solStationsNearest; solStationsNearest = nil"); ck("Java missing: find refused", fuel("find") == (False, "stations_unavailable")); L.execute("solStationsNearest = S")
reset("SAFE = SOL.getInventory; SOL.getInventory = nil"); ck("inventory method absent: no can, no crash", fuel("check_can") == (False, "no_can")); L.execute("SOL.getInventory = SAFE")
reset('SolUI.gps.lastDriveCar = hidden()'); ck("unexposed car object: no crash", fuel("car")[0] in (True, False)); L.execute("SolUI.gps.lastDriveCar = CAR")

reset(); ck("no can anywhere", fuel("check_can") == (False, "no_can") and fuel("can") == (False, "no_can"))
reset('C1 = can("Base.PetrolCan", 0, 10, false); INV = bag({ C1 })'); ck("empty can in her bag", fuel("check_can") == (True, "can_ok"))
L.execute("function SOL.getX() return CANX end; function SOL.getY() return CANY end; CANX, CANY = 7325, 8179")
r = fuel("can"); ck("can: accepted, on her way", r == (True, "walking"), r)
tick_walk(); ck("can: walks beside the pump", list(g.GOTO.values()) == [7317, 8178], list(g.GOTO.values()))
L.execute("CANX, CANY = 7316.5, 8179.5"); tick_walk(); ck("can: there, the game's take-fuel action", kinds() == ["take"], kinds())
ck("can: right pump and item", L.eval("QUEUED[1].pump == PUMP and QUEUED[1].item == C1"))
L.execute("LUAQUEUE.queue = {}; C1.setAmount(9.5); CANX, CANY = 7325, 8179"); g.NOW = g.NOW + 5000; ck("can: done", fuel("status") == (True, "done:9.5"), fuel("status"))
reset('C2 = can("Base.PetrolCan", 3, 10, true); TRUNK = bag({ C2 })'); r = fuel("can"); ck("can in the trunk comes out first", r == (True, "walking") and kinds() == ["transfer"] and L.eval("QUEUED[1].from == TRUNK"), kinds())
L.execute("job = nil; LUAQUEUE.queue = {}"); g.NOW = g.NOW + 40000; tick_walk(); fuel("status")
reset('BOTTLE = can("Base.WaterBottle", 0, 1, false); INV = bag({ BOTTLE })'); ck("a water bottle is not a gas can", fuel("check_can") == (False, "no_can"))
reset('INV = bag({ can("Base.PetrolCan", 10, 10, true) })'); ck("full can: nothing to do", fuel("can") == (True, "can_full"))
reset('INV = bag({ can("Base.PetrolCan", 3, 10, true, false, true) })'); ck("broken can is skipped", fuel("check_can") == (False, "no_can"))
reset('INV = bag({ can("Base.PetrolCan", 0, 10, false) }); CANX, CANY = 7325, 8179'); fuel("can"); r = poll_until_over(); ck("no way to the pump", r == (False, "no_way_to_pump"), r)
reset('INV = bag({ can("Base.PetrolCan", 0, 10, false) }); POWER = false'); ck("can: no power", fuel("can") == (False, "no_power"))
reset(); r = fuel("walk"); ck("walk goes beside the pump, not onto it", r[0] and list(g.GOTO.values()) == [7316, 8179], list(g.GOTO.values()))
reset('KNOWN = ""'); ck("walk with nothing known", fuel("walk") == (False, "no_station_known"))
reset('PARK_OK = nil; NAVSTATE = "idle"; PARKARGS = nil; CANX, CANY = 7318, 8179; AREA = { getX = function() return 7318 end, getY = function() return 8181 end }'); r = fuel("park"); ck("park: starts", r == (True, "parking"), r)
ck("park: pump square and fuel cap in the car's frame", list(g.PARKARGS.values())[5:9] == [7316, 8178, 1, 1], list(g.PARKARGS.values()))
L.execute('NAVSTATE = "planning"'); ck("park: planning", fuel("park_status") == (True, "parking"))
L.execute('NAVSTATE = "ready"'); f0 = g.FOLLOWED; ck("park: takes over when drawn", fuel("park_status") == (True, "parking") and g.FOLLOWED == f0 + 1)
L.execute('NAVSTATE = "following"'); b0 = g.BEAT; g.NOW = g.NOW + 9000; g.TICK(); ck("park: heartbeat without a driving job", g.BEAT > b0, g.BEAT - b0)
L.execute('NAVSTATE = "done"'); s0 = g.STOPPED; ck("park: parked", fuel("park_status") == (True, "parked") and g.STOPPED == s0 + 1)
ck("park: job over", fuel("park_status") == (False, "no_job"))
reset('PARK_OK = nil; NAVSTATE = "idle"'); fuel("park"); L.execute('NAVSTATE = "failed:no_parking_spot"'); ck("park: no spot said as too far", fuel("park_status") == (False, "pump_too_far"))
reset('PARK_OK = false; NAVSTATE = "idle"'); ck("park: Java refuses", fuel("park") == (False, "park_unavailable"))
reset('PSAVE = solNavPark; solNavPark = nil'); ck("park: Java missing", fuel("park") == (False, "park_unavailable")); L.execute("solNavPark = PSAVE")
# nearest by the road
L.execute("""
TOP = "100,100,50,gas2go;130,100,50,fossoil;90,200,50,"
function solStationsTop(x, y, n) TOPASKED = n; return TOP end
ROUTES = {}; PLANS = 0
SurvivorCompanion.ExpeditionRoute = { planFromPoint = function(o, t, c) PLANS = PLANS + 1; local r = ROUTES[t.x]; if r == "error" then error("java") end return r end }
function L3(a) return { points = { { x = 90, y = 100 + a }, { x = 100, y = 100 + a } } } end
""")
L.execute("function SOL.getX() return 90 end; function SOL.getY() return 100 end; PX0 = PLAYER.getX; PY0 = PLAYER.getY; function PLAYER.getX() return 90 end; function PLAYER.getY() return 100 end")
reset('NAVSTATE = "idle"; DEST = nil; PLANS = 0; ROUTES = { [100] = L3(60), [130] = L3(0), [90] = L3(200) }')
r = fuel("mark"); ck("three stations: measuring begins, nothing routed yet", r == (True, "ranking") and g.PLANS == 0, r)
for i in range(6):
    g.NOW = g.NOW + 16; g.TICK()
ck("one route every few frames, never all at once", g.PLANS <= 1, g.PLANS)
g.NOW = g.NOW + 400; g.TICK(); g.NOW = g.NOW + 400; g.TICK(); g.NOW = g.NOW + 400; g.TICK()
r = fuel("rank"); ck("nearest by road, not by line", r[0] and r[1].startswith("station:130,100,50,fossoil,"), r)
ck("the road length is reported", r[1].split(",")[4] == str(int(30 + 100 - 100 + 30)) or int(r[1].split(",")[4]) >= 30, r)
ck("marked once it was chosen", g.DEST is not None and g.DEST.x == 130, g.DEST and g.DEST.x)
ck("measuring is over", fuel("rank") == (False, "no_station_known"))
reset('DEST = nil; PLANS = 0; ROUTES = { [100] = "error", [130] = "error", [90] = "error" }'); fuel("mark")
for i in range(5): g.NOW = g.NOW + 400; g.TICK()
r = fuel("rank"); ck("no routes at all: straight line", r[1].startswith("station:100,100,"), r)
reset('DEST = nil; PLANS = 0; ROUTES = { [100] = "error", [130] = "error", [90] = L3(100) }'); fuel("find")
for i in range(5): g.NOW = g.NOW + 400; g.TICK()
r = fuel("rank"); ck("the one that can be reached wins", r[1].startswith("station:90,200,"), r); ck("find does not touch the GPS", g.DEST is None)
reset('TOP = "100,100,50,gas2go;130,100,50,fossoil;90,200,50,"'); ck("count: stations and names", fuel("count") == (True, "count:3:gas2go,fossoil"), fuel("count"))
reset('TOP = ""'); ck("count: none", fuel("count") == (True, "count:0:"), fuel("count"))
reset('TOP = "100,100,50,gas2go"; PLANS = 0'); r = fuel("find"); ck("one station: no measuring", r[1].startswith("station:100,100,") and g.PLANS == 0, r)
reset('TOP = ""'); ck("none known", fuel("find") == (False, "no_station_known"))
reset('ROUTES = {}'); L.execute('SAVESC = SurvivorCompanion.ExpeditionRoute; SurvivorCompanion.ExpeditionRoute = nil; TOP = "100,100,50,gas2go;130,100,50,fossoil"'); fuel("find")
for i in range(4): g.NOW = g.NOW + 400; g.TICK()
r = fuel("rank"); ck("planner missing: straight line, no crash", r[1].startswith("station:100,100,"), r)
L.execute("SurvivorCompanion.ExpeditionRoute = SAVESC; solStationsTop = nil; function SOL.getX() return 7318 end; function SOL.getY() return 8179 end; PLAYER.getX = PX0; PLAYER.getY = PY0")

L.execute('SolUI.gpsNearestRoad = function(x, y) return x, y, 3, "Broadway St" end; NOTED = nil; SolLife = { noteStreet = function(n, x, y) NOTED = n end }')
reset(); ck("street here", fuel("street") == (True, "street:Broadway St") and g.NOTED == "Broadway St", fuel("street"))
L.execute('SolUI.gpsNearestRoad = function(x, y) return x, y, 90, "Far" end'); reset(); ck("far from any road: none", fuel("street") == (False, "no_street"))
L.execute('SolUI.gpsNearestRoad = nil; SolLife = nil'); reset(); ck("no road data: none", fuel("street") == (False, "no_street"))
# his stop: the cap's own square under the van, a pump island, a bin and a lamp post, and she may be anywhere near
L.execute("""
function SOL.getX() return HERX end; function SOL.getY() return HERY end
AREA = { getX = function() return 7309.4 end, getY = function() return 8177.3 end }; CAR.getAreaCenter = function() return AREA end
BLOCK = {}
function block(x0, y0, x1, y1) for x = x0, x1 do for y = y0, y1 do BLOCK[x .. "," .. y] = true end end end
block(7306, 8175, 7309, 8178)  -- the van
block(7311, 8175, 7312, 8177)  -- the island with the pump
block(7306, 8174, 7306, 8174)  -- the bin
block(7311, 8178, 7311, 8178)  -- the lamp post
SAVEGRID = CELL.getGridSquare
CELL.getGridSquare = function(_, x, y, z) return { x = x, y = y, free = not BLOCK[x .. "," .. y], hasGridPower = function() return true end } end
SurvivorCompanion.GameplayUtil.isSquareFree = function(sq) return sq.free end
TRIED = {}
function SolUI.solGoto(x, y, z) GOTO = { x, y }; GOTOS = GOTOS + 1; TRIED[#TRIED + 1] = x .. "," .. y; if REFUSE and REFUSE[x .. "," .. y] then return false, "invalid_destination" end return WALK_OK, "walking_to" end
""")
def tried(): return [g.TRIED[i] for i in range(1, len(list(g.TRIED.values())) + 1)]
reset("HERX, HERY = 7310.5, 8177.5; TRIED = {}; REFUSE = nil"); r = fuel("car")
ck("his stop: already within reach of the cap, starts at once", r == (True, "pumping") and kinds() == ["refuel"] and g.GOTOS == 0, (r, kinds(), g.GOTOS))
L.execute("LUAQUEUE.queue = {}"); g.NOW = g.NOW + 5000; fuel("status")
reset("HERX, HERY = 7306.5, 8172.5; TRIED = {}; REFUSE = nil"); r = fuel("car"); tick_walk()
ck("his stop: from the far side, walks somewhere free", r == (True, "walking") and tried() and all(not g.BLOCK[t] for t in tried()), (r, tried()))
ck("his stop: nothing queued until she is there", kinds() == [], kinds())
L.execute("HERX, HERY = %d + 0.5, %d + 0.5" % tuple(int(v) for v in tried()[0].split(","))); tick_walk(); ck("his stop: arrives, the game's action starts", kinds() == ["refuel"], (kinds(), tried()))
L.execute("LUAQUEUE.queue = {}"); g.NOW = g.NOW + 5000; fuel("status")
reset("HERX, HERY = 7306.5, 8172.5; TRIED = {}; REFUSE = {}"); fuel("car"); tick_walk(); first = tried()[0]; L.execute('REFUSE["%s"] = true' % first); L.execute("TRIED = {}")
for i in range(60): g.NOW = g.NOW + 300; g.TICK()
ck("his stop: a refused square does not end it, the next is tried", len(set(tried())) >= 1 and first not in tried()[1:], tried())
L.execute("job = nil"); g.NOW = g.NOW + 60000; g.TICK(); fuel("status")
reset("HERX, HERY = 7306.5, 8172.5; TRIED = {}; WALK_OK = false"); r = fuel("car")
for i in range(40):
    g.NOW = g.NOW + 300; g.TICK()
n = len(set(tried())); ck("his stop: every square tried before giving up", n >= 2 and fuel("status") == (False, "no_way_to_pump"), (n, tried()))
L.execute("SV = SOL.getVehicle; SOL.getVehicle = function() return CAR end"); reset("HERX, HERY = 7310.5, 8177.5; TRIED = {}; REFUSE = nil"); r = fuel("car")
ck("sitting in the car beside the cap is not standing at it", r == (True, "walking") and kinds() == [], (r, kinds()))
tick_walk(); ck("in the car: no square is tried yet", g.GOTOS == 0, g.GOTOS)
ck("in the car: reports walking, never pumping", fuel("status") == (True, "walking"), fuel("status")); L.execute("SOL.getVehicle = SV")
g.NOW = g.NOW + 60000; g.TICK(); fuel("status")
L.execute("block(7300, 8170, 7320, 8185)"); reset("HERX, HERY = 7306.5, 8172.5; TRIED = {}"); ck("nowhere free at all: says so at once", fuel("car") == (False, "no_way_to_pump") and g.GOTOS == 0, g.GOTOS)
L.execute("BLOCK = {}; block(7306, 8175, 7309, 8178)")
reset("HERX, HERY = 7310.5, 8177.5"); ck("hold: not held", g.SolUI.solFuelHeld() is False); ck("hold: taken", fuel("hold") == (True, "held")); ck("hold: she may not be seated", g.SolUI.solFuelHeld() is True)
g.NOW = g.NOW + 31000; ck("hold: runs out by itself", g.SolUI.solFuelHeld() is False)
L.execute("""
BASECLASS = { derive = function(self, name) return { Type = name } end }
ISBaseTimedAction = BASECLASS
REAL = ISRefuelFromGasPump
ISRefuelFromGasPump = { new = function(self, c, part, pump) return setmetatable({ character = c, part = part, vehicle = CAR, pump = pump, kind = "refuel" }, { __index = self }) end, update = function() return "up" end, isValid = function() return false end }
""")
reset("HERX, HERY = 7310.5, 8177.5"); fuel("car"); L.execute("A = QUEUED[1]")
ck("arm's length counts for the game's action", L.eval("A:isValid()") is True)
ck("the game's own steps are kept", L.eval("A:update()") == "up")
L.execute("HERX, HERY = 7300.5, 8170.5"); ck("across the forecourt it does not", L.eval("A:isValid()") is False)
L.execute("HERX, HERY = 7310.5, 8177.5; SV = SOL.getVehicle; SOL.getVehicle = function() return CAR end"); ck("sitting in the car it does not", L.eval("A:isValid()") is False); L.execute("SOL.getVehicle = SV")
L.execute("LUAQUEUE.queue = {}; ISRefuelFromGasPump = REAL; ISBaseTimedAction = nil; CELL.getGridSquare = SAVEGRID; SurvivorCompanion.GameplayUtil.isSquareFree = nil; function SOL.getX() return 7318 end; function SOL.getY() return 8179 end"); g.NOW = g.NOW + 60000; fuel("status")
# nobody is asking any more, or he called it off
reset("TRIED = {}"); fuel("car"); ck("cancel: held while the job runs", g.SolUI.solFuelHeld() is True); r = fuel("cancel"); ck("cancel: the job ends and she is free", r == (True, "cancelled") and g.SolUI.solFuelHeld() is False and fuel("status") == (False, "no_job"), r)
reset("TRIED = {}"); fuel("car"); n0 = g.GOTOS
for i in range(90): g.NOW = g.NOW + 300; g.TICK()
ck("nobody polls: the job is dropped, she is free, the walk stops", g.SolUI.solFuelHeld() is False and fuel("status") == (False, "no_job"), g.GOTOS)
n1 = g.GOTOS; g.NOW = g.NOW + 9000; g.TICK(); ck("and no more walking is sent", g.GOTOS == n1, (n1, g.GOTOS))
L.execute("HERX, HERY = 7310.5, 8177.5")
reset('TRIED = {}; C9 = can("Base.PetrolCan", 3, 10, true); INV = bag({}); TRUNK = bag({ C9 })'); r = fuel("status")
# the action never runs on her: the same calls, at the same pace
L.execute("""
function SOL.getX() return 7310.5 end; function SOL.getY() return 8177.5 end
AREA = { getX = function() return 7309.4 end, getY = function() return 8177.3 end }; CAR.getAreaCenter = function() return AREA end
Vehicles = { JerryCanLitres = 10 }
UNITS = 100; SENT = 0
PART.setContainerContentAmount = function(_, v) TANK = v end
PUMP.getPipedFuelAmount = function() return UNITS end
PUMP.setPipedFuelAmount = function(_, v) UNITS = v end
CAR.transmitPartModData = function() SENT = SENT + 1 end
""")
def direct(ms):
    for i in range(int(ms / 250)):
        g.NOW = g.NOW + 250; g.TICK()
        if i % 12 == 0: fuel("status")
reset("TANK = 10; UNITS = 100; SENT = 0; TRIED = {}"); r = fuel("car"); ck("direct: action queued first", r == (True, "pumping") and kinds() == ["refuel"], (r, kinds()))
L.execute("LUAQUEUE.queue = {}"); g.NOW = g.NOW + 2000; r = fuel("status"); ck("direct: action never ran, she fills with its calls", r == (True, "pumping"), r)
direct(10000); ck("direct: fuel goes in at the game's pace", 13 <= g.TANK <= 18, g.TANK); ck("direct: the pump gives what the tank gets", g.UNITS < 100 and g.SENT >= 1, (g.UNITS, g.SENT))
ck("direct: still pumping while it fills", fuel("status") == (True, "pumping"))
LAST = None
for i in range(int(80000 / 250)):
    g.NOW = g.NOW + 250; g.TICK()
    if i % 12 == 0:
        LAST = fuel("status")
        if LAST[1].startswith("done"): break
r = LAST
ck("direct: done with litres", r == (True, "done:45") and g.TANK == 55, (r, g.TANK))
L.execute("PUMP.getPipedFuelAmount = function() return 92 end; PUMP.setPipedFuelAmount = nil; PART.setContainerContentAmount = nil; function SOL.getX() return 7318 end; function SOL.getY() return 8179 end; AREA = { getX = function() return 7307.2 end, getY = function() return 8177.4 end }; CAR.getAreaCenter = function() return AREA end")
L.execute('solStationsGardens = function(x, y, n) ASKEDN = n; return "1,2;3,4" end'); reset(); ck("gardens she has passed", fuel("gardens") == (True, "gardens:1,2;3,4") and g.ASKEDN == 30, fuel("gardens"))
L.execute('solStationsGardens = nil'); reset(); ck("no Java: none", fuel("gardens") == (False, "stations_unavailable"))
reset(); ck("unknown option", fuel("nonsense") == (False, "unknown_option"))

reset(); s0, c0 = g.STEPS, g.CENTRES
t0 = g.NOW + 1000
for i in range(30): g.NOW = t0 + i * 16; g.TICK()
ck("scan stepped every frame", g.STEPS - s0 == 30, g.STEPS - s0)
ck("centre set about twice a second, not each frame", 1 <= g.CENTRES - c0 <= 2, g.CENTRES - c0)
ck("centre passes both positions", list(g.CENTRE.values()) == [7100, 8200, 7318, 8179], list(g.CENTRE.values()))
reset("ON = false"); g.NOW = g.NOW + 2000; g.TICK(); s0 = g.STEPS; g.NOW = g.NOW + 16; g.TICK(); ck("switched off: no scanning", g.STEPS == s0)
reset("solStationsStep = nil"); g.NOW = g.NOW + 1000; ck("no Java: tick is harmless", g.TICK() is None or True)
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)

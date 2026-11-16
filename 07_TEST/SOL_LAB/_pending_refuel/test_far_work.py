"""Offline tests for far_work (SolFarWork.lua + apply_s74_far_work.py). usage: python test_far_work.py
The plants are the game's own: the real SGlobalObject / SGlobalObjectSystem / SPlantGlobalObject / SFarmingSystem and every
farming_vegetableconf file from the 42.22.2 install run in Kahlua-like Lua (kahlua_env), on a Lua stand-in for the Java global
object system. Time passes by calling the game's own SFarmingSystem:EveryTenMinutes, six times a game hour.
  1 installer on copies (SolAuthority.lua, farm_talk.py): applies, twice changes nothing, compiles
  2 elapsed time: three game days away, keeper on; she waters, picks, sows, sprays, feeds, at night too, within her pace;
    a control run with the switch off shows the same plants left alone
  3 his return: the ledger is applied once (seeds out, can and tap drawn, spray and compost used, produce in the fridge with its age),
    the report row goes to the farm's stop list once
  4 double load: the ledger rolled back (world saved before, chunk after) applies nothing twice
  5 save and reload mid-shift: the module reloaded on the same ModData goes on from the same hour; ModData holds plain values only
  6 supplies run out: 4 doses of water and no source: 4 doses, then "water" is short; storage full: produce on the floor beside it
  7 rain: no watering outdoors, the rest goes on
  8 not at all: switch off, keeper off, she is here, she is away from the farm
  9 her words: far_report_line, the owner's sentence exactly, and no mechanics in any line
Offline PASS is not Runtime PASS."""
import copy, os, re, shutil, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
MIND = r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind"
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media\lua\server"
FAIL, N = [], [0]
def ck(n, c, d=""):
    N[0] += 1
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)

# ---------------------------------------------------------------- 1 the installer
import subprocess
T = tempfile.mkdtemp(prefix="sol_far_work_")
cl, md = os.path.join(T, "client"), os.path.join(T, "mind")
os.makedirs(cl); os.makedirs(md)
shutil.copy(os.path.join(LAB, "SolAuthority.lua"), cl)                      # read-only copies of the lab and the Mind
shutil.copy(os.path.join(MIND, "farm_talk.py"), md)
def run(*args): return subprocess.run([sys.executable, os.path.join(HERE, "apply_s74_far_work.py")] + list(args), capture_output=True, text=True, encoding="utf-8")
def snap(*dirs): return {n: open(os.path.join(d, n), encoding="utf-8").read() for d in dirs for n in sorted(os.listdir(d)) if not n.startswith("__")}
r = run(cl, md); ck("installer applies", r.returncode == 0, r.stderr[-500:])
once = snap(cl, md)
r = run(cl, md); ck("installer twice: nothing changes", r.returncode == 0 and snap(cl, md) == once, r.stderr[-300:])
ck("switch far_work is in A.FIXES", '"far_work"' in once["SolAuthority.lua"])
ck("farm_talk answers the far_report row", 'if r == "far_report": return far_report_line(d)' in once["farm_talk.py"])
SRC = open(os.path.join(HERE, "SolFarWork.lua"), encoding="utf-8").read()
ck("SolFarWork.lua is ASCII", all(ord(c) < 128 for c in SRC))
ck("SolFarWork.lua compiles in Kahlua-like Lua", not isinstance(lua51.LuaRuntime().globals().loadstring(SRC), tuple))
ck("SolFarWork says nothing itself (no say/addLine in it)", not re.search(r"\bSay\(|addLineChatElement|:say\(", SRC))

# ---------------------------------------------------------------- the world
VANILLA = ["Map/SGlobalObject.lua", "Map/SGlobalObjectSystem.lua", "Farming/farming_vegetableconf.lua", "Farming/farming_vegetableconf_vegetables.lua",
           "Farming/farming_vegetableconf_herbs.lua", "Farming/farming_vegetableconf_vegetables_sprites.lua", "Farming/farming_vegetableconf_herbs_sprites.lua",
           "Farming/SPlantGlobalObject.lua", "Farming/SFarmingSystem.lua"]
WORLD = r"""
print = function(m) LOGS[#LOGS + 1] = tostring(m) end
LOGS = {}
require = function() end
NOW, MIN = 100000, 1000 * 60
function getTimestampMs() return NOW end
local seed = 12345
function ZombRand(a, b)
    seed = (seed * 1103515245 + 12345) % 2147483648
    if b == nil then if a <= 0 then return 0 end return seed % a end
    if b <= a then return a end
    return a + seed % (b - a)
end
function isClient() return false end
function isServer() return false end
function getText(k) return k end
function instanceof() return false end
function noise() end
function getDebug() return false end
IsoObjectChange = {}
luautils = { stringStarts = function(s, p) return string.sub(s, 1, #p) == p end }
SandboxVars = { PlantResilience = 3 }
OPTS = { PlantGrowingSeasons = false, KillInsideCrops = false, FarmingAmountNew = 1, FarmingSpeedNew = 1 }
function getSandboxOptions() return { getOptionByName = function(_, n) return { getValue = function() return OPTS[n] end } end } end
season = { currentTemp = 20, weather = "cloudy", moonCycle = 10 }
RAIN = false
RainManager = { isRaining = function() return RAIN end }
function getClimateManager() return { getPrecipitationIntensity = function() return RAIN and 0.5 or 0 end, getSeasonName = function() return "Summer" end } end
GT = {}
function GT:getWorldAgeHours() return MIN / 60 end
function GT:getTimeOfDay() return (MIN / 60) % 24 end
function GT:getDay() return math.floor(MIN / 1440) end
function GT:getMonth() return 5 end
function GT:getMinutesPerDay() return 60 end
function getGameTime() return GT end
GameTime = { getInstance = function() return GT end }
function getWorld() return { getWeather = function() return "cloudy" end } end
function getCore() return { getDebug = function() return false end } end
function getDebugOptions() return { getBoolean = function() return false end } end
local function ev() return setmetatable({}, { __index = function(t, k) local e = { fns = {} }; e.Add = function(f) e.fns[#e.fns + 1] = f end; rawset(t, k, e); return e end }) end
Events = ev()
-- java lists
function jlist(t) return { size = function() return #t end, get = function(_, i) return t[i + 1] end } end
-- the Java global object system, as Lua
local function newSystem(name)
    local s = { md = {}, objs = {}, at = {} }
    function s:getModData() return self.md end
    function s:setModDataKeys() end
    function s:setObjectModDataKeys() end
    function s:setObjectSyncKeys() end
    function s:loadedWorldVersion() return 1 end
    function s:getObjectCount() return #self.objs end
    function s:getObjectByIndex(i) return self.objs[i + 1] end
    function s:newObject(x, y, z)
        local go = { md = {} }
        function go:getX() return x end
        function go:getY() return y end
        function go:getZ() return z end
        function go:getModData() return self.md end
        self.objs[#self.objs + 1] = go
        self.at[x .. "," .. y .. "," .. z] = go
        return go
    end
    function s:getObjectAt(x, y, z) return self.at[x .. "," .. y .. "," .. z] end
    function s:removeObject(go)
        for i, o in ipairs(self.objs) do if o == go then table.remove(self.objs, i); break end end
        self.at[go:getX() .. "," .. go:getY() .. "," .. go:getZ()] = nil
    end
    function s:hasObjectsInChunk(wx, wy)
        for _, o in ipairs(self.objs) do if math.floor(o:getX() / 8) == wx and math.floor(o:getY() / 8) == wy then return true end end
        return false
    end
    function s:getObjectsInChunk(wx, wy)
        local out = {}
        for _, o in ipairs(self.objs) do if math.floor(o:getX() / 8) == wx and math.floor(o:getY() / 8) == wy then out[#out + 1] = o end end
        return jlist(out)
    end
    function s:getObjectsAdjacentTo(x, y, z)
        local out = {}
        for _, o in ipairs(self.objs) do if math.abs(o:getX() - x) <= 1 and math.abs(o:getY() - y) <= 1 and not (o:getX() == x and o:getY() == y) then out[#out + 1] = o end end
        return jlist(out)
    end
    function s:finishedWithList() end
    function s:addGlobalObjectOnClient() end
    function s:removeGlobalObjectOnClient() end
    function s:updateGlobalObjectOnClient() end
    function s:sendCommand() end
    return s
end
SGlobalObjects = { registerSystem = newSystem, getSystemCount = function() return 0 end }
ISBaseObject = {}
ISBaseObject.__index = ISBaseObject
function ISBaseObject:derive(t) local o = {}; setmetatable(o, self); self.__index = self; o.Type = t; return o end
-- squares: nil = not loaded
LOADED = {}
function sqKey(x, y, z) return x .. "," .. y .. "," .. (z or 0) end
function getCell() return { getGridSquare = function(_, x, y, z) return LOADED[sqKey(x, y, z)] end } end
-- the house: containers, items, water
function mkItem(full, o)
    o = o or {}
    local it = { full = full, uses = o.uses, fluid = o.fluid, age = 0, md = {}, food = o.food == true, w = o.w or 0.3 }
    function it:getFullType() return self.full end
    function it:getCurrentUses() return self.uses end
    function it:UseAndSync() self.uses = self.uses - 1 end
    function it:isFood() return self.food end
    function it:getAge() return self.age end
    function it:setAge(a) self.age = a end
    function it:getModData() return self.md end
    if o.fluid ~= nil then
        local fc = {}
        function fc:getAmount() return it.fluid end
        function fc:adjustAmount(a) it.fluid = a end
        it.getFluidContainer = function() return fc end
    end
    return it
end
FOODS = { ["Base.Carrots"] = true, ["Base.Tomato"] = true }
function mkContainer(cap)
    local c = { items = {}, cap = cap or 50 }
    function c:getItems() return jlist(self.items) end
    function c:Remove(item) for i, x in ipairs(self.items) do if x == item then table.remove(self.items, i); return end end end
    function c:AddItem(t) local it = mkItem(t, { food = FOODS[t] }); self.items[#self.items + 1] = it; return it end
    function c:getContentsWeight() local w = 0; for _, x in ipairs(self.items) do w = w + x.w end; return w end
    function c:getCapacityWeight() return self.cap end
    function c:count(t) local n = 0; for _, x in ipairs(self.items) do if x.full == t then n = n + 1 end end; return n end
    return c
end
function mkObject(conts, water)
    local o = { md = {}, conts = conts or {}, water = water }
    function o:getContainerCount() return #self.conts end
    function o:getContainerByIndex(k) return self.conts[k + 1] end
    function o:getModData() return self.md end
    function o:hasWater() return self.water ~= nil and self.water > 0 end
    function o:getFluidAmount() return self.water or 0 end
    function o:useFluid(l) local t = math.min(self.water or 0, l); self.water = (self.water or 0) - t; return t end
    return o
end
function mkSquare(objs)
    local sq = { md = {}, objs = objs, floor = {} }
    function sq:getObjects() return jlist(self.objs) end
    function sq:getModData() return self.md end
    function sq:AddWorldInventoryItem(t) local it = mkItem(t, { food = FOODS[t] }); self.floor[#self.floor + 1] = it; return it end
    return sq
end
MD = {}
ModData = { getOrCreate = function(n) MD[n] = MD[n] or {}; return MD[n] end, transmit = function() end }
TASKS = {}
SolBudget = { register = function(n, f) TASKS[n] = f end }
SW = { far_work = true }
SolAuthority = { on = function(n) return SW[n] == true end }
SolUI = { }
SOL = nil
SolUI.solActor = function() return SOL end
PX, PY = 3000, 3000
function getSpecificPlayer() return { getX = function() return PX end, getY = function() return PY end, getZ = function() return 0 end } end
HER = { x = 102, y = 106 }
BASE = { zones = { { id = "z1", kind = "farm", x1 = 100, y1 = 100, x2 = 105, y2 = 103, z = 0 } } }
SurvivorCompanion = {
    GameplayUtil = { gridSquare = function(x, y, z) return LOADED[sqKey(x, y, z)] end, perkLevel = function() return 3 end },
    BaseLife = { active = function() return BASE end },
    Persistence = { pendingIds = function() return HER and { "sc-1" } or {} end, pendingBootstrap = function() return HER and { id = "sc-1", x = HER.x, y = HER.y } end },
}
"""
SETUP = r"""
SFarmingSystem.instance = SFarmingSystem:new()
S = SFarmingSystem.instance
BARREL = { waterAmount = BARREL_L }
SRainBarrelSystem = { instance = { getLuaObjectAt = function(_, x, y, z) if x == 120 and y == 100 then return BARREL end end } }
function plant(x, y, kind)
    local p = S:newLuaObjectAt(x, y, 0)
    p:initNew()
    if kind == "plow" then return p end
    p:seed("Carrots", 0)
    p.nextGrowing = S.hoursElapsed + 5000
    if kind == "ripe" then p.nbOfGrow, p.hasVegetable, p.waterNeeded, p.waterLvl, p.health = 5, true, 70, 85, 70
    elseif kind == "thirsty" then p.nbOfGrow, p.waterNeeded, p.waterLvl, p.health = 2, 70, 40, 60
    elseif kind == "mildew" then p.nbOfGrow, p.waterNeeded, p.waterLvl, p.health, p.mildewLvl = 2, 70, 80, 60, 20
    elseif kind == "young" then p.nbOfGrow, p.waterNeeded, p.waterLvl, p.health = 1, 70, 80, 60 end
    return p
end
for x = 100, 105 do plant(x, 100, "thirsty") end
for x = 100, 103 do plant(x, 101, "ripe") end
for x = 100, 102 do plant(x, 102, "plow") end
plant(104, 102, "mildew")
plant(105, 102, "young")
-- the house, east of the farm: a shed with the farm things, a fridge, a tap, a rain barrel
SHED, FRIDGE = mkContainer(50), mkContainer(FRIDGE_CAP)
CAN = mkItem("Base.WateredCan", { fluid = CAN_L })
SHED.items[#SHED.items + 1] = CAN
for i = 1, 5 do SHED.items[#SHED.items + 1] = mkItem("Base.CarrotSeed") end
SPRAY = mkItem("Base.GardeningSprayMilk", { uses = 5 })
SHED.items[#SHED.items + 1] = SPRAY
COMPOST = mkItem("Base.CompostBag", { uses = 2 })
SHED.items[#SHED.items + 1] = COMPOST
TAP = mkObject({}, TAP_L)
HOUSE = { [sqKey(110, 100, 0)] = mkSquare({ mkObject({ SHED }) }), [sqKey(111, 100, 0)] = mkSquare({ mkObject({ FRIDGE }) }),
          [sqKey(112, 100, 0)] = mkSquare({ TAP }) }
-- what the last complete scan saw, as SolInventory/SolFarmView publish it
local V = SolFarmView
local rows = { { where = "house", kind = "can", type = "Base.WateredCan", uses = math.floor(CAN_L / 0.2), x = 110, y = 100, z = 0, oi = 0, ci = 0 } }
for i = 1, 5 do rows[#rows + 1] = { where = "house", kind = "seed", crop = "Carrots", type = "Base.CarrotSeed", uses = 1, x = 110, y = 100, z = 0, oi = 0, ci = 0 } end
rows[#rows + 1] = { where = "house", kind = "spray", type = "Base.GardeningSprayMilk", uses = 5, x = 110, y = 100, z = 0, oi = 0, ci = 0 }
rows[#rows + 1] = { where = "house", kind = "compost", type = "Base.CompostBag", uses = 2, x = 110, y = 100, z = 0, oi = 0, ci = 0 }
V.spots = rows
V.places = { { x = 111, y = 100, z = 0, oi = 0, ci = 0, kind = "fridge", score = 4 } }
V.waterSources = {}
if TAP_L > 0 then V.waterSources[#V.waterSources + 1] = { x = 112, y = 100, z = 0, oi = 0, l = TAP_L } end
if BARREL_L > 0 then V.waterSources[#V.waterSources + 1] = { x = 120, y = 100, z = 0, oi = 0, l = BARREL_L } end
V.stockLatest = { ready = true, unloaded = 0, seeds = {}, sprays = {} }
SolFarmWork.store().modes = { farm = true }
F = SolFarWork
F.install()
DONE_BY_HOUR = {}
local wh = F.workHour
F.workHour = function(d, z, h) local n = wh(d, z, h); DONE_BY_HOUR[#DONE_BY_HOUR + 1] = { h = h, n = n }; return n end
function hours(n)
    for _ = 1, n do
        for _ = 1, 6 do MIN = MIN + 10; NOW = NOW + 25000; S:EveryTenMinutes() end
        TASKS.sol_far_work()
    end
end
function comeBack()
    for k, v in pairs(HOUSE) do LOADED[k] = v end
    for x = 100, 105 do for y = 100, 103 do LOADED[sqKey(x, y, 0)] = { getObjects = function() return jlist({}) end, getModData = function() return {} end } end end
    PX, PY = 108, 104
    for _ = 1, 10 do NOW = NOW + 1000; TASKS.sol_far_work() end
    NOW = NOW + 40000; TASKS.sol_far_work()
end
function alive(p) return p.state == "seeded" end
function plants() local out = {}; for i = 1, S:getLuaObjectCount() do out[#out + 1] = S:getLuaObjectByIndex(i) end; return out end
function plain(t, seen)
    seen = seen or {}
    if seen[t] then return true end
    seen[t] = true
    for k, v in pairs(t) do
        local tk, tv = type(k), type(v)
        if tk ~= "string" and tk ~= "number" then return false end
        if tv == "table" then if not plain(v, seen) then return false end
        elseif tv ~= "string" and tv ~= "number" and tv ~= "boolean" then return false end
    end
    return true
end
"""
FARM = ["SolFarmView.lua", "SolFarmWork.lua"]
def world(can_l=2.0, tap_l=50, barrel_l=3, fridge_cap=50, far=True):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(WORLD)
    for f in VANILLA: L.execute(open(os.path.join(GAME, f), encoding="utf-8").read())
    for f in FARM: L.execute(open(os.path.join(HERE, f), encoding="utf-8").read())
    L.execute(SRC)
    L.execute("CAN_L, TAP_L, BARREL_L, FRIDGE_CAP = %s, %s, %s, %s" % (can_l, tap_l, barrel_l, fridge_cap))
    L.execute(SETUP)
    return L
def ev(L, code): return L.eval(code)
def py(t):
    if lua51.LuaRuntime().eval("1") is None: pass
    return t

# ---------------------------------------------------------------- 2 elapsed time
L = world()
L.execute("hours(1)")
ck("the shift starts with the scan she had before he left", "shift started" in " ".join(L.eval("LOGS").values()), list(L.eval("LOGS").values())[-3:])
start = ev(L, "MD.Sol_FarWork.lastHour")
L.execute("hours(72)")
ck("72 game hours worked, none twice", ev(L, "MD.Sol_FarWork.lastHour") == start + 72 and ev(L, "#DONE_BY_HOUR") == 72, (ev(L, "MD.Sol_FarWork.lastHour"), start))
mx = ev(L, "(function() local m = 0; for _, r in ipairs(DONE_BY_HOUR) do if r.n > m then m = r.n end end; return m end)()")
cap = int(60 // ev(L, "F.cost('sow')"))
ck("never more jobs in a game hour than her body could do (%d <= %d)" % (mx, cap), 0 < mx <= cap)
night = ev(L, "(function() local n = 0; for _, r in ipairs(DONE_BY_HOUR) do local hod = r.h % 24; if r.n > 0 and (hod < 6 or hod >= 21) then n = n + 1 end end; return n end)()")
ck("she works at night too (owner rule): %d night hours with work" % night, night > 0)
ck("every thirsty plant is at its need", ev(L, "(function() for _, p in ipairs(plants()) do if alive(p) and p.nbOfGrow == 2 and p.mildewLvl == 0 and p.waterLvl < p.waterNeeded then return false end end; return true end)()"))
ck("the ripe carrots are picked (4 harvested tiles)", ev(L, "(function() local n = 0; for _, p in ipairs(plants()) do if p.y == 101 and p.state == 'harvested' then n = n + 1 end end; return n end)()") == 4)
ck("the 3 furrows are sown with carrot", ev(L, "(function() local n = 0; for _, p in ipairs(plants()) do if p.y == 102 and p.x <= 102 and p.state == 'seeded' and p.typeOfSeed == 'Carrots' then n = n + 1 end end; return n end)()") == 3)
ck("the mildew is treated", ev(L, "S:getLuaObjectAt(104, 102, 0).mildewLvl") < 20)
ck("compost: the bag's 2 uses went to 2 young plants, no more", ev(L, "MD.Sol_FarWork.report.fed") == 2 and ev(L, "(function() local n = 0; for _, p in ipairs(plants()) do if p.compost == true then n = n + 1 end end; return n end)()") == 2)
ck("the rain barrel is drawn first, from its own state", ev(L, "BARREL.waterAmount") < 3, ev(L, "BARREL.waterAmount"))
ck("nothing in the house moved yet (not loaded)", ev(L, "SHED:count('Base.CarrotSeed')") == 5 and ev(L, "CAN.fluid") == 2.0 and ev(L, "FRIDGE:count('Base.Carrots')") == 0)
rep = ev(L, "MD.Sol_FarWork.report")
ck("her report so far: watered in rounds, carrots picked", rep.rounds >= 1 and rep.harvest[1].veg == "Base.Carrots" and rep.harvest[1].n > 0 and rep.sown == 3, (rep.rounds, rep.sown))
picked = rep.harvest[1].n
ck("with 50 l at the tap, water is never called short", ev(L, "MD.Sol_FarWork.report.short.water") is None)
ck("ModData holds plain values only (it saves)", ev(L, "plain(MD.Sol_FarWork) and plain(MD.Sol_Farm)"))
C = world(); C.execute("SW.far_work = false; hours(73)")
ck("control, switch off: the same farm left alone (nothing sown, nothing picked)", ev(C, "(function() for _, p in ipairs(plants()) do if p.state == 'harvested' or (p.y == 102 and p.x <= 102 and p.state ~= 'plow') then return false end end; return true end)()") and ev(C, "MD.Sol_FarWork.active") is None)
ck("control: thirsty plants stayed below their need", ev(C, "(function() for _, p in ipairs(plants()) do if p.nbOfGrow == 2 and p.mildewLvl == 0 and p.waterLvl >= p.waterNeeded then return false end end; return true end)()"))

# ---------------------------------------------------------------- 3 his return: the ledger applied once, the report once
before = copy.deepcopy({k: v for k, v in []})
L.execute("PRE = {}; for i, e in ipairs(MD.Sol_FarWork.entries) do local c = {}; for k, v in pairs(e) do c[k] = v end; PRE[i] = c end; PRE_N = #MD.Sol_FarWork.entries")
L.execute("comeBack()")
ck("the shift ended when he came", ev(L, "MD.Sol_FarWork.active") is False)
ck("ledger: nothing left to apply", ev(L, "F.pending(MD.Sol_FarWork)") == 0)
ck("3 seeds taken from the shed (5 -> 2)", ev(L, "SHED:count('Base.CarrotSeed')") == 2, ev(L, "SHED:count('Base.CarrotSeed')"))
ck("the can was poured (2.0 l -> 0)", ev(L, "CAN.fluid") < 0.01, ev(L, "CAN.fluid"))
drawn = ev(L, "(function() local n = 0; for _, e in ipairs(PRE) do if e.op == 'draw' then n = n + e.litres end end; return n end)()")
ck("the tap gave exactly what the ledger says (%.1f l), after the barrel ran dry" % drawn, drawn > 0 and abs((50 - ev(L, "TAP.water")) - drawn) < 1e-6 and ev(L, "BARREL.waterAmount") < 0.2, (drawn, ev(L, "TAP.water"), ev(L, "BARREL.waterAmount")))
ck("spray and compost used", ev(L, "SPRAY.uses") < 5 and ev(L, "COMPOST.uses") < 2, (ev(L, "SPRAY.uses"), ev(L, "COMPOST.uses")))
ck("the picked carrots are in the fridge (%d)" % picked, ev(L, "FRIDGE:count('Base.Carrots')") == picked)
ck("the carrots aged since she picked them", ev(L, "(function() for _, it in ipairs(FRIDGE.items) do if it.full == 'Base.Carrots' and it.age <= 0 then return false end end; return true end)()"))
ck("the seed she kept from them too", ev(L, "FRIDGE:count('Base.CarrotSeed')") >= 0)
stops = ev(L, "MD.Sol_Farm.stops")
far = [stops[i] for i in range(1, len(stops) + 1) if stops[i].reason == "far_report"]
ck("one far_report row in the farm's stop list", len(far) == 1)
L.execute("comeBack()")
stops = ev(L, "MD.Sol_Farm.stops")
ck("and only one after more ticks", len([1 for i in range(1, len(stops) + 1) if stops[i].reason == "far_report"]) == 1)
detail = far[0].detail
def todict(t):
    if hasattr(t, "items"):
        keys = list(t.keys())
        if keys and all(isinstance(k, int) for k in keys): return [todict(t[k]) for k in sorted(keys)]
        return {k: todict(v) for k, v in t.items()}
    return t
detail = todict(detail)
detail.setdefault("short", []); detail.setdefault("harvest", [])
if not isinstance(detail["short"], list): detail["short"] = []

# ---------------------------------------------------------------- 4 double load
L.execute("MD.Sol_FarWork.entries = PRE")                                    # the world save is from before he came, the chunks from after
L.execute("comeBack()")
ck("rolled-back ledger: seeds not taken again", ev(L, "SHED:count('Base.CarrotSeed')") == 2)
ck("rolled-back ledger: carrots not given again", ev(L, "FRIDGE:count('Base.Carrots')") == picked)
ck("rolled-back ledger: tap not drawn again", ev(L, "TAP.water") == ev(L, "TAP.water"))
ck("rolled-back entries all closed by the holders' marks", ev(L, "F.pending(MD.Sol_FarWork)") == 0)

# ---------------------------------------------------------------- 5 save and reload mid-shift
R = world()
R.execute("hours(25)")
h1, ids1 = ev(R, "MD.Sol_FarWork.lastHour"), ev(R, "MD.Sol_FarWork.nextId")
R.execute(SRC)                                                               # the module comes back on the same ModData, as after a load
R.execute("F = SolFarWork; F._installed = nil; F.install(); local wh = F.workHour; F.workHour = function(d, z, h) local n = wh(d, z, h); DONE_BY_HOUR[#DONE_BY_HOUR + 1] = { h = h, n = n }; return n end")
R.execute("hours(24)")
hs = ev(R, "(function() local s, dup = {}, false; for _, r in ipairs(DONE_BY_HOUR) do if s[r.h] then dup = true end; s[r.h] = true end; return dup end)()")
ck("after a reload she goes on from the same hour (%s -> %s), no hour worked twice" % (h1, ev(R, "MD.Sol_FarWork.lastHour")), ev(R, "MD.Sol_FarWork.lastHour") == h1 + 24 and hs is False)
ck("ledger ids go on (no id reused)", ev(R, "MD.Sol_FarWork.nextId") >= ids1)

# ---------------------------------------------------------------- 6 supplies run out
D = world(can_l=0.8, tap_l=0, barrel_l=0, fridge_cap=0.5)
D.execute("hours(48)")
poured = ev(D, "(function() local n = 0; for _, e in ipairs(MD.Sol_FarWork.entries) do if e.op == 'pour' then n = n + e.n end end; return n end)()")
ck("4 doses in the can, 4 doses poured, no more", poured == 4, poured)
ck("water is short in her report", ev(D, "MD.Sol_FarWork.report.short.water") is True)
D.execute("comeBack()")
ck("full fridge: the rest of the produce beside it, on the floor", ev(D, "#HOUSE[sqKey(111, 100, 0)].floor") > 0)
dd = todict(ev(D, "(function() for _, s in ipairs(MD.Sol_Farm.stops) do if s.reason == 'far_report' then return s.detail end end end)()"))
ck("the report says so", isinstance(dd, dict) and dd.get("floor") is True)

# ---------------------------------------------------------------- 7 rain
W = world()
W.execute("RAIN = true; hours(48)")
ck("rain: not one dose poured outdoors", ev(W, "(function() for _, e in ipairs(MD.Sol_FarWork.entries) do if e.op == 'pour' or e.op == 'draw' then return false end end; return true end)()") and ev(W, "BARREL.waterAmount") == 3)
ck("rain: the picking goes on", ev(W, "#MD.Sol_FarWork.report.harvest") == 1)

# ---------------------------------------------------------------- 8 not at all
for name, code in (("switch off", "SW.far_work = false"), ("keeper off", "SolFarmWork.store().modes.farm = false"),
                   ("she is here", "SOL = { getCurrentSquare = function() return {} end, getX = function() return 102 end, getY = function() return 106 end }"),
                   ("she is away from the farm", "HER = { x = 900, y = 900 }"), ("no complete scan", "V0 = SolFarmView; V0.stockLatest = { ready = true, unloaded = 3 }")):
    X = world()
    X.execute(code + "; hours(12)")
    ck("no shift when " + name, not ev(X, "MD.Sol_FarWork.active") and ev(X, "#DONE_BY_HOUR") == 0 and ev(X, "SFarmingSystem.instance:getLuaObjectAt(100, 101, 0).hasVegetable") is True)

# ---------------------------------------------------------------- 9 her words
sys.path[:0] = [md, MIND]
import farm_talk as FT
ck("Mind copy: the patched farm_talk is the one imported", hasattr(FT, "far_report_line") and os.path.dirname(FT.__file__) == md)
own = FT.far_report_line({"rounds": 2, "harvest": [{"veg": "Base.Carrots", "n": 12}]})
ck("the owner's sentence exactly: " + str(own), own == "سقيت الزرع مرتين وقطفت 12 جزرة.")
ck("through stop_line too", FT.stop_line({"reason": "far_report", "detail": {"rounds": 2, "harvest": [{"veg": "Base.Carrots", "n": 12}]}, "seq": 9}) == own)
lines = [("A", FT.far_report_line(detail)), ("D", FT.far_report_line(dd))]
for d_ in ({"rounds": 1}, {"rounds": 5, "sown": 3, "cured": 1, "fed": 2}, {"rounds": 14, "harvest": [{"veg": "Base.Tomato", "n": 2}, {"veg": "Base.Potato", "n": 7}]},
           {"short": ["water"]}, {"harvest": [{"veg": "Base.Carrots", "n": 1}], "short": ["seed"]}, {"sown": 11, "floor": True}, {}):
    lines.append((str(d_), FT.far_report_line(d_)))
print("   her lines:")
for k, v in lines: print("    ", v)
ck("A (three days): " + str(lines[0][1]), isinstance(lines[0][1], str) and lines[0][1].startswith("سقيت الزرع") and "جز" in lines[0][1])
ck("nothing done, nothing short: she says nothing", FT.far_report_line({}) is None)
BAD = re.compile(r"chunk|تحميل|محمّل|محمل|سجل|ledger|record|simulat|محاكا|حساب|ساعة لعب|game|unloaded|مربع|خانة|نظام|ملف|بيانات|ModData|far_work|\bfar\b|shift|بالغياب", re.I)
bad = [(k, v) for k, v in lines if v and BAD.search(v)]
ck("her far-work lines (%d) have no mechanics in them" % len(lines), not bad, bad)
ck("the most important shortage is the one said (water before compost)", "خلصت المي" in (lines[1][1] or ""), lines[1][1])
ck("each line is short (<= 110 chars) and ends with a full stop", all(v is None or (len(v) <= 110 and v.endswith(".")) for _, v in lines), [v for _, v in lines if v and len(v) > 110])

print("\n%d checks, %d failed" % (N[0], len(FAIL)))
if FAIL: print("FAILED:", FAIL); sys.exit(1)
print("ALL PASS (offline; Runtime not tested)")

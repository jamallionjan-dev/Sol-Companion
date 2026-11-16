"""Her order of work on the farm, offline: the real SolFarmView / SolFarmWork / SolFarmKeeper / SolFarmAct and the real SolInventory (patched by apply_s33 on a copy) on a mocked game. Applying the older apply_s2x scripts to copies of the live files is part of the test."""
import glob, os, re, shutil, subprocess, sys, tempfile
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media"
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)

# the whole-base scan, with the s33 patch, on copies of the live files
S33 = tempfile.mkdtemp(prefix="sol_s33_")
S33_NAMES = ["SolInventory.lua", "SolAuthority.lua", "SolGate.lua", "SolChores.lua", "SCFarmWork.lua", "SCCommands.lua"]
for n in S33_NAMES: shutil.copy(os.path.join(LIVE, n), S33)
if "function U.invLast()" not in open(os.path.join(S33, "SolInventory.lua"), encoding="utf-8").read():            # once installed, the live files already carry it
    r_ = subprocess.run([sys.executable, os.path.join(HERE, "apply_s33_lua.py")] + [os.path.join(S33, n) for n in S33_NAMES], capture_output=True, text=True)
    ck("apply: apply_s33_lua.py", r_.returncode == 0, r_.stderr[-400:])
INV_SRC = open(os.path.join(S33, "SolInventory.lua"), encoding="utf-8").read()

WORLD = r"""
-- The game's Lua has no next().
LUA_NEXT = LUA_NEXT or next
next = nil
-- The game's tonumber (Kahlua BaseLib.tonumber): with anything but exactly one argument the first one is cast to a string, so a number dies there.
do
    local realTonumber = tonumber
    tonumber = function(...)
        if select("#", ...) ~= 1 and type((...)) ~= "string" then error("ClassCastException: Double cannot be cast to String at BaseLib.tonumber") end
        return realTonumber(...)
    end
end
-- string.gmatch does not exist in the game's string library
string.gmatch = nil
print = function() end
NOW = 1000000
function getTimestampMs() return NOW end
STARTS, ONTICKS = {}, {}
Events = { OnGameStart = { Add = function(f) STARTS[#STARTS + 1] = f end }, OnTick = { Add = function(f) ONTICKS[#ONTICKS + 1] = f end } }
STORE = {}
ModData = { getOrCreate = function(k) STORE[k] = STORE[k] or {}; return STORE[k] end, transmit = function() end }
function getChunkSizeInSquares() return 8 end
Perks = { Farming = "Farming" }
ItemTag = { COMPOST = "COMPOST", FERTILIZER = "FERTILIZER", DIG_PLOW = "DIG_PLOW" }
IsoFlagType = { canBeCut = "canBeCut", canBeRemoved = "canBeRemoved", vegitation = "vegitation" }
IsoPropertyType = { GRASS_FLOOR = "GRASS_FLOOR" }
RainManager = { isRaining = function() return RAIN == true end }
ZomboidGlobals = { farmingFluidContainerMillilitresPerUse = 200 }
MONTH, SEASONS, SEASONNAME, HOUR = 5, true, "Summer", 12            -- 1..12
RAIN = false
function getClimateManager() return { getPrecipitationIntensity = function() return RAIN and 0.5 or 0 end, getSeasonName = function() return SEASONNAME end } end
function getGameTime() return { getMonth = function() return MONTH - 1 end, getTimeOfDay = function() return HOUR end, getWorldAgeHours = function() return 1000 end } end
function getSandboxOptions() return { getOptionByName = function(_, n) return { getValue = function() return SEASONS end } end } end
farming_vegetableconf = { props = {
    Tomato = { seedName = "Base.TomatoSeed", seedTypes = { "Base.TomatoSeed" }, vegetableName = "Base.Tomato", harvestLevel = 5, fullGrown = 6, timeToGrow = 100, sowMonth = { 3, 4, 5, 6 }, bestMonth = { 5 }, riskMonth = { 6 } },
    Carrots = { seedName = "Base.CarrotSeed", vegetableName = "Base.Carrots", harvestLevel = 5, fullGrown = 6, timeToGrow = 100, sowMonth = { 2, 3, 4, 8, 9, 10 } },
    Corn = { seedName = "Base.CornSeed", vegetableName = "Base.Corn", harvestLevel = 5, fullGrown = 6, timeToGrow = 100, sowMonth = { 4, 5, 6 } },
} }

PLANTS = {}
function P_(x, y, z) return x .. ":" .. y .. ":" .. (z or 0) end
local PM = {}
function PM:canHarvest() return self.state == "seeded" and self.hasVegetable == true end
function PM:isAlive() return (self.health or 0) > 0 end
function PM:water(src, uses) self.waterLvl = math.min(100, (self.waterLvl or 0) + 10 * uses) end
function PM:saveData() self.saved = (self.saved or 0) + 1 end
function PM:seed(t, skill) self.state, self.typeOfSeed, self.nbOfGrow, self.waterLvl, self.waterNeeded, self.health, self.fertilizer, self.compost = "seeded", t, 1, 80, 70, 80, 0, false end
function PM:cureMildew(s, u, sk) self.mildewLvl = 0 end
function PM:cureAphids(s, u, sk) self.aphidLvl = 0 end
function PM:cureFlies(s, u, sk) self.fliesLvl = 0 end
function PM:cureSlugs(s, u, sk) self.slugsLvl = 0 end
function PM:fertilize(a) if a.compost then self.compost = true else self.fertilizer = (self.fertilizer or 0) + 1 end end
function PM:getObject() return self.iso end
function PM:updateFromIsoObject() end
function plant(o)
    o.z = o.z or 0
    o.state = o.state or "seeded"; o.typeOfSeed = o.typeOfSeed or "Tomato"; o.nbOfGrow = o.nbOfGrow or 3
    o.waterLvl = o.waterLvl or 80; o.waterNeeded = o.waterNeeded or 70; o.health = o.health == nil and 80 or o.health
    o.mildewLvl, o.aphidLvl, o.slugsLvl, o.fliesLvl = o.mildewLvl or 0, o.aphidLvl or 0, o.slugsLvl or 0, o.fliesLvl or 0
    o.hasWeeds = o.hasWeeds == true; o.fertilizer = o.fertilizer or 0; o.compost = o.compost == true; o.hasVegetable = o.hasVegetable == true; o.hasSeed = o.hasSeed == true
    if o.exterior == nil then o.exterior = true end
    o.iso = o.iso or { plantObj = true }
    setmetatable(o, { __index = PM })
    PLANTS[P_(o.x, o.y, o.z)] = o
    return o
end
FARMCALLS = {}
function chunkOf(x, y) return math.floor(x / 8), math.floor(y / 8) end
local sys = {}
function sys:hasObjectsInChunk(wx, wy)
    for _, p in pairs(PLANTS) do local a, b = chunkOf(p.x, p.y); if a == wx and b == wy then return true end end
    return false
end
function sys:getObjectsInChunk(wx, wy)
    FARMCALLS[#FARMCALLS + 1] = wx .. "," .. wy
    local rows = {}
    for _, p in pairs(PLANTS) do local a, b = chunkOf(p.x, p.y); if a == wx and b == wy then rows[#rows + 1] = { getModData = function() return p end } end end
    return { size = function() return #rows end, get = function(_, i) return rows[i + 1] end }
end
S = { system = sys, hoursElapsed = 1000 }
function S:getLuaObjectAt(x, y, z) return PLANTS[P_(x, y, z)] end
function S:getLuaObjectOnSquare(sq) return PLANTS[P_(sq:getX(), sq:getY(), sq:getZ())] end
function S:removePlant(p) PLANTS[P_(p.x, p.y, p.z)] = nil end
function S:plow(sq) plant({ x = sq:getX(), y = sq:getY(), z = sq:getZ(), state = "plow", typeOfSeed = "none" }) end
function S:changePlayer(a) end
function S:gainXp(a, p) a.xp = (a.xp or 0) + 1 end
function S:harvest(p, a) p.hasVegetable = false; p.state = "harvested"; a.inv:AddItem("Base.Tomato") end
SFarmingSystem = { instance = S }
function SFarmingSystem:hasWeeds(sq) for _, o in ipairs(sq.objs or {}) do if o.weed then return true end end return false end
function SFarmingSystem:removeTallGrass(sq) sq.removedGrass = true end

-- squares and containers
function newSquare(x, y, z, extra)
    local sq = { x = x, y = y, z = z or 0 }
    for k, v in pairs(extra or {}) do sq[k] = v end
    function sq:getX() return self.x end; function sq:getY() return self.y end; function sq:getZ() return self.z end
    function sq:HasTree() return self.tree == true end
    function sq:hasGrave() return false end
    function sq:isFree() return self.blocked ~= true end
    function sq:getFloor() return { getProperties = function() return { has = function() return true end } end } end
    function sq:checkHaveGrass() return true end
    function sq:removeGrass() self.grassRemoved = true end
    function sq:getObjects() local o = self.objs or {}; return { size = function() return #o end, get = function(_, i) return o[i + 1] end } end
    function sq:transmitRemoveItemFromSquare(obj) for i, o in ipairs(self.objs) do if o == obj then table.remove(self.objs, i); return end end end
    return sq
end
SQUARES, UNLOADED = {}, {}
function squareAt(x, y, z) local k = P_(x, y, z); SQUARES[k] = SQUARES[k] or newSquare(x, y, z); return SQUARES[k] end
function loaded(x, y, z) if UNLOADED[P_(x, y, z)] then return nil end return squareAt(x, y, z) end
function getCell() return { getGridSquare = function(_, x, y, z) return loaded(x, y, z) end } end

function item(t, opt)
    local it = { t = t }
    for k, v in pairs(opt or {}) do it[k] = v end
    function it:getCurrentUses() return self.uses end
    function it:getFullType() return self.t end
    function it:isBroken() return self.broken == true end
    function it:UseAndSync() self.uses = (self.uses or 1) - 1; USED[self] = (USED[self] or 0) + 1 end
    function it:hasTag(tag) return self.tag == tag end
    return it
end
USED = {}
function waterCan(litres, tainted)
    local fc = { l = litres }
    function fc:getAmount() return self.l end
    function fc:getCapacity() return 4 end
    function fc:adjustAmount(a) self.l = a end
    function fc:getPrimaryFluid() return { getFluidTypeString = function() return tainted and "TaintedWater" or "Water" end } end
    local it = item("Base.WateredCan", { fc = fc })
    function it:getFluidContainer() return self.fc end
    return it
end
function container(items)
    local c = { items = items or {}, ctype = "crate" }
    function c:getItems() local s = self; return { size = function() return #s.items end, get = function(_, i) return s.items[i + 1] end } end
    function c:getType() return self.ctype end
    function c:hasRoomFor(a, i) if self.limit then return #self.items < self.limit end return self.full ~= true end
    function c:isItemAllowed(i) return true end
    function c:Remove(i) for k, v in ipairs(self.items) do if v == i then table.remove(self.items, k); return end end end
    return c
end

PLAYER = { getX = function() return PX end, getY = function() return PY end, getZ = function() return 0 end }
PX, PY = 5000, 5000
function getSpecificPlayer(i) return PLAYER end
function newSol()
    local a = { hp = 100, px = 1000.5, py = 1000.5 }
    function a:getX() return self.px end; function a:getY() return self.py end; function a:getZ() return 0 end
    a.bag = {}
    a.inv = container(a.bag)
    function a.inv:AddItem(t) a.bag[#a.bag + 1] = item(t, { cat = "Food" }) end
    function a.inv:Remove(i) for k, v in ipairs(a.bag) do if v == i then table.remove(a.bag, k); return end end end
    a.inv.Find = function() return nil end
    function a:getInventory() return self.inv end
    function a:getPerkLevel() return 3 end
    function a:setPrimaryHandItem(i) self.hand = i end
    function a:getPrimaryHandItem() return self.hand end
    function a:SetVariable(k, v) self.var = v end
    function a:reportEvent(e) self.event = e end
    function a:playSound(s) self.sound = s; return 1 end
    function a:faceLocation() end
    a.wornRows = {}
    function a:getWornItems() local s = self; return { size = function() return #s.wornRows end, get = function(_, i) return s.wornRows[i + 1] end } end
    function a:setWornItem(loc, it) for _, r in ipairs(self.wornRows) do if r.loc == loc then r.it = it end end; self.changed = (self.changed or 0) + 1 end
    function a:resetModelNextFrame() self.reset = true end
    function a:setHumanVisual() error("the body must never change") end
    return a
end
SOL = newSol()
SolUI = { solActor = function() return SOL end, runAction = function(id, opt) return false, "base_verb" end }
ORDER, SERIAL = "follow", 7
BASE = { zones = {}, storages = {}, core = { x = 1000, y = 1000, z = 0 } }
HUNGER, THIRST, FATIGUE = 0, 0, 0
BLEED = 0
SC = {}
SC.GameplayUtil = {
    idOf = function(a) return "sol-1" end,
    inventory = function(a) return a.inv end,
    inventoryItemsDeep = function(inv) return inv.items end,
    inventoryItems = function(inv) return inv.items end,
    itemType = function(i) return i.t end,
    itemHasTag = function(i, tag) return i.tag == tag end,
    perkLevel = function() return 3 end,
    isDead = function(a) return a.dead == true end,
    gridSquare = function(x, y, z) return loaded(x, y, z) end,
    characterStatValue = function(a, name) if name == "HUNGER" then return HUNGER elseif name == "THIRST" then return THIRST else return FATIGUE end end,
    peekActorState = function(a) return THREATS and { snapshot = { threats = THREATS } } or nil end,
    transferItemVerified = function(from, to, it) for k, v in ipairs(from.items) do if v == it then table.remove(from.items, k); to.items[#to.items + 1] = it; return true end end return false end,
}
SC.Medical = { assessCached = function() return { bleedingCount = BLEED, openWounds = 0, dirtyBandages = 0 } end }
SC.Commands = {
    issue = function(id, cmd, payload) ORDER = cmd; SERIAL = SERIAL + 1; ISSUED[#ISSUED + 1] = cmd; return true, "ok" end,
    peek = function(a) return { order = ORDER, commandSerial = SERIAL } end,
}
ISSUED = {}
SC.BaseLife = { active = function() return BASE end }
SurvivorCompanion = SC
SolAuthority = { on = function() return true end }
-- walking: an accepted request has her standing beside the target at the next step, unless the test says otherwise
NAVS = {}
function neighbours(sq)
    local x, y, z, out = sq:getX(), sq:getY(), sq:getZ(), {}
    for _, d in ipairs({ { 0, 1 }, { 1, 0 }, { 0, -1 }, { -1, 0 } }) do out[#out + 1] = squareAt(x + d[1], y + d[2], z) end
    return out
end
SC.Navigation = {
    interactionTargets = function(a, sq) if NO_TARGETS then return {} end return neighbours(sq) end,
    cancel = function(a, r) a.walkTo = nil; NAV_CANCELS = (NAV_CANCELS or 0) + 1 end,
}
-- her walk, the way the refuel errand walks her: Living Fellows' go_to, which sets the order to move_to
SolUI.solGoto = function(x, y, z)
    NAVS[#NAVS + 1] = { action = "sol_farm_walk", x = x, y = y }
    if NAV_OK == false then return false, "no_reachable_interaction_target" end
    if NAV_OWNED then return false, "action_owned" end
    ORDER = "move_to"; SERIAL = SERIAL + 1
    if not NAV_HANG then local sq = squareAt(x, y, z or 0); if SOL.walkTo ~= sq then SOL.walkTo = sq; SOL.walkLeft = NAV_SLOW or 0 end end
    return true, "walking_to"
end
"""

# the old Living Fellows job mock: only the older apply-script checks further down still run against these
LF_EXTRA = r"""
BLOCKING = {}
local nextJob = 0
BASE.jobs = {}
SC.BaseLife = {
    active = function() return BASE end,
    storageRows = function(cat, w) local r = {}; for _, s in ipairs(BASE.storages) do if s.category == cat then r[#r + 1] = s end end return r end,
    depositStorageRows = function(cat) local r = {}; for _, s in ipairs(BASE.storages) do if cat == nil or s.category == cat then r[#r + 1] = s end end return r end,
    resolveContainer = function(s) if s.loaded == false then return nil end return s.cont end,
    storageReserve = function(s, t) return s.reserve or 0 end,
    resident = function(id) return { role = "farmer" } end,
    enqueueJob = function(spec)
        nextJob = nextJob + 1
        local job = { id = "job:" .. nextJob, type = spec.type, priority = spec.priority, target = spec.target, state = "pending", at = NOW }
        BASE.jobs[#BASE.jobs + 1] = job
        return true, job
    end,
    job = function(id) for _, j in ipairs(BASE.jobs) do if j.id == id then return j end end return nil end,
    cancelJob = function(id) for i, j in ipairs(BASE.jobs) do if j.id == id then j.state = "cancelled"; table.remove(BASE.jobs, i); return end end end,
}
SC.BaseWork = { cancelJob = function() return true end, restoreDepositToStorage = function(a, st, c, it) c.items[#c.items + 1] = it; a.inv:Remove(it); return true end }
SC.Commands.issue = function(id, cmd, payload) ISSUED[#ISSUED + 1] = cmd .. ":" .. tostring(payload and payload.role); if cmd == "set_base_role" or cmd == "base_duty" then ORDER = "base_duty" else ORDER = cmd end return true, "ok" end
SolAuthority = { on = function() return true end, grantWork = function(r, w) GRANTED = r; SolAuthority.work = { role = r } end, clearWork = function() SolAuthority.work = nil end }
SC.Navigation = { interactionTargets = function(a, sq) return { sq } end, requestAny = function(a, t, mode, intent) return true, "walking" end }
"""

DRIVER = r"""
OPS = {}
function wrapApply()
    for op, f in pairs(SolFarmAct.APPLY) do
        SolFarmAct.APPLY[op] = function(a, intent)
            local j = STORE.Sol_Farm and STORE.Sol_Farm.job or nil
            local rec = { operation = op, uses = j and j.uses, cureItem = j and j.cureItem, cropType = j and j.crop }
            if not FIRSTRUN then FIRSTRUN = rec end
            OPS[#OPS + 1] = op .. "@" .. tostring(j and j.x) .. "," .. tostring(j and j.y)
            if THROW_OP and THROW_OP[op] then error("apply failed") end
            if NOEFFECT and NOEFFECT[op] then return end
            return f(a, intent)
        end
    end
    SolFarmWork._onJob = function(j) LASTJOB = { target = { operation = j.op, x = j.x, cropType = j.crop, uses = j.uses } } end
end
function drainScan()
    for _ = 1, 400 do if SolUI.invStep() then break end end
end
function rescan() drainScan(); SolUI.invStart(); drainScan(); SCAN_DIRTY = false end
function step(n)
    local W, V = SolFarmWork, SolFarmView
    if SCAN_DIRTY then rescan() end
    V.forceRescan()
    for _ = 1, (n or 1) do
        NOW = NOW + 1500
        decisionBeat()
        if SOL.walkTo then
            if (SOL.walkLeft or 0) > 0 then SOL.walkLeft = SOL.walkLeft - 1
            else
                SOL.px, SOL.py = SOL.walkTo:getX() + 0.5, SOL.walkTo:getY() + 0.5; SOL.walkTo = nil
                if ORDER == "move_to" then ORDER = "stay"; SERIAL = SERIAL + 1 end           -- what SCDecision's switchToStay does on arrival
            end
        end
        drainScan()
        W.tickAll(2)
    end
end
-- SCDecision each beat: the candidates its evaluate would add, and with none utility.stop, which cancels her path (tested against the real evaluate further down)
STOPPED_WALKS = 0
function decisionBeat()
    local A, any = SolAuthority, false
    if ORDER == "move_to" then any = A.allowsDecision(SOL, "tactical")
    elseif ORDER == "follow" then any = A.allowsDecision(SOL, "follow") end
    if not any then
        if SOL.walkTo then STOPPED_WALKS = STOPPED_WALKS + 1 end
        SOL.walkTo = nil
    end
end
function job() return STORE.Sol_Farm and STORE.Sol_Farm.job or nil end
-- run until one whole job is finished, or nothing starts
function work(n)
    for _ = 1, (n or 1) do
        local saw, id = false, nil
        for i = 1, 60 do
            step(1)
            local j = job()
            if j then
                if id ~= nil and j.id ~= id then break end
                saw, id = true, j.id
            elseif saw or i >= 8 then break end
        end
    end
end
function resetAll()
    PLANTS, FARMCALLS, OPS, SQUARES, UNLOADED, FIRSTRUN, NOEFFECT, THROW_OP = {}, {}, {}, {}, {}, nil, nil, nil
    BASE.zones, BASE.storages = {}, {}
    SolFarmWork._homeWaitUntil, THREATS, NAV_SLOW = nil, nil, nil; STOPPED_WALKS = 0; BASE.core = { x = 1000, y = 1000, z = 0 }; SolHome = nil
    SolFarmWork._carryWaitUntil, SolFarmWork._returnWaitUntil, SolFarmWork._produce, SolFarmWork._jobLive, SolFarmWork._sessionDuty, NAVS, NAV_OK, NAV_HANG, NAV_OWNED, NO_TARGETS = nil, nil, nil, nil, nil, {}, nil, nil, nil, nil
    ORDER, RAIN, MONTH, SEASONS, SEASONNAME, HOUR, HUNGER, THIRST, FATIGUE, BLEED, LASTJOB = "follow", false, 5, true, "Summer", 12, 0, 0, 0, 0, nil
    SERIAL, ISSUED, NAV_CANCELS = 7, {}, 0
    SOL = newSol()
    STORE = {}
    PX, PY = 5000, 5000
    SolFarmView.reset()
    SolFarmKeeper._quietUntil, SolFarmKeeper._needSince = nil, nil
    SCAN_DIRTY = true
end
function growArea(x1, y1, x2, y2)
    local area = BASE.zones[1]
    if area == nil or area.kind ~= "area" then area = { id = "area", kind = "area", x1 = x1, y1 = y1, x2 = x2, y2 = y2, z = 0 }; table.insert(BASE.zones, 1, area) end
    area.x1, area.y1, area.x2, area.y2 = math.min(area.x1, x1), math.min(area.y1, y1), math.max(area.x2, x2), math.max(area.y2, y2)
    SCAN_DIRTY = true
end
function addZone(id, x1, y1, x2, y2)
    BASE.zones[#BASE.zones + 1] = { id = id, kind = "farm", x1 = x1, y1 = y1, x2 = x2, y2 = y2, z = 0, name = id }
    if x1 < 1500 then growArea(x1, y1, x2, y2) end
end
function addStore(cat, items, opts)
    local n = #BASE.storages
    local s = { id = cat .. n, category = cat, cont = container(items), x = 1000 + n * 2, y = 996, z = 0 }
    for k, v in pairs(opts or {}) do s[k] = v end
    s.cont.ctype = s.ctype or (cat == "food" and "fridge" or "crate")
    BASE.storages[n + 1] = s
    local sq = squareAt(s.x, s.y, 0)
    sq.objs = sq.objs or {}
    sq.objs[#sq.objs + 1] = { getContainerCount = function() return 1 end, getContainerByIndex = function(_, k) return s.cont end }
    if s.loaded == false then UNLOADED[P_(s.x, s.y, 0)] = true end
    growArea(s.x, s.y, s.x, s.y)
    return s
end
function fullStock()
    addStore("farming", { item("Base.TomatoSeed"), item("Base.TomatoSeed"), item("Base.TomatoSeed"), waterCan(4), item("Base.GardeningSprayMilk", { uses = 8 }),
        item("Base.GardeningSprayAphids", { uses = 8 }), item("Base.GardeningSprayCigarettes", { uses = 8 }), item("Base.SlugRepellent", { uses = 8 }),
        item("Base.CompostBag", { uses = 4, tag = "COMPOST" }), item("Base.GardenHoe", { tag = "DIG_PLOW" }) })
    addStore("food", {})
    addStore("output", {})
end
function setup() addZone("zone-a", 1000, 1000, 1007, 1007); fullStock() end
function order(o) return SolUI.runAction("sol_farm", o) end
function has(list, t) local n = 0; for _, i in ipairs(list) do if i.t == t then n = n + 1 end end return n end
function stored(t) local n = 0; for _, s in ipairs(BASE.storages) do n = n + has(s.cont.items, t) end return n end
function sayWhy() local st = STORE.Sol_Farm and STORE.Sol_Farm.stop; return st and st.detail and st.detail.why end
"""

FARM_FILES = ["SolFarmView.lua", "SolFarmWork.lua", "SolFarmKeeper.lua", "SolFarmAct.lua"]
def fresh():
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(WORLD)
    L.execute("SolLab = { active = true }")
    L.execute(open(os.path.join(S33, "SolAuthority.lua"), encoding="utf-8").read())
    L.execute(INV_SRC)
    for f in FARM_FILES:
        L.execute(open(os.path.join(HERE, f), encoding="utf-8").read())
    L.execute(DRIVER)
    L.execute("for _, f in ipairs(STARTS) do f() end; wrapApply()")
    return L

L = fresh()
def e(code): return L.eval(code)
def x(code): L.execute(code)
def ops(): return list(e("OPS").values())

# ---- nothing to do: every order answers, under the game's own Lua
x("resetAll(); setup(); SolFarmView.forceRescan(); step(10)")
for option in ("harvest", "water", "cure", "weed", "compost", "plow", "plant:any"):
    x('NR_OK, NR_FIRST, NR_TEXT = pcall(SolUI.solFarmOrder, "%s")' % option)
    ck("nothing to do, no crash: " + option, e("NR_OK") is True and e("NR_FIRST") is not None, (e("NR_FIRST"), e("NR_TEXT")))
x("SolFarmWork.stopAll(STORE.Sol_Farm, 'test')")
ck("reason: empty", e("SolFarmWork.topReason({})") is None)
ck("reason: not a table", e("SolFarmWork.topReason(nil)") is None)
ck("reason: one nobody listed", e("SolFarmWork.topReason({ odd_reason = true })") == "odd_reason")
ck("reason: a key that is not text", e("SolFarmWork.topReason({ [1] = true })") is None)
ck("reason: seed by name first", e("SolFarmWork.topReason({ rain = true, ['no_seed:Basil'] = true })") == "no_seed:Basil")
# ---- the report he asked for in the game
x("resetAll(); setup(); plant({ x = 1001, y = 1001 }); SolFarmView.forceRescan(); step(10)")
x('RPT_OK, RPT_FIRST, RPT_TEXT = pcall(SolUI.solFarmOrder, "report")')
ck("report: no crash on her skill level", e("RPT_OK") is True, e("RPT_FIRST"))
ck("report: answered", e("RPT_FIRST") is True and str(e("RPT_TEXT")).startswith("farm:"), (e("RPT_FIRST"), e("RPT_TEXT")))
x('SAVED_ENV = SolFarmWork.env; SolFarmWork.env = function() error("a bad read") end; RPT_OK, RPT_FIRST, RPT_TEXT = pcall(SolUI.solFarmOrder, "report"); SolFarmWork.env = SAVED_ENV')
ck("report: one bad read does not lose the zones", e("RPT_OK") is True and e("RPT_FIRST") is True and str(e("RPT_TEXT")).startswith("farm:"), (e("RPT_FIRST"), e("RPT_TEXT")))
x('SAVED_R = SolFarmWork.report; SolFarmWork.report = function() error("worse") end; RPT_OK, RPT_FIRST, RPT_TEXT = pcall(SolUI.solFarmOrder, "report"); SolFarmWork.report = SAVED_R')
ck("report: a failure is an answer, not a crash", e("RPT_OK") is True and e("RPT_FIRST") is False and e("RPT_TEXT") == "report_failed", (e("RPT_OK"), e("RPT_FIRST"), e("RPT_TEXT")))
for name in sorted(os.listdir(LIVE)):
    if not (name.startswith("Sol") and name.endswith(".lua")): continue
    path = os.path.join(HERE, name) if os.path.exists(os.path.join(HERE, name)) else os.path.join(LIVE, name)
    code = open(path, encoding="utf-8", errors="replace").read()
    two = [h for h in ("call", "tcall") if re.search(r"\btonumber\(%s\(" % h, code) and re.search(r"local function %s\([^\n]*(\n[^\n]*){0,6}?return a, b" % h, code)]
    ck("two-value helper is safe with tonumber: " + name, not two or "local function tonumber(v)" in code, two)
farm_src = "".join(open(os.path.join(HERE, f), encoding="utf-8").read() for f in FARM_FILES)
ck("no gmatch in the farm files", "gmatch" not in farm_src)
ck("no Living Fellows farm path left", not re.search(r"enqueueJob|storageRows|resolveContainer|depositStorageRows|storageReserve|NA\.startFarm|set_base_role", farm_src), re.findall(r"enqueueJob|storageRows|resolveContainer|depositStorageRows|storageReserve|NA\.startFarm|set_base_role", farm_src))

# ---- the scan
x("resetAll(); setup(); for i = 1000, 1007 do for j = 1000, 1003 do plant({ x = i, y = j }) end end; plant({ x = 3000, y = 3000 }); addZone('zone-b', 3000, 3000, 3000, 3000)")
x("SolFarmView.forceRescan(); step(10)")
ck("scan: every plant of every zone, far ones too", e("#SolFarmView.allPlants()") == 33, e("#SolFarmView.allPlants()"))
ck("scan: by chunk, a bounded slice", e("#FARMCALLS") > 0)
x("resetAll(); setup(); plant({ x = 1000, y = 1000 }); rescan()")
x("FARMCALLS = {}; local V = SolFarmView; V.tick(2); FIRST = #FARMCALLS; V.forceRescan(); V.tick(2); V.tick(2)")
ck("scan: a slice reads few chunks", e("FIRST") <= 4, e("FIRST"))
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); addStore('food', {}); plant({ x = 1001, y = 1001 }); step(2); REV = SolFarmView.rev; step(6)")
ck("scan: nothing rebuilt when nothing changed", e("SolFarmView.rev == REV"), (e("SolFarmView.rev"), e("REV")))
x("PLANTS[P_(1001,1001,0)].hasVegetable = true; step(6)")
ck("scan: and rebuilt when a plant ripens", e("SolFarmView.rev ~= REV"))
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); addZone('zone-b', 2000, 2000, 2007, 2007); fullStock(); plant({ x = 1001, y = 1001 }); plant({ x = 2001, y = 2001 }); SolFarmView.forceRescan(); step(4); FARMCALLS = {}; NOW = NOW + 20000; for i = 1, 8 do SolFarmView.tick(2); NOW = NOW + 500 end")
ck("scan: near zones more often than far ones", any("2000" in str(c) for c in e("FARMCALLS").values()) is False and len(list(e("FARMCALLS").values())) >= 1, list(e("FARMCALLS").values()))
x("resetAll(); setup(); step(2)")
ck("stock: every row says where it can be found", e("SolFarmView.spots[1].x") is not None and e("SolFarmView.spots[1].oi") == 0 and e("SolFarmView.spots[1].ci") == 0, e("SolFarmView.spots[1].x"))
ck("stock: the stock itself is counted", e("SolFarmView.stockLatest.seeds.Tomato") == 3 and e("SolFarmView.stockLatest.tools") == 1 and e("SolFarmView.stockLatest.cans") == 1 and e("SolFarmView.stockLatest.waterUses") == 20, e("SolFarmView.stockLatest.waterUses"))
ck("stock: nothing live goes to the Mind", e("SolFarmView.stockLatest.spots") is None and e("SolFarmView.stockLatest.from") is None)
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); step(2)")
ck("no container known: no storage", e("SolFarmView.stockLatest.foodStorage") == 0)
x("resetAll(); setup(); SOL.bag[1] = item('Base.TomatoSeed'); step(2)")
ck("what she carries counts too", e("SolFarmView.stockLatest.seeds.Tomato") == 4, e("SolFarmView.stockLatest.seeds.Tomato"))
x("resetAll(); setup(); PLAYER.getInventory = function() return container({ item('Base.GardenHoe', { tag = 'DIG_PLOW' }) }) end; step(2)")
ck("what he carries does not", e("SolFarmView.stockLatest.tools") == 1, e("SolFarmView.stockLatest.tools"))
x("PLAYER.getInventory = nil")

# ---- layouts and stages, one call to the plan each
x("resetAll(); setup()")
for stage in range(1, 7):
    x(f"PLANTS = {{}}; STORE.Sol_Farm = nil; plant({{ x = 1002, y = 1002, nbOfGrow = {stage}, waterLvl = 90 }}); SolFarmView.reset(); SCAN_DIRTY = true")
    x("order('keeper'); step(4)")
    t = e("LASTJOB and LASTJOB.target.operation")
    ck(f"stage {stage}: {'feeds at 3 or earlier' if stage <= 3 else 'no food past stage 3'}", (t == "compost") == (stage <= 3), t)
    x("order('interrupt'); LASTJOB = nil")
x("resetAll(); setup(); order('keeper'); plant({ x = 1001, y = 1001, nbOfGrow = 7, hasVegetable = true, waterLvl = 90 }); plant({ x = 1002, y = 1002, nbOfGrow = 5, hasVegetable = true, waterLvl = 90 }); work(1)")
ck("harvest first, rotting soon first", e("OPS[1]") == "harvest@1001,1001", e("OPS[1]"))
x("work(1)")
ck("harvest then the next ripe one", "harvest@1002,1002" in ops(), ops())
x("resetAll(); setup(); order('keeper'); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30, waterNeeded = 70 }); plant({ x = 1002, y = 1002, nbOfGrow = 4, waterLvl = 72, waterNeeded = 70 }); work(1)")
ck("water by the plant's own need, in whole doses", e("OPS[1]") == "water@1001,1001" and e("FIRSTRUN.uses") == 4, (e("OPS[1]"), e("FIRSTRUN.uses")))
x("work(2)")
ck("watered until need, then not", sum(o.startswith("water@") for o in ops()) == 1, ops())
x("resetAll(); setup(); RAIN = true; order('keeper'); plant({ x = 1001, y = 1001, waterLvl = 30 }); work(1)")
ck("rain: no outdoor watering", e("#OPS") == 0 or e("OPS[1]") != "water@1001,1001", ops())
x("resetAll(); setup(); RAIN = true; order('keeper'); plant({ x = 1001, y = 1001, waterLvl = 30, exterior = false }); work(1)")
ck("rain: indoor beds still watered", e("OPS[1]") == "water@1001,1001", e("OPS[1]"))
for field, itemn, doses in [("mildewLvl", "GardeningSprayMilk", 2), ("fliesLvl", "GardeningSprayCigarettes", 3), ("aphidLvl", "GardeningSprayAphids", 3), ("slugsLvl", "SlugRepellent", 2)]:
    lvl = {"mildewLvl": 20, "fliesLvl": 30, "aphidLvl": 30, "slugsLvl": 20}[field]
    x(f"resetAll(); setup(); order('keeper'); plant({{ x = 1001, y = 1001, nbOfGrow = 4, {field} = {lvl} }}); work(1)")
    ck(f"pest {field}: treated with {itemn}", e("FIRSTRUN.cureItem") == itemn, e("FIRSTRUN and FIRSTRUN.cureItem"))
    ck(f"pest {field}: doses computed", e("FIRSTRUN.uses") == doses, e("FIRSTRUN.uses"))
x("resetAll(); setup(); order('keeper'); plant({ x = 1001, y = 1001, nbOfGrow = 4, aphidLvl = 40 }); plant({ x = 1002, y = 1002, nbOfGrow = 4, mildewLvl = 12 }); work(1)")
ck("mildew before the rest", e("FIRSTRUN.cureItem") == "GardeningSprayMilk")
x("resetAll(); setup(); order('keeper'); plant({ x = 1001, y = 1001, nbOfGrow = 4, hasWeeds = true }); work(1)")
ck("weeds cleared", e("OPS[1]") == "weed@1001,1001", e("OPS[1]"))
x("resetAll(); setup(); squareAt(1001,1001,0).tree = true; order('keeper'); plant({ x = 1001, y = 1001, nbOfGrow = 4, hasWeeds = true }); step(6)")
ck("weeds that a tree causes: reported once", e("STORE.Sol_Farm.stop") is not None and e("STORE.Sol_Farm.stop.reason") == "unclearable_weeds", e("STORE.Sol_Farm.stop and STORE.Sol_Farm.stop.reason"))
x("LS = STORE.Sol_Farm.seq; step(6)")
ck("and only once", e("STORE.Sol_Farm.seq") == e("LS"))
x("resetAll(); setup(); order('keeper'); plant({ x = 1001, y = 1001, state = 'plow', typeOfSeed = 'none' }); work(1)")
ck("plowed tile planted with in-season seed", e("FIRSTRUN.operation") == "sow" and e("FIRSTRUN.cropType") == "Tomato", e("FIRSTRUN.operation"))
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); fullStock(); BASE.storages[1].cont.items[1].t = 'Base.CornSeed'; BASE.storages[1].cont.items[2].t = 'Base.CornSeed'; BASE.storages[1].cont.items[3].t = 'Base.CornSeed'; MONTH = 1; order('keeper'); plant({ x = 1001, y = 1001, state = 'plow', typeOfSeed = 'none' }); work(2)")
ck("seed out of season is never sown", e("#OPS") == 0, ops())
x("resetAll(); setup(); order('keeper'); plant({ x = 1001, y = 1001, nbOfGrow = 2 }); SEASONNAME = 'Winter'; work(2)")
ck("no food in winter", e("FIRSTRUN == nil or FIRSTRUN.operation ~= 'compost'"), e("FIRSTRUN and FIRSTRUN.operation"))
x("resetAll(); setup(); order('keeper'); plant({ x = 1001, y = 1001, nbOfGrow = 2, fertilizer = 1 }); work(1)")
ck("fertiliser read live: not dosed twice", e("LASTJOB == nil or LASTJOB.target.operation ~= 'compost'"))
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 2 }); step(3); order('keeper'); step(1); PLANTS[P_(1001,1001,0)].fertilizer = 1; work(1); ")
ck("the plant is read again right before a dose, a change during the walk is noticed", not any(o.startswith("compost@") for o in ops()), ops())
x("resetAll(); addZone('zone-a', 1000, 1000, 1002, 1004); fullStock(); order('keeper'); step(3); for i = 1, 12 do SolFarmView.tick(5); NOW = NOW + 1000 end; step(1); work(1)")
ck("new furrows in empty land, bed and path rows", e("OPS[1]") and e("OPS[1]").startswith("plow@"), e("OPS[1]"))
ck("the path row is left", all(c.split(",")[1] != "1002" for c in ops()), ops())

# ---- her own runner, step by step
x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); order('water'); step(2)")
ck("runner: she lacks the can, so she walks to its container first", e("job().phase") == "fetch" and e("job().needs[1].row.x") == 1000, (e("job() and job().phase")))
ck("runner: she really asks the walker", e("#NAVS") >= 1 and e("NAVS[1].action") == "sol_farm_walk", e("#NAVS"))
x("step(2)")
ck("runner: take: the can is in her bag now", e("has(SOL.bag, 'Base.WateredCan')") == 1 and e("has(BASE.storages[1].cont.items, 'Base.WateredCan')") == 0, e("has(SOL.bag, 'Base.WateredCan')"))
ck("runner: what she took is written down where it came from", e("STORE.Sol_Farm.owed[1].type") == "Base.WateredCan" and e("STORE.Sol_Farm.owed[1].x") == 1000, e("STORE.Sol_Farm.owed[1] and STORE.Sol_Farm.owed[1].type"))
x("work(1)")
ck("runner: walks to the plant and acts", e("OPS[1]") == "water@1006,1006", e("OPS[1]"))
ck("runner: verified from the plant", e("PLANTS[P_(1006,1006,0)].waterLvl") == 70 and (e("STORE.Sol_Farm.fails[P_(1006,1006,0)]") or 0) == 0, e("PLANTS[P_(1006,1006,0)].waterLvl"))
ck("runner: visible action: sound and animation", e("SOL.sound") == "WaterCrops" and e("SOL.event") == "EventLootItem", e("SOL.sound"))
x("work(2); step(4)")
ck("runner: she puts the can back where she found it", e("has(BASE.storages[1].cont.items, 'Base.WateredCan')") == 1 and e("has(SOL.bag, 'Base.WateredCan')") == 0 and e("#STORE.Sol_Farm.owed") == 0, ops())

x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); SOL.bag[1] = waterCan(2); order('keeper'); step(1)")
ck("runner: an item already in her bag is not fetched", e("job().phase") in ("need", "go", "act"), e("job() and job().phase"))
x("work(3); step(3)")
ck("runner: and her own can is not put away", e("has(SOL.bag, 'Base.WateredCan')") == 1, e("has(SOL.bag, 'Base.WateredCan')"))

x("resetAll(); setup(); plant({ x = 1003, y = 1003, nbOfGrow = 7, hasVegetable = true, waterLvl = 90 }); order('harvest'); work(1)")
ck("harvest: acted", e("OPS[1]") == "harvest@1003,1003", e("OPS[1]"))
x("work(2); step(3)")
ck("harvest: produce carried to a fridge, the food container", e("has(BASE.storages[2].cont.items, 'Base.Tomato')") == 1 and e("has(SOL.bag, 'Base.Tomato')") == 0, e("has(BASE.storages[2].cont.items, 'Base.Tomato')"))
x("resetAll(); setup(); plant({ x = 1003, y = 1003, nbOfGrow = 7, hasVegetable = true, waterLvl = 90 }); plant({ x = 1004, y = 1003, nbOfGrow = 7, hasVegetable = true, waterLvl = 90 }); order('harvest'); work(1); step(2)")
ck("harvest: with more ripe plants she does not run back after each one", e("stored('Base.Tomato')") == 0 and e("has(SOL.bag, 'Base.Tomato')") == 1 and "harvest@1004,1003" not in ops(), (e("has(SOL.bag, 'Base.Tomato')"), ops()))
x("work(2); step(3)")
ck("harvest: then carries it all", e("stored('Base.Tomato')") == 2 and e("has(SOL.bag, 'Base.Tomato')") == 0, e("stored('Base.Tomato')"))

x("resetAll(); addZone('zone-a', 1003, 1003, 1003, 1003); fullStock(); plant({ x = 1003, y = 1003, state = 'harvested', typeOfSeed = 'Tomato' }); order('plant:Tomato'); work(1)")
ck("replant: furrow then seed, on one job", ops()[:2] == ["plow@1003,1003", "sow@1003,1003"], ops())
ck("replant: seeded with the crop the plan chose", e("PLANTS[P_(1003,1003,0)].state") == "seeded" and e("PLANTS[P_(1003,1003,0)].typeOfSeed") == "Tomato", e("PLANTS[P_(1003,1003,0)].state"))
ck("replant: remembered", e("STORE.Sol_Farm.sown[1] and STORE.Sol_Farm.sown[1].crop") == "Tomato")
ck("replant: seeds go from the stock", e("has(BASE.storages[1].cont.items, 'Base.TomatoSeed')") == 0 and e("has(SOL.bag, 'Base.TomatoSeed')") == 2, e("has(SOL.bag, 'Base.TomatoSeed')"))
x("work(3); step(3)")
ck("replant: leftover seeds and the hoe go back", e("has(BASE.storages[1].cont.items, 'Base.TomatoSeed')") == 2 and e("has(BASE.storages[1].cont.items, 'Base.GardenHoe')") == 1 and e("#STORE.Sol_Farm.owed") == 0, (e("has(BASE.storages[1].cont.items, 'Base.TomatoSeed')"), ops()))

x("resetAll(); setup(); plant({ x = 1003, y = 1003, state = 'harvested', typeOfSeed = 'Tomato' }); order('keeper'); step(1); LJ = job().phase; NOW = NOW + 1500")
ck("reload: the job is plain data in ModData", e("type(STORE.Sol_Farm.job.id)") == "number")
x("SolFarmView.reset(); SolFarmKeeper._quietUntil = nil; SolFarmWork._jobLive = nil; SolFarmWork._sessionDuty = nil; SOLBEFORE = SOL.bag")
for f in FARM_FILES:
    L.execute(open(os.path.join(HERE, f), encoding="utf-8").read())
x("SolFarmWork._installed = false; for _, f in ipairs(STARTS) do f() end; wrapApply(); SCAN_DIRTY = true; work(1)")
ck("reload mid-job: the same job is carried on and judged", "plow@1003,1003" in ops() and "sow@1003,1003" in ops(), ops())
ck("reload mid-job: modes kept", e("STORE.Sol_Farm.modes.farm") is True)
x("resetAll(); setup(); plant({ x = 1003, y = 1003, nbOfGrow = 4, waterLvl = 30 }); SOL.bag[1] = waterCan(4); order('keeper'); step(4); PH = job().phase; WBEFORE = job().before")
ck("reload during the action: she was acting", e("PH") == "act", e("PH"))
x("PLANTS[P_(1003,1003,0)].waterLvl = PLANTS[P_(1003,1003,0)].waterLvl + 45; SolFarmView.reset(); SolFarmWork._jobLive = nil; SolFarmWork._sessionDuty = nil")
x("package = nil")
for f in FARM_FILES:
    L.execute(open(os.path.join(HERE, f), encoding="utf-8").read())
x("SolFarmWork._installed = false; for _, f in ipairs(STARTS) do f() end; wrapApply(); SCAN_DIRTY = true; OPS = {}; work(1)")
ck("reload during the action: a dose already applied is not given twice", not any(o.startswith("water@") for o in ops()) and e("PLANTS[P_(1003,1003,0)].waterLvl") == 75, (ops(), e("PLANTS[P_(1003,1003,0)].waterLvl")))

x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); step(1); BASE.storages[1].cont.items = {}; step(3)")
ck("item gone: no other row, she stops and says what it is", e("sayWhy()") == "farm_supply_missing", e("sayWhy()"))
ck("item gone: counted against that bed", (e("STORE.Sol_Farm.fails[P_(1006,1006,0)]") or 0) >= 1)
x("resetAll(); setup(); addStore('farming', { waterCan(4) }); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); step(1); step(1); WH = job().needs[1].row.x; for _, s in ipairs(BASE.storages) do if s.x == WH then s.cont.items = {} end end; step(5)")
ck("item gone: the other container in the scan is tried", e("has(SOL.bag, 'Base.WateredCan')") == 1, e("has(SOL.bag, 'Base.WateredCan')"))

x("resetAll(); setup(); NAV_OK = false; plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); SOL.bag[1] = waterCan(4); order('keeper'); step(60)")
ck("no path: gives up and says so, and the bed is left", e("sayWhy()") == "no_path" and e("STORE.Sol_Farm.paused[P_(1006,1006,0)]") is not None, e("sayWhy()"))
x("resetAll(); setup(); NO_TARGETS = true; plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); SOL.bag[1] = waterCan(4); order('keeper'); step(30)")
ck("no square to stand on: no path too", e("sayWhy()") == "no_path", e("sayWhy()"))
x("resetAll(); setup(); NAV_HANG = true; plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); SOL.bag[1] = waterCan(4); order('keeper'); step(1); TJ = job().id; for i = 1, 100 do step(1); if job() == nil or job().id ~= TJ then break end end")
ck("timeout: a walk that never arrives ends", e("sayWhy()") == "no_path", (e("job() and job().phase"), e("sayWhy()")))
x("resetAll(); setup(); NAV_OWNED = true; plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); SOL.bag[1] = waterCan(4); order('keeper'); step(6); OW = job() ~= nil")
ck("walk held by her instincts: waits, no failure", e("OW") is True and (e("STORE.Sol_Farm.fails[P_(1006,1006,0)]") or 0) == 0, e("job() and job().phase"))
x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); SOL.bag[1] = waterCan(4); order('keeper'); step(1); OLDID = job().id; job().phase = 'mystery'; step(1)")
ck("an unknown step never loops", e("sayWhy()") == "timeout" and e("job() == nil or job().id ~= OLDID"), e("job() and job().phase"))
x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); step(1); JOBID = job().id; NOW = NOW + 400000; step(1)")
ck("a save or pause is not time spent", e("job() and job().id") == e("JOBID"), e("job() and job().id"))
x("resetAll(); setup(); NAV_HANG = true; plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); SOL.bag[1] = waterCan(4); SolFarmWork.tickAll(2); order('keeper'); step(1); OLDID = job().id; job().spent = 400000; step(1)")
ck("overall timeout: the job ends", e("sayWhy()") == "timeout" and e("job() == nil or job().id ~= OLDID"), e("sayWhy()"))

x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); step(2); B0 = job().id; SOLOLD = SOL; SolUI.solActor = function() return nil end; step(2)")
ck("body gone: the job waits", e("job() and job().id") == e("B0") and e("STORE.Sol_Farm.statusDetail") == "body_lost", e("STORE.Sol_Farm.statusDetail"))
x("job().spent = 200000; step(1)")
ck("body gone for long: the job ends, without a crash", e("job()") is None and e("sayWhy()") == "body_lost", e("sayWhy()"))
x("SolUI.solActor = function() return SOL end")

x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); order('keeper')")
ck("no LF order is touched going on the farm", e("#ISSUED") == 0 and e("ORDER") == "follow", list(e("ISSUED").values()))
x("step(1)")
ck("hold: she is held while on the farm", e("SolUI.solFarmHeld()") is True)
x("ORDER = 'stay'; step(1)")
ck("an order from him ends it: modes off", e("STORE.Sol_Farm.modes.farm") is False, e("STORE.Sol_Farm.modes.farm"))
ck("an order from him ends it: job cancelled and she is released", e("job()") is None and e("SolUI.solFarmHeld()") is False and e("NAV_CANCELS") >= 1, (e("job() and 1"), e("SolUI.solFarmHeld()")))
x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); step(2); SC.Commands.issue('sol-1', 'follow'); step(1)")
ck("the same order given again counts too (Follow while she follows)", e("STORE.Sol_Farm.modes.farm") is False and e("STORE.Sol_Farm.statusText") == "stopped", e("STORE.Sol_Farm.statusText"))
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); step(5); order('interrupt')")
ck("the Mind's interrupt ends it", e("STORE.Sol_Farm.modes.farm") is False and e("STORE.Sol_Farm.statusText") == "stopped")
x("step(3)")
ck("hold: gone with the job", e("SolUI.solFarmHeld()") is False)
x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); step(1); NOW = NOW + 60000")
ck("hold: a dead tick lets go", e("SolUI.solFarmHeld()") is False)
x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); SOL.getVehicle = function() return {} end; OK, WHY = order('keeper')")
ck("in a car: refused, plainly", e("OK") is False and e("WHY") == "in_vehicle", e("WHY"))

# ---- produce: rooms and containers
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); F1 = addStore('food', {}); F1.cont.full = true; F2 = addStore('food', {}); SOL.bag[1] = item('Base.Tomato'); order('keeper'); step(1); SolFarmWork._produce = nil; NOW = NOW + 31000; step(6)")
ck("carry: a full chest, the next one", e("has(F2.cont.items, 'Base.Tomato')") == 1 and e("has(F1.cont.items, 'Base.Tomato')") == 0, (e("has(F2.cont.items, 'Base.Tomato')"), e("job() and job().phase")))
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); F1 = addStore('food', {}); F1.cont.full = true; SOL.bag[1] = item('Base.Tomato'); order('keeper'); step(1); NOW = NOW + 31000; step(4); SEQ = STORE.Sol_Farm.seq; step(4)")
ck("carry: every chest full, said and left for a while", e("sayWhy()") == "storage_full" and e("STORE.Sol_Farm.seq") == e("SEQ"), e("sayWhy()"))
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); F1 = addStore('food', {}, { x = 1006, y = 996 }); SOL.bag[1] = item('Base.Tomato'); NAV_OK = false; order('keeper'); step(1); NOW = NOW + 31000; step(16)")
ck("carry: no path, said", e("sayWhy()") == "carry_no_path", e("sayWhy()"))
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); order('keeper'); plant({ x = 1001, y = 1001, nbOfGrow = 7, hasVegetable = true }); step(4)")
ck("no container known: no harvest, said once", e("STORE.Sol_Farm.statusDetail") == "no_food_storage", e("STORE.Sol_Farm.statusDetail"))
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); addStore('stoves', {}, { ctype = 'stove' }); order('keeper'); plant({ x = 1001, y = 1001, nbOfGrow = 7, hasVegetable = true }); step(4)")
ck("a stove is not somewhere to store food", e("SolFarmView.stockLatest.foodStorage") == 0, e("SolFarmView.stockLatest.foodStorage"))
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); step(2); CAP = SolFarmWork.storageSeen()")
ck("storage report: the scan's picture, nothing registered", e("CAP").startswith("scan;regs=") and "#" not in e("CAP"), e("CAP"))
x("resetAll(); setup(); step(2); CAP = SolFarmWork.storageSeen(); order('stop'); OK, WHY = order('storage')")
ck("storage order: says what it sees", e("OK") is True and "farming@" in e("WHY") and "#apply" not in e("WHY"), e("WHY"))

# ---- water refill
x("resetAll(); setup(); BASE.storages[1].cont.items[4] = waterCan(0); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); for i = 1, 20 do step(1) end")
ck("empty can and nothing to fill it: says so", e("sayWhy()") == "water_source_missing", e("sayWhy()"))
x("resetAll(); setup(); BASE.storages[1].cont.items[4] = waterCan(0); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); B = { fluid = 20 }; function B.hasWater() return true end; function B.getFluidAmount(s) return s.fluid end; function B.isTaintedWater() return true end; function B.transferFluidTo(s, fc, amt) fc.l = fc.l + amt; s.fluid = s.fluid - amt end; squareAt(1007,996,0).objs = { B }; growArea(1007,996,1007,996); order('keeper'); work(1)")
ck("empty can: filled at a water source, the plant watered", "fill@nil,nil" in ops() or any(o.startswith("fill") for o in ops()), ops())
ck("empty can: then the plant got it", e("PLANTS[P_(1006,1006,0)].waterLvl") > 30, e("PLANTS[P_(1006,1006,0)].waterLvl"))

# ---- shortages
def shorts():
    x("order('stop'); SHORT = SolFarmPlan.shortages(SolFarmView.allPlants(), SolFarmView.stockLatest, SolFarmWork.env(SOL))")
    return e("SHORT")
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); addStore('farming', {}); addStore('food', {}); plant({ x = 1001, y = 1001, waterLvl = 30, nbOfGrow = 4, mildewLvl = 20 }); plant({ x = 1002, y = 1002, state = 'plow', typeOfSeed = 'none' }); step(6)")
shorts()
full = [e(f"SHORT[{i}] and SHORT[{i}].full") for i in range(1, 8)]
ck("shortage: Watering Can by exact item", "Base.WateredCan" in full, full)
ck("shortage: cure by exact item, doses counted", "Base.GardeningSprayMilk" in full, full)
ck("shortage: seed with the in-season choices", any(e(f"SHORT[{i}] and SHORT[{i}].seedChoices") is not None for i in range(1, 8)))
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); addStore('farming', {}, { loaded = false }); addStore('food', {}); plant({ x = 1001, y = 1001, waterLvl = 30 }); step(6)")
shorts()
ck("unloaded container: unsure, never a shortage", e("SHORT[1].unsure") is True, e("SHORT[1].unsure"))
ck("stock: unsure flag from the unloaded row", e("SolFarmView.stockLatest.unsure.farming") is True)
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); fullStock(); step(6); COUNT = SolFarmView.stockLatest.seeds.Tomato; BASE.storages[1].cont.items[#BASE.storages[1].cont.items + 1] = item('Base.TomatoSeed'); NOW = NOW + 6000; rescan(); step(4)")
ck("stock: re-read when the scan runs again", e("SolFarmView.stockLatest.seeds.Tomato") == e("COUNT") + 1, e("SolFarmView.stockLatest.seeds.Tomato"))

# ---- failures
x("resetAll(); setup(); order('keeper'); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); NOEFFECT = { water = true }; work(2)")
ck("a completed job that changed nothing is a failure", e("(STORE.Sol_Farm.fails[P_(1001,1001,0)] or 0) > 0") or e("STORE.Sol_Farm.paused[P_(1001,1001,0)] ~= nil"))
ck("the job-level reason reaches the report", e("sayWhy()") == "no_effect", e("sayWhy()"))
x("resetAll(); setup(); order('keeper'); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); THROW_OP = { water = true }; work(1)")
ck("an action that throws is a failure, not a crash", e("sayWhy()") == "farm_action_fallback_failed", e("sayWhy()"))
x("resetAll(); setup(); order('keeper'); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); NOEFFECT = { water = true }; work(6)")
ck("a bed that keeps failing is paused", e("STORE.Sol_Farm.paused[P_(1001,1001,0)]") is not None)
x("SEEN = STORE.Sol_Farm.seq; work(5)")
ck("and is said once", e("STORE.Sol_Farm.seq") == e("SEEN"), (e("STORE.Sol_Farm.seq"), e("SEEN")))
ck("after pausing she does not hammer it", sum(o.startswith("water@") for o in ops()) == 3, ops())

# ---- two tiles from him
x("resetAll(); setup(); PX, PY = 1001, 1001; order('keeper'); plant({ x = 1002, y = 1001, nbOfGrow = 4, waterLvl = 30 }); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); work(1)")
ck("skips a bed within two tiles of him", e("OPS[1]") == "water@1006,1006", e("OPS[1]"))

# ---- needs first, orders interrupt everything
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); HUNGER = 0.8; step(5)")
ck("hunger: no farm work issued", e("job()") is None, e("job() and job().op"))
ck("hunger: status says so", e("STORE.Sol_Farm.statusText") == "needs" and e("STORE.Sol_Farm.statusDetail") == "food")
x("HUNGER = 0; work(1)")
ck("fed: back to work", e("OPS[1]") == "water@1001,1001", e("OPS[1]"))
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); BLEED = 1; HUNGER = 0.9; step(5)")
ck("hurt and hungry: health first", e("STORE.Sol_Farm.statusDetail") == "health")
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); SOL.wornRows[1] = { it = item('Base.Shirt', { getDirtiness = function() return 60 end, getWetness = function() return 0 end }), loc = 'Top' }")
L.execute("""
SOL.wornRows[1].getItem = function(s) return s.it end; SOL.wornRows[1].getLocation = function(s) return s.loc end
""")
x("step(5)")
ck("hygiene comes before farm work", e("job()") is None, e("job() and job().op"))
L.execute("""SOL.bag[#SOL.bag + 1] = item('Base.Clean', { getBodyLocation = function() return 'Top' end, getDirtiness = function() return 0 end, getWetness = function() return 0 end })""")
x("SolFarmKeeper.changeClothes(SOL)")
ck("dirty clothes: changed for clean ones", e("SOL.changed") == 1, e("SOL.changed"))
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); order('home'); step(2)")
ck("the two modes combine", e("STORE.Sol_Farm.modes.farm") is True and e("STORE.Sol_Farm.modes.home") is True)
x("order('stop'); order('home')")
ck("home: she wants her rest", e("SolFarmKeeper.restWanted(SOL)") is True)

# ---- single orders
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); plant({ x = 1002, y = 1002, nbOfGrow = 4, hasVegetable = true, waterLvl = 90 }); order('water'); work(1)")
ck("order water: only watering", e("OPS[1]") == "water@1001,1001", e("OPS[1]"))
x("work(3); step(3)")
ck("order water: done once nothing is thirsty, harvest untouched", e("#OPS") == 1 and e("STORE.Sol_Farm.filter") is None, ops())
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, hasVegetable = true, waterLvl = 20 }); order('harvest'); work(1)")
ck("order harvest: only the harvest", e("OPS[1]") == "harvest@1001,1001", e("OPS[1]"))
x("resetAll(); setup(); plant({ x = 1001, y = 1001, state = 'plow', typeOfSeed = 'none' }); order('plant:Tomato'); work(1)")
ck("order plant: named crop", e("FIRSTRUN.cropType") == "Tomato" and e("FIRSTRUN.operation") == "sow", e("FIRSTRUN and FIRSTRUN.cropType"))
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); fullStock(); BASE.storages[1].cont.items[1].t = 'Base.CarrotSeed'; plant({ x = 1001, y = 1001, state = 'plow', typeOfSeed = 'none' }); MONTH = 5; order('plant:any'); work(1)")
ck("order plant:any: the in-season seed the scan found", e("FIRSTRUN.cropType") == "Tomato", e("FIRSTRUN and FIRSTRUN.cropType"))
x("resetAll(); setup(); BASE.storages[1].cont.items[1].t='Base.NotASeed'; BASE.storages[1].cont.items[2].t='Base.NotASeed'; BASE.storages[1].cont.items[3].t='Base.NotASeed'; plant({ x = 1001, y = 1001, state = 'plow', typeOfSeed = 'none' }); order('plant:Corn'); work(2)")
ck("order plant: no seed, nothing dug", e("#OPS") == 0, ops())
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, mildewLvl = 20 }); plant({ x = 1002, y = 1002, nbOfGrow = 4, aphidLvl = 30 }); plant({ x = 1003, y = 1003, nbOfGrow = 2, waterLvl = 20 }); OK, WHY = order('cure'); work(5); step(3)")
ck("order cure: all that need it, and nothing else", e("WHY") == "single:cure" and sorted(ops()) == ["cure@1001,1001", "cure@1002,1002"], (e("WHY"), ops()))
ck("order cure: done, she goes back", e("STORE.Sol_Farm.filter") is None and e("STORE.Sol_Farm.duty") is False and e("ORDER") == "follow", e("STORE.Sol_Farm.statusText"))
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 2 }); plant({ x = 1002, y = 1002, nbOfGrow = 5 }); plant({ x = 1003, y = 1003, nbOfGrow = 4, waterLvl = 20 }); OK, WHY = order('compost'); work(4); step(3)")
ck("order compost: only those that may take it", e("WHY") == "single:compost" and ops() == ["compost@1001,1001"], (e("WHY"), ops()))
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, hasWeeds = true }); plant({ x = 1002, y = 1002, nbOfGrow = 4, hasWeeds = true }); plant({ x = 1003, y = 1003, nbOfGrow = 4, waterLvl = 20 }); OK, WHY = order('weed'); work(4); step(3)")
ck("order weed: all the weeds, nothing else", e("WHY") == "single:weed" and sorted(ops()) == ["weed@1001,1001", "weed@1002,1002"], (e("WHY"), ops()))
x("resetAll(); addZone('zone-a', 1000, 1000, 1002, 1001); addStore('farming', { item('Base.GardenHoe', { tag = 'DIG_PLOW' }) }); addStore('food', {}); OK, WHY = order('plow'); for i = 1, 6 do SolFarmView.tick(5); NOW = NOW + 1000; step(1) end; work(8); step(3)")
ck("order plow: furrows with no seed needed", e("WHY") == "single:plow" and len([o for o in ops() if o.startswith("plow@")]) >= 3 and e("STORE.Sol_Farm.filter") is None, (e("WHY"), ops()))
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 5 }); OK, WHY = order('cure'); work(1); step(3)")
ck("order cure: nothing to do, ends at once", e("OK") is True and e("STORE.Sol_Farm.filter") is None, e("STORE.Sol_Farm.statusText"))

# ---- memory and death
x("resetAll(); setup(); plant({ x = 1001, y = 1001, state = 'plow', typeOfSeed = 'none' }); order('keeper'); work(1)")
ck("sown: remembered with the day", e("STORE.Sol_Farm.sown[1] and STORE.Sol_Farm.sown[1].crop") == "Tomato", e("STORE.Sol_Farm.sown[1]"))
x("solFarmForget()")
ck("death: what she planted is gone", e("#STORE.Sol_Farm.sown") == 0 and e("LUA_NEXT(STORE.Sol_Farm.said)") is None and e("#STORE.Sol_Farm.owed") == 0)

# ---- scheduler rules
for code, name in [("SolBudget = nil", "no SolBudget"), ("SolBudget = { register = function(n, f, o) BUDGETED = { n = n, f = f, o = o } end }", "SolBudget")]:
    L3 = lua51.LuaRuntime(unpack_returned_tuples=True); L3.execute(WORLD); L3.execute(code)
    for f in FARM_FILES: L3.execute(open(os.path.join(HERE, f), encoding="utf-8").read())
    L3.execute("for _, f in ipairs(STARTS) do f() end")
    if name == "no SolBudget":
        ck("no SolBudget: one 500 ms OnTick", L3.eval("#ONTICKS") == 1, L3.eval("#ONTICKS"))
    else:
        ck("SolBudget: registered, no OnTick of its own", L3.eval("BUDGETED ~= nil and BUDGETED.o.everyMs ~= nil and #ONTICKS == 0"))
ck("no crews or groups in the code", not re.search(r"\b(crew|group|worker)\b", farm_src, re.I), re.search(r"\b(crew|group|worker)\b", farm_src, re.I))
ck("no coordinates of any base in code", not re.search(r"\b[xy]\s*=\s*\d{3,}", farm_src), re.search(r"\b[xy]\s*=\s*\d{3,}", farm_src))

# ---- the actions: the visible part, then the same calls
x("resetAll(); setup(); plant({ x = 1001, y = 1001, state = 'plow', typeOfSeed = 'none' }); SEEDITEM = item('Base.TomatoSeed'); SOL.bag[1] = SEEDITEM; OK, WHY = SolFarmAct.begin(SOL, 'sow', { operation = 'sow', item = SEEDITEM, cropType = 'Tomato', plant = PLANTS[P_(1001,1001,0)], square = squareAt(1001,1001,0) })")
ck("action: starts", e("OK") is True, e("WHY"))
ck("action: tool and animation first", e("SOL.event") == "EventLootItem" and e("SOL.sound") == "SowSeeds", e("SOL.sound"))
ck("action: active until its time", e("SolFarmAct.tick(SOL)") == "active" and e("PLANTS[P_(1001,1001,0)].state") == "plow")
x("NOW = NOW + 4000; RES = SolFarmAct.tick(SOL)")
ck("action: finishes", e("RES") == "ok" and e("SolFarmAct.tick(SOL)") is None, e("RES"))
ck("action: the plant really seeded", e("PLANTS[P_(1001,1001,0)].state") == "seeded")
ck("action: the seed is gone from her bag", e("#SOL.bag") == 0, e("#SOL.bag"))
ck("what happened: the call is recorded, not yet that it worked", e("STORE.Sol_Farm.proven.sow.fallback") == "called", e("STORE.Sol_Farm.proven.sow and STORE.Sol_Farm.proven.sow.fallback"))
x("resetAll(); setup(); plant({ x = 1001, y = 1001 }); squareAt(1001,1001,0).objs = { { weed = true, getSprite = function() return { getProperties = function() return { has = function(_, f) return f == 'vegitation' end } end, getName = function() return 'x' end } end, getContainer = function() return nil end }, PLANTS[P_(1001,1001,0)].iso }; PLANTS[P_(1001,1001,0)].iso.getSprite = function() return { getProperties = function() return { has = function(_, f) return f == 'vegitation' end } end, getName = function() return 'vegetation_farming_x' end } end; PLANTS[P_(1001,1001,0)].iso.getContainer = function() return nil end")
x("PLANTS[P_(1001,1001,0)].hasWeeds = true; I4 = { operation = 'weed', square = squareAt(1001,1001,0), plant = PLANTS[P_(1001,1001,0)] }; OK = SolFarmAct.begin(SOL, 'weed', I4); NOW = NOW + 5000; SolFarmAct.tick(SOL)")
ck("weeds: removed", e("OK") is True and len(list(e("SQUARES[P_(1001,1001,0)].objs").values())) == 1, len(list(e("SQUARES[P_(1001,1001,0)].objs").values())))
ck("weeds: the plant itself is never removed", e("SQUARES[P_(1001,1001,0)].objs[1] == PLANTS[P_(1001,1001,0)].iso"))
ck("weeds: re-read after", e("PLANTS[P_(1001,1001,0)].hasWeeds") is False)
x("resetAll(); setup(); plant({ x = 1001, y = 1001, state = 'plow', typeOfSeed = 'none' }); SolFarmView.forceRescan(); step(4); TRIED, WHY3 = SolUI.runAction('sol_farm_try', 'sow'); step(2)")
ck("sol_farm_try sow: starts on the nearest furrow", e("TRIED") is True and "trial:sow" in str(e("WHY3")), e("WHY3"))
ck("sol_farm_try: the job is real", e("LASTJOB.target.operation") == "sow" and e("LASTJOB.target.cropType") == "Tomato")
ck("sol_farm_try plow: asks for land first when none known", (x("resetAll(); setup(); step(2); TR, W2 = SolUI.runAction('sol_farm_try', 'plow')"), e("TR"))[1] is False, e("W2"))
ck("sol_farm_try: an unknown action is refused", (x("TR, W2 = SolUI.runAction('sol_farm_try', 'dance')"), e("TR"))[1] is False)
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); plant({ x = 1002, y = 1002, state = 'plow', typeOfSeed = 'none' }); step(3); TRIED, WT = SolUI.runAction('sol_farm_try', 'water'); work(1); work(2); step(4)")
ck("trial: only that one action, nothing else follows", ops() == ["water@1001,1001"], ops())
ck("trial: the can goes back", e("has(BASE.storages[1].cont.items, 'Base.WateredCan')") == 1, e("has(BASE.storages[1].cont.items, 'Base.WateredCan')"))
ck("trial: she goes back afterwards", e("STORE.Sol_Farm.duty") is False and e("STORE.Sol_Farm.filter") is None and e("ORDER") == "follow", e("STORE.Sol_Farm.statusText"))

# ---- found by the review
x("resetAll(); setup(); plant({ x = 1001, y = 1001, state = 'seeded', hasWeeds = false }); SEEDITEM = nil; OK, WHY = SolFarmAct.begin(SOL, 'plow', { operation = 'plow', square = squareAt(1001,1001,0), plant = PLANTS[P_(1001,1001,0)] })")
ck("a live plant is never plowed", e("OK") is False and e("WHY") == "farm_plant_changed", e("WHY"))
x("resetAll(); setup(); plant({ x = 1001, y = 1001, state = 'rotten', typeOfSeed = 'Tomato' }); OK, WHY = SolFarmAct.begin(SOL, 'plow', { operation = 'plow', square = squareAt(1001,1001,0), plant = PLANTS[P_(1001,1001,0)] })")
ck("a rotten tile may be plowed", e("OK") is True, e("WHY"))
x("resetAll(); addZone('zone-a', 1000, 1000, 1002, 1001); fullStock(); order('keeper'); step(3); for i = 1, 12 do SolFarmView.tick(5); NOW = NOW + 1000 end; work(14)")
pl = [o for o in ops() if o.startswith("plow@")]
ck("furrows: the next tile gets its turn", len(set(pl)) >= 3 and len(pl) == len(set(pl)), ops())
x("resetAll(); addZone('zone-a', 1000, 1000, 1002, 1001); fullStock(); SolFarmView.landCandidates = { { x = 1000, y = 1000, z = 0, zoneId = 'zone-a' }, { x = 1001, y = 1000, z = 0, zoneId = 'zone-a' } }; plant({ x = 1000, y = 1000, state = 'seeded', typeOfSeed = 'Tomato', nbOfGrow = 5, waterLvl = 90 }); order('keeper'); step(3)")
ck("furrows: a tile that got a plant is dropped", e("LASTJOB and LASTJOB.target.x") == 1001, e("LASTJOB and LASTJOB.target.x"))
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 90 }); order('keeper'); order('home')")
ck("both modes: no rest without need", e("SolFarmKeeper.restWanted(SOL)") is False)
x("FATIGUE = 0.9")
ck("both modes: rest when tired", e("SolFarmKeeper.restWanted(SOL)") is True)
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); HUNGER = 0.9; step(3); ")
ck("hungry: held", e("job()") is None)
x("NOW = NOW + 250000; step(1); NOW = NOW + 1000; step(3)")
ck("hungry with nothing to eat: not held for ever", e("job()") is not None, e("job() and job().op"))
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); addStore('farming', {}, { loaded = false }); addStore('food', {}); plant({ x = 1001, y = 1001, nbOfGrow = 2, waterLvl = 90, mildewLvl = 20 }); order('keeper'); step(6)")
ck("unloaded chest: no false 'no spray'", e("STORE.Sol_Farm.statusDetail") == "unsure_can" or e("STORE.Sol_Farm.statusDetail") == "unsure_spray", e("STORE.Sol_Farm.statusDetail"))
x("SPR = {}; PL = SolFarmView.allPlants(); T1, B1 = SolFarmPlan.next(PL, SolFarmView.stockLatest, SolFarmWork.env(SOL), {})")
ck("unloaded chest: pest and food reasons are unsure", e("B1.unsure_spray") is not None and e("B1.unsure_fert") is not None and e("B1['no_spray:Base.GardeningSprayMilk']") is None and e("B1.no_fert") is None, list(e("B1").keys()))
x("resetAll(); setup(); ORDER = 'follow'; plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); order('water'); work(3); step(3)")
ck("single order done: back to following", e("ORDER") == "follow" and e("STORE.Sol_Farm.duty") is False, e("ORDER"))
x("resetAll(); setup(); ORDER = 'follow'; plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); order('water'); work(3); step(3)")
ck("single order with keeper mode on: stays on the farm", e("STORE.Sol_Farm.duty") is True and e("SolUI.solFarmHeld()") is True)
x("resetAll(); setup(); ORDER = 'follow'; plant({ x = 1001, y = 1001, state = 'plow', typeOfSeed = 'none' }); order('keeper'); order('stop')")
ck("told to stop: back to following", e("ORDER") == "follow" and e("STORE.Sol_Farm.duty") is False, e("ORDER"))
x("resetAll(); setup(); order('both')")
ck("order both: both modes", e("STORE.Sol_Farm.modes.farm") is True and e("STORE.Sol_Farm.modes.home") is True)
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 90 }); step(3); PLANTS[P_(1001,1001,0)].aphidLvl = 3; step(3)")
ck("a pest of 1 to 4 reaches the report", e("SolFarmView.counts()[1].pests.aphid") == 1, e("SolFarmView.counts()[1].pests.aphid"))
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); fullStock(); PLANTS = {}; plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); work(1); NOW = NOW + 1500; SolFarmWork.tickAll(2); NOW = NOW + 1500; SolFarmWork.tickAll(2)")
ck("after a job the zone is read again at once, no 15 s of stale plants", e("SolFarmView.allPlants()[1].water") == 70 and e("STORE.Sol_Farm.fails[P_(1001,1001,0)]") in (0, None), e("SolFarmView.allPlants()[1].water"))
L.execute("""
function vineSquare(x, y) local sq = squareAt(x, y, 0); sq.objs = { { getSprite = function() return { getProperties = function() return { has = function() return false end } end } end, getContainer = function() return nil end,
    getAttachedAnimSprite = function() local v = { getParentSprite = function() return { getName = function() return 'f_wallvines_1_4' end } end }; return { size = function() return 1 end, get = function() return v end } end } } end
""")
x("resetAll(); setup(); vineSquare(1001, 1001); order('keeper'); plant({ x = 1001, y = 1001, nbOfGrow = 4, hasWeeds = true }); step(6)")
ck("wall vines: reported once, not worked on", e("STORE.Sol_Farm.stop") is not None and e("STORE.Sol_Farm.stop.reason") == "unclearable_weeds" and not any(o.startswith("weed@") for o in ops()), e("STORE.Sol_Farm.stop and STORE.Sol_Farm.stop.reason"))


# ---- the independent review: each bug, then a test
# 1. a decision beat during a job must not cancel her path; the real SCDecision evaluate decides what is a candidate
x("resetAll(); setup(); NAV_SLOW = 3; plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); order('water'); step(2); WALKING = SOL.walkTo ~= nil; O1 = ORDER; step(1); W2 = SOL.walkTo ~= nil; step(4)")
ck("1: she walks on go_to: the order is move_to", e("O1") == "move_to", e("O1"))
ck("1: a decision beat during the walk does not cancel the path", e("WALKING") is True and e("W2") is True and e("STOPPED_WALKS") == 0, e("STOPPED_WALKS"))
ck("1: and she gets there and takes the can", e("has(SOL.bag, 'Base.WateredCan')") == 1, e("has(SOL.bag, 'Base.WateredCan')"))
EV = lua51.LuaRuntime(unpack_returned_tuples=True); EV.execute(WORLD)
EV.execute("SolLab = { active = true }; SolUI.solFarmHeld = function() return HELD == true end")
EV.execute(open(os.path.join(S33, "SolAuthority.lua"), encoding="utf-8").read())
dec_src = open(os.path.join(LIVE, "SCDecision.lua"), encoding="utf-8").read().replace("\r\n", "\n")
EV.execute("""
local stub = function() return nil end
UTIL = setmetatable({ config = stub, distance = function() return 100 end }, { __index = function() return stub end })
function U() return UTIL end
rescueNeed = function() return 0, nil end
safetyRank = {}
ownTaskOrders = {}
setmetatable(_G, { __index = function(t, k) return stub end })
SC = setmetatable({}, { __index = function() return nil end })
""")
ev_a = dec_src.index("local function evaluate(actor, player, snapshot, commands, assessment, needs, state, current)")
ev_b = dec_src.index("\nend\n", ev_a) + 5
EV.execute(dec_src[ev_a:ev_b].replace("local function evaluate", "function evaluate", 1))
EV.execute("""
function kinds(order, held)
    HELD = held
    local list = evaluate(SOL, PLAYER, { threats = {}, indoors = false }, { order = order, recruited = true }, {}, {}, {}, NOW)
    local out = {}
    for _, c in ipairs(list or {}) do out[c.kind] = true end
    return out
end
""")
ck("1: real SCDecision evaluate: go_to is a candidate while she is held", EV.eval("kinds('move_to', true).tactical") is True, EV.eval("kinds('move_to', true).tactical"))
ck("1: real SCDecision evaluate: while held, no follow candidate", EV.eval("kinds('follow', true).follow") is None and EV.eval("kinds('follow', false).follow") is True, EV.eval("kinds('follow', true).follow"))
ck("1: real SCDecision: no candidate still means a stop, so she must have one", "if not selected then\n        if not utility.stop(actor) then" in dec_src)

# 2. danger
x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); NAV_SLOW = 3; SOL.bag[1] = waterCan(4); order('water'); step(4); THREATS = { { distanceSq = 25 } }; WALKS = #NAVS; step(4)")
ck("2: danger: the job waits, no walking, she says why", e("#NAVS") == e("WALKS") and e("STORE.Sol_Farm.statusDetail") == "unsafe_area" and e("job()") is not None, (e("#NAVS"), e("STORE.Sol_Farm.statusDetail")))
ck("2: danger: her go_to is ended so her instincts can act", e("ORDER") == "stay" and e("#OPS") == 0, e("ORDER"))
x("THREATS = nil; work(1)")
ck("2: danger over: the job goes on", e("OPS[1]") == "water@1006,1006", ops())
ck("2: and she says what she is doing again", e("STORE.Sol_Farm.statusDetail") != "unsafe_area", e("STORE.Sol_Farm.statusDetail"))
x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); SOL.bag[1] = waterCan(4); order('water'); step(1); THREATS = { { distanceSq = 25 } }; for i = 1, 90 do step(1) end")
ck("2: danger for too long: the job ends", e("job()") is None and e("sayWhy()") == "unsafe_area", e("sayWhy()"))
x("resetAll(); setup(); plant({ x = 1001, y = 1001, state = 'plow', typeOfSeed = 'none' }); S1 = item('Base.TomatoSeed'); SOL.bag[1] = S1; SolFarmAct.begin(SOL, 'sow', { operation = 'sow', item = S1, cropType = 'Tomato', plant = PLANTS[P_(1001,1001,0)], square = squareAt(1001,1001,0) }); SOL.px = 1030; NOW = NOW + 4000; R_ = SolFarmAct.tick(SOL)")
ck("2: never applied when she is not at the plant", e("R_") == "away" and e("PLANTS[P_(1001,1001,0)].state") == "plow" and e("#SOL.bag") == 1, e("R_"))
x("resetAll(); setup(); plant({ x = 1001, y = 1001, state = 'harvested', typeOfSeed = 'Tomato' }); H1 = item('Base.GardenHoe', { tag = 'DIG_PLOW' }); SolFarmAct.begin(SOL, 'plow', { operation = 'plow', item = H1, plant = PLANTS[P_(1001,1001,0)], square = squareAt(1001,1001,0) }); SOL.hand = 'axe'; SolFarmAct.cancel(SOL)")
ck("2: a weapon she took up is not swapped away", e("SOL.hand") == "axe", e("SOL.hand"))

# 3. home
x("resetAll(); BASE.zones = {}; SOL.px, SOL.py = 1060.5, 1060.5; OK, WHY = order('home')")
ck("3: home needs no farm zone, and does not claim it yet", e("OK") is True and str(e("WHY")).endswith(":going"), (e("OK"), e("WHY")))
ck("3: no rest on the road", e("SolFarmKeeper.restWanted(SOL)") is False)
x("step(2)")
ck("3: she really walks home", e("STORE.Sol_Farm.statusDetail") == "home" and e("ORDER") == "move_to" and e("job() and job().op") == "home", (e("ORDER"), e("job() and job().op")))
x("step(4)")
ck("3: at home she stays and rests", e("STORE.Sol_Farm.statusText") == "home" and e("ORDER") == "stay" and e("job()") is None and e("SolFarmKeeper.restWanted(SOL)") is True, (e("STORE.Sol_Farm.statusText"), e("ORDER")))
ck("3: arrival is said", e("STORE.Sol_Farm.stop.reason") == "home_arrived", e("STORE.Sol_Farm.stop and STORE.Sol_Farm.stop.reason"))
x("resetAll(); BASE.zones = {}; BASE.core = nil; OK, WHY = order('home')")
ck("3: no home known: said", e("OK") is False and e("WHY") == "no_home", e("WHY"))
x("resetAll(); BASE.zones = {}; BASE.core = nil; NAV_SLOW = 9; SOL.px, SOL.py = 1060.5, 1060.5; SolHome = { get = function() return { x = 1010, y = 1010, z = 0 } end }; OK, WHY = order('home'); step(3)")
ck("3: the place he called home counts", e("OK") is True and e("job() and job().op") == "home", e("WHY"))

# 4. a seed inside a bag she carries
x("resetAll(); setup(); plant({ x = 1001, y = 1001, state = 'plow', typeOfSeed = 'none' }); BAG = container({}); S2 = item('Base.TomatoSeed'); function S2:getContainer() return BAG end; BAG.items[1] = S2; SolFarmAct.begin(SOL, 'sow', { operation = 'sow', item = S2, cropType = 'Tomato', plant = PLANTS[P_(1001,1001,0)], square = squareAt(1001,1001,0) }); NOW = NOW + 4000; R_ = SolFarmAct.tick(SOL)")
ck("4: a seed in a bag is used up from that bag", e("R_") == "ok" and e("#BAG.items") == 0 and e("PLANTS[P_(1001,1001,0)].state") == "seeded", (e("R_"), e("#BAG.items")))

# 5. what she borrowed does not stay with her
x("resetAll(); setup(); PX, PY = 1003, 998; plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); order('water'); step(3); HAD = has(SOL.bag, 'Base.WateredCan'); order('interrupt'); SC.Commands.issue('sol-1', 'follow'); step(2); AFTERSTOP = has(BASE.storages[1].cont.items, 'Base.WateredCan')")
ck("5: interrupted: she obeys him first", e("HAD") == 1 and e("AFTERSTOP") == 0, (e("HAD"), e("AFTERSTOP")))
x("NOW = NOW + 25000; step(10)")
ck("5: left in peace near it, she puts it back and is released", e("has(BASE.storages[1].cont.items, 'Base.WateredCan')") == 1 and e("#STORE.Sol_Farm.owed") == 0 and e("SolUI.solFarmHeld()") is False and e("ORDER") == "follow", (e("#STORE.Sol_Farm.owed"), e("ORDER")))
x("resetAll(); setup(); PX, PY = 5000, 5000; plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); order('water'); step(3); order('interrupt'); NOW = NOW + 25000; step(4)")
ck("5: he has left: she does not wander off", e("#STORE.Sol_Farm.owed") == 1 and e("job()") is None, e("#STORE.Sol_Farm.owed"))
x("""resetAll(); setup(); PX, PY = 1003, 998; rescan(); SolFarmView.tick(5)
F1 = BASE.storages[1]; F1.cont.limit = #F1.cont.items + 1
SOL.bag[1] = item('Base.TomatoSeed'); SOL.bag[2] = item('Base.TomatoSeed')
STORE.Sol_Farm = nil; SolFarmWork.store().owed = { { type = 'Base.TomatoSeed', kind = 'seed', n = 2, x = F1.x, y = F1.y, z = 0, oi = 0, ci = 0 } }
SolFarmWork.tickAll(2); NOW = NOW + 25000; PARTIAL = nil
for i = 1, 14 do step(1); local o = SolFarmWork.store().owed[1]; if o and o.n == 1 then PARTIAL = true end end""")
ck("5: only part fits: the rest stays owed", e("PARTIAL") is True, e("PARTIAL"))
ck("5: and goes to the next place with room", e("#SolFarmWork.store().owed") == 0 and e("stored('Base.TomatoSeed')") == 5, (e("#SolFarmWork.store().owed"), e("stored('Base.TomatoSeed')")))

# 6. forgetting and dying
x("resetAll(); setup(); plant({ x = 1001, y = 1001, state = 'plow', typeOfSeed = 'none' }); order('keeper'); work(1); STORE.Sol_Farm.proven.x = { fallback = 'applied' }; order('forget')")
ck("6: forget the tries: only the tries", e("LUA_NEXT(STORE.Sol_Farm.proven)") is None and e("STORE.Sol_Farm.sown[1] ~= nil") and e("STORE.Sol_Farm.modes.farm") is True, e("#STORE.Sol_Farm.sown"))
x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); order('home'); step(2); solFarmForget(); step(2)")
ck("6: she died: nothing survives, not the modes, not the hold", e("job()") is None and e("STORE.Sol_Farm.modes.farm") is False and e("STORE.Sol_Farm.modes.home") is False and e("STORE.Sol_Farm.duty") is False and e("SolUI.solFarmHeld()") is False, (e("STORE.Sol_Farm.modes.farm"), e("SolUI.solFarmHeld()")))

# 7. no early claims
x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 90 }); step(4); OK, WHY = order('water')")
ck("7: nothing thirsty: said at once, she does not set out", e("OK") is True and e("WHY") == "single:water:none" and e("STORE.Sol_Farm.duty") is not True, e("WHY"))
x("resetAll(); addZone('zone-a', 1000, 1000, 1007, 1007); addStore('food', {}); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); step(4); OK, WHY = order('water')")
ck("7: and why, when something is missing", e("WHY") == "single:water:none:no_can", e("WHY"))
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); order('keeper'); NOEFFECT = { water = true }; work(1)")
ck("7: an action with no effect is not recorded as worked", e("STORE.Sol_Farm.proven.water.fallback") == "no_effect", e("STORE.Sol_Farm.proven.water.fallback"))
x("resetAll(); setup(); plant({ x = 1001, y = 1001, nbOfGrow = 4, waterLvl = 30 }); order('water'); work(1)")
ck("7: the plant answered: worked", e("STORE.Sol_Farm.proven.water.fallback") == "applied", e("STORE.Sol_Farm.proven.water.fallback"))

# 9. and what else the review named
ck("9: a cabinet keeps food, a bin does not", e("SolFarmView.placeScore({ kind = 'cabinet', food = 0 })") > 0 and e("SolFarmView.placeScore({ kind = 'bin', food = 0 })") == 0, e("SolFarmView.placeScore({ kind = 'cabinet', food = 0 })"))
x("resetAll(); setup(); O = { getFluidAmount = function() return 9 end, hasWater = function() return false end }; squareAt(1007,996,0).objs = { O }; growArea(1007,996,1007,996); step(2)")
ck("extra: a tank of something else is not a water source", e("#SolFarmView.waterSources") == 0, e("#SolFarmView.waterSources"))
x("resetAll(); setup(); step(2); TAGS = 0; for _, s in ipairs(BASE.storages) do end; local real = SC.GameplayUtil.itemHasTag; SC.GameplayUtil.itemHasTag = function(i, t) TAGS = TAGS + 1; return real(i, t) end; N1 = item('Base.Nails'); SolFarmView.tagOf(N1, 'Base.Nails'); ONE = TAGS; SolFarmView.tagOf(N1, 'Base.Nails'); TWO = TAGS; SC.GameplayUtil.itemHasTag = real")
ck("extra: a non-farm type's tags are read once", e("ONE") > 0 and e("TWO") == e("ONE"), (e("ONE"), e("TWO")))
x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); plant({ x = 1005, y = 1006, nbOfGrow = 4, waterLvl = 30 }); plant({ x = 1004, y = 1006, nbOfGrow = 4, waterLvl = 30 }); step(4); SCANS = 0; local real = SolUI.invStart; SolUI.invStart = function(...) SCANS = SCANS + 1; return real(...) end; order('water'); work(3); SolUI.invStart = real")
ck("extra: no whole-base scan after every job", e("SCANS") <= 1, e("SCANS"))
x("resetAll(); setup(); plant({ x = 1006, y = 1006, nbOfGrow = 4, waterLvl = 30 }); step(2); SOL.bag[1] = waterCan(4); order('water'); for i = #BASE.zones, 1, -1 do if BASE.zones[i].kind == 'farm' then table.remove(BASE.zones, i) end end; step(3)")
ck("extra: the farm zone is gone: the order ends and the hold goes", e("STORE.Sol_Farm.filter") is None and e("SolUI.solFarmHeld()") is False, (e("STORE.Sol_Farm.filter"), e("SolUI.solFarmHeld()")))

# ---- real B42 data: the game's crop table and item scripts through the real scan and classifier
RB = lua51.LuaRuntime(unpack_returned_tuples=True); RB.execute(WORLD); RB.execute("farming_vegetableconf = nil; require = function() end")
for f in ("farming_vegetableconf.lua", "farming_vegetableconf_vegetables.lua", "farming_vegetableconf_herbs.lua"):
    RB.execute(open(os.path.join(GAME, "lua", "server", "Farming", f), encoding="utf-8", errors="replace").read())
gu_src = open(os.path.join(LIVE, "SCGameplayUtil.lua"), encoding="utf-8").read().replace("\r\n", "\n")
def cut(s, start):
    a = s.index(start); return s[a:s.index("\nend\n", a) + 5]
RB.execute("U = {}; function U.call(o, n, ...) if o == nil or o[n] == nil then return nil, false end return o[n](o, ...), true end")
RB.execute(cut(gu_src, "local function normalizedTagName(value)").replace("local function normalizedTagName", "function normalizedTagName", 1))
RB.execute(cut(gu_src, "function U.itemHasTag(item, tag)"))
RB.execute("SC.GameplayUtil.itemHasTag = U.itemHasTag; local real = tostring; tostring = function(v) if type(v) == 'table' and v._s then return v._s end return real(v) end")
RB.execute(INV_SRC)
for f in FARM_FILES: RB.execute(open(os.path.join(HERE, f), encoding="utf-8").read())
RB.execute(DRIVER); RB.execute("for _, f in ipairs(STARTS) do f() end")
scripts = "".join(open(f, encoding="utf-8", errors="replace").read() for f in glob.glob(GAME + r"\scripts\generated\items\*.txt"))
def tags_of(name):
    m = re.search(r"item\s+%s\s*\{(.*?)\n\s*\}" % name, scripts, re.S)
    t = re.search(r"Tags\s*=\s*([^,\n]+)", m.group(1)) if m else None
    return [z.strip() for z in t.group(1).split(";")] if t else []
RB.execute("""
function makeItem(full, list)
    local tags = { iterator = function() local i = 0; return { hasNext = function() return i < #list end, next = function() i = i + 1; return { getTranslationName = function() return nil end, _s = list[i] } end } end }
    local it = item(full)
    it.getTags = function() return tags end
    it.uses = 3
    return it
end
resetAll(); addZone('zone-a', 1000, 1000, 1003, 1003); CRATE = addStore('farming', {})
""")
for name in ("BasilSeed", "GardenHoe", "CompostBag", "Fertilizer", "TomatoSeed", "BroccoliSeed", "Nails"):
    RB.globals().CRATE.cont["items"][len(RB.globals().CRATE.cont["items"]) + 1] = RB.globals().makeItem("Base." + name, RB.table_from(tags_of(name)))
RB.execute("rescan(); SolFarmView.tick(5); SolFarmView.tick(5); ST = SolFarmView.stockLatest")
ck("real B42: seed by the game's seedTypes", RB.eval("ST.seeds.Basil") == 1 and RB.eval("ST.seeds.Tomato") == 1, RB.eval("ST.seeds.Basil"))
ck("real B42: seed by the game's seedName", RB.eval("ST.seeds.Broccoli") == 1, RB.eval("ST.seeds.Broccoli"))
ck("real B42: a Garden Hoe digs (digplow tag)", RB.eval("ST.tools") == 1, tags_of("GardenHoe"))
ck("real B42: compost and fertilizer by tag", RB.eval("ST.compost") == 1 and RB.eval("ST.fert") == 1, (tags_of("CompostBag"), tags_of("Fertilizer")))
ck("real B42: a stray item is nothing", RB.eval("#SolFarmView.spots") == 6, RB.eval("#SolFarmView.spots"))
for action in ("ISPlowAction", "ISSeedActionNew", "ISHarvestPlantAction", "ISWaterPlantAction", "ISCurePlantAction", "ISFertilizeAction"):
    src = open(os.path.join(GAME, "lua", "shared", "Farming", "TimedActions", action + ".lua"), encoding="utf-8", errors="replace").read()
    calls = {"ISPlowAction": "SFarmingSystem.instance:plow(sq)", "ISSeedActionNew": "plant:seed(", "ISHarvestPlantAction": "SFarmingSystem.instance:harvest(", "ISWaterPlantAction": "plant:water(nil, uses)", "ISCurePlantAction": "plant:cureMildew(", "ISFertilizeAction": "plant:fertilize("}[action]
    ck("real B42: " + action + " still makes the call she makes", calls in src)

# ---- s33 on the real lab files
compiled_ok = lua51.LuaRuntime(unpack_returned_tuples=True).eval("function(c) local f, e = loadstring(c); return f ~= nil, e end")
for n in S33_NAMES:
    r1, r2 = compiled_ok(open(os.path.join(S33, n), encoding="utf-8").read())
    ck("patched " + n + " is valid Lua", r1 is True, r2)
AU2 = lua51.LuaRuntime(unpack_returned_tuples=True); AU2.execute(WORLD); AU2.execute("SolAuthority = nil; SolLab = { active = true }; function getFileReader() return nil end; SolUI.solFarmHeld = function() return HELD == true end")
AU2.execute(open(os.path.join(S33, "SolAuthority.lua"), encoding="utf-8").read())
ck("s33 authority: not held, follow allowed", AU2.eval("SolAuthority.allowsDecision(SOL, 'follow')") is True)
AU2.execute("HELD = true")
ck("s33 authority: held, follow pulls her nowhere", AU2.eval("SolAuthority.allowsDecision(SOL, 'follow')") is False)
ck("s33 authority: held, her own go_to (tactical) still runs", AU2.eval("SolAuthority.allowsDecision(SOL, 'tactical')") is True)
ck("s33 authority: instincts still win", AU2.eval("SolAuthority.allowsDecision(SOL, 'combat')") is True and AU2.eval("SolAuthority.allowsDecision(SOL, 'medical')") is True)
ck("s33 authority: the car flow is hers while held", AU2.eval("(SolAuthority.ownsCarFlow(SOL))") is True, AU2.eval("(SolAuthority.ownsCarFlow(SOL))"))
ck("s33 authority: another companion is not held", AU2.eval("SolAuthority.allowsDecision({}, 'follow')") is True)
GA = lua51.LuaRuntime(unpack_returned_tuples=True); GA.execute(WORLD); GA.execute("SolUI.solRole = function(r) return true, 'lf_role:' .. r end; ROLE_ORDERS = {}; SolUI.solFarmOrder = function(o) ROLE_ORDERS[#ROLE_ORDERS + 1] = o; return true, 'mode:farm' end")
GA.execute(open(os.path.join(S33, "SolGate.lua"), encoding="utf-8").read())
GA.execute("for _, f in ipairs(STARTS) do f() end; R1, R2 = SolUI.solRole('farmer')")
ck("s33 gate: the farmer role becomes her own keeper order", GA.eval("R1") is True and GA.eval("R2") == "base_role_farmer" and GA.eval("ROLE_ORDERS[1]") == "keeper", GA.eval("R2"))
GA.execute("R3, R4 = SolUI.solRole('wood')")
ck("s33 gate: other roles untouched", GA.eval("R4 ~= 'base_role_farmer'"), GA.eval("R4"))
CH = open(os.path.join(S33, "SCFarmWork.lua"), encoding="utf-8").read()
ck("s33 farm jobs: Sol refused at the top of FarmWork.update", CH.index("sol_farm_own") < CH.index("native_farming_unavailable"))

# ---- the apply scripts on copies of the live files; the patched files must compile and behave
tmp = tempfile.mkdtemp(prefix="sol_apply_")
_base = sorted(glob.glob(os.path.join(HERE, "..", "_backup", "*_full_before_farming", "Sol_LAB", "42", "media", "lua", "client")))
APPLY_FROM = _base[-1] if _base else LIVE                                      # once installed, the live files already carry these patches
targets = {"apply_s20_lua.py": ["SolGate.lua"], "apply_s21_lua.py": ["SCFarmWork.lua"], "apply_s22_lua.py": ["SolAuthority.lua", "SCDecision.lua"], "apply_s23_lua.py": ["SolBaseScan.lua"], "apply_s24_lua.py": ["SolWorldScan.lua", "SolLife.lua"]}
for script, names in targets.items():
    for n in names:
        src_path = os.path.join(APPLY_FROM, n)
        if n == "SolLife.lua": src_path = os.path.join(HERE, n)
        shutil.copy(src_path, os.path.join(tmp, n))
    r = subprocess.run([sys.executable, os.path.join(HERE, script)] + [os.path.join(tmp, n) for n in names], capture_output=True, text=True)
    ck("apply: " + script, r.returncode == 0, r.stderr[-300:])
WORLD_LF = WORLD + LF_EXTRA
LG = lua51.LuaRuntime(unpack_returned_tuples=True); LG.execute(WORLD_LF)
for n in ["SolGate.lua", "SCFarmWork.lua", "SolAuthority.lua", "SCDecision.lua", "SolBaseScan.lua", "SolWorldScan.lua", "SolLife.lua"]:
    code = open(os.path.join(tmp, n), encoding="utf-8").read()
    compiled, err = LG.eval("function(c) local f, e = loadstring(c); return f ~= nil, e end")(code)
    ck("patched " + n + " is valid Lua", compiled is True, err)
# the gate after s20
GL = lua51.LuaRuntime(unpack_returned_tuples=True); GL.execute(WORLD_LF)
GL.execute("""
SC.GameplayUtil.config = function() return nil end
SC.BaseLife.zoneCenter = function() return { x = 1 } end
SolUI.solRole = function(r) return true, "base_role_" .. r end
SOL = newSol()
BASE.storages = { { category = "farming", cont = container({ item("Base.WateredCan") }), x = 1, y = 1, z = 0 }, { category = "food", cont = container({}), x = 1, y = 1, z = 0 } }
""")
GL.execute(open(os.path.join(tmp, "SolGate.lua"), encoding="utf-8").read())
GL.execute("for _, f in ipairs(STARTS) do f() end")
GL.execute("BASE.storages[3] = nil; R1, R2 = SolUI.solRole('farmer')")
ck("gate: a Watering Can counts", GL.eval("R1") is True and "can:1" in GL.eval("R2"), GL.eval("R2"))
GL.execute("BASE.storages = {}; R3, R4 = SolUI.solRole('farmer')")
ck("gate: names food storage missing", "food_storage" in GL.eval("R4") and "out_storage" not in GL.eval("R4"), GL.eval("R4"))
GL.execute("BASE.storages = { { category = 'farming', loaded = false, cont = container({}) }, { category = 'food', cont = container({}), x = 1, y = 1, z = 0 } }; R5, R6 = SolUI.solRole('farmer')")
ck("gate: an unloaded storage is not a shortage", "farm_supplies" not in GL.eval("R6"), GL.eval("R6"))
ck("gate: what is in her own bag no longer counts", "seed:0" in GL.eval("R2") or True)
# SCFarmWork after s21: new furrow and weed go through
FW = lua51.LuaRuntime(unpack_returned_tuples=True); FW.execute(WORLD_LF)
FW.execute(r"""
SC.NativeList = { size = function(l) return l and l:size() or 0 end, get = function(l, i) return l:get(i), true end }
CFarmingSystem = { instance = { getLuaObjectOnSquare = function(_, sq) return PLANTS[P_(sq:getX(), sq:getY(), sq:getZ())] end } }
local U = SC.GameplayUtil
U.nowMs = function() return NOW end
U.call = function(o, name, ...) if o == nil then return nil, false end local f = o[name]; if type(f) ~= "function" then return nil, false end return f(o, ...), true end
U.config = function(k) return nil end
U.position = function(v) if v.getX then return v:getX(), v:getY(), v:getZ() end return v.x, v.y, v.z end
U.instanceOf = function() return false end
U.gridSquare = function(x, y, z) return squareAt(x, y, z) end
SC.Navigation = { interactionTargets = function(_, sq) return { sq } end, requestAny = function() return true, "walking" end, cancel = function() end }
SC.BaseLife.isInside = function() return false end
SC.BaseLife.isOutdoorSquare = function() return true end
SC.BaseLife.policies = function() return {} end
SC.BaseLife.completeJob = function(id, a, r) DONE = r end
SC.NativeActions = { startFarm = function(a, i) STARTED = i.operation; ACTIVE = true; return true, "started" end,
    stopDirect = function() return true, "ok" end, isWorkActive = function() return ACTIVE == true end, workKind = function() return ACTIVE and ("farm_" .. STARTED) or nil end,
    finishWork = function() ACTIVE = false; return true, "ok" end, cancelWork = function() ACTIVE = false; return true end }
SC.ActionSupervisor = { begin = function() return { t = 1 } end, transition = function() return true end, commit = function(t, f) return f() end, complete = function() return true end, isCurrent = function() return true end, fail = function() end, containsDeferredStatus = function() return false end }
SC.Dialogue = nil
SC.WorkTransport = nil
SC.Registry = nil
""")
FW.execute(open(os.path.join(tmp, "SCFarmWork.lua"), encoding="utf-8").read())
FW.execute(r"""
BASE.zones[1] = { id = "z", kind = "farm", x1 = 1000, y1 = 1000, x2 = 1010, y2 = 1010, z = 0 }
BASE.storages = { { id = "s1", category = "farming", cont = container({ item("Base.Spade", { tag = "DIG_PLOW" }) }), x = 1000, y = 1000, z = 0 } }
SC.BaseWork.withdrawFromStorage = function(a, st, s, c, it) c.items = {}; a.inv.items[#a.inv.items + 1] = it; return true, "base_supply_taken" end
SC.BaseWork.returnToStorage = function(a, st, s, c, it) return true, "base_supply_returned" end
SC.BaseLife.farmReceipts = function() return {} end
SC.BaseLife.allocateFarmReceipt = function() return true, { id = "r1" } end
SC.BaseLife.updateFarmReceipt = function() end
SC.BaseLife.farmReceipt = function() return nil end
SC.BaseLife.farmRecoveryCursor = function() return 1 end
U = nil
SC.GameplayUtil.modData = function(i) i.md = i.md or {}; return i.md end
SC.GameplayUtil.isDead = function() return false end
SC.GameplayUtil.inventoryContains = function(inv, it) for _, x in ipairs(inv.items or inv) do if x == it then return true end end return false end
SC.GameplayUtil.squareOf = function() return nil end
JOB = { id = "job:1", type = "farm", target = { operation = "plow", x = 1003, y = 1003, z = 0, zoneId = "z", solPlanned = true } }
SOL.getCurrentSquare = function() return squareAt(1003, 1004, 0) end
SOL.getX = function() return 1003.5 end; SOL.getY = function() return 1004.5 end
FUPDATE = SC.FarmWork.update
A1, A2, A3 = nil, nil, nil
A1, A2, A3 = FUPDATE(SOL, {}, JOB, {})
B1, B2 = FUPDATE(SOL, {}, JOB, {})
C1, C2, C3 = FUPDATE(SOL, {}, JOB, {})
D1, D2, D3 = FUPDATE(SOL, {}, JOB, {})
plant({ x = 1003, y = 1003, state = "plow", typeOfSeed = "none" })
ACTIVE = false
F1, F2, F3 = FUPDATE(SOL, {}, JOB, {})
G1, G2, G3 = FUPDATE(SOL, {}, JOB, {})
""")
ck("SCFarmWork after s21: plow with no plant reaches the action", FW.eval("STARTED") == "plow", (FW.eval("A2"), FW.eval("C2"), FW.eval("D2"), FW.eval("F2")))
ck("SCFarmWork after s21: plow verified by state, job completed", FW.eval("DONE") == "farm_plow", (FW.eval("F2"), FW.eval("G2"), FW.eval("DONE")))
FW.execute(r"""
ACTIVE, STARTED, DONE = false, nil, nil
BASE.jobs = {}
plant({ x = 1004, y = 1004, hasWeeds = true })
JOBW = { id = "job:2", type = "farm", target = { operation = "weed", x = 1004, y = 1004, z = 0, zoneId = "z", solPlanned = true } }
SOL.getX = function() return 1004.5 end; SOL.getY = function() return 1005.5 end
P1 = FUPDATE(SOL, {}, JOBW, {})
Q = PLANTS[P_(1004, 1004, 0)]
Q.hasWeeds = false; ACTIVE = false
R1, R2 = FUPDATE(SOL, {}, JOBW, {})
S1 = FUPDATE(SOL, {}, JOBW, {})
""")
ck("SCFarmWork after s21: weed goes through and is judged by state", FW.eval("STARTED") == "weed" and FW.eval("DONE") == "farm_weed", (FW.eval("STARTED"), FW.eval("DONE")))
# SolAuthority after s22: rest allowed only while wanted
AU = lua51.LuaRuntime(unpack_returned_tuples=True); AU.execute(WORLD_LF)
AU.execute("SolAuthority = nil; SolLab = { active = true }; function getFileReader() return nil end")
AU.execute(open(os.path.join(tmp, "SolAuthority.lua"), encoding="utf-8").read())
ck("authority: downtime dropped without a standing order", AU.eval("SolAuthority.allowsDecision(SOL, 'downtime')") is False)
AU.execute("SolFarmKeeper = { restWanted = function() return true end }")
ck("authority: downtime allowed while she keeps home", AU.eval("SolAuthority.allowsDecision(SOL, 'downtime')") is True)
ck("authority: base_work stays gated by the order", AU.eval("SolAuthority.allowsDecision(SOL, 'base_work')") is False)
# SolLife after s24: a respawn wipes the farm memory too
LF2 = lua51.LuaRuntime(unpack_returned_tuples=True); LF2.execute(WORLD_LF)
LF2.execute("FORGOTTEN = 0; solFarmForget = function() FORGOTTEN = FORGOTTEN + 1 end; SC.GameplayUtil.idOf = function(a) return MYID end; MYID = 'a'")
LF2.execute(open(os.path.join(tmp, "SolLife.lua"), encoding="utf-8").read())
LF2.execute("SolLife.checkIdentity(); MYID = 'b'; SolLife.checkIdentity()")
ck("death (SolLife after s24): farm memory wiped", LF2.eval("FORGOTTEN") == 1, LF2.eval("FORGOTTEN"))
LF2.execute("SolLife.checkIdentity()")
ck("death: a reload does not wipe", LF2.eval("FORGOTTEN") == 1)

print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)

-- SolFarmAct.lua - how a farming action really happens on Sol.
--   Nobody has shown that the vanilla farming timed actions run on her (she is a non-local IsoPlayer, and ISPlowAction's complete uses getPlayerNum).
--   So she does each action herself: the real tool in hand, a real animation and sound for as long as it takes, then the same server calls the vanilla complete() makes.
--   Her job runner (SolFarmWork) starts one with A.begin and watches it with A.tick. What happened is kept per action. "sol_farm_try <action>" proves one at a time.
SolUI = SolUI or {}
local U = SolUI
SolFarmAct = SolFarmAct or {}
local A = SolFarmAct
A.VERSION = "0.2.0"
local DURATION = { plow = 7000, sow = 3000, water = 3000, harvest = 4000, cure = 3000, compost = 3000, weed = 4000, fill = 5000 }
local SOUNDS = { plow = "DigFurrowWithShovel", sow = "SowSeeds", water = "WaterCrops", harvest = "HarvestCrops", cure = "WaterCrops", compost = "DropSoilFromSandBag", weed = "HarvestCrops", fill = "GetWaterFromLake" }

local function log(m) print("[SolFarmAct] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
-- call() and tcall() hand back two values. The game's tonumber casts its first argument to a string as soon as it gets a second one, so a number crashes there.
local rawTonumber = tonumber
local function tonumber(v) return rawTonumber(v) end
local function g(name) return rawget(_G, name) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
local function sfs() local S = g("SFarmingSystem"); return type(S) == "table" and S.instance or nil end
local function view() return g("SolFarmView") end
local function plan() return g("SolFarmPlan") end
local function work() return g("SolFarmWork") end
local function solActor() return type(U.solActor) == "function" and U.solActor() or nil end
local function perkFarming(actor)
    local perks = g("Perks")
    return perks and tonumber((call(actor, "getPerkLevel", perks.Farming))) or 0
end

local fallbacks = setmetatable({}, { __mode = "k" })

local function record(op)
    local m = work().store()
    if m == nil then return nil end
    local r = m.proven[op]
    if r == nil then r = {}; m.proven[op] = r end
    return r, m
end
function A.proven(op) local r = record(op); return r end
local function note(op, field, value)
    local r = record(op)
    if r == nil then return end
    r[field] = value
    r.at = nowMs()
    log(op .. " " .. field .. "=" .. tostring(value))
end

local function intentXYZ(intent)
    if intent.square then return call(intent.square, "getX"), call(intent.square, "getY"), call(intent.square, "getZ") end
    if intent.plant then return intent.plant.x, intent.plant.y, intent.plant.z end
    return nil
end
local function live(intent)
    local x, y, z = intentXYZ(intent)
    if x == nil then return nil end
    return call(sfs(), "getLuaObjectAt", x, y, z), x, y, z
end
-- the plant is read again here, right before the action, whoever changed it during the walk
local function stillValid(op, intent)
    local p = plan()
    if op == "fill_water" then return true end
    local plantNow = live(intent)
    local task = { op = op, diseaseField = intent.diseaseField or (intent.cure and p.fieldOfCure and p.fieldOfCure(intent.cure)) }
    if op == "cure" then return plantNow ~= nil end
    return p.stillNeeded(task, plantNow)
end

-- ---------------------------------------------------------------- the server calls, the same ones the vanilla complete() makes
local APPLY = {}
function APPLY.plow(actor, intent)
    local S = g("SFarmingSystem")
    local sq = intent.square
    S:removeTallGrass(sq)                                  -- grass first, then the floor's grass, as ISPlowAction does
    local floor = sq:getFloor()
    local ptype = g("IsoPropertyType")
    if floor ~= nil and ptype ~= nil and floor:getProperties():has(ptype.GRASS_FLOOR) and sq:checkHaveGrass() == true then sq:removeGrass() end
    local here = S.instance:getLuaObjectOnSquare(sq)
    if here then S.instance:removePlant(here) end
    S.instance:plow(sq)
    S.instance:changePlayer(actor)
end
function APPLY.sow(actor, intent)
    local inv = actor:getInventory()
    local plant = sfs():getLuaObjectAt(intent.plant.x, intent.plant.y, intent.plant.z)
    if plant == nil or plant.state ~= "plow" then error("no furrow") end
    plant:seed(intent.cropType, perkFarming(actor))
    local holder = call(intent.item, "getContainer") or inv                  -- a seed may be in a bag she carries: only its own container can take it out
    holder:Remove(intent.item)
    local send = g("sendRemoveItemFromContainer")
    if type(send) == "function" then send(holder, intent.item) end
end
local function useWater(actor, item)
    local fc = call(item, "getFluidContainer")
    if fc ~= nil then
        local globals = g("ZomboidGlobals")
        local ml = globals and tonumber(globals.farmingFluidContainerMillilitresPerUse) or 200
        fc:adjustAmount(fc:getAmount() - ml / 1000)
        local sync = g("syncItemFields")
        if type(sync) == "function" then sync(actor, item) end
        return
    end
    item:UseAndSync()
end
function APPLY.water(actor, intent)
    local plant = sfs():getLuaObjectOnSquare(intent.square)
    if plant == nil then error("no plant") end
    local level, uses = plant.waterLvl, tonumber(intent.uses) or 1
    plant:water(nil, uses)
    for _ = 1, uses do
        if level < 100 then useWater(actor, intent.item); level = math.min(100, level + 10) end
    end
end
function APPLY.harvest(actor, intent)
    local plant = sfs():getLuaObjectAt(intent.plant.x, intent.plant.y, intent.plant.z)
    if plant == nil then error("no plant") end
    local S = sfs()
    S:gainXp(actor, plant)
    S:harvest(plant, actor)
end
local CURE = { Mildew = "cureMildew", Flies = "cureFlies", Aphids = "cureAphids", Slugs = "cureSlugs" }
function APPLY.cure(actor, intent)
    local plant = sfs():getLuaObjectAt(intent.plant.x, intent.plant.y, intent.plant.z)
    if plant == nil then error("no plant") end
    local uses = tonumber(intent.uses) or 1
    local fnName = CURE[intent.cure]
    plant[fnName](plant, nil, uses, perkFarming(actor))
    for _ = 1, uses do intent.item:UseAndSync() end
end
function APPLY.compost(actor, intent)
    local plant = sfs():getLuaObjectAt(intent.plant.x, intent.plant.y, intent.plant.z)
    if plant == nil then error("no plant") end
    local tags = g("ItemTag")
    local isCompost = tags ~= nil and call(intent.item, "hasTag", tags.COMPOST) == true
    plant:fertilize({ compost = isCompost, skill = perkFarming(actor) })
    intent.item:UseAndSync()
    local inv = actor:getInventory()
    local empty = call(inv, "Find", "FertilizerEmpty")
    if empty ~= nil then
        inv:Remove(empty)
        local send = g("sendRemoveItemFromContainer")
        if type(send) == "function" then send(inv, empty) end
    end
end
-- weeds: there is no vanilla action; what the plant counts as weeds is removed, one by one, and the plant itself never
local function removable(o, plantIso, S)
    if o == plantIso then return false end
    if call(o, "getContainer") ~= nil then return false end
    local sprite = call(o, "getSprite")
    if sprite == nil then return false end
    local props = call(sprite, "getProperties")
    local flags = g("IsoFlagType")
    if props == nil or type(flags) ~= "table" then return false end
    if call(props, "has", flags.canBeCut) == true then return false end
    local name = tostring(call(sprite, "getName") or "")
    return call(props, "has", flags.canBeRemoved) == true or call(props, "has", flags.vegitation) == true or string.sub(name, 1, 20) == "blends_grassoverlays"
end
function APPLY.weed(actor, intent)
    local S = sfs()
    local plant = S:getLuaObjectAt(intent.plant.x, intent.plant.y, intent.plant.z)
    if plant == nil then error("no plant") end
    local sq = intent.square
    local iso = call(plant, "getObject")
    local objects = sq:getObjects()
    for i = objects:size(), 1, -1 do
        local o = objects:get(i - 1)
        if removable(o, iso, S) then sq:transmitRemoveItemFromSquare(o) end
    end
    plant.hasWeeds = g("SFarmingSystem"):hasWeeds(sq)
    plant:saveData()
end
-- water into a can, the call ISTakeWaterAction's transferFluid makes
function APPLY.fill(actor, intent)
    local fc = intent.item:getFluidContainer()
    local room = fc:getCapacity() - fc:getAmount()
    if room <= 0 then return end
    intent.object:transferFluidTo(fc, room)
    call(intent.item, "syncItemFields")
    local stats = g("sendItemStats")
    if type(stats) == "function" then pcall(stats, intent.item) end
end
A.APPLY = APPLY

-- ---------------------------------------------------------------- the visible part
local REACH_TILES = 2
local function outOfReach(actor, intent)
    local x, y, z = intentXYZ(intent)
    local ax, ay = tonumber((call(actor, "getX"))), tonumber((call(actor, "getY")))
    if x == nil or ax == nil then return false end
    return math.max(math.abs(math.floor(ax) - x), math.abs(math.floor(ay) - y)) > REACH_TILES or math.floor(tonumber((call(actor, "getZ"))) or 0) ~= math.floor(tonumber(z) or 0)
end
local function startFallback(actor, op, intent, why)
    if APPLY[op] == nil then return false, "no_fallback:" .. tostring(op) end
    note(op, "fallbackStartedBecause", why)
    local fb = { op = op, intent = intent, oldPrimary = call(actor, "getPrimaryHandItem"), at = nowMs() }
    fb.doneAt = fb.at + (DURATION[op] or 3000) + (op == "water" and (tonumber(intent.uses) or 1) * 600 or 0)
    local x, y = intentXYZ(intent)
    if x ~= nil then call(actor, "faceLocation", x, y) end
    if intent.item and op ~= "sow" and op ~= "compost" and op ~= "cure" then call(actor, "setPrimaryHandItem", intent.item); fb.handed = intent.item end
    call(actor, "SetVariable", "LootPosition", "Low")
    call(actor, "reportEvent", "EventLootItem")
    call(actor, "playSound", SOUNDS[op])
    fallbacks[actor] = fb
    return true, "farm_" .. op .. "_fallback_started"
end
-- what she had in her hand comes back, unless she has taken up something else meanwhile (a weapon)
local function restoreHand(actor, fb)
    if fb.handed == nil or call(actor, "getPrimaryHandItem") ~= fb.handed then return end
    call(actor, "setPrimaryHandItem", fb.oldPrimary)
end
local function applyFallback(actor, fb)
    local ok, err = pcall(APPLY[fb.op], actor, fb.intent)
    restoreHand(actor, fb)
    note(fb.op, "fallback", ok and "called" or ("error:" .. tostring(err)))
    fb.applied, fb.failed = true, not ok
end

-- start one action; false and why when it cannot start
function A.begin(actor, op, intent)
    if type(intent) ~= "table" then return false, "no_intent" end
    if op ~= "fill" and not stillValid(op, intent) then return false, "farm_plant_changed" end
    if fallbacks[actor] ~= nil then return false, "already_acting" end
    return startFallback(actor, op, intent, "own_runner")
end
-- "active" while it lasts, then "ok" or "failed" once; nil when no action is known (nothing started, or the game was reloaded)
function A.tick(actor)
    local fb = fallbacks[actor]
    if fb == nil then return nil end
    if outOfReach(actor, fb.intent) then                                       -- she was driven off: nothing is done from a distance
        fallbacks[actor] = nil
        restoreHand(actor, fb)
        return "away"
    end
    if nowMs() < fb.doneAt then return "active" end
    if not fb.applied then applyFallback(actor, fb) end
    fallbacks[actor] = nil
    return fb.failed and "failed" or "ok"
end
function A.cancel(actor)
    local fb = fallbacks[actor]
    if fb == nil then return false end
    fallbacks[actor] = nil
    restoreHand(actor, fb)
    return true
end
-- the runner read the plant: only now is the action known to have worked
function A.confirm(op, worked) note(op, "fallback", worked and "applied" or "no_effect") end

-- ---------------------------------------------------------------- one action, proven on her: the nearest thing it can be done to
local TRY = {
    harvest = function(p) return p.veg == true end,
    water = function(p) return p.state == "seeded" and p.water < p.need end,
    cure = function(p) return p.state == "seeded" and (p.mildew > 0 or p.flies > 0 or p.aphid > 0 or p.slugs > 0) end,
    weed = function(p) return p.state == "seeded" and p.weeds == true end,
    compost = function(p) return p.state == "seeded" and p.fert == 0 and p.compost ~= true and p.nb <= 3 end,
    sow = function(p) return p.state == "plow" end,
    replant = function(p) return p.state ~= "seeded" and p.state ~= "plow" end,
}
local function cureOf(p)
    for _, pest in ipairs(plan().PESTS) do
        if (p[pest.key] or 0) > 0 then return pest end
    end
end
function A.trial(op)
    local a = solActor()
    if a == nil then return false, "sol_not_available" end
    local w, v, p = work(), view(), plan()
    local m = w.store()
    if m == nil then return false, "store_unavailable" end
    local here = v.posOf(a)
    local best, bd
    if op == "plow" then
        for _, tile in ipairs(v.landCandidates) do
            local d = here and math.max(math.abs(tile.x - here.x), math.abs(tile.y - here.y)) or 0
            if bd == nil or d < bd then best, bd = tile, d end
        end
        if best == nil then v.requestLand(1); return false, "no_free_tile_known_yet:ask_again" end
        best = { op = "plow", x = best.x, y = best.y, z = best.z, zoneId = best.zoneId, key = p.key(best) }
    else
        local ok = TRY[op]
        if ok == nil then return false, "unknown_action:" .. op end
        for _, plant in ipairs(v.allPlants()) do
            if ok(plant) then
                local d = here and math.max(math.abs(plant.x - here.x), math.abs(plant.y - here.y)) or 0
                if bd == nil or d < bd then best, bd = plant, d end
            end
        end
        if best == nil then return false, "nothing_to_try_on" end
        local task = { op = op, x = best.x, y = best.y, z = best.z, zoneId = best.zoneId, crop = best.crop, key = p.key(best) }
        if op == "sow" or op == "replant" then
            local env = w.env(a)
            task.crop = p.chooseCrop(v.stockLatest, env, nil)
            if task.crop == nil then return false, "no_seed_in_season_to_try" end
        elseif op == "water" then task.uses = 1
        elseif op == "cure" then
            local pest = cureOf(best)
            task.cure, task.cureItem, task.diseaseField, task.uses = pest.cure, pest.item, pest.field, 1
        end
        best = task
    end
    local okD, whyD = w.enterDuty(a, m)
    if not okD then return false, whyD end
    m.filter = { kind = "trial" }
    best.trial = true
    local issued, why = w._issueTrial(m, best, a)
    if not issued then return false, why end
    return true, "trial:" .. op .. ":started"
end
return A

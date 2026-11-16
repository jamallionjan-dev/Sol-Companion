-- SolGate.lua - the requirements gate for chores. Before Sol accepts a base role she takes stock of what the
-- base really has (her bag, every registered base storage, the zones) and answers with facts, never with a guess.
-- It wraps U.solRole (SolChores.lua). The answer is one machine-readable line; Sol Mind turns it into Arabic from
-- fixed templates, so the weak language model never words the result:
--   ok:<role>;have=...                    gate passed and Living Fellows accepted the role
--   gate:<role>;miss=a,b;have=...         gate failed: nothing was issued
--   lf:<reason>;have=...                  gate passed, Living Fellows refused with its own reason
-- have = counts of what was found (seed, tool, can, compost, spray) and how many storages were searched.
-- Debug mode stops the game on any error, even a caught one, so every call is checked before it is made.
SolUI = SolUI or {}
local U = SolUI
U.GATE_VERSION = "0.1.0"
local function log(m) print("[SolGate] " .. tostring(m)) end

-- same role words as SolChores.lua
local ROLES = {
    generalist = true, guard = true, builder = true, quartermaster = true, medic = true,
    farmer = true, angler = true, chef = true, woodcutter = true, corpsekeeper = true, maintainer = true,
}
local ALIAS = {
    farm = "farmer", farming = "farmer", crops = "farmer", harvest = "farmer", plants = "farmer",
    wood = "woodcutter", lumber = "woodcutter", chop = "woodcutter", logs = "woodcutter",
    fish = "angler", fishing = "angler", clean = "maintainer", maintain = "maintainer", repair = "maintainer",
    cook = "chef", normal = "generalist", general = "generalist",
}
local function normalize(option)
    local o = string.lower(tostring(option or ""))
    o = string.gsub(o, "^%s+", ""); o = string.gsub(o, "%s+$", "")
    if ROLES[o] then return o end
    return ALIAS[o]
end

local function LF()
    local sc = SurvivorCompanion
    if type(sc) == "table" then return sc end
    return nil
end
local function call(fn, ...)
    if type(fn) ~= "function" then return nil end
    local ok, a, b = pcall(fn, ...)
    if ok then return a, b end
    return nil
end

-- the same test Living Fellows applies in FarmWork.isFarmingSupply
local function classify(gu, item)
    local kind = string.lower(tostring(call(gu.itemType, item) or ""))
    if call(gu.itemHasTag, item, "DIG_PLOW") then return "tool" end
    if call(gu.itemHasTag, item, "COMPOST") or call(gu.itemHasTag, item, "FERTILIZER") or string.find(kind, "compostbag", 1, true) or string.find(kind, "fertilizer", 1, true) then return "compost" end
    if string.find(kind, "wateredcan", 1, true) or string.find(kind, "wateringcan", 1, true) then return "can" end
    if string.find(kind, "seed", 1, true) then return "seed" end
    if string.find(kind, "gardeningspray", 1, true) or string.find(kind, "slugrepellent", 1, true) then return "spray" end
    return nil
end

-- take stock: only what the farm job can borrow, the categories it withdraws from (a storage not loaded is counted apart, it is unknown rather than empty)
local function scan(sol)
    local sc = LF()
    local gu = sc and sc.GameplayUtil or nil
    local have = { seed = 0, tool = 0, can = 0, compost = 0, spray = 0, stor = 0, unloaded = 0 }
    if type(gu) ~= "table" then return have end
    local function add(items)
        if type(items) ~= "table" then return end
        for _, item in ipairs(items) do
            local k = classify(gu, item)
            if k then have[k] = have[k] + 1 end
        end
    end
    local BL = sc.BaseLife
    if type(BL) == "table" and type(BL.storageRows) == "function" then
        for _, cat in ipairs({ "farming", "tools", "water" }) do
            local rows = call(BL.storageRows, cat, true)
            if type(rows) == "table" then
                for _, storage in ipairs(rows) do
                    local container = call(BL.resolveContainer, storage)
                    if container ~= nil then
                        have.stor = have.stor + 1
                        add(call(gu.inventoryItems, container, 80))
                    else
                        have.unloaded = have.unloaded + 1
                    end
                end
            end
        end
    end
    return have
end

local function haveText(have)
    return "have=seed:" .. have.seed .. ",tool:" .. have.tool .. ",can:" .. have.can .. ",compost:" .. have.compost
        .. ",spray:" .. have.spray .. ",stor:" .. have.stor .. ",unloaded:" .. have.unloaded
end

-- what Living Fellows needs, from its own code (SCFarmWork reasons, SCBaseLife autonomousProductionSpec)
local function check(role, have)
    local sc = LF()
    local BL = sc and sc.BaseLife or nil
    if type(BL) ~= "table" or not call(BL.active) then return { "base" } end
    local miss = {}
    if role == "farmer" then
        if not call(BL.zoneCenter, "farm") then miss[#miss + 1] = "farm_zone" end
        if have.seed + have.tool + have.can + have.compost + have.spray == 0 and have.unloaded == 0 then miss[#miss + 1] = "farm_supplies" end
        local food = call(BL.depositStorageRows, "food")
        if type(food) ~= "table" or #food == 0 then miss[#miss + 1] = "food_storage" end
    elseif role == "woodcutter" then
        local center, zone = call(BL.zoneCenter, "lumber")
        if not center then
            miss[#miss + 1] = "lumber_zone"
        elseif call(BL.lumberZoneReachable, zone) ~= true then
            miss[#miss + 1] = "lumber_unreachable"
        end
        local any = call(BL.depositStorageRows, nil)
        if type(any) ~= "table" or #any == 0 then miss[#miss + 1] = "log_storage" end
    end
    return miss
end

function U.solGate(option, base)
    local role = normalize(option)
    if not role then return base(option) end                       -- unknown word: SolChores answers
    if role == "farmer" then                                                  -- farming is hers now, not a Living Fellows role
        if type(U.solFarmOrder) ~= "function" then return false, "lf:farm_unavailable" end
        local okF, whyF = U.solFarmOrder("keeper")
        if okF then return true, "base_role_farmer" end
        return false, "lf:" .. tostring(whyF)
    end
    local sol = type(U.solActor) == "function" and U.solActor() or nil
    if sol == nil then return false, "gate:" .. role .. ";miss=sol" end
    local have = scan(sol)
    local miss = check(role, have)
    if #miss > 0 then return false, "gate:" .. role .. ";miss=" .. table.concat(miss, ",") .. ";" .. haveText(have) end
    local ok, why = base(role)
    if ok then return true, "ok:" .. role .. ";" .. haveText(have) end
    return false, "lf:" .. tostring(why) .. ";" .. haveText(have)
end

local function install()
    if U._gateInstalled then return end
    local base = U.solRole
    if type(base) ~= "function" then log("SolChores is missing: the gate is not installed"); return end
    U._gateInstalled = true
    U.solRole = function(option) return U.solGate(option, base) end
    log("gate installed v" .. U.GATE_VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(install) end
log("ready v" .. U.GATE_VERSION)

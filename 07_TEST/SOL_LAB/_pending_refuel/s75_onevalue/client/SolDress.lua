-- SolDress.lua - What Sol has on her.
-- First Sol in a world: the desert military kit and a katana, once.
-- A new Sol after a death: everything taken off her, then an ordinary vanilla outfit and nothing else.
-- A reload keeps her id, so she is left exactly as she was.
SolUI = SolUI or {}
local U = SolUI
U.DRESS_VERSION = "0.2.0"
local CHECK_MS = 3000
local LOADOUT_STORE = "Sol_InitialDesertLoadout"
local function log(m) print("[SolDress] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function call(o, name, ...)
    if o == nil then return nil end
    local f = o[name]; if f == nil then return nil end
    local ok, v = pcall(f, o, ...); if ok then return v end; return nil
end
-- one slot = first vanilla item that exists in this game version
U.SOL_OUTFIT = {
    { "Base.Bra_Straps_White", "Base.Bra_Straps_Black" },
    { "Base.Underpants_White", "Base.Underpants_Black" },
    { "Base.Socks_Ankle", "Base.Socks_Long" },
    { "Base.Tshirt_DefaultTEXTURE_TINT", "Base.Tshirt_White", "Base.Tshirt_DefaultTEXTURE" },
    { "Base.Jacket_WhiteTINT", "Base.Jacket_Padded", "Base.HoodieUP_WhiteTINT", "Base.Jumper_RoundNeck" },      -- closed, and these models hide the torso beneath them
    { "Base.Trousers_Denim", "Base.Trousers_JeanBaggy", "Base.Trousers" },
    { "Base.Shoes_TrainerTINT", "Base.Shoes_Black", "Base.Shoes_Brown" },
}
U.INITIAL_DESERT_LOADOUT = {
    { "Base.Hat_ArmyDesertNew", "wear" },
    { "Base.Jacket_ArmyCamoDesertNew", "wear" },
    { "Base.Trousers_CamoDesertNew", "wear" },
    { "Base.Vest_BulletDesertNew", "wear" },
    { "Base.Bag_ALICEpack_DesertCamo", "wear" },
    { "Base.Shoes_ArmyBootsDesert", "wear" },
    { "Base.Katana", "primary" },
}
local function itemExists(fullType)
    local sm = ScriptManager and ScriptManager.instance
    if sm and call(sm, "getItem", fullType) then return true end
    local gsm = getScriptManager and getScriptManager()
    if gsm and call(gsm, "FindItem", fullType) then return true end
    return false
end
function U.wornCount(actor)
    local worn = call(actor, "getWornItems")
    return worn and (tonumber((call(worn, "size"))) or 0) or 0
end
local function loadoutStore()
    if type(ModData) ~= "table" or type(ModData.getOrCreate) ~= "function" then
        return nil, "moddata_unavailable"
    end
    local ok, data = pcall(ModData.getOrCreate, LOADOUT_STORE)
    if not ok or type(data) ~= "table" then return nil, "moddata_failed" end
    return data
end
local function markInitialLoadoutUsed(data)
    data.initialDesertKitGranted = true
    if type(ModData.transmit) == "function" then pcall(ModData.transmit, LOADOUT_STORE) end
end
local function addAndEquip(actor, inventory, fullType, mode)
    if not itemExists(fullType) then return false, "item_missing:" .. fullType end
    local item = call(inventory, "AddItem", fullType)
    if item == nil then return false, "item_add_failed:" .. fullType end
    local ok, result = false, nil
    if mode == "primary" then
        ok, result = pcall(function() return actor:setPrimaryHandItem(item) end)
    else
        local location = call(item, "getBodyLocation")
        if location == nil or location == "" then location = call(item, "canBeEquipped") or call(item, "getCanBeEquipped") end        -- a bag is equipped, not worn (42.22 renamed it canBeEquipped)
        if location ~= nil and location ~= "" then
            ok, result = pcall(function() return actor:setWornItem(location, item) end)
        end
        if (not ok or result == false) and (call(item, "canBeEquipped") or call(item, "getCanBeEquipped")) ~= nil then
            ok, result = pcall(function() return actor:setClothingItem_Back(item) end)
        end
    end
    if not ok or result == false then return false, "equip_failed:" .. fullType end
    return true
end
-- One item that cannot be equipped must not cost her the rest of the kit.
local function grantInitialDesertLoadout(actor, inventory)
    local missed = nil
    for _, entry in ipairs(U.INITIAL_DESERT_LOADOUT) do
        local ok, reason = addAndEquip(actor, inventory, entry[1], entry[2])
        if not ok then missed = reason; log("kit item skipped: " .. tostring(reason)) end
    end
    call(actor, "resetModelNextFrame")
    if missed then return false, missed end
    return true
end
local function stripEverything(actor, inventory)
    pcall(function() actor:setPrimaryHandItem(nil) end)
    pcall(function() actor:setSecondaryHandItem(nil) end)
    pcall(function() actor:setClothingItem_Back(nil) end)
    local worn = call(actor, "getWornItems")
    if worn ~= nil then pcall(function() worn:clear() end) end
    local items = call(inventory, "getItems")
    local n = items and (tonumber((call(items, "size"))) or 0) or 0
    local all = {}
    for i = 0, n - 1 do all[#all + 1] = call(items, "get", i) end
    for _, item in ipairs(all) do
        if not pcall(function() inventory:DoRemoveItem(item) end) then pcall(function() inventory:Remove(item) end) end
    end
    log("a new Sol: took off " .. #all .. " items she should not have")
end
local function idOf(actor)
    local SC = rawget(_G, "SurvivorCompanion")
    if type(SC) ~= "table" or type(SC.GameplayUtil) ~= "table" or type(SC.GameplayUtil.idOf) ~= "function" then return nil end
    local ok, id = pcall(SC.GameplayUtil.idOf, actor)
    if ok and type(id) == "string" and id ~= "" then return id end
    return nil
end
local function dressVanilla(actor, inventory)
    local put = {}
    for _, slot in ipairs(U.SOL_OUTFIT) do
        for _, fullType in ipairs(slot) do
            if itemExists(fullType) then
                local ok = addAndEquip(actor, inventory, fullType, "wear")
                if ok then put[#put + 1] = fullType end
                break
            end
        end
    end
    if #put > 0 then call(actor, "resetModelNextFrame") end
    log("Sol had no clothes; dressed with " .. #put .. " vanilla items: " .. table.concat(put, ", "))
    return #put > 0, put
end
function U.dressSol(actor)
    actor = actor or (U.solActor and U.solActor())
    if not actor then return false, "no_sol" end
    local inv = call(actor, "getInventory")
    if not inv then return false, "no_inventory" end
    local state, stateReason = loadoutStore()
    if state == nil then return false, stateReason end
    local id = idOf(actor)
    if id == nil then return false, "moddata_unavailable" end                     -- not registered yet: looked at again in a moment
    local known = state.dressedId
    state.dressedId = id
    if state.initialDesertKitGranted == true and known ~= nil and known ~= id then
        stripEverything(actor, inv)
        if type(ModData.transmit) == "function" then pcall(ModData.transmit, LOADOUT_STORE) end
        return dressVanilla(actor, inv)
    end
    if state.initialDesertKitGranted == true and known == id then return false, "same_sol" end
    if state.initialDesertKitGranted ~= true then
        local ok, reason = grantInitialDesertLoadout(actor, inv)
        -- Consume the special starter kit even if an item definition or equip
        -- call is unavailable; the safe fallback is vanilla clothing.
        markInitialLoadoutUsed(state)
        if ok then
            log("first Sol spawn received desert military kit and a katana")
            return true, U.INITIAL_DESERT_LOADOUT
        end
        log("initial desert kit incomplete (" .. tostring(reason) .. ")")
    end
    if type(ModData.transmit) == "function" then pcall(ModData.transmit, LOADOUT_STORE) end
    if U.wornCount(actor) > 0 then return false, "already_dressed" end
    return dressVanilla(actor, inv)
end
local checkedActor, lastCheck = nil, 0
local function onTick()
    local t = nowMs()
    if t - lastCheck < CHECK_MS then return end
    lastCheck = t
    local sol = U.solActor and U.solActor()
    if not sol or sol == checkedActor then return end
    local ok, dressed, reason = pcall(U.dressSol, sol)
    if not ok then
        log("dress failed: " .. tostring(dressed))
        checkedActor = sol
    elseif dressed == false and (reason == "moddata_unavailable" or reason == "moddata_failed") then
        -- Retry when the world ModData adapter finishes initializing.
        return
    else
        checkedActor = sol          -- every new Sol actor is processed once
    end
end
require "SolBudget"
SolBudget.register("dress", onTick, { everyMs = 500, priority = 4 })
log("ready v" .. U.DRESS_VERSION)

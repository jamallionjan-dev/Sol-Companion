-- SolWeaponPick.lua - switches weapon_scan and melee_choice (2026-11-11, s99).
-- Live 12:00:58-12:02:41 (DebugLog 17488/17502): "[SurvivorCompanion/combat] ... weapon=Wrench carried=1 usable=1" and
-- "combat-engage ... weapon=Base.Wrench": she fought with a wrench although the katana and the G28 were hers (his carry
-- orders on both reached SCCombat.equipExactWeapon, which needs the item in her own containers, SCUIBridge.lua:370-373).
-- LF lists her weapons from a capped item walk: SCCombat inventoryWeapons uses SC.InventoryIndex.weapons or
-- U.inventoryItemsDeep(inventory, combatInventoryScanLimit or 240) (SCCombat.lua:1117-1121), and the walk stops at 240
-- items, 180 of them from the root (SCGameplayUtil.lua:1246-1285, SCInventoryIndex.lua:64-113). Some 500 loose 7.62x51
-- rounds are items too: the weapons after them are never seen (carried=1). The same truncated index answers
-- hasReloadAmmo (SCCombat.lua:1163-1177), so a loaded magazine behind the rounds is invisible as well.
-- weapon_scan: inventoryWeapons also takes the weapons the walk missed, from the container's own recursive lookup
--   getAllCategoryRecurse("Weapon") (Java side, no per-item Lua call), and logs once what LF missed.
-- melee_choice:
--   meleeScore(actor, w, score): damage x condition (0.25 + 0.75 x condition ratio), long blade +20, axe/blunt +14,
--     spear +12, small blade +4, small blunt 0 (WeaponCategory, as XpUpdate.lua:89-104 reads it), a tool weapon
--     (DisplayCategory ToolWeapon) -15; the one in her hands +6 (no swap for nothing). While her preferred melee weapon is
--     usable every OTHER melee weapon gets -1000, so it is her melee weapon; firearm against melee is still LF's call.
--   her preferred melee weapon: the one he picked with "carry this weapon" (item modData SolMeleeFor = her id), else a
--     katana she carries.
--   SolCombatEquipFallback.choose no longer keeps a melee weapon only because it is in her hands (it kept the wrench).
-- Switches read at call time; off = LF's own list and scores.
SolWeaponPick = SolWeaponPick or {}
local W = SolWeaponPick
W.VERSION = "0.1.0"
W.CACHE_MS = 1000
W.MAX_WEAPONS = 64
W.KATANA = { ["Base.Katana"] = true }
W.CATEGORY = { { "LONG_BLADE", 20 }, { "AXE", 14 }, { "BLUNT", 14 }, { "SPEAR", 12 }, { "SMALL_BLADE", 4 }, { "SMALL_BLUNT", 0 } }
W.TOOL_PENALTY = 15
W.OTHER_MELEE_PENALTY = 1000
W.HELD_BONUS = 6
W.cache = W.cache or setmetatable({}, { __mode = "k" })
W.said = W.said or setmetatable({}, { __mode = "k" })

local rawTonumber = tonumber
local function num(v) return rawTonumber(v) end
local function g(name) return rawget(_G, name) end
local function nowMs() local f = g("getTimestampMs"); return f and f() or 0 end
local function log(m) print("[SolWeaponPick] " .. tostring(m)) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
local function sw(fix) local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on(fix) == true end
function W.scanOn() return sw("weapon_scan") end
function W.meleeOn() return sw("melee_choice") end
local function fullType(it) return tostring(call(it, "getFullType") or "?") end
local function idOf(actor)
    local SC = g("SurvivorCompanion")
    local U = type(SC) == "table" and SC.GameplayUtil or nil
    if type(U) ~= "table" or type(U.idOf) ~= "function" then return nil end
    local ok, id = pcall(U.idOf, actor)
    return ok and id or nil
end

-- every weapon in her containers (bags included), cached for CACHE_MS per inventory
function W.weapons(inventory)
    if inventory == nil then return {} end
    local c = W.cache[inventory]
    local t = nowMs()
    if type(c) == "table" and t < c.expires then return c.items end
    local jl = call(inventory, "getAllCategoryRecurse", "Weapon", ArrayList.new())
    local items = {}
    local n = num((call(jl, "size"))) or 0
    for i = 0, math.min(n, W.MAX_WEAPONS) - 1 do
        local it = call(jl, "get", i)
        if it ~= nil then items[#items + 1] = it end
    end
    W.cache[inventory] = { items = items, expires = t + W.CACHE_MS }
    return items
end

-- weapon_scan: the weapons LF's capped walk did not list (records: LF's weapon records so far)
function W.missing(actor, inventory, records)
    if not W.scanOn() or inventory == nil then return {} end
    local have = {}
    for _, r in ipairs(records or {}) do if type(r) == "table" and r.item ~= nil then have[r.item] = true end end
    local primary = call(actor, "getPrimaryHandItem")
    local out, names = {}, {}
    for _, it in ipairs(W.weapons(inventory)) do
        if not have[it] and it ~= primary then out[#out + 1] = it; names[#names + 1] = fullType(it) end
    end
    if #out > 0 then
        local key = table.concat(names, ",")
        if W.said[inventory] ~= key then
            W.said[inventory] = key
            local root = num((call(call(inventory, "getItems"), "size"))) or -1
            log("LF's item walk (limit 240) missed " .. tostring(#out) .. " weapon(s): " .. key .. " (root container holds " .. tostring(root) .. " items)")
        end
    end
    return out
end

-- ---------------------------------------------------------------- melee
function W.categoryBonus(item)
    local WC = g("WeaponCategory")
    local script = call(item, "getScriptItem")
    if type(WC) ~= "table" and type(WC) ~= "userdata" then return 0, nil end
    if script == nil then return 0, nil end
    for _, c in ipairs(W.CATEGORY) do
        local enum = WC[c[1]]
        if enum ~= nil and call(script, "containsWeaponCategory", enum) == true then return c[2], c[1] end
    end
    return 0, nil
end
function W.isTool(item) return tostring(call(item, "getDisplayCategory") or "") == "ToolWeapon" end

-- the item he marked as her melee weapon, else nil
local function marked(item, id)
    if id == nil or call(item, "hasModData") ~= true then return false end
    local md = call(item, "getModData")
    return type(md) == "table" and md.SolMeleeFor == id
end
function W.preferredMelee(actor)
    local inv = call(actor, "getInventory")
    local id = idOf(actor)
    local katana
    local primary = call(actor, "getPrimaryHandItem")
    local all = {}
    if primary ~= nil then all[1] = primary end
    for _, it in ipairs(W.weapons(inv)) do all[#all + 1] = it end
    for _, it in ipairs(all) do
        if call(it, "isRanged") ~= true then
            if marked(it, id) and (num((call(it, "getCondition"))) or 1) > 0 then return it end
            if katana == nil and W.KATANA[fullType(it)] and (num((call(it, "getCondition"))) or 1) > 0 then katana = it end
        end
    end
    return katana
end

function W.meleeScore(actor, weapon, score)
    if not W.meleeOn() or type(weapon) ~= "table" or weapon.ranged then return score end
    local item = weapon.item
    local cond = num(weapon.conditionRatio) or 1
    local s = (num(weapon.damage) or 1) * 12 * (0.25 + 0.75 * cond)
        + (num(weapon.range) or 1) * 0.5 - (num(weapon.swing) or 1) * 2 - (num(weapon.staminaCost) or 1) * 1.5
    s = s + (W.categoryBonus(item))
    if W.isTool(item) then s = s - W.TOOL_PENALTY end
    local pm = W.preferredMelee(actor)
    if pm ~= nil and pm ~= item then s = s - W.OTHER_MELEE_PENALTY end
    if weapon.equipped == true then s = s + W.HELD_BONUS end
    return s
end

-- his "carry this weapon" on a melee weapon: it becomes her melee weapon (only one per Sol)
function W.markMelee(actor, item)
    if not W.meleeOn() or item == nil or call(item, "isRanged") == true then return false end
    local id = idOf(actor)
    if id == nil then return false end
    for _, it in ipairs(W.weapons(call(actor, "getInventory"))) do
        if it ~= item and call(it, "hasModData") == true then
            local md = call(it, "getModData")
            if type(md) == "table" and md.SolMeleeFor == id then md.SolMeleeFor = nil end
        end
    end
    local md = call(item, "getModData")
    if type(md) == "table" then md.SolMeleeFor = id end
    log("her melee weapon: " .. fullType(item))
    return true
end

log("ready v" .. W.VERSION)
return W

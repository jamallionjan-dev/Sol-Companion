-- SolKitBare.lua - switch kit_bare (s103). A weapon Sol builds or restores starts BARE, so no EFZ default part is left
-- next to the parts it really has.
-- Why (2026-11-11, live): Sol's M4A1 came back from a reload with "[TW] Assembly needs attention ... duplicatePath" on
-- mod_pistol_grip, mod_barrel, mod_gas_block, mod_muzzle, mod_handguard (x2) and mod_stock_000.
-- Root cause: EFZ's item script runs OnCreate = TWRuntime.createDefault (TW_Items.txt:79, Runtime.lua:484) every time an
-- EFZ weapon is instanced (InventoryItem.initialiseItem). SCPersistence rebuilds Sol's inventory on load with
-- AddItem(type) / CreateItem(type) (fresh item = default preset installed) and then attaches the saved parts on top.
-- Vanilla HandWeapon keys parts by PartType (one per EFZ template), so a saved part of the SAME template replaces its
-- default, but a saved part of a DIFFERENT template lands beside the default on the same TWPath: exactly the M4A1 paths
-- where Jamal's build differs from EFZ's M4A1_Std preset (his G28 is the default preset, so it never showed it).
-- EFZ's own TWRuntime.applyTree (Runtime.lua:798) already detaches every EFZ part before it installs a tree, so
-- SolSecretLoadout's give was right; it is stripped here as well, so it does not depend on that.
-- The strip is HandWeapon.clearAllWeaponParts(): the exact inverse of attachWeaponPart(part, false) (createDefault's and
-- SCPersistence's call: no stat change, no OnDetach); B42's own HandWeapon.load starts with it too.
-- ASCII only.
SolKitBare = SolKitBare or {}
local K = SolKitBare
K.VERSION = "0.1.0"
K.MAX_PRUNE = 32

local function log(m) print("[SolKitBare] " .. tostring(m)) end
local function g(name) return rawget(_G, name) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or type(f) ~= "function" then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end

function K.on()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("kit_bare") == true
end

local function runtime()
    local R = g("TWRuntime")
    if type(R) == "table" and type(R.key) == "function" then return R end
    return nil
end
local function core()
    local ok, C = pcall(require, "TW/Core")
    if ok and type(C) == "table" and type(C.validate) == "function" then return C end
    return nil
end

function K.efzKey(w)
    local R = runtime()
    if R == nil or w == nil then return nil end
    local ok, key = pcall(R.key, w)
    if ok then return key end
    return nil
end

-- The weapon's parts as a Lua array (getAllWeaponParts, 0 arguments).
function K.parts(w)
    local out = {}
    local list = call(w, "getAllWeaponParts")
    local n = tonumber(list ~= nil and call(list, "size") or 0) or 0
    for i = 0, n - 1 do
        local p = call(list, "get", i)
        if p ~= nil then out[#out + 1] = p end
    end
    return out
end

-- The EFZ path a part sits on: TWRuntime.installedPath (the detachable magazine = mod_magazine), else its TWPath.
function K.pathOf(part)
    local R = runtime()
    if R ~= nil and type(R.installedPath) == "function" then
        local ok, p = pcall(R.installedPath, part)
        if ok and type(p) == "string" then return p end
        if ok then return nil end
    end
    local md = call(part, "getModData")
    if type(md) == "table" and type(md.TWPath) == "string" then return md.TWPath end
    return nil
end

local function tplOf(part)
    local R = runtime()
    if R ~= nil and type(R.meta) == "function" then
        local ok, meta = pcall(R.meta, part)
        if ok and type(meta) == "table" then return meta.tpl end
    end
    return nil
end

-- Every part off (no stat change, no callback). Returns how many there were.
function K.strip(w)
    local n = #K.parts(w)
    if n > 0 then call(w, "clearAllWeaponParts") end
    return n
end

-- Put exactly `keep` back on, in order (attachWeaponPart(part, false), as createDefault / applyTree / SCPersistence).
local function rebuild(w, keep)
    call(w, "clearAllWeaponParts")
    for _, p in ipairs(keep) do call(w, "attachWeaponPart", p, false) end
end

-- One part per EFZ path; the LAST attached wins (a restore attaches the saved parts after the defaults).
-- Returns the dropped "path(type)" list.
function K.dedupe(w)
    local list = K.parts(w)
    if #list < 2 then return {} end
    local last, paths = {}, {}
    for i, p in ipairs(list) do
        local path = K.pathOf(p)
        paths[i] = path
        if path ~= nil then last[path] = i end
    end
    local keep, dropped = {}, {}
    for i, p in ipairs(list) do
        if paths[i] ~= nil and last[paths[i]] ~= i then dropped[#dropped + 1] = paths[i] .. "(" .. tostring(call(p, "getFullType")) .. ")"
        else keep[#keep + 1] = p end
    end
    if #dropped > 0 then rebuild(w, keep) end
    return dropped
end

-- EFZ's own rules (TW/Core C.validate): a part on a path whose parent is gone, or that its slot refuses, comes off;
-- for a conflict / too many copies the earlier attached one comes off. Returns the dropped list.
function K.prune(w)
    local key = K.efzKey(w)
    local C = core()
    local dropped = {}
    if key == nil or C == nil then return dropped end
    for _ = 1, K.MAX_PRUNE do
        local list = K.parts(w)
        local tree, at = {}, {}
        for i, p in ipairs(list) do
            local path, tpl = K.pathOf(p), tplOf(p)
            if path ~= nil and tpl ~= nil then tree[path] = tpl; at[path] = i end
        end
        local okV, valid, reason, detail = pcall(C.validate, key, tree)
        if not okV or valid == true then break end
        local victim
        if (reason == "missingParent" or reason == "incompatible" or reason == "unsupportedRoute" or reason == "unknownPart"
            or reason == "maxCopies") and type(detail) == "string" then
            victim = at[detail]
        elseif reason == "conflict" and type(detail) == "string" then
            local a, b = string.match(detail, "^(%w+):(%w+)$")
            for i, p in ipairs(list) do
                local tpl = tplOf(p)
                if victim == nil and tpl ~= nil and (tpl == a or tpl == b) then victim = i end
            end
        end
        if victim == nil then break end                         -- magazineConflict etc.: EFZ's reload owns it
        dropped[#dropped + 1] = tostring(reason) .. ":" .. tostring(K.pathOf(list[victim])) .. "(" .. tostring(call(list[victim], "getFullType")) .. ")"
        table.remove(list, victim)
        rebuild(w, list)
    end
    return dropped
end

-- EFZ's state (md.TW.ready, stats, magazine visual) from what is on it now. No player: nothing is unequipped.
function K.refresh(w)
    local R = runtime()
    if R == nil or type(R.refresh) ~= "function" or K.efzKey(w) == nil then return false end
    local ok = pcall(R.refresh, w, nil)
    return ok
end

-- A weapon with nothing on it: no part, no magazine, no round. EFZ sees a bare receiver that needs assembly.
function K.bare(w)
    local n = K.strip(w)
    call(w, "setContainsClip", false)
    call(w, "setCurrentAmmoCount", 0)
    call(w, "setRoundChambered", false)
    local md = call(w, "getModData")
    if type(md) == "table" then md.AmmoList = nil end
    K.refresh(w)
    return n
end

-- SCPersistence.addInventoryNode, before the saved parts go on: the new item's own parts (EFZ defaults) come off.
-- Only when the snapshot has parts, or the item is an EFZ weapon (a bare EFZ receiver is saved with none).
function K.beforeParts(item, entry)
    if item == nil or type(entry) ~= "table" then return 0 end
    local saved = type(entry.weaponParts) == "table" and #entry.weaponParts or 0
    if saved == 0 and K.efzKey(item) == nil then return 0 end
    local n = K.strip(item)
    if n > 0 then log("restore " .. tostring(entry.type) .. ": " .. n .. " part(s) the new item came with removed; " .. saved .. " saved part(s) go on") end
    return n
end

-- After the saved parts: a snapshot taken from an already doubled weapon is made single again.
function K.afterParts(item)
    if item == nil or K.efzKey(item) == nil then return 0 end
    local d = K.dedupe(item)
    local p = K.prune(item)
    if #d + #p > 0 then
        K.refresh(item)
        log("repaired " .. tostring(call(item, "getFullType")) .. ": duplicate " .. table.concat(d, ",") .. " invalid " .. table.concat(p, ","))
    end
    return #d + #p
end

return K

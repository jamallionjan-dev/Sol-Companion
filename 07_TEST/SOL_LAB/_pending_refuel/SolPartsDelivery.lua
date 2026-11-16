-- SolPartsDelivery.lua - switch parts_delivery (s103). Once, on the first load after install, Jamal (the PLAYER) gets
-- his two guns as a kit to assemble himself with EFZ's Assembly menu:
--   one BARE HK G28 and one BARE Colt M4A1 (receiver only: no part, no magazine, no round),
--   every part of the two stored builds as a separate loose item (EFZ's loose part = D.items[tpl].pz, no TWPath, which
--   TWRuntime.looseParts / canInstall / install take; TW_AssemblyMenu.lua lists "Install <part>" for each),
--   one EMPTY magazine per gun (the build's magazine type, w1.mag / w2.mag).
-- The builds are SolSecretLoadout's (shipped data or Zomboid/Lua/Sol_SecretLoadout.txt), decoded with EFZ's own TW/Builds.
-- A bare EFZ weapon: instanceItem runs EFZ's OnCreate (TWRuntime.createDefault, the default preset); SolKitBare.bare
-- takes it all off again and TWRuntime.refresh(w, nil) records md.TW.ready=false. With no player passed nothing is
-- unequipped; it sits in the inventory as a receiver that needs assembly (EFZ refuses it in the hands until it is ready,
-- as for any incomplete EFZ gun).
-- Once: player modData SolPartsDelivery = { v, at, items }. Switch off: nothing. ASCII only.
SolPartsDelivery = SolPartsDelivery or {}
local M = SolPartsDelivery
M.VERSION = "0.1.0"
M.FLAG = "SolPartsDelivery"
M.TRY_MS = 2000
M.MAX_TRIES = 60

local function log(m) print("[SolPartsDelivery] " .. tostring(m)) end
local function g(name) return rawget(_G, name) end
local function nowMs() local f = g("getTimestampMs"); return type(f) == "function" and f() or 0 end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or type(f) ~= "function" then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
function M.on() local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on("parts_delivery") == true end
local function player()
    local f = g("getSpecificPlayer")
    if type(f) == "function" then local ok, p = pcall(f, 0); if ok and p ~= nil then return p end end
    f = g("getPlayer")
    if type(f) == "function" then local ok, p = pcall(f); if ok then return p end end
    return nil
end
local function newItem(t)
    local f = g("instanceItem")
    if type(f) ~= "function" or t == nil or t == "" then return nil end
    local ok, it = pcall(f, t)
    if ok then return it end
    return nil
end
local function addTo(inv, item)
    if item == nil then return false end
    local got = call(inv, "AddItem", item)
    if got == nil then return false end
    local isC = g("isClient")
    local send = g("sendAddItemToContainer")
    if type(isC) == "function" and isC() and type(send) == "function" then pcall(send, inv, item) end
    return true
end
local function efz()
    local okB, B = pcall(require, "TW/Builds")
    local okC, C = pcall(require, "TW/Core")
    if not okB or type(B) ~= "table" or type(B.decode) ~= "function" then B = nil end
    if not okC or type(C) ~= "table" or type(C.isClip) ~= "function" then C = nil end
    return B, C
end

-- What one stored gun is as a kit: { weapon, parts = { type... }, mag }. From the EFZ build code when it decodes,
-- else the stored part list (the magazine type left out of the parts: it comes once, as the empty magazine).
function M.kit(rec)
    local kit = { weapon = rec.type, parts = {}, mag = rec.mag ~= "" and rec.mag or nil }
    local B, C = efz()
    if B and C and rec.code ~= nil and rec.code ~= "" then
        local ok, key, tree = pcall(B.decode, rec.code)
        if ok and type(tree) == "table" then
            local paths = {}
            for path in pairs(tree) do paths[#paths + 1] = path end
            table.sort(paths)
            for _, path in ipairs(paths) do
                local tpl = tree[path]
                local item = C.data and C.data.items and C.data.items[tpl]
                if C.isClip(tpl) then
                    if kit.mag == nil then kit.mag = C.clipType(key, tpl) end
                elseif item and item.pz then
                    kit.parts[#kit.parts + 1] = item.pz
                end
            end
            return kit, "efz"
        end
    end
    for t in string.gmatch(rec.parts or "", "[^,]+") do
        if t ~= kit.mag then kit.parts[#kit.parts + 1] = t end
    end
    return kit, "list"
end

local function bareWeapon(t)
    local w = newItem(t)
    if w == nil then return nil, 0 end
    local K = g("SolKitBare")
    local removed = 0
    if type(K) == "table" and type(K.bare) == "function" then
        removed = K.bare(w)
    else
        removed = 0
        local list = call(w, "getAllWeaponParts")
        removed = tonumber(list ~= nil and call(list, "size") or 0) or 0
        call(w, "clearAllWeaponParts")
        call(w, "setContainsClip", false)
        call(w, "setCurrentAmmoCount", 0)
        call(w, "setRoundChambered", false)
        local md = call(w, "getModData")
        if type(md) == "table" then md.AmmoList = nil end
        local R = g("TWRuntime")
        if type(R) == "table" and type(R.refresh) == "function" then pcall(R.refresh, w, nil) end
    end
    return w, removed
end

local function emptyMag(t)
    local m = newItem(t)
    if m == nil then return nil end
    call(m, "setCurrentAmmoCount", 0)
    local md = call(m, "getModData")
    if type(md) == "table" then md.AmmoList = nil end
    return m
end

local function name(it, t) return tostring(it ~= nil and call(it, "getDisplayName") or t) end

-- The delivery itself. Returns true, summary / false, reason. Flag written only when every weapon came.
function M.deliver(p)
    if not M.on() then return false, "off" end
    p = p or player()
    if p == nil then return false, "no_player" end
    local md = call(p, "getModData")
    if type(md) ~= "table" then return false, "no_moddata" end
    if md[M.FLAG] ~= nil then return false, "done" end
    local S = g("SolSecretLoadout")
    local recs = type(S) == "table" and type(S.loadout) == "function" and S.loadout() or nil
    if type(recs) ~= "table" or #recs == 0 then return false, "no_loadout" end
    local inv = call(p, "getInventory")
    if inv == nil then return false, "no_inventory" end
    local given, missing, lines = 0, {}, {}
    local weapons = 0
    for i, rec in ipairs(recs) do
        local kit, how = M.kit(rec)
        local w, removed = bareWeapon(kit.weapon)
        local got = {}
        if w ~= nil and addTo(inv, w) then
            weapons = weapons + 1; given = given + 1
            got[#got + 1] = "BARE " .. name(w, kit.weapon) .. " [" .. kit.weapon .. "] (" .. removed .. " default part(s) taken off)"
        else missing[#missing + 1] = kit.weapon end
        for _, t in ipairs(kit.parts) do
            local part = newItem(t)
            if part ~= nil and addTo(inv, part) then given = given + 1; got[#got + 1] = name(part, t) .. " [" .. t .. "]"
            else missing[#missing + 1] = t end
        end
        if kit.mag ~= nil then
            local m = emptyMag(kit.mag)
            if m ~= nil and addTo(inv, m) then given = given + 1; got[#got + 1] = "EMPTY " .. name(m, kit.mag) .. " [" .. kit.mag .. "]"
            else missing[#missing + 1] = kit.mag end
        end
        lines[#lines + 1] = "w" .. i .. " (" .. how .. ", " .. #kit.parts .. " parts + magazine): " .. table.concat(got, "; ")
    end
    for _, l in ipairs(lines) do log("delivered " .. l) end
    if #missing > 0 then log("missing " .. table.concat(missing, ",")) end
    if weapons == 0 then return false, "no_weapon" end
    md[M.FLAG] = { v = M.VERSION, at = nowMs(), items = given, missing = #missing }
    local isC = g("isClient")
    if type(isC) == "function" and isC() then call(p, "transmitModData") end
    log("done: " .. given .. " item(s) to " .. tostring(call(p, "getUsername") or "player") .. " (flag " .. M.FLAG .. " set, never again)")
    return true, "given:" .. given .. ";missing=" .. #missing
end

-- Tries after the game starts until it is delivered, already done, off, or out of tries.
local tries, nextAt, ticking = 0, 0, nil
function M.tick()
    local t = nowMs()
    if t < nextAt then return end
    nextAt = t + M.TRY_MS
    tries = tries + 1
    local ok, done, why = pcall(M.deliver)
    local finished = (ok and (done == true or why == "done" or why == "off")) or tries >= M.MAX_TRIES
    if not ok then log("error " .. tostring(done)) end
    if finished and ticking ~= nil and Events and Events.OnTick then
        pcall(Events.OnTick.Remove, ticking)
        ticking = nil
    end
end

function M.install()
    if M._installed then return end
    M._installed = true
    tries, nextAt = 0, 0
    if Events and Events.OnTick then
        ticking = function() pcall(M.tick) end
        Events.OnTick.Add(ticking)
    end
    log("ready v" .. M.VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(M.install) end
return M

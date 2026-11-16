-- SolTwoHandGrip.lua - switch two_hand_grip (2026-11-11, s97). Robustness only.
-- The game picks the pose from the hands (WeaponType.getWeaponType: a ranged weapon is FIREARM only when
-- primary == secondary and isTwoHandWeapon, otherwise HANDGUN), so a rifle in the primary hand alone is drawn one-handed,
-- gripped at the scope (live 10:38). Live: setPrimaryHandItem fires OnEquipPrimary inside the call; a listener threw
-- (game-wide Kahlua callFrame NPE, Gunworks GetBaseStatsWithAttachments), the call came back as an error although the
-- item was already in her hand, and SCNativeActions.equip returned before the second hand was set.
--   G.afterThrow: equip goes on when the item IS in the hand despite the error.
--   G.grip: a two-hander in one hand only is put in both; each set may throw, the hands are read back after.
--   tick: every 2 s, not while she is in a timed action.
-- Switch read at call time. Logs on change only.
SolTwoHandGrip = SolTwoHandGrip or {}
local G = SolTwoHandGrip
G.VERSION = "0.1.0"
G.GRIP_MS = 2000
G.state = G.state or { gripAt = 0, said = nil }
local S = G.state

local function log(m) print("[SolTwoHandGrip] " .. tostring(m)) end
local function g(name) return rawget(_G, name) end
local function nowMs() return getTimestampMs and getTimestampMs() or 0 end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
local function try(o, name, ...)
    if o == nil then return false end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return false end
    return (pcall(f, o, ...)) == true
end
function G.on() local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on("two_hand_grip") == true end
local function name(it) return tostring(call(it, "getFullType") or it) end

function G.isTwoHanded(item)
    if item == nil then return false end
    return call(item, "isTwoHandWeapon") == true or call(item, "isRequiresEquippedBothHands") == true
end

function G.busy(a)
    local Q = g("ISTimedActionQueue")
    if type(Q) == "table" and type(Q.getTimedActionQueue) == "function" then
        local ok, q = pcall(Q.getTimedActionQueue, a)
        if ok and type(q) == "table" and type(q.queue) == "table" and #q.queue > 0 then return true end
    end
    local acts = call(a, "getCharacterActions")
    return acts ~= nil and call(acts, "isEmpty") == false
end

-- a hand set came back with an error: true when the item is in that hand anyway (the listener threw after the set)
function G.afterThrow(a, item, hand)
    if item == nil or not G.on() then return false end
    if call(a, hand == "secondary" and "getSecondaryHandItem" or "getPrimaryHandItem") == item then
        log("an equip listener threw, but " .. name(item) .. " is in her " .. tostring(hand) .. " hand; going on")
        return true
    end
    return false
end

function G.bothHands(a, item)
    if call(a, "getPrimaryHandItem") ~= item then try(a, "setPrimaryHandItem", item) end
    if call(a, "getSecondaryHandItem") ~= item then try(a, "setSecondaryHandItem", item) end
    call(a, "resetEquippedHandsModels")
    return call(a, "getPrimaryHandItem") == item and call(a, "getSecondaryHandItem") == item
end

-- force: also while she is in a timed action
function G.grip(a, why, force)
    if a == nil or not G.on() then return false, "off" end
    local p, s = call(a, "getPrimaryHandItem"), call(a, "getSecondaryHandItem")
    local target
    if p ~= nil and s ~= p and G.isTwoHanded(p) then target = p
    elseif p == nil and s ~= nil and G.isTwoHanded(s) then target = s
    else return false, "fine" end
    if not force and G.busy(a) then return false, "busy" end
    local ok = G.bothHands(a, target)
    local m = (ok and "both hands on " or "could not put both hands on ") .. name(target) .. " (" .. tostring(why) .. ")"
    if m ~= S.said then log(m) end
    S.said = ok and nil or m
    return ok, ok and "gripped" or "failed"
end

function G.tick()
    if not G.on() then return end
    local t = nowMs()
    if t - S.gripAt < G.GRIP_MS then return end
    S.gripAt = t
    local U = g("SolUI")
    local a = type(U) == "table" and type(U.solActor) == "function" and U.solActor() or nil
    if a == nil or call(a, "getVehicle") ~= nil then return end
    G.grip(a, "check", false)
end

if Events and Events.OnTick and not G.hooked then G.hooked = true; Events.OnTick.Add(function() pcall(G.tick) end) end
log("ready v" .. G.VERSION)
return G

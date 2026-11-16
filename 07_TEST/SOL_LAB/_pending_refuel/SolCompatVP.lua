-- SolCompatVP.lua - switch compat_vp_harvest. A compat guard for Viewpoint's interaction gather; their files are not touched.
--   Live 2026-11-10 23:05:59 and 23:06:01: Viewpoint (LootMenu.snapshot -> InteractActions.gather -> LootActions.call, from
--   IsoCell.render) builds the vanilla world context menu to read its options (Viewpoint_Interact.lua harvest -> unseen ->
--   ISWorldObjectContextMenu.createMenu). Inside it ISFarmingMenu.getShovel (ISFarmingMenu.lua:134) calls
--   ItemContainer.getFirstEvalRecurse(predicateDigPlow): Java calls back into Lua once per item while the outer Lua->Java call
--   still holds a pooled MethodArguments. When it came back, that MethodArguments had already been recycled (returnValues = nil),
--   so LuaJavaInvoker.call (line 185) handed null to ReturnValues.put (line 61): "Cannot assign field callFrame because a is null".
--   The pools (MethodArguments.Pools, ReturnValues.Pool) are static, unsynchronised ArrayLists; one object can only be handed out
--   twice when something released it twice or used Kahlua from another thread. No Sol code touches those pools.
-- With the switch on:
--   1 ISFarmingMenu.getShovel is answered by a plain Lua walk of the hand and the bags (same test as vanilla: not broken and
--     tagged DIG_PLOW), so this menu build no longer holds a Java call open across a Java->Lua callback. Any error -> the vanilla
--     function under pcall -> nil (no Dig option this time) instead of an exception.
--   2 ProjectViewpointQOL.isKnownHarvestError also knows this error (callFrame / ReturnValues), so their own guard counts the gather
--     as "nothing gathered" and Viewpoint gathers again on the next look instead of raising it.
-- Switch off: the vanilla getShovel is called directly and their error filter answers alone.
SolCompatVP = SolCompatVP or {}
local M = SolCompatVP
M.VERSION = "0.1.0"
M.MAX_ITEMS = 4000           -- a walk of the bags never looks at more items than this (then the vanilla call)
M.stats = M.stats or { scans = 0, found = 0, fallbacks = 0, errors = 0, vpKnown = 0 }

local function g(name) return rawget(_G, name) end
local function log(m) print("[SolCompatVP] " .. tostring(m)) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, r = pcall(f, o, ...)
    if ok then return r end
    return nil
end
function M.on()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("compat_vp_harvest") == true
end

local function digTag()
    local T = g("ItemTag")
    if T == nil then return nil end
    local ok, v = pcall(function() return T.DIG_PLOW end)
    if ok then return v end
    return nil
end
local function fits(item, tag)
    if item == nil then return false end
    if call(item, "isBroken") == true then return false end
    return call(item, "hasTag", tag) == true
end
local function isBag(item)
    local f = g("instanceof")
    if type(f) ~= "function" then return false end
    local ok, yes = pcall(f, item, "InventoryContainer")
    return ok and yes == true
end
-- the hand first, then her own items, then the bags inside, breadth first. Returns item | nil, and a reason when it gave up.
function M.findDigPlow(player)
    local tag = digTag()
    if tag == nil then return nil, "no_tag" end
    local hand = call(player, "getPrimaryHandItem")
    if hand ~= nil and fits(hand, tag) then return hand end
    local inv = call(player, "getInventory")
    if inv == nil then return nil, "no_inventory" end
    local queue, qi, seen = { inv }, 1, 0
    while queue[qi] ~= nil do
        local c = queue[qi]
        qi = qi + 1
        local items = call(c, "getItems")
        local n = tonumber((call(items, "size"))) or 0
        for i = 0, n - 1 do
            local it = call(items, "get", i)
            if it ~= nil then
                seen = seen + 1
                if seen > M.MAX_ITEMS then return nil, "too_many" end
                if fits(it, tag) then return it end
                if isBag(it) then
                    local sub = call(it, "getInventory")
                    if sub ~= nil then queue[#queue + 1] = sub end
                end
            end
        end
    end
    return nil
end

local warned = {}
local function once(key, m) if not warned[key] then warned[key] = true; log(m) end end
function M.getShovel(player)
    local orig = M._orig
    if not M.on() then return orig(player) end
    M.stats.scans = M.stats.scans + 1
    local ok, item, why = pcall(M.findDigPlow, player)
    if ok and why == nil then
        if item ~= nil then M.stats.found = M.stats.found + 1 end
        return item
    end
    M.stats.fallbacks = M.stats.fallbacks + 1
    once("fallback", "getShovel: the bag walk gave up (" .. tostring(ok and why or item) .. "), the vanilla call under pcall")
    local ok2, item2 = pcall(orig, player)
    if ok2 then return item2 end
    M.stats.errors = M.stats.errors + 1
    once("error", "getShovel: the vanilla call failed too (" .. tostring(item2) .. "): no Dig option this time")
    return nil
end

function M.installShovel()
    local F = g("ISFarmingMenu")
    if type(F) ~= "table" or type(F.getShovel) ~= "function" then return false end
    if F.getShovel == M.getShovel then return true end
    M._orig = F.getShovel
    F.getShovel = M.getShovel
    return true
end

local function knownText(err)
    local msg = tostring(err or "")
    return string.find(msg, "callFrame", 1, true) ~= nil or string.find(msg, "ReturnValues", 1, true) ~= nil
end
M.knownText = knownText
function M.installKnown()
    local Q = g("ProjectViewpointQOL")
    if type(Q) ~= "table" or type(Q.isKnownHarvestError) ~= "function" then return false end
    if Q._solCompatVP then return true end
    local base = Q.isKnownHarvestError
    Q._solCompatVP = true
    Q.isKnownHarvestError = function(err)
        local okB, known = pcall(base, err)
        if okB and known then return known end
        if M.on() and knownText(err) then
            M.stats.vpKnown = M.stats.vpKnown + 1
            once("known", "a Viewpoint gather hit the Kahlua callFrame error: counted as nothing gathered (" .. M.stats.vpKnown .. ")")
            return true
        end
        if okB then return known end
        return false
    end
    return true
end

function M.install()
    local s = M.installShovel()
    local k = M.installKnown()
    if not M._logged then
        M._logged = true
        log("ready v" .. M.VERSION .. " (switch compat_vp_harvest=" .. tostring(M.on()) .. ", getShovel " .. (s and "wrapped" or "absent")
            .. ", Viewpoint QOL filter " .. (k and "wrapped" or "absent") .. ")")
    end
end
pcall(function() require "Farming/ISUI/ISFarmingMenu" end)
if Events and Events.OnGameStart then Events.OnGameStart.Add(function() pcall(M.install) end) end
return M

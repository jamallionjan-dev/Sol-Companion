-- SolFarmNight.lua - switch farm_night (Jamal 2026-11-10: "she farms at night too, always").
-- At night Sol keeps farming outdoors (on his order and as keeper). She carries a light: a flashlight or lantern from her bag, or one
-- she fetches once from a home container. Any item the game can switch on and that gives light counts (InventoryItem.canBeActivated
-- and getLightStrength > 0; e.g. Base.HandTorch, Base.Flashlight_Crafted, Base.Lantern_CraftedElectric). Zombies: the farm runner's
-- own danger check already pauses her and resumes when clear. No light anywhere: she still works and says so once.
SolUI = SolUI or {}
local U = SolUI
SolFarmNight = SolFarmNight or {}
local N = SolFarmNight
N.VERSION = "0.1.0"
N.FETCH_MS = 45000

local function g(name) return rawget(_G, name) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
local function on() local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on("farm_night") == true end
local function nowMs() return getTimestampMs and getTimestampMs() or 0 end
local function log(m) print("[SolFarmNight] " .. tostring(m)) end
local function LF() local sc = g("SurvivorCompanion"); return type(sc) == "table" and sc or nil end
local function GU() local sc = LF(); return sc and type(sc.GameplayUtil) == "table" and sc.GameplayUtil or nil end
local function list(jl) local out = {}; local n = jl and call(jl, "size") or 0; for i = 0, (n or 0) - 1 do out[#out + 1] = call(jl, "get", i) end; return out end

N.state = N.state or { saidNoLight = false, fetch = nil }
local S = N.state

function N.isLight(item)
    if item == nil or call(item, "canBeActivated") ~= true then return false end
    if (tonumber((call(item, "getLightStrength"))) or 0) <= 0 then return false end
    local uses = call(item, "getCurrentUsesFloat")
    if uses ~= nil and (tonumber(uses) or 0) <= 0 then return false end     -- an empty battery or no fuel
    return true
end

local function itemsOf(cont, deep)
    local gu = GU()
    if gu and type(gu.inventoryItemsDeep) == "function" then
        local ok, items = pcall(gu.inventoryItemsDeep, cont, 180, deep and 12 or 1)
        if ok and type(items) == "table" then return items end
    end
    return list(call(cont, "getItems"))
end

function N.held(a)
    for _, f in ipairs({ "getSecondaryHandItem", "getPrimaryHandItem" }) do
        local it = call(a, f)
        if N.isLight(it) then return it end
    end
    return nil
end

function N.bagLight(a)
    for _, it in ipairs(itemsOf(call(a, "getInventory"), true)) do if N.isLight(it) then return it end end
    return nil
end

local function placeContainer(p)
    local gu = GU()
    local sq = gu and type(gu.gridSquare) == "function" and gu.gridSquare(p.x, p.y, p.z) or nil
    local obj = sq and call(call(sq, "getObjects"), "get", p.oi)
    return obj and call(obj, "getContainerByIndex", p.ci or 0) or nil, sq
end

function N.homeLight()
    local last = type(U.invLast) == "function" and U.invLast() or nil
    for _, p in ipairs(last and last.places or {}) do
        local cont, sq = placeContainer(p)
        if cont then for _, it in ipairs(itemsOf(cont, false)) do if N.isLight(it) then return { cont = cont, sq = sq, item = it } end end end
    end
    return nil
end

-- put it in her off hand and switch it on; returns true when she has a working light in hand
function N.wield(a, item)
    local gu = GU()
    local inv = call(a, "getInventory")
    if call(item, "getContainer") ~= inv and gu and type(gu.transferItemVerified) == "function" then
        if gu.transferItemVerified(call(item, "getContainer"), inv, item) ~= true then return false end
    end
    if call(a, "getPrimaryHandItem") ~= item then pcall(function() a:setSecondaryHandItem(item) end) end
    if call(item, "isActivated") ~= true then pcall(function() item:setActivated(true) end) end
    return call(item, "isActivated") == true
end

local function say(text)
    local gu = GU()
    local a = type(U.solActor) == "function" and U.solActor() or nil
    if gu and type(gu.say) == "function" and a then pcall(gu.say, a, text) end
    log("say " .. text)
end

-- called by the farm runner while it is night and she works outdoors; never blocks the work
function N.ensure(a, night)
    if not on() or a == nil then return "off" end
    if not night then S.saidNoLight = false; S.fetch = nil; return "day" end
    if N.held(a) then local it = N.held(a); if call(it, "isActivated") ~= true then pcall(function() it:setActivated(true) end) end return "ready" end
    local bag = N.bagLight(a)
    if bag then N.wield(a, bag); return "ready" end
    local f = S.fetch
    if f == nil then
        local home = N.homeLight()
        if home == nil then
            if not S.saidNoLight then S.saidNoLight = true; say("\217\133\216\167\32\217\133\216\185\217\138\32\216\182\217\136\216\140\32\216\168\216\179\32\216\177\216\173\32\217\131\217\133\217\145\217\132\32\216\180\216\186\217\132\46") end
            return "none"
        end
        S.fetch = { home = home, at = nowMs() }
        if type(U.solGoto) == "function" then pcall(U.solGoto, call(home.sq, "getX"), call(home.sq, "getY"), call(home.sq, "getZ")) end
        return "fetching"
    end
    if nowMs() - f.at > N.FETCH_MS then S.fetch = nil; S.saidNoLight = true; return "none" end         -- could not get there: work without
    local ax, ay = call(a, "getX"), call(a, "getY")
    local sx, sy = call(f.home.sq, "getX"), call(f.home.sq, "getY")
    if ax and sx and math.max(math.abs(ax - sx), math.abs(ay - sy)) <= 1.6 then
        if N.wield(a, f.home.item) then log("took a light from home") end
        S.fetch = nil
        return "ready"
    end
    return "fetching"
end

return N

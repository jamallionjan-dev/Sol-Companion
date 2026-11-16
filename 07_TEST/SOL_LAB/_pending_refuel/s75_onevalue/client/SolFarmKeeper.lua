-- SolFarmKeeper.lua - the two standing orders: look after the farm while he is away, and stay home and rest. Her own needs come first.
--   Living Fellows already treats wounds, eats and drinks on its own ("medical" and "needs" decisions, which instinct_only keeps), and washes and
--   sleeps as "downtime", which instinct_only drops. While a standing order holds, SolAuthority lets downtime run (apply_s22_lua.py).
--   None of it involves Living Fellows' base roles: SolFarmWork keeps her from being pulled away while she is on the farm.
--   She changes her clothes here, because Living Fellows has no such thing: only what she wears changes, her body and skin are never touched.
SolUI = SolUI or {}
local U = SolUI
SolFarmKeeper = SolFarmKeeper or {}
local K = SolFarmKeeper
K.VERSION = "0.1.0"
local DIRTY, WET, CLOTHES_EVERY_MS, HOLD_MS, QUIET_MS, TIRED, HUNGRY, THIRSTY = 25, 40, 20000, 240000, 1800000, 0.7, 0.55, 0.48

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
local function tcall(f, ...) if type(f) ~= "function" then return nil end local ok, a = pcall(f, ...); if ok then return a end return nil end
local function LF() local sc = g("SurvivorCompanion"); if type(sc) == "table" then return sc end return nil end
local function GU() local sc = LF(); return sc and type(sc.GameplayUtil) == "table" and sc.GameplayUtil or nil end
local function W() return g("SolFarmWork") end
local function stat(a, name)
    local gu = GU()
    if gu and type(gu.characterStatValue) == "function" then return tonumber((tcall(gu.characterStatValue, a, name, 0))) or 0 end
    return 0
end

-- clothes: what she is wearing that is dirty or wet
local function wornList(a)
    local worn = call(a, "getWornItems")
    local n = worn and tonumber((call(worn, "size"))) or 0
    local out = {}
    for i = 0, n - 1 do
        local w = call(worn, "get", i)
        local item = call(w, "getItem")
        if item ~= nil then out[#out + 1] = { item = item, loc = call(w, "getLocation") } end
    end
    return out
end
local function fouled(item)
    return (tonumber((call(item, "getDirtiness"))) or 0) >= DIRTY or (tonumber((call(item, "getWetness"))) or 0) >= WET
end
function K.hygieneDue(a)
    for _, row in ipairs(wornList(a)) do if fouled(row.item) then return true end end
    return false
end
-- a clean dry piece for the same body location, from her bag
local function findPiece(a, loc, wornSet)
    local gu = GU()
    local inv = gu and tcall(gu.inventory, a) or nil
    local function fits(item)
        return not wornSet[item] and call(item, "getBodyLocation") == loc and (tonumber((call(item, "getDirtiness"))) or 0) < 10 and (tonumber((call(item, "getWetness"))) or 0) < 10
    end
    for _, item in ipairs(inv and (tcall(gu.inventoryItemsDeep, inv, 180, 12) or {}) or {}) do
        if fits(item) then return item end
    end
    return nil
end
function K.changeClothes(a)
    local rows = wornList(a)
    local wornSet = {}
    for _, r in ipairs(rows) do wornSet[r.item] = true end
    local changed = 0
    for _, r in ipairs(rows) do
        if fouled(r.item) and r.loc ~= nil then
            local piece = findPiece(a, r.loc, wornSet)
            if piece ~= nil then
                local okW = pcall(function() return a:setWornItem(r.loc, piece) end)
                if okW then changed = changed + 1; wornSet[piece] = true end
            end
        end
    end
    if changed > 0 then call(a, "resetModelNextFrame") end
    return changed
end

-- what her body asks for right now, in order: health, then food and drink, then hygiene and rest. Nil: she is fit for work.
function K.bodyNeed(a)
    local sc = LF()
    local med = sc and sc.Medical
    local wounded = false
    if med and type(med.assessCached) == "function" then
        local ass = tcall(med.assessCached, a, nil, 2000)
        if type(ass) == "table" then
            if (tonumber(ass.bleedingCount) or 0) > 0 then return "health" end                        -- bleeding is never waited out
            wounded = (tonumber(ass.openWounds) or 0) > 0 or (tonumber(ass.dirtyBandages) or 0) > 0
        end
    end
    local now = nowMs()
    if K._quietUntil and now < K._quietUntil then return nil end
    local need = nil
    if wounded then need = "health"
    elseif stat(a, "HUNGER") >= HUNGRY or stat(a, "THIRST") >= THIRSTY then need = "food"
    elseif K.hygieneDue(a) then need = "hygiene"
    elseif stat(a, "FATIGUE") >= TIRED then need = "rest" end
    if need == nil then K._needSince = nil; return nil end
    K._needSince = K._needSince or now
    if now - K._needSince > HOLD_MS then K._quietUntil, K._needSince = now + QUIET_MS, nil; return nil end       -- nothing to eat, no water or bed in reach: not held off work for ever
    return need
end

-- Asked by SolAuthority and SCDecision: should her downtime (washing, sleeping) win over waiting for work?
function K.restWanted(a)
    local m = W() and W().store() or nil
    if m == nil or (m.modes.farm ~= true and m.modes.home ~= true) then return false end
    if m.modes.home == true and m.modes.farm ~= true then return m.atHome == true end        -- resting is at home, not on the road
    local need = K.bodyNeed(a)
    return need == "hygiene" or need == "rest"
end

function K.set(mode, a, m)
    local work = W()
    if mode == "home" and SolFarmView.homePoint() == nil then return false, "no_home" end
    local before = m.modes[mode]     -- the other standing order is kept: they combine
    m.modes[mode] = true
    local ok, why = work.enterDuty(a, m, mode == "home" and m.modes.farm ~= true)
    if not ok then m.modes[mode] = before; return false, why end
    if mode == "home" then m.atHome = m.modes.farm ~= true and work.atHome(a, m) or nil end
    local going = m.modes.home == true and m.modes.farm ~= true and m.atHome ~= true
    return true, "mode:" .. mode .. ":" .. (m.modes.farm and "farm" or "") .. (m.modes.home and "home" or "") .. (going and ":going" or "")
end

local lastClothes = 0
function K.tick(a, m)
    local now = nowMs()
    if now - lastClothes < CLOTHES_EVERY_MS then return end
    lastClothes = now
    if m.modes.farm == true or m.modes.home == true then
        local need = K.bodyNeed(a)
        if need == "hygiene" or need == nil then K.changeClothes(a) end
    end
end
function K.onStop() end
return K

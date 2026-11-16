-- SolCarry.lua - Sol's carrying capacity (default 200 kg), measured and applied on the game's real numbers.
-- The game rejects an item that does not fit (ItemContainer:hasRoomFor), and the carry bar compares the load with the container's
-- capacity, so BOTH numbers must reach the target: the character's maximum (getMaxWeight, what Living Fellows reads) and the
-- inventory container's own capacity (getCapacity / getEffectiveCapacity). v0.1 only raised the first one, so the bar stayed at 50.
-- Every value is READ BACK from the game and "applied" is reported only when the game itself returns the target.
-- Verbs (through the SolAct_Request channel):
--   sol_carry_stats        read-only: max / base / container capacity / effective capacity / load / which setters exist
--   sol_carry_set [kg]     change the target (kept in the save) and apply it now
--   sol_carry_probe        measures what the container's capacity really does: sets 150, 100, 99 and 120 and reads each back, then re-reads
--                          after three seconds (a hard limit, or does the game put its own number back?), then applies the target again
-- Debug mode stops the game on any error, even a caught one, so a method is called only when it exists, and a value is never
-- guessed more than three times.
SolUI = SolUI or {}
local U = SolUI
U.CARRY_VERSION = "0.3.0"
local DEFAULT_KG = 200
local MAX_TRY_VALUE = 800
local function log(m) print("[SolCarry] " .. tostring(m)) end

local function num(v) if type(v) == "number" and v == v then return v end return nil end
local function has(o, name) return o ~= nil and type(o[name]) == "function" end
local function call(o, name, ...)
    if o == nil then return nil end
    local f = o[name]
    if type(f) ~= "function" then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function fmt(v) v = num(v); if not v then return "?" end return tostring(math.floor(v * 10 + 0.5) / 10) end
local function sol() return type(U.solActor) == "function" and U.solActor() or nil end

-- the target: the default unless the player set one with sol_carry_set (an old stored default is ignored)
local function target()
    if ModData and ModData.getOrCreate then
        local d = ModData.getOrCreate("SolCarry")
        if type(d) == "table" and d.userSet == true and num(d.target) and d.target > 0 then return d.target end
    end
    return DEFAULT_KG
end

local function readings(s)
    local inv = call(s, "getInventory")
    return {
        max = num(call(s, "getMaxWeight")),
        base = num(call(s, "getMaxWeightBase")),
        cap = inv and num(call(inv, "getCapacity")) or nil,
        eff = inv and num(call(inv, "getEffectiveCapacity", s)) or nil,
        load = inv and num(call(inv, "getCapacityWeight")) or nil,
    }
end
local function show(r)
    return "max=" .. fmt(r.max) .. " base=" .. fmt(r.base) .. " cap=" .. fmt(r.cap) .. " eff=" .. fmt(r.eff) .. " load=" .. fmt(r.load)
end
-- what the game compares a load with: the container's effective capacity, else its capacity, else the character's maximum
local function usable(r) return r.eff or r.cap or r.max end

function U.carryStats()
    local s = sol()
    if s == nil then return nil, "no_sol" end
    local inv = call(s, "getInventory")
    local setters = {}
    for _, name in ipairs({ "setMaxWeightBase", "setMaxWeight" }) do
        if has(s, name) then setters[#setters + 1] = name end
    end
    if has(inv, "setCapacity") then setters[#setters + 1] = "setCapacity" end
    return true, "carry " .. show(readings(s)) .. " unlimited=" .. tostring(call(s, "isUnlimitedCarry")) .. " target=" .. fmt(target())
        .. " setters=" .. (#setters > 0 and table.concat(setters, ",") or "none")
end

local st = { tries = 0, lastAttempt = nil, lastBefore = nil }

-- raise both numbers to `wanted` and read them back
function U.carryApply(wanted)
    local s = sol()
    if s == nil then return false, "no_sol" end
    local want = math.floor(num(wanted) or target())
    local r = readings(s)
    if (r.max or 0) >= want and (usable(r) or 0) >= want then
        st.tries, st.lastAttempt, st.lastBefore = 0, nil, nil
        return true, "already " .. show(r)
    end
    local note = ""
    -- 1) the character's maximum
    if (r.max or 0) < want then
        local setter = has(s, "setMaxWeightBase") and "setMaxWeightBase" or (has(s, "setMaxWeight") and "setMaxWeight" or nil)
        if not setter then
            note = " no_max_setter"
        elseif st.tries >= 3 then
            note = " max_gave_up"
        else
            local attempt = want
            if st.lastAttempt and r.max and r.max > 0 then
                if r.max ~= st.lastBefore then attempt = math.ceil(st.lastAttempt * want / r.max) + 1     -- the game scales what we give it
                else attempt = st.lastAttempt end                                                          -- a stale read: same value again
            end
            if attempt > MAX_TRY_VALUE then attempt = MAX_TRY_VALUE end
            st.lastBefore, st.lastAttempt, st.tries = r.max, attempt, st.tries + 1
            call(s, setter, attempt)
        end
    end
    -- 2) the container's own capacity: what the carry bar and hasRoomFor compare against
    local inv = call(s, "getInventory")
    if has(inv, "setCapacity") then
        local limit = math.min(want, 100)                                       -- the game refuses more than 100, and writes a warning each time it is asked
        local nowR = readings(s)
        if (usable(nowR) or 0) < want and (nowR.cap or 0) < limit then call(inv, "setCapacity", limit) end
    else
        note = note .. " no_capacity_setter"
    end
    r = readings(s)
    local ok = (r.max or 0) >= want and (usable(r) or 0) >= math.min(want, 100)
    if ok then st.tries, st.lastAttempt, st.lastBefore = 0, nil, nil end
    return ok, (ok and "applied " or "not_yet ") .. show(r) .. note
end

function U.carryProbe()
    local s = sol()
    if s == nil then return nil, "no_sol" end
    local inv = call(s, "getInventory")
    if not has(inv, "setCapacity") then return false, "no_capacity_setter" end
    local out = {}
    for _, v in ipairs({ 150, 100, 99, 120 }) do
        call(inv, "setCapacity", v)
        local r = readings(s)
        out[#out + 1] = "set" .. v .. "->cap" .. fmt(r.cap) .. "/eff" .. fmt(r.eff)
    end
    U._carryProbeAt = (getTimestampMs and getTimestampMs() or 0) + 3000
    U.carryApply()
    return true, "probe " .. table.concat(out, " ") .. " | a re-read follows in the log after 3 s"
end

function U.carrySet(option)
    local n = num(tonumber(option))
    if option ~= nil and tostring(option) ~= "" then
        if not n or n < 1 or n > 1000 then return false, "bad_value" end
        if ModData and ModData.getOrCreate then
            local d = ModData.getOrCreate("SolCarry")
            if type(d) == "table" then d.target = math.floor(n); d.userSet = true end
        end
        st.tries, st.lastAttempt, st.lastBefore = 0, nil, nil
    end
    local ok, why = U.carryApply()
    return ok, "target=" .. fmt(target()) .. " " .. tostring(why)
end

-- keep it applied: the actor can be re-created when a save is loaded and the game may recompute the numbers, so check every ten seconds
local lastCheck, backoffUntil, lastLogged = 0, 0, ""
local function onTick()
    local t = getTimestampMs and getTimestampMs() or 0
    if U._carryProbeAt and t >= U._carryProbeAt then
        U._carryProbeAt = nil
        local ps = sol()
        if ps then log("probe re-read after 3 s: " .. show(readings(ps))) end
    end
    if t - lastCheck < 10000 then return end
    lastCheck = t
    if t < backoffUntil then return end
    local s = sol()
    if s == nil then return end
    local r = readings(s)
    if (r.max or 0) >= target() and (usable(r) or 0) >= target() then return end
    local ok, why = U.carryApply()
    if why ~= lastLogged then log((ok and "applied: " or "not yet: ") .. why); lastLogged = why end
    if not ok and st.tries >= 3 then backoffUntil = t + 300000 end
end

local function install()
    if U._carryInstalled then return end
    U._carryInstalled = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "sol_carry_stats" then
            local ok, a, b = pcall(U.carryStats)
            if not ok then return false, "carry_error" end
            return a, b
        elseif id == "sol_carry_probe" then
            local ok, a, b = pcall(U.carryProbe)
            if not ok then return false, "carry_error" end
            return a, b
        elseif id == "sol_carry_set" then
            local ok, a, b = pcall(U.carrySet, option)
            if not ok then return false, "carry_error" end
            return a, b
        end
        return base(id, option)
    end
    if Events and Events.OnTick then Events.OnTick.Add(onTick) end
    log("verbs installed v" .. U.CARRY_VERSION)
end
U._carryOnTick = onTick
if Events and Events.OnGameStart then Events.OnGameStart.Add(install) end
log("ready v" .. U.CARRY_VERSION)

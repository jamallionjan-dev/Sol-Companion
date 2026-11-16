-- SolExitFirst.lua - switch exit_first (s85). An on-foot order (rest at home, farm work, sort, chickens, walk somewhere...) given
-- while Sol sits in a car: she gets out first by herself, then does it. Live 2026-11-10 21:32:36 "rest at home" from the car was
-- refused (SolFarmWork.enterDuty -> in_vehicle). Order of things:
--   she drives and the car moves (or a GPS drive is under way): the drive is stopped (SolUI.gpsStop -> LF Driving.stop), she waits
--     until the car stands, then gets out;
--   he drives and the car moves: she waits until it stands (never out of a moving car);
--   the car stands: engine off when she is the driver, then out (SolOrders.leaveCar, the same exit as the exit_car order);
--   out + a short settle (SolOrders sends her back to following once she is out; the order must come after that), then the order
--   runs through the normal SolUI.runAction chain.
-- The answer to the order is at once "leaving_car_first" / "stopping_car_first" / "waiting_car_stop" (ok); the order's own result
-- is kept for the Mind: verb sol_exit_first status -> "pending" | "done:<true|false>:<reason>" (once) | "idle".
-- A newer movement order from him (follow, stay, board, drive...) drops the waiting order.
require "SolActions"
SolUI = SolUI or {}
local U = SolUI
SolExitFirst = SolExitFirst or {}
local M = SolExitFirst
M.VERSION = "0.1.0"
M.TICK_MS = 250
M.STOP_MS = 15000          -- her own drive: the car must stand within this
M.WAIT_MS = 120000         -- his drive: she waits this long for him to stop
M.EXIT_MS = 15000          -- getting out
M.SETTLE_MS = 2000         -- after she is out, before the order
M.STANDING_KMH = 1.0

-- order id -> true (every option) or { first word of the option = true }
M.ON_FOOT = {
    sol_farm = { keeper = true, home = true, both = true, water = true, harvest = true, plant = true, cure = true, compost = true, weed = true, plow = true },
    sol_farm_try = true, sol_animals = { care = true, eggs = true }, sol_sort = { run = true }, sol_role = true,
    sol_goto = true, sol_go_inside = true, sol_fetch = true, guard = true,
}
M.DROP_ON = { follow = true, stay = true, regroup = true, retreat = true, board_vehicle = true, sol_drive = true, sol_take_wheel = true,
    sol_sit_beside = true, sol_forget = true, cautious_follow = true }

local function g(name) return rawget(_G, name) end
local function nowMs() local f = g("getTimestampMs"); if f then return f() end; return os.time() * 1000 end
local function log(m) print("[SolExitFirst] " .. tostring(m)) end
local function vcall(o, name, ...)
    if o == nil then return nil end
    local f = o[name]
    if f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function switchOn()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("exit_first") == true
end
local function solActor() if type(U.solActor) == "function" then return U.solActor() end; return nil end
local function kmh(veh)
    local v = tonumber((vcall(veh, "getCurrentSpeedKmHour")))
    if v == nil then return 0 end
    return math.abs(v)
end
local function gpsDriving()
    local G = type(U.gps) == "table" and U.gps or nil
    return G ~= nil and G.lastResult == "driving"
end

function M.onFoot(id, option)
    local want = M.ON_FOOT[tostring(id)]
    if want == true then return true end
    if type(want) ~= "table" then return false end
    local word = string.match(tostring(option or ""), "^(%w+)") or ""
    return want[word] == true
end

M.job = M.job or nil       -- { id, option, phase = stopping | waitstop | exit | settle, at = ms, phaseAt = ms, driver = bool }
M.last = M.last or nil     -- { ok = bool, why = string } until the Mind reads it

local function finish(ok, why)
    local j = M.job
    M.job = nil
    M.last = { ok = ok == true, why = tostring(why or "") }
    log("order " .. tostring(j and j.id) .. " " .. tostring(j and j.option) .. " -> " .. tostring(ok) .. " " .. tostring(why))
end

local function getOut(s, veh)
    if vcall(veh, "getDriver") == s and vcall(veh, "isEngineRunning") == true and type(U.solEngine) == "function" then pcall(U.solEngine, "off") end
    local O = g("SolOrders")
    if type(O) ~= "table" or type(O.leaveCar) ~= "function" then return false end
    local ok = pcall(O.leaveCar)
    return ok
end

local function phase(j, name) j.phase, j.phaseAt = name, nowMs() end

function M.begin(id, option, s, veh)
    local j = { id = id, option = option, at = nowMs(), driver = vcall(veh, "getDriver") == s }
    M.job, M.last = j, nil
    local moving = kmh(veh) > M.STANDING_KMH
    if j.driver and (moving or gpsDriving()) then
        phase(j, "stopping")
        if type(U.gpsStop) == "function" then pcall(U.gpsStop) end
        log(tostring(id) .. ": she drives, the car stops first")
        return true, "stopping_car_first"
    end
    if moving then
        phase(j, "waitstop")
        log(tostring(id) .. ": he drives, she gets out when the car stands")
        return true, "waiting_car_stop"
    end
    phase(j, "exit")
    if not getOut(s, veh) then M.job = nil; return false, "in_vehicle" end
    log(tostring(id) .. " " .. tostring(option) .. ": she gets out of the car first")
    return true, "leaving_car_first"
end

function M.tick()
    local j = M.job
    if j == nil then return end
    if not switchOn() then M.job = nil; return end
    local s = solActor()
    if s == nil then finish(false, "sol_not_available"); return end
    local veh = vcall(s, "getVehicle")
    local t = nowMs()
    if j.phase == "stopping" or j.phase == "waitstop" then
        if veh == nil then phase(j, "settle"); return end
        if kmh(veh) <= M.STANDING_KMH and not (j.phase == "stopping" and gpsDriving()) then
            phase(j, "exit")
            if not getOut(s, veh) then finish(false, "exit_failed") end
            return
        end
        if t - j.phaseAt > (j.phase == "stopping" and M.STOP_MS or M.WAIT_MS) then finish(false, "exit_failed") end
        return
    end
    if j.phase == "exit" then
        if veh == nil then phase(j, "settle"); return end
        if t - j.phaseAt > M.EXIT_MS then finish(false, "exit_failed") end
        return
    end
    if j.phase == "settle" and t - j.phaseAt >= M.SETTLE_MS then
        if veh ~= nil then phase(j, "exit"); getOut(s, veh); return end       -- back in a seat (LF): out again
        M.job = nil
        local okR, ok, why = pcall(U.runAction, j.id, j.option)
        M.job = j
        if not okR then finish(false, "error") else finish(ok, why) end
    end
end

function M.status()
    if M.job ~= nil then return true, "pending" end
    local l = M.last
    if l == nil then return true, "idle" end
    M.last = nil
    return true, "done:" .. tostring(l.ok) .. ":" .. l.why
end

function M.wrap()
    if M._wrapped then return end
    M._wrapped = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "sol_exit_first" then return M.status() end
        if not switchOn() then return base(id, option) end
        if M.job ~= nil and M.DROP_ON[tostring(id)] then
            log("his newer order " .. tostring(id) .. " drops " .. tostring(M.job.id))
            M.job = nil
        end
        if M.onFoot(id, option) then
            local s = solActor()
            local veh = vcall(s, "getVehicle")
            if veh ~= nil then return M.begin(id, option, s, veh) end
            if M.job ~= nil and M.job.id ~= id then M.job = nil end         -- he gave it again himself, she is out: his order runs
        end
        return base(id, option)
    end
    log("ready v" .. M.VERSION)
end

-- wrapped at the first tick after the game started, so it sits outside every module that wraps SolUI.runAction on OnGameStart
function M.install()
    if M._installed then return end
    M._installed = true
    local function step() if not M._wrapped then M.wrap() end; pcall(M.tick) end
    local budget = g("SolBudget")
    if type(budget) == "table" and type(budget.register) == "function" then
        budget.register("exit_first", step, { everyMs = M.TICK_MS, priority = 4 })
    elseif Events and Events.OnTick then
        local nextAt = 0
        Events.OnTick.Add(function() local t = nowMs(); if t < nextAt then return end; nextAt = t + M.TICK_MS; step() end)
    end
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(M.install) end
return M

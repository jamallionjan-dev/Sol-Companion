-- SolExitEngine.lua - switch exit_engine_off (s91). Jamal's rule: whenever Sol gets out of a car where she is the driver, she turns
-- the engine off first, unless his order said to leave it running (Jamal 2026-11-10, "get out and leave the engine running"). If he drives, she
-- never touches his engine.
-- One place for every exit: SurvivorCompanion.Vehicle.exit (SCVehicle.lua), the native exit every path ends in:
--   SolOrders.leaveCar (the exit_car order, the chat verb exit_vehicle, the right-click menu, follow_exits_car, exit_first s85,
--   refuel from a can), Living Fellows' own exit_vehicle (commands, the native action queue, the "player left the car" policy,
--   regroup from far), SolGPS's seat swap, SolBleedStop, expedition cars, hotwire, oddballs. Wrapped at the first tick.
-- Before her exit (the car standing, the same check the exit itself makes): she is the driver and the engine runs ->
--   SolUI.solEngine("off") (the existing engine-off path), log "engine off before exit"; with the order's option keep_engine
--   -> nothing, log "engine kept on by order". A held horn (s79) is let go as she leaves the seat.
-- keep_engine: the Mind sends exit_vehicle with option keep_engine (its model maps the explicit phrase to exit_car keep_engine);
--   it is remembered for KEEP_MS or until that exit is done, and the order itself runs as before (no option).
-- Headlights: untouched (vanilla BaseVehicle.shutOff -> VehicleEngine.shutOff never calls setHeadlightsOn).
-- Switch off: the old behaviour, the option is dropped.
require "SolActions"
SolUI = SolUI or {}
local U = SolUI
SolExitEngine = SolExitEngine or {}
local M = SolExitEngine
M.VERSION = "0.1.0"
M.TICK_MS = 500
M.KEEP_MS = 20000
M.STANDING_KMH = 0.5
M.EXIT_IDS = { exit_vehicle = true, exit_car = true }

local function g(name) return rawget(_G, name) end
local function nowMs() local f = g("getTimestampMs"); if f then return tonumber((f())) or 0 end; return os.time() * 1000 end
local function log(m) print("[SolExitEngine] " .. tostring(m)) end
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
    return type(A) == "table" and type(A.on) == "function" and A.on("exit_engine_off") == true
end
local function solActor() if type(U.solActor) == "function" then return U.solActor() end; return nil end
local function vehApi()
    local SC = g("SurvivorCompanion")
    if type(SC) == "table" and type(SC.Vehicle) == "table" then return SC.Vehicle end
    return nil
end
local function standing(veh)
    local api = vehApi()
    if api ~= nil and type(api.isStationary) == "function" then
        local ok, still = pcall(api.isStationary, veh)
        if ok then return still == true end
    end
    local v = tonumber((vcall(veh, "getCurrentSpeedKmHour")))
    return v ~= nil and math.abs(v) <= M.STANDING_KMH
end

function M.isKeep(option)
    local o = string.lower(tostring(option or ""))
    return o == "keep_engine" or o == "keep" or o == "engine_on"
end

M.keep = M.keep or nil        -- { at = ms, said = bool } after his explicit "leave it running", until that exit is done
local function keeping()
    local k = M.keep
    if k == nil then return false end
    if nowMs() - (k.at or 0) > M.KEEP_MS then M.keep = nil; return false end
    return true
end

-- before her exit: what happens to the engine. Returns "off" | "kept" | nil (not hers / not running / not standing / switch off)
function M.beforeExit(actor, vehicle)
    if not switchOn() then return nil end
    local s = solActor()
    if s == nil or actor ~= s then return nil end
    local veh = vehicle or vcall(s, "getVehicle")
    if veh == nil or vcall(s, "getVehicle") ~= veh then return nil end
    if vcall(veh, "getDriver") ~= s then return nil end                    -- a passenger never touches his engine
    if vcall(veh, "isEngineRunning") ~= true then return nil end
    if not standing(veh) then return nil end                               -- the exit itself refuses a moving car
    local H = g("SolHornHold")
    if type(H) == "table" and type(H.release) == "function" and type(H.hold) == "table" and H.hold.veh == veh then pcall(H.release, "left_driver_seat") end
    if keeping() then
        if not M.keep.said then M.keep.said = true; log("engine kept on by order") end
        return "kept"
    end
    local ok, done, why
    if type(U.solEngine) == "function" then
        ok, done, why = pcall(U.solEngine, "off")
    else
        ok = pcall(function() veh:shutOff() end); done = ok
    end
    log("engine off before exit -> " .. tostring(ok and done) .. " " .. tostring(why or ""))
    return "off"
end

function M.wrapExit()
    local api = vehApi()
    if api == nil or type(api.exit) ~= "function" then return false end
    if api.exit == M._exitFn then return true end
    local base = api.exit
    M._exitFn = function(actor, vehicle, seat, intent)
        pcall(M.beforeExit, actor, vehicle)
        local a, b, c = base(actor, vehicle, seat, intent)
        if a == true and M.keep ~= nil then
            local s = solActor()
            if s ~= nil and actor == s then M.keep = nil end
        end
        return a, b, c
    end
    api.exit = M._exitFn
    log("exit hook on")
    return true
end

function M.wrapRun()
    if M._runWrapped then return end
    M._runWrapped = true
    local base = U.runAction
    U.runAction = function(id, option)
        if M.EXIT_IDS[tostring(id)] then
            if switchOn() and M.isKeep(option) then
                M.keep = { at = nowMs(), said = false }
                log("exit with the engine left running (his order)")
            else
                M.keep = nil
            end
            if M.isKeep(option) then option = nil end                      -- the order runs as before
        end
        return base(id, option)
    end
end

function M.install()
    if M._installed then return end
    M._installed = true
    local function step()
        if not M._runWrapped then M.wrapRun() end
        pcall(M.wrapExit)
        if M.keep ~= nil then keeping() end
    end
    local budget = g("SolBudget")
    if type(budget) == "table" and type(budget.register) == "function" then
        budget.register("exit_engine_off", step, { everyMs = M.TICK_MS, priority = 4 })
    elseif Events and Events.OnTick then
        local nextAt = 0
        Events.OnTick.Add(function() local t = nowMs(); if t < nextAt then return end; nextAt = t + M.TICK_MS; step() end)
    end
    log("ready v" .. M.VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(M.install) end
return M

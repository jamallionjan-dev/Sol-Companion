-- SolHornHold.lua - switch horn_hold. Sol keeps her hand on the car horn (one long held horn, not repeated beeps) while she drives,
-- until he says stop, or she leaves the driver seat, or the engine stops, or the car is gone, or the safety cap runs out.
-- Sources (game 42.22.2, read-only):
--   BaseVehicle.onHornStart(): soundHornOn = true, and one world sound (radius 150, volume 150) that zombies hear, at the start.
--   BaseVehicle.onHornStop():  soundHornOn = false. BaseVehicle.isHornSounding(): soundHornOn while a listener is within 500.
--   HornSound.update(): plays the horn as a looped sound for as long as isHornSounding() is true; stops it when it turns false.
--   ISVehicleMenu.onKeyStartPressed / onKeyPressed: the vanilla horn key is a hold: onHornStart on press (driver only, battery
--   charge > 0), onHornStop on release. BaseVehicle.exit(): the horn stops when the car is left with no driver.
--   So a held horn is onHornStart once and onHornStop at the end; nothing is repeated.
-- Verb: horn_hold start | stop (the existing sol_horn single beep is untouched). The Mind words every answer.
require "SolActions"
SolUI = SolUI or {}
local U = SolUI
SolHornHold = SolHornHold or {}
local M = SolHornHold
M.VERSION = "0.1.0"
M.CAP_REAL_MS = 300000        -- safety cap: 5 real minutes (Jamal 2026-11-10); a GPS drive ending stops it earlier
M.TICK_MS = 250

local function g(name) return rawget(_G, name) end
local function nowMs() local f = g("getTimestampMs"); if f then return f() end; return os.time() * 1000 end
local function log(m) print("[SolHornHold] " .. tostring(m)) end
-- every game method is looked up before it is called (in debug mode a thrown Java error halts the game)
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
    return type(A) == "table" and type(A.on) == "function" and A.on("horn_hold") == true
end
local function solActor() if type(U.solActor) == "function" then return U.solActor() end; return nil end
local function gameMinutes()
    local gt = g("getGameTime")
    local t = gt and gt() or nil
    local h = vcall(t, "getWorldAgeHours")
    if type(h) == "number" then return h * 60 end
    return nil
end
local function batteryEmpty(veh)
    local part = vcall(veh, "getPartById", "Battery")
    if part == nil then return false end
    local item = vcall(part, "getInventoryItem")
    if item == nil then return true, "no_battery" end
    local charge = vcall(item, "getCurrentUsesFloat")
    if type(charge) == "number" and charge <= 0 then return true, "battery_dead" end
    return false
end
-- the action list goes out again soon, so the Mind knows whether her hand is on the horn
local function catalogSoon()
    local t = nowMs() + 300
    if U._catalogDue == nil or U._catalogDue > t then U._catalogDue = t end
end

M.hold = M.hold or nil       -- { veh = <BaseVehicle>, atMin = game minutes or nil, atMs = ms }

-- true while Sol's GPS drive is under way (SolGPS keeps it in SolUI.gps.lastResult)
local function driving()
    local U = rawget(_G, "SolUI")
    local G = type(U) == "table" and type(U.gps) == "table" and U.gps or nil
    return G ~= nil and G.lastResult == "driving"
end

-- why a held horn has to stop now, or nil while it may go on
function M.stopWhy(h)
    local s = solActor()
    if s == nil or vcall(s, "isDead") == true then return "sol_gone" end
    local veh = h.veh
    if veh == nil or vcall(veh, "isRemovedFromWorld") == true then return "car_gone" end
    if vcall(s, "getVehicle") ~= veh then return "left_car" end
    if vcall(veh, "getDriver") ~= s then return "left_driver_seat" end
    if vcall(veh, "isEngineRunning") ~= true then return "engine_off" end
    if vcall(veh, "isHornSounding") == false then return "horn_released" end
    local empty = batteryEmpty(veh)
    if empty then return "battery" end
    if h.drive and not driving() then return "drive_end" end
    if nowMs() - (h.atMs or 0) >= M.CAP_REAL_MS then return "cap" end
    return nil
end

function M.release(why)
    local h = M.hold
    M.hold = nil
    if h == nil then return false end
    vcall(h.veh, "onHornStop")
    log("horn released: " .. tostring(why))
    catalogSoon()
    return true
end

function M.start()
    local s = solActor()
    if s == nil then return false, "no_sol" end
    local veh = vcall(s, "getVehicle")
    if veh == nil then return false, "not_in_a_car" end
    if vcall(veh, "getDriver") ~= s then return false, "horn_needs_driver_seat" end
    if veh.onHornStart == nil or veh.onHornStop == nil or vcall(veh, "hasHorn") == false then return false, "horn_unavailable" end
    if vcall(veh, "isEngineRunning") ~= true then return false, "horn_engine_off" end
    local empty, why = batteryEmpty(veh)
    if empty then return false, why end
    if M.hold ~= nil then
        if M.hold.veh == veh and M.stopWhy(M.hold) == nil then return true, "horn_held" end
        M.release("restart")
    end
    vcall(veh, "onHornStart")
    M.hold = { veh = veh, atMin = gameMinutes(), atMs = nowMs(), drive = driving() }
    log("horn held")
    catalogSoon()
    return true, "horn_held"
end

function M.stop()
    if M.release("asked") then return true, "horn_released" end
    local s = solActor()
    local veh = vcall(s, "getVehicle")
    local sounding = vcall(veh, "isHornSounding") == true
    if type(U.solHorn) == "function" then pcall(U.solHorn, "stop") elseif veh ~= nil then vcall(veh, "onHornStop") end
    if sounding then return true, "horn_released" end
    return true, "horn_not_held"
end

function M.order(option)
    local o = string.lower(tostring(option or "start"))
    if o == "" or o == "start" or o == "on" or o == "hold" then return M.start() end
    if o == "stop" or o == "off" or o == "release" then return M.stop() end
    return false, "unknown_option"
end

function M.tick()
    local h = M.hold
    if h == nil then
        if not M._swept then                                     -- a horn left held by a save is let go once, when she is back
            local s = solActor()
            if s ~= nil then
                M._swept = true
                local veh = vcall(s, "getVehicle")
                if veh ~= nil and vcall(veh, "getDriver") == s and vcall(veh, "isHornSounding") == true then
                    vcall(veh, "onHornStop")
                    log("a horn left held from before was let go")
                end
            end
        end
        return
    end
    if not switchOn() then M.release("switch_off"); return end
    local why = M.stopWhy(h)
    if why ~= nil then M.release(why) end
end

function M.install()
    if M._installed then return end
    M._installed = true
    local baseRun, baseCat = U.runAction, U.actionCatalog
    U.runAction = function(id, option)
        if id == "horn_hold" and switchOn() then return M.order(option) end
        return baseRun(id, option)
    end
    U.actionCatalog = function()
        local out = baseCat()
        if switchOn() and type(out) == "table" then
            out[#out + 1] = { id = "horn_hold", kind = "sol", enabled = true, state = M.hold and "holding" or "idle",
                              label = "keep her hand on the car horn while she drives, one long held horn; option: start / stop" }
        end
        return out
    end
    local budget = g("SolBudget")
    if type(budget) == "table" and type(budget.register) == "function" then
        budget.register("horn_hold", function() pcall(M.tick) end, { everyMs = M.TICK_MS, priority = 3 })
    elseif Events and Events.OnTick then
        local nextAt = 0
        Events.OnTick.Add(function() local t = nowMs(); if t < nextAt then return end; nextAt = t + M.TICK_MS; pcall(M.tick) end)
    end
    log("ready v" .. M.VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(M.install) end
return M

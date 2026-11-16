-- SPDX-License-Identifier: MIT
-- Companion driving at low speed. The native bridge presses the car's own
-- pedals and wheel every frame (SCCompanionDriver) and stops for anything its
-- lane scan finds ahead. SCVehicle owns getting in and out of the seat.
-- SCDriving owns a supervisor lease while the runtime polls bounded route jobs.
SurvivorCompanion = SurvivorCompanion or {}
local SC = SurvivorCompanion
SC.Driving = SC.Driving or {}
local Driving = SC.Driving
local jobs = {}
local outcomes = setmetatable({}, { __mode = "k" })
local nativeStop

local function finite(value)
    value = tonumber(value)
    if value == nil or value ~= value or value == math.huge or value == -math.huge then return nil end
    return value
end

local function nowMs()
    return SC.GameplayUtil and SC.GameplayUtil.nowMs and SC.GameplayUtil.nowMs()
        or (type(getTimestampMs) == "function" and getTimestampMs() or 0)
end

local function bridge()
    local api = type(_G) == "table" and rawget(_G, "SCBridge") or nil
    if api == nil or SC.Call == nil then return nil end
    return api
end

local function lastFailure(api, fallback)
    local ok, reason = SC.Call.static(api, "getLastFailure")
    if ok and type(reason) == "string" and reason ~= "" then return reason end
    return tostring(fallback or "native driving call failed")
end

local function call(name, ...)
    local api = bridge()
    if api == nil then return false, "driving bridge is unavailable" end
    local ok, accepted = SC.Call.static(api, name, ...)
    if not ok then return false, tostring(accepted) end
    if accepted ~= true then return false, lastFailure(api) end
    return true
end

local function method(object, name, ...)
    if object == nil then return false, nil end
    return SC.Call.method(object, name, ...)
end

local function vehicleOf(actor)
    local ok, vehicle = method(actor, "getVehicle")
    return ok and vehicle or nil
end

-- Native driveStart refuses ownership while the local player is already in the
-- vehicle.  Acquisition therefore happens before the player boards; once native
-- ownership is armed, the local player may ride as a passenger.
local function localPlayerAboard(vehicle)
    if vehicle == nil or type(getSpecificPlayer) ~= "function" then return false end
    local ok, localPlayer = pcall(getSpecificPlayer, 0)
    if not ok or localPlayer == nil then return false end
    local vehicleOk, current = method(localPlayer, "getVehicle")
    return vehicleOk and current == vehicle
end

local function motionAllowed(actor)
    local job = jobs[actor]
    if job and job.managed == true then
        return false, job.parked == true and "drive_requires_release" or "drive_job_active"
    end
    return true
end

function Driving.available()
    local api = bridge()
    if api == nil then return false end
    for _, name in ipairs({ "driveStart", "driveSet", "driveStop", "driveStatus", "scanLane",
        "driveFollow", "driveApproach", "driveTurnAround" }) do
        local ok, callback = pcall(function() return api[name] end)
        if not ok or callback == nil then return false end
    end
    return true
end

-- True when the companion sits in seat zero of its car.
function Driving.isDriver(actor)
    local vehicle = vehicleOf(actor)
    if vehicle == nil then return false end
    local ok, driver = method(vehicle, "getDriver")
    return ok and driver == actor
end

-- The companion carries this car's key. Without one the car starts only when
-- it is hot-wired, has keys in the ignition, or the sandbox allows easy use.
-- the game's own key check looks only at her top level: a key in a bag she carries is moved up, so that check finds it
local function keyInBags(container, keyId, depth)
    local listOk, items = method(container, "getItems")
    local sizeOk, size = method(items, "size")
    if not listOk or not sizeOk or type(size) ~= "number" or depth > 3 then return nil, nil end
    for index = 0, math.min(size, 400) - 1 do
        local gotOk, item = method(items, "get", index)
        local innerOk, inner = false, nil
        if gotOk and item ~= nil then innerOk, inner = method(item, "getInventory") end
        if innerOk and inner ~= nil then
            local foundOk, key = method(inner, "haveThisKeyId", keyId)
            if foundOk and key ~= nil then return inner, key end
            local deeper, deepKey = keyInBags(inner, keyId, depth + 1)
            if deeper ~= nil then return deeper, deepKey end
        end
    end
    return nil, nil
end

-- a key left in the car (glove box, a seat, the trunk) or in one of her bags goes in her pocket when she is told to drive it
local function takeKeyFromCar(actor, vehicle)
    local keyOk, keyId = method(vehicle, "getKeyId")
    local invOk, inventory = method(actor, "getInventory")
    local countOk, count = method(vehicle, "getPartCount")
    if not keyOk or not invOk or inventory == nil or type(keyId) ~= "number" then return false end
    local bag, bagKey = keyInBags(inventory, keyId, 0)
    if bag ~= nil then
        method(bag, "Remove", bagKey)
        method(inventory, "AddItem", bagKey)
        print("[SolDrive] took the key out of her bag")
        return true
    end
    if not countOk or type(count) ~= "number" then return false end
    for index = 0, count - 1 do
        local partOk, part = method(vehicle, "getPartByIndex", index)
        local boxOk, box = false, nil
        if partOk and part ~= nil then boxOk, box = method(part, "getItemContainer") end
        if boxOk and box ~= nil then
            local foundOk, item = method(box, "haveThisKeyId", keyId)
            if foundOk and item ~= nil then
                method(box, "Remove", item)
                method(inventory, "AddItem", item)
                print("[SolDrive] took the key from the car")
                return true
            end
        end
    end
    return false
end

Driving.bringKeyToHand = takeKeyFromCar

function Driving.hasKey(actor, vehicle)
    vehicle = vehicle or vehicleOf(actor)
    local ignitionOk, inIgnition = method(vehicle, "isKeysInIgnition")
    if ignitionOk and inIgnition == true then return true end
    local wiredOk, wired = method(vehicle, "isHotwired")
    if wiredOk and wired == true then return true end
    local keyOk, keyId = method(vehicle, "getKeyId")
    local inventoryOk, inventory = method(actor, "getInventory")
    if not keyOk or not inventoryOk or inventory == nil or type(keyId) ~= "number" then
        return false
    end
    local found, item = method(inventory, "haveThisKeyId", keyId)
    return found and item ~= nil
end

-- Gets into the driver's seat through SCVehicle's verified boarding.
function Driving.takeWheel(actor, vehicle, intent)
    if SC.Vehicle == nil or type(SC.Vehicle.boardDriver) ~= "function" then
        return false, "vehicle boarding is unavailable"
    end
    return SC.Vehicle.boardDriver(actor, vehicle, intent)
end

-- Sol fix (drive_passenger): the native driver refuses to move while a player sits in the car,
-- because driveStart leaves its authorized passenger empty (SCCompanionDriver.beforeVehicleUpdate ->
-- stop "player_aboard"). The bridge also exposes driveStartWithPassenger, which names the player who
-- may ride along; nothing in Lua ever called it, so Sol could never drive the player anywhere.
local function solFixOn(name)
    local A = rawget(_G, "SolAuthority")
    if type(A) ~= "table" or type(A.on) ~= "function" then return false end
    local ok, on = pcall(A.on, name)
    return ok and on == true
end

local function localPlayer()
    if type(getSpecificPlayer) ~= "function" then return nil end
    local ok, p = pcall(getSpecificPlayer, 0)
    if ok then return p end
    return nil
end

local function startNative(job)
    local hasKey = Driving.hasKey(job.actor) == true or takeKeyFromCar(job.actor, job.vehicle)
    local runningOk, running = method(job.vehicle, "isEngineRunning")
    if not hasKey and not (runningOk and running == true) then                   -- no key and the engine is off: nothing can start it, and that is what he should hear
        print("[SolDrive] no key for this car")
        local hw = SC.VehicleHotwire                                             -- no key anywhere: the game's own hotwire job, if her skills allow it
        if type(hw) == "table" and type(hw.canHotwire) == "function" and type(hw.request) == "function" then
            local okC, can = pcall(hw.canHotwire, job.actor)
            if okC and can == true then
                local okH, started, whyH = pcall(hw.request, job.actor, job.vehicle, localPlayer())
                print("[SolDrive] hotwire -> " .. tostring(okH and started) .. " " .. tostring(okH and whyH or started))
                if okH and started == true then
                    Driving.stop(job.actor, "hotwiring")
                    return false, "hotwiring"
                end
            end
        end
        do local FN88 = rawget(_G, "SolFailNote"); if type(FN88) == "table" and type(FN88.keyLine) == "function" then pcall(FN88.keyLine, "drive_start", job.actor, job.vehicle) end end   -- Sol s88: her keys against the car's
        do local FN88 = rawget(_G, "SolFailNote"); if type(FN88) == "table" and type(FN88.note) == "function" then pcall(FN88.note, "drive", "no_key", "") end end
        Driving.stop(job.actor, "no_key")
        return false, "no_key"
    end
    if solFixOn("drive_passenger") then
        local player = localPlayer()
        local api = bridge()
        local exposed = false
        if api ~= nil then
            local okField, field = pcall(function() return api.driveStartWithPassenger end)
            exposed = okField and field ~= nil
        end
        if player ~= nil and exposed then
            local accepted, reason = call("driveStartWithPassenger", job.actor, player, hasKey)
            if accepted then
                job.nativeStarted, job.passengerAuthorized = true, true
                return true
            end
            print("[SolDrive] driveStartWithPassenger refused: " .. tostring(reason) .. " - falling back to driveStart")
        end
    end
    local accepted, reason = call("driveStart", job.actor, hasKey)
    if not accepted then
        print("[SolDrive] driveStart refused: " .. tostring(reason))
        do local FN88 = rawget(_G, "SolFailNote"); if type(FN88) == "table" and type(FN88.bridge) == "function" then pcall(FN88.bridge, "start", reason, job) end end   -- Sol s88: the cause behind bridge_failure
        Driving.stop(job.actor, "bridge_failure")
        local okV, car = pcall(function() return job.actor:getVehicle() end)
        if okV and car ~= nil then                                               -- a running car left behind is taken off the ground by the game when its area unloads
            local okR, running = pcall(function() return car:isEngineRunning() end)
            if okR and running == true then pcall(function() car:shutOff() end) end
        end
        return false, reason
    end
    job.nativeStarted = true
    return true
end

-- Puts the seated driver under bridge control, held still.  The local player
-- must still be outside at this acquisition boundary because the native bridge
-- rejects driveStart while a player occupies the vehicle.
function Driving.start(actor, goal)
    local allowed, why = motionAllowed(actor)
    if not allowed then return false, why end
    if not Driving.isDriver(actor) then return false, "companion is not in the driver's seat" end
    local prior = jobs[actor]
    if prior then
        local supervisor = SC.ActionSupervisor
        if prior.nativeStarted == true and prior.managed ~= true and prior.phase == "waiting"
            and supervisor and type(supervisor.isCurrent) == "function"
            and supervisor.isCurrent(prior.token) then
            return true, "drive_prepared"
        end
        return false, "drive_already_owned"
    end
    -- Sol patch 2026-10-25: player riding as passenger allowed (native driveStart only requires Sol at the wheel)
    local token, beginReason = Driving.begin(actor, goal)
    if not token then return false, beginReason end
    local started, startReason = startNative(jobs[actor])
    if not started then return false, startReason end
    return true, "drive_prepared"
end

-- Cruise at a low speed (km/h, capped natively) with steering in [-1, 1],
-- where -1 is the player's left key. Obstacle braking stays on unless the
-- caller passes false.
function Driving.cruise(actor, kmh, steering, brakeForObstacles)
    local allowed, why = motionAllowed(actor)
    if not allowed then return false, why end
    local speed = tonumber(kmh) or 0
    local steer = tonumber(steering) or 0
    return call("driveSet", actor, steer, speed, brakeForObstacles ~= false)
end

function Driving.hold(actor)
    local allowed, why = motionAllowed(actor)
    if not allowed then return false, why end
    return call("driveSet", actor, 0, 0, true)
end

-- Lets go of the wheel and parks. Safe when not driving.
function Driving.release(actor, reason)
    if not jobs[actor] then return nativeStop(actor) end
    return Driving.stop(actor, reason or "released")
end

-- The expedition road planner's route from where the car stands to a target.
function Driving.planRoute(actor, target)
    if SC.ExpeditionRoute == nil or type(SC.ExpeditionRoute.plan) ~= "function" then
        return nil, "road planner is unavailable"
    end
    return SC.ExpeditionRoute.plan(actor, target, true)
end

-- The bridge's route text, "x,y,width;...", from route points. Bounded.
function Driving.routeText(points)
    if type(points) ~= "table" then return nil, "route has no points" end
    local RF = rawget(_G, "SolRoadFirst")
    if type(RF) == "table" and RF.on() then points = RF.spaced(points) end
    local parts = {}
    for index, point in ipairs(points) do
        if index > 512 then return nil, "route has too many points" end
        local x = type(point) == "table" and tonumber(point.x) or nil
        local y = type(point) == "table" and tonumber(point.y) or nil
        if not x or not y then return nil, "route point " .. index .. " is invalid" end
        parts[#parts + 1] = string.format("%.2f,%.2f,%.1f", x, y, tonumber(point.width) or 0)
    end
    if #parts < 2 then return nil, "route has fewer than two points" end
    return table.concat(parts, ";")
end

local function followNative(actor, route, kmh)
    local points = type(route) == "table" and (route.points or route) or nil
    local text, why = Driving.routeText(points)
    if not text then return false, why end
    local followed, reason = call("driveFollow", actor, text, tonumber(kmh) or 10)
    if not followed then
        local RF = rawget(_G, "SolRoadFirst")
        if type(RF) == "table" then print("[SolDrive] route given: " .. RF.routeDetail(points)) end
    end
    if followed and jobs[actor] then jobs[actor].phase, jobs[actor].result = "following", nil end
    return followed, reason
end

-- Drives a route: the planner's table, or a plain list of {x, y, width}
-- points. The bridge keeps right, slides round wrecks in the lane, stops when
-- the road is blocked edge to edge, and stops at the end.
function Driving.followRoute(actor, route, kmh)
    local allowed, reason = motionAllowed(actor)
    if not allowed then return false, reason end
    return followNative(actor, route, kmh)
end

-- Turns round with a three-point turn; with followBack, drives the route back.
function Driving.turnAround(actor, followBack)
    local allowed, why = motionAllowed(actor)
    if not allowed then return false, why end
    local turned, reason = call("driveTurnAround", actor, followBack == true)
    if turned and jobs[actor] then jobs[actor].phase, jobs[actor].result = "turning", nil end
    return turned, reason
end

function Driving.status(actor)
    local api = bridge()
    if api == nil then return nil, "driving bridge is unavailable" end
    local out = {}
    local ok, accepted = SC.Call.static(api, "driveStatus", actor, out)
    if not ok then return nil, tostring(accepted) end
    if accepted ~= true then return nil, lastFailure(api) end
    return out
end

-- One lane scan for the car the companion sits in, lookAhead tiles past the
-- front bumper. Read-only.
function Driving.scanLane(actor, lookAhead)
    local api = bridge()
    if api == nil then return nil, "driving bridge is unavailable" end
    local out = {}
    local ok, accepted = SC.Call.static(api, "scanLane", actor, tonumber(lookAhead) or 0, out)
    if not ok then return nil, tostring(accepted) end
    if accepted ~= true then return nil, lastFailure(api) end
    return out
end

-- Job results and the seat lease are separate: an arrived/failed car is parked
-- with no pedal held, while its driver remains protected until explicitly released.
local function snapshot(job)
    local circles = {}
    for _, circle in ipairs(job.circles or {}) do
        circles[#circles + 1] = { x = circle.x, y = circle.y, radius = circle.radius }
    end
    local roadGoal = job.roadGoal
    return { phase = job.phase, result = job.result, reason = job.reason, detail = job.detail,
        attempts = job.attempts or 0, circles = circles, parked = job.parked == true,
        roadGoal = roadGoal and { x = roadGoal.x, y = roadGoal.y, z = roadGoal.z } or nil }
end

nativeStop = function(actor, job)
    local api = job and job.api or bridge()
    if not api or not SC.Call then return false, "driving bridge is unavailable" end
    local okay, accepted = SC.Call.static(api, "driveStop", actor)
    if okay and accepted == true then return true end
    if job and job.nativeStarted ~= true then return true, "drive_not_started" end
    return false, okay and lastFailure(api, "drive release rejected") or tostring(accepted)
end

local function forget(actor, job, reason)
    job.phase, job.reason = "released", reason
    job.result = job.result or "interrupted"
    outcomes[actor] = snapshot(job)
    jobs[actor] = nil
end

-- Block only the local player as driver, or a foreign non-companion.
-- The local player may ride as Sol's passenger.
local function playerAboard(vehicle)
    local localPlayer = nil
    if type(getSpecificPlayer) == "function" then
        local ok, value = pcall(getSpecificPlayer, 0)
        if ok then localPlayer = value end
    end
    if localPlayer ~= nil then
        local driverOk, driver = method(vehicle, "getDriver")
        if not driverOk then return true end
        if driver == localPlayer then return true end
    end
    local okay, seats = method(vehicle, "getMaxPassengers")
    if not okay or not finite(seats) then return true end
    for seat = 0, math.min(32, seats) - 1 do
        local called, occupant = method(vehicle, "getCharacter", seat)
        if not called then return true end
        if occupant ~= nil and occupant ~= localPlayer then
            if not SC.Actor or not SC.Actor.isCompanion
                or SC.Actor.isCompanion(occupant) ~= true then return true end
        end
    end
    return false
end

function Driving.begin(actor, goal)
    if not Driving.isDriver(actor) then return nil, "not_driver" end
    local initialStatus, statusReason = Driving.status(actor)
    if not initialStatus then return nil, statusReason or "driving_bridge_unavailable" end
    local x = type(goal) == "table" and finite(goal.x) or nil
    local y = type(goal) == "table" and finite(goal.y) or nil
    if goal ~= nil and (not x or not y
        or x < 0 or x > 30000 or y < 0 or y > 30000 or goal.z ~= 0) then
        return nil, "invalid_drive_goal"
    end
    local prior = jobs[actor]
    if prior then return prior.token, "already_owned" end
    -- Native driveStart rejects a vehicle already occupied by the local player.
    -- Check only before acquiring a fresh lease; a prepared lease remains valid
    -- after the player boards as a passenger.
    if localPlayerAboard(vehicleOf(actor)) and not solFixOn("drive_passenger") then return nil, "player_aboard" end
    local supervisor = SC.ActionSupervisor
    if not supervisor or type(supervisor.begin) ~= "function" then
        return nil, "driving_supervisor_unavailable"
    end
    local job = { actor = actor, vehicle = vehicleOf(actor), api = bridge(),
        nativeStatus = initialStatus, nativeStarted = initialStatus.active == true,
        goal = goal and { x = x, y = y, z = 0 } or nil,
        phase = "waiting", attempts = 0, circles = {} }
    local token, why = supervisor.begin(actor, {
        owner = "drive", action = "drive_route", priority = supervisor.Priority.TRAVEL,
        targetKey = goal and (tostring(goal.x) .. ":" .. tostring(goal.y) .. ":0") or "manual",
        deadlines = { selected = 0, waiting = 0 },
        onCancel = function(_, reason)
            local called, stopped, stopReason = pcall(nativeStop, actor, job)
            if not called or not stopped then
                job.phase, job.reason = "stopping", called and stopReason or stopped
                return false, job.reason
            end
            forget(actor, job, reason or "cancelled")
            return true
        end,
    })
    if not token then
        if supervisor.containsDeferredStatus and supervisor.containsDeferredStatus(why) then
            -- Urgent work took this pulse. Keep its status available to callers
            -- so they can retry without starting a native drive or recording a refusal.
            return nil, "deferred:" .. tostring(why)
        end
        return nil, why
    end
    job.token = token
    jobs[actor], outcomes[actor] = job, nil
    local waiting, transitionReason = supervisor.transition(token, "waiting")
    if not waiting then Driving.stop(actor, "drive_begin_failed") return nil, transitionReason end
    return token, "drive_owned"
end

function Driving.stop(actor, reason)
    local job = jobs[actor]
    if not job then return true, "no_drive" end
    job.releaseReason = reason or "released"
    local supervisor = SC.ActionSupervisor
    if supervisor and supervisor.isCurrent(job.token) then
        return supervisor.cancel(actor, reason or "released", nil, false)
    end
    local stopped, why = nativeStop(actor, job)
    if stopped then forget(actor, job, reason or "released") end
    return stopped, why
end

-- Kahlua keeps weak table keys. Retirement explicitly removes the outcome
-- only after native cleanup succeeds, retaining retry authority on failure.
function Driving.releaseActor(actor, reason)
    if actor == nil then return false, "actor_missing" end
    local stopped, why = Driving.stop(actor, reason or "actor_released")
    if stopped ~= true then return false, why end
    outcomes[actor] = nil
    return true, why
end

-- The gate also services native release events, so Decision cannot retain a stale
-- owner after a player boards or the bridge releases its companion driver.
function Driving.isDriving(actor)
    local job = jobs[actor]
    if not job then return false end
    local supervisor = SC.ActionSupervisor
    local dead = SC.GameplayUtil and SC.GameplayUtil.isDead
        and SC.GameplayUtil.isDead(actor) == true
    local reason = dead and "driver_dead"
        or not Driving.isDriver(actor) and "left_driver_seat"
        -- Player may board after Sol already acquired native drive ownership.
        or (not supervisor or not supervisor.isCurrent(job.token)) and "drive_owner_lost"
    if reason then
        local stopped = Driving.stop(actor, reason)
        return stopped ~= true and jobs[actor] == job
            and supervisor and supervisor.isCurrent(job.token) or false
    end
    local status, why = Driving.status(actor)
    if not status then
        print("[SolDrive] no native status: " .. tostring(why))
        do local FN88 = rawget(_G, "SolFailNote"); if type(FN88) == "table" and type(FN88.bridge) == "function" then pcall(FN88.bridge, "status", why, job) end end   -- Sol s88
        local stopped = Driving.stop(actor, "bridge_failure")
        return stopped ~= true and jobs[actor] == job and supervisor.isCurrent(job.token)
    end
    if job.nativeStarted and status.active ~= true and not job.parked then
        local stopped = Driving.stop(actor, status.reason ~= "" and status.reason or "native_released")
        return stopped ~= true and jobs[actor] == job and supervisor.isCurrent(job.token)
    end
    job.nativeStatus = status
    return true
end

local function parkResult(job, result, reason)
    local stopped, why = nativeStop(job.actor, job)
    if not stopped then
        job.phase, job.reason = "stopping", why
        job.pendingResult, job.pendingReason = result, reason
        return false
    end
    job.phase, job.result, job.reason = result, result, reason or result
    job.parked = true
    job.pendingResult, job.pendingReason = nil, nil
    return true
end

local function reachedGoal(job)
    local xOk, x = method(job.vehicle, "getX")
    local yOk, y = method(job.vehicle, "getY")
    local zOk, z = method(job.vehicle, "getZ")
    x, y, z = finite(x), finite(y), finite(z)
    if not xOk or not yOk or not zOk or not x or not y or not z
        or x < 0 or x > 30000 or y < 0 or y > 30000 then
        return false, "goal_position_unavailable"
    end
    -- The road leg ends at the router's physical road attachment. A driveway
    -- is a separate, checked parking approach owned by SCExpeditionCar.
    local tolerance = job.precise and 1 or 36
    local goal = job.precise and job.goal or job.roadGoal
    if not goal then return false, "road_goal_unavailable" end
    return math.floor(z) == job.goal.z
        and (x - goal.x)^2 + (y - goal.y)^2 <= tolerance,
        "goal_not_reached"
end

-- The original managed lease remains owned while its arrived car is parked.
-- Start a fresh native driver under that lease for one short, clear parking
-- segment. The mission owner checks the entire footprint after arrival.
function Driving.approach(actor, target, seconds)
    local job = jobs[actor]
    if not job or job.managed ~= true or job.parked ~= true
        or job.result ~= "arrived" or not SC.ActionSupervisor
        or not SC.ActionSupervisor.isCurrent(job.token) then
        return false, "parking_requires_arrived_drive"
    end
    local vehicle = vehicleOf(actor)
    local xOk, x = method(vehicle, "getX")
    local yOk, y = method(vehicle, "getY")
    local zOk, z = method(vehicle, "getZ")
    x, y, z = finite(x), finite(y), finite(z)
    local tx = type(target) == "table" and finite(target.x) or nil
    local ty = type(target) == "table" and finite(target.y) or nil
    if not xOk or not yOk or not zOk or not x or not y or z ~= 0
        or not tx or not ty or target.z ~= 0
        or (x - tx)^2 + (y - ty)^2 > 225 then
        return false, "parking_approach_out_of_range"
    end
    local routeText = string.format("%.3f,%.3f,5;%.3f,%.3f,5",
        x, y, tx, ty)
    local started, reason = startNative(job)
    if not started then return false, reason end
    local followed, followReason = call("driveApproach", actor, routeText, 5)
    if not followed then
        Driving.stop(actor, "parking_approach_rejected")
        return false, followReason
    end
    job.goal = { x = tx, y = ty, z = 0 }
    job.precise = true
    job.phase, job.result, job.reason = "approaching", nil, nil
    job.parked = false
    job.approachDeadline = nowMs() + math.min(30000,
        math.max(1000, finite(seconds) or 30000))
    return true
end

local function planJob(job)
    job.bypass, job.steer, job.unstick = nil, nil, nil       -- a fresh plan is never the tail of a detour
    local route, reason
    if not SC.ExpeditionRoute or not SC.ExpeditionRoute.planAvoidingAll then
        return parkResult(job, "failed", "no_route")
    end
    route, reason = SC.ExpeditionRoute.planAvoidingAll(job.actor, job.goal, job.circles)
    if not route then
        job.detail = reason
        return parkResult(job, "failed", "no_route")
    end
    if job.stopShortTiles > 0 and type(route.points) == "table" then
        local last = route.points[#route.points]
        local before = route.points[#route.points - 1]
        if last and before then
            local dx, dy = last.x - before.x, last.y - before.y
            local length = math.sqrt(dx * dx + dy * dy)
            -- Keep the original planner path and its junction choices. Only
            -- shorten a sufficiently long last straight so the car turns
            -- away from roadside poles after the squad walks to the site.
            if length >= job.stopShortTiles + 2 then
                last.x = last.x - dx / length * job.stopShortTiles
                last.y = last.y - dy / length * job.stopShortTiles
                route.roadLength = math.max(0,
                    (tonumber(route.roadLength) or 0) - job.stopShortTiles)
            end
        end
    end
    local endpoint = route.points and route.points[#route.points]
    local roadX = type(endpoint) == "table" and finite(endpoint.x)
    local roadY = type(endpoint) == "table" and finite(endpoint.y)
    if not roadX or not roadY then
        return parkResult(job, "failed", "road_goal_unavailable")
    end
    local followed, followReason = followNative(job.actor, route, job.speedKmh)
    if not followed then
        print("[SolDrive] route refused: " .. tostring(followReason))
        job.result, job.reason, job.detail = "failed", "bridge_failure", followReason
        do local FN88 = rawget(_G, "SolFailNote"); if type(FN88) == "table" and type(FN88.bridge) == "function" then pcall(FN88.bridge, "follow", followReason, job, route) end end   -- Sol s88
        Driving.stop(job.actor, "bridge_failure")
        return false
    end
    job.roadGoal = { x = roadX, y = roadY, z = job.goal.z }
    job.route, job.phase, job.blockedSince = route, "following", nil
    job.lastProgressAt, job.lastProgressX, job.lastProgressY = nil, nil, nil
    return true
end

-- Sol fix (road_bypass): a shut road is first passed from where the car stands (SolBypass); only when the ground
-- around it offers nothing does the old answer, a new route through the street network, take over.
-- Returns "started", "wait" (try again next tick) or nil (let the old answer run).
-- Sol fix: a driver never just stops. Blocked, she climbs this ladder, one rung every few seconds, logging each with her position:
--   1, 3, 5 steer a path the car can really drive (or, with none, nudge forward at an angle)   2, 4 back out with the native manoeuvre
--   6 only then the old answer, a new route. Five tiles nearer the goal starts the ladder again.
local BYPASS_FIRST_MS = 400
local function ladderLog(job, text)
    local _, x = method(job.vehicle, "getX")
    local _, y = method(job.vehicle, "getY")
    print(string.format("[SolDrive] ladder %s at %s,%s", tostring(text), tostring(x), tostring(y)))
end
local function carHeading(vehicle)
    local Vec = rawget(_G, "Vector3f")
    if Vec == nil then return nil end
    local okF, f = method(vehicle, "getForwardVector", Vec.new())
    if not okF or f == nil then return nil end
    local okX, x = method(f, "x")
    local okZ, z = method(f, "z")
    x, z = okX and finite(x), okZ and finite(z)
    if not x or not z then return nil end
    local length = math.sqrt(x * x + z * z)
    if length < 0.001 then return nil end
    return x / length, z / length
end
local function startSteer(job, points, why, current)
    local xOk, x = method(job.vehicle, "getX")
    local yOk, y = method(job.vehicle, "getY")
    job.steer = { points = points, i = 2, since = current, movedAt = current, x = xOk and x or 0, y = yOk and y or 0 }
    job.bypass, job.phase, job.blockedSince = true, "bypassing", nil
    job.lastProgressAt, job.lastProgressX, job.lastProgressY = nil, nil, nil
    ladderLog(job, "steering the way round: " .. tostring(#points) .. " points (" .. tostring(why) .. ")")
    return "started"
end
local function startUnstick(job, status, current)
    if solFixOn("java_nav") and type(rawget(_G, "solNavPlan")) == "function" then ladderLog(job, "no turning round for this"); return nil end
    if not followNative(job.actor, job.route, job.speedKmh) then ladderLog(job, "back-out refused: no route to hold"); return nil end
    local ok, why = call("driveTurnAround", job.actor, false)
    if not ok then ladderLog(job, "back-out refused: " .. tostring(why)); return nil end
    local xOk, x = method(job.vehicle, "getX")
    local yOk, y = method(job.vehicle, "getY")
    job.unstick = { x = xOk and x or 0, y = yOk and y or 0, at = current, ox = status.blockedX, oy = status.blockedY }
    job.phase, job.blockedSince = "bypassing", nil
    ladderLog(job, "backing out")
    return "started"
end
local function climbLadder(job, status, current)
    local planner = rawget(_G, "SolBypass")
    if type(planner) ~= "table" then return nil end
    local rung = job.ladder or 1
    job.ladder = rung + 1
    if rung % 2 == 0 then
        local started = startUnstick(job, status, current)
        if started then return started end
        rung, job.ladder = rung + 1, rung + 2
    end
    if rung > 5 then ladderLog(job, "out of rungs: asking the road planner"); return nil end
    status.routePoints = type(job.route) == "table" and job.route.points or nil
    local okPlan, points, info = pcall(planner.plan, job.actor, job.vehicle, status)
    if okPlan and type(points) == "table" then return startSteer(job, points, info, current) end
    ladderLog(job, "no way round: " .. tostring(okPlan and info or points))
    local xOk, x = method(job.vehicle, "getX")
    local yOk, y = method(job.vehicle, "getY")
    local hx, hy = carHeading(job.vehicle)
    local ox, oy = finite(status.blockedX), finite(status.blockedY)
    if xOk and yOk and hx and ox and oy then
        local okN, nudge = pcall(planner.nudge, x, y, hx, hy, ox, oy)
        if okN and type(nudge) == "table" then return startSteer(job, nudge, "nudge", current) end
    end
    if rung < 5 then return climbLadder(job, status, current) end
    ladderLog(job, "nothing left: asking the road planner")
    return nil
end
-- The Java planner: the map is read in slices and the path drawn on a worker, so nothing here can stutter the game.
local JNAV_GOAL_BEYOND, JNAV_MAX_GOAL, JNAV_MAX_FAILS, JNAV_PLAN_MS = 14, 45, 3, 4000
local JNAV_BAN_CLEAR_TILES, JNAV_BAN_CLEAN_ROUNDS = 10, 2
-- A place she failed at stays out of the plans until she has got well away and come through clean twice.
local function jnavBanHere(job, why)
    if why ~= "stalled" and why ~= "off_path" and why ~= "rear_blocked" then return end
    local xOk, x = method(job.vehicle, "getX")
    local yOk, y = method(job.vehicle, "getY")
    x, y = xOk and finite(x), yOk and finite(y)
    local hx, hy = carHeading(job.vehicle)
    if not x or not y or not hx then return end
    local planner = rawget(_G, "SolBypass")
    local okS, size = pcall(planner.measure, job.vehicle)
    local reach = (okS and type(size) == "table" and finite(size.halfLength) or 2.5) + 1
    if why == "rear_blocked" then reach = -reach end
    job.jnavBans = job.jnavBans or {}
    job.jnavBans[#job.jnavBans + 1] = { x = x + hx * reach, y = y + hy * reach, clean = 0 }
end
local function jnavBansCleanRound(job)
    local bans = job.jnavBans
    if type(bans) ~= "table" then return end
    local xOk, x = method(job.vehicle, "getX")
    local yOk, y = method(job.vehicle, "getY")
    local kept = {}
    for i = 1, #bans do
        local b = bans[i]
        b.clean = b.clean + 1
        local far = xOk and yOk and (x - b.x) ^ 2 + (y - b.y) ^ 2 >= JNAV_BAN_CLEAR_TILES ^ 2
        if not (far and b.clean >= JNAV_BAN_CLEAN_ROUNDS) then kept[#kept + 1] = b end
    end
    job.jnavBans = kept
end
local function jnavSendBans(job)
    local clear, add = rawget(_G, "solNavBanClear"), rawget(_G, "solNavBan")
    if type(clear) ~= "function" or type(add) ~= "function" then return end
    pcall(clear)
    for _, b in ipairs(job.jnavBans or {}) do pcall(add, b.x, b.y) end
    local RF = rawget(_G, "SolRoadFirst")
    if type(RF) == "table" then
        local _, x = method(job.vehicle, "getX")
        local _, y = method(job.vehicle, "getY")
        RF.sendCorridor(job, finite(x), finite(y))
    end
end
local function jnavReady() return solFixOn("java_nav") and type(rawget(_G, "solNavPlan")) == "function" and type(rawget(_G, "solNavState")) == "function" end
-- a road point past the obstacle, with the road's own heading there
local function jnavGoal(job, ox, oy, extra)
    local pts = type(job.route) == "table" and job.route.points or nil
    if type(pts) ~= "table" or #pts < 2 then return nil end
    local bi, bd = 1, nil
    for i = 1, #pts do
        local d = (pts[i].x - ox) ^ 2 + (pts[i].y - oy) ^ 2
        if not bd or d < bd then bi, bd = i, d end
    end
    local run, want = 0, JNAV_GOAL_BEYOND + (extra or 0)
    for i = bi, #pts - 1 do
        local a, b = pts[i], pts[i + 1]
        local seg = math.sqrt((b.x - a.x) ^ 2 + (b.y - a.y) ^ 2)
        run = run + seg
        if run >= want and seg > 0.01 then
            local dx, dy, over = (b.x - a.x) / seg, (b.y - a.y) / seg, run - want    -- a long straight has few points: the goal is measured along it, not at its far end
            return b.x - dx * over, b.y - dy * over, dx, dy
        end
    end
    local a, b = pts[#pts - 1], pts[#pts]
    local seg = math.sqrt((b.x - a.x) ^ 2 + (b.y - a.y) ^ 2)
    if seg > 0.01 then return b.x, b.y, (b.x - a.x) / seg, (b.y - a.y) / seg end
    return nil
end
local JNAV_NO_WAY = { no_path = true, no_path_found = true, no_corridor_wide_enough = true, out_of_time = true }
local function jnavStart(job, ox, oy, current, lead)
    if job.jnav or not jnavReady() then return false end
    local fails = job.jnavFails or 0
    local turnBack = fails == JNAV_MAX_FAILS and (job.jnavNoWay or 0) >= 1     -- three forward tries failed and the way really is shut: only now may a plan turn back
    if fails >= JNAV_MAX_FAILS and not turnBack then return false end
    local planner = rawget(_G, "SolBypass")
    if type(planner) ~= "table" or type(planner.measure) ~= "function" then return false end
    local okS, size = pcall(planner.measure, job.vehicle)
    local xOk, x = method(job.vehicle, "getX")
    local yOk, y = method(job.vehicle, "getY")
    x, y = xOk and finite(x), yOk and finite(y)
    local hx, hy = carHeading(job.vehicle)
    if not okS or type(size) ~= "table" or not x or not y or not hx then return false end
    local gx, gy, ghx, ghy = jnavGoal(job, ox or x, oy or y, job.jnavExtra)
    if not gx then return false end
    if (gx - x) ^ 2 + (gy - y) ^ 2 > JNAV_MAX_GOAL ^ 2 then return false end
    jnavSendBans(job)
    local mayTurn = rawget(_G, "solNavMayTurnBack")
    if turnBack and type(mayTurn) == "function" then pcall(mayTurn); ladderLog(job, "forward is shut: she may turn back now") end
    local ahead = lead or 0                                                 -- the car keeps rolling while the plan is drawn
    local ok, started = pcall(rawget(_G, "solNavPlan"), job.vehicle, x + hx * ahead, y + hy * ahead, hx, hy, gx, gy, ghx, ghy, size.wheelbase, size.kmax)
    if not ok or started ~= true then return false end
    job.jnav = { since = current }
    job.bypass, job.phase, job.blockedSince = true, "bypassing", nil
    job.lastProgressAt, job.lastProgressX, job.lastProgressY = nil, nil, nil
    ladderLog(job, "drawing the way round in Java")
    return true
end
-- Returns "running", "done", or "failed" with the reason.
local function jnavTick(job, current)
    local beat, follow = rawget(_G, "solNavBeat"), rawget(_G, "solNavFollow")
    local okS, st = pcall(rawget(_G, "solNavState"))
    if not okS or type(st) ~= "string" then return "failed", "no_state" end
    if type(beat) == "function" then pcall(beat) end
    if st == "ready" then
        local _ = call("driveSet", job.actor, 0, 0, true)                   -- the native route lets go; the follower takes the controls
        local okF, took = pcall(follow)
        if not okF or took ~= true then return "failed", "follow_refused" end
        ladderLog(job, "following the drawn path")
        return "running"
    end
    if st == "done" then return "done" end
    if st == "capturing" or st == "planning" then
        if current - job.jnav.since > JNAV_PLAN_MS then return "failed", "plan_timeout" end
        return "running"
    end
    if st == "following" then return "running" end
    return "failed", string.gsub(st, "^failed:", "")
end
-- Returns "running", "done" or "stalled".
local function steerTick(job, current)
    local planner, s = rawget(_G, "SolBypass"), job.steer
    local xOk, x = method(job.vehicle, "getX")
    local yOk, y = method(job.vehicle, "getY")
    x, y = xOk and finite(x), yOk and finite(y)
    local hx, hy = carHeading(job.vehicle)
    if type(planner) ~= "table" or not x or not y or not hx then return "stalled" end
    if (x - s.x) ^ 2 + (y - s.y) ^ 2 >= 0.16 then s.x, s.y, s.movedAt = x, y, current end
    if current - s.movedAt > 3000 or current - s.since > math.max(30000, #s.points * 1200) then ladderLog(job, "steering stalled"); return "stalled" end
    if current - s.since > 700 and not planner.aheadClear(x, y, hx, hy) then ladderLog(job, "steering: something at the bumper"); return "stalled" end
    local steer, kmh = planner.steerStep(s, x, y, hx, hy)
    if steer == nil then return "done" end
    local ok, why = call("driveSet", job.actor, steer, kmh, false)
    if not ok then ladderLog(job, "steering refused: " .. tostring(why)); return "stalled" end
    return "running"
end
-- Seen from far off: the road ahead is watched all the time, and the way round is planned before she gets there.
local LOOK_REPLAN_MS, LOOK_MAX_TILES = 2500, 20
local function lookAhead(job, status, current)
    if job.precise or job.steer or job.unstick or job.jnav or not solFixOn("road_bypass") then return end
    if job.lookNextAt and current < job.lookNextAt then return end
    job.lookNextAt = current + 700
    local planner = rawget(_G, "SolBypass")
    if type(planner) ~= "table" or type(planner.scanAhead) ~= "function" or type(job.route) ~= "table" then return end
    local xOk, x = method(job.vehicle, "getX")
    local yOk, y = method(job.vehicle, "getY")
    if not xOk or not yOk then return end
    local size = planner.measure and planner.measure(job.vehicle) or {}
    local speed = math.abs(finite(status.speedKmh) or 0)
    local okS, dist, ox, oy, what = pcall(planner.scanAhead, job.route.points, x, y, math.min(40, math.max(25, 25 + speed * 0.5)), size.halfLength, size.halfWidth)
    if not okS or not dist or dist > LOOK_MAX_TILES then return end
    local RF = rawget(_G, "SolRoadFirst")
    if type(RF) == "table" and RF.on() and not RF.seen(job, ox, oy, current) then return end
    if job.lookPlanAt and current - job.lookPlanAt < LOOK_REPLAN_MS then return end
    job.lookPlanAt = current
    ladderLog(job, string.format("seen ahead %.0f tiles on, at %.0f,%.0f what=%s", dist, ox, oy, tostring(what)))
    if jnavReady() and jnavStart(job, ox, oy, current, speed / 3.6 * 0.25) then return end
    local look = { blockedX = ox, blockedY = oy, routePoints = job.route.points }
    local okPlan, points, info = pcall(planner.plan, job.actor, job.vehicle, look)
    if okPlan and type(points) == "table" then startSteer(job, points, "planned ahead, " .. tostring(info), current)
    else ladderLog(job, "no way round yet: " .. tostring(okPlan and info or points)) end
end

-- Forward is used up: the road planner goes round this place by another street.
local function jnavReroute(job, status)
    if job.attempts == nil or job.circles == nil or job.attempts >= 3 or #job.circles >= 8 then return false end
    local RF = rawget(_G, "SolRoadFirst")
    if type(RF) == "table" and not job.slForce and not RF.mayReroute(job, status, job.vehicle) then return false end   -- Sol fix stall_ladder: every rung failed, the way is shut
    local xOk, x = method(job.vehicle, "getX")
    local yOk, y = method(job.vehicle, "getY")
    x, y = finite(status.blockedX) or (xOk and finite(x)), finite(status.blockedY) or (yOk and finite(y))
    if not x or not y then return false end
    job.circles[#job.circles + 1] = { x = x, y = y, radius = 12 }
    job.lastBlockX, job.lastBlockY = x, y
    job.attempts, job.phase, job.bypass = job.attempts + 1, "replanning", nil
    job.jnavFails, job.jnavNoWay, job.jnavExtra, job.ladder = 0, 0, 0, 1
    ladderLog(job, "this way is shut: another street")
    planJob(job)
    return true
end

-- Sol fix stall_ladder (s81): every stalled or failed way round feeds the next rung at once (SolStallLadder.lua).
local function slOn()
    local L = rawget(_G, "SolStallLadder")
    if solFixOn("stall_ladder") and type(L) == "table" and type(L.next) == "function" then return L end
    return nil
end
local SL_OPS = nil
local function slOps()
    if SL_OPS then return SL_OPS end
    SL_OPS = {
        log = function(job, text) ladderLog(job, text) end,
        pose = function(job)
            local xOk, x = method(job.vehicle, "getX")
            local yOk, y = method(job.vehicle, "getY")
            x, y = xOk and finite(x), yOk and finite(y)
            local hx, hy = carHeading(job.vehicle)
            if not x or not y or not hx then return nil end
            return x, y, hx, hy
        end,
        size = function(job)
            local P = rawget(_G, "SolBypass")
            if type(P) ~= "table" or type(P.measure) ~= "function" then return nil end
            local ok, size = pcall(P.measure, job.vehicle)
            return ok and type(size) == "table" and size or nil
        end,
        points = function(job) return type(job.route) == "table" and job.route.points or nil end,
        free = function(job, x, y, hx, hy, size)
            local P, L = rawget(_G, "SolBypass"), rawget(_G, "SolStallLadder")
            if type(P) ~= "table" or type(L) ~= "table" then return nil end
            local ok, free = pcall(L.spotFree, P.world, x, y, hx, hy, size.halfLength, size.halfWidth, job.vehicle)
            if ok then return free end
            return nil
        end,
        plan = function(job, sx, sy, hx, hy, gx, gy, ghx, ghy, size, kind, wide, current)
            if job.jnav or not jnavReady() then return false end
            jnavSendBans(job)
            if wide then
                local clear, mayTurn = rawget(_G, "solNavCorridorClear"), rawget(_G, "solNavMayTurnBack")
                if type(clear) == "function" then pcall(clear) end
                if type(mayTurn) == "function" then pcall(mayTurn) end
            end
            local ok, started = pcall(rawget(_G, "solNavPlan"), job.vehicle, sx, sy, hx, hy, gx, gy, ghx, ghy, size.wheelbase, size.kmax)
            if not ok or started ~= true then return false end
            job.jnav = { since = current, sl = kind }
            job.bypass, job.phase, job.blockedSince = true, "bypassing", nil
            job.lastProgressAt, job.lastProgressX, job.lastProgressY = nil, nil, nil
            ladderLog(job, "drawing the way round in Java")
            return true
        end,
        nudge = function(job, x, y, hx, hy, ox, oy, current)
            local P = rawget(_G, "SolBypass")
            if type(P) ~= "table" or type(P.nudge) ~= "function" then return false end
            local ok, points = pcall(P.nudge, x, y, hx, hy, ox, oy)
            if not ok or type(points) ~= "table" then return false end
            return startSteer(job, points, "nudge", current) == "started"
        end,
        reroute = function(job, status)
            job.slForce = true
            local ok, rerouted = pcall(jnavReroute, job, status)
            job.slForce = nil
            if not ok then ladderLog(job, "stall_ladder: road planner error: " .. tostring(rerouted)) end
            return ok and rerouted == true and not job.parked
        end,
        park = function(job, reason) return parkResult(job, "failed", reason) end,
        say = function(job, line)
            local D = SC.Dialogue
            if type(D) ~= "table" or type(D.emitResolved) ~= "function" then return false end
            local ok, spoken = pcall(D.emitResolved, job.actor, "drive_stuck", line)
            return ok and spoken == true
        end,
    }
    return SL_OPS
end

local function tryBypass(job, status, current)
    if job.precise or not solFixOn("road_bypass") then return nil end
    local xOk, vx = method(job.vehicle, "getX")
    local yOk, vy = method(job.vehicle, "getY")
    vx, vy = xOk and finite(vx), yOk and finite(vy)
    if not vx or not vy then return nil end
    local goal = job.roadGoal or job.goal
    if type(goal) == "table" and finite(goal.x) and finite(goal.y) then
        local d = math.sqrt((vx - goal.x) ^ 2 + (vy - goal.y) ^ 2)
        if not job.ladderBest or d < job.ladderBest - 5 then job.ladderBest, job.ladder = d, 1 end
    end
    do local SL = slOn(); if SL then                                                       -- Sol fix stall_ladder: the ladder owns a stop
        if current - job.blockedSince < BYPASS_FIRST_MS then return "wait" end
        SL.onBlocked(job, status, current, slOps())
        return "started"
    end end
    if (job.ladder or 1) > 5 then return nil end
    if current - job.blockedSince < BYPASS_FIRST_MS then return "wait" end
    if jnavStart(job, finite(status.blockedX), finite(status.blockedY), current, 0) then return "started" end
    if jnavReady() and (job.jnavFails or 0) >= JNAV_MAX_FAILS then
        if not jnavReroute(job, status) then parkResult(job, "failed", "no_way_round") end
        return "started"
    end
    return climbLadder(job, status, current)
end

function Driving.drive(actor, goal, options)
    options = type(options) == "table" and options or {}
    local gx = type(goal) == "table" and finite(goal.x) or nil
    local gy = type(goal) == "table" and finite(goal.y) or nil
    if not gx or not gy or goal.z ~= 0 or gx < 0 or gx > 30000 or gy < 0 or gy > 30000 then
        return false, "invalid_drive_goal"
    end

    local prior = jobs[actor]
    local supervisor = SC.ActionSupervisor
    local prepared = prior and prior.nativeStarted == true and prior.managed ~= true
        and prior.parked ~= true and prior.releaseReason == nil and prior.phase == "waiting"
        and supervisor and type(supervisor.isCurrent) == "function"
        and supervisor.isCurrent(prior.token)
    if prior and not prepared then return false, "drive_already_owned" end
    if prior and prior.goal and (prior.goal.x ~= gx or prior.goal.y ~= gy) then
        prior.goal = { x = gx, y = gy, z = 0 } -- Sol patch: a prepared lease still waiting (not moving) takes the new destination instead of stranding the player aboard
    end

    local job = prior
    if not job then
        -- driveStart must be acquired before the player boards.  SolGPS normally
        -- prepares this lease first; direct callers fail closed rather than asking
        -- the native bridge to accept an occupied vehicle.
        -- Sol patch 2026-10-25: player riding as passenger allowed (native driveStart only requires Sol at the wheel)
        local token, why = Driving.begin(actor, { x = gx, y = gy, z = 0 })
        if not token then return false, why end
        job = jobs[actor]
        local started, startReason = startNative(job)
        if not started then return false, startReason end
    elseif not job.goal then
        job.goal = { x = gx, y = gy, z = 0 }
    end

    job.managed, job.phase = true, "planning"
    job.speedKmh = math.max(0, math.min((type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("speed_levels") == true) and 70 or ((type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("drive_fast") == true) and 50 or 30), finite(options.speedKmh) or 10))   -- Sol fix speed_levels: 70 = the s80 jar ceiling; off: 50, what the old jar clamped drive_fast's 60 to
    job.stopShortTiles = math.max(0,
        math.min(10, finite(options.stopShortTiles) or 0))
    job.blockWaitMs = math.max(1000, math.min(30000, finite(options.blockWaitMs) or 5000))
    if options.circles ~= nil then
        if type(options.circles) ~= "table" or #options.circles > 8 then
            Driving.stop(actor, "invalid_road_avoidance") return false, "invalid_road_avoidance"
        end
        for key in pairs(options.circles) do
            if type(key) ~= "number" or key % 1 ~= 0 or key < 1 or key > #options.circles then
                Driving.stop(actor, "invalid_road_avoidance") return false, "invalid_road_avoidance"
            end
        end
        for _, circle in ipairs(options.circles) do
            local x = type(circle) == "table" and finite(circle.x) or nil
            local y = type(circle) == "table" and finite(circle.y) or nil
            local radius = type(circle) == "table" and finite(circle.radius) or nil
            if not x or not y or not radius or x < 0 or x > 30000 or y < 0 or y > 30000
                or radius < 4 or radius > 32 then
                Driving.stop(actor, "invalid_road_avoidance") return false, "invalid_road_avoidance"
            end
            job.circles[#job.circles + 1] = { x = x, y = y, radius = radius }
        end
    end
    planJob(job)
    return true, job.reason or "driving"
end

function Driving.clearOutcome(actor) outcomes[actor] = nil end       -- a new attempt must not be answered by the last trip's ending

function Driving.jobStatus(actor)
    local job = jobs[actor]
    return job and snapshot(job) or outcomes[actor]
end

-- Sol patch 2026-10-25: change the cruise speed of a running drive without stopping it (re-issues the same route at the new speed).
function Driving.setSpeed(actor, kmh)
    local job = jobs[actor]
    kmh = finite(kmh)
    local levels80 = (type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("speed_levels") == true)   -- Sol fix speed_levels
    if not job or not kmh or kmh <= 0 or kmh > (levels80 and 70 or 60) then return false, "no_drive" end
    if not levels80 then kmh = math.min(kmh, 50) end                         -- the old jar's ceiling, as before
    job.speedKmh = kmh
    if job.phase == "following" and job.route then return followNative(job.actor, job.route, kmh) end
    return true, "stored"
end

-- Sol patch 2026-10-25: a new destination while driving: re-plan to it without releasing the lease.
function Driving.setGoal(actor, goal)
    local job = jobs[actor]
    local gx = type(goal) == "table" and finite(goal.x) or nil
    local gy = type(goal) == "table" and finite(goal.y) or nil
    if not job or not gx or not gy or gx < 0 or gx > 30000 or gy < 0 or gy > 30000 then return false, "no_drive" end
    if job.phase ~= "following" and job.phase ~= "blocked" then return false, "not_driving" end
    job.goal = { x = gx, y = gy, z = 0 }
    job.circles, job.attempts, job.cycles, job.blockedSince, job.lastBlockX = {}, 0, 0, nil, nil
    job.phase = "replanning"
    planJob(job)
    return true, "replanned"
end
function Driving.tick(current)
    current = finite(current) or nowMs()
    local active = {}
    for actor in pairs(jobs) do active[#active + 1] = actor end
    for _, actor in ipairs(active) do
        local job = jobs[actor]
        if job and Driving.isDriving(actor) then
            if job.releaseReason then
                Driving.stop(actor, job.releaseReason)
            elseif job.pendingResult then
                parkResult(job, job.pendingResult, job.pendingReason)
            elseif not job.parked then
                local status = job.nativeStatus
                -- The actual bumper scan can brake a car while the route
                -- follower still sees a clear lane and reports FOLLOW.
                local state = status.state == "safety_blocked"
                    and "blocked" or status.mode or status.state
                if job.managed and not job.precise and (state == "follow"
                    or state == "avoiding") and status.engineRunning == true
                    and (finite(status.cruiseKmh) or 0) > 0 then
                    local xOk, x = method(job.vehicle, "getX")
                    local yOk, y = method(job.vehicle, "getY")
                    x, y = xOk and finite(x), yOk and finite(y)
                    if x and y then
                        if not job.lastProgressAt or not job.lastProgressX
                            or (x - job.lastProgressX)^2
                                + (y - job.lastProgressY)^2 >= 0.25 then
                            job.lastProgressAt = current
                            job.lastProgressX, job.lastProgressY = x, y
                        elseif current - job.lastProgressAt >= 3000
                            and math.abs(finite(status.speedKmh) or 0) < 1 then
                            state = "blocked"
                            status.blockedX, status.blockedY = x, y
                        end
                    end
                else
                    job.lastProgressAt = nil
                end
                local slFired = false                                                   -- Sol fix stall_ladder: nothing may stand still
                do local SL = slOn(); if SL and not job.jnav and not job.steer and not job.unstick then slFired = SL.watch(job, state, status, current, slOps()) == true end end
                if slFired then
                elseif job.jnav then
                    local outcome, why = jnavTick(job, current)
                    if outcome == "done" and slOn() and job.jnav.sl == "reverse" then          -- Sol fix stall_ladder: backing up is a rung, not the way past
                        job.jnav = nil
                        local _ = rawget(_G, "solNavStop") and pcall(rawget(_G, "solNavStop"))
                        if not slOn().onDone(job, "reverse", status, current, slOps()) then job.bypass, job.phase = nil, "replanning"; planJob(job) end
                    elseif outcome == "done" then
                        do local SL = slOn(); if SL then SL.passed(job) end end
                        job.jnav, job.bypass, job.phase, job.ladder, job.jnavFails, job.jnavExtra, job.jnavNoWay = nil, nil, "replanning", 1, 0, 0, 0
                        jnavBansCleanRound(job)
                        local _ = rawget(_G, "solNavStop") and pcall(rawget(_G, "solNavStop"))
                        ladderLog(job, "past it: back to the road")
                        planJob(job)
                    elseif outcome == "failed" then
                        job.jnav = nil
                        job.jnavFails = (job.jnavFails or 0) + 1
                        jnavBanHere(job, why)
                        if JNAV_NO_WAY[why] then job.jnavNoWay = (job.jnavNoWay or 0) + 1 end
                        if why == "goal_not_free" or JNAV_NO_WAY[why] then job.jnavExtra = (job.jnavExtra or 0) + 4 end  -- another try must be a different try
                        local _ = rawget(_G, "solNavStop") and pcall(rawget(_G, "solNavStop"))
                        ladderLog(job, "Java way round failed: " .. tostring(why))
                        local stopped = call("driveSet", job.actor, 0, 0, true)
                        local SLf = slOn()
                        if SLf then SLf.onFail(job, why, status, current, slOps())                 -- Sol fix stall_ladder: every failure feeds the next rung
                        elseif not jnavStart(job, finite(status.blockedX), finite(status.blockedY), current, 0) and not jnavReroute(job, status) then parkResult(job, "failed", "no_way_round") end
                    end
                elseif job.steer then
                    local outcome = steerTick(job, current)
                    if outcome == "done" then
                        job.steer, job.bypass, job.phase, job.ladder = nil, nil, "replanning", 1       -- it worked: the next obstacle starts from the first rung
                        ladderLog(job, "past it: back to the road")
                        planJob(job)
                    elseif outcome == "stalled" then
                        job.steer = nil
                        do
                            local planner = rawget(_G, "SolBypass")
                            local hxS, hyS = carHeading(job.vehicle)
                            local xOkS, xS = method(job.vehicle, "getX")
                            local yOkS, yS = method(job.vehicle, "getY")
                            if type(planner) == "table" and type(planner.noteStuck) == "function" and hxS and xOkS and yOkS then
                                pcall(planner.noteStuck, xS, yS, hxS, hyS)
                            end
                        end
                        local _ = call("driveSet", job.actor, 0, 0, true)
                        local SLs = slOn()
                        if SLs then SLs.onFail(job, "steer_stalled", status, current, slOps())      -- Sol fix stall_ladder
                        elseif climbLadder(job, status, current) == nil then job.phase = "replanning"; planJob(job) end
                    end
                elseif job.unstick then
                    local u = job.unstick
                    local xOk3, x3 = method(job.vehicle, "getX")
                    local yOk3, y3 = method(job.vehicle, "getY")
                    local moved = xOk3 and yOk3 and (x3 - u.x) ^ 2 + (y3 - u.y) ^ 2 or 0
                    local native = tostring(status.mode or status.state)
                    if moved >= 30.25 or current - u.at > 10000 or native == "turned" or native == "turn_failed" then
                        job.unstick = nil
                        ladderLog(job, "backed out (" .. native .. ")")
                        status.blockedX, status.blockedY = u.ox, u.oy
                        if climbLadder(job, status, current) == nil then job.phase = "replanning"; planJob(job) end
                    end
                elseif job.managed and status.state == "engine_failed" then
                    parkResult(job, "failed", "engine_failed")
                elseif state == "arrived" then
                    if job.bypass then       -- past the obstacle: back onto the road from here
                        job.bypass, job.phase, job.lastProgressAt = nil, "replanning", nil
                        planJob(job)
                    elseif job.managed then
                        local reached, reason = reachedGoal(job)
                        parkResult(job, reached and "arrived" or "failed", reached and "arrived" or reason)
                    else job.phase, job.result = "arrived", "arrived" end
                elseif state == "turn_failed" or status.turnState == "failed" then
                    parkResult(job, "failed", "turn_failed")
                elseif job.precise and job.approachDeadline
                    and current >= job.approachDeadline then
                    parkResult(job, "failed", "parking_approach_timeout")
                elseif job.precise and state == "blocked" then
                    parkResult(job, "failed", status.obstacleKind == "unloaded"
                        and "parking_streaming_stalled" or "parking_approach_blocked")
                elseif job.managed and state == "blocked" then
                    if status.obstacleKind == "unloaded" then
                        job.phase = "streaming_wait"
                        job.streamingSince = job.streamingSince or current
                        job.blockedSince = nil
                        if current - job.streamingSince >= 30000 then
                            parkResult(job, "failed", "streaming_stalled")
                        end
                    else
                    job.streamingSince = nil
                    job.phase = "blocked"
                    job.blockedSince = job.blockedSince or current
                    local bypass = tryBypass(job, status, current)
                    if bypass == nil and current - job.blockedSince >= (job.precise and job.blockWaitMs or math.min(job.blockWaitMs, 3000)) then
                        local x, y = finite(status.blockedX), finite(status.blockedY)
                        if not x or not y or x < 0 or x > 30000 or y < 0 or y > 30000 then
                            parkResult(job, "failed", "invalid_blocked_position")
                        elseif job.attempts >= 3 or #job.circles >= 8 then
                            job.cycles = (job.cycles or 0) + 1
                            if job.cycles > 4 then parkResult(job, "failed", "route_blocked")
                            else job.circles, job.attempts, job.blockedSince = {}, 0, current end
                        else
                            job.circles[#job.circles + 1] = { x = x, y = y, radius = 12 }
                            job.lastBlockX, job.lastBlockY = x, y
                            job.attempts, job.phase = job.attempts + 1, "replanning"
                            planJob(job)
                        end
                    end
                    end
                elseif job.managed then
                    job.phase, job.blockedSince = "following", nil
                    lookAhead(job, status, current)
                    do local G80 = rawget(_G, "SolSpeedGov"); if type(G80) == "table" and type(G80.tick) == "function" then local okG, errG = pcall(G80.tick, job, status, current, followNative, method); if not okG then print("[SolDrive] s80 governor: " .. tostring(errG)) end end end   -- Sol fix speed_levels
                    if job.lastBlockX then
                        local xOk2, vx2 = method(job.vehicle, "getX"); local yOk2, vy2 = method(job.vehicle, "getY")
                        vx2, vy2 = xOk2 and finite(vx2), yOk2 and finite(vy2)
                        if vx2 and vy2 and (vx2 - job.lastBlockX)^2 + (vy2 - job.lastBlockY)^2 > 3600 then job.attempts, job.cycles, job.circles, job.lastBlockX = 0, 0, {}, nil end
                    end
                    job.streamingSince = nil
                end
            end
        end
    end
    return true
end

function Driving.reset()
    local active, failures = {}, {}
    for actor in pairs(jobs) do active[#active + 1] = actor end
    for _, actor in ipairs(active) do
        local stopped, why = Driving.stop(actor, "interrupted_by_load")
        if not stopped then failures[#failures + 1] = tostring(why) end
    end
    if #failures > 0 then return false, table.concat(failures, "; ") end
    outcomes = setmetatable({}, { __mode = "k" })
    return true
end

return Driving

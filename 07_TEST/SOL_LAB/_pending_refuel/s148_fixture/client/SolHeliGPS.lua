-- SolHeliGPS.lua - direct-air GPS controller for AviationCore helicopters.
-- AviationCore's flight runtime is hard-wired to getPlayer() and seat 0. In
-- single-player, its local compatibility copy explicitly resolves Sol while
-- GPS flight is active and she owns seat 0. Sol can take the pilot seat from any passenger seat; if the
-- player occupies seat 0, he is moved to a free passenger seat first.
SolHeliGPS = SolHeliGPS or {}
local H = SolHeliGPS
H.VERSION = "0.4.9"
H.levels = H.levels or { low = 2.4, medium = 5.2, high = 7.6 }
H.selected = H.selected or "low"
H.speed = H.speed or "normal"
H.speedKmh = { slow = 20, normal = 40, fast = 65 }
H.active = H.active or false
H.destination = H.destination or nil
H.phase = H.phase or "ready"
H.landingRequested = H.landingRequested or false
H.reason = nil
H.startTimeoutMs = 30000
H.startRequestedAt = nil
H.startVehicle = nil
H.postLandingTimeoutMs = 30000
H.headingRetryTimeoutMs = 15000
-- Hysteresis keeps the route controller from bouncing between climb and cruise
-- when the sampled world altitude jitters around the selected band.
H.altitudeCaptureTolerance = 0.35
H.altitudeReleaseTolerance = 0.65

local function log(message) print("[SolHeliGPS] " .. tostring(message)) end
local reportRuntimeBridgeOutcome
local function restoreSpeedLimit()
    if not H._speedLimitSaved then return end
    local debugConfig = H._speedDebugConfig
    if type(debugConfig) == "table" then
        debugConfig.flightMaxForwardSpeed = H._previousMaxForwardSpeed
    end
    H._speedLimitSaved, H._speedDebugConfig, H._previousMaxForwardSpeed = false, nil, nil
    log("flight speed limit restored")
end
local function applySpeedLimit()
    local debugConfig = rawget(_G, "AviationCoreDebug")
    if type(debugConfig) ~= "table" then
        log("flight speed selection unavailable: AviationCoreDebug missing")
        return false, "flight_speed_config_unavailable"
    end
    if not H._speedLimitSaved then
        H._speedDebugConfig = debugConfig
        H._previousMaxForwardSpeed = debugConfig.flightMaxForwardSpeed
        H._speedLimitSaved = true
    end
    local kmh = H.speedKmh[H.speed] or H.speedKmh.normal
    debugConfig.flightMaxForwardSpeed = kmh / 3.6
    log("flight speed selected " .. tostring(H.speed) .. " targetKmh=" .. tostring(kmh))
    return true
end
local function call(object, name, ...)
    if object == nil or type(object[name]) ~= "function" then return nil end
    local ok, value = pcall(object[name], object, ...)
    if ok then return value end
    return nil
end
local function enabled()
    local a = rawget(_G, "SolAuthority")
    return type(a) == "table" and type(a.on) == "function" and a.on("heli_gps") == true
end
local function isHelicopter(vehicle)
    local ac = rawget(_G, "AviationCore")
    if type(ac) ~= "table" or type(ac.GetHelicopterType) ~= "function" or not vehicle then return false end
    local ok, kind = pcall(ac.GetHelicopterType, vehicle)
    return ok and kind ~= nil and kind ~= false
end
local function solActor()
    local ui = rawget(_G, "SolUI")
    if type(ui) == "table" and type(ui.solActor) == "function" then
        local ok, actor = pcall(ui.solActor)
        if ok then return actor end
    end
    return nil
end
local function player0() return getSpecificPlayer and getSpecificPlayer(0) or nil end
local function vehicleOf(actor) return call(actor, "getVehicle") end
local function seatOf(vehicle, actor)
    local seat = call(vehicle, "getSeat", actor)
    return tonumber(seat)
end
local function localPlayerIsInPilotSeat(vehicle)
    local player = player0()
    return player ~= nil and vehicleOf(player) == vehicle and seatOf(vehicle, player) == 0
end
local function stationaryForSeatChange(vehicle)
    local speed = tonumber((call(vehicle, "getCurrentSpeedKmHour")))
    if speed == nil then return false, "helicopter_speed_unavailable" end
    if math.abs(speed) > 0.5 then return false, "helicopter_must_be_stopped" end
    return true
end
local function multiplayerActive()
    for _, name in ipairs({ "isClient", "isServer" }) do
        local probe = rawget(_G, name)
        if type(probe) == "function" then
            local ok, value = pcall(probe)
            if ok and value == true then return true end
        end
    end
    return false
end
local scratchVector
local function forwardVector(vehicle)
    if vehicle and type(vehicle.getWorldPos) == "function" and rawget(_G, "Vector3f") and type(Vector3f.new) == "function" then
        if not scratchVector then
            local okNew, value = pcall(Vector3f.new)
            if okNew then scratchVector = value end
        end
        if scratchVector then
            local function sample(lz)
                local ok, point = pcall(vehicle.getWorldPos, vehicle, 0, 0, lz, scratchVector)
                if not ok or not point then return nil, nil end
                local okXY, x, y = pcall(function() return point:x(), point:y() end)
                if not okXY then return nil, nil end
                return tonumber(x), tonumber(y)
            end
            local ox, oy = sample(0)
            local fx, fy = sample(1)
            if ox and oy and fx and fy then return fx - ox, fy - oy end
        end
    end
    local direction = call(vehicle, "getForwardDirection")
    if direction then return tonumber((call(direction, "getX"))), tonumber((call(direction, "getY"))) end
    return nil, nil
end
local function applyGuidance(state, error)
    -- Match Jamal's demonstrated coordinated steering: A/D turns the nose,
    -- while LEFT/RIGHT banks and translates through the turn. Keep the same
    -- heading deadband used by GPS yaw so the two axes engage and release as
    -- one maneuver. Explicit pilot input still wins on each axis.
    local direction = H._turnDirection or 0
    if error > 0.30 then direction = 1
    elseif error < -0.30 then direction = -1
    elseif math.abs(error) < 0.18 then direction = 0 end
    H._turnDirection = direction
    local turnLeft = direction > 0
    local turnRight = direction < 0
    if not state.yawLeft and not state.yawRight then
        state.yawLeft, state.yawRight = turnLeft, turnRight
    end
    if not state.rollLeft and not state.rollRight then
        state.rollLeft, state.rollRight = turnLeft, turnRight
    end
    if not state.pitchUp and not state.pitchDown then
        state.pitchUp = math.abs(error) < 0.75
        state.pitchDown = false
    end
    return turnLeft, turnRight
end
local function worldPosition(vehicle)
    if vehicle and type(vehicle.getWorldPos) == "function" then
        if not scratchVector and rawget(_G, "Vector3f") and type(Vector3f.new) == "function" then
            local okNew, value = pcall(Vector3f.new)
            if okNew then scratchVector = value end
        end
        if scratchVector then
            local ok, point = pcall(vehicle.getWorldPos, vehicle, 0, 0, 0, scratchVector)
            if ok and point then
                local okXYZ, x, y, z = pcall(function() return point:x(), point:y(), point:z() end)
                if okXYZ then return tonumber(x), tonumber(y), tonumber(z) end
            end
        end
    end
    -- getX/getY remain useful map coordinates, but getZ() is the floor level
    -- in this vehicle API and is not helicopter altitude.
    return tonumber((call(vehicle, "getX"))), tonumber((call(vehicle, "getY"))), nil
end
local function pilotContext()
    local s, p = solActor(), player0()
    local v = vehicleOf(s)
    if not s or not v or not isHelicopter(v) then return nil, "sol_not_in_helicopter" end
    if not p or vehicleOf(p) ~= v then return nil, "player_not_in_same_helicopter" end
    local seat = seatOf(v, s)
    if seat ~= 0 then return nil, "sol_not_pilot" end
    return { vehicle = v, player = p, sol = s, seat = seat }
end
local function nowMs()
    if type(getTimestampMs) == "function" then
        local ok, value = pcall(getTimestampMs)
        if ok and tonumber(value) then return tonumber(value) end
    end
    return os and type(os.time) == "function" and os.time() * 1000 or 0
end
local function rememberDrivenHelicopter()
    local now = nowMs()
    if now - (tonumber(H._lastDrivenHelicopterCheckAt) or -100000) < 1000 then return end
    H._lastDrivenHelicopterCheckAt = now
    local player = player0()
    if not player then return end
    local vehicle = vehicleOf(player)
    if not vehicle or not isHelicopter(vehicle) then return end
    local script = call(vehicle, "getScriptName")
    if type(script) ~= "string" or script == "" then return end
    H.lastDrivenHelicopterScript = script
    local data = call(player, "getModData")
    if type(data) == "table" then data.SolLastDrivenHelicopterScript = script end
end
function H.summonHelicopter()
    local player = player0()
    if not player then return false, "no_player" end
    if type(sendClientCommand) ~= "function" then return false, "server_request_unavailable" end

    rememberDrivenHelicopter()
    local data = call(player, "getModData")
    local script = H.lastDrivenHelicopterScript
        or (type(data) == "table" and data.SolLastDrivenHelicopterScript)
    if type(script) ~= "string" or script == "" then script = "Base.UH1BHuey" end

    local now = nowMs()
    if now - (tonumber(H._lastSummonRequestAt) or -100000) < 5000 then
        return false, "summon_request_cooldown"
    end
    H._lastSummonRequestAt = now
    local ok, err = pcall(sendClientCommand, player, "SolHelicopter", "summon", {
        vehicleScript = script,
    })
    if not ok then
        H._lastSummonRequestAt = nil
        log("summon request failed script=" .. script .. " reason=" .. tostring(err))
        return false, "server_request_failed"
    end
    log("summon request queued script=" .. script)
    return true, "request_sent"
end
local function traceManualPilotInput(player, state)
    -- Passive LAB evidence only: retain the player's actual flight controls and
    -- correlate each transition with the helicopter's position and motion.
    -- Never mutate state here; the normal AviationCore input path remains owner.
    if player ~= player0() or type(state) ~= "table" then return end
    local vehicle = vehicleOf(player)
    local helicopter = vehicle ~= nil and isHelicopter(vehicle)
    local seat = helicopter and seatOf(vehicle, player) or nil
    local examiner = rawget(_G, "SolHeliExaminer")
    if type(examiner) ~= "table" and type(require) == "function" then
        local ok, loaded = pcall(require, "SolHeliExaminer")
        if ok and type(loaded) == "table" then examiner = loaded end
    end
    if type(examiner) == "table" and type(examiner.observe) == "function" then
        local ok, result = pcall(examiner.observe, player, state, helicopter and vehicle or nil, seat)
        if not ok then
            if not H._examinerErrorLogged then
                H._examinerErrorLogged = true
                log("flight examiner callback failed: " .. tostring(result))
            end
        end
    elseif not H._examinerMissingLogged then
        H._examinerMissingLogged = true
        log("flight examiner unavailable; require SolHeliExaminer failed")
    end
    if not helicopter or seat ~= 0 then return end

    local now = nowMs()
    local keys = {
        state.liftUp and "W" or "-",
        state.liftDown and "S" or "-",
        state.yawLeft and "A" or "-",
        state.yawRight and "D" or "-",
        state.pitchUp and "UP" or "-",
        state.pitchDown and "DOWN" or "-",
        state.rollLeft and "LEFT" or "-",
        state.rollRight and "RIGHT" or "-"
    }
    local signature = table.concat(keys, ",")
    local trace = H._manualPilotTrace or { lastSignature = nil, lastLogMs = -100000, sequence = 0 }
    if signature == trace.lastSignature and now - trace.lastLogMs < 1000 then return end

    trace.sequence = trace.sequence + 1
    trace.lastSignature, trace.lastLogMs = signature, now
    H._manualPilotTrace = trace

    local x, y, z = worldPosition(vehicle)
    local speed = tonumber((call(vehicle, "getCurrentSpeedKmHour")))
    local md = call(vehicle, "getModData")
    local ground = md and tonumber(md.currentGroundZ) or nil
    local fx, fy = forwardVector(vehicle)
    local function fmt(value)
        return value and string.format("%.2f", value) or "?"
    end
    log("[SolHeliTrace] n=" .. tostring(trace.sequence)
        .. " ms=" .. tostring(now)
        .. " keys=" .. table.concat(keys, "/")
        .. " worldPos=" .. fmt(x) .. "," .. fmt(y) .. "," .. fmt(z)
        .. " ground=" .. fmt(ground)
        .. " agl=" .. fmt(z and ground and (z - ground) or nil)
        .. " aglSource=" .. (z and ground and "worldPosZ-groundZ" or "unavailable")
        .. " kmh=" .. fmt(speed)
        .. " forward=" .. fmt(fx) .. "," .. fmt(fy))
end
local function requestAuthorizedEngineStart(context)
    local ac = rawget(_G, "AviationCore")
    local knowledge = type(ac) == "table" and ac.AircraftKnowledge or nil
    if type(knowledge) == "table" and type(knowledge.AuthorizeStartRequest) == "function" then
        -- AviationCore stores operator-manual knowledge per character. Sol is
        -- a separate NPC, so the vehicle's initialized glovebox manual (or the
        -- human player's read state) does not automatically qualify her. Let
        -- the player teach Sol this aircraft's manual only after the player
        -- has actually acquired the same operating knowledge. No gate bypass:
        -- the native start request still authorizes Sol afterwards.
        if type(knowledge.GetAircraftDefinition) == "function"
            and type(knowledge.CanStartAircraft) == "function"
            and type(knowledge.GrantKnowledge) == "function" then
            local okDefinition, definition = pcall(knowledge.GetAircraftDefinition, context.vehicle)
            if okDefinition and type(definition) == "table" then
                local okSol, solCanStart, solDenial = pcall(
                    knowledge.CanStartAircraft, context.sol, context.vehicle)
                local solReason = type(solDenial) == "table" and solDenial.reason or nil
                if okSol and solCanStart ~= true and solReason == "missing_type_knowledge" then
                    local okPlayer, playerCanStart = pcall(
                        knowledge.CanStartAircraft, context.player, context.vehicle)
                    if not okPlayer or playerCanStart ~= true then
                        return false, "operator_missing_type_knowledge"
                    end
                    local key = tostring(definition.operatingKnowledge or "")
                    if key == "" then return false, "aircraft_knowledge_key_unavailable" end
                    local okGrant, granted = pcall(knowledge.GrantKnowledge,
                        context.sol, key, "SolHeliGPS:player_manual_read")
                    if not okGrant then return false, "companion_knowledge_transfer_failed" end
                    local okLearned, learned = pcall(knowledge.CanStartAircraft,
                        context.sol, context.vehicle)
                    if not okLearned or learned ~= true then
                        return false, "companion_manual_knowledge_not_recorded"
                    end
                    if granted == true then
                        log("operator manual knowledge learned from player key=" .. key)
                    end
                end
            end
        end
        local ok, allowed, denial = pcall(knowledge.AuthorizeStartRequest,
            context.sol, context.vehicle, "SolHeliGPS")
        if not ok then return false, "aircraft_authorization_error" end
        if allowed ~= true then
            local reason = type(denial) == "table" and denial.reason or "aircraft_start_not_authorized"
            return false, tostring(reason)
        end
    end

    local menu = rawget(_G, "ISVehicleMenu")
    if type(menu) ~= "table" or type(menu.onStartEngine) ~= "function" then
        return false, "native_engine_start_unavailable"
    end
    local ok = pcall(menu.onStartEngine, context.sol)
    if not ok then return false, "native_engine_start_request_failed" end
    return true
end
local function activateAfterEngineReady(context)
    H.active, H.phase, H.reason = true, "climbing", nil
    H._headingUnavailableSince = nil
    H._activeVehicle = context.vehicle
    H.startRequestedAt, H.startVehicle = nil, nil
    applySpeedLimit()
    H.installRuntimePlayerProxy()
    log("engine ready; climb phase started altitude=" .. tostring(H.selected))
end
local function serviceEngineStart()
    if H.phase ~= "starting_engine" then return end
    local context, why = pilotContext()
    if not context then
        H.phase, H.reason = "failed", why or "pilot_context_lost_during_start"
        H.startRequestedAt, H.startVehicle = nil, nil
        log("engine start failed: " .. tostring(H.reason))
        return
    end
    if context.vehicle ~= H.startVehicle then
        H.phase, H.reason = "failed", "helicopter_changed_during_start"
        H.startRequestedAt, H.startVehicle = nil, nil
        log("engine start failed: helicopter_changed_during_start")
        return
    end
    local knowledge = AviationCore and AviationCore.AircraftKnowledge or nil
    local running = type(knowledge) == "table" and type(knowledge.IsEngineAlreadyRunning) == "function"
        and knowledge.IsEngineAlreadyRunning(context.vehicle) == true
    if not running then
        running = call(context.vehicle, "isEngineRunning") == true
    end
    if running then
        activateAfterEngineReady(context)
        return
    end
    local elapsed = nowMs() - (tonumber(H.startRequestedAt) or nowMs())
    if elapsed >= H.startTimeoutMs then
        H.phase, H.reason = "failed", "engine_start_timeout"
        H.startRequestedAt, H.startVehicle = nil, nil
        log("engine start failed: engine_start_timeout; check key, fuel, condition, and AviationCore knowledge")
    end
end
function H.isSolInHelicopter()
    local v = vehicleOf(solActor())
    return isHelicopter(v)
end
function H.setAltitude(level)
    if not H.levels[level] then return false, "unknown_altitude" end
    if H.selected ~= level then H._altitudeHoldReady = false end
    H.selected = level
    H.reason = nil
    log("altitude selected " .. level .. " agl=" .. tostring(H.levels[level]))
    return true
end
function H.setSpeed(level)
    if H.speedKmh[level] == nil then return false, "unknown_speed" end
    H.speed = level
    if H.active then return applySpeedLimit() end
    log("flight speed selected " .. tostring(level) .. " targetKmh=" .. tostring(H.speedKmh[level]))
    return true
end
function H.landHere()
    if not enabled() then return false, "heli_gps_disabled" end
    local s, p = solActor(), player0()
    local v = vehicleOf(s)
    if not s or not v or not isHelicopter(v) then return false, "sol_not_in_helicopter" end
    if not p or vehicleOf(p) ~= v then return false, "player_not_in_same_helicopter" end
    -- "Land here" targets the current helicopter position instead of a stale GPS marker.
    local x, y = tonumber((call(v, "getX"))), tonumber((call(v, "getY")))
    if not x or not y then return false, "helicopter_position_unavailable" end
    H.destination = { x = x, y = y }
    H.landingRequested = true
    local ok, reason = H.start(true)
    if not ok then
        log("landing request refused: " .. tostring(reason))
        return false, reason
    end
    log(string.format("landing requested target=%.0f,%.0f", H.destination.x, H.destination.y))
    return true, "landing_requested"
end
-- Put Sol in the helicopter pilot seat without ejecting or displacing anyone.
-- If the player currently occupies seat 0, move him to a free reachable
-- passenger seat first; roll that move back if Sol cannot take the pilot seat.
function H.takePilot()
    if not enabled() then return false, "heli_gps_disabled" end
    local s, p = solActor(), player0()
    local v = vehicleOf(s)
    if not s or not v or not isHelicopter(v) then return false, "sol_not_in_helicopter" end
    if not p or vehicleOf(p) ~= v then return false, "player_not_in_same_helicopter" end
    if multiplayerActive() then return false, "helicopter_pilot_is_single_player_only" end
    local solSeat, playerSeat = seatOf(v, s), seatOf(v, p)
    if solSeat == nil or playerSeat == nil or solSeat < 0 or playerSeat < 0 then
        return false, "helicopter_seat_unavailable"
    end
    if solSeat == 0 then return true, "sol_already_pilot" end
    local stopped, stopReason = stationaryForSeatChange(v)
    if not stopped then return false, stopReason end

    local occupiedOk, pilotOccupant = pcall(v.getCharacter, v, 0)
    if not occupiedOk then return false, "helicopter_pilot_seat_unavailable" end
    local playerTargetSeat
    if pilotOccupant == p then
        local count = tonumber((call(v, "getMaxPassengers")))
        if not count or count < 2 or count > 32 then return false, "no_passenger_seat_for_player" end
        local candidates = {}
        for candidate = 1, math.floor(count) - 1 do
            local installed = call(v, "isSeatInstalled", candidate)
            local occupied = call(v, "isSeatOccupied", candidate)
            local canSwitch = call(v, "canSwitchSeat", 0, candidate)
            if installed == true and occupied == false then
                candidates[#candidates + 1] = { seat = candidate, reachable = canSwitch == true }
            end
        end
        table.sort(candidates, function(a, b)
            if a.reachable ~= b.reachable then return a.reachable end
            return a.seat < b.seat
        end)
        if #candidates == 0 then return false, "no_reachable_empty_seat_for_player" end
        for _, candidate in ipairs(candidates) do
            call(v, "switchSeat", p, candidate.seat)
            if seatOf(v, p) == candidate.seat and call(v, "getCharacter", candidate.seat) == p then
                playerTargetSeat = candidate.seat
                break
            end
        end
        if not playerTargetSeat then return false, "player_seat_change_failed" end
    elseif pilotOccupant ~= nil then
        return false, "pilot_seat_occupied_by_another_crew_member"
    end
    local SC = rawget(_G, "SurvivorCompanion")
    local vehicleApi = type(SC) == "table" and SC.Vehicle or nil
    local switchedSol, switchReason
    if type(vehicleApi) == "table" and type(vehicleApi.shiftToDriver) == "function" then
        local ok, result, reason = pcall(vehicleApi.shiftToDriver, s, v)
        switchedSol, switchReason = ok and result == true, ok and reason or result
    end
    if not switchedSol or seatOf(v, s) ~= 0 or call(v, "getCharacter", 0) ~= s then
        if playerTargetSeat and call(v, "isSeatOccupied", 0) == false then
            call(v, "switchSeat", p, 0)
        end
        return false, "sol_pilot_seat_change_failed:" .. tostring(switchReason or "seat_service_unavailable")
    end
    call(v, "playPassengerAnim", 0, "idle")
    log("pilot seat acquired solFrom=" .. tostring(solSeat) .. " playerSeat=" .. tostring(seatOf(v, p)))
    return true, "sol_is_pilot"
end
function H.start(landAfterArrival)
    if not enabled() then H.phase, H.reason = "failed", "heli_gps_disabled"; return false, H.reason end
    if not H.destination then H.phase, H.reason = "failed", "no_destination"; return false, H.reason end
    if landAfterArrival ~= nil then H.landingRequested = landAfterArrival == true end
    local s = solActor()
    local v = vehicleOf(s)
    if not s or not v or not isHelicopter(v) then
        H.phase, H.reason = "failed", "sol_not_in_helicopter"
        log("start refused: sol_not_in_helicopter")
        return false, H.reason
    end
    local tookPilot, pilotReason = H.takePilot()
    if not tookPilot then
        H.phase, H.reason = "failed", pilotReason
        log("start refused: " .. tostring(pilotReason))
        return false, pilotReason
    end
    local context, why = pilotContext()
    if not context then H.phase, H.reason = "failed", why; log("start refused: " .. tostring(why)); return false, why end
    if H.phase == "starting_engine" and H.startVehicle == context.vehicle then
        return true, "engine_start_pending"
    end
    if H.active and H._activeVehicle == context.vehicle then
        log("flight already active; continuing phase=" .. tostring(H.phase))
        return true, "flight_already_active"
    end
    local knowledge = AviationCore and AviationCore.AircraftKnowledge or nil
    local alreadyRunning = type(knowledge) == "table" and type(knowledge.IsEngineAlreadyRunning) == "function"
        and knowledge.IsEngineAlreadyRunning(context.vehicle) == true
    if not alreadyRunning then alreadyRunning = call(context.vehicle, "isEngineRunning") == true end
    if alreadyRunning then
        H.active, H.phase, H.reason = true, "climbing", nil
        H._headingUnavailableSince = nil
        H._activeVehicle = context.vehicle
        applySpeedLimit()
        H.installRuntimePlayerProxy()
        log("engine already running; climb phase started altitude=" .. tostring(H.selected))
    else
        local requested, startReason = requestAuthorizedEngineStart(context)
        if not requested then
            H.active, H.phase, H.reason = false, "failed", startReason
            log("engine start refused: " .. tostring(startReason))
            return false, startReason
        end
        H.active, H.phase, H.reason = false, "starting_engine", nil
        H.startRequestedAt, H.startVehicle = nowMs(), context.vehicle
        log("authorized engine start requested; waiting for engine readiness")
    end
    return true
end
function H.setDestination(x, y)
    x, y = tonumber(x), tonumber(y)
    if not x or not y then return false, "invalid_destination" end
    H.destination = { x = x, y = y }
    H._headingUnavailableSince = nil
    H._turnDirection, H._lastGuidance = 0, nil
    if H.active then
        if H.landingRequested then H.phase = "landing"
        elseif H.phase ~= "climbing" then H.phase = "following" end
        H.reason = nil
    end
    log(string.format("direct air destination %.0f,%.0f", x, y))
    return true
end
function H.stop(reason)
    local wasActive = H.active
    if wasActive then reportRuntimeBridgeOutcome() end
    H.active, H.destination, H.landingRequested = false, nil, false
    H._headingUnavailableSince, H._lastProgressLogAt = nil, nil
    H._activeVehicle = nil
    H._postLanding = nil
    H.phase, H.reason = "stopped", reason
    H.startRequestedAt, H.startVehicle = nil, nil
    H._turnDirection, H._lastGuidance = 0, nil
    H.restoreRuntimePlayerProxy()
    restoreSpeedLimit()
    if wasActive then log("flight stopped " .. tostring(reason or "user")) end
    return true
end
function H.status()
    local context = pilotContext()
    local result = { flight = H.isSolInHelicopter(), phase = H.phase, reason = H.reason,
        altitude = H.selected, speed = H.speed, targetSpeedKmh = H.speedKmh[H.speed] or H.speedKmh.normal,
        targetAGL = (H.landingRequested and not H.destination) and 0 or H.levels[H.selected],
        active = H.active, landingRequested = H.landingRequested }
    local sol = solActor()
    local vehicle = vehicleOf(sol)
    if vehicle and isHelicopter(vehicle) then
        result.solSeat = seatOf(vehicle, sol)
        result.pilotOccupiedByPlayer = localPlayerIsInPilotSeat(vehicle)
    end
    if context then
        local v = context.vehicle
        local x, y = tonumber((call(v, "getX"))), tonumber((call(v, "getY")))
        local _, _, z = worldPosition(v)
        local md = call(v, "getModData")
        local ground = md and tonumber(md.currentGroundZ) or nil
        if x and y and H.destination then result.distance = math.sqrt((H.destination.x - x)^2 + (H.destination.y - y)^2) end
        if z and ground then result.agl = z - ground + 0.1 end
        result.worldZ = z
        result.pilotReady = true
    else
        result.pilotReady = false
    end
    return result
end

-- Explicit AviationCore call-site adapter; no debug library or global player proxy.
function H.runtimePilot()
    if H.active and enabled() then
        local context = pilotContext()
        if context then
            if not H._runtimeBridgeRoutedLogged then
                H._runtimeBridgeRoutedLogged = true
                log("FlightRuntime pilot bridge routed local pilot to Sol")
            end
            return context.sol
        end
    end
    return getPlayer()
end

reportRuntimeBridgeOutcome = function()
    if not H._runtimeBridgeRoutedLogged then log("explicit FlightRuntime pilot handoff not observed") end
end

function H.installRuntimePlayerProxy()
    H._runtimeBridgeRoutedLogged = false
    H._runtimeBridgeInstalledAt = nowMs()
    H._runtimeBridgeWatchdogLogged = false
    if rawget(_G, "SolAviationRuntimeBridgeReady") == true then
        log("explicit AviationCore pilot adapter armed; no global getPlayer replacement")
        return true
    end
    log("AviationCore pilot adapter unavailable; compatible FlightRuntime override not loaded")
    return false
end

function H.restoreRuntimePlayerProxy()
    H._runtimeBridgeRoutedLogged = false
    return true
end

local function wrapInput()
    local input = rawget(_G, "HelicopterInput")
    if type(input) ~= "table" or type(input.GetState) ~= "function" or input.solHeliGPSWrapped then return end
    local original = input.GetState
    input.solHeliGPSOriginalGetState = original
    input.GetState = function(player, ...)
        local state = original(player, ...)
        pcall(traceManualPilotInput, player, state)
        if type(state) ~= "table" or not H.active then return state end
        if not enabled() then H.stop("switch_off"); return state end
        local context, why = pilotContext()
        if context and context.sol ~= player then return state end
        if not context then H.stop(why or "pilot_context_lost"); return state end

-- GPS autopilot owns flight controls while a destination is active.
        local v = context.vehicle
        if SolAuthority.on("heli_route_ownership") == true and (H.destination or H.landingRequested) then
            -- AviationCore reads keyboard state globally, not per occupant.
            -- Ignore passenger key presses while Sol's GPS owns this flight.
            for _, key in ipairs({ "liftUp", "liftDown", "yawLeft", "yawRight",
                "pitchUp", "pitchDown", "rollLeft", "rollRight" }) do
                state[key] = false
            end
        end
        local md = call(v, "getModData")
        local ground = md and tonumber(md.currentGroundZ) or nil
        -- AviationCore's FlightContext reads the helicopter's actual altitude
        -- from getWorldPos(...):z(). getZ() is the floor/tile level here, so
        -- using it keeps altitudeReady false forever and suppresses GPS steering.
        local _, _, z = worldPosition(v)
        local altitudeReady = false
        H._altitudeReferenceReady = false
        if ground and z then
            H._missingGroundLogged = false
            H._altitudeReferenceReady = true
            local agl = z - ground + 0.1
            local maxZ = 8.0
            local fc = rawget(_G, "FlightConfig")
            if type(fc) == "table" and tonumber(fc.MAX_FLIGHT_WORLD_Z) then maxZ = tonumber(fc.MAX_FLIGHT_WORLD_Z) end
            local landingAtPoint = H.landingRequested and H.destination == nil
            local targetWorldZ = landingAtPoint and (ground - 0.1)
                or math.min(maxZ - 0.2, ground + H.levels[H.selected] - 0.1)
            local deltaZ = targetWorldZ - z
            if H._altitudeHoldVehicle ~= v then H._altitudeHoldReady = false end
            local routeFix = SolAuthority.on("heli_route_ownership") == true
            local enterBand = routeFix and (tonumber(H.altitudeCaptureTolerance) or 0.35) or 0.22
            local exitBand = routeFix and (tonumber(H.altitudeReleaseTolerance) or 0.65) or 0.22
            if H._altitudeHoldVehicle ~= v then H._altitudeHoldReady = false end
            local altitudeBand = routeFix and (H._altitudeHoldReady and exitBand or enterBand) or 0.22
            altitudeReady = math.abs(deltaZ) <= altitudeBand
            if routeFix then H._altitudeHoldReady, H._altitudeHoldVehicle = altitudeReady, v end
            if not state.liftUp and not state.liftDown then
                if deltaZ > 0.22 then state.liftUp, state.liftDown = true, false
                elseif deltaZ < -0.22 then state.liftUp, state.liftDown = false, true end
            end
            H.currentAGL = agl
            local inputSignature = table.concat({
                state.liftUp and "W" or "-", state.liftDown and "S" or "-",
                state.yawLeft and "A" or "-", state.yawRight and "D" or "-",
                state.pitchUp and "UP" or "-", state.pitchDown and "DOWN" or "-",
                state.rollLeft and "LEFT" or "-", state.rollRight and "RIGHT" or "-"
            }, "/")
            if inputSignature ~= H._lastGpsInputSignature then
                H._lastGpsInputSignature = inputSignature
                log("GPS input phase=" .. tostring(H.phase)
                    .. " controls=" .. inputSignature
                    .. " worldZ=" .. string.format("%.2f", z)
                    .. " groundZ=" .. string.format("%.2f", ground)
                    .. " targetZ=" .. string.format("%.2f", targetWorldZ)
                    .. " distance=" .. (H.destination and string.format("%.1f", math.sqrt(
                        (H.destination.x - (tonumber((call(v, "getX"))) or H.destination.x))^2
                        + (H.destination.y - (tonumber((call(v, "getY"))) or H.destination.y))^2)) or "none"))
            end
            if landingAtPoint and agl <= 0.22 and math.abs(deltaZ) <= 0.22 and not state.liftDown then
                H.active, H.landingRequested, H.phase, H.reason = false, false, "landed", nil
                H._activeVehicle = nil
                reportRuntimeBridgeOutcome()
                H.restoreRuntimePlayerProxy()
                restoreSpeedLimit()
                H._postLanding = { vehicle = v, sol = context.sol, startedAt = nowMs(), attempts = 0 }
                log("landed at destination; controls released; shutdown and exit queued")
            end
            if not landingAtPoint and not altitudeReady then
                if SolAuthority.on("heli_route_ownership") == true then
                    -- Vertical and horizontal axes are independent in AviationCore.
                    -- Keep the GPS route live while climbing or descending to a new band.
                    H.phase = "climbing"
                else
                    state.yawLeft, state.yawRight = false, false
                    state.pitchUp, state.pitchDown = false, false
                    state.rollLeft, state.rollRight = false, false
                    H.phase = "climbing"
                end
            elseif not landingAtPoint and H.phase == "climbing" then
                H.phase = "following"
                log("selected altitude reached; direct-air navigation started agl=" .. string.format("%.2f", agl))
            end
        elseif not H._missingGroundLogged then
            H._missingGroundLogged = true
            state.yawLeft, state.yawRight = false, false
            state.pitchUp, state.pitchDown = false, false
            state.rollLeft, state.rollRight = false, false
            log("GPS steering paused: current ground reference or helicopter altitude unavailable")
        end

        local destination = H.destination
        if destination and ((SolAuthority.on("heli_route_ownership") == true and H._altitudeReferenceReady)
            or altitudeReady or H.landingRequested) then
            local dx, dy = destination.x - (tonumber((call(v, "getX"))) or destination.x), destination.y - (tonumber((call(v, "getY"))) or destination.y)
            local distance = math.sqrt(dx * dx + dy * dy)
            local arrivalRadius = H.landingRequested and 2.0 or 4.0
            if distance <= arrivalRadius then
                H.destination = nil
                if H.landingRequested then
                    H.phase, H.reason = "landing", nil
                    if H.lastPhase ~= "landing" then log("destination reached; beginning vertical landing") end
                else
                    H.active, H.phase, H.reason = true, "arrived", nil
                    if H.lastPhase ~= "arrived" then log("arrived; holding selected altitude") end
                end
            else
                local fx, fy = forwardVector(v)
                if fx and fy and (math.abs(fx) + math.abs(fy)) > 0.001 then
                    H._headingUnavailableSince = nil
                    local desired = math.atan2(-dy, dx)
                    local heading = math.atan2(-fy, fx)
                    local error = desired - heading
                    while error > math.pi do error = error - 2 * math.pi end
                    while error < -math.pi do error = error + 2 * math.pi end
                    local turnLeft, turnRight = applyGuidance(state, error)
                    if SolAuthority.on("heli_route_ownership") == true then
                        -- Keep thrust only while generally aligned; coordinated yaw/roll
                        -- turns the aircraft without carrying it past a close marker.
                        state.pitchUp, state.pitchDown = distance > 4.0 and math.abs(error) < 0.75, false
                    end
                    local guidance = (turnLeft and "left" or turnRight and "right" or "straight")
                        .. (state.pitchUp and "+forward" or "")
                    if guidance ~= H._lastGuidance then
                        H._lastGuidance = guidance
                        log("GPS guidance=" .. guidance .. " headingError=" .. string.format("%.2f", error)
                            .. " coordinatedYawRoll=" .. tostring(turnLeft or turnRight))
                    end
                    H.phase, H.reason = (SolAuthority.on("heli_route_ownership") == true
                        and (altitudeReady and "following" or "climbing")) or "following", nil
                else
                    -- A single missing direction sample is transient on some
                    -- helicopter frames (takeoff/physics handoff). Keep the
                    -- altitude controller active and retry instead of tearing
                    -- down the entire GPS flight immediately.
                    local now = nowMs()
                    H._headingUnavailableSince = H._headingUnavailableSince or now
                    state.yawLeft, state.yawRight = false, false
                    state.pitchUp, state.pitchDown = false, false
                    state.rollLeft, state.rollRight = false, false
                    local elapsed = now - H._headingUnavailableSince
                    if elapsed >= H.headingRetryTimeoutMs then
                        H.phase, H.reason = "failed", "heading_unavailable"
                        H.active = false
                        if H.lastPhase ~= "failed" then
                            log("flight stopped after heading retry timeout; destination retained")
                        end
                    else
                        H.phase, H.reason = "waiting_for_heading", "heading_unavailable_retrying"
                        if H.lastPhase ~= "waiting_for_heading" then
                            log("GPS heading sample unavailable; holding altitude and retrying")
                        end
                    end
                end
            end
        end
        local now = nowMs()
        if H.active and now - (tonumber(H._lastProgressLogAt) or -100000) >= 1000 then
            H._lastProgressLogAt = now
            local px, py = tonumber((call(v, "getX"))), tonumber((call(v, "getY")))
            local currentDistance = destination and px and py
                and math.sqrt((destination.x - px)^2 + (destination.y - py)^2) or nil
            local currentSpeed = tonumber((call(v, "getCurrentSpeedKmHour")))
            log("GPS progress phase=" .. tostring(H.phase)
                .. " distance=" .. (currentDistance and string.format("%.1f", currentDistance) or "?")
                .. " agl=" .. (H.currentAGL and string.format("%.2f", H.currentAGL) or "?")
                .. " kmh=" .. (currentSpeed and string.format("%.1f", currentSpeed) or "?")
                .. " targetKmh=" .. tostring(H.speedKmh[H.speed] or H.speedKmh.normal))
        end
        H.lastPhase = H.phase
        return state
    end
    input.solHeliGPSWrapped = true
    log("AviationCore input adapter ready")
end
H.ensureInputWrapper = wrapInput
local function servicePostLanding()
    local flow = H._postLanding
    if type(flow) ~= "table" then return end
    local sol, vehicle = flow.sol, flow.vehicle
    if not sol or not vehicle or vehicleOf(sol) ~= vehicle then
        H._postLanding = nil
        H.phase, H.reason = "landed_exit_failed", "landed_vehicle_context_lost"
        log("post-landing exit failed: companion or helicopter context changed")
        return
    end
    local elapsed = nowMs() - (tonumber(flow.startedAt) or nowMs())
    local speed = tonumber((call(vehicle, "getCurrentSpeedKmHour")))
    if speed == nil then
        H._postLanding = nil
        H.phase, H.reason = "landed_exit_failed", "landing_speed_unavailable"
        log("post-landing exit failed: helicopter speed unavailable")
        return
    end
    if math.abs(speed) > 0.5 then
        if elapsed >= H.postLandingTimeoutMs then
            H._postLanding = nil
            H.phase, H.reason = "landed_exit_failed", "helicopter_did_not_settle"
            log("post-landing exit timed out waiting for a stationary helicopter")
        end
        return
    end

    if call(vehicle, "isEngineRunning") == true then
        local ui = rawget(_G, "SolUI")
        if type(ui) ~= "table" or type(ui.solEngine) ~= "function" then
            H._postLanding = nil
            H.phase, H.reason = "landed_exit_failed", "engine_shutdown_service_unavailable"
            log("post-landing exit failed: Sol engine shutdown service unavailable")
            return
        end
        if (tonumber(flow.lastShutdownAt) or 0) <= 0 or nowMs() - flow.lastShutdownAt >= 1000 then
            flow.lastShutdownAt = nowMs()
            local ok, result, reason = pcall(ui.solEngine, "off")
            if not ok or result == false then
                flow.attempts = (flow.attempts or 0) + 1
                if flow.attempts >= 3 or elapsed >= H.postLandingTimeoutMs then
                    H._postLanding = nil
                    H.phase, H.reason = "landed_exit_failed", "engine_shutdown_failed"
                    log("post-landing exit failed to shut down the engine: " .. tostring(reason or result))
                end
                return
            end
        end
        if call(vehicle, "isEngineRunning") == true then return end
    end

    local orders = rawget(_G, "SolOrders")
    if type(orders) ~= "table" or type(orders.leaveCar) ~= "function" then
        H._postLanding = nil
        H.phase, H.reason = "landed_exit_failed", "companion_exit_service_unavailable"
        log("post-landing exit failed: SolOrders.leaveCar unavailable")
        return
    end
    if flow.lastExitAttempt and nowMs() - flow.lastExitAttempt < 1000 then return end
    flow.lastExitAttempt = nowMs()
    flow.attempts = (flow.attempts or 0) + 1
    local ok, result, reason = pcall(orders.leaveCar)
    if ok and vehicleOf(sol) == nil then
        H._postLanding = nil
        H.phase, H.reason = "parked_exited", nil
        log("landing complete; engine off and Sol exited through the companion vehicle service")
        return
    end
    if flow.attempts >= 3 or elapsed >= H.postLandingTimeoutMs then
        H._postLanding = nil
        H.phase, H.reason = "landed_exit_failed", tostring(reason or result or "exit_not_verified")
        log("post-landing exit failed after " .. tostring(flow.attempts) .. " attempt(s): " .. tostring(H.reason))
    end
end

if Events and Events.OnTick then Events.OnTick.Add(function()
    pcall(rememberDrivenHelicopter)
    pcall(wrapInput)
    pcall(serviceEngineStart)
    if H.active and rawget(_G, "SolAviationRuntimeBridgeReady") ~= true then
        if H.phase ~= "failed" then
            H.phase, H.reason = "failed", "aviation_runtime_adapter_missing"
            log("flight aborted: compatible AviationCore runtime adapter missing")
        end
    end
    if H.active and not H._runtimeBridgeWatchdogLogged
        and nowMs() - (tonumber(H._runtimeBridgeInstalledAt) or nowMs()) >= 5000
        and not H._runtimeBridgeRoutedLogged then
        H._runtimeBridgeWatchdogLogged = true
        log("FlightRuntime bridge still unconfirmed after 5s unmatchedGetPlayerCalls="
            .. tostring(H._runtimeBridgeUnmatchedCalls or 0)
            .. " firstStack=" .. tostring(H._runtimeBridgeFirstStack or "none"))
    end
    pcall(servicePostLanding)
end) end
if Events and Events.OnGameStart then Events.OnGameStart.Add(function() pcall(wrapInput) end) end
if Events and Events.OnServerCommand then
    Events.OnServerCommand.Add(function(module, command, args)
        if module ~= "SolHelicopter" or command ~= "summon_result" or type(args) ~= "table" then return end
        if args.ok == true then
            log("summon confirmed script=" .. tostring(args.vehicleScript) .. " at=" .. tostring(args.x) .. "," .. tostring(args.y))
        else
            log("summon rejected reason=" .. tostring(args.reason))
        end
    end)
end
return H

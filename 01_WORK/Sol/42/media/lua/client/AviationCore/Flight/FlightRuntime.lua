-- Local Sol compatibility copy; original AviationCore FlightRuntime retained below.
-- Only the movement/correction pilot lookup is changed. See DOCS/S137_EXPLICIT_PILOT.md.
local activeMods = getActivatedMods()
if not (activeMods:contains("AviationCore") or activeMods:contains("\\AviationCore")) then return end
local function solFlightPilot()
    local gps = rawget(_G, "SolHeliGPS")
    if gps and type(gps.runtimePilot) == "function" then return gps.runtimePilot() end
    return getPlayer()
end
--[[
    FlightRuntime — Orchestrator for Helicopter Flight Engine Framework

    Thin controller tying framework + active engine together. Registers event
    handlers, manages flight state transitions, delegates all computation to
    FlightService (which dispatches to the active engine).

    Contains no physics math, no rotation math, no terrain scanning.
    All tuning constants come from FlightConfig.
]]

-------------------------------------------------------------------------------------
-- Globals (exported for HUD/UI systems in other mods)
-------------------------------------------------------------------------------------
require "AviationCore/Flight/Configuration"
require "AviationCore/Flight/FlightContext"
require "AviationCore/Flight/CorrectionContext"
require "AviationCore/Flight/Physics/ForceAdapter"
require "AviationCore/Flight/FlightAuxiliary"
require "AviationCore/Flight/FlightService"
local AirbornePersistence = require "AviationCore/AirbornePersistence"

local scratchVector = Vector3f.new()
Heli_GlobalSpeed = 0
Helicopter_GlobalSpeed = 0
Heli_GlobalHeading = 0

-------------------------------------------------------------------------------------
-- Module lifecycle: init/cleanup registration
-------------------------------------------------------------------------------------
FlightRuntime = {}
HeliMove = FlightRuntime -- External compatibility alias.
local _initCallbacks = {}
local _cleanupCallbacks = {}

function FlightRuntime.onFlightInit(fn)
    _initCallbacks[#_initCallbacks + 1] = fn
end

function FlightRuntime.onFlightCleanup(fn)
    _cleanupCallbacks[#_cleanupCallbacks + 1] = fn
end

-------------------------------------------------------------------------------------
-- Wall damage rate limiter
-------------------------------------------------------------------------------------
local _wallDamageTick = FlightConfig.GetWallDamageInterval()

-------------------------------------------------------------------------------------
-- Dual-path: OnTickEvenPaused applies corrections from position error.
-------------------------------------------------------------------------------------
local _dualPathActive = false
local ASCEND_BYPASS_GROUND_TEST = false
local _groundRefVehicleWarningLogged = false

AviationCoreFrameClock = AviationCoreFrameClock or { id = 0, ms = 0, phase = "init" }

local function aviationFrameNowMs()
    if getTimestampMs then
        local ok, value = pcall(getTimestampMs)
        if ok and type(value) == "number" then
            return value
        end
    end
    return os and os.time and (os.time() * 1000) or 0
end

local function recoveryAcceptanceDiagnosticsEnabled()
    local diagnostics = AviationCore and AviationCore.Diagnostics or nil
    return diagnostics and diagnostics.enabled == true
end

local function markAviationFrame(phase)
    local clock = AviationCoreFrameClock or { id = 0 }
    if phase == "OnTick" then
        clock.id = (clock.id or 0) + 1
    end
    clock.ms = aviationFrameNowMs()
    clock.phase = phase
    AviationCoreFrameClock = clock
    return clock
end

-------------------------------------------------------------------------------------
-- Flight state machine
-------------------------------------------------------------------------------------
local STATE_INACTIVE = "inactive"
local STATE_WARMUP   = "warmup"
local STATE_AIRBORNE = "airborne"

local _flightState = STATE_INACTIVE

-- TEMP MP diagnostic: concise 1 Hz / transition logging around the exact point
-- where native engine/rotor/lift state changes on a network client.
local _mpFlightDiag = { lastMs = 0, lastKey = nil }
local MP_RUNTIME_DIAG_ENABLED = false -- v5 sparse diagnostics owns MP tracing

local function safeBoolCall(object, methodName)
    if not object or type(object[methodName]) ~= "function" then return false end
    local ok, value = pcall(function() return object[methodName](object) end)
    return ok and value == true
end

local function safeValueCall(object, methodName, fallback)
    if not object or type(object[methodName]) ~= "function" then return fallback end
    local ok, value = pcall(function() return object[methodName](object) end)
    if ok and value ~= nil then return value end
    return fallback
end

local function squareZ(object)
    if not object or not object.getSquare then return "nil" end
    local ok, square = pcall(function() return object:getSquare() end)
    if not ok or not square or not square.getZ then return "nil" end
    local okZ, value = pcall(function() return square:getZ() end)
    return okZ and tostring(value) or "nil"
end

local function logMpFlightState(playerObj, vehicle, ctx, geometricIsAirborne, engineRunning)
    if not MP_RUNTIME_DIAG_ENABLED then return end
    local md = vehicle and vehicle.getModData and vehicle:getModData() or {}
    local now = aviationFrameNowMs()
    local engineStarted = safeBoolCall(vehicle, "isEngineStarted")
    local rotor = tonumber(md and md.rotorRPM) or -1
    local tail = tonumber(md and md.tailRotorRPM) or -1
    local phase = tostring(md and md.heliRotorStartPhase or "nil")
    local seat = vehicle and vehicle.getSeat and vehicle:getSeat(playerObj) or -1
    local physicsDt = ForceAdapter and ForceAdapter.getLastPhysicsDelta and ForceAdapter.getLastPhysicsDelta() or nil
    local subSteps = ForceAdapter and ForceAdapter.getLastSubSteps and ForceAdapter.getLastSubSteps() or nil
    local key = table.concat({
        tostring(engineRunning == true), tostring(engineStarted),
        tostring(geometricIsAirborne == true), phase,
        tostring(math.floor(rotor / 25)), tostring(seat)
    }, "|")
    local periodic = now <= 0 or _mpFlightDiag.lastMs <= 0 or (now - _mpFlightDiag.lastMs) >= 250
    if key == _mpFlightDiag.lastKey and not periodic then return end
    _mpFlightDiag.lastKey = key
    _mpFlightDiag.lastMs = now
    local vehicleId = safeValueCall(vehicle, "getId", "nil")
    local playerZ = safeValueCall(playerObj, "getZ", "nil")
    local vehicleZ = safeValueCall(vehicle, "getZ", "nil")
    print(string.format(
        "[AviationCore][MP_FLIGHT_DIAG] vehicleId=%s seat=%s state=%s engineRunning=%s engineStarted=%s rotorRPM=%.1f tailRotorRPM=%.1f rotorPhase=%s alt=%.3f ground=%.3f correctedSkidAGL=%.3f geometricAirborne=%s physicsDt=%s subSteps=%s playerZ=%s playerSquareZ=%s vehicleZ=%s vehicleSquareZ=%s",
        tostring(vehicleId), tostring(seat), tostring(_flightState),
        tostring(engineRunning == true), tostring(engineStarted), rotor, tail, phase,
        tonumber(ctx and ctx.currentAltitude) or -999, tonumber(ctx and ctx.groundLevelZ) or -999,
        tonumber(ctx and ctx.currentAltitude and ctx.groundLevelZ and FlightConfig.GetCorrectedSkidAGL(ctx.currentAltitude, ctx.groundLevelZ)) or -999,
        tostring(geometricIsAirborne == true), tostring(physicsDt), tostring(subSteps),
        tostring(playerZ), squareZ(playerObj), tostring(vehicleZ), squareZ(vehicle)))
end

local function fmtNum(value)
    local n = tonumber(value)
    if n == nil then
        return "nil"
    end
    return string.format("%.3f", n)
end

local function flag(value)
    return value and "1" or "0"
end

local function logGroundReferenceRouter(ctx, oldIsAirborne, correctedIsAirborne)
    if not AviationCoreDebug or not AviationCoreDebug.logGroundRefTest then
        return
    end

    local oldSkidAGL = FlightConfig.GetOldSkidAGL(ctx.currentAltitude, ctx.groundLevelZ)
    local correctedSkidAGL = FlightConfig.GetCorrectedSkidAGL(ctx.currentAltitude, ctx.groundLevelZ)
    if oldSkidAGL < -0.2 or oldSkidAGL > 1.5 then
        if correctedSkidAGL < -0.2 or correctedSkidAGL > 1.5 then
            return
        end
    end

    local keys = ctx.keys or {}
    AviationCoreDebug.logGroundRefTest(
        "phase=ROUTER" ..
        " state=" .. tostring(_flightState) ..
        " mode=" .. tostring(keys.w and "TAKEOFF" or (keys.s and "DESCEND" or "HOVER")) ..
        " W=" .. flag(keys.w) ..
        " S=" .. flag(keys.s) ..
        " alt=" .. fmtNum(ctx.currentAltitude) ..
        " rawFloorZ=" .. fmtNum(FlightConfig.GetRawFloorZFromGroundLevel(ctx.groundLevelZ)) ..
        " rawCandidateFloorZ=" .. fmtNum(ctx.rawFloorZ) ..
        " rawGroundLevelZ=" .. fmtNum(ctx.rawGroundLevelZ) ..
        " groundLevelZ=" .. fmtNum(ctx.groundLevelZ) ..
        " stableGroundLevelZ=" .. fmtNum(ctx.stableGroundLevelZ) ..
        " rawFloorZContaminated=" .. tostring(ctx.rawFloorZContaminated == true) ..
        " authoritativeGroundUsed=" .. tostring(ctx.authoritativeGroundUsed == true) ..
        " rawFloorZIgnoredForFlight=" .. tostring(ctx.rawFloorZIgnoredForFlight == true) ..
        " floorGuardReason=" .. tostring(ctx.floorGuardReason) ..
        " terrainSoftMargin=" .. fmtNum(FlightConfig.TERRAIN_SOFT_MARGIN) ..
        " skidClearance=" .. fmtNum(FlightConfig.LANDING_SKID_CLEARANCE) ..
        " oldSkidAGL=" .. fmtNum(oldSkidAGL) ..
        " correctedSkidAGL=" .. fmtNum(correctedSkidAGL) ..
        " oldAirborneThreshold=" .. fmtNum(ctx.groundLevelZ + FlightConfig.AIRBORNE_MARGIN) ..
        " correctedAirborneThreshold=" .. fmtNum(FlightConfig.GetRawFloorZFromGroundLevel(ctx.groundLevelZ) +
            FlightConfig.LANDING_SKID_CLEARANCE + FlightConfig.GetCorrectedAirborneMargin()) ..
        " oldIsAirborne=" .. tostring(oldIsAirborne) ..
        " correctedIsAirborne=" .. tostring(correctedIsAirborne) ..
        " groundReferenceCorrectionEnabled=" .. tostring(FlightConfig.IsGroundReferenceCorrectionEnabled()) ..
        " transitionT=nil groundBlend=nil landingTaper=nil targetVy=nil finalTargetVy=nil",
        false)
end

local function logVehicleGroundAssumption(vehicle)
    if _groundRefVehicleWarningLogged then
        return
    end
    if not AviationCoreDebug or not AviationCoreDebug.logGroundRefTest then
        return
    end
    local script = vehicle and vehicle.getScript and vehicle:getScript() or nil
    local wheelCount = script and script.getWheelCount and script:getWheelCount() or nil
    if wheelCount ~= nil and wheelCount <= 1 then
        _groundRefVehicleWarningLogged = true
        return
    end
    _groundRefVehicleWarningLogged = true
    local message = "warning=vehicle_script_not_matching_AviationCore_invisible_wheel_assumption" ..
        " wheelCount=" .. tostring(wheelCount) ..
        " suspensionStiffness=unavailable" ..
        " wheelFriction=unavailable" ..
        " stoppingMovementForce=unavailable" ..
        " brakingForce=unavailable"
    AviationCoreDebug.logGroundRefTest(message, true)
    if AviationCoreDebug.groundContactAudioEnabled == true and AviationCoreDebug.logGroundAudioTest then
        AviationCoreDebug.logGroundAudioTest(message, true)
    end
end

-------------------------------------------------------------------------------------
-- Validation
-------------------------------------------------------------------------------------
local function checkValid(playerObj, vehicle)
    if not playerObj then return false end
    if not vehicle then return false end
    if not AviationCore.GetHelicopterType(vehicle) then return false end
    local recoveryClient = AviationCore and AviationCore.AirborneRecoveryClient or nil
    if recoveryClient and type(recoveryClient.IsFlightBlocked) == "function"
            and recoveryClient.IsFlightBlocked(vehicle) then
        return false
    end
    if HelicopterGroundDrive and HelicopterGroundDrive.IsGroundVariant and HelicopterGroundDrive.IsGroundVariant(vehicle) then
        return false
    end
    local seat = vehicle:getSeat(playerObj)
    if seat ~= 0 then return false end
    return true
end

local function publishRotorDamageHandoff(md, flightResult)
    local expectedX = flightResult.rotorIntendedMoveX
    local expectedY = flightResult.rotorIntendedMoveY
    if expectedX == nil or expectedY == nil then
        expectedX = flightResult.desiredVelX or 0
        expectedY = flightResult.desiredVelZ or 0
        md.rotorHandoffSource = "legacy_engine_desired_velocity"
        md.rotorHandoffValid = nil
        md.rotorHandoffResetReason = nil
    else
        md.rotorHandoffSource = flightResult.rotorHandoffSource
        md.rotorHandoffValid = flightResult.rotorHandoffValid == true
        md.rotorHandoffResetReason = flightResult.rotorHandoffResetReason
    end
    md.rotorIntendedMoveX = expectedX
    md.rotorIntendedMoveY = expectedY
    md.rotorHandoffProducerFrame = flightResult.rotorHandoffProducerFrame
    md.rotorHandoffProducerSerial = flightResult.rotorHandoffProducerSerial
end

-------------------------------------------------------------------------------------
-- Main OnTick handler
-------------------------------------------------------------------------------------
local _mpRuntimeEntryDiag = { lastMs = 0, lastKey = nil }
local function mpRuntimeEntryLog(playerObj, vehicle)
    if not MP_RUNTIME_DIAG_ENABLED then return end
    if not playerObj or not vehicle then return end
    local now = aviationFrameNowMs()
    local heliType = AviationCore and AviationCore.GetHelicopterType and AviationCore.GetHelicopterType(vehicle) or nil
    if not heliType then return end
    local seat = -1
    if vehicle.getSeat then
        local ok, v = pcall(function() return vehicle:getSeat(playerObj) end)
        if ok and v ~= nil then seat = v end
    end
    local running = safeBoolCall(vehicle, "isEngineRunning")
    local started = safeBoolCall(vehicle, "isEngineStarted")
    local md = vehicle.getModData and vehicle:getModData() or nil
    local recoveryBlocked = false
    local recoveryClient = AviationCore and AviationCore.AirborneRecoveryClient or nil
    if recoveryClient and type(recoveryClient.IsFlightBlocked) == "function" then
        local ok, v = pcall(function() return recoveryClient.IsFlightBlocked(vehicle) end)
        recoveryBlocked = ok and v == true
    end
    local groundVariant = false
    if HelicopterGroundDrive and HelicopterGroundDrive.IsGroundVariant then
        local ok, v = pcall(function() return HelicopterGroundDrive.IsGroundVariant(vehicle) end)
        groundVariant = ok and v == true
    end
    local key = table.concat({ tostring(seat), tostring(running), tostring(started),
        tostring(recoveryBlocked), tostring(groundVariant), tostring(md and md.heliRotorStartPhase) }, "|")
    local periodic = now <= 0 or _mpRuntimeEntryDiag.lastMs <= 0 or
        (now - _mpRuntimeEntryDiag.lastMs) >= 250
    if key == _mpRuntimeEntryDiag.lastKey and not periodic then return end
    _mpRuntimeEntryDiag.lastKey = key
    _mpRuntimeEntryDiag.lastMs = now
    print(string.format(
        "[AviationCore][MP_RUNTIME_ENTRY] vehicleId=%s heliType=%s seat=%s validSeat0=%s recoveryBlocked=%s groundVariant=%s engineRunning=%s engineStarted=%s rotorRPM=%s phase=%s playerZ=%s vehicleZ=%s",
        tostring(safeValueCall(vehicle, "getId", "nil")), tostring(heliType), tostring(seat),
        tostring(seat == 0), tostring(recoveryBlocked), tostring(groundVariant),
        tostring(running), tostring(started), tostring(md and md.rotorRPM),
        tostring(md and md.heliRotorStartPhase), tostring(safeValueCall(playerObj, "getZ", "nil")),
        tostring(safeValueCall(vehicle, "getZ", "nil"))))
end

local function helicopterMovementUpdate()
    local playerObj = solFlightPilot()
    if not playerObj then return end
    local vehicle = playerObj:getVehicle()
    if vehicle then mpRuntimeEntryLog(playerObj, vehicle) end
    local recoveryClient = AviationCore and AviationCore.AirborneRecoveryClient or nil
    if recoveryClient and type(recoveryClient.IsRecoveryArmed) == "function"
            and recoveryClient.IsRecoveryArmed(vehicle)
            and type(recoveryClient.ObserveFlightRuntimeReadiness) == "function" then
        recoveryClient.ObserveFlightRuntimeReadiness(
            playerObj, vehicle, "FlightRuntime.OnTick.engine_restored")
    end
    if not checkValid(playerObj, vehicle) then
        if _flightState ~= STATE_INACTIVE then
            -- Was flying, now invalid (seat switch, exit, etc.) — clear ghost mode
            FlightAuxiliary.cleanup(playerObj)
        end
        _flightState = STATE_INACTIVE
        _dualPathActive = false
        return
    end

    local recoveryRebase = recoveryClient
        and type(recoveryClient.ConsumeFlightRebase) == "function"
        and recoveryClient.ConsumeFlightRebase(vehicle) or nil
    if recoveryRebase then
        -- Rebase only transient controller history.  Native engine state,
        -- rotor RPM, fuel, parts, inventory and occupants remain untouched.
        if VelocityAdapter and VelocityAdapter.resetSmoothing then
            VelocityAdapter.resetSmoothing()
        end
        if ForceAdapter and ForceAdapter.resetPhysicsTime then
            ForceAdapter.resetPhysicsTime()
        end
        if FlightContext and FlightContext.resetTransientState then
            FlightContext.resetTransientState()
        end
        FlightService.initFlightAfterRecovery(vehicle, recoveryRebase.verticalState)
        _flightState = STATE_WARMUP
        _dualPathActive = false
    end

    markAviationFrame("OnTick")

    -- Prevent CarController speed regulation from fighting our forces.
    vehicle:setMaxSpeed(FlightConfig.MAX_SPEED_OVERRIDE)

    -- Flight state initialization (first frame entering flight)
    -- Must run BEFORE FlightContext.build() so velocity adapter is reset before first read.
    local engineRunning = vehicle:isEngineRunning()
    if _flightState == STATE_INACTIVE and engineRunning then
        FlightService.resetFlightState()
        FlightService.initFlight(vehicle)
        for _, fn in ipairs(_initCallbacks) do fn(vehicle) end
        _flightState = STATE_WARMUP
    end

    -- Build per-frame context (keys, velocity, terrain, wall blocking)
    -- Runs after reset so VelocityAdapter starts clean on first flight frame.
    --- @type FlightContextData
    local ctx = FlightContext.build(vehicle, playerObj, scratchVector)
    local currentAltitude = ctx.currentAltitude
    local groundLevelZ = ctx.groundLevelZ
    local keys = ctx.keys
    local velX = ctx.velX
    local velY = ctx.velY
    local velZ = ctx.velZ
    local fpsMultiplier = ctx.fpsMultiplier
    local helicopterType = ctx.helicopterType
    local md = vehicle:getModData()
    md.currentGroundZ = groundLevelZ
    md.heliGroundDriveActive = false

    -- Persist the same geometric airborne decision used by the flight router.
    -- The W-key takeoff bypass is intentionally excluded: persistence requires
    -- physical clearance above support, not merely an input request.
    local oldIsAirborne = (currentAltitude > groundLevelZ + FlightConfig.AIRBORNE_MARGIN)
    local correctedSkidAGL = FlightConfig.GetCorrectedSkidAGL(currentAltitude, groundLevelZ)
    local correctedIsAirborne = correctedSkidAGL > FlightConfig.GetCorrectedAirborneMargin()
    local geometricIsAirborne = oldIsAirborne
    if FlightConfig.IsGroundReferenceCorrectionEnabled() then
        geometricIsAirborne = correctedIsAirborne
    end
    logMpFlightState(playerObj, vehicle, ctx, geometricIsAirborne, engineRunning)
    AirbornePersistence.ObserveFlightState(
        vehicle, geometricIsAirborne, currentAltitude, ctx.rawFloorZ)
    if recoveryAcceptanceDiagnosticsEnabled() and recoveryClient and
            type(recoveryClient.RecordPostRecoveryState) == "function" then
        recoveryClient.RecordPostRecoveryState(vehicle, ctx, geometricIsAirborne)
    end

    -- Ghost mode + Z-level for all occupants
    FlightAuxiliary.updateGhostMode(playerObj, currentAltitude, vehicle)

    -- Warmup: re-anchor sim to actual position each frame until physics stabilizes.
    if _flightState == STATE_WARMUP then
        FlightService.tickWarmup()
        FlightService.initFlight(vehicle)
        _dualPathActive = false
        if FlightService.isWarmedUp() then
            _flightState = STATE_AIRBORNE
        end
    end

    -- NightLight is a vehicle-light presentation, not an engine-running effect.
    -- Update it before the engine-off early return so F/headlights work with the
    -- engine stopped as well (matching normal vehicle-light behaviour).
    FlightAuxiliary.updateNightLight(playerObj, vehicle, groundLevelZ)

    -- Fuel accounting also observes the engine-off state so its continuous
    -- interval is rebased during shutdown instead of spanning a later restart.
    FlightAuxiliary.consumeGas(vehicle, currentAltitude, fpsMultiplier, helicopterType, ctx,
        "FlightRuntime.OnTick.preEngineBranch")

    -- === ENGINE OFF PATH ===
    -- Framework-level fall (engine-agnostic): simple PD toward fall speed, no gravity comp.
    if not engineRunning then
        _flightState = STATE_INACTIVE
        _dualPathActive = false
        md.rotorIntendedMoveX = 0
        md.rotorIntendedMoveY = 0
        md.rotorPendingImpact = false
        md.rotorPendingDirX = nil
        md.rotorPendingDirY = nil
        md.rotorPendingSpeed = nil
        md.rotorPendingHitXKind = nil
        md.rotorPendingHitYKind = nil
        md.rotorHandoffProducerFrame = nil
        md.rotorHandoffProducerSerial = nil
        md.rotorHandoffSource = "engine_stopped_reset"
        md.rotorHandoffValid = false
        md.rotorHandoffResetReason = "engine_stopped"
        if RotorDamageHandoff and RotorDamageHandoff.reset then
            RotorDamageHandoff.reset(vehicle, "engine_stopped")
        end
        if currentAltitude > groundLevelZ then
            local fallSpeed = FlightConfig.GetEngineOffFallSpeed()
            local fallGain = FlightConfig.GetFallPdGain()
            md.currentLiftVelocity = -fallSpeed
            if ctx.subSteps > 0 then
                local fallForceY = fallGain * (-fallSpeed - velY) * ctx.mass
                if fallForceY ~= 0 then
                    ForceAdapter.applyForceImmediate(vehicle, 0, fallForceY, 0, {
                        source = "engine_off_fall",
                        caller = "FlightRuntime.helicopterMovementUpdate",
                        phase = "ENGINE_OFF",
                        mode = "FALL",
                        groundState = "airborne",
                        w = keys.w == true,
                        s = keys.s == true,
                        agl = currentAltitude - groundLevelZ,
                        rawVelY = velY,
                        pitch = ctx.angleZ,
                        roll = ctx.angleX,
                        yaw = ctx.angleY,
                    })
                end
            end
            if HeliDebug.logEnabled then
                HeliDebug.logEngineOff(currentAltitude, fallSpeed, velX, velY, velZ)
            end
        end
        return
    end

    logVehicleGroundAssumption(vehicle)

    -- Airborne threshold: relative to actual ground surface
    local isAirborne = geometricIsAirborne
    logGroundReferenceRouter(ctx, oldIsAirborne, correctedIsAirborne)
    if ASCEND_BYPASS_GROUND_TEST and keys.w and ctx.fuelPercent > 0 then
        isAirborne = true
    end

    local flightResult = nil

    -- === AIRBORNE PATH ===
    if isAirborne then
        if _flightState ~= STATE_WARMUP then
            _flightState = STATE_AIRBORNE
        end

        flightResult = FlightService.update(ctx)
        if recoveryAcceptanceDiagnosticsEnabled() and recoveryClient and
                type(recoveryClient.RecordPostRecoveryVerticalState) == "function" then
            recoveryClient.RecordPostRecoveryVerticalState(
                vehicle, ctx, isAirborne, FlightService.getDebugState())
        end
        publishRotorDamageHandoff(md, flightResult)
        md.currentLiftVelocity = flightResult.targetVelY or 0
        if flightResult.isBlockedHit then
            local impactSpeed = math.sqrt((md.rotorIntendedMoveX * md.rotorIntendedMoveX) + (md.rotorIntendedMoveY * md.rotorIntendedMoveY))
            md.rotorPendingImpact = impactSpeed > 0.0001
            md.rotorPendingDirX = md.rotorIntendedMoveX
            md.rotorPendingDirY = md.rotorIntendedMoveY
            md.rotorPendingSpeed = impactSpeed
            md.rotorPendingHitXKind = "wall"
            md.rotorPendingHitYKind = "wall"
        else
            md.rotorPendingImpact = false
            md.rotorPendingDirX = nil
            md.rotorPendingDirY = nil
            md.rotorPendingSpeed = nil
            md.rotorPendingHitXKind = nil
            md.rotorPendingHitYKind = nil
        end

        -- Wall damage (rate-limited)
        if flightResult.isBlockedHit then
            if _wallDamageTick > 0 then
                _wallDamageTick = _wallDamageTick - 1
            else
                _wallDamageTick = math.floor(FlightConfig.GetWallDamageInterval() * getAverageFPS() / 60)
                FlightAuxiliary.applyWallDamage(vehicle)
            end
        end

        -- Update canonical actual-world speed telemetry for both HUD APIs.
        local actualGroundSpeedKmh = tonumber(flightResult.actualGroundSpeedKmh)
            or tonumber(flightResult.telemetrySpeed) or 0
        Heli_GlobalSpeed = actualGroundSpeedKmh
        Helicopter_GlobalSpeed = actualGroundSpeedKmh
        Heli_GlobalHeading = vehicle:getAngleZ()
        md.heliActualGroundSpeedMps = tonumber(flightResult.actualGroundSpeedMps) or (actualGroundSpeedKmh / 3.6)
        md.heliActualGroundSpeedKmh = actualGroundSpeedKmh
        md.heliBulletGroundSpeedMps = tonumber(flightResult.bulletGroundSpeedMps) or 0
        md.heliSimulatedGroundSpeedMps = tonumber(flightResult.simulatedGroundSpeedMps) or 0
        md.heliTargetGroundSpeedMps = tonumber(flightResult.targetGroundSpeedMps) or 0

    -- === GROUND PATH ===
    else
        local groundResult = FlightService.updateGround(ctx)
        if recoveryAcceptanceDiagnosticsEnabled() and recoveryClient and
                type(recoveryClient.RecordPostRecoveryVerticalState) == "function" then
            recoveryClient.RecordPostRecoveryVerticalState(
                vehicle, ctx, isAirborne, FlightService.getDebugState())
        end
        md.rotorIntendedMoveX = 0
        md.rotorIntendedMoveY = 0
        md.rotorHandoffProducerFrame = nil
        md.rotorHandoffProducerSerial = nil
        md.rotorHandoffSource = "grounded_reset"
        md.rotorHandoffValid = false
        md.rotorHandoffResetReason = "grounded"
        md.currentLiftVelocity = 0
        md.rotorPendingImpact = false
        md.rotorPendingDirX = nil
        md.rotorPendingDirY = nil
        md.rotorPendingSpeed = nil
        md.rotorPendingHitXKind = nil
        md.rotorPendingHitYKind = nil
        Heli_GlobalSpeed = 0
        Helicopter_GlobalSpeed = 0
        md.heliActualGroundSpeedMps = 0
        md.heliActualGroundSpeedKmh = 0
        md.heliBulletGroundSpeedMps = 0
        md.heliSimulatedGroundSpeedMps = 0
        md.heliTargetGroundSpeedMps = 0

        -- Engine ground handlers can request flight state preservation across
        -- the ground phase (e.g. Flight keeps sim/orientation alive in transition zone).
        if not groundResult.keepFlightState then
            _flightState = STATE_INACTIVE
        end

        vehicle:setSpeedKmHour(groundResult.displaySpeed)
        _dualPathActive = false
        return
    end

    -- === BELOW HERE: AIRBORNE ONLY ===

    -- Engine dead: shut off engine (gameplay side-effect, framework responsibility)
    if flightResult.engineDead and vehicle:isEngineRunning() then
        ISVehicleMenu.onShutOff(playerObj)
    end

    -- Dual-path activation (from engine results)
    _dualPathActive = flightResult.dualPathActive

    -- Display speed
    vehicle:setSpeedKmHour(flightResult.displaySpeed)

    -- === KEY STATE (shared by debug + recorder) ===
    local keyStr = nil
    if HeliDebug.logEnabled or HeliDebug.snapRequested or HeliDebug.isRecording() then
        keyStr = ""
        if keys.up then keyStr = keyStr .. "U" end
        if keys.down then keyStr = keyStr .. "D" end
        if keys.left then keyStr = keyStr .. "L" end
        if keys.right then keyStr = keyStr .. "R" end
        if keys.w then keyStr = keyStr .. "W" end
        if keys.s then keyStr = keyStr .. "S" end
        if keys.a then keyStr = keyStr .. "a" end
        if keys.d then keyStr = keyStr .. "d" end
        if keyStr == "" then keyStr = "-" end
    end

    -- === DEBUG LOGGING ===
    if HeliDebug.logEnabled or HeliDebug.snapRequested then
        local fps = getAverageFPS()
        local subSteps = 1.0 / (math.max(fps, 10) * 0.01)

        HeliDebug.captureState({
            state = _flightState,
            currentAltitude = currentAltitude,
            groundLevelZ = groundLevelZ,
            desiredVelX = flightResult.desiredVelX,
            desiredVelZ = flightResult.desiredVelZ,
            simVelX = flightResult.simVelX,
            simVelZ = flightResult.simVelZ,
            posErrorX = flightResult.errX,
            posErrorZ = flightResult.errZ,
            posErrorRateX = flightResult.errRateX,
            posErrorRateZ = flightResult.errRateZ,
            savedVelY = velY,
            gravComp = flightResult.gravComp,
            engineDead = flightResult.engineDead,
            noHInput = flightResult.noHInput,
            freeMode = flightResult.freeMode,
            blocked = flightResult.isBlockedHit,
            fps = fps,
            subSteps = subSteps,
            mass = vehicle:getMass(),
            keys = keyStr,
        })

        HeliDebug.periodicLog(_flightState, currentAltitude, flightResult.desiredVelX or 0, flightResult.desiredVelZ or 0,
            flightResult.simVelX or 0, flightResult.simVelZ or 0, flightResult.errX or 0, flightResult.errZ or 0, velY, keyStr)

        if HeliDebug.snapRequested then
            HeliDebug.snapRequested = false
        end
    end

    -- === FLIGHT DATA RECORDER ===
    -- Read raw Bullet velocity directly (don't call getVelocity() again —
    -- it has stateful side effects that corrupt stale-read detection).
    if HeliDebug.isRecording() then
        local dbg = FlightService.getDebugState()
        local recordingVelocity = vehicle:getLinearVelocity(Vector3f.new())
        HeliDebug.writeFlightFrame({
            ms          = getTimestampMs(),
            state       = _flightState,
            fps         = getAverageFPS(),
            actualX     = FlightUtilities.toLuaNum(vehicle:getX()),
            actualZ     = FlightUtilities.toLuaNum(vehicle:getY()),
            alt         = currentAltitude,
            velocityX   = FlightUtilities.toLuaNum(recordingVelocity:x()),
            velocityY   = FlightUtilities.toLuaNum(recordingVelocity:y()),
            velocityZ   = FlightUtilities.toLuaNum(recordingVelocity:z()),
            simPosX     = dbg.simPosX or 0,
            simPosZ     = dbg.simPosZ or 0,
            simVelX     = dbg.simVelX or 0,
            simVelZ     = dbg.simVelZ or 0,
            errorX      = dbg.errX or 0,
            errorZ      = dbg.errZ or 0,
            desiredVelX = flightResult.desiredVelX or 0,
            desiredVelZ = flightResult.desiredVelZ or 0,
            desiredVelY = flightResult.targetVelY or 0,
            subSteps    = ForceAdapter.getLastSubSteps(),
            tilt        = flightResult.hasHInput,
            flightAssistOff = flightResult.freeMode,
            yawSimulated = FlightService.getIntendedYaw() or 0,
            yawActual   = FlightUtilities.toLuaNum(vehicle:getAngleY()),
            gravComp    = flightResult.gravComp,
            dualPath    = _dualPathActive,
            keys        = keyStr or "-",
        })
    end

end

-------------------------------------------------------------------------------------
-- Exit vehicle handler
-------------------------------------------------------------------------------------
local function helicopterExit(player)
    local vehicle = player:getVehicle()
    if vehicle == nil then return end
    if not AviationCore.GetHelicopterType(vehicle) then return end

    -- Any occupant exiting: clear their ghost mode + Z
    if player:isGhostMode() and not player:isGodMod() then
        player:setGhostMode(false)
    end
    player:setZ(0)

    -- Pilot-only cleanup: flight state, debug, callbacks
    local seat = vehicle:getSeat(player)
    if seat == 0 then
        if HeliDebug.isRecording() then
            HeliDebug.stopRecording()
        end
        FlightAuxiliary.cleanup(player)
        for _, fn in ipairs(_cleanupCallbacks) do fn(player, vehicle) end
        _dualPathActive = false
        _flightState = STATE_INACTIVE
    end
end

-------------------------------------------------------------------------------------
-- Black zone warning (world boundary check)
-------------------------------------------------------------------------------------
local function checkBlackZone()
    local player = getPlayer()
    if not player then return end
    local vehicle = player:getVehicle()
    if not vehicle or not AviationCore.GetHelicopterType(vehicle) then return end

    local playerX, playerY = player:getX(), player:getY()
    local dist = FlightConfig.BLACK_ZONE_CHECK_DISTANCE
    local directions = {
        { x = playerX + dist, y = playerY },
        { x = playerX - dist, y = playerY },
        { x = playerX, y = playerY + dist },
        { x = playerX, y = playerY - dist },
    }
    for _, dir in ipairs(directions) do
        local square = getCell():getGridSquare(dir.x, dir.y, 0)
        if not square then
            player:Say(getText("IGUI_BlackZoneWarn"))
            vehicle:playSound("JetAlarm")
            return
        end
    end
end

-------------------------------------------------------------------------------------
-- OnTickEvenPaused: Apply CORRECTION forces (0-frame delay path).
-------------------------------------------------------------------------------------
local function helicopterCorrectionUpdate()
    if not _dualPathActive then return end

    if GameClient and not GameClient.client then
        local sc = UIManager and UIManager.getSpeedControls and UIManager.getSpeedControls()
        if sc and sc:getCurrentGameSpeed() == 0 then return end
    end

    local playerObj = solFlightPilot()
    if not playerObj then return end
    local vehicle = playerObj:getVehicle()
    if not vehicle then return end
    if not AviationCore.GetHelicopterType(vehicle) then return end
    markAviationFrame("OnTickEvenPaused")

    --- @type CorrectionContext
    local cctx = CorrectionContext.build(vehicle)
    FlightService.applyCorrectionForces(cctx)
end

-------------------------------------------------------------------------------------
-- Event registration
-------------------------------------------------------------------------------------
Events.OnTickEvenPaused.Add(helicopterCorrectionUpdate)
Events.OnTick.Add(helicopterMovementUpdate)
Events.OnExitVehicle.Add(helicopterExit)
Events.EveryOneMinute.Add(checkBlackZone)

SolAviationRuntimeBridgeReady = true

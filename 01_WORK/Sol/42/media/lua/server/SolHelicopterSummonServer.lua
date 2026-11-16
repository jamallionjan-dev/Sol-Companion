-- Server-authoritative helicopter request for Sol's Mind command.
-- Only registered AviationCore helicopters may spawn; the server chooses the
-- location, validates the footprint, fills JetFuel and creates the ignition key.
if type(isClient) == "function" and isClient() == true then return end

local AircraftRegistry = require "AviationCore/AircraftRegistry"
local AircraftFactoryParts = require "AviationCore/AircraftFactoryParts"
local OperatorManuals = require "AviationCore/OperatorManuals"

SolHelicopterSummonServer = SolHelicopterSummonServer or {}
local S = SolHelicopterSummonServer
local MODULE = "SolHelicopter"
local lastRequestByPlayer = {}

local function invoke(object, name, ...)
    if not object then return nil, false end
    local ok, fn = pcall(function() return object[name] end)
    if not ok or type(fn) ~= "function" then return nil, false end
    local called, value = pcall(fn, object, ...)
    return called and value or nil, called
end

-- invoke() also returns a success flag; capture only its first return before
-- passing values to Kahlua's tonumber (whose second argument is a string base).
local function numberMethod(object, name, ...)
    local value = invoke(object, name, ...)
    return tonumber(value)
end

local function log(message)
    print("[SolHeliSpawn] " .. tostring(message))
end

local function playerKey(player)
    local id = invoke(player, "getOnlineID")
    if id ~= nil then return tostring(id) end
    local username = invoke(player, "getUsername")
    return tostring(username or player)
end

local function reply(player, ok, reason, script, x, y)
    if type(sendServerCommand) == "function" then
        pcall(sendServerCommand, player, MODULE, "summon_result", {
            ok = ok == true, reason = tostring(reason or ""), vehicleScript = tostring(script or ""),
            x = tonumber(x), y = tonumber(y),
        })
    end
end

local function safeSquare(square)
    if not square then return false end
    local room = invoke(square, "getRoom")
    local building = invoke(square, "getBuilding")
    if room ~= nil or building ~= nil then return false end
    if invoke(square, "isOutside") ~= true then return false end
    if invoke(square, "TreatAsSolidFloor") ~= true then return false end
    if invoke(square, "isSolid") == true or invoke(square, "isSolidTrans") == true then return false end
    if invoke(square, "isSafeToSpawn") ~= true then return false end
    if invoke(square, "isFree", true) ~= true then return false end
    return true
end

local function footprintRadius(aircraft)
    local size = string.lower(tostring(aircraft and aircraft.size or "medium"))
    if size == "small" then return 1 end
    if size == "large" then return 3 end
    return 2
end

local function clearFootprint(cell, x, y, z, radius)
    for dx = -radius, radius do
        for dy = -radius, radius do
            local square = invoke(cell, "getGridSquare", x + dx, y + dy, z)
            if not safeSquare(square) then return false end
        end
    end
    return true
end

local function existingVehicleTooClose(cell, x, y, radius)
    local vehicles = invoke(cell, "getVehicles")
    local count = vehicles and invoke(vehicles, "size") or 0
    for i = 0, (tonumber(count) or 0) - 1 do
        local vehicle = invoke(vehicles, "get", i)
        if vehicle then
            local vx, vy = numberMethod(vehicle, "getX"), numberMethod(vehicle, "getY")
            if vx and vy and math.abs(vx - x) <= radius + 4 and math.abs(vy - y) <= radius + 4 then
                return true
            end
        end
    end
    return false
end

local function findSpawnSquare(player, aircraft)
    if type(getCell) ~= "function" then return nil, "cell_unavailable" end
    local cell = getCell()
    if not cell then return nil, "cell_unavailable" end
    local px, py = numberMethod(player, "getX"), numberMethod(player, "getY")
    local pz = math.floor(numberMethod(player, "getZ") or 0)
    if not px or not py then return nil, "player_position_unavailable" end
    local radius = footprintRadius(aircraft)
    local baseX, baseY = math.floor(px), math.floor(py)
    -- One bounded search, only after a command. It starts far enough from the
    -- caller to avoid appearing on top of them and tests the aircraft footprint.
    for distance = 10, 34, 3 do
        for step = 0, 15 do
            local angle = step * math.pi / 8
            local x = baseX + math.floor(math.cos(angle) * distance + 0.5)
            local y = baseY + math.floor(math.sin(angle) * distance + 0.5)
            if clearFootprint(cell, x, y, pz, radius)
                and not existingVehicleTooClose(cell, x, y, radius) then
                return { x = x, y = y, z = pz }, nil
            end
        end
    end
    return nil, "no_safe_clear_landing_area_nearby"
end

local function configureVehicle(vehicle)
    if not vehicle then return false, "vehicle_creation_failed" end
    invoke(vehicle, "setKeyIsOnDoor", false)
    local key = invoke(vehicle, "getCurrentKey")
    if not key then key = invoke(vehicle, "createVehicleKey") end
    if key then
        invoke(vehicle, "setCurrentKey", key)
        invoke(vehicle, "setKeysInIgnition", true)
    end

    if AircraftFactoryParts and type(AircraftFactoryParts.FinalizeVehicle) == "function" then
        local ok, finalized, reason = pcall(AircraftFactoryParts.FinalizeVehicle,
            vehicle, "SolHelicopterSummon")
        if not ok or finalized ~= true then
            log("factory part finalization failed: " .. tostring(ok and reason or finalized))
        end
    else
        log("factory part finalizer unavailable")
    end
    if OperatorManuals and type(OperatorManuals.FinalizeVehicleManual) == "function" then
        local ok, finalized, reason = pcall(OperatorManuals.FinalizeVehicleManual,
            vehicle, nil, "SolHelicopterSummon")
        if not ok or (finalized ~= true and reason ~= "unregistered_vehicle") then
            log("operator manual finalization failed: " .. tostring(ok and reason or finalized))
        end
    else
        log("operator manual finalizer unavailable")
    end

    local tank = invoke(vehicle, "getPartById", "GasTank")
    if not tank or invoke(tank, "isContainer") ~= true
        or tostring(invoke(tank, "getContainerContentType") or "") ~= "JetFuel" then
        invoke(vehicle, "permanentlyRemove")
        return false, "jet_fuel_tank_unavailable"
    end
    local capacity = numberMethod(tank, "getContainerCapacity")
    if not capacity or capacity <= 0 then
        invoke(vehicle, "permanentlyRemove")
        return false, "jet_fuel_capacity_unavailable"
    end
    local _, filled = invoke(tank, "setContainerContentAmount", capacity)
    invoke(vehicle, "transmitPartModData", tank)
    invoke(vehicle, "transmitPartItem", tank)
    local amount = numberMethod(tank, "getContainerContentAmount")
    if not filled or not amount or amount + 0.01 < capacity then
        invoke(vehicle, "permanentlyRemove")
        return false, "jet_fuel_fill_unverified"
    end
    return true, "ready_full_jetfuel"
end

function S.spawn(player, args)
    if not player then return false, "player_unavailable" end
    local requestKey = playerKey(player)
    local now
    if type(getTimestampMs) == "function" then
        local clockOk, clockValue = pcall(getTimestampMs)
        if clockOk then now = tonumber(clockValue) end
    end
    if not now then now = os and type(os.time) == "function" and os.time() * 1000 or 0 end
    if now - (tonumber(lastRequestByPlayer[requestKey]) or -100000) < 5000 then
        return false, "summon_cooldown"
    end
    lastRequestByPlayer[requestKey] = now

    local requested = type(args) == "table" and args.vehicleScript or nil
    local script = type(requested) == "string" and requested or "Base.UH1BHuey"
    local registry = AircraftRegistry or (AviationCore and AviationCore.AircraftRegistry)
    local aircraft = registry and registry.GetAircraft(script) or nil
    if not aircraft or aircraft.category ~= "helicopter" then
        script, aircraft = "Base.UH1BHuey", registry and registry.GetAircraft("Base.UH1BHuey") or nil
    end
    if not aircraft or aircraft.category ~= "helicopter" then return false, "registered_helicopter_not_found" end
    if type(getScriptManager) ~= "function" then return false, "vehicle_script_manager_unavailable" end
    local manager = getScriptManager()
    local vehicleScript = manager and invoke(manager, "getVehicle", aircraft.vehicleScript)
    if not vehicleScript then return false, "vehicle_script_missing:" .. tostring(aircraft.vehicleScript) end

    local point, why = findSpawnSquare(player, aircraft)
    if not point then return false, why end
    if type(addVehicle) ~= "function" then return false, "server_vehicle_factory_unavailable" end
    local ok, vehicle = pcall(addVehicle, aircraft.vehicleScript, point.x, point.y, point.z)
    if not ok or not vehicle then return false, "vehicle_creation_failed" end
    local ready, readyReason = configureVehicle(vehicle)
    if not ready then return false, readyReason end
    log(string.format("spawned script=%s at=%d,%d,%d fuel=full", aircraft.vehicleScript, point.x, point.y, point.z))
    return true, readyReason, aircraft.vehicleScript, point.x, point.y
end

function S.onClientCommand(module, command, player, args)
    if module ~= MODULE or command ~= "summon" then return end
    local ok, reason, script, x, y = S.spawn(player, args)
    log(string.format("request result ok=%s reason=%s script=%s", tostring(ok), tostring(reason), tostring(script or "")))
    reply(player, ok, reason, script, x, y)
end

local event = Events and Events.OnClientCommand
if event and type(event.Add) == "function" then
    if S.registeredHandler and type(event.Remove) == "function" then pcall(event.Remove, S.registeredHandler) end
    event.Add(S.onClientCommand)
    S.registeredHandler = S.onClientCommand
    log("server request listener ready")
else
    log("server request listener unavailable")
end

return S

-- SPDX-License-Identifier: MIT
SurvivorCompanion = SurvivorCompanion or {}
local SC = SurvivorCompanion
SC.AIPerceptionAdapter = SC.AIPerceptionAdapter or {}
local A = SC.AIPerceptionAdapter

A.PROTOCOL = "sol-ai-1"
A.SCHEMA = 1
A.MAX_THREATS = 16

local function safe(module, name, ...)
    if type(module) ~= "table" or type(module[name]) ~= "function" then return nil end
    local ok, value = pcall(module[name], ...)
    if ok then return value end
    return nil
end

local function call(object, name)
    if object == nil or type(object[name]) ~= "function" then return nil end
    local ok, value = pcall(object[name], object)
    if ok then return value end
    return nil
end

local function position(object)
    if object == nil then return nil end
    local x = call(object, "getX")
    local y = call(object, "getY")
    local z = call(object, "getZ")
    if type(x) ~= "number" or type(y) ~= "number" then return nil end
    return { x = x, y = y, z = type(z) == "number" and z or 0 }
end

local function compactVehicle(actor)
    if actor == nil then return nil end
    local vehicle = call(actor, "getVehicle")
    if vehicle == nil then return nil end
    local sqlId = call(vehicle, "getSqlId")
    if type(sqlId) ~= "number" or sqlId < 0 or sqlId ~= math.floor(sqlId) then return nil end
    local script = call(vehicle, "getScriptName")
    local seat = call(actor, "getVehicleSeat")
    return {
        sqlId = sqlId,
        script = script ~= nil and tostring(script) or nil,
        seat = type(seat) == "number" and seat or nil,
    }
end
local function compactThreat(entry, origin)
    if type(entry) ~= "table" then return nil end
    local p
    if type(entry.x) == "number" and type(entry.y) == "number" then
        p = { x = entry.x, y = entry.y, z = type(entry.z) == "number" and entry.z or 0 }
    else
        p = position(entry.actor)
    end
    if p == nil then return nil end
    local distance = entry.distance
    if type(distance) ~= "number" and origin ~= nil then
        local dx = p.x - origin.x
        local dy = p.y - origin.y
        distance = math.sqrt(dx * dx + dy * dy)
    end
    local zombieId = nil
    if entry.actor ~= nil and type(SC.GameplayUtil) == "table"
        and type(SC.GameplayUtil.isZombie) == "function"
        and type(SC.GameplayUtil.idOf) == "function"
        and SC.GameplayUtil.isZombie(entry.actor) then
        zombieId = tostring(SC.GameplayUtil.idOf(entry.actor))
    end
    return {
        zombieId = zombieId,
        x = p.x,
        y = p.y,
        z = p.z,
        distance = distance,
        visible = entry.visible ~= false,
        obstructed = entry.obstructed == true,
        grounded = entry.grounded == true,
        fenced = entry.fenced == true,
        breaching = entry.breaching == true,
        targeting = entry.targeting == true,
        attacking = entry.attacking == true,
        posture = type(entry.posture) == "string" and entry.posture or nil,
        score = type(entry.score) == "number" and entry.score or nil,
    }
end
local function compactThreats(source, origin)
    local result = {}
    if type(source) ~= "table" then return result end
    for _, entry in ipairs(source) do
        if #result >= A.MAX_THREATS then break end
        local clean = compactThreat(entry, origin)
        if clean ~= nil then result[#result + 1] = clean end
    end
    return result
end

-- Parked vehicles Sol can actually see. Without this the brain is blind to
-- every car in the street and can only report the one she already sits in.
A.MAX_VEHICLES = 8
A.VEHICLE_RADIUS = 40

-- Collect elements from whatever the engine handed us. The shape is decided
-- ONCE rather than guessed per element: getVehicles() returns a plain array
-- here, and calling :get on it throws, which halted the game in v2.0.
local function collect(list, maximum)
    local out = {}
    if list == nil then return out end
    maximum = maximum or 64
    -- v2.2: decide the shape WITHOUT provoking an error. Probing with a
    -- failing list:get(0) inside pcall was caught, but debug mode breaks on
    -- every error, so v2.1 halted the game on each perception tick.
    if type(list) == "table" then
        local first = (list[0] ~= nil) and 0 or 1
        for i = first, first + maximum - 1 do
            local value = list[i]
            if value == nil then break end
            out[#out + 1] = value
        end
        return out
    end
    local size = call(list, "size")
    if type(size) ~= "number" or size <= 0 then return out end
    if type(list.get) ~= "function" then return out end
    for i = 0, math.min(size, maximum) - 1 do
        local got, value = pcall(list.get, list, i)
        if got and value ~= nil then out[#out + 1] = value end
    end
    return out
end

local function vehicleSummary(vehicle, origin)
    if vehicle == nil then return nil end
    local p = position(vehicle)
    if p == nil then return nil end
    local dx, dy = p.x - origin.x, p.y - origin.y
    local distance = math.sqrt(dx * dx + dy * dy)
    if distance > A.VEHICLE_RADIUS then return nil end
    local sqlId = call(vehicle, "getSqlId")
    if type(sqlId) ~= "number" or sqlId < 0 or sqlId ~= math.floor(sqlId) then
        return nil
    end
    local script = call(vehicle, "getScriptName")
    local driver = call(vehicle, "getDriver")
    local engine = call(vehicle, "isEngineRunning")
    local fuel = call(vehicle, "getFluidAmount")
    local battery = call(vehicle, "getBatteryCharge")
    local locked = call(vehicle, "isAllDoorsLocked")
    return {
        sqlId = sqlId,
        script = script ~= nil and tostring(script) or nil,
        x = p.x, y = p.y, z = p.z,
        distance = distance,
        occupied = driver ~= nil,
        engineRunning = engine == true,
        fuel = type(fuel) == "number" and fuel or nil,
        battery = type(battery) == "number" and battery or nil,
        locked = locked == true,
    }
end

local function nearbyVehicles(origin)
    local result = {}
    local service = SC.Vehicle
    if type(service) ~= "table" or type(service.loadedVehicles) ~= "function" then
        return result
    end
    local ok, vehicles = pcall(service.loadedVehicles)
    if not ok or type(vehicles) ~= "table" then return result end
    for _, vehicle in ipairs(vehicles) do
        if #result >= A.MAX_VEHICLES then break end
        local entry = vehicleSummary(vehicle, origin)
        if entry ~= nil then result[#result + 1] = entry end
    end
    table.sort(result, function(a, b) return a.distance < b.distance end)
    return result
end

function A.cached(actor, runtime)
    local senses = safe(SC.Senses, "cached", actor, runtime)
    if type(senses) == "table" then return senses end
    if type(runtime) == "table"
        and type(runtime.senses) == "table"
        and type(runtime.senses.current) == "table" then
        return runtime.senses.current
    end
    return nil
end

function A.snapshot(actor, player, runtime)
    if actor == nil then return nil, "actor_missing" end
    local senses = A.cached(actor, runtime)
    if type(senses) ~= "table" then return nil, "senses_missing" end

    local origin = position(actor)
    if origin == nil then return nil, "position_missing" end

    local command = safe(SC.Commands, "peek", actor)
    local action = safe(SC.ActionSupervisor, "summary", actor)
    local navigation = safe(SC.Navigation, "status", actor)

    return {
        protocol = A.PROTOCOL,
        schema = A.SCHEMA,
        capturedAtMs = senses.reflexTime or senses.time,
        sol = {
            name = "Sol",
            position = origin,
            currentVehicle = compactVehicle(actor),
            indoors = senses.indoors == true,
            order = type(command) == "table" and command.order or nil,
            action = type(action) == "table" and {
                active = action.active == true,
                phase = action.phase,
                owner = action.owner,
                action = action.action,
                reason = action.reason,
                targetKey = action.targetKey,
            } or nil,
            navigation = type(navigation) == "table" and {
                active = navigation.active == true,
                phase = navigation.phase,
                action = navigation.action,
                target = navigation.target,
                pathReason = navigation.pathReason,
                pathFailureClass = navigation.pathFailureClass,
                terminalReason = navigation.terminalReason,
            } or nil,
        },
        player = {
            position = position(player),
            currentVehicle = compactVehicle(player),
            health = type(senses.player) == "table" and senses.player.health or nil,
            danger = type(senses.player) == "table" and senses.player.danger or nil,
            immediateThreats = type(senses.player) == "table"
                and senses.player.immediateThreats or nil,
        },
        world = {
            vehicles = nearbyVehicles(origin),
            vehicleRadius = A.VEHICLE_RADIUS,
        },
        threats = {
            count = senses.threatCount or 0,
            immediateCount = senses.immediateCount or 0,
            pressure = senses.pressure or 0,
            directionalPressure = senses.directionalPressure or 0,
            encircled = senses.encircled == true,
            visible = compactThreats(senses.threats, origin),
            heard = compactThreats(senses.heardThreats, origin),
        },
        diagnostics = {
            scanComplete = senses.scanComplete == true,
            discoveryComplete = senses.scanDiscoveryComplete ~= false,
            visualComplete = senses.scanVisualComplete ~= false,
            threatOverflow = senses.threatOverflow == true,
            immediateOverflow = senses.immediateOverflow == true,
        },
    }, "snapshot_ready"
end

function A.health()
    return {
        protocol = A.PROTOCOL,
        schema = A.SCHEMA,
        senses = type(SC.Senses) == "table",
        commands = type(SC.Commands) == "table",
        supervisor = type(SC.ActionSupervisor) == "table",
        navigation = type(SC.Navigation) == "table",
    }
end

return A


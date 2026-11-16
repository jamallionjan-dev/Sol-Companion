-- SPDX-License-Identifier: MIT
SurvivorCompanion = SurvivorCompanion or {}
local SC = SurvivorCompanion

SC.AITargetResolver = SC.AITargetResolver or {}
local R = SC.AITargetResolver

R.VERSION = 1
R.MAX_ZOMBIES = 512

local function U()
    return SC.GameplayUtil
end

local function finite(value)
    value = tonumber(value)
    if value == nil or value ~= value or value == math.huge or value == -math.huge then
        return nil
    end
    return value
end

function R.resolveObject(reference)
    if type(reference) ~= "table" then
        return nil, "invalid_object_reference"
    end
    if not SC.BaseLife or type(SC.BaseLife.resolveObject) ~= "function" then
        return nil, "object_resolver_unavailable"
    end
    local object, reason = SC.BaseLife.resolveObject(reference)
    if object == nil then return nil, reason or "object_not_found" end
    return object
end

function R.describeObject(object, createIdentity)
    if object == nil then return nil, "object_missing" end
    if not SC.BaseLife or type(SC.BaseLife.describeObject) ~= "function" then
        return nil, "object_descriptor_unavailable"
    end
    return SC.BaseLife.describeObject(object, createIdentity == true)
end

function R.resolveDoor(reference)
    local object, reason = R.resolveObject(reference)
    if object == nil then return nil, reason end
    local utility = U()
    if not utility then return nil, "gameplay_util_unavailable" end
    local isDoor, checked = utility.call(object, "isDoor")
    if checked ~= true or isDoor ~= true then
        return nil, "object_is_not_door"
    end
    return object
end

function R.resolveVehicle(reference)
    local sqlId = reference
    if type(reference) == "table" then
        sqlId = reference.sqlId or reference.vehicleId
    end
    sqlId = finite(sqlId)
    if sqlId == nil or sqlId < 0 or sqlId ~= math.floor(sqlId) then
        return nil, "invalid_vehicle_sql_id"
    end
    if not SC.Vehicle or type(SC.Vehicle.loadedBySqlId) ~= "function" then
        return nil, "vehicle_resolver_unavailable"
    end
    local vehicle = SC.Vehicle.loadedBySqlId(sqlId)
    if vehicle == nil then return nil, "vehicle_not_loaded" end
    return vehicle
end

local function zombieList()
    local utility = U()
    if not utility or type(utility.cell) ~= "function" then
        return nil, "gameplay_util_unavailable"
    end
    local cell = utility.cell()
    if cell == nil then return nil, "cell_unavailable" end
    local list, ok = utility.call(cell, "getZombieList")
    if ok ~= true or list == nil then return nil, "zombie_list_unavailable" end
    return list
end

function R.resolveZombie(reference)
    local wanted = reference
    if type(reference) == "table" then
        wanted = reference.id or reference.zombieId
    end
    if wanted == nil then return nil, "invalid_zombie_id" end
    wanted = tostring(wanted)

    local utility = U()
    if not utility then return nil, "gameplay_util_unavailable" end
    local list, reason = zombieList()
    if list == nil then return nil, reason end

    local found = nil
    utility.each(list, R.MAX_ZOMBIES, function(candidate)
        if found ~= nil then return false end
        if utility.isZombie(candidate) and not utility.isDead(candidate)
            and tostring(utility.idOf(candidate)) == wanted then
            found = candidate
            return false
        end
        return true
    end)

    if found == nil then return nil, "zombie_not_found" end
    return found
end

function R.health()
    return {
        version = R.VERSION,
        objectResolver = SC.BaseLife ~= nil
            and type(SC.BaseLife.resolveObject) == "function",
        objectDescriptor = SC.BaseLife ~= nil
            and type(SC.BaseLife.describeObject) == "function",
        vehicleResolver = SC.Vehicle ~= nil
            and type(SC.Vehicle.loadedBySqlId) == "function",
        zombieResolver = U() ~= nil,
    }
end

return R

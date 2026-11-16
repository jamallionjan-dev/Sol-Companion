-- SolCarRules.lua - which cars Sol may even consider. Switch: car_eligible_only.
--   A car counts if it is unlocked, or a key for it is with her, with him or in the car, or it is hotwired. A locked car with no key is invisible to her.
SolUI = SolUI or {}
local U = SolUI
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
function U.solCarRulesOn()
    local A = rawget(_G, "SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("car_eligible_only") == true
end
local function anyDoorUnlocked(car)
    local doors, unlocked = 0, false
    for i = 0, (tonumber((call(car, "getPartCount"))) or 0) - 1 do
        local door = call(call(car, "getPartByIndex", i), "getDoor")
        if door ~= nil then
            doors = doors + 1
            if call(door, "isLocked") ~= true then unlocked = true end
        end
    end
    return doors == 0 or unlocked
end
local function keyHeld(who, id) return who ~= nil and call(call(who, "getInventory"), "haveThisKeyId", id) ~= nil end
local function keyInCar(car, id)
    for i = 0, (tonumber((call(car, "getPartCount"))) or 0) - 1 do
        local box = call(call(car, "getPartByIndex", i), "getItemContainer")
        if box ~= nil and call(box, "haveThisKeyId", id) ~= nil then return true end
    end
    return false
end
function U.solCarEligible(car, s, player)
    if car == nil then return false end
    if call(car, "isKeysInIgnition") == true or call(car, "isHotwired") == true then return true end
    if anyDoorUnlocked(car) then return true end
    local id = call(car, "getKeyId")
    if type(id) ~= "number" then return false end
    return keyHeld(s, id) or keyHeld(player, id) or keyInCar(car, id)
end
-- the car she goes for: the one he is in or just left, then the one she knows, then the nearest she may use. second value: there were cars, none usable
function U.solPickCar(vehicles, anchor, radius)
    local p = getSpecificPlayer and getSpecificPlayer(0) or nil
    local s = U.solActor and U.solActor() or nil
    local ax, ay = tonumber((call(anchor, "getX"))), tonumber((call(anchor, "getY")))
    if ax == nil then return nil, false end
    local reach2, best, bd, any = radius * radius, nil, radius * radius, false
    local function near(v)
        local x, y = tonumber((call(v, "getX"))), tonumber((call(v, "getY")))
        if x == nil then return nil end
        local d = (x - ax) ^ 2 + (y - ay) ^ 2
        return d <= reach2 and d or nil
    end
    local G = U.gps
    for _, first in ipairs({ call(p, "getVehicle") or false, U._lastPlayerCar or false, type(G) == "table" and G.lastDriveCar or false }) do
        if first and near(first) and call(first, "isRemovedFromWorld") ~= true and U.solCarEligible(first, s, p) then return first, false end
    end
    for _, v in ipairs(vehicles) do
        local d = near(v)
        if d then
            any = true
            if d < bd and U.solCarEligible(v, s, p) then best, bd = v, d end
        end
    end
    return best, best == nil and any
end
if Events and Events.OnTick then
    local at = 0
    Events.OnTick.Add(function()
        local t = getTimestampMs and getTimestampMs() or 0
        if t - at < 1000 then return end
        at = t
        local v = call(getSpecificPlayer and getSpecificPlayer(0) or nil, "getVehicle")
        if v ~= nil then U._lastPlayerCar = v end
    end)
end

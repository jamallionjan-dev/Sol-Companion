-- ---------------------------------------------------------------- far_car keys: a car she may take must be unlocked and she must be able to start it
--   Start: a key for it in the ignition, a key for it in her own things (her live inventory, else her saved record), a key for it inside it,
--   or hotwired with the wires whole. Unknown counts as no. Her own car is held to the same rule.
local function farCarOn()
    local A = rawget(_G, "SolAuthority")
    if type(A) ~= "table" or type(A.on) ~= "function" then return false end
    local ok, v = pcall(A.on, "far_car")
    return ok and v == true
end
-- a test for "she carries a key with this id"; when her things cannot be read, she has none
local function herKeys()
    local L = liveActor()
    local inv = L and call(L, "getInventory") or nil
    if inv ~= nil then
        return function(k)
            local ok, v = pcall(function() return inv:haveThisKeyId(k) end)        -- 42.22: Key items, keyrings and bags inside
            return ok and v ~= nil and v ~= false
        end
    end
    local P = persistence()
    if P ~= nil and type(P.pendingKeyIds) == "function" and type(P.pendingIds) == "function" then
        local okI, ids = pcall(P.pendingIds)
        if okI and type(ids) == "table" and #ids == 1 then
            local okK, set = pcall(P.pendingKeyIds, ids[1])
            if okK and type(set) == "table" then return function(k) return set[tonumber(k)] == true end end
        end
    end
    return function() return false end
end
-- a loaded car (near him): the same rule, read from the car itself
local function loadedCanGo(car)
    local okD, part = pcall(function() return car:getPartById("DoorFrontLeft") end)
    local door = okD and part ~= nil and call(part, "getDoor") or nil
    if door == nil then return false, "car_lock_unknown" end
    local locked = call(door, "isLocked")
    if locked == nil then return false, "car_lock_unknown" end
    if locked == true then return false, "car_locked" end
    local kid = tonumber(call(car, "getKeyId"))
    if call(car, "isKeysInIgnition") == true then
        local key = call(car, "getCurrentKey")
        if key ~= nil and kid ~= nil and tonumber(call(key, "getKeyId")) == kid then return true end
    end
    if call(car, "isHotwired") == true and call(car, "isHotwiredBroken") == false then return true end
    if kid == nil or kid < 0 then return false, "car_no_key" end
    if herKeys()(kid) then return true end
    local n = tonumber(call(car, "getPartCount")) or 0
    for i = 0, n - 1 do
        local okP, p = pcall(function() return car:getPartByIndex(i) end)
        local c = okP and p ~= nil and call(p, "getItemContainer") or nil
        if c ~= nil then
            local okH, h = pcall(function() return c:haveThisKeyId(kid) end)
            if okH and h ~= nil and h ~= false then return true end
        end
    end
    return false, "car_no_key"
end

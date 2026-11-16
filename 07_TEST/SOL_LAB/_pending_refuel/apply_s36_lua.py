"""Run only after the game is closed. When no car is found near her the log says why; a drive that cannot start says why, and does not leave the engine running.
usage: apply_s36_lua.py <SolGPS.lua> <SCDriving.lua>"""
import sys
def patch(p, a, b):
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    a, b = a.replace("\n", nl), b.replace("\n", nl)
    assert t.count(a) == 1, (p, a[:60], t.count(a))
    open(p, "w", encoding="utf-8", newline="").write(t.replace(a, b))
    print("applied to", p)
patch(sys.argv[1], """            if d < bd then best, bd = v, d end
        end
    end
    return best
end
""", """            if d < bd then best, bd = v, d end
        end
    end
    if best == nil then log("no car within 30 tiles of " .. math.floor(ax) .. "," .. math.floor(ay) .. " (anchor " .. (sol() and "sol" or "player") .. "), cars listed: " .. #vehicles) end
    return best
end
""")
patch(sys.argv[2], """function Driving.hasKey(actor, vehicle)
    vehicle = vehicle or vehicleOf(actor)
    local keyOk, keyId = method(vehicle, "getKeyId")
""", """-- the game's own key check looks only at her top level: a key in a bag she carries is moved up, so that check finds it
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
""")
patch(sys.argv[2], """    local hasKey = Driving.hasKey(job.actor) == true
    if solFixOn("drive_passenger") then
""", """    local hasKey = Driving.hasKey(job.actor) == true or takeKeyFromCar(job.actor, job.vehicle)
    local runningOk, running = method(job.vehicle, "isEngineRunning")
    if not hasKey and not (runningOk and running == true) then                   -- no key and the engine is off: nothing can start it, and that is what he should hear
        print("[SolDrive] no key for this car")
        Driving.stop(job.actor, "no_key")
        return false, "no_key"
    end
    if solFixOn("drive_passenger") then
""")
patch(sys.argv[2], """    if not accepted then Driving.stop(job.actor, "bridge_failure") return false, reason end
    job.nativeStarted = true
""", """    if not accepted then
        print("[SolDrive] driveStart refused: " .. tostring(reason))
        Driving.stop(job.actor, "bridge_failure")
        local okV, car = pcall(function() return job.actor:getVehicle() end)
        if okV and car ~= nil then                                               -- a running car left behind is taken off the ground by the game when its area unloads
            local okR, running = pcall(function() return car:isEngineRunning() end)
            if okR and running == true then pcall(function() car:shutOff() end) end
        end
        return false, reason
    end
    job.nativeStarted = true
""")

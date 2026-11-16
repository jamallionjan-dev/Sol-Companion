"""Run only after the game is closed. Vehicles from any mod: seats that are really there, whatever the trunk and wheels are called, one shared door, the right fuel.
usage: apply_s31_lua.py <SolOrders.lua> <SCVehicleUnload.lua> <SCExpeditionCar.lua> <SCVehicle.lua> <SolFuel.lua>"""
import sys
def patch(p, pairs):
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    for a, b, *n in pairs:
        a, b = a.replace("\n", nl), b.replace("\n", nl)
        assert t.count(a) == (n[0] if n else 1), (p, a[:70], t.count(a))
        t = t.replace(a, b)
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("applied to", p)
patch(sys.argv[1], [
("""            if not taken(i) then wanted = i; break end
""", """            local missing = false                                          -- some vehicles lose or never had a seat
            local okI, installed = pcall(function() return veh:isSeatInstalled(i) end)
            if okI and installed == false then missing = true end
            if not taken(i) and not missing then wanted = i; break end
"""),
])
patch(sys.argv[2], [
("""local function trunkFor(vehicle)
    local part = call(vehicle, "getPartById", "TruckBed")
    local container = part and call(part, "getItemContainer") or nil
""", """-- The part vehicles call TruckBed, or else the biggest real storage it has: mods name theirs as they like.
local function trunkPart(vehicle)
    local part = call(vehicle, "getPartById", "TruckBed")
    if part and call(part, "getItemContainer") then return part end
    local best, room = nil, -1
    local count = tonumber(call(vehicle, "getPartCount")) or 0
    for index = 0, count - 1 do
        local candidate = call(vehicle, "getPartByIndex", index)
        local id = string.lower(tostring(candidate and call(candidate, "getId") or ""))
        local items = candidate and call(candidate, "getItemContainer") or nil
        if items and string.sub(id, 1, 4) ~= "seat" and string.sub(id, 1, 5) ~= "glove" then
            local capacity = tonumber(call(items, "getCapacity")) or 0
            if capacity > room then best, room = candidate, capacity end
        end
    end
    return best
end

local function trunkFor(vehicle)
    local part = trunkPart(vehicle)
    local container = part and call(part, "getItemContainer") or nil
"""),
])
LOOP = """    for _, part in ipairs({ "TireFrontLeft", "TireFrontRight",
        "TireRearLeft", "TireRearRight" }) do
        if not componentReady(%s, part, true) then
            return %s, "wheel_unusable"
        end
    end
"""
NEW = """    if not wheelsReady(%s) then
        return %s, "wheel_unusable"
    end
"""
patch(sys.argv[3], [
("""local function componentReady(vehicle, partId, needsItem)
""", """local componentReady
-- Every wheel the vehicle really has, whatever its script calls them.
local function wheelsReady(vehicle)
    local countOk, count = call(vehicle, "getPartCount")
    if not countOk or type(count) ~= "number" then return false end
    for index = 0, count - 1 do
        local partOk, part = call(vehicle, "getPartByIndex", index)
        if partOk and part ~= nil then
            local wheelOk, wheel = call(part, "getWheelIndex")
            if wheelOk and type(wheel) == "number" and wheel >= 0 then
                local idOk, id = call(part, "getId")
                if not idOk or not componentReady(vehicle, id, true) then return false end
            end
        end
    end
    return true
end

function componentReady(vehicle, partId, needsItem)
"""),
(LOOP % ("vehicle", "nil"), NEW % ("vehicle", "nil")),
(LOOP % ("car", "false"), NEW % ("car", "false"), 2),
])
patch(sys.argv[4], [
("""local function hasExteriorEntry(vehicle, seat)
    local area, known = exteriorArea(vehicle, seat)
    if not known then return true end -- Lightweight providers.
    if type(area) ~= "string" or area == "" then return false end
    for otherSeat = 0, seat - 1 do
""", """local function hasExteriorEntry(vehicle, seat)
    local area, known = exteriorArea(vehicle, seat)
    if not known then return true end -- Lightweight providers.
    if type(area) ~= "string" or area == "" then return false end
    -- A vehicle with one door for everybody (an APC's rear ramp): nobody has to climb past anybody.
    local countOk, count = invoke(vehicle, "getMaxPassengers")
    local firstArea = select(1, exteriorArea(vehicle, 0))
    local oneDoor = countOk and type(count) == "number" and count > 1 and firstArea == area
    if oneDoor then
        for otherSeat = 1, count - 1 do
            local otherArea = select(1, exteriorArea(vehicle, otherSeat))
            if type(otherArea) == "string" and otherArea ~= "" and otherArea ~= area then oneDoor = false; break end
        end
    end
    if oneDoor then return true end
    for otherSeat = 0, seat - 1 do
"""),
])
patch(sys.argv[5], [
("""    local part = call(veh, "getPartById", "GasTank")
    if part == nil then return false, "no_gas_tank" end
    local cur, cap = tonumber(call(part, "getContainerContentAmount")), tonumber(call(part, "getContainerCapacity"))
""", """    local part = call(veh, "getPartById", "GasTank")
    if part == nil then return false, "no_gas_tank" end
    local fuelKind = call(part, "getContainerContentType")
    if type(fuelKind) == "string" and fuelKind ~= "Gasoline" then return false, "wrong_fuel" end   -- a pump's petrol never goes in a jet fuel tank
    local cur, cap = tonumber(call(part, "getContainerContentAmount")), tonumber(call(part, "getContainerCapacity"))
"""),
])

-- SolFarComeCar.lua - s92 come_by_car: "come to me by car" from home, or from anywhere she stands with a car near her.
--   Pieces on top of SolFar (its module is SolUI.solFarF, published by apply_s92_come_car_lua.py), each behind a switch:
--   come_by_car 1 her car is in the loaded world but more than 60 tiles from him (she is out of his loaded ring, it is not):
--                 the trip still uses it (SolFar.usableCar reads F.carNear).
--               2 her own car is not loaded, another loaded car within 25 tiles of where she is saved is usable (driver's door
--                 unlocked, she can start it, fuel for the road): it becomes her car for this trip.
--               3 the car the trip chose is the car the drive takes (gps.lastDriveCar, used with the Mind's car=last), not merely the
--                 nearest car to the square she appeared on.
--   far_car     4 a far car brought in: her saved record goes to the square by the driver's door once the car is turned along the road
--                 (it went 2 tiles east of the car's centre: under the car on an east-west road).
--               5 a helicopter: she lands it, gets out and walks to him; no drive (Living Fellows' driving does not fly).
--               6 the arrival queue: when the world streamer already took the request, a 10 s timeout keeps waiting (up to 30 s) for its
--                 answer instead of falling back while the row is being staged (a staged row with no Lua left to finish it = busy for good).
--   Nothing here runs when its switch is off. Pure ASCII.
SolUI = SolUI or {}
local U = SolUI
local M = { VERSION = "0.1.0" }
SolFarComeCar = M

local function log(m) print("[SolFarComeCar] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function on(fix)
    local A = rawget(_G, "SolAuthority")
    if type(A) ~= "table" or type(A.on) ~= "function" then return false end
    local ok, v = pcall(A.on, fix)
    return ok and v == true
end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function xyOf(o)
    local x, y = tonumber((call(o, "getX"))), tonumber((call(o, "getY")))
    if x ~= nil and y ~= nil then return x, y end
    return nil
end
local function SC() local s = rawget(_G, "SurvivorCompanion"); if type(s) == "table" then return s end return nil end
local function player() local f = rawget(_G, "getSpecificPlayer"); return f and f(0) or nil end

local NEAR_HER, MIN_FUEL, QUEUE_EXTEND_MS, QUEUE_MAX_EXTENSIONS = 25, 0.5, 5000, 6
local F = nil
local pendingKind = nil

-- ---------------------------------------------------------------- 1: any loaded distance for her own loaded car
local function carNear()
    if on("come_by_car") then return 1e9 end                 -- loaded at all: the search for her square starts at the car
    return 60
end

-- ---------------------------------------------------------------- 2: a loaded car near where she is saved
local function adoptLoadedCar()
    if not on("come_by_car") or F == nil then return nil end
    if type(F.record) ~= "function" or type(F.loadedCar) ~= "function" or type(F.store) ~= "function" or type(F.loadedCanGo) ~= "function" then return nil end
    if F.loadedCar() ~= nil then return nil end                                   -- her own car is in the loaded world: SolFar's own rule
    local b = F.record()
    if b == nil or b.x == nil then return nil end
    local sc = SC()
    local service = sc and sc.Vehicle or nil
    if type(service) ~= "table" or type(service.loadedVehicles) ~= "function" then return nil end
    local ok, list = pcall(service.loadedVehicles)
    if not ok or type(list) ~= "table" then return nil end
    local pv = call(player(), "getVehicle")
    local best, bd = nil, nil
    for _, v in ipairs(list) do
        local vx, vy = xyOf(v)
        local id = tonumber((call(v, "getSqlId")))
        if vx ~= nil and id ~= nil and id >= 0 and v ~= pv then
            local d = math.sqrt((vx - b.x) ^ 2 + (vy - b.y) ^ 2)
            if d <= NEAR_HER and (bd == nil or d < bd) then
                local fuel = type(F.fuelIn) == "function" and F.fuelIn(v) or 0
                local okGo = F.loadedCanGo(v)
                local driver = call(v, "getDriver")
                if okGo == true and (tonumber(fuel) or 0) >= MIN_FUEL and driver == nil then best, bd = v, d end
            end
        end
    end
    if best == nil then return nil end
    local d = F.store()
    if d == nil then return nil end
    d.carSqlId = tonumber((call(best, "getSqlId")))
    d.carX, d.carY = xyOf(best)
    d.carZ = tonumber((call(best, "getZ"))) or 0
    d.carTowing = call(best, "getVehicleTowing") ~= nil or call(best, "getVehicleTowedBy") ~= nil
    local gps = U.gps
    if type(gps) == "table" then gps.lastDriveCar = best end                      -- rememberCar reads this every 5 s: it stays this car
    log("a loaded car near her for the trip: " .. tostring(d.carSqlId) .. " " .. tostring(call(best, "getScriptName")) .. " " .. math.floor(bd) .. " tiles from her")
    return best
end

-- ---------------------------------------------------------------- 3: the car the trip chose is the car the drive takes
local function pinTripCar()
    if not on("come_by_car") or F == nil or type(F.loadedCar) ~= "function" then return end
    local car = F.loadedCar()
    local gps = U.gps
    if car ~= nil and type(gps) == "table" then gps.lastDriveCar = car end
end

local function wrapSolFar()
    local base = U.solFar
    if type(base) ~= "function" or U.solFarComeCar92 == base then return end
    local wrapped = function(option)
        local opt = string.lower(tostring(option or "status"))
        if opt == "come_car" and on("come_by_car") then
            pcall(adoptLoadedCar)
            local ok, why = base(option)
            if ok == true and string.sub(tostring(why), 1, 8) == "waiting:" then pcall(pinTripCar) end
            log("come_car -> " .. tostring(ok) .. " " .. tostring(why))
            return ok, why
        end
        return base(option)
    end
    U.solFar = wrapped
    U.solFarComeCar92 = wrapped
end

-- ---------------------------------------------------------------- 4, 5, 6: the far arrival
local function regroup(a)
    local sc = SC()
    if type(sc) ~= "table" or type(sc.Commands) ~= "table" or type(sc.Commands.issue) ~= "function" or type(sc.GameplayUtil) ~= "table" then return false end
    local okId, id = pcall(sc.GameplayUtil.idOf, a)
    if not okId or type(id) ~= "string" or id == "" then return false end
    local SP = rawget(_G, "SolPlace")                                             -- spatial_access: through doors first, then regroup
    local px, py = xyOf(player())
    if type(SP) == "table" and type(SP.on) == "function" and SP.on() and type(SP.goNear) == "function" and px ~= nil then
        local okG, started = pcall(SP.goNear, px, py, nil, 3, function() pcall(sc.Commands.issue, id, "regroup", nil, player()) end)
        if okG and started == true then return true end
    end
    local ok, result = pcall(sc.Commands.issue, id, "regroup", nil, player())
    return ok and result ~= false
end

local function doorRecord(p)
    if p.doorMoved or type(F.record) ~= "function" or type(F.doorSquare) ~= "function" or type(F.loadedCar) ~= "function" then return end
    local car = F.loadedCar()
    if car == nil then return end
    local b = F.record()
    if b == nil or b.id == "live" then p.doorMoved = true; return end              -- a live registration is recovered at the door by SolFar
    local x, y = F.doorSquare(car)
    if x == nil then return end
    local sc = SC()
    local P = sc and sc.Persistence or nil
    if type(P) ~= "table" or type(P.pendingRelocate) ~= "function" then return end
    local ok, moved, why = pcall(P.pendingRelocate, b.id, x, y, 0)
    p.doorMoved = true
    log("her saved record " .. ((ok and moved == true) and ("goes to the driver's door square " .. x .. "," .. y) or ("stays where it was (" .. tostring(ok and why or moved) .. ")")))
end

local function heliArrive(p, t)
    if t - (p.heliAt or 0) < 1000 and t >= (p.heliAt or 0) then return end
    p.heliAt = t
    local car = type(F.loadedCar) == "function" and F.loadedCar() or nil
    if car == nil then return end
    local a = type(F.actor) == "function" and F.actor() or nil
    if a == nil then
        local L = type(U.solActor) == "function" and U.solActor() or nil
        local sc = SC()
        if L == nil or sc == nil or type(sc.Actor) ~= "table" or type(sc.Actor.recover) ~= "function" then doorRecord(p); return end   -- a saved record: the restore brings her
        local x, y, sq = F.doorSquare(car)
        if sq == nil then return end
        local okR, done = pcall(sc.Actor.recover, L, sq)
        if not (okR and done == true) then return end
        a = L
        log("she is out of the helicopter, " .. x .. "," .. y)
    end
    if call(a, "getVehicle") ~= nil then
        local sc = SC()
        local okId, id = pcall(function() return sc.GameplayUtil.idOf(a) end)
        if okId and type(id) == "string" then pcall(sc.Commands.issue, id, "exit_vehicle", nil, player()) end
        return
    end
    p.done = true                                                                 -- SolFar stops seating her
    local walked = regroup(a)
    log("helicopter landed; she walks to him (" .. tostring(walked) .. ")")
end

local function wrapArrival()
    if F == nil or F.comeCar92 then return end
    F.comeCar92 = true
    local baseTick, baseArrive = F.arriveTick, F.arrive
    if type(baseTick) == "function" then
        F.arriveTick = function(t)
            local A = F.arriving
            if A ~= nil and on("far_car") then
                pendingKind = A.kind
                local stateFn = rawget(_G, "solCarArriveState")
                if A.sent ~= nil and type(stateFn) == "function" and tostring(stateFn()) == "queued" and t - A.sent > 9000 then
                    local cancel = rawget(_G, "solCarArriveCancel")
                    local okC, had = false, false
                    if type(cancel) == "function" then okC, had = pcall(cancel) end
                    if okC and had ~= true and (A.extended or 0) < QUEUE_MAX_EXTENSIONS then
                        A.extended = (A.extended or 0) + 1
                        A.sent = t - 9000 + QUEUE_EXTEND_MS                          -- the streamer is on it: its answer is what counts
                        log("arrival request taken by the streamer, waiting for its answer (" .. A.extended .. ")")
                        return
                    end
                end
            end
            return baseTick(t)
        end
    end
    if type(baseArrive) == "function" then
        F.arrive = function(p, t)
            if type(p) ~= "table" or not on("far_car") then return baseArrive(p, t) end
            if p.kind == nil then p.kind = pendingKind or "car"; pendingKind = nil end
            if p.kind == "heli" then return heliArrive(p, t) end
            local r = baseArrive(p, t)
            if p.aligned ~= nil and not p.doorMoved then pcall(doorRecord, p) end     -- after the car is turned along the road
            return r
        end
    end
end

local ready = false
local function setup()
    if ready then return true end
    F = rawget(U, "solFarF")
    if type(F) ~= "table" then return false end
    F.carNear = carNear
    wrapSolFar()
    wrapArrival()
    ready = true
    log("ready " .. M.VERSION)
    return true
end
M.setup = setup
M.adoptLoadedCar = function() setup(); return adoptLoadedCar() end
M.heliArrive = function(p, t) setup(); return heliArrive(p, t) end

if type(Events) == "table" and Events.OnGameStart ~= nil and type(Events.OnGameStart.Add) == "function" then Events.OnGameStart.Add(setup) end
if type(Events) == "table" and Events.OnTick ~= nil and type(Events.OnTick.Add) == "function" then
    local function once() if setup() and type(Events.OnTick.Remove) == "function" then Events.OnTick.Remove(once) end end
    Events.OnTick.Add(once)
end
return M

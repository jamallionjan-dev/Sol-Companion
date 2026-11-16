-- SolFuel.lua - Sol and the fuel pumps. The pumps are remembered in Java (SolStations); this file answers the orders.
--   Action sol_fuel, option: find / mark / check_can / walk / car_near / hold / car / can / status. Answers (ok, reason).
--   A station is reported as "station:x,y,fuel,brand,distance,power,dx,dy". Switch: SolAuthority "refuel".
--   Every game method is looked up before it is called. The pumping itself is the game's own timed actions.
SolUI = SolUI or {}
local U = SolUI

local CENTRE_MS, PUMP_REACH, CAR_REACH, MAX_PUMP_MS, SETTLE_MS = 500, 12, 15, 240000, 1500
local ARM_REACH, ACTION_REACH, CAN_REACH, HOLD_MS, STALE_MS = 1.6, 1.9, 1.6, 30000, 20000
local LITRES_PER_MS = 0.0006                                                     -- ISRefuelFromGasPump:getDuration, litres * 50 ticks at 30 a second
local job = nil
local heldUntil = 0

local function log(m) print("[SolFuel] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function g(name) return rawget(_G, name) end
local function fn(name) local f = g(name); if type(f) == "function" then return f end return nil end
local function enabled()
    local A = g("SolAuthority")
    if type(A) ~= "table" or type(A.on) ~= "function" then return false end
    local ok, on = pcall(A.on, "refuel")
    return ok and on == true
end
local function actor() return type(U.solActor) == "function" and U.solActor() or nil end
local function player() local f = fn("getSpecificPlayer"); return f and f(0) or nil end
local function cell() local f = fn("getCell"); return f and f() or nil end

local function hasPower(x, y)
    local sq = call(cell(), "getGridSquare", x, y, 0)
    if sq == nil then return call(call(player(), "getCurrentSquare"), "hasGridPower") == true end       -- not loaded: the grid is the same everywhere
    if call(sq, "hasGridPower") == true then return true end
    local sv = g("SandboxVars")
    return type(sv) == "table" and sv.AllowExteriorGenerator == true and call(sq, "haveElectricity") == true
end

local function station(rx, ry)
    local nearest = fn("solStationsNearest")
    if nearest == nil then return nil, "stations_unavailable" end
    local ok, s = pcall(nearest, rx, ry)
    if not ok or type(s) ~= "string" or s == "" then return nil, "no_station_known" end
    local x, y, fuel, brand = string.match(s, "^(%-?%d+),(%-?%d+),(%-?%d+),([^,]*)$")
    if x == nil then return nil, "no_station_known" end
    x, y = tonumber(x), tonumber(y)
    local dx, dy = x - rx, y - ry
    return { x = x, y = y, fuel = tonumber(fuel), brand = brand, dx = dx, dy = dy, dist = math.floor(math.sqrt(dx * dx + dy * dy) + 0.5) }
end
local function report(st)
    return "station:" .. st.x .. "," .. st.y .. "," .. st.fuel .. "," .. st.brand .. "," .. st.dist .. "," .. (hasPower(st.x, st.y) and 1 or 0) .. "," .. math.floor(st.dx) .. "," .. math.floor(st.dy)
end

local function pumpNear(x, y)
    local at = fn("solStationsPumpAt")
    if at == nil then return nil end
    local ok, p = pcall(at, x, y, PUMP_REACH)
    if ok then return p end
    return nil
end

-- so her own instincts do not walk her off while she pumps
local function holdStill(s)
    local SC = g("SurvivorCompanion")
    if type(SC) ~= "table" or type(SC.Commands) ~= "table" or type(SC.Commands.issue) ~= "function" or type(SC.GameplayUtil) ~= "table" or type(SC.GameplayUtil.idOf) ~= "function" then return end
    local okId, id = pcall(SC.GameplayUtil.idOf, s)
    if okId and type(id) == "string" and id ~= "" then pcall(SC.Commands.issue, id, "stay", nil, player()) end
end

local function queue(action)
    local Q = g("ISTimedActionQueue")
    if type(Q) ~= "table" or type(Q.add) ~= "function" or action == nil then return false end
    return (pcall(Q.add, action))
end
-- Where the action stands in the Lua queue: "running" at the front, "waiting" behind something else (a can being fetched), or nil.
local function actionState(s, action)
    local Q = g("ISTimedActionQueue")
    if type(Q) ~= "table" or type(Q.getTimedActionQueue) ~= "function" or action == nil then return nil end
    local ok, q = pcall(Q.getTimedActionQueue, s)
    if not ok or type(q) ~= "table" or type(q.queue) ~= "table" then return nil end
    for i, a in ipairs(q.queue) do if a == action then return i == 1 and "running" or "waiting" end end
    return nil
end
local function dropAction(s, action)
    local Q = g("ISTimedActionQueue")
    if action == nil or type(Q) ~= "table" or type(Q.getTimedActionQueue) ~= "function" then return end
    local ok, q = pcall(Q.getTimedActionQueue, s)
    if type(action.forceStop) == "function" and action.action ~= nil then pcall(action.forceStop, action) end
    if ok and type(q) == "table" and type(q.removeFromQueue) == "function" then
        pcall(q.removeFromQueue, q, action)
        if q.current == action then q.current = nil end
    end
end

local function theCar(s)
    local G = U.gps
    local last = type(G) == "table" and G.lastDriveCar or nil
    if last ~= nil and call(last, "getX") ~= nil then
        local dx, dy = call(last, "getX") - call(s, "getX"), call(last, "getY") - call(s, "getY")
        if dx * dx + dy * dy <= CAR_REACH * CAR_REACH then return last end
    end
    return call(s, "getVehicle") or (type(U.nearestVehicle) == "function" and U.nearestVehicle(CAR_REACH)) or nil
end

local function petrol() local ok, p = pcall(function() return Fluid.Petrol end); if ok then return p end return nil end
-- a gas can with room, never a water bottle that happens to be empty
local function canState(item)
    local fc = call(item, "getFluidContainer")
    if fc == nil then return nil end
    local name = string.lower(tostring(call(item, "getFullType") or call(item, "getType") or ""))
    local p = petrol()
    local hasPetrol = p ~= nil and call(fc, "contains", p) == true
    if not hasPetrol and not (string.find(name, "petrol", 1, true) or string.find(name, "gascan", 1, true) or string.find(name, "jerry", 1, true)) then return nil end
    if call(item, "isBroken") == true then return nil end
    local amount, capacity = tonumber((call(fc, "getAmount"))), tonumber((call(fc, "getCapacity")))
    if amount == nil or capacity == nil then return nil end
    if hasPetrol and amount < capacity then return "room", amount end
    if call(fc, "isEmpty") == true and call(fc, "isInputLocked") ~= true then return "room", amount end
    if hasPetrol then return "full", amount end
    return nil
end
local function firstCan(container, want)
    return call(container, "getFirstEvalRecurse", function(it) local ok, st = pcall(canState, it); return ok and st == want end)
end
local function findCan(s, want)
    local inv = call(s, "getInventory")
    local item = firstCan(inv, want)
    if item then return item, inv end
    local veh = theCar(s)
    local n = tonumber((call(veh, "getPartCount"))) or 0
    for i = 0, n - 1 do
        local c = call(call(veh, "getPartByIndex", i), "getItemContainer")
        item = firstCan(c, want)
        if item then return item, c end
    end
    return nil
end

-- A route is one planner call: at most one every few frames, and no slower than the GPS preview already is.
local RANK_GAP_MS = 300
local rank = nil
local function routeLength(fromX, fromY, st)
    local SC = g("SurvivorCompanion")
    local R = type(SC) == "table" and SC.ExpeditionRoute or nil
    if type(R) ~= "table" or type(R.planFromPoint) ~= "function" then return nil end
    local ok, route = pcall(R.planFromPoint, { x = fromX, y = fromY, z = 0 }, { x = st.x, y = st.y, z = 0 }, true)
    if not ok or type(route) ~= "table" or type(route.points) ~= "table" or #route.points == 0 then return nil end
    local sum, px, py = 0, fromX, fromY
    for i = 1, #route.points do
        local q = route.points[i]
        local dx, dy = q.x - px, q.y - py
        sum = sum + math.sqrt(dx * dx + dy * dy)
        px, py = q.x, q.y
    end
    local dx, dy = st.x - px, st.y - py
    return sum + math.sqrt(dx * dx + dy * dy)
end
local function parseTop(s, rx, ry)
    local out = {}
    for part in string.gmatch(s, "[^;]+") do
        local x, y, fuel, brand = string.match(part, "^(%-?%d+),(%-?%d+),(%-?%d+),([^,]*)$")
        if x then
            x, y = tonumber(x), tonumber(y)
            local dx, dy = x - rx, y - ry
            out[#out + 1] = { x = x, y = y, fuel = tonumber(fuel), brand = brand, dx = dx, dy = dy, dist = math.floor(math.sqrt(dx * dx + dy * dy) + 0.5) }
        end
    end
    return out
end
local function markIt(st)
    if type(U.gpsSetDestination) == "function" then
        local brand = st.brand ~= "" and (" " .. st.brand) or ""
        U.gpsSetDestination({ x = st.x, y = st.y, name = "Gas station" .. brand })
    end
end
local function finishRank()
    local best, routed = nil, false
    for _, st in ipairs(rank.cands) do
        if st.route then
            if not routed or st.route < best.route then best, routed = st, true end
        elseif not routed and (best == nil or st.dist < best.dist) then best = st end
    end
    if routed then best.dist = math.floor(best.route + 0.5) end
    rank.best = best
    if rank.mark then markIt(best) end
    log("nearest station by " .. (routed and "road" or "straight line") .. ": " .. best.x .. "," .. best.y)
end
local function stepRank()
    if rank == nil or rank.best then return end
    local t = nowMs()
    if t < rank.nextAt then return end
    rank.nextAt = t + RANK_GAP_MS
    local st = rank.cands[rank.i]
    if st == nil then finishRank(); return end
    st.route = routeLength(rank.x, rank.y, st)
    rank.i = rank.i + 1
    if rank.i > #rank.cands then finishRank() end
end

local function find(option)
    local who = option == "mark" and player() or actor() or player()
    local x, y = tonumber((call(who, "getX"))), tonumber((call(who, "getY")))
    if x == nil then return false, "no_position" end
    local top = fn("solStationsTop")
    if top ~= nil then
        local ok, s = pcall(top, x, y, 3)
        local cands = ok and type(s) == "string" and parseTop(s, x, y) or {}
        if #cands == 0 then return false, "no_station_known" end
        if #cands > 1 then
            rank = { cands = cands, i = 1, x = x, y = y, mark = option == "mark", nextAt = 0 }
            return true, "ranking"
        end
        if option == "mark" then markIt(cands[1]) end
        return true, report(cands[1])
    end
    local st, why = station(x, y)
    if st == nil then return false, why end
    if option == "mark" then markIt(st) end
    return true, report(st)
end

-- The same test Living Fellows' walker applies before it accepts a square.
local function freeSquare(sq)
    local SC = g("SurvivorCompanion")
    local GU = type(SC) == "table" and SC.GameplayUtil or nil
    if type(GU) == "table" and type(GU.isSquareFree) == "function" then
        local ok, free = pcall(GU.isSquareFree, sq)
        if ok then return free == true end
    end
    return call(sq, "isFree", false) == true
end

-- Every free square she could work from, nearest to her first.
local function workSquares(cx, cy, reach, s, veh)
    local c, ox, oy, out = cell(), math.floor(cx), math.floor(cy), {}
    local sx, sy = tonumber((call(s, "getX"))) or cx, tonumber((call(s, "getY"))) or cy
    local span = math.ceil(reach) + 1
    for dy = -span, span do
        for dx = -span, span do
            local x, y = ox + dx, oy + dy
            local toWork = math.sqrt((x + 0.5 - cx) ^ 2 + (y + 0.5 - cy) ^ 2)
            if toWork <= reach then
                local sq = call(c, "getGridSquare", x, y, 0)
                if sq ~= nil and freeSquare(sq) and not (veh ~= nil and call(veh, "isIntersectingSquare", x, y, 0) == true) then
                    out[#out + 1] = { x = x, y = y, toHer = (x + 0.5 - sx) ^ 2 + (y + 0.5 - sy) ^ 2, toWork = toWork }
                end
            end
        end
    end
    table.sort(out, function(a, b) if a.toHer ~= b.toHer then return a.toHer < b.toHer end return a.toWork < b.toWork end)
    return out
end

local function walk(s)
    local st, why = station(tonumber((call(s, "getX"))) or 0, tonumber((call(s, "getY"))) or 0)
    if st == nil then return false, why end
    if type(U.solGoto) ~= "function" then return false, "walking_unavailable" end
    local c = cell()
    for _, d in ipairs({ { 0, 1 }, { 1, 0 }, { 0, -1 }, { -1, 0 } }) do
        local sq = call(c, "getGridSquare", st.x + d[1], st.y + d[2], 0)
        if sq ~= nil and freeSquare(sq) then return U.solGoto(st.x + d[1], st.y + d[2], 0) end
    end
    return U.solGoto(st.x, st.y + 1, 0)                                          -- not loaded yet: the walker finds its own way
end

-- the game's own test behind "Refuel from Gas Pump": a pump within two squares of the fuel cap
local function pumpByTheCap(veh)
    local Menu = g("ISVehiclePartMenu")
    if type(Menu) ~= "table" or type(Menu.getNearbyFuelPump) ~= "function" then return nil, "refuel_unavailable" end
    local ok, pump = pcall(Menu.getNearbyFuelPump, veh)
    if ok and pump ~= nil then return pump end
    return nil, "pump_too_far"
end

-- Parks beside the pump with the drawn-path follower: fuel cap towards it, room to walk between.
local park = nil
local function startPark(s)
    local plan = fn("solNavPark")
    if plan == nil or fn("solNavState") == nil or fn("solNavFollow") == nil then return false, "park_unavailable" end
    local veh = theCar(s)
    if veh == nil then return false, "no_car" end
    local part = call(veh, "getPartById", "GasTank")
    local cap = call(veh, "getAreaCenter", call(part, "getArea"))
    local cx, cy = tonumber((call(veh, "getX"))), tonumber((call(veh, "getY")))
    local Vec = g("Vector3f")
    local f = Vec ~= nil and call(veh, "getForwardVector", Vec.new()) or nil
    local hx, hy = tonumber((call(f, "x"))), tonumber((call(f, "z")))
    local capX, capY = tonumber((call(cap, "getX"))), tonumber((call(cap, "getY")))
    if cx == nil or hx == nil or capX == nil then return false, "park_unavailable" end
    local st = station(cx, cy)
    if st == nil then return false, "no_station_known" end
    local B = g("SolBypass")
    local okS, size = pcall(B and B.measure, veh)
    if not okS or type(size) ~= "table" then return false, "park_unavailable" end
    local dx, dy = capX - cx, capY - cy
    local along, side = dx * hx + dy * hy, -dx * hy + dy * hx
    if call(veh, "isEngineRunning") ~= true and type(U.solEngine) == "function" then pcall(U.solEngine, "on") end
    local ok, started = pcall(plan, veh, cx, cy, hx, hy, st.x, st.y, along, side, size.wheelbase, size.kmax)
    if not ok or started ~= true then return false, "park_unavailable" end
    park = { at = nowMs(), following = false }
    log("planning a stop beside the pump")
    return true, "parking"
end
local function parkStatus()
    if park == nil then return false, "no_job" end
    local state, follow, beat = fn("solNavState"), fn("solNavFollow"), fn("solNavBeat")
    if state == nil then park = nil; return false, "park_unavailable" end
    local ok, st = pcall(state)
    if beat then pcall(beat) end
    if not ok or type(st) ~= "string" then park = nil; return false, "park_unavailable" end
    if st == "ready" then
        if follow and select(2, pcall(follow)) == true then park.following = true; return true, "parking" end
        park = nil; return false, "pump_too_far"
    end
    if st == "done" then park = nil; local stop = fn("solNavStop"); if stop then pcall(stop) end; return true, "parked" end
    if string.sub(st, 1, 7) == "failed:" then
        park = nil
        local stop = fn("solNavStop"); if stop then pcall(stop) end
        log("parking failed: " .. st)
        return false, "pump_too_far"
    end
    if nowMs() - park.at > 120000 then park = nil; local stop = fn("solNavStop"); if stop then pcall(stop) end; return false, "pump_too_far" end
    return true, "parking"
end

-- Already where the work can be done: start now. Otherwise the squares to try, and a plain no when there are none.
local beginWork

local function fillCar(s)
    local veh = theCar(s)
    if veh == nil then return false, "no_car" end
    local part = call(veh, "getPartById", "GasTank")
    if part == nil then return false, "no_gas_tank" end
    local fuelKind = call(part, "getContainerContentType")
    if type(fuelKind) == "string" and fuelKind ~= "Gasoline" then return false, "wrong_fuel" end   -- a pump's petrol never goes in a jet fuel tank
    local cur, cap = tonumber((call(part, "getContainerContentAmount"))), tonumber((call(part, "getContainerCapacity")))
    if cur == nil or cap == nil then return false, "no_gas_tank" end
    local solA = rawget(_G, "SolAuthority")
    local topUp = type(solA) == "table" and type(solA.on) == "function" and solA.on("refuel_top_up") == true
    if cur >= cap - (topUp and 0.01 or 0.5) then return true, "tank_full" end
    local Refuel = g("ISRefuelFromGasPump")
    if type(Refuel) ~= "table" or type(Refuel.new) ~= "function" then return false, "refuel_unavailable" end
    local pump, far = pumpByTheCap(veh)
    if pump == nil then return false, far end
    local sq = call(pump, "getSquare")
    if not hasPower(tonumber((call(sq, "getX"))) or 0, tonumber((call(sq, "getY"))) or 0) then return false, "no_power" end
    if call(veh, "isEngineRunning") == true then call(veh, "shutOff") end
    local area = call(part, "getArea")
    local spot = call(veh, "getAreaCenter", area)
    local sx, sy = tonumber((call(spot, "getX"))), tonumber((call(spot, "getY")))
    if sx == nil or type(U.solGoto) ~= "function" then return false, "refuel_unavailable" end
    job = { kind = "car", phase = "walk", veh = veh, part = part, area = area, pump = pump, tx = sx, ty = sy, start = cur, cap = cap, at = nowMs(), sentAt = -100000, ci = 1 }
    return beginWork(s, sx, sy, ARM_REACH, veh, "walking to the fuel cap, " .. cur .. " of " .. cap)
end

local function fillCan(s)
    local item, source = findCan(s, "room")
    if item == nil then
        if findCan(s, "full") ~= nil then return true, "can_full" end
        return false, "no_can"
    end
    local Take = g("ISTakeFuel")
    if type(Take) ~= "table" or type(Take.new) ~= "function" or type(U.solGoto) ~= "function" then return false, "refuel_unavailable" end
    local pump = pumpNear(tonumber((call(s, "getX"))) or 0, tonumber((call(s, "getY"))) or 0)
    if pump == nil then return false, "no_pump_near" end
    local sq = call(pump, "getSquare")
    local px, py = tonumber((call(sq, "getX"))) or 0, tonumber((call(sq, "getY"))) or 0
    if not hasPower(px, py) then return false, "no_power" end
    local inv = call(s, "getInventory")
    if source ~= inv then
        local Util = g("ISInventoryTransferUtil")
        if type(Util) ~= "table" or type(Util.newInventoryTransferAction) ~= "function" then return false, "refuel_unavailable" end
        local okT, tr = pcall(Util.newInventoryTransferAction, s, item, source, inv)
        if not okT or not queue(tr) then return false, "refuel_unavailable" end
    end
    local _, amount = canState(item)
    job = { kind = "can", phase = "walk", item = item, pump = pump, px = px + 0.5, py = py + 0.5, start = amount or 0, at = nowMs(), sentAt = -100000, ci = 1 }
    return beginWork(s, px + 0.5, py + 0.5, CAN_REACH, nil, "walking to the pump with the can")
end

-- One step of the job. She walks with Living Fellows' own walker, and the game's action starts only when she is where it needs her.
local WALK_MS, RESEND_MS, SQUARE_MS = 45000, 4000, 9000
local function atWorkPlace(s)
    if call(s, "getVehicle") ~= nil then return false end
    if job.kind == "car" then
        if call(job.veh, "isInArea", job.area, s) == true then return true end
    end
    local x, y = tonumber((call(s, "getX"))), tonumber((call(s, "getY")))
    if x == nil then return false end
    if job.kind == "car" then return (x - job.tx) ^ 2 + (y - job.ty) ^ 2 <= ARM_REACH * ARM_REACH end
    return (x - job.px) ^ 2 + (y - job.py) ^ 2 <= CAN_REACH * CAN_REACH
end
-- The game's own action, which needs the character inside a hand-sized patch by the cap. Her walker stops on whole squares, so an arm's length from the cap counts too.
local refuelClass = nil
local function refuelAction(s, part, pump)
    local Refuel = g("ISRefuelFromGasPump")
    local Base = g("ISBaseTimedAction")
    if refuelClass == nil and type(Base) == "table" and type(Base.derive) == "function" then
        local ok, C = pcall(Base.derive, Base, "SolRefuelAtCap")
        if ok and type(C) == "table" then
            for k, v in pairs(Refuel) do if type(v) == "function" then C[k] = v end end
            C.isValid = function(self)
                local veh, who = self.vehicle, self.character
                if veh == nil or who == nil or call(who, "getVehicle") ~= nil then return false end
                local area = call(self.part, "getArea")
                if call(veh, "isInArea", area, who) == true then return true end
                local c = call(veh, "getAreaCenter", area)
                local cx, cy, x, y = tonumber((call(c, "getX"))), tonumber((call(c, "getY"))), tonumber((call(who, "getX"))), tonumber((call(who, "getY")))
                return cx ~= nil and x ~= nil and (x - cx) ^ 2 + (y - cy) ^ 2 <= ACTION_REACH * ACTION_REACH
            end
            refuelClass = C
        end
    end
    local ok, a = pcall(Refuel.new, refuelClass or Refuel, s, part, pump)
    if not ok then return nil end
    if refuelClass ~= nil and type(a) == "table" then a.isValid = refuelClass.isValid end
    return a
end
local function startPump(s)
    local action
    if job.kind == "car" then
        action = refuelAction(s, job.part, job.pump)
        if action == nil then return false end
    else
        local Take = g("ISTakeFuel")
        local ok, a = pcall(Take.new, Take, s, job.pump, job.item)
        if not ok then return false end
        action = a
    end
    if not queue(action) then return false end
    job.action, job.phase, job.at = action, "pump", nowMs()
    log("standing at the " .. job.kind .. ": the game's action started")
    return true
end
beginWork = function(s, cx, cy, reach, veh, what)
    if atWorkPlace(s) then
        holdStill(s)
        if startPump(s) then return true, "pumping" end
        job = nil
        return false, "refuel_unavailable"
    end
    job.squares = workSquares(cx, cy, reach, s, veh)
    local SS_ = rawget(_G, "SolStationSurvey")                                    -- s95 station_survey
    if job.kind == "car" and type(SS_) == "table" and type(SS_.on) == "function" and SS_.on() then
        local okS_, sq_ = pcall(SS_.standSquares, s, veh, cx, cy, reach)
        if okS_ and type(sq_) == "table" then job.squares = sq_ end
    end
    if #job.squares == 0 then
        log("no free square within reach of the work")
        job = nil
        return false, "no_way_to_pump"
    end
    job.walkMs = math.max(WALK_MS, #job.squares * SQUARE_MS + 6000)
    log(what .. ": " .. #job.squares .. " squares to try")
    return true, "walking"
end
local function stepJob(s)
    if job == nil or job.phase ~= "walk" or s == nil then return end
    local t = nowMs()
    if atWorkPlace(s) then
        holdStill(s)
        if not startPump(s) then job.phase, job.failed = "over", "refuel_unavailable" end
        return
    end
    if t - job.at > (job.walkMs or WALK_MS) then job.phase, job.failed = "over", "no_way_to_pump"; return end
    if call(s, "getVehicle") ~= nil then return end                             -- not out of the car yet: no square has been tried
    local square = job.squares[job.ci]
    if square ~= nil and square.since ~= nil and t - square.since >= SQUARE_MS then job.ci = job.ci + 1; square = job.squares[job.ci]; job.sentAt = -100000 end
    if square == nil then log("every square near the work was tried"); job.phase, job.failed = "over", "no_way_to_pump"; return end
    if t - job.sentAt >= RESEND_MS then
        job.sentAt = t
        square.since = square.since or t
        local ok, walking = pcall(U.solGoto, square.x, square.y, 0)
        if not ok or walking == false then
            log("the walk was refused at " .. square.x .. "," .. square.y)
            job.ci, job.sentAt = job.ci + 1, -100000
        end
    end
end

-- What ISRefuelFromGasPump:update does, for when the action never got going on her.
local function canFillDirectly(j)
    local okA = pcall(function() return j.part.setContainerContentAmount end)
    if not okA or j.part.setContainerContentAmount == nil then return false end
    local okB = pcall(function() return j.pump.setPipedFuelAmount end)
    return okB and j.pump.setPipedFuelAmount ~= nil
end
local function stepDirect(s)
    if job == nil or job.phase ~= "direct" or s == nil then return end
    local t = nowMs()
    if not atWorkPlace(s) then job.phase, job.failed = "over", "pump_failed"; return end
    local cur = tonumber((call(job.part, "getContainerContentAmount"))) or job.start
    local units = tonumber((call(job.pump, "getPipedFuelAmount"))) or 0
    if job.cap - cur <= 0.5 or units <= 0 or t - job.at > MAX_PUMP_MS then job.phase = "direct_done"; return end
    job.owed = (job.owed or 0) + (t - job.lastFill) * LITRES_PER_MS
    job.lastFill = t
    if job.owed < 1 then return end
    local litres = math.min(math.floor(job.owed), math.floor(job.cap - cur))
    job.owed = job.owed - litres
    local okJ, jerry = pcall(function() return Vehicles.JerryCanLitres end)
    local perLitre = 8 / ((okJ and tonumber(jerry)) or 10)
    call(job.part, "setContainerContentAmount", cur + litres)
    job.pumpLeft = (job.pumpLeft or units) - litres * perLitre                 -- a unit is more than a litre: rounding each step would never take one away
    call(job.pump, "setPipedFuelAmount", math.max(0, math.ceil(job.pumpLeft)))
    call(job.veh, "transmitPartModData", job.part)
end

local function status(s)
    if job == nil then return false, "no_job" end
    job.polledAt = nowMs()
    heldUntil = nowMs() + HOLD_MS                                               -- the next step of the errand may need her on foot too
    if job.phase == "over" then local why = job.failed; job = nil; return false, why end
    if job.phase == "walk" then
        stepJob(s)
        if job.phase == "over" then local why = job.failed; job = nil; return false, why end
        if job.phase == "walk" then return true, "walking" end
    end
    local t = nowMs() - job.at
    if job.phase == "direct" then
        stepDirect(s)
        if job.phase == "over" then local why = job.failed; job = nil; return false, why end
        if job.phase == "direct" then return true, "pumping" end
    elseif actionState(s, job.action) == "running" and t < MAX_PUMP_MS then return true, "pumping"
    elseif actionState(s, job.action) == "waiting" and t < MAX_PUMP_MS then return true, "starting"
    elseif t < SETTLE_MS then return true, "starting"
    elseif job.kind == "car" and (tonumber((call(job.part, "getContainerContentAmount"))) or job.start) <= job.start + 0.5 and canFillDirectly(job) then
        log("the game's action did not run on her: filling with its own calls")
        job.phase, job.at, job.lastFill = "direct", nowMs(), nowMs()
        return true, "pumping"
    end
    local j = job
    job = nil
    if j.kind == "car" then
        local cur = tonumber((call(j.part, "getContainerContentAmount"))) or j.start
        if cur > j.start + 0.5 then return true, "done:" .. math.floor(cur - j.start) end
        return false, "pump_failed"
    end
    local fc = call(j.item, "getFluidContainer")
    local amount = tonumber((call(fc, "getAmount"))) or j.start
    if amount > j.start + 0.05 then return true, "done:" .. string.format("%.1f", amount - j.start) end
    return false, "pump_failed"
end

-- True while the errand needs her on her feet: Living Fellows must not seat her in the player's car meanwhile.
function U.solFuelHeld() return job ~= nil or nowMs() < heldUntil end
U.solFuelParts = { theCar = theCar, station = station, hasPower = hasPower, freeSquare = freeSquare,   -- s95 station_survey
    walking = function() return job ~= nil and job.kind == "car" and job.phase == "walk" end }

function U.solFuel(option)
    if not enabled() then return false, "fix_off" end
    local opt = string.lower(tostring(option or ""))
    if opt == "find" or opt == "mark" then return find(opt) end
    if opt == "street" then
        local who = player() or actor()
        local x, y = tonumber((call(who, "getX"))), tonumber((call(who, "getY")))
        if x == nil or type(U.gpsNearestRoad) ~= "function" then return false, "no_street" end
        local ok, _, _, dist, name = pcall(U.gpsNearestRoad, x, y)
        if not ok or type(name) ~= "string" or name == "" or type(dist) ~= "number" or dist > 15 then return false, "no_street" end
        local life = g("SolLife")
        if type(life) == "table" and type(life.noteStreet) == "function" then pcall(life.noteStreet, name, x, y) end
        return true, "street:" .. name
    end
    if opt == "gardens" then
        local list, who = fn("solStationsGardens"), player() or actor()
        if list == nil then return false, "stations_unavailable" end
        local ok, s = pcall(list, tonumber((call(who, "getX"))) or 0, tonumber((call(who, "getY"))) or 0, 30)
        if not ok or type(s) ~= "string" then return false, "stations_unavailable" end
        return true, "gardens:" .. s
    end
    if opt == "list" then
        local top, who = fn("solStationsTop"), player() or actor()
        if top == nil then return false, "stations_unavailable" end
        local ok, s = pcall(top, tonumber((call(who, "getX"))) or 0, tonumber((call(who, "getY"))) or 0, 200)
        if not ok or type(s) ~= "string" then return false, "stations_unavailable" end
        return true, "list:" .. s
    end
    if opt == "count" then
        local top, who = fn("solStationsTop"), player() or actor()
        if top == nil then return false, "stations_unavailable" end
        local ok, s = pcall(top, tonumber((call(who, "getX"))) or 0, tonumber((call(who, "getY"))) or 0, 200)
        if not ok or type(s) ~= "string" then return false, "stations_unavailable" end
        local n, names = 0, {}
        for part in string.gmatch(s, "[^;]+") do
            n = n + 1
            local brand = string.match(part, "([^,]*)$")
            if brand and brand ~= "" then names[#names + 1] = brand end
        end
        return true, "count:" .. n .. ":" .. table.concat(names, ",")
    end
    if opt == "rank" then
        if rank == nil then return false, "no_station_known" end
        stepRank()
        if not rank.best then return true, "ranking" end
        local st = rank.best
        rank = nil
        return true, report(st)
    end
    local s = actor()
    if s == nil then return false, "no_sol" end
    local SS_ = rawget(_G, "SolStationSurvey")                                    -- s95 station_survey: the station decides where she stops and stands
    if type(SS_) == "table" and type(SS_.on) == "function" and SS_.on() then
        if opt == "car_near" or opt == "park" or opt == "park_status" then return SS_.handle(opt, s) end
        if opt == "cancel" then pcall(SS_.cancel) end
    end
    if opt == "check_can" then
        if findCan(s, "room") or findCan(s, "full") then return true, "can_ok" end
        return false, "no_can"
    end
    if opt == "walk" then return walk(s) end
    if opt == "hold" then heldUntil = nowMs() + HOLD_MS; return true, "held" end
    if opt == "cancel" then
        if job ~= nil then dropAction(s, job.action) end
        job, heldUntil = nil, 0
        return true, "cancelled"
    end
    if opt == "car_near" then
        local veh = theCar(s)
        if veh == nil then return false, "no_car" end
        local pump, far = pumpByTheCap(veh)
        if pump == nil then return false, far end
        return true, "near"
    end
    if opt == "park" then return startPark(s) end
    if opt == "park_status" then return parkStatus() end
    if opt == "car" then return fillCar(s) end
    if opt == "can" then return fillCan(s) end
    if opt == "status" then return status(s) end
    return false, "unknown_option"
end

local nextCentre, on, nextWalkStep = 0, false, 0
local function tick()
    local step = fn("solStationsStep")
    if step == nil then return end
    local t = nowMs()
    if t >= nextCentre then
        nextCentre = t + CENTRE_MS
        on = enabled()
        if on then
            local centre = fn("solStationsCentre")
            local p, s = player(), actor()
            local nan = 0 / 0
            if centre then pcall(centre, tonumber((call(p, "getX"))) or nan, tonumber((call(p, "getY"))) or nan, tonumber((call(s, "getX"))) or nan, tonumber((call(s, "getY"))) or nan) end
        end
    end
    if on then pcall(step) end
    if rank ~= nil then pcall(stepRank) end
    if job ~= nil and job.phase == "walk" and t >= (nextWalkStep or 0) then nextWalkStep = t + 250; stepJob(actor()) end
    if job ~= nil and job.phase == "direct" and t >= (nextWalkStep or 0) then nextWalkStep = t + 250; stepDirect(actor()) end
    if job ~= nil and job.phase ~= "over" and t - (job.polledAt or job.at) > STALE_MS then           -- nobody is waiting for this any more
        log("the errand stopped asking: job dropped")
        dropAction(actor(), job.action)
        job = nil
    end
    if park ~= nil and park.following then local beat = fn("solNavBeat"); if beat then pcall(beat) end end        -- no driving job here to keep it alive
end

if Events and Events.OnTick then Events.OnTick.Add(function() pcall(tick) end) end
return U

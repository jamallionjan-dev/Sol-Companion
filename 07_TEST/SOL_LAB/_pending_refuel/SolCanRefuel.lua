-- SolCanRefuel.lua - Sol fills the car from gas cans. Cans only: the station errand is SolFuel and is not touched here.
--   Her own cans first, then the cans stored at home. Each can goes back where it came from; nothing is ever put on the ground.
--   Switch: refuel_from_can in SolFixes_LAB.txt.
SolUI = SolUI or {}
local U = SolUI
local WALK_MS, SEND_MS, ARM_REACH, TAKE_REACH, LITRES_PER_MS, ACTION_WAIT_MS, SCAN_BATCH = 60000, 4000, 1.7, 1.9, 0.002, 2500, 300

local job, lastResult = nil, nil
local function log(m) print("[SolCanRefuel] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or 0 end
local function g(name) return rawget(_G, name) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function enabled()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("refuel_from_can") == true
end
local function actor() return type(U.solActor) == "function" and U.solActor() or nil end
local function player() local f = g("getSpecificPlayer"); return f and f(0) or nil end
local function dist(a, x, y) local ax, ay = tonumber(call(a, "getX")), tonumber(call(a, "getY")); if ax == nil then return math.huge end return math.sqrt((ax - x) ^ 2 + (ay - y) ^ 2) end

local function petrol() local ok, p = pcall(function() return Fluid.Petrol end); if ok then return p end return nil end
-- litres of petrol in this item; 0 for anything that is not a can holding petrol
local function fuelIn(item)
    local fc = call(item, "getFluidContainer")
    if fc == nil or call(item, "isBroken") == true then return 0 end
    local p = petrol()
    if p == nil or call(fc, "contains", p) ~= true then return 0 end
    return tonumber(call(fc, "getAmount")) or 0
end
local function firstFull(container)
    return call(container, "getFirstEvalRecurse", function(it) local ok, l = pcall(fuelIn, it); return ok and l > 0 end)
end

-- the tank, by what the part holds, so a modded car with its own part names works too
local function tankOf(car)
    local part = call(car, "getPartById", "GasTank")
    if part ~= nil then return part end
    for i = 0, (tonumber(call(car, "getPartCount")) or 0) - 1 do
        local p = call(car, "getPartByIndex", i)
        if call(p, "getContainerContentType") == "Gasoline" then return p end
    end
    return nil
end
local function loaded(car) return car ~= nil and call(car, "isRemovedFromWorld") ~= true and call(car, "getX") ~= nil end
local function targetCar(s)
    local mine = call(player(), "getVehicle")
    if mine ~= nil then return mine end
    local G = U.gps
    local last = type(G) == "table" and G.lastDriveCar or nil
    if loaded(last) then return last end
    return type(U.nearestVehicle) == "function" and U.nearestVehicle(30) or nil
end

-- ---------------------------------------------------------------- the cans at home
local function homeRects()
    local out = {}
    local sc = g("SurvivorCompanion")
    local BL = type(sc) == "table" and sc.BaseLife or nil
    local okB, base = false, nil
    if type(BL) == "table" and type(BL.active) == "function" then okB, base = pcall(BL.active) end
    if okB and type(base) == "table" and type(base.zones) == "table" then
        for _, z in ipairs(base.zones) do
            if type(z) == "table" and (z.kind == "area" or z.kind == "storage") and tonumber(z.x1) and tonumber(z.x2) and tonumber(z.y1) and tonumber(z.y2) then
                out[#out + 1] = { x1 = math.min(z.x1, z.x2), x2 = math.max(z.x1, z.x2), y1 = math.min(z.y1, z.y2), y2 = math.max(z.y1, z.y2), z = tonumber(z.z) or 0 }
            end
        end
    end
    local H = g("SolHome")
    if type(H) == "table" and type(H.rects) == "function" then
        local ok, r = pcall(H.rects)
        if ok and type(r) == "table" then for _, v in ipairs(r) do out[#out + 1] = v end end
    end
    return out
end
local function startScan(j)
    j.squares, j.si, j.cans = {}, 1, {}
    local seen = {}
    for _, r in ipairs(homeRects()) do
        for x = r.x1, r.x2 do for y = r.y1, r.y2 do
            local k = (x * 65536 + y) * 16 + (r.z or 0)
            if not seen[k] then seen[k] = true; j.squares[#j.squares + 1] = { x, y, r.z or 0 } end
        end end
    end
end
local function scanSlice(j, s)
    local c = g("getCell") and g("getCell")()
    local stop = math.min(j.si + SCAN_BATCH - 1, #j.squares)
    for i = j.si, stop do
        local p = j.squares[i]
        local sq = call(c, "getGridSquare", p[1], p[2], p[3])
        local objs = call(sq, "getObjects")
        for oi = 0, (tonumber(call(objs, "size")) or 0) - 1 do
            local o = call(objs, "get", oi)
            for ci = 0, (tonumber(call(o, "getContainerCount")) or 0) - 1 do
                local cont = call(o, "getContainerByIndex", ci)
                local item = firstFull(cont)
                if item ~= nil then j.cans[#j.cans + 1] = { item = item, cont = call(item, "getContainer") or cont, x = p[1], y = p[2], z = p[3] } end
            end
        end
    end
    j.si = stop + 1
    if j.si > #j.squares then
        table.sort(j.cans, function(a, b) return dist(s, a.x + 0.5, a.y + 0.5) < dist(s, b.x + 0.5, b.y + 0.5) end)
        return true
    end
    return false
end

-- ---------------------------------------------------------------- the job
local function finish(result, reason)
    if job == nil then return end
    local tank = job.part
    local now = tank and tonumber(call(tank, "getContainerContentAmount")) or nil
    local cap = tank and tonumber(call(tank, "getContainerCapacity")) or nil
    if result == "done" then
        lastResult = "done:" .. string.format("%.1f", (now or 0) - (job.start or 0)) .. ":" .. tostring(cap and cap > 0 and math.floor((now or 0) / cap * 100 + 0.5) or 0)
    else
        lastResult = "failed:" .. tostring(reason)
    end
    log(lastResult)
    job = nil
end
local function goNear(j, s, x, y, z)
    local t = nowMs()
    if j.sentAt ~= nil and t - j.sentAt < SEND_MS then return end
    j.sentAt = t
    if type(U.solGoto) ~= "function" then return end
    for _, d in ipairs({ { 0, 0 }, { 0, 1 }, { 1, 0 }, { 0, -1 }, { -1, 0 } }) do
        local ok, walking = pcall(U.solGoto, x + d[1], y + d[2], z or 0)
        if ok and walking == true then return end
    end
end
local function transfer(from, to, item)
    local sc = g("SurvivorCompanion")
    local gu = type(sc) == "table" and sc.GameplayUtil or nil
    if type(gu) ~= "table" or type(gu.transferItemVerified) ~= "function" then return false end
    local ok, done = pcall(gu.transferItemVerified, from, to, item)
    return ok and done == true
end
local function nextCan(j, s)
    local mine = firstFull(call(s, "getInventory"))
    if mine ~= nil then j.can, j.from = mine, nil; j.phase, j.at, j.sentAt = "to_car", nowMs(), nil; return true end
    while j.cans ~= nil and #j.cans > 0 do
        local c = table.remove(j.cans, 1)
        if fuelIn(c.item) > 0 then j.can, j.from = c.item, c; j.phase, j.at, j.sentAt = "fetch", nowMs(), nil; return true end
    end
    return false
end
local function afterCan(j, s)
    if j.from ~= nil then j.phase, j.at, j.sentAt = "put_back", nowMs(), nil; return end
    j.phase = "next"
end
local function fuelSpot(j)
    local spot = call(j.car, "getAreaCenter", call(j.part, "getArea"))
    return tonumber(call(spot, "getX")), tonumber(call(spot, "getY"))
end
local function startPour(j, s)
    if call(j.car, "isEngineRunning") == true then call(j.car, "shutOff") end
    call(s, "setPrimaryHandItem", j.can)
    j.phase, j.at, j.last, j.owed = "pour", nowMs(), nowMs(), 0
    j.tankStart, j.canStart = tonumber(call(j.part, "getContainerContentAmount")) or 0, fuelIn(j.can)
    local A = g("ISAddGasolineToVehicle"); local Q = g("ISTimedActionQueue")
    if type(A) == "table" and type(A.new) == "function" and type(Q) == "table" and type(Q.add) == "function" then
        local ok, action = pcall(A.new, A, s, j.part, j.can)
        if ok and action ~= nil and pcall(Q.add, action) then j.action = action; return end
    end
    j.direct = true
end
local function actionRunning(j, s)
    local Q = g("ISTimedActionQueue")
    if j.action == nil or type(Q) ~= "table" or type(Q.getTimedActionQueue) ~= "function" then return false end
    local ok, q = pcall(Q.getTimedActionQueue, s)
    if not ok or type(q) ~= "table" or type(q.queue) ~= "table" then return false end
    for _, a in ipairs(q.queue) do if a == j.action then return true end end
    return false
end
local function stepPour(j, s)
    local t = nowMs()
    local tank = tonumber(call(j.part, "getContainerContentAmount")) or 0
    local cap = tonumber(call(j.part, "getContainerCapacity")) or tank
    local left = fuelIn(j.can)
    if tank >= cap - 0.5 or left <= 0.01 then
        call(s, "setPrimaryHandItem", nil)
        if tank >= cap - 0.5 then j.full = true end
        return afterCan(j, s)
    end
    if not j.direct then
        if actionRunning(j, s) and (tank > j.tankStart or t - j.at < ACTION_WAIT_MS) then return end
        if tank > j.tankStart then j.action = nil; j.direct = true end          -- it ran and stopped early: finish by hand
        if t - j.at >= ACTION_WAIT_MS then
            local Q = g("ISTimedActionQueue")
            local ok, q = false, nil
            if type(Q) == "table" and type(Q.getTimedActionQueue) == "function" then ok, q = pcall(Q.getTimedActionQueue, s) end
            if ok and type(q) == "table" and type(q.removeFromQueue) == "function" and j.action ~= nil then pcall(q.removeFromQueue, q, j.action) end
            j.action, j.direct, j.last = nil, true, t
            log("the game's action did not run on her: pouring by hand")
        end
        return
    end
    j.owed = j.owed + (t - j.last) * LITRES_PER_MS
    j.last = t
    if j.owed < 1 then return end
    local litres = math.min(math.floor(j.owed), math.ceil(cap - tank), math.ceil(left))
    j.owed = j.owed - litres
    local fc = call(j.can, "getFluidContainer")
    call(j.part, "setContainerContentAmount", tank + litres)
    call(fc, "adjustAmount", math.max(0, left - litres))
    call(j.car, "transmitPartModData", j.part)
    call(j.can, "syncItemFields")
end
local function step(s)
    local j = job
    if j == nil then return end
    if not loaded(j.car) then return finish("failed", "car_not_loaded") end
    if nowMs() - j.at > WALK_MS and j.phase ~= "scan" and j.phase ~= "pour" then return finish("failed", "no_way") end
    if j.phase == "scan" then
        if scanSlice(j, s) then
            if not nextCan(j, s) then
                if j.poured then return finish("done") end
                return finish("failed", "no_can")
            end
        end
    elseif j.phase == "fetch" then
        if dist(s, j.from.x + 0.5, j.from.y + 0.5) <= TAKE_REACH then
            if not transfer(j.from.cont, call(s, "getInventory"), j.can) then return finish("failed", "cannot_take_can") end
            j.phase, j.at, j.sentAt = "to_car", nowMs(), nil
        else goNear(j, s, j.from.x, j.from.y, j.from.z) end
    elseif j.phase == "to_car" then
        if call(s, "getVehicle") ~= nil then
            if type(SolOrders) == "table" and type(SolOrders.leaveCar) == "function" and not j.leaving then j.leaving = true; SolOrders.leaveCar() end
            return
        end
        local x, y = fuelSpot(j)
        if x == nil then return finish("failed", "no_tank") end
        if call(j.car, "isInArea", call(j.part, "getArea"), s) == true or dist(s, x, y) <= ARM_REACH then startPour(j, s); j.poured = true
        else goNear(j, s, math.floor(x), math.floor(y), 0) end
    elseif j.phase == "pour" then stepPour(j, s)
    elseif j.phase == "put_back" then
        if dist(s, j.from.x + 0.5, j.from.y + 0.5) <= TAKE_REACH then
            transfer(call(j.can, "getContainer") or call(s, "getInventory"), j.from.cont, j.can)
            j.phase = "next"
        else goNear(j, s, j.from.x, j.from.y, j.from.z) end
    elseif j.phase == "next" then
        if j.full then return finish("done") end
        if nextCan(j, s) then return end
        if not j.scanned then j.scanned, j.phase, j.at = true, "scan", nowMs(); startScan(j); return end
        return finish("done")
    end
end
local function start()
    if job ~= nil then return true, "busy" end
    local s = actor()
    if s == nil then return false, "no_sol" end
    local car = targetCar(s)
    if car == nil then return false, "no_car" end
    if not loaded(car) then return false, "car_not_loaded" end
    local part = tankOf(car)
    if part == nil then return false, "no_tank" end
    local kind = call(part, "getContainerContentType")
    if type(kind) == "string" and kind ~= "Gasoline" then return false, "wrong_fuel" end
    local cur, cap = tonumber(call(part, "getContainerContentAmount")) or 0, tonumber(call(part, "getContainerCapacity")) or 0
    if cur >= cap - 0.5 then return false, "tank_full" end
    job, lastResult = { car = car, part = part, start = cur, at = nowMs(), cans = {} }, nil
    if not nextCan(job, s) then job.phase, job.at, job.scanned = "scan", nowMs(), true; startScan(job) end
    log("started, tank " .. cur .. " of " .. cap .. ", phase " .. tostring(job.phase))
    return true, "started"
end
function U.solCanRefuel(option)
    if not enabled() then return false, "fix_off" end
    if option == "status" then
        if job ~= nil then return true, "running:" .. tostring(job.phase) end
        return true, lastResult or "idle"
    end
    return start()
end
do
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "refuel_from_can" then return U.solCanRefuel(option) end
        return base(id, option)
    end
end
if type(SolBudget) == "table" and type(SolBudget.register) == "function" then
    SolBudget.register("can_refuel", function() if job ~= nil then local s = actor(); if s ~= nil then step(s) end end end, { everyMs = 100, priority = 5 })
end

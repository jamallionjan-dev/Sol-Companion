-- ---------------------------------------------------------------- far_car: the nearest car she can use, not only hers
--   The Java side reads the saved vehicles within 25 tiles of where she is saved (read only, on the world streamer thread); the list is
--   kept fresh while she is far. Her own car comes first when it is in that list and usable; else the nearest whose saved row says it runs,
--   has fuel for the road, an unlocked driver's door and a way to start it (see far_car keys). Anything unknown is not used: no guess.
--   How long the trip takes depends on what she comes in: a car 3 min, a tracked vehicle 3.5, a helicopter 1.
local FAR_CAR_RADIUS, CARS_EVERY_MS, CARS_FRESH_MS, CARS_MOVED_TILES, PICK_MS = 25, 15000, 60000, 3, 120000
local TRACKED_WAIT_MS, HELI_WAIT_MS, ROAD_FACTOR = 210000, 60000, 1.3
local TRACKED_WORDS, HELI_WORDS = { "bradley", "tracked", "m113" }, { "heli", "uh1", "uh60", "huey" }
local cars = { at = -1e12, askedAt = -1e12, list = nil, x = nil, y = nil }
local pick = nil
local function kindOf(script)
    local s = string.lower(tostring(script or ""))
    for _, w in ipairs(HELI_WORDS) do if string.find(s, w) then return "heli" end end
    for _, w in ipairs(TRACKED_WORDS) do if string.find(s, w) then return "tracked" end end
    return "car"
end
local function kindWait(kind)
    if kind == "heli" then return HELI_WAIT_MS end
    if kind == "tracked" then return TRACKED_WAIT_MS end
    return 180000
end
local function massOf(script)
    local ok, m = pcall(function() return getScriptManager():getVehicle(script):getMass() end)
    return ok and tonumber(m) or nil
end
local function num(s) if s == nil or s == "?" then return nil end return tonumber(s) end
-- "x,y|id,x,y,dist,script,fuel,engine,locked,quality,keyId,loaded,verdict[,ignition,hotwired,keyInCar];..."
local function parseCars(text)
    local ax, ay, body = string.match(tostring(text or ""), "^(%-?%d+),(%-?%d+)|(.*)$")
    if ax == nil then return nil end
    local list = {}
    for line in string.gmatch(body, "[^;]+") do
        local f = {}
        for v in string.gmatch(line, "[^,]+") do f[#f + 1] = v end
        if #f >= 12 and num(f[1]) ~= nil then
            list[#list + 1] = { id = num(f[1]), x = num(f[2]), y = num(f[3]), dist = num(f[4]) or 0, script = f[5] ~= "?" and f[5] or nil,
                                fuel = num(f[6]), engine = num(f[7]), locked = num(f[8]), quality = num(f[9]), keyId = num(f[10]), loaded = f[11] == "1", verdict = f[12] }
        end
    end
    return list, tonumber(ax), tonumber(ay)
end
-- asks for a fresh list around where she is saved; reads the answer when it is there
local function carsTick(t, b)
    local stateFn, resultFn, askFn = rawget(_G, "solCarsNearState"), rawget(_G, "solCarsNearResult"), rawget(_G, "solCarsNearRequest")
    if type(stateFn) ~= "function" or type(resultFn) ~= "function" or type(askFn) ~= "function" or b == nil then return end
    local okS, st = pcall(stateFn)
    st = okS and tostring(st) or "?"
    if st == "ok" and cars.askedAt > cars.at then
        local okR, text = pcall(resultFn)
        local list, ax, ay = nil, nil, nil
        if okR then list, ax, ay = parseCars(text) end
        if list ~= nil then cars.list, cars.x, cars.y, cars.at = list, ax, ay, t end
    end
    local moved = cars.x == nil or dist(cars.x, cars.y, b.x, b.y) > CARS_MOVED_TILES
    if st ~= "queued" and (moved or t - cars.askedAt >= CARS_EVERY_MS or t < cars.askedAt) then
        local okA, sent = pcall(askFn, b.x, b.y, FAR_CAR_RADIUS)
        if okA and sent == true then cars.askedAt = t end
    end
end
local function freshCars(b, t)
    if b == nil or cars.list == nil or cars.x == nil then return nil end
    if t - cars.at > CARS_FRESH_MS or t < cars.at or dist(cars.x, cars.y, b.x, b.y) > CARS_MOVED_TILES then return nil end
    return cars.list
end
local function ownCarId() local d = store(); return d and tonumber(d.carSqlId) or nil end
-- unlocked, and she can start it: the saved row says so (key in the ignition, hotwired, key inside), or she carries its key
local function startable(c, hasKey)
    if c.verdict == "ok" then return true end
    return (c.verdict == "no_key" or c.verdict == "start_unknown") and c.keyId ~= nil and c.keyId >= 0 and hasKey(c.keyId)
end
-- the car to bring: hers first when it is near her and usable, else the nearest usable one; nil and the reason when there is none
local function choose(list, px, py, ring)
    local own = ownCarId()
    local d = store() or {}
    local hasKey = herKeys()
    local best, why = nil, "no_car_near"
    local function consider(c, mine)
        if c.loaded or c.x == nil then return end
        if c.verdict == "locked" or c.verdict == "lock_unknown" then why = "locked_near"; return end
        if (c.verdict == "no_key" or c.verdict == "start_unknown") and not startable(c, hasKey) then why = "no_key_near"; return end
        if not startable(c, hasKey) then return end
        if mine and d.carTowing == true then why = "towing"; return end
        local chunks = math.max(math.abs(math.floor(c.x / 8) - math.floor(px / 8)), math.abs(math.floor(c.y / 8) - math.floor(py / 8)))
        if chunks <= ring + 2 then why = "car_too_close"; return end   -- near what is loaded a chunk may be on its way in or out
        local mass = massOf(c.script) or (mine and tonumber(d.carMass)) or 1000
        local need = fuelCost({ carMass = mass, carQuality = c.quality or 100 }, dist(c.x, c.y, px, py) * ROAD_FACTOR) + MIN_FUEL
        if c.fuel == nil or c.fuel < need then why = "no_fuel_near"; return end
        best = { id = c.id, x = c.x, y = c.y, fuel = c.fuel, mass = mass, quality = c.quality or 100, script = c.script, kind = kindOf(c.script), mine = mine }
    end
    if own ~= nil then for _, c in ipairs(list) do if c.id == own then consider(c, true) end end end
    if best == nil then for _, c in ipairs(list) do if best == nil and c.id ~= own then consider(c, false) end end end
    return best, why
end
local function carWhereFar()
    pick = nil
    local ringFn, px, py = rawget(_G, "solCarMoveRing"), xyOf(player())
    if type(ringFn) ~= "function" or type(rawget(_G, "solCarsNearRequest")) ~= "function" then return false, "no_java" end
    if px == nil then return false, "no_player" end
    local b = record()
    if b == nil then return false, pendingCount() > 0 and "cannot_travel" or "no_sol" end
    local list = freshCars(b, nowMs())
    if list == nil then pcall(carsTick, nowMs(), b); return false, "scanning" end
    local okR, ring = pcall(ringFn)
    ring = okR and tonumber(ring) or 0
    local best, why = choose(list, px, py, ring)
    if best == nil then return false, why end                                  -- her own car too: only within 25 tiles of her and usable
    best.at = nowMs()
    pick = best
    log("car for the trip: " .. tostring(best.id) .. " " .. tostring(best.script) .. (best.mine and " (hers)" or ""))
    return true, "car:" .. math.floor(best.x) .. "," .. math.floor(best.y) .. "," .. math.floor(px) .. "," .. math.floor(py) .. "," .. math.floor(ring)
end
-- what is around her, for the Mind to answer truthfully: "cars:<n>|id,script,dist,fuel,verdict,mine;..."
local function carsAnswer()
    if actor() ~= nil then return true, "here" end
    if type(rawget(_G, "solCarsNearRequest")) ~= "function" then return false, "no_java" end
    local b = record()
    if b == nil then return false, pendingCount() > 0 and "cannot_travel" or "no_sol" end
    local list = freshCars(b, nowMs())
    if list == nil then pcall(carsTick, nowMs(), b); return false, "scanning" end
    local own, parts, hasKey = ownCarId(), {}, herKeys()
    for _, c in ipairs(list) do
        local v = startable(c, hasKey) and "ok" or c.verdict                    -- her own key counts
        parts[#parts + 1] = tostring(c.id) .. "," .. tostring(c.script or "?") .. "," .. math.floor(c.dist + 0.5) .. "," .. (c.fuel and string.format("%.1f", c.fuel) or "?") .. "," .. tostring(v) .. "," .. (c.id == own and "1" or "0")
    end
    return true, "cars:" .. #list .. "|" .. table.concat(parts, ";")
end
local function startPicked(p, x, y, tiles)
    pick = nil
    local cost = fuelCost({ carMass = p.mass, carQuality = p.quality }, tiles)
    if (tonumber(p.fuel) or 0) < cost + MIN_FUEL then return false, p.mine and "no_fuel" or "picked_no_fuel" end
    local ms = kindWait(p.kind)
    wait, awake, lastResult = { left = ms, last = nowMs(), tries = 0, mode = "car_far", x = x, y = y, cost = cost, id = p.id, mass = p.mass, quality = p.quality }, true, nil
    log("car " .. tostring(p.id) .. " (" .. tostring(p.kind) .. ") from far, " .. math.floor(tiles) .. " tiles, fuel " .. cost)
    return true, "waiting:" .. math.ceil(ms / 1000)
end

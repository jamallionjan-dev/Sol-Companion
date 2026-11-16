-- SolRoadFirst.lua - she keeps to the road. Switch: road_first.
--   Off the road only past something that really blocks it, by the shortest way round, kept near the road, and back on the same road.
--   A different street only when the road is confirmed shut, at most twice per drive. Otherwise she stops and says so.
SolRoadFirst = SolRoadFirst or {}
local R = SolRoadFirst
local SAME_TILES, SEEN_NEEDED, SEEN_GAP_MS, CORRIDOR_RADIUS, CORRIDOR_REACH, BLOCK_REACH, ENDS_NEAR, MAX_REROUTES, MIN_SPACING = 3, 3, 1800, 10, 60, 1, 15, 2, 0.5

local function log(text) print("[SolRoadFirst] " .. tostring(text)) end
function R.on()
    local A = rawget(_G, "SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("road_first") == true
end

-- the same thing seen ahead on several looks in a row, not a car passing or one bad reading
function R.seen(job, ox, oy, now)
    local s = job.rfSeen
    if type(s) == "table" and now - s.at <= SEEN_GAP_MS and (ox - s.x) ^ 2 + (oy - s.y) ^ 2 <= SAME_TILES * SAME_TILES then
        s.n, s.at, s.x, s.y = s.n + 1, now, ox, oy
    else
        s = { n = 1, at = now, x = ox, y = oy }
        job.rfSeen = s
    end
    return s.n >= SEEN_NEEDED
end

local function realBlock(status, vehicle)
    local B = rawget(_G, "SolBypass")
    local x, y = tonumber(status and status.blockedX), tonumber(status and status.blockedY)
    if type(B) ~= "table" or type(B.world) ~= "table" or x == nil or y == nil then return nil end
    local okC, cars = pcall(B.world.cars, x, y, 3)
    if okC and type(cars) == "table" then
        for i = 1, #cars do
            if cars[i].v ~= vehicle then return "car" end
        end
    end
    local fx, fy = math.floor(x), math.floor(y)
    for dx = -BLOCK_REACH, BLOCK_REACH do
        for dy = -BLOCK_REACH, BLOCK_REACH do
            local ok, kind = pcall(B.world.kind, fx + dx, fy + dy)
            if ok and (kind == "solid" or kind == "post") then return kind end
        end
    end
    return nil
end

-- may she go and look for another street?
function R.mayReroute(job, status, vehicle)
    if not R.on() then return true end
    if (job.rfReroutes or 0) >= MAX_REROUTES then log("no more streets on this drive: stopping"); return false end
    local what = realBlock(status, vehicle)
    if what == nil then log("nothing real blocks the road at the stopping point: stopping, not changing street"); return false end
    job.rfReroutes = (job.rfReroutes or 0) + 1
    log("road confirmed shut by " .. tostring(what) .. ": one other street")
    return true
end

-- the way round may only use ground near the road she is on
function R.sendCorridor(job, x, y)
    local clear, add, radius = rawget(_G, "solNavCorridorClear"), rawget(_G, "solNavCorridorPoint"), rawget(_G, "solNavCorridorRadius")
    if type(clear) ~= "function" or type(add) ~= "function" or type(radius) ~= "function" then return end
    pcall(clear)
    local pts = type(job.route) == "table" and job.route.points or nil
    if not R.on() or type(pts) ~= "table" or x == nil or y == nil then return end
    if (job.jnavFails or 0) >= 1 then log("no way round close to the road: looking wider"); return end
    pcall(radius, CORRIDOR_RADIUS)
    local reach2, sent = CORRIDOR_REACH * CORRIDOR_REACH, 0
    for i = 1, #pts do
        local p = pts[i]
        if (p.x - x) ^ 2 + (p.y - y) ^ 2 <= reach2 then
            pcall(add, p.x, p.y)
            sent = sent + 1
        end
    end
    if sent == 0 then pcall(clear) end
end

-- a paved route that ends far from the place does not serve it: houses up a dirt lane need the dirt roads
function R.reaches(points, target)
    if type(points) ~= "table" or #points < 1 or type(target) ~= "table" then return false end
    local p = points[#points]
    return (p.x - target.x) ^ 2 + (p.y - target.y) ^ 2 <= ENDS_NEAR * ENDS_NEAR
end

-- the bridge refuses points closer than half a tile; a route that has nothing left to drive still has to be a route
function R.spaced(points)
    if type(points) ~= "table" or #points < 2 then return points end
    local out = { points[1] }
    local function far(a, b) return (a.x - b.x) ^ 2 + (a.y - b.y) ^ 2 >= MIN_SPACING * MIN_SPACING end
    for i = 2, #points do
        local p = points[i]
        if far(out[#out], p) then out[#out + 1] = p
        elseif i == #points and #out > 1 then out[#out] = p end
    end
    if #out >= 2 then return out end
    local a, b = points[1], points[#points]
    local dx, dy = b.x - a.x, b.y - a.y
    local len = math.sqrt(dx * dx + dy * dy)
    if len < 0.001 then dx, dy, len = 1, 0, 1 end
    out[2] = { x = a.x + dx / len, y = a.y + dy / len, width = b.width, street = b.street }
    return out
end

-- what the bridge was given, for a refused route
function R.routeDetail(points)
    if type(points) ~= "table" then return "no points" end
    local n, minW, maxW, minGap, bad = #points, nil, nil, nil, 0
    for i = 1, n do
        local p, w = points[i], nil
        local x, y = type(p) == "table" and tonumber(p.x) or nil, type(p) == "table" and tonumber(p.y) or nil
        w = type(p) == "table" and tonumber(p.width) or 0
        if x == nil or y == nil or x < 0 or y < 0 or x > 30000 or y > 30000 then bad = bad + 1 end
        if minW == nil or w < minW then minW = w end
        if maxW == nil or w > maxW then maxW = w end
        if i > 1 and x ~= nil and tonumber(points[i - 1].x) ~= nil then
            local g = math.sqrt((x - points[i - 1].x) ^ 2 + (y - points[i - 1].y) ^ 2)
            if minGap == nil or g < minGap then minGap = g end
        end
    end
    return string.format("points=%d outside=%d width=%s..%s smallest_gap=%s", n, bad, tostring(minW), tostring(maxW), tostring(minGap))
end

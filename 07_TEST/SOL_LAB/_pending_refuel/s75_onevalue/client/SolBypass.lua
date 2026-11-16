-- SolBypass.lua - go around the obstacle that is in front of her, from where she stands.
--
-- Living Fellows' driver only knows the road: when the lane is blocked edge to edge it waits,
-- then asks the road planner for another route with a no-go circle around the obstacle. On a
-- street closed by barriers or a pile of wrecks that means turning round and taking a far longer
-- way - sometimes with no way at all - while the zombies close in.
--
-- A driver does the obvious thing instead: look at the ground round the obstacle, find the
-- opening - the shoulder, the verge, the gap between two parked cars - thread the car through it
-- and come back into the lane.
--
-- v0.4.0 is a real search, not a guess. The first version tried a handful of ready-made sidesteps
-- (2.2, 3.0 ... 5.4 tiles out). A gap narrower than the sidestep it happened to try could never be
-- found, which is exactly why she turned round in front of two parked cars with a car's width
-- between them. Now the ground itself is read:
--
--   1. every square in a window round the car and the rejoin point is marked drivable or not,
--      including the bodies of the other cars (an oriented box, not a circle, so a long car does
--      not swallow the gap beside it),
--   2. a distance transform gives every free square its clearance - how far the nearest blocked
--      square is - so the search knows the width of an opening before it steers into it,
--   3. A* threads the car through, preferring wide openings and tarmac, and is run twice: once
--      wanting a comfortable corridor, and, if nothing fits, once accepting a squeeze (which is
--      then driven slower).
--
-- The world is reached through B.world, so the whole planner runs headless in the behaviour lab
-- against drawn scenes: see 05_TOOLS/sol_behavior_lab/lua_bypass_scenes.py.
--
-- Guarded by the fix switch "drive_bypass".
SolBypass = SolBypass or {}
local B = SolBypass
B.VERSION = "0.7.0"

local LOOK_AHEAD = 16          -- tiles of lane to scan in front of the bumper
local MARGIN = 10              -- how far outside the car/rejoin box the search may wander
local MAX_SIDE = 80            -- hard cap on the window, per axis (a long row of wrecks needs room)
local MAX_NODES = 6000         -- ceiling on the search
local BEHIND = 2.0             -- how far back past her own square the way round may reach
local ESCAPE = 3.0             -- tiles round her own square where any free ground will do to pull out
local REJOIN = 7               -- where the lane is rejoined, past the obstacle
local REJOIN_MAX = 40          -- how far past it is still worth looking for a clear rejoin
local CLEAR_WIDE = 2.0         -- a comfortable corridor: the centre line stays this far from anything
local CLEAR_TIGHT = 1.4         -- a squeeze: the narrowest opening a car body can still be steered through
local CLEAR_IDEAL = 2.6        -- beyond this, extra room buys nothing in the cost
local OFF_TRACK = 0.4          -- leaving the tarmac costs this much per tile, so she prefers road
local VEH_HALF_W = 1.0         -- another car's body: half width
local VEH_HALF_L = 2.2         --                    half length
local VEH_RADIUS = 1.3         -- ... when its facing is unknown
local MAX_POINTS = 48

local function log(m) print("[SolBypass] " .. tostring(m)) end
local function finite(v) return type(v) == "number" and v == v and v ~= math.huge and v ~= -math.huge and v or nil end
local function on(name)
    local A = rawget(_G, "SolAuthority")
    if type(A) ~= "table" or type(A.on) ~= "function" then return false end
    local ok, value = pcall(A.on, name)
    return ok and value == true
end
local function method(o, name, ...)
    if o == nil then return nil end
    local f = o[name]
    if f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end

-- ---------------------------------------------------------------- is this square drivable?
local function flag(name)
    local t = rawget(_G, "IsoFlagType")
    return type(t) == "table" and t[name] or nil
end

-- What a car actually hits on this square, the same way IsoChunk.calcPhysics builds the static physics shapes:
--   "solid"  a whole-square box     "post"  a thin trunk at the centre (trees, lamp posts)     "N","W","NW"  a thin wall along that edge
-- nil means nothing a car collides with.
local function squareKind(sq)
    if sq == nil then return "solid" end
    if method(sq, "isSolid") == true or method(sq, "isSolidTrans") == true then return "solid" end
    local kind = nil
    local objects = method(sq, "getObjects")
    local count = objects and tonumber((method(objects, "size"))) or 0
    for i = 0, math.min(count, 24) - 1 do
        local o = method(objects, "get", i)
        if o ~= nil then
            local sprite = method(o, "getSprite")
            local name = sprite and method(sprite, "getName") or nil
            if type(name) == "string" and (string.find(name, "lighting_outdoor_", 1, true) or name == "recreational_sports_01_21"
                    or name == "recreational_sports_01_19" or name == "recreational_sports_01_32") then
                kind = "post"
            end
            local props = method(o, "getProperties")
            if props ~= nil and props.get ~= nil then
                local shape = method(props, "get", "PhysicsShape")
                if shape == "Solid" then return "solid" end
                if shape == "Tree" then kind = "post" end
                if shape == "WallN" then kind = "N" elseif shape == "WallW" then kind = "W" end
                if method(props, "get", "PhysicsMesh") ~= nil then return "solid" end
            end
            if props ~= nil and props.has ~= nil then
                for _, fname in ipairs({ "solid", "solidtrans" }) do
                    local f = flag(fname)
                    if f ~= nil and method(props, "has", f) == true then return "solid" end
                end
            end
            if type(instanceof) == "function" then
                local okT, isTree = pcall(instanceof, o, "IsoTree")
                if okT and isTree == true then kind = "post" end
                for _, cls in ipairs({ "IsoThumpable", "IsoWindow", "IsoDoor", "IsoWindowFrame" }) do
                    local okC, hit = pcall(instanceof, o, cls)
                    if okC and hit == true then return "solid" end
                end
            end
        end
    end
    local props = method(sq, "getProperties")
    if props ~= nil and props.has ~= nil then
        local function has(n) local f = flag(n); return f ~= nil and method(props, "has", f) == true end
        if has("water") or has("solid") or has("solidtrans") then return "solid" end
        local n, w = has("collideN"), has("collideW")
        if n and w then return "NW" elseif n then return "N" elseif w then return "W" end
    end
    return kind
end

local function squareBlocks(sq)
    if sq == nil then return true, "unloaded" end                 -- not streamed in: never steer into it
    if method(sq, "isSolid") == true or method(sq, "isSolidTrans") == true then return true, "solid" end
    local props = method(sq, "getProperties")
    if props ~= nil then
        for _, name in ipairs({ "water", "collideN", "collideW", "solidtrans", "solid" }) do
            local f = flag(name)
            if f ~= nil then
                -- Build 42's PropertyContainer answers has(flag); Is(flag) is gone and throws, and in
                -- debug mode a thrown Java exception halts the game even inside a pcall. So the
                -- method is looked up first and only a method that exists is ever called.
                local hit = nil
                if props.has ~= nil then hit = method(props, "has", f)
                elseif props.Is ~= nil then hit = method(props, "Is", f) end
                if hit == true then return true, name end
            end
        end
    end
    local objects = method(sq, "getObjects")
    local count = objects and tonumber((method(objects, "size"))) or 0
    for i = 0, math.min(count, 24) - 1 do
        local o = method(objects, "get", i)
        if o ~= nil then
            local oProps = method(o, "getProperties")
            if oProps ~= nil and oProps.has ~= nil then
                for _, name in ipairs({ "solid", "solidtrans", "solidfloor" }) do
                    local f = name ~= "solidfloor" and flag(name) or nil
                    if f ~= nil and method(oProps, "has", f) == true then return true, "object_" .. name end
                end
            end
        end
        if o ~= nil and type(instanceof) == "function" then
            for _, cls in ipairs({ "IsoThumpable", "IsoWindow", "IsoDoor", "IsoTree", "IsoWindowFrame" }) do
                local ok, hit = pcall(instanceof, o, cls)
                if ok and hit == true then return true, cls end
            end
        end
    end
    return false
end

-- ---------------------------------------------------------------- the world, as the planner sees it
-- Every reading of the game goes through this one table, so the search itself is pure Lua and the
-- behaviour lab can hand it a drawn scene instead of a cell.
B.world = {
    --- Is this square open ground a car may stand on?
    open = function(x, y)
        local cell = type(getCell) == "function" and getCell() or nil
        local sq = cell and method(cell, "getGridSquare", math.floor(x), math.floor(y), 0) or nil
        local blocked = squareBlocks(sq)
        return not blocked
    end,

    --- Every other car near (x,y): centre, and facing when the game knows it.
    cars = function(x, y, radius)
        local SC = rawget(_G, "SurvivorCompanion")
        local service = type(SC) == "table" and SC.Vehicle or nil
        if type(service) ~= "table" or type(service.loadedVehicles) ~= "function" then return {} end
        local ok, list = pcall(service.loadedVehicles)
        if not ok or type(list) ~= "table" then return {} end
        local out = {}
        for _, v in ipairs(list) do
            local vx, vy = finite(tonumber((method(v, "getX")))), finite(tonumber((method(v, "getY"))))
            if vx and vy and (vx - x) ^ 2 + (vy - y) ^ 2 <= radius * radius then
                local fx = finite(tonumber((method(v, "getForwardDirectionX"))))
                local fy = finite(tonumber((method(v, "getForwardDirectionY"))))
                local Vec = rawget(_G, "Vector3f")
                local forward = Vec ~= nil and method(v, "getForwardVector", Vec.new()) or nil
                fx = finite(tonumber((method(forward, "x")))) or fx
                fy = finite(tonumber((method(forward, "z")))) or fy
                local extents = method(method(v, "getScript"), "getExtents")
                local long, wide = finite(tonumber((method(extents, "z")))), finite(tonumber((method(extents, "x"))))
                out[#out + 1] = { v = v, x = vx, y = vy, fx = fx, fy = fy, halfL = long and long > 1 and long * 0.5 or nil, halfW = wide and wide > 0.5 and wide * 0.5 or nil }
            end
        end
        return out
    end,

    --- Does this square look like something people drive on? Only a preference, never a rule.
    track = function(x, y)
        local O = rawget(_G, "SolOffroad")
        if type(O) == "table" and type(O.isTrack) == "function" then
            local ok, v = pcall(O.isTrack, x, y)
            if ok then return v == true end
        end
        return false
    end,
}

B.world.kind = function(x, y)
    local cell = type(getCell) == "function" and getCell() or nil
    return squareKind(cell and method(cell, "getGridSquare", math.floor(x), math.floor(y), 0) or nil)
end

--- One square, with nothing of the car's width assumed. Shared with SolOffroad so the detour code
--- and the off-road planner never disagree about what a car may drive over.
function B.squareOpen(x, y)
    local w = B.world
    local ok, open = pcall(w.open, x, y)
    if not ok then return false, "world_error" end
    return open == true
end

-- ---------------------------------------------------------------- the occupancy window
-- A car is a box, not a dot: a sedan lying across the lane is ~4.4 tiles long and ~2 wide, and
-- treating it as a circle big enough to cover its length would also swallow the gap beside it -
-- the very gap she is meant to drive through.
local function carCovers(car, x, y)
    local dx, dy = x - car.x, y - car.y
    local fx, fy = car.fx, car.fy
    if fx == nil or fy == nil or (fx * fx + fy * fy) < 0.01 then
        return (dx * dx + dy * dy) <= VEH_RADIUS * VEH_RADIUS
    end
    local len = math.sqrt(fx * fx + fy * fy)
    fx, fy = fx / len, fy / len
    local along = dx * fx + dy * fy
    local across = dx * (-fy) + dy * fx
    return math.abs(along) <= (car.halfL or VEH_HALF_L) and math.abs(across) <= (car.halfW or VEH_HALF_W)
end

local function buildGrid(x0, y0, x1, y1, cars, mine)
    local w, h = x1 - x0 + 1, y1 - y0 + 1
    local g = { x0 = x0, y0 = y0, w = w, h = h, blocked = {}, dist = {}, track = {}, kind = {} }
    local world = B.world
    for yy = y0, y1 do
        for xx = x0, x1 do
            local i = (yy - y0) * w + (xx - x0) + 1
            if world.kind ~= nil then
                local okK, k = pcall(world.kind, xx, yy)
                if not okK then k = "solid" end
                g.kind[i], g.blocked[i] = k, k ~= nil
            else
                local ok, open = pcall(world.open, xx, yy)
                g.blocked[i] = not (ok and open == true)
                g.kind[i] = g.blocked[i] and "solid" or nil
            end
        end
    end
    for _, spot in ipairs(B.stuckSpots or {}) do
        for yy = math.max(y0, math.floor(spot.y - 2)), math.min(y1, math.floor(spot.y + 2)) do
            for xx = math.max(x0, math.floor(spot.x - 2)), math.min(x1, math.floor(spot.x + 2)) do
                if (xx + 0.5 - spot.x) ^ 2 + (yy + 0.5 - spot.y) ^ 2 <= 1.7 then
                    local si = (yy - y0) * w + (xx - x0) + 1
                    g.blocked[si], g.kind[si] = true, "solid"
                end
            end
        end
    end
    for _, car in ipairs(cars) do
        if mine == nil or car.v ~= mine then
            local reach = math.max(car.halfL or VEH_HALF_L, VEH_RADIUS) + 1
            for yy = math.max(y0, math.floor(car.y - reach)), math.min(y1, math.ceil(car.y + reach)) do
                for xx = math.max(x0, math.floor(car.x - reach)), math.min(x1, math.ceil(car.x + reach)) do
                    if carCovers(car, xx + 0.5, yy + 0.5) then
                        g.blocked[(yy - y0) * w + (xx - x0) + 1] = true
                    end
                end
            end
        end
    end
    return g
end

-- How far is the nearest blocked square? Two chamfer sweeps: cheap, and close enough to a true
-- Euclidean distance for the widths a car cares about.
local FAR = 99
local function clearance(g)
    local w, h, d, blocked = g.w, g.h, g.dist, g.blocked
    for i = 1, w * h do d[i] = blocked[i] and 0 or FAR end
    local function relax(i, j, c)
        local v = d[j] + c
        if v < d[i] then d[i] = v end
    end
    for y = 0, h - 1 do
        for x = 0, w - 1 do
            local i = y * w + x + 1
            if d[i] > 0 then
                if x > 0 then relax(i, i - 1, 1) end
                if y > 0 then relax(i, i - w, 1) end
                if x > 0 and y > 0 then relax(i, i - w - 1, 1.4142) end
                if x < w - 1 and y > 0 then relax(i, i - w + 1, 1.4142) end
            end
        end
    end
    for y = h - 1, 0, -1 do
        for x = w - 1, 0, -1 do
            local i = y * w + x + 1
            if d[i] > 0 then
                if x < w - 1 then relax(i, i + 1, 1) end
                if y < h - 1 then relax(i, i + w, 1) end
                if x < w - 1 and y < h - 1 then relax(i, i + w + 1, 1.4142) end
                if x > 0 and y < h - 1 then relax(i, i + w - 1, 1.4142) end
            end
        end
    end
    -- the window's own edge is not a wall, but nothing beyond it is known either
    return g
end

--- The clearance of one world square, in tiles: 0 is blocked, 1 is hard against something,
--- 2 is the middle of a three-wide corridor. Exposed for the behaviour lab.
function B.clearanceAt(g, x, y)
    local xi, yi = math.floor(x) - g.x0, math.floor(y) - g.y0
    if xi < 0 or yi < 0 or xi >= g.w or yi >= g.h then return nil end
    return g.dist[yi * g.w + xi + 1]
end

-- ---------------------------------------------------------------- the search
local NEIGHBOURS = {
    { 1, 0, 1 }, { -1, 0, 1 }, { 0, 1, 1 }, { 0, -1, 1 },
    { 1, 1, 1.4142 }, { 1, -1, 1.4142 }, { -1, 1, 1.4142 }, { -1, -1, 1.4142 },
}

-- A small binary heap keyed on f: the window can hold several thousand squares, and a linear scan
-- for the cheapest open node would make a long row of cars cost seconds in Kahlua.
local function heapPush(h, node)
    h[#h + 1] = node
    local i = #h
    while i > 1 do
        local p = math.floor(i / 2)
        if h[p].f <= h[i].f then break end
        h[p], h[i] = h[i], h[p]
        i = p
    end
end
local function heapPop(h)
    local n = #h
    if n == 0 then return nil end
    local top = h[1]
    h[1] = h[n]
    h[n] = nil
    n = n - 1
    local i = 1
    while true do
        local l, r, m = i * 2, i * 2 + 1, i
        if l <= n and h[l].f < h[m].f then m = l end
        if r <= n and h[r].f < h[m].f then m = r end
        if m == i then break end
        h[m], h[i] = h[i], h[m]
        i = m
    end
    return top
end

local function search(g, sx, sy, gx, gy, need, trackCache, fx, fy)
    local w, h, d = g.w, g.h, g.dist
    local startI = (sy - g.y0) * w + (sx - g.x0) + 1
    local goalI = (gy - g.y0) * w + (gx - g.x0) + 1
    if d[goalI] < need then return nil, "rejoin_too_tight" end

    local function trackish(i, x, y)
        local v = trackCache[i]
        if v == nil then
            local ok, t = pcall(B.world.track, x, y)
            v = (ok and t == true)
            trackCache[i] = v
        end
        return v
    end
    local function heuristic(x, y) return math.sqrt((x - gx) ^ 2 + (y - gy) ^ 2) end
    -- The car is already standing where it stands, often nose to nose with the wreck. Close to its
    -- own square any free ground will do to pull out; the corridor rule applies once it is clear.
    local function allowed(ni, nx, ny)
        -- A way round goes forward: a route that starts by driving away behind her is the long
        -- detour the road planner already offers, not a bypass.
        if (nx - sx) * fx + (ny - sy) * fy < -BEHIND then return false end
        if d[ni] >= need then return true end
        return d[ni] >= 1 and (nx - sx) ^ 2 + (ny - sy) ^ 2 <= ESCAPE * ESCAPE
    end

    local best = {}
    local heap = {}
    best[startI] = 0
    heapPush(heap, { i = startI, x = sx, y = sy, g = 0, f = heuristic(sx, sy) })
    local came, closed, count = {}, {}, 0
    while count < MAX_NODES do
        local cur = heapPop(heap)
        if cur == nil then return nil, "no_way_round" end
        if not closed[cur.i] then
            if cur.i == goalI then
                local tiles, i, guard = {}, cur.i, 0
                while i ~= nil and guard < MAX_NODES do
                    local xi = (i - 1) % w
                    local yi = math.floor((i - 1) / w)
                    table.insert(tiles, 1, { x = xi + g.x0, y = yi + g.y0 })
                    i = came[i]
                    guard = guard + 1
                end
                return tiles
            end
            closed[cur.i] = true
            count = count + 1
            for _, step in ipairs(NEIGHBOURS) do
                local nx, ny = cur.x + step[1], cur.y + step[2]
                local xi, yi = nx - g.x0, ny - g.y0
                if xi >= 0 and yi >= 0 and xi < w and yi < h then
                    local ni = yi * w + xi + 1
                    if not closed[ni] and allowed(ni, nx, ny) then
                        local tight = math.max(0, CLEAR_IDEAL - d[ni])
                        local cost = step[3] * (1 + 0.8 * tight) + (trackish(ni, nx, ny) and 0 or OFF_TRACK)
                        local gScore = cur.g + cost
                        if best[ni] == nil or gScore < best[ni] then
                            best[ni] = gScore
                            came[ni] = cur.i
                            heapPush(heap, { i = ni, x = nx, y = ny, g = gScore, f = gScore + heuristic(nx, ny) })
                        end
                    end
                end
            end
        end
    end
    return nil, "search_exhausted"
end

--- Drop the points in the middle of a straight run: the follower steers better with few.
function B.simplify(points)
    if type(points) ~= "table" or #points < 3 then return points end
    local out = { points[1] }
    for i = 2, #points - 1 do
        local a, b, c = out[#out], points[i], points[i + 1]
        local abx, aby = b.x - a.x, b.y - a.y
        local bcx, bcy = c.x - b.x, c.y - b.y
        local la = math.sqrt(abx * abx + aby * aby)
        local lb = math.sqrt(bcx * bcx + bcy * bcy)
        local straight = la > 0 and lb > 0 and ((abx / la) * (bcx / lb) + (aby / la) * (bcy / lb)) > 0.999
        if not straight then out[#out + 1] = b end
    end
    out[#out + 1] = points[#points]
    while #out > MAX_POINTS do
        local thinned = { out[1] }
        for i = 2, #out - 1, 2 do thinned[#thinned + 1] = out[i] end
        thinned[#thinned + 1] = out[#out]
        out = thinned
    end
    return out
end

--- Plan one way round a thing at (hx,hy) for a car standing at (cx,cy).
-- What the native follower needs (SCRoadFollower, read from SolCombined.jar and proven in 05_TOOLS/sol_drive_sim):
--   * width 0 on every point: any lane width lets it slide off the proven squares (in the simulator, width 2 to 5 hit the wreck);
--   * with something close ahead of the bumper it will not roll forward whatever the route says, and it does not back away.
--     A first leg more than 60 degrees off the car's heading makes it do a three-point turn onto that leg: the only way out.
local DETOUR_WIDTH = 0
local NEEDS_TURN_GAP, TURN_ANGLE, TURN_STUB = 4.0, math.rad(68), 3.0

--- The end of a steep first leg on proven ground: on the side the path leaves by, else the other.
local function turnStub(g, cx, cy, heading, first)
    local fx, fy = first.x + 0.5 - cx, first.y + 0.5 - cy
    local sign = (heading.x * fy - heading.y * fx) >= 0 and 1 or -1
    for _ = 1, 2 do
        local ca, sa = math.cos(TURN_ANGLE * sign), math.sin(TURN_ANGLE * sign)
        local dx, dy = heading.x * ca - heading.y * sa, heading.x * sa + heading.y * ca
        local open, d = true, 1.0
        while d <= TURN_STUB do
            local c = B.clearanceAt(g, math.floor(cx + dx * d), math.floor(cy + dy * d))
            if c == nil or c < CLEAR_TIGHT then open = false break end
            d = d + 0.5
        end
        if open then return cx + dx * TURN_STUB, cy + dy * TURN_STUB end
        sign = -sign
    end
    return nil
end

-- A path a car can really drive. The square-by-square search draws corners no car can take: a van turns on a circle some ten tiles
-- across. This one searches the car's own moves (short arcs forward at a few wheel angles), carrying its heading, and checks the whole
-- body against the clearance grid at every step. Forward only: when nothing fits from where she stands, the driver backs out first.
local ARC_STEP, ARC_SUB = 0.8, 2
local ARC_FRACTIONS = { 0, 0.25, -0.25, 0.55, -0.55, 0.95, -0.95 }    -- of the sharpest turn this car can make: from a touch of wheel to full lock
local ARC_BINS, ARC_NODES = 24, 12000
local ARC_BUDGET_MS = 800                 -- a plan may cost one short hitch, never a freeze
local function clockMs()
    local f = rawget(_G, "getTimestampMs")
    if type(f) == "function" then return f() end
    return os.clock() * 1000
end
local BODY_PAD = 0.45                     -- spare room when the ground has it; a tight gap is tried again with 0.12

local function pointFree(walls, cars, px, py)
    local xi, yi = math.floor(px) - walls.x0, math.floor(py) - walls.y0
    if xi < 0 or yi < 0 or xi >= walls.w or yi >= walls.h then return false end
    local k = walls.kind[yi * walls.w + xi + 1]
    local fx, fy = px - math.floor(px), py - math.floor(py)
    if k == "solid" then return false end
    if k == "post" and (fx - 0.5) ^ 2 + (fy - 0.5) ^ 2 <= 0.1225 then return false end
    if (k == "N" or k == "NW") and fy < 0.13 then return false end
    if (k == "W" or k == "NW") and fx < 0.13 then return false end
    if fy > 0.87 and yi + 1 < walls.h then
        local below = walls.kind[(yi + 1) * walls.w + xi + 1]
        if below == "N" or below == "NW" then return false end
    end
    if fx > 0.87 and xi + 1 < walls.w then
        local right = walls.kind[yi * walls.w + xi + 2]
        if right == "W" or right == "NW" then return false end
    end
    for i = 1, #cars do
        if carCovers(cars[i], px, py) then return false end
    end
    return true
end

-- Cheap first: the car as a row of circles against the clearance grid decides almost every pose in a few lookups.
-- Only a pose close enough for the answer to matter gets the exact box, sampled every quarter tile round its edge.
local function bodyFree(g, walls, cars, x, y, hx, hy, halfL, halfW, pad)
    local L, W = halfL + pad, halfW + pad
    local sure, a = true, -(L - W)
    while true do
        local c = B.clearanceAt(g, x + hx * a, y + hy * a)
        if c == nil then return false end
        if c < W + 1.5 then sure = false end
        if a >= L - W then break end
        a = math.min(L - W, a + W)
    end
    if sure then return true end
    a = -L
    while a < L do
        if not pointFree(walls, cars, x + hx * a + hy * W, y + hy * a - hx * W) then return false end
        if not pointFree(walls, cars, x + hx * a - hy * W, y + hy * a + hx * W) then return false end
        a = a + 0.25
    end
    local b = -W
    while b <= W do
        if not pointFree(walls, cars, x + hx * L - hy * b, y + hy * L + hx * b) then return false end
        if not pointFree(walls, cars, x - hx * L - hy * b, y - hy * L + hx * b) then return false end
        b = b + 0.25
    end
    return true
end

local function heapUp(h, n)
    local i = #h + 1
    h[i] = n
    while i > 1 do
        local p = math.floor(i / 2)
        if h[p].f <= h[i].f then break end
        h[p], h[i] = h[i], h[p]
        i = p
    end
end
local function heapPopMin(h)
    local top, last = h[1], h[#h]
    h[#h] = nil
    if #h > 0 then
        h[1] = last
        local i = 1
        while true do
            local a, b, m = i * 2, i * 2 + 1, i
            if h[a] and h[a].f < h[m].f then m = a end
            if h[b] and h[b].f < h[m].f then m = b end
            if m == i then break end
            h[m], h[i] = h[i], h[m]
            i = m
        end
    end
    return top
end

local function curvedPath(g, walls, cars, cx, cy, heading, gx, gy, fx, fy, pad)
    local halfL, halfW = heading.halfLength or 2.8, heading.halfWidth or 1.1
    local th0 = math.atan2(heading.y, heading.x)
    local kmax = heading.kmax or (math.tan(0.6) / (1.2 * halfL))
    -- only a car already standing inside the margin gets to ease out of it
    local hemmedIn = not bodyFree(g, walls, cars, cx, cy, heading.x, heading.y, halfL, halfW, pad)
    local function bin(th) local tau = 2 * math.pi; local a = ((th % tau) + tau) % tau; return math.floor((a / tau) * ARC_BINS + 0.5) % ARC_BINS end   -- the game's % keeps the sign of th
    local function key(x, y, th) return (math.floor(x * 2) * 100000 + math.floor(y * 2)) * ARC_BINS + bin(th) end
    local start = { x = cx, y = cy, th = th0, g = 0, kappa = 0, f = math.sqrt((gx - cx) ^ 2 + (gy - cy) ^ 2) }
    local open, seen, count, began = { start }, {}, 0, clockMs()
    while #open > 0 and count < ARC_NODES do
        if count % 64 == 63 and clockMs() - began > ARC_BUDGET_MS then
            log("curved search out of time after " .. tostring(count) .. " nodes")
            return nil
        end
        local n = heapPopMin(open)
        local k = key(n.x, n.y, n.th)
        if not seen[k] then
            seen[k], count = true, count + 1
            if (n.x - gx) ^ 2 + (n.y - gy) ^ 2 <= 9 and math.cos(n.th) * fx + math.sin(n.th) * fy > 0.2 then
                local rev, out = {}, {}
                while n do rev[#rev + 1] = n; n = n.parent end
                for i = #rev, 1, -1 do out[#out + 1] = { x = rev[i].x, y = rev[i].y, width = 0 } end
                log(string.format("curved search: %d nodes in %d ms", count, clockMs() - began))
                B.lastNodes = count
                return out
            end
            for _, fraction in ipairs(ARC_FRACTIONS) do
                local kappa = fraction * kmax
                local x, y, th, ok = n.x, n.y, n.th, true
                local ds = ARC_STEP / ARC_SUB
                for _ = 1, ARC_SUB do
                    th = th + kappa * ds
                    x, y = x + math.cos(th) * ds, y + math.sin(th) * ds
                    if not bodyFree(g, walls, cars, x, y, math.cos(th), math.sin(th), halfL, halfW, (hemmedIn and n.g < 2.4) and 0.05 or pad) then ok = false break end
                end
                if ok and not seen[key(x, y, th)] then
                    local cost = n.g + ARC_STEP * (1 + (kappa ~= 0 and 0.15 or 0) + math.abs(kappa - n.kappa) * 3)
                    heapUp(open, { x = x, y = y, th = th, g = cost, parent = n, kappa = kappa,
                        f = cost + 1.6 * math.sqrt((gx - x) ^ 2 + (gy - y) ^ 2) })
                end
            end
        end
    end
    return nil
end

--- Points further along her road, nearest first: where she can rejoin it. Road width and curves come with the route itself.
function B.roadAhead(path, cx, cy)
    local best, at = nil, 1
    for i = 1, #path - 1 do
        local a, b = path[i], path[i + 1]
        local dx, dy = b.x - a.x, b.y - a.y
        local len2 = dx * dx + dy * dy
        local t = len2 > 0 and math.max(0, math.min(1, ((cx - a.x) * dx + (cy - a.y) * dy) / len2)) or 0
        local px, py = a.x + dx * t, a.y + dy * t
        local d = (px - cx) ^ 2 + (py - cy) ^ 2
        if best == nil or d < best then best, at = d, i end
    end
    local out, walked, i, x, y = {}, 0, at, cx, cy
    while i < #path and walked < 46 do
        local b = path[i + 1]
        local dx, dy = b.x - x, b.y - y
        local len = math.sqrt(dx * dx + dy * dy)
        if len > 0.01 then
            local s = 1
            while s <= len and walked + s <= 46 do
                if walked + s >= 8 then
                    out[#out + 1] = { x = x + dx / len * s, y = y + dy / len * s, tx = dx / len, ty = dy / len }
                end
                s = s + 1
            end
            walked = walked + len
        end
        x, y, i = b.x, b.y, i + 1
    end
    return #out > 0 and out or nil
end

--- She stopped making progress here: remember what is just past her nose, so the next plan cannot be the same one.
function B.noteStuck(x, y, hx, hy, halfLength)
    local reach = (halfLength or 2.8) + 0.8
    local now, kept = clockMs(), {}
    for _, s in ipairs(B.stuckSpots or {}) do
        if now - s.at < 180000 then kept[#kept + 1] = s end
    end
    kept[#kept + 1] = { x = x + hx * reach, y = y + hy * reach, at = now }
    while #kept > 12 do table.remove(kept, 1) end
    B.stuckSpots = kept
    log(string.format("learned: stuck at %.1f,%.1f, nose spot %.1f,%.1f is closed now (%d remembered)", x, y, kept[#kept].x, kept[#kept].y, #kept))
end

--- Pure: everything it knows about the world comes from B.world, so the lab can drive it.
--- @return table|nil points  world points for SC.Driving.followRoute
--- @return string            the reason it failed, or "clear"/"squeeze" when it succeeded
function B.route(cx, cy, hx, hy, mine, heading)
    cx, cy, hx, hy = finite(cx), finite(cy), finite(hx), finite(hy)
    if not cx or not cy or not hx or not hy then return nil, "bad_coordinates" end
    local fx, fy = hx - cx, hy - cy
    local ahead = math.sqrt(fx * fx + fy * fy)
    local alongRoad = nil
    if heading and heading.curved and type(heading.path) == "table" and #heading.path >= 2 then
        alongRoad = B.roadAhead(heading.path, cx, cy)
    end
    if alongRoad == nil and (ahead < 0.5 or ahead > LOOK_AHEAD + 6) then return nil, "obstacle_out_of_reach" end
    if ahead < 0.5 then fx, fy, ahead = heading.x, heading.y, 1 end
    fx, fy = fx / ahead, fy / ahead

    -- The window covers her, the obstacle and the whole stretch past it where the lane may be
    -- picked up again: a row of wrecks can run twenty-five tiles, and the rejoin has to be past
    -- the last of them, not inside the second.
    local sx, sy = math.floor(cx), math.floor(cy)
    local far_x, far_y = math.floor(hx + fx * REJOIN_MAX), math.floor(hy + fy * REJOIN_MAX)
    if alongRoad then
        far_x, far_y = sx, sy
        local minX, maxX, minY, maxY = sx, sx, sy, sy
        for _, c in ipairs(alongRoad) do
            local cxi, cyi = math.floor(c.x), math.floor(c.y)
            if math.max(maxX, cxi) - math.min(minX, cxi) > MAX_SIDE - 2 * MARGIN - 1 or math.max(maxY, cyi) - math.min(minY, cyi) > MAX_SIDE - 2 * MARGIN - 1 then break end
            minX, maxX, minY, maxY = math.min(minX, cxi), math.max(maxX, cxi), math.min(minY, cyi), math.max(maxY, cyi)
            far_x, far_y = cxi, cyi
        end
    end
    -- an obstacle remembered from further back must not stretch the window over half the town
    local winX, winY = math.floor(hx), math.floor(hy)
    if alongRoad and ahead > LOOK_AHEAD + 6 then winX, winY = sx, sy end
    local x0 = math.min(sx, far_x, winX) - MARGIN
    local x1 = math.max(sx, far_x, winX) + MARGIN
    local y0 = math.min(sy, far_y, winY) - MARGIN
    local y1 = math.max(sy, far_y, winY) + MARGIN
    if (x1 - x0) > MAX_SIDE or (y1 - y0) > MAX_SIDE then
        log(string.format("window too big from %.1f,%.1f: %d by %d, obstacle %.1f,%.1f", cx, cy, x1 - x0, y1 - y0, hx, hy))
        B.dumpMap(cx, cy, "window_too_big")
        return nil, "window_too_big"
    end

    local okCars, cars = pcall(B.world.cars, (x0 + x1) * 0.5, (y0 + y1) * 0.5, (x1 - x0) + (y1 - y0))
    if not okCars or type(cars) ~= "table" then cars = {} end

    local g = clearance(buildGrid(x0, y0, x1, y1, cars, mine))
    -- The car is standing where it stands: its own square is given, whatever the grid thinks.
    local startI = (sy - y0) * g.w + (sx - x0) + 1
    if g.dist[startI] < CLEAR_TIGHT then g.dist[startI] = CLEAR_TIGHT end

    -- Where the lane is picked up again: the first square past the obstacle - and past anything
    -- parked behind it - that has room for the car, judged on the same grid as the search.
    local function rejoinFor(need)
        if alongRoad then
            for _, c in ipairs(alongRoad) do
                local v = B.clearanceAt(g, c.x, c.y)
                local past = ahead > LOOK_AHEAD + 6 or (c.x - hx) * c.tx + (c.y - hy) * c.ty >= REJOIN      -- rejoin beyond the thing, not before it
                if v ~= nil and v >= need and past then fx, fy = c.tx, c.ty; return math.floor(c.x), math.floor(c.y) end
            end
            return nil
        end
        for reach = REJOIN, REJOIN_MAX do
            local px, py = math.floor(hx + fx * reach), math.floor(hy + fy * reach)
            local c = B.clearanceAt(g, px, py)
            if c ~= nil and c >= need then return px, py end
        end
        return nil
    end

    -- the car swings its nose and tail wider than its centre line: leave real room whenever the ground has it
    local wallsOnly = nil
    for _, need in ipairs({ CLEAR_WIDE, CLEAR_TIGHT }) do
        local rx, ry = rejoinFor(heading and heading.curved and math.max(need, (heading.halfLength or 2.8) + 1.2) or need)
        if heading and heading.curved then
            if rx ~= nil then
                local others = {}
                for _, c in ipairs(cars) do
                    if mine == nil or c.v ~= mine then others[#others + 1] = c end
                end
                wallsOnly = wallsOnly or buildGrid(x0, y0, x1, y1, {}, mine)
                -- first with room to spare, then with the car's true width: a real gap must read as a gap
                local path = curvedPath(g, wallsOnly, others, cx, cy, heading, rx + 0.5, ry + 0.5, fx, fy, need >= CLEAR_WIDE and BODY_PAD or 0.12)
                if path then
                    local shown = {}
                    for i = 1, math.min(#path, 8) do shown[i] = string.format("%.0f,%.0f", path[i].x, path[i].y) end
                    log(string.format("curved way round %d,%d from %.1f,%.1f heading %.2f,%.2f: %d points (%s) %s", math.floor(hx), math.floor(hy), cx, cy,
                        heading.x, heading.y, #path, need >= CLEAR_WIDE and "clear" or "squeeze", table.concat(shown, " ")))
                    return path, (need >= CLEAR_WIDE) and "clear" or "squeeze"
                end
            end
        else
        local tiles, why = nil, "nowhere_to_rejoin"
        if rx ~= nil then tiles, why = search(g, sx, sy, rx, ry, need, {}, fx, fy) end
        if type(tiles) == "table" and #tiles >= 2 then
            local points = {}
            for i, t in ipairs(tiles) do points[i] = { x = t.x + 0.5, y = t.y + 0.5, width = 0 } end
            points[1] = { x = cx, y = cy, width = 0 }
            points = B.simplify(points)
            local turned = false
            local gap = heading and ((hx - cx) * heading.x + (hy - cy) * heading.y - (heading.halfLength or 2.8)) or nil
            if gap and gap <= NEEDS_TURN_GAP then
                local tx, ty = turnStub(g, cx, cy, heading, tiles[2])
                local after = tx and search(g, math.floor(tx), math.floor(ty), rx, ry, need, {}, fx, fy) or nil
                if type(after) == "table" and #after >= 2 then
                    local rest = {}
                    for i, t in ipairs(after) do rest[i] = { x = t.x + 0.5, y = t.y + 0.5, width = 0 } end
                    rest[1] = { x = tx, y = ty, width = 0 }
                    rest = B.simplify(rest)
                    points = { { x = cx, y = cy, width = 0 } }
                    for _, p in ipairs(rest) do points[#points + 1] = p end
                    turned = true
                end
            end
            for _, p in ipairs(points) do p.width = DETOUR_WIDTH end
            local narrowest = FAR
            for _, t in ipairs(tiles) do
                local c = B.clearanceAt(g, t.x, t.y) or 0
                if c < narrowest then narrowest = c end
            end
            local how = (need >= CLEAR_WIDE) and "clear" or "squeeze"
            log(string.format("round the obstacle at %d,%d: %d points, narrowest gap %.1f tiles (%s) three-point=%s",
                math.floor(hx), math.floor(hy), #points, narrowest, how, tostring(turned)))
            return points, how
        end
        if why == "search_exhausted" then return nil, why end
        end
    end
    do
        local now = clockMs()
        if not B.mapLoggedAt or now - B.mapLoggedAt > 5000 then
            B.mapLoggedAt = now
            log(string.format("no way round from %.1f,%.1f: the ground (# blocked, S her, each row is y, x from %d):", cx, cy, sx - 14))
            for yy = sy - 12, sy + 12 do
                local row = {}
                for xx = sx - 14, sx + 14 do
                    local c = B.clearanceAt(g, xx, yy)
                    local ki = (yy - g.y0) * g.w + (xx - g.x0) + 1
                    local kk = c ~= nil and g.kind[ki] or nil
                    row[#row + 1] = (xx == sx and yy == sy) and "S" or (c == nil and "?" or (kk == "post" and "o" or (kk == "N" and "-" or (kk == "W" and "|" or (kk == "NW" and "+" or (c < 1 and "#" or "."))))))
                end
                log(tostring(yy) .. " " .. table.concat(row))
            end
        end
    end
    return nil, "no_way_round"
end

--- One frame of driving the detour by hand. st = { points, i }. Returns steering (-1 left .. +1 right) and km/h, or nil when done.
--- The native follower's lane scan keeps stopping her beside a wreck the proven path clears, so the detour is steered directly.
function B.steerStep(st, x, y, hx, hy)
    local pts = st.points
    while st.i <= #pts do
        local p = pts[st.i]
        local reach = st.i == #pts and 1.5 or 2.0
        if (p.x - x) ^ 2 + (p.y - y) ^ 2 > reach * reach then break end
        st.i = st.i + 1
    end
    local p = pts[st.i]
    if p == nil then return nil end
    local aim = math.atan2(p.y - y, p.x - x) - math.atan2(hy, hx)
    while aim > math.pi do aim = aim - 2 * math.pi end
    while aim < -math.pi do aim = aim + 2 * math.pi end
    local steer = math.max(-1, math.min(1, 2.5 * aim))
    -- as fast as the bend allows: nearly straight she keeps going, on full lock she crawls
    return steer, math.abs(aim) > 0.6 and 4 or (math.abs(aim) > 0.2 and 7 or 12)
end

--- Is the ground just past the nose open? Walls and fences only: other cars are the planner's business.
function B.aheadClear(x, y, hx, hy, halfLength)
    local reach = (halfLength or 2.8) + 0.15
    for _, side in ipairs({ -0.9, 0, 0.9 }) do
        if not B.squareOpen(x + hx * reach - hy * side, y + hy * reach + hx * side) then return false end
    end
    return true
end

--- A short forward move at an angle, away from the obstacle, on proven squares. Used when no way round was found.
function B.nudge(cx, cy, hx, hy, ox, oy)
    -- The obstacle is usually dead ahead, so "away from it" is no answer: measure the room on each side instead,
    -- and if she is still here after trying one side, the next try is the other side.
    local function direction(sign)
        local a = math.rad(50) * sign
        return hx * math.cos(a) - hy * math.sin(a), hx * math.sin(a) + hy * math.cos(a)
    end
    local function room(sign)
        local dx, dy = direction(sign)
        local d = 1.0
        while d <= 9.0 do
            for _, side in ipairs({ -1.0, 0, 1.0 }) do
                if not B.squareOpen(cx + dx * d - dy * side, cy + dy * d + dx * side) then return d - 0.5 end
            end
            d = d + 0.5
        end
        return d
    end
    local right, left = room(1), room(-1)
    local first = right >= left and 1 or -1
    local now, last = clockMs(), B.lastNudge
    if last and now - last.at < 90000 and (last.x - cx) ^ 2 + (last.y - cy) ^ 2 <= 100 then first = -last.sign end
    for _, sign in ipairs({ first, -first }) do
        if (sign == 1 and right or left) >= 5.0 then
            local dx, dy = direction(sign)
            B.lastNudge = { x = cx, y = cy, at = now, sign = sign }
            log(string.format("nudge %s (room right %.1f, left %.1f)", sign == 1 and "right" or "left", right, left))
            return { { x = cx, y = cy, width = 0 }, { x = cx + dx * 4.5, y = cy + dy * 4.5, width = 0 } }
        end
    end
    return nil
end

--- The car she has just taken, measured from its own script: body, wheelbase from the wheel positions, steering lock. Logged once per car.
function B.measure(vehicle)
    local script = method(vehicle, "getScript")
    if script == nil then return nil end
    local extents = method(script, "getExtents")
    local long, wide = finite(tonumber((method(extents, "z")))), finite(tonumber((method(extents, "x"))))
    local halfL = long and long > 1 and long * 0.5 or 2.8
    local halfW = wide and wide > 0.5 and wide * 0.5 or 1.1
    local front, rear = nil, nil
    local count = tonumber((method(script, "getWheelCount"))) or 0
    for i = 0, math.min(count, 8) - 1 do
        local z = finite(tonumber((method(method(method(script, "getWheel", i), "getOffset"), "z"))))
        if z then
            front = front and math.max(front, z) or z
            rear = rear and math.min(rear, z) or z
        end
    end
    local wheelbase = front and rear and front - rear > 1 and front - rear or 1.2 * halfL
    local clamp = finite(tonumber((method(script, "getSteeringClamp", 5))))
    if not clamp or clamp <= 0.15 or clamp >= 1.2 then clamp = 0.6 end
    local size = { halfLength = halfL, halfWidth = halfW, wheelbase = wheelbase, clamp = clamp, kmax = math.tan(clamp) / wheelbase }
    if B.measured ~= vehicle then
        B.measured = vehicle
        log(string.format("measured the car: %.2f long, %.2f wide, wheelbase %.2f, steering lock %.2f, turning radius %.1f", halfL * 2, halfW * 2, wheelbase, clamp, 1 / size.kmax))
    end
    return size
end

--- The ground round her as the planner reads it, in the log, for any failure.
function B.dumpMap(cx, cy, why)
    local now = clockMs()
    if B.mapLoggedAt and now - B.mapLoggedAt < 5000 then return end
    B.mapLoggedAt = now
    log(string.format("no plan (%s) from %.1f,%.1f; # solid, o post, - | + thin edge, S her; x from %d:", tostring(why), cx, cy, math.floor(cx) - 14))
    local kinds = { solid = "#", post = "o", N = "-", W = "|", NW = "+" }
    for yy = math.floor(cy) - 12, math.floor(cy) + 12 do
        local row = {}
        for xx = math.floor(cx) - 14, math.floor(cx) + 14 do
            local ok, k = pcall(B.world.kind or function() return nil end, xx, yy)
            row[#row + 1] = (xx == math.floor(cx) and yy == math.floor(cy)) and "S" or (ok and k and (kinds[k] or "#") or ".")
        end
        log(tostring(yy) .. " " .. table.concat(row))
    end
end

--- Walks her road ahead, across her car's whole swept width at the line she is really driving, and returns the first thing in the way.
local SCAN_MAX_SIDE = 4
function B.scanAhead(path, x, y, reach, halfLength, halfWidth)
    if type(path) ~= "table" or #path < 2 then return nil end
    local best, at, side = nil, 1, 0
    for i = 1, #path - 1 do
        local a, b = path[i], path[i + 1]
        local dx, dy = b.x - a.x, b.y - a.y
        local len2 = dx * dx + dy * dy
        local u = len2 > 0 and math.max(0, math.min(1, ((x - a.x) * dx + (y - a.y) * dy) / len2)) or 0
        local px, py = a.x + dx * u, a.y + dy * u
        local d = (px - x) ^ 2 + (py - y) ^ 2
        if best == nil or d < best then
            local len = math.sqrt(len2)
            best, at, side = d, i, len > 0 and ((x - px) * (-dy) + (y - py) * dx) / len or 0
        end
    end
    if on("road_first") and math.abs(side) > SCAN_MAX_SIDE then return nil end      -- not on the road yet: nothing on the road's line says anything about where she is
    local okC, cars = pcall(B.world.cars, x, y, reach + 6)
    if not okC or type(cars) ~= "table" then cars = {} end
    local cache = {}
    local function hit(px, py)
        local fx0, fy0 = math.floor(px), math.floor(py)
        local key = fx0 * 100000 + fy0
        local k = cache[key]
        if k == nil then
            if B.world.kind then
                local ok, v = pcall(B.world.kind, fx0, fy0)
                k = ok and v or false
            else
                local ok, open = pcall(B.world.open, fx0, fy0)
                k = not (ok and open == true) and "solid" or false
            end
            cache[key] = k
        end
        local fx, fy = px - fx0, py - fy0
        if k == "solid" then return "solid" end
        if k == "post" and (fx - 0.5) ^ 2 + (fy - 0.5) ^ 2 <= 0.1225 then return "post" end
        for i = 1, #cars do
            if (cars[i].v == nil or cars[i].v ~= B.measured) and carCovers(cars[i], px, py) then
                local speed = on("road_first") and math.abs(tonumber((method(cars[i].v, "getCurrentSpeedKmHour"))) or 0) or 0
                if speed <= 2 then return "car" end
            end
        end
        return false
    end
    local walked, i, sx, sy, start = 0, at, x, y, (halfLength or 2.8) + 1.0
    if on("road_first") then                                                        -- the sideways shift is added below: start from the road's line, or the first stretch counts it twice
        local p, q = path[at], path[at + 1]
        local ex, ey = q.x - p.x, q.y - p.y
        local l2 = ex * ex + ey * ey
        local u = l2 > 0 and math.max(0, math.min(1, ((x - p.x) * ex + (y - p.y) * ey) / l2)) or 0
        sx, sy = p.x + ex * u, p.y + ey * u
    end
    while i < #path and walked < reach do
        local b = path[i + 1]
        local dx, dy = b.x - sx, b.y - sy
        local len = math.sqrt(dx * dx + dy * dy)
        if len > 0.01 then
            local ux, uy = dx / len, dy / len
            local s = 0.5
            while s <= len do
                local dist = walked + s
                if dist >= start and dist <= reach then
                    local cx0, cy0 = sx + ux * s - uy * side, sy + uy * s + ux * side
                    local across = -(halfWidth or 1.1)
                    while across <= (halfWidth or 1.1) + 0.01 do
                        local what = hit(cx0 - uy * across, cy0 + ux * across)
                        if what then return dist, cx0, cy0, what end
                        across = across + 0.5
                    end
                end
                s = s + 0.5
            end
            walked = walked + len
        end
        sx, sy, i = b.x, b.y, i + 1
    end
    return nil
end

--- The game-side entry: read the car, the lane scan and the obstacle, then plan.
--- @return table|nil points, string reason/how
function B.plan(actor, vehicle, status)
    if not on("drive_bypass") then return nil, "switch_off" end
    local SC = rawget(_G, "SurvivorCompanion")
    local D = type(SC) == "table" and SC.Driving or nil
    if type(D) ~= "table" or type(D.scanLane) ~= "function" then return nil, "driving_unavailable" end

    local cx = finite(tonumber((method(vehicle, "getX"))))
    local cy = finite(tonumber((method(vehicle, "getY"))))
    if not cx or not cy then return nil, "no_car_position" end

    local scan = D.scanLane(actor, LOOK_AHEAD)
    if type(scan) ~= "table" then scan = {} end
    local hx = finite(tonumber(scan.obstacleX)) or finite(tonumber(status and status.blockedX))
    local hy = finite(tonumber(scan.obstacleY)) or finite(tonumber(status and status.blockedY))
    local heading = nil
    local Vec = rawget(_G, "Vector3f")
    local forward = Vec ~= nil and method(vehicle, "getForwardVector", Vec.new()) or nil
    local dx, dy = finite(tonumber((method(forward, "x")))), finite(tonumber((method(forward, "z"))))
    local length = dx and dy and math.sqrt(dx * dx + dy * dy) or 0
    if length > 0.001 then
        heading = { x = dx / length, y = dy / length, halfLength = 2.8, halfWidth = 1.1, curved = true, path = status and status.routePoints or nil }
        local size = B.measure(vehicle)
        if size then heading.halfLength, heading.halfWidth, heading.kmax = size.halfLength, size.halfWidth, size.kmax end
    end
    -- the safety stop can report no position: the thing is right in front of the bumper
    if (not hx or not hy) and heading then
        hx, hy = cx + heading.x * (heading.halfLength + 1.5), cy + heading.y * (heading.halfLength + 1.5)
    end
    if not hx or not hy then B.dumpMap(cx, cy, "no_obstacle_position"); return nil, "no_obstacle_position" end
    if tostring(scan.obstacleKind or "") == "unloaded" then return nil, "obstacle_unloaded" end

    return B.route(cx, cy, hx, hy, vehicle, heading)
end

log("ready v" .. B.VERSION)
return B

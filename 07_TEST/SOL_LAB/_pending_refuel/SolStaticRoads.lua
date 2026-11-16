-- SolStaticRoads.lua - the GPS knows every road of the map, seen or not. Switch: gps_static_roads.
--   The Living Fellows router (SCBridge.planRoadRoute) builds its road graph only from street pieces inside the box
--   around start and goal plus 160 tiles. When the only road between them leaves that box (Sol's home to Muldraugh
--   runs south past y 11200), the clipped graph falls apart and the router answers INCOMPLETE_MAP_DATA or
--   NO_CONNECTED_ROUTE; the panel then drew a straight line. Fog has nothing to do with it: streets.xml is static.
--   This file plans over the whole map's graph (SolStaticRoadsData.lua, generated from the game's streets.xml and
--   Sol_Trails by 05_TOOLS/sol_gps_roads/gen_static_roads.py) whenever the router gives up for that kind of reason.
--   A destination with no road connection gets a route to the nearest reachable road point (route.partial = true).
SolStaticRoads = SolStaticRoads or {}
local M = SolStaticRoads
M.VERSION = "0.1.0"
local OFFROAD, MAX_CONNECTOR, CELL, DIRT_COST, ENDS_NEAR, MAX_POINTS, CACHE_MS = 3, 100, 64, 1.25, 15, 500, 20000
local BIG = 1e30
-- router answers that mean "my clipped graph could not do it", never "the request is wrong" or "a horde blocks it"
M.FALLBACK = { INCOMPLETE_MAP_DATA = true, NO_CONNECTED_ROUTE = true, BUDGET_EXCEEDED = true, NO_ROAD_DATA = true,
    DATA_NOT_READY = true, road_bridge_failed = true, road_bridge_unavailable = true, road_geometry_invalid = true,
    road_fingerprint_invalid = true, road_plan_failed = true }

local function log(m) print("[SolStaticRoads] " .. tostring(m)) end
local function nowMs() return type(getTimestampMs) == "function" and getTimestampMs() or os.time() * 1000 end
function M.on()
    local A = rawget(_G, "SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("gps_static_roads") == true
end

-- ---------------------------------------------------------------- the graph
local G = nil
local function cellKey(cx, cy) return cx * 4096 + cy end
function M.load()
    if G ~= nil then return G or nil end
    local D = rawget(_G, "SolStaticRoadsData")
    if type(D) ~= "table" or type(D.nodes) ~= "table" or type(D.edges) ~= "table" then G = false; log("no road data"); return nil end
    local t0 = nowMs()
    local NX, NY, EA, EB, EW, EN, ED, EL, ADJ, GRID = {}, {}, {}, {}, {}, {}, {}, {}, {}, {}
    local n = 0
    for _, chunk in ipairs(D.nodes) do
        for xs, ys in string.gmatch(chunk, "([^,;]+),([^;]+)") do
            n = n + 1; NX[n] = tonumber(xs); NY[n] = tonumber(ys); ADJ[n] = {}
        end
    end
    local e = 0
    for _, chunk in ipairs(D.edges) do
        for a, b, w, nm, dirt in string.gmatch(chunk, "(%d+),(%d+),([^,]+),(%d+),(%d)") do
            local ia, ib = tonumber(a), tonumber(b)
            if ia and ib and NX[ia] and NX[ib] then
                e = e + 1
                EA[e], EB[e], EW[e], EN[e], ED[e] = ia, ib, tonumber(w) or 0, tonumber(nm) or 0, dirt == "1"
                EL[e] = math.sqrt((NX[ia] - NX[ib]) ^ 2 + (NY[ia] - NY[ib]) ^ 2)
                local la, lb = ADJ[ia], ADJ[ib]
                la[#la + 1] = e; lb[#lb + 1] = e
                local x0, x1 = math.floor(math.min(NX[ia], NX[ib]) / CELL), math.floor(math.max(NX[ia], NX[ib]) / CELL)
                local y0, y1 = math.floor(math.min(NY[ia], NY[ib]) / CELL), math.floor(math.max(NY[ia], NY[ib]) / CELL)
                for cx = x0, x1 do
                    for cy = y0, y1 do
                        local k = cellKey(cx, cy); local list = GRID[k]
                        if list == nil then list = {}; GRID[k] = list end
                        list[#list + 1] = e
                    end
                end
            end
        end
    end
    if n < 2 or e < 1 then G = false; log("road data is empty"); return nil end
    G = { NX = NX, NY = NY, EA = EA, EB = EB, EW = EW, EN = EN, ED = ED, EL = EL, ADJ = ADJ, GRID = GRID,
        names = D.names or {}, nodes = n, edges = e, stamp = {}, stampN = 0 }
    log(string.format("road graph ready: %d points, %d road pieces, %d ms", n, e, nowMs() - t0))
    return G
end

-- ---------------------------------------------------------------- geometry
local function project(px, py, ax, ay, bx, by)
    local dx, dy = bx - ax, by - ay
    local l = dx * dx + dy * dy
    if l <= 0.0001 then return 0, ax, ay end
    local t = ((px - ax) * dx + (py - ay) * dy) / l
    if t < 0 then t = 0 elseif t > 1 then t = 1 end
    return t, ax + dx * t, ay + dy * t
end
local function segDist(px, py, ax, ay, bx, by)
    local _, qx, qy = project(px, py, ax, ay, bx, by)
    return math.sqrt((px - qx) ^ 2 + (py - qy) ^ 2)
end
local function edgeBlocked(g, e, circles)
    if circles == nil then return false end
    local a, b = g.EA[e], g.EB[e]
    for i = 1, #circles do
        local c = circles[i]
        if segDist(c.x, c.y, g.NX[a], g.NY[a], g.NX[b], g.NY[b]) < c.radius then return true end
    end
    return false
end
local function connectorSafe(px, py, qx, qy, circles, source)
    if circles == nil then return true end
    for i = 1, #circles do
        local c = circles[i]
        local inside = math.sqrt((px - c.x) ^ 2 + (py - c.y) ^ 2) <= c.radius
        if source and inside then
            if math.sqrt((qx - c.x) ^ 2 + (qy - c.y) ^ 2) < c.radius then return false end
        elseif segDist(c.x, c.y, px, py, qx, qy) <= c.radius then return false end
    end
    return true
end

-- the road pieces within reach of a point, nearest first (at most 8, like the router)
local function attachments(g, px, py, opts, source)
    local out = {}
    g.stampN = g.stampN + 1
    local mark, reach = g.stampN, opts.reach or MAX_CONNECTOR
    local r = math.ceil(reach / CELL)
    local cx, cy = math.floor(px / CELL), math.floor(py / CELL)
    for x = cx - r, cx + r do
        for y = cy - r, cy + r do
            local list = g.GRID[cellKey(x, y)]
            if list then
                for i = 1, #list do
                    local e = list[i]
                    if g.stamp[e] ~= mark then
                        g.stamp[e] = mark
                        if (opts.dirt or not g.ED[e]) and not edgeBlocked(g, e, opts.circles) then
                            local a, b = g.EA[e], g.EB[e]
                            local t, qx, qy = project(px, py, g.NX[a], g.NY[a], g.NX[b], g.NY[b])
                            local d = math.sqrt((px - qx) ^ 2 + (py - qy) ^ 2)
                            if d <= reach and connectorSafe(px, py, qx, qy, opts.circles, source) then
                                out[#out + 1] = { e = e, t = t, x = qx, y = qy, d = d }
                            end
                        end
                    end
                end
            end
        end
    end
    table.sort(out, function(p, q) return p.d < q.d end)
    while #out > 8 do out[#out] = nil end
    return out
end

-- nearest road point to a world point, any distance up to `reach` (default 3000 tiles)
function M.nearest(x, y, reach)
    local g = M.load(); if not g then return nil end
    x, y = tonumber(x), tonumber(y); if not x or not y then return nil end
    local step = 200
    local limit = tonumber(reach) or 3000
    while step <= limit * 2 do
        local found = attachments(g, x, y, { reach = math.min(step, limit), dirt = true }, false)
        if found[1] then
            local p = found[1]
            return p.x, p.y, p.d, g.names[g.EN[p.e]] or ""
        end
        if step >= limit then break end
        step = step * 2
    end
    return nil
end

-- ---------------------------------------------------------------- search (A*, binary heap)
local function heapPush(h, node, f)
    local n = h.n + 1; h.n = n
    local i = n
    while i > 1 do
        local p = math.floor(i / 2)
        if h.f[p] <= f then break end
        h.node[i], h.f[i] = h.node[p], h.f[p]; i = p
    end
    h.node[i], h.f[i] = node, f
end
local function heapPop(h)
    local n = h.n
    if n == 0 then return nil end
    local top, topF = h.node[1], h.f[1]
    local lastN, lastF = h.node[n], h.f[n]
    h.node[n], h.f[n] = nil, nil; n = n - 1; h.n = n
    if n > 0 then
        local i = 1
        while true do
            local c = i * 2
            if c > n then break end
            if c < n and h.f[c + 1] < h.f[c] then c = c + 1 end
            if h.f[c] >= lastF then break end
            h.node[i], h.f[i] = h.node[c], h.f[c]; i = c
        end
        h.node[i], h.f[i] = lastN, lastF
    end
    return top, topF
end

local function edgeCost(g, e, dirt) return g.EL[e] * ((dirt and g.ED[e]) and DIRT_COST or 1) end

-- one search; returns a path description or a partial one to the reachable point nearest the target
local function search(g, sx, sy, tx, ty, opts)
    local entries = attachments(g, sx, sy, opts, true)
    if #entries == 0 then return nil, "NO_ENTRY_CANDIDATE" end
    local exits = attachments(g, tx, ty, opts, false)
    local cost, prev, prevEdge, entryOf, closed = {}, {}, {}, {}, {}
    local h = { n = 0, node = {}, f = {} }
    local NX, NY = g.NX, g.NY
    local function heur(n) return math.sqrt((NX[n] - tx) ^ 2 + (NY[n] - ty) ^ 2) end
    for i = 1, #entries do
        local c = entries[i]
        local e = c.e
        local ends, part = { g.EA[e], g.EB[e] }, { c.t * edgeCost(g, e, opts.dirt), (1 - c.t) * edgeCost(g, e, opts.dirt) }
        for s = 1, 2 do
            local v = c.d * OFFROAD + part[s]
            local nd = ends[s]
            if v < (cost[nd] or BIG) then cost[nd] = v; entryOf[nd] = i; prev[nd] = nil; prevEdge[nd] = nil; heapPush(h, nd, v + heur(nd)) end
        end
    end
    -- exits keyed by node: the cheapest way off the graph from that node
    local exitAt = {}
    for j = 1, #exits do
        local c = exits[j]; local e = c.e
        local ends, part = { g.EA[e], g.EB[e] }, { c.t * edgeCost(g, e, opts.dirt), (1 - c.t) * edgeCost(g, e, opts.dirt) }
        for s = 1, 2 do
            local v = part[s] + c.d * OFFROAD
            local cur = exitAt[ends[s]]
            if cur == nil or v < cur.v then exitAt[ends[s]] = { v = v, j = j } end
        end
    end
    local best, bestNode, bestExit, bestEntry, direct = BIG, nil, nil, nil, false
    for i = 1, #entries do
        for j = 1, #exits do
            if entries[i].e == exits[j].e then
                local v = (entries[i].d + exits[j].d) * OFFROAD + math.abs(entries[i].t - exits[j].t) * edgeCost(g, exits[j].e, opts.dirt)
                if v < best then best, bestNode, bestExit, bestEntry, direct = v, nil, j, i, true end
            end
        end
    end
    local expanded, nearNode, nearD = 0, nil, BIG
    while true do
        local nd, f = heapPop(h)
        if nd == nil or f >= best then break end
        if not closed[nd] then
            closed[nd] = true
            expanded = expanded + 1
            local gN = cost[nd]
            local dT = heur(nd)
            if dT < nearD then nearD, nearNode = dT, nd end
            local x = exitAt[nd]
            if x and gN + x.v < best then best, bestNode, bestExit, bestEntry, direct = gN + x.v, nd, x.j, entryOf[nd], false end
            local adj = g.ADJ[nd]
            for k = 1, #adj do
                local e = adj[k]
                if (opts.dirt or not g.ED[e]) and not edgeBlocked(g, e, opts.circles) then
                    local to = g.EA[e] == nd and g.EB[e] or g.EA[e]
                    local v = gN + edgeCost(g, e, opts.dirt)
                    if not closed[to] and v + 0.0001 < (cost[to] or BIG) then
                        cost[to], prev[to], prevEdge[to], entryOf[to] = v, nd, e, entryOf[nd]
                        heapPush(h, to, v + heur(to))
                    end
                end
            end
        end
    end
    local result = { entries = entries, exits = exits, expanded = expanded, cost = cost }
    if bestEntry ~= nil then
        result.direct, result.node, result.entry, result.exit = direct, bestNode, entries[bestEntry], exits[bestExit]
        result.prev, result.prevEdge, result.total = prev, prevEdge, best
        return result
    end
    -- no road reaches the destination: the reachable road point nearest to it
    if nearNode == nil then return nil, "NO_CONNECTED_ROUTE" end
    result.partial, result.node, result.entry, result.prev, result.prevEdge = true, nearNode, entries[entryOf[nearNode]], prev, prevEdge
    result.total = cost[nearNode]
    return result
end

-- ---------------------------------------------------------------- route table (the shape SCExpeditionRoute.plan returns)
local function step(g, x, y, e, junction)
    return { x = x, y = y, street = (e and g.names[g.EN[e]]) or "", width = e and g.EW[e] or 0, junction = junction == true }
end
local function thin(points)
    -- drop points that lie on the straight line between their neighbours (never junctions, never the ends)
    local out = { points[1] }
    for i = 2, #points - 1 do
        local a, p, b = out[#out], points[i], points[i + 1]
        local keep = p.junction or segDist(p.x, p.y, a.x, a.y, b.x, b.y) > 0.75 or (p.width or 0) ~= (b.width or 0)
        if keep then out[#out + 1] = p end
    end
    out[#out + 1] = points[#points]
    return out
end
-- long wide streets in lane runs of ~36 tiles, as SCExpeditionRoute.parseGeometry does for the router's geometry
local function lanes(points)
    local out = { points[1] }
    for i = 2, #points do
        local first, last = points[i - 1], points[i]
        local dx, dy = last.x - first.x, last.y - first.y
        local length = math.sqrt(dx * dx + dy * dy)
        if (last.width or 0) >= 6 and length > 48 then
            local runs = math.ceil(length / 36)
            if #out + runs + (#points - i) <= MAX_POINTS then
                for part = 1, runs - 1 do
                    local t = part / runs
                    out[#out + 1] = { x = first.x + dx * t, y = first.y + dy * t, street = last.street, width = last.width, junction = false }
                end
            end
        end
        out[#out + 1] = last
    end
    return out
end

local function buildRoute(g, r, target, circles)
    local pts = {}
    local entry = r.entry
    pts[1] = step(g, entry.x, entry.y, entry.e, false)
    local roadLen = 0
    if not r.direct then
        local rev, cursor = {}, r.node
        while cursor ~= nil do rev[#rev + 1] = cursor; cursor = r.prev[cursor]; if #rev > 20000 then return nil end end
        for i = #rev, 1, -1 do
            local nd = rev[i]
            local e = r.prevEdge[nd] or entry.e
            pts[#pts + 1] = step(g, g.NX[nd], g.NY[nd], e, #g.ADJ[nd] >= 3)
        end
    end
    if not r.partial then
        local x = r.exit
        pts[#pts + 1] = step(g, x.x, x.y, x.e, false)
    end
    -- the bridge refuses points closer than half a tile
    local spaced = { pts[1] }
    for i = 2, #pts do
        local a, p = spaced[#spaced], pts[i]
        if (a.x - p.x) ^ 2 + (a.y - p.y) ^ 2 >= 0.25 then spaced[#spaced + 1] = p elseif i == #pts and #spaced > 1 then spaced[#spaced] = p end
    end
    if #spaced < 2 then
        local p = spaced[1]
        spaced[2] = { x = p.x + 1, y = p.y, street = p.street, width = p.width, junction = false }
    end
    if #spaced > MAX_POINTS then spaced = thin(spaced) end
    if #spaced > MAX_POINTS then return nil, "BUDGET_EXCEEDED" end
    local points = lanes(spaced)
    for i = 2, #points do roadLen = roadLen + math.sqrt((points[i].x - points[i - 1].x) ^ 2 + (points[i].y - points[i - 1].y) ^ 2) end
    local last = points[#points]
    local hash = 0
    for i = 1, #points do hash = (hash * 31 + math.floor(points[i].x * 7 + points[i].y * 13)) % 1000000007 end
    return {
        points = points, index = 1, fingerprint = "static" .. tostring(hash), roadLength = roadLen,
        inferredJunctions = 0, elapsedMs = 0, goal = { x = target.x, y = target.y, z = target.z or 0 },
        avoidances = circles, avoidance = circles and circles[1] and { x = circles[1].x, y = circles[1].y, radius = circles[1].radius } or nil,
        static = true, partial = r.partial == true,
        gapToGoal = math.sqrt((last.x - target.x) ^ 2 + (last.y - target.y) ^ 2),
    }
end

local cache = {}
-- plan from a point over the whole map. circles: optional avoid list {x, y, radius}.
-- returns route (route.partial when no road reaches the destination) or nil, reason
function M.plan(sx, sy, target, circles)
    local g = M.load(); if not g then return nil, "DATA_NOT_READY" end
    sx, sy = tonumber(sx), tonumber(sy)
    if not sx or not sy or type(target) ~= "table" or tonumber(target.x) == nil or tonumber(target.y) == nil then return nil, "invalid_road_target" end
    local tx, ty = tonumber(target.x), tonumber(target.y)
    local key = math.floor(sx / 8) .. ":" .. math.floor(sy / 8) .. ">" .. math.floor(tx) .. ":" .. math.floor(ty)
    if circles then for i = 1, #circles do key = key .. "|" .. math.floor(circles[i].x) .. ":" .. math.floor(circles[i].y) .. ":" .. math.floor(circles[i].radius) end end
    local hit, now = cache[key], nowMs()
    if hit and now - hit.at < CACHE_MS then return hit.route, hit.why end
    local t0 = now
    local tgt = { x = tx, y = ty, z = 0 }
    -- paved first (road_first); dirt roads when the paved roads do not reach the place
    local r, why = search(g, sx, sy, tx, ty, { circles = circles, dirt = false })
    local route
    if r then route, why = buildRoute(g, r, tgt, circles) end
    local function reaches(rt) return rt ~= nil and not rt.partial and rt.gapToGoal <= ENDS_NEAR end
    if not reaches(route) then
        local r2, why2 = search(g, sx, sy, tx, ty, { circles = circles, dirt = true })
        local route2
        if r2 then route2, why2 = buildRoute(g, r2, tgt, circles) end
        if route2 and (route == nil or (route.partial and not route2.partial) or (route2.gapToGoal + 0.5 < route.gapToGoal)) then route, why = route2, nil
        elseif route == nil then why = why2 or why end
    end
    if route then route.elapsedMs = nowMs() - t0; why = nil end
    log(string.format("plan %d,%d -> %d,%d: %s%s, %d ms", math.floor(sx), math.floor(sy), math.floor(tx), math.floor(ty),
        route and (#route.points .. " points") or tostring(why), route and route.partial and " (no road reaches it: nearest road point)" or "", nowMs() - t0))
    cache[key] = { at = nowMs(), route = route, why = why }
    return route, why
end

-- ---------------------------------------------------------------- wiring into the router (same answers when the switch is off)
local function position(actor)
    local SC = rawget(_G, "SurvivorCompanion")
    if SC and SC.GameplayUtil and type(SC.GameplayUtil.position) == "function" then
        local ok, x, y, z = pcall(SC.GameplayUtil.position, actor)
        if ok then return tonumber(x), tonumber(y), tonumber(z) end
    end
    return nil
end
local function fallback(route, why, detail, sx, sy, target, circles)
    if route ~= nil or not M.on() or not M.FALLBACK[tostring(why)] or type(target) ~= "table" or target.z ~= 0 or sx == nil or sy == nil then
        return route, why, detail
    end
    local okS, r2, why2 = pcall(M.plan, sx, sy, target, circles)
    if okS and r2 then
        log("router said " .. tostring(why) .. ": whole-map roads used")
        return r2, nil, detail
    end
    log("router said " .. tostring(why) .. "; whole-map roads: " .. tostring(okS and why2 or r2))
    return route, why, detail
end
function M.wrap()
    local SC = rawget(_G, "SurvivorCompanion")
    local R = type(SC) == "table" and SC.ExpeditionRoute or nil
    if type(R) ~= "table" then return false end
    if type(R.planFromPoint) == "function" and R.planFromPoint ~= M.wPlanFromPoint then
        local orig = R.planFromPoint
        M.wPlanFromPoint = function(origin, target, continuing)
            local route, why, detail = orig(origin, target, continuing)
            local sx, sy = type(origin) == "table" and tonumber(origin.x) or nil, type(origin) == "table" and tonumber(origin.y) or nil
            return fallback(route, why, detail, sx, sy, target, nil)
        end
        R.planFromPoint = M.wPlanFromPoint
    end
    if type(R.plan) == "function" and R.plan ~= M.wPlan then
        local orig = R.plan
        M.wPlan = function(actor, target, continuing, avoidance)
            local route, why, detail = orig(actor, target, continuing, avoidance)
            if route ~= nil or not M.on() then return route, why, detail end
            local sx, sy, sz = position(actor)
            if sz ~= nil and sz ~= 0 then return route, why, detail end
            return fallback(route, why, detail, sx, sy, target, avoidance and { avoidance } or nil)
        end
        R.plan = M.wPlan
    end
    if type(R.planAvoidingAll) == "function" and R.planAvoidingAll ~= M.wPlanAvoidingAll then
        local orig = R.planAvoidingAll
        M.wPlanAvoidingAll = function(actor, target, circles)
            local route, why, detail = orig(actor, target, circles)
            if route ~= nil or not M.on() then return route, why, detail end
            local sx, sy, sz = position(actor)
            if sz ~= nil and sz ~= 0 then return route, why, detail end
            local list = (type(circles) == "table" and #circles > 0) and circles or nil
            return fallback(route, why, detail, sx, sy, target, list)
        end
        R.planAvoidingAll = M.wPlanAvoidingAll
    end
    -- the GPS's "nearest road" (Living Fellows' street lookup) falls back to the whole map too
    local U = rawget(_G, "SolUI")
    if type(U) == "table" and type(U.gpsNearestRoad) == "function" and U.gpsNearestRoad ~= M.wNearest then
        local orig = U.gpsNearestRoad
        M.wNearest = function(x, y)
            local sx, sy, d, name = orig(x, y)
            if sx ~= nil or not M.on() then return sx, sy, d, name end
            local nx, ny, nd, nn = M.nearest(x, y)
            if nx == nil then return nil end
            return math.floor(nx), math.floor(ny), nd, nn
        end
        U.gpsNearestRoad = M.wNearest
    end
    return true
end

pcall(M.wrap)
if Events then
    if Events.OnGameBoot then Events.OnGameBoot.Add(function() pcall(M.wrap) end) end
    if Events.OnGameStart then Events.OnGameStart.Add(function() pcall(M.wrap) end) end
end
return M

-- SolPlace.lua - switch spatial_access. Sol knows the place she is in: which side of a wall, fence, door or window each square is on,
-- and she goes through doors first, a window only when no door will do, and over a fence only as the last resort.
-- Design and evidence: DOCS/PLAN_spatial_awareness.md.
--   edges     every square border is one of: open, door, window, frame, fence, wall (a tall fence counts as wall). Live reads use the
--             same IsoGridSquare calls Living Fellows uses (isDoorTo, isWindowTo, isHoppableTo, isBlockedTo, getDoor, getWindow).
--             The kind is cached per 8x8 chunk for STRUCT_TTL_MS; the state of a door or window (open, locked, barricaded) is read
--             live every time, so a door she or he just opened counts at once. Objects added or removed drop their chunk.
--   cost      a step costs 1 (diagonal 1.414, only when both corners are open); crossing adds: open door 0.3, closed door 2,
--             window 25 (open, or no glass) / 40 (shut), window frame 25, low fence 60. Locked doors she cannot open, barricades,
--             walls and tall fences are not crossed. So a door wins unless it is ~25 tiles further than a window and ~60 than a fence.
--   route     a bounded, time-sliced A* (SolBudget slices, a clock check every 16 nodes, MAX_NODES) from her square to the goal
--             squares. A route that crosses a door, window or fence is walked in legs: to the square before each crossing, to the
--             square after it, and every LEG_TILES on long open stretches, so each leg the engine walks is short and on one side.
--   walking   U.solGoto is wrapped: every walk of hers (sort, farm, animal care, GPS door walk, far car, address book) goes this way
--             when the switch is on. Near zombies, in a car, on another floor or when nothing better is found it is the old walk.
--   LF cost   Living Fellows' own A* prices a low fence at 2.5 and an open window at 2.5 (SCTopology.lua 965-1011), below a short
--             detour to a gate. For Sol only, and only while no zombie is near, those edges cost FENCE_EXTRA / WINDOW_EXTRA more.
--   others    SolPlace.goNear(x, y, z, near, onDone): the far-away walk-in (SolFar) walks door-first to him, then LF's regroup.
--             SolPlace.nextLeg(x, y): the next square on the door-first way, for walks a caller orders itself (the passenger door
--             walk through LF Navigation.request in SolOrders startWalk); the driver's door walk (SolGPS) is a U.solGoto already.
--   access    the squares from which a container (or a plant, an animal) is used: the four sides first, a corner only when no side
--             works, standable, and nothing between it and the thing (wall, closed door, window, fence). M.reach says whether
--             she can use it from where she stands.
-- Verb: sol_place status | dump [radius] | route x,y | access x,y
SolUI = SolUI or {}
local U = SolUI
SolPlace = SolPlace or {}
local M = SolPlace
M.VERSION = "0.2.0"
M.COST = { door_open = 0.3, door_closed = 2, window_open = 25, window_closed = 40, frame = 25, fence = 60 }
M.DIAG = 1.4142
M.MARGIN = 24                 -- the search box: start and goals, plus this many tiles
M.MAX_NODES = 9000            -- a route search never expands more than this
M.LEG_TILES = 10              -- the longest leg on open ground
M.STRUCT_TTL_MS = 20000
M.PLAN_WAIT_MS = 2500         -- a search not done by then: the old walk
M.LEG_STALL_MS = 9000         -- no new square for this long on one leg: the old walk to the goal
M.ROUTE_MS = 180000
M.OFF_PATH = 4                -- further than this from the route: someone else is steering her; let go
M.DANGER_TILES = 7
M.FENCE_EXTRA, M.WINDOW_EXTRA = 40, 18
M.TICK_MS = 100

local rawTonumber = tonumber
local function tonumber(v) return rawTonumber(v) end
local function g(name) return rawget(_G, name) end
local function nowMs() local f = g("getTimestampMs"); return f and f() or 0 end
local function log(m) print("[SolPlace] " .. tostring(m)) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, r = pcall(f, o, ...)
    if ok then return r end
    return nil
end
local function floor(v) return math.floor(tonumber(v) or 0) end
function M.on()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("spatial_access") == true
end

-- ---------------------------------------------------------------- the world (live; tests put their own here with M.setWorld)
-- world.edge(x, y, z, dir): dir "N" is the border between (x,y) and (x,y-1), "W" between (x,y) and (x-1,y).
--   returns kind ("open" | "door" | "window" | "frame" | "fence" | "wall") and, for doors and windows, a state table
--   { open, locked, barricaded, smashed, noGlass, canUnlock }.
-- world.standable(x, y, z) -> true when a person can stand there.
local Live = {}
local function cell() local f = g("getCell"); return f and f() or nil end
function Live.square(x, y, z) local c = cell(); return c and call(c, "getGridSquare", x, y, z) or nil end
function Live.standable(x, y, z)
    local s = Live.square(x, y, z)
    if s == nil then return false end
    if call(s, "getFloor") == nil and call(s, "TreatAsSolidFloor") ~= true then return false end
    if call(s, "isSolid") == true or call(s, "isSolidTrans") == true then return false end
    return call(s, "isFree", false) ~= false
end
local function doorState(o, from)
    if o == nil then return nil end
    local st = { open = call(o, "IsOpen") == true, barricaded = call(o, "isBarricaded") == true }
    st.locked = not st.open and (call(o, "isLocked") == true or call(o, "isLockedByKey") == true)
    if st.locked then
        local T = type(g("SurvivorCompanion")) == "table" and g("SurvivorCompanion").Topology or nil
        local a = type(U.solActor) == "function" and U.solActor() or nil
        if T and type(T.actorCanUnlock) == "function" and a ~= nil then
            local ok, can = pcall(T.actorCanUnlock, a, o, from); st.canUnlock = ok and can == true
        end
    end
    return st
end
local function windowState(o)
    if o == nil then return nil end
    return { open = call(o, "IsOpen") == true, barricaded = call(o, "isBarricaded") == true, smashed = call(o, "isSmashed") == true,
        noGlass = call(o, "isGlassRemoved") == true }
end
-- structure cache: chunk key -> { at, e = { ["x,y,dir"] = { kind, obj } } }
local chunks = {}
M._chunks = chunks
local function chunkKey(x, y, z) return math.floor(x / 8) .. "," .. math.floor(y / 8) .. "," .. z end
function M.invalidate(x, y, z) chunks[chunkKey(x, y, z or 0)] = nil end
local function liveStruct(x, y, z, dir)
    local owner = Live.square(x, y, z)
    local other = dir == "N" and Live.square(x, y - 1, z) or Live.square(x - 1, y, z)
    if owner == nil or other == nil then return "wall", nil end
    local north = dir == "N"
    if call(other, "isDoorTo", owner) == true or call(owner, "isDoorTo", other) == true then
        return "door", call(owner, "getDoor", north) or call(other, "getDoor", north)
    end
    if call(other, "isWindowTo", owner) == true or call(owner, "isWindowTo", other) == true then
        local w = call(owner, "getWindow", north) or call(owner, "getThumpableWindow", north)
        if w ~= nil then return "window", w end
        local fr = call(owner, "getWindowFrame", north)
        if fr ~= nil then return "frame", fr end
        return "wall", nil
    end
    if call(other, "isHoppableTo", owner) == true or call(owner, "isHoppableTo", other) == true then return "fence", nil end
    if call(other, "isBlockedTo", owner) == true or call(owner, "isBlockedTo", other) == true then return "wall", nil end
    return "open", nil
end
function Live.edge(x, y, z, dir)
    local ck, t = chunkKey(x, y, z), nowMs()
    local c = chunks[ck]
    if c == nil or t - c.at > M.STRUCT_TTL_MS then c = { at = t, e = {} }; chunks[ck] = c end
    local key = x .. "," .. y .. "," .. dir
    local e = c.e[key]
    if e == nil then
        local kind, obj = liveStruct(x, y, z, dir)
        e = { kind = kind, obj = obj }
        c.e[key] = e
    end
    if e.kind == "door" then
        local from = dir == "N" and Live.square(x, y - 1, z) or Live.square(x - 1, y, z)
        return "door", doorState(e.obj, from) or { open = false }
    end
    if e.kind == "window" then return "window", windowState(e.obj) or { open = false } end
    return e.kind, nil
end
M.live = Live
local world = Live
function M.setWorld(w) world = w or Live end
function M.world() return world end

-- ---------------------------------------------------------------- one border: its kind and what crossing it costs (nil: not crossable)
local function edgeBetween(ax, ay, bx, by, z)
    if bx == ax and by == ay - 1 then return world.edge(ax, ay, z, "N") end
    if bx == ax and by == ay + 1 then return world.edge(bx, by, z, "N") end
    if by == ay and bx == ax - 1 then return world.edge(ax, ay, z, "W") end
    if by == ay and bx == ax + 1 then return world.edge(bx, by, z, "W") end
    return "wall", nil
end
M.edgeBetween = edgeBetween
function M.crossCost(kind, st)
    local C = M.COST
    if kind == "open" then return 0 end
    if kind == "door" then
        st = st or {}
        if st.barricaded then return nil end
        if st.open then return C.door_open end
        if st.locked and not st.canUnlock then return nil end
        return C.door_closed
    end
    if kind == "window" then
        st = st or {}
        if st.barricaded then return nil end
        if st.open or st.noGlass then return C.window_open end
        return C.window_closed
    end
    if kind == "frame" then return C.frame end
    if kind == "fence" then return C.fence end
    return nil
end
-- nothing at all between two neighbours (an open door counts as nothing: vanilla canReachTo only stops at a blocked door)
local function clear(ax, ay, bx, by, z)
    local kind, st = edgeBetween(ax, ay, bx, by, z)
    return kind == "open" or (kind == "door" and st ~= nil and st.open == true)
end
M.clear = clear

-- ---------------------------------------------------------------- where she can use a thing from
local SIDES = { { -1, 0 }, { 1, 0 }, { 0, -1 }, { 0, 1 } }
local CORNERS = { { -1, -1 }, { 1, -1 }, { -1, 1 }, { 1, 1 } }
-- a corner square uses the thing only when both ways round the corner are open (vanilla AdjacentFreeTileFinder.privTrySquareForWalls)
local function cornerClear(sx, sy, tx, ty, z)
    return clear(sx, sy, tx, sy, z) and clear(tx, sy, tx, ty, z) and clear(sx, sy, sx, ty, z) and clear(sx, ty, tx, ty, z)
end
function M.reach(px, py, z, tx, ty)
    local dx, dy = math.abs(px - tx), math.abs(py - ty)
    if dx + dy == 0 or dx > 1 or dy > 1 then return false end
    if dx + dy == 1 then return clear(px, py, tx, ty, z) end
    return cornerClear(px, py, tx, ty, z)
end
function M.access(tx, ty, z)
    local out = {}
    for pass = 1, 2 do
        for _, d in ipairs(pass == 1 and SIDES or CORNERS) do
            local sx, sy = tx + d[1], ty + d[2]
            if world.standable(sx, sy, z) and M.reach(sx, sy, z, tx, ty) then out[#out + 1] = { x = sx, y = sy, z = z } end
        end
        if #out > 0 then break end
    end
    return out
end
-- the same as IsoGridSquares, for code that hands squares to Living Fellows
function M.standSquares(target)
    local x, y, z = floor(call(target, "getX")), floor(call(target, "getY")), floor(call(target, "getZ"))
    local out = {}
    for _, s in ipairs(M.access(x, y, z)) do
        local sq = Live.square(s.x, s.y, s.z)
        if sq ~= nil then out[#out + 1] = sq end
    end
    return out
end

-- ---------------------------------------------------------------- the route search (A*, bounded, resumable)
local function heapPush(h, n)
    h[#h + 1] = n
    local i = #h
    while i > 1 do
        local p = math.floor(i / 2)
        if h[p].f <= h[i].f then break end
        h[p], h[i] = h[i], h[p]; i = p
    end
end
local function heapPop(h)
    local n = #h
    if n == 0 then return nil end
    local top = h[1]
    h[1] = h[n]; h[n] = nil; n = n - 1
    local i = 1
    while true do
        local l, r, s = i * 2, i * 2 + 1, i
        if l <= n and h[l].f < h[s].f then s = l end
        if r <= n and h[r].f < h[s].f then s = r end
        if s == i then break end
        h[s], h[i] = h[i], h[s]; i = s
    end
    return top
end
local function key(x, y) return x .. "," .. y end

-- goals: list of {x,y}; options: { strict = true } refuses windows and fences, { maxNodes = n }
function M.newSearch(sx, sy, z, goals, options)
    options = options or {}
    local j = { sx = sx, sy = sy, z = z, goals = {}, glist = {}, open = {}, best = {}, from = {}, via = {}, closed = {}, nodes = 0,
        strict = options.strict == true, maxNodes = options.maxNodes or M.MAX_NODES, state = "running" }
    local x0, y0, x1, y1 = sx, sy, sx, sy
    for _, gq in ipairs(goals) do
        j.goals[key(gq.x, gq.y)] = true
        j.glist[#j.glist + 1] = gq
        x0, y0, x1, y1 = math.min(x0, gq.x), math.min(y0, gq.y), math.max(x1, gq.x), math.max(y1, gq.y)
    end
    j.box = { x0 - M.MARGIN, y0 - M.MARGIN, x1 + M.MARGIN, y1 + M.MARGIN }
    local k = key(sx, sy)
    j.best[k] = 0
    heapPush(j.open, { x = sx, y = sy, g = 0, f = M._h(j, sx, sy) })
    return j
end
function M._h(j, x, y)
    local best
    for _, gq in ipairs(j.glist) do
        local dx, dy = math.abs(x - gq.x), math.abs(y - gq.y)
        local d = math.max(dx, dy) + (M.DIAG - 1) * math.min(dx, dy)
        if best == nil or d < best then best = d end
    end
    return best or 0
end
local DIRS = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 }, { 1, 1 }, { -1, 1 }, { 1, -1 }, { -1, -1 } }
local function stepCost(j, x, y, nx, ny)
    local z = j.z
    if nx < j.box[1] or ny < j.box[2] or nx > j.box[3] or ny > j.box[4] then return nil end
    if not world.standable(nx, ny, z) and not j.goals[key(nx, ny)] then return nil end
    if nx ~= x and ny ~= y then
        -- a diagonal stride only through a fully open corner
        if not (world.standable(nx, y, z) and world.standable(x, ny, z)) then return nil end
        if not cornerClear(x, y, nx, ny, z) then return nil end
        return M.DIAG, "open"
    end
    local kind, st = edgeBetween(x, y, nx, ny, z)
    local extra = M.crossCost(kind, st)
    if extra == nil then return nil end
    if j.strict and (kind == "window" or kind == "frame" or kind == "fence") then return nil end
    return 1 + extra, kind
end
-- quota: nodes; deadline: ms clock; returns "running" | "done" | "failed"
function M.resume(j, quota, deadline)
    if j.state ~= "running" then return j.state end
    local n = 0
    while true do
        local cur = heapPop(j.open)
        if cur == nil then j.state = "failed"; j.why = "no_route"; return j.state end
        local ck = key(cur.x, cur.y)
        if not j.closed[ck] and cur.g <= (j.best[ck] or math.huge) then
            j.closed[ck] = true
            if j.goals[ck] then
                j.state, j.goal = "done", { x = cur.x, y = cur.y }
                M._finish(j)
                return j.state
            end
            j.nodes = j.nodes + 1
            if j.nodes > j.maxNodes then j.state = "failed"; j.why = "too_far"; return j.state end
            for _, d in ipairs(DIRS) do
                local nx, ny = cur.x + d[1], cur.y + d[2]
                local nk = key(nx, ny)
                if not j.closed[nk] then
                    local c, kind = stepCost(j, cur.x, cur.y, nx, ny)
                    if c ~= nil then
                        local ng = cur.g + c
                        if ng < (j.best[nk] or math.huge) then
                            j.best[nk], j.from[nk], j.via[nk] = ng, ck, kind
                            heapPush(j.open, { x = nx, y = ny, g = ng, f = ng + M._h(j, nx, ny) })
                        end
                    end
                end
            end
            n = n + 1
            if n >= quota then return "running" end
            if deadline ~= nil and n % 16 == 0 and nowMs() >= deadline then return "running" end
        end
    end
end
function M._finish(j)
    local path, k = {}, key(j.goal.x, j.goal.y)
    while k ~= nil do
        local x, y = string.match(k, "^(%-?%d+),(%-?%d+)$")
        table.insert(path, 1, { x = tonumber(x), y = tonumber(y), via = j.via[k] })
        k = j.from[k]
    end
    j.path, j.cost = path, j.best[key(j.goal.x, j.goal.y)]
    local crossings, counts = {}, { door = 0, window = 0, frame = 0, fence = 0 }
    for i = 2, #path do
        local v = path[i].via
        if v ~= nil and v ~= "open" then
            crossings[#crossings + 1] = { i = i, kind = v, from = path[i - 1], to = path[i] }
            counts[v] = (counts[v] or 0) + 1
        end
    end
    j.crossings, j.counts = crossings, counts
    -- legs: before and after each crossing, every LEG_TILES on open ground, and the goal
    local legs, last = {}, 1
    local function add(i) if i > 1 and (legs[#legs] == nil or legs[#legs].i ~= i) then legs[#legs + 1] = { i = i, x = path[i].x, y = path[i].y } end end
    for i = 2, #path do
        local v = path[i].via
        if v ~= nil and v ~= "open" then add(i - 1); add(i); last = i
        elseif i - last >= M.LEG_TILES then add(i); last = i end
    end
    add(#path)
    j.legs = legs
end
-- the whole search at once (tests, debug verbs)
function M.route(sx, sy, z, goals, options)
    local j = M.newSearch(sx, sy, z, goals, options)
    while M.resume(j, 100000) == "running" do end
    return j
end

-- ---------------------------------------------------------------- danger (zombies near her: the old ways, fences are an escape then)
local dangerAt, dangerVal = -1e9, false
function M.danger(a)
    local t = nowMs()
    if t - dangerAt < 1000 then return dangerVal end
    dangerAt, dangerVal = t, false
    local c = cell()
    local list = c and call(c, "getZombieList")
    local n = tonumber(list and call(list, "size")) or 0
    local ax, ay = tonumber(call(a, "getX")), tonumber(call(a, "getY"))
    if ax == nil then return false end
    local r2 = M.DANGER_TILES * M.DANGER_TILES
    for i = 0, math.min(n, 400) - 1 do
        local zb = call(list, "get", i)
        local zx, zy = tonumber(call(zb, "getX")), tonumber(call(zb, "getY"))
        if zx ~= nil and (zx - ax) * (zx - ax) + (zy - ay) * (zy - ay) <= r2 and call(zb, "isDead") ~= true then dangerVal = true; break end
    end
    return dangerVal
end

-- ---------------------------------------------------------------- her walks: U.solGoto through the route, leg by leg
M.R = nil          -- the current route walk
M.stats = { routes = 0, legs = 0, direct = 0, fallbacks = 0, crossings = {}, nodes = 0, maxSliceMs = 0 }
local function solActor() return type(U.solActor) == "function" and U.solActor() or nil end
local function posOf(a)
    local x, y, z = tonumber(call(a, "getX")), tonumber(call(a, "getY")), tonumber(call(a, "getZ"))
    if x == nil then return nil end
    return math.floor(x), math.floor(y), math.floor(z or 0), x, y
end
local function sendLeg(R, i)
    local L = R.legs[i]
    R.li, R.sentAt, R.movedAt = i, nowMs(), nowMs()
    M.stats.legs = M.stats.legs + 1
    return M._orig(L.x, L.y, R.z)
end
-- the walk is over (arrived, given up, taken over): the caller's next step, once
local function finish(R)
    if M.R == R then M.R = nil end
    local f = R.onDone
    R.onDone = nil
    if type(f) == "function" then pcall(f) end
end
local function startLegs(R)
    local j = R.job
    M.stats.routes = M.stats.routes + 1
    M.stats.nodes = M.stats.nodes + j.nodes
    for k, v in pairs(j.counts or {}) do M.stats.crossings[k] = (M.stats.crossings[k] or 0) + v end
    if #j.crossings == 0 and #j.path <= M.LEG_TILES * 2 then
        M.stats.direct = M.stats.direct + 1
        if R.onDone ~= nil then finish(R); return true, "direct" end              -- nothing in the way: the caller's own walk does it
        M.R = nil
        return M._orig(R.gx, R.gy, R.z)
    end
    R.legs, R.path = j.legs, j.path
    log(string.format("route %d,%d -> %d,%d: %d steps, doors %d windows %d fences %d, %d legs, %d nodes", R.sx, R.sy, R.gx, R.gy, #j.path,
        j.counts.door or 0, (j.counts.window or 0) + (j.counts.frame or 0), j.counts.fence or 0, #j.legs, j.nodes))
    return sendLeg(R, 1)
end
local function fallback(R, why)
    M.stats.fallbacks = M.stats.fallbacks + 1
    log("old walk to " .. R.gx .. "," .. R.gy .. ": " .. tostring(why))
    if R.onDone ~= nil then finish(R); return true, "handed_back" end
    M.R = nil
    return M._orig(R.gx, R.gy, R.z)
end
local function begin(x, y, z, near, onDone)
    local px, py = posOf(solActor())
    local R = { gx = x, gy = y, z = z, sx = px, sy = py, at = nowMs(), near = near, onDone = onDone }
    R.job = M.newSearch(px, py, z, { { x = x, y = y } })
    if M.R ~= nil then finish(M.R) end
    M.R = R
    local st = M.resume(R.job, 600, nowMs() + 2)
    if st == "done" then return startLegs(R) end
    if st == "failed" then return fallback(R, R.job.why) end
    return true, "walking_to " .. x .. "," .. y                                      -- still searching: the budget tick goes on
end
function M.go(x, y, z)
    local a = solActor()
    if a == nil or not M.on() then return M._orig(x, y, z) end
    local px, py, pz = posOf(a)
    z = z ~= nil and math.floor(z) or pz
    x, y = math.floor(x), math.floor(y)
    if px == nil or z ~= pz or call(a, "getVehicle") ~= nil or M.danger(a) then return M._orig(x, y, z) end
    if math.max(math.abs(px - x), math.abs(py - y)) <= 1 then
        if M.R ~= nil then finish(M.R) end
        return M._orig(x, y, z)
    end
    local R = M.R
    if R ~= nil and R.gx == x and R.gy == y and R.z == z then                         -- the same walk asked again: it goes on
        return true, "walking_to " .. x .. "," .. y
    end
    return begin(x, y, z, nil, nil)
end
-- walk her to within `near` tiles of x,y the door-first way, then onDone() (also when nothing is in the way, or it gives up).
-- For walks that are not U.solGoto: the far-away walk-in ends with LF's regroup. Returns true when onDone will be called.
function M.goNear(x, y, z, near, onDone)
    local a = solActor()
    if a == nil or not M.on() then return false end
    local px, py, pz = posOf(a)
    if px == nil or call(a, "getVehicle") ~= nil or M.danger(a) then return false end
    z = z ~= nil and math.floor(z) or pz
    if z ~= pz then return false end
    x, y = math.floor(x), math.floor(y)
    near = tonumber(near) or 2
    if math.max(math.abs(px - x), math.abs(py - y)) <= near then
        if type(onDone) == "function" then pcall(onDone) end
        return true
    end
    begin(x, y, z, near, onDone)
    return true
end
-- the square to walk to next on the door-first way to x,y, or nil when the plain walk is right (nothing left in between, or the
-- route is not known yet). For walks a caller orders itself (the passenger door walk through LF Navigation.request in SolOrders).
M._next = nil
function M.nextLeg(x, y, z, again)
    local a = solActor()
    if a == nil or not M.on() then return nil end
    local px, py, pz = posOf(a)
    if px == nil or M.danger(a) then return nil end
    z = z ~= nil and math.floor(z) or pz
    if z ~= pz then return nil end
    x, y = math.floor(x), math.floor(y)
    local N = M._next
    if N == nil or N.gx ~= x or N.gy ~= y or N.z ~= z or N.job.state == "failed" then
        N = { gx = x, gy = y, z = z, job = M.newSearch(px, py, z, { { x = x, y = y } }) }
        M._next = N
    end
    local j = N.job
    if j.state == "running" then M.resume(j, 1500, nowMs() + 4) end
    if j.state ~= "done" then return nil end
    local idx
    for i = #j.path, 1, -1 do if j.path[i].x == px and j.path[i].y == py then idx = i; break end end
    if idx == nil then                                                                 -- off this route: one new one from here
        M._next = nil
        if again then return nil end
        return M.nextLeg(x, y, z, true)
    end
    local lastCross = 0
    for _, c in ipairs(j.crossings) do if c.i > lastCross then lastCross = c.i end end
    if idx >= lastCross then return nil end                                            -- nothing left in between: the plain walk
    for _, L in ipairs(j.legs) do if L.i > idx then return L.x, L.y end end
    return nil
end
function M.tick(remainingMs)
    local R = M.R
    if R == nil then return end
    local a = solActor()
    if a == nil or not M.on() then finish(R); return end
    local t = nowMs()
    if R.legs == nil then
        local t0 = t
        local st = M.resume(R.job, 2000, t0 + math.max(1, math.min(tonumber(remainingMs) or 2, 4)))
        local spent = nowMs() - t0
        if spent > M.stats.maxSliceMs then M.stats.maxSliceMs = spent end
        if st == "done" then pcall(startLegs, R); return end
        if st == "failed" then pcall(fallback, R, R.job.why); return end
        if t - R.at > M.PLAN_WAIT_MS then pcall(fallback, R, "search_slow"); return end
        return
    end
    if call(a, "getVehicle") ~= nil then finish(R); return end
    if M.danger(a) then pcall(fallback, R, "danger"); return end
    if t - R.at > M.ROUTE_MS then finish(R); return end
    local px, py, pz = posOf(a)
    if px == nil or pz ~= R.z then finish(R); return end
    if R.near ~= nil and math.max(math.abs(px - R.gx), math.abs(py - R.gy)) <= R.near then finish(R); return end
    -- where on the route is she? the furthest path square she stands on
    local L = R.legs[R.li]
    local here = px .. "," .. py
    if here ~= R.here then R.here, R.movedAt = here, t end
    local onPath, idx = false, nil
    for i = #R.path, 1, -1 do
        local p = R.path[i]
        local d = math.max(math.abs(p.x - px), math.abs(p.y - py))
        if d == 0 then idx = i; onPath = true; break end
        if d <= M.OFF_PATH then onPath = true end
    end
    if not onPath then log("she left the route (someone else is walking her)"); finish(R); return end
    if idx ~= nil and idx >= L.i then
        if R.li >= #R.legs then finish(R); return end                                -- the goal: done
        local nextLeg = R.li + 1
        while nextLeg < #R.legs and R.legs[nextLeg].i <= idx do nextLeg = nextLeg + 1 end
        pcall(sendLeg, R, nextLeg)
        return
    end
    if t - R.movedAt > M.LEG_STALL_MS then pcall(fallback, R, "leg_stalled"); return end
end

-- ---------------------------------------------------------------- Living Fellows' own A*: fences and windows cost more, for her
local memo, memoN = {}, 0
local actorAt, actorVal = -1e9, nil
local function solCached()
    local t = nowMs()
    if t - actorAt > 1000 then actorAt, actorVal = t, solActor() end
    return actorVal
end
function M.wrapTopology()
    local SC = g("SurvivorCompanion")
    local T = type(SC) == "table" and SC.Topology or nil
    if type(T) ~= "table" or type(T.classifyEdge) ~= "function" or T._solPlace then return T ~= nil end
    local base = T.classifyEdge
    T._solPlace = true
    T.classifyEdge = function(actor, fromSquare, toSquare, options)
        local r = base(actor, fromSquare, toSquare, options)
        if type(r) ~= "table" or r.traversable ~= true then return r end
        local aff = r.affordance
        local extra = (aff == "fence" and M.FENCE_EXTRA) or ((aff == "window" or aff == "window_frame") and M.WINDOW_EXTRA) or nil
        if extra == nil or actor == nil or actor ~= solCached() or not M.on() or M.danger(actor) then return r end
        local c = memo[r]
        if c == nil then
            c = {}
            for k, v in pairs(r) do c[k] = v end
            c.cost = (tonumber(r.cost) or 1) + extra
            c.solPlaceExtra = extra
            memoN = memoN + 1
            if memoN > 4096 then memo, memoN = {}, 1 end                           -- Kahlua may not honour weak keys: keep it bounded
            memo[r] = c
        end
        return c
    end
    log("Living Fellows edge costs: fence +" .. M.FENCE_EXTRA .. ", window +" .. M.WINDOW_EXTRA .. " for Sol while calm")
    return true
end

-- ---------------------------------------------------------------- verbs
local function dump(radius)
    local a = solActor()
    if a == nil then return false, "no_sol" end
    local px, py, pz = posOf(a)
    radius = math.max(4, math.min(tonumber(radius) or 20, 40))
    local f = g("getFileWriter")
    if f == nil then return false, "no_file_writer" end
    local w = f("SolPlace_dump.txt", true, false)
    w:write("-- SolPlace dump: x,y,standable,N kind,N state,W kind,W state  around " .. px .. "," .. py .. "," .. pz .. "\n")
    local function s(st) if st == nil then return "-" end return (st.open and "o" or "c") .. (st.locked and "l" or "") .. (st.barricaded and "b" or "") .. (st.noGlass and "g" or "") end
    for y = py - radius, py + radius do
        for x = px - radius, px + radius do
            local nk, ns = Live.edge(x, y, pz, "N")
            local wk, ws = Live.edge(x, y, pz, "W")
            w:write(x .. "," .. y .. "," .. (Live.standable(x, y, pz) and 1 or 0) .. "," .. nk .. "," .. s(ns) .. "," .. wk .. "," .. s(ws) .. "\n")
        end
    end
    w:close()
    return true, "dumped " .. (radius * 2 + 1) .. "x" .. (radius * 2 + 1) .. " to Zomboid/Lua/SolPlace_dump.txt"
end
function M.order(option)
    option = tostring(option or "status")
    if option == "status" then
        local s = M.stats
        local c = {}
        for k, v in pairs(s.crossings) do c[#c + 1] = k .. "=" .. v end
        return true, string.format("on=%s routes=%d legs=%d direct=%d fallbacks=%d nodes=%d maxSliceMs=%d crossings[%s] walking=%s", tostring(M.on()),
            s.routes, s.legs, s.direct, s.fallbacks, s.nodes, s.maxSliceMs, table.concat(c, " "), M.R and (M.R.gx .. "," .. M.R.gy) or "-")
    end
    local verb, rest = string.match(option, "^(%a+)%s*(.*)$")
    if verb == "dump" then return dump(rest) end
    local x, y = string.match(rest or "", "(%-?%d+)%s*,%s*(%-?%d+)")
    x, y = tonumber(x), tonumber(y)
    local a = solActor()
    if x == nil or a == nil then return false, "usage: sol_place status | dump [r] | route x,y | access x,y" end
    local px, py, pz = posOf(a)
    if verb == "access" then
        local t = {}
        for _, s in ipairs(M.access(x, y, pz)) do t[#t + 1] = s.x .. "," .. s.y end
        return true, "access " .. x .. "," .. y .. ": " .. (#t > 0 and table.concat(t, " ") or "none")
    end
    if verb == "route" then
        local j = M.route(px, py, pz, { { x = x, y = y } })
        if j.state ~= "done" then return true, "no route: " .. tostring(j.why) end
        return true, string.format("%d steps cost %.1f doors %d windows %d fences %d legs %d nodes %d", #j.path, j.cost, j.counts.door or 0,
            (j.counts.window or 0) + (j.counts.frame or 0), j.counts.fence or 0, #j.legs, j.nodes)
    end
    return false, "unknown_option"
end

function M.install()
    if M._installed then return end
    if type(U.solGoto) ~= "function" then return end
    M._installed = true
    M._orig = U.solGoto
    U.solGoto = function(x, y, z)
        if not M.on() then return M._orig(x, y, z) end
        local ok, a, b = pcall(M.go, x, y, z)
        if ok then return a, b end
        log("error " .. tostring(a))
        M.R = nil
        return M._orig(x, y, z)
    end
    local base = U.runAction
    if type(base) == "function" then
        U.runAction = function(id, option)
            if id == "sol_place" then return M.order(option) end
            return base(id, option)
        end
    end
    local budget = g("SolBudget")
    if type(budget) == "table" and type(budget.register) == "function" then
        budget.register("sol_place", function(left) pcall(M.tick, left) end, { everyMs = M.TICK_MS, priority = 3 })
    elseif Events and Events.OnTick then
        local nextAt = 0
        Events.OnTick.Add(function() local t = nowMs(); if t < nextAt then return end; nextAt = t + M.TICK_MS; pcall(M.tick, 2) end)
    end
    if Events then
        for _, name in ipairs({ "OnObjectAdded", "OnObjectAboutToBeRemoved", "OnTileRemoved" }) do
            local ev = Events[name]
            if ev and type(ev.Add) == "function" then
                ev.Add(function(o)
                    local sq = call(o, "getSquare")
                    if sq ~= nil then M.invalidate(floor(call(sq, "getX")), floor(call(sq, "getY")), floor(call(sq, "getZ"))) end
                end)
            end
        end
    end
    pcall(M.wrapTopology)
    log("ready v" .. M.VERSION .. " (switch spatial_access=" .. tostring(M.on()) .. ")")
end
-- after SolActions defines U.solGoto and after Living Fellows loads its Topology
if Events and Events.OnGameStart then Events.OnGameStart.Add(function() pcall(M.install) end) end
return M

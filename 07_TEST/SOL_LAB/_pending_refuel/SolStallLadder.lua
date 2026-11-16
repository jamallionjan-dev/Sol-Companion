-- SolStallLadder.lua - a driver never stands still. Switch: stall_ladder.
--   Stuck (the Java way round stalled, its goal was taken, a nudge stopped, or she simply stands with nothing to do),
--   she climbs one rung at once, never more than ~3 s idle:
--     1 replan from where she stands, to a goal she has not tried (further on, or the other side of the lane)
--     2 an angled nudge                    3 back up 3-4 tiles            4 replan from there, free to turn and reverse
--     5 another road: she says one plain line, the road planner goes round this place
--   Bounded: three other roads per drive, MAX_TOTAL rungs per drive; past that the drive ends as "route_blocked".
--   SCDriving calls onFail / onBlocked / onDone / passed / watch through a table of its own helpers (ops), so this file
--   runs headless in the lab. Details go to the log; the one spoken line has no technical words.
SolStallLadder = SolStallLadder or {}
local M = SolStallLadder
M.VERSION = "0.1.0"

M.IDLE_MS = 3000            -- the watchdog: this long without moving half a tile, with nothing running, is standing still
M.SPOT_TILES = 8            -- stuck again this close to where the ladder started: the same place, the ladder goes on
M.MAX_TOTAL = 40            -- rung tries per drive
M.MAX_REROUTES = 3          -- other roads per drive (SCDriving's own job.attempts < 3 also holds)
M.SAY_GAP_MS = 120000
M.EPISODE_MS = 60000        -- the watchdog only acts within this long of a ladder step or a way round
M.MAX_GOAL = 44             -- SCDriving's JNAV_MAX_GOAL is 45
M.LINE = "\\u0639\\u0644\\u0642\\u062A \\u0647\\u0648\\u0646\\u060C \\u0631\\u062D \\u062C\\u0631\\u0651\\u0628 \\u0645\\u0646 \\u0637\\u0631\\u064A\\u0642 \\u062A\\u0627\\u0646\\u064A."
M.RUNGS = { "replan", "nudge", "reverse", "replan_wide", "reroute" }
M.TRIES = { replan = 3, nudge = 1, reverse = 2, replan_wide = 3, reroute = 1 }
M.DISTS = { 12, 18, 24, 30, 38 }
M.SIDES = { 0, 3, -3 }
M.BACK = { 3.5, 2.5 }
M.SKIP = { blocked = true, arrived = true, engine_failed = true, turn_failed = true, turning = true, turned = true }

local function finite(v)
    v = tonumber(v)
    if v == nil or v ~= v or v == math.huge or v == -math.huge then return nil end
    return v
end

function M.on()
    local A = rawget(_G, "SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("stall_ladder") == true
end

local function drive(job)
    local d = job.slDrive
    if type(d) ~= "table" then d = { total = 0, reroutes = 0 }; job.slDrive = d end
    return d
end

local function rungIndex(name)
    for i = 1, #M.RUNGS do if M.RUNGS[i] == name then return i end end
    return nil
end

local function newSpot(job, x, y, current)
    job.sl = { x = x, y = y, rung = 1, tries = 0, tried = {}, since = current }
    return job.sl
end

-- ---------------------------------------------------------------- is there room for the car there? (Lua's view; Java has the last word)
local function insideCar(c, px, py)
    local dx, dy = px - c.x, py - c.y
    local fx, fy = finite(c.fx), finite(c.fy)
    if fx == nil or fy == nil or fx * fx + fy * fy < 0.01 then return dx * dx + dy * dy <= 2.2 * 2.2 end
    local len = math.sqrt(fx * fx + fy * fy)
    fx, fy = fx / len, fy / len
    local along, across = dx * fx + dy * fy, dx * (-fy) + dy * fx
    return math.abs(along) <= (finite(c.halfL) or 2.4) + 0.3 and math.abs(across) <= (finite(c.halfW) or 1.1) + 0.3
end

function M.spotFree(world, x, y, hx, hy, halfL, halfW, mine)
    if type(world) ~= "table" then return true end
    halfL, halfW = finite(halfL) or 2.4, finite(halfW) or 1.1
    local samples = {}
    for _, a in ipairs({ -halfL, 0, halfL }) do
        for _, b in ipairs({ -halfW, 0, halfW }) do
            samples[#samples + 1] = { x + hx * a - hy * b, y + hy * a + hx * b }
        end
    end
    for i = 1, #samples do
        local px, py = samples[i][1], samples[i][2]
        if type(world.kind) == "function" then
            local ok, k = pcall(world.kind, px, py)
            if ok and (k == "solid" or k == "post") then return false end
        end
        if type(world.open) == "function" then
            local ok, open = pcall(world.open, px, py)
            if ok and open == false then return false end
        end
    end
    if type(world.cars) == "function" then
        local ok, cars = pcall(world.cars, x, y, halfL + 5)
        if ok and type(cars) == "table" then
            for _, c in ipairs(cars) do
                if c.v ~= mine and finite(c.x) and finite(c.y) then
                    for i = 1, #samples do
                        if insideCar(c, samples[i][1], samples[i][2]) then return false end
                    end
                end
            end
        end
    end
    return true
end

-- ---------------------------------------------------------------- goals along the road ahead of her, and beside it
function M.candidates(points, x, y, hx, hy)
    local out = {}
    local function add(px, py, dx, dy)
        for _, s in ipairs(M.SIDES) do
            local gx, gy = px - dy * s, py + dx * s
            if (gx - x) ^ 2 + (gy - y) ^ 2 <= M.MAX_GOAL * M.MAX_GOAL then
                out[#out + 1] = { x = gx, y = gy, hx = dx, hy = dy, key = math.floor(gx + 0.5) .. ":" .. math.floor(gy + 0.5) }
            end
        end
    end
    if type(points) ~= "table" or #points < 2 then
        for _, d in ipairs(M.DISTS) do add(x + hx * d, y + hy * d, hx, hy) end
        return out
    end
    local bi, bd = 1, nil
    for i = 1, #points do
        local p = points[i]
        local d = (p.x - x) ^ 2 + (p.y - y) ^ 2
        if bd == nil or d < bd then bi, bd = i, d end
    end
    local di, run = 1, 0
    for i = bi, #points - 1 do
        local a, b = points[i], points[i + 1]
        local seg = math.sqrt((b.x - a.x) ^ 2 + (b.y - a.y) ^ 2)
        if seg > 0.01 then
            local dx, dy = (b.x - a.x) / seg, (b.y - a.y) / seg
            while di <= #M.DISTS and run + seg >= M.DISTS[di] do
                local t = M.DISTS[di] - run
                add(a.x + dx * t, a.y + dy * t, dx, dy)
                di = di + 1
            end
        end
        run = run + seg
        if di > #M.DISTS then break end
    end
    if di <= #M.DISTS then                                   -- the route ends sooner: its end, once
        local a, b = points[#points - 1], points[#points]
        local seg = math.sqrt((b.x - a.x) ^ 2 + (b.y - a.y) ^ 2)
        if seg > 0.01 then add(b.x, b.y, (b.x - a.x) / seg, (b.y - a.y) / seg) end
    end
    return out
end

-- ---------------------------------------------------------------- one try on one rung: "started", "tried" (did not start) or "none" (nothing left on this rung)
local function tryReplan(job, sl, current, ops, wide)
    local x, y, hx, hy = ops.pose(job)
    local size = ops.size(job)
    if x == nil or type(size) ~= "table" then return "none" end
    local list = M.candidates(ops.points(job), x, y, hx, hy)
    for _, c in ipairs(list) do
        if not sl.tried[c.key] then
            sl.tried[c.key] = true
            local free = ops.free(job, c.x, c.y, c.hx, c.hy, size)
            if free == false then
                ops.log(job, string.format("stall_ladder: goal %.0f,%.0f has no room, skipped", c.x, c.y))
            elseif ops.plan(job, x, y, hx, hy, c.x, c.y, c.hx, c.hy, size, wide and "replan_wide" or "replan", wide, current) then
                ops.log(job, string.format("stall_ladder: %s to %.0f,%.0f", wide and "replanning, free to back up" or "replanning from here", c.x, c.y))
                return "started"
            else
                ops.log(job, string.format("stall_ladder: the planner would not take goal %.0f,%.0f", c.x, c.y))
                return "tried"                                   -- one goal per try, started or not
            end
        end
    end
    return "none"
end

local function tryReverse(job, sl, current, ops)
    local x, y, hx, hy = ops.pose(job)
    local size = ops.size(job)
    if x == nil or type(size) ~= "table" then return "none" end
    sl.back = (sl.back or 0) + 1
    local b = M.BACK[sl.back]
    if b == nil then return "none" end
    local gx, gy = x - hx * b, y - hy * b
    if ops.free(job, gx, gy, hx, hy, size) ~= false and ops.plan(job, x, y, hx, hy, gx, gy, hx, hy, size, "reverse", true, current) then
        ops.log(job, string.format("stall_ladder: backing up %.1f tiles", b))
        return "started"
    end
    ops.log(job, string.format("stall_ladder: no room to back up %.1f tiles", b))
    return "tried"
end

local function tryNudge(job, sl, current, ops)
    local x, y, hx, hy = ops.pose(job)
    if x == nil then return "none" end
    if ops.nudge(job, x, y, hx, hy, x + hx * 3, y + hy * 3, current) then
        ops.log(job, "stall_ladder: nudging out at an angle")
        return "started"
    end
    ops.log(job, "stall_ladder: no room for a nudge")
    return "none"
end

local function tryReroute(job, sl, current, ops)
    local d = drive(job)
    if d.reroutes >= M.MAX_REROUTES then
        ops.log(job, "stall_ladder: every rung and " .. tostring(d.reroutes) .. " other roads tried: the drive ends here")
        ops.park(job, "route_blocked")
        return "parked"
    end
    d.reroutes = d.reroutes + 1
    local x, y, hx, hy = ops.pose(job)
    local bx, by = sl.x, sl.y
    if x ~= nil then bx, by = x + hx * 3, y + hy * 3 end
    local ok = ops.reroute(job, { blockedX = bx, blockedY = by })
    if not ok then
        ops.log(job, "stall_ladder: no other road from here: the drive ends here")
        if not job.parked then ops.park(job, "route_blocked") end
        return "parked"
    end
    if d.saidAt == nil or current - d.saidAt >= M.SAY_GAP_MS then
        d.saidAt = current
        ops.say(job, M.LINE)
    end
    ops.log(job, "stall_ladder: all rungs used here: another road (" .. tostring(d.reroutes) .. ")")
    job.sl = { x = sl.x, y = sl.y, rung = 1, tries = 0, tried = {}, since = current }   -- a new road, the same place: the ladder starts over
    return "started"
end

local TRY = {
    replan = function(job, sl, current, ops) return tryReplan(job, sl, current, ops, false) end,
    nudge = tryNudge,
    reverse = tryReverse,
    replan_wide = function(job, sl, current, ops) return tryReplan(job, sl, current, ops, true) end,
    reroute = tryReroute,
}

-- the next rung, at once. Always ends in something running, a new road, or the drive ended: never in nothing.
function M.next(job, current, ops)
    local d, sl = drive(job), job.sl
    if sl == nil then
        local x, y = ops.pose(job)
        sl = newSpot(job, x or 0, y or 0, current)
    end
    d.lastAt = current
    for _ = 1, 24 do
        local name = M.RUNGS[sl.rung]
        if name == nil then sl.rung, sl.tries = #M.RUNGS, 0; name = "reroute" end
        if sl.tries >= (M.TRIES[name] or 1) then
            sl.rung, sl.tries = sl.rung + 1, 0
        else
            sl.tries = sl.tries + 1
            d.total = d.total + 1
            if d.total > M.MAX_TOTAL then
                ops.log(job, "stall_ladder: " .. tostring(M.MAX_TOTAL) .. " tries on this drive: the drive ends here")
                ops.park(job, "route_blocked")
                return "parked"
            end
            local r = TRY[name](job, sl, current, ops)
            if r == "started" or r == "parked" then return r end
            if r ~= "tried" then sl.rung, sl.tries = sl.rung + 1, 0 end   -- nothing left on this rung: the next one, now
            sl = job.sl
        end
    end
    ops.park(job, "route_blocked")
    return "parked"
end

local function sameSpot(job, ops)
    local sl = job.sl
    if sl == nil then return false end
    local x, y = ops.pose(job)
    if x == nil then return true end
    return (x - sl.x) ^ 2 + (y - sl.y) ^ 2 <= M.SPOT_TILES * M.SPOT_TILES
end

-- a way round, a nudge or a back-up failed (why: SolNav's reason)
function M.onFail(job, why, status, current, ops)
    if job.sl ~= nil and not sameSpot(job, ops) then job.sl = nil end
    ops.log(job, "stall_ladder: that did not work (" .. tostring(why) .. "): next rung")
    return M.next(job, current, ops)
end

-- the road follower stopped against something
function M.onBlocked(job, status, current, ops)
    if job.sl ~= nil and not sameSpot(job, ops) then job.sl = nil end
    if job.sl == nil then ops.log(job, "stall_ladder: stuck: starting the ladder") end
    return M.next(job, current, ops)
end

-- a plan the ladder drew is done; true when the ladder takes it from here
function M.onDone(job, kind, status, current, ops)
    if kind ~= "reverse" then M.passed(job); return false end
    local sl = job.sl
    if sl == nil then return false end
    sl.rung, sl.tries = rungIndex("replan_wide"), 0
    ops.log(job, "stall_ladder: backed up: replanning from here")
    M.next(job, current, ops)
    return true
end

-- past it: the next obstacle starts from the first rung (the drive's totals stay)
function M.passed(job)
    job.sl = nil
end

-- the watchdog: true when it took this tick
function M.watch(job, state, status, current, ops)
    if job.managed ~= true or job.precise or job.parked or job.jnav or job.steer or job.unstick then return false end
    local x, y = ops.pose(job)
    if x == nil then return false end
    local w = job.slWatch
    if w == nil or (x - w.x) ^ 2 + (y - w.y) ^ 2 >= 0.25 then job.slWatch = { x = x, y = y, at = current }; return false end
    if M.SKIP[tostring(state)] or job.phase == "streaming_wait" or job.phase == "waiting" then w.at = current; return false end
    if (state == "follow" or state == "avoiding") and (finite(status and status.cruiseKmh) or 0) > 0 then return false end   -- SCDriving's own 3 s check owns that
    local d = job.slDrive
    local episode = job.sl ~= nil or job.bypass == true or (type(d) == "table" and d.lastAt ~= nil and current - d.lastAt < M.EPISODE_MS)
    if not episode or current - w.at < M.IDLE_MS then return false end
    w.at = current
    ops.log(job, "stall_ladder: standing still with nothing running (" .. tostring(state) .. "): next rung")
    M.next(job, current, ops)
    return true
end

return M

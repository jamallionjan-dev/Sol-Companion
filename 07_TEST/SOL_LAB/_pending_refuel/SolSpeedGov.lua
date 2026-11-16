-- SolSpeedGov.lua - switch speed_levels: the GPS buttons' real speeds (20 / 40 / 65 km/h) and a governor that keeps the
-- fast ones safe on the route ahead.
-- What Living Fellows' driver does by itself (SolCombined.jar, read with javap; SCDriveControl source byte-identical):
--   * it brakes by one model: stopping distance 1.5 + 0.4 v + v^2 / 6 tiles (v in m/s, 3 m/s^2) - SCDriveControl;
--   * the bumper scan looks max(8, stop(cruise + 5) + 4) tiles ahead, never more than 64 - SCCompanionDriver/SCLaneScan;
--   * it slows for a bend only when ONE route vertex turns more than 12 / 25 degrees (to 12 / 6 km/h), looking
--     clamp(stop(speed) + 5, 9, 64) tiles ahead - SCRoadFollower.
-- What it does not do: a curve drawn as several small vertices (each under 12 degrees) is never slowed for, and the look
-- for a bend shrinks as she brakes (brake, see nothing, speed up, see it again). This governor reads the route ahead,
-- finds the speed she may still carry here so that she is at the bend's speed when she reaches it (same 3 m/s^2), and
-- when that is under her cruise it re-issues the rest of the route at the bend's speed (the same driveFollow call a speed
-- button makes). Past the bend the cruise goes back up. On straight road it never asks for more than the 64-tile scan can
-- stop for (65.5 km/h at 3 m/s^2). It never touches a drive that is going round something (jnav, steer, bypass, avoiding).
local M = {}
SolSpeedGov = M
M.VERSION = "0.1.0"
M.LEVELS = { slow = 20, normal = 40, fast = 65 }
M.MAX_KMH = 70        -- the jar's new ceiling (SCDriveControl.MAX_CRUISE_KMH, build_s80_speed_levels.py)
M.DECEL = 3.0         -- m/s^2, LF's own braking model (SCDriveControl.BRAKE_DECELERATION)
M.LAT = 3.0           -- m/s^2 sideways allowed in a bend: an assumption, not a game number (in-game test)
M.SCAN = 64           -- tiles, SCLaneScan.MAX_LOOK_AHEAD
M.MIN_KMH = 12        -- under this the Java corner rule (12 / 6 km/h) does the rest
M.WINDOW = 12         -- tiles over which the turning of one bend is added up
M.BEND = math.rad(12) -- less turning than this inside a window is not a bend
M.FROM_KMH = 30       -- the governor works only for a cruise above this
M.EVERY_MS = 300
M.RAISE_MS = 1500
M.STEP = 5

local function on(name)
    local A = rawget(_G, "SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on(name) == true
end
function M.on() return on("speed_levels") end
local function log(s) print("[SolDrive] s80 " .. tostring(s)) end
local function num(v) v = tonumber(v); if v == nil or v ~= v or v == math.huge or v == -math.huge then return nil end; return v end

-- Tiles to stop from kmh, LF's formula with a chosen deceleration.
function M.stopDist(kmh, decel)
    local v = math.abs(num(kmh) or 0) / 3.6
    return 1.5 + v * 0.4 + v * v / (2 * (decel or M.DECEL))
end
-- The highest km/h whose stopping distance fits in dist tiles.
function M.maxKmhFor(dist, decel)
    local a = 1 / (2 * (decel or M.DECEL))
    local c = (num(dist) or 0) - 1.5
    if c <= 0 then return 0 end
    return (-0.4 + math.sqrt(0.16 + 4 * a * c)) / (2 * a) * 3.6
end
function M.scanCap(decel) return M.maxKmhFor(M.SCAN, decel) end

local function wrap(a)
    while a > math.pi do a = a - 2 * math.pi end
    while a < -math.pi do a = a + 2 * math.pi end
    return a
end
local function px(p) return type(p) == "table" and num(p.x) or nil end
local function py(p) return type(p) == "table" and num(p.y) or nil end

-- Where the car is on the route: the nearest segment (searched from the last one forward, so a hairpin's other leg is not
-- taken), the share t along it, its distance and the route's direction there.
function M.project(points, x, y, hint)
    local n = type(points) == "table" and #points or 0
    if n < 2 or not num(x) or not num(y) then return nil end
    local first, last = 1, n - 1
    if num(hint) then first, last = math.max(1, hint - 2), math.min(n - 1, hint + 40) end
    local best
    for i = first, last do
        local ax, ay, bx, by = px(points[i]), py(points[i]), px(points[i + 1]), py(points[i + 1])
        if ax and ay and bx and by then
            local dx, dy = bx - ax, by - ay
            local len2 = dx * dx + dy * dy
            local t = len2 > 0 and math.max(0, math.min(1, ((x - ax) * dx + (y - ay) * dy) / len2)) or 0
            local cx, cy = ax + dx * t, ay + dy * t
            local d = math.sqrt((x - cx) ^ 2 + (y - cy) ^ 2)
            if best == nil or d < best.dist - 0.01 then
                local len = math.sqrt(len2)
                best = { seg = i, t = t, dist = d, x = cx, y = cy, tx = len > 0 and dx / len or 1, ty = len > 0 and dy / len or 0 }
            end
        end
    end
    return best
end

-- The bends ahead: every vertex past the car, its distance along the route and how much the route turns there.
function M.bendsAhead(points, pr, horizon)
    local out = {}
    local n = #points
    local i = pr.seg
    local d = math.sqrt((px(points[i + 1]) - pr.x) ^ 2 + (py(points[i + 1]) - pr.y) ^ 2)
    for k = i + 1, n - 1 do
        if d > horizon then break end
        local a1 = math.atan2(py(points[k]) - py(points[k - 1]), px(points[k]) - px(points[k - 1]))
        local a2 = math.atan2(py(points[k + 1]) - py(points[k]), px(points[k + 1]) - px(points[k]))
        out[#out + 1] = { d = d, a = wrap(a2 - a1) }
        d = d + math.sqrt((px(points[k + 1]) - px(points[k])) ^ 2 + (py(points[k + 1]) - py(points[k])) ^ 2)
    end
    return out, d
end

-- The speed (km/h) she may carry here so that every bend ahead is reached at its own speed, and the bend speed to ask
-- for when that binds. Returns cap, target, why.
function M.cap(points, pr, kmhNow, want)
    want = num(want) or 0
    local cap, target, why, bendEnd = want, want, nil, nil
    local scan = M.scanCap()
    if scan < cap then cap, target, why = scan, scan, "scan" end
    local horizon = math.min(160, M.stopDist(math.max(want, num(kmhNow) or 0)) + M.WINDOW + 10)
    local bends = M.bendsAhead(points, pr, horizon)
    local reaction = 1.5 + (num(kmhNow) or 0) / 3.6 * 0.4
    for idx = 1, #bends do
        local b = bends[idx]
        local sum, lastD = 0, b.d
        for j = idx, #bends do
            if bends[j].d - b.d > M.WINDOW then break end
            sum, lastD = sum + math.abs(bends[j].a), bends[j].d
        end
        if sum >= M.BEND then
            local radius = math.max(3, lastD - b.d) / sum
            local vc = math.max(M.MIN_KMH / 3.6, math.sqrt(M.LAT * radius))
            local allowed = math.sqrt(vc * vc + 2 * M.DECEL * math.max(0, b.d - reaction)) * 3.6
            if allowed < cap then
                cap, target, bendEnd = allowed, vc * 3.6, lastD
                why = string.format("bend %.0f deg in %.0f tiles", math.deg(sum), b.d)
            end
        end
    end
    return cap, math.min(target, want), why, bendEnd
end

-- Whole steps of 5 km/h, never under MIN_KMH, never over want.
function M.band(kmh, want)
    if kmh >= want - 0.5 then return want end
    return math.max(M.MIN_KMH, math.min(want, math.floor(kmh / M.STEP) * M.STEP))
end

-- The route from where the car is to its end (the bridge refuses points closer than half a tile).
function M.rest(points, pr)
    local out = { { x = pr.x, y = pr.y, width = points[pr.seg + 1].width or points[pr.seg].width } }
    for k = pr.seg + 1, #points do
        local p = points[k]
        local q = out[#out]
        if (p.x - q.x) ^ 2 + (p.y - q.y) ^ 2 >= 1 or k == #points then out[#out + 1] = p end
    end
    if #out >= 2 and (out[#out].x - out[#out - 1].x) ^ 2 + (out[#out].y - out[#out - 1].y) ^ 2 < 0.25 then
        if #out > 2 then table.remove(out, #out - 1) else return nil end
    end
    if #out < 2 then return nil end
    return out
end
-- Tiles from the route's start to the car.
function M.along(points, pr)
    local d = 0
    for k = 1, pr.seg - 1 do
        d = d + math.sqrt((px(points[k + 1]) - px(points[k])) ^ 2 + (py(points[k + 1]) - py(points[k])) ^ 2)
    end
    return d + math.sqrt((pr.x - px(points[pr.seg])) ^ 2 + (pr.y - py(points[pr.seg])) ^ 2)
end
local function lengthFrom(points, pr)
    local d = math.sqrt((px(points[pr.seg + 1]) - pr.x) ^ 2 + (py(points[pr.seg + 1]) - pr.y) ^ 2)
    for k = pr.seg + 1, #points - 1 do
        d = d + math.sqrt((px(points[k + 1]) - px(points[k])) ^ 2 + (py(points[k + 1]) - py(points[k])) ^ 2)
    end
    return d
end

-- One look, from SCDriving's tick while she follows the road. follow(actor, route, kmh) is SCDriving's followNative,
-- method(object, name) its SC.Call wrapper (ok, value).
function M.tick(job, status, current, follow, method)
    if not M.on() or type(job) ~= "table" or type(status) ~= "table" or type(follow) ~= "function" then return end
    local want = num(job.speedKmh)
    if not want or want <= M.FROM_KMH then return end
    if job.phase ~= "following" or job.precise or job.jnav or job.steer or job.unstick or job.bypass then return end
    if (status.mode or status.state) ~= "follow" then return end
    local route = job.route
    local points = type(route) == "table" and (route.points or route) or nil
    if type(points) ~= "table" or #points < 2 then return end
    local g = job.gov80
    if type(g) ~= "table" or g.want ~= want or g.route ~= route then
        g = { want = want, route = route, at = -1e12, changedAt = -1e12 }
        job.gov80 = g
    end
    current = num(current) or 0
    if current - g.at < M.EVERY_MS then return end
    local dt = (current - g.at) / 1000
    g.at = current
    local okX, x = method(job.vehicle, "getX")
    local okY, y = method(job.vehicle, "getY")
    x, y = okX and num(x), okY and num(y)
    if not x or not y then return end
    local speed = math.abs(num(status.speedKmh) or 0)
    local cruiseNow = num(status.cruiseKmh) or want
    if g.lastV and dt > 0 and dt < 2 and speed < g.lastV then                  -- for the in-game test: how hard her brakes really are
        local rate = (g.lastV - speed) / 3.6 / dt
        if cruiseNow < g.lastV - 3 and rate > (g.hardest or 0) then g.hardest = rate end
    end
    g.lastV = speed
    local moved = g.lx and math.sqrt((x - g.lx) ^ 2 + (y - g.ly) ^ 2) or 0
    local hx, hy
    if moved > 0.5 then hx, hy = (x - g.lx) / moved, (y - g.ly) / moved end
    if moved > 0.5 or not g.lx then g.lx, g.ly = x, y end
    local pr = M.project(points, x, y, g.seg)
    if not pr then return end
    g.seg = pr.seg
    local cap, target, why, bendEnd = M.cap(points, pr, speed, want)
    local along = M.along(points, pr)
    local ask
    if cap < cruiseNow - 2 then                                                  -- a bend (or the scan) binds: down to its speed now,
        ask = M.band(target, want)                                               -- and held there until the bend is behind her
        if bendEnd then g.holdUntil = math.max(g.holdUntil or 0, along + bendEnd + 2) end
    elseif cruiseNow < want and current - g.changedAt >= M.RAISE_MS and along >= (g.holdUntil or 0) then   -- past it: back up
        local up = M.band(cap, want)
        if up >= want or up >= cruiseNow + M.STEP then ask = up end
    end
    if not ask or math.abs(ask - cruiseNow) < 0.5 then return end
    -- re-issue only from a clear place on the route: on it, going its way, with road left
    if pr.dist > 3 or (hx and hx * pr.tx + hy * pr.ty < 0.7) or lengthFrom(points, pr) < 15 then return end
    local rest = M.rest(points, pr)
    if not rest then return end
    local ok, why2 = follow(job.actor, { points = rest }, ask)
    if ok then
        log(string.format("speed %.0f -> %.0f km/h (cruise %.0f, now %.0f%s)", cruiseNow, ask, want, speed, why and (", " .. why) or ""))
        if ask >= want and g.hardest then log(string.format("hardest braking seen %.1f m/s2", g.hardest)); g.hardest = nil end
        g.changedAt = current
    else
        log("re-issue refused: " .. tostring(why2))
        g.changedAt = current
    end
end

return M

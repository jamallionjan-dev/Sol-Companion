-- SolStationSurvey.lua - s95 station_survey (council SOL_REVIEW section 47, plan DOCS/PLAN_station_survey.md). OFF by default.
-- Works only for the station refuel order: sol_fuel car_near / park / park_status, and the squares of sol_fuel car's walk.
--   1. The survey. Once per station per life, the squares within RADIUS of the pump are read: pumps with fuel
--      (the game's own test, getPipedFuelAmount() > 0), squares nobody can stand on (LF's isSquareFree, the same
--      test her walker uses), and walls between squares. Cached in ModData "Sol_StationSurvey" for this life only
--      (a new life empties it). Fuel, power, other cars and the player move, so they are read fresh every time.
--   2. The poses. Jamal's rule first: one free square is always kept between the fuel cap and the pump, and she stands
--      there. For each pump with fuel and power, 4 headings along the grid, and each square touching the pump: the car
--      centre that puts THIS car's fuel cap (its own GasTank area, from its vehicle script, so any KI5 car works) facing
--      the pump across that square, the body 0.3 clear of it, inside the game's own reach (the cap's square within 2
--      squares of the pump, ISVehiclePartMenu.getNearbyFuelPump). The body and a small margin on free squares, no wall inside it, a clear
--      lane ahead or behind it, and a walk from her door to the standing square. Best first: near, little turning,
--      standing square next to the pump, lanes open at both ends.
--   3. The drive. The Java planner (solNavPlan) to the best pose. A failed plan -> the next pose. After the stop the
--      game's own pump test and a real free square by the cap are checked from where the car really stands;
--      if they fail she re-parks (other side or other pump), at most MAX_REPARKS times.
--   4. The walk. Squares within arm's reach of the cap that are free now, nearest to the cap first (SolFuel's walk).
-- Answers are reason codes; the Mind speaks them (goal_engine RefuelErrand). No station, place or vehicle is named here.
SolUI = SolUI or {}
SolStationSurvey = SolStationSurvey or {}
local U, M = SolUI, SolStationSurvey
local loadedBefore = M.VERSION ~= nil   -- s95b: a reload in a running game (its tick already calls M.step through this table)
M.VERSION = "0.2.0"
M.RADIUS = 12            -- squares around the pump that are read once
M.PAD = 0.15             -- margin round the body when a pose's squares are checked
M.CLEAR = 0.3            -- between the body and the standing square
M.REACH = 1.5            -- standing square centre to the cap point (SolFuel's arm's reach is 1.6, its action accepts 1.9)
M.PUMP_SQUARES = 2       -- the game's own reach: the cap's square within 2 squares of the pump
M.LANE = 6               -- squares of open lane wanted ahead or behind
M.MAX_POSES = 8          -- poses tried by one park order
M.MAX_REPARKS = 2        -- after a stop that does not pass the check
M.DRIVE_MS = 60000       -- one pose: plan and drive
M.JOB_MS = 115000        -- one park order (the Mind waits 130 s)
M.CACHE_HOURS = 24       -- a station read longer ago than this is read again
M.MAX_STATIONS = 12
M.STORE = "Sol_StationSurvey"
M.LIFE = "Sol_Life"
M.HEADINGS = { { 1, 0 }, { 0, 1 }, { -1, 0 }, { 0, -1 } }
-- s95b: the planner looks at 60000 states at most. From the road 30 m off, a pose that faces back the way she came does not
-- fit in that (lab 10:26: 3 of 3 poses no_path_found). Further than APPROACH_MIN she first drives to a point beside the pose's
-- open lane end, facing the way she drives there; the short turn into the pose is a second plan from where she stopped.
M.APPROACH_MIN = 8       -- metres from the car to the pose before she goes by an approach point
M.APPROACH_SIDES = { 2.5, -2.5, 4, -4, 0 }   -- metres beside the lane's end, either side
M.MAX_APPROACHES = 3     -- approach points tried for one pose before the direct plan
M.job = M.job or nil
M.tried = M.tried or {}
M.mem = M.mem or {}       -- this session's copy when ModData is not there

local function g(name) return rawget(_G, name) end
local function log(m) print("[SolStation] " .. tostring(m)) end
local function nowMs() local f = g("getTimestampMs"); if type(f) == "function" then return f() end; return os.time() * 1000 end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function num(v) return tonumber(v) end
local function fn(name) local f = g(name); if type(f) == "function" then return f end; return nil end
local function cell() local f = fn("getCell"); if f then return f() end; return nil end
local function player() local f = fn("getSpecificPlayer"); if f then return f(0) end; return nil end
local function key(x, y) return math.floor(x) .. "," .. math.floor(y) end
local function sgn(v) if v < 0 then return -1 end; return 1 end
local function parts() local P = U.solFuelParts; if type(P) == "table" then return P end; return nil end

function M.on()
    local A = g("SolAuthority")
    if type(A) ~= "table" or type(A.on) ~= "function" then return false end
    local ok, on = pcall(A.on, "station_survey")
    return ok and on == true
end

local function failNote(reason, detail)
    local F = g("SolFailNote")
    if type(F) == "table" and type(F.note) == "function" then pcall(F.note, "station_survey", reason, detail) end
end

-- ---------------------------------------------------------------- this car
-- Everything in the car's own frame: along = forward, side = towards (-forward.y, forward.x).
function M.geometry(veh, s)
    if veh == nil then return nil, "no_car" end
    local part = call(veh, "getPartById", "GasTank")
    if part == nil then return nil, "no_gas_tank" end
    local area = call(part, "getArea")
    local cap = area ~= nil and call(veh, "getAreaCenter", area) or nil
    local capX, capY = num((call(cap, "getX"))), num((call(cap, "getY")))
    local cx, cy = num((call(veh, "getX"))), num((call(veh, "getY")))
    local Vec = g("Vector3f")
    local f = nil
    if type(Vec) == "table" and type(Vec.new) == "function" then local okV, v = pcall(Vec.new); if okV then f = call(veh, "getForwardVector", v) end end
    local hx, hy = num((call(f, "x"))), num((call(f, "z")))
    if capX == nil or capY == nil or cx == nil or cy == nil or hx == nil or hy == nil then return nil, "survey_no_cap" end
    local n = math.sqrt(hx * hx + hy * hy)
    if n < 1e-3 then return nil, "survey_no_cap" end
    hx, hy = hx / n, hy / n
    local B = g("SolBypass")
    local okS, size = false, nil
    if type(B) == "table" and type(B.measure) == "function" then okS, size = pcall(B.measure, veh) end
    if not okS or type(size) ~= "table" or num(size.halfLength) == nil or num(size.halfWidth) == nil then return nil, "park_unavailable" end
    local dx, dy = capX - cx, capY - cy
    local geo = { cx = cx, cy = cy, hx = hx, hy = hy, capX = capX, capY = capY, capAlong = dx * hx + dy * hy, capSide = -dx * hy + dy * hx,
        hl = num(size.halfLength), hw = num(size.halfWidth), wheelbase = size.wheelbase, kmax = size.kmax }
    local seat = s ~= nil and num((call(veh, "getSeat", s))) or nil
    if seat == nil or seat < 0 then seat = 0 end
    local doorArea = call(veh, "getPassengerArea", seat)
    local door = doorArea ~= nil and call(veh, "getAreaCenter", doorArea) or nil
    local ddx, ddy = num((call(door, "getX"))), num((call(door, "getY")))
    if ddx ~= nil and ddy ~= nil then
        geo.doorAlong, geo.doorSide = (ddx - cx) * hx + (ddy - cy) * hy, -(ddx - cx) * hy + (ddy - cy) * hx
    end
    return geo
end

-- ---------------------------------------------------------------- the station, read once
local function pumpFuel(sq)
    local objs = call(sq, "getObjects")
    local n = num((call(objs, "size"))) or 0
    for i = 0, n - 1 do
        local f = num((call(call(objs, "get", i), "getPipedFuelAmount")))
        if f ~= nil and f > 0 then return f end
    end
    return nil
end
local function freeSq(sq)
    local P = parts()
    if P and type(P.freeSquare) == "function" then local ok, v = pcall(P.freeSquare, sq); if ok then return v == true end end
    return call(sq, "isFree", false) == true
end

function M.scan(px, py)
    local c = cell()
    if c == nil then return nil end
    local R = M.RADIUS
    local w = { ox = px - R, oy = py - R, size = 2 * R + 1, solid = {}, wall = {}, pumps = {} }
    for y = py - R, py + R do
        for x = px - R, px + R do
            local sq = call(c, "getGridSquare", x, y, 0)
            local k = key(x, y)
            if sq == nil then w.solid[k] = "u"
            else
                if pumpFuel(sq) then w.pumps[#w.pumps + 1] = { x = x, y = y }; w.solid[k] = "p"
                elseif not freeSq(sq) then w.solid[k] = "o" end
                local e = call(c, "getGridSquare", x + 1, y, 0)
                if e ~= nil and call(sq, "isBlockedTo", e) == true then w.wall[k .. "E"] = true end
                local so = call(c, "getGridSquare", x, y + 1, 0)
                if so ~= nil and call(sq, "isBlockedTo", so) == true then w.wall[k .. "S"] = true end
            end
        end
    end
    return w
end

-- ModData keeps plain text: "x,y;x,y" lists
local function packSet(t) local out = {}; for k, v in pairs(t) do if v then out[#out + 1] = k .. "=" .. tostring(v) end end; return table.concat(out, ";") end
local function unpackSet(s) local t = {}; for part in string.gmatch(s or "", "[^;]+") do local k, v = string.match(part, "^(.-)=(.*)$"); if k then t[k] = v == "true" and true or v end end; return t end
local function store()
    local MD = g("ModData")
    if type(MD) ~= "table" or type(MD.getOrCreate) ~= "function" then return nil end
    local ok, d = pcall(MD.getOrCreate, M.STORE)
    if ok and type(d) == "table" then return d end
    return nil
end
local function lifeKey()
    local MD = g("ModData")
    if type(MD) ~= "table" or type(MD.getOrCreate) ~= "function" then return nil end
    local ok, life = pcall(MD.getOrCreate, M.LIFE)
    if not ok or type(life) ~= "table" or type(life.id) ~= "string" then return nil end
    return life.id .. "#" .. tostring(num(life.deaths) or 0)
end
local function hoursNow()
    local f = fn("getGameTime")
    local gt = f and f() or nil
    return num((call(gt, "getWorldAgeHours"))) or 0
end
-- her memory of stations: this life only
local function memory()
    local d = store() or M.mem
    local life = lifeKey() or "?"
    if d.life ~= life then
        d.life, d.st, d.n = life, {}, 0
        log("a new life: her station memory starts empty")
    end
    if type(d.st) ~= "table" then d.st, d.n = {}, 0 end
    return d
end
function M.forget() local d = store() or M.mem; d.st, d.n = {}, 0 end

function M.world(px, py, fresh)
    local d = memory()
    local h = hoursNow()
    if not fresh then
        for k, e in pairs(d.st) do
            local ox, oy = num(e.ox), num(e.oy)
            if ox and px - ox >= 3 and py - oy >= 3 and ox + num(e.size) - 1 - px >= 3 and oy + num(e.size) - 1 - py >= 3 and h - (num(e.t) or 0) <= M.CACHE_HOURS then
                local w = { ox = ox, oy = oy, size = num(e.size), solid = unpackSet(e.solid), wall = unpackSet(e.wall), pumps = {}, cached = true }
                for x, y in string.gmatch(e.pumps or "", "(%-?%d+),(%-?%d+)") do w.pumps[#w.pumps + 1] = { x = num(x), y = num(y) } end
                return w
            end
        end
    end
    local w = M.scan(px, py)
    if w == nil then return nil end
    local list = {}
    for _, p in ipairs(w.pumps) do list[#list + 1] = p.x .. "," .. p.y end
    if (d.n or 0) >= M.MAX_STATIONS then d.st, d.n = {}, 0 end
    d.st[key(px, py)] = { ox = w.ox, oy = w.oy, size = w.size, t = h, solid = packSet(w.solid), wall = packSet(w.wall), pumps = table.concat(list, ";") }
    d.n = (d.n or 0) + 1
    log(string.format("read the station at %d,%d once: %d pumps with fuel, %d squares nobody can stand on", px, py, #w.pumps, (function() local n = 0; for _ in pairs(w.solid) do n = n + 1 end; return n end)()))
    return w
end

-- what moves: cars, the player, the pumps' fuel and power
local function extentOf(v)
    local e = call(call(v, "getScript"), "getExtents")
    local ex, ez = num((call(e, "x"))), num((call(e, "z")))
    if ex and ez then return math.max(4, math.ceil(math.max(ex, ez) / 2) + 1) end       -- never less than 4: the script's units may be unscaled
    return 6
end
function M.live(w, own, includeOwn)
    w.cars, w.own = {}, {}
    local c = cell()
    local list = call(c, "getVehicles")
    local n = num((call(list, "size"))) or 0
    for i = 0, n - 1 do
        local v = call(list, "get", i)
        local vx, vy = num((call(v, "getX"))), num((call(v, "getY")))
        if vx and vy and vx > w.ox - 10 and vy > w.oy - 10 and vx < w.ox + w.size + 10 and vy < w.oy + w.size + 10 and (v ~= own or includeOwn) then
            local r = extentOf(v)
            for y = math.floor(vy) - r, math.floor(vy) + r do
                for x = math.floor(vx) - r, math.floor(vx) + r do
                    if call(v, "isIntersectingSquare", x, y, 0) == true then
                        if v == own then w.own[key(x, y)] = true else w.cars[key(x, y)] = true end
                    end
                end
            end
        end
    end
    local p = player()
    w.person = nil
    if p ~= nil and call(p, "getVehicle") == nil then
        local x, y = num((call(p, "getX"))), num((call(p, "getY")))
        if x and y then w.person = key(x, y) end
    end
    local P = parts()
    for _, pu in ipairs(w.pumps) do
        local sq = call(c, "getGridSquare", pu.x, pu.y, 0)
        pu.fuel = sq ~= nil and pumpFuel(sq) or 0
        pu.power = P ~= nil and type(P.hasPower) == "function" and P.hasPower(pu.x, pu.y) == true
    end
    return w
end

-- ---------------------------------------------------------------- poses (pure: tables in, tables out)
local function inside(w, x, y) return x >= w.ox and y >= w.oy and x < w.ox + w.size and y < w.oy + w.size end
local function blocked(w, x, y) local k = key(x, y); return not inside(w, x, y) or w.solid[k] ~= nil or (w.cars and w.cars[k]) == true or (w.own and w.own[k]) == true end
local function standAt(w, x, y) return not blocked(w, x, y) and w.person ~= key(x, y) end
M.standAt = standAt

-- an oriented box (centre, unit forward f, half length a, half width b) over the square x,y
local function boxHitsSquare(cx, cy, fx, fy, a, b, x, y)
    local qx, qy, lx, ly = x + 0.5 - cx, y + 0.5 - cy, -fy, fx
    if math.abs(qx) >= 0.5 + math.abs(fx) * a + math.abs(lx) * b then return false end
    if math.abs(qy) >= 0.5 + math.abs(fy) * a + math.abs(ly) * b then return false end
    if math.abs(qx * fx + qy * fy) >= a + 0.5 * (math.abs(fx) + math.abs(fy)) then return false end
    if math.abs(qx * lx + qy * ly) >= b + 0.5 * (math.abs(lx) + math.abs(ly)) then return false end
    return true
end
M.boxHitsSquare = boxHitsSquare
local function boxSquares(cx, cy, fx, fy, a, b)
    local out, r = {}, math.ceil(math.sqrt(a * a + b * b)) + 1
    for y = math.floor(cy) - r, math.floor(cy) + r do
        for x = math.floor(cx) - r, math.floor(cx) + r do
            if boxHitsSquare(cx, cy, fx, fy, a, b, x, y) then out[#out + 1] = { x = x, y = y } end
        end
    end
    return out
end
local function wallBetween(w, ax, ay, bx, by)
    if bx == ax + 1 then return w.wall[key(ax, ay) .. "E"] == true end
    if bx == ax - 1 then return w.wall[key(bx, by) .. "E"] == true end
    if by == ay + 1 then return w.wall[key(ax, ay) .. "S"] == true end
    if by == ay - 1 then return w.wall[key(bx, by) .. "S"] == true end
    return false
end
-- the body's squares are free and no wall runs through it; a person in the way counts too
local function bodyFree(w, sqs)
    local set = {}
    for _, q in ipairs(sqs) do
        if blocked(w, q.x, q.y) or w.person == key(q.x, q.y) then return false, nil end
        set[key(q.x, q.y)] = true
    end
    for _, q in ipairs(sqs) do
        if set[key(q.x + 1, q.y)] and wallBetween(w, q.x, q.y, q.x + 1, q.y) then return false, nil end
        if set[key(q.x, q.y + 1)] and wallBetween(w, q.x, q.y, q.x, q.y + 1) then return false, nil end
    end
    return true, set
end
-- on foot from one square to another round the parked body (he may stand in the way for a moment: only his square is not a place to stop)
local function walkable(w, fx0, fy0, tx, ty, body, maxNodes)
    if blocked(w, fx0, fy0) or body[key(fx0, fy0)] or not standAt(w, tx, ty) then return false end
    local seen, q, head = { [key(fx0, fy0)] = true }, { { fx0, fy0 } }, 1
    local steps = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } }
    while head <= #q and head <= (maxNodes or 600) do
        local e = q[head]; head = head + 1
        if e[1] == tx and e[2] == ty then return true end
        for _, d in ipairs(steps) do
            local x, y = e[1] + d[1], e[2] + d[2]
            local k = key(x, y)
            if not seen[k] and not blocked(w, x, y) and not body[k] and not wallBetween(w, e[1], e[2], x, y) then seen[k] = true; q[#q + 1] = { x, y } end
        end
    end
    return false
end
M.walkable = walkable

-- Her door square, or both sides when the car's script has no seat area. Returns a list of squares to start the walk from.
local function doorSquares(geo, cx, cy, fx, fy)
    local lx, ly = -fy, fx
    local out = {}
    local function at(along, side)
        local px, py = cx + fx * along + lx * side, cy + fy * along + ly * side
        out[#out + 1] = { x = math.floor(px), y = math.floor(py) }
    end
    local da = geo.doorAlong or 0
    if geo.doorSide ~= nil then at(da, sgn(geo.doorSide) * (geo.hw + 0.6)); at(da, -sgn(geo.doorSide) * (geo.hw + 0.6))   -- the far door is the second choice
    else at(da, geo.hw + 0.6); at(da, -(geo.hw + 0.6)) end
    return out
end

-- Jamal's rule: one free square is always kept between the fuel cap and the pump, and she stands there.
-- S (a square) is that square when it touches the pump square P (8 neighbours) and P lies beyond S as seen from the cap point A.
local function between(sx, sy, px, py, ax, ay)
    if (sx == px and sy == py) or math.abs(sx - px) > 1 or math.abs(sy - py) > 1 then return false end
    local ux, uy = px - sx, py - sy                                  -- from the square to the pump
    local vx, vy = sx + 0.5 - ax, sy + 0.5 - ay                      -- from the cap to the square
    local dS, dP = vx * vx + vy * vy, (px + 0.5 - ax) ^ 2 + (py + 0.5 - ay) ^ 2
    return ux * vx + uy * vy > 0 and dS < dP
end
M.between = between

-- Every pose that passes, best first. from = { x, y, hx, hy } where the car is now. tried = { [poseKey] = true }.
function M.poses(w, geo, from, tried)
    local out, why = {}, { reach = 0, body = 0, lane = 0, door = 0, pumps = 0, gap = 0 }
    local onEnd = (math.abs(geo.capAlong) - geo.hl) > (math.abs(geo.capSide) - geo.hw)
    for pi, p in ipairs(w.pumps) do
        if (p.fuel or 1) > 0 and p.power ~= false then
            why.pumps = why.pumps + 1
            for hi, h in ipairs(M.HEADINGS) do
                local fx, fy = h[1], h[2]
                local lx, ly = -fy, fx
                local best = nil
                for dy = -1, 1 do                                       -- the standing square touches the pump (the free square between)
                    for dx = -1, 1 do
                        local sx, sy = p.x + dx, p.y + dy
                        if (dx ~= 0 or dy ~= 0) and standAt(w, sx, sy) then
                            local scx, scy, cx, cy = sx + 0.5, sy + 0.5, nil, nil
                            if onEnd then
                                local a, sd = sgn(geo.capAlong) * (geo.hl + 0.5 + M.CLEAR), geo.capSide
                                cx, cy = scx - fx * a - lx * sd, scy - fy * a - ly * sd
                            else
                                local a, sd = geo.capAlong, sgn(geo.capSide) * (geo.hw + 0.5 + M.CLEAR)
                                cx, cy = scx - fx * a - lx * sd, scy - fy * a - ly * sd
                            end
                            local ax, ay = cx + fx * geo.capAlong + lx * geo.capSide, cy + fy * geo.capAlong + ly * geo.capSide
                            local pk = p.x .. "," .. p.y .. "/" .. hi .. "/" .. sx .. "," .. sy
                            if math.abs(math.floor(ax) - p.x) > M.PUMP_SQUARES or math.abs(math.floor(ay) - p.y) > M.PUMP_SQUARES
                                    or (ax - scx) ^ 2 + (ay - scy) ^ 2 > M.REACH * M.REACH then
                                why.reach = why.reach + 1
                            elseif not between(sx, sy, p.x, p.y, ax, ay) then
                                why.gap = why.gap + 1                       -- the cap does not face the pump across that square
                            elseif not (tried and tried[pk]) and not boxHitsSquare(cx, cy, fx, fy, geo.hl + 0.05, geo.hw + 0.05, sx, sy) then
                                local okB, body = bodyFree(w, boxSquares(cx, cy, fx, fy, geo.hl + M.PAD, geo.hw + M.PAD))
                                if not okB then why.body = why.body + 1
                                else
                                    local ll = math.min(geo.hl, M.LANE / 2)                -- a lane one body long, at most LANE squares: a long truck needs no 30 m run
                                    local ahead = bodyFree(w, boxSquares(cx + fx * (geo.hl + ll), cy + fy * (geo.hl + ll), fx, fy, ll, geo.hw + M.PAD))
                                    local behind = bodyFree(w, boxSquares(cx - fx * (geo.hl + ll), cy - fy * (geo.hl + ll), fx, fy, ll, geo.hw + M.PAD))
                                    if not ahead and not behind then why.lane = why.lane + 1
                                    else
                                        local door = nil
                                        for di, d in ipairs(doorSquares(geo, cx, cy, fx, fy)) do
                                            if door == nil and walkable(w, d.x, d.y, sx, sy, body, 600) then door = di end
                                        end
                                        if door == nil then why.door = why.door + 1
                                        else
                                            local turn = 1 - (fx * (from.hx or fx) + fy * (from.hy or fy))       -- 0 straight on, 1 a quarter turn, 2 turning round
                                            local diag = (dx ~= 0 and dy ~= 0) and 1 or 0     -- straight across the gap is best
                                            local score = math.sqrt((cx - from.x) ^ 2 + (cy - from.y) ^ 2) * 0.5 + turn * 3 + diag * 1.5
                                                + ((ahead and behind) and 0 or 2) + (door - 1) * 2
                                            if best == nil or score < best.score then
                                                best = { cx = cx, cy = cy, fx = fx, fy = fy, ax = ax, ay = ay, sx = sx, sy = sy, px = p.x, py = p.y,
                                                    score = score, key = pk, through = ahead and behind, farDoor = door > 1,
                                                    ahead = ahead == true, behind = behind == true }
                                            end
                                        end
                                    end
                                end
                            end
                        end
                    end
                end
                if best then out[#out + 1] = best end
            end
        end
    end
    table.sort(out, function(a, b) return a.score < b.score end)
    return out, why
end

-- s95b: points to drive to first, best first; empty when the pose is near. Each lies beside an open lane end of the pose,
-- the body on free squares, facing from the car towards it (an easy first plan). Through the lane ahead she backs in:
-- that second plan may reverse further (turnBack).
function M.approaches(w, geo, p, from)
    local out = {}
    if math.sqrt((p.cx - from.x) ^ 2 + (p.cy - from.y) ^ 2) < M.APPROACH_MIN then return out end
    local ll = math.min(geo.hl, M.LANE / 2)
    local lx, ly = -p.fy, p.fx
    local ends = {}
    if p.behind then ends[#ends + 1] = { -1, false } end
    if p.ahead then ends[#ends + 1] = { 1, true } end
    for ei, e in ipairs(ends) do
        for _, sd in ipairs(M.APPROACH_SIDES) do
            local ax = p.cx + p.fx * e[1] * (geo.hl + ll) + lx * sd
            local ay = p.cy + p.fy * e[1] * (geo.hl + ll) + ly * sd
            local dx, dy = ax - from.x, ay - from.y
            local n = math.sqrt(dx * dx + dy * dy)
            if n > 1 then
                local hx, hy = dx / n, dy / n
                if bodyFree(w, boxSquares(ax, ay, hx, hy, geo.hl + M.PAD, geo.hw + M.PAD)) then
                    out[#out + 1] = { cx = ax, cy = ay, fx = hx, fy = hy, turnBack = e[2],
                        score = n * 0.1 + (ei - 1) * 5 + math.abs(sd) * 0.2 + (sd == 0 and 1 or 0) }
                end
            end
        end
    end
    table.sort(out, function(a, b) return a.score < b.score end)
    while #out > M.MAX_APPROACHES do table.remove(out) end
    return out
end

-- ---------------------------------------------------------------- from where the car really stands
-- Squares within arm's reach of the cap that are free now: not under any car, not his square. Nearest to the cap first.
function M.standSquares(s, veh, ax, ay, reach, pump)
    local c = cell()
    if c == nil or ax == nil then return nil end
    reach = math.min(reach or M.REACH, M.REACH + 0.05)
    local cars, list = {}, call(c, "getVehicles")
    local n = num((call(list, "size"))) or 0
    for i = 0, n - 1 do
        local v = call(list, "get", i)
        local vx, vy = num((call(v, "getX"))), num((call(v, "getY")))
        if vx and vy and (vx - ax) ^ 2 + (vy - ay) ^ 2 < 400 then cars[#cars + 1] = v end
    end
    local p = player()
    local pk = nil
    if p ~= nil and call(p, "getVehicle") == nil then pk = key(num((call(p, "getX"))) or 0, num((call(p, "getY"))) or 0) end
    local sx, sy = num((call(s, "getX"))) or ax, num((call(s, "getY"))) or ay
    local out = {}
    for y = math.floor(ay) - 2, math.floor(ay) + 2 do
        for x = math.floor(ax) - 2, math.floor(ax) + 2 do
            local d = math.sqrt((x + 0.5 - ax) ^ 2 + (y + 0.5 - ay) ^ 2)
            if d <= reach and key(x, y) ~= pk then
                local sq = call(c, "getGridSquare", x, y, 0)
                local ok = sq ~= nil and freeSq(sq)
                for _, v in ipairs(cars) do if ok and call(v, "isIntersectingSquare", x, y, 0) == true then ok = false end end
                if ok then out[#out + 1] = { x = x, y = y, toWork = d, toHer = (x + 0.5 - sx) ^ 2 + (y + 0.5 - sy) ^ 2 } end
            end
        end
    end
    if pump == nil and veh ~= nil then
        local Menu = g("ISVehiclePartMenu")
        if type(Menu) == "table" and type(Menu.getNearbyFuelPump) == "function" then local okP, pp = pcall(Menu.getNearbyFuelPump, veh); if okP then pump = pp end end
    end
    local psq = pump ~= nil and call(pump, "getSquare") or nil
    local px, py = num((call(psq, "getX"))), num((call(psq, "getY")))
    for _, q in ipairs(out) do q.gap = px ~= nil and between(q.x, q.y, px, py, ax, ay) or false end
    table.sort(out, function(a, b)
        if a.gap ~= b.gap then return a.gap end                          -- the free square between the cap and the pump first
        if a.toWork ~= b.toWork then return a.toWork < b.toWork end
        return a.toHer < b.toHer
    end)
    return out
end

local function nearestPump(x, y)
    local P = parts()
    if P == nil or type(P.station) ~= "function" then return nil end
    local ok, st = pcall(P.station, x, y)
    if ok and type(st) == "table" then return st end
    return nil
end

-- true when she can refuel from where the car stands: the game's own pump test, power, a free square by the cap she can walk to
function M.verify(veh, s)
    local geo, why = M.geometry(veh, s)
    if geo == nil then return false, why end
    local Menu = g("ISVehiclePartMenu")
    if type(Menu) ~= "table" or type(Menu.getNearbyFuelPump) ~= "function" then return false, "refuel_unavailable" end
    local okP, pump = pcall(Menu.getNearbyFuelPump, veh)
    if not okP or pump == nil then return false, "cap_far_from_pump", geo end
    local sq = call(pump, "getSquare")
    local P = parts()
    local px, py = num((call(sq, "getX"))), num((call(sq, "getY")))
    if px == nil then return false, "cap_far_from_pump", geo end
    if P ~= nil and type(P.hasPower) == "function" and P.hasPower(px, py) ~= true then return false, "no_power_here", geo end
    local all = M.standSquares(s, veh, geo.capX, geo.capY, M.REACH, pump)
    local stand = {}
    for _, q in ipairs(all or {}) do if q.gap then stand[#stand + 1] = q end end
    if #stand == 0 then return false, "no_free_square_between", geo end              -- Jamal's rule: the square between cap and pump, free
    local w = M.world(px, py, false)
    if w ~= nil then
        M.live(w, veh, true)
        local body = w.own
        for _, d in ipairs(doorSquares(geo, geo.cx, geo.cy, geo.hx, geo.hy)) do
            for _, q in ipairs(stand) do if walkable(w, d.x, d.y, q.x, q.y, body, 600) then return true, "ok", geo, stand end end
        end
        return false, "no_walk_to_cap", geo
    end
    return true, "ok", geo, stand
end

-- ---------------------------------------------------------------- the park order
local function stopNav() local stop = fn("solNavStop"); if stop then pcall(stop) end end
local function finish(j, ok, reason, detail)
    j.over, j.ok, j.reason = true, ok, reason
    if j.following then stopNav() end
    if ok then log("parked: " .. tostring(detail or "")) else log("park order ends: " .. reason .. (detail and (" (" .. detail .. ")") or "")); failNote(reason, detail) end
end
-- one plan to the job's target (an approach point or the pose itself), from where the car stands now
local function planTarget(j)
    local t, plan = j.target, fn("solNavPlan")
    if plan == nil or t == nil then return false end
    if t.turnBack then local tb = fn("solNavMayTurnBack"); if tb then pcall(tb) end end           -- backing in through the lane ahead
    local okP, started = pcall(plan, j.veh, j.geo.cx, j.geo.cy, j.geo.hx, j.geo.hy, t.cx, t.cy, t.fx, t.fy, j.geo.wheelbase, j.geo.kmax)
    return okP and started == true
end
-- s95b: the next target for this pose: the next approach point, else the pose itself straight from here
local function aim(j)
    local p = j.pose
    if j.stage ~= "pose" then
        j.li = (j.li or 0) + 1
        local a = j.legs and j.legs[j.li]
        if a ~= nil then
            j.stage, j.target, j.via = "approach", a, a
            log(string.format("pose %d: first to %.1f,%.1f facing %.2f,%.2f (approach %d of %d)", j.i, a.cx, a.cy, a.fx, a.fy, j.li, #j.legs))
            return
        end
    end
    j.stage, j.target = "pose", { cx = p.cx, cy = p.cy, fx = p.fx, fy = p.fy, turnBack = j.via ~= nil and j.via.turnBack and j.reached == true }
end
local function planNow(j)
    j.legAt, j.following = nowMs(), false
    j.planned = planTarget(j)
end
local function startPose(j)
    j.i = j.i + 1
    local p = j.poses[j.i]
    if p == nil or j.i > M.MAX_POSES then
        if j.drove then return finish(j, false, "survey_no_stand", "no pose left after " .. j.reparks .. " re-parks") end
        return finish(j, false, j.planFails > 0 and "survey_drive_failed" or "survey_no_pose", j.planFails .. " plans failed")
    end
    j.pose, j.poseAt, j.following, j.planned = p, nowMs(), false, false
    M.tried[p.key] = true
    if call(j.veh, "isEngineRunning") ~= true and type(U.solEngine) == "function" then pcall(U.solEngine, "on") end
    log(string.format("pose %d: pump %d,%d, car centre %.1f,%.1f facing %d,%d, she stands at %d,%d%s", j.i, p.px, p.py, p.cx, p.cy, p.fx, p.fy, p.sx, p.sy,
        p.through and ", lane open both ends" or ""))
    j.stage, j.li, j.via, j.reached = nil, 0, nil, false
    j.legs = j.w ~= nil and M.approaches(j.w, j.geo, p, { x = j.geo.cx, y = j.geo.cy }) or {}
    aim(j)
    planNow(j)
    if not j.planned then log("pose " .. j.i .. ": planner busy, next frame") end
end
-- s95b: a plan that failed or never started: the next approach point, then the pose straight, then the next pose
local function legFailed(j)
    if j.stage == "approach" then aim(j); return planNow(j) end
    j.planFails = j.planFails + 1
    return startPose(j)
end
local function refreshGeo(j)
    local geo = M.geometry(j.veh, j.s)
    if geo then j.geo = geo end
end
function M.step(j)
    if j == nil or j.over then return end
    local t = nowMs()
    if t - j.at > M.JOB_MS then return finish(j, false, "survey_drive_failed", "out of time") end
    local beat = fn("solNavBeat")
    if beat then pcall(beat) end
    if not j.planned then
        j.planned = planTarget(j)
        if not j.planned and t - (j.legAt or j.poseAt) > 5000 then return legFailed(j) end
        return
    end
    local stateF = fn("solNavState")
    local okS, st = false, nil
    if stateF then okS, st = pcall(stateF) end
    if not okS or type(st) ~= "string" then return finish(j, false, "park_unavailable", "no planner state") end
    if st == "ready" then
        local follow = fn("solNavFollow")
        local okF, on = false, false
        if follow then okF, on = pcall(follow) end
        if okF and on == true then j.following, j.drove = true, true else return legFailed(j) end
        return
    end
    if string.sub(st, 1, 7) == "failed:" then
        log("pose " .. j.i .. (j.stage == "approach" and " approach " .. j.li or "") .. ": " .. st)
        if j.following then j.say = "blocked" end
        stopNav(); refreshGeo(j)
        return legFailed(j)
    end
    if st == "done" and j.following and j.stage == "approach" then           -- s95b: at the approach point; now the short turn into the pose
        stopNav(); refreshGeo(j)
        j.reached = true
        log("pose " .. j.i .. ": at the approach point, now into the pose")
        j.stage = "pose"
        aim(j)
        j.poseAt = nowMs()
        return planNow(j)
    end
    if st == "done" and j.following then
        stopNav()
        j.following = false
        local ok, why = M.verify(j.veh, j.s)
        if ok then return finish(j, true, "parked", "pose " .. j.i) end
        j.reparks = j.reparks + 1
        log("after the stop: " .. tostring(why))
        if j.reparks > M.MAX_REPARKS then return finish(j, false, "survey_no_stand", why) end
        refreshGeo(j)
        local nextP = j.poses[j.i + 1]
        j.say = (nextP and (nextP.px ~= j.pose.px or nextP.py ~= j.pose.py)) and "other_pump" or "other_side"
        return startPose(j)
    end
    if t - j.poseAt > M.DRIVE_MS then
        log("pose " .. j.i .. ": no stop in " .. M.DRIVE_MS / 1000 .. " s")
        stopNav(); refreshGeo(j)
        j.say = "blocked"
        return startPose(j)
    end
end

function M.startPark(s, veh)
    if fn("solNavPlan") == nil or fn("solNavState") == nil or fn("solNavFollow") == nil then return false, "park_unavailable" end
    local geo, why = M.geometry(veh, s)
    if geo == nil then return false, why end
    local st = nearestPump(geo.cx, geo.cy)
    if st == nil then return false, "no_station_known" end
    local w = M.world(st.x, st.y, false)
    if w == nil then return false, "park_unavailable" end
    M.live(w, veh, false)
    local any = false
    for _, p in ipairs(w.pumps) do if (p.fuel or 0) > 0 and p.power then any = true end end
    if not any then failNote("survey_no_pump", #w.pumps .. " pumps"); return false, "survey_no_pump" end
    if M.triedFor ~= key(st.x, st.y) or nowMs() - (M.triedAt or 0) > 600000 then M.tried = {} end         -- one errand at one station keeps what it tried
    M.triedFor, M.triedAt = key(st.x, st.y), nowMs()
    local poses, n = M.poses(w, geo, { x = geo.cx, y = geo.cy, hx = geo.hx, hy = geo.hy }, M.tried)
    log(string.format("%d poses beside %d pumps (left out: %d out of the hose's reach, %d cap not facing the pump across a free square, %d body on something, %d no lane in or out, %d no walk from her door)",
        #poses, n.pumps, n.reach, n.gap, n.body, n.lane, n.door))
    if #poses == 0 then
        if w.cached then M.world(st.x, st.y, true) end                                                       -- read again next time: the station may have changed
        failNote("survey_no_pose", string.format("reach %d gap %d body %d lane %d door %d", n.reach, n.gap, n.body, n.lane, n.door))
        return false, "survey_no_pose"
    end
    M.job = { s = s, veh = veh, geo = geo, w = w, poses = poses, i = 0, at = nowMs(), reparks = 0, planFails = 0 }
    startPose(M.job)
    if M.job.over then local r = M.job.reason; M.job = nil; return false, r end
    return true, "parking"
end

function M.parkStatus()
    local j = M.job
    if j == nil then return false, "no_job" end
    M.step(j)
    if j.over then
        M.job = nil
        if j.ok then return true, "parked" end
        return false, j.reason
    end
    if j.say then local say = j.say; j.say = nil; return true, "parking:" .. say end
    return true, "parking"
end

function M.cancel()
    if M.job ~= nil and M.job.following then stopNav() end
    M.job = nil
end

-- sol_fuel car_near / park / park_status while the switch is on
function M.handle(opt, s)
    local P = parts()
    local veh = P and type(P.theCar) == "function" and P.theCar(s) or nil
    if opt == "park_status" then return M.parkStatus() end
    if veh == nil then return false, "no_car" end
    if opt == "car_near" then
        local ok, why = M.verify(veh, s)
        log("from where the car stands: " .. tostring(why))
        if ok then return true, "near" end
        if why == "survey_no_cap" or why == "no_gas_tank" or why == "refuel_unavailable" then return false, why end
        return false, "pump_too_far"
    end
    if opt == "park" then
        M.cancel()
        local okS, ok, why = pcall(M.startPark, s, veh)
        if not okS then log("park error: " .. tostring(ok)); return false, "park_unavailable" end
        return ok, why
    end
    return false, "unknown_option"
end

-- SolMoveCheck asks: is this walk her walk to the fuel cap (not a walk to him)?
function U.solFuelWalking()
    if not M.on() then return false end
    local P = parts()
    return P ~= nil and type(P.walking) == "function" and P.walking() == true
end

local function tick() if M.job ~= nil and not M.job.over then pcall(M.step, M.job) end end
if Events and Events.OnTick and not loadedBefore then Events.OnTick.Add(tick) end      -- once: a reloaded copy is driven by the first tick
return M

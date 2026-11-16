-- SolFar.lua - Sol when she is out in an unloaded part of the world.
--   Her body does not exist there: the game only keeps her saved record, and it waits for the player to come close.
--   Woken, she answers. Called on foot, a square is searched for outward from the player, over what is already loaded: one she can walk to him
--   from, outdoors, safe to appear on, away from zombies and off his screen. Her record moves there, the normal restore brings her body back
--   out of his sight, and she walks to him. No chunk is loaded for any of this.
--   She takes five real minutes to get there on foot, three to her car; the pause button stops that clock.
--   Called by car, this covers her car being loaded near him: she appears out of his sight by the car; the Mind then has her drive to him.
--   Her car far away: the Mind picks a road spot just outside what is loaded around him, the Java side moves the car's saved row there (one
--   transaction, same id), her record goes beside it, and both appear the normal way when he gets close enough for that chunk to load.
--   Action sol_far, option: status / wake / come / come_car / car_where / car_far:<x>,<y>,<tiles> / poll.
--   Answers: here | far:<tiles> | awake:<tiles> | waiting:<seconds> | seeking | placed | no_spot | (false) no_sol / cannot_travel / no_player / car_not_near / no_fuel / car_taken.
require "SolBudget"
SolUI = SolUI or {}
local U = SolUI
local F = {}
local MIN_TILES, MAX_TILES, MARGIN_PX, ZOMBIE_TILES, EXTRA_STEPS = 12, 52, 120, 6, 10
local SEEK_BATCH, MAX_NODES, SPAWN_WAIT_MS, MIND_STALE_MS = 120, 9000, 60000, 20000
local FOOT_WAIT_MS, CAR_WAIT_MS, RETRY_MS, RETRIES, MAX_TICK_MS = 300000, 180000, 15000, 3, 5000
local CAR_NEAR, MIN_FUEL, STORE = 60, 0.5, "Sol_Far"
local FUEL_PER_TILE, MOVE_WAIT_MS = 0.07 / 158.53 * 1.25, 10000                  -- the rate measured on a road, for a car at its reference mass and quality
local moving = nil
local EDGE_WAIT_MS, EDGE_LEFT_TILES = 1800000, 220
local BODY_FLOORS, REGROUP_TRIES = 2, 5
local ALIVE_FILE = "SolMind_Alive.txt"
local DIRS = { "getN", "getS", "getE", "getW" }
local awake, wait, seek, placed, lastResult, expecting = false, nil, nil, nil, nil, 0
local stateAt, stateValue, mindAliveAt, aliveReadAt = 0, nil, 0, 0

local function log(m) print("[SolFar] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function SC() local s = rawget(_G, "SurvivorCompanion"); if type(s) == "table" then return s end return nil end
local function player() local f = rawget(_G, "getSpecificPlayer"); return f and f(0) or nil end
local function liveActor() return type(U.solActor) == "function" and U.solActor() or nil end
-- A companion left behind stays registered after her square unloads (2026-11-09 10:38 to 10:44: living=1, no body). She is "here" only with a square under her.
local AWAY_MS, awaySince = 2000, nil
local function bodyGone(a)
    local f = a and a.getCurrentSquare
    if type(f) ~= "function" then return false end
    local ok, sq = pcall(f, a)
    if not ok or sq ~= nil then awaySince = nil; return false end
    local t = nowMs()
    if awaySince == nil or t < awaySince then awaySince = t end
    return t - awaySince >= AWAY_MS
end
local function actor()
    local a = liveActor()
    if a ~= nil and bodyGone(a) then return nil end
    return a
end
local function GU() local sc = SC(); local g = sc and sc.GameplayUtil or nil; if type(g) == "table" then return g end return nil end
local function persistence() local sc = SC(); local p = sc and sc.Persistence or nil; if type(p) == "table" then return p end return nil end
local function call(o, name)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, v = pcall(f, o)
    if ok then return v end
    return nil
end
local function xyOf(o)
    if o == nil then return nil end
    local x, y = tonumber(call(o, "getX")), tonumber(call(o, "getY"))
    if x ~= nil and y ~= nil then return x, y end
    return nil
end
local function dist(ax, ay, bx, by) return math.sqrt((ax - bx) ^ 2 + (ay - by) ^ 2) end

-- her and nobody else: other people's saved records (faction members) are not on this list
local function pendingCount()
    local P = persistence()
    if P == nil or type(P.pendingIds) ~= "function" then return 0 end
    local ok, ids = pcall(P.pendingIds)
    return ok and type(ids) == "table" and #ids or 0
end
-- her saved record, when she is saved and not sitting in a car or being restored
local function record()
    local L = liveActor()
    if L ~= nil and actor() == nil then                                          -- registered, no body: the same trip as a saved record
        local x, y = tonumber(call(L, "getX")), tonumber(call(L, "getY"))
        if x ~= nil and y ~= nil then return { id = "live", x = x, y = y, live = L } end
    end
    local P = persistence()
    if P == nil or type(P.pendingIds) ~= "function" or type(P.pendingBootstrap) ~= "function" then return nil end
    local ok, ids = pcall(P.pendingIds)
    if not ok or type(ids) ~= "table" or #ids ~= 1 then return nil end
    local okB, b = pcall(P.pendingBootstrap, ids[1])
    if okB and type(b) == "table" then return b end
    return nil
end

function U.solFarState()
    if actor() ~= nil then return nil end
    if wait ~= nil or seek ~= nil or placed ~= nil or moving ~= nil then return "coming" end
    local t = nowMs()
    if t - stateAt >= 500 or t < stateAt then
        stateAt, stateValue = t, (record() ~= nil or pendingCount() > 0) and "far" or nil
    end
    if stateValue == "far" and awake then return "awake" end
    return stateValue
end

-- the dot: on = near or awake, far = dormant out there, off = no Sol, or Sol's systems are not up
-- her position is in a part of the world that is not loaded: the game's own catch-up must not bring her to him at once, on screen
function U.solFarUnloaded(a)
    if a == nil or a ~= liveActor() then return false end
    local x, y, z = tonumber(call(a, "getX")), tonumber(call(a, "getY")), tonumber(call(a, "getZ"))
    local gu = GU()
    if x == nil or y == nil or gu == nil or type(gu.gridSquare) ~= "function" then return false end
    local ok, sq = pcall(gu.gridSquare, x, y, z or 0)
    return ok and sq == nil
end
function U.solDotState()
    if nowMs() - mindAliveAt > MIND_STALE_MS then return "off" end
    if actor() ~= nil then return "on" end
    local state = U.solFarState()
    if state == "coming" or state == "awake" then return "on" end
    if state == "far" then return "far" end
    return "off"
end

-- ---------------------------------------------------------------- her car
local function store()
    if type(ModData) ~= "table" or type(ModData.getOrCreate) ~= "function" then return nil end
    local ok, d = pcall(ModData.getOrCreate, STORE)
    if ok and type(d) == "table" then return d end
    return nil
end
local sc_loadedCar, fuel_of
local function rememberCar()
    local gps = U.gps
    local car = type(gps) == "table" and gps.lastDriveCar or nil
    local id = car and tonumber(call(car, "getSqlId")) or nil
    local d = store()
    if d ~= nil and id ~= nil and id >= 0 then d.carSqlId = id end
    -- what is known about it stays known once it is out of the loaded world
    local loaded = d and d.carSqlId and sc_loadedCar() or nil
    if loaded == nil then return end
    local x, y = xyOf(loaded)
    local script = call(loaded, "getScript")
    d.carX, d.carY, d.carZ = x, y, tonumber(call(loaded, "getZ")) or 0
    d.carFuel = fuel_of(loaded)
    d.carMass = tonumber(call(script, "getMass")) or d.carMass
    d.carQuality = tonumber(call(loaded, "getEngineQuality")) or d.carQuality
    d.carTowing = call(loaded, "getVehicleTowing") ~= nil or call(loaded, "getVehicleTowedBy") ~= nil
end
local function fuelCost(d, tiles)
    local mass, quality = tonumber(d.carMass) or 1000, tonumber(d.carQuality) or 100
    return tiles * FUEL_PER_TILE * (math.abs(1000 - mass) / 300 + 1) * ((100 - quality) / 200 + 1)   -- the same terms as the game's own Vehicles.Update.GasTank
end
local function loadedCar()
    local d, sc = store(), SC()
    local id = d and tonumber(d.carSqlId) or nil
    local service = sc and sc.Vehicle or nil
    if id == nil or type(service) ~= "table" or type(service.loadedBySqlId) ~= "function" then return nil end
    local ok, car = pcall(service.loadedBySqlId, id)
    if ok then return car end
    return nil
end
local function fuelIn(car)
    local tank = nil
    local okT, part = pcall(car.getPartById, car, "GasTank")
    if okT then tank = part end
    return tonumber(call(tank, "getContainerContentAmount")) or 0
end
sc_loadedCar, fuel_of = loadedCar, fuelIn
-- her car, when she can really use it where it is
local function usableCar()
    local car = loadedCar()
    if car == nil then return nil, "car_not_near" end
    local px, py = xyOf(player())
    local cx, cy = xyOf(car)
    if px == nil or cx == nil or dist(px, py, cx, cy) > CAR_NEAR then return nil, "car_not_near" end
    if call(player(), "getVehicle") == car then return nil, "car_taken" end
    if fuelIn(car) < MIN_FUEL then return nil, "no_fuel" end
    return car
end

-- ---------------------------------------------------------------- where she can appear
local function offScreen(x, y)
    local tx, ty = rawget(_G, "isoToScreenX"), rawget(_G, "isoToScreenY")
    local left, top, width, height = rawget(_G, "getPlayerScreenLeft"), rawget(_G, "getPlayerScreenTop"), rawget(_G, "getPlayerScreenWidth"), rawget(_G, "getPlayerScreenHeight")
    if type(tx) ~= "function" or type(ty) ~= "function" or type(left) ~= "function" or type(top) ~= "function" or type(width) ~= "function" or type(height) ~= "function" then return false end
    local l, t, w, h = left(0), top(0), width(0), height(0)
    local function outside(sx, sy) return sx < l - MARGIN_PX or sx > l + w + MARGIN_PX or sy < t - MARGIN_PX or sy > t + h + MARGIN_PX end
    return outside(tx(0, x + 0.5, y + 0.5, 0), ty(0, x + 0.5, y + 0.5, 0))
       and outside(tx(0, x + 0.5, y + 0.5, BODY_FLOORS), ty(0, x + 0.5, y + 0.5, BODY_FLOORS))   -- her head too, at any zoom
end

local function zombieNear(s, x, y)
    for i = 1, #s.zombies, 2 do
        if math.abs(s.zombies[i] - x) <= ZOMBIE_TILES and math.abs(s.zombies[i + 1] - y) <= ZOMBIE_TILES then return true end
    end
    return false
end

local function readZombies(px, py)
    local out = {}
    local cellOf = rawget(_G, "getCell")
    local list = type(cellOf) == "function" and call(cellOf(), "getZombieList") or nil
    local n = list and tonumber(call(list, "size")) or 0
    for i = 0, n - 1 do
        local okZ, z = pcall(list.get, list, i)
        local x, y = xyOf(okZ and z or nil)
        if x ~= nil and dist(x, y, px, py) <= MAX_TILES + ZOMBIE_TILES then out[#out + 1] = x; out[#out + 1] = y end
    end
    return out
end

local function consider(s, sq, x, y, steps)
    if s.mode == "car" and dist(x, y, s.ox, s.oy) > CAR_NEAR then return end
    if dist(x, y, s.px, s.py) < MIN_TILES or not sq:isOutside() or not offScreen(x, y) or zombieNear(s, x, y) then return end
    local gu = GU()
    if gu == nil or type(gu.isSafeSpawnSquare) ~= "function" then return end
    local okS, safe = pcall(gu.isSafeSpawnSquare, sq)
    if not okS or safe ~= true then return end
    local towardHome = ((x - s.px) * s.homeX + (y - s.py) * s.homeY) / math.max(1, dist(x, y, s.px, s.py))   -- she comes from that side
    if s.mode == "car" then towardHome = -dist(x, y, s.ox, s.oy) end                                        -- as near her car as he cannot see
    if s.stopAfter == nil then s.stopAfter = steps + EXTRA_STEPS end
    if s.score == nil or towardHome > s.score then s.score, s.x, s.y = towardHome, x, y end
end

local function canStep(sq, nb)
    if not nb:TreatAsSolidFloor() or nb:isSolidTrans() or nb:isSolid() then return false end
    if not sq:isBlockedTo(nb) then return true end
    local door = sq:isDoorTo(nb) and sq:getDoorTo(nb) or nil                     -- a shut door she can open is a way through; a locked or boarded one is not
    return door ~= nil and call(door, "isLocked") ~= true and call(door, "isLockedByKey") ~= true and call(door, "isBarricaded") ~= true
end

-- a slice of the search outward from him: everything it reaches is somewhere she can walk to him from
local function seekSlice(s)
    for _ = 1, SEEK_BATCH do
        local node = s.queue[s.head]
        if node == nil then return true end
        s.queue[s.head] = nil
        s.head = s.head + 1
        local sq, x, y, steps = node[1], node[2], node[3], node[4]
        if s.stopAfter ~= nil and steps > s.stopAfter then return true end
        consider(s, sq, x, y, steps)
        for d = 1, 4 do
            local nb = sq[DIRS[d]](sq)
            if nb ~= nil then
                local nx, ny = nb:getX(), nb:getY()
                local key = nx * 100000 + ny
                if not s.seen[key] and dist(nx, ny, s.ox, s.oy) <= MAX_TILES and canStep(sq, nb) then    -- a wall on this side does not close the square from the other
                    s.seen[key] = true
                    s.count = s.count + 1
                    if s.count >= MAX_NODES then return true end
                    s.queue[s.count + 1] = { nb, nx, ny, steps + 1 }
                end
            end
        end
    end
    return false
end

-- puts her on the square that was found: a saved record is moved, a registered body is recovered there
local function moveBody(id, x, y)
    if id == "live" then
        local L, sc, gu = liveActor(), SC(), GU()
        if L == nil or sc == nil or gu == nil or type(sc.Actor) ~= "table" or type(sc.Actor.recover) ~= "function" or type(gu.gridSquare) ~= "function" then return false end
        local ok, sq = pcall(gu.gridSquare, x, y, 0)
        if not ok or sq == nil then return false end
        local okR, done = pcall(sc.Actor.recover, L, sq)
        return okR and done == true
    end
    local P = persistence()
    if P == nil or type(P.pendingRelocate) ~= "function" then return false end
    local ok, moved = pcall(P.pendingRelocate, id, x, y, 0)
    return ok and moved == true
end
local function finishSeek(s)
    seek = nil
    if s.x == nil then
        local tries = (s.tries or 0) + 1
        if tries <= RETRIES then wait = { left = RETRY_MS, last = nowMs(), tries = tries, mode = s.mode }; return end         -- he may have zoomed out, or be about to move
        log("no place to appear near him"); lastResult = "no_spot"
        return
    end
    if moveBody(s.id, s.x, s.y) then
        placed = { at = nowMs() }
        lastResult, expecting = "placed", (s.mode == "car") and 0 or REGROUP_TRIES             -- by car, the drive to him comes from the Mind
        log("appearing at " .. s.x .. "," .. s.y)
    else
        log("could not move her record")
        lastResult = "no_spot"
    end
end

local function seekTask()
    local s = seek
    if s == nil then return end
    if actor() ~= nil then seek = nil; return end
    local ok, finished = pcall(seekSlice, s)
    if not ok then log("search failed: " .. tostring(finished)); finished = true end
    if finished then finishSeek(s) end
end

local function startSeek(mode)
    local px, py = xyOf(player())
    if px == nil then return false, "no_player" end
    local b = record()
    if b == nil then return false, pendingCount() > 0 and "cannot_travel" or "no_sol" end
    local ox, oy = px, py
    if mode == "car" then
        local car, why = usableCar()
        if car == nil then return false, why end
        ox, oy = xyOf(car)
    end
    local gu = GU()
    local okS, start = false, nil
    if gu ~= nil and type(gu.gridSquare) == "function" then okS, start = pcall(gu.gridSquare, ox, oy, 0) end
    if not okS or start == nil then return false, "no_player" end
    local homeD = math.max(1, dist(px, py, b.x, b.y))
    local sx, sy = math.floor(ox), math.floor(oy)
    local queue = { { start, sx, sy, 0 } }
    seek = { id = b.id, mode = mode, ox = ox, oy = oy, px = px, py = py, homeX = (b.x - px) / homeD, homeY = (b.y - py) / homeD, queue = queue, head = 1, count = 0,
             seen = { [sx * 100000 + sy] = true }, zombies = readZombies(px, py) }
    awake, lastResult = true, nil
    return true, "seeking"
end

-- ---------------------------------------------------------------- the slow clock
local function waitSeconds() return math.max(1, math.ceil(wait.left / 1000)) end
function U.solFarEta() if wait == nil then return nil end return waitSeconds() end

local function paused()
    local f = rawget(_G, "isGamePaused")
    if type(f) ~= "function" then return false end
    local ok, v = pcall(f)
    return ok and v == true
end

-- what the Mind needs to choose where the car goes
local function carWhere()
    local d = store()
    if d == nil or tonumber(d.carSqlId) == nil or tonumber(d.carX) == nil then return false, "no_car" end
    if d.carTowing == true then return false, "towing" end
    if (tonumber(d.carZ) or 0) >= 1 then return false, "no_route" end                 -- parked up a level
    local ringFn, px, py = rawget(_G, "solCarMoveRing"), xyOf(player())
    if type(ringFn) ~= "function" or px == nil then return false, "no_java" end
    -- near what is loaded a chunk may be on its way in or out, and its row is not hers to change
    local chunks = math.max(math.abs(math.floor(d.carX / 8) - math.floor(px / 8)), math.abs(math.floor(d.carY / 8) - math.floor(py / 8)))
    if chunks <= ringFn() + 2 then return false, "car_too_close" end
    return true, "car:" .. math.floor(d.carX) .. "," .. math.floor(d.carY) .. "," .. math.floor(px) .. "," .. math.floor(py) .. "," .. math.floor(ringFn())
end

local function startFarCar(text)
    local x, y, tiles = string.match(text, "^(%-?[%d%.]+),(%-?[%d%.]+),([%d%.]+)$")
    x, y, tiles = tonumber(x), tonumber(y), tonumber(tiles)
    if x == nil or y == nil or tiles == nil then return false, "bad_spot" end
    if xyOf(player()) == nil then return false, "no_player" end
    if record() == nil then return false, pendingCount() > 0 and "cannot_travel" or "no_sol" end
    local d = store()
    if d == nil or tonumber(d.carSqlId) == nil then return false, "no_car" end
    if d.carTowing == true then return false, "towing" end
    local cost = fuelCost(d, tiles)
    if (tonumber(d.carFuel) or 0) < cost + MIN_FUEL then return false, "no_fuel" end
    wait, awake, lastResult = { left = CAR_WAIT_MS, last = nowMs(), tries = 0, mode = "car_far", x = x, y = y, cost = cost }, true, nil
    log("her car from far, " .. math.floor(tiles) .. " tiles, fuel " .. cost)
    return true, "waiting:" .. math.ceil(CAR_WAIT_MS / 1000)
end

local function moveTick(t)
    local stateFn = rawget(_G, "solCarMoveState")
    local st = type(stateFn) == "function" and tostring(stateFn()) or "no_java"
    if st == "queued" then
        if t - moving.at > MOVE_WAIT_MS then
            local cancel = rawget(_G, "solCarMoveCancel")
            if type(cancel) == "function" then pcall(cancel) end
            lastResult, moving = "move_timeout", nil
        end
        return
    end
    local m = moving
    moving = nil
    if st ~= "ok" then lastResult = st; log("car not moved: " .. st); return end
    local d = store()
    if d ~= nil then d.carX, d.carY, d.fuelDue = m.x, m.y, m.cost end              -- taken from the tank when the car is really there
    local b = record()
    local P = persistence()
    local ok, moved = false, false
    if b ~= nil and P ~= nil and type(P.pendingRelocate) == "function" then ok, moved = pcall(P.pendingRelocate, b.id, math.floor(m.x) + 3, math.floor(m.y), 0) end
    if ok and moved == true then
        placed, lastResult, expecting = { at = t, forever = true, x = m.x, y = m.y }, "placed", 0
    else
        lastResult = "record_failed"
    end
end

local function settleFuel()
    local d = store()
    local due = d and tonumber(d.fuelDue) or nil
    if due == nil then return end
    local car = loadedCar()
    if car == nil then return end
    local okT, tank = pcall(car.getPartById, car, "GasTank")
    local cur = okT and tonumber(call(tank, "getContainerContentAmount")) or nil
    if cur == nil then return end
    d.fuelDue = nil
    pcall(tank.setContainerContentAmount, tank, math.max(0, cur - due))
    log("fuel for the trip taken: " .. due)
end

local function startWait(mode)
    if xyOf(player()) == nil then return false, "no_player" end
    if record() == nil then return false, pendingCount() > 0 and "cannot_travel" or "no_sol" end
    local ms = FOOT_WAIT_MS
    if mode == "car" then
        local car, why = usableCar()
        if car == nil then return false, why end
        ms = CAR_WAIT_MS
    end
    wait, awake, lastResult = { left = ms, last = nowMs(), tries = 0, mode = mode }, true, nil
    log("on her way, " .. (ms / 1000) .. " s")
    return true, "waiting:" .. waitSeconds()
end

local function waitTick(t)
    local spent = math.min(MAX_TICK_MS, math.max(0, t - wait.last))
    wait.last = t
    if not paused() then wait.left = wait.left - spent end
    if wait.left > 0 then return end
    local tries, mode = wait.tries, wait.mode
    if mode == "car_far" then
        local m = wait
        wait = nil
        local d, req = store(), rawget(_G, "solCarMoveRequest")
        if d == nil or type(req) ~= "function" or loadedCar() ~= nil then lastResult = "loaded"; return end
        local okR, sent = pcall(req, d.carSqlId, m.x, m.y)
        if okR and sent == true then moving = { at = t, x = m.x, y = m.y, cost = m.cost } else lastResult = "move_timeout" end
        return
    end
    wait = nil
    local ok, why = startSeek(mode)
    if ok then seek.tries = tries else lastResult = (mode == "car" and why) or "no_spot" end
end

local function readAlive()
    local ok, r = pcall(getFileReader, ALIVE_FILE, false)
    if not ok or not r then return end
    local line = r:readLine()
    r:close()
    local v = line and string.match(line, "^t=(%d+)") or nil
    if v ~= nil then mindAliveAt = tonumber(v) or mindAliveAt end
end

local function regroup(a)
    local sc = SC()
    if type(sc) ~= "table" or type(sc.Commands) ~= "table" or type(sc.Commands.issue) ~= "function" or type(sc.GameplayUtil) ~= "table" then return false end
    local okId, id = pcall(sc.GameplayUtil.idOf, a)
    if not okId or type(id) ~= "string" or id == "" then return false end
    local ok, result = pcall(sc.Commands.issue, id, "regroup", nil, player())
    return ok and result ~= false
end

local function tick()
    local t = nowMs()
    if t - aliveReadAt >= 5000 or t < aliveReadAt then aliveReadAt = t; pcall(readAlive); pcall(rememberCar) end
    local a = actor()
    if a ~= nil then
        if expecting > 0 then                                                    -- also when her body comes back later than it should
            log("she is here")
            expecting = regroup(a) and 0 or expecting - 1
        end
        awake, wait, seek, placed, moving = false, nil, nil, nil, nil
        pcall(settleFuel)
        return
    end
    if wait ~= nil then waitTick(t) end
    pcall(settleFuel)
    if moving ~= nil then moveTick(t) end
    if placed ~= nil and placed.forever then
        local px, py = xyOf(player())
        if t - placed.at > EDGE_WAIT_MS or (px ~= nil and dist(px, py, placed.x, placed.y) > EDGE_LEFT_TILES) then
            log("he went the other way")
            placed, lastResult = nil, "left_behind"
        end
    end
    if placed ~= nil and not placed.forever and t - placed.at > SPAWN_WAIT_MS then
        log("her body did not come back")
        placed, lastResult = nil, "no_spot"
    end
end

local function tilesAway()
    local b = record()
    local px, py = xyOf(player())
    if b == nil or px == nil then return 0 end
    return math.floor(dist(px, py, b.x, b.y))
end

function U.solFar(option)
    local opt = string.lower(tostring(option or "status"))
    if string.sub(opt, 1, 8) == "car_far:" then
        if actor() ~= nil then return true, "here" end
        if wait ~= nil or seek ~= nil or placed ~= nil or moving ~= nil then return false, "busy" end
        return startFarCar(string.sub(opt, 9))
    end
    if opt == "car_where" then return carWhere() end
    if opt == "come" or opt == "come_car" then
        if actor() ~= nil then return true, "here" end
        if wait ~= nil then return true, "waiting:" .. waitSeconds() end
        if seek ~= nil then return true, "seeking" end
        if placed ~= nil then return true, "placed" end
        return startWait(opt == "come_car" and "car" or "foot")
    end
    if opt == "poll" then
        if actor() ~= nil then return true, "here" end
        if moving ~= nil then return true, "seeking" end
        if wait ~= nil then return true, "waiting:" .. waitSeconds() end
        if seek ~= nil then return true, "seeking" end
        if placed ~= nil then return true, "placed" end
        return true, lastResult or "idle"                                        -- nothing under way (a reload clears it): not a failed trip
    end
    if opt == "wake" then
        if actor() ~= nil then return true, "here" end
        if record() == nil and pendingCount() <= 0 then return false, "no_sol" end
        awake, stateAt = true, 0
        return true, "awake"
    end
    if opt == "status" then
        if actor() ~= nil then return true, "here" end
        if moving ~= nil then return true, "seeking" end
        if wait ~= nil then return true, "waiting:" .. waitSeconds() end
        if seek ~= nil then return true, "seeking" end
        if placed ~= nil then return true, "placed" end
        if record() == nil and pendingCount() <= 0 then return false, "no_sol" end
        return true, (awake and "awake:" or "far:") .. tilesAway()
    end
    return false, "unknown_option"
end

SolBudget.register("far", tick, { everyMs = 1000, priority = 5 })
SolBudget.register("far_seek", seekTask, { everyMs = 0, priority = 5 })
return F

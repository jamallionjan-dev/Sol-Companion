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
    local x, y = tonumber((call(o, "getX"))), tonumber((call(o, "getY")))
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
        local x, y = tonumber((call(L, "getX"))), tonumber((call(L, "getY")))
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
    local x, y, z = tonumber((call(a, "getX"))), tonumber((call(a, "getY"))), tonumber((call(a, "getZ")))
    local gu = GU()
    if x == nil or y == nil or gu == nil or type(gu.gridSquare) ~= "function" then return false end
    local ok, sq = pcall(gu.gridSquare, x, y, z or 0)
    return ok and sq == nil
end
local readAlive        -- set below; the dot calls it while the game is paused
function U.solDotState()
    local A_ = rawget(_G, "SolAuthority")
    if type(A_) == "table" and type(A_.on) == "function" and A_.on("dot_paused_fix") == true then   -- the panel draws while paused; OnTick does not run
        local t = nowMs()
        if t - aliveReadAt >= 5000 or t < aliveReadAt then aliveReadAt = t; pcall(readAlive) end
    end
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
    local id = car and tonumber((call(car, "getSqlId"))) or nil
    local d = store()
    if d ~= nil and id ~= nil and id >= 0 then d.carSqlId = id end
    -- what is known about it stays known once it is out of the loaded world
    local loaded = d and d.carSqlId and sc_loadedCar() or nil
    if loaded == nil then return end
    local x, y = xyOf(loaded)
    local script = call(loaded, "getScript")
    d.carX, d.carY, d.carZ = x, y, tonumber((call(loaded, "getZ"))) or 0
    d.carFuel = fuel_of(loaded)
    d.carMass = tonumber((call(script, "getMass"))) or d.carMass
    d.carQuality = tonumber((call(loaded, "getEngineQuality"))) or d.carQuality
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
    return tonumber((call(tank, "getContainerContentAmount"))) or 0
end
sc_loadedCar, fuel_of = loadedCar, fuelIn
-- ---------------------------------------------------------------- far_car keys: a car she may take must be unlocked and she must be able to start it
--   Start: a key for it in the ignition, a key for it in her own things (her live inventory, else her saved record), a key for it inside it,
--   or hotwired with the wires whole. Unknown counts as no. Her own car is held to the same rule.
local function farCarOn()
    local A = rawget(_G, "SolAuthority")
    if type(A) ~= "table" or type(A.on) ~= "function" then return false end
    local ok, v = pcall(A.on, "far_car")
    return ok and v == true
end
-- a test for "she carries a key with this id"; when her things cannot be read, she has none
local function herKeys()
    local L = liveActor()
    local inv = L and call(L, "getInventory") or nil
    if inv ~= nil then
        return function(k)
            local ok, v = pcall(function() return inv:haveThisKeyId(k) end)        -- 42.22: Key items, keyrings and bags inside
            return ok and v ~= nil and v ~= false
        end
    end
    local P = persistence()
    if P ~= nil and type(P.pendingKeyIds) == "function" and type(P.pendingIds) == "function" then
        local okI, ids = pcall(P.pendingIds)
        if okI and type(ids) == "table" and #ids == 1 then
            local okK, set = pcall(P.pendingKeyIds, ids[1])
            if okK and type(set) == "table" then return function(k) return set[tonumber(k)] == true end end
        end
    end
    return function() return false end
end
-- a loaded car (near him): the same rule, read from the car itself
local function loadedCanGo(car)
    local okD, part = pcall(function() return car:getPartById("DoorFrontLeft") end)
    local door = okD and part ~= nil and call(part, "getDoor") or nil
    if door == nil then return false, "car_lock_unknown" end
    local locked = call(door, "isLocked")
    if locked == nil then return false, "car_lock_unknown" end
    if locked == true then return false, "car_locked" end
    local kid = tonumber((call(car, "getKeyId")))
    if call(car, "isKeysInIgnition") == true then
        local key = call(car, "getCurrentKey")
        if key ~= nil and kid ~= nil and tonumber((call(key, "getKeyId"))) == kid then return true end
    end
    if call(car, "isHotwired") == true and call(car, "isHotwiredBroken") == false then return true end
    if kid == nil or kid < 0 then return false, "car_no_key" end
    if herKeys()(kid) then return true end
    local n = tonumber((call(car, "getPartCount"))) or 0
    for i = 0, n - 1 do
        local okP, p = pcall(function() return car:getPartByIndex(i) end)
        local c = okP and p ~= nil and call(p, "getItemContainer") or nil
        if c ~= nil then
            local okH, h = pcall(function() return c:haveThisKeyId(kid) end)
            if okH and h ~= nil and h ~= false then return true end
        end
    end
    return false, "car_no_key"
end

-- her car, when she can really use it where it is
local function usableCar()
    local car = loadedCar()
    if car == nil then return nil, "car_not_near" end
    local px, py = xyOf(player())
    local cx, cy = xyOf(car)
    if px == nil or cx == nil or dist(px, py, cx, cy) > CAR_NEAR then return nil, "car_not_near" end
    if call(player(), "getVehicle") == car then return nil, "car_taken" end
    if fuelIn(car) < MIN_FUEL then return nil, "no_fuel" end
    if farCarOn() then local okGo, why = loadedCanGo(car); if not okGo then return nil, why end end   -- far_car: unlocked and she can start it
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
    local n = list and tonumber((call(list, "size"))) or 0
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
                                fuel = num(f[6]), engine = num(f[7]), locked = num(f[8]), quality = num(f[9]), keyId = num(f[10]), loaded = f[11] == "1", verdict = f[12], metaVerdict = f[16] }       -- far_meta: f[16] only for a car kept in meta
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
        if c.verdict == "in_meta" then                                           -- far_meta: kept running far away; only the inside arrival brings it
            if c.metaVerdict == nil or type(rawget(_G, "solCarArriveRequest")) ~= "function" then return end
            local m = {}
            for k, v in pairs(c) do m[k] = v end
            m.verdict, m.meta = c.metaVerdict, true
            c = m
        end
        if c.verdict == "locked" or c.verdict == "lock_unknown" then why = "locked_near"; return end
        if (c.verdict == "no_key" or c.verdict == "start_unknown") and not startable(c, hasKey) then why = "no_key_near"; return end
        if not startable(c, hasKey) then return end
        if mine and d.carTowing == true then why = "towing"; return end
        local chunks = math.max(math.abs(math.floor(c.x / 8) - math.floor(px / 8)), math.abs(math.floor(c.y / 8) - math.floor(py / 8)))
        if chunks <= ring + 2 then why = "car_too_close"; return end   -- near what is loaded a chunk may be on its way in or out
        local mass = massOf(c.script) or (mine and tonumber(d.carMass)) or 1000
        local need = fuelCost({ carMass = mass, carQuality = c.quality or 100 }, dist(c.x, c.y, px, py) * ROAD_FACTOR) + MIN_FUEL
        if c.fuel == nil or c.fuel < need then why = "no_fuel_near"; return end
        best = { id = c.id, x = c.x, y = c.y, fuel = c.fuel, mass = mass, quality = c.quality or 100, script = c.script, kind = kindOf(c.script), mine = mine, meta = c.meta == true }
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
    log("car for the trip: " .. tostring(best.id) .. " " .. tostring(best.script) .. (best.mine and " (hers)" or "") .. (best.meta and " (kept in meta)" or ""))
    return true, "car:" .. math.floor(best.x) .. "," .. math.floor(best.y) .. "," .. math.floor(px) .. "," .. math.floor(py) .. "," .. math.floor(ring) .. "," .. tostring(best.kind or "car")
        .. (type(rawget(_G, "solCarArriveRequest")) == "function" and ",in" or "")          -- far_arrival: it can come into the loaded area
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
        local cv = c
        if c.verdict == "in_meta" and c.metaVerdict ~= nil and type(rawget(_G, "solCarArriveRequest")) == "function" then cv = { verdict = c.metaVerdict, keyId = c.keyId } end   -- far_meta
        local v = startable(cv, hasKey) and "ok" or cv.verdict                  -- her own key counts
        parts[#parts + 1] = tostring(c.id) .. "," .. tostring(c.script or "?") .. "," .. math.floor(c.dist + 0.5) .. "," .. (c.fuel and string.format("%.1f", c.fuel) or "?") .. "," .. tostring(v) .. "," .. (c.id == own and "1" or "0")
    end
    return true, "cars:" .. #list .. "|" .. table.concat(parts, ";")
end
local function startPicked(p, x, y, tiles)
    pick = nil
    local cost = fuelCost({ carMass = p.mass, carQuality = p.quality }, tiles)
    if (tonumber(p.fuel) or 0) < cost + MIN_FUEL then return false, p.mine and "no_fuel" or "picked_no_fuel" end
    local ms = kindWait(p.kind)
    wait, awake, lastResult = { left = ms, last = nowMs(), tries = 0, mode = "car_far", x = x, y = y, cost = cost, id = p.id, mass = p.mass, quality = p.quality, kind = p.kind }, true, nil
    log("car " .. tostring(p.id) .. " (" .. tostring(p.kind) .. ") from far, " .. math.floor(tiles) .. " tiles, fuel " .. cost)
    return true, "waiting:" .. math.ceil(ms / 1000)
end

local function startFarCar(text)
    F.inside = string.sub(tostring(text or ""), -3) == ",in"                     -- far_arrival: into the loaded area, out of his view
    if F.inside then text = string.sub(text, 1, -4) end
    local x, y, tiles, heading = string.match(text, "^(%-?[%d%.]+),(%-?[%d%.]+),([%d%.]+),(%-?[%d%.]+)$")       -- far_arrival: the road's heading
    if x == nil then x, y, tiles = string.match(text, "^(%-?[%d%.]+),(%-?[%d%.]+),([%d%.]+)$") end
    F.heading = tonumber(heading)
    x, y, tiles = tonumber(x), tonumber(y), tonumber(tiles)
    if x == nil or y == nil or tiles == nil then return false, "bad_spot" end
    if xyOf(player()) == nil then return false, "no_player" end
    if record() == nil then return false, pendingCount() > 0 and "cannot_travel" or "no_sol" end
    if farCarOn() then if pick ~= nil and nowMs() - pick.at <= PICK_MS then return startPicked(pick, x, y, tiles) end; return false, "pick_expired" end   -- far_car: only a car car_where chose
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
    if d ~= nil and m.id ~= nil then d.carSqlId, d.carTowing, d.carZ, d.carMass, d.carQuality, d.carFuel = m.id, false, 0, m.mass, m.quality, nil end   -- far_car: the car she came in is hers now
    if d ~= nil then d.carX, d.carY, d.fuelDue = m.x, m.y, m.cost end              -- taken from the tank when the car is really there
    local b = record()
    local P = persistence()
    local ok, moved, why = false, false, nil
    local heading = F.heading
    if b ~= nil and b.id == "live" then                -- far_arrival: registered with no body: her body comes back at the wheel when the car loads
        placed, lastResult, expecting = { at = t, forever = true, x = m.x, y = m.y, car = true, heading = heading }, "placed", 0
        log("car moved to " .. math.floor(m.x) .. "," .. math.floor(m.y) .. "; she gets in when it loads")
        return
    end
    if b ~= nil and P ~= nil and type(P.pendingRelocate) == "function" then ok, moved, why = pcall(P.pendingRelocate, b.id, math.floor(m.x) + 2, math.floor(m.y), 0) end
    if ok and moved == true then
        placed, lastResult, expecting = { at = t, forever = true, x = m.x, y = m.y, car = true, heading = heading }, "placed", 0
        log("car moved to " .. math.floor(m.x) .. "," .. math.floor(m.y) .. " with her saved record beside it")
    else
        why = (b == nil and "no_record") or ((not ok) and ("error " .. tostring(moved))) or tostring(why or "refused")
        log("car moved, her record did not (" .. tostring(b and b.id) .. ": " .. why .. "); she comes on foot")       -- the log only
        lastResult = "record_failed"
        local okW = type(F.startWait) == "function" and F.startWait("foot")
        if okW and wait ~= nil then wait.fellBack = true end
    end
end

local function settleFuel()
    local d = store()
    local due = d and tonumber(d.fuelDue) or nil
    if due == nil then return end
    local car = loadedCar()
    if car == nil then return end
    local okT, tank = pcall(car.getPartById, car, "GasTank")
    local cur = okT and tonumber((call(tank, "getContainerContentAmount"))) or nil
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
        ms = farCarOn() and kindWait(kindOf(call(car, "getScriptName"))) or CAR_WAIT_MS
    end
    wait, awake, lastResult = { left = ms, last = nowMs(), tries = 0, mode = mode }, true, nil
    log("on her way, " .. (ms / 1000) .. " s")
    return true, "waiting:" .. waitSeconds()
end
F.startWait = startWait                                                         -- far_arrival: the car path falls back to this

-- far_wait_speed: the game's fast-forward steps (zombie.ui.SpeedControls): 1x, 5x, 20x, 40x
local SPEED_STEPS = { 1, 5, 20, 40 }
local function speedFactor()
    local A = rawget(_G, "SolAuthority")
    if not (type(A) == "table" and type(A.on) == "function" and A.on("far_wait_speed") == true) then return 1 end
    local f = rawget(_G, "getGameSpeed")
    if type(f) ~= "function" then return 1 end
    local ok, step = pcall(f)
    return ok and SPEED_STEPS[tonumber(step) or 1] or 1
end

local function waitTick(t)
    local spent = math.min(MAX_TICK_MS, math.max(0, t - wait.last))
    wait.last = t
    if not paused() then wait.left = wait.left - spent * speedFactor() end
    if wait.left > 0 then return end
    local tries, mode = wait.tries, wait.mode
    if mode == "car_far" then
        local m = wait
        wait = nil
        local d, req = store(), rawget(_G, "solCarMoveRequest")
        if d == nil or type(req) ~= "function" or (m.id == nil and loadedCar() ~= nil) then lastResult = "loaded"; return end
        local follow, whyNot = F.canFollow()                                    -- far_arrival: never the car alone
        if not follow then
            log("car not moved: she could not come with it (" .. tostring(whyNot) .. "); she comes on foot")
            local okW = type(F.startWait) == "function" and F.startWait("foot")
            if okW and wait ~= nil then wait.fellBack = true else lastResult = "record_failed" end
            return
        end
        if F.inside and type(rawget(_G, "solCarArriveRequest")) == "function" then        -- far_arrival: into the loaded area
            F.arriving = { m = m, at = t, id = m.id or tonumber(d.carSqlId), heading = F.heading, kind = m.kind, tries = 0 }
            return
        end
        local okR, sent = pcall(req, m.id or d.carSqlId, m.x, m.y)
        if okR and sent == true then moving = { at = t, x = m.x, y = m.y, cost = m.cost, id = m.id, mass = m.mass, quality = m.quality } else lastResult = "move_timeout" end
        return
    end
    wait = nil
    local ok, why = startSeek(mode)
    if ok then seek.tries = tries else lastResult = (mode == "car" and why) or "no_spot" end
end

readAlive = function()
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

-- far_arrival inside: a square for the car near the Mind's spot, all of it seen live: loaded, out of his view, outdoors, on a street
-- (a helicopter: any open ground with nothing within 2 tiles), no zombie within 12 tiles, no vehicle within 6. Nearest first, 24 tiles at most.
local function freeSq(sq) local ok, v = pcall(function() return sq:isFree(false) end); return not ok or v ~= false end
local function streetFloor(sq)
    local fl = call(sq, "getFloor")
    local spr = fl and call(fl, "getSprite") or nil
    local name = string.lower(tostring(spr and call(spr, "getName") or ""))
    return string.find(name, "street", 1, true) ~= nil or string.find(name, "road", 1, true) ~= nil
end
function F.insideSpot(x0, y0, kind)
    local gu = GU()
    if gu == nil or type(gu.gridSquare) ~= "function" then return nil end
    local zs, vs = {}, {}
    local cellOf = rawget(_G, "getCell")
    local cell = type(cellOf) == "function" and cellOf() or nil
    local zl = cell and call(cell, "getZombieList") or nil
    for i = 0, (zl and tonumber((call(zl, "size"))) or 0) - 1 do
        local okZ, z = pcall(zl.get, zl, i)
        local zx, zy = xyOf(okZ and z or nil)
        if zx ~= nil then zs[#zs + 1] = { zx, zy } end
    end
    local vl = cell and call(cell, "getVehicles") or nil
    for i = 0, (vl and tonumber((call(vl, "size"))) or 0) - 1 do
        local okV, v = pcall(vl.get, vl, i)
        local vx, vy = xyOf(okV and v or nil)
        if vx ~= nil then vs[#vs + 1] = { vx, vy } end
    end
    local function clearOf(list, x, y, r) for _, p in ipairs(list) do if (p[1] - x) ^ 2 + (p[2] - y) ^ 2 < r * r then return false end end return true end
    for r = 0, 24 do
        for dx = -r, r do
            for dy = -r, r do
                if math.max(math.abs(dx), math.abs(dy)) == r then
                    local x, y = math.floor(x0) + dx, math.floor(y0) + dy
                    local okQ, sq = pcall(gu.gridSquare, x, y, 0)
                    if okQ and sq ~= nil and offScreen(x, y) and call(sq, "isOutside") ~= false and clearOf(zs, x, y, 12) and clearOf(vs, x, y, 6) then
                        local good
                        if kind == "heli" then
                            good = true
                            for ex = -2, 2 do for ey = -2, 2 do
                                local okE, e = pcall(gu.gridSquare, x + ex, y + ey, 0)
                                if not okE or e == nil or call(e, "isOutside") == false or not freeSq(e) then good = false end
                            end end
                        else
                            good = streetFloor(sq) and freeSq(sq)
                        end
                        if good then return x, y end
                    end
                end
            end
        end
    end
    return nil
end
local function insideFallback(why)
    F.arriving = nil
    log("car not brought in (" .. tostring(why) .. "); she comes on foot")       -- the log only
    local okW = type(F.startWait) == "function" and F.startWait("foot")
    if okW and wait ~= nil then wait.fellBack = true else lastResult = "record_failed" end
end
function F.arriveTick(t)
    local A = F.arriving
    local stateFn, mainFn, reqFn = rawget(_G, "solCarArriveState"), rawget(_G, "solCarArriveMain"), rawget(_G, "solCarArriveRequest")
    if type(stateFn) ~= "function" or type(mainFn) ~= "function" or type(reqFn) ~= "function" then return insideFallback("no_java") end
    if A.sent == nil then
        local follow, whyNot = F.canFollow()
        if not follow then return insideFallback(whyNot) end
        local x, y = F.insideSpot(A.m.x, A.m.y, A.kind)
        if x == nil then
            A.tries = A.tries + 1
            if A.tries > 20 then return insideFallback("no_clear_spot") end      -- 20 s of looking: a zombie, a car, his view in the way
            return
        end
        local okR, sent = pcall(reqFn, A.id, x + 0.5, y + 0.5)
        if not (okR and sent == true) then
            local st = tostring(stateFn())
            if st == "target_unloaded" and A.tries < 20 then A.tries = A.tries + 1; return end
            return insideFallback(st)
        end
        A.sent, A.x, A.y = t, x + 0.5, y + 0.5
        return
    end
    local st = tostring(stateFn())
    if st == "queued" then
        if t - A.sent > 10000 then local c = rawget(_G, "solCarArriveCancel"); if type(c) == "function" then pcall(c) end; return insideFallback("queue_timeout") end
        return
    end
    if st == "staged" then
        local okM, r = pcall(mainFn)
        st = okM and tostring(r) or "main_error"
    end
    if st == "arrived" or st == "deferred" then
        local d, m = store(), A.m
        if d ~= nil then
            d.carSqlId, d.carTowing, d.carZ, d.carFuel = A.id, false, 0, nil
            if m.mass then d.carMass, d.carQuality = m.mass, m.quality end
            d.carX, d.carY, d.fuelDue = A.x, A.y, m.cost                         -- taken from the tank once (settleFuel)
        end
        local b, P = record(), persistence()
        if b ~= nil and b.id ~= "live" and P ~= nil and type(P.pendingRelocate) == "function" then
            local okP, moved, why = pcall(P.pendingRelocate, b.id, math.floor(A.x) + 2, math.floor(A.y), 0)
            if not (okP and moved == true) then log("her record stays where it was (" .. tostring(okP and why or moved) .. ")") end
        end
        F.arriving = nil
        placed, lastResult, expecting = { at = t, forever = true, x = A.x, y = A.y, car = true, heading = A.heading }, "placed", 0
        log("her car is " .. (st == "arrived" and "here, " or "on its way in, ") .. math.floor(A.x) .. "," .. math.floor(A.y))
        if st == "arrived" then pcall(F.arrive, placed, t) end                  -- the same tick: along the road, her body at the door, the wheel
        return
    end
    return insideFallback(st)
end
-- ---------------------------------------------------------------- far_arrival: the car and she arrive together
-- can her body follow the car? a live registration (Actor.recover) or a saved record persistence will move (the same guards as pendingRelocate)
function F.canFollow()
    local b = record()
    if b == nil then return false, "no_record" end
    if b.id == "live" then return true end
    local P = persistence()
    if P == nil or type(P.pendingBootstrap) ~= "function" then return false, "no_persistence" end
    local ok, boot = pcall(P.pendingBootstrap, b.id)
    if ok and type(boot) == "table" then return true end
    return false, "record_not_movable"
end
local function carHeadingOf(car)
    local Vec = rawget(_G, "Vector3f")
    if Vec == nil then return nil end
    local okF, f = pcall(function() return car:getForwardVector(Vec.new()) end)
    if not okF or f == nil then return nil end
    local okX, x = pcall(function() return f:x() end)
    local okZ, z = pcall(function() return f:z() end)
    x, z = okX and tonumber(x) or nil, okZ and tonumber(z) or nil
    if x == nil or z == nil then return nil end
    local l = math.sqrt(x * x + z * z)
    if l < 0.001 then return nil end
    return x / l, z / l
end
-- turn the car along the road (degrees, world x/y): setAngles, then the forward vector says whether it took (the sign is checked, not assumed)
function F.align(car, deg)
    if deg == nil then return true end
    local hx, hy = math.cos(math.rad(deg)), math.sin(math.rad(deg))
    local cx, cz = carHeadingOf(car)
    if cx == nil then return false end
    if cx * hx + cz * hy > 0.985 then return true end
    local ax = tonumber((call(car, "getAngleX"))) or 0
    local ay = tonumber((call(car, "getAngleY"))) or 0
    local az = tonumber((call(car, "getAngleZ"))) or 0
    local turn = math.deg(math.atan2(hy, hx) - math.atan2(cz, cx))
    for _, s in ipairs({ 1, -1 }) do
        pcall(function() car:setAngles(ax, ay + s * turn, az) end)
        local nx, nz = carHeadingOf(car)
        if nx ~= nil and nx * hx + nz * hy > 0.97 then return true end
    end
    pcall(function() car:setAngles(ax, ay, az) end)
    return false
end
-- the square by the driver's door: loaded, out of his view, safe, nearest to the door (the game's own getEnterSeatDistance)
function F.doorSquare(car)
    local gu = GU()
    local cx, cy = xyOf(car)
    if gu == nil or cx == nil or type(gu.gridSquare) ~= "function" then return nil end
    local bx, by, bsq, bd
    for dx = -4, 4 do
        for dy = -4, 4 do
            local x, y = math.floor(cx) + dx, math.floor(cy) + dy
            local okQ, sq = pcall(gu.gridSquare, x, y, 0)
            if okQ and sq ~= nil and offScreen(x, y) then
                local okS, safe = true, true
                if type(gu.isSafeSpawnSquare) == "function" then okS, safe = pcall(gu.isSafeSpawnSquare, sq) end
                if okS and safe == true then
                    local okD, d = pcall(function() return car:getEnterSeatDistance(0, x + 0.5, y + 0.5) end)
                    d = okD and tonumber(d) or nil
                    if d ~= nil and (bd == nil or d < bd) then bx, by, bsq, bd = x, y, sq, d end
                end
            end
        end
    end
    return bx, by, bsq
end
function F.arrive(p, t)
    if t - (p.tryAt or 0) < 1000 and t >= (p.tryAt or 0) then return end
    p.tryAt = t
    local car = loadedCar()
    if car == nil then return end                                               -- its part of the world is not loaded yet
    if not p.aligned then
        p.aligned = F.align(car, p.heading)
        log("her car is there" .. (p.heading and (", along the road " .. (p.aligned and "yes" or "no")) or ""))
    end
    local sc = SC()
    local a = actor()
    if a == nil then
        local L = liveActor()
        if L == nil or sc == nil or type(sc.Actor) ~= "table" or type(sc.Actor.recover) ~= "function" then return end    -- a saved record: the restore brings her
        local x, y, sq = F.doorSquare(car)
        if sq == nil then return end
        local okR, done = pcall(sc.Actor.recover, L, sq)
        if not (okR and done == true) then return end
        a = L
        log("she is back at her car, " .. x .. "," .. y)
    end
    if call(a, "getVehicle") == car then p.done = true; return end
    p.seatTries = (p.seatTries or 0) + 1
    local D = sc and sc.Driving or nil
    if type(D) ~= "table" or type(D.takeWheel) ~= "function" then p.seatTries = 99; return end
    local okW, took, why = pcall(D.takeWheel, a, car, { playerCommand = true, immediateCommand = true })
    if okW and took ~= true and tostring(why) == "companion is not at the passenger door" and type(sc.Actor) == "table" and type(sc.Actor.recover) == "function" then
        local _, _, sq = F.doorSquare(car)                                        -- restored a little off: to the door, then the wheel
        if sq ~= nil and pcall(sc.Actor.recover, a, sq) then okW, took, why = pcall(D.takeWheel, a, car, { playerCommand = true, immediateCommand = true }) end
    end
    if call(a, "getVehicle") == car or (okW and took == true) then
        p.done = true
        log("she is at the wheel")
    else
        log("the wheel, try " .. p.seatTries .. ": " .. tostring(okW and why or took))
    end
end
local function tick()
    local t = nowMs()
    if t - aliveReadAt >= 5000 or t < aliveReadAt then aliveReadAt = t; pcall(readAlive); pcall(rememberCar) end
    if farCarOn() and actor() == nil then pcall(carsTick, t, record()) end              -- far_car: the cars near her, kept fresh
    if F.arriving ~= nil then pcall(F.arriveTick, t) end                         -- far_arrival inside
    if placed ~= nil and placed.car == true and placed.done ~= true then pcall(F.arrive, placed, t) end      -- far_arrival
    local a = actor()
    if a ~= nil then
        if expecting > 0 then                                                    -- also when her body comes back later than it should
            log("she is here")
            local SP = rawget(_G, "SolPlace")                                    -- spatial_access: to him through doors first, then regroup
            local px, py = xyOf(player())
            if type(SP) == "table" and type(SP.on) == "function" and SP.on() and type(SP.goNear) == "function" and px ~= nil then
                local okG, started = pcall(SP.goNear, px, py, nil, 3, function() regroup(a) end)
                if okG and started == true then expecting = 0 end
            end
            if expecting > 0 then expecting = regroup(a) and 0 or expecting - 1 end
        end
        local seating = placed ~= nil and placed.car == true and placed.done ~= true and (placed.seatTries or 0) < 8      -- far_arrival
        awake, wait, seek, moving = false, nil, nil, nil
        if not seating then placed = nil end
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
    if opt == "cars" and farCarOn() then return carsAnswer() end                -- far_car
    if opt == "car_where" and farCarOn() then return carWhereFar() end
    if opt == "car_where" then return carWhere() end
    if opt == "come" or opt == "come_car" then
        if actor() ~= nil then return true, "here" end
        if wait ~= nil then return true, "waiting:" .. waitSeconds() end
        if seek ~= nil then return true, "seeking" end
        if placed ~= nil then return true, "placed" end
        return startWait(opt == "come_car" and "car" or "foot")
    end
    if opt == "poll" then
        if placed ~= nil and placed.car == true and placed.done ~= true and (placed.seatTries or 0) < 8 and actor() ~= nil then return true, "seeking" end    -- far_arrival: getting in
        if actor() ~= nil then return true, "here" end
        if moving ~= nil then return true, "seeking" end
        if wait ~= nil and wait.fellBack then return true, "on_foot:" .. waitSeconds() end      -- far_arrival: she walks instead
        if F.arriving ~= nil then return true, "seeking" end                    -- far_arrival inside: the car is coming in
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

-- s78 cars_away: "cars" answers whatever the far_car switch says; it only reads the saved vehicle rows around her (Java, read
-- only). With the switch off the head says "cars:<n>/own|": only her own car may come, so the Mind offers none of these.
local function carsAnswer78()
    if actor() ~= nil then return true, "here" end
    local okA, why = carsAnswer()
    for _ = 1, 2 do                                                             -- carsAnswer reads a list in, then says "scanning" once
        if okA == false and why == "scanning" then okA, why = carsAnswer() end
    end
    if okA == true and not farCarOn() then why = (string.gsub(tostring(why), "^cars:(%d+)|", "cars:%1/own|", 1)) end
    return okA, why
end
local solFar77 = U.solFar
function U.solFar(option)
    if string.lower(tostring(option or "status")) == "cars" then return carsAnswer78() end
    return solFar77(option)
end
-- s78 end
SolBudget.register("far", tick, { everyMs = 1000, priority = 5 })
SolBudget.register("far_seek", seekTask, { everyMs = 0, priority = 5 })
return F

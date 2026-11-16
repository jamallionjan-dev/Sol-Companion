-- SolLife.lua - what she has learned about the world, and what dying costs her.
--   Streets she passes are remembered per save. A respawn takes them away, with the fuel stations; Sol Mind forgets its places when it sees the death count rise.
--   Her body, name and bond are not touched. Her map marker is here too: position cached about once a second, drawn only when a map is open.
SolUI = SolUI or {}
local U = SolUI
SolLife = SolLife or {}
local L = SolLife
local LIFE, STREETS = "Sol_Life", "Sol_Streets"
local SAMPLE_MS, LOOKUP_MS, MOVE_TILES, ROAD_NEAR, MAX_NAMES, POS_MS, ICON = 2000, 5000, 25, 8, 400, 1000, 22

local function log(m) print("[SolLife] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function store(key)
    if type(ModData) ~= "table" or type(ModData.getOrCreate) ~= "function" then return nil end
    local ok, d = pcall(ModData.getOrCreate, key)
    if ok and type(d) == "table" then return d end
    return nil
end
local function sync(key) if type(ModData) == "table" and type(ModData.transmit) == "function" then pcall(ModData.transmit, key) end end
local function actor() return type(U.solActor) == "function" and U.solActor() or nil end

-- ---------------------------------------------------------------- dying
-- A reload restores her with the id she had; a respawn makes a new one. The very first id seen in a save is not a death.
local function idOf(a)
    local SC = rawget(_G, "SurvivorCompanion")
    if type(SC) ~= "table" or type(SC.GameplayUtil) ~= "table" or type(SC.GameplayUtil.idOf) ~= "function" then return nil end
    local ok, id = pcall(SC.GameplayUtil.idOf, a)
    if ok and type(id) == "string" and id ~= "" then return id end
    return nil
end
function L.checkIdentity()
    local a = actor()
    if a == nil then return false end
    local id = idOf(a)
    local life = store(LIFE)
    if id == nil or life == nil then return false end
    if life.id == id then return false end
    local first = life.id == nil
    life.id = id
    sync(LIFE)
    if first then return false end
    life.deaths = (tonumber(life.deaths) or 0) + 1
    sync(LIFE)
    local s = store(STREETS)
    if s then s.streets = {}; s.count = 0; sync(STREETS) end
    local forget = rawget(_G, "solStationsForget")
    if type(forget) == "function" then pcall(forget) end
    local forgetFarm = rawget(_G, "solFarmForget")
    if type(forgetFarm) == "function" then pcall(forgetFarm) end
    local forgetBook = rawget(_G, "solAddressBookForget")                       -- address_book: her address book goes with her
    if type(forgetBook) == "function" then pcall(forgetBook) end
    -- secret_loadout is kept on purpose: shipped data + Sol_SecretLoadout.txt, no ModData, no forget hook (SolSecretLoadout.KEEP_ON_DEATH)
    L.last = nil
    log("she came back without what she had learned, death " .. life.deaths)
    return true
end
function L.onSpawned() return false end                                 -- the spawn can finish on a later tick; her identity is what counts

-- ---------------------------------------------------------------- streets
local nextSample, nextLookup = 0, 0
local function nameFromRoute(x, y)
    local G = U.gps
    local pts = type(G) == "table" and type(G.preview) == "table" and type(G.preview.route) == "table" and G.preview.route.points or nil
    if type(pts) ~= "table" then return nil end
    local best, bd = nil, ROAD_NEAR * ROAD_NEAR
    for i = 1, #pts do
        local p = pts[i]
        local d = (p.x - x) ^ 2 + (p.y - y) ^ 2
        if d < bd and type(p.street) == "string" and p.street ~= "" then best, bd = p.street, d end
    end
    return best
end
local function nameHere(x, y, now)
    local n = nameFromRoute(x, y)
    if n then return n end
    if now < nextLookup or type(U.gpsNearestRoad) ~= "function" then return nil end
    nextLookup = now + LOOKUP_MS
    local ok, _, _, dist, name = pcall(U.gpsNearestRoad, x, y)
    if ok and type(name) == "string" and name ~= "" and type(dist) == "number" and dist <= ROAD_NEAR then return name end
    return nil
end
function L.noteStreet(name, x, y)
    L.current = name
    local s = store(STREETS)
    if s == nil then return end
    if type(s.streets) ~= "table" then s.streets, s.count = {}, 0 end
    if s.streets[name] == nil then
        if (s.count or 0) >= MAX_NAMES then return end
        s.count = (s.count or 0) + 1
        s.streets[name] = { x = math.floor(x), y = math.floor(y), n = 1 }
        sync(STREETS)
        log("learned a street: " .. name)
    end
end

local function sample(now)
    local a = actor()
    if a == nil then return end
    local x, y = tonumber((call(a, "getX"))), tonumber((call(a, "getY")))
    if x == nil then return end
    if L.last and (x - L.last.x) ^ 2 + (y - L.last.y) ^ 2 < MOVE_TILES * MOVE_TILES then return end
    local name = nameHere(x, y, now)
    if name == nil then return end
    L.last, L.current = { x = x, y = y }, name
    local s = store(STREETS)
    if s == nil then return end
    if type(s.streets) ~= "table" then s.streets, s.count = {}, 0 end
    if s.streets[name] == nil then
        if (s.count or 0) >= MAX_NAMES then return end
        s.count = (s.count or 0) + 1
        s.streets[name] = { x = math.floor(x), y = math.floor(y), n = 0 }
        sync(STREETS)
        log("learned a street: " .. name)
    end
    s.streets[name].n = (s.streets[name].n or 0) + 1
end

-- For the world snapshot: what Sol Mind may know.
function L.snapshot()
    local life, s = store(LIFE), store(STREETS)
    local names = {}
    if s and type(s.streets) == "table" then for name in pairs(s.streets) do names[#names + 1] = name end end
    table.sort(names)
    return { deaths = life and tonumber(life.deaths) or 0 }, names, L.current
end

-- ---------------------------------------------------------------- her marker
local pos, nextPos = nil, 0
local function updatePos(now)
    local a = actor()
    if a == nil then if pos then pos.live = false end; return end
    local x, y = tonumber((call(a, "getX"))), tonumber((call(a, "getY")))
    if x == nil then return end
    local v = call(a, "getVehicle")
    pos = { x = x, y = y, live = true, car = v ~= nil }
    if v ~= nil then pos.x, pos.y = tonumber((call(v, "getX"))) or x, tonumber((call(v, "getY"))) or y end
end
local texture
function U.solMapDraw(ui, api)
    if pos == nil or ui == nil or api == nil then return end
    local okX, sx = pcall(function() return api:worldToUIX(pos.x, pos.y) end)
    local okY, sy = pcall(function() return api:worldToUIY(pos.x, pos.y) end)
    if not okX or not okY or type(sx) ~= "number" then return end
    if texture == nil then texture = type(getTexture) == "function" and getTexture("media/textures/SolUI/portrait_ring.png") or false end
    local a = pos.live and 1 or 0.45
    if texture and ui.drawTextureScaled then pcall(ui.drawTextureScaled, ui, texture, sx - ICON / 2, sy - ICON / 2, ICON, ICON, a, 1, 1, 1)
    elseif ui.drawRect then pcall(ui.drawRect, ui, sx - 5, sy - 5, 10, 10, a, 0.3, 0.8, 1) end
end
function L._pos() return pos end

local function tick()
    local t = nowMs()
    if t >= nextPos then nextPos = t + POS_MS; pcall(updatePos, t) end
    if t >= nextSample then nextSample = t + SAMPLE_MS; pcall(L.checkIdentity); pcall(sample, t) end
end
require "SolBudget"
SolBudget.register("life", tick, { everyMs = 250, priority = 4 })
return L

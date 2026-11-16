-- SolAddressTarget.lua - switch address_target. Where the GPS really drives for an address-book place, and an honest "arrived".
-- GENERATED ASCII from src/SolAddressTarget_src.lua (apply_s82_address_target.py --gen): Arabic is stored as \\uXXXX escapes.
--
-- 1. The target. A flyer's place is the CENTRE of PrintMediaDefinitions.MiscDetails[id].location1[1] (houseforsale903, 625 Dewey
--    Street: x 10816..10863, y 10096..10143 -> 10840,10120), a 48 x 48 lot box, not a door and not a road. The centre fell inside
--    the house (gazetteer house 10836..10846 x 10108..10123), so the road route ended on the nearest road (S Main St, behind the
--    garden fence) and SolNavLeg tried to drive the last 17 tiles into the house: no_corridor_wide_enough.
--    Now: the house = the game's own BuildingDef there (getWorld():getMetaGrid():getBuildingAt, the static map: no load needed),
--    else the lot box; the street = the one the address names ("Dewey Street" -> the whole-map road graph's "Dewey St",
--    SolStaticRoadsData); the target = the point of that street nearest the house, i.e. the road in front of it. No street of
--    that name within STREET_REACH: the nearest paved road to the house. Stashes and areas: the nearest paved road to the place.
--    SolAddressBook.go is wrapped: the entry itself is never changed, the GPS gets the road point. Doors are not read (the
--    building is usually not loaded when the order is given); the named street is the front of a US address.
-- 2. Arrived. Living Fellows says "arrived" when the road route ends, however far that is from the marker (today 15 tiles).
--    With the switch on, U.gpsStatus says result=arrived reason=road_end (gap = tiles to the marker) when the car stopped more than
--    ARRIVED_TILES from the destination. result stays "arrived", so SolNavLeg still drives the rest when it can and the Mind's goal
--    engine still sees the trip ended; the panel says it stopped at the end of the road, and once she has stood still for SAY_MS
--    (no off-road leg running) she says so in her words. Destinations the Mind sent (SolGPS_Request) keep the old answer: the Mind
--    reads reason=arrived for its own errands (the garage park watch).
SolAddressTarget = SolAddressTarget or {}
local M = SolAddressTarget
M.VERSION = "0.1.0"
M.ARRIVED_TILES = 10         -- a car stopped within this of the destination has arrived
M.STREET_REACH = 40          -- the named street must pass this close to the house
M.ROAD_REACH = 120           -- any paved road this close, when the named street is not found
M.SAY_MS = 15000             -- still this long at the end of the road before she says so
local CELL = 64              -- SolStaticRoads.lua CELL

local W = {
    roadEnd = "\\u0648\\u0642\\u0641\\u062A \\u0628\\u0622\\u062E\\u0631 \\u0627\\u0644\\u0637\\u0631\\u064A\\u0642\\u060C %s \\u0639\\u0644\\u0649 \\u0628\\u0639\\u062F %s \\u0645\\u062A\\u0631 \\u0645\\u0646 \\u0647\\u0648\\u0646.",
    marker = "\\u0627\\u0644\\u0639\\u0644\\u0627\\u0645\\u0629",
    panel = "\\u0622\\u062E\\u0631 \\u0627\\u0644\\u0637\\u0631\\u064A\\u0642: \\u0627\\u0644\\u0639\\u0644\\u0627\\u0645\\u0629 \\u0639\\u0644\\u0649 \\u0628\\u0639\\u062F %s \\u0645",
}
local EN = { panel = "End of the road: the marker is %s m away" }

local function log(m) print("[SolAddressTarget] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function g(name) return rawget(_G, name) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
local function fmt(s, a, b)
    local i = 0
    return (string.gsub(s, "%%s", function() i = i + 1; if i == 1 then return tostring(a) end return tostring(b) end))
end
function M.on() local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on("address_target") == true end

-- ---------------------------------------------------------------- street names
local SUF = { street = "st", st = "st", avenue = "ave", ave = "ave", av = "ave", road = "rd", rd = "rd", drive = "dr", dr = "dr", lane = "ln", ln = "ln",
    boulevard = "blvd", blvd = "blvd", court = "ct", ct = "ct", place = "pl", pl = "pl", highway = "hwy", hwy = "hwy", circle = "cir", cir = "cir",
    parkway = "pkwy", pkwy = "pkwy", terrace = "ter", ter = "ter", trail = "trl", trl = "trl" }
-- "625 Dewey Street, Muldraugh" -> "dewey st"; "Dewey St" -> "dewey st"
function M.streetKey(s)
    if type(s) ~= "string" then return nil end
    s = string.lower(string.match(s, "^([^,]*)") or s)
    s = string.gsub(s, "%.", "")
    local words = {}
    for w in string.gmatch(s, "[^%s]+") do words[#words + 1] = w end
    while #words > 0 and string.match(words[1], "^%d+%a?$") do table.remove(words, 1) end
    if #words == 0 then return nil end
    words[#words] = SUF[words[#words]] or words[#words]
    return table.concat(words, " ")
end

-- ---------------------------------------------------------------- geometry
local function project(px, py, ax, ay, bx, by)
    local dx, dy = bx - ax, by - ay
    local l = dx * dx + dy * dy
    if l <= 0.0001 then return ax, ay end
    local t = ((px - ax) * dx + (py - ay) * dy) / l
    if t < 0 then t = 0 elseif t > 1 then t = 1 end
    return ax + dx * t, ay + dy * t
end
local function rectDist(x, y, r)
    local dx = x < r.x1 and r.x1 - x or (x > r.x2 and x - r.x2 or 0)
    local dy = y < r.y1 and r.y1 - y or (y > r.y2 and y - r.y2 or 0)
    return math.sqrt(dx * dx + dy * dy)
end

-- the house: the game's BuildingDef at the place (static map data), else the entry's own box, else the point
local function buildingAt(grid, x, y)
    local def = call(grid, "getBuildingAt", math.floor(x), math.floor(y))
    if def == nil then return nil end
    local x1, y1 = tonumber((call(def, "getX"))), tonumber((call(def, "getY")))
    local x2, y2 = tonumber((call(def, "getX2"))), tonumber((call(def, "getY2")))
    if not (x1 and y1 and x2 and y2) or x2 < x1 or y2 < y1 then return nil end
    return { x1 = x1, y1 = y1, x2 = x2, y2 = y2, how = "building" }
end
function M.footprint(e)
    local world = type(getWorld) == "function" and getWorld() or nil
    local grid = call(world, "getMetaGrid")
    local box = (tonumber(e.x1) and tonumber(e.y1) and tonumber(e.x2) and tonumber(e.y2)) and { x1 = e.x1, y1 = e.y1, x2 = e.x2, y2 = e.y2 } or nil
    if grid ~= nil then
        local b = buildingAt(grid, e.x, e.y)
        if b == nil and box ~= nil then                                      -- the centre is in the garden: the biggest house in the box
            local best, area = nil, 0
            for x = box.x1 + 2, box.x2 - 2, 4 do
                for y = box.y1 + 2, box.y2 - 2, 4 do
                    local c = buildingAt(grid, x, y)
                    if c and (c.x2 - c.x1 + 1) * (c.y2 - c.y1 + 1) > area then best, area = c, (c.x2 - c.x1 + 1) * (c.y2 - c.y1 + 1) end
                end
            end
            b = best
        end
        if b ~= nil then return b end
    end
    if box ~= nil then box.how = "lot"; return box end
    return { x1 = e.x, y1 = e.y, x2 = e.x, y2 = e.y, how = "point" }
end

-- the road point in front of the house: on the named street, else the nearest paved road
function M.roadFor(fp, streetKey)
    local SR = g("SolStaticRoads")
    local gr = type(SR) == "table" and type(SR.load) == "function" and SR.load() or nil
    if type(gr) ~= "table" or type(gr.GRID) ~= "table" then return nil, "no_road_graph" end
    local cx, cy = (fp.x1 + fp.x2) / 2, (fp.y1 + fp.y2) / 2
    local reach = math.max(M.STREET_REACH, M.ROAD_REACH)
    local c0x, c1x = math.floor((fp.x1 - reach) / CELL), math.floor((fp.x2 + reach) / CELL)
    local c0y, c1y = math.floor((fp.y1 - reach) / CELL), math.floor((fp.y2 + reach) / CELL)
    local named, any, seen = nil, nil, {}
    for gx = c0x, c1x do
        for gy = c0y, c1y do
            local list = gr.GRID[gx * 4096 + gy]
            if list then
                for i = 1, #list do
                    local e = list[i]
                    if not seen[e] then
                        seen[e] = true
                        local a, b = gr.EA[e], gr.EB[e]
                        local qx, qy = project(cx, cy, gr.NX[a], gr.NY[a], gr.NX[b], gr.NY[b])
                        local d = rectDist(qx, qy, fp)
                        local tie = math.sqrt((qx - cx) ^ 2 + (qy - cy) ^ 2) / 1000
                        local name = gr.names[gr.EN[e]]
                        if streetKey and d <= M.STREET_REACH and M.streetKey(name) == streetKey and (named == nil or d + tie < named.s) then
                            named = { x = qx, y = qy, d = d, s = d + tie, street = name }
                        end
                        if not gr.ED[e] and d <= M.ROAD_REACH and (any == nil or d + tie < any.s) then
                            any = { x = qx, y = qy, d = d, s = d + tie, street = name }
                        end
                    end
                end
            end
        end
    end
    if named then return named, "named_street" end
    if any then return any, "nearest_road" end
    return nil, "no_road_near"
end

M.cache = M.cache or {}
-- { x, y, street, how, house } for an address-book entry, or nil (the GPS then gets the entry's own point, as before)
function M.target(e)
    if type(e) ~= "table" or not tonumber(e.x) or not tonumber(e.y) then return nil end
    local key = tostring(e.key or (e.x .. "," .. e.y))
    local hit = M.cache[key]
    if hit ~= nil then return hit or nil end
    local fp = M.footprint(e)
    local sk = e.kind == "house" and M.streetKey(e.name) or nil
    local p, how = M.roadFor(fp, sk)
    if p == nil then
        log("no road for " .. key .. ": " .. tostring(how)); M.cache[key] = false; return nil
    end
    local t = { x = math.floor(p.x + 0.5), y = math.floor(p.y + 0.5), street = p.street, how = how, house = fp }
    log(string.format("%s %s: %s %.0f..%.0f x %.0f..%.0f, %s %s at %.0f,%.0f (%.0f tiles from it)", key, tostring(e.name), fp.how, fp.x1, fp.x2, fp.y1, fp.y2,
        how, tostring(p.street), t.x, t.y, p.d))
    M.cache[key] = t
    return t
end

-- ---------------------------------------------------------------- wiring
M.state = M.state or { mindDest = nil, said = nil, still = nil }
local S = M.state
local function gps() local U = g("SolUI"); return type(U) == "table" and U or nil, type(U) == "table" and U.gps or nil end

function M.wrap()
    local B, U = g("SolAddressBook"), g("SolUI")
    if type(B) == "table" and type(B.go) == "function" and B.go ~= M.wGo then
        local orig = B.go
        M.wGo = function(e, ...)
            if M.on() and type(e) == "table" then
                local okT, t = pcall(M.target, e)
                if okT and t then
                    local c = {}
                    for k, v in pairs(e) do c[k] = v end
                    c.x, c.y = t.x, t.y
                    return orig(c, ...)
                elseif not okT then log("target failed: " .. tostring(t)) end
            end
            return orig(e, ...)
        end
        B.go = M.wGo
    end
    if type(U) == "table" and type(U.gpsPollRequest) == "function" and U.gpsPollRequest ~= M.wPoll then
        local orig = U.gpsPollRequest
        M.wPoll = function(...)
            local G = U.gps
            local before = type(G) == "table" and G.dest or nil
            local r = orig(...)
            G = U.gps
            if type(G) == "table" and G.dest ~= nil and G.dest ~= before then S.mindDest = G.dest end   -- the Mind's own trip
            return r
        end
        U.gpsPollRequest = M.wPoll
    end
    if type(U) == "table" and type(U.gpsStatus) == "function" and U.gpsStatus ~= M.wStatus then
        local orig = U.gpsStatus
        M.wStatus = function(...)
            local st = orig(...)
            if type(st) == "table" and st.result == "arrived" and st.reason == "arrived" and M.on() then
                local G = U.gps
                local d = tonumber(st.distance)
                if d and d > M.ARRIVED_TILES and type(G) == "table" and G.dest ~= nil and G.dest ~= S.mindDest then
                    st.reason, st.gap = "road_end", d
                end
            end
            return st
        end
        U.gpsStatus = M.wStatus
    end
    local Wd = g("SolGPSWords")
    if type(Wd) == "table" and type(Wd.panelLine) == "function" and Wd.panelLine ~= M.wPanel then
        local orig = Wd.panelLine
        M.wPanel = function(st, P, dest, pts, driving, failed, ar, current, ...)
            if M.on() and type(st) == "table" and st.reason == "road_end" and not driving then
                return fmt(ar and W.panel or EN.panel, tostring(st.gap or st.distance or "")), (Wd.TONE and Wd.TONE.wait) or nil
            end
            return orig(st, P, dest, pts, driving, failed, ar, current, ...)
        end
        Wd.panelLine = M.wPanel
    end
    return true
end

-- she says it once, when the car has stood at the end of the road for SAY_MS and no off-road leg is running
local nextCheck = 0
function M.tick()
    local t = nowMs()
    if t < nextCheck then return end
    nextCheck = t + 500
    local U, G = gps()
    if U == nil or type(G) ~= "table" or G.dest == nil or not M.on() or type(U.gpsStatus) ~= "function" then S.still = nil; return end
    local st = U.gpsStatus()
    local key = G.dest.x .. "," .. G.dest.y
    if st.reason ~= "road_end" or S.said == key then S.still = nil; return end
    local nav = g("solNavState")
    if nav then
        local okN, ns = pcall(nav)
        if okN and (ns == "capturing" or ns == "planning" or ns == "ready" or ns == "following") then S.still = nil; return end
    end
    local s = type(U.solActor) == "function" and U.solActor() or nil
    local v = call(s, "getVehicle")
    local x, y = tonumber((call(v, "getX"))), tonumber((call(v, "getY")))
    if not x then S.still = nil; return end
    if S.still == nil or S.still.key ~= key or (x - S.still.x) ^ 2 + (y - S.still.y) ^ 2 > 1 then S.still = { key = key, x = x, y = y, at = t }; return end
    if t - S.still.at < M.SAY_MS then return end
    S.said = key
    local name = tostring(G.dest.name or "")
    if name == "" or name == "Map point" or name == "\\u0646\\u0642\\u0637\\u0629 \\u0639\\u0644\\u0649 \\u0627\\u0644\\u062E\\u0631\\u064A\\u0637\\u0629" then name = W.marker end   -- a bare map point: "the marker"
    local line = fmt(W.roadEnd, name, tostring(st.gap or st.distance))
    log("said: stopped at the end of the road, " .. tostring(st.gap) .. " tiles from " .. key)
    local sc = g("SurvivorCompanion")
    local gu = type(sc) == "table" and sc.GameplayUtil or nil
    if s ~= nil and type(gu) == "table" and type(gu.say) == "function" then pcall(gu.say, s, line) end
end

pcall(M.wrap)
if Events then
    if Events.OnGameStart then Events.OnGameStart.Add(function() pcall(M.wrap) end) end
    if Events.OnTick then Events.OnTick.Add(function() pcall(M.tick) end) end
end
return M

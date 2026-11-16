-- SolFarmView.lua - what Sol really knows about the farm: every plant in every farm zone and the stock she can really use.
--   Plants are read from the farming global objects chunk by chunk, not by walking tiles, a few milliseconds at a time.
--   Near zones are read often, far ones rarely, and nothing is rebuilt when nothing changed. The Mind words the report; this file only counts.
--   The stock comes from one place only: the whole-base scan (SolInventory). A row of that scan says which square, object and container an item is in,
--   so she can walk there and find it again. A square that is not loaded makes a count "unsure", never a false shortage.
SolUI = SolUI or {}
local U = SolUI
SolFarmView = SolFarmView or {}
local V = SolFarmView
V.VERSION = "0.1.0"

local NEAR_TILES, NEAR_MS, FAR_MS, STOCK_ASK_MS, SLICE_CHUNKS, SLICE_ITEMS, BAG_DEPTH = 60, 15000, 90000, 30000, 4, 80, 4
local BUDGET_FALLBACK_MS = 2
local PLANT_DEAD = { dead = true, rotten = true, destroyed = true }

local function log(m) print("[SolFarmView] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
-- call() and tcall() hand back two values. The game's tonumber casts its first argument to a string as soon as it gets a second one, so a number crashes there.
local rawTonumber = tonumber
local function tonumber(v) return rawTonumber(v) end
local function g(name) return rawget(_G, name) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function fn(name) local f = g(name); if type(f) == "function" then return f end return nil end
local function LF() local sc = g("SurvivorCompanion"); if type(sc) == "table" then return sc end return nil end
local function BL() local sc = LF(); return sc and type(sc.BaseLife) == "table" and sc.BaseLife or nil end
local function GU() local sc = LF(); return sc and type(sc.GameplayUtil) == "table" and sc.GameplayUtil or nil end
local function tcall(f, ...) if type(f) ~= "function" then return nil end local ok, a = pcall(f, ...); if ok then return a end return nil end
local function actor() return type(U.solActor) == "function" and U.solActor() or nil end
local function player() local f = fn("getSpecificPlayer"); return f and f(0) or nil end

-- ---------------------------------------------------------------- the world around the plants
function V.props()
    local c = g("farming_vegetableconf")
    return type(c) == "table" and type(c.props) == "table" and c.props or {}
end
local function sfs() local S = g("SFarmingSystem"); return type(S) == "table" and S.instance or nil end
V.sfs = sfs
function V.livePlant(x, y, z) return call(sfs(), "getLuaObjectAt", x, y, z or 0) end
function V.raining()
    local rm = g("RainManager")
    if type(rm) == "table" and type(rm.isRaining) == "function" then
        local ok, r = pcall(rm.isRaining)
        if ok and r == true then return true end
    end
    local cm = fn("getClimateManager")
    local c = cm and cm() or nil
    return (tonumber((call(c, "getPrecipitationIntensity"))) or 0) > 0
end
function V.month()
    local gt = fn("getGameTime"); local t = gt and gt() or nil
    local m = tonumber((call(t, "getMonth")))
    return m and (m + 1) or nil
end
function V.seasonsOn()
    local sb = fn("getSandboxOptions"); local o = sb and sb() or nil
    local opt = call(o, "getOptionByName", "PlantGrowingSeasons")
    return opt ~= nil and call(opt, "getValue") == true
end
function V.winter()
    local cm = fn("getClimateManager"); local c = cm and cm() or nil
    return call(c, "getSeasonName") == "Winter"
end
function V.daylight()
    local gt = fn("getGameTime"); local t = gt and gt() or nil
    local h = tonumber((call(t, "getTimeOfDay")))
    if h == nil then return true end
    h = h % 24
    return h >= 6 and h < 21
end
function V.inSeason(crop, month)
    if not V.seasonsOn() then return true end
    local p = V.props()[crop]
    if type(p) ~= "table" or type(p.sowMonth) ~= "table" then return false end
    for _, m in ipairs(p.sowMonth) do if m == month then return true end end
    return false
end
local function rectOf(z) return math.min(z.x1, z.x2), math.max(z.x1, z.x2), math.min(z.y1, z.y2), math.max(z.y1, z.y2) end

-- ---------------------------------------------------------------- farm zones
-- where home is: the same answer as her "go home" (SolOrders): the base core, else the place he called home
function V.homePoint()
    local home = g("SolHome")
    local h = type(home) == "table" and type(home.get) == "function" and tcall(home.get) or nil
    if type(h) == "table" and type(h.x) == "number" then return { x = h.x, y = h.y, z = tonumber(h.z) or 0 } end
    local b = BL()
    local base = b and tcall(b.active) or nil
    local core = type(base) == "table" and base.core or nil
    if type(core) == "table" and type(core.x) == "number" and type(core.y) == "number" then return { x = core.x, y = core.y, z = tonumber(core.z) or 0 } end
    return nil
end
function V.zones()
    local b = BL()
    local base = b and tcall(b.active) or nil
    local out = {}
    if type(base) ~= "table" then return out end
    for _, z in ipairs(type(base.zones) == "table" and base.zones or {}) do
        if type(z) == "table" and z.kind == "farm" then out[#out + 1] = z end
    end
    table.sort(out, function(a, b2) return tostring(a.id) < tostring(b2.id) end)
    return out
end
local function zoneDistance(z, here)
    if here == nil then return 0 end
    local x1, x2, y1, y2 = rectOf(z)
    local dx = math.max(x1 - here.x, 0, here.x - x2)
    local dy = math.max(y1 - here.y, 0, here.y - y2)
    return math.max(dx, dy)
end
local function posOf(who)
    local x, y = tonumber((call(who, "getX"))), tonumber((call(who, "getY")))
    if x == nil then return nil end
    return { x = x, y = y, z = tonumber((call(who, "getZ"))) or 0 }
end
V.posOf = posOf

-- ---------------------------------------------------------------- the plant record: only the fields the plan names
local function readPlant(p, zoneId)
    return { x = p.x, y = p.y, z = p.z or 0, zoneId = zoneId, state = p.state, crop = p.typeOfSeed,
        nb = tonumber(p.nbOfGrow) or 0, water = tonumber(p.waterLvl) or 0, need = tonumber(p.waterNeeded) or 0, needMax = tonumber(p.waterNeededMax),
        veg = p.hasVegetable == true, seedy = p.hasSeed == true, health = tonumber(p.health) or 0,
        mildew = tonumber(p.mildewLvl) or 0, aphid = tonumber(p.aphidLvl) or 0, slugs = tonumber(p.slugsLvl) or 0, flies = tonumber(p.fliesLvl) or 0,
        weeds = p.hasWeeds == true, fert = tonumber(p.fertilizer) or 0, compost = p.compost == true,
        exterior = p.exterior ~= false, nextG = tonumber(p.nextGrowing) }
end
V.readPlant = readPlant
function V.isAlive(p) return p.state == "seeded" and (p.health or 0) > 0 end
function V.isDead(p) return PLANT_DEAD[p.state] == true or (p.state == "seeded" and (p.health or 0) <= 0) end

local function signature(rows)
    local sum = #rows
    for _, r in ipairs(rows) do
        local s, state = 0, tostring(r.state or "")
        for ci = 1, string.len(state) do s = (s * 31 + string.byte(state, ci)) % 65521 end        -- plain byte loop: the game's string library is not standard Lua
        sum = (sum * 33 + s + r.x * 7 + r.y * 11 + r.nb * 5 + math.floor(r.water) * 3 + math.floor(r.health / 10)
            + (r.veg and 1 or 0) * 2 + (r.seedy and 1 or 0) * 3 + math.ceil(r.mildew) * 19 + math.ceil(r.aphid) * 23 + math.ceil(r.slugs) * 29 + math.ceil(r.flies) * 31
            + (r.weeds and 1 or 0) * 7 + r.fert * 13 + (r.compost and 1 or 0) * 17) % 1000000007
    end
    return sum
end

-- every plant in one zone becomes the counts the chat report needs
local function countZone(rows, zone)
    local c = { id = zone.id, name = zone.name, n = #rows, alive = 0, ripe = 0, thirsty = 0, dead = 0, empty = 0, weeds = 0,
        pests = { mildew = 0, flies = 0, aphid = 0, slugs = 0 }, crops = {} }
    local crops = {}
    for _, p in ipairs(rows) do
        if V.isAlive(p) then
            c.alive = c.alive + 1
            local crop = crops[p.crop or "?"]
            if crop == nil then crop = { crop = p.crop, n = 0, ripe = 0, thirsty = 0 }; crops[p.crop or "?"] = crop; c.crops[#c.crops + 1] = crop end
            crop.n = crop.n + 1
            if p.veg then c.ripe = c.ripe + 1; crop.ripe = crop.ripe + 1 end
            if p.need > 0 and p.water < p.need then c.thirsty = c.thirsty + 1; crop.thirsty = crop.thirsty + 1 end
            if p.weeds then c.weeds = c.weeds + 1 end
            for k in pairs(c.pests) do if (p[k] or 0) > 0 then c.pests[k] = c.pests[k] + 1 end end
        elseif V.isDead(p) then c.dead = c.dead + 1
        elseif p.state == "plow" or p.state == "harvested" then c.empty = c.empty + 1 end
    end
    table.sort(c.crops, function(a, b2) return tostring(a.crop) < tostring(b2.crop) end)
    return c
end

-- ---------------------------------------------------------------- the scan: one chunk list per zone, a few chunks a slice
local scan = { q = nil, i = 1, zone = nil, acc = nil, due = {} }
local published = {}      -- zone id -> { zone, rows, counts, sig, at }
V.rev = 0                 -- rises only when something the report shows has changed
V.status = "idle"

function V.chunkSize()
    local f = fn("getChunkSizeInSquares")
    local v = f and tonumber((f())) or nil
    return v or 8
end
local function chunksOf(z)
    local cs, out = V.chunkSize(), {}
    local x1, x2, y1, y2 = rectOf(z)
    for wy = math.floor(y1 / cs), math.floor(y2 / cs) do
        for wx = math.floor(x1 / cs), math.floor(x2 / cs) do out[#out + 1] = { wx, wy } end
    end
    return out
end
local function pickZone(t)
    local zones, here, best, bd = V.zones(), posOf(actor()) or posOf(player()), nil, nil
    local live = {}
    for _, z in ipairs(zones) do
        live[z.id] = true
        local d = zoneDistance(z, here)
        local due = scan.due[z.id] or 0
        if t >= due and (bd == nil or d < bd) then best, bd = z, d end
    end
    for id in pairs(published) do if not live[id] then published[id] = nil; scan.due[id] = nil; V.rev = V.rev + 1 end end
    return best, bd
end
local function publish(t)
    local z, rows = scan.zone, scan.acc
    local sig = signature(rows)
    local old = published[z.id]
    if old == nil or old.sig ~= sig then
        published[z.id] = { zone = z, rows = rows, counts = countZone(rows, z), sig = sig, at = t }
        V.rev = V.rev + 1
    else
        old.at, old.zone = t, z
    end
    scan.q, scan.acc, scan.zone = nil, nil, nil
end
function V.tickPlants(remainingMs, sys)
    local t0, chunks, plants = nowMs(), 0, 0
    local budget = tonumber(remainingMs) or BUDGET_FALLBACK_MS
    if scan.q == nil then
        local z, dist = pickZone(t0)
        if z == nil then return end
        scan.due[z.id] = t0 + ((dist or 0) <= NEAR_TILES and NEAR_MS or FAR_MS)
        scan.q, scan.i, scan.zone, scan.acc = chunksOf(z), 1, z, {}
    end
    local z = scan.zone
    local x1, x2, y1, y2 = rectOf(z)
    local zz = tonumber(z.z) or 0
    while scan.i <= #scan.q and chunks < SLICE_CHUNKS do
        local ch = scan.q[scan.i]
        scan.i = scan.i + 1
        chunks = chunks + 1
        if call(sys, "hasObjectsInChunk", ch[1], ch[2]) == true then
            local list = call(sys, "getObjectsInChunk", ch[1], ch[2])
            local n = tonumber((call(list, "size"))) or 0
            for i = 0, n - 1 do
                local p = call(call(list, "get", i), "getModData")
                if type(p) == "table" and p.state ~= nil and tonumber(p.z or 0) == zz and p.x >= x1 and p.x <= x2 and p.y >= y1 and p.y <= y2 then
                    scan.acc[#scan.acc + 1] = readPlant(p, z.id)
                end
                plants = plants + 1
            end
        end
        if nowMs() - t0 >= budget then return end
    end
    if scan.i > #scan.q then publish(t0) end
end

-- ---------------------------------------------------------------- the land: only asked for when there is seed and nothing else to do, a slice at a time
local land = { zone = nil, x = nil, y = nil, found = nil, at = 0, want = 0 }
V.landCandidates = {}
local function canDig(sq)
    local menu = g("ISFarmingMenu")
    if type(menu) == "table" and type(menu.canDigHereSquare) == "function" then
        local ok, yes = pcall(menu.canDigHereSquare, sq)
        if ok then return yes == true end
        return false
    end
    if call(sq, "HasTree") == true or call(sq, "hasGrave") == true then return false end
    return call(sq, "isFree", false) == true and call(sq, "getZ") == 0 and V.livePlant(call(sq, "getX"), call(sq, "getY"), 0) == nil
end
-- the bed and path pattern: two furrow rows, one path row, whatever the zone
function V.bedRow(y1, y) return (y - y1) % 3 ~= 2 end
function V.requestLand(want, zones)
    if land.want > 0 then return end
    land.want = want
    land.zones = zones or V.zones()
    land.zi, land.zone = 1, land.zones[1]
    if land.zone then local x1, _, y1 = rectOf(land.zone); land.x, land.y = x1, y1 end
    land.found = {}
end
function V.tickLand(remainingMs)
    if land.want <= 0 or land.zone == nil then return end
    local t0, steps = nowMs(), 0
    local budget = tonumber(remainingMs) or BUDGET_FALLBACK_MS
    while land.zone do
        local z = land.zone
        local x1, x2, y1, y2 = rectOf(z)
        local zz = tonumber(z.z) or 0
        while land.y <= y2 and steps < 200 do
            if V.bedRow(y1, land.y) and V.livePlant(land.x, land.y, zz) == nil then
                local sq = tcall(GU() and GU().gridSquare, land.x, land.y, zz)
                if sq ~= nil and canDig(sq) then
                    land.found[#land.found + 1] = { x = land.x, y = land.y, z = zz, zoneId = z.id, op = "plow" }
                    if #land.found >= land.want then break end
                end
            end
            steps = steps + 1
            land.x = land.x + 1
            if land.x > x2 then land.x, land.y = x1, land.y + 1 end
            if steps >= 200 or nowMs() - t0 >= budget then break end
        end
        if #land.found >= land.want or land.y > y2 then
            land.zi = land.zi + 1
            land.zone = land.zones[land.zi]
            if land.zone == nil or #land.found >= land.want then
                V.landCandidates = land.found
                land.want, land.zone = 0, nil
                return
            end
            local nx1, _, ny1 = rectOf(land.zone)
            land.x, land.y = nx1, ny1
        else
            return
        end
    end
end
function V._landBusy() return land.want > 0 end
function V.dropLand(x, y, z)
    for i = #V.landCandidates, 1, -1 do
        local t = V.landCandidates[i]
        if t.x == x and t.y == y and (t.z or 0) == (z or 0) then table.remove(V.landCandidates, i) end
    end
end
-- a tile that has a plant on it now is not empty land any more
function V.pruneLand()
    for i = #V.landCandidates, 1, -1 do
        local t = V.landCandidates[i]
        if V.livePlant(t.x, t.y, t.z) ~= nil then table.remove(V.landCandidates, i) end
    end
    return V.landCandidates
end

-- ---------------------------------------------------------------- the stock she can use: whatever the whole-base scan found, nothing registered
local CURE_ITEMS = { ["Base.GardeningSprayMilk"] = true, ["Base.GardeningSprayAphids"] = true, ["Base.GardeningSprayCigarettes"] = true, ["Base.SlugRepellent"] = true }
local seedToCrop = nil
local function seedMap()
    if seedToCrop then return seedToCrop end
    local m, n = {}, 0
    for crop, p in pairs(V.props()) do
        n = n + 1
        if type(p) == "table" then
            if type(p.seedTypes) == "table" and #p.seedTypes > 0 then
                for _, s in ipairs(p.seedTypes) do m[s] = crop end
            elseif type(p.seedName) == "string" then m[p.seedName] = crop end
        end
    end
    if n > 0 then seedToCrop = m end
    return m
end
local function goodSeed(item)
    for _, nm in ipairs({ "isRotten", "isCooked", "isBurnt" }) do if call(item, nm) == true then return false end end
    return true
end
local function fluidUses(item)
    local fc = call(item, "getFluidContainer")
    if fc ~= nil then
        local amount = tonumber((call(fc, "getAmount"))) or 0
        local primary = call(fc, "getPrimaryFluid")
        local kind = primary and call(primary, "getFluidTypeString") or nil
        if (kind == "Water" or kind == "TaintedWater") then return math.floor(amount / 0.2) end
        return 0
    end
    return 0
end
local function drainUses(item)
    local v = tonumber((call(item, "getCurrentUses")))
    if v then return math.max(0, math.floor(v)) end
    v = tonumber((call(item, "getDrainableUsesFloat")))
    return v and math.max(0, math.floor(v)) or 0
end

-- what kind of farming thing an item is; identical in test and in game. Counts into st and says what it found.
local function classify(gu, item, full, st)
    local crop = seedMap()[full]
    if crop then
        if goodSeed(item) then st.seeds[crop] = (st.seeds[crop] or 0) + 1; return "seed", crop, 1 end
        return false
    end
    if tcall(gu.itemHasTag, item, "DIG_PLOW") == true then
        if call(item, "isBroken") ~= true then st.tools = st.tools + 1; return "tool", nil, 1 end
        return false
    end
    if tcall(gu.itemHasTag, item, "COMPOST") == true or string.find(string.lower(full), "compostbag", 1, true) then
        local uses = drainUses(item)
        if uses > 0 then st.compost = st.compost + 1; return "compost", nil, uses end
        return false
    end
    if tcall(gu.itemHasTag, item, "FERTILIZER") == true or full == "Base.Fertilizer" then
        local uses = drainUses(item)
        if uses > 0 then st.fert = st.fert + 1; return "fert", nil, uses end
        return false
    end
    if CURE_ITEMS[full] then local uses = drainUses(item); st.sprays[full] = (st.sprays[full] or 0) + uses; return "spray", nil, uses end
    if string.find(string.lower(full), "wateredcan", 1, true) or string.find(string.lower(full), "wateringcan", 1, true) then
        local uses = fluidUses(item)
        st.cans = st.cans + 1
        st.waterUses = st.waterUses + uses
        return "can", nil, uses
    end
    return nil
end

-- one item, the same answer for the scan and for her own bag
local notFarm = {}            -- item types the scripts make nothing to do with farming: their tags are not read again for every item in the base
function V.tagOf(item, full)
    if notFarm[full] then return nil end
    local gu = GU()
    if gu == nil then return nil end
    local scratch = { seeds = {}, tools = 0, compost = 0, fert = 0, sprays = {}, cans = 0, waterUses = 0 }
    local kind, crop, uses = classify(gu, item, full, scratch)
    if kind == nil and seedToCrop ~= nil then notFarm[full] = true end
    if not kind then return nil end
    return { kind = kind, crop = crop, uses = uses, full = full }
end
V.fluidUses = fluidUses
U.invFarmTag = function(item, full) return V.tagOf(item, full) end

local function newStock() return { seeds = {}, tools = 0, cans = 0, waterUses = 0, sprays = {}, compost = 0, fert = 0, rows = 0, unloaded = 0, unsure = {}, foodStorage = 0, outStorage = 0, ready = false } end
local stock = { seen = nil, read = nil, askedAt = -1e12, sig = nil }
V.stockLatest = newStock()
V.spots, V.places, V.waterSources = {}, {}, {}

-- where produce may go: a place that keeps food first, then a crate or shelf, never anything that cooks, washes or is emptied by the game
local NOT_FOR_FOOD = { "stove", "oven", "microwave", "toaster", "coffee", "barbecue", "grill", "fireplace", "campfire", "dumpster", "trash", "garbage", "dryer", "washer", "corpse", "logs", "postbox", "vending" }
local KEEPS_FOOD = { "crate", "box", "shelf", "shelves", "counter", "cabinet", "pantry", "cupboard", "drawer", "table", "locker", "wardrobe", "dresser" }
local function anyIn(s, words) for _, w in ipairs(words) do if string.find(s, w, 1, true) then return true end end return false end
function V.placeScore(p)
    local kind = string.lower(tostring(p.kind or ""))
    if kind == "bin" or anyIn(kind, NOT_FOR_FOOD) then return 0 end
    if string.find(kind, "fridge", 1, true) then return 4 end
    if (tonumber(p.food) or 0) > 0 then return 3 end
    if string.find(kind, "freezer", 1, true) or anyIn(kind, KEEPS_FOOD) then return 2 end
    return 1
end

function V.tickStock(remainingMs, gu)
    local t0, n = nowMs(), 0
    local budget = tonumber(remainingMs) or BUDGET_FALLBACK_MS
    if type(U.invLast) ~= "function" then return end
    if stock.read == nil then
        local last = U.invLast()
        if last == nil then V.stockDirty(); return end
        if last == stock.seen then return end
        stock.read = newStock()
        stock.read.i, stock.read.from, stock.read.spots = 1, last, {}
    end
    local r = stock.read
    local rows = type(r.from.farm) == "table" and r.from.farm or {}
    while r.i <= #rows and n < SLICE_ITEMS do
        local row = rows[r.i]
        r.i, n = r.i + 1, n + 1
        if row.kind == "seed" and row.crop then r.seeds[row.crop] = (r.seeds[row.crop] or 0) + 1
        elseif row.kind == "tool" then r.tools = r.tools + 1
        elseif row.kind == "compost" then r.compost = r.compost + 1
        elseif row.kind == "fert" then r.fert = r.fert + 1
        elseif row.kind == "spray" then r.sprays[row.type] = (r.sprays[row.type] or 0) + (tonumber(row.uses) or 0)
        elseif row.kind == "can" then r.cans = r.cans + 1; r.waterUses = r.waterUses + (tonumber(row.uses) or 0) end
        r.spots[#r.spots + 1] = row
        if nowMs() - t0 >= budget then return end
    end
    if r.i <= #rows then return end
    local last = r.from
    local places = {}
    for _, p in ipairs(type(last.places) == "table" and last.places or {}) do
        local score = V.placeScore(p)
        if score > 0 then p.score = score; places[#places + 1] = p end
    end
    r.foodStorage, r.outStorage, r.rows, r.unloaded = #places, #places, #rows, tonumber(last.unloaded) or 0
    if r.unloaded > 0 or last.trunc == true then r.unsure = { farming = true, tools = true, water = true } end
    r.noArea = last.noArea == true or nil
    r.ready, V.spots, V.places, V.waterSources = true, r.spots, places, type(last.waterSources) == "table" and last.waterSources or {}
    r.i, r.from, r.spots = nil, nil, nil
    V.stockLatest, stock.read, stock.seen = r, nil, last
    local seedTotal, sprayTotal = 0, 0
    for _, c in pairs(r.seeds) do seedTotal = seedTotal + c end
    for _, c in pairs(r.sprays) do sprayTotal = sprayTotal + c end
    local sig = seedTotal .. "|" .. r.tools .. "|" .. r.cans .. "|" .. r.waterUses .. "|" .. sprayTotal .. "|" .. r.compost .. "|" .. r.fert .. "|" .. r.foodStorage
    if sig ~= stock.sig then stock.sig = sig; V.rev = V.rev + 1 end
end
-- something moved: ask the scan to look again, not more than once in a few seconds
function V.stockDirty()
    local t = nowMs()
    if t - stock.askedAt < STOCK_ASK_MS then return end
    stock.askedAt = t
    if type(U.invStart) == "function" then pcall(U.invStart) end
end

-- what she moves between scans, so the plan does not wait for a whole-base scan after every job
function V.noteTaken(row, n)
    for _, r in ipairs(V.spots) do
        if n <= 0 then break end
        if r.where == "house" and r.x == row.x and r.y == row.y and (r.z or 0) == (row.z or 0) and r.type == row.type then r.where, n = "sol", n - 1 end
    end
end
function V.noteBack(o, n, to)
    for _, r in ipairs(V.spots) do
        if n <= 0 then break end
        if r.where == "sol" and r.type == o.type then r.where, r.x, r.y, r.z, r.oi, r.ci, n = "house", to.x, to.y, to.z or 0, to.oi, to.ci, n - 1 end
    end
end
function V.noteUsed(full, uses)
    local s = V.stockLatest
    for i, r in ipairs(V.spots) do
        if r.type == full then
            if r.kind == "seed" and r.crop then
                s.seeds[r.crop] = math.max(0, (s.seeds[r.crop] or 0) - 1)
                table.remove(V.spots, i)
            elseif r.kind == "spray" then
                s.sprays[full] = math.max(0, (s.sprays[full] or 0) - uses)
            end
            return
        end
    end
end

-- ---------------------------------------------------------------- finding again what the scan saw
local function spotDist(r, here)
    if here == nil then return 0 end
    return math.max(math.abs(r.x - here.x), math.abs(r.y - here.y))
end
function V.spotKey(r) return tostring(r.x) .. ":" .. tostring(r.y) .. ":" .. tostring(r.z or 0) .. ":" .. tostring(r.oi) .. ":" .. tostring(r.ci) .. ":" .. tostring(r.type) end
-- the nearest row in a container of the base that matches, not one already found empty on this job
function V.findRow(match, here, skip)
    local best, bd
    for _, r in ipairs(V.spots) do
        if r.where == "house" and r.x ~= nil and match(r) and not (skip and skip[V.spotKey(r)]) then
            local d = spotDist(r, here) - (r.kind == "can" and (tonumber(r.uses) or 0) >= 1 and 10000 or 0)
            if bd == nil or d < bd then best, bd = r, d end
        end
    end
    if best == nil then return nil end
    local copy = {}
    for k, v in pairs(best) do copy[k] = v end
    return copy
end
local function containersOn(row)
    local gu = GU()
    local sq = gu and tcall(gu.gridSquare, row.x, row.y, row.z or 0) or nil
    if sq == nil then return nil end
    local out, objs = {}, call(sq, "getObjects")
    local size = objs and tonumber((call(objs, "size"))) or 0
    if row.oi ~= nil and tonumber(row.oi) < size then
        local o = call(objs, "get", tonumber(row.oi))
        local c = o ~= nil and row.ci ~= nil and call(o, "getContainerByIndex", tonumber(row.ci)) or nil
        if c ~= nil then out[1] = c end
    end
    for i = 0, size - 1 do
        local o = call(objs, "get", i)
        local count = tonumber((call(o, "getContainerCount"))) or 0
        for k = 0, count - 1 do
            local c = call(o, "getContainerByIndex", k)
            if c ~= nil then out[#out + 1] = c end
        end
    end
    return out
end
local function findDeep(container, match, found, depth)
    local list = call(container, "getItems")
    local size = list and tonumber((call(list, "size"))) or 0
    for i = 0, size - 1 do
        local it = call(list, "get", i)
        if it ~= nil then
            if match(it) then found[#found + 1] = { item = it, container = container } end
            if depth < BAG_DEPTH then
                local inner = call(it, "getInventory")
                if inner ~= nil then findDeep(inner, match, found, depth + 1) end
            end
        end
    end
end
-- the live items at this row's place that match, each with the container it is really in; nil when the square is not loaded any more
function V.locate(row, match)
    local conts = containersOn(row)
    if conts == nil then return nil end
    local found, seen = {}, {}
    for _, c in ipairs(conts) do
        if not seen[c] then seen[c] = true; findDeep(c, match, found, 0) end
    end
    return found
end
function V.locateContainer(row)
    local conts = containersOn(row)
    return conts and conts[1] or nil
end
-- where produce goes, best first; the live test for room is made when she stands there
function V.depositPlaces(here)
    local out = {}
    for _, p in ipairs(V.places) do out[#out + 1] = p end
    table.sort(out, function(a, b)
        if a.score ~= b.score then return a.score > b.score end
        local da, db = spotDist(a, here), spotDist(b, here)
        if da ~= db then return da < db end
        return V.spotKey(a) < V.spotKey(b)
    end)
    return out
end
-- water for a can: the nearest thing that holds some, rain barrels and such before drinking water
function V.findWater(here)
    local best, bd
    for _, w in ipairs(V.waterSources) do
        local d = spotDist(w, here)
        if best == nil or (w.tainted == true and best.tainted ~= true) or (d < bd and (w.tainted == true) == (best.tainted == true)) then best, bd = w, d end
    end
    return best
end
function V.waterObject(row)
    local gu = GU()
    local sq = gu and tcall(gu.gridSquare, row.x, row.y, row.z or 0) or nil
    if sq == nil then return nil end
    local objs = call(sq, "getObjects")
    local size = objs and tonumber((call(objs, "size"))) or 0
    local function usable(o) return o ~= nil and call(o, "hasWater") == true and (tonumber((call(o, "getFluidAmount"))) or 0) > 0 and o or nil end
    local exact = row.oi ~= nil and tonumber(row.oi) < size and usable(call(objs, "get", tonumber(row.oi))) or nil
    if exact then return exact end
    for i = 0, size - 1 do local o = usable(call(objs, "get", i)); if o then return o end end
    return nil
end

-- ---------------------------------------------------------------- the slice the scheduler runs
function V.tick(remainingMs)
    local t0 = nowMs()
    local budget = tonumber(remainingMs) or BUDGET_FALLBACK_MS
    local S = sfs()
    local sys = S and S.system or nil
    if sys == nil then V.status = "no_farming_system"; return end
    local z = V.zones()
    if #z == 0 then V.status = "no_zone"; return end
    V.status = "ok"
    pcall(V.tickPlants, budget, sys)
    local gu = GU()
    local left = budget - (nowMs() - t0)
    if left > 0 and gu then pcall(V.tickStock, left, gu) end
    left = budget - (nowMs() - t0)
    if left > 0 then pcall(V.tickLand, left) end
end

-- ---------------------------------------------------------------- what the report and the plan read
local plantsCache, plantsCacheRev = nil, -1
function V.allPlants()
    if plantsCache and plantsCacheRev == V.rev then return plantsCache end
    local out = {}
    for _, row in pairs(published) do for _, p in ipairs(row.rows) do out[#out + 1] = p end end
    table.sort(out, function(a, b) if a.x ~= b.x then return a.x < b.x end if a.y ~= b.y then return a.y < b.y end return (a.z or 0) < (b.z or 0) end)
    plantsCache, plantsCacheRev = out, V.rev
    return out
end
function V.counts()
    local out = {}
    for _, z in ipairs(V.zones()) do
        local row = published[z.id]
        if row then out[#out + 1] = row.counts else out[#out + 1] = { id = z.id, name = z.name, unread = true } end
    end
    return out
end
function V.scanComplete()
    for _, z in ipairs(V.zones()) do if published[z.id] == nil then return false end end
    return #V.zones() > 0
end
function V.rescanZone(id) if id ~= nil then scan.due[id] = nil end end
function V.forceRescan() scan.due, scan.q, scan.acc, scan.zone = {}, nil, nil, nil end
function V.reset()
    published, V.rev, V.landCandidates = {}, 0, {}
    plantsCache, plantsCacheRev = nil, -1
    scan.q, scan.acc, scan.zone, scan.due = nil, nil, nil, {}
    stock.read, stock.seen, stock.sig, stock.askedAt = nil, nil, nil, -1e12
    land.want, land.zone = 0, nil
    seedToCrop = nil
    V.stockLatest, V.spots, V.places, V.waterSources = newStock(), {}, {}, {}
    notFarm = {}
end

return V

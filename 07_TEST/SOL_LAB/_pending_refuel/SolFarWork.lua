-- SolFarWork.lua - switch far_work (Jamal 2026-11-10: "she keeps farming when I am out of her area").
--   When he is far, her farm's part of the world is not loaded and her body does not exist: only her saved record does.
--   The plants do not stop: the game's farming system keeps every plant as a global object and runs all of them every
--   ten game minutes, loaded or not (SFarmingSystem.lua 87-128, 236-290; SGlobalObjectSystem.lua 40-46). On load it only copies
--   that state onto the tile (SPlantGlobalObject.lua 58-90). So her work while far is done the same way, on the same objects:
--   the same plan as the farm keeper (SolFarmPlan.next), the same server calls SolFarmAct makes (water, seed, cure, fertilize,
--   and the harvest of SFarmingSystem.harvest without a player), at the pace her body could keep, every game hour, night too.
--   Supplies cannot be touched while their squares are not loaded, so every item she uses or makes is written down first
--   (the ledger, ModData "Sol_FarWork") against what the last complete whole-base scan saw, and applied once when the square
--   loads. The object that holds the item keeps a mark of each applied entry in its own modData (saved with the chunk), so a
--   reload or a crash between the two saves can never apply it twice. Rain barrels are global objects: water drawn from them is
--   taken from the barrel's own state at once, the game copies it onto the barrel when it loads (SRainBarrelGlobalObject 47-78).
--   Not while far: plowing, replanting a dead tile, weeding, putting back borrowed tools (they need the tile); she says so once.
--   When he is back, one row "far_report" goes to the farm's stop list; the Mind words it in Levantine (farm_talk.far_report_line).
require "SolBudget"
SolUI = SolUI or {}
local U = SolUI
SolFarWork = SolFarWork or {}
local F = SolFarWork
F.VERSION = "0.1.0"

local STORE, FARM_STORE, MARK = "Sol_FarWork", "Sol_Farm", "SolFarLedger"
local TICK_MS, HOURS_PER_TICK, APPLY_PER_TICK, MAX_TASKS_HOUR = 1000, 6, 8, 30
local BASIS_MAX_AGE_H, NEAR_ZONE, BACK_TILES, REPORT_WAIT_MS = 48, 30, 70, 30000
local DOSE_L, CAN_DOSES = 0.2, 15
-- real seconds of her body for one job, walk and action included (SolFarmAct DURATION + the walks seen in the lab runs)
F.TASK_REAL_S = { water = 25, harvest = 30, cure = 25, compost = 25, sow = 20, refill = 45 }
local DOABLE = { water = true, harvest = true, cure = true, compost = true, sow = true }
local CURE_FN = { Mildew = "cureMildew", Flies = "cureFlies", Aphids = "cureAphids", Slugs = "cureSlugs" }

local function log(m) print("[SolFarWork] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local rawTonumber = tonumber
local function tonumber(v) return rawTonumber(v) end
local function g(name) return rawget(_G, name) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a, b = pcall(f, o, ...)
    if ok then return a, b end
    return nil
end
local function tcall(f, ...) if type(f) ~= "function" then return nil end local ok, a, b = pcall(f, ...); if ok then return a, b end return nil end
local function LF() local sc = g("SurvivorCompanion"); if type(sc) == "table" then return sc end return nil end
local function GU() local sc = LF(); return sc and type(sc.GameplayUtil) == "table" and sc.GameplayUtil or nil end
local function view() return g("SolFarmView") end
local function plan() return g("SolFarmPlan") end
local function work() return g("SolFarmWork") end
local function sfs() local S = g("SFarmingSystem"); return type(S) == "table" and S.instance or nil end
local function player() local f = g("getSpecificPlayer"); return type(f) == "function" and f(0) or nil end
function F.on()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("far_work") == true
end

-- ---------------------------------------------------------------- the ledger
local function store()
    if type(ModData) ~= "table" or type(ModData.getOrCreate) ~= "function" then return nil end
    local ok, d = pcall(ModData.getOrCreate, STORE)
    if not ok or type(d) ~= "table" then return nil end
    d.entries = type(d.entries) == "table" and d.entries or {}
    d.used = type(d.used) == "table" and d.used or {}
    d.nextId = tonumber(d.nextId) or 0
    if d.uid == nil then d.uid = "w" .. tostring(math.floor(nowMs())) end   -- one per world: a mark from another game never matches
    return d
end
F.store = store
local function farmStore() local w = work(); return w and type(w.store) == "function" and w.store() or nil end

local function gameTime() local f = g("getGameTime"); return type(f) == "function" and f() or nil end
function F.worldHour()
    local h = tonumber(call(gameTime(), "getWorldAgeHours"))
    return h and math.floor(h) or nil
end
-- game minutes that pass in one real second, from the world's day length
function F.gameMinPerRealSec()
    local mpd = tonumber(call(gameTime(), "getMinutesPerDay"))
    if mpd == nil or mpd <= 0 then mpd = 60 end
    return 1440 / (mpd * 60)
end
function F.cost(op) return (F.TASK_REAL_S[op] or 30) * F.gameMinPerRealSec() end

local function square(x, y, z)
    local gu = GU()
    if gu and type(gu.gridSquare) == "function" then return tcall(gu.gridSquare, x, y, z or 0) end
    local cell = tcall(g("getCell"))
    return call(cell, "getGridSquare", x, y, z or 0)
end
F.square = square
local function rectOf(z) return math.min(z.x1, z.x2), math.max(z.x1, z.x2), math.min(z.y1, z.y2), math.max(z.y1, z.y2) end

-- ---------------------------------------------------------------- where she is, where he is
-- her place while she has no body: a registered companion off the loaded map, or her one saved record (as SolFar reads it)
function F.herPlace()
    local L = type(U.solActor) == "function" and U.solActor() or nil
    if L ~= nil then
        if call(L, "getCurrentSquare") ~= nil then return nil, "present" end
        local x, y = tonumber(call(L, "getX")), tonumber(call(L, "getY"))
        if x ~= nil and y ~= nil then return { x = x, y = y } end
    end
    local sc = LF()
    local P = sc and sc.Persistence or nil
    if type(P) ~= "table" or type(P.pendingIds) ~= "function" or type(P.pendingBootstrap) ~= "function" then return nil, "no_record" end
    local ids = tcall(P.pendingIds)
    if type(ids) ~= "table" or #ids ~= 1 then return nil, "no_record" end
    local b = tcall(P.pendingBootstrap, ids[1])
    if type(b) ~= "table" then return nil, "no_record" end
    local pos = type(b.position) == "table" and b.position or b
    local x, y = tonumber(pos.x), tonumber(pos.y)
    if x == nil then return nil, "no_record" end
    return { x = x, y = y }
end
local function zoneDist(z, p)
    local x1, x2, y1, y2 = rectOf(z)
    return math.max(math.max(x1 - p.x, 0, p.x - x2), math.max(y1 - p.y, 0, p.y - y2))
end
-- a zone counts as far when none of its corners or its middle is loaded
function F.zoneLoaded(z)
    local x1, x2, y1, y2 = rectOf(z)
    local zz = tonumber(z.z) or 0
    local pts = { { x1, y1 }, { x2, y1 }, { x1, y2 }, { x2, y2 }, { math.floor((x1 + x2) / 2), math.floor((y1 + y2) / 2) } }
    for _, p in ipairs(pts) do if square(p[1], p[2], zz) ~= nil then return true end end
    return false
end
-- may she work the farm from afar right now? nil, why when not
function F.farZones()
    if not F.on() then return nil, "switched_off" end
    local fm = farmStore()
    if fm == nil or type(fm.modes) ~= "table" or fm.modes.farm ~= true then return nil, "no_keeper" end
    local v = view()
    if v == nil then return nil, "no_view" end
    local here, why = F.herPlace()
    if here == nil then return nil, why end
    local out = {}
    for _, z in ipairs(v.zones()) do
        if zoneDist(z, here) <= NEAR_ZONE and not F.zoneLoaded(z) then out[#out + 1] = z end
    end
    if #out == 0 then return nil, "not_at_farm" end
    return out
end
local function heIsBack(zones)
    local p = player()
    local x, y = tonumber(call(p, "getX")), tonumber(call(p, "getY"))
    if x == nil then return false end
    for _, z in ipairs(zones or {}) do if zoneDist(z, { x = x, y = y }) <= BACK_TILES then return true end end
    return false
end

-- ---------------------------------------------------------------- what the house holds: the last complete whole-base scan
local lastStock = nil
local function copyRow(r, fields)
    local o = {}
    for _, k in ipairs(fields) do o[k] = r[k] end
    return o
end
local ROW = { "kind", "type", "crop", "uses", "x", "y", "z", "oi", "ci" }
local PLACE = { "x", "y", "z", "oi", "ci", "kind", "score" }
local WATER = { "x", "y", "z", "oi", "l", "tainted" }
-- kept while she is home and everything is loaded; frozen into the shift when the farm goes far
function F.captureBasis(d)
    local v = view()
    local s = v and v.stockLatest or nil
    if type(s) ~= "table" or s.ready ~= true or (tonumber(s.unloaded) or 0) > 0 or s.noArea == true then return false end
    if s == lastStock and d.candidate ~= nil then return false end
    lastStock = s
    local rows, places, water = {}, {}, {}
    for _, r in ipairs(v.spots or {}) do
        if r.where == "house" and r.x ~= nil and r.kind ~= nil then
            local c = copyRow(r, ROW)
            c.i = #rows + 1                                                    -- one row is one item: two seeds in one box are two rows
            rows[#rows + 1] = c
        end
    end
    for _, p in ipairs(v.places or {}) do places[#places + 1] = copyRow(p, PLACE) end
    for _, w in ipairs(v.waterSources or {}) do water[#water + 1] = copyRow(w, WATER) end
    table.sort(places, function(a, b) if (a.score or 0) ~= (b.score or 0) then return (a.score or 0) > (b.score or 0) end return tostring(a.x) .. tostring(a.y) < tostring(b.x) .. tostring(b.y) end)
    d.candidate = { at = F.worldHour(), rows = rows, places = places, water = water }
    return true
end
local function rowKey(r) return tostring(r.x) .. ":" .. tostring(r.y) .. ":" .. tostring(r.z or 0) .. ":" .. tostring(r.oi) .. ":" .. tostring(r.ci) .. ":" .. tostring(r.type) end
local function itemKey(r) return r.i ~= nil and ("r" .. tostring(r.i)) or rowKey(r) end
local function left(d, r)
    local total = (r.kind == "seed" or r.kind == "tool") and 1 or (tonumber(r.uses) or 0)
    return math.max(0, total - (tonumber(d.used[itemKey(r)]) or 0))
end
-- the stock the plan reads: what the scan saw, less what the ledger already holds. No tools: nothing that needs one is done from afar.
function F.virtualStock(d)
    local st = { seeds = {}, tools = 0, cans = 0, waterUses = 0, sprays = {}, compost = 0, fert = 0, unsure = {}, ready = true,
        foodStorage = 0, outStorage = 0 }
    local b = d.basis
    if b == nil then return st end
    local canSeen = false
    for _, r in ipairs(b.rows) do
        local n = left(d, r)
        if r.kind == "seed" and r.crop and n > 0 then st.seeds[r.crop] = (st.seeds[r.crop] or 0) + 1
        elseif r.kind == "spray" and n > 0 then st.sprays[r.type] = (st.sprays[r.type] or 0) + n
        elseif r.kind == "compost" and n > 0 then st.compost = st.compost + 1
        elseif r.kind == "fert" and n > 0 then st.fert = st.fert + 1
        elseif r.kind == "can" then canSeen = true; st.waterUses = st.waterUses + n end
    end
    st.waterUses = st.waterUses + (tonumber(d.inCan) or 0)
    if canSeen then
        for _, w in ipairs(b.water) do st.waterUses = st.waterUses + math.floor(F.sourceLeft(d, w) / DOSE_L) end
    end
    st.cans = (canSeen and st.waterUses > 0) and 1 or 0
    st.foodStorage, st.outStorage = #b.places, #b.places
    return st
end

-- ---------------------------------------------------------------- reservations
local function addEntry(d, e)
    d.nextId = d.nextId + 1
    e.id, e.state, e.hour = tostring(d.nextId), "reserved", F.worldHour()
    d.entries[#d.entries + 1] = e
    return e
end
-- n units of the rows that match, oldest scan row first; returns how many were reserved
local function reserve(d, match, n, op)
    local got = 0
    for _, r in ipairs(d.basis and d.basis.rows or {}) do
        if got >= n then break end
        if match(r) then
            local k = math.min(left(d, r), n - got)
            if k > 0 then
                d.used[itemKey(r)] = (tonumber(d.used[itemKey(r)]) or 0) + k
                addEntry(d, { op = op, row = copyRow(r, ROW), n = k })
                got = got + k
            end
        end
    end
    return got
end
local function barrelAt(w)
    local S = g("SRainBarrelSystem")
    local inst = type(S) == "table" and S.instance or nil
    return inst and call(inst, "getLuaObjectAt", w.x, w.y, w.z or 0) or nil
end
-- litres a source can still give: a rain barrel by its own live state, anything else by the scan less the ledger
function F.sourceLeft(d, w)
    local barrel = barrelAt(w)
    if type(barrel) == "table" and tonumber(barrel.waterAmount) then return math.max(0, tonumber(barrel.waterAmount)) end
    return math.max(0, (tonumber(w.l) or 0) - (tonumber(d.used["src:" .. rowKey(w)]) or 0))
end
-- a refill of the can she carries: a rain barrel is drawn at once, any other source through the ledger
local function refill(d)
    local order = {}                                                            -- rain barrels first, as SolFarmView.findWater prefers rain water
    for _, w in ipairs(d.basis and d.basis.water or {}) do if type(barrelAt(w)) == "table" then order[#order + 1] = w end end
    for _, w in ipairs(d.basis and d.basis.water or {}) do if type(barrelAt(w)) ~= "table" then order[#order + 1] = w end end
    for _, w in ipairs(order) do
        local have = F.sourceLeft(d, w)
        if have >= DOSE_L then
            local doses = math.min(CAN_DOSES, math.floor(have / DOSE_L))
            local litres = doses * DOSE_L
            local barrel = barrelAt(w)
            if type(barrel) == "table" and tonumber(barrel.waterAmount) then
                barrel.waterAmount = math.max(0, barrel.waterAmount - litres)
            else
                d.used["src:" .. rowKey(w)] = (tonumber(d.used["src:" .. rowKey(w)]) or 0) + litres
                addEntry(d, { op = "draw", row = copyRow(w, WATER), litres = litres })
            end
            d.inCan = (tonumber(d.inCan) or 0) + doses
            return doses
        end
    end
    return 0
end
-- doses of water for one plant: what is in the cans at home first, then refills; the time a refill takes comes off the hour
local function takeWater(d, uses, budget)
    local got = reserve(d, function(r) return r.kind == "can" end, uses, "pour")
    local spent, late = 0, false
    while got < uses do
        local fromCan = math.min(tonumber(d.inCan) or 0, uses - got)
        if fromCan > 0 then d.inCan, got = d.inCan - fromCan, got + fromCan
        else
            if budget - spent < F.cost("refill") then late = true; break end      -- no time left this hour: not a shortage
            if refill(d) <= 0 then break end
            spent = spent + F.cost("refill")
        end
    end
    return got, spent, late
end

-- ---------------------------------------------------------------- the report she will give
local function report(d)
    if type(d.report) ~= "table" then d.report = { rounds = 0, watered = 0, harvest = {}, sown = 0, cured = 0, fed = 0, short = {}, since = F.worldHour() } end
    return d.report
end
local function addHarvest(rep, veg, n)
    for _, h in ipairs(rep.harvest) do if h.veg == veg then h.n = h.n + n; return end end
    rep.harvest[#rep.harvest + 1] = { veg = veg, n = n }
end

-- ---------------------------------------------------------------- one task, on the plant's global object
local function bestPlace(d)
    local p = d.basis and d.basis.places and d.basis.places[1] or nil
    return p and copyRow(p, PLACE) or nil
end
local DO = {}
function DO.water(d, t, live, hour, skill, budget)
    local got, spent, late = takeWater(d, tonumber(t.uses) or 1, budget)
    if got <= 0 then return false, late and "no_time" or "no_water", spent end
    live:water(nil, got)
    local rep = report(d)
    rep.watered = rep.watered + 1
    if rep.waterHour == nil or hour - rep.waterHour > 1 then rep.rounds = rep.rounds + 1 end
    rep.waterHour = hour
    return true, nil, spent
end
-- SFarmingSystem:harvest (SFarmingSystem.lua 333-382) without a player: the same numbers, the produce goes to the ledger
function DO.harvest(d, t, live, hour, skill)
    local props = farming_vegetableconf and farming_vegetableconf.props[live.typeOfSeed] or nil
    local count = g("getVegetablesNumber")
    if props == nil or type(count) ~= "function" then return false, "no_props" end
    local place = bestPlace(d)
    if place == nil then return false, "no_food_storage" end
    local n = tonumber(count(props.minVeg, props.maxVeg, props.minVegAutorized, props.maxVegAutorized, live, skill)) or 0
    local rep = report(d)
    if props.vegetableName and n > 0 then
        addEntry(d, { op = "give", type = props.vegetableName, n = n, place = place })
        addHarvest(rep, props.vegetableName, n)
    end
    if props.produceExtra and n > 0 then addEntry(d, { op = "give", type = props.produceExtra, n = n, place = place }) end
    if live.hasSeed and props.seedName then
        local per = props.seedPerVeg or 0.5
        addEntry(d, { op = "give", type = props.seedName, n = math.max(math.floor(n * per), 1), place = place })
    end
    live.hasVegetable = false
    live.hasSeed = false
    if props.growBack then
        live.nbOfGrow = props.growBack
        live.fertilizer = 0
        sfs():growPlant(live, nil, true)
        local sprite = farming_vegetableconf.getSpriteName(live)
        if sprite then live:setSpriteName(sprite) end
        live:saveData()
    else
        live:harvestThis()
    end
    return true
end
function DO.cure(d, t, live, hour, skill)
    local full = "Base." .. tostring(t.cureItem)
    local got = reserve(d, function(r) return r.kind == "spray" and r.type == full end, tonumber(t.uses) or 1, "use")
    if got <= 0 then return false, "no_spray" end
    live[CURE_FN[t.cure]](live, nil, got, skill)
    local rep = report(d)
    rep.cured = rep.cured + 1
    return true
end
function DO.compost(d, t, live, hour, skill)
    local kind = t.useCompost and "compost" or "fert"
    local got = reserve(d, function(r) return r.kind == kind end, 1, "use")
    if got <= 0 then
        kind = kind == "compost" and "fert" or "compost"
        got = reserve(d, function(r) return r.kind == kind end, 1, "use")
    end
    if got <= 0 then return false, "no_fert" end
    live:fertilize({ compost = kind == "compost", skill = skill })
    local rep = report(d)
    rep.fed = rep.fed + 1
    return true
end
function DO.sow(d, t, live, hour, skill)
    local got = reserve(d, function(r) return r.kind == "seed" and r.crop == t.crop end, 1, "take")
    if got <= 0 then return false, "no_seed" end
    live:seed(t.crop, skill)
    local rep = report(d)
    rep.sown = rep.sown + 1
    return true
end

-- ---------------------------------------------------------------- one game hour of her work
local function readPlants(zones)
    local S, v = sfs(), view()
    local sys = S and S.system or nil
    local out, live = {}, {}
    if sys == nil then return out, live end
    local cs = v.chunkSize()
    for _, z in ipairs(zones) do
        local x1, x2, y1, y2 = rectOf(z)
        local zz = tonumber(z.z) or 0
        for wy = math.floor(y1 / cs), math.floor(y2 / cs) do
            for wx = math.floor(x1 / cs), math.floor(x2 / cs) do
                if call(sys, "hasObjectsInChunk", wx, wy) == true then
                    local list = call(sys, "getObjectsInChunk", wx, wy)
                    local n = tonumber(call(list, "size")) or 0
                    for i = 0, n - 1 do
                        local p = call(call(list, "get", i), "getModData")
                        if type(p) == "table" and p.state ~= nil and tonumber(p.z or 0) == zz and p.x >= x1 and p.x <= x2 and p.y >= y1 and p.y <= y2
                            and square(p.x, p.y, zz) == nil then
                            local row = v.readPlant(p, z.id)
                            row.weeds = false                              -- weeds need the tile: not her work from afar
                            out[#out + 1] = row
                            live[plan().key(row)] = p
                        end
                    end
                    call(sys, "finishedWithList", list)
                end
            end
        end
    end
    table.sort(out, function(a, b) if a.x ~= b.x then return a.x < b.x end return a.y < b.y end)
    return out, live
end
local function farEnv(d)
    local v = view()
    local month = v.month()
    local props = v.props()
    local seasons = v.seasonsOn()
    return { raining = v.raining(), month = month, winter = v.winter(), day = true, nightOk = true, player = nil,
        skill = tonumber(d.skill) or 0, produce = 0,
        inSeason = function(crop) return v.inSeason(crop, month) end,
        isBest = function(crop)
            if not seasons then return false end
            local pr = props[crop]
            for _, m in ipairs(pr and pr.bestMonth or {}) do if m == month then return true end end
            return false
        end,
        props = function(crop) return props[crop] end,
        canWeed = function() return true end }
end
local SHORT_OF = { no_can = "water", no_seed = "seed", no_food_storage = "storage", no_fert = "fert" }
function F.workHour(d, zones, hour)
    local P = plan()
    local budget, done, skip = 60, 0, {}
    local fm = farmStore()
    for k, v in pairs(fm and fm.paused or {}) do skip[k] = v end
    local plants, live = readPlants(zones)
    local skill = tonumber(d.skill) or 0
    while done < MAX_TASKS_HOUR do
        local env = farEnv(d)
        local t, blocked = P.next(plants, F.virtualStock(d), env, { paused = skip, land = {} })
        if t == nil or not DOABLE[t.op] then
            local rep = report(d)
            for r, _ in pairs(blocked or {}) do
                local s = SHORT_OF[r] or (string.sub(r, 1, 8) == "no_seed:" and "seed") or (string.sub(r, 1, 9) == "no_spray:" and "spray") or nil
                if s then rep.short[s] = true end
            end
            break
        end
        local cost = F.cost(t.op)
        if cost > budget then break end
        local p = live[t.key]
        if p == nil or not P.stillNeeded(t, p) then skip[t.key] = true
        else
            t.before = (t.op == "water" and tonumber(p.waterLvl)) or (t.op == "cure" and tonumber(p[t.diseaseField])) or (t.op == "compost" and tonumber(p.fertilizer)) or nil
            local ok, res, why, spent = pcall(DO[t.op], d, t, p, hour, skill, budget - cost)
            spent = tonumber(spent) or 0
            if not ok then log(t.op .. " at " .. t.key .. " failed: " .. tostring(res)); skip[t.key] = true
            elseif res ~= true and why == "no_time" then break                    -- the next hour
            elseif res ~= true then
                skip[t.key] = true
                budget = budget - spent
                if SHORT_OF[why] or why == "no_water" or why == "no_spray" then report(d).short[(why == "no_water" and "water") or SHORT_OF[why] or "spray"] = true end
            else
                budget, done = budget - cost - spent, done + 1
                if not P.verify(t, p) then log(t.op .. " at " .. t.key .. " did not change the plant") end
                for i, row in ipairs(plants) do if P.key(row) == t.key then plants[i] = view().readPlant(p, row.zoneId); plants[i].weeds = false end end
            end
        end
    end
    if done > 0 then log("hour " .. tostring(hour) .. ": " .. done .. " jobs") end
    return done
end

-- ---------------------------------------------------------------- applying the ledger when a square loads
local function objectAt(row)
    local sq = square(row.x, row.y, row.z or 0)
    if sq == nil then return nil, nil end
    local objs = call(sq, "getObjects")
    local size = objs and tonumber(call(objs, "size")) or 0
    if row.oi ~= nil and tonumber(row.oi) < size then return call(objs, "get", tonumber(row.oi)), sq end
    return nil, sq
end
local function marks(o)
    local md = call(o, "getModData")
    if type(md) ~= "table" then return nil end
    md[MARK] = type(md[MARK]) == "table" and md[MARK] or {}
    return md[MARK]
end
local function fullType(item) return call(item, "getFullType") end
local function itemsAt(row, kind)
    local v = view()
    local found = v.locate(row, function(it) return fullType(it) == row.type end) or {}
    return found
end
local APPLY = {}
function APPLY.take(d, e)
    local found = itemsAt(e.row)
    local left_ = e.n - (tonumber(e.done) or 0)
    for _, f in ipairs(found) do
        if left_ <= 0 then break end
        call(f.container, "Remove", f.item)
        local send = g("sendRemoveItemFromContainer")
        if type(send) == "function" then pcall(send, f.container, f.item) end
        left_ = left_ - 1
        e.done = (tonumber(e.done) or 0) + 1
    end
    return left_ <= 0
end
function APPLY.use(d, e)
    local found = itemsAt(e.row)
    for _, f in ipairs(found) do
        while (tonumber(e.done) or 0) < e.n and (tonumber(call(f.item, "getCurrentUses")) or 0) > 0 do
            local okU = pcall(function() return f.item.UseAndSync end)
            if okU and f.item.UseAndSync ~= nil then call(f.item, "UseAndSync") else call(f.item, "Use") end
            e.done = (tonumber(e.done) or 0) + 1
        end
    end
    return (tonumber(e.done) or 0) >= e.n
end
function APPLY.pour(d, e)
    local found = itemsAt(e.row)
    for _, f in ipairs(found) do
        local fc = call(f.item, "getFluidContainer")
        local amount = tonumber(call(fc, "getAmount")) or 0
        local want = (e.n - (tonumber(e.done) or 0)) * DOSE_L
        local take = math.min(amount, want)
        if take > 0 then
            call(fc, "adjustAmount", amount - take)
            e.done = (tonumber(e.done) or 0) + math.floor(take / DOSE_L + 0.5)
        end
        if (tonumber(e.done) or 0) >= e.n then return true end
    end
    return (tonumber(e.done) or 0) >= e.n
end
function APPLY.draw(d, e, o, sq)
    local objs = call(sq, "getObjects")
    local size = objs and tonumber(call(objs, "size")) or 0
    local src = o
    if call(src, "hasWater") ~= true then
        src = nil
        for i = 0, size - 1 do local c = call(objs, "get", i); if call(c, "hasWater") == true then src = c; break end end
    end
    if src == nil then return false end
    call(src, "useFluid", tonumber(e.litres) or 0)
    return true
end
-- produce: the best food place first; a full one, the next; none with room, on the floor beside it. Its age is the time since she picked it.
function APPLY.give(d, e)
    local v = view()
    local places = {}
    if e.place then places[1] = e.place end
    for _, p in ipairs(d.basis and d.basis.places or {}) do places[#places + 1] = p end
    local days = math.max(0, ((F.worldHour() or e.hour) - (tonumber(e.hour) or 0)) / 24)
    local function fresh(item)
        if item == nil then return end
        local md = call(item, "getModData")
        if type(md) == "table" then md[MARK] = d.uid .. "-" .. e.id end
        if days > 0 and call(item, "isFood") == true then call(item, "setAge", (tonumber(call(item, "getAge")) or 0) + days) end
    end
    while (tonumber(e.done) or 0) < e.n do
        local placed = false
        for _, p in ipairs(places) do
            local c = v.locateContainer(p)
            if c ~= nil then
                local item = call(c, "AddItem", e.type)
                if item ~= nil then
                    local cap, w = tonumber(call(c, "getCapacityWeight")), tonumber(call(c, "getContentsWeight"))
                    if cap ~= nil and w ~= nil and w > cap then call(c, "Remove", item)
                    else fresh(item); placed = true; break end
                end
            end
        end
        if not placed then
            local p = places[1]
            local sq = p and square(p.x, p.y, p.z or 0) or nil
            if sq == nil then return false end
            fresh(call(sq, "AddWorldInventoryItem", e.type, 0.5, 0.5, 0))
            e.floor = true
            report(d).floor = true
        end
        e.done = (tonumber(e.done) or 0) + 1
    end
    return true
end
-- one entry, once: the holder's own mark says whether it was applied already (it is saved with the chunk, the ledger with the world)
function F.applyEntry(d, e)
    local row = e.op == "give" and e.place or e.row
    if row == nil then e.state = "short"; return true end
    local o, sq = objectAt(row)
    if sq == nil then return false end
    local holder = o or sq
    local mk = marks(holder)
    local id = d.uid .. "-" .. e.id
    if mk and mk[id] then e.state = "applied"; return true end
    local ok, done = pcall(APPLY[e.op], d, e, o, sq)
    if not ok then log("apply " .. e.op .. " failed: " .. tostring(done)); done = false end
    if done then
        e.state = "applied"
        if mk then mk[id] = true end
    else
        e.state = "short"
        if mk then mk[id] = true end                                       -- what was found was taken: never looked for again
        log("apply " .. e.op .. " " .. tostring(e.type or (e.row and e.row.type)) .. ": only " .. tostring(e.done or 0) .. " of " .. tostring(e.n or e.litres))
    end
    return true
end
function F.applySome(d)
    local n, any = 0, false
    for _, e in ipairs(d.entries) do
        if n >= APPLY_PER_TICK then break end
        if e.state == "reserved" then
            n = n + 1
            if F.applyEntry(d, e) then any = true end
        end
    end
    if any then
        local v = view()
        if v and v.stockDirty then pcall(v.stockDirty) end
    end
    local keep = {}
    for _, e in ipairs(d.entries) do if e.state == "reserved" then keep[#keep + 1] = e end end
    if #keep ~= #d.entries then d.entries = keep end
    return any
end
function F.pending(d)
    local n = 0
    for _, e in ipairs(d.entries) do if e.state == "reserved" then n = n + 1 end end
    return n
end

-- ---------------------------------------------------------------- the report, once, when he is back
local function any_(t) for _ in pairs(t or {}) do return true end return false end
local function pushStop(reason, detail)
    local m = farmStore()
    if m == nil then return false end
    m.seq = (tonumber(m.seq) or 0) + 1
    m.stop = { reason = reason, detail = detail, seq = m.seq, at = nowMs() }
    m.stops = type(m.stops) == "table" and m.stops or {}
    m.stops[#m.stops + 1] = m.stop
    while #m.stops > 4 do table.remove(m.stops, 1) end
    if type(ModData) == "table" and type(ModData.transmit) == "function" then pcall(ModData.transmit, FARM_STORE) end
    return true
end
function F.reportDetail(rep)
    local short = {}
    for k, v in pairs(rep.short or {}) do if v then short[#short + 1] = k end end
    table.sort(short)
    local harvest = {}
    for _, h in ipairs(rep.harvest or {}) do harvest[#harvest + 1] = { veg = h.veg, n = h.n } end
    table.sort(harvest, function(a, b) if a.n ~= b.n then return a.n > b.n end return a.veg < b.veg end)
    return { rounds = rep.rounds, watered = rep.watered, harvest = harvest, sown = rep.sown, cured = rep.cured, fed = rep.fed,
        short = short, floor = rep.floor == true, hours = math.max(0, (F.worldHour() or 0) - (tonumber(rep.since) or 0)) }
end
local function reportTick(d, zones)
    if type(d.report) ~= "table" then return end
    if not heIsBack(zones) then d.backAt = nil; return end
    d.backAt = d.backAt or nowMs()
    if F.pending(d) > 0 and nowMs() - d.backAt < REPORT_WAIT_MS then return end
    local rep = d.report
    local busy = rep.watered + rep.sown + rep.cured + rep.fed + #rep.harvest
    if busy > 0 or any_(rep.short) then pushStop("far_report", F.reportDetail(rep)) end
    d.report, d.backAt = nil, nil
    log("report given")
end

-- ---------------------------------------------------------------- the slice the scheduler runs
function F.tick()
    local d = store()
    if d == nil then return end
    local sc = LF()
    local a = type(U.solActor) == "function" and U.solActor() or nil
    if a ~= nil and call(a, "getCurrentSquare") ~= nil then                  -- she is here: what she can do is read off her, and the house is watched
        local gu = GU()
        local skill = gu and type(gu.perkLevel) == "function" and tonumber(tcall(gu.perkLevel, a, "Farming", 0)) or nil
        if skill then d.skill = skill end
    end
    if not d.active then F.captureBasis(d) end
    if F.pending(d) > 0 then F.applySome(d) end
    local v = view()
    local zones, why = F.farZones()
    if zones == nil then
        if d.active then
            d.active = false
            log("shift ended (" .. tostring(why) .. ")")
        end
        if v then reportTick(d, v.zones()) end
        return
    end
    local hour = F.worldHour()
    if hour == nil then return end
    if not d.active then
        local c = d.candidate
        if c == nil or (tonumber(c.at) or -1e9) < hour - BASIS_MAX_AGE_H then
            if d.noBasisSaid ~= hour then d.noBasisSaid = hour; log("far, but no complete look at the house: nothing she could count on") end
            return
        end
        d.basis, d.used, d.inCan, d.lastHour, d.active = c, {}, 0, hour, true
        d.candidate = nil
        lastStock = nil
        report(d)
        log("shift started at hour " .. hour .. " with " .. #c.rows .. " rows, " .. #c.places .. " places, " .. #c.water .. " water sources")
        return
    end
    local n = 0
    while d.lastHour < hour and n < HOURS_PER_TICK do
        d.lastHour = d.lastHour + 1
        n = n + 1
        local ok, err = pcall(F.workHour, d, zones, d.lastHour)
        if not ok then log("hour failed: " .. tostring(err)) end
    end
end

function F.install()
    if F._installed then return end
    F._installed = true
    local B = g("SolBudget")
    if type(B) == "table" and type(B.register) == "function" then B.register("sol_far_work", F.tick, { everyMs = TICK_MS, priority = 7 }) end
    log("ready v" .. F.VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(F.install) end
return F

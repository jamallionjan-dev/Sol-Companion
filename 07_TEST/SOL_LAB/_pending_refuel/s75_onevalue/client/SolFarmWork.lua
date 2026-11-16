-- SolFarmWork.lua - her order of work on the farm, from live plant state, for one companion.
--   The plan (SolFarmPlan) is a plain function of what the scan and stock say: most urgent first, one task at a time.
--   Each task becomes one job of her own, saved in ModData step by step: walk to the container if she lacks the item, take it, walk to the plant, do the action,
--   verify from the plant, later put back what she borrowed and carry the produce to a container with room. Living Fellows only moves her body: she walks by its go_to, as the refuel errand does.
--   The live plant is read again right before the action and judged afterwards by its state. Stock and containers come from the whole-base scan (SolFarmView).
--   Verb: sol_farm (report / status / short / keeper / home / water / harvest / cure / compost / weed / plow / plant:<crop> / storage / stop / proven / forget); sol_farm_try <action>.
--   The Mind words every answer. Nothing here goes straight to the player except through the Mind.
SolUI = SolUI or {}
local U = SolUI
SolFarmPlan = SolFarmPlan or {}
SolFarmWork = SolFarmWork or {}
local P, W = SolFarmPlan, SolFarmWork
W.VERSION = "0.2.0"

local STORE = "Sol_Farm"
local PAUSE_AFTER, PAUSE_MS, JOB_TIMEOUT_MS, TICK_MS, BAG_MS, NEW_LAND_WANT, LAND_RETRY_MS, SOWN_KEEP = 3, 1800000, 360000, 500, 30000, 6, 60000, 32
local WALK_MS, WALK_TILE_MS, RESEND_MS, REFUSED_LIMIT, BODY_LOST_MS, MAX_STEP_MS, BAG_HAUL_AT, SEED_BATCH, HOLD_STALE_MS, CARRY_RETRY_MS = 90000, 1500, 4000, 4, 120000, 3000, 24, 8, 5000, 60000
local SQUARE_MS, DANGER_TILES, DANGER_LIMIT_MS, HOME_NEAR, SETTLE_TILES, SETTLE_QUIET_MS, SCAN_WAIT_MS = 9000, 20, 120000, 5, 25, 20000, 60000

local function log(m) print("[SolFarmWork] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
-- call() and tcall() hand back two values. The game's tonumber casts its first argument to a string as soon as it gets a second one, so a number crashes there.
local rawTonumber = tonumber
local function tonumber(v) return rawTonumber(v) end
local function g(name) return rawget(_G, name) end
local function fn(name) local f = g(name); if type(f) == "function" then return f end return nil end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
local function tcall(f, ...) if type(f) ~= "function" then return nil end local ok, a = pcall(f, ...); if ok then return a end return nil end
local function LF() local sc = g("SurvivorCompanion"); if type(sc) == "table" then return sc end return nil end
local function GU() local sc = LF(); return sc and type(sc.GameplayUtil) == "table" and sc.GameplayUtil or nil end
local function actor() return type(U.solActor) == "function" and U.solActor() or nil end
local function player() local f = fn("getSpecificPlayer"); return f and f(0) or nil end
local function view() return g("SolFarmView") end
local function keeper() return g("SolFarmKeeper") end
local function store()
    if type(ModData) ~= "table" or type(ModData.getOrCreate) ~= "function" then return nil end
    local ok, d = pcall(ModData.getOrCreate, STORE)
    if not ok or type(d) ~= "table" then return nil end
    d.modes = type(d.modes) == "table" and d.modes or {}
    d.paused = type(d.paused) == "table" and d.paused or {}
    d.fails = type(d.fails) == "table" and d.fails or {}
    d.said = type(d.said) == "table" and d.said or {}
    d.sown = type(d.sown) == "table" and d.sown or {}
    d.unclearable = type(d.unclearable) == "table" and d.unclearable or {}
    d.proven = type(d.proven) == "table" and d.proven or {}
    d.owed = type(d.owed) == "table" and d.owed or {}              -- what she borrowed and has not put back yet
    return d
end
W.store = store
local function sync() if type(ModData) == "table" and type(ModData.transmit) == "function" then pcall(ModData.transmit, STORE) end end

-- ---------------------------------------------------------------- the plan: pure, from data only
P.PESTS = {
    { key = "mildew", field = "mildewLvl", cure = "Mildew", item = "GardeningSprayMilk", full = "Base.GardeningSprayMilk", min = 5 },
    { key = "flies", field = "fliesLvl", cure = "Flies", item = "GardeningSprayCigarettes", full = "Base.GardeningSprayCigarettes", min = 10 },
    { key = "aphid", field = "aphidLvl", cure = "Aphids", item = "GardeningSprayAphids", full = "Base.GardeningSprayAphids", min = 10, nearHarvest = true },
    { key = "slugs", field = "slugsLvl", cure = "Slugs", item = "SlugRepellent", full = "Base.SlugRepellent", min = 10, nearHarvest = true },
}
function P.fieldOfCure(cure) for _, pest in ipairs(P.PESTS) do if pest.cure == cure then return pest.field end end end
function P.key(p) return tostring(p.x) .. ":" .. tostring(p.y) .. ":" .. tostring(p.z or 0) end
local function alive(p) return p.state == "seeded" and (p.health or 0) > 0 end
local function close(a, b) return b ~= nil and math.max(math.abs(a.x - b.x), math.abs(a.y - b.y)) <= 2 and (a.z or 0) == (b.z or 0) end

-- whole doses up to the plant's own need; the plant takes 10 a dose and never holds more than its cap (100, or the crop's lower limit when it has one)
function P.waterDoses(p)
    local cap = math.min(100, tonumber(p.needMax) or 100)
    local need = math.min(tonumber(p.need) or 0, cap)
    local water = tonumber(p.water) or 0
    if need <= 0 or water >= need then return 0 end
    local want = math.ceil((need - water) / 10)
    local room = math.max(1, math.ceil((cap - water) / 10))
    return math.max(1, math.min(want, room))
end
function P.cureDoses(level, skill) return math.max(1, math.min(10, math.ceil((level or 0) / (10 + (skill or 0))))) end
function P.pestDue(p, pest, harvestAt, force)
    local lvl = p[pest.key] or 0
    if lvl <= 0 then return false end
    if force == true then return true end                                        -- he asked: any sign of it counts
    if lvl >= pest.min then return true end
    return pest.nearHarvest == true and harvestAt ~= nil and (p.nb or 0) >= harvestAt - 1
end
function P.chooseCrop(stock, env, wanted)
    local best, score
    for crop, count in pairs(stock.seeds or {}) do
        if count > 0 and (wanted == nil or wanted == crop) and env.inSeason(crop) then
            local s = count + (env.isBest and env.isBest(crop) and 1000 or 0)
            if score == nil or s > score or (s == score and crop < best) then best, score = crop, s end
        end
    end
    return best
end

function P.next(plants, stock, env, ctx)
    ctx = ctx or {}
    local filter, blocked, want = ctx.filter, {}, {}
    local function block(r, n) blocked[r] = (blocked[r] or 0) + (n or 1) end
    local function open(p)
        if ctx.paused and ctx.paused[P.key(p)] then block("paused"); return false end
        if close(p, env.player) then block("near_player"); return false end
        if p.exterior ~= false and env.day == false and env.nightOk ~= true then block("dark"); return false end   -- farm_night: with a light she works on
        return true
    end
    local function task(p, op, extra)
        local t = { op = op, x = p.x, y = p.y, z = p.z or 0, zoneId = p.zoneId, crop = p.crop, key = P.key(p) }
        for k, v in pairs(extra or {}) do t[k] = v end
        return t
    end
    local foodKnown = (stock.foodStorage or 0) > 0
    local toolKnown = (stock.tools or 0) > 0
    local unsureTools = stock.unsure and (stock.unsure.farming or stock.unsure.tools) or false

    -- 1. harvest: rotting soon first
    if filter == nil or filter == "harvest" then
        local ripe = {}
        for _, p in ipairs(plants) do if alive(p) and p.veg == true then ripe[#ripe + 1] = p end end
        table.sort(ripe, function(a, b) if (a.nb or 0) ~= (b.nb or 0) then return (a.nb or 0) > (b.nb or 0) end return P.key(a) < P.key(b) end)
        for _, p in ipairs(ripe) do
            if not foodKnown then block("no_food_storage"); break end
            if open(p) then return task(p, "harvest"), blocked end
        end
    end

    -- 2. water by each plant's own need, whole doses; never outdoors in rain
    if filter == nil or filter == "water" then
        local thirsty = false
        for _, p in ipairs(plants) do
            if alive(p) and P.waterDoses(p) > 0 then
                thirsty = true
                if (stock.cans or 0) <= 0 then
                    if stock.unsure and (stock.unsure.farming or stock.unsure.water) then block("unsure_can") else block("no_can") end
                    break
                end
                if p.exterior ~= false and env.raining then block("rain")
                elseif open(p) then return task(p, "water", { uses = P.waterDoses(p), emergency = p.water < p.need * 0.6 }), blocked end
            end
        end
        if filter == "water" and not thirsty then return nil, blocked end
    end
    if filter == "harvest" or filter == "water" then return nil, blocked end

    -- 3. pests: mildew first (the only one that stops growth), doses computed
    if filter == nil or filter == "cure" then
        for _, pest in ipairs(P.PESTS) do
            for _, p in ipairs(plants) do
                local props = env.props and env.props(p.crop) or nil
                if alive(p) and P.pestDue(p, pest, props and props.harvestLevel or nil, filter == "cure") then
                    if (stock.sprays and stock.sprays[pest.full] or 0) <= 0 then
                        if stock.unsure and stock.unsure.farming then block("unsure_spray") else block("no_spray:" .. pest.full) end
                        break
                    elseif open(p) then
                        return task(p, "cure", { cure = pest.cure, cureItem = pest.item, diseaseField = pest.field,
                            uses = math.min(P.cureDoses(p[pest.key], env.skill), stock.sprays[pest.full]) }), blocked
                    end
                end
            end
        end
    end
    -- 4. weeds, skipping what she has said she cannot clear
    if filter == nil or filter == "weed" then
        for _, p in ipairs(plants) do
            if alive(p) and p.weeds == true then
                if env.canWeed and env.canWeed(p) == false then
                    if ctx.noteUnclearable then ctx.noteUnclearable(p) end
                    block("unclearable_weeds")
                elseif open(p) then return task(p, "weed"), blocked end
            end
        end
    end

    -- 5. empty plowed tiles with in-season seed; then dead or harvested tiles
    local wanted = ctx.crop
    local crop = P.chooseCrop(stock, env, wanted)
    local sowing = filter == nil or filter == "plant"
    if sowing then
        for _, p in ipairs(plants) do
            if p.state == "plow" then
                if crop == nil then
                    if stock.unsure and stock.unsure.farming then block("unsure_seed") else block(wanted and ("no_seed:" .. wanted) or "no_seed") end
                    break
                end
                if open(p) then return task(p, "sow", { crop = crop }), blocked end
            end
        end
        for _, p in ipairs(plants) do
            if p.state ~= "seeded" and p.state ~= "plow" and p.state ~= nil then
                if crop == nil then break end
                if not toolKnown then if unsureTools then block("unsure_tool") else block("no_tool") end break end
                if open(p) then return task(p, "replant", { crop = crop }), blocked end
            end
        end
    end
    -- the plow order: dead or harvested tiles first, no seed needed
    if filter == "plow" then
        for _, p in ipairs(plants) do
            if p.state ~= "seeded" and p.state ~= "plow" and p.state ~= nil then
                if not toolKnown then block(unsureTools and "unsure_tool" or "no_tool"); return nil, blocked, want end
                if open(p) then return task(p, "plow"), blocked, want end
            end
        end
    end
    -- 6. new furrows in empty land, with a tool to use on them; on her own only when there is seed to put in them
    if sowing or filter == "plow" then
        if toolKnown and (crop ~= nil or filter == "plow") then
            local land = ctx.land or {}
            if #land == 0 then want.land = true end
            for _, tile in ipairs(land) do
                if open(tile) then return task(tile, "plow", { crop = crop }), blocked, want end
            end
        elseif not toolKnown and (crop ~= nil or filter == "plow") then
            block(unsureTools and "unsure_tool" or "no_tool")
        end
    end
    if filter == "plant" or filter == "plow" then return nil, blocked, want end

    -- 7. one dose of food, stage 3 or earlier, never in winter
    if filter == nil or filter == "compost" then
        for _, p in ipairs(plants) do
            if alive(p) and (p.nb or 0) <= 3 and (p.fert or 0) == 0 and p.compost ~= true then
                if env.winter then block("winter"); break end
                if (stock.compost or 0) + (stock.fert or 0) <= 0 then
                    if stock.unsure and stock.unsure.farming then block("unsure_fert") else block("no_fert") end
                    break
                end
                if open(p) then return task(p, "compost", { useCompost = (stock.compost or 0) > 0 }), blocked end
            end
        end
    end

    -- 8. produce left in her bag goes to storage
    if filter == nil and (env.produce or 0) > 0 then
        if not foodKnown and (stock.outStorage or 0) == 0 then block("no_food_storage")
        else return { op = "carry", n = env.produce, key = "carry" }, blocked end
    end
    return nil, blocked, want
end

-- the task is still worth doing, read off the live plant just before it is issued
function P.stillNeeded(t, live)
    if t.op == "plow" then return live == nil or (live.state ~= "seeded" and live.state ~= "plow") end      -- a replant starts by plowing a dead, rotten or harvested tile
    if live == nil then return false end
    if t.op == "harvest" then return live.state == "seeded" and live.hasVegetable == true and (tonumber(live.health) or 0) > 0 end
    if t.op == "water" then return live.state == "seeded" and (tonumber(live.waterLvl) or 0) < (tonumber(live.waterNeeded) or 0) end
    if t.op == "cure" then return (tonumber(live[t.diseaseField]) or 0) > 0 end
    if t.op == "weed" then return live.hasWeeds == true end
    if t.op == "sow" then return live.state == "plow" end
    if t.op == "replant" then return live.state ~= "seeded" and live.state ~= "plow" end
    if t.op == "compost" then return live.state == "seeded" and (tonumber(live.fertilizer) or 0) == 0 and live.compost ~= true and (tonumber(live.nbOfGrow) or 0) <= 3 end
    return true
end
-- what the job's outcome must look like, read off the live plant afterwards
function P.verify(t, live)
    if t.op == "harvest" then return live == nil or live.hasVegetable ~= true end
    if t.op == "water" then return live ~= nil and (tonumber(live.waterLvl) or 0) > (tonumber(t.before) or 0) end
    if t.op == "cure" then return live ~= nil and (tonumber(live[t.diseaseField]) or 0) < (tonumber(t.before) or 0) end
    if t.op == "weed" then return live == nil or live.hasWeeds ~= true end
    if t.op == "sow" or t.op == "replant" then return live ~= nil and live.state == "seeded" and live.typeOfSeed == t.crop end
    if t.op == "plow" then return live ~= nil and live.state == "plow" end
    if t.op == "compost" then return live ~= nil and (live.compost == true or (tonumber(live.fertilizer) or 0) > (tonumber(t.before) or 0)) end
    return true
end
local function beforeOf(t, live)
    if live == nil then return nil end
    if t.op == "water" then return tonumber(live.waterLvl) or 0 end
    if t.op == "cure" then return tonumber(live[t.diseaseField]) or 0 end
    if t.op == "compost" then return tonumber(live.fertilizer) or 0 end
    return nil
end

-- what a task needs in her hands, in the order she fetches it
function P.needsOf(t)
    if t.op == "water" then return { { kind = "can" } } end
    if t.op == "cure" then return { { kind = "spray", full = "Base." .. tostring(t.cureItem) } } end
    if t.op == "compost" then return { { kind = t.useCompost and "compost" or "fert" } } end
    if t.op == "plow" then return { { kind = "tool" } } end
    if t.op == "sow" then return { { kind = "seed", crop = t.crop } } end
    if t.op == "replant" then return { { kind = "tool" }, { kind = "seed", crop = t.crop } } end
    return {}
end
function P.needMatches(need, row)
    if type(row) ~= "table" then return false end
    if need.kind == "seed" then return row.kind == "seed" and row.crop == need.crop end
    if need.kind == "spray" then return row.kind == "spray" and row.full == need.full end
    if need.kind == "compost" or need.kind == "fert" then return row.kind == "compost" or row.kind == "fert" end
    return row.kind == need.kind
end

-- ---------------------------------------------------------------- shortages: exact items, how many are needed, how many she can borrow
local TOOL_NAMES = { "Base.GardenHoe", "Base.Shovel", "Base.HandShovel" }
function P.shortages(plants, stock, env)
    local out = {}
    local function add(full, need, have, unsure, alt) out[#out + 1] = { full = full, need = need, have = have or 0, unsure = unsure == true, alt = alt } end
    local unsure = stock.unsure or {}
    local tilled, dead, thirsty, weedsNeed, doses, feedable = 0, 0, 0, 0, {}, 0
    for _, p in ipairs(plants) do
        if alive(p) then
            if P.waterDoses(p) > 0 then thirsty = thirsty + 1 end
            local props = env.props and env.props(p.crop) or nil
            for _, pest in ipairs(P.PESTS) do
                if P.pestDue(p, pest, props and props.harvestLevel or nil) then
                    doses[pest.full] = (doses[pest.full] or 0) + P.cureDoses(p[pest.key], env.skill)
                end
            end
            if (p.nb or 0) <= 3 and (p.fert or 0) == 0 and p.compost ~= true and not env.winter then feedable = feedable + 1 end
        elseif p.state == "plow" then tilled = tilled + 1
        elseif p.state ~= nil then dead = dead + 1 end
    end
    if thirsty > 0 and (stock.cans or 0) <= 0 then add("Base.WateredCan", 1, 0, unsure.farming or unsure.water) end
    for full, need in pairs(doses) do
        local have = stock.sprays and stock.sprays[full] or 0
        if have < need then add(full, need, have, unsure.farming) end
    end
    local seeds, inseason = 0, {}
    for crop, n in pairs(stock.seeds or {}) do if n > 0 and env.inSeason(crop) then seeds = seeds + n; inseason[#inseason + 1] = crop end end
    if tilled > seeds then
        local names = {}
        if env.seedChoices then names = env.seedChoices() end
        table.sort(names)
        out[#out + 1] = { seedChoices = names, need = tilled, have = seeds, unsure = unsure.farming == true }
    end
    if (dead > 0 or tilled > 0) and (stock.tools or 0) <= 0 and dead > 0 then add(TOOL_NAMES[1], 1, 0, unsure.farming or unsure.tools, TOOL_NAMES) end
    if (stock.compost or 0) + (stock.fert or 0) == 0 and feedable > 0 then add("Base.CompostBag", 1, 0, unsure.farming, { "Base.CompostBag", "Base.Fertilizer" }) end
    table.sort(out, function(a, b) return tostring(a.full or "seed") < tostring(b.full or "seed") end)
    if (stock.foodStorage or 0) == 0 then out[#out + 1] = { storage = "food", unsure = unsure.farming == true } end
    return out
end

-- ---------------------------------------------------------------- the live inputs of the plan
-- farm_night: at night she carries a light; true when she may work outdoors now
function W.nightOk(a, daylight)
    local N = rawget(_G, "SolFarmNight")
    if daylight ~= false or type(N) ~= "table" or type(N.ensure) ~= "function" then return false end
    local ok, st = pcall(N.ensure, a, true)
    return ok and (st == "ready" or st == "none")
end
function W.env(a)
    local v = view()
    local month = v.month()
    local seasons = v.seasonsOn()
    local gu = GU()
    local skill = 0
    if gu and type(gu.perkLevel) == "function" then skill = tonumber((tcall(gu.perkLevel, a, "Farming", 0))) or 0 end
    local plr = player()
    local pos = plr and v.posOf(plr) or nil
    local props = v.props()
    return { raining = v.raining(), month = month, winter = v.winter(), day = v.daylight(), nightOk = W.nightOk(a, v.daylight()), player = pos, skill = skill,
        produce = 0,
        inSeason = function(crop) return v.inSeason(crop, month) end,
        isBest = function(crop)
            if not seasons then return false end
            local pr = props[crop]
            for _, m in ipairs(pr and pr.bestMonth or {}) do if m == month then return true end end
            return false
        end,
        seedChoices = function()
            local out = {}
            for crop, pr in pairs(props) do
                if type(pr) == "table" and v.inSeason(crop, month) then
                    local s = type(pr.seedTypes) == "table" and pr.seedTypes[1] or pr.seedName
                    if type(s) == "string" then out[#out + 1] = s end
                end
            end
            return out
        end,
        props = function(crop) return props[crop] end,
        canWeed = function(p) return W.canWeed(p) end }
end
function W.canWeed(p)
    local gu = GU()
    local sq = gu and tcall(gu.gridSquare, p.x, p.y, p.z or 0) or nil
    if sq == nil then return true end
    if call(sq, "HasTree") == true then return false end
    local objects = call(sq, "getObjects")
    local n = objects and tonumber((call(objects, "size"))) or 0
    for i = 0, n - 1 do
        local o = call(objects, "get", i)
        local sprite = call(o, "getSprite")
        local props = call(sprite, "getProperties")
        local flags = g("IsoFlagType")
        if props ~= nil and type(flags) == "table" and call(props, "has", flags.canBeCut) == true and (call(o, "getContainer") == nil) then return false end
        local attached = call(o, "getAttachedAnimSprite")                  -- wall vines count as weeds and nothing she does removes them
        local na = attached and tonumber((call(attached, "size"))) or 0
        for j = 0, na - 1 do
            local parent = call(call(attached, "get", j), "getParentSprite")
            if string.sub(tostring(call(parent, "getName") or ""), 1, 12) == "f_wallvines_" then return false end
        end
    end
    return true
end

-- ---------------------------------------------------------------- what she says, and the hold on her body
local SAY_AGAIN_MS = 1800000
local function say(m, key, reason, detail, onceOnly)
    -- one fact the Mind may speak: a key is said once (or again after a while), the Mind rate-limits it as well
    if key then
        local at = m.said[key]
        if at and (onceOnly or nowMs() - at < SAY_AGAIN_MS) then return end
        m.said[key] = nowMs()
    end
    m.seq = (tonumber(m.seq) or 0) + 1
    m.stop = { reason = reason, detail = detail, seq = m.seq, at = nowMs() }
    m.stops = m.stops or {}                                                      -- the Mind reads every 15 s or so: the real reason must not be overwritten before that
    m.stops[#m.stops + 1] = m.stop
    while #m.stops > 4 do table.remove(m.stops, 1) end
    sync()
end
W.status = function(m) m = m or store(); return m and m.statusText or nil end
local function setStatus(m, text, detail) m.statusText, m.statusDetail = text, detail end

local function orderState(a)
    local sc = LF()
    local cmd = sc and sc.Commands
    if type(cmd) ~= "table" or type(cmd.peek) ~= "function" then return nil end
    local st = tcall(cmd.peek, a)
    return type(st) == "table" and st or nil
end
-- zombies close by: her instincts have her body, the farm waits
local function danger(a)
    local gu = GU()
    local st = gu and type(gu.peekActorState) == "function" and tcall(gu.peekActorState, a) or nil
    local threats = type(st) == "table" and type(st.snapshot) == "table" and st.snapshot.threats or nil
    if type(threats) ~= "table" then return false end
    for i = 1, math.min(#threats, 32) do
        if (tonumber(threats[i].distanceSq) or 1e12) <= DANGER_TILES * DANGER_TILES then return true end
    end
    return false
end
W.danger = danger
local function baseline(m, a)
    local st = orderState(a)
    if st then m.dutyOrder, m.cmdSerial = st.order, tonumber(st.commandSerial) end
end
local function nearGoal(m, a)
    local g_ = m.walkGoal
    if type(g_) ~= "table" then return false end
    local x, y = tonumber((call(a, "getX"))), tonumber((call(a, "getY")))
    return x ~= nil and math.max(math.abs(x - g_.x), math.abs(y - g_.y)) <= 2.5
end
-- any order he gives after she went on the farm moves Living Fellows' order or its counter. Her own walk does too: it ends in a "stay" Living Fellows issues on arrival.
function W.dutyOk(a, m)
    local st = orderState(a)
    if st == nil then return true end
    local serial = tonumber(st.commandSerial)
    if m.dutyOrder == "move_to" and (st.order == "stay" or st.order == "base_duty") and serial ~= nil and m.cmdSerial ~= nil
        and serial == tonumber(m.cmdSerial) + 1 and nearGoal(m, a) then
        baseline(m, a)
        return true
    end
    if m.dutyOrder ~= nil and st.order ~= m.dutyOrder then return false end
    return serial == nil or m.cmdSerial == nil or serial == tonumber(m.cmdSerial)
end
-- her own go_to still running: ended with a stay (a player's order, already in the counter, is left alone)
local function stopWalk(m, a)
    if a == nil then return end
    local st = orderState(a)
    if st == nil or st.order ~= "move_to" or m.dutyOrder ~= "move_to" or tonumber(st.commandSerial) ~= tonumber(m.cmdSerial) then return end
    local sc, gu = LF(), GU()
    if sc and gu and type(sc.Commands) == "table" and type(sc.Commands.issue) == "function" then
        pcall(sc.Commands.issue, tcall(gu.idOf, a), "stay", nil, player())
        baseline(m, a)
    end
end
-- while this is true SolAuthority keeps Living Fellows' follow and stay logic from pulling her away (apply_s33); a dead tick lets go by itself
function U.solFarmHeld()
    local m = store()
    return m ~= nil and m.duty == true and nowMs() - (tonumber(W._tickAt) or 0) < HOLD_STALE_MS
end
-- she is on the farm: nothing changes in Living Fellows' orders, so she goes back to following or staying by herself afterwards
function W.enterDuty(a, m, noZone)
    m = m or store()
    if m == nil then return false, "store_unavailable" end
    if not (LF() and GU()) then return false, "lf_unavailable" end
    if noZone ~= true and #view().zones() == 0 then return false, "base_missing" end
    if call(a, "getVehicle") ~= nil then return false, "in_vehicle" end
    local st = orderState(a)
    if m.duty ~= true then m.prevOrder, m.walked = st and st.order or nil, nil end
    m.dutyOrder = st and st.order or nil
    m.cmdSerial = st and tonumber(st.commandSerial) or nil
    m.duty = true
    W._sessionDuty, W._tickAt = true, nowMs()
    sync()
    return true, "duty"
end

-- ---------------------------------------------------------------- her own job runner: one job, every step saved, never a Java object in ModData
local function act() return g("SolFarmAct") end
local function nav() local sc = LF(); return sc and type(sc.Navigation) == "table" and sc.Navigation or nil end
local function inv(a) local gu = GU(); local i = gu and tcall(gu.inventory, a) or nil; return i end
local function bagItems(a)
    local gu = GU()
    local i = inv(a)
    if not (gu and i) then return {} end
    local items = tcall(gu.inventoryItemsDeep, i, 180, 12)
    return type(items) == "table" and items or {}
end
local function fullOf(item) local gu = GU(); return gu and tostring(tcall(gu.itemType, item) or "") or "" end
local function tagOf(item) return view().tagOf(item, fullOf(item)) end
-- the best thing in her own bag for this need; a can with water beats an empty one
local function bagFind(a, need)
    local best, bestTag
    for _, item in ipairs(bagItems(a)) do
        local tag = tagOf(item)
        if P.needMatches(need, tag) and (best == nil or (tonumber(tag.uses) or 0) > (tonumber(bestTag.uses) or 0)) then best, bestTag = item, tag end
    end
    return best, bestTag
end
local function hasRoom(c, a, item)
    if call(c, "isItemAllowed", item) == false then return false end
    return call(c, "hasRoomFor", a, item) ~= false
end
local function moveItem(from, to, item)
    local gu = GU()
    return gu ~= nil and tcall(gu.transferItemVerified, from, to, item) == true
end
local function holderOf(item, fallback) return call(item, "getContainer") or fallback end

local function stopBody(m, a)
    local n, A_ = nav(), act()
    if a ~= nil and A_ then pcall(A_.cancel, a) end
    if m then stopWalk(m, a) end
    if a ~= nil and n and type(n.cancel) == "function" then pcall(n.cancel, a, "sol_farm") end
end
function W.cancelJob(m, a) if m.job then stopBody(m, a or actor()); m.job = nil end end

local function addOwed(m, need, full, n, row)
    for _, o in ipairs(m.owed) do
        if o.type == full and o.x == row.x and o.y == row.y and o.z == row.z then o.n = o.n + n; return end
    end
    m.owed[#m.owed + 1] = { type = full, kind = need.kind, n = n, x = row.x, y = row.y, z = row.z or 0, oi = row.oi, ci = row.ci }
end
local function consumeOwed(m, full, n)
    for i = #m.owed, 1, -1 do
        local o = m.owed[i]
        if o.type == full then
            o.n = o.n - n
            if o.n <= 0 then table.remove(m.owed, i) end
            return
        end
    end
end

local function failJob(m, a, reason)
    local j = m.job
    m.job = nil
    stopBody(m, a)
    if j == nil then return end
    print("[SolFarmWork] job failed op=" .. tostring(j.op) .. " reason=" .. tostring(reason) .. " walkFail=" .. tostring(j.walkFail) .. " at " .. tostring(j.x) .. "," .. tostring(j.y) .. " walkTo " .. tostring(j.walk and j.walk.x) .. "," .. tostring(j.walk and j.walk.y))
    if reason == "no_path" or reason == "carry_no_path" then                     -- "no road" only when it is true
        if j.walkUnloaded then
            view().rescanZone(j.zoneId)
            say(m, "unloaded:" .. tostring(j.key), "blocked", { op = j.op, why = "target_unloaded", crop = j.crop })
            return                                                               -- not the plant's fault: no pause counted
        end
        if j.walkBusy then reason = "body_busy" end
    end
    view().rescanZone(j.zoneId)
    if j.op == "carry" or j.op == "return" or j.op == "home" then
        if j.op == "carry" then W._carryWaitUntil = nowMs() + CARRY_RETRY_MS elseif j.op == "return" then W._returnWaitUntil = nowMs() + CARRY_RETRY_MS else W._homeWaitUntil = nowMs() + CARRY_RETRY_MS end
        say(m, j.op .. ":" .. tostring(reason), "blocked", { op = j.op, why = reason })
        return
    end
    local key = j.key
    m.fails[key] = (tonumber(m.fails[key]) or 0) + 1
    if m.fails[key] >= PAUSE_AFTER then
        m.paused[key] = { why = reason, at = nowMs(), op = j.op }
        m.fails[key] = 0
        say(m, "paused:" .. key .. ":" .. tostring(reason), "paused", { op = j.op, why = reason, crop = j.crop, x = j.x, y = j.y }, true)
    else
        say(m, "stop:" .. tostring(reason), "blocked", { op = j.op, why = reason, crop = j.crop })
    end
end
local function refreshPaused(m)
    local now = nowMs()
    for key, row in pairs(m.paused) do
        if now - (tonumber(row.at) or 0) > PAUSE_MS then m.paused[key] = nil end
    end
end

-- her own walking order, the way the refuel errand walks her: Living Fellows' go_to, which its decision beat keeps alive, and her own command is not mistaken for his
local function orderWalk(m, a, x, y, z)
    if type(U.solGoto) ~= "function" then return false, "walking_unavailable" end
    local ok, accepted, why = pcall(U.solGoto, x, y, z)
    if not ok then return false, "walk_error" end
    if accepted == true then baseline(m, a); m.walked = true end
    return accepted == true, why
end
-- one walk: "arrived", "walking", or "failed". She counts as there when she stands on a square from which the thing can be reached.
local function walkTo(m, j, a, x, y, z)
    local w = j.walk
    if w == nil or w.x ~= x or w.y ~= y or w.z ~= z then
        local here = view().posOf(a)
        local tiles = here and math.max(math.abs(here.x - x), math.abs(here.y - y)) or 0
        w = { x = x, y = y, z = z, from = j.spent, limit = WALK_MS + tiles * WALK_TILE_MS, sent = nil, since = nil, refused = 0, ti = 1 }
        j.walk = w
    end
    local gu, n = GU(), nav()
    if not (gu and n and type(n.interactionTargets) == "function") then return "failed" end
    if j.spent - w.from > w.limit then j.walkFail = "time_limit"; return "failed" end
    if call(a, "getVehicle") ~= nil then return "walking" end
    local square = tcall(gu.gridSquare, x, y, z)
    if square == nil then j.walkUnloaded = true; return "failed" end
    local targets = tcall(n.interactionTargets, a, square, { maximum = 8 })
    local SP = g("SolPlace")                                                   -- spatial_access: only squares on the plant's own side
    if type(SP) == "table" and type(SP.on) == "function" and SP.on() then
        local okS, own = pcall(SP.standSquares, square)
        if okS and type(own) == "table" and #own > 0 then targets = own end
    end
    if type(targets) ~= "table" or #targets == 0 then
        w.refused = w.refused + 1
        if w.refused >= REFUSED_LIMIT then j.walkFail = "no_standing_square" end
        return w.refused >= REFUSED_LIMIT and "failed" or "walking"
    end
    local px, py, pz = tonumber((call(a, "getX"))), tonumber((call(a, "getY"))), tonumber((call(a, "getZ")))
    if px ~= nil then
        px, py, pz = math.floor(px), math.floor(py), math.floor(pz or 0)
        for _, s in ipairs(targets) do
            if call(s, "getX") == px and call(s, "getY") == py and call(s, "getZ") == pz then
                stopWalk(m, a)
                return "arrived"
            end
        end
    end
    if w.since ~= nil and j.spent - w.since >= SQUARE_MS then
        local moved = px ~= nil and w.px ~= nil and math.max(math.abs(px - w.px), math.abs(py - w.py)) >= 1
        if moved then w.since = j.spent else w.ti, w.since, w.sent = w.ti + 1, nil, nil end                            -- no step in all that time: the next square
        w.px, w.py = px, py
    end
    if w.sent ~= nil and px ~= nil and (type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("walk_no_resend") == true) then
        if w.lx ~= px or w.ly ~= py then w.lx, w.ly, w.sent = px, py, j.spent end                                 -- a new square since the last look: leave her to it
    end
    if w.sent ~= nil and j.spent - w.sent < RESEND_MS then return "walking" end
    local target = targets[((w.ti - 1) % #targets) + 1]
    w.sent = j.spent
    w.since = w.since or j.spent
    m.walkGoal = { x = (tonumber((call(target, "getX"))) or x) + 0.5, y = (tonumber((call(target, "getY"))) or y) + 0.5 }
    local accepted, why = orderWalk(m, a, call(target, "getX"), call(target, "getY"), call(target, "getZ"))
    if accepted then w.refused = 0; j.walkBusy = nil; return "walking" end
    if type(why) == "string" and (string.find(why, "owned", 1, true) or string.find(why, "deferred", 1, true)) then j.walkBusy = true; return "walking" end       -- her instincts have her body for now
    w.refused = w.refused + 1
    if w.refused >= REFUSED_LIMIT then j.walkFail = "walk_refused:" .. tostring(why); return "failed" end
    return "walking"
end

local PHASE = {}
local startCarry, startReturn

local function afterWork(m, j, a)
    m.fails[j.key] = 0
    if j.op == "sow" or j.op == "replant" then
        m.sown[#m.sown + 1] = { crop = j.crop, x = j.x, y = j.y, day = W.gameDay() }
        while #m.sown > SOWN_KEEP do table.remove(m.sown, 1) end
    end
    m.job = nil
    setStatus(m, "done", j.op)
    sync()
    local v = view()
    v.rescanZone(j.zoneId)
    v.stockDirty()
    if j.op == "harvest" then W._produce = nil end
end
local function otherRipe(j, m)
    for _, p in ipairs(view().allPlants()) do
        if p.veg == true and p.state == "seeded" and P.key(p) ~= j.key and not m.paused[P.key(p)] then return true end
    end
    return false
end
local function produceItems(a)
    local crops, out = {}, {}
    for _, pr in pairs(view().props()) do
        if type(pr) == "table" then
            if type(pr.vegetableName) == "string" then crops[pr.vegetableName] = true end
            if type(pr.produceExtra) == "string" then crops[pr.produceExtra] = true end
        end
    end
    for _, item in ipairs(bagItems(a)) do
        if crops[fullOf(item)] then out[#out + 1] = item end
    end
    return out
end

-- what she lacks, in turn: from her bag, else from the nearest container that holds it
function PHASE.need(m, j, a)
    local need = j.needs[j.ni]
    if need == nil then j.phase = "go"; return end
    if bagFind(a, need) ~= nil then j.ni = j.ni + 1; return end
    local v = view()
    local row = v.findRow(function(r) return P.needMatches(need, r) end, v.posOf(a), j.skip)
    if row == nil then return failJob(m, a, "farm_supply_missing") end
    need.row = row
    j.phase, j.walk = "fetch", nil
end
function PHASE.fetch(m, j, a)
    local need = j.needs[j.ni]
    local row = need and need.row
    if row == nil then j.phase = "need"; return end
    local state = walkTo(m, j, a, row.x, row.y, row.z or 0)
    if state == "failed" then return failJob(m, a, "no_path") end
    if state ~= "arrived" then return end
    local v = view()
    local want = need.want or 1
    local found = v.locate(row, function(it)
        return fullOf(it) == row.type and P.needMatches(need, tagOf(it))
    end)
    if found == nil or #found == 0 then
        j.skip = j.skip or {}
        j.skip[v.spotKey(row)] = true
        need.row, j.phase = nil, "need"
        return
    end
    local i = inv(a)
    local taken = 0
    for _, hit in ipairs(found) do
        if taken >= want then break end
        if not hasRoom(i, a, hit.item) then
            if taken == 0 then return failJob(m, a, "bag_full") end
            break
        end
        if moveItem(holderOf(hit.item, hit.container), i, hit.item) then taken = taken + 1 end
    end
    if taken == 0 then
        j.skip = j.skip or {}
        j.skip[v.spotKey(row)] = true
        need.row, j.phase = nil, "need"
        return
    end
    addOwed(m, need, row.type, taken, row)
    v.noteTaken(row, taken)
    call(a, "SetVariable", "LootPosition", "Mid")
    call(a, "reportEvent", "EventLootItem")
    need.row = nil
    j.ni, j.phase, j.walk = j.ni + 1, "need", nil
    sync()
end

-- the thing she is doing right now: a replant is a plow, then a sow
local function currentOp(j) return j.stage or j.op end
local function checkTask(j, op) return { op = op, before = j.before, crop = j.crop, diseaseField = j.diseaseField } end

function PHASE.go(m, j, a)
    local state = walkTo(m, j, a, j.x, j.y, j.z or 0)
    if state == "failed" then return failJob(m, a, "no_path") end
    if state ~= "arrived" then return end
    local v = view()
    local op = currentOp(j)
    local live = v.livePlant(j.x, j.y, j.z)
    if j.acted ~= true and P.verify(checkTask(j, op), live) then return PHASE.applied(m, j, a, op, live) end         -- done before she got here, or before a reload
    if j.trial ~= true and not P.stillNeeded({ op = op, diseaseField = j.diseaseField }, live) then
        m.job = nil
        v.rescanZone(j.zoneId)
        return
    end
    local item, tag = nil, nil
    for _, need in ipairs(P.needsOf({ op = op, crop = j.crop, cureItem = j.cureItem, useCompost = j.useCompost })) do
        item, tag = bagFind(a, need)
        if item == nil then j.ni, j.phase, j.walk = 1, "need", nil; return end
    end
    local uses = tonumber(j.uses) or 1
    if op == "water" then
        local have = tonumber(tag.uses) or 0
        if have < 1 then j.phase, j.walk = "refill", nil; return end
        uses = math.max(1, math.min(uses, have))
    elseif op == "cure" then
        uses = math.max(1, math.min(uses, tonumber(tag.uses) or 1))
    end
    local gu = GU()
    local square = gu and tcall(gu.gridSquare, j.x, j.y, j.z or 0) or nil
    if square == nil then return failJob(m, a, "no_path") end
    if live ~= nil and j.before == nil then
        if op == "water" then j.before = tonumber(live.waterLvl) or 0
        elseif op == "cure" then j.before = tonumber(live[j.diseaseField or ""]) or 0
        elseif op == "compost" then j.before = tonumber(live.fertilizer) or 0 end
    end
    j.acted, j.itemType, j.usedUses = true, item and fullOf(item) or nil, uses
    local started, why = act().begin(a, op, { operation = op, square = square, plant = live or { x = j.x, y = j.y, z = j.z }, item = item, cropType = j.crop, uses = uses, cure = j.cure, diseaseField = j.diseaseField })
    if started ~= true then
        if why == "farm_plant_changed" then
            m.job = nil
            v.rescanZone(j.zoneId)
            return
        end
        return failJob(m, a, tostring(why or "farm_action_fallback_failed"))
    end
    j.phase = "act"
end
function PHASE.act(m, j, a)
    local A_ = act()
    local r = A_ and A_.tick(a) or nil
    if r == "active" then return end
    if r == nil or r == "away" then j.phase, j.acted, j.walk = "go", nil, nil; return end                     -- a reload in the middle of it, or she was not at the plant any more
    local v = view()
    local op = currentOp(j)
    local live = v.livePlant(j.x, j.y, j.z)
    if r == "failed" then return failJob(m, a, "farm_action_fallback_failed") end
    if not P.verify(checkTask(j, op), live) then
        A_.confirm(op, false)
        return failJob(m, a, "no_effect")
    end
    A_.confirm(op, true)
    return PHASE.applied(m, j, a, op, live)
end
function PHASE.applied(m, j, a, op, live)
    if op == "sow" and j.itemType then consumeOwed(m, j.itemType, 1); view().noteUsed(j.itemType, 1) end
    if op == "cure" and j.itemType then view().noteUsed(j.itemType, tonumber(j.usedUses) or 1) end
    if j.op == "replant" and op == "plow" then
        j.stage, j.acted, j.before, j.phase, j.walk = "sow", nil, nil, "go", nil
        j.ni = 2
        return
    end
    local harvest = j.op == "harvest"
    afterWork(m, j, a)
    if harvest then
        local bag = #produceItems(a)
        if bag > 0 and (bag >= BAG_HAUL_AT or not otherRipe(j, m)) then startCarry(m, a) end
    end
end

-- a can with no water: the nearest thing that holds some, and the same calls ISTakeWaterAction makes
function PHASE.refill(m, j, a)
    local v = view()
    if j.source == nil then
        j.source = v.findWater(v.posOf(a))
        if j.source == nil then return failJob(m, a, "water_source_missing") end
    end
    local state = walkTo(m, j, a, j.source.x, j.source.y, j.source.z or 0)
    if state == "failed" then return failJob(m, a, "no_path") end
    if state ~= "arrived" then return end
    local object = v.waterObject(j.source)
    local item, tag = bagFind(a, { kind = "can" })
    if object == nil or item == nil then return failJob(m, a, "water_source_missing") end
    j.fillBefore = tonumber(tag.uses) or 0
    local gu = GU()
    local started = act().begin(a, "fill", { operation = "fill", square = tcall(gu.gridSquare, j.source.x, j.source.y, j.source.z or 0), item = item, object = object })
    if started ~= true then return failJob(m, a, "water_source_missing") end
    j.phase = "filling"
end
function PHASE.filling(m, j, a)
    local A_ = act()
    local r = A_ and A_.tick(a) or nil
    if r == "active" then return end
    if r == nil then j.phase = "refill"; return end
    if r == "away" then j.phase, j.walk = "refill", nil; return end
    local _, tag = bagFind(a, { kind = "can" })
    if r == "failed" or tag == nil or (tonumber(tag.uses) or 0) <= (tonumber(j.fillBefore) or 0) then
        A_.confirm("fill", false)
        return failJob(m, a, "water_source_missing")
    end
    A_.confirm("fill", true)
    j.phase, j.walk, j.source = "go", nil, nil
end

-- produce to a container with room: the best kind first, the next when she finds it full
function PHASE.pick(m, j, a)
    local items = produceItems(a)
    if #items == 0 then m.job = nil; W._produce = 0; setStatus(m, "done", "carry"); view().stockDirty(); return end
    local v = view()
    local unloaded = false
    for _, p in ipairs(v.depositPlaces(v.posOf(a))) do
        local key = v.spotKey(p)
        if not (j.tried and j.tried[key]) then
            local c = v.locateContainer(p)
            if c == nil then unloaded = true
            elseif hasRoom(c, a, items[1]) then
                j.place = { x = p.x, y = p.y, z = p.z or 0, oi = p.oi, ci = p.ci }
                j.phase, j.walk = "haul", nil
                return
            else
                j.tried = j.tried or {}
                j.tried[key] = true
            end
        end
    end
    return failJob(m, a, unloaded and "storage_unloaded" or "storage_full")
end
function PHASE.haul(m, j, a)
    local place = j.place
    local state = walkTo(m, j, a, place.x, place.y, place.z or 0)
    if state == "failed" then return failJob(m, a, "carry_no_path") end
    if state ~= "arrived" then return end
    local v = view()
    local c = v.locateContainer(place)
    local moved = 0
    if c ~= nil then
        local i = inv(a)
        for _, item in ipairs(produceItems(a)) do
            if hasRoom(c, a, item) and moveItem(holderOf(item, i), c, item) then moved = moved + 1 end
        end
    end
    if moved == 0 then
        j.tried = j.tried or {}
        j.tried[v.spotKey(place)] = true
    else
        W._produce = nil
    end
    j.phase, j.place, j.walk = "pick", nil, nil
end

-- what she borrowed goes back where it came from; if that is gone or full, to the nearest place with room
function PHASE.back(m, j, a)
    local o = m.owed[1]
    if o == nil then m.job = nil; setStatus(m, "done", "return"); view().stockDirty(); sync(); return end
    local items = {}
    local i = inv(a)
    for _, item in ipairs(bagItems(a)) do
        if fullOf(item) == o.type then items[#items + 1] = item end
    end
    if #items == 0 then table.remove(m.owed, 1); return end                        -- used up, or she no longer has it
    local v = view()
    if j.backTo == nil then j.backTo = { x = o.x, y = o.y, z = o.z or 0, oi = o.oi, ci = o.ci } end
    local state = walkTo(m, j, a, j.backTo.x, j.backTo.y, j.backTo.z or 0)
    if state == "failed" then return failJob(m, a, "carry_no_path") end
    if state ~= "arrived" then return end
    local c = v.locateContainer(j.backTo)
    local moved = 0
    if c ~= nil then
        for k = 1, math.min(#items, o.n) do
            if items[k] ~= nil and call(a, "getPrimaryHandItem") == items[k] then pcall(a.setPrimaryHandItem, a, nil) end     -- a reload can leave the tool in her hand
            if hasRoom(c, a, items[k]) and moveItem(holderOf(items[k], i), c, items[k]) then moved = moved + 1 end
        end
    end
    if moved > 0 then
        v.noteBack(o, moved, j.backTo)
        o.n = o.n - moved                                                       -- only what really went back: the rest is still owed
        if o.n <= 0 or moved >= #items then table.remove(m.owed, 1) end
        j.backTo, j.walk = nil, nil
        return
    end
    -- full or gone: the nearest other place with room
    j.triedBack = j.triedBack or {}
    j.triedBack[v.spotKey(j.backTo)] = true
    for _, p in ipairs(v.depositPlaces(v.posOf(a))) do
        if not j.triedBack[v.spotKey(p)] then
            local other = v.locateContainer(p)
            if other ~= nil and hasRoom(other, a, items[1]) then
                j.backTo, j.walk = { x = p.x, y = p.y, z = p.z or 0, oi = p.oi, ci = p.ci }, nil
                return
            end
            j.triedBack[v.spotKey(p)] = true
        end
    end
    return failJob(m, a, "storage_full")
end

-- going home: until she stands there nothing says she is
function PHASE.gohome(m, j, a)
    local h = view().homePoint()
    if h == nil then return failJob(m, a, "no_home") end
    if W.atHome(a, m) then m.job = nil; return end
    local state = walkTo(m, j, a, h.x, h.y, h.z or 0)
    if state == "failed" then return failJob(m, a, "no_path") end
    if state == "arrived" then m.job = nil end
end

local function newJob(m, fields)
    m.jobSeq = (tonumber(m.jobSeq) or 0) + 1
    fields.id, fields.spent, fields.last = m.jobSeq, 0, nowMs()
    m.job = fields
    W._jobLive = m.jobSeq
    return fields
end
startCarry = function(m, a)
    if W._carryWaitUntil and nowMs() < W._carryWaitUntil then return false, "carry_wait" end
    if #produceItems(a) == 0 then W._produce = 0; return false, "nothing_carried" end
    newJob(m, { op = "carry", key = "carry", phase = "pick" })
    setStatus(m, "doing", "carry")
    sync()
    return true
end
startReturn = function(m, a)
    if W._returnWaitUntil and nowMs() < W._returnWaitUntil then return false end
    if #m.owed == 0 then return false end
    newJob(m, { op = "return", key = "return", phase = "back" })
    setStatus(m, "doing", "return")
    sync()
    return true
end
-- a job read back from a save: the action in progress is gone from memory, so she goes and looks at the plant again
local function resume(j)
    if j.phase == "act" then j.phase, j.acted, j.walk = "go", nil, nil
    elseif j.phase == "filling" then j.phase = "refill" end
    if type(j.walk) == "table" then j.walk.sent = nil end
    j.last = nowMs()
end
-- one step of the open job; clocks count real play time only (a long pause or a reload is not time spent)
local function jobStep(m, a)
    local j = m.job
    if j == nil then return end
    if W._jobLive ~= j.id then W._jobLive = j.id; resume(j) end
    local now = nowMs()
    j.spent = (tonumber(j.spent) or 0) + math.min(math.max(0, now - (tonumber(j.last) or now)), MAX_STEP_MS)
    j.last = now
    if j.spent > JOB_TIMEOUT_MS then return failJob(m, a, "timeout") end
    for _ = 1, 8 do                                                             -- a step that needs no time is not made to wait for the next slice
        local phase = j.phase
        local handler = PHASE[phase]
        if handler == nil then return failJob(m, a, "timeout") end
        handler(m, j, a)
        if m.job ~= j or j.phase == phase then break end
    end
    if m.job == nil then stopWalk(m, a) end
end
W._jobStep = jobStep
-- the job waits out a threat: no walking into it, no action, her instincts have her
local function pauseJob(m, j, a)
    local now = nowMs()
    j.danger = (tonumber(j.danger) or 0) + math.min(math.max(0, now - (tonumber(j.last) or now)), MAX_STEP_MS)
    j.last = now
    if j.danger > DANGER_LIMIT_MS then return failJob(m, a, "unsafe_area") end
    local A_ = act()
    if A_ then A_.cancel(a) end
    if j.phase == "act" then j.phase, j.acted = "go", nil elseif j.phase == "filling" then j.phase = "refill" end
    stopWalk(m, a)
    if type(j.walk) == "table" then j.walk.sent, j.walk.since = nil, nil end
end

local function issue(m, t, a)
    if t.op == "carry" then return startCarry(m, a) end
    local v = view()
    local live = t.x and v.livePlant(t.x, t.y, t.z) or nil
    if t.trial ~= true and not P.stillNeeded(t, live) then
        if t.op == "plow" then v.dropLand(t.x, t.y, t.z) end
        v.rescanZone(t.zoneId)
        return false, "changed"
    end
    if live ~= nil and t.op == "water" and t.trial ~= true then t.uses = math.max(1, P.waterDoses(v.readPlant(live, t.zoneId))) end       -- the doses too, from the plant as it is now
    if t.op == "plow" then v.dropLand(t.x, t.y, t.z) end
    local needs = P.needsOf(t)
    for _, need in ipairs(needs) do
        if need.kind == "seed" then need.want = SEED_BATCH end
    end
    newJob(m, { key = t.key, op = t.op, crop = t.crop, x = t.x, y = t.y, z = t.z, zoneId = t.zoneId, uses = t.uses, cure = t.cure, cureItem = t.cureItem,
        diseaseField = t.diseaseField, useCompost = t.useCompost, emergency = t.emergency, trial = t.trial, before = beforeOf(t, live), needs = needs, ni = 1, phase = "need",
        stage = t.op == "replant" and "plow" or nil })
    if type(W._onJob) == "function" then W._onJob(m.job) end
    setStatus(m, "doing", t.op)
    sync()
    return true
end
W._issueTrial = issue

function W.gameDay()
    local gt = fn("getGameTime"); local t = gt and gt() or nil
    return tonumber(call(t, "getWorldAgeHours") or 0) and math.floor((tonumber((call(t, "getWorldAgeHours"))) or 0) / 24) or 0
end

-- she goes back to what she was told before, if her walks changed it; his own new order leaves it alone (pass keep)
function W.releaseDuty(m, keep)
    local prev, walked = m.prevOrder, m.walked
    m.duty, m.prevOrder, m.walked, m.settling = false, nil, nil, nil
    if keep ~= true and walked == true then
        local sc, gu, a = LF(), GU(), actor()
        if a and sc and gu and type(sc.Commands) == "table" and type(sc.Commands.issue) == "function" then
            pcall(sc.Commands.issue, tcall(gu.idOf, a), prev == "stay" and "stay" or "follow", nil, player())
        end
    end
    sync()
end
function W.endSingle(m)
    if m.modes.farm == true or m.modes.home == true or m.duty ~= true then return end
    W.releaseDuty(m)
end
function W.engaged(m) return m.modes.farm == true or m.filter ~= nil end
-- one reason at a time: the most useful one to tell him (something short before rain or dark)
local REASON_ORDER = { "no_can", "unsure_can", "no_food_storage", "no_tool", "unsure_tool", "no_seed", "unsure_seed", "unsure_spray", "unsure_fert", "rain", "dark", "near_player", "paused", "winter", "no_fert", "unclearable_weeds" }
local function reasonOf(blocked)
    if type(blocked) ~= "table" then return nil end
    for k in pairs(blocked) do
        if type(k) == "string" and (string.sub(k, 1, 9) == "no_spray:" or string.sub(k, 1, 8) == "no_seed:") then return k end
    end
    for _, r in ipairs(REASON_ORDER) do if blocked[r] then return r end end
    for reason in pairs(blocked) do if type(reason) == "string" then return reason end end  -- the game's Lua has no next()
    return nil
end
-- saying why nothing was done must never be what breaks the order
function W.topReason(blocked)
    local ok, why = pcall(reasonOf, blocked)
    if ok then return why end
    log("no reason given: " .. tostring(why))
    return nil
end

local lastBag = 0
local function produceInBag(a)
    local now = nowMs()
    if W._produce ~= nil and now - lastBag < BAG_MS then return W._produce end
    lastBag = now
    W._produce = #produceItems(a)
    return W._produce
end
-- whether the task coming next uses what she is still carrying
local function usesOwed(m, t)
    for _, need in ipairs(P.needsOf(t)) do
        for _, o in ipairs(m.owed) do
            if o.kind == need.kind then return true end
        end
    end
    return false
end

function W.finishSingle(m, why)
    local kind = m.filter.kind
    setStatus(m, "finished", kind)
    m.filter = nil
    if why then say(m, "single:" .. kind .. ":" .. why, "waiting", { why = why }) else say(m, nil, "done", { kind = kind }) end
    W.endSingle(m)
end
-- "stay home": really at home, or on the way there
function W.atHome(a, m)
    local h = view().homePoint()
    local here = view().posOf(a)
    if h == nil or here == nil then return false end
    return math.max(math.abs(here.x - h.x), math.abs(here.y - h.y)) <= HOME_NEAR and math.floor(here.z or 0) == math.floor(h.z or 0)
end
function W.homeTick(m, a, k)
    if view().homePoint() == nil then setStatus(m, "waiting", "no_home"); return end
    if W.atHome(a, m) then
        if m.atHome ~= true or m.homeStayDone ~= true then                       -- told to stay while already there: the stay is still needed
            local arrived = m.atHome ~= true
            m.atHome, m.homeStayDone = true, true
            local st = orderState(a)
            if st and st.order ~= "stay" and st.order ~= "base_duty" then                  -- standing there, so washing and sleep can be chosen
                local sc, gu = LF(), GU()
                if sc and gu and type(sc.Commands) == "table" and type(sc.Commands.issue) == "function" then
                    pcall(sc.Commands.issue, tcall(gu.idOf, a), "stay", nil, player())
                    m.walked = true
                    baseline(m, a)
                end
            end
            if arrived then say(m, nil, "home_arrived", {}) end
        end
        local need = k and k.bodyNeed and k.bodyNeed(a) or nil
        if need then setStatus(m, "needs", need) else setStatus(m, "home") end
        return
    end
    m.atHome = false
    if W._homeWaitUntil and nowMs() < W._homeWaitUntil then setStatus(m, "waiting", "no_path"); return end
    newJob(m, { op = "home", key = "home", phase = "gohome" })
    setStatus(m, "doing", "home")
end
-- what she still owes after he ended the work: put back on her own only when he has left her be for a while and both of them are near it
function W.settleOwed(m)
    if #m.owed == 0 or m.duty == true then return end
    local a = actor()
    if a == nil or call(a, "getVehicle") ~= nil or danger(a) then return end
    local st = orderState(a)
    local serial = st and tonumber(st.commandSerial) or nil
    local now = nowMs()
    if serial ~= m.settleSerial or m.settleAfter == nil then m.settleSerial, m.settleAfter = serial, now + SETTLE_QUIET_MS; return end
    if now < tonumber(m.settleAfter) then return end
    local v = view()
    local here, plr = v.posOf(a), v.posOf(player())
    local o = m.owed[1]
    if here == nil or plr == nil or math.max(math.abs(here.x - o.x), math.abs(here.y - o.y)) > SETTLE_TILES or math.max(math.abs(plr.x - o.x), math.abs(plr.y - o.y)) > SETTLE_TILES then return end
    local ok = W.enterDuty(a, m, true)
    if not ok then return end
    m.settling = true
    if not startReturn(m, a) then W.releaseDuty(m) end
end

-- one thought per slice: one job at a time, needs first, any order from him ends it
function W.tick(remainingMs)
    local m = store()
    if m == nil then return end
    W._tickAt = nowMs()
    if not W.engaged(m) and m.modes.home ~= true and m.settling ~= true then W.settleOwed(m); return end
    if m.duty == true and W._sessionDuty ~= true then                       -- back from a save: what Living Fellows reads as the last order is taken again
        local a0 = actor()
        local st = a0 and orderState(a0) or nil
        if st then m.dutyOrder, m.cmdSerial = st.order, tonumber(st.commandSerial); W._sessionDuty = true end
    end
    local a = actor()
    if a == nil then
        local j = m.job
        if j then
            local now = nowMs()
            j.spent = (tonumber(j.spent) or 0) + math.min(math.max(0, now - (tonumber(j.last) or now)), MAX_STEP_MS)
            j.last = now
            if j.spent > BODY_LOST_MS then failJob(m, nil, "body_lost") else setStatus(m, "waiting", "body_lost") end
        end
        return
    end
    local gu = GU()
    if gu and type(gu.isDead) == "function" and tcall(gu.isDead, a) == true then return end
    if m.duty == true and not W.dutyOk(a, m) then
        W.stopAll(m, "order")
        return
    end
    refreshPaused(m)
    local k = keeper()
    if k and k.tick then pcall(k.tick, a, m) end
    if danger(a) then
        if m.job then pauseJob(m, m.job, a) end
        setStatus(m, "waiting", "unsafe_area")
        say(m, "danger", "waiting", { why = "unsafe_area" })
        return
    end
    if m.job then
        if m.statusDetail == "unsafe_area" then setStatus(m, "doing", m.job.op) end
        jobStep(m, a)
        if m.job then return end
    end
    if m.settling == true then
        if not (#m.owed > 0 and startReturn(m, a)) then W.releaseDuty(m) end
        return
    end
    if m.modes.home == true and m.modes.farm ~= true and m.filter == nil then return W.homeTick(m, a, k) end
    if not W.engaged(m) then return end
    if m.filter and m.filter.kind == "trial" then
        if #m.owed > 0 and startReturn(m, a) then return end
        setStatus(m, "finished", "trial")
        m.filter = nil
        W.endSingle(m)
        sync()
        return
    end
    local v = view()
    local need = k and k.bodyNeed and k.bodyNeed(a) or nil
    if need and (m.filter == nil or need == "health") then setStatus(m, "needs", need); return end       -- a single order he just gave does not wait for a wash
    if #v.zones() == 0 then
        if m.filter then return W.finishSingle(m, "base_missing") end
        setStatus(m, "waiting", "base_missing")
        return
    end
    local stock = v.stockLatest
    if not v.scanComplete() or not stock.ready then
        if m.filter then
            m.filter.waiting = tonumber(m.filter.waiting) or nowMs()
            if nowMs() - m.filter.waiting > SCAN_WAIT_MS then return W.finishSingle(m, "timeout") end
        end
        setStatus(m, "scanning")
        return
    end
    local env = W.env(a)
    env.produce = produceInBag(a)
    local ctx = { filter = m.filter and m.filter.kind or nil, crop = m.filter and m.filter.crop or nil, paused = m.paused,
        land = v.pruneLand(),
        noteUnclearable = function(p)
            local key = P.key(p)
            if not m.unclearable[key] then
                m.unclearable[key] = true
                m.unclearableCount = (tonumber(m.unclearableCount) or 0) + 1
                say(m, "weeds_stuck", "unclearable_weeds", { x = p.x, y = p.y }, true)
            end
        end }
    local t, blocked, want = P.next(v.allPlants(), stock, env, ctx)
    if t == nil then
        if want and want.land and m.filter and m.filter.landDone ~= true then         -- a single order waits for the look at the land before it can say it is finished
            if v._landBusy() then setStatus(m, "scanning"); return end
            if m.filter.landAsked then m.filter.landDone = true
            else
                m.filter.landAsked = true
                v.requestLand(NEW_LAND_WANT)
                setStatus(m, "scanning")
                return
            end
        elseif want and want.land and m.filter == nil and (m.landAt == nil or nowMs() - m.landAt > LAND_RETRY_MS) and not v._landBusy() then
            m.landAt = nowMs()
            v.requestLand(NEW_LAND_WANT)
        end
        if m.filter and m.filter.kind == "harvest" and not m.filter.carried and produceInBag(a) > 0 then      -- the harvest is not left in her bag
            m.filter.carried = true
            if startCarry(m, a) then return end
        end
        if #m.owed > 0 and startReturn(m, a) then return end
        if m.filter then return W.finishSingle(m, W.topReason(blocked)) end
        local why = W.topReason(blocked)
        setStatus(m, why and "waiting" or "idle", why)
        if why and why ~= "paused" and why ~= "near_player" and why ~= "unclearable_weeds" then say(m, "wait:" .. why, "waiting", { why = why }) end
        return
    end
    if m.filter then m.filter.landAsked, m.filter.landDone = nil, nil end
    if #m.owed > 0 and not usesOwed(m, t) and not (type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("farm_keep_tools") == true) and startReturn(m, a) then return end
    local ok, why = issue(m, t, a)
    if not ok and why ~= "changed" and t.op ~= "carry" then say(m, "issue:" .. tostring(why), "blocked", { op = t.op, why = why }) end
end

-- ---------------------------------------------------------------- memory: what she planted and when it will be ready
function W.dueList()
    local v = view()
    local S = v.sfs()
    local now = S and tonumber(S.hoursElapsed) or nil
    local props = v.props()
    local byKey, out = {}, {}
    for _, p in ipairs(v.allPlants()) do
        if alive(p) and not p.veg and p.crop and now ~= nil and p.nextG ~= nil then
            local pr = props[p.crop]
            local level = pr and tonumber(pr.harvestLevel)
            if level then
                local hours = math.max(0, p.nextG - now) + math.max(0, level - p.nb - 1) * (tonumber(pr.timeToGrow) or 0)
                local key = tostring(p.zoneId) .. "|" .. p.crop
                if byKey[key] == nil or hours < byKey[key].hours then byKey[key] = { zone = p.zoneId, crop = p.crop, hours = hours, veg = pr.vegetableName } end
            end
        end
    end
    for _, row in pairs(byKey) do out[#out + 1] = row end
    table.sort(out, function(a, b) return a.hours < b.hours end)
    return out
end
function W.seasonNews()
    local v = view()
    if not v.seasonsOn() then return {} end
    local month = v.month()
    if not month then return {} end
    local nextMonth = month % 12 + 1
    local out = {}
    for crop, count in pairs(v.stockLatest.seeds or {}) do
        if count > 0 then
            local p = v.props()[crop]
            if type(p) == "table" and type(p.sowMonth) == "table" then
                local now_, next_ = false, false
                for _, mo in ipairs(p.sowMonth) do
                    if mo == month then now_ = true end
                    if mo == nextMonth then next_ = true end
                end
                if now_ and not next_ then out[#out + 1] = { crop = crop, kind = "ending", seed = (p.seedTypes and p.seedTypes[1]) or p.seedName } end
                if next_ and not now_ then out[#out + 1] = { crop = crop, kind = "soon", seed = (p.seedTypes and p.seedTypes[1]) or p.seedName } end
            end
        end
    end
    return out
end
-- "forget the tries": only what she learned from sol_farm_try
function W.forgetTries()
    local m = store()
    if m == nil then return end
    m.proven = {}
    sync()
end
-- she died: the work ends, nothing of it survives, and she is not held for anything
function W.died()
    local m = store()
    if m == nil then return end
    if m.job then pcall(stopBody, nil, actor()) end
    m.sown, m.said, m.unclearable, m.paused, m.fails, m.unclearableCount, m.owed, m.proven = {}, {}, {}, {}, {}, 0, {}, {}
    m.job, m.stop, m.filter, m.duty, m.prevOrder, m.walked, m.settling, m.atHome, m.settleAfter, m.settleSerial, m.walkGoal = nil, nil, nil, false, nil, nil, nil, nil, nil, nil, nil
    m.modes.farm, m.modes.home = false, false
    m.statusText, m.statusDetail = nil, nil
    W._jobLive = nil
    sync()
    log("she died: the farm work and what she knew of it are gone")
end
rawset(_G, "solFarmForget", function() W.died() end)

function W.snapshot()
    local m = store()
    if m == nil then return nil end
    local v = view()
    local counts = v.counts()
    local ripe, thirsty = 0, 0
    for _, c in ipairs(counts) do ripe = ripe + (tonumber(c.ripe) or 0); thirsty = thirsty + (tonumber(c.thirsty) or 0) end
    return { mode = { farm = m.modes.farm == true, home = m.modes.home == true }, status = m.statusText, detail = m.statusDetail,
        stop = m.stop, stops = m.stops, seq = tonumber(m.seq) or 0, zones = counts, ripe = ripe, thirsty = thirsty,
        sown = m.sown, due = W.dueList(), season = W.seasonNews(), raining = v.raining(), unclearable = tonumber(m.unclearableCount) or 0, rev = v.rev }
end

-- ---------------------------------------------------------------- orders
function W.stopAll(m, reason)
    m = m or store()
    if m == nil then return end
    W.cancelJob(m)
    m.filter, m.modes.farm, m.modes.home, m.duty, m.settling, m.atHome = nil, false, false, false, nil, nil
    m.settleAfter = nil
    setStatus(m, "stopped", reason)
    local k = keeper()
    if k and k.onStop then pcall(k.onStop, reason) end
    sync()
end

local function enabled()
    local A = g("SolAuthority")
    if type(A) ~= "table" or type(A.on) ~= "function" then return true end
    local ok, on = pcall(A.on, "sol_farm")
    return ok and on == true
end

-- the line "sol_farm storage" answers: what the whole-base scan sees, one row per place, by what it is good for
function W.storageSeen()
    local v = view()
    local regs, seen = {}, {}
    local function add(cat, r, what)
        local key = cat .. "@" .. tostring(r.x) .. "," .. tostring(r.y)
        if seen[key] or #regs >= 60 then return end
        seen[key] = true
        regs[#regs + 1] = key .. "," .. tostring(what or "")
    end
    for _, r in ipairs(v.spots) do
        if r.where == "house" and r.x ~= nil then
            if r.kind == "tool" then add("tools", r, "tool") add("farming", r, "tool")
            elseif r.kind == "can" then add("water", r, "can")
            else add("farming", r, r.kind) end
        end
    end
    for _, p in ipairs(v.places) do
        add(p.score >= 3 and "food" or "output", p, p.kind)
        add("output", p, p.kind)
    end
    return "scan;regs=" .. table.concat(regs, "|") .. ";cls=unloaded:" .. tostring(v.stockLatest.unloaded or 0)
end

function W.report()
    local v = view()
    local a = actor()
    local env = nil
    if a then
        local okEnv, read = pcall(W.env, a)
        if okEnv then env = read else log("report: could not read her side of it: " .. tostring(read)) end
    end
    local plants = v.allPlants()
    local out = { zones = v.counts(), complete = v.scanComplete(), stock = v.stockLatest, rev = v.rev }
    if env then
        out.shortages = P.shortages(plants, v.stockLatest, env)
        local crops = {}
        for crop in pairs(v.stockLatest.seeds or {}) do crops[#crops + 1] = crop end
        out.seedNames = {}
        for crop, row in pairs(v.props()) do if type(row) == "table" then out.seedNames[crop] = (type(row.seedTypes) == "table" and row.seedTypes[1]) or row.seedName end end
        table.sort(crops)
        out.inSeason = {}
        for _, crop in ipairs(crops) do out.inSeason[#out.inSeason + 1] = { crop = crop, ok = env.inSeason(crop), seed = v.stockLatest.seeds[crop] } end
    end
    local m = store()
    if m then out.modes, out.status, out.detail, out.stop = { farm = m.modes.farm == true, home = m.modes.home == true }, m.statusText, m.statusDetail, m.stop end
    out.names = {}
    for crop, row in pairs(v.props()) do if type(row) == "table" then out.names[crop] = row.vegetableName end end
    return out
end

local function js(t)
    if type(U.jsonEncode) ~= "function" then return "{}" end
    local ok, s = pcall(U.jsonEncode, t)
    if not ok then return "{}" end
    return s
end

function U.solFarmOrder(option)
    local opt = tostring(option or "")
    local cmd, arg = opt:match("^(%w+):?(.*)$")
    cmd = cmd or opt
    local a = actor()
    if cmd == "report" then
        local okReport, out = pcall(W.report)
        if not okReport then log("report failed: " .. tostring(out)); return false, "report_failed" end
        return true, "farm:" .. js(out)
    end
    if cmd == "status" then
        local m = store()
        return m ~= nil, "status:" .. js({ status = m and m.statusText, detail = m and m.statusDetail, modes = m and m.modes, job = m and m.job, stop = m and m.stop })
    end
    if cmd == "proven" then
        local m = store()
        return true, "proven:" .. js(m and m.proven or {})
    end
    if cmd == "forget" then W.forgetTries(); return true, "forgotten" end
    if not enabled() then return false, "switched_off" end
    if a == nil then return false, "sol_not_available" end
    local v = view()
    v.forceRescan()
    local m = store()
    if m == nil then return false, "store_unavailable" end
    if cmd == "stop" or cmd == "interrupt" then
        local was = m.modes.farm or m.modes.home or m.filter ~= nil or m.job ~= nil
        local walked, prev = m.walked, m.prevOrder
        W.stopAll(m, "player_order")
        if cmd == "stop" then m.walked, m.prevOrder = walked, prev end        -- an interrupt is followed at once by his next order
        W.releaseDuty(m, cmd ~= "stop")
        return true, was and "stopped" or "nothing_running"
    end
    if (cmd == "short" or cmd == "storage") and not (type(v.stockLatest) == "table" and v.stockLatest.ready == true) then return true, "not_ready" end
    if cmd == "short" then return true, "short:" .. js(P.shortages(v.allPlants(), v.stockLatest, W.env(a))) end
    if cmd == "storage" then return true, "storage:" .. W.storageSeen() end       -- nothing is registered any more: only what the scan sees
    local k = keeper()
    if cmd == "keeper" or cmd == "home" or cmd == "both" then
        local ok, why = k.set(cmd == "home" and "home" or "farm", a, m)
        if ok and cmd == "both" then ok, why = k.set("home", a, m) end
        sync()
        return ok, why
    end
    if cmd == "water" or cmd == "harvest" or cmd == "plant" or cmd == "cure" or cmd == "compost" or cmd == "weed" or cmd == "plow" then
        local crop = (arg ~= "" and arg ~= "any") and arg or nil
        if v.scanComplete() and v.stockLatest.ready and m.job == nil then             -- nothing to do: said now, she does not set out
            local env = W.env(a)
            local t, blocked, want = P.next(v.allPlants(), v.stockLatest, env, { filter = cmd, crop = crop, paused = m.paused, land = v.pruneLand() })
            if t == nil and not (want and want.land) then
                local why = W.topReason(blocked)
                return true, "single:" .. cmd .. ":none" .. (why and (":" .. why) or "")
            end
        end
        local ok, why = W.enterDuty(a, m)
        if not ok then return false, why end
        W.cancelJob(m, a)
        m.filter = { kind = cmd, crop = crop }
        setStatus(m, "doing", cmd)
        sync()
        return true, "single:" .. cmd
    end
    return false, "unknown_farm_order"
end

function U.solFarmTry(op)
    local act = g("SolFarmAct")
    if type(act) ~= "table" or type(act.trial) ~= "function" then return false, "act_unavailable" end
    return act.trial(tostring(op or ""))
end

function W.tickAll(remainingMs)
    local v, ok = view(), nil
    local budget = tonumber(remainingMs) or 2
    if v and v.tick then ok = pcall(v.tick, budget) end
    pcall(W.tick, budget)
end

function W.install()
    if W._installed then return end
    W._installed = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "sol_farm" then return U.solFarmOrder(option) end
        if id == "sol_farm_try" then return U.solFarmTry(option) end
        return base(id, option)
    end
    local budget = g("SolBudget")
    if type(budget) == "table" and type(budget.register) == "function" then
        budget.register("sol_farm", W.tickAll, { everyMs = TICK_MS, priority = 5 })
    elseif Events and Events.OnTick then
        local nextAt = 0
        Events.OnTick.Add(function()
            local t = nowMs()
            if t < nextAt then return end
            nextAt = t + 500
            pcall(W.tickAll, 2)
        end)
    end
    log("ready v" .. W.VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(W.install) end
return W

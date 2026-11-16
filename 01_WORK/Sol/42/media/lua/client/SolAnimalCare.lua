-- SolAnimalCare.lua - switch animal_care. Sol looks after the animals of the home's animal zone: water and feed in the troughs,
-- eggs out of the hutch nest boxes and into the kitchen. One step at a time, each checked from the game's own state.
-- Sources (game 42.22.2, read-only): IsoFeedingTrough (getWater/getMaxWater/getCurrentFeedAmount/getMaxFeed/onFoodAdded),
-- ISAddWaterToTrough.lua (water goes through SFeedingTroughSystem's lua object addWater, not the iso object),
-- ISFeedingTroughMenu.lua (a trough holds food or water, never both), IsoHutch / IsoHutch$NestBox (getEggsNb/getEgg/removeEgg),
-- ISHutchGrabEgg.lua (removeEgg then AddItem), DesignationZoneAnimal.getZone + getTroughsConnected/getHutchsConnected.
-- The vanilla timed actions use getPlayerNum()/getPlayerLoot(), which a companion has not, so the same calls are made here directly.
-- Verb: sol_animals care | eggs | stop | status.   The Mind words every answer.
SolUI = SolUI or {}
local U = SolUI
SolAnimalCare = SolAnimalCare or {}
local M = SolAnimalCare
M.VERSION = "0.1.0"
M.ROUND_MS = 60000          -- a keeper looks again once a minute
M.WALK_MS = 60000           -- one walk may take this long
M.WATER_BELOW = 0.5         -- top up a water trough under half
M.FEED_BELOW = 0.5          -- feed a food trough under half
M.KEEP_FERTILIZED = true    -- a fertilized egg stays for the hen to hatch
M.EGG_TYPES = { ["Base.Egg"] = true, ["Base.TurkeyEgg"] = true }
M.KITCHEN_KINDS = { fridge = 1, freezer = 2, counter = 3, overhead = 4 }

local function log(m) print("[SolAnimalCare] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or 0 end
local function g(name) return rawget(_G, name) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a, b = pcall(f, o, ...)
    if ok then return a end                               -- one value only: a second value passed to tonumber becomes its base (Kahlua crash)
    return nil
end
local function on()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("animal_care") == true
end
local function actor() return type(U.solActor) == "function" and U.solActor() or nil end
local function LF() local sc = g("SurvivorCompanion"); return type(sc) == "table" and sc or nil end
local function GU() local sc = LF(); return sc and type(sc.GameplayUtil) == "table" and sc.GameplayUtil or nil end
local function nav() local sc = LF(); return sc and type(sc.Navigation) == "table" and sc.Navigation or nil end
local function list(jl) local out = {}; local n = jl and call(jl, "size") or 0; for i = 0, (n or 0) - 1 do out[#out + 1] = call(jl, "get", i) end; return out end
local function fullType(item) return tostring(call(item, "getFullType") or "") end

M.state = M.state or { keeper = false, job = nil, nextRound = 0, last = nil, said = {} }
local S = M.state

-- ---------------------------------------------------------------- what is there
function M.homePoint(a)
    local H = g("SolHome")
    local h = H and type(H.get) == "function" and H.get() or nil
    if type(h) == "table" and h.x then return h.x, h.y, h.z or 0 end
    if a then return math.floor(call(a, "getX") or 0), math.floor(call(a, "getY") or 0), math.floor(call(a, "getZ") or 0) end
    return nil
end

function M.zoneAt(x, y, z)
    local Z = g("DesignationZoneAnimal")
    if not Z or x == nil then return nil end
    local ok, zone = pcall(Z.getZone, x, y, z)
    return ok and zone or nil
end

-- the animal zone that serves the home: at Sol, at home, or the nearest one within reach of home
function M.findZone(a)
    local zone = a and M.zoneAt(math.floor(call(a, "getX") or 0), math.floor(call(a, "getY") or 0), math.floor(call(a, "getZ") or 0))
    if zone then return zone end
    local x, y, z = M.homePoint(a)
    zone = M.zoneAt(x, y, z)
    if zone then return zone end
    local Z = g("DesignationZoneAnimal")
    local all = Z and type(Z.getAllZones) == "function" and select(2, pcall(Z.getAllZones)) or nil
    local best, bestD
    for _, zz in ipairs(list(all)) do
        local zx, zy = call(zz, "getX"), call(zz, "getY")
        if zx and x then
            local d = math.max(math.abs(zx - x), math.abs(zy - y))
            if d <= 60 and (bestD == nil or d < bestD) then best, bestD = zz, d end
        end
    end
    return best
end

local function master(t) return call(t, "getMasterTrough") or t end

function M.troughState(t)
    local water, maxW = tonumber((call(t, "getWater"))) or 0, tonumber((call(t, "getMaxWater"))) or 0
    local feed, maxF = tonumber((call(t, "getCurrentFeedAmount"))) or 0, tonumber((call(t, "getMaxFeed"))) or 0
    local cont = call(t, "getContainer")
    local items = cont and tonumber((call(call(cont, "getItems"), "size"))) or 0
    return { water = water, maxWater = maxW, feed = feed, maxFeed = maxF, foodItems = items }
end

-- One trough, one need, from the rule that a trough holds food or water: water in it -> keep it a water trough; food in it -> keep it a food trough;
-- empty -> water if the zone has no water trough yet, else food.
function M.troughNeed(st, zoneHasWater)
    if st.water > 0 or (st.foodItems == 0 and not zoneHasWater) then
        if st.maxWater > 0 and st.water < st.maxWater * M.WATER_BELOW then return "water" end
        return nil
    end
    if st.maxFeed > 0 and st.feed < st.maxFeed * M.FEED_BELOW then return "feed" end
    return nil
end

function M.eggsIn(hutch)
    local n, eggs = tonumber((call(hutch, "getMaxNestBox"))) or 0, 0
    for i = 0, n - 1 do
        local box = call(hutch, "getNestBox", i)
        local k = box and tonumber((call(box, "getEggsNb"))) or 0
        for j = 0, k - 1 do
            local egg = call(box, "getEgg", j)
            if egg and not (M.KEEP_FERTILIZED and call(egg, "isFertilized") == true) then eggs = eggs + 1 end
        end
    end
    return eggs
end

-- the list of jobs, most urgent first: water, feed, then eggs
function M.plan(zone, eggsOnly)
    local jobs, seen, troughs, hasWater = {}, {}, {}, false
    for _, t in ipairs(list(call(zone, "getTroughsConnected"))) do
        local m = master(t)
        if m and not seen[m] then seen[m] = true; troughs[#troughs + 1] = m; if (tonumber((call(m, "getWater"))) or 0) > 0 then hasWater = true end end
    end
    if not eggsOnly then
        for _, t in ipairs(troughs) do
            local need = M.troughNeed(M.troughState(t), hasWater)
            if need == "water" then table.insert(jobs, 1, { op = "water", target = t }) ; hasWater = true
            elseif need == "feed" then jobs[#jobs + 1] = { op = "feed", target = t } end
        end
    end
    for _, h in ipairs(list(call(zone, "getHutchsConnected"))) do
        if M.eggsIn(h) > 0 then jobs[#jobs + 1] = { op = "eggs", target = h } end
    end
    return jobs, #troughs
end

-- ---------------------------------------------------------------- supplies
function M.isWaterVessel(item)
    local fc = call(item, "getFluidContainer")
    if not fc or call(fc, "isEmpty") == true then return false end
    local water = g("Fluid") and Fluid.Water
    if water and call(fc, "contains", water) ~= true then return false end
    return (tonumber((call(fc, "getPrimaryFluidAmount"))) or 0) > 0.05
end

function M.isFeed(item)
    local kind = call(item, "getAnimalFeedType")
    return kind ~= nil and tostring(kind) ~= ""
end

local function predicateFor(op) if op == "water" then return M.isWaterVessel end if op == "feed" then return M.isFeed end end

local function itemsOf(cont, deep)
    local gu = GU()
    if gu and type(gu.inventoryItemsDeep) == "function" then
        local ok, items = pcall(gu.inventoryItemsDeep, cont, 180, deep and 12 or 1)
        if ok and type(items) == "table" then return items end
    end
    return list(call(cont, "getItems"))
end

function M.bagFind(a, pred)
    for _, item in ipairs(itemsOf(call(a, "getInventory"), true)) do if pred(item) then return item end end
end

local function placeContainer(p)
    local gu = GU()
    local sq = gu and type(gu.gridSquare) == "function" and gu.gridSquare(p.x, p.y, p.z) or (getCell and getCell():getGridSquare(p.x, p.y, p.z))
    local obj = sq and call(call(sq, "getObjects"), "get", p.oi)
    return obj and call(obj, "getContainerByIndex", p.ci or 0) or nil, sq
end

-- the nearest home container that holds a matching item (SolInventory's last scan of the home)
function M.homeFind(pred, fromX, fromY)
    local last = type(U.invLast) == "function" and U.invLast() or nil
    local best
    for _, p in ipairs(last and last.places or {}) do
        local d = fromX and math.max(math.abs(p.x - fromX), math.abs(p.y - fromY)) or 0
        if best == nil or d < best.d then
            local cont, sq = placeContainer(p)
            if cont then
                for _, item in ipairs(itemsOf(cont, false)) do
                    if pred(item) then best = { d = d, cont = cont, sq = sq, item = item }; break end
                end
            end
        end
    end
    return best
end

function M.kitchen(fromX, fromY, egg, a)
    local last = type(U.invLast) == "function" and U.invLast() or nil
    local best
    for _, p in ipairs(last and last.places or {}) do
        local rank = M.KITCHEN_KINDS[p.kind]
        if rank and (p.kind ~= "counter" and p.kind ~= "overhead" or tostring(p.room or "") == "kitchen") then
            local cont, sq = placeContainer(p)
            local powered = (p.kind ~= "fridge" and p.kind ~= "freezer") or call(cont, "isPowered") == true
            if cont and powered and call(cont, "hasRoomFor", a, egg) ~= false then
                local d = fromX and math.max(math.abs(p.x - fromX), math.abs(p.y - fromY)) or 0
                local score = rank * 1000 + d
                if best == nil or score < best.score then best = { score = score, cont = cont, sq = sq } end
            end
        end
    end
    return best
end

-- ---------------------------------------------------------------- doing it (single player: the server lua runs in the same game)
function M.addWater(trough, vessel)
    local fc = call(vessel, "getFluidContainer")
    local have = tonumber((call(fc, "getPrimaryFluidAmount"))) or 0
    local space = (tonumber((call(trough, "getMaxWater"))) or 0) - (tonumber((call(trough, "getWater"))) or 0)
    local n = math.min(have, space)
    if n <= 0.01 then return false, "nothing_to_pour" end
    local sys = g("SFeedingTroughSystem")
    local lo = sys and sys.instance and sys.instance:getLuaObjectAt(call(trough, "getX"), call(trough, "getY"), call(trough, "getZ")) or nil
    if not lo then return false, "trough_not_in_system" end
    local before = tonumber((call(trough, "getWater"))) or 0
    pcall(fc.removeFluid, fc, n, false)
    lo:addWater(n)
    local after = tonumber((call(trough, "getWater"))) or 0
    if after <= before then return false, "water_not_taken" end
    return true, string.format("%.1f", after - before)
end

function M.addFeed(trough, item, a)
    local tc = call(trough, "getContainer")
    if not tc then call(trough, "checkContainer"); tc = call(trough, "getContainer") end
    if not tc then return false, "no_trough_container" end
    local before = tonumber((call(trough, "getCurrentFeedAmount"))) or 0
    local gu = GU()
    local from = call(item, "getContainer") or call(a, "getInventory")
    local moved = gu and type(gu.transferItemVerified) == "function" and gu.transferItemVerified(from, tc, item) == true
    if not moved then return false, "move_refused" end
    call(trough, "onFoodAdded")
    local after = tonumber((call(trough, "getCurrentFeedAmount"))) or 0
    if after <= before then return false, "feed_not_counted" end
    return true, string.format("%.1f", after - before)
end

function M.takeEggs(hutch, a)
    local inv, taken = call(a, "getInventory"), {}
    local n = tonumber((call(hutch, "getMaxNestBox"))) or 0
    for i = 0, n - 1 do
        local box = call(hutch, "getNestBox", i)
        local k = box and tonumber((call(box, "getEggsNb"))) or 0
        for j = k - 1, 0, -1 do
            local egg = call(box, "getEgg", j)
            if egg and not (M.KEEP_FERTILIZED and call(egg, "isFertilized") == true) then
                local got = call(box, "removeEgg", j)
                if got then call(inv, "AddItem", got); taken[#taken + 1] = got end
            end
        end
    end
    call(hutch, "sync")
    return taken
end

-- ---------------------------------------------------------------- walking (the same rule as the farm: arrived when she stands where it can be reached)
function M.walk(j, a, sq)
    local n = nav()
    if not (n and type(n.interactionTargets) == "function" and type(U.solGoto) == "function") then return "failed" end
    j.walkFrom = j.walkFrom or nowMs()
    if nowMs() - j.walkFrom > M.WALK_MS then return "failed" end
    local ok, targets = pcall(n.interactionTargets, a, sq, { maximum = 8 })
    local SP = g("SolPlace")                                                   -- spatial_access: only squares on the animal's own side
    if ok and type(SP) == "table" and type(SP.on) == "function" and SP.on() then
        local okS, own = pcall(SP.standSquares, sq)
        if okS and type(own) == "table" and #own > 0 then targets = own end
    end
    if not ok or type(targets) ~= "table" or #targets == 0 then return "failed" end
    local px, py, pz = math.floor(call(a, "getX") or -1), math.floor(call(a, "getY") or -1), math.floor(call(a, "getZ") or 0)
    for _, s in ipairs(targets) do
        if call(s, "getX") == px and call(s, "getY") == py and call(s, "getZ") == pz then j.walkFrom, j.sent = nil, nil; return "arrived" end
    end
    if j.sent == nil or nowMs() - j.sent > 3000 then
        local t = targets[1]
        pcall(U.solGoto, call(t, "getX"), call(t, "getY"), call(t, "getZ"))
        j.sent = nowMs()
    end
    return "walking"
end

-- ---------------------------------------------------------------- the runner
local function say(key, text)
    S.last = { key = key, text = text, at = nowMs() }
    log(key .. (text and (" " .. text) or ""))
end

function M.start(eggsOnly, a)
    a = a or actor()
    if not a then return false, "no_sol" end
    local zone = M.findZone(a)
    if not zone then say("no_zone"); return false, "no_animal_zone" end
    if type(U.invLast) == "function" and U.invLast() == nil and type(U.invStart) == "function" then pcall(U.invStart) end   -- the home's containers, for feed, water and the kitchen
    local jobs, troughs = M.plan(zone, eggsOnly)
    S.queue, S.zone = jobs, zone
    S.done = S.done or { water = 0, feed = 0, eggs = 0 }                -- counted from his order; a keeper's later rounds add to it
    if #jobs == 0 then say("nothing_to_do", "troughs=" .. tostring(troughs)); return true, "nothing_to_do" end
    S.job = table.remove(S.queue, 1)
    S.job.phase = "fetch"
    say("start", S.job.op .. " +" .. tostring(#S.queue))
    return true, "started:" .. S.job.op
end

function M.held() return S.job ~= nil end
U.solAnimalsHeld = M.held

local function finish(j, ok, why)
    say((ok and "done " or "failed ") .. j.op, why)
    if ok then S.done[j.op] = (S.done[j.op] or 0) + 1 end
    S.job = S.queue and table.remove(S.queue, 1) or nil
    if S.job then S.job.phase = "fetch" end
end

function M.step(a)
    local j = S.job
    if not j then return end
    if j.phase == "fetch" then
        if j.op == "eggs" then j.phase = "go"; return end
        local pred = predicateFor(j.op)
        j.item = M.bagFind(a, pred)
        if j.item then j.phase = "go"; return end
        local tx, ty = call(j.target, "getX"), call(j.target, "getY")
        local src = M.homeFind(pred, tx, ty)
        if not src then return finish(j, false, j.op == "water" and "no_water_vessel" or "no_animal_feed") end
        j.src, j.phase = src, "to_source"
    elseif j.phase == "to_source" then
        local w = M.walk(j, a, j.src.sq)
        if w == "failed" then return finish(j, false, "cannot_reach_supply") end
        if w ~= "arrived" then return end
        local gu = GU()
        local ok = gu and type(gu.transferItemVerified) == "function" and gu.transferItemVerified(j.src.cont, call(a, "getInventory"), j.src.item) == true
        if not ok then return finish(j, false, "take_refused") end
        j.item, j.phase = j.src.item, "go"
    elseif j.phase == "go" then
        local sq = j.op == "eggs" and (call(j.target, "getEntrySq") or call(j.target, "getSquare")) or call(j.target, "getSquare")
        local w = M.walk(j, a, sq)
        if w == "failed" then return finish(j, false, "cannot_reach") end
        if w ~= "arrived" then return end
        if j.op == "water" then return finish(j, M.addWater(j.target, j.item)) end
        if j.op == "feed" then return finish(j, M.addFeed(j.target, j.item, a)) end
        j.eggs = M.takeEggs(j.target, a)
        if #j.eggs == 0 then return finish(j, false, "no_eggs_taken") end
        local k = M.kitchen(call(a, "getX"), call(a, "getY"), j.eggs[1], a)
        if not k then return finish(j, true, "eggs_kept_on_her:" .. #j.eggs) end
        j.kitchen, j.phase = k, "to_kitchen"
    elseif j.phase == "to_kitchen" then
        local w = M.walk(j, a, j.kitchen.sq)
        if w == "failed" then return finish(j, true, "eggs_kept_on_her:" .. #j.eggs) end
        if w ~= "arrived" then return end
        local gu, put = GU(), 0
        for _, egg in ipairs(j.eggs) do
            if gu and gu.transferItemVerified(call(egg, "getContainer") or call(a, "getInventory"), j.kitchen.cont, egg) == true then put = put + 1 end
        end
        finish(j, put > 0, "eggs_stored:" .. put .. "/" .. #j.eggs)
    end
end

function M.tick()
    if not on() then if S.job then S.job, S.queue = nil, nil end return end
    local a = actor()
    if not a then return end
    if S.job then local ok, err = pcall(M.step, a); if not ok then log("error " .. tostring(err)); S.job, S.queue = nil, nil end return end
    if S.keeper and nowMs() >= S.nextRound then S.nextRound = nowMs() + M.ROUND_MS; pcall(M.start, false, a) end
end

function M.order(option)
    if not on() then return false, "switch_off" end
    option = tostring(option or "")
    if option == "stop" then
        S.keeper, S.job, S.queue = false, nil, nil
        return true, "stopped"
    end
    if option == "status" then
        local d = S.done or {}
        return true, string.format("keeper=%s job=%s water=%d feed=%d eggs=%d last=%s", tostring(S.keeper), S.job and S.job.op or "none",
            d.water or 0, d.feed or 0, d.eggs or 0, S.last and (S.last.key .. " " .. tostring(S.last.text or "")) or "-")
    end
    if option == "care" then S.keeper = true; S.nextRound = nowMs() + M.ROUND_MS; S.done = nil; return M.start(false) end
    if option == "eggs" then S.done = nil; return M.start(true) end
    return false, "unknown_option"
end

function M.install()
    if M._installed then return end
    M._installed = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "sol_animals" then return M.order(option) end
        return base(id, option)
    end
    local budget = g("SolBudget")
    if type(budget) == "table" and type(budget.register) == "function" then
        budget.register("sol_animals", function() pcall(M.tick) end, { everyMs = 500, priority = 5 })
    elseif Events and Events.OnTick then
        local nextAt = 0
        Events.OnTick.Add(function() local t = nowMs(); if t < nextAt then return end; nextAt = t + 500; pcall(M.tick) end)
    end
    log("ready v" .. M.VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(M.install) end
return M

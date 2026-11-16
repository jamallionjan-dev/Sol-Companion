-- SolWorldScan.lua - what Sol knows about the world: both characters' state, every reachable inventory
-- (player, Sol, nearby containers, vehicle parts), food freshness, fluids, plants, animals, time, weather,
-- utility shut-off. Written as JSON (ASCII, \uXXXX escapes) to SolWorld_Snapshot.txt for Sol Mind.
-- Only APIs found in Project Zomboid 42.21's own Lua are used directly; anything else is called guarded.
require "SolText"
local SolScanCoordinator = require "SolScanCoordinator"
SolUI = SolUI or {}
local U = SolUI
local T = SolText
U.SCAN_VERSION = "0.3.2"
local FILE = "SolWorld_Snapshot.txt"
local INTERVAL_MS = 60000
local RADIUS, ZSPAN = 15, 1
local MAX_CONTAINERS, MAX_ITEMS = 300, 250
local function log(m) print("[SolWorld] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end

-- guarded method call: returns value or nil (never throws)
local function call(o, name, ...)
    if o == nil then return nil end
    local f = o[name]
    if f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function num(v) if type(v) == "number" and v == v and v ~= math.huge and v ~= -math.huge then return v end return nil end
local function round(v, d) v = num(v); if not v then return nil end local m = 10 ^ (d or 2); return math.floor(v * m + 0.5) / m end

-- ---------------------------------------------------------------- JSON (ASCII only)
local function jstr(s)
    s = tostring(s)
    if not string.find(s, "[^ -~]") and not string.find(s, "[\\\"]") then return '"' .. s .. '"' end   -- plain ASCII: no per-char work
    local cps = T.codepoints(s)
    local out = { '"' }
    for _, cp in ipairs(cps) do
        if cp == 34 then out[#out + 1] = '\\"'
        elseif cp == 92 then out[#out + 1] = "\\\\"
        elseif cp < 32 then out[#out + 1] = " "
        elseif cp < 127 then out[#out + 1] = string.char(cp)
        else out[#out + 1] = "\\u" .. T.hex4(cp % 65536) end
    end
    out[#out + 1] = '"'
    return table.concat(out)
end
local function isArray(t) local n = 0 for _ in pairs(t) do n = n + 1 end return n == #t end
local function encode(v, depth)
    depth = depth or 0
    if depth > 12 then return "null" end
    local tv = type(v)
    if tv == "nil" then return "null"
    elseif tv == "boolean" then return v and "true" or "false"
    elseif tv == "number" then v = num(v); if not v then return "null" end
        if v == math.floor(v) and math.abs(v) < 1e15 then return tostring(math.floor(v)) end
        return tostring(round(v, 4))
    elseif tv == "string" then return jstr(v)
    elseif tv == "table" then
        local parts = {}
        if isArray(v) then
            for i = 1, #v do parts[#parts + 1] = encode(v[i], depth + 1) end
            return "[" .. table.concat(parts, ",") .. "]"
        end
        for k, x in pairs(v) do parts[#parts + 1] = jstr(k) .. ":" .. encode(x, depth + 1) end
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return "null"
end
U.jsonEncode = encode

-- ---------------------------------------------------------------- characters
local STATS = { "HUNGER", "THIRST", "FATIGUE", "ENDURANCE", "STRESS", "PANIC", "PAIN", "BOREDOM", "UNHAPPINESS",
                "WETNESS", "TEMPERATURE", "SICKNESS", "FOOD_SICKNESS", "POISON", "INTOXICATION", "MORALE", "ZOMBIE_INFECTION" }
-- the first 11 are used by the game's own Lua (42.21); the rest are read only if the enum has them
local MOODLES = { "HYPOTHERMIA", "HYPERTHERMIA", "TIRED", "HEAVY_LOAD", "PAIN", "PANIC", "STRESS", "UNHAPPY", "DRUNK", "ENDURANCE", "FOOD_EATEN",
                  "HUNGRY", "THIRST", "WET", "SICK", "INJURED", "BLEEDING", "HAS_A_COLD", "WINDCHILL", "BORED", "ZOMBIE" }
local function charState(c)
    if not c then return nil end
    local s = { x = round(call(c, "getX"), 1), y = round(call(c, "getY"), 1), z = num(call(c, "getZ")) }
    local stats = call(c, "getStats")
    if stats and CharacterStat then
        s.stats = {}
        for _, k in ipairs(STATS) do
            local okE, e = pcall(function() return CharacterStat[k] end)
            if okE and e ~= nil then s.stats[k] = round(call(stats, "get", e), 3) end
        end
    end
    local moodles = call(c, "getMoodles")
    if moodles and MoodleType then
        s.moodles = {}
        for _, k in ipairs(MOODLES) do
            local okE, e = pcall(function() return MoodleType[k] end)
            if okE and e ~= nil then local lv = num(call(moodles, "getMoodleLevel", e)); if lv and lv > 0 then s.moodles[k] = lv end end
        end
    end
    local bd = call(c, "getBodyDamage")
    if bd then
        s.health = round(call(bd, "getOverallBodyHealth"), 1)
        s.infected = call(bd, "IsInfected") == true
        local parts = call(bd, "getBodyParts")
        local wounds = {}
        local n = parts and num(call(parts, "size")) or 0
        for i = 0, n - 1 do
            local bp = call(parts, "get", i)
            local w = {}
            if call(bp, "bleeding") then w[#w + 1] = "bleeding" end
            if call(bp, "bitten") then w[#w + 1] = "bitten" end
            if call(bp, "scratched") then w[#w + 1] = "scratched" end
            if call(bp, "isDeepWounded") then w[#w + 1] = "deep" end
            if call(bp, "getFractureTime") and num(call(bp, "getFractureTime")) and call(bp, "getFractureTime") > 0 then w[#w + 1] = "fracture" end
            if call(bp, "bandaged") then w[#w + 1] = "bandaged" end
            if #w > 0 then wounds[#wounds + 1] = { part = tostring(call(call(bp, "getType"), "toString") or i), state = w } end
        end
        s.wounds = wounds
    end
    local sq = call(c, "getCurrentSquare") or call(c, "getSquare")
    local room = sq and call(sq, "getRoom")
    if room then s.room = call(room, "getName") end
    s.indoors = room ~= nil
    s.inVehicle = call(c, "getVehicle") ~= nil
    local prim = call(c, "getPrimaryHandItem")
    if prim then s.weapon = call(prim, "getDisplayName") end
    s.temperatureAir = getClimateManager and round(call(getClimateManager(), "getAirTemperatureForCharacter", c, false), 1) or nil
    s.temperatureBody = s.stats and s.stats.TEMPERATURE or nil
    -- skills (same list as the skills screen) and who she is
    if PerkFactory and PerkFactory.PerkList then
        local list, sk = PerkFactory.PerkList, {}
        local n = num(call(list, "size")) or 0
        for i = 0, n - 1 do
            local perk = call(list, "get", i)
            local lv = num(call(c, "getPerkLevel", perk))
            if lv and lv > 0 then
                local t = call(perk, "getType")
                sk[tostring(call(t, "name") or call(perk, "getId") or i)] = lv
            end
        end
        s.skills = sk
    end
    local desc = call(c, "getDescriptor")
    if desc then s.profession = call(desc, "getProfession") end
    return s
end

-- ---------------------------------------------------------------- items
local function itemInfo(it)
    do local S_ = rawget(_G, "SolItemStacks"); if type(S_) == "table" and type(S_.cachedRead) == "function" then local d_ = S_.cachedRead(it, "ws"); if d_ ~= nil then return d_ end end end   -- s100 item_stacks
    local d = { type = call(it, "getFullType"), name = call(it, "getDisplayName"), cat = call(it, "getDisplayCategory") or call(it, "getCategory") }
    local fc = call(it, "getFluidContainer")
    if fc and not call(fc, "isEmpty") then
        local fl = call(fc, "getPrimaryFluid")
        d.fluid = { liters = round(call(fc, "getAmount"), 3), kind = fl and tostring(call(fl, "getFluidTypeString") or call(fl, "toString") or "") or nil,
                    poison = fl and call(fl, "isPoisonous") == true or nil }
    end
    if instanceof and instanceof(it, "Food") then
        d.food = { hunger = round(call(it, "getHungerChange") or call(it, "getHungChange"), 3), fresh = call(it, "isFresh"), rotten = call(it, "isRotten"),
                   cooked = call(it, "isCooked"), burnt = call(it, "isBurnt"), frozen = call(it, "isFrozen"),
                   calories = round(call(it, "getCalories"), 1), age = round(call(it, "getAge"), 2),
                   offAge = num(call(it, "getOffAge")), offAgeMax = num(call(it, "getOffAgeMax")) }
    end
    if instanceof and instanceof(it, "DrainableComboItem") then d.uses = round(call(it, "getCurrentUsesFloat"), 3) end
    local cmax = num(call(it, "getConditionMax"))
    if cmax and cmax > 0 then d.cond = round((num(call(it, "getCondition")) or 0) / cmax, 2) end
    do local S_ = rawget(_G, "SolItemStacks"); if type(S_) == "table" and type(S_.remember) == "function" then S_.remember(it, d, "ws") end end   -- s100 item_stacks
    return d
end
local MAX_BAG_DEPTH = 4
local function itemsOf(container)
    -- every item of the container, and of every bag inside it (flattened into one record, 4 levels deep)
    local agg, order, foods, fluids = {}, {}, {}, {}
    local total, cut = 0, false
    local queue, qi = { { container, 0 } }, 1
    while queue[qi] do
        local cont, depth = queue[qi][1], queue[qi][2]
        qi = qi + 1
        local list = call(cont, "getItems")
        local n = list and num(call(list, "size")) or 0
        for i = 0, n - 1 do
            local it = call(list, "get", i)
            if it then
                total = total + 1
                local d = itemInfo(it)
                if d.food or d.fluid then
                    if #foods + #fluids < MAX_ITEMS then
                        if d.food then foods[#foods + 1] = d else fluids[#fluids + 1] = d end
                    else cut = true end
                else
                    local key = tostring(d.type)
                    local a = agg[key]
                    if not a then
                        if #order < MAX_ITEMS then
                            a = { type = d.type, name = d.name, cat = d.cat, count = 0 }
                            agg[key] = a
                            order[#order + 1] = a
                        else cut = true end
                    end
                    if a then
                        a.count = a.count + 1
                        if d.uses then a.uses = round((a.uses or 0) + d.uses, 3) end
                        if d.cond then a.cond = math.min(a.cond or 1, d.cond) end
                    end
                end
                if depth < MAX_BAG_DEPTH and instanceof and instanceof(it, "InventoryContainer") then
                    local inner = call(it, "getInventory")
                    if inner then queue[#queue + 1] = { inner, depth + 1 } end
                end
            end
        end
    end
    return order, foods, fluids, total, cut
end
local seenFor, seenSet = nil, {}
local function addContainer(snap, where, container, extra)
    if not container then return end
    if seenFor ~= snap then seenFor, seenSet = snap, {} end      -- a container is recorded once, wherever the windows meet
    if seenSet[container] then return end
    seenSet[container] = true
    if #snap.containers >= MAX_CONTAINERS then U._worldCut = true return end
    local items, foods, fluids, n, cut = itemsOf(container)
    if n == 0 then return end
    local c = { where = where, kind = call(container, "getType"), total = n, items = items, foods = foods, fluids = fluids }
    if cut then c.cut = true end
    for k, v in pairs(extra or {}) do c[k] = v end
    snap.containers[#snap.containers + 1] = c
end

-- s77 cars_near: could she use this car? Read from the car and her things; the Mind words it, nothing here is spoken.
--   locked: the driver's door (nil when unknown). key: true = key in the ignition, hotwired with the wires whole, its key in her
--   things or inside the car; false = none of those; nil = unknown. The same rule as SolFar's loadedCanGo.
local function carUse(v, sol)
    local locked = nil
    local door = call((call(v, "getPartById", "DoorFrontLeft")), "getDoor")
    if door ~= nil then
        local l = call(door, "isLocked")
        if type(l) == "boolean" then locked = l end
    end
    if call(v, "isKeysInIgnition") == true then return locked, true end
    if call(v, "isHotwired") == true and call(v, "isHotwiredBroken") == false then return locked, true end
    local kid = num((call(v, "getKeyId")))
    if kid == nil then return locked, nil end
    if kid < 0 then return locked, false end
    local inv = nil
    if sol ~= nil then inv = call(sol, "getInventory") end
    if inv ~= nil then
        local h = call(inv, "haveThisKeyId", kid)
        if h ~= nil and h ~= false then return locked, true end
    end
    local n = num((call(v, "getPartCount"))) or 0
    for i = 0, n - 1 do
        local c = call((call(v, "getPartByIndex", i)), "getItemContainer")
        if c ~= nil then
            local h = call(c, "haveThisKeyId", kid)
            if h ~= nil and h ~= false then return locked, true end
        end
    end
    if inv == nil then return locked, nil end
    return locked, false
end
-- s77 end
-- ---------------------------------------------------------------- scan
local function scanJob()
    local player = getSpecificPlayer and getSpecificPlayer(0)
    if not player then return nil end
    local snap = { v = 1, scan = U.SCAN_VERSION, t = nowMs(), containers = {}, vehicles = {}, plants = {}, animals = {}, waterSources = {} }
    local world = getWorld and getWorld()
    snap.world = { name = call(world, "getWorld"), mode = call(world, "getGameMode") }
    local gt = getGameTime and getGameTime()
    local ageH = num(call(gt, "getWorldAgeHours")) or 0
    local apo = num(call(getSandboxOptions and getSandboxOptions(), "getTimeSinceApo")) or 1
    snap.time = { day = round(ageH / 24 + (apo - 1) * 30, 2), hour = num(call(gt, "getHour")), ageHours = round(ageH, 2) }
    local cm = getClimateManager and getClimateManager()
    snap.weather = { season = call(cm, "getSeasonName"), air = round(call(cm, "getAirTemperatureForCharacter", player, false), 1),
                     rain = round(call(cm, "getPrecipitationIntensity"), 2) }
    if SandboxVars then snap.utilities = { waterShutDay = SandboxVars.WaterShutModifier, elecShutDay = SandboxVars.ElecShutModifier } end
    snap.player = charState(player)
    local sol = U.solActor and U.solActor() or nil
    snap.sol = charState(sol)
    if snap.sol and type(U.solFarState) == "function" and U.solFarState() ~= nil then snap.sol.away = true end   -- registered, no body
    -- s99 perf_slice: her and his inventories are read by the first step (first, as before), not when the job is made
    local pre = { function() addContainer(snap, "player", call(player, "getInventory")) end }
    if sol then pre[#pre + 1] = function() addContainer(snap, "sol", call(sol, "getInventory")) end end
    local cell = getCell and getCell()
    local px, py, pz = math.floor(call(player, "getX") or 0), math.floor(call(player, "getY") or 0), math.floor(call(player, "getZ") or 0)
    local centers = { { px, py, pz, RADIUS } }
    do      -- Sol far from the player: look around her too. The windows never overlap, so nothing is counted twice.
        local sx, sy, sz = num(call(sol, "getX")), num(call(sol, "getY")), num(call(sol, "getZ"))
        if sx and sy then
            local d = math.max(math.abs(sx - px), math.abs(sy - py))
            local r2 = math.min(RADIUS, math.floor(d) - RADIUS - 1)
            if r2 >= 3 then centers[#centers + 1] = { math.floor(sx), math.floor(sy), math.floor(sz or 0), r2 } end
        end
    end
    U._lastWindows, U._worldCut = #centers, false
    local farming = CFarmingSystem and CFarmingSystem.instance
    local waterSeen = {}
    local function visit(x, y, z)
                local sq = cell and call(cell, "getGridSquare", x, y, z)
                if sq then
                    local objs = call(sq, "getObjects")
                    local n = objs and num(call(objs, "size")) or 0
                    local roomObj = call(sq, "getRoom")
                    local room = roomObj and call(roomObj, "getName") or nil
                    for i = 0, n - 1 do
                        local o = call(objs, "get", i)
                        local cc = num(call(o, "getContainerCount")) or 0
                        for k = 0, cc - 1 do
                            addContainer(snap, "square", call(o, "getContainerByIndex", k), { x = x, y = y, z = z, room = room,
                                object = call(call(o, "getSprite"), "getName") })
                        end
                        -- Fixed world water sources (especially wells) are IsoObjects,
                        -- not inventory containers. Keep them separate from stored liters.
                        if o and not waterSeen[o] then
                            local isWater, isWaterOk = call(o, "isWaterSource")
                            local amount, amountOk = call(o, "getFluidAmount")
                            local hasFluid, hasFluidOk = call(o, "hasFluid")
                            if #snap.waterSources < 64 and (isWater == true or (num(amount) and num(amount) > 0) or hasFluid == true) then   -- call() returns one value: there are no "ok" flags
                                waterSeen[o] = true
                                local tainted, taintedOk = call(o, "isTaintedWater")
                                local sprite = call(o, "getSprite")
                                local label = call(o, "getObjectName") or call(o, "getName") or call(sprite, "getName") or call(o, "getType")
                                label = label and tostring(label) or "water source"
                                local lower = string.lower(label)
                                local kind = string.find(lower, "well", 1, true) and "well" or "water_source"
                                local waterTainted = nil
                                if type(tainted) == "boolean" then waterTainted = tainted end
                                snap.waterSources[#snap.waterSources + 1] = {
                                    kind = kind, name = label, x = x, y = y, z = z,
                                    amount = num(amount) and round(num(amount), 2) or nil,
                                    tainted = waterTainted,
                                }
                            end
                        end
                    end
                    if farming then
                        local plant = call(farming, "getLuaObjectOnSquare", sq)
                        if plant then
                            snap.plants[#snap.plants + 1] = { x = x, y = y, z = z, seed = plant.typeOfSeed, water = num(plant.waterLvl),
                                grow = num(plant.nbOfGrow), state = plant.state, health = num(plant.health), exterior = plant.exterior }
                        end
                    end
                    local movers = call(sq, "getMovingObjects")
                    local mn = movers and num(call(movers, "size")) or 0
                    for i = 0, mn - 1 do
                        local m = call(movers, "get", i)
                        if m and instanceof and instanceof(m, "IsoAnimal") then
                            local st = call(m, "getStats")
                            snap.animals[#snap.animals + 1] = { x = x, y = y, z = z, kind = call(m, "getAnimalType"),
                                thirst = round(call(m, "getThirst"), 2), hunger = st and CharacterStat and round(call(st, "get", CharacterStat.HUNGER), 2) or nil }
                        end
                    end
                end
    end
    -- s99 perf_slice: finish is a stepper. The same vehicles in the same order as the old single loop; finish() runs it to the end.
    local fin = nil
    local function finishStep(budgetMs)
        local stopAt = nowMs() + budgetMs
        if fin == nil then
    local vlist, vseen, vfree = {}, {}, {}
    local carsLoaded = {}                                                        -- getVehicles is a Set in B42: no get(i). The same list the rest of the mod uses.
    local carService = rawget(_G, "SurvivorCompanion") and SurvivorCompanion.Vehicle or nil
    if type(carService) == "table" and type(carService.loadedVehicles) == "function" then
        local okC, listC = pcall(carService.loadedVehicles)
        if okC and type(listC) == "table" then carsLoaded = listC end
    end
    for _, v0 in ipairs(carsLoaded) do
        if v0 and not vseen[v0] then vseen[v0] = true; vlist[#vlist + 1] = v0 end
    end
    for _, v0 in ipairs(U.invVehicleObjects and U.invVehicleObjects() or {}) do      -- found from the squares by the base inventory
        if not vseen[v0] then vseen[v0] = true; vfree[v0] = true; vlist[#vlist + 1] = v0 end
    end
            fin = { vlist = vlist, vfree = vfree, vi = 1, phase = "veh" }
            if nowMs() >= stopAt then return false end
        end
        local vlist, vfree = fin.vlist, fin.vfree
        while fin.phase == "veh" do
            local vi = fin.vi
            if vi > #vlist then
                fin.phase = "sol"
                -- s78 cars_away: the loaded cars around HER body, wherever he is (the Mind's cars_near). Read only. Absent when her body is not
                -- in the loaded world (sol.away): the Mind then asks sol_far "cars", the saved rows around her.
                local sx78, sy78 = num((call(sol, "getX"))), num((call(sol, "getY")))
                if sol ~= nil and snap.sol ~= nil and snap.sol.away ~= true and sx78 ~= nil and sy78 ~= nil then
                    snap.solVehicles = {}
                    fin.sx78, fin.sy78, fin.vi = sx78, sy78, 1
                else
                    fin.phase = "done"
                end
            else
                fin.vi = vi + 1
        local v = vlist[vi]
        local vx, vy = num(call(v, "getX")), num(call(v, "getY"))
        if v and vx and vy and (vfree[v] or (math.abs(vx - px) <= RADIUS * 3 and math.abs(vy - py) <= RADIUS * 3)) then
            local name = call(call(v, "getScript"), "getName") or "vehicle"
            local gas = call(v, "getPartById", "GasTank")
            local info = { name = name, x = round(vx, 0), y = round(vy, 0), id = num(call(v, "getSqlId")) or num(call(v, "getId")),
                           fuel = gas and round(call(gas, "getContainerContentAmount"), 1) or nil,
                           fuelMax = gas and num(call(gas, "getContainerCapacity")) or nil }
            info.locked, info.key = carUse(v, sol)                                    -- s77 cars_near
            snap.vehicles[#snap.vehicles + 1] = info
            local pc = num(call(v, "getPartCount")) or 0
            for k = 0, pc - 1 do
                local part = call(v, "getPartByIndex", k)
                local ic = call(part, "getItemContainer")
                if ic then addContainer(snap, "vehicle", ic, { vehicle = name, part = call(part, "getId"), x = info.x, y = info.y }) end
            end
        end
            end
            if nowMs() >= stopAt then return fin.phase == "done" end
        end
        while fin.phase == "sol" do
            local vi = fin.vi
            if vi > #vlist then
                fin.phase = "done"
            else
                fin.vi = vi + 1
                local REACH78 = 60
                local sx78, sy78 = fin.sx78, fin.sy78
            local v = vlist[vi]
            local vx, vy = num((call(v, "getX"))), num((call(v, "getY")))
            if vx ~= nil and vy ~= nil and math.abs(vx - sx78) <= REACH78 and math.abs(vy - sy78) <= REACH78 and #snap.solVehicles < 40 then
                local gas = call(v, "getPartById", "GasTank")
                local info = { name = call((call(v, "getScript")), "getName") or "vehicle", x = round(vx, 0), y = round(vy, 0),
                               id = num((call(v, "getSqlId"))) or num((call(v, "getId"))),
                               fuel = gas and round((call(gas, "getContainerContentAmount")), 1) or nil,
                               fuelMax = gas and num((call(gas, "getContainerCapacity"))) or nil }
                info.locked, info.key = carUse(v, sol)
                snap.solVehicles[#snap.solVehicles + 1] = info
            end
            end
            if fin.phase ~= "done" and nowMs() >= stopAt then return false end
        end
        return true
    end
    local function finish()
        while not finishStep(1000000) do end
        return snap
    end
    -- s78 end
    -- the same squares in the same order as one loop would read them, but a few at a time
    -- s99 perf_slice: fine = true checks the clock after every square (a slice ends within one square of its budget)
    local ci, ctr, xNow, yNow, zNow = 1, nil, nil, nil, nil
    local preI = 1
    local function step(budgetMs, fine)
        local stopAt, n = nowMs() + budgetMs, 0
        while pre[preI] ~= nil do
            local f = pre[preI]
            preI = preI + 1
            f()
            if fine == true and nowMs() >= stopAt then return false end
        end
        while true do
            if not ctr then
                ctr = centers[ci]
                if not ctr then return true end
                xNow, yNow, zNow = ctr[1] - ctr[4], ctr[2] - ctr[4], ctr[3] - ZSPAN
            end
            visit(xNow, yNow, zNow)
            yNow = yNow + 1
            if yNow > ctr[2] + ctr[4] then
                yNow, xNow = ctr[2] - ctr[4], xNow + 1
                if xNow > ctr[1] + ctr[4] then
                    xNow, zNow = ctr[1] - ctr[4], zNow + 1
                    if zNow > ctr[3] + ZSPAN then ctr, ci = nil, ci + 1 end
                end
            end
            n = n + 1
            if (fine == true or n % 12 == 0) and nowMs() >= stopAt then return false end
        end
    end
    return { step = step, finish = finish, finishStep = finishStep }
end
function U.scanWorld()
    local job = scanJob()
    if not job then return nil end
    while not job.step(1000000) do end
    return job.finish()
end
U._scanJob = scanJob

local scanSamples = 0
function U.worldScanTuned(ms)
    -- one scan costs a few milliseconds; if it ever costs more than 150 the radius shrinks by itself, and grows back when it is cheap
    scanSamples = scanSamples + 1
    U.lastWorldScanMs = ms
    if ms > 150 and RADIUS > 9 then RADIUS = RADIUS - 2
    elseif ms < 40 and RADIUS < 15 then RADIUS = RADIUS + 1 end
    if scanSamples % 10 == 1 then log("scan ms=" .. tostring(ms) .. " radius=" .. RADIUS .. " windows=" .. tostring(U._lastWindows)) end
end
function U.writeWorld()
    local t0 = nowMs()
    local r = U.writeWorldRaw()
    U.worldScanTuned(nowMs() - t0)
    if U.perfAdd then U.perfAdd("world_scan", nowMs() - t0) end
    return r
end
-- s99 perf_slice: what writeWorldRaw adds to a snapshot before it is encoded, in the old order; each piece is one unit of a slice
local DECOR = {
function(snap)
    if type(SolLife) == "table" and type(SolLife.snapshot) == "function" then
        local okL, life, streets, current = pcall(SolLife.snapshot)
        if okL then snap.solLife, snap.knownStreets, snap.currentStreet = life, streets, current end
    end
end,
function(snap)
    if type(SolHome) == "table" and type(SolHome.get) == "function" then snap.solHome = SolHome.get() end   -- Sol Mind adopts it when its memory has no home
    if snap.solHome == nil and type(SurvivorCompanion) == "table" and type(SurvivorCompanion.BaseLife) == "table" and type(SurvivorCompanion.BaseLife.active) == "function" then
        local okB, base = pcall(SurvivorCompanion.BaseLife.active)                -- the area he marked as the base is home
        local x1, y1, x2, y2, floor = nil, nil, nil, nil, 0
        for _, z in ipairs(okB and type(base) == "table" and type(base.zones) == "table" and base.zones or {}) do
            if type(z) == "table" and z.kind == "area" and tonumber(z.x1) and tonumber(z.x2) and tonumber(z.y1) and tonumber(z.y2) then
                local ax, bx, ay, by = math.min(z.x1, z.x2), math.max(z.x1, z.x2), math.min(z.y1, z.y2), math.max(z.y1, z.y2)
                x1, x2, y1, y2 = x1 and math.min(x1, ax) or ax, x2 and math.max(x2, bx) or bx, y1 and math.min(y1, ay) or ay, y2 and math.max(y2, by) or by
                floor = tonumber(z.z) or floor
            end
        end
        if x1 ~= nil then snap.solHome = { x = math.floor((x1 + x2) / 2), y = math.floor((y1 + y2) / 2), z = floor, fromBase = true } end
    end
end,
function(snap)
    if type(SurvivorCompanion) == "table" and type(SurvivorCompanion.BaseLife) == "table" and type(SurvivorCompanion.BaseLife.active) == "function" then
        local okP, parkBase = pcall(SurvivorCompanion.BaseLife.active)
        for _, z in ipairs(okP and type(parkBase) == "table" and type(parkBase.zones) == "table" and parkBase.zones or {}) do
            if type(z) == "table" and z.kind == "parking" and tonumber(z.x1) and tonumber(z.x2) and tonumber(z.y1) and tonumber(z.y2) then
                local spot = { x = math.floor((z.x1 + z.x2) / 2), y = math.floor((z.y1 + z.y2) / 2), x1 = math.min(z.x1, z.x2), x2 = math.max(z.x1, z.x2), y1 = math.min(z.y1, z.y2), y2 = math.max(z.y1, z.y2) }
                snap.solParking = snap.solParking or { x = spot.x, y = spot.y }
                snap.solParkings = snap.solParkings or {}
                snap.solParkings[#snap.solParkings + 1] = spot
            end
        end
    end
end,
function(snap)
    if type(SolFarmWork) == "table" and type(SolFarmWork.snapshot) == "function" then
        local okF, farm = pcall(SolFarmWork.snapshot)
        if okF then snap.solFarm = farm end
    end
end,
function(snap)
    if type(SolBookMemory) == "table" and type(SolBookMemory.snapshot) == "function" then      -- book_memory: her address book, compact, for the Mind
        local okBM, bm = pcall(SolBookMemory.snapshot)
        if okBM then snap.solBook = bm end
    end
end,
function(snap)
    snap.coverage = { radius = RADIUS, windows = U._lastWindows or 1, containers = #snap.containers, containersCut = U._worldCut == true, ms = U.lastWorldScanMs }
    if U.invCompact then
        local inv = U.invCompact()
        if inv and U.invCovers then      -- the base inventory already holds these containers: never count them twice
            local keep = {}
            for _, c in ipairs(snap.containers) do if not U.invCovers(c) then keep[#keep + 1] = c end end
            snap.containers = keep
            snap.coverage.containers = #keep
        end
        snap.baseInventory = inv
    end
end,
}
local function writeText(text)
    local okw, w = pcall(getFileWriter, FILE, true, false)
    if not okw or not w then return false end
    w:write(text); w:close()
    U.lastWorldWrite = nowMs()
    return true
end
function U.writeWorldRaw(ready)
    local ok, snap = true, ready
    if ready == nil then ok, snap = pcall(U.scanWorld) end
    if not ok then log("scan failed: " .. tostring(snap)); return false end
    if not snap then return false end
    for i = 1, #DECOR do DECOR[i](snap) end
    local ok2, text = pcall(encode, snap)
    if not ok2 then log("encode failed: " .. tostring(text)); return false end
    return writeText(text)
end

-- s99 perf_slice: the same text as encode(v), built one value at a time. step(budgetMs) returns true when result() is ready.
-- A table's keys are listed once when it is opened (pairs order, as encode would walk them); its values are read when reached.
function U.jsonEncodeJob(root)
    local result, stack = nil, {}
    local function open(t, depth, prefix)
        local f = { t = t, depth = depth, prefix = prefix, parts = {}, i = 0 }
        if isArray(t) then f.arr = true; f.n = #t
        else
            local keys = {}
            for k in pairs(t) do keys[#keys + 1] = k end
            f.keys, f.n = keys, #keys
        end
        stack[#stack + 1] = f
    end
    if type(root) == "table" then open(root, 0, "") else result = encode(root, 0) end
    local function step(budgetMs)
        if result ~= nil then return true end
        local stopAt = nowMs() + budgetMs
        while true do
            local f = stack[#stack]
            f.i = f.i + 1
            if f.i > f.n then
                stack[#stack] = nil
                local s
                if f.arr then s = "[" .. table.concat(f.parts, ",") .. "]" else s = "{" .. table.concat(f.parts, ",") .. "}" end
                local p = stack[#stack]
                if p == nil then result = s; return true end
                p.parts[#p.parts + 1] = f.prefix .. s
            else
                local x, prefix
                if f.arr then x, prefix = f.t[f.i], ""
                else local k = f.keys[f.i]; x, prefix = f.t[k], jstr(k) .. ":" end
                if type(x) == "table" and f.depth + 1 <= 12 then open(x, f.depth + 1, prefix)
                else f.parts[#f.parts + 1] = prefix .. encode(x, f.depth + 1) end
            end
            if nowMs() >= stopAt then return false end
        end
    end
    return { step = step, result = function() return result end }
end

local SLICE_MS = 4
local function sliceOn() local A_ = rawget(_G, "SolAuthority"); return type(A_) == "table" and type(A_.on) == "function" and (A_.on("perf_slice") == true or A_.on("task_scoped_perception") == true) end
U.worldSliceOn = sliceOn
local lastTick = 0
local sliced, slicedMs = nil, 0
local scanRequested, worldLease = false, nil
-- s99 perf_slice: squares, then finish, then each DECOR piece, then the encode, then the file; at most budgetMs a call
-- (plus the one unit that crosses it). tuneMs leaves out finish, as the old count did.
local function slicedTick(t, remainingMs)
    local b = tonumber(remainingMs) or SLICE_MS
    if b > SLICE_MS then b = SLICE_MS end
    if b < 1 then b = 1 end
    if not sliceOn() then b = 1000000 end                                      -- switched off half way: the rest at once, as before
    local job = sliced
    if job.phase == nil then job.phase, job.tuneMs, job.di = "squares", 0, 1 end
    local stopAt = t + b
    local finMs = 0
    while true do
        local ph = job.phase
        if ph == "squares" then
            if job.step(math.max(stopAt - nowMs(), 0), true) then job.phase = "finish" end
        elseif ph == "finish" then
            local tf = nowMs()
            local done = job.finishStep(math.max(stopAt - nowMs(), 0))
            finMs = finMs + (nowMs() - tf)
            if done then job.snap = job.finish(); job.phase = "decor" end
        elseif ph == "decor" then
            local f = DECOR[job.di]
            if f == nil then job.phase = "encode"; job.enc = U.jsonEncodeJob(job.snap)
            else job.di = job.di + 1; f(job.snap) end
        elseif ph == "encode" then
            if job.enc.step(math.max(stopAt - nowMs(), 0)) then job.phase = "write" end
        elseif ph == "write" then
            writeText(job.enc.result())
            job.phase = "done"
        end
        if job.phase == "done" or nowMs() >= stopAt then break end
    end
    local ms = nowMs() - t
    slicedMs = slicedMs + ms
    job.tuneMs = job.tuneMs + ms - finMs
    if U.perfAdd then U.perfAdd("world_scan", ms) end                         -- one call per frame: max is the real frame cost
    if job.phase == "done" then
        sliced = nil
        U.worldScanTuned(job.tuneMs)
        if worldLease ~= nil then SolScanCoordinator.release("world_scan", worldLease, "done"); worldLease = nil end
    end
end
local function onTick(remainingMs)
    local t = nowMs()
    if sliced ~= nil and worldLease ~= nil and not SolScanCoordinator.owns("world_scan", worldLease) then
        sliced, slicedMs, worldLease = nil, 0, nil
        log("cancelled superseded scan")
    end
    if sliced == nil then
        if not scanRequested and t - lastTick < INTERVAL_MS then return end
        local profile = scanRequested and "requested" or "background"
        local acquired, generation = SolScanCoordinator.tryAcquire("world_scan", profile)
        if not acquired then return end
        worldLease = generation
        scanRequested = false
        lastTick = t
        local ok, job = pcall(scanJob)
        if not ok or job == nil then
            log("scan start failed: " .. tostring(job))
            SolScanCoordinator.release("world_scan", worldLease, "start_failed")
            worldLease = nil
            return
        end
        sliced, slicedMs = job, 0
        if sliceOn() then
            local ms = nowMs() - t
            slicedMs = ms
            job.phase, job.tuneMs, job.di = "squares", ms, 1
            if U.perfAdd then U.perfAdd("world_scan", ms) end
            return
        end
    end
    if sliced.phase ~= nil or sliceOn() then
        local okS, err = pcall(slicedTick, t, remainingMs)
        if not okS then
            log("scan failed: " .. tostring(err))
            sliced = nil
            if worldLease ~= nil then SolScanCoordinator.release("world_scan", worldLease, "failed"); worldLease = nil end
        end
        return
    end
    local ok, done = pcall(sliced.step, remainingMs or 2)
    slicedMs = slicedMs + (nowMs() - t)
    if not ok then
        log("scan failed: " .. tostring(done)); sliced = nil
        if worldLease ~= nil then SolScanCoordinator.release("world_scan", worldLease, "failed"); worldLease = nil end
        return
    end
    if done then
        local job = sliced
        sliced = nil
        local okF, snap = pcall(job.finish)
        if not okF then
            log("scan failed: " .. tostring(snap))
            if worldLease ~= nil then SolScanCoordinator.release("world_scan", worldLease, "finish_failed"); worldLease = nil end
            return
        end
        local t1 = nowMs()
        U.writeWorldRaw(snap)
        U.worldScanTuned(slicedMs + (nowMs() - t1))
        if U.perfAdd then U.perfAdd("world_scan", slicedMs + (nowMs() - t1)) end
        if worldLease ~= nil then SolScanCoordinator.release("world_scan", worldLease, "done"); worldLease = nil end
    end
end
U.requestWorldScan = function() scanRequested = true; return true, "queued" end
U.scanNow = function()
    local A_ = rawget(_G, "SolAuthority")
    if type(A_) == "table" and type(A_.on) == "function" and A_.on("task_scoped_perception") == true then
        return U.requestWorldScan()
    end
    if worldLease ~= nil then SolScanCoordinator.release("world_scan", worldLease, "sync_override"); worldLease = nil end
    sliced = nil; lastTick = nowMs(); return U.writeWorld()
end
require "SolBudget"
SolBudget.register("world_scan", onTick, { everyMs = 0, priority = 6 })
log("world scanner ready v" .. U.SCAN_VERSION)

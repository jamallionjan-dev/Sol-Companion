-- SolInventory.lua - the full inventory: what the team really holds, read from the game itself.
-- Sources: Sol's inventory, the player's inventory (both opened recursively: a backpack, a case or a box inside
-- another container is opened too), every container on the squares of the base area, and the vehicles near it.
-- The old world scan looked 15 tiles around the player only and never opened bags; this one covers the whole base.
-- It works in small slices on OnTick (a few milliseconds each) so the game never stutters, and says how much it
-- could not see (squares that are not loaded) instead of guessing.
-- Verbs (SolAct_Request channel):
--   sol_inv_scan   start a scan (returns at once)           sol_inv_stats  progress and totals on one line
--   sol_inv_probe  raw samples (ammo, food) to calibrate     The window and the chat card read U.invModel().
-- Debug mode stops the game on any error, even a caught one, so every game call is checked first.
SolUI = SolUI or {}
local U = SolUI
U.INV_VERSION = "0.1.0"
local MARGIN, SQ_PER_STEP, CONT_PER_STEP, BUDGET_MS, MAX_DEPTH, MAX_SQUARES, MAX_ROWS, VEH_REACH = 4, 150, 8, 4, 4, 12000, 1500, 30
local AUTO_MS, FRESH_MS = 120000, 300000      -- a new scan every 2 minutes; Sol Mind may use one up to 5 minutes old
local Z_BELOW, Z_ABOVE = 1, 2                  -- floors scanned around the base area: a basement and two upper floors
local function log(m) print("[SolInventory] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or 0 end
local function method(o, name, ...)
    if o == nil then return nil end
    local f = o[name]
    if type(f) ~= "function" then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function num(v) return tonumber(v) end
local function is(o, cls) return type(instanceof) == "function" and instanceof(o, cls) == true end

local job, model = nil, nil
local last = nil          -- the last FINISHED scan: stays available while the next one runs, so there is never a gap

-- ---------------------------------------------------------------- reading one item
local function itemRead(it)
    local d = { type = tostring(method(it, "getFullType") or "?"), name = tostring(method(it, "getDisplayName") or "?"),
                cat = tostring(method(it, "getDisplayCategory") or "") }
    local n = num(method(it, "getCount"))
    d.n = (n and n > 0) and n or 1
    local fc = method(it, "getFluidContainer")
    if fc ~= nil and method(fc, "isEmpty") ~= true then
        local fl = method(fc, "getPrimaryFluid")
        d.fluid = { l = num(method(fc, "getAmount")) or 0, kind = tostring(fl and method(fl, "getFluidTypeString") or "?"),
                    bad = (fl ~= nil and method(fl, "isPoisonous") == true) }
    end
    if is(it, "Food") then
        d.food = { cal = num(method(it, "getCalories")) or 0, hunger = num(method(it, "getHungerChange")) or num(method(it, "getHungChange")) or 0,
                   rotten = method(it, "isRotten") == true, age = num(method(it, "getAge")), offMax = num(method(it, "getOffAgeMax")) }
    end
    if is(it, "InventoryContainer") then d.bag = method(it, "getInventory") end
    return d
end

local function has(s, ...) for _, w in ipairs({ ... }) do if string.find(s, w, 1, true) then return true end end return false end
local function groupOf(d)
    local low, cat, ty = string.lower(d.name), string.lower(d.cat), string.lower(d.type)
    if d.bag ~= nil then return "bags" end
    if d.fluid then
        local k = string.lower(d.fluid.kind)
        if has(k, "water", "tainted") then return "water" end
        if has(k, "petrol", "gasoline", "diesel", "kerosene", "fuel") then return "fuel" end
        return "fluids"
    end
    if d.food then
        if has(low, "dog food", "cat food", "pet food", "kibble") then return "petfood" end
        return "food"
    end
    if has(cat, "ammo") then return "ammo" end
    if has(cat, "weapon") then return "weapons" end
    if has(cat, "firstaid", "first aid", "medic", "bandage") or has(ty, "bandage", "pills", "disinfect") then return "medical" end
    if has(ty, "seed") or has(cat, "plant", "seed", "garden", "farm") then return "plants" end
    if has(cat, "tool") then return "tools" end
    if has(cat, "material", "resource", "construction") or has(ty, "nails", "plank", "screws") then return "materials" end
    if has(cat, "cloth", "accessor", "wear") then return "clothing" end
    if has(cat, "literature", "book", "magazine") then return "books" end
    if has(cat, "appliance", "machine", "electr", "generator") then return "machines" end
    return "other"
end

-- ---------------------------------------------------------------- the model
local function newModel(opts)
    return { v = 1, version = U.INV_VERSION, t = nowMs(), rows = {}, byKey = {}, grp = {}, cats = {}, conts = 0, items = 0,
             squares = 0, unloaded = 0, vehicles = 0, vehConts = 0, vsrc = { sq = 0, list = 0 }, vehObjs = {}, trunc = false, state = "running",
             food = { cal = 0, soon = 0, rotten = 0, pet = 0, items = 0, hunger = 0, soonList = {}, rottenList = {} }, water = { clean = 0, bad = 0 }, fuel = 0,
             sample = { ammo = {}, food = {} }, ammo = {}, places = {}, farm = {}, waterSources = {} }
end

local function addItem(m, where, d, label)
    m.items = m.items + 1
    local g = groupOf(d)
    m.cats[d.cat] = (m.cats[d.cat] or 0) + 1
    local key = where .. "|" .. d.type .. "|" .. tostring(d.fluid and d.fluid.kind or "") .. "|" .. tostring(d.food and d.food.rotten or "") .. "|" .. tostring(label or "")
    local r = m.byKey[key]
    if not r then
        if #m.rows >= MAX_ROWS then m.trunc = true return end
        r = { where = where, label = label, type = d.type, name = d.name, cat = d.cat, grp = g, count = 0, cal = 0, liters = 0, rotten = false }
        m.byKey[key] = r
        m.rows[#m.rows + 1] = r
    end
    r.count = r.count + d.n
    m.grp[g] = (m.grp[g] or 0) + d.n
    if d.fluid then
        r.liters = r.liters + d.fluid.l
        r.bad = d.fluid.bad
        if g == "water" then if d.fluid.bad or string.find(string.lower(d.fluid.kind), "tainted", 1, true) then m.water.bad = m.water.bad + d.fluid.l else m.water.clean = m.water.clean + d.fluid.l end
        elseif g == "fuel" then m.fuel = m.fuel + d.fluid.l end
    end
    if d.food then
        r.rotten = d.food.rotten
        if g == "food" then
            if d.food.rotten then
                m.food.rotten = m.food.rotten + 1                              -- rotten food gives no calories and no hunger relief
                if #m.food.rottenList < 12 then m.food.rottenList[#m.food.rottenList + 1] = { d.name, label or where } end
            else
                local hun = -(d.food.hunger or 0)
                if hun > 0 then
                    m.food.items = m.food.items + 1
                    m.food.hunger = m.food.hunger + hun
                    r.hun = (r.hun or 0) + hun
                    m.food.cal = m.food.cal + d.food.cal
                    r.cal = r.cal + d.food.cal
                end
                if hun > 0 and d.food.offMax and d.food.age then
                    local left = math.max(0, d.food.offMax - d.food.age)
                    if left <= 2 then
                        m.food.soon = m.food.soon + 1
                        r.dl = math.min(r.dl or left, left)
                        if #m.food.soonList < 12 then m.food.soonList[#m.food.soonList + 1] = { d.name, math.floor(left * 10 + 0.5) / 10, label or where } end
                    end
                end
            end
        else m.food.pet = m.food.pet + d.n end
        if #m.sample.food < 6 then m.sample.food[#m.sample.food + 1] = d.type .. "=" .. tostring(d.food.cal) .. "cal/h" .. tostring(d.food.hunger) end
    end
    if g == "ammo" then
        local a = m.ammo[d.type]
        if not a then a = { name = d.name, items = 0, n = 0 }; m.ammo[d.type] = a end
        a.items = a.items + 1
        a.n = a.n + d.n
    end
    if g == "ammo" and #m.sample.ammo < 8 then m.sample.ammo[#m.sample.ammo + 1] = d.type .. "=" .. d.name .. "/n" .. tostring(d.n) .. "/" .. d.cat end
end

-- ---------------------------------------------------------------- job
local function areaRects(base)
    local out = {}
    for _, z in ipairs(type(base) == "table" and type(base.zones) == "table" and base.zones or {}) do
        if type(z) == "table" and z.kind == "area" and num(z.x1) and num(z.x2) and num(z.y1) and num(z.y2) then
            out[#out + 1] = { x1 = math.min(z.x1, z.x2), x2 = math.max(z.x1, z.x2), y1 = math.min(z.y1, z.y2), y2 = math.max(z.y1, z.y2), z = num(z.z) or 0 }
        end
    end
    return out
end

function U.invStart()
    if job and job.phase ~= "done" then return false, "busy" end
    local sc = SurvivorCompanion
    local BL = type(sc) == "table" and sc.BaseLife or nil
    local base = type(BL) == "table" and type(BL.active) == "function" and select(2, pcall(BL.active)) or nil
    local rects = areaRects(base)
    if #rects == 0 and type(SolHome) == "table" and type(SolHome.rects) == "function" then   -- no Living Fellows base: Sol's own home area
        local okH, hr = pcall(SolHome.rects); if okH and type(hr) == "table" then rects = hr end
    end
    local player = getSpecificPlayer and getSpecificPlayer(0) or nil
    if player == nil then return false, "no_player" end
    model = newModel()
    job = { phase = "squares", squares = {}, si = 1, conts = {}, ci = 1, rects = rects, seenVeh = {}, px = num(method(player, "getX")), py = num(method(player, "getY")) }
    local sol = U.solActor and U.solActor() or nil
    job.conts[#job.conts + 1] = { cont = method(player, "getInventory"), where = "player", depth = 0 }
    if sol ~= nil then job.conts[#job.conts + 1] = { cont = method(sol, "getInventory"), where = "sol", depth = 0 } end
    local seen = {}
    for _, r in ipairs(rects) do
        for z = r.z - Z_BELOW, r.z + Z_ABOVE do
            for x = r.x1 - MARGIN, r.x2 + MARGIN do
                for y = r.y1 - MARGIN, r.y2 + MARGIN do
                    local k = (z + 8) * 4294967296 + x * 65536 + y
                    if not seen[k] then
                        seen[k] = true
                        if #job.squares >= MAX_SQUARES then model.trunc = true else job.squares[#job.squares + 1] = { x, y, z, z == r.z } end
                    end
                end
            end
        end
    end
    model.noArea = (#rects == 0)
    model.rects = rects
    model.sources = #job.conts
    return true, "started"
end

local function readVehicle(v, src)
    if v == nil or job.seenVeh[v] then return end
    job.seenVeh[v] = true
    model.vehicles = model.vehicles + 1
    model.vsrc[src] = (model.vsrc[src] or 0) + 1
    model.vehObjs[#model.vehObjs + 1] = v
    local script = method(v, "getScript")
    local label = tostring(method(script, "getName") or method(v, "getScriptName") or method(v, "getObjectName") or "vehicle")
    local pc = num(method(v, "getPartCount")) or 0
    for p = 0, pc - 1 do
        local part = method(v, "getPartByIndex", p)
        local c = part and method(part, "getItemContainer")
        if c ~= nil then model.vehConts = model.vehConts + 1; job.conts[#job.conts + 1] = { cont = c, where = "vehicle", depth = 0, label = label } end
    end
end

local function stepSquares(cell)
    local n = 0
    while job.si <= #job.squares and n < SQ_PER_STEP do
        local s = job.squares[job.si]; job.si = job.si + 1; n = n + 1
        local sq = method(cell, "getGridSquare", s[1], s[2], s[3])
        if sq == nil then if s[4] then model.unloaded = model.unloaded + 1 end
        else
            model.squares = model.squares + 1
            local room = method(method(sq, "getRoom"), "getName")
            readVehicle(method(sq, "getVehicleContainer"), "sq")
            local objs = method(sq, "getObjects")
            local cnt = objs and num(method(objs, "size")) or 0
            for i = 0, cnt - 1 do
                local o = method(objs, "get", i)
                if o ~= nil and not is(o, "IsoDeadBody") then
                    local litres = method(o, "hasWater") == true and num(method(o, "getFluidAmount")) or nil     -- what could fill a watering can, and where: water only
                    if litres ~= nil and litres > 0 and #model.waterSources < 64 then
                        model.waterSources[#model.waterSources + 1] = { x = s[1], y = s[2], z = s[3], oi = i, l = litres, tainted = method(o, "isTaintedWater") == true }
                    end
                    local cc = num(method(o, "getContainerCount")) or 0
                    for k = 0, cc - 1 do
                        local c = method(o, "getContainerByIndex", k)
                        if c ~= nil then job.conts[#job.conts + 1] = { cont = c, where = "house", depth = 0, room = room, x = s[1], y = s[2], z = s[3], oi = i, ci = k } end
                    end
                end
            end
        end
    end
    if job.si > #job.squares then job.phase = "vehicles" end
end

local function stepVehicles(cell)
    local vlist = {}
    local SCv = type(SurvivorCompanion) == "table" and SurvivorCompanion.Vehicle or nil
    if type(SCv) == "table" and type(SCv.loadedVehicles) == "function" then
        local okV, loaded = pcall(SCv.loadedVehicles)
        if okV and type(loaded) == "table" then vlist = loaded end
    end
    if #vlist == 0 then      -- the cell's vehicle list is a Set in B42: size() works, get(i) does not
        local list = method(cell, "getVehicles")
        local cnt = list and num(method(list, "size")) or 0
        for i = 0, cnt - 1 do
            local v = method(list, "get", i)
            if v ~= nil then vlist[#vlist + 1] = v end
        end
    end
    for _, v in ipairs(vlist) do
        local vx, vy = num(method(v, "getX")), num(method(v, "getY"))
        local near = false
        if #job.rects == 0 then      -- no base area: only vehicles close to the player
            near = (job.px ~= nil and job.py ~= nil and vx ~= nil and vy ~= nil and math.abs(vx - job.px) <= VEH_REACH and math.abs(vy - job.py) <= VEH_REACH)
        end
        for _, r in ipairs(job.rects) do
            if vx and vy and vx >= r.x1 - VEH_REACH and vx <= r.x2 + VEH_REACH and vy >= r.y1 - VEH_REACH and vy <= r.y2 + VEH_REACH then near = true end
        end
        if v ~= nil and near then readVehicle(v, "list") end
    end
    job.phase = "conts"
end

-- so a row can be found again: the square, the object on it and its container. The farm reads this; the table for the Mind is unchanged.
local MAX_PLACES, MAX_FARM = 400, 1500
local function placeFor(e)
    if e.where ~= "house" or e.x == nil or e.depth ~= 0 then return nil end
    if #model.places >= MAX_PLACES then model.trunc = true; return nil end
    local p = { x = e.x, y = e.y, z = e.z, oi = e.oi, ci = e.ci, room = e.room, kind = tostring(method(e.cont, "getType") or ""), food = 0 }
    model.places[#model.places + 1] = p
    return p
end
local function noteFarm(e, it, d, place)
    if place ~= nil and d.food ~= nil then place.food = place.food + 1 end
    if (e.where ~= "house" and e.where ~= "sol") or type(U.invFarmTag) ~= "function" then return end
    local ok, row = pcall(U.invFarmTag, it, d.type)
    if not ok or type(row) ~= "table" then return end
    if #model.farm >= MAX_FARM then model.trunc = true; return end
    row.type, row.name, row.where, row.x, row.y, row.z, row.oi, row.ci, row.depth = d.type, d.name, e.where, e.x, e.y, e.z, e.oi, e.ci, e.depth
    model.farm[#model.farm + 1] = row
end

local function stepConts()
    local n = 0
    while job.ci <= #job.conts and n < CONT_PER_STEP do
        local e = job.conts[job.ci]; job.ci = job.ci + 1; n = n + 1
        if e.cont ~= nil then
            model.conts = model.conts + 1
            local list = method(e.cont, "getItems")
            local cnt = list and num(method(list, "size")) or 0
            local place = placeFor(e)
            for i = 0, cnt - 1 do
                local it = method(list, "get", i)
                if it ~= nil then
                    local d = itemRead(it)
                    addItem(model, e.where, d, e.label or e.room)
                    noteFarm(e, it, d, place)
                    if d.bag ~= nil and e.depth < MAX_DEPTH then
                        job.conts[#job.conts + 1] = { cont = d.bag, where = e.where, depth = e.depth + 1, label = e.label, room = e.room, x = e.x, y = e.y, z = e.z, oi = e.oi, ci = e.ci }
                    end
                end
            end
        end
    end
    if job.ci > #job.conts then job.phase = "finish" end
end

local function finish()
    local gt = getGameTime and getGameTime() or nil
    local sb = getSandboxOptions and getSandboxOptions() or nil
    local ageH = num(method(gt, "getWorldAgeHours")) or 0
    local apo = num(method(sb, "getTimeSinceApo")) or 1
    model.day = ageH / 24 + (apo - 1) * 30
    if SandboxVars then model.waterShutDay, model.elecShutDay = SandboxVars.WaterShutModifier, SandboxVars.ElecShutModifier end
    if model.squares == 0 and last ~= nil and ((tonumber(last.squares) or 0) > 0 or last.baseFrom ~= nil) then     -- he is away and the base is not loaded: what she last saw there still stands
        for _, r in ipairs(last.rows or {}) do
            if r.where ~= "player" and r.where ~= "sol" and #model.rows < MAX_ROWS then model.rows[#model.rows + 1] = r end
        end
        model.baseFrom = last.baseFrom or last.t
    end
    model.state = "done"; model.ms = nowMs() - model.t; model.byKey = nil
    last = model
    job.phase = "done"
end

function U.invStep()
    if not job or job.phase == "done" then return true end
    local cell = getCell and getCell() or nil
    if cell == nil then return false end
    if job.phase == "squares" then stepSquares(cell)
    elseif job.phase == "vehicles" then stepVehicles(cell)
    elseif job.phase == "conts" then stepConts()
    elseif job.phase == "finish" then finish() end
    return job.phase == "done"
end

function U.invModel() return model end
function U.invLast() return last end               -- the last scan that finished; a running one is half a picture

local function top(map, n)
    local arr = {}
    for k, v in pairs(map) do arr[#arr + 1] = { k, v } end
    table.sort(arr, function(a, b) if a[2] ~= b[2] then return a[2] > b[2] end return a[1] < b[1] end)
    local out = {}
    for i = 1, math.min(n, #arr) do out[#out + 1] = (arr[i][1] ~= "" and arr[i][1] or "-") .. ":" .. arr[i][2] end
    return table.concat(out, ",")
end

function U.invStats()
    local m = model
    if not m then return false, "inv;state=idle" end
    local total = job and (#job.squares + #job.conts) or 0
    local at = job and ((job.si - 1) + (job.ci - 1)) or 0
    local text = "inv;state=" .. m.state .. ";progress=" .. at .. "/" .. total .. ";conts=" .. m.conts .. ";items=" .. m.items
        .. ";rows=" .. #m.rows .. ";sq=" .. m.squares .. ";unloaded=" .. m.unloaded .. ";veh=" .. m.vehicles .. "/" .. m.vehConts .. "(sq" .. m.vsrc.sq .. ",list" .. m.vsrc.list .. ")"
        .. ";trunc=" .. (m.trunc and 1 or 0) .. ";noarea=" .. (m.noArea and 1 or 0) .. ";ms=" .. tostring(m.ms or 0)
        .. ";grp=" .. top(m.grp, 12) .. ";food=" .. math.floor(m.food.cal) .. "cal/soon" .. m.food.soon .. "/rot" .. m.food.rotten .. "/pet" .. m.food.pet
        .. ";water=" .. string.format("%.1f", m.water.clean) .. "/" .. string.format("%.1f", m.water.bad) .. ";fuel=" .. string.format("%.1f", m.fuel)
        .. ";cats=" .. top(m.cats, 12)
    if string.len(text) > 900 then text = string.sub(text, 1, 900) end
    return true, text
end

function U.invCompact()
    -- what the world snapshot carries for Sol Mind: one row per (place, item type), nothing guessed
    local m = last
    if not m or nowMs() - m.t > FRESH_MS then return nil end
    local rows = {}
    for i = 1, math.min(#m.rows, 600) do
        local r = m.rows[i]
        rows[#rows + 1] = { w = r.where, t = r.type, n = r.name, c = r.cat, g = r.grp, k = r.count, room = r.label,
                            cal = (r.cal > 0) and math.floor(r.cal) or nil, l = (r.liters > 0) and math.floor(r.liters * 100 + 0.5) / 100 or nil, rot = r.rotten or nil,
                            hun = r.hun and math.floor(r.hun * 1000 + 0.5) / 1000 or nil, dl = r.dl and math.floor(r.dl * 10 + 0.5) / 10 or nil, bad = r.bad or nil }
    end
    return { t = m.t, day = m.day, waterShutDay = m.waterShutDay, elecShutDay = m.elecShutDay, squares = m.squares, unloaded = m.unloaded, conts = m.conts,
             vehicles = m.vehicles, baseFrom = m.baseFrom, trunc = m.trunc or nil, noArea = m.noArea or nil, rows = rows,
             ammo = (function() local out = {}
                 for t, a in pairs(m.ammo) do out[#out + 1] = { t = t, n = a.name, items = a.items, rounds = a.n } end
                 table.sort(out, function(x, y) if x.rounds ~= y.rounds then return x.rounds > y.rounds end return x.t < y.t end)
                 while #out > 24 do table.remove(out) end
                 return out end)(),
             food = { cal = math.floor(m.food.cal), soon = m.food.soon, rotten = m.food.rotten, pet = m.food.pet, items = m.food.items,
                      hunger = math.floor(m.food.hunger * 1000 + 0.5) / 1000, soonList = m.food.soonList, rottenList = m.food.rottenList },
             water = { clean = math.floor(m.water.clean * 100 + 0.5) / 100, bad = math.floor(m.water.bad * 100 + 0.5) / 100 }, fuel = math.floor(m.fuel * 100 + 0.5) / 100 }
end

function U.invCovers(c)
    -- true when the container record (from the world snapshot) is already part of the base inventory, so it must not be counted twice
    local m = last
    if not m or m.noArea or type(c) ~= "table" then return false end
    if c.where == "player" or c.where == "sol" then return true end
    local x, y, z = num(c.x), num(c.y), num(c.z)
    for _, r in ipairs(m.rects or {}) do
        if c.where == "square" and x and y and z and x >= r.x1 - MARGIN and x <= r.x2 + MARGIN and y >= r.y1 - MARGIN and y <= r.y2 + MARGIN
            and z >= r.z - Z_BELOW and z <= r.z + Z_ABOVE then return true end
        if c.where == "vehicle" and m.vehConts > 0 and ((x == nil or y == nil) or (x and y and x >= r.x1 - VEH_REACH and x <= r.x2 + VEH_REACH and y >= r.y1 - VEH_REACH and y <= r.y2 + VEH_REACH)) then return true end
    end
    return false
end

function U.invVehicleObjects()
    -- the vehicles the last scan found (from the squares): the world scan lists them for Sol Mind (fuel, position)
    return last and last.vehObjs or {}
end

function U.invProbe()
    local m = model
    if not m then return false, "probe;none" end
    local types = {}
    for t, a in pairs(m.ammo) do types[#types + 1] = { t, a } end
    table.sort(types, function(x, y) if x[2].n ~= y[2].n then return x[2].n > y[2].n end return x[1] < y[1] end)
    local at = {}
    for i = 1, math.min(10, #types) do at[#at + 1] = types[i][1] .. "=" .. types[i][2].name .. ":" .. types[i][2].items .. "items/" .. types[i][2].n .. "n" end
    local text = "probe;ammoTypes=" .. table.concat(at, " | ") .. ";food=" .. table.concat(m.sample.food, " | ")
    if string.len(text) > 900 then text = string.sub(text, 1, 900) end
    return true, text
end

local function install()
    if U._invInstalled then return end
    U._invInstalled = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "sol_inv_scan" then local ok, a, b = pcall(U.invStart); if not ok then return false, "inv_error" end return a, b
        elseif id == "sol_inv_stats" then local ok, a, b = pcall(U.invStats); if not ok then return false, "inv_error" end return a, b
        elseif id == "sol_inv_probe" then local ok, a, b = pcall(U.invProbe); if not ok then return false, "inv_error" end return a, b end
        return base(id, option)
    end
    do
        local lastAuto = 0
        local function invTick()
            local t = nowMs()
            if job and job.phase ~= "done" then
                U.invStep()
                if U.perfAdd then U.perfAdd("inventory", nowMs() - t) end
                return
            end
            if t - lastAuto >= AUTO_MS and getSpecificPlayer and getSpecificPlayer(0) ~= nil then lastAuto = t; pcall(U.invStart) end
        end
        if type(SolBudget) == "table" and type(SolBudget.register) == "function" then SolBudget.register("inventory", invTick, { everyMs = 0, priority = 7 })
        elseif Events and Events.OnTick then Events.OnTick.Add(invTick) end
    end
    log("verbs installed v" .. U.INV_VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(install) end
log("ready v" .. U.INV_VERSION)

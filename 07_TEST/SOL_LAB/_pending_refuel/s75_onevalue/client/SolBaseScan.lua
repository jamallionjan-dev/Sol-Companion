-- SolBaseScan.lua - Sol finds the farm and the containers by herself, says what she found, and registers it only when told.
-- Verbs (SolAct_Request channel):
--   sol_base_scan   read-only: looks at the base area (and the work-reach band around it) for plants and containers,
--                   proposes farm zones (<= 225 tiles each, Living Fellows limit is 256) and the few storages farming needs.
--   sol_base_apply  registers the last proposal through Living Fellows' own BaseLife.beginZone / finishZone / registerStorage.
--                   Refuses without a fresh proposal (5 minutes). Nothing is registered by the scan itself.
-- Why registration matters: LF only works with what is registered, and a registered storage lets LF take from it and put into it,
-- so the proposal registers the minimum (farming supplies, one output, one food) and never every container.
-- One line comes back; Sol Mind words it in Arabic from fixed templates.
-- Debug mode stops the game on any error, even a caught one, so every call is checked first.
SolUI = SolUI or {}
local U = SolUI
U.BASESCAN_VERSION = "0.1.0"
local MARGIN, MAX_SQUARES, MAX_MS, CHUNK, TTL_MS, MAX_ZONES_DEFAULT = 30, 12000, 500, 15, 300000, 24
local function log(m) print("[SolBaseScan] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or 0 end
local function LF() local sc = SurvivorCompanion; if type(sc) == "table" then return sc end return nil end
local function call(fn, ...)
    if type(fn) ~= "function" then return nil end
    local ok, a, b = pcall(fn, ...)
    if ok then return a, b end
    return nil
end
local function method(o, name, ...)
    if o == nil then return nil end
    local f = o[name]
    if type(f) ~= "function" then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end

local function areaRects(base)
    local out = {}
    for _, z in ipairs(type(base.zones) == "table" and base.zones or {}) do
        if type(z) == "table" and z.kind == "area" and tonumber(z.x1) and tonumber(z.x2) and tonumber(z.y1) and tonumber(z.y2) then
            out[#out + 1] = { x1 = math.min(z.x1, z.x2), x2 = math.max(z.x1, z.x2), y1 = math.min(z.y1, z.y2), y2 = math.max(z.y1, z.y2), z = tonumber(z.z) or 0 }
        end
    end
    return out
end
local function inRect(r, x, y) return x >= r.x1 and x <= r.x2 and y >= r.y1 and y <= r.y2 end
local function inAny(rects, x, y) for _, r in ipairs(rects) do if inRect(r, x, y) then return true end end return false end

-- what is inside a container, in the same terms Living Fellows uses (FarmWork.isFarmingSupply)
local TOOLWORDS = { "hammer", "saw", "screwdriver", "wrench", "axe", "shovel", "crowbar", "pliers", "hoe", "pickaxe", "trowel" }
local function classify(gu, cont)
    local items = call(gu.inventoryItems, cont, 80)
    if type(items) ~= "table" or #items == 0 then return "empty" end
    local n = { farming = 0, tool = 0, food = 0, water = 0, total = #items }
    for _, it in ipairs(items) do
        local kind = string.lower(tostring(call(gu.itemType, it) or ""))
        if call(gu.itemHasTag, it, "DIG_PLOW") or call(gu.itemHasTag, it, "COMPOST") or string.find(kind, "seed", 1, true)
            or string.find(kind, "wateredcan", 1, true) or string.find(kind, "wateringcan", 1, true) or string.find(kind, "compostbag", 1, true)
            or string.find(kind, "gardeningspray", 1, true) or string.find(kind, "slugrepellent", 1, true) then
            n.farming = n.farming + 1
        else
            local isTool = call(gu.itemHasTag, it, "CLEAN_STAINS") and true or false
            for _, w in ipairs(TOOLWORDS) do if string.find(kind, w, 1, true) then isTool = true break end end
            if isTool then n.tool = n.tool + 1
            elseif string.find(kind, "waterbottle", 1, true) or string.find(kind, "waterdispenser", 1, true) or string.find(kind, "bucketwater", 1, true) then n.water = n.water + 1
            elseif method(it, "getCategory") == "Food" then n.food = n.food + 1 end
        end
    end
    if n.farming >= 1 and n.farming * 3 >= n.total then return "farming" end
    if n.food >= 1 and n.food * 2 >= n.total then return "food" end
    if n.tool >= 1 and n.tool * 2 >= n.total then return "tool" end
    if n.water >= 1 and n.water * 2 >= n.total then return "water" end
    return "general"
end

local function neighbours(plantSet, x, y)
    local out = {}
    for dx = -3, 3 do for dy = -3, 3 do
        local k = (x + dx) * 65536 + (y + dy)
        if plantSet[k] and not (dx == 0 and dy == 0) then out[#out + 1] = k end
    end end
    return out
end

-- plants -> groups (gaps of up to 3 tiles are bridged: paths between beds) -> rectangles of at most CHUNK x CHUNK
local function farmRects(plants, z)
    local set, idx = {}, {}
    for i, p in ipairs(plants) do set[p.x * 65536 + p.y] = i; idx[i] = p end
    local seen, rects = {}, {}
    for i, p in ipairs(plants) do
        local k0 = p.x * 65536 + p.y
        if not seen[k0] then
            local queue, head, minx, maxx, miny, maxy = { k0 }, 1, p.x, p.x, p.y, p.y
            seen[k0] = true
            local members = {}
            while queue[head] do
                local k = queue[head]; head = head + 1
                local q = idx[set[k]]
                members[#members + 1] = q
                if q.x < minx then minx = q.x end; if q.x > maxx then maxx = q.x end
                if q.y < miny then miny = q.y end; if q.y > maxy then maxy = q.y end
                for _, nk in ipairs(neighbours(set, q.x, q.y)) do
                    if not seen[nk] then seen[nk] = true; queue[#queue + 1] = nk end
                end
            end
            if (maxx - minx + 1) <= CHUNK and (maxy - miny + 1) <= CHUNK then
                rects[#rects + 1] = { x1 = minx, y1 = miny, x2 = maxx, y2 = maxy, z = z, n = #members }
            else
                local blocks = {}
                for _, q in ipairs(members) do
                    local bx, by = math.floor((q.x - minx) / CHUNK), math.floor((q.y - miny) / CHUNK)
                    local bk = bx * 1000 + by
                    local b = blocks[bk]
                    if not b then b = { x1 = q.x, y1 = q.y, x2 = q.x, y2 = q.y, z = z, n = 0 }; blocks[bk] = b end
                    if q.x < b.x1 then b.x1 = q.x end; if q.x > b.x2 then b.x2 = q.x end
                    if q.y < b.y1 then b.y1 = q.y end; if q.y > b.y2 then b.y2 = q.y end
                    b.n = b.n + 1
                end
                local keys = {}
                for bk in pairs(blocks) do keys[#keys + 1] = bk end
                table.sort(keys)
                for _, bk in ipairs(keys) do rects[#rects + 1] = blocks[bk] end
            end
        end
    end
    return rects
end

local function covered(zones, x, y, z)
    for _, zn in ipairs(zones) do
        if type(zn) == "table" and zn.kind == "farm" and (tonumber(zn.z) or 0) == z
            and x >= math.min(zn.x1, zn.x2) and x <= math.max(zn.x1, zn.x2) and y >= math.min(zn.y1, zn.y2) and y <= math.max(zn.y1, zn.y2) then return true end
    end
    return false
end

function U.baseScan()
    local sc = LF()
    local BL = sc and sc.BaseLife or nil
    local gu = sc and sc.GameplayUtil or nil
    if type(BL) ~= "table" or type(gu) ~= "table" then return false, "lf_unavailable" end
    local base = call(BL.active)
    if type(base) ~= "table" then return false, "base_missing" end
    local cell = getCell and getCell() or nil
    if cell == nil then return false, "no_cell" end
    local rects = areaRects(base)
    if #rects == 0 then return false, "no_area_zone" end
    local zones = type(base.zones) == "table" and base.zones or {}
    local system = type(CFarmingSystem) == "table" and CFarmingSystem.instance or nil
    local t0, visited, partial = nowMs(), 0, false
    local plants, containers, seen = {}, {}, {}
    local z0 = rects[1].z
    for _, r in ipairs(rects) do
        for x = r.x1 - MARGIN, r.x2 + MARGIN do
            for y = r.y1 - MARGIN, r.y2 + MARGIN do
                local key = (x * 65536 + y) * 16 + r.z
                if not seen[key] then
                    seen[key] = true
                    visited = visited + 1
                    if visited > MAX_SQUARES or (visited % 400 == 0 and nowMs() - t0 > MAX_MS) then partial = true break end
                    local sq = method(cell, "getGridSquare", x, y, r.z)
                    if sq ~= nil then
                        if system ~= nil and method(system, "getLuaObjectOnSquare", sq) ~= nil
                            and (type(BL.withinWorkReach) ~= "function" or call(BL.withinWorkReach, sq) == true)
                            and not covered(zones, x, y, r.z) then
                            plants[#plants + 1] = { x = x, y = y }
                        end
                        if inAny(rects, x, y) then
                            local objs = method(sq, "getObjects")
                            local n = objs and tonumber((method(objs, "size"))) or 0
                            for i = 0, n - 1 do
                                local o = method(objs, "get", i)
                                if o ~= nil and not (type(instanceof) == "function" and instanceof(o, "IsoDeadBody")) then
                                    for ci = 0, (tonumber((method(o, "getContainerCount"))) or 0) - 1 do       -- a fridge has a freezer too
                                        local c = method(o, "getContainerByIndex", ci)
                                        if c ~= nil then containers[#containers + 1] = { obj = o, x = x, y = y, z = r.z, cont = c, type = tostring(method(c, "getType") or "?") } end
                                    end
                                end
                            end
                        end
                    end
                end
            end
            if partial then break end
        end
        if partial then break end
    end
    -- farm zones, limited by the free slots LF has
    local maxZones = tonumber((call(gu.config, "baseMaxZones"))) or MAX_ZONES_DEFAULT      -- the extra parentheses keep ONE value: PZ's Lua rejects tonumber(x, nil)
    local free = math.max(0, maxZones - #zones)
    local farm = farmRects(plants, z0)
    local trimmed = false
    while #farm > free do table.remove(farm); trimmed = true end
    -- containers: classify, then propose the minimum
    local cls, byClass = {}, { farming = {}, food = {}, tool = {}, water = {}, general = {}, empty = {} }
    for _, c in ipairs(containers) do
        c.class = classify(gu, c.cont)
        cls[c.class] = (cls[c.class] or 0) + 1
        byClass[c.class][#byClass[c.class] + 1] = c
    end
    local cx, cy, np = 0, 0, #plants
    for _, p in ipairs(plants) do cx = cx + p.x; cy = cy + p.y end
    if np > 0 then cx, cy = cx / np, cy / np end
    local function nearest(list)
        local best, bd
        for _, c in ipairs(list) do
            local d = (c.x - cx) ^ 2 + (c.y - cy) ^ 2
            if not bd or d < bd then best, bd = c, d end
        end
        return best
    end
    local regs = {}
    for i, c in ipairs(byClass.farming) do if i <= 3 then regs[#regs + 1] = { cat = "farming", c = c } end end
    if byClass.tool[1] then regs[#regs + 1] = { cat = "tools", c = nearest(byClass.tool) } end
    if byClass.water[1] then regs[#regs + 1] = { cat = "water", c = nearest(byClass.water) } end
    local pool = {}
    for _, c in ipairs(byClass.empty) do pool[#pool + 1] = c end
    for _, c in ipairs(byClass.general) do pool[#pool + 1] = c end
    local function has(t, ...) for _, w in ipairs({ ... }) do if string.find(t, w, 1, true) then return true end end return false end
    local function outRank(c)       -- where harvest may go: crates and shelves first; furniture people live in is never proposed
        local t = string.lower(tostring(c.type))
        if has(t, "wardrobe", "dresser", "sidetable", "nightstand", "desk", "fridge", "freezer", "medicine", "stove", "oven", "microwave", "shoerack", "toolbox") then return 9 end
        if has(t, "crate", "box") then return 1 end
        if has(t, "shelf", "shelves", "display") then return 2 end
        if has(t, "locker") then return 3 end
        return 5
    end
    local function foodRank(c)
        local t = string.lower(tostring(c.type))
        if has(t, "fridge", "freezer") then return 1 end
        if has(t, "shelf", "shelves", "counter") then return 2 end
        if has(t, "crate", "box") then return 3 end
        return 5
    end
    local function best(list, rank, limit)
        local pick, pr, pd
        for _, c in ipairs(list) do
            local r = rank(c)
            if r < limit then
                local d = (c.x - cx) ^ 2 + (c.y - cy) ^ 2
                if not pick or r < pr or (r == pr and d < pd) then pick, pr, pd = c, r, d end
            end
        end
        return pick
    end
    local out = best(pool, outRank, 9)
    if out then regs[#regs + 1] = { cat = "output", c = out } end
    local food = best(byClass.food, foodRank, 99)
    if food then regs[#regs + 1] = { cat = "food", c = food } end
    -- never propose a storage LF already has registered
    local have = {}
    for _, s in ipairs(type(base.storages) == "table" and base.storages or {}) do if type(s) == "table" and s.x then have[s.x * 65536 + (s.y or 0)] = true end end
    local keep = {}
    for _, r in ipairs(regs) do if not have[r.c.x * 65536 + r.c.y] then keep[#keep + 1] = r end end
    U.baseProposal = (#farm + #keep > 0) and { at = nowMs(), farm = farm, regs = keep } or nil     -- nothing new: nothing to apply
    local zt, rt = {}, {}
    for _, f in ipairs(farm) do zt[#zt + 1] = f.x1 .. "," .. f.y1 .. "," .. f.x2 .. "," .. f.y2 .. "," .. f.n end
    for _, r in ipairs(keep) do rt[#rt + 1] = r.cat .. "@" .. r.c.x .. "," .. r.c.y .. "," .. r.c.type end
    local ct = {}
    for _, k in ipairs({ "farming", "tool", "food", "water", "general", "empty" }) do if (cls[k] or 0) > 0 then ct[#ct + 1] = k .. ":" .. cls[k] end end
    local text = "scan;plants=" .. np .. ";sq=" .. visited .. ";partial=" .. (partial and 1 or 0) .. ";trim=" .. (trimmed and 1 or 0)
        .. ";cont=" .. #containers .. ";cls=" .. table.concat(ct, ",")
        .. ";zones=" .. table.concat(zt, "|") .. ";regs=" .. table.concat(rt, "|")
    if string.len(text) > 900 then text = string.sub(text, 1, 900) end
    return true, text
end

function U.baseApply()
    local p = U.baseProposal
    if type(p) ~= "table" then return false, "apply;none" end
    if nowMs() - (p.at or 0) > TTL_MS then U.baseProposal = nil; return false, "apply;stale" end
    local sc = LF()
    local BL = sc and sc.BaseLife or nil
    local cell = getCell and getCell() or nil
    if type(BL) ~= "table" or cell == nil then return false, "apply;lf_unavailable" end
    local zok, zall, rok, rall, fails = 0, #p.farm, 0, #p.regs, {}
    for _, f in ipairs(p.farm) do
        local a = method(cell, "getGridSquare", f.x1, f.y1, f.z)
        local b = method(cell, "getGridSquare", f.x2, f.y2, f.z)
        if a == nil or b == nil then
            fails[#fails + 1] = "farm@" .. f.x1 .. "," .. f.y1 .. ":unloaded"
        else
            local ok1, why1 = call(BL.beginZone, "farm", a)
            if ok1 ~= true then
                fails[#fails + 1] = "farm@" .. f.x1 .. "," .. f.y1 .. ":" .. tostring(why1)
            else
                local ok2, why2 = call(BL.finishZone, b, "farm")
                if ok2 == true then zok = zok + 1 else
                    call(BL.cancelZone)
                    fails[#fails + 1] = "farm@" .. f.x1 .. "," .. f.y1 .. ":" .. tostring(why2)
                end
            end
        end
    end
    for _, r in ipairs(p.regs) do
        local ok, why = call(BL.registerStorage, r.c.obj, r.cat)
        if ok == true then rok = rok + 1 else fails[#fails + 1] = r.cat .. "@" .. r.c.x .. "," .. r.c.y .. ":" .. tostring(why) end
    end
    U.baseProposal = nil
    local text = "apply;zones=" .. zok .. "/" .. zall .. ";regs=" .. rok .. "/" .. rall .. ";fail=" .. table.concat(fails, "|")
    if string.len(text) > 900 then text = string.sub(text, 1, 900) end
    return (zok + rok) > 0 or (zall + rall) == 0, text
end

local function install()
    if U._baseScanInstalled then return end
    U._baseScanInstalled = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "sol_base_scan" then
            local ok, a, b = pcall(U.baseScan)
            if not ok then return false, "scan_error" end
            return a, b
        elseif id == "sol_base_apply" then
            local ok, a, b = pcall(U.baseApply)
            if not ok then return false, "apply_error" end
            return a, b
        end
        return base(id, option)
    end
    log("verbs installed v" .. U.BASESCAN_VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(install) end
log("ready v" .. U.BASESCAN_VERSION)

-- SolGearRecover.lua - switch gear_recover (s97). Live 2026-11-11 10:40:51: Sol vaulted the porch railing, fell, her helmet came
-- off ("IsoFallingClothing added x=7406.197 y=8258.394") and she never picked it up or put it back on.
--   remember  every second the items she wears and holds are noted (item id, type, body location or hand) in ModData
--             "SolGearRecover", so her own gear is known after a reload too.
--   fall      every 250 ms her state is read: a fall, trip, knockdown, bump, lying on the ground, getting up, a fence or window
--             climb (action state names, isOnFloor, isKnockedDown, isBumpFall) marks the time.
--   lost      a worn or held item that is no longer anywhere in her inventory, within FALL_WINDOW_MS of such a moment (headwear and
--             glasses also without one: only a hit or a fall takes them off) -> pending, with the square where it happened.
--   recover   a pending item is looked for on the floor within SCAN_TILES of that square and of her (its id, else its type
--             near that square), PENDING_MS long (it may still be falling). When she is calm (no zombie she perceives within
--             CALM_SEEN tiles, none on her floor within CALM_CLOSE) and free (not driving, not sorting, no SolPlace walk running,
--             her order follow or stay): next to it she takes it at once (LF takeWorldItemVerified) and puts it back on (its body
--             location, when that place is free) or back in her hand (when her hand is empty; both hands for a two-handed one);
--             up to WALK_MAX tiles away she walks there first (U.solGoto); following him, she follows again after.
--   load      once after a load or after the switch comes on: any remembered item of hers that is not on her and lies within
--             SCAN_TILES of her is recovered the same way.
--   verb      sol_gear status | take   (take: Jamal's order, the wearable items lying within SCAN_TILES whose place on her is free)
-- Switch off: nothing is read or done.
SolGearRecover = SolGearRecover or {}
local M = SolGearRecover
M.VERSION = "0.1.0"
M.POLL_MS, M.WORN_MS = 250, 1000
M.FALL_WINDOW_MS = 15000
M.SCAN_TILES = 3
M.PENDING_MS = 120000
M.WALK_MAX = 12
M.WALK_MS = 20000
M.RETRY_MS = 30000
M.CALM_SEEN, M.CALM_CLOSE = 8, 3
M.STORE = "SolGearRecover"
M.FALL_STATES = { falldown = true, fall = true, falling = true, knockeddown = true, bumped = true, onground = true, getup = true,
    staggerback = true, climbfence = true, climbwindow = true, climbwall = true, playerfalldown = true, playerknockeddown = true,
    playerongroundstate = true, playergetup = true, fallonfront = true }
M.HEAD_WORDS = { "hat", "helmet", "mask", "eye", "head", "scba" }

local rawTonumber = tonumber
local function tonumber(v) return rawTonumber(v) end
local function g(name) return rawget(_G, name) end
local function nowMs() local f = g("getTimestampMs"); return f and f() or 0 end
local function log(m) print("[SolGearRecover] " .. tostring(m)) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, r = pcall(f, o, ...)
    if ok then return r end
    return nil
end
local function on()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("gear_recover") == true
end
M.on = on
local function U() return g("SolUI") or {} end
local function solActor() local f = U().solActor; if type(f) ~= "function" then return nil end; local ok, a = pcall(f); return ok and a or nil end
local function SC() local s = g("SurvivorCompanion"); return type(s) == "table" and s or nil end
local function GU() local s = SC(); return s and type(s.GameplayUtil) == "table" and s.GameplayUtil or nil end
local function pos(o)
    local x, y, z = tonumber((call(o, "getX"))), tonumber((call(o, "getY"))), tonumber((call(o, "getZ")))
    if x == nil or y == nil then return nil end
    return x, y, z or 0
end
local function idOf(item)
    local v = call(item, "getID")
    if v == nil then return nil end
    return tostring(v)
end
local function fullType(item) return tostring(call(item, "getFullType") or "?") end
-- headwear and glasses: a location name with hat, helmet, mask, eye or head in it ("Hat", "FullHat", "base:hat", "Eyes" ...)
function M.isHead(loc)
    local s = string.lower(tostring(loc or ""))
    for _, w in ipairs(M.HEAD_WORDS) do if string.find(s, w, 1, true) then return true end end
    return false
end

-- ---------------------------------------------------------------- the store (ModData, kept per LF id)
local function store(a)
    local MD = g("ModData")
    if type(MD) ~= "table" or type(MD.getOrCreate) ~= "function" then M._mem = M._mem or {}; return M._mem end
    local ok, d = pcall(MD.getOrCreate, M.STORE)
    if not ok or type(d) ~= "table" then M._mem = M._mem or {}; return M._mem end
    local key = "sol"
    local gu = GU()
    if gu and type(gu.idOf) == "function" and a ~= nil then
        local okI, id = pcall(gu.idOf, a)
        if okI and type(id) == "string" and id ~= "" then key = id end
    end
    d[key] = d[key] or {}
    local s = d[key]
    s.worn = s.worn or {}
    s.pending = s.pending or {}
    return s
end
M.store = store

-- ---------------------------------------------------------------- what she has on and in her hands
function M.snapshot(a)
    local out = {}
    local worn = call(a, "getWornItems")
    local n = tonumber((worn and call(worn, "size"))) or 0
    for i = 0, n - 1 do
        local w = call(worn, "get", i)
        local item = call(w, "getItem")
        local id = idOf(item)
        local raw = call(w, "getLocation") or call(item, "getBodyLocation")
        if id ~= nil then out[id] = { item = item, id = id, ft = fullType(item), loc = tostring(raw or ""), rawLoc = raw, kind = "worn" } end
    end
    local p = call(a, "getPrimaryHandItem")
    local s = call(a, "getSecondaryHandItem")
    if p ~= nil and idOf(p) ~= nil then out[idOf(p)] = { item = p, id = idOf(p), ft = fullType(p), kind = "primary", two = (s == p) } end
    if s ~= nil and s ~= p and idOf(s) ~= nil then out[idOf(s)] = { item = s, id = idOf(s), ft = fullType(s), kind = "secondary" } end
    return out
end
local function hasItem(a, e)
    local inv = call(a, "getInventory")
    if inv == nil then return true end                                     -- cannot tell: not lost
    if e.item ~= nil then
        local r = call(inv, "containsRecursive", e.item)
        if r == nil then r = call(inv, "contains", e.item) end
        if r ~= nil then return r == true end
    end
    local n = tonumber(e.id)
    if n ~= nil then
        local r = call(inv, "containsID", n)
        if r ~= nil then return r == true end
    end
    return true
end

-- ---------------------------------------------------------------- calm and free
function M.calm(a)
    local SP = g("SolPlace")
    local gu = GU()
    local ax, ay, az = pos(a)
    if ax == nil then return false end
    if gu and type(gu.peekActorState) == "function" then
        local ok, st = pcall(gu.peekActorState, a)
        local th = ok and type(st) == "table" and type(st.snapshot) == "table" and st.snapshot.threats or nil
        if type(th) == "table" then
            for i = 1, math.min(#th, 32) do
                local d = type(th[i]) == "table" and tonumber((th[i].distanceSq)) or nil
                if d ~= nil and d <= M.CALM_SEEN * M.CALM_SEEN then return false end
            end
        end
    end
    local f = g("getCell")
    local c = f and f() or nil
    local list = c and call(c, "getZombieList")
    local n = tonumber((list and call(list, "size"))) or 0
    for i = 0, math.min(n, 400) - 1 do
        local zb = call(list, "get", i)
        local zx, zy, zz = pos(zb)
        if zx ~= nil and math.floor(zz) == math.floor(az) and (zx - ax) * (zx - ax) + (zy - ay) * (zy - ay) <= M.CALM_CLOSE * M.CALM_CLOSE
                and call(zb, "isDead") ~= true then return false end
    end
    if type(SP) == "table" and type(SP.flee) == "function" and SP.flee(a) == true then return false end
    return true
end
local function lfOrder(a)
    local s = SC()
    local C = s and s.Commands
    if type(C) ~= "table" or type(C.peek) ~= "function" then return nil end
    local ok, st = pcall(C.peek, a)
    if ok and type(st) == "table" then return st.order end
    return nil
end
function M.free(a)
    if call(a, "getVehicle") ~= nil then return false, "in_car" end
    local held = U().solSortHeld
    if type(held) == "function" then local ok, v = pcall(held); if ok and v == true then return false, "sorting" end end
    local SP = g("SolPlace")
    if type(SP) == "table" and SP.R ~= nil and M.walk == nil then return false, "walking" end
    local o = lfOrder(a)
    if o ~= nil and o ~= "follow" and o ~= "stay" and not (M.walk and o == "move_to") then return false, "order_" .. tostring(o) end
    return true
end

-- ---------------------------------------------------------------- the falls
function M.fallen(a)
    local s = string.lower(tostring(call(a, "getActionStateName") or ""))
    if M.FALL_STATES[s] then return true, s end
    if call(a, "isOnFloor") == true then return true, "on_floor" end
    if call(a, "isKnockedDown") == true then return true, "knocked_down" end
    if call(a, "isBumpFall") == true then return true, "bump_fall" end
    return false
end

-- ---------------------------------------------------------------- the floor
local function worldItemsNear(cx, cy, z, r, visit)
    local f = g("getCell")
    local c = f and f() or nil
    if c == nil then return end
    cx, cy, z = math.floor(cx), math.floor(cy), math.floor(z or 0)
    for x = cx - r, cx + r do
        for y = cy - r, cy + r do
            local sq = call(c, "getGridSquare", x, y, z)
            local objs = sq and call(sq, "getWorldObjects")
            local n = tonumber((objs and call(objs, "size"))) or 0
            for i = 0, n - 1 do
                local wo = call(objs, "get", i)
                local item = call(wo, "getItem")
                if item ~= nil and visit(wo, item, sq, x, y, z) == true then return end
            end
        end
    end
end
-- the floor copy of a pending entry: its id first; its type near the place it was lost (ids may be new after a reload)
function M.find(a, e)
    local ax, ay, az = pos(a)
    local hit
    local function byId(wo, item, sq, x, y, z)
        if idOf(item) == e.id then hit = { wo = wo, item = item, sq = sq, x = x, y = y, z = z }; return true end
    end
    if e.x ~= nil then worldItemsNear(e.x, e.y, e.z, M.SCAN_TILES, byId) end
    if hit == nil and ax ~= nil then worldItemsNear(ax, ay, az, M.SCAN_TILES, byId) end
    if hit == nil and e.x ~= nil then
        worldItemsNear(e.x, e.y, e.z, M.SCAN_TILES, function(wo, item, sq, x, y, z)
            if fullType(item) == e.ft then hit = { wo = wo, item = item, sq = sq, x = x, y = y, z = z }; return true end
        end)
    end
    return hit
end

-- ---------------------------------------------------------------- take it and put it back on
function M.putBack(a, e, item)
    if e.kind == "worn" then
        local loc = call(item, "getBodyLocation") or M.rawLoc[e.id]           -- the game's own location value (a string or a location object)
        if loc == nil or tostring(loc) == "" then return "in_bag" end
        local cur = call(a, "getWornItem", loc)
        if cur ~= nil and cur ~= item then return "in_bag (" .. tostring(loc) .. " taken)" end
        local ok = pcall(function() return a:setWornItem(loc, item) end)
        call(a, "resetModelNextFrame")
        if ok and call(a, "getWornItem", loc) == item then return "worn " .. tostring(loc) end
        return ok and ("worn " .. tostring(loc)) or "in_bag"
    end
    if call(item, "isBroken") == true then return "in_bag (broken)" end
    local p, s = call(a, "getPrimaryHandItem"), call(a, "getSecondaryHandItem")
    local two = call(item, "isTwoHandWeapon") == true or call(item, "isRequiresEquippedBothHands") == true or e.two == true
    if e.kind == "primary" or e.kind == "secondary" then
        if e.kind == "primary" and p == nil and (not two or s == nil) then
            pcall(function() a:setPrimaryHandItem(item) end)
            if two then pcall(function() a:setSecondaryHandItem(item) end) end
            call(a, "resetModelNextFrame")
            return "in hand"
        end
        if e.kind == "secondary" and s == nil then
            pcall(function() a:setSecondaryHandItem(item) end)
            call(a, "resetModelNextFrame")
            return "in hand"
        end
    end
    return "in_bag (hands busy)"
end
function M.take(a, e, hit)
    local inv = call(a, "getInventory")
    local gu = GU()
    if inv == nil then return false, "no_inventory" end
    local ok, done, why = false, false, nil
    if gu and type(gu.takeWorldItemVerified) == "function" then
        ok, done, why = pcall(gu.takeWorldItemVerified, hit.wo, inv, hit.item)
        if not ok then done, why = false, tostring(done) end
    else
        local sq = hit.sq
        pcall(function() sq:transmitRemoveItemFromSquare(hit.wo) end)
        pcall(function() sq:removeWorldObject(hit.wo) end)
        pcall(function() hit.wo:removeFromWorld() end)
        pcall(function() hit.wo:removeFromSquare() end)
        pcall(function() hit.item:setWorldItem(nil) end)
        pcall(function() inv:AddItem(hit.item) end)
        done = call(inv, "contains", hit.item) == true
        why = done and "taken" or "add_failed"
    end
    if done ~= true then return false, tostring(why) end
    local where = M.putBack(a, e, hit.item)
    return true, where
end

-- ---------------------------------------------------------------- the runner
M.last = nil
M.fallAt, M.fallWhy = -1e9, nil
M.walk = nil              -- { id, x, y, at, prevOrder }
M.rawLoc = M.rawLoc or {}
M.loadPass = false
M.stats = M.stats or { lost = 0, recovered = 0, walks = 0, notFound = 0 }
local function remember(s, snap)
    local w = {}
    for id, e in pairs(snap) do w[id] = { ft = e.ft, loc = e.loc, kind = e.kind, two = e.two } end
    s.worn = w
end
local function pendingCount(s) local n = 0; for _ in pairs(s.pending) do n = n + 1 end; return n end

function M.notice(a, t)
    local fell, why = M.fallen(a)
    if fell then M.fallAt, M.fallWhy = t, why end
    if M.lastWornAt ~= nil and t - M.lastWornAt < M.WORN_MS then return end
    M.lastWornAt = t
    local s = store(a)
    local snap = M.snapshot(a)
    local ax, ay, az = pos(a)
    if M.last ~= nil then
        for id, e in pairs(M.last) do
            if snap[id] == nil and s.pending[id] == nil and not hasItem(a, e) then
                local head = e.kind == "worn" and M.isHead(e.loc)
                if t - M.fallAt <= M.FALL_WINDOW_MS or head then
                    M.rawLoc[id] = e.rawLoc                                          -- session only: ModData keeps plain values
                    s.pending[id] = { id = id, ft = e.ft, loc = e.loc, kind = e.kind, two = e.two, at = t, x = M.lastX or ax, y = M.lastY or ay,
                        z = M.lastZ or az, why = (t - M.fallAt <= M.FALL_WINDOW_MS) and tostring(M.fallWhy) or "came_off" }
                    M.stats.lost = M.stats.lost + 1
                    log("lost " .. e.ft .. " (" .. tostring(e.kind == "worn" and e.loc or e.kind) .. ") after " .. s.pending[id].why
                        .. " near " .. math.floor(s.pending[id].x or 0) .. "," .. math.floor(s.pending[id].y or 0))
                end
            end
        end
    end
    M.last = snap
    M.lastX, M.lastY, M.lastZ = ax, ay, az
    remember(s, snap)
end

-- once after a load or the switch coming on: remembered gear of hers lying near her
function M.loadScan(a, t)
    local s = store(a)
    local ax, ay, az = pos(a)
    if ax == nil then return end
    local snap = M.snapshot(a)
    local found = 0
    for id, e in pairs(s.worn or {}) do
        if snap[id] == nil and s.pending[id] == nil then
            local item
            worldItemsNear(ax, ay, az, M.SCAN_TILES, function(wo, it) if idOf(it) == id then item = it; return true end end)
            if item ~= nil then
                s.pending[id] = { id = id, ft = e.ft, loc = e.loc, kind = e.kind, two = e.two, at = t, x = ax, y = ay, z = az, why = "found_on_load" }
                found = found + 1
            end
        end
    end
    log("load pass: " .. found .. " remembered item(s) of hers lying near her, " .. pendingCount(s) .. " pending")
end

function M.recover(a, t)
    local s = store(a)
    local e
    for _, p in pairs(s.pending) do if (p.retryAt or 0) <= t then e = p; break end end
    if e == nil then return end
    if t - (e.at or t) > M.PENDING_MS and M.walk == nil then
        local hit = M.find(a, e)
        if hit == nil then
            s.pending[e.id] = nil
            M.stats.notFound = M.stats.notFound + 1
            log("gave up on " .. tostring(e.ft) .. ": not on the floor near " .. math.floor(e.x or 0) .. "," .. math.floor(e.y or 0))
            return
        end
    end
    if not M.calm(a) then return end
    local okF, why = M.free(a)
    if not okF then return end
    local hit = M.find(a, e)
    if hit == nil then e.retryAt = t + 2000; return end                      -- still in the air, or not there yet
    local ax, ay, az = pos(a)
    local d = math.max(math.abs(math.floor(ax) - hit.x), math.abs(math.floor(ay) - hit.y))
    local SP = g("SolPlace")
    local near = d == 0 or (d == 1 and (type(SP) ~= "table" or type(SP.reach) ~= "function" or SP.reach(math.floor(ax), math.floor(ay), hit.z, hit.x, hit.y)))
    if near and math.floor(az) == hit.z then
        local ok, where = M.take(a, e, hit)
        if ok then
            s.pending[e.id] = nil
            M.stats.recovered = M.stats.recovered + 1
            log("picked up " .. tostring(e.ft) .. " at " .. hit.x .. "," .. hit.y .. ": " .. tostring(where))
            local w = M.walk
            M.walk = nil
            if w ~= nil and w.prevOrder == "follow" and type(U().issueLF) == "function" then pcall(U().issueLF, "follow") end
            M.lastWornAt = nil
        else
            e.retryAt = t + 3000
            log("could not pick up " .. tostring(e.ft) .. ": " .. tostring(where))
        end
        return
    end
    if d > M.WALK_MAX or math.floor(az) ~= hit.z then e.retryAt = t + M.RETRY_MS; return end
    local w = M.walk
    if w ~= nil and w.id == e.id and t - w.at > M.WALK_MS then
        log("walk to " .. tostring(e.ft) .. " at " .. hit.x .. "," .. hit.y .. " did not get there; later")
        M.walk = nil
        e.retryAt = t + M.RETRY_MS
        return
    end
    if w == nil or w.id ~= e.id or t - (w.sentAt or 0) > 4000 then
        local go = U().solGoto
        if type(go) ~= "function" then return end
        if w == nil or w.id ~= e.id then
            w = { id = e.id, at = t, prevOrder = lfOrder(a) }
            M.walk = w
            M.stats.walks = M.stats.walks + 1
            log("walking to " .. tostring(e.ft) .. " at " .. hit.x .. "," .. hit.y .. " (" .. d .. " tiles)")
        end
        w.sentAt = t
        pcall(go, hit.x, hit.y, hit.z)
    end
end

function M.tick()
    if not on() then M.loadPass, M.last = false, nil; return end
    local a = solActor()
    if a == nil then return end
    local t = nowMs()
    if not M.loadPass then M.loadPass = true; pcall(M.loadScan, a, t) end   -- before the first snapshot replaces the remembered list
    M.notice(a, t)
    local ok, err = pcall(M.recover, a, t)
    if not ok then log("error " .. tostring(err)) end
end

-- verbs: sol_gear status | take
function M.order(option)
    option = string.lower(tostring(option or "status"))
    local a = solActor()
    if a == nil then return false, "no_sol" end
    local s = store(a)
    if option == "take" then
        local ax, ay, az = pos(a)
        local n = 0
        worldItemsNear(ax, ay, az, M.SCAN_TILES, function(wo, item, sq, x, y, z)
            local loc = tostring(call(item, "getBodyLocation") or "")
            if loc ~= "" and call(a, "getWornItem", loc) == nil and idOf(item) ~= nil and s.pending[idOf(item)] == nil then
                s.pending[idOf(item)] = { id = idOf(item), ft = fullType(item), loc = loc, kind = "worn", at = nowMs(), x = x, y = y, z = z, why = "his_order" }
                n = n + 1
            end
        end)
        return true, "pending " .. n .. " wearable item(s) within " .. M.SCAN_TILES .. " tiles"
    end
    local worn = 0
    for _ in pairs(s.worn or {}) do worn = worn + 1 end
    local st = M.stats
    return true, string.format("on=%s remembered=%d pending=%d lost=%d recovered=%d walks=%d notFound=%d", tostring(on()), worn, pendingCount(s),
        st.lost, st.recovered, st.walks, st.notFound)
end

function M.install()
    if M._installed then return end
    M._installed = true
    local base = U().runAction
    if type(base) == "function" then
        U().runAction = function(id, option)
            if id == "sol_gear" then return M.order(option) end
            return base(id, option)
        end
    end
    if Events and Events.OnTick and type(Events.OnTick.Add) == "function" then
        local nextAt = 0
        Events.OnTick.Add(function()
            local t = nowMs()
            if t < nextAt then return end
            nextAt = t + M.POLL_MS
            local ok, err = pcall(M.tick)
            if not ok then log("error " .. tostring(err)) end
        end)
    end
    log("ready v" .. M.VERSION .. " (switch gear_recover=" .. tostring(on()) .. ")")
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(function() pcall(M.install) end) end
return M

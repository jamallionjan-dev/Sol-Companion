-- SolMagFill.lua - switch mag_fill (2026-11-11, s99). She loads her magazines herself.
-- Live 11:59-12:04: "carry this weapon" on the G28 -> "no_usable_weapon (empty)"; she carries ~500 loose 7.62x51 rounds and
-- no loaded magazine. LF (SCCombat) decides a firearm is usable from weapon.ammo (getCurrentAmmoCount only, the chambered
-- round not counted) and hasReloadAmmo (a magazine of gun:getMagazineType() holding rounds, found in LF's truncated item
-- scan). Loose rounds never fill a magazine on her: the game only does that inside its reload actions.
-- What this file does (switch read at call time, off = nothing):
--   loadedRounds(gun, ammo)  rounds the gun can fire now = getCurrentAmmoCount + 1 when a round is chambered (B42 racking
--                            moves one round from the count into the chamber: ISRackFirearm.lua:62-64). EFZ/Gunworks keep the
--                            same vanilla fields (TW/Runtime.lua:747-751 and 823-831) plus modData.AmmoList (logged if it
--                            disagrees, never trusted alone).
--   reloadReady(inv, gun)    a magazine gun: true when a COMPATIBLE magazine (Gunworks profile list,
--                            Magazine.GetMagazineTypesForGun, Magazine.lua:154; else gun:getMagazineType()) holds rounds,
--                            searched by the container's own recursive lookup (getAllTypeRecurse), so LF's 240-item scan
--                            budget does not hide it; false otherwise (loose rounds are not a reload in a fight). nil for a
--                            gun without magazines (LF decides).
--   the fill                 when she is idle (empty timed-action queue, not in a car) and safe (no living zombie within
--                            SAFE_TILES on her floor): an empty or partial compatible magazine is filled with loose rounds of a
--                            matching calibre (Gunworks Ammo.GetAutomaticReloadAmmoType, Ammo.lua:169; else the magazine's
--                            getAmmoType():getItemKey()), through Gunworks Magazine.reloadMagazine (Magazine.lua:194-210:
--                            transferBullets + ISLoadBulletsInMagazine with the round kind) or the vanilla path
--                            (ISReloadWeaponAction.lua:301-312). The gun in her hands with no magazine in it then gets
--                            ISInsertMagazine (it queues the rack itself, ISInsertMagazine.lua:52-53, and EFZ TWAutoRack
--                            adds one if missing, TW/AutoRack.lua:125-129); a loaded magazine with an empty chamber gets
--                            ISRackFirearm. One step per poll, only on her own queue (ISTimedActionQueue.add(action), the way
--                            SCNativeActions queues reload/unjam, SCNativeActions.lua:3464-3515).
--   triggers                 the gun in her hands; a gun asked for (request: an "empty" refusal, his carry order); her
--                            preferred gun (LF marker SC_ManualEquipFor). A zombie within SAFE_TILES: nothing starts and an
--                            action of ours that runs or waits is stopped (SolCombatEquipFallback's fallback stands).
--   speech                   plain Arabic, once per gun per minute: "<fill> G28" (decimal escapes, ASCII file).
SolMagFill = SolMagFill or {}
local M = SolMagFill
M.VERSION = "0.1.0"
M.SAFE_TILES = 6
M.POLL_MS = 2000
M.REQUEST_MS = 180000
M.SPEAK_MS = 60000
M.SCAN_ZOMBIES = 400
M.pending = M.pending or setmetatable({}, { __mode = "k" })
M.mine = M.mine or setmetatable({}, { __mode = "k" })
M.spoke = M.spoke or setmetatable({}, { __mode = "k" })
M.noted = M.noted or setmetatable({}, { __mode = "k" })
M.lastLog = M.lastLog or setmetatable({}, { __mode = "k" })

-- "I'm filling the magazine of the " (UTF-8 as decimal escapes) + short gun name
M.AR = {
    FILL = "\216\185\217\133 \216\185\216\168\217\145\217\138 \217\133\216\174\216\178\217\134 \216\167\217\132\217\128",
}

local rawTonumber = tonumber
local function num(v) return rawTonumber(v) end
local function g(name) return rawget(_G, name) end
local function nowMs() local f = g("getTimestampMs"); return f and f() or 0 end
local function log(m) print("[SolMagFill] " .. tostring(m)) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
function M.on()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("mag_fill") == true
end
local function short(it)
    local t = tostring(call(it, "getType") or call(it, "getFullType") or "")
    t = string.match(t, "([%w_]+)$") or t
    return t
end
local function fullType(it) return tostring(call(it, "getFullType") or "?") end
local function logOnce(actor, key, m)
    if actor == nil then log(m); return end
    if M.lastLog[actor] == key then return end
    M.lastLog[actor] = key
    log(m)
end
local function list(jl, cap)
    local out = {}
    if jl == nil then return out end
    if type(jl) == "table" and call(jl, "size") == nil then
        for i = 1, math.min(#jl, cap or 64) do out[#out + 1] = jl[i] end
        return out
    end
    local n = num((call(jl, "size"))) or 0
    for i = 0, math.min(n, cap or 64) - 1 do
        local it = call(jl, "get", i)
        if it ~= nil then out[#out + 1] = it end
    end
    return out
end

-- Gunworks modules (EFZ requires them: TW/AmmoKind.lua:13, TW_BulkMagazineReload.lua:7); nil without Gunworks.
local function gw(name)
    local loaded = type(package) == "table" and type(package.loaded) == "table" and package.loaded[name] or nil
    if type(loaded) == "table" then return loaded end
    local req = g("require")
    if type(req) ~= "function" then return nil end
    local ok, m = pcall(req, name)
    if ok and type(m) == "table" then return m end
    return nil
end
M.gw = gw

-- ---------------------------------------------------------------- state of a gun
function M.isRanged(item) return call(item, "isRanged") == true end

-- rounds the gun can fire now: the inserted magazine's count + the chambered round
function M.loadedRounds(item, ammo)
    if not M.on() or item == nil then return ammo end
    local cur = num((call(item, "getCurrentAmmoCount"))) or num(ammo) or 0
    if cur < 0 then cur = 0 end
    local n = cur
    if call(item, "isRoundChambered") == true then n = n + 1 end
    if call(item, "hasModData") == true then
        local md = call(item, "getModData")
        local al = type(md) == "table" and md.AmmoList or nil
        if type(al) == "table" and #al ~= n and M.noted[item] ~= #al .. "/" .. n then
            M.noted[item] = #al .. "/" .. n
            log(fullType(item) .. ": Gunworks AmmoList has " .. tostring(#al) .. " rounds, vanilla fields say " .. tostring(n) .. " (vanilla fields used)")
        end
    end
    return n
end

-- compatible magazine types: Gunworks profile (a part may change it), else the gun's own magazine type
function M.magTypes(gun)
    local out, seen = {}, {}
    local MG = gw("WeaponSystems/Utils/Magazine")
    if MG and type(MG.GetMagazineTypesForGun) == "function" then
        local ok, l = pcall(MG.GetMagazineTypesForGun, gun)
        if ok and type(l) == "table" then
            for _, t in ipairs(l) do if type(t) == "string" and t ~= "" and not seen[t] then seen[t] = true; out[#out + 1] = t end end
        end
    end
    local own = call(gun, "getMagazineType")
    if own ~= nil and tostring(own) ~= "" and not seen[tostring(own)] then out[#out + 1] = tostring(own) end
    return out
end

-- every compatible magazine she carries (the container's own recursive lookup, bags included)
function M.magazines(inventory, gun)
    local out = {}
    if inventory == nil then return out end
    for _, t in ipairs(M.magTypes(gun)) do
        for _, mag in ipairs(list(call(inventory, "getAllTypeRecurse", t), 32)) do
            out[#out + 1] = { item = mag, count = num((call(mag, "getCurrentAmmoCount"))) or 0, max = num((call(mag, "getMaxAmmo"))) or 0 }
        end
    end
    return out
end

-- LF asks this many times per combat pulse: the answer is kept READY_MS per (inventory, gun)
M.READY_MS = 500
M.ready = M.ready or setmetatable({}, { __mode = "k" })
function M.reloadReady(inventory, gun)
    if not M.on() or gun == nil then return nil end
    local byInv = inventory ~= nil and M.ready[inventory] or nil
    local c = byInv and byInv[gun] or nil
    local t = nowMs()
    if type(c) == "table" and t < c.expires then return c.value end
    local value
    if #M.magTypes(gun) > 0 then
        value = false
        for _, m in ipairs(M.magazines(inventory, gun)) do
            if m.count > 0 then value = true; break end
        end
    end
    if inventory ~= nil then
        if byInv == nil then byInv = setmetatable({}, { __mode = "k" }); M.ready[inventory] = byInv end
        byInv[gun] = { value = value, expires = t + M.READY_MS }
    end
    return value
end

-- the loose round kind that fits this magazine and that she has; nil when none
function M.roundKind(actor, mag)
    local A = gw("WeaponSystems/Utils/Ammo")
    if A and type(A.GetAutomaticReloadAmmoType) == "function" then
        local ok, k = pcall(A.GetAutomaticReloadAmmoType, actor, mag)
        if ok then return type(k) == "string" and k ~= "" and k or nil end
    end
    local at = call(mag, "getAmmoType")
    local key = at ~= nil and call(at, "getItemKey") or nil
    if type(key) ~= "string" or key == "" then return nil end
    local inv = call(actor, "getInventory")
    if (num((call(inv, "getCountTypeRecurse", key))) or 0) > 0 then return key end
    return nil
end

-- a magazine she can fill now (not full, matching rounds on her): fullest first, so one ends up full (ISFirearmRadialMenu.lua:86-93)
function M.fillable(actor, gun, skip)
    local inv = call(actor, "getInventory")
    local best, bestKind
    for _, m in ipairs(M.magazines(inv, gun)) do
        if m.item ~= skip and m.max > 0 and m.count < m.max then
            local kind = M.roundKind(actor, m.item)
            if kind ~= nil and (best == nil or m.count > best.count) then best, bestKind = m, kind end
        end
    end
    return best, bestKind
end

local function loadedMag(actor, gun)
    local best
    for _, m in ipairs(M.magazines(call(actor, "getInventory"), gun)) do
        if m.count > 0 and (best == nil or m.count > best.count) then best = m end
    end
    return best
end

local function fullMag(actor, gun)
    for _, m in ipairs(M.magazines(call(actor, "getInventory"), gun)) do
        if m.max > 0 and m.count >= m.max then return m end
    end
    return nil
end

-- ---------------------------------------------------------------- her situation
function M.zombieNear(actor, tiles)
    local ax, ay, az = num((call(actor, "getX"))), num((call(actor, "getY"))), num((call(actor, "getZ"))) or 0
    if ax == nil or ay == nil then return true end
    local f = g("getCell")
    local cell = f and f() or nil
    local zl = cell and call(cell, "getZombieList") or nil
    local n = num((call(zl, "size"))) or 0
    local r = tiles or M.SAFE_TILES
    for i = 0, math.min(n, M.SCAN_ZOMBIES) - 1 do
        local z = call(zl, "get", i)
        local zx, zy, zz = num((call(z, "getX"))), num((call(z, "getY"))), num((call(z, "getZ"))) or 0
        if zx ~= nil and zy ~= nil and math.floor(zz) == math.floor(az) and call(z, "isDead") ~= true
            and (zx - ax) * (zx - ax) + (zy - ay) * (zy - ay) <= r * r then
            return true
        end
    end
    return false
end
function M.safe(actor) return not M.zombieNear(actor, M.SAFE_TILES) end

local function queueOf(actor)
    local Q = g("ISTimedActionQueue")
    if type(Q) ~= "table" or type(Q.getTimedActionQueue) ~= "function" then return nil end
    local ok, q = pcall(Q.getTimedActionQueue, actor)
    if ok and type(q) == "table" then return q end
    return nil
end
function M.idle(actor)
    if call(actor, "getVehicle") ~= nil then return false end
    local q = queueOf(actor)
    if q == nil then return false end
    return q.current == nil and (type(q.queue) ~= "table" or #q.queue == 0)
end

local function snapshot(q)
    local s = {}
    for _, a in ipairs(q and type(q.queue) == "table" and q.queue or {}) do s[a] = true end
    return s
end
local function newActions(q, before)
    local out = {}
    for _, a in ipairs(q and type(q.queue) == "table" and q.queue or {}) do if not before[a] then out[#out + 1] = a end end
    return out
end

-- our actions still running or waiting
function M.busy(actor)
    local rec = M.mine[actor]
    if type(rec) ~= "table" then return false end
    local q = queueOf(actor)
    if q == nil then return false end
    for _, a in ipairs(rec.actions or {}) do
        if q.current == a then return true end
        for _, b in ipairs(type(q.queue) == "table" and q.queue or {}) do if b == a then return true end end
    end
    return false
end

-- a zombie came close: stop what is ours (never the rest of her queue)
function M.abort(actor, why)
    local rec = M.mine[actor]
    if type(rec) ~= "table" then return false end
    local q = queueOf(actor)
    local stopped = 0
    for _, a in ipairs(rec.actions or {}) do
        if q and q.current == a then
            if type(a.forceStop) == "function" then pcall(a.forceStop, a); stopped = stopped + 1 end
        elseif q and type(q.removeFromQueue) == "function" then
            for _, b in ipairs(type(q.queue) == "table" and q.queue or {}) do
                if b == a then pcall(q.removeFromQueue, q, a); stopped = stopped + 1; break end
            end
        end
    end
    M.mine[actor] = nil
    log("stopped (" .. tostring(why) .. "): " .. tostring(stopped) .. " action(s) of hers")
    return stopped > 0
end

-- ---------------------------------------------------------------- speech
local function speak(actor, gun)
    local key = fullType(gun)
    local last = M.spoke[actor]
    local t = nowMs()
    if type(last) == "table" and last.key == key and t - (last.at or 0) < M.SPEAK_MS then return false end
    M.spoke[actor] = { key = key, at = t }
    local line = M.AR.FILL .. short(gun)
    local O = g("SolOverlay")
    local shown = false
    if type(O) == "table" and type(O.speak) == "function" then
        local ok, r = pcall(O.speak, actor, line, 6000); shown = ok and r == true
    end
    if not shown then
        local SC = g("SurvivorCompanion")
        local U = type(SC) == "table" and SC.GameplayUtil or nil
        if type(U) == "table" and type(U.say) == "function" then pcall(U.say, actor, line) end
    end
    return true
end

-- ---------------------------------------------------------------- the steps (each queues on HER queue)
local function addAction(action)
    local Q = g("ISTimedActionQueue")
    if type(Q) ~= "table" or type(Q.add) ~= "function" or action == nil then return false end
    local ok = pcall(Q.add, action)
    return ok
end
local function transferIfNeeded(actor, item)
    local CM = g("ISInventoryPaneContextMenu")
    if type(CM) == "table" and type(CM.transferIfNeeded) == "function" then pcall(CM.transferIfNeeded, actor, item) end
end

-- fill one magazine with loose rounds (Gunworks first, else vanilla)
function M.queueFill(actor, mag, kind)
    local MG = gw("WeaponSystems/Utils/Magazine")
    if MG and type(MG.reloadMagazine) == "function" then
        local ok, n = pcall(MG.reloadMagazine, actor, mag)
        return ok and (num(n) or 0) > 0
    end
    local CM, L = g("ISInventoryPaneContextMenu"), g("ISLoadBulletsInMagazine")
    if type(CM) ~= "table" or type(CM.transferBullets) ~= "function" or type(L) ~= "table" or type(L.new) ~= "function" then return false end
    local cur = num((call(mag, "getCurrentAmmoCount"))) or 0
    local max = num((call(mag, "getMaxAmmo"))) or 0
    local ok, add = pcall(CM.transferBullets, actor, kind, cur, max)
    if not ok or (num(add) or 0) <= 0 then return false end
    transferIfNeeded(actor, mag)
    return addAction(L:new(actor, mag, cur + add))
end
function M.queueInsert(actor, gun, mag)
    local I = g("ISInsertMagazine")
    if type(I) ~= "table" or type(I.new) ~= "function" then return false end
    transferIfNeeded(actor, mag)
    return addAction(I:new(actor, gun, mag))
end
function M.queueEject(actor, gun)
    local E = g("ISEjectMagazine")
    if type(E) ~= "table" or type(E.new) ~= "function" then return false end
    return addAction(E:new(actor, gun))
end
function M.queueRack(actor, gun)
    local R, W = g("ISRackFirearm"), g("ISReloadWeaponAction")
    if type(R) ~= "table" or type(R.new) ~= "function" then return false end
    if type(W) == "table" and type(W.canRack) == "function" then
        local ok, can = pcall(W.canRack, gun)
        if ok and can ~= true then return false end
    end
    return addAction(R:new(actor, gun))
end

-- the next step for this gun, or nil + why
function M.plan(actor, gun)
    local held = call(actor, "getPrimaryHandItem") == gun
    local clip = call(gun, "isContainsClip") == true
    local cur = num((call(gun, "getCurrentAmmoCount"))) or 0
    local chambered = call(gun, "isRoundChambered") == true
    -- a full magazine goes in as it is; else the fullest one she can fill is filled first; else a partial one goes in
    if held and not clip then
        local full = fullMag(actor, gun)
        if full ~= nil then return "insert", full.item end
        local f, kind = M.fillable(actor, gun)
        if f ~= nil then return "fill_insert", f.item, kind end
        local m = loadedMag(actor, gun)
        if m ~= nil then return "insert", m.item end
        return nil, "no_magazine_or_rounds"
    end
    if held and clip and cur <= 0 and not chambered then
        local full = fullMag(actor, gun)
        if full ~= nil then return "swap", full.item end
        local f, kind = M.fillable(actor, gun)
        if f ~= nil then return "fill_swap", f.item, kind end
        local m = loadedMag(actor, gun)
        if m ~= nil then return "swap", m.item end
        -- the only magazine is the empty one in the gun: take it out; the next poll fills it and puts it back
        if M.roundKind(actor, gun) ~= nil then return "eject" end
        return nil, "no_rounds"
    end
    if held and clip and cur > 0 and not chambered and call(gun, "haveChamber") ~= false then return "rack" end
    local f, kind = M.fillable(actor, gun)
    if f ~= nil then return "fill", f.item, kind end
    return nil, "nothing_to_fill"
end

function M.step(actor, gun, why)
    if not M.on() or actor == nil or gun == nil then return false, "off" end
    if #M.magTypes(gun) == 0 then return false, "not_a_magazine_gun" end
    if not M.safe(actor) then return false, "zombie_within_" .. tostring(M.SAFE_TILES) end
    if M.busy(actor) then return false, "busy_ours" end
    if not M.idle(actor) then return false, "busy" end
    local kind, mag, rounds = M.plan(actor, gun)
    if kind == nil then return false, mag end
    local q = queueOf(actor)
    local before = snapshot(q)
    local ok = false
    if kind == "insert" then ok = M.queueInsert(actor, gun, mag)
    elseif kind == "fill_insert" then ok = M.queueFill(actor, mag, rounds) and M.queueInsert(actor, gun, mag)
    elseif kind == "swap" then ok = M.queueEject(actor, gun) and M.queueInsert(actor, gun, mag)
    elseif kind == "fill_swap" then ok = M.queueFill(actor, mag, rounds) and M.queueEject(actor, gun) and M.queueInsert(actor, gun, mag)
    elseif kind == "eject" then ok = M.queueEject(actor, gun)
    elseif kind == "rack" then ok = M.queueRack(actor, gun)
    elseif kind == "fill" then ok = M.queueFill(actor, mag, rounds) end
    q = queueOf(actor)
    local added = newActions(q, before)
    if q and q.current ~= nil and not before[q.current] then added[#added + 1] = q.current end
    M.mine[actor] = { actions = added, gun = gun, kind = kind, at = nowMs() }
    if kind == "fill" or kind == "fill_insert" or kind == "fill_swap" then speak(actor, gun) end
    logOnce(actor, kind .. "|" .. tostring(gun) .. "|" .. tostring(mag), fullType(gun) .. ": " .. kind
        .. (mag and (" " .. fullType(mag) .. " " .. tostring(num((call(mag, "getCurrentAmmoCount"))) or 0) .. "/" .. tostring(num((call(mag, "getMaxAmmo"))) or 0)) or "")
        .. (rounds and (" with " .. tostring(rounds)) or "") .. " (" .. tostring(why) .. ")" .. (ok and "" or " - not queued"))
    return ok, kind
end

-- ---------------------------------------------------------------- requests and the poll
-- an "empty" refusal or his order: fill this gun's magazines as soon as she is safe and idle
function M.request(actor, gun, why)
    if not M.on() or actor == nil or gun == nil or #M.magTypes(gun) == 0 then return false end
    M.pending[actor] = { item = gun, at = nowMs(), why = why }
    logOnce(actor, "req|" .. tostring(gun), "asked to load " .. fullType(gun) .. " (" .. tostring(why) .. ")")
    return true
end

-- his order on a magazine gun with no loaded magazine: allowed when she can fill one (the fill waits until she is safe)
function M.orderFill(actor, gun)
    if not M.on() or gun == nil or not M.isRanged(gun) or #M.magTypes(gun) == 0 then return false end
    if loadedMag(actor, gun) == nil and M.fillable(actor, gun) == nil then return false end
    return M.request(actor, gun, "carry_order")
end

local function preferredGun(actor)
    local SC = g("SurvivorCompanion")
    local U = type(SC) == "table" and SC.GameplayUtil or nil
    if type(U) ~= "table" or type(U.idOf) ~= "function" then return nil end
    local ok, id = pcall(U.idOf, actor)
    if not ok or id == nil then return nil end
    for _, it in ipairs(list(call(call(actor, "getInventory"), "getAllCategoryRecurse", "Weapon", ArrayList.new()), 64)) do
        if call(it, "hasModData") == true and M.isRanged(it) then
            local md = call(it, "getModData")
            if type(md) == "table" and md.SC_ManualEquipFor == id then return it end
        end
    end
    return nil
end

function M.targets(actor)
    local out = {}
    local held = call(actor, "getPrimaryHandItem")
    if held ~= nil and M.isRanged(held) then out[#out + 1] = held end
    local p = M.pending[actor]
    if type(p) == "table" then
        if nowMs() - (p.at or 0) > M.REQUEST_MS then M.pending[actor] = nil
        elseif p.item ~= held then out[#out + 1] = p.item end
    end
    local pref = preferredGun(actor)
    if pref ~= nil and pref ~= held and not (type(p) == "table" and p.item == pref) then out[#out + 1] = pref end
    return out
end

function M.poll(actor)
    if not M.on() or actor == nil then return nil end
    if call(actor, "isDead") == true then return nil end
    if M.mine[actor] ~= nil and M.zombieNear(actor, M.SAFE_TILES) then
        if M.busy(actor) then M.abort(actor, "zombie within " .. tostring(M.SAFE_TILES) .. " tiles") end
        M.mine[actor] = nil
        return "aborted"
    end
    for _, gun in ipairs(M.targets(actor)) do
        local ok, kind = M.step(actor, gun, gun == call(actor, "getPrimaryHandItem") and "in_hands" or "asked")
        if ok then return kind end
        if kind == "busy" or kind == "busy_ours" or string.find(tostring(kind), "zombie_within", 1, true) then return kind end
    end
    return nil
end

function M.install()
    if M.installed then return end
    M.installed = true
    local E = g("Events")
    if E and E.OnTick and type(E.OnTick.Add) == "function" then
        local nextAt = 0
        E.OnTick.Add(function()
            local t = nowMs()
            if t < nextAt then return end
            nextAt = t + M.POLL_MS
            if not M.on() then return end
            local UI = g("SolUI")
            local f = type(UI) == "table" and UI.solActor or nil
            if type(f) ~= "function" then return end
            local ok, a = pcall(f)
            if ok and a ~= nil then pcall(M.poll, a) end
        end)
    end
    log("ready v" .. M.VERSION .. " (switch mag_fill=" .. tostring(M.on()) .. ")")
end
do local E = g("Events"); if E and E.OnGameStart and type(E.OnGameStart.Add) == "function" then E.OnGameStart.Add(function() pcall(M.install) end) end end
return M

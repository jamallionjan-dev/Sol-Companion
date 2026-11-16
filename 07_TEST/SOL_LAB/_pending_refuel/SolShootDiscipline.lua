-- SolShootDiscipline.lua - switch shooting_discipline (2026-11-11, s104). Aimed single shots for Sol's firearms.
-- Live 13:09:41-13:09:48: Sol with the EFZ Colt M4A1 (Aiming 10) emptied a 30-round magazine, 8 hits logged by FPZombiesHD
-- (one Head, the rest torso), no kill. Causes (council note DOCS/COUNCIL_s104_shooting.md):
--   * the M4A1's FireMode is Auto (TW_Items.txt, FireModePossibilities Auto/Single). CombatManager.calculateAttackVars sets
--     no recoil delay for a ranged weapon in "Auto", so LF's recovery gate (SCNativeActions.combatReadiness, recoil > 0) never
--     holds her; hits came 72-114 ms apart (13:09:43.060/.155/.269), faster than LF's own aim (>= 220 ms).
--   * LF's aim wait is wall time (SCCombat.prepareRangedShot, 220-1800 ms), not the engine's aim: hit chance subtracts
--     CombatManager.getAimDelayPenalty(character.getAimingDelay(), ...); aimingDelay starts at the weapon's AimingTime (40)
--     and only falls while aiming (IsoGameCharacter.updateAimingDelay), and every shot adds to it again.
--   * LF offers "shoot" at any visible distance and scores far shots higher (54 + min(MaxRange 60, d) * 2); the engine
--     subtracts (d - MaxSightRange) * (4 + 0.3 * (d - MaxSightRange)) past MaxSightRange (10 for the M4A1).
--   * stopping right before the shot leaves getBeenMovingFor() high (CombatManager.getMovePenalty).
-- What this file does (switch read at call time; off = LF exactly as before):
--   gate   before each shot LF has settled: stand still (isMoving false, getBeenMovingFor() <= MOVE_SETTLE), aim until the
--          engine's getAimingDelay() <= SETTLE_FRAC x AimingTime (at least MIN_SETTLE_MS, at most MAX_SETTLE_MS, then she
--          fires anyway and logs it); the weapon is put on Single/Semi when it offers it; a cap on misses at one
--          zombie until it comes CLOSING tiles nearer (s104b); a zombie at point blank / attacking is shot without the wait.
--          Short bursts: GROUP_COUNT zombies within GROUP_RADIUS allow BURST_MAX quicker shots (half-settled aim).
--   shape  decision: a "shoot" beyond the effective range (MaxSightRange + RANGE_EXTRA) becomes hold_range (she stands,
--          aims, waits); with no loaded spare magazine left she keeps the last one for zombies within RESERVE_RANGE, at
--          Jamal or attacking; a magazine at or under LOW_FRAC with a loaded spare and nothing within RELOAD_CLEAR gets a
--          tactical reload (vanilla BeginAutomaticReload ejects and inserts the best magazine).
--   rank   with a firearm in her hands, zombies nearest Jamal score higher; zombies past the effective range lower.
-- Downed zombies: LF never offers "shoot" at a grounded target (SCCombat.lua:2644, 2664); melee/stomp finish them.
-- s104b (0.2.0), live 14:55-14:57: aimed shots hit (FPZombiesHD ~15 ms after the shot) but zombies took 5+ hits, and the
-- 5-shot cap held fire at a zombie she was hitting; "RealAuto -> Single" every shot. Changes:
--   * the cap counts MISSES: a shot is a hit when Events.OnHitZombie (IsoZombie.Hit raises it before the damage; read-only
--     listener) names her as attacker for that zombie within HIT_WINDOW_MS. MISS_CAP misses in a row, or MAX_ROUNDS rounds,
--     hold her until the zombie comes CLOSING tiles nearer. Hits keep her firing.
--   * fire mode: EFZ TW_FireModeSwitch (OnWeaponSwing) turns a standard mode ("Single") back into the last Gunworks mode it
--     saw ("RealAuto") after every shot; Gunworks' own name for single shot is "RealSingle" (not standard, so left alone).
--     She gets RealSingle for a Gunworks-registered gun, else Single; set just before the shot, logged once per weapon.
--   * a zombie that is down (on the floor, prone, crawling) is never shot: LF's finisher (stomp/melee) takes it.
--   * kill ledger (read-only, for the damage question): per zombie the hits by Sol and by Jamal (local player) and its
--     health at each hit event; one "[SolShootDiscipline] kill:" line on Events.OnZombieDead.
-- ASCII only. Java calls by name through call() (checked by jarcall_check.py); no overloaded method gets a wrong type.
SolShootDiscipline = SolShootDiscipline or {}
local M = SolShootDiscipline
M.VERSION = "0.2.0"
M.FIX = "shooting_discipline"

M.RANGE_EXTRA = 2.0
M.RANGE_MIN, M.RANGE_MAX = 4.0, 30.0
-- The emergency point-blank bypass is reserved for contact range. At 3 tiles
-- it skipped aim settling and let Sol spend rounds while she should be spacing.
M.CLOSE = 1.35
M.SETTLE_FRAC = 0.15
M.SETTLE_FLOOR = 1.0
M.BURST_SETTLE_FRAC = 0.5
M.MIN_SETTLE_MS = 300
M.BURST_MIN_SETTLE_MS = 120
M.MAX_SETTLE_MS = 2500
M.EMERGENCY_MAX_SETTLE_MS = 600
M.MOVE_SETTLE = 6.0
M.MISS_CAP = 3
M.MAX_ROUNDS = 12
M.EXTRA_ROUNDS = 3
M.HIT_WINDOW_MS = 400
M.CLOSING = 2.0
M.LEDGER_HP = 16
M.TARGET_FORGET_MS = 10000
M.GROUP_RADIUS, M.GROUP_COUNT = 5.0, 3
M.BURST_MAX = 3
M.BURST_WINDOW_MS = 1500
M.LOW_FRAC = 0.25
M.RELOAD_CLEAR = 6.0
M.RESERVE_RANGE = 5.0
M.GUARD_RADIUS = 3.0
M.PLAYER_BONUS = 3.0
M.PLAYER_BONUS_TILES = 10.0
M.RANGE_PENALTY = 2.0
M.SPARE_CACHE_MS = 1000
M.LOG_MS = 5000
M.SINGLE_MODES = { "Single", "RealSingle", "Semi" }

M.actors = M.actors or setmetatable({}, { __mode = "k" })
M.ledger = M.ledger or setmetatable({}, { __mode = "k" })
M.modeLogged = M.modeLogged or setmetatable({}, { __mode = "k" })
M.targets = M.targets or setmetatable({}, { __mode = "k" })
M.spareCache = M.spareCache or setmetatable({}, { __mode = "k" })
M.modeSet = M.modeSet or setmetatable({}, { __mode = "k" })
M.lastLog = M.lastLog or {}

local rawTonumber = tonumber
local function num(v) return rawTonumber(v) end
local function g(name) return rawget(_G, name) end
local function nowMs() local f = g("getTimestampMs"); return f and f() or 0 end
local function log(m) print("[SolShootDiscipline] " .. tostring(m)) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
local function U()
    local SC = g("SurvivorCompanion")
    return type(SC) == "table" and SC.GameplayUtil or nil
end
function M.on()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on(M.FIX) == true
end
local function logEvery(key, m)
    local t = nowMs()
    if M.lastLog[key] ~= nil and t - M.lastLog[key] < M.LOG_MS then return end
    M.lastLog[key] = t
    log(m)
end
local function f1(v) v = num(v); if v == nil then return "?" end; return string.format("%.1f", v) end

local function pos(o)
    if o == nil then return nil end
    local x, y = num((call(o, "getX"))), num((call(o, "getY")))
    if x == nil or y == nil then return nil end
    return x, y
end
local function dist(a, b)
    local ax, ay = pos(a)
    local bx, by = pos(b)
    if ax == nil or bx == nil then return nil end
    local dx, dy = ax - bx, ay - by
    return math.sqrt(dx * dx + dy * dy)
end
local function targetDistance(actor, target)
    if type(target) ~= "table" then return nil end
    local d = num(target.distance)
    if d == nil and num(target.distanceSq) ~= nil then d = math.sqrt(num(target.distanceSq)) end
    if d == nil then d = dist(actor, target.actor) end
    return d
end
local function down(z)
    if z == nil then return true end
    return call(z, "isDead") == true or call(z, "isOnFloor") == true or call(z, "isProne") == true
        or call(z, "isCrawling") == true
end

-- ---------------------------------------------------------------- weapon facts
-- the engine's optimal-range edge: past HandWeapon.getMaxSightRange() every tile costs 4 + 0.3 per tile more to-hit
-- (CombatManager.getDistanceModifier, OPTIMAL_RANGE_DROP_OFF_TO_HIT_PENALTY / _INCREMENT). The no-argument overload only.
function M.effectiveRange(item, fallbackRange)
    local sight = num((call(item, "getMaxSightRange")))
    local r
    if sight ~= nil and sight > 0 then r = sight + M.RANGE_EXTRA
    else r = math.min(num(fallbackRange) or 12, 12) end
    if r < M.RANGE_MIN then r = M.RANGE_MIN end
    if r > M.RANGE_MAX then r = M.RANGE_MAX end
    return r
end

-- loaded spare magazines she carries (the magazine in the gun is not an inventory item). nil = not a magazine gun / unknown.
function M.spareMagazines(actor, item, inventory)
    if item == nil then return nil end
    local t = nowMs()
    local c = M.spareCache[item]
    if type(c) == "table" and t < c.expires then return c.value end
    inventory = inventory or call(actor, "getInventory")
    local value
    local MF = g("SolMagFill")
    if type(MF) == "table" and type(MF.on) == "function" and MF.on() and type(MF.magazines) == "function"
        and type(MF.magTypes) == "function" then
        local okT, types = pcall(MF.magTypes, item)
        if okT and type(types) == "table" and #types > 0 then
            local ok, mags = pcall(MF.magazines, inventory, item)
            if ok and type(mags) == "table" then
                value = 0
                for _, m in ipairs(mags) do if (num(m.count) or 0) > 0 then value = value + 1 end end
            end
        end
    end
    if value == nil then
        local mt = call(item, "getMagazineType")
        if mt ~= nil and tostring(mt) ~= "" and inventory ~= nil then
            local list = call(inventory, "getAllTypeRecurse", tostring(mt))
            local n = num((call(list, "size"))) or 0
            value = 0
            for i = 0, math.min(n, 32) - 1 do
                local mag = call(list, "get", i)
                if (num((call(mag, "getCurrentAmmoCount"))) or 0) > 0 then value = value + 1 end
            end
        end
    end
    M.spareCache[item] = { value = value, expires = t + M.SPARE_CACHE_MS }
    return value
end

-- Single (or Semi) when the weapon offers it; Gunworks re-applies its stat layers so EFZ's RecoilDelay comes back.
function M.ensureSingle(actor, item)
    if item == nil or call(item, "isRanged") ~= true then return false end
    local mode = tostring(call(item, "getFireMode") or "")
    for _, s in ipairs(M.SINGLE_MODES) do if mode == s then return false end end
    local list = call(item, "getFireModePossibilities")
    local n = num((call(list, "size"))) or 0
    local offered = {}
    for i = 0, n - 1 do
        local v = call(list, "get", i)
        if v ~= nil then offered[tostring(v)] = true end
    end
    local pick
    for _, s in ipairs(M.SINGLE_MODES) do if offered[s] then pick = s; break end end
    if pick == nil then
        if M.modeSet[item] ~= "none" then
            M.modeSet[item] = "none"
            log("no single-shot mode on " .. tostring(call(item, "getFullType")) .. " (mode " .. mode .. "); cadence held by the aim gate")
        end
        return false
    end
    local okR, Rate = pcall(function() local r = g("require"); return r and r("WeaponSystems/Utils/RateOfFire") end)
    if not okR or type(Rate) ~= "table" then Rate = nil end
    -- Gunworks names its single shot "RealSingle"; a standard "Single" on a Gunworks gun is turned back by EFZ's
    -- OnWeaponSwing check (TW_FireModeSwitch.lua:47-55) to the last non-standard mode it saw.
    if pick == "Single" then
        local registered = false
        if Rate ~= nil and type(Rate.IsWeaponRegistered) == "function" then
            local ok, r = pcall(Rate.IsWeaponRegistered, item); registered = ok and r == true
        end
        if registered or string.sub(mode, 1, 4) == "Real" then pick = "RealSingle" end
    end
    call(item, "setFireMode", pick)
    if Rate ~= nil and type(Rate.RecoilDelayAdjuster) == "function" then
        pcall(Rate.RecoilDelayAdjuster, actor, item)
    end
    if tostring(call(item, "getFireMode") or "") == pick then
        M.modeSet[item] = pick
        local n2 = (M.modeLogged[item] or 0) + 1
        M.modeLogged[item] = n2
        if n2 == 1 then
            log("fire mode " .. mode .. " -> " .. pick .. " on " .. tostring(call(item, "getFullType")) .. " (logged once per weapon)")
        end
        return true
    end
    return false
end

-- ---------------------------------------------------------------- per-actor / per-target memory
local function actorState(actor)
    local st = M.actors[actor]
    if st == nil then st = { burst = 0 }; M.actors[actor] = st end
    return st
end
local function targetRecord(target, t)
    local r = M.targets[target]
    if r == nil or t - (r.at or 0) > M.TARGET_FORGET_MS then
        r = { n = 0, hits = 0, misses = 0, maxShots = M.MAX_ROUNDS, at = t }
        M.targets[target] = r
    end
    return r
end
-- a shot still waiting for its OnHitZombie becomes a miss once HIT_WINDOW_MS has passed
local function resolve(rec, t)
    if rec.pendingAt ~= nil and t - rec.pendingAt >= M.HIT_WINDOW_MS then
        rec.misses = rec.misses + 1
        rec.pendingAt = nil
    end
end
M._resolve = resolve

local function groupCount(actor, snapshot)
    local n = 0
    if type(snapshot) ~= "table" or type(snapshot.threats) ~= "table" then return 0 end
    for _, th in ipairs(snapshot.threats) do
        local z = type(th) == "table" and th.actor or nil
        if z ~= nil and not down(z) then
            local d = num(th.distance)
            if d == nil and num(th.distanceSq) ~= nil then d = math.sqrt(num(th.distanceSq)) end
            if d == nil then d = dist(actor, z) end
            if d ~= nil and d <= M.GROUP_RADIUS then n = n + 1 end
        end
    end
    return n
end
M._groupCount = groupCount

local function nearestThreat(actor, snapshot)
    local best = math.huge
    if type(snapshot) ~= "table" or type(snapshot.threats) ~= "table" then return best end
    for _, th in ipairs(snapshot.threats) do
        local z = type(th) == "table" and th.actor or nil
        if z ~= nil and call(z, "isDead") ~= true then
            local d = num(th.distance)
            if d == nil and num(th.distanceSq) ~= nil then d = math.sqrt(num(th.distanceSq)) end
            if d == nil then d = dist(actor, z) end
            if d ~= nil and d < best then best = d end
        end
    end
    return best
end
M._nearestThreat = nearestThreat

local function urgent(actor, player, target, d)
    if type(target) ~= "table" then return false end
    if target.attacking == true or (d ~= nil and d <= M.CLOSE) then return true end
    local dp = player ~= nil and dist(player, target.actor) or nil
    return dp ~= nil and dp <= M.GUARD_RADIUS
end
M._urgent = urgent

-- keep her aiming at the target while the gate holds: the same ready_weapon LF's own aim and hold_range use
local function holdAim(actor, target, st)
    local u = U()
    local aiming = call(actor, "isAiming") == true
    local moving = call(actor, "isMoving") == true
    if (not aiming or moving or st.holdIssued ~= target.actor) and u and type(u.move) == "function" then
        local ok = pcall(u.move, actor, "walk", {
            action = "ready_weapon", facingTarget = target.actor, target = target.actor,
            deliberateAim = true, keepFacing = true, weaponReady = true,
        })
        st.holdIssued = ok and target.actor or nil
    end
end

-- ---------------------------------------------------------------- gate (SCCombat.update, after LF's own aim settled)
-- returns true, "aiming" = hold this pulse (LF keeps the aim); false, reason = fire now.
function M.gate(actor, player, state, snapshot, target, weapon, aimReason, t)
    if not M.on() or type(weapon) ~= "table" or weapon.ranged ~= true or type(target) ~= "table" then
        return false, aimReason
    end
    t = num(t) or nowMs()
    local st = actorState(actor)
    local item = weapon.item
    local d = targetDistance(actor, target)
    if target.actor == nil or call(target.actor, "isDead") == true then return false, aimReason end
    -- a zombie that is down is LF's finisher's (stomp / melee), never a round
    if target.grounded == true or target.fallen == true or down(target.actor) then
        holdAim(actor, target, st)
        logEvery("down", "hold: the zombie is down (d=" .. f1(d) .. "), left to a stomp or a blow")
        st.reason = "target_down"
        return true, "aiming"
    end
    local isUrgent = urgent(actor, player, target, d)
    if d ~= nil and d <= M.CLOSE and target.attacking == true then
        M.ensureSingle(actor, item)
        st.reason = "point_blank"
        return false, aimReason
    end
    if aimReason == "aim_not_safe" then
        holdAim(actor, target, st)
        st.reason = "unsafe_range"
        logEvery("unsafe_range", "hold: too close to aim safely (d=" .. f1(d) .. "); create space before firing")
        return true, "unsafe_range"
    end
    -- per-target cap on MISSES: hits keep her firing; MISS_CAP misses in a row or MAX_ROUNDS rounds without the kill
    -- hold her until the zombie comes CLOSING tiles nearer (then one more miss, or EXTRA_ROUNDS rounds, re-cap)
    local rec = targetRecord(target.actor, t)
    resolve(rec, t)
    if not isUrgent and rec.pendingAt == nil and (rec.misses >= M.MISS_CAP or rec.n >= rec.maxShots) then
        rec.capD = rec.capD or d
        if d ~= nil and d <= rec.capD - M.CLOSING then
            rec.misses = math.min(rec.misses, M.MISS_CAP - 1)
            rec.maxShots = rec.n + M.EXTRA_ROUNDS
            rec.capD = nil
        else
            holdAim(actor, target, st)
            logEvery("cap", "hold: " .. tostring(rec.n) .. " rounds, " .. tostring(rec.hits) .. " hits, "
                .. tostring(rec.misses) .. " misses in a row at this zombie; waits until it is "
                .. f1(M.CLOSING) .. " tiles nearer (d=" .. f1(d) .. ")")
            st.reason = "per_target_cap"
            return true, "aiming"
        end
    end
    if rec.pendingAt ~= nil and not isUrgent then
        -- the last round's hit is not in yet: no new round until it is read (at most HIT_WINDOW_MS)
        holdAim(actor, target, st)
        st.reason = "await_hit"
        return true, "aiming"
    end
    local eff = M.effectiveRange(item, weapon.range)
    if d ~= nil and d > eff and not isUrgent then
        holdAim(actor, target, st)
        logEvery("range", "hold: out of effective range d=" .. f1(d) .. " > " .. f1(eff))
        st.reason = "out_of_range"
        return true, "aiming"
    end
    st.since = st.since or t
    local waited = t - st.since
    local emergency = aimReason == "aim_not_required" or isUrgent
    local maxWait = emergency and M.EMERGENCY_MAX_SETTLE_MS or M.MAX_SETTLE_MS
    local group = groupCount(actor, snapshot)
    if st.burst > 0 and t - (st.lastShotAt or 0) > M.BURST_WINDOW_MS then st.burst = 0 end
    local burst = group >= M.GROUP_COUNT and st.burst < M.BURST_MAX
    local aimTime = num((call(item, "getAimingTime"))) or 0
    local frac = burst and M.BURST_SETTLE_FRAC or M.SETTLE_FRAC
    local need = math.max(M.SETTLE_FLOOR, aimTime * frac)
    local delay = num((call(actor, "getAimingDelay")))
    local moved = num((call(actor, "getBeenMovingFor")))
    local moving = call(actor, "isMoving") == true
    local minWait = burst and M.BURST_MIN_SETTLE_MS or M.MIN_SETTLE_MS
    if emergency then minWait = 0 end
    local why
    if moving or (moved ~= nil and moved > M.MOVE_SETTLE) then why = "settle_move"
    elseif delay ~= nil and delay > need then why = "settle_aim"
    elseif waited < minWait then why = "settle_min" end
    if why ~= nil and waited < maxWait then
        holdAim(actor, target, st)
        st.reason = why
        return true, "aiming"
    end
    if why ~= nil then
        logEvery("timeout", "fires after " .. tostring(waited) .. " ms without a settled aim (" .. why
            .. " aimingDelay=" .. f1(delay) .. "/" .. f1(need) .. " beenMovingFor=" .. f1(moved) .. ")")
    end
    M.ensureSingle(actor, item)
    st.reason = burst and "burst" or "aimed"
    st.fireDelay, st.fireMoved, st.fireWaited, st.fireD = delay, moved, waited, d
    return false, aimReason
end

-- SCCombat.update after execute() accepted the shot
function M.fired(actor, target, weapon, t)
    if not M.on() or type(target) ~= "table" or target.actor == nil then return end
    t = num(t) or nowMs()
    local st = actorState(actor)
    local rec = targetRecord(target.actor, t)
    resolve(rec, t)
    rec.n = rec.n + 1
    rec.at = t
    -- a hit already read in this same frame (the round resolved inside DoAttack) is not pending
    if rec.lastHitAt ~= nil and t - rec.lastHitAt < 50 then rec.pendingAt = nil else rec.pendingAt = t end
    local d = targetDistance(actor, target)
    if st.reason == "burst" then st.burst = st.burst + 1 else st.burst = 0 end
    st.lastShotAt = t
    local lg = M.ledger[target.actor]
    if lg ~= nil then lg.solRounds = (lg.solRounds or 0) + 1 else M.ledger[target.actor] = { sol = 0, jamal = 0, solRounds = 1, hp = {} } end
    log("shot " .. tostring(st.reason) .. " n=" .. tostring(rec.n) .. " hits=" .. tostring(rec.hits) .. " d=" .. f1(d)
        .. " aimingDelay=" .. f1(st.fireDelay) .. " beenMovingFor=" .. f1(st.fireMoved)
        .. " waited=" .. tostring(st.fireWaited or 0) .. "ms ammo=" .. tostring(type(weapon) == "table" and weapon.ammo or "?")
        .. " mode=" .. tostring(type(weapon) == "table" and call(weapon.item, "getFireMode") or "?"))
    st.since = nil
    st.holdIssued = nil
    st.fireDelay, st.fireMoved, st.fireWaited, st.fireD = nil, nil, nil, nil
end

-- ---------------------------------------------------------------- shape (SCCombat actionUtilities, before the sort)
function M.shape(actor, player, snapshot, target, weapon, inventory, actions, distance, reloadReady)
    if not M.on() or type(weapon) ~= "table" or weapon.ranged ~= true or type(actions) ~= "table"
        or type(target) ~= "table" then return end
    local d = num(distance) or targetDistance(actor, target)
    local eff = M.effectiveRange(weapon.item, weapon.range)
    local isUrgent = urgent(actor, player, target, d)
    local spares
    local isDown = target.grounded == true or target.fallen == true or down(target.actor)
    for i, a in ipairs(actions) do
        if a.kind == "shoot" and isDown then
            actions[i] = { kind = "hold_range", score = math.min(num(a.score) or 0, 40), sdHold = "target_down" }
            logEvery("shape-down", "shoot -> hold_range (target_down) d=" .. f1(d) .. ": a stomp or a blow, not a round")
        elseif a.kind == "shoot" and not isUrgent then
            local why
            if d ~= nil and d > eff then why = "out_of_range"
            else
                if spares == nil then spares = M.spareMagazines(actor, weapon.item, inventory) or -1 end
                if spares == 0 and d ~= nil and d > M.RESERVE_RANGE then why = "reserve" end
            end
            if why ~= nil then
                actions[i] = { kind = "hold_range", score = a.score, sdHold = why }
                logEvery("shape-" .. why, "shoot -> hold_range (" .. why .. ") d=" .. f1(d) .. " range=" .. f1(eff)
                    .. (why == "reserve" and " last magazine kept for zombies within " .. f1(M.RESERVE_RANGE) or ""))
            end
        end
    end
    local ammo, maxAmmo = num(weapon.ammo) or 0, num(weapon.maxAmmo) or 0
    if ammo > 0 and maxAmmo > 1 and ammo <= math.max(1, math.floor(maxAmmo * M.LOW_FRAC))
        and weapon.jammed ~= true and nearestThreat(actor, snapshot) >= M.RELOAD_CLEAR then
        if spares == nil then spares = M.spareMagazines(actor, weapon.item, inventory) or -1 end
        local ready = spares > 0
        if spares < 0 and type(reloadReady) == "function" then
            local ok, r = pcall(reloadReady); ready = ok and r == true
        end
        if ready then
            for _, a in ipairs(actions) do if a.kind == "reload" then return end end
            actions[#actions + 1] = { kind = "reload", score = 120, sdTactical = true }
            logEvery("tactical", "tactical reload: " .. tostring(ammo) .. "/" .. tostring(maxAmmo) .. ", spare magazines " .. tostring(spares))
        end
    end
end

-- ---------------------------------------------------------------- rank (SCCombat.update, after scoreTargets)
function M.rank(actor, player, scored)
    if not M.on() or type(scored) ~= "table" or #scored == 0 then return end
    local item = call(actor, "getPrimaryHandItem")
    if item == nil or call(item, "isRanged") ~= true then return end
    local eff = M.effectiveRange(item, nil)
    local changed = false
    for _, r in ipairs(scored) do
        if type(r) == "table" and r.actor ~= nil and r.grounded ~= true and r.fallen ~= true then
            local bonus = 0
            local dp = player ~= nil and dist(player, r.actor) or nil
            if dp ~= nil and dp < M.PLAYER_BONUS_TILES then bonus = bonus + (M.PLAYER_BONUS_TILES - dp) * M.PLAYER_BONUS end
            local d = num(r.distance)
            if d ~= nil and d > eff then bonus = bonus - (d - eff) * M.RANGE_PENALTY end
            if bonus ~= 0 then
                r.score = (num(r.score) or 0) + bonus
                r.sdBonus = bonus
                changed = true
            end
        end
    end
    if changed then
        table.sort(scored, function(a, b)
            if a.score == b.score then return (a.distanceSq or math.huge) < (b.distanceSq or math.huge) end
            return a.score > b.score
        end)
    end
end

-- cover fire while retreating (SCCombat.executeRetreatCounter): not past the effective range
function M.coverFireOk(actor, weapon, distance)
    if not M.on() or type(weapon) ~= "table" then return true end
    local d = num(distance)
    return d == nil or d <= M.effectiveRange(weapon.item, weapon.range)
end

-- ---------------------------------------------------------------- hits and kills (read-only listeners)
local function isSol(actor)
    if actor == nil then return false end
    if M.actors[actor] ~= nil then return true end
    local UI = g("SolUI")
    if type(UI) == "table" and type(UI.solActor) == "function" then
        local ok, a = pcall(UI.solActor); if ok and a == actor then return true end
    end
    return false
end
M._isSol = isSol

-- Events.OnHitZombie(zombie, attacker, bodyPart, weapon): raised by IsoZombie.Hit BEFORE the damage is applied, so
-- getHealth() here is the health before this hit. bodyPart is Torso_Upper/Torso_Lower at random, Head on a critical hit
-- (IsoZombie.Hit bytecode 21-70), not where the round struck.
function M.onHit(zombie, attacker, bodyPart, weapon)
    if not M.on() or zombie == nil or attacker == nil then return end
    if weapon == nil or call(weapon, "isRanged") ~= true then return end
    local who
    if isSol(attacker) then who = "sol" elseif call(attacker, "isLocalPlayer") == true then who = "jamal" else return end
    local t = nowMs()
    local lg = M.ledger[zombie]
    if lg == nil then lg = { sol = 0, jamal = 0, solRounds = 0, hp = {} }; M.ledger[zombie] = lg end
    lg[who] = lg[who] + 1
    lg.weapon = tostring(call(weapon, "getType") or "?")
    if #lg.hp < M.LEDGER_HP then
        lg.hp[#lg.hp + 1] = string.sub(who, 1, 1) .. f1(num((call(zombie, "getHealth")))) .. (tostring(bodyPart) == "Head" and "c" or "")
    end
    if who == "sol" then
        local rec = M.targets[zombie]
        if rec ~= nil then
            rec.hits = rec.hits + 1
            rec.misses = 0
            rec.pendingAt = nil
            rec.lastHitAt = t
        else
            M.targets[zombie] = { n = 0, hits = 1, misses = 0, maxShots = M.MAX_ROUNDS, at = t, lastHitAt = t }
        end
    end
end

-- Events.OnZombieDead(zombie): one line per zombie either of them shot
function M.onDead(zombie)
    local lg = zombie ~= nil and M.ledger[zombie] or nil
    if lg == nil then return end
    M.ledger[zombie] = nil
    if not M.on() then return end
    log("kill: " .. tostring(lg.weapon) .. " hits sol=" .. tostring(lg.sol) .. " jamal=" .. tostring(lg.jamal)
        .. " solRounds=" .. tostring(lg.solRounds or 0) .. " health-before-each-hit=" .. table.concat(lg.hp, ">")
        .. " (s/j = shooter, c = critical)")
end

if Events ~= nil and not M.hooked then
    M.hooked = true
    if Events.OnHitZombie and type(Events.OnHitZombie.Add) == "function" then
        Events.OnHitZombie.Add(function(z, a, p, w) pcall(M.onHit, z, a, p, w) end)
    end
    if Events.OnZombieDead and type(Events.OnZombieDead.Add) == "function" then
        Events.OnZombieDead.Add(function(z) pcall(M.onDead, z) end)
    end
end

log("loaded " .. M.VERSION)
return M

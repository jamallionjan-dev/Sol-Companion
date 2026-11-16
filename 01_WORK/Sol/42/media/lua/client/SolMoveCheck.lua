-- SolMoveCheck.lua - switch move_check (s87, ledger A10; council SOL_REVIEW section 45).
-- While Sol carries out a walk he gave her (Living Fellows' order move_to: every update its decision layer calls
-- SC.Navigation.request(actor, target, mode, { action = "ordered_move", ... })), this file sits on that call and adds:
--   1. "did not move": every 600 ms her position is compared with the last sample; less than 0.25 tiles of progress
--      (not while she climbs, gets up, is bumped, waits at a door or the path search runs) means stuck: the old navigation
--      state is dropped (SC.Navigation.cancel) and this same request starts a fresh path. 1.2 s pause between two kicks,
--      at most 8 kicks for one target, then LF's own recovery is left alone (logged once).
--      Idea from BanditsPerformanceOverride's ManageStuck (sample every 600 ms, 0.25 tiles, cooldown, re-path); no code copied.
--   2. run far, walk near: more than 8 tiles to go -> jog, 4 tiles or less -> walk, in between she keeps what she does
--      (no flapping). A sneak order stays a sneak.
--   3. a walk to him ends 1.5 tiles from him: when the target is within 2.5 tiles of the player and she is within 1.5 of
--      him (same floor), the request answers "arrived" (LF then makes her stay, as at any arrival) and her motion stops,
--      instead of pushing into his square.
-- Ideas 2 and 3 from Project Remnants as recorded in DOCS/SOL_TODO_20261109.md (community table); no code copied.
-- Every other caller and every other actor goes straight to LF's own request, unchanged.
SolMoveCheck = SolMoveCheck or {}
local M = SolMoveCheck
M.VERSION = "0.1.0"
M.SAMPLE_MS = 600
M.MIN_MOVE = 0.25
M.COOLDOWN_MS = 1200
M.MAX_KICKS = 8
M.RUN_FROM = 8
M.WALK_WITHIN = 4
M.STOP_NEAR_HIM = 1.5
M.HIS_GOAL = 2.5
M.BUSY = { bumped = true, onground = true, climbfence = true, climbwindow = true, climbrope = true, getup = true,
    turnalerted = true, staggerback = true, knockeddown = true, falldown = true, fall = true }
M.QUIET_PHASES = { planning = true, waiting = true }

local function g(name) return rawget(_G, name) end
local function nowMs() local f = g("getTimestampMs"); if f then return f() end; return os.time() * 1000 end
local function log(m) print("[SolMoveCheck] " .. tostring(m)) end
local function finite(v) return type(v) == "number" and v == v and v < 1e30 and v > -1e30 and v or nil end
local function vcall(o, name, ...)
    if o == nil then return nil end
    local ok0, f = pcall(function() return o[name] end)
    if not ok0 or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function num(o, name) return finite(tonumber((vcall(o, name)))) end
local function switchOn()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("move_check") == true
end
local function LF() local sc = g("SurvivorCompanion"); if type(sc) == "table" then return sc end; return nil end
local function isSol(actor)
    if actor == nil then return false end
    local U = g("SolUI")
    if type(U) == "table" and type(U.solActor) == "function" then
        local ok, s = pcall(U.solActor)
        if ok and s ~= nil then return s == actor end
    end
    local S = g("SolSpeechAR")
    if type(S) == "table" and type(S.isSol) == "function" then
        local ok, v = pcall(S.isSol, actor)
        return ok and v == true
    end
    return false
end
local function player()
    local f = g("getSpecificPlayer")
    if type(f) ~= "function" then return nil end
    local ok, p = pcall(f, 0)
    if ok then return p end
    return nil
end
-- a square, a table {x, y, z} or anything with getX/getY
local function xyz(t)
    if type(t) == "table" and finite(t.x) and finite(t.y) then return t.x, t.y, finite(t.z) or 0 end
    local x, y = num(t, "getX"), num(t, "getY")
    if x == nil or y == nil then return nil end
    return x, y, num(t, "getZ") or 0
end
local function dist(ax, ay, bx, by) return math.sqrt((ax - bx) ^ 2 + (ay - by) ^ 2) end

M.track = M.track or nil   -- { key, at, x, y, kicks, cdUntil, mode, gaveUp }
M.stats = M.stats or { kicks = 0, nearHim = 0, jog = 0, walk = 0 }

function M.chooseMode(requested, left)
    if requested == "sneak" then return "sneak" end
    local t = M.track
    local mode
    if left > M.RUN_FROM then mode = "jog"
    elseif left <= M.WALK_WITHIN then mode = "walk"
    else mode = (t and t.mode) or requested or "walk" end
    if t then
        if t.mode ~= mode then
            M.stats[mode] = (M.stats[mode] or 0) + 1
            log(string.format("%s, %.1f tiles to go", mode, left))
        end
        t.mode = mode
    end
    return mode
end

-- true when she has to be given a fresh path now
function M.stuck(actor, ax, ay, now)
    local t = M.track
    if t == nil then return false end
    local state = string.lower(tostring(vcall(actor, "getActionStateName") or ""))
    local SC = LF()
    local Nav = SC and SC.Navigation
    local phase = nil
    if type(Nav) == "table" and type(Nav.status) == "function" then
        local ok, st = pcall(Nav.status, actor)
        if ok and type(st) == "table" then phase = st.phase end
    end
    if M.BUSY[state] or M.QUIET_PHASES[tostring(phase)] or vcall(actor, "getVehicle") ~= nil then
        t.at = nil
        return false
    end
    if t.cdUntil and now < t.cdUntil then return false end
    if t.at == nil then t.at, t.x, t.y = now, ax, ay; return false end
    if now - t.at < M.SAMPLE_MS then return false end
    local moved = dist(ax, ay, t.x, t.y)
    t.at, t.x, t.y = now, ax, ay
    if moved >= M.MIN_MOVE then return false end
    if t.kicks >= M.MAX_KICKS then
        if not t.gaveUp then t.gaveUp = true; log("still stuck after " .. t.kicks .. " fresh paths: LF's own recovery from here") end
        return false
    end
    t.kicks = t.kicks + 1
    t.cdUntil = now + M.COOLDOWN_MS
    t.at = nil
    return true
end

function M.wrap()
    local SC = LF()
    local Nav = SC and SC.Navigation
    if type(Nav) ~= "table" or type(Nav.request) ~= "function" then return false end
    if Nav._solMoveCheck then M._wrapped = true; return true end
    local base = Nav.request
    Nav.request = function(actor, target, mode, intent, a5, a6)
        if type(intent) ~= "table" or intent.action ~= "ordered_move" or not switchOn() or not isSol(actor) then
            return base(actor, target, mode, intent, a5, a6)
        end
        local ax, ay, az = xyz(actor)
        local tx, ty, tz = xyz(target)
        if ax == nil or tx == nil then return base(actor, target, mode, intent, a5, a6) end
        local now = nowMs()
        local key = math.floor(tx) .. "," .. math.floor(ty) .. "," .. math.floor(tz)
        if M.track == nil or M.track.key ~= key then M.track = { key = key, kicks = 0, mode = M.track and M.track.mode or nil } end
        local p = player()
        local px, py, pz = xyz(p)
        local SU_ = g("SolUI")                                                     -- s95: her walk to the fuel cap is not a walk to him
        local errand_ = type(SU_) == "table" and type(SU_.solFuelWalking) == "function" and SU_.solFuelWalking() == true
        if not errand_ and px ~= nil and math.floor(pz) == math.floor(az) and math.floor(tz) == math.floor(az)
                and dist(tx, ty, px, py) <= M.HIS_GOAL and dist(ax, ay, px, py) <= M.STOP_NEAR_HIM then
            if not M.track.near then
                M.track.near = true
                M.stats.nearHim = M.stats.nearHim + 1
                log(string.format("%.1f tiles from him: there", dist(ax, ay, px, py)))
            end
            pcall(Nav.cancel, actor, "sol_move_check_near_him")
            return true, "arrived"
        end
        mode = M.chooseMode(mode, dist(ax, ay, tx, ty))
        if M.stuck(actor, ax, ay, now) then
            M.stats.kicks = M.stats.kicks + 1
            log(string.format("did not move in %d ms at %.1f,%.1f: fresh path to %s (%d)", M.SAMPLE_MS, ax, ay, key, M.track.kicks))
            pcall(Nav.cancel, actor, "sol_move_check")
        end
        return base(actor, target, mode, intent, a5, a6)
    end
    Nav._solMoveCheck = true
    M._wrapped = true
    log("ready v" .. M.VERSION)
    return true
end

-- wrapped at the first tick after the game started (LF's tables exist by then); retried each tick until LF is there
function M.install()
    if M._installed then return end
    M._installed = true
    if Events and Events.OnTick then
        local function step()
            if not M._wrapped then pcall(M.wrap) end
            if M._wrapped and Events.OnTick.Remove then Events.OnTick.Remove(step) end
        end
        Events.OnTick.Add(step)
    else
        M.wrap()
    end
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(M.install) end
return M

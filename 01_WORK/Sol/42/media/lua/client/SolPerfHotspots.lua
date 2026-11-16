-- SolPerfHotspots.lua - switch perf_hotspots (s108, 2026-11-11). Less Lua per frame for the same decisions.
-- Live (DebugLog 2026-11-11_14-48, s106 lua_profiler, OnTick ms/s): LF SCRuntime.lua fn@L1344 (productionTick: LF's whole AI tick,
-- its scheduler included) 35-49 ms/s while riding, 396-443 ms/s for 90 s while she followed him on foot past the porch fence
-- (14:52:32-14:53:50, 11-13 ms a frame); SolBudget.lua fn@L22 (B.step) 1.4-3 ms/s idle, 12-21 ms/s while the world scan or the
-- inventory report ran their 4 ms slices; SolActions.lua fn@L749 (its OnTick) 2.5-3.6 ms/s, 7 ms/s with the catalog.
-- Three parts, all behind the one switch (read at call time; off = everything as before):
--  1. The frame clock for switch reads. SolAuthority.on(name) read the Java clock (getTimestampMs) on every call, only to know
--     whether 5 s had passed since the switch file was read. Sol's hooks inside Living Fellows' decision, combat, path and car
--     code ask it many times a frame. Now one OnTick handler reads the clock once a frame (A._tickNow) and A.on uses that value.
--     Same answers; a switch-file reload can come at most one frame later. If no OnTick ran for STALL_CALLS reads (loading,
--     main menu), A.on reads the real clock again.
--  2. Her bag, once a second (SolActions U.trackGivenItems, "what did he give me"): it walked every item of hers (two Java calls an
--     item, hundreds of items) to find new ones. Now the walk notes the containers it read; the next second checks each one's
--     item count and contents weight (three Java calls a container) and walks again only when one changed, the root container is
--     another object, or she is another actor. Unchanged = no new item = nothing to mark, the same as the walk would find.
--  3. A breakdown line for Living Fellows' own tick (diagnostic): every WINDOW_MS the top LF systems by ms/s, from the same numbers
--     LF already records (SC.Performance.record: tick.total, tick.pre-scheduler, scheduler.<task>, decision, zombie-targeting,
--     zombie-attack, ...), plus switch reads a second and the bag walks done / skipped. Set M.LF_LOG = false to drop it.
-- Reaction-critical paths are not touched: LF's decision, combat, zombie and driving cadences stay exactly as they were.
SolPerfHotspots = SolPerfHotspots or {}
local M = SolPerfHotspots
M.VERSION = "0.1.0"
M.FIX = "perf_hotspots"
M.WINDOW_MS = M.WINDOW_MS or 15000
M.CHECK_MS = M.CHECK_MS or 1000
M.TOP = M.TOP or 10
M.STALL_CALLS = M.STALL_CALLS or 4000
if M.LF_LOG == nil then M.LF_LOG = true end
M.stats = M.stats or { reads = 0, bagWalks = 0, bagSkips = 0, frames = 0 }   -- this window
M.totals = M.totals or { bagWalks = 0, bagSkips = 0 }                        -- since load
M.lf = M.lf or {}

local G = _G
local function g(n) return rawget(G, n) end
local function log(m) print("[SolPerfHot] " .. tostring(m)) end
local function clock()
    local f = g("getTimestampMs")
    if type(f) == "function" then return tonumber((f())) or 0 end
    return 0
end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or type(f) ~= "function" then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end

function M.on()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on(M.FIX) == true
end

-- ---------------------------------------------------------------- 2. her bag
-- the walk's containers (root first) -> their item counts and contents weights
local function sig(c)
    local list = call(c, "getItems")
    local n = tonumber((call(list, "size")))
    local w = tonumber((call(c, "getContentsWeight")))
    return n, w
end
function M.bagMark(actor, containers)
    if actor == nil or type(containers) ~= "table" or containers[1] == nil then M.bag = nil; return end
    local b = { actor = actor, containers = {}, n = {}, w = {} }
    for i, c in ipairs(containers) do
        local n, w = sig(c)
        b.containers[i], b.n[i], b.w[i] = c, n, w
    end
    M.bag = b
    M.stats.bagWalks = M.stats.bagWalks + 1
    M.totals.bagWalks = M.totals.bagWalks + 1
end
function M.bagSame(actor)
    local b = M.bag
    if b == nil or actor == nil or b.actor ~= actor then return false end
    if call(actor, "getInventory") ~= b.containers[1] then return false end
    for i, c in ipairs(b.containers) do
        local n, w = sig(c)
        if n == nil or w == nil or n ~= b.n[i] or w ~= b.w[i] then return false end
    end
    M.stats.bagSkips = M.stats.bagSkips + 1
    M.totals.bagSkips = M.totals.bagSkips + 1
    return true
end

-- ---------------------------------------------------------------- 3. Living Fellows' own numbers
local function lfPerf()
    local SC = g("SurvivorCompanion")
    local P = type(SC) == "table" and SC.Performance or nil
    if type(P) == "table" and type(P.record) == "function" then return P end
    return nil
end
function M.wrapRecord()
    local P = lfPerf()
    if P == nil or P._solHot then return P ~= nil end
    local base = P.record
    M._baseRecord, M._wrapper = base, nil
    local function wrapper(system, companionId, elapsedMs, units, yielded)
        local acc = M.lf
        local e = acc[system]
        if e == nil then e = { ms = 0, n = 0 }; acc[system] = e end
        e.ms = e.ms + (tonumber(elapsedMs) or 0)
        e.n = e.n + 1
        return base(system, companionId, elapsedMs, units, yielded)
    end
    M._wrapper = wrapper
    P.record, P._solHot = wrapper, true
    return true
end
function M.unwrapRecord()
    local P = lfPerf()
    if P == nil or not P._solHot then return end
    if P.record == M._wrapper and M._baseRecord ~= nil then P.record = M._baseRecord end
    P._solHot = nil
    M._wrapper = nil
end

local function fmt(x) return string.format("%.2f", x) end
function M.report(t)
    local span = math.max(1, t - (M.windowAt or t))
    local rows = {}
    for k, e in pairs(M.lf) do rows[#rows + 1] = { k = tostring(k), ms = e.ms, n = e.n } end
    table.sort(rows, function(a, b) if a.ms ~= b.ms then return a.ms > b.ms end return a.k < b.k end)
    local parts = {}
    for i = 1, math.min(#rows, M.TOP) do
        local r = rows[i]
        parts[#parts + 1] = r.k .. " " .. fmt(r.ms * 1000 / span) .. " (" .. fmt(r.n * 1000 / span) .. "/s)"
    end
    local s = M.stats
    local line = "window " .. fmt(span / 1000) .. "s, " .. s.frames .. " frames | LF ms/s: " .. (#parts > 0 and table.concat(parts, " | ") or "none")
        .. " | switch reads " .. fmt(s.reads * 1000 / span) .. "/s on the frame clock | her bag: " .. s.bagWalks .. " walk(s), " .. s.bagSkips .. " skipped (unchanged)"
    M.lastLine = line
    if M.LF_LOG then log(line) end
    M.lf = {}                                                                  -- the wrapper sums into the fresh table
    s.reads, s.bagWalks, s.bagSkips, s.frames = 0, 0, 0, 0
    M.windowAt = t
    return line
end

-- ---------------------------------------------------------------- 1. the frame clock (and the once-a-second housekeeping)
M.nextCheck = M.nextCheck or 0
function M.frame()
    local t = clock()
    local A = g("SolAuthority")
    if type(A) == "table" then
        M.stats.reads = M.stats.reads + (tonumber(A._tickCalls) or 0)
        A._tickNow, A._tickCalls = t, 0
    end
    M.stats.frames = M.stats.frames + 1
    if t >= M.nextCheck then
        M.nextCheck = t + M.CHECK_MS
        local was = M.active
        M.active = M.on()
        if M.active and M.LF_LOG then M.wrapRecord() else M.unwrapRecord() end
        if M.active and not was then
            M.windowAt, M.lf = t, {}
            M.stats.reads, M.stats.bagWalks, M.stats.bagSkips, M.stats.frames = 0, 0, 0, 0
            log("on v" .. M.VERSION .. ": switch reads on the frame clock, her bag walked only when it changed, LF breakdown every "
                .. math.floor(M.WINDOW_MS / 1000) .. " s" .. (M.LF_LOG and "" or " (log off)"))
        elseif was and not M.active then
            M.bag = nil
            log("off: everything as before")
        end
    end
    if M.active and t - (M.windowAt or t) >= M.WINDOW_MS then M.report(t) end
end

if not M._hooked and Events and Events.OnTick and type(Events.OnTick.Add) == "function" then
    M._hooked = true
    Events.OnTick.Add(M.frame)
end
return M

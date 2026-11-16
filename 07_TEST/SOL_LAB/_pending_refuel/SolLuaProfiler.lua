-- SolLuaProfiler.lua - switch lua_profiler (s106, 2026-11-11). Diagnostic only: which mods' Lua eats the main thread.
-- JFR (PERF_STUTTER_20261111.md): 61% of the main thread is the Kahlua interpreter, 44% under IngameState.onTick, and JFR
-- cannot split it by mod. This times every Lua handler of OnTick, OnPlayerUpdate, OnRenderTick and OnZombieUpdate and sums
-- the time by source file (mod folder + file). Every 15 s it prints the top 15 files per event, in ms per second.
-- How (projectzomboid.jar 42.22.2, javap):
--   Events.<X> is a Lua table { Add = zombie.Lua.Event$Add, Remove = Event$Remove }; Event$Add.e is the zombie.Lua.Event and
--   Event.callbacks (public ArrayList<LuaClosure>) is what Event.trigger walks by index, calling each closure through
--   LuaCaller.protectedCallVoid. getNumClassFields/getClassField/getClassFieldVal (LuaManager.GlobalObject, -debug only)
--   reach that list from Lua. On: each closure in the list is replaced IN PLACE (ArrayList.set) by a timing wrapper, and
--   Events.<X>.Add/Remove become Lua functions that wrap new handlers and translate Remove(original) to the wrapper.
--   So handlers registered before this file loaded are timed too; load order does not matter.
--   Off: every original closure goes back into its slot and the Java Add/Remove go back into the tables (vanilla state).
-- Clock: getTimestampMs (System.currentTimeMillis; Lua has no finer clock). One handler call is far below 1 ms, so a single
--   reading is 0 or a clock step; summed over thousands of calls in 15 s the total is unbiased (calls start at random phase
--   to the clock). The clock step is measured at switch-on and printed.
-- Cost: two Java calls per timed call. Measured at switch-on (calibration loop, about 20-60 ms once) and printed per window
--   as "overhead ~X ms/s". OnZombieUpdate (one call per zombie per handler) times 1 call in STRIDE and scales it up.
-- Limits: a dispatcher library (one handler calling many mods' functions) is charged to the library's file. Times are
--   inclusive (a handler that triggers another profiled event is counted in both). A handler's error shows one extra frame
--   (this file) in the stack trace. Without -debug the reflection calls fail and nothing is wrapped (logged once).
SolLuaProfiler = SolLuaProfiler or {}
local M = SolLuaProfiler
M.VERSION = "0.1.0"
M.EVENTS = M.EVENTS or { "OnTick", "OnPlayerUpdate", "OnRenderTick", "OnZombieUpdate" }
M.STRIDE = M.STRIDE or { OnZombieUpdate = 4 }     -- time 1 call in N for very frequent events, scale by N
M.WINDOW_MS = M.WINDOW_MS or 15000
M.TOP = M.TOP or 15
M.TOP_MODS = M.TOP_MODS or 12
M.CALIB_N = M.CALIB_N or 20000
M.CHECK_MS = M.CHECK_MS or 1000                    -- switch read at most once a second
M.hooks = M.hooks or {}                            -- [event] = hook state
M.own = M.own or {}                                -- our own closures, never wrapped
M.active = M.active or false
M.cost = M.cost or { timedUs = 0, untimedUs = 0, stepMs = 0 }

local G = _G
local function log(m) print("[SolLuaProfiler] " .. tostring(m)) end
local function now() local f = rawget(G, "getTimestampMs"); if type(f) == "function" then return f() end; return 0 end
local function fmt(x, d) return string.format("%." .. tostring(d or 2) .. "f", x) end

function M.on()
    local A = rawget(G, "SolAuthority")
    if type(A) ~= "table" or type(A.on) ~= "function" then return false end
    local ok, v = pcall(A.on, "lua_profiler")
    return ok and v == true
end

-- "C:/.../108600/123/mods/EscapeFromZomboidFirearms/42/media/lua/client/TW/Core.lua" -> "EscapeFromZomboidFirearms/client/TW/Core.lua"
-- "media/lua/client/ISUI/ISPanel.lua" (no mods folder) -> "vanilla/client/ISUI/ISPanel.lua"
local keyCache = {}
function M.keyOf(fname)
    if fname == nil then return "?" end
    local s = string.gsub(tostring(fname), "\\", "/")
    local hit = keyCache[s]
    if hit ~= nil then return hit end
    local low = string.lower(s)
    local key
    local a, b, side = string.find(low, "/?media/lua/(%a+)/")
    local rel = a and string.sub(s, b + 1) or nil
    local mod, from = nil, 1
    while true do
        local ma, mb = string.find(low, "/mods/[^/]+/", from)
        if ma == nil or (a ~= nil and ma > a) then break end
        mod = string.sub(s, ma + 6, mb - 1); from = mb
    end
    if rel ~= nil then key = (mod or "vanilla") .. "/" .. side .. "/" .. rel
    else key = (mod and (mod .. "/") or "") .. (string.match(s, "([^/]+)$") or s) end
    keyCache[s] = key
    return key
end

local function fileOf(fn)
    local f = rawget(G, "getFilenameOfClosure")
    if type(f) ~= "function" then return nil end
    local ok, v = pcall(f, fn)
    return ok and v or nil
end
local function lineOf(fn)
    local f = rawget(G, "getFirstLineOfClosure")
    if type(f) ~= "function" then return 0 end
    local ok, v = pcall(f, fn)
    return ok and (tonumber(v) or 0) or 0
end

-- the Java callbacks list behind Events.<X>.Add (Event$Add.e.callbacks); nil when not reachable (no -debug, or Add replaced)
local function fieldVal(obj, name)
    local nf, gf, gv = rawget(G, "getNumClassFields"), rawget(G, "getClassField"), rawget(G, "getClassFieldVal")
    if type(nf) ~= "function" or type(gf) ~= "function" or type(gv) ~= "function" then return nil, "no reflection functions" end
    local okN, n = pcall(nf, obj)
    if not okN then return nil, tostring(n) end
    n = tonumber(n) or 0
    for i = 0, n - 1 do
        local okF, f = pcall(gf, obj, i)
        if okF and f ~= nil then
            -- Field.toString(): "[modifiers] type declaring.Class.name"; no Field method call needed
            local s = tostring(f)
            if string.sub(s, -(string.len(name) + 1)) == "." .. name then
                local okV, v = pcall(gv, obj, f)
                if okV and v ~= nil and v ~= "<private>" then return v end
                return nil, "field " .. name .. " unreadable"
            end
        end
    end
    return nil, "no field " .. name
end
function M.callbacksOf(javaAdd)
    local ev, why = fieldVal(javaAdd, "e")
    if ev == nil then return nil, why end
    local list, why2 = fieldVal(ev, "callbacks")
    if list == nil then return nil, why2 end
    local okS = pcall(function() return list:size() end)
    if not okS then return nil, "callbacks is not a list" end
    return list
end

local function listSize(list) local ok, n = pcall(function() return list:size() end); return ok and (tonumber(n) or 0) or 0 end
local function listGet(list, i) local ok, v = pcall(function() return list:get(i) end); if ok then return v end; return nil end
local function listSet(list, i, v) return (pcall(function() list:set(i, v) end)) end

-- the timing wrapper for one closure of one event
local function makeWrapper(fn, rec, stride, clock)
    if stride <= 1 then
        return function(...)
            local t0 = clock()
            fn(...)
            rec.ms = rec.ms + (clock() - t0)
            rec.n = rec.n + 1
        end
    end
    local k = 0
    return function(...)
        k = k + 1
        if k < stride then rec.u = rec.u + 1; return fn(...) end
        k = 0
        local t0 = clock()
        fn(...)
        rec.ms = rec.ms + (clock() - t0) * stride
        rec.n = rec.n + 1
    end
end
M._makeWrapper = makeWrapper

local function wrap(h, fn)
    local w = h.wrapOf[fn]
    if w ~= nil then return w end
    if h.origOf[fn] ~= nil then return fn end
    local file = fileOf(fn)
    local rec = { key = M.keyOf(file), line = lineOf(fn), ms = 0, n = 0, u = 0 }
    h.recs[#h.recs + 1] = rec
    w = makeWrapper(fn, rec, M.STRIDE[h.name] or 1, h.clock)
    h.wrapOf[fn], h.origOf[w] = w, fn
    return w
end

-- put a wrapper into every slot that still holds a raw closure (handlers added by a path that skipped our Add)
local function sweep(h)
    local n, c = listSize(h.list), 0
    for i = 0, n - 1 do
        local fn = listGet(h.list, i)
        if type(fn) == "function" and not M.own[fn] and h.origOf[fn] == nil then
            if listSet(h.list, i, wrap(h, fn)) then c = c + 1 end
        end
    end
    return c
end

local function removeFn(h, fn)
    local w = type(fn) == "function" and h.wrapOf[fn] or nil
    if w ~= nil then
        local ok, has = pcall(function() return h.list:contains(w) end)
        if ok and has == true then return h.remove(w) end
    end
    return h.remove(fn)
end

function M.calibrate(clock)
    clock = clock or rawget(G, "getTimestampMs")
    local n = M.CALIB_N
    local empty = function() end
    local rec = { ms = 0, n = 0, u = 0 }
    local w1 = makeWrapper(empty, rec, 1, clock)
    local w4 = makeWrapper(empty, rec, 1000000000, clock)    -- never times: the untimed path alone
    for i = 1, 2000 do empty(i); w1(i); w4(i) end             -- warm up first
    local b0, b1, b2 = 1e9, 1e9, 1e9                          -- best of 3 rounds (ms clock: rounds of n calls)
    for _ = 1, 3 do
        local t0 = clock(); for i = 1, n do empty(i) end; local d0 = clock() - t0
        t0 = clock(); for i = 1, n do w1(i) end; local d1 = clock() - t0
        t0 = clock(); for i = 1, n do w4(i) end; local d2 = clock() - t0
        if d0 < b0 then b0 = d0 end
        if d1 < b1 then b1 = d1 end
        if d2 < b2 then b2 = d2 end
    end
    local d0, d1, d2 = b0, b1, b2
    -- clock step: smallest change seen in a short spin
    local step, last, spins, a = 1e9, clock(), 0, clock()
    while spins < 200000 and clock() - a < 40 do
        spins = spins + 1
        local t = clock()
        if t ~= last then if t - last < step then step = t - last end; last = t end
    end
    if step == 1e9 then step = 0 end
    M.cost.timedUs = math.max(0, (d1 - d0) * 1000 / n)
    M.cost.untimedUs = math.max(0, (d2 - d0) * 1000 / n)
    M.cost.stepMs = step
    return M.cost
end

function M.enable()
    if M.active then return true end
    local clock = rawget(G, "getTimestampMs")
    local ev = rawget(G, "Events")
    if type(clock) ~= "function" or type(ev) ~= "table" then log("not started: no getTimestampMs or Events"); return false end
    local found, parts, any = {}, {}, false
    for _, name in ipairs(M.EVENTS) do          -- first only look: nothing changes unless at least one list is reachable
        local et = ev[name]
        if type(et) ~= "table" then parts[#parts + 1] = name .. "=no event"
        else
            local list, why = M.callbacksOf(rawget(et, "Add"))
            if list == nil then parts[#parts + 1] = name .. "=skipped (" .. tostring(why) .. ")" else found[name] = list; any = true end
        end
    end
    if not any then log("NOT STARTED " .. table.concat(parts, ", ")); return false end
    local c = M.calibrate(clock)
    log("calibration: timed call +" .. fmt(c.timedUs) .. " us, untimed call +" .. fmt(c.untimedUs) .. " us, clock step " .. tostring(c.stepMs) .. " ms")
    for _, name in ipairs(M.EVENTS) do
        local et = ev[name]
        local h = M.hooks[name] or { name = name, recs = {} }
        M.hooks[name] = h
        h.wrapOf, h.origOf, h.live, h.clock, h.recs = {}, {}, false, clock, {}
        local list = found[name]
        if list ~= nil then
            local add, remove = rawget(et, "Add"), rawget(et, "Remove")
            do
                h.tbl, h.add, h.remove, h.list, h.live = et, add, remove, list, true
                h.ourAdd = function(fn)
                    if type(fn) ~= "function" or M.own[fn] then return add(fn) end
                    return add(wrap(h, fn))
                end
                h.ourRemove = function(fn) return removeFn(h, fn) end
                rawset(et, "Add", h.ourAdd); rawset(et, "Remove", h.ourRemove)
                parts[#parts + 1] = name .. "=" .. tostring(sweep(h)) .. " handlers"
                any = true
            end
        end
    end
    M.active = any
    log((any and "ON " or "NOT STARTED ") .. table.concat(parts, ", "))
    return any
end

function M.disable()
    local parts = {}
    for _, name in ipairs(M.EVENTS) do
        local h = M.hooks[name]
        if h ~= nil and h.live then
            if rawget(h.tbl, "Add") == h.ourAdd then rawset(h.tbl, "Add", h.add) end
            if rawget(h.tbl, "Remove") == h.ourRemove then rawset(h.tbl, "Remove", h.remove) end
            local n, back = listSize(h.list), 0
            for i = 0, n - 1 do
                local x = listGet(h.list, i)
                local orig = x ~= nil and h.origOf[x] or nil
                if orig ~= nil and listSet(h.list, i, orig) then back = back + 1 end
            end
            parts[#parts + 1] = name .. "=" .. tostring(back) .. " restored"
            h.wrapOf, h.origOf, h.live, h.recs = {}, {}, false, {}
        end
    end
    M.active = false
    log("OFF " .. table.concat(parts, ", "))
end

-- one window: per event the top files, then the top mod folders over the four events
function M.report(spanMs, frames)
    local secs = math.max(0.001, spanMs / 1000)
    frames = math.max(1, frames or 1)
    local mods, modOrder, allMs, allOver = {}, {}, 0, 0
    for _, name in ipairs(M.EVENTS) do
        local h = M.hooks[name]
        if h ~= nil and h.live then
            local agg, order, total, calls, handlers, over = {}, {}, 0, 0, 0, 0
            for _, r in ipairs(h.recs) do
                local cnt = r.n + r.u
                if cnt > 0 then
                    handlers = handlers + 1
                    local a = agg[r.key]
                    if a == nil then a = { key = r.key, ms = 0, n = 0, line = r.line, lineMs = -1 }; agg[r.key] = a; order[#order + 1] = a end
                    a.ms = a.ms + r.ms; a.n = a.n + cnt
                    if r.ms > a.lineMs then a.lineMs = r.ms; a.line = r.line end
                    total = total + r.ms; calls = calls + cnt
                    over = over + r.n * M.cost.timedUs + r.u * M.cost.untimedUs
                    local mk = string.match(r.key, "^([^/]+)") or r.key
                    local mm = mods[mk]
                    if mm == nil then mm = { key = mk, ms = 0 }; mods[mk] = mm; modOrder[#modOrder + 1] = mm end
                    mm.ms = mm.ms + r.ms
                end
                r.ms, r.n, r.u = 0, 0, 0
            end
            allMs = allMs + total; allOver = allOver + over
            table.sort(order, function(x, y) return x.ms > y.ms end)
            log(name .. " " .. fmt(secs, 1) .. "s " .. tostring(frames) .. " frames: " .. fmt(total / secs) .. " ms/s (" .. fmt(total / frames) .. " ms/frame), "
                .. tostring(handlers) .. " handlers, " .. fmt(calls / secs, 0) .. " calls/s, profiler overhead ~" .. fmt(over / 1000 / secs) .. " ms/s")
            for i = 1, math.min(M.TOP, #order) do
                local a = order[i]
                if a.ms <= 0 then break end
                log(name .. " #" .. tostring(i) .. " " .. fmt(a.ms / secs) .. " ms/s  " .. a.key .. " (fn@L" .. tostring(a.line) .. ")  " .. fmt(a.n / secs, 0) .. " calls/s")
            end
        end
    end
    table.sort(modOrder, function(x, y) return x.ms > y.ms end)
    local parts = {}
    for i = 1, math.min(M.TOP_MODS, #modOrder) do
        if modOrder[i].ms <= 0 then break end
        parts[#parts + 1] = modOrder[i].key .. " " .. fmt(modOrder[i].ms / secs)
    end
    log("mods ms/s (4 events " .. fmt(allMs / secs) .. ", overhead ~" .. fmt(allOver / 1000 / secs) .. "): " .. table.concat(parts, " | "))
end

local ticks, frames, lastCheck, winStart = 0, 0, -1e12, 0
function M.tick()
    frames = frames + 1
    ticks = ticks + 1
    if ticks < 30 then return end
    ticks = 0
    local t = now()
    if t - lastCheck >= M.CHECK_MS then
        lastCheck = t
        local want = M.on()
        if want and not M.active and not M.failed then
            if M.enable() then winStart = now(); frames = 0
            else M.failed = true; log("not retried until lua_profiler goes off and on again") end
        elseif not want then
            M.failed = false
            if M.active then M.disable() end
        end
    end
    if M.active and t - winStart >= M.WINDOW_MS then
        local okR, err = pcall(M.report, t - winStart, frames)
        if not okR then log("report failed: " .. tostring(err)) end
        for _, name in ipairs(M.EVENTS) do local h = M.hooks[name]; if h ~= nil and h.live then sweep(h) end end
        winStart, frames = now(), 0
    end
end
M.own[M.tick] = true
function M.resetWindow()       -- start a fresh window now (tests; or by hand from the debug console)
    for _, name in ipairs(M.EVENTS) do local h = M.hooks[name]; if h ~= nil and h.recs ~= nil then for _, r in ipairs(h.recs) do r.ms, r.n, r.u = 0, 0, 0 end end end
    winStart, frames = now(), 0
end
M._sweep, M._wrap = sweep, wrap

if not M.tickAdded and type(rawget(G, "Events")) == "table" and Events.OnTick ~= nil then
    Events.OnTick.Add(M.tick)
    M.tickAdded = true
end
print("[SolLuaProfiler] ready v" .. M.VERSION .. " (switch lua_profiler, default off; events " .. table.concat(M.EVENTS, ",") .. ")")
return M

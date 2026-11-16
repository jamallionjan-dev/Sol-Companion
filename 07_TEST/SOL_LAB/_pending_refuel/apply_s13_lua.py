"""Run only after the game is closed, after copying SolBudget.lua into the client folder. The world scan and the recipe list are spread over frames under the shared allowance.
usage: apply_s13_lua.py <SolWorldScan.lua> <SolSkills.lua> <SolDress.lua> <SolLife.lua>"""
import sys
def patch(p, pairs):
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    for a, b in pairs:
        a, b = a.replace("\n", nl), b.replace("\n", nl)
        assert t.count(a) == 1, (p, a[:70], t.count(a))
        t = t.replace(a, b)
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("applied to", p)
patch(sys.argv[1], [
('''function U.scanWorld()
    local player = getSpecificPlayer and getSpecificPlayer(0)
''', '''local function scanJob()
    local player = getSpecificPlayer and getSpecificPlayer(0)
'''),
('''    for _, ctr in ipairs(centers) do
    for z = ctr[3] - ZSPAN, ctr[3] + ZSPAN do
        for x = ctr[1] - ctr[4], ctr[1] + ctr[4] do
            for y = ctr[2] - ctr[4], ctr[2] + ctr[4] do
                local sq = cell and call(cell, "getGridSquare", x, y, z)
''', '''    local function visit(x, y, z)
                local sq = cell and call(cell, "getGridSquare", x, y, z)
'''),
('''                end
            end
        end
    end
    end      -- windows
    local vlist, vseen, vfree = {}, {}, {}
''', '''                end
    end
    local function finish()
    local vlist, vseen, vfree = {}, {}, {}
'''),
('''    return snap
end

local scanSamples = 0
''', '''    return snap
    end
    -- the same squares in the same order as one loop would read them, but a few at a time
    local ci, ctr, xNow, yNow, zNow = 1, nil, nil, nil, nil
    local function step(budgetMs)
        local stopAt, n = nowMs() + budgetMs, 0
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
            if n % 12 == 0 and nowMs() >= stopAt then return false end
        end
    end
    return { step = step, finish = finish }
end
function U.scanWorld()
    local job = scanJob()
    if not job then return nil end
    while not job.step(1000000) do end
    return job.finish()
end
U._scanJob = scanJob

local scanSamples = 0
'''),
('''function U.writeWorldRaw()
    local ok, snap = pcall(U.scanWorld)
    if not ok then log("scan failed: " .. tostring(snap)); return false end
''', '''function U.writeWorldRaw(ready)
    local ok, snap = true, ready
    if ready == nil then ok, snap = pcall(U.scanWorld) end
    if not ok then log("scan failed: " .. tostring(snap)); return false end
'''),
('''local lastTick = 0
local function onTick()
    local t = nowMs()
    if t - lastTick < INTERVAL_MS then return end
    lastTick = t
    U.writeWorld()
end
U.scanNow = function() lastTick = 0; return U.writeWorld() end
if Events and Events.OnTick then Events.OnTick.Add(onTick) end
''', '''local lastTick = 0
local sliced, slicedMs = nil, 0
local function onTick(remainingMs)
    local t = nowMs()
    if sliced == nil then
        if t - lastTick < INTERVAL_MS then return end
        lastTick = t
        local ok, job = pcall(scanJob)
        if not ok or job == nil then return end
        sliced, slicedMs = job, 0
    end
    local ok, done = pcall(sliced.step, remainingMs or 2)
    slicedMs = slicedMs + (nowMs() - t)
    if not ok then log("scan failed: " .. tostring(done)); sliced = nil; return end
    if done then
        local job = sliced
        sliced = nil
        local okF, snap = pcall(job.finish)
        if not okF then log("scan failed: " .. tostring(snap)); return end
        local t1 = nowMs()
        U.writeWorldRaw(snap)
        U.worldScanTuned(slicedMs + (nowMs() - t1))
        if U.perfAdd then U.perfAdd("world_scan", slicedMs + (nowMs() - t1)) end
    end
end
U.scanNow = function() sliced = nil; lastTick = nowMs(); return U.writeWorld() end
require "SolBudget"
SolBudget.register("world_scan", onTick, { everyMs = 0, priority = 6 })
'''),
])
patch(sys.argv[2], [
('''        for i = job.i, stop - 1 do
            local rec = call(job.all, "get", i)
            if rec then local ok, info = pcall(U.recipeInfo, rec, job.actor); if ok then job.out[#job.out + 1] = info end end
        end
        job.i = stop
''', '''        for i = job.i, stop - 1 do
            local rec = call(job.all, "get", i)
            if rec then local ok, info = pcall(U.recipeInfo, rec, job.actor); if ok then job.out[#job.out + 1] = info end end
            job.i = i + 1
            if nowMs() - t0 >= 2 then break end
        end
'''),
('''if Events and Events.OnTick then Events.OnTick.Add(onTick) end
''', '''require "SolBudget"
SolBudget.register("recipes", onTick, { everyMs = 0, priority = 8 })
'''),
])
patch(sys.argv[3], [
('''if Events and Events.OnTick then Events.OnTick.Add(onTick) end
''', '''require "SolBudget"
SolBudget.register("dress", onTick, { everyMs = 500, priority = 4 })
'''),
])
patch(sys.argv[4], [
('''if Events and Events.OnTick then Events.OnTick.Add(tick) end
''', '''require "SolBudget"
SolBudget.register("life", tick, { everyMs = 250, priority = 4 })
'''),
])

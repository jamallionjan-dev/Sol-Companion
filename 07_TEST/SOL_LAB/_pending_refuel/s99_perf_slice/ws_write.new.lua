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
local function sliceOn() local A_ = rawget(_G, "SolAuthority"); return type(A_) == "table" and type(A_.on) == "function" and A_.on("perf_slice") == true end
U.worldSliceOn = sliceOn
local lastTick = 0
local sliced, slicedMs = nil, 0
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
    end
end
local function onTick(remainingMs)
    local t = nowMs()
    if sliced == nil then
        if t - lastTick < INTERVAL_MS then return end
        lastTick = t
        local ok, job = pcall(scanJob)
        if not ok or job == nil then return end
        sliced, slicedMs = job, 0
        if sliceOn() then                                                      -- s99 perf_slice: making the job is this frame's work
            local ms = nowMs() - t
            slicedMs = ms
            job.phase, job.tuneMs, job.di = "squares", ms, 1
            if U.perfAdd then U.perfAdd("world_scan", ms) end
            return
        end
    end
    if sliced.phase ~= nil or sliceOn() then                                   -- s99 perf_slice
        local okS, err = pcall(slicedTick, t, remainingMs)
        if not okS then log("scan failed: " .. tostring(err)); sliced = nil end
        return
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

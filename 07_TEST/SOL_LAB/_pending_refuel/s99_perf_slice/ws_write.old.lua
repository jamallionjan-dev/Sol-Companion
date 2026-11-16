function U.writeWorldRaw(ready)
    local ok, snap = true, ready
    if ready == nil then ok, snap = pcall(U.scanWorld) end
    if not ok then log("scan failed: " .. tostring(snap)); return false end
    if not snap then return false end
    if type(SolLife) == "table" and type(SolLife.snapshot) == "function" then
        local okL, life, streets, current = pcall(SolLife.snapshot)
        if okL then snap.solLife, snap.knownStreets, snap.currentStreet = life, streets, current end
    end
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
    if type(SolFarmWork) == "table" and type(SolFarmWork.snapshot) == "function" then
        local okF, farm = pcall(SolFarmWork.snapshot)
        if okF then snap.solFarm = farm end
    end
    if type(SolBookMemory) == "table" and type(SolBookMemory.snapshot) == "function" then      -- book_memory: her address book, compact, for the Mind
        local okBM, bm = pcall(SolBookMemory.snapshot)
        if okBM then snap.solBook = bm end
    end
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
    local ok2, text = pcall(encode, snap)
    if not ok2 then log("encode failed: " .. tostring(text)); return false end
    local okw, w = pcall(getFileWriter, FILE, true, false)
    if not okw or not w then return false end
    w:write(text); w:close()
    U.lastWorldWrite = nowMs()
    return true
end

local lastTick = 0
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

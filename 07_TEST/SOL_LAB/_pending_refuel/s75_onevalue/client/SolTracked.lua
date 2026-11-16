-- SolTracked.lua - switch tracked_mode.
-- Tracked vehicles (the Bradley and any other vehicle Trucksmith turns) have no steered wheels: Trucksmith turns them
-- with a push it computes from the steering value. Its loop only runs for vehicles a real player drives
-- (Trucksmith_Stabilizer.lua S.onTick: getSpecificPlayer(i) ... v:isDriver(player)), so with Sol at the wheel nothing turned.
-- Here the same two Trucksmith steps run for the vehicle Sol drives: TrackSteer.step (the turn) then Stabilizer.step (the push).
-- Nothing of Trucksmith's is changed; which way the turn goes is learned by SolSteerAdapt (vehicle_steer_adapt).
local M = {}
SolTracked = M
M.SCAN_MS = 1000
M.list, M.scanAt, M.failed, M.seen = {}, -1e9, false, {}

local function on(name)
    local A = rawget(_G, "SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on(name) == true
end

local function log(s) print("[SolTracked] " .. s) end

-- A vehicle Sol drives: a driver that is not one of the players at this screen. Trucksmith already runs those.
function M.npcDriven(v)
    local ok, d = pcall(function() return v:getDriver() end)
    if not ok or d == nil then return false end
    local okP, isPlayer = pcall(function() return instanceof(d, "IsoPlayer") and d:isLocalPlayer() end)
    return not (okP and isPlayer)
end

function M.api()
    local T = rawget(_G, "Trucksmith")
    if type(T) ~= "table" then return nil end
    local S, TS = T.Stabilizer, T.TrackSteer
    if type(S) ~= "table" or type(TS) ~= "table" then return nil end
    if type(S.step) ~= "function" or type(TS.step) ~= "function" or type(TS.config) ~= "function" then return nil end
    return S, TS
end

function M.rescan(TS, now)
    M.scanAt = now
    local list = {}
    local okWalk = pcall(function()
        local cell = getCell and getCell()
        local set = cell and cell:getVehicles()                   -- a java Set in 42.22: walked with its iterator
        if not set then return end
        local it = set:iterator()
        while it:hasNext() do
            local v = it:next()
            if v and M.npcDriven(v) then
                local ok, tc = pcall(TS.config, v)
                if ok and tc then list[#list + 1] = v end
            end
        end
    end)
    if not okWalk and not M.walkWarned then M.walkWarned = true; log("cell vehicles not readable") end
    M.list = list
end

function M.stepOne(S, TS, v, now)
    local tc = TS.config(v)
    if not tc then return end
    local a, b, d, e, f, g = TS.step(tc, v, now)
    if not a then return end
    local n = nil
    if type(S.config) == "function" and type(S.numbers) == "function" then
        local c = S.config(v)
        if c then n = S.numbers(c, v) end
    end
    S.step(n, v, now, e, f, g, a, b, d, nil)
    local id = v:getId()
    if not M.seen[id] then M.seen[id] = true; log("turning " .. tostring(v:getScriptName()) .. " for Sol through Trucksmith") end
end

function M.tick()
    if M.failed or not on("tracked_mode") then return end
    local S, TS = M.api()
    if not S then return end
    local now = getTimestampMs and getTimestampMs() or 0
    if now - M.scanAt >= M.SCAN_MS then M.rescan(TS, now) end
    for _, v in ipairs(M.list) do
        if M.npcDriven(v) then
            local ok, err = pcall(M.stepOne, S, TS, v, now)
            if not ok then M.failed = true; log("stopped after an error: " .. tostring(err)); return end
        end
    end
end

if Events and Events.OnTick then Events.OnTick.Add(M.tick) end
return M

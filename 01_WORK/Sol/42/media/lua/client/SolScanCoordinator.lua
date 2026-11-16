-- One Sol-owned spatial/inventory scan may hold the mission lease at a time.
-- LF's independent urgent perception does not acquire this lease.
SolScanCoordinator = SolScanCoordinator or {}
local C = SolScanCoordinator
C.active = nil
C.sequence = C.sequence or 0

local function log(text)
    print("[SolScanCoordinator] " .. tostring(text))
end

function C.tryAcquire(owner, profile)
    owner = tostring(owner or "")
    if owner == "" then return false, nil, "invalid_owner" end
    if C.active ~= nil then
        if C.active.owner == owner then return true, C.active.generation, "already_owned" end
        return false, nil, "busy:" .. tostring(C.active.owner)
    end
    C.sequence = C.sequence + 1
    C.active = { owner = owner, profile = tostring(profile or "mission"), generation = C.sequence, startedAt = (getTimestampMs and getTimestampMs()) or 0 }
    log("acquire owner=" .. owner .. " profile=" .. C.active.profile .. " generation=" .. tostring(C.sequence))
    return true, C.sequence, "acquired"
end

function C.release(owner, generation, reason)
    owner = tostring(owner or "")
    local active = C.active
    if active == nil or active.owner ~= owner then return false end
    if generation ~= nil and active.generation ~= generation then return false end
    C.active = nil
    log("release owner=" .. owner .. " generation=" .. tostring(active.generation) .. " reason=" .. tostring(reason or "done"))
    return true
end

function C.owns(owner, generation)
    local active = C.active
    return active ~= nil and active.owner == tostring(owner or "")
        and (generation == nil or active.generation == generation)
end

function C.cancelAll(reason)
    local active = C.active
    if active == nil then return false end
    C.active = nil
    log("cancel owner=" .. tostring(active.owner) .. " generation=" .. tostring(active.generation) .. " reason=" .. tostring(reason or "replaced"))
    return true, active.owner, active.generation
end

function C.status()
    local a = C.active
    if a == nil then return { busy = false, generation = C.sequence } end
    return { busy = true, owner = a.owner, profile = a.profile, generation = a.generation, startedAt = a.startedAt }
end

return C

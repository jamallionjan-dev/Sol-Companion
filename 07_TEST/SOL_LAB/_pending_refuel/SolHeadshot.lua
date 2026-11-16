-- Routes only successful Sol firearm hits through Build 42's native head-hit outcome.
SolHeadshotControl = SolHeadshotControl or {}
local C = SolHeadshotControl
C.lastSync = C.lastSync or 0

local function sync()
    local clock = rawget(_G, "getTimestampMs")
    local now = type(clock) == "function" and clock() or 0
    if now - C.lastSync < 1000 then return end
    C.lastSync = now
    local authority = rawget(_G, "SolAuthority")
    local enabled = type(authority) == "table" and type(authority.on) == "function"
        and authority.on("sol_headshots") == true
    local setter = rawget(_G, "solHeadshotSet")
    if type(setter) == "function" then pcall(setter, enabled) end
end

if Events ~= nil then
    if Events.OnGameStart and type(Events.OnGameStart.Add) == "function" then Events.OnGameStart.Add(sync) end
    if Events.OnTick and type(Events.OnTick.Add) == "function" then Events.OnTick.Add(sync) end
end

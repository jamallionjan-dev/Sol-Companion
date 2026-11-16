-- A tiny pure helper for the load-aware ordinary decision cadence.
local M = {}

function M.ordinaryInterval(baseMs, loadLevel, enabled, nowMs, urgentUntilMs)
    local base = tonumber(baseMs) or 100
    if base < 1 then base = 1 end
    local level = tonumber(loadLevel) or 0
    if enabled ~= true or level < 2 then return base end
    local now = tonumber(nowMs) or 0
    local urgentUntil = tonumber(urgentUntilMs) or 0
    if now < urgentUntil then return base end
    if base >= 150 then return base end
    return math.min(150, math.floor(base * 1.5))
end

return M

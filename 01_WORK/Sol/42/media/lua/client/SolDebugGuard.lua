-- SolDebugGuard.lua - switch debug_ctrl_a_guard. Keeps the Java guard (SolDebugGuard) in step with the switch.
-- The guard stops the game's debug Ctrl+A (add animal) from throwing in single player and dropping to the main menu.
local function on(name)
    local A = rawget(_G, "SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on(name) == true
end
if Events and Events.OnTick then
    local at = 0
    Events.OnTick.Add(function()
        local t = getTimestampMs and getTimestampMs() or 0
        if t - at < 2000 then return end
        at = t
        local f = rawget(_G, "solDebugGuardSet")
        if type(f) == "function" then pcall(f, on("debug_ctrl_a_guard")) end
    end)
end

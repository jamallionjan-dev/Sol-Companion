-- SolNavTick.lua - gives the Java navigation its frame. The work itself is sliced and threaded in Java.
local warmed = false
local function tick()
    local step = rawget(_G, "solNavStep")
    if type(step) ~= "function" then return end
    if not warmed then
        warmed = true
        local warm = rawget(_G, "solNavWarmUp")
        if type(warm) == "function" then pcall(warm) end
    end
    pcall(step)
end
if Events and Events.OnTick then Events.OnTick.Add(tick) end

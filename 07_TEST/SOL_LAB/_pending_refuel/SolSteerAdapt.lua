-- SolSteerAdapt.lua - switch vehicle_steer_adapt. Keeps the Java SolSteerAdapt in step with the switch.
-- Vehicles that turn the other way from her steering (some tracked vehicles) get her steering mirrored, learned from how they move.
local function on(name)
    local A = rawget(_G, "SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on(name) == true
end
if Events and Events.OnTick then
    local at, last = 0, nil
    Events.OnTick.Add(function()
        local t = getTimestampMs and getTimestampMs() or 0
        if t - at < 2000 then return end
        at = t
        local want = on("vehicle_steer_adapt")
        if want == last then return end
        local f = rawget(_G, "solSteerAdaptSet")
        if type(f) == "function" and pcall(f, want) then last = want end
    end)
end

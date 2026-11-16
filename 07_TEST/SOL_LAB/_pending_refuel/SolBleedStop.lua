-- SolBleedStop.lua - bleeding at the wheel: she gets out, bandages, and drives on. Switch: bleed_get_out.
--   Seen in the log: seated in a car she never starts treating a wound, and every drive is cancelled while it bleeds. On foot she bandages within seconds.
--   So: car stopped, no zombie close, bleeding for a few seconds -> she gets out. When the bleeding has stopped she takes the wheel for the same trip,
--   unless he gave another order meanwhile.
SolUI = SolUI or {}
local U = SolUI
local CHECK_MS, BLEED_MS, ZOMBIE_TILES, RESUME_WITHIN_MS = 1500, 3000, 6, 120000
local at, since, pending = 0, nil, nil

local function log(m) print("[SolBleedStop] " .. tostring(m)) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function on()
    local A = rawget(_G, "SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("bleed_get_out") == true
end
local function nowMs() return getTimestampMs and getTimestampMs() or 0 end
local function bleeding(s) return (tonumber(call(call(s, "getBodyDamage"), "getNumPartsBleeding")) or 0) > 0 end
local function zombieNear(s)
    local x, y = tonumber(call(s, "getX")), tonumber(call(s, "getY"))
    local list = call(getCell and getCell() or nil, "getZombieList")
    local n = tonumber(call(list, "size")) or 0
    if x == nil then return true end
    for i = 0, n - 1 do
        local z = call(list, "get", i)
        local zx, zy = tonumber(call(z, "getX")), tonumber(call(z, "getY"))
        if zx and (zx - x) ^ 2 + (zy - y) ^ 2 <= ZOMBIE_TILES * ZOMBIE_TILES and call(z, "isDead") ~= true then return true end
    end
    return false
end
local function say(s, line)
    local O = rawget(_G, "SolOverlay")
    if type(O) == "table" and type(O.speak) == "function" then pcall(O.speak, s, line, 4000) end
end

function U.solBleedTick(t)
    if not on() then since, pending = nil, nil; return end
    local s = type(U.solActor) == "function" and U.solActor() or nil
    if s == nil then return end
    local v = call(s, "getVehicle")
    local G = U.gps
    if v ~= nil then
        if not bleeding(s) then since = nil; return end
        since = since or t
        if t - since < BLEED_MS then return end
        if math.abs(tonumber(call(v, "getCurrentSpeedKmHour")) or 0) > 2 then return end
        if zombieNear(s) then return end
        local SC = rawget(_G, "SurvivorCompanion")
        local exit = type(SC) == "table" and type(SC.Vehicle) == "table" and SC.Vehicle.exit or nil
        if type(exit) ~= "function" then return end
        local dest = type(G) == "table" and G.dest or nil
        local ok, done = pcall(exit, s, v, call(v, "getSeat", s), { playerCommand = true })
        log("bleeding at the wheel: getting out -> " .. tostring(ok and done))
        if ok and done then
            say(s, "عم نزف، بنزل ضمّد حالي.")
            pending = dest and { x = dest.x, y = dest.y, at = t } or nil
        end
        since = nil
        return
    end
    if pending == nil then return end
    if t - pending.at > RESUME_WITHIN_MS then log("not resuming: it took too long"); pending = nil; return end
    local dest = type(G) == "table" and G.dest or nil
    if dest == nil or dest.x ~= pending.x or dest.y ~= pending.y then log("not resuming: he gave another order"); pending = nil; return end
    if bleeding(s) or zombieNear(s) then return end
    pending = nil
    if type(U.gpsStart) == "function" then
        local ok, why = pcall(U.gpsStart, nil, nil)
        log("bandaged: back to the trip -> " .. tostring(ok and why))
    end
end

if Events and Events.OnTick then
    Events.OnTick.Add(function()
        local t = nowMs()
        if t - at < CHECK_MS then return end
        at = t
        pcall(U.solBleedTick, t)
    end)
end

-- SolNavLeg.lua - when the road network stops short of where she was sent, she drives the rest over whatever ground a car can cross.
--   The drawn-path follower does it in short stages. Switch: SolAuthority "java_nav". Fuel stops are left to the refuel errand's own parking.
SolUI = SolUI or {}
local U = SolUI
local ARRIVED, FAILS, CHECK_MS, PLAN_MS = 3, 2, 250, 6000
local leg, nextCheck, doneKey = nil, 0, nil

local function log(m) print("[SolNavLeg] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function fn(name) local f = rawget(_G, name); if type(f) == "function" then return f end return nil end
local function on()
    local A = rawget(_G, "SolAuthority")
    if type(A) ~= "table" or type(A.on) ~= "function" then return false end
    local ok, v = pcall(A.on, "java_nav")
    return ok and v == true
end
local function carOf()
    local s = type(U.solActor) == "function" and U.solActor() or nil
    local v = call(s, "getVehicle")
    if v == nil or call(v, "getDriver") ~= s then return nil end
    return v, s
end
local function heading(v)
    local Vec = rawget(_G, "Vector3f")
    if Vec == nil then return nil end
    local f = call(v, "getForwardVector", Vec.new())
    return tonumber(call(f, "x")), tonumber(call(f, "z"))
end
local function stop() local f = fn("solNavStop"); if f then pcall(f) end end
local function finish(key, why)
    if leg and leg.following then stop() end
    leg, doneKey = nil, key
    log(why)
end

local function startStage(v, now)
    local plan, B = fn("solNavLeg"), rawget(_G, "SolBypass")
    if plan == nil or type(B) ~= "table" or type(B.measure) ~= "function" then return false end
    local okS, size = pcall(B.measure, v)
    local x, y = tonumber(call(v, "getX")), tonumber(call(v, "getY"))
    local hx, hy = heading(v)
    if not okS or type(size) ~= "table" or not x or not hx then return false end
    local ok, started = pcall(plan, v, x, y, hx, hy, leg.x, leg.y, size.wheelbase, size.kmax)
    if not ok or started ~= true then return false end
    leg.at, leg.following = now, false
    return true
end

local function tick()
    local G = U.gps
    if type(G) ~= "table" or type(U.gpsStatus) ~= "function" then return end
    local now = nowMs()
    if leg then local b = fn("solNavBeat"); if b then pcall(b) end end
    if now < nextCheck then return end
    nextCheck = now + CHECK_MS
    if not on() or fn("solNavLeg") == nil then return end
    local st = U.gpsStatus()
    local d = G.dest
    local key = d and (d.x .. "," .. d.y) or nil

    if leg then
        if key ~= leg.key or st.result == "stopped" or st.phase == "following" or st.phase == "planning" then finish(key, "abandoned: a new order"); doneKey = nil; return end
        local v = carOf()
        if v == nil then finish(leg.key, "abandoned: she left the wheel"); return end
        local state = fn("solNavState")
        local okS, s = pcall(state)
        if not okS or type(s) ~= "string" then finish(leg.key, "abandoned: no state"); return end
        if s == "ready" then
            local follow = fn("solNavFollow")
            if not follow or select(2, pcall(follow)) ~= true then finish(leg.key, "abandoned: follower refused"); return end
            leg.following = true
        elseif s == "capturing" or s == "planning" then
            if now - leg.at > PLAN_MS then leg.fails = leg.fails + 1; stop(); if leg.fails >= FAILS then finish(leg.key, "gave up: plan timeout") else startStage(v, now) end end
        elseif s == "following" then return
        else
            local good = s == "done"
            stop(); leg.following = false
            if not good then
                leg.fails = leg.fails + 1
                log("stage failed: " .. s)
                if leg.fails >= FAILS then finish(leg.key, "gave up: " .. s); return end
            end
            local x, y = tonumber(call(v, "getX")), tonumber(call(v, "getY"))
            if x and (x - leg.x) ^ 2 + (y - leg.y) ^ 2 <= ARRIVED ^ 2 then finish(leg.key, "arrived off the road"); return end
            if not startStage(v, now) then finish(leg.key, "gave up: cannot plan") end
        end
        return
    end

    if not d or key == doneKey or not (st.result == "arrived" or st.phase == "arrived") then return end
    if string.sub(tostring(d.name or ""), 1, 11) == "Gas station" then return end
    local v = carOf()
    if v == nil then return end
    local x, y = tonumber(call(v, "getX")), tonumber(call(v, "getY"))
    if not x or (x - d.x) ^ 2 + (y - d.y) ^ 2 <= ARRIVED ^ 2 then doneKey = key; return end
    if call(v, "isEngineRunning") ~= true and type(U.solEngine) == "function" then pcall(U.solEngine, "on") end
    leg = { key = key, x = d.x, y = d.y, fails = 0, following = false, at = now }
    log("the road stops short: driving the rest to " .. key)
    if not startStage(v, now) then finish(key, "gave up: cannot plan") end
end

if Events and Events.OnTick then Events.OnTick.Add(function() pcall(tick) end) end
return U

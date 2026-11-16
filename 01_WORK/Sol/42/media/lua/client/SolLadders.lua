-- SolLadders.lua - Sol goes up and down ladders when she has no other way to his floor. Switch: sol_ladders.
--   The game's path finder has no ladders in it, so the walk to the ladder and the climb are separate steps. The climb itself is the game's own.
--   ladder_fast_slide is applied in Java (SolLadderFast); this file only tells Java whether the switch is on.
SolLadders = SolLadders or {}
local L = SolLadders
local RADIUS, WAIT_MS, SCAN_MS, GIVE_UP_MS, BLOCK_MS, MAX_TRIES, MAX_TO_GOAL2 = 16, 5000, 3000, 25000, 30000, 3, 40 * 40

local function log(text) print("[SolLadders] " .. tostring(text)) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function on(name)
    local A = rawget(_G, "SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on(name) == true
end
local function floorOf(sq) local z = tonumber((call(sq, "getZ"))); return z and math.floor(z) or nil end
local function same(a, b)
    return a ~= nil and b ~= nil and call(a, "getX") == call(b, "getX") and call(a, "getY") == call(b, "getY") and call(a, "getZ") == call(b, "getZ")
end
local function tell(actor, up)
    local line = up and "ما قدرت إطلع عالسلم." or "ما قدرت إنزل عالسلم."
    log((up and "up" or "down") .. ": gave up")
    local O = rawget(_G, "SolOverlay")
    if type(O) == "table" and type(O.speak) == "function" then pcall(O.speak, actor, line, 4000) end
end
local function threatened(actor) return (tonumber((call(actor, "getSurroundingAttackingZombies"))) or 0) > 0 end

local function scan(actor, src, goal, fz, up)
    local cell = getCell and getCell() or nil
    local cx, cy, gx, gy = tonumber((call(src, "getX"))), tonumber((call(src, "getY"))), tonumber((call(goal, "getX"))), tonumber((call(goal, "getY")))
    if cell == nil or cx == nil or gx == nil then return nil end
    local best, bestCost = nil, nil
    for x = cx - RADIUS, cx + RADIUS do
        for y = cy - RADIUS, cy + RADIUS do
            local sq = call(cell, "getGridSquare", x, y, fz)
            if sq ~= nil then
                local ok
                if up then ok = call(sq, "getLadder") ~= nil and call(actor, "getClimbLadder", sq) ~= nil
                else ok = call(sq, "getLadderUnder") ~= nil and call(actor, "getClimbLadderDown", sq) ~= nil end
                if ok then
                    local toGoal = (x - gx) ^ 2 + (y - gy) ^ 2
                    local cost = (x - cx) ^ 2 + (y - cy) ^ 2 + toGoal
                    if toGoal <= MAX_TO_GOAL2 and (bestCost == nil or cost < bestCost) then best, bestCost = sq, cost end
                end
            end
        end
    end
    return best
end

-- the ladder she should use now, or nil while the normal way may still work
local function decide(actor, state, src, goal, now)
    if type(state) ~= "table" or not on("sol_ladders") then return nil end
    local fz, gz = floorOf(src), floorOf(goal)
    if fz == nil or gz == nil or fz == gz then state.solLadder = nil; return nil end
    local key, s = fz .. ">" .. gz, state.solLadder
    if type(s) ~= "table" or s.key ~= key then s = { key = key, since = now, tries = 0 }; state.solLadder = s end
    if s.blockedUntil ~= nil and now < s.blockedUntil then return nil end
    if now - s.since < WAIT_MS or threatened(actor) then return nil end
    local up = gz > fz
    if s.scanAt == nil or now - s.scanAt >= SCAN_MS then
        local found = scan(actor, src, goal, fz, up)
        if found ~= nil and not same(found, s.target) then
            log((up and "up" or "down") .. ": ladder at " .. tostring(call(found, "getX")) .. "," .. tostring(call(found, "getY")))
        end
        s.target, s.scanAt = found, now
    end
    return s, up
end

local function block(actor, s, up, now)
    s.blockedUntil, s.tries, s.walkSince, s.target, s.scanAt = now + BLOCK_MS, 0, nil, nil, nil
    tell(actor, up)
end

-- the square to walk to, when she is not standing at the ladder yet
function L.walkGoal(actor, state, src, goal, now)
    local s, up = decide(actor, state, src, goal, now)
    if s == nil or s.target == nil or same(s.target, src) then return nil end
    s.walkSince = s.walkSince or now
    if now - s.walkSince > GIVE_UP_MS then block(actor, s, up, now); return nil end
    return s.target
end

local function downSpot(square, ladder)
    local x, y = (tonumber((call(square, "getX"))) or 0) + 0.5, (tonumber((call(square, "getY"))) or 0) + 0.7
    local P, props = rawget(_G, "IsoPropertyType"), call(ladder, "getProperties")
    if P == nil or props == nil then return x, y end
    if call(props, "has", P.LADDER_S) == true then y = y - 0.5
    elseif call(props, "has", P.LADDER_E) == true then y, x = y - 0.2, x - 0.3
    elseif call(props, "has", P.LADDER_W) == true then y, x = y - 0.2, x + 0.3 end
    return x, y
end

-- standing at the ladder: what to climb
function L.climbHere(actor, state, src, goal, now)
    local s, up = decide(actor, state, src, goal, now)
    if s == nil or s.target == nil or not same(s.target, src) then return nil end
    s.tries = s.tries + 1
    if s.tries > MAX_TRIES then block(actor, s, up, now); return nil end
    local ladder = call(actor, up and "getClimbLadder" or "getClimbLadderDown", src)
    if ladder == nil then s.target, s.scanAt = nil, nil; return nil end
    log((up and "up" or "down") .. ": climbing")
    if up then return { down = false } end
    local x, y = downSpot(src, ladder)
    return { down = true, x = x, y = y }
end

if Events and Events.OnTick then
    local at = 0
    Events.OnTick.Add(function()
        local t = getTimestampMs and getTimestampMs() or 0
        if t - at < 2000 then return end
        at = t
        local f = rawget(_G, "solLadderFastSet")
        if type(f) == "function" then pcall(f, on("ladder_fast_slide")) end
    end)
end

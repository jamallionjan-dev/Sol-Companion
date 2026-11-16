-- SolRestoreHands.lua - switch restore_hands (2026-11-11). When a saved weapon could not be put in her hand while her body was being
-- rebuilt, the restore goes on with the item in her bag (SCPersistence, s93) and this puts it back in her hand once she stands in the
-- world: a few tries, a second apart. Two-handed items take both hands. Logs only.
SolRestoreHands = SolRestoreHands or {}
local R = SolRestoreHands
R.queue = R.queue or {}
local function log(m) print("[SolRestoreHands] " .. tostring(m)) end
local function on() local A = rawget(_G, "SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on("restore_hands") == true end
local function now() return getTimestampMs and getTimestampMs() or 0 end

function R.later(actor, item, hand)
    if actor == nil or item == nil then return end
    R.queue[#R.queue + 1] = { a = actor, it = item, hand = hand, tries = 0, at = now() + 1500 }
    log("will put back " .. tostring(hand) .. " " .. tostring(item.getFullType and item:getFullType() or item))
end

local function tryOne(q)
    local a, it = q.a, q.it
    local okSq, sq = pcall(function() return a:getCurrentSquare() end)
    if not okSq or sq == nil then return false end
    local okC, cont = pcall(function() return it:getContainer() end)
    local okI, inv = pcall(function() return a:getInventory() end)
    if okC and okI and cont ~= inv then pcall(function() inv:AddItem(it) end) end
    local twoHanded = false
    pcall(function() twoHanded = it:isTwoHandWeapon() == true end)
    if q.hand == "primary" then
        pcall(function() a:setPrimaryHandItem(it) end)
        if twoHanded then pcall(function() a:setSecondaryHandItem(it) end) end
        local okR, cur = pcall(function() return a:getPrimaryHandItem() end)
        return okR and cur == it
    end
    pcall(function() a:setSecondaryHandItem(it) end)
    local okR, cur = pcall(function() return a:getSecondaryHandItem() end)
    return okR and cur == it
end

function R.tick()
    if #R.queue == 0 or not on() then return end
    local t = now()
    for i = #R.queue, 1, -1 do
        local q = R.queue[i]
        if t >= q.at then
            q.tries = q.tries + 1
            if tryOne(q) then log("back in her " .. tostring(q.hand) .. " hand"); table.remove(R.queue, i)
            elseif q.tries >= 10 then log("left in her bag after " .. q.tries .. " tries (" .. tostring(q.hand) .. ")"); table.remove(R.queue, i)
            else q.at = t + 1000 end
        end
    end
end

if Events and Events.OnTick and not R.hooked then R.hooked = true; Events.OnTick.Add(function() pcall(R.tick) end) end
log("ready v0.1.0")
return R

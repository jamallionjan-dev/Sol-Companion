-- SolVehShootSeated.lua - switch veh_shoot_seated. While HE (a local human player) sits in a vanilla car seat, aiming keeps
-- the seated body instead of the standing aim pose that pushes his upper body out through the roof.
-- Sources (game 42.22.2, read-only):
--   media/AnimSets/player-vehicle/aim/aim_default.xml, aim_rifle.xml, aim_handgun.xml ...: the seated "aim" state plays the
--     STANDING clips (Bob_IdleAim1Hand, Bob_IdleAimRifle, Bob_IdleAimHandgun ...) with no bone mask, while
--     media/AnimSets/player-vehicle/idle/default.xml plays Bob_IdleDriving. So aiming in a vanilla car stands the body up.
--   media/AnimSets/player-vehicle/ranged/firearm/FirearmDefault.xml: the shot is a SUB-state with upper-body bone weights,
--     layered over whatever the aim node plays. So a seated aim node keeps him seated and the shot still raises the gun.
--   AnimNode.compareSelectionConditions (projectzomboid.jar): nodes are ranked by m_ConditionPriority first, then by the
--     number of conditions; AnimState.getAnimNodes keeps only the top rank that passes. Our node (AnimSets/player-vehicle/
--     aim/SolSeatAim.xml) has m_ConditionPriority 10 and one condition, SolSeatAim == true, so it wins only while this file
--     sets that variable, and the vanilla nodes come back the moment it is cleared.
--   IsoPlayer.updateWhileInVehicle / attackWhileInVehicle: aiming and firing from a seat are vanilla; firing needs the
--     seat's door window open, broken or removed (VehicleWindow.isHittable false). Nothing here changes that.
-- KI5 (damnlib) cars already keep the seat pose in aim (their own nodes, variable damnVehicle=True): we step aside there.
-- This file only sets or clears ONE animation variable on the local human player; it never moves, seats, aims or fires
-- anyone, and Sol (the companion) is never touched. Switch off -> the variable is cleared on the next tick after
-- SolAuthority re-reads the switch file (at most ~5 s).
SolUI = SolUI or {}
local U = SolUI
SolVehShootSeated = SolVehShootSeated or {}
local M = SolVehShootSeated
M.VERSION = "0.1.0"
M.FIX = "veh_shoot_seated"
M.VAR = "SolSeatAim"
M.TICK_MS = 100

local function g(name) return rawget(_G, name) end
local function nowMs() local f = g("getTimestampMs"); if f then return f() end; return os.time() * 1000 end
local function log(m) print("[SolVehShootSeated] " .. tostring(m)) end
-- every game method is looked up before it is called (in debug mode a thrown Java error halts the game)
local function vcall(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function switchOn()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on(M.FIX) == true
end
local function solActor() if type(U.solActor) == "function" then local ok, a = pcall(U.solActor); if ok then return a end end; return nil end

-- KI5 / damnlib manages this car's seat poses (and keeps the seat pose while aiming): leave it to them.
function M.ki5(pl, veh)
    local D = g("DAMN")
    if type(D) == "table" and type(D.vehicleIsManaged) == "function" then
        local script = vcall(veh, "getScript")
        local name = vcall(script, "getFullName")
        if type(name) == "string" then
            local ok, managed = pcall(D.vehicleIsManaged, D, name)
            if ok and managed then return true end
        end
    end
    return vcall(pl, "getVariableString", "damnVehicle") == "True"
end

-- (wanted, reason) for one local player
function M.wanted(pl)
    if pl == nil then return false, "no_player" end
    if not switchOn() then return false, "switch_off" end
    if vcall(pl, "isDead") == true then return false, "dead" end
    local sol = solActor()
    if sol ~= nil and sol == pl then return false, "sol" end
    local veh = vcall(pl, "getVehicle")
    if veh == nil then return false, "not_in_vehicle" end
    if M.ki5(pl, veh) then return false, "ki5_seat_poses" end
    return true, "seated"
end

M.set = M.set or {}          -- [player number] = true while we hold the variable on that player

function M.update(pl, idx)
    local want, why = M.wanted(pl)
    local had = M.set[idx] == true
    if want and not had then
        vcall(pl, "setVariable", M.VAR, true)
        M.set[idx] = true
        log("player " .. tostring(idx) .. " seated aim on (" .. why .. ")")
    elseif not want and had then
        if pl ~= nil then vcall(pl, "clearVariable", M.VAR) end
        M.set[idx] = nil
        log("player " .. tostring(idx) .. " seated aim off (" .. why .. ")")
    end
    return want, why
end

M.lastTick = nil
function M.tick()
    local now = nowMs()
    if M.lastTick ~= nil and now - M.lastTick < M.TICK_MS then return end
    M.lastTick = now
    local gsp = g("getSpecificPlayer")
    if gsp == nil then return end
    local n = 1
    local gnp = g("getNumActivePlayers")
    if gnp ~= nil then local ok, v = pcall(gnp); if ok and type(v) == "number" and v >= 1 then n = v end end
    for i = 0, 3 do
        local pl = nil
        if i < n then local ok, p = pcall(gsp, i); if ok then pl = p end end
        if pl ~= nil or M.set[i] then M.update(pl, i) end
    end
end

if Events and Events.OnTick and not M.hooked then
    Events.OnTick.Add(M.tick)
    M.hooked = true
end

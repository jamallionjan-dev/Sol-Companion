-- SolActionRegistry.lua - Layer 1: one generic runner for the game's own timed actions (Build 42.21: 273 classes
-- derived from ISBaseTimedAction, scanned 2026-10-25 from the installed media/lua), plus a verb table that gives the
-- brain a small, checkable vocabulary. No action is executed unless its precondition (the "no cheating" gate)
-- passes; the gate result and reason go into the catalog so Sol can say *why* before trying.
--
-- Loads after SolActions.lua and wraps U.runAction / U.actionCatalog at OnGameStart. Verbs are reachable
-- through the same SolAct_Request.txt channel: action=<verb> option=<text>.
require "SolActions"
SolUI = SolUI or {}
local U = SolUI
local SC = SurvivorCompanion
U.REGISTRY_VERSION = "0.1.3"
local function log(m) print("[SolRegistry] " .. tostring(m)) end
local function mcall(o, name, ...) if o == nil then return nil end local f = o[name]; if type(f) ~= "function" then return nil end local ok, v = pcall(f, o, ...); if ok then return v end return nil end
local function sol() return U.solActor and U.solActor() or nil end
local function player() return getSpecificPlayer and getSpecificPlayer(0) or nil end
local function dist2(a, bx, by) return (a:getX() - bx) ^ 2 + (a:getY() - by) ^ 2 end

-- ---------------------------------------------------------------- generic timed-action runner
-- U.timed("ISToggleStoveAction", sol, stove) -> true,"queued" | false,reason
function U.timed(className, ...)
    local cls = _G[className]
    if type(cls) ~= "table" or type(cls.new) ~= "function" then return false, "no_class:" .. tostring(className) end
    local ok, act = pcall(cls.new, cls, ...)
    if not ok or not act then return false, "new_failed:" .. tostring(act) end
    if type(act.isValid) == "function" then
        local okv, valid = pcall(act.isValid, act)
        if okv and valid == false then return false, "not_valid_now" end
    end
    local okq, err = pcall(ISTimedActionQueue.add, act)
    if not okq then return false, "queue_failed:" .. tostring(err) end
    return true, "queued"
end
function U.queueIdle(actor)
    local q = ISTimedActionQueue and ISTimedActionQueue.getTimedActionQueue and ISTimedActionQueue.getTimedActionQueue(actor)
    local qq = q and q.queue
    return qq == nil or #qq == 0
end

-- ---------------------------------------------------------------- world lookups (what Sol can actually see)
local SCAN = 14
local function eachObjectNear(cx, cy, z, radius, fn)
    local cell = getCell and getCell()
    if not cell then return end
    for x = cx - radius, cx + radius do
        for y = cy - radius, cy + radius do
            local sq = cell:getGridSquare(x, y, z)
            local objs = sq and mcall(sq, "getObjects")
            local n = objs and (tonumber((mcall(objs, "size"))) or 0) or 0
            for i = 0, n - 1 do
                local o = mcall(objs, "get", i)
                if o and fn(o, sq, x, y) == true then return o, sq end
            end
        end
    end
end
-- nearest object of a Java class (e.g. "IsoStove", "IsoDoor", "IsoWindow", "IsoLightSwitch") around an actor
function U.nearestObject(actor, javaClass, radius, filter)
    if not actor then return nil end
    local ax, ay, z = actor:getX(), actor:getY(), math.floor(actor:getZ())
    local best, bd = nil, nil
    eachObjectNear(math.floor(ax), math.floor(ay), z, radius or SCAN, function(o, sq, x, y)
        if instanceof and instanceof(o, javaClass) and (not filter or filter(o)) then
            local d = (x + 0.5 - ax) ^ 2 + (y + 0.5 - ay) ^ 2
            if not bd or d < bd then best, bd = o, d end
        end
        return false
    end)
    return best, bd and math.sqrt(bd) or nil
end
-- stoves that can run: powered (grid or generator) or fuelled; IsoStove exposes isActivated / Activate / getContainer
function U.nearestStove(actor, radius)
    return U.nearestObject(actor, "IsoStove", radius, function(o) return mcall(o, "getContainer") ~= nil end)
end
local function stoveUsable(stove)
    -- Build 42.21 source: ISOvenUI / StoveToggle / ISInventoryPaneContextMenu test stove:getContainer():isPowered()
    local c = mcall(stove, "getContainer")
    if c and mcall(c, "isPowered") == true then return true end
    return false, "stove_has_no_power"
end
U.stoveUsable = stoveUsable

-- ---------------------------------------------------------------- verbs: checkable vocabulary over the 273 classes
-- Each verb: label (for the brain), check(sol, player, opt) -> ok, reason, ctx ; run(sol, player, opt, ctx) -> ok, reason
-- check is a dry run; it must not change the world. run is called only after check passed.
local V = {}
U.verbs = V
local function nearDoor(actor, wantOpen)
    return U.nearestObject(actor, "IsoDoor", 6, function(d) return mcall(d, "IsOpen") ~= wantOpen end)
end
V.sol_open_door = { label = "open the nearest closed door",
    check = function(s) local d = nearDoor(s, true); if not d then return false, "no_closed_door_near" end return true, "ok", d end,
    run = function(s, p, o, d) return U.timed("ISOpenCloseDoor", s, d) end }
V.sol_close_door = { label = "close the nearest open door",
    check = function(s) local d = nearDoor(s, false); if not d then return false, "no_open_door_near" end return true, "ok", d end,
    run = function(s, p, o, d) return U.timed("ISOpenCloseDoor", s, d) end }
V.sol_open_window = { label = "open / close the nearest window",
    check = function(s) local w = U.nearestObject(s, "IsoWindow", 6); if not w then return false, "no_window_near" end return true, "ok", w end,
    run = function(s, p, o, w) return U.timed("ISOpenCloseWindow", s, w) end }
V.sol_toggle_light = { label = "flip the nearest light switch",
    check = function(s) local l = U.nearestObject(s, "IsoLightSwitch", 8); if not l then return false, "no_light_switch_near" end return true, "ok", l end,
    run = function(s, p, o, l) return U.timed("ISToggleLightAction", s, l) end }
V.sol_stove_on = { label = "turn the nearest stove on",
    check = function(s) local st = U.nearestStove(s, 10); if not st then return false, "no_stove_near" end
        local ok, why = stoveUsable(st); if not ok then return false, why end
        if mcall(st, "Activated") == true then return false, "already_on" end return true, "ok", st end,
    run = function(s, p, o, st) return U.timed("ISToggleStoveAction", s, st) end }
V.sol_stove_off = { label = "turn the nearest stove off",
    check = function(s) local st = U.nearestStove(s, 10); if not st then return false, "no_stove_near" end
        if mcall(st, "Activated") ~= true then return false, "already_off" end return true, "ok", st end,
    run = function(s, p, o, st) return U.timed("ISToggleStoveAction", s, st) end }
V.sol_rest = { label = "rest on the nearest bed (or sit on the ground)",
    check = function(s) local b = U.nearestObject(s, "IsoObject", 10, function(o) return mcall(o, "getSprite") and mcall(mcall(mcall(o, "getSprite"), "getProperties"), "Is", "IsBed") == true end)
        return true, b and "bed" or "ground", b end,
    run = function(s, p, o, b) if b then return U.timed("ISRestAction", s, b, true) end return U.timed("ISSitOnGround", s, nil) end }
V.sol_wash = { label = "wash herself at the nearest sink / water source",
    check = function(s) local w = U.nearestObject(s, "IsoObject", 10, function(o) return mcall(o, "hasWater") == true end)
        if not w then return false, "no_water_source_near" end return true, "ok", w end,
    run = function(s, p, o, w) return U.timed("ISWashYourself", s, w) end }
V.sol_equip_best = { label = "equip the best weapon in her bag (option: melee / gun)",
    check = function(s, p, o)
        local best, bs
        for _, rec in ipairs(U.solBagItems and U.solBagItems(s) or {}) do
            local it = rec.item
            if instanceof and instanceof(it, "HandWeapon") then
                local gun = mcall(it, "isRanged") == true
                if (o ~= "gun" or gun) and (o ~= "melee" or not gun) then
                    local sc = (tonumber((mcall(it, "getMaxDamage"))) or 0) * (tonumber((mcall(it, "getCondition"))) or 1)
                    if not bs or sc > bs then best, bs = it, sc end
                end
            end
        end
        if not best then return false, "no_weapon_in_her_bag" end
        if mcall(s, "getPrimaryHandItem") == best then return false, "already_equipped" end
        return true, "ok", best
    end,
    run = function(s, p, o, it) return U.timed("ISEquipWeaponAction", s, it, 50, true, mcall(it, "isTwoHandWeapon") == true) end }
V.sol_reload = { label = "reload the gun in her hands",
    check = function(s) local g = mcall(s, "getPrimaryHandItem")
        if not g or mcall(g, "isRanged") ~= true then return false, "no_gun_in_hands" end return true, "ok", g end,
    run = function(s, p, o, g) return U.timed("ISReloadWeaponAction", s, g) end }
V.sol_take_pill = { label = "take painkillers / pills from her bag (option: part of the item name)",
    check = function(s, p, o)
        for _, rec in ipairs(U.solBagItems and U.solBagItems(s) or {}) do
            local n = string.lower(tostring(mcall(rec.item, "getFullType") or ""))
            if string.find(n, "pills", 1, true) and (not o or o == "" or string.find(n, string.lower(o), 1, true)) then return true, "ok", rec.item end
        end
        return false, "no_pills_in_her_bag"
    end,
    run = function(s, p, o, it) return U.timed("ISTakePillAction", s, it) end }
V.sol_fill_water = { label = "fill an empty bottle from the nearest water source",
    check = function(s)
        local w = U.nearestObject(s, "IsoObject", 10, function(o) return mcall(o, "hasWater") == true end)
        if not w then return false, "no_water_source_near" end
        for _, rec in ipairs(U.solBagItems and U.solBagItems(s) or {}) do
            local fc = mcall(rec.item, "getFluidContainer")
            if fc and mcall(fc, "isEmpty") == true then return true, "ok", { src = w, bottle = rec.item } end
        end
        return false, "no_empty_bottle_in_her_bag"
    end,
    run = function(s, p, o, c) return U.timed("ISTakeWaterAction", s, c.bottle, c.src, false) end }

V.sol_take_wheel = { label = "take the wheel only: Sol gets into the driver's seat; this does not start a trip. Use for: take the wheel, sit in the driver seat.",
    check = function() if not U.gpsTakeWheel then return false, "gps_unavailable" end return true, "ok" end,
    run = function() return U.gpsTakeWheel() end }
V.sol_pilot_helicopter = { label = "Sol takes the pilot seat of the helicopter she and the player are riding in; the helicopter must be stopped. If the player is piloting, Sol moves him to a reachable empty passenger seat first. Does not eject anyone or start a flight.",
    check = function(s, p)
        local h = rawget(_G, "SolHeliGPS")
        if type(h) ~= "table" or type(h.takePilot) ~= "function" then return false, "heli_gps_unavailable" end
        local v = s and mcall(s, "getVehicle")
        if not v or not h.isSolInHelicopter or h.isSolInHelicopter() ~= true then return false, "sol_not_in_helicopter" end
        if not p or mcall(p, "getVehicle") ~= v then return false, "player_not_in_same_helicopter" end
        return true, "ok", v
    end,
    run = function() return SolHeliGPS.takePilot() end }
V.sol_heli_fly_marker = { label = "start Sol's direct-air helicopter GPS flight to the destination already selected on Sol GPS; does not choose a destination or landing point.",
    check = function(s, p)
        local h = rawget(_G, "SolHeliGPS")
        if type(h) ~= "table" or type(h.start) ~= "function" or type(h.isSolInHelicopter) ~= "function" then
            return false, "heli_gps_unavailable"
        end
        if type(SolAuthority) ~= "table" or type(SolAuthority.on) ~= "function"
            or SolAuthority.on("heli_gps") ~= true or SolAuthority.on("heli_voice_fly") ~= true then
            return false, "heli_voice_fly_disabled"
        end
        local v = s and mcall(s, "getVehicle")
        if not v or h.isSolInHelicopter() ~= true then return false, "sol_not_in_helicopter" end
        if not p or mcall(p, "getVehicle") ~= v then return false, "player_not_in_same_helicopter" end
        if type(U.gpsStatus) ~= "function" or type(U.gpsStart) ~= "function" then return false, "gps_unavailable" end
        local status = U.gpsStatus()
        if type(status) ~= "table" or type(status.dest) ~= "table" or not status.dest.x or not status.dest.y then
            return false, "no_destination"
        end
        return true, "ok"
    end,
    run = function() return U.gpsStart(nil, false) end }
V.sol_summon_helicopter = { label = "request a fresh, fully fueled helicopter of the last helicopter model the player drove; AviationCore must have that model registered, otherwise request the UH-1B Huey.",
    check = function()
        local h = rawget(_G, "SolHeliGPS")
        if type(h) ~= "table" or type(h.summonHelicopter) ~= "function" then
            return false, "heli_summon_unavailable"
        end
        return true, "ok"
    end,
    run = function() return SolHeliGPS.summonHelicopter() end }
V.sol_let_player_drive = { label = "when asked to give control, Sol leaves the driver/pilot seat for a reachable empty passenger seat in the same stationary car, helicopter, or tracked vehicle; she stays aboard and does not eject anyone.",
    check = function(s, p)
        local enabled = type(SolAuthority) == "table" and type(SolAuthority.on) == "function"
            and SolAuthority.on("seat_handoff") == true
        if not enabled then return false, "seat_handoff_disabled" end
        local v = s and mcall(s, "getVehicle")
        if not v or mcall(v, "getSeat", s) ~= 0 then return false, "sol_not_driving" end
          if not p then return false, "player_unavailable" end
          local playerVehicle = mcall(p, "getVehicle")
          if playerVehicle ~= nil and playerVehicle ~= v then return false, "player_in_other_vehicle" end
          if playerVehicle == v and mcall(v, "getSeat", p) == 0 then return false, "player_already_driving" end
        if not (SC and SC.Vehicle and type(SC.Vehicle.shiftFromDriver) == "function") then
            return false, "seat_switch_unavailable"
        end
        return true, "ok", v
    end,
    run = function(s, p, o, v) return SC.Vehicle.shiftFromDriver(s, v) end }
V.sol_sit_beside = { label = "sit next to me: get into the front passenger seat of the car the player is driving. Use for: sit beside me, get in next to me.",
    check = function(s, p) local v = p and p:getVehicle(); if not v then return false, "player_not_in_car" end return true, "ok", v end,
    run = function(s, p, o, v)
        if SolOrders and type(SolOrders.board) == "function" then return SolOrders.board(v) end
        if U.extractPage then pcall(U.extractPage, "orders") end
        return U.issueLF("board_vehicle", { vehicle = v, seat = 1 })
    end }
-- ---------------------------------------------------------------- dispatch + catalog wrapping
function U.checkVerb(id, opt)
    local v = V[id]; local s = sol()
    if not v then return false, "unknown_verb" end
    if not s then return false, "no_sol" end
    local ok, chk, reason, ctx = pcall(v.check, s, player(), opt)
    if not ok then return false, "check_error:" .. tostring(chk) end
    return chk == true, tostring(reason or (chk and "ok" or "blocked")), ctx
end
local function runVerb(id, opt)
    local v = V[id]
    local s, p = sol(), player()
    if not s then return false, "no_sol" end
    local ok, chk, reason, ctx = pcall(v.check, s, p, opt)
    if not ok then return false, "check_error:" .. tostring(chk) end
    if not chk then return false, tostring(reason or "blocked") end
    local okr, r1, r2 = pcall(v.run, s, p, opt, ctx)
    if not okr then return false, "run_error:" .. tostring(r1) end
    return r1, r2
end
local function install()
    local baseRun, baseCat = U.runAction, U.actionCatalog
    if U._registryInstalled then return end
    U._registryInstalled = true
    U.runAction = function(id, option)
        if V[id] then return runVerb(id, option) end
        if U.planRun and U.planIds and U.planIds[id] then return U.planRun(id, option) end
        return baseRun(id, option)
    end
    U.actionCatalog = function()
        local out = baseCat()
        local s = sol()
        local names = {}
        for id in pairs(V) do names[#names + 1] = id end
        table.sort(names)
        for _, id in ipairs(names) do
            local e = { id = id, kind = "verb", label = V[id].label }
            if s then local ok, why = U.checkVerb(id, nil); e.enabled = ok; e.reason = why end
            out[#out + 1] = e
        end
        local have = {}
        for _, e in ipairs(out) do have[e.id] = e end
        if have.sol_drive then have.sol_drive.label = "start driving to the destination already selected on Sol GPS; she takes the driver seat first and waits for the player to board when nearby" end
        for _, x in ipairs({ { "board_vehicle", "get into the car as a passenger (any free seat)" }, { "exit_vehicle", "get out of the car" }, { "follow", "follow the player" }, { "stay", "stay here and wait" } }) do
            if not have[x[1]] then out[#out + 1] = { id = x[1], kind = "lf", label = x[2] } end
        end
        if U.planCatalog then for _, e in ipairs(U.planCatalog()) do out[#out + 1] = e end end
        return out
    end
    log("installed v" .. U.REGISTRY_VERSION .. " over SolActions v" .. tostring(U.ACTIONS_VERSION))
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(install) end
log("ready v" .. U.REGISTRY_VERSION)

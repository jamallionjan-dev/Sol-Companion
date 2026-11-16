-- SolAuthority.lua - one place that says who decides for Sol.
--   Living Fellows' follow logic copies the player's car state: when the player gets out, the companion gets out.
--   That is right for a passenger and wrong for a driver: Sol in the driver's seat (or told by Sol Mind / the order window to
--   stay in the car) keeps her seat until an explicit order says otherwise.
--   SCDecision asks SolAuthority.keepsSeat before its follow/exit policy moves her out of a car.
SolAuthority = SolAuthority or {}
local A = SolAuthority
A.VERSION = "0.3.0"

-- Per-fix switches, so each fix is tested alone in the Sol_LAB copy and then switched on in the main copy.
--   Sol_LAB carries media/lua/shared/SolLab.lua (SolLab = { active = true }); it reads ~/Zomboid/Lua/SolFixes_LAB.txt and a
--   missing file means every fix ON. The main copy reads ~/Zomboid/Lua/SolFixes_MAIN.txt and a missing file means every fix
--   OFF (Sol plays as before). One line per fix: name=on or name=off. The file is read again every 5 seconds.
A.FIXES = {
    "perf_hotspots",   -- s108: switch reads on the frame clock; her bag walked only when it changed; LF per-system ms/s every 15 s
    "sol_one_shot_kill", -- s118: lethal Sol firearm hits against zombies only
    "fierce_fast_react", -- s120: shorter aim-settle cap on urgent fierce targets
    "grounded_fire", -- s120: fierce firearm finisher for a nearby downed zombie
    "retreat_close_fire", -- s119: fierce cover-fire while retreating
    "sol_headshots", -- s113/s116: native Sol firearm part routing
    "shooting_discipline",   -- s104: aimed single shots, standing, inside the effective range; 5 per zombie; last magazine kept
    "task_scoped_perception", -- s112: one Sol scan lease; urgent LF perception remains independent
    "perf_slice",          -- s99: world scan, base inventory and action catalog work about 4 ms a frame
    "gear_page",   -- s107: her gear tab: hands, favourites, fighting plan, worn, her bag, his bag on click, car/home, like me
    "combat_plans",   -- s105: one plan name sets her fighting knobs; never across him, retreat under 30%, smart after death
    "item_stacks",   -- s100: identical stateless items are one entry with a count (500 rounds = one stack); LF walk keeps 240 distinct
    "melee_choice",   -- s99: melee by damage x condition and kind; her melee weapon (his pick, else katana) first
    "weapon_scan",   -- s99: LF's weapon list also takes weapons its 240-item walk missed
    "mag_fill",   -- s99: she fills magazines with loose rounds when safe; EFZ chamber counted; loaded magazines found past the scan cap
    "preferred_weapon",   -- s98: carry this weapon = her preferred weapon; she says why when she cannot use it
    "combat_equip_fallback",   -- s98: a refused equip is logged, blocked, expires; she fires the gun in her hands
    "decision_load_throttle", -- s110: ordinary decision cadence stretches to 150 ms under measured load; safety and fresh commands stay fast
    "shooting_damage_probe", -- s111: read-only before/after health probe for matched firearm hits
    "decision_load_throttle", -- s110: ordinary decision cadence stretches to 150 ms under measured load; safety and fresh commands stay fast
    "restore_hands",
    "heli_gps",              -- s121: direct-air GPS guidance and altitude targets for Sol's helicopter
    "heli_route_ownership", -- s148: keep GPS route and speed active across altitude changes
    "heli_voice_fly",        -- s144: let Sol Mind start flight to the already selected helicopter GPS marker
    "seat_handoff",           -- Let the player take over while Sol stays aboard
    "move_check",
    "smart_park",
    "exit_engine_off",
    "fail_reasons",          -- s88: "why" says the real reason; no code in her words
    "book_hint",     -- a paper he opened while she was far: she asks to see it when she is beside him
    "book_visited",     -- a stash row is marked visited by itself when she gets there
    "book_memory",     -- her address book, compact, in the world snapshot for the Mind's memory
    "exit_first",
    "address_places",     -- every paper or map with a place goes into her book, by kind; our home at the top
    "place_leg_arrive",
    "compat_vp_harvest",
    "speed_levels",
    "veh_shoot_seated",
    "preview_calm",
    "address_target",
    "stall_ladder",
    "horn_hold",
    "gps_static_roads",
    "gps_plain_words",
    "secret_loadout",
    "far_work",           -- far away, she keeps the farm from her saved place; supplies through a ledger
    "farm_night",
    "spatial_access",     -- doors first, a window only when no door will do, a fence last; access squares on the thing's side
    "address_book",       -- Sol's address book: listings, stash maps and area maps she saw him read
    "dot_paused_fix",
    "far_wait_speed",
    "item_sort",
    "far_car",            -- far away, she comes by the nearest usable car near her, not only hers
    "animal_care",
    "tracked_mode",
    "vehicle_steer_adapt",
    "bleed_get_out",
    "drive_replace", "home_parks",
    "refuel_top_up", "refuel_short_hop",
    "debug_ctrl_a_guard",
    "road_first",
    "sol_ladders", "ladder_fast_slide",
    "refuel_from_can", "car_eligible_only",
    "follow_exits_car",
    "order_engine_path",
    "drive_fast",
    "walk_search_fast", "order_jog", "walk_no_resend", "order_breaks_rest", "farm_keep_tools",
    "retry_reset",        -- 1 an explicit board order is never refused as retry_exhausted
    "driver_keeps_seat",  -- 2 Sol at the wheel (or told to wait in the car) stays in her seat when the player gets out
    "car_flow",           -- 3 taking the wheel / walking to a door is not undone by Living Fellows' follow logic
    "door_squares",       -- 4 door squares under the car's body are replaced by a free square next to them
    "instinct_only",      -- 5 Living Fellows keeps only her instincts; its own routines and world life are off
    "order_menu",         -- 6 the fixed orders in the order window (follow, wait, come, fight, flee, rescue, marker, home)
    "sol_home",           -- 7 "this is home": the store room she knows without a Living Fellows base
    "rescue_gps",         -- 8 the rescue return trip waits for the player and goes back to her own car
    "drive_passenger",    -- 9 she can drive while the player rides with her (driveStartWithPassenger)
    "home_errand",        -- 10 she drives alone to the base, empties the car with Living Fellows' unload job and comes back
    "road_bypass",        -- 11 a shut road is passed from where the car stands, off the tarmac for a few tiles if it must
    "java_nav",           -- the Java planner and path follower replace the Lua detour
    "refuel",             -- she remembers fuel pumps and fills a car or a can when told
    "solo_drive",         -- 12 she drives when told to, whether or not the player is in the car (a rescue return trip still waits for him)
    "gps_trails",         -- 13 the route planner also knows the dirt roads
    "order_arbiter",      -- 14 an order that meets a short action of hers waits for it instead of hammering it
    "sol_farm",           -- 15 her own order of work on the farm, and staying home to rest
}
local function isLab() return type(rawget(_G, "SolLab")) == "table" and SolLab.active == true end
A.lab = isLab
local switches, switchesAt, switchesLogged = nil, -1e12, nil
local function readSwitches()
    local t = {}
    local name = isLab() and "SolFixes_LAB.txt" or "SolFixes_MAIN.txt"
    local okR, r = pcall(function() return getFileReader and getFileReader(name, false) or nil end)
    if okR and r ~= nil then
        while true do
            local okL, line = pcall(function() return r:readLine() end)
            if not okL or line == nil then break end
            local k, v = tostring(line):match("^%s*([%w_]+)%s*=%s*(%a+)")
            if k then v = v:lower(); t[k] = (v == "on" or v == "true" or v == "1" or v == "yes") end
        end
        pcall(function() r:close() end)
    end
    return t, name
end
function A.on(fix)
    local now, hot_ = nil, switches ~= nil and A._tickNow ~= nil and (A._tickCalls or 0) < 4000 and switches.perf_hotspots   -- s108 perf_hotspots: the frame's clock
    if hot_ == nil then hot_ = isLab() end
    if hot_ == true then A._tickCalls = (A._tickCalls or 0) + 1; now = A._tickNow
    else now = (getTimestampMs and getTimestampMs()) or 0 end
    if switches == nil or now - switchesAt > 5000 then
        local t, file = readSwitches()
        switches, switchesAt = t, now
        local parts = {}
        for _, f in ipairs(A.FIXES) do parts[#parts + 1] = f .. "=" .. (t[f] == nil and (isLab() and "on" or "off") or (t[f] and "on" or "off")) end
        local line = table.concat(parts, " ")
        if line ~= switchesLogged then       -- log at boot and again whenever a switch changes
            switchesLogged = line
            print("[SolAuthority] " .. (isLab() and "LAB" or "MAIN") .. " switches (" .. file .. "): " .. line)
        end
    end
    local v = switches[fix]
    if v == nil then return isLab() end      -- lab: untested fixes on; main: off until switched on
    return v == true
end

local hold = nil -- { vehicle = <BaseVehicle or nil for "any">, reason = string, at = ms }

local function nowMs() return (getTimestampMs and getTimestampMs()) or 0 end
local function log(m) print("[SolAuthority] " .. tostring(m)) end

local function isDriver(actor)
    local SC = SurvivorCompanion
    local D = type(SC) == "table" and SC.Driving or nil
    if D and type(D.isDriver) == "function" then
        local ok, d = pcall(D.isDriver, actor)
        if ok then return d == true end
    end
    return false
end

-- an explicit order (Sol Mind or the order window): stay in this car until released
function A.holdVehicle(vehicle, reason)
    hold = { vehicle = vehicle, reason = tostring(reason or "sol_order"), at = nowMs() }
    log("hold vehicle reason=" .. hold.reason)
    return true
end

function A.releaseVehicle(reason)
    if hold ~= nil then log("release vehicle hold=" .. tostring(hold.reason) .. " by=" .. tostring(reason)) end
    hold = nil
    return true
end

function A.vehicleHold() return hold end

-- true when Sol must not be moved out of `vehicle` by Living Fellows' follow/exit policy
function A.keepsSeat(actor, vehicle)
    if actor == nil or vehicle == nil then return false, nil end
    if not A.on("driver_keeps_seat") then return false, nil end
    if type(SolUI) == "table" and type(SolUI.solActor) == "function" then
        local ok, s = pcall(SolUI.solActor)
        if ok and s ~= nil and s ~= actor then return false, nil end   -- only Sol, never another companion
    end
    if isDriver(actor) then return true, "sol_is_driver" end
    if hold ~= nil and (hold.vehicle == nil or hold.vehicle == vehicle) then return true, "sol_order_hold:" .. hold.reason end
    return false, nil
end

-- Living Fellows decision kinds Sol keeps: her instincts. Everything else (routines, idles, rituals, base work, scavenging,
-- barricading, fishing, social scenes, faction life, mental episodes) is Living Fellows deciding for her and is switched off.
A.instinctOnly = (A.instinctOnly ~= false)
A.INSTINCTS = A.INSTINCTS or {
    combat = true,        -- fight what threatens her or the player
    retreat = true,       -- flee when outmatched
    medical = true,       -- treat herself / the player when hurt
    follow = true,        -- stay with the player, copy walk/run/sneak
    tactical = true,      -- the player's own move / hold orders
    alert = true,         -- warn about threats
    companion_alert = true,
    needs = true,         -- eat / drink when the body needs it (survival)
}
A.dropped = A.dropped or {}
-- Work Living Fellows carries out only after an explicit order (sol_role: farmer, chef, woodcutter, angler, maintainer, ...).
A.WORK_KINDS = A.WORK_KINDS or {
    base_work = true, logistics = true, fishing = true, barricade = true, remove_barricade = true, dismantle = true, scavenge = true,
}
A.work = A.work or nil   -- { role = string, at = ms } while an ordered job runs
function A.grantWork(role, reason)
    A.work = { role = tostring(role or "work"), at = nowMs() }
    log("work granted role=" .. A.work.role .. " by=" .. tostring(reason))
end
function A.clearWork(reason)
    if A.work ~= nil then log("work cleared role=" .. A.work.role .. " by=" .. tostring(reason)) end
    A.work = nil
end
-- true while a standing order lets her wash, sleep and rest (SolFarmKeeper decides)
function A.restWanted(actor)
    local K = rawget(_G, "SolFarmKeeper")
    if type(K) ~= "table" or type(K.restWanted) ~= "function" then return false end
    local ok, wanted = pcall(K.restWanted, actor)
    return ok and wanted == true
end
-- true while she is working the farm: following him would pull her off it. Her own walks are Living Fellows' go_to (a "tactical" decision), so that one stays.
function A.farmHeld(actor)
    if type(SolUI) == "table" and type(SolUI.solSortHeld) == "function" then                   -- item_sort: same hold as farm work
        local okS, s = pcall(SolUI.solActor)
        local okH, h = pcall(SolUI.solSortHeld)
        if okH and h == true and (not okS or s == nil or s == actor) then return true end
    end
    if type(SolUI) == "table" and type(SolUI.solAnimalsHeld) == "function" then                 -- animal_care: same hold as farm work
        local okS, s = pcall(SolUI.solActor)
        local okH, h = pcall(SolUI.solAnimalsHeld)
        if okH and h == true and (not okS or s == nil or s == actor) then return true end
    end
    if type(SolUI) ~= "table" or type(SolUI.solFarmHeld) ~= "function" then return false end
    if type(SolUI.solActor) == "function" then
        local okA, s = pcall(SolUI.solActor)
        if okA and s ~= nil and s ~= actor then return false end
    end
    local ok, held = pcall(SolUI.solFarmHeld)
    return ok and held == true
end
function A.allowsDecision(actor, kind, detail)
    if tostring(kind) == "follow" and A.farmHeld(actor) then return false end
    -- on the farm her bag is full of what she is carrying on purpose: sorting it away takes her legs from the job (32 refused walks, 2026-11-09 09:14)
    if (tostring(kind) == "logistics" or tostring(kind) == "base_work" or (tostring(kind) == "downtime" and not A.restWanted(actor))) and A.farmHeld(actor) then return false end
    if A.instinctOnly ~= true or not A.on("instinct_only") then return true end
    if tostring(kind) == "downtime" and A.restWanted(actor) then
        local ok, s = true, nil
        if type(SolUI) == "table" and type(SolUI.solActor) == "function" then ok, s = pcall(SolUI.solActor) end
        if ok and (s == nil or s == actor) then return true end
    end
    if type(SolUI) == "table" and type(SolUI.solActor) == "function" then
        local ok, s = pcall(SolUI.solActor)
        if ok and s ~= nil and s ~= actor then return true end      -- other companions keep their own logic
    end
    if A.INSTINCTS[tostring(kind)] == true then return true end
    if A.work ~= nil and A.WORK_KINDS[tostring(kind)] == true then return true end   -- work the player / Sol Mind asked for
    local k = tostring(kind)
    local n = (A.dropped[k] or 0) + 1
    A.dropped[k] = n
    if n == 1 or n % 200 == 0 then log("dropped Living Fellows decision kind=" .. k .. " count=" .. n) end
    return false
end

-- Living Fellows scheduler tasks that run its own world life; SCRuntime.registerTasks leaves them out.
A.OFF_TASKS = A.OFF_TASKS or {
    ["factions"] = true, ["base-maintenance"] = true, ["infection-crisis"] = true, ["community"] = true,
    ["banter"] = true, ["companion-gifts"] = true, ["gestures"] = true, ["diary"] = true,
}

-- true while one of Sol's own car orders is under way (taking the wheel, walking to a door, a SolOrders job): Living Fellows'
-- follow logic must not board her into the player's passenger seat or pull her out in the middle of it.
-- (2026-11-07 log: "take the wheel" -> she got out of the passenger seat -> LF follow boarded her straight back as passenger.)
-- Sol fix: the player told her to get out while he sits in the car. Without this, the follow logic boards her again in the same
-- breath. She stays out until he gives a car order, or until he leaves the car himself.
local orderedOut = nil
function A.holdOut(reason)
    orderedOut = tostring(reason or "order")
    log("ordered out of the car: stays out (" .. orderedOut .. ")")
end
function A.clearHoldOut(reason)
    if orderedOut ~= nil then log("ordered-out hold ended by " .. tostring(reason)) end
    orderedOut = nil
end
function A.heldOut(actor, player)
    if orderedOut == nil then return false, nil end
    if type(SolUI) == "table" and type(SolUI.solActor) == "function" then
        local ok, s = pcall(SolUI.solActor)
        if ok and s ~= nil and s ~= actor then return false, nil end
    end
    local okV, playerCar = pcall(function() return player:getVehicle() end)
    if okV and playerCar == nil then A.clearHoldOut("player_left_the_car"); return false, nil end
    return true, "sol_ordered_out:" .. orderedOut
end

function A.ownsCarFlow(actor)
    if not A.on("car_flow") then return false, nil end
    if type(SolUI) == "table" and type(SolUI.solActor) == "function" then
        local ok, s = pcall(SolUI.solActor)
        if ok and s ~= nil and s ~= actor then return false, nil end
    end
    local g = type(SolUI) == "table" and type(SolUI.gps) == "table" and SolUI.gps or nil
    if g ~= nil then
        if g.wheelWaitSince ~= nil then return true, "sol_taking_wheel" end
        if g.doorWalk ~= nil then return true, "sol_walking_to_door" end
    end
    if type(SolUI) == "table" and type(SolUI.solFuelHeld) == "function" then
        local ok, held = pcall(SolUI.solFuelHeld)
        if ok and held == true then return true, "sol_fuel_errand" end
    end
    if A.farmHeld(actor) then return true, "sol_farm_work" end
    if type(SolOrders) == "table" and type(SolOrders.busy) == "function" then
        local ok, b = pcall(SolOrders.busy)
        if ok and b then return true, "sol_order_job:" .. tostring(b) end
    end
    return false, nil
end

-- A door-side square the walk order will accept. Living Fellows' boardingSquares can return squares under the car's own body
-- (getVehicleContainer), which move_to refuses with invalid_destination (2026-11-07 log: every door square refused, so boarding
-- burned its tries without a step). Keep the square when it is free, else the nearest free neighbour of it.
function A.walkableNear(square)
    local SC = SurvivorCompanion
    local GU = type(SC) == "table" and SC.GameplayUtil or nil
    if not A.on("door_squares") then return square end
    if square == nil or type(GU) ~= "table" or type(GU.isSquareFree) ~= "function" then return square end
    local okF, free = pcall(GU.isSquareFree, square)
    if okF and free == true then return square end
    local cell = getCell and getCell() or nil
    if cell == nil then return square end
    local x, y, z = square:getX(), square:getY(), square:getZ()
    for r = 1, 1 do   -- one ring only: boarding needs her within ~1.6 tiles of the door (vehicleBoardRangeSquared)
        local best, bd = nil, nil
        for dx = -r, r do
            for dy = -r, r do
                if math.max(math.abs(dx), math.abs(dy)) == r then
                    local q = cell:getGridSquare(x + dx, y + dy, z)
                    if q ~= nil then
                        local okQ, fq = pcall(GU.isSquareFree, q)
                        local d = dx * dx + dy * dy
                        if okQ and fq == true and (bd == nil or d < bd) then best, bd = q, d end
                    end
                end
            end
        end
        if best ~= nil then return best end
    end
    return square
end

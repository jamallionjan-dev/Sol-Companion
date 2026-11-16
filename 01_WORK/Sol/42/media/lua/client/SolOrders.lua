-- SolOrders.lua - Sol's practical orders in the right-click menu (replaces the "Squad commands" submenu, which means nothing with one companion).
--   board in the front passenger seat, take the driver seat, stage home on GPS, get out, stop. GPS alone starts a UI-planned trip.
--   Every order that needs the car is ONE job with ONE owner:
--     - it starts from a clean slate (the GPS's door/wheel bookkeeping from earlier orders is cleared, so an old counter can no longer refuse a new order),
--     - it is followed until it is really done or really failed, and Sol says what happened: she is "in the driver's seat" only when she is the driver
--       (Living Fellows' own isDriver), "in" only when she is in a vehicle, "out" only when she is out - never because an order was merely sent,
--     - every failure says why (the game's own reason is shown when it is not one we know).
--   The log also records who sends her walking orders and Living Fellows commands, so a source of constant interruptions can be named.
require "SolLF_AR"
SolUI = SolUI or {}
SolOrders = SolOrders or {}
local O = SolOrders
O.VERSION = "0.10.0"
local U = SolUI
local SolScanCoordinator = require "SolScanCoordinator"
-- Levantine colloquial, Sol speaks as a woman and is spoken to as one
local AR = {
    header = "\\u0623\\u0648\\u0627\\u0645\\u0631 \\u0633\\u0648\\u0644",
    board = "\\u0627\\u0631\\u0643\\u0628\\u064A \\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629",
    board_selected = "\\u0627\\u0631\\u0643\\u0628\\u064A \\u0647\\u064A \\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629",
    wheel = "\\u0633\\u0648\\u0642\\u064A \\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629",
    home = "\\u062C\\u0647\\u0651\\u0632\\u064A GPS \\u0644\\u0644\\u0628\\u064A\\u062A",
    home_destination_ready = "\\u062D\\u062F\\u0651\\u062F\\u062A \\u0627\\u0644\\u0628\\u064A\\u062A \\u0639\\u0644\\u0649 GPS\\u060C \\u0627\\u0636\\u063A\\u0637\\u064A \\u0633\\u0648\\u0642\\u064A \\u0645\\u0646 \\u0634\\u0627\\u0634\\u0629 GPS.",
    exit = "\\u0627\\u0646\\u0632\\u0644\\u064A \\u0645\\u0646 \\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629",
    stop = "\\u0648\\u0642\\u0641\\u064A",
    boarding = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0631\\u0627\\u064A\\u062D\\u0629 \\u0639\\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629.",
    boarding_passenger = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0631\\u062D \\u0627\\u0631\\u0643\\u0628 \\u0645\\u0639\\u0643.",
    moving_to_wheel = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0631\\u0627\\u064A\\u062D\\u0629 \\u0639\\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629.",
    walking_to_door = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0631\\u0627\\u064A\\u062D\\u0629 \\u0639\\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629.",
    no_vehicle_near = "\\u0645\\u0627 \\u0641\\u064A \\u0633\\u064A\\u0627\\u0631\\u0629 \\u0642\\u0631\\u064A\\u0628\\u0629.",
    no_destination = "\\u062D\\u062F\\u062F \\u0648\\u062C\\u0647\\u0629 \\u0639\\u0644\\u0649 GPS \\u0623\\u0648\\u0644\\u0627\\u064B.",
    player_not_in_vehicle = "\\u0627\\u0631\\u0643\\u0628 \\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629 \\u0623\\u0648\\u0644\\u0627\\u064B\\u060C \\u0648\\u0628\\u0631\\u0643\\u0628 \\u062C\\u0646\\u0628\\u0643.",
    player_is_driver = "\\u0625\\u0646\\u062A \\u0633\\u0627\\u064A\\u0642\\u060C \\u0645\\u0627 \\u0641\\u064A\\u0646\\u064A \\u0622\\u062E\\u062F \\u0627\\u0644\\u0645\\u0642\\u0648\\u062F.",
    driving_unavailable = "\\u0645\\u0627 \\u0641\\u064A\\u0646\\u064A \\u0633\\u0648\\u0642 \\u0647\\u0644\\u0623.",
    driving = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0631\\u0627\\u064A\\u062D\\u0629.",
    no_home = "\\u0645\\u0627 \\u0641\\u064A \\u0628\\u064A\\u062A \\u0645\\u062D\\u062F\\u062F \\u0644\\u0633\\u0627.",
    exiting = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0639\\u0645 \\u0646\\u0632\\u0644.",
    stopped = "\\u0648\\u0642\\u0641\\u062A.",
    generic = "\\u0645\\u0627 \\u0642\\u062F\\u0631\\u062A \\u0623\\u0639\\u0645\\u0644 \\u0647\\u0627\\u0644\\u0634\\u064A \\u0647\\u0644\\u0623",
    no_square = "\\u0645\\u0627 \\u0639\\u0631\\u0641\\u062A \\u0648\\u064A\\u0646 \\u062A\\u0642\\u0635\\u062F.",
    now_out = "\\u0646\\u0632\\u0644\\u062A.",
    already_out = "\\u0623\\u0646\\u0627 \\u0628\\u0631\\u0627 \\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629 \\u0623\\u0635\\u0644\\u0627\\u064B.",
    still_in = "\\u0644\\u0633\\u0627 \\u0628\\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629\\u060C \\u0645\\u0627 \\u0642\\u062F\\u0631\\u062A \\u0623\\u0646\\u0632\\u0644.",
    board_ok = "\\u0631\\u0643\\u0628\\u062A.",
    already_in_other_vehicle = "\\u0623\\u0646\\u0627 \\u0631\\u0627\\u0643\\u0628\\u0629 \\u0628\\u0633\\u064A\\u0627\\u0631\\u0629 \\u062B\\u0627\\u0646\\u064A\\u0629.",
    wheel_ok = "\\u0631\\u0643\\u0628\\u062A \\u0648\\u0645\\u0627\\u0633\\u0643\\u0629 \\u0627\\u0644\\u0645\\u0642\\u0648\\u062F.",
    board_timeout = "\\u0645\\u0627 \\u0642\\u062F\\u0631\\u062A \\u0623\\u0631\\u0643\\u0628.",
    wheel_timeout = "\\u0645\\u0627 \\u0642\\u062F\\u0631\\u062A \\u0623\\u0648\\u0635\\u0644 \\u0644\\u0644\\u0645\\u0642\\u0639\\u062F.",
    no_row = "\\u0645\\u0627 \\u0642\\u062F\\u0631\\u062A \\u0623\\u0648\\u0635\\u0644 \\u0644\\u0623\\u0648\\u0627\\u0645\\u0631\\u064A.",
    unavailable_exit = "\\u0645\\u0627 \\u0628\\u0642\\u062F\\u0631 \\u0623\\u0646\\u0632\\u0644 \\u0647\\u0644\\u0623. \\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629 \\u0645\\u0627\\u0634\\u064A\\u0629\\u061F",
    unavailable_board = "\\u0645\\u0627 \\u0641\\u064A \\u0645\\u0642\\u0639\\u062F \\u0641\\u0627\\u0636\\u064A \\u0623\\u0631\\u0643\\u0628 \\u0641\\u064A\\u0647 \\u0647\\u0644\\u0623.",
    door_far = "\\u0644\\u0633\\u0627 \\u0645\\u0627 \\u0648\\u0635\\u0644\\u062A \\u0644\\u0628\\u0627\\u0628 \\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629.",
    door_unreachable = "\\u0645\\u0627 \\u0642\\u062F\\u0631\\u062A \\u0623\\u0648\\u0635\\u0644 \\u0644\\u0628\\u0627\\u0628 \\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629.",
    no_wheel = "\\u0645\\u0627 \\u0642\\u062F\\u0631\\u062A \\u0623\\u0645\\u0633\\u0643 \\u0627\\u0644\\u0645\\u0642\\u0648\\u062F.",
    no_path = "\\u0645\\u0627 \\u0644\\u0642\\u064A\\u062A \\u0637\\u0631\\u064A\\u0642 \\u0644\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629.",
    forget = "\\u062E\\u0644\\u0651\\u0635\\u060C \\u0627\\u0646\\u0633\\u064A \\u0643\\u0644 \\u0634\\u064A",
    forgot = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0646\\u0633\\u064A\\u062A \\u0643\\u0644 \\u0634\\u064A \\u0648\\u0631\\u062C\\u0639\\u062A \\u0623\\u062A\\u0628\\u0639\\u0643.",
    busy = "\\u0623\\u0646\\u0627 \\u0645\\u0634\\u063A\\u0648\\u0644\\u0629 \\u0628\\u0634\\u064A \\u062A\\u0627\\u0646\\u064A \\u0647\\u0644\\u0623.",
    threat = "\\u0641\\u064A \\u0632\\u0648\\u0645\\u0628\\u064A \\u0642\\u0631\\u064A\\u0628\\u060C \\u0644\\u0627\\u0632\\u0645 \\u0646\\u062E\\u0644\\u0651\\u0635 \\u0645\\u0646\\u0647 \\u0623\\u0648\\u0644.",
    no_seat = "\\u0645\\u0627 \\u0641\\u064A \\u0645\\u0642\\u0639\\u062F \\u0641\\u0627\\u0636\\u064A \\u0623\\u0631\\u0643\\u0628 \\u0641\\u064A\\u0647 \\u0647\\u0644\\u0623.",
    front_seat_unavailable = "\\u0645\\u0627 \\u0641\\u064A\\u0646\\u064A \\u0623\\u062D\\u062F\\u0651\\u062F \\u0627\\u0644\\u0645\\u0642\\u0639\\u062F \\u0627\\u0644\\u0644\\u064A \\u062C\\u0646\\u0628 \\u0627\\u0644\\u0633\\u0627\\u064A\\u0642 \\u0647\\u0644\\u0623.",
    stranger = "\\u0641\\u064A \\u062D\\u062F\\u0627 \\u0628\\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629 \\u063A\\u064A\\u0631\\u064A.",
    door_locked = "\\u0628\\u0627\\u0628 \\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629 \\u0645\\u0642\\u0641\\u0648\\u0644.",
    cmd_set_home = "\\u0647\\u0648\\u0646 \\u0627\\u0644\\u0628\\u064A\\u062A",
    home_set = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0647\\u0648\\u0646 \\u0628\\u064A\\u062A\\u0646\\u0627. \\u0631\\u062D \\u0627\\u062A\\u0630\\u0643\\u0631 \\u0634\\u0648 \\u0641\\u064A \\u0628\\u0627\\u0644\\u0645\\u062E\\u0632\\u0646.",
    cmd_follow = "\\u0627\\u062A\\u0628\\u0639\\u064A\\u0646\\u064A",
    cmd_stay = "\\u0627\\u0646\\u062A\\u0638\\u0631\\u064A \\u0647\\u0648\\u0646",
    cmd_come = "\\u062A\\u0639\\u0627\\u0644\\u064A \\u0644\\u0639\\u0646\\u062F\\u064A",
    cmd_cautious = "\\u0627\\u0645\\u0634\\u064A \\u0648\\u0631\\u0627\\u064A\\u064A \\u0628\\u062D\\u0630\\u0631",
    cmd_fire = "\\u0642\\u0627\\u062A\\u0644\\u064A",
    cmd_hold_fire = "\\u0644\\u0627 \\u062A\\u0642\\u0627\\u062A\\u0644\\u064A",
    cmd_retreat = "\\u0627\\u0647\\u0631\\u0628\\u064A",
    cmd_rescue = "\\u062A\\u0639\\u0627\\u0644\\u064A \\u0627\\u0646\\u0642\\u0630\\u064A\\u0646\\u064A",
    cmd_drive_marker = "\\u0633\\u0648\\u0642\\u064A \\u0644\\u0644\\u0639\\u0644\\u0627\\u0645\\u0629 \\u0639\\u0644\\u0649 \\u0627\\u0644\\u062E\\u0631\\u064A\\u0637\\u0629",
    ok_follow = "\\u0645\\u0627\\u0634\\u064A\\u0629 \\u0648\\u0631\\u0627\\u0643.",
    ok_stay = "\\u0631\\u062D \\u0627\\u0633\\u062A\\u0646\\u0627\\u0643 \\u0647\\u0648\\u0646.",
    ok_come = "\\u062C\\u0627\\u064A\\u0629.",
    ok_fire = "\\u062A\\u0645\\u0627\\u0645\\u060C \\u0628\\u0642\\u0627\\u062A\\u0644.",
    ok_hold = "\\u0645\\u0627 \\u0631\\u062D \\u0627\\u0637\\u0644\\u0642.",
    ok_retreat = "\\u0639\\u0645 \\u0628\\u0646\\u0633\\u062D\\u0628!",
    rescue_sent = "\\u0648\\u0635\\u0644\\u062A\\u0646\\u064A\\u060C \\u062C\\u0627\\u064A\\u0629!",
    rescue_no_mind = "\\u0633\\u0648\\u0644 \\u0645\\u0627\\u064A\\u0646\\u062F \\u0645\\u0634 \\u0634\\u063A\\u0627\\u0644\\u060C \\u0645\\u0627 \\u0628\\u0642\\u062F\\u0631 \\u0627\\u0639\\u0645\\u0644 \\u0627\\u0644\\u0645\\u0647\\u0645\\u0629 \\u0647\\u0644\\u0623.",
    rescue_text = "\\u0627\\u0646\\u0642\\u0630\\u064A\\u0646\\u064A \\u0627\\u0646\\u0627 \\u0645\\u062D\\u0627\\u0635\\u0631 \\u0628\\u0627\\u0644\\u0632\\u0648\\u0645\\u0628\\u064A",
}
O.AR = AR
if type(SolLF_AR) == "table" then SolLF_AR["UI_SC_Context_SolOrders"] = AR.header end
local function log(m) print("[SolOrders] " .. tostring(m)) end
local function nowMs() return (getTimestampMs and getTimestampMs()) or 0 end

local function sol() return type(U.solActor) == "function" and U.solActor() or nil end
local function say(line)
    local s = sol()
    if s and SolBubble and type(SolBubble.speak) == "function" then SolBubble.speak(s, line, 4500) end
end
local function G() return type(U.gps) == "table" and U.gps or nil end
local function drivingApi() local SC = SurvivorCompanion; return type(SC) == "table" and type(SC.Driving) == "table" and SC.Driving or nil end

-- where she is: "driver", "passenger" or "out" (nil when there is no Sol)
local function seat()
    local s = sol()
    if not s then return nil end
    local inside = type(s.getVehicle) == "function" and s:getVehicle() or nil
    if inside == nil then return "out" end
    local D = drivingApi()
    if D and type(D.isDriver) == "function" then
        local ok, d = pcall(D.isDriver, s)
        if ok and d == true then return "driver" end
    end
    return "passenger"
end

-- zombies near Sol: while she is in a fight Living Fellows' combat layer owns her movement ("combat-engage", "safety-hold"): a walking order does nothing
-- and only interrupts the fight, so the jobs wait (their time budget paused) and say why
function O.threatNear(radius)
    radius = radius or 6
    if type(getCell) ~= "function" then return 0, nil end
    local me = sol()
    local sx, sy
    if me ~= nil and type(me.getX) == "function" then sx, sy = tonumber((me:getX())), tonumber((me:getY())) end
    if not sx then return 0, nil end
    local okc, cell = pcall(getCell)
    if not okc or cell == nil or type(cell.getZombieList) ~= "function" then return 0, nil end
    local okl, list = pcall(cell.getZombieList, cell)
    if not okl or list == nil or type(list.size) ~= "function" or type(list.get) ~= "function" then return 0, nil end
    local count, nearest = 0, nil
    for i = 0, list:size() - 1 do
        local z = list:get(i)
        if z ~= nil and type(z.getX) == "function" and not (type(z.isDead) == "function" and z:isDead()) then
            local d = math.sqrt((tonumber((z:getX())) - sx) ^ 2 + (tonumber((z:getY())) - sy) ^ 2)
            if d <= radius then count = count + 1; if not nearest or d < nearest then nearest = d end end
        end
    end
    return count, nearest
end
local function sayThreatOnce(j)
    local t = nowMs()
    if t - (j.saidThreat or -100000) > 12000 then j.saidThreat = t; say(AR.threat) end
end

-- a new order starts clean: the door/wheel bookkeeping of earlier orders (a counter that was never reset refused every later order) is cleared
local function freshFlow()
    local g = G()
    if not g then return end
    g.doorTries, g.doorTriesAt, g.doorWalk, g.wheelWaitSince, g.retryWhenOut, g.awaitPlayer, g.wheelCar = 0, nil, nil, nil, false, false, nil
    g.doorWalkFrom, g.doorRetryAt, g.leaveSeatCount = nil, nil, 0       -- a new order from the player starts with a clean slate
    if type(SolAuthority) == "table" and type(SolAuthority.clearHoldOut) == "function" then SolAuthority.clearHoldOut("new_car_order") end
end

-- the sentence for a failure: what we know, and the game's own reason in brackets when we do not
local KNOWN = {
    ["companion is not at the passenger door"] = "door_far", ["could_not_reach_door"] = "door_unreachable", ["cannot_take_wheel"] = "no_wheel",
    ["passenger door is locked"] = "door_locked", ["requested vehicle seat is unavailable"] = "no_seat", ["vehicle has no bounded passenger seat"] = "no_seat", ["someone who is not a companion is in this vehicle"] = "stranger", ["no_vehicle_near"] = "no_vehicle_near", ["player_is_driver"] = "player_is_driver",
    ["driving_unavailable"] = "driving_unavailable", ["no_row"] = "no_row",
}
local TRANSIT = { walking_to_door = true, moving_to_wheel = true, board_passenger = true, await_destination = true, ready = true }
local function failText(reason, context)
    do local FN88 = rawget(_G, "SolFailNote"); if type(FN88) == "table" and type(FN88.note) == "function" then pcall(FN88.note, "order_" .. tostring(context), reason, "") end end   -- Sol s88: the code, in the log and for "why"
    if type(reason) == "string" and (reason:find("stationary", 1, true) or reason:find("moving", 1, true)) then return AR.unavailable_exit end
    if reason == "unavailable" and context == "exit" then return AR.unavailable_exit end
    if reason == "unavailable" and context == "board" then return AR.unavailable_board end
    local k = KNOWN[tostring(reason)]
    if k then return AR[k] end
    if type(reason) == "string" and reason ~= "" then log("refused: " .. reason); return AR.generic end
    return AR.generic
end

-- Living Fellows' commands need the companion's row; SolGPS prepares it before every command, so does this
local function lf(command)
    if type(U.issueLF) ~= "function" then return false, "no_issueLF" end
    if type(U.extractPage) == "function" then pcall(U.extractPage, "orders") end
    O._own = true                                   -- our own order: the observer below must not take it for the player's
    local ok, a, b = pcall(U.issueLF, command)
    O._own = false
    if not ok then return false, "error" end
    log(command .. " -> " .. tostring(a) .. (b and (" " .. tostring(b)) or ""))
    return a == true, b
end

-- the job being followed
local job = nil
function O.busy() return job ~= nil and tostring(job.kind) or nil end   -- read by SolAuthority.ownsCarFlow
local stepBoard
local function follow(kind, ms) job = { kind = kind, since = nowMs(), deadline = nowMs() + ms } end
-- SolGPS keeps its own door / wheel bookkeeping; a job that ends or is replaced must leave none of it behind (the destination only when asked)
local function releaseGps(clearDest)
    local g = G()
    if g then
        g.doorTries, g.doorTriesAt, g.doorWalk, g.wheelWaitSince, g.retryWhenOut, g.awaitPlayer, g.wheelCar = 0, nil, nil, nil, false, false, nil
        if clearDest then g.dest = nil end
    end
end
-- the player's orders win: any Living Fellows order that does NOT come from this module (the Orders page, the menu, the chat) ends the job that is running
-- (the job re-sent its walking order every few seconds and wrote over whatever the player had just ordered). "stay" is excluded: Living Fellows itself issues it when a move order arrives.
local USER_ORDERS = { follow = true, guard = true, regroup = true, retreat = true, cautious_follow = true, move_to = true, board_vehicle = true, exit_vehicle = true }
local MOVEMENT_VERBS = { board_vehicle = true, exit_vehicle = true, sol_take_wheel = true, sol_sit_beside = true, sol_goto = true, sol_go_inside = true, sol_drive = true,
    sol_let_player_drive = true,
    sol_pilot_helicopter = true,
    follow = true, stay = true, guard = true, regroup = true, retreat = true, cautious_follow = true, sol_fetch = true }
local function onTick()
    if not job then return end
    local t = nowMs()
    if t - (job.polled or 0) < 1000 then return end
    job.polled = t
    local st = seat()
    local g = G() or {}
    if job.kind == "wheel" then
        if st == "driver" then job = nil; return say(AR.wheel_ok) end
        if O.threatNear(6) > 0 then job.deadline = job.deadline + 1000; return sayThreatOnce(job) end
        local reason = g.reason
        if g.lastResult == "failed" and reason and not TRANSIT[reason] and t - job.since > 3000 then job = nil; return say(failText(reason, "wheel")) end
        if t >= job.deadline then job = nil; return say(AR.wheel_timeout) end
    elseif job.kind == "boardlf" then
        if st == "passenger" or st == "driver" then job = nil; return say(AR.board_ok) end
        if t >= job.deadline then job = nil; return say(AR.board_timeout) end
    elseif job.kind == "ride" then
        stepBoard(t)
    elseif job.kind == "exit" then
        if st == "out" then
            job = nil
            say(AR.now_out)
            -- she is out: the routine is Living Fellows' again. Its move orders leave her on "stay" when they arrive, and nothing brings her back to following; an order given
            -- while she drives would stop the drive, so this is done only here, after getting out.
            local okf = lf("follow")
            log("back to following after getting out -> " .. tostring(okf))
            return
        end
        if t >= job.deadline then job = nil; return say(AR.still_in) end
    end
end
O._tick = onTick

local function homePoint()
    local h = type(SolHome) == "table" and type(SolHome.get) == "function" and SolHome.get() or nil   -- Sol's own home ("this is home"): what he named comes first
    if h then return h.x, h.y end
    local SC = SurvivorCompanion
    local base = SC and SC.BaseLife and type(SC.BaseLife.active) == "function" and SC.BaseLife.active() or nil
    local core = type(base) == "table" and base.core or nil
    if type(core) == "table" and type(core.x) == "number" and type(core.y) == "number" then return core.x, core.y end
    return nil
end

-- "take the wheel": a clean start, then SolGPS's own door-and-wheel machine, followed until she is the driver
function O.takeWheel()
    if type(U.gpsTakeWheel) ~= "function" then return say(AR.driving_unavailable) end
    if seat() == "driver" then return say(AR.wheel_ok) end
    freshFlow()
    local ok, reason = U.gpsTakeWheel()
    log("take the wheel -> " .. tostring(ok) .. " " .. tostring(reason))
    if not ok then return say(failText(reason, "wheel")) end
    if seat() == "driver" or reason == "board_passenger" or reason == "await_destination" then return say(AR.wheel_ok) end
    say(AR.moving_to_wheel); follow("wheel", 90000)
end
-- Start the route already selected on Sol's GPS. Selecting a point only stages
-- it; this action is the explicit command that hands the route to SC.Driving.
function O.driveDestination()
    if type(U.gpsStart) ~= "function" then say(AR.driving_unavailable); return false, "gps_unavailable" end
    local g = G()
    if not g or not g.dest then say(AR.no_destination); return false, "no_destination" end
    freshFlow()
    local ok, reason = U.gpsStart(nil, false)
    log("drive selected destination -> " .. tostring(ok) .. " " .. tostring(reason))
    if not ok then say(failText(reason, "wheel")); return false, reason end
    if reason == "moving_to_wheel" or reason == "walking_to_door" then
        say(AR.moving_to_wheel)
        follow("wheel", 90000)
    elseif reason == "board_passenger" then
        say(AR.boarding_passenger)
    else
        say(AR.driving)
    end
    return true, reason or "driving"
end
-- ---------------------------------------------------------------- getting in, on Sol's own machine (Living Fellows' board_vehicle order is a closed box that
-- answers only "board_vehicle_rejected"): walk to a free square beside the door, ask Living Fellows' own board function (it answers with a reason), repeat.
local function vehApi()
    local SC = SurvivorCompanion
    local v = type(SC) == "table" and SC.Vehicle or nil
    if type(v) == "table" and type(v.board) == "function" then return v end
    return nil
end
local function xy(o)
    if (type(o) ~= "table" and type(o) ~= "userdata") or type(o.getX) ~= "function" then return nil, nil end
    return tonumber((o:getX())), tonumber((o:getY()))
end
local function playerVehicle()
    local p = getSpecificPlayer and getSpecificPlayer(0)
    return p and type(p.getVehicle) == "function" and p:getVehicle() or nil
end
-- a square beside the door that the player's body is not on (the first one may be where he stands); a later try takes the next one
local function pickSquare(sqs, tries)
    if type(sqs) ~= "table" then return nil end
    local px, py = xy(getSpecificPlayer and getSpecificPlayer(0))
    local free = {}
    for i = 1, #sqs do
        local sq = sqs[i]
        if type(SolAuthority) == "table" and type(SolAuthority.walkableNear) == "function" then
            local okW, w = pcall(SolAuthority.walkableNear, sq); if okW and w ~= nil then sq = w end   -- not a square under the car's body
        end
        local qx, qy = xy(sq)
        if qx then
            if not (px and (qx + 0.5 - px) ^ 2 + (qy + 0.5 - py) ^ 2 < 1.69) then
                free[#free + 1] = { qx + 0.5, qy + 0.5, sq }
            end
        end
    end
    -- The player standing at the door is a real navigation obstacle. Do not
    -- fall back to a tile occupied by their body; choose another door-side
    -- tile so pathfinding can pass around them.
    local list = free
    if #list == 0 then return nil end
    local q = list[(tries % #list) + 1]
    return q[1], q[2], q[3]
end
-- WHY THE WALK IS A move_to ORDER (found in the field log of 2026-10-26): Navigation.request is a state machine that the OWNER of the movement must call again every cycle until
-- she arrives (Living Fellows' decision layer does exactly that for the order "move_to": it calls Navigation.request each update and checks navigationArrived). A single call only
-- answers "path_searching" and then nothing moves. So the walk is given as the order the brain already carries out each cycle, and a reservation token is NOT held meanwhile
-- (it would make the brain's own movement requests fail with "action_owned"). The token code below stays for jobs that call Navigation every cycle themselves: O.useToken = true.
O.useToken = false
-- ---------------------------------------------------------------- Sol's own reservation of her movement
-- Living Fellows' action supervisor decides who owns the actor: an action with a higher priority replaces a lower one, a lower or equal one is refused with
-- "actor_owned_by:<owner>:<action>", and a movement request that does not carry the owner's token is refused ("action_owned"). A token with PLAYER priority (400)
-- is what Living Fellows itself gives an order of the player's: the following, working and needs layers (<= 300) cannot cut it, combat and survival (>= 500) still can.
-- The token covers only the walk to the door: the boarding itself starts its own transaction (a second token of the same priority is refused), so the token is
-- given back first. Every way out of the job gives it back; its 60 s deadline is only the net under that.
local function sup()
    local SC = SurvivorCompanion
    local S = type(SC) == "table" and SC.ActionSupervisor or nil
    if type(S) == "table" and type(S.begin) == "function" and type(S.complete) == "function" and type(S.isCurrent) == "function" and type(S.Priority) == "table" then return S end
    return nil
end
local function playerIntent() return { playerCommand = true, immediateCommand = true } end   -- a fresh table each time: the callee writes into it
local function beginToken(j)
    local S, me = sup(), sol()
    if not S or not me then return nil, "no_supervisor" end
    if j.token and S.isCurrent(j.token) then return j.token end
    local ok, tok, why = pcall(S.begin, me, {
        owner = "player_control", action = "sol_" .. tostring(j.kind), priority = S.Priority.PLAYER or 400,
        targetKey = "sol:" .. tostring(j.kind), targetLabel = "Sol order", phase = "approaching", ignoreRetry = true,
        deadlines = { approaching = 60000, waiting = 60000 }, allowedActions = { sol_walk = true },
        onCancel = function() j.preempted = true end,
    })
    if not ok then return nil, "error" end
    if tok then j.token = tok; return tok end
    return nil, tostring(why)
end
local function endToken(j, reason)
    local S = sup()
    if S and j and j.token then
        if S.isCurrent(j.token) then pcall(S.complete, j.token, reason or "sol_done") end
        j.token = nil
    end
end
local function busyText(why)
    local A88 = rawget(_G, "SolAuthority")
    if type(A88) == "table" and type(A88.on) == "function" and A88.on("fail_reasons") == true then log("busy: " .. tostring(why)); return AR.busy end   -- Sol fix fail_reasons: the code goes to the log, never into her words
    return AR.busy .. " (" .. tostring(why) .. ")"
end
-- walk to a free square beside the door, carrying the token when there is one (the answer says why when it refuses), else by the old order
local function startWalk(j, sqs, t)
    local me = sol()
    local S = O.useToken and sup() or nil
    local nav = SurvivorCompanion and SurvivorCompanion.Navigation
    local n = type(sqs) == "table" and #sqs or 0
    for _ = 1, math.max(1, n) do
        local x, y, obj = pickSquare(sqs, j.tries)
        if not x then return false end
        local leg = nil
        local SP = rawget(_G, "SolPlace")
        if type(SP) == "table" and type(SP.on) == "function" and SP.on() and type(SP.nextLeg) == "function" then      -- spatial_access: the door first
            local okL, lx, ly = pcall(SP.nextLeg, x, y)
            if okL and lx ~= nil then
                local cellF = rawget(_G, "getCell")
                local lsq = cellF and cellF():getGridSquare(lx, ly, math.floor(me:getZ())) or nil
                if lsq ~= nil then leg = { x = x, y = y }; x, y, obj = lx, ly, lsq end
            end
        end
        local accepted, why
        if S and j.token and obj ~= nil and type(nav) == "table" and type(nav.request) == "function" then
            local ok, a, b = pcall(nav.request, me, obj, "walk", { action = "sol_walk", targetSquare = obj, supervisorToken = j.token })
            accepted, why = ok and a or false, ok and b or "error"
        elseif type(U.solGoto) == "function" then
            local SC = SurvivorCompanion
            if SC and SC.Decision and type(SC.Decision.cancelWork) == "function" then pcall(SC.Decision.cancelWork, me, "sol_orders") end
            accepted, why = U.solGoto(x, y)
        else
            return false
        end
        log("walk to " .. tostring(x) .. "," .. tostring(y) .. " -> " .. tostring(accepted) .. " " .. tostring(why))
        if accepted == true or (accepted and accepted ~= false) then j.walk = { x = x, y = y, askedAt = t, bestAt = t, leg = leg }; return true end
        j.tries = j.tries + 1                                            -- refused: the next square
    end
    return false
end
-- a job that fails: she says why, gives everything back and returns to following (a leftover "move_to" would otherwise stay her order for good)
local function endFail(text)
    do local FN88 = rawget(_G, "SolFailNote"); if type(FN88) == "table" and type(FN88.orderEnd) == "function" then pcall(FN88.orderEnd, text, job) end end   -- Sol s88: the reason and how long / how often she tried
    endToken(job)
    job = nil
    say(text)
    pcall(lf, "follow")
end
-- the trip recorder: one line every 2 s while a job runs - who owns her (the action supervisor's current token), her distance to the walk target, the answer of the last walking order
local function trace(j, t, me)
    if t - (j.tracedAt or -100000) < 2000 then return end
    j.tracedAt = t
    local owner = "none"
    local S = type(SurvivorCompanion) == "table" and SurvivorCompanion.ActionSupervisor or nil
    if type(S) == "table" and type(S.snapshot) == "function" and me ~= nil then
        local ok, snap = pcall(S.snapshot, me)
        if ok and type(snap) == "table" then owner = tostring(snap.owner) .. ":" .. tostring(snap.action) .. ":" .. tostring(snap.phase) end
    end
    local sx, sy = xy(me)
    local w = j.walk
    local d = (w and sx) and string.format("%.1f", math.sqrt((sx - w.x) ^ 2 + (sy - w.y) ^ 2)) or "-"
    log("trace job=" .. tostring(j.kind) .. " owner=" .. owner .. " dist=" .. d .. " walk=" .. tostring(w and (w.x .. "," .. w.y) or "none") .. " tries=" .. tostring(j.tries))
end
stepBoard = function(t)
    local api, me = vehApi(), sol()
    if not api or not me then endToken(job); job = nil; return say(AR.driving_unavailable) end
    local st = seat()
    if st == "passenger" or st == "driver" then endToken(job); job = nil; return say(AR.board_ok) end
    if job.entering then
        if t - job.entering > 15000 then return endFail(AR.board_timeout) end
        return
    end
    if O.threatNear(6) > 0 then
        endToken(job, "sol_threat")        -- a fight: the actor belongs to Living Fellows' combat layer; the reservation is given back and the budget paused
        job.walk = nil
        job.deadline = job.deadline + (t - (job.lastStep or t)); job.lastStep = t
        return sayThreatOnce(job)
    end
    job.lastStep = t
    trace(job, t, me)
    if t >= job.deadline then return endFail(AR.board_timeout) end
    local sx, sy = xy(me)
    local w = job.walk
    if w and sx then
        local d = math.sqrt((sx - w.x) ^ 2 + (sy - w.y) ^ 2)
        if not w.best then w.best, w.bestAt = d, t
        elseif d < w.best - 0.3 then w.best, w.bestAt = d, t; job.noProgress = 0 end
        local S0 = sup(); if S0 and job.token then pcall(S0.progress, job.token, "d" .. math.floor(d)) end
    end
    if t - (job.lastTry or 0) < 1000 then return end
    job.lastTry = t
    -- 1) can she board from where she stands? (a pure check: no transaction, no reservation)
    local prep, why = nil, nil
    local havePre = type(api.preflightBoard) == "function"
    if havePre then
        local okp, a, b = pcall(api.preflightBoard, me, job.veh, job.seat, false)
        if okp then prep, why = a, b else why = "error" end
    end
    if prep ~= nil or not havePre then
        endToken(job, "sol_at_door")       -- the boarding transaction takes the actor itself
        local ok, a, b = pcall(api.board, me, job.veh, job.seat, playerIntent())
        if not ok then job = nil; return say(failText("error", "board")) end
        if a then job.entering = t; return end
        why = b
    end
    if why == "companion is not at the passenger door" then
        local sqs = nil
        local S = O.useToken and sup() or nil
        local wasPreempted = job.preempted == true            -- Living Fellows took the actor from us since the last step
        local tok, bwhy
        if S then
            tok, bwhy = beginToken(job)
            if not tok then                                     -- someone else owns her: say who, do not walk
                log("reservation refused: " .. tostring(bwhy))
                if t - (job.saidBusy or -100000) > 12000 then job.saidBusy = t; say(busyText(bwhy)) end
                return
            end
        end
        local ask = (w == nil) or wasPreempted
        if not ask and w ~= nil and w.leg ~= nil and sx ~= nil and (sx - w.x - 0.5) ^ 2 + (sy - w.y - 0.5) ^ 2 < 0.81 then ask = true end   -- spatial_access: at a door on her way, the next leg at once
        if w and w.bestAt and t - w.bestAt > 4000 and t - w.askedAt > 5000 then
            ask = true; job.tries = job.tries + 1
            job.noProgress = (job.noProgress or 0) + 1
            if job.noProgress >= 3 then return endFail(AR.no_path) end       -- three walks in a row that did not bring her closer: there is no way there from where she stands
        end
        if ask then
            if wasPreempted then job.preemptions = (job.preemptions or 0) + 1; job.preempted = false end
            if (job.preemptions or 0) > 6 then return endFail(busyText("preempted")) end
            local oks, got = pcall(api.boardingSquares, me, job.veh, job.seat, false)
            sqs = oks and got or nil
            if not startWalk(job, sqs, t) then
                job.failedWalks = (job.failedWalks or 0) + 1
                if job.failedWalks >= 3 then return endFail(AR.door_unreachable) end
            end
        end
        return
    end
    if type(why) == "string" and (why:find("stationary", 1, true) or why:find("moving", 1, true)) then return end      -- a moving car: wait until it stops
    return endFail(failText(why, "board"))
end

-- Board the front passenger seat (seat 1) of an explicitly selected car or the nearest car within the default radius.
function O.board(targetVehicle)
    local st = seat()
    if st == "passenger" or st == "driver" then
        local current = sol()
        current = current and type(current.getVehicle) == "function" and current:getVehicle() or nil
        if targetVehicle and current ~= targetVehicle then return say(AR.already_in_other_vehicle) end
        return say(AR.board_ok)
    end
    local veh = targetVehicle or playerVehicle()
    if not veh and type(U.nearestVehicle) == "function" then veh = U.nearestVehicle(30) end
    if not veh then return say(AR.no_vehicle_near) end
    if vehApi() and veh ~= nil then
        local function taken(i) local ok, v = pcall(function() return veh:isSeatOccupied(i) end); return ok and v == true end
        local wanted = nil
        local okN, n = pcall(function() return veh:getMaxPassengers() end)
        for i = 1, ((okN and tonumber(n)) or 2) - 1 do          -- seat 0 is the wheel: that takes an order to drive, never "get in"
            local missing = false                                          -- some vehicles lose or never had a seat
            local okI, installed = pcall(function() return veh:isSeatInstalled(i) end)
            if okI and installed == false then missing = true end
            if not taken(i) and not missing then wanted = i; break end
        end
        if wanted == nil then return say(AR.no_seat) end
        freshFlow()
        log("board target=" .. (targetVehicle and "selected" or "nearest") .. " radius=30 seat=" .. tostring(wanted))
        job = { kind = "ride", veh = veh, seat = wanted, since = nowMs(), deadline = nowMs() + 90000, tries = 0 }
        say(AR.boarding)
        return stepBoard(nowMs())
    end
    if vehApi() then return say(AR.no_vehicle_near) end
    return say(AR.front_seat_unavailable)
end
-- by car to a point (Sol Mind turns "home" / a remembered place into x,y before it reaches here): she drives on her own, the trip does not wait for the player to board
function O.driveToXY(x, y)
    if type(U.gpsSetDestination) ~= "function" or type(U.gpsStart) ~= "function" then return say(AR.driving_unavailable) end
    freshFlow()
    U.gpsSetDestination({ x = x, y = y, name = "" })
    local ok, reason = U.gpsStart(nil, true)
    log("drive to point " .. tostring(x) .. "," .. tostring(y) .. " -> " .. tostring(ok) .. " " .. tostring(reason))
    if not ok then return say(failText(reason, "wheel")) end
    say(AR.driving)
end
function O.goHome()
    local x, y = homePoint()
    if not x then return say(AR.no_home) end
    return O.driveToXY(x, y)
end
-- A menu request only stages the saved home as the GPS destination. The
-- player deliberately starts the actual trip from the GPS Drive control.
function O.setHomeDestination()
    local x, y = homePoint()
    if not x then return say(AR.no_home) end
    if type(U.gpsSetDestination) ~= "function" then return say(AR.driving_unavailable) end
    freshFlow()
    U.gpsSetDestination({ x = x, y = y, name = "home" })
    local g = G()
    if g and type(g.preview) == "table" then g.preview.at = nil end
    say(AR.home_destination_ready)
end
function O.leaveCar()
    if type(SolAuthority) == "table" and type(SolAuthority.releaseVehicle) == "function" then SolAuthority.releaseVehicle("order:exit") end
    if seat() == "out" then return say(AR.already_out) end
    freshFlow()
    local api, me = vehApi(), sol()
    local veh = me and type(me.getVehicle) == "function" and me:getVehicle() or nil
    if type(SolAuthority) == "table" and type(SolAuthority.holdOut) == "function" then SolAuthority.holdOut("player_order") end
    if api and type(api.exit) == "function" and veh ~= nil then
        local ok, a, b = pcall(api.exit, me, veh, nil, playerIntent())
        log("exit -> " .. tostring(ok) .. " " .. tostring(a) .. " " .. tostring(b))
        if ok and a then say(AR.exiting); follow("exit", 12000); return end
        return say(failText(ok and b or "error", "exit"))
    end
    local ok, reason = lf("exit_vehicle")
    if not ok then return say(failText(reason, "exit")) end
    say(AR.exiting); follow("exit", 12000)
end
function O.stop()
    endToken(job)
    job = nil
    if type(U.gpsStop) == "function" then U.gpsStop() end
    say(AR.stopped)
end

-- "enough, forget it": everything that could be holding her is released, each step on its own so one failing step never blocks the rest.
-- Ours: the job and its reservation. SolGPS: the drive, the door/wheel bookkeeping and the destination. Living Fellows': the current action token (forced), the retry
-- cool-downs and queued urgent work, a half-made boarding transaction, her current work; and last she goes back to following (the routine is Living Fellows' again).
function O.forget()
    SolScanCoordinator.cancelAll("sol_forget")
    local me = sol()
    local report = {}
    local function step(name, fn)
        local ok, a, b = pcall(fn)
        report[#report + 1] = name .. "=" .. (ok and "ok" or ("error:" .. tostring(a)))
        return ok, a, b
    end
    step("job", function() endToken(job); job = nil end)
    step("gps", function()
        if type(U.gpsStop) == "function" then U.gpsStop() end
        releaseGps(true)
    end)
    local SC = SurvivorCompanion
    if me ~= nil and type(SC) == "table" then
        local S = SC.ActionSupervisor
        if type(S) == "table" then
            if type(S.cancel) == "function" then step("token", function() return S.cancel(me, "sol_forget", nil, true) end) end
            if type(S.resetRetry) == "function" then step("retries", function() return S.resetRetry(me, "sol_forget") end) end
            if type(S.clearUrgent) == "function" then step("urgent", function() return S.clearUrgent(me, "sol_forget") end) end
        end
        local Vh = SC.Vehicle
        if type(Vh) == "table" and type(Vh.cancelTransaction) == "function" then step("boarding", function() return Vh.cancelTransaction(me, "sol_forget") end) end
        local Dn = SC.Decision
        if type(Dn) == "table" and type(Dn.cancelWork) == "function" then step("work", function() return Dn.cancelWork(me, "sol_forget") end) end
    end
    step("authority", function()
        if type(SolAuthority) == "table" then SolAuthority.clearWork("sol_forget"); SolAuthority.releaseVehicle("sol_forget") end
    end)
    step("follow", function() return lf("follow") end)
    log("forget -> " .. table.concat(report, " "))
    say(AR.forgot)
    return true, table.concat(report, " ")
end

-- the fixed orders of the order window: Living Fellows' own commands, one owner, then she returns to her instincts
local function fixedOrder(command, line)
    SolScanCoordinator.cancelAll("new_direct_order:" .. tostring(command))
    endToken(job); job = nil; releaseGps(false)
    if type(SolAuthority) == "table" and type(SolAuthority.clearWork) == "function" then SolAuthority.clearWork("order:" .. command) end   -- a new order ends ordered work
    if command ~= "stay" and type(SolAuthority) == "table" and type(SolAuthority.releaseVehicle) == "function" then SolAuthority.releaseVehicle("order:" .. command) end
    if command == "stay" and seat() ~= "out" and type(SolAuthority) == "table" and type(SolAuthority.holdVehicle) == "function" then
        local me = sol(); SolAuthority.holdVehicle(me and type(me.getVehicle) == "function" and me:getVehicle() or nil, "order:stay")   -- "wait here" in a car: she waits in the car
    end
    local ok, reason = lf(command)
    if not ok then return say(failText(reason, "order")) end
    say(line)
end
function O.follow() return fixedOrder("follow", AR.ok_follow) end
function O.stay() return fixedOrder("stay", AR.ok_stay) end
function O.come() return fixedOrder("regroup", AR.ok_come) end
function O.cautious() return fixedOrder("cautious_follow", AR.ok_follow) end
function O.fireAtWill() local ok, r = lf("fire_at_will"); if not ok then return say(failText(r, "order")) end say(AR.ok_fire) end
function O.holdFire() local ok, r = lf("hold_fire"); if not ok then return say(failText(r, "order")) end say(AR.ok_hold) end
function O.retreat() return fixedOrder("retreat", AR.ok_retreat) end
-- the rescue is a Sol Mind goal (drive, fight, bring the player home): the window sends the same sentence the chat would
function O.rescue()
    if type(U.sendChat) ~= "function" then return say(AR.rescue_no_mind) end
    local A_ = rawget(_G, "SolAuthority")
    local scoped = type(A_) == "table" and type(A_.on) == "function" and A_.on("task_scoped_perception") == true
    if U.scanNow and not scoped then pcall(U.scanNow) end
    local id = U.sendChat({ text = AR.rescue_text })
    log("rescue request -> " .. tostring(id))
    if not id then return say(AR.rescue_no_mind) end
    say(AR.rescue_sent)
end
function O.setHomeHere()
    if type(SolHome) ~= "table" or type(SolHome.setHere) ~= "function" then return say(AR.generic) end
    local ok, reason = SolHome.setHere()
    if not ok then return say(failText(reason, "home")) end
    say(AR.home_set)
end
function O.driveToMarker()
    if type(U.gpsMapMarker) ~= "function" or type(U.gpsSetDestination) ~= "function" or type(U.gpsStart) ~= "function" then return say(AR.driving_unavailable) end
    local m, why = U.gpsMapMarker()
    if not m then return say(AR.no_destination) end
    freshFlow()
    U.gpsSetDestination(m)
    local ok, reason = U.gpsStart(nil, nil)
    log("drive to marker " .. tostring(m.x) .. "," .. tostring(m.y) .. " -> " .. tostring(ok) .. " " .. tostring(reason))
    if not ok then return say(failText(reason, "wheel")) end
    say(AR.driving)
end

-- the menu: called by the hook in SCUIContext with the submenu, the player and the square that was right-clicked
function O.addMenu(menu, player, square, targetVehicle)
    if (type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("order_menu")) then   -- Sol fix 6
        menu:addOption(AR.cmd_follow, nil, function() O.follow() end)
        menu:addOption(AR.cmd_stay, nil, function() O.stay() end)
        menu:addOption(AR.cmd_come, nil, function() O.come() end)
        menu:addOption(AR.cmd_cautious, nil, function() O.cautious() end)
        menu:addOption(AR.cmd_fire, nil, function() O.fireAtWill() end)
        menu:addOption(AR.cmd_hold_fire, nil, function() O.holdFire() end)
        menu:addOption(AR.cmd_retreat, nil, function() O.retreat() end)
        menu:addOption(AR.cmd_rescue, nil, function() O.rescue() end)
        menu:addOption(AR.cmd_drive_marker, nil, function() O.driveToMarker() end)
        if type(SolHome) == "table" and (type(SolHome.enabled) ~= "function" or SolHome.enabled()) then
            menu:addOption(AR.cmd_set_home, nil, function() O.setHomeHere() end)
        end
    end
    menu:addOption(AR.board, nil, function() O.board() end)
    if targetVehicle then menu:addOption(AR.board_selected, nil, function() O.board(targetVehicle) end) end
    menu:addOption(AR.wheel, nil, function() O.takeWheel() end)
    menu:addOption(AR.home, nil, function() O.setHomeDestination() end)
    menu:addOption(AR.exit, nil, function() O.leaveCar() end)
    menu:addOption(AR.stop, nil, function() O.stop() end)
    menu:addOption(AR.forget, nil, function() O.forget() end)
end

-- measuring verb: which way does the game say a character faces?
function O.dirProbe()
    local p = getSpecificPlayer and getSpecificPlayer(0)
    if not p then return false, "no_player" end
    local out = {}
    local d = type(p.getDir) == "function" and p:getDir() or nil
    out[#out + 1] = "dir=" .. tostring(d)
    local fd = type(p.getForwardDirection) == "function" and p:getForwardDirection() or nil
    if fd and type(fd.getX) == "function" then out[#out + 1] = "fwd=" .. tostring(fd:getX()) .. "," .. tostring(fd:getY()) end
    if type(p.getDirectionAngle) == "function" then out[#out + 1] = "angle=" .. tostring(p:getDirectionAngle()) end
    local v = type(p.getVehicle) == "function" and p:getVehicle() or nil
    if v then
        for _, n in ipairs({ "getAngleX", "getAngleY", "getAngleZ" }) do
            if type(v[n]) == "function" then out[#out + 1] = n .. "=" .. tostring(v[n](v)) end
        end
    end
    return true, table.concat(out, " ")
end

-- observation only (results pass through unchanged): what changes or ends a drive, who sends her walking orders and which Living Fellows commands arrive
local function wrapObservers()
    local D = drivingApi()
    if D and not D._solLogged then
        D._solLogged = true
        for _, name in ipairs({ "setSpeed", "stop", "release", "releaseActor" }) do
            local f = D[name]
            if type(f) == "function" then
                D[name] = function(...)
                    local a, b = f(...)
                    print("[SolDrive] " .. name .. "(" .. tostring((select(2, ...))) .. ") -> " .. tostring(a) .. " " .. tostring(b))
                    return a, b
                end
            end
        end
    end
    if not O._gotoLogged and type(U.solGoto) == "function" then
        O._gotoLogged = true
        local f = U.solGoto
        U.solGoto = function(x, y, ...)
            local g = G() or {}
            O._own = true
            local okc, a, b = pcall(f, x, y, ...)
            O._own = false
            if not okc then error(a, 0) end
            print("[SolDrive] solGoto(" .. tostring(x) .. "," .. tostring(y) .. ") doorWalk=" .. tostring(g.doorWalk ~= nil) .. " wheelWait=" .. tostring(g.wheelWaitSince ~= nil)
                .. " await=" .. tostring(g.awaitPlayer) .. " dest=" .. tostring(g.dest ~= nil) .. " -> " .. tostring(a) .. " " .. tostring(b))
            return a, b
        end
    end
    local SC = SurvivorCompanion
    local Vh = type(SC) == "table" and SC.Vehicle or nil
    if type(Vh) == "table" and not Vh._solLogged then
        Vh._solLogged = true
        for _, name in ipairs({ "board", "exit" }) do
            local f = Vh[name]
            if type(f) == "function" then
                Vh[name] = function(...)
                    local a, b = f(...)
                    print("[SolDrive] Vehicle." .. name .. " -> " .. tostring(a) .. " " .. tostring(b))
                    return a, b
                end
            end
        end
    end
    local C = type(SC) == "table" and SC.Commands or nil
    if type(C) == "table" and not C._solLogged and type(C.issue) == "function" then
        C._solLogged = true
        local f = C.issue
        C.issue = function(rowId, command, ...)
            print("[SolDrive] LF command " .. tostring(command))
            if job and not O._own and USER_ORDERS[command] then
                log("the order " .. tostring(command) .. " replaces the job " .. tostring(job.kind))
                endToken(job); job = nil; releaseGps(false)
            elseif not job and not O._own and USER_ORDERS[command] and command ~= "move_to" and command ~= "board_vehicle" then
                local g = G()                                                    -- the door walk is not a job: his order has to end it too (its own step is a move_to)
                if g and g.doorWalk then
                    log("the order " .. tostring(command) .. " ends the walk to the car")
                    g.doorRetryAt = nil
                    releaseGps(false)
                end
            end
            return f(rowId, command, ...)
        end
    end
end
O.wrapObservers = wrapObservers
O.wrapDriving = wrapObservers

-- what the chat and the voice ask for goes through the SAME functions as the right-click menu (one path, one priority): Sol Mind sends verbs to
-- U.runAction, which used to reach Living Fellows' closed order ("board_vehicle_rejected") for these.
local CHAT_VERBS = {
    board_vehicle = function() O.board() end,
    sol_sit_beside = function() O.board() end,
    exit_vehicle = function() O.leaveCar() end,
    sol_take_wheel = function() O.takeWheel() end,
    sol_drive = function(option) return O.driveDestination(option) end,
    sol_forget = function() O.forget() end,
}
local function install()
    if O._installed then return end
    O._installed = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "sol_dir_probe" then
            local ok, a, b = pcall(O.dirProbe)
            if not ok then return false, "probe_error" end
            return a, b
        end
        if job and MOVEMENT_VERBS[id] then                  -- a newer request from the chat or the voice replaces the running job
            log("the request " .. tostring(id) .. " replaces the job " .. tostring(job.kind))
            endToken(job); job = nil; releaseGps(false)
        end
        local handler = CHAT_VERBS[id]
        if handler then
            local ok, accepted, reason = pcall(handler)
            log("chat verb " .. tostring(id) .. " -> " .. tostring(ok) .. (ok and (" " .. tostring(accepted) .. " " .. tostring(reason or "")) or (" " .. tostring(accepted))))
            if not ok then return false, "orders_error" end
            if id == "sol_drive" then return accepted == true, reason or (accepted and "issued" or "drive_refused") end
            return true, "issued"
        end
        if id == "sol_goto" then        -- "go home" / "go there": by car when she is in one, on foot otherwise (Sol Mind sends the point as "x,y")
            local st = seat()
            if st == "driver" or st == "passenger" then
                local x, y = string.match(tostring(option or ""), "(%-?%d+)%s*,%s*(%-?%d+)")
                local ok, err
                if x then ok, err = pcall(O.driveToXY, tonumber(x), tonumber(y))
                elseif option == "home" then ok, err = pcall(O.goHome) end
                if ok ~= nil then
                    log("chat verb sol_goto (in a car) -> " .. tostring(ok))
                    return ok == true, ok and "issued" or "orders_error"
                end
            end
        end
        return base(id, option)
    end
    if Events and Events.OnTick then
        Events.OnTick.Add(function() onTick(); if not (O._gotoLogged and (drivingApi() or {})._solLogged) then pcall(wrapObservers) end end)
    end
    pcall(wrapObservers)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(install) end
print("[SolOrders] ready v" .. O.VERSION)

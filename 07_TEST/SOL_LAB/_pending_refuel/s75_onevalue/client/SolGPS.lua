-- SolGPS.lua - Sol drives you to a destination, with a Sol-styled GPS panel.
-- Driving is Living Fellows' own (SCDriving.lua): the native bridge presses the car's pedals and wheel, follows
-- the street route of SCExpeditionRoute, slides round wrecks, stops for blocked lanes and re-plans up to 3 times.
--   SC.Driving.takeWheel(actor, vehicle, intent)  -> Sol takes the driver's seat (SC.Vehicle.boardDriver)
--   SC.Driving.drive(actor, {x, y, z = 0}, { speedKmh <= 30 })
--   SC.Driving.jobStatus(actor) / SC.Driving.status(actor) / SC.Driving.stop(actor, reason)
-- Destinations: the newest symbol you placed on the world map, home, a remembered place, or Sol Mind's request.
require "ISUI/ISPanel"
require "SolText"
SolUI = SolUI or {}
local U = SolUI
local T = SolText
U.GPS_VERSION = "0.5.1"
local REQ, STATE = "SolGPS_Request.txt", "SolGPS_State.txt"
local SPEEDS = { slow = 10, normal = 20, fast = 30 }          -- LF caps companion driving at 30 km/h
local W, H = 330, 236
local function log(m) print("[SolGPS] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function LF() local sc = SurvivorCompanion; return type(sc) == "table" and sc or nil end
local function call(o, name, ...)
    if o == nil then return nil end
    local f = o[name]; if f == nil then return nil end
    local ok, v = pcall(f, o, ...); if ok then return v end; return nil
end
local function isAr() return not (U.lang and U.lang() == "en") end

U.gps = U.gps or { dest = nil, speed = "normal", lastResult = nil, reason = nil }
local G = U.gps
if G.solo == nil then G.solo = false end

-- ---------------------------------------------------------------- destinations
function U.gpsMapMarker()
    local wm = ISWorldMap_instance
    local api = wm and wm.mapAPI and call(wm.mapAPI, "getSymbolsAPI")
    if not api then return nil, "map_not_opened" end
    local n = tonumber((call(api, "getSymbolCount"))) or 0
    if n <= 0 then return nil, "no_marker" end
    local s = call(api, "getSymbolByIndex", n - 1)
    local x, y = tonumber((call(s, "getWorldX"))), tonumber((call(s, "getWorldY")))
    if not x or not y then return nil, "no_marker" end
    return { x = math.floor(x), y = math.floor(y), name = isAr() and "\\u0627\\u0644\\u0639\\u0644\\u0627\\u0645\\u0629 \\u0639\\u0644\\u0649 \\u0627\\u0644\\u062E\\u0631\\u064A\\u0637\\u0629" or "Map marker" }
end
function U.gpsSetDestination(d) if d and d.x and d.y then G.dest = { x = math.floor(d.x), y = math.floor(d.y), name = d.name or "" }; return true end return false end

-- Takes the destination off the screen. option "errand": only a target an errand set for itself, never one the player chose.
function U.gpsClear(option)
    if not G.dest then return true, "already_clear" end
    if option == "errand" then
        local name = tostring(G.dest.name or "")
        if string.sub(name, 1, 11) ~= "Gas station" and name ~= "back to the player" then return true, "not_an_errand_target" end
    end
    local st = U.gpsStatus and U.gpsStatus() or {}
    if option ~= "errand" and (st.phase == "following" or st.phase == "planning" or st.phase == "replanning" or st.phase == "blocked" or st.phase == "streaming_wait") then U.gpsStop() end
    G.dest = nil
    if G.preview then G.preview.at, G.preview.route, G.preview.reason, G.preview.snap, G.preview.key = nil, nil, nil, nil, nil end
    if G.lastResult ~= "failed" or option ~= "errand" then G.lastResult, G.reason = nil, nil end
    return true, "destination_cleared"
end
-- A click on the map: the same spot again takes it off, anywhere else sets it.
function U.gpsMapClick(wx, wy, driving)
    local d = G.dest
    if d and not driving and math.abs(d.x - wx) <= 2 and math.abs(d.y - wy) <= 2 then
        U.gpsClear()
        return "cleared"
    end
    return "set"
end

-- ---------------------------------------------------------------- driving
local function sol() return U.solActor and U.solActor() or nil end
local function playerVehicle() local p = getSpecificPlayer and getSpecificPlayer(0); return p and call(p, "getVehicle") or nil end
local function carStillLoaded(car)
    local sc = LF()
    local service = sc and sc.Vehicle
    if type(service) ~= "table" or type(service.loadedVehicles) ~= "function" then return true end
    local ok, vehicles = pcall(service.loadedVehicles)
    if not ok or type(vehicles) ~= "table" then return true end
    for _, v in ipairs(vehicles) do if v == car then return true end end
    return false
end
-- she sits in a car that has left the loaded world: nothing may be done with that car
local function seatedInGoneCar(s)
    local inside = call(s, "getVehicle")
    if inside == nil or carStillLoaded(inside) then return false end
    log("she is seated in a car that is no longer in the loaded world")
    G.wheelCar, G.lastResult, G.reason = nil, "failed", "no_vehicle_near"
    return true
end
local function nearestCar()
    local p = getSpecificPlayer and getSpecificPlayer(0)
    local anchor = sol() or p
    if not anchor then return nil end
    local sc = LF()
    local service = sc and sc.Vehicle
    if type(service) ~= "table" or type(service.loadedVehicles) ~= "function" then return nil end
    local ok, vehicles = pcall(service.loadedVehicles)
    if not ok or type(vehicles) ~= "table" then return nil end
    local ax, ay = tonumber((call(anchor, "getX"))), tonumber((call(anchor, "getY")))
    if not ax or not ay then return nil end
    if type(U.solPickCar) == "function" and U.solCarRulesOn() then
        local picked, none = U.solPickCar(vehicles, anchor, 30)
        U._noEligibleCar = none == true
        if picked == nil then log("no car she may use within 30 tiles") end
        return picked
    end
    local best, bd = nil, 30 * 30
    for _, v in ipairs(vehicles) do
        local vx, vy = tonumber((call(v, "getX"))), tonumber((call(v, "getY")))
        if vx and vy then
            local d = (vx - ax)^2 + (vy - ay)^2
            if d < bd then best, bd = v, d end
        end
    end
    if best == nil then log("no car within 30 tiles of " .. math.floor(ax) .. "," .. math.floor(ay) .. " (anchor " .. (sol() and "sol" or "player") .. "), cars listed: " .. #vehicles) end
    return best
end
-- Native driving ownership must be armed while the player is still outside.
-- Sol fix (order_arbiter): "action_owned:..." means a short action of hers (a bandage, say) holds the body. Asking again every
-- frame only cancels and re-sends orders; the walk waits for it and asks once a second.
local ORDER_WAIT_LAST_ASK = 500        -- the door walk re-asks 1.5 s after lastAsk, so this leaves about 1 s
local function orderMustWait(reason)
    local A = rawget(_G, "SolAuthority")
    return type(reason) == "string" and string.find(reason, "action_owned", 1, true) == 1
        and type(A) == "table" and type(A.on) == "function" and A.on("order_arbiter") == true
end

-- sitting or lounging holds the body for as long as it likes, and he has just told her to go
local function yieldDowntime(s, reason)
    if type(reason) ~= "string" or string.find(reason, "action_owned:downtime:", 1, true) ~= 1 then return end
    if not (type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("order_breaks_rest") == true) then return end
    local SC = LF()
    if SC and type(SC.Downtime) == "table" and type(SC.Downtime.cancel) == "function" then pcall(SC.Downtime.cancel, s, "sol_gps") end
end

-- Once armed, the player can board as passenger and the prepared job is promoted
-- to a route without calling the native driveStart bridge a second time.
local function prepareDriver(D, s)
    if not D or type(D.start) ~= "function" then
        G.lastResult, G.reason = "failed", "driving_unavailable"
        return false, G.reason
    end
    local goal = G.dest and { x = G.dest.x, y = G.dest.y, z = 0 } or nil
    local ok, why = D.start(s, goal)
    if not ok then
        G.lastResult, G.reason = "failed", tostring(why or "cannot_prepare_drive")
        return false, G.reason
    end
    if G.dest then
        G.lastResult, G.reason = "failed", "board_passenger"
        return true, "board_passenger"
    end
    G.lastResult, G.reason = "ready", "await_destination"
    return true, "await_destination"
end

-- Sol takes the driver's seat.  If she is already a passenger she first exits
-- and re-enters through SCVehicle's verified driver-seat transaction; no direct
-- switchSeat shortcut is used.
-- Sol patch 2026-10-26: which car is hers? The one she sits in; otherwise the one nearest to HER, never one just because the player sits in it.
-- Sol patch 2026-10-26: the door-walk allowance (3 tries) was never given back, so every order after the third walk of a session was refused; it renews after a quiet spell
-- Sol patch 2026-10-26 (door squares): the first square may be where the player stands, and Living Fellows accepts boarding by the distance to the DOOR, not by standing on the square
-- Sol patch 2026-10-26 (fight): while a zombie is near, Living Fellows' combat layer owns her movement; the walk waits and its time budget is paused
local function solThreatNear()
    return SolOrders ~= nil and type(SolOrders.threatNear) == "function" and (SolOrders.threatNear(6)) > 0
end
local function solThreatPause(w)
    if not solThreatNear() then return false end
    w.since = w.since + 1000
    w.lastAsk = (w.lastAsk or 0) + 1000
    if w.movedAt then w.movedAt = w.movedAt + 1000 end
    if G.doorWalkFrom then G.doorWalkFrom = G.doorWalkFrom + 1000 end
    return true
end
local function solPickDoorSquare(sqs, s, offset)
    if type(sqs) ~= "table" then return nil end
    local pl = getSpecificPlayer and getSpecificPlayer(0)
    local px, py = pl and tonumber((call(pl, "getX"))), pl and tonumber((call(pl, "getY")))
    local free = {}
    for i = 1, #sqs do
        local q = sqs[i]
        if type(SolAuthority) == "table" and type(SolAuthority.walkableNear) == "function" then
            local okW, w = pcall(SolAuthority.walkableNear, q); if okW and w ~= nil then q = w end   -- Sol: not a square under the car's body
        end
        local qx, qy = tonumber((call(q, "getX"))), tonumber((call(q, "getY")))
        if qx and qy then
            local blocked = px and py and ((qx + 0.5 - px) ^ 2 + (qy + 0.5 - py) ^ 2) < 1.69      -- the player's body is on it (1.3 tiles)
            if not blocked then free[#free + 1] = q end
        end
    end
    -- Never send Sol onto the square occupied by the player. If every valid
    -- door-side square is blocked, fail this candidate instead of walking into
    -- the player; the next door-square attempt can route around them.
    local list = free
    if #list == 0 then return nil end
    return list[(((G.doorTries or 0) + (offset or 0)) % #list) + 1]                                              -- a later try uses the next square
end
-- Sol fix: going round the car to the far door takes her along its side, so the straight-line distance to the door hardly
-- changes. That used to count as "stuck": boarding was tried from the wrong side, refused, and the five allowed tries were
-- gone in half a minute. Now she is stuck only when she has really stopped, and she is at the door when the game's own
-- boarding check says so. Returns "board", "stopped" or "walk".
local function solDoorStep(w, x, y, ddx, ddy, ready, t)
    if not w.movedAt then w.moveX, w.moveY, w.movedAt = x, y, t end
    if (x - w.moveX) ^ 2 + (y - w.moveY) ^ 2 >= 0.16 then w.moveX, w.moveY, w.movedAt = x, y, t end
    local d2 = ddx * ddx + ddy * ddy
    if ready == true or d2 <= 0.5625 then return "board" end
    if t - w.movedAt > 4000 and d2 <= 12.25 then return "stopped" end
    return "walk"
end
-- true: she can board from where she stands. false: she is not at the door yet. nil: something else; the real attempt will say what.
local function solDoorReady(s)
    local SC = LF()
    local api = SC and SC.Vehicle
    if not G.wheelCar or type(api) ~= "table" or type(api.preflightBoard) ~= "function" then return nil end
    local ok, plan, why = pcall(api.preflightBoard, s, G.wheelCar, 0, true)
    if not ok then return nil end
    if plan ~= nil then return true end
    if why == "companion is not at the passenger door" then return false end
    return nil
end
local DOOR_WALK_BUDGET_MS = 60000
local function solDoorTriesLeft()
    local t = nowMs()
    if not G.doorWalkFrom or ((G.doorTriesAt or 0) > 0 and t - G.doorTriesAt > 45000) then G.doorWalkFrom, G.doorTries = t, 0 end
    return t - G.doorWalkFrom < DOOR_WALK_BUDGET_MS
end
local function solClaimsCar(inside, pv)
    if inside ~= nil then return inside == pv end
    local near = nearestCar and nearestCar()
    return near == nil or near == pv
end
-- Sol: out of the passenger seat, on the way to the driver's. Issued straight to Living Fellows: going through the order page
-- needs that page's row, and without it the order was dropped without a word. A refusal (a bandage in progress) is retried.
local function solLeaveSeat(s)
    local SC, player = LF(), getSpecificPlayer and getSpecificPlayer(0) or nil
    local accepted, reason = false, "lf_unavailable"
    if SC and type(SC.Commands) == "table" and type(SC.Commands.issue) == "function"
            and type(SC.GameplayUtil) == "table" and type(SC.GameplayUtil.idOf) == "function" then
        local okId, id = pcall(SC.GameplayUtil.idOf, s)
        if okId and type(id) == "string" and id ~= "" then
            local ok, a, b = pcall(SC.Commands.issue, id, "exit_vehicle", nil, player)
            accepted, reason = ok and a == true, ok and b or a
        else reason = "no_actor_id" end
    end
    G.wheelExitNext = nowMs() + (accepted and 4000 or 1500)       -- once accepted, the getting-out animation is left alone
    if not accepted and G.wheelExitWhy ~= tostring(reason) then
        G.wheelExitWhy = tostring(reason)
        log("leaving the passenger seat refused: " .. G.wheelExitWhy)
    end
    return accepted
end

function U.gpsTakeWheel()
    local SC = LF(); local D = SC and SC.Driving
    if not D or type(D.takeWheel) ~= "function" or type(D.start) ~= "function" then
        G.lastResult, G.reason = "failed", "driving_unavailable"; return false, G.reason
    end
    local s = sol(); if not s then G.lastResult, G.reason = "failed", "no_sol"; return false, G.reason end
    if seatedInGoneCar(s) then return false, G.reason end
    if type(D.clearOutcome) == "function" then D.clearOutcome(s) end
    if D.isDriver and D.isDriver(s) then log("takeWheel: already at the wheel"); return prepareDriver(D, s) end
    if type(SolAuthority) == "table" and type(SolAuthority.clearHoldOut) == "function" then SolAuthority.clearHoldOut("take_wheel") end
    -- already walking to the door: a second request must not interrupt the walk
    if G.doorWalk and nowMs() - G.doorWalk.since < DOOR_WALK_BUDGET_MS then
        log("takeWheel: already walking to the door")
        G.lastResult, G.reason = "failed", "walking_to_door"
        return true, "moving_to_wheel"
    end
    local inside = call(s, "getVehicle")
    local pv = playerVehicle()
    if pv and not solClaimsCar(inside, pv) then log("takeWheel: the player's car is not hers"); pv = nil end
    if pv then
        local drv, me = call(pv, "getDriver"), getSpecificPlayer and getSpecificPlayer(0)
        if drv ~= nil and drv == me then G.lastResult, G.reason = "failed", "player_is_driver"; return false, G.reason end
        G.wheelCar = pv
    end
    if inside then
        if SC.Vehicle and type(SC.Vehicle.shiftToDriver) == "function" then
            local okS, shifted, whyS = pcall(SC.Vehicle.shiftToDriver, s, inside)
            log("takeWheel: seat change inside the car -> " .. tostring(okS and shifted) .. " " .. tostring(okS and whyS or shifted))
            if okS and shifted == true and D.isDriver and D.isDriver(s) then
                G.wheelCar, G.leaveSeatCount, G.wheelWaitSince = nil, 0, nil
                return prepareDriver(D, s)
            end
        end
        log("takeWheel: getting out to walk round to the driver's door")
        G.wheelCar, G.wheelWaitSince = inside, nowMs()
        -- Sol: never a loop. Getting out, being refused the wheel and sitting back down must not repeat without end.
        if (G.leaveSeatAt or 0) < nowMs() - 60000 then G.leaveSeatCount = 0 end
        if (G.leaveSeatCount or 0) >= 2 then
            G.wheelWaitSince = nil
            G.lastResult, G.reason = "failed", "cannot_take_wheel"
            log("gave up on the driver's seat after " .. tostring(G.leaveSeatCount) .. " tries")
            return false, G.reason
        end
        G.leaveSeatCount, G.leaveSeatAt = (G.leaveSeatCount or 0) + 1, nowMs()
        G.wheelExitWhy = nil
        solLeaveSeat(s)
        G.lastResult, G.reason = "failed", "moving_to_wheel"
        return true, "moving_to_wheel"
    end
    if G.wheelCar ~= nil and not carStillLoaded(G.wheelCar) then log("the car she was going for is no longer in the loaded world"); G.wheelCar = nil end
    local veh = G.wheelCar or nearestCar()
    if not veh then G.lastResult, G.reason = "failed", (U._noEligibleCar == true) and "no_usable_car" or "no_vehicle_near"; return false, G.reason end
    local ok, why = D.takeWheel(s, veh, { playerCommand = true, immediateCommand = true })
    do
        local px, py = call(s, "getX"), call(s, "getY")
        log("takeWheel: board -> " .. tostring(ok) .. " " .. tostring(why) .. " at " .. tostring(px) .. "," .. tostring(py)
            .. " door distance squared " .. tostring(px and py and call(veh, "getEnterSeatDistance", 0, px, py)))
    end
    -- same as LF SCExpeditionCar 376-394: refused for not being at the door -> walk to the door square, then retry
    if not ok and why == "companion is not at the passenger door" and SC.Vehicle and type(SC.Vehicle.boardingSquares) == "function" and solDoorTriesLeft() and U.solGoto then
        local sqs = SC.Vehicle.boardingSquares(s, veh, 0, true)
        local sq = solPickDoorSquare(sqs, s)
        local dx, dy = sq and tonumber((call(sq, "getX"))), sq and tonumber((call(sq, "getY")))
        if dx and dy then
            if SC.Decision and type(SC.Decision.cancelWork) == "function" then pcall(SC.Decision.cancelWork, s, "sol_gps") end
            local okw, whyw = U.solGoto(dx, dy)
            if okw ~= true and orderMustWait(whyw) then        -- she is finishing something short: no other square helps, and no door try is spent
                yieldDowntime(s, whyw)
                G.wheelCar, G.doorWalk = veh, { x = dx + 0.5, y = dy + 0.5, since = nowMs(), lastAsk = nowMs() - ORDER_WAIT_LAST_ASK }
                G.lastResult, G.reason = "failed", "walking_to_door"
                return true, "moving_to_wheel"
            end
            if okw ~= true then        -- refused (the square is not free): the next square beside the door, at once
                for k = 1, #sqs - 1 do
                    local q2 = solPickDoorSquare(sqs, s, k)
                    local ex, ey = q2 and tonumber((call(q2, "getX"))), q2 and tonumber((call(q2, "getY")))
                    if ex and ey and U.solGoto(ex, ey) == true then dx, dy = ex, ey; break end
                end
            end
            G.doorTries = (G.doorTries or 0) + 1; G.doorTriesAt = nowMs()
            G.wheelCar, G.doorWalk = veh, { x = dx + 0.5, y = dy + 0.5, since = nowMs(), lastAsk = nowMs() }
            log("takeWheel: walking to the door square " .. tostring(dx) .. "," .. tostring(dy) .. " try " .. tostring(G.doorTries))
            G.lastResult, G.reason = "failed", "walking_to_door"
            return true, "moving_to_wheel"
        end
        -- no free square beside the door yet (the player may be standing on them): look again in a moment
        G.wheelCar, G.doorRetryAt, G.doorTriesAt = veh, nowMs() + 2000, nowMs()
        G.lastResult, G.reason = "failed", "walking_to_door"
        return true, "moving_to_wheel"
    end
    if not ok then
        local notAtDoor = why == "companion is not at the passenger door"
        if notAtDoor then G.doorWalkFrom = nil; log("door not reached in time") end       -- the next order gets a fresh minute
        G.lastResult, G.reason = "failed", notAtDoor and "could_not_reach_door" or tostring(why or "cannot_take_wheel")
        return false, G.reason
    end
    G.wheelCar, G.doorWalkFrom = nil, nil                 -- she is in it: the next trip chooses afresh
    return prepareDriver(D, s)
end

-- nearest named road to a world point, through the same bridge call Living Fellows uses (SCFactions nearestStreetFromBridge)
function U.gpsNearestRoad(x, y)
    local SC = LF(); local api = SC and SC.Factions and SC.Factions.streetDataApi and SC.Factions.streetDataApi()
    local bridge = type(_G) == "table" and rawget(_G, "SCBridge") or nil
    if not api or not bridge or not SC.Call or type(SC.Call.static) ~= "function" then return nil end
    local called, packed = SC.Call.static(bridge, "nearestStreet", api, x, y, 1500)
    if not called or type(packed) ~= "string" then return nil end
    local name, d, sx, sy = string.match(packed, "^([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)$")
    sx, sy = tonumber(sx), tonumber(sy)
    if not sx or not sy then return nil end
    return math.floor(sx), math.floor(sy), tonumber(d), name
end
function U.gpsStart(speedKey, soloMode)
    local SC = LF(); local D = SC and SC.Driving
    if not D or type(D.drive) ~= "function" or type(D.start) ~= "function" then
        G.lastResult, G.reason = "failed", "driving_unavailable"; return false, G.reason
    end
    if not G.dest then G.lastResult, G.reason = "failed", "no_destination"; return false, G.reason end
    local s = sol(); if not s then G.lastResult, G.reason = "failed", "no_sol"; return false, G.reason end
    if speedKey and SPEEDS[speedKey] then G.speed = speedKey end
    if soloMode ~= nil then G.solo = soloMode == true end
    if seatedInGoneCar(s) then return false, G.reason end

    -- Sol: a finished trip still holds the car ("drive_already_owned") and its old "arrived" would answer for the new one
    if D.isDriver and D.isDriver(s) and type(D.jobStatus) == "function" and type(D.stop) == "function" then
        local okJ, js = pcall(D.jobStatus, s)
        local solA = rawget(_G, "SolAuthority")
        local replace = type(solA) == "table" and type(solA.on) == "function" and solA.on("drive_replace") == true      -- a new order replaces the trip she is on
        if okJ and type(js) == "table" and (js.result == "arrived" or js.result == "failed" or replace) then pcall(D.stop, s, "new_destination") end
    end

    if not (D.isDriver and D.isDriver(s)) then
        local ok, why = U.gpsTakeWheel()
        if not ok then return false, why end
        if why == "moving_to_wheel" then return true, why end
    else
        local prepared, why = prepareDriver(D, s)
        if not prepared then return false, why end
    end

    -- Normal trips wait for the local player to board. Emergency/rescue plans
    -- may explicitly arm solo driving so Sol can travel to a remote player.
    -- Sol patch 2026-10-25: the player is not in the car (for example he marked the destination from afar): do not wait for him.
    do
        local p0 = getSpecificPlayer and getSpecificPlayer(0)
        if not G.solo and not G.mustWaitPlayer and p0 and not playerVehicle() then   -- Sol: an explicit solo=0 (rescue return trip) always waits for the player
            local ddx = (tonumber((call(p0, "getX"))) or 0) - (tonumber((call(s, "getX"))) or 0)
            local ddy = (tonumber((call(p0, "getY"))) or 0) - (tonumber((call(s, "getY"))) or 0)
            local goesAlone = type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("solo_drive")   -- Sol fix 12: "drive" means drive, with the player or without
            if goesAlone or ddx * ddx + ddy * ddy > 196 then G.solo = true end
        end
    end
    local pv = playerVehicle()
    local sv = call(s, "getVehicle")
    if not G.solo then
        if not pv then
            G.awaitPlayer = true
            G.lastResult, G.reason = "failed", "board_passenger"
            return true, "board_passenger"
        end
        if pv ~= sv then G.solo = true; log("the player is in another vehicle: she drives alone") end
    end

    G.awaitPlayer = false
    local goal = { x = G.dest.x, y = G.dest.y, z = 0 }
    local P0 = G.preview
    if P0 and P0.snap and P0.key == (G.dest.x .. "," .. G.dest.y) then goal = { x = P0.snap.x, y = P0.snap.y, z = 0 } end
    local ok, why = D.drive(s, goal, { speedKmh = (SPEEDS[G.speed] or 10) + ((type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("drive_fast") == true) and 10 or 0), blockWaitMs = 2500 })
    G.lastResult, G.reason = ok and "driving" or "failed", ok and nil or tostring(why)
    if ok then G.lastDriveCar = call(s, "getVehicle") or G.lastDriveCar end            -- Sol: the car she drives is the one a return trip comes back to
    G.startedAt = nowMs()
    log((ok and "driving to " or "drive refused: ") .. G.dest.x .. "," .. G.dest.y
        .. " at " .. SPEEDS[G.speed] .. " km/h " .. tostring(why or ""))
    return ok, why
end
function U.gpsStop()
    G.retryWhenOut, G.awaitPlayer, G.wheelWaitSince, G.doorWalk, G.doorTries, G.doorWalkFrom, G.doorRetryAt = false, false, nil, nil, 0, nil, nil
    G.leaveSeatCount = 0
    G.solo = false
    G.mustWaitPlayer = false
    local SC = LF(); local s = sol()
    if SC and SC.Driving and s then pcall(SC.Driving.stop, s, "player_stop") end
    G.lastResult, G.reason = "stopped", nil
    return true
end
function U.gpsStatus()
    local SC = LF(); local s = sol()
    local st = { dest = G.dest, speed = G.speed, result = G.lastResult, reason = G.reason, solo = G.solo == true }
    if SC and SC.Driving and s then
        local okJ, js = false, nil
        if type(SC.Driving.jobStatus) == "function" then okJ, js = pcall(SC.Driving.jobStatus, s) end
        if okJ and type(js) == "table" then st.phase = js.phase; st.result = js.result or st.result; st.reason = js.reason or st.reason; if js.reason == "no_route" and js.detail then st.reason = "no_route:" .. tostring(js.detail) end end
        if okJ and type(js) == "table" and st.result == "arrived" and st.reason ~= "arrived" then st.result = "interrupted" end -- Sol patch: a drive released by an order is not an arrival
    end
    local veh = playerVehicle() or (s and call(s, "getVehicle"))
    if veh then
        local vx, vy = tonumber((call(veh, "getX"))), tonumber((call(veh, "getY")))
        if vx and G.dest then st.distance = math.floor(math.sqrt((vx - G.dest.x) ^ 2 + (vy - G.dest.y) ^ 2) + 0.5) end
        st.kmh = tonumber((call(veh, "getCurrentSpeedKmHour")))
        local gas = call(veh, "getPartById", "GasTank")
        local amt, cap = tonumber((call(gas, "getContainerContentAmount"))), tonumber((call(gas, "getContainerCapacity")))
        if amt and cap and cap > 0 then st.fuel = amt / cap end
    end
    st.inVehicle = veh ~= nil
    return st
end

-- Living Fellows' runtime normally ticks SC.Driving; if nothing ticks it while Sol drives, Sol does.
local lfTicks, lastSeen, lastOwnTick = 0, 0, 0
local function wrapTick()
    local SC = LF(); local D = SC and SC.Driving
    if not D or D.solTickWrapped or type(D.tick) ~= "function" then return end
    local orig = D.tick
    D.solTickOrig = orig
    D.tick = function(...) lfTicks = lfTicks + 1; return orig(...) end
    D.solTickWrapped = true
end

-- ---------------------------------------------------------------- Sol Mind channel (drive_to / stop from chat)
local lastId = 0
local function readRequest()
    local ok, r = pcall(getFileReader, REQ, false)
    if not ok or not r then return nil end
    local t, line = {}, r:readLine()
    while line ~= nil do local k, v = string.match(line, "^([^=]+)=(.*)$"); if k then t[k] = v end; line = r:readLine() end
    r:close()
    return t
end
local function writeState()
    local st = U.gpsStatus()
    local okw, w = pcall(getFileWriter, STATE, true, false)
    if not okw or not w then return end
    w:write("ack=" .. tostring(lastId) .. "\nresult=" .. tostring(st.result or "") .. "\nphase=" .. tostring(st.phase or "") ..
        "\nreason=" .. tostring(st.reason or "") .. "\ndistance=" .. tostring(st.distance or "") .. "\nspeed=" .. tostring(st.speed or "") ..
        "\ninVehicle=" .. tostring(st.inVehicle) .. "\nfuel=" .. tostring(st.fuel and math.floor(st.fuel * 100) or "") ..
        "\nsolo=" .. tostring(st.solo == true) .. "\n")
    w:close()
end
function U.gpsPollRequest()
    local r = readRequest()
    local id = r and tonumber(r.id) or 0
    if not G.pollPrimed then G.pollPrimed = true; if id > lastId then lastId = id end; return false end -- Sol patch: a request left in the file by an earlier session is not an order
    if id <= lastId then return false end
    lastId = id
    if r.action == "stop" then U.gpsStop()
    elseif r.action == "take_wheel" then U.gpsTakeWheel()
    else
        G.solo = r.solo == "1" or r.solo == "true"
        G.mustWaitPlayer = (type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("rescue_gps")) and (r.solo == "0" or r.solo == "false") or false   -- Sol fix 8
        if (type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("rescue_gps")) and r.car == "last" and G.lastDriveCar ~= nil and call(G.lastDriveCar, "getX") ~= nil then G.wheelCar = G.lastDriveCar end   -- Sol: back to her own car
        if r.target == "marker" then local m, why = U.gpsMapMarker(); if m then U.gpsSetDestination(m) elseif G.dest then G.reason = nil else G.lastResult, G.reason = "failed", why end
        elseif r.x and r.y and r.near == "1" and U.gpsNearestRoad then                                         -- beside the place, on the road: for a home with no parking marked
            local sx, sy = U.gpsNearestRoad(tonumber(r.x), tonumber(r.y))
            if sx then U.gpsSetDestination({ x = sx, y = sy, name = r.name }); log("near " .. tostring(r.x) .. "," .. tostring(r.y) .. ": the road at " .. sx .. "," .. sy)
            else U.gpsSetDestination({ x = tonumber(r.x), y = tonumber(r.y), name = r.name }) end
        elseif r.x and r.y then U.gpsSetDestination({ x = tonumber(r.x), y = tonumber(r.y), name = r.name }) end
        if G.dest and G.reason ~= "map_not_opened" and G.reason ~= "no_marker" then U.gpsStart(r.speed, G.solo) end
    end
    writeState()
    return true
end

-- ---------------------------------------------------------------- the GPS panel
local Panel = ISPanel:derive("SolGPS")
U.GPSClass = Panel
function Panel:new(x, y) local o = ISPanel:new(x, y, W, H); setmetatable(o, self); self.__index = self; o.background = false; return o end
local function tex(n) return getTexture("media/textures/SolUI/" .. n .. ".png") end
local function txt(ui, s, x, y, w, scale, align, c, a) T.drawLine(ui, s, x, y, w, { scale = scale, align = align or "right", r = c and c[1] or 0.94, g = c and c[2] or 0.96, b = c and c[3] or 0.98, a = a or 1 }) end
local PH_AR = { planning = "\\u062A\\u062E\\u0637\\u0637 \\u0627\\u0644\\u0637\\u0631\\u064A\\u0642", following = "\\u062A\\u0642\\u0648\\u062F", replanning = "\\u062A\\u0639\\u064A\\u062F \\u0627\\u0644\\u062A\\u062E\\u0637\\u064A\\u0637", blocked = "\\u0627\\u0644\\u0637\\u0631\\u064A\\u0642 \\u0645\\u0633\\u062F\\u0648\\u062F \\u2014 \\u062A\\u0646\\u062A\\u0638\\u0631", streaming_wait = "\\u062A\\u0646\\u062A\\u0638\\u0631 \\u062A\\u062D\\u0645\\u064A\\u0644 \\u0627\\u0644\\u0637\\u0631\\u064A\\u0642", arrived = "\\u0648\\u0635\\u0644\\u0646\\u0627", turning = "\\u062A\\u0633\\u062A\\u062F\\u064A\\u0631" }
local REASON_AR = {
    map_not_opened = "\\u0627\\u0641\\u062A\\u062D \\u0627\\u0644\\u062E\\u0631\\u064A\\u0637\\u0629 \\u0645\\u0631\\u0629 \\u0623\\u0648\\u0644\\u064B\\u0627\\u060C \\u0623\\u0648 \\u0627\\u062E\\u062A\\u0631 \\u0627\\u0644\\u0648\\u062C\\u0647\\u0629 \\u0628\\u0627\\u0644\\u0632\\u0631 \\u0627\\u0644\\u0623\\u064A\\u0645\\u0646 \\u0639\\u0644\\u064A\\u0647\\u0627",
    no_marker = "\\u0644\\u0627 \\u062A\\u0648\\u062C\\u062F \\u0639\\u0644\\u0627\\u0645\\u0629 \\u0639\\u0644\\u0649 \\u0627\\u0644\\u062E\\u0631\\u064A\\u0637\\u0629",
    not_in_vehicle = "\\u0644\\u0633\\u0646\\u0627 \\u0641\\u064A \\u0633\\u064A\\u0627\\u0631\\u0629",
    no_destination = "\\u0627\\u062E\\u062A\\u0631 \\u0648\\u062C\\u0647\\u0629 \\u0623\\u0648\\u0644\\u064B\\u0627",
    driving_unavailable = "\\u0627\\u0644\\u0642\\u064A\\u0627\\u062F\\u0629 \\u063A\\u064A\\u0631 \\u0645\\u062A\\u0627\\u062D\\u0629 \\u0627\\u0644\\u0622\\u0646",
    cannot_take_wheel = "\\u0644\\u0645 \\u0623\\u0633\\u062A\\u0637\\u0639 \\u0627\\u0644\\u062C\\u0644\\u0648\\u0633 \\u062E\\u0644\\u0641 \\u0627\\u0644\\u0645\\u0642\\u0648\\u062F",
    moving_to_wheel = "\\u0623\\u0646\\u062A\\u0642\\u0644 \\u0625\\u0644\\u0649 \\u0645\\u0642\\u0639\\u062F \\u0627\\u0644\\u0633\\u0627\\u0626\\u0642...",
    player_aboard = "\\u0627\\u0646\\u0632\\u0644 \\u0644\\u062D\\u0638\\u0629 \\u0644\\u0623\\u062C\\u0644\\u0633 \\u062E\\u0644\\u0641 \\u0627\\u0644\\u0645\\u0642\\u0648\\u062F\\u060C \\u062B\\u0645 \\u0627\\u0631\\u0643\\u0628 \\u0628\\u062C\\u0627\\u0646\\u0628\\u064A",
    board_passenger = "\\u0627\\u0631\\u0643\\u0628 \\u0645\\u0646 \\u0628\\u0627\\u0628 \\u0627\\u0644\\u0631\\u0627\\u0643\\u0628\\u060C \\u0648\\u0646\\u0646\\u0637\\u0644\\u0642",
    await_destination = "\\u0623\\u0646\\u0627 \\u062e\\u0644\\u0641 \\u0627\\u0644\\u0645\\u0642\\u0648\\u062f\\u060c \\u0642\\u0644 \\u0644\\u064a \\u0625\\u0644\\u0649 \\u0623\\u064a\\u0646 \\u0646\\u0630\\u0647\\u0628",
    no_vehicle_near = "\\u0644\\u0627 \\u062A\\u0648\\u062C\\u062F \\u0633\\u064A\\u0627\\u0631\\u0629 \\u0642\\u0631\\u064A\\u0628\\u0629",
    no_sol = "\\u0633\\u0648\\u0644 \\u0644\\u064A\\u0633\\u062A \\u0647\\u0646\\u0627",
    walking_to_door = "\\u0623\\u0645\\u0634\\u064A \\u0625\\u0644\\u0649 \\u0628\\u0627\\u0628 \\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629...",
    could_not_reach_door = "\\u0644\\u0645 \\u0623\\u0635\\u0644 \\u0625\\u0644\\u0649 \\u0628\\u0627\\u0628 \\u0627\\u0644\\u0633\\u064A\\u0627\\u0631\\u0629",
    player_is_driver = "\\u0623\\u0646\\u062A \\u0641\\u064A \\u0645\\u0642\\u0639\\u062F \\u0627\\u0644\\u0633\\u0627\\u0626\\u0642\\u060C \\u0627\\u0646\\u062A\\u0642\\u0644 \\u0625\\u0644\\u0649 \\u0627\\u0644\\u0645\\u0642\\u0639\\u062F \\u0627\\u0644\\u0645\\u062C\\u0627\\u0648\\u0631 \\u0644\\u0623\\u0642\\u0648\\u062F \\u0623\\u0646\\u0627",
    route_blocked = "\\u0627\\u0644\\u0637\\u0631\\u064A\\u0642 \\u0645\\u0633\\u062F\\u0648\\u062F \\u0648\\u0644\\u0645 \\u0623\\u062C\\u062F \\u0637\\u0631\\u064A\\u0642\\u0627\\u064B \\u0622\\u062E\\u0631",
    turn_failed = "\\u0644\\u0645 \\u0623\\u0633\\u062A\\u0637\\u0639 \\u0627\\u0644\\u0627\\u0633\\u062A\\u062F\\u0627\\u0631\\u0629 \\u0647\\u0646\\u0627",
    engine_failed = "\\u0627\\u0644\\u0645\\u062D\\u0631\\u0643 \\u0644\\u0627 \\u064A\\u0634\\u062A\\u063A\\u0644",
    streaming_stalled = "\\u0627\\u0644\\u062E\\u0631\\u064A\\u0637\\u0629 \\u0644\\u0645 \\u062A\\u062D\\u0645\\u0644 \\u0628\\u0639\\u062F",
    drive_already_owned = "\\u0623\\u0646\\u0627 \\u0623\\u0642\\u0648\\u062F \\u0627\\u0644\\u0622\\u0646\\u060C \\u0623\\u0648\\u0642\\u0641\\u0646\\u064A \\u0623\\u0648\\u0644\\u064B\\u0627",
}
local RS_AR = { failed = "\\u062A\\u0639\\u0630\\u0651\\u0631", stopped = "\\u062A\\u0648\\u0642\\u0641\\u062A", driving = "\\u062A\\u0642\\u0648\\u062F", arrived = "\\u0648\\u0635\\u0644\\u0646\\u0627" }
-- SolGPS map panel v3 (Sol 2026-10-25): the game's own world-map renderer (UIWorldMap, same init as vanilla ISMiniMap),
-- route drawn on top with worldToUI, pin + heading arrow icons, zoom/recentre buttons, click on the map to set the destination.
W, H = 340, 404
local MX, MY, MW, MH = 10, 34, 320, 262
local GREEN, RED, YELLOW, BLUE, MUTED, NAVY = { 0.18, 0.83, 0.39 }, { 0.94, 0.47, 0.43 }, { 0.95, 0.71, 0.19 }, { 0.29, 0.66, 1.0 }, { 0.62, 0.71, 0.78 }, { 0.05, 0.10, 0.14 }
local function ar(a, e) if isAr() then return a end return e end
local ROUTE_AR = {
    NO_ROAD_DATA = "\\u0644\\u0627 \\u062A\\u0648\\u062C\\u062F \\u0637\\u0631\\u0642 \\u0645\\u0633\\u062C\\u0644\\u0629 \\u0647\\u0646\\u0627",
    NO_ENTRY_CANDIDATE = "\\u0646\\u062D\\u0646 \\u0628\\u0639\\u064A\\u062F\\u0627\\u0646 \\u0639\\u0646 \\u0623\\u064A \\u0637\\u0631\\u064A\\u0642 \\u0645\\u0633\\u062C\\u0644",
    NO_EXIT_CANDIDATE = "\\u0627\\u0644\\u0648\\u062C\\u0647\\u0629 \\u0628\\u0639\\u064A\\u062F\\u0629 \\u0639\\u0646 \\u0623\\u064A \\u0637\\u0631\\u064A\\u0642 \\u0645\\u0633\\u062C\\u0644",
    NO_CONNECTED_ROUTE = "\\u0627\\u0644\\u0637\\u0631\\u0642 \\u063A\\u064A\\u0631 \\u0645\\u062A\\u0635\\u0644\\u0629 \\u062D\\u062A\\u0649 \\u0627\\u0644\\u0648\\u062C\\u0647\\u0629",
    BUDGET_EXCEEDED = "\\u0627\\u0644\\u0648\\u062C\\u0647\\u0629 \\u0628\\u0639\\u064A\\u062F\\u0629 \\u0639\\u0644\\u0649 \\u0627\\u0644\\u0645\\u062E\\u0637\\u0637\\u060C \\u0627\\u062E\\u062A\\u0631 \\u0648\\u062C\\u0647\\u0629 \\u0623\\u0642\\u0631\\u0628",
    DATA_NOT_READY = "\\u0628\\u064A\\u0627\\u0646\\u0627\\u062A \\u0627\\u0644\\u0637\\u0631\\u0642 \\u0644\\u0645 \\u062A\\u062D\\u0645\\u0644 \\u0628\\u0639\\u062F",
    INCOMPLETE_MAP_DATA = "\\u0628\\u064A\\u0627\\u0646\\u0627\\u062A \\u0627\\u0644\\u062E\\u0631\\u064A\\u0637\\u0629 \\u0646\\u0627\\u0642\\u0635\\u0629 \\u0647\\u0646\\u0627",
    NO_SAFE_ROAD_DETOUR = "\\u0644\\u0627 \\u064A\\u0648\\u062C\\u062F \\u0637\\u0631\\u064A\\u0642 \\u0622\\u0645\\u0646 \\u062D\\u0648\\u0644 \\u0627\\u0644\\u0639\\u0627\\u0626\\u0642",
}
G.preview = G.preview or {}
G.mapFollow = G.mapFollow ~= false
local function originPoint()
    local p = getSpecificPlayer and getSpecificPlayer(0)
    local v = playerVehicle() or (sol() and call(sol(), "getVehicle"))
    local o = v or sol() or p
    if not o then return nil end
    local x, y = tonumber((call(o, "getX"))), tonumber((call(o, "getY")))
    if not x or not y then return nil end
    return { x = x, y = y, z = 0 }
end
local function previewTick()
    local P = G.preview
    if not U.gpsPanel or not G.dest then P.route, P.reason, P.key, P.snap = nil, nil, nil, nil; return end
    local t = nowMs()
    local key = G.dest.x .. "," .. G.dest.y
    if P.key == key and P.at and t - P.at < 4000 then return end
    P.key, P.at = key, t
    local SC = LF(); local R = SC and SC.ExpeditionRoute
    local o = originPoint()
    if not R or type(R.planFromPoint) ~= "function" or not o then P.route, P.reason = nil, "planner_unavailable"; return end
    local ok, route, why = pcall(R.planFromPoint, o, { x = G.dest.x, y = G.dest.y, z = 0 }, true)
    P.snap = nil
    if P.lastLogged ~= key .. tostring(why) then P.lastLogged = key .. tostring(why); log("preview " .. key .. " -> " .. tostring(route and "route" or why)) end
    if ok and not route and tostring(why) == "NO_EXIT_CANDIDATE" and U.gpsNearestRoad then
        local sx, sy = U.gpsNearestRoad(G.dest.x, G.dest.y)
        log("road snap for " .. key .. " -> " .. tostring(sx) .. "," .. tostring(sy))
        if sx then P.snap = { x = sx, y = sy }; ok, route, why = pcall(R.planFromPoint, o, { x = sx, y = sy, z = 0 }, true) end
    end
    if ok and type(route) == "table" and type(route.points) == "table" and #route.points >= 2 then
        local last = route.points[#route.points]
        local gap = math.sqrt((last.x - G.dest.x) ^ 2 + (last.y - G.dest.y) ^ 2)
        if P.lastEnd ~= key then P.lastEnd = key; log(string.format("preview %s: from %.0f,%.0f, %d points, ends %.0f,%.0f, %.0f tiles short of the marker", key, o.x, o.y, #route.points, last.x, last.y, gap)) end
    end
    if ok and type(route) == "table" and type(route.points) == "table" and #route.points >= 2 then P.route, P.reason = route, nil
    else P.route, P.reason = nil, ok and tostring(why or "no_route") or "planner_error" end
end
if Events and Events.OnTick then Events.OnTick.Add(function() pcall(previewTick) end) end
local texCache = {}
local function icon(n) local t = texCache[n]; if t == nil then t = getTexture("media/textures/SolUI/" .. n .. ".png") or false; texCache[n] = t end; return t or nil end
local function routeLength(pts)
    local n = 0
    for i = 2, #pts do n = n + math.sqrt((pts[i].x - pts[i - 1].x) ^ 2 + (pts[i].y - pts[i - 1].y) ^ 2) end
    return n
end

-- ---------------------------------------------------------------- the map element
local MapEl = ISUIElement:derive("SolGPSMap")
function MapEl:new(x, y, w, h) local o = ISUIElement.new(self, x, y, w, h); o.zoomSet = false; return o end
function MapEl:instantiate()
    self.javaObject = UIWorldMap.new(self)
    self.mapAPI = self.javaObject:getAPIv3()
    self.mapAPI:setMapItem(MapItem.getSingleton())
    self.mapAPI:setMaxZoom(20)
    self.javaObject:setX(self.x); self.javaObject:setY(self.y)
    self.javaObject:setWidth(self.width); self.javaObject:setHeight(self.height)
    self.javaObject:setAnchorLeft(true); self.javaObject:setAnchorTop(true)
    local dirs = getLotDirectories()
    for i = 1, dirs:size() do
        local file = "media/maps/" .. dirs:get(i - 1) .. "/worldmap.xml"
        if fileExists(file) then self.mapAPI:addData(file) end
        self.mapAPI:endDirectoryData()
        self.mapAPI:addImages("media/maps/" .. dirs:get(i - 1))
    end
    self.mapAPI:setBoundsFromWorld()
    self.mapAPI:setZoom(17)
    self.mapAPI:setBoolean("HideUnvisited", true)
    self.mapAPI:setBoolean("Players", true)
    self.mapAPI:setBoolean("Symbols", false)
    self.mapAPI:setBoolean("MiniMapSymbols", true)
    self.mapAPI:setBoolean("ImagePyramid", false)
    MapUtils.initDefaultStyleV1(self)
    self:createChildren()
end
function MapEl:prerender()
    MapUtils.renderDarkModeOverlay(self)
    if G.mapFollow and not self.dragging then
        local o = originPoint(); if o then self.mapAPI:centerOn(o.x, o.y) end
    end
end
function MapEl:toUI(x, y) return self.mapAPI:worldToUIX(x, y), self.mapAPI:worldToUIY(x, y) end
function MapEl:dot(x, y, sz, c, a)
    if x < 1 or y < 1 or x > self.width - sz - 1 or y > self.height - sz - 1 then return end
    self:drawRect(x - sz / 2, y - sz / 2, sz, sz, a or 1, c[1], c[2], c[3])
end
function MapEl:line(ax, ay, bx, by, gap, sz, c, a)
    local dx, dy = bx - ax, by - ay
    local n = math.max(1, math.floor(math.sqrt(dx * dx + dy * dy) / gap))
    if n > 600 then n = 600 end
    for i = 0, n do self:dot(ax + dx * i / n, ay + dy * i / n, sz, c, a) end
end
function MapEl:render()
    local P, dest = G.preview or {}, G.dest
    local pts = P.route and P.route.points or nil
    if pts then
        local prev = nil
        for pass = 1, 2 do
            prev = nil
            for i = 1, #pts do
                local x, y = self:toUI(pts[i].x, pts[i].y)
                if prev then
                    if pass == 1 then self:line(prev[1], prev[2], x, y, 2, 7, NAVY, 0.9) else self:line(prev[1], prev[2], x, y, 2, 4, BLUE, 1) end
                end
                prev = { x, y }
            end
        end
    end
    local o = originPoint()
    if dest and P.snap then local ax, ay = self:toUI(P.snap.x, P.snap.y); local bx, by = self:toUI(dest.x, dest.y); self:line(ax, ay, bx, by, 8, 3, YELLOW, 0.9)
    elseif dest and not pts and o then local ax, ay = self:toUI(o.x, o.y); local bx, by = self:toUI(dest.x, dest.y); self:line(ax, ay, bx, by, 8, 3, YELLOW, 0.8)
    elseif dest and pts and (pts[#pts].x - dest.x) ^ 2 + (pts[#pts].y - dest.y) ^ 2 > 225 then local ax, ay = self:toUI(pts[#pts].x, pts[#pts].y); local bx, by = self:toUI(dest.x, dest.y); self:line(ax, ay, bx, by, 8, 3, YELLOW, 0.9) end
    if dest then
        local bx, by = self:toUI(dest.x, dest.y)
        bx, by = math.max(18, math.min(self.width - 18, bx)), math.max(44, math.min(self.height - 2, by))
        local t = icon("gps_pin"); if t then self:drawTexture(t, bx - 18, by - 44, 1, 1, 1, 1) end
    end
    if U.solMapDraw then pcall(U.solMapDraw, self, self.mapAPI) end
    -- Sol v2: the vehicle's arrow only while someone sits in a vehicle (it points the way the vehicle travels); the player's arrow shows the way his character faces
    local veh = playerVehicle() or (sol() and call(sol(), "getVehicle")) or nil
    if o and veh then
        local last = self.lastPos
        if not last or (o.x - last.x) ^ 2 + (o.y - last.y) ^ 2 > 0.25 then
            if last then       -- Sol: measured on the map as drawn; the map is tilted, so a world angle points the wrong way on it
                local ux0, uy0 = self:toUI(last.x, last.y)
                local ux1, uy1 = self:toUI(o.x, o.y)
                self.headingRad = math.atan2(uy1 - uy0, ux1 - ux0)
            end
            self.lastPos = { x = o.x, y = o.y }
        end
        if self.headingRad and SolTheme then
            local ax, ay = self:toUI(o.x, o.y)
            ax, ay = math.max(15, math.min(self.width - 15, ax)), math.max(15, math.min(self.height - 15, ay))
            SolTheme.arrow(self, ax, ay, 13, self.headingRad, SolTheme.c.green, SolTheme.c.bg)
        end
    else
        self.lastPos, self.headingRad = nil, nil
    end
    local pl = getSpecificPlayer and getSpecificPlayer(0)
    if pl and SolTheme and not playerVehicle() then
        local px, py = tonumber((call(pl, "getX"))), tonumber((call(pl, "getY")))
        if px and py then
            local ux, uy = self:toUI(px, py)
            if ux > 6 and uy > 6 and ux < self.width - 6 and uy < self.height - 6 then
                local h = math.pi / 4
                local DIRANG = { N = -2 * h, NE = -h, E = 0, SE = h, S = 2 * h, SW = 3 * h, W = 4 * h, NW = -3 * h }
                local dir = call(pl, "getDir")
                local name = dir ~= nil and tostring(dir) or nil
                if name then name = string.match(name, "(%u+)$") or name end
                local ang = name and DIRANG[name] or nil
                if ang == nil then
                    local fd = call(pl, "getForwardDirection")
                    ang = (fd ~= nil and type(fd.getX) == "function") and math.atan2(fd:getY(), fd:getX()) or 0
                end
                local ufx, ufy = self:toUI(px + math.cos(ang) * 4, py + math.sin(ang) * 4)      -- Sol: the same tilt as the vehicle's arrow
                ang = math.atan2(ufy - uy, ufx - ux)
                SolTheme.arrow(self, ux, uy, 9, ang, SolTheme.c.num, SolTheme.c.bg)
            end
        end
    end
    -- controls on the map's edges
    self.hits = {}
    local function pill(label, x, y, w, h, on, action, arg)
        self:drawRect(x, y, w, h, 0.92, on and 0.12 or NAVY[1], on and 0.48 or NAVY[2], on and 0.84 or NAVY[3])
        self:drawRectBorder(x, y, w, h, 0.9, 0.18, 0.56, 0.85)
        txt(self, label, x, y + 2, w, 0.42, "center")
        self.hits[#self.hits + 1] = { r = { x, y, w, h }, action = action, arg = arg }
    end
    pill(ar("\\u0633\\u0631\\u064A\\u0639", "Fast"), 8, 8, 48, 24, G.speed == "fast", "speed", "fast")
    pill(ar("\\u0645\\u062A\\u0648\\u0633\\u0637", "Normal"), 58, 8, 48, 24, G.speed == "normal", "speed", "normal")
    pill(ar("\\u0628\\u0637\\u064A\\u0621", "Slow"), 108, 8, 48, 24, G.speed == "slow", "speed", "slow")
    pill(ar("\\u0627\\u0644\\u0639\\u0644\\u0627\\u0645\\u0629", "Marker"), self.width - 84, 8, 76, 24, false, "marker")
    pill("+", self.width - 42, 42, 34, 34, false, "zoom", 1)
    pill("-", self.width - 42, 80, 34, 34, false, "zoom", -1)
    pill(ar("\\u0633\\u064A\\u0627\\u0631\\u062A\\u064A", "Car"), self.width - 58, 118, 50, 26, G.mapFollow, "follow")
    if not dest then
        self:drawRect(8, self.height - 32, 190, 24, 0.85, NAVY[1], NAVY[2], NAVY[3])
        txt(self, ar("\\u0627\\u0646\\u0642\\u0631 \\u0639\\u0644\\u0649 \\u0627\\u0644\\u062E\\u0631\\u064A\\u0637\\u0629 \\u0644\\u062A\\u062D\\u062F\\u064A\\u062F \\u0627\\u0644\\u0648\\u062C\\u0647\\u0629", "Click the map to set a destination"), 8, self.height - 30, 190, 0.4, "center", MUTED)
    end
end
function MapEl:onMouseWheel(del) self.mapAPI:zoomAt(self:getMouseX(), self:getMouseY(), del); return true end
function MapEl:onMouseDown(x, y)
    self.dragging, self.dragMoved, self.dragStartX, self.dragStartY = true, false, x, y
    self.dragStartCX, self.dragStartCY = self.mapAPI:getCenterWorldX(), self.mapAPI:getCenterWorldY()
    self.dragStartZoomF = self.mapAPI:getZoomF()
    self.dragStartWorldX, self.dragStartWorldY = self.mapAPI:uiToWorldX(x, y), self.mapAPI:uiToWorldY(x, y)
    return true
end
function MapEl:onMouseMove(dx, dy)
    if not self.dragging then return end
    local mx, my = self:getMouseX(), self:getMouseY()
    if not self.dragMoved and math.abs(mx - self.dragStartX) + math.abs(my - self.dragStartY) > 6 then self.dragMoved = true; G.mapFollow = false end
    if self.dragMoved then
        local wx = self.mapAPI:uiToWorldX(mx, my, self.dragStartZoomF, self.dragStartCX, self.dragStartCY)
        local wy = self.mapAPI:uiToWorldY(mx, my, self.dragStartZoomF, self.dragStartCX, self.dragStartCY)
        self.mapAPI:centerOn(self.dragStartCX + self.dragStartWorldX - wx, self.dragStartCY + self.dragStartWorldY - wy)
    end
    return true
end
function MapEl:onMouseMoveOutside(dx, dy) return self:onMouseMove(dx, dy) end
function MapEl:onMouseUpOutside(x, y) self.dragging = false end
function MapEl:onMouseUp(x, y)
    local moved = self.dragMoved
    self.dragging, self.dragMoved = false, false
    if moved then return true end
    for _, h in ipairs(self.hits or {}) do
        local r = h.r
        if x >= r[1] and y >= r[2] and x < r[1] + r[3] and y < r[2] + r[4] then
            local st = U.gpsStatus()
            if h.action == "speed" then G.speed = h.arg; local SCs = LF(); local Ds = SCs and SCs.Driving; if st and st.phase == "following" and Ds and Ds.setSpeed and sol() then pcall(Ds.setSpeed, sol(), SPEEDS[h.arg]) end
            elseif h.action == "marker" then local m, why = U.gpsMapMarker(); if m then U.gpsSetDestination(m); G.preview.at = nil else G.lastResult, G.reason = "failed", why end
            elseif h.action == "zoom" then self.mapAPI:setZoom(math.max(10, math.min(20, self.mapAPI:getZoomF() + h.arg)))
            elseif h.action == "follow" then G.mapFollow = true end
            return true
        end
    end
    local wx, wy = self.mapAPI:uiToWorldX(x, y), self.mapAPI:uiToWorldY(x, y)
    local stClick = wx and wy and U.gpsStatus() or {}
    local clickDriving = stClick.phase == "following" or stClick.phase == "planning" or stClick.phase == "replanning" or stClick.phase == "blocked" or stClick.phase == "streaming_wait"
    if wx and wy and U.gpsMapClick(wx, wy, clickDriving) == "cleared" then return true end
    if wx and wy then
        U.gpsSetDestination({ x = math.floor(wx), y = math.floor(wy), name = ar("\\u0646\\u0642\\u0637\\u0629 \\u0639\\u0644\\u0649 \\u0627\\u0644\\u062E\\u0631\\u064A\\u0637\\u0629", "Map point") })
        G.preview.at = nil
        local stc = U.gpsStatus(); local SCc = LF(); local Dc = SCc and SCc.Driving
        if stc and (stc.phase == "following" or stc.phase == "blocked") and Dc and Dc.setGoal and sol() and G.dest then pcall(Dc.setGoal, sol(), { x = G.dest.x, y = G.dest.y, z = 0 }) end
    end
    return true
end

-- ---------------------------------------------------------------- the panel around it
function Panel:createChildren()
    self.map = MapEl:new(MX, MY, MW, MH)
    self.map:initialise()
    self:addChild(self.map)
end
function Panel:prerender()
    local st = U.gpsStatus(); self.st = st
    local t = tex("pg_btn"); if t then self:drawTextureScaled(t, 0, 0, W, H, 0.97, 1, 1, 1) end
    self:drawRectBorder(0, 0, W, H, 1, 0.16, 0.56, 0.85)
    local driving = st.phase == "following" or st.phase == "planning" or st.phase == "replanning" or st.phase == "blocked" or st.phase == "streaming_wait"
    local failed = st.result == "failed"
    local dc = failed and RED or (driving and GREEN or BLUE)
    self:drawRect(14, 12, 10, 10, 1, dc[1], dc[2], dc[3])
    txt(self, "GPS  " .. ar("\\u0633\\u0648\\u0644", "Sol"), 10, 6, W - 20, 0.56, "right", BLUE)
    self:drawRectBorder(MX - 1, MY - 1, MW + 2, MH + 2, 1, 0.16, 0.56, 0.85)
    if st.fuel then
        local fc = st.fuel < 0.2 and RED or (st.fuel < 0.4 and YELLOW or GREEN)
        self:drawRect(MX, MY + MH + 2, MW, 3, 1, 0.05, 0.12, 0.18)
        self:drawRect(MX, MY + MH + 2, MW * math.min(1, st.fuel), 3, 1, fc[1], fc[2], fc[3])
    end
    local P, dest = G.preview or {}, G.dest
    local pts = P.route and P.route.points or nil
    local meters = pts and routeLength(pts) or st.distance
    local info = ""
    if meters then
        local kmh = math.max(5, tonumber(SPEEDS and SPEEDS[G.speed]) or 20)
        info = string.format("%.1f", meters / 1000) .. ar(" \\u0643\\u0645", " km") .. "  " .. math.max(1, math.floor(meters / 1000 / kmh * 60 + 0.5)) .. ar(" \\u062F", " min")
    end
    txt(self, info, 10, MY + MH + 10, W - 20, 0.5, "right")
    local side = (st.kmh and (math.floor(math.abs(st.kmh) + 0.5) .. " km/h") or "") .. (st.fuel and ("   " .. ar("\\u0627\\u0644\\u0648\\u0642\\u0648\\u062F ", "Fuel ") .. math.floor(st.fuel * 100) .. "%") or "")
    txt(self, side, 10, MY + MH + 12, 200, 0.42, "left", MUTED)
    local state = (st.phase and PH_AR[st.phase]) or (st.result and RS_AR[st.result]) or ""
    if not isAr() then state = tostring(st.phase or st.result or "") end
    local sc = GREEN
    if st.reason and failed then
        local rs = tostring(st.reason)
        local base, det = rs:match("^([^:]+)"), rs:match(":(.+)$")
        local r = isAr() and (ROUTE_AR[det or ""] or REASON_AR[base or ""])
        state, sc = r or (state .. ": " .. rs), RED
    elseif not driving and dest and P.reason then
        state, sc = (isAr() and ROUTE_AR[P.reason]) or ("no_route: " .. P.reason), YELLOW
    elseif not driving and dest and pts and P.snap then
        state, sc = ar("\\u0627\\u0644\\u0639\\u0644\\u0627\\u0645\\u0629 \\u062E\\u0627\\u0631\\u062C \\u0627\\u0644\\u0637\\u0631\\u0642\\u060C \\u0633\\u0623\\u0642\\u0648\\u062F \\u0625\\u0644\\u0649 \\u0623\\u0642\\u0631\\u0628 \\u0637\\u0631\\u064A\\u0642 \\u0645\\u0646\\u0647\\u0627", "Marker is off-road: driving to the nearest road"), YELLOW
    elseif not driving and dest and pts and (pts[#pts].x - dest.x) ^ 2 + (pts[#pts].y - dest.y) ^ 2 > 225 then
        state, sc = ar("\\u0627\\u0644\\u0637\\u0631\\u064A\\u0642 \\u0628\\u064A\\u0648\\u0642\\u0641 \\u0642\\u0628\\u0644 \\u0627\\u0644\\u0639\\u0644\\u0627\\u0645\\u0629", "The road stops short of the marker"), YELLOW
    elseif not driving and dest and pts then
        state, sc = ar("\\u0627\\u0644\\u0637\\u0631\\u064A\\u0642 \\u062C\\u0627\\u0647\\u0632\\u060C \\u0627\\u0636\\u063A\\u0637 \\u0642\\u0648\\u062F\\u064A", "Route ready - press Drive"), BLUE
    end
    txt(self, state, 10, MY + MH + 36, W - 20, 0.44, "right", sc)
    self.hits = {}
    self:drawRect(34, 8, 26, 20, 0.9, NAVY[1], NAVY[2], NAVY[3]); self:drawRectBorder(34, 8, 26, 20, 0.9, 0.18, 0.56, 0.85)
    txt(self, "-", 34, 8, 26, 0.5, "center")
    self.hits[#self.hits + 1] = { r = { 34, 8, 26, 20 }, action = "collapse" }
    if dest then
        self:drawRect(66, 8, 60, 20, 0.9, 0.45, 0.14, 0.12); self:drawRectBorder(66, 8, 60, 20, 0.9, 0.95, 0.6, 0.55)
        txt(self, ar("\\u0625\\u0644\\u063A\\u0627\\u0621", "Clear"), 66, 8, 60, 0.46, "center")
        self.hits[#self.hits + 1] = { r = { 66, 8, 60, 20 }, action = "clear" }
    end
    local by, bh = H - 46, 36
    local half = (W - 28) / 2
    self:drawRect(W - 10 - half, by, half, bh, 1, 0.10, 0.50, 0.30)
    self:drawRectBorder(W - 10 - half, by, half, bh, 1, 0.5, 0.9, 0.7)
    txt(self, ar("\\u0633\\u0648\\u0642\\u064A", "Drive"), W - 10 - half, by + 5, half, 0.56, "center")
    self.hits[#self.hits + 1] = { r = { W - 10 - half, by, half, bh }, action = "drive" }
    self:drawRect(10, by, half, bh, 1, 0.55, 0.16, 0.14)
    self:drawRectBorder(10, by, half, bh, 1, 0.95, 0.6, 0.55)
    txt(self, ar("\\u0648\\u0642\\u0641\\u064A", "Stop"), 10, by + 5, half, 0.56, "center")
    self.hits[#self.hits + 1] = { r = { 10, by, half, bh }, action = "stop" }
end
function Panel:onMouseUp(x, y)
    self.drag = nil
    for _, h in ipairs(self.hits or {}) do
        local r = h.r
        if x >= r[1] and y >= r[2] and x < r[1] + r[3] and y < r[2] + r[4] then
            local st = self.st or {}
            local busy = st.phase == "following" or st.phase == "planning" or st.phase == "replanning" or st.phase == "blocked" or st.phase == "streaming_wait"
            if h.action == "drive" then
                if not busy then U.gpsStart(nil, false) end
            elseif h.action == "stop" then U.gpsStop()
            elseif h.action == "clear" then U.gpsClear()
            elseif h.action == "collapse" then
                G.collapsed = true
                if U.gpsIcon then U.gpsIcon:setX(self:getX() + W - 52); U.gpsIcon:setY(self:getY()) end
            end
            return true
        end
    end
    return true
end
-- Sol v3: the window is dragged by the mouse's position on the SCREEN (captured), so it can never be left behind
local function panelMouseAbs()
    if Mouse and Mouse.getXA and Mouse.getYA then return Mouse.getXA(), Mouse.getYA() end
    return nil, nil
end
function Panel:onMouseDown(x, y)
    local mx, my = panelMouseAbs()
    self.drag = { x, y, mx = mx, my = my, sx = self:getX(), sy = self:getY() }
    if type(self.setCapture) == "function" then self:setCapture(true) end
    return true
end
do
    local origUp = Panel.onMouseUp
    function Panel:onMouseUp(x, y)
        if type(self.setCapture) == "function" then self:setCapture(false) end
        return origUp(self, x, y)
    end
end
function Panel:onMouseUpOutside(x, y) return self:onMouseUp(x, y) end

-- ---------------------------------------------------------------- floating icon + when the GPS shows
local Icon = ISPanel:derive("SolGPSIcon")
function Icon:new(x, y) local o = ISPanel:new(x, y, 52, 52); setmetatable(o, self); self.__index = self; o.background = false; return o end
function Icon:prerender()
    local st = U.gpsStatus()
    local driving = st.phase == "following" or st.phase == "planning" or st.phase == "replanning" or st.phase == "blocked" or st.result == "driving"
    local c = (st.result == "failed") and RED or (driving and GREEN or BLUE)
    if SolTheme then SolTheme.disc(self, 26, 26, 25, NAVY, 0.96, c, 1)
    else self:drawRect(0, 0, 52, 52, 0.95, NAVY[1], NAVY[2], NAVY[3]) end
    txt(self, "GPS", 0, 12, 52, 0.5, "center", BLUE)
    txt(self, st.kmh and tostring(math.floor(math.abs(st.kmh) + 0.5)) or "-", 0, 30, 52, 0.46, "center")
end
-- dragging: the mouse is captured and the position is the start position plus how far the mouse has moved on the SCREEN, so the icon cannot be left behind
local function mouseAbs()
    if Mouse and Mouse.getXA and Mouse.getYA then return Mouse.getXA(), Mouse.getYA() end
    return nil, nil
end
function Icon:onMouseDown(x, y)
    local mx, my = mouseAbs()
    self.press = { x = x, y = y, mx = mx, my = my, sx = self:getX(), sy = self:getY(), moved = false }
    if type(self.setCapture) == "function" then self:setCapture(true) end
    return true
end
function Icon:onMouseMove()
    local p = self.press
    if not p or not (isMouseButtonDown and isMouseButtonDown(0)) then return end
    local mx, my = mouseAbs()
    local absolute = mx ~= nil and p.mx ~= nil
    local dx, dy
    if absolute then dx, dy = mx - p.mx, my - p.my else dx, dy = self:getMouseX() - p.x, self:getMouseY() - p.y end
    if math.abs(dx) + math.abs(dy) > 4 then p.moved = true end
    if p.moved then
        if absolute then self:setX(p.sx + dx); self:setY(p.sy + dy)
        else self:setX(self:getX() + dx); self:setY(self:getY() + dy) end
    end
end
function Icon:onMouseMoveOutside() return self:onMouseMove() end
function Icon:onMouseUpOutside(x, y) return self:onMouseUp(x, y) end
function Icon:onMouseUp(x, y)
    local p = self.press; self.press = nil
    if type(self.setCapture) == "function" then self:setCapture(false) end
    if p and not p.moved then
        G.collapsed = false; G.openedAt = getTimestampMs and getTimestampMs() or 0
        if U.gpsPanel then
            U.gpsPanel:setX(math.max(0, math.min(getCore():getScreenWidth() - W, self:getX() + 52 - W)))
            U.gpsPanel:setY(math.max(0, self:getY()))
        end
    end
    return true
end

-- the GPS is offered whenever the player is in a vehicle with Sol around, or Sol herself is at the wheel
function U.gpsShouldShow()
    local s = sol()
    if not s then return false end
    if playerVehicle() ~= nil then return true end
    local SC = LF(); local D = SC and SC.Driving
    if D and D.isDriver then local ok, d = pcall(D.isDriver, s); if ok and d then return true end end
    return false
end
function U.gpsApplyVisibility()
    local inCar = U.gpsShouldShow()
    local now = getTimestampMs and getTimestampMs() or 0
    if inCar ~= G.lastInCar then G.lastInCar = inCar; G.collapsed = not inCar; G.openedAt = now end -- Sol patch 2026-10-26
    if G.collapsed == false and not inCar then
        local busy = G.lastResult == "driving" or G.doorWalk ~= nil or G.wheelWaitSince ~= nil or G.awaitPlayer == true
        if busy then G.openedAt = now elseif now - (G.openedAt or now) > 30000 then G.collapsed = true end
    end
    local show = true
    if show and not U.gpsPanel then
        U.gpsPanel = Panel:new(getCore():getScreenWidth() - W - 20, 120)
        U.gpsPanel:initialise(); U.gpsPanel:instantiate(); U.gpsPanel:addToUIManager()
    end
    if show and not U.gpsIcon then
        U.gpsIcon = Icon:new(getCore():getScreenWidth() - 72, 120)
        U.gpsIcon:initialise(); U.gpsIcon:instantiate(); U.gpsIcon:addToUIManager()
    end
    if U.gpsPanel then U.gpsPanel:setVisible(show and not G.collapsed) end
    if U.gpsIcon then U.gpsIcon:setVisible(show and G.collapsed == true) end
end


function Panel:onMouseMove()
    local d = self.drag
    if not d or not (isMouseButtonDown and isMouseButtonDown(0)) then return end
    local mx, my = panelMouseAbs()
    local x, y
    if mx and d.mx then x, y = d.sx + mx - d.mx, d.sy + my - d.my
    else x, y = self:getX() + self:getMouseX() - d[1], self:getY() + self:getMouseY() - d[2] end
    local sw, sh = getCore():getScreenWidth(), getCore():getScreenHeight()
    self:setX(math.max(0, math.min(sw - self.width, x))); self:setY(math.max(0, math.min(sh - self.height, y)))
end
function Panel:onMouseMoveOutside() return self:onMouseMove() end

-- shown automatically while the player sits in a vehicle (and Sol exists)
local last = 0
local function onTick()
    local t = nowMs()
    wrapTick()
    -- if nobody else ticks LF driving while Sol drives, tick it here
    local SC = LF(); local D = SC and SC.Driving
    if D and D.solTickOrig and G.lastResult == "driving" and t - lastOwnTick >= 250 then
        if lfTicks == lastSeen then pcall(D.solTickOrig, t) end
        lastSeen, lastOwnTick = lfTicks, t
    end
    if t - last < 1000 then return end
    last = t
    pcall(U.gpsPollRequest)
    local w = G.doorWalk
    if w and sol() then
        G.doorTriesAt = t       -- still walking: the minute's budget is not "quiet"
        local s0 = sol()
        local x0, y0 = tonumber((call(s0, "getX"))) or 0, tonumber((call(s0, "getY"))) or 0
        local ddx, ddy = x0 - w.x, y0 - w.y
        local ready = solDoorReady(s0)
        local step = solDoorStep(w, x0, y0, ddx, ddy, ready, t)
        if step == "board" or (step == "stopped" and not solThreatNear()) then
            log("door walk: " .. step .. " ready=" .. tostring(ready) .. string.format(" at %.1f,%.1f, %.1f from the square", x0, y0, math.sqrt(ddx * ddx + ddy * ddy)))
            G.doorWalk = nil
            if G.dest then pcall(U.gpsStart) else pcall(U.gpsTakeWheel) end
        elseif solThreatPause(w) then
            -- a zombie is near: nothing is sent, the budget is paused
        elseif t - w.since > DOOR_WALK_BUDGET_MS then
            G.doorWalk, G.doorWalkFrom = nil, nil; G.lastResult, G.reason = "failed", "could_not_reach_door"
            if U.issueLF then pcall(U.issueLF, "follow") end                     -- not left standing under the walk order
        elseif t - w.lastAsk > 1500 and t - w.movedAt > 1200 and U.solGoto then
            w.lastAsk = t
            do                                                                   -- why she stands still is not in the logs yet: this line settles it
                local SCn, okP, peek = LF(), false, nil
                local nav = SCn and SCn.Navigation
                if nav and type(nav.peek) == "function" then okP, peek = pcall(nav.peek, s0) end
                local navText = "none"
                if okP and type(peek) == "table" then navText = tostring(peek.status or peek.state or peek.action or "active")
                elseif okP and peek ~= nil then navText = tostring(peek) end
                log(string.format("door walk stalled at %.1f,%.1f for %d ms, nav=%s", x0, y0, math.floor(t - w.movedAt), navText))
            end
            local SC0 = LF(); if SC0 and SC0.Decision and type(SC0.Decision.cancelWork) == "function" then pcall(SC0.Decision.cancelWork, s0, "sol_gps") end
            local okr, whyr = U.solGoto(w.x, w.y)
            if okr ~= true and orderMustWait(whyr) then yieldDowntime(s0, whyr); w.lastAsk = t - ORDER_WAIT_LAST_ASK        -- still busy: ask again in a moment
            elseif okr ~= true then G.doorWalk = nil; pcall(U.gpsTakeWheel) end        -- refused: a fresh walk to the next square
        end
    end
    if G.doorRetryAt and t >= G.doorRetryAt then
        G.doorRetryAt = nil
        if G.dest then pcall(U.gpsStart) else pcall(U.gpsTakeWheel) end
    end
    -- refused while the player was aboard: as soon as the player is out, carry on by itself
    if G.retryWhenOut and not playerVehicle() then
        G.retryWhenOut = false
        if G.dest then pcall(U.gpsStart) else pcall(U.gpsTakeWheel) end
    end
    -- She stepped out of her passenger seat: now enter seat zero through the
    -- verified transaction and arm native ownership before the player boards.
    if G.wheelWaitSince and sol() and not call(sol(), "getVehicle") then
        G.wheelWaitSince = nil
        if G.dest then pcall(U.gpsStart) else pcall(U.gpsTakeWheel) end
    elseif G.wheelWaitSince and t - G.wheelWaitSince > 30000 then
        G.wheelWaitSince = nil; G.lastResult, G.reason = "failed", "cannot_take_wheel"
        log("could not leave the passenger seat in 30 s: " .. tostring(G.wheelExitWhy))
    elseif G.wheelWaitSince and t >= (G.wheelExitNext or 0) and sol() then
        solLeaveSeat(sol())
    end
    if G.awaitPlayer and G.dest then
        local pv, s = playerVehicle(), sol()
        if pv and s and pv == call(s, "getVehicle") then G.awaitPlayer = false; pcall(U.gpsStart) end
    end
    local inVeh = U.gpsShouldShow and U.gpsShouldShow() or false
    if U.gpsApplyVisibility then pcall(U.gpsApplyVisibility) end
    -- Sol patch 2026-10-26: panel follows G.collapsed only
    if G.lastResult then
        local st = U.gpsStatus()
        local sig = tostring(st.result) .. tostring(st.phase) .. tostring(st.distance and math.floor(st.distance / 5)) .. tostring(st.reason)
        if sig ~= G.lastSig then G.lastSig = sig; pcall(writeState) end
    end
end
-- the world map's own right-click menu (ISWorldMap.lua 907: onRightMouseUp builds it, mapAPI:uiToWorldX/Y)
-- gets a Sol walk action. Driving destinations are selected on GPS and started from the GPS panel.
function U.gpsMapChoose(wx, wy, mode)
    G.solo = false
    G.mustWaitPlayer = false
    local dest = { x = math.floor(wx), y = math.floor(wy), name = (isAr() and "\\u0646\\u0642\\u0637\\u0629 \\u0639\\u0644\\u0649 \\u0627\\u0644\\u062E\\u0631\\u064A\\u0637\\u0629" or "Map point") }
    U.gpsSetDestination(dest)
    if G.preview then G.preview.at = nil end
    if mode == "walk" then
        if U.solGoto then return U.solGoto(dest.x, dest.y, 0) end
        return false, "walking_unavailable"
    end
    return true, "destination_selected"
end
local function hookMap()
    if not ISWorldMap or ISWorldMap.solHooked or type(ISWorldMap.onRightMouseUp) ~= "function" then return end
    if type(ISWorldMap.render) == "function" then
        local origRender = ISWorldMap.render
        ISWorldMap.render = function(self, ...)
            local r = origRender(self, ...)
            if U.solMapDraw and self.mapAPI then pcall(U.solMapDraw, self, self.mapAPI) end
            return r
        end
    end
    local orig = ISWorldMap.onRightMouseUp
    ISWorldMap.onRightMouseUp = function(self, x, y)
        local r = orig(self, x, y)
        local ok = pcall(function()
            local api = self.mapAPI
            local wx, wy = api:uiToWorldX(x, y), api:uiToWorldY(x, y)
            local pn = 0
            local menu = getPlayerContextMenu and getPlayerContextMenu(pn)
            if not (menu and menu.isVisible and menu:isVisible() and menu.numOptions and menu.numOptions > 1) then
                menu = ISContextMenu.get(pn, x + self:getAbsoluteX(), y + self:getAbsoluteY())
            end
            -- Select the map destination here, then start driving with the
            -- GPS panel's Drive control; do not add a second direct-drive action.
            menu:addOption("\\u0633\\u0648\\u0644: \\u0627\\u0645\\u0634\\u064A \\u0644\\u0647\\u0648\\u0646", self, function() U.gpsMapChoose(wx, wy, "walk") end)
        end)
        return r
    end
    ISWorldMap.solHooked = true
end
U.gpsHookMap = hookMap
if Events and Events.OnGameStart then Events.OnGameStart.Add(hookMap) end
pcall(hookMap)

if Events and Events.OnTick then Events.OnTick.Add(onTick) end
U.gpsTick = onTick
log("ready v" .. U.GPS_VERSION)


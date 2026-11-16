"""The full review of 2026-11-09 (DOCS/SOL_REVIEW_20261109.md). Run only with the game closed. All or nothing: every edit is checked first, then every file is written.
usage: apply_s39_lua.py <client dir>"""
import os, sys
D = sys.argv[1]
EDITS = {}
def E(f, a, b): EDITS.setdefault(f, []).append((a, b))

# ---- what the game's Lua does not have
E("SCExpeditionPrototype.lua", "                if next(responders) then\n",
  "                local anyResponder = false                       -- the game's Lua has no next()\n                for _ in pairs(responders) do anyResponder = true; break end\n                if anyResponder then\n")
E("SCProduction.lua", "    -- A blocked/cancelled attempt must not strand a borrowed shovel in the\n",
  "    local function solFirstKey(t) for k in pairs(t) do return k end return nil end   -- the game's Lua has no next()\n    -- A blocked/cancelled attempt must not strand a borrowed shovel in the\n")
E("SCProduction.lua", "        and next(state.borrowedTools) ~= nil then\n        local key = next(state.borrowedTools)\n",
  "        and solFirstKey(state.borrowedTools) ~= nil then\n        local key = solFirstKey(state.borrowedTools)\n")
E("SCFactionLife.lua", """        local relation = group.life.relationships[memberPairKey(active.left, active.right)]
        if relation then
            local discipline = tonumber(group.life.personality.values.discipline) or 50
""", """        local relation = group.life.relationships[memberPairKey(active.left, active.right)]
        local discipline = tonumber(group.life.personality.values.discipline) or 50
        if relation then
""")
E("SolBypass.lua", "local function bin(th) return math.floor(((th % (2 * math.pi)) / (2 * math.pi)) * ARC_BINS + 0.5) % ARC_BINS end",
  "local function bin(th) local tau = 2 * math.pi; local a = ((th % tau) + tau) % tau; return math.floor((a / tau) * ARC_BINS + 0.5) % ARC_BINS end   -- the game's % keeps the sign of th")

# ---- boarding: a car that left the world, and the seat rule
E("SCVehicle.lua", "local function availableSeat(vehicle, identity, seat, actorId)\n",
  """-- A car whose chunk has unloaded still answers some calls, and sitting in it corrupts the saved car (NPE VehiclesDB2, 2026-11-09 10:38).
local function goneFromWorld(vehicle)
    local ok, removed = invoke(vehicle, "isRemovedFromWorld")
    return ok and removed == true
end

local function availableSeat(vehicle, identity, seat, actorId)
""")
E("SCVehicle.lua", """    if identity == nil then return nil, "vehicle identity is unavailable" end
    local stopped, stoppedReason = stationary(vehicle)
""", """    if identity == nil then return nil, "vehicle identity is unavailable" end
    if goneFromWorld(vehicle) then return nil, "vehicle is not in the loaded world" end
    local stopped, stoppedReason = stationary(vehicle)
""")
E("SCVehicle.lua", """    if identity == nil then return nil, nil, "vehicle identity is unavailable" end
    local seat, reason = chooseSeat(vehicle, actor, requestedSeat, identity,
        allowDriver == true)
""", """    if identity == nil then return nil, nil, "vehicle identity is unavailable" end
    if goneFromWorld(vehicle) then return nil, nil, "vehicle is not in the loaded world" end
    local seat, reason = chooseSeat(vehicle, actor, requestedSeat, identity,
        allowDriver == true)
""")
E("SCVehicle.lua", """    if identity == nil then return nil, "vehicle identity is unavailable" end
    local seat, reason = chooseSeat(vehicle, actor, requestedSeat, identity,
        intent.driverSeat == true)
""", """    if identity == nil then return nil, "vehicle identity is unavailable" end
    if goneFromWorld(vehicle) then return nil, "vehicle is not in the loaded world" end
    local seat, reason = chooseSeat(vehicle, actor, requestedSeat, identity,
        intent.driverSeat == true)
""")
E("SCVehicle.lua", """    if identity == nil or id == nil then return nil, "vehicle or companion identity is unavailable" end
    local seatOk, fromSeat = invoke(vehicle, "getSeat", actor)
""", """    if identity == nil or id == nil then return nil, "vehicle or companion identity is unavailable" end
    if goneFromWorld(vehicle) then return nil, "vehicle is not in the loaded world" end
    local seatOk, fromSeat = invoke(vehicle, "getSeat", actor)
""")
E("SCVehicle.lua", """    local actorX, actorY = coordinates(actor)
    local best, bestDistance
    for seat = 1, count - 1 do
        if (not onlyFront or seat == 1)
            and availableSeat(vehicle, identity, seat, actorId) then
            local distance = actorX and doorDistanceSquared(vehicle, seat, actorX, actorY) or nil
            if best == nil or (distance ~= nil and (bestDistance == nil or distance < bestDistance)) then
                best, bestDistance = seat, distance
            end
        end
    end
    if best == nil then return nil, "vehicle has no available passenger seat" end
    return best
end
""", """    -- the rule: the first free passenger seat, every time; the driver's seat only on a driving order (above)
    for seat = 1, count - 1 do
        if (not onlyFront or seat == 1)
            and availableSeat(vehicle, identity, seat, actorId) then
            return seat
        end
    end
    return nil, "vehicle has no available passenger seat"
end
""")

# ---- driving
E("SCDriving.lua", "function Driving.jobStatus(actor)\n", "function Driving.clearOutcome(actor) outcomes[actor] = nil end       -- a new attempt must not be answered by the last trip's ending\n\nfunction Driving.jobStatus(actor)\n")
E("SCDriving.lua", """        print("[SolDrive] no key for this car")
        Driving.stop(job.actor, "no_key")
""", """        print("[SolDrive] no key for this car")
        local hw = SC.VehicleHotwire                                             -- no key anywhere: the game's own hotwire job, if her skills allow it
        if type(hw) == "table" and type(hw.canHotwire) == "function" and type(hw.request) == "function" then
            local okC, can = pcall(hw.canHotwire, job.actor)
            if okC and can == true then
                local okH, started, whyH = pcall(hw.request, job.actor, job.vehicle, localPlayer())
                print("[SolDrive] hotwire -> " .. tostring(okH and started) .. " " .. tostring(okH and whyH or started))
                if okH and started == true then
                    Driving.stop(job.actor, "hotwiring")
                    return false, "hotwiring"
                end
            end
        end
        Driving.stop(job.actor, "no_key")
""")
E("SolGPS.lua", "local function nearestCar()\n", """-- she sits in a car that has left the loaded world: nothing may be done with that car
local function seatedInGoneCar(s)
    local inside = call(s, "getVehicle")
    if inside == nil or carStillLoaded(inside) then return false end
    log("she is seated in a car that is no longer in the loaded world")
    G.wheelCar, G.lastResult, G.reason = nil, "failed", "no_vehicle_near"
    return true
end
local function nearestCar()
""")
E("SolGPS.lua", """    local s = sol(); if not s then G.lastResult, G.reason = "failed", "no_sol"; return false, G.reason end
    if D.isDriver and D.isDriver(s) then log("takeWheel: already at the wheel"); return prepareDriver(D, s) end
""", """    local s = sol(); if not s then G.lastResult, G.reason = "failed", "no_sol"; return false, G.reason end
    if seatedInGoneCar(s) then return false, G.reason end
    if type(D.clearOutcome) == "function" then D.clearOutcome(s) end
    if D.isDriver and D.isDriver(s) then log("takeWheel: already at the wheel"); return prepareDriver(D, s) end
""")
E("SolGPS.lua", """    if speedKey and SPEEDS[speedKey] then G.speed = speedKey end
    if soloMode ~= nil then G.solo = soloMode == true end

""", """    if speedKey and SPEEDS[speedKey] then G.speed = speedKey end
    if soloMode ~= nil then G.solo = soloMode == true end
    if seatedInGoneCar(s) then return false, G.reason end

""")
E("SolGPS.lua", "G.wheelCar, G.leaveSeatCount, G.wheelWaitSince = inside, 0, nil", "G.wheelCar, G.leaveSeatCount, G.wheelWaitSince = nil, 0, nil")
E("SolGPS.lua", "    G.wheelCar, G.doorWalkFrom = veh, nil\n    return prepareDriver(D, s)", "    G.wheelCar, G.doorWalkFrom = nil, nil                 -- she is in it: the next trip chooses afresh\n    return prepareDriver(D, s)")
E("SolGPS.lua", "-- Once armed, the player can board as passenger and the prepared job is promoted\n", """-- sitting or lounging holds the body for as long as it likes, and he has just told her to go
local function yieldDowntime(s, reason)
    if type(reason) ~= "string" or string.find(reason, "action_owned:downtime:", 1, true) ~= 1 then return end
    local SC = LF()
    if SC and type(SC.Downtime) == "table" and type(SC.Downtime.cancel) == "function" then pcall(SC.Downtime.cancel, s, "sol_gps") end
end

-- Once armed, the player can board as passenger and the prepared job is promoted
""")
E("SolGPS.lua", "            if okw ~= true and orderMustWait(whyw) then        -- she is finishing something short: no other square helps, and no door try is spent\n",
  "            if okw ~= true and orderMustWait(whyw) then        -- she is finishing something short: no other square helps, and no door try is spent\n                yieldDowntime(s, whyw)\n")
E("SolGPS.lua", "if okr ~= true and orderMustWait(whyr) then w.lastAsk = t - ORDER_WAIT_LAST_ASK", "if okr ~= true and orderMustWait(whyr) then yieldDowntime(s0, whyr); w.lastAsk = t - ORDER_WAIT_LAST_ASK")
E("SolGPS.lua", """G.doorWalk, G.doorWalkFrom = nil, nil; G.lastResult, G.reason = "failed", "could_not_reach_door"
""", """G.doorWalk, G.doorWalkFrom = nil, nil; G.lastResult, G.reason = "failed", "could_not_reach_door"
            if U.issueLF then pcall(U.issueLF, "follow") end                     -- not left standing under the walk order
""")
E("SolGPS.lua", """        elseif t - w.lastAsk > 1500 and t - w.movedAt > 1200 and U.solGoto then
            w.lastAsk = t
""", """        elseif t - w.lastAsk > 1500 and t - w.movedAt > 1200 and U.solGoto then
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
""")
E("SolOrders.lua", """                endToken(job); job = nil; releaseGps(false)
            end
            return f(rowId, command, ...)
""", """                endToken(job); job = nil; releaseGps(false)
            elseif not job and not O._own and USER_ORDERS[command] and command ~= "move_to" and command ~= "board_vehicle" then
                local g = G()                                                    -- the door walk is not a job: his order has to end it too (its own step is a move_to)
                if g and g.doorWalk then
                    log("the order " .. tostring(command) .. " ends the walk to the car")
                    g.doorRetryAt = nil
                    releaseGps(false)
                end
            end
            return f(rowId, command, ...)
""")

# ---- home: what he named comes first
E("SolOrders.lua", """    local SC = SurvivorCompanion
    local base = SC and SC.BaseLife and type(SC.BaseLife.active) == "function" and SC.BaseLife.active() or nil
    local core = type(base) == "table" and base.core or nil
    if type(core) == "table" and type(core.x) == "number" and type(core.y) == "number" then return core.x, core.y end
    local h = type(SolHome) == "table" and type(SolHome.get) == "function" and SolHome.get() or nil   -- Sol's own home ("this is home")
    if h then return h.x, h.y end
    return nil
""", """    local h = type(SolHome) == "table" and type(SolHome.get) == "function" and SolHome.get() or nil   -- Sol's own home ("this is home"): what he named comes first
    if h then return h.x, h.y end
    local SC = SurvivorCompanion
    local base = SC and SC.BaseLife and type(SC.BaseLife.active) == "function" and SC.BaseLife.active() or nil
    local core = type(base) == "table" and base.core or nil
    if type(core) == "table" and type(core.x) == "number" and type(core.y) == "number" then return core.x, core.y end
    return nil
""")
E("SolFarmView.lua", """function V.homePoint()
    local b = BL()
    local base = b and tcall(b.active) or nil
    local core = type(base) == "table" and base.core or nil
    if type(core) == "table" and type(core.x) == "number" and type(core.y) == "number" then return { x = core.x, y = core.y, z = tonumber(core.z) or 0 } end
    local home = g("SolHome")
    local h = type(home) == "table" and type(home.get) == "function" and tcall(home.get) or nil
    if type(h) == "table" and type(h.x) == "number" then return { x = h.x, y = h.y, z = tonumber(h.z) or 0 } end
    return nil
""", """function V.homePoint()
    local home = g("SolHome")
    local h = type(home) == "table" and type(home.get) == "function" and tcall(home.get) or nil
    if type(h) == "table" and type(h.x) == "number" then return { x = h.x, y = h.y, z = tonumber(h.z) or 0 } end
    local b = BL()
    local base = b and tcall(b.active) or nil
    local core = type(base) == "table" and base.core or nil
    if type(core) == "table" and type(core.x) == "number" and type(core.y) == "number" then return { x = core.x, y = core.y, z = tonumber(core.z) or 0 } end
    return nil
""")
E("SolActions.lua", """    if id == "sol_far" and type(U.solFar) == "function" then return U.solFar(option) end
""", """    if id == "sol_far" and type(U.solFar) == "function" then return U.solFar(option) end
    if id == "sol_set_home" and type(SolHome) == "table" and type(SolHome.setHere) == "function" then return SolHome.setHere() end
""")

# ---- far: her body can be gone while she is still registered
E("SolFar.lua", """local function actor() return type(U.solActor) == "function" and U.solActor() or nil end
""", """local function liveActor() return type(U.solActor) == "function" and U.solActor() or nil end
-- A companion left behind stays registered after her square unloads (2026-11-09 10:38 to 10:44: living=1, no body). She is "here" only with a square under her.
local AWAY_MS, awaySince = 2000, nil
local function bodyGone(a)
    local f = a and a.getCurrentSquare
    if type(f) ~= "function" then return false end
    local ok, sq = pcall(f, a)
    if not ok or sq ~= nil then awaySince = nil; return false end
    local t = nowMs()
    if awaySince == nil or t < awaySince then awaySince = t end
    return t - awaySince >= AWAY_MS
end
local function actor()
    local a = liveActor()
    if a ~= nil and bodyGone(a) then return nil end
    return a
end
""")
E("SolFar.lua", """local function record()
    local P = persistence()
""", """local function record()
    local L = liveActor()
    if L ~= nil and actor() == nil then                                          -- registered, no body: the same trip as a saved record
        local x, y = tonumber(call(L, "getX")), tonumber(call(L, "getY"))
        if x ~= nil and y ~= nil then return { id = "live", x = x, y = y, live = L } end
    end
    local P = persistence()
""")
E("SolFar.lua", """local function finishSeek(s)
""", """-- puts her on the square that was found: a saved record is moved, a registered body is recovered there
local function moveBody(id, x, y)
    if id == "live" then
        local L, sc, gu = liveActor(), SC(), GU()
        if L == nil or sc == nil or gu == nil or type(sc.Actor) ~= "table" or type(sc.Actor.recover) ~= "function" or type(gu.gridSquare) ~= "function" then return false end
        local ok, sq = pcall(gu.gridSquare, x, y, 0)
        if not ok or sq == nil then return false end
        local okR, done = pcall(sc.Actor.recover, L, sq)
        return okR and done == true
    end
    local P = persistence()
    if P == nil or type(P.pendingRelocate) ~= "function" then return false end
    local ok, moved = pcall(P.pendingRelocate, id, x, y, 0)
    return ok and moved == true
end
local function finishSeek(s)
""")
E("SolFar.lua", """    local P = persistence()
    if P == nil or type(P.pendingRelocate) ~= "function" then lastResult = "no_spot"; return end
    local ok, moved = pcall(P.pendingRelocate, s.id, s.x, s.y, 0)
    if ok and moved == true then
        placed = { at = nowMs() }
""", """    if moveBody(s.id, s.x, s.y) then
        placed = { at = nowMs() }
""")
E("SolFar.lua", """        if placed ~= nil then return true, "placed" end
        return true, lastResult or "no_spot"
""", """        if placed ~= nil then return true, "placed" end
        return true, lastResult or "idle"                                        -- nothing under way (a reload clears it): not a failed trip
""")
E("SolFar.lua", "function U.solDotState()\n", """-- her position is in a part of the world that is not loaded: the game's own catch-up must not bring her to him at once, on screen
function U.solFarUnloaded(a)
    if a == nil or a ~= liveActor() then return false end
    local x, y, z = tonumber(call(a, "getX")), tonumber(call(a, "getY")), tonumber(call(a, "getZ"))
    local gu = GU()
    if x == nil or y == nil or gu == nil or type(gu.gridSquare) ~= "function" then return false end
    local ok, sq = pcall(gu.gridSquare, x, y, z or 0)
    return ok and sq == nil
end
function U.solDotState()
""")
E("SCRuntime.lua", "                local square, recoveryKind = followerRecoverySquare(record, currentPlayer, current)\n",
  "                if type(SolUI) == \"table\" and type(SolUI.solFarUnloaded) == \"function\" and SolUI.solFarUnloaded(record.actor) then return end   -- SolFar brings her: after the wait, off screen\n                local square, recoveryKind = followerRecoverySquare(record, currentPlayer, current)\n")
E("SolWorldScan.lua", "    snap.sol = charState(sol)\n", "    snap.sol = charState(sol)\n    if snap.sol and type(U.solFarState) == \"function\" and U.solFarState() ~= nil then snap.sol.away = true end   -- registered, no body\n")

# ---- what the scan sees
E("SolWorldScan.lua", """                            if (isWaterOk and isWater == true)
                                or (amountOk and num(amount) and amount > 0)
                                or (hasFluidOk and hasFluid == true) then
""", """                            if #snap.waterSources < 64 and (isWater == true or (num(amount) and num(amount) > 0) or hasFluid == true) then   -- call() returns one value: there are no "ok" flags
""")
E("SolWorldScan.lua", """if taintedOk and type(tainted) == "boolean" then waterTainted = tainted end""", """if type(tainted) == "boolean" then waterTainted = tainted end""")
E("SolWorldScan.lua", """amount = amountOk and round(amount, 2) or nil,""", """amount = num(amount) and round(num(amount), 2) or nil,""")
E("SolWorldScan.lua", """    local vehicles = cell and call(cell, "getVehicles")
    local vn = vehicles and num(call(vehicles, "size")) or 0
    for i = 0, vn - 1 do
        local v0 = call(vehicles, "get", i)
        if v0 and not vseen[v0] then vseen[v0] = true; vlist[#vlist + 1] = v0 end
    end
""", """    local carsLoaded = {}                                                        -- getVehicles is a Set in B42: no get(i). The same list the rest of the mod uses.
    local carService = rawget(_G, "SurvivorCompanion") and SurvivorCompanion.Vehicle or nil
    if type(carService) == "table" and type(carService.loadedVehicles) == "function" then
        local okC, listC = pcall(carService.loadedVehicles)
        if okC and type(listC) == "table" then carsLoaded = listC end
    end
    for _, v0 in ipairs(carsLoaded) do
        if v0 and not vseen[v0] then vseen[v0] = true; vlist[#vlist + 1] = v0 end
    end
""")
E("SolInventory.lua", """    model.state = "done"; model.ms = nowMs() - model.t; model.byKey = nil
""", """    if model.squares == 0 and last ~= nil and ((tonumber(last.squares) or 0) > 0 or last.baseFrom ~= nil) then     -- he is away and the base is not loaded: what she last saw there still stands
        for _, r in ipairs(last.rows or {}) do
            if r.where ~= "player" and r.where ~= "sol" and #model.rows < MAX_ROWS then model.rows[#model.rows + 1] = r end
        end
        model.baseFrom = last.baseFrom or last.t
    end
    model.state = "done"; model.ms = nowMs() - model.t; model.byKey = nil
""")
E("SolInventory.lua", "vehicles = m.vehicles, trunc = m.trunc or nil,", "vehicles = m.vehicles, baseFrom = m.baseFrom, trunc = m.trunc or nil,")
E("SolInventory.lua", """    if Events and Events.OnTick then
        local lastAuto = 0
        Events.OnTick.Add(function()
            if job and job.phase ~= "done" then U.invStep() return end
            local t = nowMs()
            if t - lastAuto >= AUTO_MS and getSpecificPlayer and getSpecificPlayer(0) ~= nil then lastAuto = t; pcall(U.invStart) end
        end)
    end
""", """    do
        local lastAuto = 0
        local function invTick()
            local t = nowMs()
            if job and job.phase ~= "done" then
                U.invStep()
                if U.perfAdd then U.perfAdd("inventory", nowMs() - t) end
                return
            end
            if t - lastAuto >= AUTO_MS and getSpecificPlayer and getSpecificPlayer(0) ~= nil then lastAuto = t; pcall(U.invStart) end
        end
        if type(SolBudget) == "table" and type(SolBudget.register) == "function" then SolBudget.register("inventory", invTick, { everyMs = 0, priority = 7 })
        elseif Events and Events.OnTick then Events.OnTick.Add(invTick) end
    end
""")
E("SolBaseScan.lua", "                local key = x * 65536 + y\n", "                local key = (x * 65536 + y) * 16 + r.z\n")
E("SolBaseScan.lua", """                                    local c = method(o, "getContainer")
                                    if c ~= nil then containers[#containers + 1] = { obj = o, x = x, y = y, z = r.z, cont = c, type = tostring(method(c, "getType") or "?") } end
""", """                                    for ci = 0, (tonumber(method(o, "getContainerCount")) or 0) - 1 do       -- a fridge has a freezer too
                                        local c = method(o, "getContainerByIndex", ci)
                                        if c ~= nil then containers[#containers + 1] = { obj = o, x = x, y = y, z = r.z, cont = c, type = tostring(method(c, "getType") or "?") } end
                                    end
""")

# ---- never on the ground, never in English
E("SCLogistics.lua", """    if type(SolUI) == "table" and type(SolUI.solActor) == "function" and SolUI.solActor() == actor then
        moveMemory.note(actor, "drop", state.item, U().nowMs())
""", """    if type(SolSpeechAR) == "table" and type(SolSpeechAR.isSol) == "function" and SolSpeechAR.isSol(actor) then      -- solActor() is nil with a second companion alive
        moveMemory.note(actor, "drop", state.item, U().nowMs())
""")
E("SCUIContext.lua", """    safeMethod(actor, "Say", likes and (nickname .. "? Alright. I'll answer to it.")
""", """    if type(SolSpeechAR) == "table" and type(SolSpeechAR.isSol) == "function" and SolSpeechAR.isSol(actor) then return end     -- nothing in English above her head
    safeMethod(actor, "Say", likes and (nickname .. "? Alright. I'll answer to it.")
""")
E("SCDialogue.lua", """        overheadLine = SolSpeechAR.resolve(actor, topic, resolvedLine)
        if overheadLine then resolvedLine = overheadLine end
""", """        overheadLine = SolSpeechAR.resolve(actor, topic, resolvedLine)
        if overheadLine then resolvedLine = overheadLine else return false, "no_arabic" end       -- not even in the transcript
""")
E("SCDialogue.lua", """        and utility.speechDisplayMillis(resolvedLine) or 8000
""", """        and utility.speechDisplayMillis((string.gsub(resolvedLine, "\\\\u%x%x%x%x", "x"))) or 8000     -- \\uXXXX is one letter on the bubble
""")
E("SolSpeechAR.lua", """local function tidy(s)
    s = string.gsub(s, "%s+", " ")
    s = string.gsub(s, "^ ", "")
    s = string.gsub(s, " $", "")
    return s
end
""", """local function tidy(s)
    s = string.gsub(s, "%s+", " ")
    s = string.gsub(s, "^[%s%-:,%.]+", "")                                       -- what is left at the edges when a Latin name was taken out
    s = string.gsub(s, "[%s%-:,]+$", "")
    return s
end
""")

# ---- the farm
E("SolAuthority.lua", """function A.allowsDecision(actor, kind, detail)
    if tostring(kind) == "follow" and A.farmHeld(actor) then return false end
""", """function A.allowsDecision(actor, kind, detail)
    if tostring(kind) == "follow" and A.farmHeld(actor) then return false end
    -- on the farm her bag is full of what she is carrying on purpose: sorting it away takes her legs from the job (32 refused walks, 2026-11-09 09:14)
    if (tostring(kind) == "logistics" or tostring(kind) == "base_work" or (tostring(kind) == "downtime" and not A.restWanted(actor))) and A.farmHeld(actor) then return false end
""")
E("SolFarmWork.lua", """function P.pestDue(p, pest, harvestAt)
    local lvl = p[pest.key] or 0
    if lvl <= 0 then return false end
""", """function P.pestDue(p, pest, harvestAt, force)
    local lvl = p[pest.key] or 0
    if lvl <= 0 then return false end
    if force == true then return true end                                        -- he asked: any sign of it counts
""")
E("SolFarmWork.lua", """                if alive(p) and P.pestDue(p, pest, props and props.harvestLevel or nil) then
""", """                if alive(p) and P.pestDue(p, pest, props and props.harvestLevel or nil, filter == "cure") then
""")
E("SolFarmWork.lua", """    if (stock.foodStorage or 0) == 0 then out[#out + 1] = { storage = "food", unsure = false } end
""", """    if (stock.foodStorage or 0) == 0 then out[#out + 1] = { storage = "food", unsure = unsure.farming == true } end
""")
E("SolFarmWork.lua", """    m.stop = { reason = reason, detail = detail, seq = m.seq, at = nowMs() }
""", """    m.stop = { reason = reason, detail = detail, seq = m.seq, at = nowMs() }
    m.stops = m.stops or {}                                                      -- the Mind reads every 15 s or so: the real reason must not be overwritten before that
    m.stops[#m.stops + 1] = m.stop
    while #m.stops > 4 do table.remove(m.stops, 1) end
""")
E("SolFarmWork.lua", """        stop = m.stop, seq = tonumber(m.seq) or 0, zones = counts,""", """        stop = m.stop, stops = m.stops, seq = tonumber(m.seq) or 0, zones = counts,""")
E("SolFarmWork.lua", """    local square = tcall(gu.gridSquare, x, y, z)
    if square == nil then return "failed" end
    local targets = tcall(n.interactionTargets, a, square, { maximum = 8 })
""", """    local square = tcall(gu.gridSquare, x, y, z)
    if square == nil then j.walkUnloaded = true; return "failed" end
    local targets = tcall(n.interactionTargets, a, square, { maximum = 8 })
""")
E("SolFarmWork.lua", """    if accepted then w.refused = 0; return "walking" end
    if type(why) == "string" and (string.find(why, "owned", 1, true) or string.find(why, "deferred", 1, true)) then return "walking" end""",
  """    if accepted then w.refused = 0; j.walkBusy = nil; return "walking" end
    if type(why) == "string" and (string.find(why, "owned", 1, true) or string.find(why, "deferred", 1, true)) then j.walkBusy = true; return "walking" end""")
E("SolFarmWork.lua", """local function failJob(m, a, reason)
    local j = m.job
    m.job = nil
    stopBody(m, a)
    if j == nil then return end
""", """local function failJob(m, a, reason)
    local j = m.job
    m.job = nil
    stopBody(m, a)
    if j == nil then return end
    if reason == "no_path" or reason == "carry_no_path" then                     -- "no road" only when it is true
        if j.walkUnloaded then
            view().rescanZone(j.zoneId)
            say(m, "unloaded:" .. tostring(j.key), "blocked", { op = j.op, why = "target_unloaded", crop = j.crop })
            return                                                               -- not the plant's fault: no pause counted
        end
        if j.walkBusy then reason = "body_busy" end
    end
""")
E("SolFarmWork.lua", """            if hasRoom(c, a, items[k]) and moveItem(holderOf(items[k], i), c, items[k]) then moved = moved + 1 end
""", """            if items[k] ~= nil and call(a, "getPrimaryHandItem") == items[k] then pcall(a.setPrimaryHandItem, a, nil) end     -- a reload can leave the tool in her hand
            if hasRoom(c, a, items[k]) and moveItem(holderOf(items[k], i), c, items[k]) then moved = moved + 1 end
""")
E("SolFarmWork.lua", """        if m.atHome ~= true then
            m.atHome = true
            local st = orderState(a)
""", """        if m.atHome ~= true or m.homeStayDone ~= true then                       -- told to stay while already there: the stay is still needed
            local arrived = m.atHome ~= true
            m.atHome, m.homeStayDone = true, true
            local st = orderState(a)
""")
E("SolFarmWork.lua", """            say(m, nil, "home_arrived", {})
        end
        local need = k and k.bodyNeed and k.bodyNeed(a) or nil
""", """            if arrived then say(m, nil, "home_arrived", {}) end
        end
        local need = k and k.bodyNeed and k.bodyNeed(a) or nil
""")
E("SolFarmWork.lua", """    if need then setStatus(m, "needs", need); return end
    if #v.zones() == 0 then
""", """    if need and (m.filter == nil or need == "health") then setStatus(m, "needs", need); return end       -- a single order he just gave does not wait for a wash
    if #v.zones() == 0 then
""")
E("SolFarmWork.lua", """        if #m.owed > 0 and startReturn(m, a) then return end
        if m.filter then return W.finishSingle(m, W.topReason(blocked)) end
""", """        if m.filter and m.filter.kind == "harvest" and not m.filter.carried and produceInBag(a) > 0 then      -- the harvest is not left in her bag
            m.filter.carried = true
            if startCarry(m, a) then return end
        end
        if #m.owed > 0 and startReturn(m, a) then return end
        if m.filter then return W.finishSingle(m, W.topReason(blocked)) end
""")
E("SolFarmWork.lua", """        if seen[key] or #regs >= 24 then return end""", """        if seen[key] or #regs >= 60 then return end""")
E("SolFarmWork.lua", """    if cmd == "short" then return true, "short:" .. js(P.shortages(v.allPlants(), v.stockLatest, W.env(a))) end
    if cmd == "storage" then return true, "storage:" .. W.storageSeen() end""", """    if (cmd == "short" or cmd == "storage") and not (type(v.stockLatest) == "table" and v.stockLatest.ready == true) then return true, "not_ready" end
    if cmd == "short" then return true, "short:" .. js(P.shortages(v.allPlants(), v.stockLatest, W.env(a))) end
    if cmd == "storage" then return true, "storage:" .. W.storageSeen() end""")

if len(sys.argv) > 2 and sys.argv[2] == "--verify":          # every edit is in the deployed files
    missing = 0
    for f, pairs_ in EDITS.items():
        t = open(os.path.join(D, f), encoding="utf-8", newline="").read().replace(chr(13) + chr(10), chr(10))
        for a, b in pairs_:
            if t.count(b) < 1: missing += 1; print("MISSING", f, b[:70])
    print("verified", sum(len(v) for v in EDITS.values()), "edits, missing", missing)
    sys.exit(1 if missing else 0)
# ---- plan: compute everything first, write only if all of it fits
out = {}
for f, pairs_ in EDITS.items():
    p = os.path.join(D, f)
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    for a, b in pairs_:
        a2, b2 = a.replace("\n", nl), b.replace("\n", nl)
        assert t.count(a2) == 1, (f, a[:70], t.count(a2))
        t = t.replace(a2, b2)
    out[p] = t
for p, t in out.items(): open(p, "w", encoding="utf-8", newline="").write(t)
print("applied", sum(len(v) for v in EDITS.values()), "edits to", len(out), "files in", D)

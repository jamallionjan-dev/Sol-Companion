"""far_arrival: her car from far comes WITH her, at the wheel, on a road, facing along it, then she drives to where he is now.
Also: door-first passenger boarding and walk-in (spatial_access), and every far-flow line in her own words. Game closed only.
In place and idempotent (each edit is skipped when already there); for a lab with apply_s64/s65/s68 (SolFar) and apply_s70.
Plan: DOCS/PLAN_spatial_awareness.md 9; council SOL_REVIEW_20261109.md 37.

Confirmed cause of 2026-11-10 19:47:36 "record_failed" (lab DebugLog 2026-11-10_18-45, lines 24844-24891):
  she had been with him this session, so after he drove off she stayed a REGISTERED companion with no body ("[Sol-Diag][gate] ...
  no saved Sol is pending" every few seconds 19:19-19:51 = pendingCompanionCount() == 0; "captureRecord ok id=sc-..." at each save).
  SolFar.record() then answers { id = "live" } (SolFar.lua 76-81). moveTick handed "live" to persistence.pendingRelocate, whose first
  guard is pending[id] == nil (SCPersistence.lua 4176-4178): pending["live"] is always nil. The walk-in at 19:51 worked because moveBody()
  treats "live" separately (Actor.recover). No vehicle flag, spawn ticket or quarantine was involved.

  SCPersistence.lua  pendingRelocate: the same guards, now with a reason (no_pending_entry, in_vehicle_record, spawn_pending, quarantined,
                     no_position)
  SolFar.lua         car_far:<x>,<y>,<tiles>[,<heading>] and car_where answers ...,<kind>
                     before the car moves: can her body follow it? (live, or a saved record persistence will move); if not, the car stays,
                       the reason goes to the log and she comes on foot (poll on_foot:<s>)
                     after the move: a saved record moves beside the car; a live one waits for it; nothing is said
                     when the car's part of the world loads: the car is turned along the road (setAngles, checked with getForwardVector),
                       her body comes back at the driver's door out of his view (Actor.recover), and she takes the wheel the same second
                       (SC.Driving.takeWheel); retried each second up to 8 times; poll says "seeking" until she is in, then "here"
                     on foot, "she is here": SolPlace walks her to him door-first, then regroup
  SolOrders.lua      passenger door walk: the next door-first leg (SolPlace.nextLeg); at a leg, the next one at once
  chat_service.py    the spot: road_route.pickup_spot_dir (a straight stretch of street just outside what is loaded, heading toward him;
                     a helicopter: an open place); "here" after a car_far -> "صرت قريبة، عضّة كوساية وبوصل." and the drive, quiet;
                     a car that cannot come -> she walks, "جاية، اصبر شوي."; no mechanics in any far line
  goal_engine.py     fetch_player follows him: a new GPS target when he moved 12 tiles (was 40); "جايتك، استناني." once, not with quiet
  road_route.py      pickup_spot_dir, heli_spot (appended, src/road_route_spot.py)
usage: apply_s72_far_arrival.py <client dir> <sol_mind dir>      (either may be '-')"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)
HERE = os.path.dirname(os.path.abspath(__file__))

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

# ---------------------------------------------------------------- SCPersistence
P_OLD = """    if entry == nil or entry.vehicle == true or entry.spawnTicket ~= nil or entry.status == "quarantined" then return false end
    local saved = entry.record
    local position = type(saved) == "table" and saved.position or nil
    if type(position) ~= "table" then return false end
    position.x, position.y, position.z = x, y, z"""
P_NEW = """    if entry == nil then return false, "no_pending_entry" end                    -- far_arrival: why, for SolFar's log; the same guards
    if entry.vehicle == true then return false, "in_vehicle_record" end
    if entry.spawnTicket ~= nil then return false, "spawn_pending" end
    if entry.status == "quarantined" then return false, "quarantined" end
    local saved = entry.record
    local position = type(saved) == "table" and saved.position or nil
    if type(position) ~= "table" then return false, "no_position" end
    position.x, position.y, position.z = x, y, z"""

# ---------------------------------------------------------------- SolFar
SF = []
SF.append(("""    local x, y, tiles = string.match(text, "^(%-?[%d%.]+),(%-?[%d%.]+),([%d%.]+)$")
""", """    local x, y, tiles, heading = string.match(text, "^(%-?[%d%.]+),(%-?[%d%.]+),([%d%.]+),(%-?[%d%.]+)$")       -- far_arrival: the road's heading
    if x == nil then x, y, tiles = string.match(text, "^(%-?[%d%.]+),(%-?[%d%.]+),([%d%.]+)$") end
    F.heading = tonumber(heading)
"""))
SF.append(("""    return true, "car:" .. math.floor(best.x) .. "," .. math.floor(best.y) .. "," .. math.floor(px) .. "," .. math.floor(py) .. "," .. math.floor(ring)
""", """    return true, "car:" .. math.floor(best.x) .. "," .. math.floor(best.y) .. "," .. math.floor(px) .. "," .. math.floor(py) .. "," .. math.floor(ring) .. "," .. tostring(best.kind or "car")
"""))
SF.append(("""    log("on her way, " .. (ms / 1000) .. " s")
    return true, "waiting:" .. waitSeconds()
end
""", """    log("on her way, " .. (ms / 1000) .. " s")
    return true, "waiting:" .. waitSeconds()
end
F.startWait = startWait                                                         -- far_arrival: the car path falls back to this
"""))
# before the car moves: can she follow it?
SF.append(("""        if d == nil or type(req) ~= "function" or (m.id == nil and loadedCar() ~= nil) then lastResult = "loaded"; return end
""", """        if d == nil or type(req) ~= "function" or (m.id == nil and loadedCar() ~= nil) then lastResult = "loaded"; return end
        local follow, whyNot = F.canFollow()                                    -- far_arrival: never the car alone
        if not follow then
            log("car not moved: she could not come with it (" .. tostring(whyNot) .. "); she comes on foot")
            local okW = type(F.startWait) == "function" and F.startWait("foot")
            if okW and wait ~= nil then wait.fellBack = true else lastResult = "record_failed" end
            return
        end
"""))
SF.append(("""    local b = record()
    local P = persistence()
    local ok, moved = false, false
    if b ~= nil and P ~= nil and type(P.pendingRelocate) == "function" then ok, moved = pcall(P.pendingRelocate, b.id, math.floor(m.x) + 3, math.floor(m.y), 0) end
    if ok and moved == true then
        placed, lastResult, expecting = { at = t, forever = true, x = m.x, y = m.y }, "placed", 0
    else
        lastResult = "record_failed"
    end
end
""", """    local b = record()
    local P = persistence()
    local ok, moved, why = false, false, nil
    local heading = F.heading
    if b ~= nil and b.id == "live" then                -- far_arrival: registered with no body: her body comes back at the wheel when the car loads
        placed, lastResult, expecting = { at = t, forever = true, x = m.x, y = m.y, car = true, heading = heading }, "placed", 0
        log("car moved to " .. math.floor(m.x) .. "," .. math.floor(m.y) .. "; she gets in when it loads")
        return
    end
    if b ~= nil and P ~= nil and type(P.pendingRelocate) == "function" then ok, moved, why = pcall(P.pendingRelocate, b.id, math.floor(m.x) + 2, math.floor(m.y), 0) end
    if ok and moved == true then
        placed, lastResult, expecting = { at = t, forever = true, x = m.x, y = m.y, car = true, heading = heading }, "placed", 0
        log("car moved to " .. math.floor(m.x) .. "," .. math.floor(m.y) .. " with her saved record beside it")
    else
        why = (b == nil and "no_record") or ((not ok) and ("error " .. tostring(moved))) or tostring(why or "refused")
        log("car moved, her record did not (" .. tostring(b and b.id) .. ": " .. why .. "); she comes on foot")       -- the log only
        lastResult = "record_failed"
        local okW = type(F.startWait) == "function" and F.startWait("foot")
        if okW and wait ~= nil then wait.fellBack = true end
    end
end
"""))
SF.append(("local function tick()\n", """-- ---------------------------------------------------------------- far_arrival: the car and she arrive together
-- can her body follow the car? a live registration (Actor.recover) or a saved record persistence will move (the same guards as pendingRelocate)
function F.canFollow()
    local b = record()
    if b == nil then return false, "no_record" end
    if b.id == "live" then return true end
    local P = persistence()
    if P == nil or type(P.pendingBootstrap) ~= "function" then return false, "no_persistence" end
    local ok, boot = pcall(P.pendingBootstrap, b.id)
    if ok and type(boot) == "table" then return true end
    return false, "record_not_movable"
end
local function carHeadingOf(car)
    local Vec = rawget(_G, "Vector3f")
    if Vec == nil then return nil end
    local okF, f = pcall(function() return car:getForwardVector(Vec.new()) end)
    if not okF or f == nil then return nil end
    local okX, x = pcall(function() return f:x() end)
    local okZ, z = pcall(function() return f:z() end)
    x, z = okX and tonumber(x) or nil, okZ and tonumber(z) or nil
    if x == nil or z == nil then return nil end
    local l = math.sqrt(x * x + z * z)
    if l < 0.001 then return nil end
    return x / l, z / l
end
-- turn the car along the road (degrees, world x/y): setAngles, then the forward vector says whether it took (the sign is checked, not assumed)
function F.align(car, deg)
    if deg == nil then return true end
    local hx, hy = math.cos(math.rad(deg)), math.sin(math.rad(deg))
    local cx, cz = carHeadingOf(car)
    if cx == nil then return false end
    if cx * hx + cz * hy > 0.985 then return true end
    local ax = tonumber(call(car, "getAngleX")) or 0
    local ay = tonumber(call(car, "getAngleY")) or 0
    local az = tonumber(call(car, "getAngleZ")) or 0
    local turn = math.deg(math.atan2(hy, hx) - math.atan2(cz, cx))
    for _, s in ipairs({ 1, -1 }) do
        pcall(function() car:setAngles(ax, ay + s * turn, az) end)
        local nx, nz = carHeadingOf(car)
        if nx ~= nil and nx * hx + nz * hy > 0.97 then return true end
    end
    pcall(function() car:setAngles(ax, ay, az) end)
    return false
end
-- the square by the driver's door: loaded, out of his view, safe, nearest to the door (the game's own getEnterSeatDistance)
function F.doorSquare(car)
    local gu = GU()
    local cx, cy = xyOf(car)
    if gu == nil or cx == nil or type(gu.gridSquare) ~= "function" then return nil end
    local bx, by, bsq, bd
    for dx = -4, 4 do
        for dy = -4, 4 do
            local x, y = math.floor(cx) + dx, math.floor(cy) + dy
            local okQ, sq = pcall(gu.gridSquare, x, y, 0)
            if okQ and sq ~= nil and offScreen(x, y) then
                local okS, safe = true, true
                if type(gu.isSafeSpawnSquare) == "function" then okS, safe = pcall(gu.isSafeSpawnSquare, sq) end
                if okS and safe == true then
                    local okD, d = pcall(function() return car:getEnterSeatDistance(0, x + 0.5, y + 0.5) end)
                    d = okD and tonumber(d) or nil
                    if d ~= nil and (bd == nil or d < bd) then bx, by, bsq, bd = x, y, sq, d end
                end
            end
        end
    end
    return bx, by, bsq
end
function F.arrive(p, t)
    if t - (p.tryAt or 0) < 1000 and t >= (p.tryAt or 0) then return end
    p.tryAt = t
    local car = loadedCar()
    if car == nil then return end                                               -- its part of the world is not loaded yet
    if not p.aligned then
        p.aligned = F.align(car, p.heading)
        log("her car is there" .. (p.heading and (", along the road " .. (p.aligned and "yes" or "no")) or ""))
    end
    local sc = SC()
    local a = actor()
    if a == nil then
        local L = liveActor()
        if L == nil or sc == nil or type(sc.Actor) ~= "table" or type(sc.Actor.recover) ~= "function" then return end    -- a saved record: the restore brings her
        local x, y, sq = F.doorSquare(car)
        if sq == nil then return end
        local okR, done = pcall(sc.Actor.recover, L, sq)
        if not (okR and done == true) then return end
        a = L
        log("she is back at her car, " .. x .. "," .. y)
    end
    if call(a, "getVehicle") == car then p.done = true; return end
    p.seatTries = (p.seatTries or 0) + 1
    local D = sc and sc.Driving or nil
    if type(D) ~= "table" or type(D.takeWheel) ~= "function" then p.seatTries = 99; return end
    local okW, took, why = pcall(D.takeWheel, a, car, { playerCommand = true, immediateCommand = true })
    if okW and took ~= true and tostring(why) == "companion is not at the passenger door" and type(sc.Actor) == "table" and type(sc.Actor.recover) == "function" then
        local _, _, sq = F.doorSquare(car)                                        -- restored a little off: to the door, then the wheel
        if sq ~= nil and pcall(sc.Actor.recover, a, sq) then okW, took, why = pcall(D.takeWheel, a, car, { playerCommand = true, immediateCommand = true }) end
    end
    if call(a, "getVehicle") == car or (okW and took == true) then
        p.done = true
        log("she is at the wheel")
    else
        log("the wheel, try " .. p.seatTries .. ": " .. tostring(okW and why or took))
    end
end
local function tick()
"""))
SF.append(("""    local a = actor()
    if a ~= nil then
        if expecting > 0 then""", """    if placed ~= nil and placed.car == true and placed.done ~= true then pcall(F.arrive, placed, t) end      -- far_arrival
    local a = actor()
    if a ~= nil then
        if expecting > 0 then"""))
SF.append(("""        awake, wait, seek, placed, moving = false, nil, nil, nil, nil
""", """        local seating = placed ~= nil and placed.car == true and placed.done ~= true and (placed.seatTries or 0) < 8      -- far_arrival
        awake, wait, seek, moving = false, nil, nil, nil
        if not seating then placed = nil end
"""))
SF.append(("""    if opt == "poll" then
        if actor() ~= nil then return true, "here" end
        if moving ~= nil then return true, "seeking" end
""", """    if opt == "poll" then
        if placed ~= nil and placed.car == true and placed.done ~= true and (placed.seatTries or 0) < 8 and actor() ~= nil then return true, "seeking" end    -- far_arrival: getting in
        if actor() ~= nil then return true, "here" end
        if moving ~= nil then return true, "seeking" end
        if wait ~= nil and wait.fellBack then return true, "on_foot:" .. waitSeconds() end      -- far_arrival: she walks instead
"""))
SF.append(("""            log("she is here")
            expecting = regroup(a) and 0 or expecting - 1
""", """            log("she is here")
            local SP = rawget(_G, "SolPlace")                                    -- spatial_access: to him through doors first, then regroup
            local px, py = xyOf(player())
            if type(SP) == "table" and type(SP.on) == "function" and SP.on() and type(SP.goNear) == "function" and px ~= nil then
                local okG, started = pcall(SP.goNear, px, py, nil, 3, function() regroup(a) end)
                if okG and started == true then expecting = 0 end
            end
            if expecting > 0 then expecting = regroup(a) and 0 or expecting - 1 end
"""))

# ---------------------------------------------------------------- far_arrival inside the loaded area (owner, 2026-11-10: he stays where he is)
# car_where says ",in" when the Java side (SolCarArrive) is there; the Mind then picks a road spot INSIDE the loaded ring, out of his view.
SF.append(("""    return true, "car:" .. math.floor(best.x) .. "," .. math.floor(best.y) .. "," .. math.floor(px) .. "," .. math.floor(py) .. "," .. math.floor(ring) .. "," .. tostring(best.kind or "car")
""", """    return true, "car:" .. math.floor(best.x) .. "," .. math.floor(best.y) .. "," .. math.floor(px) .. "," .. math.floor(py) .. "," .. math.floor(ring) .. "," .. tostring(best.kind or "car")
        .. (type(rawget(_G, "solCarArriveRequest")) == "function" and ",in" or "")          -- far_arrival: it can come into the loaded area
"""))
SF.append(("""local function startFarCar(text)
""", """local function startFarCar(text)
    F.inside = string.sub(tostring(text or ""), -3) == ",in"                     -- far_arrival: into the loaded area, out of his view
    if F.inside then text = string.sub(text, 1, -4) end
"""))
SF.append(("""        local okR, sent = pcall(req, m.id or d.carSqlId, m.x, m.y)
""", """        if F.inside and type(rawget(_G, "solCarArriveRequest")) == "function" then        -- far_arrival: into the loaded area
            F.arriving = { m = m, at = t, id = m.id or tonumber(d.carSqlId), heading = F.heading, kind = m.kind, tries = 0 }
            return
        end
        local okR, sent = pcall(req, m.id or d.carSqlId, m.x, m.y)
"""))
SF.append(("""    wait, awake, lastResult = { left = ms, last = nowMs(), tries = 0, mode = "car_far", x = x, y = y, cost = cost, id = p.id, mass = p.mass, quality = p.quality }, true, nil
""", """    wait, awake, lastResult = { left = ms, last = nowMs(), tries = 0, mode = "car_far", x = x, y = y, cost = cost, id = p.id, mass = p.mass, quality = p.quality, kind = p.kind }, true, nil
"""))
SF.append(("-- ---------------------------------------------------------------- far_arrival: the car and she arrive together\n", """-- far_arrival inside: a square for the car near the Mind's spot, all of it seen live: loaded, out of his view, outdoors, on a street
-- (a helicopter: any open ground with nothing within 2 tiles), no zombie within 12 tiles, no vehicle within 6. Nearest first, 24 tiles at most.
local function freeSq(sq) local ok, v = pcall(function() return sq:isFree(false) end); return not ok or v ~= false end
local function streetFloor(sq)
    local fl = call(sq, "getFloor")
    local spr = fl and call(fl, "getSprite") or nil
    local name = string.lower(tostring(spr and call(spr, "getName") or ""))
    return string.find(name, "street", 1, true) ~= nil or string.find(name, "road", 1, true) ~= nil
end
function F.insideSpot(x0, y0, kind)
    local gu = GU()
    if gu == nil or type(gu.gridSquare) ~= "function" then return nil end
    local zs, vs = {}, {}
    local cellOf = rawget(_G, "getCell")
    local cell = type(cellOf) == "function" and cellOf() or nil
    local zl = cell and call(cell, "getZombieList") or nil
    for i = 0, (zl and tonumber(call(zl, "size")) or 0) - 1 do
        local okZ, z = pcall(zl.get, zl, i)
        local zx, zy = xyOf(okZ and z or nil)
        if zx ~= nil then zs[#zs + 1] = { zx, zy } end
    end
    local vl = cell and call(cell, "getVehicles") or nil
    for i = 0, (vl and tonumber(call(vl, "size")) or 0) - 1 do
        local okV, v = pcall(vl.get, vl, i)
        local vx, vy = xyOf(okV and v or nil)
        if vx ~= nil then vs[#vs + 1] = { vx, vy } end
    end
    local function clearOf(list, x, y, r) for _, p in ipairs(list) do if (p[1] - x) ^ 2 + (p[2] - y) ^ 2 < r * r then return false end end return true end
    for r = 0, 24 do
        for dx = -r, r do
            for dy = -r, r do
                if math.max(math.abs(dx), math.abs(dy)) == r then
                    local x, y = math.floor(x0) + dx, math.floor(y0) + dy
                    local okQ, sq = pcall(gu.gridSquare, x, y, 0)
                    if okQ and sq ~= nil and offScreen(x, y) and call(sq, "isOutside") ~= false and clearOf(zs, x, y, 12) and clearOf(vs, x, y, 6) then
                        local good
                        if kind == "heli" then
                            good = true
                            for ex = -2, 2 do for ey = -2, 2 do
                                local okE, e = pcall(gu.gridSquare, x + ex, y + ey, 0)
                                if not okE or e == nil or call(e, "isOutside") == false or not freeSq(e) then good = false end
                            end end
                        else
                            good = streetFloor(sq) and freeSq(sq)
                        end
                        if good then return x, y end
                    end
                end
            end
        end
    end
    return nil
end
local function insideFallback(why)
    F.arriving = nil
    log("car not brought in (" .. tostring(why) .. "); she comes on foot")       -- the log only
    local okW = type(F.startWait) == "function" and F.startWait("foot")
    if okW and wait ~= nil then wait.fellBack = true else lastResult = "record_failed" end
end
function F.arriveTick(t)
    local A = F.arriving
    local stateFn, mainFn, reqFn = rawget(_G, "solCarArriveState"), rawget(_G, "solCarArriveMain"), rawget(_G, "solCarArriveRequest")
    if type(stateFn) ~= "function" or type(mainFn) ~= "function" or type(reqFn) ~= "function" then return insideFallback("no_java") end
    if A.sent == nil then
        local follow, whyNot = F.canFollow()
        if not follow then return insideFallback(whyNot) end
        local x, y = F.insideSpot(A.m.x, A.m.y, A.kind)
        if x == nil then
            A.tries = A.tries + 1
            if A.tries > 20 then return insideFallback("no_clear_spot") end      -- 20 s of looking: a zombie, a car, his view in the way
            return
        end
        local okR, sent = pcall(reqFn, A.id, x + 0.5, y + 0.5)
        if not (okR and sent == true) then
            local st = tostring(stateFn())
            if st == "target_unloaded" and A.tries < 20 then A.tries = A.tries + 1; return end
            return insideFallback(st)
        end
        A.sent, A.x, A.y = t, x + 0.5, y + 0.5
        return
    end
    local st = tostring(stateFn())
    if st == "queued" then
        if t - A.sent > 10000 then local c = rawget(_G, "solCarArriveCancel"); if type(c) == "function" then pcall(c) end; return insideFallback("queue_timeout") end
        return
    end
    if st == "staged" then
        local okM, r = pcall(mainFn)
        st = okM and tostring(r) or "main_error"
    end
    if st == "arrived" or st == "deferred" then
        local d, m = store(), A.m
        if d ~= nil then
            d.carSqlId, d.carTowing, d.carZ, d.carFuel = A.id, false, 0, nil
            if m.mass then d.carMass, d.carQuality = m.mass, m.quality end
            d.carX, d.carY, d.fuelDue = A.x, A.y, m.cost                         -- taken from the tank once (settleFuel)
        end
        local b, P = record(), persistence()
        if b ~= nil and b.id ~= "live" and P ~= nil and type(P.pendingRelocate) == "function" then
            local okP, moved, why = pcall(P.pendingRelocate, b.id, math.floor(A.x) + 2, math.floor(A.y), 0)
            if not (okP and moved == true) then log("her record stays where it was (" .. tostring(okP and why or moved) .. ")") end
        end
        F.arriving = nil
        placed, lastResult, expecting = { at = t, forever = true, x = A.x, y = A.y, car = true, heading = A.heading }, "placed", 0
        log("her car is " .. (st == "arrived" and "here, " or "on its way in, ") .. math.floor(A.x) .. "," .. math.floor(A.y))
        if st == "arrived" then pcall(F.arrive, placed, t) end                  -- the same tick: along the road, her body at the door, the wheel
        return
    end
    return insideFallback(st)
end
-- ---------------------------------------------------------------- far_arrival: the car and she arrive together
"""))
SF.append(("""    if placed ~= nil and placed.car == true and placed.done ~= true then pcall(F.arrive, placed, t) end      -- far_arrival
""", """    if F.arriving ~= nil then pcall(F.arriveTick, t) end                         -- far_arrival inside
    if placed ~= nil and placed.car == true and placed.done ~= true then pcall(F.arrive, placed, t) end      -- far_arrival
"""))
SF.append(("""        if wait ~= nil and wait.fellBack then return true, "on_foot:" .. waitSeconds() end      -- far_arrival: she walks instead
""", """        if wait ~= nil and wait.fellBack then return true, "on_foot:" .. waitSeconds() end      -- far_arrival: she walks instead
        if F.arriving ~= nil then return true, "seeking" end                    -- far_arrival inside: the car is coming in
"""))

# ---------------------------------------------------------------- SolOrders
SO = [("""        local x, y, obj = pickSquare(sqs, j.tries)
        if not x then return false end
""", """        local x, y, obj = pickSquare(sqs, j.tries)
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
"""), ("j.walk = { x = x, y = y, askedAt = t, bestAt = t }; return true end", "j.walk = { x = x, y = y, askedAt = t, bestAt = t, leg = leg }; return true end"),
      ("        local ask = (w == nil) or wasPreempted\n", "        local ask = (w == nil) or wasPreempted\n"
       "        if not ask and w ~= nil and w.leg ~= nil and sx ~= nil and (sx - w.x - 0.5) ^ 2 + (sy - w.y - 0.5) ^ 2 < 0.81 then ask = true end   -- spatial_access: at a door on her way, the next leg at once\n")]

def client(cl):
    edit(os.path.join(cl, "SCPersistence.lua"), P_OLD, P_NEW)
    for o, n in SF: edit(os.path.join(cl, "SolFar.lua"), o, n)
    for o, n in SO: edit(os.path.join(cl, "SolOrders.lua"), o, n)

# ---------------------------------------------------------------- the Mind
CS = [
    ('FAR_NO_SPOT = "ما لقيت مكان قريب منك أوصل عليه، تحرك شوي وجرب كمان مرة."', 'FAR_NO_SPOT = "علقت شوي بالطريق، ناديني كمان مرة بعد شوي."'),
    ('FAR_NO_CAR = "لسا ما بقدر أجيب السيارة من بعيد. إذا بدك بجي مشي، قلي تعالي مشي."', 'FAR_NO_CAR = "ما بقدر جيب السيارة هلأ. إذا بدك بجي مشي، قلي تعالي مشي."'),
    ('FAR_AT_EDGE = "وصلت بالسيارة لطرف منطقتك من جهة البيت. قرب شوي من هديك الجهة وبتشوفني."', 'FAR_AT_EDGE = "صرت قريبة، عضّة كوساية وبوصل."'),
    ('_FAR_CAR_FAILED = "ما قدرت أجيب السيارة هلأ. إذا بدك بجي مشي، قلي تعالي مشي."', '_FAR_CAR_FAILED = "علقت شوي، ناديني كمان مرة بعد شوي."'),
    ('FAR_CAR_NO.update({"no_route": "ما لقيت طريق للسيارة لعندك. إذا بدك بجي مشي، قلي تعالي مشي.",', 'FAR_CAR_NO.update({"no_route": "ما بقدر جيب السيارة هلأ. إذا بدك بجي مشي، قلي تعالي مشي.",'),
    ('"car_too_close": "سيارتي قريبة منك بس مو ظاهرة. قرب منها شوي وبرجع جربها، أو قلي تعالي مشي."})', '"car_too_close": "سيارتي قريبة منك، قرب منها شوي أو قلي تعالي مشي."})'),
    ('FAR_ENDED["record_failed"] = "وصلت السيارة لطرف منطقتك من جهة البيت، بس أنا ما قدرت أوصل معها. قلي تعالي مشي وبجي."', 'FAR_ENDED["record_failed"] = "علقت شوي، ناديني كمان مرة بعد شوي."'),
    ('FAR_ENDED["left_behind"] = "ضليت أنا والسيارة بطرف منطقتك من جهة البيت، بس أنت بعدت. ارجع من هديك الجهة وبتلاقينا."',
     'FAR_ENDED["left_behind"] = "ضليت ناطرتك بالسيارة، تعا لعندي."\n'
     'FAR_CAR_MOVE_FAILED = frozenset(("loaded", "target_loaded", "not_in_db", "in_meta", "blob_mismatch", "spot_taken", "move_timeout", "no_java", "record_failed"))      # far_arrival: she walks instead'),
    ('self._forced = far_wait_line(reason, "ما في سيارة بتمشي جنبي هلأ، جاية مشي، بدي %s.")', 'self._forced = far_wait_line(reason, "جاية مشي، بدي %s.")'),
    ('def far_cars_line(reason):', 'def _num(s):\n    try: return float(s)\n    except (TypeError, ValueError): return 99.0\n\n\ndef far_cars_line(reason):'),
    ('        bit = "%s%s على بعد %s خطوة، %s" % (name, " (سيارتي)" if mine == "1" else "", d, FAR_CARS_STATE.get(verdict, "ما بعرف وضعها"))\n        if verdict == "ok" and fuel != "?": bit += "، فيها %s لتر" % fuel',
     '        near = "قريبة" if _num(d) < 15 else "مش بعيدة" if _num(d) < 40 else "بعيدة شوي"                    # far_arrival: no step counts, no litres\n        bit = "%s%s %s، %s" % (name, " (سيارتي)" if mine == "1" else "", near, FAR_CARS_STATE.get(verdict, "ما بعرف وضعها"))'),
    ('        m = re.match(r"^car:(-?\\d+),(-?\\d+),(-?\\d+),(-?\\d+),(\\d+)$", reason) if isinstance(r, dict) and r.get("ok") else None',
     '        m = re.match(r"^car:(-?\\d+),(-?\\d+),(-?\\d+),(-?\\d+),(\\d+)(?:,(\\w+))?(,in)?$", reason) if isinstance(r, dict) and r.get("ok") else None'),
    ('        cx, cy, px, py, ring = (int(v) for v in m.groups())\n        spot = RR.pickup_spot(cx, cy, px, py, ring)',
     '        cx, cy, px, py, ring = (int(v) for v in m.groups()[:5])\n        kind = m.group(6) or "car"\n        inside = m.group(7) is not None                                    # far_arrival: the game can bring it into the loaded area\n        spot = RR.pickup_spot_dir(cx, cy, px, py, ring, kind, inner=inside)   # far_arrival: a straight stretch of road (an open place for a helicopter)'),
    ('        return "car_far:%.1f,%.1f,%.0f" % spot, None', '        return ("car_far:%.1f,%.1f,%.0f,%.0f" % spot) + (",in" if inside else ""), None'),
    # "here" after a far car: she is at the wheel; one line, then the drive (quiet: the goal does not talk over it)
    ('                goal = getattr(self, "_far_drive_goal", None) or IE.make_goal("fetch_player", {"then": "stay_with_player"}, source="deterministic", text="")',
     '                goal = getattr(self, "_far_drive_goal", None) or IE.make_goal("fetch_player", {"then": "stay_with_player"}, source="deterministic", text="")\n'
     '                if mode == "car_far":                                            # far_arrival: she came with the car, at the wheel\n'
     '                    goal.setdefault("slots", {})["quiet"] = "1"\n'
     '                    with self.lock: self.hist.append({"role": "sol", "text": FAR_AT_EDGE, "t": time.time()})\n'
     '                    self._save(); self.publish()'),
    ('        elif reason == "placed" and mode == "car_far":\n            if not getattr(self, "_far_told_edge", False):',
     '        elif reason == "placed" and mode == "car_far" and False:                  # far_arrival: nothing to say until she is there\n            if not getattr(self, "_far_told_edge", False):'),
    ('        elif reason == "placed" and mode != "car": self._far_waiting = False\n',
     '        elif reason.startswith("on_foot:") and mode == "car_far":                 # far_arrival: she walks instead, said once in her words\n'
     '            self._far_waiting = "foot"\n'
     '            with self.lock: self.hist.append({"role": "sol", "text": FAR_ON_WAY, "t": time.time()})\n'
     '            self._save(); self.publish()\n'
     '        elif mode == "car_far" and reason in FAR_CAR_MOVE_FAILED and isinstance(p, dict) and p.get("ok"):\n'
     '            r = run_action(self.dir, "sol_far", "come", wait=2.5)                 # the car could not come: she walks, nothing said about why\n'
     '            self.log("chat: far car ended %s, on foot -> %s" % (reason, r))\n'
     '            ok_foot = isinstance(r, dict) and r.get("ok") and str(r.get("reason")).startswith("waiting:")\n'
     '            self._far_waiting = "foot" if ok_foot else False\n'
     '            with self.lock: self.hist.append({"role": "sol", "text": FAR_ON_WAY if ok_foot else _FAR_CAR_FAILED, "t": time.time()})\n'
     '            self._save(); self.publish()\n'
     '        elif reason == "placed" and mode not in ("car", "car_far"): self._far_waiting = False\n'),
]
# what the first s72 (installed 2026-11-10 20:14) wrote for the lines this one writes differently
UPGRADE = {'        m = re.match(r"^car:(-?\\d+),(-?\\d+),(-?\\d+),(-?\\d+),(\\d+)(?:,(\\w+))?(,in)?$", reason) if isinstance(r, dict) and r.get("ok") else None': ['        m = re.match(r"^car:(-?\\d+),(-?\\d+),(-?\\d+),(-?\\d+),(\\d+)(?:,(\\w+))?$", reason) if isinstance(r, dict) and r.get("ok") else None'], '        cx, cy, px, py, ring = (int(v) for v in m.groups()[:5])\n        kind = m.group(6) or "car"\n        inside = m.group(7) is not None                                    # far_arrival: the game can bring it into the loaded area\n        spot = RR.pickup_spot_dir(cx, cy, px, py, ring, kind, inner=inside)   # far_arrival: a straight stretch of road (an open place for a helicopter)': ['        cx, cy, px, py, ring = (int(v) for v in m.groups()[:5])\n        kind = m.group(6) or "car"\n        spot = RR.pickup_spot_dir(cx, cy, px, py, ring, kind)                 # far_arrival: a straight stretch of road (an open place for a helicopter)'], '        return ("car_far:%.1f,%.1f,%.0f,%.0f" % spot) + (",in" if inside else ""), None': ['        return "car_far:%.1f,%.1f,%.0f,%.0f" % spot, None']}

GE = [
    ('            self._speak("جايتك، استناني.")\n            return\n',
     '            if not g.get("spoke") and not slots.get("quiet"): self._speak("جايتك، استناني.")      # far_arrival: once, and not over her arrival line\n'
     '            g["spoke"] = True\n            return\n'),
    ('math.hypot(xy[0] - to["x"], xy[1] - to["y"]) > 40:', 'math.hypot(xy[0] - to["x"], xy[1] - to["y"]) > 12:      # far_arrival: where he is now'),
]

def mind(md):
    for name, edits in (("chat_service.py", CS), ("goal_engine.py", GE)):
        p = os.path.join(md, name)
        for o, n in edits:
            t = open(p, encoding="utf-8", newline="").read()
            nl = CRLF if CRLF in t else NL
            if n.replace(NL, nl) in t: continue
            if o.replace(NL, nl) not in t:                                          # the first s72 (installed 2026-11-10 20:14) wrote it differently
                for first in UPGRADE.get(n, ()):
                    if first.replace(NL, nl) in t: o = first; break
            edit(p, o, n)
    rr = os.path.join(md, "road_route.py")
    t = open(rr, encoding="utf-8").read()
    if "def pickup_spot_dir(" not in t or "inner=False" not in t:     # the first s72 (20:14) appended a pickup_spot_dir without inner=:
        add = open(os.path.join(HERE, "src", "road_route_spot.py"), encoding="utf-8").read()     # appended again, the later defs win
        with open(rr, "a", encoding="utf-8", newline="") as h: h.write(add)

if __name__ == "__main__":
    CL, MD = sys.argv[1], sys.argv[2]
    if CL != "-": client(CL)
    if MD != "-": mind(MD)
    print("far_arrival applied")

-- SolSmartPark.lua - switch smart_park (s87, ledger A1; council SOL_REVIEW section 45).
-- "park the car" (safi as-sayyara) anywhere, not only at the home garage (home_parks stays the garage): the game lists the free spots near her
-- car, takes the nearest one the car fits in that blocks no road and no door, and after the drive checks that the whole car
-- stands inside that spot. The Mind drives there (GPS, like the garage park) and asks this file three things:
--   sol_smart_park find    -> ok "spot:cx,cy,x1,y1,x2,y2,kind,n"  (kind = stall | open, n = spots looked at)
--                             ok "already:x1,y1,x2,y2"             (the car already stands inside a free spot)
--                             fail no_car | no_spot | not_loaded | sol_not_available
--   sol_smart_park settle  -> LF's own precise last segment (SC.Driving.approach, the same one the garage park uses) to the
--                             middle of the chosen spot, after the GPS drive arrived. ok "approaching" | fail <LF reason>
--   sol_smart_park status  -> ok "working" | ok "inside" | ok "outside:<corners out>" | fail <reason>
-- Spots, nearest first:
--   stall  the map's own parking zones (getVehicleZoneAt, type ParkingStall; the traffic-jam zones lie on the road and are
--          skipped). A row of stalls is cut into bays the car's size; the car stands along the short side when it fits it.
--   open   only when no stall is free: a car-sized box of open outdoor ground off every road of the map's road graph
--          (SolStaticRoads, the road's half width + a margin), never inside a building.
--   every bay: loaded, ground floor, nothing solid, no other car on it or overlapping it, no door on it or next to it.
-- No vehicle or place names anywhere: only sizes and what is on the squares.
require "SolActions"
SolUI = SolUI or {}
local U = SolUI
SolSmartPark = SolSmartPark or {}
local M = SolSmartPark
M.VERSION = "0.1.0"
M.STALL_REACH = 40        -- tiles around the car where map stalls are looked for
M.OPEN_REACH = 24         -- tiles around the car for open ground
M.SCAN_STEP = 2           -- zone probe spacing (a stall is at least 3 wide)
M.MAX_CHECK = 160         -- bays checked per kind, nearest first
M.MARGIN = 0.3            -- a bay must be this much longer and wider than the car
M.DOOR_GAP = 1            -- no door on the bay or this many squares around it
M.ROAD_GAP = 0.5          -- open ground keeps this far beyond a road's half width
M.CAR_REACH = 10          -- on foot: her car is the nearest one within this
M.INSIDE_SLACK = 0.15     -- a footprint corner may stick out this much and still count as inside
M.ROAD_CELL, M.ROAD_KEY = 64, 4096   -- SolStaticRoads' grid (CELL, cellKey = cx * 4096 + cy); test_s87 checks they match

local function g(name) return rawget(_G, name) end
local function log(m) print("[SolSmartPark] " .. tostring(m)) end
local function finite(v) return type(v) == "number" and v == v and v < 1e30 and v > -1e30 and v or nil end
local function vcall(o, name, ...)
    if o == nil then return nil end
    local ok0, f = pcall(function() return o[name] end)
    if not ok0 or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function num(o, name, ...) return finite(tonumber((vcall(o, name, ...)))) end
local function switchOn()
    local A = g("SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("smart_park") == true
end
local function LF() local sc = g("SurvivorCompanion"); if type(sc) == "table" then return sc end; return nil end
local function solActor() if type(U.solActor) == "function" then return U.solActor() end; return nil end
local function isA(o, cls)
    local f = g("instanceof")
    if type(f) ~= "function" or o == nil then return false end
    local ok, v = pcall(f, o, cls)
    return ok and v == true
end

-- ---------------------------------------------------------------- the car
local function loadedCars()
    local SC = LF()
    if SC and type(SC.Vehicle) == "table" and type(SC.Vehicle.loadedVehicles) == "function" then
        local ok, list = pcall(SC.Vehicle.loadedVehicles)
        if ok and type(list) == "table" then return list end
    end
    local out = {}
    local cell = type(getCell) == "function" and getCell() or nil
    local vs = vcall(cell, "getVehicles")
    local n = tonumber((vcall(vs, "size"))) or 0
    for i = 0, n - 1 do out[#out + 1] = vcall(vs, "get", i) end
    return out
end

function M.herCar(s)
    local car = vcall(s, "getVehicle")
    if car ~= nil then return car end
    local sx, sy = num(s, "getX"), num(s, "getY")
    if sx == nil then return nil end
    local best, bestD = nil, M.CAR_REACH * M.CAR_REACH
    for _, v in ipairs(loadedCars()) do
        local vx, vy = num(v, "getX"), num(v, "getY")
        if vx and vy then
            local d = (vx - sx) ^ 2 + (vy - sy) ^ 2
            local okE = type(U.solCarEligible) ~= "function" or U.solCarEligible(v, s) ~= false
            if d < bestD and okE then best, bestD = v, d end
        end
    end
    return best
end

-- four corners {x1..y4}: LF's own footprint (the car's physics box), else centre + heading + the script's extents
function M.footprint(car)
    local SC = LF()
    local EC = SC and SC.ExpeditionCar
    if type(EC) == "table" and type(EC.footprint) == "function" then
        local ok, p = pcall(EC.footprint, car)
        if ok and type(p) == "table" and finite(p.x1) and finite(p.y4) then return p end
    end
    local cx, cy = num(car, "getX"), num(car, "getY")
    if cx == nil or cy == nil then return nil end
    local ext = vcall(vcall(car, "getScript"), "getExtents")
    local long, wide = num(ext, "z"), num(ext, "x")
    local hl = long and long > 1 and long * 0.5 or 2.4
    local hw = wide and wide > 0.5 and wide * 0.5 or 1.0
    local fx, fy = num(car, "getForwardDirectionX"), num(car, "getForwardDirectionY")
    local Vec = g("Vector3f")
    local fwd = Vec ~= nil and type(Vec.new) == "function" and vcall(car, "getForwardVector", Vec.new()) or nil
    fx = num(fwd, "x") or fx
    fy = num(fwd, "z") or fy
    if fx == nil or fy == nil or fx * fx + fy * fy < 0.01 then fx, fy = 0, 1 end
    local l = math.sqrt(fx * fx + fy * fy); fx, fy = fx / l, fy / l
    local ax, ay, bx, by = fx * hl, fy * hl, -fy * hw, fx * hw
    return { x1 = cx + ax + bx, y1 = cy + ay + by, x2 = cx + ax - bx, y2 = cy + ay - by,
             x3 = cx - ax - bx, y3 = cy - ay - by, x4 = cx - ax + bx, y4 = cy - ay + by }
end

-- length and width of the car from its corners
function M.size(poly)
    local function d(a, b) return math.sqrt((poly["x" .. a] - poly["x" .. b]) ^ 2 + (poly["y" .. a] - poly["y" .. b]) ^ 2) end
    local e1, e2 = d(1, 2), d(2, 3)
    return math.max(e1, e2), math.min(e1, e2)
end

local function box(poly)
    local x0, y0, x1, y1 = 1e30, 1e30, -1e30, -1e30
    for i = 1, 4 do
        local x, y = poly["x" .. i], poly["y" .. i]
        if x < x0 then x0 = x end; if x > x1 then x1 = x end
        if y < y0 then y0 = y end; if y > y1 then y1 = y end
    end
    return x0, y0, x1, y1
end

-- corners of the footprint outside the bay (tiles x1..x2, y1..y2 inclusive)
function M.cornersOut(poly, bay, slack)
    slack = slack or M.INSIDE_SLACK
    local n = 0
    for i = 1, 4 do
        local x, y = poly["x" .. i], poly["y" .. i]
        if x < bay.x1 - slack or x > bay.x2 + 1 + slack or y < bay.y1 - slack or y > bay.y2 + 1 + slack then n = n + 1 end
    end
    return n
end

-- ---------------------------------------------------------------- bays
-- a zone's tiles -> bays the car fits in; the car stands along the short side when that side holds its length (a row)
function M.baysOf(zx, zy, zw, zh, L, W, kind)
    local out = {}
    local needL, needW = L + M.MARGIN, W + M.MARGIN
    local short, long = math.min(zw, zh), math.max(zw, zh)
    local alongX
    if short >= needL then alongX = (zw <= zh)
    elseif long >= needL and short >= needW then alongX = (zw >= zh)
    else return out end
    local spanAlong, spanAcross = alongX and zw or zh, alongX and zh or zw
    local bayL = spanAlong >= 2 * needL and math.ceil(needL) or spanAlong
    local bayW = spanAcross >= 2 * needW and math.max(3, math.ceil(needW)) or spanAcross
    local a = 0
    while a + bayL <= spanAlong do
        local c = 0
        while c + bayW <= spanAcross do
            local b
            if alongX then b = { x1 = zx + a, x2 = zx + a + bayL - 1, y1 = zy + c, y2 = zy + c + bayW - 1 }
            else b = { x1 = zx + c, x2 = zx + c + bayW - 1, y1 = zy + a, y2 = zy + a + bayL - 1 } end
            b.kind = kind
            out[#out + 1] = b
            c = c + bayW
        end
        a = a + bayL
    end
    return out
end

local function skipZone(z)
    local name = string.lower(tostring(vcall(z, "getName") or ""))
    local typ = string.lower(tostring(vcall(z, "getType") or ""))
    if typ ~= "" and typ ~= "parkingstall" then return true end
    return string.find(name, "trafficjam", 1, true) ~= nil
end

function M.stallBays(cx, cy, L, W)
    local probe = g("getVehicleZoneAt")
    local out, seen = {}, {}
    if type(probe) ~= "function" then return out end
    local r, step = M.STALL_REACH, M.SCAN_STEP
    local x0, y0 = math.floor(cx), math.floor(cy)
    for x = x0 - r, x0 + r, step do
        for y = y0 - r, y0 + r, step do
            local ok, z = pcall(probe, x, y, 0)
            if ok and z ~= nil then
                local zx, zy, zw, zh = num(z, "getX"), num(z, "getY"), num(z, "getWidth"), num(z, "getHeight")
                if zx and zy and zw and zh then
                    local key = zx .. "," .. zy .. "," .. zw .. "," .. zh
                    if not seen[key] then
                        seen[key] = true
                        if not skipZone(z) then
                            for _, b in ipairs(M.baysOf(zx, zy, zw, zh, L, W, "stall")) do out[#out + 1] = b end
                        end
                    end
                end
            end
        end
    end
    return out
end

function M.openBays(cx, cy, L, W)
    local out = {}
    local bl, bw = math.ceil(L + M.MARGIN), math.max(2, math.ceil(W + M.MARGIN))
    local r = M.OPEN_REACH
    local x0, y0 = math.floor(cx), math.floor(cy)
    for x = x0 - r, x0 + r, 2 do
        for y = y0 - r, y0 + r, 2 do
            out[#out + 1] = { x1 = x, x2 = x + bl - 1, y1 = y, y2 = y + bw - 1, kind = "open" }
            out[#out + 1] = { x1 = x, x2 = x + bw - 1, y1 = y, y2 = y + bl - 1, kind = "open" }
        end
    end
    return out
end

local function centre(b) return (b.x1 + b.x2 + 1) * 0.5, (b.y1 + b.y2 + 1) * 0.5 end
local function sortNear(list, cx, cy)
    for _, b in ipairs(list) do local x, y = centre(b); b.d = (x - cx) ^ 2 + (y - cy) ^ 2 end
    table.sort(list, function(p, q) return p.d < q.d end)
    return list
end

-- ---------------------------------------------------------------- what is on the squares
local function isDoor(o)
    if isA(o, "IsoDoor") then return true end
    if isA(o, "IsoThumpable") and vcall(o, "isDoor") == true then return true end
    return false
end
local function squareHasDoor(sq)
    local objs = vcall(sq, "getObjects")
    local n = tonumber((vcall(objs, "size"))) or 0
    for i = 0, math.min(n, 24) - 1 do
        if isDoor(vcall(objs, "get", i)) then return true end
    end
    return false
end
local function squareOpen(sq, x, y)
    if vcall(sq, "isSolid") == true or vcall(sq, "isSolidTrans") == true then return false end
    if vcall(sq, "getRoom") ~= nil then return false end
    local B = g("SolBypass")
    if type(B) == "table" and type(B.world) == "table" and type(B.world.kind) == "function" then
        local ok, k = pcall(B.world.kind, x, y)
        if ok and k ~= nil then return false end
    end
    return true
end

-- other cars as boxes (her own car is not in the way of its own spot)
local function otherBoxes(car)
    local out = {}
    for _, v in ipairs(loadedCars()) do
        if v ~= nil and v ~= car then
            local p = M.footprint(v)
            if p then local x0, y0, x1, y1 = box(p); out[#out + 1] = { x0 = x0, y0 = y0, x1 = x1, y1 = y1 } end
        end
    end
    return out
end

-- road pieces of the map's graph near a point: {ax, ay, bx, by, half}
local function roadPieces(cx, cy, reach)
    local R = g("SolStaticRoads")
    if type(R) ~= "table" or type(R.load) ~= "function" then return nil end
    local ok, G = pcall(R.load)
    if not ok or type(G) ~= "table" or type(G.GRID) ~= "table" then return nil end
    local out, seen = {}, {}
    local C = M.ROAD_CELL
    local r = math.ceil(reach / C) + 1
    local kx, ky = math.floor(cx / C), math.floor(cy / C)
    for x = kx - r, kx + r do
        for y = ky - r, ky + r do
            local list = G.GRID[x * M.ROAD_KEY + y]
            if list then
                for i = 1, #list do
                    local e = list[i]
                    if not seen[e] then
                        seen[e] = true
                        local a, b = G.EA[e], G.EB[e]
                        out[#out + 1] = { ax = G.NX[a], ay = G.NY[a], bx = G.NX[b], by = G.NY[b], half = (tonumber(G.EW[e]) or 6) * 0.5 }
                    end
                end
            end
        end
    end
    return out
end
local function segDist(px, py, ax, ay, bx, by)
    local dx, dy = bx - ax, by - ay
    local l = dx * dx + dy * dy
    local t = 0
    if l > 0.0001 then t = ((px - ax) * dx + (py - ay) * dy) / l; if t < 0 then t = 0 elseif t > 1 then t = 1 end end
    local qx, qy = ax + dx * t, ay + dy * t
    return math.sqrt((px - qx) ^ 2 + (py - qy) ^ 2)
end
function M.onRoad(b, pieces)
    if pieces == nil then return true end           -- no road map: open ground is never chosen
    for x = b.x1, b.x2 do
        for y = b.y1, b.y2 do
            local px, py = x + 0.5, y + 0.5
            for i = 1, #pieces do
                local p = pieces[i]
                if segDist(px, py, p.ax, p.ay, p.bx, p.by) < p.half + M.ROAD_GAP + 0.5 then return true end
            end
        end
    end
    return false
end

-- why a bay cannot take the car, nil when it can
function M.bayProblem(cell, b, others, pieces)
    for x = b.x1 - M.DOOR_GAP, b.x2 + M.DOOR_GAP do
        for y = b.y1 - M.DOOR_GAP, b.y2 + M.DOOR_GAP do
            local sq = vcall(cell, "getGridSquare", x, y, 0)
            local inside = x >= b.x1 and x <= b.x2 and y >= b.y1 and y <= b.y2
            if sq == nil then if inside then return "not_loaded" end
            else
                if squareHasDoor(sq) then return "door" end
                if inside and not squareOpen(sq, x, y) then return "blocked" end
            end
        end
    end
    for _, o in ipairs(others) do
        if b.x1 < o.x1 and b.x2 + 1 > o.x0 and b.y1 < o.y1 and b.y2 + 1 > o.y0 then return "taken" end
    end
    if b.kind == "open" and M.onRoad(b, pieces) then return "road" end
    return nil
end

-- ---------------------------------------------------------------- the verbs
M.job = M.job or nil      -- { bay, phase = drive | approach | done, at }

function M.find()
    local s = solActor()
    if s == nil then return false, "sol_not_available" end
    local car = M.herCar(s)
    if car == nil then return false, "no_car" end
    local poly = M.footprint(car)
    if poly == nil then return false, "no_car" end
    local L, W = M.size(poly)
    local cx, cy = num(car, "getX"), num(car, "getY")
    local cell = type(getCell) == "function" and getCell() or nil
    if cell == nil or cx == nil then return false, "not_loaded" end
    local others = otherBoxes(car)
    local looked, why = 0, {}
    local function pick(list, pieces)
        sortNear(list, cx, cy)
        for i = 1, math.min(#list, M.MAX_CHECK) do
            local b = list[i]
            looked = looked + 1
            local p = M.bayProblem(cell, b, others, pieces)
            if p == nil then return b end
            why[p] = (why[p] or 0) + 1
        end
        return nil
    end
    local bay = pick(M.stallBays(cx, cy, L, W), nil)
    if bay == nil then bay = pick(M.openBays(cx, cy, L, W), roadPieces(cx, cy, M.OPEN_REACH + 8)) end
    local parts = {}
    for k, v in pairs(why) do parts[#parts + 1] = k .. "=" .. v end
    if bay == nil then
        log(string.format("no spot for a %.1fx%.1f car near %d,%d (%d looked at: %s)", L, W, math.floor(cx), math.floor(cy), looked, table.concat(parts, " ")))
        M.job = nil
        return false, "no_spot"
    end
    local bx, by = centre(bay)
    log(string.format("spot %s %d,%d-%d,%d for a %.1fx%.1f car, %.1f tiles away (%d looked at: %s)", bay.kind, bay.x1, bay.y1,
        bay.x2, bay.y2, L, W, math.sqrt(bay.d), looked, table.concat(parts, " ")))
    if M.cornersOut(poly, bay) == 0 then
        M.job = nil
        return true, string.format("already:%d,%d,%d,%d", bay.x1, bay.y1, bay.x2, bay.y2)
    end
    M.job = { bay = bay, phase = "drive", at = type(getTimestampMs) == "function" and getTimestampMs() or 0 }
    return true, string.format("spot:%.1f,%.1f,%d,%d,%d,%d,%s,%d", bx, by, bay.x1, bay.y1, bay.x2, bay.y2, bay.kind, looked)
end

function M.settle()
    local j = M.job
    if j == nil then return false, "no_spot" end
    local SC = LF()
    local D = SC and SC.Driving
    if type(D) ~= "table" or type(D.approach) ~= "function" then return false, "lf_unavailable" end
    local s = solActor()
    if s == nil then return false, "sol_not_available" end
    local bx, by = centre(j.bay)
    local okA, accepted, reason = pcall(D.approach, s, { x = bx, y = by, z = 0 }, 30000)
    if not okA then return false, "park_error" end
    if accepted ~= true then return false, tostring(reason or "park_refused") end
    j.phase = "approach"
    log(string.format("last metres to %.1f,%.1f", bx, by))
    return true, "approaching"
end

function M.status()
    local j = M.job
    if j == nil then return false, "no_spot" end
    local s = solActor()
    if s == nil then return false, "sol_not_available" end
    local SC = LF()
    local D = SC and SC.Driving
    if j.phase == "approach" then
        if type(D) ~= "table" or type(D.jobStatus) ~= "function" then return false, "lf_unavailable" end
        local okJ, js = pcall(D.jobStatus, s)
        if not okJ or type(js) ~= "table" then return false, "no_drive" end
        if js.result == "failed" then M.job = nil; return false, tostring(js.reason or "park_failed") end
        if js.result ~= "arrived" then return true, "working" end
    end
    local car = M.herCar(s)
    local poly = car and M.footprint(car) or nil
    if poly == nil then return false, "no_car" end
    local out = M.cornersOut(poly, j.bay)
    M.job = nil
    log(string.format("parked: %d corner(s) outside %d,%d-%d,%d", out, j.bay.x1, j.bay.y1, j.bay.x2, j.bay.y2))
    if out == 0 then return true, "inside" end
    return true, "outside:" .. out
end

local VERBS = { find = M.find, settle = M.settle, status = M.status }

function M.wrap()
    if M._wrapped then return end
    M._wrapped = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id ~= "sol_smart_park" then return base(id, option) end
        if not switchOn() then return false, "fix_off" end
        local f = VERBS[tostring(option or "")]
        if f == nil then return false, "unknown_option" end
        local ok, a, b = pcall(f)
        if not ok then log("error: " .. tostring(a)); return false, "smart_park_error" end
        return a, b
    end
    log("ready v" .. M.VERSION)
end

function M.install()
    if M._installed then return end
    M._installed = true
    if Events and Events.OnTick then
        local function once()
            if not M._wrapped then M.wrap() end
            if Events.OnTick.Remove then Events.OnTick.Remove(once) end
        end
        Events.OnTick.Add(once)
    else
        M.wrap()
    end
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(M.install) end
return M

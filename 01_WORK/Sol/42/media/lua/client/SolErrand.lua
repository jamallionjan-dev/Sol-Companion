-- SolErrand.lua - the game side of "go and empty the car at home, then come back".
--   Sol Mind plans the trip (goal_engine.HomeErrand); this file answers three questions through the action mailbox.
--   The unloading itself is Living Fellows' own verified base job (SCVehicleUnload): items stay in the trunk, the worker
--   or the marked destination at every step. It needs an LF base with a parking area and storage; without them we say so.
--   Switch: SolAuthority "home_errand".
SolUI = SolUI or {}
SolErrand = SolErrand or {}
local U, E = SolUI, SolErrand
E.VERSION = "0.1.0"
local function log(m) print("[SolErrand] " .. tostring(m)) end

local function enabled()
    local A = rawget(_G, "SolAuthority")
    if type(A) ~= "table" or type(A.on) ~= "function" then return false end
    local ok, on = pcall(A.on, "home_errand")
    return ok and on == true
end

local function LF()
    local sc = rawget(_G, "SurvivorCompanion")
    if type(sc) == "table" then return sc end
    return nil
end

local function ready()
    local SC = LF()
    if not (SC and type(SC.BaseLife) == "table" and type(SC.BaseLife.active) == "function"
            and type(SC.VehicleUnload) == "table" and type(SC.ExpeditionCar) == "table") then
        return nil, "lf_unavailable"
    end
    local ok, base = pcall(SC.BaseLife.active)
    if not ok or type(base) ~= "table" then return nil, "no_base" end
    return SC, base
end

local function parkingCentre(SC)
    local ok, zones = pcall(SC.ExpeditionCar.parkingAreas)
    if not ok or type(zones) ~= "table" or zones[1] == nil then return nil end
    local z = zones[1]
    return math.floor((z.x1 + z.x2) / 2), math.floor((z.y1 + z.y2) / 2)
end

-- where to bring the car: the middle of the base's first valid parking area
function E.parking()
    local SC, why = ready()
    if not SC then return false, why end
    local x, y = parkingCentre(SC)
    if not x then return false, "no_parking_area" end
    return true, string.format("parking:%d,%d", x, y)
end

-- GPS "arrived" stops some tiles short, and LF only unloads a car whose whole footprint is inside the parking area.
-- Driving.approach is LF's precise last segment for an arrived drive.
function E.park()
    local SC, why = ready()
    if not SC then return false, why end
    local sol = type(U.solActor) == "function" and U.solActor() or nil
    if sol == nil then return false, "sol_not_available" end
    local x, y = parkingCentre(SC)
    if not x then return false, "no_parking_area" end
    local okA, accepted, reason = pcall(SC.Driving.approach, sol, { x = x + 0.5, y = y + 0.5, z = 0 }, 30000)
    if not okA then return false, "park_error" end
    if accepted ~= true then return false, tostring(reason or "park_refused") end
    return true, "approaching"
end

function E.parkStatus()
    local SC, why = ready()
    if not SC then return false, why end
    local sol = type(U.solActor) == "function" and U.solActor() or nil
    if sol == nil then return false, "sol_not_available" end
    local okJ, js = pcall(SC.Driving.jobStatus, sol)
    if not okJ or type(js) ~= "table" then return false, "no_drive" end
    if js.result == "arrived" then return true, "done" end
    if js.result == "failed" then return false, tostring(js.reason or "park_failed") end
    return true, "working"
end

local function openJob(base, vehicleId)
    for _, job in ipairs(base.jobs or {}) do
        if job.type == "unload_vehicle" and job.state ~= "completed" and job.state ~= "cancelled"
                and type(job.target) == "table" and tonumber(job.target.vehicleId) == vehicleId then
            return job
        end
    end
    return nil
end

local function trunkRow(SC, vehicleId)
    local ok, rows = pcall(SC.VehicleUnload.rows)
    if not ok or type(rows) ~= "table" then return nil end
    for _, row in ipairs(rows) do
        if row.id == vehicleId then return row end
    end
    return nil
end

local function nearestCargoCar(SC, sol)
    local okRows, rows = pcall(SC.VehicleUnload.rows)
    if not okRows or type(rows) ~= "table" or rows[1] == nil then return nil, false end
    local best, bestD = nil, nil
    for _, row in ipairs(rows) do
        if row.count > 0 then
            local okCar, car = pcall(SC.Vehicle.loadedBySqlId, row.id)
            if okCar and car ~= nil then
                local d = (car:getX() - sol:getX()) ^ 2 + (car:getY() - sol:getY()) ^ 2
                if bestD == nil or d < bestD then best, bestD = row.id, d end
            end
        end
    end
    return best, true
end

function E.unload()
    local SC, why = ready()
    if not SC then return false, why end
    local sol = type(U.solActor) == "function" and U.solActor() or nil
    if sol == nil then return false, "sol_not_available" end
    local vehicleId, anyParked = nearestCargoCar(SC, sol)
    if vehicleId == nil then
        if anyParked then return true, "nothing_to_unload" end
        return false, "car_not_parked_at_base"
    end
    local okQ, accepted, reason = pcall(SC.VehicleUnload.queue, vehicleId)
    if not okQ then return false, "unload_error" end
    if accepted ~= true and reason ~= "car_unload_already_queued" then return false, tostring(reason or "unload_refused") end
    E.vehicleId = vehicleId
    -- the quartermaster weighs car unloading above her other base work; entering the role puts her on base duty
    local okR, roleOk, roleWhy = pcall(U.solRole, "quartermaster")
    if not okR or roleOk ~= true then
        E.vehicleId = nil
        return false, "role_" .. tostring(okR and roleWhy or "error")
    end
    log("unload queued for car " .. tostring(vehicleId))
    return true, "unload_started"
end

function E.status()
    local SC, base = ready()
    if not SC then return false, base end
    if E.vehicleId == nil then return false, "no_unload_job" end
    local row = trunkRow(SC, E.vehicleId)
    local left = row and row.count or -1
    local job = openJob(base, E.vehicleId)
    if job == nil then return true, "done:" .. tostring(left) end
    return true, "working:" .. tostring(job.state) .. ":" .. tostring(left)
end

-- she was only on base duty for this errand: back to the ordinary role, which also ends the granted work
function E.finish()
    E.vehicleId = nil
    if type(U.solRole) ~= "function" then return true, "finished" end
    local ok, done, why = pcall(U.solRole, "generalist")
    if not ok or done ~= true then log("role reset: " .. tostring(ok and why or done)) end
    return true, "finished"
end

local VERBS = {
    sol_errand_parking = E.parking, sol_errand_park = E.park, sol_errand_park_status = E.parkStatus, sol_unload_car = E.unload,
    sol_unload_status = E.status, sol_errand_finish = E.finish,
}

local function install()
    if U._errandInstalled then return end
    U._errandInstalled = true
    local base = U.runAction
    U.runAction = function(id, option)
        local verb = VERBS[id]
        if verb == nil then return base(id, option) end
        if not enabled() then return false, "fix_off" end
        local ok, a, b = pcall(verb)
        if not ok then log(id .. " error: " .. tostring(a)); return false, "errand_error" end
        return a, b
    end
    log("verbs installed v" .. E.VERSION)
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(install) end

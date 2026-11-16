    local function finish()
    local vlist, vseen, vfree = {}, {}, {}
    local carsLoaded = {}                                                        -- getVehicles is a Set in B42: no get(i). The same list the rest of the mod uses.
    local carService = rawget(_G, "SurvivorCompanion") and SurvivorCompanion.Vehicle or nil
    if type(carService) == "table" and type(carService.loadedVehicles) == "function" then
        local okC, listC = pcall(carService.loadedVehicles)
        if okC and type(listC) == "table" then carsLoaded = listC end
    end
    for _, v0 in ipairs(carsLoaded) do
        if v0 and not vseen[v0] then vseen[v0] = true; vlist[#vlist + 1] = v0 end
    end
    for _, v0 in ipairs(U.invVehicleObjects and U.invVehicleObjects() or {}) do      -- found from the squares by the base inventory
        if not vseen[v0] then vseen[v0] = true; vfree[v0] = true; vlist[#vlist + 1] = v0 end
    end
    for vi = 1, #vlist do
        local v = vlist[vi]
        local vx, vy = num(call(v, "getX")), num(call(v, "getY"))
        if v and vx and vy and (vfree[v] or (math.abs(vx - px) <= RADIUS * 3 and math.abs(vy - py) <= RADIUS * 3)) then
            local name = call(call(v, "getScript"), "getName") or "vehicle"
            local gas = call(v, "getPartById", "GasTank")
            local info = { name = name, x = round(vx, 0), y = round(vy, 0), id = num(call(v, "getSqlId")) or num(call(v, "getId")),
                           fuel = gas and round(call(gas, "getContainerContentAmount"), 1) or nil,
                           fuelMax = gas and num(call(gas, "getContainerCapacity")) or nil }
            info.locked, info.key = carUse(v, sol)                                    -- s77 cars_near
            snap.vehicles[#snap.vehicles + 1] = info
            local pc = num(call(v, "getPartCount")) or 0
            for k = 0, pc - 1 do
                local part = call(v, "getPartByIndex", k)
                local ic = call(part, "getItemContainer")
                if ic then addContainer(snap, "vehicle", ic, { vehicle = name, part = call(part, "getId"), x = info.x, y = info.y }) end
            end
        end
    end
    -- s78 cars_away: the loaded cars around HER body, wherever he is (the Mind's cars_near). Read only. Absent when her body is not
    -- in the loaded world (sol.away): the Mind then asks sol_far "cars", the saved rows around her.
    local sx78, sy78 = num((call(sol, "getX"))), num((call(sol, "getY")))
    if sol ~= nil and snap.sol ~= nil and snap.sol.away ~= true and sx78 ~= nil and sy78 ~= nil then
        local REACH78 = 60
        snap.solVehicles = {}
        for vi = 1, #vlist do
            local v = vlist[vi]
            local vx, vy = num((call(v, "getX"))), num((call(v, "getY")))
            if vx ~= nil and vy ~= nil and math.abs(vx - sx78) <= REACH78 and math.abs(vy - sy78) <= REACH78 and #snap.solVehicles < 40 then
                local gas = call(v, "getPartById", "GasTank")
                local info = { name = call((call(v, "getScript")), "getName") or "vehicle", x = round(vx, 0), y = round(vy, 0),
                               id = num((call(v, "getSqlId"))) or num((call(v, "getId"))),
                               fuel = gas and round((call(gas, "getContainerContentAmount")), 1) or nil,
                               fuelMax = gas and num((call(gas, "getContainerCapacity"))) or nil }
                info.locked, info.key = carUse(v, sol)
                snap.solVehicles[#snap.solVehicles + 1] = info
            end
        end
    end
    -- s78 end
    return snap
    end
    -- the same squares in the same order as one loop would read them, but a few at a time
    local ci, ctr, xNow, yNow, zNow = 1, nil, nil, nil, nil
    local function step(budgetMs)
        local stopAt, n = nowMs() + budgetMs, 0
        while true do
            if not ctr then
                ctr = centers[ci]
                if not ctr then return true end
                xNow, yNow, zNow = ctr[1] - ctr[4], ctr[2] - ctr[4], ctr[3] - ZSPAN
            end
            visit(xNow, yNow, zNow)
            yNow = yNow + 1
            if yNow > ctr[2] + ctr[4] then
                yNow, xNow = ctr[2] - ctr[4], xNow + 1
                if xNow > ctr[1] + ctr[4] then
                    xNow, zNow = ctr[1] - ctr[4], zNow + 1
                    if zNow > ctr[3] + ZSPAN then ctr, ci = nil, ci + 1 end
                end
            end
            n = n + 1
            if n % 12 == 0 and nowMs() >= stopAt then return false end
        end
    end
    return { step = step, finish = finish }

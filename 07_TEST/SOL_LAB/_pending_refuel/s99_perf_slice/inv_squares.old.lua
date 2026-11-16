local function stepSquares(cell)
    local n = 0
    while job.si <= #job.squares and n < SQ_PER_STEP do
        local s = job.squares[job.si]; job.si = job.si + 1; n = n + 1
        local sq = method(cell, "getGridSquare", s[1], s[2], s[3])
        if sq == nil then if s[4] then model.unloaded = model.unloaded + 1 end
        else
            model.squares = model.squares + 1
            local room = method(method(sq, "getRoom"), "getName")
            readVehicle(method(sq, "getVehicleContainer"), "sq")
            local objs = method(sq, "getObjects")
            local cnt = objs and num(method(objs, "size")) or 0
            for i = 0, cnt - 1 do
                local o = method(objs, "get", i)
                if o ~= nil and not is(o, "IsoDeadBody") then
                    local litres = method(o, "hasWater") == true and num(method(o, "getFluidAmount")) or nil     -- what could fill a watering can, and where: water only
                    if litres ~= nil and litres > 0 and #model.waterSources < 64 then
                        model.waterSources[#model.waterSources + 1] = { x = s[1], y = s[2], z = s[3], oi = i, l = litres, tainted = method(o, "isTaintedWater") == true }
                    end
                    local cc = num(method(o, "getContainerCount")) or 0
                    for k = 0, cc - 1 do
                        local c = method(o, "getContainerByIndex", k)
                        if c ~= nil then job.conts[#job.conts + 1] = { cont = c, where = "house", depth = 0, room = room, x = s[1], y = s[2], z = s[3], oi = i, ci = k } end
                    end
                end
            end
        end
    end
    if job.si > #job.squares then job.phase = "vehicles" end
end

-- s99 perf_slice: one x column of one floor of one area, in the order of the old loops (invStart); then the squares phase
local function planColumn()
    local p = job.plan
    local r = job.rects[p.ri]
    if r == nil then job.plan = nil; job.phase = "squares"; return end
    if p.z == nil then p.z, p.x = r.z - Z_BELOW, r.x1 - MARGIN end
    local z, x, seen = p.z, p.x, p.seen
    for y = r.y1 - MARGIN, r.y2 + MARGIN do
        local k = (z + 8) * 4294967296 + x * 65536 + y
        if not seen[k] then
            seen[k] = true
            if #job.squares >= MAX_SQUARES then model.trunc = true else job.squares[#job.squares + 1] = { x, y, z, z == r.z } end
        end
    end
    p.x = x + 1
    if p.x > r.x2 + MARGIN then
        p.x, p.z = r.x1 - MARGIN, z + 1
        if p.z > r.z + Z_ABOVE then p.ri, p.z = p.ri + 1, nil end
    end
end
-- s99 perf_slice: one square is the unit; stepSquares does SQ_PER_STEP of them as before
local function squareOne(cell)
        local s = job.squares[job.si]; job.si = job.si + 1
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
local function stepSquares(cell)
    local n = 0
    while job.si <= #job.squares and n < SQ_PER_STEP do
        squareOne(cell); n = n + 1
    end
    if job.si > #job.squares then job.phase = "vehicles" end
end

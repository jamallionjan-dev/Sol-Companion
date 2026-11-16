    local seen = {}
    local A99_ = rawget(_G, "SolAuthority")                                       -- s99 perf_slice: the list of squares is made a column per unit
    if type(A99_) == "table" and type(A99_.on) == "function" and A99_.on("perf_slice") == true then
        job.phase, job.plan = "plan", { ri = 1, seen = seen }
    else
    for _, r in ipairs(rects) do
        for z = r.z - Z_BELOW, r.z + Z_ABOVE do
            for x = r.x1 - MARGIN, r.x2 + MARGIN do
                for y = r.y1 - MARGIN, r.y2 + MARGIN do
                    local k = (z + 8) * 4294967296 + x * 65536 + y
                    if not seen[k] then
                        seen[k] = true
                        if #job.squares >= MAX_SQUARES then model.trunc = true else job.squares[#job.squares + 1] = { x, y, z, z == r.z } end
                    end
                end
            end
        end
    end
    end
    model.noArea = (#rects == 0)

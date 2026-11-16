local function stepConts()
    local n = 0
    while job.ci <= #job.conts and n < CONT_PER_STEP do
        local e = job.conts[job.ci]; job.ci = job.ci + 1; n = n + 1
        if e.cont ~= nil then
            model.conts = model.conts + 1
            local list = method(e.cont, "getItems")
            local cnt = list and num(method(list, "size")) or 0
            local place = placeFor(e)
            for i = 0, cnt - 1 do
                local it = method(list, "get", i)
                if it ~= nil then
                    local d = itemRead(it)
                    addItem(model, e.where, d, e.label or e.room)
                    noteFarm(e, it, d, place)
                    if d.bag ~= nil and e.depth < MAX_DEPTH then
                        job.conts[#job.conts + 1] = { cont = d.bag, where = e.where, depth = e.depth + 1, label = e.label, room = e.room, x = e.x, y = e.y, z = e.z, oi = e.oi, ci = e.ci }
                    end
                end
            end
        end
    end
    if job.ci > #job.conts then job.phase = "finish" end
end

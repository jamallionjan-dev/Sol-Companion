-- s99 perf_slice: a container is opened (its items listed once, so a slice boundary never shifts them) and read an item at a time.
-- stepConts (switch off) is the old code; a container a slice left half read (switched off half way) is finished first.
local function contOpen(e)
    model.conts = model.conts + 1
    local list = method(e.cont, "getItems")
    local cnt = list and num(method(list, "size")) or 0
    local place = placeFor(e)
    local items = {}
    for i = 0, cnt - 1 do items[i + 1] = method(list, "get", i) or false end
    return { e = e, items = items, cnt = cnt, place = place, i = 0 }
end
local function contItem(c)
    local e, place = c.e, c.place
    c.i = c.i + 1
    local it = c.items[c.i]
                if it ~= nil and it ~= false then
                    local d = itemRead(it)
                    addItem(model, e.where, d, e.label or e.room)
                    noteFarm(e, it, d, place)
                    if d.bag ~= nil and e.depth < MAX_DEPTH then
                        job.conts[#job.conts + 1] = { cont = d.bag, where = e.where, depth = e.depth + 1, label = e.label, room = e.room, x = e.x, y = e.y, z = e.z, oi = e.oi, ci = e.ci }
                    end
                end
end
local function stepConts()
    if job.cur ~= nil then local c = job.cur; while c.i < c.cnt do contItem(c) end; job.cur = nil end
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
-- s99: one unit = one item, or opening the next container
local function contUnit()
    local c = job.cur
    if c ~= nil then
        if c.i < c.cnt then contItem(c); return end
        job.cur = nil
    end
    if job.ci > #job.conts then job.phase = "finish"; return end
    local e = job.conts[job.ci]; job.ci = job.ci + 1
    if e.cont ~= nil then job.cur = contOpen(e) end
end

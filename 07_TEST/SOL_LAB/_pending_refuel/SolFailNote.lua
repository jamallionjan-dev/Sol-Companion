-- SolFailNote.lua - s88: why something failed, in one place (open items A6, A7, A8).
--   SolFailNote.note(source, reason, detail)   one log line "[SolFail] ..." and SolFail_State.txt for the Mind's "why" answer
--   SolFailNote.bridge(site, cause, job, route) the cause behind bridge_failure: job.detail, "[SolDrive] bridge_failure at=..."
--   SolFailNote.keyLine(where, actor, car)     "[SolKeys] ..." her key numbers, his, the ones in the car, vs the car's key id
--   SolFailNote.orderEnd(text, job)            SolOrders' endFail: the order's own reason and how long / how often she tried
-- Log and file only: what she does is unchanged. The one spoken change (no "(reason)" after "busy") is in SolOrders.lua
-- behind the switch fail_reasons.
SolFailNote = SolFailNote or {}
local M = SolFailNote
M.VERSION = "0.1.0"
M.FILE = "SolFail_State.txt"
M.seq = M.seq or 0
local KEY_LIST_MAX, ITEMS_MAX, DEPTH_MAX = 12, 400, 3

local function nowMs() return (type(getTimestampMs) == "function" and getTimestampMs()) or 0 end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, v = pcall(f, o, ...)
    if ok then return v end
    return nil
end
local function clean(v, n)
    local s = tostring(v == nil and "" or v)
    s = string.gsub(s, "[%c|]", " ")
    s = string.gsub(s, "[^ -~]", "?")
    if #s > n then s = string.sub(s, 1, n) end
    return s
end
M.clean = clean

-- one failure: the log line and the file the Mind reads (newest only)
function M.note(source, reason, detail)
    M.seq = M.seq + 1
    local row = { seq = M.seq, t = nowMs(), source = clean(source, 32), reason = clean(reason, 80), detail = clean(detail, 240) }
    M.last = row
    print("[SolFail] source=" .. row.source .. " reason=" .. row.reason .. (row.detail ~= "" and (" detail=" .. row.detail) or ""))
    if type(getFileWriter) == "function" then
        local okw, w = pcall(getFileWriter, M.FILE, true, false)
        if okw and w then
            pcall(function()
                w:write("seq=" .. tostring(row.seq) .. "\nt=" .. tostring(row.t) .. "\nsource=" .. row.source .. "\nreason=" .. row.reason
                    .. "\ndetail=" .. row.detail .. "\n")
            end)
            pcall(function() w:close() end)
        end
    end
    return row
end

-- the route the bridge refused, in numbers: how many points, how many outside the map, the closest two
local function routeShape(route)
    local points = type(route) == "table" and (route.points or route) or nil
    local RF = rawget(_G, "SolRoadFirst")
    if type(points) ~= "table" then return "" end
    if type(RF) == "table" and type(RF.routeDetail) == "function" then
        local ok, d = pcall(RF.routeDetail, points)
        if ok and d then return tostring(d) end
    end
    return "points=" .. tostring(#points)
end
M.routeShape = routeShape

-- bridge_failure: the bridge's own words plus where it happened (start / status / follow) go into the outcome and the log
function M.bridge(site, cause, job, route)
    local detail = tostring(site) .. ": " .. tostring(cause == nil and "no reason given" or cause)
    if route ~= nil then
        local shape = routeShape(route)
        if shape ~= "" then detail = detail .. " (" .. shape .. ")" end
    end
    if type(job) == "table" then job.detail = detail end
    print("[SolDrive] bridge_failure at=" .. tostring(site) .. " cause=" .. clean(detail, 300))
    M.note("drive", "bridge_failure", detail)
    return detail
end

-- every key id in a container and in the bags, key rings and boxes inside it
local function keyIds(container, out, depth)
    if container == nil or depth > DEPTH_MAX or #out >= KEY_LIST_MAX then return end
    local items = call(container, "getItems")
    local n = tonumber((call(items, "size"))) or 0
    for i = 0, math.min(n, ITEMS_MAX) - 1 do
        if #out >= KEY_LIST_MAX then return end
        local it = call(items, "get", i)
        if it ~= nil then
            local k = tonumber((call(it, "getKeyId")))
            if k ~= nil and k ~= -1 then out[#out + 1] = tostring(math.floor(k)) .. ":" .. clean(call(it, "getType") or "?", 24) end
            local inner = call(it, "getInventory")
            if inner ~= nil then keyIds(inner, out, depth + 1) end
        end
    end
end
M.keyIds = keyIds
local function heldIds(who)
    local out = {}
    if who ~= nil then keyIds(call(who, "getInventory"), out, 0) end
    return out
end
local function carIds(car)
    local out = {}
    local n = tonumber((call(car, "getPartCount"))) or 0
    for i = 0, math.min(n, 64) - 1 do
        local box = call(call(car, "getPartByIndex", i), "getItemContainer")
        if box ~= nil then keyIds(box, out, 1) end
    end
    return out
end
local function has(list, id)
    if id == nil then return false end
    local want = tostring(math.floor(id)) .. ":"
    for _, v in ipairs(list) do if string.sub(v, 1, #want) == want then return true end end
    return false
end
local function localPlayer()
    if type(getSpecificPlayer) ~= "function" then return nil end
    local ok, p = pcall(getSpecificPlayer, 0)
    return ok and p or nil
end

-- the key check that failed, in numbers: the car's key id against every key she, he and the car hold
local lastKeyLine = {}
function M.keyLine(where, actor, car)
    if car == nil then return nil end
    local t = nowMs()
    local id = tonumber((call(car, "getKeyId")))
    local tag = tostring(where) .. "|" .. tostring(id)
    if lastKeyLine[tag] and t - lastKeyLine[tag] < 5000 then return nil end   -- an order retried every tick logs once
    lastKeyLine[tag] = t
    local hers, his, inCar = heldIds(actor), heldIds(localPlayer()), carIds(car)
    local match = (has(hers, id) and "hers") or (has(his, id) and "his") or (has(inCar, id) and "in_car") or "none"
    local line = string.format("[SolKeys] %s car=%s car_key=%s ignition=%s hotwired=%s hers=[%s] his=[%s] in_car=[%s] match=%s",
        clean(where, 32), clean(call(call(car, "getScript"), "getName") or call(car, "getScriptName") or "?", 48), tostring(id),
        tostring(call(car, "isKeysInIgnition") == true), tostring(call(car, "isHotwired") == true),
        table.concat(hers, ","), table.concat(his, ","), table.concat(inCar, ","), match)
    print(line)
    return line
end

-- SolOrders' endFail gets only the sentence: the order's own reason is the AR key that holds it; the job says how long and how often
function M.orderEnd(text, job)
    local AR = type(rawget(_G, "SolOrders")) == "table" and SolOrders.AR or nil
    local reason = "unknown"
    if type(AR) == "table" and type(text) == "string" then
        for k, v in pairs(AR) do
            if v == text then reason = k; break end
        end
        if reason == "unknown" and type(AR.busy) == "string" and string.sub(text, 1, #AR.busy) == AR.busy then
            reason = string.match(text, "%((.-)%)%s*$") or "busy"
        end
    end
    local last = M.last
    if (reason == "generic" or reason == "unknown") and type(last) == "table" and string.sub(last.source, 1, 6) == "order_"
        and nowMs() - (tonumber((last.t)) or 0) < 2000 then
        reason = last.reason                                                    -- endFail(failText(why)): failText's code is the true one
    end
    local detail = ""
    if type(job) == "table" then
        local since = tonumber((job.since))
        detail = string.format("kind=%s secs=%s tries=%s no_progress=%s failed_walks=%s preemptions=%s",
            tostring(job.kind or job.mode or "?"), since and tostring(math.floor((nowMs() - since) / 1000)) or "?",
            tostring(job.tries or 0), tostring(job.noProgress or 0), tostring(job.failedWalks or 0), tostring(job.preemptions or 0))
    end
    return M.note("order", reason, detail)
end

-- the car she was to pick: cars there, none she may use -> each of the nearest three, keys against the car (A8)
local function wrapPickCar()
    local U = rawget(_G, "SolUI")
    if type(U) ~= "table" or type(U.solPickCar) ~= "function" or U._s88PickWrapped then return end
    local orig = U.solPickCar
    U.solPickCar = function(vehicles, anchor, radius)
        local best, none = orig(vehicles, anchor, radius)
        if best == nil and none == true then
            pcall(function()
                local ax, ay = tonumber((call(anchor, "getX"))), tonumber((call(anchor, "getY")))
                local s = type(U.solActor) == "function" and U.solActor() or nil
                local near = {}
                for _, v in ipairs(vehicles or {}) do
                    local x, y = tonumber((call(v, "getX"))), tonumber((call(v, "getY")))
                    if x and ax then near[#near + 1] = { v = v, d = (x - ax) ^ 2 + (y - ay) ^ 2 } end
                end
                table.sort(near, function(a, b) return a.d < b.d end)
                for i = 1, math.min(3, #near) do M.keyLine("pick_car", s, near[i].v) end
                M.note("car", "no_usable_car", "cars=" .. tostring(#near))
            end)
        end
        return best, none
    end
    U._s88PickWrapped = true
end
M.wrapPickCar = wrapPickCar
wrapPickCar()
if Events and Events.OnGameStart then Events.OnGameStart.Add(wrapPickCar) end

-- SolAddressVisit.lua - s89: three small things of Sol's address book (PLAN_address_book.md s6/s7, ledger A3 A4 A5).
-- GENERATED ASCII from src/SolAddressVisit_src.lua (apply_s89_address_visit.py --gen): Arabic is stored as \\uXXXX escapes.
--
-- book_visited (A3)  A stash row of her book is marked "انزار" by itself when she gets there: she stays within ARRIVE_TILES of the
--                    stash's spot (any floor: a stash box may be upstairs) for DWELL_MS, alive. Once per row: after the "رجّعيه"
--                    button (or "رجّعي") the row is never marked again by itself. She says it once. No world scan: one distance per
--                    stash row every TICK_MS. (The game gives no Lua way to the spawned box: StashSystem exposes only the stash's
--                    building point, so "she sees the box empty" is not read; arriving is the mark, as PLAN s3 "لما توصل".)
-- book_hint (A4)     "شو هالورقة؟ فرجيني ياها" (PLAN s6, the optional line). He opens a paper or map WITH a place while she is
--                    far (or on another floor, or asleep): nothing is learned (the rule stays), the paper is remembered (memory
--                    only, this life). When she is next beside him (12 tiles, his floor, awake, or the same car) she asks once to
--                    see it; he opens it again beside her and the book's own rule learns it. Rate-limited (HINT_GAP_MS), each
--                    paper asked about once, forgotten after PENDING_MS, never for a paper already in her book.
-- address_target (A5, the s82 switch) An area row (a revealed map's rectangle) drives to the nearest entrance of the area on the
--                    road: the point where a paved road crosses the area's edge nearest to him; already inside the area (or no
--                    road crosses its edge): the paved road nearest the area's centre inside it. s82 alone sent an area through
--                    its house footprint (a scan of the whole rectangle for its biggest building, then the road by that
--                    building): a stall on a town map and an arbitrary end. Houses, stashes, places: unchanged (s82 / s84).
-- Runtime wraps only (no anchor in any file): SolAddressBook.sees, ISReadABook.displayPrintMedia / ISMap.initMapData (outside the
-- book's own hooks), SolAddressTarget.target. Each wrap is put on once (a flag), so the s82/s84 re-wraps at game start stack around
-- it harmlessly.
SolUI = SolUI or {}
local U = SolUI
SolAddressVisit = SolAddressVisit or {}
local M = SolAddressVisit
M.VERSION = "0.1.0"
M.ARRIVE_TILES = 10
M.DWELL_MS = 6000
M.TICK_MS = 1000
M.HINT_GAP_MS = 5 * 60 * 1000
M.PENDING_MS = 30 * 60 * 1000
M.PENDING_MAX = 8
M.HINT_AFTER_MS = 3000          -- not while he is still reading it
M.EDGE_IN = 2                   -- tiles inside the area's edge for the entrance point
local CELL = 64                 -- SolStaticRoads.lua CELL

local W = {
    visited = "وصلنا عـ%s. علّمتو بالدفتر إنو انزار.",
    hintOne = "شو هالورقة؟ فرجيني ياها وأنا حدك، وبحفظلك المكان.",
    hintMany = "شو هالأوراق اللي فتحتها؟ فرجيني ياهن وأنا حدك، وبحفظلك الأماكن.",
}
M.W = W

local function log(m) print("[SolAddressVisit] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or os.time() * 1000 end
local function g(name) return rawget(_G, name) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
local function sw(name) local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on(name) == true end
local function fmt(s, a) return (string.gsub(s, "%%s", function() return tostring(a) end)) end
local function B() local b = g("SolAddressBook"); if type(b) == "table" then return b end return nil end
local function actor() return type(U.solActor) == "function" and U.solActor() or nil end
local function player() return getSpecificPlayer and getSpecificPlayer(0) or nil end
local function sync() if type(ModData) == "table" and type(ModData.transmit) == "function" then pcall(ModData.transmit, "Sol_AddressBook") end end
local function say(a, line, kind)
    log("say " .. tostring(kind))
    local sc = g("SurvivorCompanion")
    local gu = type(sc) == "table" and sc.GameplayUtil or nil
    if a ~= nil and type(gu) == "table" and type(gu.say) == "function" then pcall(gu.say, a, line) end
end

M.state = M.state or { at = {}, pending = {}, life = nil, lastHint = nil, ctx = nil, nextTick = 0 }
local S = M.state

-- ---------------------------------------------------------------- A3 book_visited
function M.checkVisits(t)
    local book = B()
    if book == nil or not sw("book_visited") or not sw("address_book") then S.at = {}; return 0 end
    local a = actor()
    if a == nil or call(a, "isDead") == true then S.at = {}; return 0 end
    local x, y = tonumber((call(a, "getX"))), tonumber((call(a, "getY")))
    if not x then return 0 end
    local marked, live = 0, {}
    local r2 = M.ARRIVE_TILES * M.ARRIVE_TILES
    for _, e in ipairs(book.entries()) do
        if e.kind == "stash" and e.looted ~= true and e.autoVisit ~= true and tonumber(e.x) then
            local dx, dy = e.x - x, e.y - y
            if dx * dx + dy * dy <= r2 then
                live[e.key] = true
                local since = S.at[e.key]
                if since == nil then S.at[e.key] = t
                elseif t - since >= M.DWELL_MS then
                    e.looted, e.autoVisit, e.visitedAt = true, true, t
                    sync()
                    S.at[e.key] = nil
                    marked = marked + 1
                    log("visited " .. tostring(e.key))
                    local name = type(book.shortName) == "function" and book.shortName(e) or tostring(e.name)
                    say(a, fmt(W.visited, name), "visited")
                end
            end
        end
    end
    for k in pairs(S.at) do if not live[k] then S.at[k] = nil end end
    return marked
end

-- ---------------------------------------------------------------- A4 book_hint
local function lifeKey() local book = B(); if book and type(book.lifeKey) == "function" then local ok, k = pcall(book.lifeKey); if ok then return k end end return nil end
local function known(src)
    local book = B()
    if book == nil or src == nil then return false end
    local s = string.lower(tostring(src))
    for _, e in ipairs(book.entries()) do
        for _, x in ipairs(type(e.src) == "table" and e.src or {}) do if string.lower(tostring(x)) == s then return true end end
    end
    return false
end
M.known = known
local FAR = { far = true, other_floor = true, asleep = true }
-- the book's sees() during a read: remember "she did not see it" for this read
function M.wrapSees()
    local book = B()
    if book == nil or type(book.sees) ~= "function" or book._s89Sees then return false end
    book._s89Sees = true
    local orig = book.sees
    book.sees = function(...)
        local seen, why = orig(...)
        if S.ctx ~= nil and not seen and FAR[why] then S.ctx.far = why end
        return seen, why
    end
    return true
end
function M.remember(src, label, why)
    if not sw("book_hint") or not sw("address_book") or src == nil then return false end
    local life = lifeKey()
    if life == nil then return false end
    if S.life ~= life then S.pending, S.life = {}, life end
    if known(src) then return false end
    local key = string.lower(tostring(src))
    for _, p in ipairs(S.pending) do if p.key == key then p.at = nowMs(); return false end end
    table.insert(S.pending, { key = key, label = label, at = nowMs(), why = why })
    while #S.pending > M.PENDING_MAX do table.remove(S.pending, 1) end
    log("he read " .. key .. " while she was " .. tostring(why) .. "; she will ask to see it")
    return true
end
local function around(base, getSrc)
    return function(self, ...)
        local outer = S.ctx
        S.ctx = {}
        local ok, r = pcall(base, self, ...)
        local ctx = S.ctx
        S.ctx = outer
        if ctx.far then
            local okS, src, label = pcall(getSrc, self)
            if okS then pcall(M.remember, src, label, ctx.far) end
        end
        if not ok then error(r) end
        return r
    end
end
local function txt(key)
    if type(key) ~= "string" then return nil end
    if type(getTextOrNull) == "function" then local ok, s = pcall(getTextOrNull, key); if ok and type(s) == "string" then return s end end
    return nil
end
local function printSrc(self)
    local md = call(self.item, "getModData")
    local pm = type(md) == "table" and md.printMedia or nil
    if type(pm) ~= "table" or type(pm.id) ~= "string" then return nil end
    return pm.id, txt(pm.title) or pm.id
end
local function mapSrc(self)
    local item = type(self) == "table" and self.mapObj or nil
    if item == nil then return nil end
    local label = tostring(call(item, "getDisplayName") or call(item, "getName") or "Map")
    local stash = call(item, "getStashMap")
    if type(stash) == "string" and stash ~= "" then return stash, label end
    return tostring(call(item, "getMapID") or label), label
end
function M.wrapReads()
    local n = 0
    local RB = g("ISReadABook")
    if type(RB) == "table" and type(RB.displayPrintMedia) == "function" and not RB._s89Hint then
        RB._s89Hint = true
        RB.displayPrintMedia = around(RB.displayPrintMedia, printSrc)
        n = n + 1
    end
    local MP = g("ISMap")
    if type(MP) == "table" and type(MP.initMapData) == "function" and not MP._s89Hint then
        MP._s89Hint = true
        MP.initMapData = around(MP.initMapData, mapSrc)
        n = n + 1
    end
    return n
end
function M.checkHint(t)
    if #S.pending == 0 then return false end
    if not sw("book_hint") or not sw("address_book") then return false end
    local book = B()
    if book == nil then return false end
    if lifeKey() ~= S.life then S.pending = {}; return false end
    local keep = {}
    for _, p in ipairs(S.pending) do
        if t - p.at <= M.PENDING_MS and not known(p.key) then keep[#keep + 1] = p end
    end
    S.pending = keep
    if #keep == 0 then return false end
    if S.lastHint and t - S.lastHint < M.HINT_GAP_MS then return false end
    local ready = 0
    for _, p in ipairs(keep) do if t - p.at >= M.HINT_AFTER_MS then ready = ready + 1 end end
    if ready == 0 then return false end
    local ok, seen = pcall(book.sees, player())
    if not ok or not seen then return false end
    S.lastHint = t
    local rest = {}
    for _, p in ipairs(keep) do if t - p.at < M.HINT_AFTER_MS then rest[#rest + 1] = p end end
    S.pending = rest
    say(actor(), ready > 1 and W.hintMany or W.hintOne, "hint")
    return true
end

-- ---------------------------------------------------------------- A5 an area: the nearest entrance on the road
local function inBox(x, y, b, pad) return x >= b.x1 - pad and x <= b.x2 + pad and y >= b.y1 - pad and y <= b.y2 + pad end
-- the crossings of road edge a-b with the box's four sides
local function crossings(ax, ay, bx, by, b, out)
    for _, side in ipairs({ { "y", b.y1 }, { "y", b.y2 }, { "x", b.x1 }, { "x", b.x2 } }) do
        local v = side[2]
        if side[1] == "y" then
            if ay ~= by and (ay - v) * (by - v) <= 0 then
                local x = ax + (v - ay) / (by - ay) * (bx - ax)
                if x >= b.x1 and x <= b.x2 then out[#out + 1] = { x = x, y = v, side = side, ax = ax, ay = ay, bx = bx, by = by } end
            end
        elseif ax ~= bx and (ax - v) * (bx - v) <= 0 then
            local y = ay + (v - ax) / (bx - ax) * (by - ay)
            if y >= b.y1 and y <= b.y2 then out[#out + 1] = { x = v, y = y, side = side, ax = ax, ay = ay, bx = bx, by = by } end
        end
    end
end
-- a few tiles along the road, toward the end that is inside the box
local function stepIn(c, b)
    local ix, iy
    if inBox(c.ax, c.ay, b, 0) and not (c.ax == c.x and c.ay == c.y) then ix, iy = c.ax, c.ay else ix, iy = c.bx, c.by end
    local dx, dy = ix - c.x, iy - c.y
    local l = math.sqrt(dx * dx + dy * dy)
    if l < 0.001 then return c.x, c.y end
    local s = math.min(M.EDGE_IN, l)
    return c.x + dx / l * s, c.y + dy / l * s
end
function M.areaTarget(T, e, px, py)
    local b = { x1 = tonumber(e.x1), y1 = tonumber(e.y1), x2 = tonumber(e.x2), y2 = tonumber(e.y2) }
    if not (b.x1 and b.y1 and b.x2 and b.y2) or b.x2 <= b.x1 or b.y2 <= b.y1 then return nil, "no_box" end
    local SR = g("SolStaticRoads")
    local gr = type(SR) == "table" and type(SR.load) == "function" and SR.load() or nil
    if type(gr) ~= "table" or type(gr.GRID) ~= "table" then return nil, "no_road_graph" end
    if px and not inBox(px, py, b, 0) then
        local seen, best, bd = {}, nil, nil
        local cx1, cx2, cy1, cy2 = math.floor(b.x1 / CELL), math.floor(b.x2 / CELL), math.floor(b.y1 / CELL), math.floor(b.y2 / CELL)
        local cells = {}
        for gx = cx1, cx2 do cells[#cells + 1] = { gx, cy1 }; cells[#cells + 1] = { gx, cy2 } end
        for gy = cy1, cy2 do cells[#cells + 1] = { cx1, gy }; cells[#cells + 1] = { cx2, gy } end
        for _, c in ipairs(cells) do
            local list = gr.GRID[c[1] * 4096 + c[2]]
            if list then
                for i = 1, #list do
                    local ed = list[i]
                    if not seen[ed] and not gr.ED[ed] then
                        seen[ed] = true
                        local ia, ib = gr.EA[ed], gr.EB[ed]
                        local out = {}
                        crossings(gr.NX[ia], gr.NY[ia], gr.NX[ib], gr.NY[ib], b, out)
                        for _, p in ipairs(out) do
                            local d = (p.x - px) ^ 2 + (p.y - py) ^ 2
                            if bd == nil or d < bd then best, bd = p, d; best.street = gr.names[gr.EN[ed]] end
                        end
                    end
                end
            end
        end
        if best then
            local x, y = stepIn(best, b)
            return { x = math.floor(x + 0.5), y = math.floor(y + 0.5), street = best.street, how = "area_entrance", house = b }
        end
    end
    if type(T.roadFor) == "function" then
        local ok, p = pcall(T.roadFor, b, nil)
        if ok and type(p) == "table" and inBox(p.x, p.y, b, 0) then
            return { x = math.floor(p.x + 0.5), y = math.floor(p.y + 0.5), street = p.street, how = "area_centre_road", house = b }
        end
    end
    return nil, "no_road"
end
function M.wrapTarget()
    local T = g("SolAddressTarget")
    if type(T) ~= "table" or type(T.target) ~= "function" or T._s89Area then return false end
    T._s89Area = true
    local orig = T.target
    T.target = function(e, ...)
        if type(e) == "table" and e.kind == "area" and type(T.on) == "function" and T.on() then
            local p = player()
            local v = call(p, "getVehicle")
            local px, py = tonumber((call(v or p, "getX"))), tonumber((call(v or p, "getY")))
            local ok, t, why = pcall(M.areaTarget, T, e, px, py)
            if ok and t then
                log(tostring(e.key) .. " " .. tostring(e.name) .. ": " .. t.how .. " " .. tostring(t.street) .. " at " .. tostring(t.x) .. "," .. tostring(t.y))
                return t
            end
            log("area " .. tostring(e.key) .. ": " .. tostring(ok and why or t) .. ", the old way")
        end
        return orig(e, ...)
    end
    return true
end

-- ---------------------------------------------------------------- wiring
function M.tick()
    local t = nowMs()
    if t < (S.nextTick or 0) then return end
    S.nextTick = t + M.TICK_MS
    pcall(M.checkVisits, t)
    pcall(M.checkHint, t)
end
function M.wrap()
    pcall(M.wrapSees)
    pcall(M.wrapTarget)
    return true
end
function M.start()
    M.wrap()
    local n = M.wrapReads()
    log("ready v" .. M.VERSION .. " reads=" .. tostring(n))
end
pcall(M.wrap)
if Events then
    if Events.OnGameStart then Events.OnGameStart.Add(function() pcall(M.start) end) end
    if Events.OnTick then Events.OnTick.Add(function() pcall(M.tick) end) end
end
return M

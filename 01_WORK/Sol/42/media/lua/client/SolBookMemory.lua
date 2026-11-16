-- SolBookMemory.lua - switch book_memory (s86). Her address book, compact, for Sol Mind's memory (the memory section of the model card).
-- ASCII only. The book itself stays where it is: ModData "Sol_AddressBook" of this life (SolAddressBook.lua, s84 SolAddressPlaces.lua);
-- this module only reads it. SolWorldScan.writeWorldRaw puts SolBookMemory.snapshot() into SolWorld_Snapshot.txt as "solBook":
--   { n = <rows in the book>, from = "sol" | "player", rows = { { g, n, c, st, ls, lt, d, dir }, ... } }   (at most MAX_ROWS)
--   g    group: home | house | tourist | shop | public | stash | area   (s84's page sections; "place" rows by their cat)
--   n    the name as the game wrote it (a house: its street and town; a stash: the street near it, else the map's name); none for home
--   c    the town (not for home); st  home's street; ls  a rental; lt  looted
--   d    whole tiles from her (from him when she is away or gone); dir  1..8 = N, NE, E, SE, S, SW, W, NW (north is -y)
-- No coordinates leave the game: the Mind words the distance and the direction, the book's own action (sol_address) drives there.
-- Order: our home first, then the page's sections (houses, attractions, shops, public places, stashes, areas), looted last in
-- their section, newest first. Our home is the book's home row (s84) or, when the book has none, SolHome's.
SolBookMemory = SolBookMemory or {}
local M = SolBookMemory
M.VERSION = "0.1.0"
M.MAX_ROWS = 40
M.ORDER = { home = 1, house = 2, tourist = 3, shop = 4, public = 5, stash = 6, area = 7 }

local function g(name) return rawget(_G, name) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end                               -- one value only (Kahlua: a second value given to tonumber is its base)
    return nil
end
local function on() local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on("book_memory") == true end
M.on = on
local function str(s) if type(s) == "string" and s ~= "" then return s end return nil end
local function groupOf(e) if e.kind == "place" then return e.cat or "tourist" end return e.kind end

-- 8 directions without atan, as SolAddressBook.distanceText: north is -y, tan(22.5) = 0.4142
function M.dir8(dx, dy)
    local ax, ay = math.abs(dx), math.abs(dy)
    if ax <= ay * 0.4142 then return dy < 0 and 1 or 5 end
    if ay <= ax * 0.4142 then return dx > 0 and 3 or 7 end
    if dx > 0 then return dy < 0 and 2 or 4 end
    return dy < 0 and 8 or 6
end

-- where the distance is counted from: her, while she is here; him when she is away (SolFar) or gone
function M.origin()
    local U = g("SolUI")
    local a = type(U) == "table" and type(U.solActor) == "function" and U.solActor() or nil
    local away = type(U) == "table" and type(U.solFarState) == "function" and U.solFarState() ~= nil
    if a ~= nil and not away then
        local x, y = tonumber((call(a, "getX"))), tonumber((call(a, "getY")))
        if x and y then return x, y, "sol" end
    end
    local p = getSpecificPlayer and getSpecificPlayer(0) or nil
    local x, y = tonumber((call(p, "getX"))), tonumber((call(p, "getY")))
    if x and y then return x, y, "player" end
    return nil
end

function M.row(e, ox, oy)
    local k = groupOf(e)
    if M.ORDER[k] == nil then return nil end
    local r = { g = k }
    if k == "home" then r.st = str(e.street)
    elseif k == "stash" then r.n = str(e.sub) or str(e.name)
    else r.n = str(e.name) end
    if k ~= "home" then r.c = str(e.city) end
    if k == "house" and e.lease then r.ls = true end
    if e.looted == true then r.lt = true end
    local ex, ey = tonumber(e.x), tonumber(e.y)
    if ox and ex and ey then
        local dx, dy = ex - ox, ey - oy
        r.d = math.floor(math.sqrt(dx * dx + dy * dy) + 0.5)
        if r.d >= 3 then r.dir = M.dir8(dx, dy) end
    end
    return r
end

function M.snapshot()
    if not on() then return nil end
    local B = g("SolAddressBook")
    if type(B) ~= "table" or type(B.entries) ~= "function" then return nil end
    local okE, list = pcall(B.entries)
    if not okE or type(list) ~= "table" then return nil end
    local ox, oy, from = M.origin()
    local rows, hasHome = {}, false
    for _, e in ipairs(list) do
        if type(e) == "table" then
            local r = M.row(e, ox, oy)
            if r ~= nil then
                if r.g == "home" then
                    if not hasHome then hasHome = true; rows[#rows + 1] = { r = r, seq = tonumber(e.seq) or 0 } end
                else rows[#rows + 1] = { r = r, seq = tonumber(e.seq) or 0 } end
            end
        end
    end
    if not hasHome then
        local H = g("SolHome")
        local okH, h = false, nil
        if type(H) == "table" and type(H.get) == "function" then okH, h = pcall(H.get) end
        if okH and type(h) == "table" and tonumber(h.x) and tonumber(h.y) then
            rows[#rows + 1] = { r = M.row({ kind = "home", x = h.x, y = h.y }, ox, oy), seq = 0 }
        end
    end
    table.sort(rows, function(p, q)
        local a, b = M.ORDER[p.r.g], M.ORDER[q.r.g]
        if a ~= b then return a < b end
        if (p.r.lt == true) ~= (q.r.lt == true) then return q.r.lt == true end
        return p.seq > q.seq
    end)
    local out = {}
    for i = 1, math.min(#rows, M.MAX_ROWS) do out[i] = rows[i].r end
    return { n = #rows, from = from, rows = out }
end

return M

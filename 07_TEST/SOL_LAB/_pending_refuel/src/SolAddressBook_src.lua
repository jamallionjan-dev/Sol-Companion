-- SolAddressBook.lua - switch address_book. "دفتر العناوين": what Sol saw you read, kept in her own book, for this life of hers.
-- GENERATED ASCII from src/SolAddressBook_src.lua (src/gen.py): Arabic is stored as \\uXXXX escapes (SolText decodes them).
-- What is captured (game 42.22.2, all read-only hooks, one call per event, no world scan):
--   house  "House for Sale" / "Premises for Lease" flyers of Homeward Real Estate. The game opens the flyer window in
--          ISReadABook:perform -> self:displayPrintMedia() (shared/TimedActions/ISReadABook.lua 206-212, 252-298) every time it is
--          read, whatever the read flag. The item's modData.printMedia = { id, title, info, text } (RecipeCodeHelper.setPrintMediaInfo);
--          id is the registry path, lower case ("houseforsale903"); the house's rectangle is PrintMediaDefinitions.MiscDetails[id]
--          (shared/PrintMedia/PrintMediaDefinitions.lua 50-138), the address is the last line of getText(text) ("625 Dewey Street, Muldraugh, KY.").
--   stash  a stash map: ISReadMapItem:showUI makes an ISMap; ISMap:update calls self:initMapData() once per opened map
--          (client/ISUI/Maps/ISMap.lua 375-404), every time it is opened. mapObj:getStashMap() names the stash; its building is
--          StashDescriptions[*].buildingX/Y (shared/StashDescriptions/*.lua), or StashSystem.getStash(name):getBuildingX/Y().
--   area   any other map item: the same initMapData; after LootMaps.Init the map API holds the bounds the game reveals
--          (MapUtils.revealKnownArea, client/ISUI/Maps/ISMapDefinitions.lua 377-384). Kept as a rectangle with its center.
-- She learns it only when she sees it: alive, awake, on his floor and within SEE_TILES, or in the same car as him.
-- Her book is ModData "Sol_AddressBook", for the life "<her id>#<deaths>" of ModData "Sol_Life" (SolLife.lua). A respawn empties it
-- (SolLife.checkIdentity calls solAddressBookForget, with the streets and the stations); a reload keeps it.
-- The book is a tab of her More window (SolPages), right under Family. A click: in the same car, the GPS destination and the drive
-- (the GPS panel's own U.gpsSetDestination + U.gpsStart); otherwise the destination only, and she asks.
-- Verb: sol_address list | go:<kind>:<words> | looted:<kind>:<words>   (kind: house, stash, area, any)
SolUI = SolUI or {}
local U = SolUI
SolAddressBook = SolAddressBook or {}
local M = SolAddressBook
M.VERSION = "0.1.0"
M.SEE_TILES = 12             -- SolFar.lua MIN_TILES: from 12 tiles on, she counts as out of his sight
M.MAX_ENTRIES = 300
M.MAX_AREA_TILES = 2500      -- a "map" wider than this is the whole world, not a place
M.STORE, M.LIFE = "Sol_AddressBook", "Sol_Life"
M.REFRESH_MS = 2000
-- the More window's content box (SolPages.lua: CX, CW, CY, H - CY - 44)
local CX, CW, CY, CH = 14, 418, 66, 640 - 66 - 44
local ROW_H, SEC_H = 52, 34
local SCALE_TXT, SCALE_SUB, SCALE_SEC = 0.57, 0.46, 0.67

local W = {
    tab = "دفتر العناوين",
    secHouse = "بيوت للبيع", secStash = "غنائم ومخابئ", secArea = "أماكن مكشوفة",
    hint = "كبسة عالسطر: إذا نحنا بالسيارة بسوق لعندو، وإلا بحطلك علامة.",
    empty = "دفتري فاضي. افتح إعلان بيت أو خريطة قدّامي وأنا بحفظها.",
    house = "بيت للبيع", lease = "للإيجار", stash = "مخبأ", area = "منطقة",
    looted = "انزار", lootBtn = "انزار", unlootBtn = "رجّعيه",
    meters = "%s م", km = "%s كم", sep = "، ",
    dirs = { "شمال", "شمال شرق", "شرق", "جنوب شرق", "جنوب", "جنوب غرب", "غرب", "شمال غرب" },
    -- what she says
    houseNew = "حفظت بيت %s بالدفتر.",
    houseKnown = "بيت %s عندي بالدفتر من قبل.",
    houseMore = "هاد نفس بيت %s، زدت هالإعلان عالسطر نفسو.",
    stashNew = "خريطة مخبأ! حفظت المكان، قريب من %s.",
    stashNewNoSt = "خريطة مخبأ! حفظت المكان بالدفتر.",
    stashKnown = "هاد المخبأ عندي بالدفتر من قبل.",
    stashVisited = "هاد المخبأ زرناه قبل.",
    areaNew = "حفظت منطقة %s بالدفتر.",
    areaKnown = "هالمنطقة عندي بالدفتر من قبل.",
    full = "دفتري تعبّى، ما عاد في محل.",
    going = "يلا، ماشيين عـ%s.",
    askCar = "حطيتلك العلامة عـ%s. بدك نروح بالسيارة؟",
    driveFail = "حطيت العلامة عـ%s، بس ما قدرت إطلع عالسواقة هلأ.",
    noGps = "ما فيني حط علامة هلأ.",
    notSeen = "ما شفت هالعنوان معك.",
    which = "عندي أكتر من عنوان: %s. أيا واحد؟",
    lootedSet = "تمام، علّمت %s إنو انزار.",
    lootedUnset = "رجّعت %s عالقائمة متل ما كان.",
    listHead = "بالدفتر عندي: %s.",
    listMore = " وغيرهن كمان %s.",
    listEmpty = "دفتري فاضي، ما شفت معك ولا إعلان ولا خريطة لهلّق.",
    off = "دفتر العناوين مسكّر هلأ.",
}
local EN = { tab = "Address Book", secHouse = "Houses for sale", secStash = "Stashes", secArea = "Revealed areas",
    hint = "Click a row: in the car she drives there, otherwise she sets the marker.", empty = "The book is empty. Read a listing or a map in front of her.",
    house = "House for sale", lease = "For lease", stash = "Stash", area = "Area", looted = "looted", lootBtn = "Looted", unlootBtn = "Restore",
    meters = "%s m", km = "%s km", dirs = { "N", "NE", "E", "SE", "S", "SW", "W", "NW" } }
M.W = W

local function log(m) print("[SolAddressBook] " .. tostring(m)) end
local function nowMs() return getTimestampMs and getTimestampMs() or 0 end
local function g(name) return rawget(_G, name) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a, b = pcall(f, o, ...)
    if ok then return a end                               -- one value only: a second return value passed to tonumber becomes its base a second one as its base (Kahlua: Double cast to String)
    return nil
end
local function int(n) return tostring(math.floor((tonumber(n) or 0) + 0.5)) end
local function on() local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on("address_book") == true end
local function actor() return type(U.solActor) == "function" and U.solActor() or nil end
local function player() return getSpecificPlayer and getSpecificPlayer(0) or nil end
local function isAr() return not (type(U.lang) == "function" and U.lang() == "en") end
local function word(k) if not isAr() and EN[k] ~= nil then return EN[k] end return W[k] end
local function store(key)
    if type(ModData) ~= "table" or type(ModData.getOrCreate) ~= "function" then return nil end
    local ok, d = pcall(ModData.getOrCreate, key)
    if ok and type(d) == "table" then return d end
    return nil
end
local function sync(key) if type(ModData) == "table" and type(ModData.transmit) == "function" then pcall(ModData.transmit, key) end end
local function fmt(s, a) return (string.gsub(s, "%%s", function() return tostring(a) end)) end

M.state = M.state or { said = {} }
local S = M.state
local function say(a, text, kind)
    S.said[#S.said + 1] = { kind = kind, text = text }
    while #S.said > 24 do table.remove(S.said, 1) end
    log("say " .. tostring(kind))
    local sc = g("SurvivorCompanion")
    local gu = type(sc) == "table" and sc.GameplayUtil or nil
    if a ~= nil and type(gu) == "table" and type(gu.say) == "function" then pcall(gu.say, a, text) end
end

-- ---------------------------------------------------------------- her life
local function idOf(a)
    local sc = g("SurvivorCompanion")
    if type(sc) ~= "table" or type(sc.GameplayUtil) ~= "table" or type(sc.GameplayUtil.idOf) ~= "function" then return nil end
    local ok, id = pcall(sc.GameplayUtil.idOf, a)
    if ok and type(id) == "string" and id ~= "" then return id end
    return nil
end
-- "<id>#<deaths>" of the Sol who is here now. A new id first goes through SolLife (counts the death, empties what she knew).
function M.lifeKey()
    local life = store(M.LIFE)
    if life == nil then return nil end
    local a = actor()
    if a ~= nil then
        local id = idOf(a)
        if id ~= nil and life.id ~= id then
            local L = g("SolLife")
            if type(L) == "table" and type(L.checkIdentity) == "function" then pcall(L.checkIdentity) end
            life = store(M.LIFE)
            if life == nil or life.id ~= id then return nil end
        end
    end
    if type(life.id) ~= "string" then return nil end
    return life.id .. "#" .. tostring(tonumber(life.deaths) or 0)
end
-- the book of this life; create = start it when it belongs to an earlier life (or none)
local function book(create)
    local b = store(M.STORE)
    if b == nil then return nil end
    local key = M.lifeKey()
    if key == nil then return nil end
    if b.life ~= key then
        if not create then return nil end
        b.life, b.entries, b.n, b.seq = key, {}, 0, 0
        sync(M.STORE)
    end
    if type(b.entries) ~= "table" then b.entries, b.n = {}, 0 end
    return b
end
M.book = book
function M.forget()
    local b = store(M.STORE)
    if b == nil then return false end
    b.entries, b.n, b.seq, b.life = {}, 0, 0, nil
    sync(M.STORE)
    log("her book went with her")
    return true
end
solAddressBookForget = M.forget          -- SolLife.checkIdentity calls it on a respawn, beside the streets and the stations

-- ---------------------------------------------------------------- does she see it
function M.sees(reader)
    local a = actor()
    if a == nil then return false, "no_sol" end
    if call(a, "isDead") == true then return false, "dead" end
    if call(a, "isAsleep") == true then return false, "asleep" end
    local p = reader or player()
    if p == nil then return false, "no_player" end
    local pv, sv = call(p, "getVehicle"), call(a, "getVehicle")
    if pv ~= nil and sv ~= nil and pv == sv then return true, "same_car" end
    local ax, ay, az = tonumber((call(a, "getX"))), tonumber((call(a, "getY"))), tonumber((call(a, "getZ"))) or 0
    local px, py, pz = tonumber((call(p, "getX"))), tonumber((call(p, "getY"))), tonumber((call(p, "getZ"))) or 0
    if not ax or not px then return false, "no_position" end
    if math.abs(az - pz) >= 1 then return false, "other_floor" end
    local dx, dy = ax - px, ay - py
    if dx * dx + dy * dy <= M.SEE_TILES * M.SEE_TILES then return true, "near" end
    return false, "far"
end

-- ---------------------------------------------------------------- the book
function M.keyOf(kind, x, y) return kind .. ":" .. int(x) .. "," .. int(y) end
-- e = { kind, x, y, name, sub, city, num, src, x1, y1, x2, y2, lease }. Returns ok, "new" | "known" | "more", entry
function M.record(e)
    local b = book(true)
    if b == nil then return false, "no_book" end
    local key = M.keyOf(e.kind, e.x, e.y)
    local old = b.entries[key]
    if old ~= nil then
        old.src = type(old.src) == "table" and old.src or {}
        for _, s in ipairs(old.src) do if s == e.src then return true, "known", old end end
        old.src[#old.src + 1] = e.src
        sync(M.STORE)
        return true, "more", old
    end
    if (b.n or 0) >= M.MAX_ENTRIES then return false, "full" end
    b.seq = (b.seq or 0) + 1
    local n = { key = key, kind = e.kind, x = math.floor(e.x + 0.5), y = math.floor(e.y + 0.5), name = e.name, sub = e.sub, city = e.city, num = e.num,
        src = { e.src }, seq = b.seq, looted = false, lease = e.lease, x1 = e.x1, y1 = e.y1, x2 = e.x2, y2 = e.y2 }
    b.entries[key] = n
    b.n = (b.n or 0) + 1
    sync(M.STORE)
    log("learned " .. key .. " " .. tostring(e.name))
    return true, "new", n
end
function M.entries()
    local b = book(false)
    local out = {}
    if b == nil then return out end
    for _, e in pairs(b.entries) do out[#out + 1] = e end
    table.sort(out, function(p, q) return (p.seq or 0) > (q.seq or 0) end)
    return out
end
function M.count() return #M.entries() end

-- ---------------------------------------------------------------- what the game gives at the event
local HOUSE_IDS = { "^houseforsale(%d+)$", "^premisesforlease(%d+)$", "^premiseswithapartmentsforleaselistingno(%d+)$" }
local function txt(key)
    if type(key) ~= "string" then return nil end
    if type(getTextOrNull) == "function" then local ok, s = pcall(getTextOrNull, key); if ok and type(s) == "string" then return s end end
    if type(getText) == "function" then local ok, s = pcall(getText, key); if ok and type(s) == "string" and s ~= key then return s end end
    return nil
end
-- "625 Dewey Street, Muldraugh, KY." -> "625 Dewey Street", "Muldraugh"
function M.parseAddress(text)
    if type(text) ~= "string" then return nil end
    local t = string.gsub(text, "\\n", "\n")
    local last
    for line in string.gmatch(t .. "\n", "([^\n]*)\n") do
        local s = string.match(line, "^%s*(.-)%s*$")
        if s ~= "" and string.find(s, ", KY", 1, true) then last = s end
    end
    if last == nil then return nil end
    local street, city = string.match(last, "^(.-),%s*(.-),%s*KY")
    if street == nil then return nil end
    return street, city
end
local function rectOf(det)
    local list = type(det) == "table" and det.location1 or nil
    local r = type(list) == "table" and list[1] or nil
    if type(r) ~= "table" or not r.x1 then return nil end
    return r
end
-- a flyer the player opened (ISReadABook:displayPrintMedia)
function M.onPrintMedia(character, item)
    if not on() then return false, "switch_off" end
    local md = call(item, "getModData")
    local pm = type(md) == "table" and md.printMedia or nil
    if type(pm) ~= "table" or type(pm.id) ~= "string" then return false, "not_print_media" end
    local id = string.lower(pm.id)
    local num
    for _, rx in ipairs(HOUSE_IDS) do num = num or string.match(id, rx) end
    if num == nil then return false, "not_a_listing" end
    local defs = g("PrintMediaDefinitions")
    local r = rectOf(type(defs) == "table" and type(defs.MiscDetails) == "table" and (defs.MiscDetails[id] or defs.MiscDetails[pm.id]) or nil)
    if r == nil then return false, "no_location" end
    local seen, why = M.sees(character)
    if not seen then log("flyer " .. id .. " read, she did not see it: " .. tostring(why)); return false, why end
    local street, city = M.parseAddress(txt(pm.text))                               -- "Print_Text_<Id>_info": the flyer's text, address last
    if street == nil then street, city = M.parseAddress(txt(pm.info)) end
    local title = txt(pm.title) or id
    local name = street and (street .. (city and (", " .. city) or "")) or title
    local ok, how, e = M.record({ kind = "house", x = (r.x1 + r.x2) / 2, y = (r.y1 + r.y2) / 2, name = name, sub = title, city = city, num = num,
        src = id, lease = string.find(id, "lease", 1, true) ~= nil, x1 = r.x1, y1 = r.y1, x2 = r.x2, y2 = r.y2 })
    local a = actor()
    if not ok then if how == "full" then say(a, W.full, "full") end; return false, how end
    say(a, fmt(how == "new" and W.houseNew or (how == "more" and W.houseMore or W.houseKnown), e.name), "house_" .. how)
    return true, how
end

local function stashSpot(name)
    local list = g("StashDescriptions")
    if type(list) == "table" then
        for _, d in ipairs(list) do
            if type(d) == "table" and d.name == name and tonumber(d.buildingX) then
                local c = type(d.containers) == "table" and d.containers[1] or nil
                if type(c) == "table" and tonumber(c.contX) and tonumber(c.contY) then return tonumber(c.contX), tonumber(c.contY), d end
                return tonumber(d.buildingX), tonumber(d.buildingY), d
            end
        end
    end
    local SS = g("StashSystem")
    local okS, st = false, nil
    if SS ~= nil then okS, st = pcall(function() return SS.getStash(name) end) end
    if not okS then st = nil end
    local x, y = tonumber((call(st, "getBuildingX"))), tonumber((call(st, "getBuildingY")))
    if x and y then return x, y, nil end
    return nil
end
local function streetNear(x, y)
    if type(U.gpsNearestRoad) ~= "function" then return nil end
    local ok, _, _, dist, name = pcall(U.gpsNearestRoad, x, y)
    if ok and type(name) == "string" and name ~= "" and (tonumber(dist) or 999) <= 60 then return name end
    return nil
end
local function mapBounds(mapUI)
    local jo = type(mapUI) == "table" and mapUI.javaObject or nil                    -- as MapUtils.revealKnownArea reads it
    local api = call(jo, "getAPIv1") or (type(mapUI) == "table" and mapUI.mapAPI or nil)
    local x1, y1 = tonumber((call(api, "getMinXInSquares"))), tonumber((call(api, "getMinYInSquares")))
    local x2, y2 = tonumber((call(api, "getMaxXInSquares"))), tonumber((call(api, "getMaxYInSquares")))
    if not (x1 and y1 and x2 and y2) then return nil end
    return x1, y1, x2, y2
end
-- a map item the player opened (ISMap:initMapData, after the game's own init)
function M.onMapRead(mapUI, character)
    if not on() then return false, "switch_off" end
    local item = type(mapUI) == "table" and mapUI.mapObj or nil
    if item == nil then return false, "no_map" end
    local who = character or (type(mapUI) == "table" and mapUI.character) or nil
    local stashName = call(item, "getStashMap")
    local label = tostring(call(item, "getDisplayName") or call(item, "getName") or "Map")
    if type(stashName) == "string" and stashName ~= "" then
        local x, y = stashSpot(stashName)
        if not x then return false, "no_stash_location" end
        local seen, why = M.sees(who)
        if not seen then log("stash map " .. stashName .. " read, she did not see it: " .. tostring(why)); return false, why end
        local st = streetNear(x, y)
        local ok, how, e = M.record({ kind = "stash", x = x, y = y, name = label, sub = st, src = stashName })
        local a = actor()
        if not ok then if how == "full" then say(a, W.full, "full") end; return false, how end
        if how == "new" then say(a, st and fmt(W.stashNew, st) or W.stashNewNoSt, "stash_new")
        else say(a, e.looted and W.stashVisited or W.stashKnown, "stash_known") end
        return true, how
    end
    local x1, y1, x2, y2 = mapBounds(mapUI)
    if not x1 then return false, "no_bounds" end
    if x2 - x1 > M.MAX_AREA_TILES or y2 - y1 > M.MAX_AREA_TILES or x2 <= x1 or y2 <= y1 then return false, "not_an_area" end
    local seen, why = M.sees(who)
    if not seen then log("map " .. label .. " read, she did not see it: " .. tostring(why)); return false, why end
    local cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    local ok, how, e = M.record({ kind = "area", x = cx, y = cy, name = label, sub = streetNear(cx, cy), src = tostring(call(item, "getMapID") or label),
        x1 = x1, y1 = y1, x2 = x2, y2 = y2 })
    local a = actor()
    if not ok then if how == "full" then say(a, W.full, "full") end; return false, how end
    say(a, fmt(how == "new" and W.areaNew or W.areaKnown, e.name), "area_" .. how)
    return true, how
end

-- ---------------------------------------------------------------- reading the book
local function shortName(e)
    if e.kind == "house" then return e.name end
    if e.kind == "stash" then return W.stash .. (e.sub and (" " .. e.sub) or (" " .. tostring(e.name))) end
    return tostring(e.name)
end
M.shortName = shortName
function M.distanceText(e, px, py)
    if not px then return "" end
    local dx, dy = e.x - px, e.y - py
    local d = math.sqrt(dx * dx + dy * dy)
    local dist = d < 1000 and fmt(word("meters"), int(d)) or fmt(word("km"), tostring(math.floor(d / 100 + 0.5) / 10))
    if d < 3 then return dist end
    -- 8 directions without atan: north is -y. tan(22.5) = 0.4142
    local ax, ay = math.abs(dx), math.abs(dy)
    local i
    if ax <= ay * 0.4142 then i = dy < 0 and 1 or 5
    elseif ay <= ax * 0.4142 then i = dx > 0 and 3 or 7
    elseif dx > 0 then i = dy < 0 and 2 or 4
    else i = dy < 0 and 8 or 6 end
    return dist .. " " .. word("dirs")[i]
end
-- rows for the page: sections in a fixed order, looted ones last in their section
function M.rows()
    local p = player()
    local px, py = tonumber((call(p, "getX"))), tonumber((call(p, "getY")))
    local groups = { house = {}, stash = {}, area = {} }
    for _, e in ipairs(M.entries()) do if groups[e.kind] then table.insert(groups[e.kind], e) end end
    local out = {}
    for _, k in ipairs({ "house", "stash", "area" }) do
        local list = groups[k]
        if #list > 0 then
            table.sort(list, function(a, b) if (a.looted == true) ~= (b.looted == true) then return b.looted == true end return (a.seq or 0) > (b.seq or 0) end)
            out[#out + 1] = { kind = "section", text = word(k == "house" and "secHouse" or (k == "stash" and "secStash" or "secArea")) }
            for _, e in ipairs(list) do out[#out + 1] = { kind = "entry", e = e, dist = M.distanceText(e, px, py) } end
        end
    end
    return out
end
function M.contentHeight(rows)
    local h = 40
    for _, r in ipairs(rows or {}) do h = h + (r.kind == "section" and SEC_H or ROW_H) end
    return math.max(h, 80)
end

-- ---------------------------------------------------------------- going there
function M.go(e)
    local p, a = player(), actor()
    local name = shortName(e)
    if type(U.gpsSetDestination) ~= "function" then return false, "no_gps", W.noGps end
    local G = U.gps
    if type(G) == "table" then G.solo, G.mustWaitPlayer = false, false end          -- the same steps as a map choice (SolGPS U.gpsMapChoose)
    U.gpsSetDestination({ x = e.x, y = e.y, name = name })
    if type(G) == "table" and type(G.preview) == "table" then G.preview.at = nil end
    local pv, sv = call(p, "getVehicle"), call(a, "getVehicle")
    if pv ~= nil and sv ~= nil and pv == sv then
        if type(U.gpsStart) ~= "function" then return false, "no_drive", fmt(W.driveFail, name) end
        local ok, why = U.gpsStart(nil, false)                                       -- the GPS panel's Drive button
        if ok then return true, "driving", fmt(W.going, name) end
        return false, tostring(why), fmt(W.driveFail, name)
    end
    return true, "marker_set", fmt(W.askCar, name)
end
function M.setLooted(e, v)
    local b = book(false)
    if b == nil or b.entries[e.key] == nil then return false end
    b.entries[e.key].looted = v == true
    sync(M.STORE)
    return true
end
function M.onClick(h)
    local a = actor()
    if h.kind == "loot" then
        local v = not (h.e.looted == true)
        if M.setLooted(h.e, v) then say(a, fmt(v and W.lootedSet or W.lootedUnset, shortName(h.e)), "looted") end
        return true
    end
    local ok, why, line = M.go(h.e)
    say(a, line, "go_" .. tostring(why))
    return ok
end

-- the Mind's words: kind and words come from the Mind (Arabic towns already turned into their English game names)
local function lower(s) return string.lower(tostring(s or "")) end
function M.find(kind, words)
    local list = {}
    for _, e in ipairs(M.entries()) do if kind == nil or kind == "" or kind == "any" or e.kind == kind then list[#list + 1] = e end end
    if #list == 0 then return nil, "none" end
    local toks = {}
    for t in string.gmatch(lower(words), "[^%s,]+") do if #t >= 2 then toks[#toks + 1] = t end end
    if #toks > 0 then
        local best, bestN, tie = nil, 0, false
        for _, e in ipairs(list) do
            local hay = lower(table.concat({ tostring(e.name or ""), tostring(e.sub or ""), tostring(e.city or ""), tostring(e.num or ""),
                table.concat(type(e.src) == "table" and e.src or {}, " ") }, " "))
            local n = 0
            for _, t in ipairs(toks) do if string.find(hay, t, 1, true) then n = n + 1 end end
            if n > bestN then best, bestN, tie = e, n, false elseif n == bestN and n > 0 then tie = true end
        end
        if best and not tie then return best end
        if bestN == 0 then return nil, "none" end
        return nil, "ambiguous", list
    end
    local live = {}
    for _, e in ipairs(list) do if not e.looted then live[#live + 1] = e end end
    if #live == 1 then return live[1] end
    if #live == 0 and #list == 1 then return list[1] end
    return nil, "ambiguous", (#live > 0 and live or list)
end
function M.listLine()
    local list = M.entries()
    if #list == 0 then return W.listEmpty end
    local names = {}
    for i = 1, math.min(5, #list) do
        local e = list[i]
        names[#names + 1] = (e.kind == "house" and (W.house .. " " .. e.name) or (e.kind == "area" and (W.area .. " " .. tostring(e.name)) or shortName(e)))
            .. (e.looted and (" (" .. W.looted .. ")") or "")
    end
    local s = fmt(W.listHead, table.concat(names, W.sep))
    if #list > 5 then s = s .. fmt(W.listMore, int(#list - 5)) end
    return s
end
function M.order(option)
    if not on() then return false, W.off end
    option = tostring(option or "")
    if option == "" or option == "list" then return true, M.listLine() end
    local verb, kind, words = string.match(option, "^(%a+):(%a*):?(.*)$")
    if verb == "go" or verb == "looted" then
        local e, why, cands = M.find(kind, words)
        if e == nil then
            if why == "ambiguous" then
                local n = {}
                for i = 1, math.min(4, #cands) do n[#n + 1] = shortName(cands[i]) end
                return false, fmt(W.which, table.concat(n, W.sep))
            end
            return false, W.notSeen
        end
        if verb == "looted" then
            M.setLooted(e, true)
            return true, fmt(W.lootedSet, shortName(e))
        end
        local ok, _, line = M.go(e)
        return ok, line
    end
    return false, "unknown_option"
end

-- ---------------------------------------------------------------- the tab in her More window (SolPages)
local T
local texCache = {}
local function tex(n) local t = texCache[n]; if t == nil then t = getTexture and getTexture("media/textures/SolUI/" .. n .. ".png") or false; texCache[n] = t end; return t or nil end
local function inside(x, y, r) return x >= r[1] and y >= r[2] and x < r[1] + r[3] and y < r[2] + r[4] end
local function text(ui, s, x, y, w, scale, align, c, a)
    if T == nil then T = g("SolText") end
    if T == nil then return end
    T.drawLine(ui, s, x, y, w, { scale = scale, align = align or "right", r = c and c[1] or 0.94, g = c and c[2] or 0.96, b = c and c[3] or 0.98, a = a or 1 })
end
local BLUE, MUTED, GOLD = { 0.42, 0.72, 1.0 }, { 0.62, 0.71, 0.78 }, { 1.0, 0.86, 0.45 }
function M.drawPage(self)
    self.abHits = {}
    local y = CY - (self.scroll or 0)
    local mx, my = self:getMouseX(), self:getMouseY()
    local rows = self.abRows or {}
    text(self, word("hint"), CX, y + 2, CW - 6, SCALE_SUB, "right", MUTED); y = y + 30
    if #rows == 0 then
        text(self, word("empty"), CX, y + 10, CW - 6, SCALE_TXT, "right")
        return
    end
    for _, r in ipairs(rows) do
        if r.kind == "section" then
            text(self, r.text, CX, y + 4, CW - 6, SCALE_SEC, "right", BLUE); y = y + SEC_H
        else
            local e = r.e
            local rect = { CX, y + 2, CW, ROW_H - 6 }
            if y + ROW_H >= CY and y <= CY + CH then
                local bt = tex("pg_btn"); if bt then self:drawTextureScaled(bt, rect[1], rect[2], rect[3], rect[4], e.looted and 0.55 or 1, 1, 1, 1) end
                local hv = tex("pg_btn_hover")
                local btnW = e.kind == "stash" and 86 or 0
                if hv and self:isMouseOver() and inside(mx, my, rect) and not (btnW > 0 and mx < CX + btnW + 6) then self:drawTextureScaled(hv, rect[1], rect[2], rect[3], rect[4], 1, 1, 1, 1) end
                local kindTxt = e.kind == "house" and (e.lease and word("lease") or (e.num and ("#" .. tostring(e.num)) or word("house"))) or (e.kind == "area" and word("area") or word("stash"))
                text(self, shortName(e), CX + btnW + 8, y + 4, CW - btnW - 16, SCALE_TXT, "right", e.looted and MUTED or nil)
                local sub = r.dist .. "   " .. kindTxt .. (e.looted and ("   " .. word("looted")) or "")
                text(self, sub, CX + btnW + 8, y + 25, CW - btnW - 16, SCALE_SUB, "right", e.looted and MUTED or GOLD)
                if btnW > 0 then
                    local br = { CX + 4, y + 8, btnW, ROW_H - 18 }
                    local tb = tex("pg_tab_off"); if tb then self:drawTextureScaled(tb, br[1], br[2], br[3], br[4], 1, 1, 1, 1) end
                    text(self, e.looted and word("unlootBtn") or word("lootBtn"), br[1], br[2] + 2, br[3], SCALE_SUB, "center")
                    self.abHits[#self.abHits + 1] = { r = br, kind = "loot", e = e }
                end
                self.abHits[#self.abHits + 1] = { r = rect, kind = "go", e = e }
            end
            y = y + ROW_H
        end
    end
end
function M.installPage()
    local P = U.PageClass
    if type(P) ~= "table" or P.solAddressBook or type(U.pageTabs) ~= "function" then return false end
    P.solAddressBook = true
    local baseTabs = U.pageTabs
    U.pageTabs = function()
        local out = baseTabs()
        if not on() then return out end
        local at = #out + 1
        for i, tb in ipairs(out) do if tb.id == "family" then at = i + 1 end end
        table.insert(out, at, { id = "address", label = word("tab"), sol = true })
        return out
    end
    local baseRefresh = P.refresh
    P.refresh = function(self, force, follow)
        if self.tab == "address" then
            if not on() then self.tab = "status"; return baseRefresh(self, true, false) end
            if not force and nowMs() - (self.abBuild or 0) < M.REFRESH_MS then return end
            self.abBuild = nowMs()
            self.items, self.rows = {}, {}
            local ok, rows = pcall(M.rows)
            self.abRows = ok and rows or {}
            self.contentH = M.contentHeight(self.abRows)
            return
        end
        return baseRefresh(self, force, follow)
    end
    local basePre = P.prerenderBody
    P.prerenderBody = function(self)
        basePre(self)
        if self.tab ~= "address" then self.abHits = nil; return end
        self:setStencilRect(CX, CY, CW, CH)
        local ok, err = pcall(M.drawPage, self)
        self:clearStencilRect()
        if not ok then log("draw failed: " .. tostring(err)) end
    end
    local baseUp = P.onMouseUp
    P.onMouseUp = function(self, x, y)
        if self.tab == "address" and not self.dragging and not self.dd then
            for _, h in ipairs(self.abHits or {}) do
                if inside(x, y, h.r) then pcall(M.onClick, h); self:refresh(true); return true end
            end
        end
        return baseUp(self, x, y)
    end
    log("tab ready")
    return true
end

-- ---------------------------------------------------------------- hooks (once, at game start)
function M.installHooks()
    local n = 0
    local RB = g("ISReadABook")
    if type(RB) == "table" and type(RB.displayPrintMedia) == "function" and not RB.solAddressBook then
        RB.solAddressBook = true
        local base = RB.displayPrintMedia
        RB.displayPrintMedia = function(self, ...)
            local r = base(self, ...)
            local ok, err = pcall(M.onPrintMedia, self.character, self.item)
            if not ok then log("flyer failed: " .. tostring(err)) end
            return r
        end
        n = n + 1
    end
    local MP = g("ISMap")
    if type(MP) == "table" and type(MP.initMapData) == "function" and not MP.solAddressBook then
        MP.solAddressBook = true
        local base = MP.initMapData
        MP.initMapData = function(self, ...)
            local r = base(self, ...)
            local ok, err = pcall(M.onMapRead, self, self.character)
            if not ok then log("map failed: " .. tostring(err)) end
            return r
        end
        n = n + 1
    end
    return n
end

function M.install()
    if M._installed then return end
    M._installed = true
    local base = U.runAction
    U.runAction = function(id, option)
        if id == "sol_address" then return M.order(option) end
        if type(base) == "function" then return base(id, option) end
        return false, "unknown_action"
    end
    local hooks = M.installHooks()
    local page = M.installPage()
    log("ready v" .. M.VERSION .. " hooks=" .. tostring(hooks) .. " tab=" .. tostring(page))
end
if Events and Events.OnGameStart then Events.OnGameStart.Add(M.install) end
return M

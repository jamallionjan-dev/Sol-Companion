-- SolAddressPlaces.lua - switch address_places. Every paper or map that shows a place on the world map goes into Sol's book, by kind.
-- GENERATED ASCII from src/SolAddressPlaces_src.lua (apply_s84_address_places.py --gen): Arabic is stored as \\uXXXX escapes.
--
-- The vanilla mechanism (game 42.22.2, read only):
--   * Every flier and brochure is print media. Its OnCreate (ItemCodeOnCreate.onCreateBrochure / onCreateFlier / onCreateFlierNolan)
--     calls RecipeCodeHelper.setPrintMediaInfo: item modData.printMedia = { id, title, info, text }; id is the registry path of the
--     Brochure / Flier object (zombie.scripting.objects.Brochure / Flier, 22 brochures + 111 fliers), e.g. "coalfield".
--   * Reading it: ISReadABook:perform -> self:displayPrintMedia() (shared/TimedActions/ISReadABook.lua 209-211, 252-266), each time,
--     whatever was read before; complete() -> character:addReadPrintMedia(id) (363) and, with the option on,
--     revealPrintMediaLocationsOnMap(id) (300-321): WorldMapVisited:setKnownInSquares for each box of
--     PrintMediaDefinitions.MiscDetails[id].location1..location5 (shared/PrintMedia/PrintMediaDefinitions.lua, 135 ids, every one of the 133 papers has a box).
--   * The world map then draws a flier icon at the centre of every box of every id in character:getReadPrintMedia()
--     (client/ISUI/Maps/ISWorldMap.lua 451-515), named by Brochure.get(...) or Flier.get(...):getTranslationKey();
--     the paper's own "reveal on map" button does the same reveal and centres the map on the average of the box centres
--     (client/PZAPI/ui/organisms/PrintMedia.lua 286-318).
--   So the place is ALWAYS MiscDetails[id] (a mod adds its own ids to the same table), the name is the paper's title, and
--   the one Lua door every paper passes is ISReadABook:displayPrintMedia, already hooked by SolAddressBook (address_book).
--   Map items (vanilla town maps, stash maps, a mod's LootMaps.Init maps) pass ISMap:initMapData, hooked there too.
--   The world-map symbols API (WorldMapSymbolsV2 addTexture / addTranslatedText) is Java: Kahlua 42.22.2 has no
--   __classmetatables, so a Lua mod's own call to it cannot be wrapped from Lua. Nothing in Jamal's lists needs it (see the review).
--
-- This module (no new hook, no world scan): it wraps SolAddressBook.onPrintMedia. A house listing still goes the old way; any
-- other paper with a place (or a title that is a known place of the map, from the gazetteer, when the paper has no box) becomes
-- one entry: kind "place" with cat tourist | shop | public, or kind "house" for rentals and apartments. One entry per place
-- (several papers of the same place are one row with several sources). Multi-box places keep each box as a part.
-- "Our home" (SolHome) is pinned at the top while she is here and the home is known. Same rules as the book: she learns only what
-- she sees (12 tiles, his floor, awake, or the same car), her book dies with her.
-- The GPS target is SolAddressTarget's (s82): the street the paper names when it names one, else the nearest paved road; a whole site
-- (a box over BIG_BOX, like Coalfield) goes to the paved road that reaches its box (Coalfield Road at its south edge), else to its own
-- named building inside the box (the gazetteer's), never the middle of the woods.
SolUI = SolUI or {}
local U = SolUI
SolAddressPlaces = SolAddressPlaces or {}
local M = SolAddressPlaces
M.VERSION = "0.1.0"
M.BIG_BOX = 160               -- a box wider or taller than this is a whole site: the drive goes to its named building
M.MAX_PLACES = 20

local W = {
    secHome = "بيتنا", secHouse = "بيوت للبيع", secTourist = "أماكن سياحية", secShop = "محلات", secPublic = "أماكن عامة وخدمات",
    secStash = "غنائم ومخابئ", secArea = "أماكن مكشوفة",
    home = "بيتنا", tourist = "مكان سياحي", shop = "محل", public = "خدمات", lease = "للإيجار", places = "%s محل جوّا",
    sep = "، ",
    touristNew = "حفظت %s بالدفتر. شكلو محل بيستاهل نشوفو.",
    shopNew = "حفظت %s بالدفتر، منعرف وين نلاقي غراض.",
    publicNew = "حفظت %s بالدفتر، منعرف وين صار.",
    houseNew = "حفظت %s بالدفتر.",
    known = "%s عندي بالدفتر من قبل.",
    more = "هاد نفس %s، زدت هالورقة عالسطر نفسو.",
    full = "دفتري تعبّى، ما عاد في محل.",
}
local EN = { secHome = "Home", secHouse = "Houses for sale", secTourist = "Attractions", secShop = "Shops", secPublic = "Public places",
    secStash = "Stashes", secArea = "Revealed areas", home = "Home", tourist = "Attraction", shop = "Shop", public = "Public", lease = "For lease",
    places = "%s places inside", sep = ", " }
M.W = W

local function log(m) print("[SolAddressPlaces] " .. tostring(m)) end
local function g(name) return rawget(_G, name) end
local function call(o, name, ...)
    if o == nil then return nil end
    local okF, f = pcall(function() return o[name] end)
    if not okF or f == nil then return nil end
    local ok, a = pcall(f, o, ...)
    if ok then return a end
    return nil
end
function M.on() local A = g("SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on("address_places") == true end
local function isAr() return not (type(U.lang) == "function" and U.lang() == "en") end
local function word(k) if not isAr() and EN[k] ~= nil then return EN[k] end return W[k] end
local function fmt(s, a) return (string.gsub(s, "%%s", function() return tostring(a) end)) end
local function B() local b = g("SolAddressBook"); if type(b) == "table" then return b end return nil end
local function sync() if type(ModData) == "table" and type(ModData.transmit) == "function" then pcall(ModData.transmit, "Sol_AddressBook") end end
local function txt(key)
    if type(key) ~= "string" then return nil end
    if type(getTextOrNull) == "function" then local ok, s = pcall(getTextOrNull, key); if ok and type(s) == "string" then return s end end
    if type(getText) == "function" then local ok, s = pcall(getText, key); if ok and type(s) == "string" and s ~= key then return s end end
    return nil
end

-- ---------------------------------------------------------------- what kind of place (by the paper's type, then its id/title)
-- the game's brochures (zombie.scripting.objects.Brochure, 42.22.2): the item is Base.Brochure; this list is only the fallback
local BROCHURES = {}
for _, id in ipairs({ "airport", "artgalleryoflouisville", "cardinalplaza", "coalfield", "coldwarbunker", "crossroadsmall", "darkwallowguesthouse",
    "dinerinthewoods", "fossoilfield", "grandohiomall", "havishamsuites", "irvingtonspeedway", "lsu", "pondview", "quillmanor", "sanatorium",
    "scarletoakdistillery", "sleepeazzzeinn", "sunstarmotel", "wellingtonheightsgolfclub", "westmaplecountryclub", "delilah" }) do BROCHURES[id] = true end
-- the game's fliers that are not shops (the rest of the 111 are shops, job ads at shops and the gas stations)
local FLIER_CAT = {
    brandenburgfd = "public", lvfd = "public", rosewoodfd = "public", muldraughpd = "public", lvpdhq = "public", riversidepd = "public",
    brookslibrary = "public", ekroncollege = "public", fallaslakechurch = "public", wptownhall = "public", yourlocalshelterbrandenburg = "public",
    sunsetpinesfuneralhome = "public", marchridgeschooljobad = "public", mailcarrieradekron = "public", oldcgecorpbuilding = "public",
    musicfest93 = "tourist", muldraughbakesale = "tourist", riversideindependencedaypartyallwelcome = "tourist", farmersmarket = "tourist",
    fourthofjulycelebrationdixiemobilepark = "tourist", knoxgunownersclubgettogether = "tourist", onyxdriveintheater = "tourist",
    roxysrollerrink = "tourist", elveearena = "tourist", dragracingtrack = "tourist", irvingtongunclub = "tourist", meadshireestate = "tourist",
    gnomesweetgnome = "tourist", surefitnessboxingclub = "tourist", civilwarfort = "tourist",
    goldensunset = "public", fivealarmchili = "shop",
    benscabin = "house", cabinforrentdixie = "house", ducaseapartments = "house", highstreetapartments = "house", redoakapartments = "house", lowrycourt = "house",
    leafhillheights = "house",
}
-- any other id or title (a mod's paper, a gazetteer name): words
local KW = {
    { "house", { "houseforsale", "forsale", "forlease", "forrent", "lease", "apartment" } },
    { "public", { "fd$", "pd$", "pdhq", "police", "fire", "sheriff", "college", "school", "university", "library", "church", "chapel", "cathedral",
        "townhall", "town hall", "hall$", "hospital", "clinic", "shelter", "prison", "detention", "funeral", "post office", "courthouse" } },
    { "tourist", { "brochure", "derby", "rodeo", "carnival", "concert", "tournament", "show", "museum", "gallery", "fest", "festival", "party", "celebration", "park", "arena", "theater", "theatre", "rink",
        "speedway", "golf", "country club", "estate", "manor", "camp", "zoo", "fair", "tour", "historic", "coalfield", "trailer park" } },
}
local function norm(s) return (string.gsub(string.lower(tostring(s or "")), "[^%w ]", "")) end
function M.category(id, title, itemType)
    local lid = string.lower(tostring(id or ""))
    if string.match(lid, "^houseforsale%d+$") or string.match(lid, "^premises") then return "house" end
    if FLIER_CAT[lid] then return FLIER_CAT[lid] end
    if itemType == "Brochure" or BROCHURES[lid] then return "tourist" end
    local t = norm(title)
    for _, row in ipairs(KW) do
        for _, k in ipairs(row[2]) do
            if string.find(lid, k) or string.find(t, k) then return row[1] end
        end
    end
    return "shop"                                                         -- a flier with a place and no other sign: a business
end

-- ---------------------------------------------------------------- where (the game's own boxes)
-- MiscDetails is keyed by the id as written in PrintMediaDefinitions (lower case for the game's, any case or "ns:id" for a mod's)
function M.details(id)
    local defs = g("PrintMediaDefinitions")
    local md = type(defs) == "table" and defs.MiscDetails or nil
    if type(md) ~= "table" or type(id) ~= "string" then return nil end
    if type(md[id]) == "table" then return md[id], id end
    local lid = string.lower(id)
    if type(md[lid]) == "table" then return md[lid], lid end
    for k, v in pairs(md) do
        if type(k) == "string" and type(v) == "table" then
            local lk = string.lower(k)
            if lk == lid or string.match(lk, ":(.*)$") == lid or string.match(lid, ":(.*)$") == lk then return v, k end
        end
    end
    return nil
end
-- every box of location1..5; the place = the game's own centre of location1 (average of its box centres, PrintMedia.lua 314-316)
function M.boxes(det)
    if type(det) ~= "table" then return nil end
    local parts, sx, sy, n = {}, 0, 0, 0
    local ux1, uy1, ux2, uy2
    for j = 1, 5 do
        local list = det["location" .. j]
        if type(list) ~= "table" then break end
        for _, r in ipairs(list) do
            local x1, y1, x2, y2 = tonumber(r.x1), tonumber(r.y1), tonumber(r.x2), tonumber(r.y2)
            if x1 and y1 and x2 and y2 then
                parts[#parts + 1] = { loc = j, x = math.floor((x1 + x2) / 2 + 0.5), y = math.floor((y1 + y2) / 2 + 0.5), x1 = x1, y1 = y1, x2 = x2, y2 = y2 }
                if j == 1 then sx, sy, n = sx + x1 + x2, sy + y1 + y2, n + 1 end
                ux1 = ux1 and math.min(ux1, x1) or x1; uy1 = uy1 and math.min(uy1, y1) or y1
                ux2 = ux2 and math.max(ux2, x2) or x2; uy2 = uy2 and math.max(uy2, y2) or y2
            end
        end
    end
    if #parts == 0 then return nil end
    local cx, cy
    if n > 0 then cx, cy = sx / (2 * n), sy / (2 * n) else cx, cy = parts[1].x, parts[1].y end
    return { x = cx, y = cy, x1 = ux1, y1 = uy1, x2 = ux2, y2 = uy2, parts = parts }
end

-- ---------------------------------------------------------------- the map's names (SolAddressPlacesData.lua, from the gazetteer)
local function data() local d = g("SolAddressPlacesData"); if type(d) == "table" then return d end return nil end
function M.townAt(x, y)
    local d = data()
    if d == nil or not x then return nil end
    local best, bd = nil, 1400 * 1400
    for _, t in ipairs(d.towns or {}) do
        if t.x1 and x >= t.x1 and x <= t.x2 and y >= t.y1 and y <= t.y2 then
            local dd = (t.x - x) ^ 2 + (t.y - y) ^ 2
            if best == nil or best.inBox ~= true or dd < bd then best, bd = { n = t.n, inBox = true }, dd end
        elseif best == nil or best.inBox ~= true then
            local dd = (t.x - x) ^ 2 + (t.y - y) ^ 2
            if dd < bd then best, bd = { n = t.n }, dd end
        end
    end
    return best and best.n or nil
end
-- a known place whose name is the paper's title (no box on the paper)
function M.byName(title)
    local d = data()
    local t = norm(title)
    if d == nil or #t < 4 then return nil end
    for _, p in ipairs(d.named or {}) do if norm(p.n) == t then return p end end
    for _, p in ipairs(d.named or {}) do local n = norm(p.n); if #n >= 6 and string.find(t, n, 1, true) then return p end end
    for _, p in ipairs(d.towns or {}) do if norm(p.n) == t then return { n = p.n, x = p.x, y = p.y, town = true } end end
    return nil
end
-- the named building inside a big site's box (Coalfield's 256 x 296 box -> the "Coalfield" building at its entrance)
function M.gateIn(box, title)
    local d = data()
    if d == nil or type(box) ~= "table" then return nil end
    local t = norm(title)
    local best
    for _, p in ipairs(d.named or {}) do
        if p.x1 and p.x >= box.x1 and p.x <= box.x2 and p.y >= box.y1 and p.y <= box.y2 then
            local n = norm(p.n)
            if n == t or (#n >= 5 and (string.find(t, n, 1, true) or string.find(n, t, 1, true))) then best = p; break end
            best = best or p
        end
    end
    return best
end

-- ---------------------------------------------------------------- what the paper says
-- "2400 Haysville Road, Ekron, Kentucky" / "625 Dewey Street, Muldraugh, KY." -> street, city (the last such line)
function M.parseAddress(text)
    if type(text) ~= "string" then return nil end
    local t = string.gsub(text, "\\n", "\n")
    local street, city
    for line in string.gmatch(t .. "\n", "([^\n]*)\n") do
        local s = string.match(line, "^%s*(.-)%s*$")
        local a, b = string.match(s, "^(%d+[%w%.' ]-),%s*([%a%.' ]-),%s*K[Ye]")
        if a and b then street, city = a, b end
    end
    return street, city
end
-- "1. Church\n2. Greengrocer & Dry Goods\n..." -> { "Church", "Greengrocer & Dry Goods", ... } (a brochure's map key; names only)
function M.placeList(text)
    if type(text) ~= "string" then return nil end
    local t = string.gsub(text, "\\n", "\n")
    local out = {}
    for line in string.gmatch(t .. "\n", "([^\n]*)\n") do
        local n = string.match(line, "^%s*%d+%.%s+(.-)%s*$")
        if n and n ~= "" and #out < M.MAX_PLACES then out[#out + 1] = n end
    end
    if #out < 2 then return nil end
    return out
end

-- ---------------------------------------------------------------- learning a paper
local function itemType(item) return call(item, "getType") end
function M.learnPrint(character, item)
    local book = B()
    if book == nil then return false, "no_book_module" end
    local md = call(item, "getModData")
    local pm = type(md) == "table" and md.printMedia or nil
    if type(pm) ~= "table" or type(pm.id) ~= "string" then return false, "not_print_media" end
    local id = pm.id
    local title = txt(pm.title) or id
    local text = txt(pm.text)
    local det, key = M.details(id)
    local bx = M.boxes(det)
    local how = "box"
    if bx == nil then
        local p = M.byName(title) or M.byName(string.match(title, "^(.-)%s*%(") or "")
        if p == nil then return false, "no_location" end
        how = "name"
        bx = { x = p.x, y = p.y, parts = {} }
        if p.x1 then bx.x1, bx.y1, bx.x2, bx.y2 = p.x1, p.y1, p.x2, p.y2 end
    end
    local seen, why = book.sees(character)
    if not seen then log("paper " .. tostring(id) .. " read, she did not see it: " .. tostring(why)); return false, why end
    local cat = M.category(key or id, title, itemType(item))
    local street, city = M.parseAddress(text)
    city = city or M.townAt(bx.x, bx.y)
    local small = bx.x1 and (bx.x2 - bx.x1) <= M.BIG_BOX and (bx.y2 - bx.y1) <= M.BIG_BOX
    local e = { kind = cat == "house" and "house" or "place", x = bx.x, y = bx.y, name = title, sub = title, city = city, src = string.lower(id),
        lease = cat == "house" and string.find(string.lower(id), "houseforsale", 1, true) == nil or nil }
    if cat == "house" and street then e.name = street .. (city and (", " .. city) or "") end
    if small then e.x1, e.y1, e.x2, e.y2 = bx.x1, bx.y1, bx.x2, bx.y2 end
    local ok, res, n = book.record(e)
    local a = type(U.solActor) == "function" and U.solActor() or nil
    local function say(line, kind)
        local sc = g("SurvivorCompanion")
        local gu = type(sc) == "table" and sc.GameplayUtil or nil
        log("say " .. tostring(kind))
        if a ~= nil and type(gu) == "table" and type(gu.say) == "function" then pcall(gu.say, a, line) end
    end
    if not ok then if res == "full" then say(W.full, "full") end; return false, res end
    if res == "new" then
        n.cat = cat ~= "house" and cat or nil
        n.street = street
        n.how = how
        n.places = M.placeList(text)
        n.parts = (bx.parts and #bx.parts > 1) and bx.parts or nil
        if bx.x1 and not small then
            n.bx1, n.by1, n.bx2, n.by2 = bx.x1, bx.y1, bx.x2, bx.y2
            local gate = M.gateIn(bx, title)
            if gate then n.gx, n.gy, n.gx1, n.gy1, n.gx2, n.gy2, n.gate = gate.x, gate.y, gate.x1, gate.y1, gate.x2, gate.y2, gate.n end
        end
        n.sub = table.concat({ title, street or "", n.places and table.concat(n.places, " ") or "" }, " ")   -- the Mind's words find "the saloon in Coalfield"
        sync()
        log("learned " .. tostring(n.key) .. " " .. tostring(cat) .. " " .. tostring(title) .. " (" .. how .. ")")
    end
    local line = res == "new" and W[(cat == "house" and "house" or cat) .. "New"] or (res == "more" and W.more or W.known)
    say(fmt(line, n.name), "place_" .. tostring(res))
    return true, res, n
end

-- ---------------------------------------------------------------- "our home" at the top
local function houseAt(book, x, y)
    for _, e in ipairs(book.entries()) do
        if e.kind == "house" and e.x1 and x >= e.x1 - 2 and x <= e.x2 + 2 and y >= e.y1 - 2 and y <= e.y2 + 2 then return e end
    end
    return nil
end
local function streetNear(x, y)
    if type(U.gpsNearestRoad) == "function" then
        local ok, _, _, dist, name = pcall(U.gpsNearestRoad, x, y)
        if ok and type(name) == "string" and name ~= "" and (tonumber(dist) or 999) <= 60 then return name end
    end
    local T = g("SolAddressTarget")
    if type(T) == "table" and type(T.roadFor) == "function" then
        local ok, p = pcall(T.roadFor, { x1 = x, y1 = y, x2 = x, y2 = y }, nil)
        if ok and type(p) == "table" and type(p.street) == "string" and (tonumber(p.d) or 999) <= 60 then return p.street end
    end
    return nil
end
function M.syncHome()
    local book = B()
    local H = g("SolHome")
    if book == nil or type(book.book) ~= "function" then return false end
    local h = type(H) == "table" and type(H.get) == "function" and H.get() or nil
    local hasSol = type(U.solActor) == "function" and U.solActor() ~= nil
    local b = book.book(hasSol and h ~= nil)
    if b == nil or type(b.entries) ~= "table" then return false end
    local want = h and book.keyOf("home", h.x, h.y) or nil
    for k, e in pairs(b.entries) do
        if e.kind == "home" and k ~= want then b.entries[k] = nil; b.n = math.max(0, (b.n or 1) - 1); sync() end
    end
    if want == nil then return false end
    local e = b.entries[want]
    if e == nil then
        local ok, _, n = book.record({ kind = "home", x = h.x, y = h.y, name = W.home, src = "home" })
        if not ok then return false end
        e = n
        e.city = M.townAt(h.x, h.y)
        sync()
    end
    local flyer = houseAt(book, h.x, h.y)                                -- the listing of this very house: its street and number
    local street = flyer and flyer.name or (e.street or streetNear(h.x, h.y))
    if street ~= e.street then e.street = street; e.sub = street; sync() end
    return true
end

-- ---------------------------------------------------------------- the page rows
local ORDER = { "home", "house", "tourist", "shop", "public", "stash", "area" }
local SEC = { home = "secHome", house = "secHouse", tourist = "secTourist", shop = "secShop", public = "secPublic", stash = "secStash", area = "secArea" }
local function groupOf(e)
    if e.kind == "place" then return e.cat or "tourist" end
    return e.kind
end
local function kindText(e)
    local k = groupOf(e)
    local s
    if k == "home" then s = e.street or word("home")
    elseif k == "house" then s = e.lease and word("lease") or nil
    elseif k == "tourist" or k == "shop" or k == "public" then s = word(k) end
    if s == nil then return nil end
    if e.city and k ~= "home" then s = s .. word("sep") .. e.city end
    if type(e.places) == "table" and #e.places > 0 then s = s .. word("sep") .. fmt(word("places"), tostring(#e.places)) end
    return s
end
M.kindText = kindText
function M.rows(origRows)
    local book = B()
    pcall(M.syncHome)
    local p = getSpecificPlayer and getSpecificPlayer(0) or nil
    local px, py = tonumber((call(p, "getX"))), tonumber((call(p, "getY")))
    local groups = {}
    for _, k in ipairs(ORDER) do groups[k] = {} end
    for _, e in ipairs(book.entries()) do local k = groupOf(e); if groups[k] then table.insert(groups[k], e) end end
    local out = {}
    for _, k in ipairs(ORDER) do
        local list = groups[k]
        if #list > 0 then
            table.sort(list, function(a, b) if (a.looted == true) ~= (b.looted == true) then return b.looted == true end return (a.seq or 0) > (b.seq or 0) end)
            out[#out + 1] = { kind = "section", text = word(SEC[k]) }
            for _, e in ipairs(list) do out[#out + 1] = { kind = "entry", e = e, dist = book.distanceText(e, px, py), kindTxt = kindText(e) } end
        end
    end
    return out
end

-- ---------------------------------------------------------------- the drive: the s82 target, with the paper's street and a site's gate
function M.targetEntry(e)
    if type(e) ~= "table" or not (e.street and e.kind ~= "house") then return e end
    local c = {}
    for k, v in pairs(e) do c[k] = v end
    c.kind, c.name = "house", e.street                                    -- s82 drives a "house" to the street its name gives
    return c
end
-- a whole site (Coalfield, the airport): the road that reaches its box (the named street first), else its own named building
function M.siteTarget(T, e)
    if not e.bx1 or type(T.roadFor) ~= "function" then return nil end
    local box = { x1 = e.bx1, y1 = e.by1, x2 = e.bx2, y2 = e.by2, how = "site" }
    local sk = (e.street and type(T.streetKey) == "function") and T.streetKey(e.street) or nil
    local ok, p, how = pcall(T.roadFor, box, sk)
    if ok and type(p) == "table" then
        return { x = math.floor(p.x + 0.5), y = math.floor(p.y + 0.5), street = p.street, how = "site_" .. tostring(how), house = box }
    end
    if e.gx then return { x = e.gx, y = e.gy, how = "gate", house = { x1 = e.gx1 or e.gx, y1 = e.gy1 or e.gy, x2 = e.gx2 or e.gx, y2 = e.gy2 or e.gy, how = "gate" } } end
    return nil
end

-- ---------------------------------------------------------------- wiring (load, game start; both orders with s82)
function M.wrap()
    local book = B()
    if book == nil then return false end
    if type(book.onPrintMedia) == "function" and book.onPrintMedia ~= M.wPrint then
        local orig = book.onPrintMedia
        M.wPrint = function(character, item, ...)
            local ok, how, e = orig(character, item, ...)
            if not ok and M.on() and (how == "not_a_listing" or how == "no_location") then
                local okL, a, b2, c = pcall(M.learnPrint, character, item)
                if okL then return a, b2, c end
                log("paper failed: " .. tostring(a))
            end
            return ok, how, e
        end
        book.onPrintMedia = M.wPrint
    end
    if type(book.rows) == "function" and book.rows ~= M.wRows then
        local orig = book.rows
        M.wRows = function(...)
            if M.on() then
                local okR, r = pcall(M.rows)
                if okR then return r end
                log("rows failed: " .. tostring(r))
            end
            return orig(...)
        end
        book.rows = M.wRows
    end
    local T = g("SolAddressTarget")
    if type(T) == "table" and type(T.target) == "function" and T.target ~= M.wTarget then
        local orig = T.target
        M.wTarget = function(e, ...)
            if M.on() and type(e) == "table" then
                if e.bx1 then
                    local okS, s = pcall(M.siteTarget, T, e)
                    if okS and s then return s end
                end
                return orig(M.targetEntry(e), ...)
            end
            return orig(e, ...)
        end
        T.target = M.wTarget
    end
    return true
end

pcall(M.wrap)
if Events and Events.OnGameStart then Events.OnGameStart.Add(function() pcall(M.wrap) end) end
return M

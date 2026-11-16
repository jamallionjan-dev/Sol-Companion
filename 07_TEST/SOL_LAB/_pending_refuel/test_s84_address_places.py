"""s84 address_places, offline. Installers on copies (s82 then s84, s84 then s82: same files, idempotent, switch file), then the lab's
own SolAddressBook.lua (patched copy) + SolLife.lua + SolAddressTarget.lua + SolStaticRoads(Data).lua under kahlua_env, with the game's
PrintMediaDefinitions.lua, EN Print_Text.json / Print_Media.json (read only), the gazetteer's building boxes as the metagrid, and
stubs shaped like ISReadABook / ISMap / SolHome / SolPages. Jamal's eight papers and his map; every vanilla paper with a place;
mod papers (a mixed-case and a namespaced MiscDetails id, a paper with no box whose title is a map name) and a mod loot map
(Authentic Z hit list bounds). Offline PASS is not Runtime PASS.
Run: set PYTHONIOENCODING=utf-8 & python test_s84_address_places.py"""
import codecs, gzip, hashlib, json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, HERE)
from kahlua_env import lua51
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LAB_CL = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media\lua"
GATE = os.path.join(ROOT, "05_TOOLS", "sol_kahlua", "tonumber_check.py")
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
def read(p): return open(p, encoding="utf-8", newline="").read()
def run(*a): return subprocess.run([sys.executable] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
def digest(d, names): return {n: hashlib.md5(open(os.path.join(d, n), "rb").read()).hexdigest() for n in names if os.path.exists(os.path.join(d, n))}
def ar(s): return codecs.decode(str(s), "unicode_escape") if s is not None else ""

# ---------------------------------------------------------------- 1. installers on copies, both orders
r = run(os.path.join(HERE, "apply_s84_address_places.py"), "--gen")
ck("generator runs; both modules ASCII", r.returncode == 0 and all(ord(c) < 128 for f in ("SolAddressPlaces.lua", "SolAddressPlacesData.lua") for c in read(os.path.join(HERE, f))), r.stderr[-300:])
FILES = ["SolAuthority.lua", "SolAddressBook.lua", "SolGPS.lua"]
OUT = FILES + ["SolAddressTarget.lua", "SolAddressPlaces.lua", "SolAddressPlacesData.lua"]
live = digest(LAB_CL, OUT)
live_fix = read(os.path.join(LAB_CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt"))
def fresh(tag):
    T = tempfile.mkdtemp(prefix="sol_s84_%s_" % tag)
    zb = os.path.join(T, "Zomboid"); cl = os.path.join(zb, "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(cl); os.makedirs(os.path.join(zb, "Lua"))
    for f in FILES: shutil.copy(os.path.join(LAB_CL, f), cl)
    a = os.path.join(cl, "SolAuthority.lua")
    t = read(a); t = re.sub(r'\n[ \t]*"address_target",[^\n]*', "", t, count=1)          # the copy before s82
    open(a, "w", encoding="utf-8", newline="").write(t)
    open(os.path.join(zb, "Lua", "SolFixes_LAB.txt"), "w", encoding="utf-8", newline="").write("address_book=on\r\nmodel_first=on")
    return cl, os.path.join(zb, "Lua", "SolFixes_LAB.txt")
s82, s84 = os.path.join(HERE, "apply_s82_address_target.py"), os.path.join(HERE, "apply_s84_address_places.py")
clA, fixA = fresh("a"); a1 = run(s82, clA); a2 = run(s84, clA)
clB, fixB = fresh("b"); b1 = run(s84, clB); b2 = run(s82, clB)
ck("s82 then s84 applies", a1.returncode == 0 and a2.returncode == 0 and "s84 address_places applied" in a2.stdout, (a1.stderr[-300:], a2.stderr[-300:]))
ck("s84 then s82 applies", b1.returncode == 0 and b2.returncode == 0 and "s82 address_target applied" in b2.stdout, (b1.stderr[-300:], b2.stderr[-300:]))
dA = digest(clA, OUT)
ck("both orders: SolAddressBook.lua and the modules identical", {k: v for k, v in dA.items() if k != "SolAuthority.lua"} == {k: v for k, v in digest(clB, OUT).items() if k != "SolAuthority.lua"})
a3 = run(s84, clA); a4 = run(s82, clA)
ck("idempotent: second runs change nothing", a3.returncode == 0 and a4.returncode == 0 and digest(clA, OUT) == dA and "kept" in a3.stdout, a3.stdout[-300:])
auth = read(os.path.join(clA, "SolAuthority.lua"))
ck("A.FIXES: address_places once, address_target once", auth.count('"address_places"') == 1 and auth.count('"address_target"') == 1)
fx = read(fixA)
ck("switch file: address_places=on once, own line", fx.count("address_places=on") == 1 and fx.endswith("\r\n") and "model_first=on\r\n" in fx, repr(fx))
book_src = read(os.path.join(clA, "SolAddressBook.lua"))
ck("SolAddressBook: one anchor, the row's own kind line first", book_src.count("r.kindTxt or") == 1 and book_src.count('local kindTxt = ') == 1)
ck("SolAddressBook: the gps_plain_words line is kept", "SolGPSWords.cleanName" in book_src)
lab_book = read(os.path.join(LAB_CL, "SolAddressBook.lua"))
ck("SolAddressBook: nothing else changed", book_src.replace("r.kindTxt or ", "", 1) == lab_book)
staged_book = os.path.join(HERE, "SolAddressBook.lua")
if os.path.exists(staged_book):                                                      # the staged s69 file (without gps_plain_words) takes the anchor too
    T3 = tempfile.mkdtemp(prefix="sol_s84_c_"); shutil.copy(os.path.join(LAB_CL, "SolAuthority.lua"), T3); shutil.copy(staged_book, T3)
    ck("anchor also fits the staged s69 SolAddressBook.lua", run(s84, T3).returncode == 0 and "r.kindTxt or" in read(os.path.join(T3, "SolAddressBook.lua")))
ck("live lab files untouched", digest(LAB_CL, OUT) == live and read(os.path.join(LAB_CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")) == live_fix)
for f in ("SolAddressPlaces.lua", "SolAddressPlacesData.lua"):
    g = run(GATE, os.path.join(HERE, f)); ck("tonumber gate: " + f, g.returncode == 0, g.stdout[-300:])
g = run(GATE, os.path.join(clA, "SolAddressBook.lua")); ck("tonumber gate: patched SolAddressBook.lua", g.returncode == 0, g.stdout[-300:])

# ---------------------------------------------------------------- 2. the runtime
TR = {}
for f in ("Print_Text.json", "Print_Media.json"): TR.update(json.load(open(os.path.join(GAME, "shared", "Translate", "EN", f), encoding="utf-8")))
TRL = {k.lower(): v for k, v in TR.items()}
gz = json.load(gzip.open(os.path.join(ROOT, "05_TOOLS", "sol_mind", "gazetteer.json.gz"), "rt", encoding="utf-8"))
blds = [b for b in gz["buildings"] if gz["kinds"][b[4]] != "farmland"]
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.globals().TR = lambda k: TRL.get(str(k).lower())
L.execute("BL = {}")
add = L.eval("function(i, a, b, c, d) BL[i] = { a, b, c, d } end")
for i, b in enumerate(blds, 1): add(i, b[0], b[1], b[2], b[3])
L.execute(r"""
NOW = 0
SW = { address_book = true, address_target = true, address_places = true, sol_home = true }
function getTimestampMs() return NOW end
SolAuthority = { on = function(n) return SW[n] == true end }
MD = {}
ModData = { getOrCreate = function(k) MD[k] = MD[k] or {}; return MD[k] end, transmit = function() end }
STARTED = {}
Events = { OnGameStart = { Add = function(f) STARTED[#STARTED + 1] = f end }, OnTick = { Add = function() end } }
function require() end
SolBudget = { register = function() end }
LOGS = {}
function print(s) LOGS[#LOGS + 1] = tostring(s) end
local function body(t)
  function t:getX() return self.x end function t:getY() return self.y end function t:getZ() return self.z or 0 end
  function t:getVehicle() return self.vehicle end function t:isDead() return self.dead == true end function t:isAsleep() return self.asleep == true end
  return t end
PLAYER = body({ x = 10800, y = 10100, z = 0 })
SOL = body({ x = 10805, y = 10100, z = 0, id = "sc-1" })
SOL_HERE = true
function getSpecificPlayer() return PLAYER end
SolUI = { solActor = function() if SOL_HERE then return SOL end return nil end, lang = function() return "ar" end }
SAID = {}
SurvivorCompanion = { GameplayUtil = { idOf = function(a) return a.id end, say = function(a, line) SAID[#SAID + 1] = line; return true end } }
SolUI.gps = { preview = { at = 5 } }
STARTS = 0
function SolUI.gpsSetDestination(d) SolUI.gps.dest = { x = math.floor(d.x), y = math.floor(d.y), name = d.name }; return true end
function SolUI.gpsStart() STARTS = STARTS + 1; return true, nil end
ROADNAME = "Dewey Street"
function SolUI.gpsNearestRoad(x, y) return x, y, 4, ROADNAME end
SolUI.runAction = function(id, option) return false, "base:" .. tostring(id) end
function getTextOrNull(k) return TR(k) end
function getText(k) return getTextOrNull(k) or k end
HOME = nil
SolHome = { get = function() return HOME end }
-- the game's hooks, shaped like ISReadABook / ISMap
ISReadABook = {}
function ISReadABook:displayPrintMedia() end
ISMap = {}
function ISMap:initMapData() end
-- a paper as RecipeCodeHelper.setPrintMediaInfo makes it: id = registry path (lower case), title/info/text = translation keys
function paper(id, key, itype)
  key = key or id
  return { getType = function() return itype or "Flier" end,
           getModData = function() return { printMedia = { id = id, title = "Print_Media_" .. key .. "_title", info = "Print_Media_" .. key .. "_info", text = "Print_Text_" .. key .. "_info" } } end }
end
function readPaper(id, key, itype, who)
  local act = setmetatable({ character = who or PLAYER, item = paper(id, key, itype) }, { __index = ISReadABook })
  act:displayPrintMedia()
end
function openMap(stash, bounds, name, mapId)
  local item = { getStashMap = function() return stash end, getDisplayName = function() return name or "Map" end, getMapID = function() return mapId end }
  local api = { getMinXInSquares = function() return bounds[1] end, getMinYInSquares = function() return bounds[2] end,
                getMaxXInSquares = function() return bounds[3] end, getMaxYInSquares = function() return bounds[4] end }
  local ui = setmetatable({ mapObj = item, character = PLAYER, javaObject = { getAPIv1 = function() return api end } }, { __index = ISMap })
  ui:initMapData()
end
-- metagrid from the gazetteer (as test_s82)
METAGRID = true
local function def(b) local o = { b = b }
  function o:getX() return self.b[1] end function o:getY() return self.b[2] end function o:getX2() return self.b[3] end function o:getY2() return self.b[4] end
  return o end
local GRID = {}
function GRID:getBuildingAt(x, y) for i = 1, #BL do local b = BL[i]; if x >= b[1] and x <= b[3] and y >= b[2] and y <= b[4] then return def(b) end end return nil end
function getWorld() return { getMetaGrid = function(self) if METAGRID then return GRID end return nil end } end
-- SolPages
SolText = { drawLine = function(ui, s) ui.drawn[#ui.drawn + 1] = s end }
function getTexture() return {} end
Page = {}
function Page:refresh() end
function Page:prerenderBody() end
function Page:onMouseUp() return true end
SolUI.PageClass = Page
function SolUI.pageTabs() return { { id = "status" }, { id = "family" } } end
function newPage(tab)
  local p = setmetatable({ tab = tab, scroll = 0, drawn = {} }, { __index = Page })
  function p:getMouseX() return 0 end function p:getMouseY() return 0 end function p:isMouseOver() return false end
  function p:drawTextureScaled() end function p:setStencilRect() end function p:clearStencilRect() end
  return p
end
""")
for f in ("SolLife.lua",): L.execute(read(os.path.join(LAB_CL, f)))
L.execute(read(os.path.join(GAME, "shared", "PrintMedia", "PrintMediaDefinitions.lua")))
L.execute(read(os.path.join(GAME, "shared", "StashDescriptions", "StashUtil.lua")))
L.execute(read(os.path.join(GAME, "shared", "StashDescriptions", "MulStashDesc.lua")))
# mod papers, as ExtraFliersB42 / SapphCooking add them (same table): a mixed-case key and a namespaced key
L.execute("PrintMediaDefinitions.MiscDetails.AMZSteelDeon = { location1 = { { x1 = 1889, y1 = 10812, x2 = 1965, y2 = 10844 } } }")
L.execute('PrintMediaDefinitions.MiscDetails["modpack:FishingDerby"] = { location1 = { { x1 = 7200, y1 = 8500, x2 = 7290, y2 = 8580 } } }')
TRL.update({"print_media_amzsteeldeon_title": "AMZ Steel", "print_text_amzsteeldeon_info": "Steel for Kentucky.",
            "print_media_fishingderby_title": "Fallas Lake Fishing Derby", "print_text_fishingderby_info": "Bring your rod.",
            "print_media_modairport_title": "Louisville International Airport", "print_text_modairport_info": "Fly with us."})
for f in ("SolStaticRoadsData.lua", "SolStaticRoads.lua"): L.execute(read(os.path.join(LAB_CL, f)))
L.execute(read(os.path.join(clA, "SolAddressBook.lua")))
L.execute(read(os.path.join(HERE, "SolAddressPlacesData.lua")))
L.execute(read(os.path.join(HERE, "SolAddressPlaces.lua")))
L.execute(read(os.path.join(HERE, "SolAddressTarget.lua")))
L.execute("for _, f in ipairs(STARTED) do f() end")                                  # OnGameStart: book install, s84 wrap, s82 wrap
L.execute("SolAddressBook.install(); SolLife.checkIdentity()")
ck("wired: onPrintMedia, rows and the s82 target wrapped; s82 wrapped go", L.eval("SolAddressBook.onPrintMedia == SolAddressPlaces.wPrint and SolAddressBook.rows == SolAddressPlaces.wRows and SolAddressTarget.target == SolAddressPlaces.wTarget and SolAddressBook.go == SolAddressTarget.wGo"))
L.execute("pcall(SolAddressPlaces.wrap); pcall(SolAddressTarget.wrap); pcall(SolAddressPlaces.wrap)")
ck("wrapping again does not stack", L.eval("SolAddressBook.onPrintMedia == SolAddressPlaces.wPrint and SolAddressBook.go == SolAddressTarget.wGo"))
def count(): return int(L.eval("SolAddressBook.count()"))
def entry(src): return L.eval("(function(s) for _, e in ipairs(SolAddressBook.entries()) do for _, x in ipairs(e.src) do if x == s then return e end end end end)")(src)
def last(): return ar(L.eval("SAID[#SAID]"))

# ---------------------------------------------------------------- 3. Jamal's bag (all read in front of her)
JAMAL = [  # (id as the item carries it, translation key, item type, group, title)
    ("artgalleryoflouisville", "ArtGalleryofLouisville", "Brochure", "tourist", "Art Gallery of Louisville"),
    ("coalfield", "Coalfield", "Brochure", "tourist", "Coalfield"),
    ("eptoolslv", "EPToolsLV", "Flier", "shop", "E.P. Tools (Louisville)"),
    ("ekroncollege", "EkronCollege", "Flier", "public", "Ekron Community College"),
    ("houseforsale903", "HouseforSale903", "Flier", "house", None),
    ("houseforsale929", "HouseforSale929", "Flier", "house", None),
    ("musicfest93", "MusicFest93", "Flier", "tourist", "Louisville Music Festival 1993"),
    ("rosewoodfd", "RosewoodFD", "Flier", "public", "Rosewood Fire Department"),
]
grp = L.eval("function(e) if e.kind == 'place' then return e.cat end return e.kind end")
for pid, key, it, want, title in JAMAL:
    L.execute("PLAYER.x, PLAYER.y = SOL.x + 3, SOL.y")
    L.eval("readPaper")(pid, key, it)
    e = entry(pid)
    ok = e is not None and isinstance(e.x, (int, float)) and isinstance(e.y, (int, float)) and grp(e) == want and (title is None or e.name == title)
    ck("Jamal's %s: an entry with a location, group %s" % (pid, want), ok, None if e is None else (e.kind, e.cat, e.x, e.y, e.name))
L.execute("openMap(nil, { 12000, 1000, 13200, 2200 }, 'Louisville Central', 'LouisvilleMap1')")
ck("Jamal's map 'Louisville Central': an area entry (as before)", entry("LouisvilleMap1") is not None and entry("LouisvilleMap1").kind == "area")
ck("Jamal's bag: 9 rows (8 papers + 1 map)", count() == 9, count())
c = entry("coalfield")
ck("Coalfield: the place = the centre of its box (3352..3607 x 8120..8415)", (c.x, c.y) == (3480, 8268), (c.x, c.y))
ck("Coalfield: a whole site (256 x 296): the box kept apart, its own building as the gate", c.x1 is None and c.bx1 == 3352 and c.gate == "Coalfield" and 3471 <= c.gx <= 3499 and 8172 <= c.gy <= 8188, (c.x1, c.bx1, c.gate, c.gx, c.gy))
pl = [c.places[i] for i in range(1, len(c.places) + 1)] if c.places else []
ck("Coalfield: the brochure's 14 numbered places kept as names (no coordinates in the game's data)", len(pl) == 14 and pl[0] == "Church" and "El Grande Saloon" in pl and pl[-1] == "Entrance Building", pl)
ck("Coalfield: no address line in the brochure; no town within 1400 tiles (it stands alone)", c.city is None and c.street is None, (c.city, c.street))
ck("Coalfield: her line", "Coalfield" in ar(L.eval("SAID[2]")) and "\u0628\u0627\u0644\u062f\u0641\u062a\u0631" in ar(L.eval("SAID[2]")), ar(L.eval("SAID[2]")))
ek = entry("ekroncollege")
ck("Ekron College: the paper's address -> street '2400 Haysville Road', city Ekron", ek.street == "2400 Haysville Road" and ek.city == "Ekron", (ek.street, ek.city))
ck("E.P. Tools: its address line -> street '802 Southside Drive', city Louisville", entry("eptoolslv").city == "Louisville" and entry("eptoolslv").street == "802 Southside Drive", (entry("eptoolslv").city, entry("eptoolslv").street))
h = entry("houseforsale903")
ck("house 903: still the s69 way (625 Dewey Street, Muldraugh, no. 903)", h.kind == "house" and h.name == "625 Dewey Street, Muldraugh" and h.num == "903" and h.cat is None, (h.name, h.num))

# again, dedup, far, dead, asleep, switch off
n0, s0 = count(), int(L.eval("#SAID"))
L.eval("readPaper")("coalfield", "Coalfield", "Brochure")
ck("Coalfield again: no second row; she says it is in the book", count() == n0 and "\u0645\u0646 \u0642\u0628\u0644" in last(), last())
L.eval("readPaper")("crossroadsmall", "CrossRoadsMall", "Brochure"); L.eval("readPaper")("tacodelpancho", "TacodelPancho", "Flier")
cm = entry("crossroadsmall")
ck("two papers of one place (Crossroads Mall brochure + Taco del Pancho, same box): one row, two sources", cm is not None and entry("tacodelpancho") is not None and L.eval("#SolAddressBook.entries()") == n0 + 1 and len(list(cm.src.values())) == 2)
n0 = count()
L.execute("PLAYER.x = SOL.x + 30"); L.eval("readPaper")("brookslibrary", "BrooksLibrary")
ck("read 30 tiles away: not learned", count() == n0 and entry("brookslibrary") is None)
L.execute("PLAYER.x = SOL.x + 3; SOL.asleep = true"); L.eval("readPaper")("brookslibrary", "BrooksLibrary")
ck("she is asleep: not learned", count() == n0)
L.execute("SOL.asleep = false; PLAYER.z = 1"); L.eval("readPaper")("brookslibrary", "BrooksLibrary")
ck("another floor: not learned", count() == n0)
L.execute("PLAYER.z = 0; PLAYER.x = SOL.x + 300; PLAYER.vehicle = CAR; SOL.vehicle = CAR; CAR = {}")
L.execute("PLAYER.vehicle = {}; SOL.vehicle = PLAYER.vehicle"); L.eval("readPaper")("brookslibrary", "BrooksLibrary")
ck("same car, 300 tiles from where she stood: learned", entry("brookslibrary") is not None and L.eval("SolAddressPlaces.kindText")(entry("brookslibrary")) is not None)
L.execute("PLAYER.vehicle = nil; SOL.vehicle = nil; PLAYER.x = SOL.x + 3; SW.address_places = false")
n0 = count(); L.eval("readPaper")("lvfd", "LVFD")
ck("switch off: a fire-department paper is not learned (the old book: listings only)", count() == n0 and entry("lvfd") is None)
L.eval("readPaper")("houseforsale922", "HouseforSale922")
ck("switch off: a house listing still learned", entry("houseforsale922") is not None)
rows_off = L.eval("SolAddressBook.rows()")
kinds_off = set(rows_off[i].e.kind for i in range(1, len(rows_off) + 1) if rows_off[i].kind == "entry")
ck("switch off: the page shows only houses, stashes, areas (as before)", kinds_off <= {"house", "stash", "area"}, kinds_off)
L.execute("SW.address_places = true")

# mod papers
L.eval("readPaper")("amzsteeldeon", "AMZSteelDeon")
e = entry("amzsteeldeon")
ck("mod paper, mixed-case MiscDetails key (ExtraFliers' AMZSteelDeon): learned at its box", e is not None and (e.x, e.y) == (1927, 10828) and e.cat == "shop", None if e is None else (e.x, e.y, e.cat))
L.eval("readPaper")("fishingderby", "FishingDerby")
e = entry("fishingderby")
ck("mod paper, namespaced key (modpack:FishingDerby): learned, tourist", e is not None and e.cat == "tourist" and (e.x, e.y) == (7245, 8540), None if e is None else (e.cat, e.x, e.y))
L.eval("readPaper")("modairport", "modairport")
e = entry("modairport")
ck("a paper with no box whose title is a map name: the gazetteer's place (Louisville International Airport)", e is not None and e.how == "name" and abs(e.x - 15461) < 200, None if e is None else (e.x, e.y, e.how))
n0 = count(); L.eval("readPaper")("knoxknews", "NoSuchPaper")
ck("a paper with no box and no known name (a newspaper): nothing", count() == n0)
L.execute("openMap(nil, { 10540, 9240, 12990, 10480 }, 'Hit List', 'PZAZ_hitlist1')")
ck("mod loot map (Authentic Z hit list, LootMaps.Init bounds): an area row", entry("PZAZ_hitlist1") is not None and entry("PZAZ_hitlist1").kind == "area")
L.eval("readPaper")("westmaplecountryclub", "WestMapleCountryClub", "Brochure")
wm = entry("westmaplecountryclub")
ck("two-box place (West Maple Country Club): one row, both boxes kept as parts, centre = the game's average", wm is not None and len(list(wm.parts.values())) == 2 and (wm.x, wm.y) == (5875, 6420), None if wm is None else (wm.x, wm.y))

# ---------------------------------------------------------------- 4. our home
L.execute("HOME = { x = 10840, y = 10120, z = 0 }")
rows = L.eval("SolAddressBook.rows()")
first = rows[1].text, rows[2].e.kind, rows[2].e.name, rows[2].e.street
ck("home known: 'بيتنا' pinned first, with the listing's street and number (625 Dewey Street)", ar(first[0]) == "بيتنا" and first[1] == "home" and ar(first[2]) == "بيتنا" and first[3] == "625 Dewey Street, Muldraugh", [ar(x) for x in first])
L.execute("HOME = { x = 11000, y = 9000, z = 0 }; ROADNAME = 'Jefferson Rd'")
rows = L.eval("SolAddressBook.rows()")
homes = [rows[i].e for i in range(1, len(rows) + 1) if rows[i].kind == "entry" and rows[i].e.kind == "home"]
ck("home moved: one home row, the new one, street from the road names", len(homes) == 1 and homes[0].x == 11000 and homes[0].street == "Jefferson Rd", [(x.x, x.street) for x in homes])
order = [ar(rows[i].text) for i in range(1, len(rows) + 1) if rows[i].kind == "section"]
ck("sections in order: بيتنا, بيوت للبيع, أماكن سياحية, محلات, أماكن عامة وخدمات, (مخابئ), أماكن مكشوفة",
   order == ["بيتنا", "بيوت للبيع", "أماكن سياحية", "محلات", "أماكن عامة وخدمات", "أماكن مكشوفة"], order)
kt = L.eval("SolAddressPlaces.kindText")
ck("kind line: Coalfield 'مكان سياحي، 14 محل جوّا'", ar(kt(entry("coalfield"))) == "مكان سياحي، 14 محل جوّا", ar(kt(entry("coalfield"))))
ck("kind line: Ekron College 'خدمات، Ekron'; E.P. Tools 'محل، Louisville'", ar(kt(entry("ekroncollege"))) == "خدمات، Ekron" and ar(kt(entry("eptoolslv"))) == "محل، Louisville", (ar(kt(entry("ekroncollege"))), ar(kt(entry("eptoolslv")))))
p = L.eval("newPage")("address"); p.abRows = rows
L.eval("SolAddressBook.drawPage")(p)
drawn = [ar(p.drawn[i]) for i in range(1, len(p.drawn) + 1)]
ck("page: the patched row draws the row's own kind line (home street, places' kind), never 'مخبأ' for a place", any("Jefferson Rd" in d for d in drawn) and any("مكان سياحي" in d for d in drawn) and not any("مخبأ" in d for d in drawn), drawn[:8])
ck("Mind words: 'saloon' finds Coalfield", L.eval("SolAddressBook.find('any', 'saloon')").src[1] == "coalfield")
L.execute("HOME = nil"); L.eval("SolAddressBook.rows()")
ck("home unknown: no home row", not any(e.kind == "home" for e in L.eval("SolAddressBook.entries()").values()))
L.execute("HOME = { x = 10840, y = 10120, z = 0 }"); L.eval("SolAddressBook.rows()")
# death: the book goes with her; the new Sol starts empty; home comes back when home is known; papers only when re-read
SOLN = count()
L.execute("SOL.id = 'sc-2'; SolLife.checkIdentity()")
ents = list(L.eval("SolAddressBook.entries()").values())
ck("death: her book is empty (%d rows before)" % SOLN, len(ents) == 0, len(ents))
L.eval("SolAddressBook.rows()")
ents = list(L.eval("SolAddressBook.entries()").values())
ck("the new Sol: only 'our home' (home is known), no paper back-filled", len(ents) == 1 and ents[0].kind == "home", [x.kind for x in ents])
L.eval("readPaper")("coalfield", "Coalfield", "Brochure")
ck("the new Sol learns Coalfield when he opens it again in front of her", entry("coalfield") is not None and "\u062d\u0641\u0638\u062a" in last())

# ---------------------------------------------------------------- 5. the drive (s82 target through the s84 wrap)
L.execute("SolAddressTarget.cache = {}; SolUI.gps.dest = nil")
c = entry("coalfield")
L.eval("SolAddressBook.go")(c)
d = L.eval("SolUI.gps.dest")
ck("Coalfield click: the GPS target is Coalfield Road where it reaches the site (south edge), not the middle of the box", d is not None and 3352 <= d.x <= 3607 and 8380 <= d.y <= 8420, None if d is None else (d.x, d.y))
st = L.eval("SolAddressTarget.target")(c)
ck("  ... named Coalfield Road (site_nearest_road)", st.street == "Coalfield Road" and st.how == "site_nearest_road", (st.street, st.how))
L.execute("SolStaticRoadsBackup = SolStaticRoads.load; SolStaticRoads.load = function() return nil end")
st = L.eval("SolAddressTarget.target")(c)
ck("  ... no road graph: its own named building (the gate), not the box centre", st is not None and st.how == "gate" and (st.x, st.y) == (3485, 8180), None if st is None else (st.how, st.x, st.y))
L.execute("SolStaticRoads.load = SolStaticRoadsBackup")
L.eval("readPaper")("ekroncollege", "EkronCollege")
L.execute("SolAddressTarget.cache = {}")
tg = L.eval("SolAddressTarget.target")(entry("ekroncollege"))
ck("Ekron College: the target is on a road (the named street when the road graph has it)", tg is not None and tg.how in ("named_street", "nearest_road"), None if tg is None else (tg.how, tg.street, tg.x, tg.y))
print("      Ekron College target:", None if tg is None else (tg.how, tg.street, tg.x, tg.y))
L.execute("SW.address_places = false; SolAddressTarget.cache = {}")
tg2 = L.eval("SolAddressTarget.target")(entry("coalfield"))
ck("switch off: s82 target unchanged (the box centre)", tg2 is None or abs(tg2.x - 3480) + abs(tg2.y - 8268) < 400)
L.execute("SW.address_places = true")

# ---------------------------------------------------------------- 6. every vanilla paper with a place
defs = read(os.path.join(GAME, "shared", "PrintMedia", "PrintMediaDefinitions.lua"))
ids = re.findall(r"^\s*([A-Za-z0-9_]+)\s*=\s*\{\s*location1", defs, re.M)
L.execute("MD = {}; SOL.id = 'sc-9'; SolLife.checkIdentity(); HOME = nil; SAID = {}")
L.execute("SolAddressBook.MAX_ENTRIES = 1000")
reg = {}
jar_ok = True
BRO = {"airport", "artgalleryoflouisville", "cardinalplaza", "coalfield", "coldwarbunker", "crossroadsmall", "darkwallowguesthouse", "dinerinthewoods",
       "fossoilfield", "grandohiomall", "havishamsuites", "irvingtonspeedway", "lsu", "pondview", "quillmanor", "sanatorium", "scarletoakdistillery",
       "sleepeazzzeinn", "sunstarmotel", "wellingtonheightsgolfclub", "westmaplecountryclub", "delilah"}
learned, cats = 0, {}
for i in ids:
    key = next((k[len("print_media_"):-len("_title")] for k in TRL if k.startswith("print_media_") and k.endswith("_title") and k[len("print_media_"):-len("_title")] == i.lower()), i)
    L.eval("readPaper")(i.lower(), key, "Brochure" if i.lower() in BRO else "Flier")
    e = entry(i.lower())
    if e is not None:
        learned += 1
        cats[grp(e)] = cats.get(grp(e), 0) + 1
rowsN = count()
print("      vanilla ids with a box: %d, learned: %d, rows: %d (same box = one row), by group: %s" % (len(ids), learned, rowsN, cats))
ck("every vanilla paper with a box is learned (%d ids; CivilWarfort has no item)" % len(ids), learned >= len(ids) - 1, [i for i in ids if entry(i.lower()) is None])
ck("groups: houses, attractions, shops, public places all present", all(cats.get(k, 0) > 0 for k in ("house", "tourist", "shop", "public")), cats)
ck("no Lua error logged", not any("failed" in str(l) for l in L.eval("LOGS").values()), [l for l in L.eval("LOGS").values() if "failed" in str(l)][:3])
print("RESULT", "ALL PASS" if not FAIL else "%d FAILED: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)

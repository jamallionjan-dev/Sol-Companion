"""s89 address_visit, offline. The installer on copies of the CURRENT lab client (s69 + s82 + s84 installed: SolAddressBook.lua with
both anchors, SolAddressPlaces(Data).lua, SolAddressTarget.lua), idempotent, switch file; then all of them + SolLife.lua +
SolStaticRoads(Data).lua + the new SolAddressVisit.lua under kahlua_env, with the game's PrintMediaDefinitions.lua, StashUtil.lua +
MulStashDesc.lua, EN Print_Text.json / Print_Media.json (read only), the gazetteer's building boxes as the metagrid, and stubs shaped
like ISReadABook / ISMap. A3 book_visited, A4 book_hint, A5 the area entrance (address_target). Offline PASS is not Runtime PASS.
Run: set PYTHONIOENCODING=utf-8 & python test_s89_address_visit.py"""
import codecs, gzip, hashlib, json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, HERE)
from kahlua_env import lua51
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LAB_CL = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
LAB_FIX = os.path.join(LAB_CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
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

# ---------------------------------------------------------------- 1. the installer on copies of the current lab client
AP = os.path.join(HERE, "apply_s89_address_visit.py")
r = run(AP, "--gen")
ck("generator runs; module is ASCII", r.returncode == 0 and all(ord(c) < 128 for c in read(os.path.join(HERE, "SolAddressVisit.lua"))), r.stderr[-300:])
FILES = ["SolAuthority.lua", "SolAddressBook.lua", "SolAddressPlaces.lua", "SolAddressPlacesData.lua", "SolAddressTarget.lua", "SolLife.lua",
         "SolStaticRoads.lua", "SolStaticRoadsData.lua"]
OUT = FILES + ["SolAddressVisit.lua"]
live, live_fix = digest(LAB_CL, OUT), read(LAB_FIX)
ck("lab client has s82 + s84 installed (the base of s89)", "r.kindTxt or" in read(os.path.join(LAB_CL, "SolAddressBook.lua")) and
   all(os.path.exists(os.path.join(LAB_CL, f)) for f in FILES) and '"address_target"' in read(os.path.join(LAB_CL, "SolAuthority.lua")))
T = tempfile.mkdtemp(prefix="sol_s89_")
ZB = os.path.join(T, "Zomboid"); CL = os.path.join(ZB, "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(CL); os.makedirs(os.path.join(ZB, "Lua"))
FIXF = os.path.join(ZB, "Lua", "SolFixes_LAB.txt")
open(FIXF, "w", encoding="utf-8", newline="").write("address_book=on\r\naddress_target=on")
for f in FILES: shutil.copy(os.path.join(LAB_CL, f), CL)
before = digest(CL, FILES)
q1 = run(AP, CL); d1 = digest(CL, OUT); f1 = read(FIXF)
q2 = run(AP, CL)
ck("installer applies", q1.returncode == 0 and "s89 address_visit applied" in q1.stdout, q1.stderr[-400:])
ck("idempotent: a second run changes nothing", q2.returncode == 0 and digest(CL, OUT) == d1 and read(FIXF) == f1 and "kept" in q2.stdout, q2.stdout[-300:])
auth = read(os.path.join(CL, "SolAuthority.lua"))
ck("A.FIXES: book_visited once, book_hint once; address_target still once", auth.count('"book_visited"') == 1 and auth.count('"book_hint"') == 1 and auth.count('"address_target"') == 1)
ck("switch file: both on once, own lines", f1 == "address_book=on\r\naddress_target=on\r\nbook_visited=on\r\nbook_hint=on\r\n", repr(f1))
ck("no other file changed (book, places, target, life, roads)", {k: v for k, v in d1.items() if k not in ("SolAuthority.lua", "SolAddressVisit.lua")} == {k: v for k, v in before.items() if k != "SolAuthority.lua"})
ck("SolAuthority: only the two lines added", re.sub(r'\n[ \t]*"book_(visited|hint)",[^\n]*', "", auth.replace("\r\n", "\n")) == read(os.path.join(LAB_CL, "SolAuthority.lua")).replace("\r\n", "\n"))
ck("live lab files untouched", digest(LAB_CL, OUT) == live and read(LAB_FIX) == live_fix)
g = run(GATE, os.path.join(HERE, "SolAddressVisit.lua")); ck("tonumber gate: SolAddressVisit.lua", g.returncode == 0, g.stdout[-300:])
ck("file name loads after SolAddressBook / Places / Target (name order)", sorted(["SolAddressBook.lua", "SolAddressPlaces.lua", "SolAddressTarget.lua", "SolAddressVisit.lua"])[-1] == "SolAddressVisit.lua")

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
SW = { address_book = true, address_target = true, address_places = true, sol_home = true, book_visited = true, book_hint = true }
function getTimestampMs() return NOW end
SolAuthority = { on = function(n) return SW[n] == true end }
MD = {}
ModData = { getOrCreate = function(k) MD[k] = MD[k] or {}; return MD[k] end, transmit = function() end }
STARTED, TICKS = {}, {}
Events = { OnGameStart = { Add = function(f) STARTED[#STARTED + 1] = f end }, OnTick = { Add = function(f) TICKS[#TICKS + 1] = f end } }
function tickAll() for _, f in ipairs(TICKS) do f() end end
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
function SolUI.gpsSetDestination(d) SolUI.gps.dest = { x = math.floor(d.x), y = math.floor(d.y), name = d.name }; return true end
function SolUI.gpsStart() return true, nil end
function SolUI.gpsNearestRoad(x, y) return x, y, 4, "Dewey Street" end
SolUI.runAction = function(id, option) return false, "base:" .. tostring(id) end
function getTextOrNull(k) return TR(k) end
function getText(k) return getTextOrNull(k) or k end
HOME = nil
SolHome = { get = function() return HOME end }
ISReadABook = {}
function ISReadABook:displayPrintMedia() end
ISMap = {}
function ISMap:initMapData() end
function paper(id, key, itype)
  key = key or id
  return { getType = function() return itype or "Flier" end,
           getModData = function() return { printMedia = { id = id, title = "Print_Media_" .. key .. "_title", info = "Print_Media_" .. key .. "_info", text = "Print_Text_" .. key .. "_info" } } end }
end
function readPaper(id, key, itype)
  local act = setmetatable({ character = PLAYER, item = paper(id, key, itype) }, { __index = ISReadABook })
  act:displayPrintMedia()
end
function openMap(stash, bounds, name, mapId)
  bounds = bounds or { 0, 0, 0, 0 }
  local item = { getStashMap = function() return stash end, getDisplayName = function() return name or "Map" end, getMapID = function() return mapId end }
  local api = { getMinXInSquares = function() return bounds[1] end, getMinYInSquares = function() return bounds[2] end,
                getMaxXInSquares = function() return bounds[3] end, getMaxYInSquares = function() return bounds[4] end }
  local ui = setmetatable({ mapObj = item, character = PLAYER, javaObject = { getAPIv1 = function() return api end } }, { __index = ISMap })
  ui:initMapData()
end
BUILDING_CALLS = 0
local function def(b) local o = { b = b }
  function o:getX() return self.b[1] end function o:getY() return self.b[2] end function o:getX2() return self.b[3] end function o:getY2() return self.b[4] end
  return o end
local GRID = {}
function GRID:getBuildingAt(x, y) BUILDING_CALLS = BUILDING_CALLS + 1; for i = 1, #BL do local b = BL[i]; if x >= b[1] and x <= b[3] and y >= b[2] and y <= b[4] then return def(b) end end return nil end
function getWorld() return { getMetaGrid = function(self) return GRID end } end
SolText = { drawLine = function(ui, s) end }
function getTexture() return {} end
Page = {}
function Page:refresh() end
function Page:prerenderBody() end
function Page:onMouseUp() return true end
SolUI.PageClass = Page
function SolUI.pageTabs() return { { id = "status" }, { id = "family" } } end
""")
L.execute(read(os.path.join(CL, "SolLife.lua")))
L.execute(read(os.path.join(GAME, "shared", "PrintMedia", "PrintMediaDefinitions.lua")))
L.execute(read(os.path.join(GAME, "shared", "StashDescriptions", "StashUtil.lua")))
L.execute(read(os.path.join(GAME, "shared", "StashDescriptions", "MulStashDesc.lua")))
for f in ("SolStaticRoadsData.lua", "SolStaticRoads.lua", "SolAddressBook.lua", "SolAddressPlacesData.lua", "SolAddressPlaces.lua", "SolAddressTarget.lua", "SolAddressVisit.lua"):
    L.execute(read(os.path.join(CL, f)))                                                # the game's order: file names
L.execute("for _, f in ipairs(STARTED) do f() end")                                  # OnGameStart: book install, s84, s82, s89
L.execute("SolLife.checkIdentity()")
ck("wired: sees, both read hooks and the s82 target carry the s89 wrap; the book's own hooks still there",
   L.eval("SolAddressBook._s89Sees == true and ISReadABook._s89Hint == true and ISMap._s89Hint == true and SolAddressTarget._s89Area == true and ISReadABook.solAddressBook == true and ISMap.solAddressBook == true"))
L.execute("F0 = { SolAddressBook.sees, ISReadABook.displayPrintMedia, ISMap.initMapData }")
L.execute("SolAddressVisit.start(); SolAddressVisit.wrap(); for _, f in ipairs(STARTED) do f() end")
ck("starting again does not stack the s89 wraps", L.eval("F0[1] == SolAddressBook.sees and F0[2] == ISReadABook.displayPrintMedia and F0[3] == ISMap.initMapData"))
def count(): return int(L.eval("SolAddressBook.count()"))
def entry(src): return L.eval("(function(s) for _, e in ipairs(SolAddressBook.entries()) do for _, x in ipairs(e.src) do if string.lower(x) == string.lower(s) then return e end end end end)")(src)
def nsaid(): return int(L.eval("#SAID"))
def last(): return ar(L.eval("SAID[#SAID]"))
def nask(): return sum(1 for v in L.eval("SAID").values() if "فرجيني" in ar(v))
def at(ms): L.execute("NOW = %d; tickAll()" % ms)
def sol(x, y, z=0): L.execute("SOL.x, SOL.y, SOL.z = %d, %d, %d" % (x, y, z))
def near(): L.execute("PLAYER.x, PLAYER.y, PLAYER.z = SOL.x + 3, SOL.y, SOL.z")
def far(): L.execute("PLAYER.x, PLAYER.y, PLAYER.z = SOL.x + 40, SOL.y, SOL.z")

# ---------------------------------------------------------------- 3. A3 book_visited
sol(10800, 10100); near()
for s in ("MulStashMap2", "MulStashMap3", "MulStashMap4", "MulStashMap11"): L.eval("openMap")(s, None, "Muldraugh map")
ck("four stash maps read in front of her: four stash rows", all(entry(s) is not None and entry(s).kind == "stash" for s in ("MulStashMap2", "MulStashMap3", "MulStashMap4", "MulStashMap11")))
e2 = entry("MulStashMap2")
ck("MulStashMap2 at its building point (10876,10191)", (e2.x, e2.y) == (10876, 10191), (e2.x, e2.y))
n0 = nsaid()
sol(10879, 10193); at(100000); at(103000)
ck("there 3 s: not yet", e2.looted is not True)
at(107000)
ck("there 7 s: marked انزار by itself, once, she says it", e2.looted is True and e2.autoVisit is True and nsaid() == n0 + 1 and "انزار" in last() and "وصلنا" in last(), (e2.looted, last()))
at(120000)
ck("no second line while she stays", nsaid() == n0 + 1)
L.eval("SolAddressBook.setLooted")(e2, False)
at(130000); at(140000)
ck("after 'رجّعيه' it is never marked again by itself", e2.looted is False)
e3 = entry("MulStashMap3")
sol(10673, 10186); at(150000); sol(10600, 10186); at(152000); sol(10673, 10186); at(153000); at(157000)
ck("passing by (left and came back): the 6 s start again", e3.looted is not True)
at(159500)
ck("  ... then marked", e3.looted is True)
e4 = entry("MulStashMap4")
L.execute("SW.book_visited = false"); sol(10873, 10025); at(170000); at(180000); at(190000)
ck("switch off: not marked", e4.looted is not True)
L.execute("SW.book_visited = true"); at(191000); at(198000)
ck("switch on: marked", e4.looted is True)
e11 = entry("MulStashMap11")
L.execute("SOL.dead = true"); sol(10612, 10649 - 1000); sol(10612, 9649); at(200000); at(210000)
ck("dead: not marked", e11.looted is not True)
L.execute("SOL.dead = false"); sol(10612, 9649, 1); at(211000); at(218000)
ck("upstairs over the stash (z 1): marked (the box may be upstairs)", e11.looted is True)
near()
ck("the stash looted line on reading the map again: 'زرناه قبل'", (L.eval("openMap")("MulStashMap11", None, "Muldraugh map") or True) and "زرناه" in last(), last())

# ---------------------------------------------------------------- 4. A4 book_hint
L.execute("SOL.id = 'sc-2'; SolLife.checkIdentity(); SAID = {}")
sol(10800, 10100); far()
L.eval("readPaper")("coalfield", "Coalfield", "Brochure")
ck("read 40 tiles away: not learned (the rule stays)", entry("coalfield") is None and count() == 0)
ck("  ... remembered for a later ask", L.eval("#SolAddressVisit.state.pending") == 1)
ck("  ... she says nothing now (she did not see it)", nask() == 0)
at(300000); at(310000)
ck("still far: no ask", nask() == 0)
near(); at(311000)
ck("beside him: she asks once 'شو هالورقة؟ فرجيني ياها'", nask() == 1 and "شو هالورقة" in last() and "فرجيني" in last(), last())
at(320000); at(330000)
ck("asked once only", nask() == 1 and L.eval("#SolAddressVisit.state.pending") == 0)
L.eval("readPaper")("coalfield", "Coalfield", "Brochure")
ck("he opens it again beside her: learned by the book's rule", entry("coalfield") is not None)
# two papers far -> one line, after the rate limit
L.execute("NOW = 335000"); far(); L.eval("readPaper")("lvfd", "LVFD"); L.eval("readPaper")("brookslibrary", "BrooksLibrary")
L.execute("NOW = 340000"); near(); at(344000)
ck("two papers read far, she is back within the gap (5 min): no ask yet", nask() == 2 - 1)
at(311000 + 5 * 60 * 1000 + 1000)
ck("after the gap: one line for both papers", nask() == 2 and "الأوراق" in last(), last())
# a paper with no place: nothing to remember
far(); L.eval("readPaper")("knoxknews", "NoSuchPaper")
ck("a paper with no place read far: nothing remembered", L.eval("#SolAddressVisit.state.pending") == 0)
# already in her book: nothing
L.eval("readPaper")("coalfield", "Coalfield", "Brochure")
ck("a paper already in her book read far: nothing remembered", L.eval("#SolAddressVisit.state.pending") == 0)
# read far, then again beside her before she asks: no ask
L.execute("NOW = 2000000"); far(); L.eval("readPaper")("ekroncollege", "EkronCollege"); near(); L.eval("readPaper")("ekroncollege", "EkronCollege")
n0 = nask(); at(2005000)
ck("read far then again beside her: learned, no ask", entry("ekroncollege") is not None and nask() == n0 and L.eval("#SolAddressVisit.state.pending") == 0)
# maps too
L.execute("NOW = 3000000"); far(); L.execute("openMap(nil, { 12000, 1000, 13200, 2200 }, 'Louisville Central', 'LouisvilleMap1')")
ck("an area map read far: remembered", L.eval("#SolAddressVisit.state.pending") == 1 and entry("LouisvilleMap1") is None)
near(); at(3004000)
ck("  ... she asks when beside him", "شو هالورقة" in last())
near(); L.execute("openMap(nil, { 12000, 1000, 13200, 2200 }, 'Louisville Central', 'LouisvilleMap1')")
ck("  ... opened beside her: an area row", entry("LouisvilleMap1") is not None and entry("LouisvilleMap1").kind == "area")
# asleep beside him: remembered; asks when she wakes
L.execute("NOW = 4000000; SOL.asleep = true"); near(); L.eval("readPaper")("rosewoodfd", "RosewoodFD")
n0 = nask(); at(4005000)
ck("asleep beside him: not learned, remembered, no ask while asleep", entry("rosewoodfd") is None and nask() == n0 and L.eval("#SolAddressVisit.state.pending") == 1)
L.execute("SOL.asleep = false"); at(4006000)
ck("  ... she wakes: she asks", nask() == n0 + 1)
# expiry
L.execute("NOW = 5000000"); far(); L.eval("readPaper")("musicfest93", "MusicFest93")
n0 = nask(); near(); at(5000000 + 31 * 60 * 1000)
ck("more than 30 min later: forgotten, no ask", nask() == n0 and L.eval("#SolAddressVisit.state.pending") == 0)
# switch off
L.execute("SW.book_hint = false; NOW = 7000000"); far(); L.eval("readPaper")("musicfest93", "MusicFest93")
ck("switch off: nothing remembered", L.eval("#SolAddressVisit.state.pending") == 0)
L.execute("SW.book_hint = true")
# death empties it
L.execute("NOW = 8000000"); far(); L.eval("readPaper")("musicfest93", "MusicFest93")
L.execute("SOL.id = 'sc-3'; SolLife.checkIdentity()"); n0 = nask(); near(); at(8010000)
ck("she died before he came back: the new Sol does not ask about it", nask() == n0 and L.eval("#SolAddressVisit.state.pending") == 0)

# ---------------------------------------------------------------- 5. A5 the area: nearest entrance on the road
near(); L.execute("openMap(nil, { 12000, 1000, 13200, 2200 }, 'Louisville Central', 'LouisvilleMap1')")
A = entry("LouisvilleMap1")
onroad = L.eval(r"""function(x, y)
  local gr = SolStaticRoads.load(); local best = 1e9
  for e = 1, #gr.EA do if not gr.ED[e] then
    local ax, ay, bx, by = gr.NX[gr.EA[e]], gr.NY[gr.EA[e]], gr.NX[gr.EB[e]], gr.NY[gr.EB[e]]
    local dx, dy = bx - ax, by - ay; local l = dx * dx + dy * dy; local t = l > 0 and ((x - ax) * dx + (y - ay) * dy) / l or 0
    if t < 0 then t = 0 elseif t > 1 then t = 1 end
    local d = math.sqrt((ax + dx * t - x) ^ 2 + (ay + dy * t - y) ^ 2); if d < best then best = d end end end
  return best end""")
tgt = L.eval("SolAddressTarget.target")
L.execute("PLAYER.x, PLAYER.y = 10800, 10100; BUILDING_CALLS = 0")                     # home in Muldraugh: south-west of Louisville
t1 = tgt(A)
ck("from Muldraugh: an entrance on the area's edge (south or west side), on a paved road", t1 is not None and t1.how == "area_entrance" and
   12000 <= t1.x <= 13200 and 1000 <= t1.y <= 2200 and (t1.y >= 2200 - 3 or t1.x <= 12000 + 3) and onroad(t1.x, t1.y) <= 1.5,
   None if t1 is None else (t1.how, t1.x, t1.y, t1.street, onroad(t1.x, t1.y)))
print("      from Muldraugh:", None if t1 is None else (t1.how, t1.street, t1.x, t1.y))
ck("  ... no building scan of the whole map (s82's footprint is not used for an area)", L.eval("BUILDING_CALLS") == 0, L.eval("BUILDING_CALLS"))
L.execute("PLAYER.x, PLAYER.y = 12600, 400")
t2 = tgt(A)
ck("from the north: an entrance on the north edge", t2 is not None and t2.how == "area_entrance" and t2.y <= 1000 + 3 and onroad(t2.x, t2.y) <= 1.5, None if t2 is None else (t2.how, t2.x, t2.y))
L.execute("PLAYER.x, PLAYER.y = 14000, 1600")
t3 = tgt(A)
ck("from the east: an entrance on the east edge", t3 is not None and t3.how == "area_entrance" and t3.x >= 13200 - 3, None if t3 is None else (t3.how, t3.x, t3.y))
L.execute("PLAYER.x, PLAYER.y = 12600, 1600")
t4 = tgt(A)
ck("already inside: the paved road nearest the area's centre", t4 is not None and t4.how == "area_centre_road" and abs(t4.x - 12600) + abs(t4.y - 1600) < 150 and onroad(t4.x, t4.y) <= 1.5, None if t4 is None else (t4.how, t4.x, t4.y))
L.execute("PLAYER.vehicle = { getX = function() return 10800 end, getY = function() return 10100 end }; SOL.vehicle = PLAYER.vehicle; SolUI.gps.dest = nil")
L.eval("SolAddressBook.go")(A)
d = L.eval("SolUI.gps.dest")
ck("a click in the car: the GPS gets the entrance (the car's position counts)", d is not None and (d.x, d.y) == (t1.x, t1.y), None if d is None else (d.x, d.y))
L.execute("PLAYER.vehicle = nil; SOL.vehicle = nil; PLAYER.x, PLAYER.y = 10800, 10100")
L.eval("readPaper")("houseforsale903", "HouseforSale903")
h = entry("houseforsale903")
L.execute("SolAddressTarget.cache = {}")
th = tgt(h)
ck("a house is unchanged (s82: Dewey St in front of 625)", th is not None and th.how == "named_street" and th.street == "Dewey St", None if th is None else (th.how, th.street))
L.execute("SW.address_target = false")
t5 = tgt(A)
ck("address_target off: the area goes the old way (no entrance)", t5 is None or t5.how not in ("area_entrance", "area_centre_road"))
L.execute("SW.address_target = true")
L.execute("openMap(nil, { 3000, 13600, 3060, 13660 }, 'Woods', 'WoodsMap')")
W_ = entry("WoodsMap")
tw = tgt(W_) if W_ is not None else None
ck("an area no paved road reaches: no error, the old way", W_ is not None and (tw is None or tw.how not in ("area_entrance",)) and any("the old way" in str(l) for l in L.eval("LOGS").values()),
   None if tw is None else (tw.how, tw.x, tw.y))

ck("no Lua error logged", not any("failed" in str(l) for l in L.eval("LOGS").values()), [l for l in L.eval("LOGS").values() if "failed" in str(l)][:3])
print("RESULT", "ALL PASS" if not FAIL else "%d FAILED: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)

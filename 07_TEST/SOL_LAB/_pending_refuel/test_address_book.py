"""Offline tests for address_book (SolAddressBook.lua + apply_s69_address_book.py), lupa. usage: python test_address_book.py
The game's own data is used where it is plain Lua or JSON (read only): PrintMediaDefinitions.lua, StashUtil.lua + MulStashDesc.lua,
EN Print_Text.json / Print_Media.json. The hooks are stubs shaped like ISReadABook / ISMap; SolLife.lua is the lab's, patched by the
installer in a temp copy. Offline PASS is not Runtime PASS."""
import codecs, glob, json, os, shutil, subprocess, sys, tempfile
from lupa import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media\lua"
LAB = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid"
ok_n = bad = 0
def check(name, ok, extra=None):
    global ok_n, bad
    print(("PASS " if ok else "FAIL ") + name + ("" if ok or extra is None else "   -> " + str(extra))); ok_n += bool(ok); bad += (not ok)
def ar(s): return codecs.decode(str(s), "unicode_escape")

# ---------------------------------------------------------------- installer on copies
T = tempfile.mkdtemp(prefix="sol_addr_")
cl, mind = os.path.join(T, "1", "2", "3", "4", "5", "6", "client"), os.path.join(T, "mind")
os.makedirs(cl); os.makedirs(mind); os.makedirs(os.path.join(T, "1", "Lua"))
for f in ("SolAuthority.lua", "SolLife.lua"): shutil.copy(os.path.join(LAB, "mods", "Sol_LAB", "42", "media", "lua", "client", f), cl)   # read only: copied
shutil.copy(os.path.join(LAB, "Lua", "SolFixes_LAB.txt"), os.path.join(T, "1", "Lua"))
for f in glob.glob(r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind\*.py"): shutil.copy(f, mind)
mr0 = open(os.path.join(mind, "model_router.py"), encoding="utf-8").read()
def apply(*args): return subprocess.run([sys.executable, os.path.join(HERE, "apply_s69_address_book.py")] + list(args), capture_output=True, text=True)
r1 = apply(cl, mind)
snap1 = {p: open(p, encoding="utf-8").read() for p in [os.path.join(cl, "SolAuthority.lua"), os.path.join(cl, "SolLife.lua"), os.path.join(cl, "SolAddressBook.lua"),
         os.path.join(T, "1", "Lua", "SolFixes_LAB.txt"), os.path.join(mind, "chat_service.py"), os.path.join(mind, "model_router.py")]}
r2 = apply(cl, mind)
snap2 = {p: open(p, encoding="utf-8").read() for p in snap1}
check("installer runs twice on copies", r1.returncode == 0 and r2.returncode == 0, (r1.stderr[-400:], r2.stderr[-400:]))
check("second run changes nothing (idempotent)", snap1 == snap2)
auth = snap2[os.path.join(cl, "SolAuthority.lua")]
check("switch address_book in A.FIXES once", auth.count('"address_book"') == 1)
check("address_book=on once in SolFixes_LAB.txt", snap2[os.path.join(T, "1", "Lua", "SolFixes_LAB.txt")].count("address_book=on") == 1)
life_src = snap2[os.path.join(cl, "SolLife.lua")]
check("SolLife: the respawn forgets the book, once, beside streets/stations", life_src.count("solAddressBookForget") == 1 and life_src.index("solAddressBookForget") < life_src.index("L.last = nil"))
check("the module is ASCII only (SolText rule)", all(ord(c) < 128 for c in open(os.path.join(HERE, "SolAddressBook.lua"), encoding="ascii").read()))

# ---------------------------------------------------------------- the Lua runtime
TR = {}
for f in ("Print_Text.json", "Print_Media.json"): TR.update(json.load(open(os.path.join(GAME, "shared", "Translate", "EN", f), encoding="utf-8")))
STUBS = r"""
NOW = 0
SWITCH = true
function getTimestampMs() return NOW end
SolAuthority = { on = function(n) return n == "address_book" and SWITCH end }
MD = {}
ModData = { getOrCreate = function(k) MD[k] = MD[k] or {}; return MD[k] end, transmit = function() end }
TICKS = 0
Events = { OnGameStart = { Add = function() end }, OnTick = { Add = function() TICKS = TICKS + 1 end } }
SolBudget = { register = function() end }
function require() end
CAR, CAR2 = { name = "car" }, { name = "car2" }
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
-- the GPS (SolGPS.lua U.gpsSetDestination / U.gpsStart, as the Drive button)
SolUI.gps = { preview = { at = 5 } }
STARTS = 0
function SolUI.gpsSetDestination(d) SolUI.gps.dest = { x = math.floor(d.x), y = math.floor(d.y), name = d.name }; return true end
function SolUI.gpsStart(speed, solo) STARTS = STARTS + 1; return true, nil end
function SolUI.gpsNearestRoad(x, y) return x, y, 4, "Dewey Street" end
SolUI.runAction = function(id, option) return false, "base:" .. tostring(id) end
-- translations
function getTextOrNull(k) local v = TR(k); if v == nil then return nil end return v end
function getText(k) return getTextOrNull(k) or k end
-- the hooks, shaped like the game's
ISReadABook = {}
OPENED = 0
function ISReadABook:displayPrintMedia() OPENED = OPENED + 1 end
ISMap = {}
INITS = 0
function ISMap:initMapData() INITS = INITS + 1 end
function readFlyer(id, who)
  local key = id
  local it = { getModData = function() return { printMedia = { id = string.lower(id), title = "Print_Media_" .. key .. "_title", info = "Print_Media_" .. key .. "_info", text = "Print_Text_" .. key .. "_info" } } end }
  local act = setmetatable({ character = who or PLAYER, item = it }, { __index = ISReadABook })
  act:displayPrintMedia()
end
function openMap(stash, bounds, name, mapId)
  local item = { getStashMap = function() return stash end, getDisplayName = function() return name or "Map" end, getMapID = function() return mapId end }
  local api = { getMinXInSquares = function() return bounds and bounds[1] end, getMinYInSquares = function() return bounds and bounds[2] end,
                getMaxXInSquares = function() return bounds and bounds[3] end, getMaxYInSquares = function() return bounds and bounds[4] end }
  local ui = setmetatable({ mapObj = item, character = PLAYER, javaObject = { getAPIv1 = function() return api end } }, { __index = ISMap })
  ui:initMapData()
end
-- SolPages: the page class and the tabs (as SolPages.lua builds them)
SolText = { drawLine = function(ui, s) ui.drawn[#ui.drawn + 1] = s end }
function getTexture() return {} end
BASE = { refresh = 0, up = 0 }
Page = {}
function Page:refresh(force, follow) BASE.refresh = BASE.refresh + 1 end
function Page:prerenderBody() self.hits = {}; self:refresh(false) end
function Page:onMouseUp(x, y) BASE.up = BASE.up + 1; return true end
SolUI.PageClass = Page
function SolUI.pageTabs() return { { id = "status" }, { id = "skills" }, { id = "orders" }, { id = "loadout" }, { id = "family" } } end
function newPage(tab)
  local p = setmetatable({ tab = tab, scroll = 0, drawn = {}, mx = 0, my = 0 }, { __index = Page })
  function p:getMouseX() return self.mx end function p:getMouseY() return self.my end function p:isMouseOver() return true end
  function p:drawTextureScaled() end function p:setStencilRect() end function p:clearStencilRect() end
  return p
end
function tabIds() local t = {} for _, x in ipairs(SolUI.pageTabs()) do t[#t + 1] = x.id end return table.concat(t, ",") end
"""
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.globals().TR = lambda k: TR.get(k)
L.execute(STUBS)
L.execute(open(os.path.join(cl, "SolLife.lua"), encoding="ascii").read())                       # the patched copy
L.execute(open(os.path.join(GAME, "shared", "PrintMedia", "PrintMediaDefinitions.lua"), encoding="utf-8").read())
L.execute(open(os.path.join(GAME, "shared", "StashDescriptions", "StashUtil.lua"), encoding="utf-8").read())
L.execute(open(os.path.join(GAME, "shared", "StashDescriptions", "MulStashDesc.lua"), encoding="utf-8").read())
# a second listing of the very same house (same rectangle as no. 903): two flyers, one row
L.execute("PrintMediaDefinitions.MiscDetails.houseforsale9031 = PrintMediaDefinitions.MiscDetails.houseforsale903")
TR["Print_Text_houseforsale9031_info"] = TR["Print_Text_HouseforSale903_info"]
ticks0 = L.eval("TICKS")
L.execute(open(os.path.join(HERE, "SolAddressBook.lua"), encoding="ascii").read())
check("no per-tick work: loading the module adds no OnTick", L.eval("TICKS") == ticks0)
L.execute("SolAddressBook.install()")
B = L.eval("SolAddressBook")
def count(): return int(L.eval("SolAddressBook.count()"))
def said(): return ar(L.eval("SAID[#SAID]") or "")
L.execute("SolLife.checkIdentity()")                                     # first id of the save: not a death

# houses
L.execute("readFlyer('HouseforSale903')")
check("house: read near her -> one entry", count() == 1)
e = L.eval("SolAddressBook.entries()[1]")
check("house: kind, place = center of PrintMediaDefinitions rect (10816..10863, 10096..10143)", e.kind == "house" and e.x == 10840 and e.y == 10120, (e.kind, e.x, e.y))
check("house: exact in-game address and number", e.name == "625 Dewey Street, Muldraugh" and e.city == "Muldraugh" and e.num == "903", (e.name, e.city, e.num))
check("house: her line names it", said() == "حفظت بيت 625 Dewey Street, Muldraugh بالدفتر.", said())
check("house: the game's own window still opens", L.eval("OPENED") == 1)
L.execute("readFlyer('HouseforSale903')")
check("re-reading an already-read flyer: no second row, she knows it", count() == 1 and said() == "بيت 625 Dewey Street, Muldraugh عندي بالدفتر من قبل." and L.eval("OPENED") == 2, said())
L.execute("readFlyer('houseforsale9031')")
e = L.eval("SolAddressBook.entries()[1]")
check("dedupe: a second listing of the same house is one row with two sources", count() == 1 and len(list(e.src.values())) == 2 and "زدت" in said(), said())
L.execute("SOL.x = 10850")                                               # 50 tiles away
L.execute("readFlyer('HouseforSale895')")
check("far (50 tiles): not learned", count() == 1)
L.execute("SOL.x = 10811")                                               # 11 tiles: inside SEE_TILES = 12
L.execute("readFlyer('HouseforSale895')")
check("near (11 tiles): learned", count() == 2)
L.execute("SOL.x = 10813")
L.execute("readFlyer('HouseforSale907')")
check("13 tiles: not learned", count() == 2)
L.execute("SOL.x, SOL.y, SOL.vehicle, PLAYER.vehicle = 10900, 10180, CAR, CAR")
L.execute("readFlyer('HouseforSale907')")
check("same car (seat positions apart): learned", count() == 3)
L.execute("SOL.vehicle = CAR2")
L.execute("readFlyer('HouseforSale912')")
check("other car and far: not learned", count() == 3)
L.execute("SOL.vehicle, PLAYER.vehicle, SOL.x, SOL.y = nil, nil, 10802, 10100")
L.execute("SOL.asleep = true; readFlyer('HouseforSale912'); SOL.asleep = false")
check("asleep beside him: not learned", count() == 3)
L.execute("SOL.z = 1; readFlyer('HouseforSale912'); SOL.z = 0")
check("other floor: not learned", count() == 3)
L.execute("SOL_HERE = false; readFlyer('HouseforSale912'); SOL_HERE = true")
check("not in the world (far record): not learned", count() == 3)
L.execute("readFlyer('Fossoil1')")
check("a flyer that is not a listing is not an address", count() == 3)
L.execute("readFlyer('PremisesforLease863')")
e = L.eval("SolAddressBook.entries()[1]")
check("Homeward premises for lease is a listing too (302 3rd St., West Point)", count() == 4 and e.name == "302 3rd St., West Point" and e.lease, e.name)

# stash and area maps
L.execute("openMap('MulStashMap2')")
e = L.eval("SolAddressBook.entries()[1]")
check("stash map: building of StashDescriptions MulStashMap2 (10876, 10191)", count() == 5 and e.kind == "stash" and e.x == 10876 and e.y == 10191, (e.kind, e.x, e.y))
check("stash map: her line with the street near it", said() == "خريطة مخبأ! حفظت المكان، قريب من Dewey Street.", said())
check("stash map: the game's own init still runs", L.eval("INITS") == 1)
L.execute("openMap('MulStashMap2')")
check("stash map re-read: no second row", count() == 5 and said() == "هاد المخبأ عندي بالدفتر من قبل.")
L.execute("openMap(nil, {9700, 12470, 10579, 13199}, 'March Ridge Map', 'MarchRidgeMap')")
e = L.eval("SolAddressBook.entries()[1]")
check("area map: kept as an area with its rectangle and center", count() == 6 and e.kind == "area" and e.x == 10140 and e.y == 12835 and e.x1 == 9700 and e.y2 == 13199, (e.kind, e.x, e.y))
check("area map: her line", said() == "حفظت منطقة March Ridge Map بالدفتر.", said())
L.execute("openMap(nil, {0, 0, 19800, 15900}, 'Map', 'Base.Map')")
check("a whole-world map is not an area", count() == 6)
L.execute("SWITCH = false; readFlyer('HouseforSale912'); SWITCH = true")
check("switch off: nothing learned", count() == 6)

# the tab and the click
check("tab: right under Family", L.eval("tabIds()") == "status,skills,orders,loadout,family,address")
L.execute("SWITCH = false"); off_tabs = L.eval("tabIds()"); L.execute("SWITCH = true")
check("tab: gone with the switch off", off_tabs == "status,skills,orders,loadout,family")
L.execute("P = newPage('address'); P:refresh(true); P:prerenderBody()")
check("tab: refresh never builds a Living Fellows page", L.eval("BASE.refresh") == 0)
check("tab: tab label in Arabic", ar(L.eval("SolUI.pageTabs()[6].label")) == "دفتر العناوين")
drawn = [ar(L.eval("P.drawn[%d]" % i)) for i in range(1, int(L.eval("#P.drawn")) + 1)]
check("tab: sections in order, entries drawn", drawn.index("بيوت للبيع") < drawn.index("غنائم ومخابئ") < drawn.index("أماكن مكشوفة") and "625 Dewey Street, Muldraugh" in drawn, drawn[:6])
check("tab: distance and direction on each row", any(("م " in d or "كم " in d) and ("شمال" in d or "جنوب" in d or "شرق" in d or "غرب" in d) for d in drawn), drawn)
# click the Dewey row, not in a car: marker + question
L.execute("""for _, h in ipairs(P.abHits) do if h.kind == 'go' and h.e.name == '625 Dewey Street, Muldraugh' then HIT = h end end
P.onMouseUp(P, HIT.r[1] + 200, HIT.r[2] + 5)""")
check("click not in car: GPS marker on the house, no drive", L.eval("SolUI.gps.dest.x") == 10840 and L.eval("SolUI.gps.dest.y") == 10120 and L.eval("STARTS") == 0)
check("click not in car: she asks", said() == "حطيتلك العلامة عـ625 Dewey Street, Muldraugh. بدك نروح بالسيارة؟", said())
check("click: the page's own handler is not called for a row", L.eval("BASE.up") == 0)
L.execute("SOL.vehicle, PLAYER.vehicle = CAR, CAR; P:prerenderBody()")
L.execute("for _, h in ipairs(P.abHits) do if h.kind == 'go' and h.e.kind == 'area' then HIT = h end end; P.onMouseUp(P, HIT.r[1] + 200, HIT.r[2] + 5)")
check("click in the same car: marker + the GPS drive (gpsStart once)", L.eval("SolUI.gps.dest.x") == 10140 and L.eval("STARTS") == 1 and L.eval("SolUI.gps.preview.at") is None)
check("click in car: her line", said() == "يلا، ماشيين عـMarch Ridge Map.", said())
L.execute("SOL.vehicle, PLAYER.vehicle = nil, nil; P.onMouseUp(P, 500, 300)")
check("click elsewhere goes to the page's own handler", L.eval("BASE.up") == 1)
L.execute("P:prerenderBody(); for _, h in ipairs(P.abHits) do if h.kind == 'loot' then HIT = h end end; P.onMouseUp(P, HIT.r[1] + 2, HIT.r[2] + 2)")
check("stash: mark looted from the tab", L.eval("HIT.e.looted") is True and said().startswith("تمام، علّمت"), said())
L.execute("openMap('MulStashMap1')"); L.execute("P:refresh(true)")
rows = L.eval("P.abRows")
order = [rows[i].e.looted for i in range(1, len(list(rows.keys())) + 1) if rows[i].kind == "entry" and rows[i].e.kind == "stash"]
check("looted stash goes to the bottom of its section", order == [False, True], order)
L.execute("openMap('MulStashMap2')")
check("looted stash re-read: 'we visited it'", said() == "هاد المخبأ زرناه قبل.", said())

# the Mind's action
okL, lineL = L.eval("SolUI.runAction('sol_address', 'list')")
check("action list: her book in one line", okL is True and "302 3rd St., West Point" in ar(lineL) and "منطقة March Ridge Map" in ar(lineL), ar(lineL))
okG, lineG = L.eval("SolUI.runAction('sol_address', 'go:house:dewey')")
check("action go:house:dewey (not in car): marker + question", okG is True and ar(lineG).startswith("حطيتلك العلامة عـ625 Dewey") and L.eval("SolUI.gps.dest.x") == 10840)
L.execute("SOL.vehicle, PLAYER.vehicle = CAR, CAR")
okG2, lineG2 = L.eval("SolUI.runAction('sol_address', 'go:house:302 west point')")
check("action go:house:302 west point (in car): drives to 302 3rd St.", okG2 is True and ar(lineG2) == "يلا، ماشيين عـ302 3rd St., West Point." and L.eval("STARTS") == 2, ar(lineG2))
okA, lineA = L.eval("SolUI.runAction('sol_address', 'go:house:')")
check("action go:house: with several houses: she asks which", okA is False and ar(lineA).startswith("عندي أكتر من عنوان"), ar(lineA))
okN, lineN = L.eval("SolUI.runAction('sol_address', 'go:house:riverside')")
check("action: an address she never saw", okN is False and ar(lineN) == "ما شفت هالعنوان معك.", ar(lineN))
okR, lineR = L.eval("SolUI.runAction('sol_address', 'go:area:')")
check("action go:area: the one area", okR is True and L.eval("SolUI.gps.dest.x") == 10140)
L.execute("SOL.vehicle, PLAYER.vehicle = nil, nil")
okT, lineT = L.eval("SolUI.runAction('sol_address', 'looted:stash:')")
check("action looted:stash: marks the one not yet looted", okT is True and ar(lineT).startswith("تمام، علّمت"), ar(lineT))
okB, why = L.eval("SolUI.runAction('sol_farm', 'x')")
check("other actions pass through", why == "base:sol_farm")
L.execute("SWITCH = false"); okO, lineO = L.eval("SolUI.runAction('sol_address', 'list')"); L.execute("SWITCH = true")
check("action with the switch off: a line, not an order", okO is False and ar(lineO) == "دفتر العناوين مسكّر هلأ.")

# death, reload, respawn
n_before = count()
L.execute("SolLife.checkIdentity()")
check("reload (same id): the same book", count() == n_before and L.eval("MD.Sol_AddressBook.life") == "sc-1#0")
L.execute("SOL.id = 'sc-2'; SolLife.checkIdentity()")
check("respawn: the book is empty, the death counted", count() == 0 and L.eval("MD.Sol_Life.deaths") == 1)
okE, lineE = L.eval("SolUI.runAction('sol_address', 'list')")
check("respawn: she says her book is empty", ar(lineE) == "دفتري فاضي، ما شفت معك ولا إعلان ولا خريطة لهلّق.", ar(lineE))
L.execute("readFlyer('HouseforSale903')")
check("relearn after respawn: the same flyer read again before her", count() == 1 and L.eval("MD.Sol_AddressBook.life") == "sc-2#1" and said().startswith("حفظت بيت"))
L.execute("SOL.id = 'sc-3'; readFlyer('HouseforSale895')")
check("respawn caught at the capture itself (before SolLife's tick): old book gone, new one has only this", count() == 1 and L.eval("MD.Sol_Life.deaths") == 2 and L.eval("SolAddressBook.entries()[1].num") == "895")
L.execute("MD.Sol_AddressBook.life = 'sc-1#0'")
check("a book of an earlier life is never shown", count() == 0)

# ---------------------------------------------------------------- the Mind's words, on the patched copy
code = r"""
import sys, json; sys.path.insert(0, sys.argv[1]); import chat_service as CS, model_router as MR
cases = {"شو في عنا عناوين": "list", "شو في عناوين بدفترك؟": "list", "فرجيني دفتر العناوين": "list",
         "خديني عالعنوان Dewey": "go:any:dewey", "خديني عالبيت اللي بالإعلان": "go:house:", "خديني عالبيت اللي للبيع بمولدرو": "go:house:muldraugh",
         "روحي عالمخبأ اللي بشارع Dewey": "go:stash:dewey", "وديني عالإعلان رقم ٩٠٣": "go:house:903", "خديني عالمنطقة اللي بالخريطة": "go:area:",
         "خلصنا من المخبأ": "looted:stash:", "سوقي عالبيت": None, "سوقي عالعلامة": None, "خديني عالبيت": None, "رتبي الاغراض": None,
         "شو في عنا اكل": None, "اعطيني الدفتر": None, "سوقي على West Point": None}
for t, want in cases.items():
    got = CS.address_intent(t)
    print(("OK " if got == want else "BAD ") + t, got)
print("REPLY", CS.address_reply({"ok": True, "reason": "حفظت"}) == "حفظت",
      CS.address_reply({"ok": False, "reason": "unknown_option"}) == "ما قدرت إفتح الدفتر هلأ.", CS.address_reply({"ok": None}) == "لحظة، عم دوّر بالدفتر.")
# the chat path: the address check runs before the far-away orders and the model, and sends one action
sent = []
CS.run_action = lambda d, a, o=None, wait=3.0: (sent.append((a, o)) or {"ok": True, "reason": "يلا، ماشيين عـ625 Dewey Street, Muldraugh."})
c = CS.Chat.__new__(CS.Chat); c.dir = "."; c.log = lambda *a: None; c._forced = None
c._far_order = lambda *a, **k: (_ for _ in ()).throw(AssertionError("far order before the book"))
done = c._pre_intents([{"role": "user", "text": "خديني عالعنوان Dewey"}], {}, None)
print("PRE", sent == [("sol_address", "go:any:dewey")], c._forced == "يلا، ماشيين عـ625 Dewey Street, Muldraugh.", bool(done))
c._model_first = lambda: True
print("MODEL", c._route_by_model([{"role": "user", "text": "شو في عنا عناوين"}], {}, "", {}, None) is None)
print("CARD", "address_book" in MR.COMMANDS, "address_book" in MR.sheet([], ""))
print("NKEYS", len(MR.COMMANDS))
"""
r4 = subprocess.run([sys.executable, "-c", code, mind], capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
out = r4.stdout
check("Mind: 17 phrases map to the one action (or to nothing)", r4.returncode == 0 and "BAD" not in out and out.count("OK ") == 17, out + r4.stderr[-800:])
check("Mind: her line from the game is the chat reply; codes become a short line", "REPLY True True True" in out, out)
check("Mind: the chat path sends sol_address before the far-away orders", "PRE True True True" in out, out + r4.stderr[-800:])
check("Mind: the model is not asked for an address sentence", "MODEL True" in out, out + r4.stderr[-800:])
import re as _re
n0 = len(_re.findall(r'^\s{4}"[a-z_]+":\s', mr0.split("COMMANDS = {")[1].split("}")[0], _re.M))
nk = int((_re.search(r"NKEYS (\d+)", out) or [0, 0])[1]) if _re.search(r"NKEYS (\d+)", out) else -1
check("Mind: one card entry, address_book, and no other new one", "CARD True True" in out and nk == n0 + 1, (n0, nk))
shutil.rmtree(T, ignore_errors=True)
print("RESULT", ok_n, "/", ok_n + bad)
sys.exit(1 if bad else 0)

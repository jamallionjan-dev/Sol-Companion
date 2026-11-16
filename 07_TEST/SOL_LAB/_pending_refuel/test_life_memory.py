"""Her memory questions, what dying costs, the first-spawn kit, streets and her marker."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
M = r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind"
sys.path.insert(0, M)
import memory_answers as MA, intent_engine as IE, chat_service as CS, reply_gate as RG
from kahlua_env import lua51
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)

class Mem:
    def __init__(self, places=(), home=None): self.data = {"places": list(places), "home": home}; self.saved = 0
    def save(self): self.saved += 1
SNAP = {"player": {"x": 1000, "y": 1000}, "sol": {"x": 1000, "y": 950}, "vehicles": [{"name": "Van", "x": 1040, "y": 1000, "fuel": 9, "fuelMax": 75}, {"name": "Car", "x": 900, "y": 1000}], "knownStreets": ["Main St", "Oak Ave", "River Rd"], "currentStreet": "Oak Ave"}
STA = [(1200, 1000, 90, "gas2go"), (1000, 1500, 40, "fossoil"), (800, 800, 12, "")]
PLACES = [{"name": "المزرعة", "x": 1, "y": 2}, {"name": "الصيدلية", "x": 3, "y": 4}]
def ask(t, snap=SNAP, mem=None, st=STA): return MA.answer(t, snap, mem if mem is not None else Mem(PLACES, {"x": 1000, "y": 1200}), (lambda: st))
for t in ["شو الكازيات اللي بتعرفيها", "وين الكازيات", "كم كازيات بتعرفي", "سمي الكازيات اللي حافظتيها", "وين المحطات", "what stations do you know"]:
    r = ask(t); ck("stations: " + t, r and "3 كازيات" in r and "غاز تو غو" in r and "فوس أويل" in r, r)
ck("stations: distance and side", "200 متر بالشرق" in ask("وين الكازيات"), ask("وين الكازيات"))
ck("stations: none", "ولا كازية" in ask("شو الكازيات اللي بتعرفيها", st=[]))
ck("stations: game silent, not a false no", ask("شو الكازيات", st=None) is None)
for t in ["شو الاماكن اللي حافظتها", "كم مكان... الاماكن كم", "احكيلي عن الاماكن", "أماكن شو بتعرفي"]:
    r = ask(t); ck("places: " + t, r and "مكانين" in r and "المزرعة" in r, r)
ck("places: none", "ولا مكان" in ask("شو الاماكن", mem=Mem()))
for t in ["شو الشوارع اللي بتعرفيها", "كم شوارع حافظة", "الطرقات شو بتعرفي"]:
    r = ask(t); ck("streets: " + t, r and "3 شوارع" in r and "Main St" in r, r)
ck("streets: none", "ولا شارع" in ask("شو الشوارع", snap={"knownStreets": []}))
ck("this road known", "هاد Oak Ave" in ask("بتعرفي هالطريق"), ask("بتعرفي هالطريق"))
ck("this road new", "أول مرة" in ask("بتعرفي هالطريق", snap=dict(SNAP, currentStreet="New Rd")))
for t in ["وينك", "سول وينك", "وين انتي", "where are you"]:
    r = ask(t); ck("self: " + t, r and "50 متر بالشمال" in r, r)
ck("home", "200 متر بالجنوب" in ask("وين البيت"), ask("وين البيت"))
STA2 = [(1020, 1010, 90, "gas2go"), (5000, 5000, 40, "fossoil")]
for t, st, want in [("سول شو اسم هذ الكازية", STA2, "غاز تو غو"), ("شو اسم هالمحطة", STA2, "غاز تو غو"), ("شو اسم الكازية", STA, "ما بعرف كازية هون"), ("شو اسم الشارع", STA2, "Oak Ave"), ("تحقق من اسم الشارع ومحطة البنزين", STA2, "Oak Ave")]:
    r = ask(t, st=st); ck("name: " + t, r and want in r, r)
def ask2(t, street="Elm St", st=STA2): return MA.answer(t, SNAP, Mem(), (lambda: st), (lambda: street))
ck("street looked up now, not the last sample", "Elm St" in ask2("شو اسم هالشارع"), ask2("شو اسم هالشارع"))
ck("lookup fails: the last sample", "Oak Ave" in ask2("شو اسم هالشارع", None), ask2("شو اسم هالشارع", None))
for t in ["وين نحنا", "سول وين صرنا", "وين وصلنا", "where are we"]:
    r = ask2(t); ck("where: " + t, r and "Elm St" in r and "غاز تو غو" in r, r)
ck("where, no station near", "كازية" not in ask2("وين نحنا", st=[(5000, 5000, 9, "gas2go")]), ask2("وين نحنا", st=[(5000, 5000, 9, "gas2go")]))
for t in ["شو اسم هاي الكازية", "شو اسم الكازية هون", "شو هاي الكازية"]:
    r = ask(t, st=STA2); ck("this station: " + t, r and "غاز تو غو" in r, r)
r = ask("تحقق من اسم الشارع ومحطة البنزين", st=STA2); ck("both in one answer", r and "Oak Ave" in r and "غاز تو غو" in r, r)
ck("no street known", "ما بعرفه" in ask("شو اسم الشارع", snap={"player": {"x": 1, "y": 1}}))
ck("no home", "ما عنا بيت" in ask("وين البيت", mem=Mem()))
ck("the car", "40 متر بالشرق" in ask("وين السيارة"), ask("وين السيارة"))
ck("cars", "سيارتين" in ask("كم سيارات حوالينا"), ask("كم سيارات حوالينا"))
for t in ["وين اقرب كازية", "زمري مرة وحدة", "طفي الضو", "سول عبي السيارة بنزين", "كيف حالك", "الشارع حلو"]:
    ck("not for this layer: " + t, ask(t) is None, ask(t))
ck("model is told what she knows", "المزرعة" in MA.facts(SNAP, Mem(PLACES)) and "Oak Ave" in MA.facts(SNAP, Mem(PLACES)))
for t, want in [("كم كازية حافظة", "count"), ("كم كازية في بالخريطة", "count_map"), ("قديش كازية بالخريطة كلها", "count_map")]:
    g = IE.parse_high_confidence(t); ck("count: " + t, g and g["slots"].get("ask") == want, g)
bad = [s for s in MA.LOST_MEMORY_LINES if any(w in s for w in RG.BANNED) or RG.mojibake(s)]
ck("her lines after dying are in character", not bad, bad)

# the Mind forgets on a death
said = []
class Goals: mind = type("M", (), {"say": staticmethod(said.append)})(); mind_lock = None
def chat():
    c = CS.Chat.__new__(CS.Chat); c.goals, c.log = Goals(), (lambda x: None); return c
m = Mem(PLACES, {"x": 1, "y": 2}); c = chat()
ck("no death: nothing", c._life_watch({"solLife": {"deaths": 0}}, m) is False and len(m.data["places"]) == 2)
ck("a death: forgets", c._life_watch({"solLife": {"deaths": 1}}, m) is True and m.data["places"] == [] and m.saved == 1)
ck("the home stays", m.data["home"] == {"x": 1, "y": 2})
ck("she says it once", len(said) == 1 and said[0] in MA.LOST_MEMORY_LINES, said)
ck("seen once: not again", c._life_watch({"solLife": {"deaths": 1}}, m) is False and len(said) == 1)
m.data["places"] = PLACES[:1]; ck("next death: again", c._life_watch({"solLife": {"deaths": 2}}, m) is True and m.data["places"] == [])
ck("no life data: nothing", c._life_watch({}, Mem(PLACES)) is False)

# the Lua side
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("""
NOW = 1000; print = function() end; TICK = nil
function getTimestampMs() return NOW end
Events = { OnTick = { Add = function(f) TICK = f end } }
STORE = {}
ModData = { getOrCreate = function(k) STORE[k] = STORE[k] or {}; return STORE[k] end, transmit = function() end }
SX, SY = 100, 100
SOL = { getX = function() return SX end, getY = function() return SY end, getVehicle = function() return CAR end }
CAR = nil
LOOKS = 0
ROAD, DIST = "Main St", 3
SolUI = { solActor = function() return THERE and SOL or nil end, gps = {} }
function SolUI.gpsNearestRoad(x, y) LOOKS = LOOKS + 1; return x, y, DIST, ROAD end
THERE = true
FORGOT = 0
function solStationsForget() FORGOT = FORGOT + 1 end
""")
L.execute(open(os.path.join(HERE, "SolLife.lua"), encoding="utf-8").read()); g = L.globals()
def t(ms=2100): g.NOW = g.NOW + ms; g.TICK()
L.execute('MYID = "sol-1"; SurvivorCompanion = { GameplayUtil = { idOf = function(a) return MYID end } }')
ck("first sight of her: not a death", g.SolLife.checkIdentity() is False and not L.eval("(STORE.Sol_Life or {}).deaths"))
t(); ck("learns the street she is on", L.eval('STORE.Sol_Streets.streets["Main St"] ~= nil'))
looks = g.LOOKS; t(); ck("not moved: no lookup", g.LOOKS == looks, g.LOOKS)
L.execute('SX = 200; ROAD = "Oak Ave"'); g.NOW = g.NOW + 6000; g.TICK(); ck("moved: next street", L.eval('STORE.Sol_Streets.streets["Oak Ave"] ~= nil'))
L.execute('SX = 240; ROAD = "Far"; DIST = 40'); g.NOW = g.NOW + 6000; g.TICK(); ck("too far from any road: not learned", L.eval('STORE.Sol_Streets.streets["Far"] == nil'))
L.execute('SX = 300; ROAD = "x"; DIST = 3; SolUI.gps.preview = { route = { points = { { x = 299, y = 100, street = "Route St" } } } }'); L.execute("LOOKS = 0"); g.NOW = g.NOW + 2100; g.TICK()
ck("on a trip the route's own names, no lookup", L.eval('STORE.Sol_Streets.streets["Route St"] ~= nil') and g.LOOKS == 0, g.LOOKS)
L.execute("SolUI.gps.preview = nil")
g.SolLife.noteStreet("Asked St", 400, 400); ck("a street he asked about is learned", L.eval('STORE.Sol_Streets.streets["Asked St"] ~= nil') and g.SolLife.current == "Asked St")
L.execute('STORE.Sol_Streets.streets["Asked St"] = nil; STORE.Sol_Streets.count = STORE.Sol_Streets.count - 1')
ck("snapshot", list(L.eval("(select(2, SolLife.snapshot()))").values()) == ["Main St", "Oak Ave", "Route St"])
ck("a reload never calls it: streets stay", L.eval('STORE.Sol_Streets.count') == 3)
ck("a reload, same id: not a death", g.SolLife.checkIdentity() is False and not L.eval("STORE.Sol_Life.deaths"))
L.execute('THERE = false'); ck("gone for now: nothing", g.SolLife.checkIdentity() is False); L.execute('THERE = true')
L.execute('MYID = "sol-2"')
ck("a new id: a death", g.SolLife.checkIdentity() is True and L.eval("STORE.Sol_Life.deaths") == 1)
ck("streets gone", L.eval("STORE.Sol_Streets.count") == 0 and L.eval("LUA_NEXT(STORE.Sol_Streets.streets) == nil"))
ck("stations forgotten", g.FORGOT == 1)
ck("seen once: only one death", g.SolLife.checkIdentity() is False and L.eval("STORE.Sol_Life.deaths") == 1)
L.execute('MYID = "sol-3"'); g.SolLife.checkIdentity(); ck("second death counts", L.eval("STORE.Sol_Life.deaths") == 2)
L.execute('solStationsForget = nil; MYID = "sol-4"'); ck("no Java: still fine", g.SolLife.checkIdentity() is True)
L.execute('SAVEID = SurvivorCompanion; SurvivorCompanion = nil'); ck("no companion system: nothing", g.SolLife.checkIdentity() is False); L.execute("SurvivorCompanion = SAVEID")
L.execute('MYID = "sol-5"; ModData = nil'); ck("no ModData: no crash", g.SolLife.checkIdentity() is False); L.execute("ModData = { getOrCreate = function(k) STORE[k] = STORE[k] or {}; return STORE[k] end, transmit = function() end }")
L.execute('MYID = "sol-5"'); g.SolLife.checkIdentity()
L.execute('LB0 = STORE.Sol_Life.deaths; MYID = "sol-6"'); g.NOW = g.NOW + 2100; g.TICK(); ck("the tick notices it by itself", L.eval("STORE.Sol_Life.deaths == LB0 + 1"))
# her marker
DRAW = """
DRAWN = {}
UIX = { drawTextureScaled = function(self, t, x, y, w, h, a) DRAWN = { x = x, y = y, a = a, w = w } end }
API = { worldToUIX = function(self, x, y) return x * 2 end, worldToUIY = function(self, x, y) return y * 3 end }
TEXTURE = {}
function getTexture() return TEXTURE end
"""
L.execute(DRAW)
L.execute("SX, SY = 50, 60; THERE = true"); g.NOW = g.NOW + 1100; g.TICK(); g.SolUI.solMapDraw(g.UIX, g.API)
ck("marker at her place, centred", g.DRAWN.x == 100 - 11 and g.DRAWN.y == 180 - 11 and g.DRAWN.a == 1, (g.DRAWN.x, g.DRAWN.y, g.DRAWN.a))
L.execute("CAR = { getX = function() return 70 end, getY = function() return 80 end }"); g.NOW = g.NOW + 1100; g.TICK(); g.SolUI.solMapDraw(g.UIX, g.API); ck("in a car: on the car", g.DRAWN.x == 140 - 11, g.DRAWN.x)
L.execute("CAR = nil; THERE = false"); g.NOW = g.NOW + 1100; g.TICK(); g.SolUI.solMapDraw(g.UIX, g.API); ck("out of reach: dim at the last place", g.DRAWN.a == 0.45 and g.DRAWN.x == 140 - 11, (g.DRAWN.a, g.DRAWN.x))
L.execute("SX = 10; THERE = true"); g.NOW = g.NOW + 100; g.TICK(); ck("updated about once a second, not every frame", L.eval("SolLife._pos().x") == 70, L.eval("SolLife._pos().x"))
L.execute("CAR = nil")
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)

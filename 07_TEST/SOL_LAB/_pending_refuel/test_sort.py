"""Offline tests for item_sort v0.2: the Lua runner on stub containers (lupa), and the Mind's words on copies. usage: python test_sort.py
Offline PASS is not Runtime PASS: the stubs are the game as SolSort expects it (weights in kg, hasRoomFor(chr, item), instant verified transfers)."""
import codecs, glob, os, shutil, subprocess, sys, tempfile
from lupa import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
ok_n = bad = 0
def check(name, ok, extra=None):
    global ok_n, bad
    print(("PASS " if ok else "FAIL ") + name + ("" if ok or extra is None else "   -> " + str(extra))); ok_n += bool(ok); bad += (not ok)
def ar(s): return codecs.decode(str(s), "unicode_escape")

STUBS = r"""
NOW = 0
SWITCH = true
function getTimestampMs() return NOW end
SolAuthority = { on = function(n) return n == "item_sort" and SWITCH end }
local function jlist(t) return { size = function() return #t end, get = function(_, i) return t[i + 1] end } end
local function wsum(t) local s = 0 for _, it in ipairs(t) do s = s + it.w end return s end
SOL = { x = 0, y = 0, inv = { items = {}, cap = 10 } }
function SOL.inv:getItems() return jlist(self.items) end
function SOL.inv:getCapacityWeight() return wsum(self.items) end
function SOL.inv:hasRoomFor(chr, it) return wsum(self.items) + it.w <= self.cap end
function SOL.inv:Remove(it) for i, x in ipairs(self.items) do if x == it then table.remove(self.items, i) return end end end
function SOL:getInventory() return self.inv end
function SOL:getMaxWeight() return self.inv.cap end
function SOL:getX() return self.x end function SOL:getY() return self.y end function SOL:getZ() return 0 end
FLOOR = {}
function SOL:getCurrentSquare() local s = SQ(self.x, self.y); s.AddWorldInventoryItem = function(_, it) FLOOR[#FLOOR + 1] = it; it.cont = nil end; return s end
SolUI = { solActor = function() return SOL end, runAction = function() return false, "base" end }
GOTOS = {}
SolUI.solGoto = function(x, y)            -- she gets there at once, except next to a FLAKY box (she never arrives)
  GOTOS[#GOTOS + 1] = x .. "," .. y
  for bx in pairs(FLAKY) do if math.abs(x - bx) <= 1 and math.abs(y - 1) <= 1 then return true end end
  SOL.x, SOL.y = x, y; return true end
CLS, CLS_TICK = 0, 0
function item(cat, name, off, extra, w)
  local it = { cat = cat, name = name, off = off, w = w or 1 }
  function it:getFullType() return "Base." .. self.name end
  function it:getOffAgeMax() return self.off end
  function it:getContainer() return self.cont end
  function it:getUnequippedWeight() return self.w end
  function it:isFavorite() return extra == "fav" end
  function it:isEquipped() return false end
  return it end
function box(kind, room, x, cap)
  local c = { kind = kind, room = room, x = x, items = {}, cap = cap or 50, powered = true }
  function c:getItems() return jlist(self.items) end
  function c:getType() return self.kind end
  function c:getCapacity() return self.cap end
  function c:getCapacityWeight() return wsum(self.items) end
  function c:hasRoomFor(chr, it) if self.refuse then return false end return wsum(self.items) + it.w <= self.cap end
  function c:isItemAllowed() return true end
  function c:isPowered() return self.powered end
  function c:setDrawDirty() end
  return c end
function put(c, it) c.items[#c.items + 1] = it; it.cont = c; return it end
function names(c) local t = {} for _, it in ipairs(c.items) do t[#t + 1] = it.name end table.sort(t) return table.concat(t, ",") end
SAID = {}
LABELS = {}
UNREACHABLE, CORNER_ONLY, FLAKY, SQS = {}, {}, {}, {}
local function boxAt(x, y) if y ~= 1 then return nil end for _, c in ipairs(BOXES) do if c.x == x then return c end end end
local function near(t, x, y) for bx in pairs(t) do if math.abs(x - bx) <= 1 and math.abs(y - 1) <= 1 then return bx end end end
-- the world: boxes stand on y = 1 and are not standable; around an UNREACHABLE box nothing is; around a CORNER_ONLY box only the corners are
function SQ(x, y)
  local k = x .. "," .. y
  if SQS[k] then return SQS[k] end
  local s = { x = x, y = y }
  function s:getX() return x end function s:getY() return y end function s:getZ() return 0 end
  function s:canStand()
    if boxAt(x, y) then return false end
    if near(UNREACHABLE, x, y) then return false end
    local c = near(CORNER_ONLY, x, y)
    if c and (x == c or y == 1) then return false end
    return true end
  function s:canReachTo(o) return math.max(math.abs(o.x - x), math.abs(o.y - y)) <= 1 end
  local c = boxAt(x, y)
  if c then function s:getObjects() return jlist({ { getContainerByIndex = function() return c end } }) end end
  SQS[k] = s
  return s end
SurvivorCompanion = {
  Logistics = { itemCategory = function(it) CLS = CLS + 1; CLS_TICK = CLS_TICK + 1; return it.cat end },
  PersonalItems = { isProtected = function(it) return it.name == "Protected" end },
  BaseLife = { storageRows = function() return LABELS end },
  GameplayUtil = {
    say = function(a, line) SAID[#SAID + 1] = line; return true end,
    transferItemVerified = function(from, to, it)
      for i, x in ipairs(from.items) do if x == it then table.remove(from.items, i); to.items[#to.items + 1] = it; it.cont = to; return true end end
      return false end,
    gridSquare = function(x, y) return SQ(x, y) end } }
function places() local out = {} for _, c in ipairs(BOXES) do out[#out + 1] = { x = c.x, y = 1, z = 0, oi = 0, ci = 0, kind = c.kind, room = c.room } end return out end
SolUI.invLast = function() return { places = places() } end
function TICK() NOW = NOW + 600; CLS_TICK = 0; SolSort.tick(); MAXCLS = math.max(MAXCLS or 0, CLS_TICK) end
"""

def fresh(gap0=True):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(STUBS)
    src = open(os.path.join(HERE, "SolSort.lua"), encoding="ascii").read()       # ASCII only: Kahlua reads it as is
    L.execute(src)
    L.execute("SolSort.install()")
    if gap0: L.execute("SolSort.SAY_GAP_MS = 0")
    return L
def run(L, n=300): L.execute("for i = 1, %d do TICK() end" % n)
def said(L): return [ar(L.eval("SAID[%d]" % i)) for i in range(1, L.eval("#SAID") + 1)]

HOUSE = """
CRATE = box("crate", "garage", 1); FRIDGE = box("fridge", "kitchen", 5); COUNTER = box("counter", "kitchen", 6)
TOOLS = box("toolcabinet", "garage", 9); MED = box("medicine", "bathroom", 12); WARD = box("wardrobe", "bedroom", 15)
SHELF = box("shelves", "livingroom", 18); BCOUNT = box("counter", "bathroom", 20); STOVE = box("stove", "kitchen", 22)
BOXES = { CRATE, FRIDGE, COUNTER, TOOLS, MED, WARD, SHELF, BCOUNT, STOVE }
put(CRATE, item("food", "Steak", 4)); put(CRATE, item("food", "TinnedBeans", 1000000000)); put(CRATE, item("tools", "Hammer"))
put(CRATE, item("medicine", "Bandage")); put(CRATE, item("clothing", "Tshirt")); put(CRATE, item("general", "Junk"))
put(CRATE, item("tools", "Protected")); put(CRATE, item("tools", "Saw", nil, "fav")); put(CRATE, item("farming", "CarrotSeed"))
put(CRATE, item("tools", "KeyRing"))
put(TOOLS, item("tools", "Screwdriver")); put(COUNTER, item("literature", "Novel")); put(COUNTER, item("clothing", "Socks"))
put(STOVE, item("food", "PanFriedSteak", 4))
"""

# ---------------------------------------------------------------- the house
L = fresh()
L.execute(HOUSE + "ok, why = SolUI.runAction('sol_sort', 'run')")
check("order accepted", L.eval("ok") is True and L.eval("why") == "started")
check("a second order while working changes nothing", L.eval("select(2, SolUI.runAction('sol_sort', 'run'))") == "already")
run(L)
check("perishable food to the powered fridge", L.eval("names(FRIDGE)") == "Steak")
check("tinned food to the kitchen counter", L.eval("names(COUNTER)") == "TinnedBeans")
check("tools to the tool cabinet, the one there stays", L.eval("names(TOOLS)") == "Hammer,Screwdriver")
check("medicine to the medicine cabinet", L.eval("names(MED)") == "Bandage")
check("clothes from two containers to the wardrobe", L.eval("names(WARD)") == "Socks,Tshirt")
check("a book from the kitchen to the shelves", L.eval("names(SHELF)") == "Novel")
check("a bathroom counter never gets kitchen food", L.eval("#BCOUNT.items") == 0)
check("general, protected, favourite, key and seeds (crate) stay", L.eval("names(CRATE)") == "CarrotSeed,Junk,KeyRing,Protected,Saw")
check("the stove is never opened", L.eval("names(STOVE)") == "PanFriedSteak")
check("done, hold released, nothing in her hands", L.eval("SolSort.held()") is False and L.eval("#SOL.inv.items") == 0)
check("plan computed once, one round", L.eval("SolSort.state.stats.plans") == 1 and L.eval("SolSort.state.stats.rounds") == 1)
visits = [(L.eval("SolSort.state.visits[%d].place" % i), L.eval("SolSort.state.visits[%d].put" % i), L.eval("SolSort.state.visits[%d].take" % i))
          for i in range(1, L.eval("#SolSort.state.visits") + 1)]
check("each container visited once", len(visits) == len(set(v[0] for v in visits)) == 7, visits)
check("batches: everything from the crate in one visit, both clothes put down in one visit",
      visits[0] == (1, 0, 5) and any(v[0] == 6 and v[1] == 2 for v in visits), visits)
check("the walk: crate first (nearest source), then outward", [v[0] for v in visits] == [1, 2, 3, 4, 5, 6, 7], visits)
lines = said(L)
check("start line", lines[0] == "طيب، خليني شوف شو في بالخزاين أول.", lines[:1])
check("plan line counts what is out of place", "في 7 أغراض مش بمحلّن، يلا رتّبن." in lines, lines)
check("progress names what and where: food in the kitchen", "عم رتّب الأكل بالمطبخ" in lines, lines)
check("progress: fresh food in the fridge, clothes in the bedroom",
      "عم رتّب الأكل الطازة بالبراد" in lines and "عم رتّب التياب بغرفة النوم" in lines, lines)
check("summary at the end", lines[-1].startswith("رتّبت 7 أغراض: ") and "تياب لغرفة النوم" in lines[-1] and lines[-1].endswith("."), lines[-1])
check("budget per tick respected (scan/classify/plan/moves)",
      L.eval("SolSort.state.stats.max.scan") <= 4 and L.eval("SolSort.state.stats.max.items") <= 40 and L.eval("SolSort.state.stats.max.moves") <= 4
      and L.eval("MAXCLS") <= 40)
print("   lines:", " | ".join(lines))

L = fresh(gap0=False)
L.execute(HOUSE + "SolUI.runAction('sol_sort', 'run')"); run(L)
prog = [l for l in said(L) if l.startswith("عم رتّب")]
check("progress lines are rate-limited (one per 7 s)", 1 <= len(prog) < 6, prog)

# ---------------------------------------------------------------- fridge power
L = fresh()
L.execute("""CRATE = box("crate", "garage", 1); FRIDGE = box("fridge", "kitchen", 5); FRIDGE.powered = false; COUNTER = box("counter", "kitchen", 6)
BOXES = { CRATE, FRIDGE, COUNTER }; put(CRATE, item("food", "Steak", 4)); put(FRIDGE, item("food", "Milk", 3)); SolUI.runAction("sol_sort", "run")""")
run(L)
check("no power: fresh food goes to the counter, not into a dead fridge", L.eval("names(FRIDGE)") == "Milk" and L.eval("names(COUNTER)") == "Steak")
check("no power: what is already in the fridge is not dragged out", L.eval("#FRIDGE.items") == 1)

# ---------------------------------------------------------------- full containers
L = fresh()
L.execute("""CRATE = box("crate", "garage", 1); TOOLS = box("toolcabinet", "garage", 9, 1.5)
BOXES = { CRATE, TOOLS }; put(CRATE, item("tools", "Hammer")); put(CRATE, item("tools", "Saw")); put(CRATE, item("tools", "Axe")); SolUI.runAction("sol_sort", "run")""")
run(L)
check("a cabinet with room for one: one goes, two stay, none carried", L.eval("#TOOLS.items") == 1 and L.eval("#CRATE.items") == 2 and L.eval("#SOL.inv.items") == 0)
check("the summary says what found no place", "وفي غرضين ما لقيتلن محل." in said(L)[-1], said(L)[-1:])

L = fresh()
L.execute("""CRATE = box("crate", "garage", 1); TOOLS = box("toolcabinet", "garage", 9); TOOLS.refuse = true
BOXES = { CRATE, TOOLS }; put(CRATE, item("tools", "Hammer")); SolUI.runAction("sol_sort", "run")""")
run(L)
check("cabinet refuses at the last moment: the hammer goes back to its crate", L.eval("names(CRATE)") == "Hammer" and L.eval("#SOL.inv.items") == 0 and L.eval("SolSort.held()") is False)

L = fresh()
L.execute("""CRATE = box("crate", "garage", 1); TOOLS = box("toolcabinet", "garage", 9); TOOLS2 = box("toolcabinet", "garage", 30); TOOLS.refuse = true
BOXES = { CRATE, TOOLS, TOOLS2 }; put(TOOLS2, item("tools", "Wrench")); put(TOOLS, item("tools", "Pliers")); put(TOOLS, item("tools", "Drill"))
put(CRATE, item("tools", "Hammer")); SolUI.runAction("sol_sort", "run")""")
run(L)
check("a refused cabinet: the next one of its kind takes it", L.eval("names(TOOLS2)") == "Hammer,Wrench" and L.eval("#SOL.inv.items") == 0)

# ---------------------------------------------------------------- her hands carry so much
L = fresh()
L.execute("""CRATE = box("crate", "garage", 1); WARD = box("wardrobe", "bedroom", 9); BOXES = { CRATE, WARD }; SOL.inv.cap = 4
LABELS = { { x = 1, y = 1, z = 0, objectIndex = 0, category = "general" } }        -- the player's drop box: emptied even when it is all one kind
for i = 1, 10 do put(CRATE, item("clothing", "Shirt" .. i)) end; SolUI.runAction("sol_sort", "run")""")
run(L, 600)
check("more than she can carry (a labelled drop box): several rounds, all moved", L.eval("#WARD.items") == 10 and L.eval("SolSort.state.stats.rounds") >= 3)
check("never over her carry limit", L.eval("SolSort.state.stats.plans") == 1 and L.eval("#SOL.inv.items") == 0)

# ---------------------------------------------------------------- the player's labels and the majority
L = fresh()
L.execute("""CRATE = box("crate", "garage", 1); MED = box("medicine", "bathroom", 12); FIRSTAID = box("crate", "garage", 30)
BOXES = { CRATE, MED, FIRSTAID }; LABELS = { { x = 30, y = 1, z = 0, objectIndex = 0, category = "medical" } }
put(CRATE, item("medicine", "Bandage")); SolUI.runAction("sol_sort", "run")""")
run(L)
check("the player's own label wins over the type (medical crate)", L.eval("names(FIRSTAID)") == "Bandage" and L.eval("#MED.items") == 0)

L = fresh()
L.execute("""CRATE = box("crate", "garage", 1); BOXR = box("smallbox", "bedroom", 40); NOTE = box("sidetable", "bedroom", 42)
BOXES = { CRATE, BOXR, NOTE }
for _, n in ipairs({ "Pliers", "Wrench", "Drill", "Spanner" }) do put(BOXR, item("tools", n)) end
put(CRATE, item("tools", "Hammer")); put(NOTE, item("tools", "Saw")); SolUI.runAction("sol_sort", "run")""")
run(L)
check("no tool cabinet: tools go to the box that is already mostly tools", L.eval("#BOXR.items") == 6 and L.eval("#CRATE.items") == 0)

L = fresh()
L.execute("""LOG = box("wardrobe", "bedroom", 1); WARD = box("wardrobe", "bedroom", 9); TOOLS = box("toolcabinet", "garage", 20)
BOXES = { LOG, WARD, TOOLS }
for _, n in ipairs({ "Pliers", "Wrench", "Drill", "Spanner", "Hammer" }) do put(LOG, item("tools", n)) end
SolUI.runAction("sol_sort", "run")""")
run(L)
check("a wardrobe the player filled with tools is left as it is", L.eval("#LOG.items") == 5 and L.eval("#TOOLS.items") == 0)

# ---------------------------------------------------------------- stop, switch, danger, unreachable
L = fresh()
L.execute(HOUSE + "SolUI.runAction('sol_sort', 'run')")
for _ in range(200):
    L.execute("TICK()")
    if L.eval("SolSort.carrying()") > 0: break
carried = L.eval("SolSort.carrying()")
r = L.eval("select(2, SolUI.runAction('sol_sort', 'stop'))")
run(L, 60)
total = L.eval("#CRATE.items + #FRIDGE.items + #COUNTER.items + #TOOLS.items + #MED.items + #WARD.items + #SHELF.items + #BCOUNT.items")
check("stop mid-way while carrying: she walks it back, nothing in her hands", carried > 0 and r == "stopping" and L.eval("#SOL.inv.items") == 0 and L.eval("SolSort.held()") is False and total == 13, (carried, r, total))
check("stop mid-way: things go back where they came from", L.eval("#CRATE.items") >= 9 and L.eval("#FLOOR") == 0)
check("stop says so", "تمام، وقّفت الترتيب." in said(L), said(L)[-2:])

L = fresh()
L.execute(HOUSE + "SolUI.runAction('sol_sort', 'run')")
for _ in range(200):
    L.execute("TICK()")
    if L.eval("SolSort.carrying()") > 0: break
L.execute("SWITCH = false; TICK()")
check("switch off mid-way: hands emptied at once, hold released", L.eval("#SOL.inv.items") == 0 and L.eval("SolSort.held()") is False)

UNREACH_SETUP = """CRATE = box("crate", "garage", 1); MED = box("medicine", "bathroom", 12); WARD = box("wardrobe", "bedroom", 15)
BOXES = { CRATE, MED, WARD }; put(CRATE, item("medicine", "Bandage")); put(CRATE, item("clothing", "Tshirt"))"""
def near12(L): return sum(1 for i in range(1, L.eval("#GOTOS") + 1) if abs(int(L.eval("GOTOS[%d]" % i).split(",")[0]) - 12) <= 1)
L = fresh()
L.execute(UNREACH_SETUP + "; UNREACHABLE[12] = true; SolUI.runAction('sol_sort', 'run')")
run(L)
check("no standing square around a container: left out of the plan, never walked to", near12(L) == 0 and L.eval("names(WARD)") == "Tshirt"
      and L.eval("names(CRATE)") == "Bandage" and L.eval("#SOL.inv.items") == 0 and L.eval("SolSort.held()") is False, near12(L))
check("...the summary names it, no 'cannot' on the way", said(L)[-1].endswith("وما قدرت أوصل لصندوق واحد.") and not any(l.startswith("ما قدرت وصل") for l in said(L)), said(L)[-1:])

L = fresh()
L.execute(UNREACH_SETUP + "; CORNER_ONLY[12] = true; SolUI.runAction('sol_sort', 'run')")
run(L)
check("sides blocked, a corner free: she uses the corner, as vanilla does", L.eval("names(MED)") == "Bandage" and L.eval("SolSort.state.visits[2].place") == 2)

L = fresh()
L.execute(UNREACH_SETUP + "; FLAKY[12] = true; SolUI.runAction('sol_sort', 'run')")
t0 = None
for i in range(400):
    L.execute("TICK()")
    if t0 is None and near12(L) > 0: t0 = L.eval("NOW")
    if not L.eval("SolSort.held()"): break
check("a container she never gets to: two orders, no re-send inside 5 s, then skipped", near12(L) == 2, (near12(L), list(L.eval("GOTOS[%d]" % i) for i in range(1, L.eval("#GOTOS") + 1))))
check("...the rest is done, what she carried for it goes home, hands empty", L.eval("names(WARD)") == "Tshirt" and L.eval("names(CRATE)") == "Bandage"
      and L.eval("#SOL.inv.items") == 0 and L.eval("SolSort.held()") is False)
check("...says it once, and the summary names it", sum(1 for l in said(L) if l == "ما قدرت وصل لخزانة الدوا، بكمّل بالباقي.") == 1
      and said(L)[-1].endswith("وما قدرت أوصل لصندوق واحد."), said(L))

L = fresh()
L.execute("""CRATE = box("crate", "garage", 1); TOOLS = box("toolcabinet", "garage", 9); T2 = box("toolcabinet", "garage", 30); BOXES = { CRATE, TOOLS, T2 }
FLAKY[9] = true; put(T2, item("tools", "Wrench")); put(TOOLS, item("tools", "Pliers")); put(CRATE, item("tools", "Hammer")); SolUI.runAction("sol_sort", "run")""")
run(L, 400)
check("a flaky destination: the next cabinet of its kind takes the item", L.eval("names(T2)") == "Hammer,Wrench" and L.eval("#SOL.inv.items") == 0)
L = fresh()
L.execute("""BOXES = {}; for i = 1, 4 do BOXES[i] = box("crate", "garage", i * 10); UNREACHABLE[i * 10] = true end
WARD = box("wardrobe", "bedroom", 60); BOXES[5] = WARD; put(BOXES[1], item("clothing", "Tshirt")); SolUI.runAction("sol_sort", "run")""")
run(L, 40)
check("all the messy ones out of reach: 'all in place' and how many boxes", said(L)[-1] == "كل شي بمحلّه، ما في شي لرتّبه. وما قدرت أوصل لـ4 صناديق.", said(L)[-1:])

L = fresh()
L.execute(HOUSE + """SolUI.runAction('sol_sort', 'run')
DANGER = false
SurvivorCompanion.GameplayUtil.peekActorState = function() if DANGER then return { snapshot = { threats = { { distanceSq = 4 } } } } end return nil end""")
for _ in range(200):
    L.execute("TICK()")
    if L.eval("SolSort.carrying()") > 0: break
L.execute("DANGER = true")
run(L, 30)
paused = L.eval("SolSort.held()") is True and L.eval("SolSort.carrying()") > 0
run(L, 200)
check("danger: she waits, then gives up and puts everything back", paused and L.eval("SolSort.held()") is False and L.eval("#SOL.inv.items") == 0, paused)

# ---------------------------------------------------------------- big home: per-tick budget
L = fresh()
L.execute("""BOXES = {}
for i = 1, 30 do local b = box(i % 3 == 0 and "wardrobe" or (i % 3 == 1 and "crate" or "toolcabinet"), i % 3 == 0 and "bedroom" or "garage", 100 + i * 2, 200)
  BOXES[#BOXES + 1] = b
  for k = 1, 20 do put(b, item(k % 2 == 0 and "clothing" or "tools", "I" .. i .. "_" .. k, nil, nil, 0.2)) end end
SolUI.runAction("sol_sort", "run")""")
ticks = 0
while L.eval("SolSort.held()") and ticks < 3000:
    L.execute("TICK()"); ticks += 1
check("600 items in 30 containers: done", L.eval("SolSort.held()") is False, ticks)
check("budget: <= 4 containers read, <= 40 classified, <= 60 planned, <= 4 moved per tick",
      L.eval("SolSort.state.stats.max.scan") <= 4 and L.eval("SolSort.state.stats.max.items") <= 40 and L.eval("MAXCLS") <= 40
      and L.eval("SolSort.state.stats.max.plan") <= 60 and L.eval("SolSort.state.stats.max.moves") <= 4,
      [L.eval("SolSort.state.stats.max." + k) for k in ("scan", "items", "plan", "moves")])
ward = L.eval("(function() local n = 0 for _, b in ipairs(BOXES) do if b.kind == 'wardrobe' then for _, it in ipairs(b.items) do if it.cat ~= 'clothing' then n = n + 1 end end end end return n end)()")
check("big home: one order moves at most 300 (100 tools stay in wardrobes), plan once", ward == 100 - 70 and L.eval("SolSort.state.moved") == 300
      and L.eval("SolSort.state.stats.plans") == 1, (ward, L.eval("SolSort.state.moved")))
check("big home: the summary says how many are left for next time", "وبعد في 100 غرض، قلّي إذا بدّك كمّل." in said(L)[-1], said(L)[-1:])
nv = L.eval("#SolSort.state.visits")
check("big home: visits stay within rounds x containers", nv <= 30 * L.eval("SolSort.state.stats.rounds"), (nv, L.eval("SolSort.state.stats.rounds")))

# ---------------------------------------------------------------- no scan, nothing to do
L = fresh()
L.execute("SAVED = SolUI.invLast; SolUI.invLast = function() return nil end; STARTED = false; SolUI.invStart = function() STARTED = true end; ok, why = SolUI.runAction('sol_sort', 'run')")
check("no home scan yet: accepted, asks for one and waits", L.eval("ok") is True and L.eval("why") == "scanning_home" and L.eval("STARTED") is True)
L.execute(HOUSE + "SolUI.invLast = SAVED"); run(L)
check("...then sorts once the scan is there", L.eval("names(FRIDGE)") == "Steak" and L.eval("SolSort.held()") is False)
L = fresh()
L.execute("""COUNTER = box("counter", "kitchen", 6); BOXES = { COUNTER }; put(COUNTER, item("food", "Beans", 1000000000)); SolUI.runAction("sol_sort", "run")""")
run(L, 20)
check("all in place: says so and stops", said(L)[-1] == "كل شي بمحلّه، ما في شي لرتّبه." and L.eval("SolSort.held()") is False)
L = fresh()
L.execute("BOXES = {}; SolUI.runAction('sol_sort', 'run'); r = select(2, SolUI.runAction('sol_sort', 'stop'))")
check("stop with nothing in hand", L.eval("SolSort.held()") is False and L.eval("r") == "stopped")
check("the lines are ASCII escapes only (SolSpeechAR rule)", all(ord(c) < 128 for c in open(os.path.join(HERE, "SolSort.lua"), encoding="ascii").read()))

# ---------------------------------------------------------------- installer and the Mind, on copies
T = tempfile.mkdtemp(prefix="sol_sort_")
cl, mind = os.path.join(T, "1", "2", "3", "4", "5", "6", "client"), os.path.join(T, "mind")
os.makedirs(cl); os.makedirs(mind); os.makedirs(os.path.join(T, "1", "Lua"))
LAB = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid"
shutil.copy(LAB + r"\mods\Sol_LAB\42\media\lua\client\SolAuthority.lua", cl)          # read only: copied, never written
shutil.copy(LAB + r"\Lua\SolFixes_LAB.txt", os.path.join(T, "1", "Lua"))
for f in glob.glob(r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind\*.py"): shutil.copy(f, mind)
def apply(name, *args): return subprocess.run([sys.executable, os.path.join(HERE, name)] + list(args), capture_output=True, text=True)
auth0 = open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read()
r1, r2, r3 = apply("apply_s66_mind.py", mind), apply("apply_s67.py", cl, mind), apply("apply_s67.py", cl, mind)
check("installer runs, twice, on copies of the lab (which already has v0.1)", r1.returncode == 0 and r2.returncode == 0 and r3.returncode == 0, (r1.stderr[-300:], r2.stderr[-300:], r3.stderr[-300:]))
auth1 = open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read()
check("switch item_sort kept once, hold once", auth1.count('"item_sort"') == 1 and auth1.count("SolUI.solSortHeld") == auth0.count("SolUI.solSortHeld") == 2 and auth0 == auth1)
check("v0.2.2 installed in the copy", 'M.VERSION = "0.2.2"' in open(os.path.join(cl, "SolSort.lua"), encoding="ascii").read())
check("item_sort=on once", open(os.path.join(T, "1", "Lua", "SolFixes_LAB.txt"), encoding="utf-8").read().count("item_sort=") == 1)
code = r"""
import sys; sys.path.insert(0, sys.argv[1]); import chat_service as CS, farm_talk as FT, model_router as MR, intent_engine as IE
cases = {"رتبي الاغراض": ("sol_sort", "run"), "رتّبي الأغراض": ("sol_sort", "run"), "رتبيلي الاغراض": ("sol_sort", "run"),
         "نظميلي الخزانات": ("sol_sort", "run"), "رتبي الاشياء": ("sol_sort", "run"), "حطي كل شي بمحله": ("sol_sort", "run"),
         "رجعي كل شي لمكانه": ("sol_sort", "run"), "وقفي الترتيب": ("sol_sort", "stop"), "وقّفي الترتيب": ("sol_sort", "stop"),
         "بكفي ترتيب": ("sol_sort", "stop"), "اهتمي بالدجاج": None, "رتبي السيارة": None, "صفي السيارة": None}
for t, want in cases.items():
    got = [x for x in CS.action_intents(CS._shami(t)) if x[0] == "sol_sort"]
    ok = (got[:1] == [want]) if want else got == []
    if want and FT.order(t) is not None: ok = False
    g = IE.parse_high_confidence(t)
    if want and g is not None and "unload" in str(g): ok = False
    print(("OK " if ok else "BAD ") + t, got, g and g.get("intent"))
g = IE.parse_high_confidence("روحي فضي الاغراض بالبيت وارجعي")
print("ERRAND", g is not None and "unload" in str(g))
print("CARD", all(k in MR.COMMANDS for k in ("sort_items", "sort_stop")) and sum(1 for k in MR.COMMANDS if k.startswith("sort")) == 2)
"""
r4 = subprocess.run([sys.executable, "-c", code, mind], capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("Mind: sort words and synonyms map to sol_sort, nothing else catches them", r4.returncode == 0 and "BAD" not in r4.stdout and r4.stdout.count("OK ") == 13, r4.stdout + r4.stderr[-600:])
check("Mind: the errand phrase is still the errand", "ERRAND True" in r4.stdout)
check("Mind: card actions unchanged (sort_items, sort_stop, no new one)", "CARD True" in r4.stdout)
shutil.rmtree(T, ignore_errors=True)
print("RESULT", ok_n, "/", ok_n + bad)
sys.exit(1 if bad else 0)

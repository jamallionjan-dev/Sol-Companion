"""Offline tests for animal_care: the Lua runner on stub game objects, and the Mind's words on copies. usage: python test_animals.py"""
import glob, os, shutil, subprocess, sys, tempfile
from lupa import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
ok_n = bad = 0
def check(name, ok):
    global ok_n, bad
    print(("PASS " if ok else "FAIL ") + name); ok_n += bool(ok); bad += (not ok)

STUBS = r"""
NOW = 0
function getTimestampMs() return NOW end
SolAuthority = { on = function(n) return n == "animal_care" end }
local function jlist(t) return { size = function() return #t end, get = function(_, i) return t[i + 1] end } end
JL = jlist
function sq(x, y) return { getX = function() return x end, getY = function() return y end, getZ = function() return 0 end } end
-- Sol
SOL = { x = 0, y = 0, inv = { items = {} } }
function SOL.inv:getItems() return jlist(self.items) end
function SOL.inv:AddItem(it) self.items[#self.items + 1] = it; it.cont = self end
function SOL:getInventory() return self.inv end
function SOL:getX() return self.x end function SOL:getY() return self.y end function SOL:getZ() return 0 end
SolUI = { solActor = function() return SOL end, runAction = function() return false, "base" end }
SolUI.solGoto = function(x, y, z) SOL.x, SOL.y = x, y; return true end
SurvivorCompanion = { Navigation = { interactionTargets = function(a, s) return { s } end },
  GameplayUtil = { transferItemVerified = function(from, to, item)
      for i, it in ipairs(from.items) do if it == item then table.remove(from.items, i); to.items[#to.items + 1] = item; item.cont = to; return true end end
      return false end,
    gridSquare = function(x, y) return sq(x, y) end } }
-- a water vessel and a feed bag in a home crate
Fluid = { Water = "water" }
function vessel(n) local fc = { amt = n }
  function fc:isEmpty() return self.amt <= 0 end
  function fc:contains(f) return f == "water" end
  function fc:getPrimaryFluidAmount() return self.amt end
  function fc:removeFluid(x) self.amt = self.amt - x end
  return { fc = fc, getFluidContainer = function(s) return s.fc end, getFullType = function() return "Base.Bucket" end, getContainer = function(s) return s.cont end } end
function feed() return { getAnimalFeedType = function() return "AnimalFeed" end, getFullType = function() return "Base.AnimalFeedBag" end, getContainer = function(s) return s.cont end } end
CRATE = { items = {} } function CRATE:getItems() return jlist(self.items) end
FRIDGE = { items = {} } function FRIDGE:getItems() return jlist(self.items) end
function FRIDGE:isPowered() return POWER end function FRIDGE:hasRoomFor() return true end
POWER = true
local places = { { x = 5, y = 5, z = 0, oi = 0, ci = 0, kind = "crate", cont = CRATE }, { x = 9, y = 9, z = 0, oi = 0, ci = 0, kind = "fridge", room = "kitchen", cont = FRIDGE } }
SolUI.invLast = function() return { places = places } end
getCell = function() return { getGridSquare = function(_, x, y) for _, p in ipairs(places) do if p.x == x and p.y == y then
    return { getX = function() return x end, getY = function() return y end, getZ = function() return 0 end,
      getObjects = function() return jlist({ { getContainerByIndex = function() return p.cont end } }) end } end end
    return sq(x, y) end } end
SurvivorCompanion.GameplayUtil.gridSquare = function(x, y) return getCell():getGridSquare(x, y) end
-- troughs and a hutch
function trough(x, water, maxW, feedAmt, maxF, foodItems)
  local t = { x = x, water = water, maxW = maxW, feed = feedAmt, maxF = maxF, cont = { items = {} } }
  for i = 1, foodItems do t.cont.items[i] = {} end
  function t.cont:getItems() return jlist(self.items) end
  function t:getWater() return self.water end function t:getMaxWater() return self.maxW end
  function t:getCurrentFeedAmount() return self.feed end function t:getMaxFeed() return self.maxF end
  function t:getContainer() return self.cont end
  function t:onFoodAdded() self.feed = self.feed + 10 * #self.cont.items end
  function t:getX() return self.x end function t:getY() return 1 end function t:getZ() return 0 end
  function t:getSquare() return sq(self.x, 1) end
  return t end
function egg(fert) return { fert = fert, isFertilized = function(s) return s.fert end, getContainer = function(s) return s.cont end } end
function hutch(eggs)
  local box = { eggs = eggs }
  function box:getEggsNb() return #self.eggs end
  function box:getEgg(i) return self.eggs[i + 1] end
  function box:removeEgg(i) return table.remove(self.eggs, i + 1) end
  local h = { box = box }
  function h:getMaxNestBox() return 1 end function h:getNestBox(i) return self.box end
  function h:getEntrySq() return sq(20, 20) end function h:sync() end
  function h:getX() return 20 end function h:getY() return 20 end
  return h end
SFeedingTroughSystem = { instance = { getLuaObjectAt = function(_, x) for _, t in ipairs(TROUGHS) do if t.x == x then
  return { addWater = function(_, n) t.water = math.min(t.maxW, t.water + n) end } end end end } }
function zone(troughs, hutches) return { getTroughsConnected = function() return jlist(troughs) end, getHutchsConnected = function() return jlist(hutches) end } end
DesignationZoneAnimal = { getZone = function() return ZONE end }
"""

def fresh():
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(STUBS)
    L.execute(open(os.path.join(HERE, "SolAnimalCare.lua"), encoding="utf-8").read())
    L.execute("SolAnimalCare.install()")
    return L

def run(L, n=60):
    L.execute("for i = 1, %d do NOW = NOW + 600; SolAnimalCare.tick() end" % n)

# rules
L = fresh()
check("empty trough and no water trough yet: water", L.eval("SolAnimalCare.troughNeed({water=0,maxWater=40,feed=0,maxFeed=20,foodItems=0}, false)") == "water")
check("empty trough when the zone already has water: feed", L.eval("SolAnimalCare.troughNeed({water=0,maxWater=40,feed=0,maxFeed=20,foodItems=0}, true)") == "feed")
check("a trough with food is never watered (it would wipe the food)", L.eval("SolAnimalCare.troughNeed({water=0,maxWater=40,feed=2,maxFeed=20,foodItems=1}, false)") == "feed")
check("a full water trough: nothing", L.eval("SolAnimalCare.troughNeed({water=30,maxWater=40,feed=0,maxFeed=20,foodItems=0}, false)") is None)

# a whole round: one water trough low, one food trough low, eggs (one fertilized)
L = fresh()
L.execute("""
TROUGHS = { trough(2, 5, 40, 0, 20, 0), trough(3, 0, 40, 2, 20, 1) }
CRATE.items = { vessel(30), feed() } ; for _, it in ipairs(CRATE.items) do it.cont = CRATE end
H = hutch({ egg(false), egg(true), egg(false) })
ZONE = zone(TROUGHS, { H })
ok, why = SolUI.runAction("sol_animals", "care")
""")
check("order accepted", L.eval("ok") is True)
run(L, 120)
check("water trough topped up from the crate's bucket", L.eval("TROUGHS[1].water") > 5 and L.eval("CRATE.items[1] == nil or CRATE.items[1].getAnimalFeedType ~= nil"))
check("food trough fed from the feed bag (counted by the trough)", L.eval("TROUGHS[2].feed") > 2)
check("two eggs taken, the fertilized one left for the hen", L.eval("#H.box.eggs") == 1 and L.eval("H.box.eggs[1].fert") is True)
check("eggs put in the powered kitchen fridge", L.eval("#FRIDGE.items") == 2)
check("job finished, hold released", L.eval("SolAnimalCare.held()") is False)
st = L.eval("select(2, SolUI.runAction('sol_animals', 'status'))")
check("status counts the work", "water=1" in st and "feed=1" in st and "eggs=1" in st)

# no power: eggs stay with her, never in a dead fridge
L = fresh()
L.execute("POWER = false; TROUGHS = {}; H = hutch({ egg(false) }); ZONE = zone(TROUGHS, { H }); FRIDGE.items = {}; SolUI.runAction('sol_animals', 'eggs')")
run(L, 40)
check("fridge without power: eggs kept on her", L.eval("#FRIDGE.items") == 0 and L.eval("#SOL.inv.items") == 1)

# nothing to feed with
L = fresh()
L.execute("TROUGHS = { trough(3, 0, 40, 2, 20, 1) }; CRATE.items = {}; ZONE = zone(TROUGHS, {}); SolUI.runAction('sol_animals', 'care')")
run(L, 10)
check("no feed anywhere: fails cleanly and says why", "no_animal_feed" in str(L.eval("SolAnimalCare.state.last.text")))

# no zone
L = fresh()
L.execute("ZONE = nil; ok, why = SolUI.runAction('sol_animals', 'care')")
check("no animal zone: refused with the reason", L.eval("ok") is False and L.eval("why") == "no_animal_zone")

# stop and other verbs pass through
L = fresh()
L.execute("TROUGHS = { trough(2, 5, 40, 0, 20, 0) }; CRATE.items = { vessel(30) }; CRATE.items[1].cont = CRATE; ZONE = zone(TROUGHS, {}); SolUI.runAction('sol_animals', 'care'); SolUI.runAction('sol_animals', 'stop')")
check("stop ends the job and the keeper", L.eval("SolAnimalCare.held()") is False and L.eval("SolAnimalCare.state.keeper") is False)
check("other verbs untouched", L.eval("select(2, SolUI.runAction('sol_farm', 'x'))") == "base")

# the Mind's words, on copies
T = tempfile.mkdtemp(prefix="sol_anim_")
cl, mind = os.path.join(T, "1", "2", "3", "4", "5", "6", "client"), os.path.join(T, "mind")
os.makedirs(cl); os.makedirs(mind); os.makedirs(os.path.join(T, "1", "Lua"))
LAB = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid"
shutil.copy(LAB + r"\mods\Sol_LAB\42\media\lua\client\SolAuthority.lua", cl)
shutil.copy(LAB + r"\Lua\SolFixes_LAB.txt", os.path.join(T, "1", "Lua"))
for f in glob.glob(r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind\*.py"): shutil.copy(f, mind)
r = subprocess.run([sys.executable, os.path.join(HERE, "apply_s60.py"), cl, mind], capture_output=True, text=True)
check("installer runs on copies", r.returncode == 0 and "applied" in r.stdout)
r2 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s60.py"), cl, mind], capture_output=True, text=True)
check("installer is safe to run twice", r2.returncode == 0)
R = lua51.LuaRuntime()
check("SolAuthority still compiles", not isinstance(R.eval("loadstring")(open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read()), tuple))
code = r"""
import sys; sys.path.insert(0, sys.argv[1]); import chat_service as CS, farm_talk as FT, model_router as MR
cases = {"اهتمي بالدجاج": ("sol_animals", "care"), "اجمعي البيض": ("sol_animals", "eggs"), "وقفي شغل الدجاج": ("sol_animals", "stop"),
         "طعمي الدجاج": ("sol_animals", "care"), "اهتمي بالمزرعة": None, "اسقي الزرع": None}
for t, want in cases.items():
    got = [x for x in CS.action_intents(CS._shami(t)) if x[0] == "sol_animals"]
    farm = FT.order(t)
    ok = (got[:1] == [want]) if want else (got == [])
    if want and farm is not None: ok = False
    print(("OK " if ok else "BAD ") + t, got, farm)
print("CARD", all(k in MR.COMMANDS for k in ("animal_care", "eggs", "animal_stop")))
"""
r3 = subprocess.run([sys.executable, "-c", code, mind], capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
out = r3.stdout
check("Mind: chicken orders map to sol_animals and never to the farm; farm orders untouched", r3.returncode == 0 and "BAD" not in out and out.count("OK ") == 6)
check("Mind: model card lines present", "CARD True" in out)
if "BAD" in out or r3.returncode: print(out, r3.stderr[-800:])
print("RESULT", ok_n, "/", ok_n + bad)
sys.exit(1 if bad else 0)

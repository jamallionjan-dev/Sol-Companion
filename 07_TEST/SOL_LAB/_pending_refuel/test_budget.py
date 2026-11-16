"""The shared per-frame allowance, and the world scan spread over frames, on the real files with the game stubbed."""
import os, shutil, subprocess, sys, tempfile, json
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
CL = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\lua\client"
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
BASE = r"""
NOW = 1000
function getTimestampMs() return NOW end
TICK = nil
Events = { OnTick = { Add = function(f) TICK = f end } }
print = function() end
"""
def budget():
    L = lua51.LuaRuntime(unpack_returned_tuples=True); L.execute(BASE)
    L.execute(open(os.path.join(HERE, "SolBudget.lua"), encoding="utf-8").read())
    return L
L = budget(); g = L.globals()
L.execute(r"""
RAN = {}
function task(name, costMs) return function(left) RAN[#RAN + 1] = name; LEFT = left; NOW = NOW + math.min(costMs, left) end end
SolBudget.register("slow", task("slow", 5), { everyMs = 0, priority = 5 })
SolBudget.register("first", task("first", 0), { everyMs = 0, priority = 1 })
SolBudget.register("last", task("last", 0), { everyMs = 0, priority = 9 })
""")
def ran(): return [g.RAN[i] for i in range(1, len(list(g.RAN.values())) + 1)]
L.execute("RAN = {}"); g.TICK(); ck("priority first and shared allowance stops at two ms", ran() == ["first", "slow"] and g.NOW == 1002, (ran(), g.NOW))
L.execute("RAN = {}"); g.NOW = g.NOW + 16; g.TICK(); ck("next frame starts with the highest current priority", ran()[:2] == ["first", "slow"], ran())
L.execute('RAN = {}; SEEN = 0; local f = task("last", 0); SolBudget.register("last", function(l) SEEN = SEEN + 1; f(l) end, { everyMs = 0, priority = 9 })')
for i in range(400): g.NOW = g.NOW + 16; g.TICK()
ck("aged due work eventually runs without budget bypass", g.SEEN >= 2, g.SEEN)
L = budget(); g = L.globals()
L.execute('N = 0; SolBudget.register("timed", function() N = N + 1 end, { everyMs = 1000 })')
for i in range(100): g.NOW = g.NOW + 100; g.TICK()
ck("a timed task runs on its interval", 9 <= g.N <= 11, g.N)
L = budget(); g = L.globals()
L.execute('SolBudget.register("bad", function() error("x") end, {}); SolBudget.register("good", function() OK = true end, {})'); g.TICK(); ck("one failing task does not stop the others", g.OK is True)
L = budget(); g = L.globals()
L.execute('COUNT = 0; SolBudget.register("x", function() COUNT = COUNT + 1 end, {}); SolBudget.register("x", function() COUNT = COUNT + 10 end, {})'); g.TICK(); ck("registering twice replaces", g.COUNT == 10, g.COUNT)

# the world scan, sliced
src = os.path.join(CL, "SolWorldScan.lua")
tmp = tempfile.mkdtemp(prefix="sol_budget_")
needed = ["SolWorldScan.lua", "SolSkills.lua", "SolDress.lua", "SolLife.lua"]
for n in needed: shutil.copy(os.path.join(CL, n) if n != "SolLife.lua" else os.path.join(HERE, "SolLife.lua"), tmp)
if "SolBudget.register" not in open(os.path.join(tmp, "SolWorldScan.lua"), encoding="utf-8").read():
    shutil.copy(os.path.join(HERE, "SolDress.lua"), tmp)
    subprocess.check_call([sys.executable, os.path.join(HERE, "apply_s13_lua.py")] + [os.path.join(tmp, n) for n in needed], stdout=subprocess.DEVNULL)
L = lua51.LuaRuntime(unpack_returned_tuples=True); L.execute(BASE)
L.execute(open(os.path.join(HERE, "SolBudget.lua"), encoding="utf-8").read())
L.execute(r"""
require = function() end
SolText = {}
GRID = {}
PLANTS = { ["5,5,0"] = true, ["-3,2,0"] = true, ["10,-9,1"] = true, ["15,15,-1"] = true }
READS = 0
OBJS = { size = function() return 0 end, get = function() end }
function square(x, y, z) return { x = x, y = y, z = z, getObjects = function() READS = READS + 1; NOW = NOW + 0.02; return OBJS end, getRoom = function() end, getMovingObjects = function() return OBJS end } end
CELL = { getGridSquare = function(_, x, y, z) return square(x, y, z) end, getVehicles = function() return OBJS end }
function getCell() return CELL end
PLAYER = { getX = function() return 0 end, getY = function() return 0 end, getZ = function() return 0 end, getInventory = function() return nil end, getStats = function() return nil end }
function getSpecificPlayer() return PLAYER end
CFarmingSystem = { instance = { getLuaObjectOnSquare = function(_, sq) local k = sq.x .. "," .. sq.y .. "," .. sq.z; if PLANTS[k] then return { typeOfSeed = k, waterLvl = 1, nbOfGrow = 1, state = "seeded", health = 9 } end return nil end } }
WRITTEN = nil
function getFileWriter() return { write = function(_, t) WRITTEN = t end, close = function() end } end
SolUI = {}
SolAuthority = { on = function(name) return name == "perf_slice" end }
SolScanCoordinator = {
  tryAcquire = function() return true, 1 end,
  owns = function() return true end,
  release = function() return true end
}
require = function(name) if name == "SolScanCoordinator" then return SolScanCoordinator end end
""")
L.execute(open(os.path.join(tmp, "SolWorldScan.lua"), encoding="utf-8").read())
g = L.globals()
sync = L.eval("SolUI.scanWorld()")
keys = lambda snap: sorted(snap.plants[i].seed for i in range(1, len(list(snap.plants.values())) + 1))
want = sorted(["5,5,0", "-3,2,0", "10,-9,1", "15,15,-1"]); ck("all at once: every plant", keys(sync) == want, keys(sync))
total_reads = g.READS
L.execute("READS = 0; WRITTEN = nil")
frames = 0; biggest = 0
g.NOW = g.NOW + 70000
for frames in range(1, 2000):
    before = g.READS; g.NOW = g.NOW + 16; g.TICK(); biggest = max(biggest, g.READS - before)
    if g.WRITTEN: break
snap = json.loads(g.WRITTEN)
ck("spread over frames: the same plants", sorted(p["seed"] for p in snap["plants"]) == want, [p["seed"] for p in snap["plants"]])
ck("spread over frames: every square once, as before", g.READS == total_reads, (g.READS, total_reads))
print("     all at once %d squares in one frame; sliced: at most %d squares in a frame, over %d frames" % (total_reads, biggest, frames))
ck("no frame reads more than a tenth of the squares", biggest * 10 <= total_reads, (biggest, total_reads))
L.execute("WRITTEN = nil"); L.eval("SolUI.scanNow()"); ck("asking for it now still gives it now", g.WRITTEN is not None)
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)

"""s99 perf_slice offline: SolWorldScan.lua, SolInventory.lua and SolActions.lua (patched on a temporary copy, and the lab originals
for reference) under the game's Lua rules (kahlua_env), on a synthetic world: squares with containers, nested bags, food, fluids,
water sources, plants, animals, unloaded squares; cars with part containers; Living Fellows pages for the action catalog.
A fake clock: every game-object call costs JCOST ms, every tostring TSCOST ms, a Living Fellows page PAGE_MS ms, a frame 16 ms.
Checks:
  - sliced output == one-shot output (world snapshot JSON, base inventory model, action catalog JSON);
  - switch off == the unpatched lab code, byte for byte / field for field, and still one call per scan / catalog;
  - no slice longer than its budget plus one unit; the old paths' worst frame for comparison;
  - jsonEncodeJob == encode byte for byte (nested, depth cut, non-ASCII, empty tables), under any budget;
  - switched off half way: the rest finishes at once, same output;
  - installer idempotent, switch listed once, SolFixes_LAB line once; tonumber gate; ASCII.
Run: python test_s99_perf_slice.py [candidate client dir] [pre-merge baseline client dir]. Offline PASS is not Runtime PASS."""
import json, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)[:600]) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
BASE = sys.argv[2] if len(sys.argv) > 2 else CL
FILES = ("SolWorldScan.lua", "SolInventory.lua", "SolActions.lua", "SolAuthority.lua")
tmp = tempfile.mkdtemp(prefix="s99_")
cl = os.path.join(tmp, "a", "b", "c", "d", "e", "client"); os.makedirs(cl)
os.makedirs(os.path.join(tmp, "Lua"))
fixfile = os.path.join(tmp, "Lua", "SolFixes_LAB.txt")
open(fixfile, "w", newline="").write("gear_recover=on\r\n")
for f in FILES: shutil.copy(os.path.join(CL, f), cl)

# ---------------------------------------------------------------- installer
integrated_s112 = os.path.isfile(os.path.join(CL, "SolScanCoordinator.lua")) and "local SolScanCoordinator = require \"SolScanCoordinator\"" in open(os.path.join(CL, "SolWorldScan.lua"), encoding="utf-8").read()
if integrated_s112:
    auth0 = open(os.path.join(CL, "SolAuthority.lua"), encoding="utf-8").read()
    ok_markers = all(x in auth0 for x in ('"perf_slice"', '"task_scoped_perception"'))
    ok_files = all("SolScanCoordinator" in open(os.path.join(CL, f), encoding="utf-8").read()
                   for f in ("SolWorldScan.lua", "SolInventory.lua", "SolBaseScan.lua", "SolOrders.lua"))
    ck("candidate already contains the integrated s99+s112 scan implementation", ok_markers and ok_files)
    with open(fixfile, "a", encoding="utf-8", newline="") as h: h.write("perf_slice=on\r\n")
else:
    for i in (1, 2):
        r = subprocess.run([sys.executable, os.path.join(HERE, "apply_s99_perf_slice.py"), cl], capture_output=True, text=True)
        ck("installer run %d" % i, r.returncode == 0 and (i == 1 or (r.stdout.count("kept") == 4 and "edited" not in r.stdout)), r.stdout + r.stderr)
A = open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8", newline="").read()
ck("switch listed once in A.FIXES", A.count('"perf_slice"') == 1)
ck("SolFixes_LAB.txt: perf_slice=on once", open(fixfile).read().count("perf_slice=on") == 1, open(fixfile).read())
for f in FILES[:3]:
    t = open(os.path.join(cl, f), encoding="utf-8", newline="").read()
    o = open(os.path.join(CL, f), encoding="utf-8", newline="").read()
    ck("line endings kept: " + f, ("\r\n" in t) == ("\r\n" in o))
    ck("ascii only: " + f, all(ord(c) < 128 for c in t))
for fn in sorted(os.listdir(os.path.join(HERE, "s99_perf_slice"))):
    t = open(os.path.join(HERE, "s99_perf_slice", fn), encoding="utf-8").read()
    if not all(ord(c) < 128 for c in t): ck("ascii only: fragment " + fn, False)
NEW = {f: open(os.path.join(cl, f), encoding="utf-8").read() for f in FILES[:3]}
OLD = {f: open(os.path.join(BASE, f), encoding="utf-8").read() for f in FILES[:3]}

# ---------------------------------------------------------------- the synthetic world (Lua)
ENV = r"""
NOW = 1000000
JCOST, TSCOST, PAGE_MS = 0.01, 0.002, 3
function getTimestampMs() return NOW end
local prevTs = tostring
tostring = function(v, ...) NOW = NOW + TSCOST; return prevTs(v, ...) end
RAWTS = prevTs
LOGS = {}
function print(m) LOGS[#LOGS + 1] = prevTs(m) end
SW = { perf_slice = true }
SolAuthority = { on = function(f) return SW[f] == true end }
local SCAN = { generation = 0 }
function SCAN.tryAcquire(owner, profile) SCAN.generation = SCAN.generation + 1; return true, SCAN.generation end
function SCAN.owns(owner, lease) return lease == SCAN.generation end
function SCAN.release(owner, lease, reason) if lease == SCAN.generation then return true end return false end
function require(name) if name == "SolScanCoordinator" then return SCAN end end
FILES, WRITES = {}, {}
function getFileWriter(name) local buf = {}
    return { write = function(self, s) buf[#buf + 1] = s end, close = function(self) FILES[name] = table.concat(buf); WRITES[#WRITES + 1] = name end } end
function getFileReader() return nil end
TASKS, TICKS, STARTS = {}, {}, {}
SolBudget = { register = function(name, fn, o) TASKS[name] = fn end }
Events = { OnTick = { Add = function(f) TICKS[#TICKS + 1] = f end }, OnGameStart = { Add = function(f) STARTS[#STARTS + 1] = f end } }
PERF = {}
SolUI = { perfAdd = function(name, ms) local p = PERF[name] or { n = 0, max = 0, total = 0 }; PERF[name] = p
    p.n = p.n + 1; p.total = p.total + ms; if ms > p.max then p.max = ms end end }
SolText = {}
function SolText.codepoints(s)
    NOW = NOW + 0.01
    local out, i, n = {}, 1, string.len(s)
    while i <= n do
        local c = string.byte(s, i)
        if c < 128 then out[#out + 1] = c; i = i + 1
        elseif c < 224 then out[#out + 1] = (c - 192) * 64 + (string.byte(s, i + 1) - 128); i = i + 2
        elseif c < 240 then out[#out + 1] = (c - 224) * 4096 + (string.byte(s, i + 1) - 128) * 64 + (string.byte(s, i + 2) - 128); i = i + 3
        else out[#out + 1] = 63; i = i + 4 end
    end
    return out
end
function SolText.hex4(n) return string.format("%04X", n) end
local NEXTID = 0
function J(o)             -- a game object: every method costs JCOST
    NEXTID = NEXTID + 1; o.__obj = NEXTID
    local fns = {}
    for k, f in pairs(o) do if type(f) == "function" then fns[k] = f end end
    for k, f in pairs(fns) do o[k] = function(...) NOW = NOW + JCOST; return f(...) end end
    return o
end
function LIST(t) return J({ size = function(self) return #t end, get = function(self, i) return t[i + 1] end }) end
function instanceof(o, c) return type(o) == "table" and type(o.cls) == "table" and o.cls[c] == true end
local AR = "\216\179\217\132"     -- two Arabic letters (UTF-8): the non-ASCII path of jstr
function H(x, y, z) return (x * 7919 + y * 104729 + (z + 3) * 1299709) % 1000 end
function CONT(kind, items)
    return J({ getItems = function(self) return LIST(items) end, getType = function(self) return kind end,
               haveThisKeyId = function(self, k) return false end })
end
function ITEM(h, depth)
    local k = h % 9
    local it = { cls = {} }
    it.getFullType = function(self) return "Base.Item" .. (h % 23) end
    it.getDisplayName = function(self) return (h % 5 == 0) and ("Thing " .. AR .. (h % 23)) or ("Thing " .. (h % 23)) end
    it.getDisplayCategory = function(self) return ({ "Food", "Ammo", "Weapon", "Tool", "FirstAid", "Material", "Clothing", "Literature", "Junk" })[k + 1] end
    it.getCount = function(self) return (k == 1) and (h % 30 + 1) or 1 end
    it.getConditionMax = function(self) return 10 end
    it.getCondition = function(self) return h % 11 end
    if k == 0 then
        it.cls.Food = true
        it.getHungerChange = function(self) return -((h % 20) / 100) end
        it.isRotten = function(self) return h % 4 == 0 end
        it.isFresh = function(self) return h % 4 ~= 0 end
        it.getCalories = function(self) return h % 400 + 0.5 end
        it.getAge = function(self) return (h % 7) + 0.25 end
        it.getOffAgeMax = function(self) return 8 end
        it.getOffAge = function(self) return 5 end
    end
    if k == 4 or k == 8 then
        local fl = J({ getFluidTypeString = function(self) return (h % 2 == 0) and "Water" or "Petrol" end, isPoisonous = function(self) return h % 6 == 0 end })
        it.getFluidContainer = function(self) return J({ isEmpty = function(self) return false end, getPrimaryFluid = function(self) return fl end,
                                                          getAmount = function(self) return (h % 10) / 4 end }) end
    end
    if k == 3 then it.cls.DrainableComboItem = true; it.getCurrentUsesFloat = function(self) return (h % 10) / 10 end end
    if k == 5 and depth < 6 then
        it.cls.InventoryContainer = true
        local inner = {}
        for j = 1, h % 6 do inner[#inner + 1] = ITEM((h * 31 + j * 17) % 1000, depth + 1) end
        local c = CONT("Bag", inner)
        it.getInventory = function(self) return c end
    end
    return J(it)
end
SQ = {}
function SQUARE(x, y, z)
    local key = x .. "," .. y .. "," .. z
    if SQ[key] ~= nil then return SQ[key] or nil end
    local h = H(x, y, z)
    if h % 97 == 5 then SQ[key] = false; return nil end
    local objs, movers = {}, {}
    if h % 6 == 0 then
        local items = {}
        for j = 1, h % 14 do items[#items + 1] = ITEM((h * 13 + j * 7) % 1000, 0) end
        local c = CONT((h % 2 == 0) and "crate" or "fridge", items)
        local o = { getContainerCount = function(self) return 1 end, getContainerByIndex = function(self, i) return c end,
                    getSprite = function(self) return J({ getName = function(self) return "spr_" .. (h % 17) end }) end }
        objs[#objs + 1] = J(o)
    end
    if h % 53 == 1 then
        objs[#objs + 1] = J({ isWaterSource = function(self) return true end, getFluidAmount = function(self) return 40 + h % 9 end,
                              hasWater = function(self) return true end, hasFluid = function(self) return true end,
                              isTaintedWater = function(self) return h % 2 == 0 end, getObjectName = function(self) return "Well" end })
    end
    if h % 61 == 2 then movers[#movers + 1] = J({ cls = { IsoAnimal = true }, getAnimalType = function(self) return "cow" end,
                                                  getThirst = function(self) return 0.3 end, getStats = function(self) return nil end }) end
    local room = (h % 3 == 0) and J({ getName = function(self) return "kitchen" .. AR end }) or nil
    local sq = J({ h = h, getObjects = function(self) return LIST(objs) end, getMovingObjects = function(self) return LIST(movers) end,
                   getRoom = function(self) return room end, getVehicleContainer = function(self) return nil end })
    SQ[key] = sq
    return sq
end
function getCell() return J({ getGridSquare = function(self, x, y, z) return SQUARE(x, y, z) end,
                              getVehicles = function(self) return LIST({}) end }) end
CFarmingSystem = { instance = J({ getLuaObjectOnSquare = function(self, sq)
    if sq.h % 41 == 3 then return { typeOfSeed = "Carrots", waterLvl = 50, nbOfGrow = 3, state = "seeded", health = 80, exterior = true } end
    return nil end }) }
function CAR(x, y, n)
    local parts = {}
    for p = 1, 4 do
        local items = {}
        for j = 1, (n * 3 + p) % 7 do items[#items + 1] = ITEM((n * 101 + p * 37 + j) % 1000, 0) end
        local c = (p % 2 == 1) and CONT("TruckBed", items) or nil
        parts[p] = J({ getItemContainer = function(self) return c end, getId = function(self) return "Part" .. p end })
    end
    local gas = J({ getContainerContentAmount = function(self) return 12.5 + n end, getContainerCapacity = function(self) return 60 end })
    return J({ getX = function(self) return x end, getY = function(self) return y end, getSqlId = function(self) return 500 + n end,
               getScript = function(self) return J({ getName = function(self) return "Car" .. n end }) end,
               getPartById = function(self, id) if id == "GasTank" then return gas end return nil end,
               getPartCount = function(self) return #parts end, getPartByIndex = function(self, i) return parts[i + 1] end,
               isKeysInIgnition = function(self) return n == 1 end, getKeyId = function(self) return 40 + n end })
end
CARS = { CAR(105, 98, 1), CAR(120, 110, 2), CAR(140, 141, 3), CAR(400, 400, 4) }
local function actor(x, y, inv) return J({ getX = function(self) return x end, getY = function(self) return y end, getZ = function(self) return 0 end,
    getInventory = function(self) return inv end }) end
local pitems, sitems = {}, {}
for j = 1, 12 do pitems[#pitems + 1] = ITEM((j * 77) % 1000, 0) end
for j = 1, 9 do sitems[#sitems + 1] = ITEM((j * 91 + 5) % 1000, 0) end
PLAYER = actor(100.5, 100.5, CONT("none", pitems))
SOL = actor(140.5, 140.5, CONT("none", sitems))
function getSpecificPlayer(i) return PLAYER end
SolUI.solActor = function() return SOL end
SurvivorCompanion = { Vehicle = { loadedVehicles = function() return CARS end },
    BaseLife = { active = function() return { zones = { { kind = "area", x1 = 92, x2 = 108, y1 = 94, y2 = 104, z = 0 },
                                                         { kind = "area", x1 = 105, x2 = 112, y1 = 100, y2 = 106, z = 0 },
                                                         { kind = "parking", x1 = 110, x2 = 114, y1 = 90, y2 = 92, z = 0 } } } end } }
SolLife = { snapshot = function() return { mood = "calm " .. AR, days = 3 }, { "Main St", "Elm" }, "Main St" end }
SolFarmWork = { snapshot = function() return { beds = 2, note = "ok" } end }
SolBookMemory = { snapshot = function() return { { name = "Home", x = 1, y = 2 } } end }
SandboxVars = { WaterShutModifier = 14, ElecShutModifier = 20 }
function DUMP(v)
    local t = type(v)
    if t == "table" then
        if v.__obj then return "obj" .. RAWTS(v.__obj) end
        local keys = {}
        for k in pairs(v) do keys[#keys + 1] = k end
        table.sort(keys, function(a, b) return RAWTS(a) < RAWTS(b) end)
        local parts = {}
        for _, k in ipairs(keys) do if k ~= "t" and k ~= "ms" then parts[#parts + 1] = RAWTS(k) .. "=" .. DUMP(v[k]) end end
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return RAWTS(v)
end
"""
def fresh(sources, on, pre=""):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV); L.execute(pre)
    L.execute("SW.perf_slice = %s" % ("true" if on else "false"))
    for s in sources: L.execute(s)
    return L

FRAME = 16
def drive(L, call, done, max_frames=20000, flip_at=None):
    """one call a frame; returns the list of (ms spent in the call) and the frames used"""
    spent = []
    for fr in range(max_frames):
        if flip_at is not None and fr == flip_at: L.execute("SW.perf_slice = false")
        L.execute("NOW = NOW + %d" % FRAME)
        t0 = L.eval("NOW"); call(); spent.append(L.eval("NOW") - t0)
        if done(): return spent, fr + 1
    return spent, max_frames

# ---------------------------------------------------------------- 1. jsonEncodeJob == encode
L = fresh([NEW["SolWorldScan.lua"]], True)
L.execute(r"""
local AR = "\216\179\217\132"
local function deep(n) if n == 0 then return { leaf = "x" } end return { d = deep(n - 1), n = n } end
DOC = { a = 1, b = 2.25, c = "plain", d = "q\"uote\\back" .. AR, e = true, f = false, g = {}, h = { 1, 2, 3, { x = 1 } },
        i = deep(16), j = { [1] = "a", [3] = "c" }, k = 1/0, m = 0/0, n = -0.000012345, o = 1e20, p = { { { {} } } } }
for i = 1, 300 do DOC["k" .. i] = { name = "item " .. i .. ((i % 7 == 0) and AR or ""), n = i * 1.5, list = { i, i + 1, "s" .. i } } end
""")
ref = L.eval("SolUI.jsonEncode(DOC)")
for budget in (1000000, 1, 0.05, 0):
    L.execute("JOB = SolUI.jsonEncodeJob(DOC); STEPS = 0; while not JOB.step(%r) do STEPS = STEPS + 1 end" % budget)
    ck("jsonEncodeJob == encode byte for byte (budget %r ms, %d slices)" % (budget, L.eval("STEPS") + 1), L.eval("JOB.result()") == ref)
ck("jsonEncodeJob on a plain value", L.eval("(function() local j = SolUI.jsonEncodeJob('a\"b'); j.step(1); return j.result() end)()") == L.eval("SolUI.jsonEncode('a\"b')"))
L.execute("JOB = SolUI.jsonEncodeJob(DOC); SL = {}; while true do local t0 = NOW; local d = JOB.step(4); SL[#SL + 1] = NOW - t0; if d then break end end")
sl = [L.eval("SL")[i] for i in range(1, len(L.eval("SL")) + 1)]
ck("encode slices within 4 ms + one value (fake clock: tostring %s ms, codepoints 0.01 ms)" % "0.002", max(sl) <= 4.1, (max(sl), len(sl)))

# ---------------------------------------------------------------- 2. world scan
def world_run(src, on, flip_at=None, remaining=4):
    L = fresh([src], on, pre="SolUI.invCompact = function() return { rows = { { w = 'house', t = 'Base.Can', k = 3 } }, food = { cal = 10 } } end;"
                               "SolUI.invCovers = function(c) return c.where == 'square' and (c.x or 0) < 95 end")
    spent, frames = drive(L, lambda: L.eval("TASKS.world_scan(%r)" % remaining), lambda: L.eval("FILES['SolWorld_Snapshot.txt'] ~= nil"), flip_at=flip_at)
    return L, spent, frames
Lref, sp_ref, fr_ref = world_run(OLD["SolWorldScan.lua"], False)
Loff, sp_off, fr_off = world_run(NEW["SolWorldScan.lua"], False)
Lon, sp_on, fr_on = world_run(NEW["SolWorldScan.lua"], True)
Lflip, sp_flip, _ = world_run(NEW["SolWorldScan.lua"], True, flip_at=8)
txt_ref, txt_off, txt_on, txt_flip = (x.eval("FILES['SolWorld_Snapshot.txt']") for x in (Lref, Loff, Lon, Lflip))
snap = json.loads(txt_ref)
ck("synthetic world is not trivial (containers, foods, fluids, plants, animals, water, cars, two windows, solVehicles)",
   len(snap["containers"]) > 40 and len(snap["plants"]) > 0 and len(snap["animals"]) > 0 and len(snap["waterSources"]) > 0
   and len(snap["vehicles"]) >= 2 and len(snap.get("solVehicles", [])) >= 1 and snap["coverage"]["windows"] == 2
   and any(c.get("foods") for c in snap["containers"]) and any(c.get("fluids") for c in snap["containers"]),
   {k: (len(v) if isinstance(v, list) else v) for k, v in snap.items() if k in ("containers", "plants", "animals", "waterSources", "vehicles", "solVehicles", "coverage")})
ck("world: switch off == unpatched lab code, byte for byte", txt_off == txt_ref)
ck("world: switch off still one perfAdd for the whole scan (old behaviour)", Loff.eval("PERF.world_scan.n") == 1 and Lref.eval("PERF.world_scan.n") == 1)
ck("world: sliced snapshot == one-shot snapshot (parsed JSON)", json.loads(txt_on) == json.loads(txt_ref))
print("     byte-identical too: %s" % (txt_on == txt_ref))
ck("world: switched off half way -> finished at once, same snapshot", json.loads(txt_flip) == json.loads(txt_ref))
Lu = fresh([NEW["SolWorldScan.lua"]], True)
Lu.execute("""UNIT = 0; local job = SolUI._scanJob()
  while true do local t0 = NOW; local d = job.step(0, true); UNIT = math.max(UNIT, NOW - t0); if d then break end end
  while true do local t0 = NOW; local d = job.finishStep(0); UNIT = math.max(UNIT, NOW - t0); if d then break end end""")
WUNIT = Lu.eval("UNIT")
print("     world: heaviest single unit (one square or one car) on this world: %.2f ms" % WUNIT)
ck("world: sliced worst frame <= 4 ms + one unit (%.2f ms over %d frames; one-shot worst frame %.2f ms)" % (max(sp_on), fr_on, max(sp_ref)),
   max(sp_on) <= 4 + WUNIT + 0.01, max(sp_on))
ck("world: the old worst frame is the finish + write frame and is far over budget (the spike this removes)", max(sp_ref) > 8, max(sp_ref))
ck("world: perfAdd once a frame when sliced (max == worst frame)", Lon.eval("PERF.world_scan.n") == fr_on and abs(Lon.eval("PERF.world_scan.max") - max(sp_on)) < 1e-6)
ck("world: done well inside the 60 s interval (%d frames = %.1f s at 16 ms)" % (fr_on, fr_on * FRAME / 1000.0), fr_on * FRAME < 60000)
spn, frn = drive(Lon, lambda: Lon.eval("TASKS.world_scan(4)"), lambda: False, max_frames=50)
ck("world: no new scan before the interval", Lon.eval("#WRITES") == 1)
ck("world: radius tuning count unchanged (lastWorldScanMs comparable)", Lon.eval("SolUI.lastWorldScanMs") is not None)
L2, sp2, fr2 = world_run(NEW["SolWorldScan.lua"], True, remaining=2)
ck("world: SolBudget's 2 ms allowance is respected (worst %.2f ms)" % max(sp2), max(sp2) <= 2 + WUNIT + 0.01 and json.loads(L2.eval("FILES['SolWorld_Snapshot.txt']")) == json.loads(txt_ref))
Ls = fresh([NEW["SolWorldScan.lua"]], True)
ck("world: U.scanNow still writes at once (chat path)", Ls.eval("SolUI.scanNow()") is True and Ls.eval("FILES['SolWorld_Snapshot.txt'] ~= nil"))

# ---------------------------------------------------------------- 3. base inventory
def inv_run(src, on, flip_at=None, remaining=4):
    L = fresh([src], on, pre="SolUI.invFarmTag = function(it, ty) if ty == 'Base.Item3' then return { seed = true } end return nil end")
    L.execute("for _, f in ipairs(STARTS) do f() end")
    spent, frames = drive(L, lambda: L.eval("TASKS.inventory(%r)" % remaining), lambda: L.eval("SolUI.invLast() ~= nil"), flip_at=flip_at)
    return L, spent, frames
Iref, ip_ref, ifr_ref = inv_run(OLD["SolInventory.lua"], False)
Ioff, ip_off, _ = inv_run(NEW["SolInventory.lua"], False)
Ion, ip_on, ifr_on = inv_run(NEW["SolInventory.lua"], True)
Iflip, _, _ = inv_run(NEW["SolInventory.lua"], True, flip_at=40)
d_ref, d_off, d_on, d_flip = (x.eval("DUMP(SolUI.invLast())") for x in (Iref, Ioff, Ion, Iflip))
m = Iref.eval("SolUI.invLast()")
ck("inventory world is not trivial", m["items"] > 200 and m["conts"] > 30 and m["vehicles"] >= 1 and m["unloaded"] > 0 and len(m["rows"]) > 20 and len(m["farm"]) > 0,
   (m["items"], m["conts"], m["vehicles"], m["unloaded"], len(m["rows"])))
ck("inventory: switch off == unpatched lab code (every field)", d_off == d_ref)
ck("inventory: sliced model == one-shot model (every field)", d_on == d_ref, (len(d_on), len(d_ref)))
ck("inventory: switched off half way -> same model", d_flip == d_ref)
ck("inventory: sliced worst frame <= 4 ms + one unit (%.2f ms over %d frames; old worst %.2f ms)" % (max(ip_on), ifr_on, max(ip_ref)), max(ip_on) <= 4 + 1.0, max(ip_on))
ck("inventory: old worst frame over budget on the same world (the spike this removes)", max(ip_ref) > 6, max(ip_ref))
ck("inventory: done well inside the 2 min interval (%d frames)" % ifr_on, ifr_on * FRAME < 120000)
I2, ip2, _ = inv_run(NEW["SolInventory.lua"], True, remaining=2)
ck("inventory: SolBudget's 2 ms allowance (worst %.2f ms)" % max(ip2), max(ip2) <= 2 + 1.0 and I2.eval("DUMP(SolUI.invLast())") == d_ref)
ck("inventory: invLast stays the previous scan while a new one runs",
   Ion.eval("(function() local a = SolUI.invLast(); NOW = NOW + 200000; TASKS.inventory(4); TASKS.inventory(4); return SolUI.invLast() == a and SolUI.invModel() ~= a end)()") is True)
Iv = fresh([NEW["SolInventory.lua"]], True); Iv.execute("for _, f in ipairs(STARTS) do f() end")
ok, msg = Iv.eval("SolUI.runAction('sol_inv_scan')")
ck("inventory: sol_inv_scan with the switch on starts a sliced scan (plan phase)", ok is True and "state=running" in Iv.eval("SolUI.invStats()")[1] and Iv.eval("SolUI.invModel().noArea") is False, Iv.eval("SolUI.invStats()"))

# ---------------------------------------------------------------- 4. action catalog
PAGES_LUA = r"""
local AR = "\216\179\217\132"
SolUI.extractPage = function(page)
    NOW = NOW + PAGE_MS
    local out = { { kind = "section", text = page .. " top" } }
    for i = 1, 40 do
        out[#out + 1] = { kind = "button", command = page .. "_cmd" .. i, text = "Do " .. i .. ((i % 3 == 0) and AR or ""), enabled = (i % 2 == 0), tip = "why " .. AR .. i }
        if i % 5 == 0 then out[#out + 1] = { kind = "section", text = "part " .. i } end
        if i % 4 == 0 then out[#out + 1] = { kind = "combo", command = page .. "_combo" .. i, options = { "one", "two " .. AR, "three" }, selected = "two " .. AR } end
        if i % 6 == 0 then out[#out + 1] = { kind = "tick", command = page .. "_tick" .. i, options = { { text = "on it", on = true }, { text = "b" } } } end
    end
    return out, "x"
end
"""
def act_run(scan_src, act_src, on, flip_at=None):
    L = fresh([scan_src, PAGES_LUA, act_src], on)
    spent, frames = drive(L, lambda: L.execute("for _, f in ipairs(TICKS) do f() end"), lambda: L.eval("FILES['SolActions_Snapshot.txt'] ~= nil"), flip_at=flip_at)
    return L, spent, frames
def cat(L):
    d = json.loads(L.eval("FILES['SolActions_Snapshot.txt']")); d.pop("t", None); return d
Aref, ap_ref, _ = act_run(OLD["SolWorldScan.lua"], OLD["SolActions.lua"], False)
Aoff, ap_off, _ = act_run(NEW["SolWorldScan.lua"], NEW["SolActions.lua"], False)
Aon, ap_on, afr_on = act_run(NEW["SolWorldScan.lua"], NEW["SolActions.lua"], True)
Aflip, _, _ = act_run(NEW["SolWorldScan.lua"], NEW["SolActions.lua"], True, flip_at=3)
ck("catalog is not trivial", len(cat(Aref)["actions"]) > 100, len(cat(Aref)["actions"]))
ck("catalog: switch off == unpatched lab code (byte for byte)", Aoff.eval("FILES['SolActions_Snapshot.txt']") == Aref.eval("FILES['SolActions_Snapshot.txt']"))
ck("catalog: switch off still written in the frame it is due (one call)", Aoff.eval("PERF.actions_catalog.n") == 1)
ck("catalog: sliced == one-shot (parsed JSON, t aside)", cat(Aon) == cat(Aref))
ck("catalog: switched off half way -> same catalog", cat(Aflip) == cat(Aref))
pages = [x for x in ap_on if abs(x - 3) < 0.6]
ck("catalog: one Living Fellows page a frame (PAGE_MS each), every other frame <= 4 ms + one value (worst %.2f ms over %d frames; old %.2f ms)"
   % (max(ap_on), afr_on, max(ap_ref)), len(pages) >= 2 and all(x <= 4.1 for x in ap_on), ap_on)
ck("catalog: the old frame was both pages + encode at once", max(ap_ref) >= 2 * 3 + 1, max(ap_ref))
Ac = fresh([NEW["SolWorldScan.lua"], PAGES_LUA, NEW["SolActions.lua"]], True)
Ac.execute("NOW = NOW + 16; for _, f in ipairs(TICKS) do f() end; NOW = NOW + 16; for _, f in ipairs(TICKS) do f() end")
Ac.execute("SolUI.writeActionCatalog()")
w1 = Ac.eval("#WRITES")
for _ in range(30): Ac.execute("NOW = NOW + 16; for _, f in ipairs(TICKS) do f() end")
ck("catalog: writeActionCatalog (chat / spawn) writes at once and cancels the sliced one", w1 == 1 and Ac.eval("#WRITES") == 1, (w1, Ac.eval("#WRITES")))
ck("catalog: actionCatalog() without pages still reads them itself", len(list(Ac.eval("SolUI.actionCatalog()").values())) == len(cat(Aref)["actions"]))

# ---------------------------------------------------------------- 5. tonumber gate
GATE = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py")
if os.path.exists(GATE):
    r = subprocess.run([sys.executable, GATE] + [os.path.join(cl, f) for f in FILES[:3]], capture_output=True, text=True)
    ck("tonumber gate (three patched files)", r.returncode == 0, r.stdout[-400:])
else:
    ck("tonumber gate present", False, GATE)
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)

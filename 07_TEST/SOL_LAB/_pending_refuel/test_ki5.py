"""Vehicle handling against real KI5 vehicle scripts: the code is cut from the real files with apply_s31 applied to copies."""
import glob, os, re, shutil, subprocess, sys, tempfile
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
CL = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\lua\client"
W = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\108600"
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
NAMES = ("SolOrders.lua", "SCVehicleUnload.lua", "SCExpeditionCar.lua", "SCVehicle.lua", "SolFuel.lua")
d = tempfile.mkdtemp(prefix="sol_ki5_")
for n in NAMES: shutil.copy(os.path.join(CL, n), d)
if "wheelsReady" not in open(os.path.join(d, "SCExpeditionCar.lua"), encoding="utf-8").read():
    subprocess.check_call([sys.executable, os.path.join(HERE, "apply_s31_lua.py")] + [os.path.join(d, n) for n in NAMES], stdout=subprocess.DEVNULL)
SRC = {n: open(os.path.join(d, n), encoding="utf-8").read().replace("\r\n", "\n") for n in NAMES}
for n, s in SRC.items(): ck("still compiles: " + n, not isinstance(lua51.LuaRuntime().globals().loadstring(s), tuple))
def cut(file, start):
    s = SRC[file]; a = s.index(start); b = s.index("\nend\n", a) + 5
    return s[a:b]

def block_end(t, i):
    depth = 0
    while True:
        if t[i] == "{": depth += 1
        elif t[i] == "}":
            depth -= 1
            if depth == 0: return i
        i += 1
def parse(path):
    t = re.sub(r"/\*.*?\*/", "", open(path, encoding="utf-8", errors="replace").read(), flags=re.S)
    parts, seats, wheels = {}, [], []
    for m in re.finditer(r"\bpart\s+([\w*]+)\s*\{", t):
        body = t[m.end() - 1:block_end(t, m.end() - 1) + 1]
        cap = re.search(r"container\s*\{[^}]*?capacity\s*=\s*(\d+)", body, re.S)
        kind = re.search(r"contentType\s*=\s*(\w+)", body)
        parts[m.group(1)] = {"capacity": int(cap.group(1)) if cap else None, "kind": kind.group(1) if kind else None, "container": "container" in body}
    for m in re.finditer(r"\bpassenger\s+(\w+)\s*\{", t):
        body = t[m.end() - 1:block_end(t, m.end() - 1) + 1]
        o = re.search(r"position\s+outside\s*\{([^}]*)\}", body, re.S)
        area = None
        if o:
            a = re.search(r"area\s*=\s*(\w+)", o.group(1)); area = a.group(1) if a else None
        seats.append({"name": m.group(1), "outside": o is not None, "area": area})
    for m in re.finditer(r"\bwheel\s+(\w+)\s*\{", t): wheels.append(m.group(1))
    if len(seats) < 2:                                                       # kept in a template next to the vehicle
        for other in sorted(glob.glob(os.path.join(os.path.dirname(path), "*.txt"))):
            if other != path and len(re.findall(r"\bpassenger\s+\w+\s*\{", open(other, encoding="utf-8", errors="replace").read())) >= 2:
                seats = parse(other)["seats"]
                break
    return {"parts": parts, "seats": seats, "wheels": wheels}
FIX = {
    "69mini": r"2937786633\mods\69mini\*\media\scripts\vehicles\69mini.txt",
    "MR2": r"3052360250\mods\*\*\media\scripts\vehicles\87toyotaMR2.txt",
    "M35A2": r"2799152995\mods\*\*\media\scripts\vehicles\78amgeneralM35A2.txt",
    "E150long": r"2870394916\mods\86fordE150\*\media\scripts\vehicles\86fordE150long.txt",
    "Bushmaster": r"2897390033\mods\97bushmaster\*\media\scripts\vehicles\97bushmaster.txt",
    "SchoolBus": r"3110911330\mods\*\*\media\scripts\vehicles\87fordB700school.txt",
    "Quint": r"2942793445\mods\*\*\media\scripts\vehicles\90pierceArrowQuint.txt",
}
CARS = {}
for name, pat in FIX.items():
    hits = sorted(glob.glob(os.path.join(W, pat)))
    ck("fixture found: " + name, bool(hits), pat)
    if hits: CARS[name] = parse(hits[-1])

def build(L, car, tires=True, tire_item=True, driver_only=False, missing=()):
    """A vehicle table with exactly the parts and seats its script declares."""
    parts = [(k, v) for k, v in car["parts"].items() if "*" not in k]
    L.execute("PARTS = {}; SEATS = {}; MISSING = {}")
    g = L.globals()
    for pid, p in parts:
        g.addPart(pid, p["capacity"] or -1, p["kind"] or "", -1)
    if tires:
        for i, w in enumerate(car["wheels"]): g.addPart("Tire" + w, -1, "", i, tire_item)
    for i, s in enumerate(car["seats"]): g.addSeat(i, s["outside"], s["area"] or "")
    for i in missing: L.execute("MISSING[%d] = true" % i)
MOCK = r"""
function addPart(id, capacity, kind, wheel, item)
    local p = { id = id, capacity = capacity, kind = kind, wheel = wheel, item = item }
    PARTS[#PARTS + 1] = p
    p.getId = function() return id end
    p.getWheelIndex = function() return wheel end
    p.getCondition = function() return 90 end
    p.getInventoryItem = function() if item == false then return nil end return {} end
    p.getContainerContentType = function() if kind == "" then return nil end return kind end
    if capacity and capacity > 0 and kind == "" then p.getItemContainer = function() return { getCapacity = function() return capacity end } end
    else p.getItemContainer = function() return nil end end
end
function addSeat(i, outside, area) SEATS[i] = { outside = outside, area = area } end
VEH = {
    getPartCount = function() return #PARTS end,
    getPartByIndex = function(self, i) return PARTS[i + 1] end,
    getPartById = function(self, id) for _, p in ipairs(PARTS) do if p.id == id then return p end end return nil end,
    isTrunkLocked = function() return false end,
    getMaxPassengers = function() local n = 0; while SEATS[n] do n = n + 1 end; return n end,
    isSeatInstalled = function(self, i) return not MISSING[i] end,
    isSeatOccupied = function(self, i) return OCCUPIED and OCCUPIED[i] == true end,
    canSwitchSeat = function(self, a, b) return true end,
    getScript = function() return { getPassenger = function(self, i) local s = SEATS[i]; if not s then return nil end
        return { getPositionById = function(self, name) if not s.outside then return nil end return { getArea = function() return s.area end } end } end } end,
}
SC = { GameplayUtil = { call = function(o, m, ...) if o == nil or o[m] == nil then return nil, false end return o[m](o, ...), true end } }
local function U() return SC.GameplayUtil end
function call2(object, method, ...) local v, ok = SC.GameplayUtil.call(object, method, ...); return ok and v or nil end
function callOk(object, method, ...) local v, ok = SC.GameplayUtil.call(object, method, ...); return ok == true, v end
function finite(v) return v end
invoke = callOk
"""
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(MOCK)
L.execute("local call = call2\n" + cut("SCVehicleUnload.lua", "local function trunkPart(vehicle)").replace("local function trunkPart", "function trunkPart", 1))
L.execute("local call = call2\n" + cut("SCExpeditionCar.lua", "function componentReady(vehicle, partId, needsItem)").replace("call(", "callOk(") + "\n")
src = cut("SCExpeditionCar.lua", "local function wheelsReady(vehicle)").replace("local function wheelsReady", "function wheelsReady", 1).replace("call(", "callOk(")
L.execute(src)
L.execute(cut("SCVehicle.lua", "local function exteriorArea(vehicle, seat)").replace("local function exteriorArea", "function exteriorArea", 1))
L.execute(cut("SCVehicle.lua", "local function hasExteriorEntry(vehicle, seat)").replace("local function hasExteriorEntry", "function hasExteriorEntry", 1))
g = L.globals()
for name, car in CARS.items():
    build(L, car)
    ck("%s: %d seats read from its own script" % (name, len(car["seats"])), g.VEH.getMaxPassengers(g.VEH) == len(car["seats"]) and len(car["seats"]) >= 2, len(car["seats"]))
    ck("%s: wheels ready with all its tires" % name, g.wheelsReady(g.VEH) is True, car["wheels"])
    build(L, car, tire_item=False)
    ck("%s: a missing tire is noticed" % name, g.wheelsReady(g.VEH) is False)
if "E150long" in CARS:
    build(L, CARS["E150long"]); t = g.trunkPart(g.VEH)
    ck("E150: its own trunk, by what it holds", t is not None and t.id == "E150Trunk", t and t.id)
    ck("E150: not a seat or glove box", t is not None and not t.id.lower().startswith(("seat", "glove")))
if "Bushmaster" in CARS:
    build(L, CARS["Bushmaster"]); car = CARS["Bushmaster"]
    outside = [i for i, s in enumerate(car["seats"]) if s["area"]]
    ck("Bushmaster: all crew seats share the ramp", len(outside) >= 10 and len({car["seats"][i]["area"] for i in outside}) == 1, outside)
    ck("Bushmaster: every crew seat can be reached", all(g.hasExteriorEntry(g.VEH, i) is True for i in outside), [i for i in outside if g.hasExteriorEntry(g.VEH, i) is not True])
L.execute("PARTS = {}; SEATS = {}; addSeat(0, true, 'SeatFrontLeft'); addSeat(1, true, 'SeatFrontRight'); addSeat(2, true, 'SeatMiddleRight'); addSeat(3, true, 'SeatMiddleRight')")
ck("ordinary van: the seat behind the door still needs a seat switch", g.hasExteriorEntry(g.VEH, 2) is True and g.hasExteriorEntry(g.VEH, 3) is False, (g.hasExteriorEntry(g.VEH, 2), g.hasExteriorEntry(g.VEH, 3)))
L.execute("addPart('Huey', -1, '', -1)")
ck("no wheels declared: nothing to fail on", g.wheelsReady(g.VEH) is True)

# ---- which seat, on the real board code
B = SRC["SolOrders.lua"]; a = B.index("function O.board(targetVehicle)"); b = B.index("-- by car to a point", a)
B1 = lua51.LuaRuntime(unpack_returned_tuples=True)
B1.execute(r"""
O, U, SAID, JOB = {}, {}, nil, nil
AR = setmetatable({}, { __index = function(_, k) return k end })
function say(t) SAID = t end
function log() end
function nowMs() return 1000 end
function freshFlow() end
function vehApi() return true end
function seat() return "out" end
function sol() return nil end
function stepBoard() end
O.takeWheel = function() end
U.gpsTakeWheel = function() end
function playerVehicle() return VEH end
SEATN = 5; TAKEN = {}; GONE = {}
VEH = { getMaxPassengers = function() return SEATN end, isSeatOccupied = function(self, i) return TAKEN[i] == true end, isSeatInstalled = function(self, i) return not GONE[i] end }
job = nil
""")
B1.execute(B[a:b])
g2 = B1.globals()
B1.execute("GONE = { [1] = true }; O.board(VEH)")
ck("a seat that is not there is skipped", g2.job is not None and g2.job.seat == 2, g2.job and g2.job.seat)
B1.execute("job = nil; GONE = { [1] = true, [2] = true, [3] = true, [4] = true }; SAID = nil; O.board(VEH)")
ck("no installed seat: says so", g2.job is None and g2.SAID == "no_seat", g2.SAID)

# ---- fuel kind and the generic trunk fall-through
FU = SRC["SolFuel.lua"]
ck("a tank that takes other fuel is refused", '"wrong_fuel"' in FU and 'fuelKind ~= "Gasoline"' in FU)
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)

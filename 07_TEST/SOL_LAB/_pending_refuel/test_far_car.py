"""Switch far_car on a mocked game under the game's Lua rules (kahlua_env), plus the Mind's words. Everything runs on temporary copies.
1. apply_s65.py patches copies of SolFar.lua / SolAuthority.lua / chat_service.py; applying twice changes nothing; it applies before or after
   a stand-in for apply_s64.py (waitTick's clock) and before or after apply_s63_mind.py.
2. With the switch off, the whole of test_far.py passes on the patched copies (the same behaviour as today).
3. With it on: the list, the choice (hers first, nearest, fuel, verdicts, too close, stale list), the wait per kind, the move, the failures."""
import glob, os, re, shutil, subprocess, sys, tempfile
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"C:\Users\JAMAL\Desktop\Sol"
LAB_CL = ROOT + r"\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\lua\client"
MIND_SRC = ROOT + r"\05_TOOLS\sol_mind"
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)

TMP = tempfile.mkdtemp(prefix="sol_far_car_")
def fresh(name):
    d = os.path.join(TMP, name)
    os.makedirs(os.path.join(d, "client"))
    shutil.copy(os.path.join(HERE, "SolFar.lua"), os.path.join(d, "client"))
    shutil.copy(os.path.join(LAB_CL, "SolAuthority.lua"), os.path.join(d, "client"))
    shutil.copy(os.path.join(LAB_CL, "SCPersistence.lua"), os.path.join(d, "client"))
    os.makedirs(os.path.join(d, "mind"))
    for f in glob.glob(os.path.join(MIND_SRC, "*")):
        if os.path.isfile(f): shutil.copy(f, os.path.join(d, "mind"))
    return os.path.join(d, "client"), os.path.join(d, "mind")
def apply(script, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, script)] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
def read(p): return open(p, encoding="utf-8", newline="").read()

# a stand-in for apply_s64.py: it changes waitTick's clock line in place
def s64_stub(cl):
    if os.path.exists(os.path.join(HERE, "apply_s64.py")):                     # the real one, when it is staged
        r = apply("apply_s64.py", cl); assert r.returncode == 0, r.stderr[-300:]; return
    p = os.path.join(cl, "SolFar.lua"); t = read(p)
    old = "if not paused() then wait.left = wait.left - spent end"
    if "SPEED_STUB" in t: return
    assert t.count(old) == 1
    open(p, "w", encoding="utf-8", newline="").write(t.replace(old, "if not paused() then wait.left = wait.left - spent * 1 end -- SPEED_STUB"))

# ---- 1. the patch
cl, md = fresh("a")
r = apply("apply_s65.py", cl, md); ck("applies", r.returncode == 0, r.stderr[-400:])
once = (read(os.path.join(cl, "SolFar.lua")), read(os.path.join(cl, "SolAuthority.lua")), read(os.path.join(md, "chat_service.py")))
r = apply("apply_s65.py", cl, md); ck("applied twice: no change", r.returncode == 0 and once == (read(os.path.join(cl, "SolFar.lua")), read(os.path.join(cl, "SolAuthority.lua")), read(os.path.join(md, "chat_service.py"))), r.stderr[-300:])
ck("the switch is listed once", once[1].count('"far_car"') == 1)
_sp = read(os.path.join(cl, "SCPersistence.lua"))
ck("her saved keys: one read-only function added", _sp.count("function persistence.pendingKeyIds(") == 1 and not isinstance(lua51.LuaRuntime().globals().loadstring(_sp), tuple))
_fn = _sp[_sp.index("function persistence.pendingKeyIds(id)"):_sp.index("function persistence.pendingSnapshot()")]
_L = lua51.LuaRuntime(unpack_returned_tuples=True)
_L.execute("persistence = {}; pending = { sol = { record = { inventory = { schema = 2, complete = true, roots = { { type = 'Base.Bag', children = { { type = 'Base.CarKey', key = { id = 4242 } } } }, { type = 'Base.KeyRing', key = { id = 7 } } } } } }, q = { status = 'quarantined', record = {} } }")
_L.execute(_fn)
_k = _L.eval("persistence.pendingKeyIds('sol')")
ck("her saved keys: found in a bag and loose", _k is not None and _k[4242] is True and _k[7] is True and _k[5] is None, _k and dict(_k))
ck("her saved keys: nothing for another record or a quarantined one", _L.eval("persistence.pendingKeyIds('x')") is None and _L.eval("persistence.pendingKeyIds('q')") is None)
ck("SolFar.lua compiles", not isinstance(lua51.LuaRuntime().globals().loadstring(once[0]), tuple), lua51.LuaRuntime().globals().loadstring(once[0]))
ck("the original's line ends are kept", ("\r\n" in once[2]) == ("\r\n" in read(os.path.join(MIND_SRC, "chat_service.py"))))
clB, mdB = fresh("b"); s64_stub(clB); r = apply("apply_s65.py", clB, "-")
ck("after apply_s64 (stand-in): applies", r.returncode == 0 and re.search("SPEED_STUB|speedFactor", read(os.path.join(clB, "SolFar.lua"))) and "carWhereFar" in read(os.path.join(clB, "SolFar.lua")), r.stderr[-300:])
clC, mdC = fresh("c"); apply("apply_s65.py", clC, "-"); s64_stub(clC)
ck("before apply_s64 (stand-in): both there", re.search("SPEED_STUB|speedFactor", read(os.path.join(clC, "SolFar.lua"))) and "carWhereFar" in read(os.path.join(clC, "SolFar.lua")))
ck("either order: the same file", read(os.path.join(clB, "SolFar.lua")) == read(os.path.join(clC, "SolFar.lua")))
for _d in (clB, clC):
    apply("apply_s65.py", _d, "-"); s64_stub(_d); apply("apply_s65.py", _d, "-")
ck("both, again in either order: still the same, each switch listed once", read(os.path.join(clB, "SolFar.lua")) == read(os.path.join(clC, "SolFar.lua"))
   and all(read(os.path.join(_d, "SolAuthority.lua")).count('"far_car"') == 1 and read(os.path.join(_d, "SolAuthority.lua")).count('"far_wait_speed"') <= 1 for _d in (clB, clC)))
ck("both: SolFar.lua compiles", not isinstance(lua51.LuaRuntime().globals().loadstring(read(os.path.join(clB, "SolFar.lua"))), tuple))
BOTH = read(os.path.join(clB, "SolFar.lua"))
r1 = apply("apply_s63_mind.py", mdB); r2 = apply("apply_s65.py", "-", mdB)
ck("Mind: after apply_s63_mind", r1.returncode == 0 and r2.returncode == 0, (r1.stderr[-200:], r2.stderr[-200:]))
r1 = apply("apply_s65.py", "-", mdC); r2 = apply("apply_s63_mind.py", mdC)
ck("Mind: before apply_s63_mind", r1.returncode == 0 and r2.returncode == 0, (r1.stderr[-200:], r2.stderr[-200:]))
ck("Mind: either order, the same file", read(os.path.join(mdB, "chat_service.py")) == read(os.path.join(mdC, "chat_service.py")))

# ---- 2. switch off: today's behaviour, by today's own test
reg = os.path.join(TMP, "reg")
shutil.copytree(HERE, reg, ignore=shutil.ignore_patterns("__pycache__", "speech_tr"))
shutil.copy(os.path.join(cl, "SolFar.lua"), os.path.join(reg, "SolFar.lua"))
tf = read(os.path.join(reg, "test_far.py")).replace(r'r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind"', "r" + repr(md)[0] + md + repr(md)[0])
open(os.path.join(reg, "test_far.py"), "w", encoding="utf-8", newline="").write(tf)
r = subprocess.run([sys.executable, "test_far.py"], cwd=reg, capture_output=True, text=True, encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1"))
last = (r.stdout.strip().splitlines() or [""])[-1]
ck("switch off: test_far.py passes on the patched SolFar.lua and chat_service.py", r.returncode == 0 and "ALL PASS" in last, last + r.stderr[-300:])

# ---- 3. switch on
SRC = once[0]
_t = read(os.path.join(HERE, "test_far.py"))
WORLD = re.search(r'WORLD = r"""(.*?)"""\nSRC', _t.replace("\r\n", "\n"), re.S).group(1)
CARS = r"""
FARCAR = true
SolAuthority = { on = function(n) return n == "far_car" and FARCAR end }
FUEL = 20
DOOR_LOCKED, IGNITION, IGN_KEY, HOT, HOT_BROKEN, CAR_KEY, KEY_INSIDE = false, true, 4242, false, false, 4242, false
THE_CAR = { getX = function() return CARX or 1010 end, getY = function() return 1000 end, getSqlId = function() return 77 end, getScriptName = function() return CAR_SCRIPT or "Base.CarNormal" end,
            getPartById = function(self, id)
                if id == "GasTank" then return { getContainerContentAmount = function() return FUEL end, setContainerContentAmount = function(s, v) LEFT = v end } end
                if id == "DoorFrontLeft" and not NO_DOOR then return { getDoor = function() return { isLocked = function() return DOOR_LOCKED end } end } end
            end,
            getKeyId = function() return CAR_KEY end, isKeysInIgnition = function() return IGNITION end,
            getCurrentKey = function() if IGNITION then return { getKeyId = function() return IGN_KEY end } end end,
            isHotwired = function() return HOT end, isHotwiredBroken = function() return HOT_BROKEN end,
            getPartCount = function() return 2 end,
            getPartByIndex = function(self, i) if i == 1 then return { getItemContainer = function() return { haveThisKeyId = function(s, k) if KEY_INSIDE and k == CAR_KEY then return {} end end } end } end return {} end }
SAVED_KEYS = {}
SurvivorCompanion.Persistence.pendingKeyIds = function(id) return SAVED_KEYS end
NOT_LOADED = true
LOADED_ID = 77
SurvivorCompanion.Vehicle = { loadedBySqlId = function(id) if id == LOADED_ID and not NOT_LOADED then return THE_CAR end end }
MD = { carSqlId = 77, carX = 5000, carY = 5000, carFuel = 20, carMass = 1000, carQuality = 100 }
ModData = { getOrCreate = function() return MD end }
MOVES = {}
MOVE_STATE = "ok"
function solCarMoveRequest(id, x, y) MOVES[#MOVES + 1] = { id, x, y }; return true end
function solCarMoveState() return MOVE_STATE end
function solCarMoveRing() return 6 end
function solCarMoveCancel() return true end
REQS = {}
CN_STATE = "idle"
LIST = ""
function solCarsNearRequest(x, y, r) REQS[#REQS + 1] = { x, y, r }; CN_STATE = "ok"; return true end
function solCarsNearState() return CN_STATE end
function solCarsNearResult() return "1600,1000|" .. LIST end
"""
def world(setup=""):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(WORLD); L.execute(CARS)
    if setup: L.execute(setup)
    L.execute(SRC)
    return L, L.globals()
def car(i, x, y, script="Base.SmallCar", fuel="30", verdict="ok", loaded="0", quality="100", key=None, start="1,0,0"):
    d = round(((x - 1600) ** 2 + (y - 1000) ** 2) ** 0.5, 1)
    return "%d,%s,%s,%s,%s,%s,80,0,%s,%d,%s,%s,%s" % (i, x, y, d, script, fuel, quality, key if key is not None else 9000 + i, loaded, verdict, start)
def listed(*rows): return 'LIST = "' + ";".join(rows) + '"'
def ready(L, g): g.alive(); g.clock(1000)                       # the first tick asks, the next one reads
def run_wait(L, secs): L.execute("for i = 1, %d do NOW = NOW + 1000; TASKS['far']() end" % secs)
far = lambda g, o: tuple(g.SolUI.solFar(o))

L, g = world("FARCAR = false"); g.alive(); g.clock(20000)
ck("off: no list is asked for", len(g.REQS) == 0, len(g.REQS))
ck("off: 'cars' is not an option", far(g, "cars") == (False, "unknown_option"), far(g, "cars"))
ck("off: car_where as before (her car)", far(g, "car_where") == (True, "car:5000,5000,1000,1000,6"), far(g, "car_where"))
L, g = world("FARCAR = false; NOT_LOADED = false; CAR_SCRIPT = 'Base.RKCBradleyM3'"); g.alive()
ck("off: a tracked car near him still 3 minutes", far(g, "come_car") == (True, "waiting:180"), far(g, "come_car"))

L, g = world(listed(car(5, 1610, 1000), car(6, 1585, 1000, "Base.RKCBradleyM3", "60")))
g.alive()
ck("on: the list is asked for around her, 25 tiles", len(g.REQS) == 1 and list(g.REQS[1].values()) == [1600, 1000, 25], [list(v.values()) for v in g.REQS.values()])
ck("on: before it is read: scanning, nothing chosen", far(g, "car_where") == (False, "scanning"))
g.clock(1000)
r = far(g, "cars"); ck("on: what is around her", r[0] is True and r[1].startswith("cars:2|5,Base.SmallCar,10,30.0,ok,0;6,Base.RKCBradleyM3,15,60.0,ok,0"), r)
ck("on: nearest usable car chosen", far(g, "car_where") == (True, "car:1610,1000,1000,1000,6"), far(g, "car_where"))
r = far(g, "car_far:1100.5,1000.5,600"); ck("on: a car: 3 minutes", r == (True, "waiting:180"), r)
ck("on: nothing moved during the wait", len(g.MOVES) == 0)
run_wait(L, 181); g.clock(1000)
ck("on: that car's row is moved, not hers", len(g.MOVES) == 1 and list(g.MOVES[1].values()) == [5, 1100.5, 1000.5], [list(v.values()) for v in g.MOVES.values()])
expect = 600 * 0.07 / 158.53 * 1.25
ck("on: it is hers now, fuel owed for the road", g.MD.carSqlId == 5 and abs(g.MD.fuelDue - expect) < 1e-6 and g.MD.carX == 1100.5, (g.MD.carSqlId, g.MD.fuelDue))
ck("on: she goes beside it", list(g.MOVED.values()) == [1103, 1000, 0] and far(g, "poll") == (True, "placed"), g.MOVED and list(g.MOVED.values()))
L.execute("LOADED_ID = 5; NOT_LOADED = false"); g.clock(1000)
ck("on: fuel taken from that car once it is there", abs(g.LEFT - (20 - expect)) < 1e-5 and g.MD.fuelDue is None, g.LEFT)

L, g = world(listed(car(5, 1610, 1000, fuel="30"), car(77, 1620, 1000, "Base.CarNormal", "20"))); ready(L, g)
ck("hers first when she can use it, even farther", far(g, "car_where") == (True, "car:1620,1000,1000,1000,6"), far(g, "car_where"))
r = far(g, "car_far:1100,1000,600"); run_wait(L, 181); g.clock(1000)
ck("hers: moved by its own id", r == (True, "waiting:180") and list(g.MOVES[1].values())[0] == 77, r)
L, g = world(listed(car(5, 1610, 1000), car(77, 1605, 1000, "Base.CarNormal", "?", "fuel_unknown"))); ready(L, g)
ck("hers with fuel unknown: not taken any more, the next one", far(g, "car_where") == (True, "car:1610,1000,1000,1000,6"), far(g, "car_where"))
L, g = world("SAVED_KEYS = { [77] = true }; " + listed(car(77, 1605, 1000, "Base.CarNormal", "20", "locked", key=77))); ready(L, g)
ck("hers locked: refused even with her key (unlocked first)", far(g, "car_where") == (False, "locked_near"), far(g, "car_where"))
L, g = world(listed(car(77, 1605, 1000, "Base.CarNormal", "20", "no_key", key=77, start="0,0,0"))); ready(L, g)
ck("hers, no key anywhere: refused like any other", far(g, "car_where") == (False, "no_key_near"), far(g, "car_where"))
L, g = world("SAVED_KEYS = { [77] = true }; " + listed(car(77, 1605, 1000, "Base.CarNormal", "20", "no_key", key=77, start="0,0,0"))); ready(L, g)
ck("hers, its key in her saved things: hers", far(g, "car_where") == (True, "car:1605,1000,1000,1000,6"), far(g, "car_where"))
# ---- unlocked and startable (the owner's rule), on the list the Java side gives
L, g = world("MD = {}; " + listed(car(5, 1605, 1000, verdict="locked", start="1,0,0"))); ready(L, g)
ck("a locked car: not used, says so", far(g, "car_where") == (False, "locked_near"), far(g, "car_where"))
L, g = world("MD = {}; " + listed(car(5, 1605, 1000, verdict="lock_unknown", start="1,0,0"))); ready(L, g)
ck("lock unknown: not used", far(g, "car_where") == (False, "locked_near"), far(g, "car_where"))
L, g = world("MD = {}; " + listed(car(5, 1605, 1000, verdict="no_key", start="0,0,0"))); ready(L, g)
ck("no key anywhere: not used, says so", far(g, "car_where") == (False, "no_key_near") and far(g, "cars")[1].endswith("5,Base.SmallCar,5,30.0,no_key,0"), (far(g, "car_where"), far(g, "cars")))
L, g = world("MD = {}; " + listed(car(5, 1605, 1000, verdict="start_unknown", start="?,0,0"))); ready(L, g)
ck("start unknown and no key with her: not used (never a guess)", far(g, "car_where") == (False, "no_key_near"), far(g, "car_where"))
for what, start in (("a key in the ignition", "1,0,0"), ("hotwired", "0,1,0"), ("a key in the glovebox", "0,0,1")):
    L, g = world("MD = {}; " + listed(car(5, 1605, 1000, verdict="ok", start=start))); ready(L, g)
    ck("startable by " + what + ": used", far(g, "car_where") == (True, "car:1605,1000,1000,1000,6"), far(g, "car_where"))
L, g = world("MD = {}; SAVED_KEYS = { [9005] = true }; " + listed(car(5, 1605, 1000, verdict="no_key", start="0,0,0"))); ready(L, g)
ck("its key in her saved things: used, and listed as usable", far(g, "car_where") == (True, "car:1605,1000,1000,1000,6") and far(g, "cars")[1].endswith(",ok,0"), (far(g, "car_where"), far(g, "cars")))
L, g = world("MD = {}; SAVED_KEYS = { [9005] = true }; " + listed(car(5, 1605, 1000, verdict="start_unknown", start="?,0,?"))); ready(L, g)
ck("start unknown but its key is with her: used", far(g, "car_where") == (True, "car:1605,1000,1000,1000,6"), far(g, "car_where"))
L, g = world("MD = {}; SAVED_KEYS = { [1234] = true }; " + listed(car(5, 1605, 1000, verdict="no_key", start="0,0,0"))); ready(L, g)
ck("a key with her for another car: not used", far(g, "car_where") == (False, "no_key_near"), far(g, "car_where"))
LIVE = "MD = {}; LIVE_BODY = { getX = function() return 1600 end, getY = function() return 1000 end, getCurrentSquare = function() return nil end, getInventory = function() return { haveThisKeyId = function(s, k) if k == LIVE_KEY then return {} end end } end }; SolUI.solActor = function() return LIVE_BODY end; "
L, g = world(LIVE + "LIVE_KEY = 9005; " + listed(car(5, 1605, 1000, verdict="no_key", start="0,0,0"))); g.alive(); g.clock(3000); g.clock(1000)
ck("registered without a body: its key in her live inventory: used", far(g, "car_where") == (True, "car:1605,1000,1000,1000,6"), far(g, "car_where"))
L, g = world(LIVE + "LIVE_KEY = 1; " + listed(car(5, 1605, 1000, verdict="no_key", start="0,0,0"))); g.alive(); g.clock(3000); g.clock(1000)
ck("registered without a body, no key for it: not used", far(g, "car_where") == (False, "no_key_near"), far(g, "car_where"))
L, g = world("MD = {}; SurvivorCompanion.Persistence.pendingKeyIds = nil; SAVED_KEYS = nil; " + listed(car(5, 1605, 1000, verdict="no_key", start="0,0,0"))); ready(L, g)
ck("her things cannot be read: no key counted", far(g, "car_where") == (False, "no_key_near"), far(g, "car_where"))
L, g = world("MD.carTowing = true; " + listed(car(77, 1605, 1000), car(5, 1610, 1000))); ready(L, g)
ck("hers is towing: the next one", far(g, "car_where") == (True, "car:1610,1000,1000,1000,6"), far(g, "car_where"))
L, g = world(listed(car(5, 1601, 1000, verdict="no_fuel", fuel="0"), car(6, 1602, 1000, verdict="locked"), car(7, 1603, 1000, "Base.VanSeatsBurnt", "?", "wreck"),
                    car(8, 1604, 1000, verdict="loaded", loaded="1"), car(9, 1605, 1000, verdict="fuel_unknown", fuel="?"), car(10, 1606, 1000, verdict="no_engine"),
                    car(11, 1590, 1020)))
ready(L, g)
ck("not ok: passed over (no fuel, locked, burnt, loaded, fuel unknown, no engine)", far(g, "car_where") == (True, "car:1590,1020,1000,1000,6"), far(g, "car_where"))
L, g = world("MD = {}; " + listed(car(5, 1610, 1000, fuel="0.6"))); ready(L, g)
ck("fuel for the road counted: too little is not used", far(g, "car_where") == (False, "no_fuel_near"), far(g, "car_where"))
L, g = world("MD = {}; LIST = ''"); ready(L, g)
ck("no car near her: says so", far(g, "car_where") == (False, "no_car_near") and far(g, "cars") == (True, "cars:0|"), (far(g, "car_where"), far(g, "cars")))
L, g = world("LIST = ''"); ready(L, g)
ck("no car near her, hers far away: not taken unchecked any more", far(g, "car_where") == (False, "no_car_near"), far(g, "car_where"))
ck("car_far without a choice from car_where: refused, nothing waits", far(g, "car_far:1100,1000,600") == (False, "pick_expired") and far(g, "poll") == (True, "idle"))
L, g = world("PX, PY = 1560, 1000; MD = {}; " + listed(car(5, 1590, 1000)))
ready(L, g)
ck("a car right next to what is loaded around him: not touched", far(g, "car_where") == (False, "car_too_close"), far(g, "car_where"))
for script, secs in (("Base.RKCBradleyM3", 210), ("Base.UH1HHelicopter", 60), ("Base.PickUpTruck", 180)):
    L, g = world(listed(car(5, 1610, 1000, script))); ready(L, g); far(g, "car_where")
    r = far(g, "car_far:1100,1000,600"); ck("the wait for %s: %d s" % (script, secs), r == (True, "waiting:%d" % secs), r)
L, g = world("NOT_LOADED = false; CAR_SCRIPT = 'Base.RKCBradleyM3'"); g.alive()
ck("on: a tracked car near him: 3.5 minutes", far(g, "come_car") == (True, "waiting:210"), far(g, "come_car"))
# ---- her car loaded near him: the same rule, read from the car
NEAR = "NOT_LOADED = false; IGNITION = false; "
for what, setup, want in (("locked", "DOOR_LOCKED = true; IGNITION = true", (False, "car_locked")),
                          ("door unreadable", "NO_DOOR = true; IGNITION = true", (False, "car_lock_unknown")),
                          ("no key anywhere", "", (False, "car_no_key")),
                          ("a key for it in the ignition", "IGNITION = true", (True, "waiting:180")),
                          ("another car's key in the ignition", "IGNITION = true; IGN_KEY = 1", (False, "car_no_key")),
                          ("hotwired", "HOT = true", (True, "waiting:180")),
                          ("hotwired, wires broken", "HOT = true; HOT_BROKEN = true", (False, "car_no_key")),
                          ("its key in her saved things", "SAVED_KEYS = { [4242] = true }", (True, "waiting:180")),
                          ("its key inside the car", "KEY_INSIDE = true", (True, "waiting:180"))):
    L, g = world(NEAR + setup); g.alive()
    ck("near him, " + what, far(g, "come_car") == want, far(g, "come_car"))
L, g = world("FARCAR = false; NOT_LOADED = false; DOOR_LOCKED = true; IGNITION = false"); g.alive()
ck("off: near him, locked and no key: as before (not checked)", far(g, "come_car") == (True, "waiting:180"), far(g, "come_car"))
L, g = world(listed(car(5, 1610, 1000, fuel="2"))); ready(L, g); far(g, "car_where")
ck("the road turns out longer than the fuel: says so, nothing waits", far(g, "car_far:1100,1000,9000") == (False, "picked_no_fuel") and far(g, "poll") == (True, "idle"), far(g, "poll"))
L, g = world(listed(car(5, 1610, 1000))); ready(L, g); far(g, "car_where"); L.execute("NOW = NOW + 130000")
r = far(g, "car_far:1100,1000,600")
ck("a choice too old is not used, and nothing else is taken instead", r == (False, "pick_expired") and len(g.MOVES) == 0, r)
L, g = world("MOVE_STATE = 'spot_taken'; " + listed(car(5, 1610, 1000))); ready(L, g); far(g, "car_where"); far(g, "car_far:1100,1000,600"); run_wait(L, 181); g.clock(1000)
ck("the move refused: says why, she stays, hers is still hers, nothing owed", far(g, "poll") == (True, "spot_taken") and g.MOVED is None and g.MD.carSqlId == 77 and g.MD.fuelDue is None, (far(g, "poll"), g.MD.carSqlId))
L, g = world("MOVE_STATE = 'loaded'; " + listed(car(5, 1610, 1000))); ready(L, g); far(g, "car_where"); far(g, "car_far:1100,1000,600"); run_wait(L, 181); g.clock(1000)
ck("the chosen car got loaded meanwhile: refused by the Java side, nothing changed", far(g, "poll") == (True, "loaded") and g.MD.carSqlId == 77)
L, g = world("NOT_LOADED = false; CARX = 2000; " + listed(car(5, 1610, 1000))); ready(L, g); far(g, "car_where"); far(g, "car_far:1100,1000,600"); run_wait(L, 181); g.clock(1000)
ck("her own car loaded somewhere: the chosen one still moves", len(g.MOVES) == 1 and list(g.MOVES[1].values())[0] == 5, far(g, "poll"))
L, g = world(listed(car(5, 1610, 1000))); ready(L, g); L.execute("REC = { id = 'sol-1', x = 1700, y = 1000, z = 0 }")
ck("she is somewhere else now: the old list is not used", far(g, "car_where") == (False, "scanning") and far(g, "cars") == (False, "scanning"))
L, g = world(listed(car(5, 1610, 1000))); ready(L, g); L.execute("CN_STATE = 'queued'; NOW = NOW + 61000")
ck("the list too old and the next not there yet: scanning", far(g, "cars") == (False, "scanning"))
L, g = world("solCarsNearRequest = nil"); g.alive()
ck("the jar without the list: no_java, no crash", far(g, "car_where") == (False, "no_java") and far(g, "cars") == (False, "no_java"))
L, g = world("IDS = {}"); g.alive(); ck("no saved Sol", far(g, "cars") == (False, "no_sol"))
L, g = world(); g.alive(); L.execute("BODY = { }"); ck("she is here", far(g, "cars") == (True, "here"))
L, g = world("solCarsNearResult = function() error('boom') end; " + listed(car(5, 1610, 1000))); ready(L, g)
ck("a bad answer from the Java side: no crash, scanning", far(g, "car_where") == (False, "scanning"))
L, g = world(listed(car(5, 1610, 1000))); g.alive(); n0 = len(g.REQS); g.clock(5000); g.clock(5000)
ck("the list is not asked for every tick", len(g.REQS) == n0, (n0, len(g.REQS)))
g.clock(16000); ck("but again after a while", len(g.REQS) == n0 + 1, len(g.REQS))

# ---- with apply_s64 too: the picked car's wait follows its clock
SRC = BOTH
L, g = world(listed(car(6, 1610, 1000, "Base.RKCBradleyM3"))); ready(L, g); far(g, "car_where"); far(g, "car_far:1100,1000,600"); run_wait(L, 205)
ck("both patches, 1x: a tracked car still waiting after 205 s", far(g, "poll")[1].startswith("waiting:") and len(g.MOVES) == 0, far(g, "poll"))
run_wait(L, 6); g.clock(1000); ck("both patches, 1x: moved after 210 s", len(g.MOVES) == 1 and list(g.MOVES[1].values())[0] == 6, far(g, "poll"))
if "speedFactor" in BOTH:
    L, g = world("SolAuthority.on = function(n) return n == 'far_car' or n == 'far_wait_speed' end; function getGameSpeed() return 2 end; " + listed(car(6, 1610, 1000, "Base.RKCBradleyM3")))
    ready(L, g); far(g, "car_where"); far(g, "car_far:1100,1000,600"); run_wait(L, 43); g.clock(1000)
    ck("both patches, fast-forward step 2 (5x): a 210 s trip in 43 s", len(g.MOVES) == 1 and list(g.MOVES[1].values())[0] == 6, far(g, "poll"))
SRC = once[0]

# ---- the Mind
sys.path.insert(0, md)
import chat_service as CS, intent_engine as IE
CS.FAR_WAKE = True
CS.time.sleep = lambda s: None
ACT, STATE = [], {"cars": [(True, "cars:3|5,Base.SmallCar,10,30.0,ok,0;77,Base.CarNormal,14,?,locked,1;7,Base.VanSeatsBurnt,20,?,wreck,0")], "where": [(True, "car:1610,1000,1000,1000,6")]}
def fake(lua, aid, option=None, wait=3.0):
    ACT.append((aid, option))
    if option == "status": return {"ok": True, "reason": "far:600"}
    if option == "cars": v = STATE["cars"].pop(0) if len(STATE["cars"]) > 1 else STATE["cars"][0]; return {"ok": v[0], "reason": v[1]}
    if option == "come_car": return {"ok": False, "reason": "car_not_near"}
    if option == "car_where": v = STATE["where"].pop(0) if len(STATE["where"]) > 1 else STATE["where"][0]; return {"ok": v[0], "reason": v[1]}
    if option and option.startswith("car_far:"): return {"ok": True, "reason": "waiting:210"}
    return {"ok": False, "reason": "unknown_option"}
CS.run_action = fake
CS.RR.pickup_spot = lambda *a: (1100.5, 1000.5, 600.0)
class Goals:
    def __init__(self): self.sub = []
    def submit(self, g): self.sub.append(g); return {"ok": True}
    def cancel(self, reason=""): return False
    def describe(self): return "none"
def chat():
    c = CS.Chat.__new__(CS.Chat)
    c.dir, c.log, c.goals, c.pending_card, c._forced, c._turn_action_results = TMP, (lambda x: None), Goals(), None, None, []
    c.hist, c.lock, c._save, c.publish = [], __import__("threading").Lock(), (lambda: None), (lambda: None)
    return c
def say(text, snap={"player": {"x": 1000, "y": 1000}}):
    ACT.clear(); c = chat(); c._pre_intents([{"role": "user", "text": text}], snap, None); return c
for t in ["شو في سيارات حواليكي؟", "في سيارات حواليكي", "شو في سيارات جنبك؟", "كم سيارة في حواليكي؟", "في عربيات قريبة منك؟"]:
    c = say(t); f = c._forced or ""
    ck("cars question: " + t, ("sol_far", "cars") in ACT and f.startswith("حواليّ في 3 سيارات:") and "SmallCar على بعد 10 خطوة، بتمشي، فيها 30.0 لتر" in f
       and "CarNormal (سيارتي)" in f and "مقفولة" in f and "محروقة" in f and "تعالي بالسيارة" in f, (f, ACT))
STATE["cars"] = [(True, "cars:2|5,Base.SmallCar,10,30.0,no_key,0;6,Base.CarNormal,12,?,start_unknown,0")]; c = say("شو في سيارات حواليكي؟")
ck("cars question: the key words", "ما في مفتاحها ولا مشرّطة" in (c._forced or "") and "ما بعرف إذا بقدر شغّلها" in (c._forced or "") and "تعالي بالسيارة" not in (c._forced or ""), c._forced)
STATE["cars"] = [(True, "cars:3|5,Base.SmallCar,10,30.0,ok,0;77,Base.CarNormal,14,?,locked,1;7,Base.VanSeatsBurnt,20,?,wreck,0")]
c = say("شو في سيارات حواليكي؟")
ck("one game call for the question, no other action", [a for a in ACT if a[1] not in ("status",)] == [("sol_far", "cars")], ACT)
STATE["cars"] = [(True, "cars:0|")]; c = say("شو في سيارات حواليكي؟"); ck("none: says so", c._forced == "ما في ولا سيارة حواليّ.", c._forced)
STATE["cars"] = [(False, "scanning"), (False, "scanning"), (True, "cars:1|5,Base.SmallCar,10,30.0,ok,0")]; c = say("شو في سيارات حواليكي؟")
ck("still reading: asks again, then answers", c._forced and c._forced.startswith("حواليّ في سيارة وحدة:") and ACT.count(("sol_far", "cars")) == 3, (c._forced, ACT))
STATE["cars"] = [(False, "unknown_option")]; c = say("شو في سيارات حواليكي؟")
ck("switch off in the game: not answered by this (as before)", c._forced is None or "حواليّ" not in c._forced, c._forced)
STATE["cars"] = [(False, "no_java")]; c = say("شو في سيارات حواليكي؟"); ck("cannot read: honest", c._forced == "ما قدرت شوف شو في سيارات حواليّ هلأ، جرب كمان شوي.", c._forced)
STATE["cars"] = [(True, "cars:1|5,Base.SmallCar,10,30.0,ok,0")]
c = say("شو في سيارات حواليكي؟", {"player": {"x": 1}, "sol": {"x": 1}}); ck("she is here: not this answer", ("sol_far", "cars") not in ACT, ACT)
for t in ["ركبي السيارة الاقرب عليكي", "تعالي بالسيارة", "سيارتي حلوة"]:
    c = say(t); ck("not the question: " + t, ("sol_far", "cars") not in ACT, ACT)
STATE["where"] = [(False, "scanning"), (True, "car:1610,1000,1000,1000,6")]
c = say("تعالي بالسيارة"); ck("car_where still reading: asked again, the trip starts", ("sol_far", "car_far:1100.5,1000.5,600") in ACT and ACT.count(("sol_far", "car_where")) == 2 and c._forced == "جاية بالسيارة، بدي 4 دقايق.", (c._forced, ACT))
for why in ("no_car_near", "no_fuel_near", "scanning", "no_key_near", "locked_near"):
    STATE["where"] = [(False, why)]; c = say("تعالي بالسيارة"); ck("car_where says %s: honest" % why, c._forced == CS.FAR_CAR_NO[why], c._forced)

print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if FAIL else 0)

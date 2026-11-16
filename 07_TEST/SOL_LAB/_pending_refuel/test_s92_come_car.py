"""Offline tests for s92 come_by_car (apply_s92_come_car_lua.py + apply_s92_come_car_mind.py). usage: python test_s92_come_car.py
  1 installers on COPIES of the current live lab files and the live Mind: apply, twice change nothing, compile (Kahlua-like Lua, py_compile),
    pure ASCII Lua, no tonumber(f()) site added, come_by_car=on added to a copy of the switch file, far_car never written
  2 come_by_car 1: her car loaded 70 tiles from him while she is out of his loaded ring: before car_not_near, after she comes by it
  3 come_by_car 2: her own car not loaded, a usable loaded car 6 tiles from her: it becomes hers for the trip; a locked one is not taken
  4 come_by_car 3: the car the trip chose is gps.lastDriveCar
  5 far_car 4: a far car brought in with her SAVED record: the record ends at the driver's door square (before: 2 tiles east of the centre)
  6 far_car 5: a helicopter: down, she is out of it at the door square, no wheel, she walks to him
  7 far_car 6: the arrival queue taken by the streamer: no fall back at 10 s, the answer comes at 20 s and the car arrives; cancelled: falls back
  8 switches off: SolFarComeCar changes nothing (come_car answers as before)
  9 Mind FetchPlayer92 (fake engine): by car near him on foot is not arrival; in the car within 3 tiles is; GPS arrived short of him re-aims;
    no usable car -> one line, follow, on foot; he moves: re-aim at a quarter of her distance (12..60); switch off -> the old FetchPlayer
 10 Mind chat block: car=last and by_car on the drive goal (mode car); a helicopter: no drive goal; the kind kept from car_where
The world is test_far_arrival.py's (WORLD and ARRIVE, read from its source, not run). Offline PASS is not Runtime PASS."""
import ast, importlib, os, re, shutil, struct, subprocess, sys, tempfile, time, types
from kahlua_env import lua51
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
HERE = os.path.dirname(os.path.abspath(__file__))
LAB_NOW = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
FIXES_NOW = os.path.join(HERE, "..", "profile", "Zomboid", "Lua", "SolFixes_LAB.txt")
MIND_NOW = r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind"
SAVE = os.path.join(HERE, "place_fixtures", "save_20261110_1947")
TONUM = r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_kahlua\tonumber_check.py"
FAIL, N = [], [0]
def ck(n, c, d=""):
    N[0] += 1
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
def run(*a): return subprocess.run([sys.executable, "-I"] + list(a), capture_output=True, text=True, encoding="utf-8")

src = open(os.path.join(HERE, "test_far_arrival.py"), encoding="utf-8").read()
consts = {n.targets[0].id: n.value.value for n in ast.parse(src).body
          if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)}
WORLD, ARRIVE = consts["WORLD"], consts["ARRIVE"]

# ---------------------------------------------------------------- 1 installers on copies
T = tempfile.mkdtemp(prefix="sol_s92_")
def fresh(tag):
    root = os.path.join(T, tag)
    cl = os.path.join(root, "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
    md = os.path.join(root, "mind")
    os.makedirs(cl); os.makedirs(md); os.makedirs(os.path.join(root, "Zomboid", "Lua"))
    for n in ("SCPersistence.lua", "SolFar.lua", "SolAuthority.lua"): shutil.copy(os.path.join(LAB_NOW, n), cl)
    shutil.copy(FIXES_NOW, os.path.join(root, "Zomboid", "Lua", "SolFixes_LAB.txt"))
    for n in ("chat_service.py", "goal_engine.py"): shutil.copy(os.path.join(MIND_NOW, n), md)
    return cl, md, os.path.join(root, "Zomboid", "Lua", "SolFixes_LAB.txt")
def snap(*ds): return {os.path.join(d, n): open(os.path.join(d, n), "rb").read() for d in ds for n in sorted(os.listdir(d)) if os.path.isfile(os.path.join(d, n))}
cl, md, fx = fresh("a")
pre = os.path.join(T, "pre"); os.makedirs(pre); shutil.copy(os.path.join(cl, "SolFar.lua"), pre)
fx_before = open(fx, encoding="utf-8").read()
r = run(os.path.join(HERE, "apply_s92_come_car_lua.py"), cl); ck("lua installer applies", r.returncode == 0, r.stdout[-300:] + r.stderr[-400:])
r = run(os.path.join(HERE, "apply_s92_come_car_mind.py"), md); ck("mind installer applies", r.returncode == 0, r.stdout[-300:] + r.stderr[-400:])
once = snap(cl, md); fx_once = open(fx, encoding="utf-8").read()
r1 = run(os.path.join(HERE, "apply_s92_come_car_lua.py"), cl); r2 = run(os.path.join(HERE, "apply_s92_come_car_mind.py"), md)
ck("both installers twice: nothing changes", r1.returncode == 0 and r2.returncode == 0 and snap(cl, md) == once and open(fx, encoding="utf-8").read() == fx_once, r1.stderr[-200:] + r2.stderr[-200:])
ck("switch file: come_by_car=on added once", fx_once.count("come_by_car=on") == 1 and ("come_by_car" in fx_before) == False or fx_before.count("come_by_car") == fx_once.count("come_by_car"), fx_once[-80:])
far_lines = lambda t: [l.strip() for l in t.splitlines() if l.strip().startswith("far_car")]
ck("switch file: far_car untouched (%s)" % far_lines(fx_once), far_lines(fx_once) == far_lines(fx_before))
for n in ("SolFar.lua", "SolFarComeCar.lua", "SolAuthority.lua"):
    s = open(os.path.join(cl, n), encoding="utf-8").read()
    ck("%s compiles in Kahlua-like Lua" % n, not isinstance(lua51.LuaRuntime().globals().loadstring(s), tuple))
    ck("%s pure ASCII" % n, all(ord(c) < 128 for c in s))
ck("SolAuthority lists come_by_car", '"come_by_car"' in open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read())
if os.path.exists(TONUM):
    def sites(f): return sorted(re.sub(r":\d+ ", " ", l) for l in run(TONUM, f).stdout.splitlines() if "tonumber" in l and "CHECK" not in l)
    ck("tonumber_check: SolFar.lua gets no new site", sites(os.path.join(pre, "SolFar.lua")) == sites(os.path.join(cl, "SolFar.lua")))
    ck("tonumber_check: SolFarComeCar.lua has no site", sites(os.path.join(cl, "SolFarComeCar.lua")) == [], sites(os.path.join(cl, "SolFarComeCar.lua")))
import py_compile
for n in ("chat_service.py", "goal_engine.py"):
    try: py_compile.compile(os.path.join(md, n), doraise=True); okc = True
    except Exception as e: okc = str(e)
    ck("%s compiles" % n, okc is True, okc)
PF, PP, PC = os.path.join(cl, "SolFar.lua"), os.path.join(cl, "SCPersistence.lua"), os.path.join(cl, "SolFarComeCar.lua")

# ---------------------------------------------------------------- the world
mod = open(os.path.join(SAVE, "global_mod_data.bin"), "rb").read()
def dbl(key, start=0):
    i = mod.index(key, start) + len(key) + 1
    return struct.unpack(">d", mod[i:i + 8])[0], i
car_x, _ = dbl(b"\x04carX"); car_y, _ = dbl(b"\x04carY"); car_id, _ = dbl(b"\x08carSqlId"); fuel, _ = dbl(b"\x07carFuel")
mass, _ = dbl(b"\x07carMass"); qual, _ = dbl(b"\x0acarQuality")
pos = mod.index(b"\x08position"); her_x, j = dbl(b"\x01x", pos); her_y, _ = dbl(b"\x01y", j)
def relocate_src(path):
    s = open(path, encoding="utf-8").read()
    body = s[s.index("function persistence.pendingRelocate"):]
    body = body[:body.index("\nend\n") + 5]
    return "PENDING = {}\nlocal pending = PENDING\nlocal persistence = {}\n" + body + "PENDING_RELOCATE = persistence.pendingRelocate\n"
EXTRA = """
SolUI.gps = {}
SW.come_by_car = COME
-- the car is a loaded vehicle with a driver's door, a key and parts, as SolFar's loadedCanGo reads it
LOCKED, KEY_IN = false, true
function CAR:getKeyId() return 77 end
function CAR:isKeysInIgnition() return KEY_IN end
function CAR:getCurrentKey() return { getKeyId = function() return 77 end } end
function CAR:isHotwired() return false end
function CAR:isHotwiredBroken() return false end
function CAR:getPartCount() return 0 end
function CAR:getSqlId() return CAR_ID end
function CAR:getDriver() return nil end
function CAR:getVehicleTowing() return nil end
function CAR:getVehicleTowedBy() return nil end
local basePart = CAR.getPartById
function CAR:getPartById(id)
    if id == "DoorFrontLeft" then return { getDoor = function() return { isLocked = function() return LOCKED end } end } end
    return basePart(self, id)
end
SurvivorCompanion.Vehicle.loadedVehicles = function() if chunkLoaded(CAR.x, CAR.y) then return { CAR } end return {} end
"""
def world(setup="", come=True, comecar=True):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute("CAR_X, CAR_Y, CAR_ID, CAR_FUEL, MASS, QUAL, HER_X, HER_Y = %r, %r, %d, %r, %r, %r, %r, %r" % (car_x, car_y, int(car_id), fuel, mass, qual, her_x, her_y))
    L.execute(relocate_src(PP))
    L.execute(WORLD)
    L.execute("COME = %s" % ("true" if come else "false"))
    L.execute(EXTRA)
    if setup: L.execute(setup)
    L.execute(open(PF, encoding="utf-8").read())
    if comecar:
        L.execute(open(PC, encoding="utf-8").read())
        L.execute("SolFarComeCar.setup()")
    return L, L.globals()
def logs(g): return [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]

# ---------------------------------------------------------------- 2 her car loaded, 70 tiles from him; she is outside his ring
PLACE = "CAR.x, CAR.y = 7275.5, 8148.5; MD.carX, MD.carY = 7275.5, 8148.5; LIVE.x, LIVE.y = 7300, 8150"
L, g = world(PLACE, come=False)
for _ in range(3): g.tick(1000)
ck("before (switch off): her loaded car 70 tiles from him -> car_not_near", tuple(g.SolUI.solFar("come_car")) == (False, "car_not_near"), tuple(g.SolUI.solFar("come_car")))
L, g = world(PLACE)
for _ in range(3): g.tick(1000)
r = tuple(g.SolUI.solFar("come_car"))
ck("after: she comes by it (%s)" % (r,), r == (True, "waiting:180"), r)
ck("after: the trip's car is the drive's car (gps.lastDriveCar)", g.SolUI.gps.lastDriveCar is not None and L.eval("SolUI.gps.lastDriveCar == CAR"))
for _ in range(185): g.tick(1000)
for _ in range(30):
    g.tick(1000); L.execute("TASKS['far_seek']()")
ck("after: she appears by it (a square found, her body back)", g.RECOVERS == 1 and any("appearing at" in l for l in logs(g)), logs(g)[-4:])

# ---------------------------------------------------------------- 3 her own car not loaded; another usable loaded car 6 tiles from her
ADOPT = "MD.carSqlId = 99; CAR_ID = 12; CAR.x, CAR.y = 7275.5, 8150.5; LIVE.x, LIVE.y = 7281, 8150"
L, g = world(ADOPT)
for _ in range(3): g.tick(1000)
r = tuple(g.SolUI.solFar("come_car"))
ck("adopt: the loaded car near her becomes hers for the trip (%s)" % (r,), r == (True, "waiting:180") and g.MD.carSqlId == 12, (r, g.MD.carSqlId, logs(g)[-3:]))
ck("adopt: said in the log only", any("a loaded car near her for the trip: 12" in l for l in logs(g)))
L, g = world(ADOPT + "; LOCKED = true")
for _ in range(3): g.tick(1000)
r = tuple(g.SolUI.solFar("come_car"))
ck("adopt: a locked car is not taken (%s)" % (r,), r[0] is False and g.MD.carSqlId == 99, (r, g.MD.carSqlId))
L, g = world(ADOPT + "; KEY_IN = false")
for _ in range(3): g.tick(1000)
r = tuple(g.SolUI.solFar("come_car"))
ck("adopt: one she cannot start is not taken (%s)" % (r,), r[0] is False and g.MD.carSqlId == 99, (r, g.MD.carSqlId))
L, g = world(ADOPT + "; LIVE.x, LIVE.y = 7320, 8150")
for _ in range(3): g.tick(1000)
r = tuple(g.SolUI.solFar("come_car"))
ck("adopt: one 44 tiles from her is not near her (%s)" % (r,), r[0] is False and g.MD.carSqlId == 99, (r, g.MD.carSqlId))

# ---------------------------------------------------------------- 8 switches off: nothing changes
L, g = world(ADOPT, come=False)
for _ in range(3): g.tick(1000)
r = tuple(g.SolUI.solFar("come_car"))
ck("switch off: no adoption, as before (%s)" % (r,), r == (False, "car_not_near") and g.MD.carSqlId == 99, (r, g.MD.carSqlId))
L0, g0 = world(ADOPT, come=False, comecar=False)
for _ in range(3): g0.tick(1000)
ck("switch off answers exactly as SolFar without SolFarComeCar", tuple(g0.SolUI.solFar("come_car")) == r)

# ---------------------------------------------------------------- 5, 6, 7 far arrival (far_car on, the inside arrival)
sys.path.insert(0, MIND_NOW)
import road_route as RR
si = RR.pickup_spot_dir(7412, 8262, 7205, 8148, 9, "car", os.path.join(MIND_NOW, "gazetteer.json.gz"), inner=True)
SPOT_IN = "%.1f,%.1f,%.0f,%.0f,in" % si
ROAD = "function ROAD(x, y) return math.abs(x - %d) <= 2 or math.abs(y - %d) <= 2 end; " % (int(si[0]), int(si[1]))
CARS = "SW.far_car = true; function solCarsNearRequest() return true end; function solCarsNearState() return 'ok' end; function solCarsNearResult() return CARLIST end; "
def carlist(*lines): return "CARLIST = '%d,%d|%s'" % (her_x, her_y, ";".join(lines))
def line(i, script, verdict="ok"): return "%d,%d,%d,4,%s,64.01,100,0,100,79868708,0,%s,0,1,0" % (i, her_x + 3, her_y, script, verdict)
SAVED = "REGISTERED = false; IDS = { 's1' }; REC = { id = 's1', x = HER_X, y = HER_Y }; PENDING.s1 = { record = { position = { x = HER_X, y = HER_Y, z = 0 } } }; "
def far_trip(setup, secs, streamer_at=None):
    L, g = world(ARRIVE + ROAD + CARS + setup)
    for _ in range(3): g.tick(1000)
    g.tick(16000); g.tick(1000)
    w = tuple(g.SolUI.solFar("car_where"))
    L.execute("CAR_ID = 6; MD.carSqlId = 99")
    r = tuple(g.SolUI.solFar("car_far:" + SPOT_IN))
    for _ in range(secs + 2): g.tick(1000)
    if streamer_at is None:
        g.tick(1000); L.execute("STREAMER()"); g.tick(1000)
    return L, g, w, r

L, g, w, r = far_trip(SAVED + carlist(line(6, "Base.SmallCar")), 180)
ck("far car with her saved record: arrived (%s %s)" % (w, r), g.AR.state == "arrived" and r == (True, "waiting:180"), (w, r, g.AR.state, logs(g)[-5:]))
p = g.PENDING.s1.record.position
dx, dy = L.eval("CAR:door()")
ck("saved record at the driver's door square (%d,%d; door %.1f,%.1f)" % (p.x, p.y, dx, dy), (p.x + 0.5 - dx) ** 2 + (p.y + 0.5 - dy) ** 2 <= 1.6, (p.x, p.y, dx, dy, logs(g)[-4:]))
ck("not 2 tiles east of the car's centre any more", not (p.x == int(g.AR.req[2]) + 2 and p.y == int(g.AR.req[3])), (p.x, p.y))
ck("the log says where her record went", any("driver's door square" in l for l in logs(g)), logs(g)[-4:])

L, g, w, r = far_trip(carlist(line(6, "Base.UH1HueyHeli")), 60)
ck("helicopter: chosen as heli, 60 s (%s %s)" % (w, r), w[1].endswith(",heli,in") and r == (True, "waiting:60"), (w, r))
for _ in range(4): g.tick(1000)
ck("helicopter: down, she is out at its door, never at the controls", g.AR.state == "arrived" and g.RECOVERS == 1 and g.WHEEL == 0 and g.LIVE.veh is None, (g.AR.state, g.RECOVERS, g.WHEEL, logs(g)[-4:]))
ck("helicopter: she walks to him (regroup)", g.ISSUED == "regroup" and any("she walks to him" in l for l in logs(g)), (g.ISSUED, logs(g)[-3:]))
ck("helicopter: poll here (the Mind's cue)", g.poll() == "here", g.poll())

L, g, w, r = far_trip(carlist(line(6, "Base.SmallCar")) + "; function solCarArriveCancel() return false end", 180, streamer_at=20)
for _ in range(15): g.tick(1000)
ck("queue taken by the streamer: no fall back at 15 s", g.F_WALK if False else not any("comes on foot" in l for l in logs(g)) and g.AR.state == "queued", (g.AR.state, logs(g)[-3:]))
L.execute("STREAMER()")
for _ in range(3): g.tick(1000)
ck("queue taken by the streamer: its answer at 18 s brings the car in", g.AR.state == "arrived" and g.LIVE.veh is not None, (g.AR.state, logs(g)[-5:]))
L, g, w, r = far_trip(carlist(line(6, "Base.SmallCar")), 180, streamer_at=99)
for _ in range(12): g.tick(1000)
ck("queue never taken (cancel succeeds): falls back on foot as before", any("comes on foot" in l for l in logs(g)) and g.AR.state == "cancelled", (g.AR.state, logs(g)[-3:]))

# ---------------------------------------------------------------- 9 Mind: FetchPlayer92
sys.path.insert(0, md)
for m in ("goal_engine",):
    if m in sys.modules: del sys.modules[m]
GE = importlib.import_module("goal_engine")
ck("the patched goal_engine is the one imported", hasattr(GE, "FetchPlayer92") and GE.PLANNERS["fetch_player"] is GE.FetchPlayer92)
class Eng:
    def __init__(self, d, on=True):
        self.lua_dir = d; self.said = []; self.tools = []; self.done = None; self.per = {}
        open(os.path.join(d, "SolFixes_LAB.txt"), "w", encoding="utf-8").write("come_by_car=%s\n" % ("on" if on else "off"))
    def perception(self): return self.per
    def wait(self, g, r): g["reason"] = r
    def fail(self, g, r): self.done = ("fail", r); return True
    def complete(self, g, r): self.done = ("complete", r); return True
    def say_once(self, g, t): self.said.append(t)
    def request_tool(self, g, tool, args=None): self.tools.append(tool); return "t%d" % len(self.tools)
    def tool_status(self, rid): return {"status": "accepted"}
    def home(self): return None
def mk(text, on=True, slots=None):
    d = tempfile.mkdtemp(dir=T)
    e = Eng(d, on)
    goal = {"intent": "fetch_player", "slots": dict({"then": "stay_with_player"}, **(slots or {})), "text": text}
    p = GE.PLANNERS["fetch_player"](e, goal)
    return e, goal, p
def per(e, sx, sy, px, py, veh=None): e.per = {"sol": {"position": {"x": sx, "y": sy}, "currentVehicle": veh}, "player": {"position": {"x": px, "y": py}}}
def gps(e, goal, **kv):
    kv["ack"] = goal.get("gpsRid")
    open(os.path.join(e.lua_dir, GE.GPS_STATE), "w", encoding="ascii").write("".join("%s=%s\n" % (k, v) for k, v in kv.items()))
def req(e): return dict(l.split("=", 1) for l in open(os.path.join(e.lua_dir, GE.GPS_REQ), encoding="utf-8").read().splitlines() if "=" in l)
try: GE.FetchPlayer92.__init__
except AttributeError: pass
e, goal, p = mk("تعالي لعندي بالسيارة")
per(e, 105, 100, 100, 100)
p.tick(1000.0)
ck("by car: the drive is sent to him", req(e).get("action") == "drive" and req(e).get("x") == "100", req(e))
gps(e, goal, result="failed", reason="walking_to_door", distance=5)
p.tick(1001.0)
ck("by car: 5 tiles from him on foot is NOT arrival (before: arrived at once, never boarded)", e.done is None, e.done)
per(e, 102, 100, 100, 100, veh={"id": 1})
gps(e, goal, result="driving", distance=2)
p.tick(1002.0)
ck("by car: in the car 2 tiles from him -> arrived, out, follow", e.done == ("complete", "arrived_at_player") and e.tools[:2] == ["exit_vehicle", "follow"], (e.done, e.tools))
e, goal, p = mk("تعالي لعندي بالسيارة")
per(e, 300, 100, 100, 100, veh={"id": 1}); p.tick(1000.0)
per(e, 108, 100, 100, 100, veh={"id": 1}); gps(e, goal, result="driving", distance=8)
p.tick(1001.0)
ck("driving, 8 tiles out: not yet (the GPS parks)", e.done is None, e.done)
p.tick(1022.0)
ck("driving, 8 tiles out and the GPS still for 20 s: arrived", e.done == ("complete", "arrived_at_player"), e.done)
e, goal, p = mk("تعالي لعندي بالسيارة")
per(e, 300, 100, 100, 100, veh={"id": 1}); p.tick(1000.0)
per(e, 130, 100, 100, 130, veh={"id": 1}); gps(e, goal, result="arrived", reason="arrived", distance=0)
p.tick(1001.0)
ck("GPS arrived where he WAS, he is 42 tiles on: re-aim, not done", e.done is None and goal["phase"] == "resolve", (e.done, goal.get("phase")))
p.tick(1002.0)
ck("re-aimed at where he is now", req(e).get("y") == "130", req(e))
e, goal, p = mk("تعالي لعندي بالسيارة")
per(e, 300, 100, 100, 100); p.tick(1000.0)
gps(e, goal, result="failed", reason="no_usable_car")
p.tick(1001.0)
ck("no usable car: one line, follow, on foot", e.done == ("complete", "coming_on_foot:no_usable_car") and "follow" in e.tools and any("جاية مشي" in s for s in e.said), (e.done, e.tools, e.said))
ck("no usable car: the line has no mechanics in it", all(not re.search(r"[A-Za-z0-9_]", s) for s in e.said[1:]), e.said)
e, goal, p = mk("تعالي لعندي بالسيارة")
per(e, 300, 100, 100, 100, veh={"id": 1}); p.tick(1000.0)
per(e, 250, 100, 100, 100, veh={"id": 1}); gps(e, goal, result="driving", distance=150)
per(e, 250, 100, 100, 100 + 30, veh={"id": 1}); p.tick(1001.0)
ck("he moved 30 tiles while she is 150 out: no re-aim yet (limit 37.5)", goal["phase"] == "driving_to_player", goal.get("phase"))
per(e, 250, 100, 100, 100 + 45, veh={"id": 1}); p.tick(1002.0)
ck("he moved 45 tiles: re-aim", goal["phase"] == "resolve", goal.get("phase"))
e, goal, p = mk("تعالي لعندي بالسيارة")
per(e, 30, 100, 100, 100, veh={"id": 1}); p.tick(1000.0)
per(e, 30, 100, 100, 113, veh={"id": 1}); gps(e, goal, result="driving", distance=70); p.tick(1001.0)
ck("near (70 out): 13 tiles is within the limit (max(12, 70/4) = 17.5): no re-aim", goal["phase"] == "driving_to_player", goal.get("phase"))
e, goal, p = mk("تعالي لعندي")
per(e, 105, 100, 100, 100); p.tick(1000.0)
gps(e, goal, result="failed", reason="walking_to_door", distance=5); p.tick(1001.0)
ck("no car words, on foot 5 tiles from him: arrived as before", e.done == ("complete", "arrived_at_player"), e.done)
e, goal, p = mk("تعالي لعندي بالسيارة", slots={"car": "last"})
per(e, 300, 100, 100, 100); p.tick(1000.0)
ck("slots car=last goes to the GPS", req(e).get("car") == "last", req(e))
e, goal, p = mk("تعالي لعندي بالسيارة", on=False)
per(e, 105, 100, 100, 100); p.tick(1000.0)
gps(e, goal, result="failed", reason="walking_to_door", distance=5); p.tick(1001.0)
ck("switch off: the old FetchPlayer (arrived at once, as before)", e.done == ("complete", "arrived_at_player"), e.done)
e, goal, p = mk("تعالي لعندي بالسيارة")
per(e, 105, 100, 100, 100); p.tick(1000.0)
gps(e, goal, result="failed", reason="walking_to_door", distance=5)
p.tick(1001.0); goal["phaseSince"] = 1000.0; p.tick(1000.0 + 400)
ck("never reached the car in 300 s: one line, on foot", e.done == ("complete", "coming_on_foot:board_timeout") and "follow" in e.tools, (e.done, e.tools))

# ---------------------------------------------------------------- 10 Mind chat block
blk = open(os.path.join(md, "chat_service.py"), encoding="utf-8").read()
ck("chat block appended once, after every earlier batch", blk.count("s92 come_by_car") == 1 and blk.rindex("s92 come_by_car") > blk.rindex("Chat._route_by_model"))
NS = {}
code = blk[blk.index("# ---------------------------------------------------------------- s92 come_by_car"):]
class Chat:
    def _far_car_spot(self):
        r = NS["run_action"](self.dir, "sol_far", "car_where", wait=2.5)
        return ("car_far:1,2,3,4,in", None)
    def _far_watch(self): self.base_watch = True
def fake_run(d, action, option=None, wait=2.5):
    CALLS.append((action, option))
    if option == "car_where": return {"ok": True, "reason": "car:7412,8262,7205,8148,9,heli,in"}
    if option == "poll": return {"ok": True, "reason": POLL[0]}
    return {"ok": True, "reason": "x"}
CALLS, POLL = [], ["here"]
class IEf:
    @staticmethod
    def make_goal(i, s, source="", text=""): return {"intent": i, "slots": dict(s)}
import threading
NS.update(Chat=Chat, run_action=fake_run, re=re, time=time, IE=IEf, FAR_AT_EDGE="صرت قريبة", fix_on=lambda d, n: SWON[0])
SWON = [True]
exec(code, NS)
class Me(NS["Chat"]):
    def __init__(self): self.dir = T; self.lock = threading.Lock(); self.hist = []; self.logs = []
    def _save(self): pass
    def publish(self): pass
    def log(self, m): self.logs.append(m)
c = Me()
c._far_car_spot()
ck("the kind is kept from car_where (heli)", c._far_kind_s92 == "heli", getattr(c, "_far_kind_s92", None))
c._far_waiting = "car_far"; c._far_watch()
ck("helicopter down and here: no drive goal, her near line, the watch ends", c._far_waiting is False and not getattr(c, "base_watch", False) and c.hist and c.hist[-1]["text"] == "صرت قريبة", (c._far_waiting, c.hist))
c = Me(); c._far_waiting = "car"; c._far_watch()
ck("mode car: the drive goal takes that car (car=last) and is by car", c._far_drive_goal["slots"].get("car") == "last" and c._far_drive_goal["slots"].get("by_car") == "1" and c.base_watch)
c = Me(); c._far_waiting = "car_far"; c._far_kind_s92 = "car"; c._far_watch()
ck("mode car_far (a car): by car, no car=last (she is at its wheel), the old watch runs", c._far_drive_goal["slots"].get("by_car") == "1" and "car" not in c._far_drive_goal["slots"] and c.base_watch)
SWON[0] = False
c = Me(); c._far_waiting = "car_far"; c._far_kind_s92 = "heli"; c._far_watch()
ck("switch off: the old watch, untouched", c.base_watch and getattr(c, "_far_drive_goal", None) is None)

print("%d checks, %d failed" % (N[0], len(FAIL)))
for f in FAIL: print("  FAILED:", f)
shutil.rmtree(T, ignore_errors=True)
sys.exit(1 if FAIL else 0)

"""Offline tests for s95b (apply_s95b_station_approach.py, apply_s95b_tank_mind.py, S95bPlanReplay.java).
usage: set PYTHONIOENCODING=utf-8 & python test_s95b_station_approach.py
  1 installers on COPIES of the live lab files and the live Mind: apply, twice change nothing, Kahlua-like compile, ASCII,
    tonumber_check, py_compile, the live files untouched
  2 the 10:26 lab failure with the SHIPPED Java planner (S95bPlanReplay, sources 05_TOOLS/sol_nav_java) on the forecourt of
    the 10:26 perception dumps, the car where it stood (7279.16,8179.49, facing north): the three logged poses fail
  3 the same, driven by the Lua: the s95 SolStationSurvey (git e1f3da6) and the s95b one, each in the game mocks of
    test_s95_station_refuel.py, with every solNavPlan answered by the real planner (java "serve"). The game adds an off-road
    cost the dumps do not keep, so offline a plan that needs more than MARGIN of the 60000 states is counted as the game's
    no_path_found (pose 3: 59335). Old: 3 of 3 fail -> survey_drive_failed, as logged. New: parked, every plan well inside.
  4 the tank of THE car she would fill (Mind): the 10:27:38 "مليانة (100%)" reproduced with the old car_is_full, then
    96.8% / 99.2% / 50% on the model branch and on the errand path (no drive at 99%+, "فيها 96%، رح كمّلها" at 90-99%)
Offline PASS is not Runtime PASS."""
import ast, json, math, os, py_compile, re, shutil, subprocess, sys, tempfile, importlib
from kahlua_env import lua51
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LAB_NOW = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
LUA_DIR = os.path.join(HERE, "..", "profile", "Zomboid", "Lua")
MIND_NOW = os.path.join(ROOT, "05_TOOLS", "sol_mind")
NAV_SRC = os.path.join(ROOT, "05_TOOLS", "sol_nav_java", "localplayerbody")
TONUM = os.path.join(ROOT, "05_TOOLS", "sol_kahlua", "tonumber_check.py")
DUMP_A = os.path.join(LUA_DIR, "SolPerception_1794389185383.txt")     # 10:26:25, the car standing where the three plans started
DUMP_B = os.path.join(LUA_DIR, "SolPerception_1794389223475.txt")     # 10:27:03, the forecourt
MARGIN = 50000
FAIL, N = [], [0]
def ck(n, c, d=""):
    N[0] += 1
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
def run(*a): return subprocess.run([sys.executable, "-I"] + list(a), capture_output=True, text=True, encoding="utf-8")

# ---------------------------------------------------------------- 1 installers on copies
T = tempfile.mkdtemp(prefix="sol_s95b_")
LIVE = {n: open(os.path.join(LAB_NOW, n), "rb").read() for n in ("SolFuel.lua", "SolMoveCheck.lua", "SolStationSurvey.lua")}
LIVE_MIND = {n: open(os.path.join(MIND_NOW, n), "rb").read() for n in ("goal_engine.py", "chat_service.py")}
OLD_SURVEY = subprocess.run(["git", "-C", ROOT, "show", "e1f3da6:07_TEST/SOL_LAB/_pending_refuel/SolStationSurvey.lua"], capture_output=True).stdout
STAGED_S95B = open(os.path.join(HERE, "SolStationSurvey.lua"), "rb").read()
ck("live LAB has the staged s95b survey; old baseline is available for replay", LIVE["SolStationSurvey.lua"].replace(b"\r\n", b"\n") == STAGED_S95B.replace(b"\r\n", b"\n") and len(OLD_SURVEY) > 1000)
OLD, NEW = os.path.join(T, "old"), os.path.join(T, "new")
for d in (OLD, NEW):
    os.makedirs(d)
    for n, b in LIVE.items(): open(os.path.join(d, n), "wb").write(b)
    open(os.path.join(d, "SolStationSurvey.lua"), "wb").write(OLD_SURVEY)
r = run(os.path.join(HERE, "apply_s95b_station_approach.py"), NEW); ck("lua installer applies", r.returncode == 0, r.stdout[-300:] + r.stderr[-500:])
once = open(os.path.join(NEW, "SolStationSurvey.lua"), "rb").read()
r = run(os.path.join(HERE, "apply_s95b_station_approach.py"), NEW)
ck("lua installer twice: nothing changes", r.returncode == 0 and open(os.path.join(NEW, "SolStationSurvey.lua"), "rb").read() == once)
e = os.path.join(T, "empty"); os.makedirs(e)
ck("lua installer refuses where s95 is not installed", run(os.path.join(HERE, "apply_s95b_station_approach.py"), e).returncode != 0)
s = once.decode("utf-8")
ck("SolStationSurvey.lua (s95b) compiles in Kahlua-like Lua", not isinstance(lua51.LuaRuntime().globals().loadstring(s), tuple))
ck("SolStationSurvey.lua (s95b) is pure ASCII", all(ord(c) < 128 for c in s))
rt = run(TONUM, os.path.join(NEW, "SolStationSurvey.lua"))
ck("tonumber_check passes on SolStationSurvey.lua (s95b)", rt.returncode == 0, rt.stdout[-400:] + rt.stderr[-200:])
ck("only SolStationSurvey.lua changes (SolFuel / SolMoveCheck as installed)", all(open(os.path.join(NEW, n), "rb").read() == LIVE[n] for n in ("SolFuel.lua", "SolMoveCheck.lua")))
MD = os.path.join(T, "mind"); os.makedirs(MD)
for n in os.listdir(MIND_NOW):
    if n.endswith(".py"): shutil.copy(os.path.join(MIND_NOW, n), MD)
r = run(os.path.join(HERE, "apply_s95b_tank_mind.py"), MD); ck("mind installer applies", r.returncode == 0, r.stdout[-300:] + r.stderr[-800:])
m1 = {n: open(os.path.join(MD, n), "rb").read() for n in LIVE_MIND}
r = run(os.path.join(HERE, "apply_s95b_tank_mind.py"), MD)
ck("mind installer twice: nothing changes", r.returncode == 0 and all(open(os.path.join(MD, n), "rb").read() == b for n, b in m1.items()), r.stderr[-300:])
for n in LIVE_MIND:
    try: py_compile.compile(os.path.join(MD, n), doraise=True); okc = True
    except Exception as ex: okc = ex
    ck("%s compiles" % n, okc is True, okc)

# ---------------------------------------------------------------- 2 the shipped planner on the 10:26 forecourt
JOUT = os.path.join(T, "java")
jc = subprocess.run(["javac", "-d", JOUT, os.path.join(NAV_SRC, "SolNavPlanner.java"), os.path.join(NAV_SRC, "SolNavTrack.java"), os.path.join(HERE, "S95bPlanReplay.java")], capture_output=True, text=True)
ck("S95bPlanReplay builds against the shipped planner sources", jc.returncode == 0, jc.stderr[-600:])
def nodes(line): m = re.search(r"(\d+) nodes", line); return int(m.group(1)) if m else -1
out = subprocess.run(["java", "-cp", JOUT, "localplayerbody.S95bPlanReplay", DUMP_A, DUMP_B, "old"], capture_output=True, text=True).stdout.splitlines()
print("  " + "\n  ".join(out))
pl = [l for l in out if l.startswith("pose ")]
ck("10:26 replay: start = the car's poly (7279.16,8179.49, facing north), 3 other cars", out and "7279.16,8179.49" in out[0] and "3 other cars" in out[0], out[:1])
ck("10:26 replay: pose 1 (7307.3,8181.0 facing west) -> no_path_found, all 60000 states spent", len(pl) == 3 and "no_path_found" in pl[0] and nodes(pl[0]) == 60000, pl)
ck("10:26 replay: pose 2 (7315.3,8181.0 facing west) -> no_path_found, all 60000 states spent", len(pl) == 3 and "no_path_found" in pl[1] and nodes(pl[1]) == 60000, pl)
ck("10:26 replay: pose 3 (7311.0,8180.7 facing south) needs more than %d of 60000 states (the game, with its off-road cost, ran out)" % MARGIN, len(pl) == 3 and nodes(pl[2]) > MARGIN, pl)
out = subprocess.run(["java", "-cp", JOUT, "localplayerbody.S95bPlanReplay", DUMP_A, DUMP_B, "turnback"], capture_output=True, text=True).stdout.splitlines()
pl = [l for l in out if l.startswith("pose ")]
ck("not the reverse limit: with solNavMayTurnBack the far poses still spend all 60000 states", len(pl) == 3 and nodes(pl[0]) == 60000 and nodes(pl[1]) == 60000, pl)
out = subprocess.run(["java", "-cp", JOUT, "localplayerbody.S95bPlanReplay", DUMP_A, DUMP_B, "old", "-", "7322,8185,0,-1"], capture_output=True, text=True).stdout.splitlines()
pl = [l for l in out if l.startswith("pose ")]
ck("not the goal: the same three poses from 8 m east of the islands are found (goals free, convention right)", len(pl) == 3 and all(l.split("-> ")[1].startswith("found") for l in pl), pl)

# ---------------------------------------------------------------- 3 the Lua with the real planner
SRC95 = open(os.path.join(HERE, "test_s95_station_refuel.py"), encoding="utf-8").read()
WANT = {"MOCK", "FORECOURT", "PUMPS_REAL", "PARKED_REAL", "SMALL", "env", "forecourt", "her_car", "fuel", "logs", "park_errand"}
NS = {"lua51": lua51, "os": os, "CL": NEW}
for node in ast.parse(SRC95).body:
    names = [t.id for t in node.targets if isinstance(t, ast.Name)] if isinstance(node, ast.Assign) else [node.name] if isinstance(node, ast.FunctionDef) else []
    if set(names) & WANT: exec(compile(ast.Module(body=[node], type_ignores=[]), "test_s95", "exec"), NS)
ck("the s95 game mocks are loaded from test_s95_station_refuel.py", all(k in NS for k in WANT))
own = None
for line in open(DUMP_A, encoding="utf-8"):
    if line.startswith("car "): own = [float(v) for v in re.split(r"[ ,]", line[4:].strip())]; break
CX, CY = sum(own[0::2]) / 4, sum(own[1::2]) / 4
HX, HY = (own[0] + own[2] - own[4] - own[6]) / 2, (own[1] + own[3] - own[5] - own[7]) / 2
HN = math.hypot(HX, HY); HX, HY = HX / HN, HY / HN
JAVA = subprocess.Popen(["java", "-cp", JOUT, "localplayerbody.S95bPlanReplay", DUMP_A, DUMP_B, "serve"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
def real_plan(sx, sy, hx, hy, gx, gy, ghx, ghy, tb):
    JAVA.stdin.write("%r %r %r %r %r %r %r %r %d\n" % (float(sx), float(sy), float(hx), float(hy), float(gx), float(gy), float(ghx), float(ghy), int(tb)))
    JAVA.stdin.flush()
    return JAVA.stdout.readline().strip()
PLANS = []
def py_plan(sx, sy, hx, hy, gx, gy, ghx, ghy, tb):
    why = real_plan(sx, sy, hx, hy, gx, gy, ghx, ghy, tb)
    ok = why.startswith("found") and nodes(why) <= MARGIN
    PLANS.append(((round(gx, 1), round(gy, 1), round(ghx, 2), round(ghy, 2), int(tb)), why, ok))
    return "ok" if ok else ("no_path_found" if why.startswith("found") or why.startswith("no_path_found") else why.split(" ")[0])
REAL_NAV = """
function solNavMayTurnBack() NAV.tb = true end
function solNavPlan(car, sx, sy, hx, hy, gx, gy, ghx, ghy, wb, k)
    NAV.plans = NAV.plans + 1
    local why = PYPLAN(sx, sy, hx, hy, gx, gy, ghx, ghy, NAV.tb and 1 or 0)
    NAV.tb = false
    NAV.goal = { car = car, x = gx, y = gy, fx = ghx, fy = ghy, i = NAV.plans, why = why }
    NAV.goals[#NAV.goals + 1] = NAV.goal
    NAV.state, NAV.n = "capturing", 0
    return true
end
function solNavState()
    NAV.n = NAV.n + 1
    if NAV.state == "capturing" and NAV.n >= 2 then NAV.state = (NAV.goal.why == "ok") and "ready" or ("failed:" .. NAV.goal.why) end
    if NAV.state == "following" and NAV.n >= 3 then
        local c = NAV.goal.car
        c.cx, c.cy, c.fx, c.fy = NAV.goal.x, NAV.goal.y, NAV.goal.fx, NAV.goal.fy
        NAV.state = "done"
    end
    return NAV.state
end
"""
LOG_POSES = ["pose 1: pump 7308,8178, car centre 7307.3,8181.0 facing -1,0, she stands at 7308,8179",
             "pose 2: pump 7316,8178, car centre 7315.3,8181.0 facing -1,0, she stands at 7316,8179",
             "pose 3: pump 7308,8178, car centre 7311.0,8180.7 facing 0,1, she stands at 7309,8179"]
def lab_1026(d):
    del PLANS[:]
    L = NS["env"](d=d)
    L.globals().PYPLAN = py_plan
    L.execute(REAL_NAV)
    NS["forecourt"](L, extra_cars=[(7317.5, 8201.38, 0, 1, 2.12, 0.85)])
    NS["her_car"](L, CX, CY, HX, HY, NS["SMALL"])
    L.execute("PLAYER.veh = CAR; PLAYER.x, PLAYER.y = CAR.cx, CAR.cy")
    r, said = NS["park_errand"](L)
    return L, r, [l for l in NS["logs"](L) if "SolStation" in l]

L, r, lg = lab_1026(OLD)
print("  old: " + "\n  old: ".join(lg)); print("  old plans: %s" % PLANS)
ck("s95 Lua on the 10:26 forecourt: the same three poses as the game log, in the same order",
   [l for l in lg if re.match(r"\[SolStation\] pose \d: pump", l)] == ["[SolStation] " + p + (", lane open both ends" if i < 2 else "") for i, p in enumerate(LOG_POSES)], lg)
ck("s95 Lua: the same reasons as the game log ('cap_far_from_pump', 17 cap not facing, 4 body on something)",
   any("from where the car stands: cap_far_from_pump" in l for l in lg) and any("3 poses beside 2 pumps (left out: 0 out of the hose's reach, 17 cap not facing the pump across a free square, 4 body on something" in l for l in lg), lg)
ck("s95 Lua + real planner: 3 plans, 3 failures, survey_drive_failed (3 plans failed) - the 10:26 log reproduced",
   r == (False, "survey_drive_failed") and len(PLANS) == 3 and not any(p[2] for p in PLANS) and any("3 plans failed" in l for l in lg), (r, PLANS))
OLDPLANS = list(PLANS)

L, r, lg = lab_1026(NEW)
print("  new: " + "\n  new: ".join(lg)); print("  new plans: %s" % PLANS)
c = L.globals().CAR
ck("s95b Lua + real planner: parked, and the game's own pump test passes from the stop", r == (True, "near"), (r, lg[-4:]))
ck("s95b: pose 1 is the logged pose 1, reached by an approach point then the pose", any(LOG_POSES[0] in l for l in lg) and any("first to" in l for l in lg) and any("at the approach point" in l for l in lg), lg)
ck("s95b: every plan she asked for was found well inside the planner's limit (<= %d states)" % MARGIN, PLANS and all(p[2] for p in PLANS), PLANS)
ck("s95b: the car stands at pose 1 facing west", abs(c.cx - 7307.3) < 0.15 and abs(c.cy - 8181.0) < 0.15 and c.fx == -1, (c.cx, c.cy, c.fx, c.fy))
# each logged pose by itself: its first approach point is found, then the pose from there (backing in through the lane ahead)
L = NS["env"](d=NEW); L.globals().PYPLAN = py_plan; L.execute(REAL_NAV)
NS["forecourt"](L, extra_cars=[(7317.5, 8201.38, 0, 1, 2.12, 0.85)]); NS["her_car"](L, CX, CY, HX, HY, NS["SMALL"])
L.execute("PLAYER.veh = CAR; W_ = SolStationSurvey.live(SolStationSurvey.world(7308, 8178, false), CAR, false); G_ = SolStationSurvey.geometry(CAR, SOL)")
L.execute("P_ = SolStationSurvey.poses(W_, G_, { x = CAR.cx, y = CAR.cy, hx = CAR.fx, hy = CAR.fy }, {})")
for i, want in enumerate(LOG_POSES):
    p = L.eval("P_[%d]" % (i + 1))
    ap = L.eval("SolStationSurvey.approaches(W_, G_, P_[%d], { x = CAR.cx, y = CAR.cy })" % (i + 1))
    a = ap[1] if ap is not None and len(ap) > 0 else None
    if a is None: ck("pose %d: an approach point exists" % (i + 1), False, "none"); continue
    w1 = real_plan(CX, CY, HX, HY, a.cx, a.cy, a.fx, a.fy, 0)
    w2 = real_plan(a.cx, a.cy, a.fx, a.fy, p.cx, p.cy, p.fx, p.fy, 1 if a.turnBack else 0)
    ck("pose %d (%.1f,%.1f facing %d,%d): approach %.1f,%.1f (%s) found, then the pose found, both <= %d states" % (i + 1, p.cx, p.cy, p.fx, p.fy, a.cx, a.cy, "backs in" if a.turnBack else "drives in", MARGIN),
       w1.startswith("found") and w2.startswith("found") and nodes(w1) <= MARGIN and nodes(w2) <= MARGIN, (w1, w2))
JAVA.stdin.close(); JAVA.wait(timeout=30)

# hot reload in a running game: a second load of the file adds no second tick and keeps the job table
L = NS["env"](d=NEW)
n1 = len(L.globals().TICKS)
L.execute(open(os.path.join(NEW, "SolStationSurvey.lua"), encoding="utf-8").read())
ck("reloading SolStationSurvey.lua in a running game adds no second OnTick (the first tick drives M.step of the same table)", len(L.globals().TICKS) == n1)
L = NS["env"](d=OLD); n1 = len(L.globals().TICKS)
L.execute(open(os.path.join(NEW, "SolStationSurvey.lua"), encoding="utf-8").read())
ck("loading s95b over the running s95 (the lab now): no second tick, the old tick now runs the new step", len(L.globals().TICKS) == n1 and L.eval('SolStationSurvey.VERSION') == "0.2.0" and L.eval("type(SolStationSurvey.approaches)") == "function")

# the near case is unchanged: within 8 m no approach point
L = NS["env"](d=NEW); NS["forecourt"](L); NS["her_car"](L, 7300.5, 8181.0, 1, 0, NS["SMALL"]); L.execute("PLAYER.veh = CAR")
r, said = NS["park_errand"](L)
lgn = [l for l in NS["logs"](L) if "SolStation" in l]
ck("near the pumps (car 7 m off): no approach point, the pose straight (as s95)", r == (True, "near") and not any("first to" in l for l in lgn), (r, lgn[-4:]))
# a failed approach plan -> the next approach -> the pose straight -> the next pose (mock planner)
L = NS["env"](d=NEW); NS["forecourt"](L); NS["her_car"](L, CX, CY, HX, HY, NS["SMALL"]); L.execute("PLAYER.veh = CAR")
L.execute("for i = 1, 4 do NAV.failAt[i] = true end")
r, said = NS["park_errand"](L)
lgf = [l for l in NS["logs"](L) if "SolStation" in l]
ck("approaches 1-3 and the straight plan of pose 1 fail: then pose 2, parked", r == (True, "near") and sum("approach" in l and "failed:" in l for l in lgf) == 3 and any(l.startswith("[SolStation] pose 2: pump") for l in lgf), (r, lgf))

# ---------------------------------------------------------------- 4 the tank of the car she would fill
sys.path.insert(0, MD)
for m in list(sys.modules):
    if m in ("goal_engine", "chat_service") or m.startswith("world_"): del sys.modules[m]
GE = importlib.import_module("goal_engine")
try: CS = importlib.import_module("chat_service"); csok = True
except Exception as ex: CS, csok = None, ex
ck("the patched chat_service imports", csok is True, csok)
def snap(fuel, sol_in=True, extra=()):
    vs = [{"name": "SmallCar", "x": 7279, "y": 8179, "id": 11, "fuel": fuel, "fuelMax": 59}] + list(extra)
    return {"player": {"x": 7308.4, "y": 8176.6, "inVehicle": True}, "sol": {"x": 7279.2, "y": 8179.5, "inVehicle": sol_in}, "vehicles": vs}
STATION_CAR = {"name": "CarNormal", "x": 7308, "y": 8176, "id": 30, "fuel": 66.0, "fuelMax": 66}       # the full car at pump 1, where he was at 10:27
s1027 = snap(57.1, extra=[STATION_CAR])
if CS:
    ck("10:27:38 reproduced: the old check (car nearest HIM) says 100% while her car has 57.1 / 59", CS.car_is_full_s95(s1027) == 100, CS.car_is_full_s95(s1027))
    ck("10:27:38 fixed: her car is 96%, not full: the model branch lets the errand go", CS.car_is_full(s1027) is None, CS.car_is_full(s1027))
    ck("model branch at 99.2% (58.53 / 59): she refuses at once with the true number",
       CS.car_is_full(snap(58.53)) == 99 and CS.TANK_FULL_SAY % 99 == "السيارة مليانة (99%)، ما بدها تعبية.", CS.car_is_full(snap(58.53)))
    ck("model branch at 50%: not full", CS.car_is_full(snap(29.5)) is None)
    src = open(os.path.join(MD, "chat_service.py"), encoding="utf-8").read()
    ck("model branch: refuel_at_station uses car_is_full and the shared line", "full = car_is_full(snap)" in src and "return TANK_FULL_SAY % full" in src)
ck("tank_gate: 57.121 / 59 (the GPS panel's 96.8%) -> top_up 96", GE.tank_gate({"sol": {"x": 0, "y": 0, "inVehicle": True}, "vehicles": [{"x": 0, "y": 0, "fuel": 57.121, "fuelMax": 59}]}) == ("top_up", 96))
ck("tank_gate: 99.2% -> full 99; 50% -> go 50; no car near her -> unknown",
   GE.tank_gate(snap(58.53)) == ("full", 99) and GE.tank_gate(snap(29.5)) == ("go", 50) and GE.tank_gate({"sol": {"x": 0, "y": 0}, "vehicles": [STATION_CAR]}) == (None, None))
ck("her car, not his: him beside a full car, her in hers -> her tank", GE.her_tank(s1027)[:2] == (57.1, 59))
ck("on foot: her last car within 15 counts (SolFuel's reach), a car 20 off does not",
   GE.her_tank({"sol": {"x": 0, "y": 0, "inVehicle": False}, "vehicles": [{"x": 10, "y": 5, "fuel": 30, "fuelMax": 60}]})[2] == 50.0
   and GE.her_tank({"sol": {"x": 0, "y": 0, "inVehicle": False}, "vehicles": [{"x": 20, "y": 0, "fuel": 30, "fuelMax": 60}]}) is None)
RE = GE.PLANNERS["refuel_errand"]
class Eng:
    def __init__(self, d): self.lua_dir = d; self.said = []; self.done = None
    def perception(self): return {"sol": {"currentVehicle": 1}}
    def wait(self, g, r): g["reason"] = r
    def fail(self, g, r): self.done = ("fail", r); return True
    def complete(self, g, r): self.done = ("complete", r); return True
    def say_once(self, g, t): self.said.append(t)
def errand(fuel, target="car", extra=()):
    d = tempfile.mkdtemp(prefix="sol_s95b_snap_", dir=T)
    open(os.path.join(d, "SolWorld_Snapshot.txt"), "w", encoding="ascii").write(json.dumps(snap(fuel, extra=extra)))
    e = Eng(d)
    goal = {"intent": "refuel_errand", "slots": {"target": target, "transport": "car"}, "phase": "leave", "phaseSince": 100.0,
            "destFields": {"x": 7316, "y": 8178, "name": "Gas station"}, "station": {"x": 7316, "y": 8178}}
    p = RE(e, goal)
    drives = []
    p._gps = lambda f: drives.append(f)
    p._action = lambda *a, **k: "r1"
    p._pump_in_reach = lambda g, s: False
    p._clear_own_target = lambda: None
    p.tick(101.0)
    return e, goal, drives
e, goal, drives = errand(57.121, extra=[STATION_CAR])
ck("errand path, 96.8% (the 10:25 order): she says 'فيها 96%، رح كمّلها.' and drives out", e.said == ["فيها 96%، رح كمّلها."] and len(drives) == 1 and goal["phase"] == "driving_out" and e.done is None, (e.said, drives, goal.get("phase")))
e, goal, drives = errand(58.53)
ck("errand path, 99.2%: 'السيارة مليانة (99%)، ما بدها تعبية.', no drive, the errand ends", e.said == ["السيارة مليانة (99%)، ما بدها تعبية."] and drives == [] and e.done == ("complete", "tank_full"), (e.said, drives, e.done))
e, goal, drives = errand(29.5)
ck("errand path, 50%: she just goes ('ماشي، رايحة عالكازية.')", e.said == ["ماشي، رايحة عالكازية."] and len(drives) == 1 and e.done is None, (e.said, drives))
e, goal, drives = errand(58.53, target="both")
ck("errand path, 99.2% with a can too: the car is left, she still goes for the can", goal["slots"]["target"] == "can" and len(drives) == 1 and e.said[0].startswith("السيارة مليانة (99%)"), (e.said, goal["slots"]))
ck("live lab files and live Mind untouched", all(open(os.path.join(LAB_NOW, n), "rb").read() == b for n, b in LIVE.items())
   and all(open(os.path.join(MIND_NOW, n), "rb").read() == b for n, b in LIVE_MIND.items()))

print("")
print("%d checks, %d failed" % (N[0], len(FAIL)))
if FAIL: print("FAILED: " + "; ".join(FAIL)); sys.exit(1)
print("ALL PASS (offline; not a runtime PASS)")

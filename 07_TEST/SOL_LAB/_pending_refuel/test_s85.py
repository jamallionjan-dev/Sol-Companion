"""s85: apply_s85_lua.py + apply_s85_mind.py on temporary copies (idempotent), SolExitFirst.lua under the game's Lua rules, the GPS
ready line, the card within budget with every switch on (card_check.py's own numbers), several actions in one reply (in order,
each finished before the next, a refusal ends the chain), the exit-first lines, and the far_report line in the chat once.
Nothing live is touched.
Run: set PYTHONIOENCODING=utf-8 & python test_s85.py [sol_mind dir] [client dir]   (defaults: 05_TOOLS/sol_mind, the lab client; read only)
Offline PASS is not Runtime PASS."""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, HERE)
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)


# ================================================================ child: the patched Mind with mocks
def mind_child(mind):
    sys.path.insert(0, mind)
    import time as T
    import chat_service as CS, model_router as MR, reply_gate as RG, providers as P, settings_service as SS, world_knowledge as W
    import farm_talk as FT
    ck("child: the patched copy is what got imported", os.path.dirname(os.path.abspath(CS.__file__)) == os.path.abspath(mind))
    # --- parse
    p = MR.parse('{"actions":[{"action":"sol_engine","args":{"option":"off"}},{"action":"exit_car"}],"speech":""}')
    ck("parse: 'actions' reads as its first action", p == {"action": "sol_engine", "args": {"option": "off"}, "speech": ""}, p)
    ck("parse: ... and the whole list waits in LAST_STEPS", MR.LAST_STEPS == [{"action": "sol_engine", "args": {"option": "off"}}, {"action": "exit_car", "args": {}}], MR.LAST_STEPS)
    p = MR.parse('{"action":"follow","speech":""}')
    ck("parse: the one-action form is unchanged, no steps", p == {"action": "follow", "args": {}, "speech": ""} and MR.LAST_STEPS == [], (p, MR.LAST_STEPS))
    ck("parse: an empty or broken actions list is unreadable", MR.parse('{"actions":[]}') is None and MR.parse('{"actions":[{"x":1}]}') is None)
    MR.parse('{"actions":[{"action":"a"},{"action":"b"},{"action":"c"},{"action":"d"}]}')
    ck("parse: at most %d steps" % MR.MAX_STEPS_S85, len(MR.LAST_STEPS) == MR.MAX_STEPS_S85)

    # --- the chat with mocks
    SS.load_config = lambda: {"source": "local", "provider": "custom", "model": "test", "base": ""}
    W.situation_text = lambda s, m: "world"
    CS.MA.answer = lambda *a, **k: None
    CS.MA.known_names = lambda *a, **k: []
    CS.time.sleep = lambda s: None
    CS.load_actions = lambda d: [{"id": i, "kind": "sol"} for i in ("sol_engine", "sol_headlights", "sol_horn")]
    TMPD = tempfile.mkdtemp(prefix="sol_s85_child_")
    SEQ, LOG, LATER, BUBBLE = [], [], [], []
    GAME = {"answer": lambda a, o: {"ok": True, "reason": ""}}
    def base_run(d, action, option=None, wait=3.0):
        SEQ.append(("game", action, option)); return GAME["answer"](action, option)
    CS._run_action_s85_base = base_run
    REPLY = {"v": ""}
    P.chat = lambda *a, **k: REPLY["v"]
    WORLD = {"in_car": 0}
    def world():
        sol = {"x": 1, "y": 1}
        if WORLD["in_car"] > 0:
            WORLD["in_car"] -= 1; sol["currentVehicle"] = "car"
        return {"sol": sol, "player": {"x": 1, "y": 1}}, None

    def chat():
        c = CS.Chat.__new__(CS.Chat)
        c.dir, c.log, c._forced, c._sheet = TMPD, LOG.append, None, None
        c._world = world
        c.gps_state = lambda: {}
        def pre(h, s, m):                      # the Mind's own order for a COMMANDS action; go_home_rest is the farm order (as _farm_orders)
            text = h[-1]["text"]
            cmd = next((k for k, v in MR.COMMANDS.items() if v[1] == text), None)
            SEQ.append(("pre", cmd))
            if cmd == "go_home_rest":
                r = CS.run_action(c.dir, "sol_farm", "home"); c._forced = FT.reply_for("home", r)
            return ["ran"]
        c._pre_intents = pre
        c._receipt = lambda: "تكرم."
        c._player_takes_over = lambda a: None
        c._remember_action = lambda a, o: None
        c._memory_text = lambda s, m: "لا شيء."
        c._gate_context = lambda h, a, k, n=(): RG.Context(h[-1]["text"], [], [], k, False, (), [])
        c._model_first = lambda: True
        c._say_later = LATER.append
        return c
    def say(text, reply):
        del SEQ[:], LOG[:], LATER[:]
        REPLY["v"] = reply
        c = chat()
        return c, c._route_by_model([{"role": "user", "text": text}], SS.load_config(), "", {}, None)

    # several actions, in order, the next after the first is done
    WORLD["in_car"] = 3
    c, r = say("طفي المحرك ونزلي", '{"actions":[{"action":"sol_engine","args":{"option":"off"}},{"action":"exit_car"}],"speech":""}')
    ck("steps: engine off, then out of the car, in that order", SEQ == [("game", "sol_engine", "off"), ("pre", "exit_car")], SEQ)
    ck("steps: the route log names both", any("2 steps: sol_engine then exit_car" in l for l in LOG), LOG)
    WORLD["in_car"] = 3
    c, r = say("نزلي من السيارة وتعالي لعندي", '{"actions":[{"action":"exit_car"},{"action":"come_foot"}],"speech":""}')
    ck("steps: out of the car, then come", SEQ == [("pre", "exit_car"), ("pre", "come_foot")], SEQ)
    ck("steps: come waited until the snapshot showed her out (3 looks in the car)", WORLD["in_car"] == 0, WORLD)
    WORLD["in_car"] = 10 ** 6
    import time as _tt
    real_time = _tt.time
    clock = {"t": 1000.0}
    CS.time.time = lambda: clock.__setitem__("t", clock["t"] + 1.0) or clock["t"]
    try: c, r = say("نزلي من السيارة وتعالي لعندي", '{"actions":[{"action":"exit_car"},{"action":"come_foot"}],"speech":""}')
    finally: CS.time.time = real_time
    WORLD["in_car"] = 0
    ck("steps: she never shows out: after %ds the next order still goes (the game gets her out first)" % CS.STEP_WAIT_S85["exit_car"],
       SEQ == [("pre", "exit_car"), ("pre", "come_foot")] and any("not seen done in time" in l for l in LOG), (SEQ, LOG[-3:]))
    GAME["answer"] = lambda a, o: {"ok": False, "reason": "not_in_vehicle"} if a == "sol_engine" else {"ok": True, "reason": ""}
    c, r = say("طفي المحرك ونزلي", '{"actions":[{"action":"sol_engine","args":{"option":"off"}},{"action":"exit_car"}],"speech":""}')
    ck("steps: a refusal ends the chain, he hears why", SEQ == [("game", "sol_engine", "off")] and r == CS.reason_ar("not_in_vehicle"), (SEQ, r))
    GAME["answer"] = lambda a, o: {"ok": True, "reason": ""}
    c, r = say("طفي المحرك وطيري", '{"actions":[{"action":"sol_engine","args":{"option":"off"}},{"action":"fly"}],"speech":""}')
    ck("steps: a second action that is not on the list runs nothing more, the first one's line stays", SEQ == [("game", "sol_engine", "off")] and r != CS.ASK_AGAIN_S82, (SEQ, r))
    c, r = say("الحقيني", '{"action":"follow","speech":""}')
    ck("one action: as before", SEQ == [("pre", "follow")] and r == "تكرم.", (SEQ, r))

    # exit first: the game gets her out, she says so now and the order's line when it ran
    GAME["answer"] = lambda a, o: {"ok": True, "reason": "leaving_car_first"} if a == "sol_farm" else {"ok": True, "reason": "pending"}
    c, r = say("رتاحي بالبيت", '{"action":"go_home_rest","speech":""}')
    ck("exit first: 'رتاحي بالبيت' in the car -> 'ماشي، بنزل من السيارة أول.'", r == "ماشي، بنزل من السيارة أول." and c._exit_waiting["action"] == "sol_farm", (r, getattr(c, "_exit_waiting", None)))
    for why, line in (("stopping_car_first", "ماشي، بوقف السيارة وبنزل أول."), ("waiting_car_stop", "ماشي، بس توقف السيارة بنزل.")):
        GAME["answer"] = lambda a, o, why=why: {"ok": True, "reason": why} if a == "sol_farm" else {"ok": True, "reason": "pending"}
        c2, r2 = say("رتاحي بالبيت", '{"action":"go_home_rest","speech":""}')
        ck("exit first: %s -> '%s'" % (why, line), r2 == line, r2)
    for status, want in (("pending", None), ("done:true:home:going", "home"), ("done:false:base_missing", "ما في قاعدة مسجلة، حددها إلي بالأول."),
                         ("done:false:exit_failed", "ما قدرت انزل من السيارة."), ("idle", None)):
        c._exit_waiting = {"action": "sol_farm", "option": "home", "t": _tt.time(), "at": 0.0}
        del LATER[:]
        GAME["answer"] = lambda a, o, s=status: {"ok": True, "reason": s}
        CS._exit_watch(c)
        if want == "home": ok = len(LATER) == 1 and LATER[0] in ("ماشي، راجعة عالبيت وبرتاح هناك.", "تكرم، رايحة عالبيت.")
        else: ok = LATER == ([want] if want else [])
        ck("exit first, then '%s' -> %s" % (status, LATER), ok and (c._exit_waiting is not None) == (status == "pending"), (LATER, c._exit_waiting))
    c._exit_waiting = {"action": "sol_goto", "option": "1,2", "t": _tt.time(), "at": 0.0}; del LATER[:]
    GAME["answer"] = lambda a, o: {"ok": True, "reason": "done:true:walking_to"}
    CS._exit_watch(c)
    ck("exit first: a walk that went fine adds nothing (the bubble and the walk say it)", LATER == [], LATER)
    c._exit_waiting = {"action": "sol_farm", "option": "home", "t": _tt.time() - 1000, "at": 0.0}
    CS._exit_watch(c)
    ck("exit first: after %d s the Mind stops asking" % CS.EXIT_WATCH_SECONDS, c._exit_waiting is None)
    lines = list(CS.EXIT_LINES.values()) + [CS.EXIT_FAILED_LINE, CS.FAR_BACK_PREFIX]
    ck("lines: nothing technical (no latin, no digits, no meta words)", all(not re.search(r"[A-Za-z0-9_]|لاعب|سويتش", l) for l in lines), lines)

    # far_report: one line in the chat, once; it stays in her memory
    class Mem:
        def __init__(self): self.data = {"farm": {"stopSeen": 59}}; self.saved = 0
        def save(self): self.saved += 1
    class Mind:
        def say(self, line): BUBBLE.append(line)
    class Goals: pass
    m = Mem(); c = chat(); c.goals = Goals(); c.goals.mind = Mind(); c.goals.mind_lock = None
    c._memory_text = CS.Chat._memory_text.__get__(c)
    c._survey_answer = lambda s: "البيت محدد."
    rep = {"rounds": 1, "watered": 5, "harvest": [], "sown": 0, "cured": 0, "fed": 38, "short": [], "floor": False, "hours": 5}
    old = {"reason": "far_report", "detail": rep, "seq": 59, "at": 1794348326278}
    snap = {"solFarm": {"stops": [{"reason": "waiting", "detail": {"why": "dark"}, "seq": 58, "at": 1}, old], "zones": []}}
    del LATER[:], BUBBLE[:], LOG[:]
    c._farm_watch(snap, m)
    ck("far_report: a report already counted (seq 59, as the live memory has it) is not said again", LATER == [] and BUBBLE == [], (LATER, BUBBLE))
    new = dict(old, seq=60, at=1794348999999, detail=dict(rep, harvest=[{"veg": "Base.Tomato", "n": 3}]))
    snap["solFarm"]["stops"].append(new)
    snap["solFarm"]["stops"].append({"reason": "waiting", "detail": {"why": "dark"}, "seq": 61, "at": 2})
    c._farm_watch(snap, m)
    want = CS.FAR_BACK_PREFIX + FT.far_report_line(new["detail"])
    ck("far_report: a new one -> one line in the chat '%s'" % want, LATER == [want], LATER)
    ck("far_report: ... not as an in-game bubble too; the other stop rows still are", not any("سقيت" in b for b in BUBBLE) and len(BUBBLE) == 1, BUBBLE)
    ck("far_report: logged", any("far_report seq=60" in l for l in LOG), LOG)
    del LATER[:], BUBBLE[:]
    c._farm_watch(snap, m)
    ck("far_report: said once", LATER == [] and BUBBLE == [], (LATER, BUBBLE))
    mt = c._memory_text({}, m)
    ck("far_report: it stays in her memory on the card ('بغيابك: ...')", ("بغيابك: " + FT.far_report_line(new["detail"])) in mt, mt)
    ck("far_report: why still answers it from the stop row", FT.stop_line(new) == FT.far_report_line(new["detail"]))
    m2 = Mem(); m2.data["farm"]["stopSeen"] = 80                               # a new world counts from one again
    del LATER[:]
    c._farm_watch({"solFarm": {"stops": [dict(new, seq=2, at=5)]}}, m2)
    ck("far_report: a new world (lower seq) is said", len(LATER) == 1, LATER)
    return FAIL


if len(sys.argv) > 2 and sys.argv[1] == "--mind-child":
    mind_child(sys.argv[2])
    sys.exit(1 if FAIL else 0)

from kahlua_env import lua51
SRC = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind"))
LAB_CL = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client"))
LAB_LUA = os.path.abspath(os.path.join(HERE, "..", "profile", "Zomboid", "Lua"))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
GATE = os.path.join(ROOT, "05_TOOLS", "sol_kahlua", "tonumber_check.py")
CARD_CHECK = os.path.join(ROOT, "05_TOOLS", "sol_kahlua", "card_check.py")
def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, script)] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
def digest(d, names): return {n: hashlib.md5(open(os.path.join(d, n), "rb").read()).hexdigest() for n in names if os.path.exists(os.path.join(d, n))}
def read(p): return open(p, encoding="utf-8", newline="").read()
TMP = tempfile.mkdtemp(prefix="sol_s85_")
ENVP = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")

# ================================================================ 1. the Lua installer on copies
ZB = os.path.join(TMP, "Zomboid")
CL = os.path.join(ZB, "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(CL)
os.makedirs(os.path.join(ZB, "Lua"))
FIXF = os.path.join(ZB, "Lua", "SolFixes_LAB.txt")
open(FIXF, "w", encoding="utf-8", newline="").write("retry_reset=on\r\nhorn_hold=on")
LFILES = ["SolAuthority.lua", "SolOrders.lua", "SolGPS.lua"]
for f in LFILES: shutil.copy(os.path.join(LAB_CL, f), CL)
live_l = digest(LAB_CL, LFILES + ["SolExitFirst.lua"])
q1 = run("apply_s85_lua.py", CL); a1 = digest(CL, LFILES + ["SolExitFirst.lua"]); f1 = read(FIXF)
q2 = run("apply_s85_lua.py", CL); a2 = digest(CL, LFILES + ["SolExitFirst.lua"]); f2 = read(FIXF)
ck("lua installer: applies", q1.returncode == 0 and "applied" in q1.stdout, (q1.stdout + q1.stderr)[-500:])
ck("lua installer: idempotent (files and switch file)", q2.returncode == 0 and a1 == a2 and f1 == f2, q2.stdout[-300:])
ck("lua installer: exit_first in A.FIXES once", read(os.path.join(CL, "SolAuthority.lua")).count('"exit_first"') == 1)
ck("lua installer: exit_first=on added once, on its own line", f1 == "retry_reset=on\r\nhorn_hold=on\r\nexit_first=on\r\n", repr(f1))
ck("lua installer: SolOrders.lua untouched", digest(CL, ["SolOrders.lua"]) == digest(LAB_CL, ["SolOrders.lua"]))
ck("lua installer: the installed files are untouched", digest(LAB_CL, LFILES + ["SolExitFirst.lua"]) == live_l)
EF = read(os.path.join(CL, "SolExitFirst.lua"))
ck("lua: SolExitFirst.lua is pure ASCII", all(ord(ch) < 128 for ch in EF))
g = subprocess.run([sys.executable, GATE, os.path.join(CL, "SolExitFirst.lua")], capture_output=True, text=True, encoding="utf-8", errors="replace")
ck("lua: tonumber gate passes", g.returncode == 0, (g.stdout + g.stderr)[-400:])
for n in ("SolExitFirst.lua", "SolAuthority.lua", "SolGPS.lua"):
    e = lua51.LuaRuntime().eval("function(s) local f, e = loadstring(s); return e end")(read(os.path.join(CL, n)))
    ck("lua: %s compiles" % n, e is None, e)

# ---- 2. the GPS ready line says the button's word
def unesc(s): return re.sub(r"\\\\u([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), s)
gps = read(os.path.join(CL, "SolGPS.lua"))
ready = re.search(r'state, sc = ar\("([^"]*)", "Route ready - press Drive"\)', gps)
button = re.search(r'txt\(self, ar\("([^"]*)", "Drive"\)', gps)
ck("gps: the ready line and the Drive button are found", ready is not None and button is not None)
if ready and button:
    rb, bb = unesc(ready.group(1)), unesc(button.group(1))
    ck("gps: the ready line says 'اضغط %s' like the button (was 'اضغط قودي')" % bb, rb.endswith("اضغط " + bb) and "قودي" not in rb, rb)
ck("gps: nothing else in SolGPS.lua changed", len(gps) == len(read(os.path.join(LAB_CL, "SolGPS.lua"))) and
   sum(1 for a, b in zip(gps, read(os.path.join(LAB_CL, "SolGPS.lua"))) if a != b) <= 20)

# ---- 3. SolExitFirst under the game's Lua rules
ENV = r"""
print = function(m) LOGS[#LOGS + 1] = tostring(m) end
LOGS = {}
require = function() end
NOW, SWITCH = 1000000, true
function getTimestampMs() return NOW end
SolAuthority = { on = function(f) return f == "exit_first" and SWITCH end }
BUDGET = {}
SolBudget = { register = function(name, fn, o) BUDGET[name] = fn end }
Events = { OnGameStart = { Add = function(f) START = f end } }
CALLS = { base = {}, leave = 0, engine = {}, gpsStop = 0 }
CAR = { kmh = 0, engine = true }
CAR.getCurrentSpeedKmHour = function(self) return self.kmh end
CAR.isEngineRunning = function(self) return self.engine end
CAR.getDriver = function(self) return self.driver end
SOL = {}
SOL.getVehicle = function(self) return self.car end
SolUI = { solActor = function() return SOL end, gps = { lastResult = "idle" } }
SolUI.runAction = function(id, o)
    CALLS.base[#CALLS.base + 1] = id .. "|" .. tostring(o)
    if SOL.car ~= nil and id == "sol_farm" then return false, "in_vehicle" end
    return true, "base:" .. tostring(o)
end
SolUI.gpsStop = function() CALLS.gpsStop = CALLS.gpsStop + 1; SolUI.gps.lastResult = "stopped"; return true end
SolUI.solEngine = function(o) CALLS.engine[#CALLS.engine + 1] = o; CAR.engine = false; return true end
SolOrders = { leaveCar = function() CALLS.leave = CALLS.leave + 1 end }
function tick(ms) NOW = NOW + (ms or 250); BUDGET.exit_first() end
function run(id, o) return SolUI.runAction(id, o) end
function nbase() return #CALLS.base end
"""
def world(setup=""):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV); L.execute(setup); L.execute(EF); L.execute("START()")
    L.execute("SolUI_inner = SolUI.runAction")
    return L, L.globals()
R = lambda g, i, o=None: tuple(g.run(i, o))
def out(L): L.execute("SOL.car = nil")

# a. parked passenger: out, settle, then the order
L, g = world("SOL.car = CAR; CAR.driver = {}")
g.tick()                                                                    # first tick: the wrapper goes on
r = R(g, "sol_farm", "home")
ck("lua parked: 'home' in the car -> (true, leaving_car_first), out via SolOrders.leaveCar, the order not yet run", r == (True, "leaving_car_first") and g.CALLS.leave == 1 and g.nbase() == 0, (r, g.CALLS.leave, g.nbase()))
ck("lua parked: status pending", R(g, "sol_exit_first", "status") == (True, "pending"))
g.tick(); g.tick()
ck("lua parked: still in the car: nothing runs", g.nbase() == 0)
out(L); g.tick(); g.tick(1000)
ck("lua parked: out, within the settle: not yet", g.nbase() == 0)
g.tick(1000)
ck("lua parked: out + settle: the order runs once through the chain", list(g.CALLS.base.values()) == ["sol_farm|home"], list(g.CALLS.base.values()))
ck("lua parked: status done:true:base:home once, then idle", R(g, "sol_exit_first", "status") == (True, "done:true:base:home") and R(g, "sol_exit_first", "status") == (True, "idle"))
ck("lua parked: a passenger does not touch the engine", len(g.CALLS.engine) == 0)
# b. she drives, the car moves
L, g = world("SOL.car = CAR; CAR.driver = SOL; CAR.kmh = 40; SolUI.gps.lastResult = 'driving'"); g.tick()
r = R(g, "sol_sort", "run")
ck("lua her drive: -> stopping_car_first, the drive stopped, not out of a moving car", r == (True, "stopping_car_first") and g.CALLS.gpsStop == 1 and g.CALLS.leave == 0, (r, g.CALLS.gpsStop, g.CALLS.leave))
g.tick(); g.tick()
ck("lua her drive: still moving: still in", g.CALLS.leave == 0)
L.execute("CAR.kmh = 0.4"); g.tick()
ck("lua her drive: the car stands: engine off, then out", list(g.CALLS.engine.values()) == ["off"] and g.CALLS.leave == 1)
out(L); g.tick(); g.tick(2100)
ck("lua her drive: then the order", list(g.CALLS.base.values()) == ["sol_sort|run"])
L, g = world("SOL.car = CAR; CAR.driver = SOL; CAR.kmh = 40; SolUI.gps.lastResult = 'driving'; SolUI.gpsStop = function() return true end"); g.tick()
R(g, "sol_sort", "run"); g.tick(16000)
ck("lua her drive: the car never stops in 15 s -> done:false:exit_failed, the order never runs", R(g, "sol_exit_first", "status") == (True, "done:false:exit_failed") and g.nbase() == 0)
# c. he drives, she sits beside him
L, g = world("SOL.car = CAR; CAR.driver = {}; CAR.kmh = 30"); g.tick()
r = R(g, "sol_animals", "care")
ck("lua his drive: -> waiting_car_stop, his drive untouched", r == (True, "waiting_car_stop") and g.CALLS.gpsStop == 0 and g.CALLS.leave == 0, r)
g.tick(60000)
ck("lua his drive: a minute moving: she stays in", g.CALLS.leave == 0 and R(g, "sol_exit_first", "status") == (True, "pending"))
L.execute("CAR.kmh = 0"); g.tick()
ck("lua his drive: he stops: she gets out", g.CALLS.leave == 1 and len(g.CALLS.engine) == 0)
# d. not in a car / switch off / not an on-foot order / a newer order of his
L, g = world(); g.tick()
ck("lua: not in a car: the order runs at once, as before", R(g, "sol_farm", "home") == (True, "base:home") and g.CALLS.leave == 0)
L, g = world("SOL.car = CAR; SWITCH = false"); g.tick()
ck("lua: switch off: as before (in_vehicle)", R(g, "sol_farm", "home") == (False, "in_vehicle") and g.CALLS.leave == 0)
L, g = world("SOL.car = CAR"); g.tick()
ck("lua: sol_farm status from the car is not an on-foot order", R(g, "sol_farm", "status") == (False, "in_vehicle") and g.CALLS.leave == 0)
ck("lua: sol_horn, drive verbs pass through", R(g, "sol_horn", "once") == (True, "base:once") and g.CALLS.leave == 0)
for i, o in (("sol_goto", "1,2"), ("sol_go_inside", None), ("sol_fetch", "food"), ("guard", None), ("sol_role", "farmer"), ("sol_farm", "water:any"), ("sol_farm_try", "plant")):
    L, g = world("SOL.car = CAR; CAR.driver = {}"); g.tick()
    ck("lua: %s %s from the car -> she gets out first" % (i, o), R(g, i, o) == (True, "leaving_car_first"))
L, g = world("SOL.car = CAR; CAR.driver = {}"); g.tick()
R(g, "sol_farm", "home"); R(g, "follow")
ck("lua: his newer 'follow' drops the waiting order", R(g, "sol_exit_first", "status") == (True, "idle"))
out(L); g.tick(5000); g.tick(5000)
ck("lua: ... and it never runs", list(g.CALLS.base.values()) == ["follow|nil"], list(g.CALLS.base.values()))
L, g = world("SOL.car = CAR; CAR.driver = {}; SolOrders = nil"); g.tick()
ck("lua: no SolOrders: refused as before (in_vehicle)", R(g, "sol_farm", "home") == (False, "in_vehicle"))
L, g = world("SOL.car = CAR; CAR.driver = {}"); g.tick()
R(g, "sol_farm", "home"); g.tick(16000)
ck("lua: she does not get out in 15 s -> done:false:exit_failed", R(g, "sol_exit_first", "status") == (True, "done:false:exit_failed"))
# e. outside every other wrapper: a module that wraps runAction on OnGameStart after hers is still inside
L, g = world("SOL.car = CAR; CAR.driver = {}")
L.execute("local b = SolUI.runAction; SolUI.runAction = function(id, o) if id == 'sol_sort' then if SOL.car then return false, 'in_vehicle' end; return true, 'sorted' end; return b(id, o) end")
g.tick()
ck("lua: wrapped at the first tick, outside a later OnGameStart wrapper", R(g, "sol_sort", "run") == (True, "leaving_car_first"))
out(L); g.tick(); g.tick(2100)
ck("lua: ... and that module runs the order once she is out", R(g, "sol_exit_first", "status") == (True, "done:true:sorted"))

# ================================================================ 4. the Mind installer on copies
MFILES = ["model_router.py", "chat_service.py"]
live_m = digest(SRC, MFILES)
M = os.path.join(TMP, "mind"); os.makedirs(M)
for f in os.listdir(SRC):
    if f.endswith((".py", ".json.gz")): shutil.copy(os.path.join(SRC, f), M)
for pre in ("apply_s78_cars_away_mind.py", "apply_s79_horn_hold_mind.py", "apply_s82_engine_words.py"):    # kept when already in
    run(pre, M)
q1 = run("apply_s85_mind.py", M); m1 = digest(M, MFILES)
q2 = run("apply_s85_mind.py", M); m2 = digest(M, MFILES)
ck("mind installer: applies", q1.returncode == 0 and "applied" in q1.stdout, (q1.stdout + q1.stderr)[-600:])
ck("mind installer: idempotent", q2.returncode == 0 and m1 == m2 and q2.stdout.count("kept") == 2, q2.stdout)
for n in MFILES:
    ck("mind installer: line endings kept in %s" % n, (b"\r\n" in open(os.path.join(SRC, n), "rb").read()) == (b"\r\n" in open(os.path.join(M, n), "rb").read()))
imp = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import chat_service, model_router, memory_answers", M], capture_output=True, text=True, env=ENVP)
ck("mind: imports", imp.returncode == 0, imp.stderr[-600:])
NO82 = os.path.join(TMP, "no82"); os.makedirs(NO82)
for n in MFILES: open(os.path.join(NO82, n), "w", encoding="utf-8").write("def _route_by_model(self): pass\n")
q = run("apply_s85_mind.py", NO82)
ck("mind installer: refuses a Mind without s82", q.returncode != 0 and "s82 is not installed" in q.stderr, q.stderr[-200:])

# ---- 5. the card: card_check's own numbers (full catalog with every switch on, her hand off / on the horn)
cc = subprocess.run([sys.executable, CARD_CHECK, M, "--lua", LAB_CL, "--lua-profile", LAB_LUA, "--no-eval"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
size = re.search(r"full catalog (\d+), hand on the horn (\d+)", cc.stdout)
print("card_check:", size.group(0) if size else "?")
fails = [l for l in cc.stdout.splitlines() if l.startswith("FAIL ") and not l.startswith("FAIL (e)")]
ck("card_check: no failure on the patched Mind (the doc section aside: --write-doc after install)", not fails, fails)
ck("card_check: full catalog and hand on the horn both <= 4600", size is not None and int(size.group(1)) <= 4600 and int(size.group(2)) <= 4600, size and size.group(0))
CARD = r'''
import json, sys; sys.path.insert(0, sys.argv[1])
import chat_service as CS, model_router as MR
acts = [dict(a, enabled=True) for a in CS.load_actions(sys.argv[2])] + [{"id": "horn_hold", "kind": "sol", "state": "idle"}]
MR.HORN_HELD = False; idle = MR.sheet(acts, "")
MR.HORN_HELD = True; held = MR.sheet(acts, "")
print(json.dumps({"idle": idle, "held": held}, ensure_ascii=False))
'''
cr = subprocess.run([sys.executable, "-c", CARD, M, LAB_LUA], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
cards = json.loads(cr.stdout.strip().splitlines()[-1]) if cr.returncode == 0 else {"idle": "", "held": ""}
import s82_route_harness as H
ex_i, ex_h = H.examples(cards["idle"]), H.examples(cards["held"])
ck("card: horn_hold start / stop one line each", sum(1 for v in set(ex_i.values()) if '"horn_hold"' in v) == 2, [v for v in set(ex_i.values()) if "horn_hold" in v])
ck("card: 'بس' stops the horn only while held", "بس" not in ex_i and '"stop"' in ex_h.get("بس", ""))
ck("card: no duplicate 'زمري' example (the list shows it)", "زمري" not in ex_i)
ck("card: 'شوفي عنا بالمخزون' -> farm_report", ex_i.get("شوفي عنا بالمخزون") == '{"action":"farm_report"}', ex_i.get("شوفي عنا بالمخزون"))
two = [(k, json.loads(v)) for k, v in ex_i.items() if '"actions"' in v]
ck("card: exactly 2 examples with several actions", len(two) == 2, [k for k, _ in two])
ck("card: 'طفي المحرك ونزلي' -> sol_engine off, exit_car", ex_i.get("طفي المحرك ونزلي") and [a["action"] for a in json.loads(ex_i["طفي المحرك ونزلي"])["actions"]] == ["sol_engine", "exit_car"])
ck("card: 'نزلي من السيارة وتعالي لعندي' -> exit_car, come_foot", ex_i.get("نزلي من السيارة وتعالي لعندي") and [a["action"] for a in json.loads(ex_i["نزلي من السيارة وتعالي لعندي"])["actions"]] == ["exit_car", "come_foot"])
ck("card: the rule for several actions is on it", '"actions" بالترتيب' in cards["idle"])
ck("card: bare 'تعالي لعندي' left to come_car (Jamal)", "تعالي لعندي بالسيارة" in cards["idle"] and "تعالي لعندي" not in ex_i)
for b in ("regroup", "retreat", "set_combat_doctrine", "open_inventory", "open_health", "bandage"):
    ck("card: game button %s has a short example" % b, re.search(r'(?m)^%s: .* \| "[^"]+"$' % b, cards["idle"]) is not None)
ck("card: cars_near says it works while she is far", re.search(r'(?m)^cars_near: .*حتى لو بعيدة', cards["idle"]) is not None)

# ---- 6. the chat, mocked
c = subprocess.run([sys.executable, os.path.abspath(__file__), "--mind-child", M], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
for l in c.stdout.strip().splitlines(): print("  [mind] " + l)
ck("mind: the chat checks pass", c.returncode == 0 and not any(l.startswith("FAIL") for l in c.stdout.splitlines()), c.stderr[-1200:])
ck("mind installer: the live Mind is untouched", digest(SRC, MFILES) == live_m)

shutil.rmtree(TMP, ignore_errors=True)
print("\n%d FAIL" % len(FAIL) if FAIL else "\nALL PASS")
sys.exit(1 if FAIL else 0)

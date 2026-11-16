"""s91: engine off whenever she gets out of a car she drives, unless his order said to leave it running (exit_car keep_engine).
apply_s91_engine_off_exit_lua.py + apply_s91_engine_off_exit_mind.py on temporary copies (idempotent); SolExitEngine.lua under the
game's Lua rules on every exit path (with / without the option, he drives, another companion, a moving car, the switch off, the
held horn, SolExitFirst's own exit); the Mind's route (the model's answer exit_car keep_engine -> the game gets exit_vehicle
keep_engine, nothing else does); s90's example bank in three shapes; card_check.py PASS and test_s82_route_eval.py --as-is.
Nothing live is touched.
Run: set PYTHONIOENCODING=utf-8 & python test_s91_engine_off_exit.py [sol_mind dir] [client dir]   (defaults: the live ones, read only)
Offline PASS is not Runtime PASS."""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, HERE)
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)


KEEP_SAID = "نزلي من السيارة وخلي المحرك شغال"
KEEP_JSON = '{"action":"exit_car","args":{"option":"keep_engine"},"speech":""}'


# ================================================================ child: the patched Mind's chat with mocks
def mind_child(mind):
    sys.path.insert(0, mind)
    import chat_service as CS, model_router as MR, reply_gate as RG, providers as P, settings_service as SS, world_knowledge as W
    ck("child: the patched copy is what got imported", os.path.dirname(os.path.abspath(CS.__file__)) == os.path.abspath(mind))
    ck("parse: exit_car keep_engine -> KEEP_ENGINE_S91", MR.parse(KEEP_JSON)["action"] == "exit_car" and MR.KEEP_ENGINE_S91 is True)
    MR.parse('{"action":"exit_car","speech":""}')
    ck("parse: plain exit_car -> no keep", MR.KEEP_ENGINE_S91 is False)
    MR.parse('{"actions":[{"action":"exit_car","args":{"option":"keep_engine"}},{"action":"come_foot"}]}')
    ck("parse: 'actions' with exit_car keep_engine first -> keep", MR.KEEP_ENGINE_S91 is True and len(MR.LAST_STEPS) == 2)
    ck("intents: 'انزلي' (exit_car's own phrase) is the game's exit_vehicle, no option", ("action", {"action": "exit_vehicle", "option": None}) in CS.intents(MR.COMMANDS["exit_car"][1]))

    SS.load_config = lambda: {"source": "local", "provider": "custom", "model": "test", "base": ""}
    W.situation_text = lambda s, m: "world"
    CS.MA.answer = lambda *a, **k: None
    CS.MA.known_names = lambda *a, **k: []
    CS.time.sleep = lambda s: None
    CS.load_actions = lambda d: [{"id": i, "kind": "sol"} for i in ("sol_engine", "sol_headlights", "sol_horn")]
    TMPD = tempfile.mkdtemp(prefix="sol_s91_child_")
    GAME, LOG = [], []
    def base_run(d, action, option=None, wait=3.0):
        GAME.append((action, option)); return {"ok": True, "reason": ""}
    CS._run_action_s85_base = base_run
    REPLY = {"v": ""}
    P.chat = lambda *a, **k: REPLY["v"]
    WORLD = {"in_car": 0}
    def world():
        sol = {"x": 1, "y": 1}
        if WORLD["in_car"] > 0: WORLD["in_car"] -= 1; sol["currentVehicle"] = "car"
        return {"sol": sol, "player": {"x": 1, "y": 1}}, None

    def chat():
        c = CS.Chat.__new__(CS.Chat)
        c.dir, c.log, c._forced, c._sheet = TMPD, LOG.append, None, None
        c._world = world
        c.gps_state = lambda: {}
        def pre(h, s, m):                       # the Mind's own word path for a COMMANDS phrase: intents() -> resolve_and_run, as _pre_intents does
            ran = []
            for name, args in CS.intents(h[-1]["text"]):
                if name == "action":
                    CS.resolve_and_run(c.dir, args["action"], args.get("option"), m, s); ran.append(args["action"])
            return ran or ["ran"]
        c._pre_intents = pre
        c._receipt = lambda: "تكرم."
        c._player_takes_over = lambda a: None
        c._remember_action = lambda a, o: None
        c._memory_text = lambda s, m: "لا شيء."
        c._gate_context = lambda h, a, k, n=(): RG.Context(h[-1]["text"], [], [], k, False, (), [])
        c._model_first = lambda: True
        c._say_later = lambda l: None
        return c
    def say(text, reply):
        del GAME[:], LOG[:]
        REPLY["v"] = reply
        c = chat()
        return c._route_by_model([{"role": "user", "text": text}], SS.load_config(), "", {}, None)

    r = say(KEEP_SAID, KEEP_JSON)
    ck("route: '%s' -> the game gets exit_vehicle keep_engine, once" % KEEP_SAID, GAME == [("exit_vehicle", "keep_engine")], GAME)
    ck("route: ... her line stays natural (the receipt)", r == "تكرم.", r)
    ck("route: ... the keep is not left over", MR.KEEP_ENGINE_S91 is False)
    r = say("نزلي من السيارة", '{"action":"exit_car","speech":""}')
    ck("route: plain 'نزلي من السيارة' -> exit_vehicle, no option (the game turns her engine off)", GAME == [("exit_vehicle", None)], GAME)
    r = say("انزلي", '{"action":"exit_car","args":{"option":"fast"},"speech":""}')
    ck("route: any other option on exit_car -> no keep", GAME == [("exit_vehicle", None)], GAME)
    WORLD["in_car"] = 2
    r = say("نزلي وخلي المحرك شغال وتعالي لعندي", '{"actions":[{"action":"exit_car","args":{"option":"keep_engine"}},{"action":"come_foot"}],"speech":""}')
    ck("steps: exit_car keep_engine, then come: only the exit carries the keep", GAME and GAME[0] == ("exit_vehicle", "keep_engine") and all(o != "keep_engine" for _, o in GAME[1:]), GAME)
    r = say("طفي المحرك ونزلي", '{"actions":[{"action":"sol_engine","args":{"option":"off"}},{"action":"exit_car"}],"speech":""}')
    ck("steps: 'طفي المحرك ونزلي' -> engine off, exit with no keep", GAME == [("sol_engine", "off"), ("exit_vehicle", None)], GAME)
    r = say("سوقي عالبيت", '{"action":"exit_car","args":{"option":"keep_engine"},"speech":""}')
    MR.KEEP_ENGINE_S91 = True                      # a stray flag (e.g. a route that never reached the exit) ...
    r = say("انزلي", '{"action":"exit_car","speech":""}')
    ck("leak: a new route clears it: plain exit, no keep", GAME == [("exit_vehicle", None)], GAME)
    MR.KEEP_ENGINE_S91 = False
    CS.resolve_and_run(TMPD, "exit_vehicle", None, None, None)
    ck("outside the model route (word lists, goals): never a keep", GAME[-1] == ("exit_vehicle", None), GAME)
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
DOC = os.path.join(ROOT, "DOCS", "SOL_MODEL_CARD.md")
ENVP = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, script)] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
def digest(d, names): return {n: hashlib.md5(open(os.path.join(d, n), "rb").read()).hexdigest() for n in names if os.path.exists(os.path.join(d, n))}
def read(p): return open(p, encoding="utf-8", newline="").read()
TMP = tempfile.mkdtemp(prefix="sol_s91_")

# ================================================================ 1. the Lua installer on copies
ZB = os.path.join(TMP, "Zomboid")
CL = os.path.join(ZB, "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(CL)
os.makedirs(os.path.join(ZB, "Lua"))
FIXF = os.path.join(ZB, "Lua", "SolFixes_LAB.txt")
open(FIXF, "w", encoding="utf-8", newline="").write("horn_hold=on\r\nexit_first=on")
LFILES = ["SolAuthority.lua", "SolActions.lua", "SolOrders.lua"]
for f in LFILES: shutil.copy(os.path.join(LAB_CL, f), CL)
live_l = digest(LAB_CL, LFILES + ["SolExitEngine.lua"])
q1 = run("apply_s91_engine_off_exit_lua.py", CL); a1 = digest(CL, LFILES + ["SolExitEngine.lua"]); f1 = read(FIXF)
q2 = run("apply_s91_engine_off_exit_lua.py", CL); a2 = digest(CL, LFILES + ["SolExitEngine.lua"]); f2 = read(FIXF)
ck("lua installer: applies", q1.returncode == 0 and "applied" in q1.stdout, (q1.stdout + q1.stderr)[-500:])
ck("lua installer: idempotent (files and switch file)", q2.returncode == 0 and a1 == a2 and f1 == f2, q2.stdout[-300:])
ck("lua installer: exit_engine_off in A.FIXES once", read(os.path.join(CL, "SolAuthority.lua")).count('"exit_engine_off"') == 1)
ck("lua installer: exit_engine_off=on added once, on its own line", f1 == "horn_hold=on\r\nexit_first=on\r\nexit_engine_off=on\r\n", repr(f1))
ck("lua installer: SolActions.lua, SolOrders.lua untouched", digest(CL, ["SolActions.lua", "SolOrders.lua"]) == digest(LAB_CL, ["SolActions.lua", "SolOrders.lua"]))
ck("lua installer: the installed files are untouched", digest(LAB_CL, LFILES + ["SolExitEngine.lua"]) == live_l)
EE = read(os.path.join(CL, "SolExitEngine.lua"))
ck("lua: SolExitEngine.lua is pure ASCII", all(ord(ch) < 128 for ch in EE))
g = subprocess.run([sys.executable, GATE, os.path.join(CL, "SolExitEngine.lua")], capture_output=True, text=True, encoding="utf-8", errors="replace")
ck("lua: tonumber gate passes", g.returncode == 0, (g.stdout + g.stderr)[-400:])
for n in ("SolExitEngine.lua", "SolAuthority.lua"):
    e = lua51.LuaRuntime().eval("function(s) local f, e = loadstring(s); return e end")(read(os.path.join(CL, n)))
    ck("lua: %s compiles" % n, e is None, e)

# ================================================================ 2. SolExitEngine under the game's Lua rules
# SC.Vehicle.exit is a stand-in with the real one's contract: refuses a moving car, else she is out (true, "native_exit").
ENV = r"""
print = function(m) LOGS[#LOGS + 1] = tostring(m) end
LOGS = {}
require = function() end
NOW, SW = 1000000, { exit_engine_off = true, exit_first = true }
function getTimestampMs() return NOW end
SolAuthority = { on = function(f) return SW[f] == true end }
BUDGET = {}
SolBudget = { register = function(name, fn, o) BUDGET[name] = fn end }
STARTS = {}
Events = { OnGameStart = { Add = function(f) STARTS[#STARTS + 1] = f end } }
CALLS = { engine = {}, exits = {}, base = {}, horn = 0 }
function newCar() local c = { kmh = 0, engine = true }
    c.getCurrentSpeedKmHour = function(self) return self.kmh end
    c.isEngineRunning = function(self) return self.engine end
    c.getDriver = function(self) return self.driver end
    c.shutOff = function(self) self.engine = false end
    c.onHornStop = function(self) CALLS.horn = CALLS.horn + 1 end
    return c end
CAR = newCar()
SOL, HIM, OTHER = {}, {}, {}
SOL.getVehicle = function(self) return self.car end
OTHER.getVehicle = function(self) return self.car end
SolUI = { solActor = function() return SOL end, gps = { lastResult = "idle" } }
SolUI.solEngine = function(o)                              -- the existing path's contract: Driving.stop, shutOff when running
    CALLS.engine[#CALLS.engine + 1] = o
    local v = SOL.car
    if v == nil then return false, "not_in_a_car" end
    if not v.engine then return true, "already_off" end
    v.engine = false; return true, "engine_off" end
SurvivorCompanion = { Vehicle = {} }
SurvivorCompanion.Vehicle.isStationary = function(v) if math.abs(v.kmh) > 0.5 then return false, "vehicle is moving" end; return true end
SurvivorCompanion.Vehicle.exit = function(actor, vehicle, seat, intent)
    local v = vehicle or actor.car
    CALLS.exits[#CALLS.exits + 1] = tostring(intent and intent.from or "?") .. ":" .. tostring(v and v.engine)
    if v == nil then return false, "actor is not in a native vehicle seat" end
    if math.abs(v.kmh) > 0.5 then return false, "vehicle is moving" end
    actor.car = nil
    if v.driver == actor then v.driver = nil end
    return true, "native_exit" end
SolUI.runAction = function(id, o)                          -- SolOrders' chat verb: exit_vehicle -> leaveCar -> SC.Vehicle.exit
    CALLS.base[#CALLS.base + 1] = tostring(id) .. "|" .. tostring(o)
    if id == "exit_vehicle" then
        if SOL.car == nil or QUEUED then return true, "issued" end           -- QUEUED: LF's exit_vehicle, run by the action queue later
        SurvivorCompanion.Vehicle.exit(SOL, SOL.car, nil, { from = "leaveCar" }); return true, "issued" end
    return true, "base" end
SolOrders = { leaveCar = function() if SOL.car then SurvivorCompanion.Vehicle.exit(SOL, SOL.car, nil, { from = "leaveCar" }) end end }
function tick(ms) NOW = NOW + (ms or 500); for _, f in pairs(BUDGET) do f() end end
function start() for _, f in ipairs(STARTS) do f() end end
function exitBy(from, who) local a = who or SOL; return SurvivorCompanion.Vehicle.exit(a, a.car, 0, { from = from }) end
function nEngine() return #CALLS.engine end
function lastLog() return LOGS[#LOGS] end
function hasLog(s) for _, l in ipairs(LOGS) do if string.find(l, s, 1, true) then return true end end; return false end
"""
def world(setup="", extra=None):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV); L.execute(setup)
    for src in extra or []: L.execute(src)
    L.execute(EE); L.execute("start()"); L.execute("tick()")
    return L, L.globals()
DRIVES = "SOL.car = CAR; CAR.driver = SOL"
R = lambda g, i, o=None: tuple(g.SolUI.runAction(i, o))

L, g = world(DRIVES)
ck("lua: the exit is wrapped at the first tick", g.hasLog("exit hook on") and g.hasLog("ready v0.1.0"))
r = R(g, "exit_vehicle")
ck("order exit_car (she drives, engine running): engine off first, then out", list(g.CALLS.engine.values()) == ["off"] and list(g.CALLS.exits.values()) == ["leaveCar:false"], (list(g.CALLS.engine.values()), list(g.CALLS.exits.values())))
ck("order exit_car: logged 'engine off before exit'", g.hasLog("engine off before exit"))
ck("order exit_car: the order ran as before (no option)", list(g.CALLS.base.values()) == ["exit_vehicle|nil"], list(g.CALLS.base.values()))
L, g = world(DRIVES)
r = R(g, "exit_vehicle", "keep_engine")
ck("order exit_car keep_engine: the engine stays on, she gets out", g.nEngine() == 0 and list(g.CALLS.exits.values()) == ["leaveCar:true"] and g.CAR.engine is True, (g.nEngine(), list(g.CALLS.exits.values())))
ck("order exit_car keep_engine: logged 'engine kept on by order'", g.hasLog("engine kept on by order"))
ck("order exit_car keep_engine: the order itself runs as before (option dropped)", list(g.CALLS.base.values()) == ["exit_vehicle|nil"], list(g.CALLS.base.values()))
ck("order exit_car keep_engine: the keep is used up by that exit", g.SolExitEngine.keep is None)
L.execute("SOL.car = CAR; CAR.driver = SOL"); g.exitBy("native")
ck("... the next exit (no order) turns the engine off again", list(g.CALLS.engine.values()) == ["off"] and g.CAR.engine is False)
L, g = world(DRIVES)
R(g, "exit_car", "keep_engine")
ck("id exit_car with keep_engine is the same order", g.SolExitEngine.keep is not None)
L, g = world(DRIVES)
L.execute("CAR.kmh = 20"); R(g, "exit_vehicle", "keep_engine")       # the car still rolls: the exit is refused, the keep waits
ck("keep_engine on a rolling car: refused exit, engine untouched", g.nEngine() == 0 and g.CAR.engine is True and g.SOL.car is not None)
g.tick(21000); L.execute("CAR.kmh = 0"); g.exitBy("native")
ck("keep_engine expires after %d s: a later exit turns the engine off" % (g.SolExitEngine.KEEP_MS // 1000), list(g.CALLS.engine.values()) == ["off"])
L, g = world(DRIVES)
R(g, "exit_vehicle", "keep_engine"); R(g, "follow")
L.execute("SOL.car = CAR; CAR.driver = SOL; CAR.engine = true"); R(g, "exit_vehicle")
ck("a plain exit order after a keep order: engine off (the newer order wins)", list(g.CALLS.engine.values()) == ["off"])

# every exit path ends in SC.Vehicle.exit; she drives / he drives / another companion / engine already off / moving
for path in ("leaveCar", "native_action_queue", "player_left_car_policy", "far_regroup", "bleed_stop", "exit_first", "follow_exits_car", "can_refuel", "park_end", "stall_exit", "expedition"):
    L, g = world(DRIVES)
    ok = tuple(g.exitBy(path))[:2]
    ck("path %s, she drives: engine off before exit, then out" % path, ok == (True, "native_exit") and list(g.CALLS.engine.values()) == ["off"] and list(g.CALLS.exits.values()) == [path + ":false"], (ok, list(g.CALLS.engine.values()), list(g.CALLS.exits.values())))
    L, g = world(DRIVES)
    L.execute("QUEUED = true"); R(g, "exit_vehicle", "keep_engine")
    g.exitBy(path)
    ck("path %s, she drives, after his keep_engine order: engine stays on" % path, g.nEngine() == 0 and g.CAR.engine is True)
L, g = world("SOL.car = CAR; CAR.driver = HIM")
g.exitBy("leaveCar"); R(g, "exit_vehicle", "keep_engine"); L.execute("SOL.car = CAR"); g.exitBy("seat_swap")
ck("he drives (she is a passenger): his engine is never touched, every path", g.nEngine() == 0 and g.CAR.engine is True and not g.hasLog("engine off before exit"))
L, g = world("SOL.car = CAR; CAR.driver = nil")
g.exitBy("leaveCar")
ck("nobody at the wheel, she sits beside: engine untouched", g.nEngine() == 0)
L, g = world("OTHER.car = CAR; CAR.driver = OTHER")
g.exitBy("expedition", g.OTHER)
ck("another companion leaves the wheel: not hers to turn off", g.nEngine() == 0 and g.CAR.engine is True)
L, g = world(DRIVES + "; CAR.engine = false")
g.exitBy("leaveCar")
ck("engine already off: nothing to do, no log", g.nEngine() == 0 and not g.hasLog("engine off before exit"))
L, g = world(DRIVES + "; CAR.kmh = 30")
ok = tuple(g.exitBy("leaveCar"))
ck("a moving car: the exit refuses, the engine is not cut on the road", ok[0] is False and g.nEngine() == 0 and g.CAR.engine is True, ok)
L, g = world(DRIVES + "; SolUI.solEngine = nil")
g.exitBy("leaveCar")
ck("no solEngine (older SolActions): BaseVehicle.shutOff directly", g.CAR.engine is False)
# the switch off: the old behaviour
L, g = world(DRIVES + "; SW.exit_engine_off = false")
g.exitBy("leaveCar")
ck("switch off: she leaves the engine as before", g.nEngine() == 0 and g.CAR.engine is True)
L, g = world(DRIVES + "; SW.exit_engine_off = false")
R(g, "exit_vehicle", "keep_engine")
ck("switch off: the keep_engine option is dropped, the order runs as before, nothing kept", list(g.CALLS.base.values()) == ["exit_vehicle|nil"] and g.SolExitEngine.keep is None and g.nEngine() == 0)
L, g = world(DRIVES)
L.execute("SW.exit_engine_off = false"); g.exitBy("leaveCar")
ck("switch turned off in play: the hook stays but does nothing", g.nEngine() == 0)
ck("other verbs pass through untouched", R(g, "sol_horn", "once") == (True, "base"))
# the held horn (s79): let go as she leaves the seat, kept engine or not
for keep in (False, True):
    L, g = world(DRIVES + "; SolHornHold = { hold = { veh = CAR }, release = function(why) HORN_WHY = why; SolHornHold.hold = nil; CAR:onHornStop() end }")
    if keep: R(g, "exit_vehicle", "keep_engine"); L.execute(DRIVES)
    g.exitBy("leaveCar")
    ck("held horn: let go on her exit (%s)" % ("engine kept on" if keep else "engine off"), g.CALLS.horn == 1 and g.HORN_WHY == "left_driver_seat")
HH = os.path.join(LAB_CL, "SolHornHold.lua")
ck("held horn: SolHornHold.lua (s79) still stops on left_car / left_driver_seat / engine_off itself", os.path.exists(HH) and all(w in read(HH) for w in ('"left_car"', '"left_driver_seat"', '"engine_off"')))
# SolExitFirst (s85) with this hook: its own engine-off and the hook agree (one off, no second call needed)
EF = os.path.join(LAB_CL, "SolExitFirst.lua")
if os.path.exists(EF):
    L, g = world(DRIVES, [read(EF)])
    g.tick()
    r = R(g, "sol_farm", "home")
    ck("exit_first (s85): 'rest at home' from her seat -> out with the engine off", r == (True, "leaving_car_first") and g.CAR.engine is False and g.SOL.car is None, (r, g.CAR.engine))
    ck("exit_first: one engine-off call reaches the car (the hook finds it already off)", list(g.CALLS.engine.values()) == ["off"], list(g.CALLS.engine.values()))
# SolActions' follow_exits_car path (the real U.runAction head) and the plain exit_vehicle chat verb through the real SolOrders are
# covered by the stand-in above: both end in SolOrders.leaveCar -> SC.Vehicle.exit (SolActions.lua:62-72, SolOrders.lua:547-563).
src_a, src_o = read(os.path.join(LAB_CL, "SolActions.lua")), read(os.path.join(LAB_CL, "SolOrders.lua"))
ck("source: follow_exits_car ends in SolOrders.leaveCar", "SolOrders.leaveCar()" in src_a)
ck("source: SolOrders.leaveCar goes through SurvivorCompanion.Vehicle.exit (api.exit) or LF's exit_vehicle", "pcall(api.exit, me, veh" in src_o and 'lf("exit_vehicle")' in src_o)
nat = read(os.path.join(LAB_CL, "SCNativeActions.lua")) if os.path.exists(os.path.join(LAB_CL, "SCNativeActions.lua")) else ""
ck("source: LF's native exit_vehicle action looks SC.Vehicle.exit up at call time (the wrap reaches it)", "SC.Vehicle.board or SC.Vehicle.exit" in nat)
direct = [f for f in os.listdir(LAB_CL) if f.endswith(".lua") and f != "SCVehicle.lua" and re.search(r'invoke\([^)]*"exit"|:exit\(', read(os.path.join(LAB_CL, f)))]
ck("source: no client file calls BaseVehicle.exit past SC.Vehicle.exit", not direct, direct)

# ================================================================ 3. the Mind installer on copies
MFILES = ["model_router.py", "chat_service.py"]
live_m = digest(SRC, MFILES)
M = os.path.join(TMP, "mind"); os.makedirs(M)
for f in os.listdir(SRC):
    if f.endswith((".py", ".json.gz")): shutil.copy(os.path.join(SRC, f), M)
q1 = run("apply_s91_engine_off_exit_mind.py", M); m1 = digest(M, MFILES)
q2 = run("apply_s91_engine_off_exit_mind.py", M); m2 = digest(M, MFILES)
ck("mind installer: applies", q1.returncode == 0 and "applied" in q1.stdout, (q1.stdout + q1.stderr)[-600:])
ck("mind installer: idempotent", q2.returncode == 0 and m1 == m2 and q2.stdout.count("kept") == 2, q2.stdout)
for n in MFILES:
    ck("mind installer: line endings kept in %s" % n, (b"\r\n" in open(os.path.join(SRC, n), "rb").read()) == (b"\r\n" in open(os.path.join(M, n), "rb").read()))
imp = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import chat_service, model_router, memory_answers", M], capture_output=True, text=True, env=ENVP)
ck("mind: imports", imp.returncode == 0, imp.stderr[-600:])
MV = os.path.join(TMP, "moved"); shutil.copytree(M, MV)
with open(os.path.join(MV, "model_router.py"), "a", encoding="utf-8", newline="") as h: h.write("\n# a later stage\nLATER_STAGE = 1\n")
q = run("apply_s91_engine_off_exit_mind.py", MV)
mr_t = read(os.path.join(MV, "model_router.py"))
ck("mind installer: a later stage appended after it -> the s91 block moves to the end, once", "model_router moved to the end" in q.stdout and mr_t.rstrip().endswith("s91 end") and mr_t.count("s91 engine off on exit") == 1 and "LATER_STAGE = 1" in mr_t, q.stdout)
NO85 = os.path.join(TMP, "no85"); os.makedirs(NO85)
for n in MFILES: open(os.path.join(NO85, n), "w", encoding="utf-8").write("x = 1\n")
q = run("apply_s91_engine_off_exit_mind.py", NO85)
ck("mind installer: refuses a Mind without s85", q.returncode != 0 and "s85 is not installed" in q.stderr, q.stderr[-200:])

# ---- 4. the card: card_check PASS (doc section written to a temp copy of the doc), the example on it, the budget
DOCT = os.path.join(TMP, "SOL_MODEL_CARD.md"); shutil.copy(DOC, DOCT)
cc = subprocess.run([sys.executable, CARD_CHECK, M, "--lua", LAB_CL, "--lua-profile", LAB_LUA, "--doc", DOCT, "--write-doc"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
size = re.search(r"full catalog (\d+), hand on the horn (\d+)", cc.stdout)
print("card_check:", size.group(0) if size else "?", "|", (cc.stdout.strip().splitlines() or ["?"])[-1])
ck("card_check: PASS on the patched Mind (route eval included)", cc.returncode == 0 and "CARD_CHECK: PASS" in cc.stdout, [l for l in cc.stdout.splitlines() if l.startswith("FAIL")][:8])
ck("card_check: full catalog and hand on the horn both <= 4600", size is not None and int(size.group(1)) <= 4600 and int(size.group(2)) <= 4600, size and size.group(0))
ck("doc: the generated card section names the keep_engine example (written to the temp copy only)", KEEP_SAID in read(DOCT) and read(DOC) != read(DOCT))
CARD = r'''
import json, sys; sys.path.insert(0, sys.argv[1])
import chat_service as CS, model_router as MR
acts = [dict(a, enabled=True) for a in CS.load_actions(sys.argv[2])] + [{"id": "horn_hold", "kind": "sol", "state": "idle"}]
def full(a):
    """The card; on s90's two-tier card: tier 1 with every bank example on it, one line per answer (what any message can be shown)."""
    s = MR.sheet(a, "")
    if not (getattr(MR, "CARD_TIERS", False) and hasattr(MR, "example_bank")): return s
    groups = {}
    for said, ans in MR.example_bank(a): groups.setdefault(ans, []).append(said)
    lines = [" / ".join(v) + " -> " + k for k, v in groups.items()]
    return s.replace(chr(10) * 2 + "ذاكرتك الآن:", chr(10) + chr(10).join(lines) + chr(10) * 2 + "ذاكرتك الآن:", 1)
said = "نزلي من السيارة وخلي المحرك شغال"
one = MR.add_examples(MR.sheet(acts, ""), said, acts) if getattr(MR, "CARD_TIERS", False) and hasattr(MR, "add_examples") else None
print(json.dumps({"card": full(acts), "bare": full([]), "one": one}, ensure_ascii=False))
'''
cr = subprocess.run([sys.executable, "-c", CARD, M, LAB_LUA], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
cards = json.loads(cr.stdout.strip().splitlines()[-1]) if cr.returncode == 0 else {"card": "", "bare": ""}
import s82_route_harness as H
ex = H.examples(cards["card"])
ck("card: '%s' -> exit_car keep_engine" % KEEP_SAID, ex.get(KEEP_SAID) == '{"action":"exit_car","args":{"option":"keep_engine"}}', ex.get(KEEP_SAID))
ck("card: 'خلي الموتور شغال' -> exit_car keep_engine", ex.get("خلي الموتور شغال") == '{"action":"exit_car","args":{"option":"keep_engine"}}')
ck("card: one keep_engine line, also on a card built with no catalog", cards["card"].count("keep_engine") == 1 and cards["bare"].count("keep_engine") == 1)
ck("card: plain 'نزلي من السيارة' still -> exit_car", ex.get("نزلي من السيارة") == '{"action":"exit_car"}')
ck("card: the s85 lines are untouched ('طفي المحرك ونزلي', 'نزلي من السيارة وتعالي لعندي', the actions rule)",
   "طفي المحرك ونزلي" in ex and "نزلي من السيارة وتعالي لعندي" in ex and '"actions" بالترتيب' in cards["card"])
if cards.get("one") is not None:                                         # s90 two-tier card: the line's own card shows it
    ck("card (s90, per message): '%s' gets the keep_engine example" % KEEP_SAID, H.examples(cards["one"]).get(KEEP_SAID) == '{"action":"exit_car","args":{"option":"keep_engine"}}')
ck("card: no keyword override in the Mind (the phrase is nowhere but the card's example)", "خلي المحرك شغال" not in re.sub(r"(?s)KEEP_ENGINE_SAID_S91 = \([^)]*\)", "", read(os.path.join(M, "model_router.py")) + read(os.path.join(M, "chat_service.py"))))
ev = run("test_s82_route_eval.py", "--as-is", M)
ck("route eval --as-is: %s" % (ev.stdout.strip().splitlines() or ["?"])[-1], ev.returncode == 0, [l for l in ev.stdout.splitlines() if l.startswith("FAIL")][:8])

# ---- 5. s90's example bank (list of lines / pairs / dict): the example goes there, not on the card a second time
BANKS = {"lines": 'EXAMPLE_BANK = ["رقصي -> {\\"action\\":\\"unknown\\"}"]',
         "pairs": 'EXAMPLE_BANK = [("رقصي", "{\\"action\\":\\"unknown\\"}")]',
         "dict": 'EXAMPLE_BANK = {"رقصي": {"action": "unknown"}}'}
PROBE = r'''
import json, sys; sys.path.insert(0, sys.argv[1])
import model_router as MR
print(json.dumps({"bank": MR.BANK_S91, "entries": repr(MR.EXAMPLE_BANK), "card": MR.sheet([], "").count("keep_engine")}, ensure_ascii=False))
'''
for shape, line in BANKS.items():
    B = os.path.join(TMP, "bank_" + shape); os.makedirs(B)
    for f in MFILES: shutil.copy(os.path.join(SRC, f), B)
    for f in os.listdir(SRC):
        if f.endswith(".py") and f not in MFILES: shutil.copy(os.path.join(SRC, f), B)
    with open(os.path.join(B, "model_router.py"), "a", encoding="utf-8", newline="") as h: h.write("\n# s90 stand-in\n" + line + "\n")
    q = run("apply_s91_engine_off_exit_mind.py", B)
    pr = subprocess.run([sys.executable, "-c", PROBE, B], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
    d = json.loads(pr.stdout.strip().splitlines()[-1]) if pr.returncode == 0 else {}
    ok = d.get("bank") == "EXAMPLE_BANK" and d.get("card") == 0 and KEEP_SAID in d.get("entries", "") and "keep_engine" in d.get("entries", "")
    ck("s90 bank (%s): the keep_engine example goes into EXAMPLE_BANK, the card adds no line of its own" % shape, ok, (q.stderr[-300:], pr.stderr[-300:], d))

# ---- 6. the chat, mocked
c = subprocess.run([sys.executable, os.path.abspath(__file__), "--mind-child", M], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENVP)
for l in c.stdout.strip().splitlines(): print("  [mind] " + l)
ck("mind: the chat checks pass", c.returncode == 0 and not any(l.startswith("FAIL") for l in c.stdout.splitlines()), c.stderr[-1200:])
ck("mind installer: the live Mind is untouched", digest(SRC, MFILES) == live_m)

shutil.rmtree(TMP, ignore_errors=True)
print("\n%d FAIL" % len(FAIL) if FAIL else "\nALL PASS")
sys.exit(1 if FAIL else 0)

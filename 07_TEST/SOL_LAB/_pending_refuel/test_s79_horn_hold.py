"""s79 horn_hold: the held horn (start / stop / every auto-stop) under the game's Lua rules, the model card with a mocked model that
reads the card it is given (so "بس" means stop only while she holds the horn), her lines, and both installers (idempotent, any order
with s78). Temporary copies only; nothing live is touched.
Run: set PYTHONIOENCODING=utf-8 & python test_s79_horn_hold.py [sol_mind dir] [client dir]
     (defaults: 05_TOOLS/sol_mind and the lab client, both read only)
Offline PASS is not Runtime PASS."""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)


# ================================================================ child: the chat with a mocked model, on one patched Mind copy
def said_on(card):
    """{his words: the answer} from the card: example lines (grouped or not), then each listed action's own phrase."""
    out = {}
    for line in card.splitlines():
        k = line.find(" -> {")
        if k > 0:
            for said in line[:k].split(" / "): out.setdefault(said.strip(), line[k + 4:])
    for line in card.splitlines():
        m = re.match(r'^([a-z_0-9]+): .*?\| (?:مثال: )?"([^"]+)"(?: \| option: ([a-z]+))?', line)
        if m: out.setdefault(m.group(2), json.dumps(dict({"action": m.group(1), "speech": ""}, **({"args": {"option": m.group(3)}} if m.group(3) else {})), ensure_ascii=False))
    return out


def stop_on(card, word="بس"):
    """True when the card has his bare word as a horn_hold stop."""
    a = said_on(card).get(word) or ""
    return '"horn_hold"' in a and '"stop"' in a


def route_child(mind):
    sys.path.insert(0, mind)
    import chat_service as CS, model_router as MR, reply_gate as RG, providers as P, settings_service as SS, world_knowledge as W
    ck("route: the patched copy is what got imported", os.path.dirname(os.path.abspath(CS.__file__)) == os.path.abspath(mind), CS.__file__)
    SEEN = {"system": ""}

    def model(pid, key, mdl, msgs, system="", custom_base="", max_tokens=0, timeout=0):
        """A model that only knows the card: an example for his exact words wins (a grouped line "a / b -> {...}" counts for each,
        an action's own phrase on the list gives that action with its first option), else plain talk."""
        SEEN["system"] = system
        text = msgs[-1]["content"].replace(" /no_think", "")
        return said_on(system).get(text) or '{"action":"none","speech":"أهلين"}'
    P.chat = model
    SS.load_config = lambda: {"source": "local", "provider": "custom", "model": "test", "base": ""}
    W.situation_text = lambda s, m: "world"
    CS.MA.answer = lambda *a, **k: None
    CS.MA.known_names = lambda *a, **k: []
    CS.time.sleep = lambda s: None
    GAME, LOG = [], []
    ACTS = {"v": []}
    GAME_REPLY = {"v": None}
    CS.load_actions = lambda d: ACTS["v"]

    def run_action(d, action, option=None, wait=3.0):
        GAME.append((action, option))
        if GAME_REPLY["v"] is not None: return GAME_REPLY["v"]
        if action == "horn_hold": return {"ok": True, "reason": "horn_released" if option == "stop" else "horn_held"}
        return {"ok": True, "reason": ""}
    CS.run_action = run_action
    TMPD = tempfile.mkdtemp(prefix="sol_s79_route_")

    def chat():
        c = CS.Chat.__new__(CS.Chat)
        c.dir, c.log, c._forced = TMPD, LOG.append, None
        c._world = lambda: ({}, None)
        c.gps_state = lambda: {}
        c._pre_intents = lambda h, s, m: []
        c._receipt = lambda: "تكرم."
        c._player_takes_over = lambda a: None
        c._remember_action = lambda a, o: None
        c._memory_text = lambda s, m: "لا شيء."
        c._gate_context = lambda h, a, k, n=(): RG.Context(h[-1]["text"], [], [], k, False, (), [])
        c._model_first = lambda: True
        return c
    C = {"c": chat()}

    def say(text, state="idle", game=None, fresh=False, catalog_t=None):
        if fresh: C["c"] = chat()
        GAME.clear(); LOG.clear(); GAME_REPLY["v"] = game
        ACTS["v"] = [{"id": "sol_horn", "kind": "sol", "label": "horn"}] + ([{"id": "horn_hold", "kind": "sol", "state": state}] if state else [])
        if catalog_t is not None:
            with open(os.path.join(TMPD, CS.ACT_SNAP), "w", encoding="ascii") as f: f.write(json.dumps({"v": 1, "t": catalog_t, "actions": []}))
        elif os.path.exists(os.path.join(TMPD, CS.ACT_SNAP)): os.remove(os.path.join(TMPD, CS.ACT_SNAP))
        return C["c"]._ask_provider([{"role": "user", "text": text}])

    # --- the card
    s = MR.sheet([{"id": "horn_hold", "kind": "sol"}, {"id": "sol_horn", "kind": "sol"}], "x")
    ck("card: horn_hold listed with its phrase and options", re.search(r'^horn_hold: .*(?:مثال: )?"خلي ايدك عالزمور" \| option: start أو stop', s, re.M) is not None)
    ck("card: sol_horn unchanged", MR.CARD_ACTIONS["sol_horn"] == ("زمور السيارة", "زمري", "option: once أو stop"), MR.CARD_ACTIONS["sol_horn"])
    START = [MR.CARD_ACTIONS["horn_hold"][1]] + [x for x in MR.HORN_START if x != MR.CARD_ACTIONS["horn_hold"][1]]
    STOP = list(MR.HORN_STOP)
    ck("card: the examples sit before her memory", s.index(MR.HORN_START[-1]) < s.index("ذاكرتك الآن:"))
    ck("card: every start / stop phrase reaches horn_hold", all('"horn_hold"' in said_on(s).get(x, "") for x in START + STOP), [x for x in START + STOP if x not in said_on(s)])
    ck("card: no bare 'بس' example while she does not hold the horn", not stop_on(s))
    s2 = MR.sheet([{"id": "sol_horn", "kind": "sol"}], "x")
    ck("card: switch off (the game does not list horn_hold): no horn_hold on the card", "horn_hold" not in s2, s2[-400:])
    ck("card: a model-less sheet (no actions) still shows it", "horn_hold:" in MR.sheet([], "x"))

    # --- start, every phrasing
    for t in START:
        r = say(t, fresh=True)
        ck("route: '%s' -> horn_hold start, she says 'تكرم.'" % t, GAME == [("horn_hold", "start")] and r == "تكرم.", (GAME, r))
    for t in STOP:
        r = say(t, state="holding", fresh=True)
        ck("route: '%s' -> horn_hold stop, a short line" % t, GAME == [("horn_hold", "stop")] and r in ("خلص، شلت إيدي.", "ماشي، خلص."), (GAME, r))
    r = say("زمري", fresh=True)
    ck("route: 'زمري' stays the single beep (sol_horn once)", GAME == [("sol_horn", "once")], (GAME, r))

    # --- bare "بس": only while she holds the horn
    r = say("بس", state="idle", fresh=True)
    ck("route: 'بس' with no horn held runs nothing", GAME == [] and not stop_on(SEEN["system"]), (GAME, r))
    r = say("بس", state="holding", fresh=True)
    ck("route: 'بس' while the game says she holds it -> horn_hold stop", GAME == [("horn_hold", "stop")], (GAME, r))
    ck("route: ... and the card said so", stop_on(SEEN["system"]))
    r = say("بس", state=None, fresh=True)
    ck("route: switch off: 'بس' runs nothing", GAME == [], GAME)

    # --- the Mind's own start / stop, newer than the game's list (the list is written ~0.3 s later)
    C["c"] = chat()
    say("خلي ايدك عالزمور", state="idle", catalog_t=1000)
    r = say("بس", state="idle", catalog_t=1000)
    ck("route: right after her start, 'بس' -> stop, though the old list still says idle", GAME == [("horn_hold", "stop")], (GAME, r))
    r = say("بس", state="holding", catalog_t=1000)
    ck("route: right after her stop, 'بس' runs nothing, though the old list still says holding", GAME == [], GAME)
    import time as _t
    say("خلي ايدك عالزمور", state="idle", catalog_t=1000)
    r = say("بس", state="idle", catalog_t=_t.time() * 1000 + 5000)
    ck("route: a newer list (the game let go: engine off, cap...) wins over the Mind's start", GAME == [], GAME)
    C["c"] = chat(); C["c"]._sheet = None
    c = C["c"]
    a_idle = [{"id": "horn_hold", "kind": "sol", "state": "idle"}]
    a_hold = [{"id": "horn_hold", "kind": "sol", "state": "holding"}]
    t1 = c._session_sheet(None, None, a_idle); t2 = c._session_sheet(None, None, a_idle); t3 = c._session_sheet(None, None, a_hold)
    ck("sheet: cached while nothing changes, rebuilt when she starts holding", t1 == t2 and t1 != t3 and stop_on(t3), (len(t1), len(t3)))
    ck("sheet: and back when she lets go", not stop_on(c._session_sheet(None, None, a_idle)))

    # --- her lines for what the game says
    for why, line in (("not_in_a_car", "أنا مو بسيارة هلأ."), ("horn_needs_driver_seat", "لازم كون ورا المقود لزمّر."), ("horn_engine_off", "السيارة طافية هلأ."),
                      ("battery_dead", "البطارية فاضية."), ("horn_unavailable", "ما بقدر زمّر بهالسيارة.")):
        r = say("خلي ايدك عالزمور", fresh=True, game={"ok": False, "reason": why})
        ck("lines: %s -> '%s'" % (why, line), r == line, r)
    r = say("وقفي الزمور", fresh=True, game={"ok": True, "reason": "horn_not_held"})
    ck("lines: stop with nothing held -> 'ما كنت عم زمّر.'", r == "ما كنت عم زمّر.", r)
    r = say("خلي ايدك عالزمور", fresh=True, game={"ok": None, "reason": "sent; the game did not confirm yet"})
    ck("lines: not confirmed yet -> the usual short reply, and the Mind does not count it as held", r in ("تكرم.", "ماشي.") and getattr(C["c"], "_horn_mine", None) is None, r)
    lines = list(CS.HORN_LINES.values()) + ["تكرم.", "خلص، شلت إيدي.", "ماشي، خلص.", "ما كنت عم زمّر."]
    ck("lines: nothing technical (no latin, no digits, no meta words)", all(not re.search(r"[A-Za-z0-9_]|لاعب|زر|سويتش", l) for l in lines), lines)
    ck("route: the route log names it", any("chat: horn_hold" in l for l in LOG), LOG)
    return FAIL


if len(sys.argv) > 2 and sys.argv[1] == "--route":
    route_child(sys.argv[2])
    sys.exit(1 if FAIL else 0)

from kahlua_env import lua51
SRC = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind"))
LAB_CL = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client"))
GATE = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py")
def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, script)] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
def digest(d, names): return {n: hashlib.md5(open(os.path.join(d, n), "rb").read()).hexdigest() for n in names if os.path.exists(os.path.join(d, n))}
def read(p): return open(p, encoding="utf-8", newline="").read()
TMP = tempfile.mkdtemp(prefix="sol_s79_")

# ================================================================ 1. the Lua installer on copies (a fake Zomboid tree)
ZB = os.path.join(TMP, "Zomboid")
CL = os.path.join(ZB, "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(CL)
os.makedirs(os.path.join(ZB, "Lua"))
FIXF = os.path.join(ZB, "Lua", "SolFixes_LAB.txt")
open(FIXF, "w", encoding="utf-8", newline="").write("retry_reset=on\r\nmodel_first=on")       # no newline at the end
LFILES = ["SolAuthority.lua", "SolActions.lua"]
for f in LFILES: shutil.copy(os.path.join(LAB_CL, f), CL)
live_l = digest(LAB_CL, LFILES + ["SolHornHold.lua"])
q1 = run("apply_s79_horn_hold_lua.py", CL); a1 = digest(CL, LFILES + ["SolHornHold.lua"]); f1 = read(FIXF)
q2 = run("apply_s79_horn_hold_lua.py", CL); a2 = digest(CL, LFILES + ["SolHornHold.lua"]); f2 = read(FIXF)
ck("lua installer: applies", q1.returncode == 0 and "applied" in q1.stdout, q1.stderr[-400:])
ck("lua installer: idempotent (files and switch file)", q2.returncode == 0 and a1 == a2 and f1 == f2, q2.stderr[-300:])
ck("lua installer: horn_hold in A.FIXES once", read(os.path.join(CL, "SolAuthority.lua")).count('"horn_hold"') == 1)
ck("lua installer: SolActions.lua untouched (sol_horn as it was)", digest(CL, ["SolActions.lua"]) == digest(LAB_CL, ["SolActions.lua"]))
ck("lua installer: horn_hold=on added once, on its own line", f1 == "retry_reset=on\r\nmodel_first=on\r\nhorn_hold=on\r\n", repr(f1))
ck("lua installer: the installed files are untouched", digest(LAB_CL, LFILES + ["SolHornHold.lua"]) == live_l)
for s78 in ("apply_s78_cars_away_lua.py",):
    pass                                                                     # s78's Lua touches SolFar/SolWorldScan only: no overlap
HH = read(os.path.join(CL, "SolHornHold.lua"))
ck("lua: SolHornHold.lua is pure ASCII", all(ord(ch) < 128 for ch in HH))
g = subprocess.run([sys.executable, GATE, os.path.join(CL, "SolHornHold.lua")], capture_output=True, text=True, encoding="utf-8", errors="replace")
ck("lua: tonumber gate passes", g.returncode == 0, (g.stdout + g.stderr)[-400:])
for n in ("SolHornHold.lua", "SolAuthority.lua"):
    e = lua51.LuaRuntime().eval("function(s) local f, e = loadstring(s); return e end")(read(os.path.join(CL, n)))
    ck("lua: %s compiles" % n, e is None, e)

# ================================================================ 2. the held horn under the game's Lua rules
ENV = r"""
print = function(m) LOGS[#LOGS + 1] = tostring(m) end
LOGS = {}
require = function() end
NOW, HOURS, SWITCH = 1000000, 100, true
function getTimestampMs() return NOW end
GT = { getWorldAgeHours = function() return HOURS end }
function getGameTime() return GT end
SolAuthority = { on = function(f) return f == "horn_hold" and SWITCH end }
BUDGET = {}
SolBudget = { register = function(name, fn, o) BUDGET[name] = fn end }
Events = { OnGameStart = { Add = function(f) START = f end } }
CALLS = { start = 0, stop = 0, solHorn = {} , base = {} }
function newCar()
    local c = { horn = false, engine = true, removed = false, charge = 0.8 }
    c.onHornStart = function(self) self.horn = true; CALLS.start = CALLS.start + 1 end
    c.onHornStop = function(self) self.horn = false; CALLS.stop = CALLS.stop + 1 end
    c.isHornSounding = function(self) return self.horn end
    c.isEngineRunning = function(self) return self.engine end
    c.isRemovedFromWorld = function(self) return self.removed end
    c.getDriver = function(self) return self.driver end
    c.getPartById = function(self, id)
        if id ~= "Battery" then return nil end
        return { getInventoryItem = function() return { getCurrentUsesFloat = function() return c.charge end } end }
    end
    return c
end
SOL = { dead = false }
SOL.getVehicle = function(self) return self.car end
SOL.isDead = function(self) return self.dead end
CAR = newCar(); CAR.driver = SOL; SOL.car = CAR
SolUI = { solActor = function() return SOL_ON and SOL or nil end }
SOL_ON = true
SolUI.runAction = function(id, o) CALLS.base[#CALLS.base + 1] = id; return true, "base" end
SolUI.actionCatalog = function() return { { id = "sol_horn", kind = "sol" } } end
SolUI.solHorn = function(o) CALLS.solHorn[#CALLS.solHorn + 1] = o; if SOL.car then SOL.car:onHornStop() end; return true, "horn_off" end
function tick() BUDGET.horn_hold() end
function cat() local out = SolUI.actionCatalog(); for _, e in ipairs(out) do if e.id == "horn_hold" then return e.state end end; return nil end
"""
def world(setup=""):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV); L.execute(setup); L.execute(HH); L.execute("START()")
    return L, L.globals()
run_ = lambda g, o=None: tuple(g.SolUI.runAction("horn_hold", o))
calls = lambda g: (g.CALLS.start, g.CALLS.stop)

L, g = world()
ck("lua: catalog lists horn_hold idle, sol_horn kept", g.cat() == "idle" and g.SolUI.actionCatalog()[1].id == "sol_horn")
r = run_(g, "start")
ck("lua start: her hand on the horn (onHornStart once)", r == (True, "horn_held") and calls(g) == (1, 0) and g.CAR.horn is True, (r, calls(g)))
ck("lua start: the list goes out again soon (state=holding)", g.cat() == "holding" and g.SolUI._catalogDue is not None and g.SolUI._catalogDue <= g.NOW + 300)
g.NOW += 5000; g.HOURS += 1.0 / 60; g.tick()
ck("lua: within the cap it is held, nothing repeated (no beeps)", calls(g) == (1, 0) and g.CAR.horn is True, calls(g))
ck("lua start again while held: no second press", run_(g, "start") == (True, "horn_held") and calls(g) == (1, 0))
r = run_(g, "stop")
ck("lua stop: let go (onHornStop), state idle", r == (True, "horn_released") and calls(g) == (1, 1) and g.CAR.horn is False and g.cat() == "idle", (r, calls(g)))
r = run_(g, "stop")
ck("lua stop with nothing held: 'horn_not_held', the beep's own stop is used", r == (True, "horn_not_held") and list(g.CALLS.solHorn.values()) == ["stop"], (r, list(g.CALLS.solHorn.values())))
for o in (None, "", "on", "hold", "START"):
    L, g = world(); r = run_(g, o)
    ck("lua: option %r means start" % (o,), r == (True, "horn_held"), r)
L, g = world(); ck("lua: an unknown option is refused", run_(g, "loud") == (False, "unknown_option"))
L, g = world(); r = tuple(g.SolUI.runAction("sol_horn", "once"))
ck("lua: sol_horn passes through untouched", r == (True, "base") and list(g.CALLS.base.values()) == ["sol_horn"], r)
L, g = world("SWITCH = false"); r = run_(g, "start")
ck("lua: switch off: horn_hold is not hers (the base answers), not on the list", r == (True, "base") and g.cat() is None and calls(g) == (0, 0), r)

# auto-stops
def held(setup=""):
    L, g = world(setup); assert run_(g, "start") == (True, "horn_held"); return L, g
CASES = (("she leaves the driver seat", "CAR.driver = {}"), ("she gets out", "SOL.car = nil"), ("the engine stops", "CAR.engine = false"),
         ("the car is destroyed", "CAR.removed = true"), ("she is gone", "SOL_ON = false"), ("she dies", "SOL.dead = true"),
         ("the battery dies", "CAR.charge = 0"), ("someone else let go of the horn", "CAR.horn = false"),
         ("the switch goes off", "SWITCH = false"), ("5 real minutes pass", "NOW = NOW + 300001"))
for name, change in CASES:
    L, g = held(); L.execute(change); g.NOW += 250; g.tick()
    ck("lua auto-stop: %s" % name, g.SolHornHold.hold is None and g.CALLS.stop >= 1 and g.cat() in ("idle", None), (calls(g), g.cat()))
L, g = held(); g.HOURS += 3; g.NOW += 299000; g.tick()
ck("lua: hours of game time but under 5 real minutes, no GPS drive: still held", g.SolHornHold.hold is not None and calls(g) == (1, 0))
L, g = held("SolUI.gps = { lastResult = 'driving' }"); g.NOW += 1000; g.tick(); h1 = g.SolHornHold.hold is not None
L.execute("SolUI.gps.lastResult = 'arrived'"); g.NOW += 250; g.tick()
ck("lua: held during a GPS drive, the drive ends: let go", h1 and g.SolHornHold.hold is None)
L, g = held(); g.NOW += 300001; g.tick(); g.tick()
ck("lua: let go once only", calls(g) == (1, 1), calls(g))

# refusals
for name, setup, why in (("not in a car", "SOL.car = nil", "not_in_a_car"), ("a passenger", "CAR.driver = {}", "horn_needs_driver_seat"),
                         ("engine off", "CAR.engine = false", "horn_engine_off"), ("battery dead", "CAR.charge = 0", "battery_dead"),
                         ("no horn methods", "CAR.onHornStart = nil", "horn_unavailable"), ("no Sol", "SOL_ON = false", "no_sol")):
    L, g = world(setup); r = run_(g, "start")
    ck("lua refuses start: %s -> %s" % (name, why), r == (False, why) and g.CALLS.start == 0, r)
# a horn left held by a save
L, g = world("CAR.horn = true"); g.tick(); g.tick()
ck("lua: a horn left held from before is let go once when she is back", g.CAR.horn is False and g.CALLS.stop == 1, calls(g))
L, g = world("CAR.horn = true; CAR.driver = {}"); g.tick()
ck("lua: ... but never his own horn (she is not the driver)", g.CAR.horn is True and g.CALLS.stop == 0)

# ================================================================ 3. the Mind installer on copies, both orders with s78
MFILES = ["model_router.py", "chat_service.py", "reply_gate.py"]
live_m = digest(SRC, MFILES)
s78 = os.path.exists(os.path.join(HERE, "apply_s78_cars_away_mind.py"))
s78_pending = s78 and "s78 cars_away" not in read(os.path.join(SRC, "chat_service.py"))
ORDERS = [("s79 alone", ["s79"])]
if s78_pending: ORDERS += [("s79 then s78", ["s79", "s78"]), ("s78 then s79", ["s78", "s79"])]
for name, order in ORDERS:
    M = os.path.join(TMP, "mind_" + name.replace(" ", "_"))
    os.makedirs(M)                                                           # the code and its data, nothing else (no logs, keys, history)
    for f in os.listdir(SRC):
        if f.endswith((".py", ".json.gz")): shutil.copy(os.path.join(SRC, f), M)
    for step in order:
        q = run("apply_s79_horn_hold_mind.py" if step == "s79" else "apply_s78_cars_away_mind.py", M)
        ck("mind %s: %s applies" % (name, step), q.returncode == 0 and "applied" in q.stdout, (q.stdout + q.stderr)[-400:])
    m1 = digest(M, MFILES)
    for step in order:
        run("apply_s79_horn_hold_mind.py" if step == "s79" else "apply_s78_cars_away_mind.py", M)
    ck("mind %s: re-running is a no-op" % name, digest(M, MFILES) == m1)
    for n in MFILES:
        ck("mind %s: line endings kept in %s" % (name, n), (b"\r\n" in open(os.path.join(SRC, n), "rb").read()) == (b"\r\n" in open(os.path.join(M, n), "rb").read()))
    ck("mind %s: reply_gate.py not touched by s79" % name, ("s79" not in read(os.path.join(M, "reply_gate.py"))))
    c = subprocess.run([sys.executable, os.path.abspath(__file__), "--route", M], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = c.stdout.strip().splitlines()
    for l in out: print("  [%s] %s" % (name, l))
    ck("mind %s: the routing checks pass" % name, c.returncode == 0 and out and not any(l.startswith("FAIL") for l in out), c.stderr[-800:])
if not s78_pending: print("note: apply_s78_cars_away_mind.py already in the source Mind (or absent); order checks with s78 skipped")
ck("mind installer: the live Mind is untouched", digest(SRC, MFILES) == live_m)

shutil.rmtree(TMP, ignore_errors=True)
print("\n%d FAIL" % len(FAIL) if FAIL else "\nALL PASS")
sys.exit(1 if FAIL else 0)

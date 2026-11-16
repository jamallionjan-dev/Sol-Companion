"""s109 reply_after_result offline: apply_s109_reply_after_result_mind.py on temp copies of 05_TOOLS/sol_mind (*.py and *.gz; the
live Mind is only read), apply_s109_reply_after_result.py on a temp copy of the lab client. The real Chat code runs (model routing,
_pre_intents, the far pieces, the watchers) with a mocked model and a scripted game (run_action / the GPS state file / the goals).
Shows:
  replay 15:03-15:04: come_car -> car_not_near -> the old far move: she says the car stops at the nearest road and she will say
    where (not "جاية بالسيارة"); placed -> he hears where (distance + direction); "اديش بدك لتوصلي" -> not "أنا هنا معك";
    "تعي لعندي مشي" while placed -> the road line, not "جاية، اصبر شوي".
  far, car not possible -> the reason first, then on foot; nothing possible -> a refusal (no "جاية").
  success unchanged: her car near him; the far_car inside arrival (",in").
  near him: the drive started -> "رايحة عالسيارة وجايتك."; no car -> s88's reason + on foot; no answer -> "ثانية" then the answer.
  every action with a result: a refusal in s88's words; not confirmed -> "ثانية، عم شوف." then the late answer; confirmed in the
    extra wait -> the usual line.
  switch off: every reply exactly as the unpatched Mind. Installers idempotent; install order after s92 (staged); gates.
Run: python test_s109_reply_after_result.py"""
import json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LIVE_MIND = os.path.join(ROOT, "05_TOOLS", "sol_mind")
LAB = os.path.join(ROOT, "07_TEST", "SOL_LAB")
CL = os.path.join(LAB, "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
PROFILE = os.path.join(LAB, "profile", "Zomboid", "Lua")
KAH = os.path.join(ROOT, "05_TOOLS", "sol_kahlua")
FAIL, P = [], []
def ck(n, c, d=""): print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else "")); (P if c else FAIL).append(n)
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
tmp = tempfile.mkdtemp(prefix="s109_")


def copy_mind(name):
    d = os.path.join(tmp, name); os.makedirs(d)
    for f in os.listdir(LIVE_MIND):
        if f.endswith((".py", ".gz")): shutil.copy(os.path.join(LIVE_MIND, f), d)
    return d


def run(*a): return subprocess.run([sys.executable] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)


old, new, order = copy_mind("old"), copy_mind("new"), copy_mind("order")
APPLY = os.path.join(HERE, "apply_s109_reply_after_result_mind.py")
r1, r2 = run(APPLY, new), run(APPLY, new)
ck("mind installer runs", r1.returncode == 0 and "appended" in r1.stdout, r1.stdout + r1.stderr)
ck("mind installer second run changes nothing", r2.returncode == 0 and "kept" in r2.stdout and "appended" not in r2.stdout, r2.stdout + r2.stderr)
s92 = run(os.path.join(HERE, "apply_s92_come_car_mind.py"), order)
r3 = run(APPLY, order)
ck("install order: after the staged s92 Mind patch too", s92.returncode == 0 and r3.returncode == 0 and "appended" in r3.stdout, s92.stdout + s92.stderr + r3.stdout + r3.stderr)
ck("the patched chat_service.py compiles", run("-m", "py_compile", os.path.join(new, "chat_service.py")).returncode == 0)

CHILD = r'''
import json, os, random, re, sys, tempfile, threading, time
sys.path.insert(0, sys.argv[1])
import chat_service as CS, model_router as MR, reply_gate as RG, providers as P, settings_service as SS, world_knowledge as W, road_route as RR
SWITCH = sys.argv[2]
random.seed(1)
W.situation_text = lambda s, m: "world"
RR.pickup_spot_dir = lambda cx, cy, px, py, ring, kind="car", inner=False: (8100.5, 11079.5, 3743.550712336325, 90.0)   # the live answer (log 15:03:05)
for k in ("EXTRA_WAIT_S109", "HERE_WAIT_S109"):
    if hasattr(CS, k): setattr(CS, k, 0.4)
OUT = []
FAR_SNAP = {"player": {"x": 8079, "y": 11166, "z": 0}, "sol": {"away": True}, "knownStreets": []}
HERE_SNAP = {"player": {"x": 10825, "y": 10121, "z": 0}, "sol": {"x": 10829, "y": 10121, "z": 0}, "knownStreets": ["S Main St"], "vehicles": [{"x": 10840, "y": 10121, "name": "car"}]}


class Game:
    """sol_far answers by option (a function of the call count for poll/status), other actions by name."""
    def __init__(self, far=None, acts=None):
        self.far, self.acts, self.calls = dict(far or {}), dict(acts or {}), []
    def __call__(self, d, action, option=None, wait=3.0):
        self.calls.append([action, option])
        if action == "sol_far":
            o = str(option or "")
            v = self.far.get("car_far" if o.startswith("car_far:") else o)
            if callable(v): v = v()
            if v is None: v = (False, "unknown_option")
        else:
            v = self.acts.get(action, (True, ""))
        if isinstance(v, dict): return dict(v)
        return {"ok": v[0], "reason": v[1]}


class Goals:
    """A stand-in GoalEngine: submit records the goal; after(g) plays the game's first answer to it."""
    def __init__(self, after=None):
        self.lock, self.active, self.history, self.after, self.submitted = threading.RLock(), None, [], after, []
    def submit(self, goal):
        g = dict(goal, id="goal-1", status="running", phase="resolve", reason="accepted")
        self.submitted.append(goal); self.active = g
        if self.after: self.after(g)
        return {"ok": True, "goalId": "goal-1", "status": "running", "phase": "resolve"}
    def cancel(self, g=None, reason=""): return False
    def describe(self): return "none"
    def wait_answer(self, gid, seconds=3.0): return None


def chat(d, snap, game, goals=None):
    CS.run_action = game
    c = CS.Chat.__new__(CS.Chat)
    c.dir, c.log, c._forced, c._sheet = d, LOG.append, None, None
    c.lock, c.hist = threading.Lock(), []
    c._save = lambda: None
    c.publish = lambda: None
    c._world = lambda: (snap, None)
    c.goals = goals or Goals()
    c._player_takes_over = lambda a: None
    c._remember_action = lambda a, o: None
    c._memory_text = lambda s, m: ""
    c._gate_context = lambda h, a, k, n=(): RG.Context(h[-1]["text"], [], [], k, False, (), [])
    c._model_first = lambda: True
    c._station_list = lambda: []
    c._street_now = lambda: ""
    c._gardens = lambda: []
    c._farm_orders = lambda *a: None
    c._stop_farm_if_running = lambda s: None
    return c


MODEL = {}
P.chat = lambda *a, **k: json.dumps(MODEL["reply"], ensure_ascii=False)
CFG = {"source": "local", "provider": "custom", "model": "test", "base": ""}
SS.load_config = lambda: CFG
CS.load_actions = lambda d: [{"id": i, "kind": "sol", "label": i} for i in ("sol_engine", "sol_horn", "regroup")]


def say(c, text, model, snap):
    MODEL["reply"] = model
    del LOG[:]
    try: r = c._route_by_model([{"role": "user", "text": text}], CFG, "", snap, None)
    except Exception as e: r = "ERROR %r" % (e,)
    return r


def lua_dir():
    d = tempfile.mkdtemp(prefix="s109_lua_")
    open(os.path.join(d, "SolFixes_LAB.txt"), "w", encoding="utf-8").write("fail_reasons=on\nreply_after_result=%s\n" % SWITCH)
    return d


def state(d, name, kv):
    open(os.path.join(d, name), "w", encoding="ascii").write("".join("%s=%s\n" % kv_ for kv_ in kv.items()))


LOG = []
def rec(name, **kw): kw["case"] = name; OUT.append(kw)

# A. the live case, 15:03-15:04
d = lua_dir()
polls = {"n": 0}
g = Game(far={"status": (True, "awake:2832"), "come_car": (False, "car_not_near"), "car_where": (True, "car:7413,8264,8079,11166,9"),
              "car_far": (True, "waiting:180"), "poll": (True, "placed"), "come": (True, "placed")})
c = chat(d, FAR_SNAP, g)
r1 = say(c, "سوقي السيارة وتعي لعندي", {"action": "come_car", "speech": ""}, FAR_SNAP)
calls1 = [x[:] for x in g.calls]
g.far["status"] = (True, "placed")
c._far_watch()
told = [m["text"] for m in c.hist]
r2 = say(c, "اديش بدك لتوصلي", {"action": "none", "speech": "أنا هنا معك"}, FAR_SNAP)
r3 = say(c, "تعي لعندي مشي", {"action": "come_foot", "speech": ""}, FAR_SNAP)
rec("replay", r1=r1, calls1=calls1, told=told, r2=r2, r3=r3, waiting=getattr(c, "_far_waiting", None))

# B. far, the car not possible
for name, far in (("no_fuel", {"come_car": (False, "no_fuel")}),
                  ("too_close", {"come_car": (False, "car_not_near"), "car_where": (False, "car_too_close")}),
                  ("no_spot", {"come_car": (False, "car_not_near"), "car_where": (True, "car:7413,8264,8079,11166,9"), "car_far": (False, "no_fuel")})):
    base = {"status": (True, "awake:2832"), "come": (True, "waiting:300")}
    base.update(far)
    c = chat(lua_dir(), FAR_SNAP, Game(far=base))
    rec("foot_" + name, r=say(c, "سوقي السيارة وتعي لعندي", {"action": "come_car", "speech": ""}, FAR_SNAP))
c = chat(lua_dir(), FAR_SNAP, Game(far={"status": (True, "awake:2832"), "come_car": (False, "car_not_near"), "car_where": (False, "no_car"), "come": (False, "cannot_travel")}))
rec("nothing", r=say(c, "سوقي السيارة وتعي لعندي", {"action": "come_car", "speech": ""}, FAR_SNAP))

# C. success unchanged
c = chat(lua_dir(), FAR_SNAP, Game(far={"status": (True, "awake:120"), "come_car": (True, "waiting:180")}))
rec("near_car", r=say(c, "سوقي السيارة وتعي لعندي", {"action": "come_car", "speech": ""}, FAR_SNAP))
c = chat(lua_dir(), FAR_SNAP, Game(far={"status": (True, "awake:2832"), "come_car": (False, "car_not_near"), "car_where": (True, "car:7413,8264,8079,11166,9,car,in"), "car_far": (True, "waiting:180")}))
rec("far_inside", r=say(c, "سوقي السيارة وتعي لعندي", {"action": "come_car", "speech": ""}, FAR_SNAP))
c = chat(lua_dir(), FAR_SNAP, Game(far={"status": (True, "awake:2832"), "come": (True, "waiting:300")}))
rec("far_foot", r=say(c, "تعي لعندي مشي", {"action": "come_foot", "speech": ""}, FAR_SNAP))
c = chat(lua_dir(), FAR_SNAP, Game(far={"status": (True, "waiting:120")}))
rec("far_chat_other", r=say(c, "شو اسمك", {"action": "none", "speech": "اسمي سول."}, FAR_SNAP))

# D. near him (her body is here)
def here(after, d=None):
    d = d or lua_dir()
    goals = Goals(after)
    c = chat(d, HERE_SNAP, Game(), goals)
    r = say(c, "سوقي السيارة وتعي لعندي", {"action": "come_car", "speech": ""}, HERE_SNAP)
    return c, goals, r
def no_car(g): g.update(status="completed", reason="coming_on_foot:no_vehicle_near")
c, goals, r = here(no_car)
rec("here_no_car", r=r, quiet=[(x.get("slots") or {}).get("quiet") for x in goals.submitted])
d = lua_dir()
state(d, "SolGPS_State.txt", {"ack": 5, "result": "failed", "reason": "walking_to_door"})
c, goals, r = here(lambda g: g.update(gpsRid=5, phase="driving_to_player"), d)
rec("here_started", r=r)
c, goals, r = here(None)
goals.active.update(status="completed", reason="coming_on_foot:no_usable_car")
if hasattr(CS, "_s109_watch"): CS._s109_watch(c)
rec("here_late", r=r, later=[m["text"] for m in c.hist])

# E. any action with a result
d = lua_dir()
c = chat(d, HERE_SNAP, Game(acts={"sol_engine": (False, "no_key")}))
rec("act_refused", r=say(c, "شغلي السيارة", {"action": "sol_engine", "args": {"option": "on"}, "speech": ""}, HERE_SNAP))
d = lua_dir()
c = chat(d, HERE_SNAP, Game(acts={"sol_engine": {"ok": None, "reason": "sent; the game did not confirm yet", "rid": 42}}))
r = say(c, "شغلي السيارة", {"action": "sol_engine", "args": {"option": "on"}, "speech": ""}, HERE_SNAP)
state(d, "SolAct_State.txt", {"ack": 42, "ok": "false", "reason": "battery_dead"})
if hasattr(CS, "_s109_watch"): CS._s109_watch(c)
rec("act_late", r=r, later=[m["text"] for m in c.hist])
d = lua_dir()
state(d, "SolAct_State.txt", {"ack": 43, "ok": "true", "reason": "on"})
c = chat(d, HERE_SNAP, Game(acts={"sol_engine": {"ok": None, "reason": "sent; the game did not confirm yet", "rid": 43}}))
rec("act_in_extra_wait", r=say(c, "شغلي السيارة", {"action": "sol_engine", "args": {"option": "on"}, "speech": ""}, HERE_SNAP))
c = chat(lua_dir(), HERE_SNAP, Game(acts={"sol_engine": (True, "on")}))
rec("act_ok", r=say(c, "شغلي السيارة", {"action": "sol_engine", "args": {"option": "on"}, "speech": ""}, HERE_SNAP))
print(json.dumps(OUT, ensure_ascii=False))
'''


def child(m, sw):
    r = subprocess.run([sys.executable, "-c", CHILD, m, sw], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV, cwd=tmp)
    if r.returncode: print(r.stdout[-2000:], r.stderr[-3000:]); return None
    return {c["case"]: c for c in json.loads(r.stdout.strip().splitlines()[-1])}


OK_WORDS = ("تكرم.", "ماشي.", "حاضر.")
FETCH = ("جايتك، استناني.", "مسافة الطريق وبكون عندك.")
def norm(v):
    if isinstance(v, str): return "<ok>" if v in OK_WORDS else "<fetch>" if v in FETCH else v
    if isinstance(v, list): return [norm(x) for x in v]
    if isinstance(v, dict): return {k: norm(x) for k, x in v.items() if k != "quiet"}
    return v


on, off, base = child(new, "on"), child(new, "off"), child(old, "on")
if os.environ.get("S109_DUMP") and on: print(json.dumps({k: on[k] for k in ("replay", "nothing", "here_late", "act_late")}, ensure_ascii=False, indent=0))
ck("patched Mind runs the scenarios (switch on and off), the unpatched one too", on is not None and off is not None and base is not None)
if on and off and base:
    ck("switch off = the old behaviour: every reply and every game call as the unpatched Mind", norm(off) == norm(base),
       json.dumps({k: (norm(off[k]), norm(base[k])) for k in off if norm(off[k]) != norm(base[k])}, ensure_ascii=False)[:1500])
    A, A0 = on["replay"], base["replay"]
    print("     15:03 before: " + str(A0["r1"]) + "\n     15:03 now:    " + str(A["r1"]))
    ck("replay 15:03, old Mind: 'جاية بالسيارة، بدي 3 دقايق.' (the live line)", A0["r1"] == "جاية بالسيارة، بدي 3 دقايق.", A0["r1"])
    ck("replay 15:03: the game is asked first (status, come_car -> car_not_near, car_where, car_far), then she speaks",
       [c[1] if not str(c[1]).startswith("car_far:") else "car_far" for c in A["calls1"]] == ["status", "come_car", "car_where", "car_far"], A["calls1"])
    ck("replay 15:03: no 'جاية بالسيارة'; she says the car stops at the nearest road and she will say where",
       "جاية بالسيارة" not in A["r1"] and "سيارتي بعيدة كتير عنك" in A["r1"] and "لأقرب طريق منك" in A["r1"] and "3 دقايق" in A["r1"], A["r1"])
    ck("replay 15:03:22 placed: he hears where the car is, once (distance and side from him)",
       len(A["told"]) == 1 and "صرت بالسيارة عالطريق، شي 90 متر بالشمال منك" in A["told"][0], A["told"])
    ck("replay 15:03:22, old Mind: nothing said", A0["told"] == [], A0["told"])
    ck("replay 15:04:22 'اديش بدك لتوصلي': not 'أنا هنا معك'; the road line", A["r2"] != "أنا هنا معك" and "عالطريق" in A["r2"], A["r2"])
    ck("replay 15:04:22, old Mind: 'أنا هنا معك' (the live line)", A0["r2"] == "أنا هنا معك", A0["r2"])
    ck("replay 15:04:41 'تعي لعندي مشي' while placed: the road line, not 'جاية، اصبر شوي.'", A["r3"] != "جاية، اصبر شوي." and "قرّب لصوبي" in A["r3"], A["r3"])
    ck("replay 15:04:41, old Mind: 'جاية، اصبر شوي.' (the live line)", A0["r3"] == "جاية، اصبر شوي.", A0["r3"])
    ck("far, her car has no fuel: the reason, then on foot with the time", on["foot_no_fuel"]["r"] == "سيارتي ما فيها بنزين كفاية، فجاية مشي، بدي 5 دقايق.", on["foot_no_fuel"]["r"])
    ck("far, her car too close to move: the reason, then on foot", on["foot_too_close"]["r"].startswith("سيارتي مو بعيدة عنك بس ما بقدر جيبها من هون، فجاية مشي"), on["foot_too_close"]["r"])
    ck("far, the far move refused (no fuel for the road): the reason, then on foot", on["foot_no_spot"]["r"].startswith("سيارتي ما فيها بنزين كفاية، فجاية مشي"), on["foot_no_spot"]["r"])
    ck("old Mind in those cases: 'جاية مشي' with no reason", all(base[k]["r"] == "جاية مشي، بدي 5 دقايق." for k in ("foot_no_fuel", "foot_too_close", "foot_no_spot")))
    ck("far, nothing possible: a refusal, no 'جاية'", "جاية" not in on["nothing"]["r"] and on["nothing"]["r"] == base["nothing"]["r"], on["nothing"]["r"])
    for k in ("near_car", "far_inside", "far_foot", "far_chat_other"):
        ck("success unchanged: %s -> %s" % (k, on[k]["r"]), on[k]["r"] == base[k]["r"], (on[k]["r"], base[k]["r"]))
    ck("success: her car near him -> 'جاية بالسيارة، بدي 3 دقايق.'", on["near_car"]["r"] == "جاية بالسيارة، بدي 3 دقايق.", on["near_car"]["r"])
    ck("near him, no car she can drive: s88's reason + on foot", on["here_no_car"]["r"] == "ما كان في سيارة قريبة، فجاية مشي.", on["here_no_car"]["r"])
    ck("near him: the goal does not say its own line on top (quiet)", on["here_no_car"]["quiet"] == ["1"] and base["here_no_car"]["quiet"] == [None], (on["here_no_car"]["quiet"], base["here_no_car"]["quiet"]))
    ck("near him, the drive started (walking to the door): 'رايحة عالسيارة وجايتك.'", on["here_started"]["r"] == "رايحة عالسيارة وجايتك.", on["here_started"]["r"])
    ck("near him, old Mind: the order line before any answer", base["here_no_car"]["r"] in FETCH and base["here_started"]["r"] in FETCH)
    ck("near him, no answer yet: 'ثانية، عم شوف.', then the answer (locked cars, on foot)", on["here_late"]["r"] == "ثانية، عم شوف." and on["here_late"]["later"] == ["السيارات اللي حوالينا كلها مقفولة وما معنا مفاتيحها، فجاية مشي."], on["here_late"])
    ck("an action refused: s88's words for the reason", on["act_refused"]["r"] == "ما كان معي مفتاح هالسيارة.", on["act_refused"]["r"])
    ck("an action not confirmed: old Mind said a success word", base["act_late"]["r"] in OK_WORDS, base["act_late"]["r"])
    ck("an action not confirmed: 'ثانية، عم شوف.', then the late refusal in her words", on["act_late"]["r"] == "ثانية، عم شوف." and on["act_late"]["later"] == ["البطارية فاضية."], on["act_late"])
    ck("an action confirmed in the extra wait: the usual line", on["act_in_extra_wait"]["r"] in OK_WORDS, on["act_in_extra_wait"]["r"])
    ck("an action confirmed: unchanged", on["act_ok"]["r"] in OK_WORDS and base["act_ok"]["r"] in OK_WORDS)
    lines = [v for c in on.values() for k, v in c.items() if k in ("r", "r1", "r2", "r3") and isinstance(v, str)]
    ck("her lines carry no codes (no latin letters, no underscores)", not any(re.search(r"[A-Za-z_]", l) for l in lines), [l for l in lines if re.search(r"[A-Za-z_]", l)])
ordr = child(order, "on")
ck("install order (s92 Mind first): the 15:03 replay gives the same lines", ordr is not None and on is not None and norm(ordr["replay"]) == norm(on["replay"]), ordr and ordr.get("replay"))

# game side: switch registration on a temp copy of the client (+ a temp switch file next to it, same relative place)
prof = os.path.join(tmp, "profile", "Zomboid"); cl = os.path.join(prof, "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(cl); os.makedirs(os.path.join(prof, "Lua"))
for f in os.listdir(CL):
    if f.endswith(".lua"): shutil.copy(os.path.join(CL, f), cl)
fixes = os.path.join(prof, "Lua", "SolFixes_LAB.txt"); shutil.copy(os.path.join(PROFILE, "SolFixes_LAB.txt"), fixes)
LUA = os.path.join(HERE, "apply_s109_reply_after_result.py")
l1, l2 = run(LUA, cl), run(LUA, cl)
ck("game installer runs: SolAuthority edited, switch on in the lab file", l1.returncode == 0 and "edited SolAuthority.lua" in l1.stdout and "reply_after_result=on" in l1.stdout, l1.stdout + l1.stderr)
ck("game installer second run changes nothing", l2.returncode == 0 and "kept SolAuthority.lua" in l2.stdout and "kept SolFixes_LAB.txt" in l2.stdout, l2.stdout + l2.stderr)
auth = open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read()
ck("SolAuthority lists the switch once; ASCII", auth.count('"reply_after_result"') == 1 and all(ord(ch) < 128 for ch in auth))
ck("the switch file has reply_after_result=on once", open(fixes, encoding="utf-8").read().count("reply_after_result=on") == 1)
t = run("-I", os.path.join(KAH, "tonumber_check.py"), cl)
ck("tonumber gate on the patched client", t.returncode == 0, t.stdout[-400:])
j = run("-I", os.path.join(KAH, "jarcall_check.py"), cl)
ck("jarcall gate on the patched client", j.returncode == 0, j.stdout[-400:])
doc = os.path.join(tmp, "SOL_MODEL_CARD.md"); shutil.copy(os.path.join(ROOT, "DOCS", "SOL_MODEL_CARD.md"), doc)
cc = run("-I", os.path.join(KAH, "card_check.py"), new, "--lua", cl, "--fixes", fixes, "--doc", doc)
tail = cc.stdout.strip().splitlines()[-1] if cc.stdout.strip() else cc.stderr[-300:]
ck("card_check on the patched Mind + patched client (no card change): PASS", cc.returncode == 0, "\n".join(l for l in cc.stdout.splitlines() if l.startswith("FAIL"))[:800] or tail)
print("     " + tail)
ev = run(os.path.join(HERE, "test_s82_route_eval.py"), "--as-is", new)
ck("s82 route eval --as-is on the patched Mind: ALL PASS", ev.returncode == 0 and "ALL PASS" in ev.stdout, ev.stdout[-600:])
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(P), len(FAIL))); sys.exit(1 if FAIL else 0)

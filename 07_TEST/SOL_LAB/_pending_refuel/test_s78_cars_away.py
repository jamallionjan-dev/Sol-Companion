"""s78 cars_away: cars_near in all three states (beside him, live body away from him, body not loaded), come_car's phrases, and the
meta-word line gate. Real Mind code with a fake model and a fake game; the Lua under the game's rules (kahlua_env). Temporary copies only.
Run: set PYTHONIOENCODING=utf-8 & python test_s78_cars_away.py [sol_mind dir] [client dir]
     (defaults: 05_TOOLS/sol_mind and the lab client, both read only; nothing live is touched)
Offline PASS is not Runtime PASS."""
import glob, hashlib, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
SRC = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind"))
LAB_CL = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client"))
GATE = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua", "tonumber_check.py")
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, script)] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
def digest(d, names): return {n: hashlib.md5(open(os.path.join(d, n), "rb").read()).hexdigest() for n in names}
def read(p): return open(p, encoding="utf-8", newline="").read()
TMP = tempfile.mkdtemp(prefix="sol_s78_")

# ================================================================ 1. the Lua installer on copies
CL = os.path.join(TMP, "client"); os.makedirs(CL)
LFILES = ["SolFar.lua", "SolWorldScan.lua"]
for f in LFILES: shutil.copy(os.path.join(LAB_CL, f), CL)
live_l = digest(LAB_CL, LFILES)
b = digest(CL, LFILES)
q1 = run("apply_s78_cars_away_lua.py", CL); a1 = digest(CL, LFILES)
q2 = run("apply_s78_cars_away_lua.py", CL); a2 = digest(CL, LFILES)
ck("lua installer: applies", q1.returncode == 0 and "applied" in q1.stdout, q1.stderr[-400:])
ck("lua installer: changes both files", all(b[n] != a1[n] for n in LFILES))
ck("lua installer: idempotent", q2.returncode == 0 and a1 == a2, q2.stderr[-300:])
ck("lua installer: the installed files are untouched", digest(LAB_CL, LFILES) == live_l)
q = run("apply_s77_lua.py", CL); ck("lua: re-running apply_s77_lua.py after s78 changes nothing", q.returncode == 0 and digest(CL, LFILES) == a1, q.stderr[-300:])
g = subprocess.run([sys.executable, GATE, CL], capture_output=True, text=True, encoding="utf-8", errors="replace")
ck("lua: tonumber gate passes on the staged files", g.returncode == 0, (g.stdout + g.stderr)[-400:])
FAR_SRC, SWS_SRC = read(os.path.join(CL, "SolFar.lua")), read(os.path.join(CL, "SolWorldScan.lua"))
for n, s in (("SolFar.lua", FAR_SRC), ("SolWorldScan.lua", SWS_SRC)):
    e = lua51.LuaRuntime().eval("function(s) local f, e = loadstring(s); return e end")(s)
    ck("lua: %s compiles" % n, e is None, e)
ck("lua: the far_car block itself is untouched", 'if opt == "cars" and farCarOn() then return carsAnswer() end' in FAR_SRC)

# ================================================================ 2. SolFar "cars" under the game's Lua rules (the far_car harness)
_tf = read(os.path.join(HERE, "test_far.py")).replace("\r\n", "\n")
WORLD = re.search(r'WORLD = r"""(.*?)"""\nSRC', _tf, re.S).group(1)
_tc = read(os.path.join(HERE, "test_far_car.py")).replace("\r\n", "\n")
CARS = re.search(r'CARS = r"""(.*?)"""\ndef world', _tc, re.S).group(1)
def far_world(setup):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(WORLD); L.execute(CARS); L.execute(setup); L.execute(FAR_SRC)
    return L, L.globals()
far = lambda g, o: tuple(g.SolUI.solFar(o))
ROWS = 'LIST = "5,1610,1000,10,Base.SmallCar,30,80,0,100,9005,0,ok,1,0,0;6,1585,1000,15,Base.VanSeats,0,80,1,100,9006,0,locked,0,0,0"'
# her body registered, its square not loaded (21:35): she is at 1600,1000, he at 1000,1000
AWAY = ("LIVE_BODY = { getX = function() return 1600 end, getY = function() return 1000 end, getCurrentSquare = function() return nil end, "
        "getInventory = function() return { haveThisKeyId = function() return nil end } end }; SolUI.solActor = function() return LIVE_BODY end; ")
for sw in ("false", "true"):
    L, g = far_world(AWAY + "FARCAR = %s; " % sw + ROWS); g.alive(); g.clock(3000)
    r = far(g, "cars")
    head = "cars:2/own|" if sw == "false" else "cars:2|"
    ck("lua away, far_car %s: 'cars' answers from the saved rows" % ("off" if sw == "false" else "on"), r[0] is True and r[1].startswith(head + "5,Base.SmallCar,10,30.0,ok,0;6,Base.VanSeats,15,0.0,locked,0"), r)
    ck("lua away, far_car %s: asked around HER (1600,1000), not him" % ("off" if sw == "false" else "on"), [list(v.values()) for v in g.REQS.values()][:1] == [[1600, 1000, 25]], [list(v.values()) for v in g.REQS.values()])
L, g = far_world(AWAY + "FARCAR = false; " + ROWS); g.alive(); g.clock(3000)
ck("lua: far_car off: the switch still keeps its own work off (car_where = her own car, as before)", far(g, "car_where") == (True, "car:5000,5000,1000,1000,6"), far(g, "car_where"))
ck("lua: other options pass through (status)", far(g, "status")[1].startswith(("far:", "awake:")), far(g, "status"))
L, g = far_world("FARCAR = false; CN_STATE = 'idle'; function solCarsNearRequest(x, y, r) REQS[#REQS + 1] = { x, y, r }; CN_STATE = 'queued'; return true end; " + AWAY + ROWS)
g.alive(); g.clock(3000)
ck("lua: the list not in yet: 'scanning' (the Mind asks again)", far(g, "cars") == (False, "scanning"), far(g, "cars"))
HERE_BODY = "MD = {}; LIVE_BODY = { getX = function() return 1600 end, getY = function() return 1000 end, getCurrentSquare = function() return {} end }; SolUI.solActor = function() return LIVE_BODY end; "
L, g = far_world(HERE_BODY + "FARCAR = false; " + ROWS); g.alive(); g.clock(3000)
ck("lua: her body loaded: 'here' (the snapshot answers), nothing asked", far(g, "cars") == (True, "here") and len(g.REQS) == 0, (far(g, "cars"), len(g.REQS)))

# ================================================================ 3. SolWorldScan: solVehicles around HER
SCAN_ENV = r"""
print = function() end
require = function() end
SolText = {}
SolBudget = { register = function() end }
NOW = 1000
function getTimestampMs() return NOW end
INV = { haveThisKeyId = function(self, k) if k == 7 then return {} end return nil end }
function body(x, y) return { getX = function() return x end, getY = function() return y end, getZ = function() return 0 end,
                             getInventory = function() return INV end, getCurrentSquare = function() return {} end } end
PLAYER = body(1000, 1000)
function getSpecificPlayer() return PLAYER end
function getCell() return { getGridSquare = function() return nil end } end
function car(id, x, y, name, locked, kid)
    return { getX = function() return x end, getY = function() return y end, getSqlId = function() return id end,
             getScript = function() return { getName = function() return name end } end,
             getPartById = function(self, p)
                 if p == "GasTank" then return { getContainerContentAmount = function() return 20 end, getContainerCapacity = function() return 50 end } end
                 if p == "DoorFrontLeft" then return { getDoor = function() return { isLocked = function() return locked end } end } end
             end,
             isKeysInIgnition = function() return false end, isHotwired = function() return false end, getKeyId = function() return kid end,
             getPartCount = function() return 0 end }
end
CARS = {}
SurvivorCompanion = { Vehicle = { loadedVehicles = function() return CARS end } }
SolUI = { solActor = function() return SOL end, solFarState = function() return FARSTATE end }
"""
def scan(setup):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(SCAN_ENV); L.execute(setup); L.execute(SWS_SRC)
    s = L.eval("SolUI.scanWorld()")
    rows = lambda t: None if t is None else sorted((int(t[i].id), t[i].locked, t[i].key) for i in range(1, len(t) + 1))
    return {"vehicles": rows(s.vehicles), "solVehicles": rows(s.solVehicles), "away": s.sol and s.sol.away}
CARS3 = "CARS = { car(1, 1004, 1000, 'SmallCar', false, 7), car(2, 1105, 1000, 'VanSeats', true, 8), car(3, 1300, 1000, 'PickUpTruck', false, 7) }; "
s = scan(CARS3 + "SOL = body(1002, 1000)")
ck("scan, beside him: solVehicles = the cars around her", s["solVehicles"] == [(1, False, True)] and s["vehicles"] == [(1, False, True)], s)
s = scan(CARS3 + "SOL = body(1100, 1000)")
ck("scan, live body away from him: solVehicles around HER, with lock/key", s["solVehicles"] == [(2, True, False)], s)
ck("scan, live body away from him: vehicles stay around him", s["vehicles"] == [(1, False, True)], s)
s = scan(CARS3 + "SOL = body(1300, 1000); FARSTATE = 'far'")
ck("scan, body not loaded (away): no solVehicles (the Mind asks the game)", s["solVehicles"] is None and s["away"] is True, s)
s = scan(CARS3 + "SOL = nil")
ck("scan, no Sol: no solVehicles", s["solVehicles"] is None, s)

# ================================================================ 4. the Mind installer on a copy
MIND = os.path.join(TMP, "sol_mind"); os.makedirs(MIND)
for f in glob.glob(os.path.join(SRC, "*")):
    if os.path.isfile(f) and not f.endswith((".log", ".pem")): shutil.copy(f, MIND)
MFILES = ["chat_service.py", "model_router.py", "reply_gate.py"]
live_m = digest(SRC, MFILES)
b = digest(MIND, MFILES)
r1 = run("apply_s78_cars_away_mind.py", MIND); m1 = digest(MIND, MFILES)
r2 = run("apply_s78_cars_away_mind.py", MIND); m2 = digest(MIND, MFILES)
ck("mind installer: applies", r1.returncode == 0 and "applied" in r1.stdout, r1.stderr[-400:])
ck("mind installer: changes the three files", all(b[n] != m1[n] for n in MFILES))
ck("mind installer: idempotent", r2.returncode == 0 and m1 == m2, r2.stderr[-300:])
ck("mind installer: the live Mind is untouched", digest(SRC, MFILES) == live_m)
for script, args in (("apply_s77_mind.py", [MIND]), ("apply_s71_mind.py", [MIND]), ("apply_s72_far_arrival.py", ["-", MIND]), ("apply_s74_secret_loadout.py", ["-", MIND])):
    if not os.path.exists(os.path.join(HERE, script)): continue
    q = run(script, *args)
    ck("mind: re-running %s after s78 changes nothing" % script, q.returncode == 0 and digest(MIND, MFILES) == m1, (q.returncode, q.stderr[-300:]))
for n in MFILES:
    ck("mind: line endings kept in " + n, (b"\r\n" in open(os.path.join(SRC, n), "rb").read()) == (b"\r\n" in open(os.path.join(MIND, n), "rb").read()))

sys.path.insert(0, MIND)
import chat_service as CS, model_router as MR, reply_gate as RG, providers as P, settings_service as SS, world_knowledge as W, intent_engine as IE
ck("the patched copy is what got imported", os.path.dirname(os.path.abspath(CS.__file__)) == MIND, CS.__file__)

# ---------------------------------------------------------------- the card: come_car's phrases, nothing new
ex = dict(MR.EXAMPLES)
ck("card: come_car's phrase is 'تعالي لعندي بالسيارة'", MR.COMMANDS["come_car"][1] == "تعالي لعندي بالسيارة", MR.COMMANDS["come_car"])
ck("card: 'تعالي بالسيارة' and 'هاتي السيارة وتعي لعندي' are come_car examples", ex.get("تعالي بالسيارة") == "come_car" and ex.get("هاتي السيارة وتعي لعندي") == "come_car")
ck("card: come_foot unchanged", MR.COMMANDS["come_foot"] == ("لما تكون بعيدة: تجي مشي", "تعالي مشي"), MR.COMMANDS["come_foot"])
ck("card: no bare 'تعالي لعندي' example anywhere", "تعالي لعندي" not in ex and all(ph != "تعالي لعندي" for _m, ph in MR.COMMANDS.values()))
ck("card: no new action", len([k for k in MR.COMMANDS if k.startswith("come")]) == 2)
sheet = MR.sheet([], "x")
ck("card: the sheet shows come_car with its phrase", re.search(r'^come_car: .*(?:مثال: )?"تعالي لعندي بالسيارة"', sheet, re.M) is not None)
ck("card: the sheet tells the model not to say 'اللاعب'", "لا تقولي \"اللاعب\"" in sheet)
ck("come_car's phrase is the Mind's own 'come to me' (fetch_player)", (IE.parse_high_confidence("تعالي لعندي بالسيارة", {}) or {}).get("intent") == "fetch_player")

# ---------------------------------------------------------------- the chat with a fake model and a fake game
REPLY, GAME, LOG = {"v": ""}, [], []
P.chat = lambda pid, key, model, msgs, system="", custom_base="", max_tokens=0, timeout=0: REPLY["v"]
SS.load_config = lambda: {"source": "local", "provider": "custom", "model": "test", "base": ""}
W.situation_text = lambda s, m: "world"
CS.load_actions = lambda d: []
FAR = {"status": None, "cars": None, "come_car": None, "come": None}
def fake_run_action(d, action, option=None, wait=3.0):
    GAME.append((action, option))
    if action == "sol_far": return FAR.get(option) or {"ok": False, "reason": "here"}
    return {"ok": True}
CS.run_action = fake_run_action
CS.resolve_and_run = lambda d, a, o, m, s: (GAME.append((a, o)), {"ok": True})[1]
CS.time.sleep = lambda s: None
def chat(snap, pre=None):
    c = CS.Chat.__new__(CS.Chat)
    c.dir, c.log, c._forced = TMP, LOG.append, None
    c._world = lambda: (snap, None)
    c.gps_state = lambda: {}
    c._pre_intents = pre or (lambda h, s, m: [])
    c._receipt = lambda: "تكرم."
    c._player_takes_over = lambda a: None
    c._remember_action = lambda a, o: None
    c._gate_context = lambda h, a, k, n=(): RG.Context(h[-1]["text"], [], [], k, False, (), [])
    c._model_first = lambda: True
    return c
def say(snap, text, reply, far=None, pre=None):
    REPLY["v"] = reply; GAME.clear(); LOG.clear()
    FAR.update({"status": None, "cars": None, "come_car": None, "come": None}); FAR.update(far or {})
    return chat(snap, pre)._ask_provider([{"role": "user", "text": text}])
J = lambda a, sp="": '{"action":"%s","speech":"%s"}' % (a, sp)
Q = "سول شو في سيارات حواليكي"
NOT_SEEN = "ما قدرت شوف شو في سيارات حواليّ هلأ، جرب كمان شوي."
HIS_CARS = [{"name": "SmallCar", "x": 7236, "y": 8147, "id": 900, "fuel": 30, "fuelMax": 50, "locked": False, "key": True}]
HER_CARS = [{"name": "VanSeats", "x": 7415, "y": 8258, "id": 101, "fuel": 40, "fuelMax": 70, "locked": True, "key": False},
            {"name": "PickUpTruck", "x": 7420, "y": 8262, "id": 102, "fuel": 30, "fuelMax": 60, "locked": False, "key": True}]

# state 1: beside him (her body here, a step from him)
S1 = {"player": {"x": 7410, "y": 8255}, "sol": {"x": 7412, "y": 8255}, "vehicles": HER_CARS}
r = say(dict(S1, solVehicles=HER_CARS), Q, J("cars_near"))
ck("state 1 (beside him): her cars, in words", r.startswith("حواليّ في سيارتين:") and "الفان" in r and "البيك أب" in r and ("sol_far", "cars") not in GAME, (r, GAME))
r = say(S1, Q, J("cars_near"))
ck("state 1, older game side (no solVehicles): the snapshot's cars, she is beside him", r.startswith("حواليّ في سيارتين:"), r)
ck("state 1: no numbers but the count", re.findall(r"\d+", r) == [], r)

# state 2: her body live and loaded, away from him (60 tiles): solVehicles, never his cars
S2 = {"player": {"x": 7350, "y": 8255}, "sol": {"x": 7412, "y": 8255}, "vehicles": HIS_CARS + [dict(HIS_CARS[0], x=7352, id=901)]}
r = say(dict(S2, solVehicles=HER_CARS), Q, J("cars_near"))
ck("state 2 (live, away from him): the cars around HER", r.startswith("حواليّ في سيارتين:") and "الفان" in r and "الصغيرة" not in r, r)
ck("state 2: logged from solVehicles", any("cars near her" in l and "id=101" in l and "id=900" not in l for l in LOG), LOG[-2:])
r = say(dict(S2, solVehicles=[]), Q, J("cars_near"))
ck("state 2, none around her: 'none', even with cars around him", r == "ما في ولا سيارة حواليّ.", r)
r = say(S2, Q, J("cars_near"))
ck("state 2, older game side (no solVehicles): honest 'could not see', never his cars", r == NOT_SEEN, r)

# state 3: her body registered, square not loaded (the 21:35 snapshot): the game's saved rows around her
S3 = {"player": {"x": 7234.6, "y": 8146.8}, "sol": {"x": 7412.2, "y": 8255.8, "away": True, "inVehicle": False}, "vehicles": HIS_CARS}
LIST = "cars:2/own|5,Base.VanSeats,4,40.0,locked,0;6,Base.PickUpTruck,9,30.0,ok,0"
r = say(S3, Q, J("cars_near"), {"status": {"ok": True, "reason": "awake:209"}, "cars": {"ok": True, "reason": LIST}})
print("   state 3:", r)
ck("state 3 (away, the 21:35 bug): answered from the game's list around her", ("sol_far", "cars") in GAME and r.startswith("حواليّ في سيارتين:") and "الفان" in r and "البيك أب" in r, (r, GAME))
ck("state 3: never his cars", "الصغيرة" not in r, r)
ck("state 3, far_car off (/own): no offer to bring one of them", "تعالي بالسيارة" not in r, r)
r = say(S3, Q, J("cars_near"), {"status": {"ok": True, "reason": "awake:209"}, "cars": {"ok": True, "reason": LIST.replace("/own", "")}})
ck("state 3, far_car on: the offer stays (as s77)", "تعالي بالسيارة" in r, r)
n = []
def scanning_then(d, action, option=None, wait=3.0):
    GAME.append((action, option))
    if option == "status": return {"ok": True, "reason": "far:209"}
    if option == "cars":
        n.append(1); return {"ok": False, "reason": "scanning"} if len(n) < 3 else {"ok": True, "reason": LIST}
    return {"ok": False, "reason": "here"}
CS.run_action = scanning_then
r = say(S3, Q, J("cars_near"))
ck("state 3: 'scanning' is asked again until the list is in", len(n) == 3 and r.startswith("حواليّ في سيارتين:"), (len(n), r))
CS.run_action = fake_run_action
r = say(S3, Q, J("cars_near"), {"status": {"ok": True, "reason": "awake:209"}, "cars": {"ok": False, "reason": "no_java"}})
ck("state 3, the game cannot read: honest, never his cars", r == NOT_SEEN, r)
r = say(S3, Q, J("cars_near"), {"status": {"ok": True, "reason": "awake:209"}, "cars": {"ok": False, "reason": "unknown_option"}})
ck("state 3, old game side (no s78 Lua): honest, never his cars", r == NOT_SEEN and any("away" in l for l in LOG), (r, LOG[-2:]))
ck("no snapshot at all: honest", say(None, Q, J("cars_near")) == NOT_SEEN)

# ---------------------------------------------------------------- come_car: the routed order reaches the far trip by car
def pre_far(h, snap, mem):
    done = []
    chat_obj = CUR["c"]
    chat_obj._far_order(h[-1]["text"], snap, done, h[-1].get("said") or h[-1]["text"])
    return done
CUR = {}
def say_come(text, reply, far):
    REPLY["v"] = reply; GAME.clear(); LOG.clear()
    FAR.update({"status": None, "cars": None, "come_car": None, "come": None}); FAR.update(far)
    c = chat(S3); c._pre_intents = pre_far; CUR["c"] = c
    CS.FAR_WAKE = True
    return c._ask_provider([{"role": "user", "text": text}])
for t in ("سول هاتي السيارة وتعي لعندي", "تعالي لعندي بالسيارة", "تعالي بالسيارة"):
    r = say_come(t, J("come_car"), {"status": {"ok": True, "reason": "awake:209"}, "come_car": {"ok": True, "reason": "waiting:180"}})
    ck("come_car '%s', away: the trip by car" % t, ("sol_far", "come_car") in GAME and r and "بالسيارة" in r, (r, GAME))
r = say_come("جيبيلي حالك", J("come_car"), {"status": {"ok": True, "reason": "awake:209"}, "come_car": {"ok": True, "reason": "waiting:180"}})
ck("come_car chosen for words with no car word: still by car first", ("sol_far", "come_car") in GAME, GAME)
r = say_come("سول هاتي السيارة وتعي لعندي", J("come_car"), {"status": {"ok": True, "reason": "awake:209"}, "come_car": {"ok": False, "reason": "no_car"},
                                                          "car_where": {"ok": False, "reason": "no_car_near"}, "come": {"ok": True, "reason": "waiting:120"}})
ck("come_car, no car to bring: she comes on foot and says so", ("sol_far", "come") in GAME and r and "مشي" in r, (r, GAME))
r = say_come("تعالي مشي", J("come_foot"), {"status": {"ok": True, "reason": "awake:209"}, "come": {"ok": True, "reason": "waiting:120"}})
ck("come_foot unchanged: on foot", ("sol_far", "come") in GAME and ("sol_far", "come_car") not in GAME, GAME)

# ---------------------------------------------------------------- the line gate: meta words, codes, her own name
ctx = lambda u="سول تعالي لعندي": RG.Context(u, [], [], "", False, (), [])
for line, why in (("سول هنصحك على بقية اللاعب", "meta_line"), ("رح ساعد اللاعب", "meta_line"), ("I am an NPC", "meta_line"), ("هاد من المود", "meta_line"),
                  ("الـ switch مطفي", "meta_line"), ("ما بقدر، Lua مش جاهزة", "meta_line"), ("السيارة Base.SmallCar جاهزة", "code_line"),
                  ("شغلت far_car", "code_line"), ("سول جاية", "names_herself")):
    c = ctx(); s, w = RG.check_speech({"speech": line}, c, False)
    ck("gate: '%s' -> the ask-again line (%s)" % (line, why), s == RG.ASK_AGAIN and w == why and c.stripped, (s, w))
s, w = RG.check_speech({"speech": "رح ساعد اللاعب"}, ctx(), True)
ck("gate: after an action ran: a plain ack, not a question", s in RG.SAFE_NOTHING and w == "meta_line", (s, w))
for ok_line in ("أهلين، كيفك؟", "أنا سول، رفيقتك.", "ما بحب التلاعب بالكلام.", "إيه فايقة، قلي شو بدك."):
    s, w = RG.check_speech({"speech": ok_line}, RG.Context("مرحبا", [], [], "", False, (), []), False)
    ck("gate: ordinary speech stands: " + ok_line, w is None and s == ok_line, (s, w))
s, w = RG.check_speech({"speech": "البيت عند 7411,8258، والسيارة جنبي"}, RG.Context("وين البيت", [], [], "7411,8258", False, (), []), False)
ck("gate: coordinates still go (s77)", "7411" not in s, s)
r = say(S3, "سول تعالي لعندي", J("none", "سول هنصحك على بقية اللاعب"))
ck("21:37:44 replay: the line never reaches the chat", r == RG.ASK_AGAIN, r)
ck("21:37:44 replay: logged with why", any("gate=meta_line" in l for l in LOG), LOG[-2:])
ck("clean_reply keeps the ask-again line", CS.clean_reply(RG.ASK_AGAIN) == RG.ASK_AGAIN, CS.clean_reply(RG.ASK_AGAIN))

shutil.rmtree(TMP, ignore_errors=True)
print("SUMMARY " + ("ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL)))
sys.exit(1 if FAIL else 0)

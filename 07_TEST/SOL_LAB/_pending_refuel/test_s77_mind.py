"""s77: cars_near (the cars around HER, far or here) and no coordinates in chat. Fake model, real Mind code, on temporary copies.
Run: set PYTHONIOENCODING=utf-8 & python test_s77_mind.py [sol_mind dir]   (default: 05_TOOLS/sol_mind, read only; nothing live is touched)
Offline PASS is not Runtime PASS."""
import glob, hashlib, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind"))
LAB_CL = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, script)] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
def digest(d, names): return {n: hashlib.md5(open(os.path.join(d, n), "rb").read()).hexdigest() for n in names}

# ---------------------------------------------------------------- 1. the Mind installer on a copy
TMP = tempfile.mkdtemp(prefix="sol_s77_")
MIND = os.path.join(TMP, "sol_mind")
os.makedirs(MIND)
for f in glob.glob(os.path.join(SRC, "*")):
    if os.path.isfile(f) and not f.endswith((".log", ".pem")): shutil.copy(f, MIND)
FILES = ["chat_service.py", "model_router.py", "reply_gate.py", "sol_templates.py"]
before = digest(MIND, FILES)
r1 = run("apply_s77_mind.py", MIND); after1 = digest(MIND, FILES)
r2 = run("apply_s77_mind.py", MIND); after2 = digest(MIND, FILES)
ck("installer: applies", r1.returncode == 0 and "s77_mind applied" in r1.stdout, r1.stderr[-400:])
ck("installer: changes the four files", all(before[n] != after1[n] for n in FILES), [n for n in FILES if before[n] == after1[n]])
ck("installer: idempotent (second run changes nothing)", r2.returncode == 0 and after1 == after2, r2.stderr[-400:])
ck("installer: the live files are untouched", digest(SRC, FILES) == before)
for script, args in (("apply_s71_mind.py", [MIND]), ("apply_s72_far_arrival.py", ["-", MIND]), ("apply_s74_secret_loadout.py", ["-", MIND])):
    if not os.path.exists(os.path.join(HERE, script)): continue
    q = run(script, *args)
    ck("installer: re-running %s after s77 changes nothing" % script, q.returncode == 0 and digest(MIND, FILES) == after1, (q.returncode, q.stderr[-300:]))
for n in FILES:
    t = open(os.path.join(MIND, n), "rb").read()
    ck("installer: line endings kept in " + n, (b"\r\n" in open(os.path.join(SRC, n), "rb").read()) == (b"\r\n" in t))

sys.path.insert(0, MIND)
import chat_service as CS, model_router as MR, reply_gate as RG, providers as P, settings_service as SS, world_knowledge as W, sol_templates as STPL
ck("the patched copy is what got imported", os.path.dirname(os.path.abspath(CS.__file__)) == MIND, CS.__file__)

# ---------------------------------------------------------------- 2. the card: one action, its own examples
PHRASES = ["شوفي سيارات حواليكي", "شو في سيارات حواليكي", "في سيارة قريبة؟"]
ck("card: cars_near is one Mind command", "cars_near" in MR.COMMANDS and list(MR.COMMANDS).count("cars_near") == 1)
ex = dict(MR.EXAMPLES)
ck("card: the asked phrases are cars_near examples", all(ex.get(p) == "cars_near" for p in PHRASES), {p: ex.get(p) for p in PHRASES})
ck("card: a couple of natural variants too", sum(1 for _p, a in MR.EXAMPLES if a == "cars_near") >= 5)
ck("card: survey keeps its own examples", ex.get("عنا شو بالمكان") == "survey" and MR.EXTRA_EXAMPLE.get("survey") == "فحصي المكان")
ck("card: survey no longer offers cars", "سيارات" not in MR.COMMANDS["survey"][0], MR.COMMANDS["survey"][0])
AROUND = lambda p: "سيار" in p and re.search("حوال|حول|قريب|جنبك", p)
ck("card: no 'cars around' phrase maps to anything else", all(a == "cars_near" for p, a in MR.EXAMPLES if AROUND(p)), [e for e in MR.EXAMPLES if AROUND(e[0])])
sheet = MR.sheet([], "x")
ck("card: the sheet lists cars_near with an example", re.search(r'^cars_near: .*(?:مثال: )?"شوفي سيارات حواليكي"', sheet, re.M) is not None)
ck("card: the sheet tells the model no coordinates", "إحداثيات" in sheet)

# ---------------------------------------------------------------- the chat, with a fake model and a fake game
REPLY, CALLS, GAME, LOG = {"v": ""}, [], [], []
def fake_chat(pid, key, model, msgs, system="", custom_base="", max_tokens=0, timeout=0):
    CALLS.append(msgs[-1]["content"]); return REPLY["v"]
P.chat = fake_chat
SS.load_config = lambda: {"source": "local", "provider": "custom", "model": "test", "base": ""}
W.situation_text = lambda s, m: "world"
CS.load_actions = lambda d: []
FAR = {"status": None, "cars": None}
def fake_run_action(d, action, option=None, wait=3.0):
    GAME.append((action, option))
    if action == "sol_far" and option == "status": return FAR["status"] or {"ok": False, "reason": "here"}
    if action == "sol_far" and option == "cars": return FAR["cars"] or {"ok": False, "reason": "here"}
    return {"ok": True}
CS.run_action = fake_run_action
CS.resolve_and_run = lambda d, a, o, m, s: (GAME.append((a, o)), {"ok": True})[1]
def chat(snap):
    c = CS.Chat.__new__(CS.Chat)
    c.dir, c.log, c._forced = TMP, LOG.append, None
    c._world = lambda: (snap, None)
    c.gps_state = lambda: {}
    c._pre_intents = lambda h, s, m: []
    c._receipt = lambda: "تكرم."
    c._player_takes_over = lambda a: None
    c._remember_action = lambda a, o: None
    c._gate_context = lambda h, a, k, n=(): RG.Context(h[-1]["text"], [], [], k, False, (), [])
    c._model_first = lambda: True
    return c
def say(snap, text, model_reply):
    REPLY["v"] = model_reply; CALLS.clear(); GAME.clear(); LOG.clear(); FAR.update(status=None, cars=None) if model_reply is None else None
    return chat(snap)._ask_provider([{"role": "user", "text": text}])
J = lambda a, sp="": '{"action":"%s","speech":"%s"}' % (a, sp)
NUMS = lambda s: re.findall(r"\d+", s or "")

# a live snapshot: Sol at 7411,8258, him far from her (the distance is hers), five cars in the window
SNAP = {"player": {"x": 7300, "y": 8100}, "sol": {"x": 7411.4, "y": 8258.2},
        "solHome": {"x": 7411, "y": 8258}, "solParking": {"x": 7413, "y": 8264}, "solFarm": {"zones": [{"n": 59, "alive": 24, "empty": 34}]},
        "vehicles": [
            {"name": "SmallCar", "x": 7413, "y": 8259, "id": 101, "fuel": 30.2, "fuelMax": 50, "locked": False, "key": True},
            {"name": "VanSeats", "x": 7425, "y": 8262, "id": 102, "fuel": 40.0, "fuelMax": 70, "locked": True, "key": False},
            {"name": "PickUpTruck", "x": 7450, "y": 8250, "id": 103, "fuel": 0.0, "fuelMax": 60, "locked": False, "key": True},
            {"name": "ModernCar", "x": 7415, "y": 8240, "id": 104, "fuel": 5.0, "fuelMax": 50, "locked": False, "key": True},
            {"name": "SportsCar", "x": 7800, "y": 8800, "id": 105, "fuel": 30.0, "fuelMax": 50, "locked": False, "key": True}]}

# ---------------------------------------------------------------- 3. routing: each phrase, through the card, to the near answer
for t in PHRASES + ["شوفي سيارات حوليكي"]:
    r = say(SNAP, t, J("cars_near"))
    ck("route: '%s' -> cars_near -> the cars around her" % t, CALLS and r.startswith("حواليّ في 4 سيارات:"), r)
ck("route: here, no far scan was asked of the game", ("sol_far", "cars") not in GAME and ("sol_far", "status") not in GAME, GAME)
ck("route: the numbers went to the log", any("cars near her" in l and "id=101" in l and "fuel=30.2/50" in l for l in LOG), LOG[-3:])

# ---------------------------------------------------------------- 4. the near answer, word by word
line = CS.near_cars_line(SNAP)
print("   near:", line)
ck("near: names in Arabic", all(w in line for w in ("السيارة الصغيرة", "الفان", "البيك أب", "السيارة الحديثة")), line)
ck("near: nearest first, 'next to me'", line.split(":", 1)[1].strip().startswith("السيارة الصغيرة جنبي، جاهزة."), line)
ck("near: locked / no key", "الفان قريبة، مسكّرة وما معي مفتاحها." in line, line)
ck("near: no fuel", "البيك أب بآخر الشارع، ما فيها بنزين." in line, line)
ck("near: low fuel said in words", "السيارة الحديثة قريبة، جاهزة، بس بنزينها قليل." in line, line)
ck("near: a car beyond her street is left out", "الرياضية" not in line, line)
ck("near: no number but the count (no tiles, litres, coordinates, ids)", NUMS(line) == ["4"], NUMS(line))
old = {"sol": {"x": 10, "y": 10}, "vehicles": [{"name": "Base.CarNormal", "x": 12, "y": 10, "fuel": 20, "fuelMax": 50}, {"name": "TrailerCover", "x": 30, "y": 10}]}
l2 = CS.near_cars_line(old)
ck("near, snapshot without lock/key (no Lua part): never 'ready'", "جاهزة" not in l2 and "السيارة العادية جنبي، فيها بنزين، بس ما جرّبتها." in l2, l2)
ck("near: a trailer is a trailer", "المقطورة قريبة، مقطورة." in l2, l2)
ck("near: an unknown type is 'a car', no English id", "سيارة " in CS.near_cars_line({"sol": {"x": 0, "y": 0}, "vehicles": [{"name": "KI5Whatever", "x": 1, "y": 1}]}) and "KI5" not in CS.near_cars_line({"sol": {"x": 0, "y": 0}, "vehicles": [{"name": "KI5Whatever", "x": 1, "y": 1}]}))
ck("near: none around her", CS.near_cars_line({"sol": {"x": 0, "y": 0}, "vehicles": []}) == "ما في ولا سيارة حواليّ.")
r = say({"sol": {"x": 0, "y": 0}, "vehicles": []}, "في سيارة قريبة؟", J("cars_near")); ck("near: none, through the chat", r == "ما في ولا سيارة حواليّ.", r)
ck("near: one car, two cars", CS.cars_head(1) == "حواليّ في سيارة وحدة:" and CS.cars_head(2) == "حواليّ في سيارتين:")

# ---------------------------------------------------------------- 5. the far answer: the existing far_car scan
FAR_SNAP = {"player": {"x": 1000, "y": 1000}, "sol": None, "vehicles": [{"name": "SmallCar", "x": 1001, "y": 1000, "fuel": 30, "fuelMax": 50}]}
def far_say(text, cars):
    REPLY["v"] = J("cars_near"); CALLS.clear(); GAME.clear(); LOG.clear()
    FAR.update(status={"ok": True, "reason": "far:120"}, cars=cars)
    return chat(FAR_SNAP)._ask_provider([{"role": "user", "text": text}])
r = far_say("شوفي سيارات حواليكي", {"ok": True, "reason": "cars:2|5,Base.SmallCar,4,30.0,ok,1;9,Base.VanSeats,44,0.0,no_fuel,0"})
print("   far:", r)
ck("far: the game's far_car list was asked", ("sol_far", "cars") in GAME, GAME)
ck("far: answered from it, same words as near", r.startswith("حواليّ في سيارتين:") and "السيارة الصغيرة (سيارتي) جنبي، جاهزة." in r and "الفان بآخر الشارع، ما فيها بنزين." in r, r)
ck("far: not the snapshot around him", "فيها بنزين، بس" not in r, r)
ck("far: no numbers but the count", NUMS(r) == [], NUMS(r))
r = far_say("في سيارة قريبة؟", {"ok": False, "reason": "no_java"}); ck("far: cannot read: honest", r == "ما قدرت شوف شو في سيارات حواليّ هلأ، جرب كمان شوي.", r)
r = far_say("في سيارة قريبة؟", {"ok": False, "reason": "unknown_option"})
ck("far, switch off: no answer from the cars around HIM", r == "ما قدرت شوف شو في سيارات حواليّ هلأ، جرب كمان شوي.", r)
ck("far_cars_line: names and distance words", CS.far_cars_line("cars:1|5,Base.CarNormal,30,?,locked,0") == "حواليّ في سيارة وحدة: السيارة العادية بآخر الشارع، مسكّرة.", CS.far_cars_line("cars:1|5,Base.CarNormal,30,?,locked,0"))

# no keyword override: the model said "none" to a car question, the Mind does not override it with a word match
r = far_say("شو في سيارات حواليكي؟", None); REPLY["v"] = J("none", "مو متأكدة")
GAME.clear(); r = chat(FAR_SNAP)._ask_provider([{"role": "user", "text": "شو في سيارات حواليكي؟"}])
ck("no keyword override of the model's 'none'", ("sol_far", "cars") not in GAME, (GAME, r))

# ---------------------------------------------------------------- 6. survey and the model's memory: no coordinates
r = say(SNAP, "فحصي المكان", J("survey"))
print("   survey:", r)
ck("survey: still answers the place", "البيت محدد." in r and "في مكان محدد لصف السيارات." in r and "24" in r, r)
ck("survey: no coordinates", "7411" not in r and "8258" not in r and "7413" not in r and RG.COORD_RX.search(r) is None, r)
ck("survey: no tile count", "59" not in r and "خانة" not in r, r)
mem_text = chat(SNAP)._memory_text(SNAP, type("M", (), {"data": {"home": {"x": 7411, "y": 8258}, "places": []}})())
ck("the model's memory sheet: no coordinates", RG.COORD_RX.search(mem_text) is None and "7411" not in mem_text, mem_text)
src = open(os.path.join(MIND, "chat_service.py"), encoding="utf-8").read()
ck("no Arabic chat template formats x,y any more", re.search(r'"[^"\n]*[؀-ۿ][^"\n]*%d,%d', src) is None)

# ---------------------------------------------------------------- 7. the gate strips coordinates from model speech
ctx = RG.Context("وين البيت", [], [], "home 7411,8258 parking 7413,8264", False, (), [])
s, why = RG.check_speech({"speech": "البيت عند 7411,8258، والسيارة جنبي"}, ctx, False)
ck("gate: the clause with the position goes, even though the numbers were in what she was told", "7411" not in s and "8258" not in s, (s, why))
ck("gate: says why in the log", any(w == "coordinates" for w, _c in ctx.stripped), ctx.stripped)
ctx = RG.Context("مرحبا", [], [], "7411,8258", False, (), [])
s, why = RG.check_speech({"speech": "بيتنا عند ٧٤١١،٨٢٥٨"}, ctx, False)
ck("gate: Arabic digits and comma too", "7411" not in s and "٧٤١١" not in s, s)
s, why = RG.check_speech({"speech": "أهلين، كيفك؟"}, RG.Context("مرحبا", [], [], "", False, (), []), False)
ck("gate: ordinary speech untouched", s == "أهلين، كيفك؟" and why is None, (s, why))
ck("clean_reply: drops a sentence holding a position", CS.clean_reply("البيت محدد عند 7411,8258. مكان صف السيارات عند 7413,8264. عنا منطقة زراعة.") == "عنا منطقة زراعة.", CS.clean_reply("البيت محدد عند 7411,8258. مكان صف السيارات عند 7413,8264. عنا منطقة زراعة."))
ck("clean_reply: x/y form too", "7411" not in CS.clean_reply("أنا عند x 7411 y 8258 هلأ"), CS.clean_reply("أنا عند x 7411 y 8258 هلأ"))
ck("clean_reply: decimals and amounts stay", CS.clean_reply("فيها 12.5 لتر.") == "فيها 12.5 لتر." and CS.clean_reply("عنا 5,000 رصاصة") == "عنا 5,000 رصاصة")
ck("clean_reply: the 20:41 reply cannot reach him", RG.COORD_RX.search(CS.clean_reply("البيت محدد عند 7411,8258. مكان صف السيارات عند 7413,8264.")) is None)

# ---------------------------------------------------------------- 8. the Lua part (snapshot: locked, key), when its files are here
if os.path.exists(os.path.join(LAB_CL, "SolWorldScan.lua")):
    cl = os.path.join(TMP, "client"); os.makedirs(cl)
    shutil.copy(os.path.join(LAB_CL, "SolWorldScan.lua"), cl)
    b = digest(cl, ["SolWorldScan.lua"])
    q1 = run("apply_s77_lua.py", cl); a1 = digest(cl, ["SolWorldScan.lua"])
    q2 = run("apply_s77_lua.py", cl); a2 = digest(cl, ["SolWorldScan.lua"])
    ck("lua installer: applies and is idempotent", q1.returncode == 0 and q2.returncode == 0 and b != a1 and a1 == a2, (q1.stderr[-300:], q2.stderr[-300:]))
    lua_src = open(os.path.join(cl, "SolWorldScan.lua"), encoding="utf-8").read()
    ck("lua: the row gets locked and key", "info.locked, info.key = carUse(v, sol)" in lua_src)
    ck("lua: Kahlua rule, no tonumber(f())", re.search(r"tonumber\(\s*call\(", lua_src[lua_src.find("s77 cars_near"):lua_src.find("-- s77 end")]) is None)
    try:
        sys.path.insert(0, HERE)
        from kahlua_env import lua51
        L = lua51.LuaRuntime()
        ok = L.eval("function(s) local f, e = loadstring(s); return e end")(lua_src)
        ck("lua: the patched file compiles", ok is None, ok)
        helpers = lua_src[lua_src.find("local function call(o, name, ...)"):lua_src.find("local function round(")]
        body = lua_src[lua_src.find("local function carUse(v, sol)"):lua_src.find("-- s77 end")]
        L.execute(helpers + body + """
function CAR(t)
    local door = t.door
    local parts = t.parts or {}
    return { getPartById = function(self, id) if id == "DoorFrontLeft" and door ~= nil then return { getDoor = function() return door end } end return nil end,
             isKeysInIgnition = function() return t.ign == true end, isHotwired = function() return t.hot == true end,
             isHotwiredBroken = function() return t.broken == true end, getKeyId = function() return t.kid end,
             getPartCount = function() return #parts end, getPartByIndex = function(self, i) return parts[i + 1] end }
end
function DOOR(l) return { isLocked = function() return l end } end
function HAS(ids) return { haveThisKeyId = function(self, k) if ids[k] then return {} end return nil end } end
function SOL(ids) return { getInventory = function() return HAS(ids) end } end
function USE(car, sol) local a, b = carUse(car, sol); return tostring(a) .. "," .. tostring(b) end
""")
        U = lambda e: L.eval(e)
        ck("lua: unlocked, key in her things", U('USE(CAR{door = DOOR(false), kid = 7}, SOL{[7] = true})') == "false,true", U('USE(CAR{door = DOOR(false), kid = 7}, SOL{[7] = true})'))
        ck("lua: locked, no key anywhere", U('USE(CAR{door = DOOR(true), kid = 7}, SOL{})') == "true,false")
        ck("lua: key in the ignition", U('USE(CAR{door = DOOR(true), kid = 7, ign = true}, SOL{})') == "true,true")
        ck("lua: hotwired, wires whole / broken", U('USE(CAR{door = DOOR(false), kid = 7, hot = true}, SOL{})') == "false,true" and U('USE(CAR{door = DOOR(false), kid = 7, hot = true, broken = true}, SOL{})') == "false,false")
        ck("lua: key inside the car", U('USE(CAR{door = DOOR(false), kid = 7, parts = { { getItemContainer = function() return HAS{[7] = true} end } }}, SOL{})') == "false,true")
        ck("lua: no door, no her: unknown", U('USE(CAR{kid = 7}, nil)') == "nil,nil")
        ck("lua: no key id at all", U('USE(CAR{door = DOOR(false), kid = -1}, SOL{})') == "false,false")
    except ImportError as e:
        print("SKIP lua runtime checks (lupa missing): %s" % e)
else:
    print("SKIP lua part: lab client not found")

# ---------------------------------------------------------------- 9. existing Mind tests in the sol_mind dir, on the patched copy
own = sorted(glob.glob(os.path.join(SRC, "test_*.py")))
for t in own:
    shutil.copy(t, MIND)
    q = subprocess.run([sys.executable, os.path.basename(t)], cwd=MIND, capture_output=True, text=True, encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    ck("existing Mind test on the patched copy: " + os.path.basename(t), q.returncode == 0 and "FAIL" not in q.stdout, (q.stdout + q.stderr)[-400:])
if not own: print("NOTE no test_*.py in %s: nothing more to run there" % SRC)

shutil.rmtree(TMP, ignore_errors=True)
print("SUMMARY " + ("ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL)))
sys.exit(1 if FAIL else 0)

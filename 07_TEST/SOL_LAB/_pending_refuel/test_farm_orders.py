"""Her farm orders and everything she says about the farm, from the Mind's side, with no model connected at any point."""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind")
import chat_service as CS, farm_talk as FT, sol_templates as TPL
CS.Chat._far_order = lambda self, text, snap, done: False                         # she is in the world in these tests; far away is covered by test_far.py
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)

GAME = {}          # option -> (ok, reason)
RAN = []
def fake_run(lua, action, option=None, wait=3.0):
    RAN.append((action, option))
    ok, reason = GAME.get(option, (True, "ok"))
    return {"ok": ok, "reason": reason}
CS.run_action = fake_run
MODEL = []
class Goals:
    def __init__(self): self.mind = None; self.mind_lock = None
    def cancel(self, reason=""): return False
    def submit(self, g): return {"ok": False}
    def describe(self): return ""
def chat():
    c = CS.Chat.__new__(CS.Chat)
    c.dir, c.log, c.goals, c.pending_card = ".", (lambda x: None), Goals(), None
    return c
class Mem:
    def __init__(self): self.data = {"places": [], "visited": []}; self.saved = 0
    def save(self): self.saved += 1

ORDERS = [
    ("دبري المزرعة بغيابي", ("sol_farm", "keeper")), ("سول دبري المزرعة بغيابي", ("sol_farm", "keeper")), ("يا سول دبري أمر المزرعة بغيابي", ("sol_farm", "keeper")),
    ("اهتمي بالمزرعة بغيابي", ("sol_farm", "keeper")), ("اهتمّي بالمزرعة بغيابي", ("sol_farm", "keeper")), ("إهتمي بالمزرعه بغيابي", ("sol_farm", "keeper")),
    ("اعتني بالمزرعة بغيابي", ("sol_farm", "keeper")), ("اهتمي بالزرع", ("sol_farm", "keeper")),
    ("ضلي بالبيت ارتاحي", ("sol_farm", "home")), ("ضلّي بالبيت وارتاحي", ("sol_farm", "home")), ("سول ضلي بالبيت ارتاحي", ("sol_farm", "home")), ("خليكي بالبيت ارتاحي", ("sol_farm", "home")),
    ("ابقي بالبيت وارتاحي", ("sol_farm", "home")), ("ارتاحي بالبيت", ("sol_farm", "home")), ("ضلي بالبيت", ("sol_farm", "home")),
    ("اسقي", ("sol_farm", "water")), ("إسقي", ("sol_farm", "water")), ("سول اسقي", ("sol_farm", "water")), ("اسقي الزرع", ("sol_farm", "water")), ("اسقي المزرعة", ("sol_farm", "water")),
    ("احصدي", ("sol_farm", "harvest")), ("إحصدي", ("sol_farm", "harvest")), ("سول احصدي", ("sol_farm", "harvest")), ("احصدي الزرع", ("sol_farm", "harvest")),
    ("ازرعي بندورة بهالقطعة", ("sol_farm", "plant:Tomato")), ("إزرعي جزر", ("sol_farm", "plant:Carrots")), ("ازرعي", ("sol_farm", "plant:any")), ("سول ازرعي ذرة", ("sol_farm", "plant:Corn")),
    ("شوفي شو ناقصنا", ("sol_farm", "short")), ("شو ناقصنا", ("sol_farm", "short")), ("سول شوفي شو ناقصنا", ("sol_farm", "short")), ("شوفي شو ناقصنا للزراعة", ("sol_farm", "short")),
    ("سجلي المخازن", ("sol_farm", "storage")), ("جهزي مخازن المزرعة", ("sol_farm", "storage")),
    ("sol_farm_try plow", ("sol_farm_try", "plow")),
]
for text, want in ORDERS:
    got = FT.order(text)
    ck("caught without any model: " + text, got == want, got)
for text in ["كيفك يا سول", "اسقيني مي", "هات المحروقات", "ضلي هون", "ازرع", "شو الأخبار", "خلينا نمشي"]:
    ck("not a farm order: " + text, FT.order(text) is None, FT.order(text))

for text in ["وقفي", "وقفي السيارة", "سوقي", "سوقي عالبيت", "قودي", "اركبي", "انزلي", "زمري", "سول وقفي", "خذيني عالبيت", "وصليني عالبيت", "سوقي عالبيت وضلي بالبيت", "لمي", "لمي اغراضك", "شو بدنا", "شو لازمنا"]:
    ck("a plain or driving order is never a farm order: " + text, FT.order(text) is None, FT.order(text))
ck("the car really stops on a plain stop", any(n == "drive_stop" for n, _ in CS.intents("وقفي")), CS.intents("وقفي"))
for text in ["لمي المحصول", "شو بدنا للزراعة", "وقفي شغل المزرعة"]:
    ck("with a farm word it is a farm order: " + text, FT.order(text) is not None, FT.order(text))
ck("one sentence, both orders", FT.order("دبري المزرعة بغيابي وضلي بالبيت ارتاحي") == ("sol_farm", "both"), FT.order("دبري المزرعة بغيابي وضلي بالبيت ارتاحي"))

# through the Mind's own pre-intents, no provider configured
CS.SS.load_config = lambda: {"source": "none"}
for text, want in [("سول دبري المزرعة بغيابي", "keeper"), ("ضلي بالبيت ارتاحي", "home"), ("اسقي", "water"), ("احصدي", "harvest")]:
    RAN.clear(); GAME.clear(); GAME[want] = (True, "ok")
    c = chat()
    done = c._pre_intents([{"role": "user", "text": text}], {}, None)
    ck("reaches the game with no model: " + want, RAN and RAN[-1] == ("sol_farm", want), RAN)
    ck("she answers, in Levantine, no model: " + want, bool(getattr(c, "_forced", None)) and c._forced in FT.ACK[want], getattr(c, "_forced", None))

# orders and refusals
GAME.clear(); GAME["water"] = (False, "base_missing")
c = chat(); c._pre_intents([{"role": "user", "text": "اسقي"}], {}, None)
ck("no base: says so instead of lying", "قاعدة" in c._forced, c._forced)
GAME.clear(); GAME["plant:unknown:عشبة"] = (True, "single:plant")
ck("unknown crop: she says she does not know it", "ما بعرف" in FT.reply_for("plant:unknown:عشبة", {"ok": True, "reason": "x"}))

c = chat(); RAN.clear(); c._pre_intents([{"role": "user", "text": "ازرعي عشبة غريبة"}], {}, None)
ck("unknown crop: nothing sent to the game", RAN == [] and "ما بعرف" in c._forced, (RAN, c._forced))

# the report: truth per zone, item names as the game shows them
REPORT = {"complete": True, "names": {"Tomato": "Base.Tomato"}, "seedNames": {"Tomato": "Base.TomatoSeed"}, "stock": {"seeds": {"Tomato": 5}, "compost": 2, "fert": 0},
    "zones": [{"id": "a", "alive": 12, "n": 13, "ripe": 3, "thirsty": 4, "dead": 1, "empty": 2, "weeds": 1, "pests": {"mildew": 2, "flies": 0, "aphid": 1, "slugs": 0}, "crops": [{"crop": "Tomato", "ripe": 3}]},
              {"id": "b", "n": 0, "alive": 0}], "shortages": [{"full": "Base.WateredCan", "need": 1, "have": 0}]}
t = FT.report_text(REPORT)
for needle, desc in [("3 جاهز للقطف", "ripe"), ("Tomato", "exact crop name"), ("4 عطشانة", "thirsty"), ("عفن على 2", "mildew by name"), ("من على 1", "aphids"), ("1 ميتة", "dead"), ("2 محروثة", "empty"), ("1 فيها عشب", "weeds"), ("القطعة 2: فاضية", "second zone"), ("Tomato Seeds", "seed name exact"), ("Watering Can", "short item exact name")]:
    ck("report: " + desc, needle in t, t)
ck("report: an unloaded chest is not 'no seed or fertiliser'", "مو متأكدة" in FT.report_text({"zones": [{"id": "a", "n": 0, "alive": 0}], "stock": {"seeds": {}, "unsure": {"farming": True}}}))
ck("report: no zones is not 'all watered'", "ما في منطقة زراعة" in FT.report_text({"zones": []}))
ck("no 15-tile report left", TPL.farm_text({"solFarm": REPORT}, None) == t)

# shortages
s = FT.shortages_text([{"full": "Base.WateredCan", "need": 1, "have": 0}, {"full": "Base.GardeningSprayMilk", "need": 3, "have": 1}, {"seedChoices": ["Base.TomatoSeed"], "need": 2, "have": 0}])
ck("shortage: exact in-game names, amounts", "Watering Can" in s and "Mildew Spray" in s and "بدنا 3" in s and "Tomato Seeds" in s, s)
s = FT.shortages_text([{"full": "Base.WateredCan", "need": 1, "have": 0, "unsure": True}])
ck("shortage: unsure, not a false 'we have none'", "مو متأكدة" in s and "ناقصنا" not in s, s)
s = FT.shortages_text([{"full": "Base.GardenHoe", "alt": ["Base.GardenHoe", "Base.Shovel"], "need": 1, "have": 0}])
ck("shortage: an item not in the world still by its game name", "Garden Hoe" in s and "Spade" in s, s)

# storages in one order
line = FT.storage_line("scan;regs=farming@1,2,crate|food@3,4,fridge;cls=empty:2#apply;zones=1/1;regs=2/2;fail=")
ck("storage order: registered and what is still missing", "سجلت" in line and "خزانة أدوات" in line and "مخزن محصول" in line, line)

# what she says she is doing
for st, needle in [({"status": "doing", "detail": "harvest"}, "بحصد"), ({"status": "needs", "detail": "food"}, "باكل"), ({"status": "waiting", "detail": "no_can"}, "Watering Can"), ({"status": "idle"}, "كلشي"), ({"status": "waiting", "detail": "rain"}, "تشتي")]:
    ck("status: " + str(st), needle in FT.status_line(st), FT.status_line(st))
ck("stop reason: job level", "مصدر مي" in (FT.stop_line({"reason": "blocked", "detail": {"why": "water_source_missing"}}) or ""))
ck("stop reason: paused bed", "قطعة" in (FT.stop_line({"reason": "paused", "detail": {"why": "timeout"}}) or ""))
ck("no talk of crews or groups", not any(w in json.dumps(FT.WHY_AR, ensure_ascii=False) for w in ("طاقم", "فريق", "عمال")))

# status questions only when she is at it
GAME.clear(); GAME["status"] = (True, "status:" + json.dumps({"status": "doing", "detail": "water"}))
c = chat(); RAN.clear(); c._pre_intents([{"role": "user", "text": "شو عم تعملي"}], {"solFarm": {"mode": {"farm": True}}}, None)
ck("asked what she is doing: from the game", RAN == [("sol_farm", "status")] and "بسقي" in c._forced, (RAN, c._forced))
c = chat(); RAN.clear(); c._forced = None; done = c._pre_intents([{"role": "user", "text": "شو عم تعملي"}], {}, None)
ck("not on the farm: left to normal chat", RAN == [] and c._forced is None, (RAN, c._forced))

# any other order from him interrupts
GAME.clear()
c = chat(); RAN.clear(); c._player_takes_over = lambda a: None; c._remember_action = lambda *a: None
snap = {"solFarm": {"mode": {"farm": True}}}
CS.resolve_and_run = lambda lua, aid, opt, mem, s, log=print: (RAN.append((aid, opt)), {"ok": True, "reason": "done"})[1]
c._pre_intents([{"role": "user", "text": "اتبعيني"}], snap, None)
ck("any order interrupts the farm", ("sol_farm", "interrupt") in RAN and RAN.index(("sol_farm", "interrupt")) < RAN.index(("follow", None)), RAN)
c = chat(); RAN.clear(); c._player_takes_over = lambda a: None; c._remember_action = lambda *a: None
c._pre_intents([{"role": "user", "text": "اتبعيني"}], {"solFarm": {"mode": {}}}, None)
ck("nothing running: no extra message to the game", RAN == [("follow", None)], RAN)

# memory, warnings
farm = {"due": [{"zone": "a", "crop": "Tomato", "veg": "Base.Tomato", "hours": 48}], "sown": [{"crop": "Tomato", "x": 1, "y": 1, "day": 10}], "ripe": 3, "thirsty": 5, "raining": False,
        "season": [{"crop": "Corn", "kind": "ending", "seed": "Base.CornSeed"}, {"crop": "Carrots", "kind": "soon", "seed": "Base.CarrotSeed"}],
        "zones": [{"crops": [{"crop": "Tomato", "ripe": 3}]}], "stop": {"seq": 4, "reason": "paused", "detail": {"why": "timeout"}}}
m = Mem(); c = chat(); said = []
class Mind:
    def say(self, line): said.append(line)
c.goals.mind = Mind()
ck("watch: warns", c._farm_watch({"solFarm": farm}, m) is True and any("Tomato" in s for s in said), said)
ck("watch: what she planted kept", m.data.get("farm", {}).get("sown") == farm["sown"])
ck("watch: stored and saved", m.saved >= 1)
ck("due: she can say when it is ready", "Tomato" in FT.FarmMemory(m).due_text() and "يوم" in FT.FarmMemory(m).due_text(), FT.FarmMemory(m).due_text())
warn = FT.FarmMemory(m).warnings({"due": [{"crop": "Tomato", "veg": "Base.Tomato"}], "thirsty": 5, "zones": [{"crops": [{"crop": "Tomato", "ripe": 2}]}], "season": [{"crop": "Corn", "kind": "ending", "seed": "Base.CornSeed"}]}, now=time.time())
ck("warnings: rate-limited", warn == [], warn)
warn = FT.FarmMemory(m).warnings({"due": [{"crop": "Tomato", "veg": "Base.Tomato"}], "thirsty": 5, "zones": [{"crops": [{"crop": "Tomato", "ripe": 2}]}], "season": [{"crop": "Corn", "kind": "ending", "seed": "Base.CornSeed"}]}, now=time.time() + 2000)
ck("warnings: ready, thirsty, season, again after the cooldown", len(warn) == 3 and any("Corn" in w and "موسم" in w for w in warn), warn)
wc = FT.FarmMemory(Mem()).warnings({"thirsty": 5, "raining": True, "zones": []}, now=1000)
ck("warnings: not thirsty alarm while it rains", wc == [], wc)
ck("stop reason said once", (c._farm_watch({"solFarm": farm}, m), len([s for s in said if "قطعة" in s]))[1] == 1, said)

# death wipes the Mind's side too
m = Mem(); m.data["farm"] = {"sown": [{"crop": "Tomato"}], "due": {"a|Tomato": {}}, "warned": {"x": 1}}; m.data["deaths"] = 0
c = chat(); CS.MA.LOST_MEMORY_LINES = ["x"]
c._life_watch({"solLife": {"deaths": 1}}, m)
ck("death: what she planted is forgotten by the Mind", m.data.get("farm") == {}, m.data.get("farm"))

# what she says must be true by then, and never a raw code
ck("nothing thirsty: says so, not 'on my way'", FT.reply_for("water", {"ok": True, "reason": "single:water:none"}) == FT.NOTHING_ON["water"], FT.reply_for("water", {"ok": True, "reason": "single:water:none"}))
ck("something missing: says what", "Watering Can" in FT.reply_for("water", {"ok": True, "reason": "single:water:none:no_can"}), FT.reply_for("water", {"ok": True, "reason": "single:water:none:no_can"}))
ck("a single order that ended says so", FT.stop_line({"reason": "done", "detail": {"kind": "water"}}) == "خلصت السقاية.", FT.stop_line({"reason": "done", "detail": {"kind": "water"}}))
ck("arrived home is said", FT.stop_line({"reason": "home_arrived", "detail": {}}) == "وصلت عالبيت.")
home_line = FT.reply_for("home", {"ok": True, "reason": "mode:home:home:going"})
ck("home: on the way, not already there", home_line not in FT.ACK["home"] and "عالبيت" in home_line, home_line)
ck("proven: a call that was not verified is not 'worked'", "زبط معي" not in FT.proven_line('proven:{"water": {"fallback": "called"}}') and "زبط معي" in FT.proven_line('proven:{"water": {"fallback": "applied"}}'))
for code in ("already_acting", "no_fallback:weed", "lf_unavailable", "store_unavailable", "unknown_farm_order", "no_home", "base_missing", "some_new_code"):
    ck("never a raw code: " + code, code not in FT.why_ar(code) and not any("a" <= c <= "z" for c in FT.why_ar(code)), FT.why_ar(code))

print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)

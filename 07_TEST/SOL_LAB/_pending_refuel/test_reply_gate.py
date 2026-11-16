"""The gate between a model and the game: the checks alone, then the real chat path with the model and the game replaced."""
import json, os, sys, tempfile, time
M = r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind"
sys.path.insert(0, M)
import reply_gate as RG, chat_service as CS, intent_engine as IE, providers as P, settings_service as SS
CS.Chat._model_first = lambda self: False      # this file tests the old path; test_model_first.py has the new one
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)

ALLOWED = {"sol_engine", "sol_horn", "sol_headlights"}
def ctx(text="سول بدي شي", known="", car=True, recent=()): return RG.Context(text, ALLOWED, IE.SUPPORTED, known, car, recent)
J = lambda **k: json.dumps({"speech": k.get("speech", "تكرم"), "action": k.get("action"), "option": k.get("option"), "facts": []}, ensure_ascii=False)

p = RG.parse(J(speech="ماشي", action="sol_horn", option="once")); ck("JSON reply read", p["speech"] == "ماشي" and p["action"] == "sol_horn" and p["option"] == "once", p)
p = RG.parse("ماشي [فعل: sol_engine | on]"); ck("old tags read as a proposal", p["action"] == "sol_engine" and p["option"] == "on" and "[" not in p["speech"], p)
p = RG.parse("تكرم يا جمال"); ck("plain words", p["speech"] == "تكرم يا جمال" and p["action"] is None, p)
p = RG.parse('{"broken'); ck("broken JSON is not executed", p["action"] is None, p)
p = RG.parse("[هدف: refuel_errand | car | car] ماشي"); ck("goal tag read", p["goal"] == "refuel_errand", p)

ck("hallucinated action refused", RG.check_action({"action": "sol_launch_missiles", "goal": None}, ctx())[0] is False)
ck("unknown goal refused", RG.check_action({"goal": "take_over", "action": None}, ctx())[0] is False)
ck("known action allowed", RG.check_action({"action": "sol_horn", "goal": None, "option": "once"}, ctx())[0] is True)
ck("a question never runs anything", RG.check_action({"action": "sol_horn", "goal": None}, ctx("وين اقرب كازية"))[0] is False)
ck("question mark too", RG.check_action({"action": "sol_horn", "goal": None}, ctx("فيكي تزمري؟"))[0] is False)
ck("car action outside a car refused", RG.check_action({"action": "sol_engine", "goal": None, "option": "on"}, ctx(car=False))[1] == "not_in_a_car")
now = 1000.0
ck("the engine she just turned off stays off", RG.check_action({"action": "sol_engine", "goal": None, "option": "on"}, ctx(recent=[(now - 9, "sol_engine", "off")]), now)[1] == "contradicts_what_was_just_done")
ck("after a minute it may change", RG.check_action({"action": "sol_engine", "goal": None, "option": "on"}, ctx(recent=[(now - 90, "sol_engine", "off")]), now)[0] is True)

def speech(s, known="", ran=False, text="سول احكيلي"): return RG.check_speech({"speech": s}, ctx(text, known), ran)
ck("a normal line stands", speech("ماشي، أنا معك.")[1] is None)
ck("made-up station refused", speech("أقرب كازية عند مفرق الجسر.")[1] == "world_claim_not_known")
ck("known place stands", speech("الكازية عند مفرق الجسر.", known="مفرق الجسر فيه كازية")[1] is None)
ck("made-up number refused", speech("بعيدة 250 خطوة.")[1].startswith("number_not_known"))
ck("known number stands", speech("معي 12 طلقة.", known="ammo 12")[1] is None)
ck("Arabic digits are read as digits", speech("معي ١٢ طلقة.", known="ammo 12")[1] is None)
ck("claims without doing refused", speech("طفيت الضو.")[1] == "claims_an_action")
ck("claims when it ran stand", speech("طفيت الضو.", ran=True)[1] is None)
ck("meta words refused", speech("قبلت اللعبة الأمر.")[1] == "meta_words")
ck("model talk refused", speech("أنا نموذج لغوي.")[1] == "meta_words")
ck("brackets refused", speech("(قبلت) ماشي")[1] == "not_speech")
ck("mojibake refused", speech("أقرب".encode("utf-8").decode("latin-1"))[1] == "mojibake")
ck("a raw JSON dump refused", speech('{"speech": "x"}')[1] == "not_speech")
ck("empty gets a line", speech("")[0] != "")

for line, why in [("دوري، ما بتحتاجين ماء", "speaks_to_herself"), ("تقدر تسرع بس ما بتحتاجين ماء", "speaks_to_herself"), ("انتي تعبانة", "speaks_to_herself")]: ck("talks to Sol, not as Sol: " + line, speech(line)[1] == why, speech(line))
for line in ["ماشي، أنا معك.", "إنت بدك شي؟", "بتقدر تستناني شوي؟", "بشوفك هلأ."]: ck("talks to him: " + line, speech(line)[1] is None, speech(line))
t = speech("مزرعة بجوارها حديقة زراعية")[1]; ck("a farm nobody told her about", t == "world_claim_not_known", t)
for q in ["سول في شي مزرعة قريبة علينا بالمنطقة", "تذكري مرينا شي من جنب مزرعة", "شفنا كازية؟"]: ck("asking, though no question word: " + q, RG.is_question(q))
for q in ["وين اقرب محطة بنزين", "كم الساعة الان", "شو عندنا", "سول وين البيت", "فيكي تزمري؟"]: ck("question: " + q, RG.is_question(q))
for o in ["زمري مرة وحدة", "طفي الضو", "سول طفي محرك السيارة", "ابحثي"]: ck("order: " + o, not RG.is_question(o))
ck("station question is about the world", RG.about_the_world("وين اقرب محطة بنزين"))

# ---------------------------------------------------------------- names the model misspells
import memory_answers as MA
NAMES = [("Broadway St", ()), ("Elm St", ()), ("Main St", ())] + MA.known_names({}, None, [(1, 1, 9, "gas2go"), (2, 2, 9, "fossoil")])
def named(s, known=""):
    c = RG.Context("سول احكيلي", ALLOWED, IE.SUPPORTED, known, True, (), NAMES)
    r = RG.check_speech({"speech": s}, c, False)
    return r[0], r[1], c.fixes
for line, right, wrong in [("الشارع المقرب هو برايدوو", "Broadway St", "برايدوو"), ("هاد شارع برودواي", "Broadway St", "برودواي"), ("شارع برادوي قريب", "Broadway St", "برادوي"), ("شارع Broadwy", "Broadway St", "Broadwy"),
                           ("الشارع broadway", "Broadway St", "broadway St St"), ("شارع ايلم", "Elm St", "ايلم"), ("شارع ماين", "Main St", "ماين"),
                           ("الكازية Gas2Go قريبة", "غاز تو غو", "Gas2Go"), ("كازية جاس تو جو", "غاز تو غو", "جاس"), ("كازية قاز تو قو", "غاز تو غو", "قاز"), ("هاي محطة Gas to Go", "غاز تو غو", "Gas to Go"),
                           ("محطة فوسويل", "فوس أويل", "فوسويل"), ("كازية Fossoil", "فوس أويل", "Fossoil"), ("كازية فوس اويل", "فوس أويل", "فوس اويل")]:
    t, why, fx = named(line); ck("put right: " + line, why is None and right in t and wrong not in t and fx, (t, why, fx))
t, why, fx = named("شارع Broadway St"); ck("already right: kept, nothing to fix", why is None and "Broadway St" in t and not fx, (t, why, fx))
t, why, fx = named("كازية غاز تو غو قريبة"); ck("the Arabic name itself stands", why is None and t == "كازية غاز تو غو قريبة" and not fx, (t, why, fx))
for line in ["الشارع المقرب هو الملك فيصل", "شارع بغداد", "شارع بردى", "كازية شل", "كازية Shell", "شارع Maple Drive", "كازية فيصل", "كازية Shell بشارع Broadway St", "شارع بغداد قرب كازية غاز تو غو"]:
    t, why, fx = named(line); ck("invented refused: " + line, why and t in RG.SAFE_UNKNOWN, (t, why, fx))
ck("an invented name says which", named("كازية Shell بشارع Broadway St")[1] == "invented_name:Shell", named("كازية Shell بشارع Broadway St"))
ck("two streets equally close: she won't guess", RG.match_name("Mainn", [("Main St", ()), ("Mann St", ())]) is None)
ck("a common word near a marker is not a street", named("الكازية قريبة من هون")[2] == [], named("الكازية قريبة من هون"))
ck("no world word: left alone", named("ماشي يا جمال")[0] == "ماشي يا جمال")
LV = NAMES + [("لويزفيل", ("Louisville",)), ("Sunstar Motel", ())]
def namedv(s):
    c = RG.Context("سول احكيلي", ALLOWED, IE.SUPPORTED, "", True, (), LV); r = RG.check_speech({"speech": s}, c, False); return r[0], r[1], c.fixes
for line, right, wrong in [("مدينة لويسفيل قريبة", "لويزفيل", "لويسفيل"), ("في Sunstar Motl قريب", "Sunstar Motel", "Motl"), ("لويسفيل قريبة من هون", "لويزفيل", "لويسفيل")]:
    t, why, fx = namedv(line); ck("names are found anywhere: " + line, why is None and right in t and wrong not in t, (t, why, fx))
for w in ["مستودعات", "سيارتنا", "كتابتها"]: ck("a long ordinary word is left alone: " + w, namedv("ماشي " + w + ".")[0] == "ماشي " + w + ".", namedv("ماشي " + w + "."))
ck("broadway keys alike", RG.name_key("Broadway") == RG.name_key("برايدوو") == RG.name_key("برودواي"))
S = {"player": {"x": 1000, "y": 1000}, "knownStreets": ["Elm St"], "currentStreet": "Broadway St"}
f = MA.facts(S, None, [(1030, 1000, 50, "gas2go"), (5000, 5000, 50, "fossoil")]); ck("facts: street and nearest station with distance", "Broadway St" in f and "غاز تو غو حوالي 30 متر بالشرق" in f, f)
n = MA.known_names(S, None, [(1, 1, 5, "gas2go")]); ck("names: what she knows and no more", [x[0] for x in n] == ["Broadway St", "Elm St", "غاز تو غو"], n)
ck("names: an unnamed brand adds nothing", MA.known_names({}, None, [(1, 1, 5, "other")]) == [])

# ---------------------------------------------------------------- the real chat path
d = tempfile.mkdtemp(prefix="sol_gate_")
class Goals:
    def __init__(self): self.sub = []
    def submit(self, g): self.sub.append(g); return {"ok": True, "goalId": "g1"}
    def wait_answer(self, gid, s=3.0): return "أقرب وحدة بعرفها كازية، حوالي 30 متر. علّمتلك ياها عالـ GPS."
    def describe(self): return "none"
    def cancel(self, reason=""): return False
    def perception(self): return {"sol": {"currentVehicle": {"id": 1}}, "player": {}}
RAN, CALLS, REPLY = [], [], {"v": None}
SYSTEMS, ASKED = [], []
def fake_run_action(lua, aid, option=None, wait=3.0):
    ASKED.append(option)
    if option == "street": return {"ok": True, "reason": "street:Broadway St"}
    if option == "list": return {"ok": True, "reason": "list:1010,1010,90,gas2go"}
    return {"ok": False, "reason": "x"}
CS.run_action = fake_run_action
CS.resolve_and_run = lambda lua, aid, opt, mem, snap, log=print: (RAN.append((aid, opt)), {"ok": True, "reason": "done"})[1]
CS.load_actions = lambda _d: [{"id": "sol_horn", "label": "x", "kind": "sol"}]
CS.actions_text = lambda a: "x"
SS.load_config = lambda: {"source": "api", "provider": "custom", "model": "m"}
CS.S.get = lambda k: ""
def fake_model(*a, **k): CALLS.append(k.get("tools") or a[4]); SYSTEMS.append(k.get("system")); return REPLY["v"]
P.chat_with_tools = fake_model
CS.W.load_snapshot = lambda _d: {"world": {"name": "w"}}
CS.W.Memory = lambda w: None
CS.W.situation_text = lambda s, m: "situation"
def chat():
    c = CS.Chat.__new__(CS.Chat)
    c.dir, c.log, c.goals, c.pending_card, c._forced, c._turn_action_results = d, (lambda x: None), Goals(), None, None, []
    c.system_prompt = lambda s, m: "world"
    c.gps_state = lambda: {}
    return c
def say(c, text): return c._ask_provider([{"role": "user", "text": text}])
def reset(reply): RAN.clear(); CALLS.clear(); REPLY["v"] = reply

reset(J(speech="ماشي", action="sol_engine", option="on")); c = chat(); r = say(c, "سول طفي محرك السيارة")
ck("real order: the model is never asked", len(CALLS) == 0, CALLS)
ck("real order: only what he asked", RAN == [("sol_engine", "off")], RAN)
ck("real order: a natural receipt", r in ("تكرم.", "ماشي.", "حاضر."), r)
reset(J(speech="ماشي", action="sol_engine", option="on")); c = chat(); say(c, "زمري مرة وحدة"); ck("horn is the horn, no model", RAN == [("sol_horn", "once")] and not CALLS, (RAN, CALLS))
reset(J()); c = chat(); r = say(c, "طفي الضو"); ck("lights are the lights, no model", RAN == [("sol_headlights", "off")] and not CALLS, (RAN, CALLS))
reset(J()); c = chat(); r = say(c, "وين اقرب محطة بنزين"); ck("station question: the Mind answers, in the chat", "GPS" in r and not CALLS, (r, CALLS)); ck("question starts no drive", c.goals.sub[0]["intent"] == "station_query", c.goals.sub)
reset(J()); c = chat(); r = say(c, "سول عبي السيارة بنزين من الكازية"); ck("order line, no model", not CALLS and "بدأت" not in r and r in [v for vs in CS.ORDER_LINES.values() for v in vs], r)
reset(J(speech="الكازية عند الجسر الكبير 40 متر")); c = chat(); r = say(c, "شو في بالبلدة وين المحطة"); ck("world question the Mind can't answer: the model is asked, an invention is refused", len(CALLS) == 1 and r in RG.SAFE_UNKNOWN, (r, CALLS))
ck("world question: asked with what she knows", "Broadway St" in SYSTEMS[-1], SYSTEMS[-1][-200:])
reset(J(speech="هاد شارع برايدوو.")); c = chat(); r = say(c, "شو في بهالشارع؟"); ck("world question: a real name misspelt comes through right", len(CALLS) == 1 and "Broadway St" in r and "برايدوو" not in r, (r, CALLS))
reset(J(speech="ماشي")); c = chat(); r = say(c, "وين في بنزين بالبلدة؟"); ck("world question: runs nothing", RAN == [], RAN)
reset(J(speech="ماشي، بعمل هيك.", action="sol_nuke")); c = chat(); r = say(c, "سول احكي معي"); ck("hallucinated action: nothing runs", RAN == [] and len(CALLS) == 1, RAN)
reset(J(speech="ماشي", action="sol_horn", option="once")); c = chat(); r = say(c, "سول اعملي صوت"); ck("a proposal that passes is run by the Mind", RAN == [("sol_horn", "once")], RAN)
reset(J(speech="تكرم", action="sol_horn", option="once")); c = chat(); r = say(c, "شو رأيك"); ck("a chat question runs nothing", RAN == [], RAN)
reset(J(speech="زمرت مرتين.")); c = chat(); r = say(c, "سول احكيلي"); ck("claims without an action replaced", r in RG.SAFE_NOT_DONE, r)
reset(J(speech="ماشي")); c = chat(); say(c, "سول احكيلي"); names = [t["function"]["name"] for t in CALLS[0]]; ck("the model has no way to act", "do_action" not in names and "request_goal" not in names, names)
reset("ماشي [فعل: sol_engine | on]"); c = chat(); say(c, "سول طفي محرك السيارة"); c.goals = Goals(); c._turn_action_results = []; say(c, "سول احكيلي"); ck("tag cannot undo what he just ordered", ("sol_engine", "on") not in RAN, RAN)
LOG = []
def logged(reply, text="سول احكيلي عن الشارع"):
    reset(reply); LOG.clear(); ASKED.clear(); c = chat(); c.log = LOG.append
    return say(c, text)
r = logged(J(speech="الشارع المقرب هو برايدوو.")); ck("real path: the spelling is put right, the reply kept", "Broadway St" in r and "برايدوو" not in r, r)
ck("real path: logged as corrected", any("gate: corrected" in x and "Broadway St" in x for x in LOG), LOG)
ck("real path: the correction is not in what he reads", "gate" not in r and "->" not in r, r)
ck("real path: street and stations read at that moment", "street" in ASKED and "list" in ASKED, ASKED)
ck("real path: the facts reached the model", "Broadway St" in SYSTEMS[-1], SYSTEMS[-1][-300:])
r = logged(J(speech="الشارع المقرب هو الملك فيصل.")); ck("real path: invented is refused", r in RG.SAFE_UNKNOWN, r); ck("real path: logged as rejected", any("gate: rejected (world_claim_not_known)" in x for x in LOG), LOG)
r = logged(J(speech="ماشي، أنا معك.")); ck("real path: logged as kept", any("gate: kept" in x for x in LOG), LOG)
r = logged(J(speech="كازية Gas2Go قريبة.")); ck("real path: a brand with a digit is not a made-up number", "غاز تو غو" in r, r)
reset(None); REPLY["v"] = J(speech="تمام"); CS.SS.load_config = lambda: {"source": "none"}; c = chat(); r = say(c, "زمري مرة وحدة"); ck("no model connected: no reply and nothing happens", r is None and RAN == [] and not CALLS, (r, RAN))
r = say(c, "وين اقرب كازية"); ck("no model connected: not even the Mind answers in the chat", r is None and c.goals.sub == [], (r, c.goals.sub))
c = chat(); c.ask = lambda h: None; c.hist, c.lock, c.status, c.code, c.pending_card = [], __import__("threading").Lock(), "ok", "", None; c.publish = lambda: None; c.handle("زمري")
ck("no model: his line shows, no answer, no error", [m["role"] for m in c.hist] == ["user"] and c.status == "ok" and c.code == "", (c.hist, c.status, c.code))
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)

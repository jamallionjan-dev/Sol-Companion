"""The model reads every line first; the Mind runs it; if the model is off she is not frozen. Fake model, real Mind code. Offline PASS is not Runtime PASS."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "05_TOOLS", "sol_mind"))
import chat_service as CS, model_router as MR, reply_gate as RG, providers as P, settings_service as SS, world_knowledge as W
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
REPLY, CALLS, INTENTS, RAN = {"v": ""}, [], [], []
def fake_chat(pid, key, model, msgs, system="", custom_base="", max_tokens=0, timeout=0):
    CALLS.append((msgs[-1]["content"], timeout, max_tokens, system))
    if isinstance(REPLY["v"], Exception): raise REPLY["v"]
    return REPLY["v"]
P.chat = fake_chat
SS.load_config = lambda: {"source": "local", "provider": "custom", "model": "qwen3-test", "base": ""}
W.situation_text = lambda s, m: "world"
CS.resolve_and_run = lambda d, a, o, m, s: (RAN.append((a, o)), {"ok": True})[1]
CS.load_actions = lambda d: [{"id": "sol_cook", "kind": "button", "label": "طبخ", "enabled": True}, {"id": "sol_off", "kind": "button", "label": "x", "enabled": False}]
class Mem: data = {"places": [{"name": "الكازية"}], "deaths": 0}
tmp = tempfile.mkdtemp(prefix="sol_mf_")
def chat(off=False):
    c = CS.Chat.__new__(CS.Chat)
    c.dir, c.log, c._forced = tmp, lambda *a: None, None
    c._world = lambda: ({"solHome": {"x": 1, "y": 2}, "solParking": {"x": 3, "y": 4}, "solFarm": {"zones": [{"n": 59, "alive": 24, "empty": 34}], "stop": {"reason": "blocked", "detail": {"why": "no_path"}}}, "vehicles": [1, 2]}, Mem())
    c.gps_state = lambda: {}
    def pre(h, s, m):
        INTENTS.append(h[-1]["text"])
        if h[-1]["text"] == "الحقيني": c._turn_action_results = [{"ok": True}]; return ["ran follow"]
        return []
    c._pre_intents = pre
    c._receipt = lambda: "تكرم."
    c._player_takes_over = lambda a: None
    c._remember_action = lambda a, o: None
    c._gate_context = lambda h, a, k, n=(): RG.Context(h[-1]["text"], [], [], k, False, (), [])
    c._model_first = lambda: not off
    return c
def say(c, t): return c._ask_provider([{"role": "user", "text": t}])
def reset(v): REPLY["v"] = v; CALLS.clear(); INTENTS.clear(); RAN.clear()
J = lambda a, sp="": '{"action":"%s","args":{"option":null},"speech":"%s"}' % (a, sp)

reset(J("follow")); c = chat(); r = say(c, "الحقني")
ck("a typo reaches the Mind as its own order", INTENTS == ["الحقيني"], INTENTS)
ck("the model was asked first, quick", CALLS and CALLS[0][1] == 4 and CALLS[0][2] <= 80, CALLS[:1])
ck("thinking is off", CALLS[0][0].endswith("/no_think"))
ck("the reply is the Mind's", r == "تكرم.", r)
sheet = CALLS[0][3]
ck("sheet: who she is", "سول" in sheet and "مو بوت" in sheet)
ck("sheet: every Mind command", all(k in sheet for k in MR.COMMANDS))
ck("sheet: live actions, enabled only", "sol_cook" in sheet and "sol_off" not in sheet)
ck("sheet: her memory", "الكازية" in sheet and "59" in sheet)
reset(J("sol_cook")); c = chat(); r = say(c, "طبخي"); ck("a live action runs through the Mind", RAN == [("sol_cook", None)], RAN)
reset(J("fly_to_moon")); c = chat(); r = say(c, "طيري"); ck("not on the list: she asks, runs nothing", r.startswith("شو قصدك") and not RAN and not INTENTS, r)
reset(J("sol_off")); c = chat(); r = say(c, "x"); ck("a disabled action is not run", r.startswith("شو قصدك") and not RAN, r)
reset(J("unknown")); c = chat(); r = say(c, "ثثث"); ck("unknown: she asks", r.startswith("شو قصدك"), r)
reset(J("why")); c = chat(); r = say(c, "ليش"); ck("why: the real reason from the game", "طريق" in r, r)
reset(J("survey")); c = chat(); r = say(c, "فحصي المكان"); ck("survey: from the game", "1,2" in r and "3,4" in r and "59" in r and "24" in r and "2 سيارة" in r, r)
reset(J("none", "أهلين")); c = chat(); r = say(c, "مرحبا"); ck("talk: stands, runs nothing", r == "أهلين" and not RAN, r)
reset(J("none", "طفيتها")); c = chat(); r = say(c, "شو عملتي"); ck("talk: a claim the game did not confirm is refused", "طفيتها" not in r, r)
reset(P.ProviderError("unreachable")); c = chat(); r = say(c, "الحقيني"); ck("model down: urgent order still runs", INTENTS == ["الحقيني"] and r == "تكرم.", (INTENTS, r))
reset(P.ProviderError("unreachable")); c = chat(); r = say(c, "ثثث"); ck("model down, no order: answers at once, no second call", len(CALLS) == 1 and isinstance(r, str), (len(CALLS), r))
reset("كلام مو JSON"); c = chat(); r = say(c, "الحقيني"); ck("unreadable reply: word lists take it", INTENTS == ["الحقيني"], INTENTS)
ctx = RG.Context("وين الكازية؟", [], [], "", False, (), []); ctx.strict = True
t, why = RG.check_speech({"speech": "طفيتها، الجو حلو"}, ctx, False)
ck("a question never gets a remnant", why == "claims_an_action", (t, why))
ctx2 = RG.Context("وين الكازية؟", [], [], "", False, (), [])
t2, why2 = RG.check_speech({"speech": "طفيتها، الجو حلو"}, ctx2, False)
ck("switch off: the gate is as it was", why2 is None and t2 == "الجو حلو", (t2, why2))
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED: " + str(FAIL[:6]))
sys.exit(1 if FAIL else 0)

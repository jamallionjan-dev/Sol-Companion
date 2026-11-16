"""s90 two-tier card (apply_s90_card_tiers.py): installer on copies (idempotent, needs s85, applies after s86 / an s87-style
example change, and an s87-style card wrapper installed after it still works), tier 1 (rules + one index line of every action
+ memory), tier 2 (per-message examples: retrieval, compound and horn "بس" lines, the budget trim), CARD_TIERS off gives the
old card back, the chat builds the card per message, card_check.py and test_s82_route_eval.py pass on the patched copy.
Temp copies only; the live Mind and DOCS are read only (the doc check runs on a temp copy of SOL_MODEL_CARD.md).
Run: set PYTHONIOENCODING=utf-8 & python test_s90_card_tiers.py [sol_mind dir]      Offline PASS is not Runtime PASS."""
import hashlib, json, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, HERE)
import s82_route_harness as H
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "05_TOOLS", "sol_mind"))
CARD_CHECK = os.path.join(ROOT, "05_TOOLS", "sol_kahlua", "card_check.py")
DOC = os.path.join(ROOT, "DOCS", "SOL_MODEL_CARD.md")
APPLY = os.path.join(HERE, "apply_s90_card_tiers.py")
MARK85 = "# ---------------------------------------------------------------- s85 card budget, two orders in one line, exit first, far report"
NEW38 = ["board_vehicle", "exit_vehicle", "set_allow_overload", "set_follow_fan_out", "set_hold_fire", "set_ride_with_player", "set_scavenge",
         "sol_attack_nearest", "sol_bandage_player", "sol_car_wait", "sol_close_door", "sol_cook", "sol_cook_and_serve", "sol_drink", "sol_drive",
         "sol_eat", "sol_equip_best", "sol_fetch", "sol_fill_water", "sol_fuel", "sol_give", "sol_go_inside", "sol_goto", "sol_gps_clear",
         "sol_open_door", "sol_open_window", "sol_plan_cancel", "sol_plan_status", "sol_read", "sol_reload", "sol_replace_bandage", "sol_rest",
         "sol_sit_beside", "sol_stove_off", "sol_stove_on", "sol_take_pill", "sol_take_wheel", "sol_wash"]
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
def digest(d): return {f: hashlib.md5(open(os.path.join(d, f), "rb").read()).hexdigest() for f in sorted(os.listdir(d)) if f.endswith(".py")}
def copy_mind():
    d = tempfile.mkdtemp(prefix="sol_s90_")
    for f in os.listdir(SRC):
        if f.endswith((".py", ".gz")): shutil.copy(os.path.join(SRC, f), d)
    return d
def run(args, **kw): return subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV, **kw)
def add_block(d, f, block):
    p = os.path.join(d, f)
    t = open(p, encoding="utf-8", newline="").read()
    nl = chr(13) + chr(10) if chr(13) + chr(10) in t else chr(10)
    open(p, "w", encoding="utf-8", newline="").write(t.rstrip(chr(13) + chr(10)) + nl + nl + block.replace(chr(10), nl) + nl)

live0 = digest(SRC)
doc0 = hashlib.md5(open(DOC, "rb").read()).hexdigest() if os.path.exists(DOC) else None

# ---------------------------------------------------------------- 1. installer
A = copy_mind()
q1 = run([APPLY, A]); a1 = digest(A)
q2 = run([APPLY, A]); a2 = digest(A)
ck("installer applies (both files)", q1.returncode == 0 and q1.stdout.count("appended") == 2, q1.stdout + q1.stderr[-600:])
ck("installer is idempotent (second run keeps both, same bytes)", q2.returncode == 0 and q2.stdout.count("kept") == 2 and a1 == a2, q2.stdout)
B = copy_mind()
for f in ("model_router.py", "chat_service.py"):                      # the Mind before s85: refused, nothing written
    p = os.path.join(B, f); t = open(p, encoding="utf-8", newline="").read()
    if MARK85 in t: open(p, "w", encoding="utf-8", newline="").write(t[:t.index(MARK85)])
b0 = digest(B); q3 = run([APPLY, B])
ck("installer refuses a Mind without s85", q3.returncode != 0 and "s85 is not installed" in q3.stderr and digest(B) == b0, q3.stderr[-300:])
ck("installer: usage without a folder", run([APPLY]).returncode != 0)

# ---------------------------------------------------------------- 2. the card itself (child interpreter on the patched copy)
PROBE = r'''
import json, sys; sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[2])
import model_router as MR, s82_route_harness as H
acts = [{"id": i, "kind": "button" if i in H.BUTTONS else "tick" if i in H.TICKS else "sol", "label": i} for i in H.LIVE_IDS]
acts.append({"id": "horn_hold", "kind": "sol", "label": "horn_hold"})
out = {"tiers": MR.CARD_TIERS, "budget": MR.CARD_BUDGET, "index": MR.index_ids(acts), "index_line": MR.index_line(acts)}
out["tier1"] = MR.sheet(acts, "MEMORY-HERE")
out["bank"] = MR.example_bank(acts)
cards = {}
for s in ["طفي الغاز", "خدي حبة مسكن للوجع", "لا تطخي هلأ", "سول كيفك اليوم", "قعدي جنبي قدام بالسيارة", "بس", "اطبخيلي بيض وجيبيلي ياه"]:
    cards[s] = MR.add_examples(MR.sheet(acts, "MEMORY-HERE"), s, acts)
MR.HORN_HELD = True
out["held_bs"] = MR.add_examples(MR.sheet(acts, "MEMORY-HERE"), "بس", acts)
out["held_bank"] = MR.example_bank(acts)
MR.HORN_HELD = False
out["cards"] = cards
out["sim"] = {"same": MR.similarity_s90("اركبي السيارة", "ركبي السياره"), "alef": MR.similarity_s90("أعطيني مي", "اعطيني مى"),
              "far": MR.similarity_s90("طفي الغاز", "احرثي الارض")}
out["norm"] = MR.norm_s90("أإآى ة، مَرحَبًا!")
b0 = MR.CARD_BUDGET
t1 = len(MR.sheet(acts, "").rsplit("\n\nذاكرتك الآن:", 1)[0])
MR.CARD_BUDGET = t1 + 150
tight = MR.add_examples(MR.sheet(acts, ""), "طفي الغاز", acts)
out["tight"] = [len(tight.rsplit("\n\nذاكرتك الآن:", 1)[0]), MR.CARD_BUDGET, len(H.examples(tight))]
MR.CARD_BUDGET = b0
MR.CARD_TIERS = False
out["legacy"] = MR.sheet(acts, "MEMORY-HERE")
out["legacy_same"] = out["legacy"] == MR._sheet_pre_s90(acts, "MEMORY-HERE")
print(json.dumps(out, ensure_ascii=False))
'''
r = run(["-c", PROBE, A, HERE])
ck("probe runs", r.returncode == 0, r.stderr[-800:])
P = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else {}
if P:
    idx, t1 = P["index"], P["tier1"]
    ck("CARD_TIERS is on", P["tiers"] is True)
    ck("tier 1: the index line holds every one of the 38 actions the old card hid", all(a in idx for a in NEW38), [a for a in NEW38 if a not in idx])
    ck("tier 1: the index holds COMMANDS, CARD_ACTIONS and the game buttons", all(a in idx for a in ("follow", "refuel_from_can", "why", "survey", "cars_near",
                                                                                                  "sol_engine", "sol_headlights", "sol_horn", "horn_hold", "regroup", "bandage")))
    ck("tier 1: the index is one line, on the card, with option hints", "\n" not in P["index_line"] and P["index_line"] in t1 and "sol_engine(on|off)" in t1
       and "set_hold_fire(on|off)" in t1 and "horn_hold(start|stop)" in t1)
    ck("tier 1: no examples, memory kept at the end", "\nأمثلة:" in t1 and " -> {" not in t1 and t1.endswith("ذاكرتك الآن:\nMEMORY-HERE"))
    ck("tier 1: the rules stay (unknown, none, several actions) and say the examples are the nearest only",
       'action = "unknown"' in t1 and 'action = "none"' in t1 and '"actions"' in t1 and "الأقرب لكلامه" in t1)
    ck("tier 1 within the budget", len(t1.rsplit("\n\nذاكرتك الآن:", 1)[0]) <= P["budget"])
    bank_actions = {}
    for said, ans in P["bank"]:
        for a in [x.get("action") for x in json.loads(ans).get("actions", [json.loads(ans)])]: bank_actions.setdefault(a, []).append(said)
    ck("bank: every index action has >= 1 example", all(bank_actions.get(a) for a in idx), [a for a in idx if not bank_actions.get(a)])
    ck("bank: one answer per phrase", len({s for s, _ in P["bank"]}) == len(P["bank"]))
    ck("bank: the old card's examples are in it", all(any(s == x for s, _ in P["bank"]) for x in ("طفي متور السيارة", "شوفي عنا بالمخزون", "طفي المحرك ونزلي", "الحقيني")))
    ck("bank: 'بس' only while her hand is on the horn", not any(s == "بس" for s, _ in P["bank"]) and any(s == "بس" for s, _ in P["held_bank"]))
    C = P["cards"]
    def has(card, action): return any('"action":"%s"' % action in v for v in H.examples(card).values())
    for said, act in (("طفي الغاز", "sol_stove_off"), ("خدي حبة مسكن للوجع", "sol_take_pill"), ("لا تطخي هلأ", "set_hold_fire"),
                      ("قعدي جنبي قدام بالسيارة", "sol_sit_beside"), ("اطبخيلي بيض وجيبيلي ياه", "sol_cook_and_serve"), ("سول كيفك اليوم", "none")):
        ck("tier 2: '%s' gets a %s example" % (said, act), has(C[said], act), list(H.examples(C[said]))[:6])
    ck("tier 2: every card has a several-orders example", all('{"actions":' in c for c in C.values()))
    ck("tier 2: different lines, different examples", H.examples(C["طفي الغاز"]) != H.examples(C["لا تطخي هلأ"]))
    ck("tier 2: memory stays last", all(c.endswith("ذاكرتك الآن:\nMEMORY-HERE") for c in C.values()))
    ck("tier 2: every card within the budget", all(len(c.rsplit("\n\nذاكرتك الآن:", 1)[0]) <= P["budget"] for c in C.values()))
    ck("tier 2: 'بس' while not on the horn has no horn stop rule", "بس ->" not in C["بس"] and "إيدك عالزمور هلأ" not in C["بس"])
    ck("tier 2: hand on the horn, 'بس' gets its stop line first, with the rule", H.examples(P["held_bs"]).get("بس", "").find('"stop"') > 0 and "إيدك عالزمور هلأ" in P["held_bs"])
    ck("retrieval: alef / ya / ta marbuta folded, prefixes light", P["sim"]["same"] > 0.75 and P["sim"]["alef"] > 0.9 and P["sim"]["far"] < 0.3, P["sim"])
    ck("retrieval: norm folds letters and drops tashkeel / punctuation", P["norm"] == "اااي ه مرحبا", P["norm"])
    ck("budget trim: a tight budget keeps the card within it, at least one example", P["tight"][0] <= P["tight"][1] and P["tight"][2] >= 1, P["tight"])
    ck("CARD_TIERS off: the old one-tier card, unchanged", P["legacy_same"] and "\nالأفعال:\nfollow: " in P["legacy"] and " -> {" in P["legacy"])

# ---------------------------------------------------------------- 3. the chat builds the card per message (harness, mocked model)
res = H.run(A, [{"text": t, "model": "card_near"} for t in ("طفي الغاز", "خدي حبة مسكن للوجع", "عطيني شوية مي")] + [{"text": "x", "model": "unknown", "want_card": True}])
ck("chat: 'طفي الغاز' -> sol_stove_off through the card built for it", res[0]["game"] == [["sol_stove_off", None]], res[0]["game"])
ck("chat: 'خدي حبة مسكن للوجع' -> sol_take_pill", res[1]["game"] == [["sol_take_pill", None]], res[1]["game"])
ck("chat: 'عطيني شوية مي' -> sol_give water", res[2]["game"] == [["sol_give", "water"]], res[2]["game"])
ck("chat: each line got its own card size, all within the budget", len({r["card_chars"] for r in res[:3]}) > 1 and all(r["card_chars"] <= 4600 for r in res), [r["card_chars"] for r in res])
ck("chat: logs the per-line card", any("card for this line" in l for l in res[0]["log"]), res[0]["log"])
ck("harness: the bank comes back for the eval", len(res[3]["bank"]) >= 100, len(res[3]["bank"]))

# ---------------------------------------------------------------- 4. order: s87-style examples before s90, an s87-style card wrapper after it
S87_BEFORE = '''# ---------------------------------------------------------------- test: an s87-style change before s90
EXAMPLES += (("تعي لهون بسرعة", "come_foot"),)
_sheet_t87 = sheet


def sheet(actions, memory):
    text = _sheet_t87(actions, memory)
    return text.replace("\\n\\nذاكرتك الآن:", "\\nشو عم تعملي هلأ -> {\\"action\\":\\"farm_status\\"}\\n\\nذاكرتك الآن:", 1)
'''
S87_AFTER = S87_BEFORE.replace("_sheet_t87", "_sheet_t87b").replace("before s90", "after s90").replace("تعي لهون بسرعة", "تعي لعندي مشي هلأ").replace("شو عم تعملي هلأ", "شو عم تعملي بالضبط")
C1 = copy_mind(); add_block(C1, "model_router.py", S87_BEFORE)
q4 = run([APPLY, C1])
ck("installer applies after an s87-style change", q4.returncode == 0, q4.stderr[-400:])
r = run(["-c", PROBE, C1, HERE])
B1 = json.loads(r.stdout.strip().splitlines()[-1])["bank"] if r.returncode == 0 else []
ck("s87-style examples (EXAMPLES and a sheet wrapper) land in the bank", ("تعي لهون بسرعة", '{"action":"come_foot"}') in [tuple(x) for x in B1]
   and ("شو عم تعملي هلأ", '{"action":"farm_status"}') in [tuple(x) for x in B1], r.stderr[-400:])
add_block(C1, "model_router.py", S87_AFTER)
r = run(["-c", PROBE, C1, HERE])
ck("an s87-style card wrapper installed after s90 still builds (tier 1 + its line, per message)", r.returncode == 0 and "شو عم تعملي بالضبط" in json.loads(r.stdout.strip().splitlines()[-1])["cards"]["طفي الغاز"], r.stderr[-400:])
res = H.run(C1, [{"text": "طفي الغاز", "model": "card_near"}])
ck("... and the chat still routes through it", res[0]["game"] == [["sol_stove_off", None]], res[0]["game"])

# ---------------------------------------------------------------- 4b. the real later stages, in the install order: s90, s87 mind, s91 mind
LATER = [os.path.join(HERE, f) for f in ("apply_s87_mind.py", "apply_s91_engine_off_exit_mind.py")]
if all(os.path.exists(f) for f in LATER):
    C2 = copy_mind(); C2_ok = run([APPLY, C2]).returncode == 0
    for f in LATER: C2_ok = C2_ok and run([f, C2]).returncode == 0
    ck("s90 then s87 mind then s91 mind apply", C2_ok)
    r = run(["-c", PROBE, C2, HERE])
    P2 = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else {"bank": [], "cards": {}}
    bank2 = {s: a for s, a in P2["bank"]}
    ck("s91's keep_engine example is in s90's bank (not a fixed card line)", bank2.get("نزلي من السيارة وخلي المحرك شغال") == '{"action":"exit_car","args":{"option":"keep_engine"}}'
       and "keep_engine" not in P2.get("tier1", "keep_engine"), r.stderr[-300:])
    ck("s87's smart park has its example in the bank", bank2.get("صفيها بأقرب مكان فاضي") == '{"action":"park"}')
    tmpdoc2 = os.path.join(tempfile.mkdtemp(prefix="sol_s90_doc_"), "SOL_MODEL_CARD.md")
    if os.path.exists(DOC): shutil.copy(DOC, tmpdoc2)
    r = run([CARD_CHECK, C2, "--doc", tmpdoc2, "--write-doc"])
    ck("card_check.py on s90 + s87 + s91: %s" % ((r.stdout.strip().splitlines() or [""])[-1]), r.returncode == 0, [l for l in r.stdout.splitlines() if l.startswith("FAIL")][:8])
    for test in ("test_s87.py", "test_s91_engine_off_exit.py"):
        if os.path.exists(os.path.join(HERE, test)):
            r = run([os.path.join(HERE, test), C2])
            ck("%s on s90 + s87 + s91: %s" % (test, (r.stdout.strip().splitlines() or [""])[-1]), r.returncode == 0, [l for l in r.stdout.splitlines() if "FAIL" in l][:8])
else:
    print("     4b. skipped: apply_s87_mind.py / apply_s91_engine_off_exit_mind.py not here")

# ---------------------------------------------------------------- 5. the gates on the patched copy
tmpdoc = os.path.join(tempfile.mkdtemp(prefix="sol_s90_doc_"), "SOL_MODEL_CARD.md")
if os.path.exists(DOC): shutil.copy(DOC, tmpdoc)
r = run([CARD_CHECK, A, "--doc", tmpdoc, "--write-doc"])
last = (r.stdout.strip().splitlines() or [""])[-1]
ck("card_check.py on the patched copy (doc: a temp copy, --write-doc) passes: %s" % last, r.returncode == 0, [l for l in r.stdout.splitlines() if l.startswith("FAIL")][:10])
ck("card_check: no warnings left (the 38 hidden actions are on the index)", "0 warnings" in last, last)
r2 = run([CARD_CHECK, A, "--doc", tmpdoc, "--no-eval"])
ck("card_check: the written doc section matches (second run)", r2.returncode == 0, [l for l in r2.stdout.splitlines() if l.startswith("FAIL")][:5])
r = run([os.path.join(HERE, "test_s82_route_eval.py"), "--as-is", A])
ck("test_s82_route_eval.py --as-is on the patched copy: %s" % ((r.stdout.strip().splitlines() or [""])[-1]), r.returncode == 0,
   [l for l in r.stdout.splitlines() if l.startswith("FAIL")][:10] or r.stderr[-400:])

# ---------------------------------------------------------------- 6. nothing live touched
ck("the live Mind is unchanged", digest(SRC) == live0)
ck("DOCS/SOL_MODEL_CARD.md is unchanged", (hashlib.md5(open(DOC, "rb").read()).hexdigest() if os.path.exists(DOC) else None) == doc0)
print("RESULT", "ALL PASS" if not FAIL else "%d FAILED" % len(FAIL))
sys.exit(1 if FAIL else 0)

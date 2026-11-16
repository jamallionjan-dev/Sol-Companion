"""s82 Mind (apply_s82_engine_words.py): installer on copies (idempotent, any order with s78 / s79), the card budget, the card's
rules and examples, and the routing with mocked models: the live 22:15:41 misroute ("طفي متور السيارة" -> headlights) reproduced on
the old card by a nearest-example model and gone on the new one; street / town questions answered by the map, also when the
model says unknown. Temp copies only; the live Mind and the lab are read only.
Run: set PYTHONIOENCODING=utf-8 & python test_s82_mind.py [sol_mind dir]      Offline PASS is not Runtime PASS."""
import hashlib, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Arabic lines, whoever runs it
sys.path.insert(0, HERE)
import s82_route_harness as H
SRC = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind"))
LAB_LUA = os.path.abspath(os.path.join(HERE, "..", "profile", "Zomboid", "Lua"))
BUDGET = 4600
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
FILES = ["model_router.py", "chat_service.py", "memory_answers.py"]
def copy_mind():
    d = tempfile.mkdtemp(prefix="sol_s82m_")
    for f in os.listdir(SRC):
        if f.endswith((".py", ".gz")): shutil.copy(os.path.join(SRC, f), d)
    return d
def apply(script, d): return subprocess.run([sys.executable, os.path.join(HERE, script), d], capture_output=True, text=True, encoding="utf-8", errors="replace")
def digest(d): return {f: hashlib.md5(open(os.path.join(d, f), "rb").read()).hexdigest() for f in FILES}
SIZE = r'''
import json, sys; sys.path.insert(0, sys.argv[1])
import chat_service as CS, model_router as MR
acts = CS.load_actions(sys.argv[2])
if len(sys.argv) > 3:                                                       # horn_hold on (its switch), her hand off / on the horn
    acts = [dict(a, enabled=True) for a in acts if a.get("id") != "horn_hold"] + [{"id": "horn_hold", "kind": "sol", "state": "idle"}]
    MR.HORN_HELD = sys.argv[3] == "held"
s = MR.sheet(acts, "")
print(json.dumps({"size": len(s.rsplit("\n\nذاكرتك الآن:", 1)[0]), "budget": getattr(MR, "CARD_BUDGET", None), "card": s, "n_acts": len(acts)}, ensure_ascii=False))
'''
def card_of(d, horn=None):
    import json
    r = subprocess.run([sys.executable, "-c", SIZE, d, LAB_LUA] + ([horn] if horn else []), capture_output=True, text=True, encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout.strip().splitlines()[-1])

MARK82 = "# ---------------------------------------------------------------- s82 engine words, place questions, compact card"
def before_s82(src):
    """The Mind as it was before s82 (s82 and everything after it cut off each file), or src itself when s82 is not in it yet."""
    if MARK82 not in open(os.path.join(src, "model_router.py"), encoding="utf-8").read(): return src
    d = copy_mind()
    for f in FILES:
        t = open(os.path.join(d, f), encoding="utf-8", newline="").read()
        if MARK82 in t:
            nl = chr(13) + chr(10) if chr(13) + chr(10) in t else chr(10)
            open(os.path.join(d, f), "w", encoding="utf-8", newline="").write(t[:t.index(MARK82)].rstrip(chr(13) + chr(10)) + nl)
    return d
OLD = before_s82(SRC)
live0 = digest(SRC)
# ---------------------------------------------------------------- 1. installer
A = copy_mind()
q1 = apply("apply_s82_engine_words.py", A); a1 = digest(A)
q2 = apply("apply_s82_engine_words.py", A); a2 = digest(A)
ck("installer applies", q1.returncode == 0 and "applied" in q1.stdout, q1.stderr[-600:])
ck("installer is idempotent", q2.returncode == 0 and a1 == a2 and q2.stdout.count("kept") == 3, q2.stdout)
for order in (("apply_s78_cars_away_mind.py", "apply_s79_horn_hold_mind.py", "apply_s82_engine_words.py"),
              ("apply_s82_engine_words.py", "apply_s78_cars_away_mind.py", "apply_s79_horn_hold_mind.py")):
    B = copy_mind()
    rs = [apply(s, B) for s in order]
    ok = all(r.returncode == 0 for r in rs)
    imp = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import chat_service, model_router, memory_answers", B], capture_output=True, text=True)
    c = card_of(B) if ok else {"size": -1, "card": ""}
    ck("with s78 + s79, order %s: applies, imports, card %d chars <= %d (horn_hold off, as in the lab now)" % ("/".join(o[6:9] for o in order), c["size"], BUDGET),
       ok and imp.returncode == 0 and 0 < c["size"] <= BUDGET, [r.stderr[-300:] for r in rs] + [imp.stderr[-300:]])
    ck("  ... and its examples are still on the card", all(x in c["card"] for x in ("طفي متور السيارة", "شو اسم هالشارع", "تعالي بالسيارة")))
for step in ("apply_s85_mind.py",):                                             # what comes after s82 (the card budget with every switch on)
    if os.path.exists(os.path.join(HERE, step)):
        q = apply(step, A)
        ck("%s applies after s82" % step, q.returncode == 0, q.stderr[-600:])
ck("live Mind untouched", digest(SRC) == live0)

# ---------------------------------------------------------------- 2. the card
old, new = card_of(OLD), card_of(A)
print("card size (the lab's live action list, no memory): before %d, after %d, budget %d" % (old["size"], new["size"], BUDGET))
ck("card budget: %d <= CARD_BUDGET %s" % (new["size"], new["budget"]), new["budget"] == BUDGET and new["size"] <= BUDGET, new["size"])
ck("card is smaller than before s82", new["size"] < old["size"], (old["size"], new["size"]))
for horn in ("idle", "held"):
    h = card_of(A, horn)
    ck("card budget with horn_hold on, her hand %s the horn: %d <= %d" % ("on" if horn == "held" else "off", h["size"], BUDGET), h["size"] <= BUDGET, h["size"] - BUDGET)
    if "s79 horn_hold" in open(os.path.join(A, "model_router.py"), encoding="utf-8").read():          # s79 installed
        ck("  ... horn_hold listed, 'بس' only while held", (chr(10) + "horn_hold: ") in h["card"] and (("/ بس ->" in h["card"] or (chr(10) + "بس ->") in h["card"]) == (horn == "held")))
ck("card lists actions (not an empty action file)", new["n_acts"] > 0 and "sol_engine:" in new["card"])
card = new["card"]
ck("rule: a request not on the list -> unknown", 'طلب شغلة مو بالقائمة، أو كلام مش مفهوم أبدًا: action = "unknown"' in card)
ck("rule: a question (street, town, station, where) -> none", 'سؤال (وين نحنا، شو اسم الشارع أو المدينة أو الكازية) أو كلام عادي بدون طلب: action = "none"' in card)
ck("old rule gone", "أو مو موجود بالقائمة" not in card)
ex = H.examples(card)
for t, a, o in (("طفي متور السيارة", "sol_engine", "off"), ("طفي الموتور", "sol_engine", "off"), ("شغلي الموتور", "sol_engine", "on"), ("طفي ضو السيارة", "sol_headlights", "off")):
    ck("example: %s -> %s %s" % (t, a, o), t in ex and ('"action":"%s"' % a) in ex[t] and ('"option":"%s"' % o) in ex[t], ex.get(t))
for t in ("شو اسم هالشارع", "بأي شارع نحنا", "وين نحنا هلأ", "شو اسم هي المدينة", "بأي ضيعة نحنا", "شو هالكازية"):
    ck("example: %s -> none" % t, ex.get(t) == '{"action":"none"}', ex.get(t))
body = card.split("\nأمثلة:\n", 1)[1].split("\n\nذاكرتك الآن:", 1)[0].splitlines()
answers = [l[l.find(" -> {") + 4:] for l in body if " -> {" in l]
ck("examples: one line per answer", len(answers) == len(set(answers)), [a for a in answers if answers.count(a) > 1])
ck("examples: none repeats the list's own example", all(x not in ex for x in ("ليش ما زبطت", "شوفي سيارات حواليكي")))
ck("action list: compact ' | \"x\"' form", ' | مثال: "' not in card and 'sol_engine: محرك السيارة | "شغلي السيارة" | option: on أو off' in card)
CASES = ["سول طفي متور السيارة", "طفي الموتور", "شغلي الموتور"]

# ---------------------------------------------------------------- 3. routing, mocked models
r0 = H.run(OLD, [{"text": t, "model": "nearest"} for t in CASES])
r1 = H.run(A, [{"text": t, "model": "nearest"} for t in CASES] + [{"text": t, "model": "card"} for t in CASES])
ck("old card, nearest-example model: 'سول طفي متور السيارة' -> sol_headlights off (the live 22:15:41 misroute)", r0[0]["game"] == [["sol_headlights", "off"]], r0[0]["game"])
for i, (t, o) in enumerate(zip(CASES, ("off", "off", "on"))):
    ck("new card, nearest-example model: '%s' -> sol_engine %s" % (t, o), r1[i]["game"] == [["sol_engine", o]], r1[i]["game"])
    ck("new card, card model: '%s' -> sol_engine %s" % (t, o), r1[3 + i]["game"] == [["sol_engine", o]], r1[3 + i]["game"])
Q = [("شو اسم هالشارع", "هاد S Main St."), ("شو اسم هاد الشارع", "هاد S Main St."), ("بأي شارع نحنا", "هاد S Main St."),
     ("وين نحنا هلأ", "نحنا على S Main St بـمولدرو."), ("شو اسم هي المدينة", "هاي مولدرو."), ("بأي ضيعة نحنا", "هاي مولدرو."), ("بأي مدينة نحنا", "هاي مولدرو.")]
rq = H.run(A, [{"text": t, "model": "card"} for t, _ in Q] + [{"text": t, "model": "unknown"} for t, _ in Q])
for i, (t, want) in enumerate(Q):
    ck("card model: '%s' -> none -> the map: '%s'" % (t, want), rq[i]["path"] == "memory" and rq[i]["reply"] == want and not rq[i]["game"], (rq[i]["path"], rq[i]["reply"]))
    ck("unknown model: '%s' -> path=memory_after_unknown '%s'" % (t, want), rq[len(Q) + i]["path"] == "memory_after_unknown" and rq[len(Q) + i]["reply"] == want, (rq[len(Q) + i]["path"], rq[len(Q) + i]["reply"]))
ru = H.run(A, [{"text": "رقصي", "model": "unknown"}, {"text": "سوقي عالبيت", "model": "unknown"}, {"text": "شو اسم هالشارع", "model": {"action": "refuel_from_can"}},
               {"text": "شو اسم هالشارع", "model": {"action": "fly_away"}}])
ck("unknown, not a question: asks him again, runs nothing", ru[0]["reply"] == "شو قصدك؟ عيدها بكلمة تانية." and not ru[0]["game"])
ck("unknown on an order: no order runs from the fallback (model first)", not ru[1]["game"] and not ru[1]["pre"] and ru[1]["reply"] == "شو قصدك؟ عيدها بكلمة تانية.", ru[1])
ck("refuel chosen with no fuel word: still asks him (that is not an unknown)", ru[2]["reply"] == "شو قصدك؟ عيدها بكلمة تانية." and ru[2]["path"] == "model", (ru[2]["path"], ru[2]["reply"]))
ck("an action not on the list counts as unknown: the map answers", ru[3]["path"] == "memory_after_unknown" and ru[3]["reply"] == "هاد S Main St.", (ru[3]["path"], ru[3]["reply"]))
rl = H.run(OLD, [{"text": "شو اسم هالشارع", "model": "unknown"}])
ck("old Mind, unknown model: 'شو اسم هالشارع' asked him again (the live 22:22:17 reply, reproduced)", rl[0]["reply"] == "شو قصدك؟ عيدها بكلمة تانية.", rl[0]["reply"])
print("RESULT", "ALL PASS" if not FAIL else "%d FAILED: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)

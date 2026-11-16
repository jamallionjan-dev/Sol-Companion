"""s105 combat_plans offline, Mind side: apply_s105_combat_plans_mind.py on a temp copy of 05_TOOLS/sol_mind (the live Mind is
only read). Shows: installer idempotent; with the switch off (sol_combat_plan not in the game's list) the card is exactly the old
one; with it on: one action line with every plan id and its Arabic name, at least one example line, the team-doctrine button off
the card, within CARD_BUDGET with her hand on the horn or not; the two-tier bank (s90) gets every plan example; the model's
answer runs the game verb with the plan id (an Arabic plan name as option is mapped back), she answers in her own words, an
unknown plan runs nothing; card_check passes on the patched Mind + patched Lua with combat_plans=on; the s82 route eval passes.
Run: python test_s105_combat_plans_mind.py"""
import json, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import s82_route_harness as H
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LIVE_MIND = os.path.join(ROOT, "05_TOOLS", "sol_mind")
LAB = os.path.join(ROOT, "07_TEST", "SOL_LAB")
CL = os.path.join(LAB, "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
PROFILE = os.path.join(LAB, "profile", "Zomboid", "Lua")
FAIL, P = [], []
def ck(n, c, d=""): print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else "")); (P if c else FAIL).append(n)
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
tmp = tempfile.mkdtemp(prefix="s105m_")
mind = os.path.join(tmp, "mind"); os.makedirs(mind)
for f in os.listdir(LIVE_MIND):
    if f.endswith((".py", ".gz")): shutil.copy(os.path.join(LIVE_MIND, f), mind)
r1 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s105_combat_plans_mind.py"), mind], capture_output=True, text=True, env=ENV)
r2 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s105_combat_plans_mind.py"), mind], capture_output=True, text=True, env=ENV)
ck("mind installer runs", r1.returncode == 0 and "appended" in r1.stdout, r1.stdout + r1.stderr)
ck("mind installer second run changes nothing", r2.returncode == 0 and "appended" not in r2.stdout and "kept" in r2.stdout, r2.stdout + r2.stderr)

CHILD = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import chat_service as CS, model_router as MR
acts = CS.load_actions(sys.argv[2])
full = [dict(a, enabled=True) for a in acts] + [{"id": "horn_hold", "kind": "sol", "enabled": True}]
plan = full + [{"id": "sol_combat_plan", "kind": "sol", "enabled": True}]
out = {"budget": MR.CARD_BUDGET, "has_s105": hasattr(MR, "plan_id_s105")}
for held in (False, True):
    MR.HORN_HELD = held
    out["off_%s" % held] = MR.sheet(full, "")
    out["on_%s" % held] = MR.sheet(plan, "")
    out["size_on_%s" % held] = MR.card_size(plan)
MR.HORN_HELD = False
if out["has_s105"]:
    out["ids"] = {o: MR.plan_id_s105(o) for o in ("fierce", "Careful", "حذرة", "شرسة", "ما تطلقي", "مخفية", "banana", "", None)}
    out["lines"] = CS.PLAN_LINES_S105
    out["fail"] = {w: CS.plan_line_s105("careful", {"ok": False, "reason": w}) for w in ("no_sol", "unknown_option", "not_recruited", "lf_error:x")}
    out["unconfirmed"] = CS.plan_line_s105("careful", {"ok": None, "reason": "sent; the game did not confirm yet"})
    if hasattr(MR, "example_bank"):
        MR.CARD_TIERS = True
        out["bank"] = [list(e) for e in MR.example_bank(plan) if "sol_combat_plan" in e[1]]
        out["index"] = MR.index_line(plan)
        MR.CARD_TIERS = False
print(json.dumps(out, ensure_ascii=False))
'''
def child(m):
    r = subprocess.run([sys.executable, "-c", CHILD, m, PROFILE], capture_output=True, text=True, encoding="utf-8", env=ENV, cwd=tmp)
    if r.returncode: print(r.stderr[-1500:]); return None
    return json.loads(r.stdout.strip().splitlines()[-1])
old, new = child(LIVE_MIND), child(mind)
ck("patched Mind imports", new is not None and new.get("has_s105"))
NL = "\n"
for held in (False, True):
    ck("switch off (no sol_combat_plan in the game's list), hand on horn %s: the card is exactly the old one" % held, old and new and old["off_%s" % held] == new["off_%s" % held])
    ck("switch on, hand on horn %s: card %d <= budget %d" % (held, new["size_on_%s" % held], new["budget"]), new["size_on_%s" % held] <= new["budget"])
card = new["on_False"]
line = next((l for l in card.split(NL) if l.startswith("sol_combat_plan: ")), "")
ck("one action line for the plans", card.count(NL + "sol_combat_plan: ") == 1, line)
for pid, ar in (("smart", "ذكية"), ("normal", "عادي"), ("fierce", "شرسة"), ("support", "إسناد"), ("careful", "حذرة"), ("stealth", "مخفية"), ("avoid", "تجنّب"), ("hold", "ما تطلقي")):
    ck("the line names plan %s with its Arabic name %s" % (pid, ar), (pid + " " + ar) in line, line)
shots = [l for l in card.split(NL) if '"action":"sol_combat_plan"' in l]
ck("at most 2 plan examples on the card (the line's own + at most one line)", len(shots) <= 1 and '"قاتلي بشراسة"' in line, shots)
ck("the none rule remains concise (place questions use none)", '- سؤال عن المكان أو كلام عادي: action = "none"' in card)
ck("the team-doctrine button is off the card while the plans are on it", "set_combat_doctrine: " not in card and "set_combat_doctrine: " in new["off_False"])
none_line = next((l for l in card.split(NL) if l.endswith('-> {"action":"none"}')), "")
ck("the none examples still ask a street, a place and a station (card_check features)", "شارع" in none_line and "ضيعة" in none_line and "كازية" in none_line, none_line)
ck("plan ids: fierce, Careful, Arabic names -> ids; unknown / empty -> None", new["ids"] == {"fierce": "fierce", "Careful": "careful", "حذرة": "careful", "شرسة": "fierce", "ما تطلقي": "hold", "مخفية": "stealth", "banana": None, "": None, "null": None}, new["ids"])
ck("her lines: one per plan, the careful one as Jamal wrote it", len(new["lines"]) == 8 and new["lines"]["careful"] == "تمام، رح كون حذرة.", new["lines"])
ck("her lines are plain words (no ids, no technical words)", all(all(ord(c) > 127 or c in " ،.!؟," for c in v) for v in new["lines"].values()), new["lines"])
ck("refusals in her words", new["fail"]["no_sol"] == "ما فيني هلأ." and new["fail"]["unknown_option"] == "أي خطة بتقصد؟" and new["fail"]["lf_error:x"] == "ما قدرت غيّر الخطة هلأ.", new["fail"])
ck("a result the game has not confirmed keeps the usual reply", new["unconfirmed"] is None)
if "bank" in new:
    got = {s: json.loads(a)["args"]["option"] for s, a in new["bank"]}
    ck("two-tier bank (s90): every plan has an example", set(got.values()) == {"smart", "normal", "fierce", "support", "careful", "stealth", "avoid", "hold"}, got)
    ck("two-tier bank: 'قاتلي بشراسة' -> fierce, 'ما تطلقي' -> hold, 'خليكي حذرة' -> careful", got.get("قاتلي بشراسة") == "fierce" and got.get("ما تطلقي") == "hold" and got.get("خليكي حذرة") == "careful", got)
    ck("two-tier index: sol_combat_plan with its options", "sol_combat_plan(fierce|smart|normal|support|careful|stealth|avoid|hold)" in new["index"], new["index"][-200:])

# the model's answer, through the real Chat._route_by_model (mocked model, stub game: s82_route_harness)
IDS = H.LIVE_IDS + ["sol_combat_plan"]
def case(text, model, ids=IDS): return {"text": text, "model": model, "actions": ids}
def plan(o): return {"action": "sol_combat_plan", "args": {"option": o}, "speech": ""}
cases = [case("خليكي حذرة", plan("careful")), case("قاتلي بشراسة", plan("شرسة")), case("رح نقاتل هلأ", plan("banana")),
         case("اسنديني من بعيد", "card"), case("ما تطلقي وتعالي ورايي", {"actions": [{"action": "sol_combat_plan", "args": {"option": "hold"}}, {"action": "follow"}]}),
         case("خليكي حذرة", plan("careful"), H.LIVE_IDS)]
cases += [case("plan " + p, plan(p)) for p in ("smart", "normal", "fierce", "support", "careful", "stealth", "avoid", "hold")]
res = H.run(mind, cases)
ck("'خليكي حذرة' -> the game runs sol_combat_plan careful; she says 'تمام، رح كون حذرة.'", res[0]["game"] == [["sol_combat_plan", "careful"]] and res[0]["reply"] == "تمام، رح كون حذرة.", res[0])
ck("an Arabic plan name as option (شرسة) -> the game gets fierce", res[1]["game"] == [["sol_combat_plan", "fierce"]] and res[1]["reply"] == new["lines"]["fierce"], res[1])
ck("an unknown plan -> nothing runs, she asks which plan", res[2]["game"] == [] and res[2]["reply"] == "أي خطة بتقصد؟", res[2])
ck("card mock: a plan phrase that is not an example line on the card runs nothing by itself (model first)", res[3]["game"] in ([], [["sol_combat_plan", "support"]]), res[3])
ck("two orders: hold fire then follow -> both run, her hold line is in the reply", ["sol_combat_plan", "hold"] in res[4]["game"] and "ما بطلق" in str(res[4]["reply"]), res[4])
ck("switch off (not in the game's list): the Mind does not run it", res[5]["game"] == [] and res[5]["gate"] == "not_an_action", res[5])
for i, p in enumerate(("smart", "normal", "fierce", "support", "careful", "stealth", "avoid", "hold")):
    r = res[6 + i]
    ck("plan %s: game gets %s, she says her line" % (p, p), r["game"] == [["sol_combat_plan", p]] and r["reply"] == new["lines"][p], r)

# card_check on the patched Mind + the patched Lua with combat_plans=on (a temp doc copy; the real doc is not touched)
cl = os.path.join(tmp, "client"); os.makedirs(cl)
for f in os.listdir(CL):
    if f.endswith(".lua"): shutil.copy(os.path.join(CL, f), cl)
subprocess.run([sys.executable, os.path.join(HERE, "apply_s105_combat_plans.py"), cl], capture_output=True, text=True)
fixes = os.path.join(tmp, "SolFixes_LAB.txt")
body = open(os.path.join(PROFILE, "SolFixes_LAB.txt"), encoding="utf-8").read()
open(fixes, "w", encoding="utf-8").write(body + ("" if body.endswith("\n") else "\n") + "combat_plans=on\n")
doc = os.path.join(tmp, "SOL_MODEL_CARD.md"); shutil.copy(os.path.join(ROOT, "DOCS", "SOL_MODEL_CARD.md"), doc)
CC = os.path.join(ROOT, "05_TOOLS", "sol_kahlua", "card_check.py")
w = subprocess.run([sys.executable, "-I", CC, mind, "--lua", cl, "--fixes", fixes, "--doc", doc, "--write-doc", "--no-eval"], capture_output=True, text=True, encoding="utf-8", env=ENV)
c = subprocess.run([sys.executable, "-I", CC, mind, "--lua", cl, "--fixes", fixes, "--doc", doc], capture_output=True, text=True, encoding="utf-8", env=ENV)
tail = c.stdout.strip().splitlines()[-1] if c.stdout.strip() else c.stderr[-300:]
ck("card_check (combat_plans on, switch-gated action found, doc regenerated on a copy, route eval): PASS", c.returncode == 0, "\n".join(l for l in c.stdout.splitlines() if l.startswith("FAIL"))[:800] or tail)
ck("card_check sees sol_combat_plan behind combat_plans", "sol_combat_plan" in c.stdout and "combat_plans" in c.stdout)
print("     " + tail)
c0 = subprocess.run([sys.executable, "-I", CC, mind, "--lua", CL, "--no-eval"], capture_output=True, text=True, encoding="utf-8", env=ENV)
fails0 = [l for l in c0.stdout.splitlines() if l.startswith("FAIL ")]
ck("install the Mind and the Lua side TOGETHER: the patched Mind with today's Lua fails card_check on exactly that (sol_combat_plan not in the game's list)",
   c0.returncode == 1 and len(fails0) == 1 and "CARD_ACTIONS sol_combat_plan exists in the game catalog" in fails0[0], fails0)
ev = subprocess.run([sys.executable, os.path.join(HERE, "test_s82_route_eval.py"), "--as-is", mind], capture_output=True, text=True, encoding="utf-8", env=ENV)
ck("s82 route eval on the patched Mind: ALL PASS", ev.returncode == 0 and "ALL PASS" in ev.stdout, ev.stdout[-600:])
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(P), len(FAIL))); sys.exit(1 if FAIL else 0)

"""s82 route regression eval: every phrase in s82_route_eval.json (what the routing got right before, from sol_mind.log, plus the
street / town / station questions) and every example on the card, replayed through Chat._route_by_model with a mocked model.
  1. the model gives the recorded answer -> the right action runs (or the map answer for a question); nothing else runs.
  2. the model says unknown            -> a question still gets the map answer (path=memory_after_unknown); an order runs NOTHING
                                          (model first: the fallback only answers, it never routes an order).
  3. the card mock (examples only)     -> each example on the card reaches its own answer, and every answer it names is routable.
                                          s90 two-tier card: every example in the bank, each on the card built for that very line.
  4. s90 (two-tier card only): the cases marked "mock": "card" (one per action the old card never showed) with a model that
     reads only the examples on the card built for that line (card_near) -> the right action runs; every message's card
     (tier 1 + its examples, without memory) <= model_router.CARD_BUDGET.
Run:  python test_s82_route_eval.py                 a temp copy of 05_TOOLS/sol_mind with apply_s82_engine_words.py and apply_s85_mind.py applied
      python test_s82_route_eval.py --as-is <dir>   that Mind exactly as it is (build_release.py runs this on the live Mind)
      python test_s82_route_eval.py --live --yes-jamal-is-not-playing [<dir>]
                                                    the connected (phone) model, for real. Refuses without the second flag, and
                                                    while the game runs. Only reads; prints a table, exit 1 on any miss.
Offline PASS is not Runtime PASS."""
import json, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Arabic lines, whoever runs it
sys.path.insert(0, HERE)
import s82_route_harness as H
LIVE_MIND = os.path.abspath(os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind"))
ASK = "شو قصدك؟ عيدها بكلمة تانية."
SPECIAL = {"survey": "survey", "why": "why", "cars_near": "cars"}      # the harness's stub answers for the Mind's own handlers
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)


def mind_dir(args):
    if "--as-is" in args: return os.path.abspath(args[args.index("--as-is") + 1])
    rest = [a for a in args if not a.startswith("--")]
    src = os.path.abspath(rest[0]) if rest else LIVE_MIND
    if "--live" in args: return src
    d = tempfile.mkdtemp(prefix="sol_s82_eval_")
    for f in os.listdir(src):
        if f.endswith((".py", ".gz")): shutil.copy(os.path.join(src, f), d)
    for step in ("apply_s82_engine_words.py", "apply_s85_mind.py", "apply_s90_card_tiers.py"):   # s85 after s82, s90 (two-tier card) last
        if not os.path.exists(os.path.join(HERE, step)): continue
        r = subprocess.run([sys.executable, os.path.join(HERE, step), d], capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert r.returncode == 0, r.stderr[-800:]
    return d


def steps_ok(steps, r, commands):
    """s85: every step ran, in this order (a game action with its option, or a Mind command routed by its phrase)."""
    seq, i = r.get("seq") or [], 0
    for s in steps:
        a, o = s["action"], s.get("option")
        while i < len(seq) and not ((seq[i][0] == "game" and seq[i][1] == a and (o is None or seq[i][2] == o)) or (seq[i][0] == "pre" and seq[i][1] == a)):
            i += 1
        if i >= len(seq): return False
        i += 1
    return True


def outcome_ok(case, r, commands):
    """Did the routing do what this phrase needs, given the model gave the expected answer?"""
    if case.get("steps"): return steps_ok(case["steps"], r, commands)
    a, o = case["action"], case.get("option")
    if case["kind"] == "memory":
        return r["path"] in ("memory", "memory_after_unknown") and bool(r["reply"]) and r["reply"] != ASK and not r["game"] and not r["pre"]
    if a in SPECIAL: return r["reply"] == SPECIAL[a] and not r["game"]
    if a == "sol_drive" and r["action"] == "sol_drive" and r["path"] == "model": return True   # goes to the GPS (stubbed), not run_action
    if any(g[0] == a and (o is None or g[1] == o) for g in r["game"]): return True       # a game action (refuel_from_can too)
    return a in commands and r["action"] == a and bool(r["pre"])


def answer_of(case):
    if case.get("steps"):
        return {"actions": [dict({"action": s["action"]}, **({"args": {"option": s["option"]}} if s.get("option") else {})) for s in case["steps"]], "speech": ""}
    d = {"action": case["action"], "speech": ""}
    if case.get("option"): d["args"] = {"option": case["option"]}
    return d


def main(args):
    cases = json.load(open(os.path.join(HERE, "s82_route_eval.json"), encoding="utf-8"))
    d = mind_dir(args)
    if "--live" in args:
        if "--yes-jamal-is-not-playing" not in args: sys.exit("live mode talks to the phone model: add --yes-jamal-is-not-playing if he is not playing")
        if "java.exe" in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower(): sys.exit("live mode refused: the game is running")
        res = H.run(d, [{"text": c["text"], "model": "live"} for c in cases])
        commands = set(res[0]["commands"]) if res else set()
        for c, r in zip(cases, res):
            ok = outcome_ok(c, r, commands)
            print("%s %-14s %-16s %-22s %s" % ("ok  " if ok else "MISS", "+".join(s["action"] for s in c["steps"]) if c.get("steps") else c["action"],
                                               "+".join(x[1] or "?" for x in r.get("seq") or []) if c.get("steps") else str(r["action"]), str(r["path"]), c["text"]))
            if not ok: FAIL.append(c["text"])
            if not ok or "--raw" in args: print("       model said: %s" % str(r.get("raw")).replace(chr(10), " ")[:200])
        print("live: %d/%d" % (len(cases) - len(FAIL), len(cases)))
        return
    print("Mind:", d)
    # 1. the recorded answer
    res = H.run(d, [{"text": c["text"], "model": answer_of(c)} for c in cases])
    commands = set(res[0]["commands"])
    for c, r in zip(cases, res):
        ck("recorded answer: '%s' -> %s %s" % (c["text"], c["action"], c.get("option") or ""), outcome_ok(c, r, commands), (r["path"], r["action"], r["game"], r["pre"], r["reply"]))
    # 2. the model says unknown
    res = H.run(d, [{"text": c["text"], "model": "unknown"} for c in cases])
    for c, r in zip(cases, res):
        if c["kind"] == "memory":
            ck("unknown -> the map answer: '%s'" % c["text"], r["path"] == "memory_after_unknown" and r["reply"] not in (None, "", ASK) and not r["game"], (r["path"], r["reply"]))
        else:
            ck("unknown -> no order runs: '%s'" % c["text"], not r["game"] and not r["pre"] and (r["reply"] == ASK or r["path"] == "memory_after_unknown"), (r["path"], r["game"], r["reply"]))
    # 3. every card example reaches its answer (s90: every bank example, on the card built for that line)
    got = H.run(d, [{"text": "x", "model": "unknown", "want_card": True}])[0]
    tiers = bool(got.get("tiers")) and bool(got.get("bank"))
    ex = {}
    for line in got["bank"]:                                               # s90: "his words -> answer", one phrase each
        said, _, answer = line.partition(" -> ")
        ex.setdefault(said, answer)
    ex = ex or H.examples(got["card"])
    ck("card: has examples%s" % (" (s90 bank)" if tiers else ""), len(ex) >= (100 if tiers else 30), len(ex))
    probes = list(ex)
    res = H.run(d, [{"text": t, "model": "card"} for t in probes])
    budget = got.get("budget") or 4600
    for t, r in zip(probes, res):
        if tiers: ck("card for '%s' within the budget (%d <= %d)" % (t, r["card_chars"], budget), r["card_chars"] <= budget)
        want = json.loads(ex[t])
        if want.get("actions"):
            steps = [{"action": s["action"], "option": (s.get("args") or {}).get("option")} for s in want["actions"]]
            ck("card example: '%s' -> %s" % (t, " then ".join(s["action"] for s in steps)), steps_ok(steps, r, commands), (r["path"], r["seq"], r["reply"]))
            continue
        a = want["action"]
        if a == "unknown": ok = r["reply"] == ASK and not r["game"]
        elif a == "none": ok = not r["game"] and not r["pre"]
        elif a == "address_book" and r["path"] is None and r["reply"] is None and not r["game"]: ok = True   # her own address words ran before the model
        else: ok = outcome_ok({"kind": "action", "action": a, "option": (want.get("args") or {}).get("option")}, r, commands)
        ck("card example: '%s' -> %s" % (t, a), ok, (r["path"], r["action"], r["game"], r["reply"]))
    # 4. s90: the newly shown actions, by a model that reads only this line's card; every line's card within the budget
    marked = [c for c in cases if c.get("mock") == "card"]
    if not tiers:
        print("     4. skipped: not a two-tier card (CARD_TIERS off or s90 not installed); %d marked cases" % len(marked))
        return
    res = H.run(d, [{"text": c["text"], "model": "card_near"} for c in cases])
    for c, r in zip(cases, res):
        ck("card for '%s' within the budget (%d <= %d)" % (c["text"], r["card_chars"], budget), r["card_chars"] <= budget)
    seen = set()
    for c, r in zip(cases, res):
        if c.get("mock") != "card": continue
        seen.add(c["action"])
        ck("this line's card, nearest example: '%s' -> %s %s" % (c["text"], c["action"], c.get("option") or ""), outcome_ok(c, r, commands),
           (r["path"], r["action"], r["game"], r["reply"]))
    near = sum(1 for c, r in zip(cases, res) if not c.get("mock") and outcome_ok(c, r, commands))
    print("     (info) the older cases by the same nearest-example mock: %d/%d" % (near, sum(1 for c in cases if not c.get("mock"))))


if __name__ == "__main__":
    main(sys.argv[1:])
    print("RESULT", "ALL PASS" if not FAIL else "%d FAILED" % len(FAIL))
    sys.exit(1 if FAIL else 0)

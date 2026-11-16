"""Gate: the model entry card (the sheet any connected model receives) is complete, honest, within budget and documented.

Jamal's standing rule: "لاتنسة تحدث بطاقة العقل دايما مع العقل" -- every Mind change updates the card in the same change.
There are two cards: the runtime one, built by model_router.sheet() (logged as "briefing sheet sent to the model, N chars"),
and the human one, DOCS/SOL_MODEL_CARD.md. This gate checks both against the Mind and the game's action catalog.

  (a) catalog: the game's own action list (SolActions_Snapshot.txt, what the Mind loads) plus every action a Lua file adds
      to U.actionCatalog behind a switch that is on in SolFixes_LAB.txt (e.g. horn_hold), all counted as available. The
      runtime card is built from that full catalog, with her hand off and on the horn.
  (b) every action the Mind can execute from the model's answer is on the card with at least one example:
      COMMANDS, CARD_ACTIONS, the ids chat_service's model branch handles itself (why, survey, cars_near, refuel_*),
      the catalog actions the card lists, and the switch-gated catalog actions.
  (c) nothing on the card (action list or example answers) without a Mind action or handler behind it.
  (d) the card without her memory is <= model_router.CARD_BUDGET (the one shared budget; test_s82_mind.py uses 4600 too).
  (e) DOCS/SOL_MODEL_CARD.md holds the generated section between <!-- CARD:BEGIN --> and <!-- CARD:END --> and it matches
      the card built now (--write-doc rewrites that section only).
  (f) test_s82_route_eval.py --as-is <mind> (offline replay, mocked model) passes.
  plus named feature checks (FAIL: must be on the card; WARN: reported, not refused).
  s90 two-tier card (model_router.CARD_TIERS on): tier 1 is the rules + one index line of every action name + memory, tier 2 the
  examples picked per message from model_router.example_bank(). Then: (b) every executable action is on the index and has >= 1
  bank example (every index action too); (b) every bank example is on the card built for its own words; (d) tier 1 + the
  examples <= CARD_BUDGET for every phrase in s82_route_eval.json and every bank phrase, her hand off and on the horn; (e) the
  doc shows tier 1, one per-message card and every action with its bank examples.

usage: card_check.py <sol_mind dir> [--lua <lua client dir>] [--lua-profile <Zomboid\\Lua dir>] [--fixes <SolFixes file>]
                     [--doc <SOL_MODEL_CARD.md>] [--write-doc] [--no-eval]
exit 0 = PASS, 1 = FAIL (every failure listed), 2 = usage / cannot load. Read-only except --write-doc (the doc section)."""
import copy, glob, inspect, json, os, re, subprocess, sys

if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.dont_write_bytecode = True                        # importing the Mind must not write into its folder
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LAB = os.path.join(ROOT, "07_TEST", "SOL_LAB")
DEF_LUA = os.path.join(LAB, "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
DEF_PROFILE = os.path.join(LAB, "profile", "Zomboid", "Lua")
DEF_DOC = os.path.join(ROOT, "DOCS", "SOL_MODEL_CARD.md")
EVAL = os.path.join(LAB, "_pending_refuel", "test_s82_route_eval.py")
BEGIN, END = "<!-- CARD:BEGIN -->", "<!-- CARD:END -->"
MEM = "ذاكرتك الآن:"
NL = "\n"
SPECIAL_SKIP = {"none", "unknown"}

FAIL, WARN = [], []
def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(detail)) if not ok and detail != "" else ""))
    if not ok: FAIL.append(name + ((" : " + str(detail)) if detail != "" else ""))
def warn(name, detail=""):
    print("WARN " + name + ((" : " + str(detail)) if detail != "" else ""))
    WARN.append(name + ((" : " + str(detail)) if detail != "" else ""))


def arg(args, flag, default=None):
    return args[args.index(flag) + 1] if flag in args and args.index(flag) + 1 < len(args) else default


# ---------------------------------------------------------------- (a) catalog
def read_fixes(path):
    out = {}
    try:
        for line in open(path, encoding="utf-8", errors="replace"):
            k, sep, v = line.strip().partition("=")
            if sep: out[k.strip()] = v.strip().lower() == "on"
    except OSError: pass
    return out


def lua_gated_actions(lua_dir, fixes):
    """Actions a Lua file appends inside its own U.actionCatalog wrapper: [(entry, file, switches, included)]."""
    found = []
    for f in sorted(glob.glob(os.path.join(lua_dir, "*.lua"))):
        src = open(f, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"U\.actionCatalog\s*=\s*function\s*\(\s*\)", src):
            indent = src.rfind(NL, 0, m.start()) + 1
            pad = src[indent:m.start()]
            end = src.find(NL + pad + "end", m.end())
            block = src[m.end():end if end > 0 else len(src)]
            switches = sorted(set(re.findall(r"""\bon\(\s*["']([a-z_0-9]+)["']\s*\)""", src)))
            on = (not switches) or any(fixes.get(s) for s in switches)
            for em in re.finditer(r"""\{\s*id\s*=\s*"([a-z_0-9]+)"(.*?)\}""", block, re.S):
                lab = re.search(r'label\s*=\s*"([^"]*)"', em.group(2))
                found.append(({"id": em.group(1), "kind": "sol", "label": lab.group(1) if lab else em.group(1), "enabled": True},
                              os.path.basename(f), switches, on))
    return found


def chat_handled_ids(CS):
    """Ids chat_service's model branch handles itself: `action == "x"` / `action in ("x", "y")`, any version of the route."""
    src = inspect.getsource(CS)
    ids = set(re.findall(r'\baction\s*==\s*"([a-z_0-9]+)"', src))
    for grp in re.findall(r'\baction\s+in\s+\(([^)]*)\)', src):
        ids |= set(re.findall(r'"([a-z_0-9]+)"', grp))
    return ids - SPECIAL_SKIP


# ---------------------------------------------------------------- card parsing
def parse_card(card):
    """(list: id -> (line, example or None), examples: action -> [phrases], example answers: [(phrases, json)])"""
    body = card.rsplit(NL + NL + MEM, 1)[0]
    head, _, shots = body.partition(NL + "أمثلة:" + NL)
    listed = {}
    in_list = False
    for line in head.split(NL):
        if line.strip() == "الأفعال:": in_list = True; continue
        if not in_list: continue
        m = re.match(r'^([a-z_0-9]+): (.*)$', line)
        if not m: continue
        ex = re.search(r' \| (?:مثال: )?"([^"]+)"', line)
        listed[m.group(1)] = (line, ex.group(1) if ex else None)
    examples, answers = {}, []
    for line in shots.split(NL):
        k = line.find(" -> {")
        if k <= 0: continue
        phrases = [p.strip() for p in line[:k].split(" / ") if p.strip()]
        am = re.search(r'"action":"([^"]+)"', line[k:])
        if not am: continue
        examples.setdefault(am.group(1), []).extend(phrases)
        answers.append((phrases, line[k + 4:]))
    return listed, examples, answers


def tiers_on(MR):
    return bool(getattr(MR, "CARD_TIERS", False)) and all(hasattr(MR, f) for f in ("example_bank", "index_ids", "index_line", "answer_actions_s90"))


def tier_parse(MR, catalog):
    """The two-tier card read like parse_card: (index: id -> (index line, first example), examples: action -> [phrases],
    answers: [([phrase], json)], bank: [(phrase, json)]), for the horn state MR.HORN_HELD is in now."""
    bank = MR.example_bank(catalog)
    line = MR.index_line(catalog)
    examples, answers = {}, []
    for said, ans in bank:
        for a in MR.answer_actions_s90(ans):
            if a: examples.setdefault(a, []).append(said)
        answers.append(([said], ans))
    listed = {i: (line, (examples.get(i) or [None])[0]) for i in MR.index_ids(catalog)}
    return listed, examples, answers, bank


def per_message(MR, catalog, said):
    """The card one message gets, built the way chat_service builds it: the session sheet (tier 1), then this line's examples."""
    return MR.add_examples(MR.sheet(catalog, ""), said, catalog)


def card_examples(card):
    """{phrase: answer} from the examples section of one built card."""
    out = {}
    body = card.rsplit(NL + NL + MEM, 1)[0].split(NL + "أمثلة:" + NL, 1)[-1]
    for line in body.split(NL):
        k = line.find(" -> {")
        if k <= 0: continue
        for said in line[:k].split(" / "): out.setdefault(said.strip(), line[k + 4:])
    return out


def eval_phrases():
    try: return [c["text"] for c in json.load(open(os.path.join(os.path.dirname(EVAL), "s82_route_eval.json"), encoding="utf-8"))]
    except (OSError, ValueError, KeyError, TypeError): return []


def build_tier_doc_section(MR, card, sample, sample_said, size, max_size, budget, catalog, gated, listed, examples, hidden):
    rows = []
    for aid in MR.index_ids(catalog):
        if aid in MR.COMMANDS: where = "COMMANDS"
        elif aid in MR.CARD_ACTIONS: where = "CARD_ACTIONS"
        elif aid in {e["id"] for e, *_ in gated}: where = "game (switch)"
        else: where = "game"
        rows.append("| `%s` | %s | %s |" % (aid, where, " / ".join(dict.fromkeys(examples.get(aid, []))) or "-"))
    for aid in ("none", "unknown"):
        if examples.get(aid): rows.append("| `%s` | card rule | %s |" % (aid, " / ".join(dict.fromkeys(examples[aid]))))
    out = [BEGIN,
           "<!-- generated by 05_TOOLS/sol_kahlua/card_check.py --write-doc from the live Mind and the full game catalog; do not edit by hand -->",
           "",
           "### البطاقة كما تُرسل الآن / The card as sent now (two tiers, s90)",
           "",
           "Tier 1 (every message, cached per session): %d chars without memory. Tier 1 + the examples picked for one message: at most %d chars "
           "over the eval phrases and every bank phrase (hand on the horn or not); budget `model_router.CARD_BUDGET` = %d. "
           "Per message: the %d example lines most like his words (`model_router.TOP_K_S90`), the best several-orders example, and \"بس\" "
           "with its rule while her hand is on the horn. Catalog: %d game actions, all counted as available%s." % (
               size, max_size, budget, getattr(MR, "TOP_K_S90", 0), len(catalog),
               (", plus switch-gated: " + ", ".join(sorted({e["id"] for e, f, s, on in gated if on}))) if any(on for *_, on in gated) else ""),
           "",
           "#### Tier 1",
           "",
           "```",
           card.rsplit(NL + NL + MEM, 1)[0],
           "",
           MEM,
           "(her memory: home, garden, cars, places she knows, her address book; built per session by chat_service._memory_text)",
           "```",
           "",
           "#### Tier 2 for one message: \"%s\"" % sample_said,
           "",
           "```",
           sample.rsplit(NL + NL + MEM, 1)[0].split(NL + "أمثلة:" + NL, 1)[-1],
           "```",
           "",
           "### كل أفعال البطاقة وأمثلتها / Every action on the index and its examples in the bank",
           "",
           "| action | from | example(s) in the bank |",
           "|---|---|---|"] + rows
    if hidden:
        out += ["", "Game actions the Mind would run if named but the card does not show (not reachable by the model): " + ", ".join("`%s`" % h for h in sorted(hidden)) + "."]
    out += [END]
    return NL.join(out)


def build_doc_section(MR, card, held_card, size, held_size, budget, catalog, gated, listed, examples, executable, hidden):
    rows = []
    for aid in sorted(set(listed) | set(examples)):
        if aid in SPECIAL_SKIP: continue
        if aid in MR.COMMANDS: where = "COMMANDS"
        elif aid in MR.CARD_ACTIONS: where = "CARD_ACTIONS"
        elif aid in {e["id"] for e, *_ in gated}: where = "game (switch)"
        else: where = "game"
        ex = [x for x in ([listed.get(aid, (None, None))[1]] + examples.get(aid, [])) if x]
        rows.append("| `%s` | %s | %s |" % (aid, where, " / ".join(dict.fromkeys(ex)) or "-"))
    out = [BEGIN,
           "<!-- generated by 05_TOOLS/sol_kahlua/card_check.py --write-doc from the live Mind and the full game catalog; do not edit by hand -->",
           "",
           "### البطاقة كما تُرسل الآن / The card as sent now",
           "",
           "Size without memory: %d chars (hand on the horn: %d), budget `model_router.CARD_BUDGET` = %d. Catalog: %d game actions, all counted as available%s." % (
               size, held_size, budget, len(catalog), (", plus switch-gated: " + ", ".join(sorted({e["id"] for e, f, s, on in gated if on}))) if any(on for *_, on in gated) else ""),
           "",
           "```",
           card.rsplit(NL + NL + MEM, 1)[0],
           "",
           MEM,
           "(her memory: home, garden, cars, places she knows; built per session by chat_service._memory_text)",
           "```",
           "",
           "### كل أفعال البطاقة / Every action on the card",
           "",
           "| action | from | example(s) on the card |",
           "|---|---|---|"] + rows
    if hidden:
        out += ["", "Game actions the Mind would run if named but the card does not show (not reachable by the model): " + ", ".join("`%s`" % h for h in sorted(hidden)) + "."]
    out += [END]
    return NL.join(out)


def main(args):
    rest = [a for a in args if not a.startswith("--") and a not in {arg(args, f) for f in ("--lua", "--lua-profile", "--fixes", "--doc")}]
    if not rest: print(__doc__); return 2
    mind = os.path.abspath(rest[0])
    lua_dir = os.path.abspath(arg(args, "--lua", DEF_LUA))
    profile = os.path.abspath(arg(args, "--lua-profile", DEF_PROFILE))
    fixes_path = os.path.abspath(arg(args, "--fixes", os.path.join(profile, "SolFixes_LAB.txt")))
    doc = os.path.abspath(arg(args, "--doc", DEF_DOC))
    if not os.path.isfile(os.path.join(mind, "model_router.py")): print("no model_router.py in", mind); return 2
    sys.path.insert(0, mind)
    try:
        import model_router as MR
        import chat_service as CS
    except Exception as e:
        print("FAIL cannot import the Mind from %s: %r" % (mind, e)); return 2
    print("Mind:", mind)

    # (a) the full catalog
    snap = CS.load_actions(profile)
    ck("(a) the game's action catalog is readable (%s)" % os.path.join(profile, CS.ACT_SNAP), len(snap) > 0, "empty or missing")
    fixes = read_fixes(fixes_path)
    ck("(a) switches readable (%s)" % fixes_path, len(fixes) > 0, "empty or missing")
    gated = lua_gated_actions(lua_dir, fixes)
    catalog = [dict(copy.deepcopy(a), enabled=True) for a in snap if isinstance(a, dict) and a.get("id")]
    have = {a["id"] for a in catalog}
    for e, f, sw, on in gated:
        print("     Lua %s adds %s to the catalog behind %s -> %s%s" % (f, e["id"], "/".join(sw) or "no switch", "on" if on else "off",
                                                                      "" if on and e["id"] not in have else (" (already in the snapshot)" if e["id"] in have else "")))
        if on and e["id"] not in have:
            catalog.append(dict(e)); have.add(e["id"])
    ids = {a["id"] for a in catalog}
    gated_on = {e["id"] for e, f, sw, on in gated if on}

    tiers = tiers_on(MR)
    held0 = getattr(MR, "HORN_HELD", False)
    try:
        MR.HORN_HELD = False
        card = MR.sheet(catalog, "")
        if tiers: listed, examples, answers, bank = tier_parse(MR, catalog)
        MR.HORN_HELD = True
        held_card = MR.sheet(catalog, "")
        if tiers: _, held_examples, _, held_bank = tier_parse(MR, catalog)
        MR.HORN_HELD = False
        live_card = MR.sheet(snap, "")
    finally:
        MR.HORN_HELD = held0
    if not tiers:
        listed, examples, answers = parse_card(card)
        _, held_examples, _ = parse_card(held_card)
    print("     card%s: %d %s actions, %d example answers, catalog %d (%d from switches)" % (
        " (two tiers: index + per-message examples)" if tiers else "", len(listed), "indexed" if tiers else "listed", len(answers), len(ids), len(gated_on - {a.get('id') for a in snap})))

    # (b) everything the Mind can execute is on the card with an example
    handled = chat_handled_ids(CS)
    executable = {}
    for k in MR.COMMANDS: executable.setdefault(k, "COMMANDS")
    for k in MR.CARD_ACTIONS:
        if k in ids: executable.setdefault(k, "CARD_ACTIONS")
    for k in handled:
        if k in MR.COMMANDS or k in ids: executable.setdefault(k, "chat_service model branch")
    for k in listed:
        if k in ids: executable.setdefault(k, "game catalog, listed on the card")
    for k in gated_on: executable.setdefault(k, "game catalog, switch-gated")
    if tiers:
        for k in ids: executable.setdefault(k, "game catalog")
    for aid in sorted(executable):
        if tiers:
            ck("(b) %s [%s] on the index line with >= 1 bank example" % (aid, executable[aid]), aid in listed and bool(examples.get(aid)),
               "not on the index" if aid not in listed else "on the index, but no example in the bank (EXAMPLE_BANK_S90)")
            continue
        on_card = aid in listed or aid in examples
        has_ex = bool((listed.get(aid) or (None, None))[1]) or bool(examples.get(aid))
        ck("(b) %s [%s] on the card with an example" % (aid, executable[aid]), on_card and has_ex,
           "not on the card" if not on_card else "listed, but no example (no | \"...\" on its line, no example line)")
    if tiers:
        for aid in listed:
            if aid not in executable: ck("(b) index action %s has >= 1 bank example" % aid, bool(examples.get(aid)))
    hidden = sorted(i for i in ids if i not in listed and i not in examples and (tiers or i not in executable))
    if hidden: (ck if tiers else warn)("(b) game actions the Mind runs if named but the card never shows the model (%d)" % len(hidden), ", ".join(hidden))
    elif tiers: ck("(b) every game action in the catalog is on the index (%d)" % len(ids), True)
    phrase_cards = {}                                                   # (said, held) -> the card that message gets
    if tiers:
        held0 = getattr(MR, "HORN_HELD", False)
        try:
            for held, bk in ((False, bank), (True, held_bank)):
                MR.HORN_HELD = held
                for said in dict.fromkeys([p for p, _ in bk] + eval_phrases()):
                    phrase_cards[(said, held)] = per_message(MR, catalog, said)
        finally:
            MR.HORN_HELD = held0
        for held, bk in ((False, bank), (True, held_bank)):
            missed = [p for p, ans in bk if card_examples(phrase_cards[(p, held)]).get(p) != ans]
            ck("(b) every bank example is on the card built for its own words (%d, hand %s the horn)" % (len(bk), "on" if held else "off"),
               not missed, "; ".join(missed[:12]))

    # (c) nothing on the card without a Mind action / handler
    for aid in sorted(set(listed) | set(examples) | (set(held_examples) if tiers else set())):
        if aid in SPECIAL_SKIP: continue
        ck("(c) card entry %s has a Mind action behind it" % aid, aid in MR.COMMANDS or aid in ids,
           "not in COMMANDS and not in the game catalog: the Mind answers 'not_an_action'")
    for cid, (meaning, phrase) in MR.COMMANDS.items():
        if phrase is None:
            ck("(c) COMMANDS %s (no phrase) has its own branch in chat_service" % cid, cid in handled, "the Mind would route it to an empty phrase")
    for cid in MR.CARD_ACTIONS:
        ck("(c) CARD_ACTIONS %s exists in the game catalog" % cid, cid in ids, "listed when the card has no catalog, refused by the Mind")
    for name in ("EXTRA_EXAMPLE", "ARGS_NOTE"):
        for k in getattr(MR, name, {}):
            ck("(c) %s[%s] belongs to an action" % (name, k), k in MR.COMMANDS or k in ids or k in MR.CARD_ACTIONS)
    dup = set(MR.COMMANDS) & set(MR.CARD_ACTIONS)
    ck("(c) COMMANDS and CARD_ACTIONS do not overlap", not dup, sorted(dup))

    # (d) budget
    budget = getattr(MR, "CARD_BUDGET", None)
    ck("(d) model_router.CARD_BUDGET is defined (the one shared budget)", isinstance(budget, int) and budget > 0, budget)
    strip = lambda t: len(t.rsplit(NL + NL + MEM, 1)[0])
    size, held_size, live_size = strip(card), strip(held_card), strip(live_card)
    print("     card size without memory: full catalog %d, hand on the horn %d, the lab's catalog as written now %d; budget %s" % (size, held_size, live_size, budget))
    if isinstance(budget, int):
        ck("(d) full-catalog card %d <= %d%s" % (size, budget, " (tier 1)" if tiers else ""), size <= budget, size - budget)
        ck("(d) full-catalog card with her hand on the horn %d <= %d%s" % (held_size, budget, " (tier 1)" if tiers else ""), held_size <= budget, held_size - budget)
    max_size, max_said = max(size, held_size), ""
    if tiers:
        sizes = {k: strip(v) for k, v in phrase_cards.items()}
        (max_said, _), max_size = max(sizes.items(), key=lambda kv: kv[1])
        over = sorted(("%s%s %d" % (s, " (horn held)" if h else "", n) for (s, h), n in sizes.items() if isinstance(budget, int) and n > budget))
        print("     two-tier card: tier 1 %d (hand on the horn %d), tier 1 + this message's examples at most %d ('%s') over %d messages" % (
            size, held_size, max_size, max_said, len(sizes)))
        ck("(d) tier 1 + per-message examples <= %s for every eval and bank phrase (max %d)" % (budget, max_size), not over, "; ".join(over[:12]))

    # named features (what recent stages put on the card, and what is known to be missing)
    def ex_for(action, *words, option=None):
        return [p for (ps, ans) in answers for p in ps if '"action":"%s"' % action in ans and (option is None or '"option":"%s"' % option in ans)
                and all(w in p for w in words)]
    ck("feature horn_hold start example", bool(ex_for("horn_hold", option="start")), "no horn_hold start line on the full-catalog card")
    ck("feature horn_hold stop example", bool(ex_for("horn_hold", option="stop")), "no horn_hold stop line on the full-catalog card")
    ck("feature 'بس' stops the horn only while held", "بس" in held_examples.get("horn_hold", []) and "بس" not in examples.get("horn_hold", []))
    if tiers:
        hc = phrase_cards.get(("بس", True)) or ""
        ck("feature tier 2: hand on the horn, 'بس' gets the stop example and its rule", card_examples(hc).get("بس", "").find('"stop"') > 0 and getattr(MR, "HORN_RULE_S90", "#") in hc)
        nomulti = [s for (s, h), c in phrase_cards.items() if '{"actions":' not in c.rsplit(NL + NL + MEM, 1)[0]]
        ck("feature tier 2: every message's card has a several-orders example", not nomulti, "; ".join(nomulti[:8]))
        ck("feature tier 1: the index is one line", "\n" not in MR.index_line(catalog) and MR.index_line(catalog) in card)
    ck("feature engine word متور -> sol_engine", bool(ex_for("sol_engine", "متور")))
    ck("feature engine word موتور -> sol_engine", bool(ex_for("sol_engine", "موتور")))
    ck("feature street question -> none", bool(ex_for("none", "شارع")))
    ck("feature town question -> none", bool(ex_for("none", "مدينة")) or bool(ex_for("none", "ضيعة")))
    ck("feature 'هاتي السيارة وتعي لعندي' -> come_car", "هاتي السيارة وتعي لعندي" in examples.get("come_car", []))
    cn = (listed.get("cars_near") or ("", None))[0] + " " + " ".join(examples.get("cars_near", []))
    if not re.search(r"(?:لما|وهي|حتى لو|ولو)\s+(?:تكون\s+)?بعيدة|بعيدة عن(?:و|ه|ك)|بغيابك|\baway\b", cn):     # "قديش بعيدة" is a distance, not her being away
        warn("feature cars_near when she is away", "the card's cars_near line and examples never say it also answers while she is far from him: " + cn.strip()[:160])
    memsrc = inspect.getsource(CS.Chat._memory_text)
    if not re.search(r"far_report|far_work|sol_far|غيابك|بغيابك", memsrc):
        warn("feature far_work return report in her memory", "chat_service.Chat._memory_text has no line for what she did while he was away (farm_talk.far_report_line is spoken as a notice only); asked 'شو عملتي بغيابي' the model has nothing on the card")
    if not re.search(r"address|sol_address|عناوين", memsrc):
        warn("feature address-book places in her memory", "the memory section lists mem.data['places'] only; the address book (game side, sol_address) is never on the card, so 'none' answers about its places have nothing to read")

    # (e) the doc
    if tiers:
        sample_said = "سول طفي الغاز وتعي ورايي"
        held0 = getattr(MR, "HORN_HELD", False)
        try:
            MR.HORN_HELD = False
            sample = per_message(MR, catalog, sample_said)
        finally:
            MR.HORN_HELD = held0
        section = build_tier_doc_section(MR, card, sample, sample_said, size, max_size, budget or 0, catalog, gated, listed, examples, hidden)
    else:
        section = build_doc_section(MR, card, held_card, size, held_size, budget or 0, catalog, gated, listed, examples, executable, hidden)
    try: text = open(doc, encoding="utf-8").read()
    except OSError: text = None
    if "--write-doc" in args and text is not None:
        if BEGIN in text and END in text:
            new = text[:text.index(BEGIN)] + section + text[text.index(END) + len(END):]
        else:
            new = text.rstrip() + NL + NL + section + NL
        if new != text:
            open(doc, "w", encoding="utf-8", newline="\n").write(new)
            print("     wrote the generated section of", doc)
        text = new
    ck("(e) %s exists" % doc, text is not None)
    if text is not None:
        ok = BEGIN in text and END in text
        ck("(e) the doc has the generated section markers", ok, "%s ... %s missing" % (BEGIN, END))
        if ok:
            cur = text[text.index(BEGIN):text.index(END) + len(END)].replace("\r\n", NL)
            ck("(e) the doc's card section matches the card built now", cur == section, "run: card_check.py <mind> --write-doc")
            for aid in sorted(set(listed) | set(examples)):
                if aid not in SPECIAL_SKIP and "`%s`" % aid not in cur: ck("(e) the doc lists %s" % aid, False)

    # (f) the offline route replay
    if "--no-eval" in args:
        print("     (f) route eval skipped (--no-eval)")
    elif not os.path.isfile(EVAL):
        ck("(f) %s exists" % EVAL, False)
    else:
        r = subprocess.run([sys.executable, EVAL, "--as-is", mind], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"), cwd=os.path.dirname(EVAL))
        lines = (r.stdout or "").strip().splitlines()
        bad = [l for l in lines if l.startswith("FAIL ")]
        ck("(f) test_s82_route_eval.py --as-is passes (%s)" % (lines[-1] if lines else "no output"), r.returncode == 0,
           "; ".join(bad[:12]) or (r.stderr or "")[-600:])

    print("")
    if WARN: print("WARNINGS (%d, not refused):" % len(WARN)); [print("  - " + w) for w in WARN]
    if FAIL: print("FAILURES (%d):" % len(FAIL)); [print("  - " + f) for f in FAIL]
    print("CARD_CHECK: %s (%d failed, %d warnings; card %d/%s chars)" % ("PASS" if not FAIL else "FAIL", len(FAIL), len(WARN), max_size, budget))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

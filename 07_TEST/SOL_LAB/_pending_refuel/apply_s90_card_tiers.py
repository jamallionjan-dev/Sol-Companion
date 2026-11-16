"""s90 Mind: the card in two tiers (Jamal 2026-11-10: every Mind action on the card with an example, "by name only" is not enough).

Tier 1, every message (cached per session as before): who she is, the rules, ONE line with every action name the Mind can run
  (COMMANDS, every enabled game action in the catalog incl. the ones the old card never showed, CARD_ACTIONS), an option hint
  next to the ones that take one ("sol_engine(on|off)"), and her memory exactly as before.
Tier 2, per message: an example bank (>= 1 natural Levantine example for every action: the old card's examples and list
  phrases, plus EXAMPLES_S90 for the 38 actions the old card hid; later stages may append lines to EXAMPLE_BANK_S90), and for each line he types the TOP_K_S90 examples most
  like his words (cheap fuzzy similarity: Arabic letters normalised (alef / ya / ta marbuta / hamza seats, no tashkeel),
  light prefixes / suffixes off, char 3-grams + word overlap) appended under "أمثلة:". Always added: the best
  several-orders example ("actions" in order), two when his line looks like two orders, and while her hand is on the horn the
  "بس" stop example with its one-line rule. The model still decides from the whole index; this only picks which examples it
  sees (model first, examples only, no routing). tier1 + examples <= CARD_BUDGET for every message (trimmed from the bottom).
CARD_TIERS = False in model_router.py gives the old one-tier card back (needs a Mind restart).

Blocks appended at the end of model_router.py and chat_service.py (redefinitions, outermost wrapper); needs s85 installed.
Built on whatever the card is when installed (s86 address-book memory, s87 examples): the bank is read from the old card itself.
Mind only; needs a Mind restart. In place, idempotent. Afterwards: card_check.py <mind> --write-doc.
usage: apply_s90_card_tiers.py <sol_mind dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)
MARK = "# ---------------------------------------------------------------- s90 card tiers: index + per-message examples"
NEED = "# ---------------------------------------------------------------- s85 card budget, two orders in one line, exit first, far report"


def append(path, block):
    t = open(path, encoding="utf-8", newline="").read()
    if MARK in t: return "kept"
    assert NEED in t, "s85 is not installed in " + path
    nl = CRLF if CRLF in t else NL
    sep = "" if t.endswith(nl) else nl
    open(path, "w", encoding="utf-8", newline="").write(t + sep + nl + nl + (MARK + NL + block).replace(NL, nl))
    return "appended"


MR = r'''# Tier 1 (every message): rules, one line with every action name, her memory. Tier 2 (per message): the examples most like
# his words, from a bank with at least one example for every action. The model decides; retrieval only picks examples.
CARD_TIERS = True                                                             # False: the old one-tier card (Mind restart)
TOP_K_S90 = 12                                                                # example lines per message (the budget trims)
PHRASES_PER_LINE_S90 = 2
INDEX_HEAD_S90 = "الأفعال (المعرف حرفيًا؛ (on|off) يعني option):"
OPTION_RULE_S90 = '- option: بس للأفعال اللي جنبها (...) بالقائمة: "args":{"option":"..."}، متل الأمثلة.'
EXAMPLES_RULE_S90 = "- الأمثلة تحت هي الأقرب لكلامه، مو كل شي: إذا ولا وحدة قصدو، اختاري من القائمة."
HORN_RULE_S90 = 'إيدك عالزمور هلأ: "بس" لحالها يعني شيلي إيدك عنه.'
OPTION_HINT_S90 = {"sol_give": "water|food|all|mine", "sol_fetch": "book|food|water", "sol_cook": "egg", "sol_cook_and_serve": "egg",
                   "sol_equip_best": "melee|gun", "sol_goto": "home|مكان", "sol_go_inside": "home", "sol_drive": "مكان",
                   "sol_take_pill": "اسم الحبوب"}
# >= 1 example for each action the old card never showed (and a few more for the ones it did): (his words, action, option)
EXAMPLES_S90 = (
    ("اركبي بأي كرسي فاضي بالسيارة", "board_vehicle", None), ("طلعي عالسيارة وين ما في محل", "board_vehicle", None),
    ("فلي من السيارة هلأ", "exit_vehicle", None),
    ("احملي زيادة عادي لو تقلتي", "set_allow_overload", "on"), ("لا تحملي فوق طاقتك", "set_allow_overload", "off"),
    ("انتشروا وانتو ماشيين ورايي", "set_follow_fan_out", "on"), ("لا تنتشروا، امشوا ورايي سوا", "set_follow_fan_out", "off"),
    ("لا تطخي", "set_hold_fire", "on"), ("وقفي طخ هلأ", "set_hold_fire", "on"), ("رجعي طخي عادي", "set_hold_fire", "off"),
    ("اركبي معي كل ما يكون في مقعد", "set_ride_with_player", "on"), ("لا تركبي معي بالسيارة بعد هيك", "set_ride_with_player", "off"),
    ("فتشي عالأغراض لما يكون الوضع أمان", "set_scavenge", "on"), ("بطلي تفتشي عالأغراض", "set_scavenge", "off"),
    ("اضربي هالزومبي القريب", "sol_attack_nearest", None), ("قوصي عالزومبي اللي جنبك", "sol_attack_nearest", None),
    ("ضمديلي جرحي", "sol_bandage_player", None), ("لفيلي إيدي بشاش", "sol_bandage_player", None),
    ("استنيني بالسيارة", "sol_car_wait", None), ("ضلي قاعدة بالسيارة لحتى إرجع", "sol_car_wait", None),
    ("سكري الباب", "sol_close_door", None),
    ("اطبخي بيض", "sol_cook", "egg"), ("اطبخي شي ناكلو", "sol_cook", None),
    ("اطبخيلي شي وجيبيلي ياه", "sol_cook_and_serve", None), ("اطبخيلي بيض وطعميني", "sol_cook_and_serve", "egg"),
    ("اشربي مي", "sol_drink", None), ("انتي عطشانة؟ اشربي", "sol_drink", None),
    ("سوقينا عالمستشفى", "sol_drive", "المستشفى"), ("سوقي لعند الصيدلية", "sol_drive", "الصيدلية"),
    ("كلي شي", "sol_eat", None), ("انتي جوعانة؟ كلي", "sol_eat", None),
    ("مسكي أحسن سلاح عندك", "sol_equip_best", None), ("طلعي البارودة", "sol_equip_best", "gun"), ("مسكي سكينة أو عصاية", "sol_equip_best", "melee"),
    ("جيبيلي كتاب من الخزانة", "sol_fetch", "book"), ("جيبيلي شي آكلو من البراد", "sol_fetch", "food"),
    ("عبي القنينة مي", "sol_fill_water", None), ("املي المطرة من الحنفية", "sol_fill_water", None),
    ("شغلي مضخة البنزين", "sol_fuel", None),
    ("عطيني مي", "sol_give", "water"), ("عطيني أكل من شنتتك", "sol_give", "food"), ("رجعيلي غراضي", "sol_give", "mine"),
    ("عطيني كلشي معك", "sol_give", "all"),
    ("فوتي لجوا", "sol_go_inside", None), ("ادخلي عالبيت من البرد", "sol_go_inside", "home"),
    ("امشي لعند البيت", "sol_goto", "home"),
    ("امسحي الوجهة من الجي بي اس", "sol_gps_clear", None), ("شيلي العنوان من الجي بي اس", "sol_gps_clear", None),
    ("افتحي الباب", "sol_open_door", None),
    ("افتحي الشباك", "sol_open_window", None), ("سكري الشباك", "sol_open_window", None),
    ("الغي الخطة اللي عم تعمليها", "sol_plan_cancel", None), ("خلص بطلي الطبخة", "sol_plan_cancel", None),
    ("وين وصلتي بالطبخة؟", "sol_plan_status", None), ("شو صار بالخطة", "sol_plan_status", None),
    ("اقري كتاب", "sol_read", None), ("اقري شي مجلة", "sol_read", None),
    ("بدلي المخزن", "sol_reload", None), ("عبي الفرد فشك", "sol_reload", None),
    ("غيري الشاش الوسخ", "sol_replace_bandage", None), ("بدلي ضمادتك", "sol_replace_bandage", None),
    ("تمددي عالتخت شوي", "sol_rest", None), ("قعدي ريحي شوي", "sol_rest", None),
    ("قعدي جنبي قدام", "sol_sit_beside", None),
    ("طفي الغاز", "sol_stove_off", None), ("ولعي الغاز", "sol_stove_on", None), ("شغلي الفرن", "sol_stove_on", None),
    ("خدي حبة مسكن", "sol_take_pill", None), ("خدي دوا للوجع", "sol_take_pill", None),
    ("قعدي ورا الدركسيون", "sol_take_wheel", None), ("استلمي السواقة بس لا تمشي", "sol_take_wheel", None),
    ("اغسلي حالك", "sol_wash", None), ("روحي تغسلي", "sol_wash", None),
    ("ضوي الضو", "sol_toggle_light", None), ("طفي ضو البيت", "sol_toggle_light", None),
    ("زمري مرة", "sol_horn", "once"),
    ("صفيها بأقرب مكان فاضي", "park", None),                          # s87 smart_park: the garage or the nearest free spot
    ("اركبي السيارة", "board_car", None), ("سوقي للمكان المحدد عالخريطة", "drive_marker", None),
    ("شو في سيارات حواليكي ولو بعيدة عني", "cars_near", None),
    ("كيفك اليوم", "none", None), ("شكرًا حبيبتي", "none", None), ("شو رأيك بهالمكان", "none", None),
)
COMPOUNDS_S90 = (
    ("طفي الضو ونزلي من السيارة", (("sol_headlights", "off"), ("exit_car", None))),
    ("سكري الباب وتعي ورايي", (("sol_close_door", None), ("follow", None))),
)
COMPOUND_CUE_S90 = ("وبعدين", "بعدين", "بعدها", "وبعدها", "ثم", "وبعد")
_sheet_pre_s90 = sheet
_TASHKEEL_S90 = re.compile("[\u064B-\u065F\u0670\u0640]")
_AR_S90 = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})
_STOP_S90 = {"سول", "لو", "سمحتي", "زكاتك", "بليز", "يلا", "طيب", "خلص", "يا", "هلا", "هلق"}
_PRE_S90 = ("وال", "بال", "فال", "عال", "لل", "ال", "و", "ف", "ب", "ا")             # "ا": اركبي / ركبي, اطبخي / طبخي
_SUF_S90 = ("يلي", "يها", "كي", "ها", "ك", "ي", "ه")


def norm_s90(s):
    """His words for comparing: no tashkeel, one alef, ya / ta marbuta / hamza seats folded, no punctuation."""
    s = _TASHKEEL_S90.sub("", str(s or "")).translate(_AR_S90).lower()
    return " ".join(re.sub(r"[^\w\s]|_", " ", s).split())


def _stem_s90(w):
    for p in _PRE_S90:
        if w.startswith(p) and len(w) - len(p) >= 3: w = w[len(p):]; break
    for x in _SUF_S90:
        if w.endswith(x) and len(w) - len(x) >= 3: w = w[:-len(x)]; break
    return w


def _feats_s90(s):
    words = [w for w in norm_s90(s).split() if w not in _STOP_S90]
    toks = {_stem_s90(w) for w in words}
    flat = " " + " ".join(words) + " "
    grams = {}
    for i in range(len(flat) - 2):
        g = flat[i:i + 3]
        grams[g] = grams.get(g, 0) + 1
    return toks, grams


def similarity_s90(a, b):
    """0..1: word overlap (Dice, light stems) and char 3-gram cosine. Cheap, no model."""
    ta, ga = a if isinstance(a, tuple) else _feats_s90(a)
    tb, gb = b if isinstance(b, tuple) else _feats_s90(b)
    dice = 2.0 * len(ta & tb) / (len(ta) + len(tb)) if ta and tb else 0.0
    dot = sum(v * gb.get(k, 0) for k, v in ga.items())
    na = sum(v * v for v in ga.values()) ** 0.5
    nb = sum(v * v for v in gb.values()) ** 0.5
    cos = dot / (na * nb) if na and nb else 0.0
    return 0.55 * dice + 0.45 * cos


def _shot_s90(said, steps):
    """One example answer line: his words -> the compact answer (no speech, as on the card)."""
    def one(a, o): return {"action": a, "args": {"option": o}} if o else {"action": a}
    d = one(*steps[0]) if len(steps) == 1 else {"actions": [one(a, o) for a, o in steps]}
    return said, json.dumps(d, ensure_ascii=False, separators=(",", ":"))


def answer_actions_s90(answer):
    try: d = json.loads(answer)
    except ValueError: return []
    if not isinstance(d, dict): return []
    if isinstance(d.get("actions"), list): return [x.get("action") for x in d["actions"] if isinstance(x, dict)]
    return [d.get("action")]


# The bank as card lines ("a / b -> {json}"), a list: a later stage adds its examples here (s91 looks for a list named *BANK*).
EXAMPLE_BANK_S90 = ["%s -> %s" % _shot_s90(said, [(a, o)]) for said, a, o in EXAMPLES_S90] + ["%s -> %s" % _shot_s90(said, list(steps)) for said, steps in COMPOUNDS_S90]


def index_ids(actions):
    """Every action the Mind can run from the model's answer, in card order: COMMANDS, the game's enabled actions, CARD_ACTIONS."""
    out = list(COMMANDS)
    if actions:
        out += [a["id"] for a in actions if a.get("id") and a.get("enabled", True) and a["id"] not in COMMANDS]
    else:
        out += [k for k in CARD_ACTIONS if k not in COMMANDS]
    return list(dict.fromkeys(out))


def _option_hint_s90(aid, actions):
    if aid in OPTION_HINT_S90: return OPTION_HINT_S90[aid]
    if aid in CARD_ACTIONS and CARD_ACTIONS[aid][2]:
        words = re.findall(r"\b[a-z]+\b", CARD_ACTIONS[aid][2].replace("option", ""))
        if words: return "|".join(words)
    kind = next((a.get("kind") for a in actions or [] if a.get("id") == aid), None)
    return "on|off" if kind == "tick" else None


def index_line(actions):
    return ", ".join(i + ("(%s)" % h if h else "") for i in index_ids(actions) for h in [_option_hint_s90(i, actions)])


def _split_s90(text):
    """The old card in parts: (head before the action list, list lines, example lines, other lines in the examples, tail from the memory)."""
    n = chr(10)
    mem = n + n + "ذاكرتك الآن:"
    body, msep, mtail = text.rpartition(mem)
    if not msep: body, mtail = text, None
    head, lsep, rest = body.partition(n + "الأفعال:" + n)
    if not lsep: return body, [], [], [], (msep + mtail if msep else "")
    lst, esep, exs = rest.partition(n + n + "أمثلة:" + n)
    shots, notes = [], []
    for line in (exs.split(n) if esep else []):
        if " -> {" in line: shots.append(line)
        elif line.strip(): notes.append(line)
    return head, [l for l in lst.split(n) if l.strip()], shots, notes, (msep + mtail if msep else "")


def example_bank(actions):
    """[(his words, answer json)]: the old card's examples and list phrases, then EXAMPLE_BANK_S90; only answers whose
    actions are all on the index (none / unknown always). One answer per phrase (the first)."""
    ids = set(index_ids(actions)) | {"none", "unknown"}
    _, lst, shots, _, _ = _split_s90(_sheet_pre_s90(actions, ""))
    out, seen = [], set()
    def add(said, answer):
        said = said.strip()
        if not said or said in seen: return
        acts = answer_actions_s90(answer)
        if not acts or not all(a in ids for a in acts): return
        seen.add(said); out.append((said, answer))
    for line in shots:
        k = line.find(" -> {")
        for said in line[:k].split(" / "): add(said, line[k + 4:])
    for line in lst:
        m = re.match(r'^([a-z_0-9]+): .*?\| (?:مثال: )?"([^"]+)"', line)
        if not m: continue
        opt = re.search(r"option: ([a-z]+)", line)
        add(m.group(2), _shot_s90(m.group(2), [(m.group(1), opt.group(1) if opt else None)])[1])
    for line in EXAMPLE_BANK_S90:
        k = line.find(" -> {")
        if k > 0:
            for said in line[:k].split(" / "): add(said, line[k + 4:])
    return out


def tier1(actions, memory):
    """The card every message gets: the old head with the option rule for the index, one index line, her memory."""
    n = chr(10)
    head, _, _, notes, tail = _split_s90(_sheet_pre_s90(actions, memory))
    rules = head.split(n)
    for i, line in enumerate(rules):
        if line.startswith("- option:"): rules[i] = OPTION_RULE_S90
    if EXAMPLES_RULE_S90 not in rules:
        last = max([i for i, l in enumerate(rules) if l.startswith("- ")] or [len(rules) - 1])
        rules.insert(last + 1, EXAMPLES_RULE_S90)
    text = n.join(rules) + n + INDEX_HEAD_S90 + n + index_line(actions) + n + n + "أمثلة:" + n.join([""] + notes)
    return text + (tail or n + n + "ذاكرتك الآن:" + n + str(memory or "لا شيء بعد."))


def pick_examples(said, actions, k=None):
    """The example lines for this message, best first: the TOP_K_S90 answers most like his words (up to two phrases each),
    the best several-orders example (two when his line looks like two orders), and "بس" with its rule while she holds the horn."""
    k = TOP_K_S90 if k is None else k
    bank = example_bank(actions)
    q = _feats_s90(said or "")
    best = {}
    order = []
    for i, (phrase, answer) in enumerate(bank):
        s = similarity_s90(q, _feats_s90(phrase)) if said else 0.0
        if answer not in best: best[answer] = []; order.append(answer)
        best[answer].append((s, -i, phrase))
    ranked = sorted(order, key=lambda a: (-max(best[a])[0], -max(best[a])[1]))
    multi = [a for a in ranked if '"actions"' in a]
    words = norm_s90(said).split()
    two = any(w in COMPOUND_CUE_S90 for w in words) or sum(1 for w in words[1:] if w.startswith("و") and len(w) > 3) >= 1
    forced = multi[:2 if two else 1]
    held = [a for a in order if any(p == "بس" for _, _, p in best[a])] if HORN_HELD else []
    chosen = [a for a in ranked if a not in forced and a not in held][:max(0, k - len(forced))]
    pick = chosen[:]
    for a in forced:                                                          # several orders: after the closest single ones
        pick.insert(min(len(pick), 3), a)
    lines = []
    for a in held + pick:
        ph = [p for _, _, p in sorted(best[a], reverse=True)[:PHRASES_PER_LINE_S90]]
        if a in held: ph = ["بس"] + [p for p in ph if p != "بس"][:PHRASES_PER_LINE_S90 - 1]
        lines.append(" / ".join(ph) + " -> " + a)
    if held: lines.insert(1, HORN_RULE_S90)
    return lines, len(held) + (1 if held else 0)


def add_examples(card, said, actions):
    """Tier 2: this message's examples under "أمثلة:", the whole card before her memory within CARD_BUDGET."""
    n = chr(10)
    lines, keep = pick_examples(said, actions)
    mem = n + n + "ذاكرتك الآن:"
    body, msep, mtail = card.rpartition(mem)
    if not msep: body, mtail = card, ""
    while True:
        text = body + n + n.join(lines)
        if len(text) <= CARD_BUDGET or len(lines) <= max(1, keep): break
        lines.pop()
    return text + msep + mtail


def sheet(actions, memory, said=None):
    """CARD_TIERS: tier 1 (said=None, what the chat caches per session), with his line: plus its examples (tier 2).
    Otherwise the old card."""
    if not CARD_TIERS: return _sheet_pre_s90(actions, memory)
    card = tier1(actions, memory)
    return card if said is None else add_examples(card, said, actions)


def card_size(actions, said=None):
    return len(sheet(actions, "", said).rsplit(chr(10) + chr(10) + "ذاكرتك الآن:", 1)[0])
'''

CS = r'''# The card's tier 1 is the cached session sheet; the examples are added per message, from what he just wrote.
_SAID_S90 = []
_session_sheet_pre_s90 = Chat._session_sheet


def _session_sheet_s90(self, snap, mem, acts):
    text = _session_sheet_pre_s90(self, snap, mem, acts)
    if not getattr(MR, "CARD_TIERS", False) or not _SAID_S90: return text
    card = MR.add_examples(text, _SAID_S90[-1], acts)
    self.log("chat: card for this line %d chars (tier 1 %d)" % (len(card), len(text)))
    return card


_route_by_model_pre_s90 = Chat._route_by_model


def _route_by_model_s90(self, history, c, key, snap, mem):
    """As before; the line he wrote is kept for the card's examples while it is routed."""
    _SAID_S90[:] = [str(history[-1].get("text") or "")] if history else []
    try: return _route_by_model_pre_s90(self, history, c, key, snap, mem)
    finally: del _SAID_S90[:]


Chat._session_sheet = _session_sheet_s90
Chat._route_by_model = _route_by_model_s90
'''


def mind(d):
    cs = os.path.join(d, "chat_service.py")
    assert "def _route_by_model" in open(cs, encoding="utf-8").read(), "not the Sol Mind: " + d
    print("model_router.py", append(os.path.join(d, "model_router.py"), MR))
    print("chat_service.py", append(cs, CS))


if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    mind(sys.argv[1])
    print("s90_card_tiers applied")

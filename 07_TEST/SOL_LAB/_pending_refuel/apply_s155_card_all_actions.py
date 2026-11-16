"""s155: every game action the Mind can run is ON the card, always (Jamal 2026-11-15: an action that exists but that the
model is never told about is a bug).
Before: card_check warned about 39 catalog actions the Mind runs if named but the card never shows (eat, drink, wash, cook,
read, reload, give, fetch, doors, windows, stove, bandage, pills, the squad ticks ...). s154 showed one only when his line
looked like a stored example. Now each of them has its own line in the action list, in the card's own format
(id: what she does | "his words" | option: ...), built from the s90 example bank. The lines that were already on the card
are not changed: the old card is built first with the old budget, the new lines are added after its list.
Not listed: the card duplicates (exit_vehicle = exit_car, board_vehicle = board_car, set_combat_doctrine =
sol_combat_plan) and sol_fuel (the pump helper the refuel goals use; "not called alone" in the game's own label).
CARD_BUDGET grows to hold the longer list. LIST_ALL_S155 = False gives the old card back.
v2, after the live phone eval of 2026-11-15 (qwen3-4b: old card 68/114, v1 95/114):
  - a few words on what she does for the lines the model mixed up or answered as small talk;
  - the model sometimes drops the "sol_" of a listed id ("rest", "plan_cancel"): read as that listed action;
  - an on/off action named without an option ("set_scavenge") means on.
usage: apply_s155_card_all_actions.py <sol_mind dir>. "kept" when already applied; an older s155 block is replaced."""
import os, sys
MIND = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)
BEGIN = "# ---------------------------------------------------------------- s155 every action on the card"
END = "# ---------------------------------------------------------------- s155 end"

BLOCK = BEGIN + '''
LIST_ALL_S155 = True                # False: the card as before s155
if "BASE_BUDGET_S155" not in globals(): BASE_BUDGET_S155 = CARD_BUDGET      # the old card is still built within the old budget
CARD_BUDGET = 6600                  # with the full list (card_check (d) and the tests read this one number)
LIST_SKIP_S155 = {"sol_fuel"}       # plus CARD_DUPLICATES
# what she does, in a few words, where the name and one example were not enough for the phone model (live eval 2026-11-15)
DESC_S155 = {
    "sol_take_wheel": "هي تقعد محل السواق وما تمشي",
    "sol_sit_beside": "تقعد بالمقعد القدماني جنبه",
    "sol_car_wait": "تطفي المحرك وتستناه بالسيارة",
    "sol_drive": "تسوق لمكان باسمه",
    "sol_goto": "تمشي عرجليها لمكان",
    "sol_go_inside": "تفوت لأقرب بناية",
    "sol_rest": "تتمدد وترتاح محلها",
    "sol_eat": "هي تاكل من أكلها",
    "sol_drink": "هي تشرب",
    "sol_give": "تعطيه غرض من شنتتها",
    "sol_fetch": "تجيبله غرض من خزانة قريبة",
    "sol_equip_best": "تمسك سلاح بإيدها",
    "sol_reload": "تبدل مخزن سلاحها",
    "sol_plan_status": "وين وصلت بالشغلة اللي عم تعملها",
    "sol_plan_cancel": "تلغي الشغلة اللي عم تعملها",
    "sol_attack_nearest": "تهجم على أقرب زومبي",
    "set_ride_with_player": "تركب معه لحالها كل مرة، أو لا",
    "set_scavenge": "تفتش عالأغراض لحالها",
    "set_hold_fire": "ما تطلق نار",
}
# his words on the list line, where the bank's first phrase shares its key word with another action's phrase
SAID_S155 = {"sol_take_wheel": "قعدي محل السواق"}       # not "ورا الدركسيون": "عطيني الدركسيون" is sol_let_player_drive (live eval)
# card examples added with the list (live eval: "زمري" was answered with option stop, on the old card too)
SHOTS_S155 = ('زمري / زمري بالسيارة -> {"action":"sol_horn","args":{"option":"once"}}',)
if "_sheet_s155_base" not in globals(): _sheet_s155_base = sheet
if "_parse_s155_base" not in globals(): _parse_s155_base = parse
_TICKS_S155 = set()


def _bank_s155():
    """From the s90 bank, per action: his first words and the option values of its single-action examples."""
    said, opts = {}, {}
    for line in EXAMPLE_BANK_S90:
        k = line.find(" -> {")
        if k <= 0 or '"actions"' in line[k:]: continue
        ids = answer_actions_s90(line[k + 4:])
        if len(ids) != 1: continue
        aid = ids[0]
        said.setdefault(aid, line[:k].split(" / ")[0].strip())
        m = re.search(r'"option":"([^"]+)"', line[k:])
        if m and m.group(1) not in opts.setdefault(aid, []): opts[aid].append(m.group(1))
    return said, opts


def extra_list_lines_s155(card, actions):
    """One list line per catalog action that the card does not list yet: id: what she does | "his words" | option: values."""
    visible = set(re.findall(r"(?m)^([a-z_0-9]+):", card))
    skip = set(CARD_DUPLICATES) | LIST_SKIP_S155 | visible
    kinds = {a.get("id"): a.get("kind") for a in actions or []}
    said, opts = _bank_s155()
    out = []
    for a in actions or []:
        aid = a.get("id")
        if not aid or aid in skip or aid not in said: continue
        skip.add(aid)
        line = '%s: %s| "%s"' % (aid, (DESC_S155[aid] + " ") if aid in DESC_S155 else "", SAID_S155.get(aid, said[aid]))
        if kinds.get(aid) == "tick": line += " | option: on \\u0623\\u0648 off"
        elif opts.get(aid): line += " | option: " + " ".join(opts[aid][:4])
        out.append(line)
    return out


def sheet(actions, memory, *more, **kw):
    """The card as before, then every other game action as its own list line."""
    global CARD_BUDGET
    full = CARD_BUDGET
    CARD_BUDGET = BASE_BUDGET_S155
    try: text = _sheet_s155_base(actions, memory, *more, **kw)
    finally: CARD_BUDGET = full
    _TICKS_S155.clear(); _TICKS_S155.update(a.get("id") for a in actions or [] if a.get("kind") == "tick")
    if not LIST_ALL_S155 or CARD_TIERS: return text
    n = chr(10)
    mark = n + n + "\\u0623\\u0645\\u062b\\u0644\\u0629:" + n
    if mark not in text: return text
    lines = extra_list_lines_s155(text, actions)
    if not lines: return text
    head, sep, rest = text.partition(mark)
    shots = [s for s in SHOTS_S155 if s not in rest and (n + s.split('"action":"')[1].split('"')[0] + ": ") in (head + n)]
    return head + n + n.join(lines) + sep + (n.join(shots) + n if shots else "") + rest


def _fix_step_s155(step, listed):
    if not isinstance(step, dict) or not isinstance(step.get("action"), str): return
    a = step["action"]
    if a not in listed and a not in COMMANDS and a not in CARD_ACTIONS and ("sol_" + a) in listed:
        step["action"] = a = "sol_" + a                               # "rest" -> sol_rest: the listed action, its prefix dropped
    if a in _TICKS_S155:
        args = step.get("args") if isinstance(step.get("args"), dict) else {}
        if not str(args.get("option") or "").strip(): step["args"] = dict(args, option="on")   # named without on/off: on


def parse(raw):
    """As before; a listed id written without its sol_ prefix is that action, and an on/off action without an option is on."""
    p = _parse_s155_base(raw)
    if not LIST_ALL_S155: return p
    if not p:
        # the phone model sometimes writes two orders as {"action":"a","args":{..},{"action":"b"}}: not JSON, but clear
        found = re.findall(r'\{\s*"action"\s*:\s*"([a-z_0-9]+)"(?:\s*,\s*"args"\s*:\s*(\{[^{}]*\}))?', re.sub(r"<think>.*?</think>", "", str(raw or ""), flags=re.S))
        steps = []
        for aid, args in found[:MAX_STEPS_S85]:
            try: a = json.loads(args) if args else {}
            except ValueError: a = {}
            steps.append({"action": aid, "args": a if isinstance(a, dict) else {}})
        if len(steps) < 2: return p
        del LAST_STEPS[:]; LAST_STEPS.extend(steps)
        p = {"action": steps[0]["action"], "args": steps[0]["args"], "speech": ""}
    if not LAST_STEPS:
        # {"action":"a","args":{..},"actions":[{"action":"b"}]}: the first order beside the list of the rest
        m = _JSON.search(re.sub(r"<think>.*?</think>", "", str(raw or ""), flags=re.S))
        try: d = json.loads(m.group(0)) if m else None
        except ValueError: d = None
        if isinstance(d, dict) and isinstance(d.get("action"), str) and isinstance(d.get("actions"), list):
            rest = [s for s in (_one_step(x) for x in d["actions"][:MAX_STEPS_S85 - 1]) if s and s.get("action") != p["action"]]
            if rest: LAST_STEPS.extend([{"action": p["action"], "args": p["args"]}] + rest)
    listed = set(_bank_s155()[0]) - set(CARD_DUPLICATES) - LIST_SKIP_S155
    _fix_step_s155(p, listed)
    for s in LAST_STEPS: _fix_step_s155(s, listed)
    return p
''' + END + NL

path = os.path.join(MIND, "model_router.py")
text = open(path, encoding="utf-8", newline="").read()
nl = CRLF if CRLF in text else NL
block = BLOCK.replace(NL, nl)
if block in text:
    print("kept model_router.py")
else:
    if BEGIN in text:
        i = text.index(BEGIN); j = text.index(END, i) + len(END)
        while text[j:j + len(nl)] == nl: j += len(nl)
        text = text[:i].rstrip(CRLF) + nl + nl + nl + block + text[j:]
        print("edited model_router.py (s155 block replaced)")
    else:
        text = text.rstrip(CRLF) + nl + nl + nl + block
        print("edited model_router.py")
    open(path, "w", encoding="utf-8", newline="").write(text)
print("s155 card: every action listed")

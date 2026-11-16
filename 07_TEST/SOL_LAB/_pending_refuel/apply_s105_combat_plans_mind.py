"""s105 combat_plans, Mind side (PLAN_gear_and_combat.md step 1). Pairs with apply_s105_combat_plans.py (switch combat_plans).

ONE action, sol_combat_plan, option = the plan id (smart normal fierce support careful stealth avoid hold). Model first: his words
reach a plan only through the card (the action line carries each plan's Arabic name next to its id, plus example lines); no
word list routes anything. The Mind only maps an Arabic plan NAME the model may have written as the option back to its id.
  model_router.py  s105 block: CARD_ACTIONS["sol_combat_plan"] (shown only when the game lists it, i.e. the switch is on);
                   the card trades lines to stay within CARD_BUDGET: the team-doctrine button (set_combat_doctrine, now the same
                   behaviour as a plan) is left off the card while sol_combat_plan is on it, s91's shorter wording of two
                   rules (_TRIM_S91) is applied, the none examples keep 4 of 6 (the none rule keeps its parenthetical);
                   the plans take one compact line (every id + Arabic name, one example) and at most one more example
                   line, only while within the budget. s90's example bank (two-tier card) gets every plan example.
  chat_service.py  s105 block: her own line for the plan the game confirmed ("تمام، رح كون حذرة"), or a short refusal; nothing
                   technical. A result the game has not confirmed yet keeps the usual reply.
Every change is a block appended at the end of its file (redefinitions), so no earlier installer's text is touched. Mind only;
needs a Mind restart, then card_check.py --write-doc. In place, idempotent.
usage: apply_s105_combat_plans_mind.py <sol_mind dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)
MARK = "# ---------------------------------------------------------------- s105 combat_plans"


def append(path, block):
    t = open(path, encoding="utf-8", newline="").read()
    if MARK in t: return "kept"
    nl = CRLF if CRLF in t else NL
    sep = "" if t.endswith(nl) else nl
    open(path, "w", encoding="utf-8", newline="").write(t + sep + nl + nl + (MARK + NL + block).replace(NL, nl))
    return "appended"


MR = r'''# sol_combat_plan: her fighting plan, one action; option = the plan id. Each plan's Arabic name sits next to its id on the card.
PLAN_IDS_S105 = ("fierce", "smart", "normal", "support", "careful", "stealth", "avoid", "hold")
PLAN_AR_S105 = {"ذكي": "smart", "ذكية": "smart", "عادي": "normal", "عادية": "normal", "شرس": "fierce", "شرسة": "fierce", "إسناد": "support",
                "اسناد": "support", "حذر": "careful", "حذرة": "careful", "تخفي": "stealth", "مخفية": "stealth", "تجنب": "avoid",
                "تجنّب": "avoid", "لا تطلقي": "hold", "ما تطلقي": "hold"}
CARD_ACTIONS["sol_combat_plan"] = ("قتال", "قاتلي بشراسة",                     # compact: every plan id with its Arabic name
                                   "option: fierce شرسة smart ذكية normal عادي support إسناد careful حذرة stealth مخفية avoid تجنّب hold ما تطلقي")
MAX_CARD_SHOTS_S105 = 1                                                      # plan example lines on the card (+ the line's own example = 2)
CARD_DUPLICATES["set_combat_doctrine"] = "sol_combat_plan"                  # the team-doctrine button: the same behaviour as a plan
# his words -> plan: on the card in this order while it stays within CARD_BUDGET; all of them in s90's example bank
PLAN_SHOTS_S105 = (("ما تطلقي", "hold"), ("اسنديني من بعيد", "support"), ("خليكي مخفية", "stealth"), ("خليكي حذرة", "careful"),
                   ("ارجعي قاتلي عادي", "normal"), ("قاتلي بذكاء", "smart"), ("ابعدي عن الزومبي", "avoid"), ("قاتلي بشراسة", "fierce"))
# with sol_combat_plan on the card, the card trades words to stay within CARD_BUDGET (each says the same in fewer words):
TRIMS_S105 = tuple(globals().get("_TRIM_S91", ()))                         # the none rule keeps its parenthetical (town / street -> map)
NONE_DROP_S105 = ("بأي شارع نحنا / ", "شو اسم هي المدينة / ")                  # the none line keeps 4 of 6: a street, where, a village, a station
for _bank in [v for k, v in list(globals().items()) if "BANK" in k and not k.endswith("_S91") and isinstance(v, list)][-1:]:
    for _said, _plan in PLAN_SHOTS_S105:
        _line = '%s -> {"action":"sol_combat_plan","args":{"option":"%s"}}' % (_said, _plan)
        if _said == "قاتلي بشراسة":
            _bank[:] = [x for x in _bank if not x.startswith(_said + " -> ")]
        if _line not in _bank: _bank.append(_line)
_sheet_s105_base = sheet


def plan_id_s105(option):
    """The plan id for what the model wrote as option (an id, or a plan's Arabic name), or None."""
    o = str(option or "").strip()
    if o.lower() in PLAN_IDS_S105: return o.lower()
    return PLAN_AR_S105.get(o.replace("ـ", ""))


def sheet(actions, memory, *more, **kw):
    """The card as before. With sol_combat_plan on it: the trims above, no team-doctrine button line, plan examples while
    within the budget. Without it (switch off): the card exactly as before."""
    text = _sheet_s105_base(actions, memory, *more, **kw)
    n = chr(10)
    if n + "sol_combat_plan: " not in text: return text
    for old, new in TRIMS_S105: text = text.replace(old, new)
    # The 0.28.5 card has newer actions than the original s105 baseline. Keep the
    # same behaviors and map-away wording while trimming duplicate examples to fit.
    text = text.replace(
        'شو في سيارات حواليكي / في سيارة قريبة؟ / شو السيارات اللي حولك -> {"action":"cars_near"}',
        'شو السيارات حواليكي حتى لو بعيدة -> {"action":"cars_near"}')
    text = text.replace(
        'تعالي بالسيارة / هاتي السيارة وتعي لعندي -> {"action":"come_car"}',
        'هاتي السيارة وتعي لعندي -> {"action":"come_car"}')
    text = text.replace(
        '- احكي معه متل إنسان لإنسان: لا تقولي "اللاعب" ولا أي كلمة تقنية، ولا تبلشي كلامك باسمك.',
        '- احكي طبيعي: بلا كلام تقني، لا تقولي اللاعب ولا تبلشي باسمك.')
    lines = []
    for l in text.split(n):
        if l.startswith("set_combat_doctrine: "): continue
        if l.endswith('-> {"action":"none"}'):
            for d in NONE_DROP_S105: l = l.replace(d, "")
        lines.append(l)
    text = n.join(lines)
    tail = n + n + "ذاكرتك الآن:"
    if tail not in text or (n + "أمثلة:" + n) not in text: return text
    body, sep, rest = text.partition(tail)
    added = 0
    for said, plan in PLAN_SHOTS_S105:
        line = '%s -> {"action":"sol_combat_plan","args":{"option":"%s"}}' % (said, plan)
        if said in body: continue
        if added >= MAX_CARD_SHOTS_S105 or len(body) + 1 + len(line) > CARD_BUDGET: break
        body += n + line
        added += 1
    return body + sep + rest
'''

CS = r'''# sol_combat_plan: her own line for the plan the game set; the option the model wrote goes to the game as the plan id.
PLAN_LINES_S105 = {
    "smart": "تمام، رح اختار سلاحي حسب الموقف.",
    "normal": "تمام، رح قاتل عادي.",
    "fierce": "ماشي، رح كون شرسة، بس ما ببعد عنك.",
    "support": "تمام، رح ضل وراك وإحميك من بعيد.",
    "careful": "تمام، رح كون حذرة.",
    "stealth": "حاضر، رح ضل مخفية وما بعمل صوت.",
    "avoid": "ماشي، رح ابعد عن القتال قد ما فيني.",
    "hold": "حاضر، ما بطلق.",
}
PLAN_FAIL_S105 = {"no_sol": "ما فيني هلأ.", "unknown_option": "أي خطة بتقصد؟", "switch_off": "ما بقدر غيّر الخطة هلأ.",
                  "not_recruited": "ما بقدر غيّر الخطة هلأ.", "unknown_action": "ما بقدر غيّر الخطة هلأ."}
_PLAN_RUN_S105 = []


def plan_line_s105(plan, result):
    """Her line for a sol_combat_plan result, or None to keep the usual reply (the game did not confirm yet)."""
    r = result if isinstance(result, dict) else {}
    if r.get("ok") is None and not r.get("error"): return None
    why = str(r.get("reason") or r.get("error") or "")
    if r.get("error") or r.get("ok") is False:
        return PLAN_FAIL_S105.get(why.split(":", 1)[0]) or "ما قدرت غيّر الخطة هلأ."
    return PLAN_LINES_S105.get(plan) or "تمام."


_resolve_and_run_s105_base = resolve_and_run


def resolve_and_run(lua_dir, aid, opt, mem, snap, log=print):
    if aid != "sol_combat_plan": return _resolve_and_run_s105_base(lua_dir, aid, opt, mem, snap, log)
    plan = MR.plan_id_s105(opt)
    if plan is None:
        r = {"ok": False, "reason": "unknown_option"}
    else:
        r = _resolve_and_run_s105_base(lua_dir, aid, plan, mem, snap, log)
    _PLAN_RUN_S105.append((plan, r))
    return r


_route_by_model_s105_base = Chat._route_by_model


def _route_by_model_s105(self, history, c, key, snap, mem):
    """As before; a sol_combat_plan the model chose is answered in her own words."""
    del _PLAN_RUN_S105[:]
    reply = _route_by_model_s105_base(self, history, c, key, snap, mem)
    if not _PLAN_RUN_S105: return reply
    plan, r = _PLAN_RUN_S105[-1]
    del _PLAN_RUN_S105[:]
    line = plan_line_s105(plan, r)
    self.log("chat: sol_combat_plan %s -> %s" % (plan, str(r)[:90]))
    if line is None: return reply
    if len(getattr(MR, "LAST_STEPS", None) or []) > 1 and reply and reply != line: return reply + " " + line
    return line


Chat._route_by_model = _route_by_model_s105
'''


def mind(d):
    cs = os.path.join(d, "chat_service.py")
    t = open(cs, encoding="utf-8").read()
    assert "def _route_by_model" in t and "def resolve_and_run" in t, "not the Sol Mind: " + d
    mr = open(os.path.join(d, "model_router.py"), encoding="utf-8").read()
    assert "CARD_ACTIONS" in mr and "CARD_BUDGET" in mr and "CARD_DUPLICATES" in mr, "model_router lacks the s82/s85 card: " + d
    print("model_router.py", append(os.path.join(d, "model_router.py"), MR))
    print("chat_service.py", append(cs, CS))


if __name__ == "__main__":
    mind(sys.argv[1])
    print("s105_combat_plans_mind applied")

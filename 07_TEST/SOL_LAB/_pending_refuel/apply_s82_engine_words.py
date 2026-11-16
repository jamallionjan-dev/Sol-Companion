"""s82 Mind (Jamal 2026-11-10): engine words, place questions, the unknown -> map answer fallback, a compact card.

Live 22:15:41 "سول طفي متور السيارة" -> the model chose sol_headlights (off, already_off): the only "طفي ... السيارة" example on the
card was the headlights one. Live 22:22:17 "شو اسم هالشارع", 22:22:35 "شو اسم هي المدينة", 22:22:52 "شو اسم هاد الشارع" -> action
unknown, and the unknown branch asked him again before the map answer (memory_answers.answer) was ever tried. On 2026-11-10 01:23 the
same question went none -> "هاد Railview Road." (path=memory); the card has grown since (4600 -> ~4950 chars) and the rule
"مو موجود بالقائمة -> unknown" now catches questions.

Model first, all four parts:
1. model_router.py, the card (a block at the end that rewraps sheet(), works with or without s78/s79, before or after them):
   - examples: "طفي متور السيارة" / "طفي الموتور" -> sol_engine off, "شغلي الموتور" -> sol_engine on;
     "شو اسم هالشارع" / "بأي شارع نحنا" / "وين نحنا هلأ" / "شو اسم هي المدينة" / "بأي ضيعة نحنا" / "شو هالكازية" -> none.
   - the two rules: a request for something not on the list -> unknown; a question (where are we, the street, the town, the
     station) or plain talk -> none.
   - compact: the examples are grouped one line per answer ("a / b -> {...}"), the examples that only repeat the list's own
     example (or one letter off it) are dropped, ' | مثال: "x"' becomes ' | "x"', and the examples leave out the empty ,"speech":"" (the answer line at
     the top of the card still shows it; parse() reads a missing speech as ""). Budget: CARD_BUDGET chars (the sheet without her
     memory, the game's live action list).
2. chat_service.py: when the model says unknown or names no valid action, the map answer is tried (memory_answers.answer, the
   same call the none path makes) and only when it has nothing is he asked again. Logged as path=memory_after_unknown. Never
   before the model, never an action: it only answers questions about the map and her memory.
3. memory_answers.py: "بأي ضيعة نحنا" / "بأي مدينة نحنا" (no "اسم", no "?") are the town question ("شو اسم هي المدينة").
Mind only; needs a Mind restart. In place, idempotent (a marker per file).
usage: apply_s82_engine_words.py <sol_mind dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)
MARK = "# ---------------------------------------------------------------- s82 engine words, place questions, compact card"


def append(path, block):
    t = open(path, encoding="utf-8", newline="").read()
    if MARK in t: return "kept"
    nl = CRLF if CRLF in t else NL
    sep = "" if t.endswith(nl) else nl
    open(path, "w", encoding="utf-8", newline="").write(t + sep + nl + nl + (MARK + NL + block).replace(NL, nl))
    return "appended"


MR = r'''# The card: engine words, place questions go to none (the Mind answers them from the map), and one line per answer.
CARD_BUDGET = 4600                                                            # chars of the sheet without her memory (live actions)
_UNKNOWN_RULE = '- إذا الطلب مش مفهوم أبدًا، أو مو موجود بالقائمة: action = "unknown". لا تختاري فعل ما إلو علاقة بالطلب.'
_NONE_RULE = '- إذا كلام عادي بدون طلب: action = "none"، وجملة قصيرة بـ speech، من الذاكرة بس. لا تذكري مكان أو رقم مو مكتوب تحت.'
UNKNOWN_RULE_S82 = '- طلب شغلة مو بالقائمة، أو كلام مش مفهوم أبدًا: action = "unknown". لا تختاري فعل ما إلو علاقة بالطلب.'
NONE_RULE_S82 = '- سؤال (وين نحنا، شو اسم الشارع أو المدينة أو الكازية) أو كلام عادي بدون طلب: action = "none"، وجملة قصيرة بـ speech، من الذاكرة بس. لا تذكري مكان أو رقم مو مكتوب تحت.'
assert CARD.count(_UNKNOWN_RULE) == 1 and CARD.count(_NONE_RULE) == 1, "s82: the card rules are not the ones this block replaces"
CARD = CARD.replace(_UNKNOWN_RULE, UNKNOWN_RULE_S82).replace(_NONE_RULE, NONE_RULE_S82)
ENGINE_SHOTS_S82 = (("طفي متور السيارة", "off"), ("طفي الموتور", "off"), ("شغلي الموتور", "on"))
PLACE_SHOTS_S82 = ("شو اسم هالشارع", "بأي شارع نحنا", "وين نحنا هلأ", "شو اسم هي المدينة", "بأي ضيعة نحنا", "شو هالكازية")
DROP_SHOTS_S82 = ("سول هتمي بالزرعات بغيابي", "في شي سيارة جنبك؟")      # one letter off the list example; a fourth cars_near line
# and any example that is word for word its own action's example on the list (e.g. "ليش ما زبطت" -> why), found on the card itself
_sheet_s81 = sheet
import re as _re_s82


def compact_examples(text):
    """The examples one line per answer, in the order they first appear; lines that are not examples stay where they were."""
    n = chr(10)
    head, sep, rest = text.partition(n + "أمثلة:" + n)
    if not sep: return text
    body, tail_sep, tail = rest.partition(n + n + "ذاكرتك الآن:")
    listed = {}                                                              # action id -> its example on the list
    for line in head.split(n):
        m = _re_s82.match(r'^([a-z_0-9]+): .*? \| (?:مثال: )?"([^"]+)"', line)
        if m: listed[m.group(1)] = m.group(2)
    groups, order, out = {}, [], []
    for line in body.split(n):
        k = line.find(" -> {")
        if k <= 0:
            out.append(line); continue
        said, answer = line[:k], line[k + 4:].replace(',"speech":""}', "}")   # the answer line at the top already shows speech
        m = _re_s82.search(r'"action":"([^"]+)"', answer)
        if said in DROP_SHOTS_S82 or (m and "args" not in answer and listed.get(m.group(1)) == said): continue
        if answer not in groups:
            groups[answer] = []
            order.append(answer)
            out.append(answer)                                               # its place in the list
        if said not in groups[answer]: groups[answer].append(said)
    lines = [(" / ".join(groups[l]) + " -> " + l) if l in groups else l for l in out]
    return head + sep + n.join(lines) + tail_sep + tail


def sheet(actions, memory):
    """The card as before, with the s82 examples, grouped one line per answer."""
    text = _sheet_s81(actions, memory)
    known = {a.get("id") for a in actions or [] if a.get("enabled", True)}
    n = chr(10)
    shots = []
    if not actions or "sol_engine" in known:
        shots += ['%s -> {"action":"sol_engine","args":{"option":"%s"},"speech":""}' % (t, o) for t, o in ENGINE_SHOTS_S82]
    shots += ['%s -> {"action":"none","speech":""}' % t for t in PLACE_SHOTS_S82]
    tail = n + n + "ذاكرتك الآن:"
    text = text.replace(tail, n + n.join(shots) + tail, 1) if tail in text else text + n + n.join(shots)
    text = text.replace(' | مثال: "', ' | "')
    return compact_examples(text)


def card_size(actions):
    """The sheet's length without her memory: what the budget counts."""
    return len(sheet(actions, "").rsplit(chr(10) + chr(10) + "ذاكرتك الآن:", 1)[0])
'''

CS = r'''# The model said unknown (or named nothing on the list): before asking him again, the map answer is tried, the same call the
# none path makes (streets, towns, stations, where we are). Only words; it never runs an action. path=memory_after_unknown.
ASK_AGAIN_S82 = "شو قصدك؟ عيدها بكلمة تانية."
_parse_s81 = MR.parse
_LAST_PARSE_S82 = []


def _parse_s82(raw):
    p = _parse_s81(raw)
    del _LAST_PARSE_S82[:]
    _LAST_PARSE_S82.append(p)
    return p


MR.parse = _parse_s82
_route_by_model_s81 = Chat._route_by_model


def _route_by_model_s82(self, history, c, key, snap, mem):
    del _LAST_PARSE_S82[:]
    t0 = time.time()
    reply = _route_by_model_s81(self, history, c, key, snap, mem)
    if reply != ASK_AGAIN_S82 or not _LAST_PARSE_S82 or not _LAST_PARSE_S82[-1] or not history: return reply
    action = _LAST_PARSE_S82[-1]["action"]
    ids = {a.get("id") for a in load_actions(self.dir) if a.get("enabled", True)}
    if not (action == "unknown" or (action != "none" and action not in MR.COMMANDS and action not in ids)): return reply   # e.g. refuel with no fuel word
    text = history[-1]["text"]
    try:
        said = MA.answer(text, snap, mem, lambda: self._station_list(), lambda: self._street_now(), GZ.load(), lambda: self._gardens())
    except Exception as e:                                                   # the map answer must never cost him the reply
        self.log("chat: map answer after unknown failed: %r" % (e,))
        said = None
    if not said: return reply
    self.log("chat: route text=%s path=memory_after_unknown ms=%d action=%s gate=- result=%s" % (text[:60], int((time.time() - t0) * 1000), action, str(said)[:90]))
    return said


Chat._route_by_model = _route_by_model_s82
'''

MA = r'''# "بأي ضيعة نحنا" / "بأي مدينة نحنا": the town question, said without "اسم" and without "?".
import re as _re_s82
_TOWN_WHICH_S82 = _re_s82.compile(r"(?:^|\s)(?:ب|ع|على\s*|في\s*)?اي\s+(?:ضيعه|ضيعة|مدينه|مدينة|بلده|بلدة)(?:\s|$)")
_answer_s81 = answer


def answer(text, snap, mem, stations=None, street_now=None, gaz=None, gardens=None):
    said = _answer_s81(text, snap, mem, stations, street_now, gaz, gardens)
    if said is None and _TOWN_WHICH_S82.search(norm(text) or ""):
        said = _answer_s81("شو اسم هي المدينة", snap, mem, stations, street_now, gaz, gardens)
    return said
'''


def mind(d):
    cs = os.path.join(d, "chat_service.py")
    t = open(cs, encoding="utf-8").read()
    assert "def _route_by_model" in t and "MA.answer(" in t and 'return "شو قصدك؟ عيدها بكلمة تانية."' in t, "not the Sol Mind: " + d
    assert "def answer(text, snap, mem, stations=None, street_now=None, gaz=None, gardens=None)" in open(os.path.join(d, "memory_answers.py"), encoding="utf-8").read()
    print("model_router.py", append(os.path.join(d, "model_router.py"), MR))
    print("chat_service.py", append(cs, CS))
    print("memory_answers.py", append(os.path.join(d, "memory_answers.py"), MA))


if __name__ == "__main__":
    mind(sys.argv[1])
    print("s82 engine_words applied")

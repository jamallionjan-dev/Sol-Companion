"""Every line he types goes to the connected model first. It picks the nearest action the Mind can run; the Mind checks it, runs it and reads the result from the game.
The model only chooses and words a line; nothing it says counts as done until the game has confirmed it."""
import json, re

# id -> (what it means, the phrase the Mind's own orders already understand). None: the Mind answers it itself.
COMMANDS = {
    "follow":        ("تمشي ورا اللاعب وهي جنبه", "الحقيني"),
    "stay":          ("تضل واقفة بمكانها", "ضلي هون"),
    "forget_all":    ("تلغي كل أوامرها وترجع تلحقه", "انسي كلشي"),
    "come_foot":     ("لما تكون بعيدة: تجي مشي", "تعالي مشي"),
    "come_car":      ("لما تكون بعيدة: تجي بالسيارة", "تعالي بالسيارة"),
    "awake":         ("يسأل إذا هي فايقة", "سول فايقة؟"),
    "drive":         ("تركب السيارة وتسوق", "سوقي السيارة"),
    "drive_marker":  ("تسوق للعلامة عالخريطة", "سوقي عالعلامة"),
    "drive_home":    ("تسوق عالبيت", "سوقي عالبيت"),
    "drive_stop":    ("توقف السيارة", "وقفي السيارة"),
    "sol_let_player_drive": ("تعطيه مقعد القيادة بنفس المركبة", "عطيني القيادة"),
    "sol_pilot_helicopter": ("تأخذ مقعد الطيار بالمروحية التي يركبها اللاعب فقط", "سول طيري بالمروحية"),
    "sol_heli_fly_marker": ("تبدأ الطيران الجوي المباشر إلى علامة GPS المحددة مسبقًا", "سول طيري على العلامة"),
    "sol_summon_helicopter": ("تطلب مروحية JetFuel من آخر نوع قاده اللاعب؛ الافتراضي Huey", "سول فيكي تجيبي هليكوبتر"),
    "exit_car":      ("تنزل من السيارة", "انزلي"),
    "board_car":     ("تركب جنب اللاعب كراكبة", "اركبي معي"),
    "park":          ("تصف السيارة بالكراج", "صفي السيارة"),
    "set_home":      ("هذا المكان صار بيتنا", "هاد بيتنا"),
    "go_home_rest":  ("تضل بالبيت وترتاح", "ضلي بالبيت ارتاحي"),
    "farm_keeper":   ("تهتم بالمزرعة لحالها", "سول اهتمي بالزرعات بغيابي"),
    "farm_stop":     ("توقف شغل المزرعة", "وقفي شغل المزرعة"),
    "harvest":       ("تحصد المحصول الجاهز", "احصدي الحصاد"),
    "water":         ("تسقي الزرع", "اسقي الزرع"),
    "cure":          ("تعالج الزرع من المرض", "عالجي الزرع"),
    "weed":          ("تنظف العشب", "نظفي الزرع من العشب"),
    "fertilize":     ("تسمد الزرع", "حطي للزرع سماد"),
    "plow":          ("تحرث الأرض", "احرثي الارض"),
    "plant":         ("تزرع البذور", "ازرعي البذور اللي بهاد الموسم"),
    "farm_short":    ("شو ناقص للزراعة", "شو ناقصنا للزراعة"),
    "farm_status":   ("شو عم تعمل هلأ", "شو عم تعملي"),
    "farm_report":   ("تقرير عن حالة الزرع", "شوفي عنا بالمزرعة"),
    "sort_items":    ("ترتب أغراض البيت كل شي بمكانو", "رتبي الاغراض"),
    "sort_stop":     ("توقف الترتيب", "وقفي الترتيب"),
    "animal_care":   ("تهتم بالدجاج: مي وأكل بالمعالف وبيض للمطبخ", "اهتمي بالدجاج"),
    "eggs":          ("تجمع البيض وتحطو بالمطبخ", "اجمعي البيض"),
    "animal_stop":   ("توقف شغل الدجاج", "وقفي شغل الدجاج"),
    "address_book":  ("دفتر عناوينها: بيوت للبيع، مخابئ ومناطق شافتها معه؛ بتقول شو فيه أو بتاخدو لعنوان منو", "شو في عنا عناوين"),
    "refuel_from_can":   ("تعبي السيارة من بدونة بنزين", None),
    "refuel_at_station": ("تعبي السيارة أو بدونات البنزين من الكازية", "عبي السيارة بنزين من الكازية"),
    "survey":        ("تفحص البيت والمكان كلو: البيت، الزراعة، الكراج، أماكن الشغل", None),
    "cars_near":     ("تقلو شو في سيارات حواليها هي: أساميها، قديش بعيدة، وإذا بتمشي", None),     # s77: her surroundings, far or here
    "why":           ("يسأل ليش فشل آخر شي", None),
    "secret_loadout": ("تعطيه نسخة من سلاحه السري: سلاحين بكل قطعهن ومخازن مليانة وذخيرة", "عطيني سلاحي السري"),
}
EXTRA_EXAMPLE = {"survey": "فحصي المكان", "cars_near": "شوفي سيارات حواليكي", "why": "ليش ما زبطت", "refuel_from_can": "عبي السيارة بنزين"}
ARGS_NOTE = {"sol_cook": "option: شو تطبخ، مثال: طبخي بيض"}
# game actions the panel does not list as buttons, that he asks for in plain words
CARD_ACTIONS = {
    "sol_headlights": ("ضو السيارة", "شغلي ضو السيارة", "option: on أو off"),
    "sol_toggle_light": ("ضو الغرفة أو البيت، أقرب مفتاح ضو", "ضوي الغرفة", None),
    "sol_engine": ("محرك السيارة", "شغلي السيارة", "option: on أو off"),
    "sol_horn": ("زمور السيارة", "زمري", "option: once أو stop"),
}

CARD = """أنتِ سول: مرافقة حقيقية للاعب داخل لعبة Project Zomboid، امرأة، بتحكي بالشامي عن حالك بصيغة المؤنث، ومو بوت دردشة.
مهمتك: اقرئي جملة اللاعب، حتى لو فيها أخطاء كتابة، واختاري فعل واحد من القائمة، الأقرب لقصدو. العقل بينفذ الفعل ويتأكد منه باللعبة، وهو اللي بيقول النتيجة، فلا تقولي إنك عملتِ شي.
الجواب سطر JSON واحد بس:
{"action":"معرف القائمة حرفيًا","speech":""}

- action: معرف القائمة؛ option عند الحاجة.
- speech: فاضي إلا مع none.
- للطيران: «طيري بالمروحية» لمقعد الطيار فقط. بعد اختيار علامة GPS، «طيري على العلامة» تبدأ الرحلة؛ السرعة والارتفاع والهبوط من GPS.
- الطلب غير المفهوم أو غير الموجود: unknown. الكلام العادي: none وجملة قصيرة من الذاكرة.
- لا تختلقي موقعًا أو رقمًا."""

EXAMPLES = (("سول هتمي بالزرعات بغيابي", "farm_keeper"), ("خلص انسي كلشي", "forget_all"), ("بكفي هيك وقفي الترتيب", "sort_stop"), ("خليكي ورايي", "follow"), ("اطلعي بالسيارة وسوقي", "drive"), ("نزلي من السيارة", "exit_car"), ("اركبي جنبي", "board_car"), ("صفيها", "park"), ("شو الأماكن اللي سجلتيها", "address_book"), ("ليش ما زبطت", "why"),
            ("اقطفي الزرع", "harvest"), ("دبريلي الارض بغيابي", "farm_keeper"), ("خلص وقفي زراعة", "farm_stop"), ("انتي صاحية", "awake"), ("عنا شو بالمكان", "survey"),
            ("جيبيلي سلاحي السري", "secret_loadout"), ("بدي أسلحتي السرية", "secret_loadout"))
EXAMPLES += (("شوفي سيارات حواليكي", "cars_near"), ("شو في سيارات حواليكي", "cars_near"), ("في سيارة قريبة؟", "cars_near"),   # s77
             ("في شي سيارة جنبك؟", "cars_near"), ("شو السيارات اللي حولك", "cars_near"))
EXAMPLES += (("عطيني القيادة", "sol_let_player_drive"), ("سول طيري بالمروحية", "sol_pilot_helicopter"),
             ("سول طيري على العلامة", "sol_heli_fly_marker"))


# Game catalog buttons that do what one of her own commands already does (2026-11-11: the loadout page lists exit_vehicle while
# she is near a car). The card shows her command only; the Mind still runs the game id if a reply names it.
CARD_DUPLICATES = {"exit_vehicle": "exit_car", "board_vehicle": "board_car"}

def sheet(actions, memory):
    """The entry card any connected model gets: who she is, its one job, what it can ask for, what she remembers. Generated from the Mind's own lists."""
    n = chr(10)
    lines = []
    for cid, (meaning, phrase) in COMMANDS.items():
        example = phrase or EXTRA_EXAMPLE.get(cid)
        lines.append("%s: %s%s" % (cid, meaning, ' | مثال: "%s"' % example if example else ""))
    for a in actions or []:
        if a.get("id") not in COMMANDS and CARD_DUPLICATES.get(a.get("id")) not in COMMANDS and a.get("enabled", True) and a.get("kind") == "button":   # one action per behaviour: a game button that duplicates her own command stays off the card
            note = ARGS_NOTE.get(a["id"])
            lines.append("%s: %s%s" % (a["id"], str(a.get("label") or a.get("reason") or "")[:40], " | " + note if note else ""))
    known = {a.get("id") for a in actions or [] if a.get("enabled", True)}
    for cid, (meaning, phrase, note) in CARD_ACTIONS.items():
        if cid in known or not actions:
            lines.append('%s: %s | مثال: "%s"%s' % (cid, meaning, phrase, " | " + note if note else ""))
    shots = n.join('%s -> {"action":"%s","speech":""}' % e for e in EXAMPLES)
    shots += n + 'شغلي الضو -> {"action":"sol_headlights","args":{"option":"on"},"speech":""}'
    shots += n + 'طفي ضو السيارة -> {"action":"sol_headlights","args":{"option":"off"},"speech":""}'
    shots += n + 'ضوي الغرفة -> {"action":"sol_toggle_light","speech":""}'
    shots += n + 'رقصي -> {"action":"unknown","speech":""}'
    return CARD + n + n + "الأفعال:" + n + n.join(lines) + n + n + "أمثلة:" + n + shots + n + n + "ذاكرتك الآن:" + n + str(memory or "لا شيء بعد.")


_JSON = re.compile(r"\{.*\}", re.S)


def parse(raw):
    """{"action", "args", "speech"} or None when the reply cannot be read."""
    text = re.sub(r"<think>.*?</think>", "", str(raw or ""), flags=re.S).strip()
    m = _JSON.search(text)
    if not m: return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    if not isinstance(d, dict) or not isinstance(d.get("action"), str): return None
    args = d.get("args") if isinstance(d.get("args"), dict) else {}
    return {"action": d["action"].strip(), "args": args, "speech": str(d.get("speech") or "").strip()}


def message(text, model=""):
    """Models with a thinking mode are told to skip it here, in the transport, so the card itself stays the same for every model."""
    return [{"role": "user", "content": str(text) + (" /no_think" if "qwen3" in str(model).lower() else "")}]


# ---------------------------------------------------------------- s78 cars_away
# come_car: "تعالي لعندي بالسيارة" is its phrase; synonyms only, no new action. Talking to him as a person.
COMMANDS["come_car"] = (COMMANDS["come_car"][0], "تعالي لعندي بالسيارة")
EXAMPLES += (("تعالي بالسيارة", "come_car"), ("هاتي السيارة وتعي لعندي", "come_car"))
CARD += "\n- احكي معه متل إنسان لإنسان: لا تقولي \"اللاعب\" ولا أي كلمة تقنية، ولا تبلشي كلامك باسمك."


# ---------------------------------------------------------------- s79 horn_hold
# horn_hold: her hand stays on the horn while she drives, until he says stop. sol_horn (one beep) is unchanged.
HORN_HELD = False                                                             # set by the chat for each sheet it builds
CARD_ACTIONS["horn_hold"] = ("تضلي حاطة إيدك عالزمور وإنتِ عم تسوقي، لحتى يقلك وقفي", "خلي ايدك عالزمور", "option: start أو stop")
HORN_START = ("خلي ايدك عالزمور", "ضلك زمري", "ضلي زمري", "زمري طول الطريق", "زرمي طول الطريق")
HORN_STOP = ("وقفي الزمور", "شيلي ايدك عن الزمور", "خلص بلا زمور")
HORN_HELD_STOP = ("بس",)                                                      # only while her hand is on the horn
_sheet_s78 = sheet


def _horn_shot(text, action, option):
    return '%s -> {"action":"%s","args":{"option":"%s"},"speech":""}' % (text, action, option)


def sheet(actions, memory):
    """The card as before; with horn_hold on it, its examples, and "بس" as a stop only while she holds the horn."""
    text = _sheet_s78(actions, memory)
    known = {a.get("id") for a in actions or [] if a.get("enabled", True)}
    if actions and "horn_hold" not in known: return text
    n = chr(10)
    shots = [_horn_shot(t, "horn_hold", "start") for t in HORN_START] + [_horn_shot(t, "horn_hold", "stop") for t in HORN_STOP]
    if not actions or "sol_horn" in known: shots.append(_horn_shot("زمري", "sol_horn", "once"))
    if HORN_HELD:
        shots += [_horn_shot(t, "horn_hold", "stop") for t in HORN_HELD_STOP]
        shots.append("إيدك عالزمور هلأ: \"بس\" لحالها يعني شيلي إيدك عنه.")
    tail = n + n + "ذاكرتك الآن:"
    if tail not in text: return text + n + n.join(shots)
    return text.replace(tail, n + n.join(shots) + tail, 1)


# ---------------------------------------------------------------- s82 engine words, place questions, compact card
# The card: engine words, place questions go to none (the Mind answers them from the map), and one line per answer.
CARD_BUDGET = 4600                                                            # chars of the sheet without her memory (live actions)
_UNKNOWN_RULE = '- إذا الطلب مش مفهوم أبدًا، أو مو موجود بالقائمة: action = "unknown". لا تختاري فعل ما إلو علاقة بالطلب.'
_NONE_RULE = '- إذا كلام عادي بدون طلب: action = "none"، وجملة قصيرة بـ speech، من الذاكرة بس. لا تذكري مكان أو رقم مو مكتوب تحت.'
UNKNOWN_RULE_S82 = '- طلب مو واضح أو مو بالقائمة: action = "unknown".'
NONE_RULE_S82 = '- سؤال عن المكان أو كلام عادي: action = "none"، كلام قصير من الذاكرة فقط.'
_UNKNOWN_RULE_COMPACT = '- الطلب غير المفهوم أو غير الموجود: unknown. الكلام العادي: none وجملة قصيرة من الذاكرة.'
_NONE_RULE_COMPACT = '- لا تختلقي موقعًا أو رقمًا.'
if CARD.count(_UNKNOWN_RULE) == 1 and CARD.count(_NONE_RULE) == 1:
    CARD = CARD.replace(_UNKNOWN_RULE, UNKNOWN_RULE_S82).replace(_NONE_RULE, NONE_RULE_S82)
elif CARD.count(_UNKNOWN_RULE_COMPACT) == 1 and CARD.count(_NONE_RULE_COMPACT) == 1:
    CARD = CARD.replace(_UNKNOWN_RULE_COMPACT, UNKNOWN_RULE_S82).replace(_NONE_RULE_COMPACT, NONE_RULE_S82)
else:
    raise AssertionError("s82: the card rules are not the ones this block replaces")
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


# ---------------------------------------------------------------- s85 card budget, two orders in one line, exit first, far report
# The card within CARD_BUDGET with every switch on (horn_hold listed, her hand on it or not): shorter words, one example per
# horn answer, a short example for each game button, two orders in one line ("actions", in order), "شوفي عنا بالمخزون".
_INTRO_S85 = (("أنتِ سول: مرافقة حقيقية للاعب داخل لعبة Project Zomboid، امرأة، بتحكي بالشامي عن حالك بصيغة المؤنث، ومو بوت دردشة.",
               "أنتِ سول، رفيقته بـProject Zomboid، بتحكي شامي بصيغة المؤنث."),
              ("مهمتك: اقرئي جملة اللاعب، حتى لو فيها أخطاء كتابة، واختاري فعل واحد من القائمة، الأقرب لقصدو. العقل بينفذ الفعل ويتأكد منه باللعبة، وهو اللي بيقول النتيجة، فلا تقولي إنك عملتِ شي.",
               "افهمي طلبه واختاري أقرب فعل؛ العقل ينفذ ويتأكد."),
              ("- لا تكتبي إحداثيات أو أرقام مواقع بالكلام أبدًا." + chr(10) + "- احكي معه متل إنسان لإنسان: لا تقولي \"اللاعب\" ولا أي كلمة تقنية، ولا تبلشي كلامك باسمك.",
               "- احكي طبيعيًا، بلا كلام تقني، ولا تخترعي أماكن أو أرقامًا." + chr(10)
               + "- طلبين: \"actions\" بالترتيب، متل الأمثلة."),
              ("- للطيران: «طيري بالمروحية» لمقعد الطيار فقط. بعد اختيار علامة GPS، «طيري على العلامة» تبدأ الرحلة؛ السرعة والارتفاع والهبوط من GPS.",
               "- طيران: «طيري بالمروحية» للمقعد؛ اختاري علامة ثم «طيري على العلامة». السرعة والارتفاع والهبوط من GPS."))
for _old, _new in _INTRO_S85:
    if _old in CARD: CARD = CARD.replace(_old, _new)
_MEANING_S85 = {
    "follow": "تمشي وراه", "board_car": "تركب جنبه كراكبة",
    "animal_care": "تهتم بالدجاج: مي وأكل وبيض", "address_book": "دفتر عناوينها: بيوت ومخابئ شافتها، شو فيه أو تاخدو لعنوان",
    "survey": "تفحص البيت والزراعة والكراج وأماكن الشغل", "cars_near": "شو في سيارات حواليها، حتى لو بعيدة عنو",
    "secret_loadout": "نسخة من سلاحه السري مع ذخيرة", "refuel_at_station": "تعبي السيارة والبدونات من الكازية", "farm_keeper": "تهتم بالمزرعة لحالها",
    "sol_pilot_helicopter": "تأخذ مقعد الطيار فقط",
    "sol_heli_fly_marker": "تبدأ رحلة لعلامة GPS",
    "sol_summon_helicopter": "مروحية ممتلئة من آخر نوع؛ الافتراضي Huey",
}
for _k, _v in _MEANING_S85.items():
    if _k in COMMANDS: COMMANDS[_k] = (_v, COMMANDS[_k][1])
# the phrase says it all: the line keeps the id and the phrase ("water: | \"اسقي الزرع\"")
PHRASE_ONLY_S85 = ("stay", "drive_stop", "exit_car", "set_home", "farm_stop", "harvest", "water", "cure", "weed", "fertilize", "plow",
                   "sort_stop", "animal_stop", "drive_home", "farm_short", "farm_status", "awake", "drive", "drive_marker", "go_home_rest",
                   "sort_items", "eggs", "plant")
# horn_hold: one example per answer; "زمري" is the list's own sol_horn example; "بس" only while her hand is on the horn (s79)
CARD_ACTIONS["horn_hold"] = ("إيدك عالزمور طول ما عم تسوقي", "خلي ايدك عالزمور", "option: start أو stop")
HORN_START = ("ضلك زمري", "زرمي طول الطريق")
HORN_STOP = ("وقفي الزمور",)
_HORN_DROP_S85 = ('زمري -> {"action":"sol_horn","args":{"option":"once"}}', "إيدك عالزمور هلأ: \"بس\" لحالها يعني شيلي إيدك عنه.")
# the game's own buttons: a short example each (the label stays as the game wrote it)
ARGS_NOTE.update({"regroup": '"تجمعي حدي"', "retreat": '"انسحبي"', "set_combat_doctrine": '"طبقي الخطة عالكل"',
                  "open_inventory": '"فرجيني شنتتك"', "open_health": '"افحصي صحتك"', "bandage": '"ضمدي جرحك"'})
SHOTS_S85 = ('شوفي عنا بالمخزون -> {"action":"farm_report"}',
             'طفي المحرك ونزلي -> {"actions":[{"action":"sol_engine","args":{"option":"off"}},{"action":"exit_car"}]}',
             'نزلي من السيارة وتعالي لعندي -> {"actions":[{"action":"exit_car"},{"action":"come_foot"}]}')
MAX_STEPS_S85 = 3
_sheet_s82 = sheet


def sheet(actions, memory):
    """The card as before, within the budget: horn lines as one answer each, phrase-only lines, the s85 examples."""
    text = _sheet_s82(actions, memory)
    n = chr(10)
    lines = []
    for line in text.split(n):
        if line in _HORN_DROP_S85: continue
        cid = line.split(": ", 1)[0]
        if cid in PHRASE_ONLY_S85 and cid in COMMANDS and ' | "' in line: line = '%s: | "%s"' % (cid, line.split(' | "', 1)[1].rstrip('"'))
        lines.append(line)
    text = n.join(lines)
    known = {a.get("id") for a in actions or [] if a.get("enabled", True)}
    shots = [s for s in SHOTS_S85 if not ("sol_engine" in s and actions and "sol_engine" not in known)]
    tail = n + n + "ذاكرتك الآن:"
    return text.replace(tail, n + n.join(shots) + tail, 1) if tail in text else text + n + n.join(shots)


def card_size(actions):
    return len(sheet(actions, "").rsplit(chr(10) + chr(10) + "ذاكرتك الآن:", 1)[0])


# "actions": two or three orders in one line, in order. The first is what parse() returns (every older path reads it);
# the whole list waits in LAST_STEPS for the chat, which runs the rest after the first has finished.
LAST_STEPS = []
_parse_s85_base = parse


def _one_step(d):
    if not isinstance(d, dict) or not isinstance(d.get("action"), str) or not d["action"].strip(): return None
    return {"action": d["action"].strip(), "args": d.get("args") if isinstance(d.get("args"), dict) else {}}


def parse(raw):
    """As before; a reply with "actions" (a list) reads as its first action, the rest go to LAST_STEPS."""
    del LAST_STEPS[:]
    text = re.sub(r"<think>.*?</think>", "", str(raw or ""), flags=re.S).strip()
    m = _JSON.search(text)
    d = None
    if m:
        try: d = json.loads(m.group(0))
        except ValueError: d = None
    if isinstance(d, dict) and isinstance(d.get("actions"), list) and not isinstance(d.get("action"), str):
        steps = [s for s in (_one_step(x) for x in d["actions"][:MAX_STEPS_S85]) if s]
        if not steps: return None
        LAST_STEPS.extend(steps)
        return {"action": steps[0]["action"], "args": steps[0]["args"], "speech": str(d.get("speech") or "").strip()}
    return _parse_s85_base(raw)


# ---------------------------------------------------------------- s90 card tiers: index + per-message examples
# Tier 1 (every message): rules, one line with every action name, her memory. Tier 2 (per message): the examples most like
# his words, from a bank with at least one example for every action. The model decides; retrieval only picks examples.
CARD_TIERS = False                                                             # False: the old one-tier card (Mind restart)
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
    ("سول عبي بدونات البنزين من الكازية", "refuel_at_station", None),
    ("عبي السيارة بنزين من الكازية", "refuel_at_station", None),
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
    ("سول عطيني القيادة", "sol_let_player_drive", None), ("عطيني القيادة", "sol_let_player_drive", None),
    ("سول طيري بالمروحية", "sol_pilot_helicopter", None), ("خدي مقعد الطيار بالمروحية", "sol_pilot_helicopter", None),
    ("سول طيري على العلامة", "sol_heli_fly_marker", None), ("طيري للمكان المحدد على الجي بي اس", "sol_heli_fly_marker", None),
    ("سول فيكي تجيبي هليكوبتر", "sol_summon_helicopter", None), ("سول فيكي تجيبي مروحية", "sol_summon_helicopter", None),
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


# ---------------------------------------------------------------- s87 smart_park: park near any place
# park: the garage, or the nearest free spot when he is not at home (the game decides which; the model only picks "park")
COMMANDS["park"] = ("تصف السيارة بالكراج أو أقرب مكان فاضي", COMMANDS["park"][1])

# ---------------------------------------------------------------- s91 engine off on exit, unless he says keep it running
# exit_car keep_engine: his explicit "get out and leave the engine running". One variant of exit_car, taught by an example.
KEEP_ENGINE_SAID_S91 = ("نزلي من السيارة وخلي المحرك شغال", "خلي الموتور شغال")
KEEP_ENGINE_ANSWER_S91 = '{"action":"exit_car","args":{"option":"keep_engine"}}'
KEEP_ENGINE_LINE_S91 = " / ".join(KEEP_ENGINE_SAID_S91) + " -> " + KEEP_ENGINE_ANSWER_S91
KEEP_ENGINE_S91 = False                                                      # set by parse(), read and cleared by the chat
_TRIM_S91 = (('الجواب سطر JSON واحد فقط، بدون أي كلام تاني:' + chr(10) + '{"action":"معرف من القائمة","speech":""}' + chr(10) + chr(10)
              + '- action: معرف القائمة حرفيًا.' + chr(10),
              'الجواب سطر JSON واحد بس:' + chr(10) + '{"action":"معرف من القائمة حرفيًا","speech":""}' + chr(10) + chr(10)),
             ('- option: أضيفيها بس للأفعال المكتوب جنبها option.', '- option: بس للأفعال اللي جنبها option.'))


def _bank_add_s91():
    """s90's example bank, when this Mind has one: the keep_engine example goes there in the bank's own shape. The bank's name, or None."""
    names = [k for k, v in list(globals().items()) if "BANK" in k and not k.endswith("_S91") and isinstance(v, (list, dict))]
    if not names: return None
    name = names[-1]
    bank = globals()[name]
    answer = json.loads(KEEP_ENGINE_ANSWER_S91)
    if isinstance(bank, dict):
        sample = next(iter(bank.values()), KEEP_ENGINE_ANSWER_S91)
        for said in KEEP_ENGINE_SAID_S91: bank.setdefault(said, answer if isinstance(sample, dict) else KEEP_ENGINE_ANSWER_S91)
        return name
    sample = bank[0] if bank else KEEP_ENGINE_LINE_S91
    if isinstance(sample, str):
        if KEEP_ENGINE_LINE_S91 not in bank: bank.append(KEEP_ENGINE_LINE_S91)
        return name
    if isinstance(sample, (tuple, list)) and len(sample) == 2 and isinstance(sample[0], str):
        for said in KEEP_ENGINE_SAID_S91:
            if not any(e[0] == said for e in bank):
                e = (said, answer if isinstance(sample[1], dict) else KEEP_ENGINE_ANSWER_S91)
                bank.append(e if isinstance(sample, tuple) else list(e))
        return name
    return None


BANK_S91 = _bank_add_s91()
if BANK_S91 is None:
    for _old, _new in _TRIM_S91:
        if _old in CARD: CARD = CARD.replace(_old, _new)
_sheet_s91_base = sheet


def sheet(actions, memory, *more, **kw):
    """The card as before; with no example bank, the keep_engine example as one line after the others."""
    text = _sheet_s91_base(actions, memory, *more, **kw)
    if BANK_S91 is not None or KEEP_ENGINE_LINE_S91 in text: return text
    tail = chr(10) + chr(10) + "ذاكرتك الآن:"
    return text.replace(tail, chr(10) + KEEP_ENGINE_LINE_S91 + tail, 1) if tail in text else text + chr(10) + KEEP_ENGINE_LINE_S91


_parse_s91_base = parse


def parse(raw):
    """As before; KEEP_ENGINE_S91 says whether this reply is exit_car with option keep_engine."""
    global KEEP_ENGINE_S91
    p = _parse_s91_base(raw)
    KEEP_ENGINE_S91 = bool(p and p.get("action") == "exit_car" and str((p.get("args") or {}).get("option") or "").strip().lower() == "keep_engine")
    return p
# ---------------------------------------------------------------- s91 end



# ---------------------------------------------------------------- s105 combat_plans
# sol_combat_plan: her fighting plan, one action; option = the plan id. Each plan's Arabic name sits next to its id on the card.
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


# ---------------------------------------------------------------- s154 card_extra_actions
# Game actions that are not on the one-tier card, shown to the model only with the message that asks for one of them.
EXTRA_MIN_S154 = 0.6                # eval 2026-11-15 (s82_route_eval.json): none of the 76 lines for card actions reaches it
EXTRA_MAX_S154 = 2
EXTRA_SKIP_S154 = {"sol_fuel"}      # the pump helper: used by the refuel goals, not called alone


def extra_action_lines(card, said, actions):
    """Bank examples for this line whose action the card does not list, best first. [] when nothing is close enough."""
    if not said: return []
    visible = set(re.findall(r"(?m)^([a-z_0-9]+):", card)) | {"none", "unknown"}
    possible = {a.get("id") for a in actions or [] if a.get("enabled") is not False}
    skip = set(CARD_DUPLICATES) | EXTRA_SKIP_S154
    q = _feats_s90(said)
    best = {}
    for line in EXAMPLE_BANK_S90:
        k = line.find(" -> {")
        if k <= 0: continue
        answer = line[k + 4:]
        ids = answer_actions_s90(answer)
        new = [i for i in ids if i not in visible]
        if not new or any(i in skip or i not in possible for i in new): continue
        for phrase in line[:k].split(" / "):
            s = similarity_s90(q, _feats_s90(phrase))
            if s >= EXTRA_MIN_S154 and s > best.get(answer, (0.0, ""))[0]: best[answer] = (s, phrase.strip())
    ranked = sorted(best.items(), key=lambda kv: -kv[1][0])[:EXTRA_MAX_S154]
    return ["%s -> %s" % (phrase, answer) for answer, (_, phrase) in ranked]


def add_extra_actions(card, said, actions):
    """The card as it is, plus this message's examples of actions it does not list (before her memory)."""
    lines = extra_action_lines(card, said, actions)
    if not lines: return card
    n = chr(10)
    tail = n + n + "\u0630\u0627\u0643\u0631\u062a\u0643 \u0627\u0644\u0622\u0646:"
    body, sep, rest = card.partition(tail)
    return body + n + n.join(lines) + sep + rest
# ---------------------------------------------------------------- s154 end


# ---------------------------------------------------------------- s155 every action on the card
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
        if kinds.get(aid) == "tick": line += " | option: on \u0623\u0648 off"
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
    mark = n + n + "\u0623\u0645\u062b\u0644\u0629:" + n
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
# ---------------------------------------------------------------- s155 end


# ---------------------------------------------------------------- s157 phone_patience
# When the model does not answer: his words against the example bank. Near-exact only (OFFLINE_MIN_S157): a guess here
# would run an order he did not give. Short forms he typed on 2026-11-15 that the bank does not hold are listed beside it.
OFFLINE_MIN_S157 = 0.85
OFFLINE_SAID_S157 = (
    ("شربي", '{"action":"sol_drink"}'), ("اشربي", '{"action":"sol_drink"}'), ("شربي شي", '{"action":"sol_drink"}'),
    ("غسلي", '{"action":"sol_wash"}'), ("تغسلي", '{"action":"sol_wash"}'),
    ("عطيني الدركسيون", '{"action":"sol_let_player_drive"}'), ("عطيني سوق", '{"action":"sol_let_player_drive"}'),
    ("خليني سوق", '{"action":"sol_let_player_drive"}'), ("خليني انا سوق", '{"action":"sol_let_player_drive"}'),
    ("زمري", '{"action":"sol_horn","args":{"option":"once"}}'), ("زمري بالسيارة", '{"action":"sol_horn","args":{"option":"once"}}'),
    ("طفي المحرك ونزلي", '{"action":"exit_car"}'), ("طفي المحرك وانزلي", '{"action":"exit_car"}'),
)
_NAME_S157 = re.compile("^\\s*(?:يا\\s+)?سول[\\s،,]+")


def offline_answer_s157(said, actions):
    """The bank's answer for words that are (nearly) one of its examples, as the JSON text a model would have sent. None otherwise."""
    said = _NAME_S157.sub("", str(said or "")).strip()
    if not said: return None
    possible = {a.get("id") for a in actions or [] if a.get("enabled") is not False} | set(COMMANDS)
    q = _feats_s90(said)
    pairs = list(OFFLINE_SAID_S157)
    for line in EXAMPLE_BANK_S90:
        k = line.find(" -> {")
        if k > 0: pairs.extend((ph.strip(), line[k + 4:]) for ph in line[:k].split(" / "))
    best, answer = 0.0, None
    for phrase, ans in pairs:
        s = similarity_s90(q, _feats_s90(_NAME_S157.sub("", phrase)))
        if s > best: best, answer = s, ans
    if answer is None or best < OFFLINE_MIN_S157: return None
    ids = answer_actions_s90(answer)
    if not ids or any(i in ("none", "unknown") or i not in possible for i in ids): return None
    return answer
# ---------------------------------------------------------------- s157 end


# ---------------------------------------------------------------- s160 bank_first
EXACT_MIN_S160 = 0.97               # his words are the example itself (her name and small spelling marks aside)


def exact_answer_s160(said, actions):
    """The bank's answer when his words are one of its examples; None otherwise (the model decides)."""
    global OFFLINE_MIN_S157
    keep = OFFLINE_MIN_S157
    OFFLINE_MIN_S157 = EXACT_MIN_S160
    try: return offline_answer_s157(said, actions)
    finally: OFFLINE_MIN_S157 = keep
# ---------------------------------------------------------------- s160 end

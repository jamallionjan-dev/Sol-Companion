"""The farm orders the Mind catches itself, and every sentence she says about the farm.
The game reports numbers and item types; the words are here, in Levantine, and an item always keeps the name the game shows.
The language model never starts farm work and never states a farm fact: orders are decided here before any model is asked."""
import json, random, re, time

_POLITE = r"(?:(?:يا\s+)?سول|يلا|لو سمحتي|لو سمحت|من فضلك|بليز|زكات[كم]|زكاتكي|الله يخليك[ي]?|يخليك[ي]?|شو رايك)"
_DIAC = re.compile(r"[ً-ٰٟۖ-ۭ]")
def norm(text):
    t = _DIAC.sub("", str(text or ""))
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي").replace("ة", "ه")
    t = re.sub(r"[.،؟!,?؛]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^(?:" + _POLITE + r"\s+)+", "", t + " ").strip()
    return re.sub(r"(?:\s+(?:" + _POLITE + r"))+$", "", t).strip()

_FARM_WORD = r"(?:ال)?(?:مزرع[هت]|زراعه|زرع(?:ه)?|مزروعات|حقل|محصول|محاصيل|نباتات|ارض)"
_AWAY = r"(?:بغيابي|بغيبتي|وانا غايب|لما اغيب|وقت اغيب|لما اروح|لحين ارجع|لحتي ارجع|بدوني|عني)"
KEEPER_RX = re.compile(
    r"دبريلي\s+(?:ال)?(?:ارض|مزرعه|زرع)|"
    r"(?:(?:^|\s)و?دبر(?:ي)?\s+(?:امر\s+|حال\s+)?" + _FARM_WORD + r"(?:\s+" + _AWAY + r")?"
    r"|(?:^|\s)و?(?:ا?هتمي|ا?هتم|اعتني|اعتم[يا]|ديري بالك|دير[ي]? بال[كه]|راعي|تولي امر)\s+(?:ب|عل[يا]\s+|عال)?" + _FARM_WORD + r"(?:\s+" + _AWAY + r")?"
    r"|(?:^|\s)و?(?:ا?شتغلي|ا?شتغل|ا?بلشي|ابدي)\s+(?:ب|في\s+|عل[يا]\s+|عال?)?" + _FARM_WORD + r"(?:\s+" + _AWAY + r")?"
    r"|" + _FARM_WORD + r"\s+(?:عليكي|عليك)\s+" + _AWAY + r")"
)
HOME_RX = re.compile(
    r"(?:^|\s)و?(?:ضل[ي]?|ظل[ي]?|ابقي|خليك[ي]?|خلكي|استني|ضليت[ي]?)\s+(?:هون\s+|ا?رتاحي\s+|ريحي\s+)?(?:ب|في\s+|فال|عل[يا]\s+)?(?:ال)?(?:بيت|دار|منزل|قاعده)\b"
    r"|(?:^|\s)و?(?:ا?رتاحي|ريحي|استريحي|نامي|اتريحي)\s+(?:ب|في\s+|عال?)?(?:ال)?(?:بيت|دار|منزل|قاعده)\b"
)
HOME_REST_WORD = re.compile(r"(?:ا?رتاحي|ريحي|استريحي|نامي|اتريحي|ارتاحي شوي)")
_TO_FARM = r"(?:لل|ل|عال?|عل[يا]\s+)?" + _FARM_WORD
_THEM = r"(?:ها|هن|هم)?"
WATER_RX = re.compile(r"^(?:ا|ت)?سقي" + _THEM + r"(?:\s+" + _FARM_WORD + r")?\s*$")
HARVEST_RX = re.compile(r"^(?:(?:ا|ت)?حصدي?|(?:ا|ت)?قطفي|(?:لمي|ا?جمعي|تجمعي)(?=\s+" + _FARM_WORD + r"))" + _THEM + r"(?:\s+(?:" + _FARM_WORD + r"|(?:ال)?حصاد|النضج|اللي نضج|الي نضج|الجاهز|كله))?\s*$")
CURE_RX = re.compile(r"^ت?(?:عالجي|داوي|رشي)" + _THEM + r"(?:\s+" + _FARM_WORD + r")?(?:\s+من\s+\S+(?:\s+\S+)?)?\s*$")
COMPOST_RX = re.compile(r"^(?:(?:ا|ت)?سمدي" + _THEM + r"(?:\s+" + _FARM_WORD + r")?|ت?(?:حطي|ضيفي)\s+(?:" + _TO_FARM + r"\s+)?سماد(?:\s+" + _TO_FARM + r")?)\s*$")
_WEEDS = r"(?:ال)?(?:عشب|اعشاب|حشيش)"
_CLEAN = r"ت?(?:نظفي|نضفي|نتشي|عشبي|ا?قلعي|شيلي)"
WEED_RX = re.compile(r"^" + _CLEAN + r"\s+(?:" + _FARM_WORD + r"(?:\s+من\s+" + _WEEDS + r")?|" + _WEEDS + r"(?:\s+(?:من\s+)?" + _TO_FARM + r")?)\s*$")
PLOW_RX = re.compile(r"^(?:ا|ت)?(?:حرثي|فلحي)" + _THEM + r"(?:\s+" + _FARM_WORD + r")?\s*$")
SEEDS_WORD = re.compile(r"[بي]ذور|بزور|بذار|موسم")
PLANT_RX = re.compile(r"(?:^|\s)(?:ا|ت)?زرعي\s*(?P<crop>.*)$")
_SHORT_FOR = r"(?:للزراعه|للمزرعه|بالمزرعه|من المزرعه|زراعه)"
SHORT_RX = re.compile(r"(?:شوف(?:ي)?\s+)?(?:شو|ايش|ماذا)\s+(?:ناقص(?:نا|ني)?(?:\s+" + _SHORT_FOR + r")?|(?:لازم(?:نا|ني)?|بدنا|نحتاج)\s+" + _SHORT_FOR + r")\s*$")
STOP_RX = re.compile(r"^(?:خلص(?:ي)?\s+)?(?:خلص زراعه|وقفي زراعه|وقفي(?:\s+شغل)?\s+" + _FARM_WORD + r")\s*$")
_DRIVING = re.compile(r"(?:^|\s)(?:سوقي|قودي|خذيني|خديني|وصليني|اركبي|انزلي|زمري)(?:\s|$)")
TRY_RX = re.compile(r"^sol_farm_try\s+([a-z_]+)\s*$")
PROVEN_RX = re.compile(r"^(?:شو|ايش)\s+(?:(?:ال|الي|اللي)\s*)?(?:زبط|نجح|جربتي|اشتغل)(?:\s+معك)?(?:\s+ب(?:ال)?(?:زراعه|مزرعه))?\s*$")
FORGET_TRIES_RX = re.compile(r"^(?:انسي|امسحي)\s+(?:التجارب|تجارب(?:\s+(?:ال)?زراعه)?|اللي\s+جربتيه)\s*$")
NOTHING_ON = {"plant": "ما في أرض فاضية أزرعها هلأ.", "plow": "ما في أرض بدها فلاحة هلأ.", "harvest": "ما لقيت زرعة بدها حصاد هلأ.", "water": "ما لقيت زرعة عطشانة هلأ.", "cure": "ما لقيت زرعة مريضة هلأ.", "weed": "ما لقيت زرعة فيها عشب هلأ.",
              "compost": "ما لقيت زرعة بدها سماد هلأ.", "sow": "ما لقيت أرض محروثة فاضية هلأ.", "replant": "ما لقيت زرعة ميتة أبدلها هلأ."}
TRY_NAME = {"plant": "الزرع", "harvest": "الحصاد", "water": "السقاية", "cure": "العلاج", "weed": "قلع العشب", "compost": "التسميد", "plow": "الحراثة", "sow": "البذر", "replant": "إعادة الزرع"}


def trial_line(op, r):
    """What a one-action test answered, in her words."""
    name = TRY_NAME.get(op, op)
    reason = str((r or {}).get("reason") or "")
    if isinstance(r, dict) and r.get("ok"): return "عم جرب %s هلأ." % name
    if reason == "nothing_to_try_on": return NOTHING_ON.get(op, "ما لقيت شي أجرب عليه %s هلأ." % name)
    if reason.startswith("no_free_tile_known_yet"): return "لسا عم دور على أرض فاضية، قلي كمان مرة بعد شوي."
    if reason == "no_seed_in_season_to_try": return "ما في بذور بموسمها أجرب فيها."
    if reason == "sol_not_available": return "مو قريبة هلأ لأجرب."
    return "ما قدرت أجرب %s هلأ." % name


def proven_line(reason):
    """What she has tried so far, in words."""
    try: done = json.loads(str(reason).split(":", 1)[1]) or {}
    except (ValueError, IndexError): done = {}
    if not isinstance(done, dict) or not done: return "لسا ما جربت شي من شغل الزراعة."
    good = [TRY_NAME.get(k, k) for k, v in done.items() if isinstance(v, dict) and (v.get("vanilla") == "ok" or v.get("fallback") == "applied")]
    bad = [TRY_NAME.get(k, k) for k, v in done.items() if isinstance(v, dict) and not (v.get("vanilla") == "ok" or v.get("fallback") == "applied")]
    parts = []
    if good: parts.append("زبط معي: %s." % "، ".join(good))
    if bad: parts.append("ما زبط لسا: %s." % "، ".join(bad))
    return " ".join(parts)
STORAGE_RX = re.compile(r"(?:(?:جهز|سجل|رتب|اعتمد)(?:ي)?\s+(?:مخازن|مخزن|المخازن|المخزن|التخزين)(?:\s+المزرعه|\s+الزراعه)?|شوفي وين نخزن)")
STATUS_RX = re.compile(r"(?:شو|شنو|ايش)\s+(?:عم|عما)\s+(?:تعملي|تساوي|تعمل|تسوي)|ليش\s+(?:وقفتي|وقفت|ما\s+عم\s+تشتغلي|مو\s+شغال\S*|ما\s+زرعتي|ما\s+سقيتي)|وينك\s+بالمزرعه")

CROPS = (
    (("بندوره", "طماطم", "tomato"), "Tomato"), (("بطاطا", "بطاطس", "potato", "potatoes"), "Potatoes"), (("جزر", "carrot", "carrots"), "Carrots"),
    (("ملفوف", "كرنب", "cabbage", "cabbages"), "Cabbages"), (("خس", "lettuce"), "Lettuce"), (("بصل", "onion", "onions"), "Onion"), (("ثوم", "garlic"), "Garlic"),
    (("فلفل", "bell pepper", "bellpepper"), "BellPepper"), (("بروكلي", "broccoli"), "Broccoli"), (("قرنبيط", "زهره", "cauliflower"), "Cauliflower"), (("ذره", "corn"), "Corn"),
    (("خيار", "cucumber"), "Cucumber"), (("قرع", "pumpkin"), "Pumpkin"), (("كوسا", "zucchini"), "Zucchini"), (("بطيخ", "watermelon"), "Watermelon"), (("سبانخ", "spinach"), "Spinach"),
    (("فجل", "radish", "radishes"), "Radishes"), (("لفت", "turnip"), "Turnip"), (("بازلاء", "بازيلا", "peas", "greenpeas"), "Greenpeas"), (("فول الصويا", "صويا", "soybeans"), "Soybeans"),
    (("فريز", "فراوله", "strawberry"), "Strawberryplant"), (("قمح", "wheat"), "Wheat"), (("شعير", "barley"), "Barley"), (("ساق", "kale"), "Kale"),
)
def crop_id(word):
    w = norm(word).lower()
    for names, crop in CROPS:
        if any(n in w for n in names): return crop
    return None

def order(text):
    """(option for sol_farm, or (action, option)) when this message is a farm order; None otherwise. Nothing else in the sentence matters."""
    t = norm(text)
    if not t: return None
    m = TRY_RX.match(t)
    if m: return ("sol_farm_try", m.group(1))
    if PROVEN_RX.match(t): return ("sol_farm", "proven")
    if FORGET_TRIES_RX.match(t): return ("sol_farm", "forget")
    if _DRIVING.search(t): return None                                     # a driving order is never a farm order, whatever else the sentence says
    keeper = KEEPER_RX.search(t) is not None
    home = HOME_RX.search(t) is not None and (HOME_REST_WORD.search(t) is not None or re.search(r"(?:ضل[ي]?|خليك[ي]?|ابقي|ظل[ي]?).*(?:بيت|دار|منزل)", t) is not None)
    if keeper and home: return ("sol_farm", "both")
    if keeper: return ("sol_farm", "keeper")
    if home: return ("sol_farm", "home")
    if STOP_RX.match(t): return ("sol_farm", "stop")
    if STORAGE_RX.search(t): return ("sol_farm", "storage")
    if SHORT_RX.search(t): return ("sol_farm", "short")
    if WATER_RX.match(t): return ("sol_farm", "water")
    if HARVEST_RX.match(t): return ("sol_farm", "harvest")
    if CURE_RX.match(t): return ("sol_farm", "cure")
    if COMPOST_RX.match(t): return ("sol_farm", "compost")
    if WEED_RX.match(t): return ("sol_farm", "weed")
    if PLOW_RX.match(t): return ("sol_farm", "plow")
    m = PLANT_RX.search(t)
    if m:
        crop = re.sub(r"\b(?:بهالقطعه|هون|بالمزرعه|عالارض|بالارض)\b", "", m.group("crop")).strip()
        if not crop or (SEEDS_WORD.search(crop) and not crop_id(crop)): return ("sol_farm", "plant:any")
        return ("sol_farm", "plant:" + (crop_id(crop) or ("unknown:" + crop)))
    return None

def is_status_question(text): return STATUS_RX.search(norm(text)) is not None
WHEN_RX = re.compile(r"(?:شو|شنو)\s+زرعتي|(?:ايمت|امتي|وقتيش|كيف)\s+.*(?:الزرع|المزروعات|الموسم|ينضج|تنضج|رح يجهز|يجهز)")
def is_due_question(text): return WHEN_RX.search(norm(text)) is not None

# ---------------------------------------------------------------- names
def _days(n):
    import sol_templates as TPL
    return ("%d %s" % (n, TPL.days_word(n))) if n != 2 else TPL.days_word(2)
def _name(full):
    import chat_service as CS
    return CS.item_name(full)
def crop_name(crop, names=None):
    """"Tomato" -> the name the game shows for what the crop gives."""
    full = (names or {}).get(crop) or ("Base." + str(crop))
    return _name(full)

# ---------------------------------------------------------------- lines
ACK = {
    "water": ("تكرم، رايحة أسقي.", "ماشي، بسقيهن هلأ."),
    "harvest": ("حاضر، رايحة أحصد.", "ماشي، بحصد اللي جاهز."),
    "keeper": ("ماشي، المزرعة عندي، روح وأنا بدبرها.", "تكرم، بدبر المزرعة لحين ترجع."),
    "home": ("ماشي، بضل بالبيت وبرتاح.", "تكرم، بالبيت وبرتاح وبس تحتاجني ناديني."),
    "plant": ("تكرم، بزرع هلأ.", "ماشي، رايحة أزرع."),
    "cure": ("تكرم، رايحة عالج الزرع.", "ماشي، بعالج اللي مريض."),
    "compost": ("تكرم، بحط سماد للزرع.", "ماشي، رايحة سمّد."),
    "weed": ("تكرم، بنظف الزرع من العشب.", "ماشي، رايحة نتش العشب."),
    "plow": ("تكرم، رايحة أفلح الأرض.", "ماشي، بفلح هلأ."),
    "both": ("ماشي، بضل بالبيت وبدبر المزرعة، وبرتاح لما بدي.", "تكرم، المزرعة عندي وأنا بالبيت."),
    "stop": ("ماشي، وقفت.", "تكرم، تركت الشغل."),
}
def ack(opt):
    cmd = str(opt or "").split(":", 1)[0]
    return random.choice(ACK.get(cmd) or ("ماشي.",))

OP_DOING = {"home": "راجعة عالبيت", "return": "عم رجع الأغراض لمحلها", "harvest": "عم بحصد", "water": "عم بسقي", "cure": "عم بعالج النبات من الآفة", "weed": "عم بنتش العشب", "sow": "عم بزرع", "replant": "عم بزرع مكان اللي مات",
            "plow": "عم بفلح أرض جديدة", "compost": "عم بسمّد", "carry": "عم بنقل المحصول عالمخزن"}
NEED_DOING = {"health": "عم بضمد جروحي", "food": "جوعانة أو عطشانة، باكل وبشرب", "hygiene": "عم بتحمم وبغير تيابي", "rest": "تعبانة، عم برتاح"}
WHY_AR = {
    "body_busy": "كنت مشغولة بشي تاني وما قدرت أوصل", "target_unloaded": "المكان بعيد عنك وما بقدر أوصلو هلأ",
    "no_can": "ما عندي Watering Can أستعير من المخزن", "unsure_can": "مو متأكدة إذا عندنا Watering Can، في خزانة بعيدة مو واصلتها",
    "rain": "عم تشتي، السقي برّا ما له داعي", "dark": "الدنيا عتمة، الشغل برّا مو أمان",
    "near_player": "إنت واقف جنب هالقطعة، بستنى لتبعد شوي", "no_food_storage": "ما لقيت مكان فيه فراغ أحط فيه المحصول",
    "no_home": "ما بعرف وين البيت، قلي هون البيت بالأول", "base_missing": "ما في قطعة زراعة مسجلة", "already_acting": "لسا بإيدي شغلة، خلصها وبرجع", "no_intent": "ما عرفت شو المطلوب بالضبط", "lf_unavailable": "مو قادرة أتحرك هلأ", "store_unavailable": "ذاكرة المزرعة مو جاهزة هلأ", "unknown_farm_order": "هيدا الطلب ما بعرفه بالمزرعة", "act_unavailable": "الشغل مو جاهز هلأ", "report_failed": "ما قدرت أقرا المزرعة هلأ", "walking_unavailable": "مو قادرة أمشي هلأ", "walk_error": "ما قدرت أمشي لهونيك",
    "no_path": "ما لقيت طريق أوصل منه", "bag_full": "شنتتي مليانة، لازم فضيها أول", "body_lost": "انقطع الشغل وما كملت", "in_vehicle": "أنا بالسيارة، لازم انزل أول",
    "no_seed": "ما في بذور بالموسم بالمخزن", "unsure_seed": "مو متأكدة من البذور، في خزانة مو واصلتها", "no_tool": "ما عندي أداة حفر بالمخزن", "unsure_tool": "مو متأكدة من الأدوات، في خزانة مو واصلتها",
    "unsure_spray": "مو متأكدة من المبيد، في خزانة مو واصلتها", "unsure_fert": "مو متأكدة من السماد، في خزانة مو واصلتها",
    "storage_full": "مخازن المحصول مليانة", "storage_unloaded": "مخزن المحصول مو واصلتله", "carry_no_path": "ما لقيت طريق لمخزن المحصول",
    "no_fert": "ما عندنا سماد", "winter": "الشتا مو وقت سماد", "paused": "في قطعة وقفت عليها بعد ما فشلت كذا مرة", "unclearable_weeds": "في عشب مو طالع من شجرة أو شوك، ما بقدر أشيله",
    "farm_supply_missing": "الغرض اللي بدي ياه مو بالمخزن", "farm_food_storage_missing": "ما في مخزن أكل مسجل", "farm_output_storage_missing": "ما في مخزن أحط فيه المحصول",
    "water_source_missing": "ما لقيت مصدر مي قريب أعبي منه", "farm_action_timeout": "الشغلة طولت كتير وتركتها", "unsafe_area": "المنطقة مو أمان، في زومبي قريب",
    "farm_outside_night": "نزل الليل، ما بشتغل برّا", "farm_plot_missing": "الزرعة اللي كنت جاية عليها مو موجودة", "farm_plant_changed": "الزرعة تغيرت قبل ما أوصل",
    "no_effect": "جربت وما تغيرت الزرعة", "timeout": "الشغلة علقت", "farm_action_fallback_failed": "ما زبطت معي الشغلة",
}
def why_ar(reason):
    r = str(reason or "")
    if r.startswith("no_spray:"): return "ما عندي %s" % _name(r[9:])
    if r.startswith("no_seed:"): return "ما عندي بذور %s بالموسم" % _name("Base." + r[8:])
    if r.startswith("no_fallback:"): return "هالشغلة ما بعرف أعملها"
    return WHY_AR.get(r) or "صار شي ومنعني كمل"

def status_line(s):
    """"What are you doing?" - from what the game says she is doing right now."""
    if not isinstance(s, dict): return "لسا ما بعرف، لحظة."
    st, det = s.get("status"), s.get("detail")
    if st == "doing": return OP_DOING.get(det, "عم بشتغل بالمزرعة") + "."
    if st == "home": return "أنا بالبيت وعم برتاح."
    if st == "needs": return NEED_DOING.get(det, "عم دير بالي على حالي") + "."
    if st == "waiting": return "واقفة: %s." % why_ar(det)
    if st == "idle": return "ما في شغل بالمزرعة هلأ، كلشي تمام."
    if st == "scanning": return "عم شوف المزرعة، لحظة."
    if st == "stopped" or not st: return "ما عندي شغل بالمزرعة هلأ."
    if st == "finished": return "خلصت، ما ضل شي."
    return "عم بشتغل بالمزرعة."

# ---------------------------------------------------------------- far_work: what she did while he was away, one short line
# (one, two, three to ten, eleven and up) as people say them
FAR_CROP_AR = {
    "Base.Carrots": ("جزرة وحدة", "جزرتين", "جزرات", "جزرة"),
    "Base.Tomato": ("حبة بندورة", "حبتين بندورة", "حبات بندورة", "حبة بندورة"),
    "Base.Potato": ("حبة بطاطا", "حبتين بطاطا", "حبات بطاطا", "حبة بطاطا"),
    "Base.Cabbage": ("ملفوفة وحدة", "ملفوفتين", "ملفوفات", "ملفوفة"),
    "Base.Broccoli": ("راس بروكلي", "راسين بروكلي", "روس بروكلي", "راس بروكلي"),
    "Base.Cauliflower": ("راس زهرة", "راسين زهرة", "روس زهرة", "راس زهرة"),
    "Base.RedRadish": ("فجلة وحدة", "فجلتين", "فجلات", "فجلة"),
    "Base.Strewberrie": ("حبة فريز", "حبتين فريز", "حبات فريز", "حبة فريز"),
    "Base.Spinach": ("ضمة سبانخ", "ضمتين سبانخ", "ضمات سبانخ", "ضمة سبانخ"),
    "Base.Leek": ("ضمة كراث", "ضمتين كراث", "ضمات كراث", "ضمة كراث"),
    "Base.SugarBeet": ("شمندرة وحدة", "شمندرتين", "شمندرات", "شمندرة"),
}
FAR_SHORT_AR = {"water": "بس خلصت المي", "seed": "بس خلصوا البذور", "storage": "بس ما لقيت محل للمحصول", "fert": "بس خلص السماد", "spray": "بس خلص الدوا"}
def _far_count(n, forms):
    one, two, few, many = forms
    if n == 1: return one
    if n == 2: return two
    if n <= 10: return "%d %s" % (n, few)
    return "%d %s" % (n, many)
def _far_crop(full, n):
    forms = FAR_CROP_AR.get(full)
    if forms is None:
        nm = _name(full)
        forms = ("حبة %s" % nm, "حبتين %s" % nm, "حبات %s" % nm, "حبة %s" % nm)
    return _far_count(n, forms)
def far_report_line(d):
    """While he was away: watering, picking, sowing, spraying, feeding, and what ran out. Numbers only from the game."""
    if not isinstance(d, dict): return None
    parts = []
    rounds = int(d.get("rounds") or 0)
    if rounds: parts.append("سقيت الزرع" + ("" if rounds == 1 else (" مرتين" if rounds == 2 else (" %d مرات" % rounds if rounds <= 10 else " %d مرة" % rounds))))
    picked = [h for h in (d.get("harvest") or []) if isinstance(h, dict) and int(h.get("n") or 0) > 0][:2]
    if picked: parts.append("قطفت " + " و".join(_far_crop(h.get("veg"), int(h["n"])) for h in picked))
    if d.get("floor"): parts.append("حطيت الزيادة عالأرض جنب المخزن لأنو امتلى")
    sown = int(d.get("sown") or 0)
    if sown: parts.append("زرعت " + _far_count(sown, ("تلم", "تلمين", "أتلام", "تلم")))
    if int(d.get("cured") or 0): parts.append("رشيت الزرع المريض")
    if int(d.get("fed") or 0): parts.append("حطيت سماد")
    got = set(d.get("short") or [])
    short = [FAR_SHORT_AR[s] for s in ("water", "seed", "storage", "spray", "fert") if s in got][:1]      # the one that matters most
    if not parts and not short: return None
    if not parts: return "ما قدرت أعمل كتير، " + short[0][3:] + "."
    line = parts[0] + "".join(" و" + p for p in parts[1:4])
    if short: line += "، " + short[0]
    return line + "."

def stop_line(stop):
    """Why she stopped or could not go on, once: the Mind says it and the game has already limited how often."""
    if not isinstance(stop, dict): return None
    d = stop.get("detail") or {}
    r = stop.get("reason")
    if r == "paused": return "تركت قطعة وحدة من المزرعة بعد كذا محاولة: %s." % why_ar(d.get("why"))
    if r == "blocked": return "وقفت: %s." % why_ar(d.get("why"))
    if r == "waiting": return why_ar(d.get("why")) + "."
    if r == "unclearable_weeds": return "في عشب عند شجرة أو شجيرة، ما بقدر أشيله."
    if r == "done": return "خلصت %s." % TRY_NAME.get(d.get("kind"), "الشغل")
    if r == "home_arrived": return "وصلت عالبيت."
    if r == "far_report": return far_report_line(d)
    return None

def report_text(report):
    """The farm per zone, what is ready, thirsty, sick, dead, empty, weeds and what is short. Only what the game sent."""
    if not isinstance(report, dict) or not report.get("zones"): return "ما في منطقة زراعة مسجلة، حددها إلي بالأول."
    names = report.get("names") or {}
    parts = []
    total = len(report["zones"])
    for i, z in enumerate(report["zones"], 1):
        label = "المزرعة" if total == 1 else ("القطعة %d" % i)
        if z.get("unread"): parts.append("%s لسا ما قريتها." % label); continue
        bits = []
        alive, n = z.get("alive") or 0, z.get("n") or 0
        if n == 0: bits.append("فاضية")
        else: bits.append("%d نبتة حيّة%s" % (alive, " من %d" % n if n != alive else ""))
        if z.get("ripe"):
            ripe = [c for c in z.get("crops") or [] if c.get("ripe")]
            bits.append("%d جاهز للقطف (%s)" % (z["ripe"], "، ".join("%s %d" % (crop_name(c["crop"], names), c["ripe"]) for c in ripe)))
        if z.get("thirsty"): bits.append("%d عطشانة" % z["thirsty"])
        p = z.get("pests") or {}
        pests = [("عفن", "mildew"), ("دبان", "flies"), ("من", "aphid"), ("بزاق", "slugs")]
        got = ["%s على %d" % (ar, p[k]) for ar, k in pests if p.get(k)]
        if got: bits.append("فيها " + "، ".join(got))
        if z.get("weeds"): bits.append("%d فيها عشب" % z["weeds"])
        if z.get("dead"): bits.append("%d ميتة" % z["dead"])
        if z.get("empty"): bits.append("%d محروثة وفاضية" % z["empty"])
        parts.append("%s: %s." % (label, "، ".join(bits)))
    stock = report.get("stock") or {}
    seeds = stock.get("seeds") or {}
    if seeds: parts.append("البذور بالمخزن: %s." % "، ".join("%d %s" % (n, _seed_name(c, report.get("seedNames"))) for c, n in sorted(seeds.items()) if n > 0))
    fert = int(stock.get("compost") or 0) + int(stock.get("fert") or 0)
    if fert: parts.append("والسماد عندنا %d." % fert)
    if stock.get("ready") is False:
        parts.append("لسا عم اتفقد المخازن.")
    elif not seeds and not fert:
        parts.append("مو متأكدة من البذور والسماد، في خزانة مو واصلتها." if (stock.get("unsure") or {}) else "ما في بذور ولا سماد بالمخازن.")
    if report.get("shortages") and stock.get("ready") is not False: parts.append(shortages_text(report["shortages"]))
    stop = stop_line(report.get("stop"))
    if stop: parts.append(stop)
    return " ".join(parts)

def _seed_name(crop, seed_names):
    full = (seed_names or {}).get(crop) or ("Base.%sSeed" % crop)
    return _name(full)

def shortages_text(rows):
    """Exact item names, how many she needs and has, and "not sure" when a store is not loaded."""
    if not rows: return "ما ناقصنا شي للزراعة هلأ."
    missing, unsure, stores = [], [], []
    for r in rows:
        if r.get("storage"): (unsure if r.get("unsure") else stores).append("مكان فيه فراغ للأكل" if r["storage"] == "food" else "مكان للمحصول"); continue
        if r.get("seedChoices") is not None:
            names = "، ".join(_name(s) for s in r["seedChoices"][:3]) or "بذور بالموسم"
            text = "%s (بدنا %d، عنا %d)" % (names, r.get("need", 0), r.get("have", 0))
        else:
            alts = r.get("alt") or [r.get("full")]
            text = "%s (بدنا %d، عنا %d)" % (" أو ".join(_name(a) for a in alts if a), r.get("need", 0), r.get("have", 0))
        (unsure if r.get("unsure") else missing).append(text)
    parts = []
    if missing: parts.append("ناقصنا: %s." % "، ".join(missing))
    if stores: parts.append("وما عنا: %s." % "، ".join(stores))
    if unsure: parts.append("ومو متأكدة من: %s، في خزانة مو واصلتها." % "، ".join(unsure))
    return " ".join(parts) or "ما ناقصنا شي للزراعة هلأ."

def storage_line(reason):
    """storage:<scan line>#<apply line>: what she found and registered, and what is still missing."""
    text = str(reason or "")
    scan, _, applied = text.partition("#")
    regs = re.search(r"regs=([^;]*)", scan)
    regs = [] if regs is None else [x for x in regs.group(1).split("|") if x]
    done = dict((m[0], m[1]) for m in re.findall(r"(zones|regs)=(\d+/\d+)", applied))
    cats = {x.split("@")[0] for x in regs}
    miss = []
    labels = {"farming": "خزانة للبذور والأدوات", "tools": "خزانة أدوات", "water": "مخزن مي", "output": "مخزن محصول", "food": "مخزن أكل"}
    have = re.search(r"cls=([^;]*)", scan)
    known = have.group(1) if have else ""
    for cat, label in labels.items():
        if cat not in cats: miss.append(label)
    bits = []
    if done:
        zones = int(done.get("zones", "0/0").split("/")[0] or 0)
        bits.append("سجلت %s مخزن للمزرعة، وصرت أقدر آخد منهم." % done.get("regs", "0/0").split("/")[0])
        bits.append("وسجلت %d قطعة أرض جديدة." % zones if zones else "والمزرعة نفسها كانت مسجلة من قبل.")
    if not regs and "apply" not in text: bits.append("ما لقيت مخازن أضيفها.")
    if miss: bits.append("ما لقيت: %s." % "، ".join(miss))
    return " ".join(bits) or "تمام، المخازن جاهزة."

def reply_for(option, result):
    """The sentence for one farm order, built from what the game answered."""
    cmd = str(option or "").split(":", 1)[0]
    if not isinstance(result, dict) or result.get("ok") is None: return "لحظة، ما وصلني شي."
    why = str(result.get("reason") or "")
    if result.get("ok") is False:
        if why == "base_missing": return "ما في قاعدة مسجلة، حددها إلي بالأول."
        if why == "switched_off": return "لسا هالشغلة مو مفتوحة عندي."
        if why.startswith("storage:"): return "ما قدرت أشوف المخازن هلأ."
        if why == "sol_not_available": return "مو قادرة هلأ."
        return "ما قدرت: %s." % why_ar(why)
    if why.startswith("single:") and why.split(":")[2:3] == ["none"]:
        blocked = ":".join(why.split(":")[3:])
        return why_ar(blocked) + "." if blocked else NOTHING_ON.get(cmd, "ما في شي بدو شغل هلأ.")
    if cmd == "home" and why.endswith(":going"): return random.choice(("ماشي، راجعة عالبيت وبرتاح هناك.", "تكرم، رايحة عالبيت."))
    if cmd in ("short", "storage") and why == "not_ready": return "لسا عم اتفقد المخازن، اسألني كمان شوي."
    if cmd == "storage": return storage_line(why[8:] if why.startswith("storage:") else why)
    if cmd in ("short",):
        rows = json.loads(why.split(":", 1)[1]) if ":" in why else []
        return shortages_text(rows)
    if cmd == "plant" and "unknown:" in str(option): return "ما بعرف هالزرعة، قولها بالاسم يلي منعرفو."
    if cmd == "stop": return random.choice(ACK["stop"]) if why == "stopped" else "ما كان عندي شغل بالمزرعة."
    if cmd == "try": return why
    if cmd == "home" and "farmhome" in why: return random.choice(ACK["both"])
    if cmd in ACK: return ack(option)
    return "تكرم."

# ---------------------------------------------------------------- memory and warnings
SEASON_END = ("موسم %s عم يخلص، عنا بذرها.",)
SEASON_SOON = ("الشهر الجاي بيفتح موسم %s، خلي البذر جاهز.",)
READY = ("%s جاهزة للقطف.", "صار في %s بدها قطف.")
THIRSTY = ("المزرعة عطشانة، %d نبتة بدها سقي.",)

class FarmMemory:
    """The Mind keeps per world what she planted and when due; the game's snapshot refreshes it, a death empties it."""
    def __init__(self, mem): self.mem = mem
    @property
    def data(self):
        d = self.mem.data.get("farm")
        if not isinstance(d, dict): d = self.mem.data["farm"] = {}
        return d
    def forget(self): self.mem.data["farm"] = {}
    def note(self, snap_farm):
        """What she knows now about what she planted and when it is due."""
        d = self.data
        changed = False
        due = {}
        for row in (snap_farm or {}).get("due") or []:
            due["%s|%s" % (row.get("zone"), row.get("crop"))] = {"crop": row.get("crop"), "veg": row.get("veg"), "hours": row.get("hours")}
        if due != d.get("due"): d["due"] = due; changed = True
        sown = (snap_farm or {}).get("sown") or []
        if sown != d.get("sown"): d["sown"] = sown; changed = True
        return changed
    def due_text(self):
        d = self.data
        rows = sorted((d.get("due") or {}).values(), key=lambda r: r.get("hours") or 0)
        if not rows: return "ما زرعت شي لسا."
        parts = []
        for r in rows[:6]:
            days = max(0, round((r.get("hours") or 0) / 24.0))
            name = _name(r["veg"]) if r.get("veg") else str(r.get("crop"))
            parts.append("%s بعد %s" % (name, _days(days)) if days else "%s جاهزة قريب" % name)
        return "زرعنا، و" + "، ".join(parts) + "."
    def warnings(self, snap_farm, now=None, cooldown=1800):
        """What she should tell him without being asked, at most one each per half hour."""
        now = now if now is not None else time.time()
        d = self.data
        warned = d.get("warned")
        if not isinstance(warned, dict): warned = d["warned"] = {}
        out = []
        def fire(key, line):
            if len(out) < 3 and now - warned.get(key, 0) >= cooldown:
                warned[key] = now; out.append(line)
        if not isinstance(snap_farm, dict): return out
        names = {r.get("crop"): r.get("veg") for r in snap_farm.get("due") or [] if r.get("veg")}
        ripe_by_crop = {}
        for z in snap_farm.get("zones") or []:
            for c in z.get("crops") or []:
                if c.get("ripe"): ripe_by_crop[c["crop"]] = ripe_by_crop.get(c["crop"], 0) + c["ripe"]
        for crop in sorted(ripe_by_crop):
            fire("ready:" + crop, random.choice(READY) % crop_name(crop, names))
        thirsty = int(snap_farm.get("thirsty") or 0)
        if thirsty and not snap_farm.get("raining"): fire("thirsty", THIRSTY[0] % thirsty)
        for row in snap_farm.get("season") or []:
            name = _name(row.get("seed") or "Base.%s" % row.get("crop"))
            fire("season:%s:%s" % (row.get("kind"), row.get("crop")), (SEASON_END if row.get("kind") == "ending" else SEASON_SOON)[0] % name)
        return out

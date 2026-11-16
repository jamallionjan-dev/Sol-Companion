"""Natural-language goal recognition for Sol Mind.

Layering is deliberate:
1) deterministic high-confidence safety/emergency intents run without any model;
2) provider/ChatGPT can submit the same structured goal schema for semantic requests;
3) legacy one-step action parsing remains a fallback in chat_service.

Adding a future goal means registering a planner in goal_engine and exposing its name here;
no parser rewrite is required.
"""
import re
import time

GOAL_VERSION = 1
# The one list of Sol's multi-step goals. Whatever model connects (any provider, or ChatGPT through Sol Link) is told
# from here what it can ask for, so a new goal needs one entry here plus its planner in goal_engine.
GOALS = {
    "emergency_rescue": {
        "when": "اللاعب بخطر أو طلب منك تجيه تساعديه أو تنقذيه أو تاخديه عالبيت، حتى لو كان بعيدًا: تسوقين إليه، تحمينه، ثم تعيدينه للبيت إن عُرف البيت",
        "tag": "[هدف: emergency_rescue | player أو marker | home_if_known أو home أو none]",
    },
    "errand_round_trip": {
        "when": "اللاعب طلب مشوارًا تذهبين فيه وحدك بالسيارة إلى البيت أو العلامة أو مكان محفوظ، تنجزين المهمة ثم ترجعين إليه.",
        "tag": "[هدف: errand_round_trip | home أو marker | unload أو none]",
    },
    "fetch_player": {
        "when": "اللاعب طلب أن تأتي إليه بالسيارة، وربما أن تأخذيه إلى البيت، دون خطر عليه.",
        "tag": "[هدف: fetch_player | stay_with_player أو take_player_home]",
    },
    "home_errand": {
        "when": "اللاعب طلب تفضية أغراض السيارة بالبيت: تسوقين وحدك لموقف القاعدة، تفرغين صندوق السيارة، ثم ترجعين لمكان اللاعب. يحتاج قاعدة فيها موقف سيارات ومخزن، وسيارة قريبة منك",
        "tag": "[هدف: home_errand]",
    },
    "refuel_errand": {
        "when": "اللاعب طلب تعبئة السيارة أو الغالون بنزين: تأخذين سيارة وتذهبين لأقرب كازية تتذكرينها، تعبئين، ثم ترجعين إليه. بدون سيارة تمشين وتعبئين الغالون فقط",
        "tag": "[هدف: refuel_errand | car أو can أو both | car أو foot]",
    },
    "station_query": {
        "when": "اللاعب يسأل فقط أين أقرب كازية أو محطة بنزين، دون أن يطلب الذهاب: تجيبينه وتعلّمينها على الـ GPS",
        "tag": "[هدف: station_query]",
    },
}
SUPPORTED = tuple(GOALS)

_AR_DIAC = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")

def _norm(text):
    t = _AR_DIAC.sub("", str(text or "").lower())
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
    return re.sub(r"\s+", " ", t).strip()

_DISTRESS = (
    "محاصر", "حاصروني", "حوالي زومبي", "الزومبي حولي", "الزومبي محاوط", "مساعدة",
    "ساعديني", "انقذيني", "نجدة", "الحقيني", "بموت", "سريع", "بسرعة",
    "surrounded", "trapped", "help me", "rescue me", "zombies around", "emergency",
)
_SUMMON = ("تعالي", "تعي", "اجي", "تجي", "come", "get here", "تعال")
_MARKER = ("العلامة", "علامة", "الخريطة", "الماب", "marker", "map marker", "pin")
_HOME = ("البيت", "بيتنا", "المنزل", "home", "base")
_UNLOAD_VERB = ("فضي", "فظي", "فرغي", "نزلي", "unload", "empty")
_CARGO = ("اغراض", "غراض", "حمول", "الصندوق", "اشياء", "اشيا", "car", "cargo", "trunk", "stuff")
_TAKE_ME = ("خديني", "خذيني", "وديني", "وصليني", "رجعيني", "take me", "drive me")


_PLACE_RX = re.compile(r"(?:روحي|روح|اذهبي|اطلعي|سوقي|قودي|توجهي)\s+(?:بالسيارة\s+)?(?:على|علي|عل|الي|الى|نحو|لل|ل|ع)?\s*(?P<place>.+?)\s+(?:و\s*)?(?:ارجعي|رجعي|ترجعي|تعي|تعالي)")
_PLACE_SKIP = ("فضي", "فرغي", "نزلي", "رتبي", "خزني", "الاغراض", "الاشياء", "السيارة")


def _errand_place(n):
    """"روحي عالمزرعة وارجعي" -> "المزرعة": the place named between the go-word and the come-back word."""
    m = _PLACE_RX.search(re.sub(r"(?<![\u0621-\u064a])عال", "على ال", n))
    if not m: return ""
    place = m.group("place").strip(" .،؟!")
    place = re.sub(r"^(?:على|الى|الي|نحو)\s+", "", place).strip()
    if not place or any(w in place for w in _PLACE_SKIP): return ""
    return place


_GO = ("روحي", "روح", "اذهبي", "اطلعي", "خذي الاغراض", "go", "drive to")
_UNLOAD = ("فضي", "فضّي", "فرغي", "نزلي الاغراض", "نزلي الاشياء", "رتبي الاغراض", "خزني", "unload", "drop off", "empty the car")
_RETURN = ("ارجعي", "رجعي", "وترجعي", "ترجعي", "come back", "return")
_TAKE_HOME = ("خذيني", "خديني", "وديني", "رجعيني", "take me home", "drive me home", "get me home")
_COME_HERE = ("تعي لعندي", "تعالي لعندي", "اجي لعندي", "لعندي", "اجيني", "تعي خذيني", "come to me", "come get me", "pick me up")

_FILL_RX = re.compile(r"(?<![\u0621-\u064a])و?(?:عبي|عبيلي|عبيلنا|عبيها|عبيه|تعبي|تعبيها|املي|امليها|امليلي)(?![\u0621-\u064a])|refuel|fill up|fill the")
_FUEL_WORDS = ("بنزين", "بانزين", "وقود", "كاز", "fuel", "gas")
_CAN_WORDS = ("غالون", "غلون", "جالون", "جلون", "جركن", "جيركن", "بيدون", "بدونات", "بدونة", "تنكة", "تنكه", "gas can", "jerry")
_CAR_WORDS = ("سيارة", "سياره", "الفان", "شاحنة", "شاحنه", "car", "van", "truck")
_NOT_FUEL = ("اغراض", "غراض", "حمول", "مي ", "ميه", "مياه", "water")
_ON_FOOT = ("امشي", "مشي على", "روحي مشي", "ع رجليك", "على رجليك", "عرجليك", "بدون سيارة", "من غير سيارة", "بلا سيارة", "on foot", "without a car", "without the car")
_PUMP_WORDS = ("مضخة", "مضخه", "مظخة", "مظخه", "المضخات", "pump")
_RETRY_WORDS = ("حاولي", "جربي", "كملي", "روحي", "ارجعي", "تعبي", "try again", "go to the pump")
_STATION_WORDS = ("كازية", "كازيه", "محطة بنزين", "محطه بنزين", "محطة وقود", "محطه وقود", "gas station", "fuel station", "petrol station")
_HOW_MANY = ("كم", "قديش", "عدد", "how many")
_HER_MEMORY = ("حافظ", "حفظت", "بتعرفي", "تعرفي", "عرفتي", "بتذكري", "تتذكري", "عندك", "مريتي", "you know", "remember")
_ASK_WORDS = ("وين", "فين", "اقرب", "بتعرفي", "تعرفي", "شفتي", "في كازي", "where", "nearest", "know any")


def _refuel(n, text):
    """Fill the car, the can, or both; a plain question about stations is the other goal."""
    fill = _FILL_RX.search(n) is not None
    can, car, fuel = any(w in n for w in _CAN_WORDS), any(w in n for w in _CAR_WORDS), any(w in n for w in _FUEL_WORDS)
    if fill and (can or car or fuel) and not any(w in n for w in _NOT_FUEL):
        foot = any(w in n for w in _ON_FOOT)
        target = "both" if can and car and not foot else ("can" if can or foot else "car")
        return make_goal("refuel_errand", {"target": target, "transport": "foot" if foot else "car"}, source="deterministic", text=text)
    if any(w in n for w in _PUMP_WORDS) and any(w in n for w in _RETRY_WORDS) and not any(w in n for w in ("وين", "where")):
        return make_goal("refuel_errand", {"target": "both" if can else "car", "transport": "car"}, source="deterministic", text=text)
    if any(w in n for w in _STATION_WORDS) and any(w in n for w in _HOW_MANY):
        whole_map = not any(w in n for w in _HER_MEMORY) and any(w in n for w in ("خريطة", "خريطه", "الخريطة", "المنطقة", "المنطقه", "كلها"))
        return make_goal("station_query", {"ask": "count_map" if whole_map else "count"}, source="deterministic", text=text)
    if any(w in n for w in _STATION_WORDS) and any(w in n for w in _ASK_WORDS):
        return make_goal("station_query", {}, source="deterministic", text=text)
    return None


def parse_high_confidence(text, snapshot=None):
    """Return one structured goal only when intent is strong enough to execute safely."""
    n = _norm(text)
    if not n:
        return None
    goal = _refuel(n, text)
    if goal:
        return goal
    # An errand: she drives there alone, does the work, and comes back by herself.
    # "روحي فضي الاغراض بالبيت وارجعي" -> errand_round_trip(home, unload, return).
    sort_only = "رتبي الاغراض" in n and not (any(w in n for w in _GO) or "سيار" in n or any(w in n for w in _RETURN))   # alone it is the sort order
    unload_hit = any(w in n for w in _UNLOAD if w != "رتبي الاغراض") or ("رتبي الاغراض" in n and not sort_only)
    if unload_hit or (any(w in n for w in _GO) and any(w in n for w in _RETURN)):
        dest = "home" if any(w in n for w in _HOME) else ("marker" if any(w in n for w in _MARKER) else "home")
        place = _errand_place(n) if dest == "home" and not any(w in n for w in _HOME) else ""
        if place: dest = "place"
        return make_goal("errand_round_trip", {
            "destination": dest,
            "place": place or None,
            "task": "unload" if unload_hit else "none",
            "then": "stay" if ("بلاش ترجعي" in n or "لا ترجعي" in n) else "return_to_player",
        }, source="deterministic", text=text)
    # "تعي لعندي" / "خذيني عالبيت": she comes to the player, no rescue drama.
    take_home = any(w in n for w in _TAKE_HOME)
    if take_home or any(w in n for w in _COME_HERE):
        return make_goal("fetch_player", {
            "then": "take_player_home" if take_home or any(w in n for w in _HOME) else "stay_with_player",
        }, source="deterministic", text=text)
    distress = sum(1 for w in _DISTRESS if w in n)
    summon = any(w in n for w in _SUMMON)
    zombie = "زومبي" in n or "zombie" in n
    # Emergency rescue must have either explicit rescue language or a combination
    # of summoning + danger. This avoids turning ordinary "تعالي" into a rescue.
    explicit = any(w in n for w in ("ساعديني", "انقذيني", "نجدة", "rescue me", "help me"))
    if explicit or (summon and "ساعد" in n) or (summon and distress >= 1 and zombie):
        target = "marker" if any(w in n for w in _MARKER) else "player"
        extract = "home" if any(w in n for w in _HOME) else "home_if_known"
        return make_goal("emergency_rescue", {
            "target": target,
            "transport": "vehicle_preferred",
            "combat": "clear_path_and_protect_player",
            "extract": extract,
            "urgency": "emergency",
        }, source="deterministic", text=text)
    return None


def make_goal(intent, slots=None, source="model", text=""):
    if intent not in SUPPORTED:
        return {"ok": False, "error": "unsupported_goal", "intent": intent}
    slots = dict(slots or {})
    if intent == "refuel_errand":
        # the text bridge fills target and extract positionally, so its second value lands in extract
        transport = slots.get("transport") or slots.get("extract")
        slots = {"target": slots.get("target") if slots.get("target") in ("car", "can", "both") else "car",
                 "transport": "foot" if transport == "foot" else "car"}
        if slots["transport"] == "foot": slots["target"] = "can"
    if intent == "emergency_rescue":
        target = slots.get("target") or "player"
        if target not in ("player", "marker"):
            target = "player"
        extract = slots.get("extract") or "home_if_known"
        if extract not in ("home", "home_if_known", "none"):
            extract = "home_if_known"
        slots.update({
            "target": target,
            "transport": slots.get("transport") or "vehicle_preferred",
            "combat": slots.get("combat") or "clear_path_and_protect_player",
            "extract": extract,
            "urgency": "routine" if slots.get("urgency") == "routine" else "emergency",
        })
    return {
        "ok": True,
        "version": GOAL_VERSION,
        "intent": intent,
        "slots": slots,
        "source": source,
        "text": str(text or "")[:1000],
        "createdAt": time.time(),
    }


def capabilities_text(tags=False):
    """What any connected model must know about its job and what it can make happen. tags=True for text-only bridges."""
    how = "اكتبي الوسم المذكور" if tags else "استدعي الأداة request_goal بالاسم المذكور، أو اكتبي الوسم المذكور"
    lines = ["[وظيفتك] أنتِ عقل سول داخل اللعبة: تفهمين طلب اللاعب وتختارين ما تفعله سول، واللعبة تنفذ وتؤكد النتيجة. "
             "نفّذي الطلب الواضح فورًا ولا تسألي عما قيل فيه. سول هي السائقة دائمًا إذا طُلبت القيادة، فلا تسألي من يقود. "
             "للقيادة اكتبي [فعل: sol_drive | marker] للمكان المحدد على الخريطة، أو home للبيت، أو اسم مكان محفوظ. لأضواء السيارة اكتبي [فعل: sol_headlights | on] أو [فعل: sol_headlights | off]. "
             "إذا طلب اللاعب شيئًا ليس في قائمة الأفعال ولا في الأهداف فقولي بوضوح: هذه القدرة غير متاحة الآن. "
             "لكل طلب من عدة خطوات " + how + " مرة واحدة، ولا تقسميه إلى أفعال منفردة. قبول الأمر بداية وليس إنجازًا. الأهداف المتاحة:"]
    for name, goal in GOALS.items():
        lines.append("- %s %s: %s" % (name, goal["tag"], goal["when"]) if not tags else "- %s: %s" % (goal["tag"], goal["when"]))
    return "\n".join(lines)


def provider_tool():
    return {"type": "function", "function": {
        "name": "request_goal",
        "description": "Submit one multi-step goal for Sol. The goals and when to use each are listed in the system prompt. The goal engine plans and monitors the steps; do not emit individual movement/combat actions for the same request.",
        "parameters": {"type": "object", "properties": {
            "intent": {"type": "string", "enum": list(SUPPORTED)},
            "target": {"type": "string", "enum": ["player", "marker", "car", "can", "both"]},
            "transport": {"type": "string", "enum": ["car", "foot"]},
            "extract": {"type": "string", "enum": ["home", "home_if_known", "none"]},
        }, "required": ["intent"]}
    }}

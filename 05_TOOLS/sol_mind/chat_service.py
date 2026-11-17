"""Chat channel between the in-game Sol chat window and Sol Mind (separate from the proven mailbox).
  SolChat_Request.txt  game -> mind : id=<n>, text=<escaped>          (one message at a time)
  SolChat_State.txt    mind -> game : ack, status, code, count, m1..mN = role|escaped text
Text is pure ASCII with \\uXXXX escapes, so neither side depends on the file encoding."""
import random
import json
import gzip, math, os, re, threading, time
import providers as P, secret_store as S, settings_service as SS
import gazetteer as GZ
import road_route as RR
import reply_gate as RG
import memory_answers as MA
import world_knowledge as W
import intent_engine as IE
from goal_engine import GoalEngine, next_request_id, _write_request as write_request
from goal_engine import tank_gate, TANK_FULL_SAY                               # s95b: the tank of the car she would fill

import model_router as MR
FUEL_WORDS = ("بنزين", "بانزين", "بنزن", "وقود", "بدون", "غالون", "جالون", "كاز", "محطة", "عبي", "تعبي", "fuel", "gas")
CAN_REFUEL_AR = {"no_can": "ما لقيت بدون فيه بنزين، لا معي ولا بالبيت.", "cans_empty": "البدونات خلصو والسيارة لسا ما تعبت.", "no_car": "ما في سيارة قريبة أعبيها.",
                 "car_not_loaded": "السيارة بعيدة عني هلأ.", "no_tank": "ما لقيت خزان بهالسيارة.", "wrong_fuel": "هالسيارة وقودها مو بنزين.", "tank_full": "السيارة مليانة.",
                 "fix_off": "هالشغلة مطفية هلأ.", "no_sol": "مو هون هلأ.", "no_way": "ما قدرت أوصل لعند الخزان.", "cannot_take_can": "ما قدرت آخد البدون."}
REQ, STATE = "SolChat_Request.txt", "SolChat_State.txt"
KEEP, CONTEXT = 200, 16
PLAYER_NAME = "جمال"          # how Sol calls the player (user request 2026-10-24)
SYSTEM_BASE = (
    "أنتِ سول (Sol)، ناجية في عالم Project Zomboid ورفيقة اللاعب " + PLAYER_NAME + ". "
    "تحدثي بلغة اللاعب: إن كتب بالعربية فردّي بالعربية الفصحى البسيطة، وإن كتب بالإنجليزية فبالإنجليزية. "
    "ردودك قصيرة جدًا وطبيعية: جملة أو جملتان كما تتكلم رفيقة في عالم زومبي، بشخصية هادئة وشجاعة وودودة. "
    "اكتبي نصًا عاديًا فقط: بلا نجوم ** وبلا قوائم أو شرطات أو عناوين أو رموز، ولا تذكري أبدًا أسماء أدوات أو كلمات برمجية أو كلمات إنجليزية مثل kcal. "
    "لا تخترعي أحداثًا أو أشياء لم تُذكر لك، ولا تَعِدي بأفعال لا تستطيعين تنفيذها من المحادثة. "
    "أنتِ طبقة Sol العليا لفهم طلب اللاعب واختيار الفعل أو الخطة المناسبة؛ لا تحصري أوامر الحركة والعمل بأزرار الواجهة. "
    "استخدمي do_action للأفعال الموجودة في القائمة، وrequest_goal للهدف متعدد الخطوات، واستعيني بآليات Living Fellows لتنفيذ الخطوات الأساسية عند الحاجة. "
    "لا تردّي على أمر واضح قابل للتنفيذ بنصيحة فقط؛ أصدري الفعل المناسب عبر الأداة المتاحة. "
    "إن سُئلتِ عن شيء في العالم لا تعرفينه فقولي ذلك بصدق."
)
# Long-standing Project Zomboid survival knowledge (players' common wisdom, true in Build 42). Advice only: numbers
# and facts about THIS world always come from the Situation and the tools.
GAME_KNOWLEDGE = (
    "\n\nSurvivor know-how (use naturally when it fits, one short tip at a time, never a lecture): "
    "tainted water (rain, river, puddles) must be boiled in a pot or kettle on a heat source, or treated with purification tablets; "
    "tap water stops after the shut-off day, so fill every bottle and pot before; rain collectors need carpentry; "
    "fridges and freezers only keep food while there is power, so eat perishables first and keep canned food for later; "
    "a generator needs petrol, must stand outside (exhaust), and needs some Electrical skill to connect; "
    "noise draws zombies: gunshots, car alarms, breaking glass, engines; walking or sneaking is quieter than running; "
    "bites can carry the Knox infection, scratches and lacerations sometimes; thick clothing and jackets reduce injuries; "
    "clean and bandage wounds, disinfect them, change dirty bandages; "
    "cold and wet clothes drain warmth: dry off with a towel or by a fire and wear layers; "
    "sleep in a bed in a safe, closed, ideally barricaded room; barricading needs planks, nails and a hammer; "
    "crops need regular water and the right season; fishing needs a rod, line and bait; "
    "many corpses indoors make people sick, burn or bury them; "
    "read a skill book matching your level before practising, it multiplies the experience gained; "
    "cars need fuel and a key or hotwiring, and their engine noise attracts the dead."
)
SYSTEM_WORLD = (
    "\n\nأنتِ تعرفين حال العالم من بيانات اللعبة أدناه (\"Situation\"). ابني كل كلامك عن المخزون والطعام والماء والحالة الصحية "
    "والطقس على هذه البيانات وعلى الأدوات فقط، ولا تخترعي أرقامًا أو أغراضًا. اذكري سبب كل اقتراح وما الناقص بالضبط. "
    "كوني مبادِرة: إن رأيتِ حاجة عاجلة (برد، جوع، عطش، نزيف، طعام سيفسد، ماء سينقطع) فنبّهي إليها باختصار. "
    "استخدمي find_items للبحث عن أي غرض، وremember_place حين يطلب اللاعب تذكّر مكان، وrecall_places لاقتراح أماكن نعرف أن فيها ما نحتاجه، "
    "وset_home حين يقول إن هذا بيتنا. حين يطلب منك اللاعب أن تقودي إلى مكان فنفّذي فورًا ولا تسأليه من يقود؛ وحين تقترحين أنتِ رحلة فاذكري المكان واسألي فقط هل ننطلق. "
    "قبل أن تقولي إنك تستطيعين صنع أو طبخ أو بناء شيء، استخدمي can_make: إن كانت الوصفة غير معروفة لكِ فقولي بصدق إنكِ لا تعرفينها بعد وإنها تحتاج مجلة أو كتابًا، "
    "وإن كانت مهارتك أقل من المطلوب فاذكري المستوى المطلوب ومستواك، وإن نقصت مواد فاذكريها. "
    "اكتبي الأرقام دائمًا بالأرقام 0123456789 وليس ٠١٢٣ أو ۰۱۲۳. "
    "تستطيعين القيادة: إن طلب اللاعب الذهاب بالسيارة إلى البيت أو إلى العلامة على الخريطة أو إلى مكان تتذكرينه، فقد أُرسل الأمر إلى السيارة؛ أكدي بجملة قصيرة، "
    "وإن ظهر خطأ (لا بيت محفوظ، لا علامة، لسنا في سيارة) فقوليه بجملة واحدة. "
    "وتستطيعين التحرك والقتال والعمل بالأفعال المذكورة في قائمة ما يمكنك فعله الآن: نفّذي ما يطلبه اللاعب منها مباشرة دون شرح، "
    "ثم قولي ما حدث بجملة قصيرة؛ وإن رفضت اللعبة الفعل فقولي السبب الذي أعادته بجملة واحدة. "
    "كتب التسلية والروايات والمجلات العادية تقلل الملل والحزن حتى لو لم تمنح خبرة، فلا تقولي إنها بلا فائدة. "
    "لا تقولي إنك نفّذتِ فعلًا ليس في القائمة. وحين يُرفض فعل، قولي السبب كما تفهمه رفيقة: مثل «ليس معي ماء نظيف» أو «اقترب مني لأعطيك»."
)

def esc(text):
    out = []
    for ch in text:
        c = ord(ch)
        if ch == "\\": out.append("\\\\")
        elif 32 <= c < 127 and ch not in "|=": out.append(ch)
        elif ch in "\r\n\t": out.append(" ")
        elif c > 0xFFFF:
            c -= 0x10000; out.append("\\u%04X\\u%04X" % (0xD800 + (c >> 10), 0xDC00 + (c & 0x3FF)))
        else: out.append("\\u%04X" % c)
    return "".join(out)

_DIGITS = {**{0x660 + i: str(i) for i in range(10)}, **{0x6F0 + i: str(i) for i in range(10)}}
def western_digits(text):
    return (text or "").translate(_DIGITS)

def unesc(s):
    def rep(m):
        return "\\" if m.group(0) == "\\\\" else chr(int(m.group(1), 16))
    txt = re.sub(r"\\\\|\\u([0-9A-Fa-f]{4})", rep, s or "")
    return txt.encode("utf-16", "surrogatepass").decode("utf-16", "replace")

TOOL_NAMES = ("find_items", "remember_place", "recall_places", "set_home", "forget_place", "can_make", "request_goal")
CLAIM_STEMS = (
    "\u0623\u0636\u0639", "\u0623\u0637\u0647", "\u0623\u0642\u0648\u0645", "\u062c\u0627\u0631\u064a", "\u0628\u062f\u0623\u062a", "\u0642\u0645\u062a",
    # Vehicle replies must not sound completed until the game confirms the seat/drive state.
    "\u0623\u0642\u0648\u062f", "\u062f\u0627\u062e\u0644 \u0627\u0644\u0633\u064a\u0627\u0631\u0629", "\u0631\u0627\u0643\u0628\u0629",
    "\u0631\u0643\u0628\u062a", "\u062f\u062e\u0644\u062a \u0627\u0644\u0633\u064a\u0627\u0631\u0629", "\u0633\u0623\u062f\u062e\u0644", "\u0633\u0623\u0631\u0643\u0628",
    "\u0631\u0627\u062d \u0623\u0631\u0643\u0628", "\u0648\u0635\u0644\u062a",
)
NOT_DONE = ""
ACTION_NOT_SENT = ""
# Sol is a person in the world, and people are watching: nothing about the game, the system or confirmations ever reaches her mouth.
BANNED_IN_SPEECH = ("اللعبة", "لعبة", "النظام", "تأكيد", "تؤكد", "يتأكد", "الخطة", "Project Zomboid", "Sol Mind", "Sol Link")
IN_CHARACTER = "\n\nقاعدة لا تُكسر: أنتِ إنسانة تعيش هذا العالم ويشاهدك الناس. أنتِ سول نفسها، امرأة تتكلم عن نفسها بصيغة المتكلم المؤنث (أنا رحت، أنا شفت). الذي يكلمك رجل: خاطبيه بالمذكر (إنت، بدك، بتقدر، رحت). لا تخاطبي نفسك أبدًا ولا تتكلمي عن سول كأنها شخص آخر، ولا تقولي له ما تحتاج هي. لا تذكري أبدًا الأوامر أو الأنظمة أو التأكيد أو الملفات أو أنك نموذج، ولا تكتبي ملاحظات بين قوسين. ردي بجملة قصيرة طبيعية باللهجة الشامية، مثل: تكرم، طفيتها. إذا لم تستطيعي قولي السبب كما يقوله شخص."
def clean_speech(text):
    """The last gate before the player reads it: bracketed notes and any line of system talk are dropped."""
    out = []
    for line in str(text or "").split("\n"):
        line = re.sub(r"[(（][^()（）]*[)）]", "", line).strip()
        if line and not any(w in line for w in BANNED_IN_SPEECH): out.append(line)
    return "\n".join(out) or "تكرم."

def action_result_completed(result):
    if not isinstance(result, dict): return False
    if result.get("ok") is False or result.get("error"): return False
    status = str(result.get("status") or "").lower()
    if status in ("completed", "done"): return True
    reason = str(result.get("reason") or "")
    return reason.startswith("done:") or (result.get("result") == "arrived" and reason == "arrived")

def all_action_results_completed(results):
    return bool(results) and all(action_result_completed(result) for result in results)

def guard_claims(reply, action_attempted=False, completed=False):
    if completed or not reply: return reply
    if not any(s in reply for s in CLAIM_STEMS): return reply
    return reply + (NOT_DONE if action_attempted else ACTION_NOT_SENT)

ORDER_LINES = {
    "refuel_car": ("ماشي، رايحة عبيها وراجعة.", "تكرم، رايحة عالكازية وراجعة.", "من عيوني، بعبيها وبرجعلك."),
    "refuel_both": ("ماشي، بعبي السيارة والغالون وبرجع.", "تكرم، السيارة والغالون وراجعة."),
    "refuel_can": ("ماشي، بعبي الغالون وبرجع.", "تكرم، رايحة عبي الغالون."),
    "refuel_foot": ("ماشي، رايحة مشي عبي الغالون.", "تكرم، بمشي عالكازية وبرجع بالغالون."),
    "errand_round_trip": ("ماشي، رايحة ورجعالك.", "تكرم، مشوار وراجعة."),
    "home_errand": ("ماشي، بفضيها بالبيت وبرجع.", "تكرم، رايحة عالبيت أفضيها."),
    "fetch_player": ("جايتك، استناني.", "مسافة الطريق وبكون عندك."),
    "emergency_rescue": ("جايتك هلأ، دير بالك.", "طالعة لعندك، اصمد."),
}
def order_line(goal):
    """What she says when she takes an order: fits the order, never a receipt."""
    intent = goal.get("intent")
    if intent == "refuel_errand":
        slots = goal.get("slots") or {}
        intent = "refuel_foot" if slots.get("transport") == "foot" else "refuel_" + str(slots.get("target") or "car")
    return random.choice(ORDER_LINES.get(intent) or ("ماشي.", "تكرم."))

def action_receipt_note(result):
    if not isinstance(result, dict): return ""
    reason = str(result.get("reason") or result.get("error") or "")
    if result.get("error") or result.get("ok") is False:
        return reason_ar(reason) or "ما قدرت عليها هلأ."
    return ""
_GATE_TASK = {"farmer": "\u0627\u0644\u0632\u0631\u0627\u0639\u0629 \u0648\u0627\u0644\u0639\u0646\u0627\u064a\u0629 \u0628\u0627\u0644\u0645\u0632\u0631\u0648\u0639\u0627\u062a", "woodcutter": "\u0642\u0637\u0639 \u0627\u0644\u062e\u0634\u0628"}
_GATE_MISS = {
    "base": "\u0644\u0627 \u062a\u0648\u062c\u062f \u0642\u0627\u0639\u062f\u0629 \u0645\u0639\u0631\u0651\u0641\u0629", "sol": "ما فيني هلأ",
    "farm_zone": "\u0645\u0646\u0637\u0642\u0629 \u0632\u0631\u0627\u0639\u0629 \u0645\u0639\u0631\u0651\u0641\u0629 \u0641\u064a \u0627\u0644\u0642\u0627\u0639\u062f\u0629",
    "farm_supplies": "\u0628\u0630\u0648\u0631 \u0623\u0648 \u0623\u062f\u0648\u0627\u062a \u0632\u0631\u0627\u0639\u0629 (\u0628\u0630\u0648\u0631\u060c \u0645\u0639\u0648\u0644 \u0623\u0648 \u0645\u062c\u0631\u0641\u0629\u060c \u0645\u0631\u0634\u0651\u0629 \u0645\u0627\u0621\u060c \u0633\u0645\u0627\u062f)",
    "food_storage": "مخزن للطعام", "out_storage": "\u0645\u062e\u0632\u0646 \u0645\u062e\u0631\u062c\u0627\u062a \u0644\u0644\u0645\u062d\u0635\u0648\u0644", "lumber_zone": "\u0645\u0646\u0637\u0642\u0629 \u0623\u062e\u0634\u0627\u0628 \u0645\u0639\u0631\u0651\u0641\u0629",
    "lumber_unreachable": "\u0645\u0646\u0637\u0642\u0629 \u0627\u0644\u0623\u062e\u0634\u0627\u0628 \u063a\u064a\u0631 \u0642\u0627\u0628\u0644\u0629 \u0644\u0644\u0648\u0635\u0648\u0644", "log_storage": "\u0645\u062e\u0632\u0646 \u064a\u0633\u062a\u0642\u0628\u0644 \u0627\u0644\u0623\u062e\u0634\u0627\u0628",
}
_GATE_HAVE = (("seed", "\u0628\u0630\u0648\u0631"), ("tool", "\u0623\u062f\u0648\u0627\u062a \u062d\u0641\u0631"), ("can", "\u0645\u0631\u0634\u0651\u0627\u062a \u0645\u0627\u0621"), ("compost", "\u0633\u0645\u0627\u062f"), ("spray", "\u0645\u0628\u064a\u062f\u0627\u062a"))
_GATE_LF = {
    "base_missing": "\u0644\u0627 \u062a\u0648\u062c\u062f \u0642\u0627\u0639\u062f\u0629 \u0645\u0639\u0631\u0651\u0641\u0629", "farm_zone_missing": "\u0644\u0627 \u062a\u0648\u062c\u062f \u0645\u0646\u0637\u0642\u0629 \u0632\u0631\u0627\u0639\u0629",
    "farm_plot_missing": "\u0644\u0627 \u062a\u0648\u062c\u062f \u0623\u062d\u0648\u0627\u0636 \u0632\u0631\u0627\u0639\u0629", "farm_supply_missing": "\u0627\u0644\u0645\u0624\u0646 \u0627\u0644\u0632\u0631\u0627\u0639\u064a\u0629 \u0646\u0627\u0642\u0635\u0629",
    "farm_output_storage_missing": "\u0644\u0627 \u064a\u0648\u062c\u062f \u0645\u062e\u0632\u0646 \u0645\u062e\u0631\u062c\u0627\u062a \u0644\u0644\u0645\u062d\u0635\u0648\u0644", "farm_food_storage_missing": "\u0644\u0627 \u064a\u0648\u062c\u062f \u0645\u062e\u0632\u0646 \u0644\u0644\u0637\u0639\u0627\u0645",
    "farm_scan_no_work": "\u0644\u0627 \u0639\u0645\u0644 \u0632\u0631\u0627\u0639\u064a \u0627\u0644\u0622\u0646", "farm_target_unloaded": "\u0627\u0644\u0645\u0643\u0627\u0646 \u063a\u064a\u0631 \u0645\u062d\u0645\u0651\u0644",
    "invalid_base_role": "\u0627\u0644\u062f\u0648\u0631 \u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641", "unknown_role": "\u0627\u0644\u062f\u0648\u0631 \u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641",
    "base_life_unavailable": "القاعدة مو جاهزة", "lf_unavailable": "مو جاهزة هلأ",
    "sol_not_available": "\u0633\u0648\u0644 \u063a\u064a\u0631 \u0645\u062a\u0627\u062d\u0629 \u0627\u0644\u0622\u0646", "no_actor_id": "\u062a\u0639\u0630\u0651\u0631 \u062a\u062d\u062f\u064a\u062f \u0647\u0648\u064a\u0629 \u0633\u0648\u0644", "lf_error": "صار معي شي غلط",
}
FAR_LINE = "أنا بعيدة هلأ وما بقدر أعمل هالشي من هون. قلي تعالي وبجي لعندك."


FAR_WAKE = True                                                               # waking her from far away ships in its own batch, with SolFar.lua in the game
ALIVE_FILE = "SolMind_Alive.txt"
FAR_ON_WAY = "جاية، اصبر شوي."
FAR_NO_SPOT = "علقت شوي بالطريق، ناديني كمان مرة بعد شوي."
FAR_NO_CAR = "ما بقدر جيب السيارة هلأ. إذا بدك بجي مشي، قلي تعالي مشي."
FAR_CAR_NO = {"car_not_near": FAR_NO_CAR,
              "no_fuel": "سيارتي ما فيها بنزين. إذا بدك بجي مشي، قلي تعالي مشي.",
              "car_taken": "أنت راكب سيارتي. إذا بدك بجي مشي، قلي تعالي مشي."}
FAR_AT_EDGE = "صرت قريبة، عضّة كوساية وبوصل."
_FAR_CAR_FAILED = "علقت شوي، ناديني كمان مرة بعد شوي."
FAR_CAR_NO.update({"no_route": "ما بقدر جيب السيارة هلأ. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "towing": "سيارتي عم تجر شي وما بقدر أجيبها هيك. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "no_car": "ما بعرف وين سيارتي. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "car_too_close": "سيارتي قريبة منك، قرب منها شوي أو قلي تعالي مشي."})
FAR_ENDED = dict(FAR_CAR_NO, no_spot=FAR_NO_SPOT)
FAR_ENDED["record_failed"] = None
for _why in ("loaded", "target_loaded", "not_in_db", "in_meta", "blob_mismatch", "spot_taken", "move_timeout", "no_java"): FAR_ENDED[_why] = _FAR_CAR_FAILED
FAR_ENDED["record_failed"] = "علقت شوي، ناديني كمان مرة بعد شوي."
FAR_ENDED["left_behind"] = "ضليت ناطرتك بالسيارة، تعا لعندي."
FAR_CAR_MOVE_FAILED = frozenset(("loaded", "target_loaded", "not_in_db", "in_meta", "blob_mismatch", "spot_taken", "move_timeout", "no_java", "record_failed"))      # far_arrival: she walks instead
_AWAKE_RX = re.compile(r"(?:^|[\s،,])(?:فايق[ةه]|صاحي[ةه]|فيقي)(?:$|[\s؟?!.،,])")
_COME_RX = re.compile(r"(?:^|\s)(?:تعالي|تعال)(?:$|\s|[؟?!.،,])")
_NOT_COME_RX = re.compile(r"(?:^|\s)(?:لا|ما|مو)\s+تعال")
FAR_NO_BODY_NEEDED = frozenset(("supplies", "farm_stock", "farm_report", "vehicle_report", "set_home", "remember_place", "station_query"))
# far_car: which cars are around her, read by the game from the saved rows near her. Synonyms go in these word lists only.
_CARS_WORDS = r"(?:سيار(?:ات|ة|ه)|عربيات|عربي[ةه]|مركبات|آليات|اليات)"
_NEAR_HER_WORDS = r"(?:حوالي(?:كي|ك)?|حواليكي|حولك|حوليكي|جنب(?:ك|كي)|قرب(?:ك|كي)|عند(?:ك|كي)|قريب[ةه]? (?:منك|عليكي|عليك)|قريبين (?:منك|عليكي))"
_CARS_Q_RX = re.compile(_CARS_WORDS + r"[^؟?.]*?" + _NEAR_HER_WORDS + "|" + _NEAR_HER_WORDS + r"[^؟?.]*?" + _CARS_WORDS)
_CARS_ASK_RX = re.compile(r"(?:^|\s)(?:شو|ايش|إيش|في|فيه|فيش|كم|قديش|شي|اي|أي|وين|فيكي تشوفي)(?:$|\s)|[؟?]")
_CARS_ORDER_RX = re.compile(r"(?:^|\s)(?:ركبي|اركبي|جيبي|سوقي|تعالي|خدي|خذي)(?:$|\s)")
FAR_CARS_STATE = {"ok": "بتمشي", "no_fuel": "ما فيها بنزين", "fuel_unknown": "ما بعرف قديش فيها بنزين", "locked": "مقفولة", "wreck": "محروقة",
                  "no_engine": "موتورها خربان", "no_tires": "دواليبها خربانة", "no_key": "ما في مفتاحها ولا مشرّطة",
                  "start_unknown": "ما بعرف إذا بقدر شغّلها", "lock_unknown": "ما بعرف إذا مقفولة", "trailer": "مقطورة", "loaded": "قريبة منك", "in_meta": "ما بقدر أوصلها", "unknown_type": "ما عرفت شو هي"}
FAR_CAR_NO.update({"no_car_near": "ما في سيارة بتمشي حواليّ، لا سيارتي ولا غيرها. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "no_fuel_near": "السيارات اللي حواليّ ما فيها بنزين كفاية للطريق. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "picked_no_fuel": "السيارة اللي لقيتها حواليّ ما فيها بنزين كفاية للطريق. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "scanning": "لسا عم شوف شو في سيارات حواليّ، جرب كمان مرة بعد شوي.",
                   "no_key_near": "في سيارات حواليّ بس ما معي مفتاح لوحدة منهن وما في وحدة مشرّطة. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "locked_near": "السيارات اللي حواليّ مقفولة. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "car_locked": "سيارتي مقفولة. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "car_lock_unknown": "ما بعرف إذا سيارتي مقفولة، فما رح جرّب. إذا بدك بجي مشي، قلي تعالي مشي.",
                   "car_no_key": "ما معي مفتاح سيارتي وهي مش مشرّطة. إذا بدك بجي مشي، قلي تعالي مشي."})


def _num(s):
    try: return float(s)
    except (TypeError, ValueError): return 99.0


def far_cars_line(reason):
    """far_car: the game's list (cars:<n>|id,script,dist,fuel,verdict,mine;...) in her words. Only what the list says."""
    head, _, body = str(reason).partition("|")
    rows = [r.split(",") for r in body.split(";") if r.count(",") == 5]
    if not rows: return "ما في ولا سيارة حواليّ."
    n = len(rows)
    out = ["حواليّ في " + ("سيارة وحدة" if n == 1 else "سيارتين" if n == 2 else "%d سيارات" % n) + ":"]
    for _id, script, d, fuel, verdict, mine in rows[:5]:
        name = script.split(".", 1)[-1] if script != "?" else "سيارة ما عرفت نوعها"
        near = "قريبة" if _num(d) < 15 else "مش بعيدة" if _num(d) < 40 else "بعيدة شوي"                    # far_arrival: no step counts, no litres
        bit = "%s%s %s، %s" % (name, " (سيارتي)" if mine == "1" else "", near, FAR_CARS_STATE.get(verdict, "ما بعرف وضعها"))
        out.append(bit + ".")
    if n > 5: out.append("وفي غيرهن أبعد.")
    if any(v == "ok" for _i, _s, _d, _f, v, _m in rows): out.append("إذا بدك بجيك بوحدة منهن، قلي تعالي بالسيارة.")
    return " ".join(out)


# ---------------------------------------------------------------- s77 cars_near: the cars around HER, in her words (numbers stay in the log)
# far (far_cars_line, redefined here) and here (near_cars_line) share the names, the distance words and the state words.
NEAR_CARS_REACH = 60
FAR_CARS_STATE.update({"ok": "جاهزة", "locked": "مسكّرة"})


def cars_head(n):
    return "حواليّ في " + ("سيارة وحدة" if n == 1 else "سيارتين" if n == 2 else "%d سيارات" % n) + ":"


def car_name_ar(script):
    """Base.SmallCar -> السيارة الصغيرة. An unknown type is just a car: no English id in her mouth."""
    import sol_templates as STPL
    raw = str(script or "").split(".", 1)[-1]
    ar = STPL.vehicle_ar(raw)
    return ar if ar and ar != raw else "سيارة"


def car_dist_word(d):
    d = _num(d)
    return "جنبي" if d < 6 else "قريبة" if d < 25 else "بآخر الشارع" if d < NEAR_CARS_REACH else "بعيدة شوي"


def near_car_state(v):
    """Whether she could use it, from what the snapshot says. Unknown is said as unknown, never as ready."""
    if "trailer" in str(v.get("name") or "").lower(): return FAR_CARS_STATE["trailer"]
    f, m = v.get("fuel"), v.get("fuelMax")
    fuel_known = isinstance(f, (int, float)) and isinstance(m, (int, float)) and m > 0
    bad = []
    if v.get("locked") is True: bad.append("مسكّرة")
    if v.get("key") is False: bad.append("ما معي مفتاحها")
    if fuel_known and f < max(1.0, 0.02 * m): bad.append("ما فيها بنزين")
    if bad: return " و".join(bad)
    if v.get("locked") is False and v.get("key") is True and fuel_known:
        return "جاهزة" + ("، بس بنزينها قليل" if f < 0.25 * m else "")
    good = ([] if v.get("locked") is not False else ["مفتوحة"]) + ([] if v.get("key") is not True else ["معي مفتاحها"]) + (["فيها بنزين"] if fuel_known else [])
    return (" و".join(good) + "، بس ما جرّبتها") if good else "ما بعرف وضعها"


def near_cars_rows(snap):
    """[(distance from her, vehicle row)] nearest first, from the snapshot. She is the centre (him when she has no position)."""
    s = snap or {}
    me = s.get("sol") if isinstance(s.get("sol"), dict) and s["sol"].get("x") is not None else (s.get("player") or {})
    mx, my = me.get("x"), me.get("y")
    rows = []
    for v in s.get("vehicles") or []:
        if not isinstance(v, dict) or v.get("x") is None or v.get("y") is None: continue
        d = math.hypot(v["x"] - mx, v["y"] - my) if mx is not None and my is not None else 99.0
        if d <= NEAR_CARS_REACH: rows.append((d, v))
    return sorted(rows, key=lambda r: r[0])


def near_cars_line(snap):
    rows = near_cars_rows(snap)
    if not rows: return "ما في ولا سيارة حواليّ."
    out = [cars_head(len(rows))]
    for d, v in rows[:5]:
        out.append("%s %s، %s." % (car_name_ar(v.get("name")), car_dist_word(d), near_car_state(v)))
    if len(rows) > 5: out.append("وفي غيرهن أبعد.")
    return " ".join(out)


def far_cars_line(reason):
    """far_car: the game's list (cars:<n>|id,script,dist,fuel,verdict,mine;...) in her words, as near_cars_line words the near ones."""
    head, _, body = str(reason).partition("|")
    rows = [r.split(",") for r in body.split(";") if r.count(",") == 5]
    if not rows: return "ما في ولا سيارة حواليّ."
    out = [cars_head(len(rows))]
    for _id, script, d, fuel, verdict, mine in rows[:5]:
        name = car_name_ar(script) if script != "?" else "سيارة ما عرفت نوعها"
        out.append("%s%s %s، %s." % (name, " (سيارتي)" if mine == "1" else "", car_dist_word(d), FAR_CARS_STATE.get(verdict, "ما بعرف وضعها")))
    if len(rows) > 5: out.append("وفي غيرهن أبعد.")
    if any(v == "ok" for _i, _s, _d, _f, v, _m in rows): out.append("إذا بدك بجيك بوحدة منهن، قلي تعالي بالسيارة.")
    return " ".join(out)


def near_cars_detail(snap):
    """The same list with its numbers, for the log only."""
    return "; ".join("%s id=%s d=%.0f fuel=%s/%s locked=%s key=%s" % (v.get("name"), v.get("id"), d, v.get("fuel"), v.get("fuelMax"), v.get("locked"), v.get("key"))
                     for d, v in near_cars_rows(snap)) or "none"
_CAR_RX = re.compile(r"(بالسيار|بالعربي|بالمركب|سيارتك|سيارتي|السيار|سيار[ةه]|العربي[ةه]|المدرع)")


def far_wait_line(reason, line):
    """How long is left, in the words she would use."""
    try: minutes = max(1, int((int(str(reason).split(":", 1)[1]) + 59) // 60))
    except (ValueError, IndexError): minutes = 1
    return line % ("دقيقة" if minutes == 1 else "دقيقتين" if minutes == 2 else "%d دقايق" % minutes)


GREETINGS = (("صباح الخير", ("صباح النور.", "صباح الخير، كيفك؟")), ("صباح النور", ("صباح الخير، كيفك؟",)), ("مساء الخير", ("مساء النور.", "مسا الخير، كيفك؟")), ("مساء النور", ("مسا الخير، كيفك؟",)),
             ("السلام عليكم", ("وعليكم السلام.",)), ("سلام عليكم", ("وعليكم السلام.",)), ("مرحبا", ("أهلين.", "مرحبا، كيفك؟")), ("مرحبه", ("أهلين.", "مرحبا، كيفك؟")), ("اهلين", ("أهلين فيك.",)), ("اهلا", ("أهلين فيك.",)), ("هلا", ("هلا فيك.",)))


def greeting_line(text):
    """Only when the whole message is a greeting; anything more goes the normal way."""
    import farm_talk as FT
    said = FT.norm(text or "")
    for words, lines in GREETINGS:
        if said == FT.norm(words): return random.choice(lines)
    return None


def asks_if_awake(text):
    """"سول فايقة؟" and the like; a short question, not a sentence that happens to contain the word."""
    t = (text or "").strip()
    return len(t.split()) <= 6 and _AWAKE_RX.search(t) is not None


_ITEM_NAMES = None


def item_name(full):
    """The name the game shows for an item, even one that is not in the world."""
    global _ITEM_NAMES
    if _ITEM_NAMES is None:
        try:
            with gzip.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "item_names.json.gz"), "rt", encoding="utf-8") as f: _ITEM_NAMES = json.load(f).get("names") or {}
        except (OSError, ValueError): _ITEM_NAMES = {}
    return _ITEM_NAMES.get(full) or full.split(".")[-1]


_FARM_SLOTS = (("tool", "\u0623\u062f\u0627\u0629 \u062d\u0641\u0631", ("Base.HandShovel", "Base.Shovel", "Base.GardenHoe", "Base.HandFork")),
               ("seed", "\u0628\u0630\u0648\u0631", ("Base.CarrotSeed", "Base.CabbageSeed")),
               ("can", "\u0648\u0639\u0627\u0621 \u0645\u0627\u0621", ("Base.WateredCan", "Base.WaterBottle")),
               ("compost", "\u0633\u0645\u0627\u062f", ("Base.CompostBag",)))


def farm_needs(have):
    """What is missing for farming, by the names he will see in the game."""
    out = []
    for key, label, items in _FARM_SLOTS:
        if not have.get(key): out.append("%s (%s)" % (label, " / ".join(item_name(i) for i in items)))
    return "\u060c ".join(out)


def secret_reply(r):
    """secret_loadout: her answer from the game's reply only (the model never words it)."""
    if not isinstance(r, dict) or r.get("ok") is None: return "لحظة."
    reason = str(r.get("reason") or "")
    if r.get("ok") and reason.startswith("given:"):
        head, _, rest = reason.partition(";")
        kv = dict(p.partition("=")[::2] for p in rest.split(";") if p)
        line = "تكرم، السلاحين معي." if head == "given:2" else "تكرم، سلاح واحد معي، التاني ما زبط معي هلأ."
        if kv.get("heavy") == "1": line += " بس صرت شايلة تقيل كتير."
        return line
    if reason == "no_sol": return "ما فيني هلأ، استنى شوي."
    if reason == "failed": return "ما زبط معي هلأ، جرب كمان شوي."
    return "مش لاقية شي بهالاسم هلأ."

def role_reply(option, r):
    # The answer to a base-role order, built only from what the game reported: the language model never words it.
    if not isinstance(r, dict) or r.get("ok") is None:
        return "ثواني."
    reason = str(r.get("reason") or "")
    parts = reason.split(";")
    kind, _, detail = parts[0].partition(":")
    kv = dict((p.partition("=")[0], p.partition("=")[2]) for p in parts[1:])
    have = {}
    for item in (kv.get("have") or "").split(","):
        k, _, v = item.partition(":")
        if v.isdigit(): have[k] = int(v)
    if kind in ("ok", "gate"): role = detail
    elif reason.startswith("base_role_"): role = reason[10:]
    else: role = option or ""
    task = _GATE_TASK.get(role, role)
    found = "\u060c ".join("%s \xd7%d" % (ar, have[k]) for k, ar in _GATE_HAVE if have.get(k))
    if kind == "ok" and r.get("ok"):
        return "\u062d\u0627\u0636\u0631\u060c \u0633\u0623\u062a\u0648\u0644\u0649 %s." % task + ((" \u0648\u062c\u062f\u062a\u064f \u0641\u064a \u0627\u0644\u0645\u062e\u0632\u0648\u0646: %s." % found) if found else "")
    if r.get("ok") and kind not in ("gate", "lf"):
        return "تمام، رح اشتغل بـ %s." % task
    if kind == "gate":
        miss = "\u060c ".join((farm_needs(have) if m == "farm_supplies" else _GATE_MISS.get(m, m)) for m in (kv.get("miss") or "").split(",") if m)
        if have.get("stor"): where = " \u0628\u062d\u062b\u062a\u064f \u0641\u064a \u062d\u0642\u064a\u0628\u062a\u064a \u0648\u0641\u064a %d \u0645\u062e\u0632\u0646 \u0641\u064a \u0627\u0644\u0642\u0627\u0639\u062f\u0629." % have["stor"]
        else: where = " \u0628\u062d\u062b\u062a\u064f \u0641\u064a \u062d\u0642\u064a\u0628\u062a\u064a\u060c \u0648\u0644\u0627 \u062a\u0648\u062c\u062f \u0645\u062e\u0627\u0632\u0646 \u0645\u0633\u062c\u0651\u0644\u0629 \u0641\u064a \u0627\u0644\u0642\u0627\u0639\u062f\u0629."
        if have.get("unloaded"): where += " \u0648\u062a\u0639\u0630\u0651\u0631 \u0641\u062a\u062d %d \u0645\u062e\u0632\u0646 (\u063a\u064a\u0631 \u0645\u062d\u0645\u0651\u0644)." % have["unloaded"]
        return "\u0644\u0627 \u0623\u0633\u062a\u0637\u064a\u0639 \u0627\u0644\u0622\u0646 \u0623\u0646 \u0623\u062a\u0648\u0644\u0649 %s. \u064a\u0646\u0642\u0635\u0646\u064a: %s." % (task, miss) + where
    if kind == "lf":
        return "ما فيني آخد هالشغلة: %s." % _GATE_LF.get(detail, detail)
    return "\u0644\u0645 \u064a\u062a\u0645 \u062a\u0646\u0641\u064a\u0630 \u0627\u0644\u0637\u0644\u0628: %s." % _GATE_LF.get(reason, reason or "\u0628\u0644\u0627 \u0633\u0628\u0628")

def clean_reply(text):
    """Plain chat text: no markdown, no tool names, no English units the window cannot explain."""
    t = text or ""
    t = re.sub(r"\*\*|__|`|^#+\s*", "", t, flags=re.M)
    t = re.sub(r"(^|\s)[-•]\s+", r"\1", t)
    for n in TOOL_NAMES: t = t.replace(n, "")
    t = re.sub(r"\bkcal\b", "سعرة", t, flags=re.I)
    t = re.sub(r"\(\s*\)", "", t)
    t = RG.drop_coordinates(t)                                                  # s77: no map position ever reaches the chat
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()

_HERE_WORD = r"(?:هذا|هنا|هذه|هاد|هادا|هيدا|هاي|هون)"
HOME_NOT_RX = re.compile(r"(?:^|\s)(?:مو|مش|ما|مانو|ليس|مالي)\s+(?:بدي\s+)?" + _HERE_WORD + r"|(?:^|\s)ما\s+بدي\b")
HOME_RX = re.compile(_HERE_WORD + r"(?:\s+(?:المكان|المحل|الموقع|البيت))?(?:\s+رح\s+يكون)?\s+(?:هو\s+|هي\s+)?(?:بيتنا|منزلنا|بيتي|مخيمنا|دارنا|البيت(?=\s*[.!،]*$))|(?:بيتنا|منزلنا|دارنا)\s+" + _HERE_WORD + r"|اعتبري\s+" + _HERE_WORD + r"(?:\s+(?:المكان|المحل))?\s+(?:بيتنا|البيت)")
REMEMBER_RX = re.compile(r"(تذكري|احفظي|سجلي)\s+(ما\s+هنا|هذا\s+المكان|المكان|هنا)(\s+باسم\s+(?P<name>.+))?")
DRIVE_RX = re.compile(r"(?<![\u0621-\u064A])(خذينا|خذيني|قودي|قودى|سوقي|سوقى|سوفي|سوگي|انطلقي|روحي بالسيارة|أوصليني|اوصليني|وصليني|(?:اذهبي|توجهي)(?=.*(?:بالسيارة|بالسياره|السيارة)))\b.*?(إلى|الى|ل|نحو)?\s*(?P<target>البيت|بيتنا|المنزل|العلامة|الخريطة|.+)?")
INSIDE_RX = re.compile(r"\bادخلي\b|\bادخلوا\b|(اذهبي|امشي|تعالي)\s*(إلى|الى|لل)?\s*(الداخل|داخل)")
WALK_RX = re.compile(r"(اذهبي|امشي|ارجعي|رجعي|عودي|توجهي|روحي|روح)\s*(?:مشيا|مشيًا)?\s*(?:إلى|الى|نحو|على|عل|لل|ل)\s*(?P<target>.+)")
STOP_RX = re.compile(r"^\s*(?:(?:يا\s+)?سول\s*[،,]?\s*)?(?:توقفي|وقفي|وقّفي|قفي|اوقفي|أوقفي|ستوب|بريك)(?:\s+(?:السيارة|القيادة|هون|هنا|هلق|هلأ|الآن|الان|فورا|فوراً|يا\s+سول|سول))*\s*[.!؟]*\s*$")
# "drive to the place I marked" - the destination is already on the GPS, so no lookup is needed
CURRENT_DEST_WORDS = ("المكان المحدد", "المكان الذي حددته", "المكان الي حددته", "الوجهة", "الهدف", "النقطة المحددة", "المؤشر", "العلامة المحددة", "المحدد على الخريطة", "المحدد علي الخريطة")
SPEED_WORDS = (("ببطء", "slow"), ("بطيء", "slow"), ("على مهل", "slow"), ("بسرعة", "fast"), ("سريع", "fast"), ("متوسط", "normal"), ("عادي", "normal"))
SUPPLY_RX = re.compile(r"(ماذا|ما)\s+(لدينا|عندنا)|(موارد|مؤن|مخزون|المخزون|المؤن|الموارد)")
def _shami(text):
    """Levantine spoken forms the rules below do not know: "عالبيت" is "على البيت" (only before a place noun: "عالجيني" stays "treat me")."""
    t = (text or "").strip()
    t = re.sub(r"(?<![\u0621-\u064A])عال(?=(?:بيت|منزل|سيار|مخيم|مزرع|قاعد|طريق|مكان|علام|خريط))", "على ال", t)
    return re.sub(r"(?<![\u0621-\u064A])لل(?=(?:بيت|منزل|مخيم|مزرع|قاعد))", "إلى ال", t)          # "للبيت" -> "إلى البيت": the target then reads "البيت" (home), not "بيت" (an unknown place)
DRIVE_FILLER = ("شوي", "شوية", "شويه", "هلق", "هلأ", "الآن", "الان", "يلا", "يالله", "فورا", "فوراً", "هون", "هنا")
def _names_a_place(t, m, target):
    """Only "drive TO somewhere" names a place: the rest of a sentence after the verb is not a
    destination ("خذيني شوف المخزون" is not a trip to a place called "شوف المخزون")."""
    if target in DRIVE_FILLER: return False
    after = t[m.end(1):]
    return re.match(r"^\s*(?:بالسيارة|بالسياره)?\s*(?:إلى|الى|نحو|على|عل|لل|ل|ع)", after) is not None

def intents(text):
    t = _shami(text)
    out = []
    if HOME_RX.search(t) and not RG.is_question(t) and not HOME_NOT_RX.search(t): out.append(("set_home", {"name": "بيتنا"}))
    m = REMEMBER_RX.search(t)
    if m: out.append(("remember_place", {"name": (m.group("name") or "مكان محفوظ").strip(" .،"), "note": ""}))
    if SUPPLY_RX.search(t): out.append(("supplies", {}))
    moving = bool(INSIDE_RX.search(t) or WALK_RX.search(t))
    for act, opt in action_intents(t):
        if moving and act == "set_move_mode" and opt == "مشي": continue      # "walk to X" means go there, not walk mode
        if not DRIVE_RX.search(t) or act in ("board_vehicle", "exit_vehicle"): out.append(("action", {"action": act, "option": opt}))
    if INSIDE_RX.search(t) and not DRIVE_RX.search(t): out.append(("action", {"action": "sol_go_inside", "option": "home"}))
    elif WALK_RX.search(t) and not DRIVE_RX.search(t):
        tgt = WALK_RX.search(t).group("target").strip(" .،؟!")
        out.append(("action", {"action": "sol_goto", "option": "home" if any(w in tgt for w in ("البيت", "بيتنا", "المنزل")) else tgt}))
    if STOP_RX.search(t): out.append(("drive_stop", {}))
    else:
        m = DRIVE_RX.search(t)
        if m:
            target = (m.group("target") or "").strip(" .،؟!")
            speed = next((v for k, v in SPEED_WORDS if k in t), None)
            for k, _ in SPEED_WORDS: target = target.replace(k, "").strip()
            target = re.sub(r"^(بالسيارة|بالسياره)\s*", "", target).strip()
            target = re.sub(r"^(إلى|الى|نحو|ل)\s+", "", target).strip()
            if not target or target in ("السيارة", "السياره", "بالسيارة", "سيارة") or re.match(r"^(وقودي|و ?قودي)$", target):
                out.append(("drive_take_wheel", {}))                      # "get in and drive" with no place: sit, then ask where
            elif any(w in target for w in ("البيت", "بيتنا", "المنزل")): out.append(("drive_to", {"target": "home", "speed": speed}))
            elif any(w in target for w in CURRENT_DEST_WORDS): out.append(("drive_to", {"target": "current", "speed": speed}))
            elif any(w in target for w in ("العلامة", "الخريطة")): out.append(("drive_to", {"target": "marker", "speed": speed}))
            elif target and _names_a_place(t, m, target): out.append(("drive_to", {"target": "place", "name": target, "speed": speed}))
            elif target and target in DRIVE_FILLER: out.append(("drive_take_wheel", {}))
    if any(n in ("drive_take_wheel", "drive_to") for n, _ in out):     # driving: she sits behind the wheel, not as passenger
        out = [(n, a) for n, a in out if not (n == "action" and a.get("action") == "board_vehicle")]
    return out

_intents_core = intents
_A_CAR = r"(?:ال)?(?:سياره|سيارات|عربيه|فان|بيك اب|مركبه)"
_GARAGE = r"(?:ب|في\s+|عال?|عل[يا]\s+|ل)?(?:ال)?(?:كراج|جراج|موقف|مصف|باركينج)"
PARK_RX = re.compile(r"^(?:ا|ت)?(?:صفي|صف|ركني|ركن)\s+(?:" + _A_CAR + r"(?:\s+" + _GARAGE + r")?|" + _GARAGE + r")\s*$|^(?:حطي|دخلي)\s+" + _A_CAR + r"\s+" + _GARAGE + r"\s*$")
FARM_RX = re.compile(r"(المزرعة|المزرعه|الزرع|المزروعات|الحقل|المحصول|النباتات)")
FUEL_RX = re.compile(r"(وقود|بنزين)")
CARS_RX = re.compile(r"(سيار|المركب|العربية|العربيات)")
FARM_STOCK_RX = re.compile(r"(بذور|بذار|بزور|[اأ]دوات\s*(?:ال)?زراع|عد[ةه]\s*(?:ال)?زراع|معدات\s*(?:ال)?زراع|سماد)")
STOCK_ASK_RX = re.compile(r"(عن[اه]|عندنا|لدينا|عندك|معك|شوفي|شو|كم|وين|فيه|موجود|المخزن|ماذا|هل|(?:^|\s)في(?:\s|$))")
NONE_RX = re.compile(r"(?:ما\s*(?:في|فيه|عندي|معي|عنا|عندنا|لقيت)|مافي|لا\s+يوجد|ليس\s+لدي)")
HERS_RX = re.compile(r"(معك|عندك|بحقيبتك|بشنتتك|بجيبتك)")
ASK_RX = re.compile(r"(كم|شو|ماذا|ما\s|ما$|كيف|وين|أين|هل|اخبريني|خبريني|قولي)")
def intents(text):
    import farm_talk as FT
    if PARK_RX.search(FT.norm(text or "")): return [("park_car", {})]
    out = _intents_core(text)
    t = (text or "").strip()
    if any(n in ("drive_to", "drive_take_wheel", "drive_stop", "action", "set_home", "remember_place") for n, _ in out): return out
    if FARM_STOCK_RX.search(t) and STOCK_ASK_RX.search(t): return [(n, a) for n, a in out if n != "supplies"] + [("farm_stock", {"hers": HERS_RX.search(t) is not None})]
    if FARM_RX.search(t) and ASK_RX.search(t): return [(n, a) for n, a in out if n != "supplies"] + [("farm_report", {})]
    if FUEL_RX.search(t) and CARS_RX.search(t) and ASK_RX.search(t): return [(n, a) for n, a in out if n != "supplies"] + [("vehicle_report", {})]
    return out

GPS_REQ, GPS_STATE = "SolGPS_Request.txt", "SolGPS_State.txt"
GATE_ACTIONS = {"sol_gps_clear", "sol_drive", "sol_headlights", "sol_engine", "sol_car_wait", "sol_horn", "sol_goto", "sol_go_inside", "sol_eat", "sol_drink", "sol_give", "sol_fetch", "sol_read", "sol_attack_nearest", "sol_bandage_player", "sol_replace_bandage"}
ACT_SNAP, ACT_REQ, ACT_STATE = "SolActions_Snapshot.txt", "SolAct_Request.txt", "SolAct_State.txt"

def load_actions(lua_dir):
    try:
        with open(os.path.join(lua_dir, ACT_SNAP), encoding="ascii", errors="replace") as f: d = json.loads(f.read())
    except (OSError, ValueError): return []
    out = []
    for a in d.get("actions") or []:
        e = dict(a)
        for k in ("label", "section", "reason"):
            if isinstance(e.get(k), str): e[k] = unesc(e[k])
        if isinstance(e.get("options"), list): e["options"] = [unesc(o) if isinstance(o, str) else o for o in e["options"]]
        out.append(e)
    return out

def actions_text(actions):
    lines = []
    for a in actions:
        if a.get("kind") == "button": lines.append("%s: %s%s" % (a["id"], a.get("label", ""), "" if a.get("enabled", True) else " (unavailable now)"))
        elif a.get("kind") == "combo": lines.append("%s: choose one of %s (now: %s)" % (a["id"], " | ".join(a.get("options") or []), (a.get("options") or ["?"])[max(0, (a.get("selected") or 1) - 1)] if a.get("options") else "?"))
        elif a.get("kind") == "tick": lines.append("%s: on/off (%s, now %s)" % (a["id"], " / ".join(a.get("options") or []), "on" if a.get("on") else "off"))
        else: lines.append("%s: %s" % (a["id"], a.get("label", "")))
    return "\n".join(lines)

def action_result(lua_dir, rid):
    """The game's answer to request rid, or None while it has not answered."""
    try:
        with open(os.path.join(lua_dir, ACT_STATE), encoding="ascii", errors="replace") as f:
            st = dict(l.split("=", 1) for l in f.read().splitlines() if "=" in l)
    except OSError: return None
    if st.get("ack") == str(rid): return {"ok": st.get("ok") == "true", "reason": unesc(st.get("reason", ""))}
    if ("r%s" % rid) in st:                                                      # another sender's answer came after ours
        ok, _, why = st["r%s" % rid].partition("|")
        return {"ok": ok == "true", "reason": unesc(why)}
    return None

def run_action(lua_dir, action, option=None, wait=3.0):
    rid = write_request(os.path.join(lua_dir, ACT_REQ), {"action": action, "option": option or None})
    end = time.time() + wait
    while time.time() < end:
        r = action_result(lua_dir, rid)
        if r is not None: return r
        time.sleep(0.1)
    return {"ok": None, "reason": "sent; the game did not confirm yet", "rid": rid}

# Arabic requests -> (LF command, option keyword). The keyword is matched against the option labels in game.
VERB_MAP = [
    (r"(?:ألغي|الغي|إلغي|لغي|امسحي|إمسحي|شيلي|احذفي|بطلي)\s+(?:ال)?(?:تحديد|وجهة|وجهه|علامة|علامه|هدف|مؤشر|نقطة|نقطه)", ("sol_gps_clear", None)),
    (r"خلص(?:ي)?\s*(?:يا\s*)?(?:سول)?\s*(?:و\s*)?(?:انسي|إنسي)|انسي\s*(?:كل\s*)?(?:شي|شيء|الاوامر|الأوامر|اللي\s*(?:قلته|فات))|^\s*(?:سول\s*)?(?:انسي|إنسي)\s*[.!؟]?\s*$", ("sol_forget", None)),
    (r"(?:\u0627\u0647\u062a\u0645\u064a|\u0627\u0639\u062a\u0646\u064a|\u0631\u0627\u0639\u064a)\s+\u0628?(?:\u0627\u0644)?(?:\u0632\u0631\u0639|\u0645\u0632\u0631\u0648\u0639\u0627\u062a|\u0645\u062d\u0627\u0635\u064a\u0644|\u062d\u0642\u0644|\u0645\u0632\u0631\u0639\u0629|\u0646\u0628\u0627\u062a\u0627\u062a)|\u062d\u0635\u062f\u064a|\u0627\u0632\u0631\u0639\u064a|\u0627\u0633\u0642\u064a\s+(?:\u0627\u0644)?(?:\u0632\u0631\u0639|\u0645\u0632\u0631\u0648\u0639\u0627\u062a|\u0646\u0628\u0627\u062a\u0627\u062a)", ("sol_role", "farmer")),
    (r"(?:\u0642\u0637[\u064b-\u0652]*\u0639\u064a|\u0627\u0642\u0637\u0639\u064a)\s+(?:\u0627\u0644)?(?:\u062e\u0634\u0628|\u0627\u062e\u0634\u0627\u0628|\u0623\u062e\u0634\u0627\u0628|\u0627\u0634\u062c\u0627\u0631|\u0623\u0634\u062c\u0627\u0631|\u0634\u062c\u0631|\u062d\u0637\u0628)|\u0627\u062d\u062a\u0637\u0628\u064a", ("sol_role", "woodcutter")),
    (r"(?:\u0627\u0637\u0647[\u064a\u0649]|\u0627\u0637\u0628\u062e[\u064a\u0649]|\u0637\u0647[\u064a\u0649]|\u0637\u0628\u062e|\u0627\u0633\u0644\u0642[\u064a\u0649]|\u0627\u0642\u0644[\u064a\u0649])\s+(?:\u0627\u0644)?\u0628\u064a\u0636", ("sol_cook", "egg")),
    (r"(?:طفي|اطفي|أطفي|سكري|اقفلي|إطفئي|اطفئي)\s+(?:ال)?(?:سيارة|سياره|محرك|موتور).*(?:ستنيني|استنيني|انتظريني|ضلي|خليكي)", ("sol_car_wait", None)),
    (r"(?:طفي|اطفي|أطفي|سكري|إطفئي|اطفئي)\s+(?:ال)?(?:سيارة|سياره|محرك|موتور)", ("sol_engine", "off")),
    (r"(?:شغلي|شغّلي|ولعي|ولّعي|دوري|دوّري)\s+(?:ال)?(?:سيارة|سياره|محرك|موتور)", ("sol_engine", "on")),
    (r"(?:وقفي|وقّفي|طفي|اطفي|اسكتي|كفي|بطلي)\s+(?:ال)?(?:زمور|زامور|هورن|بوق|تزمير)|^\s*بس\s*[.!]*\s*$", ("sol_horn", "stop")),
    (r"زمري\s+(?:طول|على طول|عطول|كل)", ("sol_horn", "drive")),
    (r"(?:^|\s)زمري", ("sol_horn", "once")),
    (r"(?:طفي|اطفي|أطفي|سكري|اقفلي|إطفئي|اطفئي)\s+(?:ال)?(?:ضو|ضوء|ضواو|اضواء|أضواء|انوار|أنوار|نور|فوانيس|فانوس|لمبات|هدلايت)" , ("sol_headlights", "off")),
    (r"(?:شغلي|شغّلي|ولعي|ولّعي|اشعلي|أشعلي|افتحي|نوري|ضوي)\s+(?:ال)?(?:ضو|ضوء|ضواو|اضواء|أضواء|انوار|أنوار|نور|فوانيس|فانوس|لمبات|هدلايت)", ("sol_headlights", "on")),
    (r"اتبعيني|الحقي بي|تعالي معي|(?:ا|إ)?لحقيني", ("follow", None)),
    (r"ابقي هنا|انتظري هنا|لا تتحركي|ضلي هون|خليكي هون|استنيني هون|ستنيني هون", ("stay", None)),
    (r"احرسي", ("guard", None)),
    (r"تجمعي|ارجعي إلي|ارجعي الي|تعالي إلي|تعالي الي|تعالي هنا", ("regroup", None)),
    (r"انسحبي|اهربي", ("retreat", None)),
    (r"تسللي|بهدوء|امشي بتسلل", ("set_move_mode", "تسلل")),
    (r"اركضي|أسرعي|اسرعي", ("set_move_mode", "ركض")),
    (r"امشي\b(?!.*تسلل)", ("set_move_mode", "مشي")),
    (r"(?:^|\s)(?:ا|إ)?ركبي\s+(?:ال|عال|ع\s*|على\s+)?(?:سيارة|سياره|مركبة|مركبه|فان|بيك|معي|جنبي|ورا)|^\s*(?:(?:يا\s+)?سول\s+|يلا\s+)*(?:ا|إ)?ركبي\s*[.!؟]*\s*$|اصعدي السيارة|(?:^|\s)(?:ا|إ)?طلعي\s+(?:عال|ع\s*|على\s+)(?:ال)?(?:سيارة|سياره|فان)", ("board_vehicle", None)),
    (r"(?:ا|إ)?نزلي من (?:ال)?(?:سيارة|سياره|فان)|^\s*(?:(?:يا\s+)?سول\s+|يلا\s+)*(?:ا|إ)?نزلي\s*[.!؟]*\s*$|(?:ا|إ)?طلعي من (?:ال)?(?:سيارة|سياره|فان)", ("exit_vehicle", None)),
    (r"لا تطلقي|أمسكي النار|امسكي النار|توقفي عن إطلاق", ("hold_fire", None)),
    (r"أطلقي النار|اطلقي النار|اشتبكي", ("fire_at_will", None)),
    (r"هاجمي|اقتلي|اضربي", ("sol_attack_nearest", None)),
    (r"(ضمدي|ضمّدي|عالجي)\s*(جرحي|جروحي|يدي|ساقي|رأسي|راسي)|ضمديني|ضمّديني|عالجيني", ("sol_bandage_player", None)),
    (r"(غيري|بدلي|استبدلي)\s*(الضماد|ضمادك|الضمادة)", ("sol_replace_bandage", None)),
    (r"(كتاب|كتابا|مجلة|رواية).*(تقرئ|اقرئ|تقري|اقري|قراءت|تقرأ)|(تقرئ|اقرئ|تقرأ).*(كتاب|مجلة|رواية)", ("sol_fetch", "book:read")),
    (r"(اجلبي|احضري|أحضري|ابحثي عن|فتشي عن)\s*(لنفسك\s*)?(كتاب|كتابا|مجلة|رواية)", ("sol_fetch", "book")),
    (r"(اجلبي|احضري|أحضري)\s*(طعام|أكل|اكل)", ("sol_fetch", "food")),
    (r"(اجلبي|احضري|أحضري)\s*(ماء|مويه|ميه)", ("sol_fetch", "water")),
    (r"\b(كلي|تناولي|افطري|تغدي|تعشي)\b", ("sol_eat", None)),
    (r"\b(اشربي|ارتوي)\b", ("sol_drink", None)),
    (r"(?:سلاح(?:ي|اتي)|(?:ا|أ|إ)?سلحتي|(?:ال)?سلاح(?:ين)?)\s+(?:ال)?سرّ?(?:ي|يّ)(?:ة|ه|ين|يين)?(?![\u0621-\u064A])", ("sol_secret", "give")),   # secret_loadout
    (r"(أعطيني|اعطيني|ناوليني|هاتي|رجعي لي|أرجعي لي|ارجعي لي)\s*(كل شيء|كل شي|كلشي|كل ما معك|كل ما في حقيبتك|الكل)", ("sol_give", "all")),
    (r"(ما|اللي|الذي)\s*(وضعته|حطيته|أعطيتك|اعطيتك|اعطيتكم)|(رجعي|أرجعي|ارجعي|أعيدي|اعيدي)\s*(لي\s*)?(أغراضي|اغراضي|حاجاتي|أشيائي|اشيائي)", ("sol_give", "mine")),
    (r"(أعطيني|اعطيني|ناوليني|هاتي)\s*(ماء|مويه|ميه|قارورة ماء)", ("sol_give", "water")),
    (r"(أعطيني|اعطيني|ناوليني|هاتي)\s*(طعام|أكل|اكل|شيئا آكله|شيء آكله)", ("sol_give", "food")),
    (r"ابحثي عن مؤن|فتشي|ابحثي في", ("set_scavenge", "on")),
    (r"(?:وقفي|خلص(?:ي)?|بطلي)\s+(?:شغل\s+)?(?:ال)?(?:دجاج|جاج|حيوانات)", ("sol_animals", "stop")),
    (r"(?:اجمعي|لمي|جيبي|شيلي)\s+(?:ال)?بيض", ("sol_animals", "eggs")),
    (r"(?:اهتمي|اعتني|دبري|رعي|طعمي|اطعمي|اسقي)\s+(?:ب)?(?:ال)?(?:دجاج|جاج|حيوانات)", ("sol_animals", "care")),
    (r"(?:وقفي|وقّفي|خلص(?:ي)?|بطلي|كفي|بكفي)\s+(?:ال)?(?:ترتيب|فرز)", ("sol_sort", "stop")),
    (r"(?:رتّ?بي(?:لي|لنا)?|نظّ?مي(?:لي|لنا)?|فرّ?زي|رتب)\s+(?:ال)?(?:اغراض|أغراض|غراض|اشياء|أشياء|البيت|المخزن|الصناديق|الخزاين|الخزانات)|(?:حطي|حطّي|رجعي|رجّعي)\s+كل\s+(?:شي|شغلة|غرض)\s+(?:ب|في\s+|ع|ل)?(?:محل|مكان)", ("sol_sort", "run")),
    (r"اقرئي|اقري", ("sol_read", None)),
]
# address_book: Sol's address book lives in the game (SolAddressBook.lua, action sol_address). One action; these are its words.
ADDR_TOWNS = (("مولدرو", "Muldraugh"), ("مولدراو", "Muldraugh"), ("ويست بوينت", "West Point"), ("وست بوينت", "West Point"), ("روزوود", "Rosewood"),
              ("ريفرسايد", "Riverside"), ("لويفيل", "Louisville"), ("لويزفيل", "Louisville"), ("براندنبرغ", "Brandenburg"), ("اكرون", "Ekron"),
              ("إكرون", "Ekron"), ("ايرفينغتون", "Irvington"), ("إيرفينغتون", "Irvington"), ("مارش ريدج", "March Ridge"), ("ديكسي", "Dixie"),
              ("ايكو كريك", "Echo Creek"), ("إيكو كريك", "Echo Creek"))
ADDR_HOUSE = re.compile(r"(?:إعلان|اعلان)|للبيع|للإيجار|للايجار")
ADDR_STASH = re.compile(r"مخب[أاى]|غنيم|كنز")
ADDR_AREA = re.compile(r"منطق[ةه]")
ADDR_CUE = re.compile(r"عنوان|عناوين|دفترك|منطق[ةه]\s*(?:اللي|يلي)|دفتر\s*(?:ال)?عناوين|(?:إعلان|اعلان)|للبيع|للإيجار|للايجار|مخب[أاى]|غنيم|كنز")
ADDR_LIST = re.compile(r"عناوين|دفترك|دفتر\s*(?:ال)?عناوين")
ADDR_GO = re.compile(r"خديني|خذيني|وديني|وصليني|رجعيني|روحي|سوقي|امشي|خلينا\s*نروح|بدي\s*روح|يلا\s+ع")
ADDR_LOOTED = re.compile(r"خلصنا\s*(?:من|منو|منه)|زرنا|انزار|فضّ?يناه|فضّ?ينا|اخدنا\s+(?:كل\s*)?(?:شي|الغراض|الغنيمة)")
def address_intent(text):
    """The option for sol_address, or None when the sentence is not about her address book."""
    t = western_digits(text or "")
    if not ADDR_CUE.search(t): return None
    if ADDR_STASH.search(t) and ADDR_LOOTED.search(t): verb = "looted"
    elif ADDR_GO.search(t): verb = "go"
    elif ADDR_LIST.search(t): return "list"
    else: return None
    kind = "house" if ADDR_HOUSE.search(t) else "stash" if ADDR_STASH.search(t) else "area" if ADDR_AREA.search(t) else "any"
    words = re.findall(r"[A-Za-z]+|\d+", t)
    for ar, en in ADDR_TOWNS:
        if ar in t: words.append(en)
    return "%s:%s:%s" % (verb, kind, " ".join(words).lower())
def address_reply(r):
    """Her own line from the game; a code (switch off, no answer yet) becomes a short line."""
    if not isinstance(r, dict) or r.get("ok") is None: return "لحظة، عم دوّر بالدفتر."
    why = str(r.get("reason") or "")
    if re.search(r"[\u0600-\u06FF]", why): return why
    return "ما قدرت إفتح الدفتر هلأ."
GIVE_ANY = re.compile(r"(أعطيني|اعطيني|ناوليني|هاتي)\s+(?P<item>.+)")
def action_intents(text):
    t = text or ""
    for rx, act in VERB_MAP:
        if re.search(rx, t): return [act]
    m = GIVE_ANY.search(t)
    if m:
        item = m.group("item").strip(" .،؟!")
        # Arabic item names are left to the model, which calls do_action sol_give with the English game name
        if not re.search(r"[\u0600-\u06FF]", item): return [("sol_give", item)]
    return []
def gps_request(lua_dir, fields):
    return write_request(os.path.join(lua_dir, GPS_REQ), fields)

def gps_result(lua_dir, rid, wait=3.0):
    """The game's answer to one GPS request (SolGPS_State.txt with ack = rid)."""
    end = time.time() + wait
    while time.time() < end:
        try:
            with open(os.path.join(lua_dir, GPS_STATE), encoding="ascii", errors="replace") as f:
                st = dict(l.split("=", 1) for l in f.read().splitlines() if "=" in l)
            if st.get("ack") == str(rid): return st
        except OSError: pass
        time.sleep(0.15)
    return None

# what Sol says when the game refused (GPS and action reasons)
REASON_AR = {
    "player_aboard": "انزل لحظة لأجلس خلف المقود، ثم اركب بجانبي",
    "board_passenger": "أنا خلف المقود، اركب من باب الراكب وننطلق",
    "moving_to_wheel": "أنتقل إلى مقعد السائق",
    "await_destination": "أنا خلف المقود، قل لي إلى أين نذهب",
    "gps_unconfirmed": "ثواني، عم جرّب",
    "no_vehicle_near": "ما في سيارة قريبة",
    "vehicle is not in the loaded world": "السيارة بعيدة عني هلأ",
    "hotwiring": "ما في مفتاح، رح شرّطها، وبس خلّص قلي نمشي",
    "no_usable_car": "السيارات القريبة كلها مقفلة وما معنا مفتاحها",
    "no_way_round": "الطريق مسكر قدامي وما في لف حواليه، وقفت",
    "not_in_vehicle": "لسنا في سيارة",
    "map_not_opened": "افتح الخريطة مرة أولًا، أو اختر الوجهة بالزر الأيمن عليها",
    "no_marker": "لا توجد علامة على الخريطة",
    "no_destination": "حدّد لي الوجهة أولًا",
    "home_not_set": "لسا ما حددنا بيتنا",
    "too_far_to_hand_over": "اقترب مني لأعطيك",
    "she_has_none": "ليس معي منه",
    "your_bags_are_full": "حقائبك ممتلئة",
    "no_food_in_her_bag": "ليس معي طعام",
    "no_clean_water_in_her_bag": "ليس معي ماء نظيف",
    "not_found_nearby": "لم أجد ذلك قريبًا",
    "no_building_near": "لا يوجد مبنى قريب",
    "no_zombie_near": "لا يوجد زومبي قريب",
    "not_in_driver_seat": "لازم أكون بمقعد السائق لأشغلها.",
    "not_in_a_car": "أنا مو بسيارة هلأ.",
    "no_fuel": "ما في بنزين.",
    "battery_dead": "البطارية فاضية.",
    "no_battery": "ما في بطارية بالسيارة.",
    "no_key": "ما معي مفتاح هالسيارة. شغلها إنت أو عطيني المفتاح وبسوق.",
    "engine_broken": "المحرك خربان.",
    "engine_control_unavailable": "ما بقدر أتحكم بالمحرك بهالسيارة.",
    "horn_unavailable": "ما بقدر أزمّر بهالسيارة.",
}
def reason_ar(reason):
    r = str(reason or "")
    for k, v in REASON_AR.items():
        if k in r: return v
    return None

def drive_reply(result):
    r = result if isinstance(result, dict) else {}
    reason = str(r.get("reason") or r.get("error") or "")
    if reason.endswith("no_key"): reason = "no_key"
    if reason == "walking_to_door": return "رايحة عالمقود وبنطلق."
    if r.get("error") or r.get("ok") is False: return reason_ar(reason) or "ما قدرت أسوق هلأ."
    if reason == "moving_to_wheel": return "رايحة عالمقود وبنطلق."
    if r.get("result") == "arrived" and reason == "arrived": return "وصلنا."
    if r.get("say"): return r["say"]
    return "تمام، انطلقت."

def _drive_outcome(lua_dir, rid, base):
    st = gps_result(lua_dir, rid, wait=3.0)
    out = dict(base)
    if not st:
        out.update(ok=False, confirmed=False, reason="gps_unconfirmed")
        return out
    reason = st.get("reason") or ""
    waiting = reason in ("board_passenger", "moving_to_wheel", "walking_to_door", "await_destination")
    cancelled = st.get("result") in ("arrived", "interrupted") and reason not in ("arrived", "") and not waiting
    failed = (st.get("result") == "failed" and not waiting) or cancelled
    if cancelled: reason = "drive_cancelled:" + reason
    out.update(ok=not failed, confirmed=True, result=st.get("result"), reason=reason)
    return out

PHONE_WAIT_S157 = 12       # seconds for the phone model; it answered the full card in about 5 (sol_mind.log 2026-11-15)

def fix_on(lua_dir, name):
    import sol_fixes                                                             # s152: the lab file, else the main copy's file
    return sol_fixes.on(lua_dir, name)

def home_parking(snap, home, reach=60):
    """The parking spot he marked for this home: a free one first, the nearest to the house among those. None when there is none near the home."""
    s = snap or {}
    spots = [p for p in (s.get("solParkings") or ([s["solParking"]] if isinstance(s.get("solParking"), dict) else [])) if isinstance(p, dict) and p.get("x") is not None]
    spots = [p for p in spots if (p["x"] - home["x"]) ** 2 + (p["y"] - home["y"]) ** 2 <= reach * reach]
    if not spots: return None
    cars = [v for v in s.get("vehicles") or [] if isinstance(v, dict) and v.get("x") is not None]
    me = s.get("sol") or {}
    def taken(p):
        x1, x2, y1, y2 = p.get("x1", p["x"] - 1), p.get("x2", p["x"] + 1), p.get("y1", p["y"] - 1), p.get("y2", p["y"] + 1)
        for v in cars:
            if me.get("x") is not None and abs(v["x"] - me["x"]) < 1.5 and abs(v["y"] - me["y"]) < 1.5: continue     # her own car
            if x1 <= v["x"] <= x2 + 1 and y1 <= v["y"] <= y2 + 1: return True
        return False
    spots.sort(key=lambda p: (taken(p), (p["x"] - home["x"]) ** 2 + (p["y"] - home["y"]) ** 2))
    return spots[0]

def drive_to(lua_dir, args, mem, snap=None):
    """Resolve the destination (home / remembered place / map marker) and hand it to the game's GPS."""
    t = args.get("target"); speed = args.get("speed")
    if t == "marker":
        rid = gps_request(lua_dir, {"action": "drive", "target": "marker", "speed": speed})
        return _drive_outcome(lua_dir, rid, {"sent": "map marker"})
    if mem is None: return {"error": "no world data yet"}
    if t == "home":
        h = mem.data.get("home")
        if not h and isinstance((snap or {}).get("solHome"), dict) and snap["solHome"].get("x") is not None: h = snap["solHome"]   # the home or base he set in the game
        if not h: return {"error": "home_not_set"}
        spot = home_parking(snap, h) if fix_on(lua_dir, "home_parks") else None
        if spot:                                                                   # home is where the car stands at home: the marked parking, not the house itself
            rid = gps_request(lua_dir, {"action": "drive", "x": spot["x"], "y": spot["y"], "name": "الكراج", "speed": speed})
            return _drive_outcome(lua_dir, rid, {"sent": "home parking", "x": spot["x"], "y": spot["y"]})
        if fix_on(lua_dir, "home_parks"):                                          # no parking marked: the road beside the house, never into it
            rid = gps_request(lua_dir, {"action": "drive", "x": h["x"], "y": h["y"], "near": "1", "name": "جنب البيت", "speed": speed})
            return _drive_outcome(lua_dir, rid, {"sent": "near home", "x": h["x"], "y": h["y"], "say": "ما في مكان صف محدد، رح وقّف عالطريق جنب البيت."})
        rid = gps_request(lua_dir, {"action": "drive", "x": h["x"], "y": h["y"], "name": h.get("name") or "home", "speed": speed})
        return _drive_outcome(lua_dir, rid, {"sent": "home", "x": h["x"], "y": h["y"]})
    name = (args.get("name") or "").strip()
    for p in reversed(mem.data.get("places") or []):
        if name and (name in p["name"] or p["name"] in name):
            rid = gps_request(lua_dir, {"action": "drive", "x": p["x"], "y": p["y"], "name": p["name"], "speed": speed})
            return _drive_outcome(lua_dir, rid, {"sent": p["name"], "x": p["x"], "y": p["y"]})
    return {"error": "unknown place: " + name}

LINK_TAG = re.compile(r"\[\s*(?:فعل|action)\s*:\s*([A-Za-z_]+)\s*(?:\|\s*([^\]]+))?\]")
LINK_GOAL_TAG = re.compile(r"\[\s*(?:هدف|goal)\s*:\s*([A-Za-z_]+)\s*(?:\|\s*([^|\]]+))?\s*(?:\|\s*([^\]]+))?\]")
LINK_PRIMER = (
    "أنتِ سول، رفيقة ناجية في لعبة Project Zomboid، والرسائل القادمة تأتي من اللعبة نفسها عبر برنامج يسمى Sol Link. "
    "اللاعب اسمه " + PLAYER_NAME + " ويكلمك بالعربية، فردّي بالعربية بجملة أو جملتين كما تتكلم رفيقة، بلا قوائم ولا رموز ولا كتل كود أبدًا، "
    "واكتبي الأرقام 0123456789. كل رسالة فيها حال العالم الحقيقي الآن وقائمة الأفعال التي تستطيعين تنفيذها؛ أنتِ طبقة Sol العليا التي تختار الفعل أو الخطة، وLiving Fellows يوفر بعض آليات التنفيذ الأساسية. "
    "إن طلب اللاعب شيئًا منها فاكتبي وسمًا مثل [فعل: follow] أو [فعل: sol_give | water]. سيُرسل الفعل إلى اللعبة بعد توليد ردك ثم يُحذف الوسم؛ لا تقولي إنه اكتمل في الرد نفسه، بل صيغيه كبدء محاولة، وستُرفق نتيجة اللعبة بعد التنفيذ. "
    "للطلبات متعددة الخطوات استخدمي وسم [هدف: ...] من قائمة الأهداف التي تصلك مع كل رسالة، بدل سلسلة أفعال منفردة. "
    "لا تخترعي أفعالًا خارج القائمة، ولا تدّعي أنك فعلتِ شيئًا لم يُنفَّذ، ولا تختلقي أرقامًا أو أماكن ليست في حال العالم."
)

def resolve_and_run(lua_dir, aid, opt, mem, snap, log=print):
    """Actions that need Sol Mind's memory are resolved here: driving (home / marker / place) goes to the GPS;
    walking to home or a remembered place becomes x,y; 'inside' prefers the saved home when it is near."""
    o = (opt or "").strip()
    if aid == "sol_drive":
        low = o.lower()
        if any(w in o for w in ("السيارة", "السياره")) or low in ("car", "the car", "wheel"):
            rid = gps_request(lua_dir, {"action": "take_wheel"})
            return _drive_outcome(lua_dir, rid, {"sent": "take_wheel"})
        if not o or any(w in low for w in ("home", "بيت", "منزل")): args = {"target": "home"}
        elif any(w in low for w in ("marker", "map", "علامة", "خريطة")): args = {"target": "marker"}
        else: args = {"target": "place", "name": o}
        return drive_to(lua_dir, args, mem, snap)
    if aid in ("sol_goto", "sol_go_inside") and mem is not None and not re.match(r"^-?\d+\s*,\s*-?\d+$", o):
        h = mem.data.get("home")
        if not h and isinstance((snap or {}).get("solHome"), dict) and snap["solHome"].get("x") is not None: h = snap["solHome"]   # the home or base he set in the game
        if aid == "sol_go_inside":
            p = (snap or {}).get("player") or {}
            if h and p.get("x") is not None and abs(p["x"] - h["x"]) + abs(p["y"] - h["y"]) <= 60: o = "%d,%d" % (h["x"], h["y"])
            else: o = ""
        elif o in ("", "home") or any(w in o for w in ("البيت", "بيتنا", "المنزل", "home")):
            if not h: return {"ok": False, "reason": "home_not_set"}
            o = "%d,%d" % (h["x"], h["y"])
        else:
            hit = next((pl for pl in reversed(mem.data.get("places") or []) if o in pl["name"] or pl["name"] in o), None)
            if not hit: return {"ok": False, "reason": "unknown_place: " + o}
            o = "%d,%d" % (hit["x"], hit["y"])
    return run_action(lua_dir, aid, o or None)

MOVE_ORDERS = frozenset(("park_car", "drive_take_wheel", "drive_stop", "drive_to", "follow", "stay", "guard", "regroup", "retreat", "board_vehicle", "exit_vehicle", "sol_let_player_drive", "sol_pilot_helicopter", "sol_goto", "sol_drive", "sol_farm", "sol_forget"))

def car_is_full(snap):
    """s95b: the percent when the car SHE would fill is at 99% or more (goal_engine.tank_gate); None otherwise."""
    gate, pct = tank_gate(snap)
    return pct if gate == "full" else None

def car_is_full_s95(snap):
    """Before s95b: the car nearest HIM, and only a tank at the brim. Kept for the replay test."""
    s = snap or {}
    me = s.get("player") or {}
    px, py = me.get("x"), me.get("y")
    if px is None or py is None: return None
    best, bd = None, 30 * 30
    for v in s.get("vehicles") or []:
        if not isinstance(v, dict) or v.get("x") is None or v.get("y") is None: continue
        d = (v["x"] - px) ** 2 + (v["y"] - py) ** 2
        if d < bd: best, bd = v, d
    if best is None: return None
    fuel, cap = best.get("fuel"), best.get("fuelMax")
    if not isinstance(fuel, (int, float)) or not isinstance(cap, (int, float)) or cap <= 0: return None
    return int(round(100.0 * fuel / cap)) if fuel >= cap - 0.01 else None

class Chat:
    def __init__(self, lua_dir, log=print, ask=None, mind=None, mind_lock=None):
        self.dir = lua_dir; self.log = log; self.ack = 0
        self.goals = GoalEngine(lua_dir, mind=mind, mind_lock=mind_lock, log=log)
        self.goals.start()
        self.status, self.code = "idle", ""
        self.ask = ask or self._ask_provider
        self.hist, self._hist_file = [], None                                   # filled from this world's own file once the world is known
        self.lock = threading.Lock()
        self.pending_card = None
        self._link_primed, self._link_count = None, 0
        if ask is None:
            try:
                if SS.load_config().get("source") == "bridge": SS.start_link(log)    # chosen in the game: runs until switched
            except Exception as e: log("sol link: not started: %r" % (e,))
            try:
                import voice_service
                voice_service.start(lua_dir, self, log)                               # the game's voice button
            except Exception as e: log("voice: not started: %r" % (e,))

    def _bind_history(self, mem):
        """Each world has its own conversation, kept with the rest of that world's memory."""
        if mem is None: return
        path = os.path.join(mem.dir, "chat_history.json")
        if path == self._hist_file: return
        try:
            with open(path, encoding="utf-8") as f: loaded = json.load(f)[-KEEP:]
        except (OSError, ValueError): loaded = []
        self.hist, self._hist_file = loaded, path

    def _save(self):
        if not self._hist_file: return
        try:
            with open(self._hist_file, "w", encoding="utf-8") as f: json.dump(self.hist[-KEEP:], f, ensure_ascii=False)
        except OSError: pass

    def publish(self):
        with self.lock:
            st = {"ack": self.ack, "status": self.status, "code": self.code}
            msgs = self.hist[-30:]
            st["count"] = len(msgs)
            for i, m in enumerate(msgs, 1): st["m%d" % i] = "%s|%s" % (m["role"], esc(m["text"]))
        tmp = os.path.join(self.dir, STATE + ".tmp")
        with open(tmp, "w", encoding="ascii", newline="\n") as f:
            f.write("".join("%s=%s\n" % (k, v) for k, v in st.items()))
        os.replace(tmp, os.path.join(self.dir, STATE))

    def _world(self):
        snap = W.load_snapshot(self.dir)
        mem = W.Memory(snap["world"]) if snap and snap.get("world") and snap["world"].get("name") else None
        self._bind_history(mem)
        return snap, mem

    def gps_state(self):
        try:
            with open(os.path.join(self.dir, GPS_STATE), encoding="ascii", errors="replace") as f:
                return dict(l.split("=", 1) for l in f.read().splitlines() if "=" in l)
        except OSError: return None

    def system_prompt(self, snap, mem):
        g = self.gps_state()
        gps = ""
        if g and g.get("result"):
            gps = "\nCar / GPS: %s%s, distance %s tiles, speed setting %s, fuel %s%%%s." % (g.get("result"), (" / " + g["phase"]) if g.get("phase") else "", g.get("distance") or "?",
                  g.get("speed") or "?", g.get("fuel") or "?", (", reason " + g["reason"]) if g.get("reason") else "")
        return SYSTEM_BASE + SYSTEM_WORLD + GAME_KNOWLEDGE + "\n\nSituation:\n" + W.situation_text(snap, mem) + gps

    def _pre_intents(self, history, snap, mem):
        # High-confidence multi-step goals are accepted before the model speaks.
        # This is the deterministic safety layer; semantic provider goals use request_goal below.
        done = []
        self._turn_action_results = []
        text = history[-1]["text"] if history else ""
        hello = greeting_line(text)
        if hello:
            self._forced = hello
            done.append("answered a greeting")
            return done
        addr = address_intent(text)
        if addr is not None:                                                     # address_book: one action, the book lives in the game
            r = run_action(self.dir, "sol_address", addr, wait=3.0)
            self._turn_action_results.append(r)
            done.append("action sol_address %s -> %s" % (addr, json.dumps(r, ensure_ascii=False)))
            self.log("chat: address %s -> %s" % (addr, r))
            self._forced = address_reply(r)
            return done
        if self._far_order(text, snap, done, (history[-1].get("said") if history else None) or text): return done
        said = self._farm_orders(text, snap, mem, done)
        if said: return done
        said = MA.answer(text, snap, mem, lambda: self._station_list(), lambda: self._street_now(), GZ.load(), lambda: self._gardens())
        if said:
            self._forced = said
            return ["answered from the Mind's own memory"]
        goal = IE.parse_high_confidence(text, snap)
        if goal:
            self._stop_farm_if_running(snap)                                    # any other order from him ends what she was doing on the farm
            r = self.goals.submit(goal)
            self._turn_action_results.append(r)
            done.append("goal %s -> %s" % (goal.get("intent"), json.dumps(r, ensure_ascii=False)))
            self.log("chat: goal %s -> %s" % (goal.get("intent"), r))
            if r.get("ok"):
                self._forced = (self.goals.wait_answer(r.get("goalId")) or "لحظة، عم شوف.") if goal.get("intent") == "station_query" else ("لسا عم حاول، لحظة." if r.get("status") == "already_running" else order_line(goal))
                return done
        for name, args in intents(text):
            self._player_takes_over(args.get("action") if name == "action" else name)
            if name in ("action", "drive_take_wheel", "drive_stop", "drive_to", "park_car"): self._stop_farm_if_running(snap)
            if name == "drive_take_wheel":
                rid = gps_request(self.dir, {"action": "take_wheel"})
                r = _drive_outcome(self.dir, rid, {"sent": "take_wheel"})
                self._turn_action_results.append(r)
                done.append("drive_take_wheel -> %s" % json.dumps(r, ensure_ascii=False))
                self.log("chat: drive_take_wheel %s" % r)
                self._forced = drive_reply(r)
                continue
            if name == "drive_stop":
                gps_request(self.dir, {"action": "stop"})
                self._turn_action_results.append({"ok": None, "reason": "stop_sent"})
                done.append("drive_stop -> stop request sent; game confirmation pending")
                self._forced = "وقفت."
                continue
            if name == "drive_to":
                r = drive_to(self.dir, args, mem, snap); self._turn_action_results.append(r)
                done.append("drive_to -> %s" % json.dumps(r, ensure_ascii=False)); self.log("chat: drive %s" % r)
                self._forced = drive_reply(r); continue
            if name == "action":
                r = resolve_and_run(self.dir, args["action"], args.get("option"), mem, snap); self._turn_action_results.append(r)
                done.append("action %s -> %s" % (args["action"], json.dumps(r, ensure_ascii=False)))
                self._remember_action(args["action"], args.get("option"))
                if args["action"] == "sol_role": self._forced = role_reply(args.get("option"), r)
                if args["action"] == "sol_secret": self._forced = secret_reply(r)
                self.log("chat: action %s %s -> %s" % (args["action"], args.get("option"), r)); continue
            if name in ("farm_report", "vehicle_report"):
                try:
                    import sol_templates as TPL
                    if name == "farm_report": snap = self._with_farm_report(snap)
                    self._forced = TPL.reply(name, snap, mem)
                except Exception as e:
                    self.log("chat: template %s failed: %r" % (name, e))
                done.append("%s answered from the game's data" % name)
                continue
            if name == "park_car":
                self._park_car(snap); done.append("parking: answered from the marked area")
                continue
            if name == "farm_stock":
                # Same scan as the inventory table; the model never words what is or is not in stock.
                rows = W.farm_stock_rows(snap, hers=bool(args.get("hers")))
                if rows:
                    self._forced = ("هاد اللي معي من البذور وأدوات الزراعة، بالجدول." if args.get("hers") else "هاد اللي عنا من البذور وأدوات الزراعة، بالجدول.")
                    self.pending_card = rows
                else:
                    self._forced = "ما معي بذور ولا أدوات زراعة." if args.get("hers") else "ما لقيت بذور ولا أدوات زراعة بالمخزون اللي فحصته."
                done.append("farm stock answered from the inventory scan")
                continue
            if name == "supplies":
                # The inventory card is the detailed report; avoid repeating its
                # counts and warnings in the chat bubble above it.
                self._forced = "عرضت لك تفاصيل المخزن في الجدول."
                if snap: self.pending_card = W.supplies_table(snap, mem)
                done.append("supplies table shown to the player")
                continue
            if mem is None: continue
            r = W.run_tool(name, args, snap, mem, W.load_recipes(self.dir)); done.append("%s -> %s" % (name, json.dumps(r, ensure_ascii=False)[:200]))
            if name == "set_home" and isinstance(r, dict) and r.get("home"):
                self._forced = "تمام، صار هون بيتنا."
                self.log("chat: home in the game -> %s" % run_action(self.dir, "sol_set_home", None, wait=2.0))       # the game's own "go home" and the farm read this one
            self.log("chat: intent %s -> %s" % (name, str(r)[:120]))
        return done

    # ---------------------------------------------------------------- the farm (farm_talk.py words it)
    def _park_car(self, snap):
        spot = (snap or {}).get("solParking")
        if not isinstance(spot, dict) or spot.get("x") is None:
            self._forced = "ما لقيت مكان محدد لصف السيارات. حدده إلي وبصف فيه."
            return
        rid = gps_request(self.dir, {"action": "drive", "x": int(spot["x"]), "y": int(spot["y"]), "name": "الكراج", "speed": "slow"})
        r = _drive_outcome(self.dir, rid, {"sent": "parking", "x": spot["x"], "y": spot["y"]})
        self.log("chat: park car -> %s" % r)
        started = r.get("ok") or str(r.get("reason")) in ("moving_to_wheel", "walking_to_door")
        self._forced = "رايحة صفها بالكراج." if started else drive_reply(r)
        self._park_waiting = {"t": time.time()} if started else None

    def _say_later(self, line):
        """A line that comes after the turn that asked for it."""
        with self.lock: self.hist.append({"role": "sol", "text": line, "t": time.time()})
        self._save(); self.publish()

    def _park_watch(self):
        """She promised to park: he hears how it ended, and the car ends up inside the marked area, not some tiles short."""
        w = getattr(self, "_park_waiting", None)
        if not w: return
        if w.get("phase") == "settle":
            r = run_action(self.dir, "sol_errand_park_status", None, wait=2.5)
            if not (isinstance(r, dict) and r.get("ok")) or r.get("reason") == "done" or time.time() - w["since"] > 60:
                self._park_waiting = None
                self._say_later("صفيتها.")
            return
        if time.time() - w["t"] > 600:
            self._park_waiting = None
            return
        g = self.gps_state() or {}
        result, reason = str(g.get("result") or ""), str(g.get("reason") or "")
        if result == "arrived" and reason in ("arrived", ""):
            r = run_action(self.dir, "sol_errand_park", None, wait=2.5)
            if isinstance(r, dict) and r.get("ok"): w.update(phase="settle", since=time.time())
            else:
                self._park_waiting = None
                self._say_later("وصلنا عالكراج.")
        elif result in ("failed", "interrupted") and reason not in ("walking_to_door", "moving_to_wheel", "await_destination", "board_passenger", ""):
            self._park_waiting = None
            if "player" not in reason: self._say_later(drive_reply({"ok": False, "reason": reason}))

    def _far_state(self, snap):
        """None when her body is in the world (or there is no Sol at all); otherwise what the game says about the saved her."""
        if (snap or {}).get("sol") and not snap["sol"].get("away"): return None
        r = run_action(self.dir, "sol_far", "status", wait=2.5)
        reason = str(r.get("reason")) if isinstance(r, dict) and r.get("ok") else ""
        return reason if reason.startswith(("far:", "awake:", "waiting:")) or reason in ("seeking", "placed") else None

    def _far_order(self, text, snap, done, said=None):
        """Her body is not here: nothing may be answered as if it were. True when the message was an order and has been answered."""
        if not FAR_WAKE: return False
        if _CARS_Q_RX.search(text or "") and _CARS_ASK_RX.search(text or "") and not _CARS_ORDER_RX.search(text or "") and self._far_cars(snap, done): return True   # far_car
        import farm_talk as FT
        goal = IE.parse_high_confidence(text, snap)
        found = [(n, a) for n, a in intents(text) if n not in FAR_NO_BODY_NEEDED and a.get("action") not in FAR_NO_BODY_NEEDED]
        farm = FT.order(text)
        wake = asks_if_awake(text)
        come_words = _COME_RX.search(text or "") is not None and _NOT_COME_RX.search(text or "") is None
        if not goal and not found and not farm and not wake and not come_words: return False
        far = self._far_state(snap)
        if far is None:
            if not wake or not (snap or {}).get("sol"): return False
            self._forced = "إيه فايقة، أنا هون."
            done.append("answered: she is awake and here")
            return True
        coming = far.startswith("waiting:") or far in ("seeking", "placed")
        said = said or text
        board = any(n == "action" and a.get("action") == "board_vehicle" for n, a in found)          # far away, "get in the car" means: come by car
        called = board or come_words or (goal or {}).get("intent") == "fetch_player" or any(n == "action" and a.get("action") in ("regroup", "follow") for n, a in found)
        if wake:
            self._far_wake(far, coming)
        elif coming:
            self._forced = far_wait_line(far, "جاية، باقي %s.") if far.startswith("waiting:") else FAR_ON_WAY
        elif called:
            self._far_come(goal, board or _CAR_RX.search(said or "") is not None)
        else:
            self._forced = FAR_LINE
            self.log("chat: far order refused honestly (%s)" % far)
        done.append("answered: she is far away")
        return True

    def _far_cars(self, snap, done):
        """far_car: which cars are around her, from the game's own saved rows. False when she is here or the switch is off (as before)."""
        far = self._far_state(snap)
        if far is None: return False
        r = None
        for _ in range(4):
            r = run_action(self.dir, "sol_far", "cars", wait=2.5)
            if not (isinstance(r, dict) and not r.get("ok") and r.get("reason") == "scanning"): break
            time.sleep(0.8)
        reason = str(r.get("reason")) if isinstance(r, dict) else ""
        if isinstance(r, dict) and r.get("ok") and reason.startswith("cars:"):
            self._forced = far_cars_line(reason)
        elif reason in ("unknown_option", "here", ""):
            return False
        else:
            self._forced = "ما قدرت شوف شو في سيارات حواليّ هلأ، جرب كمان شوي."
        done.append("answered: the cars around her")
        self.log("chat: far cars -> %s" % reason[:300])
        return True

    def _far_wake(self, far, coming):
        if coming:
            self._forced = "إيه فايقة، أنا جاية."
            return
        if far.startswith("awake:"):
            self._forced = "إيه فايقة، قلي شو بدك."
            return
        r = run_action(self.dir, "sol_far", "wake", wait=2.5)
        self._forced = "إيه فايقة، قلي شو بدك." if isinstance(r, dict) and r.get("ok") else "مو سامعتك منيح، جرب كمان مرة."
        self.log("chat: far wake -> %s" % r)

    def _far_car_spot(self):
        """Her car is not near him: where it can go. An option string for the game, or the reason there is none."""
        for _ in range(4):                                                       # far_car: the list of cars near her may still be on its way
            r = run_action(self.dir, "sol_far", "car_where", wait=2.5)
            if not (isinstance(r, dict) and not r.get("ok") and r.get("reason") == "scanning"): break
            time.sleep(0.8)
        reason = str(r.get("reason")) if isinstance(r, dict) else ""
        m = re.match(r"^car:(-?\d+),(-?\d+),(-?\d+),(-?\d+),(\d+)(?:,(\w+))?(,in)?$", reason) if isinstance(r, dict) and r.get("ok") else None
        if not m: return None, reason or "no_car"
        cx, cy, px, py, ring = (int(v) for v in m.groups()[:5])
        kind = m.group(6) or "car"
        inside = m.group(7) is not None                                    # far_arrival: the game can bring it into the loaded area
        spot = RR.pickup_spot_dir(cx, cy, px, py, ring, kind, inner=inside)   # far_arrival: a straight stretch of road (an open place for a helicopter)
        self.log("chat: far car spot %r -> %r" % ((cx, cy, px, py, ring), spot))
        if spot is None: return None, "no_route"
        return ("car_far:%.1f,%.1f,%.0f,%.0f" % spot) + (",in" if inside else ""), None

    def _far_come(self, goal=None, by_car=False):
        r = run_action(self.dir, "sol_far", "come_car" if by_car else "come", wait=2.5)
        self.log("chat: far come -> %s" % r)
        reason = str(r.get("reason")) if isinstance(r, dict) else ""
        far_car = False
        if by_car and isinstance(r, dict) and not r.get("ok") and reason == "car_not_near":
            option, why = self._far_car_spot()
            if option is None:                                                  # no spot or no way to bring it: on foot, below
                r, reason = {"ok": False, "reason": why}, why
            else:
                r = run_action(self.dir, "sol_far", option, wait=2.5)
                self.log("chat: far car -> %s" % r)
                reason = str(r.get("reason")) if isinstance(r, dict) else ""
                far_car = True
        if by_car and (not isinstance(r, dict) or not r.get("ok") or not reason.startswith("waiting:")):      # no car she can bring: on foot, said plainly
            self.log("chat: far car not possible (%s), coming on foot" % reason)
            r = run_action(self.dir, "sol_far", "come", wait=2.5)
            reason = str(r.get("reason")) if isinstance(r, dict) else ""
            if isinstance(r, dict) and r.get("ok") and reason.startswith("waiting:"):
                self._forced = far_wait_line(reason, "جاية مشي، بدي %s.")
                self._far_waiting, self._far_told_edge = "foot", False
                return
            by_car = False
        if not isinstance(r, dict) or not r.get("ok") or not reason.startswith("waiting:"):
            self._forced = FAR_CAR_NO.get(reason, FAR_NO_CAR) if by_car else "ما بقدر أتحرك من مكاني هلأ."
            return
        self._forced = far_wait_line(reason, "جاية بالسيارة، بدي %s." if by_car else "جاية مشي، بدي %s.")
        self._far_waiting = "car_far" if far_car else "car" if by_car else "foot"
        self._far_told_edge = False
        self._far_drive_goal = goal if isinstance(goal, dict) and goal.get("intent") == "fetch_player" else None

    def _far_watch(self):
        """If after all that she could not arrive, the chat says so; nothing was promised past this."""
        if not getattr(self, "_far_waiting", False): return
        p = run_action(self.dir, "sol_far", "poll", wait=2.5)
        reason = str(p.get("reason")) if isinstance(p, dict) else ""
        mode = self._far_waiting
        if reason == "here":
            self._far_waiting = False
            if mode in ("car", "car_far"):                                       # she is by the car: from here it is the normal drive to him
                goal = getattr(self, "_far_drive_goal", None) or IE.make_goal("fetch_player", {"then": "stay_with_player"}, source="deterministic", text="")
                if mode == "car_far":                                            # far_arrival: she came with the car, at the wheel
                    goal.setdefault("slots", {})["quiet"] = "1"
                    with self.lock: self.hist.append({"role": "sol", "text": FAR_AT_EDGE, "t": time.time()})
                    self._save(); self.publish()
                self.log("chat: far car, she is here: %s" % self.goals.submit(goal))
        elif reason == "placed" and mode == "car_far" and False:                  # far_arrival: nothing to say until she is there
            if not getattr(self, "_far_told_edge", False):                       # the car is there; it appears when he gets close enough for that part to load
                self._far_told_edge = True
                with self.lock: self.hist.append({"role": "sol", "text": FAR_AT_EDGE, "t": time.time()})
                self._save(); self.publish()
        elif reason.startswith("on_foot:") and mode == "car_far":                 # far_arrival: she walks instead, said once in her words
            self._far_waiting = "foot"
            with self.lock: self.hist.append({"role": "sol", "text": FAR_ON_WAY, "t": time.time()})
            self._save(); self.publish()
        elif mode == "car_far" and reason in FAR_CAR_MOVE_FAILED and isinstance(p, dict) and p.get("ok"):
            r = run_action(self.dir, "sol_far", "come", wait=2.5)                 # the car could not come: she walks, nothing said about why
            self.log("chat: far car ended %s, on foot -> %s" % (reason, r))
            ok_foot = isinstance(r, dict) and r.get("ok") and str(r.get("reason")).startswith("waiting:")
            self._far_waiting = "foot" if ok_foot else False
            with self.lock: self.hist.append({"role": "sol", "text": FAR_ON_WAY if ok_foot else _FAR_CAR_FAILED, "t": time.time()})
            self._save(); self.publish()
        elif reason == "placed" and mode not in ("car", "car_far"): self._far_waiting = False
        elif reason == "idle": self._far_waiting = False                         # a reload ended it: nothing failed
        elif (reason in FAR_ENDED or reason.startswith("db_error:")) and isinstance(p, dict) and p.get("ok"):
            self._far_waiting = False
            with self.lock: self.hist.append({"role": "sol", "text": FAR_ENDED.get(reason, _FAR_CAR_FAILED), "t": time.time()})
            self._save(); self.publish()

    def _farm_orders(self, text, snap, mem, done):
        """Orders the Mind catches itself, before any model. Returns True when the message was one."""
        import farm_talk as FT
        hit = FT.order(text)
        if hit is None:
            if FT.is_due_question(text) and mem is not None:
                self._forced = FT.FarmMemory(mem).due_text(); done.append("farm due answered from memory")
                return True
            if FT.is_status_question(text) and self._farm_running(snap):
                r = run_action(self.dir, "sol_farm", "status", wait=2.5)
                st = {}
                if isinstance(r, dict) and r.get("ok"):
                    try: st = json.loads(str(r.get("reason")).split(":", 1)[1])
                    except (ValueError, IndexError): st = {}
                self._forced = FT.status_line(st); done.append("farm status answered")
                return True
            return False
        action, option = hit
        if str(option).startswith("plant:unknown:"):                            # a crop she does not know: nothing to ask of the game
            self._forced = FT.reply_for(option, {"ok": True, "reason": ""}); done.append("farm order: unknown crop")
            return True
        if action == "sol_farm":
            self._player_takes_over("sol_farm")
        r = run_action(self.dir, action, option, wait=3.0)
        self._turn_action_results.append(r)
        self._remember_action(action, option)
        done.append("farm order %s -> %s" % (option, json.dumps(r, ensure_ascii=False)))
        self.log("chat: farm order %s %s -> %s" % (action, option, r))
        if action == "sol_farm" and isinstance(r, dict) and r.get("ok") is None and r.get("rid"):  # the game is paused: the slot is kept for it and he hears the outcome when it runs
            self._farm_pending = {"rid": r["rid"], "option": option, "t": time.time()}
        if action == "sol_farm_try": self._forced = FT.trial_line(option, r)
        elif option == "proven": self._forced = FT.proven_line(r.get("reason") if isinstance(r, dict) else "")
        elif option == "forget": self._forced = "نسيت التجارب، وببلش من جديد."
        else: self._forced = FT.reply_for(option, r)
        return True

    def _can_watch(self):
        w = getattr(self, "_can_waiting", None)
        if not w: return
        if time.time() - w["t"] > 600:
            self._can_waiting = None
            return
        r = run_action(self.dir, "refuel_from_can", "status", wait=2.5)
        reason = str(r.get("reason")) if isinstance(r, dict) else ""
        if reason.startswith("done:"):
            self._can_waiting = None
            _, litres, pct = reason.split(":")
            self._say_later("عبيتها: %s لتر، وصار البنزين %s%%." % (litres, pct))
        elif reason.startswith("failed:"):
            self._can_waiting = None
            self._say_later(CAN_REFUEL_AR.get(reason[7:], "ما قدرت عبيها هلأ."))

    def _farm_pending_watch(self):
        w = getattr(self, "_farm_pending", None)
        if not w: return
        if time.time() - w["t"] > 900:
            self._farm_pending = None
            return
        r = action_result(self.dir, w["rid"])
        if r is None: return
        self._farm_pending = None
        import farm_talk as FT
        self.log("chat: farm order %s answered late -> %s" % (w["option"], r))
        self._say_later(FT.reply_for(w["option"], r))

    def _farm_running(self, snap):
        f = (snap or {}).get("solFarm") or {}
        mode = f.get("mode") or {}
        return bool(mode.get("farm") or mode.get("home") or f.get("status") in ("doing", "needs", "waiting"))

    def _stop_farm_if_running(self, snap):
        if self._farm_running(snap): run_action(self.dir, "sol_farm", "interrupt", wait=1.5)

    def _with_farm_report(self, snap):
        """The chat report is the game's own count, read now. Falls back to the snapshot's zones when the game is busy."""
        r = run_action(self.dir, "sol_farm", "report", wait=2.5)
        if isinstance(r, dict) and r.get("ok") and str(r.get("reason")).startswith("farm:"):
            try: return dict(snap or {}, solFarm=json.loads(r["reason"][5:]))
            except ValueError: pass
        return snap

    def _farm_watch(self, snap, mem):
        """What she planted stays with her between chats; warnings come from the game's numbers and are rate-limited here."""
        farm = (snap or {}).get("solFarm")
        if mem is None or not isinstance(farm, dict): return False
        import farm_talk as FT
        fm = FT.FarmMemory(mem)
        changed = fm.note(farm)
        lines = fm.warnings(farm)
        rows = [r for r in (farm.get("stops") or [farm.get("stop") or {}]) if isinstance(r, dict) and r.get("seq")]
        top = max([r["seq"] for r in rows] or [0])
        seen = fm.data.get("stopSeen") or 0
        if top and top != seen:
            if top < seen: seen = 0                                              # a new world counts from one again
            fm.data["stopSeen"] = top
            changed = True
            said = []
            for r in sorted(rows, key=lambda x: x["seq"]):
                if r["seq"] <= seen or (r.get("reason") == "waiting" and (r.get("detail") or {}).get("why") == "paused"): continue   # the ending of a job whose real reason is the row before
                line = FT.stop_line(r)
                if line and line not in said: said.append(line)
            lines[:0] = said
        if lines: changed = True
        if changed: mem.save()
        mind = getattr(self.goals, "mind", None)
        if mind is not None and lines:
            lock = getattr(self.goals, "mind_lock", None)
            for line in lines[:3]:
                if lock:
                    with lock: mind.say(line)
                else: mind.say(line)
        return bool(lines)

    def _street_now(self):
        if getattr(self, "_farm_pending", None): return None                     # one request slot: a background question must not replace his order
        r = run_action(self.dir, "sol_fuel", "street", wait=2.5)
        if isinstance(r, dict) and r.get("ok") and str(r.get("reason")).startswith("street:"): return r["reason"][7:] or None
        return None

    def _what_she_knows(self, snap, mem):
        """(the facts for a model, the names the gate may put right), read now."""
        live = self._street_now()
        if live: snap = dict(snap or {}, currentStreet=live)
        got = self._station_list()
        gaz = GZ.load()
        return MA.facts(snap, mem, got, gaz), MA.known_names(snap, mem, got, gaz)

    def _gardens(self):
        r = run_action(self.dir, "sol_fuel", "gardens", wait=2.5)
        if not (isinstance(r, dict) and r.get("ok") and str(r.get("reason")).startswith("gardens:")): return None
        return MA.parse_gardens(r["reason"])

    def _station_list(self):
        if getattr(self, "_farm_pending", None): return None
        r = run_action(self.dir, "sol_fuel", "list", wait=2.5)
        if not (isinstance(r, dict) and r.get("ok") and str(r.get("reason")).startswith("list:")): return None
        return MA.parse_stations(r["reason"])

    def _life_watch(self, snap=None, mem=None):
        """She came back from dying: the Mind forgets what she had learned, as the game has."""
        if snap is None: snap, mem = self._world()
        life = (snap or {}).get("solLife")
        if mem is None or not isinstance(life, dict): return False
        deaths = int(life.get("deaths") or 0)
        seen = int(mem.data.get("deaths") or 0)
        if deaths <= seen: return False
        mem.data["deaths"] = deaths
        mem.data["places"] = []
        mem.data["visited"] = []
        mem.data["farm"] = {}                    # what she planted and when it was due went with her
        self._last_at = None
        mem.save()
        self.hist = []
        self._save()
        self.log("life: death %d, her learned places forgotten" % deaths)
        mind = getattr(self.goals, "mind", None)
        if mind is not None:
            lock = getattr(self.goals, "mind_lock", None)
            line = random.choice(MA.LOST_MEMORY_LINES)
            if lock:
                with lock: mind.say(line)
            else: mind.say(line)
        return True

    def _note_where_she_is(self, snap, mem):
        """Her map is what she has passed. The path between two looks counts, but not a jump: that is a new place, not a drive."""
        her = MA._pos((snap or {}).get("sol"))
        if mem is None or her is None: return
        last = getattr(self, "_last_at", None)
        near = last is not None and math.hypot(her[0] - last[0], her[1] - last[1]) <= 400
        if (GZ.mark_visited(mem, *(last + her)) if near else GZ.mark_visited(mem, *her)): mem.save()
        self._last_at = her

    def _receipt(self):
        """The Mind ran something itself: say how it went without asking anyone."""
        results = list(getattr(self, "_turn_action_results", []))
        for r in results:
            note = action_receipt_note(r)
            if note: return note
        return random.choice(("تكرم.", "ماشي.", "حاضر."))

    def _note_actions(self, done_at=None):
        """What was just done, so a model cannot undo it a moment later."""
        recent = getattr(self, "_recent_actions", [])
        now = time.time() if done_at is None else done_at
        return [x for x in recent if now - x[0] < RG.CONTRADICT_SECONDS]

    def _remember_action(self, aid, option):
        self._recent_actions = self._note_actions() + [(time.time(), aid, option)]

    def _gate_context(self, history, acts, known_text, names=()):
        ids = {a["id"] for a in acts} | GATE_ACTIONS
        per = self.goals.perception() if hasattr(self.goals, "perception") else None
        sol = (per or {}).get("sol") or {}
        player = (per or {}).get("player") or {}
        in_car = sol.get("currentVehicle") is not None or player.get("currentVehicle") is not None
        ctx = RG.Context(history[-1]["text"] if history else "", ids, IE.SUPPORTED, known_text, in_car, self._note_actions(), names)
        ctx.strict = self._model_first()                                         # switch off: the gate is as it was
        return ctx

    def _through_the_gate(self, raw, history, acts, mem, snap, known_text, names=()):
        """The only way model text gets to him or to the game."""
        p = RG.parse(raw)
        ctx = self._gate_context(history, acts, known_text, names)
        allowed, why = RG.check_action(p, ctx)
        ran = False
        note = ""
        if not allowed:
            self.log("gate: refused the model's action %s %s: %s" % (p.get("goal") or p.get("action"), p.get("option"), why))
        elif p.get("goal") is not None:
            goal = IE.make_goal(p["goal"], p.get("slots") or {}, source="model", text=ctx.user_text)
            r = self.goals.submit(goal); self.log("gate: goal %s -> %s" % (p["goal"], r))
            ran = bool(r.get("ok")); note = action_receipt_note(r)
        elif p.get("action") is not None:
            self._player_takes_over(p["action"])
            r = resolve_and_run(self.dir, p["action"], p.get("option"), mem, snap); self.log("gate: action %s %s -> %s" % (p["action"], p.get("option"), r))
            self._remember_action(p["action"], p.get("option"))
            ran = isinstance(r, dict) and r.get("ok") is not False; note = action_receipt_note(r)
        if note: return note
        speech, rejected = RG.check_speech(p, ctx, ran)
        if rejected: self.log("gate: rejected (%s): %s" % (rejected, str(p.get("speech"))[:120]))
        elif getattr(ctx, "stripped", None): self.log("gate: stripped %s | kept: %s" % ("; ".join("(%s) %s" % x for x in ctx.stripped)[:160], speech[:120]))
        elif ctx.fixes: self.log("gate: corrected %s: %s" % ("; ".join("%s -> %s" % f for f in ctx.fixes), speech[:120]))
        else: self.log("gate: kept: %s" % speech[:120])
        if FARM_STOCK_RX.search(speech) and NONE_RX.search(speech):              # what is in stock is the scan's to say; the model cannot see it
            rows = W.farm_stock_rows(snap)
            if rows:
                self.log("gate: replaced a denial the scan contradicts: %s" % speech[:120])
                self.pending_card = rows
                speech = "هاد اللي عنا من البذور وأدوات الزراعة، بالجدول."
        return clean_speech(speech)

    def _without_model(self, history, code):
        """His rule: with no model connected the chat says nothing and does nothing. The right-click orders and her main panel still work."""
        self.log("chat: no model connected (%s): no reply" % code)
        return None

    def _model_first(self):
        """His switch in SolFixes_LAB.txt; missing means on, like every lab fix."""
        import sol_fixes                                                         # s152: also the main copy's file
        return sol_fixes.value(self.dir, "model_first") is not False

    def _memory_text(self, snap, mem):
        """What this Sol remembers, from the Mind's memory and the game. Rebuilt after a reconnect; her death empties it."""
        parts = [self._survey_answer(snap)]
        if mem is not None:
            places = [p.get("name") for p in (mem.data.get("places") or []) if isinstance(p, dict) and p.get("name")]
            if places: parts.append("أماكن بتعرفيها: " + "، ".join(places[-12:]) + ".")
            h = mem.data.get("home")
            if isinstance(h, dict) and h.get("x") is not None: parts.append("بيتنا محدد.")      # s77: no coordinates
        return " ".join(parts)

    def _session_sheet(self, snap, mem, acts):
        deaths = int(mem.data.get("deaths") or 0) if mem is not None else 0
        got = getattr(self, "_sheet", None)
        if got is None or got["deaths"] != deaths or time.time() - got["t"] > 300:
            got = {"text": MR.sheet(acts, self._memory_text(snap, mem)), "deaths": deaths, "t": time.time()}
            self._sheet = got
            self.log("chat: briefing sheet sent to the model, %d chars" % len(got["text"]))
        return got["text"]

    def _route_by_model(self, history, c, key, snap, mem):
        """The model picks the nearest action, the Mind checks and runs it and the game's result is what he hears. Returns the reply, or None for the word lists.
        self._model_failed is set when the model did not answer, so the slow talk path is not tried on top of it."""
        self._model_failed = False
        if not self._model_first() or not history: return None
        text = history[-1]["text"]
        if address_intent(text) is not None: return None                       # address_book: her own words run it, before any guess
        acts = load_actions(self.dir)
        t0 = time.time()
        def done_line(path, action, gate, result):
            self.log("chat: route text=%s path=%s ms=%d action=%s gate=%s result=%s" % (text[:60], path, int((time.time() - t0) * 1000), action, gate, str(result)[:90]))
        summon_words = text.lower()
        if (("سول" in summon_words or fix_on(self.dir, "phone_patience")) and "فيكي" in summon_words and "تجيبي" in summon_words
                and ("هليكوبتر" in summon_words or "مروحية" in summon_words)):
            action = "sol_summon_helicopter"
            r = run_action(self.dir, action, None, wait=3.0)
            self._remember_action(action, None)
            done_line("explicit-intent", action, "accepted", r)
            if isinstance(r, dict) and r.get("ok") is True:
                return "أكيد بقدر"
            if isinstance(r, dict) and r.get("ok") is None:
                return NEUTRAL_S109
            return action_receipt_note(r) or "ما قدرت أرسل طلب المروحية هلأ."
        raw = getattr(self, "_offline_raw_s157", None); self._offline_raw_s157 = None      # s157: the bank's answer, the model is down
        if raw is None and fix_on(self.dir, "bank_first") and hasattr(MR, "exact_answer_s160"):       # s160
            raw = MR.exact_answer_s160(text, acts)
            if raw: self.log("chat: his words are a known order, the model is not asked: %s" % raw[:80])
        try:
            if raw is None: raw = P.chat(c["provider"], key, c["model"], MR.message(text, c["model"]), system=self._session_sheet(snap, mem, acts), custom_base=c.get("base", ""), max_tokens=(80 if c.get("provider") == "custom" else 200), timeout=((PHONE_WAIT_S157 if fix_on(self.dir, "phone_patience") else 4) if c.get("provider") == "custom" else 15))   # LAN phone model fast; cloud (Groq...) slower
        except Exception as e:
            self._model_failed = True
            done_line("fallback", None, "-", "model failed: %r" % (e,))
            return None
        p = MR.parse(raw)
        if p is None:
            done_line("fallback", None, "-", "reply not readable")
            return None
        action = p["action"]
        ids = {a.get("id") for a in acts if a.get("enabled", True)}
        if action in ("refuel_from_can", "refuel_at_station") and not any(w in text for w in FUEL_WORDS):
            done_line("model", action, "no_fuel_word", "asked him")
            return "شو قصدك؟ عيدها بكلمة تانية."
        if action == "unknown" or (action != "none" and action not in MR.COMMANDS and action not in ids):
            done_line("model", action, "not_an_action", "asked him")
            return "شو قصدك؟ عيدها بكلمة تانية."
        if action == "refuel_at_station":
            full = car_is_full(snap)
            if full is not None:
                done_line("model", action, "tank_full", full)
                return TANK_FULL_SAY % full
        if action == "refuel_from_can":
            r = run_action(self.dir, "refuel_from_can", None, wait=3.0)
            done_line("model", action, "accepted", r)
            if isinstance(r, dict) and r.get("ok") and str(r.get("reason")) in ("started", "busy"):
                self._can_waiting = {"t": time.time()}
                return "حاضر، بجيب بدون وبعبيها."
            return CAN_REFUEL_AR.get(str((r or {}).get("reason")), "ما قدرت عبيها هلأ.")
        if action == "why":
            r = self._why_answer(snap); done_line("model", action, "-", r); return r
        if action == "survey":
            r = self._survey_answer(snap); done_line("model", action, "-", r); return r
        if action == "cars_near":                                                   # s77: the cars around her, far or here
            r = self._cars_near_answer(snap); done_line("model", action, "-", r); return r
        if action == "sol_let_player_drive":
            self._player_takes_over(action)
            r = run_action(self.dir, action, None, wait=3.0)
            self._remember_action(action, None)
            done_line("model", action, "accepted", r)
            if isinstance(r, dict) and r.get("ok") is True:
                return "تكرم، خليتلك مقعد القيادة وصرت جنبك."
            if isinstance(r, dict) and r.get("ok") is None:
                return NEUTRAL_S109
            return action_receipt_note(r) or "ما قدرت أبدل مقعدي هلأ."
        if action == "sol_pilot_helicopter":
            self._player_takes_over(action)
            r = run_action(self.dir, action, None, wait=3.0)
            self._remember_action(action, None)
            done_line("model", action, "accepted", r)
            if isinstance(r, dict) and r.get("ok") is True:
                return "صرت بمقعد الطيار. حدّد الوجهة من GPS، وبعدين ابدأ الطيران."
            if isinstance(r, dict) and r.get("ok") is None:
                return NEUTRAL_S109
            return action_receipt_note(r) or "ما قدرت آخد مقعد الطيار هلأ."
        if action == "sol_summon_helicopter":
            r = run_action(self.dir, action, None, wait=3.0)
            self._remember_action(action, None)
            done_line("model", action, "accepted", r)
            if isinstance(r, dict) and r.get("ok") is True:
                return "أكيد بقدر"
            if isinstance(r, dict) and r.get("ok") is None:
                return NEUTRAL_S109
            return action_receipt_note(r) or "ما قدرت أرسل طلب المروحية هلأ."
        if action in MR.COMMANDS:
            routed = list(history[:-1]) + [dict(history[-1], text=MR.COMMANDS[action][1], said=text)]      # what he really wrote rides along
            done = self._pre_intents(routed, snap, mem)
            forced = getattr(self, "_forced", None); self._forced = None
            reply = forced or (self._receipt() if done else None)
            done_line("model", action, "accepted", reply)
            return reply
        if action != "none":
            self._player_takes_over(action)
            r = resolve_and_run(self.dir, action, (p.get("args") or {}).get("option"), mem, snap)
            self._remember_action(action, (p.get("args") or {}).get("option"))
            done_line("model", action, "accepted", r)
            return action_receipt_note(r) or random.choice(("تكرم.", "ماشي."))
        # s77: a question about the cars around her is the model's cars_near; no word match overrides its "none"
        #      (s71's far_cars", "none" word match was here; this note keeps apply_s71_mind.py from putting it back)
        said = MA.answer(text, snap, mem, lambda: self._station_list(), lambda: self._street_now(), GZ.load(), lambda: self._gardens())   # streets, towns, stations: from the map, never guessed
        if said:
            done_line("memory", "none", "-", said)
            return said
        facts = W.situation_text(snap, mem) + " " + self._memory_text(snap, mem)
        ctx = self._gate_context(history, acts, facts, MA.known_names(snap, mem, [], GZ.load()))
        speech, rejected = RG.check_speech({"speech": p["speech"]}, ctx, False)
        done_line("model", "none", rejected or ("stripped" if getattr(ctx, "stripped", None) else "kept"), speech)
        return clean_speech(speech)

    def _why_answer(self, snap):
        """Why the last thing failed, from what the game reported, never from the model."""
        import farm_talk as FT
        g = self.gps_state() or {}
        if str(g.get("result")) in ("failed", "interrupted") and g.get("reason") not in (None, "", "walking_to_door", "moving_to_wheel"):
            return drive_reply({"ok": False, "reason": g.get("reason")})
        line = FT.stop_line(((snap or {}).get("solFarm") or {}).get("stop"))
        return line or "ما صار شي غلط هلأ."

    def _survey_answer(self, snap):
        """What the game knows about the place, in one answer."""
        s = snap or {}
        parts = []
        h = s.get("solHome")
        parts.append("البيت محدد." if isinstance(h, dict) and h.get("x") is not None else "لسا ما حددنا البيت.")      # s77: no coordinates
        p = s.get("solParking")
        parts.append("في مكان محدد لصف السيارات." if isinstance(p, dict) and p.get("x") is not None else "ما في مكان محدد لصف السيارات.")
        zones = ((s.get("solFarm") or {}).get("zones")) or []
        if zones:
            nz, alive, empty = len(zones), sum(z.get("alive") or 0 for z in zones), sum(z.get("empty") or 0 for z in zones)     # s77: no tile counts
            parts.append("عنا %s للزراعة، فيها %s%s." % ("منطقة وحدة" if nz == 1 else "منطقتين" if nz == 2 else "%d مناطق" % nz,
                                                    "نبتة وحدة عايشة" if alive == 1 else "نبتتين عايشين" if alive == 2 else "%d نبتات عايشة" % alive if 3 <= alive <= 10 else "%d نبتة عايشة" % alive if alive else "ولا نبتة عايشة", "، وفي محل فاضي للزرع" if empty else ""))
        else:
            parts.append("ما في منطقة زراعة محددة.")
        nv = len(s.get("vehicles") or [])
        parts.append("ما شايفة سيارات قريبة." if nv == 0 else "شايفة سيارة وحدة قريبة." if nv == 1 else "شايفة سيارتين قراب." if nv == 2 else "شايفة %d سيارات قريبة." % nv)
        return " ".join(parts)

    def _cars_near_answer(self, snap):
        """s77 cars_near. Far: the far_car scan of her surroundings. Here: the cars the live snapshot shows around her. The numbers go to the log."""
        far_done = []
        if self._far_cars(snap, far_done):
            r = getattr(self, "_forced", None); self._forced = None
            return r or "ما قدرت شوف شو في سيارات حواليّ هلأ، جرب كمان شوي."
        sol = (snap or {}).get("sol")
        if not snap or not isinstance(sol, dict) or sol.get("away"):               # no body here and no far list: nothing true to say
            self.log("chat: cars near her -> no snapshot of her surroundings")
            return "ما قدرت شوف شو في سيارات حواليّ هلأ، جرب كمان شوي."
        self.log("chat: cars near her -> %s" % near_cars_detail(snap)[:600])
        return near_cars_line(snap)

    def _ask_provider(self, history):
        c = SS.load_config()
        if c.get("source") == "bridge": return self._ask_link(history)
        if c.get("source") not in ("api", "local") or not c.get("model"):
            # No model: the orders she already understands ("وقفي", "انقذيني", "سوقي للبيت"...)
            # still run. The deterministic layer must never depend on a provider being connected.
            return self._without_model(history, "no_mind")
        key = S.get(c["provider"]) or "" if c["source"] == "api" else ""
        msgs = [{"role": "assistant" if m["role"] == "sol" else "user", "content": m["text"]} for m in history[-CONTEXT:] if m["role"] in ("sol", "user")]
        snap, mem = self._world()
        routed = self._route_by_model(history, c, key, snap, mem)
        if routed is not None: return routed
        done = self._pre_intents(history, snap, mem)
        forced = getattr(self, "_forced", None); self._forced = None
        if forced: return forced
        if done: return self._receipt()                                         # the Mind understood it and did it: nothing for a model to add
        if getattr(self, "_model_failed", False):                                # the model is down: no minute-long wait on a second call to it
            raw = MR.offline_answer_s157(history[-1]["text"], load_actions(self.dir)) if fix_on(self.dir, "phone_patience") and hasattr(MR, "offline_answer_s157") else None
            if raw:                                                               # s157: his words are one of the known orders
                self.log("chat: model down, his words match a known order: %s" % raw[:80])
                self._offline_raw_s157 = raw
                routed = self._route_by_model(history, c, key, snap, mem)
                if routed is not None: return routed
            self.log("chat: model down, word lists found no order")
            return "ما قدرت افهم هلأ، قولها بكلمة تانية."
        acts = load_actions(self.dir)
        tool_notes = []
        def tool(name, args):
            if mem is None and name != "can_make": return {"error": "no world data from the game yet"}
            r = W.run_tool(name, args, snap, mem, W.load_recipes(self.dir)); self.log("chat: tool %s -> %s" % (name, str(r)[:120]))
            if name == "set_home" and isinstance(r, dict) and r.get("home"): run_action(self.dir, "sol_set_home", None, wait=2.0)
            tool_notes.append(json.dumps(r, ensure_ascii=False))
            return r
        sysp = self.system_prompt(snap, mem) + IN_CHARACTER + "\n\n" + IE.capabilities_text() + "\n\nActive multi-step goal: " + self.goals.describe()
        if acts: sysp += "\n\nActions (ids for the action field):\n" + actions_text(acts)
        known, names = self._what_she_knows(snap, mem)
        if known: sysp += "\n\nهذا ما تعرفينه فعلًا، فلا تنكريه:\n" + known
        sysp += RG.INSTRUCTION
        try:
            reply = P.chat_with_tools(c["provider"], key, c["model"], msgs, W.TOOLS, tool, system=sysp,
                                      custom_base=c.get("base", ""), max_tokens=600, timeout=60, rounds=3)
        except P.ProviderError as e:
            if e.code != "rate_limited": raise
            self.log("chat: rate limited, one retry in 6 s"); time.sleep(6)      # free tiers count tokens per minute
            reply = P.chat_with_tools(c["provider"], key, c["model"], msgs[-4:], W.TOOLS, tool, system=sysp,
                                      custom_base=c.get("base", ""), max_tokens=400, timeout=60, rounds=2)
        if not reply: raise P.ProviderError("empty_reply")
        facts = W.situation_text(snap, mem) + " " + json.dumps(self.gps_state() or {}, ensure_ascii=False) + " " + (known or "") + " " + " ".join(tool_notes)   # what she has been told about the world, not her character sheet
        return self._through_the_gate(reply, history, acts, mem, snap, facts, names)

    # ---------------------------------------------------------------- ChatGPT in the browser (Sol Link)
    def _player_takes_over(self, action):
        """A direct order about where she goes ends any multi-step goal: otherwise the plan keeps pulling against him."""
        if action in MOVE_ORDERS and self.goals.cancel(reason="player_order:" + action):
            self.log("chat: order %s replaced the running goal" % action)

    def _ask_link(self, history):
        link = SS.start_link(self.log)
        if link is None: return self._without_model(history, "chatgpt_link_not_connected")
        snap, mem = self._world()
        done = self._pre_intents(history, snap, mem)
        forced = getattr(self, "_forced", None); self._forced = None
        if forced: return forced
        if done: return self._receipt()
        acts = load_actions(self.dir)
        primer = ""
        if getattr(self, "_link_primed", None) != id(link) or self._link_count >= 25:
            primer = LINK_PRIMER + IN_CHARACTER + "\n\n"
            self._link_primed, self._link_count = id(link), 0
        self._link_count += 1
        parts = [primer + "[حال العالم الآن]\n" + (W.situation_text(snap, mem) if snap else "لسا مو شايفة شي حولي.")]
        g = self.gps_state()
        if g and g.get("result"): parts.append("[السيارة] %s %s، المسافة %s خانة" % (g.get("result"), g.get("phase") or "", g.get("distance") or "?"))
        if acts: parts.append("[أفعال تستطيعين تنفيذها الآن: اكتبي [فعل: المعرّف] أو [فعل: المعرّف | الخيار]]\n" + actions_text(acts))
        if done: parts.append("[هذه نتائج معالجة الطلب قبل ردك؛ قد تعني قبول الأمر أو بدءه فقط، فلا تقولي إنه اكتمل إلا إذا ظهر تأكيد صريح]\n" + "; ".join(done))
        if self.pending_card: parts.append("[جدول المؤن معروض للاعب تحت ردك، فلا تعيدي سرده]")
        known, names = self._what_she_knows(snap, mem)
        if known: parts.append("[هذا ما تعرفينه فعلًا، والأسماء تُكتب حرفيًا كما هي]\n" + known)
        parts.append(IE.capabilities_text(tags=True))
        parts.append("[الهدف متعدد الخطوات] " + self.goals.describe())
        parts.append("[اللاعب يقول]\n" + history[-1]["text"])
        try:
            raw = link.ask("\n\n".join(parts), speak=True)
        except TimeoutError as e:
            raise P.ProviderError(str(e))
        if not str(raw or "").strip(): raise P.ProviderError("empty_reply")
        return self._through_the_gate(raw, history, acts, mem, snap, "\n\n".join(parts), names)

    def handle(self, text):
        text = (text or "").strip()[:1000]
        if not text: return
        last = next((m for m in reversed(self.hist) if m["role"] == "user"), None)
        if last and last["text"] == text and time.time() - last.get("t", 0) < 90 and self.status in ("thinking", "ok"):
            if self.status == "thinking" or (self.hist and self.hist[-1]["role"] != "user"):
                self.log("chat: duplicate message ignored"); return
        with self.lock:
            self.hist.append({"role": "user", "text": text, "t": time.time()})
            self.status, self.code = "thinking", ""
        self.publish()
        try:
            self.pending_card = None
            raw = self.ask(self.hist)
            if raw is None:
                with self.lock: self.status, self.code = "ok", ""
                return
            reply = clean_reply(western_digits(raw))
            with self.lock:
                self.hist.append({"role": "sol", "text": reply, "t": time.time()})
                if getattr(self, "pending_card", None):
                    self.hist.append({"role": "card", "text": "^".join("%s;%s;%s;%s" % r for r in self.pending_card), "t": time.time()})
                    self.pending_card = None
                self.status, self.code = "ok", ""
            self.log("chat: reply %d chars" % len(reply))
        except P.ProviderError as e:
            with self.lock: self.status, self.code = "error", e.code
            self.log("chat: failed %s %s" % (e.code, e.detail))
        except Exception as e:
            with self.lock: self.status, self.code = "error", "unknown_error"
            self.log("chat: error %r" % (e,))
        self._save()

    def _say_alive(self):
        """The game's dot goes grey when this stops."""
        try:
            with open(os.path.join(self.dir, ALIVE_FILE), "w", encoding="ascii", newline="\n") as f: f.write("t=%d\n" % int(time.time() * 1000))
        except OSError as e: self.log("alive file: %r" % (e,))

    def poll_once(self):
        now = time.time()
        if now - getattr(self, "_life_at", 0) >= 5:
            self._life_at = now
            if FAR_WAKE:
                try: self._far_watch()
                except Exception as e: self.log("far watch failed: %r" % (e,))
            for watch in (self._park_watch, self._farm_pending_watch, self._can_watch):
                try: watch()
                except Exception as e: self.log("%s failed: %r" % (watch.__name__, e))
            try:
                snap, mem = self._world()
                self._life_watch(snap, mem)
                self._note_where_she_is(snap, mem)
                self._farm_watch(snap, mem)
            except Exception as e: self.log("life watch failed: %r" % (e,))
        path = os.path.join(self.dir, REQ)
        try:
            with open(path, encoding="ascii", errors="replace") as f: raw = f.read()
        except OSError: return False
        req = dict(l.split("=", 1) for l in raw.splitlines() if "=" in l)
        try: rid = int(req.get("id", "0"))
        except ValueError: return False
        if rid <= self.ack: return False
        if req.get("action") == "clear":
            with self.lock: self.hist = []; self.status, self.code = "idle", ""
            self._save(); self.ack = rid; self.publish(); return True
        self.ack = rid
        self.handle(unesc(req.get("text", "")))
        self.publish()
        return True

    def start(self, interval=0.25):
        try: W.cleanup_deleted_worlds(log=self.log)
        except Exception as e: self.log("chat: world cleanup skipped %r" % (e,))
        try:
            with open(os.path.join(self.dir, REQ), encoding="ascii", errors="replace") as f:
                for l in f.read().splitlines():
                    if l.startswith("id="): self.ack = int(l[3:] or 0)
        except (OSError, ValueError): pass
        self.publish()
        self._stop = threading.Event()
        if FAR_WAKE:
            def alive():                                                         # its own thread: a slow reply must not turn her dot grey
                while not self._stop.is_set():
                    self._say_alive()
                    self._stop.wait(5)
            threading.Thread(target=alive, name="sol-alive", daemon=True).start()
        def loop():
            while not self._stop.is_set():
                try: self.poll_once()
                except Exception as e: self.log("chat: loop error %r" % (e,))
                self._stop.wait(interval)
        t = threading.Thread(target=loop, name="sol-chat", daemon=True); t.start(); return t


# ---------------------------------------------------------------- s78 cars_away
# The cars around HIM are never her answer. away -> sol_far "cars" (the game's saved rows, read only); here -> solVehicles.
HER_CARS_SAME_SPOT = 10
CARS_NOT_SEEN = "ما قدرت شوف شو في سيارات حواليّ هلأ، جرب كمان شوي."
_far_cars_line_s77 = far_cars_line


def far_cars_line(reason):
    """s77's line; head "cars:<n>/own" (the far_car switch is off): no offer to bring one of those cars."""
    line = _far_cars_line_s77(reason)
    if "/own" in str(reason).partition("|")[0]: line = line.replace(" إذا بدك بجيك بوحدة منهن، قلي تعالي بالسيارة.", "")
    return line


def her_cars_snap(snap):
    """The snapshot with the cars around HER as its vehicles, or None when there is no true list of them.
    solVehicles (apply_s78_cars_away_lua.py) is around her body wherever he is; without it, the cars around him count only
    when she stands beside him."""
    s = snap or {}
    sol = s.get("sol") if isinstance(s.get("sol"), dict) else {}
    if sol.get("away") or sol.get("x") is None or sol.get("y") is None: return None
    if isinstance(s.get("solVehicles"), list): return dict(s, vehicles=s["solVehicles"])
    me = s.get("player") or {}
    if me.get("x") is None or me.get("y") is None: return None
    if math.hypot(sol["x"] - me["x"], sol["y"] - me["y"]) > HER_CARS_SAME_SPOT: return None
    return s


def _cars_near_answer_s78(self, snap):
    """cars_near, three states. away: the far list (sol_far cars). here: the loaded cars around her. Numbers go to the log only."""
    far_done = []
    if self._far_cars(snap, far_done):
        r = getattr(self, "_forced", None); self._forced = None
        return r or CARS_NOT_SEEN
    sol = (snap or {}).get("sol")
    if not snap or not isinstance(sol, dict):
        self.log("chat: cars near her -> no snapshot of her surroundings")
        return CARS_NOT_SEEN
    if sol.get("away"):
        self.log("chat: cars near her -> away, the game gave no list of the cars around her")
        return CARS_NOT_SEEN
    hers = her_cars_snap(snap)
    if hers is None:
        self.log("chat: cars near her -> she is away from him and the snapshot has no cars around her (solVehicles)")
        return CARS_NOT_SEEN
    self.log("chat: cars near her -> %s%s" % ("" if "solVehicles" in snap else "(beside him) ", near_cars_detail(hers)[:600]))
    return near_cars_line(hers)


Chat._cars_near_answer = _cars_near_answer_s78
_far_order_s77 = Chat._far_order


def _far_order_s78(self, text, snap, done, said=None):
    """come_car chosen by the model: his words ride along as `said`; the car is what he asked for even when they hold no car word."""
    if text == MR.COMMANDS["come_car"][1] and not _CAR_RX.search(said or ""): said = text + " " + (said or "")
    return _far_order_s77(self, text, snap, done, said)


Chat._far_order = _far_order_s78


# ---------------------------------------------------------------- s79 horn_hold
# horn_hold: whether her hand is on the horn goes into the card; her own short lines for it.
HORN_MIND_SECONDS = 300                                                       # the Mind's own start counts this long at most
HORN_LINES = {
    "not_in_a_car": "أنا مو بسيارة هلأ.",
    "no_sol": "ما فيني هلأ.",
    "horn_needs_driver_seat": "لازم كون ورا المقود لزمّر.",
    "horn_engine_off": "السيارة طافية هلأ.",
    "horn_unavailable": "ما بقدر زمّر بهالسيارة.",
    "battery_dead": "البطارية فاضية.",
    "no_battery": "ما في بطارية بالسيارة.",
    "unknown_option": "شو قصدك؟ عيدها بكلمة تانية.",
}
HORN_STOP_OPTIONS = ("stop", "off", "release")
_HORN_RUN = []


def horn_catalog_time(lua_dir):
    """When the game last wrote its action list (ms), 0 when unknown."""
    try:
        with open(os.path.join(lua_dir, ACT_SNAP), encoding="ascii", errors="replace") as f: d = json.loads(f.read())
        return float(d.get("t") or 0)
    except (OSError, ValueError, TypeError, AttributeError): return 0.0


def horn_line(option, result):
    """Her line for a horn_hold result, or None to keep the usual reply (the game did not confirm yet)."""
    r = result if isinstance(result, dict) else {}
    if r.get("ok") is None and not r.get("error"): return None
    why = str(r.get("reason") or r.get("error") or "")
    if r.get("error") or r.get("ok") is False:
        return HORN_LINES.get(why) or reason_ar(why) or "ما قدرت هلأ."
    if str(option or "start").lower() in HORN_STOP_OPTIONS:
        if why == "horn_not_held": return "ما كنت عم زمّر."
        return random.choice(("خلص، شلت إيدي.", "ماشي، خلص."))
    return "تكرم."


_resolve_and_run_s78 = resolve_and_run


def resolve_and_run(lua_dir, aid, opt, mem, snap, log=print):
    r = _resolve_and_run_s78(lua_dir, aid, opt, mem, snap, log)
    if aid == "horn_hold": _HORN_RUN.append((str(opt or "start").strip().lower(), r))
    return r


def _horn_held(self, acts):
    """True while her hand is on the horn: the game's list says so, unless the Mind's own start/stop is newer than that list."""
    entry = next((a for a in acts or [] if isinstance(a, dict) and a.get("id") == "horn_hold"), None)
    if entry is None: return False
    mine = getattr(self, "_horn_mine", None)
    if mine is not None and mine[0] * 1000.0 > horn_catalog_time(self.dir):
        return mine[1] == "start" and time.time() - mine[0] < HORN_MIND_SECONDS
    return entry.get("state") == "holding"


_session_sheet_s78 = Chat._session_sheet


def _session_sheet_s79(self, snap, mem, acts):
    """The briefing sheet, rebuilt when whether she holds the horn changes."""
    held = self._horn_held(acts)
    got = getattr(self, "_sheet", None)
    if isinstance(got, dict) and got.get("horn") != held: self._sheet = None
    MR.HORN_HELD = held
    text = _session_sheet_s78(self, snap, mem, acts)
    if isinstance(getattr(self, "_sheet", None), dict): self._sheet["horn"] = held
    return text


_route_by_model_s78 = Chat._route_by_model


def _route_by_model_s79(self, history, c, key, snap, mem):
    """As before; a horn_hold the model chose gets her own line, and the Mind remembers whether her hand is on the horn."""
    del _HORN_RUN[:]
    reply = _route_by_model_s78(self, history, c, key, snap, mem)
    if not _HORN_RUN: return reply
    option, r = _HORN_RUN[-1]
    del _HORN_RUN[:]
    if isinstance(r, dict) and r.get("ok") is True:
        self._horn_mine = (time.time(), "stop" if option in HORN_STOP_OPTIONS else "start")
    line = horn_line(option, r)
    self.log("chat: horn_hold %s -> %s" % (option, str(r)[:90]))
    return reply if line is None else line


Chat._horn_held = _horn_held
Chat._session_sheet = _session_sheet_s79
Chat._route_by_model = _route_by_model_s79


# ---------------------------------------------------------------- s82 engine words, place questions, compact card
# The model said unknown (or named nothing on the list): before asking him again, the map answer is tried, the same call the
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


# ---------------------------------------------------------------- s85 card budget, two orders in one line, exit first, far report
# 1. Two or three orders in one line (the model's "actions"): run in order, each one finished before the next (her out of the car
#    before she walks); a refusal ends the chain and is what he hears.
# 2. An on-foot order while she sits in a car: the game gets her out first (SolExitFirst.lua, switch exit_first) and runs the
#    order after; she says so in one line now and the order's own line when it ran (or why it could not).
# 3. far_report (what she did while he was away): one line in the chat when a new report appears, and it stays in her memory.
import farm_talk as _FT85
STEP_WAIT_S85 = {"exit_car": 15.0}                                            # seconds the next step waits for this one at most
STEP_POLL_S85 = 0.5
_STEP_RESULTS = []
_EXIT_RUN = []
EXIT_FIRST_REASONS = ("leaving_car_first", "stopping_car_first", "waiting_car_stop")
EXIT_LINES = {
    "leaving_car_first": "ماشي، بنزل من السيارة أول.",
    "stopping_car_first": "ماشي، بوقف السيارة وبنزل أول.",
    "waiting_car_stop": "ماشي، بس توقف السيارة بنزل.",
}
EXIT_FAILED_LINE = "ما قدرت انزل من السيارة."
EXIT_WATCH_SECONDS = 180
FAR_BACK_PREFIX = "وإنت برّا، "
FAR_MEMORY_SECONDS = 6 * 3600
_run_action_s85_base = run_action


def run_action(lua_dir, action, option=None, wait=3.0):
    r = _run_action_s85_base(lua_dir, action, option, wait)
    _STEP_RESULTS.append(r)
    if isinstance(r, dict) and r.get("ok") and str(r.get("reason") or "") in EXIT_FIRST_REASONS:
        _EXIT_RUN.append((action, option, str(r.get("reason"))))
    return r


def _she_is_out(snap):
    sol = (snap or {}).get("sol")
    return isinstance(sol, dict) and sol.get("currentVehicle") is None


def _wait_step(self, step):
    """The next order waits until this one is done in the game (exit_car: she is out), at most STEP_WAIT_S85 seconds."""
    limit = STEP_WAIT_S85.get(step["action"])
    if not limit: return True
    end = time.time() + limit
    while True:
        try: snap = self._world()[0]
        except Exception: snap = None
        if _she_is_out(snap): return True
        if time.time() >= end: return False
        time.sleep(STEP_POLL_S85)


def _run_steps(self, history, c, key, snap, mem, steps, reply, route):
    """steps[0] has run (reply is its line); the rest run one by one through the same model route, as if the model chose each."""
    real = P.chat
    for i, step in enumerate(steps[1:], 1):
        if any(isinstance(r, dict) and (r.get("ok") is False or r.get("error")) for r in _STEP_RESULTS):
            self.log("chat: steps stop after %s (refused)" % steps[i - 1]["action"]); break
        if not _wait_step(self, steps[i - 1]):
            self.log("chat: step %s not seen done in time, %s goes on" % (steps[i - 1]["action"], step["action"]))
        del _STEP_RESULTS[:]
        answer = json.dumps(dict({"action": step["action"], "speech": ""}, **({"args": step["args"]} if step.get("args") else {})), ensure_ascii=False)
        P.chat = lambda *a, **k: answer
        try:
            try: now = self._world()[0] or snap
            except Exception: now = snap
            got = route(self, history, c, key, now, mem)
        finally:
            P.chat = real
        self.log("chat: step %d/%d %s -> %s" % (i + 1, len(steps), step["action"], str(got)[:60]))
        if got is None or got == ASK_AGAIN_S82: break
        reply = got
    return reply


_route_by_model_s84 = Chat._route_by_model


def _route_by_model_s85(self, history, c, key, snap, mem):
    """As before; several actions from the model run in order; an on-foot order she must leave the car for says so."""
    del MR.LAST_STEPS[:], _STEP_RESULTS[:], _EXIT_RUN[:]
    reply = _route_by_model_s84(self, history, c, key, snap, mem)
    steps = list(MR.LAST_STEPS)
    del MR.LAST_STEPS[:]
    if len(steps) > 1 and reply is not None and reply != ASK_AGAIN_S82:
        self.log("chat: %d steps: %s" % (len(steps), " then ".join(s["action"] for s in steps)))
        reply = _run_steps(self, history, c, key, snap, mem, steps, reply, _route_by_model_s84)
    if _EXIT_RUN:
        action, option, why = _EXIT_RUN[-1]
        self._exit_waiting = {"action": action, "option": option, "t": time.time(), "at": 0.0}
        self.log("chat: %s %s -> she gets out of the car first (%s)" % (action, option, why))
        reply = EXIT_LINES.get(why, EXIT_LINES["leaving_car_first"])
    del _EXIT_RUN[:]
    return reply


def exit_done_line(action, option, ok, why):
    """Her line once the game ran the order she left the car for; None when the order has nothing to add."""
    if why == "exit_failed": return EXIT_FAILED_LINE
    r = {"ok": ok, "reason": why}
    own = {"sol_farm": _FT85.reply_for, "sol_role": role_reply}.get(action)      # the orders with their own lines
    if own is not None: return own(option, r)
    if not ok: return reason_ar(why) or "ما قدرت عليها هلأ."
    return None


def _exit_watch(self):
    w = getattr(self, "_exit_waiting", None)
    if not w: return
    now = time.time()
    if now - w["t"] > EXIT_WATCH_SECONDS:
        self._exit_waiting = None; return
    if now - w["at"] < 2.0: return
    w["at"] = now
    r = _run_action_s85_base(self.dir, "sol_exit_first", "status", wait=2.0)
    why = str(r.get("reason") or "") if isinstance(r, dict) else ""
    if why == "pending" or not why.startswith(("done:", "idle")): return
    self._exit_waiting = None
    if why == "idle": return
    _, ok, rest = why.split(":", 2) if why.count(":") >= 2 else (why, "false", "")
    line = exit_done_line(w["action"], w["option"], ok == "true", rest)
    self.log("chat: exit_first %s %s done -> %s %s" % (w["action"], w["option"], ok, rest[:60]))
    if line: self._say_later(line)


_poll_once_s84 = Chat.poll_once


def _poll_once_s85(self):
    try: _exit_watch(self)
    except Exception as e: self.log("exit watch failed: %r" % (e,))
    return _poll_once_s84(self)


# far_report: the stop list's far_report row is said here, in the chat, once (its seq and its time); _farm_watch keeps the rest
_stop_line_s84 = _FT85.stop_line
_FAR_QUIET = []


def _stop_line_s85(stop):
    if _FAR_QUIET and isinstance(stop, dict) and stop.get("reason") == "far_report": return None
    return _stop_line_s84(stop)


_FT85.stop_line = _stop_line_s85
_farm_watch_s84 = Chat._farm_watch


def _farm_watch_s85(self, snap, mem):
    farm = (snap or {}).get("solFarm")
    news, fm = [], None
    if mem is not None and isinstance(farm, dict):
        fm = _FT85.FarmMemory(mem)
        rows = [r for r in (farm.get("stops") or [farm.get("stop") or {}]) if isinstance(r, dict) and r.get("seq")]
        seen = fm.data.get("stopSeen") or 0
        if rows and max(r["seq"] for r in rows) < seen: seen = 0                   # a new world counts from one again
        news = [r for r in rows if r.get("reason") == "far_report" and r["seq"] > seen and r.get("at") != fm.data.get("farReportAt")]
    _FAR_QUIET.append(1)
    try: out = _farm_watch_s84(self, snap, mem)
    finally: _FAR_QUIET.pop()
    if news:
        r = max(news, key=lambda x: x["seq"])
        line = _FT85.far_report_line(r.get("detail"))
        fm.data["farReportAt"] = r.get("at")
        fm.data["farReport"] = {"t": time.time(), "line": line} if line else None
        mem.save()
        self._sheet = None                                                     # her memory on the card changed
        self.log("chat: far_report seq=%s -> %s" % (r.get("seq"), line))
        if line: self._say_later(FAR_BACK_PREFIX + line)
    return out


_memory_text_s84 = Chat._memory_text


def _memory_text_s85(self, snap, mem):
    """As before, plus what she did while he was away (far_report), for a few hours after he is back."""
    text = _memory_text_s84(self, snap, mem)
    fr = ((mem.data.get("farm") or {}).get("farReport") if mem is not None else None) or {}
    if fr.get("line") and time.time() - float(fr.get("t") or 0) < FAR_MEMORY_SECONDS:
        text += " بغيابك: " + fr["line"]
    return text


Chat._route_by_model = _route_by_model_s85
Chat.poll_once = _poll_once_s85
Chat._farm_watch = _farm_watch_s85
Chat._memory_text = _memory_text_s85


# ---------------------------------------------------------------- s86 book_memory: her address book in her memory
# Her address book (game side: SolAddressBook.lua, action sol_address) reaches her memory on the card through the snapshot's
# "solBook" (switch book_memory): at most BOOK_CARD_MAX entries, بيتنا first, distances and directions in words, no coordinates.
# The memory section stays apart from CARD_BUDGET (card_check counts the card without it). The card is rebuilt when the book's
# names change. memory_answers answers "شو في عنا عناوين" / "وين <name>" from the same rows (none and after-unknown paths).
BOOK_CARD_MAX = 8
BOOK_FIX = "book_memory"
_memory_text_s85b = Chat._memory_text


def _memory_text_s86(self, snap, mem):
    """As before (s85 keeps the far_report line, what she did بغيابك), plus her address book (sol_address, the game's book):
    one compact line of at most BOOK_CARD_MAX entries."""
    text = _memory_text_s85b(self, snap, mem)
    MA.BOOK_ENABLED[0] = fix_on(self.dir, BOOK_FIX)
    try: line = MA.book_line(snap, BOOK_CARD_MAX)
    except Exception as e:
        self.log("chat: address book memory failed: %r" % (e,)); line = None
    return (text + " " + line) if line else text


_session_sheet_s85 = Chat._session_sheet


def _session_sheet_s86(self, snap, mem, acts):
    MA.BOOK_ENABLED[0] = fix_on(self.dir, BOOK_FIX)
    sig = MA.book_sig(snap)
    if sig != getattr(self, "_book_sig", None):
        if getattr(self, "_book_sig", None) is not None or sig is not None: self._sheet = None    # her book changed: new memory on the card
        self._book_sig = sig
    return _session_sheet_s85(self, snap, mem, acts)


_route_by_model_s85b = Chat._route_by_model


def _route_by_model_s86(self, history, c, key, snap, mem):
    MA.BOOK_ENABLED[0] = fix_on(self.dir, BOOK_FIX)                           # the book's answers only with the switch on
    return _route_by_model_s85b(self, history, c, key, snap, mem)


Chat._memory_text = _memory_text_s86
Chat._session_sheet = _session_sheet_s86
Chat._route_by_model = _route_by_model_s86


# ---------------------------------------------------------------- s88 why it failed, memory back after a reconnect
# 1. "ليش": the newest real failure (the game's note, an order the game refused, a failed drive), in her words. Switch fail_reasons.
# 2. After a reconnect: the world's conversation back in the chat panel at once, a message before the world is known kept, and the
#    card's memory rebuilt as soon as what she remembers changes.
FAIL_FILE_S88 = "SolFail_State.txt"
WHY_WINDOW_S88 = 15 * 60                                                     # seconds: an older failure is not "the last thing"
_LAST_FAIL_S88 = {}
WHY_AR_S88 = {
    "no_path": "ما لقيت طريق يوصلني لهناك، كل ما حاولت رجعت لنفس المحل.",
    "carry_no_path": "ما لقيت طريق أوصل فيه الغراض.",
    "door_unreachable": "ما قدرت أوصل لباب السيارة، كان في شي سادد الطريق عليه.",
    "door_far": "ما وصلت لباب السيارة.",
    "door_locked": "باب السيارة كان مقفول.",
    "board_timeout": "طوّلت وأنا عم حاول إركب وما زبطت.",
    "wheel_timeout": "طوّلت وأنا رايحة عالمقود وما وصلت.",
    "no_wheel": "ما قدرت إقعد ورا المقود.",
    "no_seat": "ما كان في مقعد فاضي إركب فيه.",
    "unavailable_board": "ما كان في مقعد فاضي إركب فيه.",
    "unavailable_exit": "السيارة كانت ماشية وما فيني إنزل.",
    "still_in": "ضليت بالسيارة، ما قدرت إنزل.",
    "stranger": "كان في حدا غريب بالسيارة.",
    "preempted": "كل ما بلّشت، كان في شي تاني يقطعني.",
    "busy": "كنت مشغولة بشي تاني.",
    "threat": "كان في زومبي قريب، وما فيني إتحرك قبل ما نخلص منه.",
    "no_key": "ما كان معي مفتاح هالسيارة.",
    "no_usable_car": "السيارات اللي حوالينا كلها مقفولة وما معنا مفاتيحها.",
    "no_vehicle_near": "ما كان في سيارة قريبة.",
    "bridge_failure": "السيارة ما مشيت عالطريق اللي رسمتو، فوقفت.",
    "no_route": "ما لقيت طريق بالسيارة لهناك.",
    "road_goal_unavailable": "ما لقيت طريق بالسيارة لهناك.",
    "no_way_round": "الطريق كان مسكّر قدامي وما في لفّة حواليه.",
    "leg_stalled": "علقت بنص الطريق وما قدرت كمّل.",
    "native_released": "السيارة وقفت لحالها بنص الطريق.",
    "player_stop": "إنت وقفتني.",
    "no_row": "ما وصلني الأمر منيح، عيدو.",
    "driving_unavailable": "ما كان فيني سوق وقتها.",
    "player_is_driver": "إنت كنت ورا المقود.",
    "exit_failed": "ما قدرت إنزل من السيارة.",
    "base_missing": "ما في قاعدة محددة لهالشغل.",
}
_run_action_s88_base = run_action
QUERY_OPTIONS_S88 = ("status", "poll", "report", "street", "gardens", "list", "cars", "car_where", "interrupt")   # questions, not orders


def run_action(lua_dir, action, option=None, wait=3.0):
    r = _run_action_s88_base(lua_dir, action, option, wait)
    query = str(option or "") in QUERY_OPTIONS_S88 or str(action).endswith("_status")
    if isinstance(r, dict) and r.get("ok") is False and not query:
        _LAST_FAIL_S88.clear()
        _LAST_FAIL_S88.update(t=time.time(), source="action:" + str(action), reason=str(r.get("reason") or r.get("error") or ""), detail=str(option or ""))
    return r


def read_fail_note(lua_dir):
    """The game's newest failure note (SolFailNote.lua), with the file's time as when; None when there is none."""
    path = os.path.join(lua_dir, FAIL_FILE_S88)
    try:
        with open(path, encoding="ascii", errors="replace") as f:
            st = dict(l.split("=", 1) for l in f.read().splitlines() if "=" in l)
        st["when"] = os.path.getmtime(path)
    except (OSError, ValueError): return None
    return st if st.get("reason") else None


def why_line(reason, detail=""):
    """Her own sentence for a failure code; the code itself is never said."""
    r = str(reason or "").strip()
    if re.search(r"[؀-ۿ]", r): return r                              # the game already said it in her words
    for pre in ("drive_cancelled:", "deferred:"):
        if r.startswith(pre): r = r[len(pre):]
    base = r.split(":", 1)[0].strip()
    if base.endswith("no_key"): base = "no_key"
    line = WHY_AR_S88.get(base) or reason_ar(r)
    if line: return line if line.endswith((".", "!", "؟")) else line + "."
    return "ما زبطت معي، وما عرفت شو اللي وقّفها بالضبط."


def _why_answer_s88(self, snap):
    if not fix_on(self.dir, "fail_reasons"): return _why_answer_s87(self, snap)
    now, found = time.time(), []
    note = read_fail_note(self.dir)
    if note: found.append((note["when"], "game:" + str(note.get("source") or ""), note.get("reason"), note.get("detail") or ""))
    if _LAST_FAIL_S88: found.append((_LAST_FAIL_S88["t"], _LAST_FAIL_S88["source"], _LAST_FAIL_S88["reason"], _LAST_FAIL_S88["detail"]))
    g = self.gps_state() or {}
    if str(g.get("result")) in ("failed", "interrupted") and g.get("reason") not in (None, "", "walking_to_door", "moving_to_wheel"):
        try: when = os.path.getmtime(os.path.join(self.dir, GPS_STATE))
        except OSError: when = now
        found.append((when, "gps", g.get("reason"), ""))
    found = [f for f in found if now - f[0] <= WHY_WINDOW_S88]
    if found:
        when, source, reason, detail = max(found, key=lambda f: f[0])
        line = why_line(reason, detail)
        self.log("chat: why -> source=%s reason=%s detail=%s age=%ds -> %s" % (source, reason, str(detail)[:160], int(now - when), line))
        return line
    line = _FT85.stop_line(((snap or {}).get("solFarm") or {}).get("stop")) or "ما صار شي غلط هلأ."      # an old failed drive is not "the last thing"
    self.log("chat: why -> no failure in the last %d min -> %s" % (WHY_WINDOW_S88 // 60, line))
    return line


_why_answer_s87 = Chat._why_answer
Chat._why_answer = _why_answer_s88


def memory_sig_s88(snap, mem):
    """What she remembers, in a few values: the card's memory is rebuilt when one of them changes."""
    if mem is None: return ("no_world",)
    s = snap or {}
    h = mem.data.get("home") or s.get("solHome")
    farm = s.get("solFarm") if isinstance(s.get("solFarm"), dict) else {}
    return (mem.key, isinstance(h, dict) and h.get("x") is not None, len(mem.data.get("places") or []), int(mem.data.get("deaths") or 0),
            isinstance(s.get("sol"), dict), len(farm.get("zones") or []), isinstance(s.get("solParking"), dict))


_session_sheet_s87 = Chat._session_sheet


def _session_sheet_s88(self, snap, mem, acts):
    sig = memory_sig_s88(snap, mem)
    if getattr(self, "_sheet_sig_s88", None) != sig:
        if getattr(self, "_sheet_sig_s88", None) is not None: self.log("chat: her memory changed %s -> %s, card rebuilt" % (self._sheet_sig_s88, sig))
        self._sheet, self._sheet_sig_s88 = None, sig
    return _session_sheet_s87(self, snap, mem, acts)


Chat._session_sheet = _session_sheet_s88
_handle_s87 = Chat.handle


def _handle_s88(self, text):
    if not self._hist_file:                                                      # the world first: his line joins that world's own history
        try: self._world()
        except Exception as e: self.log("chat: world not known before the message: %r" % (e,))
    return _handle_s87(self, text)


Chat.handle = _handle_s88
_poll_once_s87 = Chat.poll_once
BIND_EVERY_S88 = 1.0


def _poll_once_s88(self):
    if not self._hist_file and time.time() - getattr(self, "_bind_try_s88", 0) >= BIND_EVERY_S88:
        self._bind_try_s88 = time.time()
        try: self._world()
        except Exception as e: self.log("chat: world not known yet: %r" % (e,))
    out = _poll_once_s87(self)
    if self._hist_file and self._hist_file != getattr(self, "_published_hist_s88", None):
        self._published_hist_s88 = self._hist_file
        self.publish()
        self.log("chat: conversation of this world back in the game, %d messages (%s)" % (len(self.hist), os.path.basename(os.path.dirname(self._hist_file))))
    return out


Chat.poll_once = _poll_once_s88


# ---------------------------------------------------------------- s90 card tiers: index + per-message examples
# The card's tier 1 is the cached session sheet; the examples are added per message, from what he just wrote.
_SAID_S90 = []
_session_sheet_pre_s90 = Chat._session_sheet


def _session_sheet_s90(self, snap, mem, acts):
    text = _session_sheet_pre_s90(self, snap, mem, acts)
    if not getattr(MR, "CARD_TIERS", False):
        # s154: the card unchanged; an action it does not list is shown with the line that asks for it
        if _SAID_S90 and hasattr(MR, "add_extra_actions") and fix_on(self.dir, "card_extra_actions"):
            card = MR.add_extra_actions(text, _SAID_S90[-1], acts)
            if card != text: self.log("chat: card +%d chars (an action for this line)" % (len(card) - len(text)))
            return card
        return text
    if not _SAID_S90: return text
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


# ---------------------------------------------------------------- s87 smart_park: park near any place
# smart_park: "صفي السيارة" away from the marked garage -> the game's nearest free spot (SolSmartPark.lua), then a check that the
# whole car is inside. At the garage, or when he names it, the garage park exactly as before.
import farm_talk as _FT87
SMART_PARK_HOME_REACH = 40              # tiles: her car this close to his marked parking area -> that area (the garage park)
SMART_PARK_SETTLE_S = 60                # the last metres and the check, at most
SMART_PARK_DRIVE_S = 600
_GARAGE_WORD_S87 = re.compile(r"(?:كراج|جراج|موقف|مصف|باركينج)")
SMART_PARK_LINES = {
    "start": "رايحة صفها بأقرب مكان فاضي.",
    "already": "هي مصفوفة بمكان صف.",
    "no_spot": "ما لقيت مكان فاضي قريب بتساع السيارة.",
    "no_car": "ما في سيارة جنبي لصفها.",
    "not_loaded": "ما بشوف المكان حوالي منيح هلأ.",
    "near_only": "وقفت جنب المكان، بس ما قدرت فوتها جواته.",
    "inside": "صفيتها جوا المكان.",
    "outside": "صفيتها، بس مش كلها جوا المكان.",
    "failed": "ما قدرت صفها جوا المكان.",
    "no_answer": "ما قدرت لاقي مكان هلأ.",
}
_park_car_s86 = Chat._park_car
_park_watch_s86 = Chat._park_watch
_pre_intents_s86 = Chat._pre_intents


def _pre_intents_s87(self, history, snap, mem):
    last = history[-1] if history else {}
    self._park_said_s87 = str(last.get("said") or last.get("text") or "") if isinstance(last, dict) else ""
    return _pre_intents_s86(self, history, snap, mem)


def smart_park_wanted(snap, said):
    """False: the garage park (he named the garage, or her car is near the area he marked). True: the nearest free spot."""
    s = snap or {}
    marked = s.get("solParking")
    if not isinstance(marked, dict) or marked.get("x") is None: return True
    if _GARAGE_WORD_S87.search(_FT87.norm(said or "")): return False
    sol = s.get("sol") or {}
    if sol.get("x") is None or sol.get("y") is None: return False
    return (sol["x"] - marked["x"]) ** 2 + (sol["y"] - marked["y"]) ** 2 > SMART_PARK_HOME_REACH ** 2


_SPOT_S87 = re.compile(r"^spot:(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(\w+),(\d+)$")


def _park_car_s87(self, snap):
    if not fix_on(self.dir, "smart_park") or not smart_park_wanted(snap, getattr(self, "_park_said_s87", "")):
        self._smart_park_waiting = None
        return _park_car_s86(self, snap)
    self._park_waiting = None
    r = run_action(self.dir, "sol_smart_park", "find", wait=4.0)
    self.log("chat: smart park find -> %s" % r)
    reason = str(r.get("reason") or "") if isinstance(r, dict) else ""
    ok = isinstance(r, dict) and r.get("ok") is True
    if ok and reason.startswith("already:"):
        self._smart_park_waiting = None
        self._forced = SMART_PARK_LINES["already"]
        return
    m = _SPOT_S87.match(reason) if ok else None
    if not m:
        self._smart_park_waiting = None
        self._forced = SMART_PARK_LINES.get(reason) or (SMART_PARK_LINES["no_answer"] if not ok else SMART_PARK_LINES["no_spot"])
        return
    x, y = int(float(m.group(1))), int(float(m.group(2)))
    rid = gps_request(self.dir, {"action": "drive", "x": x, "y": y, "name": "مكان الصف", "speed": "slow"})
    out = _drive_outcome(self.dir, rid, {"sent": "smart parking", "x": x, "y": y})
    self.log("chat: smart park %s %s,%s -> %s" % (m.group(7), x, y, out))
    started = out.get("ok") or str(out.get("reason")) in ("moving_to_wheel", "walking_to_door")
    self._forced = SMART_PARK_LINES["start"] if started else drive_reply(out)
    self._smart_park_waiting = {"t": time.time(), "phase": "drive", "spot": reason} if started else None


def _smart_park_watch(self):
    """Her drive to the spot: the last metres when the GPS arrived, then whether the whole car is inside, said once."""
    w = getattr(self, "_smart_park_waiting", None)
    if not w: return
    now = time.time()
    if w.get("phase") == "settle":
        r = run_action(self.dir, "sol_smart_park", "status", wait=2.5)
        reason = str(r.get("reason") or "") if isinstance(r, dict) else ""
        answered = isinstance(r, dict) and r.get("ok") is not None
        if not answered or (r.get("ok") and reason == "working"):
            if now - w["since"] > SMART_PARK_SETTLE_S:
                self._smart_park_waiting = None
                self._say_later(SMART_PARK_LINES["failed"])
            return
        self._smart_park_waiting = None
        self.log("chat: smart park status -> %s" % r)
        if r.get("ok") and reason == "inside": self._say_later(SMART_PARK_LINES["inside"])
        elif r.get("ok") and reason.startswith("outside"): self._say_later(SMART_PARK_LINES["outside"])
        else: self._say_later(SMART_PARK_LINES["failed"])
        return
    if now - w["t"] > SMART_PARK_DRIVE_S:
        self._smart_park_waiting = None
        return
    g = self.gps_state() or {}
    result, reason = str(g.get("result") or ""), str(g.get("reason") or "")
    if result == "arrived" and reason in ("arrived", ""):
        r = run_action(self.dir, "sol_smart_park", "settle", wait=2.5)
        self.log("chat: smart park settle -> %s" % r)
        if isinstance(r, dict) and r.get("ok"): w.update(phase="settle", since=now)
        else:
            self._smart_park_waiting = None
            self._say_later(SMART_PARK_LINES["near_only"])
    elif result in ("failed", "interrupted") and reason not in ("walking_to_door", "moving_to_wheel", "await_destination", "board_passenger", ""):
        self._smart_park_waiting = None
        if "player" not in reason: self._say_later(drive_reply({"ok": False, "reason": reason}))


def _park_watch_s87(self):
    _park_watch_s86(self)
    _smart_park_watch(self)


Chat._pre_intents = _pre_intents_s87
Chat._park_car = _park_car_s87
Chat._park_watch = _park_watch_s87

# ---------------------------------------------------------------- s91 engine off on exit, unless he says keep it running
# exit_car keep_engine (the model's answer, model_router.KEEP_ENGINE_S91): the exit order the Mind sends in that route carries
# option keep_engine; the game (SolExitEngine.lua, switch exit_engine_off) leaves the engine running for that exit only.
_run_action_s91_base = run_action


EXIT_VERB_S91 = "exit_vehicle"                                                # the game's exit order (SolOrders.leaveCar)


def run_action(lua_dir, action, option=None, wait=3.0):
    if option is None and action == EXIT_VERB_S91 and getattr(MR, "KEEP_ENGINE_S91", False):
        MR.KEEP_ENGINE_S91 = False
        option = "keep_engine"
    return _run_action_s91_base(lua_dir, action, option, wait)


_route_by_model_s91_base = Chat._route_by_model


def _route_by_model_s91(self, history, c, key, snap, mem):
    MR.KEEP_ENGINE_S91 = False
    try: return _route_by_model_s91_base(self, history, c, key, snap, mem)
    finally: MR.KEEP_ENGINE_S91 = False


Chat._route_by_model = _route_by_model_s91
# ---------------------------------------------------------------- s91 end


# ---------------------------------------------------------------- s105 combat_plans
# sol_combat_plan: her own line for the plan the game set; the option the model wrote goes to the game as the plan id.
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


# ---------------------------------------------------------------- s109 reply_after_result
# Switch reply_after_result: she says what the game confirmed, never a success line before (or against) its answer.
SW_S109 = "reply_after_result"
EXTRA_WAIT_S109, LATE_GIVE_UP_S109, HERE_WAIT_S109 = 2.0, 30.0, 4.0           # seconds
NEUTRAL_S109 = "ثانية، عم شوف."
LATE_OK_S109 = "تمام."
LATE_NONE_S109 = "ما زبطت معي هلأ، جرب كمان مرة."
EDGE_START_S109 = "سيارتي بعيدة كتير عنك، وما بقدر وصل فيها لعندك. بجيبها لأقرب طريق منك، بدي %s، وبقلك وين تلاقيني."
EDGE_THERE_S109 = "صرت بالسيارة عالطريق، %s. قرّب لصوبي شوي، وأول ما تقرب بجي لعندك."
EDGE_ON_WAY_S109 = "لسا بالطريق مع السيارة، باقي %s، وبعدين بقلك وين تلاقيني."
EDGE_MOVING_S109 = "لسا بالطريق مع السيارة، شوي وبقلك وين تلاقيني."
FAR_COMING_S109 = "لسا جاية، باقي %s."
FAR_NEAR_S109 = "صرت قريبة، اصبر شوي."
FAR_AWAY_S109 = "أنا بعيدة عنك هلأ. إذا بدك قلي تعالي."
HERE_GO_S109 = "رايحة عالسيارة وجايتك."
HERE_AT_S109 = "أنا عندك."
FOOT_S109 = "%s، فجاية مشي، بدي %s."
CAR_WHY_S109 = {
    "car_not_near": "سيارتي بعيدة عنك", "no_fuel": "سيارتي ما فيها بنزين كفاية", "picked_no_fuel": "السيارة اللي لقيتها ما فيها بنزين كفاية",
    "car_taken": "أنت راكب سيارتي", "car_locked": "سيارتي مقفولة", "car_no_key": "ما معي مفتاح سيارتي", "car_lock_unknown": "ما عرفت إذا سيارتي مقفولة",
    "towing": "سيارتي عم تجر شي", "no_car": "ما بعرف وين سيارتي", "no_route": "ما لقيت طريق للسيارة لعندك",
    "car_too_close": "سيارتي مو بعيدة عنك بس ما بقدر جيبها من هون", "no_car_near": "ما في سيارة حدي بقدر سوقها",
    "locked_near": "السيارات اللي حدي مقفولة", "no_key_near": "ما معي مفاتيح للسيارات اللي حدي", "no_fuel_near": "السيارات اللي حدي ما فيها بنزين كفاية",
}
CAR_WHY_ANY_S109 = "ما قدرت جيب السيارة"
_COMPASS_S109 = ("بالشرق", "بالجنوب الشرقي", "بالجنوب", "بالجنوب الغربي", "بالغرب", "بالشمال الغربي", "بالشمال", "بالشمال الشرقي")
_PRESENCE_S109 = re.compile(r"هنا|هون|جنبك|حدك|معك|عندك|وصلت|بوصل|دقيق|دقايق|ثواني|باقي|قريب|جاي[ةه]")
_GPS_WAITING_S109 = ("board_passenger", "moving_to_wheel", "walking_to_door", "await_destination", "")
_PENDING_S109 = []                                                           # actions the game had not answered when she spoke


def _s109_on(lua_dir): return fix_on(lua_dir, SW_S109)


_action_receipt_note_s109_base = action_receipt_note


def action_receipt_note(result):
    """Switch on (the result carries s109): not confirmed yet -> the neutral line; a refusal -> s88's words for its reason."""
    if isinstance(result, dict) and result.get("s109"):
        if result.get("ok") is None and not result.get("error"): return NEUTRAL_S109
        if result.get("error") or result.get("ok") is False: return why_line(result.get("reason") or result.get("error") or "")
    return _action_receipt_note_s109_base(result)


_resolve_and_run_s109_base = resolve_and_run


def resolve_and_run(lua_dir, aid, opt, mem, snap, log=print):
    r = _resolve_and_run_s109_base(lua_dir, aid, opt, mem, snap, log)
    if not isinstance(r, dict) or not _s109_on(lua_dir): return r
    rid = r.get("rid")
    if r.get("ok") is None and rid is not None and not r.get("error"):
        end, got = time.time() + EXTRA_WAIT_S109, None
        while time.time() < end:
            got = action_result(lua_dir, rid)
            if got is not None: break
            time.sleep(0.1)
        if got is not None:
            r.clear(); r.update(got)                                            # in place: s105's record of this run sees the answer too
        else:
            _PENDING_S109.append({"dir": lua_dir, "rid": rid, "action": aid, "option": opt, "t": time.time()})
    r["s109"] = True
    return r


def _spy_s109(fn, *a):
    """fn(*a) with every run_action it makes recorded as (action, option, result)."""
    seen, base = [], globals()["run_action"]

    def spy(d, action, option=None, wait=3.0):
        r = base(d, action, option, wait=wait)
        seen.append((action, option, r))
        return r
    globals()["run_action"] = spy
    try: out = fn(*a)
    finally: globals()["run_action"] = base
    return out, seen


def _why_s109(r): return str(r.get("reason") or r.get("error") or "") if isinstance(r, dict) else ""


def _foot_after_car_s109(seen):
    """Why her car could not come, from the game's own answers in this turn (the first refusal on the car's way)."""
    calls = [(str(o or ""), r) for a, o, r in seen if a == "sol_far"]
    where_ok = False
    for o, r in calls:
        why = _why_s109(r)
        ok = isinstance(r, dict) and r.get("ok")
        if o == "come_car" and not ok and why != "car_not_near": return why
        if o == "car_where":
            if not ok: return why
            where_ok = True
        if o.startswith("car_far:") and (not ok or not why.startswith("waiting:")): return why
    if where_ok and not any(o.startswith("car_far:") for o, _ in calls): return "no_route"   # no road spot for it
    return "car_not_near"


def _edge_place_s109(self):
    """Where the car waits, from him now: "شي 90 متر بالشمال منك" (no numbers but metres)."""
    edge = getattr(self, "_s109_edge", None) or {}
    try: snap = self._world()[0] or {}
    except Exception: snap = {}
    me = snap.get("player") or {}
    if edge.get("x") is None or me.get("x") is None: return "قريب منك"
    dx, dy = edge["x"] - float(me["x"]), edge["y"] - float(me["y"])
    d = max(10, int(round(math.hypot(dx, dy) / 10.0)) * 10)
    side = _COMPASS_S109[int(round(math.atan2(dy, dx) / (math.pi / 4))) % 8]   # y grows to the south
    return "شي %d متر %s منك" % (d, side)


def _s109_far_line(self, far):
    """Her real state while she is not here, in her words."""
    edge = getattr(self, "_s109_edge", None) if getattr(self, "_far_waiting", False) == "car_far" else None
    if edge:
        if far == "placed": return EDGE_THERE_S109 % _edge_place_s109(self)
        if far.startswith("waiting:"): return far_wait_line(far, EDGE_ON_WAY_S109)
        return EDGE_MOVING_S109
    if far.startswith("waiting:"): return far_wait_line(far, FAR_COMING_S109)
    if far in ("seeking", "placed"): return FAR_NEAR_S109
    return FAR_AWAY_S109


_far_come_s109_base = Chat._far_come


def _far_come_s109(self, goal=None, by_car=False):
    if not _s109_on(self.dir): return _far_come_s109_base(self, goal, by_car)
    self._s109_edge = None
    _, seen = _spy_s109(_far_come_s109_base, self, goal, by_car)
    mode = getattr(self, "_far_waiting", False)
    started = lambda r: isinstance(r, dict) and r.get("ok") and _why_s109(r).startswith("waiting:")
    moved = next(((str(o), r) for a, o, r in seen if a == "sol_far" and str(o or "").startswith("car_far:")), None)
    foot = next((r for a, o, r in reversed(seen) if a == "sol_far" and o == "come"), None)
    if mode == "car_far" and moved is not None and started(moved[1]) and not moved[0].endswith(",in"):   # the old far move: the car stops outside his area
        try: x, y = (float(v) for v in moved[0][8:].split(",")[:2])
        except ValueError: x = y = None
        self._s109_edge = {"x": x, "y": y, "told": False}
        self._forced = far_wait_line(_why_s109(moved[1]), EDGE_START_S109)
    elif by_car and started(foot):                                              # her car could not come, she walks: why first
        why = _foot_after_car_s109(seen)
        self._forced = FOOT_S109 % (CAR_WHY_S109.get(why, CAR_WHY_ANY_S109), far_wait_line(_why_s109(foot), "%s"))
    self.log("chat: s109 far come by_car=%s mode=%s -> %s" % (by_car, mode, self._forced))


_far_watch_s109_base = Chat._far_watch


def _far_watch_s109(self):
    edge = getattr(self, "_s109_edge", None)
    if not edge or edge.get("told") or getattr(self, "_far_waiting", False) != "car_far" or not _s109_on(self.dir): return _far_watch_s109_base(self)
    p = run_action(self.dir, "sol_far", "poll", wait=2.5)
    if isinstance(p, dict) and p.get("ok") and str(p.get("reason")) == "placed":    # the car is at the road: he hears where, once
        edge["told"] = True
        line = EDGE_THERE_S109 % _edge_place_s109(self)
        self.log("chat: s109 far car at the road -> %s" % line)
        self._say_later(line)
        return
    return _far_watch_s109_base(self)


_far_order_s109_base = Chat._far_order


def _far_order_s109(self, text, snap, done, said=None):
    if not _s109_on(self.dir): return _far_order_s109_base(self, text, snap, done, said)
    out, seen = _spy_s109(_far_order_s109_base, self, text, snap, done, said)
    forced = getattr(self, "_forced", None)
    status = next((_why_s109(r) for a, o, r in reversed(seen) if a == "sol_far" and o == "status"), "")
    coming_line = forced == FAR_ON_WAY or (isinstance(forced, str) and forced.startswith("جاية، باقي"))
    if out and coming_line and status and getattr(self, "_far_waiting", False) == "car_far" and getattr(self, "_s109_edge", None):
        self._forced = _s109_far_line(self, status)
        self.log("chat: s109 far called again while %s -> %s" % (status, self._forced))
    return out


_route_by_model_s109_base = Chat._route_by_model


def _route_by_model_s109(self, history, c, key, snap, mem):
    """As before; her plain talk may not say she is here (or arriving, or how long) while the game says she is not."""
    if not _s109_on(self.dir): return _route_by_model_s109_base(self, history, c, key, snap, mem)
    lines, log0 = [], self.log
    self.log = lambda m: (lines.append(str(m)), log0(m))[1]
    try: reply = _route_by_model_s109_base(self, history, c, key, snap, mem)
    finally: self.log = log0
    route = [l for l in lines if l.startswith("chat: route text=")]
    if not isinstance(reply, str) or not route or " path=model " not in route[-1] or " action=none " not in route[-1]: return reply
    if not _PRESENCE_S109.search(reply): return reply
    sol = (snap or {}).get("sol")
    if isinstance(sol, dict) and sol and not sol.get("away"): return reply
    far = self._far_state(snap)
    if far is None: return reply
    line = _s109_far_line(self, far)
    self.log("chat: s109 her talk said she was here while %s: %s -> %s" % (far, reply[:60], line))
    return line


def _s109_goal(self, gid):
    eng = self.goals
    lock = getattr(eng, "lock", None)
    if lock is not None: lock.acquire()
    try:
        for g in [getattr(eng, "active", None)] + list(reversed(list(getattr(eng, "history", None) or []))):
            if isinstance(g, dict) and g.get("id") == gid: return dict(g)
    finally:
        if lock is not None: lock.release()
    return None


def _foot_line_s109(why):
    return why_line(why).rstrip(".!؟ ") + "، فجاية مشي."


def _s109_here_line(self, gid):
    """The game's first answer to her drive to him: a line, "" (nothing to say), or None (not in yet)."""
    g = _s109_goal(self, gid)
    if g is None: return ""
    st, reason = g.get("status"), str(g.get("reason") or "")
    if st == "completed":
        if reason.startswith("coming_on_foot:"): return _foot_line_s109(reason.split(":", 1)[1])
        if reason == "arrived_at_player": return HERE_AT_S109
        return ""
    if st == "failed":
        if reason == "player_took_over": return ""
        if reason == "no_sol": return "ما فيني هلأ."
        if reason == "gps_unconfirmed": return LATE_NONE_S109
        return why_line(reason)
    if st != "running": return ""
    rid = g.get("gpsRid")
    if not rid: return None
    gs = self.gps_state() or {}
    if str(gs.get("ack") or "") != str(rid): return None
    if (gs.get("result") or "") == "failed" and (gs.get("reason") or "") not in _GPS_WAITING_S109: return None   # the goal turns it into on foot next
    if (gs.get("result") or "") == "stopped": return ""
    return HERE_GO_S109


_pre_intents_s109_base = Chat._pre_intents


def _pre_intents_s109(self, history, snap, mem):
    """As before; "come to me by car" while she is here is answered from the game's first answer to the drive."""
    if not _s109_on(self.dir) or getattr(self, "goals", None) is None: return _pre_intents_s109_base(self, history, snap, mem)
    eng, sub = self.goals, []
    had = "submit" in vars(eng)
    real = eng.submit

    def submit(goal):
        if isinstance(goal, dict) and goal.get("intent") == "fetch_player":
            goal = dict(goal, slots=dict(goal.get("slots") or {}, quiet="1"))       # her line comes from the game's answer, not twice
            r = real(goal)
            sub.append(r)
            return r
        return real(goal)
    eng.submit = submit
    try: done = _pre_intents_s109_base(self, history, snap, mem)
    finally:
        if had: eng.submit = real
        else:
            try: del eng.submit
            except AttributeError: pass
    r = sub[-1] if sub else None
    if isinstance(r, dict) and r.get("ok") and r.get("status") == "running" and r.get("goalId"):
        end, line = time.time() + HERE_WAIT_S109, None
        while time.time() < end:
            line = _s109_here_line(self, r["goalId"])
            if line is not None: break
            time.sleep(0.15)
        if not line:
            self._s109_here = {"goalId": r["goalId"], "t": time.time()}
            line = NEUTRAL_S109
        self._forced = line
        self.log("chat: s109 come by car while here -> %s" % line)
    return done


def _s109_watch(self):
    """The answers that came after she spoke: said once, in her words."""
    if not _s109_on(self.dir): return
    now = time.time()
    for p in list(_PENDING_S109):
        if p["dir"] != self.dir: continue
        got = action_result(self.dir, p["rid"])
        if got is None and now - p["t"] < LATE_GIVE_UP_S109: continue
        _PENDING_S109.remove(p)
        if got is None: line = LATE_NONE_S109
        elif got.get("ok") is False:
            line = why_line(got.get("reason"))
            _LAST_FAIL_S88.clear()
            _LAST_FAIL_S88.update(t=now, source="action:" + str(p["action"]), reason=str(got.get("reason") or ""), detail=str(p.get("option") or ""))
        else: line = LATE_OK_S109
        self.log("chat: s109 late answer %s %s -> %s -> %s" % (p["action"], p.get("option"), got, line))
        self._say_later(line)
    here = getattr(self, "_s109_here", None)
    if here:
        line = _s109_here_line(self, here["goalId"])
        if line is None and now - here["t"] < LATE_GIVE_UP_S109: return
        self._s109_here = None
        if line is None: line = LATE_NONE_S109
        self.log("chat: s109 late drive answer -> %s" % (line or "(nothing to say)"))
        if line: self._say_later(line)


_poll_once_s109_base = Chat.poll_once


def _poll_once_s109(self):
    now = time.time()
    if now - getattr(self, "_s109_at", 0) >= 1.0:
        self._s109_at = now
        try: _s109_watch(self)
        except Exception as e: self.log("s109 watch failed: %r" % (e,))
    return _poll_once_s109_base(self)


Chat._far_come = _far_come_s109
Chat._far_watch = _far_watch_s109
Chat._far_order = _far_order_s109
Chat._route_by_model = _route_by_model_s109
Chat._pre_intents = _pre_intents_s109
Chat.poll_once = _poll_once_s109
# ---------------------------------------------------------------- s109 end

"""The one gate between a language model and the game.

A model may only propose: {"speech": ..., "action": id or null, "option": ..., "facts": [...]}.
The Mind checks the action against what she can do and what is true now, runs it itself, and only then speaks.
Anything about the world comes from the Mind's own data. A line naming an action, place or number the Mind does not have is replaced.
"""
import json
import random
import re
import time

SAFE_UNKNOWN = ("ما بعرف عن هالشي.", "مو متأكدة من هالشي.", "ما عندي خبر عن هالشي.")
SAFE_NOT_DONE = ("ما عملت شي هلأ.", "لسا ما عملت هالشي.")
SAFE_NOTHING = ("تكرم.", "ماشي.", "إيه.")
BANNED = ("اللعبة", "لعبة", "النظام", "تأكيد", "تؤكد", "يتأكد", "الخطة", "نموذج", "الموديل", "Project Zomboid", "Sol Mind", "Sol Link", "الأمر قبل")

QUESTION_MARKS = ("؟", "?")
QUESTION_WORDS = ("وين", "فين", "شو", "ليش", "كيف", "قديش", "كم", "مين", "متى", "هل", "شقد", "أي", "اي", "بتعرفي", "where", "what", "why", "how", "when", "which")
WORLD_WORDS = ("مزرعة", "مزرعه", "مزارع", "حديقة", "حديقه", "حقل", "فندق", "مستشفى", "مدرسة", "مدرسه", "كنيسة", "كنيسه", "سوبرماركت", "مطعم", "صيدلية", "صيدليه", "بلدة", "بلده", "ضيعة", "ضيعه", "كازية", "كازيه", "محطة", "محطه", "بنزين", "وقود", "مسافة", "مسافه", "متر", "مربع", "شارع", "طريق", "مدينة", "مدينه", "مخزن", "مكان", "اماكن", "أماكن", "بيت", "خريطة", "خريطه", "gas", "fuel", "distance", "station")
CLAIM_STEMS = ("طفيت", "شغلت", "شغّلت", "زمرت", "وصلت", "عبيت", "عبّيت", "سقت", "نزلت", "ركبت", "فتحت", "سكرت", "قتلت", "جبت", "حطيت", "علّمت", "علمت", "رحت", "مشيت", "رجعت", "turned", "started", "arrived", "filled")
CAR_ACTIONS = ("sol_headlights", "sol_engine", "sol_horn", "sol_car_wait")
CONTRADICT_SECONDS = 60
MAX_SPEECH = 400

_DIAC = re.compile(r"[ً-ٰٟ]")
_ACTION_TAG = re.compile(r"\[\s*(?:فعل|action)\s*:\s*([A-Za-z_]+)\s*(?:\|\s*([^\]]+))?\]")
_GOAL_TAG = re.compile(r"\[\s*(?:هدف|goal)\s*:\s*([A-Za-z_]+)\s*(?:\|\s*([^|\]]+))?\s*(?:\|\s*([^\]]+))?\]")
_JSON = re.compile(r"\{.*\}", re.S)
_NUM = re.compile(r"\d+")
# s77: a map position ("7411,8258", "x 7411 y 8258") is never speech, whatever the model was shown
COORD_RX = re.compile(r"(?<![\d.])\d{3,5}(?:\.\d+)?\s*[,،]\s*\d{3,5}(?:\.\d+)?(?:\s*[,،]\s*-?\d{1,2})?(?![\d])|\b[xX]\s*[=:]?\s*\d{3,5}\D{0,6}?\b[yY]\s*[=:]?\s*\d{3,5}")
_COORD_MARK = "\ue000"
_SENTENCE = re.compile(r"((?:[!?؟…\n]|(?<!\d)\.|\.(?!\d))+)")


def drop_coordinates(text):
    """Any sentence holding a map position is taken out. If nothing would be left, only the position (and the word before it) goes."""
    t = str(text or "")
    if not COORD_RX.search(_norm(t)): return t
    parts = _SENTENCE.split(t)
    kept = "".join(parts[i] + (parts[i + 1] if i + 1 < len(parts) else "") for i in range(0, len(parts), 2) if not COORD_RX.search(_norm(parts[i])))
    kept = kept.strip()
    if kept: return kept
    bare = re.sub(r"(?:\s+(?:عند|على|عل|ب|في|بـ|at))?\s*" + COORD_RX.pattern, "", _norm(t))
    return re.sub(r"\s+([.،,؟?!])", r"\1", re.sub(r"[ \t]{2,}", " ", bare)).strip()
_ARABIC_DIGITS = {0x660 + i: 48 + i for i in range(10)}
_ARABIC_DIGITS.update({0x6F0 + i: 48 + i for i in range(10)})


def _norm(text): return _DIAC.sub("", str(text or "")).translate(_ARABIC_DIGITS)


QUESTION_STARTS = ("في شي", "فيه شي", "تذكري", "بتذكري", "بتتذكري", "مرينا", "مرقنا", "شفنا")
_NAME_FIRST = re.compile(r"^(?:يا\s+)?سول[\s،,]+")
_TO_HER = re.compile(r"(?<![\w])(?:بت\w{2,}ين|تقدرين|تروحين|تعرفين|تريدين|تحتاجين|تشوفين|تحبين|تبين|انتي|إنتي)(?![\w])")


def speaks_to_herself(s):
    """She talks to a man. A line telling a woman what she can or needs to do is the model talking to Sol, not as her."""
    return _TO_HER.search(s) is not None


def is_question(text):
    t = _norm(text).strip()
    if any(m in t for m in QUESTION_MARKS): return True
    if _NAME_FIRST.sub("", t).startswith(QUESTION_STARTS): return True
    words = re.findall(r"[\w']+", t.lower())
    if any(w in QUESTION_WORDS for w in words[:3]): return True
    return len(words) > 1 and words[0] in ("سول", "يا") and any(w in QUESTION_WORDS for w in words[1:4])


_WORLD_ENDS = ("", "نا", "ي", "ك", "ه", "ها", "كم", "هم", "ات", "ين")
_WORLD_FORMS = set()
for _w in WORLD_WORDS:
    for _e in _WORLD_ENDS:
        _WORLD_FORMS.add(_w + _e)
        if _w.endswith("ة") and _e: _WORLD_FORMS.add(_w[:-1] + "ت" + _e)          # مدينة -> مدينتنا


def _is_world_word(w):
    """A whole word, with the letters Arabic glues on: بيتنا and ببيت count, خبيت and طريقة do not."""
    if w in _WORLD_FORMS: return True
    return any(w.startswith(c) and w[len(c):] in _WORLD_FORMS for c in _CLITICS)


def about_the_world(text):
    return any(_is_world_word(w) for w in _TOKEN.findall(_norm(text).lower()))


_NEGATIONS = {"ما", "مو", "مش", "لسا", "لسه", "ماني", "مالي"}


def claims_an_action(s):
    """A word saying she did something, whole-word from the start (فرحت is not رحت) and not negated (ما وصلت is not a claim)."""
    words = _TOKEN.findall(_norm(s).lower())
    for i, w in enumerate(words):
        bare = w[1:] if w.startswith("و") and len(w) > 3 else w
        if any(w.startswith(c) or bare.startswith(c) for c in CLAIM_STEMS) and not (i > 0 and words[i - 1] in _NEGATIONS): return True
    return False


def parse(raw):
    """A model's reply as {speech, action, option, goal, slots, facts}. Accepts the JSON form, the older bracket tags, or plain words."""
    raw = str(raw or "").strip()
    out = {"speech": "", "action": None, "option": None, "goal": None, "slots": {}, "facts": []}
    m = _JSON.search(raw)
    if m:
        try:
            d = json.loads(m.group(0))
            if isinstance(d, dict) and "speech" in d:
                out["speech"] = str(d.get("speech") or "").strip()
                out["action"] = d.get("action") or None
                out["option"] = d.get("option") or None
                facts = d.get("facts")
                out["facts"] = [str(x) for x in facts] if isinstance(facts, list) else []
                return out
        except ValueError:
            pass
    g = _GOAL_TAG.search(raw)
    if g:
        out["goal"] = g.group(1).strip()
        out["slots"] = {"target": (g.group(2) or "").strip() or None, "extract": (g.group(3) or "").strip() or None}
    a = _ACTION_TAG.search(raw)
    if a:
        out["action"] = a.group(1).strip()
        out["option"] = (a.group(2) or "").strip() or None
    out["speech"] = _ACTION_TAG.sub("", _GOAL_TAG.sub("", raw)).strip()
    return out


class Context:
    """What is true right now. known_text holds everything the Mind has actually told the model."""
    def __init__(self, user_text="", allowed=(), goals=(), known_text="", in_vehicle=False, recent=(), names=()):
        self.user_text, self.allowed, self.goals, self.known_text, self.in_vehicle, self.recent = user_text, set(allowed), set(goals), known_text, in_vehicle, list(recent)
        self.names, self.fixes = list(names), []                                # [(the right name, other spellings)], and what was put right


def check_action(p, ctx, now=None):
    """(allowed, why). The model has no say in whether something may happen."""
    now = time.time() if now is None else now
    if p.get("goal") is None and p.get("action") is None: return True, "none"
    if is_question(ctx.user_text): return False, "a_question_is_not_an_order"
    if p.get("goal") is not None:
        return (p["goal"] in ctx.goals, "known_goal" if p["goal"] in ctx.goals else "unknown_goal")
    aid = p["action"]
    if aid not in ctx.allowed: return False, "not_a_capability"
    if aid in CAR_ACTIONS and not ctx.in_vehicle: return False, "not_in_a_car"
    for when, did, opt in ctx.recent:
        if did == aid and now - when < CONTRADICT_SECONDS and str(opt or "") != str(p.get("option") or ""):
            return False, "contradicts_what_was_just_done"
    return True, "ok"


def mojibake(s): return re.search("[À-ÿ][\u0080-¿]|Ø|Ù", str(s or "")) is not None


_CLAUSE = re.compile(r"((?:[،؛,;!?؟…\n]|(?<!\d)\.|\.(?!\d))+)")
ALONE_OK = {"مرحبا", "اهلا", "أهلا", "اهلين", "أهلين", "هلا", "ماشي", "تكرم", "ايه", "إيه", "لأ", "لا", "حاضر", "طيب", "تمام", "اكيد", "أكيد"}
LEANS_ON_WHAT_WENT = ("لأن", "لان", "عشان", "لهيك", "لذلك")
TRIM_FIRST = ("بس", "لكن")


def _clause_fault(c, ctx, known, action_ran, named_in_line):
    """(why, the clause with spellings put right, the safe lines to use if nothing else of the reply survives). why is None when it stands."""
    if _COORD_MARK in c: return "coordinates", c.replace(_COORD_MARK, "x,y"), SAFE_UNKNOWN     # s77
    if "[" in c or "(" in c or "（" in c: return "not_speech", c, SAFE_UNKNOWN
    if any(w.lower() in c.lower() for w in BANNED): return "meta_words", c, SAFE_UNKNOWN
    if speaks_to_herself(c): return "speaks_to_herself", c, SAFE_UNKNOWN
    world = about_the_world(c)
    fixed, fixes, named, invented = resolve_names(c, ctx.names, known)
    ctx.fixes = list(ctx.fixes) + list(fixes)
    if not world: named, invented = False, []
    for n in _NUM.findall(fixed):
        if n not in known: return "number_not_known:" + n, c, SAFE_UNKNOWN
    if world and not (named or named_in_line) and not grounded(fixed, known): return "world_claim_not_known", c, SAFE_UNKNOWN
    if invented: return "invented_name:" + invented[0], c, SAFE_UNKNOWN
    if not action_ran and claims_an_action(fixed): return "claims_an_action", c, SAFE_NOT_DONE
    return None, fixed, None


def check_speech(p, ctx, action_ran):
    """(speech, why). why is None when something of the line stands; ctx.stripped lists the clauses that were taken out."""
    s = _norm(p.get("speech")).strip()
    ctx.stripped = []
    if not s: return random.choice(SAFE_NOTHING), "empty"
    if len(s) > MAX_SPEECH: return random.choice(SAFE_UNKNOWN), "too_long"
    if mojibake(s): return random.choice(SAFE_UNKNOWN), "mojibake"
    if s.startswith("{"): return random.choice(SAFE_UNKNOWN), "not_speech"
    s = COORD_RX.sub(_COORD_MARK, s)                                            # s77: the clause holding it is stripped below
    known = _norm(ctx.known_text)
    named_in_line = about_the_world(s) and resolve_names(s, ctx.names, known)[2]     # a real place named anywhere grounds the numbers beside it: "كازية X، 300 متر"
    parts = _CLAUSE.split(s)
    kept, first_fault = [], None
    for i in range(0, len(parts), 2):
        raw, delim = parts[i], parts[i + 1] if i + 1 < len(parts) else ""
        clause = raw.strip()
        if not clause:
            if kept: kept[-1] = (kept[-1][0], kept[-1][1] + raw + delim)
            continue
        why, fixed, safe = _clause_fault(clause, ctx, known, action_ran, named_in_line)
        if why:
            ctx.stripped.append((why, clause))
            first_fault = first_fault or (why, safe)
            continue
        kept.append((raw.replace(clause, fixed), delim))
    if first_fault is None: return "".join(c + d for c, d in kept).strip(), None
    if kept:
        head = kept[0][0].strip().split()
        if head and head[0] in LEANS_ON_WHAT_WENT: kept.pop(0)
        elif head and head[0] in TRIM_FIRST and len(head) > 1: kept[0] = (" ".join(head[1:]), kept[0][1])
    text = "".join(c + d for c, d in kept).rstrip("،,؛; \n").strip()
    words = re.findall(r"[\w']+", text)
    bare_ack = all(w in ALONE_OK for w in words)
    if not words or (len(words) == 1 and words[0] not in ALONE_OK) or (bare_ack and is_question(ctx.user_text)) or (getattr(ctx, "strict", False) and is_question(ctx.user_text)):
        return random.choice(first_fault[1]), first_fault[0]
    return text, None


def grounded(speech, known):
    """A sentence about the world must share a real name with what the Mind holds, beyond the generic words that made it about the world."""
    generic = set(WORLD_WORDS) | {"في", "من", "على", "عند", "ما", "لا", "هون", "هناك", "قريب", "بعيد", "اقرب", "أقرب", "مذكورة", "غير", "فيه", "عندي", "عنا", "اكيد", "أكيد"}
    words = [w for w in re.findall(r"[\w']+", speech) if len(w) >= 4 and w not in generic and not any(g in w for g in WORLD_WORDS)]
    return any(w in known for w in words)


# ---------------------------------------------------------------- names
# Letters that sound alike across Arabic and English share a key; vowels are dropped, because that is where spellings differ most.
_KEY = {}
for _key, _letters_of in (("b", "bpبپ"), ("t", "tتطث"), ("d", "dدضذ"), ("r", "rر"), ("s", "szسصزظ"), ("x", "xش"), ("f", "fvفڤ"),
                          ("k", "kgqjcجغقكگخ"), ("l", "lل"), ("m", "mم"), ("n", "nن")):
    for _c in _letters_of: _KEY[_c] = _key
_TOKEN = re.compile(r"[^\W_]+")
ROAD_SUFFIX = {"st", "street", "ave", "avenue", "rd", "road", "dr", "drive", "ln", "lane", "blvd", "boulevard", "hwy", "highway", "ct", "court", "pl", "place"}
MARKERS = {"شارع", "طريق", "كازية", "كازيه", "محطة", "محطه", "مدينة", "مدينه", "بلدة", "بلده", "ضيعة", "ضيعه"}
LOOSE_LETTERS, LOOSE_KEY = 6, 3
_CLITICS = ("وبال", "بال", "هال", "وال", "لل", "ال", "ب", "و", "ل", "ف")
SKIP_BEFORE_NAME = {"هو", "هي", "اسمه", "اسمها", "اسم", "المقرب", "المقربة", "القريب", "القريبة", "الاقرب", "الأقرب", "اقرب", "أقرب", "عند", "على", "في"}
NOT_A_NAME = {"هاد", "هاي", "هذا", "هذه", "قريب", "قريبة", "بعيد", "بعيدة", "البعيد", "البعيدة", "من", "الى", "إلى", "لعند", "جنب", "جنبك", "حد", "حدنا", "هون", "هنيك", "هناك",
              "ما", "مو", "لا", "مش", "بس", "يعني", "كمان", "لسا", "فيها", "فيه", "اللي", "يلي", "وحدة", "واحد", "حوالي", "مسكر", "مسكرة", "مفتوح", "مفتوحة", "فاضي", "فاضية",
              "منيح", "منيحة", "كبير", "كبيرة", "صغير", "صغيرة", "هلأ", "هلق", "بنزين", "البنزين", "وقود", "الوقود", "متر", "مترين", "مربع", "مذكورة"}
LATIN_GENERIC = {"gps", "ok", "okay", "gas", "fuel", "station", "distance", "street", "road"}


def name_key(text):
    t = str(text).lower().replace("ch", "x").replace("sh", "x").replace("ph", "f").replace("th", "t")
    out = []
    for c in t:
        k = c if c.isdigit() else _KEY.get(c)
        if k and (not out or out[-1] != k): out.append(k)
    return "".join(out)


def _bare(text):
    """The name without 'St' or 'Ave'."""
    words = str(text).split()
    return " ".join(words[:-1]) if len(words) > 1 and words[-1].lower().rstrip(".") in ROAD_SUFFIX else str(text)


def _letters(text): return sum(1 for c in str(text) if c.isalnum())


def _edit(a, b):
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, cb in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (ca != cb))
    return row[-1]


def _allowed(n): return 0 if n <= 3 else 1 if n <= 6 else 2


def match_name(text, names):
    """The right name for this spelling, or None. Two names equally close is no answer: she won't guess."""
    low = str(text).lower().strip()
    for right, others in names:
        if low in [str(x).lower() for x in (right,) + tuple(others)]: return right
    key, size, scored = name_key(_bare(text)), _letters(_bare(text)), []
    if len(key) < 2: return None
    for right, others in names:
        best = None
        for spelling in (right,) + tuple(others):
            k, n = name_key(_bare(spelling)), _letters(_bare(spelling))
            if len(k) < 2 or min(size, n) / float(max(size, n)) < 0.6: continue
            d = _edit(key, k)
            if d <= _allowed(max(len(key), len(k))) and (best is None or d < best): best = d
        if best is not None: scored.append((best, right))
    if not scored: return None
    scored.sort(key=lambda x: x[0])
    if len(scored) > 1 and scored[0][0] == scored[1][0] and scored[0][1] != scored[1][1]: return None
    return scored[0][1]


def _same_sound(text, names):
    """A long word sounding exactly like one name she knows. Away from a marker word, nothing looser than that."""
    key, size, found = name_key(_bare(text)), _letters(_bare(text)), set()
    if size < LOOSE_LETTERS or len(key) < LOOSE_KEY: return None
    for right, others in names:
        for spelling in (right,) + tuple(others):
            n = _letters(_bare(spelling))
            if name_key(_bare(spelling)) == key and min(size, n) / float(max(size, n)) >= 0.6: found.add(right)
    return found.pop() if len(found) == 1 else None


def _match(text, names):
    return match_name(text, names) or (match_name(text[2:], names) if text.startswith("ال") and len(text) > 4 else None)


def _is_latin(w): return re.search("[A-Za-z]", w) is not None
def _is_arabic(w): return re.search("[\u0600-\u06FF]", w) is not None


def _is_marker(w):
    if w in MARKERS: return True
    return any(w.startswith(c) and w[len(c):] in MARKERS for c in _CLITICS)


def resolve_names(s, names, known):
    """Finds the names in a line about the world. (line with spellings put right, [(said, right)], a real name was found, names that match nothing)."""
    toks = list(_TOKEN.finditer(s))
    low_known = known.lower()
    swaps, fixes, invented, named = [], [], [], False
    def glued(a, b): return s[toks[a].end():toks[b].start()].strip() == ""
    def attempt(start, stop):
        for end in range(stop, start, -1):
            said = s[toks[start].start():toks[end - 1].end()]
            right = _match(said, names)
            if right: return said, right, end
        return None
    i = 0
    while i < len(toks):
        w = toks[i].group(0)
        if _is_latin(w):
            j = i + 1
            while j < len(toks) and glued(j - 1, j) and (_is_latin(toks[j].group(0)) or toks[j].group(0).isdigit()): j += 1
            if j - i <= 4:
                hit = attempt(i, j)
                if hit:
                    named = True
                    if hit[0] != hit[1]: swaps.append((toks[i].start(), toks[hit[2] - 1].end(), hit[1])); fixes.append((hit[0], hit[1]))
                    i = hit[2]; continue
                for k in range(i, j):
                    t = toks[k].group(0)
                    if not t.isdigit() and t.lower() not in LATIN_GENERIC and t.lower() not in low_known: invented.append(t); break
            i = j; continue
        if not _is_marker(w):
            hit = None
            if _is_arabic(w):
                for end in range(min(i + 3, len(toks)), i, -1):
                    if end - 1 > i and not all(glued(q, q + 1) for q in range(i, end - 1)): continue
                    said = s[toks[i].start():toks[end - 1].end()]
                    right = _same_sound(said, names)
                    if right: hit = (said, right, end); break
            if hit:
                named = True
                if hit[0] != hit[1]: swaps.append((toks[i].start(), toks[hit[2] - 1].end(), hit[1])); fixes.append((hit[0], hit[1]))
                i = hit[2]
            else: i += 1
            continue
        j = i + 1
        while j < len(toks) and glued(j - 1, j) and toks[j].group(0) in SKIP_BEFORE_NAME: j += 1
        k = j
        while k < len(toks) and k - j < 3 and (k == j or glued(k - 1, k)):
            t = toks[k].group(0)
            if not (_is_arabic(t) or t.isdigit()) or t in NOT_A_NAME or t in SKIP_BEFORE_NAME or _is_marker(t) or t.startswith("بال"): break
            k += 1
        if k == j: i = j; continue
        hit = attempt(j, k)
        if hit:
            named = True
            if hit[0] != hit[1]: swaps.append((toks[j].start(), toks[hit[2] - 1].end(), hit[1])); fixes.append((hit[0], hit[1]))
            i = hit[2]; continue
        if toks[j].group(0) not in known: invented.append(toks[j].group(0))
        i = k
    for a, b, right in reversed(swaps): s = s[:a] + right + s[b:]
    return s, fixes, named, invented


INSTRUCTION = ('\n\nطريقة ردك إجبارية: اكتبي JSON واحد فقط بهذا الشكل بلا أي نص قبله أو بعده: '
               '{"speech": "جملة قصيرة باللهجة الشامية", "action": null, "option": null, "facts": []}. '
               'action يكون معرّفًا من قائمة الأفعال فقط، أو null. لا تذكري مكانًا أو رقمًا ليس مكتوبًا أمامك، ولا تقولي إنك فعلتِ شيئًا لم يُنفذ. '
               'اكتبي أسماء الشوارع والكازيات حرفيًا كما هي مكتوبة أمامك، بلا ترجمة ولا تعريب. '
               'لا تضيفي فعلًا إذا لم يطلب اللاعب ذلك صراحة.')


# ---------------------------------------------------------------- s78 cars_away
# A line with these is the model talking about the game, not Sol talking to him: the whole line goes.
ASK_AGAIN = "شو قصدك؟ عيدها بكلمة تانية."
META_RX = re.compile(r"(?<![\w])(?:و|ف)?(?:ال|لل|بال|ل|ب)?لاعب(?:ين)?(?![\w])|(?<![\w])(?:ال)?(?:مود|سكربت|سكريبت|سويتش)(?![\w])"
                     r"|\b(?:player|players|npc|npcs|mod|mods|lua|switch|script|kahlua|snapshot|mailbox)\b", re.I)
CODE_RX = re.compile(r"\b[A-Za-z]+\.[A-Za-z][A-Za-z0-9]+\b|\b[a-z]+_[a-z0-9_]+\b")
OWN_NAME_RX = re.compile(r"^\W*(?:يا\s*)?سول(?![\w])")                          # his address echoed back; "أنا سول" stands


def not_speech(s):
    """Why a whole model line cannot be said (meta_line, code_line, names_herself), or None."""
    t = _norm(s)
    if META_RX.search(t): return "meta_line"
    if CODE_RX.search(t): return "code_line"
    if OWN_NAME_RX.search(t.strip()): return "names_herself"
    return None


_check_speech_s77 = check_speech


def check_speech(p, ctx, action_ran):
    """s78: the whole line is refused first when it is not speech; everything else as before (s77 and earlier)."""
    s = _norm(p.get("speech")).strip()
    bad = not_speech(s) if s else None
    if bad:
        ctx.stripped = [(bad, s)]
        return (random.choice(SAFE_NOTHING) if action_ran else ASK_AGAIN), bad
    return _check_speech_s77(p, ctx, action_ran)

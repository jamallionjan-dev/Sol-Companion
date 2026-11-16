"""Questions about what Sol knows, answered from the Mind's own data. No model is involved."""
import math
import re

import gazetteer as GZ
import reply_gate as RG

_DIAC = re.compile(r"[ً-ٰٟ]")
HOW_MANY = ("كم", "قديش", "شقد", "عدد", "how many")
WHICH = ("شو", "ايش", "اي ", "عددي", "سمي", "احكيلي", "قوليلي", "خبريني", "وين", "بتعرفي", "تعرفي", "حافظ", "بتذكري", "what", "which", "list", "where")
STATIONS_PLURAL = ("الكازيات", "كازيات", "محطات", "المحطات", "stations")
PLACES = ("الاماكن", "اماكن", "محلات", "المحلات", "places")
STREETS = ("الشوارع", "شوارع", "طرقات", "الطرقات", "streets", "roads")
ONE_STREET = ("هالشارع", "هالطريق", "هاد الطريق", "هاد الشارع", "this road", "this street")
CARS = ("السيارات", "سيارات", "cars")
THE_CAR = ("وين السيارة", "وين السياره", "وين الفان", "وين سيارتنا", "وين سيارتك", "where is the car")
HOME = ("وين البيت", "وين بيتنا", "وين القاعدة", "وين القاعده", "where is home")
SELF = ("وينك", "وين انتي", "وين صرتي", "وين بتكوني", "where are you")
_COMPASS = ("بالشرق", "بالجنوب الشرقي", "بالجنوب", "بالجنوب الغربي", "بالغرب", "بالشمال الغربي", "بالشمال", "بالشمال الشرقي")
_BRAND_AR = {"gas2go": "غاز تو غو", "fossoil": "فوس أويل"}
_BRAND_OTHERS = {"gas2go": ("gas2go", "gas 2 go", "gas to go", "غاز 2 غو", "gas2go station"), "fossoil": ("fossoil", "foss oil")}
MAX_NAMED = 5
ONE_STATION = ("كازيه", "كازية", "محطه", "محطة", "البنزين", "gas station")
STREET_WORD = ("الشارع", "شارع", "street")
NAME_WORDS = ("اسم", "name", "شو هالكازيه", "شو هالكازية", "شو هاي الكازية", "شو هالشارع", "باي شارع", "على اي شارع")
HERE_REACH = 40
NOT_BEEN = "ما بعرف، ما رحت لهونيك."
REMEMBER_WORDS = ("تذكري", "بتذكري", "بتتذكري", "مرينا", "مرقنا", "شفنا", "زرنا")
TOWN_WORDS = ("المدينه", "المدينة", "مدينه", "مدينة", "البلده", "البلدة", "بلده", "بلدة", "الضيعه", "الضيعة", "ضيعه", "ضيعة", "city", "town")
THIS_BUILDING = ("هالمبنى", "هاد المبنى", "هادا المبنى", "هذا المبنى", "هذ المبنى", "هالبنايه", "هالبناية", "هاي البنايه", "هاي البناية", "هي البنايه", "هي البناية", "هالمحل", "هاد المحل", "هادا المحل", "هالفندق", "هاد الفندق", "هذا الفندق", "هالبيت", "هاد البيت", "this building", "this place", "this hotel")
NEAR_WORDS = ("قريب", "قريبه", "قريبة", "اقرب", "حوالينا", "هون", "nearby", "near", "close")
GO_WORDS = ("كيف بروح ع", "كيف اروح ع", "كيف نروح ع", "كيف بوصل ل", "كيف اوصل ل", "كيف بوصل ع", "وين بتكون ", "وين صارت ", "وين ", "how do i get to ", "where is ")
WHERE_WE_ARE = ("وين نحنا", "وين نحن", "وين احنا", "وين صرنا", "وين وصلنا", "where are we")


def norm(text):
    t = _DIAC.sub("", str(text or "").lower())
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
    return re.sub(r"\s+", " ", t).strip()


def _pos(d):
    if not isinstance(d, dict): return None
    p = d.get("position") if isinstance(d.get("position"), dict) else d
    try: return float(p["x"]), float(p["y"])
    except (KeyError, TypeError, ValueError): return None


def _where(frm, to):
    """About how far and which way, as she would say it. In this world y grows to the south."""
    dx, dy = to[0] - frm[0], to[1] - frm[1]
    dist = math.hypot(dx, dy)
    if dist < 8: return "جنبك"
    how = "قريب" if dist < 15 else "حوالي %d متر" % (int(round(dist / 10.0)) * 10)
    return "%s %s" % (how, _COMPASS[int(round(math.atan2(dy, dx) / (math.pi / 4))) % 8])


def _names(names):
    names = [n for n in names if n][:MAX_NAMED]
    if len(names) < 2: return names[0] if names else ""
    return "، ".join(names[:-1]) + " و" + names[-1]


def _plural(n, one, two, many):
    if n == 1: return one
    if n == 2: return two
    return "%d %s" % (n, many)


def parse_gardens(reason):
    """"gardens:x,y;..." -> [(x, y)]."""
    out = []
    for part in str(reason or "")[8:].split(";"):
        a = part.split(",")
        if len(a) == 2:
            try: out.append((int(a[0]), int(a[1])))
            except ValueError: pass
    return out


def parse_stations(reason):
    """"list:x,y,fuel,brand;..." -> [(x, y, fuel, brand)]."""
    out = []
    for part in str(reason or "")[5:].split(";"):
        a = part.split(",")
        if len(a) == 4:
            try: out.append((int(a[0]), int(a[1]), int(a[2]), a[3]))
            except ValueError: pass
    return out


def _town_name(t): return GZ.TOWN_AR.get(t["n"], t["n"])


_PREFIX = r"(?:و|ب|ل|ف|ع|ال|بال|لل|وال|هال)?"


def _word(n, w):
    """w as a word of its own, with the little Arabic prefixes allowed: never inside another word."""
    return re.search(r"(?<!\w)" + _PREFIX + re.escape(w) + r"(?!\w)", n) is not None


def _asks(text, n):
    if RG.is_question(text) or any(w in n for w in REMEMBER_WORDS): return True
    bare = re.sub(r"^(?:سول|يا سول)\s+", "", n)
    return bare.startswith("في ") and any(_word(n, w) for w in NEAR_WORDS)


def _place_of(gaz, x, y):
    t, s = gaz.town_at(x, y), gaz.street_near(x, y)
    bits = []
    if s: bits.append("على %s" % s)
    if t is not None: bits.append("بـ%s" % _town_name(t))
    return (" " + " ".join(bits)) if bits else ""


def _place_answer(n, snap, mem, gaz, where, gardens=None):
    """Towns and buildings. where is the point the question is about."""
    if gaz is None or where is None: return None
    x, y = where
    towny = any(_word(n, w) for w in TOWN_WORDS)
    if towny and any(w in n for w in ("اقرب", "nearest", "closest")):
        known = [t for t in gaz.towns if GZ.visited(mem, t["x"], t["y"], GZ.TOWN_REACH)]
        if not known: return NOT_BEEN
        return "أقرب وحدة بعرفها %s." % _town_name(min(known, key=lambda t: math.hypot(t["x"] - x, t["y"] - y)))
    if towny and "وين" not in n and "where" not in n and ("اسم" in n or "شو" in n or "name" in n or "what" in n):
        t = gaz.town_at(x, y)
        return "هاي %s." % _town_name(t) if t is not None else "نحنا برا البلدات."
    if any(w in n for w in THIS_BUILDING):
        if not GZ.visited(mem, x, y): return NOT_BEEN
        b = gaz.building_at(x, y)
        if b is None: return "ما في بناية هون."
        return "هاد %s، اسمه %s." % (b["label"], b["name"]) if b["name"] else "هاد %s." % b["label"]
    kind = next((k for k, words in GZ.KIND_WORDS if any(_word(n, w) for w in words)), None)
    if kind is not None and (any(_word(n, w) for w in NEAR_WORDS) or n.startswith("في ") or " في " in n or "وين" in n or any(w in n for w in REMEMBER_WORDS)):
        b = gaz.nearest_kind(kind, x, y, lambda cx, cy: GZ.visited(mem, cx, cy))
        remembering = any(w in n for w in REMEMBER_WORDS)
        if kind == "farm":
            seen = gardens() if gardens else None
            if seen:
                gx, gy = min(seen, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
                if b is None or math.hypot(gx - x, gy - y) < math.hypot(b["x"] - x, b["y"] - y): b = {"label": "حديقة زراعية", "name": None, "x": gx, "y": gy}
        if b is None: return "لا، ما بتذكر إننا مرقنا من جنب شي متل هيك." if remembering else NOT_BEEN
        named = "%s %s" % (b["label"], b["name"]) if b["name"] else b["label"]
        return "%s %s%s، %s منك." % ("إيه، مرقنا من جنب" if remembering else "في", named, _place_of(gaz, b["x"], b["y"]), _where(where, (b["x"], b["y"])))
    for go in GO_WORDS:
        at = n.find(go)
        if at < 0: continue
        rest = re.sub(r"^(?:ـ|ال)?\s*", "", n[at + len(go):]).strip(" .؟?")
        rest = re.sub(r"^(?:مدينه|مدينة|بلده|بلدة|ضيعه|ضيعة)\s+", "", rest)
        if not rest: return None
        right = RG.match_name(rest, [(p[0], p[1]) for p in gaz.places()])
        if right is not None:
            p = next(q for q in gaz.places() if q[0] == right)
            if not GZ.visited(mem, p[2], p[3], p[4]): return NOT_BEEN
            return "%s %s منك." % (right, _where(where, (p[2], p[3])))
        known = snap.get("knownStreets") or []
        street = RG.match_name(rest, [(s, ()) for s in known])
        if street is not None:
            q = gaz.street_point(street, x, y)
            if q: return "%s %s منك." % (street, _where(where, tuple(q)))
        return None
    return None


def answer(text, snap, mem, stations=None, street_now=None, gaz=None, gardens=None):
    """The Mind's own answer, or None when this isn't a question about what she knows."""
    n = norm(text)
    if not n: return None
    snap = snap or {}
    me = _pos(snap.get("player"))
    her = _pos(snap.get("sol"))
    how_many = any(w in n for w in HOW_MANY)
    which = any(w in n for w in WHICH)

    asks_name = any(w in n for w in NAME_WORDS)
    where_we_are = any(w in n for w in WHERE_WE_ARE)
    if where_we_are or (asks_name and any(w in n for w in STREET_WORD)):
        live = street_now() if street_now else None
        if live: snap = dict(snap, currentStreet=live)
    if where_we_are:
        cur = snap.get("currentStreet")
        town = gaz.town_at(*(me or her)) if gaz is not None and (me or her) else None
        line = "نحنا على %s." % cur if cur else "مو عارفة اسم هالمطرح."
        if town is not None: line = "نحنا على %s بـ%s." % (cur, _town_name(town)) if cur else "نحنا بـ%s." % _town_name(town)
        got = stations() if stations else None
        if got and me:
            x, y, fuel, brand = min(got, key=lambda s: (s[0] - me[0]) ** 2 + (s[1] - me[1]) ** 2)
            if math.hypot(x - me[0], y - me[1]) <= HERE_REACH and brand in _BRAND_AR: line += " وهاي كازية %s حدّنا." % _BRAND_AR[brand]
        return line
    if asks_name and not how_many and not any(w in n for w in STATIONS_PLURAL) and (any(w in n for w in ONE_STATION) or any(w in n for w in STREET_WORD)):
        parts = []
        if any(w in n for w in STREET_WORD):
            cur = snap.get("currentStreet")
            parts.append("هاد %s." % cur if cur else "اسم الشارع ما بعرفه.")
        if any(w in n for w in ONE_STATION):
            got = stations() if stations else None
            here = None
            if got and me:
                x, y, fuel, brand = min(got, key=lambda s: (s[0] - me[0]) ** 2 + (s[1] - me[1]) ** 2)
                if math.hypot(x - me[0], y - me[1]) <= HERE_REACH: here = brand
            if here is None: parts.append("ما بعرف كازية هون.")
            else: parts.append("هاي كازية %s." % _BRAND_AR[here] if here in _BRAND_AR else "هاي كازية، اسمها مو مكتوب.")
        return " ".join(parts)

    said = _place_answer(n, snap, mem, gaz, me or her, gardens) if _asks(text, n) and not any(w in n for w in SELF + HOME + THE_CAR) else None
    if said: return said

    if any(w in n for w in STATIONS_PLURAL) and (how_many or which):
        got = stations() if stations else None
        if got is None: return None
        if not got: return "لسا ما بعرف ولا كازية."
        head = "بعرف " + _plural(len(got), "كازية وحدة", "كازيتين", "كازيات")
        if me is None: return head + "."
        parts = []
        for x, y, fuel, brand in got[:MAX_NAMED]:
            parts.append("%s %s" % (_BRAND_AR.get(brand, "وحدة"), _where(me, (x, y))))
        return head + ": " + "، ".join(parts) + "."

    if any(w in n for w in PLACES) and (how_many or which):
        places = (mem.data.get("places") if mem is not None else None) or []
        if not places: return "لسا ما حفظت ولا مكان."
        head = "حافظة " + _plural(len(places), "مكان واحد", "مكانين", "اماكن")
        return "%s: %s." % (head, _names([p.get("name") for p in reversed(places)]))

    street_names = snap.get("knownStreets") or []
    if any(w in n for w in ONE_STREET) and any(w in n for w in ("بتعرفي", "تعرفي", "شو اسم", "اسم", "know")):
        cur = snap.get("currentStreet")
        if cur: return "إيه، هاد %s." % cur if cur in street_names else "هاد %s، أول مرة بمرق منه." % cur
        return "ما بعرف اسمه."
    if any(w in n for w in STREETS) and (how_many or which):
        if not street_names: return "لسا ما حفظت ولا شارع."
        head = "بعرف " + _plural(len(street_names), "شارع واحد", "شارعين", "شوارع")
        return "%s، منها %s." % (head, _names(street_names)) if len(street_names) > 1 else "%s: %s." % (head, street_names[0])

    if any(w in n for w in SELF):
        if her is None: return "مو عارفة وين أنا هلأ."
        return "أنا %s منك." % _where(me, her) if me else "أنا هون."

    if any(w in n for w in HOME):
        h = (mem.data.get("home") if mem is not None else None) or snap.get("solHome")
        if not h: return "لسا ما عنا بيت محدد."
        p = _pos(h)
        return "البيت %s منك." % _where(me, p) if me and p else "البيت محفوظ عندي."

    cars = snap.get("vehicles") or []
    if any(w in n for w in CARS) and (how_many or which):
        if not cars: return "ما شايفة ولا سيارة حوالينا."
        head = "شايفة " + _plural(len(cars), "سيارة وحدة", "سيارتين", "سيارات")
        if not me: return head + "."
        nearest = min(cars, key=lambda v: (v.get("x", 0) - me[0]) ** 2 + (v.get("y", 0) - me[1]) ** 2)
        return "%s حوالينا، أقربها %s." % (head, _where(me, (nearest.get("x", 0), nearest.get("y", 0))))
    if any(w in n for w in THE_CAR):
        if not cars or not me: return "ما شايفة السيارة من هون."
        nearest = min(cars, key=lambda v: (v.get("x", 0) - me[0]) ** 2 + (v.get("y", 0) - me[1]) ** 2)
        return "السيارة %s منك." % _where(me, (nearest.get("x", 0), nearest.get("y", 0)))
    return None


def known_names(snap, mem, got=None, gaz=None):
    """[(the right name, other spellings)] for everything she can name right now."""
    snap = snap or {}
    names = list(snap.get("knownStreets") or [])
    if snap.get("currentStreet"): names.append(snap["currentStreet"])
    names += [p.get("name") for p in ((mem.data.get("places") if mem is not None else None) or [])]
    out = [(n, ()) for n in sorted({str(n) for n in names if n})]
    for brand in sorted({s[3] for s in got or () if s[3] in _BRAND_AR}): out.append((_BRAND_AR[brand], _BRAND_OTHERS[brand]))
    if gaz is not None:
        for name, others, x, y, reach in gaz.places():
            if GZ.visited(mem, x, y, reach): out.append((name, tuple(others)))
    return out


def facts(snap, mem, got=None, gaz=None):
    """What she knows, for a model that is asked something the Mind can't answer: so it doesn't deny what is true."""
    snap = snap or {}
    bits = []
    places = (mem.data.get("places") if mem is not None else None) or []
    if places: bits.append("أماكن محفوظة: " + "، ".join(str(p.get("name")) for p in places[-12:]))
    streets = snap.get("knownStreets") or []
    if streets: bits.append("شوارع تعرفينها: " + "، ".join(streets[:20]))
    if snap.get("currentStreet"): bits.append("الشارع الحالي: " + str(snap["currentStreet"]))
    me = _pos(snap.get("player"))
    if got and me:
        near = sorted(got, key=lambda s: (s[0] - me[0]) ** 2 + (s[1] - me[1]) ** 2)[:3]
        bits.append("أقرب الكازيات: " + "، ".join("%s %s" % (_BRAND_AR.get(s[3], "كازية بلا اسم"), _where(me, (s[0], s[1]))) for s in near))
    where = me or _pos(snap.get("sol"))
    if gaz is not None and where:
        t = gaz.town_at(*where)
        if t is not None: bits.append("البلدة: " + _town_name(t))
        seen = [p for p in gaz.places() if GZ.visited(mem, p[2], p[3], p[4])]
        if seen:
            seen.sort(key=lambda p: math.hypot(p[2] - where[0], p[3] - where[1]))
            bits.append("أماكن رحتِ عليها: " + "، ".join("%s %s" % (p[0], _where(where, (p[2], p[3]))) for p in seen[:6]))
    return "\n".join(bits)


LOST_MEMORY_LINES = ("راسي فاضي... مو متذكرة وين كنا.", "رجعت، بس كل الأماكن راحت من راسي.", "مو عم بتذكر الطرق اللي مرقنا منها.")


# ---------------------------------------------------------------- s82 engine words, place questions, compact card
# "بأي ضيعة نحنا" / "بأي مدينة نحنا": the town question, said without "اسم" and without "?".
import re as _re_s82
_TOWN_WHICH_S82 = _re_s82.compile(r"(?:^|\s)(?:ب|ع|على\s*|في\s*)?اي\s+(?:ضيعه|ضيعة|مدينه|مدينة|بلده|بلدة)(?:\s|$)")
_answer_s81 = answer


def answer(text, snap, mem, stations=None, street_now=None, gaz=None, gardens=None):
    said = _answer_s81(text, snap, mem, stations, street_now, gaz, gardens)
    if said is None and _TOWN_WHICH_S82.search(norm(text) or ""):
        said = _answer_s81("شو اسم هي المدينة", snap, mem, stations, street_now, gaz, gardens)
    return said


# ---------------------------------------------------------------- s86 book_memory: her address book in her memory
# The game writes a compact copy of her address book into the snapshot ("solBook", apply_s86_book_memory_lua.py): rows
# { g: group, n: name, c: town, st: home's street, ls: rental, lt: looted, d: tiles, dir: 1..8 = N..NW }, "from": sol | player.
# Her memory line for the card, and the answers to "شو في عنا عناوين" / "وين <name>" from it. No coordinates anywhere.
BOOK_ENABLED = [True]                                                          # chat_service sets it from the switch book_memory
BOOK_MAX = 8
BOOK_GROUP_AR = {"home": "بيتنا", "house": "بيت للبيع", "tourist": "مكان سياحي", "shop": "محل", "public": "خدمات", "stash": "مخبأ", "area": "منطقة"}
BOOK_LEASE_AR = "للإيجار"
BOOK_DIR_AR = ("بالشمال", "بالشمال الشرقي", "بالشرق", "بالجنوب الشرقي", "بالجنوب", "بالجنوب الغربي", "بالغرب", "بالشمال الغربي")
BOOK_LIST_WORDS = ("عناوين", "دفتر", "addresses", "address book")
BOOK_EMPTY = "دفتري فاضي، لسا ما شفت معك ولا ورقة فيها عنوان."
BOOK_NOT_ASKED = SELF + HOME + THE_CAR + WHERE_WE_ARE


def book_rows(snap):
    """The book's rows from the snapshot, or None when the game sent none (switch off, older game files)."""
    if not BOOK_ENABLED[0]: return None
    b = (snap or {}).get("solBook")
    if not isinstance(b, dict) or not isinstance(b.get("rows"), list): return None
    return [r for r in b["rows"] if isinstance(r, dict) and r.get("g") in BOOK_GROUP_AR]


def _book_total(snap, rows):
    n = (snap.get("solBook") or {}).get("n")
    return n if isinstance(n, int) and n >= len(rows) else len(rows)


def book_name(r):
    g, n = r.get("g"), str(r.get("n") or "").strip()
    if g == "home": return "بيتنا"
    if g in ("stash", "area"): return BOOK_GROUP_AR[g] + ((" " + n) if n else "")
    return n or BOOK_GROUP_AR[g]


def book_kind(r):
    g, c = r.get("g"), str(r.get("c") or "").strip()
    if g == "home": return str(r.get("st") or "").strip() or None
    k = (BOOK_LEASE_AR if r.get("ls") else BOOK_GROUP_AR[g]) if g == "house" else (None if g in ("stash", "area") else BOOK_GROUP_AR[g])
    if c and c not in book_name(r): k = (k + "، " + c) if k else c
    return k


def book_where(r):
    """Distance and direction in words ("حوالي 1.2 كم بالشمال"), None when the game sent no distance."""
    d = r.get("d")
    if not isinstance(d, (int, float)) or isinstance(d, bool): return None
    if d < 15: return "قريب"
    if d < 1000: how = "حوالي %d متر" % (int(round(d / 10.0)) * 10)
    else:
        km = round(d / 1000.0, 1)
        how = "حوالي %s كم" % (("%d" % km) if km == int(km) else ("%.1f" % km))
    k = r.get("dir")
    if isinstance(k, int) and not isinstance(k, bool) and 1 <= k <= 8: how += " " + BOOK_DIR_AR[k - 1]
    return how


def book_sig(snap):
    """What changes the card's memory: the names and the looted marks, not the distances."""
    rows = book_rows(snap)
    if rows is None: return None
    return (_book_total(snap, rows),) + tuple((r.get("g"), r.get("n"), bool(r.get("lt"))) for r in rows[:BOOK_MAX])


def book_line(snap, most=BOOK_MAX):
    """Her memory line for the card: بيتنا first, at most `most` entries, distances in words; None without the book."""
    rows = book_rows(snap)
    if rows is None: return None
    if not rows: return "دفتر عناوينك فاضي."
    bits = []
    for r in rows[:most]:
        info = [x for x in (book_kind(r), book_where(r), "انزار" if r.get("lt") else None) if x]
        bits.append(book_name(r) + ((" (" + "، ".join(info) + ")") if info else ""))
    who = "منك" if (snap.get("solBook") or {}).get("from") == "sol" else "منه"
    line = "دفتر عناوينك (البعد %s): %s" % (who, "؛ ".join(bits))
    total = _book_total(snap, rows)
    if total > len(bits): line += "؛ و%d غيرهن" % (total - len(bits))
    return line + "."


def book_list(snap):
    rows = book_rows(snap)
    if rows is None: return None
    if not rows: return BOOK_EMPTY
    total = _book_total(snap, rows)
    names = [book_name(r) + (" (انزار)" if r.get("lt") else "") for r in rows[:MAX_NAMED]]
    line = "بالدفتر عندي %s: %s" % (_plural(total, "عنوان واحد", "عنوانين", "عناوين"), "، ".join(names))
    return line + ("، وغيرهن." if total > len(names) else ".")


def _book_aliases(r):
    name = str(r.get("n") or "").strip()
    out = []
    head = name.split(",")[0].strip()                                          # "625 Dewey Street, Muldraugh" -> "625 Dewey Street"
    bare = re.sub(r"^\d+\s+", "", head).strip()                               #                               -> "Dewey Street"
    plain = re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()                      # "E.P. Tools (Louisville)" -> "E.P. Tools"
    for a in (name, head, bare, plain):
        if a and a != book_name(r) and a not in out: out.append(a)
    return tuple(out)


def _book_words(s): return re.findall(r"[a-z0-9]+", str(s or "").lower())


def book_find(rest, rows):
    """The book's rows this spelling names (one, several, or none). Our home is the home question's."""
    cands = [r for r in rows if r.get("g") != "home"]
    if not rest or not cands: return []
    right = RG.match_name(rest, [(book_name(r), _book_aliases(r)) for r in cands])
    hits = [r for r in cands if book_name(r) == right] if right is not None else []
    if not hits:
        toks = [t for t in _book_words(rest) if len(t) >= 3]
        if toks: hits = [r for r in cands if all(t in _book_words(str(r.get("n") or "") + " " + str(r.get("c") or "")) for t in toks)]
    return hits


def book_answer(text, snap):
    """"شو في عنا عناوين" / "وين <name>" from her book; None when the question is not about it (or the game sent no book)."""
    rows = book_rows(snap)
    if rows is None: return None
    n = norm(text)
    if not n: return None
    if any(w in n for w in BOOK_LIST_WORDS) and (any(w in n for w in HOW_MANY) or any(w in n for w in WHICH) or _word(n, "عنا") or RG.is_question(text)):
        return book_list(snap)
    if any(w in n for w in BOOK_NOT_ASKED): return None
    who = "منّي" if (snap.get("solBook") or {}).get("from") == "sol" else "منك"
    for go in GO_WORDS:
        at = n.find(go)
        if at < 0: continue
        rest = re.sub(r"^(?:ـ|ال)\s*", "", n[at + len(go):]).strip(" .؟?!")
        rest = re.sub(r"\s+(?:من\s*هون|منا|مننا|منك|مني)$", "", rest).strip(" .؟?!")
        hits = book_find(rest, rows)
        if not hits: return None
        if len(hits) > 1: return "عندي بالدفتر أكتر من وحدة: %s. أيا وحدة؟" % "، ".join(book_name(r) for r in hits[:4])
        r = hits[0]
        kind, where = book_kind(r), book_where(r)
        name = book_name(r) + ((" (%s)" % kind) if kind else "")
        if where is None: line = "%s عندي بالدفتر، بس ما بعرف قديش بعيد هلأ." % name
        else: line = "%s %s %s." % (name, where, who)
        return line[:-1] + "، وانزار." if r.get("lt") else line
    return None


_answer_s85 = answer
NO_PLACES = "لسا ما حفظت ولا مكان."


def answer(text, snap, mem, stations=None, street_now=None, gaz=None, gardens=None):
    said = book_answer(text, snap)
    if said: return said
    said = _answer_s85(text, snap, mem, stations, street_now, gaz, gardens)
    if said == NO_PLACES and book_rows(snap): said = book_list(snap)
    return said


_known_names_s85 = known_names


def known_names(snap, mem, got=None, gaz=None):
    out = _known_names_s85(snap, mem, got, gaz)
    for r in book_rows(snap) or []:
        if r.get("g") != "home": out.append((book_name(r), _book_aliases(r)))
    return out


_facts_s85 = facts


def facts(snap, mem, got=None, gaz=None):
    text = _facts_s85(snap, mem, got, gaz)
    line = book_line(snap)
    return (text + "\n" + line).strip() if line else text

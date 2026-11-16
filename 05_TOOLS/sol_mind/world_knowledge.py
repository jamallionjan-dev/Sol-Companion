"""Sol's world knowledge: reads SolWorld_Snapshot.txt (written by the game), keeps one memory per save
(created on first sight, deleted when the save folder is deleted), computes stock and needs from what the
game reports, and offers tools to the brain (find items, remember/recall places, set home)."""
import json, math, os, re, shutil, time

SNAP = "SolWorld_Snapshot.txt"
MEM_VERSION = 1

def _root():
    r = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
    d = os.path.join(r, "SolMind", "worlds"); os.makedirs(d, exist_ok=True); return d

def world_key(world):
    name = str((world or {}).get("name") or "unknown"); mode = str((world or {}).get("mode") or "Sandbox")
    return re.sub(r"[^A-Za-z0-9_.-]", "_", mode + "__" + name)

def save_folder(world, zomboid_dir=None):
    zd = zomboid_dir or os.path.join(os.environ.get("USERPROFILE") or os.path.expanduser("~"), "Zomboid")
    return os.path.join(zd, "Saves", str((world or {}).get("mode") or "Sandbox"), str((world or {}).get("name") or ""))

def cleanup_deleted_worlds(zomboid_dir=None, log=print):
    """Delete the memory of every world whose save folder no longer exists."""
    removed = []
    for key in os.listdir(_root()):
        meta = os.path.join(_root(), key, "memory.json")
        try:
            with open(meta, encoding="utf-8") as f: w = json.load(f).get("world") or {}
        except (OSError, ValueError): continue
        try:
            with open(meta, encoding="utf-8") as f: verified = json.load(f).get("save_verified")
        except (OSError, ValueError): verified = False
        # only memories whose save folder was seen once are eligible: a wrong path never wipes a memory
        if verified and w.get("name") and not os.path.isdir(save_folder(w, zomboid_dir)):
            shutil.rmtree(os.path.join(_root(), key), ignore_errors=True); removed.append(key)
            log("world memory removed (save deleted): %s" % key)
    return removed

class Memory:
    def __init__(self, world):
        self.world = world; self.key = world_key(world)
        self.dir = os.path.join(_root(), self.key); os.makedirs(self.dir, exist_ok=True)
        self.path = os.path.join(self.dir, "memory.json")
        try:
            with open(self.path, encoding="utf-8") as f: self.data = json.load(f)
        except (OSError, ValueError):
            self.data = {"version": MEM_VERSION, "world": world, "created": time.time(), "home": None, "places": [], "notes": [], "hunger_log": []}
            self.save()
        if not self.data.get("save_verified") and os.path.isdir(save_folder(world)):
            self.data["save_verified"] = True; self.save()
    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f: json.dump(self.data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

def load_snapshot(lua_dir):
    try:
        with open(os.path.join(lua_dir, SNAP), encoding="ascii", errors="replace") as f: return json.loads(f.read())
    except (OSError, ValueError): return None

# ---------------------------------------------------------------- stock and needs (from game data only)
def _inv(snap):
    inv = snap.get("baseInventory") if isinstance(snap, dict) else None
    return inv if isinstance(inv, dict) and isinstance(inv.get("rows"), list) else None

def _inv_containers(snap):
    """Containers rebuilt from the base inventory the game scanned (SolInventory): one per place, exact counts."""
    inv = _inv(snap)
    if not inv: return []
    groups = {}
    for r in inv["rows"]:
        if not isinstance(r, dict): continue
        w, room = r.get("w"), r.get("room")
        key = (w, room if w in ("house", "vehicle") else None)
        c = groups.get(key)
        if c is None:
            c = {"where": "square" if w == "house" else w, "room": room if w == "house" else None,
                 "vehicle": room if w == "vehicle" else None, "part": "container", "synthetic": True,
                 "items": [], "foods": [], "fluids": []}
            groups[key] = c
        e = {"type": r.get("t"), "name": r.get("n"), "cat": r.get("c"), "count": r.get("k") or 1}
        g = r.get("g")
        if g == "food":
            e["food"] = {"hunger": -(r.get("hun") or 0.0), "calories": r.get("cal"), "rotten": bool(r.get("rot"))}
            if r.get("dl") is not None: e["food"].update({"age": 0.0, "offAge": 0.0, "offAgeMax": max(float(r["dl"]), 0.1)})
            c["foods"].append(e)
        elif g in ("water", "fuel"):
            kind = ("TaintedWater" if r.get("bad") else "Water") if g == "water" else "Petrol"
            e["fluid"] = {"kind": kind, "liters": r.get("l") or 0, "poison": bool(r.get("bad"))}
            c["fluids"].append(e)
        else:
            c["items"].append(e)
    return list(groups.values())

def _containers(snap): return (snap.get("containers") or []) + _inv_containers(snap)
def _place_label(c):
    w = c.get("where")
    if w == "player": return "your bag"
    if w == "sol": return "Sol's bag"
    if w == "vehicle": return "%s (%s)" % (c.get("vehicle"), c.get("part"))
    if c.get("synthetic"): return str(c.get("room") or "house")
    return "%s at %s,%s" % (c.get("room") or c.get("object") or "container", c.get("x"), c.get("y"))

def food_report(snap):
    edible, spoiling, rotten = [], [], []
    for c in _containers(snap):
        for f in c.get("foods") or []:
            fd = f.get("food") or {}
            if fd.get("rotten"): rotten.append((f.get("name"), _place_label(c))); continue
            hunger = -(fd.get("hunger") or 0)
            if hunger <= 0: continue
            days_left = None
            if fd.get("offAge") is not None and fd.get("age") is not None and fd.get("offAgeMax") not in (None, 0) and fd["offAgeMax"] < 1e6:
                days_left = round(max(0.0, fd["offAgeMax"] - fd["age"]), 1)
            edible.append({"name": f.get("name"), "where": _place_label(c), "hunger": round(hunger, 3), "calories": fd.get("calories"), "rot_in_days": days_left})
            if days_left is not None and days_left <= 2: spoiling.append((f.get("name"), days_left, _place_label(c)))
    total_hunger = round(sum(e["hunger"] for e in edible), 2)
    cal = [e["calories"] for e in edible if e["calories"] is not None]
    return {"items": len(edible), "hunger_points": total_hunger, "calories": round(sum(cal)) if cal else None,
            "spoiling_soon": spoiling[:12], "rotten": rotten[:12]}

_food_report_core = food_report
def food_report(snap):
    r = _food_report_core(snap)
    extra = 0          # a base-inventory row counts every item it holds, not one
    for c in _containers(snap):
        if c.get("synthetic"):
            for f in c.get("foods") or []:
                fd = f.get("food") or {}
                if not fd.get("rotten") and -(fd.get("hunger") or 0) > 0: extra += max(0, int(f.get("count") or 1) - 1)
    if extra: r["items"] = r["items"] + extra
    return r

def water_report(snap):
    clean, tainted = 0.0, 0.0
    for c in _containers(snap):
        for f in c.get("fluids") or []:
            fl = f.get("fluid") or {}
            kind = str(fl.get("kind") or "")
            liters = fl.get("liters") or 0
            if "Water" not in kind and "water" not in kind: continue
            if fl.get("poison") or "Tainted" in kind: tainted += liters
            else: clean += liters
    t = snap.get("time") or {}; u = snap.get("utilities") or {}
    day = t.get("day")
    sources = []
    for source in (snap.get("waterSources") or []):
        if not isinstance(source, dict): continue
        sources.append({
            "kind": str(source.get("kind") or "water_source"),
            "name": str(source.get("name") or "مصدر ماء"),
            "amount": source.get("amount") if isinstance(source.get("amount"), (int, float)) else None,
            "tainted": source.get("tainted") if isinstance(source.get("tainted"), bool) else None,
            "x": source.get("x"), "y": source.get("y"), "z": source.get("z"),
        })
    out = {"clean_liters": round(clean, 2), "tainted_liters": round(tainted, 2), "sources": sources}
    for k, label in (("waterShutDay", "water_off_in_days"), ("elecShutDay", "power_off_in_days")):
        v = u.get(k)
        if isinstance(v, (int, float)) and v > -1 and day is not None: out[label] = round(v - day, 1)
    return out

def hunger_rate(mem, snap):
    """Measured from the game: player HUNGER stat over time (only rises between meals). Returns hunger/day or None."""
    p = (snap.get("player") or {}).get("stats") or {}
    h = p.get("HUNGER"); t = (snap.get("time") or {}).get("ageHours")
    if h is None or t is None: return None
    log = mem.data.setdefault("hunger_log", [])
    if not log or abs(log[-1][0] - t) > 0.05: log.append([t, h]); del log[:-200]
    rates = [(b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(log, log[1:]) if b[0] - a[0] >= 0.5 and b[1] > a[1]]
    if len(rates) < 2: return None
    rates.sort(); return round(rates[len(rates) // 2] * 24, 3)

def needs(snap, mem=None):
    """Urgent needs from the game's own moodles and stats + stock facts."""
    out = []
    for who, key in (("player", "player"), ("Sol", "sol")):
        s = snap.get(key) or {}
        m = s.get("moodles") or {}; st = s.get("stats") or {}
        if m.get("HYPOTHERMIA"): out.append({"who": who, "need": "warmth", "level": m["HYPOTHERMIA"], "why": "hypothermia moodle %s, air %s C" % (m["HYPOTHERMIA"], s.get("temperatureAir"))})
        if m.get("HYPERTHERMIA"): out.append({"who": who, "need": "cool_down", "level": m["HYPERTHERMIA"], "why": "hyperthermia moodle %s" % m["HYPERTHERMIA"]})
        # the game's own moodles first (level 1-4); raw stat only when the moodle is not exposed
        if m.get("HUNGRY"): out.append({"who": who, "need": "eat", "level": m["HUNGRY"], "why": "hungry moodle %s" % m["HUNGRY"]})
        elif "HUNGRY" not in m and (st.get("HUNGER") or 0) >= 0.25: out.append({"who": who, "need": "eat", "level": st["HUNGER"], "why": "hunger stat %.2f" % st["HUNGER"]})
        if m.get("THIRST"): out.append({"who": who, "need": "drink", "level": m["THIRST"], "why": "thirst moodle %s" % m["THIRST"]})
        elif "THIRST" not in m and (st.get("THIRST") or 0) >= 0.25: out.append({"who": who, "need": "drink", "level": st["THIRST"], "why": "thirst stat %.2f" % st["THIRST"]})
        if (st.get("WETNESS") or 0) >= 25: out.append({"who": who, "need": "dry_clothes", "level": st["WETNESS"], "why": "wetness %s" % st["WETNESS"]})
        if m.get("TIRED", 0) >= 2: out.append({"who": who, "need": "sleep", "level": m["TIRED"], "why": "tired moodle %s" % m["TIRED"]})
        for w in s.get("wounds") or []:
            if "bleeding" in w.get("state", []) and "bandaged" not in w.get("state", []):
                out.append({"who": who, "need": "bandage", "level": 3, "why": "bleeding %s" % w.get("part")})
    f = food_report(snap); wr = water_report(snap)
    if f["spoiling_soon"]: out.append({"who": "stock", "need": "eat_first", "level": 1, "why": "spoils within 2 days: " + ", ".join("%s (%s d)" % (n, d) for n, d, _ in f["spoiling_soon"][:5])})
    if wr.get("water_off_in_days") is not None and 0 <= wr["water_off_in_days"] <= 3: out.append({"who": "stock", "need": "store_water", "level": 2, "why": "tap water stops in %s days" % wr["water_off_in_days"]})
    return out

def _words(s): return [w for w in re.split(r"[^a-z0-9]+", str(s or "").lower()) if w]
def _stem(w): return w[:-1] if len(w) > 3 and w.endswith("s") else w
def find_items(snap, query):
    """Semantic-ish search: 'nails' matches Base.Nails / 'Nails', not 'Fashion Nails - Blood Red' (nail polish) when real
    nails exist. Score: exact type > all query words as whole words in the name/type > category."""
    qw = [_stem(w) for w in _words(query)]
    if not qw: return []
    scored = []
    for c in _containers(snap):
        for group in ("items", "foods", "fluids"):
            for it in c.get(group) or []:
                tname = str(it.get("type", "")).split(".")[-1]
                tw = [_stem(w) for w in _words(re.sub(r"(?<=[a-z])(?=[A-Z])", " ", tname))]
                nw = [_stem(w) for w in _words(it.get("name"))]
                cw = [_stem(w) for w in _words(it.get("cat"))]
                if tw == qw or [_stem(w) for w in _words(tname)] == qw: score = 3
                elif all(w in nw or w in tw for w in qw) and len(nw) <= len(qw) + 1: score = 2
                elif all(w in nw or w in tw for w in qw): score = 1
                elif all(w in cw for w in qw): score = 0.5
                else: continue
                scored.append((score, {"name": it.get("name"), "count": it.get("count", 1), "where": _place_label(c)}))
    if not scored: return []
    best = max(sc for sc, _ in scored)
    keep = [r for sc, r in scored if sc >= min(best, 2)] if best >= 2 else [r for sc, r in scored if sc == best]
    return keep[:40]

SUPPLY_GROUPS = [
    ("طعام", lambda it, g: g == "foods"), ("ماء نظيف (لتر)", None), ("ذخيرة", lambda it, g: "Ammo" in str(it.get("cat")) or "Bullets" in str(it.get("type")) or "Shells" in str(it.get("type"))),
    ("مسامير", lambda it, g: str(it.get("type")).split(".")[-1] in ("Nails",)), ("ألواح خشب", lambda it, g: str(it.get("type")).split(".")[-1] in ("Plank", "Log")),
    ("ضمادات", lambda it, g: "Bandage" in str(it.get("type")) or "RippedSheets" in str(it.get("type"))),
    ("بذور", lambda it, g: "Seed" in str(it.get("type"))), ("سماد", lambda it, g: "Fertilizer" in str(it.get("type")) or "Compost" in str(it.get("type"))),
    ("وقود", lambda it, g: "Petrol" in str(it.get("type")) or "Gas" in str(it.get("type"))),
]
_SUPPLY_CATEGORIES = {
    "Food": "طعام", "Cooking": "طبخ", "CookingWeapon": "أدوات مطبخ",
    "Gardening": "زراعة", "GardeningWeapon": "أدوات زراعة", "Tool": "أدوات",
    "ToolWeapon": "أدوات", "Weapon": "أسلحة", "WeaponCrafted": "أسلحة",
    "JunkWeapon": "أدوات", "MaterialWeapon": "مواد وأدوات", "Material": "مواد",
    "Ammo": "ذخيرة", "FirstAid": "إسعافات", "Medical": "إسعافات",
    "WaterContainer": "حاويات ماء", "VehicleMaintenance": "صيانة مركبات",
    "Electronics": "إلكترونيات", "SkillBook": "كتب مهارات", "RecipeResource": "كتب ووصفات",
    "Literature": "كتب", "Clothing": "ملابس", "ProtectiveGear": "معدات حماية",
    "Bag": "حقائب", "Container": "حاويات", "Accessory": "إكسسوارات",
    "Household": "أغراض منزلية", "HouseholdWeapon": "أدوات منزلية", "Furniture": "أثاث",
    "Camping": "تخييم", "Security": "مفاتيح وأمان", "Trapping": "صيد",
    "Fishing": "صيد السمك", "Cartography": "خرائط", "Paint": "دهان",
    "Appearance": "عناية شخصية", "Memento": "تذكارات", "Entertainment": "ترفيه",
    "Communications": "اتصالات", "FireSource": "مصادر إشعال", "LightSource": "إضاءة",
}
_SUPPLY_CATEGORY_ORDER = (
    "طعام", "مشروبات", "ماء", "زراعة", "أدوات زراعة", "أدوات", "طبخ",
    "مواد وأدوات", "مواد", "ذخيرة", "أسلحة", "إسعافات", "صيانة مركبات",
    "حاويات ماء", "حقائب", "ملابس", "معدات حماية", "كتب مهارات", "كتب ووصفات",
    "كتب", "إلكترونيات", "اتصالات", "أغراض منزلية", "أدوات منزلية", "أثاث",
    "تخييم", "مصادر إشعال", "إضاءة", "صيد", "خرائط", "تذكارات", "ترفيه", "أخرى",
)

def _supply_place(c):
    where = c.get("where")
    if where == "player": return "حقيبة اللاعب"
    if where == "sol": return "حقيبة سول"
    if where == "vehicle": return "المركبة"
    room = str(c.get("room") or c.get("kind") or c.get("part") or "")
    rooms = {
        "kitchen": "المطبخ", "bedroom": "غرفة النوم", "bathroom": "الحمام",
        "hall": "الصالة", "livingroom": "غرفة المعيشة", "closet": "الخزانة",
        "garagestorage": "مخزن الكراج", "garage": "الكراج",
        "trunk": "صندوق السيارة", "truckbed": "صندوق السيارة", "glovebox": "درج السيارة",
        "container": "مخزن", "metal_shelves": "رفوف معدنية", "counter": "سطح المطبخ",
        "stove": "الموقد", "bin": "سلة", "dishwasher": "غسالة الأطباق",
        "shed": "السقيفة", "storage": "غرفة التخزين", "pantry": "المؤونة", "laundry": "غرفة الغسيل", "office": "المكتب", "diningroom": "غرفة الطعام",
        "kidsbedroom": "غرفة الأولاد", "barn": "الحظيرة", "farmstorage": "مخزن المزرعة", "warehouse": "المستودع", "garagestorage2": "مخزن الكراج", "emptyoutside": "برا", "empty": "غرفة فاضية",
        "toolstore": "محل الأدوات", "grocery": "السوبرماركت", "gasstore": "محل الكازية", "medical": "العيادة", "pharmacy": "الصيدلية", "bar": "البار", "attic": "السقيفة العلوية",
        "vanseats": "مقاعد الفان", "seat": "مقعد السيارة", "gloveboxfront": "درج السيارة",
    }
    return rooms.get(room.lower(), room or "المخزن")

def _supply_category(item, group):
    typ = str(item.get("type") or "").split(".")[-1]
    cat = str(item.get("cat") or "")
    if group == "fluids":
        kind = str((item.get("fluid") or {}).get("kind") or "")
        return "ماء" if "water" in kind.lower() else "مشروبات"
    if cat in _SUPPLY_CATEGORIES: return _SUPPLY_CATEGORIES[cat]
    if group == "foods": return "طعام"
    if "ammo" in cat.lower() or "bullet" in typ.lower() or "shell" in typ.lower(): return "ذخيرة"
    return _SUPPLY_CATEGORIES.get(cat, "أخرى")

def _supply_number(value, default=0):
    try: return float(value)
    except (TypeError, ValueError): return float(default)

def _format_supply_count(value):
    return str(int(value)) if abs(value - round(value)) < 1e-8 else ("%.1f" % value)

_FARM_TYPES = ("Seed", "Trowel", "Rake", "Shovel", "Spade", "Hoe", "Fertilizer", "Compost", "Slug", "Insecticide", "Mildew", "GardenSpray", "WateringCan", "WateredCan")


def is_farm_item(item):
    """Seeds and farm tools by what the game says they are; never crops or food."""
    return str(item.get("cat")) in ("Gardening", "GardeningWeapon") or any(k in str(item.get("type")) for k in _FARM_TYPES)


def farm_stock_rows(snap, hers=False):
    """The same rows as the inventory table, only seeds and farm tools; hers: only what she carries. Empty when there are none."""
    def keep(c, group, item):
        return group == "items" and is_farm_item(item) and (not hers or c.get("where") == "sol")
    return supplies_table(snap, keep=keep)


def supplies_table(snap, mem=None, keep=None):
    """Itemized inventory rows: in-game name, total quantity, and category/location."""
    grouped = {}
    for c in _containers(snap or {}):
        place = _supply_place(c)
        for group in ("items", "foods", "fluids"):
            for item in c.get(group) or []:
                if keep is not None and not keep(c, group, item): continue
                name = str(item.get("name") or item.get("type") or "غرض غير مسمى")
                typ = str(item.get("type") or name)
                key = (group, typ, name)
                row = grouped.get(key)
                if row is None:
                    category = _supply_category(item, group)
                    row = grouped[key] = {
                        "name": name, "category": category, "count": 0.0,
                        "locations": set(), "liters": 0.0, "calories": 0.0,
                    }
                count = _supply_number(item.get("count"), 1)
                row["count"] += count
                row["locations"].add(place)
                if group == "fluids":
                    row["liters"] += _supply_number((item.get("fluid") or {}).get("liters")) * count
                elif group == "foods":
                    row["calories"] += _supply_number((item.get("food") or {}).get("calories")) * count

    order = {name: i for i, name in enumerate(_SUPPLY_CATEGORY_ORDER)}
    values = sorted(grouped.values(), key=lambda r: (order.get(r["category"], len(order)), r["category"], r["name"].casefold()))
    rows = []
    for item in values:
        details = item["category"]
        if item["liters"] > 0:
            details += " · %s لتر" % _format_supply_count(item["liters"])
        elif item["calories"] > 0:
            details += " · %s سعرة" % _format_supply_count(item["calories"])
        places = sorted(item["locations"])
        if len(places) > 3: location = "، ".join(places[:3]) + "، وغيرها"
        else: location = "، ".join(places)
        details += " · " + (location or "المخزن")
        rows.append((item["name"], _format_supply_count(item["count"]), details, "muted"))
    if keep is not None: return rows
    # Fixed world sources are useful supply facts, but are not carried inventory.
    for source in (snap or {}).get("waterSources") or []:
        if not isinstance(source, dict): continue
        kind = str(source.get("kind") or "water_source")
        name = "بئر (مصدر ماء)" if kind == "well" else str(source.get("name") or "مصدر ماء")
        amount = source.get("amount")
        if isinstance(amount, (int, float)):
            detail = "مصدر ثابت · كمية مقروءة %s لتر" % _format_supply_count(float(amount))
        else:
            detail = "مصدر ثابت · السعة والكمية غير معروفتين"
        if source.get("tainted") is True: detail += " · الماء ملوث"
        elif source.get("tainted") is None: detail += " · نظافة الماء غير مؤكدة"
        x, y = source.get("x"), source.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            detail += " · x %s, y %s" % (_format_supply_count(x), _format_supply_count(y))
        rows.append((name, "1", detail, "muted"))
    if not rows:
        rows.append(("لا توجد أغراض مرصودة", "0", "ضمن نطاق الفحص الحالي", "muted"))
    return rows

def situation_text(snap, mem):
    if not snap: return "No world data from the game yet."
    t = snap.get("time") or {}; w = snap.get("weather") or {}
    lines = ["Game day %s, hour %s, season %s, outside air %s C (measured where the player stands), rain %s." % (t.get("day"), t.get("hour"), w.get("season"), w.get("air"), w.get("rain"))]
    for who, key in (("Player", "player"), ("Sol", "sol")):
        s0 = snap.get(key) or {}
        if s0.get("x") is not None:
            where = s0.get("room") or ("outdoors" if not s0.get("indoors") else "indoors")
            lines.append("%s position: x %s, y %s, floor %s, %s%s." % (who, round(s0.get("x")), round(s0.get("y")), s0.get("z"), where, ", in a vehicle" if s0.get("inVehicle") else ""))
    for who, key in (("Player", "player"), ("Sol", "sol")):
        s = snap.get(key) or {}
        if not s: continue
        st = s.get("stats") or {}
        lines.append("%s: health %s, hunger %s, thirst %s, fatigue %s, wet %s, moodles %s, wounds %s, weapon %s, room %s." % (
            who, s.get("health"), st.get("HUNGER"), st.get("THIRST"), st.get("FATIGUE"), st.get("WETNESS"), s.get("moodles") or {},
            len(s.get("wounds") or []), s.get("weapon"), s.get("room") or ("outside" if not s.get("indoors") else "?")))
        if s.get("temperatureBody") is not None: lines.append("%s body temperature %s C." % (who, s.get("temperatureBody")))
        if s.get("skills") is not None:
            lines.append("%s skills (level 1-10, only those above 0): %s%s." % (who, ", ".join("%s %s" % kv for kv in sorted(s["skills"].items())) or "none above 0",
                                                                        ("; profession " + str(s.get("profession"))) if s.get("profession") else ""))
    f = food_report(snap); wr = water_report(snap); rate = hunger_rate(mem, snap)
    food = "Food: %s edible items, %s hunger points%s." % (f["items"], f["hunger_points"], (", %s kcal" % f["calories"]) if f["calories"] else "")
    if rate: food += " Measured player hunger rate %.2f/day -> about %.1f days for one person at the current pace." % (rate, f["hunger_points"] / rate if rate else 0)
    lines.append(food)
    lines.append("Water: %s L clean, %s L tainted%s%s." % (wr["clean_liters"], wr["tainted_liters"],
        (", tap water stops in %s days" % wr["water_off_in_days"]) if "water_off_in_days" in wr else "",
        (", power stops in %s days" % wr["power_off_in_days"]) if "power_off_in_days" in wr else ""))
    if snap.get("vehicles"): lines.append("Vehicles: " + "; ".join("%s fuel %s/%s" % (v.get("name"), v.get("fuel"), v.get("fuelMax")) for v in snap["vehicles"][:5]))
    if snap.get("plants"): lines.append("Plants nearby: %d (lowest water %s)." % (len(snap["plants"]), min((p.get("water") or 0) for p in snap["plants"])))
    if snap.get("animals"): lines.append("Animals nearby: %d." % len(snap["animals"]))
    nd = needs(snap, mem)
    if nd: lines.append("Urgent: " + "; ".join("%s %s (%s)" % (n["who"], n["need"], n["why"]) for n in nd[:8]))
    home = mem.data.get("home") if mem else None
    if not home and isinstance(snap.get("solHome"), dict) and snap["solHome"].get("x") is not None:
        sh = snap["solHome"]; home = {"name": "home", "x": sh["x"], "y": sh["y"], "z": sh.get("z", 0)}   # set in game ("this is home")
    if home:
        p = snap.get("player") or {}
        d = None
        if p.get("x") is not None: d = round(math.hypot(p["x"] - home["x"], p["y"] - home["y"]))
        lines.append("Home: %s at x %s, y %s%s." % (home.get("name"), home.get("x"), home.get("y"), (", %s tiles from the player" % d) if d is not None else ""))
    if mem and mem.data.get("places"): lines.append("Remembered places: " + "; ".join("%s (%s,%s)" % (p["name"], p["x"], p["y"]) for p in mem.data["places"][-10:]))
    cats = {}
    for c in _containers(snap):
        for it in c.get("items") or []: cats[it.get("cat") or "Other"] = cats.get(it.get("cat") or "Other", 0) + (it.get("count") or 1)
    if cats: lines.append("Other stock by category: " + ", ".join("%s %d" % kv for kv in sorted(cats.items(), key=lambda kv: -kv[1])[:12]))
    return "\n".join(lines)

# ---------------------------------------------------------------- what Sol can make (game recipes judged for Sol in game)
RECIPES = "SolRecipes_Snapshot.txt"
def load_recipes(lua_dir):
    try:
        with open(os.path.join(lua_dir, RECIPES), encoding="ascii", errors="replace") as f: return json.loads(f.read())
    except (OSError, ValueError): return None

def stock_by_type(snap):
    have = {}
    for c in _containers(snap or {}):
        for grp in ("items", "foods", "fluids"):
            for it in c.get(grp) or []:
                t = it.get("type")
                if t: have[t] = have.get(t, 0) + (it.get("count") or 1)
    return have

def can_make(query, recipes, snap):
    if not recipes: return {"error": "recipe catalog not received from the game yet"}
    q = (query or "").lower().strip()
    if not q: return {"error": "empty query"}
    have = stock_by_type(snap)
    hits = [r for r in recipes.get("recipes") or [] if q in str(r.get("n", "")).lower() or q in str(r.get("t", "")).lower()]
    hits.sort(key=lambda r: (len(str(r.get("t") or r.get("n") or "")), str(r.get("n"))))
    out = []
    for r in hits[:5]:
        missing_skills = [{"skill": s[0], "needs": s[1]} for s in r.get("skills") or [] if not s[2]]
        inputs, missing_items = [], []
        for inp in r.get("in") or []:
            got = {a: have[a] for a in inp.get("a", []) if have.get(a)}
            inputs.append({"any_of": inp.get("a"), "amount": inp.get("q"), "have": got})
            if not got: missing_items.append(inp.get("a", [])[:3])
        if r.get("learn") and not r.get("known"): verdict = "not_learned"
        elif missing_skills: verdict = "skill_too_low"
        elif missing_items: verdict = "missing_items"
        else: verdict = "can_make"
        out.append({"recipe": r.get("t") or r.get("n"), "id": r.get("n"), "verdict": verdict, "needs_learning": bool(r.get("learn")),
                    "known": r.get("known"), "missing_skills": missing_skills, "missing_items": missing_items, "inputs": inputs[:8]})
    return {"matches": out, "total_matches": len(hits)}

# ---------------------------------------------------------------- tools for the brain
TOOLS = [
    {"type": "function", "function": {"name": "find_items", "description": "Search every reachable inventory (player, Sol, nearby containers, vehicle trunks) for an item by name, type or category, e.g. 'nails', 'seed', 'fertilizer', 'water'.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "remember_place", "description": "Remember the player's current location with a name and what is there (containers and items seen now are stored).", "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "note": {"type": "string"}}, "required": ["name"]}}},
    {"type": "function", "function": {"name": "recall_places", "description": "List remembered places, optionally only those that had a given item.", "parameters": {"type": "object", "properties": {"item": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "set_home", "description": "Mark the player's current location as home.", "parameters": {"type": "object", "properties": {"name": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "can_make", "description": "Check, with the game's own rules, whether Sol can make/cook/build something: is the recipe known to her (or does it need a magazine/book), are her skill levels enough, and which ingredients/tools we have or miss. Query in English recipe words, e.g. 'stew', 'door', 'bandage'.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "forget_place", "description": "Forget a remembered place by name.", "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}},
]

def run_tool(name, args, snap, mem, recipes=None):
    args = args or {}
    if name == "can_make": return can_make(args.get("query", ""), recipes, snap)
    if not snap and name in ("find_items", "remember_place", "set_home"): return {"error": "no world data from the game yet"}
    if name == "find_items": return {"results": find_items(snap, args.get("query", ""))}
    p = snap.get("player") if snap else {}
    if name == "remember_place":
        items = {}
        for c in _containers(snap):
            if c.get("where") in ("square", "vehicle"):
                for grp in ("items", "foods", "fluids"):
                    for it in c.get(grp) or []: items[it.get("name")] = items.get(it.get("name"), 0) + (it.get("count") or 1)
        place = {"name": args.get("name"), "note": args.get("note", ""), "x": round(p.get("x") or 0), "y": round(p.get("y") or 0), "z": p.get("z"),
                 "room": p.get("room"), "items": items, "day": (snap.get("time") or {}).get("day")}
        mem.data["places"] = [q for q in mem.data["places"] if q["name"] != place["name"]] + [place]; mem.save()
        return {"saved": place["name"], "items_seen": len(items)}
    if name == "recall_places":
        q = (args.get("item") or "").lower()
        out = [{"name": pl["name"], "x": pl["x"], "y": pl["y"], "note": pl.get("note"), "day": pl.get("day"),
                "matching": {k: v for k, v in pl.get("items", {}).items() if q and q in str(k).lower()}} for pl in mem.data["places"]
               if not q or any(q in str(k).lower() for k in pl.get("items", {}))]
        return {"places": out[:20]}
    if name == "set_home":
        mem.data["home"] = {"name": args.get("name") or "home", "x": round(p.get("x") or 0), "y": round(p.get("y") or 0), "z": p.get("z")}; mem.save()
        return {"home": mem.data["home"]}
    if name == "forget_place":
        before = len(mem.data["places"]); mem.data["places"] = [q for q in mem.data["places"] if q["name"] != args.get("name")]; mem.save()
        return {"removed": before - len(mem.data["places"])}
    return {"error": "unknown tool"}

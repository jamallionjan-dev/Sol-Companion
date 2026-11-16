# sol_templates.py - fixed answers in Levantine colloquial for the questions Sol gets all the time (supplies, farm, fuel and cars).
# The numbers come straight from the game's snapshot, so the weak language model can no longer write "oil" for fuel, mix the digits into the
# sentence, or count dead plants as thirsty ones. Sol speaks as a woman and speaks to the player as a man.
import re

def _w():
    import world_knowledge as W      # imported when used, so this file can be tested without the game's modules around
    return W

def num(x):
    try: v = float(x)
    except (TypeError, ValueError): return "0"
    s = ("%.1f" % v).rstrip("0").rstrip(".")
    return s or "0"

def days_word(n):
    return "يوم" if n == 1 else "يومين" if n == 2 else "أيام" if 3 <= n <= 10 else "يوم"

def plants_word(n):
    return "نبتة" if n == 1 else "نبتتين" if n == 2 else "نباتات" if 3 <= n <= 10 else "نبتة"

def when(d):
    try: d = float(d)
    except (TypeError, ValueError): return ""
    if d < 1: return "قبل ما يخلص اليوم"
    if d < 2: return "بعد يوم تقريباً"
    n = int(round(d))
    return "بعد %d %s" % (n, days_word(n))

# the game's food names, in the words Sol would use (an unknown food keeps the game's own name)
FOODS = [("baloney", "البولوني"), ("bread", "الخبز"), ("sausage", "السجق"), ("steak", "الستيك"), ("chicken", "الدجاج"), ("tuna", "التونة"),
         ("corn", "الذرة"), ("chili", "الشيلي"), ("soup", "الشوربة"), ("beans", "الفاصوليا"), ("cheese", "الجبنة"), ("milk", "الحليب"),
         ("egg", "البيض"), ("bacon", "اللحم المقدد"), ("beef", "اللحم"), ("pork", "لحم الخنزير"), ("fish", "السمك"), ("apple", "التفاح"),
         ("banana", "الموز"), ("orange", "البرتقال"), ("peach", "الخوخ"), ("pasta", "المعكرونة"), ("rice", "الرز"), ("tomato", "البندورة"),
         ("potato", "البطاطا"), ("carrot", "الجزر"), ("cabbage", "الملفوف"), ("pizza", "البيتزا"), ("burger", "البرغر"), ("sandwich", "السندويش")]
def food_ar(name):
    n = str(name or "").lower()
    word = next((ar for k, ar in FOODS if k in n), None)
    if word is None: return str(name or "")
    return ("علبة %s المفتوحة" % word) if "(open)" in n else word

VEHICLES = [("ambulance", "سيارة الإسعاف"), ("police", "سيارة الشرطة"), ("fire", "سيارة الإطفاء"), ("taxi", "التاكسي"), ("bradley", "البرادلي"), ("heli", "الهليكوبتر"),   # s77
            ("trooper", "التروبر"), ("ford", "الفورد"), ("trailer", "المقطورة"), ("astrodome", "المقطورة"), ("van", "الفان"), ("pickup", "البيك أب"), ("truck", "الشاحنة"),
            ("sportscar", "السيارة الرياضية"), ("luxury", "السيارة الفخمة"), ("offroad", "الجيب"), ("suv", "الجيب"), ("stationwagon", "الستيشن"),
            ("smallcar", "السيارة الصغيرة"), ("moderncar", "السيارة الحديثة"), ("carnormal", "السيارة العادية")]
def vehicle_ar(name):
    n = str(name or "").lower()
    return next((ar for k, ar in VEHICLES if k in n), str(name or "سيارة"))

def _soon(snap, f):
    """[(name, days)] of what spoils first: the base inventory's own list when there is one, else the report's."""
    out = []
    inv = (snap or {}).get("baseInventory") or {}
    for e in ((inv.get("food") or {}).get("soonList") or []):
        if isinstance(e, (list, tuple)) and len(e) >= 2: out.append((e[0], e[1]))
    if not out:
        for e in (f.get("spoiling_soon") or []):
            if isinstance(e, dict): out.append((e.get("name") or e.get("n"), e.get("days") if e.get("days") is not None else e.get("dl")))
            elif isinstance(e, (list, tuple)) and len(e) >= 2: out.append((e[0], e[1]))
    out = [(n, d) for n, d in out if n and isinstance(d, (int, float))]
    return sorted(out, key=lambda x: x[1])

def _ammo(snap):
    inv = (snap or {}).get("baseInventory") or {}
    loose = other = 0
    for a in inv.get("ammo") or []:
        n = str(a.get("n") or "").lower()
        if n.endswith("rounds"): loose += int(a.get("rounds") or 0)
        else: other += int(a.get("items") or 0)
    return loose, other

def supplies_text(snap, mem):
    W = _w(); f = W.food_report(snap); wr = W.water_report(snap)
    parts = []
    items, cal = f.get("items"), f.get("calories")
    if items: parts.append("عنّا %s غرض أكل%s." % (items, (("، يعني حوالي %s سعرة" % cal) if cal else "")))
    soon = _soon(snap, f)
    if soon: parts.append("أول شي رح يخرب: %s %s%s." % (food_ar(soon[0][0]), when(soon[0][1]), ("، وفي %d أصناف غيره قرب وقتها" % (len(soon) - 1)) if len(soon) > 1 else ""))
    water = "المي النضيفة المخزنة بالحاويات %s لتر" % num(wr.get("clean_liters"))
    sources = wr.get("sources") or []
    wells = [source for source in sources if source.get("kind") == "well"]
    other_sources = [source for source in sources if source.get("kind") != "well"]
    if wells:
        known_amounts = [source["amount"] for source in wells if source.get("amount") is not None]
        if known_amounts:
            water += "، وفي %d بئر قريب فيه كمية مقروءة %s لتر" % (len(wells), num(sum(known_amounts)))
        else:
            water += "، وفي %d بئر قريب كمصدر ماء لكن سعته وكمية الماء غير معروفتين" % len(wells)
        if any(source.get("tainted") is True for source in wells):
            water += " وبعض مياهه ملوثة"
        elif any(source.get("tainted") is None for source in wells):
            water += " ونظافة مياهه غير مؤكدة"
    if other_sources:
        water += "، وفي %d مصدر ماء آخر ضمن المنطقة الممسوحة" % len(other_sources)
    for key, label in (("water_off_in_days", "والحنفية رح تنقطع"), ("power_off_in_days", "والكهربا رح تنقطع")):
        if wr.get(key) is not None:
            n = max(0, int(round(wr[key]))); water += "، %s بعد %d %s" % (label, n, days_word(n))
    parts.append(water + ".")
    loose, other = _ammo(snap)
    if loose or other: parts.append("الذخيرة حوالي %d طلقة سايبة%s." % (loose, ("، غير %d مخزن وعلبة" % other) if other else ""))
    rows = W.supplies_table(snap, mem)
    zero = [r[0] for r in rows if len(r) > 2 and r[2] == "لا يوجد"]
    if zero: parts.append("وما عنّا: %s." % " و".join(zero))
    return " ".join(parts)

def farm_text(snap, mem):
    """Truthful farm report, zone by zone, from the game's own farm scan (not the tiles around him)."""
    import farm_talk as FT
    return FT.report_text((snap or {}).get("solFarm"))

def vehicles_text(snap, mem):
    vs = (snap or {}).get("vehicles") or []
    if not vs: return "ما شايفة سيارات حواليّ."
    fueled, bare, low = [], [], []
    for v in vs:
        name = vehicle_ar(v.get("name"))
        f, m = v.get("fuel"), v.get("fuelMax")
        if isinstance(f, (int, float)) and isinstance(m, (int, float)) and m > 0:
            fueled.append("%s فيها %s لتر من %s" % (name, num(f), num(m)))
            if f / m < 0.25: low.append(name)
        else: bare.append(name)
    parts = []
    if fueled: parts.append("، و".join(fueled) + ".")
    if bare: parts.append("%s ما إلها وقود." % " و".join(bare))
    if low: parts.append("وقود %s قليل." % " و".join(low))
    can = ((snap or {}).get("baseInventory") or {}).get("fuel")
    if isinstance(can, (int, float)): parts.append(("وبالعلب عنّا %s لتر وقود." % num(can)) if can > 0 else "وما عنّا وقود بالعلب.")
    return " ".join(parts)

def reply(kind, snap, mem):
    if not snap: return None
    return {"supplies": supplies_text, "farm_report": farm_text, "vehicle_report": vehicles_text}[kind](snap, mem)

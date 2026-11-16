"""The map as the game draws it, for answering questions. Built offline from the game's own files by 05_TOOLS/sol_gazetteer.

What she may say about it is decided by where she has actually been: see visited().
"""
import gzip, json, math, os

BIN = 64
VISIT_CELL = 30
TOWN_REACH = 450
TOWN_AR = {"Louisville": "لويزفيل", "Muldraugh": "مولدرو", "West Point": "ويست بوينت", "Riverside": "ريفرسايد", "Rosewood": "روزوود", "March Ridge": "مارش ريدج",
           "Valley Station": "فالي ستيشن", "Fallas Lake": "فالاس ليك", "Echo Creek": "إيكو كريك", "Ekron": "إيكرون", "Irvington": "إرفينغتون", "Brandenburg": "براندنبورغ"}
KIND_AR = {"gas": "كازية", "gas2go": "كازية غاز تو غو", "fossoil": "كازية فوس أويل", "hospital": "مستشفى", "hotel": "فندق", "police": "مخفر شرطة", "fire": "مركز إطفاء", "school": "مدرسة", "church": "كنيسة", "bank": "بنك",
           "pharmacy": "صيدلية", "clinic": "عيادة", "grocery": "سوبرماركت", "restaurant": "مطعم", "bar": "بار", "guns": "محل أسلحة", "mechanic": "كراج تصليح", "prison": "سجن", "army": "موقع عسكري",
           "warehouse": "مستودع", "library": "مكتبة", "tools": "محل أدوات", "clothes": "محل ألبسة", "gym": "نادي رياضة", "house": "بيت", "farm": "مزرعة", "farmland": "أرض زراعية", "office": "مكاتب", "building": "بناية"}
KIND_WORDS = (("hotel", ("فندق", "اوتيل", "موتيل", "hotel", "motel")), ("hospital", ("مستشفى", "مشفى", "hospital")), ("clinic", ("عياده", "عيادة", "طبيب", "دكتور", "clinic")),
              ("pharmacy", ("صيدليه", "صيدلية", "pharmacy")), ("police", ("مخفر", "شرطه", "شرطة", "police")), ("fire", ("اطفاء", "اطفائية", "fire station")), ("school", ("مدرسه", "مدرسة", "school")),
              ("church", ("كنيسه", "كنيسة", "church")), ("bank", ("بنك", "مصرف", "bank")), ("grocery", ("سوبرماركت", "سوبر ماركت", "بقاليه", "بقالية", "دكان", "grocery", "supermarket")),
              ("restaurant", ("مطعم", "restaurant")), ("bar", ("خماره", "خمارة", "بار", "bar")), ("guns", ("محل اسلحه", "محل اسلحة", "محل سلاح", "gun store")), ("mechanic", ("كراج", "ميكانيك", "mechanic")),
              ("warehouse", ("مستودع", "مصنع", "warehouse", "factory")), ("library", ("مكتبه", "مكتبة", "library")), ("farm", ("مزرعه", "مزرعة", "مزارع", "حقل", "حقول", "حديقه", "حديقة", "زراعيه", "زراعية", "farm", "garden")))
_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gazetteer.json.gz")


class Gazetteer:
    def __init__(self, path=_DEFAULT):
        with gzip.open(path, "rt", encoding="utf-8") as f: d = json.load(f)
        self.towns, self.landmarks, self.kinds, self.names, self.buildings, self.streets = d["towns"], d["landmarks"], d["kinds"], d["names"], d["buildings"], d["streets"]
        self.bins = {}
        for i, b in enumerate(self.buildings):
            if self.kinds[b[4]] == "farmland": continue                          # land, not a building anyone is standing in front of
            for x in range(b[0] // BIN, b[2] // BIN + 1):
                for y in range(b[1] // BIN, b[3] // BIN + 1): self.bins.setdefault((x, y), []).append(i)
        self.by_kind = {}
        for i, b in enumerate(self.buildings): self.by_kind.setdefault(self._base_kind(b), []).append(i)

    def _base_kind(self, b):
        k = self.kinds[b[4]]
        return "gas" if k in ("gas2go", "fossoil") else "farm" if k == "farmland" else k

    def _describe(self, b):
        k = self.kinds[b[4]]
        return {"kind": self._base_kind(b), "label": KIND_AR.get(k, "بناية"), "name": self.names[b[5]] if b[5] >= 0 else None, "x": (b[0] + b[2]) // 2, "y": (b[1] + b[3]) // 2}

    def town_at(self, x, y):
        """The town this point is in, or None out in the country."""
        best, bd = None, 1e18
        for t in self.towns:
            d = math.hypot(t["x"] - x, t["y"] - y)
            inside = any(r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3] for r in t["r"])
            if (inside or d <= TOWN_REACH) and d < bd: best, bd = t, d
        return best

    def nearest_town(self, x, y): return min(self.towns, key=lambda t: math.hypot(t["x"] - x, t["y"] - y))

    def building_at(self, x, y, reach=25):
        """The building at this point, or the closest one within reach."""
        best, bd = None, reach * reach + 1
        for bx in range((int(x) - reach) // BIN, (int(x) + reach) // BIN + 1):
            for by in range((int(y) - reach) // BIN, (int(y) + reach) // BIN + 1):
                for i in self.bins.get((bx, by), ()):
                    b = self.buildings[i]
                    dx, dy = max(b[0] - x, 0, x - b[2]), max(b[1] - y, 0, y - b[3])
                    d = dx * dx + dy * dy
                    if d < bd: best, bd = b, d
        return self._describe(best) if best is not None else None

    def nearest_kind(self, kind, x, y, allowed):
        """The nearest building of this kind that passes allowed(x, y), or None."""
        best, bd = None, 1e18
        for i in self.by_kind.get(kind, ()):
            b = self.buildings[i]
            cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
            d = (cx - x) ** 2 + (cy - y) ** 2
            if d < bd and allowed(cx, cy): best, bd = b, d
        return self._describe(best) if best is not None else None

    def places(self):
        """Everything that can be asked about by name: [(right name, other spellings, x, y, reach)]."""
        out = [(TOWN_AR.get(t["n"], t["n"]), (t["n"],), t["x"], t["y"], TOWN_REACH) for t in self.towns]
        out += [(l["n"], (), l["x"], l["y"], 40) for l in self.landmarks]
        for n in sorted({self.names[b[5]] for b in self.buildings if b[5] >= 0} - {l["n"] for l in self.landmarks}):
            b = next(x for x in self.buildings if x[5] >= 0 and self.names[x[5]] == n)
            out.append((n, (), (b[0] + b[2]) // 2, (b[1] + b[3]) // 2, 40))
        return out

    def street_near(self, x, y, reach=40):
        """The name of the street closest to this point, or None."""
        best, bd = None, reach * reach + 1
        for s in self.streets:
            pts = s["p"]
            for a, b in zip(pts, pts[1:]):
                dx, dy = b[0] - a[0], b[1] - a[1]
                n = dx * dx + dy * dy
                t = 0 if n == 0 else max(0, min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / n))
                d = (a[0] + t * dx - x) ** 2 + (a[1] + t * dy - y) ** 2
                if d < bd: best, bd = s["n"], d
        return best

    def street_point(self, name, x, y):
        pts = [p for s in self.streets if s["n"] == name for p in s["p"]]
        return min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2) if pts else None


_loaded = None


def load(path=_DEFAULT):
    """The one index, or None if the file is missing or damaged: she then just doesn't know."""
    global _loaded
    if _loaded is None:
        try: _loaded = Gazetteer(path)
        except (OSError, ValueError, KeyError): _loaded = False
    return _loaded or None


def mark_visited(mem, x0, y0, x1=None, y1=None):
    """Marks what she has passed: every area within reach of the line from the last position to this one. True if anything new."""
    have = set(mem.data.get("visited") or [])
    before = len(have)
    x1, y1 = x0 if x1 is None else x1, y0 if y1 is None else y1
    steps = max(1, int(math.hypot(x1 - x0, y1 - y0) // VISIT_CELL))
    for i in range(steps + 1):
        x, y = x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps
        cx, cy = int(x) // VISIT_CELL, int(y) // VISIT_CELL
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1): have.add("%d,%d" % (cx + dx, cy + dy))
    if len(have) == before: return False
    mem.data["visited"] = sorted(have)
    return True


def visited(mem, x, y, reach=0):
    """Has she been here, or within reach of here?"""
    have = (mem.data.get("visited") or []) if mem is not None else []
    if not have: return False
    have = set(have)
    c = int(reach // VISIT_CELL) + 0
    cx, cy = int(x) // VISIT_CELL, int(y) // VISIT_CELL
    for dx in range(-c, c + 1):
        for dy in range(-c, c + 1):
            if "%d,%d" % (cx + dx, cy + dy) in have: return True
    return False

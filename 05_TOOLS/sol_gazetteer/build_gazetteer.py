"""Builds Sol Mind's map index from the game's own files. It only reads the game install; nothing there is changed.

Sources (media/maps/Muldraugh, KY):
  *.lotheader                every building, room by room
  streets.xml                street names with their geometry
  worldmap-annotations.lua   town, place and landmark labels
  regions.lua                town areas and named buildings
  media/lua/shared/Translate/EN/MapLabel.json   the proper town names

usage: build_gazetteer.py [output.json.gz]
"""
import glob, gzip, json, os, re, struct, sys, xml.etree.ElementTree as ET

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media"
MAP = os.path.join(GAME, "maps", "Muldraugh, KY")
CELL = 256
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sol_mind", "gazetteer.json.gz")
TOWN_REGIONS = {"Louisville", "Muldraugh", "WestPoint", "Riverside", "MarchRidge", "Rosewood", "ValleyStation"}
LABEL_NAME_FIX = {"WestPoint": "West Point", "MarchRidge": "March Ridge", "ValleyStation": "Valley Station", "EchoCreek": "Echo Creek", "FallasLake": "Fallas Lake"}


def parse_header(path):
    b = open(path, "rb").read(); i = 8
    def rint():
        nonlocal i
        v = struct.unpack_from("<i", b, i)[0]; i += 4; return v
    def rstr():
        nonlocal i
        e = b.index(b"\n", i); s = b[i:e].decode("latin-1"); i = e + 1; return s
    for _ in range(rint()): rstr()
    rint(); rint(); rint(); rint()
    rooms = []
    for _ in range(rint()):
        name = rstr(); rint()
        rects = [(rint(), rint(), rint(), rint()) for _ in range(rint())]
        for _ in range(rint()): rint(); rint(); rint()
        rooms.append((name, rects))
    return rooms, [[rint() for _ in range(rint())] for _ in range(rint())]


def kind_of(names):
    s = set(names)
    def any_in(*w): return any(n in s for n in w)
    def part(*w): return any(x in n for n in s for x in w)
    if "gas2go" in s: return "gas", "gas2go"
    if "fossoil" in s: return "gas", "fossoil"
    if any_in("gasstore", "gasstorage"): return "gas", ""
    if part("hospital", "patientroom", "operatingroom"): return "hospital", ""
    if part("motel", "hotel"): return "hotel", ""
    if part("police"): return "police", ""
    if part("fire"): return "fire", ""
    if part("school", "classroom"): return "school", ""
    if any_in("church"): return "church", ""
    if any_in("bank", "bankstorage"): return "bank", ""
    if part("pharmacy"): return "pharmacy", ""
    if any_in("medclinic", "clinic", "dentist", "medical", "medicaloffice"): return "clinic", ""
    if any_in("grocery", "grocerystorage", "gigamart", "conveniencestore", "cornerstore", "zippeestore", "generalstore", "producestorage"): return "grocery", ""
    if part("restaurant", "pizza", "burger", "spiffo", "diner", "chinese", "bakery", "icecream", "cafe"): return "restaurant", ""
    if any_in("bar", "barstorage", "barkitchen"): return "bar", ""
    if part("gunstore"): return "guns", ""
    if any_in("mechanic"): return "mechanic", ""
    if part("prisoncell"): return "prison", ""
    if part("armystorage", "armytent"): return "army", ""
    if any_in("warehouse", "factory", "factorystorage", "storageunit"): return "warehouse", ""
    if any_in("library"): return "library", ""
    if part("toolstore"): return "tools", ""
    if part("clothesstore", "shoestore"): return "clothes", ""
    if part("gym"): return "gym", ""
    if any_in("bedroom", "livingroom", "kidsbedroom"): return "house", ""
    if any_in("kitchen", "bathroom") and not any_in("office"): return "house", ""
    if any_in("barn", "farmstorage", "stable", "chickencoop"): return "farm", ""
    if any_in("office", "officestorage"): return "office", ""
    return "building", ""


def camel(s): return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)


def main():
    text = open(os.path.join(MAP, "worldmap-annotations.lua"), encoding="utf-8").read()
    translate = json.load(open(os.path.join(GAME, "lua", "shared", "Translate", "EN", "MapLabel.json"), encoding="utf-8"))
    towns, landmarks = {}, []
    for raw, style, x, y in re.findall(r'add(?:Unt|T)ranslatedText\("([^"]+)",\s*"([^"]+)",\s*(-?\d+),\s*(-?\d+)\)', text):
        x, y = int(x), int(y)
        if style == "text-town":
            key = raw.replace("MapLabel_", "")
            towns[key] = {"n": LABEL_NAME_FIX.get(key, translate.get(raw, key).title()), "x": x, "y": y, "r": []}
        elif style in ("text-building", "text-place"):
            landmarks.append({"n": re.sub(r"\s+", " ", re.sub(r"(?i)<br>", " ", raw)).strip(), "x": x, "y": y})
    regions = open(os.path.join(MAP, "regions.lua"), encoding="utf-8").read()
    named = []
    for name, typ, x, y, w, h in re.findall(r'name = "([^"]+)", type = "(\w+)", x = (-?\d+), y = (-?\d+), z = -?\d+, width = ?(\d+), height = ?(\d+)', regions):
        x, y, w, h = int(x), int(y), int(w), int(h)
        if typ == "Region" and name in TOWN_REGIONS and name in towns: towns[name]["r"].append([x, y, w, h])
        elif typ == "BuildingName": named.append((camel(name), x, y, w, h))
    names, name_at = [], {}
    def name_id(n):
        if n not in name_at: name_at[n] = len(names); names.append(n)
        return name_at[n]
    kinds, kind_at, buildings = [], {}, []
    files = glob.glob(os.path.join(MAP, "*.lotheader"))
    for f in files:
        cx, cy = map(int, os.path.basename(f)[:-10].split("_"))
        rooms, blds = parse_header(f)
        for rs in blds:
            xs0, ys0, xs1, ys1, rn = [], [], [], [], []
            for idx in rs:
                nm, rects = rooms[idx]
                rn.append(nm)
                for x, y, w, h in rects: xs0.append(x); ys0.append(y); xs1.append(x + w); ys1.append(y + h)
            if not xs0: continue
            kind, brand = kind_of(rn)
            label = brand or kind
            if label not in kind_at: kind_at[label] = len(kinds); kinds.append(label)
            ox, oy = cx * CELL, cy * CELL
            buildings.append([ox + min(xs0), oy + min(ys0), ox + max(xs1), oy + max(ys1), kind_at[label], -1])
    for nm, x, y, w, h in named:
        best, bd = None, 25.0 ** 2
        for b in buildings:
            dx = max(b[0] - (x + w / 2), 0, (x + w / 2) - b[2]); dy = max(b[1] - (y + h / 2), 0, (y + h / 2) - b[3])
            d = dx * dx + dy * dy
            if b[4] != kind_at.get("house") and d < bd: best, bd = b, d
        if best is not None: best[5] = name_id(nm)
    for lm in landmarks:
        best, bd = None, 30.0 ** 2
        for b in buildings:
            dx = max(b[0] - lm["x"], 0, lm["x"] - b[2]); dy = max(b[1] - lm["y"], 0, lm["y"] - b[3])
            d = dx * dx + dy * dy
            if d < bd: best, bd = b, d
        if best is not None and best[5] < 0: best[5] = name_id(lm["n"])
    fields = 0
    objects = open(os.path.join(MAP, "objects.lua"), encoding="utf-8").read()
    if "farmland" not in kind_at: kind_at["farmland"] = len(kinds); kinds.append("farmland")
    for typ, x, y, w, h in re.findall(r'type = "(Farm|FarmLand|Ranch)", x = (-?\d+), y = (-?\d+), z = -?\d+, width = ?(\d+), height = ?(\d+)', objects):
        x, y, w, h = int(x), int(y), int(w), int(h)
        buildings.append([x, y, x + w, y + h, kind_at["farmland"], -1]); fields += 1
    print("farm land areas", fields)
    streets = []
    for st in ET.parse(os.path.join(MAP, "streets.xml")).getroot().iter("street"):
        pts = [[int(float(p.get("x"))), int(float(p.get("y")))] for p in st.iter("point")]
        if st.get("name") and pts: streets.append({"n": st.get("name"), "p": pts})
    data = {"v": 1, "towns": list(towns.values()), "landmarks": landmarks, "kinds": kinds, "names": names, "buildings": buildings, "streets": streets}
    with gzip.open(OUT, "wt", encoding="utf-8") as z: json.dump(data, z, ensure_ascii=False, separators=(",", ":"))
    print("towns", len(towns), "landmarks", len(landmarks), "named buildings", sum(1 for b in buildings if b[5] >= 0), "buildings", len(buildings), "streets", len(streets), "from", len(files), "cells;", os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()

"""Item names as the game shows them, for naming things that are not in the world yet. Reads the game install only.
usage: build_item_names.py [output.json.gz]"""
import glob, gzip, json, os, re, sys

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sol_mind", "item_names.json.gz")
tr = {}
for f in glob.glob(os.path.join(GAME, "lua", "shared", "Translate", "EN", "ItemName*.json")):
    tr.update(json.load(open(f, encoding="utf-8")))
names, tags = {}, {}
for f in glob.glob(os.path.join(GAME, "scripts", "**", "*.txt"), recursive=True):
    text = open(f, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"\bitem\s+(\w+)\s*\{(.*?)\n\s*\}", text, re.S):
        full = "Base." + m.group(1)
        if full in names: continue
        shown = tr.get(full) or tr.get("ItemName_" + full)
        if shown is None: continue
        names[full] = shown
        t = re.search(r"Tags\s*=\s*([^,\n]+)", m.group(2))
        for tag in (t.group(1).split(";") if t else []):
            tags.setdefault(tag.strip().replace("base:", ""), []).append(full)
with gzip.open(OUT, "wt", encoding="utf-8") as z: json.dump({"names": names, "tags": tags}, z, ensure_ascii=False, separators=(",", ":"))
print("items", len(names), "tags", len(tags), "digplow", len(tags.get("digplow", [])), "compost", len(tags.get("compost", [])), os.path.getsize(OUT), "bytes")

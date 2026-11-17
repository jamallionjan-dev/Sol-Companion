"""Read-only: the enabled mods of the main game, grouped by Workshop item, with Steam's own install dates.
usage: workshop_inventory.py [--days N]   -> prints a table and writes 05_TOOLS/out/workshop_inventory.tsv
Columns: workshop id, Steam's timeupdated (when the author last updated it), enabled mod ids, name, description."""
import datetime, os, re, sys
WS = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\108600"
ACF = r"C:\Program Files (x86)\Steam\steamapps\workshop\appworkshop_108600.acf"
LIST = r"C:\Users\JAMAL\Zomboid\mods\default.txt"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "workshop_inventory.tsv")
days = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 10 ** 6
order = re.findall(r"mod = ([^,\r\n]+),", open(LIST, encoding="utf-8").read())
en = set(order)
acf = open(ACF, encoding="utf-8", errors="replace").read()
inst = re.search(r'"WorkshopItemsInstalled"\s*\{(.*?)\n\t\}', acf, re.S).group(1)
upd = {m.group(1): int(dict(re.findall(r'"(\w+)"\s*"([^"]*)"', m.group(2))).get("timeupdated", 0)) for m in re.finditer(r'"(\d+)"\s*\{(.*?)\}', inst, re.S)}
items = {}
for wid in os.listdir(WS):
    base = os.path.join(WS, wid, "mods")
    if not os.path.isdir(base): continue
    for dp, dirs, fs in os.walk(base):
        if dp.count(os.sep) - base.count(os.sep) > 3: dirs[:] = []; continue
        if "mod.info" not in fs: continue
        t = open(os.path.join(dp, "mod.info"), encoding="utf-8", errors="replace").read()
        i = re.search(r"(?mi)^id\s*=\s*\\?(.+?)\s*$", t)
        if not i or i.group(1).strip() not in en: continue
        n = re.search(r"(?mi)^name\s*=\s*(.+?)\s*$", t); d = re.search(r"(?mi)^description\s*=\s*(.+?)\s*$", t)
        it = items.setdefault(wid, {"ids": [], "name": n.group(1).strip() if n else "", "desc": (d.group(1).strip() if d else "")})
        if i.group(1).strip() not in it["ids"]: it["ids"].append(i.group(1).strip())
now = datetime.datetime.now()
rows = sorted(items.items(), key=lambda kv: -upd.get(kv[0], 0))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("workshop_id\tupdated\tmod_ids\tname\tdescription\n")
    for wid, it in rows:
        tu = datetime.datetime.fromtimestamp(upd.get(wid, 0))
        f.write("%s\t%s\t%s\t%s\t%s\n" % (wid, tu.strftime("%Y-%m-%d %H:%M"), ",".join(it["ids"]), it["name"], it["desc"][:300].replace("\t", " ")))
recent = [(w, it) for w, it in rows if (now - datetime.datetime.fromtimestamp(upd.get(w, 0))).days <= days]
print("enabled Workshop items: %d (mods %d); updated in the last %d days: %d" % (len(rows), sum(len(it["ids"]) for _, it in rows), days, len(recent)))
for w, it in recent:
    print("%s  %s  %-40s %s" % (w, datetime.datetime.fromtimestamp(upd.get(w, 0)).strftime("%m-%d %H:%M"), it["name"][:40], ",".join(it["ids"])[:70]))
print("written", OUT)

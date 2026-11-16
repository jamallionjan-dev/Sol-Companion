"""Main game mod list: the body Jamal wants (Hotsco's New Body and its size add-on) loads LAST, so its body file and its
clothing definitions win over every other mod that changes the female body or clothing (Female Model Fix, Tomb's Player
Body family, Fluffy Hair, Vanilla Outfits Expanded, Sol's own shoe definitions).
usage: main_body_mod_order.py            shows what would change (nothing is written)
       main_body_mod_order.py apply      backs the list up to 03_BACKUPS and moves the lines
       main_body_mod_order.py restore    puts the backed-up list back
Only the two (or three, with the EX add-on) Hotsco lines move; every other mod keeps its place and nothing is enabled or
disabled. Never run while the game is running."""
import os, re, shutil, subprocess, sys
LIST = r"C:\Users\JAMAL\Zomboid\mods\default.txt"
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BACK = os.path.join(ROOT, "03_BACKUPS", "main_modlist_20261116", "default.before_body_order.txt")
LAST = ["HotscoNewBody", "HNBXS", "HNBS", "HNBL", "HNBXL", "HotscoNewBodyEX"]      # in this order, at the very end
mode = sys.argv[1] if len(sys.argv) > 1 else "show"
if any(n in subprocess.run(["tasklist"], capture_output=True, text=True).stdout for n in ("ProjectZomboid64.exe", "java.exe")):
    sys.exit("refused: the game is running")
if mode == "restore":
    shutil.copy2(BACK, LIST); print("restored the list from " + BACK); sys.exit(0)
text = open(LIST, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in text else "\n"
m = re.search(r"(mods\s*\{" + re.escape(nl) + r")(.*?)(\}" + re.escape(nl) + r")", text, re.S)
if not m: sys.exit("mods block not found")
lines = [l for l in m.group(2).split(nl) if l.strip()]
ids = [re.sub(r"^\s*mod\s*=\s*|,\s*$", "", l) for l in lines]
move = [i for i in LAST if i in ids]
keep = [l for l, i in zip(lines, ids) if i not in move]
new_lines = keep + ["    mod = %s," % i for i in move]
before = [i for i in ids if i in move or i in ("Sol", "TombBody", "TombBodyCompat", "TombBodyCustom", "VanillaOutfitsExpanded", "FemaleModelFix", "FH")]
after_ids = [re.sub(r"^\s*mod\s*=\s*|,\s*$", "", l) for l in new_lines]
print("mods: %d before, %d after (same set: %s)" % (len(ids), len(after_ids), sorted(ids) == sorted(after_ids)))
print("order now  :", " < ".join("%s(%d)" % (i, ids.index(i) + 1) for i in before))
print("order after:", " < ".join("%s(%d)" % (i, after_ids.index(i) + 1) for i in sorted(before, key=after_ids.index)))
if ids == after_ids: print("kept: already in this order"); sys.exit(0)
if mode != "apply": print("nothing written (run with: apply)"); sys.exit(0)
os.makedirs(os.path.dirname(BACK), exist_ok=True)
if not os.path.exists(BACK): shutil.copy2(LIST, BACK)
new = text[:m.start(2)] + nl.join(new_lines) + nl + text[m.end(2):]
open(LIST, "w", encoding="utf-8", newline="").write(new)
print("written; backup: " + BACK)

"""Read-only check of the main game's mod list (C:\\Users\\JAMAL\\Zomboid\\mods\\default.txt):
- what changed against a saved list (optional argument: path of the older list)
- every mod's own `require` line: the required mods are enabled and come BEFORE it
- the body rule: Hotsco's New Body and its size add-on are the last mods
- Viewpoint add-ons come after Viewpoint
usage: check_mod_order.py [older list]"""
import os, re, sys
WS = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\108600"
LOCAL = r"C:\Users\JAMAL\Zomboid\mods"
LIST = os.path.join(LOCAL, "default.txt")


def ids(path): return re.findall(r"mod = ([^,\r\n]+),", open(path, encoding="utf-8").read())


order = ids(LIST)
pos = {m: i + 1 for i, m in enumerate(order)}
info = {}
roots = [os.path.join(WS, w, "mods") for w in os.listdir(WS)] + [LOCAL]
for r in roots:
    if not os.path.isdir(r): continue
    for m in os.listdir(r):
        for sub in ("42", "42.13", "42.12", "42.0", "common", ""):
            p = os.path.join(r, m, sub, "mod.info")
            if not os.path.isfile(p): continue
            t = open(p, encoding="utf-8", errors="replace").read()
            i = re.search(r"(?mi)^id\s*=\s*\\?(.+?)\s*$", t)
            if not i: continue
            d = info.setdefault(i.group(1).strip(), {})
            for k in ("name", "require", "loadModAfter", "loadModBefore", "incompatible"):
                v = re.search(r"(?mi)^%s\s*=\s*(.+?)\s*$" % k, t)
                if v and k not in d: d[k] = v.group(1).strip()


def split(v): return [x.strip().lstrip("\\") for x in re.split(r"[,;]", v or "") if x.strip()]


print("enabled mods: %d (with a mod.info found: %d)" % (len(order), sum(1 for m in order if m in info)))
if len(sys.argv) > 1:
    old = ids(sys.argv[1])
    gone = [m for m in old if m not in pos]; new = [m for m in order if m not in old]
    print("against %s (%d mods): removed %d, added %d" % (os.path.basename(sys.argv[1]), len(old), len(gone), len(new)))
    if gone: print("  removed:", ", ".join(gone))
    if new: print("  added:", ", ".join(new))
    common_old = [m for m in old if m in pos]; common_new = [m for m in order if m in old]
    print("  the mods that stayed are in the same order:", common_old == common_new)
problems = 0
print("--- requirements")
for m in order:
    d = info.get(m, {})
    for r in split(d.get("require")):
        if r not in pos: problems += 1; print("  MISSING: %s (%d) requires %s, which is not enabled" % (m, pos[m], r))
        elif pos[r] > pos[m]: problems += 1; print("  ORDER: %s (%d) requires %s, which comes later (%d)" % (m, pos[m], r, pos[r]))
    for r in split(d.get("loadModAfter")):
        if r in pos and pos[r] > pos[m]: problems += 1; print("  ORDER: %s (%d) asks to load after %s (%d)" % (m, pos[m], r, pos[r]))
    for r in split(d.get("loadModBefore")):
        if r in pos and pos[r] < pos[m]: problems += 1; print("  ORDER: %s (%d) asks to load before %s (%d)" % (m, pos[m], r, pos[r]))
    for r in split(d.get("incompatible")):
        if r in pos: problems += 1; print("  CONFLICT: %s (%d) says it is incompatible with %s (%d)" % (m, pos[m], r, pos[r]))
if not problems: print("  none")
print("--- body rule")
hot = [m for m in ("HotscoNewBody", "HNBXS", "HNBS", "HNBL", "HNBXL", "HotscoNewBodyEX") if m in pos]
tail = order[-len(hot):] if hot else []
print("  Hotsco mods enabled: %s ; last %d mods of the list: %s ; rule kept: %s" % (hot, len(hot), tail, bool(hot) and tail == hot))
body = [m for m in ("FemaleModelFix", "FH", "TombBody", "TombBodyCompat", "TombBodyCustom", "TombWardrobeALT", "VanillaOutfitsExpanded", "Sol", "SpnCloth", "SpnHair") if m in pos]
print("  body and clothing mods before Hotsco:", all(pos[m] < pos[hot[0]] for m in body) if hot else "no Hotsco", "(%s)" % ", ".join("%s %d" % (m, pos[m]) for m in body))
print("--- Viewpoint")
if "Viewpoint" in pos:
    vp = [m for m in order if "iewpoint" in m.lower() and m != "Viewpoint"]
    early = [m for m in vp if pos[m] < pos["Viewpoint"]]
    print("  Viewpoint at %d; add-ons enabled: %d; add-ons placed BEFORE it: %s" % (pos["Viewpoint"], len(vp), early or "none"))
else: print("  Viewpoint is not enabled")
print("  ZombieBuddy at", pos.get("ZombieBuddy", "NOT ENABLED"), "; Sol at", pos.get("Sol", "NOT ENABLED"))

"""Read-only survey: which enabled lab mods shadow vanilla female clothing/body/hair resources, in load order.
usage: survey_body_overrides.py   (reads MODS_LAB_MIN.txt, the workshop folder and the game's media)"""
import os, re, hashlib, collections
LAB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media"
WS = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\108600"
order = re.findall(r"mod = ([^,\r\n]+),", open(os.path.join(LAB, "MODS_LAB_MIN.txt"), encoding="utf-8").read())
# mod id -> media dirs (42 folder and common)
where = {}
roots = [os.path.join(WS, w, "mods") for w in os.listdir(WS)] + [os.path.join(LAB, "profile", "Zomboid", "mods")]
for r in roots:
    if not os.path.isdir(r): continue
    for m in os.listdir(r):
        base = os.path.join(r, m)
        for sub in ("42", "42.0", "common", ""):
            info = os.path.join(base, sub, "mod.info")
            if os.path.isfile(info):
                mid = re.search(r"(?mi)^id\s*=\s*(.+?)\s*$", open(info, encoding="utf-8", errors="replace").read())
                if mid:
                    dirs = [os.path.join(base, s, "media") for s in ("common", "42", "42.0") if os.path.isdir(os.path.join(base, s, "media"))]
                    where.setdefault(mid.group(1).strip().lstrip("\\"), dirs)
                break


def files(root, rel):
    d = os.path.join(root, rel)
    out = {}
    if os.path.isdir(d):
        for dp, _, fs in os.walk(d):
            for f in fs:
                out[os.path.relpath(os.path.join(dp, f), root).replace("\\", "/").lower()] = os.path.join(dp, f)
    return out


def stem(p): return os.path.splitext(p)[0]
AREAS = ["clothing/clothingitems", "models_x/skinned/clothes", "models_x/skinned/hair", "models_x/skinned", "models_x/static/clothes", "hairstyles", "clothing"]
van = {a: {stem(k) for k in files(GAME, a)} for a in AREAS}
print("vanilla counts:", {a: len(v) for a, v in van.items()})
winner = {}
for mid in order:
    dirs = where.get(mid)
    if not dirs: continue
    line = []
    for a in AREAS:
        mine = {}
        for d in dirs: mine.update(files(d, a))
        if a in ("models_x/skinned", "clothing"): mine = {k: v for k, v in mine.items() if k.count("/") == a.count("/") + 1}
        hit = [k for k in mine if stem(k) in van[a]]
        if mine: line.append("%s: %d files, %d shadow vanilla" % (a, len(mine), len(hit)))
        for k in hit: winner[stem(k)] = (mid, mine[k])
    if line: print("%-28s %s" % (mid, " | ".join(line)))
print()
by = collections.Counter(m for m, _ in winner.values())
print("winner (last in load order) per shadowed vanilla resource:", dict(by))
# what do the winning clothingItems XML do to the female model?
def fem(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(r"<m_FemaleModel>(.*?)</m_FemaleModel>", t, re.S)
    b = re.findall(r"<m_BaseTextures>(.*?)</m_BaseTextures>", t, re.S)
    return (m.group(1).strip().lower().replace("\\", "/") if m else ""), tuple(x.strip().lower().replace("\\", "/") for x in b)
vx = files(GAME, "clothing/clothingitems")
chg = collections.Counter(); ex = collections.defaultdict(list)
for k, p in vx.items():
    w = winner.get(stem(k))
    if not w: continue
    a, b = fem(p), fem(w[1])
    kind = ("model" if a[0] != b[0] else "") + ("+tex" if a[1] != b[1] else "")
    chg[(w[0], kind or "same")] += 1
    if kind and len(ex[(w[0], kind)]) < 3: ex[(w[0], kind)].append("%s: %s -> %s" % (os.path.basename(k), a[0] or a[1][:1], b[0] or b[1][:1]))
print("clothingItems winners, female model/texture changed:", dict(chg))
for k, v in ex.items(): print(" ", k, v)
for key in ("models_x/skinned/femalebody", "models_x/skinned/malebody"):
    print(key, "->", winner.get(key, ("vanilla",))[0])
print("meshes at vanilla clothes paths that DIFFER from vanilla bytes:")
gm = files(GAME, "models_x/skinned/clothes")
gh = {stem(k): hashlib.md5(open(p, "rb").read()).hexdigest() for k, p in gm.items()}
dif = collections.Counter()
for s, (mid, p) in winner.items():
    if s in gh: dif[(mid, "same" if hashlib.md5(open(p, "rb").read()).hexdigest() == gh[s] and os.path.splitext(p)[1].lower() == ".x" else "different")] += 1
print(" ", dict(dif))
print("load order of body mods:", [m for m in order if re.search(r"(?i)tomb|hotsco|hnb|spn|femalemodel|^FH$|^Sol$", m)])

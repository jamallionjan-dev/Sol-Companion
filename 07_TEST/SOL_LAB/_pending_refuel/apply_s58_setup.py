"""Game set-up asked for by the Escape From Zomboid Firearms page, plus the Viewpoint view-switch settings. Game closed only, and only on Jamal's yes.
usage: apply_s58_setup.py <world save dir> [--dry]
- EFZPvadsBridge on, after ProjectViewpointADS and EscapeFromZomboidFirearms (Jamal keeps Recoil & ADS and subscribed to the bridge)
- the world's list and the lab list made equal to the game's list
- SWMG loaded before Viewpoint (the EFZ page's order: ZombieBuddy, SWMG, Viewpoint, EscapeFromZomboidFirearms)
- Java memory -Xmx4096m -> -Xmx8192m (the EFZ page: at least 8192m; this PC has 32 GB)
- viewpoint-live.properties: game.releaseIsoChunkTextures=false, chunks.buildBudgetMs=6.0, chunks.buildMaxMs=16.0
Every changed file is copied to _backup\\20261110_before_s58 first."""
import os, re, shutil, sys
LAB = r"C:\Users\JAMAL\Desktop\Sol\07_TEST\SOL_LAB"
Z = LAB + r"\profile\Zomboid"
WORLD, DRY = sys.argv[1], "--dry" in sys.argv
B = LAB + r"\_backup\20261110_before_s58"
LISTS = [Z + r"\mods\default.txt", os.path.join(WORLD, "mods.txt"), LAB + r"\MODS_LAB_MIN.txt"]
ARGS, VP = LAB + r"\sol_lab.args", Z + r"\viewpoint-live.properties"

def read(p): return open(p, encoding="utf-8", newline="").read()
def save(p, t, tag):
    if DRY: print("would change", tag, p); return
    os.makedirs(B, exist_ok=True); shutil.copy(p, os.path.join(B, tag + "_" + os.path.basename(p)))
    open(p, "w", encoding="utf-8", newline="").write(t); print("changed", tag, p)

def fix_list(t):
    nl = "\r\n" if "\r\n" in t else "\n"
    lines = t.split(nl)
    if not any(re.match(r"^\s*mod = EFZPvadsBridge,\s*$", l) for l in lines):     # its mod.info: loadModAfter=ProjectViewpointADS,EscapeFromZomboidFirearms
        last = max(i for i, l in enumerate(lines) if re.match(r"^\s*mod = (ProjectViewpointADS|EscapeFromZomboidFirearms|EscapeFromZomboidFirearmsServer),\s*$", l))
        lines.insert(last + 1, re.sub(r"mod = \w+,", "mod = EFZPvadsBridge,", lines[last]))
    iv = next((i for i, l in enumerate(lines) if re.match(r"^\s*mod = Viewpoint,\s*$", l)), None)
    isw = next((i for i, l in enumerate(lines) if re.match(r"^\s*mod = SWMG,\s*$", l)), None)
    if iv is not None and isw is not None and isw > iv:
        sw = lines.pop(isw); lines.insert(iv, sw)
    return nl.join(lines)

base = fix_list(read(LISTS[0]))                               # the list he set in the game's menu is the one the game loads
for i, p in enumerate(LISTS):
    t = read(p); n = base if i else base
    if n != t: save(p, n, "list%d" % i)
t = read(ARGS); n = t.replace("-Xmx4096m", "-Xmx8192m")
if n != t: save(ARGS, n, "args")
t = read(VP); n = t
for k, v in (("game.releaseIsoChunkTextures", "false"), ("chunks.buildBudgetMs", "6.0"), ("chunks.buildMaxMs", "16.0")):
    n, c = re.subn(r"(?m)^" + re.escape(k) + r"=.*$", k + "=" + v, n)
    assert c == 1, k
if n != t: save(VP, n, "viewpoint")
print("done" + (" (dry)" if DRY else ""))

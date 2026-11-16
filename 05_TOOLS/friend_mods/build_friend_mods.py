"""Builds the friend's mod package (Jamal 2026-11-16): a .bat that turns on, in his friend's game, exactly the mods
Jamal has on now, in the same order, and installs the local fix mod SolFixDGVEyes. Output: a zip on the Desktop.
usage: build_friend_mods.py
Reads Jamal's C:\\Users\\JAMAL\\Zomboid\\mods\\default.txt and the Workshop folder (read only). Writes:
  05_TOOLS\\friend_mods\\out\\Sol-Mods-Friend\\  (ENABLE MODS.bat, files\\...)  and  Desktop\\Sol-Mods-Friend-<date>.zip"""
import datetime, hashlib, io, os, re, shutil, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
WS = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\108600"
LOCAL = r"C:\Users\JAMAL\Zomboid\mods"
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
FIX = os.path.join(LOCAL, "SolFixDGVEyes")
HUD_REL = os.path.join("mods", "DGVViewpointEyes", "42", "media", "lua", "client", "DGVE_Blocks.lua")
VP_REL = os.path.join("mods", "Viewpoint", "42", "media", "java", "client")
BOM = "\ufeff"


def mod_infos(root):
    """mod id -> (folder of the Workshop item or local mod, name)"""
    out = {}
    for dp, dirs, fs in os.walk(root):
        if dp.count(os.sep) - root.count(os.sep) > 5: dirs[:] = []; continue
        if "mod.info" in fs:
            try: t = open(os.path.join(dp, "mod.info"), encoding="utf-8", errors="replace").read()
            except OSError: continue
            i = re.search(r"(?mi)^id\s*=\s*\\?(.+?)\s*$", t); n = re.search(r"(?mi)^name\s*=\s*(.+?)\s*$", t)
            if i: out.setdefault(i.group(1).strip(), (dp, n.group(1).strip() if n else ""))
    return out


order = re.findall(r"mod = ([^,\r\n]+),", open(os.path.join(LOCAL, "default.txt"), encoding="utf-8").read())
ws, loc = mod_infos(WS), mod_infos(LOCAL)
rows, missing = [], []
for m in order:
    if m in ws:
        wid = os.path.relpath(ws[m][0], WS).split(os.sep)[0]; rows.append((m, wid, ws[m][1]))
    elif m in loc:
        rows.append((m, "local", loc[m][1]))
    else:
        missing.append(m)
if missing: sys.exit("mods in Jamal's list that are not on this PC: %s" % missing)
local_ids = [m for m, w, _ in rows if w == "local"]
if set(local_ids) - {"Sol", "SolFixDGVEyes"}: sys.exit("unexpected local mods: %s" % local_ids)
hud = os.path.join(WS, "3838246684", HUD_REL)
hud_sha = hashlib.sha256(open(hud, "rb").read()).hexdigest()
built_from = re.search(r"file ([0-9a-f]{12})", open(os.path.join(FIX, "42", "mod.info"), encoding="utf-8").read()).group(1)
if not hud_sha.startswith(built_from): sys.exit("SolFixDGVEyes is not built from the HUD file on this PC: rebuild it first")
vp_sha = hashlib.sha256(open(os.path.join(WS, "3809306528", VP_REL, "Viewpoint.jar"), "rb").read()).hexdigest()
sol_ver = re.search(r"modversion=(\S+)", open(os.path.join(LOCAL, "Sol", "42", "mod.info"), encoding="utf-8").read()).group(1)

out = os.path.join(HERE, "out", "Sol-Mods-Friend")
if os.path.isdir(out): shutil.rmtree(out)
files = os.path.join(out, "files")
shutil.copytree(FIX, os.path.join(files, "SolFixDGVEyes"))
with io.open(os.path.join(files, "modlist.tsv"), "w", encoding="utf-8", newline="\r\n") as f:
    f.write("# Jamal's mod list, in load order: mod id <TAB> Workshop item (local = installed by this package or by the Sol package) <TAB> name\n")
    for m, w, n in rows: f.write("%s\t%s\t%s\n" % (m, w, n))
with io.open(os.path.join(files, "check.txt"), "w", encoding="utf-8", newline="\r\n") as f:
    f.write("hud_sha256=%s\nviewpoint_bad_sha256=%s\nsol_version=%s\nbuilt=%s\n" % (hud_sha, vp_sha, sol_ver, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
ps = io.open(os.path.join(HERE, "enable_mods.ps1"), encoding="utf-8").read()
io.open(os.path.join(files, "enable_mods.ps1"), "w", encoding="utf-8", newline="\r\n").write(BOM + ps.lstrip(BOM))
bat = io.open(os.path.join(HERE, "ENABLE MODS.bat"), encoding="utf-8").read()
io.open(os.path.join(out, "ENABLE MODS.bat"), "w", encoding="ascii", newline="\r\n").write(bat)
readme = io.open(os.path.join(HERE, "README.txt"), encoding="utf-8").read().replace("{N}", str(len(rows))).replace("{SOL}", sol_ver)
io.open(os.path.join(out, "اقرأني - README.txt"), "w", encoding="utf-8", newline="\r\n").write(BOM + readme.lstrip(BOM))
zname = os.path.join(DESKTOP, "Sol-Mods-Friend-%s.zip" % datetime.date.today().isoformat())
if os.path.exists(zname): os.remove(zname)
with zipfile.ZipFile(zname, "w", zipfile.ZIP_DEFLATED) as z:
    for dp, _, fs in os.walk(out):
        for fn in fs:
            p = os.path.join(dp, fn); z.write(p, os.path.join("Sol-Mods-Friend", os.path.relpath(p, out)))
print("mods %d (Workshop items %d, local %s); zip %s (%d bytes)" % (len(rows), len({w for _, w, _ in rows if w != "local"}), local_ids, zname, os.path.getsize(zname)))

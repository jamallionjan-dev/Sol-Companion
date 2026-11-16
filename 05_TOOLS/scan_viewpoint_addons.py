"""Read-only: which ENABLED mods carry Java code that reaches into Project Viewpoint's own classes, and which of those
touch its shaders (the kind of add-on that stopped Viewpoint 0.1.7 on 2026-11-16: "PVNV cannot patch ...glsl").
usage: scan_viewpoint_addons.py"""
import datetime, glob, os, re, zipfile
WS = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\108600"
LIST = r"C:\Users\JAMAL\Zomboid\mods\default.txt"
order = re.findall(r"mod = ([^,\r\n]+),", open(LIST, encoding="utf-8").read())
enabled = set(order)
vp_jar = os.path.join(WS, "3809306528", "mods", "Viewpoint", "42", "media", "java", "client", "Viewpoint.jar")
vp_time = os.path.getmtime(vp_jar)
rows = []
for info in glob.glob(os.path.join(WS, "*", "mods", "*", "**", "mod.info"), recursive=True):
    t = open(info, encoding="utf-8", errors="replace").read()
    i = re.search(r"(?mi)^id\s*=\s*\\?(.+?)\s*$", t)
    if not i or i.group(1).strip() not in enabled or i.group(1).strip() == "Viewpoint": continue
    mid = i.group(1).strip()
    root = os.path.dirname(info)
    for jar in glob.glob(os.path.join(root, "**", "*.jar"), recursive=True):
        try:
            z = zipfile.ZipFile(jar)
            blob = b"".join(z.read(n) for n in z.namelist() if n.endswith(".class"))
        except Exception:
            continue
        if b"viewpoint/" not in blob and b"viewpoint." not in blob: continue
        refs = set(re.findall(rb"viewpoint[/.](?:[a-z]+[/.])+[A-Z][A-Za-z_$]+", blob))
        shader = [k.decode() for k in (b".glsl", b"GlProgram", b"ShaderPacks", b"cannot patch", b"shader") if k in blob]
        rows.append((mid, os.path.basename(jar), len(refs), shader, os.path.getmtime(jar)))
seen = set()
print("Viewpoint.jar dated", datetime.datetime.fromtimestamp(vp_time).strftime("%Y-%m-%d %H:%M"))
print("enabled add-ons whose Java code uses Viewpoint's own classes (%d):" % len({(r[0], r[1]) for r in rows}))
for mid, jar, refs, shader, mt in sorted(rows, key=lambda r: (-len(r[3]), -r[2])):
    if (mid, jar) in seen: continue
    seen.add((mid, jar))
    age = "older than this Viewpoint" if mt < vp_time - 3600 else "same day or newer"
    print("  %-36s %-32s classes %3d | shaders: %-28s | %s (%s)" % (mid, jar[:32], refs, ",".join(shader) or "-", datetime.datetime.fromtimestamp(mt).strftime("%m-%d"), age))

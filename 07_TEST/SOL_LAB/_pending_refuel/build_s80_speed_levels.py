"""s80 speed_levels, Java side: a copy of SolCombined.jar whose SCDriveControl lets a cruise reach 70 km/h (was 50).

Living Fellows' SCDriveControl.clampCruise holds every cruise to MAX_CRUISE_KMH = 50 (javap of the lab jar), so 65 never
reached the pedals. The installed class is byte-identical to LF's published source compiled with --release 17 (checked
here again before anything is built); the only change is that one constant. Nothing else in the jar is touched: the
road follower, lane scan and companion driver already scale their look-ahead with the cruise (see SolSpeedGov.lua).
SCBridge keeps two inlined 50s: the convoy follow check (driveFollowVehicle, not used by the GPS) and the status field
maxCruiseKmh (read by no Lua).

  out dir:  SolCombined.jar (the copy), SCDriveControl.class, orig/ and new/ javap listings
usage: build_s80_speed_levels.py <out dir> [deploy]     ('deploy' copies it into the lab: game closed only, ZB approval)"""
import os, re, shutil, subprocess, sys, tempfile, zipfile
ROOT = r"C:\Users\JAMAL\Desktop\Sol"
JAR = ROOT + r"\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\java\SolCombined.jar"
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\projectzomboid.jar"
JDK = r"C:\Program Files\Eclipse Adoptium\jdk-25.0.4.101-hotspot\bin"
SRC = (ROOT + r"\03_BACKUPS\Sol_BACKUP_BEFORE_LIVING_FELLOWS_20261020_191529\00_RESEARCH_COMMUNITY\living-fellows\bridge"
       r"\src\main\java\survivorcompanion\bridge\SCDriveControl.java")
ENTRY = "survivorcompanion/bridge/SCDriveControl.class"
OLD, NEW = "static final float MAX_CRUISE_KMH = 50.0f;", "static final float MAX_CRUISE_KMH = 70.0f; // Sol s80 speed_levels (was 50)"


def run(c):
    r = subprocess.run(c, capture_output=True, text=True)
    if r.returncode: print(r.stdout.strip()); print(r.stderr.strip()); sys.exit("failed: " + " ".join(os.path.basename(x) for x in c[:2]))
    return r.stdout


def javap(cls_file):
    return run([JDK + r"\javap.exe", "-c", "-p", "-constants", cls_file])


def compile_src(text, out):
    d = tempfile.mkdtemp(prefix="s80src_")
    os.makedirs(os.path.join(d, "survivorcompanion", "bridge"))
    p = os.path.join(d, "survivorcompanion", "bridge", "SCDriveControl.java")
    open(p, "w", encoding="utf-8", newline="").write(text)
    run([JDK + r"\javac.exe", "--release", "17", "-nowarn", "-encoding", "UTF-8", "-d", out, p])
    return os.path.join(out, *ENTRY.split("/"))


OUT = os.path.abspath(sys.argv[1])
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
src = open(SRC, encoding="utf-8").read()
assert src.count(OLD) == 1, "SCDriveControl source changed"
with zipfile.ZipFile(JAR) as z: live = z.read(ENTRY)
open(os.path.join(OUT, "live.class"), "wb").write(live)
same = compile_src(src, os.path.join(OUT, "orig"))
assert open(same, "rb").read() == live, "the lab's SCDriveControl is not LF's source any more: stop"
print("orig: LF source recompiles byte-identical to the lab jar's SCDriveControl")
new = compile_src(src.replace(OLD, NEW), os.path.join(OUT, "new"))
a, b = javap(same), javap(new)
diff = [l for l in set(b.splitlines()) ^ set(a.splitlines())]
assert all(re.search(r"50\.0|70\.0", l) for l in diff), diff
print("javap difference only in the ceiling:", sorted(set(l.strip() for l in diff)))
shutil.copy(new, os.path.join(OUT, "SCDriveControl.class"))
nb = open(new, "rb").read()
out_jar = os.path.join(OUT, "SolCombined.jar")
with zipfile.ZipFile(JAR) as zi, zipfile.ZipFile(out_jar, "w", zipfile.ZIP_DEFLATED) as zo:
    for info in zi.infolist():
        zo.writestr(info, nb if info.filename == ENTRY else zi.read(info.filename), compress_type=zipfile.ZIP_DEFLATED)
print("built", out_jar)
for gate in ("linkcheck.py", "patch_access_check.py"):
    args = [sys.executable, "-I", os.path.join(ROOT, "05_TOOLS", "sol_kahlua", gate)] + ([GAME, out_jar] if gate == "linkcheck.py" else [out_jar])
    print(gate, "pass", run(args).strip().splitlines()[-1:])
if len(sys.argv) > 2 and sys.argv[2] == "deploy":
    if "projectzomboid" in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower() or \
            "java.exe" in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower():
        sys.exit("game is running")
    shutil.copy(JAR, JAR + ".before_s80")
    shutil.copy(out_jar, JAR)
    print("deployed (backup: SolCombined.jar.before_s80)")

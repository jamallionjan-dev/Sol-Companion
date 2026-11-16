"""Build the corrected s113 Java classes into a new candidate jar; never installs it."""
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = r"C:\Users\JAMAL\Desktop\Sol"
PZDIR = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid"
GAME = PZDIR + r"\projectzomboid.jar"
ZB = PZDIR + r"\ZombieBuddy.jar"
LAB = ROOT + r"\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\java\SolCombined.jar"
SRC = ROOT + r"\05_TOOLS\sol_nav_java\localplayerbody"
JDK = r"C:\Program Files\Eclipse Adoptium\jdk-25.0.4.101-hotspot\bin"
OUT = os.path.join(os.path.dirname(__file__), "build_s113_physical")
ENTRY = "localplayerbody/SolHeadshot"

if os.path.exists(OUT):
    raise SystemExit("candidate output already exists; refusing to overwrite: " + OUT)
os.makedirs(os.path.join(OUT, "classes"))
os.makedirs(os.path.join(OUT, "tests"))

def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.stdout.strip():
        print(p.stdout.strip())
    if p.returncode:
        if p.stderr.strip():
            print(p.stderr.strip())
        raise SystemExit("failed: " + os.path.basename(args[0]))

orig = os.path.join(OUT, "SolCombined.orig.jar")
shutil.copyfile(LAB, orig)
cp = GAME + ";" + ZB + ";" + orig
classes = os.path.join(OUT, "classes")
tests = os.path.join(OUT, "tests")
run([JDK + r"\javac.exe", "-nowarn", "-encoding", "UTF-8", "-cp", cp, "-d", classes,
     os.path.join(SRC, "SolHeadshot.java")])
run([JDK + r"\javac.exe", "-nowarn", "-encoding", "UTF-8", "-cp", classes + ";" + cp, "-d", tests,
     os.path.join(SRC, "SolHeadshotTest.java")])
run([JDK + r"\java.exe", "-cp", tests + ";" + classes + ";" + cp, "localplayerbody.SolHeadshotTest"])

add = {}
for name in os.listdir(os.path.join(classes, "localplayerbody")):
    if name.startswith("SolHeadshot") and name.endswith(".class"):
        add["localplayerbody/" + name] = open(os.path.join(classes, "localplayerbody", name), "rb").read()
if "localplayerbody/SolHeadshot$HeadPartSelection.class" not in add:
    raise SystemExit("compiled head-selection advice not found")

candidate = os.path.join(OUT, "SolCombined.jar")
with zipfile.ZipFile(orig) as zi, zipfile.ZipFile(candidate, "w", zipfile.ZIP_DEFLATED) as zo:
    for info in zi.infolist():
        if info.filename not in add:
            zo.writestr(info, zi.read(info.filename), compress_type=zipfile.ZIP_DEFLATED)
    for name, data in add.items():
        zo.writestr(name, data)

run([sys.executable, "-I", ROOT + r"\05_TOOLS\sol_kahlua\linkcheck.py", GAME, candidate])
run([sys.executable, "-I", ROOT + r"\05_TOOLS\sol_kahlua\patch_access_check.py", candidate])
digest = hashlib.sha256(open(candidate, "rb").read()).hexdigest()
print("candidate", candidate)
print("class entries", len(add), "sha256", digest)
print("not installed; install only after the game process exits")

"""Build SolDebugGuard into a copy of SolCombined.jar and run the link and patch-access gates.
usage: build_guard.py <out dir> [deploy]   ('deploy' copies it into the lab, game closed only)"""
import glob, os, shutil, subprocess, sys, zipfile
ROOT = r"C:\Users\JAMAL\Desktop\Sol"
JAVA = ROOT + r"\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\java\SolCombined.jar"
GAME_D = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid"
GAME, ZB = GAME_D + r"\projectzomboid.jar", GAME_D + r"\ZombieBuddy.jar"
JDK = r"C:\Program Files\Eclipse Adoptium\jdk-25.0.4.101-hotspot\bin"
OUT = sys.argv[1]
def run(c):
    r = subprocess.run(c, capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode:
        print(r.stderr.strip()); sys.exit("failed: " + os.path.basename(c[1] if c[0] == sys.executable else c[0]))
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT + r"\c")
run([JDK + r"\javac.exe", "-nowarn", "-encoding", "UTF-8", "-cp", GAME + ";" + ZB, "-d", OUT + r"\c", ROOT + r"\05_TOOLS\sol_nav_java\localplayerbody\SolDebugGuard.java"])
add = {"localplayerbody/" + os.path.basename(f): open(f, "rb").read() for f in glob.glob(OUT + r"\c\localplayerbody\*.class")}
print("built", sorted(add))
new = OUT + r"\SolCombined.jar"
with zipfile.ZipFile(JAVA) as zi, zipfile.ZipFile(new, "w", zipfile.ZIP_DEFLATED) as zo:
    for info in zi.infolist():
        if info.filename in add: continue
        zo.writestr(info, zi.read(info.filename), compress_type=zipfile.ZIP_DEFLATED)
    for n, b in add.items():
        zo.writestr(n, b)
run([sys.executable, "-I", ROOT + r"\05_TOOLS\sol_kahlua\linkcheck.py", GAME, new])
run([sys.executable, "-I", ROOT + r"\05_TOOLS\sol_kahlua\patch_access_check.py", new])
if len(sys.argv) > 2 and sys.argv[2] == "deploy":
    if "java.exe" in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower():
        sys.exit("game is running")
    shutil.copy(new, JAVA)
    print("deployed")

"""far_arrival Java: build SolCarArrive (+ SolCarArriveCore) and SolCarMove (its streamer hook now also runs SolCarArrive.onStreamer) with the
classes they share into a COPY of SolCombined.jar, run SolCarArriveCoreTest and the existing SolCarMoveCoreTest on a COPY of vehicles.db,
then the link and patch-access gates on the copy. far_meta: also SolCarsNearCoreTest (a car kept in meta is listed with its own verdict). Never deploys: installing the jar is a separate step with the game closed, and
ZombieBuddy will ask to approve the changed jar on the next start.
usage: build_far_arrive.py <out dir> <copy of vehicles.db>"""
import glob, os, shutil, subprocess, sys, zipfile, hashlib
ROOT = r"C:\Users\JAMAL\Desktop\Sol"
JAVA = ROOT + r"\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\java\SolCombined.jar"
GAME_D = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid"
GAME, ZB = GAME_D + r"\projectzomboid.jar", GAME_D + r"\ZombieBuddy.jar"
JDK = r"C:\Program Files\Eclipse Adoptium\jdk-25.0.4.101-hotspot\bin"
SRC = ROOT + r"\05_TOOLS\sol_nav_java\localplayerbody"
OUT, DB = sys.argv[1], sys.argv[2]
if os.path.normcase(os.path.abspath(DB)).startswith(os.path.normcase(ROOT + r"\07_TEST\SOL_LAB\profile")):
    sys.exit("give a COPY of vehicles.db, not the save's own file")
def run(c):
    r = subprocess.run(c, capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode:
        print(r.stderr.strip()); sys.exit("failed: " + " ".join(os.path.basename(x) for x in c[:3]))
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT + r"\c"); os.makedirs(OUT + r"\t")
jar_copy = OUT + r"\SolCombined.orig.jar"
shutil.copy(JAVA, jar_copy)                                                     # read the lab jar once, as a copy
cp = GAME + ";" + ZB + ";" + jar_copy
MAIN = ["SolCarMove.java", "SolCarMoveCore.java", "SolCarsNear.java", "SolCarsNearCore.java", "SolCarBlob.java", "SolCarArrive.java", "SolCarArriveCore.java"]
run([JDK + r"\javac.exe", "-nowarn", "-encoding", "UTF-8", "-cp", cp, "-d", OUT + r"\c"] + [SRC + "\\" + f for f in MAIN])
run([JDK + r"\javac.exe", "-nowarn", "-encoding", "UTF-8", "-cp", OUT + r"\c;" + cp, "-d", OUT + r"\t", SRC + r"\SolCarArriveCoreTest.java", SRC + r"\SolCarMoveCoreTest.java", SRC + r"\SolCarsNearCoreTest.java"])
tcp = OUT + r"\t;" + OUT + r"\c;" + cp
run([JDK + r"\java.exe", "-cp", tcp, "localplayerbody.SolCarArriveCoreTest", DB])
run([JDK + r"\java.exe", "-cp", tcp, "localplayerbody.SolCarMoveCoreTest", DB])
run([JDK + r"\java.exe", "-cp", tcp, "localplayerbody.SolCarsNearCoreTest", DB])                  # far_meta: the 16th field for a car kept in meta
add = {"localplayerbody/" + os.path.basename(f): open(f, "rb").read() for f in glob.glob(OUT + r"\c\localplayerbody\*.class")}
print("built", sorted(add))
new = OUT + r"\SolCombined.jar"
with zipfile.ZipFile(jar_copy) as zi, zipfile.ZipFile(new, "w", zipfile.ZIP_DEFLATED) as zo:
    for info in zi.infolist():
        if info.filename in add: continue
        zo.writestr(info, zi.read(info.filename), compress_type=zipfile.ZIP_DEFLATED)
    for n, b in add.items():
        zo.writestr(n, b)
run([sys.executable, "-I", ROOT + r"\05_TOOLS\sol_kahlua\linkcheck.py", GAME, new])
run([sys.executable, "-I", ROOT + r"\05_TOOLS\sol_kahlua\patch_access_check.py", new])
print("staged jar", new, "sha256", hashlib.sha256(open(new, "rb").read()).hexdigest()[:16], "(ZombieBuddy approval needed when installed)")

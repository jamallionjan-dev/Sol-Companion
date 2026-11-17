"""s161 body_scope: Sol's body (and her under-cloth chest) only for Sol, not for every female NPC.
usage: python apply_s161_body_scope.py [--lab-only]
Installs out/s161/SolCombined.jar (the installed jar + the new SolNPCAdapter.class) into the main game and the lab,
after backing up each old jar to 03_BACKUPS, and adds the line body_scope=on to SolFixes_MAIN.txt / SolFixes_LAB.txt.
Idempotent; refuses while the game runs. ZombieBuddy asks once to Allow the changed SolCombined.jar."""
import hashlib, os, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
NEW = os.path.join(HERE, "out", "s161", "SolCombined.jar")
BASE = os.path.join(HERE, "out", "s161", "SolCombined.in.jar")
TARGETS = [
    (r"C:\Users\JAMAL\Zomboid\mods\Sol\42\media\java\SolCombined.jar", r"C:\Users\JAMAL\Zomboid\Lua\SolFixes_MAIN.txt"),
    (os.path.join(ROOT, r"07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media\java\SolCombined.jar"),
     os.path.join(ROOT, r"07_TEST\SOL_LAB\profile\Zomboid\Lua\SolFixes_LAB.txt")),
]
if "--lab-only" in sys.argv: TARGETS = TARGETS[1:]
if any(n in subprocess.run(["tasklist"], capture_output=True, text=True).stdout for n in ("ProjectZomboid64.exe", "java.exe")):
    sys.exit("refused: the game is running")
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
new, base = sha(NEW), sha(BASE)
bak = os.path.join(ROOT, "03_BACKUPS", "s161_body_scope_" + time.strftime("%Y%m%d_%H%M%S"))
for jar, switches in TARGETS:
    cur = sha(jar)
    if cur == new:
        print("jar already installed:", jar)
    elif cur != base:
        print("SKIPPED (this jar is not the one the fix was built from):", jar); continue
    else:
        os.makedirs(bak, exist_ok=True)
        shutil.copy2(jar, os.path.join(bak, ("main" if "JAMAL\\Zomboid" in jar else "lab") + "_SolCombined.jar"))
        shutil.copy2(NEW, jar); print("installed:", jar)
    text = open(switches, encoding="utf-8").read() if os.path.exists(switches) else ""
    if "body_scope=" in text:
        print("switch line already there:", switches)
    else:
        with open(switches, "a", encoding="utf-8", newline="") as f:
            f.write(("" if text.endswith("\n") or not text else "\r\n") + "body_scope=on\r\n")
        print("switch body_scope=on added:", switches)
print("backup:", bak if os.path.isdir(bak) else "(nothing replaced)")

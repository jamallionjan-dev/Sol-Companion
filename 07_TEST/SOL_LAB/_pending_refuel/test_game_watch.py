"""Sol Mind goes away with the game, by itself, and a second one refuses to run."""
import os, subprocess, sys, tempfile, time
M = r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind"
sys.path.insert(0, M)
import game_watch as W
PY = sys.executable
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
ck("this process is alive", W.process_alive(os.getpid()))
ck("no pid is not alive", W.process_alive(0) is False)
d = subprocess.Popen([PY, "-c", "import time; time.sleep(120)"])
ck("a running process is alive", W.process_alive(d.pid))
w = W.Watch(d.pid); ck("watch: game there", not w.game_is_gone())
d.kill(); d.wait(); ck("watch: game gone", w.game_is_gone())
tmp = tempfile.mkdtemp(prefix="sol_watch_")
hb = os.path.join(tmp, "beat.txt")
w = W.Watch(0, hb); ck("no heartbeat yet: waits, does not quit", not w.game_is_gone())
open(hb, "w").close(); ck("beating", not w.game_is_gone() and w.seen)
old = time.time() - 120; os.utime(hb, (old, old)); ck("stopped beating: gone", w.game_is_gone())
w2 = W.Watch(0, hb); ck("an old file from a past session does not close a fresh start", not w2.game_is_gone())

game = subprocess.Popen([PY, "-c", "import time; time.sleep(120)"])
open(os.path.join(tmp, "SolAI_Outbox.txt"), "w").close(); open(os.path.join(tmp, "SolAI_Inbox.txt"), "w").close()
mind = subprocess.Popen([PY, os.path.join(M, "sol_mind.py"), "--lua-dir", tmp, "--headless", "--game-pid", str(game.pid)], cwd=M, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
time.sleep(5)
ck("the Mind runs while the game does", mind.poll() is None, mind.poll())
second = subprocess.run([PY, os.path.join(M, "sol_mind.py"), "--lua-dir", tmp, "--headless", "--game-pid", str(game.pid)], cwd=M, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
ck("a second Mind refuses", second.returncode == 2, (second.returncode, second.stdout[-200:]))
t0 = time.time(); game.kill(); game.wait()
try:
    mind.wait(timeout=8); took = time.time() - t0
    ck("the Mind exits by itself within 5 s (%.1f s)" % took, took <= 5.0, took)
    ck("cleanly", mind.returncode == 0, mind.returncode)
except subprocess.TimeoutExpired:
    mind.kill(); ck("the Mind exits by itself", False, "still running after 8 s")
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED %d: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)

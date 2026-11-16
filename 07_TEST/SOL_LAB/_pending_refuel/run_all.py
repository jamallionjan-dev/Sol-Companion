"""Every offline test here, one summary. Offline PASS is not Runtime PASS."""
import glob, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
tests = sorted(glob.glob(os.path.join(HERE, "test_*.py")))
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
fails = []
for t in tests:
    t0 = time.time()
    r = subprocess.run([sys.executable, t], capture_output=True, encoding="utf-8", errors="replace", cwd=HERE, env=env, timeout=500)
    out = (r.stdout or "") + (r.stderr or "")
    bad = [l for l in out.splitlines() if l.startswith("FAIL")]
    ok = r.returncode == 0 and not bad
    print("%-34s %s  pass=%d fail=%d  %.1fs" % (os.path.basename(t), "ok " if ok else "BAD", out.count("\nPASS") + out.startswith("PASS"), len(bad), time.time() - t0))
    if not ok:
        fails.append(os.path.basename(t))
        for l in bad[:12]: print("    " + l[:200])
        if not bad: print("    " + out[-500:].replace("\n", "\n    "))
print("SUMMARY", "ALL PASS" if not fails else "FAILED: " + " ".join(fails))
sys.exit(1 if fails else 0)

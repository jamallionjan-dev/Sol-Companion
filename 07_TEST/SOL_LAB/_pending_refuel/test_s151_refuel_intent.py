"""s151 installer replay from the pre-change backup, idempotence and source parity."""
import os, py_compile, shutil, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
BACKUP = os.path.join(ROOT, "07_TEST", "SOL_LAB", "_backup", "20261114_before_s151_refuel_fix", "05_TOOLS", "sol_mind")
LIVE = os.path.join(ROOT, "05_TOOLS", "sol_mind")
NAMES = ("intent_engine.py", "chat_service.py", "model_router.py")
assert all(os.path.isfile(os.path.join(BACKUP, n)) for n in NAMES), "s151 pre-change backup is missing"
tmp = tempfile.mkdtemp(prefix="sol_s151_")
for n in NAMES: shutil.copy2(os.path.join(BACKUP, n), tmp)
script = os.path.join(HERE, "apply_s151_refuel_intent.py")
subprocess.run([sys.executable, script, tmp], check=True)
first = {n: open(os.path.join(tmp, n), "rb").read() for n in NAMES}
subprocess.run([sys.executable, script, tmp], check=True)
assert first == {n: open(os.path.join(tmp, n), "rb").read() for n in NAMES}, "installer is not idempotent"
assert all(first[n] == open(os.path.join(LIVE, n), "rb").read() for n in NAMES), "installer output differs from LAB Mind"
for n in NAMES: py_compile.compile(os.path.join(tmp, n), doraise=True)
sys.path.insert(0, tmp)
import intent_engine as IE
can = IE.parse_high_confidence("سول عبي بدونات البنزين من الكازية")
car = IE.parse_high_confidence("سول عبي السيارة بنزين من الكازية")
assert can and can["slots"]["target"] == "can", can
assert car and car["slots"]["target"] == "car", car
print("s151 installer replay PASS; idempotent; source parity; py_compile; can/car intent PASS")

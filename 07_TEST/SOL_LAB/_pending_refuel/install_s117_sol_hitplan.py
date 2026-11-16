"""Install s117 only into SOL_LAB after the game is fully closed; keep a timestamped jar backup."""
import hashlib
import os
import shutil
import time

ROOT = r"C:\Users\JAMAL\Desktop\Sol"
LAB_ROOT = os.path.join(ROOT, "07_TEST", "SOL_LAB")
PROFILE = os.path.join(LAB_ROOT, "profile", "Zomboid")
LOG = os.path.join(PROFILE, "Logs", "2026-11-12_16-10_DebugLog.txt")
TARGET = os.path.join(PROFILE, "mods", "Sol_LAB", "42", "media", "java", "SolCombined.jar")
CANDIDATE = os.path.join(os.path.dirname(__file__), "build_s117_sol_hitplan_candidate", "SolCombined.jar")
BACKUP = os.path.join(LAB_ROOT, "_backup", "20261112_before_s117_sol_hitplan")
EXPECTED_BASE = "c8bb708f516bae02a285a5b1ea0560c1af3401d5ead1cfb786a072b10b6ae254"
EXPECTED_CANDIDATE = "bacce36b672718cc450b20ea3970094f0854e93df75875e28de11c743e1285fc"

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

if not os.path.isfile(CANDIDATE) or sha(CANDIDATE) != EXPECTED_CANDIDATE:
    raise SystemExit("candidate missing or hash mismatch; rebuild s117 first")
if not os.path.isfile(TARGET) or sha(TARGET) != EXPECTED_BASE:
    raise SystemExit("LAB jar differs from the known s116 base; refusing to replace it")
if not os.path.isfile(LOG):
    raise SystemExit("expected LAB debug log is missing; refusing install without session check")
if time.time() - os.path.getmtime(LOG) < 60:
    raise SystemExit("LAB debug log is still fresh; close the game and retry")

if os.path.exists(BACKUP):
    raise SystemExit("backup folder already exists; refusing to overwrite: " + BACKUP)
os.makedirs(BACKUP)
backup_jar = os.path.join(BACKUP, "SolCombined.s116.jar")
shutil.copy2(TARGET, backup_jar)
if sha(backup_jar) != EXPECTED_BASE:
    raise SystemExit("backup verification failed; target was not changed")
staged = TARGET + ".s117.tmp"
shutil.copyfile(CANDIDATE, staged)
if sha(staged) != EXPECTED_CANDIDATE:
    os.remove(staged)
    raise SystemExit("staged candidate hash mismatch; target was not changed")
os.replace(staged, TARGET)
if sha(TARGET) != EXPECTED_CANDIDATE:
    raise SystemExit("installed jar verification failed; restore from " + backup_jar)
print("installed s117 into SOL_LAB only")
print("backup", backup_jar)
print("candidate_sha256", sha(TARGET))

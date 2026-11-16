"""One-time cleanup Jamal approved on 2026-11-16 ("delete the safe set"): old, duplicated or superseded backup copies.
usage: cleanup_20261116.py            lists what would go and checks it (nothing is deleted)
       cleanup_20261116.py delete     deletes exactly that list
Refuses if any listed path holds a file tracked by git, or resolves outside the project. Kept on purpose: the 0.28.8
pre-install backups, 02_STABLE, releases 0.28.7 and 0.28.8, Sol-0.28.8.zip, this week's lab backups, the small backups."""
import os, re, shutil, stat, subprocess, sys
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DELETE = len(sys.argv) > 1 and sys.argv[1] == "delete"
KEEP_RELEASES = {"SOL_2026-11-15_0.28.7", "SOL_2026-11-16_0.28.8"}
items = [
    "03_BACKUPS/Sol_BACKUP_BEFORE_LIVING_FELLOWS_20261020_191529",
    "04_ARCHIVE/Sol_SUPERSEDED_20261020_192445",
    "03_BACKUPS/Sol_WORK_BEFORE_VSGIRL_DEDUPE_20261022_063144",
    "03_BACKUPS/Sol_LIVE_BEFORE_VSGIRL_DEDUPE_20261022_063144",
    "03_BACKUPS/Sol_BACKUP_LOCAL_BEFORE_LATEST_20261022_005045",
    "01_WORK/INTEGRATION/SOL_2026-11-14_0.28.6_ERRORFIX",
    "07_TEST/SOL_LAB/_backup/20261114_before_heli_route_speed_fix",
    "07_TEST/SOL_LAB/_backup/20261114_before_heli_route_speed_fix_complete",
    "08_PUBLIC/Sol-0.28.3.zip",
    "08_PUBLIC/Sol-0.28.7.zip",
]
for d in sorted(os.listdir(os.path.join(ROOT, "03_BACKUPS"))):
    if re.match(r"^Sol_(install|WORK)_before_(0\.27\.0|0\.28\.0|0\.28\.1|0\.28\.2|0\.28\.3)_\d{8}$", d): items.append("03_BACKUPS/" + d)
for d in sorted(os.listdir(os.path.join(ROOT, "01_WORK", "RELEASE"))):
    if d not in KEEP_RELEASES: items.append("01_WORK/RELEASE/" + d)


def size(p):
    if os.path.isfile(p): return os.path.getsize(p), 1
    t = n = 0
    for dp, _, fs in os.walk(p):
        for f in fs:
            try: t += os.path.getsize(os.path.join(dp, f)); n += 1
            except OSError: pass
    return t, n


def force(func, path, exc):
    os.chmod(path, stat.S_IWRITE); func(path)


total = files = 0
todo = []
for rel in items:
    p = os.path.normpath(os.path.join(ROOT, rel))
    if not p.startswith(ROOT + os.sep): sys.exit("outside the project: " + rel)
    if not os.path.exists(p): print("  (already gone) " + rel); continue
    tracked = subprocess.run(["git", "-C", ROOT, "ls-files", "--", rel], capture_output=True, text=True).stdout.strip()
    if tracked: sys.exit("REFUSED, tracked by git: " + rel)
    s, n = size(p); total += s; files += n; todo.append((p, rel, s))
    print("  %8.1f MB  %s" % (s / 1e6, rel))
print("%d items, %d files, %.2f GB" % (len(todo), files, total / 1e9))
if not DELETE: print("nothing deleted (run with: delete)"); sys.exit(0)
failed = 0
for p, rel, s in todo:
    try:
        if os.path.isfile(p): os.chmod(p, stat.S_IWRITE); os.remove(p)
        else: shutil.rmtree(p, onerror=force)
    except Exception as e:
        failed += 1; print("FAILED " + rel + ": " + str(e))
print("deleted %d of %d items" % (len(todo) - failed, len(todo)))

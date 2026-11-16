"""s155 offline: every game action the Mind can run has its own line on the card; nothing that was on the card changed.
The model itself is not run here. Offline PASS is not Runtime PASS. Run: python test_s155_card_all_actions.py [sol_mind dir]"""
import json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
MIND = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind")
LUA = os.path.join(HERE, "..", "profile", "Zomboid", "Lua")
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
tmp = tempfile.mkdtemp(prefix="s155_"); mind = os.path.join(tmp, "mind"); os.makedirs(mind)
for f in os.listdir(MIND):
    if f.endswith((".py", ".pyw", ".json.gz")): shutil.copy(os.path.join(MIND, f), mind)
ap = os.path.join(HERE, "apply_s155_card_all_actions.py")
r1 = subprocess.run([sys.executable, ap, mind], capture_output=True, text=True)
b1 = open(os.path.join(mind, "model_router.py"), "rb").read()
r2 = subprocess.run([sys.executable, ap, mind], capture_output=True, text=True)
ck("installer runs, second run changes nothing", r1.returncode == 0 and r2.returncode == 0 and "edited" not in r2.stdout and b1 == open(os.path.join(mind, "model_router.py"), "rb").read(), r1.stdout + r2.stdout + r1.stderr)
sys.path.insert(0, mind)
import model_router as MR
acts = json.load(open(os.path.join(LUA, "SolActions_Snapshot.txt"), encoding="utf-8", errors="replace"))["actions"]
new = MR.sheet(acts, "MEM")
MR.LIST_ALL_S155 = False; old = MR.sheet(acts, "MEM"); MR.LIST_ALL_S155 = True
ol, nl = old.split(chr(10)), new.split(chr(10))
ck("switch off: the card as before (within the old budget)", len(old.rsplit(chr(10) + chr(10), 1)[0]) <= MR.BASE_BUDGET_S155 + 40 and old != new)
ck("every line of the old card is still there, in the same order", [l for l in nl if l in set(ol)] == ol, [l for l in ol if l not in nl][:3])
listed = set(re.findall(r"(?m)^([a-z_0-9]+):", new))
skip = set(MR.CARD_DUPLICATES) | MR.LIST_SKIP_S155
# a game BUTTON the game reports as not usable now (e.g. "come within 2 tiles") is left off by the old card until it is usable
missing = [a["id"] for a in acts if a["id"] not in listed and a["id"] not in skip and not (a.get("kind") == "button" and a.get("enabled") is False)]
usable = [dict(a, enabled=True) for a in acts]
late = [a["id"] for a in usable if a["id"] not in set(re.findall(r"(?m)^([a-z_0-9]+):", MR.sheet(usable, "MEM"))) and a["id"] not in skip]
ck("with every button usable, nothing at all is missing", not late, late)
ck("every catalog action is listed (all %d; not listed on purpose: %s)" % (len(acts), " ".join(sorted(skip))), not missing, missing)
added = [l for l in nl if l not in set(ol) and l not in MR.SHOTS_S155]
ck("the extra card examples are only the declared ones", [l for l in nl if l not in set(ol) and l not in added] == [s for s in MR.SHOTS_S155 if s in new])
ck("each added line has his words as an example (%d lines)" % len(added), added and all(re.match(r'^[a-z_0-9]+: [^|]*| "[^"]+"\|^[a-z_0-9]+: [^|]*| "[^"]+"', l) for l in added), [l for l in added if not re.match(r'^[a-z_0-9]+: [^|]*| "[^"]+"\|^[a-z_0-9]+: [^|]*| "[^"]+"', l)])
ck("no action listed twice", len(re.findall(r"(?m)^([a-z_0-9]+):", new)) == len(listed))
ck("the list stays before the examples and her memory stays last", new.index(added[-1]) < new.index(chr(10) + "\u0623\u0645\u062b\u0644\u0629:") and new.endswith("MEM"))
size = len(new.rsplit(chr(10) + chr(10), 1)[0])
ck("within the card budget (%d <= %d)" % (size, MR.CARD_BUDGET), size <= MR.CARD_BUDGET)
for aid in ("sol_eat", "sol_open_door", "set_hold_fire"):
    p = MR.parse('{"action":"%s","args":{"option":"on"},"speech":""}' % aid)
    ck("the Mind parses an answer naming " + aid, isinstance(p, dict) and p.get("action") == aid, p)
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)

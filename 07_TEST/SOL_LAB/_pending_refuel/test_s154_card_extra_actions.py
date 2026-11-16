"""s154 offline: actions that are not on the card reach the model only with the message that asks for them.
Uses the lab's action snapshot and s82_route_eval.json (the 114 live-eval lines). The model itself is not run here:
this proves what the card contains, not how a model answers. Offline PASS is not Runtime PASS.
Run: python test_s154_card_extra_actions.py [sol_mind dir]"""
import json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
MIND = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind")
LUA = os.path.join(HERE, "..", "profile", "Zomboid", "Lua")
FAIL, PASSED = [], []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    (PASSED if c else FAIL).append(n)
tmp = tempfile.mkdtemp(prefix="s154_")
os.environ["LOCALAPPDATA"] = os.path.join(tmp, "appdata"); os.makedirs(os.environ["LOCALAPPDATA"])
mind = os.path.join(tmp, "mind"); os.makedirs(mind)
for f in os.listdir(MIND):
    if f.endswith((".py", ".pyw", ".json.gz")): shutil.copy(os.path.join(MIND, f), mind)
sw = os.path.join(tmp, "SolFixes_LAB.txt"); open(sw, "w", newline="").write("model_first=on\r\n")
ap = os.path.join(HERE, "apply_s154_card_extra_actions.py")
r1 = subprocess.run([sys.executable, ap, mind, sw], capture_output=True, text=True)
snap = {f: open(os.path.join(mind, f), "rb").read() for f in ("model_router.py", "chat_service.py")}
r2 = subprocess.run([sys.executable, ap, mind, sw], capture_output=True, text=True)
ck("installer runs", r1.returncode == 0, r1.stdout + r1.stderr)
ck("installer second run changes nothing", r2.returncode == 0 and "edited" not in r2.stdout and snap == {f: open(os.path.join(mind, f), "rb").read() for f in snap}, r2.stdout + r2.stderr)
ck("switch written once", open(sw).read().count("card_extra_actions=on") == 1)
sys.path.insert(0, mind)
import model_router as MR
if hasattr(MR, "LIST_ALL_S155"): MR.LIST_ALL_S155 = False     # s155 lists every action; this test is about the card without that list
acts = json.load(open(os.path.join(LUA, "SolActions_Snapshot.txt"), encoding="utf-8", errors="replace"))["actions"]
card = MR.sheet(acts, "")
visible = set(re.findall(r"(?m)^([a-z_0-9]+):", card)) | {"none", "unknown"}
ev = json.load(open(os.path.join(HERE, "s82_route_eval.json"), encoding="utf-8"))
def wanted(c):
    a = c.get("action")
    return [a] if isinstance(a, str) else [x.get("action") if isinstance(x, dict) else x for x in (a or c.get("actions") or [])]
on_card = [c for c in ev if all(i in visible for i in wanted(c) if i)]
off_card = [c for c in ev if any(i and i not in visible for i in wanted(c))]
changed = [c["text"] for c in on_card if MR.add_extra_actions(card, c["text"], acts) != card]
ck("the %d eval lines for card actions get the card byte for byte as before" % len(on_card), not changed, changed)
enabled = {a["id"] for a in acts if a.get("enabled") is not False}
skip = set(MR.CARD_DUPLICATES) | MR.EXTRA_SKIP_S154
can = [c for c in off_card if all(i in visible or (i in enabled and i not in skip) for i in wanted(c) if i)]
shown = [c for c in can if all(('"%s"' % i) in MR.add_extra_actions(card, c["text"], acts)[len(card.partition(chr(10) + chr(10) + "ذاكرتك")[0]):] or i in visible for i in wanted(c) if i)]
missed = [c["text"] for c in can if c not in shown]
print("     off-card eval lines: %d; possible now (enabled, not a duplicate): %d; shown their action: %d" % (len(off_card), len(can), len(shown)))
ck("every possible off-card eval line gets its own action as an example", not missed, missed)
dup = [c["text"] for c in ev if any(('"%s"' % d) in MR.add_extra_actions(card, c["text"], acts) for d in skip)]
ck("card duplicates and helpers are never added (exit_vehicle, board_vehicle, set_combat_doctrine, sol_fuel)", not dup, dup)
dis = [a["id"] for a in acts if a.get("enabled") is False]
bad = [c["text"] for c in ev if any(('"%s"' % d) in MR.add_extra_actions(card, c["text"], acts)[len(card) - 40:] for d in dis)]
ck("an action the game says is not possible now is not added (%d such now)" % len(dis), not bad, bad)
grown = max(len(MR.add_extra_actions(card, c["text"], acts)) - len(card) for c in ev)
ck("at most %d example lines, small (largest growth %d chars)" % (MR.EXTRA_MAX_S154, grown), grown <= 330, grown)
for said in ("مرحبا سول", "كيفك اليوم", "شو اسم هالشارع", ""):
    ck("small talk leaves the card alone: %r" % said, MR.add_extra_actions(card, said, acts) == card)
with_mem = MR.sheet(acts, "MEMORY-LINE")
out = MR.add_extra_actions(with_mem, "اشربي مي", acts)
ck("the example goes before her memory, the memory stays last", out != with_mem and out.endswith("MEMORY-LINE") and out.index('"sol_drink"') < out.index("MEMORY-LINE"), out[-300:])
p = MR.parse('{"action":"sol_drink","speech":""}')
ck("the Mind parses the model's answer for such an action", isinstance(p, dict) and p.get("action") == "sol_drink", p)
# the chat hook: switch off = the card exactly as before
import chat_service as C
class Fake:
    dir = tmp
    logs = []
    def log(self, m): self.logs.append(m)
C._session_sheet_pre_s90 = lambda self, snap, mem, a: card
C._SAID_S90[:] = ["اشربي مي"]
on = C._session_sheet_s90(Fake(), None, None, acts)
open(sw, "w", newline="").write("card_extra_actions=off\r\n")
off = C._session_sheet_s90(Fake(), None, None, acts)
del C._SAID_S90[:]
ck("switch on: his line adds the action; switch off: the card as before", on != card and '"sol_drink"' in on and off == card)
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(PASSED), len(FAIL)))
sys.exit(1 if FAIL else 0)

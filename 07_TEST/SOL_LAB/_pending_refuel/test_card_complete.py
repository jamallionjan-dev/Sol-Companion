"""Fails if anything she can be told to do is missing from the card the model gets. usage: test_card_complete.py [sol_mind dir]"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
M = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind")
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_mind")); sys.path.insert(0, M)
import model_router as MR
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
SNAP = os.path.join(HERE, "..", "profile", "Zomboid", "Lua", "SolActions_Snapshot.txt")
acts = json.load(open(SNAP, encoding="ascii", errors="replace"))["actions"]
card = MR.sheet(acts, "")
shown = lambda i: re.search(r"(?m)^" + re.escape(i) + r":", card) is not None
game = [a["id"] for a in acts if a["id"] not in MR.NOT_ORDERS]
miss = [i for i in game if not shown(i)]
ck("every action the game reports is on the card", not miss, miss)
src = open(os.path.join(M, "chat_service.py"), encoding="utf-8").read()
blk = src[src.index("VERB_MAP = ["):src.index("GIVE_ANY =")]
targets = sorted(set(re.findall(r'\("([a-z_]+)",\s*(?:None|"[^"]*")\)\),?\s*$', blk, re.M)))
ck("found the word list", len(targets) > 20, targets)
aliases = {"board_vehicle": "board_car", "exit_vehicle": "exit_car"}
miss = [x for x in targets if not shown(x) and not shown(aliases.get(x, "-"))]
ck("everything the old word list could do is on the card", not miss, miss)
ck("the card is one table: no duplicates between its two lists", not (set(MR.COMMANDS) & set(MR.CARD_ACTIONS)), set(MR.COMMANDS) & set(MR.CARD_ACTIONS))
ck("a disabled action is still listed", shown("sol_toggle_light") and shown("sol_cook"))
print("card chars", len(card))
print("SUMMARY", "ALL PASS" if not FAIL else "FAILED: %s" % FAIL[:6])
sys.exit(1 if FAIL else 0)

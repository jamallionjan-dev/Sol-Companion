"""Mind: "هتمي" (spoken without the first alef) is "اهتمي", so "سول هتمي بالزرعات بغيابي" starts the full farm keeper, like
"اهتمي بالزرعات بغيابي" already does. Synonym only, same existing action; plus one model-card example. usage: apply_s72_mind.py <sol_mind dir>"""
import os, sys
M = sys.argv[1]
p = os.path.join(M, "farm_talk.py")
t = open(p, encoding="utf-8", newline="").read()
old = "(?:اهتمي|اهتم|اعتني|"
new = "(?:ا?هتمي|ا?هتم|اعتني|"
if new not in t:
    assert t.count(old) == 1, "KEEPER_RX shape changed"
    t = t.replace(old, new)
open(p, "w", encoding="utf-8", newline="").write(t)
r = os.path.join(M, "model_router.py")
t = open(r, encoding="utf-8", newline="").read()
old_card = '"farm_keeper":   ("تهتم بالمزرعة لحالها", "اهتمي بالمزرعة"),'
new_card = '"farm_keeper":   ("تهتم بالمزرعة لحالها", "سول اهتمي بالزرعات بغيابي"),'      # Jamal's own words; same single action
if new_card not in t:
    assert t.count(old_card) == 1, "farm_keeper card line changed"
    t = t.replace(old_card, new_card)
if '("دبريلي الارض بغيابي", "farm_keeper")' not in t:
    t = t.replace("EXAMPLES = ((", 'EXAMPLES = (("دبريلي الارض بغيابي", "farm_keeper"), (', 1)
if '("سول هتمي بالزرعات بغيابي", "farm_keeper")' not in t:
    assert t.count("EXAMPLES = ((") == 1
    t = t.replace("EXAMPLES = ((", 'EXAMPLES = (("سول هتمي بالزرعات بغيابي", "farm_keeper"), (', 1)
open(r, "w", encoding="utf-8", newline="").write(t)
print("applied")

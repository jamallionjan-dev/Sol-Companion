"""Mind words for the farm: "خلص وقفي زراعة" (the stop line on the model card) and "دبريلي الارض" reach the farm. usage: apply_s62_mind.py <sol_mind dir>"""
import os, sys
MIND = sys.argv[1]
p = os.path.join(MIND, "farm_talk.py")
t = open(p, encoding="utf-8", newline="").read()
old = 'STOP_RX = re.compile(r"^(?:خلص زراعه|وقفي زراعه|وقفي(?:\\s+شغل)?\\s+" + _FARM_WORD + r")\\s*$")'
new = 'STOP_RX = re.compile(r"^(?:خلص(?:ي)?\\s+)?(?:خلص زراعه|وقفي زراعه|وقفي(?:\\s+شغل)?\\s+" + _FARM_WORD + r")\\s*$")'
if new not in t:
    assert t.count(old) == 1, "STOP_RX not found"
    t = t.replace(old, new)
old_k = "KEEPER_RX = re.compile("
new_k = "KEEPER_RX = re.compile(r\"دبريلي\\s+(?:ال)?(?:ارض|مزرعه|زرع)|\"\n    "
if "دبريلي" not in t:
    assert t.count(old_k) == 1
    i = t.index(old_k) + len(old_k)
    # the original pattern follows; prepend an alternative to it
    j = t.index("r\"", i) if t.find("r\"", i) != -1 and t.find("r\"", i) - i < 20 else None
    assert j is not None, "KEEPER_RX shape changed"
    t = t[:j] + "r\"دبريلي\\s+(?:ال)?(?:ارض|مزرعه|زرع)|\"\n    " + t[j:]
open(p, "w", encoding="utf-8", newline="").write(t)
print("applied")

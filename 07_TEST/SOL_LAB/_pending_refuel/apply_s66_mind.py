"""Mind: "رتّبي الأغراض" alone is the sort order (sol_sort), not the old errand.
Confirmed 2026-11-10 18:08-18:09 game time (sol_mind.log): the model chose sort_items, the card line "رتبي الاغراض" went through the goal parser first,
intent_engine.parse_high_confidence matched "رتبي الاغراض" in _UNLOAD and made errand_round_trip(home, unload, return), so she drove off
("ماشي، رايحة ورجعالك." from goal_engine.py). Now the sort words make an errand only together with a going word, a car word or "بالبيت ... وارجعي";
"روحي فضي الاغراض بالبيت وارجعي" and the other errand phrases are unchanged. usage: apply_s66_mind.py <sol_mind dir>"""
import os, sys
p = os.path.join(sys.argv[1], "intent_engine.py")
t = open(p, encoding="utf-8", newline="").read()
NL = "\r\n" if "\r\n" in t else "\n"
old = "    if any(w in n for w in _UNLOAD) or (any(w in n for w in _GO) and any(w in n for w in _RETURN)):" + NL
new = ("    sort_only = \"رتبي الاغراض\" in n and not (any(w in n for w in _GO) or \"سيار\" in n or any(w in n for w in _RETURN))   # alone it is the sort order" + NL +
       "    unload_hit = any(w in n for w in _UNLOAD if w != \"رتبي الاغراض\") or (\"رتبي الاغراض\" in n and not sort_only)" + NL +
       "    if unload_hit or (any(w in n for w in _GO) and any(w in n for w in _RETURN)):" + NL)
if new not in t:
    assert t.count(old) == 1, "errand rule changed"
    t = t.replace(old, new)
old2 = '            "task": "unload" if any(w in n for w in _UNLOAD) else "none",'
new2 = '            "task": "unload" if unload_hit else "none",'
if new2 not in t:
    assert t.count(old2) == 1
    t = t.replace(old2, new2)
open(p, "w", encoding="utf-8", newline="").write(t)
print("applied")

"""Variant (b) of s70: no keyword override; the model learns the cancel orders from its own card.
Adds one card action forget_all (card line "انسي كلشي", which the word list already maps to sol_forget = cancel her orders and follow)
and examples so "خلص انسي كلشي" / "بكفي هيك وقفي الترتيب" are picked as actions, not chat. Model first stays as Jamal's rule says.
usage: apply_s70b_mind.py <sol_mind dir>"""
import os, sys
p = os.path.join(sys.argv[1], "model_router.py")
t = open(p, encoding="utf-8", newline="").read()
NL = "\r\n" if "\r\n" in t else "\n"
k = '    "stay":          ("تضل واقفة بمكانها", "ضلي هون"),' + NL
if '"forget_all"' not in t:
    assert t.count(k) == 1
    t = t.replace(k, k + '    "forget_all":    ("تلغي كل أوامرها وترجع تلحقه", "انسي كلشي"),' + NL)
ek = 'EXAMPLES = (('
if '("خلص انسي كلشي", "forget_all")' not in t:
    assert t.count(ek) == 1
    t = t.replace(ek, 'EXAMPLES = (("خلص انسي كلشي", "forget_all"), ("بكفي هيك وقفي الترتيب", "sort_stop"), (', 1)
open(p, "w", encoding="utf-8", newline="").write(t)
print("applied")

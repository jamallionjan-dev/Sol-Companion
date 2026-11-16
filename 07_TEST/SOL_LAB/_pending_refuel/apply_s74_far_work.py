"""far_work (DOCS/PLAN_far_work.md, council SOL_REVIEW_20261109.md 39): Sol keeps the farm while he is far and her farm is not loaded.
Her work is done on the plants' own global objects every game hour (the game keeps simulating them unloaded), at the pace her body
could keep, night too (owner rule 2026-11-10), from real home supplies through a ledger applied once when the house loads.
On his return she says one short line ("far_report" row; farm_talk.far_report_line words it).
In place and idempotent (each edit is skipped when already there). Game closed only; the Mind restarted afterwards.

  SolFarWork.lua      new file, copied into the client dir (switch far_work, off = nothing runs)
  SolAuthority.lua    "far_work" in A.FIXES
  SolFixes_LAB.txt    far_work=on (lab only; MAIN stays off until proven)
  farm_talk.py        far_report_line(); stop_line answers the "far_report" row
usage: apply_s74_far_work.py <client dir> <sol_mind dir>      (either may be '-')"""
import os, shutil, sys
NL, CRLF = chr(10), chr(13) + chr(10)
HERE = os.path.dirname(os.path.abspath(__file__))

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

FT_OLD = '''def stop_line(stop):'''
FT_NEW = '''# ---------------------------------------------------------------- far_work: what she did while he was away, one short line
# (one, two, three to ten, eleven and up) as people say them
FAR_CROP_AR = {
    "Base.Carrots": ("جزرة وحدة", "جزرتين", "جزرات", "جزرة"),
    "Base.Tomato": ("حبة بندورة", "حبتين بندورة", "حبات بندورة", "حبة بندورة"),
    "Base.Potato": ("حبة بطاطا", "حبتين بطاطا", "حبات بطاطا", "حبة بطاطا"),
    "Base.Cabbage": ("ملفوفة وحدة", "ملفوفتين", "ملفوفات", "ملفوفة"),
    "Base.Broccoli": ("راس بروكلي", "راسين بروكلي", "روس بروكلي", "راس بروكلي"),
    "Base.Cauliflower": ("راس زهرة", "راسين زهرة", "روس زهرة", "راس زهرة"),
    "Base.RedRadish": ("فجلة وحدة", "فجلتين", "فجلات", "فجلة"),
    "Base.Strewberrie": ("حبة فريز", "حبتين فريز", "حبات فريز", "حبة فريز"),
    "Base.Spinach": ("ضمة سبانخ", "ضمتين سبانخ", "ضمات سبانخ", "ضمة سبانخ"),
    "Base.Leek": ("ضمة كراث", "ضمتين كراث", "ضمات كراث", "ضمة كراث"),
    "Base.SugarBeet": ("شمندرة وحدة", "شمندرتين", "شمندرات", "شمندرة"),
}
FAR_SHORT_AR = {"water": "بس خلصت المي", "seed": "بس خلصوا البذور", "storage": "بس ما لقيت محل للمحصول", "fert": "بس خلص السماد", "spray": "بس خلص الدوا"}
def _far_count(n, forms):
    one, two, few, many = forms
    if n == 1: return one
    if n == 2: return two
    if n <= 10: return "%d %s" % (n, few)
    return "%d %s" % (n, many)
def _far_crop(full, n):
    forms = FAR_CROP_AR.get(full)
    if forms is None:
        nm = _name(full)
        forms = ("حبة %s" % nm, "حبتين %s" % nm, "حبات %s" % nm, "حبة %s" % nm)
    return _far_count(n, forms)
def far_report_line(d):
    """While he was away: watering, picking, sowing, spraying, feeding, and what ran out. Numbers only from the game."""
    if not isinstance(d, dict): return None
    parts = []
    rounds = int(d.get("rounds") or 0)
    if rounds: parts.append("سقيت الزرع" + ("" if rounds == 1 else (" مرتين" if rounds == 2 else (" %d مرات" % rounds if rounds <= 10 else " %d مرة" % rounds))))
    picked = [h for h in (d.get("harvest") or []) if isinstance(h, dict) and int(h.get("n") or 0) > 0][:2]
    if picked: parts.append("قطفت " + " و".join(_far_crop(h.get("veg"), int(h["n"])) for h in picked))
    if d.get("floor"): parts.append("حطيت الزيادة عالأرض جنب المخزن لأنو امتلى")
    sown = int(d.get("sown") or 0)
    if sown: parts.append("زرعت " + _far_count(sown, ("تلم", "تلمين", "أتلام", "تلم")))
    if int(d.get("cured") or 0): parts.append("رشيت الزرع المريض")
    if int(d.get("fed") or 0): parts.append("حطيت سماد")
    got = set(d.get("short") or [])
    short = [FAR_SHORT_AR[s] for s in ("water", "seed", "storage", "spray", "fert") if s in got][:1]      # the one that matters most
    if not parts and not short: return None
    if not parts: return "ما قدرت أعمل كتير، " + short[0][3:] + "."
    line = parts[0] + "".join(" و" + p for p in parts[1:4])
    if short: line += "، " + short[0]
    return line + "."

def stop_line(stop):'''
FT2_OLD = '''    if r == "home_arrived": return "وصلت عالبيت."'''
FT2_NEW = '''    if r == "home_arrived": return "وصلت عالبيت."
    if r == "far_report": return far_report_line(d)'''

def client(cl):
    shutil.copy(os.path.join(HERE, "SolFarWork.lua"), os.path.join(cl, "SolFarWork.lua"))
    A = os.path.join(cl, "SolAuthority.lua")
    if '"far_work"' not in open(A, encoding="utf-8").read():
        edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "far_work",           -- far away, she keeps the farm from her saved place; supplies through a ledger' + NL)
    fix = os.path.join(cl, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
    if os.path.exists(fix) and "far_work=" not in open(fix, encoding="utf-8").read():
        with open(fix, "a", encoding="utf-8", newline="") as h: h.write("far_work=on" + CRLF)

def mind(md):
    p = os.path.join(md, "farm_talk.py")
    edit(p, FT_OLD, FT_NEW)
    edit(p, FT2_OLD, FT2_NEW)

if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit(__doc__)
    if sys.argv[1] != "-": client(sys.argv[1])
    if sys.argv[2] != "-": mind(sys.argv[2])
    print("far_work applied")

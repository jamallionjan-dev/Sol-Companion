"""s103 parts_delivery: once, on the first load after install, Jamal (the player) gets a BARE HK G28, a BARE Colt M4A1,
every part of the two stored builds (Sol_SecretLoadout.txt / SolSecretLoadoutData) as a loose EFZ part, and one empty
magazine per gun, to assemble with EFZ's Assembly menu. Flag: player modData SolPartsDelivery. Switch parts_delivery
(off = nothing). Needs SolSecretLoadout.lua (installed, s74) and SolKitBare.lua (copied here too). Game closed only.
usage: apply_s103_parts_delivery.py <client>"""
import os, sys, shutil
CL = sys.argv[1]; NL, CRLF = chr(10), chr(13) + chr(10)
HERE = os.path.dirname(os.path.abspath(__file__))
def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: print("kept " + os.path.basename(path)); return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old))
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new)); print("edited " + os.path.basename(path))

assert os.path.exists(os.path.join(CL, "SolSecretLoadout.lua")), "SolSecretLoadout.lua (s74) must be installed first"
for f in ("SolKitBare.lua", "SolPartsDelivery.lua"):
    shutil.copy(os.path.join(HERE, f), os.path.join(CL, f)); print("copied " + f)
A = os.path.join(CL, "SolAuthority.lua")
if '"parts_delivery"' not in open(A, encoding="utf-8").read():
    edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "parts_delivery",   -- s103: once, his two guns as a bare kit (receivers, loose parts, empty magazines) into HIS inventory' + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "parts_delivery" not in open(fix, encoding="utf-8").read():
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("parts_delivery=on" + CRLF)
print("s103 parts_delivery applied")

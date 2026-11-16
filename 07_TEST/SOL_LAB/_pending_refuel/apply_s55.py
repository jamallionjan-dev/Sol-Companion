"""Bleeding at the wheel: she gets out, bandages and drives on. Game closed only. usage: apply_s55.py <client dir>"""
import os, shutil, sys
CL = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
A = os.path.join(CL, "SolAuthority.lua")
t = open(A, encoding="utf-8", newline="").read()
nl = CRLF if CRLF in t else NL
k = "A.FIXES = {" + nl
assert t.count(k) == 1
open(A, "w", encoding="utf-8", newline="").write(t.replace(k, k + '    "bleed_get_out",' + nl))
shutil.copy(os.path.join(HERE, "SolBleedStop.lua"), os.path.join(CL, "SolBleedStop.lua"))
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix):
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("bleed_get_out=on" + CRLF)
print("applied")

"""Vehicles that turn the other way: Lua side and switch. Game closed only. usage: apply_s57.py <client dir>
The Java class goes into SolCombined.jar with build_steer.py."""
import os, shutil, sys
CL = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
A = os.path.join(CL, "SolAuthority.lua")
t = open(A, encoding="utf-8", newline="").read()
nl = CRLF if CRLF in t else NL
k = "A.FIXES = {" + nl
assert t.count(k) == 1
if '"vehicle_steer_adapt"' not in t:
    open(A, "w", encoding="utf-8", newline="").write(t.replace(k, k + '    "vehicle_steer_adapt",' + nl))
shutil.copy(os.path.join(HERE, "SolSteerAdapt.lua"), os.path.join(CL, "SolSteerAdapt.lua"))
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "vehicle_steer_adapt" not in open(fix, encoding="utf-8").read():
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("vehicle_steer_adapt=on" + CRLF)
print("applied")

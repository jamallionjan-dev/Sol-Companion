"""s104b shooting_discipline 0.2.0: misses (not hits) count toward the per-zombie cap; RealSingle for Gunworks guns, set
just before the shot and logged once per weapon; a downed zombie is never shot; read-only kill ledger (hits by Sol / by
Jamal and the zombie's health before each hit, one "kill:" line per zombie).
Live 2026-11-11 14:55-14:57 (DebugLog 2026-11-11_14-48): aimed shots hit, zombies took 5+ hits, the 5-shot cap held fire
at a zombie she was hitting; "fire mode RealAuto -> Single" every shot (EFZ TW_FireModeSwitch.lua:47-55 on OnWeaponSwing).
Only SolShootDiscipline.lua changes; SCCombat keeps the 5 s104 hooks (installed by apply_s104 if missing). Same switch.
Install with the game closed (Lua only), then restart.
usage: apply_s104b_shooting_discipline.py <client>"""
import os, sys, shutil, subprocess, filecmp
CL = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(CL, "SCCombat.lua")
if open(C, encoding="utf-8").read().count("-- s104 shooting_discipline") != 5:
    r = subprocess.run([sys.executable, os.path.join(HERE, "apply_s104_shooting_discipline.py"), CL], capture_output=True, text=True)
    print(r.stdout.strip()); assert r.returncode == 0, r.stderr
src, dst = os.path.join(HERE, "SolShootDiscipline.lua"), os.path.join(CL, "SolShootDiscipline.lua")
if os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False):
    print("kept SolShootDiscipline.lua")
else:
    shutil.copy(src, dst); print("copied SolShootDiscipline.lua (0.2.0)")
assert 'M.VERSION = "0.2.0"' in open(dst, encoding="utf-8").read()
print("s104b shooting_discipline applied")

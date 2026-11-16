"""LAB only: put Hotsco's New Body and its EX add-on in the lab mod list, right after SPNCC (which the base mod requires).
usage: lab_enable_hotsco.py [off]   - "off" takes both out again.
Edits 07_TEST/SOL_LAB/MODS_LAB_MIN.txt and profile/Zomboid/mods/default.txt together (launch_lab.ps1 refuses when they differ).
The main game's list is never touched."""
import os, sys
LAB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FILES = [os.path.join(LAB, "MODS_LAB_MIN.txt"), os.path.join(LAB, "profile", "Zomboid", "mods", "default.txt")]
CRLF = chr(13) + chr(10)
ANCHOR = "    mod = SPNCC," + CRLF
ADD = "    mod = HotscoNewBody," + CRLF + "    mod = HotscoNewBodyEX," + CRLF
off = len(sys.argv) > 1 and sys.argv[1] == "off"
for p in FILES:
    t = open(p, encoding="utf-8", newline="").read()
    if off:
        if ADD not in t: print("kept " + os.path.basename(p)); continue
        t = t.replace(ADD, "")
    else:
        if ADD in t: print("kept " + os.path.basename(p)); continue
        if t.count(ANCHOR) != 1: raise RuntimeError((p, "expected one SPNCC line", t.count(ANCHOR)))
        t = t.replace(ANCHOR, ANCHOR + ADD)
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("edited " + os.path.basename(p))

"""Install the read-only s111 damage comparison probe and its own lab switch."""
import os
import shutil
import sys

CLIENT = os.path.abspath(sys.argv[1])
HERE = os.path.dirname(os.path.abspath(__file__))
NL = "\n"
CRLF = "\r\n"


def add_switch(path, switch):
    with open(path, "r", encoding="utf-8", newline="") as handle:
        text = handle.read()
    if '"' + switch + '"' in text:
        print("kept " + os.path.basename(path))
        return
    marker = "A.FIXES = {" + NL
    newline = CRLF if CRLF in text else NL
    marker = marker.replace(NL, newline)
    insert = (marker + '    "' + switch + '", -- s111: read-only before/after health probe for matched firearm hits'
              + newline)
    if text.count(marker) != 1:
        raise SystemExit("expected one A.FIXES marker in " + path)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace(marker, insert, 1))
    print("edited " + os.path.basename(path))


probe = os.path.join(HERE, "SolDamageProbe.lua")
target = os.path.join(CLIENT, "SolDamageProbe.lua")
if os.path.exists(target):
    with open(probe, "rb") as handle:
        expected = handle.read()
    with open(target, "rb") as handle:
        current = handle.read()
    if expected != current:
        raise SystemExit("refusing to overwrite changed SolDamageProbe.lua")
    print("kept SolDamageProbe.lua")
else:
    shutil.copyfile(probe, target)
    print("copied SolDamageProbe.lua")

add_switch(os.path.join(CLIENT, "SolAuthority.lua"), "shooting_damage_probe")
profile = os.path.normpath(os.path.join(CLIENT, "..", "..", "..", "..", "..", ".."))
switch_file = os.path.join(profile, "Lua", "SolFixes_LAB.txt")
if os.path.isfile(switch_file):
    with open(switch_file, "r", encoding="utf-8", newline="") as handle:
        text = handle.read()
    if "shooting_damage_probe=" not in text:
        newline = CRLF if CRLF in text else NL
        if text and not text.endswith((NL, CRLF)):
            text += newline
        text += "shooting_damage_probe=on" + newline
        with open(switch_file, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        print("enabled shooting_damage_probe in lab only")
    else:
        print("kept shooting_damage_probe lab switch")
print("s111 read-only damage probe applied")

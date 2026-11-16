"""Install the opt-in Sol-only native head-hit bridge into the LAB Lua client."""
import os
import shutil
import sys

CLIENT = os.path.abspath(sys.argv[1])
HERE = os.path.dirname(os.path.abspath(__file__))
SWITCH = "sol_headshots"

source = os.path.join(HERE, "SolHeadshot.lua")
target = os.path.join(CLIENT, "SolHeadshot.lua")
with open(source, "rb") as handle:
    expected = handle.read()
if os.path.exists(target):
    with open(target, "rb") as handle:
        current = handle.read()
    if current != expected:
        raise SystemExit("refusing to overwrite changed SolHeadshot.lua")
    print("kept SolHeadshot.lua")
else:
    shutil.copyfile(source, target)
    print("copied SolHeadshot.lua")

authority_path = os.path.join(CLIENT, "SolAuthority.lua")
with open(authority_path, "r", encoding="utf-8", newline="") as handle:
    authority = handle.read()
if '"' + SWITCH + '"' not in authority:
    marker = 'A.FIXES = {\n'
    newline = "\r\n" if "\r\n" in authority else "\n"
    marker = marker.replace("\n", newline)
    if authority.count(marker) != 1:
        raise SystemExit("expected one A.FIXES marker in SolAuthority.lua")
    inserted = marker + '    "' + SWITCH + '", -- s113: native Sol firearm head-hit outcome' + newline
    with open(authority_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(authority.replace(marker, inserted, 1))
    print("added SolAuthority switch")
else:
    print("kept SolAuthority switch")

profile = os.path.normpath(os.path.join(CLIENT, "..", "..", "..", "..", "..", ".."))
switch_path = os.path.join(profile, "Lua", "SolFixes_LAB.txt")
if not os.path.isfile(switch_path):
    raise SystemExit("LAB switch file not found: " + switch_path)
with open(switch_path, "r", encoding="utf-8", newline="") as handle:
    switches = handle.read()
if SWITCH + "=" not in switches:
    newline = "\r\n" if "\r\n" in switches else "\n"
    if switches and not switches.endswith(("\n", "\r\n")):
        switches += newline
    switches += SWITCH + "=on" + newline
    with open(switch_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(switches)
    print("enabled sol_headshots in LAB only")
else:
    print("kept LAB switch")

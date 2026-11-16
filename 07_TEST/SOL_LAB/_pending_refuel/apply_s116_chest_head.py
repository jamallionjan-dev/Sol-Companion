"""Wire Sol's native hit-part plan to her per-shot decision and install its verified Java patch."""
import hashlib
import os
import shutil
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: apply_s116_chest_head.py <client-dir> <candidate-jar>")
client = os.path.abspath(sys.argv[1])
candidate = os.path.abspath(sys.argv[2])
lua_path = os.path.join(client, "SolShootDiscipline.lua")
with open(lua_path, "r", encoding="ascii", newline="") as handle:
    lua = handle.read()
anchor = '    local burst = group >= M.GROUP_COUNT and st.burst < M.BURST_MAX'
insert = anchor + '''
    -- Select the native hit-part plan for this shot. Java advances the 2 chest : 1 head cycle
    -- only when the zombie hit resolves, so retries and missed aim pulses do not skip a part.
    local hitModeSetter = rawget(_G, "solHeadshotSetFireMode")
    local hitAuthority = rawget(_G, "SolAuthority")
    if type(hitAuthority) == "table" and type(hitAuthority.on) == "function"
        and hitAuthority.on("sol_headshots") == true and type(hitModeSetter) == "function" then
        pcall(hitModeSetter, burst and "burst" or "single")
    end'''
if "-- s116: route the resolved shot mode to native hit-part plan" not in lua:
    if lua.count(anchor) != 1:
        raise SystemExit("expected one burst-plan anchor in SolShootDiscipline.lua")
    lua = lua.replace(anchor, insert + ' -- s116: route the resolved shot mode to native hit-part plan', 1)
    with open(lua_path, "w", encoding="ascii", newline="") as handle:
        handle.write(lua)
    print("wired per-shot single/burst mode to native hit plan")
else:
    print("kept native hit-plan mode wiring")

authority_path = os.path.join(client, "SolAuthority.lua")
with open(authority_path, "r", encoding="ascii", newline="") as handle:
    authority = handle.read()
if '"sol_headshots"' not in authority:
    anchor = "A.FIXES = {"
    if authority.count(anchor) != 1:
        raise SystemExit("expected one A.FIXES anchor in SolAuthority.lua")
    authority = authority.replace(anchor, anchor + '\n    "sol_headshots", -- s113/s116: native Sol firearm part routing', 1)
    with open(authority_path, "w", encoding="ascii", newline="") as handle:
        handle.write(authority)
    print("registered sol_headshots switch")

profile = os.path.abspath(os.path.join(client, "..", "..", "..", "..", "..", ".."))
switch_path = os.path.join(profile, "Lua", "SolFixes_LAB.txt")
if not os.path.isfile(switch_path):
    switch_path = os.path.join(profile, "Lua", "SolFixes_MAIN.txt")
if not os.path.isfile(switch_path):
    raise SystemExit("SolFixes_LAB.txt or SolFixes_MAIN.txt is missing under " + profile)
with open(switch_path, "r", encoding="ascii", newline="") as handle:
    switches = handle.read()
if "sol_headshots=on" not in switches.splitlines():
    newline = "\r\n" if "\r\n" in switches else "\n"
    if switches and not switches.endswith(("\n", "\r\n")):
        switches += newline
    switches += "sol_headshots=on" + newline
    with open(switch_path, "w", encoding="ascii", newline="") as handle:
        handle.write(switches)
    print("enabled sol_headshots in " + os.path.basename(switch_path))

if not os.path.isfile(candidate):
    raise SystemExit("candidate jar not found: " + candidate)
jar_path = os.path.normpath(os.path.join(client, "..", "..", "java", "SolCombined.jar"))
os.makedirs(os.path.dirname(jar_path), exist_ok=True)
digest = hashlib.sha256(open(candidate, "rb").read()).hexdigest()
if os.path.isfile(jar_path) and hashlib.sha256(open(jar_path, "rb").read()).hexdigest() == digest:
    print("kept verified native hit-plan jar", digest)
else:
    shutil.copyfile(candidate, jar_path)
    if hashlib.sha256(open(jar_path, "rb").read()).hexdigest() != digest:
        raise SystemExit("installed candidate jar hash mismatch")
    print("installed verified native hit-plan jar", jar_path)
print("sha256", digest)

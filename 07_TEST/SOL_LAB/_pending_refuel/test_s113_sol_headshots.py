"""Offline checks for the opt-in Sol firearm head-part selection bridge."""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
BASE = os.path.join(ROOT, "07_TEST", "SOL_LAB", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
sys.path.insert(0, HERE)
from kahlua_env import lua51

FAIL = []
PASS = 0


def ck(name, ok):
    global PASS
    print(("PASS " if ok else "FAIL ") + name)
    if ok:
        PASS += 1
    else:
        FAIL.append(name)


def main():
    with tempfile.TemporaryDirectory(prefix="sol_s113_headshots_") as temp:
        profile = os.path.join(temp, "profile", "Zomboid")
        client = os.path.join(profile, "mods", "Sol_LAB", "42", "media", "lua", "client")
        os.makedirs(client)
        os.makedirs(os.path.join(profile, "Lua"))
        shutil.copyfile(os.path.join(BASE, "SolAuthority.lua"), os.path.join(client, "SolAuthority.lua"))
        switches = os.path.join(profile, "Lua", "SolFixes_LAB.txt")
        with open(switches, "w", encoding="ascii", newline="\n") as handle:
            handle.write("shooting_discipline=on\n")

        apply = os.path.join(HERE, "apply_s113_sol_headshots.py")
        first = subprocess.run([sys.executable, apply, client], capture_output=True, text=True)
        second = subprocess.run([sys.executable, apply, client], capture_output=True, text=True)
        ck("installer applies to isolated profile", first.returncode == 0 and "copied SolHeadshot.lua" in first.stdout)
        ck("installer is idempotent", second.returncode == 0 and "kept SolHeadshot.lua" in second.stdout)

        auth = open(os.path.join(client, "SolAuthority.lua"), encoding="ascii").read()
        lua = open(os.path.join(client, "SolHeadshot.lua"), encoding="ascii").read()
        switch_text = open(switches, encoding="ascii").read()
        ck("switch registered once", auth.count('"sol_headshots"') == 1)
        ck("LAB switch enabled once", switch_text.count("sol_headshots=on") == 1)
        ck("new Lua is ASCII", all(ord(char) < 128 for char in lua))

        syntax = lua51.LuaRuntime(unpack_returned_tuples=True)
        ok, error = syntax.eval("function(s) local f,e=loadstring(s); return f~=nil,e end")(lua)
        ck("Lua 5.1 syntax", ok)

        runtime = lua51.LuaRuntime(unpack_returned_tuples=True)
        runtime.execute(r'''
            NOW=10000; SW=true; EVENTS={}; enabled=nil
            function getTimestampMs() return NOW end
            SolAuthority={on=function(name) return name=="sol_headshots" and SW end}
            function solHeadshotSet(value) enabled=value end
            local function event() local e={}; e.Add=function(fn) e.fn=fn end; return e end
            Events={OnGameStart=event(),OnTick=event()}
        ''')
        runtime.execute(lua)
        runtime.execute("Events.OnGameStart.fn(); assert(enabled==true)")
        ck("LAB on switch enables bridge", runtime.eval("enabled == true"))
        runtime.execute("SW=false; NOW=11001; Events.OnTick.fn(); assert(enabled==false)")
        ck("switch off restores native hit selection", runtime.eval("enabled == false"))
        runtime.execute("SW=true; NOW=12002; Events.OnTick.fn(); assert(enabled==true)")
        ck("switch can be re-enabled at runtime", runtime.eval("enabled == true"))
        ck("no per-frame scan or world query", "OnPlayerUpdate" not in lua and "getCell" not in lua and "for " not in lua)

    java = open(os.path.join(ROOT, "05_TOOLS", "sol_nav_java", "localplayerbody", "SolHeadshot.java"), encoding="utf-8").read()
    ck("patch scopes native CombatManager hit resolution", 'CombatManager", methodName = "processHit"' in java)
    ck("cached ballistic target part is overridden", 'BallisticsController", methodName = "getCachedTargetedBodyPart"' in java)
    ck("non-camera fallback target part is overridden", 'CombatManager", methodName = "getBodyPart"' in java)
    ck("both native part-selection hooks include their argument signatures", "@Patch.Argument(0) int targetId" in java and "@Patch.Argument(0) HitReaction reaction" in java)
    ck("event-part advice still matches FromIndex(int)", 'BodyPartType", methodName = "FromIndex"' in java and "@Patch.Argument(0) int index" in java)
    ck("vanilla RNG and critical state are untouched", "Rand.NextBool" not in java and "setCriticalHit" not in java)
    print("%d passed, %d failed" % (PASS, len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

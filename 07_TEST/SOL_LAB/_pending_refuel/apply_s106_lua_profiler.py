"""s106 lua_profiler: a per-mod Lua profiler for the stutter (DOCS/PERF_STUTTER_20261111.md: 61% of the main thread is Kahlua,
44% under IngameState.onTick, JFR cannot split it by mod). Diagnostic only, Lua only (no jar, no ZombieBuddy approval).
SolLuaProfiler.lua times every handler of OnTick, OnPlayerUpdate, OnRenderTick and OnZombieUpdate (also those registered before
it loaded: it swaps them in place in zombie.Lua.Event.callbacks, reached with the -debug reflection globals) and prints, every
15 s, the top 15 source files (mod folder + file) per event in ms/s, plus the top mod folders and its own overhead.
Switch lua_profiler. This installer writes lua_profiler=off into SolFixes_LAB.txt: OFF by default in the lab too (it costs
about 0.3-1 us per handler call while on). Turn it on live (lab only, needs -debug): lua_profiler=on; off restores everything.
MAIN: missing switch = off. Install with the game closed.
usage: apply_s106_lua_profiler.py <client>"""
import os, sys, shutil
CL = sys.argv[1]; NL, CRLF = chr(10), chr(13) + chr(10)
HERE = os.path.dirname(os.path.abspath(__file__))
def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: print("kept " + os.path.basename(path)); return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old))
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new)); print("edited " + os.path.basename(path))

src, dst = os.path.join(HERE, "SolLuaProfiler.lua"), os.path.join(CL, "SolLuaProfiler.lua")
if os.path.exists(dst) and open(dst, "rb").read() == open(src, "rb").read(): print("kept SolLuaProfiler.lua")
else: shutil.copy(src, dst); print("copied SolLuaProfiler.lua")
A = os.path.join(CL, "SolAuthority.lua")
if '"lua_profiler"' not in open(A, encoding="utf-8").read():
    edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "lua_profiler",   -- s106: diagnostic; every 15 s the top Lua files per event (OnTick etc.) in ms/s; default off' + NL)
else: print("kept SolAuthority.lua")
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix):
    body = open(fix, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in body else NL
    if "lua_profiler" not in body:
        with open(fix, "a", encoding="utf-8", newline="") as h: h.write(("" if body.endswith(NL) or body == "" else nl) + "lua_profiler=off" + nl)
        print("switch lua_profiler=off added to SolFixes_LAB.txt")
    else: print("kept SolFixes_LAB.txt")
print("s106 lua_profiler applied")

"""dot_paused_fix: Sol's avatar dot no longer turns grey while the game is paused.
Cause (from SolFar.lua): the dot is grey when the Mind's heartbeat is older than 20 s (MIND_STALE_MS). The heartbeat file is only read inside
SolFar's tick, which runs on OnTick; while the game is paused (Jamal's screenshots show "Game Paused"; the log shows the game paused
17:42-17:48), OnTick stops, the last read ages past 20 s and the dot goes grey although the Mind writes every 5 s.
The panel is drawn while paused, so the dot now reads the heartbeat itself (at most every 5 s of real time). Off = as before.
usage: apply_s68_dot.py <client dir>"""
import os, sys
CL = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (path, old[:60])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

F = os.path.join(CL, "SolFar.lua")
edit(F, "function U.solDotState()" + NL + "    if nowMs() - mindAliveAt > MIND_STALE_MS then return \"off\" end" + NL,
     "function U.solDotState()" + NL +
     "    local A_ = rawget(_G, \"SolAuthority\")" + NL +
     "    if type(A_) == \"table\" and type(A_.on) == \"function\" and A_.on(\"dot_paused_fix\") == true then   -- the panel draws while paused; OnTick does not run" + NL +
     "        local t = nowMs()" + NL +
     "        if t - aliveReadAt >= 5000 or t < aliveReadAt then aliveReadAt = t; pcall(readAlive) end" + NL +
     "    end" + NL +
     "    if nowMs() - mindAliveAt > MIND_STALE_MS then return \"off\" end" + NL)
# readAlive is defined later in the file than U.solDotState; make it visible there
t = open(F, encoding="utf-8", newline="").read()
if "local readAlive" not in t.split("function U.solDotState()")[0]:
    nl = CRLF if CRLF in t else NL
    t = t.replace("function U.solDotState()", "local readAlive        -- set below; the dot calls it while the game is paused" + nl + "function U.solDotState()", 1)
    assert t.count("local function readAlive()") == 1
    t = t.replace("local function readAlive()", "readAlive = function()", 1)
    open(F, "w", encoding="utf-8", newline="").write(t)
A = os.path.join(CL, "SolAuthority.lua")
if '"dot_paused_fix"' not in open(A, encoding="utf-8").read():
    edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "dot_paused_fix",' + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "dot_paused_fix" not in open(fix, encoding="utf-8").read():
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("dot_paused_fix=on" + CRLF)
print("applied")

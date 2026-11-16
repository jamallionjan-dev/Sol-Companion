"""far_wait_speed: far-Sol arrival waits follow game speed (Jamal's rule). Game closed only. usage: apply_s64.py <client dir>
SolFar.lua waitTick counted real milliseconds (paused = stopped). Now each tick counts spent * the game's speed:
the game's own fast-forward steps are 1x / 5x / 20x / 40x (zombie.ui.SpeedControls: GameTime.setMultiplier 1.0, 5.0, 20.0, 40.0;
Lua getGameSpeed() returns the step 1..4). Off = exactly as before."""
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
edit(F, "local function waitTick(t)" + NL,
     "-- far_wait_speed: the game's fast-forward steps (zombie.ui.SpeedControls): 1x, 5x, 20x, 40x" + NL +
     "local SPEED_STEPS = { 1, 5, 20, 40 }" + NL +
     "local function speedFactor()" + NL +
     "    local A = rawget(_G, \"SolAuthority\")" + NL +
     "    if not (type(A) == \"table\" and type(A.on) == \"function\" and A.on(\"far_wait_speed\") == true) then return 1 end" + NL +
     "    local f = rawget(_G, \"getGameSpeed\")" + NL +
     "    if type(f) ~= \"function\" then return 1 end" + NL +
     "    local ok, step = pcall(f)" + NL +
     "    return ok and SPEED_STEPS[tonumber(step) or 1] or 1" + NL +
     "end" + NL + NL +
     "local function waitTick(t)" + NL)
edit(F, "    if not paused() then wait.left = wait.left - spent end" + NL,
     "    if not paused() then wait.left = wait.left - spent * speedFactor() end" + NL)
A = os.path.join(CL, "SolAuthority.lua")
if '"far_wait_speed"' not in open(A, encoding="utf-8").read():                      # once, wherever other patches put their lines
    edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "far_wait_speed",' + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "far_wait_speed" not in open(fix, encoding="utf-8").read():
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("far_wait_speed=on" + CRLF)
print("applied")

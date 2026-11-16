"""s102 reaim_hold (2026-11-11 12:3x live): while following, the s97b re-aim ran a fresh climb probe and logged a new line about every
second (11 lines, several at 7181,8222), because each follow step has a new target (the leader moves), so the per-target cache never hit.
With the switch on: the last gap/door waypoint is kept for REUSE_MS while she has not reached it and vanilla can still walk her there
without a climb; no new probe, no new log line. Off = s97b as installed. Needs s97b. Game closed only. usage: apply_s102_reaim_hold.py <client>"""
import os, sys
CL = sys.argv[1]; NL, CRLF = chr(10), chr(13) + chr(10)
def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: print("kept " + os.path.basename(path)); return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old))
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new)); print("edited " + os.path.basename(path))
P = os.path.join(CL, "SolPlace.lua")
edit(P, '''    local c = NV.native[k]
    if c ~= nil and t - c.at <= NV.NATIVE_TTL_MS then return c.wp end''', '''    local c = NV.native[k]
    if c ~= nil and t - c.at <= NV.NATIVE_TTL_MS then return c.wp end
    local A_ = rawget(_G, "SolAuthority")   -- s102 reaim_hold: keep the last gap while it still serves (follow targets move every step)
    local L_ = NV.lastWp
    if L_ ~= nil and type(A_) == "table" and type(A_.on) == "function" and A_.on("reaim_hold") == true and t - L_.at <= (NV.REUSE_MS or 3000)
        and L_.z == pz and math.max(math.abs(L_.x - px), math.abs(L_.y - py)) > 1 and not NV.lineClimbs(px, py, L_.x, L_.y, pz) then
        NV.stats.heldWaypoints = (NV.stats.heldWaypoints or 0) + 1
        return { x = L_.x, y = L_.y, z = L_.z }
    end''')
edit(P, '''    if wp ~= nil then
        NV.stats.nativeWaypoints = NV.stats.nativeWaypoints + 1''', '''    if wp ~= nil then
        NV.lastWp = { x = wp.x, y = wp.y, z = wp.z, at = t }   -- s102
        NV.stats.nativeWaypoints = NV.stats.nativeWaypoints + 1''')
A = os.path.join(CL, "SolAuthority.lua")
if '"reaim_hold"' not in open(A, encoding="utf-8").read(): edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "reaim_hold",' + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "reaim_hold" not in open(fix, encoding="utf-8").read():
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("reaim_hold=on" + CRLF)
print("s102 reaim_hold applied")

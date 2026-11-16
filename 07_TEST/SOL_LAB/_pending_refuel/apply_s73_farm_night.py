"""farm_night: Sol farms outdoors at night too (Jamal 2026-11-10), with a light; zombies still pause her through the farm runner's
own danger check. Replaces the darkness refusal (SolFarmWork.lua P.next open(): block("dark") when exterior and not daylight).
While she walks to fetch a light from home the outdoor plots wait (no two walks at once); with no light anywhere she works anyway and
says so once. Off = exactly as before. Game closed only. usage: apply_s73_farm_night.py <client dir>"""
import os, shutil, sys
CL = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (path, old[:70])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

W = os.path.join(CL, "SolFarmWork.lua")
edit(W, '        if p.exterior ~= false and env.day == false then block("dark"); return false end',
        '        if p.exterior ~= false and env.day == false and env.nightOk ~= true then block("dark"); return false end   -- farm_night: with a light she works on')
edit(W, "function W.env(a)" + NL,
        "-- farm_night: at night she carries a light; true when she may work outdoors now" + NL +
        "function W.nightOk(a, daylight)" + NL +
        "    local N = rawget(_G, \"SolFarmNight\")" + NL +
        "    if daylight ~= false or type(N) ~= \"table\" or type(N.ensure) ~= \"function\" then return false end" + NL +
        "    local ok, st = pcall(N.ensure, a, true)" + NL +
        "    return ok and (st == \"ready\" or st == \"none\")" + NL +
        "end" + NL +
        "function W.env(a)" + NL)
edit(W, "day = v.daylight(), player = pos,",
        "day = v.daylight(), nightOk = W.nightOk(a, v.daylight()), player = pos,")
shutil.copy(os.path.join(HERE, "SolFarmNight.lua"), os.path.join(CL, "SolFarmNight.lua"))
A = os.path.join(CL, "SolAuthority.lua")
if '"farm_night"' not in open(A, encoding="utf-8").read():
    edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "farm_night",' + NL)
fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix) and "farm_night" not in open(fix, encoding="utf-8").read():
    with open(fix, "a", encoding="utf-8", newline="") as h: h.write("farm_night=on" + CRLF)
print("applied")

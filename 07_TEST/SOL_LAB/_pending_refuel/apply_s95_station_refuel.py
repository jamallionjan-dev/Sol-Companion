"""s95 station_survey (2026-11-11): station refuel ("عبي السيارة بنزين من الكازية") succeeded about 1 in 10 in the logs.
Causes (DOCS/PLAN_station_survey.md): her walk to the fuel cap was cut by move_check's "1.5 tiles from him: there" while he
sat in the car; she stood the car with no free square between the cap and the pump; the Java park found no pose at all.
This adds SolStationSurvey.lua (station read once per life, poses with the cap beside a pump and a free standing square,
drive, check from the real stop, re-park at most twice) and hooks it into SolFuel (car_near / park / park_status and the
walk squares of "car") and SolMoveCheck (her walk to the cap is not a walk to him). Switch station_survey, written OFF
into SolFixes_LAB.txt (a missing switch reads ON in the lab). Idempotent; refuses when an anchor is not found exactly once.
Game closed only. usage: apply_s95_station_refuel.py <client dir> [<switch file>]"""
import os, shutil, sys
CL = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)
HERE = os.path.dirname(os.path.abspath(__file__))

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

F = os.path.join(CL, "SolFuel.lua")
# 1. what the survey needs from SolFuel (its locals), right after solFuelHeld
edit(F,
     'function U.solFuelHeld() return job ~= nil or nowMs() < heldUntil end' + NL,
     'function U.solFuelHeld() return job ~= nil or nowMs() < heldUntil end' + NL +
     'U.solFuelParts = { theCar = theCar, station = station, hasPower = hasPower, freeSquare = freeSquare,   -- s95 station_survey' + NL +
     '    walking = function() return job ~= nil and job.kind == "car" and job.phase == "walk" end }' + NL)
# 2. car_near / park / park_status go to the survey while the switch is on; cancel also ends its park order
edit(F,
     '    local s = actor()' + NL + '    if s == nil then return false, "no_sol" end' + NL,
     '    local s = actor()' + NL + '    if s == nil then return false, "no_sol" end' + NL +
     '    local SS_ = rawget(_G, "SolStationSurvey")                                    -- s95 station_survey: the station decides where she stops and stands' + NL +
     '    if type(SS_) == "table" and type(SS_.on) == "function" and SS_.on() then' + NL +
     '        if opt == "car_near" or opt == "park" or opt == "park_status" then return SS_.handle(opt, s) end' + NL +
     '        if opt == "cancel" then pcall(SS_.cancel) end' + NL +
     '    end' + NL)
# 3. the walk squares of "car": free now, not under any car, not his square, nearest to the cap first
edit(F,
     '    job.squares = workSquares(cx, cy, reach, s, veh)' + NL,
     '    job.squares = workSquares(cx, cy, reach, s, veh)' + NL +
     '    local SS_ = rawget(_G, "SolStationSurvey")                                    -- s95 station_survey' + NL +
     '    if job.kind == "car" and type(SS_) == "table" and type(SS_.on) == "function" and SS_.on() then' + NL +
     '        local okS_, sq_ = pcall(SS_.standSquares, s, veh, cx, cy, reach)' + NL +
     '        if okS_ and type(sq_) == "table" then job.squares = sq_ end' + NL +
     '    end' + NL)

MC = os.path.join(CL, "SolMoveCheck.lua")
edit(MC,
     '        if px ~= nil and math.floor(pz) == math.floor(az) and math.floor(tz) == math.floor(az)' + NL,
     '        local SU_ = g("SolUI")                                                     -- s95: her walk to the fuel cap is not a walk to him' + NL +
     '        local errand_ = type(SU_) == "table" and type(SU_.solFuelWalking) == "function" and SU_.solFuelWalking() == true' + NL +
     '        if not errand_ and px ~= nil and math.floor(pz) == math.floor(az) and math.floor(tz) == math.floor(az)' + NL)

shutil.copy(os.path.join(HERE, "SolStationSurvey.lua"), os.path.join(CL, "SolStationSurvey.lua"))
A = os.path.join(CL, "SolAuthority.lua")
if '"station_survey"' not in open(A, encoding="utf-8").read():
    edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "station_survey",' + NL)
fix = sys.argv[2] if len(sys.argv) > 2 else os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix):
    txt = open(fix, encoding="utf-8").read()
    if "station_survey=" not in txt:
        with open(fix, "a", encoding="utf-8", newline="") as h: h.write(("" if txt.endswith(NL) else CRLF) + "station_survey=off" + CRLF)
print("s95 station_survey applied (switch station_survey: off until Jamal turns it on)")

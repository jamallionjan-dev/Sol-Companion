"""s80 speed_levels (Jamal 2026-11-10): the GPS panel's three speed buttons drive at بطيء 20, متوسط 40, سريع 65 km/h.
Game closed only. In place and idempotent: every edit is skipped when its marker is already there; anchors are lines no
other staged installer (s76..s79) touches, so the order does not matter.

Before (drive_fast on): SPEEDS 10/20/30 + 10 = 20/30/40 real; the log printed the table value (10 too low); a mid-drive
button press sent SPEEDS without the +10; the ETA used SPEEDS. With speed_levels on all four use the real speed.
SCDriving caps a drive at 70 with the switch on (the jar's new ceiling, build_s80_speed_levels.py), else as before:
drive_fast 50 (it said 60, but the old jar clamped every cruise to 50, so 50 is what it always was) or 30.
SolSpeedGov.lua: the bend/scan governor for cruises above 30 (see its header); one hook line after lookAhead in the tick.

  copies   SolSpeedGov.lua -> <client dir>
  edits    SolAuthority.lua  A.FIXES += "speed_levels"
           SolGPS.lua        realKmh80 after the SPEEDS line; drive, log, mid-drive button, ETA use it
           SCDriving.lua     drive cap, setSpeed cap, governor hook
           <Zomboid>/Lua/SolFixes_LAB.txt  speed_levels=on (only when missing)
Needs the s80 jar (build_s80_speed_levels.py) for 65: the old jar clamps every cruise to 50 (SCDriveControl.clampCruise).
usage: apply_s80_speed_levels.py <client dir>"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "speed_levels"
ON = '(type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("%s") == true)'


def edit(path, old, new, done_marker):
    t = open(path, encoding="utf-8", newline="").read()
    if done_marker in t: return "kept"
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    return "edited"


# ---------------------------------------------------------------- SolGPS.lua
GPS_SPEEDS = 'local SPEEDS = { slow = 10, normal = 20, fast = 30 }          -- LF caps companion driving at 30 km/h\n'
GPS_REAL = ('local SPEEDS80 = { slow = 20, normal = 40, fast = 65 }       -- Sol fix speed_levels: the buttons\' real km/h\n'
            'local function fixOn80(n) local A = rawget(_G, "SolAuthority"); return type(A) == "table" and type(A.on) == "function" and A.on(n) == true end\n'
            'local function realKmh80(key)                                -- what the car is really asked for\n'
            '    if fixOn80("speed_levels") then return SPEEDS80[key] or 20 end\n'
            '    return (SPEEDS[key] or 10) + (fixOn80("drive_fast") and 10 or 0)\n'
            'end\n')
GPS_DRIVE_OLD = ('local ok, why = D.drive(s, goal, { speedKmh = (SPEEDS[G.speed] or 10) + ((type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("drive_fast") == true) and 10 or 0), blockWaitMs = 2500 })')
GPS_DRIVE_NEW = 'local ok, why = D.drive(s, goal, { speedKmh = realKmh80(G.speed), blockWaitMs = 2500 })   -- Sol fix speed_levels'
GPS_LOG_OLD = '        .. " at " .. SPEEDS[G.speed] .. " km/h " .. tostring(why or ""))\n'
GPS_LOG_NEW = '        .. " at " .. tostring(realKmh80(G.speed)) .. " km/h " .. tostring(why or ""))   -- Sol fix speed_levels: the real speed\n'
GPS_BTN_OLD = 'pcall(Ds.setSpeed, sol(), SPEEDS[h.arg]) end'
GPS_BTN_NEW = 'pcall(Ds.setSpeed, sol(), fixOn80("speed_levels") and realKmh80(h.arg) or SPEEDS[h.arg]) end   -- Sol fix speed_levels: same speed as a new drive'
GPS_ETA_OLD = 'local kmh = math.max(5, tonumber(SPEEDS and SPEEDS[G.speed]) or 20)'
GPS_ETA_NEW = 'local kmh = math.max(5, tonumber((fixOn80("speed_levels") and realKmh80(G.speed) or (SPEEDS and SPEEDS[G.speed]))) or 20)   -- Sol fix speed_levels'

# ---------------------------------------------------------------- SCDriving.lua
DRV_CAP_OLD = ('    job.speedKmh = math.max(0, math.min(' + ON % "drive_fast" + ' and 60 or 30, finite(options.speedKmh) or 10))\n')
DRV_CAP_NEW = ('    job.speedKmh = math.max(0, math.min(' + ON % "speed_levels" + ' and 70 or (' + ON % "drive_fast" + ' and 50 or 30), finite(options.speedKmh) or 10))'
               '   -- Sol fix speed_levels: 70 = the s80 jar ceiling; off: 50, what the old jar clamped drive_fast\'s 60 to\n')
DRV_SET_OLD = '    if not job or not kmh or kmh <= 0 or kmh > 60 then return false, "no_drive" end\n'
DRV_SET_NEW = ('    local levels80 = ' + ON % "speed_levels" + '   -- Sol fix speed_levels\n'
               '    if not job or not kmh or kmh <= 0 or kmh > (levels80 and 70 or 60) then return false, "no_drive" end\n'
               '    if not levels80 then kmh = math.min(kmh, 50) end                         -- the old jar\'s ceiling, as before\n')
DRV_HOOK_OLD = '                    lookAhead(job, status, current)\n'
DRV_HOOK_NEW = (DRV_HOOK_OLD +
                '                    do local G80 = rawget(_G, "SolSpeedGov"); if type(G80) == "table" and type(G80.tick) == "function" then'
                ' local okG, errG = pcall(G80.tick, job, status, current, followNative, method); if not okG then print("[SolDrive] s80 governor: " .. tostring(errG)) end end end'
                '   -- Sol fix speed_levels\n')


def client(cl):
    assert os.path.isfile(os.path.join(cl, "SolAuthority.lua")), "not a Sol client dir: " + cl
    src = os.path.join(HERE, "SolSpeedGov.lua")
    body = open(src, encoding="ascii").read()
    assert 'M.VERSION = "0.1.0"' in body
    shutil.copy(src, os.path.join(cl, "SolSpeedGov.lua")); print("copied SolSpeedGov.lua")
    print("SolAuthority", edit(os.path.join(cl, "SolAuthority.lua"), "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "%s",' % FIX + NL, '"%s"' % FIX))
    gps = os.path.join(cl, "SolGPS.lua")
    print("SolGPS real", edit(gps, GPS_SPEEDS, GPS_SPEEDS + GPS_REAL, "local SPEEDS80 = "))
    print("SolGPS drive", edit(gps, GPS_DRIVE_OLD, GPS_DRIVE_NEW, GPS_DRIVE_NEW))
    print("SolGPS log", edit(gps, GPS_LOG_OLD, GPS_LOG_NEW, "tostring(realKmh80(G.speed)) .. \" km/h"))
    print("SolGPS button", edit(gps, GPS_BTN_OLD, GPS_BTN_NEW, "realKmh80(h.arg)"))
    print("SolGPS eta", edit(gps, GPS_ETA_OLD, GPS_ETA_NEW, 'fixOn80("speed_levels") and realKmh80(G.speed) or (SPEEDS'))
    drv = os.path.join(cl, "SCDriving.lua")
    print("SCDriving cap", edit(drv, DRV_CAP_OLD, DRV_CAP_NEW, "70 = the s80 jar ceiling"))
    print("SCDriving setSpeed", edit(drv, DRV_SET_OLD, DRV_SET_NEW, "local levels80 = "))
    print("SCDriving governor", edit(drv, DRV_HOOK_OLD, DRV_HOOK_NEW, 'rawget(_G, "SolSpeedGov")'))
    fixfile = os.path.join(cl, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
    if os.path.exists(fixfile):
        have = open(fixfile, encoding="utf-8").read()
        if FIX + "=" not in have:
            with open(fixfile, "a", encoding="utf-8", newline="") as h:
                if have and not have.endswith(NL): h.write(CRLF)
                h.write(FIX + "=on" + CRLF)
            print("SolFixes_LAB", FIX + "=on")


if __name__ == "__main__":
    client(sys.argv[1])
    print("s80 speed_levels applied")

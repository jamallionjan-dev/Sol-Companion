"""s82 preview_calm (the FPS look at the 2026-11-10 21:43-22:16 drives). Game closed only. In place and idempotent.

What was ours: the GPS panel re-plans its preview route every 4 s from where the car is, also while she drives (the drive has its
own route; the preview is only the drawing and the km / min line). Each re-plan is the Living Fellows router (Java, not timed in the
log) and, when that gives up (INCOMPLETE_MAP_DATA, 21:43:59-22:02:12, every 4 s), the whole-map A* of SolStaticRoads: 22-52 ms on
one frame. Its 20 s cache never hits while moving (the key holds the start rounded to 8 tiles; she moves 30+ tiles in 4 s).
With the switch on:
  - while the car moves (> 5 km/h) the preview re-plans every 12 s instead of 4 s (parked: 4 s, as before);
  - SolPerf gets two more lines: gps_preview (the preview's planner calls) and drive_tick (Living Fellows' SC.Driving.tick with
    Sol's patches in it: lookAhead, the s80 governor, the ladder), so the next drive shows what ours costs per 15 s.
  edits    SolGPS.lua        previewTick: the gap line, a timer round planFromPoint; wrapTick: a timer round D.tick
           SolAuthority.lua  A.FIXES += "preview_calm"
           <Zomboid>/Lua/SolFixes_LAB.txt  preview_calm=on (only when missing)
Anchors: lines no staged installer (s76..s81, s82 address_target) touches.
usage: apply_s82_preview_calm.py <client dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "preview_calm"
ON = '(type(rawget(_G, "SolAuthority")) == "table" and type(SolAuthority.on) == "function" and SolAuthority.on("preview_calm") == true)'

GAP_OLD = '    if P.key == key and P.at and t - P.at < 4000 then return end\n'
GAP_NEW = (GAP_OLD +
           '    if P.key == key and P.at and t - P.at < 12000 and ' + ON + ' then   -- Sol fix preview_calm: moving, the preview is only a drawing\n'
           '        local v82 = playerVehicle() or (sol() and call(sol(), "getVehicle"))\n'
           '        if v82 and math.abs(tonumber((call(v82, "getCurrentSpeedKmHour"))) or 0) > 5 then return end\n'
           '    end\n')
PLAN_OLD = '    local ok, route, why = pcall(R.planFromPoint, o, { x = G.dest.x, y = G.dest.y, z = 0 }, true)\n'
PLAN_NEW = ('    local t82 = nowMs()   -- Sol fix preview_calm: timed for SolPerf\n' + PLAN_OLD +
            '    if U.perfAdd and ' + ON + ' then U.perfAdd("gps_preview", nowMs() - t82) end\n')
TICK_OLD = '    D.tick = function(...) lfTicks = lfTicks + 1; return orig(...) end\n'
TICK_NEW = ('    D.tick = function(...) lfTicks = lfTicks + 1\n'
            '        if U.perfAdd and ' + ON + ' then local t82 = nowMs(); local a, b, c = orig(...); U.perfAdd("drive_tick", nowMs() - t82); return a, b, c end   -- Sol fix preview_calm\n'
            '        return orig(...) end\n')


def edit(path, old, new, done_marker):
    t = open(path, encoding="utf-8", newline="").read()
    if done_marker in t: return "kept"
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    return "edited"


def client(cl):
    assert os.path.isfile(os.path.join(cl, "SolAuthority.lua")) and os.path.isfile(os.path.join(cl, "SolGPS.lua")), "not a Sol client dir: " + cl
    gps = os.path.join(cl, "SolGPS.lua")
    t = open(gps, encoding="utf-8").read()
    for name in ("local function nowMs()", "local function sol()", "local function playerVehicle()", "local function call("):
        assert name in t, "SolGPS.lua has no " + name
    print("SolGPS gap", edit(gps, GAP_OLD, GAP_NEW, "Sol fix preview_calm: moving"))
    print("SolGPS timer", edit(gps, PLAN_OLD, PLAN_NEW, '"gps_preview"'))
    print("SolGPS drive_tick", edit(gps, TICK_OLD, TICK_NEW, '"drive_tick"'))
    print("SolAuthority", edit(os.path.join(cl, "SolAuthority.lua"), "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "%s",' % FIX + NL, '"%s"' % FIX))
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
    print("s82 preview_calm applied")

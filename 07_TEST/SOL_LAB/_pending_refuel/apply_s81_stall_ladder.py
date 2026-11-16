"""s81 stall_ladder (Jamal 2026-11-08 standing rule: a driver never stands still), game side only. No Java change.

Live 2026-11-10 22:04:42 and 22:08:15: after the Java way round failed (stalled / goal_not_free x3) jnavStart refused (3 fails,
none counted as "no way"), jnavReroute asked SolRoadFirst.mayReroute, which found "nothing real" at the stopping point, and
parkResult(failed, no_way_round) parked the drive: she stood until Jamal pressed drive again. With the switch on, every
failure feeds SolStallLadder: replan from here (a goal not yet tried, further on or the other side of the lane) -> angled
nudge -> back up 3-4 tiles -> replan free to back up -> one plain line and another road. Bounded per drive.
  copies   SolStallLadder.lua
  edits    SCDriving.lua      ops table before tryBypass; tryBypass hook; jnavReroute force flag; jnav done/failed hooks;
                              steer stalled hook; the watchdog before the jnav branch.  (Away from s80's lines: the speed
                              caps in Driving.drive / Driving.setSpeed and the lookAhead hook line are not touched.)
           SolAuthority.lua   A.FIXES += "stall_ladder"
           <Zomboid>/Lua/SolFixes_LAB.txt  stall_ladder=on (only when missing; only when the file exists)
Game closed only. In place, idempotent.
usage: apply_s81_stall_ladder.py <client dir>"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)
FIX = "stall_ladder"
TAG = "-- Sol fix stall_ladder"


def edit(path, old, new, done_marker):
    t = open(path, encoding="utf-8", newline="").read()
    if done_marker in t: return "kept"
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    return "edited"


# ---------------------------------------------------------------- SCDriving.lua
OPS_OLD = "local function tryBypass(job, status, current)\n"
OPS_NEW = '''-- Sol fix stall_ladder (s81): every stalled or failed way round feeds the next rung at once (SolStallLadder.lua).
local function slOn()
    local L = rawget(_G, "SolStallLadder")
    if solFixOn("stall_ladder") and type(L) == "table" and type(L.next) == "function" then return L end
    return nil
end
local SL_OPS = nil
local function slOps()
    if SL_OPS then return SL_OPS end
    SL_OPS = {
        log = function(job, text) ladderLog(job, text) end,
        pose = function(job)
            local xOk, x = method(job.vehicle, "getX")
            local yOk, y = method(job.vehicle, "getY")
            x, y = xOk and finite(x), yOk and finite(y)
            local hx, hy = carHeading(job.vehicle)
            if not x or not y or not hx then return nil end
            return x, y, hx, hy
        end,
        size = function(job)
            local P = rawget(_G, "SolBypass")
            if type(P) ~= "table" or type(P.measure) ~= "function" then return nil end
            local ok, size = pcall(P.measure, job.vehicle)
            return ok and type(size) == "table" and size or nil
        end,
        points = function(job) return type(job.route) == "table" and job.route.points or nil end,
        free = function(job, x, y, hx, hy, size)
            local P, L = rawget(_G, "SolBypass"), rawget(_G, "SolStallLadder")
            if type(P) ~= "table" or type(L) ~= "table" then return nil end
            local ok, free = pcall(L.spotFree, P.world, x, y, hx, hy, size.halfLength, size.halfWidth, job.vehicle)
            if ok then return free end
            return nil
        end,
        plan = function(job, sx, sy, hx, hy, gx, gy, ghx, ghy, size, kind, wide, current)
            if job.jnav or not jnavReady() then return false end
            jnavSendBans(job)
            if wide then
                local clear, mayTurn = rawget(_G, "solNavCorridorClear"), rawget(_G, "solNavMayTurnBack")
                if type(clear) == "function" then pcall(clear) end
                if type(mayTurn) == "function" then pcall(mayTurn) end
            end
            local ok, started = pcall(rawget(_G, "solNavPlan"), job.vehicle, sx, sy, hx, hy, gx, gy, ghx, ghy, size.wheelbase, size.kmax)
            if not ok or started ~= true then return false end
            job.jnav = { since = current, sl = kind }
            job.bypass, job.phase, job.blockedSince = true, "bypassing", nil
            job.lastProgressAt, job.lastProgressX, job.lastProgressY = nil, nil, nil
            ladderLog(job, "drawing the way round in Java")
            return true
        end,
        nudge = function(job, x, y, hx, hy, ox, oy, current)
            local P = rawget(_G, "SolBypass")
            if type(P) ~= "table" or type(P.nudge) ~= "function" then return false end
            local ok, points = pcall(P.nudge, x, y, hx, hy, ox, oy)
            if not ok or type(points) ~= "table" then return false end
            return startSteer(job, points, "nudge", current) == "started"
        end,
        reroute = function(job, status)
            job.slForce = true
            local ok, rerouted = pcall(jnavReroute, job, status)
            job.slForce = nil
            if not ok then ladderLog(job, "stall_ladder: road planner error: " .. tostring(rerouted)) end
            return ok and rerouted == true and not job.parked
        end,
        park = function(job, reason) return parkResult(job, "failed", reason) end,
        say = function(job, line)
            local D = SC.Dialogue
            if type(D) ~= "table" or type(D.emitResolved) ~= "function" then return false end
            local ok, spoken = pcall(D.emitResolved, job.actor, "drive_stuck", line)
            return ok and spoken == true
        end,
    }
    return SL_OPS
end

local function tryBypass(job, status, current)
'''
BYPASS_OLD = '''    if (job.ladder or 1) > 5 then return nil end
    if current - job.blockedSince < BYPASS_FIRST_MS then return "wait" end
'''
BYPASS_NEW = '''    do local SL = slOn(); if SL then                                                       -- Sol fix stall_ladder: the ladder owns a stop
        if current - job.blockedSince < BYPASS_FIRST_MS then return "wait" end
        SL.onBlocked(job, status, current, slOps())
        return "started"
    end end
''' + BYPASS_OLD
REROUTE_OLD = '''    if type(RF) == "table" and not RF.mayReroute(job, status, job.vehicle) then return false end
'''
REROUTE_NEW = '''    if type(RF) == "table" and not job.slForce and not RF.mayReroute(job, status, job.vehicle) then return false end   -- Sol fix stall_ladder: every rung failed, the way is shut
'''
WATCH_OLD = '''                if job.jnav then
                    local outcome, why = jnavTick(job, current)
'''
WATCH_NEW = '''                local slFired = false                                                   -- Sol fix stall_ladder: nothing may stand still
                do local SL = slOn(); if SL and not job.jnav and not job.steer and not job.unstick then slFired = SL.watch(job, state, status, current, slOps()) == true end end
                if slFired then
                elseif job.jnav then
                    local outcome, why = jnavTick(job, current)
'''
DONE_OLD = '''                    if outcome == "done" then
                        job.jnav, job.bypass, job.phase, job.ladder, job.jnavFails, job.jnavExtra, job.jnavNoWay = nil, nil, "replanning", 1, 0, 0, 0
'''
DONE_NEW = '''                    if outcome == "done" and slOn() and job.jnav.sl == "reverse" then          -- Sol fix stall_ladder: backing up is a rung, not the way past
                        job.jnav = nil
                        local _ = rawget(_G, "solNavStop") and pcall(rawget(_G, "solNavStop"))
                        if not slOn().onDone(job, "reverse", status, current, slOps()) then job.bypass, job.phase = nil, "replanning"; planJob(job) end
                    elseif outcome == "done" then
                        do local SL = slOn(); if SL then SL.passed(job) end end
                        job.jnav, job.bypass, job.phase, job.ladder, job.jnavFails, job.jnavExtra, job.jnavNoWay = nil, nil, "replanning", 1, 0, 0, 0
'''
FAIL_OLD = '''                        if not jnavStart(job, finite(status.blockedX), finite(status.blockedY), current, 0) and not jnavReroute(job, status) then parkResult(job, "failed", "no_way_round") end
'''
FAIL_NEW = '''                        local SLf = slOn()
                        if SLf then SLf.onFail(job, why, status, current, slOps())                 -- Sol fix stall_ladder: every failure feeds the next rung
                        elseif not jnavStart(job, finite(status.blockedX), finite(status.blockedY), current, 0) and not jnavReroute(job, status) then parkResult(job, "failed", "no_way_round") end
'''
STEER_OLD = '''                        local _ = call("driveSet", job.actor, 0, 0, true)
                        if climbLadder(job, status, current) == nil then job.phase = "replanning"; planJob(job) end
'''
STEER_NEW = '''                        local _ = call("driveSet", job.actor, 0, 0, true)
                        local SLs = slOn()
                        if SLs then SLs.onFail(job, "steer_stalled", status, current, slOps())      -- Sol fix stall_ladder
                        elseif climbLadder(job, status, current) == nil then job.phase = "replanning"; planJob(job) end
'''
DRV_EDITS = [
    ("ops", OPS_OLD, OPS_NEW, "local function slOps()"),
    ("tryBypass", BYPASS_OLD, BYPASS_NEW, "the ladder owns a stop"),
    ("jnavReroute", REROUTE_OLD, REROUTE_NEW, "not job.slForce and"),
    ("watchdog", WATCH_OLD, WATCH_NEW, "local slFired = false"),
    ("jnav done", DONE_OLD, DONE_NEW, 'job.jnav.sl == "reverse"'),
    ("jnav failed", FAIL_OLD, FAIL_NEW, "local SLf = slOn()"),
    ("steer stalled", STEER_OLD, STEER_NEW, "local SLs = slOn()"),
]


def client(cl):
    assert os.path.isfile(os.path.join(cl, "SolAuthority.lua")) and os.path.isfile(os.path.join(cl, "SCDriving.lua")), "not a Sol client dir: " + cl
    src = os.path.join(HERE, "SolStallLadder.lua")
    body = open(src, "rb").read()
    body.decode("ascii")                                        # pure ASCII, like every Sol Lua file
    assert b'M.VERSION = "0.1.0"' in body
    dst = os.path.join(cl, "SolStallLadder.lua")
    if not os.path.exists(dst) or open(dst, "rb").read() != body:
        shutil.copy(src, dst); print("copied SolStallLadder.lua")
    else: print("kept SolStallLadder.lua")
    drv = os.path.join(cl, "SCDriving.lua")
    for name, old, new, marker in DRV_EDITS:
        print("SCDriving", name, edit(drv, old, new, marker))
    print("SolAuthority", FIX, edit(os.path.join(cl, "SolAuthority.lua"), "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "%s",' % FIX + NL, '"%s"' % FIX))
    fixfile = os.path.normpath(os.path.join(cl, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt"))
    if os.path.exists(fixfile):
        have = open(fixfile, encoding="utf-8", newline="").read()
        if FIX + "=" not in have:
            with open(fixfile, "a", encoding="utf-8", newline="") as h:
                if have and not have.endswith(NL): h.write(CRLF)
                h.write(FIX + "=on" + CRLF)
            print("SolFixes_LAB", FIX + "=on")


if __name__ == "__main__":
    client(sys.argv[1])
    print("s81_stall_ladder applied")

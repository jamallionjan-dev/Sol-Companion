"""Run only after the game is closed. A simple obstacle never brings out the old turn-around; turning back needs three forward tries that found nothing. usage: apply_s8_lua.py <SCDriving.lua>"""
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in t else "\n"
def sub(a, b):
    global t
    a, b = a.replace("\n", nl), b.replace("\n", nl)
    assert t.count(a) == 1, (a[:70], t.count(a))
    t = t.replace(a, b)
sub("""local function startUnstick(job, status, current)
""", """local function startUnstick(job, status, current)
    if solFixOn("java_nav") and type(rawget(_G, "solNavPlan")) == "function" then ladderLog(job, "no turning round for this"); return nil end
""")
sub("""        if run >= want and seg > 0.01 then return b.x, b.y, (b.x - a.x) / seg, (b.y - a.y) / seg end
""", """        if run >= want and seg > 0.01 then
            local dx, dy, over = (b.x - a.x) / seg, (b.y - a.y) / seg, run - want    -- a long straight has few points: the goal is measured along it, not at its far end
            return b.x - dx * over, b.y - dy * over, dx, dy
        end
""")
sub("""local function jnavStart(job, ox, oy, current, lead)
    if job.jnav or not jnavReady() or (job.jnavFails or 0) >= JNAV_MAX_FAILS then return false end
""", """local JNAV_NO_WAY = { no_path = true, no_path_found = true, no_corridor_wide_enough = true, out_of_time = true }
local function jnavStart(job, ox, oy, current, lead)
    if job.jnav or not jnavReady() then return false end
    local fails = job.jnavFails or 0
    local turnBack = fails == JNAV_MAX_FAILS and (job.jnavNoWay or 0) >= JNAV_MAX_FAILS     -- three forward tries found nothing at all: only now may a plan turn back
    if fails >= JNAV_MAX_FAILS and not turnBack then return false end
""")
sub("""    local ahead = lead or 0                                                 -- the car keeps rolling while the plan is drawn
""", """    local mayTurn = rawget(_G, "solNavMayTurnBack")
    if turnBack and type(mayTurn) == "function" then pcall(mayTurn); ladderLog(job, "forward is shut: she may turn back now") end
    local ahead = lead or 0                                                 -- the car keeps rolling while the plan is drawn
""")
sub("""                        job.jnav, job.bypass, job.phase, job.ladder, job.jnavFails, job.jnavExtra = nil, nil, "replanning", 1, 0, 0
""", """                        job.jnav, job.bypass, job.phase, job.ladder, job.jnavFails, job.jnavExtra, job.jnavNoWay = nil, nil, "replanning", 1, 0, 0, 0
""")
sub("""                        if why == "goal_not_free" then job.jnavExtra = (job.jnavExtra or 0) + 4 end
""", """                        if JNAV_NO_WAY[why] then job.jnavNoWay = (job.jnavNoWay or 0) + 1 end
                        if why == "goal_not_free" or JNAV_NO_WAY[why] then job.jnavExtra = (job.jnavExtra or 0) + 4 end  -- another try must be a different try
""")
sub("""    local turnBack = fails == JNAV_MAX_FAILS and (job.jnavNoWay or 0) >= JNAV_MAX_FAILS     -- three forward tries found nothing at all: only now may a plan turn back
""", """    local turnBack = fails == JNAV_MAX_FAILS and (job.jnavNoWay or 0) >= 1     -- three forward tries failed and the way really is shut: only now may a plan turn back
""")
sub("""local function tryBypass(job, status, current)
""", """-- Forward is used up: the road planner goes round this place by another street.
local function jnavReroute(job, status)
    if job.attempts == nil or job.circles == nil or job.attempts >= 3 or #job.circles >= 8 then return false end
    local xOk, x = method(job.vehicle, "getX")
    local yOk, y = method(job.vehicle, "getY")
    x, y = finite(status.blockedX) or (xOk and finite(x)), finite(status.blockedY) or (yOk and finite(y))
    if not x or not y then return false end
    job.circles[#job.circles + 1] = { x = x, y = y, radius = 12 }
    job.lastBlockX, job.lastBlockY = x, y
    job.attempts, job.phase, job.bypass = job.attempts + 1, "replanning", nil
    job.jnavFails, job.jnavNoWay, job.jnavExtra, job.ladder = 0, 0, 0, 1
    ladderLog(job, "this way is shut: another street")
    planJob(job)
    return true
end

local function tryBypass(job, status, current)
""")
sub("""    if jnavReady() and (job.jnavFails or 0) >= JNAV_MAX_FAILS then parkResult(job, "failed", "no_way_round"); return "started" end
""", """    if jnavReady() and (job.jnavFails or 0) >= JNAV_MAX_FAILS then
        if not jnavReroute(job, status) then parkResult(job, "failed", "no_way_round") end
        return "started"
    end
""")
sub("""                        if not jnavStart(job, finite(status.blockedX), finite(status.blockedY), current, 0) then parkResult(job, "failed", "no_way_round") end
""", """                        if not jnavStart(job, finite(status.blockedX), finite(status.blockedY), current, 0) and not jnavReroute(job, status) then parkResult(job, "failed", "no_way_round") end
""")
open(p, "w", encoding="utf-8", newline="").write(t)
print("applied to", p)

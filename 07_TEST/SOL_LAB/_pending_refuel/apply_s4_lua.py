"""Run only after the game is closed. Driver Lua changes from the first live test. usage: apply_s4_lua.py <SCDriving.lua>"""
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in t else "\n"
def sub(a, b):
    global t
    a, b = a.replace("\n", nl), b.replace("\n", nl)
    assert t.count(a) == 1, (a[:70], t.count(a))
    t = t.replace(a, b)
# the plan is drawn in a fraction of a second: do not start it so far ahead of the car
sub('jnavStart(job, ox, oy, current, speed / 3.6 * 0.5)', 'jnavStart(job, ox, oy, current, speed / 3.6 * 0.25)')
# a failed follow draws again from where she is before falling back to the old back-out
sub('''                        ladderLog(job, "Java way round failed: " .. tostring(why))
                        local stopped = call("driveSet", job.actor, 0, 0, true)
                        if climbLadder(job, status, current) == nil then job.phase = "replanning"; planJob(job) end
''', '''                        ladderLog(job, "Java way round failed: " .. tostring(why))
                        local stopped = call("driveSet", job.actor, 0, 0, true)
                        if not jnavStart(job, finite(status.blockedX), finite(status.blockedY), current, 0)
                            and climbLadder(job, status, current) == nil then job.phase = "replanning"; planJob(job) end
''')
open(p, "w", encoding="utf-8", newline="").write(t)
print("applied to", p)

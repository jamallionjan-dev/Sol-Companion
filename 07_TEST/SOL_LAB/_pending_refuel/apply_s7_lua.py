"""Run only after the game is closed. When the drawn way round has failed three times she stops and says so; the old turn-around is not used any more. usage: apply_s7_lua.py <SCDriving.lua>"""
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in t else "\n"
def sub(a, b):
    global t
    a, b = a.replace("\n", nl), b.replace("\n", nl)
    assert t.count(a) == 1, (a[:70], t.count(a))
    t = t.replace(a, b)
sub('''                        if not jnavStart(job, finite(status.blockedX), finite(status.blockedY), current, 0)
                            and climbLadder(job, status, current) == nil then job.phase = "replanning"; planJob(job) end
''', '''                        if not jnavStart(job, finite(status.blockedX), finite(status.blockedY), current, 0) then parkResult(job, "failed", "no_way_round") end
''')
sub('''    if jnavStart(job, finite(status.blockedX), finite(status.blockedY), current, 0) then return "started" end
    return climbLadder(job, status, current)
''', '''    if jnavStart(job, finite(status.blockedX), finite(status.blockedY), current, 0) then return "started" end
    if jnavReady() and (job.jnavFails or 0) >= JNAV_MAX_FAILS then parkResult(job, "failed", "no_way_round"); return "started" end
    return climbLadder(job, status, current)
''')
open(p, "w", encoding="utf-8", newline="").write(t)
print("applied to", p)

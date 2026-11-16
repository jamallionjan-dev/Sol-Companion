"""s95b station approach (2026-11-11). Lab 10:26: the s95 survey found 3 good poses, and the Java planner answered
no_path_found for all 3. Cause (S95bPlanReplay on the 10:26 perception dumps, the shipped planner): she stood on the road
28-36 m west of the pumps, facing north; poses 1 and 2 face west, so the plan must turn her round, and over that distance
the search spends its 60000 states (MAX_NODES) before it finds the loop; pose 3 needs 59335 of 60000 offline and fails in
the game, which adds the off-road cost. The goal handoff was right (centre -> rear axle, heading vector, cap side).
Fix (Lua only, SolStationSurvey.lua 0.2.0): further than 8 m, she first drives to an approach point beside the pose's open
lane end, facing from the car towards it, then plans the short turn into the pose from where she stopped; through the lane
ahead she backs in (solNavMayTurnBack for that plan only). A failed approach -> the next one (3 at most) -> the pose straight.
Replay: 3 of 3 poses planned (approach + pose), see test_s95b_station_approach.py.
Needs s95 installed (SolStationSurvey.lua present). Copies the staged file; idempotent.
usage: apply_s95b_station_approach.py <client dir>"""
import os, shutil, sys
CL = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(CL, "SolStationSurvey.lua")
assert os.path.exists(dst), "s95 is not installed here (no SolStationSurvey.lua): run apply_s95_station_refuel.py first"
src = os.path.join(HERE, "SolStationSurvey.lua")
new = open(src, "rb").read()
assert b'M.VERSION = "0.2.0"' in new and b"function M.approaches" in new, "the staged SolStationSurvey.lua is not the s95b one"
if open(dst, "rb").read() != new: shutil.copy(src, dst)
print("s95b station approach applied (SolStationSurvey.lua 0.2.0)")

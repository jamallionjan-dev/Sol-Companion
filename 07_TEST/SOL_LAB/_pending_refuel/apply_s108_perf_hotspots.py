"""s108 perf_hotspots: less Lua a frame for the same decisions (s106 profile, DebugLog 2026-11-11_14-48, OnTick ms/s):
LF SCRuntime.lua fn@L1344 (productionTick = LF's whole AI tick with its scheduler) 35-49 ms/s riding, 396-443 ms/s for 90 s while
she followed him on foot past the porch fence; SolBudget.lua fn@L22 1.4-3 ms/s idle, 12-21 with the world-scan / inventory slices;
SolActions.lua fn@L749 2.5-3.6 ms/s.
1. SolAuthority.on: the frame's clock (SolPerfHotspots sets A._tickNow once a frame) instead of one getTimestampMs per switch read.
2. SolActions U.trackGivenItems: her bag walked once a second only when a container it read changed (count, contents weight).
3. SolPerfHotspots: LF's own per-system numbers (SC.Performance.record) as ms/s every 15 s, switch reads/s, bag walks/skips.
Switch perf_hotspots (read at call time; off = all as before). Lua only. Install with the game closed (restart needed).
usage: apply_s108_perf_hotspots.py <client>"""
import os, sys, shutil
CL = sys.argv[1]; NL, CRLF = chr(10), chr(13) + chr(10)
HERE = os.path.dirname(os.path.abspath(__file__))
def edit(path, old, new):
    raw = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in raw else NL
    t = raw.replace(CRLF, NL)
    if new in t: print("kept " + os.path.basename(path)); return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old))
    updated = t.replace(old, new).replace(NL, nl)
    open(path, "w", encoding="utf-8", newline="").write(updated); print("edited " + os.path.basename(path))

src, dst = os.path.join(HERE, "SolPerfHotspots.lua"), os.path.join(CL, "SolPerfHotspots.lua")
if os.path.exists(dst) and open(dst, "rb").read() == open(src, "rb").read(): print("kept SolPerfHotspots.lua")
else: shutil.copy(src, dst); print("copied SolPerfHotspots.lua")

A = os.path.join(CL, "SolAuthority.lua")
# 1. switch reads on the frame clock
authority = open(A, encoding="utf-8", newline="").read()
if "s108 perf_hotspots: the frame's clock" not in authority:
    edit(A, '''function A.on(fix)
    local now = (getTimestampMs and getTimestampMs()) or 0
''', '''function A.on(fix)
    local now, hot_ = nil, switches ~= nil and A._tickNow ~= nil and (A._tickCalls or 0) < 4000 and switches.perf_hotspots   -- s108 perf_hotspots: the frame's clock
    if hot_ == nil then hot_ = isLab() end
    if hot_ == true then A._tickCalls = (A._tickCalls or 0) + 1; now = A._tickNow
    else now = (getTimestampMs and getTimestampMs()) or 0 end
''')
else: print("kept SolAuthority.lua (frame clock)")
if '"perf_hotspots"' not in open(A, encoding="utf-8").read():
    edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "perf_hotspots",   -- s108: switch reads on the frame clock; her bag walked only when it changed; LF per-system ms/s every 15 s' + NL)
else: print("kept SolAuthority.lua (FIXES)")

S = os.path.join(CL, "SolActions.lua")
# 2a. the walk can note the containers it read (callers that pass one argument get the same list as before)
actions = open(S, encoding="utf-8", newline="").read()
if "s108 perf_hotspots: the containers this walk read" not in actions:
    edit(S, '''local function bagItems(actor)
    local out = {}
    local function walk(container, depth)
        local list = mcall(container, "getItems")
''', '''local function bagItems(actor, seen)
    local out = {}
    local function walk(container, depth)
        if seen then seen[#seen + 1] = container end   -- s108 perf_hotspots: the containers this walk read
        local list = mcall(container, "getItems")
''')
else: print("kept SolActions.lua (walk containers)")
# 2b. unchanged bag = no new item = no walk
actions = open(S, encoding="utf-8", newline="").read()
if "s108 perf_hotspots: her bag unchanged" not in actions:
    edit(S, '''    local sol = U.solActor and U.solActor()
    if not sol then return end
    local now = {}
    for _, rec in ipairs(bagItems(sol)) do now[rec.item] = true end
    if lastSeen then
        local p = getSpecificPlayer and getSpecificPlayer(0)
        local near = p and math.sqrt((sol:getX() - p:getX()) ^ 2 + (sol:getY() - p:getY()) ^ 2) <= 3
        for it in pairs(now) do if not lastSeen[it] and near then U.givenByPlayer[it] = true end end
    end
    lastSeen = now
end''', '''    local sol = U.solActor and U.solActor()
    if not sol then return end
    local H_ = rawget(_G, "SolPerfHotspots")   -- s108 perf_hotspots: her bag unchanged since the last walk = nothing new to remember
    local hot_ = type(H_) == "table" and type(H_.on) == "function" and H_.on() == true
    if hot_ and lastSeen ~= nil and H_.bagSame(sol) then return end
    local seen_ = hot_ and {} or nil
    local now = {}
    for _, rec in ipairs(bagItems(sol, seen_)) do now[rec.item] = true end
    if lastSeen then
        local p = getSpecificPlayer and getSpecificPlayer(0)
        local near = p and math.sqrt((sol:getX() - p:getX()) ^ 2 + (sol:getY() - p:getY()) ^ 2) <= 3
        for it in pairs(now) do if not lastSeen[it] and near then U.givenByPlayer[it] = true end end
    end
    lastSeen = now
    if seen_ then H_.bagMark(sol, seen_) elseif type(H_) == "table" then H_.bag = nil end
end''')
else: print("kept SolActions.lua (unchanged-bag cache)")

fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fix):
    body = open(fix, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in body else NL
    if "perf_hotspots" not in body:
        with open(fix, "a", encoding="utf-8", newline="") as h: h.write(("" if body.endswith(NL) or body == "" else nl) + "perf_hotspots=on" + nl)
        print("SolFixes_LAB.txt: perf_hotspots=on")
    else: print("kept SolFixes_LAB.txt")
print("s108 perf_hotspots applied")

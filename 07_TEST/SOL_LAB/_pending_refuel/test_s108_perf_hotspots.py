"""s108 perf_hotspots offline (kahlua_env = lupa with Kahlua's rules). Real files after the installer, on a temp copy of the live
client: SolAuthority.lua, SolActions.lua, SolPerfHotspots.lua, LF's SCPerformance.lua. Fakes stand in for the game only.
Shows, each with the switch off (= before) and on (= after):
 A. switch reads: 30 s at 51 frames/s, 60 reads a frame, the switch file changed twice -> the same answer for every read; Java clock
    calls per frame (before: one per read; after: one per frame); lupa wall time ratio. A second run with the clock moving inside
    the frame shows how many reads differ (only reads in the one frame where a reload lands).
 B. her bag: a 100 s replay at 51 frames/s of SolActions' own OnTick (the real handler) with a 300-item kit (root, a backpack with
    a pouch, an empty fanny pack): items he gives (near), items she picks up near and far, eats, moves into the pouch, a swap, a
    lighter that loses weight, a new actor -> U.givenByPlayer the same after every second; Java calls and lupa time before/after.
 C. LF breakdown: SC.Performance.record wrapped -> LF's own snapshot identical with and without it; the line's ms/s; off restores
    the original function.
 Plus: installer idempotent (twice), switch listed, LAB file line, install order with the pending s107 both ways, ASCII,
 compiles, tonumber gate, jarcall gate.
Run: set PYTHONIOENCODING=utf-8 & python test_s108_perf_hotspots.py [client dir]"""
import os, sys, shutil, subprocess, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from kahlua_env import lua51
CL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
TOOLS = os.path.join(HERE, "..", "..", "..", "05_TOOLS", "sol_kahlua")
FAIL, P = [], []
def ck(n, c, d=""): print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else "")); (P if c else FAIL).append(n)

# ---------------------------------------------------------------- install on a temp copy (profile layout, so the LAB file is found)
tmp = tempfile.mkdtemp(prefix="s108_")
cl = os.path.join(tmp, "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(cl)
os.makedirs(os.path.join(tmp, "profile", "Zomboid", "Lua"))
labfix = os.path.join(tmp, "profile", "Zomboid", "Lua", "SolFixes_LAB.txt")
open(labfix, "w", newline="").write("retry_reset=on\ninstinct_only=off\n")
for f in os.listdir(CL):
    if f.endswith(".lua"): shutil.copy(os.path.join(CL, f), cl)
ORIG = {f: open(os.path.join(cl, f), encoding="utf-8", newline="").read() for f in ("SolAuthority.lua", "SolActions.lua")}
APPLY = os.path.join(HERE, "apply_s108_perf_hotspots.py")
r1 = subprocess.run([sys.executable, APPLY, cl], capture_output=True, text=True)
r2 = subprocess.run([sys.executable, APPLY, cl], capture_output=True, text=True)
ck("installer runs", r1.returncode == 0 and "applied" in r1.stdout, r1.stdout + r1.stderr)
ck("installer second run changes nothing", r2.returncode == 0 and "edited" not in r2.stdout and "copied" not in r2.stdout
   and r2.stdout.count("perf_hotspots=on") == 0, r2.stdout + r2.stderr)
ck("LAB file gets perf_hotspots=on once", open(labfix).read().count("perf_hotspots=on") == 1, open(labfix).read())
AUTH = open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8", newline="").read()
ACTS = open(os.path.join(cl, "SolActions.lua"), encoding="utf-8", newline="").read()
HOT = open(os.path.join(cl, "SolPerfHotspots.lua"), encoding="utf-8", newline="").read()
ck("switch listed once in A.FIXES", AUTH.count('"perf_hotspots"') == 1)
ck("SolAuthority: one s108 hook", AUTH.count("-- s108 perf_hotspots") == 1)
ck("SolActions: two s108 hooks", ACTS.count("-- s108 perf_hotspots") == 2)
ck("CRLF kept", "\r\n" in AUTH and "\r\n" in ACTS and AUTH.count("\n") == AUTH.count("\r\n") and ACTS.count("\n") == ACTS.count("\r\n"))
for name, txt in (("SolAuthority.lua", AUTH), ("SolActions.lua", ACTS), ("SolPerfHotspots.lua", HOT)):
    ck("ascii " + name, all(ord(c) < 128 for c in txt))
    ok, e = lua51.LuaRuntime().eval("function(s) local f, e = loadstring(s); return f ~= nil, e end")(txt)
    ck("compiles " + name, ok, e)
ck("pre-merged candidate stays byte-for-byte stable on the install check",
   ORIG["SolActions.lua"] == ACTS and "s108 perf_hotspots: the containers this walk read" in ACTS
   and "s108 perf_hotspots: her bag unchanged" in ACTS)

# ---------------------------------------------------------------- A. switch reads
ENV_A = r"""
NOW, STEP = 0, 0
CLOCKS = 0
function getTimestampMs() CLOCKS = CLOCKS + 1; local t = NOW; NOW = NOW + STEP; return t end
LOGS = {}; print = function(s) LOGS[#LOGS + 1] = tostring(s) end
SolLab = { active = true }
FILE = {}
function getFileReader(name, create)
    if name ~= "SolFixes_LAB.txt" then return nil end
    local i = 0
    return { readLine = function(self) i = i + 1; return FILE[i] end, close = function(self) end }
end
TICKS = {}
Events = { OnTick = { Add = function(f) TICKS[#TICKS + 1] = f end } }
"""
NAMES = ["shooting_discipline", "combat_plans", "item_stacks", "walk_no_vault", "reaim_hold", "instinct_only", "speed_levels",
         "perf_slice", "spatial_access", "edge_api", "not_listed_fix", "mag_fill"]
def run_reads(hot, step, frames=30 * 51, per=60):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV_A); L.execute(AUTH)
    if hot is not None: L.execute(HOT)
    L.execute("NAMES = {" + ",".join('"%s"' % n for n in NAMES) + "}")
    L.execute("""
    function SETFILE(sd, hot)
        FILE = { "shooting_discipline=" .. sd, "combat_plans=on", "item_stacks=off", "instinct_only=off", "perf_slice=on",
                 "perf_hotspots=" .. hot }
    end
    function RUN(frames, per, step, hot)
        STEP = step
        local out, n = {}, 0
        SETFILE("on", hot)
        for f = 1, frames do
            NOW = (f - 1) * 1000 / 51
            if f == 7 * 51 then SETFILE("off", hot) end
            if f == 13 * 51 then SETFILE("on", hot) end
            for _, h in ipairs(TICKS) do h() end
            for i = 1, per do
                local nm = NAMES[(i % #NAMES) + 1]
                n = n + 1; out[n] = SolAuthority.on(nm) and "1" or "0"
            end
        end
        return table.concat(out)
    end""")
    t0 = time.perf_counter()
    s = L.eval("RUN")(frames, per, step, "on" if hot else "off")
    dt = time.perf_counter() - t0
    return s, L.eval("CLOCKS"), dt, L
off_s, off_c, off_t, _ = run_reads(False, 0)
on_s, on_c, on_t, LA = run_reads(True, 0)
frames, per = 30 * 51, 60
ck("A: every switch read gives the same answer (30 s, %d reads, two file changes)" % len(off_s), off_s == on_s and "0" in on_s,
   sum(1 for a, b in zip(off_s, on_s) if a != b))
ck("A: the shooting_discipline flip is seen (off at 7 s, on again at 13 s)", "0" in on_s[7 * 51 * per:13 * 51 * per] and on_s[-per:] == off_s[-per:])
ck("A: Java clock calls before = one per read + reloads", off_c >= frames * per, off_c)
ck("A: Java clock calls after = about one a frame", on_c <= frames * 1.1 + 40, on_c)
print("INFO A: clock calls %d -> %d (%.1f -> %.2f a frame); lupa time %.0f ms -> %.0f ms (ratio %.2f)"
      % (off_c, on_c, off_c / frames, on_c / frames, off_t * 1000, on_t * 1000, on_t / off_t))
off2, _, _, _ = run_reads(False, 0.3)
on2, _, _, _ = run_reads(True, 0.3)
diff = [i for i, (a, b) in enumerate(zip(off2, on2)) if a != b]
dframes = sorted(set(i // per for i in diff))
clusters = []
for fr in dframes:
    if clusters and fr - clusters[-1][-1] <= 1: clusters[-1].append(fr)
    else: clusters.append([fr])
dnames = set(NAMES[(i % per + 1) % len(NAMES)] for i in diff)
ck("A: clock moving inside the frame (0.3 ms a read): only reads of the switch that was flipped differ, only around the two reloads"
   " that pick the flips up, each within 3 frames (60 ms of a 5 s reload period)",
   dnames <= {"shooting_discipline"} and len(clusters) <= 2 and all(len(c) <= 3 for c in clusters), (len(diff), dframes, dnames))
print("INFO A: with the clock moving in the frame, %d of %d reads differ (reload one frame earlier/later)" % (len(diff), len(off2)))
L = lua51.LuaRuntime(unpack_returned_tuples=True); L.execute(ENV_A); L.execute(AUTH); L.execute(HOT)
L.execute('FILE = { "perf_hotspots=on" }; NOW = 1000; SolAuthority.on("x"); SolAuthority._tickNow = 1000; SolAuthority._tickCalls = 3990; CLOCKS = 0')
L.execute('for i = 1, 20 do SolAuthority.on("x") end')
ck("A: no OnTick for 4000 reads (loading, menu): the real clock again", L.eval("CLOCKS") == 10, L.eval("CLOCKS"))
L.execute('SolLab = nil; FILE = {}; SolAuthority._tickNow = nil; NOW = NOW + 6000; CLOCKS = 0; R1 = SolAuthority.on("x")')
ck("A: MAIN (no SolLab), switch missing: off as before, real clock", L.eval("R1") is False and L.eval("CLOCKS") == 1)

# ---------------------------------------------------------------- B. her bag
ENV_B = r"""
NOW = 0
JCALLS = 0
local function J() JCALLS = JCALLS + 1 end
function getTimestampMs() J(); return NOW end
LOGS = {}; print = function(s) LOGS[#LOGS + 1] = tostring(s) end
SolLab = { active = true }
FILE = {}
function getFileReader(name, create)
    if name ~= "SolFixes_LAB.txt" then return nil end
    local i = 0
    return { readLine = function(self) i = i + 1; return FILE[i] end, close = function(self) end }
end
function getFileWriter() return nil end
function require() end
TICKS = {}
Events = { OnTick = { Add = function(f) TICKS[#TICKS + 1] = f end }, OnGameStart = { Add = function() end } }
-- the game: containers and items (Java objects: every method call counts)
SEQ = 0
function LIST(t) return { size = function(self) J(); return #t end, get = function(self, i) J(); return t[i + 1] end } end
function CONTAINER(red)
    local c = { items = {}, red = red or 1 }
    function c:getItems() J(); return LIST(self.items) end
    function c:getContentsWeight() J(); local w = 0; for _, it in ipairs(self.items) do w = w + it:weightOf() end; return w end
    return c
end
function ITEM(w, inner)
    SEQ = SEQ + 1
    local it = { id = SEQ, w = w, inner = inner }
    function it:getInventory() J(); return self.inner end
    function it:weightOf() return self.w + (self.inner and self.inner:getContentsWeight() * self.inner.red or 0) end
    return it
end
function ACTOR(inv)
    local a = { inv = inv, x = 100.5, y = 100.5 }
    function a:getInventory() J(); return self.inv end
    function a:getX() J(); return self.x end
    function a:getY() J(); return self.y end
    function a:getVehicle() J(); return nil end
    return a
end
PLAYER = { x = 102.5, y = 100.5 }
function PLAYER:getX() J(); return self.x end
function PLAYER:getY() J(); return self.y end
function getSpecificPlayer(i) J(); return PLAYER end
SolUI = SolUI or {}
"""
KIT = r"""
ROOT = CONTAINER()
for i = 1, 240 do ROOT.items[#ROOT.items + 1] = ITEM(0.01 * ((i % 7) + 1)) end
POUCH = CONTAINER(0.5); for i = 1, 8 do POUCH.items[#POUCH.items + 1] = ITEM(0.1) end
BACK = CONTAINER(0.3); for i = 1, 50 do BACK.items[#BACK.items + 1] = ITEM(0.2) end
BACK.items[#BACK.items + 1] = ITEM(0.2, POUCH)
FANNY = CONTAINER(0.4)
ROOT.items[#ROOT.items + 1] = ITEM(1.0, BACK)
ROOT.items[#ROOT.items + 1] = ITEM(0.3, FANNY)
SOL = ACTOR(ROOT)
SolUI.solActor = function() return SOL end
LIGHTER = ITEM(0.4); ROOT.items[#ROOT.items + 1] = LIGHTER
function GIVEN() local t = {} for it in pairs(SolUI.givenByPlayer or {}) do t[#t + 1] = it.id end table.sort(t) return table.concat(t, ",") end
EVENTS = {
    [5300] = function() ROOT.items[#ROOT.items + 1] = ITEM(0.5) end,                       -- he gives (near)
    [12600] = function() BACK.items[#BACK.items + 1] = ITEM(0.7) end,                      -- he gives into the backpack
    [20100] = function() table.remove(ROOT.items, 3) end,                                    -- she eats
    [25400] = function() local it = table.remove(ROOT.items, 10); POUCH.items[#POUCH.items + 1] = it end,   -- moved into the pouch
    [31200] = function() FANNY.items[#FANNY.items + 1] = ITEM(0.05) end,                   -- into the empty fanny pack (near)
    [40000] = function() PLAYER.x = 125.5 end,                                               -- he walks off
    [45000] = function() ROOT.items[#ROOT.items + 1] = ITEM(0.9) end,                      -- she picks up, far
    [70000] = function() PLAYER.x = 101.5 end,                                               -- back
    [72500] = function() ROOT.items[#ROOT.items + 1] = ITEM(0.25) end,                     -- she picks up, near
    [80200] = function() table.remove(ROOT.items, 20); ROOT.items[#ROOT.items + 1] = ITEM(0.33) end,   -- a swap
    [88000] = function() SOL = ACTOR(ROOT) end,                                              -- a new actor
    [93000] = function() LIGHTER.w = LIGHTER.w - 0.01 end,                                   -- lighter used
}
function RUN(frames)
    local marks = {}
    for f = 1, frames do
        NOW = math.floor((f - 1) * 1000 / 51)
        for at, fn in pairs(EVENTS) do if NOW >= at and not FIRED[at] then FIRED[at] = true; fn() end end
        for _, h in ipairs(TICKS) do h() end
        if f % 51 == 0 then marks[#marks + 1] = GIVEN() end
    end
    return table.concat(marks, "|")
end
FIRED = {}
"""
def run_bag(hot):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV_B)
    L.execute('FILE = { "perf_hotspots=%s", "perf_slice=on" }' % ("on" if hot else "off"))
    L.execute(AUTH); L.execute(HOT); L.execute(ACTS); L.execute(KIT)
    L.execute("JCALLS = 0")
    t0 = time.perf_counter()
    marks = L.eval("RUN")(100 * 51)
    dt = time.perf_counter() - t0
    return marks, L.eval("JCALLS"), dt, L
off_m, off_j, off_bt, LO = run_bag(False)
on_m, on_j, on_bt, LN = run_bag(True)
ck("B: SolActions' OnTick and the hotspot frame handler are the real ones", LN.eval("#TICKS") == 2, LN.eval("#TICKS"))
ck("B: U.givenByPlayer identical after every second of the 100 s replay", off_m == on_m, [(i, a, b) for i, (a, b) in enumerate(zip(off_m.split("|"), on_m.split("|"))) if a != b][:4])
last = off_m.split("|")[-1].split(",")
ck("B: the replay marks what it should: his 3 gifts (root, backpack, empty fanny pack), her near pick-up and the swap-in; not the far"
   " pick-up, the eaten item, the item moved into the pouch, the lighter, or anything for the new actor", off_m.split("|")[-1] == "303,304,305,307,308", off_m.split("|")[-1])
walks, skips = LN.eval("SolPerfHotspots.totals.bagWalks"), LN.eval("SolPerfHotspots.totals.bagSkips")
ck("B: walks only when something changed (10 changes in 100 s), skipped otherwise", walks <= 12 and skips >= 85, (walks, skips))
ck("B: Java calls cut", on_j < off_j * 0.35, (off_j, on_j))
print("INFO B: Java calls in 100 s %d -> %d (%.0f -> %.0f a second); bag walks %d, skipped %d; lupa time %.0f ms -> %.0f ms (ratio %.2f)"
      % (off_j, on_j, off_j / 100, on_j / 100, walks, skips, off_bt * 1000, on_bt * 1000, on_bt / off_bt))
L = lua51.LuaRuntime(unpack_returned_tuples=True); L.execute(ENV_B); L.execute('FILE = { "perf_hotspots=on" }')
L.execute(AUTH); L.execute(HOT); L.execute(ACTS); L.execute(KIT)
L.execute("SolUI.trackGivenItems(); SolUI.trackGivenItems(); JCALLS = 0; SolUI.trackGivenItems(); ONE_ON = JCALLS")
L2 = lua51.LuaRuntime(unpack_returned_tuples=True); L2.execute(ENV_B); L2.execute('FILE = { "perf_hotspots=off" }')
L2.execute(AUTH); L2.execute(HOT); L2.execute(ACTS); L2.execute(KIT)
L2.execute("SolUI.trackGivenItems(); JCALLS = 0; SolUI.trackGivenItems(); ONE_OFF = JCALLS")
print("INFO B: one unchanged-bag check: %d Java calls before, %d after" % (L2.eval("ONE_OFF"), L.eval("ONE_ON")))
ck("B: one unchanged check is a few Java calls (not hundreds)", L.eval("ONE_ON") < 25 and L2.eval("ONE_OFF") > 500, (L2.eval("ONE_OFF"), L.eval("ONE_ON")))
L.execute('FILE = { "perf_hotspots=off" }; NOW = NOW + 6000; SolPerfHotspots.nextCheck = 0; SolPerfHotspots.frame(); ROOT.items[#ROOT.items + 1] = ITEM(0.5); SolUI.trackGivenItems(); JCALLS = 0; SolUI.trackGivenItems(); OFFAGAIN = JCALLS; BAG = SolPerfHotspots.bag')
ck("B: switched off live: the full walk again, the signature dropped", L.eval("OFFAGAIN") > 500 and L.eval("BAG") is None, L.eval("OFFAGAIN"))

# ---------------------------------------------------------------- C. LF breakdown
PERF = open(os.path.join(cl, "SCPerformance.lua"), encoding="utf-8").read()
ENV_C = r"""
NOW = 0
function getTimestampMs() return NOW end
LOGS = {}; print = function(s) LOGS[#LOGS + 1] = tostring(s) end
SolLab = { active = true }
FILE = { "perf_hotspots=on" }
function getFileReader(name) local i = 0; return { readLine = function(self) i = i + 1; return FILE[i] end, close = function() end } end
function require() end
TICKS = {}
Events = { OnTick = { Add = function(f) TICKS[#TICKS + 1] = f end } }
SurvivorCompanion = {}
"""
def run_lf(hot):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(ENV_C); L.execute(PERF); L.execute(AUTH)
    if hot: L.execute(HOT)
    L.execute("ORIG = SurvivorCompanion.Performance.record")
    L.execute("""
    function RUN()
        for f = 1, 16 * 51 do
            NOW = math.floor((f - 1) * 1000 / 51)
            for _, h in ipairs(TICKS) do h() end
            local P = SurvivorCompanion.Performance
            P.record("tick.total", nil, 0.70)
            P.record("tick.pre-scheduler", nil, 0.05)
            P.record("scheduler.decision", nil, 0.40)
            if f % 5 == 0 then P.record("decision", "sc-1", 1.80) end
            if f % 10 == 0 then P.record("zombie-targeting", "sc-1", 0.30) end
        end
        local s = SurvivorCompanion.Performance.snapshot()
        local t = {}
        for _, m in ipairs(s.topSystems) do t[#t + 1] = m.key .. ":" .. m.runs .. ":" .. string.format("%.4f", m.averageMs) end
        for _, m in ipairs(s.topActors) do t[#t + 1] = m.key .. ":" .. m.runs .. ":" .. string.format("%.4f", m.averageMs) end
        return table.concat(t, " ")
    end""")
    return L.eval("RUN")(), L
snap_off, _ = run_lf(False)
snap_on, LC = run_lf(True)
ck("C: LF's own performance snapshot identical with the breakdown on", snap_off == snap_on, (snap_off, snap_on))
logs = [LC.eval("LOGS")[i] for i in range(1, len(LC.eval("LOGS")) + 1)]
line = next((m for m in logs if "LF ms/s" in m), "")
ck("C: one breakdown line after 15 s, LF numbers as ms/s (tick.total about 35.7, decision about 18.4)",
   "tick.total 35.7" in line and "decision 18.3" in line or "decision 18.4" in line, line)
print("INFO C: " + line)
LC.execute('FILE = { "perf_hotspots=off" }; NOW = NOW + 6000; SolPerfHotspots.nextCheck = 0; SolPerfHotspots.frame()')
ck("C: switched off: LF's record function is the original again", LC.eval("SurvivorCompanion.Performance.record == ORIG") is True)

# ---------------------------------------------------------------- install order with the pending s107 (both ways)
S107 = os.path.join(HERE, "apply_s107_gear_page.py")
if os.path.exists(S107):
    for order in ((S107, APPLY), (APPLY, S107)):
        t2 = tempfile.mkdtemp(prefix="s108o_")
        c2 = os.path.join(t2, "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(c2)
        os.makedirs(os.path.join(t2, "profile", "Zomboid", "Lua"))
        for f in os.listdir(CL):
            if f.endswith(".lua"): shutil.copy(os.path.join(CL, f), c2)
        rs = [subprocess.run([sys.executable, s, c2], capture_output=True, text=True) for s in order]
        a2 = open(os.path.join(c2, "SolAuthority.lua"), encoding="utf-8").read()
        ck("install order %s: both apply, both switches listed" % " -> ".join(os.path.basename(s)[6:10] for s in order),
           all(r.returncode == 0 for r in rs) and '"perf_hotspots"' in a2 and '"gear_page"' in a2, [r.stdout[-200:] + r.stderr[-300:] for r in rs])
        shutil.rmtree(t2, ignore_errors=True)

# ---------------------------------------------------------------- gates
GATE = os.path.join(TOOLS, "tonumber_check.py")
r = subprocess.run([sys.executable, GATE, cl], capture_output=True, text=True)
ck("tonumber gate (whole patched client)", r.returncode == 0, r.stdout[-400:] + r.stderr[-300:])
JAR = os.path.join(TOOLS, "jarcall_check.py")
r = subprocess.run([sys.executable, JAR, cl], capture_output=True, text=True)
ck("jarcall gate (whole patched client)", r.returncode == 0, r.stdout[-600:] + r.stderr[-300:])
ck("jarcall: SolPerfHotspots' Java names not flagged", "SolPerfHotspots" not in r.stdout, [l for l in r.stdout.splitlines() if "SolPerfHotspots" in l])
shutil.rmtree(tmp, ignore_errors=True)
print("SUMMARY pass=%d fail=%d" % (len(P), len(FAIL)))
sys.exit(1 if FAIL else 0)

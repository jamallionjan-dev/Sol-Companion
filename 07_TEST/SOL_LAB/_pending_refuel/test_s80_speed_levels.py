"""s80 speed_levels: the installer on copies, the Lua under the game's rules (kahlua_env), the jar copy, and the driving
model: LF's own driver classes (from a COPY of the lab jar, old and s80) driven through scenes with five vehicle bodies at
20 / 40 / 65 km/h, with and without the Lua governor (SolSpeedGov.tick, run for real in Lua on every 0.3 s step).
Run: set PYTHONIOENCODING=utf-8 & python test_s80_speed_levels.py [client dir]      (default: the lab client, read only)
Nothing live is touched: temporary copies only; the jar is built into a temp dir. Offline PASS is not Runtime PASS."""
import hashlib, math, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kahlua_env import lua51
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LAB_CL = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client"))
LAB_JAR = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "java", "SolCombined.jar")
GATE = os.path.join(ROOT, "05_TOOLS", "sol_kahlua", "tonumber_check.py")
JDK = r"C:\Program Files\Eclipse Adoptium\jdk-25.0.4.101-hotspot\bin"
PZ = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\projectzomboid.jar"
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, script)] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
def digest(d, names): return {n: hashlib.md5(open(os.path.join(d, n), "rb").read()).hexdigest() for n in names}
def read(p): return open(p, encoding="utf-8", newline="").read()
TMP = tempfile.mkdtemp(prefix="sol_s80_")

# ================================================================ 1. the installer on copies
CL = os.path.join(TMP, "client"); os.makedirs(CL)
FILES = ["SolAuthority.lua", "SolGPS.lua", "SCDriving.lua"]
for f in FILES: shutil.copy(os.path.join(LAB_CL, f), CL)
live = digest(LAB_CL, FILES)
b0 = digest(CL, FILES)
q1 = run("apply_s80_speed_levels.py", CL); a1 = digest(CL, FILES + ["SolSpeedGov.lua"])
q2 = run("apply_s80_speed_levels.py", CL); a2 = digest(CL, FILES + ["SolSpeedGov.lua"])
ck("installer: applies", q1.returncode == 0 and "applied" in q1.stdout, q1.stderr[-500:])
ck("installer: changes all three files", all(b0[n] != a1[n] for n in FILES))
ck("installer: idempotent (second run all kept)", q2.returncode == 0 and a1 == a2 and "edited" not in q2.stdout, q2.stdout[-300:] + q2.stderr[-300:])
ck("installer: the installed files are untouched", digest(LAB_CL, FILES) == live)
# with s79 (another agent's, also on A.FIXES) in either order
for order in (("apply_s79_horn_hold_lua.py", "apply_s80_speed_levels.py"), ("apply_s80_speed_levels.py", "apply_s79_horn_hold_lua.py")):
    if not os.path.exists(os.path.join(HERE, "apply_s79_horn_hold_lua.py")): break
    d = os.path.join(TMP, "order_" + order[0][6:9]); os.makedirs(d)
    for f in FILES + ["SolActions.lua"]: shutil.copy(os.path.join(LAB_CL, f), d)
    rs = [run(s, d) for s in order]
    au = read(os.path.join(d, "SolAuthority.lua"))
    ck("installer: with s79 in order %s -> %s" % (order[0][6:9], order[1][6:9]), all(r.returncode == 0 for r in rs) and '"horn_hold"' in au and '"speed_levels"' in au,
       " | ".join(r.stderr[-200:] for r in rs))
q = run("apply_s76_gps_roads.py", CL)
ck("installer: re-running apply_s76_gps_roads.py after s80 keeps its edits", q.returncode == 0 and "edited" not in q.stdout.replace("SolAddressBook", ""), q.stdout[-300:] + q.stderr[-300:])
for f in ("SolStaticRoads.lua", "SolStaticRoadsData.lua", "SolGPSWords.lua"):
    p = os.path.join(CL, f)
    if os.path.exists(p): os.remove(p)
g = subprocess.run([sys.executable, GATE, CL], capture_output=True, text=True, encoding="utf-8", errors="replace")
ck("lua: tonumber gate passes on the staged files", g.returncode == 0, (g.stdout + g.stderr)[-400:])
L0 = lua51.LuaRuntime()
for n in FILES + ["SolSpeedGov.lua"]:
    e = L0.eval("function(s) local f, e = loadstring(s); return e end")(read(os.path.join(CL, n)))
    ck("lua: %s compiles" % n, e is None, e)
GPS, DRV, AUTH = (read(os.path.join(CL, n)).replace("\r\n", "\n") for n in ("SolGPS.lua", "SCDriving.lua", "SolAuthority.lua"))
ck("lua: A.FIXES lists speed_levels", '"speed_levels",' in AUTH)
ck("lua: SolGPS drive asks realKmh80", "speedKmh = realKmh80(G.speed), blockWaitMs = 2500" in GPS)
ck("lua: SolGPS log prints the real speed", '" at " .. tostring(realKmh80(G.speed)) .. " km/h "' in GPS and '" at " .. SPEEDS[G.speed]' not in GPS)
ck("lua: SolGPS mid-drive button uses the real speed (switch on)", 'pcall(Ds.setSpeed, sol(), fixOn80("speed_levels") and realKmh80(h.arg) or SPEEDS[h.arg])' in GPS)
ck("lua: SolGPS ETA uses the real speed (switch on)", 'tonumber((fixOn80("speed_levels") and realKmh80(G.speed) or (SPEEDS and SPEEDS[G.speed])))' in GPS)
ck("lua: SolGPS keeps the old SPEEDS table (switch off unchanged)", "local SPEEDS = { slow = 10, normal = 20, fast = 30 }" in GPS)
ck("lua: SCDriving governor hook sits after lookAhead", re.search(r"lookAhead\(job, status, current\)\n\s+do local G80 = rawget\(_G, \"SolSpeedGov\"\)", DRV) is not None)

# ---------------------------------------------------------------- the real speeds, under Kahlua rules
blk = GPS[GPS.index("local SPEEDS = {"):GPS.index("\nend\n", GPS.index("local function realKmh80")) + 5]
def real(sw, key):
    L = lua51.LuaRuntime()
    L.execute("SW = {}; SolAuthority = { on = function(n) return SW[n] == true end }")
    for s in sw: L.execute('SW["%s"] = true' % s)
    return L.execute(blk + "\nreturn realKmh80('%s')" % key)
for key, want in (("slow", 20), ("normal", 40), ("fast", 65)):
    ck("speeds: speed_levels on, %s = %d km/h" % (key, want), real(["speed_levels", "drive_fast"], key) == want and real(["speed_levels"], key) == want)
for key, want in (("slow", 20), ("normal", 30), ("fast", 40)):
    ck("speeds: switch off, drive_fast on, %s = %d (as before)" % (key, want), real(["drive_fast"], key) == want)
ck("speeds: both off, fast = 30 (as before)", real([], "fast") == 30)

# ---------------------------------------------------------------- SCDriving caps, under Kahlua rules
capline = re.search(r"\n(    job\.speedKmh = math\.max\(0, math\.min\(.*\n)", DRV).group(1)
setfn = re.search(r"\nfunction Driving\.setSpeed\(actor, kmh\)\n.*?\nend\n", DRV, re.S).group(0)
def drive_cap(sw, asked):
    L = lua51.LuaRuntime()
    L.execute("SW = {}; SolAuthority = { on = function(n) return SW[n] == true end }; finite = function(v) return tonumber(v) end")
    for s in sw: L.execute('SW["%s"] = true' % s)
    return L.execute("local job, options = {}, { speedKmh = %s }\n%s\nreturn job.speedKmh" % (asked, capline))
def set_speed(sw, kmh):
    L = lua51.LuaRuntime()
    L.execute("SW = {}; SolAuthority = { on = function(n) return SW[n] == true end }; finite = function(v) return tonumber(v) end")
    for s in sw: L.execute('SW["%s"] = true' % s)
    L.execute("Driving = {}; local A = 'sol'; jobs = { sol = { phase = 'following', route = { points = {} }, actor = 'sol' } }; SENT = nil\n"
              "function followNative(a, r, k) SENT = k; return true end\n" + setfn.replace("local job = jobs[actor]", "local job = jobs[actor]"))
    ok = L.execute("local ok = Driving.setSpeed('sol', %s); return ok" % kmh)
    return ok, L.eval("SENT"), L.eval("jobs.sol.speedKmh")
ck("caps: speed_levels on, 65 asked -> 65", drive_cap(["speed_levels", "drive_fast"], 65) == 65)
ck("caps: speed_levels on, 90 asked -> 70", drive_cap(["speed_levels"], 90) == 70)
ck("caps: off, drive_fast on, 60 asked -> 50 (what the old jar gave)", drive_cap(["drive_fast"], 60) == 50)
ck("caps: off, drive_fast on, 40 asked -> 40", drive_cap(["drive_fast"], 40) == 40)
ck("caps: both off, 40 asked -> 30", drive_cap([], 40) == 30)
ck("setSpeed: on, 65 -> sent 65", set_speed(["speed_levels"], 65) == (True, 65, 65))
ck("setSpeed: on, 75 -> refused", set_speed(["speed_levels"], 75)[0] is False)
ck("setSpeed: off, 55 -> 50 (old jar ceiling)", set_speed([], 55) == (True, 50, 50))
ck("setSpeed: off, 65 -> refused (as before)", set_speed([], 65)[0] is False)

# ================================================================ 2. SolSpeedGov under Kahlua rules
GOVSRC = read(os.path.join(CL, "SolSpeedGov.lua"))
def gov_rt(on=True):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute("SolAuthority = { on = function(n) return %s and n == 'speed_levels' end }" % ("true" if on else "false"))
    L.execute(GOVSRC)
    return L, L.globals().SolSpeedGov
L, G = gov_rt()
def stop_java(kmh):                                              # SCDriveControl.stoppingDistance (javap: 1.5 + v*0.4 + v^2/6)
    v = abs(kmh) / 3.6; return 1.5 + v * 0.4 + v * v / 6.0
for k in (20, 40, 65):
    ck("gov: stopDist(%d) is LF's formula (%.1f tiles)" % (k, stop_java(k)), abs(G.stopDist(k) - stop_java(k)) < 1e-6)
ck("gov: the 64-tile scan stops for up to %.1f km/h at 3 m/s2 (65 fits)" % G.scanCap(), 65 <= G.scanCap() < 66)
def pts(lst): return L.table_from([L.table_from({"x": float(a), "y": float(b), "width": 8.0}) for a, b in lst])
straight = pts([(0, 0), (100, 0), (400, 0)])
pr = G.project(straight, 50, 1, None)
cap, tgt, why, _ = G.cap(straight, pr, 65, 65)
ck("gov: straight road -> no limit at 65", cap == 65 and why is None, (cap, why))
lbend = pts([(0, 0), (200, 0), (200, 200)])
caps = []
for x in (20, 100, 130, 150, 170, 190):
    c, t, w, _ = G.cap(lbend, G.project(lbend, x, 2, None), 65, 65); caps.append(round(c, 1))
ck("gov: 90-degree bend -> the cap falls as she nears it (%s)" % caps, all(caps[i] >= caps[i + 1] for i in range(len(caps) - 1)) and caps[0] == 65 and caps[-1] <= 25)
c, t, w, _ = G.cap(lbend, G.project(lbend, 150, 2, None), 65, 65)
ck("gov: 90-degree bend -> asks for the bend speed (12), says why", t == 12 and "bend 90 deg" in w, (t, w))
arc = [(0, 0), (150, 0)] + [(150 + 30 * math.sin(math.radians(9 * i)), 30 - 30 * math.cos(math.radians(9 * i))) for i in range(1, 11)] + [(180, 230)]
arc = pts(arc)
c, t, w, _ = G.cap(arc, G.project(arc, 120, 1, None), 65, 65)
ck("gov: curve of 9-degree vertices (Java never slows) -> limited to %.0f km/h, %s" % (t, w), 20 <= t <= 35 and c < 65)
ck("gov: band() steps of 5, floor 12", G.band(63.2, 65) == 60 and G.band(64.7, 65) == 65 and G.band(7, 65) == 12)
rest = G.rest(lbend, G.project(lbend, 50.2, 1, None))
ck("gov: rest() starts at the car and keeps the corner", rest[1].x == 50.2 and rest[2].x == 200 and rest[3].y == 200 and len(rest) == 3)
# tick: re-issue rules
def tick_case(on=True, speed_kmh=65, want=65, mode="follow", x=150.0, extra=""):
    L2, G2 = gov_rt(on)
    L2.execute("SENT = {}; function FOLLOW(a, r, k) SENT[#SENT + 1] = { k = k, n = #r.points, x = r.points[1].x }; return true end\n"
               "function METHOD(o, n) return true, o[n] end\n"
               "VEH = { getX = %s, getY = 2 }\n"
               "JOB = { speedKmh = %s, phase = 'following', route = { points = { {x=0,y=0,width=8}, {x=200,y=0,width=8}, {x=200,y=200,width=8} } }, vehicle = VEH, actor = 'sol' }\n%s"
               % (x, want, extra))
    L2.execute("SolSpeedGov.tick(JOB, { mode = '%s', speedKmh = %s, cruiseKmh = %s }, 1000, FOLLOW, METHOD)" % (mode, speed_kmh, want))
    return L2.eval("SENT")
s = tick_case()
ck("tick: near a bend at 65 -> one re-issue at the bend speed from the car", len(s) == 1 and s[1].k == 12 and s[1].x == 150.0, [(v.k, v.x) for v in s.values()])
ck("tick: switch off -> nothing", len(tick_case(on=False)) == 0)
ck("tick: cruise 30 or less -> nothing", len(tick_case(want=30)) == 0)
ck("tick: going round something (avoiding) -> nothing", len(tick_case(mode="avoiding")) == 0)
ck("tick: jnav running -> nothing", len(tick_case(extra="JOB.jnav = {}")) == 0)
ck("tick: far from the bend -> nothing", len(tick_case(x=20.0)) == 0)

# ================================================================ 3. the jar copy
JOUT = os.path.join(TMP, "jar")
qb = run("build_s80_speed_levels.py", JOUT)
ck("jar: builds, LF source byte-identical first, only the ceiling differs, linkcheck + patch access pass",
   qb.returncode == 0 and "byte-identical" in qb.stdout and "LINKCHECK OK" in qb.stdout and "PATCH ACCESS OK" in qb.stdout, (qb.stdout + qb.stderr)[-600:])
NEWJAR = os.path.join(JOUT, "SolCombined.jar")
OLDJAR = os.path.join(TMP, "old.jar"); shutil.copy(LAB_JAR, OLDJAR)
ck("jar: the lab jar is untouched by the build", hashlib.md5(open(LAB_JAR, "rb").read()).hexdigest() == hashlib.md5(open(OLDJAR, "rb").read()).hexdigest())

# ================================================================ 4. driving model: scenes x vehicles x speeds
SIMC = os.path.join(TMP, "simc")
r = subprocess.run([JDK + r"\javac.exe", "-nowarn", "-cp", NEWJAR + ";" + PZ, "-d", SIMC, os.path.join(HERE, "S80DriveSim.java")], capture_output=True, text=True)
ck("sim: compiles against the s80 jar copy", r.returncode == 0, r.stderr[-400:])
# bodies measured in game by SolBypass.measure (console logs) and from the scripts (KI5 67commando, RKC Bradley)
CARS = {  # name: halfW, halfL, wheelbase, lock, top km/h (script maxSpeed)
    "vanilla_small": (0.69, 1.68, 1.94, 0.86, 70), "vanilla_normal": (0.85, 2.12, 2.56, 0.85, 90),
    "vanilla_van": (1.17, 2.35, 2.88, 0.84, 65), "ki5_67commando": (0.85, 1.96, 2.45, 0.86, 58),
    "bradley_tracked": (1.62, 3.30, 3.91, 0.87, 50)}
def fence(route_pts, half, near=1.5, far=4.0, skip=()):
    """Solid squares in a band beside the road (fences / houses): near..far tiles past the road edge."""
    out = set()
    segs = list(zip(route_pts, route_pts[1:]))
    xs = [p[0] for p in route_pts]; ys = [p[1] for p in route_pts]
    for sx in range(int(min(xs) - half - far - 1), int(max(xs) + half + far + 2)):
        for sy in range(int(min(ys) - half - far - 1), int(max(ys) + half + far + 2)):
            cx, cy = sx + 0.5, sy + 0.5
            d = min(seg_dist(cx, cy, a, b) for a, b in segs)
            if half + near < d <= half + far and not any(x1 <= sx <= x2 and y1 <= sy <= y2 for x1, y1, x2, y2 in skip): out.add((sx, sy))
    return out
def seg_dist(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; l2 = dx * dx + dy * dy
    t = max(0, min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / l2)) if l2 else 0
    return math.hypot(x - a[0] - dx * t, y - a[1] - dy * t)
def scene_lines(route_pts, solid, marks):
    rt = ";".join("%.2f,%.2f,8.0" % p for p in route_pts)
    lines = ["route " + rt] + ["mark %.1f %.1f" % m for m in marks]
    for (sx, sy) in sorted(solid): lines.append("solid %d %d %d %d" % (sx, sy, sx, sy))
    return lines
R_STRAIGHT = [(100, 100), (500, 100)]
WRECK = {(x, y) for x in range(330, 335) for y in range(101, 104)}
R_L = [(100, 100), (300, 100), (300, 320)]
R_ARC = [(100, 100), (250, 100)] + [(250 + 30 * math.sin(math.radians(9 * i)), 130 - 30 * math.cos(math.radians(9 * i))) for i in range(1, 11)] + [(280, 340)]
SCENES = {
    "straight_wreck": (R_STRAIGHT, fence(R_STRAIGHT, 4) | WRECK, [(330, 102)]),
    "l_bend_90": (R_L, fence(R_L, 4), [(300, 100)]),
    "curve_9deg_vertices_r30": (R_ARC, fence(R_ARC, 4), [(250 + 30 * math.sin(math.radians(45)), 130 - 30 * math.cos(math.radians(45)))]),
    "open_curve_r30_no_fence": (R_ARC, set(), [(250 + 30 * math.sin(math.radians(45)), 130 - 30 * math.cos(math.radians(45)))]),
}
def lua_gov():
    L3, G3 = gov_rt(True)
    L3.execute("STATE = { x = 0, y = 0 }; VEH = { }; function METHOD(o, n) if n == 'getX' then return true, STATE.x end return true, STATE.y end\n"
               "SENT = nil; function FOLLOW(a, r, k) local t = {} for i = 1, #r.points do t[#t + 1] = string.format('%.2f,%.2f,%.1f', r.points[i].x, r.points[i].y, r.points[i].width or 8) end; SENT = { k = k, text = table.concat(t, ';') }; return true end")
    return L3
def simulate(jar, scene, car, kmh, gov, brake, grip=5.0):
    route_pts, solid, marks = SCENES[scene]
    hw, hl, wb, lock, top = CARS[car]
    hx, hy = route_pts[1][0] - route_pts[0][0], route_pts[1][1] - route_pts[0][1]; n = math.hypot(hx, hy)
    lines = ["car %.2f %.2f %.4f %.4f %.2f %.2f %.2f %.2f" % (route_pts[0][0] + 0.5, route_pts[0][1] + 2, hx / n, hy / n, hw, hl, wb, lock),
             "phys %.2f 15 %.1f %.2f" % (brake, top, grip), "cruise %d" % kmh, "gov %s" % ("on" if gov else "off")] + scene_lines(route_pts, solid, marks)
    sf = os.path.join(TMP, "scene.txt"); open(sf, "w").write("\n".join(lines))
    p = subprocess.Popen([JDK + r"\java.exe", "-cp", SIMC + ";" + jar + ";" + PZ, "survivorcompanion.bridge.S80DriveSim", sf, "150"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    L3 = lua_gov() if gov else None
    if L3:
        L3.execute("JOB = { speedKmh = %d, phase = 'following', vehicle = VEH, actor = 'sol', route = { points = { %s } } }"
                   % (kmh, ",".join("{x=%.2f,y=%.2f,width=8}" % q for q in route_pts)))
    out, sets = None, []
    for line in p.stdout:
        if line.startswith("G "):
            _, t, x, y, sp, cr, mode = line.split()
            L3.execute("STATE.x, STATE.y = %s, %s; SENT = nil; SolSpeedGov.tick(JOB, { mode = '%s', speedKmh = %s, cruiseKmh = %s }, %s, FOLLOW, METHOD)" % (x, y, mode, sp, cr, t))
            s = L3.eval("SENT")
            if s: sets.append(int(s.k)); p.stdin.write("S %s %s\n" % (s.k, s.text))
            else: p.stdin.write("-\n")
            p.stdin.flush()
        elif line.startswith("R "): out = line.strip()
    p.wait()
    d = dict(kv.split("=", 1) for kv in out[2:].split())
    d["sets"] = sets
    return d

print("\n--- the old jar clamps at 50; the s80 jar reaches 65 (straight road, normal car) ---")
old = simulate(OLDJAR, "straight_wreck", "vanilla_normal", 65, False, 6.0)
new = simulate(NEWJAR, "straight_wreck", "vanilla_normal", 65, False, 6.0)
print("old jar:", old); print("s80 jar:", new)
ck("jar: old jar never goes past 50+3 at cruise 65", float(old["vmax"]) <= 53.1)
ck("jar: s80 jar reaches 65 (+3 controller band)", 64 <= float(new["vmax"]) <= 68.1)

print("\n--- scenes (brake m/s2: 3 = LF's own model, 6 = likely real B42; grip 5 m/s2) ---")
print("%-24s %-16s %4s %-4s %5s | %-8s %5s %5s %-10s %6s %-13s %s" % ("scene", "car", "kmh", "gov", "brake", "result", "vmax", "t", "at mark", "maxlat", "ends at", "governor asked"))
table = []
for scene in SCENES:
    for car in CARS:
        for kmh in (20, 40, 65):
            for brake in (3.0, 6.0):
                for gov in ((False, True) if kmh > 30 else (False,)):
                    r = simulate(NEWJAR, scene, car, kmh, gov, brake)
                    table.append((scene, car, kmh, gov, brake, r))
                    print("%-24s %-16s %4d %-4s %5.1f | %-8s %5s %5s %-10s %6s %-13s %s" % (scene, car, kmh, "on" if gov else "off", brake, r["result"], r["vmax"], r["t"], r["marks"], r["maxlat"], r["x"] + "," + r["y"], r["sets"][:10]))
ck("model: nothing is ever hit, governor on or off", all(t[5]["result"] != "crash" for t in table), [(t[0], t[1], t[2], t[3], t[4]) for t in table if t[5]["result"] == "crash"])
base = {(t[0], t[1], t[2], t[4]): t[5] for t in table if not t[3]}
worse = [(t[0], t[1], t[2], t[4]) for t in table if t[3] and base[(t[0], t[1], t[2], t[4])]["result"] == "arrived" and t[5]["result"] != "arrived"]
ck("model: the governor never turns an arrival into a stop", not worse, worse)
noarr = sorted(set((t[0], t[1], t[2], t[5]["result"], t[5]["x"] + "," + t[5]["y"]) for t in table if not t[3] and t[5]["result"] != "arrived"))
print("without the governor these do not arrive either (LF as it is, not s80):", noarr)
open65 = [t for t in table if t[0] == "open_curve_r30_no_fence" and t[2] == 65]
for t in open65: print("open curve 65 %-16s gov %-3s brake %.0f: widest %s tiles off the centre line" % (t[1], "on" if t[3] else "off", t[4], t[5]["maxlat"]))
ck("model: open curve at 65, with the governor she stays on the road (centre within 5 tiles of the line)",
   all(float(t[5]["maxlat"]) <= 5 for t in open65 if t[3]), [(t[1], t[4], t[5]["maxlat"]) for t in open65 if t[3]])
gov65 = [t for t in table if t[3] and t[2] == 65 and t[0] == "curve_9deg_vertices_r30"]
ck("model: the governor slows for the 9-degree-vertex curve at 65", all(t[5]["sets"] and min(t[5]["sets"]) <= 35 for t in gov65))
top = [t for t in table if t[0] == "l_bend_90" and t[2] == 65 and t[3] and CARS[t[1]][4] >= 65]
ck("model: on the long straight before the bend she does reach 60+", all(float(t[5]["vmax"]) >= 60 for t in top), [(t[1], t[5]["vmax"]) for t in top])

shutil.rmtree(TMP, ignore_errors=True)
print("\n%d FAIL" % len(FAIL) if FAIL else "\nALL PASS")
sys.exit(1 if FAIL else 0)

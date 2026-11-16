"""gps_static_roads + gps_plain_words on a mocked game. Offline PASS is not Runtime PASS.

The bridge is replaced by a Python port of the LIVE router (SCRoadRouter + the 2026-10-25 bridge patch,
05_TOOLS/sol_gps_roads/router_port.py) reading the same street files, so the installed SCExpeditionRoute.lua runs unchanged
and gives the same answer the game gave: INCOMPLETE_MAP_DATA from Sol's home to 625 Dewey St."""
import glob, math, os, shutil, subprocess, sys, tempfile, time
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TOOLS = os.path.join(ROOT, "05_TOOLS", "sol_gps_roads")
sys.path.insert(0, TOOLS)
import router_port as RP          # noqa: E402
import gen_static_roads as GS     # noqa: E402
LIVE = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
TRAILS = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "maps", "Sol_Trails", "streets.xml")
FAIL = []
def ck(n, c, d=""):
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)

PAVED = RP.load(GS.PAVED)
DIRT = RP.load(TRAILS)
ALL = PAVED + DIRT
HOME, DEWEY = (7413, 8262), (10840, 10120)

def bridge(name, api, x, y, tx, ty, a=None, b=None):
    result = b if b is not None else a
    st, path, _ = RP.route(ALL if api == "trails" else PAVED, (x, y), (tx, ty), RP.MARGIN)
    result["status"] = st.split("/")[0] if st != "NO_CONNECTED_ROUTE/INCOMPLETE" else "INCOMPLETE_MAP_DATA"
    if st == "READY":
        result["geometry"] = ";".join("%.2f,%.2f,0,0," % p for p in path[:500])
        result["fingerprint"] = "live"
    return True

WORLD = r"""
LOGS = {}
print = function(s) LOGS[#LOGS + 1] = tostring(s) end
NOW = 1000000
getTimestampMs = function() return NOW end
FIXES = { road_first = true, gps_trails = true, gps_static_roads = true, gps_plain_words = true }
SolAuthority = { on = function(n) return FIXES[n] == true end }
SCBridge = {}
SolTrails = { api = function() return FIXES.gps_trails and "trails" or nil end }
NEAREST = nil
SolUI = { gpsNearestRoad = function(x, y) return NEAREST end }
SurvivorCompanion = {
    Config = { get = function() return true end },
    Factions = { streetDataApi = function() return "paved" end },
    Call = { static = function(bridge, name, api, ...) return true, PYBRIDGE(name, api, ...) end },
    GameplayUtil = { position = function(a) return a.x, a.y, 0 end },
}
"""
def world(static=True):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.globals()["PYBRIDGE"] = bridge
    L.execute(WORLD)
    for path in (os.path.join(LIVE, "SolRoadFirst.lua"), os.path.join(LIVE, "SCExpeditionRoute.lua"),
                 os.path.join(HERE, "SolStaticRoadsData.lua"), os.path.join(HERE, "SolStaticRoads.lua"),
                 os.path.join(HERE, "SolGPSWords.lua")):
        with open(path, encoding="utf-8") as h: L.execute(h.read())
    if not static: L.execute("FIXES.gps_static_roads = false")
    return L

def pts(L, expr):
    t = L.eval(expr)
    return [(t[i].x, t[i].y) for i in range(1, len(t) + 1)]

# every point of every road piece of the route lies on a mapped street (paved or dirt) or a router junction bridge
SEGS = [(p[i - 1], p[i]) for _, p, _ in ALL for i in range(1, len(p))]
GRID = {}
for i, (a, b) in enumerate(SEGS):
    for cx in range(int(min(a[0], b[0]) // 32), int(max(a[0], b[0]) // 32) + 1):
        for cy in range(int(min(a[1], b[1]) // 32), int(max(a[1], b[1]) // 32) + 1):
            GRID.setdefault((cx, cy), []).append(i)
def road_gap(x, y):
    best = 1e9
    for cx in range(int(x // 32) - 1, int(x // 32) + 2):
        for cy in range(int(y // 32) - 1, int(y // 32) + 2):
            for i in GRID.get((cx, cy), ()):
                a, b = SEGS[i]; best = min(best, RP.segd((x, y), a, b))
    return best
def worst_off_road(points):
    worst = 0.0
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) / 2))
        for k in range(n + 1):
            worst = max(worst, road_gap(ax + (bx - ax) * k / n, ay + (by - ay) * k / n))
    return worst

# ---------------------------------------------------------------- the reported trip
L = world(static=False)
L.execute("R, WHY = SurvivorCompanion.ExpeditionRoute.planFromPoint({ x = 7413, y = 8262, z = 0 }, { x = 10840, y = 10120, z = 0 }, true)")
ck("switch off: the live router gives up on home -> 625 Dewey St (the bug)", L.eval("R") is None and L.eval("WHY") == "INCOMPLETE_MAP_DATA", L.eval("WHY"))
st, _, _ = RP.route(PAVED, HOME, DEWEY, 1500)
ck("cause: the road exists, it only leaves the router's 160-tile box", st == "READY", st)

L = world()
t0 = time.time()
L.execute("R, WHY = SurvivorCompanion.ExpeditionRoute.planFromPoint({ x = 7413, y = 8262, z = 0 }, { x = 10840, y = 10120, z = 0 }, true)")
dt = time.time() - t0
ck("switch on: the GPS preview gets a route", L.eval("R ~= nil and R.static == true and not R.partial"), L.eval("WHY"))
route = pts(L, "R.points")
ys = [p[1] for p in route]
ck("it is a road route, not a straight line (many points)", len(route) > 20, len(route))
w = worst_off_road(route)
ck("every stretch of it lies on a mapped road (<= 12.5 tiles from a centre line, router bridges included)", w <= 12.5, "%.1f" % w)
ck("it starts on the road next to her", math.hypot(route[0][0] - HOME[0], route[0][1] - HOME[1]) <= 100, route[0])
gap = math.hypot(route[-1][0] - DEWEY[0], route[-1][1] - DEWEY[1])
ck("it ends on the road beside 625 Dewey St (within 100 tiles)", gap <= 100, "%.0f" % gap)
ck("it uses the southern road the router's box cut off", max(ys) > 10280, max(ys))
ck("bridge limits: <= 512 points, spaced >= 0.5 tile", len(route) <= 512 and all(math.hypot(b[0] - a[0], b[1] - a[1]) >= 0.5 for a, b in zip(route, route[1:])))
print("  info: %d points, road %.0f tiles, ends %.0f tiles from the marker, %.0f ms in lupa (first plan includes loading the graph)"
      % (len(route), L.eval("R.roadLength"), gap, dt * 1000))
ck("the log names the fallback", any("whole-map roads used" in str(s) for s in L.eval("LOGS").values()))

L.execute("A = { x = 7413, y = 8262 }; D, DWHY = SurvivorCompanion.ExpeditionRoute.planAvoidingAll(A, { x = 10840, y = 10120, z = 0 }, {})")
ck("the drive itself (planAvoidingAll) gets the same road route", L.eval("D ~= nil and D.static == true and #D.points == #R.points"), L.eval("DWHY"))
L.execute("P2, P2WHY = SurvivorCompanion.ExpeditionRoute.plan(A, { x = 10840, y = 10120, z = 0 }, true)")
ck("Driving.planRoute's Route.plan too", L.eval("P2 ~= nil and P2.static == true"), L.eval("P2WHY"))

L.execute("S, SWHY = SurvivorCompanion.ExpeditionRoute.planFromPoint({ x = 7413, y = 8262, z = 0 }, { x = 9904, y = 9987, z = 0 }, true)")
ck("a trip the router can do is still the router's own route", L.eval("S ~= nil and S.static == nil and S.fingerprint == 'live'"), L.eval("SWHY"))

L.execute("FIXES.gps_static_roads = false; NOW = NOW + 60000; O, OWHY = SurvivorCompanion.ExpeditionRoute.planFromPoint({ x = 7413, y = 8262, z = 0 }, { x = 10840, y = 10120, z = 0 }, true)")
ck("switch off again: exactly the old answer", L.eval("O == nil and OWHY == 'INCOMPLETE_MAP_DATA'"))
L.execute("FIXES.gps_static_roads = true")

L.execute("H, HWHY = SurvivorCompanion.ExpeditionRoute.planAvoidingAll(A, { x = 10840, y = 10120, z = 0 }, { { x = 9440, y = 9789, radius = 20 } })")
if L.eval("H ~= nil"):
    hp = pts(L, "H.points")
    near = min(RP.segd((9440, 9789), a, b) for a, b in zip(hp, hp[1:]))
    ck("a horde circle on the way: the whole-map route keeps out of it", near >= 20 - 0.01, "%.1f" % near)
else:
    ck("a horde circle on the way: no route through it", L.eval("HWHY") is not None)

# ---------------------------------------------------------------- a destination no road reaches
nodes, edges = GS.build([(n, p, w, 0) for n, p, w in PAVED] + [(n, p, w, 1) for n, p, w in DIRT])
parent = list(range(len(nodes)))
def find(x):
    while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
    return x
for a, b, *_ in edges: parent[find(a)] = find(b)
sizes = {}
for i in range(len(nodes)): sizes[find(i)] = sizes.get(find(i), 0) + 1
main = max(sizes, key=sizes.get)
island = next(i for i in range(len(nodes)) if find(i) != main and sizes[find(i)] >= 40 and math.hypot(nodes[i][0] - HOME[0], nodes[i][1] - HOME[1]) < 6000)
ix, iy = nodes[island]
L.execute("NOW = NOW + 60000; I, IWHY = SolStaticRoads.plan(7413, 8262, { x = %f, y = %f, z = 0 })" % (ix, iy))
ck("a place on roads that join nothing else: a route to the nearest reachable road point, marked partial",
   L.eval("I ~= nil and I.partial == true and I.gapToGoal > 15"), L.eval("IWHY"))
if L.eval("I ~= nil"):
    ck("  that route is on roads too", worst_off_road(pts(L, "I.points")) <= 12.5)
L.execute("Pv = { route = I }; TXT, COL = SolGPSWords.panelLine({}, Pv, { x = 1, y = 1 }, I and I.points, false, false, true, 'x')")
ck("  the panel warns: no road reaches it, going to the nearest road point", L.eval("TXT") == L.eval("SolGPSWords.PHRASES.partial.ar"), L.eval("TXT"))

# far from every road: the router says NO_EXIT_CANDIDATE, the GPS snaps to the nearest road (now also from the whole map)
far_candidates = [(x, y) for x in range(6500, 13500, 97) for y in range(5500, 12500, 97)]
def nearest_any(x, y):
    return min(RP.segd((x, y), a, b) for a, b in SEGS)
far = next(p for p in far_candidates if road_gap(*p) > 1e8 and nearest_any(*p) > 150)
L.execute("NOW = NOW + 60000; F, FWHY = SurvivorCompanion.ExpeditionRoute.planFromPoint({ x = 7413, y = 8262, z = 0 }, { x = %d, y = %d, z = 0 }, true)" % far)
ck("a marker 150+ tiles from any road: the router's NO_EXIT_CANDIDATE stands (the GPS then snaps)", L.eval("F == nil and FWHY == 'NO_EXIT_CANDIDATE'"), L.eval("FWHY"))
L.execute("NX, NY, ND = SolUI.gpsNearestRoad(%d, %d)" % far)
want = nearest_any(*far)
ck("the GPS's nearest road falls back to the whole map when the street lookup has none", L.eval("NX") is not None and abs(L.eval("ND") - want) < 1.0, (L.eval("ND"), want))
L.execute("FR, FRWHY = SolStaticRoads.plan(7413, 8262, { x = %d, y = %d, z = 0 })" % far)
ck("planning straight to that marker: partial route ending on the road nearest it", L.eval("FR ~= nil and FR.partial == true"), L.eval("FRWHY"))
L.execute("NOW = NOW + 60000; E, EWHY = SolStaticRoads.plan(%d, %d, { x = 10840, y = 10120, z = 0 })" % far)
ck("starting far from every road: NO_ENTRY_CANDIDATE, never a made-up line", L.eval("E == nil and EWHY == 'NO_ENTRY_CANDIDATE'"), L.eval("EWHY"))

# ---------------------------------------------------------------- plain words
CODES = ["player_stop", "player_order", "new_destination", "no_route", "no_route:INCOMPLETE_MAP_DATA", "no_route:NO_CONNECTED_ROUTE",
         "NO_EXIT_CANDIDATE", "BUDGET_EXCEEDED", "planner_unavailable", "planner_error", "could_not_reach_door", "engine_failed",
         "drive_already_owned", "bridge_failure", "streaming_stalled", "no_key", "hotwiring", "survival_priority",
         "companion is not at the passenger door", "something_brand_new", "", "interrupted_by_load", "no_pump_near", "wrong_fuel"]
L = world()
for c in CODES:
    L.execute("T1, C1 = SolGPSWords.panelLine({ reason = %r, result = 'failed' }, {}, nil, nil, false, true, true, 'x')" % c)
    L.execute("T2 = SolGPSWords.panelLine({ reason = %r, result = 'failed' }, {}, nil, nil, false, true, false, 'x')" % c)
    t1, t2 = L.eval("T1"), L.eval("T2")
    ok = isinstance(t1, str) and isinstance(t2, str) and not L.eval("SolGPSWords.isRaw(T1)") and not L.eval("SolGPSWords.isRaw(T2)") \
        and (c == "" or (c not in t1 and c not in t2)) and t1.startswith("\\u")
    ck("reason %r: a plain phrase in both languages, no code on screen" % c, ok, (t1, t2))
L.execute("T, C = SolGPSWords.panelLine({ reason = 'player_stop' }, {}, nil, nil, false, true, true, 'x')")
ck("player_stop reads as a calm 'we stopped', not a red failure", L.eval("T") == L.eval("SolGPSWords.PHRASES.stopped.ar") and L.eval("C[3]") == 1.0)
L.execute("T = SolGPSWords.panelLine({}, { reason = 'planner_error' }, { x = 1, y = 1 }, nil, false, false, false, 'no_route: planner_error')")
ck("an English no-route line is plain too", L.eval("T") == "That did not work this time", L.eval("T"))
L.execute("T = SolGPSWords.panelLine({ phase = 'streaming_wait' }, {}, nil, nil, true, false, false, 'streaming_wait')")
ck("an English raw phase becomes words", L.eval("T") == "Waiting for the road ahead", L.eval("T"))
L.execute("T = SolGPSWords.panelLine({ phase = 'following' }, {}, nil, nil, true, false, true, '\\\\u062A\\\\u0642\\\\u0648\\\\u062F')")
ck("a good Arabic line is left alone", L.eval("T") is None)
ck("an id as a place name is replaced", L.eval("SolGPSWords.cleanName('Flier_Muldraugh_House_12', 'HOUSE')") == "HOUSE")
ck("a real address is kept", L.eval("SolGPSWords.cleanName('625 Dewey St, Muldraugh', 'HOUSE')") == "625 Dewey St, Muldraugh")
L.execute("FIXES.gps_plain_words = false")
ck("switch off: the panel keeps its own line", L.eval("SolGPSWords.panelLine({ reason = 'player_stop' }, {}, nil, nil, false, true, true, 'x')") is None
   and L.eval("SolGPSWords.cleanName('Flier_X_1', 'HOUSE')") == "Flier_X_1")

# ---------------------------------------------------------------- installer on copies (installed files and the s75 one-value versions)
for label, srcdir in (("installed", LIVE), ("s75_onevalue", os.path.join(HERE, "s75_onevalue", "client"))):
    if not os.path.isdir(srcdir): continue
    tmp = tempfile.mkdtemp()
    cl = os.path.join(tmp, "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client"); os.makedirs(cl)
    os.makedirs(os.path.join(tmp, "Zomboid", "Lua"))
    for f in ("SolAuthority.lua", "SolGPS.lua", "SolAddressBook.lua"):
        shutil.copy(os.path.join(srcdir if os.path.exists(os.path.join(srcdir, f)) else LIVE, f), cl)
    fix = os.path.join(tmp, "Zomboid", "Lua", "SolFixes_LAB.txt")
    open(fix, "w", newline="").write("road_first=on\r\nsecret_loadout=on")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r1 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s76_gps_roads.py"), cl], capture_output=True, encoding="utf-8", env=env)
    snap = {f: open(os.path.join(cl, f), encoding="utf-8").read() for f in os.listdir(cl)}
    r2 = subprocess.run([sys.executable, os.path.join(HERE, "apply_s76_gps_roads.py"), cl], capture_output=True, encoding="utf-8", env=env)
    same = all(open(os.path.join(cl, f), encoding="utf-8").read() == snap[f] for f in snap)
    ck("installer on the %s files: applies, then changes nothing the second time" % label, r1.returncode == 0 and r2.returncode == 0 and same, (r1.stdout + r1.stderr)[-300:])
    gps = open(os.path.join(cl, "SolGPS.lua"), encoding="utf-8").read()
    ab = open(os.path.join(cl, "SolAddressBook.lua"), encoding="utf-8").read()
    au = open(os.path.join(cl, "SolAuthority.lua"), encoding="utf-8").read()
    fx = open(fix, encoding="utf-8", newline="").read()
    ck("  hook, cleanName, switches and SolFixes lines are in", gps.count("Sol fix gps_plain_words") == 1 and ab.count("Sol fix gps_plain_words") == 1
       and '"gps_static_roads"' in au and '"gps_plain_words"' in au and fx.count("gps_static_roads=on") == 1 and fx.count("gps_plain_words=on") == 1
       and "secret_loadout=on\r\ngps_static_roads=on" in fx, fx)
    Lc = lua51.LuaRuntime()
    for f in ("SolGPS.lua", "SolAddressBook.lua", "SolAuthority.lua", "SolStaticRoads.lua", "SolStaticRoadsData.lua", "SolGPSWords.lua"):
        src = open(os.path.join(cl, f), encoding="utf-8").read()
        ck("  %s compiles after install" % f, Lc.eval("loadstring")(src) is not None)
    shutil.rmtree(tmp, ignore_errors=True)

print("SUMMARY", "ALL PASS" if not FAIL else "FAILED: " + str(FAIL[:8]))
sys.exit(1 if FAIL else 0)

"""Offline tests for apply_s76_far_meta.py (far arrival for a vehicle the game keeps "in meta"). usage: python test_far_meta.py
  1 the installer on copies of the lab files after apply_s72_far_arrival: applies, twice changes nothing, compiles, no tonumber(f())
  2 his Bradley kept in meta (row 6 of the save copy: Base.RKCBradleyM3, hotwired, unlocked, 64 l), with the new jar's 16th field and the
    inside arrival: chosen, ",tracked,in", 210 s, one request for row 6 inside the loaded ring, arrived, at the wheel
  3 the same Bradley without the inside arrival (old jar / Java missing) or without the 16th field: not chosen; she comes on foot with the
    Mind's own line, which has no mechanics in it
  4 the game changed its mind between staging and the main thread (meta_changed) or he moved (meta_deferred): she walks, the log says why
  5 a helicopter kept in meta: ",heli,in", 60 s, arrives at the controls
  6 what she says about the cars around her: the Bradley "ok" with the inside arrival, "in_meta" without
The world is the one test_far_arrival.py builds (its WORLD and ARRIVE Lua, read from that file). Offline PASS is not Runtime PASS."""
import ast, os, re, shutil, sqlite3, struct, subprocess, sys, tempfile
from kahlua_env import lua51
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
HERE = os.path.dirname(os.path.abspath(__file__))
LAB_NOW = os.path.join(HERE, "..", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "lua", "client")
LAB_OLD = os.path.join(HERE, "..", "_backup", "20261110_before_s67_73", "client")
MIND_NOW = r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_mind"
SAVE = os.path.join(HERE, "place_fixtures", "save_20261110_1947")
TONUM = r"C:\Users\JAMAL\Desktop\Sol\05_TOOLS\sol_kahlua\tonumber_check.py"
FAIL, N = [], [0]
def ck(n, c, d=""):
    N[0] += 1
    print(("PASS " if c else "FAIL ") + n + ((" : " + str(d)) if not c and d != "" else ""))
    if not c: FAIL.append(n)
def run(*a): return subprocess.run([sys.executable, "-I"] + list(a), capture_output=True, text=True, encoding="utf-8")

# the harness of test_far_arrival.py, taken from its source (not run)
src = open(os.path.join(HERE, "test_far_arrival.py"), encoding="utf-8").read()
consts = {n.targets[0].id: n.value.value for n in ast.parse(src).body
          if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)}
WORLD, ARRIVE = consts["WORLD"], consts["ARRIVE"]

# ---------------------------------------------------------------- 1 the installer
T = tempfile.mkdtemp(prefix="sol_far_meta_")
def fresh(tag, lab):
    cl, md = os.path.join(T, tag, "client"), os.path.join(T, tag, "mind")
    os.makedirs(cl); os.makedirs(md)
    for n in ("SCPersistence.lua", "SolFar.lua", "SolOrders.lua"): shutil.copy(os.path.join(lab, n), cl)
    for n in ("chat_service.py", "goal_engine.py", "road_route.py", "model_router.py"): shutil.copy(os.path.join(MIND_NOW, n), md)
    r = run(os.path.join(HERE, "apply_s72_far_arrival.py"), cl, md)
    return cl, md, r
def snap(d): return {n: open(os.path.join(d, n), encoding="utf-8").read() for n in sorted(os.listdir(d))}
for tag, lab in (("now", LAB_NOW), ("old", LAB_OLD)):
    cl, md, r0 = fresh(tag, lab)
    ck("%s lab: apply_s72 first" % tag, r0.returncode == 0, r0.stderr[-300:])
    pre = os.path.join(T, tag, "pre_s76"); os.makedirs(pre); shutil.copy(os.path.join(cl, "SolFar.lua"), pre)
    r = run(os.path.join(HERE, "apply_s76_far_meta.py"), cl); ck("%s lab: apply_s76 applies" % tag, r.returncode == 0, r.stderr[-400:])
    once = snap(cl)
    r = run(os.path.join(HERE, "apply_s76_far_meta.py"), cl); ck("%s lab: twice changes nothing" % tag, r.returncode == 0 and snap(cl) == once, r.stderr[-300:])
    s = open(os.path.join(cl, "SolFar.lua"), encoding="utf-8").read()
    ck("%s lab: SolFar.lua compiles in Kahlua-like Lua" % tag, not isinstance(lua51.LuaRuntime().globals().loadstring(s), tuple))
    if os.path.exists(TONUM):                                                  # the gate on the one file s76 touches: no new site
        def sites(f): return sorted(re.sub(r":\d+ ", " ", l) for l in run(TONUM, f).stdout.splitlines() if "tonumber" in l and "CHECK" not in l)
        before, after = sites(os.path.join(pre, "SolFar.lua")), sites(os.path.join(cl, "SolFar.lua"))
        ck("%s lab: tonumber_check: s76 adds no tonumber site to SolFar.lua (%d there before it, from earlier batches)" % (tag, len(before)), after == before, [x for x in after if x not in before])
cl, md, _ = fresh("main", LAB_NOW)
run(os.path.join(HERE, "apply_s76_far_meta.py"), cl)
PF, PP = os.path.join(cl, "SolFar.lua"), os.path.join(cl, "SCPersistence.lua")

# ---------------------------------------------------------------- the world (as test_far_arrival.py builds it)
mod = open(os.path.join(SAVE, "global_mod_data.bin"), "rb").read()            # read-only
def dbl(key, start=0):
    i = mod.index(key, start) + len(key) + 1
    return struct.unpack(">d", mod[i:i + 8])[0], i
car_x, _ = dbl(b"\x04carX"); car_y, _ = dbl(b"\x04carY"); car_id, _ = dbl(b"\x08carSqlId"); fuel, _ = dbl(b"\x07carFuel")
mass, _ = dbl(b"\x07carMass"); qual, _ = dbl(b"\x0acarQuality")
pos = mod.index(b"\x08position"); her_x, j = dbl(b"\x01x", pos); her_y, _ = dbl(b"\x01y", j)
def relocate_src(path):
    s = open(path, encoding="utf-8").read()
    body = s[s.index("function persistence.pendingRelocate"):]
    body = body[:body.index("\nend\n") + 5]
    return "PENDING = {}\nlocal pending = PENDING\nlocal persistence = {}\n" + body + "PENDING_RELOCATE = persistence.pendingRelocate\n"
def world(setup=""):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute("CAR_X, CAR_Y, CAR_ID, CAR_FUEL, MASS, QUAL, HER_X, HER_Y = %r, %r, %d, %r, %r, %r, %r, %r" % (car_x, car_y, int(car_id), fuel, mass, qual, her_x, her_y))
    L.execute(relocate_src(PP))
    L.execute(WORLD)
    if setup: L.execute(setup)
    L.execute(open(PF, encoding="utf-8").read())
    return L, L.globals()
def logs(g): return [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]

# his Bradley, as the save copy has it (read from a copy of vehicles.db; the jar's line for it, with the 16th field)
tmpdb = os.path.join(T, "vehicles.db"); shutil.copy(os.path.join(SAVE, "vehicles.db"), tmpdb)
con = sqlite3.connect(tmpdb)
b6 = con.execute("SELECT x, y, inMeta FROM vehicles WHERE id = 6").fetchone()
con.close()
ck("save copy: row 6 is kept in meta (%s)" % (b6,), b6 is not None and b6[2] == 1)
# Java's own line for it (SolCarsNearCoreTest DUMP of the same row): fuel 64.01, engine 100, unlocked, quality 100, hotwired; she stands 4 tiles away
def line(i, script, verdict, meta=None):
    return "%d,%d,%d,4,%s,64.01,100,0,100,79868708,0,%s,0,1,0%s" % (i, her_x + 3, her_y, script, verdict, ("," + meta) if meta else "")
CARS = "SW.far_car = true; function solCarsNearRequest() return true end; function solCarsNearState() return 'ok' end; function solCarsNearResult() return CARLIST end; "
def carlist(*lines): return "CARLIST = '%d,%d|%s'" % (her_x, her_y, ";".join(lines))
def where(setup):
    L, g = world(setup)
    for _ in range(3): g.tick(1000)
    g.tick(16000); g.tick(1000)
    return L, g, g.SolUI.solFar("car_where")

# the inside spot the Mind picks for his trip (road_route of the s72-patched Mind copy)
sys.path.insert(0, md); sys.path.insert(1, MIND_NOW)
import road_route as RR
ck("the Mind as installed (first s72, 20:14), upgraded by apply_s72: pickup_spot_dir takes inner= (the s72 upgrade fix)", "inner" in RR.pickup_spot_dir.__code__.co_varnames, RR.pickup_spot_dir.__code__.co_varnames)
r = run(os.path.join(HERE, "apply_s72_far_arrival.py"), "-", md)
ck("apply_s72 on that Mind twice: road_route unchanged", r.returncode == 0 and open(os.path.join(md, "road_route.py"), encoding="utf-8").read().count("def pickup_spot_dir(") == 2, r.stderr[-300:])
si = RR.pickup_spot_dir(7412, 8262, 7205, 8148, 9, "car", os.path.join(MIND_NOW, "gazetteer.json.gz"), inner=True)
SPOT_IN = "%.1f,%.1f,%.0f,%.0f,in" % si
ROAD = "function ROAD(x, y) return math.abs(x - %d) <= 2 or math.abs(y - %d) <= 2 end; " % (int(si[0]), int(si[1]))
def trip(setup, secs, result=None):
    L, g, w = where(ARRIVE + ROAD + CARS + setup)
    L.execute("CAR_ID = 6; MD.carSqlId = 99")                                 # her own car is elsewhere; this one is near her
    if result: L.execute("AR.result = '%s'" % result)
    r = g.SolUI.solFar("car_far:" + SPOT_IN)
    for _ in range(secs + 2): g.tick(1000)
    g.tick(1000); L.execute("STREAMER()"); g.tick(1000)
    return L, g, w, r

# ---------------------------------------------------------------- 2 the Bradley kept in meta, with the inside arrival
L, g, w, r = trip(carlist(line(6, "Base.RKCBradleyM3", "in_meta", "ok")), 210)
ck("Bradley kept in meta: chosen, a tracked vehicle, brought inside (%s)" % (w,), w[0] and w[1].endswith(",tracked,in"), w)
ck("Bradley kept in meta: 3.5 minutes", r == (True, "waiting:210"), r)
ck("Bradley kept in meta: one request, for row 6, inside his loaded ring", g.AR.n == 1 and g.AR.req[1] == 6, (g.AR.n, g.AR.req and tuple(g.AR.req.values())))
ck("Bradley kept in meta: arrived, she is at the wheel the same tick", g.AR.state == "arrived" and g.LIVE.veh is not None and g.WHEEL >= 1, (g.AR.state, logs(g)[-4:]))
ck("Bradley kept in meta: never the old outside move", len(g.MOVES) == 0, len(g.MOVES))
ck("Bradley kept in meta: the log says it was kept in meta (the log only)", any("(kept in meta)" in l for l in logs(g)), logs(g)[-6:])
for _ in range(5): g.tick(1000)
ck("Bradley kept in meta: poll here", g.poll() == "here", g.poll())

# ---------------------------------------------------------------- 3 until the inside arrival is there: she walks
L, g, w = where(CARS + carlist(line(6, "Base.RKCBradleyM3", "in_meta", "ok")))   # new jar's line, no SolCarArrive
ck("no inside arrival: the Bradley kept in meta is not chosen (%s)" % (w,), w[0] is False or w[0] is None, w)
L, g, w = where(ARRIVE + CARS + carlist(line(6, "Base.RKCBradleyM3", "in_meta")))  # old jar's 15 fields
ck("old jar (no 16th field): not chosen either (%s)" % (w,), not w[0], w)
L, g, w = where(ARRIVE + CARS + carlist(line(6, "Base.RKCBradleyM3", "in_meta", "locked")))
ck("kept in meta but locked: not chosen (%s)" % (w,), not w[0] and w[1] == "locked_near", w)
L, g, w = where(ARRIVE + CARS + carlist(line(7, "Base.SmallCar", "ok"), line(6, "Base.RKCBradleyM3", "in_meta", "ok")))
ck("a nearer plain car comes first, as before (%s)" % (w,), w[0] and w[1].endswith(",car,in") and any("car for the trip: 7 " in l for l in logs(g)), (w, logs(g)[-2:]))
L, g, w = where(ARRIVE + CARS + carlist(line(6, "Base.RKCBradleyM3", "in_meta", "ok"), line(7, "Base.SmallCar", "ok")))
ck("the Bradley kept in meta, nearest: it comes (%s)" % (w,), w[0] and w[1].endswith(",tracked,in") and any("car for the trip: 6 Base.RKCBradleyM3 (kept in meta)" in l for l in logs(g)), (w, logs(g)[-2:]))
sys.modules.pop("chat_service", None)
import chat_service as CS
walk = CS.far_wait_line("waiting:300", "جاية مشي، بدي %s.")
BAD = re.compile(r"meta|java|row|spot|record|chunk|edge|teleport|طرف منطقتك|مربع|خطوة|لتر|تحميل", re.I)
ck("the walking line (%s) has no mechanics in it" % walk, not BAD.search(walk) and not BAD.search(CS.FAR_ON_WAY), walk)

# ---------------------------------------------------------------- 4 the game moved first: she walks, the reason in the log only
for why in ("meta_changed", "meta_deferred", "in_meta"):
    # the Java answering `why` at the main thread
    L, g, w = where(ARRIVE + ROAD + CARS + carlist(line(6, "Base.RKCBradleyM3", "in_meta", "ok")))
    L.execute("CAR_ID = 6; MD.carSqlId = 99")
    L.execute("local base = solCarArriveMain; function solCarArriveMain() if AR.state == 'staged' then AR.state = '%s'; return '%s' end return base() end" % (why, why))
    g.SolUI.solFar("car_far:" + SPOT_IN)
    for _ in range(212): g.tick(1000)
    g.tick(1000); L.execute("STREAMER()"); g.tick(1000); g.tick(1000)
    ck("%s: she walks (poll %s), nothing created, the reason in the log only" % (why, g.poll()), str(g.poll()).startswith("on_foot:") and g.LIVE.veh is None and any(("not brought in (%s)" % why) in l for l in logs(g)), (g.poll(), logs(g)[-3:]))

# ---------------------------------------------------------------- 5 a helicopter kept in meta
L, g, w, r = trip(carlist(line(6, "Base.UH1BHuey", "in_meta", "ok")), 60)
ck("helicopter kept in meta: ',heli,in', 60 s, arrived at the controls", w[1].endswith(",heli,in") and r == (True, "waiting:60") and g.AR.state == "arrived" and g.LIVE.veh is not None, (w, r, g.AR.state))

# ---------------------------------------------------------------- 6 what she says about the cars around her
L, g, w = where(ARRIVE + CARS + carlist(line(6, "Base.RKCBradleyM3", "in_meta", "ok")))
a = g.SolUI.solFar("cars")
ck("cars: with the inside arrival the Bradley is listed as one she can bring (%s)" % (a,), a[0] and ",ok," in a[1], a)
L, g, w = where(CARS + carlist(line(6, "Base.RKCBradleyM3", "in_meta", "ok")))
a = g.SolUI.solFar("cars")
ck("cars: without it, as before: in_meta (%s)" % (a,), a[0] and ",in_meta," in a[1], a)

print("SUMMARY pass=%d fail=%d" % (N[0] - len(FAIL), len(FAIL)))
sys.exit(1 if FAIL else 0)

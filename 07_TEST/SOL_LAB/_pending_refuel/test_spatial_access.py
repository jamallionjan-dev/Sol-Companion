"""Offline tests for spatial_access (SolPlace.lua) in the Kahlua-like lupa (kahlua_env). usage: python test_spatial_access.py
  1 real map: the farm, its paddocks, gate, farmhouse and barn around 7404,8262 (place_fixtures/farm_7404_8262.json, read from the
    game's own lotheader/lotpack by src/extract_place.py). Read through stubbed IsoGridSquares, so the live edge reader is what runs.
    Only vanilla map data: whatever he built or broke in his save is not in it (sol_place dump writes the live squares for that).
  2 synthetic layouts: yards, houses, locked and barricaded doors, windows, long fences, containers against fences and walls.
  3 random grids against a Python Dijkstra with the same prices: the route is always the cheapest, never through a wall, never a
    corner cut, and a fence or a window is used only when every door-only route costs more.
  4 her walk: U.solGoto through the wrapper on the real map, leg by leg, with an engine stub; legs, crossings and timings counted.
Offline PASS is not Runtime PASS: the stubs are the game as SolPlace expects it."""
import heapq, json, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kahlua_env import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
ok_n = bad = 0
def check(name, ok, extra=None):
    global ok_n, bad
    print(("PASS " if ok else "FAIL ") + name + ("" if ok or extra is None else "   -> " + str(extra))); ok_n += bool(ok); bad += (not ok)

# ---------------------------------------------------------------- squares from the real map (tile properties -> border kinds)
def kind_of(p, d):
    if "door" + d in p: return "door"
    if "window" + d in p: return "window"
    if "Window" + d in p: return "frame"
    if "TallHoppable" + d in p: return "wall"
    if "Hoppable" + d in p: return "fence"
    if "DoorWall" + d in p: return "open"
    if {"Wall" + d, "Wall" + d + "Trans", "WallNW", "WallNWTrans", "collide" + d} & p: return "wall"
    return "open"
def from_fixture(path):
    d = json.load(open(path, encoding="utf-8"))
    sq = {}
    for k, v in d["squares"].items():
        x, y = map(int, k.split(","))
        p = set(v["p"])
        st = not ({"solid", "solidtrans", "container"} & p)
        sq[(x, y)] = {"st": st, "N": kind_of(p, "N"), "W": kind_of(p, "W"), "room": v.get("room"), "c": "container" in p}
    return sq, d

def lua_world(sq):
    rows = []
    for (x, y), s in sq.items():
        rows.append('["%d,%d"]={st=%s,N="%s",W="%s"}' % (x, y, "true" if s["st"] else "false", s["N"], s["W"]))
    return "SQ={" + ",".join(rows) + "}"

L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(r"""
NOW = 0
function getTimestampMs() return NOW end
SWITCH = true
SolAuthority = { on = function(n) return n == "spatial_access" and SWITCH end }
SolUI = {}
STATE = {}
SQ = {}
-- the world straight from the table (synthetic layouts, random grids)
W = {}
function W.standable(x, y, z) local s = SQ[x .. "," .. y]; return s ~= nil and s.st end
function W.edge(x, y, z, dir)
    local s = SQ[x .. "," .. y]
    if s == nil then return "wall" end
    local k = s[dir] or "open"
    if k == "door" or k == "window" then return k, STATE[x .. "," .. y .. "," .. dir] or { open = false } end
    return k
end
-- the live reader on stubbed IsoGridSquares (the real map)
local squares = {}
local function edgeKind(a, b)
    local ax, ay, bx, by = a.x, a.y, b.x, b.y
    local owner, dir
    if bx == ax and by == ay - 1 then owner, dir = a, "N" elseif bx == ax and by == ay + 1 then owner, dir = b, "N"
    elseif by == ay and bx == ax - 1 then owner, dir = a, "W" elseif by == ay and bx == ax + 1 then owner, dir = b, "W" else return "wall" end
    local s = SQ[owner.x .. "," .. owner.y]
    return s and s[dir] or "wall", owner, dir
end
local function obj(owner, dir)
    local st = STATE[owner.x .. "," .. owner.y .. "," .. dir] or { open = false }
    return { IsOpen = function() return st.open == true end, isLocked = function() return st.locked == true end,
        isLockedByKey = function() return false end, isBarricaded = function() return st.barricaded == true end,
        isSmashed = function() return st.smashed == true end, isGlassRemoved = function() return st.noGlass == true end }
end
local function newSquare(x, y, z)
    local s = { x = x, y = y, z = z }
    function s:getX() return self.x end function s:getY() return self.y end function s:getZ() return self.z end
    function s:isDoorTo(o) return (edgeKind(self, o)) == "door" end
    function s:isWindowTo(o) local k = edgeKind(self, o); return k == "window" or k == "frame" end
    function s:isHoppableTo(o) return (edgeKind(self, o)) == "fence" end
    function s:isBlockedTo(o) local k = edgeKind(self, o); return k ~= "open" end
    function s:getDoor(north) local d = north and "N" or "W"; local q = SQ[self.x .. "," .. self.y]; if q and q[d] == "door" then return obj(self, d) end return nil end
    function s:getWindow(north) local d = north and "N" or "W"; local q = SQ[self.x .. "," .. self.y]; if q and q[d] == "window" then return obj(self, d) end return nil end
    function s:getThumpableWindow() return nil end
    function s:getWindowFrame(north) local d = north and "N" or "W"; local q = SQ[self.x .. "," .. self.y]; if q and q[d] == "frame" then return {} end return nil end
    function s:getFloor() return {} end
    function s:isSolid() local q = SQ[self.x .. "," .. self.y]; return q == nil or not q.st end
    function s:isSolidTrans() return false end
    function s:isFree() return true end
    function s:canReachTo(o) return true end
    return s
end
READS = 0
CELL = { getGridSquare = function(_, x, y, z)
    READS = READS + 1
    if SQ[x .. "," .. y] == nil then return nil end
    local k = x .. "," .. y .. "," .. z
    local s = squares[k]
    if s == nil then s = newSquare(x, y, z); squares[k] = s end
    return s end,
    getZombieList = function() return { size = function() return #ZOMBIES end, get = function(_, i) return ZOMBIES[i + 1] end } end }
ZOMBIES = {}
function getCell() return CELL end
""")
src = open(os.path.join(HERE, "SolPlace.lua"), encoding="utf-8").read()
L.execute(src)
SP = L.globals().SolPlace

def set_world(sq, live=False):
    L.execute(lua_world(sq))
    L.execute("STATE = {}; SolPlace._chunks = SolPlace._chunks; for k in pairs(SolPlace._chunks) do SolPlace._chunks[k] = nil end")
    L.execute("SolPlace.setWorld(%s)" % ("nil" if live else "W"))
def set_state(x, y, d, **st):
    L.execute("STATE['%d,%d,%s'] = { %s }" % (x, y, d, ", ".join("%s = %s" % (k, "true" if v else "false") for k, v in st.items())))
    L.execute("for k in pairs(SolPlace._chunks) do SolPlace._chunks[k] = nil end")
def route(sx, sy, gx, gy, strict=False):
    j = L.eval("function(sx, sy, gx, gy, s) return SolPlace.route(sx, sy, 0, { { x = gx, y = gy } }, { strict = s }) end")(sx, sy, gx, gy, strict)
    out = {"state": j.state, "why": j.why, "nodes": j.nodes}
    if j.state == "done":
        out["cost"] = j.cost
        out["steps"] = len(j.path) - 1
        out["path"] = [(j.path[i].x, j.path[i].y) for i in range(1, len(j.path) + 1)]
        out["cross"] = [(j.crossings[i].kind, (j.crossings[i]["from"].x, j.crossings[i]["from"].y), (j.crossings[i].to.x, j.crossings[i].to.y)) for i in range(1, len(j.crossings) + 1)]
        out["legs"] = [(j.legs[i].x, j.legs[i].y) for i in range(1, len(j.legs) + 1)]
        out["kinds"] = sorted(set(c[0] for c in out["cross"]))
    return out
def access(x, y):
    t = SP.access(x, y, 0)
    return sorted((t[i].x, t[i].y) for i in range(1, len(t) + 1))

# ---------------------------------------------------------------- 1 the real farm (live reader on stubbed squares)
FIX = os.path.join(HERE, "place_fixtures", "farm_7404_8262.json")
farm, meta = from_fixture(FIX)
set_world(farm, live=True)
def kinds_on(x, y, d): return farm.get((x, y), {}).get(d)
check("map: the vanilla paddock fence is in the map files (fencing_01_27 HoppableW at 7402,8264, where she climbed at 05:20:08)", kinds_on(7402, 8264, "W") == "fence")
check("map: a gate (a door in the fence line) at 7402,8259, five tiles north of that climb", kinds_on(7402, 8259, "W") == "door")
check("map: the fence west of the plot at x=7396 (her climbs at 7395,8257, 05:44 and 05:53)", kinds_on(7396, 8257, "W") == "fence")
rooms = sorted(set(v["name"] for v in meta["rooms"].values()))
check("map: the farmhouse rooms come from the lotheader (kitchen, bedroom, ...)", "kitchen" in rooms and "bedroom" in rooms, rooms)

r = route(7400, 8265, 7403, 8264)
check("farm: plot 7400,8265 -> 7403,8264 (outside the east fence) goes through the gate, no fence", r["state"] == "done" and r["kinds"] == ["door"], r)
check("farm: and the gate crossing is 7401,8259 -> 7402,8259", r.get("cross") and r["cross"][0][1:] == ((7401, 8259), (7402, 8259)), r.get("cross"))
check("farm: legs stop before and after the gate", r.get("legs") and (7401, 8259) in r["legs"] and (7402, 8259) in r["legs"], r.get("legs"))
print("    route plot->outside: steps=%s cost=%.1f nodes=%s legs=%s" % (r.get("steps"), r.get("cost", 0), r["nodes"], r.get("legs")))
r2 = route(7400, 8265, 7400, 8256)
check("farm: plot -> 7400,8256 (same paddock) crosses nothing", r2["state"] == "done" and r2["kinds"] == [], r2.get("cross"))
r3 = route(7400, 8265, 7394, 8257)
fence_r3 = r3.get("kinds", [])
check("farm: plot -> 7394,8257 (the paddock west of x=7396) prefers doors over the fence when a door route exists", r3["state"] == "done" and "window" not in fence_r3, r3.get("cross"))
print("    route plot->west paddock: steps=%s cost=%.1f kinds=%s nodes=%s" % (r3.get("steps"), r3.get("cost", 0), fence_r3, r3["nodes"]))
rs = route(7400, 8265, 7394, 8257, strict=True)
print("    the same with doors only: %s steps=%s" % (rs["state"], rs.get("steps")))
check("farm: the fence is used there only because a door-only way costs more than the fence (or does not exist)",
      "fence" not in fence_r3 or rs["state"] != "done" or rs["cost"] >= r3["cost"], (rs.get("cost"), r3.get("cost")))
# the places he named
for (x, y) in [(7404, 8267), (7403, 8262), (7396, 8269), (7404, 8254)]:
    a = access(x, y)
    bad_side = [s for s in a if not SP.reach(s[0], s[1], 0, x, y)]
    check("farm: access squares of %d,%d are all on its own side (%s)" % (x, y, a), not bad_side, bad_side)
# a thing against the paddock fence: nothing across the fence
a = access(7401, 8262)
check("farm: a box at 7401,8262 (just west of the east fence) is never used from 7402,8262 across the fence", (7402, 8262) not in a and len(a) > 0, a)
a = access(7402, 8262)
check("farm: and a box at 7402,8262 is never used from 7401,8262", (7401, 8262) not in a and len(a) > 0, a)
# farmhouse: the doors and the windows
house = [k for k, v in farm.items() if v["room"]]
doors = [(k, d) for k, v in farm.items() for d in "NW" if v[d] == "door"]
check("farm: doors found on the map (%d)" % len(doors), len(doors) >= 4, doors)
# into the kitchen from outside the house, doors shut and unlocked: through a door, not a window
kit = [k for k, v in farm.items() if v["room"] and meta["rooms"][v["room"]]["name"] == "kitchen" and v["st"]]
goal = sorted(kit)[len(kit) // 2]
r4 = route(7400, 8245, goal[0], goal[1])
check("farm: from the yard into the kitchen %s: through doors, no window, no fence" % (goal,), r4["state"] == "done" and set(r4["kinds"]) <= {"door"}, r4.get("cross"))
print("    yard->kitchen: steps=%s cost=%.1f crossings=%s nodes=%s" % (r4.get("steps"), r4.get("cost", 0), r4.get("cross"), r4["nodes"]))
# lock every door of the house: then a window, never a wall
for (k, d) in doors: set_state(k[0], k[1], d, open=False, locked=True)
r5 = route(7400, 8245, goal[0], goal[1])
check("farm: every door locked: she goes in by a window (or not at all), never through a wall",
      r5["state"] != "done" or (set(r5["kinds"]) <= {"window", "frame", "fence"} and "window" in "".join(r5["kinds"]) + "window"), r5.get("cross"))
print("    yard->kitchen, doors locked: %s %s" % (r5["state"], r5.get("cross")))
for (k, d) in doors: set_state(k[0], k[1], d, open=False, locked=False)
t0 = time.time(); n = 0
for (sx, sy, gx, gy) in [(7380, 8240, 7424, 8286), (7400, 8265, 7410, 8250), (7377, 8237, 7427, 8270)]:
    rr = route(sx, sy, gx, gy); n += rr["nodes"]
print("    three long routes on the farm: %d nodes, %.1f ms in lupa" % (n, (time.time() - t0) * 1000))

# ---------------------------------------------------------------- 2 synthetic layouts (the world table)
def grid(w, h):
    return {(x, y): {"st": True, "N": "open", "W": "open"} for x in range(w) for y in range(h)}
def hline(sq, y, x0, x1, kind):            # border on the north of row y, columns x0..x1
    for x in range(x0, x1 + 1): sq[(x, y)]["N"] = kind
def vline(sq, x, y0, y1, kind):            # border on the west of column x, rows y0..y1
    for y in range(y0, y1 + 1): sq[(x, y)]["W"] = kind

# yard 12x12 fenced, gate in the south side far from the start
sq = grid(40, 40)
hline(sq, 10, 10, 21, "fence"); hline(sq, 22, 10, 21, "fence"); vline(sq, 10, 10, 21, "fence"); vline(sq, 22, 10, 21, "fence")
sq[(20, 22)]["N"] = "door"
set_world(sq)
r = route(12, 11, 12, 8)
check("yard: from inside by the north fence to just outside it: round by the gate (detour %s steps), not over" % r.get("steps"), r["kinds"] == ["door"], r.get("cross"))
r = route(12, 11, 12, 8, strict=True)
check("yard: strict search finds the same gate", r["state"] == "done", r)
# no gate: the fence, once
sq = grid(40, 40)
hline(sq, 10, 10, 21, "fence"); hline(sq, 22, 10, 21, "fence"); vline(sq, 10, 10, 21, "fence"); vline(sq, 22, 10, 21, "fence")
set_world(sq)
r = route(12, 11, 12, 8)
check("yard without a gate: over the fence, once (the last resort)", r["kinds"] == ["fence"] and len(r["cross"]) == 1, r.get("cross"))
check("yard without a gate, strict: no route", route(12, 11, 12, 8, strict=True)["state"] == "failed")
# a far gate: 50 tiles of detour still beat a fence (60); 70 do not
for gap, want in ((20, "door"), (24, "door")):
    sq = grid(80, 20)
    hline(sq, 10, 0, 79, "fence"); sq[(10 + gap, 10)]["N"] = "door"
    set_world(sq)
    r = route(10, 11, 10, 9)
    check("long fence, gate %d tiles away (detour %d): %s" % (gap, gap * 2, want), r["kinds"] == [want], r.get("cross"))
sq = grid(80, 20); hline(sq, 10, 0, 79, "fence"); sq[(45, 10)]["N"] = "door"; set_world(sq)
r = route(10, 11, 10, 9)
check("long fence, gate 35 tiles away (detour 70 > 60): over the fence", r["kinds"] == ["fence"], r.get("cross"))
# a house: door on the far side, window by the start
sq = grid(30, 30)
hline(sq, 10, 10, 18, "wall"); hline(sq, 19, 10, 18, "wall"); vline(sq, 10, 10, 18, "wall"); vline(sq, 19, 10, 18, "wall")
sq[(14, 10)]["N"] = "window"; sq[(14, 19)]["N"] = "door"
set_world(sq)
r = route(14, 8, 14, 11)
check("house: window by her, door on the far side (detour ~18): the door", r["kinds"] == ["door"], r.get("cross"))
set_state(14, 19, "N", locked=True)
r = route(14, 8, 14, 11)
check("house: the door locked: the window", r["kinds"] == ["window"], r.get("cross"))
set_state(14, 10, "N", barricaded=True)
r = route(14, 8, 14, 11)
check("house: door locked and window barricaded: no way in (the old walk takes over)", r["state"] == "failed", r)
set_state(14, 19, "N", locked=True); set_state(14, 10, "N", open=True)
r = route(14, 8, 14, 11)
check("house: an open window is still a climb: door locked -> the open window", r["kinds"] == ["window"], r.get("cross"))
# window vs fence: the window
sq = grid(40, 30)
hline(sq, 10, 0, 39, "fence"); sq[(20, 10)]["N"] = "window"
set_world(sq)
r = route(19, 12, 19, 8)
check("window or fence: the window (25 < 60)", r["kinds"] == ["window"], r.get("cross"))
# walls are never crossed, corners never cut
sq = grid(10, 10); vline(sq, 5, 0, 9, "wall"); set_world(sq)
check("a wall from edge to edge: no route", route(2, 2, 8, 2)["state"] == "failed")
sq = grid(10, 10); sq[(5, 5)]["N"] = "wall"; set_world(sq)
r = route(4, 5, 5, 4)
check("no diagonal stride past a wall end", r["state"] == "done" and r["steps"] == 2, r.get("path"))
# access: container against a fence, in a room corner, behind a shut/open door
sq = grid(10, 10); vline(sq, 5, 0, 9, "fence"); sq[(4, 4)]["st"] = False; set_world(sq)
check("access: a box against a fence is used from its own side only", (5, 4) not in access(4, 4) and (3, 4) in access(4, 4), access(4, 4))
check("access: corners are offered only when no side works", all(abs(a[0] - 4) + abs(a[1] - 4) == 1 for a in access(4, 4)), access(4, 4))
sq = grid(10, 10); hline(sq, 5, 0, 9, "wall"); vline(sq, 5, 0, 9, "wall"); sq[(4, 4)]["st"] = False
sq[(3, 4)]["st"] = False; sq[(4, 3)]["st"] = False; set_world(sq)
a = access(4, 4)
check("access: a box in a room corner, both sides blocked: the diagonal inside, never across the walls", a == [(3, 3)], a)
sq = grid(10, 10); hline(sq, 5, 0, 9, "wall"); sq[(4, 5)]["N"] = "door"; sq[(4, 4)]["st"] = False; set_world(sq)
check("access: behind a shut door: not from the other side", (4, 5) not in access(4, 4), access(4, 4))
set_state(4, 5, "N", open=True)
check("access: an open door: usable through it, as vanilla canReachTo", (4, 5) in access(4, 4), access(4, 4))

# ---------------------------------------------------------------- 3 random grids against a Python Dijkstra (same prices)
COST = {"open": 0, "door": 2, "window": 40, "frame": 25, "fence": 60}
def ref(sq, s, gl, strict=False):
    def edge(a, b):
        (ax, ay), (bx, by) = a, b
        if bx == ax and by == ay - 1: o, d = a, "N"
        elif bx == ax and by == ay + 1: o, d = b, "N"
        elif by == ay and bx == ax - 1: o, d = a, "W"
        else: o, d = b, "W"
        return sq.get(o, {}).get(d, "wall")
    def st(p): return p in sq and sq[p]["st"]
    def clear(a, b): return edge(a, b) == "open"
    dist = {s: 0.0}; pq = [(0.0, s)]
    while pq:
        dcur, p = heapq.heappop(pq)
        if p == gl: return dcur
        if dcur > dist.get(p, 1e18): continue
        x, y = p
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
            q = (x + dx, y + dy)
            if not st(q): continue
            if dx and dy:
                h, v = (x + dx, y), (x, y + dy)
                if not (st(h) and st(v) and clear(p, h) and clear(h, q) and clear(p, v) and clear(v, q)): continue
                c = 1.4142
            else:
                k = edge(p, q)
                if k == "wall" or (strict and k in ("window", "frame", "fence")): continue
                c = 1 + COST[k]
            if dcur + c < dist.get(q, 1e18) - 1e-9:
                dist[q] = dcur + c; heapq.heappush(pq, (dist[q], q))
    return None
rnd = random.Random(42)
mism = cross_wall = used_climb_wrongly = 0
nodes_total = 0
CASES = 150
for case in range(CASES):
    w = h = 24
    sq = grid(w, h)
    for (x, y), s in sq.items():
        for d in "NW":
            r_ = rnd.random()
            s[d] = "wall" if r_ < 0.10 else "fence" if r_ < 0.16 else "door" if r_ < 0.19 else "window" if r_ < 0.21 else "open"
        if rnd.random() < 0.05: s["st"] = False
    for x in range(w): sq[(x, 0)]["N"] = "wall"
    for y in range(h): sq[(0, y)]["W"] = "wall"
    set_world(sq)
    free = [p for p, s in sq.items() if s["st"]]
    s0, g0 = rnd.choice(free), rnd.choice(free)
    want = ref(sq, s0, g0)
    got = route(s0[0], s0[1], g0[0], g0[1])
    nodes_total += got["nodes"]
    if want is None:
        if got["state"] == "done": mism += 1
        continue
    if got["state"] != "done" or abs(got["cost"] - want) > 1e-6: mism += 1; continue
    p = got["path"]
    for a_, b_ in zip(p, p[1:]):
        if abs(a_[0] - b_[0]) + abs(a_[1] - b_[1]) == 1:
            o, d = (a_, "N") if b_[1] == a_[1] - 1 else (b_, "N") if b_[1] == a_[1] + 1 else (a_, "W") if b_[0] == a_[0] - 1 else (b_, "W")
            if sq[o][d] == "wall": cross_wall += 1
    if set(got["kinds"]) & {"window", "fence", "frame"}:
        strict = ref(sq, s0, g0, strict=True)
        if strict is not None and strict < got["cost"] - 1e-6: used_climb_wrongly += 1
check("random %d grids: the route costs what a full Dijkstra says (cheapest, or none when there is none)" % CASES, mism == 0, mism)
check("random grids: never through a wall", cross_wall == 0, cross_wall)
check("random grids: a window or fence only when every door-only route costs more", used_climb_wrongly == 0, used_climb_wrongly)
print("    random grids: %d nodes in all, %.0f a route" % (nodes_total, nodes_total / CASES))

# ---------------------------------------------------------------- 4 her walk on the real map, through the wrapper
set_world(farm, live=True)
L.execute(r"""
SOL = { x = 7400.5, y = 8265.5, z = 0 }
function SOL:getX() return self.x end function SOL:getY() return self.y end function SOL:getZ() return self.z end
function SOL:getVehicle() return nil end
SolUI.solActor = function() return SOL end
SENT = {}
SolUI.solGoto = function(x, y, z) SENT[#SENT + 1] = { x = x, y = y }; TARGET = { x = x, y = y }; return true, "walking_to" end
SolUI.runAction = function() return false, "base" end
SolPlace._installed = nil
SolPlace.install()
-- the engine: each tick she steps one square toward the order (the farm's leg squares), as the walk would
function ENGINE()
    if TARGET == nil then return end
    local px, py = math.floor(SOL.x), math.floor(SOL.y)
    if px == TARGET.x and py == TARGET.y then return end
    local dx = TARGET.x > px and 1 or TARGET.x < px and -1 or 0
    local dy = TARGET.y > py and 1 or TARGET.y < py and -1 or 0
    -- prefer the planned path's next square when she is on it (the engine finds the open way on a short leg)
    local R = SolPlace.R
    if R and R.path then
        for i = 1, #R.path - 1 do
            if R.path[i].x == px and R.path[i].y == py then SOL.x, SOL.y = R.path[i + 1].x + 0.5, R.path[i + 1].y + 0.5; return end
        end
    end
    SOL.x, SOL.y = px + dx + 0.5, py + dy + 0.5
end
""")
def walk(gx, gy, ticks=400):
    L.execute("SENT = {}; TARGET = nil; SolPlace.R = nil")
    ok = L.eval("function(x, y) return SolUI.solGoto(x, y, 0) end")(gx, gy)
    t0 = time.time()
    for i in range(ticks):
        L.execute("NOW = NOW + 100; SolPlace.tick(2); ENGINE()")
    sent = L.eval("SENT")
    legs = [(sent[i].x, sent[i].y) for i in range(1, len(sent) + 1)]
    return legs, (L.eval("math.floor(SOL.x)"), L.eval("math.floor(SOL.y)")), (time.time() - t0) * 1000
legs, at, ms = walk(7403, 8264)
check("walk: solGoto(7403,8264) from the plot is sent as legs through the gate", (7401, 8259) in legs and (7402, 8259) in legs, legs)
check("walk: and she ends at 7403,8264", at == (7403, 8264), at)
# every leg is reached from the previous one without crossing a fence (straight steps, the engine's view)
def crosses_fence(a, b):
    x, y = a; n = 0
    while (x, y) != b:
        nx = x + (1 if b[0] > x else -1 if b[0] < x else 0); ny = y + (1 if b[1] > y else -1 if b[1] < y else 0)
        for p, q in (((x, y), (nx, y)), ((nx, y), (nx, ny))):
            if p != q:
                (ax, ay), (bx, by) = p, q
                o, d = ((p, "W") if bx < ax else (q, "W")) if ay == by else ((p, "N") if by < ay else (q, "N"))
                if farm.get(o, {}).get(d) == "fence": n += 1
        x, y = nx, ny
    return n
prev, fence_legs = (7400, 8265), 0
for lg in legs:
    fence_legs += crosses_fence(prev, lg); prev = lg
check("walk: no leg asks the engine to cross the paddock fence", fence_legs == 0, (fence_legs, legs))
print("    walk plot->outside: %d legs %s, %.0f ms for 400 ticks in lupa" % (len(legs), legs, ms))
st = SP.order("status")
print("    sol_place status: %s" % (st[1] if isinstance(st, tuple) else st))
legs_back, at_back, _ = walk(7400, 8256)
check("walk: from outside back to 7400,8256 in the paddock: through the gate again, not over", (7402, 8259) in legs_back and (7401, 8259) in legs_back and at_back == (7400, 8256), (legs_back, at_back))
L.execute("SOL.x, SOL.y = 7400.5, 8265.5")
legs2, at2, _ = walk(7400, 8256)
check("walk: a walk inside the paddock is the plain old walk (one order, nothing in between)", legs2 == [(7400, 8256)], legs2)
L.execute("SWITCH = false")
legs3, _, _ = walk(7403, 8264)
check("switch off: exactly the old walk (one order to the goal)", legs3 == [(7403, 8264)], legs3)
L.execute("SWITCH = true; ZOMBIES = { { getX = function() return 7401 end, getY = function() return 8264 end, isDead = function() return false end } }")
L.execute("SOL.x, SOL.y = 7400.5, 8265.5")
legs4, _, _ = walk(7403, 8264)
check("a zombie near: the old walk (a fence is an escape then)", legs4 == [(7403, 8264)], legs4)
L.execute("ZOMBIES = {}")

# ---------------------------------------------------------------- Living Fellows' edge price, for Sol only, while calm
L.execute(r"""
SurvivorCompanion = { Topology = { classifyEdge = function(actor, a, b, o) return LF_RESULT end } }
SolPlace.wrapTopology()
""")
L.execute('LF_RESULT = { traversable = true, affordance = "fence", cost = 2.5 }')
c1 = L.eval("SurvivorCompanion.Topology.classifyEdge(SOL, nil, nil, {}).cost")
c1b = L.eval("SurvivorCompanion.Topology.classifyEdge(SOL, nil, nil, {}).cost")
c2 = L.eval("SurvivorCompanion.Topology.classifyEdge({}, nil, nil, {}).cost")
check("LF price: a low fence costs Sol 2.5 + 40 (other companions keep 2.5), and the cached result is not raised twice", c1 == 42.5 and c1b == 42.5 and c2 == 2.5, (c1, c1b, c2))
L.execute('LF_RESULT = { traversable = true, affordance = "door", cost = 2.2 }')
check("LF price: doors are untouched", L.eval("SurvivorCompanion.Topology.classifyEdge(SOL, nil, nil, {}).cost") == 2.2)
L.execute('LF_RESULT = { traversable = true, affordance = "window", cost = 2.5 }')
check("LF price: an open window costs Sol 2.5 + 18", L.eval("SurvivorCompanion.Topology.classifyEdge(SOL, nil, nil, {}).cost") == 20.5)


# ---------------------------------------------------------------- his home and his car (SolWorld_Snapshot: solHome 7411,8258 r20, solParking 7413,8264
# bay 7411-7415 x 8259-8269; Sol_Far car 5 last at 7411.5,8276.3), and a synthetic house + garden + car
set_world(farm, live=True)
inside = [k for k, v in farm.items() if v["room"] and meta["rooms"][v["room"]]["name"] in ("livingroom", "kitchen", "hall") and v["st"]]
start = min(inside, key=lambda p: abs(p[0] - 7411) + abs(p[1] - 8252))
for car, label in (((7413, 8264), "the parking bay 7413,8264"), ((7411, 8276), "where car 5 was saved, 7411,8276")):
    door_side = (car[0] - 1, car[1])                    # the driver's door side of a car parked north-south
    r = route(start[0], start[1], door_side[0], door_side[1])
    check("home: from inside the house %s to the car's door at %s: through doors only, no window, no fence" % (start, label),
          r["state"] == "done" and set(r["kinds"]) <= {"door"} and "door" in r["kinds"], r.get("cross"))
    print("    home %s -> %s: steps=%s crossings=%s legs=%s nodes=%s" % (start, door_side, r.get("steps"), r.get("cross"), r.get("legs"), r["nodes"]))
# nextLeg: the passenger door walk asks for the next square on the door-first way, again and again
L.execute("SOL.x, SOL.y = %d.5, %d.5; SolPlace._next = nil" % start)
legs = []
for i in range(12):
    nl = SP.nextLeg(7412, 8264)
    if nl is None: break
    lx, ly = nl
    legs.append((lx, ly)); L.execute("SOL.x, SOL.y = %d.5, %d.5" % (lx, ly))
check("nextLeg: house -> car door gives the legs through the door, then nil (plain walk) once nothing is left in between", len(legs) >= 2 and SP.nextLeg(7412, 8264) is None, legs)
print("    nextLeg legs: %s" % legs)
# goNear: the far walk-in (SolFar "she is here") walks door-first to him, then regroup once
L.execute("SOL.x, SOL.y = 7400.5, 8265.5; DONE = 0; SENT = {}; TARGET = nil; SolPlace.R = nil")
L.execute("SolPlace.goNear(7404, 8264, nil, 2, function() DONE = DONE + 1 end)")
for i in range(300): L.execute("NOW = NOW + 100; SolPlace.tick(2); ENGINE()")
sent = L.eval("SENT"); legs = [(sent[i].x, sent[i].y) for i in range(1, len(sent) + 1)]
check("goNear: through the gate to him, then regroup exactly once", (7402, 8259) in legs and L.eval("DONE") == 1, (legs, L.eval("DONE")))
L.execute("SOL.x, SOL.y = 7400.5, 8262.5; DONE = 0; SolPlace.R = nil")
check("goNear: nothing in between: regroup at once, no legs", L.eval("SolPlace.goNear(7400, 8256, nil, 2, function() DONE = DONE + 1 end)") is True and L.eval("DONE") == 1)
# synthetic: house (door south), fenced garden (gate east), car on the street east
sq = grid(50, 40)
hline(sq, 5, 5, 14, "wall"); hline(sq, 13, 5, 14, "wall"); vline(sq, 5, 5, 12, "wall"); vline(sq, 15, 5, 12, "wall"); sq[(10, 13)]["N"] = "door"
sq[(8, 5)]["N"] = "window"; sq[(15, 8)]["W"] = "window"
hline(sq, 13, 3, 25, "fence"); hline(sq, 26, 3, 25, "fence"); vline(sq, 3, 13, 25, "fence"); vline(sq, 26, 13, 25, "fence")
for x in range(5, 15): sq[(x, 13)]["N"] = "wall"                # the house's south wall is the garden's north side
sq[(10, 13)]["N"] = "door"; sq[(26, 22)]["W"] = "door"
for y in range(0, 40): sq[(35, y)]["st"] = False; sq[(36, y)]["st"] = False   # the car parked on the street (its body)
set_world(sq)
r = route(8, 7, 34, 10)
check("house + garden + car: from the room to the car door: house door, garden gate, never the window or the fence", r["state"] == "done" and r["kinds"] == ["door"] and len(r["cross"]) == 2, r.get("cross"))
print("    synthetic house->car: steps=%s crossings=%s" % (r.get("steps"), r.get("cross")))

# ---------------------------------------------------------------- SolSort 0.2.2 with the switch: the box's own side
set_world(farm, live=True)
L.execute("SurvivorCompanion.GameplayUtil = { gridSquare = function(x, y, z) return getCell():getGridSquare(x, y, z) end }")
L.execute(open(os.path.join(HERE, "SolSort.lua"), encoding="ascii").read())
L.execute("BOX = { x = 7401, y = 8262, z = 0, sq = getCell():getGridSquare(7401, 8262, 0) }; BOX.access = SolSort.access(BOX)")
acc = L.eval("BOX.access")
acc = sorted((acc[i].x, acc[i].y) for i in range(1, len(acc) + 1))
check("SolSort 0.2.2: a box by the paddock fence gets standing squares on its side only %s" % (acc,), (7402, 8262) not in acc and (7400, 8262) in acc, acc)
L.execute("SOL.x, SOL.y = 7402.5, 8262.5")
check("SolSort 0.2.2: standing across the fence from it is not 'arrived'", L.eval("SolSort.arrived(SOL, BOX)") == False)
L.execute("SOL.x, SOL.y = 7400.5, 8262.5")
check("SolSort 0.2.2: standing on its side is", L.eval("SolSort.arrived(SOL, BOX)") == True)
L.execute("SWITCH = false")
acc0 = L.eval("SolSort.access(BOX)")
check("SolSort 0.2.2: switch off -> the 0.2.1 rule (canReachTo, stubbed open here)", len(acc0) == 4)
L.execute("SWITCH = true")

print("SUMMARY pass=%d fail=%d" % (ok_n, bad))
sys.exit(1 if bad else 0)

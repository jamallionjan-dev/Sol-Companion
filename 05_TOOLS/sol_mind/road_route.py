"""Her way to him on the game's own roads, from the gazetteer built offline. Runs here in the Mind: no game time spent and no chunk loaded."""
import gzip, heapq, json, math, os, threading

STEP = 12             # tiles between graph points along a road
JOIN = 14             # two roads this close meet
BRIDGE = 48           # the last gaps between otherwise separate road nets
CELL = 16
MAX_OFF_ROAD = 900    # further than this from any road and there is no route to speak of
DIRECT = 90           # this close she just walks over
MAX_POINTS = 400
_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gazetteer.json.gz")


def _simplify(points, tolerance):
    """Douglas-Peucker without recursion."""
    if len(points) < 3: return list(points)
    keep = {0, len(points) - 1}
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = points[a]; bx, by = points[b]
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy) or 1.0
        worst, at = -1.0, None
        for i in range(a + 1, b):
            d = abs((points[i][0] - ax) * dy - (points[i][1] - ay) * dx) / length
            if d > worst: worst, at = d, i
        if at is not None and worst > tolerance:
            keep.add(at); stack += [(a, at), (at, b)]
    return [points[i] for i in sorted(keep)]


class Roads:
    def __init__(self, streets):
        self.xy, self.adj, self.street = [], [], []
        for sid, s in enumerate(streets):
            prev = None
            for (ax, ay), (bx, by) in zip(s["p"], s["p"][1:]):
                n = max(1, int(math.ceil(math.hypot(bx - ax, by - ay) / STEP)))
                for k in range(0 if prev is None else 1, n + 1):
                    i = self._node(ax + (bx - ax) * k / n, ay + (by - ay) * k / n, sid)
                    if prev is not None: self._edge(prev, i)
                    prev = i
        self.cells = {}
        for i, (x, y) in enumerate(self.xy): self.cells.setdefault((int(x // CELL), int(y // CELL)), []).append(i)
        self._join_streets()
        self._join_nets()

    def _node(self, x, y, sid):
        self.xy.append((x, y)); self.adj.append([]); self.street.append(sid)
        return len(self.xy) - 1

    def _edge(self, a, b):
        d = math.dist(self.xy[a], self.xy[b])
        self.adj[a].append((b, d)); self.adj[b].append((a, d))

    def _join_streets(self):
        reach = int(math.ceil(JOIN / CELL))
        for i, (x, y) in enumerate(self.xy):
            cx, cy = int(x // CELL), int(y // CELL)
            nearest = {}
            for gx in range(cx - reach, cx + reach + 1):
                for gy in range(cy - reach, cy + reach + 1):
                    for j in self.cells.get((gx, gy), ()):
                        if j <= i or self.street[j] == self.street[i]: continue
                        d = math.dist(self.xy[i], self.xy[j])
                        if d <= JOIN and d < nearest.get(self.street[j], (1e9, 0))[0]: nearest[self.street[j]] = (d, j)
            for _, j in nearest.values(): self._edge(i, j)

    def _components(self):
        seen = [-1] * len(self.xy)
        sizes = []
        for s in range(len(self.xy)):
            if seen[s] >= 0: continue
            c = len(sizes); seen[s] = c; stack = [s]; n = 0
            while stack:
                a = stack.pop(); n += 1
                for b, _ in self.adj[a]:
                    if seen[b] < 0: seen[b] = c; stack.append(b)
            sizes.append(n)
        return seen, sizes

    def _join_nets(self):
        """Only the leftovers: a road that stops a little short of the next one."""
        reach = int(math.ceil(BRIDGE / CELL))
        for _ in range(64):
            seen, sizes = self._components()
            if len(sizes) <= 1: return
            joined = False
            for c in sorted(range(len(sizes)), key=lambda k: sizes[k])[:-1]:
                best = (BRIDGE + 1, None, None)
                for i, (x, y) in enumerate(self.xy):
                    if seen[i] != c: continue
                    cx, cy = int(x // CELL), int(y // CELL)
                    for gx in range(cx - reach, cx + reach + 1):
                        for gy in range(cy - reach, cy + reach + 1):
                            for j in self.cells.get((gx, gy), ()):
                                if seen[j] != c:
                                    d = math.dist(self.xy[i], self.xy[j])
                                    if d < best[0]: best = (d, i, j)
                if best[1] is not None:
                    self._edge(best[1], best[2]); joined = True
                    break                                                        # the nets changed: count them again
            if not joined: return

    def nearest(self, x, y):
        best, at = 1e18, None
        for i, (a, b) in enumerate(self.xy):
            d = (a - x) ** 2 + (b - y) ** 2
            if d < best: best, at = d, i
        return at, math.sqrt(best) if at is not None else 1e9

    def _astar(self, start, goal):
        gx, gy = self.xy[goal]
        best = {start: 0.0}; came = {}
        heap = [(math.hypot(self.xy[start][0] - gx, self.xy[start][1] - gy), start)]
        while heap:
            _, a = heapq.heappop(heap)
            if a == goal:
                path = [a]
                while a in came: a = came[a]; path.append(a)
                path.reverse()
                return path, best[goal]
            for b, d in self.adj[a]:
                g = best[a] + d
                if g < best.get(b, 1e18):
                    best[b] = g; came[b] = a
                    heapq.heappush(heap, (g + math.hypot(self.xy[b][0] - gx, self.xy[b][1] - gy), b))
        return None, 0.0

    def route(self, fx, fy, tx, ty):
        """(way points between her and him, tiles in all), or None when there is no way. Empty way points: she walks straight over."""
        straight = math.hypot(tx - fx, ty - fy)
        if straight <= DIRECT: return [], straight
        a, off_a = self.nearest(fx, fy)
        b, off_b = self.nearest(tx, ty)
        if a is None or b is None or off_a > MAX_OFF_ROAD or off_b > MAX_OFF_ROAD: return None
        if off_a + off_b >= straight: return [], straight                        # the roads are further than he is
        path, tiles = self._astar(a, b)
        if path is None: return None
        points = [self.xy[i] for i in path]
        tolerance = 4.0
        out = _simplify(points, tolerance)
        while len(out) > MAX_POINTS:
            tolerance *= 2
            out = _simplify(points, tolerance)
        return [(int(round(x)), int(round(y))) for x, y in out], tiles + off_a + off_b


_roads, _lock, _buildings = None, threading.Lock(), None


def route(fx, fy, tx, ty, path=_DEFAULT):
    """The first call builds the network, about a second, once."""
    global _roads
    with _lock:
        if _roads is None:
            with gzip.open(path, "rt", encoding="utf-8") as f: _roads = Roads(json.load(f)["streets"])
    return _roads.route(fx, fy, tx, ty)


CHUNK = 8
BUILDING_MARGIN = 4
MAX_EXTRA_CHUNKS = 8    # the road comes no nearer to him than this: not a pickup he could walk to


def _clear_of_buildings(x, y, path):
    global _buildings
    with _lock:
        if _buildings is None:
            with gzip.open(path, "rt", encoding="utf-8") as f: _buildings = json.load(f)["buildings"]
    return not any(b[0] - BUILDING_MARGIN <= x <= b[2] + BUILDING_MARGIN and b[1] - BUILDING_MARGIN <= y <= b[3] + BUILDING_MARGIN for b in _buildings)


def pickup_spot(cx, cy, px, py, ring, path=_DEFAULT):
    """Where on the road from her car to him the car can wait, just outside what is loaded around him: (x, y, tiles she drove), or None."""
    found = route(cx, cy, px, py, path)
    if found is None or len(found[0]) < 2: return None
    points = [found[0][0]] + found[0][1:]                                       # the road only: not the stretch from where the car is parked
    pwx, pwy = int(px // CHUNK), int(py // CHUNK)
    gone = math.dist((cx, cy), found[0][0])
    prev = points[0]
    best, closest = None, ring + MAX_EXTRA_CHUNKS + 1
    for point in points[1:]:
        seg = math.dist(prev, point)
        steps = max(1, int(seg / 2))
        for k in range(1, steps + 1):
            x, y = prev[0] + (point[0] - prev[0]) * k / steps, prev[1] + (point[1] - prev[1]) * k / steps
            reach = max(abs(int(x // CHUNK) - pwx), abs(int(y // CHUNK) - pwy))
            if ring + 2 <= reach <= closest and _clear_of_buildings(x, y, path):       # the last such point on the way is the nearest to him
                best, closest = (math.floor(x) + 0.5, math.floor(y) + 0.5, gone + seg * k / steps), reach
        gone += seg
        prev = point
    return best


# ---------------------------------------------------------------- far_arrival: where the car and Sol appear together (apply_s71)
STRAIGHT_AHEAD = 12     # tiles of the same street ahead of the spot that run straight: she can set off at once
STRAIGHT_BEHIND = 6
STRAIGHT_COS = math.cos(math.radians(20))
HELI_MARGIN = 8         # a helicopter lands this far from any building


def _unit(ax, ay, bx, by):
    d = math.hypot(bx - ax, by - ay) or 1.0
    return (bx - ax) / d, (by - ay) / d


def _straight_run(pts, streets, k, t, hx, hy, ahead, forward):
    """Tiles of the same street from point t on segment k, going forward or back, while every segment keeps within 20 degrees of hx,hy."""
    sid = streets[k]
    run = (1 - t) * math.dist(pts[k], pts[k + 1]) if forward else t * math.dist(pts[k], pts[k + 1])
    j = k + 1 if forward else k - 1
    while run < ahead and 0 <= j < len(pts) - 1:
        if streets[j] != sid or streets[j + 1] != sid: break
        ux, uy = _unit(*pts[j], *pts[j + 1])
        if ux * hx + uy * hy < STRAIGHT_COS: break
        run += math.dist(pts[j], pts[j + 1])
        j += 1 if forward else -1
    return run


def pickup_spot_dir(cx, cy, px, py, ring, kind="car", path=_DEFAULT, roads=None):
    """Where the car (and she, in it) appear: (x, y, tiles driven, heading in degrees toward him along the road), or None.
    On a street of the game's own map, just outside what is loaded around him (ring + 2 chunks), the last such point on her way to him, away
    from buildings, where the street runs straight 12 tiles ahead and 6 behind. A helicopter needs no road: an open spot on the straight line."""
    if kind == "heli": return heli_spot(cx, cy, px, py, ring, path)
    global _roads
    R = roads
    if R is None:
        with _lock:
            if _roads is None:
                with gzip.open(path, "rt", encoding="utf-8") as f: _roads = Roads(json.load(f)["streets"])
        R = _roads
    a, off_a = R.nearest(cx, cy)
    b, off_b = R.nearest(px, py)
    if a is None or b is None or off_a > MAX_OFF_ROAD or off_b > MAX_OFF_ROAD: return None
    nodes, _ = R._astar(a, b)
    if not nodes or len(nodes) < 2: return None
    pts = [R.xy[i] for i in nodes]
    streets = [R.street[i] for i in nodes]
    pwx, pwy = int(px // CHUNK), int(py // CHUNK)
    gone = off_a
    best, closest = None, ring + MAX_EXTRA_CHUNKS + 1
    for k in range(len(pts) - 1):
        seg = math.dist(pts[k], pts[k + 1])
        if streets[k] == streets[k + 1] and seg > 0:                             # a joint between two streets is no place to stop
            hx, hy = _unit(*pts[k], *pts[k + 1])
            steps = max(1, int(seg))
            for s in range(steps + 1):
                t = s / steps
                x, y = pts[k][0] + (pts[k + 1][0] - pts[k][0]) * t, pts[k][1] + (pts[k + 1][1] - pts[k][1]) * t
                reach = max(abs(int(x // CHUNK) - pwx), abs(int(y // CHUNK) - pwy))
                if not (ring + 2 <= reach <= closest): continue
                if _straight_run(pts, streets, k, t, hx, hy, STRAIGHT_AHEAD, True) < STRAIGHT_AHEAD: continue
                if _straight_run(pts, streets, k, t, -hx, -hy, STRAIGHT_BEHIND, False) < STRAIGHT_BEHIND: continue
                if roads is None and not _clear_of_buildings(x, y, path): continue
                best, closest = (math.floor(x) + 0.5, math.floor(y) + 0.5, gone + seg * t, math.degrees(math.atan2(hy, hx))), reach
        gone += seg
    return best


def heli_spot(cx, cy, px, py, ring, path=_DEFAULT, clear=None):
    """A helicopter: on the straight line from where it is to him, the nearest point just outside what is loaded (ring + 2 chunks), moved
    sideways up to 24 tiles to an open place (no building within HELI_MARGIN). (x, y, tiles flown, heading), or None."""
    clear = clear or (lambda x, y: _clear_of_buildings_margin(x, y, path, HELI_MARGIN))
    d = math.hypot(px - cx, py - cy)
    if d < 1: return None
    ux, uy = (px - cx) / d, (py - cy) / d
    pwx, pwy = int(px // CHUNK), int(py // CHUNK)
    for back in range(0, int(d)):
        x, y = px - ux * back, py - uy * back
        reach = max(abs(int(x // CHUNK) - pwx), abs(int(y // CHUNK) - pwy))
        if reach < ring + 2: continue
        for side in (0, 4, -4, 8, -8, 12, -12, 16, -16, 20, -20, 24, -24):
            sx, sy = x - uy * side, y + ux * side
            reach2 = max(abs(int(sx // CHUNK) - pwx), abs(int(sy // CHUNK) - pwy))
            if reach2 >= ring + 2 and clear(sx, sy):
                return (math.floor(sx) + 0.5, math.floor(sy) + 0.5, math.hypot(sx - cx, sy - cy), math.degrees(math.atan2(uy, ux)))
    return None


def _clear_of_buildings_margin(x, y, path, margin):
    global _buildings
    with _lock:
        if _buildings is None:
            with gzip.open(path, "rt", encoding="utf-8") as f: _buildings = json.load(f)["buildings"]
    return not any(b[0] - margin <= x <= b[2] + margin and b[1] - margin <= y <= b[3] + margin for b in _buildings)


# ---------------------------------------------------------------- far_arrival: where the car and Sol appear together (apply_s71)
STRAIGHT_AHEAD = 12     # tiles of the same street ahead of the spot that run straight: she can set off at once
STRAIGHT_BEHIND = 6
STRAIGHT_COS = math.cos(math.radians(20))
HELI_MARGIN = 8         # a helicopter lands this far from any building
INNER_MIN = 4           # inside the loaded ring: at least this many chunks from him (32+ tiles: out of his view at any zoom the game allows)


def _unit(ax, ay, bx, by):
    d = math.hypot(bx - ax, by - ay) or 1.0
    return (bx - ax) / d, (by - ay) / d


def _straight_run(pts, streets, k, t, hx, hy, ahead, forward):
    """Tiles of the same street from point t on segment k, going forward or back, while every segment keeps within 20 degrees of hx,hy."""
    sid = streets[k]
    run = (1 - t) * math.dist(pts[k], pts[k + 1]) if forward else t * math.dist(pts[k], pts[k + 1])
    j = k + 1 if forward else k - 1
    while run < ahead and 0 <= j < len(pts) - 1:
        if streets[j] != sid or streets[j + 1] != sid: break
        ux, uy = _unit(*pts[j], *pts[j + 1])
        if ux * hx + uy * hy < STRAIGHT_COS: break
        run += math.dist(pts[j], pts[j + 1])
        j += 1 if forward else -1
    return run


def pickup_spot_dir(cx, cy, px, py, ring, kind="car", path=_DEFAULT, roads=None, inner=False):
    """Where the car (and she, in it) appear: (x, y, tiles driven, heading in degrees toward him along the road), or None.
    On a street of the game's own map, just outside what is loaded around him (ring + 2 chunks), the last such point on her way to him, away
    from buildings, where the street runs straight 12 tiles ahead and 6 behind. A helicopter needs no road: an open spot on the straight line.
    inner=True (the game can bring the car into the loaded area): the same, but INSIDE the loaded ring, INNER_MIN..ring-1 chunks from him."""
    lo, hi = (INNER_MIN, ring - 1) if inner else (ring + 2, ring + MAX_EXTRA_CHUNKS + 1)
    if lo > hi: return None
    if kind == "heli": return heli_spot(cx, cy, px, py, ring, path, lo=lo, hi=hi)
    global _roads
    R = roads
    if R is None:
        with _lock:
            if _roads is None:
                with gzip.open(path, "rt", encoding="utf-8") as f: _roads = Roads(json.load(f)["streets"])
        R = _roads
    a, off_a = R.nearest(cx, cy)
    b, off_b = R.nearest(px, py)
    if a is None or b is None or off_a > MAX_OFF_ROAD or off_b > MAX_OFF_ROAD: return None
    nodes, _ = R._astar(a, b)
    if not nodes or len(nodes) < 2: return None
    pts = [R.xy[i] for i in nodes]
    streets = [R.street[i] for i in nodes]
    pwx, pwy = int(px // CHUNK), int(py // CHUNK)
    gone = off_a
    best, closest = None, hi + 1
    for k in range(len(pts) - 1):
        seg = math.dist(pts[k], pts[k + 1])
        if streets[k] == streets[k + 1] and seg > 0:                             # a joint between two streets is no place to stop
            hx, hy = _unit(*pts[k], *pts[k + 1])
            steps = max(1, int(seg))
            for s in range(steps + 1):
                t = s / steps
                x, y = pts[k][0] + (pts[k + 1][0] - pts[k][0]) * t, pts[k][1] + (pts[k + 1][1] - pts[k][1]) * t
                reach = max(abs(int(x // CHUNK) - pwx), abs(int(y // CHUNK) - pwy))
                if not (lo <= reach <= min(hi, closest)): continue
                if _straight_run(pts, streets, k, t, hx, hy, STRAIGHT_AHEAD, True) < STRAIGHT_AHEAD: continue
                if _straight_run(pts, streets, k, t, -hx, -hy, STRAIGHT_BEHIND, False) < STRAIGHT_BEHIND: continue
                if roads is None and not _clear_of_buildings(x, y, path): continue
                best, closest = (math.floor(x) + 0.5, math.floor(y) + 0.5, gone + seg * t, math.degrees(math.atan2(hy, hx))), reach
        gone += seg
    return best


def heli_spot(cx, cy, px, py, ring, path=_DEFAULT, clear=None, lo=None, hi=None):
    """A helicopter: on the straight line from where it is to him, the nearest point just outside what is loaded (ring + 2 chunks), moved
    sideways up to 24 tiles to an open place (no building within HELI_MARGIN). (x, y, tiles flown, heading), or None."""
    clear = clear or (lambda x, y: _clear_of_buildings_margin(x, y, path, HELI_MARGIN))
    lo = ring + 2 if lo is None else lo
    hi = 10 ** 6 if hi is None else hi
    d = math.hypot(px - cx, py - cy)
    if d < 1: return None
    ux, uy = (px - cx) / d, (py - cy) / d
    pwx, pwy = int(px // CHUNK), int(py // CHUNK)
    for back in range(0, int(d)):
        x, y = px - ux * back, py - uy * back
        reach = max(abs(int(x // CHUNK) - pwx), abs(int(y // CHUNK) - pwy))
        if not (lo <= reach <= hi): continue
        for side in (0, 4, -4, 8, -8, 12, -12, 16, -16, 20, -20, 24, -24):
            sx, sy = x - uy * side, y + ux * side
            reach2 = max(abs(int(sx // CHUNK) - pwx), abs(int(sy // CHUNK) - pwy))
            if lo <= reach2 <= hi and clear(sx, sy):
                return (math.floor(sx) + 0.5, math.floor(sy) + 0.5, math.hypot(sx - cx, sy - cy), math.degrees(math.atan2(uy, ux)))
    return None


def _clear_of_buildings_margin(x, y, path, margin):
    global _buildings
    with _lock:
        if _buildings is None:
            with gzip.open(path, "rt", encoding="utf-8") as f: _buildings = json.load(f)["buildings"]
    return not any(b[0] - margin <= x <= b[2] + margin and b[1] - margin <= y <= b[3] + margin for b in _buildings)

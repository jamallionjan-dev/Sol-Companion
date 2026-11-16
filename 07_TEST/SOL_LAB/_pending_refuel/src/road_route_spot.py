

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

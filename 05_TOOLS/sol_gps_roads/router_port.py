"""Python port of the live SCRoadRouter (LF + 2026-10-25 bridge patch), for diagnosis only."""
import heapq, math, re, sys
from collections import defaultdict

EPS = 1e-4
MAX_SEGMENTS, MAX_NODES, MARGIN, MAX_CONNECTOR, OFFROAD = 4096, 8192, 160.0, 100.0, 3.0


def load(path):
    text = open(path, encoding="utf-8").read()
    lines = []
    for m in re.finditer(r'<street name="([^"]*)" width="([^"]*)">(.*?)</street>', text, re.S):
        pts = [(float(x), float(y)) for x, y in re.findall(r'<point x="([-\d.]+)" y="([-\d.]+)"', m.group(3))]
        lines.append((m.group(1), pts, float(m.group(2))))
    return lines


def dist(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])


def project(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; l = dx * dx + dy * dy
    if l <= EPS: return 0.0
    return max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l))


def segd(p, a, b):
    t = project(p, a, b); return dist(p, (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))


def route(lines, s, t, margin=MARGIN, verbose=False):
    minx, maxx = min(s[0], t[0]) - margin, max(s[0], t[0]) + margin
    miny, maxy = min(s[1], t[1]) - margin, max(s[1], t[1]) + margin
    segs = []  # (a, b, name, line, width, starts, ends)
    for li, (name, pts, w) in enumerate(lines):
        prev = None
        for i, p in enumerate(pts):
            if prev is not None and dist(prev, p) > EPS and min(prev[0], p[0]) <= maxx and max(prev[0], p[0]) >= minx \
                    and min(prev[1], p[1]) <= maxy and max(prev[1], p[1]) >= miny:
                segs.append((prev, p, name, li, w, i - 1 == 0, i == len(pts) - 1))
                if len(segs) > MAX_SEGMENTS: return "BUDGET_EXCEEDED", "segment_limit", len(segs)
            prev = p
    if not segs: return "NO_ROAD_DATA", None, 0
    bins = defaultdict(list)
    for sid, sg in enumerate(segs):
        for bx in range(math.floor(min(sg[0][0], sg[1][0]) / 32), math.floor(max(sg[0][0], sg[1][0]) / 32) + 1):
            for by in range(math.floor(min(sg[0][1], sg[1][1]) / 32), math.floor(max(sg[0][1], sg[1][1]) / 32) + 1):
                bins[(bx, by)].append(sid)
    junctions = []
    def join(sid, end):
        own = segs[sid]; best = None; bg = 1e18; bridge = None; brg = 1e18; seen = set()
        for bx in range(math.floor((end[0] - 24) / 32), math.floor((end[0] + 24) / 32) + 1):
            for by in range(math.floor((end[1] - 24) / 32), math.floor((end[1] + 24) / 32) + 1):
                for oid in bins.get((bx, by), ()):
                    o = segs[oid]
                    if o[3] == own[3] or oid in seen: continue
                    seen.add(oid)
                    g = segd(end, o[0], o[1])
                    if g <= EPS: return
                    tol = min(12.0, o[4] * 0.5 + 1.5)
                    if g <= tol and g < bg: best, bg = oid, g
                    lim = 24.0 if (own[2].strip() and own[2] == o[2]) else 16.0
                    if g <= lim and g < brg: bridge, brg = oid, g
        if best is None: best = bridge
        if best is None: return
        o = segs[best]; tt = project(end, o[0], o[1])
        junctions.append((end, (o[0][0] + (o[1][0] - o[0][0]) * tt, o[0][1] + (o[1][1] - o[0][1]) * tt), best, tt, own[2]))
    for sid, sg in enumerate(segs):
        if sg[5]: join(sid, sg[0])
        if sg[6]: join(sid, sg[1])
    splits = [{0.0: sg[0], 1.0: sg[1]} for sg in segs]
    # crossings
    for sid in range(len(segs)):
        pass
    cells = defaultdict(list); compared = set()
    for sid, sg in enumerate(segs):
        for bx in range(math.floor(min(sg[0][0], sg[1][0]) / 32), math.floor(max(sg[0][0], sg[1][0]) / 32) + 1):
            for by in range(math.floor(min(sg[0][1], sg[1][1]) / 32), math.floor(max(sg[0][1], sg[1][1]) / 32) + 1):
                for oid in cells[(bx, by)]:
                    if (oid, sid) in compared: continue
                    compared.add((oid, sid))
                    f, g = segs[oid], sg
                    rx, ry = f[1][0] - f[0][0], f[1][1] - f[0][1]; sx, sy = g[1][0] - g[0][0], g[1][1] - g[0][1]
                    den = rx * sy - ry * sx
                    if abs(den) <= EPS: continue
                    qx, qy = g[0][0] - f[0][0], g[0][1] - f[0][1]
                    a = (qx * sy - qy * sx) / den; u = (qx * ry - qy * rx) / den
                    if a < -EPS or a > 1 + EPS or u < -EPS or u > 1 + EPS: continue
                    a = max(0, min(1, a)); u = max(0, min(1, u))
                    pt = (f[0][0] + rx * a, f[0][1] + ry * a)
                    splits[oid][a] = pt; splits[sid][u] = pt
                cells[(bx, by)].append(sid)
    for j in junctions: splits[j[2]][j[3]] = j[1]
    nodes, nid, edges, links = [], {}, [], []
    def node(p):
        k = (round(p[0] * 1000), round(p[1] * 1000))
        if k in nid: return nid[k]
        nid[k] = len(nodes); nodes.append(p); links.append([]); return nid[k]
    def edge(a, b, name, w):
        l = dist(a, b)
        if l <= EPS: return
        fa, fb = node(a), node(b)
        if fa == fb: return
        eid = len(edges); edges.append((fa, fb, l, name, w)); links[fa].append((fb, eid, l)); links[fb].append((fa, eid, l))
    for sid, sg in enumerate(segs):
        prev = None
        for k in sorted(splits[sid]):
            p = splits[sid][k]
            if prev is not None: edge(prev, p, sg[2], sg[4])
            prev = p
    for j in junctions: edge(j[0], j[1], j[4], segs[j[2]][4])
    if len(nodes) > MAX_NODES: return "BUDGET_EXCEEDED", "graph_limit", len(nodes)
    def attach(p):
        out = []
        for eid, (a, b, l, n, w) in enumerate(edges):
            A, B = nodes[a], nodes[b]; tt = project(p, A, B); pr = (A[0] + (B[0] - A[0]) * tt, A[1] + (B[1] - A[1]) * tt)
            c = dist(p, pr)
            if c <= MAX_CONNECTOR: out.append((c, eid, tt, pr))
        out.sort(); return out[:8]
    ent, ex = attach(s), attach(t)
    if not ent: return "NO_ENTRY_CANDIDATE", None, len(nodes)
    if not ex: return "NO_EXIT_CANDIDATE", None, len(nodes)
    cost = [math.inf] * len(nodes); prev = [-1] * len(nodes); q = []
    for c, eid, tt, pr in ent:
        a, b, l, n, w = edges[eid]
        for nd, ll in ((a, tt * l), (b, (1 - tt) * l)):
            v = c * OFFROAD + ll
            if v < cost[nd]: cost[nd] = v; heapq.heappush(q, (v, nd))
    expanded = 0
    while q:
        c, nd = heapq.heappop(q)
        if c > cost[nd] + EPS: continue
        expanded += 1
        if expanded > MAX_NODES: return "BUDGET_EXCEEDED", "search_limit", len(nodes)
        for to, eid, l in links[nd]:
            if c + l + EPS < cost[to]: cost[to] = c + l; prev[to] = nd; heapq.heappush(q, (c + l, to))
    best = math.inf; bn = -1
    for c, eid, tt, pr in ex:
        a, b, l, n, w = edges[eid]
        for nd, ll in ((a, tt * l), (b, (1 - tt) * l)):
            v = cost[nd] + ll + c * OFFROAD
            if v < best: best, bn = v, nd
    if bn < 0 or best == math.inf:
        return "NO_CONNECTED_ROUTE/INCOMPLETE", (nodes, edges, links, cost, ent, ex), len(nodes)
    path = []
    while bn >= 0: path.append(nodes[bn]); bn = prev[bn]
    return "READY", path[::-1], len(nodes)


if __name__ == "__main__":
    G = r"C:/Program Files (x86)/Steam/steamapps/common/ProjectZomboid/media/maps/Muldraugh, KY/streets.xml"
    T = r"C:/Users/JAMAL/Desktop/Sol/07_TEST/SOL_LAB/profile/Zomboid/mods/Sol_LAB/42/media/maps/Sol_Trails/streets.xml"
    paved = load(G); trails = load(T)
    print("paved streets", len(paved), "trail streets", len(trails))
    s, t = (7413, 8262), (10840, 10120)
    for label, lines in (("paved", paved), ("paved+trails", paved + trails)):
        for m in (160, 600, 1500):
            st, info, n = route(lines, s, t, m)
            print(label, "margin", m, st, "nodes", n, (len(info) if st == "READY" else ""))

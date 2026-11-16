"""Builds Sol's static road graph (SolStaticRoadsData.lua) from the game's own street files.

The whole map is known from the game files: media/maps/Muldraugh, KY/streets.xml (paved streets, the same file the
game's street API and the Living Fellows router read) plus Sol's dirt roads (media/maps/Sol_Trails/streets.xml, made
by 05_TOOLS/sol_trails/gen_trails.py from the game's worldmap.xml). Nothing here depends on what the player has seen.

The graph is joined exactly like the live router (SCRoadRouter + the 2026-10-25 bridge patch): streets are split where
they cross, and a street end joins another street within its half width + 1.5 tiles (max 12), else bridges to the
nearest street within 16 tiles (24 for the same street name). The only difference: the whole map at once, no clip box.

    python gen_static_roads.py [out.lua]     default: 07_TEST/SOL_LAB/_pending_refuel/SolStaticRoadsData.lua
"""
import math, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from router_port import load  # noqa: E402

PAVED = r"C:/Program Files (x86)/Steam/steamapps/common/ProjectZomboid/media/maps/Muldraugh, KY/streets.xml"
TRAILS_CANDIDATES = [
    os.path.join(ROOT, "01_WORK", "Sol", "42", "media", "maps", "Sol_Trails", "streets.xml"),
    os.path.join(ROOT, "07_TEST", "SOL_LAB", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "maps", "Sol_Trails", "streets.xml"),
]
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "07_TEST", "SOL_LAB", "_pending_refuel", "SolStaticRoadsData.lua")
EPS = 1e-4
CHUNK = 12000


def dist(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])


def project(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; l = dx * dx + dy * dy
    if l <= EPS: return 0.0
    return max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l))


def segd(p, a, b):
    t = project(p, a, b); return dist(p, (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))


def cells_of(a, b):
    for bx in range(math.floor(min(a[0], b[0]) / 32), math.floor(max(a[0], b[0]) / 32) + 1):
        for by in range(math.floor(min(a[1], b[1]) / 32), math.floor(max(a[1], b[1]) / 32) + 1):
            yield bx, by


def build(lines):
    """lines: [(name, [(x, y)], width, kind)] -> nodes [(x, y)], edges [(a, b, name, width, kind)] (0-based)."""
    segs = []
    for li, (name, pts, w, kind) in enumerate(lines):
        w = max(0.0, min(64.0, w))
        for i in range(1, len(pts)):
            if dist(pts[i - 1], pts[i]) > EPS:
                segs.append((pts[i - 1], pts[i], name, li, w, i - 1 == 0, i == len(pts) - 1, kind))
    bins = defaultdict(list)
    for sid, sg in enumerate(segs):
        for c in cells_of(sg[0], sg[1]): bins[c].append(sid)
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
                    if g <= min(12.0, o[4] * 0.5 + 1.5) and g < bg: best, bg = oid, g
                    lim = 24.0 if (own[2].strip() and own[2] == o[2]) else 16.0
                    if g <= lim and g < brg: bridge, brg = oid, g
        if best is None: best = bridge
        if best is None: return
        o = segs[best]; t = project(end, o[0], o[1])
        junctions.append((end, (o[0][0] + (o[1][0] - o[0][0]) * t, o[0][1] + (o[1][1] - o[0][1]) * t), best, t, own[2], own[7]))

    for sid, sg in enumerate(segs):
        if sg[5]: join(sid, sg[0])
        if sg[6]: join(sid, sg[1])
    splits = [{0.0: sg[0], 1.0: sg[1]} for sg in segs]
    cells = defaultdict(list); compared = set()
    for sid, g in enumerate(segs):
        for c in cells_of(g[0], g[1]):
            for oid in cells[c]:
                if (oid, sid) in compared: continue
                compared.add((oid, sid))
                f = segs[oid]
                rx, ry = f[1][0] - f[0][0], f[1][1] - f[0][1]; sx, sy = g[1][0] - g[0][0], g[1][1] - g[0][1]
                den = rx * sy - ry * sx
                if abs(den) <= EPS: continue
                qx, qy = g[0][0] - f[0][0], g[0][1] - f[0][1]
                a = (qx * sy - qy * sx) / den; u = (qx * ry - qy * rx) / den
                if a < -EPS or a > 1 + EPS or u < -EPS or u > 1 + EPS: continue
                a = max(0.0, min(1.0, a)); u = max(0.0, min(1.0, u))
                pt = (f[0][0] + rx * a, f[0][1] + ry * a)
                splits[oid][a] = pt; splits[sid][u] = pt
            cells[c].append(sid)
    for j in junctions: splits[j[2]][j[3]] = j[1]
    nodes, nid, edges, seen_e = [], {}, [], set()

    def node(p):
        k = (round(p[0] * 10), round(p[1] * 10))          # 0.1 tile: what the Lua file keeps
        if k not in nid: nid[k] = len(nodes); nodes.append((k[0] / 10, k[1] / 10))
        return nid[k]

    def edge(a, b, name, w, kind):
        fa, fb = node(a), node(b)
        if fa == fb: return
        key = (min(fa, fb), max(fa, fb))
        if key in seen_e: return
        seen_e.add(key); edges.append((fa, fb, name, w, kind))

    for sid, sg in enumerate(segs):
        prev = None
        for k in sorted(splits[sid]):
            p = splits[sid][k]
            if prev is not None and dist(prev, p) > EPS: edge(prev, p, sg[2], sg[4], sg[7])
            prev = p
    for j in junctions:
        if dist(j[0], j[1]) > EPS: edge(j[0], j[1], j[4], segs[j[2]][4], max(j[5], segs[j[2]][7]))
    return nodes, edges


def components(n, edges):
    parent = list(range(n))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b, *_ in edges: parent[find(a)] = find(b)
    size = defaultdict(int)
    for i in range(n): size[find(i)] += 1
    return sorted(size.values(), reverse=True)


def fmt(v):
    s = ("%.1f" % v)
    return s[:-2] if s.endswith(".0") else s


def chunks(items):
    out, cur, ln = [], [], 0
    for it in items:
        cur.append(it); ln += len(it) + 1
        if ln >= CHUNK: out.append(";".join(cur)); cur, ln = [], 0
    if cur: out.append(";".join(cur))
    return out


def lua_str(s):
    assert all(32 <= ord(c) < 127 for c in s), s
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    trails_path = next((p for p in TRAILS_CANDIDATES if os.path.exists(p)), None)
    paved = [(n, p, w, 0) for n, p, w in load(PAVED)]
    trails = [(n, p, w, 1) for n, p, w in load(trails_path)] if trails_path else []
    nodes, edges = build(paved + trails)
    names = sorted({e[2] for e in edges})
    index = {n: i + 1 for i, n in enumerate(names)}
    comp = components(len(nodes), edges)
    node_txt = chunks(["%s,%s" % (fmt(x), fmt(y)) for x, y in nodes])
    edge_txt = chunks(["%d,%d,%s,%d,%d" % (a + 1, b + 1, fmt(w), index[n], k) for a, b, n, w, k in edges])
    with open(OUT, "w", encoding="ascii", newline="\n") as h:
        h.write("-- SolStaticRoadsData.lua - generated by 05_TOOLS/sol_gps_roads/gen_static_roads.py; do not edit.\n")
        h.write("-- The whole map's road graph from the game's streets.xml (%d paved streets) + Sol_Trails (%d dirt roads).\n" % (len(paved), len(trails)))
        h.write("-- nodes: \"x,y;...\" (1-based order); edges: \"a,b,width,name,dirt;...\"\n")
        h.write("SolStaticRoadsData = {\n    version = 1, nodeCount = %d, edgeCount = %d,\n" % (len(nodes), len(edges)))
        h.write("    names = {\n" + "".join("        %s,\n" % lua_str(n) for n in names) + "    },\n")
        h.write("    nodes = {\n" + "".join("        %s,\n" % lua_str(c) for c in node_txt) + "    },\n")
        h.write("    edges = {\n" + "".join("        %s,\n" % lua_str(c) for c in edge_txt) + "    },\n}\n")
    print("paved %d, dirt %d (%s)" % (len(paved), len(trails), trails_path))
    print("nodes %d, edges %d, names %d, components %d, largest %s" % (len(nodes), len(edges), len(names), len(comp), comp[:6]))
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()

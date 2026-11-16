"""Minimal binary FBX reader (versions < 7500, 32-bit node records): enough to get a mesh's control points, polygons,
and its skin clusters (bone name -> vertex indices and weights). Standard library + numpy only. Read-only."""
import struct, zlib
import numpy as np


class Node:
    __slots__ = ("name", "props", "kids")

    def __init__(self, name, props, kids): self.name, self.props, self.kids = name, props, kids

    def find(self, name): return [k for k in self.kids if k.name == name]

    def first(self, name):
        for k in self.kids:
            if k.name == name: return k
        return None


_ARR = {b"f": "<f4", b"d": "<f8", b"l": "<i8", b"i": "<i4", b"b": "<i1", b"c": "<i1"}
_SCALAR = {b"Y": "<h", b"C": "<?", b"I": "<i", b"F": "<f", b"D": "<d", b"L": "<q"}


def _prop(buf, p):
    t = buf[p:p + 1]; p += 1
    if t in _SCALAR:
        fmt = _SCALAR[t]; n = struct.calcsize(fmt)
        return struct.unpack_from(fmt, buf, p)[0], p + n
    if t in _ARR:
        count, enc, clen = struct.unpack_from("<III", buf, p); p += 12
        raw = buf[p:p + clen]; p += clen
        if enc == 1: raw = zlib.decompress(raw)
        return np.frombuffer(raw, dtype=_ARR[t], count=count), p
    if t in (b"S", b"R"):
        n = struct.unpack_from("<I", buf, p)[0]; p += 4
        raw = buf[p:p + n]
        return (raw.decode("utf-8", "replace") if t == b"S" else raw), p + n
    raise ValueError("unknown FBX property type %r at %d" % (t, p))


def _node(buf, p):
    end, nprops, plen = struct.unpack_from("<III", buf, p); p += 12
    nlen = buf[p]; p += 1
    name = buf[p:p + nlen].decode("ascii", "replace"); p += nlen
    if end == 0: return None, p
    props = []
    pe = p + plen
    for _ in range(nprops):
        v, p = _prop(buf, p); props.append(v)
    p = pe
    kids = []
    while p < end:
        k, p = _node(buf, p)
        if k is None: break
        kids.append(k)
    return Node(name, props, kids), end


def read(path):
    buf = open(path, "rb").read()
    if not buf.startswith(b"Kaydara FBX Binary"): raise ValueError("not a binary FBX")
    version = struct.unpack_from("<I", buf, 23)[0]
    if version >= 7500: raise ValueError("FBX %d uses 64-bit records; not supported here" % version)
    p = 27
    kids = []
    while p < len(buf) - 160:
        k, p = _node(buf, p)
        if k is None: break
        kids.append(k)
    return Node("", [version], kids)


def meshes(root):
    """[{id, name, verts (N,3) float64, polys [list of index lists], uv (per polygon-vertex) or None}]"""
    out = []
    objs = root.first("Objects")
    for g in objs.find("Geometry"):
        v = g.first("Vertices"); pi = g.first("PolygonVertexIndex")
        if v is None or pi is None: continue
        verts = np.asarray(v.props[0], dtype=np.float64).reshape(-1, 3)
        polys, cur = [], []
        for i in np.asarray(pi.props[0]).tolist():
            if i < 0: cur.append(-i - 1); polys.append(cur); cur = []
            else: cur.append(i)
        out.append({"id": g.props[0], "name": str(g.props[1]).split("\x00")[0], "verts": verts, "polys": polys})
    return out


def skins(root):
    """{geometry id: {bone name: (indices int array, weights float array)}} from Deformer/Cluster and the connections."""
    objs = root.first("Objects")
    names, clusters, skin_ids = {}, {}, set()
    for m in objs.find("Model"): names[m.props[0]] = str(m.props[1]).split("\x00")[0]
    for d in objs.find("Deformer"):
        kind = d.props[2]
        if kind == "Skin": skin_ids.add(d.props[0])
        elif kind == "Cluster":
            idx, w = d.first("Indexes"), d.first("Weights")
            if idx is not None and w is not None:
                clusters[d.props[0]] = (np.asarray(idx.props[0]).astype(np.int64), np.asarray(w.props[0]).astype(np.float64))
    parent = {}
    for c in root.first("Connections").find("C"):
        if c.props[0] == "OO": parent.setdefault(c.props[1], []).append(c.props[2])
    child_of = {}
    for c in root.first("Connections").find("C"):
        if c.props[0] == "OO": child_of.setdefault(c.props[2], []).append(c.props[1])
    out = {}
    for sid in skin_ids:
        geos = parent.get(sid, [])
        for cid in child_of.get(sid, []):
            if cid not in clusters: continue
            bones = [names[b] for b in child_of.get(cid, []) if b in names]
            if not bones: continue
            for gid in geos: out.setdefault(gid, {})[bones[0]] = clusters[cid]
    return out

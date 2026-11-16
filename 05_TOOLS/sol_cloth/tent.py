"""The "under cloth" shape of a body region: what tight cloth stretched over it looks like.
Method: (1) the small tips are smoothed away locally, (2) the region's outer surface is replaced by its convex envelope
along one direction (cloth spans hollows, it never dips into them), (3) the change fades out at the region's borders.
Works on vertex positions only: same vertices, same triangles, same skinning. numpy + scipy."""
import numpy as np
from scipy.spatial import ConvexHull


def weld(v, tol=1e-5):
    """Vertices at the same place (UV seams) -> one id. Returns (ids per vertex, count)."""
    key = np.round(v / tol).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    return inv.reshape(-1), int(inv.max()) + 1


def neighbours(tri, ids, n):
    nb = [set() for _ in range(n)]
    for a, b, c in ids[tri]:
        if a != b: nb[a].add(b); nb[b].add(a)
        if b != c: nb[b].add(c); nb[c].add(b)
        if a != c: nb[a].add(c); nb[c].add(a)
    return [np.fromiter(s, dtype=np.int64) if s else np.zeros(0, dtype=np.int64) for s in nb]


def smooth_local(v, tri, weight, iters=20, lam=0.5):
    """Laplacian smoothing, each vertex moved by lam * weight (0..1) toward the mean of its neighbours. Seams stay closed."""
    ids, n = weld(v)
    nb = neighbours(tri, ids, n)
    p = np.zeros((n, 3)); cnt = np.zeros(n)
    np.add.at(p, ids, v); np.add.at(cnt, ids, 1); p /= cnt[:, None]
    w = np.zeros(n); np.maximum.at(w, ids, weight)
    act = np.where(w > 1e-4)[0]
    for _ in range(iters):
        q = p.copy()
        for i in act:
            if len(nb[i]): q[i] = p[i] + lam * w[i] * (p[nb[i]].mean(0) - p[i])
        p = q
    return p[ids]


def envelope(points, axis=2):
    """Upper convex envelope of points along +axis as a function of the other two coordinates: f(u, w) -> height."""
    hull = ConvexHull(points)
    eq = hull.equations                                   # n . x + d <= 0 inside
    up = eq[eq[:, axis] > 1e-6]
    others = [k for k in range(3) if k != axis]
    a = -up[:, others[0]] / up[:, axis]; b = -up[:, others[1]] / up[:, axis]; c = -up[:, 3] / up[:, axis]

    def f(u, w):
        u = np.asarray(u)[:, None]; w = np.asarray(w)[:, None]
        return (a[None, :] * u + b[None, :] * w + c[None, :]).min(axis=1)
    return f, others


def smoothstep(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


def tent(v, tri, region, direction=+1.0, axis=2, strength=1.0, border=None, tips=None, tip_radius=0.03, tip_iters=25,
         inner_gap=0.004, normals=None, relax=60, relax_depth=0.006):
    """v (N,3). region: bool mask of the vertices cloth can cover. direction: +1 the envelope faces +axis, -1 faces -axis.
    border: per-vertex 0..1 weight (1 = full effect); tips: list of points whose surroundings are smoothed first.
    Returns the new positions. Vertices outside the region are not moved."""
    out = v.copy()
    work = v.copy()
    if tips is not None and len(tips):
        d = np.min(np.stack([np.linalg.norm(v - t, axis=1) for t in tips]), axis=0)
        w = np.where(region, smoothstep(1.0 - d / tip_radius), 0.0)
        work = smooth_local(work, tri, w, iters=tip_iters)
    pts = work[region].copy()
    pts[:, axis] *= direction
    f, others = envelope(pts, axis)
    h = f(work[region][:, others[0]], work[region][:, others[1]]) * direction
    cur = work[region][:, axis]
    gap = np.zeros(region.sum())
    if normals is not None:                               # sheets that face away from the cloth sit just behind it
        facing = normals[region][:, axis] * direction
        gap = inner_gap * smoothstep((0.25 - facing) / 0.5)
    target = h - direction * gap
    moved = (target - cur) * direction > 0                # cloth only spans hollows: nothing is pushed inward
    wgt = strength * (border[region] if border is not None else 1.0)
    new = np.where(moved, cur + wgt * (target - cur), cur)
    res = work[region].copy(); res[:, axis] = new
    if relax > 0:
        # the hollow's own skin is now folded flat on the cloth plane: spread it out so the cloth is one even sheet
        # (move within the sheet, then back onto the envelope), otherwise the folds show as dark seams
        full = work.copy(); full[region] = res
        ids, n = weld(v)
        nb = neighbours(tri, ids, n)
        depth = np.zeros(len(v)); depth[region] = np.where(moved, np.abs(target - cur), 0.0) * (wgt if np.ndim(wgt) else 1.0)
        wv = smoothstep(depth / relax_depth)
        w = np.zeros(n); np.maximum.at(w, ids, wv)
        p = np.zeros((n, 3)); cnt = np.zeros(n)
        np.add.at(p, ids, full); np.add.at(cnt, ids, 1); p /= cnt[:, None]
        act = np.where(w > 1e-3)[0]
        o0, o1 = others
        for _ in range(relax):
            q = p.copy()
            for i in act:
                if len(nb[i]):
                    m = p[nb[i]].mean(0)
                    q[i, o0] = p[i, o0] + 0.5 * w[i] * (m[o0] - p[i, o0])
                    q[i, o1] = p[i, o1] + 0.5 * w[i] * (m[o1] - p[i, o1])
            hh = f(q[act, o0], q[act, o1]) * direction
            # back onto the cloth: never below the envelope's share this vertex had
            q[act, axis] = p[act, axis] + w[act] * (hh - p[act, axis]) * 1.0
            p = q
        res = p[ids][region]
    # outside the border weight the tip smoothing must fade too
    if border is not None:
        b = border[region][:, None]
        res = v[region] + np.clip(b * 4, 0, 1) * (res - v[region])
    out[region] = res
    return out

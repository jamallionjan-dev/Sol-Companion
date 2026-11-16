"""The "under cloth" shape of a body region, as a stretched membrane over the body.
The body's outer surface along one direction is a height field g(u, w) (a z-buffer of the region). Tight cloth is the
membrane h >= g that rests on the body where the body pushes it and spans every hollow in between (the obstacle problem):
    h = max(g, average of the neighbours - pull)        iterated to rest; pull > 0 lets the cloth sink a little into wide hollows
Each vertex then goes to the cloth at its own (u, w); skin that was hidden behind the outer surface stays just behind
the cloth. Same vertices, same triangles, same skinning. numpy only."""
import numpy as np


def smoothstep(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


def heightfield(v, tri, box, cell=0.002, axis=2, direction=1.0):
    """z-buffer of the triangles over box = (u0, u1, w0, w1) of the two other axes. Returns (grid, origin, cell); -inf = no body."""
    o = [k for k in range(3) if k != axis]
    nu = int(np.ceil((box[1] - box[0]) / cell)) + 1; nw = int(np.ceil((box[3] - box[2]) / cell)) + 1
    g = np.full((nw, nu), -np.inf)
    U = (v[:, o[0]] - box[0]) / cell; Wc = (v[:, o[1]] - box[2]) / cell; Z = v[:, axis] * direction
    for a, b, c in tri:
        us = (U[a], U[b], U[c]); ws = (Wc[a], Wc[b], Wc[c])
        x0, x1 = int(max(0, np.floor(min(us)))), int(min(nu - 1, np.ceil(max(us))))
        y0, y1 = int(max(0, np.floor(min(ws)))), int(min(nw - 1, np.ceil(max(ws))))
        if x0 > x1 or y0 > y1: continue
        d = (ws[1] - ws[2]) * (us[0] - us[2]) + (us[2] - us[1]) * (ws[0] - ws[2])
        if abs(d) < 1e-12: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1, dtype=np.float64), np.arange(y0, y1 + 1, dtype=np.float64))
        w0 = ((ws[1] - ws[2]) * (gx - us[2]) + (us[2] - us[1]) * (gy - ws[2])) / d
        w1 = ((ws[2] - ws[0]) * (gx - us[2]) + (us[0] - us[2]) * (gy - ws[2])) / d
        w2 = 1 - w0 - w1
        m = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        if not m.any(): continue
        z = w0 * Z[a] + w1 * Z[b] + w2 * Z[c]
        sub = g[y0:y1 + 1, x0:x1 + 1]
        np.maximum(sub, np.where(m, z, -np.inf), out=sub)
    return g


def hang(g, slope, cell):
    """Cloth hanging from the body under gravity along the grid's rows (row index grows upward): below a bulge the cloth
    does not follow the body back in, it comes down at `slope` (metres toward the body per metre down) until it meets
    the body again. slope 0 = hangs straight down, large = follows the body."""
    h = np.where(np.isfinite(g), g, -np.inf).copy()
    step = slope * cell
    for r in range(h.shape[0] - 2, -1, -1):
        h[r] = np.where(np.isfinite(g[r]), np.maximum(g[r], h[r + 1] - step), -np.inf)
    return h


def relax(g, free, pull=0.0, iters=6000, tol=1e-7, across=1.0, along=1.0):
    """Membrane over the obstacle g. free: bool grid of the cells the cloth may lift off the body (elsewhere h = g).
    Cells without body are not part of the cloth."""
    body = np.isfinite(g)
    h = np.where(body, g, 0.0)
    act = free & body
    for it in range(iters):
        s = np.zeros_like(h); n = np.zeros_like(h)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            sh = np.roll(h, (dy, dx), axis=(0, 1)); sb = np.roll(body, (dy, dx), axis=(0, 1))
            if dy == 1: sb[0, :] = False
            if dy == -1: sb[-1, :] = False
            if dx == 1: sb[:, 0] = False
            if dx == -1: sb[:, -1] = False
            k = across if dx != 0 else along                      # tension across the body vs. along it
            s += np.where(sb, sh, 0.0) * k; n += sb * k
        avg = np.where(n > 0, s / np.maximum(n, 1e-12), h) - pull
        new = np.where(act, np.maximum(g, avg), h)
        if it % 200 == 199 and np.abs(new - h).max() < tol: h = new; break
        h = new
    return np.where(body, h, -np.inf)


def blur(h, body, passes=3):
    for _ in range(passes):
        s = np.zeros_like(h); n = np.zeros_like(h)
        for dy, dx in ((0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)):
            sh = np.roll(h, (dy, dx), axis=(0, 1)); sb = np.roll(body, (dy, dx), axis=(0, 1))
            s += np.where(sb, sh, 0.0); n += sb
        h = np.where(body, s / np.maximum(n, 1), h)
    return h


def sample(grid, box, cell, u, w):
    """Bilinear sample; cells without body are skipped (nearest body value)."""
    x = np.clip((u - box[0]) / cell, 0, grid.shape[1] - 1.001); y = np.clip((w - box[2]) / cell, 0, grid.shape[0] - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
    vals = np.stack([grid[y0, x0], grid[y0, x0 + 1], grid[y0 + 1, x0], grid[y0 + 1, x0 + 1]])
    wts = np.stack([(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy])
    ok = np.isfinite(vals)
    wts = np.where(ok, wts, 0.0); vals = np.where(ok, vals, 0.0)
    tot = wts.sum(0)
    return np.where(tot > 1e-9, (vals * wts).sum(0) / np.maximum(tot, 1e-9), -np.inf)


def drape(v, tri, region, weight, box, axis=2, direction=1.0, cell=0.002, pull=0.0, soften=4, behind=0.0008, front_tol=0.003, fold_iters=300, slope=None, along=1.0, normals=None, hull=0.0):
    """v (N,3); region: vertices the cloth can cover (their triangles make the obstacle); weight 0..1 per vertex (borders).
    Returns new positions; nothing is ever moved inward."""
    o = [k for k in range(3) if k != axis]
    inreg = region[tri].all(axis=1)
    g = heightfield(v, tri[inreg], box, cell, axis, direction)
    body = np.isfinite(g)
    # the cloth is free where the region's weight is on; at the border it is pinned to the body
    wgrid = np.zeros_like(g); cnt = np.zeros_like(g)
    xi = np.clip(np.round((v[region, o[0]] - box[0]) / cell).astype(int), 0, g.shape[1] - 1)
    yi = np.clip(np.round((v[region, o[1]] - box[2]) / cell).astype(int), 0, g.shape[0] - 1)
    np.add.at(wgrid, (yi, xi), weight[region]); np.add.at(cnt, (yi, xi), 1)
    known = cnt > 0
    wgrid = np.where(known, wgrid / np.maximum(cnt, 1), 0.0)
    for _ in range(40):                                            # spread the vertex weights over the cells between them
        s = np.zeros_like(wgrid); n = np.zeros_like(wgrid)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)):
            s += np.roll(wgrid * known, (dy, dx), axis=(0, 1)); n += np.roll(known.astype(float), (dy, dx), axis=(0, 1))
        fill = (~known) & (n > 0)
        wgrid = np.where(fill, s / np.maximum(n, 1), wgrid); known = known | fill
    free = (wgrid > 0.02) & body
    g0 = g
    if hull > 0:
        # one smooth convex sheet over the whole region: what a top that is not skin-tight looks like (no hollow at all)
        from scipy.spatial import ConvexHull
        ys, xs = np.where(free)
        step = 2
        sel = (ys % step == 0) & (xs % step == 0)
        pts = np.stack([xs[sel] * cell, ys[sel] * cell, g[ys[sel], xs[sel]]], axis=1)
        eq = ConvexHull(pts).equations
        up = eq[eq[:, 2] > 1e-6]
        a, b, c = -up[:, 0] / up[:, 2], -up[:, 1] / up[:, 2], -up[:, 3] / up[:, 2]
        env = np.full(g.shape, -np.inf)
        for r in np.unique(ys):
            cx = xs[ys == r]
            env[r, cx] = (a[None, :] * (cx[:, None] * cell) + b[None, :] * (r * cell) + c[None, :]).min(axis=1)
        gh = np.where(free, g + hull * (np.maximum(env, g) - g), g)
        h = np.where(body, np.maximum(g, blur(np.where(body, gh, 0.0), body, 6)), -np.inf)
    elif slope is not None:
        gh = hang(g, slope, cell)
        g = np.where(free, gh, g)                                    # the hanging cloth is what the membrane rests on
        h = relax(g, free, pull=pull, across=1.0, along=along)
    else:
        h = relax(g, free, pull=pull, across=1.0, along=along)
    g = g0
    if soften: h = np.where(body, np.maximum(g, blur(np.where(body, h, 0.0), body, soften)), -np.inf)
    lift = np.where(body, (np.where(body, h, 0.0) - np.where(body, g, 0.0)) * smoothstep(wgrid / 0.6), 0.0)   # fade the lift toward the borders
    cloth = np.where(body, g + lift, -np.inf)
    u, w = v[region, o[0]], v[region, o[1]]
    hz = sample(cloth, box, cell, u, w); gz = sample(g, box, cell, u, w)
    z = v[region, axis] * direction
    ok = np.isfinite(hz) & np.isfinite(gz)
    depth = np.maximum(gz - z, 0.0)                                 # how far behind the outer surface this skin was
    # hidden skin: it faces away from the cloth (the underside of an overhang, the walls of a cleft) or lies well behind
    # the outer surface. The z-buffer alone is not trusted near silhouettes, where it is off by millimetres.
    facing = normals[region][:, axis] * direction if normals is not None else np.ones(len(z))
    hidden = ((facing < 0.05) | (depth > 0.02)).astype(float)
    target = np.where(hidden > 0.5, hz - behind, hz)
    new = np.where(ok, np.maximum(z, target), z)
    out = v.copy()
    out[region, axis] = new * direction
    # Skin that was hidden behind the outer surface (the underside of an overhang, the inner walls of a cleft) has no
    # place on a single cloth sheet. It is folded away to nothing: each such vertex goes to the average of its
    # neighbours, the visible ones held still, so the pocket closes into the line where its two visible rims meet.
    import tent as _T
    hid_full = np.zeros(len(v), dtype=bool)
    hid_full[np.where(region)[0][(hidden > 0.5) & ok]] = True
    if hid_full.any() and fold_iters > 0:
        ids, n = _T.weld(v)
        nb = _T.neighbours(tri, ids, n)
        p = np.zeros((n, 3)); cnt = np.zeros(n)
        np.add.at(p, ids, out); np.add.at(cnt, ids, 1); p /= cnt[:, None]
        hw = np.zeros(n, dtype=bool); hw[ids[hid_full]] = True
        vis = np.zeros(n, dtype=bool); vis[ids[~hid_full]] = True
        act = np.where(hw & ~vis)[0]
        for it in range(fold_iters):
            q = p.copy()
            for i in act:
                if len(nb[i]): q[i] = p[nb[i]].mean(0)
            p = q
        cz = sample(cloth, box, cell, p[act, o[0]], p[act, o[1]])    # and it ends up behind the cloth, never through it
        okc = np.isfinite(cz)
        lim = (cz[okc] - behind) * direction
        cur_ = p[act[okc], axis]
        p[act[okc], axis] = np.where((cur_ - lim) * direction > 0, lim, cur_)
        moved_ids = np.zeros(n, dtype=bool); moved_ids[act] = True
        sel = moved_ids[ids]
        out[sel] = p[ids[sel]]
    return out, {"g": g, "cloth": cloth, "free": free, "hidden": hid_full}

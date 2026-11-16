"""Chest "under cloth" body shape, third method: the cloth is computed AROUND the torso (rays from the torso's vertical
axis), not from the front only, so the sides of the bust are measured as well as its front.
  g(angle, height)  the body's outer radius along each ray (a z-buffer in cylinder coordinates)
  across            every horizontal slice is replaced by its convex outline: cloth spans from one side to the other
  down              below a bulge the cloth comes back to the body at a fixed slope instead of following it in
  smooth            the sheet is blurred a little and never goes inside the body
Each vertex then moves out along its own ray onto the sheet; skin hidden behind the outer surface is folded away just
behind the sheet and shaded like it. usage: python chest_preview3.py -> out/chest3_L.png. Nothing in the game is touched."""
import os, sys
import numpy as np
from scipy.spatial import ConvexHull
import render as R, tent as T, membrane as M
from chest_preview import load
HERE = os.path.dirname(os.path.abspath(__file__))
RREF = 0.15            # metres of grid per radian
CELL = 0.002


def to_cyl(v, zc):
    x, z = v[:, 0], v[:, 2] - zc
    r = np.hypot(x, z); th = np.arctan2(x, z)                 # 0 = straight ahead
    return np.stack([th * RREF, v[:, 1], r], axis=1)


def from_cyl(c, zc):
    th = c[:, 0] / RREF
    return np.stack([c[:, 2] * np.sin(th), c[:, 1], zc + c[:, 2] * np.cos(th)], axis=1)


def slice_hull(g, box, strength=1.0):
    """Per row: the convex outline of the slice, as radius per angle."""
    out = g.copy()
    th = (box[0] + np.arange(g.shape[1]) * CELL) / RREF
    d = np.stack([np.sin(th), np.cos(th)], axis=1)
    for r in range(g.shape[0]):
        ok = np.isfinite(g[r])
        if ok.sum() < 8: continue
        pts = np.vstack([d[ok] * g[r, ok][:, None], [[0.0, -0.02]]])
        try: eq = ConvexHull(pts).equations
        except Exception: continue
        nd = eq[:, :2] @ d.T                                  # (edges, angles)
        with np.errstate(divide="ignore", invalid="ignore"):
            cand = np.where(nd > 1e-6, -eq[:, 2:3] / nd, np.inf)
        hull = cand.min(axis=0)
        out[r, ok] = g[r, ok] + strength * (np.maximum(hull[ok], g[r, ok]) - g[r, ok])
    return out


def chest(v, tri, names, W, slope=0.6, across=1.0, y0=0.98, y1=1.38, fade=0.05, tip_radius=0.05, blur=8, span=1.75):
    torso = np.zeros(len(v))
    for b in ("Bip01_Spine1", "Bip01_Spine", "Bip01_L_Clavicle", "Bip01_R_Clavicle", "Bip01_Pelvis"):
        if b in names: torso += W[:, names.index(b)]
    band = (torso > 0.5) & (v[:, 1] > y0 - 0.03) & (v[:, 1] < y1 + 0.03)
    zc = float(np.median(v[band, 2])) - 0.02
    c = to_cyl(v, zc)
    ang = np.abs(c[:, 0] / RREF)
    region = band & (ang < span) & (np.abs(v[:, 0]) < 0.21)
    weight = (region * T.smoothstep((v[:, 1] - y0) / fade) * T.smoothstep((y1 - v[:, 1]) / fade) * T.smoothstep((span - 0.15 - ang) / 0.35))
    # tips
    tips = []
    for side in (-1, 1):
        s = region & (v[:, 0] * side > 0.03) & (ang < 1.2)
        tips.append(v[np.where(s)[0][v[s, 2].argmax()]])            # the tip: the point furthest forward
    dd = np.min(np.stack([np.linalg.norm(v - t, axis=1) for t in tips]), axis=0)
    work = T.smooth_local(v, tri, np.where(region, T.smoothstep(1.0 - dd / tip_radius), 0.0), iters=70) if tip_radius > 0 else v.copy()
    cw = to_cyl(work, zc)
    box = (-span * RREF - 0.01, span * RREF + 0.01, y0 - 0.04, y1 + 0.04)
    inreg = region[tri].all(axis=1)
    # triangles that wrap across the back are not in the region (|angle| < span), so angles are continuous here
    g = M.heightfield(cw, tri[inreg], box, CELL, axis=2, direction=1.0)
    body = np.isfinite(g)
    h = slice_hull(g, box, across)
    h = np.where(body, M.hang(h, slope, CELL), -np.inf)
    hb = M.blur(np.where(body, h, 0.0), body, blur)
    h = np.where(body, np.maximum(g, hb), -np.inf)
    # fade to the body at the region's borders
    wg = np.zeros_like(g); cnt = np.zeros_like(g)
    xi = np.clip(np.round((cw[region, 0] - box[0]) / CELL).astype(int), 0, g.shape[1] - 1)
    yi = np.clip(np.round((cw[region, 1] - box[2]) / CELL).astype(int), 0, g.shape[0] - 1)
    np.add.at(wg, (yi, xi), weight[region]); np.add.at(cnt, (yi, xi), 1)
    known = cnt > 0; wg = np.where(known, wg / np.maximum(cnt, 1), 0.0)
    for _ in range(60):
        s = np.zeros_like(wg); n = np.zeros_like(wg)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)):
            s += np.roll(wg * known, (dy, dx), axis=(0, 1)); n += np.roll(known.astype(float), (dy, dx), axis=(0, 1))
        fill = (~known) & (n > 0); wg = np.where(fill, s / np.maximum(n, 1), wg); known = known | fill
    cloth = np.where(body, g + (np.where(body, h, 0) - np.where(body, g, 0)) * T.smoothstep(wg / 0.7), -np.inf)
    # vertices
    idx = np.where(region)[0]
    u, w_, r = cw[idx, 0], cw[idx, 1], cw[idx, 2]
    hz = M.sample(cloth, box, CELL, u, w_); gz = M.sample(g, box, CELL, u, w_)
    ok = np.isfinite(hz) & np.isfinite(gz)
    nrm0 = R.vertex_normals(work, tri)
    th = u / RREF
    radial = np.stack([np.sin(th), np.zeros(len(th)), np.cos(th)], axis=1)
    facing = (nrm0[idx] * radial).sum(1)
    hidden = ok & ((facing < 0.05) | (gz - r > 0.02))
    newr = np.where(ok & ~hidden, np.maximum(r, hz), r)
    cn = cw.copy(); cn[idx, 2] = newr
    out = from_cyl(cn, zc)
    # fold the hidden skin away between its visible rims, then put it a hair behind the sheet
    hid = np.zeros(len(v), dtype=bool); hid[idx[hidden]] = True
    ids, n = T.weld(v); nb = T.neighbours(tri, ids, n)
    p = np.zeros((n, 3)); cnt2 = np.zeros(n); np.add.at(p, ids, out); np.add.at(cnt2, ids, 1); p /= cnt2[:, None]
    hw = np.zeros(n, dtype=bool); hw[ids[hid]] = True
    vis = np.zeros(n, dtype=bool); vis[ids[~hid]] = True
    act = np.where(hw & ~vis)[0]
    if len(act):
        deg = max(len(nb[i]) for i in act); ix = np.zeros((len(act), deg), dtype=np.int64); mk = np.zeros((len(act), deg))
        for k, i in enumerate(act): ix[k, :len(nb[i])] = nb[i]; mk[k, :len(nb[i])] = 1
        for _ in range(400): p[act] = (p[ix] * mk[:, :, None]).sum(1) / np.maximum(mk.sum(1, keepdims=True), 1)
        pc = to_cyl(p[act], zc)
        cz = M.sample(cloth, box, CELL, pc[:, 0], pc[:, 1]); okc = np.isfinite(cz)
        pc[okc, 2] = cz[okc] - 0.001
        p[act] = from_cyl(pc, zc)
        sel = np.zeros(n, dtype=bool); sel[act] = True; s2 = sel[ids]
        out[s2] = p[ids[s2]]
    # normals: the sheet's own where the skin was lifted or folded away
    P = np.zeros(cloth.shape + (3,))
    thg = (box[0] + np.arange(cloth.shape[1]) * CELL) / RREF
    cl = np.where(body, cloth, np.nan)
    P[..., 0] = cl * np.sin(thg)[None, :]; P[..., 1] = (box[2] + np.arange(cloth.shape[0]) * CELL)[:, None]; P[..., 2] = cl * np.cos(thg)[None, :]
    dth = np.gradient(P, axis=1); dy = np.gradient(P, axis=0)
    nn = np.cross(dth, dy); nn /= np.maximum(np.linalg.norm(nn, axis=2, keepdims=True), 1e-12)
    nn = np.where(np.isfinite(nn), nn, 0.0)
    for _ in range(3):                                           # a little smoothing of the normal field
        acc = np.zeros_like(nn); cntn = np.zeros(cloth.shape)
        for dy_, dx_ in ((0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)):
            acc += np.roll(nn, (dy_, dx_), axis=(0, 1)); cntn += 1
        nn = acc / cntn[..., None]
    oc = to_cyl(out, zc)
    sn = np.stack([M.sample(np.where(body, nn[..., k], -np.inf), box, CELL, oc[:, 0], oc[:, 1]) for k in range(3)], axis=1)
    sn = np.where(np.isfinite(sn), sn, 0.0)
    ln = np.linalg.norm(sn, axis=1, keepdims=True)
    base = R.vertex_normals(out, tri)
    lift = np.linalg.norm(out - work, axis=1)
    k = np.maximum(T.smoothstep(lift / 0.004), hid.astype(float)) * region * (ln[:, 0] > 0.5)
    nrm = base * (1 - k[:, None]) + (sn / np.maximum(ln, 1e-9)) * k[:, None]
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    stats = {"moved": int((lift > 1e-4).sum()), "max_out_mm": float(lift.max() * 1000), "hidden": int(hid.sum()),
             "inward_mm": float(max(0.0, (r - newr).max()) * 1000)}
    return out, nrm, stats


if __name__ == "__main__":
    v, tri, names, W = load("")
    variants = [("painted top today", v, None)]
    for label, kw in (("under cloth 1", dict(slope=0.9)), ("under cloth 2", dict(slope=0.6)), ("under cloth 3", dict(slope=0.4, y0=0.95))):
        nv, nrm, st = chest(v, tri, names, W, **kw)
        print(label, st)
        variants.append((label, nv, nrm))
    skin, cloth = np.array([0.86, 0.72, 0.64]), np.array([0.36, 0.50, 0.72])
    tshirt = (v[:, 1] > 0.94) & (v[:, 1] < 1.37) & (np.abs(v[:, 0]) < 0.24)
    col = np.where(tshirt[:, None], cloth, skin)
    ims, labels = [], []
    for name, yaw, pitch in (("front", 0, 0), ("three-quarter", 40, 0), ("side", 90, 0), ("from below", 25, -35), ("from above", 20, 30)):
        band = v[(v[:, 1] > 0.95) & (v[:, 1] < 1.50) & (np.abs(v[:, 0]) < 0.30)] @ R.view_matrix(yaw, pitch).T
        cx, cy = (band[:, 0].min() + band[:, 0].max()) / 2, (band[:, 1].min() + band[:, 1].max()) / 2
        vb = (cx - 0.30, cx + 0.30, cy - 0.275, cy + 0.275)
        for label, nv, nrm in variants:
            ims.append(R.render(nv, tri, yaw=yaw, pitch=pitch, box=vb, size=(300, 275), vcolor=col, normals=nrm))
            labels.append("%s / %s" % (name, label))
    out = os.path.join(HERE, "out", "chest3_L.png")
    R.sheet(ims, labels, cols=4).save(out)
    print("wrote", out)

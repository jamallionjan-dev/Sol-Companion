"""Chest under cloth, the result Jamal accepted (chest_preview4, "held" + partial bridge), with two small refinements he
asked for and nothing else: the place of the tips, and the roundness of the mound.
  tips       instead of flattening the patch (which leaves a flat spot), the patch is put on the sphere that fits the
             skin AROUND it, so the mound keeps its own curvature through that place
  roundness  Taubin smoothing (lambda/mu, "smoothing without shrinkage", Taubin 1995): small lumps go, size and shape stay
usage: python chest_preview5.py -> out/chest5_L.png. Nothing in the game or the mod is touched."""
import os
import numpy as np
import render as R, tent as T
from chest_preview import load
import chest_preview3 as C3
from chest_preview4 import support
HERE = os.path.dirname(os.path.abspath(__file__))


def chest_band(v, names, W):
    torso = np.zeros(len(v))
    for b in ("Bip01_Spine1", "Bip01_Spine"):
        if b in names: torso += W[:, names.index(b)]
    return (torso > 0.5) & (v[:, 1] > 1.0) & (v[:, 1] < 1.38)


def find_tips(v, band):
    out = []
    for side in (-1, 1):
        s = band & (v[:, 0] * side > 0.03)
        out.append(v[np.where(s)[0][v[s, 2].argmax()]].copy())
    return out


def round_tips(v, band, tips, inner=0.034, ring=(0.038, 0.07)):
    out = v.copy()
    for t in tips:
        d = np.linalg.norm(v - t, axis=1)
        side = band & (v[:, 0] * np.sign(t[0]) > 0.0)
        rs = side & (d > ring[0]) & (d < ring[1]) & (v[:, 2] > t[2] - 0.05)
        P = v[rs]
        A = np.hstack([2 * P, np.ones((len(P), 1))]); b = (P ** 2).sum(1)
        sol = np.linalg.lstsq(A, b, rcond=None)[0]
        c = sol[:3]; rad = np.sqrt(sol[3] + (c ** 2).sum())
        sel = side & (d < inner + 0.012)
        rel = v[sel] - c
        target = c + rel / np.linalg.norm(rel, axis=1, keepdims=True) * rad
        w = T.smoothstep((inner + 0.012 - d[sel]) / 0.016)[:, None]
        out[sel] = v[sel] + w * (target - v[sel])
    return out


def taubin(v, tri, weight, passes=8, lam=0.5, mu=-0.53):
    ids, n = T.weld(v); nb = T.neighbours(tri, ids, n)
    p = np.zeros((n, 3)); cnt = np.zeros(n); np.add.at(p, ids, v); np.add.at(cnt, ids, 1); p /= cnt[:, None]
    w = np.zeros(n); np.maximum.at(w, ids, weight)
    act = np.where(w > 1e-3)[0]
    deg = max(len(nb[i]) for i in act); ix = np.zeros((len(act), deg), dtype=np.int64); mk = np.zeros((len(act), deg))
    for k, i in enumerate(act): ix[k, :len(nb[i])] = nb[i]; mk[k, :len(nb[i])] = 1
    den = np.maximum(mk.sum(1, keepdims=True), 1); wa = w[act][:, None]
    for _ in range(passes):
        for f in (lam, mu):
            mean = (p[ix] * mk[:, :, None]).sum(1) / den
            p[act] = p[act] + f * wa * (mean - p[act])
    return p[ids]


def build(v, tri, names, W, refine, across, slope):
    sv = support(v, tri, names, W)
    band = chest_band(sv, names, W)
    if not refine:
        return C3.chest(sv, tri, names, W, across=across, slope=slope, blur=10)
    tips = find_tips(sv, band)
    rv = round_tips(sv, band, tips)
    dmin = np.min(np.stack([np.linalg.norm((sv - t) * np.array([1, 1, 0.6]), axis=1) for t in tips]), axis=0)
    wm = T.smoothstep(1.0 - dmin / 0.13) * band
    rv = taubin(rv, tri, wm, passes=8)
    return C3.chest(rv, tri, names, W, across=across, slope=slope, blur=10, tip_radius=0.0)


if __name__ == "__main__":
    v, tri, names, W = load("")
    variants = [("painted top today", v, None)]
    for label, refine, across, slope in (("last result (accepted)", False, 0.45, 1.6), ("refined, light bridge", True, 0.45, 1.6), ("refined, more bridge", True, 0.75, 1.2)):
        nv, nrm, st = build(v, tri, names, W, refine, across, slope)
        print(label, st)
        variants.append((label, nv, nrm))
    a, b = variants[1][1], variants[2][1]
    print("refined vs accepted: max difference %.1f mm, vertices changed more than 1 mm: %d" % (np.linalg.norm(a - b, axis=1).max() * 1000, (np.linalg.norm(a - b, axis=1) > 0.001).sum()))
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
    out = os.path.join(HERE, "out", "chest5_L.png")
    R.sheet(ims, labels, cols=4).save(out)
    print("wrote", out)

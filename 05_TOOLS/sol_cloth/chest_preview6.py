"""The accepted chest shape (chest_preview4 column "held, light bridge") with ONE local change: the tip patch, inside a
small radius, follows the mound's own curvature. No overall smoothing, nothing else moved (the script proves it by
measuring where the two shapes differ). usage: python chest_preview6.py -> out/chest6_L.png"""
import os
import numpy as np
import render as R, tent as T
from chest_preview import load
import chest_preview3 as C3
from chest_preview4 import support
from chest_preview5 import chest_band, find_tips
HERE = os.path.dirname(os.path.abspath(__file__))


def tip_only(acc, base, band, tips, radius=0.03):
    """acc: the accepted shape. Inside `radius` of each tip the surface is put on the sphere fitted to the accepted
    skin just around it; the change fades to zero at the radius."""
    out = acc.copy()
    for t in tips:
        d0 = np.linalg.norm(base - t, axis=1)                       # distances measured on the body before the cloth step
        side = band & (base[:, 0] * np.sign(t[0]) > 0.0)
        ring = side & (d0 > radius) & (d0 < radius + 0.03) & (base[:, 2] > t[2] - 0.05)
        P = acc[ring]
        A = np.hstack([2 * P, np.ones((len(P), 1))]); b = (P ** 2).sum(1)
        sol = np.linalg.lstsq(A, b, rcond=None)[0]
        c = sol[:3]; rad = np.sqrt(sol[3] + (c ** 2).sum())
        sel = side & (d0 < radius)
        rel = acc[sel] - c
        target = c + rel / np.linalg.norm(rel, axis=1, keepdims=True) * rad
        w = T.smoothstep((radius - d0[sel]) / (radius * 0.5))[:, None]
        out[sel] = acc[sel] + w * (target - acc[sel])
    return out


if __name__ == "__main__":
    v, tri, names, W = load("")
    sv = support(v, tri, names, W)
    band = chest_band(sv, names, W)
    tips = find_tips(sv, band)
    acc, nrm, st = C3.chest(sv, tri, names, W, across=0.45, slope=1.6, blur=10)
    new = tip_only(acc, sv, band, tips)
    diff = np.linalg.norm(new - acc, axis=1)
    far = np.min(np.stack([np.linalg.norm(sv - t, axis=1) for t in tips]), axis=0) > 0.03
    print("accepted vs tip-only: changed vertices %d, max change %.1f mm, changed outside the 3 cm tip patches: %d" % ((diff > 1e-5).sum(), diff.max() * 1000, (diff[far] > 1e-6).sum()))
    variants = [("painted top today", v, None), ("accepted", acc, nrm), ("accepted + tip patch only", new, nrm)]
    skin, cloth = np.array([0.86, 0.72, 0.64]), np.array([0.36, 0.50, 0.72])
    tshirt = (v[:, 1] > 0.94) & (v[:, 1] < 1.37) & (np.abs(v[:, 0]) < 0.24)
    col = np.where(tshirt[:, None], cloth, skin)
    ims, labels = [], []
    for name, yaw, pitch in (("front", 0, 0), ("three-quarter", 40, 0), ("side", 90, 0), ("from below", 25, -35), ("from above", 20, 30)):
        bandp = v[(v[:, 1] > 0.95) & (v[:, 1] < 1.50) & (np.abs(v[:, 0]) < 0.30)] @ R.view_matrix(yaw, pitch).T
        cx, cy = (bandp[:, 0].min() + bandp[:, 0].max()) / 2, (bandp[:, 1].min() + bandp[:, 1].max()) / 2
        vb = (cx - 0.30, cx + 0.30, cy - 0.275, cy + 0.275)
        for label, nv, nr in variants:
            ims.append(R.render(nv, tri, yaw=yaw, pitch=pitch, box=vb, size=(380, 350), vcolor=col, normals=nr))
            labels.append("%s / %s" % (name, label))
    out = os.path.join(HERE, "out", "chest6_L.png")
    R.sheet(ims, labels, cols=3).save(out)
    print("wrote", out)

"""Chest under cloth, fourth method: what clothed-body presets do in practice (Skyrim BodySlide outfit presets, the Daz
"Clothing Breast Helper" morphs): the bust keeps its two mounds; the tips are collapsed, the bust is lifted and held a
little closer to the chest and together (as cloth and a bra do), and the cloth is bridged only PARTLY across the valley
and under the bust. Not a tent over everything.
usage: python chest_preview4.py -> out/chest4_L.png. Nothing in the game or the mod is touched."""
import os
import numpy as np
import render as R, tent as T
from chest_preview import load
import chest_preview3 as C3
HERE = os.path.dirname(os.path.abspath(__file__))


def support(v, tri, names, W, lift=0.30, press=0.12, together=0.006, radius=0.135, low=0.75):
    """The bust as held by cloth: per side, a smooth field around the mound.
    lift: how much the mound tilts up; low: how much of the hang below the apex is kept (1 = all);
    press: how much it is pressed toward the chest; together: metres each side moves to the middle."""
    torso = np.zeros(len(v))
    for b in ("Bip01_Spine1", "Bip01_Spine"):
        if b in names: torso += W[:, names.index(b)]
    band = (torso > 0.5) & (v[:, 1] > 1.0) & (v[:, 1] < 1.38)
    wall = float(np.median(v[band & (np.abs(v[:, 0]) < 0.03) & (v[:, 2] > np.median(v[band, 2])), 2]))   # the breastbone
    out = v.copy()
    for side in (-1, 1):
        s = band & (v[:, 0] * side > 0.03)
        apex = v[np.where(s)[0][v[s, 2].argmax()]]
        base = np.array([apex[0], apex[1] + 0.01, wall - 0.02])
        d = np.linalg.norm((v - apex) * np.array([1.0, 1.0, 0.6]), axis=1)
        w = T.smoothstep(1.0 - d / radius) * band * (v[:, 0] * side > -0.01)
        rel = v - base
        proj = np.maximum(rel[:, 2], 0.0)                         # how far the point stands out from the chest
        new = rel.copy()
        new[:, 2] = rel[:, 2] * (1.0 - press)
        below = np.minimum(rel[:, 1], 0.0)
        new[:, 1] = np.maximum(rel[:, 1], 0.0) + below * low + lift * proj * 0.5
        new[:, 0] = rel[:, 0] - side * together * np.clip(proj / 0.06, 0, 1)
        out += (new - rel) * w[:, None]
    return out


if __name__ == "__main__":
    v, tri, names, W = load("")
    variants = [("painted top today", v, None)]
    for label, sk, ck in (("held, light bridge", dict(), dict(across=0.45, slope=1.6, blur=10)),
                          ("held, more bridge", dict(), dict(across=0.75, slope=1.2, blur=10)),
                          ("held more, bridge", dict(lift=0.42, press=0.18, low=0.6), dict(across=0.6, slope=1.4, blur=10))):
        sv = support(v, tri, names, W, **sk)
        nv, nrm, st = C3.chest(sv, tri, names, W, **ck)
        print(label, st, "support moved max %.1f mm" % (np.linalg.norm(sv - v, axis=1).max() * 1000))
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
    out = os.path.join(HERE, "out", "chest4_L.png")
    R.sheet(ims, labels, cols=4).save(out)
    print("wrote", out)

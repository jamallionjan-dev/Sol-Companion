"""Offline look at the chest "under cloth" body shape (mesh-space method, undercloth.py) on Sol's body.
usage: python chest_preview2.py [size: "" L | M | S] -> out/chest2_<size>.png. Nothing in the game or the mod is touched."""
import os, sys
import numpy as np
import render as R, tent as T, undercloth as U
from chest_preview import load
HERE = os.path.dirname(os.path.abspath(__file__))


def chest(v, tri, names, W, iters, y0=0.98, y1=1.38, fade=0.05, tip_radius=0.042):
    torso = np.zeros(len(v))
    for b in ("Bip01_Spine1", "Bip01_Spine", "Bip01_L_Clavicle", "Bip01_R_Clavicle", "Bip01_Pelvis"):
        if b in names: torso += W[:, names.index(b)]
    band = (torso > 0.5) & (v[:, 1] > y0) & (v[:, 1] < y1) & (np.abs(v[:, 0]) < 0.20)
    zmid = np.median(v[band, 2])
    weight = (band * T.smoothstep((v[:, 1] - y0) / fade) * T.smoothstep((y1 - v[:, 1]) / fade)
              * T.smoothstep((0.175 - np.abs(v[:, 0])) / 0.03) * T.smoothstep((v[:, 2] - zmid + 0.01) / 0.03))
    front = band & (v[:, 2] > zmid)
    tips = []
    for side in (-1, 1):
        s = front & (v[:, 0] * side > 0.03)
        tips.append(v[np.where(s)[0][v[s, 2].argmax()]])
    d = np.min(np.stack([np.linalg.norm(v - t, axis=1) for t in tips]), axis=0)
    work = T.smooth_local(v, tri, np.where(front, T.smoothstep(1.0 - d / tip_radius), 0.0) * (weight > 0.5), iters=45)
    out = U.relax_outward(work, tri, weight, iters=iters, normals=R.vertex_normals(work, tri))
    return out


if __name__ == "__main__":
    size = sys.argv[1] if len(sys.argv) > 1 else ""
    v, tri, names, W = load("" if size in ("", "L") else size)
    variants = [("painted top today", v)]
    for label, it in (("under cloth, light", 60), ("under cloth, medium", 250), ("under cloth, full", 1200)):
        nv = chest(v, tri, names, W, it)
        mv = np.linalg.norm(nv - v, axis=1)
        print("%-22s moved %d verts, max %.1f mm" % (label, (mv > 1e-4).sum(), mv.max() * 1000))
        variants.append((label, nv))
    skin, cloth = np.array([0.86, 0.72, 0.64]), np.array([0.36, 0.50, 0.72])
    tshirt = (v[:, 1] > 0.98) & (v[:, 1] < 1.37) & (np.abs(v[:, 0]) < 0.24)
    col = np.where(tshirt[:, None], cloth, skin)
    ims, labels = [], []
    for name, yaw, pitch in (("front", 0, 0), ("three-quarter", 40, 0), ("side", 90, 0), ("from below", 25, -35)):
        band = v[(v[:, 1] > 0.95) & (v[:, 1] < 1.50) & (np.abs(v[:, 0]) < 0.30)] @ R.view_matrix(yaw, pitch).T
        cx, cy = (band[:, 0].min() + band[:, 0].max()) / 2, (band[:, 1].min() + band[:, 1].max()) / 2
        vb = (cx - 0.30, cx + 0.30, cy - 0.275, cy + 0.275)
        for label, nv in variants:
            ims.append(R.render(nv, tri, yaw=yaw, pitch=pitch, box=vb, size=(300, 275), vcolor=col))
            labels.append("%s / %s" % (name, label))
    out = os.path.join(HERE, "out", "chest2_%s.png" % (size or "L"))
    R.sheet(ims, labels, cols=4).save(out)
    print("wrote", out)

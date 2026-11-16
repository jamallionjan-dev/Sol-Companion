"""Offline look at the chest "under cloth" shape on Sol's body (size L): renders the painted top of today next to the
cloth shape, from several views. usage: python chest_preview.py -> out/chest_L.png. Nothing in the game or the mod is touched."""
import os
import numpy as np
import fbx_read as F, render as R, tent as T, membrane as M
HERE = os.path.dirname(os.path.abspath(__file__))
BODY = os.path.join(HERE, "..", "..", "07_TEST", "SOL_LAB", "profile", "Zomboid", "mods", "Sol_LAB", "42", "media", "models_X", "Skinned", "localplayervsgirl", "FemaleBody%s.fbx")


def load(size=""):
    r = F.read(BODY % size)
    m = F.meshes(r)[0]
    v = m["verts"] * np.array([1, -1, -1.0])
    scale = 1.65 / (v[:, 1].max() - v[:, 1].min())
    v = v * scale; v[:, 1] -= v[:, 1].min()               # metres, head up, front = +z
    tri = R.triangles(m["polys"])
    sk = list(F.skins(r).values())[0]
    names = sorted(sk)
    W = np.zeros((len(v), len(names)))
    for j, b in enumerate(names):
        i, w = sk[b]; W[i, j] = w
    return v, tri, names, W


def chest(v, tri, names, W, y0=1.00, y1=1.37, fade=0.04, pull=0.0, tip_radius=0.042, slope=None, along=1.0, soften=10, hull=0.0):
    torso = np.zeros(len(v))
    for b in ("Bip01_Spine1", "Bip01_Spine", "Bip01_L_Clavicle", "Bip01_R_Clavicle", "Bip01_Pelvis"):
        if b in names: torso += W[:, names.index(b)]
    band = (torso > 0.5) & (v[:, 1] > y0 - 0.02) & (v[:, 1] < y1 + 0.02) & (np.abs(v[:, 0]) < 0.19)
    zmid = np.median(v[band, 2])
    region = band & (v[:, 2] > zmid - 0.01)
    weight = (T.smoothstep((v[:, 1] - y0) / fade) * T.smoothstep((y1 - v[:, 1]) / fade)
              * T.smoothstep((0.165 - np.abs(v[:, 0])) / 0.03) * T.smoothstep((v[:, 2] - zmid) / 0.03))
    tips = []
    for side in (-1, 1):
        s = region & (v[:, 0] * side > 0.03)
        tips.append(v[np.where(s)[0][v[s, 2].argmax()]])
    d = np.min(np.stack([np.linalg.norm(v - t, axis=1) for t in tips]), axis=0)
    work = T.smooth_local(v, tri, np.where(region, T.smoothstep(1.0 - d / tip_radius), 0.0), iters=45)
    box = (-0.20, 0.20, y0 - 0.03, y1 + 0.03)
    out, info = M.drape(work, tri, region, weight, box, axis=2, direction=1.0, pull=pull, slope=slope, along=along, soften=soften, normals=R.vertex_normals(work, tri), hull=hull)
    # shading: where the cloth lifted off the skin (and for the skin folded away behind it) the surface normal is the
    # cloth's own, taken from the cloth height field, so the folded skin cannot show as a seam
    cl = info["cloth"]; cell = 0.002
    cz = np.where(np.isfinite(cl), cl, np.nan)
    gy, gx = np.gradient(cz, cell)
    nx = M.sample(np.where(np.isfinite(gx), -gx, -np.inf), box, cell, out[:, 0], out[:, 1])
    ny = M.sample(np.where(np.isfinite(gy), -gy, -np.inf), box, cell, out[:, 0], out[:, 1])
    cn = np.stack([np.where(np.isfinite(nx), nx, 0), np.where(np.isfinite(ny), ny, 0), np.ones(len(out))], axis=1)
    cn /= np.linalg.norm(cn, axis=1, keepdims=True)
    base = R.vertex_normals(work, tri)
    lift = np.abs(out[:, 2] - work[:, 2])
    k = np.maximum(T.smoothstep(lift / 0.004), info["hidden"].astype(float)) * region
    nrm = base * (1 - k[:, None]) + cn * k[:, None]
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    chest.normals = nrm
    return out, region, weight, tips


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    v, tri, names, W = load("")
    variants = [("painted top today", v, None)]
    for label, kw in (("sheet, short", dict(hull=1.0, y0=1.05)), ("sheet, to the waist", dict(hull=1.0, y0=0.98)), ("hanging cloth", dict(slope=0.6, along=0.5))):
        nv, region, weight, tips = chest(v, tri, names, W, **kw)
        variants.append((label, nv, chest.normals))
        moved = nv[:, 2] - v[:, 2]
        print("%-18s moved %d verts, max out %.1f mm, max in %.1f mm" % (label, (np.abs(moved) > 1e-4).sum(), moved.max() * 1000, -moved.min() * 1000))
    skin, cloth = np.array([0.86, 0.72, 0.64]), np.array([0.36, 0.50, 0.72])
    views = [("front", 0, 0), ("three-quarter", 40, 0), ("side", 90, 0), ("from below", 25, -35)]
    ims, labels = [], []
    for name, yaw, pitch in views:
        band = v[(v[:, 1] > 0.95) & (v[:, 1] < 1.50) & (np.abs(v[:, 0]) < 0.30)] @ R.view_matrix(yaw, pitch).T
        cx, cy = (band[:, 0].min() + band[:, 0].max()) / 2, (band[:, 1].min() + band[:, 1].max()) / 2
        vb = (cx - 0.30, cx + 0.30, cy - 0.275, cy + 0.275)
        for label, nv, nrm in variants:
            tshirt = (v[:, 1] > 0.98) & (v[:, 1] < 1.37) & (np.abs(v[:, 0]) < 0.24)
            col = np.where(tshirt[:, None], cloth, skin)
            ims.append(R.render(nv, tri, yaw=yaw, pitch=pitch, box=vb, size=(300, 275), vcolor=col, normals=nrm))
            labels.append("%s / %s" % (name, label))
    R.sheet(ims, labels, cols=4).save(os.path.join(HERE, "out", "chest_L.png"))
    print("wrote out/chest_L.png")

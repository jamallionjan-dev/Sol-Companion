"""The body's shape UNDER cloth, computed on the mesh itself (no projection, no hidden-surface guessing).
Jamal 2026-11-16, with a reference picture: under a top the chest must read as one soft, even mound - no tips, no cleft
between, no crease underneath, a gentle run-out to the belly. The bare body is not touched.
Method: (1) the tips are smoothed away locally; (2) the region is relaxed like a stretched sheet (each vertex toward the
mean of its neighbours) but a vertex may never end up inside the original body: after every step it is put back on or
above its own original surface. Hollows fill, bulges stay, folds open out by themselves. More steps = more filled.
Same vertices, same triangles, same skinning."""
import numpy as np
import tent as T


def relax_outward(v, tri, weight, iters=300, lam=0.6, normals=None):
    """weight 0..1 per vertex (0 = fixed). Returns new positions."""
    ids, n = T.weld(v)
    nb = T.neighbours(tri, ids, n)
    def welded(a):
        out = np.zeros((n,) + a.shape[1:]); cnt = np.zeros(n)
        np.add.at(out, ids, a); np.add.at(cnt, ids, 1)
        return out / cnt.reshape((-1,) + (1,) * (a.ndim - 1))
    p0 = welded(v)
    n0 = welded(normals); n0 /= np.maximum(np.linalg.norm(n0, axis=1, keepdims=True), 1e-12)
    w = np.zeros(n); np.maximum.at(w, ids, weight)
    act = np.where(w > 1e-3)[0]
    # neighbour lists as a padded matrix for speed
    deg = max(len(nb[i]) for i in act) if len(act) else 1
    idx = np.zeros((len(act), deg), dtype=np.int64); msk = np.zeros((len(act), deg))
    for r, i in enumerate(act):
        k = len(nb[i]); idx[r, :k] = nb[i]; msk[r, :k] = 1
    cntn = np.maximum(msk.sum(1, keepdims=True), 1)
    p = p0.copy()
    wa = w[act][:, None]
    for _ in range(iters):
        mean = (p[idx] * msk[:, :, None]).sum(1) / cntn
        q = p[act] + lam * wa * (mean - p[act])
        d = ((q - p0[act]) * n0[act]).sum(1)                    # how far outside its own original surface
        q = q - np.minimum(d, 0.0)[:, None] * n0[act]            # never inside the body
        p[act] = q
    return p[ids]

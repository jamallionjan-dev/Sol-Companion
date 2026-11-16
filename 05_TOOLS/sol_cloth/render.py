"""Tiny orthographic software renderer (numpy + PIL): z-buffer, smooth Lambert shading. For looking at a body mesh offline."""
import numpy as np
from PIL import Image


def triangles(polys):
    out = []
    for p in polys:
        for i in range(1, len(p) - 1): out.append((p[0], p[i], p[i + 1]))
    return np.asarray(out, dtype=np.int64)


def vertex_normals(v, tri):
    n = np.zeros_like(v)
    fn = np.cross(v[tri[:, 1]] - v[tri[:, 0]], v[tri[:, 2]] - v[tri[:, 0]])
    for k in range(3): np.add.at(n, tri[:, k], fn)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.maximum(ln, 1e-30)


def view_matrix(yaw_deg, pitch_deg=0.0):
    """Rows = screen right, screen up, toward the viewer, for a y-up mesh. yaw 0 looks at the front (+z toward the viewer)."""
    y, p = np.radians(yaw_deg), np.radians(pitch_deg)
    ry = np.array([[np.cos(y), 0, np.sin(y)], [0, 1, 0], [-np.sin(y), 0, np.cos(y)]])
    rx = np.array([[1, 0, 0], [0, np.cos(p), -np.sin(p)], [0, np.sin(p), np.cos(p)]])
    return rx @ ry


def render(v, tri, yaw=0.0, pitch=0.0, box=None, size=(420, 420), color=(0.82, 0.80, 0.78), vcolor=None, light=(0.35, 0.45, 0.82), normals=None):
    """box = (xmin, xmax, ymin, ymax) in view space; None = fit everything. vcolor: optional (N,3) per-vertex colours."""
    R = view_matrix(yaw, pitch)
    p = v @ R.T
    n = (vertex_normals(v, tri) if normals is None else normals) @ R.T
    if box is None:
        box = (p[:, 0].min(), p[:, 0].max(), p[:, 1].min(), p[:, 1].max())
    W, H = size
    sx = (W - 1) / (box[1] - box[0]); sy = (H - 1) / (box[3] - box[2]); s = min(sx, sy)
    cx, cy = (box[0] + box[1]) / 2, (box[2] + box[3]) / 2
    X = (p[:, 0] - cx) * s + W / 2
    Y = H / 2 - (p[:, 1] - cy) * s
    Z = p[:, 2]
    L = np.asarray(light, dtype=np.float64); L /= np.linalg.norm(L)
    shade = np.clip(n @ L, 0, 1) * 0.8 + 0.2
    base = np.tile(np.asarray(color, dtype=np.float64), (len(v), 1)) if vcolor is None else np.asarray(vcolor, dtype=np.float64)
    col = base * shade[:, None]
    img = np.zeros((H, W, 3)); img[:] = (0.07, 0.10, 0.14)
    zb = np.full((H, W), -np.inf)
    for a, b, c in tri:
        xs = (X[a], X[b], X[c]); ys = (Y[a], Y[b], Y[c])
        x0, x1 = int(max(0, np.floor(min(xs)))), int(min(W - 1, np.ceil(max(xs))))
        y0, y1 = int(max(0, np.floor(min(ys)))), int(min(H - 1, np.ceil(max(ys))))
        if x0 > x1 or y0 > y1: continue
        d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(d) < 1e-12: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
        w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
        w2 = 1 - w0 - w1
        m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not m.any(): continue
        z = w0 * Z[a] + w1 * Z[b] + w2 * Z[c]
        sub = zb[y0:y1 + 1, x0:x1 + 1]
        m &= z > sub
        if not m.any(): continue
        sub[m] = z[m]
        c3 = w0[..., None] * col[a] + w1[..., None] * col[b] + w2[..., None] * col[c]
        img[y0:y1 + 1, x0:x1 + 1][m] = c3[m]
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


def sheet(images, labels=None, cols=4, pad=6):
    w, h = images[0].size
    rows = (len(images) + cols - 1) // cols
    out = Image.new("RGB", (cols * (w + pad) + pad, rows * (h + pad) + pad), (20, 26, 34))
    from PIL import ImageDraw
    d = ImageDraw.Draw(out)
    for i, im in enumerate(images):
        x, y = pad + (i % cols) * (w + pad), pad + (i // cols) * (h + pad)
        out.paste(im, (x, y))
        if labels: d.text((x + 6, y + 4), labels[i], fill=(240, 240, 120))
    return out

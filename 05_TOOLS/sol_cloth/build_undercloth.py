"""Builds the accepted "under cloth" chest shape (Jamal 2026-11-16: chest_preview6, column 3) for one body size and
saves it as data: per vertex of the body FBX, the offset (in the FBX file's own units and axes) from the bare shape to
the under-cloth shape, and the under-cloth normal. The bare body file is not changed.
usage: python build_undercloth.py [L|M|S] -> out/undercloth_<size>.npz and a check line"""
import os, sys
import numpy as np
import render as R
from chest_preview import load, BODY
import fbx_read as F
import chest_preview3 as C3
from chest_preview4 import support
from chest_preview5 import chest_band, find_tips
from chest_preview6 import tip_only
HERE = os.path.dirname(os.path.abspath(__file__))
size = sys.argv[1] if len(sys.argv) > 1 else "L"
suffix = "" if size == "L" else size
v, tri, names, W = load(suffix)
sv = support(v, tri, names, W)
band = chest_band(sv, names, W)
tips = find_tips(sv, band)
acc, nrm, st = C3.chest(sv, tri, names, W, across=0.45, slope=1.6, blur=10)
new = tip_only(acc, sv, band, tips)
raw = F.meshes(F.read(BODY % suffix))[0]["verts"]
scale = 1.65 / (raw[:, 1].max() - raw[:, 1].min())
flip = np.array([1, -1, -1.0])
offset_file = (new - v) / scale * flip                       # back to the file's units and axes
normal_file = nrm * flip
moved = np.linalg.norm(new - v, axis=1)
np.savez_compressed(os.path.join(HERE, "out", "undercloth_%s.npz" % size), offset=offset_file.astype(np.float32),
                    normal=normal_file.astype(np.float32), moved=(moved > 1e-5), scale=scale)
print("size %s: %d of %d vertices move, max %.1f mm, mean of moved %.1f mm; vertices outside the chest band moved: %d"
      % (size, (moved > 1e-5).sum(), len(v), moved.max() * 1000, moved[moved > 1e-5].mean() * 1000,
         int(((moved > 1e-5) & ((v[:, 1] < 0.93) | (v[:, 1] > 1.43))).sum())))

"""Signed-distance parts -> game-ready triangle meshes (marching cubes), in metres."""
import numpy as np
from skimage.measure import marching_cubes
import designs as D

def mesh_part(fn, lo, hi, step):
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    xs = [np.arange(lo[i] - step, hi[i] + 2 * step, step) for i in range(3)]
    X, Y, Z = np.meshgrid(*xs, indexing="ij"); P = np.stack([X, Y, Z], -1)
    d = fn(P.reshape(-1, 3)).reshape(X.shape)
    if d.min() >= 0: return None
    # anything touching the box edge would be cut open: make the outer shell of the grid "outside"
    d[0], d[-1], d[:, 0], d[:, -1], d[:, :, 0], d[:, :, -1] = [np.maximum(a, step) for a in (d[0], d[-1], d[:, 0], d[:, -1], d[:, :, 0], d[:, :, -1])]
    v, f, _, _ = marching_cubes(d, 0.0, spacing=(step,) * 3)
    v = v + np.array([x[0] for x in xs])
    e = step * 0.35
    g = np.stack([fn(v + np.eye(3)[i] * e) - fn(v - np.eye(3)[i] * e) for i in range(3)], 1)
    n = g / (np.linalg.norm(g, axis=1, keepdims=True) + 1e-12)
    fnrm = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    flip = (fnrm * n[f].mean(1)).sum(1) < 0                       # wind every triangle outward (counter-clockwise)
    f = f.copy(); f[flip] = f[flip][:, [0, 2, 1]]
    keep = np.linalg.norm(fnrm, axis=1) > 1e-14                    # drop degenerate slivers
    f = f[keep]
    used = np.unique(f); remap = np.full(len(v), -1); remap[used] = np.arange(len(used))
    return v[used] * D.S, n[used], remap[f]

FINE = {"bones": 0.0055, "straw": 0.0045, "iron": 0.0035, "teeth": 0.004, "eyes": 0.006, "dark": 0.005, "stem": 0.006,
        "flame": 0.006, "features": 0.005}

def figure(key, step=0.011):
    """{(group, kind): [(P, N, I, swatch), ...]} in metres (pedestal-top origin), and the pivot height in metres"""
    parts, pivot = D.BUILD[key]()
    out = {}
    for group, kind, swatch, fn, (lo, hi) in parts:
        name = getattr(fn, "__name__", "")
        st = FINE.get(name, step)
        if name in ("shell", "core"): st = min(step, (hi - lo).max() / 2.7 / (12 if name == "shell" else 7))   # by pumpkin size
        m = mesh_part(fn, lo, hi, st)
        if m is None: raise SystemExit(f"{key}: a part produced no surface ({group} {kind} {swatch})")
        out.setdefault((group, kind), []).append(m + (swatch,))
    return out, pivot * D.S

"""Preview renders of the BUILT meshes (software z-buffer), to check what goes into the game.
Reads work/out/<key>_meshes.pkl written by model.py."""
import numpy as np, os, sys, math
from PIL import Image, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C, designs as D

KIND_COL = {D.CANDLE: (1.0, 0.62, 0.16), D.GLOW: (0.35, 1.0, 0.5), D.GHOST: (0.80, 0.88, 1.0)}
EMIT = {D.CANDLE: 1.0, D.GLOW: 1.0}

def srgb_lin(c): return (np.asarray(c, float) / 255) ** 2.2

def load(key):
    import pickle; return pickle.load(open(os.path.join(C.WORK, "out", f"{key}_meshes.pkl"), "rb"))

def rot(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
    return Rx @ Ry

def render(key, W=420, H=520, yaw=25, pitch=-10, ppu=2400, focus_y=0.075, glow=1.0, flicker=1.0, bg=(0.05, 0.045, 0.06), wob=0.0):
    """meshes: list of (group, kind, P, N, I, colour_per_vertex)"""
    meshes = load(key)
    Rm = rot(yaw, pitch); zb = np.full((H, W), -9.0); col = np.zeros((H, W, 3)); emi = np.zeros((H, W, 3))
    L = np.array([-0.5, 0.75, -0.6]); L /= np.linalg.norm(L)
    for (group, kind, P, N, I, vc, piv, *rest) in meshes:
        UV = rest[0] if rest else None
        tex = None
        if UV is not None:
            import model as _M; tex = _M.jack_texture(kind); th, tw = tex.shape[:2]
        P = P.copy()
        if group == "head" and wob:
            a = math.radians(wob); Rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
            P = (P - [0, piv, 0]) @ Rz.T + [0, piv, 0]; N = N @ Rz.T
        Q = P @ Rm.T; Nq = N @ Rm.T
        sx = W / 2 + Q[:, 0] * ppu; sy = H / 2 - (Q[:, 1] - focus_y) * ppu; z = -Q[:, 2]
        lit = np.clip(N @ L, 0, 1) * 0.75 + 0.2
        rim = (1 - np.clip(-Nq[:, 2], 0, 1)) ** 2.5
        if kind in EMIT:
            c = np.tile(np.array(KIND_COL[kind]) * (glow if kind == D.GLOW else flicker), (len(P), 1)); e = c
        elif kind == D.GLOWTEX:
            c = vc; e = vc * 0.6
        elif kind == D.GHOST:
            c = np.array(KIND_COL[kind]) * lit[:, None] * 0.75 + rim[:, None] * np.array([0.4, 0.75, 0.6]) * 0.9; e = rim[:, None] * np.array([0.2, 0.5, 0.35])
        else:
            c = vc * lit[:, None]; e = np.zeros_like(c)
        tri = I
        x0 = np.floor(np.min(sx[tri], 1)).astype(int); x1 = np.ceil(np.max(sx[tri], 1)).astype(int)
        y0 = np.floor(np.min(sy[tri], 1)).astype(int); y1 = np.ceil(np.max(sy[tri], 1)).astype(int)
        for t in range(len(tri)):
            a, b, cc = tri[t]
            xa, xb = max(x0[t], 0), min(x1[t], W - 1); ya, yb = max(y0[t], 0), min(y1[t], H - 1)
            if xa > xb or ya > yb: continue
            X, Y = np.meshgrid(np.arange(xa, xb + 1) + 0.5, np.arange(ya, yb + 1) + 0.5)
            ax, ay, bx, by, cx, cy = sx[a], sy[a], sx[b], sy[b], sx[cc], sy[cc]
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-12: continue
            w0 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den; w1 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den; w2 = 1 - w0 - w1
            m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not m.any(): continue
            zz = w0 * z[a] + w1 * z[b] + w2 * z[cc]
            sub = zb[ya:yb + 1, xa:xb + 1]; upd = m & (zz > sub)
            if not upd.any(): continue
            sub[upd] = zz[upd]
            cv = w0[..., None] * c[a] + w1[..., None] * c[b] + w2[..., None] * c[cc]
            if tex is not None:                                  # textured kinds: sample the texture per pixel
                u_ = w0 * UV[a, 0] + w1 * UV[b, 0] + w2 * UV[cc, 0]; v_ = w0 * UV[a, 1] + w1 * UV[b, 1] + w2 * UV[cc, 1]
                tc = tex[np.clip((v_ * th).astype(int), 0, th - 1), np.clip((u_ * tw).astype(int), 0, tw - 1)]
                cv = tc * (1.0 if kind == D.GLOWTEX else (w0[..., None] * lit[a] + w1[..., None] * lit[b] + w2[..., None] * lit[cc]))
            ev = w0[..., None] * e[a] + w1[..., None] * e[b] + w2[..., None] * e[cc]
            if tex is not None: ev = tc * 0.6 if kind == D.GLOWTEX else np.zeros_like(cv)
            col[ya:yb + 1, xa:xb + 1][upd] = cv[upd]; emi[ya:yb + 1, xa:xb + 1][upd] = ev[upd]
    img = np.where((zb > -9)[..., None], col, np.array(bg))
    gi = Image.fromarray((np.clip(emi, 0, 1) * 255).astype(np.uint8))
    g = np.asarray(gi.filter(ImageFilter.GaussianBlur(5))).astype(float) / 255 + 0.5 * np.asarray(gi.filter(ImageFilter.GaussianBlur(14))).astype(float) / 255
    out = np.clip(img ** (1 / 2.2) + 0.8 * g, 0, 1)
    return Image.fromarray((out * 255).astype(np.uint8)), (zb > -9)

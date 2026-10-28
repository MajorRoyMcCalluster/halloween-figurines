"""Low-poly analytic mesh primitives (positions, smooth normals, triangles wound counter-clockwise from outside)."""
import numpy as np

class Mesh:
    def __init__(self, P=None, N=None, I=None, UV=None):
        self.P = np.zeros((0, 3)) if P is None else np.asarray(P, float)
        self.N = np.zeros((0, 3)) if N is None else np.asarray(N, float)
        self.I = np.zeros((0, 3), int) if I is None else np.asarray(I, int)
        self.UV = UV                                    # fixed UVs (None: box-projected later)
    def __add__(self, o):
        if self.UV is not None or o.UV is not None:
            a = self.UV if self.UV is not None else np.full((len(self.P), 2), np.nan)
            b = o.UV if o.UV is not None else np.full((len(o.P), 2), np.nan)
            uv = np.vstack([a, b])
        else: uv = None
        return Mesh(np.vstack([self.P, o.P]), np.vstack([self.N, o.N]), np.vstack([self.I, o.I + len(self.P)]), uv)
    def transformed(self, R=np.eye(3), t=(0, 0, 0)):
        return Mesh(self.P @ R.T + np.asarray(t), self.N @ R.T, self.I.copy(), None if self.UV is None else self.UV.copy())

def merge(ms):
    out = Mesh()
    for m in ms: out = out + m
    return out

def _fix_winding(P, N, I):
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    flip = (fn * N[I].mean(1)).sum(1) < 0
    I = I.copy(); I[flip] = I[flip][:, [0, 2, 1]]
    return I

def _grid_faces(nu, nv, offset=0, wrap_u=False):
    tris = []
    cols = nu if wrap_u else nu - 1
    for j in range(nv - 1):
        for i in range(cols):
            a = offset + j * nu + i; b = offset + j * nu + (i + 1) % nu
            c = offset + (j + 1) * nu + i; d = offset + (j + 1) * nu + (i + 1) % nu
            tris += [(a, b, d), (a, d, c)]
    return np.array(tris, int)

def _edge_samples(b, r, n_arc, n_flat):
    """1D sample positions on [-b, b] dense in the rounded bands (uniform in angle)"""
    inner = b - r
    th = np.linspace(0, np.pi / 4, n_arc + 1)
    arc = inner + r * np.tan(th)                         # inner .. b along the face, 0..45 deg of the bevel
    flat = np.linspace(-inner, inner, n_flat + 2)[1:-1] if inner > 1e-9 else np.array([])
    return np.unique(np.round(np.concatenate([-arc[::-1], flat, arc]), 12))

def rbox(c, b, r, n_arc=4, n_flat=2):
    """rounded box: centre c, half extents b, corner radius r"""
    c = np.asarray(c, float); b = np.asarray(b, float); inner = b - r
    P, N, I = [], [], []
    axes = [(0, 1, 2), (1, 2, 0), (2, 0, 1)]
    for ax, u, v in axes:
        su = _edge_samples(b[u], r, n_arc, n_flat); sv = _edge_samples(b[v], r, n_arc, n_flat)
        for s in (-1, 1):
            U, Vv = np.meshgrid(su, sv)
            q = np.zeros(U.shape + (3,)); q[..., ax] = s * b[ax]; q[..., u] = U; q[..., v] = Vv
            q = q.reshape(-1, 3); cl = np.clip(q, -inner, inner); d = q - cl
            nrm = d / np.linalg.norm(d, axis=1, keepdims=True)
            p = c + cl + r * nrm
            f = _grid_faces(len(su), len(sv), len(P) and sum(len(x) for x in P))
            P.append(p); N.append(nrm); I.append(f)
    P = np.vstack(P); N = np.vstack(N); I = np.vstack(I)
    return Mesh(P, N, _fix_winding(P, N, I))

def _frame(axis):
    a = np.asarray(axis, float); a = a / np.linalg.norm(a)
    t = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(a, t); u /= np.linalg.norm(u); v = np.cross(a, u)
    return a, u, v

def cylinder(a, b, r, seg=24, caps=True, bevel=0.0):
    """capped cylinder from a to b (optional small bevel ring on the caps)"""
    a = np.asarray(a, float); b = np.asarray(b, float)
    ax, u, v = _frame(b - a); h = np.linalg.norm(b - a)
    ang = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    ring = np.cos(ang)[:, None] * u + np.sin(ang)[:, None] * v
    P, N, I = [], [], []
    # side
    for t, rr in ((bevel, r), (h - bevel, r)):
        P.append(a + ax * t + ring * rr); N.append(ring)
    side = Mesh(np.vstack(P), np.vstack(N), _grid_faces(seg, 2, 0, True))
    parts = [side]
    if caps:
        for t, s in ((0, -1), (h, 1)):
            pts = []; nn = []
            if bevel > 0:
                k = (bevel if s > 0 else -bevel) * 0  # bevel ring
                pts.append(a + ax * (t - s * bevel) + ring * r); nn.append(ring * 0.6 + ax * s * 0.8)
                pts.append(a + ax * t + ring * (r - bevel)); nn.append(np.tile(ax * s, (seg, 1)))
            else:
                pts.append(a + ax * t + ring * r); nn.append(np.tile(ax * s, (seg, 1)))
            centre = a + ax * t
            Pc = np.vstack(pts + [centre[None]]); Nc = np.vstack(nn + [ax[None] * s])
            Nc = Nc / np.linalg.norm(Nc, axis=1, keepdims=True)
            nr = len(pts); tris = []
            if nr == 2: tris += list(_grid_faces(seg, 2, 0, True))
            last = (nr - 1) * seg; ci = nr * seg
            tris += [(last + i, last + (i + 1) % seg, ci) for i in range(seg)]
            I = np.array(tris, int); parts.append(Mesh(Pc, Nc, _fix_winding(Pc, Nc, I)))
    m = merge(parts); m.I = _fix_winding(m.P, m.N, m.I)
    return m

def sphere(c, r, seg=20, rings=12, squash=(1, 1, 1)):
    c = np.asarray(c, float)
    th = np.linspace(0, np.pi, rings + 1); ph = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    T, Ph = np.meshgrid(th, ph, indexing="ij")
    n = np.stack([np.sin(T) * np.cos(Ph), np.cos(T), np.sin(T) * np.sin(Ph)], -1).reshape(-1, 3)
    sq = np.asarray(squash, float)
    P = c + n * r * sq; N = n / sq; N /= np.linalg.norm(N, axis=1, keepdims=True)
    I = _grid_faces(seg, rings + 1, 0, True)
    I = I[np.abs(np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])).sum(1) > 1e-14]
    return Mesh(P, N, _fix_winding(P, N, I))

def tube(points, radii, seg=12, cap_spheres=True):
    """swept tube along a polyline (smooth joints), with sphere caps"""
    pts = np.asarray(points, float); rr = np.broadcast_to(np.asarray(radii, float), (len(pts),))
    tang = np.gradient(pts, axis=0); tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    _, u, _ = _frame(tang[0]); P, N = [], []
    for k in range(len(pts)):
        u = u - tang[k] * (u @ tang[k]); u /= np.linalg.norm(u); v = np.cross(tang[k], u)
        ang = np.linspace(0, 2 * np.pi, seg, endpoint=False)
        ring = np.cos(ang)[:, None] * u + np.sin(ang)[:, None] * v
        P.append(pts[k] + ring * rr[k]); N.append(ring)
    P = np.vstack(P); N = np.vstack(N)
    m = Mesh(P, N, _fix_winding(P, N, _grid_faces(seg, len(pts), 0, True)))
    if cap_spheres:
        m = m + sphere(pts[0], rr[0], seg, 8) + sphere(pts[-1], rr[-1], seg, 8)
    return m

def disc_poly(c, r, normal=(0, 0, -1), sides=8, rot=np.pi / 8):
    """flat polygon (one-sided, facing `normal`)"""
    c = np.asarray(c, float); ax, u, v = _frame(normal)
    ang = rot + np.linspace(0, 2 * np.pi, sides, endpoint=False)
    P = np.vstack([c, c + (np.cos(ang)[:, None] * u + np.sin(ang)[:, None] * v) * r])
    N = np.tile(ax, (len(P), 1)); I = np.array([(0, 1 + i, 1 + (i + 1) % sides) for i in range(sides)])
    return Mesh(P, N, _fix_winding(P, N, I))

def rounded_rect(c, w, h, r, normal=(0, 0, -1), n_arc=5):
    """flat rounded rectangle in the XY plane at c (one-sided, facing normal); w,h half sizes"""
    c = np.asarray(c, float); pts = []
    for cx, cy, a0 in ((w - r, h - r, 0), (-(w - r), h - r, 90), (-(w - r), -(h - r), 180), (w - r, -(h - r), 270)):
        for t in np.radians(np.linspace(a0, a0 + 90, n_arc + 1)):
            pts.append((cx + r * np.cos(t), cy + r * np.sin(t)))
    pts = np.array(pts)
    P = np.vstack([c, np.column_stack([pts, np.zeros(len(pts))]) + c])
    N = np.tile(np.asarray(normal, float), (len(P), 1)); n = len(pts)
    I = np.array([(0, 1 + i, 1 + (i + 1) % n) for i in range(n)])
    return Mesh(P, N, _fix_winding(P, N, I))

def dome(c, r, normal=(0, 0, -1), seg=20, rings=6, height=0.6):
    """spherical cap (lens) facing `normal`, base radius r, bulge height*r"""
    c = np.asarray(c, float); ax, u, v = _frame(normal)
    R = (r * r + (height * r) ** 2) / (2 * height * r); a_max = np.arcsin(min(1, r / R))
    centre = c - ax * (R - height * r); P, N = [centre + ax * R], [ax]
    for k in range(1, rings + 1):
        a = a_max * k / rings
        for i in range(seg):
            phi = 2 * np.pi * i / seg; d = ax * np.cos(a) + (u * np.cos(phi) + v * np.sin(phi)) * np.sin(a)
            P.append(centre + d * R); N.append(d)
    P = np.array(P); N = np.array(N); tris = [(0, 1 + i, 1 + (i + 1) % seg) for i in range(seg)]
    for k in range(rings - 1):
        o0 = 1 + k * seg; o1 = o0 + seg
        for i in range(seg):
            j = (i + 1) % seg; tris += [(o0 + i, o1 + i, o1 + j), (o0 + i, o1 + j, o0 + j)]
    I = np.array(tris); return Mesh(P, N, _fix_winding(P, N, I))

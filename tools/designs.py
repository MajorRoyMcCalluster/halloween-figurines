"""The three Halloween figurines as signed-distance functions (concept units; x S = metres).

Origin = centre of the pedestal top, +Y up, -Z is the front (faces the pilot).
Each figurine is a list of parts: (group, kind, swatch, sdf, (lo, hi)).
  group   "head" wobbles on the figurine's bobble joint about PIVOT; "body" stays put
  kind    LIT     lit, coloured from the palette (bone, pumpkin, stem, ...)
          CANDLE  unlit flickering candle light (flipbook) - inside the jack-o'-lanterns, the lantern
          GLOW    unlit pulsing cursed-green glow (flipbook) - the skeleton's eyes
          GHOST   lit, translucent pale sheet - the ghost
"""
import numpy as np

S = 0.18
LIT, CANDLE, GLOW, GHOST = "LIT", "CANDLE", "GLOW", "GHOST"
# palette swatches for LIT
BONE, PUMPKIN, STEM, DARK, CLOTH, STRAW, IRON, INSIDE = range(8)
PALETTE = {  # sRGB colour, roughness, metallic
    BONE: ((228, 219, 196), 0.62, 0.0), PUMPKIN: ((236, 112, 18), 0.42, 0.0), STEM: ((92, 104, 40), 0.75, 0.0),
    DARK: ((14, 12, 16), 0.9, 0.0), CLOTH: ((60, 34, 78), 0.85, 0.0), STRAW: ((205, 160, 80), 0.8, 0.0),
    IRON: ((70, 66, 62), 0.45, 1.0), INSIDE: ((255, 170, 60), 0.6, 0.0),
}

V = lambda *a: np.array(a, float)
def length(p): return np.sqrt((p * p).sum(-1))
def sphere(p, c, r): return length(p - c) - r
def rbox(p, c, b, r):
    q = np.abs(p - c) - (np.array(b) - r); return length(np.maximum(q, 0)) + np.minimum(q.max(-1), 0) - r
def capsule(p, a, b, ra, rb=None):
    rb = ra if rb is None else rb; pa = p - a; ba = b - a; h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    return length(pa - h[..., None] * ba) - (ra + (rb - ra) * h)
def cyly(p, c, r, h):
    q = p - c; d = np.stack([length(q[..., [0, 2]]) - r, np.abs(q[..., 1]) - h], -1)
    return np.minimum(d.max(-1), 0) + length(np.maximum(d, 0))
def smin(a, b, k): h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1); return b * (1 - h) + a * h - k * h * (1 - h)
def smax(a, b, k): return -smin(-a, -b, k)
def ellip(p, c, r):
    q = (p - c) / r; k0 = length(q); k1 = length(q / r); return k0 * (k0 - 1) / np.maximum(k1, 1e-9)
def torus_y(p, c, R, r):
    q = p - c; return length(np.stack([length(q[..., [0, 2]]) - R, q[..., 1]], -1)) - r

# ---------------------------------------------------------------- 2D helpers (jack-o'-lantern faces)
def tri2(px, py, a, b, c):
    """signed distance to a 2D triangle (iq)"""
    p = np.stack([px, py], -1); a, b, c = map(np.asarray, (a, b, c))
    e0, e1, e2 = b - a, c - b, a - c; v0, v1, v2 = p - a, p - b, p - c
    def seg(v, e):
        h = np.clip((v @ e) / (e @ e), 0, 1); d = v - h[..., None] * e; return (d * d).sum(-1)
    s = np.sign(e0[0] * e2[1] - e0[1] * e2[0])
    cr = lambda v, e: s * (v[..., 0] * e[1] - v[..., 1] * e[0])
    d = np.minimum(np.minimum(seg(v0, e0), seg(v1, e1)), seg(v2, e2))
    inside = np.minimum(np.minimum(cr(v0, e0), cr(v1, e1)), cr(v2, e2))
    return -np.sqrt(d) * np.sign(inside)

def face2(u, v):
    """jack-o'-lantern face in units of the pumpkin radius (negative inside a carved hole)"""
    eyes = np.minimum(tri2(u, v, (-0.58, 0.05), (-0.16, 0.05), (-0.37, 0.42)), tri2(u, v, (0.16, 0.05), (0.58, 0.05), (0.37, 0.42)))
    nose = tri2(u, v, (-0.09, -0.12), (0.09, -0.12), (0.0, 0.04))
    mouth = np.maximum(length(np.stack([u, v + 0.05], -1)) - 0.62, -(length(np.stack([u, v - 0.38], -1)) - 0.7))
    mouth = np.maximum(mouth, np.abs(u) - 0.56)
    for tx, up in ((-0.3, True), (0.0, False), (0.3, True)):           # three square teeth
        tooth = np.maximum(np.abs(u - tx) - 0.06, np.abs(v - (-0.38 if up else -0.6)) - 0.09)
        mouth = np.maximum(mouth, -tooth)
    return np.minimum(np.minimum(eyes, nose), mouth)

def pumpkin_parts(group, c, r, rot=0.0, face=True, stem_tilt=0.12):
    """a carved jack-o'-lantern: ribbed hollow shell with the face cut through, a candle-lit core inside, and a stem"""
    ca, sa = np.cos(rot), np.sin(rot)
    def local(p):
        q = p - c
        return np.stack([ca * q[..., 0] - sa * q[..., 2], q[..., 1], sa * q[..., 0] + ca * q[..., 2]], -1)
    def outer(q):
        az = np.arctan2(q[..., 2], q[..., 0]); rib = 1 - 0.075 * np.abs(np.cos(4 * az)) ** 0.7
        return ellip(q, V(0, 0, 0), V(r * 1.12, r * 0.84, r * 1.12) * rib[..., None])
    def shell(p):
        q = local(p); o = outer(q)
        d = np.maximum(o, -(o + r * 0.13))                              # hollow
        if face:
            f = face2(q[..., 0] / r, q[..., 1] / r) * r
            d = np.maximum(d, -np.maximum(f, q[..., 2]))               # cut the face through the front half
        return d
    def core(p):
        q = local(p); return ellip(q, V(0, -0.05 * r, 0.05 * r), V(r * 0.78, r * 0.55, r * 0.78))
    def stem(p):
        q = local(p); return capsule(q, V(0, r * 0.62, 0), V(r * stem_tilt, r * 1.12, -r * 0.04), r * 0.15, r * 0.1)
    box = (c - r * 1.35, c + r * 1.35)
    out = [(group, LIT, PUMPKIN, shell, box), (group, LIT, STEM, stem, box)]
    if face: out.append((group, CANDLE, None, core, box))
    return out

def base_pumpkins():
    """two little jack-o'-lanterns on the pedestal, front left and right of the figurine"""
    return pumpkin_parts("body", V(-0.205, 0.058, -0.135), 0.072, rot=-0.45) + \
           pumpkin_parts("body", V(0.215, 0.052, -0.12), 0.064, rot=0.5, stem_tilt=-0.1)

# ---------------------------------------------------------------- A: ghost (the whole ghost sways from its base)
def ghost():
    def body(p):
        y = p[..., 1]; az = np.arctan2(p[..., 2], p[..., 0])
        hem = 0.10 + 0.035 * np.sin(6 * az)
        R0, yc = 0.212, 0.55                                            # round head flowing into a flared sheet
        cap = np.sqrt(np.maximum(R0 ** 2 - (y - yc) ** 2, 0.0))
        rad = np.where(y > yc, cap, R0 + 0.055 * np.clip((yc - y) / 0.42, 0, 1) ** 1.3)
        b = np.maximum(length(p[..., [0, 2]]) - rad, y - (yc + R0))
        b = smax(b, -(y - hem), 0.03)
        arms = np.minimum(capsule(p, V(-0.2, 0.42, -0.02), V(-0.31, 0.33, -0.12), 0.05, 0.035),
                          capsule(p, V(0.2, 0.42, -0.02), V(0.30, 0.50, -0.10), 0.05, 0.035))
        b = smin(b, arms, 0.04)
        return smax(b, -features(p), 0.008)
    def features(p):                                                  # two eyes and an "oooh" mouth, pressed in
        eyes = np.minimum(ellip(p, V(-0.075, 0.58, -0.205), V(0.034, 0.055, 0.03)), ellip(p, V(0.075, 0.58, -0.205), V(0.034, 0.055, 0.03)))
        mouth = ellip(p, V(0, 0.475, -0.21), V(0.038, 0.05, 0.03))
        return np.minimum(eyes, mouth)
    def dark(p): return features(p) + 0.006
    box = (V(-0.42, 0.06, -0.33), V(0.42, 0.8, 0.3))
    parts = [("head", GHOST, None, body, box), ("head", LIT, DARK, dark, (V(-0.15, 0.4, -0.27), V(0.15, 0.66, -0.12)))]
    parts += pumpkin_parts("head", V(-0.285, 0.27, -0.165), 0.092, rot=0.4)       # the jack-o'-lantern it carries
    return parts + base_pumpkins(), 0.10

# ---------------------------------------------------------------- B: skeleton on a pumpkin (the big skull nods)
def skeleton():
    def skull(p):
        s = smin(sphere(p, V(0, 0.64, 0), 0.165), rbox(p, V(0, 0.545, -0.035), (0.095, 0.055, 0.085), 0.04), 0.05)
        sockets = np.minimum(sphere(p, V(-0.063, 0.645, -0.145), 0.046), sphere(p, V(0.063, 0.645, -0.145), 0.046))
        nose = capsule(p, V(0, 0.585, -0.16), V(0, 0.6, -0.12), 0.016)
        return smax(s, -np.minimum(sockets, nose), 0.012)
    def teeth(p):
        t = np.full(p.shape[:-1], 1e9)
        for i in range(-3, 4):
            t = np.minimum(t, rbox(p, V(i * 0.021, 0.512, -0.108 + abs(i) * 0.007), (0.0085, 0.013, 0.01), 0.004))
        return t
    def eyes(p):
        return np.minimum(sphere(p, V(-0.063, 0.645, -0.125), 0.028), sphere(p, V(0.063, 0.645, -0.125), 0.028))
    def bones(p):
        def bone(a, b, r=0.016):
            return np.minimum(capsule(p, a, b, r), np.minimum(sphere(p, a, r * 1.6), sphere(p, b, r * 1.6)))
        d = capsule(p, V(0, 0.47, 0.02), V(0, 0.25, 0.03), 0.021)                    # spine
        for yy, R in ((0.425, 0.08), (0.385, 0.088), (0.345, 0.084), (0.305, 0.07)):  # ribs, open at the back
            d = np.minimum(d, np.maximum(torus_y(p, V(0, yy, 0.0), R, 0.0105), p[..., 2] - 0.03))
        d = np.minimum(d, ellip(p, V(0, 0.235, 0.0), V(0.08, 0.038, 0.05)))           # pelvis
        d = np.minimum(d, capsule(p, V(-0.1, 0.445, 0.01), V(0.1, 0.445, 0.01), 0.012))  # collar bones
        d = np.minimum(d, bone(V(-0.1, 0.445, 0.0), V(-0.17, 0.33, -0.07)))          # left arm, hand on knee
        d = np.minimum(d, bone(V(-0.17, 0.33, -0.07), V(-0.11, 0.24, -0.16)))
        d = np.minimum(d, bone(V(0.1, 0.445, 0.0), V(0.2, 0.40, -0.06)))             # right arm, waving
        d = np.minimum(d, bone(V(0.2, 0.40, -0.06), V(0.22, 0.56, -0.1)))
        for sd in (-1, 1):
            d = np.minimum(d, bone(V(sd * 0.05, 0.225, -0.02), V(sd * 0.085, 0.235, -0.18), 0.018))   # thighs
            d = np.minimum(d, bone(V(sd * 0.085, 0.235, -0.18), V(sd * 0.1, 0.07, -0.23), 0.016))     # shins
            d = np.minimum(d, ellip(p, V(sd * 0.1, 0.055, -0.255), V(0.026, 0.016, 0.04)))           # feet
        for k in range(4):                                                           # waving fingers
            a = V(0.22, 0.56, -0.1); d = np.minimum(d, capsule(p, a, a + V(-0.02 + 0.014 * k, 0.05 - 0.006 * abs(k - 1.5), -0.004), 0.006))
        return d
    parts = [("head", LIT, BONE, skull, (V(-0.2, 0.44, -0.22), V(0.2, 0.83, 0.2))),
             ("head", LIT, BONE, teeth, (V(-0.1, 0.48, -0.13), V(0.1, 0.54, -0.07))),
             ("head", GLOW, None, eyes, (V(-0.11, 0.6, -0.17), V(0.11, 0.69, -0.08))),
             ("body", LIT, BONE, bones, (V(-0.24, 0.0, -0.3), V(0.28, 0.65, 0.12)))]
    parts += pumpkin_parts("body", V(0, 0.115, 0.0), 0.15)                           # the big jack-o'-lantern seat
    parts += pumpkin_parts("body", V(-0.235, 0.05, -0.13), 0.062, rot=-0.5)           # and a little one beside it
    return parts, 0.47

# ---------------------------------------------------------------- C: pumpkin-head (the pumpkin head bobs)
def pumpkinhead():
    def cloak(p):
        y = p[..., 1]; az = np.arctan2(p[..., 2], p[..., 0])
        c = length(p[..., [0, 2]]) - (0.09 + 0.17 * np.clip((0.42 - y) / 0.36, 0, 1))
        c = smin(c, sphere(p, V(0, 0.4, 0), 0.095), 0.05)
        c = smax(c, -(y - 0.04 - 0.022 * np.sin(9 * az)), 0.02)                   # ragged hem
        c = smax(c, y - 0.44, 0.02)
        arms = np.minimum(capsule(p, V(-0.11, 0.37, 0), V(-0.23, 0.27, -0.08), 0.04, 0.03),
                          capsule(p, V(0.11, 0.37, 0), V(0.22, 0.25, -0.1), 0.04, 0.03))
        return smin(c, arms, 0.03)
    def straw(p):
        d = torus_y(p, V(0, 0.43, 0), 0.085, 0.025)                                  # straw collar
        for sd, h in ((-1, V(-0.23, 0.27, -0.08)), (1, V(0.22, 0.25, -0.1))):
            for k in range(4):
                tip = h + V(sd * (0.035 + 0.008 * k), -0.045 + 0.012 * k, -0.02 + 0.012 * k)
                d = np.minimum(d, capsule(p, h, tip, 0.006, 0.004))
        return d
    lc = V(0.255, 0.13, -0.135)                                                      # lantern, hanging from the right hand
    def iron(p):
        frame = np.maximum(rbox(p, lc, (0.045, 0.06, 0.045), 0.006), -rbox(p, lc, (0.037, 0.052, 0.037), 0.003))
        frame = np.maximum(frame, -rbox(p, lc, (0.06, 0.047, 0.03), 0.004))         # glass windows on all four sides
        frame = np.maximum(frame, -rbox(p, lc, (0.03, 0.047, 0.06), 0.004))
        frame = np.minimum(frame, rbox(p, lc + V(0, 0.065, 0), (0.05, 0.008, 0.05), 0.004))
        frame = np.minimum(frame, rbox(p, lc - V(0, 0.065, 0), (0.05, 0.008, 0.05), 0.004))
        handle = np.maximum(np.abs(length((p - (lc + V(0, 0.075, 0)))[..., [0, 1]]) - 0.03) - 0.005, np.abs(p[..., 2] - lc[2]) - 0.005)
        handle = np.maximum(handle, -(p[..., 1] - (lc[1] + 0.075)))
        return np.minimum(frame, np.minimum(handle, capsule(p, lc + V(0, 0.105, 0), V(0.225, 0.25, -0.105), 0.004)))
    def flame(p): return rbox(p, lc, (0.03, 0.045, 0.03), 0.012)
    parts = [("body", LIT, CLOTH, cloak, (V(-0.33, 0.0, -0.3), V(0.33, 0.5, 0.3))),
             ("body", LIT, STRAW, straw, (V(-0.32, 0.18, -0.18), V(0.32, 0.47, 0.12))),
             ("body", LIT, IRON, iron, (lc - 0.09, lc + V(0.09, 0.14, 0.09))),
             ("body", CANDLE, None, flame, (lc - 0.07, lc + 0.07))]
    parts += pumpkin_parts("head", V(0, 0.585, 0), 0.165)
    parts += pumpkin_parts("body", V(-0.215, 0.055, -0.14), 0.066, rot=-0.45)
    return parts, 0.43

BUILD = {"ghost": ghost, "skeleton": skeleton, "pumpkinhead": pumpkinhead}

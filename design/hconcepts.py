"""Halloween figurine concepts (design round 1): ghost, skeleton, pumpkin-head, plus jack-o'-lanterns.
Ray-marched SDFs, metres-ish units like the Box-Bot concepts (pedestal top at y=0)."""
import numpy as np, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, "/tmp/claude-0/x/robot")
import importlib.util as _u; _s = _u.spec_from_file_location("bbconcepts", "/tmp/claude-0/x/robot/concepts.py"); _m = _u.module_from_spec(_s); _s.loader.exec_module(_m)
V, length, sphere, rbox, capsule, cylz, cyly, smin = _m.V, _m.length, _m.sphere, _m.rbox, _m.capsule, _m.cylz, _m.cyly, _m.smin

FB = "/mnt/user-data/uploads/Fonts/AGENCYB.TTF"; FR = "/mnt/user-data/uploads/Fonts/AGENCYR.TTF"
# materials
GHOST, DARK, BONE, GLOW_G, PUMP, STEM, CANDLE, PED, PEDGLOW, CLOTH, STRAW = range(11)

def smax(a, b, k): return -smin(-a, -b, k)
def ellip(p, c, r):
    q = (p - c) / r; k0 = length(q); k1 = length(q / r); return k0 * (k0 - 1) / np.maximum(k1, 1e-6)
def torus_y(p, c, R, r):
    q = p - c; return length(np.stack([length(q[..., [0, 2]]) - R, q[..., 1]], -1)) - r

def pumpkin(p, c, r, face=True, rot=0.0):
    """ribbed pumpkin with a carved jack-o'-lantern face (CANDLE glow where carved) facing -z"""
    q = p - c
    ca, sa = np.cos(rot), np.sin(rot)
    q = np.stack([ca * q[..., 0] - sa * q[..., 2], q[..., 1], sa * q[..., 0] + ca * q[..., 2]], -1)
    az = np.arctan2(q[..., 2], q[..., 0])
    rib = 1 - 0.07 * np.abs(np.cos(4 * az)) ** 0.6
    d = ellip(q, V(0, 0, 0), V(r * 1.12, r * 0.86, r * 1.12) * rib[..., None])
    stem = capsule(q, V(0, r * 0.7, 0), V(r * 0.12, r * 1.15, -r * 0.05), r * 0.13, r * 0.09)
    mat = np.full(d.shape, PUMP)
    if face:
        u, v = q[..., 0] / r, q[..., 1] / r
        front = q[..., 2] < -0.5 * r
        def tri(cx, cy, s):   # triangle eye, point up
            return (v > cy - s * 0.5) & (v < cy + s * 0.5) & (np.abs(u - cx) < (cy + s * 0.5 - v) * 0.6)
        eyes = tri(-0.38, 0.22, 0.38) | tri(0.38, 0.22, 0.38)
        nose = (np.abs(u) < (0.05 - v) * 0.7) & (v > -0.08) & (v < 0.05)
        mouth = (np.abs(u) < 0.62) & (v < -0.18 + 0.06 * np.cos(u * 18)) & (v > -0.5 + 0.35 * u ** 2 + 0.05 * np.cos(u * 18 + 1.5))
        carved = front & (eyes | nose | mouth)
        mat = np.where(carved, CANDLE, mat)
        d = np.where(carved, d + 0.004, d)
    mat = np.where(stem < d, STEM, mat)
    return np.minimum(d, stem), mat

def pedestal(p):
    base = cyly(p, V(0, -0.03, 0), 0.30, 0.03)
    ring = torus_y(p, V(0, -0.01, 0), 0.29, 0.012)
    return [(base, PED), (ring, PEDGLOW)]

T = [0.0]
def ghost(p, t=None):
    t = T[0] if t is None else t
    y = p[..., 1]
    az = np.arctan2(p[..., 2], p[..., 0])
    hem = 0.10 + 0.035 * np.sin(6 * az + t * 2.5)
    rad = 0.2 + 0.06 * np.clip((0.5 - y) / 0.4, 0, 1)
    column = np.maximum(length(p[..., [0, 2]]) - rad, y - 0.52)
    body = smin(sphere(p, V(0, 0.55, 0), 0.21), column, 0.08)
    body = smax(body, -(y - hem) * 1.0, 0.03)                     # wavy, tattered hem
    arms = np.minimum(capsule(p, V(-0.2, 0.42, -0.02), V(-0.31, 0.33, -0.12), 0.05, 0.035),
                      capsule(p, V(0.2, 0.42, -0.02), V(0.30, 0.48, -0.10), 0.05, 0.035))
    body = smin(body, arms, 0.04)
    eyes = np.minimum(ellip(p, V(-0.075, 0.57, -0.19), V(0.035, 0.055, 0.03)), ellip(p, V(0.075, 0.57, -0.19), V(0.035, 0.055, 0.03)))
    mouth = ellip(p, V(0, 0.47, -0.205), V(0.04, 0.05, 0.03))
    holes = np.minimum(eyes, mouth)
    parts = [(smax(body, -holes, 0.01), GHOST), (holes + 0.008, DARK)]
    d, m = pumpkin(p, V(-0.28, 0.27, -0.16), 0.09, rot=0.4)       # carrying a little jack-o'-lantern
    parts.append((d, m))
    return parts

def skeleton(p):
    parts = []
    skull = smin(sphere(p, V(0, 0.62, 0), 0.17), rbox(p, V(0, 0.52, -0.03), (0.10, 0.06, 0.09), 0.04), 0.05)
    sockets = np.minimum(sphere(p, V(-0.065, 0.63, -0.15), 0.048), sphere(p, V(0.065, 0.63, -0.15), 0.048))
    nose = rbox(p, V(0, 0.565, -0.16), (0.012, 0.02, 0.03), 0.008)
    skull = smax(skull, -np.minimum(sockets, nose), 0.012)
    teeth = np.full(skull.shape, 1e9)
    for i in range(-3, 4):
        teeth = np.minimum(teeth, rbox(p, V(i * 0.022, 0.49, -0.115 + abs(i) * 0.006), (0.009, 0.014, 0.01), 0.004))
    parts += [(skull, BONE), (teeth, BONE), (sphere(p, V(-0.065, 0.625, -0.13), 0.026), GLOW_G), (sphere(p, V(0.065, 0.625, -0.13), 0.026), GLOW_G),
              (nose + 0.012, DARK)]
    spine = capsule(p, V(0, 0.44, 0.02), V(0, 0.22, 0.03), 0.022)
    ribs = np.full(spine.shape, 1e9)
    for k, (yy, R) in enumerate([(0.40, 0.085), (0.36, 0.09), (0.32, 0.085), (0.28, 0.07)]):
        rr = torus_y(p, V(0, yy, 0.0), R, 0.011)
        rr = np.maximum(rr, p[..., 2] - 0.035)                     # open at the back
        ribs = np.minimum(ribs, rr)
    pelvis = ellip(p, V(0, 0.20, 0.0), V(0.08, 0.04, 0.05))
    bones = np.minimum(np.minimum(spine, ribs), pelvis)
    def bone(a, b, r=0.016):
        return np.minimum(capsule(p, a, b, r), np.minimum(sphere(p, a, r * 1.7), sphere(p, b, r * 1.7)))
    for sd in (-1, 1):
        bones = np.minimum(bones, bone(V(sd * 0.1, 0.42, 0.0), V(sd * 0.17, 0.30, -0.07)))
        bones = np.minimum(bones, bone(V(sd * 0.17, 0.30, -0.07), V(sd * 0.13 + 0.05 * (sd > 0), 0.40 + 0.12 * (sd > 0), -0.13)))   # one arm waving
        bones = np.minimum(bones, bone(V(sd * 0.05, 0.18, -0.02), V(sd * 0.09, 0.18, -0.18), 0.018))     # thighs (sitting)
        bones = np.minimum(bones, bone(V(sd * 0.09, 0.18, -0.18), V(sd * 0.10, 0.04, -0.22), 0.016))     # shins down the front
    parts.append((bones, BONE))
    d, m = pumpkin(p, V(0, 0.09, -0.03), 0.16, face=True)        # sitting on a big jack-o'-lantern
    parts.append((d, m))
    return parts

def pumpkinhead(p):
    parts = []
    d, m = pumpkin(p, V(0, 0.56, 0), 0.17)
    parts.append((d, m))
    cloak = smin(cyly(p, V(0, 0.27, 0), 0.0, 0.0) * 0 + (length(p[..., [0, 2]]) - (0.1 + 0.18 * np.clip((0.42 - p[..., 1]) / 0.35, 0, 1))), sphere(p, V(0, 0.42, 0), 0.1), 0.05)
    cloak = smax(cloak, -(p[..., 1] - 0.05 - 0.02 * np.sin(9 * np.arctan2(p[..., 2], p[..., 0]))), 0.02)
    cloak = smax(cloak, p[..., 1] - 0.45, 0.02)
    parts.append((cloak, CLOTH))
    collar = torus_y(p, V(0, 0.43, 0), 0.1, 0.03)
    parts.append((collar, STRAW))
    for sd in (-1, 1):
        parts.append((capsule(p, V(sd * 0.12, 0.38, 0), V(sd * 0.24, 0.26, -0.08), 0.035), CLOTH))
        for k in range(3):
            parts.append((capsule(p, V(sd * 0.24, 0.26, -0.08), V(sd * (0.28 + 0.02 * k), 0.20 + 0.02 * k, -0.12 + 0.02 * k), 0.008), STRAW))
    lantern = cyly(p, V(0.27, 0.16, -0.12), 0.045, 0.06)
    parts.append((lantern, CANDLE))
    parts.append((capsule(p, V(0.24, 0.27, -0.09), V(0.27, 0.22, -0.12), 0.006), DARK))
    return parts

SCENES = {"ghost": lambda p: ghost(p), "skeleton": skeleton, "pumpkinhead": pumpkinhead}
EMISSIVE = {GLOW_G: 1.0, CANDLE: 1.0, PEDGLOW: 0.8}
PAL = {GHOST: (0.80, 0.86, 0.95), DARK: (0.02, 0.02, 0.03), BONE: (0.86, 0.83, 0.74), GLOW_G: (0.35, 1.0, 0.45),
       PUMP: (0.95, 0.42, 0.06), STEM: (0.25, 0.32, 0.12), CANDLE: (1.0, 0.62, 0.15), PED: (0.07, 0.075, 0.08),
       PEDGLOW: (0.3, 1.0, 0.5), CLOTH: (0.18, 0.10, 0.22), STRAW: (0.75, 0.6, 0.3)}

def scene(name, p, ped=True):
    parts = SCENES[name](p) + (pedestal(p) if ped else [])
    D = np.stack([np.broadcast_to(d, p.shape[:-1]) for d, _ in parts], -1)
    M = np.stack([np.broadcast_to(np.asarray(m), p.shape[:-1]) for _, m in parts], -1)
    a = D.argmin(-1)
    return np.take_along_axis(D, a[..., None], -1)[..., 0], np.take_along_axis(M, a[..., None], -1)[..., 0]

def render(name, yaw=25, W=420, H=520, scale=420, cy=0.42, pitch=-8, flicker=1.0, eye=1.0, pal=None, bg=(0.05, 0.045, 0.06)):
    pal = dict(PAL, **(pal or {}))
    a = np.radians(yaw); R = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    b = np.radians(pitch); Rx = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]]); R = R @ Rx
    xs = (np.arange(W) - W / 2) / scale; ys = -(np.arange(H) - H / 2) / scale + cy
    X, Y = np.meshgrid(xs, ys); n = X.size
    ro = np.stack([X.ravel(), Y.ravel(), np.full(n, -2.0)], 1) @ R.T; rd = np.tile(V(0, 0, 1) @ R.T, (n, 1))
    f = lambda q: scene(name, q)
    t = np.zeros(n); hit = np.zeros(n, bool); alive = np.ones(n, bool)
    for _ in range(170):
        idx = np.where(alive)[0]
        if not len(idx): break
        d, _ = f(ro[idx] + rd[idx] * t[idx, None]); t[idx] += d * 0.8
        h = d < 2e-4; hit[idx[h]] = True; alive[idx[h]] = False; alive[idx[t[idx] > 4]] = False
    p = ro[hit] + rd[hit] * t[hit, None]; _, m = f(p); e = 1e-4
    g = np.stack([f(p + np.eye(3)[i] * e)[0] - f(p - np.eye(3)[i] * e)[0] for i in range(3)], 1)
    N = g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
    L = V(-0.5, 0.7, -0.6); L /= np.linalg.norm(L); Vv = -rd[hit]; Hh = L + Vv; Hh /= np.linalg.norm(Hh, axis=1, keepdims=True)
    dif = np.clip(N @ L, 0, 1) * 0.75 + 0.18
    spec = np.clip((N * Hh).sum(1), 0, 1) ** 30 * 0.35
    rim = (1 - np.clip((N * Vv).sum(1), 0, 1)) ** 2.5
    lut = np.array([pal[i] for i in range(11)], float)
    base = lut[m]
    c = base * dif[:, None] + spec[:, None]
    # warm candle light spilling onto everything near a jack-o'-lantern + cool ghost rim
    c += np.where((m == GHOST)[:, None], rim[:, None] * np.array([0.45, 0.7, 1.0]) * 0.9, 0)
    em = np.zeros_like(c)
    for mat, s in EMISSIVE.items():
        k = m == mat
        amt = s * (flicker if mat == CANDLE else eye if mat == GLOW_G else 1.0)
        c[k] = np.array(pal[mat]) * (0.35 + 1.0 * amt); em[k] = np.array(pal[mat]) * amt
    img = np.zeros((n, 3)); img[:] = bg; img[hit] = c
    emi = np.zeros((n, 3)); emi[np.where(hit)[0]] = em
    im = np.clip(img.reshape(H, W, 3), 0, 1)
    gi = Image.fromarray((np.clip(emi.reshape(H, W, 3), 0, 1) * 255).astype(np.uint8))
    glow = np.asarray(gi.filter(ImageFilter.GaussianBlur(6))).astype(float) / 255 + 0.6 * np.asarray(gi.filter(ImageFilter.GaussianBlur(18))).astype(float) / 255
    return Image.fromarray((np.clip(im + 0.9 * glow, 0, 1) * 255).astype(np.uint8))

def sheet(out):
    os.makedirs(out, exist_ok=True)
    rows = [("A  GHOST", "ghost", "translucent sheet, rippling hem, carries a jack-o'-lantern"),
            ("B  SKELETON", "skeleton", "big-skull bobblehead, glowing eyes, sits on a pumpkin"),
            ("C  PUMPKIN-HEAD", "pumpkinhead", "jack-o'-lantern head, cloak, straw hands, lantern")]
    sheet = Image.new("RGB", (3 * 430 + 10, 640), (12, 10, 14)); d = ImageDraw.Draw(sheet)
    for i, (lbl, nm, sub) in enumerate(rows):
        sheet.paste(render(nm), (5 + i * 430, 70))
        d.text((20 + i * 430, 14), lbl, font=ImageFont.truetype(FB, 40), fill=(255, 150, 40))
        d.text((20 + i * 430, 598), sub, font=ImageFont.truetype(FR, 21), fill=(200, 195, 205))
    sheet.save(f"{out}/halloween_concepts_ABC.jpg", quality=92)


def anim(out):
    """ghost hem ripple + candle flicker; skeleton eye pulse"""
    import math
    fr = []
    rng = np.random.default_rng(4)
    for k in range(16):
        T[0] = k * 2 * math.pi / 16 / 2.5
        fl = 0.75 + 0.25 * rng.random()
        a = render("ghost", W=320, H=400, scale=330, flicker=fl)
        b = render("skeleton", W=320, H=400, scale=330, flicker=fl, eye=0.55 + 0.45 * math.sin(k * 2 * math.pi / 16))
        a = haze(a, t=k * 0.4, seed=7); b = haze(b, t=k * 0.4, seed=9)
        f = Image.new("RGB", (640, 400)); f.paste(a, (0, 0)); f.paste(b, (320, 0)); fr.append(f)
    fr[0].save(f"{out}/halloween_animation_ideas.gif", save_all=True, append_images=fr[1:], duration=110, loop=0)


def haze(img, t=0.0, seed=1, strength=1.0):
    """mock of the cursed-frigate haze: drifting green cloud puffs low around the figurine + a few glowing motes"""
    W, H = img.size; r = np.random.default_rng(seed)
    a = np.asarray(img).astype(float) / 255
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    fog = np.zeros((H, W))
    for k in range(9):
        cx = W * (0.15 + 0.7 * r.random()) + 25 * np.sin(t * 0.8 + k); cy = H * (0.62 + 0.25 * r.random()) - 8 * t * (0.5 + r.random()) % 40
        s = W * (0.10 + 0.08 * r.random())
        fog += np.exp(-(((xx - cx) / s) ** 2 + ((yy - cy) / (s * 0.6)) ** 2)) * (0.5 + 0.5 * r.random())
    fog = np.clip(fog, 0, 1.4) * 0.30 * strength
    col = np.array([0.45, 1.0, 0.72])
    a = a * (1 - 0.25 * fog[..., None]) + fog[..., None] * col * 0.8
    m = np.zeros((H, W))
    for k in range(14):
        ph = (t * 0.15 + r.random()) % 1
        mx = W * (0.2 + 0.6 * r.random()) + 12 * np.sin(ph * 6 + k); my = H * (0.85 - 0.6 * ph)
        m += np.exp(-(((xx - mx) ** 2 + (yy - my) ** 2) / 6.0)) * np.sin(np.pi * ph)
    a += m[..., None] * col * 1.2 * strength
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))

def sheet_haze(out):
    rows = [("A  GHOST", "ghost"), ("B  SKELETON", "skeleton"), ("C  PUMPKIN-HEAD", "pumpkinhead")]
    sh = Image.new("RGB", (3 * 430 + 10, 640), (12, 10, 14)); d = ImageDraw.Draw(sh)
    for i, (lbl, nm) in enumerate(rows):
        sh.paste(haze(render(nm), t=i, seed=i + 2), (5 + i * 430, 70))
        d.text((20 + i * 430, 14), lbl, font=ImageFont.truetype(FB, 40), fill=(255, 150, 40))
    d.text((20, 598), "with the cursed-frigate haze: drifting green fog and glowing motes from the game's own ghost-ship effect, shrunk to dashboard size",
           font=ImageFont.truetype(FR, 21), fill=(200, 195, 205))
    sh.save(f"{out}/halloween_concepts_with_haze.jpg", quality=92)


if __name__ == "__main__":
    o = sys.argv[1]; sheet(o); sheet_haze(o); anim(o); print("ok")

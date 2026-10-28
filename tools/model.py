"""Generates the three Halloween figurine scenes, each built on a copy of the game's Polo Figurine scene (for its
wobble joint and pedestal), plus the shared materials, textures and the cursed-frigate haze particles.

Mesh slots (the template's mesh names are kept so the scene's name-hash links still match):
  head (wobbles on Headjnt):  POLOHEAD, SUB1..SUB3POLOHEAD          one per material kind used by the head
  body (static):              POLOMODEL, SUB1..SUB5POLOMODEL        one per material kind used by the body
                              SUB6, SUB7 the game's pedestal and its green glow ring (kept)
Material kinds: LIT (palette: bone, pumpkin, ...), CANDLE (flickering), GLOW (pulsing green), GHOST (translucent).
"""
import numpy as np, re, base64, os, sys, copy, struct, math
import xml.etree.ElementTree as ET
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C, designs as D, mesher

T = C.TEMPLATE
OUT = os.path.join(C.WORK, "out") + os.sep
HEAD_SLOTS = ["POLOHEAD", "SUB1POLOHEAD", "SUB2POLOHEAD", "SUB3POLOHEAD"]
BODY_SLOTS = ["POLOMODEL", "SUB1POLOMODEL", "SUB2POLOMODEL", "SUB3POLOMODEL", "SUB4POLOMODEL", "SUB5POLOMODEL"]
KINDS = [D.LIT, D.GHOST, D.CANDLE, D.GLOW]

SCENE_DIR = "MODELS\\PLANETS\\BIOMES\\COMMON\\BUILDINGS\\PROPS\\BOBBLEHEADS\\"
SHARED_DIR = SCENE_DIR + "HWFSHARED\\"                     # materials + particles shared by all three figurines
TEX_DIR = "TEXTURES/PLANETS/BIOMES/COMMON/BUILDINGS/PROPS/HALLOWEENFIGS/"
def mat_file(kind): return f"{C.PREFIX}_{kind}_MAT.MATERIAL.MBIN"
def mat_path(kind): return SHARED_DIR + mat_file(kind)
FX = {"HAZE": "cloudglow", "MOTES": "plasma"}               # our particle -> the ghost-ship effect it's made from
def fx_mat(n): return f"{C.PREFIX}_{n}.MATERIAL.MBIN"
def fx_data(n): return f"{C.PREFIX}_{n}.PARTICLE.MBIN"

# ---------------------------------------------------------------- flipbooks
FRAMES = 64                                                 # power of two: the UV step 1/64 is exact
CANDLE_FPS, GLOW_FPS = 12, 8
CELL = 4                                                    # each frame is one solid 4x4 block (exact in BC1)

def candle_levels():
    r = np.random.default_rng(31); b = []; x = 0.9
    for k in range(FRAMES):
        x = np.clip(x + r.normal(0, 0.09) + (0.88 - x) * 0.25, 0.62, 1.0)
        if r.random() < 0.06: x = 0.55 + 0.1 * r.random()        # the odd gutter
        b.append(x)
    return np.array(b)

def glow_levels():
    return 0.42 + 0.58 * (0.5 - 0.5 * np.cos(np.arange(FRAMES) * 2 * np.pi / FRAMES * 2)) ** 1.3   # two slow pulses a loop

CANDLE_RGB = (1.0, 0.55, 0.12)
GLOW_RGB = (0.30, 1.0, 0.45)

def srgb(c): return tuple(int(round(255 * (min(1, max(0, x)) ** (1 / 2.2)))) for x in c)

def strip(levels, rgb):
    a = np.zeros((CELL, CELL * FRAMES, 3), np.uint8)
    for k, l in enumerate(levels): a[:, k * CELL:(k + 1) * CELL] = srgb(np.array(rgb) * l)
    return Image.fromarray(a)

def strip_uv(): return np.array([(CELL / 2) / (CELL * FRAMES), 0.5])

# ---------------------------------------------------------------- palette (LIT) + ghost textures
PAL_W = 8                                                   # each swatch 8x8 texels
def palette_images():
    n = len(D.PALETTE); dif = np.zeros((8, PAL_W * n, 3), np.uint8); msk = np.zeros((8, PAL_W * n, 3), np.uint8)
    for i, (rgb, rough, metal) in D.PALETTE.items():
        dif[:, i * PAL_W:(i + 1) * PAL_W] = rgb
        msk[:, i * PAL_W:(i + 1) * PAL_W] = (int(rough * 255), int(metal * 255), 0)
    return Image.fromarray(dif), Image.fromarray(msk)
def swatch_uv(i): return np.array([(i * PAL_W + PAL_W / 2) / (PAL_W * len(D.PALETTE)), 0.5])

def ghost_image():
    r = np.random.default_rng(5); W = 64
    y, x = np.mgrid[0:W, 0:W] / W
    n = 0.06 * np.sin(2 * np.pi * (x * 2 + y * 3)) + 0.04 * np.sin(2 * np.pi * (x * 5 - y * 2)) + r.normal(0, 0.01, (W, W))
    rgb = np.stack([215 + 40 * n, 232 + 30 * n, 255 + 0 * n], -1)
    a = np.clip(150 + 120 * n, 0, 255)[..., None]
    return Image.fromarray(np.clip(np.concatenate([rgb, a], -1), 0, 255).astype(np.uint8), "RGBA")

def mip_dds(img, fmt, path, mips=True):
    w, h = img.size; levels = []; cur = img
    code = {"DXT1": 1, "DXT5": 3, "ATI2": 5}[fmt]
    while True:
        cw, ch = cur.size
        c4 = cur if (cw >= 4 and ch >= 4) else cur.resize((max(4, cw), max(4, ch)), Image.BOX)
        levels.append(c4.tobytes("bcn", code))
        if not mips or (cw == 1 and ch == 1): break
        cur = cur.resize((max(1, cw // 2), max(1, ch // 2)), Image.BOX)
    blk = 8 if fmt == "DXT1" else 16
    hdr = struct.pack("<4s7I", b"DDS ", 124, 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000, h, w,
                      max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * blk, 0, len(levels)) + b"\0" * 44
    hdr += struct.pack("<2I4s5I", 32, 0x4, fmt.encode(), 0, 0, 0, 0, 0) + struct.pack("<5I", 0x1000 | 0x8 | 0x400000, 0, 0, 0, 0)
    open(path, "wb").write(hdr + b"".join(levels))

def textures():
    os.makedirs(OUT + "tex", exist_ok=True); t = OUT + "tex/" + C.PREFIX
    dif, msk = palette_images()
    mip_dds(dif, "DXT1", t + "_PALETTE.DDS", mips=False); mip_dds(msk.convert("RGB"), "ATI2", t + "_PALETTE.MASKS.DDS", mips=False)
    mip_dds(Image.new("RGB", (16, 16), (128, 128, 255)), "ATI2", t + "_FLAT.NORMAL.DDS")
    mip_dds(Image.new("RGB", (16, 16), (60, 0, 0)), "ATI2", t + "_GHOST.MASKS.DDS")
    mip_dds(ghost_image(), "DXT5", t + "_GHOST.DDS")
    mip_dds(strip(candle_levels(), CANDLE_RGB), "DXT1", t + "_CANDLE.DDS", mips=False)
    mip_dds(strip(glow_levels(), GLOW_RGB), "DXT1", t + "_GLOW.DDS", mips=False)
    strip(candle_levels(), CANDLE_RGB).resize((CELL * FRAMES, 32), Image.NEAREST).save(OUT + "preview_candle_strip.png")

# ---------------------------------------------------------------- materials
def _rename(m, name):
    return re.sub(r'(<Data template="cTkMaterialData">\s*<Property name="Name" value=")[^"]*', r'\g<1>' + name, m, count=1)
def _set_vec(m, uniform, vals):
    pat = re.compile(r'(<Property name="Name" value="%s" />\s*<Property name="Values"[^>]*>\s*)'
                     r'<Property name="X" value="[^"]*" />\s*<Property name="Y" value="[^"]*" />\s*'
                     r'<Property name="Z" value="[^"]*" />\s*<Property name="W" value="[^"]*" />' % uniform)
    assert pat.search(m), uniform
    x, y, z, w = vals
    return pat.sub(lambda g: g.group(1) + f'<Property name="X" value="{x:.8f}" />\n\t\t\t\t<Property name="Y" value="{y:.6f}" />'
                   f'\n\t\t\t\t<Property name="Z" value="{z:.6f}" />\n\t\t\t\t<Property name="W" value="{w:.6f}" />', m, count=1)
def _drop_flag(m, flag):
    m2 = re.sub(r'\s*<Property name="Flags" value="TkMaterialFlags" _index="\d+">\s*<Property name="MaterialFlag" value="%s" />\s*</Property>' % flag, "", m)
    assert m2 != m, flag
    k = [0]
    def renum(g):
        s = g.group(0); s = re.sub(r'_index="\d+"', f'_index="{k[0]}"', s); k[0] += 1; return s
    return re.sub(r'<Property name="Flags" value="TkMaterialFlags" _index="\d+">', renum, m2)
def _sampler(m, name, **props):
    blk = re.search(r'<Property name="Name" value="%s" />.*?</Property>\s*</Property>' % name, m, re.S)
    assert blk, name
    b = blk.group(0)
    for k, v in props.items():
        b2 = re.sub(r'(<Property name="%s" value=")[^"]*' % k, r'\g<1>' + v, b, count=1); assert b2 != b or v in b, (name, k); b = b2
    return m[:blk.start()] + b + m[blk.end():]

def materials():
    rd = lambda rel: open(C.mxml_of(rel)).read(); out = {}
    t = TEX_DIR + C.PREFIX
    m = rd(C.COCKPIT + "plasticgrain_mat.material.mbin")
    m = _sampler(m, "gDiffuseMap", Map=t + "_PALETTE.DDS", UseMipMaps="false", TextureFilterMode="Bilinear")
    m = _sampler(m, "gMasksMap", Map=t + "_PALETTE.MASKS.DDS", UseMipMaps="false", TextureFilterMode="Bilinear")
    m = _sampler(m, "gNormalMap", Map=t + "_FLAT.NORMAL.DDS")
    out[D.LIT] = _rename(m, f"{C.PREFIX}_LIT_MAT")
    g = rd("models/planets/creatures/weird/weirdrig/eggcrystal_mat1.material.mbin")
    g = _drop_flag(g, "_F21_VERTEXCUSTOM")
    g = _sampler(g, "gDiffuseMap", Map=t + "_GHOST.DDS"); g = _sampler(g, "gMasksMap", Map=t + "_GHOST.MASKS.DDS")
    g = _sampler(g, "gNormalMap", Map=t + "_FLAT.NORMAL.DDS")
    g = g.replace('<Property name="CastShadow" value="true" />', '<Property name="CastShadow" value="false" />')
    out[D.GHOST] = _rename(g, f"{C.PREFIX}_GHOST_MAT")
    for kind, fps in ((D.CANDLE, CANDLE_FPS), (D.GLOW, GLOW_FPS)):
        u = rd("models/planets/biomes/common/rareresource/ground/robotheads/warningscreen_mat.material.mbin")
        u = _sampler(u, "gDiffuseMap", Map=t + f"_{kind}.DDS", UseMipMaps="false", TextureFilterMode="Bilinear")
        u = _set_vec(u, "gUVScrollStepVec4", (1.0 / FRAMES, 1.0, float(fps), 0.0))
        u = u.replace('<Property name="CastShadow" value="true" />', '<Property name="CastShadow" value="false" />')
        out[kind] = _rename(u, f"{C.PREFIX}_{kind}_MAT")
    os.makedirs(OUT + "build/shared", exist_ok=True)
    for k, txt in out.items():
        p = OUT + "build/shared/" + mat_file(k).replace(".MBIN", ".MXML"); open(p, "w").write(txt); C.mbin(p)

# ---------------------------------------------------------------- the cursed-frigate haze, shrunk to dashboard size
def _float_prop(t, name, fixed=None, lo=None, hi=None, authoring=None):
    pat = re.compile(r'(<Property name="%s" value="TkEmitterFloatProperty">\s*<Property name="Authoring" value=")(\w+)(" />\s*'
                     r'<Property name="FixedValue" value=")([^"]+)(" />\s*<Property name="MinRandomValue" value=")([^"]+)(" />\s*'
                     r'<Property name="MaxRandomValue" value=")([^"]+)(")' % re.escape(name))
    m = pat.search(t); assert m, name
    g = list(m.groups())
    if authoring is not None: g[1] = authoring
    if fixed is not None: g[3] = "%.6f" % fixed
    if lo is not None: g[5] = "%.6f" % lo
    if hi is not None: g[7] = "%.6f" % hi
    return t[:m.start()] + "".join(g) + t[m.end():]
def _set(t, name, value):
    t2, n = re.subn(r'(<Property name="%s" value=")[^"]*(")' % re.escape(name), r'\g<1>' + value + r'\g<2>', t, count=1); assert n, name; return t2
def _vec(t, name, xyz):
    pat = re.compile(r'(<Property name="%s">\s*<Property name="X" value=")[^"]*(" />\s*<Property name="Y" value=")[^"]*(" />\s*<Property name="Z" value=")[^"]*(")' % re.escape(name))
    m = pat.search(t); assert m, name
    return t[:m.start()] + m.group(1) + "%.6f" % xyz[0] + m.group(2) + "%.6f" % xyz[1] + m.group(3) + "%.6f" % xyz[2] + m.group(4) + t[m.end():]
def _colour(t, name, rgba):
    pat = re.compile(r'(<Property name="%s">\s*<Property name="R" value=")[^"]*(" />\s*<Property name="G" value=")[^"]*(" />\s*'
                     r'<Property name="B" value=")[^"]*(" />\s*<Property name="A" value=")[^"]*(")' % re.escape(name))
    m = pat.search(t); assert m, name
    v = ["%.6f" % x for x in rgba]
    return t[:m.start()] + m.group(1) + v[0] + m.group(2) + v[1] + m.group(3) + v[2] + m.group(4) + v[3] + m.group(5) + t[m.end():]

def particles():
    out = OUT + "build/shared/"
    # HAZE: soft green cloud puffs drifting low around the figurine (from the ghost ship's CloudGlow)
    h = open(C.mxml_of(C.GHOSTFX + "cloudglow.particle.mbin")).read()
    h = _set(h, "MaxCount", "24")
    h = _float_prop(h, "EmissionRate", fixed=2.2)
    h = _float_prop(h, "ParticleLife", lo=4.0, hi=6.0)
    h = _float_prop(h, "ParticleSpeedMultiplier", authoring="RandomRangeFloat", lo=0.004, hi=0.012)
    h = _vec(h, "SpawnOffsetParams", (0.0, 0.0, 0.045))
    h = _float_prop(h, "GeneralSize", lo=0.035, hi=0.06, fixed=0.05)
    h = _colour(h, "ColourStart", (0.40, 0.95, 0.62, 0.0)); h = _colour(h, "ColourMiddle", (0.40, 0.95, 0.62, 0.55)); h = _colour(h, "ColourEnd", (0.30, 0.80, 0.55, 0.0))
    # MOTES: little glowing sparks rising slowly (from the ghost ship's Plasma)
    p = open(C.mxml_of(C.GHOSTFX + "plasma.particle.mbin")).read()
    p = _set(p, "MaxCount", "20")
    p = _float_prop(p, "EmissionRate", fixed=2.5)
    p = _float_prop(p, "ParticleLife", lo=3.0, hi=5.0)
    p = _float_prop(p, "ParticleSpeedMultiplier", authoring="RandomRangeFloat", lo=0.01, hi=0.025)
    p = _vec(p, "SpawnOffsetParams", (0.0, 0.0, 0.05))
    p = _float_prop(p, "GeneralSize", authoring="RandomRangeFloat", lo=0.003, hi=0.006, fixed=0.005)
    p = _colour(p, "ColourMiddle", (0.55, 1.0, 0.75, 0.9))
    for name, txt in (("HAZE", h), ("MOTES", p)):
        txt = _set(txt, "Minimum", "0.000000"); txt = _set(txt, "Maximum", "0.000000")          # CameraDistanceFade off (as the cockpit's own smoke)
        # soft-particle fade: alpha scales with (depth behind the particle) x strength. The ghost ship's 0.1 is for 100 m clouds;
        # 2-4 cm above the dashboard needs a sharp fade or the whole puff is faded out (the cockpit's smoke uses 5)
        txt = _set(txt, "SoftFadeStrength", "40.000000"); txt = _set(txt, "MaxRenderDistance", "60.000000")
        txt = _set(txt, "MaxSpawnDistance", "60.000000")
        txt = _set(txt, "EmitterSpreadAngle", "50.000000")                                       # mostly upward
        pp = out + fx_data(name).replace(".MBIN", ".MXML"); open(pp, "w").write(txt); C.mbin(pp)
        mt = open(C.mxml_of(C.GHOSTFX + FX[name] + ".material.mbin")).read()
        mt = _rename(mt, f"{C.PREFIX}_{name}")
        pm = out + fx_mat(name).replace(".MBIN", ".MXML"); open(pm, "w").write(mt); C.mbin(pm)

def emitter_node(name, kind, at, tmpl):
    n = copy.deepcopy(tmpl)
    props = {c.get("name"): c for c in n}
    props["Name"].set("value", name); props["Type"].set("value", "EMITTER")
    if "NameHash" in props: props["NameHash"].set("value", "0")          # game effect scenes leave it 0; don't reuse the template's
    for c in props["Transform"]:
        nm = c.get("name"); v = {"TransX": at[0], "TransY": at[1], "TransZ": at[2]}.get(nm, 1.0 if nm.startswith("Scale") else 0.0)
        c.set("value", "%.6f" % v)
    attrs = props["Attributes"]
    for e in list(attrs): attrs.remove(e)
    for i, (k, v) in enumerate((("MATERIAL", SHARED_DIR + fx_mat(kind)), ("DATA", SHARED_DIR + fx_data(kind).replace(".MBIN", ".MXML")))):
        a = ET.SubElement(attrs, "Property", {"name": "Attributes", "value": "TkSceneNodeAttributeData", "_index": str(i)})
        ET.SubElement(a, "Property", {"name": "Name", "value": k}); ET.SubElement(a, "Property", {"name": "Value", "value": v})
    if "Children" in props:
        for e in list(props["Children"]): props["Children"].remove(e)
    return n

# ---------------------------------------------------------------- meshes
def cyl_uv(P):
    u = (np.arctan2(P[:, 2], P[:, 0]) / (2 * np.pi)) % 1 * 2; v = P[:, 1] / 0.03
    return np.stack([u, v], 1)

def build_meshes(key):
    parts, pivot = mesher.figure(key)
    o = np.array(T["origin"]); bt = np.array(T["body_root_t"])
    slots = {}; preview = []
    for grp, slot_names in (("head", HEAD_SLOTS), ("body", BODY_SLOTS)):
        kinds = [k for k in KINDS if (grp, k) in parts]
        assert len(kinds) <= len(slot_names), (key, grp, kinds)
        for kind, slot in zip(kinds, slot_names):
            Ps, Ns, UVs, Is, VC = [], [], [], [], []; off = 0
            for (P, N, I, sw) in parts[(grp, kind)]:
                if kind == D.LIT: uv = np.tile(swatch_uv(sw), (len(P), 1)); vc = np.tile((np.array(D.PALETTE[sw][0]) / 255) ** 2.2, (len(P), 1))
                elif kind == D.GHOST: uv = cyl_uv(P); vc = np.ones((len(P), 3))
                else: uv = np.tile(strip_uv(), (len(P), 1)); vc = np.ones((len(P), 3))
                Ps.append(P); Ns.append(N); UVs.append(uv); Is.append(I + off); VC.append(vc); off += len(P)
            P = np.vstack(Ps); N = np.vstack(Ns); UV = np.vstack(UVs); I = np.vstack(Is); vc = np.vstack(VC)
            preview.append((grp, kind, P, N, I, vc, pivot))
            Pg = P + o - (bt if grp == "body" else 0)
            slots[slot] = (Pg.astype(np.float32), N, UV, I.astype(np.int64), kind)
    return slots, pivot, preview

def empty_mesh(at):
    P = np.array([at, at, at], np.float32); N = np.array([[0, 1, 0]] * 3, float)
    return P, N, np.full((3, 2), 0.5), np.array([[0, 1, 2]]), D.LIT

def pack_normal(n):
    n = n / np.linalg.norm(n, axis=1, keepdims=True)
    s = np.abs(n).sum(1, keepdims=True); o = n[:, :2] / s
    neg = n[:, 2] < 0
    ox = np.where(neg, (1 - np.abs(o[:, 1])) * np.sign(o[:, 0] + 1e-12), o[:, 0])
    oy = np.where(neg, (1 - np.abs(o[:, 0])) * np.sign(o[:, 1] + 1e-12), o[:, 1])
    qx = np.clip(np.round((ox + 1) * 511.5), 0, 1023).astype(np.uint32)
    qy = np.clip(np.round((oy + 1) * 511.5), 0, 1023).astype(np.uint32)
    return qx | (qy << 10) | (np.uint32(512) << 20) | (np.uint32(3) << 30)

def streams(P, N, UV, I, stride):
    n = len(P); assert n < 65536, n
    if stride == 8:
        vd = np.zeros(n, dtype=[("c", "u1", 4), ("n", "<u4")]); vd["c"] = 255; vd["n"] = pack_normal(N)
    else:
        vd = pack_normal(N).astype("<u4")
    pos = np.zeros((n, 8), np.float32); pos[:, :3] = P; pos[:, 3] = 1; pos[:, 4:6] = UV; pos[:, 7] = 1
    return vd.tobytes(), I.astype("<u2").tobytes(), pos.astype("<f2").tobytes()

def fix_position_counts(path, ds):
    b = bytearray(open(path, "rb").read())
    for k, d in enumerate(ds):
        at = 0x58 + 0x48 * k
        cur = struct.unpack_from("<I", b, at)[0]
        assert cur in (len(d["vb"]) + len(d["ib"]), len(d["pb"])), f"unexpected layout at mesh {k}: {cur}"
        struct.pack_into("<I", b, at, len(d["pb"]))
    open(path, "wb").write(bytes(b)); return bytes(b)

def scene(fig):
    key, SC = fig["key"], fig["scene"]; SCENE_PATH = SCENE_DIR + SC
    meshes, pivot_m, preview = build_meshes(key)
    import pickle; pickle.dump(preview, open(OUT + f"{key}_meshes.pkl", "wb"))
    for name in HEAD_SLOTS + BODY_SLOTS:
        if name not in meshes:
            ref = meshes["POLOHEAD"][0].mean(0) if "HEAD" in name else meshes["POLOMODEL"][0].mean(0)
            meshes[name] = empty_mesh(ref)
    base = C.BOB + C.SCENE_LC
    GEO_DATA = C.mxml_of(base + ".geometry.data.mbin.pc"); GEO_HDR = C.mxml_of(base + ".geometry.mbin.pc")
    od = open(GEO_DATA).read(); hd = open(GEO_HDR).read(); order = T["order"]
    STRIDE = int(re.search(r'name="VertexLayout" value="TkVertexLayout">\s*<Property name="ElementCount" value="\d+" />\s*<Property name="Stride" value="(\d+)"', hd).group(1))
    data = {}
    for name in order:
        if name in meshes:
            P, N, UV, I, _ = meshes[name]; vb, ib, pb = streams(P, N, UV, I, STRIDE)
            data[name] = dict(vb=vb, ib=ib, pb=pb, nv=len(P), ni=I.size, aabb=(P.min(0), P.max(0)), P=P)
        else:
            m = re.search(r'IdString" value="%s".*?VertexDataSize" value="(\d+)".*?IndexDataSize" value="(\d+)".*?MeshDataStream" value="([^"]*)".*?MeshPositionDataStream" value="([^"]*)"' % name, od, re.S)
            vs, isz = int(m.group(1)), int(m.group(2)); b = base64.b64decode(m.group(3)); p = base64.b64decode(m.group(4))
            pos = np.frombuffer(p, "<f2").reshape(-1, 8).astype(np.float32)
            data[name] = dict(vb=b[:vs], ib=b[vs:vs + isz], pb=p, nv=vs // STRIDE, ni=isz // 2, aabb=None, P=pos[:, :3])
    bd = OUT + f"build/{SC}/"; os.makedirs(bd, exist_ok=True)
    dt = ET.parse(GEO_DATA)
    arr = [e for e in dt.getroot() if e.get("name") == "StreamDataArray"][0]
    for ent in arr:
        props = {c.get("name"): c for c in ent}; d = data[props["IdString"].get("value")]
        props["VertexDataSize"].set("value", str(len(d["vb"]))); props["VertexPositionDataSize"].set("value", str(len(d["pb"])))
        props["IndexDataSize"].set("value", str(len(d["ib"])))
        props["MeshDataStream"].set("value", base64.b64encode(d["vb"] + d["ib"]).decode())
        props["MeshPositionDataStream"].set("value", base64.b64encode(d["pb"]).decode())
    dpath = bd + f"{SC}.GEOMETRY.DATA.MXML"; dt.write(dpath, encoding="utf-8", xml_declaration=True); C.mbin(dpath)
    raw = fix_position_counts(bd + f"{SC}.GEOMETRY.DATA.MBIN.PC", [data[n] for n in order])
    ht = ET.parse(GEO_HDR); hp = {c.get("name"): c for c in ht.getroot()}
    ohull = [tuple(float(x.find("./Property[@name='%s']" % c).get("value")) for c in "XYZ") for x in hp["BoundHullVerts"]]
    ohs = [int(x.get("value")) for x in hp["BoundHullVertSt"]]; ohe = [int(x.get("value")) for x in hp["BoundHullVertEd"]]
    starts, ends, hst, hed, hull, batch_starts = [], [], [], [], [], []; v0 = 0; bi = 0
    for k, name in enumerate(order):
        d = data[name]; starts.append(v0); ends.append(v0 + d["nv"] - 1); v0 += d["nv"]; batch_starts.append(bi); bi += d["ni"]
        if d["aabb"] is None: pts = ohull[ohs[k]:ohe[k]]
        else:
            lo, hi = d["aabb"]; pts = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
        hst.append(len(hull)); hull += pts; hed.append(len(hull))
    def set_list(prop, vals):
        for e, v in zip(prop, vals): e.set("value", str(v))
    hp["VertexCount"].set("value", str(v0)); hp["IndexCount"].set("value", str(bi))
    set_list(hp["MeshVertRStart"], starts); set_list(hp["MeshVertREnd"], ends)
    set_list(hp["BoundHullVertSt"], hst); set_list(hp["BoundHullVertEd"], hed)
    tmpl = copy.deepcopy(hp["BoundHullVerts"][0])
    for e in list(hp["BoundHullVerts"]): hp["BoundHullVerts"].remove(e)
    for i, (x, y, z) in enumerate(hull):
        e = copy.deepcopy(tmpl); e.set("_index", str(i))
        for c, v in zip("XYZ", (x, y, z)): e.find("./Property[@name='%s']" % c).set("value", "%.6f" % v)
        e.find("./Property[@name='W']").set("value", "1.000000"); hp["BoundHullVerts"].append(e)
    aabbs = {}
    for k, (emin, emax) in enumerate(zip(hp["MeshAABBMin"], hp["MeshAABBMax"])):
        name = order[k]; d = data[name]
        if d["aabb"] is not None:
            for c, i in zip("XYZ", range(3)):
                emin.find("./Property[@name='%s']" % c).set("value", "%.6f" % d["aabb"][0][i])
                emax.find("./Property[@name='%s']" % c).set("value", "%.6f" % d["aabb"][1][i])
        aabbs[name] = [float(emin.find("./Property[@name='%s']" % c).get("value")) for c in "XYZ"] + \
                      [float(emax.find("./Property[@name='%s']" % c).get("value")) for c in "XYZ"]
    for ent in hp["StreamMetaDataArray"]:
        props = {c.get("name"): c for c in ent}; d = data[props["IdString"].get("value")]
        vio = raw.find(d["vb"] + d["ib"]); po = raw.find(d["pb"]); assert vio > 0 and po > 0
        props["VertexDataSize"].set("value", str(len(d["vb"]))); props["VertexDataOffset"].set("value", str(vio))
        props["VertexPositionDataSize"].set("value", str(len(d["pb"]))); props["VertexPositionDataOffset"].set("value", str(po))
        props["IndexDataSize"].set("value", str(len(d["ib"]))); props["IndexDataOffset"].set("value", str(len(d["vb"])))
    hpath = bd + f"{SC}.GEOMETRY.MXML"; ht.write(hpath, encoding="utf-8", xml_declaration=True); C.mbin(hpath)
    # ---- scene
    st = ET.parse(C.mxml_of(base + ".scene.mbin")); sroot = st.getroot()
    def walk(e):
        props = {c.get("name"): c for c in e if c.tag == "Property"}
        yield e, props
        if "Children" in props:
            for c in props["Children"]: yield from walk(c)
    k_of = {n: i for i, n in enumerate(order)}
    pivot = T["origin"][1] + pivot_m
    for node, props in walk(sroot):
        typ = props["Type"].get("value"); name = props["Name"].get("value")
        if typ == "MODEL":
            props["Name"].set("value", SCENE_PATH)
            for a in props["Attributes"]:
                ap = {c.get("name"): c for c in a}
                if ap["Name"].get("value") == "GEOMETRY": ap["Value"].set("value", SCENE_PATH + ".GEOMETRY.MBIN")
        if typ == "JOINT" and name == T["head_joint"]:
            [c for c in props["Transform"] if c.get("name") == "TransX"][0].set("value", "%.6f" % pivot)
        if typ != "MESH": continue
        uname = name.upper()
        if uname not in k_of: continue
        k = k_of[uname]; d = data[uname]
        attrs = {}
        for a in props["Attributes"]:
            ap = {c.get("name"): c for c in a}; attrs[ap["Name"].get("value")] = ap["Value"]
        vals = {"BATCHSTARTPHYSI": batch_starts[k], "VERTRSTARTPHYSI": starts[k], "VERTRENDPHYSICS": ends[k],
                "BATCHSTARTGRAPH": 0, "BATCHCOUNT": d["ni"], "VERTRSTARTGRAPH": 0, "VERTRENDGRAPHIC": d["nv"] - 1,
                "BOUNDHULLST": hst[k], "BOUNDHULLED": hed[k]}
        for c, v in zip(["AABBMINX", "AABBMINY", "AABBMINZ", "AABBMAXX", "AABBMAXY", "AABBMAXZ"], aabbs[uname]): vals[c] = "%.6f" % v
        if uname in meshes: vals["MATERIAL"] = mat_path(meshes[uname][4])
        for key_, v in vals.items(): attrs[key_].set("value", str(v))
        if uname == T["head_root"]:
            for c in props["Transform"]:
                c.set("value", "1.000000" if c.get("name").startswith("Scale") else "0.000000")
            [c for c in props["Transform"] if c.get("name") == "TransY"][0].set("value", "%.6f" % -pivot)
    # the haze + motes: two emitters on the pedestal, children of the scene root
    rp = {c.get("name"): c for c in sroot if c.tag == "Property"}
    tmpl = list(rp["Children"])[0]
    o = T["origin"]
    for i, (nm, kind, y) in enumerate((("HWHaze", "HAZE", 0.012), ("HWMotes", "MOTES", 0.02))):
        e = emitter_node(nm, kind, (o[0], o[1] + y, o[2]), tmpl); e.set("_index", str(len(list(rp["Children"])))); rp["Children"].append(e)
    spath = bd + f"{SC}.SCENE.MXML"; st.write(spath, encoding="utf-8", xml_declaration=True); C.mbin(spath)
    print("%-12s verts=%6d tris=%6d pivot=%.4f m" % (key, v0, bi // 3, pivot_m))
    for n in order: print("    %-14s %6d verts  %s" % (n, data[n]["nv"], meshes[n][4] if n in meshes else "(game pedestal)"))

def main():
    os.makedirs(OUT + "build", exist_ok=True)
    for f in C.FIGS: scene(f)
    materials(); particles(); textures()

if __name__ == "__main__":
    main()

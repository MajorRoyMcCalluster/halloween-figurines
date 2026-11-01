"""Release checks for the built Halloween Figurines mod folder."""
import os, re, sys, subprocess, shutil, struct, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C, model as M, tables, designs as D

def run(m):
    ok = True; n = 0
    def check(cond, msg):
        nonlocal ok, n; n += 1
        if not cond: ok = False; print("FAIL:", msg)
    tmp = tempfile.mkdtemp()
    def decompile(p):
        q = os.path.join(tmp, os.path.basename(p)); shutil.copy(p, q); C.mbin(q)
        for ext in (".MBIN.PC", ".MBIN"):
            if q.endswith(ext): return open(q[: -len(ext)] + ".MXML").read()
    G = os.path.join(m, M.SCENE_DIR.replace("\\", "/")); S = os.path.join(m, M.SHARED_DIR.replace("\\", "/"))
    # shared materials + particles
    for k in M.KINDS: check(os.path.isfile(S + M.mat_file(k)), "missing material " + M.mat_file(k))
    for nm in M.FX: check(os.path.isfile(S + M.fx_mat(nm)) and os.path.isfile(S + M.fx_data(nm)), "missing particle " + nm)
    for k in M.KINDS:
        t = decompile(S + M.mat_file(k))
        for tex in re.findall(r'"Map" value="([^"]+)"', t):
            check(os.path.isfile(os.path.join(m, tex)), f"{k}: texture missing in mod: {tex}")
        if k in (D.CANDLE, D.GLOW):
            check("_F13_UV_EFFECT" in t and ("%.6f" % (1 / M.FRAMES)) in t, k + " flipbook settings")
            check(struct.pack("<f", 1 / M.FRAMES) in open(S + M.mat_file(k), "rb").read() and (M.FRAMES & (M.FRAMES - 1)) == 0, k + " step exact")
        if k == D.GHOST: check('"Translucent"' in t and "_F21_VERTEXCUSTOM" not in t, "ghost material")
        if k == D.GLOWTEX: check("_F07_UNLIT" in t and "_F13_UV_EFFECT" not in t, "Lantern Jack's cracks: unlit, no flipbook")
        if k == D.BONETEX: check(all(s in t for s in ("_JACKBONE.DDS", "_JACKBONE.NORMAL.DDS", "_JACKBONE.MASKS.DDS")), "Lantern Jack's bone maps")
    for nm in M.FX:
        t = decompile(S + M.fx_data(nm))
        size = re.search(r'name="GeneralSize" value="TkEmitterFloatProperty">.*?MaxRandomValue" value="([^"]+)"', t, re.S)
        check(size and float(size.group(1)) < 0.1, nm + " particles still frigate-sized")
        mt = decompile(S + M.fx_mat(nm))
        for tex in re.findall(r'"Map" value="([^"]+)"', mt): check(tex.startswith("TEXTURES/EFFECTS/"), nm + " unexpected texture " + tex)
    # each figurine
    for f in C.FIGS:
        sc = f["scene"]
        for fn in (f"{sc}.SCENE.MBIN", f"{sc}.GEOMETRY.MBIN.PC", f"{sc}.GEOMETRY.DATA.MBIN.PC"): check(os.path.isfile(G + fn), "missing " + fn)
        st = decompile(G + f"{sc}.SCENE.MBIN")
        check("POLOBOBBLEHEAD.GEOMETRY" not in st, sc + " still points at the Polo geometry")
        for ref in re.findall(r'value="(MODELS\\[^"]+\.M(?:BIN|XML))"', st):
            if "BOBBLEHEADS" in ref and ("HWF" in ref or sc in ref):
                p = ref.replace("\\", "/").replace(".GEOMETRY.MBIN", ".GEOMETRY.MBIN.PC").replace(".PARTICLE.MXML", ".PARTICLE.MBIN")
                check(os.path.isfile(os.path.join(m, p)), f"{sc}: scene ref missing: {ref}")
        check(st.count('value="EMITTER"') == 2, sc + " haze emitters")
        import pickle; meshes = pickle.load(open(os.path.join(C.WORK, "out", f"{f['key']}_meshes.pkl"), "rb"))
        for (grp, kind, P, N, I, vc, piv, *_) in meshes:
            check(len(P) < 65536 and I.max() < len(P) and np.isfinite(P).all() and np.isfinite(N).all(), f"{sc} {grp} {kind} mesh")
            check(P[:, 1].min() > -0.002 and P[:, 1].max() < 0.2 and np.abs(P[:, [0, 2]]).max() < 0.085, f"{sc} {grp} {kind} outside the pedestal area")
        # vertex budget: a 42k-vertex mesh on the Box-Bot Traveller filled the whole screen with red shards in game
        check(all(len(m[2]) <= 20000 for m in meshes), f"{sc}: a mesh is over 20,000 vertices")
        check(sum(len(m[2]) for m in meshes) <= 32000, f"{sc}: over 32,000 vertices in total")
    # game-data merge files
    ours = set()
    for f in C.FIGS: ours |= {f["tech"], f["product"], f["reward"], *f["keys"]}
    for rel in tables.FILES:
        p = os.path.join(m, rel); check(os.path.isfile(p), "missing " + rel)
        if not os.path.isfile(p): continue
        if rel.endswith(".MBIN"):
            x = decompile(p)
            check(all(f["tech"] in x and f["scene"] in x for f in C.FIGS) and "BOXBOTBOBBLEHEAD" in x and "ATLASBOBBLEHEAD" in x, "figurine list entries")
            check(x.count('value="GcCustomisationBobbleHead"') == 8 + len(C.OTHER_FIGURINES) + len(C.FIGS), "figurine list length")
            continue
        t = open(p, encoding="utf-8").read()
        tops = re.findall(r'^\t\t<Property name="\w+" value="\w+"(?: _id="([^"]*)")?>', t, re.M)
        check(len(tops) > 0 and all(i in ours for i in tops), rel + " top-level entries need _id with our own IDs")
        q = os.path.join(tmp, os.path.basename(rel).replace(".EXML", ".MXML")); shutil.copy(p, q)
        r = subprocess.run([C.find_mbincompiler(), "-y", "-q", q], capture_output=True, text=True)
        check(r.returncode == 0, rel + " does not compile")
    for f in C.FIGS:
        for kind in ("SPECIAL", "HERO"):
            check(os.path.isfile(os.path.join(m, "TEXTURES/UI/FRONTEND/ICONS/SPECIALSHOP", f"{kind}.{f['icon']}.DDS")), f"icon {kind} {f['icon']}")
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"{n} checks, {'all passed' if ok else 'FAILURES'}")
    return ok

if __name__ == "__main__":
    sys.exit(0 if run(sys.argv[1] if len(sys.argv) > 1 else os.path.join(C.WORK, "mod", C.MOD_FOLDER)) else 1)

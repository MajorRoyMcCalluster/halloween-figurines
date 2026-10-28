"""Build the Halloween Figurines mod from your own No Man's Sky install.

    python tools/build.py --game "C:\\Steam\\steamapps\\common\\No Man's Sky" [--install]

Steps: extract the game files it needs (HGPAKtool) -> decompile (MBINCompiler) -> generate the three figurines,
their materials, textures, haze particles, icons and the game-data entries -> run the checks -> zip into dist/.
Options: --extracted DIR  use already-extracted game files (lower-case game paths) instead of the .pak files
         --skip-extract   reuse work/game from a previous build
         --install        also copy the finished mod into GAMEDATA/MODS
"""
import argparse, os, shutil, subprocess, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

def extract(game, extracted=None):
    dst = os.path.join(C.WORK, "game"); shutil.rmtree(dst, ignore_errors=True); os.makedirs(dst)
    if extracted:
        for rel in C.GAME_FILES:
            src = os.path.join(extracted, rel)
            if not os.path.isfile(src): sys.exit(f"missing in --extracted folder: {rel}")
            os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True); shutil.copy(src, os.path.join(dst, rel))
    else:
        banks = os.path.join(game, "GAMEDATA", "PCBANKS")
        if not os.path.isdir(banks): sys.exit(f"can't find {banks} - pass your No Man's Sky folder with --game")
        filters = [f"-f=*{rel}" for rel in C.GAME_FILES]
        r = subprocess.run([sys.executable, "-c", "from hgpaktool.cli import run; run()", "-U", *filters, "-O", dst, banks],
                           capture_output=True, text=True)
        missing = [rel for rel in C.GAME_FILES if not os.path.isfile(os.path.join(dst, rel))]
        if missing: print(r.stdout, r.stderr); sys.exit("couldn't extract: " + ", ".join(missing))
    for rel in C.GAME_FILES:
        C.mbin(C.game_path(rel))
        if not os.path.isfile(C.mxml_of(rel)): sys.exit("decompile failed: " + rel)
    print(f"extracted and decompiled {len(C.GAME_FILES)} game files")

def assemble():
    import model as M, tables, icons
    out = os.path.join(C.WORK, "out")
    m = os.path.join(C.WORK, "mod", C.MOD_FOLDER); shutil.rmtree(os.path.dirname(m), ignore_errors=True)
    G = os.path.join(m, M.SCENE_DIR.replace("\\", "/")); os.makedirs(G)
    for f in C.FIGS:
        sc = f["scene"]
        for fn in (f"{sc}.SCENE.MBIN", f"{sc}.GEOMETRY.MBIN.PC", f"{sc}.GEOMETRY.DATA.MBIN.PC"):
            shutil.copy(os.path.join(out, "build", sc, fn), G)
    S = os.path.join(m, M.SHARED_DIR.replace("\\", "/")); os.makedirs(S)
    for fn in os.listdir(os.path.join(out, "build", "shared")):
        if fn.endswith(".MBIN"): shutil.copy(os.path.join(out, "build", "shared", fn), S)
    T = os.path.join(m, M.TEX_DIR); os.makedirs(T)
    for fn in os.listdir(os.path.join(out, "tex")): shutil.copy(os.path.join(out, "tex", fn), T)
    icons.write(os.path.join(m, "TEXTURES/UI/FRONTEND/ICONS/SPECIALSHOP"))
    tables.write(m)
    readme = open(os.path.join(C.REPO, "tools", "mod_readme.txt"), encoding="utf-8").read()
    readme = readme.format(name=C.MOD_NAME, version=C.VERSION, author=C.AUTHOR, folder=C.MOD_FOLDER, price=C.PRICE_QS,
                           items="\n".join(f"  - {f['name_l']}" for f in C.FIGS))
    open(os.path.join(m, "README.txt"), "w", encoding="utf-8", newline="\r\n").write(readme)
    return m

def package(m):
    os.makedirs(C.DIST, exist_ok=True)
    z = os.path.join(C.DIST, f"{C.RELEASE_NAME}-{C.VERSION}.zip")
    if os.path.exists(z): os.remove(z)
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(m):
            for f in sorted(files):
                p = os.path.join(root, f); zf.write(p, os.path.relpath(p, os.path.dirname(m)))
    return z

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game"); ap.add_argument("--extracted"); ap.add_argument("--skip-extract", action="store_true")
    ap.add_argument("--install", action="store_true"); ap.add_argument("--no-check", action="store_true")
    a = ap.parse_args()
    if not a.skip_extract:
        if not (a.game or a.extracted): ap.error("pass --game (or --extracted, or --skip-extract)")
        extract(a.game, a.extracted)
    import model; model.main()
    m = assemble()
    if not a.no_check:
        import check
        if not check.run(m): sys.exit("checks failed - nothing was packaged")
    z = package(m); print("built:", z)
    if a.install:
        if not a.game: sys.exit("--install needs --game")
        dst = os.path.join(a.game, "GAMEDATA", "MODS", C.MOD_FOLDER)
        shutil.rmtree(dst, ignore_errors=True); shutil.copytree(m, dst); print("installed:", dst)

if __name__ == "__main__":
    main()

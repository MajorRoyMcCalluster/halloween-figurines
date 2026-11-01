"""Shared settings and helpers for the Halloween Figurines build."""
import os, shutil, subprocess, sys

VERSION = "1.0.1"
AUTHOR = "MajorRoyMcCalluster"
MOD_NAME = "Halloween Figurines"
MOD_FOLDER = "HalloweenFigurines"                # folder inside GAMEDATA/MODS
RELEASE_NAME = "Halloween Figurines"
PREFIX = "HWF"                                   # file prefix for our materials / textures
LOC = "NMS_LOC7"                                 # our text file name (merged by the game, shared with Box-Bot)
PRICE_QS = 3200                                  # Quicksilver, same as the game's own figurines
SHOP_NUMBER, MISSION_TIER = 1, -1                # first shop page, no tier requirement
BONUS = ("Ship_Launcher_TakeOffCost", "0.900000")

# ---- the new figurines (scene ids: 16 characters max; item ids: 15 max)
FIGS = [
    dict(key="ghost", scene="HWGHOSTBOBBLE", tech="T_BOBBLE_GHOST", product="BOBBLE_GHOST", reward="R_BOBBLE_GHOST",
         icon="BOBBLEGHOST", name="BOO FIGURINE", name_l="Boo Figurine",
         desc="A little sheet ghost, glowing faintly, waving hello and carrying a jack-o'-lantern pail of sweets. A cursed green haze "
              "drifts around it, the same ghost-light that clings to haunted frigates.\n\nInstall to an "
              "<TECHNOLOGY>Inventory Slot<> to decorate your ship's interior."),
    dict(key="lanternjack", scene="HWJACKBOBBLE", tech="T_BOBBLE_JACK", product="BOBBLE_JACK", reward="R_BOBBLE_JACK",
         icon="BOBBLEJACK", name="LANTERN JACK FIGURINE", name_l="Lantern Jack Figurine",
         desc="A skeleton with a grinning jack-o'-lantern for a head, holding up a glowing lantern to light the way "
              "between the stars and leaning on a crooked staff. Its pumpkin head nods along with every manoeuvre."
              "\n\nInstall to an <TECHNOLOGY>Inventory Slot<> to decorate your ship's interior."),
]
for f in FIGS:
    f["keys"] = ("UI_" + f["product"] + "_NAME", "UI_" + f["product"] + "_NAME_L", "UI_" + f["product"] + "_DESC")
    assert len(f["scene"]) <= 16 and all(len(f[k]) <= 15 for k in ("tech", "product", "reward")), f

# other figurines of ours that share the game's figurine list (it ships as one complete file in each mod)
OTHER_FIGURINES = [("T_BOBBLE_BOXBOT", "BOXBOTBOBBLEHEAD"), ("T_BOBBLE_BOXTRV", "BOXBOTTRAVELLER"), ("T_BOBBLE_WRETCH", "WRETCHBOBBLE")]

# ---- the game figurine whose scene we start from (its joints, wobble set-up and pedestal are reused)
TEMPLATE = dict(
    scene="POLOBOBBLEHEAD",
    order=["POLOHEAD", "SUB1POLOHEAD", "SUB2POLOHEAD", "SUB3POLOHEAD", "POLOMODEL", "SUB1POLOMODEL", "SUB2POLOMODEL",
           "SUB3POLOMODEL", "SUB4POLOMODEL", "SUB5POLOMODEL", "SUB6POLOMODEL", "SUB7POLOMODEL"],
    head_root="POLOHEAD", head_joint="Headjnt",
    body_root="POLOMODEL", body_root_t=(-0.005799, 0.079075, -0.011222),
    pedestal=["SUB6POLOMODEL", "SUB7POLOMODEL"],     # kept: the game's own pedestal and its green glow ring
    origin=(0.0, 0.0192, -0.011222),                 # centre of the pedestal top, in figurine space
)
SCENE_LC = TEMPLATE["scene"].lower()

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(REPO, "work")
DIST = os.path.join(REPO, "dist")

BOB = "models/planets/biomes/common/buildings/props/bobbleheads/"
COCKPIT = "models/common/spacecraft/fighters/cockpit/cockpitcommon_interior/"
GHOSTFX = "models/effects/space/ghostshipatmos/"
GAME_FILES = [
    BOB + SCENE_LC + ".scene.mbin", BOB + SCENE_LC + ".geometry.mbin.pc", BOB + SCENE_LC + ".geometry.data.mbin.pc",
    COCKPIT + "plasticgrain_mat.material.mbin",                                   # lit template (our palette maps)
    "models/planets/biomes/common/rareresource/ground/robotheads/warningscreen_mat.material.mbin",   # unlit flipbook
    "models/planets/creatures/weird/weirdrig/eggcrystal_mat1.material.mbin",      # translucent template (ghost)
    GHOSTFX + "cloudglow.material.mbin", GHOSTFX + "cloudglow.particle.mbin",     # the cursed-frigate haze
    GHOSTFX + "plasma.material.mbin", GHOSTFX + "plasma.particle.mbin",           # ... and its glowing motes
    "metadata/reality/tables/nms_reality_gctechnologytable.mbin",
    "metadata/reality/tables/nms_reality_gcproducttable.mbin",
    "metadata/reality/tables/rewardtable.mbin",
    "metadata/reality/tables/purchaseablespecials.mbin",
    "metadata/gamestate/playerdata/bobbleheadcustomisationdata.mbin",
]

def game_path(rel): return os.path.join(WORK, "game", rel)
def mxml_of(rel):
    p = game_path(rel)
    for ext in (".mbin.pc", ".mbin"):
        if p.endswith(ext): return p[: -len(ext)] + ".MXML"
    raise ValueError(rel)

def find_mbincompiler():
    cand = [os.environ.get("MBINCOMPILER", "")]
    here = os.path.join(REPO, "tools", "bin")
    cand += [os.path.join(here, n) for n in ("MBINCompiler.exe", "MBINCompiler-linux", "MBINCompiler")]
    cand += [shutil.which(n) or "" for n in ("MBINCompiler", "MBINCompiler.exe", "MBINCompiler-linux")]
    for c in cand:
        if c and os.path.isfile(c): return c
    sys.exit("MBINCompiler not found. Put MBINCompiler.exe in tools/bin/ or set the MBINCOMPILER environment variable.")

def mbin(path, quiet=True):
    r = subprocess.run([find_mbincompiler(), "-y"] + (["-q"] if quiet else []) + [path], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr); sys.exit("MBINCompiler failed on " + path)

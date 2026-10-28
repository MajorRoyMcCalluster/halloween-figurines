"""Game-data patches that add the three Halloween figurines as new items (partial EXML files merged by the game).

Each new entry carries an _id with its own new ID: the game finds no match and adds it, so other mods that patch
the same tables keep working. The figurine list has no ID field, so it ships complete (as an MBIN): the game's own
figurines + Box-Bot (from our Cockpit Robot mod) + these three. It's harmless if Box-Bot isn't installed.

  technology table   T_BOBBLE_*      the installable figurines (ship tech, like the game's figurines)
  product table      BOBBLE_*        the Quicksilver shop items
  reward table       R_BOBBLE_*      buying an item teaches its tech
  purchaseable specials              puts the items on sale at the Quicksilver Synthesis Companion
  figurine list      T_BOBBLE_* -> *.SCENE.MBIN   which model the dashboard shows
  language NMS_LOC7  names and descriptions
Every entry is copied from the Atlas Figurine's own entry, so every field matches the current game version.
"""
import os, re, sys, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

TB = "metadata/reality/tables/"
ICON_DIR = "TEXTURES/UI/FRONTEND/ICONS/SPECIALSHOP/"
SCENE_FILE = "MODELS/PLANETS/BIOMES/COMMON/BUILDINGS/PROPS/BOBBLEHEADS/%s.SCENE.MBIN"

def entry(text, list_name, value, ident):
    m = re.search(r'(\t*)<Property name="%s" value="%s" _id="%s">.*?\n\1</Property>' % (list_name, value, ident), text, re.S)
    assert m, f"{ident} not found - the game data changed"
    return m.group(0), m.group(1)

def reindent(block, ind_from, ind_to):
    return "\n".join(ind_to + l[len(ind_from):] if l.startswith(ind_from) else l for l in block.split("\n"))

def wrap(template, list_name, bodies):
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            f'<!-- {C.MOD_NAME} v{C.VERSION}: adds the Halloween figurines (new entries only; merged into the game\'s table) -->\n'
            f'<Data template="{template}">\n\t<Property name="{list_name}">\n' + "\n".join(bodies) + '\n\t</Property>\n</Data>\n')

def _icon(f, kind): return ICON_DIR + f"{kind}.{f['icon']}.DDS"

def tech():
    t = open(C.mxml_of(TB + "nms_reality_gctechnologytable.mbin")).read()
    base, ind = entry(t, "Table", "GcTechnology", "T_BOBBLE_ATLAS"); out = []
    for f in C.FIGS:
        b = base.replace("T_BOBBLE_ATLAS", f["tech"]).replace("UI_BOBBLE_ATLAS_NAME_L", f["keys"][1]) \
                .replace("UI_BOBBLE_ATLAS_NAME", f["keys"][0]).replace("UI_BOBBLE_ATLAS_DESC", f["keys"][2])
        b = b.replace("TEXTURES/UI/FRONTEND/ICONS/SPECIALSHOP/SPECIAL.BOBBLEATLAS.DDS", _icon(f, "SPECIAL"))
        sb = re.search(r'<Property name="StatBonuses">.*?\n\t*</Property>\n(?=\t*<Property name="RequiredTech")', b, re.S); assert sb
        new = re.sub(r'(<Property name="StatsType" value=")[^"]*', r'\g<1>' + C.BONUS[0], sb.group(0), count=1)
        new = re.sub(r'(<Property name="Bonus" value=")[^"]*', r'\g<1>' + C.BONUS[1], new, count=1)
        b = b.replace(sb.group(0), new)
        assert "ATLAS" not in b, f["tech"]
        out.append(reindent(b, ind, "\t\t"))
    return wrap("cGcTechnologyTable", "Table", out)

def product():
    t = open(C.mxml_of(TB + "nms_reality_gcproducttable.mbin")).read()
    base, ind = entry(t, "Table", "GcProductData", "BOBBLE_ATLAS"); out = []
    for f in C.FIGS:
        b = base.replace('"BOBBLE_ATLAS"', '"%s"' % f["product"]).replace("UI_BOBBLE_ATLAS_NAME_L", f["keys"][1]) \
                .replace("UI_BOBBLE_ATLAS_NAME", f["keys"][0]).replace("UI_BOBBLE_ATLAS_DESC", f["keys"][2])
        b = b.replace("TEXTURES/UI/FRONTEND/ICONS/SPECIALSHOP/SPECIAL.BOBBLEATLAS.DDS", _icon(f, "SPECIAL"))
        b = b.replace("TEXTURES/UI/FRONTEND/ICONS/SPECIALSHOP/HERO.BOBBLEATLAS.DDS", _icon(f, "HERO"))
        b = b.replace('"R_BOBBLE_ATLAS"', '"%s"' % f["reward"])
        b = re.sub(r'(<Property name="BaseValue" value=")\d+', r'\g<1>%d' % C.PRICE_QS, b, count=1)
        assert "ATLAS" not in b, f["product"]
        out.append(reindent(b, ind, "\t\t"))
    return wrap("cGcProductTable", "Table", out)

def reward():
    t = open(C.mxml_of(TB + "rewardtable.mbin")).read()
    base, ind = entry(t, "SpecialRewardTable", "GcGenericRewardTableEntry", "R_BOBBLE_ATLAS"); out = []
    for f in C.FIGS:
        b = base.replace('"R_BOBBLE_ATLAS"', '"%s"' % f["reward"]).replace('"T_BOBBLE_ATLAS"', '"%s"' % f["tech"])
        assert "ATLAS" not in b; out.append(reindent(b, ind, "\t\t"))
    return wrap("cGcRewardTable", "SpecialRewardTable", out)

def specials():
    t = open(C.mxml_of(TB + "purchaseablespecials.mbin")).read()
    base, ind = entry(t, "Table", "GcPurchaseableSpecial", "BOBBLE_ATLAS"); out = []
    for f in C.FIGS:
        b = base.replace('"BOBBLE_ATLAS"', '"%s"' % f["product"])
        b = re.sub(r'(<Property name="ShopNumber" value=")-?\d+', r'\g<1>%d' % C.SHOP_NUMBER, b)
        b = re.sub(r'(<Property name="MissionTier" value=")-?\d+', r'\g<1>%d' % C.MISSION_TIER, b)
        out.append(reindent(b, ind, "\t\t"))
    return wrap("cGcPurchaseableSpecials", "Table", out)

def bobbleheads():
    """the game's complete list + Box-Bot + ours (written as MXML, compiled to MBIN by write())"""
    t = open(C.mxml_of("metadata/gamestate/playerdata/bobbleheadcustomisationdata.mbin")).read()
    n = t.count('value="GcCustomisationBobbleHead"'); assert n >= 8
    add = [(tech, scene) for tech, scene in C.OTHER_FIGURINES] + [(f["tech"], f["scene"]) for f in C.FIGS]
    body = ""
    for i, (tech, scene) in enumerate(add):
        assert tech not in t
        body += (f'\t\t<Property name="BobbleHeads" value="GcCustomisationBobbleHead" _index="{n + i}">\n'
                 f'\t\t\t<Property name="LinkedTechId" value="{tech}" />\n'
                 '\t\t\t<Property name="BobbleHead" value="TkModelResource">\n'
                 f'\t\t\t\t<Property name="Filename" value="{SCENE_FILE % scene}" />\n'
                 '\t\t\t\t<Property name="Seed" value="0" />\n'
                 '\t\t\t</Property>\n\t\t</Property>\n')
    i = t.rfind('\t</Property>\n</Data>'); assert i > 0
    return t[:i] + body + t[i:]

def esc(s): return html.escape(s, quote=True).replace("&#x27;", "'").replace("\n", "&#xA;")

def language(col):
    o = ['<?xml version="1.0" encoding="utf-8"?>', f'<!-- {C.MOD_NAME} v{C.VERSION}: Halloween figurine text (new entries) -->',
         '<Data template="cTkLocalisationTable">', '\t<Property name="Table">']
    for f in C.FIGS:
        for k, v in zip(f["keys"], (f["name"], f["name_l"], f["desc"])):
            o += [f'\t\t<Property name="Table" value="TkLocalisationEntry" _id="{k}">', f'\t\t\t<Property name="Id" value="{k}" />',
                  f'\t\t\t<Property name="{col}" value="{esc(v)}" />', '\t\t</Property>']
    return "\n".join(o + ['\t</Property>', '</Data>', ''])

FILES = {
    "METADATA/REALITY/TABLES/NMS_REALITY_GCTECHNOLOGYTABLE.EXML": tech,
    "METADATA/REALITY/TABLES/NMS_REALITY_GCPRODUCTTABLE.EXML": product,
    "METADATA/REALITY/TABLES/REWARDTABLE.EXML": reward,
    "METADATA/REALITY/TABLES/PURCHASEABLESPECIALS.EXML": specials,
    "METADATA/GAMESTATE/PLAYERDATA/BOBBLEHEADCUSTOMISATIONDATA.MBIN": bobbleheads,
    f"LANGUAGE/{C.LOC}_ENGLISH.EXML": lambda: language("English"),
    f"LANGUAGE/{C.LOC}_USENGLISH.EXML": lambda: language("USEnglish"),
}

def write(mod_dir):
    for rel, fn in FILES.items():
        p = os.path.join(mod_dir, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        if rel.endswith(".MBIN"):
            x = p[:-5] + ".MXML"; open(x, "w", encoding="utf-8").write(fn()); C.mbin(x); os.remove(x)
            assert os.path.isfile(p), "compile produced nothing for " + rel
        else:
            open(p, "w", encoding="utf-8", newline="\r\n").write(fn())
    return list(FILES)

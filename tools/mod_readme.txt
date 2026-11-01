{name} v{version}  by {author}
============================================================
Adds two NEW Halloween cockpit figurines to No Man's Sky (none of the game's figurines are replaced):
  - Boo: a see-through sheet ghost waving hello, with a glowing jack-o'-lantern pail of sweets
  - Lantern Jack: a skeleton with a grinning jack-o'-lantern head, holding up a glowing lantern and leaning
    on a crooked staff
Each sits on the figurine pedestal with candle-lit jack-o'-lanterns that flicker, and a cursed green haze
rolls around it with glowing motes - the same ghost-light effect the game uses on its haunted frigates,
shrunk down to dashboard size. The heads wobble like the game's own figurines.

INSTALL
  1. Extract the "{folder}" folder into:  No Man's Sky\GAMEDATA\MODS\
  2. In game, buy the figurines for {price} Quicksilver each from the Quicksilver Synthesis Companion on the
     Space Anomaly (near the end of the shop), then install one in your starship's inventory like any other
     figurine. Your cockpit shows one figurine at a time, so remove any other figurine.

UNINSTALL
  Remove the figurines from your ship first, then delete the "{folder}" folder.

COMPATIBILITY
  - The shop, technology, reward and product changes are small merge files (EXML) that only ADD new
    entries, so other mods that change those tables keep working. If a shop mod replaces the whole
    Quicksilver list (e.g. ~Consumerism), this mod must load AFTER it: in Binaries\SETTINGS\GCMODSETTINGS.MXML
    give HALLOWEENFIGURINES a LOWER ModPriority number than that mod (the lowest number loads last and wins).
  - The cockpit figurine list (BOBBLEHEADCUSTOMISATIONDATA.MBIN) is a complete file. It already includes
    the Box-Bot figurines from my Cockpit Robot mod and the Wretch from my Wretch Figurine mod, so they all
    work together. Other mods that replace the figurine list will conflict.
  - Multiplayer: other players without the mod won't see the figurines.
  - Names and descriptions are in English and US English.

CREDITS
  Built with MBINCompiler (monkeyman192 and the NMS modding community) and HGPAKtool.
  The haze uses the game's own ghost-ship particle effect and textures. Happy Halloween!

# Halloween Figurines (No Man's Sky)

Three new Halloween cockpit figurines for No Man's Sky, sold in the Quicksilver shop. No game figurine is replaced.

![The three figurines](nexus/images/00_header.jpg)

| Figurine | |
|---|---|
| **Boo** | A see-through sheet ghost waving hello, with a glowing jack-o'-lantern pail of sweets |
| **Skelly** | A little skeleton sitting on a big grinning jack-o'-lantern, eyes glowing cursed green |
| **Pumpkin-Head** | A scarecrow in a tattered cloak with an angry carved head, straw hands and a lit lantern |

Every figurine has flickering candle-lit jack-o'-lanterns and a cursed green haze with glowing motes, made from the
particle effect the game uses on its haunted frigates. The heads wobble like the game's own figurines.

## Install

1. Download the release zip (Nexus Mods or the Releases tab here).
2. Extract the `HalloweenFigurines` folder into `No Man's Sky\GAMEDATA\MODS\`.
3. Buy the figurines for 3,200 Quicksilver each from the Quicksilver Synthesis Companion on the Space Anomaly,
   then install one in your starship's inventory.

Shop overhauls that replace the whole Quicksilver list (such as ~Consumerism) must load *before* this mod: give
`HALLOWEENFIGURINES` a lower `ModPriority` number in `Binaries\SETTINGS\GCMODSETTINGS.MXML` (the lowest number loads last).

## Compatibility

- Table changes are EXML merge files that only add new entries.
- The cockpit figurine list is a complete file. It also lists the Box-Bot figurines from
  [Box-Bot Cockpit Figurine](https://github.com/MajorRoyMcCalluster/box-bot-cockpit-figurine), so the two mods work together.
  Other mods that replace the figurine list will conflict.

## Building from source

The models are in `design/halloween_v2.blend` (Blender 5.2). Its `hw_export` text block writes `design/v2_*.pkl`.

```
pip install -r requirements.txt
python tools/build.py --game "C:/path/to/No Man's Sky" --install
```

`build.py` extracts the game files it needs (HGPAKtool), decompiles them (MBINCompiler: put `MBINCompiler.exe` in
`tools/bin/` or set `MBINCOMPILER`), builds the scenes, materials, flipbook textures, particles and shop entries,
runs the release checks and packages `dist/Halloween Figurines-<version>.zip`. No game files are stored in this repo.

## Credits

MajorRoyMcCalluster. Built with MBINCompiler and HGPAKtool by the NMS modding community.

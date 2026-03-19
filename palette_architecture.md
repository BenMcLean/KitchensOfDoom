# Palette Architecture — Muppets Inside / Swedish Chef's Kitchens of Doom

## Overview

All game graphics under `chef/` use a **palette-swap model** with exactly **4 palettes** — one per kitchen theme. No separate sprite palette exists; sprites were designed to share the same palette as whichever kitchen is active.

Every palette is 256 colors (768 bytes of raw RGB triplets, 3 bytes per entry, no header). Each PCX file embeds its own copy of the applicable palette in the last 768 bytes of the file, preceded by the standard PCX palette marker byte `0x0C` at offset −769.

---

## Palette Structure

Each of the 4 palettes shares the same two-zone layout:

| Index range | Content | Same across all 4 palettes? |
|-------------|---------|----------------------------|
| 0 | Transparent / background color | No, but irrelevant — never rendered |
| 1 – 89 | Sprite colors (also referenced by kitchen textures — identical in all 4 palettes) | **Yes — bit-for-bit identical** |
| 90 – 255 | Kitchen-exclusive texture colors | No — unique per kitchen |

Sprites (food enemies and held utensils) use only pixel indices within the range 1–89. Kitchen texture tiles use indices from the full range 1–255 — they reference the sprite range as well as their own exclusive range. This means any of the 4 kitchen palettes can be loaded and sprites will render correctly without remapping.

---

## The 4 Palettes

### FIFTS — Fifties Kitchen
- **Reference file:** `chef/KITCHENS/FIFTS_00.PCX`
- Used by levels: 1, 5
- Also the palette embedded in all `chef/FOODS/` and `chef/UTENSILS/` sprite files (the "main game palette")

### TECHY — Techy / Modern Kitchen
- **Reference file:** `chef/KITCHENS/TECHY_00.PCX`
- Used by levels: 2, 7, 9

### WOODY — Woody Kitchen
- **Reference file:** `chef/KITCHENS/WOODY_00.PCX`
- Used by levels: 3, 8

### MEDIV — Medieval Kitchen
- **Reference file:** `chef/KITCHENS/MEDIV_00.PCX`
- Used by levels: 4, 6, 10

To extract any palette as a raw 768-byte binary, read the last 768 bytes of the reference PCX (i.e., bytes at offset `filesize − 768`).

---

## How Each Graphic Type Uses the Palette

### KITCHENS (wall/floor/ceiling textures)
Files: `chef/KITCHENS/FIFTS_*.PCX`, `TECHY_*.PCX`, `WOODY_*.PCX`, `MEDIV_*.PCX`

Each file embeds its own kitchen's palette. Pixel indices span the full range 1–255, drawing on both the shared 1–89 zone and the kitchen-exclusive 90–255 zone.

### FOODS (enemy sprites — carrots, tomatoes, etc.)
Files: `chef/FOODS/*.PCX`

All embed the FIFTS/main palette. Pixel indices used: 1–89 only. These sprites render correctly under any of the 4 kitchen palettes without remapping.

### UTENSILS (held weapon sprites — whisk, batter gun, etc.)
Files: `chef/UTENSILS/SM_*.PCX`, `MD_*.PCX`, `LG_*.PCX`, `UTEN_*.PCX`

Same as FOODS: all embed the FIFTS/main palette and use only pixel indices 1–89.

### MISC
Files: `chef/MISC/*.PCX`

Various UI elements (font, number glyphs, info bar). These use their own independent palettes and are not subject to the kitchen palette-swap model.

### LEVELS
Files: `chef/LEVELS/LEVEL*.PCX`

Level map files used by the level editor — not rendered textures. Each embeds a completely unrelated palette used for color-coded map visualization. Not relevant to in-game rendering.

---

## Anomalous File: `UTENSILS/MD_WSKFL.PCX`

This file should be disregarded:

- **Dimensions:** 128×64 — does not match any size tier (`SM_`=64×64, `MD_`=96×96, `LG_`=128×128)
- **Content:** Appears to be a batter gun image, unrelated to the whisk its name implies
- **Palette:** Completely unique — shares almost no colors with any kitchen or sprite palette, and uses pixel indices throughout 0–255 rather than staying within 1–89
- **Status:** Almost certainly an unused leftover from development; no evidence it is referenced by `bork.exe`

This file is the sole exception to the palette-swap model and can be safely excluded from any port or conversion.

---

## Summary: Deriving the Palettes

To obtain all 4 palettes, read the last 768 bytes of these four files:

```
chef/KITCHENS/FIFTS_00.PCX   -> FIFTS palette (also the main sprite palette)
chef/KITCHENS/TECHY_00.PCX   -> TECHY palette
chef/KITCHENS/WOODY_00.PCX   -> WOODY palette
chef/KITCHENS/MEDIV_00.PCX   -> MEDIV palette
```

Any `_00.PCX` kitchen file works as a reference; the palette is consistent across all files belonging to the same kitchen theme. The `_00` tile is simply the most convenient anchor point.

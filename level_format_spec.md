# Muppets Inside (1996) — The Swedish Chef's Kitchens of Doom
# Level Format Technical Specification

- **Game:** Muppets Inside, Starwave, 1996
- **Minigame:** The Swedish Chef's Kitchens of Doom
- **Engine:** I3D Tool Kit 2.1, copyright 1993–94 Jim O'Keane, probably behind https://sites.google.com/view/disintegrator/home
- **Authored by:** Ben McLean, reverse engineering of installed game files

---

## Citation Key

All facts in this document are sourced from one of:

| Tag | Source |
|-----|--------|
| `[hex]` | Direct hex dump via `xxd` of the named file |
| `[strings]` | Output of printable-string extraction from `bork.exe` |
| `[blk:01]` | Plain-text content of `LEVELS/LEVEL01.BLK` (and similarly for other levels) |
| `[decode]` | Result of running the PCX RLE decoder and analyzing the 256×256 grid |
| `[pcxspec]` | Standard PCX file format specification (widely documented, e.g. ZSoft PCX Technical Reference) |
| `[user]` | Playing the game |

---

## 1. Engine

`[strings]` The string `I3D Tool Kit 2.1 (c)1993-94 Jim O'Keane` was found literally in `bork.exe` (the minigame executable). The string `?I3D 2.1 Demo` also appears in the same binary. The `.BLK` files begin with the header line `I3D DEMO block database file version: 2.0` `[blk:01]`.

This is a Wolfenstein-3D–style raycasting engine with a grid-based world. Geometry is defined as axis-aligned cubes (blocks). The player navigates a 2D tile grid that is rendered in first-person 3D.

---

## 2. File Organization

```
Muppets Inside/chef/
├── bork.exe                    ← minigame executable
├── LEVELS/
│   ├── LEVEL01.PCX             ← map grid for level 1
│   ├── LEVEL01.BLK             ← block/entity definitions for level 1
│   ├── LEVEL02.PCX
│   ├── LEVEL02.BLK
│   ...
│   ├── LEVEL10.PCX
│   └── LEVEL10.BLK
├── KITCHENS/                   ← wall/floor/ceiling textures
│   ├── FIFTS_00.PCX ... FIFTS_15.PCX   (Fifties theme)
│   ├── MEDIV_00.PCX ... MEDIV_16.PCX   (Medieval theme)
│   ├── TECHY_00.PCX ... TECHY_13.PCX   (Techy theme)
│   └── WOODY_00.PCX ... WOODY_14.PCX   (Woody theme)
├── FOODS/                      ← enemy sprite sheets
├── UTENSILS/                   ← item sprite sheets
└── MISC/                       ← UI/HUD images
```

`[strings]` The file naming pattern `LEVELS\%s%02d` appears in `bork.exe` error messages, confirming the level numbering scheme. The range is 1–10: `Error - game level must be between 1 and 10`.

Each level is **exactly one `.PCX` file paired with one `.BLK` file**, both sharing the same base name. They must be loaded together; neither is independently meaningful.

---

## 3. The PCX Map File (`.PCX`)

### 3.1 It Is a Standard PCX File

`[hex:LEVEL01.PCX]` The file begins with bytes `0A 05 01 08` — the standard ZSoft PCX magic. Despite the extension being used unconventionally (the file encodes a map grid, not a photographic image), it is a fully valid, standards-compliant PCX file that any PCX decoder will correctly expand.

### 3.2 PCX Header (128 bytes)

All multi-byte integers are **little-endian**. `[hex:LEVEL01.PCX]` `[pcxspec]`

| Offset | Size | Value (all levels) | Meaning |
|--------|------|--------------------|---------|
| 0 | 1 | `0x0A` | PCX manufacturer magic |
| 1 | 1 | `0x05` | Version 5.0 (supports VGA 256-color palette) |
| 2 | 1 | `0x01` | Encoding: 1 = Run-Length Encoded (RLE) |
| 3 | 1 | `0x08` | Bits per pixel: 8 |
| 4–5 | 2 | `0x0000` | Xmin = 0 |
| 6–7 | 2 | `0x0000` | Ymin = 0 |
| 8–9 | 2 | `0x00FF` = 255 | Xmax = 255 |
| 10–11 | 2 | `0x00FF` = 255 | Ymax = 255 |
| 12–13 | 2 | `0x0096` = 150 | Horizontal DPI (not semantically meaningful here) |
| 14–15 | 2 | `0x0096` = 150 | Vertical DPI (not semantically meaningful here) |
| 16–63 | 48 | varies | 16-color EGA palette (not used; VGA palette is at file end) |
| 64 | 1 | `0x00` | Reserved, always 0 |
| 65 | 1 | `0x01` | Color planes = 1 |
| 66–67 | 2 | `0x0100` = 256 | Bytes per scan line |
| 68–69 | 2 | `0x0001` = 1 | Palette type: 1 = color |
| 70–71 | 2 | `0x0000` | Horizontal screen size (unused) |
| 72–73 | 2 | `0x0000` | Vertical screen size (unused) |
| 74–127 | 54 | `0x00…` | Filler (all zeroes) |

`[decode]` All 10 level PCX files have identical header field values. The map is always **256 columns × 256 rows**, one byte per cell.

### 3.3 RLE-Compressed Pixel Data (bytes 128 to EOF−769)

`[pcxspec]` PCX RLE encoding: read one byte at a time starting at offset 128.

```
if (byte & 0xC0) == 0xC0:
	count = byte & 0x3F      # upper 2 bits set → run; count in lower 6 bits
	value = next_byte()      # the repeated value
	emit count copies of value
else:
	emit 1 copy of byte      # literal byte (top 2 bits both clear)
```

Expand until you have accumulated `256 × 256 = 65536` bytes. Lay them out row-major: the first 256 bytes are row 0 (Y=0), bytes 256–511 are row 1 (Y=1), etc.

`[decode]` Observed compressed sizes range from 17,694 bytes (level 1) to roughly 20,000 bytes across all 10 levels.

**The decompressed result is the map grid:** `grid[y][x]` is a **block ID** (0–255) at column x, row y.

### 3.4 VGA 256-Color Palette (last 769 bytes)

`[decode]` For all 10 level files, the byte at offset `−769` (i.e., `file_size − 769`) is `0x0C` — the standard PCX Version 5 VGA palette marker. `[pcxspec]` Following it are `768 bytes = 256 × 3` RGB triplets, 8 bits per channel (0–255). This palette defines the visual color of each block ID for the level editor; it is **not needed for map parsing** in a modern engine. `[decode]` The palette varies across levels (4 distinct palettes observed, corresponding to the 4 kitchen themes).

---

## 4. The Map Grid Layout (256 × 256)

`[decode]` The 256×256 cell grid is divided into three regions. Only the **playable maze** is needed for a game engine import.

```
  Column 0                    ~53        54                         255
Row 0   ┌──────────────────────┬─────────────────────────────────────┐
		│                      │                                     │
		│    PLAYABLE MAZE     │     LEVEL EDITOR TILE PALETTE       │
		│                      │    (block type examples in rooms)   │
		│   (actual game map)  │                                     │
~Row 127│                      │                                     │
		├──────────────────────┤                                     │
		│  TILE PREVIEW ROWS   │                                     │
		│  (palette, rows of   │                                     │
		│   solid walls with   │                                     │
		│   sample IDs inset)  │                                     │
Row 199 └──────────────────────┴─────────────────────────────────────┘
Row 200–255: all void (0xFF)
```

### 4.1 Playable Maze Region

`[decode]` The playable maze occupies the **left portion** of the grid (columns 0–~53) at a **Y position determined by the player start** in the BLK file. It is not always at row 0:

| Level | Player Start (x,y) | Approximate Maze Row Range |
|-------|--------------------|----------------------------|
| 01 | (2, 2) | rows 0–19 |
| 02 | (2, 2) | rows 0–15 |
| 03 | (3, 33) | rows 8–35 |
| 04 | (18, 7) | rows 0–28 |
| 05 | (16, 18) | rows 0–36 |
| 06 | (3, 35) | rows 0–42 |
| 07 | (46, 3) | rows 0–34 |
| 08 | (37, 32) | rows 0–33 |
| 09 | (3, 3) | rows 0–47 |
| 10 | (2, 9) | rows 0–28 |

`[blk:01–10]` Player start coordinates come from the `Player start x` and `Player start y` fields in the BLK file header. To extract only the maze, use a flood-fill from the player start position (see Section 7).

### 4.2 Level Editor Tile Palette (columns ~54–255)

`[decode]` Columns 54–255 contain the **level editor's tile palette**: every defined block type is displayed as a small rectangular room (walls on all sides, with the block ID of interest filling the interior). These cells are never reachable by the player's flood-fill and should be **ignored entirely** for game engine import. Block IDs in this region of every level file each appear exactly 21 times (a 3-column × 7-row room per block type).

### 4.3 Reserved/Palette Lower Rows (rows ~128–199, columns 0–53)

`[decode]` Below the playable maze and its surrounding empty space (cells filled with `0x00` = open floor), starting around row 128, the left columns contain another region used by the level editor: solid walls (`id=1`) forming a large block with small insets showing variant block IDs. The final rows of this region (rows 188–199 in level 1) contain a solid fill of the *next level's primary wall block ID* `[decode]` — seemingly a preview. This region is also **not reachable by flood-fill** from the player start and should be ignored for game import.

### 4.4 Special Cell Values

| Block ID | Meaning | Source |
|----------|---------|--------|
| `0x00` (0) | Open floor (passable, no geometry) | `[blk:01]` `block 0 { open block }` — `shape = empty; set trans;` |
| `0xFF` (255) | Void / outside the map (never rendered) | `[decode]` Fills the right palette area exterior and unused rows |
| All others | Block or thing ID, defined in the paired `.BLK` file | `[blk:01–10]` |

---

## 5. The BLK Block Database File (`.BLK`)

### 5.1 File Encoding

`[decode]` Line endings are **CRLF** (`0x0D 0x0A`). The file begins with a bare `0x0D 0x0A` before the version line (i.e., the first line is blank). All 10 BLK files exhibit this. Encoding is 7-bit ASCII.

### 5.2 Top-Level Structure

```
\r\n
I3D DEMO block database file version: 2.0\r\n
Background color index: N \r\n
Shadow color index    : N \r\n
Highlight color index : N \r\n
Floor color index     : N \r\n
Ceiling color index   : N \r\n
Player start x        :  N\r\n
Player start y        :  N\r\n
Player start heading  :  N \r\n
\r\n
{ comment block }\r\n
block N ( { optional inline comment }\r\n
	property = value;\r\n
	...\r\n
)\r\n
\r\n
thing N ( { optional inline comment }\r\n
	...\r\n
)\r\n
\r\n
action N ( { optional inline comment }\r\n
	...\r\n
)\r\n
\r\n
anim N ( { optional inline comment }\r\n
	...\r\n
)\r\n
```

`[blk:01]` The first non-blank line is always `I3D DEMO block database file version: 2.0`. Everything else is order-independent within each section.

### 5.3 Header Fields

`[blk:01]` Parsed from the header lines above the first `block`/`thing` definition:

| Field | Key string | Type | Notes |
|-------|-----------|------|-------|
| Background color index | `Background color index:` | integer | Index into VGA palette (not needed for import) |
| Shadow color index | `Shadow color index    :` | integer | |
| Highlight color index | `Highlight color index :` | integer | |
| Floor color index | `Floor color index     :` | integer | Default floor color for unspecified cells |
| Ceiling color index | `Ceiling color index   :` | integer | Default ceiling color |
| **Player start X** | `Player start x        :` | integer | **Map column (0-based)** |
| **Player start Y** | `Player start y        :` | integer | **Map row (0-based)** |
| **Player start heading** | `Player start heading  :` | integer | **Spawn direction (see Section 6.2)** |

Parsing: split on `:`, strip whitespace, parse as integer. The value may have trailing whitespace.

### 5.4 Entry Types

`[blk:01–10]` Four entry types are defined. All use the same syntax:

```
keyword ID ( { optional comment }
	property = value;
	set flag;
	...
)
```

- `keyword` is one of: `block`, `thing`, `action`, `anim`
- `ID` is a decimal integer
- The body is delimited by `(` and `)` (not braces — the braces are used only for comments)
- Body lines are tab-indented
- Property assignments end with `;`
- `set flagname;` sets a boolean flag on the entry
- Comments use `{ curly braces }` and may appear inline anywhere on a line; they do not nest

**Important:** `[blk:01]` The integer IDs are *not globally unique across types*. For example, `block 1` (walls) and `action 01` (cabbage action) both use ID 1 in LEVEL01.BLK. The engine uses type context to disambiguate. **In the PCX map grid, only `block` and `thing` IDs appear as pixel values.** When the same integer ID appears for both a `block`/`thing` and an `action`/`anim`, the `block` or `thing` definition is the one relevant to the map.

### 5.5 `block` Entry Properties

`[blk:01–10]` All properties observed across all 10 level files:

| Property | Example Value | Meaning |
|----------|--------------|---------|
| `shape` | `empty`, `cube`, `horz` | Geometry type. `empty` = no geometry (floor tile). `cube` = solid cube. `horz` = horizontal half-wall (passable from N/S, solid from E/W — used for goal door markers). |
| `set wall` | (flag) | Cell is solid and blocks movement |
| `set trans` | (flag) | Cell is transparent / passable (no collision) |
| `set hitable` | (flag) | Cell can receive damage (used on thing entries) |
| `n_wall` | `kitchens\fifts_00` | Texture for north face. Path is relative to `chef/`, backslash-separated, no extension — the file is a PCX. |
| `e_wall` | `kitchens\fifts_01` | Texture for east face |
| `s_wall` | `kitchens\fifts_02` | Texture for south face |
| `w_wall` | `kitchens\fifts_03` | Texture for west face |
| `ceil` | `kitchens\fifts_06` | Ceiling texture |
| `floor` | `kitchens\fifts_05` | Floor texture |
| `t_width` | `256` | Texture width in pixels (typically 256) |
| `t_height` | `256` | Texture height in pixels (typically 256) |
| `obstacle` | `kitchens\fifts_07` | (Commented out in all observed files; purpose unclear) |

`[blk:01]` For blocks with `shape = empty`, the `n_wall`/`e_wall`/`s_wall`/`w_wall` properties are absent. Only `ceil` and `floor` are specified.

### 5.6 `thing` Entry Properties

`[blk:01–10]` Things are entities placed on the floor (enemies, pickups). They always have `set trans` (passable — the player can walk into the cell and trigger the entity).

| Property | Example | Meaning |
|----------|---------|---------|
| `set trans` | (flag) | Always set; thing is passable |
| `set wall` | (flag) | Sometimes set; implies the sprite blocks sight |
| `set hitable` | (flag) | Sometimes set |
| `panel` | `utensils\uten_wsk` | Sprite sheet PCX path (relative to `chef/`, no extension) |
| `t_width` | `256` | Sprite width hint |
| `t_height` | `128` | Sprite height hint |
| `action` | `10` | Links to an `action` entry by ID (defines enemy behavior) |

### 5.7 `action` Entry Properties

`[blk:01–10]` Actions define enemy combat stats. These are linked from `thing` entries via the `action` property. Not directly relevant for geometry import.

| Property | Example | Meaning |
|----------|---------|---------|
| `name` | `carrot` | Display name |
| `radius` | `0.92` | Collision radius in cells |
| `walk_anim` | `10` | ID of walking animation (links to `anim` entry) |
| `throw_anim` | `11` | ID of attack animation |
| `talk_anim` | `12` | ID of idle/talk animation |
| `die_anim` | `13` | ID of death animation |
| `dead_anim` | `14` | ID of dead (corpse) animation |
| `speed` | `75` | Movement speed (0=still, 100=fast) |
| `wisk` | `256 86 64` | Damage thresholds for whisk weapon (3 integers) |
| `egg_beater` | `256 86 64` | Damage thresholds for egg-beater weapon |
| `rolling_pin` | `256 128 86` | Damage thresholds for rolling-pin weapon |
| `food_processor` | `256 256 128` | Damage thresholds for food-processor weapon |
| `pastry_gun` | `256 256 256` | Damage thresholds for pastry-gun weapon |

`[blk:01]` Damage thresholds appear to be 3 integers representing thresholds for different difficulty settings. The comment `{ 4 hits required }` in the file clarifies: `256` = requires the maximum hits (one hit = floor(255/threshold) damage).

### 5.8 `anim` Entry Properties

`[blk:01]` Animation sheet definitions, linked from `action` entries.

| Property | Example | Meaning |
|----------|---------|---------|
| `panel` | `foods\ca_wlk` | Base path of sprite sheet PCX(s) |
| `frames` | `3` | Number of animation frames |
| `views` | `3` | Number of view angles (1 = single sprite, 3 or 8 = directional) |

---

## 6. Coordinate and Heading System

### 6.1 Cell Coordinates

`[decode]` The PCX grid uses standard 2D raster coordinates:

- **X** increases left → right (west → east)
- **Y** increases top → bottom (north → south)
- `(0, 0)` is the top-left cell

`[strings]` In `bork.exe`, runtime position is logged as `(%d:%3d, %d:%3d)` — a **fixed-point format** where the integer part is the cell index and the fractional part is a sub-cell offset (0–999, i.e., 1/1000 of a cell). Example: `(2:000, 2:000)` = cell (2,2) at the center. This is the **in-engine runtime format**; the BLK file stores only the integer cell coordinates.

### 6.2 Heading (Player Spawn Orientation)

`[blk:01–10]` The `Player start heading` field stores an integer angle. `[decode]` Observed values: `0, 32, 64, 96, 144, 192, 250`. The values 0, 32, 64, 96, 144, 192 are all multiples of 32 (= 256/8), strongly indicating a **256-unit-per-revolution binary angle measurement (BAM)** system, where the full circle maps to 0–255.

Under the assumption that `0 = North` and the angle increases **clockwise** (consistent with 2D game conventions where Y increases downward):

| Heading value | Degrees | Cardinal |
|---------------|---------|----------|
| 0 | 0° | North |
| 32 | 45° | NE |
| 64 | 90° | East |
| 96 | 135° | SE |
| 128 | 180° | South |
| 144 | ~202° | SSW |
| 192 | 270° | West |
| 224 | 315° | NW |
| 250 | ~352° | NNW |

> **Caveat:** The axis convention (which direction is 0) is inferred from the BAM structure and reasonable raycasting defaults. It has not been confirmed by running the game and observing player spawn direction. The value 144 (used in level 4) does not fall on a standard 45° boundary, which suggests the engine may use true continuous angles rather than cardinal snapping.

`[strings]` `bork.exe` contains the token `inc_angle_tok`, suggesting a concept of angular increments confirming that heading is indeed a continuous angle, not an enumerated direction.

---

## 7. Extracting the Playable Maze

The 256×256 grid contains editor metadata beyond the playable maze. Use the following algorithm to isolate the maze for import.

### 7.1 Algorithm: Flood Fill from Player Start

```python
def extract_maze(grid, blk):
	px = blk.player_x
	py = blk.player_y
	defs = blk.definitions   # dict: id -> {type, shape, is_wall, is_thing, ...}

	def is_passable(val):
		if val == 0:   return True   # open floor [blk:01 block 0]
		if val == 255: return False  # void
		d = defs.get(val)
		if d is None: return False
		# things (set trans) and shape=empty blocks are passable [blk:01]
		return d['type'] == 'thing' or d.get('shape') == 'empty' or d.get('is_thing')

	# BFS from player start
	from collections import deque
	visited = set()
	q = deque([(px, py)])
	visited.add((px, py))
	while q:
		x, y = q.popleft()
		for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
			nx, ny = x+dx, y+dy
			if 0 <= nx < 256 and 0 <= ny < 256:
				if (nx, ny) not in visited and is_passable(grid[ny][nx]):
					visited.add((nx, ny))
					q.append((nx, ny))

	# Bounding box of reachable cells + 1 border row/col to include surrounding walls
	xs = [p[0] for p in visited]
	ys = [p[1] for p in visited]
	x0 = max(0, min(xs) - 1)
	y0 = max(0, min(ys) - 1)
	x1 = min(255, max(xs) + 1)
	y1 = min(255, max(ys) + 1)

	maze = [[grid[y][x] for x in range(x0, x1+1)] for y in range(y0, y1+1)]
	player_local_x = px - x0
	player_local_y = py - y0
	return maze, player_local_x, player_local_y
```

`[decode]` This algorithm correctly isolates all 10 playable mazes. The editor palette region (columns 54+) and the tile preview rows are never reachable from the player start because they are separated by void (`0xFF`) or solid wall cells.

### 7.2 Maze Cell Semantics for Import

After extraction, each cell in the maze sub-grid has one of these semantic roles:

| Value | Role | Notes |
|-------|------|-------|
| `0` | Open floor | Passable, render floor + ceiling texture |
| `255` | Void | Outside map bounds; treat as impassable, do not render |
| `1` | Generic wall | Solid, render all 4 faces |
| `2` | Horizontal goal door | `shape = horz` `[blk:01]`: passable from N/S only (half-wall marking a level exit) |
| `3` | Vertical goal door | `shape = cube` with exit textures on E/W faces |
| `4`–`9` (varies) | Weapon pickup | Thing at floor level; passable. Which weapon ID maps to which pickup is defined **per-level** in the BLK — see Section 13 |
| `10`, `19`, etc. | Enemy spawn point | Thing at floor level; passable by player on spawn |
| `20`–`24`, `60`–`65`, etc. | Textured wall variants | Solid; use `n_wall`/`e_wall`/`s_wall`/`w_wall` for per-face textures |
| `86`, `87`, `88`, `89` | Exit/easy-out markers | `[blk:01]` described as "easy out north-south/east-west"; `shape = cube`, `set wall`. Mark passable exit cells that end the level |

For a Wolfenstein-style import, the minimum viable classification is:
- `0` or any cell where `shape == empty` or `set trans` → **floor** (empty cell)
- `255` → **void** (skip)
- All others → **wall** (solid), with face textures from the BLK definition

---

## 8. Kitchen Tileset Themes

`[blk:01–10]` Each level's BLK file references textures from one of four kitchen theme directories under `KITCHENS/`. The theme is identified by the texture path prefix:

| Prefix | Theme | Levels |
|--------|-------|--------|
| `fifts_` | Fifties kitchen | 1, 5 |
| `techy_` | Techy/modern kitchen | 2, 7, 9 |
| `woody_` | Woody/cabin kitchen | 3, 8 |
| `mediv_` | Medieval kitchen | 4, 6, 10 |

Texture paths in the BLK use **Windows backslash** as a path separator and have **no file extension**. The actual files on disk are PCX format with uppercase names (e.g., `KITCHENS\FIFTS_00.PCX`). `[strings]` The executable references both `.PCX` and `.pcx` case variants when loading, suggesting case-insensitive path resolution.

---

## 9. Enemy and Item Types (All Levels)

`[blk:01–10]` All food enemies and item types observed across the 10 BLK files:

| Name (in BLK `name` field or comment) | Map symbol | Levels |
|---------------------------------------|-----------|--------|
| carrot | `thing` | 1, 8, 10 |
| cabbage | `thing` | 1, 10 |
| lemon | `thing` | 2, 10 |
| watermellon (sic) | `thing` | 2, 10 |
| coliflower (sic, = cauliflower) | `thing` | 3, 10 |
| cucumber | `thing` | 3, 10 |
| tomato | `thing` | 4, 5, 6, 7, 8, 9, 10 |
| potato | `thing` | 5, 7, 10 |
| cheese | `thing` | 6, 10 |
| egg | `thing` | 6, 7, 10 |
| whisk (utensil/pickup) | `thing` | 1, 2, ... |

`[blk:01–10]` Level 10 contains all food enemy types simultaneously, making it the final/hardest level.

---

## 10. Weapons and Damage System

`[blk:01]` The `action` entries define five named weapons and three damage-resistance thresholds per weapon (values are out of 255 total health):

| Weapon | Threshold values (typical) | Hits to kill (typical) |
|--------|---------------------------|------------------------|
| `wisk` | `256 86 64` | 4 hits |
| `egg_beater` | `256 86 64` | 4 hits |
| `rolling_pin` | `256 128 86` | 3 hits |
| `food_processor` | `256 256 128` | 2 hits |
| `pastry_gun` | `256 256 256` | 1 hit |

`[blk:01]` The comment `{ out of 255 health points, so 4 hits required }` appears inline. A threshold value of `256` means a single hit does not kill (> 255 HP), so multiple hits are needed.

---

## 11. Parsing Pseudocode (Language-Agnostic)

### 11.1 Parse the PCX Map

```
function parse_pcx_map(bytes):
	# Header
	assert bytes[0] == 0x0A            # PCX magic
	assert bytes[1] == 0x05            # Version 5
	assert bytes[2] == 0x01            # RLE encoding
	assert bytes[3] == 0x08            # 8 bpp
	xmax = read_u16_le(bytes, 8)       # always 255
	ymax = read_u16_le(bytes, 10)      # always 255
	width  = xmax + 1                  # always 256
	height = ymax + 1                  # always 256
	bytes_per_line = read_u16_le(bytes, 66)  # always 256

	# Decode RLE starting at byte 128
	pixels = []
	pos = 128
	target = height * bytes_per_line   # 65536
	while len(pixels) < target:
		b = bytes[pos]; pos++
		if (b & 0xC0) == 0xC0:
			count = b & 0x3F
			value = bytes[pos]; pos++
			repeat value, count times into pixels
		else:
			append b to pixels

	# Build 2D grid [row][col]
	grid = new array[height][width]
	for y in 0..height-1:
		for x in 0..width-1:
			grid[y][x] = pixels[y * bytes_per_line + x]

	# Optional: read VGA palette (not needed for map import)
	assert bytes[len(bytes) - 769] == 0x0C   # palette marker
	palette = bytes[len(bytes)-768 .. len(bytes)-1]  # 256 * RGB

	return grid
```

### 11.2 Parse the BLK File

```
function parse_blk(text):
	result = {
		player_x: 2, player_y: 2, player_heading: 0,
		floor_color: 0, ceiling_color: 0,
		blocks: {}, things: {}, actions: {}, anims: {}
	}

	lines = split text by CRLF
	i = 0
	while i < len(lines):
		line = trim(lines[i])

		# Header fields (parse until first block/thing/action/anim keyword)
		if line starts with "Player start x": result.player_x = int(after ":")
		if line starts with "Player start y": result.player_y = int(after ":")
		if line starts with "Player start heading": result.player_heading = int(after ":")
		if line starts with "Floor color index": result.floor_color = int(after ":")
		if line starts with "Ceiling color index": result.ceiling_color = int(after ":")

		# Entry definitions
		keyword, id, comment = try_parse_entry_header(line)
		# entry header format: "keyword N ( { optional comment }"
		if keyword matched:
			entry = {id: id, comment: comment, shape: "cube",
					 is_wall: false, is_thing: false, properties: {}}
			i++
			while i < len(lines):
				body_line = trim(lines[i])
				if body_line starts with ")": break
				if body_line == "set wall;": entry.is_wall = true
				if body_line == "set trans;": entry.is_thing = true
				if body_line starts with "shape":
					entry.shape = value_of(body_line)  # empty/cube/horz
				# Parse "key = value;" — strip inline { comments } first
				key, value = parse_property(strip_comments(body_line))
				if key: entry.properties[key] = value
				i++
			# Store in appropriate namespace
			if keyword == "block": result.blocks[id] = entry
			if keyword == "thing": result.things[id] = entry
			if keyword == "action": result.actions[id] = entry
			if keyword == "anim":  result.anims[id]   = entry

		i++

	return result
```

> **Note on ID collision:** `[blk:01]` In the same BLK file, `block 0` (open floor), `thing 10` (carrot), and `action 10` (carrot behavior) can coexist with the same integer ID. When looking up a map cell value, **always check `blocks` first, then `things`.** `action` and `anim` entries are not stored as map cells.

### 11.3 Resolve a Cell to Geometry

```
function cell_to_geometry(cell_value, blk):
	if cell_value == 0:   return FLOOR
	if cell_value == 255: return VOID

	block = blk.blocks.get(cell_value)
	if block:
		if block.shape == "empty": return FLOOR
		if block.is_wall:
			return WALL(
				faces: {
					N: resolve_texture(block.n_wall),
					E: resolve_texture(block.e_wall),
					S: resolve_texture(block.s_wall),
					W: resolve_texture(block.w_wall),
				},
				floor: resolve_texture(block.floor),
				ceil:  resolve_texture(block.ceil)
			)

	thing = blk.things.get(cell_value)
	if thing:
		return ENTITY(
			sprite: resolve_texture(thing.panel),
			action_id: thing.properties.get("action")
		)

	return UNKNOWN  # ID present in map but not defined in this BLK
```

### 11.4 Resolve a Texture Path

```
function resolve_texture(blk_path):
	# blk_path example: "kitchens\fifts_00"
	# Replace backslash with platform separator, append ".PCX"
	return base_dir + "/" + blk_path.replace("\\", "/") + ".PCX"
	# On disk: chef/KITCHENS/FIFTS_00.PCX (files are uppercase)
```

---

## 12. Known Unknowns

The following were observed but not fully determined by this analysis:

1. **Blocks 86–89 ("easy out" markers):** `[blk:01]` Defined as `shape = cube; set wall;` with descriptors like "easy out north-south". Appear at level exits in the map. Their exact runtime behavior (teleport? level-end trigger?) is not confirmed from static file analysis alone.

2. **Heading axis convention:** `[decode]` The heading unit (256/revolution) is confirmed, but whether `0 = North` or `0 = East` was inferred, not directly observed.

3. **Multiple undefined block IDs:** `[decode]` Cells with IDs not defined in the paired BLK (e.g., ID `86` in LEVEL05.PCX where LEVEL05.BLK lacks a `block 86` entry) appear to be valid map data. These may reference a built-in default the engine knows about (the executable likely has hardcoded fallback definitions for certain IDs).

4. **`obstacle` property:** `[blk:01]` Appears in commented-out form in LEVEL01.BLK: `{obstacle = kitchens\fifts_07;}`. Purpose unknown (possibly an AI navigation blocker).

5. **`background color index` / `shadow` / `highlight` palette indices:** `[blk:01]` Specified in the BLK header. Likely used for ambient lighting or fog effects at runtime. Not needed for static geometry import.

6. **VGA palette:** `[decode]` The 256-color palette at the end of the PCX is not needed to interpret map cell IDs. It was used by the level editor to render the map preview.

---

## 13. Weapons and Pickups

### 13.1 The Five Weapons

`[utensils/]` The `UTENSILS/` directory contains exactly five floor-pickup sprites — one per weapon — plus three sets of in-hand animation sprite sheets. The five weapons, identified by their file name stems:

| Stem | Weapon name | Floor pickup file |
|------|-------------|------------------|
| `WSK` | Whisk | `UTENSILS/UTEN_WSK.PCX` |
| `BTR` | Egg Beater | `UTENSILS/UTEN_BTR.PCX` |
| `PIN` | Rolling Pin | `UTENSILS/UTEN_PIN.PCX` |
| `PRO` | Food Processor | `UTENSILS/UTEN_PRO.PCX` |
| `GUN` | Pastry Gun | `UTENSILS/UTEN_GUN.PCX` |

These correspond exactly to the five weapon names in the `action` damage table (Section 10): `wisk`, `egg_beater`, `rolling_pin`, `food_processor`, `pastry_gun`.

### 13.2 In-Hand Weapon Animation Sprite Sheets

`[utensils/]` Each weapon also has three sets of animation frames, distinguished by a size prefix:

| Prefix | Meaning (inferred) | Frame count |
|--------|--------------------|-------------|
| `SM_` | Small (weapon at rest / lowered) | 7 frames (00–06) |
| `MD_` | Medium (weapon mid-raise) | 7 frames (00–06) |
| `LG_` | Large (weapon raised / firing) | 7 frames (00–06); 16 frames for `GUN` (00–15) |

Examples: `SM_WSK00.PCX`–`SM_WSK06.PCX`, `LG_GUP00.PCX`–`LG_GUP15.PCX`.

`[utensils/]` One additional file, `MD_WSKFL.PCX`, exists only for the whisk. The `FL` suffix likely means "flash" (muzzle/hit flash frame). This is the only weapon with a named flash frame; the others may encode the flash as one of the numbered frames.

> **Note:** The SM/MD/LG distinction and the exact engine animation state that triggers each set are inferred from the file naming. The I3D engine likely cycles through the numbered frames during the attack animation and selects the size based on a game state variable (e.g., weapon charge or bob phase).

### 13.3 Thing IDs Are Per-Level, Not Global

`[blk:01–10]` **Weapon pickup thing IDs are not fixed across levels.** The mapping from thing ID to weapon sprite is defined individually in each level's BLK file via the `panel` property. The same weapon can use a different thing ID in different levels, and different weapons can share the same ID across levels.

The BLK `thing` entry for a weapon pickup has these characteristics (distinguishing it from an enemy `thing`):
- Has a `panel` property pointing to `utensils\uten_xxx`
- Has **no** `action` property (enemies always have `action = N`)
- Has `set trans` (passable)
- Observed IDs used for weapon pickups: **4, 5, 6, 7, 8, 9**

### 13.4 Per-Level Pickup Mapping Table

`[blk:01–10]` The complete mapping of thing ID → weapon for each level, and how many of each pickup are placed in the playable maze:

| Level | Thing ID | Weapon | Count in maze |
|-------|----------|--------|---------------|
| 01 | 4 | WSK (Whisk) | 1 |
| 02 | 8 | PRO (Food Processor) | 1 |
| 02 | 9 | GUN (Pastry Gun) | 1 |
| 03 | 5 | PIN (Rolling Pin) | 1 |
| 03 | 8 | PRO (Food Processor) | 1 |
| 04 | 4 | WSK (Whisk) | — (defined but 0 in maze) |
| 04 | 5 | PIN (Rolling Pin) | 2 |
| 04 | 6 | BTR (Egg Beater) | 1 |
| 05 | 4 | WSK (Whisk) | 1 |
| 05 | 7 | PIN (Rolling Pin) | 1 |
| 05 | 8 | PRO (Food Processor) | 1 |
| 05 | 9 | GUN (Pastry Gun) | 1 |
| 06 | 4 | WSK (Whisk) | 1 |
| 06 | 5 | PIN (Rolling Pin) | — (defined but 0 in maze) |
| 06 | 6 | BTR (Egg Beater) | 1 |
| 07 | 8 | PRO (Food Processor) | 1 |
| 07 | 9 | GUN (Pastry Gun) | 1 |
| 08 | 6 | BTR (Egg Beater) | 1 |
| 08 | 8 | PRO (Food Processor) | 1 |
| 08 | 9 | GUN (Pastry Gun) | 1 |
| 09 | 9 | GUN (Pastry Gun) | 1 |
| 10 | 4 | WSK (Whisk) | 1 |
| 10 | 5 | PIN (Rolling Pin) | 1 |
| 10 | 6 | BTR (Egg Beater) | 1 |
| 10 | 7 | PIN (Rolling Pin) | 1 (second rolling pin — distinct ID, same sprite) |
| 10 | 8 | PRO (Food Processor) | 1 |
| 10 | 9 | GUN (Pastry Gun) | 1 |

`[blk:10]` Level 10 defines both thing 5 and thing 7 as `uten_pin` (rolling pin) — two separate pickup entities with different IDs but the same weapon sprite, allowing two rolling pins to be placed with independent pickup tracking.

### 13.5 Weapon Progression Pattern

`[blk:01–10]` The pickup selection across levels follows a clear escalation:

- **Level 1:** Whisk only — the player's starting weapon, weakest
- **Levels 2–3:** Mid-tier weapons appear (food processor, rolling pin)
- **Levels 4–6:** Egg beater introduced; whisk re-appears in some levels
- **Levels 7–8:** Consistently high-tier (food processor + pastry gun)
- **Level 9:** Pastry gun only — single most powerful weapon as the only pickup
- **Level 10:** All five weapons placed — one of each available in the final level

### 13.6 Resolving a Pickup Cell

For a game engine import, to identify whether a cell contains a weapon pickup:

```
function is_weapon_pickup(cell_value, blk):
	thing = blk.things.get(cell_value)
	if thing is None: return false
	panel = thing.properties.get("panel", "")
	return panel.startswith("utensils") and "action" not in thing.properties

function get_weapon_sprite(cell_value, blk):
	thing = blk.things.get(cell_value)
	panel = thing.properties["panel"]          # e.g. "utensils\uten_wsk"
	floor_sprite = resolve_texture(panel)       # UTENSILS/UTEN_WSK.PCX
	return floor_sprite
```

---

## 14. Combat System — Health, Damage, and Hits to Kill

### 14.1 Enemy Hit Points

`[blk:01]` Every enemy action entry includes an inline comment:

```
wisk = 256 86 64;  { out of 255 health points, so 4 hits required }
```

This explicitly states that **all enemies have 255 hit points**. HP is not stored in the map or BLK file as a variable — it is a constant embedded in the engine.

### 14.2 Weapon Damage Values (Per-Hit, Per Skill Level)

`[blk:01–10]` Each `action` entry specifies per-weapon damage delivered per hit, at three skill levels:

```
weapon_name = skill1_damage  skill2_damage  skill3_damage;
```

- **Skill 1** = easiest difficulty (highest damage → fewest hits to kill)
- **Skill 3** = hardest difficulty (lowest damage → most hits to kill)
- A damage value of **256** exceeds the enemy's 255 HP, guaranteeing a one-hit kill

The following table lists the raw per-hit damage values for each enemy, for each weapon, at each skill level:

| Enemy | WSK | BTR | PIN | PRO | GUN |
|-------|-----|-----|-----|-----|-----|
| Carrot | 256 / 86 / 64 | 256 / 86 / 64 | 256 / 128 / 86 | 256 / 256 / 128 | 256 / 256 / 256 |
| Cabbage | 256 / 86 / 64 | 256 / 86 / 64 | 256 / 128 / 86 | 256 / 128 / 86 | 256 / 256 / 256 |
| Lemon | 128 / 86 / 64 | 128 / 86 / 64 | 128 / 86 / 86 | 128 / 128 / 128 | 256 / 256 / 256 |
| Watermelon | 128 / 64 / 52 | 128 / 64 / 64 | 128 / 64 / 64 | 128 / 64 / 64 | 256 / 256 / 256 |
| Cauliflower | 256 / 64 / 52 | 256 / 64 / 52 | 256 / 128 / 86 | 256 / 128 / 86 | 256 / 256 / 256 |
| Cucumber | 256 / 128 / 86 | 256 / 128 / 86 | 256 / 128 / 86 | 256 / 128 / 86 | 256 / 256 / 256 |
| Tomato | 128 / 52 / 43 | 128 / 52 / 43 | 128 / 52 / 43 | 128 / 64 / 52 | 256 / 256 / 256 |
| Potato | 128 / 86 / 64 | 128 / 86 / 64 | 128 / 86 / 64 | 128 / 86 / 64 | 256 / 256 / 256 |
| Cheese | 256 / 128 / 86 | 256 / 128 / 86 | 256 / 86 / 64 | 256 / 86 / 64 | 256 / 256 / 256 |
| Egg | 256 / 128 / 86 | 256 / 256 / 128 | 128 / 128 / 86 | 128 / 128 / 86 | 256 / 256 / 256 |

### 14.3 Hits to Kill (ceil(255 / damage))

The following table gives the number of hits required to kill each enemy, derived from the damage values above using `ceil(255 / damage)`. Format: `skill1 / skill2 / skill3`.

| Enemy | WSK | BTR | PIN | PRO | GUN |
|-------|-----|-----|-----|-----|-----|
| Carrot | 1/3/4 | 1/3/4 | 1/2/3 | 1/1/2 | 1/1/1 |
| Cabbage | 1/3/4 | 1/3/4 | 1/2/3 | 1/2/3 | 1/1/1 |
| Lemon | 2/3/4 | 2/3/4 | 2/3/3 | 2/2/2 | 1/1/1 |
| Watermelon | 2/4/5 | 2/4/4 | 2/4/4 | 2/4/4 | 1/1/1 |
| Cauliflower | 1/4/5 | 1/4/5 | 1/2/3 | 1/2/3 | 1/1/1 |
| Cucumber | 1/2/3 | 1/2/3 | 1/2/3 | 1/2/3 | 1/1/1 |
| Tomato | 2/5/6 | 2/5/6 | 2/5/6 | 2/4/5 | 1/1/1 |
| Potato | 2/3/4 | 2/3/4 | 2/3/4 | 2/3/4 | 1/1/1 |
| Cheese | 1/2/3 | 1/2/3 | 1/3/4 | 1/3/4 | 1/1/1 |
| Egg | 1/2/3 | 1/1/2 | 2/2/3 | 2/2/3 | 1/1/1 |

**Notable anomalies:**

- `[blk:06]` **Egg** takes fewer hits with the Egg Beater than with the Rolling Pin or Food Processor — the egg is specifically vulnerable to being beaten (egg_beater skill3=128 vs rolling_pin skill3=86). Unusual because BTR is weaker than PIN/PRO against most enemies.
- `[blk:06]` **Cheese** takes fewer hits with WSK/BTR than with PIN/PRO — the rolling pin and food processor are actually *less effective* against cheese, suggesting a flavor-based design choice.
- **Cauliflower** at skill 2/3 takes 4–5 wisk/egg-beater hits but only 2–3 rolling pin hits — a strong per-weapon vulnerability.
- **Tomato** is the toughest enemy at skill 3: up to 6 hits with wisk, egg beater, or rolling pin. Combined with its many appearances (levels 4, 8, 9), it is the most punishing single-type level (level 9).
- **Pastry Gun** one-hit-kills every enemy at every skill level. It is always placed as the rarest pickup.

### 14.4 Player Health

`[hex]` The `MISC/CHEF_C/L/R/T 00–04.PCX` files establish that the player HUD uses the same 4-direction × 5-state health face design as Wolfenstein 3D: directions C (center), L (left), R (right), T (top) indicate the direction the player was last hit, and states 00–04 represent increasing damage (00 = full health, 04 = near death).

The exact maximum player HP value is not confirmed from the files analyzed. The 255 HP figure for enemies is explicitly stated in BLK comments; player HP is likely also byte-range (0–255) but is hardcoded in the engine and not represented in any level file.

Player damage taken (enemy projectile → player HP reduction) is also hardcoded in the engine and not found in the BLK files.

### 14.5 Food-Enemy-to-Consumable Mechanic

`[strings]` When an enemy's HP reaches zero, it transitions through a unique two-phase death sequence not present in Wolfenstein 3D or Doom:

1. **`DYING`** — death animation plays (`die_anim`)
2. **`DEAD`** — enemy lies on the floor; `dead_anim` sprite plays (looping idle). The enemy is now a consumable food item on the ground.
3. **`EATEN`** — triggered when the player walks over the dead enemy's cell. The food item is consumed.

After the EATEN transition:
- `snd_burp()` is called (plays `sounds\snd_bl00.wav` or similar from the burp sound pool)
- `snd_really_burp()` is called for a second, more emphatic burp
- The enemy entity is removed from the map

This mechanic replaces the separate pickup-drop system used in most Wolf3D-style games: the enemy body itself is the health pickup.

`[strings]` The `SPLAT` state also appears in the AI state machine strings in `bork.exe`. It is associated with the function `snd_splat_chef()` and may represent the player's death animation (the chef being flattened) rather than an enemy state.

---

## 15. Enemy AI State Machine

`[strings]` The following state names appear as literal strings in `bork.exe` in sequential order, indicating a state machine with these transitions:

```
WAITING → WANDER → TALK → CHASE → DYING → DEAD → EATEN
												 ↘ SPLAT (player death)
```

| State | Description |
|-------|-------------|
| `WAITING` | Enemy is idle, not yet aware of player |
| `WANDER` | Enemy patrols or moves randomly through the maze |
| `TALK` | Enemy has spotted the player; voice line plays; transition to chase |
| `CHASE` | Enemy actively pursues the player and attacks |
| `DYING` | Enemy HP reached zero; death animation (`die_anim`) plays |
| `DEAD` | Enemy lies on floor as a food item; `dead_anim` plays |
| `EATEN` | Player walked over the dead enemy; burp sounds play; entity removed |
| `SPLAT` | Player death state; `snd_splat_chef()` plays |

`[strings]` The function `talk_actor(%lx)` is called on transition to `TALK` state. The enemy voice line (`INT_XX00.WAV`) plays during this state. A debug toggle `Toggle vegetable speech` is present in `bork.exe`, confirming that voice lines are a discrete, toggleable feature.

---

## 16. Sound System

### 16.1 Sound File Location

`[cd]` All audio files are located on the game CD at `5\SOUNDS\`. The installed game references them via the path prefix `sounds\` (relative to the `chef\` directory). File format: PCM WAV.

### 16.2 Enemy Voice Lines (Sighting)

`[cd]` Each enemy type has exactly one sighting voice line, played when entering the `TALK` state (enemy spots the player):

| File | Enemy |
|------|-------|
| `INT_CA00.WAV` | Carrot |
| `INT_CB00.WAV` | Cabbage |
| `INT_CO00.WAV` | Cauliflower (spelled "coliflower" in BLK) |
| `INT_CS00.WAV` | Cheese |
| `INT_CU00.WAV` | Cucumber |
| `INT_EG00.WAV` | Egg |
| `INT_LE00.WAV` | Lemon |
| `INT_PO00.WAV` | Potato |
| `INT_TO00.WAV` | Tomato |
| `INT_WM00.WAV` | Watermelon |

The `INT_` prefix likely stands for "intercept" (enemy intercepting / spotting the player). Each file has only a `00` variant (no multiple takes per enemy type).

### 16.3 Per-Enemy Chase/Ambient Sounds

`[strings]` The pattern `sounds\snd_%s.wav` in `bork.exe` loads per-enemy sounds using the same two-letter abbreviation codes as the INT files. These are likely played during the `CHASE` state (enemy movement/attack sounds):

| File | Enemy |
|------|-------|
| `SND_CA.WAV` | Carrot |
| `SND_CB.WAV` | Cabbage |
| `SND_CO.WAV` | Cauliflower |
| `SND_CS.WAV` | Cheese |
| `SND_CU.WAV` | Cucumber |
| `SND_EG.WAV` | Egg |
| `SND_LE.WAV` | Lemon |
| `SND_PO.WAV` | Potato |
| `SND_TO.WAV` | Tomato |
| `SND_WM.WAV` | Watermelon |

### 16.4 Weapon Fire Sounds

`[cd]` One WAV file per weapon, played on each shot fired:

| File | Weapon |
|------|--------|
| `SND_WSK.WAV` | Whisk |
| `SND_BTR.WAV` | Egg Beater |
| `SND_PIN.WAV` | Rolling Pin |
| `SND_PRO.WAV` | Food Processor |
| `SND_GUP.WAV` | Pastry Gun |

Note: The pastry gun file uses abbreviation `GUP` rather than `GUN`, which is also how it is referenced in bork.exe sprite path strings (`lg_gup00.pcx` etc.).

### 16.5 Hit and Projectile Sounds

`[strings]` `SND_BONK.WAV` — played by `snd_bonk()` when a projectile hits a wall or enemy.

### 16.6 Player State Sounds

| File | Trigger |
|------|---------|
| `SND_OOF.WAV` | Player takes damage (hurt sound) |
| `SPLAT00.WAV` / `SPLAT_00.WAV` | Player death; played by `snd_splat_chef()` |
| `SND_BL00.WAV` | Player eats a dead food enemy (burp); called via `snd_burp()` |
| `SND_BL01.WAV` | Emphatic burp after eating; called via `snd_really_burp()` |

`[strings]` The pattern `sounds\snd_bl%02d.wav` is used to load burp sounds by index.

### 16.7 UI and Menu Sounds

| File | Trigger |
|------|---------|
| `SND_WON.WAV` | Level completed (win) |
| `SND_LOST.WAV` | Game over (player died) |
| `SND_CHNG.WAV` | Weapon switched |
| `SND_CHIM.WAV` | Chime (likely played on reaching the exit/goal) |
| `SND_QUIT.WAV` | Quit game |
| `TITLE0.WAV` | Title screen audio |

### 16.8 Chef Voice Lines

`[strings]` The pattern `sounds\chtlk%02d.wav` loads Swedish Chef dialogue. Eight files exist (`CHTLK00.WAV` through `CHTLK07.WAV`). These are likely triggered when the player fires a weapon or at other gameplay events (separate from enemy sighting lines, which use `INT_XX00.WAV`).

### 16.9 Music

`[strings]` The pattern `sounds\music%02d.wav` loads background music tracks. Four tracks exist: `MUSIC00.WAV` through `MUSIC03.WAV`.

`[user]` All four tracks are sections of the same song (the Swedish Chef theme). Playback is randomized: when a track finishes, the next track is chosen at random from the four, with replacement (the same track can repeat). There is no per-level or per-theme track assignment. This design reflects that Kitchens of Doom was intended as a short minigame within the larger Muppets Inside CD-ROM experience, not a standalone game to be played for extended sessions.

### 16.10 Enemy Abbreviation Reference

For implementing the sound system, the two-letter enemy abbreviations used in both `INT_XX00.WAV` and `SND_XX.WAV` filenames:

| Code | Enemy | BLK name |
|------|-------|----------|
| `CA` | Carrot | `carrot` |
| `CB` | Cabbage | `cabbage` |
| `CO` | Cauliflower | `coliflower` |
| `CS` | Cheese | `cheese` |
| `CU` | Cucumber | `cucumber` |
| `EG` | Egg | `egg` |
| `LE` | Lemon | `lemon` |
| `PO` | Potato | `potato` |
| `TO` | Tomato | `tomato` |
| `WM` | Watermelon | `watermellon` (note: double-l in BLK) |

---

## 17. Enemy Movement and Collision

### 17.1 Enemy Speed

`[blk:01–10]` Each `action` entry includes a `speed` property with an inline scale comment:

```
speed = 75; { 0 is still, 25 is very slow, 50 is ok, 100 is fast }
```

The scale is: **0** = stationary · **25** = very slow · **50** = moderate · **100** = fast. This is an opaque integer unit whose exact mapping to tiles/second is hardcoded in the engine.

| Enemy | Speed | Relative pace |
|-------|-------|---------------|
| Tomato | 100 | Fastest |
| Carrot | 75 | Fast |
| Cucumber | 75 | Fast |
| Cheese | 75 | Fast |
| Egg | 75 | Fast |
| Potato | 75 | Fast |
| Cabbage | 50 | Moderate |
| Lemon | 50 | Moderate |
| Cauliflower | 25 | Very slow |
| Watermelon | 25 | Very slow |

**Design note:** Tomato is simultaneously the fastest enemy (speed=100), the toughest at high difficulty (up to 6 wisk hits at skill 3), and the only weapon that always kills it in 1 hit is the Pastry Gun. Level 9 contains only Tomatoes and only a Pastry Gun pickup — a deliberate difficulty spike.

Player speed is not present in the BLK file format; it is hardcoded in `bork.exe`.

### 17.2 Enemy Collision Radius

`[blk:01–10]` Each `action` entry includes a `radius` property (a floating-point value in cell units where 1.0 = full cell width). This is the radius of the enemy's collision circle used for both wall collision and player-proximity checks.

| Enemy | Radius (standard) |
|-------|-------------------|
| Cauliflower | 1.00 |
| Watermelon | 0.99 |
| Tomato | 0.98 |
| Potato | 0.97 |
| Cheese | 0.96 |
| Lemon | 0.95 |
| Egg | 0.94 |
| Cabbage | 0.93 |
| Cucumber | 0.93 |
| Carrot | 0.92 |

`[blk:07]` **Level 7 exception:** In LEVEL07.BLK, the Egg has `radius = 0.40` and the Potato has `radius = 0.70` — significantly smaller than their standard values in all other levels. This makes both enemies much harder to hit with projectiles in Level 7. This appears to be an intentional per-level difficulty adjustment, as all other properties (speed, HP, anims) remain unchanged.

### 17.3 Collision Flags (Thing Entry)

`[blk:01]` Enemy `thing` entries carry three flags that govern different aspects of collision:

| Flag | Present on enemies | Present on weapon pickups | Meaning |
|------|--------------------|--------------------------|---------|
| `set hitable` | Yes | No | Can be targeted and hit by the player's projectile weapons |
| `set wall` | Yes | No | Solid obstacle: blocks player movement using radius-based circle collision |
| `set trans` | Yes | Yes | Sprite uses palette transparency; also marks the thing cell as traversable for map-parsing purposes (see Section 8) |

Weapon pickup `thing` entries carry only `set trans`. The player collects a pickup by walking into its cell — no separate interaction is needed, and the pickup has no collision circle.

---

## 18. Sprite Animation System

### 18.1 Anim Entry Format (Full Detail)

`[blk:01–10]` Each `anim` entry defines one animation clip. The three properties are:

| Property | Meaning |
|----------|---------|
| `panel` | Base filename path (relative to `chef/`, no extension, no frame/view digits) |
| `frames` | Number of sequential frames in the animation |
| `views` | Number of viewing-angle variants (1 = omnidirectional; 3 = directional) |

### 18.2 Sprite File Naming Convention

`[foods/]` Sprite files are named by appending a two-digit suffix to the `panel` base name:

```
{panel}{view_digit}{frame_digit}.PCX
```

- `view_digit` is 0 to (views − 1)
- `frame_digit` is 0 to (frames − 1)

**Examples for Carrot walk anim** (`panel = foods\ca_wlk`, frames=3, views=3):

```
CA_WLK00.PCX   (view 0, frame 0)
CA_WLK01.PCX   (view 0, frame 1)
CA_WLK02.PCX   (view 0, frame 2)
CA_WLK10.PCX   (view 1, frame 0)
CA_WLK11.PCX   (view 1, frame 1)
CA_WLK12.PCX   (view 1, frame 2)
CA_WLK20.PCX   (view 2, frame 0)
CA_WLK21.PCX   (view 2, frame 1)
CA_WLK22.PCX   (view 2, frame 2)
```

**Examples for Carrot throw anim** (`panel = foods\ca_thr`, frames=3, views=1):

```
CA_THR00.PCX   (view 0, frame 0)
CA_THR01.PCX   (view 0, frame 1)
CA_THR02.PCX   (view 0, frame 2)
```

For views=1 animations, the view digit is always `0`. The engine selects the view digit at runtime based on the angle between the camera and the enemy; which view index maps to which angle range is hardcoded in `bork.exe` (not represented in the BLK format).

`[blk:01]` The `thing` entry for an enemy uses `panel = foods\{code}_wlk00` — this is the static map-editor/palette sprite, hardcoded to view 0, frame 0 of the walk animation.

### 18.3 AI State to Animation Mapping

`[blk:01–10]` The `action` entry bridges AI states to anim IDs via five named properties:

| Property | AI State(s) | Views | Notes |
|----------|-------------|-------|-------|
| `walk_anim` | `WANDER`, `CHASE` | 3 | Directional walking; view selected by camera angle |
| `throw_anim` | `CHASE` (attacking) | 1 | Played during an attack; not directional |
| `talk_anim` | `TALK` | 1 | Plays when enemy spots the player; sighting voice line plays concurrently |
| `die_anim` | `DYING` | 1 | Death sequence; plays once through |
| `dead_anim` | `DEAD` | 1 | Single-frame idle displayed while enemy is an edible food item on the floor |

There is no dedicated `idle_anim`; the `WAITING` state presumably displays the first frame of `walk_anim` (view 0, frame 0) as a static sprite. This is consistent with the `thing` entry using `_wlk00` as its panel.

The `EATEN` state removes the entity entirely — no sprite is displayed.

### 18.4 Per-Enemy Animation Frame Counts

`[blk:01–10]` `[foods/]` Frame counts vary per enemy and per animation type. All walk animations use 3 views × 3 frames = 9 PCX files. All `dead_anim` (FNL) entries use 1 frame × 1 view = 1 PCX file.

| Enemy | WLK files (v×f) | THR frames | TLK frames | DIE frames |
|-------|-----------------|------------|------------|------------|
| Carrot | 3×3 = 9 | 3 | 3 | 5 |
| Cabbage | 3×3 = 9 | 3 | 3 | 5 |
| Cauliflower | 3×3 = 9 | 3 | 3 | 3 |
| Cucumber | 3×3 = 9 | 3 | 3 | 3 |
| Cheese | 3×3 = 9 | 3 | 3 | 5 |
| Egg | 3×3 = 9 | **4** | **5** | 5 |
| Lemon | 3×3 = 9 | 3 | 3 | 3 |
| Potato | 3×3 = 9 | 3 | 3 | 3 |
| Tomato | 3×3 = 9 | 3 | 3 | 3 |
| Watermelon | 3×3 = 9 | 3 | 3 | 3 |

`[foods/]` The Egg is the only enemy with non-standard frame counts: 4 throw frames and 5 talk frames. An additional unnumbered file `EG_THR.PCX` also exists in `FOODS/` alongside the numbered frames; its purpose is unknown (possibly a debug or legacy file). The DIE animation length (3 vs 5 frames) may correspond to animation complexity: carrot, cabbage, cheese, cucumber, and egg have 5-frame deaths; the remaining five enemies have 3-frame deaths.

# Customization

[← Back to README](https://github.com/dterracino/color_tools/blob/main/README.md) | [Usage](https://github.com/dterracino/color_tools/blob/main/docs/Usage.md) | [Troubleshooting →](https://github.com/dterracino/color_tools/blob/main/docs/Troubleshooting.md)

---

This document covers the data file formats, user extensions, custom palettes, and configuration options for Color Tools.

## Table of Contents

- [Data Files](#data-files)
  - [colors.json](#colorsjson---css-color-database)
  - [filaments.json](#filamentsjson---3d-printing-filament-database)
  - [maker_synonyms.json](#maker_synonymsjson---maker-name-synonyms)
- [User Data Files (Optional Extensions)](#user-data-files-optional-extensions)
  - [owned-filaments.json](#owned-filamentsjson---filament-ownership-tracking)
- [Custom Palettes](#custom-palettes)
- [Configuration Options](#configuration-options)

---

## Data Files

The data is organized into three separate JSON files in the `data/` directory:

### colors.json - CSS Color Database

Array of color objects with complete color space representations:

```json
[
  {
    "name": "coral",
    "hex": "#FF7F50",
    "rgb": [255, 127, 80],
    "hsl": [16.1, 100.0, 65.7],
    "lab": [67.30, 45.35, 47.49],
    "lch": [67.30, 65.67, 46.3]
  }
]
```

**Note on Cyan and Magenta:** These colors use non-standard values to avoid RGB duplication:

- **cyan**: `#00B7EB` (printer cyan) instead of CSS `#00FFFF`
- **magenta**: `#FF0090` (printer magenta) instead of CSS `#FF00FF`
- **aqua** and **fuchsia** retain the CSS-standard values

This ensures all colors have unique RGB coordinates for reliable dictionary lookups.

### filaments.json - 3D Printing Filament Database

Array of filament objects with manufacturer info and color data:

```json
[
  {
    "id": "bambu-lab-pla-basic-black",
    "maker": "Bambu Lab",
    "type": "PLA",
    "finish": "Basic", 
    "color": "Black",
    "hex": "#000000",
    "td_value": null,
    "other_names": null
  }
]
```

**Field Descriptions:**

- **id** (string, required): Unique record identifier
  - Example: `"bambu-lab-pla-silk-plus-red"`
  - Bundled IDs are preserved once assigned because ownership tracking and
    deterministic exports use them as identity keys.
  - User records use the same required stable ID for searching, overrides,
    ownership tracking, and deterministic HueForge export.
  
- **maker** (string, required): Manufacturer name (canonical form)
  
- **type** (string, required): Filament material type (PLA, PETG, ABS, etc.)
  
- **finish** (string or null): Surface finish or product line (Silk, Matte, Basic, etc.)
  
- **color** (string, required): Color name as labeled by manufacturer
  
- **hex** (string, required): Hex color code
  - Single color: `"#RRGGBB"`
  - Multi-color: `"#RRGGBB-#RRGGBB"` (ordered, dash-separated components)
  
- **td_value** (number or null): Transmission distance in millimeters when
  known. It is not a percentage or a normalized value; see
  [Contributing filament data](../CONTRIBUTING.md#adding-to-the-filament-database).
  
- **other_names** (array of strings or null, optional): Alternative names for this filament
  - Regional variations: `["Premium Red (EU)", "Classic Red (US)"]`
  - Historical names: `["Atomic Age Teal"]` (when manufacturer renames product)
  - Marketing variations: `["Fire Red", "Ferrari Red"]`
  - Only populated when alternatives exist

### maker_synonyms.json - Maker Name Synonyms

Mapping of canonical maker names to common synonyms/abbreviations:

```json
{
  "Bambu Lab": ["Bambu", "BBL"],
  "Paramount 3D": ["Paramount", "Paramount3D"]
}
```

**Synonym Support:** Filament searches automatically support maker synonyms. For example, searching for "Bambu" will find all "Bambu Lab" filaments.

---

## User Data Files (Optional Extensions)

You can extend the core databases with optional files under `data/user/`:

- **user-colors.json** - Add or replace colors using only `name` and `hex`
- **user-filaments.json** - Add filaments or replace complete records by ID
- **user-synonyms.json** - Add or extend maker synonyms (same format as maker_synonyms.json)
- **owned-filaments.json** - Track which filaments you own (v6.0.0+)

User data is automatically loaded and merged with core data. User files are optional and ignored if they don't exist.

**Integrity Verification:** User-file verification is **optional** - you can generate `.sha256` hash files for your user data and active `user-*.json` palettes, then verify them later. Copyable `*.example.json` files are excluded:

```bash
# Generate .sha256 files for user data and user palettes
color-tools --generate-user-hashes

# Verify user-file integrity
color-tools --verify-user-data

# Validate all four user data files and their cross-file references
color-tools --validate-user-files

# Verify everything (core + user data)
color-tools --verify-all
```

If no `.sha256` file exists, user files work without verification - giving you full control.

**Getting Started:** Example files are included in the `data/user/` directory:

- `user-colors.example.json` - Copy/rename to `user-colors.json` to start adding custom colors
- `user-filaments.example.json` - Copy/rename to `user-filaments.json` to start adding custom filaments
- `user-synonyms.example.json` - Copy/rename to `user-synonyms.json` to start adding maker synonyms
- `owned-filaments.example.json` - Copy/rename to `owned-filaments.json` to start tracking owned filaments (v6.0.0+)

**Example user-colors.json:**

```json
[
  {
    "name": "myCustomPurple",
    "hex": "#9B59B6"
  }
]
```

**Example user-filaments.json:**

```json
[
  {
    "id": "my-local-shop-pla-basic-red",
    "maker": "My Local Shop",
    "type": "PLA",
    "finish": "Basic",
    "color": "Red",
    "hex": "#CC0000",
    "td_value": null,
    "other_names": null
  }
]
```

Every filament requires a stable lowercase, hyphenated `id`. Generate the
canonical ID from its maker, type, optional finish, and color name:

```bash
color-tools filament --generate-id --maker "My Local Shop" --type PLA \
  --finish Basic --color Red
```

The command reports whether the ID is available or would replace an existing
record, and suggests the first available `-2`, `-3`, and so on suffix when it
would collide. Hex and TD values are deliberately excluded from the ID so they
can be corrected without breaking owned-filament references.

#### Importing and updating user filaments from Python

The `user_filaments` importer reads this strict source schema into
`FilamentExportData`. `UserFilamentsExporter` then plans an ID-based merge into
`user-filaments.json` without writing by default:

```python
from color_tools import UserFilamentsExporter
from color_tools.importers import import_filaments

data = import_filaments(
    "incoming-user-filaments.json",
    format_name="user_filaments",
)
exporter = UserFilamentsExporter()
plan = exporter.plan(data)

for change in plan.changes:
    print(change.action, change.incoming.id, change.message)
for warning in plan.warnings:
    print("Warning:", warning)

if plan.can_apply:
    exporter.apply(plan)
```

Stable IDs are the only replacement key. The same ID with different fields is
a conflict unless `conflict_policy="replace"` is selected; `"skip"` retains the
current record. A different ID is a distinct filament even when maker, type,
finish, color, or RGB values match. In that descriptive-identity case the plan
reports a warning but retains both IDs, supporting the documented `-2`, `-3`,
and later suffix workflow.

Applying validates the complete effective catalog, rejects a stale plan if the
destination changed after planning, atomically replaces `user-filaments.json`,
and refreshes its SHA-256 sidecar. It does not modify `owned-filaments.json`;
catalog and ownership updates remain independent operations.

**Example user-synonyms.json:**

```json
{
  "Bambu Lab": ["Bambu Labs"],
  "3D Jake": ["3DJake"]
}
```

Maker keys are matched case-insensitively and must identify a maker in the
merged filament database, including makers added through `user-filaments.json`.
User aliases are additive: bundled aliases are never removed. Each alias must
be globally unique after case folding and cannot equal any canonical maker
name. Repeating an alias already assigned to the same maker is an unchanged
no-op; assigning it to another maker is an error.

**Note:** Color names may intentionally replace existing colors. A color cannot
reuse the effective RGB value of any other current color; invalid records are
rejected with the conflicting color and source identified.

### Importing and updating user colors from Python

The `user_colors` importer reads the same minimal `name`/`hex` schema and
returns `PaletteExportData`. All RGB, HSL, LAB, and LCH values are calculated by
Color Tools rather than trusted from the file.

`UserColorsExporter` is state-aware: `plan()` only inspects the proposed merge
and does not write anything. Review its typed changes, then call `apply()`
explicitly. Name changes conflict by default; pass `conflict_policy="replace"`
to intentionally override a system or existing user color by normalized name,
or `"skip"` to leave conflicts unchanged. Reusing another color's RGB value is
never allowed because effective color values must remain unique.

```python
from color_tools import UserColorsExporter
from color_tools.importers import get_importer

imported = get_importer("user_colors").import_palette("incoming-colors.json")
exporter = UserColorsExporter()  # package data directory by default

plan = exporter.plan(imported, conflict_policy="replace")
for change in plan.changes:
    print(change.action, change.incoming.name, change.message)

if plan.can_apply:
    result = exporter.apply(plan)
    print(result.data_written, result.sidecar_written)
```

Applying validates the complete prospective file, refuses a stale plan if the
destination changed after planning, atomically replaces `user-colors.json`, and
refreshes `user-colors.json.sha256`. Supplying `data_dir` to the constructor
targets another Color Tools data directory, which is useful for applications
that keep user data outside the installed package.

### owned-filaments.json - Filament Ownership Tracking

Track which filaments you own for personalized color matching.

When you create an `owned-filaments.json` file with filament IDs, all filament searches automatically default to your owned filaments only - perfect for finding the best match from what you already have on hand!

**Location:** `data/user/owned-filaments.json`

**File Format:**

```json
{
  "owned_filaments": [
    "bambu-lab-pla-matte-charcoal",
    "polymaker-pla-polylite-black",
    "bambu-lab-pla-basic-red"
  ]
}
```

**Getting Started:** An example file is included:

- `owned-filaments.example.json` - Copy/rename to `owned-filaments.json` to start tracking

**How It Works:**

- **Auto-detect:** If file exists with IDs, `filter()` and `nearest_filament()` methods default to `owned=True`
- **No file?** No change - all filaments are searched (backward compatible)
- **Shopping mode:** Pass `owned=False` parameter (API) or `--all-filaments` flag (CLI) to search all filaments
- **User additions:** A new filament in `user-filaments.json` can be marked owned by listing its ID here
- **User overrides:** Ownership follows the stable ID, so replacing a system filament by ID automatically keeps its owned status
- **Validation:** `color-tools --validate-user-files` rejects malformed, duplicate, or unresolved owned IDs after merging system and user filaments

Only IDs belong in this file. Filament product data remains in `filaments.json`
or `user-filaments.json`; it is not duplicated as inventory state. If a user
filament's ID changes, update its ownership reference at the same time.

**CLI Commands:**

```bash
# Add filaments you own
color-tools filament --add-owned "bambu-lab-pla-matte-charcoal"

# List your owned filaments
color-tools filament --list-owned

# Find nearest match (automatically uses owned filaments if file exists)
color-tools filament --nearest --value 255 128 64

# Override to search ALL filaments (shopping/browsing)
color-tools filament --nearest --value 255 128 64 --all-filaments

# Remove a filament from owned list
color-tools filament --remove-owned "bambu-lab-pla-matte-charcoal"
```

**Python API:**

```python
from color_tools import FilamentPalette

# Load palette (auto-loads owned filaments if file exists)
palette = FilamentPalette.load_default()

# Search owned filaments (auto-detected if file exists)
filament, distance = palette.nearest_filament((255, 128, 64))

# Explicitly search owned only
filament, distance = palette.nearest_filament((255, 128, 64), owned=True)

# Override to search ALL filaments
filament, distance = palette.nearest_filament((255, 128, 64), owned=False)

# Manage owned filaments programmatically
palette.add_owned("bambu-lab-pla-matte-charcoal")  # Adds and saves
owned_list = palette.list_owned()  # Returns FilamentRecord objects
palette.remove_owned("bambu-lab-pla-matte-charcoal")  # Removes and saves
```

**Use Cases:**

- **Filament selection:** "What filament do I own that's closest to this color?"
- **Project planning:** Filter to your current inventory when matching colors
- **Shopping mode:** Use `--all-filaments` to browse the full catalog when shopping
- **Inventory management:** Track what's in stock vs what needs restocking

See [Usage Guide - Filament Command](https://github.com/dterracino/color_tools/blob/main/docs/Usage.md#owned-filaments-tracking-v600) for complete CLI documentation.

### User Override System (v3.8.0+)

User files are merged with core data according to each data type's rules.
For colors, each user record contains only `name` and `hex`; the library
calculates RGB, HSL, LAB, and LCH.

#### **Override Behavior:**

- **Color name conflicts**: A user color replaces the current color with the
  same trimmed, case-insensitive name, in the same list position
- **Color RGB conflicts**: A user color cannot reuse another current color's
  effective RGB value; this is validated sequentially as records are merged
- **New colors**: Unique user names append in user-file order
- **Nearest-color ties**: Exact distance ties prefer `user-*` sources, then
  preserve merged-list order
- **Filament ID conflicts**: A user filament with an existing ID replaces the
  complete record at the same list position
- **New filament IDs**: New records append in user-file order; duplicate RGB
  values and product descriptions are allowed because ID defines identity
- **Duplicate user filament IDs**: Rejected within a user file
- **Maker synonyms**: User aliases only extend the aliases for a known maker.
  Alias and maker matching is case-insensitive; aliases must be globally unique
  and cannot shadow a canonical maker name
- **Source tracking**: Every record tracks its source file (colors.json, user-colors.json, cga4.json, etc.)

#### **Override Detection:**

```bash
# Check what user data overrides core data
color-tools --check-overrides
```

**Example output:**

```text
User Override Report
==================================================

Color Loading:
  System colors loaded: 148
  User colors loaded: 2
  Colors overridden by name: 1
  Unique user colors loaded: 1
  Total colors available: 149

Color Changes:
  Overrode red (#FF0000, colors.json) with red (#DC143C, user-colors.json)
  Added brand orange (#FF8533)
```

The report also includes current record totals and active source files. Those
counts depend on the installed release and which optional user files are active.
It receives structured events from the same loaders used by the library; it
does not infer changes from logging output.

#### **Source Information in Output:**

All CLI commands now show the source file:

```bash
$ color-tools color --name red
Name: red [from user-colors.json]
Hex:  #DC143C
RGB:  (220, 20, 60)

$ color-tools color --nearest --value 255 0 0 --space rgb  
Nearest color: red (distance=0.00) [from user-colors.json]
```

#### **Common Use Cases:**

- **Brand colors**: Override "red" with your company's specific red shade
- **Monitor calibration**: Adjust colors for display differences
- **Personal preferences**: Custom color naming and values
- **Regional variations**: Different color standards for different markets
- **Hardware-specific**: Printer or monitor-specific color corrections

#### **Programmatic Access:**

```python
from color_tools import Palette

palette = Palette.load_default()
red_color = palette.find_by_name("red")
print(f"Red color from: {red_color.source}")
# Output: Red color from: user-colors.json
```

---

## Custom Palettes

Color Tools supports custom palettes for retro graphics, pixel art, or specialized color matching. Built-in palettes live in `data/palettes/`; put personal palettes in `data/user/palettes/` so package data remains separate from user data.

### Using Custom Palettes

**Via CLI:**

```bash
# Find nearest color in a built-in palette
python -m color_tools color --palette cga4 --nearest --value 128 64 200 --space rgb

# List all available palettes (both commands show the same information)
color-tools color --palette list
color-tools image --list-palettes

# Use a user palette for image quantization
color-tools image --file photo.jpg --quantize-palette user-mycustom

# Use the same user palette from a custom data directory
color-tools --json DIR image --file photo.jpg --quantize-palette user-mycustom
```

**Via Python API:**

```python
from color_tools import load_palette

# Load built-in palettes
cga = load_palette('cga4')
ega = load_palette('ega16')
vga = load_palette('vga')
web = load_palette('web')

# Find nearest color
nearest, distance = cga.nearest_color((128, 64, 200), space='rgb')
print(f"Nearest color: {nearest.name} ({nearest.hex})")
```

### Built-in Palettes

Built-in system and retro palettes are presentation-style sRGB
representations for simulating how an image would look when displayed by a
given system. They are selected for useful, recognizable image conversion on
modern displays rather than as claims of electrically exact hardware output.
Values can therefore differ from published specifications, emulator tables, or
captured hardware because video standard, hardware revision, analog signal
path, CRT behavior, gamma, and reproduction choices all affect the result.

General-purpose collections such as `crayola` and `web` are ordinary color
collections rather than system-display simulations.

| Palette | Colors | Description |
| --------- | -------- | ------------- |
| `amstrad-cpc` | 27 | Amstrad CPC 3-level RGB hardware palette |
| `apple2` | 6 | Apple II display palette |
| `bbc-micro` | 8 | BBC Micro static physical colors |
| `cga4` | 4 | CGA 4-color (Palette 1, high intensity) |
| `cga16` | 16 | CGA 16-color (full RGBI palette) |
| `colecovision` | 15 | Gamma-corrected TMS9918 CRT-style palette |
| `commodore64` | 16 | Commodore 64 palette |
| `crayola` | 120 | Crayola crayon color collection |
| `ega16` | 16 | EGA 16-color (standard/default palette) |
| `ega64` | 64 | EGA 64-color (full 6-bit RGB palette) |
| `gameboy` | 4 | GB Studio monochrome authoring palette |
| `gameboy-dmg` | 4 | SameBoy DMG-01 screen approximation |
| `gameboy-light` | 4 | SameBoy backlit Game Boy Light approximation |
| `gameboy-pocket` | 4 | Neutral four-level Game Boy Pocket grayscale |
| `intellivision` | 16 | Vivid CRT-style Intellivision STIC palette |
| `macintosh` | 8 | Classic Macintosh system palette |
| `msx1` | 15 | Gamma-corrected TMS9918 CRT-style palette |
| `nes` | 54 | NES display palette |
| `pico8` | 16 | PICO-8 default fantasy-console palette |
| `sms` | 64 | Sega Master System 6-bit RGB palette |
| `sg-1000` | 15 | Gamma-corrected TMS9918 CRT-style palette |
| `tandy16` | 16 | Tandy/PCjr 16-color palette |
| `ti-99-4a` | 15 | Gamma-corrected TMS9918 CRT-style palette |
| `tic80` | 16 | TIC-80 default SWEETIE-16 palette |
| `vga` | 256 | VGA 256-color (Mode 13h palette) |
| `vic-20` | 16 | VIC-I CRT-style display palette |
| `virtualboy` | 4 | Virtual Boy four-level red palette |
| `web` | 216 | Web-safe 216-color palette (6×6×6 RGB cube) |
| `zx-spectrum` | 15 | ZX Spectrum normal/bright display approximation |

### Creating a User Palette

Create a versioned palette document in `data/user/palettes/`. User palette
filenames must begin with `user-`; use the full filename stem when loading the
palette. The required metadata ID must exactly match that filename stem. Each
entry in `palette.colors` requires exactly `name` and `hex`; RGB, HSL, LAB, and
LCH values are calculated from the hex color when loaded. Derived or unknown
fields are rejected so stale cached values cannot be mistaken for authored
data. Files ending in `example.json` are skipped during palette
discovery. For example, save this as
`data/user/palettes/user-mycustom.json`:

```json
{
  "schema_version": 1,
  "metadata": {
    "id": "user-mycustom",
    "name": "My Custom Palette",
    "description": "A small palette for my project."
  },
  "palette": {
    "type": "indexed",
    "colors": [
      {"name": "Primary Red", "hex": "#FF0000"},
      {"name": "Primary Green", "hex": "#00FF00"}
    ]
  }
}
```

Then load it with:

```python
my_palette = load_palette('user-mycustom')
```

User palettes are listed by `color-tools color --palette list` and `color-tools image --list-palettes`. They can also be used with `color --palette user-mycustom` and image quantization via `--quantize-palette user-mycustom`. The Python image API accepts the same optional data-directory path:

```python
from color_tools.image import quantize_image_to_palette

quantized = quantize_image_to_palette(
    "photo.jpg",
    "user-mycustom",
    json_path="path/to/data",
)
```

The `user-` prefix keeps user palette names separate from built-in palette names: `user-gameboy` does not replace `gameboy`. When using a custom data directory with the global `--json DIR` option, keep the same layout beneath that directory (`DIR/palettes/` and `DIR/user/palettes/`).

Example files named `*example.json` are ignored in the available-palette list.
Copy or rename an example to `user-mycustom.json`, then change its
`metadata.id` to `user-mycustom` before using it.

Use `data/palettes/` only when adding or maintaining a built-in palette in the source distribution; those files are covered by the project's data-integrity checks.

---

## Configuration Options

### Multi-Color Configuration

The configuration interface accepts `first` (default), `last`, and `srgb_mean`.
Other planned selection and averaging modes are not accepted yet.
Filament `hex` preserves the exact source text. All components are parsed once
into immutable ordered `rgb_components`, retaining duplicates. `first` selects
the first, `last` the last, and `srgb_mean` averages encoded sRGB channels with
equal weights and Python nearest-even rounding once per channel. Stored LAB
is derived from the final RGB. Means are empirical candidate models, not
predictions of physical pigment mixing.

Compound inputs support any positive number of colors separated by hyphen,
ASCII space, comma, underscore, slash, colon, or semicolon. Spaces may surround
punctuation; empty components/repeated punctuation are errors. Each component
uses 3, 4, 6, or 8 ASCII hex digits, optionally preceded by one `#`.
Four/eight-digit forms use CSS/PNG RGBA byte order, not Windows/Android ARGB.
Alpha is validated but dropped for now. Single-color `hex_to_rgb()` does not
accept separators or surrounding whitespace and raises `ValueError` on invalid
input instead of returning `None`.

Use `effective_hex` for a normalized single-color value. Generic CSV/JSON
exports retain source `hex`, include `rgb_components` and `effective_hex`, and
omit removed `hex2`. AutoForge's single-color column uses `effective_hex`.
GUI export templates provide these same fields, including indexed component
paths. JSON files with `hex2` must move those components into `hex`.

**Via CLI:**

```bash
# Use first color (default)
python -m color_tools filament --nearest --value 255 0 0 --multi-color-mode first

# Use last color
python -m color_tools filament --nearest --value 255 0 0 --multi-color-mode last

# Average encoded sRGB channels
python -m color_tools filament --nearest --value 255 0 0 --multi-color-mode srgb_mean
```

**Via Python API:**

```python
from color_tools import config_context, get_config, reset_config, set_config

set_config(multi_color_mode="last")
snapshot = get_config()  # Current frozen ColorConfig instance, not a copy
with config_context(multi_color_mode="srgb_mean"):
    print(get_config().multi_color_mode)
assert get_config() is snapshot
reset_config()
```

### Configuration Scope and Validation

Settings use `ContextVar`, not a mutable process-wide singleton. New asyncio
tasks inherit their creation context; later updates in sibling tasks are
isolated. Independent threads do not automatically inherit overrides. Set
configuration inside the worker, or explicitly propagate `copy_context()`.
Worker contexts can retain updates across jobs; prefer `config_context` for
temporary overrides.

Nested contexts restore the exact previous instance even after exceptions,
including changes made by `set_config` or `reset_config` inside the block.
Filament records capture settings at construction; existing records do not
change afterward. Palette caches distinguish modes. CLI overrides are scoped
to the command, including GUI/TUI entry points.

`set_config` accepts keyword arguments; `None` leaves a setting unchanged.
Updates validate atomically. Invalid types raise `TypeError`, invalid values
raise `ValueError`:

- `gamut_tolerance`: finite number >= 0, excluding booleans; default 0.01 in
  0-255 RGB channel units.
- `gamut_max_iterations`: integer >= 1, excluding booleans; default 20.
  Larger limits are allowed, but numerical convergence stops the search early.

Version 7.0.0 removes all former individual getters/setters and
`--dual-color-mode`, without compatibility aliases. Replace `mix` with
`srgb_mean` only if an encoded RGB mean is intended; it is not a LAB blend.
The planned `lab_mean` is not available yet. Gamut checks use unrounded RGB,
so sub-integer tolerances are effective. The mapper reduces chroma at constant
LCH lightness/hue, not necessarily to the globally nearest color. Invalid LAB
coordinates or a lightness with no feasible neutral raise `ValueError`.

### Custom Data Directory

Use a custom directory for JSON data files:

**Via CLI:**

```bash
python -m color_tools --json /path/to/custom/data color --name coral
```

**Via Python API:**

```python
from color_tools import Palette, FilamentPalette
from pathlib import Path

custom_dir = Path('/path/to/custom/data')
palette = Palette.load_from_dir(custom_dir)
filament_palette = FilamentPalette.load_from_dir(custom_dir)
```

---

[← Back to README](https://github.com/dterracino/color_tools/blob/main/README.md) | [Usage](https://github.com/dterracino/color_tools/blob/main/docs/Usage.md) | [Troubleshooting →](https://github.com/dterracino/color_tools/blob/main/docs/Troubleshooting.md)

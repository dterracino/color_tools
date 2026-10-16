# Frequently Asked Questions

[← Back to README](https://github.com/dterracino/color_tools/blob/main/README.md) | [Troubleshooting](https://github.com/dterracino/color_tools/blob/main/docs/Troubleshooting.md)

---

## Table of Contents

- [General Questions](#general-questions)
- [Color Spaces](#color-spaces)
- [Distance Metrics](#distance-metrics)
- [3D Printing Filaments](#3d-printing-filaments)
- [User Customization](#user-customization)
- [Image Processing](#image-processing)
- [Contributing](#contributing)

---

## General Questions

### What is Color Tools?

Color Tools is a comprehensive Python library for color science operations, color space conversions, and color matching. It provides perceptually accurate color distance calculations, gamut checking, and extensive databases of CSS colors and 3D printing filament colors.

### Why should I use this instead of other color libraries?

Color Tools offers:

- **Zero dependencies** for the core module (pure Python standard library)
- **Perceptually accurate** color matching using CIEDE2000 and other professional formulas
- **Specialized databases** for CSS colors and 3D printing filaments
- **Context-safe** frozen configuration for threads and asynchronous tasks
- **Data integrity verification** via SHA-256 hashing
- **Optional image processing** for CVD simulation and retro palette conversion

### How do I get started quickly?

```bash
# Install
pip install color-match-tools

# Find a color by name
color-tools color --name coral

# Find the nearest CSS color to an RGB value
color-tools color --nearest --value 255 128 64 --space rgb

# Find matching 3D printing filaments
color-tools filament --nearest --value 255 128 64
```

### What should I know before upgrading to version 7.0?

Version 7.0 is a breaking release and requires Python 3.12 or newer. The most
visible migration points are:

- Nearest-result limits now use `--limit N`; `--count` now prints the number of
  filaments that match a query.
- Multi-color filament components belong in the single `hex` field. The old
  `hex2` field is rejected.
- User colors contain only `name` and `hex`; derived color spaces are calculated
  when loaded.
- User filament records require stable IDs, which also determine overrides.
- Bundled and user palettes use the versioned `schema_version: 1` document
  envelope.
- The old individual configuration accessors and `--dual-color-mode` option
  have been removed in favor of `ColorConfig` and `--multi-color-mode`.

See the [7.0 changelog](../CHANGELOG.md#700---2026-10-14),
[Customization guide](Customization.md), and [Installation guide](Installation.md)
for the complete details. Python 3.10 and 3.11 users should remain on a release
older than 7.0.

### Which optional extra should I install?

The base package has no third-party runtime dependencies. Install only the
features you need:

| Extra | Adds |
| --- | --- |
| `[fuzzy]` | Faster enhanced fuzzy color-name matching |
| `[image]` | Image analysis, conversion, quantization, SVG/HEIF support, and ASE export |
| `[interactive]` | Terminal filament manager and guided wizard |
| `[gui]` | PySide6 desktop filament manager |
| `[logging]` | Rich colorized logging |
| `[mcp]` | MCP server support |
| `[all]` | All user-facing optional features |

For example, use `pip install "color-match-tools[image]"`. See
[Installation](Installation.md#install-from-pypi-recommended) for dependency
details and development extras.

---

## Color Spaces

### What is RGB?

**RGB** (Red, Green, Blue) is the standard color model for digital displays. Each component ranges from 0-255 in 8-bit color. This is what your monitor uses to display colors.

### What is HSL?

**HSL** (Hue, Saturation, Lightness) is a more intuitive color model:

- **Hue**: 0-360 degrees (color wheel position)
- **Saturation**: 0-100% (color intensity)
- **Lightness**: 0-100% (brightness)

### What is LAB (CIELAB)?

**LAB** is a perceptually uniform color space designed to approximate human vision:

- **L*** (Lightness): 0-100
- **a*** (Green to Red): typically -100 to +100
- **b*** (Blue to Yellow): typically -100 to +100

LAB is preferred for color matching because equal numerical differences correspond to roughly equal perceived color differences.

### What is LCH?

**LCH** is the cylindrical representation of LAB:

- **L*** (Lightness): 0-100
- **C*** (Chroma): 0+ (color intensity/saturation)
- **h°** (Hue): 0-360 degrees

LCH is ideal for user interfaces because hue can be adjusted independently, making it more intuitive than LAB for color manipulation.

### When should I use which color space?

| Use Case | Recommended Space |
| ---------- | ------------------- |
| Display/screen colors | RGB |
| User color pickers | HSL or LCH |
| Color matching/comparison | LAB |
| Hue-based adjustments | LCH |
| Printing workflows | LAB |

### Does `--space` affect hex input?

No. `--hex` is always interpreted as RGB and is a shortcut for supplying RGB
channels. On the `color` command, `--space` describes only `--value`; if it is
omitted, `--value` defaults to LAB. On the `convert` command, numeric `--value`
input requires an explicit `--from` space.

```bash
# These are RGB input
color-tools color --nearest --hex "#323232"
color-tools color --nearest --value 50 50 50 --space rgb

# This is LAB input because color --value defaults to LAB
color-tools color --nearest --value 50 50 50
```

### What is gamut and why does it matter?

**Gamut** is the range of colors a device can display or reproduce. LAB can represent colors that are outside the sRGB gamut (what most monitors can show). Use `--check-gamut` to verify if a color can be displayed:

```bash
python -m color_tools convert --check-gamut --value 90 50 100
```

### Why are cyan and magenta different from the CSS standard?

Color Tools uses modified values for **cyan** and **magenta** to avoid RGB duplication issues:

- **Cyan**: `#00B7EB` (true printer cyan) instead of CSS `#00FFFF`
- **Magenta**: `#FF0090` (true printer magenta) instead of CSS `#FF00FF`
- **Aqua**: `#00FFFF` (retains CSS standard)
- **Fuchsia**: `#FF00FF` (retains CSS standard)

**Why the change?** In the CSS standard, cyan and aqua share the same value (`#00FFFF`), as do magenta and fuchsia (`#FF00FF`). This caused RGB lookup collisions where searching by RGB value would only return one color name. Our modified values:

1. Use more accurate printer/subtractive color representations
2. Give each color unique RGB coordinates for reliable lookups
3. Better represent what designers expect from "cyan" and "magenta"

If you need strict CSS compliance, use **aqua** and **fuchsia** instead.

---

## Distance Metrics

### What is Delta E?

**Delta E** (ΔE) is a measure of color difference. Smaller values mean more
similar colors. Values near 1 are often used as a rough just-noticeable
difference, but perception depends on the colors, viewing conditions, observer,
and Delta E formula, so the ranges below are practical guidance rather than
hard boundaries.

| Delta E | Perception |
| --------- | ------------ |
| 0-1 | Not perceptible |
| 1-2 | Perceptible through close observation |
| 2-10 | Perceptible at a glance |
| 11-49 | Colors are more similar than opposite |
| 50+ | Very different colors |

### Which Delta E formula should I use?

- **CIEDE2000** (`de2000`): **Recommended for most applications**. Current gold standard, handles all edge cases well.
- **CIE94** (`de94`): Good balance of accuracy and simplicity. Faster than DE2000.
- **CIE76** (`de76`): Simple Euclidean distance in LAB. Fastest but least accurate.
- **CMC** (`cmc`): Industry standard for textiles. Has configurable lightness/chroma weights.

### What are CMC parameters?

CMC (Color Measurement Committee) allows you to weight lightness vs chroma differences:

- **CMC(2:1)** (`cmc21`): Acceptability threshold (more tolerant of lightness differences)
- **CMC(1:1)** (`cmc11`): Perceptibility threshold (equal weight)
- **Custom**: Use `--cmc-l` and `--cmc-c` for specific weighting

```bash
# CMC with custom weights (emphasize chroma differences)
python -m color_tools color --nearest --value 50 25 30 --metric cmc --cmc-l 1.0 --cmc-c 2.0
```

### Why not just use simple RGB distance?

RGB distance (`euclidean`) doesn't account for how humans perceive color. Two colors with the same RGB distance can look very different to the eye. LAB-based Delta E formulas are designed to match human perception.

---

## 3D Printing Filaments

### How many filaments are in the database?

The database contains **1,545 filaments** from major manufacturers including Bambu Lab, IEMAI, Overture, Polymaker, Sunlu, Paramount 3D, and more.

### How do I find filaments from a specific manufacturer?

```bash
# List all manufacturers
python -m color_tools filament --list-makers

# Find filaments from a specific maker in the complete database
python -m color_tools filament --maker "Bambu Lab" --all-filaments

# Count filaments from a specific maker without listing them
python -m color_tools filament --maker "Bambu Lab" --all-filaments --count

# Use synonyms (Bambu = Bambu Lab)
python -m color_tools filament --maker "Bambu" --type "PLA" --all-filaments
```

If you have an `owned-filaments.json` file, filament queries default to that
inventory. Add `--all-filaments` when you intend to browse or count the complete
database.

### What are maker synonyms?

Maker synonyms allow you to search using common abbreviations or alternate names:

- "Bambu" → "Bambu Lab"
- "Paramount" → "Paramount 3D"
- "BBL" → "Bambu Lab"

### What are multi-color filaments?

Some filaments contain two or more ordered source colors, often because their
appearance changes with viewing angle. The `hex` field stores every component,
for example `#333333-#666666`. Select how records resolve to one effective color
for matching:

```bash
--multi-color-mode first      # Use the first component (default)
--multi-color-mode last       # Use the last component
--multi-color-mode srgb_mean  # Average encoded-sRGB channels
```

All components remain available through `FilamentRecord.rgb_components`.
The mean is a practical color-selection model, not a prediction of physical
pigment mixing.

### What is TD, and why is it useful for HueForge?

TD means **transmission distance**: the approximate thickness, in millimeters,
at which a filament attenuates transmitted light. HueForge uses it to model how
stacked filament layers contribute color, so an RGB or hex value alone is not
enough for a HueForge filament-library record.

Color Tools includes TD values when they are available. Values may originate
from manufacturers, community data, or direct measurements; the database does
not track provenance or claim that all values were measured by one method.
Treat TD as a useful starting point and calibrate important prints for your own
material, printer, and process.

### How do I export filaments for HueForge?

Use `--has-td` so the query contains only records HueForge can use:

```bash
color-tools filament --all-filaments --maker "Bambu Lab" --type PLA \
  --has-td --export hueforge --output bambu-pla-hueforge.json
```

The HueForge exporter is strict: if any selected filament lacks TD, it rejects
the export instead of silently dropping records. Python callers can set the
initial `Owned` value with `HueForgeExportOptions`; generated UUIDs are stable
and derive from Color Tools filament IDs. See
[Usage: Exporting Filaments](Usage.md#filament-command) for the full workflow.

### Why does a filament search show only filaments I own?

The presence of `data/user/owned-filaments.json` makes owned inventory the
default search scope. Use `--all-filaments` for shopping or complete-database
queries:

```bash
color-tools filament --nearest --hex "#336699" --limit 5 --all-filaments
```

In Python, pass `owned=False`. See
[Customization: owned-filaments.json](Customization.md#owned-filamentsjson---filament-ownership-tracking).

### What is the difference between `--count` and `--limit`?

`--count` produces one integer: the number of filaments that would match the
query. `--limit N` caps how many nearest matches are returned. They no longer
mean the same thing in version 7.0.

```bash
# Count all matching Bambu Lab PLA records
color-tools filament --maker "Bambu Lab" --type PLA --all-filaments --count

# Return the five nearest matching records
color-tools filament --nearest --hex "#336699" --all-filaments --limit 5
```

The color command also uses `--limit N` for multiple nearest-color results; it
does not provide the filament query-count operation.

### How do I find alternatives for unavailable filaments?

Use `--limit` to find multiple matches:

```bash
# Find top 5 alternatives to a color
python -m color_tools filament --nearest --value 180 100 200 --limit 5 --all-filaments

# Find alternatives only in PLA
python -m color_tools filament --nearest --value 180 100 200 --type "PLA" \
  --maker "*" --limit 5 --all-filaments
```

---

## User Customization

### How do I override a core color with my own custom color?

Place your custom colors in `data/user/user-colors.json`. Each record contains
exactly `name` and `hex`; the library calculates all other color spaces.

**Tip:** An example file `user-colors.example.json` is included in `data/user/` - copy/rename it to `user-colors.json` to get started.

```json
[
  {
    "name": "red",
    "hex": "#DC143C"
  }
]
```

Your custom "red" replaces the core red record by its trimmed,
case-insensitive name. A new name is appended. A user color is rejected if its
effective RGB value already belongs to any other current color.

### How do I add custom 3D printing filaments or override existing ones?

Create `data/user/user-filaments.json` with your custom filaments.

**Tip:** An example file `user-filaments.example.json` is included in `data/user/` - copy/rename it to `user-filaments.json` to get started.

```json
[
  {
    "id": "my-company-pla-matte-custom-blue",
    "maker": "My Company",
    "type": "PLA",
    "finish": "Matte",
    "color": "Custom Blue",
    "hex": "#0066CC"
  }
]
```

Generate the ID rather than composing it by hand:

```bash
color-tools filament --generate-id --maker "My Company" --type PLA \
  --finish Matte --color "Custom Blue"
```

The ID is the override key. Reusing a system filament ID replaces that complete
record in place; a new ID appends a record. Equal RGB values are allowed and do
not constitute overrides. Duplicate IDs in one user file are rejected. The
generator reports whether an ID would override an existing record and suggests
the first available numeric suffix when you want a distinct record instead.

### How do I add maker synonyms?

Create `data/user/user-synonyms.json` to add aliases for makers in the merged
filament database.

**Tip:** An example file `user-synonyms.example.json` is included in `data/user/` - copy/rename it to `user-synonyms.json` to get started.

```json
{
  "Bambu Lab": ["Bambu Labs"],
  "3D Jake": ["3DJake"]
}
```

Maker keys and aliases are matched case-insensitively. The maker must exist in
the system filaments or `user-filaments.json`. User aliases are always additive
and never replace bundled aliases. Every alias must be globally unique after
case folding and cannot equal a canonical maker name. Repeating an alias for
the same maker is an unchanged no-op; assigning it to another maker is rejected.

### How can I see what user data is overriding core data?

Use the `--check-overrides` flag to see a comprehensive report:

```bash
color-tools --check-overrides
```

This shows:

- How many system and user colors loaded
- Which colors were overridden by name and which were added
- Which filaments are replaced by ID and which are added
- Which maker synonym lists are added, extended, or unchanged
- Source files for all data

### What happens when my user file conflicts with core data?

Each user-data type defines its own conflict rules:

- **Color name conflicts**: Your color replaces the current record with that name
- **Color RGB conflicts**: Reusing another color's RGB value is rejected
- **Exact nearest-color ties**: A `user-*` source sorts first; other ties retain
  the merged record order
- **Filament ID conflicts**: Your complete record replaces the record with the
  same ID; RGB and descriptive fields do not define conflicts
- **Synonym conflicts**: Unknown maker keys, aliases assigned to more than one
  maker, and aliases that shadow canonical maker names are rejected

Color merging therefore produces one deterministic record per normalized name
and effective RGB value before lookups are built.

### Can I disable user overrides temporarily?

Yes. Rename or move the active file outside its exact expected path—for example,
rename `user-colors.json` to `user-colors.json.bak`. You can do this in File
Explorer or with your shell. Renaming the whole `data/user` directory disables
all user data, including owned filaments and user palettes.

For repeatable isolated runs, use the global `--json DIR` option with a separate
data-directory layout instead of repeatedly renaming files. See
[Customization: Custom Data Directory](Customization.md#custom-data-directory).

### How do I verify my user data files haven't been corrupted?

Generate hash files for integrity checking:

```bash
# Generate .sha256 files for user data and user palettes
color-tools --generate-user-hashes

# Verify user-file integrity
color-tools --verify-user-data

# Verify everything (core + user data)
color-tools --verify-all
```

Hash verification detects file changes. To validate JSON schemas, IDs, values,
and the cumulative merge rules without writing anything, run:

```bash
color-tools --validate-user-files
```

Hash files (`.sha256`) are created alongside user data files and active
`user-*.json` palettes, then checked during verification. Copyable
`*.example.json` files are excluded.

### What is the difference between validation and hash verification?

They answer different questions:

- `--validate-user-files` parses `user-colors.json`, `user-filaments.json`, and
  `user-synonyms.json` using the same schema and merge rules as normal loading.
  It detects invalid fields, IDs, values, overrides, and synonym conflicts.
- `--verify-user-data` compares active user files and user palettes with their
  optional `.sha256` sidecars. It detects changes since the hash was generated,
  but does not replace schema validation.
- `--verify-all` verifies protected core data and system palettes, then verifies
  user files that have sidecars.

A user file without a sidecar is still usable: no hash comparison occurs, and
the missing sidecar is not an integrity failure. Run validation after editing
content and regenerate its sidecar only after you approve the change. See
[Troubleshooting: Data Integrity Verification](Troubleshooting.md#data-integrity-verification).

---

## Image Processing

### What extras do I need for image processing?

Install with the `[image]` extra:

```bash
pip install color-match-tools[image]
```

This installs the complete image extra, including Pillow, NumPy, image-analysis
libraries, HEIC/SVG support, and the optional Adobe ASE dependency.

### What is CVD (Color Vision Deficiency)?

CVD refers to colorblindness. Color Tools can simulate and correct for:

- **Protanopia**: Reduced red sensitivity
- **Deuteranopia**: Reduced green sensitivity (most common)
- **Tritanopia**: Reduced blue sensitivity (rare)

### How do I test if my images are accessible to colorblind users?

```bash
# Simulate deuteranopia (most common colorblindness)
python -m color_tools image --file chart.png --cvd-simulate deuteranopia --output test.png
```

### How do I convert images to retro palettes?

```bash
# Convert to CGA 4-color
python -m color_tools image --file photo.jpg --quantize-palette cga4

# Use dithering for smoother gradients
python -m color_tools image --file photo.jpg --quantize-palette gameboy --dither
```

### What palettes are available for image quantization?

Built-in system and retro palettes are presentation-style sRGB
representations. Their purpose is to produce a useful visual simulation of how
the selected system would present an image, not to guarantee electrically
exact RGB values for every hardware revision, region, analog signal path,
display, capture, specification, or emulator. Differences from other published
tables can therefore be intentional.

**To see all available palettes (core + user) with color counts:**

```bash
# Using color command
color-tools color --palette list

# Using image command
color-tools image --list-palettes
```

Both commands show the same information: palette names and the number of colors in each.

**Core palettes include:**

- Classic computers: `amstrad-cpc`, `apple2`, `bbc-micro`, `cga4`, `cga16`,
  `commodore64`, `ega16`, `ega64`, `macintosh`, `msx1`, `tandy16`,
  `ti-99-4a`, `vga`, `vic-20`, and `zx-spectrum`
- Consoles and handhelds: `gameboy`, `gameboy-dmg`, `gameboy-light`,
  `gameboy-pocket`, `colecovision`, `intellivision`, `nes`, `sg-1000`, `sms`,
  and `virtualboy`
- Fantasy consoles: `pico8` and `tic80`
- General color collections: `crayola` and `web`

### Can I create custom retro palettes?

Yes! Create custom palettes in `data/user/palettes/` with `user-` prefix:

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
      {"name": "MyRed", "hex": "#FF0000"},
      {"name": "MyBlue", "hex": "#0000FF"}
    ]
  }
}
```

**Important:** User palette files **must** start with the `user-` prefix, and
`metadata.id` must exactly match the filename stem. For the example above, the
filename is `user-mycustom.json` and the ID is `user-mycustom`.

Only `metadata.id` and `metadata.name` are required. `description` and
`release_year` are optional. The `schema_version`, `metadata`, `palette.type`,
and `palette.colors` envelope is required so user and bundled palettes follow
the same validated format.

Each entry in `palette.colors` needs only `name` and `hex`. RGB, HSL, LAB, and
LCH values are calculated from hex when loaded, so they should not be added to
the file; unknown fields are rejected. Files ending in `example.json` are
ignored by palette discovery; copy or rename the example and update its
metadata ID before using it.

**Features:**

- **No core palette conflicts**: `user-gameboy.json` won't override core `gameboy`
- **Automatic discovery**: Your palettes appear in `--palette list`
- **Full CLI integration**: Use with `--palette user-mycustom`
- **Image processing support**: Works with image quantization

**Usage:**

```bash
# List all available palettes (core + user)
color-tools color --palette list

# Use your custom palette
color-tools color --palette user-mycustom --nearest --value 128 64 200 --space rgb

# Image processing with custom palette
python -m color_tools image --file photo.jpg --quantize-palette user-mycustom
```

---

## Contributing

### How do I set up for development?

```bash
git clone https://github.com/dterracino/color_tools.git
cd color_tools
pip install -r requirements-dev.txt
pip install -e .
```

### Can I modify the color science constants?

**NO.** The color science constants in `constants.py` represent fundamental values from international standards (CIE, sRGB specification). Modifying them would break color accuracy.

To verify constants haven't been tampered with:

```bash
python -m color_tools --verify-constants
```

### How do I add new filaments or colors?

For personal use, create user data files:

- `user-colors.json` for custom colors
- `user-filaments.json` for custom filaments
- `user-synonyms.json` for custom maker synonyms

For contributing to the bundled filament database, use the
[filament data issue form](https://github.com/dterracino/color_tools/issues/new?template=filament_data.yml);
no Git or JSON editing is required. Contributors who prefer a code change
should follow [CONTRIBUTING.md](../CONTRIBUTING.md) and include the source and
review details described there rather than editing protected data casually.

### How do I update hashes after modifying data files?

Use the automated tooling:

```bash
python tooling/update_hashes.py --autoupdate
```

See [Troubleshooting: Data Integrity Verification](Troubleshooting.md#data-integrity-verification)
for verification behavior and recovery guidance.

### Where do I report bugs or request features?

Open an issue on GitHub: [https://github.com/dterracino/color_tools/issues](https://github.com/dterracino/color_tools/issues)

---

[← Back to README](https://github.com/dterracino/color_tools/blob/main/README.md) | [Troubleshooting](https://github.com/dterracino/color_tools/blob/main/docs/Troubleshooting.md)

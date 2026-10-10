# Usage

[← Back to README](https://github.com/dterracino/color_tools/blob/main/README.md) | [Installation](https://github.com/dterracino/color_tools/blob/main/docs/Installation.md) | [Customization →](https://github.com/dterracino/color_tools/blob/main/docs/Customization.md)

---

Color Tools can be used in three ways:

1. **As a Python Library**: Import functions directly in your Python code
2. **As a CLI Tool**: Use `python -m color_tools` from the repository
3. **As an Installed Command**: Use `color-tools` command after `pip install`

## Table of Contents

- [Library Usage](#library-usage)
  - [Basic Examples](#basic-examples)
  - [Common Library Functions](#common-library-functions)
  - [Data Structures](#data-structures)
- [CLI Usage](#cli-usage)
  - [Interactive Wizard](#interactive-wizard-requires-interactive-extra)
  - [Color Command](#color-command)
  - [Filament Command](#filament-command)
    - [Owned Filaments Tracking](#owned-filaments-tracking-v600)
  - [Convert Command](#convert-command)
  - [Image Command](#image-command-requires-image-extra)
  - [Global Arguments](#global-arguments)
- [Logging](#logging)
- [Examples](#examples)

---

## Library Usage

Import and use color_tools functions in your Python code.

### Basic Examples

```python
from color_tools import (
    FilamentCollections,
    FilamentPalette,
    Palette,
    delta_e_2000,
    hex_to_rgb,
    rgb_to_lab,
)

# Convert hex to RGB (supports both 3-char and 6-char hex codes)
rgb1 = hex_to_rgb("#FF8040")  # 6-character hex
rgb2 = hex_to_rgb("#F80")     # 3-character hex (expanded to #FF8800)
print(f"6-char hex RGB: {rgb1}")  # RGB: (255, 128, 64)
print(f"3-char hex RGB: {rgb2}")  # RGB: (255, 136, 0)

# Convert RGB to LAB color space
lab = rgb_to_lab((255, 128, 64))
print(f"LAB: {lab}")  # LAB: (67.05, 42.83, 74.02)

# Calculate color difference between two LAB colors
color1 = (50, 25, -30)
color2 = (55, 20, -25)
difference = delta_e_2000(color1, color2)
print(f"Delta E: {difference}")

# Load CSS color palette and find nearest color
palette = Palette.load_default()
nearest, distance = palette.nearest_color(lab, space="lab")
print(f"Nearest CSS color: {nearest.name} (distance: {distance:.2f})")

# Load a retro/classic palette (CGA, EGA, VGA, Web Safe)
from color_tools import load_palette

cga = load_palette('cga4')  # Classic CGA 4-color palette
color, distance = cga.nearest_color((128, 64, 200), space='rgb')
print(f"Nearest CGA color: {color.name} ({color.hex})")

# Available palettes: Use color-tools color --palette list to see all 20 core palettes
ega = load_palette('ega16')     # Standard EGA 16-color palette
vga = load_palette('vga')       # VGA 256-color palette (Mode 13h)
web = load_palette('web')       # Web-safe 216-color palette
crayola = load_palette('crayola')  # 120 Crayola crayon colors
pico8 = load_palette('pico8')   # PICO-8 fantasy console 16-color palette

# Error handling - helpful messages if palette doesn't exist
try:
    palette = load_palette('unknown')
except FileNotFoundError as e:
    print(e)  # Lists all available palettes

# Load filament palette and search
filament_palette = FilamentPalette.load_default()
filament, distance = filament_palette.nearest_filament((180, 100, 200))
print(f"Nearest filament: {filament.maker} {filament.type} - {filament.color}")

# Filter filaments by criteria (supports maker synonyms)
pla_filaments = filament_palette.filter(type_name="PLA", maker="Bambu")  # "Bambu" finds "Bambu Lab"
print(f"Found {len(pla_filaments)} Bambu Lab PLA filaments")

# Reuse case-insensitive criteria for inclusion and exclusion
from color_tools import FilamentFilterCriteria

available_pla = filament_palette.filter_by_criteria(
    include=FilamentFilterCriteria(type_name="pla"),
    exclude=FilamentFilterCriteria(maker="bambu", finish="silk"),
)
nearest_pla, distance = filament_palette.nearest_filament_by_criteria(
    (180, 100, 200),
    include=FilamentFilterCriteria(type_name=["PLA", "PETG"]),
    exclude=FilamentFilterCriteria(finish="silk"),
)

# Access predefined immutable collections without configuring filters
bambu_basic = FilamentCollections.BAMBU_PLA_BASIC
bambu_matte = FilamentCollections.BAMBU_PLA_MATTE
bambu_basic_and_matte = FilamentCollections.BAMBU_PLA_BASICMATTE

# Validate color names against hex codes
from color_tools.validation import validate_color

result = validate_color("light blue", "#ADD8E6")
if result.is_match:
    print(f"✓ Valid! '{result.name_match}' matches {result.hex_value}")
    print(f"  Confidence: {result.name_confidence:.0%}, Delta E: {result.delta_e:.2f}")
else:
    print(f"✗ No match: {result.message}")
    print(f"  Suggested: '{result.name_match}' ({result.suggested_hex})")

# Image transformations (requires [image] extra)
from color_tools.image import simulate_cvd_image, quantize_image_to_palette

# Test accessibility - see how colorblind users view your image
sim_image = simulate_cvd_image("chart.png", "deuteranopia")
sim_image.save("colorblind_simulation.png")

# Convert to retro CGA palette with dithering
retro_image = quantize_image_to_palette("photo.jpg", "cga4", dither=True)
retro_image.save("retro_cga4.png")

# Convert to Game Boy aesthetic
gameboy_image = quantize_image_to_palette("artwork.png", "gameboy")
gameboy_image.save("gameboy_style.png")
```

### Common Library Functions

#### Color Conversions

- `rgb_to_lab()`, `lab_to_rgb()` - RGB ↔ LAB conversion (most common)
- `rgb_to_lab_array()` - shape-preserving NumPy conversion for sRGB arrays shaped `(..., 3)`;
  its LAB output can be passed directly to `delta_e_2000_array()` (requires the `[image]` extra)
- `rgb_to_lch()`, `lch_to_rgb()` - RGB ↔ LCH conversion  
- `rgb_to_hsl()`, `hsl_to_rgb()` - RGB ↔ HSL conversion (0-360, 0-100, 0-100 range)
- `rgb_to_winhsl240()` - RGB → winHSL240: Windows OS (Paint, WordPad, Win32 GDI) — H: 0–239, S/L: 0–240
- `rgb_to_winhsl255()` - RGB → winHSL255: Microsoft Office colour picker — H: 0–254, S/L: 0–255
- `rgb_to_winhsl()` - Alias for `rgb_to_winhsl240()` (backward compatibility)
- `hex_to_rgb()`, `rgb_to_hex()` - Hex ↔ RGB conversion
  - Supports 3-character shorthand (`#F00` or `F00` → `(255, 0, 0)`)
  - Supports 6-character standard (`#FF0000` or `FF0000` → `(255, 0, 0)`)
  - Works with or without `#` prefix
- `lab_to_lch()`, `lch_to_lab()` - LAB ↔ LCH conversion
- `rgb_to_xyz()`, `xyz_to_rgb()` - RGB ↔ XYZ conversion (CIE standard)
- `xyz_to_lab()`, `lab_to_xyz()` - XYZ ↔ LAB conversion (for advanced use)
- `rgb_to_cmy()`, `cmy_to_rgb()` - RGB ↔ CMY conversion (0-100% per channel; no black)
- `rgb_to_cmyk()`, `cmyk_to_rgb()` - RGB ↔ CMYK conversion (0-100% per channel; K extracts black)

#### Distance Metrics

- `delta_e_2000()` - CIEDE2000 (recommended)
- `delta_e_2000_array()` - vectorized CIEDE2000 for NumPy arrays (requires the `[image]` extra)
- `delta_e_94()` - CIE94
- `delta_e_76()` - CIE76
- `delta_e_cmc()` - CMC color difference
- `euclidean()` - Simple Euclidean distance

#### Gamut Operations

- `is_in_srgb_gamut()` - Check if LAB color is displayable
- `find_nearest_in_gamut()` - Find closest displayable color
- `clamp_to_gamut()` - Force color into sRGB gamut

#### Color Harmonies

- `generate_harmony()` - Generate an LCH-based harmony from an RGB tuple
- `generate_harmony_lch()` - Generate a harmony directly from an LCH tuple

```python
from color_tools import generate_harmony, generate_harmony_lch

# Primary RGB API
calm_triad = generate_harmony(
  (224, 0, 107),
  "triadic",
  mood="calm",
  tone="dark",
)

# Direct LCH API for advanced workflows
warm_complement = generate_harmony_lch(
  (48.15, 76.58, 4.77),
  "complementary",
  mood="warm",
)

for color in calm_triad.colors:
  print(color.ideal_lch, color.hex, color.gamut_delta_e)
```

Supported schemes are `analogous`, `complementary`, `split-complementary`, `triadic`,
`square`, `tetradic`, `monochromatic`, `rainbow`, and `full-spectrum`. Rainbow and
full-spectrum are aliases that produce six colors at 60-degree intervals.

Mood and tone compose with the selected harmony:

```text
base color + harmony + mood + tone
```

| Mood | Lightness | Chroma and temperature emphasis |
| --- | --- | --- |
| `warm` | Preserved | Strengthens warm hues and subdues cool hues |
| `cool` | Preserved | Strengthens cool hues and subdues warm hues |
| `happy` | Raised | Higher chroma with warm emphasis |
| `calm` | Slightly raised | Lower chroma with cool emphasis |
| `intense` | Increased contrast around mid-lightness | Substantially higher chroma |
| `sad` | Lowered | Lower chroma with cool emphasis |
| `energetic` | Alternates lighter and darker | Higher chroma |

The independent `tone` parameter accepts `normal`, `dark`, or `light`. Dark and light use
proportional lightness shifts, which avoid the clipping caused by fixed additions or
subtractions. Mood is applied first, tone second, and sRGB gamut mapping last.

The base color remains unchanged by default so the requested anchor color is represented
exactly. Set `grade_base=True` to apply mood and tone to every color, including the base.

Mood presets are opinionated design heuristics. Emotional color associations vary by culture,
context, medium, and viewer. Warm and cool presets preserve harmony hue angles; they establish
temperature emphasis through chroma rather than forcing every palette member into one hue
family.

#### Palettes

- `Palette.load_default()` - Load CSS color database
- `load_palette(name)` - Load retro/classic palette (use `color-tools color --palette list` to see all 20 available)
- `FilamentPalette.load_default()` - Load filament database
- `palette.nearest_color()` - Find nearest color match
- `palette.find_by_name()` - Look up color by name
- `palette.find_by_rgb()` - Look up by exact RGB value
- `palette.find_by_lab()` - Look up by LAB value (with rounding)
- `palette.find_by_lch()` - Look up by LCH value (with rounding)
- `filament_palette.nearest_filament()` - Find nearest filament
- `filament_palette.filter()` - Filter by maker, type, finish, color (supports maker synonyms)
- `filament_palette.filter_by_criteria()` - Apply reusable maker, type, finish, and color inclusions and exclusions
- `filament_palette.nearest_filament_by_criteria()` - Find the nearest filament within reusable criteria
- `filament_palette.find_by_maker()` - Get all filaments from a maker (supports synonyms)
- `filament_palette.find_by_type()` - Get all filaments of a type

`FilamentFilterCriteria` accepts one string or an iterable for `maker`, `type_name`,
`finish`, and `color`. Values within a field use OR semantics; active fields use AND semantics.
Matching, including maker synonyms, ignores case and surrounding whitespace. An exclusion
removes a record only when every active exclusion field matches. Empty exclusion criteria
exclude nothing. The existing filtering and nearest-search methods remain available with
their original signatures.

For color naming, `generate_color_names()` eagerly returns a list of `(name, match_type)`
tuples with one CSS palette load. `iter_color_names()` provides the same results lazily and
does not load the palette until its first input is requested.

#### Configuration

- `set_dual_color_mode()` - Set how dual-color filaments are handled
- `get_dual_color_mode()` - Get current dual-color mode

#### Validation

- `validate_color()` - Validate if hex code matches a color name using fuzzy matching and Delta E
  - Automatically uses `rapidfuzz` if installed, otherwise falls back to hybrid matcher
  - Returns `ColorValidationRecord` with match confidence, suggested hex, and Delta E distance
  - Example: `validate_color("light blue", "#ADD8E6")` → validates color name/hex pairing

#### Export

- `get_exporter()` - Create a fresh exporter instance by format identifier
- `list_export_formats()` - Discover registered formats, filtered by data type and dependency availability
- `export_colors()` - Backward-compatible facade for exporting raw color records
- `export_filaments()` - Backward-compatible facade for exporting filament records
- `PaletteExportData` and `PaletteMetadata` - Supply palette-level metadata to compatible formats
- `ExportOptionsBase` subclasses - Provide strongly typed configuration for a single export operation
- `generate_filename()` - Generate timestamped filenames

Available format identifiers:

- Colors and filaments: `csv`, `json`
- Colors: `ase`, `aseprite`, `css`, `glsl`, `gpl`, `hex`, `jasc_pal`, `kpl`, `lospec`,
  `paintnet`, `palette_lut`, `python`, `riff_pal`, `scribus`, `sketchpalette`, `soc`,
  `swatch_image`
- Filaments: `autoforge`

`ase` requires the `swatch` package and `swatch_image` requires Pillow. Both are installed by
the `[image]` extra. By default, `list_export_formats()` omits formats whose dependencies are
unavailable; pass `available_only=False` to list every registered format.

#### PNG Writing (stdlib, no Pillow)

- `from color_tools.image import SimplePNGWriter` — write RGB color strips as PNG without Pillow

```python
from color_tools.image import SimplePNGWriter
from color_tools import load_palette

# Write a 1×N LUT strip (for GLSL shaders)
palette = load_palette('nes')
colors = [r.rgb for r in palette.records]
SimplePNGWriter(colors, swatch_width=1, swatch_height=1).save("nes_lut.png")

# Write a preview strip (32×32 px swatches)
SimplePNGWriter(colors, swatch_width=32, swatch_height=32).save("nes_preview.png")

# Get raw bytes without writing a file
png_bytes = SimplePNGWriter(colors).to_bytes()
```

#### Exporting a Custom RGB Palette

Create a palette directly from RGB tuples, then choose an export format:

```python
from color_tools import Palette, PaletteMetadata, export_palette

rgb_colors = [
    (255, 127, 80),
    (30, 144, 255),
    (50, 205, 50),
]

palette = Palette.from_rgb(rgb_colors, auto_name=True)

output_path = export_palette(
    palette,
    "aseprite",
    "my_palette.aseprite",
    metadata=PaletteMetadata(name="My Custom Palette", columns=3),
)
print(f"Exported to {output_path}")
```

By default, `auto_name=False` produces `Color 1`, `Color 2`, etc. Enable it for
built-in CSS/descriptive names, or supply explicit names:

```python
palette = Palette.from_rgb(
    rgb_colors,
    names=["Accent", "Background", "Highlight"],
)

# Reuse the same palette with other formats
export_palette(palette, "gpl", "my_palette.gpl")
export_palette(palette, "json", "my_palette.json")
```

Explicit names override auto-naming and must match the number of colors.
RGB inputs require three integers from 0 to 255; derived color-space values are
computed automatically. Order and duplicates are preserved. Hex inputs are also
supported with `Palette.from_hex(["#f00", "#0f0", "#00f"])`.

Use `aseprite` with **`.aseprite`** for Aseprite's native swatch document;
`ase` with **`.ase`** remains Adobe Swatch Exchange and requires `swatch`.
Aseprite exports prepend a named transparent-black entry at index zero by default.
Input colors remain opaque, shift by one index, and are not modified. Color names
are preserved, and `columns` controls layout including the added slot.
To export only your supplied colors:

```python
from color_tools.exporters import AsepriteExportOptions

export_palette(
    palette, "aseprite", "my_palette.aseprite",
    options=AsepriteExportOptions(include_transparent=False),
)
```

Up to 256 total entries use indexed pixels; larger palettes use RGBA. With the
transparent entry enabled, 256 input colors therefore produce an RGBA document.
The input limit is 65,534 colors by default, or 65,535 with transparency disabled.
The palette name becomes the background layer name; other palette
metadata is not preserved by this format.

#### Exporting GLSL Shader Palettes

The dependency-free `glsl` exporter writes reusable shader source as a constant
array, named constants, or preprocessor defines. Values are normalized to 0.0-1.0
by default and use `vec3`; enable alpha to emit opaque `vec4` values.

```python
from color_tools.exporters import GLSLExportOptions

export_palette(
    palette,
    "glsl",
    "my_palette.glsl",
    options=GLSLExportOptions(
        representation="defines",
        normalized=False,
        include_alpha=True,
        identifier_prefix="GAME_",
    ),
)
```

Raw 0-255 channels remain GLSL floating-point literals such as `255.0` and
`0.0`. Set `representation="array"` for indexed access or
`representation="constants"` for named `const` values. `include_version=True`
places `#version 330 core` first; customize it with `version`. Color names are
converted to legal, unique GLSL identifiers for constants and defines.

**Advanced Export Examples:**

```python
from color_tools import FilamentPalette, Palette, export_filaments, export_colors
from color_tools.exporters import get_exporter, list_export_formats
from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.palette_metadata import PaletteMetadata
from color_tools.exporters.swatch_image_exporter import SwatchImageOptions

# Discover currently usable color exporters
formats = list_export_formats("colors")

# Export raw color records through the registry
color_palette = Palette.load_default()
get_exporter("jasc_pal").export_colors(
  color_palette.records,
  "all_colors.pal",
)

# Preserve palette-level metadata
palette_data = PaletteExportData(
  colors=color_palette.records[:8],
  metadata=PaletteMetadata(
    name="Sample Palette",
    author="Color Tools",
    description="An eight-color example.",
    columns=4,
    tags=("sample", "documentation"),
  ),
)
get_exporter("json").export_palette(palette_data, "sample_palette.json")

# Configure an individual export without mutating the exporter instance
get_exporter("swatch_image").export_palette(
  palette_data,
  "sample_palette.png",
  options=SwatchImageOptions(
    show_rgb=True,
    show_lab=True,
    show_lch=True,
  ),
)

# Existing facade calls remain supported; format precedes output path
filament_palette = FilamentPalette.load_default()
matte_filaments = filament_palette.filter(finish="Matte")
export_filaments(matte_filaments, "csv", "matte_filaments.csv")
export_colors(color_palette.records, "hex", "all_colors.hex")
```

Call `export_colors()` for an ordered list of `ColorRecord` objects when palette-level metadata
is unnecessary. Call the public `export_palette()` helper with a `Palette` and optional
`metadata`, or with `PaletteExportData` containing its own metadata. For direct exporter
calls, use `get_exporter(...).export_palette(palette_data, ...)`. Each format preserves
only the metadata fields it supports, such as name, author, description, columns, tags,
or custom properties.
Formats that do not support palette metadata safely fall back to raw color export.

### Data Structures

The library uses immutable dataclasses for color and filament records:

```python
# ColorRecord - returned by Palette methods
color = palette.find_by_name("coral")
print(color.name)   # "coral"
print(color.hex)    # "#FF7F50"
print(color.rgb)    # (255, 127, 80)
print(color.hsl)    # (16.1, 100.0, 65.7)
print(color.lab)    # (67.3, 45.4, 47.5)
print(color.lch)    # (67.3, 65.7, 46.3)

# FilamentRecord - returned by FilamentPalette methods
filament, distance = filament_palette.nearest_filament((255, 0, 0))
print(filament.id)      # e.g., "polymaker-pla-polymax-red"
print(filament.maker)   # e.g., "Polymaker"
print(filament.type)    # e.g., "PLA"
print(filament.finish)  # e.g., "PolyMax"
print(filament.color)   # e.g., "Red"
print(filament.hex)     # e.g., "#ED2F20"
print(filament.rgb)     # e.g., (237, 47, 32)
print(filament.lab)     # e.g., (48.2, 68.1, 54.3) - computed on demand
print(filament.lch)     # e.g., (48.2, 87.4, 38.6) - computed on demand
print(filament.other_names)  # e.g., ["Classic Red"] or None
```

#### Data Classes Quick Reference

All data classes are immutable (frozen) with comprehensive docstrings. See [API Documentation](https://dterracino.github.io/color_tools/) for full details.

| Class | Module | Purpose | Key Fields | Full Docs |
| ------- | -------- | --------- | ------------ | ----------- |
| **ColorRecord** | `palette` | Named CSS color with precomputed color space values | `name`, `hex`, `rgb`, `lab`, `lch`, `hsl` | [API](https://dterracino.github.io/color_tools/api/color_tools.palette.html#color_tools.palette.ColorRecord) |
| **FilamentRecord** | `filament_palette` | 3D printing filament color (handles dual-color variants) | `maker`, `type`, `color`, `hex`, `rgb` (property), `lab`, `lch` | [API](https://dterracino.github.io/color_tools/api/color_tools.filament_palette.html#color_tools.filament_palette.FilamentRecord) |
| **ColorValidationRecord** | `validation` | Color name/hex validation results with fuzzy matching | `is_match`, `name_match`, `name_confidence`, `delta_e`, `message` | [API](https://dterracino.github.io/color_tools/api/color_tools.validation.html#color_tools.validation.ColorValidationRecord) |
| **ColorCluster** | `image` | K-means color cluster from image (requires [image] extra) | `centroid_rgb`, `centroid_lab`, `pixel_count`, `pixel_indices` | [API](https://dterracino.github.io/color_tools/api/color_tools.image.html#color_tools.image.ColorCluster) |
| **ColorChange** | `image` | Before/after luminance redistribution for HueForge | `original_rgb`, `new_rgb`, `delta_e`, `hueforge_layer` | [API](https://dterracino.github.io/color_tools/api/color_tools.image.html#color_tools.image.ColorChange) |

**Notes:**

- All RGB values are tuples: `(r, g, b)` with 0-255 range
- LAB values: `(L, a, b)` where L is 0-100, a/b are roughly -128 to +127
- LCH values: `(L, C, H)` where L is 0-100, C is 0-100+, H is 0-360°
- HSL values: `(H, S, L)` where H is 0-360°, S/L are 0-100%
- FilamentRecord's `rgb`, `lab`, and `lch` are computed properties (not stored)
- Validation uses fuzzy matching - install `[fuzzy]` extra for improved results: `pip install color-match-tools[fuzzy]`
- Image classes require `[image]` extra: `pip install color-match-tools[image]`

---

## CLI Usage

The CLI provides three main commands: `color`, `filament`, and `convert`.

### Color Command

Search and query the CSS color database.

#### Find Color by Name

```bash
python -m color_tools color --name "coral"
python -m color_tools color --name "steelblue"
```

#### Find Nearest Color by Value

```bash
# Find nearest CSS color to RGB(128, 64, 200) using CIEDE2000
python -m color_tools color --nearest --value 128 64 200 --space rgb

# Find top 3 nearest colors
python -m color_tools color --nearest --value 128 64 200 --space rgb --count 3

# Find nearest using LAB values with CIE94 metric
python -m color_tools color --nearest --value 50 25 -30 --space lab --metric de94

# Find nearest using HSL values
python -m color_tools color --nearest --value 16.1 100 65.7 --space hsl

# Find nearest using LCH values (perceptually uniform cylindrical space)
python -m color_tools color --nearest --value 67.3 65.7 46.3 --space lch

# Use CMC color difference formula
python -m color_tools color --nearest --value 70 15 45 --space lab --metric cmc --cmc-l 2.0 --cmc-c 1.0
```

**Color Command Arguments:**

- `--name NAME`: Find exact color by name (case-insensitive)
- `--nearest`: Find the closest color to specified value
- `--value V1 V2 V3`: Color value tuple (format depends on `--space`)
- `--space {rgb,hsl,lab,lch}`: Color space of input value (default: lab)
- `--metric {euclidean,de76,de94,de2000,cmc,cmc21,cmc11}`: Distance metric (default: de2000)
- `--cmc-l FLOAT`: CMC lightness parameter (default: 2.0)
- `--cmc-c FLOAT`: CMC chroma parameter (default: 1.0)
- `--count N`: Return top N nearest colors instead of just one (default: 1, max: 50)
- `--palette NAME`: Use retro/classic palette instead of CSS colors (use `--palette list` to see all available)

#### Custom Palettes

Use retro/classic color palettes for vintage graphics, pixel art, or color quantization:

```bash
# Find nearest CGA 4-color match (classic gaming palette)
python -m color_tools color --palette cga4 --nearest --value 128 64 200 --space rgb

# Find nearest EGA 16-color match
python -m color_tools color --palette ega16 --nearest --value 255 128 0 --space rgb

# Find nearest VGA 256-color match (Mode 13h)
python -m color_tools color --palette vga --nearest --value 100 200 150 --space rgb

# Find nearest web-safe color (6×6×6 RGB cube)
python -m color_tools color --palette web --nearest --value 123 200 88 --space rgb
```

**Available Palettes:**

- `cga4` - CGA 4-color (Palette 1, high intensity): Black, Light Cyan, Light Magenta, White
- `cga16` - CGA 16-color (full RGBI palette)
- `ega16` - EGA 16-color (standard/default palette)
- `ega64` - EGA 64-color (full 6-bit RGB palette)
- `vga` - VGA 256-color (Mode 13h palette)
- `web` - Web-safe 216-color palette (6×6×6 RGB cube)

### Harmony Command

Generate an LCH-based harmony from a hex color or from RGB/LCH values:

```bash
# Basic triadic harmony
python -m color_tools harmony --type triadic --hex "#E0006B"

# Compose a mood and tone with the harmony
python -m color_tools harmony --type complementary --hex "#E0006B" --mood calm --tone dark

# Generate directly from RGB values
python -m color_tools harmony --type analogous --value 224 0 107 --space rgb

# Generate directly from LCH values
python -m color_tools harmony --type square --value 48.15 76.58 4.77 --space lch

# Grade the base color along with generated colors
python -m color_tools harmony --type triadic --hex "#E0006B" --mood happy --grade-base

# Preserve out-of-gamut ideal colors without mapping them to sRGB
python -m color_tools harmony --type complementary --value 50 150 20 --space lch --no-gamut-map
```

Harmony arguments:

- `--type SCHEME`: Generate `analogous`, `complementary`, `full-spectrum`, `monochromatic`,
  `rainbow`, `split-complementary`, `triadic`, `square`, or `tetradic`
- `--hex COLOR`: Base color as a hexadecimal RGB value
- `--value V1 V2 V3`: Base color as RGB or LCH components
- `--space {rgb,lch}`: Color space of `--value` (default: `rgb`)
- `--mood MOOD`: Apply `warm`, `cool`, `happy`, `calm`, `intense`, `sad`, or `energetic`
- `--tone TONE`: Apply `normal`, `dark`, or `light` independently of mood
- `--grade-base`: Apply mood and tone to the base color instead of preserving it unchanged
- `--no-gamut-map`: Leave out-of-gamut colors without displayable RGB or hex values

`--type` and either `--hex` or `--value` are required. RGB channels must be integers from 0
through 255.

### Filament Command

Search and query the 3D printing filament database.

#### Find Nearest Filament Color

```bash
# Find nearest filament to red color
python -m color_tools filament --nearest --value 255 0 0

# Find top 5 nearest filaments 
python -m color_tools filament --nearest --value 255 0 0 --count 5

# Use different color distance metrics
python -m color_tools filament --nearest --value 100 150 200 --metric cmc
python -m color_tools filament --nearest --value 100 150 200 --metric de94

# Adjust CMC parameters for different perceptual weighting
python -m color_tools filament --nearest --value 100 150 200 --metric cmc --cmc-l 1.0 --cmc-c 1.0

# Restrict results to the same hue family (prevents blue→purple substitution, etc.)
python -m color_tools filament --nearest --hex "#5c94fc" --count 5 --max-hue-delta 30

# Restrict candidates by color name
python -m color_tools filament --nearest --hex "#ed1c24" --color "Red"

# Exclude silk finishes from the nearest search
python -m color_tools filament --nearest --hex "#ed1c24" --exclude-finish "Silk" "Silk+"

# Exclude only Bambu Lab records whose type is PETG (exclusion fields use AND)
python -m color_tools filament --nearest --hex "#ed1c24" --exclude-maker "Bambu Lab" --exclude-type PETG
```

#### Handle Dual-Color Filaments

Some filaments have two colors (e.g., "#333333-#666666"). Control how these are handled:

```bash
# Use first color (default)
python -m color_tools filament --nearest --value 255 0 0 --dual-color-mode first

# Use second color
python -m color_tools filament --nearest --value 255 0 0 --dual-color-mode last

# Perceptually blend both colors in LAB space
python -m color_tools filament --nearest --value 255 0 0 --dual-color-mode mix
```

#### List and Filter Filaments

```bash
# List all manufacturers
python -m color_tools filament --list-makers

# List all filament types
python -m color_tools filament --list-types

# List all finishes
python -m color_tools filament --list-finishes

# Filter by specific criteria (supports maker synonyms)
python -m color_tools filament --maker "Bambu" --type "PLA"  # "Bambu" finds "Bambu Lab"
python -m color_tools filament --finish "Matte" --color "Black"

# Filter by multiple makers (can mix canonical names and synonyms)
python -m color_tools filament --maker "Bambu" "Polymaker"

# Filter by multiple types
python -m color_tools filament --type PLA "PLA+" PETG

# Filter by multiple finishes
python -m color_tools filament --finish Basic "Silk+" Matte

# Use wildcard (*) to bypass individual filters while keeping others
python -m color_tools filament --maker "*" --type "PLA"        # All makers, only PLA
python -m color_tools filament --maker "Bambu" --type "*"      # Only Bambu, all types
python -m color_tools filament --finish "*" --color "Black"    # All finishes, only Black
```

**Filament Command Arguments:**

**Nearest Neighbor Search:**

- `--nearest`: Find nearest filament to RGB color
- `--value R G B`: RGB color value (0-255 for each component)
- `--metric {euclidean,de76,de94,de2000,cmc}`: Distance metric (default: de2000)
- `--cmc-l FLOAT`: CMC lightness parameter (default: 2.0)
- `--cmc-c FLOAT`: CMC chroma parameter (default: 1.0)
- `--count N`: Return top N nearest filaments instead of just one (default: 1, max: 50)
- `--max-hue-delta DEGREES`: Restrict results to filaments within DEGREES of the target hue (LCH hue angle, 0-180). Useful when the best perceptual match changes hue (e.g., blue→purple). Achromatic colors are unaffected.
- `--dual-color-mode {first,last,mix}`: Handle dual-color filaments (default: first)

**Filtering and Listing:**

- `--list-makers`: List all filament manufacturers
- `--list-types`: List all filament types (PLA, PETG, etc.)
- `--list-finishes`: List all finish types (Matte, Glossy, etc.)
- `--maker NAME [NAME ...]`: Filter by one or more manufacturers (e.g., --maker "Bambu" "Polymaker"). Supports maker synonyms (e.g., "Bambu" finds "Bambu Lab"). Use "*" to bypass this filter.
- `--type NAME [NAME ...]`: Filter by one or more filament types (e.g., --type PLA "PLA+"). Use "*" to bypass this filter.
- `--finish NAME [NAME ...]`: Filter by one or more finish types (e.g., --finish Basic "Silk+"). Use "*" to bypass this filter.
- `--color NAME`: Filter by color name
- `--exclude-maker NAME [NAME ...]`: With `--nearest`, exclude matching makers
- `--exclude-type NAME [NAME ...]`: With `--nearest`, exclude matching filament types
- `--exclude-finish NAME [NAME ...]`: With `--nearest`, exclude matching finishes
- `--exclude-color NAME`: With `--nearest`, exclude a matching color name

Values within one exclusion option use OR semantics. Different exclusion fields use
AND semantics, so `--exclude-maker "Bambu Lab" --exclude-type PETG` excludes Bambu Lab
PETG records rather than excluding every Bambu Lab and every PETG record. Exclusion
options require `--nearest`.

**Owned Filaments (v6.0.0+):**

- `--add-owned ID`: Add a filament ID to your owned list and save to file
- `--remove-owned ID`: Remove a filament ID from your owned list and save to file
- `--list-owned`: Display all filaments you currently own
- `--all-filaments`: Override owned filtering to search all filaments (shopping mode)

**Combining Multiple Results with Filtering:**

```bash
# Find top 3 PLA filaments from any maker nearest to blue
python -m color_tools filament --nearest --value 33 33 255 --type "PLA" --maker "*" --count 3

# Find top 5 Bambu filaments of any type nearest to purple  
python -m color_tools filament --nearest --value 128 0 128 --maker "Bambu" --type "*" --count 5

# Find top 10 matte finish filaments from any maker/type nearest to green
python -m color_tools filament --nearest --value 0 255 0 --finish "Matte" --maker "*" --type "*" --count 10
```

**Note:** When any filter argument (`--maker`, `--type`, `--finish`, `--color`) is provided, the command displays matching filaments. Use "*" as a wildcard to bypass individual filters while keeping others active.

#### Owned Filaments Tracking (v6.0.0+)

Track which filaments you own for personalized color matching. When you create an `owned-filaments.json` file, all filament searches automatically filter to your owned filaments by default.

**Manage Owned Filaments:**

```bash
# Add filaments you own
python -m color_tools filament --add-owned "bambu-lab_pla-matte_jet-black"
python -m color_tools filament --add-owned "polymaker_polyterra-pla_charcoal-black"

# List your owned filaments
python -m color_tools filament --list-owned

# Remove a filament from your owned list
python -m color_tools filament --remove-owned "bambu-lab_pla-matte_jet-black"
```

**Search Behavior with Owned Filaments:**

```bash
# Find nearest match (automatically uses owned filaments if file exists)
python -m color_tools filament --nearest --value 255 128 64

# Find nearest with filters (still respects owned filaments)
python -m color_tools filament --nearest --value 255 128 64 --type "PLA"

# Override to search ALL filaments (shopping/browsing mode)
python -m color_tools filament --nearest --value 255 128 64 --all-filaments
python -m color_tools filament --nearest --value 255 128 64 --type "PLA" --all-filaments
```

**Owned Filaments Arguments:**

- `--add-owned ID`: Add a filament ID to your owned list
- `--remove-owned ID`: Remove a filament ID from your owned list
- `--list-owned`: Display all filaments you own
- `--all-filaments`: Override owned filtering to search all filaments (use when shopping)

**How It Works:**

1. Create `data/user/owned-filaments.json` with your filament IDs
2. All `--nearest` searches automatically filter to owned filaments only
3. Use `--all-filaments` flag when you want to browse the full catalog (shopping mode)
4. No file? Everything works exactly as before (backward compatible)

See [Customization Guide - Owned Filaments](https://github.com/dterracino/color_tools/blob/main/docs/Customization.md#owned-filamentsjson---filament-ownership-tracking) for file format and Python API usage.

#### Interactive Filament Library Manager (v6.0.0+)

Manage your owned filaments with a full-featured terminal user interface (TUI). The interactive manager provides a visual, keyboard-driven interface for browsing, filtering, and managing your filament collection.

**Requirements:**

Install the `[interactive]` extra:

```bash
pip install color-match-tools[interactive]
```

**Launch the Manager:**

```bash
color-tools filament --interactive
# or
python -m color_tools filament --interactive
```

`filament --manage` remains available as an alias. This is separate from the
top-level `color-tools --interactive` guided wizard for color, filament, and
conversion searches.

**Interface Overview:**

````text
╭─── Filament Library Manager ─────────────────────────────────────────────────╮
│ 1,050 total | 42 owned* | Showing 1,050 filaments                            │
├──────────────────────────────────────────────────────────────────────────────┤
│ > [✓] Bambu Lab - PLA Matte - Jet Black                                      │
│   [ ] Bambu Lab - PLA Matte - White                                          │
│   [✓] Polymaker - PolyTerra PLA - Charcoal Black                             │
│   [ ] Polymaker - PolyTerra PLA - Savannah Yellow                            │
│                                                                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ Spc=toggle | ↑↓Pg/Home/End | (f)ilter | (c)lear | (r)evert | (s)ave | (q)uit│
╰──────────────────────────────────────────────────────────────────────────────╯
````

**Key Bindings:**

| Key | Action |
| ----- | -------- |
| **Space** | Toggle owned status of selected filament |
| **↑ / ↓** | Move selection up/down |
| **PgUp / PgDn** | Jump up/down by one page (12 filaments) |
| **Home / End** | Jump to first/last filament |
| **(f)** | Enter filter mode |
| **(c)** | Clear all active filters |
| **(r)** | Revert unsaved ownership changes |
| **(s)** | Save changes to owned-filaments.json |
| **(q)** | Quit (prompts to save if changes exist) |
| **Esc** | Exit filter mode or quit (if no changes) |

**Filter Mode:**

Press `f` to enter filter mode and narrow down the filament list:

````text
│ FILTER MODE (Tab=next field, Esc=exit)                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ Maker : Bambu_                                                                │
│ Type  : PLA                                                                   │
│ Finish:                                                                       │
│ Color :                                                                       │
````

**Filter Mode Key Bindings:**

All printable letters are entered as filter text in this mode, including letters
used for manager actions such as `s` (save), `r` (revert), and `c` (clear).

| Key | Action |
| ----- | -------- |
| **Type** | Enter text to filter (case-insensitive substring match) |
| **Tab** | Move to next filter field (cycles through Maker/Type/Finish/Color) |
| **Shift+Tab** | Move to previous filter field |
| **Backspace** | Delete last character from active field |
| **Esc** | Exit filter mode (keeps filters active) |

**Visual Indicators:**

- **Cyan text** - Owned filaments
- **Reverse video** - Selected filament (current cursor position)
- **Yellow asterisk** (*) - Unsaved changes (appears next to owned count)
- **Yellow bold reverse** - Active filter field (in filter mode)

**Exit Summary:**

When you quit the manager, you'll see a summary of all changes made during the session:

```text
📊 Session Summary:
────────────────────────────────────────────────────────────
✅ Added 3 filament(s) to owned list:
   + Bambu Lab - PLA Matte - White
   + Polymaker - PolyTerra PLA - Savannah Yellow
   + eSun - PLA+ - Silver

❌ Removed 1 filament(s) from owned list:
   - Bambu Lab - PLA Matte - Jet Black

Total owned: 42 → 44
────────────────────────────────────────────────────────────
```

**Example Workflows:**

**Browse and add filaments:**

1. Launch manager: `color-tools filament --interactive`
2. Use arrow keys or Page Up/Down to browse
3. Press Space to mark filaments as owned (checkboxes toggle)
4. Press `s` to save changes
5. Press `q` to quit and see summary

**Filter by maker:**

1. Launch manager
2. Press `f` to enter filter mode
3. Type "Bambu" in Maker field
4. Press Esc to exit filter mode (only Bambu Lab filaments shown)
5. Browse and toggle owned status
6. Press `c` to clear filter (see all filaments again)

**Filter by multiple criteria:**

1. Press `f` to enter filter mode
2. Type "Polymaker" in Maker field
3. Press Tab to move to Type field
4. Type "PLA" in Type field
5. Press Esc to see results (only Polymaker PLA filaments)
6. Toggle owned status as needed

**Revert mistakes:**

1. Toggle several filaments by accident
2. Press `r` to revert all unsaved changes (restores last saved state)
3. Or press `q`, then `n` to quit without saving

**Tips:**

- The manager automatically loads `owned-filaments.json` if it exists
- Changes are only saved when you press `s` or confirm save on quit
- Filter is case-insensitive and matches substrings (e.g., "poly" matches "Polymaker" and "PolyTerra")
- Press `c` to quickly clear all filters and see the full list again
- The yellow asterisk (*) next to owned count reminds you of unsaved changes
- Exit summary compares original state to final saved state (captures all saves during session)

### PySide6 Desktop Filament Manager

For a desktop manager with color swatches, live filters, ownership checkboxes,
and save/revert controls, install the separate optional `[gui]` extra:

```bash
pip install color-match-tools[gui]
color-tools filament --gui
```

The desktop manager shows each filament's effective color in a swatch, alongside
its maker, type, finish, color name, TD value, and ID. Filter by maker, type,
finish, and color name; check or uncheck filaments to edit your owned list. Select **Save
changes** to persist edits or **Revert** to restore the last saved list. Closing
with unsaved edits offers save, discard, or cancel.

The **File** menu provides **Save**, **Reload**, **Export Owned...**, and
**Exit**. Reload reads the owned list from disk and prompts about pending edits
first. Export Owned... exports all currently owned filament records, regardless
of the active view or filters. Its dialog provides editable Generic CSV,
Generic JSON, AutoForge CSV, and Custom text templates, a file extension field,
and a live preview. Templates use `<%=loop_start%>` and `<%=loop_end%>` to mark
the repeated-record block and tags such as `<%=maker%>`, `<%=color%>`, and
`<%=td_value%>` for record values. The tag selector and **Insert tag** button
add the selected tag at the editor cursor, and template tags are colorized.
Nested values support sequence indexes and object or mapping properties, for
example `<%=rgb[0]%>`, `<%=rgb.r%>`, and `<%=metadata["key"]%>`. Bracketed
mapping keys must be quoted; paths read values only and do not evaluate
expressions or call methods. Add a Python format spec after a colon to control
output, for example `<%=td_value:.3f%>` or `<%=maker:>24%>`. Formatting follows
Python's standard format mini-language; for JSON, formatted numeric values stay
numbers when the result is a valid JSON number, while other formatted values
are emitted as strings. When a format spec is applied to a sequence, it is
applied to each item; for example, `<%=lab:.3f%>` emits all LAB components as a
formatted JSON array. You can edit a preset or change the extension to adapt it
to another tool; JSON templates must produce valid JSON. The compact
template editor uses a fixed-width font, inserts four spaces when you press
Tab, and preserves the current line's indentation when you press Enter. The
**View** menu switches between **Owned** and **All Filaments** without changing
ownership.

The terminal manager remains available with
`color-tools filament --interactive` (or `--manage`) and requires the separate
`[interactive]` extra. The top-level `color-tools --interactive` is the guided
search wizard and is independent of both library managers.

### Interactive Wizard *(requires [interactive] extra)*

The interactive wizard guides you through `color`, `filament`, and `convert` searches
with step-by-step prompts — no need to remember flags or argument syntax.

**Requirements:**

```bash
pip install color-match-tools[interactive]
```

**Launch:**

```bash
# Automatically when no arguments are given
color-tools
python -m color_tools

# Or explicitly
color-tools --interactive
color-tools -i
```

**What it does:**

1. Asks which command you want: `color`, `filament`, or `convert`
2. Walks through the relevant options with numbered menus and Tab-completion
3. For every color input, offers a choice of **hex** (e.g. `#FF8040`) or **RGB** values
4. Filament filters (maker, type, finish) support **multiple values** — pick one at a time,
   press Enter on an empty line when done
5. After collecting all options, prints the **equivalent CLI command** before running it:

```text
  ▶  color-tools filament --nearest --hex #FFAACC --maker 'Bambu Lab' --finish Matte Basic --all-filaments
  ─────────────────────────────────────────────────────────────────────────────────
  Maker:   Bambu Lab     Type: PLA     Finish: Matte
  Color:   Sakura Pink   Hex:  #FFAABB
  ΔE2000:  1.34
```

The printed command is ready to copy-paste directly into a script or shell alias.

Falls back to `--help` output if `prompt_toolkit` is not installed.

---

### Convert Command

Convert between color spaces and check gamut constraints.

#### Color Space Conversions

```bash
# Convert RGB to LAB
python -m color_tools convert --from rgb --to lab --value 255 128 0

# Convert LAB to LCH (cylindrical LAB)
python -m color_tools convert --from lab --to lch --value 50 25 -30

# Convert LCH back to RGB
python -m color_tools convert --from lch --to rgb --value 50 33.54 -50.19

# Convert RGB to CMYK (print workflow)
python -m color_tools convert --from rgb --to cmyk --value 255 128 0

# Convert CMYK back to RGB (4 values required)
python -m color_tools convert --from cmyk --to rgb --value 0 49.8 100 0

# Convert RGB to CMY (simple subtractive — no black channel)
python -m color_tools convert --from rgb --to cmy --value 255 128 0
```

#### Gamut Checking

```bash
# Check if LAB color is representable in sRGB
python -m color_tools convert --check-gamut --value 50 100 50

# Check LCH color gamut
python -m color_tools convert --check-gamut --from lch --value 70 80 120
```

**Convert Command Arguments:**

- `--from {rgb,hsl,lab,lch,cmy,cmyk}`: Source color space
- `--to {rgb,hsl,lab,lch,cmy,cmyk}`: Target color space
- `--value V ...`: Color value (3 components for most spaces; 4 for CMYK)
- `--check-gamut`: Check if LAB/LCH color is in sRGB gamut

### Image Command *(requires [image] extra)*

Process images with color transformations, CVD simulation/correction, and retro palette conversion.

#### List Available Palettes

```bash
# Show all available retro palettes (both commands work identically)
color-tools color --palette list
color-tools image --list-palettes
```

#### Color Vision Deficiency (CVD) Operations

```bash
# Simulate how colorblind users see an image
python -m color_tools image --file photo.jpg --cvd-simulate protanopia
python -m color_tools image --file chart.png --cvd-simulate deuteranopia --output colorblind_view.png

# Apply CVD correction for improved discriminability
python -m color_tools image --file infographic.png --cvd-correct deutan
python -m color_tools image --file artwork.jpg --cvd-correct tritan --output corrected.png
```

#### Retro Palette Conversion

```bash
# Convert to classic CGA 4-color palette
python -m color_tools image --file photo.jpg --quantize-palette cga4

# Convert to Game Boy palette with dithering for smoother gradients
python -m color_tools image --file artwork.png --quantize-palette gameboy --dither

# Use different distance metrics for palette matching
python -m color_tools image --file image.jpg --quantize-palette vga --metric de94
python -m color_tools image --file photo.png --quantize-palette commodore64 --metric cmc --dither
```

#### HueForge Color Analysis

```bash
# Extract and redistribute luminance (existing functionality)
python -m color_tools image --file photo.jpg --redistribute-luminance --colors 8
```

**Image Command Arguments:**

- `--file FILE`: Path to input image file
- `--output OUTPUT`: Path to save output image (optional, auto-generates if not provided)
- `--redistribute-luminance`: Extract colors and redistribute luminance for HueForge
- `--colors N`: Number of unique colors to extract (default: 10)
- `--cvd-simulate TYPE`: Simulate color vision deficiency (protanopia, deuteranopia, tritanopia)
- `--cvd-correct TYPE`: Apply CVD correction for specified deficiency
- `--quantize-palette NAME`: Convert to specified retro palette
- `--metric {de2000,de94,de76,cmc,euclidean,hsl_euclidean}`: Color distance metric (default: de2000)
- `--dither`: Apply Floyd-Steinberg dithering for palette quantization
- `--list-palettes`: List all available retro palettes with color counts

**Available Palettes:** Use `color-tools color --palette list` or `color-tools image --list-palettes` to see all 20 core palettes (including apple2, cga4, cga16, commodore64, crayola, ega16, ega64, gameboy variants, macintosh, nes, pico8, sms, tandy16, vga, virtualboy, web) plus any custom user palettes

### Global Arguments

These arguments work with all commands:

- `--json DIR`: Path to directory containing all JSON data files (colors.json, filaments.json, maker_synonyms.json). Must be a directory, not a file. Default: uses package data directory
- `--verify-constants`: Verify integrity of color science constants before proceeding
- `--verify-data`: Verify integrity of core data files before proceeding
- `--verify-matrices`: Verify integrity of transformation matrices before proceeding
- `--verify-all`: Verify integrity of constants, data files, and matrices before proceeding
- `--check-overrides`: Show report of user overrides (user-colors.json, user-filaments.json) and exit
- `--log-file PATH`: Write log output to this file (enables rotating file logging)
- `--log-level LEVEL`: Minimum level written to the log file — `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (default: `DEBUG`)
- `--version`: Show version number and exit

---

## Logging

The `color_tools` library includes a structured logging system backed by Python's standard
`logging` module. It fans out to both a console handler and an optional rotating file handler
with a single `setup_logging()` call.

### Quick Start

```python
from pathlib import Path
import logging
from color_tools import setup_logging, get_logger, log_info, log_debug

# Console only — INFO+ messages
setup_logging()

# Console (INFO+) + rotating file (DEBUG+)
setup_logging(log_file=Path("color_tools.log"))

# Verbose console — DEBUG+ messages
setup_logging(console_level=logging.DEBUG)

# Force plain output even if Rich is installed
setup_logging(rich=False)
```

### Module-Level Loggers

```python
from color_tools import get_logger

# Returns a logger scoped under "color_tools.*"
logger = get_logger(__name__)           # e.g. "color_tools.conversions"
logger.info("Loaded %d colors", count)  # lazy % formatting — no cost when disabled
logger.error("Failed to open %s", path, exc_info=True)
```

### Shortcut Functions

Convenience wrappers on the library root logger:

```python
from color_tools import log_debug, log_info, log_warning, log_error, log_critical

log_info("Processing started")
log_warning("Color %s outside sRGB gamut", name)
log_error("Failed to load data: %s", path)
```

### Level Constants

```python
from color_tools import LOG_LEVEL, CONSOLE_LEVEL
# LOG_LEVEL     = logging.DEBUG  (10) — default file level
# CONSOLE_LEVEL = logging.INFO   (20) — default console level
```

### Colorized Output

Install the optional `[logging]` extra for colorized console output via
[Rich](https://github.com/Textualize/rich):

```bash
pip install color-match-tools[logging]
```

Rich is detected automatically at import time. If it is not installed, a plain
`StreamHandler` is used with no errors or warnings.

### CLI Logging

The `--log-file` and `--log-level` global flags activate file logging for any command:

```bash
# Log INFO+ to file while running a filament search
color-tools --log-file run.log filament --nearest --hex "#FF0000"

# Log everything (DEBUG+) for troubleshooting
color-tools --log-file debug.log --log-level DEBUG color --nearest --hex "#FF8040"
```

### Security: Log-Injection Prevention

All messages and their arguments are automatically sanitized to strip `CR`, `LF`, and `NUL`
characters before reaching any handler. This prevents a crafted color name (e.g. read from a
user-supplied JSON file) from forging extra log lines.

---

## Examples

### Find Similar Filament Colors

```bash
# I have RGB(180, 100, 200) and want to find matching filaments
python -m color_tools filament --nearest --value 180 100 200

# Find top 3 alternatives in case my preferred filament is unavailable
python -m color_tools filament --nearest --value 180 100 200 --count 3

# Use CMC color difference (textile industry standard)
python -m color_tools filament --nearest --value 180 100 200 --metric cmc

# Use different distance metric
python -m color_tools filament --nearest --value 180 100 200 --metric de94

# Find alternatives from any maker but only PLA type
python -m color_tools filament --nearest --value 180 100 200 --type "PLA" --maker "*" --count 5
```

### Color Space Analysis

```bash
# Convert my RGB color to LAB for analysis
python -m color_tools convert --from rgb --to lab --value 180 100 200

# Convert HSL to RGB
python -m color_tools convert --from hsl --to rgb --value 16.1 100 65.7

# Convert LAB to LCH for hue-based analysis
python -m color_tools convert --from lab --to lch --value 65.2 25.8 -15.4

# Convert LCH back to RGB
python -m color_tools convert --from lch --to rgb --value 65.2 30.1 328.3

# Check if a highly saturated LAB color can be displayed
python -m color_tools convert --check-gamut --value 50 80 60

# Find the CSS color name closest to my LAB measurement
python -m color_tools color --nearest --value 65.2 25.8 -15.4 --space lab

# Find top 3 nearest CSS colors for broader options
python -m color_tools color --nearest --value 65.2 25.8 -15.4 --space lab --count 3

# Find nearest color using LCH (perceptually uniform cylindrical space)
python -m color_tools color --nearest --value 67.3 65.7 46.3 --space lch
```

### Batch Operations

```bash
# Find all matte black filaments
python -m color_tools filament --finish "Matte" --color "Black"

# Find filaments with multiple finish types
python -m color_tools filament --finish Basic Matte "Silk+"

# Search across multiple manufacturers and types
python -m color_tools filament --maker "Bambu Lab" "Sunlu" --type PLA PETG

# Search all types from a specific maker (wildcard type filter)
python -m color_tools filament --maker "Polymaker" --type "*"

# Search specific type from any maker (wildcard maker filter)  
python -m color_tools filament --type "PLA+" --maker "*"

# List all available filament types from a specific maker
# (Note: This uses Unix tools; on Windows, use PowerShell or view the full output)
python -m color_tools filament --maker "Polymaker" | grep -o 'type: [^,]*' | sort -u
```

---

[← Back to README](https://github.com/dterracino/color_tools/blob/main/README.md) | [Installation](https://github.com/dterracino/color_tools/blob/main/docs/Installation.md) | [Customization →](https://github.com/dterracino/color_tools/blob/main/docs/Customization.md)

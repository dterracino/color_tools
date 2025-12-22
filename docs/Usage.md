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
  - [Color Command](#color-command)
  - [Filament Command](#filament-command)
  - [Convert Command](#convert-command)
  - [Image Command](#image-command-requires-image-extra)
  - [Global Arguments](#global-arguments)
- [Examples](#examples)

---

## Library Usage

Import and use color_tools functions in your Python code.

### Basic Examples

```python
from color_tools import rgb_to_lab, delta_e_2000, Palette, FilamentPalette, hex_to_rgb

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

# Available palettes: cga4, cga16, ega16, ega64, vga, web
ega = load_palette('ega16')  # Standard EGA 16-color palette
vga = load_palette('vga')    # VGA 256-color palette (Mode 13h)
web = load_palette('web')    # Web-safe 216-color palette

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
- `rgb_to_lch()`, `lch_to_rgb()` - RGB ↔ LCH conversion  
- `rgb_to_hsl()`, `hsl_to_rgb()` - RGB ↔ HSL conversion (0-360, 0-100, 0-100 range)
- `rgb_to_winhsl()` - RGB → Windows HSL (0-240, 0-240, 0-240 range)
- `hex_to_rgb()`, `rgb_to_hex()` - Hex ↔ RGB conversion
  - Supports 3-character shorthand (`#F00` or `F00` → `(255, 0, 0)`)
  - Supports 6-character standard (`#FF0000` or `FF0000` → `(255, 0, 0)`)
  - Works with or without `#` prefix
- `lab_to_lch()`, `lch_to_lab()` - LAB ↔ LCH conversion
- `rgb_to_xyz()`, `xyz_to_rgb()` - RGB ↔ XYZ conversion (CIE standard)
- `xyz_to_lab()`, `lab_to_xyz()` - XYZ ↔ LAB conversion (for advanced use)

#### Distance Metrics

- `delta_e_2000()` - CIEDE2000 (recommended)
- `delta_e_94()` - CIE94
- `delta_e_76()` - CIE76
- `delta_e_cmc()` - CMC color difference
- `euclidean()` - Simple Euclidean distance

#### Gamut Operations

- `is_in_srgb_gamut()` - Check if LAB color is displayable
- `find_nearest_in_gamut()` - Find closest displayable color
- `clamp_to_gamut()` - Force color into sRGB gamut

#### Palettes

- `Palette.load_default()` - Load CSS color database
- `load_palette(name)` - Load retro/classic palette (cga4, cga16, ega16, ega64, vga, web)
- `FilamentPalette.load_default()` - Load filament database
- `palette.nearest_color()` - Find nearest color match
- `palette.find_by_name()` - Look up color by name
- `palette.find_by_rgb()` - Look up by exact RGB value
- `palette.find_by_lab()` - Look up by LAB value (with rounding)
- `palette.find_by_lch()` - Look up by LCH value (with rounding)
- `filament_palette.nearest_filament()` - Find nearest filament
- `filament_palette.filter()` - Filter by maker, type, finish, color (supports maker synonyms)
- `filament_palette.find_by_maker()` - Get all filaments from a maker (supports synonyms)
- `filament_palette.find_by_type()` - Get all filaments of a type

#### Configuration

- `set_dual_color_mode()` - Set how dual-color filaments are handled
- `get_dual_color_mode()` - Get current dual-color mode

#### Validation

- `validate_color()` - Validate if hex code matches a color name using fuzzy matching and Delta E
  - Automatically uses `fuzzywuzzy` if installed, otherwise falls back to hybrid matcher
  - Returns `ColorValidationRecord` with match confidence, suggested hex, and Delta E distance
  - Example: `validate_color("light blue", "#ADD8E6")` → validates color name/hex pairing

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
- `--palette {cga4,cga16,ega16,ega64,vga,web}`: Use retro/classic palette instead of CSS colors

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
- `--dual-color-mode {first,last,mix}`: Handle dual-color filaments (default: first)

**Filtering and Listing:**

- `--list-makers`: List all filament manufacturers
- `--list-types`: List all filament types (PLA, PETG, etc.)
- `--list-finishes`: List all finish types (Matte, Glossy, etc.)
- `--maker NAME [NAME ...]`: Filter by one or more manufacturers (e.g., --maker "Bambu" "Polymaker"). Supports maker synonyms (e.g., "Bambu" finds "Bambu Lab"). Use "*" to bypass this filter.
- `--type NAME [NAME ...]`: Filter by one or more filament types (e.g., --type PLA "PLA+"). Use "*" to bypass this filter.
- `--finish NAME [NAME ...]`: Filter by one or more finish types (e.g., --finish Basic "Silk+"). Use "*" to bypass this filter.
- `--color NAME`: Filter by color name

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
```

#### Gamut Checking

```bash
# Check if LAB color is representable in sRGB
python -m color_tools convert --check-gamut --value 50 100 50

# Check LCH color gamut
python -m color_tools convert --check-gamut --from lch --value 70 80 120
```

**Convert Command Arguments:**

- `--from {rgb,hsl,lab,lch}`: Source color space
- `--to {rgb,hsl,lab,lch}`: Target color space
- `--value V1 V2 V3`: Color value tuple
- `--check-gamut`: Check if LAB/LCH color is in sRGB gamut

### Image Command *(requires [image] extra)*

Process images with color transformations, CVD simulation/correction, and retro palette conversion.

#### List Available Palettes

```bash
# Show all available retro palettes
python -m color_tools image --list-palettes
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
- `--list-palettes`: List all available retro palettes

**Available Palettes:** cga4, cga16, ega16, ega64, vga, web, gameboy_dmg, gameboy_gbl, gameboy_mgb, commodore64 (plus any custom palettes in data/palettes/)

### Global Arguments

These arguments work with all commands:

- `--json DIR`: Path to directory containing all JSON data files (colors.json, filaments.json, maker_synonyms.json). Must be a directory, not a file. Default: uses package data directory
- `--verify-constants`: Verify integrity of color science constants before proceeding
- `--verify-data`: Verify integrity of core data files before proceeding
- `--verify-matrices`: Verify integrity of transformation matrices before proceeding
- `--verify-all`: Verify integrity of constants, data files, and matrices before proceeding
- `--check-overrides`: Show report of user overrides (user-colors.json, user-filaments.json) and exit
- `--version`: Show version number and exit

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

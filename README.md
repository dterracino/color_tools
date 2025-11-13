# Color Tools

A comprehensive Python library for color science operations, color space conversions, and color matching. This tool provides perceptually accurate color distance calculations, gamut checking, and extensive databases of CSS colors and 3D printing filament colors.

**Version:** 3.3.0 | [Changelog](https://github.com/dterracino/color_tools/blob/main/CHANGELOG.md)

## Features

- **Multiple Color Spaces**: RGB, HSL, LAB, LCH with accurate conversions
- **Perceptual Color Distance**: Delta E formulas (CIE76, CIE94, CIEDE2000, CMC)
- **Color Databases**:
  - Complete CSS color names with hex/RGB/HSL/LAB/LCH values
  - Extensive 3D printing filament database (584 filaments) with manufacturer info
  - Unique semantic IDs for all filaments (e.g., "bambu-lab-pla-silk-red")
  - Alternative name support for regional variations and rebranding
  - Maker synonym support for flexible filament searches
  - **Retro/Classic Palettes**: CGA, EGA, VGA, and Web-safe color palettes
- **Gamut Checking**: Verify if colors are representable in sRGB
- **Thread-Safe**: Configurable runtime settings per thread
- **Color Science Integrity**: Built-in verification of color constants

## Installation

**Requirements:** Python 3.10+

### Install from PyPI (Recommended)

**Base package (zero dependencies):**

```bash
pip install color-match-tools
```

**With enhanced fuzzy matching:**

```bash
pip install color-match-tools[fuzzy]
```

Adds fuzzywuzzy for better color name validation (validation module has built-in fallback).

**With image processing support:**

```bash
pip install color-match-tools[image]
```

Adds Pillow for image color analysis, k-means clustering, and Hueforge optimization.

**With all optional features:**

```bash
pip install color-match-tools[all]
```

Installs everything: fuzzy matching + image processing.

All variants install the `color-tools` command globally in your terminal.

### For Development

Clone this repository and install in development mode with all optional features:

```bash
git clone https://github.com/dterracino/color_tools.git
cd color_tools
pip install -r requirements-dev.txt
pip install -e .
```

This installs:

- Base package in "editable" mode (modify code while using it)
- All optional dependencies (fuzzy matching, image processing)
- Development tools (coverage, pyright, build, twine)

**Minimal development setup (base only):**

```bash
pip install -r requirements.txt
pip install -e .
```

### Dependencies

The core module uses **only Python standard library** - **zero external dependencies** required!

**Optional dependencies:**

- `[fuzzy]`: fuzzywuzzy >= 0.18.0 for enhanced fuzzy color name matching (validation module has built-in fallback)
- `[image]`: Pillow >= 10.0.0 for image processing features
- `[all]`: All of the above (fuzzy + image)

**Requirements files (for development/manual installation):**

- `requirements.txt`: Base package (currently empty - zero dependencies)
- `requirements-fuzzy.txt`: Base + fuzzywuzzy dependencies
- `requirements-image.txt`: Base + Pillow
- `requirements-dev.txt`: All of above + development tools (coverage, pyright, build, twine)

The validation module works without fuzzywuzzy using a built-in Levenshtein distance implementation. Install fuzzywuzzy for better fuzzy matching performance:

```bash
pip install color-match-tools[fuzzy]  # OR
pip install fuzzywuzzy
```

**Note:** If `fuzzywuzzy` is not installed, the validation module automatically falls back to a built-in hybrid fuzzy matcher using exact/substring/Levenshtein matching. This provides good results without external dependencies, though `fuzzywuzzy` is recommended for optimal matching accuracy.

## Usage

Color Tools can be used in three ways:

1. **As a Python Library**: Import functions directly in your Python code
2. **As a CLI Tool**: Use `python -m color_tools` from the repository
3. **As an Installed Command**: Use `color-tools` command after `pip install`

### Library Usage

Import and use color_tools functions in your Python code:

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
```

**Common Library Functions:**

**Color Conversions:**

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

**Distance Metrics:**

- `delta_e_2000()` - CIEDE2000 (recommended)
- `delta_e_94()` - CIE94
- `delta_e_76()` - CIE76
- `delta_e_cmc()` - CMC color difference
- `euclidean()` - Simple Euclidean distance

**Gamut Operations:**

- `is_in_srgb_gamut()` - Check if LAB color is displayable
- `find_nearest_in_gamut()` - Find closest displayable color
- `clamp_to_gamut()` - Force color into sRGB gamut

**Palettes:**

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

**Configuration:**

- `set_dual_color_mode()` - Set how dual-color filaments are handled
- `get_dual_color_mode()` - Get current dual-color mode

**Validation:**

- `validate_color()` - Validate if hex code matches a color name using fuzzy matching and Delta E
  - Automatically uses `fuzzywuzzy` if installed, otherwise falls back to hybrid matcher
  - Returns `ColorValidationRecord` with match confidence, suggested hex, and Delta E distance
  - Example: `validate_color("light blue", "#ADD8E6")` → validates color name/hex pairing

**Data Structures:**

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

### CLI Usage

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
```

**Filament Command Arguments:**

**Nearest Neighbor Search:**

- `--nearest`: Find nearest filament to RGB color
- `--value R G B`: RGB color value (0-255 for each component)
- `--metric {euclidean,de76,de94,de2000,cmc}`: Distance metric (default: de2000)
- `--cmc-l FLOAT`: CMC lightness parameter (default: 2.0)
- `--cmc-c FLOAT`: CMC chroma parameter (default: 1.0)
- `--dual-color-mode {first,last,mix}`: Handle dual-color filaments (default: first)

**Filtering and Listing:**

- `--list-makers`: List all filament manufacturers
- `--list-types`: List all filament types (PLA, PETG, etc.)
- `--list-finishes`: List all finish types (Matte, Glossy, etc.)
- `--maker NAME [NAME ...]`: Filter by one or more manufacturers (e.g., --maker "Bambu" "Polymaker"). Supports maker synonyms (e.g., "Bambu" finds "Bambu Lab").
- `--type NAME [NAME ...]`: Filter by one or more filament types (e.g., --type PLA "PLA+")
- `--finish NAME [NAME ...]`: Filter by one or more finish types (e.g., --finish Basic "Silk+")
- `--color NAME`: Filter by color name

**Note:** When any filter argument (`--maker`, `--type`, `--finish`, `--color`) is provided, the command displays matching filaments.

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

### Global Arguments

These arguments work with all commands:

- `--json DIR`: Path to directory containing all JSON data files (colors.json, filaments.json, maker_synonyms.json). Must be a directory, not a file. Default: uses package data directory
- `--verify-constants`: Verify integrity of color science constants before proceeding
- `--verify-data`: Verify integrity of core data files before proceeding
- `--verify-all`: Verify integrity of both constants and data files before proceeding
- `--version`: Show version number and exit

## Color Spaces

### RGB

Standard 8-bit RGB values (0-255 for each component).

### HSL

- **H** (Hue): 0-360 degrees
- **S** (Saturation): 0-100%
- **L** (Lightness): 0-100%

### LAB (CIELAB)

Perceptually uniform color space:

- **L*** (Lightness): 0-100
- **a*** (Green-Red): typically -100 to +100
- **b*** (Blue-Yellow): typically -100 to +100

### LCH

Cylindrical representation of LAB:

- **L*** (Lightness): 0-100
- **C*** (Chroma): 0+ (color intensity)
- **h°** (Hue): 0-360 degrees

**LCH is ideal for user interfaces** because:

- Hue can be adjusted independently (0-360°)
- Chroma controls saturation in a perceptually uniform way
- Much more intuitive than HSL for color manipulation
- Perfect for color picker wheels and gradients

## Distance Metrics

### Delta E Formulas

1. **CIE76** (`de76`/`euclidean`): Simple Euclidean distance in LAB space
2. **CIE94** (`de94`): Improved perceptual uniformity over CIE76
3. **CIEDE2000** (`de2000`): Current gold standard, handles all edge cases
4. **CMC** (`cmc`): Textile industry standard with configurable lightness/chroma weights

**Recommended**: Use `de2000` for most applications as it provides the best perceptual uniformity.

### CMC Parameters

- **CMC(2:1)** (`cmc21`): Acceptability threshold
- **CMC(1:1)** (`cmc11`): Perceptibility threshold
- **Custom**: Use `--cmc-l` and `--cmc-c` for specific weighting

## Examples

### Find Similar Filament Colors

```bash
# I have RGB(180, 100, 200) and want to find matching filaments
python -m color_tools filament --nearest --value 180 100 200

# Use CMC color difference (textile industry standard)
python -m color_tools filament --nearest --value 180 100 200 --metric cmc

# Use different distance metric
python -m color_tools filament --nearest --value 180 100 200 --metric de94
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

# List all available filament types from a specific maker
python -m color_tools filament --maker "Polymaker" | grep -o 'type: [^,]*' | sort -u
```

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

- **id** (string, required): Unique semantic identifier generated from maker-type-finish-color
  - Example: `"bambu-lab-pla-silk-plus-red"`
  - Format: lowercase, hyphen-separated, URL-safe (+ becomes -plus)
  - Human-readable and stable (barring manufacturer rebranding)
  
- **maker** (string, required): Manufacturer name (canonical form)
  
- **type** (string, required): Filament material type (PLA, PETG, ABS, etc.)
  
- **finish** (string or null): Surface finish or product line (Silk, Matte, Basic, etc.)
  
- **color** (string, required): Color name as labeled by manufacturer
  
- **hex** (string, required): Hex color code
  - Single color: `"#RRGGBB"`
  - Dual color (silk/mixed): `"#RRGGBB-#RRGGBB"` (dash-separated)
  
- **td_value** (number or null): Translucency/transparency value (manufacturer-specific scale)
  
- **other_names** (array of strings or null, optional): Alternative names for this filament
  - Regional variations: `["Premium Red (EU)", "Classic Red (US)"]`
  - Historical names: `["Atomic Age Teal"]` (when manufacturer renames product)
  - Marketing variations: `["Fire Red", "Ferrari Red"]`
  - Only populated when alternatives exist

### maker_synonyms.json - Maker Name Synonyms

Mapping of canonical maker names to common synonyms/abbreviations:

```json
{
  "Bambu Lab": ["Bambu", "BLL"],
  "Paramount 3D": ["Paramount", "Paramount3D"]
}
```

**Synonym Support:** Filament searches automatically support maker synonyms. For example, searching for "Bambu" will find all "Bambu Lab" filaments.

### User Data Files (Optional Extensions)

You can extend the core databases with your own custom data by creating optional user files in the same directory as the core data files:

- **user-colors.json** - Add custom colors (same format as colors.json)
- **user-filaments.json** - Add custom filaments (same format as filaments.json)
- **user-synonyms.json** - Add or extend maker synonyms (same format as maker_synonyms.json)

User data is automatically loaded and merged with core data. User files are optional and ignored if they don't exist. These files are **not** verified for integrity - only core data files are protected by SHA-256 hashes.

**Example user-colors.json:**

```json
[
  {
    "name": "myCustomPurple",
    "hex": "#9B59B6",
    "rgb": [155, 89, 182],
    "hsl": [283.1, 39.0, 53.1],
    "lab": [48.5, 45.7, -40.2],
    "lch": [48.5, 60.8, 318.6]
  }
]
```

**Note:** Users are responsible for avoiding duplicate entries between core and user data files.

### Data Integrity Verification

Core data files are protected with SHA-256 hashes to ensure integrity:

```bash
# Verify data files only
python -m color_tools --verify-data

# Verify color science constants only
python -m color_tools --verify-constants

# Verify both constants and data files
python -m color_tools --verify-all
```

User data files are not verified - you have full control over their contents.

## Technical Notes

### Color Science Constants

The tool includes comprehensive color science constants from international standards:

- CIE illuminants and observers
- sRGB transformation matrices
- Gamma correction parameters
- Delta E formula coefficients

All constants include integrity verification via SHA-256 hashing.

### Thread Safety

Runtime configuration (like dual-color mode) uses `threading.local()` for thread-safe operation in multi-threaded applications.

### Gamut Handling

The tool can detect when LAB colors fall outside the sRGB gamut and automatically find the nearest representable color by reducing chroma while preserving hue and lightness.

## Error Handling

Common errors and solutions:

- **"Color not found"**: Check spelling and case of color names
- **"No filaments match criteria"**: Verify manufacturer/type names with `--list-makers` and `--list-types`
- **"Unknown metric"**: Use one of the supported metrics: euclidean, de76, de94, de2000, cmc
- **Out of gamut warnings**: Use `--check-gamut` to verify color representability

## Performance

The tool uses indexed lookups for fast color matching:

- Color names: O(1) hash lookup
- RGB values: O(1) exact match
- Nearest neighbor: O(n) with optimized distance calculations

For large datasets, consider filtering by manufacturer or type before performing nearest neighbor searches.

## Contributing

### Constants Integrity

**CRITICAL**: The color science constants in `constants.py` should **NEVER** be modified. They represent fundamental values from international standards (CIE, sRGB specification) and changing them would break color accuracy.

To verify the constants haven't been tampered with:

```bash
python -m color_tools --verify-constants
```

**If constants verification fails**, this indicates either:

1. **Accidental modification** - restore from git: `git checkout constants.py`
2. **Malicious tampering** - investigate and restore from a known good backup
3. **Development changes** - if you're a maintainer who legitimately needs to update constants, you'll need to regenerate the integrity hash (contact project maintainers)

The integrity check uses SHA-256 hashing to ensure the mathematical foundation remains scientifically accurate and unchanged.

# Color Tools

A comprehensive Python library for color science operations, color space conversions, and color matching. This tool provides perceptually accurate color distance calculations, gamut checking, and extensive databases of CSS colors and 3D printing filament colors.

## Features

- **Multiple Color Spaces**: RGB, HSL, LAB, LCH with accurate conversions
- **Perceptual Color Distance**: Delta E formulas (CIE76, CIE94, CIEDE2000, CMC)
- **Color Databases**:
  - Complete CSS color names with hex/RGB/HSL/LAB values
  - Extensive 3D printing filament database with manufacturer info
- **Gamut Checking**: Verify if colors are representable in sRGB
- **Thread-Safe**: Configurable runtime settings per thread
- **Color Science Integrity**: Built-in verification of color constants

## Installation

Clone this repository and ensure you have Python 3.7+:

```bash
git clone <repository-url>
cd color_tools
```

The core module uses only Python standard library - no external dependencies required for basic functionality.

**Optional dependency**: The `validation` module requires `fuzzywuzzy` for fuzzy color name matching. Install with:
```bash
pip install fuzzywuzzy
```

**To use as a library**, add the repository to your Python path or import it directly:

```python
# Option 1: Add to Python path
import sys
sys.path.insert(0, '/path/to/color_tools')
from color_tools import rgb_to_lab, Palette

# Option 2: Run from the color_tools directory
# Then import normally in your scripts
```

**To use the CLI**, run from the repository directory:

```bash
python -m color_tools --help
```

## Usage

Color Tools can be used in two ways:
1. **As a Python Library**: Import functions directly in your Python code
2. **As a CLI Tool**: Use the command-line interface for interactive work

### Library Usage

Import and use color_tools functions in your Python code:

```python
from color_tools import rgb_to_lab, delta_e_2000, Palette, FilamentPalette

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

# Load filament palette and search
filament_palette = FilamentPalette.load_default()
filament, distance = filament_palette.nearest_filament((180, 100, 200))
print(f"Nearest filament: {filament.maker} {filament.type} - {filament.color}")

# Filter filaments by criteria
pla_filaments = filament_palette.filter(type_name="PLA", maker="Bambu Lab")
print(f"Found {len(pla_filaments)} Bambu Lab PLA filaments")
```

**Common Library Functions:**

**Color Conversions:**
- `rgb_to_lab()`, `lab_to_rgb()` - RGB ↔ LAB conversion (most common)
- `rgb_to_lch()`, `lch_to_rgb()` - RGB ↔ LCH conversion  
- `rgb_to_hsl()` - RGB → HSL conversion (0-360, 0-100, 0-100 range)
- `rgb_to_winhsl()` - RGB → Windows HSL (0-240, 0-240, 0-240 range)
- `hex_to_rgb()`, `rgb_to_hex()` - Hex ↔ RGB conversion
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
- `FilamentPalette.load_default()` - Load filament database
- `palette.nearest_color()` - Find nearest color match
- `palette.find_by_name()` - Look up color by name
- `palette.find_by_rgb()` - Look up by exact RGB value
- `filament_palette.nearest_filament()` - Find nearest filament
- `filament_palette.filter()` - Filter by maker, type, finish, color
- `filament_palette.find_by_maker()` - Get all filaments from a maker
- `filament_palette.find_by_type()` - Get all filaments of a type

**Configuration:**
- `set_dual_color_mode()` - Set how dual-color filaments are handled
- `get_dual_color_mode()` - Get current dual-color mode

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

# FilamentRecord - returned by FilamentPalette methods
filament, distance = filament_palette.nearest_filament((255, 0, 0))
print(filament.maker)   # e.g., "Polymaker"
print(filament.type)    # e.g., "PLA"
print(filament.finish)  # e.g., "PolyMax"
print(filament.color)   # e.g., "Red"
print(filament.hex)     # e.g., "#ED2F20"
print(filament.rgb)     # e.g., (237, 47, 32)
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

# Use CMC color difference formula
python -m color_tools color --nearest --value 70 15 45 --space lab --metric cmc --cmc-l 2.0 --cmc-c 1.0
```

**Color Command Arguments:**

- `--name NAME`: Find exact color by name (case-insensitive)
- `--nearest`: Find the closest color to specified value
- `--value V1 V2 V3`: Color value tuple (format depends on `--space`)
- `--space {rgb,hsl,lab}`: Color space of input value (default: lab)
- `--metric {euclidean,de76,de94,de2000,cmc,cmc21,cmc11}`: Distance metric (default: de2000)
- `--cmc-l FLOAT`: CMC lightness parameter (default: 2.0)
- `--cmc-c FLOAT`: CMC chroma parameter (default: 1.0)

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

# Filter by specific criteria
python -m color_tools filament --maker "Bambu Lab" --type "PLA"
python -m color_tools filament --finish "Matte" --color "Black"

# Filter by multiple makers
python -m color_tools filament --maker "Bambu Lab" "Polymaker"

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
- `--maker NAME [NAME ...]`: Filter by one or more manufacturers (e.g., --maker "Bambu Lab" "Polymaker")
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

- `--json PATH`: Path to JSON data file (default: color_tools.json)
- `--verify-constants`: Verify integrity of color science constants

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

# Check if a highly saturated LAB color can be displayed
python -m color_tools convert --check-gamut --value 50 80 60

# Find the CSS color name closest to my LAB measurement
python -m color_tools color --nearest --value 65.2 25.8 -15.4 --space lab
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

### color_tools.json Structure

The JSON file contains two main sections:

- **colors**: CSS color database with name, hex, RGB, HSL, and LAB values
- **filaments**: 3D printing filament database with manufacturer, type, finish, color name, hex value, and optional transparency (td_value)

Example filament entry:

```json
{
  "maker": "Bambu Lab",
  "type": "PLA",
  "finish": "Basic", 
  "color": "Black",
  "hex": "#000000",
  "td_value": null
}
```

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

When modifying color science constants, always verify integrity:

```bash
python -m color_tools --verify-constants
```

This ensures the mathematical foundation remains scientifically accurate.

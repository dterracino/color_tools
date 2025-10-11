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

The script uses only Python standard library modules - no additional dependencies required.

## Usage

The tool provides three main commands: `color`, `filament`, and `convert`.

### Color Command

Search and query the CSS color database.

#### Find Color by Name

```bash
python color_tools.py color --name "coral"
python color_tools.py color --name "steelblue"
```

#### Find Nearest Color by Value

```bash
# Find nearest CSS color to RGB(128, 64, 200) using CIEDE2000
python color_tools.py color --nearest --value 128 64 200 --space rgb

# Find nearest using LAB values with CIE94 metric
python color_tools.py color --nearest --value 50 25 -30 --space lab --metric de94

# Use CMC color difference formula
python color_tools.py color --nearest --value 70 15 45 --space lab --metric cmc --cmc-l 2.0 --cmc-c 1.0
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
python color_tools.py filament --nearest --value 255 0 0

# Find nearest with specific manufacturer filter
python color_tools.py filament --nearest --value 128 200 64 --maker "Prusament"

# Use different color distance metric
python color_tools.py filament --nearest --value 100 150 200 --metric cmc
```

#### Handle Dual-Color Filaments

Some filaments have two colors (e.g., "#333333-#666666"). Control how these are handled:

```bash
# Use first color (default)
python color_tools.py filament --nearest --value 255 0 0 --dual-color-mode first

# Use second color
python color_tools.py filament --nearest --value 255 0 0 --dual-color-mode last

# Perceptually blend both colors in LAB space
python color_tools.py filament --nearest --value 255 0 0 --dual-color-mode mix
```

#### List and Filter Filaments

```bash
# List all manufacturers
python color_tools.py filament --list-makers

# List all filament types
python color_tools.py filament --list-types

# List all finishes
python color_tools.py filament --list-finishes

# Filter by specific criteria
python color_tools.py filament --filter --maker "Prusament" --type "PLA"
python color_tools.py filament --filter --finish "Matte" --color "Black"
```

**Filament Command Arguments:**

- `--nearest`: Find nearest filament to RGB color
- `--value R G B`: RGB color value (0-255 for each component)
- `--metric {euclidean,de76,de94,de2000,cmc}`: Distance metric (default: de2000)
- `--cmc-l FLOAT`: CMC lightness parameter (default: 2.0)
- `--cmc-c FLOAT`: CMC chroma parameter (default: 1.0)
- `--dual-color-mode {first,last,mix}`: Handle dual-color filaments (default: first)
- `--list-makers`: List all filament manufacturers
- `--list-types`: List all filament types (PLA, PETG, etc.)
- `--list-finishes`: List all finish types (Matte, Glossy, etc.)
- `--filter`: Display filaments matching filter criteria
- `--maker NAME`: Filter by manufacturer
- `--type NAME`: Filter by filament type
- `--finish NAME`: Filter by finish type
- `--color NAME`: Filter by color name

### Convert Command

Convert between color spaces and check gamut constraints.

#### Color Space Conversions

```bash
# Convert RGB to LAB
python color_tools.py convert --from rgb --to lab --value 255 128 0

# Convert LAB to LCH (cylindrical LAB)
python color_tools.py convert --from lab --to lch --value 50 25 -30

# Convert LCH back to RGB
python color_tools.py convert --from lch --to rgb --value 50 33.54 -50.19
```

#### Gamut Checking

```bash
# Check if LAB color is representable in sRGB
python color_tools.py convert --check-gamut --value 50 100 50

# Check LCH color gamut
python color_tools.py convert --check-gamut --from lch --value 70 80 120
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
python color_tools.py filament --nearest --value 180 100 200

# Only search Prusament PLA filaments
python color_tools.py filament --nearest --value 180 100 200 --maker "Prusament" --type "PLA"

# Use CMC color difference (textile industry standard)
python color_tools.py filament --nearest --value 180 100 200 --metric cmc
```

### Color Space Analysis

```bash
# Convert my RGB color to LAB for analysis
python color_tools.py convert --from rgb --to lab --value 180 100 200

# Check if a highly saturated LAB color can be displayed
python color_tools.py convert --check-gamut --value 50 80 60

# Find the CSS color name closest to my LAB measurement
python color_tools.py color --nearest --value 65.2 25.8 -15.4 --space lab
```

### Batch Operations

```bash
# Find all matte black filaments
python color_tools.py filament --filter --finish "Matte" --color "Black"

# List all available Prusa filament types
python color_tools.py filament --filter --maker "Prusament" | grep -o 'type: [^,]*' | sort -u
```

## Data Files

### color_tools.json Structure

The JSON file contains two main sections:

- **colors**: CSS color database with name, hex, RGB, HSL, and LAB values
- **filaments**: 3D printing filament database with manufacturer, type, finish, color name, hex value, and optional transparency (td_value)

Example filament entry:

```json
{
  "maker": "Prusament",
  "type": "PLA",
  "finish": "Matte", 
  "color": "Jet Black",
  "hex": "#000000",
  "td_value": 0.1
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
python color_tools.py --verify-constants
```

This ensures the mathematical foundation remains scientifically accurate.

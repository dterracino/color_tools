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

---

## User Data Files (Optional Extensions)

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

**Example user-synonyms.json:**

```json
{
  "My Local Shop": ["LocalShop", "MLS"],
  "Bambu Lab": ["BBL"]
}
```

**Note:** Users are responsible for avoiding duplicate entries between core and user data files.

### User Override System (v3.8.0+)

User files **automatically override** core data when there are conflicts, ensuring your customizations always take priority:

#### **Override Behavior:**

- **Name conflicts**: User colors/filaments with the same name override core entries
- **RGB conflicts**: User colors/filaments with the same RGB values override core entries
- **Consistent lookups**: All search methods (name, RGB, nearest neighbor) return user overrides consistently
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

Override Details:
  Colors: User colors override 1 core colors by name: [('red', 'colors.json', 'user-colors.json')]
  Colors: User colors override 1 core colors by RGB: [('my_red (255, 0, 0)', 'red (colors.json)', 'user-colors.json')]

Summary:
  Total colors: 142
  Total filaments: 585

Active Sources:
  Colors:
    colors.json: 141 records
    user-colors.json: 1 records
  Filaments:
    filaments.json: 585 records
```

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

Color Tools supports custom color palettes for retro graphics, pixel art, or specialized color matching. Palettes are stored in the `data/palettes/` directory.

### Using Custom Palettes

**Via CLI:**

```bash
# Find nearest color in a custom palette
python -m color_tools color --palette cga4 --nearest --value 128 64 200 --space rgb

# List all available palettes
python -m color_tools image --list-palettes
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

| Palette | Colors | Description |
| --------- | -------- | ------------- |
| `cga4` | 4 | CGA 4-color (Palette 1, high intensity) |
| `cga16` | 16 | CGA 16-color (full RGBI palette) |
| `ega16` | 16 | EGA 16-color (standard/default palette) |
| `ega64` | 64 | EGA 64-color (full 6-bit RGB palette) |
| `vga` | 256 | VGA 256-color (Mode 13h palette) |
| `web` | 216 | Web-safe 216-color palette (6×6×6 RGB cube) |
| `gameboy_dmg` | 4 | Original Game Boy (DMG) green-tinted palette |
| `gameboy_gbl` | 4 | Game Boy Light palette |
| `gameboy_mgb` | 4 | Game Boy Pocket palette |
| `commodore64` | 16 | Commodore 64 palette |

### Creating Custom Palettes

To create a custom palette, add a JSON file to the `data/palettes/` directory:

#### Example: my_palette.json

```json
[
  {
    "name": "Primary Red",
    "hex": "#FF0000",
    "rgb": [255, 0, 0],
    "hsl": [0, 100, 50],
    "lab": [53.23, 80.11, 67.22],
    "lch": [53.23, 104.55, 40.0]
  },
  {
    "name": "Primary Green",
    "hex": "#00FF00",
    "rgb": [0, 255, 0],
    "hsl": [120, 100, 50],
    "lab": [87.74, -86.18, 83.18],
    "lch": [87.74, 119.78, 136.02]
  }
]
```

Then load it with:

```python
# The palette name is the filename without .json extension
my_palette = load_palette('my_palette')
```

---

## Configuration Options

### Dual-Color Mode

Some filaments have two colors (e.g., silk filaments with different appearances from different angles). The dual-color mode controls how these are handled during color matching:

**Via CLI:**

```bash
# Use first color (default)
python -m color_tools filament --nearest --value 255 0 0 --dual-color-mode first

# Use second color
python -m color_tools filament --nearest --value 255 0 0 --dual-color-mode last

# Perceptually blend both colors in LAB space
python -m color_tools filament --nearest --value 255 0 0 --dual-color-mode mix
```

**Via Python API:**

```python
from color_tools import set_dual_color_mode, get_dual_color_mode

# Set mode before loading FilamentPalette
set_dual_color_mode('first')  # Use first color (default)
set_dual_color_mode('last')   # Use second color
set_dual_color_mode('mix')    # Blend colors in LAB space

# Check current mode
print(get_dual_color_mode())
```

### Thread-Safe Configuration

Runtime configuration (like dual-color mode) uses `threading.local()` for thread-safe operation in multi-threaded applications. Each thread can have its own configuration without affecting others.

```python
import threading
from color_tools import set_dual_color_mode, get_dual_color_mode

def thread_with_first_mode():
    set_dual_color_mode('first')
    # This thread uses 'first' mode
    print(f"Thread 1: {get_dual_color_mode()}")

def thread_with_mix_mode():
    set_dual_color_mode('mix')
    # This thread uses 'mix' mode
    print(f"Thread 2: {get_dual_color_mode()}")

t1 = threading.Thread(target=thread_with_first_mode)
t2 = threading.Thread(target=thread_with_mix_mode)
t1.start()
t2.start()
```

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

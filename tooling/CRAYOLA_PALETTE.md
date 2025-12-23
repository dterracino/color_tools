# Crayola Palette Generation

## Overview
Successfully processed `crayola_crayon_colors.json` source data and created the Crayola crayon colors palette.

## Files Created

### 1. Generation Script
- **File**: `tooling/generate_crayola_palette.py`
- **Purpose**: Processes Crayola source data and generates the full palette file
- **Function**: Reads RGB values from source, computes HSL/LAB/LCH color spaces

### 2. Palette File
- **File**: `color_tools/data/palettes/crayola.json`
- **Colors**: 120 Crayola crayon colors
- **Format**: Standard palette format with name, hex, rgb, hsl, lab, lch values

## Usage

### Loading the Palette
```python
from color_tools.palette import load_palette

# Load Crayola palette
crayola = load_palette("crayola")
print(f"Loaded {len(crayola.records)} Crayola colors")

# Find nearest color (using LAB space)
from color_tools.conversions import rgb_to_lab
test_rgb = (255, 127, 80)
test_lab = rgb_to_lab(test_rgb)
color, distance = crayola.nearest_color(test_lab)
print(f"Nearest to {test_rgb}: {color.name} (distance: {distance:.2f})")

# Or use RGB space directly
color, distance = crayola.nearest_color(test_rgb, space='rgb')
print(f"Nearest (RGB space): {color.name}")
```

### Sample Color Matches
| Input RGB      | Nearest Crayola Color |
|----------------|----------------------|
| (255, 127, 80) | Burnt Orange         |
| (255, 0, 0)    | Sunset Orange        |
| (0, 0, 255)    | Purple Heart         |
| (0, 255, 0)    | Screamin' Green      |

## Color Collection
The palette includes 120 colors from the Crayola crayon collection, including:
- **Yellows**: Canary, Laser Lemon, Banana Mania, Goldenrod
- **Oranges**: Atomic Tangerine, Burnt Orange, Sunset Orange
- **Reds**: Scarlet, Red, Brick Red, Maroon
- **Pinks**: Wild Strawberry, Cotton Candy, Carnation Pink
- **Purples**: Royal Purple, Wisteria, Violet, Plum
- **Blues**: Navy Blue, Cerulean, Pacific Blue, Sky Blue
- **Greens**: Jungle Green, Forest Green, Screamin' Green, Spring Green
- **Browns**: Chestnut, Mahogany, Sepia, Burnt Sienna
- **Grays**: Silver, Timberwolf, Gray, Outer Space
- **Black & White**: Black, White

## Regenerating the Palette

If the source data is updated, regenerate the palette with:
```bash
python tooling/generate_crayola_palette.py
```

The script will:
1. Read from `.source_data/crayola_crayon_colors.json`
2. Compute HSL, LAB, and LCH values from RGB
3. Output to `color_tools/data/palettes/crayola.json`

## Notes
- Source data includes CMYK values, but these are not used in the palette (color_tools focuses on RGB/LAB/HSL/LCH)
- Hex values are normalized to lowercase in the output
- All color space values are rounded to 1 decimal place for consistency
- The palette is automatically discovered by `load_palette()` function

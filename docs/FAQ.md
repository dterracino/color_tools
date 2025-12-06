# Frequently Asked Questions

[← Back to README](https://github.com/dterracino/color_tools/blob/main/README.md) | [Troubleshooting](https://github.com/dterracino/color_tools/blob/main/docs/Troubleshooting.md)

---

## Table of Contents

- [General Questions](#general-questions)
- [Color Spaces](#color-spaces)
- [Distance Metrics](#distance-metrics)
- [3D Printing Filaments](#3d-printing-filaments)
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
- **Thread-safe** configuration for multi-threaded applications
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
|----------|-------------------|
| Display/screen colors | RGB |
| User color pickers | HSL or LCH |
| Color matching/comparison | LAB |
| Hue-based adjustments | LCH |
| Printing workflows | LAB |

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

**Delta E** (ΔE) is a measure of color difference. A Delta E of 1.0 is considered the "just noticeable difference" - the smallest color difference the average human eye can perceive.

| Delta E | Perception |
|---------|------------|
| 0-1 | Not perceptible |
| 1-2 | Perceptible through close observation |
| 2-10 | Perceptible at a glance |
| 11-49 | Colors are more similar than opposite |
| 100 | Colors are exact opposite |

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

The database contains **584+ filaments** from major manufacturers including Bambu Lab, Polymaker, Sunlu, Paramount 3D, and more.

### How do I find filaments from a specific manufacturer?

```bash
# List all manufacturers
python -m color_tools filament --list-makers

# Find filaments from a specific maker
python -m color_tools filament --maker "Bambu Lab"

# Use synonyms (Bambu = Bambu Lab)
python -m color_tools filament --maker "Bambu" --type "PLA"
```

### What are maker synonyms?

Maker synonyms allow you to search using common abbreviations or alternate names:

- "Bambu" → "Bambu Lab"
- "Paramount" → "Paramount 3D"
- "BLL" → "Bambu Lab"

### What are dual-color filaments?

Some filaments (especially silk) have two colors that appear different depending on viewing angle. The hex code shows both: `#333333-#666666`. You can choose how to handle them:

```bash
--dual-color-mode first  # Use first color (default)
--dual-color-mode last   # Use second color
--dual-color-mode mix    # Blend both colors in LAB space
```

### How do I find alternatives for unavailable filaments?

Use `--count` to find multiple matches:

```bash
# Find top 5 alternatives to a color
python -m color_tools filament --nearest --value 180 100 200 --count 5

# Find alternatives only in PLA
python -m color_tools filament --nearest --value 180 100 200 --type "PLA" --maker "*" --count 5
```

---

## Image Processing

### What extras do I need for image processing?

Install with the `[image]` extra:

```bash
pip install color-match-tools[image]
```

This adds Pillow for image manipulation.

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

- Classic PC: `cga4`, `cga16`, `ega16`, `ega64`, `vga`
- Game consoles: `gameboy_dmg`, `gameboy_gbl`, `gameboy_mgb`, `commodore64`
- Web: `web` (216-color web-safe palette)

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

For contributing to the core database, submit a pull request with your additions to the main data files.

### How do I update hashes after modifying data files?

Use the automated tooling:

```bash
python tooling/update_hashes.py --autoupdate
```

See [Hash_Update_Guide.md](https://github.com/dterracino/color_tools/blob/main/docs/Hash_Update_Guide.md) for detailed instructions.

### Where do I report bugs or request features?

Open an issue on GitHub: [https://github.com/dterracino/color_tools/issues](https://github.com/dterracino/color_tools/issues)

---

[← Back to README](https://github.com/dterracino/color_tools/blob/main/README.md) | [Troubleshooting](https://github.com/dterracino/color_tools/blob/main/docs/Troubleshooting.md)

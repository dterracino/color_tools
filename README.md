# Color Tools

A comprehensive Python library for color science operations, color space conversions, and color matching. This tool provides perceptually accurate color distance calculations, gamut checking, and extensive databases of CSS colors and 3D printing filament colors.

**Version:** 5.1.0 | [Changelog](https://github.com/dterracino/color_tools/blob/main/CHANGELOG.md)

## 📚 Documentation

**[📖 Full API Documentation](https://dterracino.github.io/color_tools/)** - Complete API reference with examples

### User Guides

| Document | Description |
| ----------- | ------------- |
| [Installation](https://github.com/dterracino/color_tools/blob/main/docs/Installation.md) | Setup, dependencies, development install |
| [Usage](https://github.com/dterracino/color_tools/blob/main/docs/Usage.md) | Library API, CLI commands, examples |
| [Customization](https://github.com/dterracino/color_tools/blob/main/docs/Customization.md) | Data files, custom palettes, configuration |
| [Troubleshooting](https://github.com/dterracino/color_tools/blob/main/docs/Troubleshooting.md) | Error handling, performance, technical notes |
| [FAQ](https://github.com/dterracino/color_tools/blob/main/docs/FAQ.md) | Color spaces, distance metrics, contributing |

## ✨ Features

- **Multiple Color Spaces**: RGB, HSL, LAB, LCH with accurate conversions
- **Perceptual Color Distance**: Delta E formulas (CIE76, CIE94, CIEDE2000, CMC)
- **Color Databases**:
  - Complete CSS color names with hex/RGB/HSL/LAB/LCH values
  - Extensive 3D printing filament database (584 filaments) with manufacturer info
  - Unique semantic IDs for all filaments (e.g., "bambu-lab-pla-silk-red")
  - Alternative name support for regional variations and rebranding
  - Maker synonym support for flexible filament searches
  - **Retro/Classic Palettes**: CGA, EGA, VGA, and Web-safe color palettes
- **Image Transformations** *(with [image] extra)*:
  - **Color Vision Deficiency (CVD)**: Simulate and correct for colorblindness (protanopia, deuteranopia, tritanopia)
  - **Palette Quantization**: Convert images to retro palettes (CGA, EGA, VGA, Game Boy) with dithering support
  - **Unified Architecture**: All transformations leverage existing color science infrastructure
- **Gamut Checking**: Verify if colors are representable in sRGB
- **Thread-Safe**: Configurable runtime settings per thread
- **Color Science Integrity**: Built-in verification of color constants

## 🚀 Quick Start

### Installation

```bash
# Base package (zero dependencies)
pip install color-match-tools

# With image processing support
pip install color-match-tools[image]

# With all optional features
pip install color-match-tools[all]
```

See [Installation Guide](https://github.com/dterracino/color_tools/blob/main/docs/Installation.md) for development setup and detailed options.

### CLI Usage

```bash
# Find a CSS color by name
color-tools color --name coral

# Find nearest CSS color to an RGB value
color-tools color --nearest --value 255 128 64 --space rgb

# Find matching 3D printing filaments
color-tools filament --nearest --value 255 128 64

# Convert between color spaces
color-tools convert --from rgb --to lab --value 255 128 64

# Simulate colorblindness on an image
color-tools image --file photo.jpg --cvd-simulate deuteranopia

# Convert image to retro CGA palette
color-tools image --file photo.jpg --quantize-palette cga4 --dither
```

### Library Usage

```python
from color_tools import rgb_to_lab, delta_e_2000, Palette, FilamentPalette

# Convert RGB to LAB
lab = rgb_to_lab((255, 128, 64))
print(f"LAB: {lab}")

# Find nearest CSS color
palette = Palette.load_default()
nearest, distance = palette.nearest_color(lab, space="lab")
print(f"Nearest: {nearest.name} (ΔE: {distance:.2f})")

# Find matching filaments
filament_palette = FilamentPalette.load_default()
filament, distance = filament_palette.nearest_filament((255, 128, 64))
print(f"Filament: {filament.maker} {filament.color}")
```

See [Usage Guide](https://github.com/dterracino/color_tools/blob/main/docs/Usage.md) for complete API reference and CLI documentation.

## 🎨 Color Spaces

| Space | Description | Range |
| ------- | ------------- | ------- |
| **RGB** | Red, Green, Blue | 0-255 per component |
| **HSL** | Hue, Saturation, Lightness | H: 0-360°, S: 0-100%, L: 0-100% |
| **LAB** | Perceptually uniform | L: 0-100, a/b: ±100 |
| **LCH** | Cylindrical LAB | L: 0-100, C: 0+, H: 0-360° |

**Use LAB or LCH for color matching** - they're designed to match human perception.

## 📏 Distance Metrics

| Metric | Use Case |
| -------- | ---------- |
| **CIEDE2000** (`de2000`) | **Recommended** - Gold standard for perceptual accuracy |
| **CIE94** (`de94`) | Good balance of accuracy and performance |
| **CIE76** (`de76`) | Fast, simple Euclidean in LAB space |
| **CMC** (`cmc`) | Textile industry standard |

See [FAQ](https://github.com/dterracino/color_tools/blob/main/docs/FAQ.md) for detailed explanations of when to use each metric.

## 📦 Data Files

The library includes extensive color databases:

- **CSS Colors**: 147 named colors with full color space representations
- **3D Printing Filaments**: 584+ filaments from major manufacturers
- **Retro Palettes**: CGA, EGA, VGA, Game Boy, Commodore 64, and more

Extend with your own data using [User Data Files](https://github.com/dterracino/color_tools/blob/main/docs/Customization.md#user-data-files-optional-extensions).

## 🔒 Data Integrity

All core data files are protected with SHA-256 hashes:

```bash
python -m color_tools --verify-all
```

See [Troubleshooting](https://github.com/dterracino/color_tools/blob/main/docs/Troubleshooting.md#data-integrity-verification) for verification details.

## 🤝 Contributing

**CRITICAL**: Color science constants should **NEVER** be modified. They represent fundamental values from international standards.

See [FAQ](https://github.com/dterracino/color_tools/blob/main/docs/FAQ.md#contributing) for contribution guidelines.

## 📄 License

MIT License - see [LICENSE](https://github.com/dterracino/color_tools/blob/main/LICENSE) for details.

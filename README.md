# Color Tools

A comprehensive Python library for color science operations, color space conversions, and color matching. This tool provides perceptually accurate color distance calculations, gamut checking, and extensive databases of CSS colors and 3D printing filament colors.

[![PyPI version](https://img.shields.io/pypi/v/color-match-tools.svg)](https://pypi.org/project/color-match-tools/)
[![Python versions](https://img.shields.io/pypi/pyversions/color-match-tools.svg)](https://pypi.org/project/color-match-tools/)
[![CI](https://github.com/dterracino/color_tools/actions/workflows/ci.yml/badge.svg)](https://github.com/dterracino/color_tools/actions/workflows/ci.yml)
[![CodeQL](https://github.com/dterracino/color_tools/actions/workflows/codeql.yml/badge.svg)](https://github.com/dterracino/color_tools/actions/workflows/codeql.yml)
[![codecov](https://codecov.io/gh/dterracino/color_tools/branch/main/graph/badge.svg)](https://codecov.io/gh/dterracino/color_tools)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/dterracino/color_tools/blob/main/LICENSE)
[![PyPI downloads](https://img.shields.io/pypi/dm/color-match-tools.svg)](https://pypi.org/project/color-match-tools/)

[Changelog](https://github.com/dterracino/color_tools/blob/main/CHANGELOG.md)

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
- **Perceptual Color Distance**: Delta E formulas (CIE76, CIE94, CIEDE2000, CMC, HyAB)
- **Color Databases**:
  - Complete CSS color names with hex/RGB/HSL/LAB/LCH values
  - Extensive 3D printing filament database (913 filaments) with manufacturer info
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

# With interactive filament library manager
pip install color-match-tools[interactive]

# With colorized console logging (Rich)
pip install color-match-tools[logging]

# With all optional features
pip install color-match-tools[all]
```

See [Installation Guide](https://github.com/dterracino/color_tools/blob/main/docs/Installation.md) for development setup and detailed options.

### CLI Usage

```bash
# Interactive wizard — guided prompts for color, filament, and convert
# (requires: pip install color-match-tools[interactive])
color-tools
color-tools --interactive

# Find a CSS color by name
color-tools color --name coral

# Find nearest CSS color to an RGB value
color-tools color --nearest --value 255 128 64 --space rgb

# Find matching 3D printing filaments
color-tools filament --nearest --value 255 128 64

# Convert between color spaces
color-tools convert --from rgb --to lab --value 255 128 64
color-tools convert --from rgb --to cmyk --value 255 128 64
color-tools convert --from cmyk --to rgb --value 0 50 75 0

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
| **CMY** | Subtractive (no black channel) | C/M/Y: 0-100% each |
| **CMYK** | Subtractive print model (with black) | C/M/Y/K: 0-100% each |

**Use LAB or LCH for color matching** - they're designed to match human perception.
**Use CMYK for print workflows** - the K channel produces richer blacks than CMY alone.

## 📏 Distance Metrics

| Metric | Use Case |
| -------- | ---------- |
| **CIEDE2000** (`de2000`) | **Recommended** - Gold standard for perceptual accuracy |
| **CIE94** (`de94`) | Good balance of accuracy and performance |
| **CIE76** (`de76`) | Fast, simple Euclidean in LAB space |
| **CMC** (`cmc`) | Textile industry standard |
| **HyAB** (`hyab`) | Best for large color differences and image quantization |

See [FAQ](https://github.com/dterracino/color_tools/blob/main/docs/FAQ.md) for detailed explanations of when to use each metric.

## 📦 Data Files

The library includes extensive color databases:

- **CSS Colors**: 147 named colors with full color space representations
- **3D Printing Filaments**: 584+ filaments from major manufacturers
- **Retro Palettes**: 20 official palettes including CGA, EGA, VGA, Game Boy, Commodore 64, PICO-8, and more

Extend with your own data using [User Data Files](https://github.com/dterracino/color_tools/blob/main/docs/Customization.md#user-data-files-optional-extensions).

**Track your owned filaments** for personalized color matching - create an `owned-filaments.json` file to automatically filter searches to filaments you already have. See [Owned Filaments](https://github.com/dterracino/color_tools/blob/main/docs/Customization.md#owned-filamentsjson---filament-ownership-tracking) in the Customization Guide.

## 🔧 Export & Integration

Export colors and filaments to various formats for use with external tools:

### Available Formats

**Universal Formats (Colors + Filaments):**

- **CSV** - Generic CSV with all fields (preserves full metadata)
- **JSON** - Raw data format for backup/restore (preserves full metadata)

**Palette/Graphics Applications (Colors Only):**

- **GIMP Palette (.gpl)** - Import into GIMP, Inkscape, Krita
- **Hex (.hex)** - Simple hex color list (uppercase, no # prefix)
- **JASC-PAL (.pal)** - Paint Shop Pro palette format (compatible with Aseprite)
- **PAINT.NET (.txt)** - PAINT.NET palette format (AARRGGBB hex codes)
- **Lospec JSON (.json)** - Lospec.com palette format for sharing palettes

**3D Printing (Filaments Only):**

- **AutoForge (.csv)** - Specialized CSV for AutoForge/HueForge lithophane workflow

> **Note:** Palette formats (Hex, JASC-PAL, PAINT.NET, Lospec) only export color values and lose filament metadata (maker, type, finish, TD values). For full filament data preservation, use CSV or JSON.

### Export Examples

```python
from color_tools import Palette, FilamentPalette
from color_tools.exporters import get_exporter, list_export_formats

# List available formats for colors
formats = list_export_formats('colors')
print(formats)
# {'csv': '...', 'json': '...', 'gpl': '...', 'hex': '...', 'pal': '...', ...}

# Export to various formats
palette = Palette.load_default()

# GIMP Palette for graphics work
get_exporter('gpl').export_colors(palette.records[:20], 'colors.gpl')

# Hex format for web/programming
get_exporter('hex').export_colors(palette.records[:20], 'colors.hex')

# JASC-PAL for Paint Shop Pro/Aseprite
get_exporter('pal').export_colors(palette.records[:20], 'colors.pal')

# Lospec JSON for sharing online
get_exporter('lospec').export_colors(palette.records[:20], 'palette.json')

# Export filaments to AutoForge CSV
filaments = FilamentPalette.load_default()
bambu_pla = filaments.filter(maker="Bambu Lab", type_name="PLA")
get_exporter('autoforge').export_filaments(bambu_pla, 'bambu_pla.csv')
```

### Plugin Architecture

The exporter system uses a plugin architecture - new formats can be added without modifying existing code:

```python
from color_tools.exporters import register_exporter
from color_tools.exporters.base import PaletteExporter, ExporterMetadata

@register_exporter
class MyExporter(PaletteExporter):
    @property
    def metadata(self):
        return ExporterMetadata(
            name='myformat',
            description='My custom format',
            file_extension='txt',
            supports_colors=True,
            supports_filaments=False,
        )
    
    def _export_colors_impl(self, colors, output_path):
        # Implementation here
        pass
```

See [exporters/gpl_exporter.py](https://github.com/dterracino/color_tools/blob/main/color_tools/exporters/gpl_exporter.py) for a complete example.

## 📋 Logging

The library ships with a structured logging system that fans out to console and an
optional rotating file — one call, both destinations:

```python
from pathlib import Path
import logging
from color_tools import setup_logging, get_logger, log_info

# Console-only (INFO+ by default)
setup_logging()

# Console + rotating file (DEBUG+ to file, INFO+ to console)
setup_logging(log_file=Path("color_tools.log"), console_level=logging.DEBUG)

# Module-level logger (use __name__ to get "color_tools.mymodule")
logger = get_logger(__name__)
logger.info("Loaded %d colors", count)

# Convenience shortcuts on the library root logger
log_info("Processing %d filaments", n)
```

For colorized console output install the `[logging]` extra:

```bash
pip install color-match-tools[logging]   # adds Rich
```

The library registers a `NullHandler` at import time (Python library best practice), so
no output is produced until `setup_logging()` is explicitly called.

**CLI file logging** — write logs while using the command line:

```bash
color-tools --log-file color_tools.log color --nearest --hex "#FF8040"
color-tools --log-file debug.log --log-level DEBUG filament --nearest --hex "#FF0000"
```

See [Usage Guide](https://github.com/dterracino/color_tools/blob/main/docs/Usage.md#logging) for the full API reference.

## �🔒 Data Integrity

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

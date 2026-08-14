# Color Tools

A comprehensive Python library for color science operations, color space conversions, and color matching. This tool provides perceptually accurate color distance calculations, gamut checking, and extensive databases of CSS colors and 3D printing filament colors.

[![PyPI version](https://img.shields.io/pypi/v/color-match-tools.svg)](https://pypi.org/project/color-match-tools/)
[![Python versions](https://img.shields.io/pypi/pyversions/color-match-tools.svg)](https://pypi.org/project/color-match-tools/)
[![CI](https://github.com/dterracino/color_tools/actions/workflows/ci.yml/badge.svg)](https://github.com/dterracino/color_tools/actions/workflows/ci.yml)
[![CodeQL](https://github.com/dterracino/color_tools/actions/workflows/codeql.yml/badge.svg)](https://github.com/dterracino/color_tools/actions/workflows/codeql.yml)
[![codecov](https://codecov.io/gh/dterracino/color_tools/branch/main/graph/badge.svg)](https://codecov.io/gh/dterracino/color_tools)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/dterracino/color_tools/blob/main/LICENSE)
[![PyPI downloads](https://img.shields.io/pypi/dm/color-match-tools.svg)](https://pypi.org/project/color-match-tools/)

[![Color of the Day](https://color-tools-nine.vercel.app/badges/color_of_day)](https://color-tools-nine.vercel.app/badges/color_of_day)
[![Filament of the Day](https://color-tools-nine.vercel.app/badges/filament_of_day)](https://color-tools-nine.vercel.app/badges/filament_of_day)

> **Note:** The swatch images above are served by a personal demo deployment — not a public API.
> They may change or be unavailable without notice. See [docs/Badges.md](https://github.com/dterracino/color_tools/blob/main/docs/Badges.md) for details.

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
- **Agent Integration** *(with [mcp] extra)*: Typed MCP tools for color analysis, conversion,
  perceptual comparison, palette search, filament matching, gamut mapping, and CVD transforms
- **Thread-Safe**: Configurable runtime settings per thread
- **Color Science Integrity**: Built-in verification of color constants

## 🎨 Demos

### Color Vision Deficiency (CVD) Simulation & Correction

![CVD Demo – Protanopia, Deuteranopia, Tritanopia](cvd_demo.png)

*Animated: Original → Simulated (colorblind view) → Corrected, for all three deficiency types (protanopia, deuteranopia, tritanopia).*

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

# With the Color Tools MCP server for agents
pip install color-match-tools[mcp]

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

# Generate a calm, dark triadic harmony
color-tools harmony --type triadic --hex "#E0006B" --mood calm --tone dark

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

### Color Harmonies

Generate perceptual color harmonies in CIE LCH space from an RGB base color:

```python
from color_tools import generate_harmony

palette = generate_harmony(
  (224, 0, 107),
  "triadic",
  mood="calm",
  tone="dark",
)

print([color.hex for color in palette.colors])
```

Harmony schemes include analogous, complementary, split-complementary, triadic, square,
tetradic, monochromatic, and six-color rainbow/full-spectrum. Optional `warm`, `cool`,
`happy`, `calm`, `intense`, `sad`, and `energetic` mood presets adjust palette lightness and
chroma without changing the harmony's hue relationships. Independent `dark` and `light` tones
can be composed with any mood.

Mood presets are opinionated design heuristics rather than universal psychological rules. The
base color remains unchanged by default; pass `grade_base=True` to style it with the generated
colors.

### MCP Server

The optional MCP server exposes Color Tools to GitHub Copilot and other MCP-compatible agents as
typed, structured tools:

```bash
pip install "color-match-tools[mcp]"
color-tools-mcp
```

MCP clients normally launch the stdio server automatically with `python -m color_tools.mcp`.
See the [MCP server guide](https://github.com/dterracino/color_tools/blob/main/color_tools/mcp/README.md)
for the tool catalog and client configuration.

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

| Identifier | Output | Data | Palette metadata | Dependency |
| --- | --- | --- | --- | --- |
| `ase` | Adobe Swatch Exchange (`.ase`) | Colors | Yes | `swatch` via `[image]` |
| `autoforge` | AutoForge CSV (`.csv`) | Filaments | No | None |
| `css` | CSS custom properties (`.css`) | Colors | No | None |
| `csv` | Generic CSV (`.csv`) | Colors and filaments | No | None |
| `gpl` | GIMP Palette (`.gpl`) | Colors | Yes | None |
| `hex` | Plain HEX list (`.hex`) | Colors | No | None |
| `jasc_pal` | JASC Paint Shop Pro palette (`.pal`) | Colors | No | None |
| `json` | Generic JSON (`.json`) | Colors and filaments | Yes for palettes | None |
| `kpl` | Krita palette (`.kpl`) | Colors | Yes | None |
| `lospec` | Lospec JSON (`.json`) | Colors | Yes | None |
| `paintnet` | PAINT.NET palette (`.txt`) | Colors | No | None |
| `palette_lut` | GPU palette LUT (`.png`) | Colors | No | None |
| `riff_pal` | Microsoft RIFF palette (`.pal`) | Colors | No | None |
| `scribus` | Scribus XML palette (`.xml`) | Colors | Yes | None |
| `sketchpalette` | Sketch Palettes plugin (`.sketchpalette`) | Colors | No | None |
| `soc` | LibreOffice/OpenOffice palette (`.soc`) | Colors | No | None |
| `swatch_image` | Presentation swatch sheet (`.png`) | Colors | Yes | Pillow via `[image]` |

`list_export_formats()` returns only formats whose optional dependencies are installed by default.
Pass `available_only=False` to include unavailable formats. Install `color-match-tools[image]`
for ASE and presentation swatch images.

### Export Examples

```python
from color_tools import Palette, FilamentPalette
from color_tools.exporters import get_exporter, list_export_formats
from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.palette_metadata import PaletteMetadata
from color_tools.exporters.swatch_image_exporter import SwatchImageOptions

# List available formats for colors
formats = list_export_formats("colors")

# Export raw color records
palette = Palette.load_default()
get_exporter("gpl").export_colors(palette.records[:20], "colors.gpl")
get_exporter("jasc_pal").export_colors(palette.records[:20], "colors.pal")

# Preserve palette-level metadata when the format supports it
palette_data = PaletteExportData(
  colors=palette.records[:8],
  metadata=PaletteMetadata(
    name="Sample Palette",
    author="Color Tools",
    description="Eight colors exported with palette metadata.",
    columns=4,
  ),
)
get_exporter("json").export_palette(palette_data, "palette.json")

# Supply strongly typed, per-export options to configurable exporters
get_exporter("swatch_image").export_palette(
  palette_data,
  "palette.png",
  options=SwatchImageOptions(show_rgb=True, show_lab=True),
)

# Export filament records
filaments = FilamentPalette.load_default()
bambu_pla = filaments.filter(maker="Bambu Lab", type_name="PLA")
get_exporter("autoforge").export_filaments(bambu_pla, "bambu_pla.csv")
```

The functions in `color_tools.export`, including `export_colors()` and `export_filaments()`,
remain available as backward-compatible facades. New integrations should use the exporter registry
when they need capability metadata, palette metadata, optional dependency checks, or typed options.

### Plugin Architecture

The exporter system uses a plugin architecture - new formats can be added without modifying existing code:

```python
from color_tools.exporters import register_exporter
from color_tools.exporters.base import PaletteExporter, ExporterMetadata

@register_exporter
class MyExporter(PaletteExporter):
    @property
  def metadata(self) -> ExporterMetadata:
        return ExporterMetadata(
      name="myformat",
      description="My custom format",
      file_extension="txt",
            supports_colors=True,
            supports_filaments=False,
        )

  def _export_colors_impl(self, colors, output_path) -> str:
    # Write the file and return its path.
    return str(output_path)
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

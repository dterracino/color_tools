# Import and Export System

## Status

- **Export system:** Implemented as a registry-driven plugin architecture.
- **Import system:** Not implemented; the proposal remains documented below.

The export implementation is code-driven. There are no `export-formats.json` or
`user-export-formats.json` files. Each concrete exporter declares its behavior through
`ExporterMetadata` and registers itself with `@register_exporter`.

## Current Export Architecture

```text
color_tools/
  export.py                         # Backward-compatible facade functions
  exporters/
    __init__.py                     # Public package API and built-in registration
    base.py                         # PaletteExporter and capability metadata
    export_options_base.py          # Base type for per-export configuration
    palette_export_data.py          # Colors plus palette-level metadata
    palette_metadata.py             # Shared palette metadata model
    registry.py                     # Registration, lookup, and discovery
    *_exporter.py                   # One implementation per format
```

The registry stores exporter classes and returns a fresh stateless instance from
`get_exporter()`. Optional dependencies are declared in metadata and checked only when the
exporter is used. `list_export_formats()` omits unavailable exporters by default.

### Export Operations

`PaletteExporter` exposes three operations:

- `export_colors(colors, output_path=None, options=None)` exports raw `ColorRecord` values.
- `export_filaments(filaments, output_path=None, options=None)` exports `FilamentRecord` values.
- `export_palette(palette, output_path=None, options=None)` exports colors together with
  `PaletteMetadata` when the format supports it.

Existing calls without `options` remain valid. Configurable exporters declare an
`ExportOptionsBase` subclass through `ExporterMetadata.options_type`; the base class validates
that callers supply the correct options type.

### Discovery

```python
from color_tools.exporters import get_exporter, list_export_formats

# Only installed and usable color exporters.
available = list_export_formats("colors")

# Include formats whose optional dependencies are missing.
registered = list_export_formats("colors", available_only=False)

exporter = get_exporter("gpl")
print(exporter.metadata.supports_palette_metadata)
print(exporter.is_available)
print(exporter.missing_dependencies)
```

Supported filters are `"colors"`, `"filaments"`, and `"both"`.

## Registered Formats

| Identifier | Extension | Data | Palette metadata | Notes |
| --- | --- | --- | --- | --- |
| `ase` | `.ase` | Colors | Yes | Adobe Swatch Exchange; requires `swatch` |
| `autoforge` | `.csv` | Filaments | No | AutoForge filament library |
| `css` | `.css` | Colors | No | CSS custom properties |
| `csv` | `.csv` | Both | No | All record fields |
| `gpl` | `.gpl` | Colors | Yes | GIMP palette |
| `hex` | `.hex` | Colors | No | One `RRGGBB` value per line |
| `jasc_pal` | `.pal` | Colors | No | JASC Paint Shop Pro palette |
| `json` | `.json` | Both | Yes for palettes | All record fields |
| `kpl` | `.kpl` | Colors | Yes | Krita native palette |
| `lospec` | `.json` | Colors | Yes | Lospec-compatible JSON |
| `paintnet` | `.txt` | Colors | No | PAINT.NET palette |
| `palette_lut` | `.png` | Colors | No | One-pixel-high GPU LUT |
| `riff_pal` | `.pal` | Colors | No | Microsoft RIFF palette |
| `scribus` | `.xml` | Colors | Yes | Scribus XML palette |
| `sketchpalette` | `.sketchpalette` | Colors | No | Sketch Palettes plugin |
| `soc` | `.soc` | Colors | No | LibreOffice/OpenOffice palette |
| `swatch_image` | `.png` | Colors | Yes | Presentation image; requires Pillow |

The `[image]` extra installs the optional dependencies used by `ase` and `swatch_image`.

## Library Usage

### Raw Records

```python
from color_tools import Palette
from color_tools.exporters import get_exporter

palette = Palette.load_default()
get_exporter("hex").export_colors(
    palette.records,
    "colors.hex",
)
```

### Palette Metadata

```python
from color_tools.exporters import get_exporter
from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.palette_metadata import PaletteMetadata

palette_data = PaletteExportData(
    colors=palette.records[:16],
    metadata=PaletteMetadata(
        name="Example Palette",
        author="Color Tools",
        description="A metadata-aware palette export.",
        columns=4,
        tags=("example", "documentation"),
    ),
)

get_exporter("gpl").export_palette(
    palette_data,
    "example.gpl",
)
```

Formats without palette metadata support accept `export_palette()` but fall back to exporting
the ordered color records.

### Typed Export Options

```python
from color_tools.exporters import get_exporter
from color_tools.exporters.swatch_image_exporter import SwatchImageOptions

get_exporter("swatch_image").export_palette(
    palette_data,
    "example.png",
    options=SwatchImageOptions(
        show_index=True,
        show_hex=True,
        show_rgb=True,
        show_lab=True,
        show_lch=True,
    ),
)
```

Options configure one export operation rather than mutating the exporter instance.

### Backward-Compatible Facade

The functions in `color_tools.export` continue to delegate to the registry:

```python
from color_tools import export_colors, export_filaments

export_colors(colors, "json", "colors.json")
export_filaments(filaments, "autoforge", "filaments.csv")
```

The argument order is records, format identifier, then optional output path.

## CLI Usage

```bash
# List formats available in the current environment.
python -m color_tools color --list-export-formats
python -m color_tools filament --list-export-formats

# Export colors or filtered filaments.
python -m color_tools color --export json --output colors.json
python -m color_tools filament --maker "Bambu Lab" --export autoforge --output bambu.csv
```

CLI exports use the backward-compatible facade and default exporter settings. Exporter-specific
typed options are currently available through the Python API.

## Adding an Exporter

1. Create a module under `color_tools/exporters/`.
2. Subclass `PaletteExporter`.
3. Declare capabilities through `ExporterMetadata`.
4. Decorate the class with `@register_exporter`.
5. Import the module from `color_tools/exporters/__init__.py` so built-in registration occurs.
6. Add focused format, registry, dependency, metadata, and error-path tests.
7. Add the module to the Sphinx autosummary tree.

Use lazy imports inside the export implementation for optional third-party dependencies so the
base package remains importable without extras.

## Future Import System

No general import framework or import CLI currently exists. A future implementation may provide:

- HueForge and AutoForge filament imports.
- Explicit field mapping and value transformations.
- Validation before writing user-managed data.
- Duplicate detection across core and user records.
- `skip`, `update`, and `replace` merge strategies.
- Dry-run reports and atomic writes.
- User-data imports by default, with protected core-data updates requiring explicit confirmation
  and hash regeneration.

The import design should be specified from verified external format documentation before coding.
It should not reuse the exporter registry unless a shared abstraction removes real complexity;
import and export have different validation, conflict-resolution, and persistence concerns.

## Open Questions

- Which import format has the strongest immediate user need?
- Should import duplicate identity be based on stable IDs, names, colors, or format-specific keys?
- Which exporter-specific options should become available through the CLI?
- Should third-party applications be able to register exporters through Python entry points?

**Last updated:** 2026-08-11

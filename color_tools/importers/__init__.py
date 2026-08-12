"""
Palette importer system.

Importers convert external palette formats into the shared color_tools palette
representation:

    PaletteExportData
        ├── list[ColorRecord]
        └── PaletteMetadata

Importer classes register automatically when this package is imported.

Basic usage:

    >>> from color_tools.importers import import_palette
    >>>
    >>> palette = import_palette("palette.gpl")
    >>> print(palette.metadata.name)

Explicit importer selection is also available:

    >>> from color_tools.importers import get_importer
    >>>
    >>> importer = get_importer("gpl")
    >>> palette = importer.import_palette("palette.gpl")

Automatic detection becomes especially useful for extensions shared by multiple
formats. For example, future JASC PAL and RIFF PAL importers can both register
the ``.pal`` extension and distinguish themselves by inspecting file contents.
"""

from color_tools.importers.base import (
    ImporterDependency,
    ImporterMetadata,
    MissingImporterDependencyError,
    PaletteImporter,
)
from color_tools.importers.registry import (
    detect_importer,
    get_importer,
    get_importers_for_extension,
    import_palette,
    list_import_formats,
    register_importer,
)

# Import concrete importers to trigger @register_importer registration.
from color_tools.importers.gpl_importer import GPLImporter
from color_tools.importers.hex_importer import HexImporter
from color_tools.importers.jascpal_importer import JascPalImporter
from color_tools.importers.riffpal_importer import RiffPalImporter


__all__ = [
    "ImporterDependency",
    "ImporterMetadata",
    "MissingImporterDependencyError",
    "PaletteImporter",
    "register_importer",
    "get_importer",
    "get_importers_for_extension",
    "detect_importer",
    "import_palette",
    "list_import_formats",
    "GPLImporter",
    "HexImporter",
    "JascPalImporter",
    "RiffPalImporter",
]

"""
Palette and filament importer system.

Importers convert external files into the corresponding shared transfer model:

    PaletteExportData
        ├── list[ColorRecord]
        └── PaletteMetadata

    FilamentExportData
        ├── list[FilamentRecord]
        └── FilamentMetadata

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

Palette and filament registries are separate, so JSON formats are detected in
the context of the requested data kind.
"""

from color_tools.importers.base import (
    ImporterDependency,
    ImporterMetadata,
    MissingImporterDependencyError,
    PaletteImporter,
)
from color_tools.importers.filament_importer import FilamentImporter
from color_tools.importers.registry import (
    detect_filament_importer,
    detect_importer,
    get_filament_importer,
    get_filament_importers_for_extension,
    get_importer,
    get_importers_for_extension,
    import_filaments,
    import_palette,
    list_filament_import_formats,
    list_import_formats,
    register_filament_importer,
    register_importer,
)

# Import concrete importers to trigger @register_importer registration.
from color_tools.importers.gpl_importer import GPLImporter
from color_tools.importers.hex_importer import HexImporter
from color_tools.importers.jascpal_importer import JascPalImporter
from color_tools.importers.riffpal_importer import RiffPalImporter
from color_tools.importers.user_colors_importer import UserColorsImporter
from color_tools.importers.user_filaments_importer import UserFilamentsImporter


__all__ = [
    "ImporterDependency",
    "ImporterMetadata",
    "FilamentImporter",
    "MissingImporterDependencyError",
    "PaletteImporter",
    "register_importer",
    "register_filament_importer",
    "get_importer",
    "get_filament_importer",
    "get_importers_for_extension",
    "get_filament_importers_for_extension",
    "detect_importer",
    "detect_filament_importer",
    "import_palette",
    "import_filaments",
    "list_import_formats",
    "list_filament_import_formats",
    "GPLImporter",
    "HexImporter",
    "JascPalImporter",
    "RiffPalImporter",
    "UserColorsImporter",
    "UserFilamentsImporter",
]

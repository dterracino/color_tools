"""Typed registries for palette and filament import formats."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from color_tools.importers.base import ImporterBase

if TYPE_CHECKING:
    from color_tools.exporters.filament_export_data import FilamentExportData
    from color_tools.exporters.palette_export_data import PaletteExportData
    from color_tools.importers.base import PaletteImporter
    from color_tools.importers.filament_importer import FilamentImporter


_ImporterT = TypeVar("_ImporterT", bound=ImporterBase)

_IMPORTERS: dict[str, type[PaletteImporter]] = {}
_FILAMENT_IMPORTERS: dict[str, type[FilamentImporter]] = {}


def _register(
    registry: dict[str, type[_ImporterT]],
    cls: type[_ImporterT],
) -> type[_ImporterT]:
    """Register one importer class in a typed data-kind registry."""
    name = cls().metadata.name
    if name in registry:
        raise ValueError(
            f"Importer '{name}' is already registered. "
            "Each importer must have a unique name."
        )
    registry[name] = cls
    return cls


def _get(
    registry: dict[str, type[_ImporterT]],
    format_name: str,
) -> _ImporterT:
    """Create a fresh importer from a typed registry."""
    importer_class = registry.get(format_name)
    if importer_class is None:
        available = ", ".join(sorted(registry))
        raise ValueError(
            f"Unknown import format: '{format_name}'. "
            f"Available formats: {available}"
        )
    return importer_class()


def _list_formats(
    registry: dict[str, type[_ImporterT]],
    *,
    available_only: bool,
) -> dict[str, str]:
    """List descriptions from one typed importer registry."""
    result: dict[str, str] = {}
    for name, importer_class in registry.items():
        importer = importer_class()
        if available_only and not importer.is_available:
            continue
        result[name] = importer.metadata.description
    return result


def _for_extension(
    registry: dict[str, type[_ImporterT]],
    extension: str,
    *,
    available_only: bool,
) -> list[_ImporterT]:
    """Return available importers supporting one normalized extension."""
    normalized = extension.removeprefix(".").lower()
    result: list[_ImporterT] = []
    for importer_class in registry.values():
        importer = importer_class()
        if available_only and not importer.is_available:
            continue
        extensions = {
            item.lower() for item in importer.metadata.file_extensions
        }
        if normalized in extensions:
            result.append(importer)
    return result


def _detect(
    registry: dict[str, type[_ImporterT]],
    input_path: Path | str,
    *,
    format_label: str,
) -> _ImporterT:
    """Detect one importer by extension and format-specific inspection."""
    path = Path(input_path)
    title = format_label.capitalize()
    if not path.exists():
        raise FileNotFoundError(f"{title} file does not exist: {path}")

    candidates = _for_extension(
        registry,
        path.suffix,
        available_only=True,
    )
    if not candidates:
        extension = path.suffix or "<none>"
        raise ValueError(
            f"No {format_label} importer is registered for "
            f"extension '{extension}'"
        )

    matches = [
        importer for importer in candidates if importer.can_import(path)
    ]
    if len(matches) == 1:
        return matches[0]

    candidate_names = ", ".join(
        importer.metadata.name for importer in candidates
    )
    if not matches:
        raise ValueError(
            f"Unable to determine {format_label} format for '{path}'. "
            f"Candidate importers: {candidate_names}"
        )

    match_names = ", ".join(importer.metadata.name for importer in matches)
    raise ValueError(
        f"{title} format for '{path}' is ambiguous. "
        f"Matching importers: {match_names}"
    )


def register_importer(
    cls: type[PaletteImporter],
) -> type[PaletteImporter]:
    """Register a palette importer class and return the original class."""
    return _register(_IMPORTERS, cls)


def register_filament_importer(
    cls: type[FilamentImporter],
) -> type[FilamentImporter]:
    """Register a filament importer class and return the original class."""
    return _register(_FILAMENT_IMPORTERS, cls)


def get_importer(format_name: str) -> PaletteImporter:
    """Create a palette importer by registered format name."""
    return _get(_IMPORTERS, format_name)


def get_filament_importer(format_name: str) -> FilamentImporter:
    """Create a filament importer by registered format name."""
    return _get(_FILAMENT_IMPORTERS, format_name)


def list_import_formats(*, available_only: bool = True) -> dict[str, str]:
    """List registered palette import formats and descriptions."""
    return _list_formats(_IMPORTERS, available_only=available_only)


def list_filament_import_formats(
    *,
    available_only: bool = True,
) -> dict[str, str]:
    """List registered filament import formats and descriptions."""
    return _list_formats(_FILAMENT_IMPORTERS, available_only=available_only)


def get_importers_for_extension(
    extension: str,
    *,
    available_only: bool = True,
) -> list[PaletteImporter]:
    """Return palette importers registered for a file extension."""
    return _for_extension(
        _IMPORTERS,
        extension,
        available_only=available_only,
    )


def get_filament_importers_for_extension(
    extension: str,
    *,
    available_only: bool = True,
) -> list[FilamentImporter]:
    """Return filament importers registered for a file extension."""
    return _for_extension(
        _FILAMENT_IMPORTERS,
        extension,
        available_only=available_only,
    )


def detect_importer(input_path: Path | str) -> PaletteImporter:
    """Detect the palette importer for a file by extension and contents."""
    return _detect(_IMPORTERS, input_path, format_label="palette")


def detect_filament_importer(input_path: Path | str) -> FilamentImporter:
    """Detect the filament importer for a file by extension and contents."""
    return _detect(_FILAMENT_IMPORTERS, input_path, format_label="filament")


def import_palette(
    input_path: Path | str,
    *,
    format_name: str | None = None,
) -> PaletteExportData:
    """Import palette transfer data using explicit or automatic selection."""
    importer = (
        detect_importer(input_path)
        if format_name is None
        else get_importer(format_name)
    )
    return importer.import_palette(input_path)


def import_filaments(
    input_path: Path | str,
    *,
    format_name: str | None = None,
) -> FilamentExportData:
    """Import filament transfer data using explicit or automatic selection."""
    importer = (
        detect_filament_importer(input_path)
        if format_name is None
        else get_filament_importer(format_name)
    )
    return importer.import_filaments(input_path)


__all__ = [
    "detect_filament_importer",
    "detect_importer",
    "get_filament_importer",
    "get_filament_importers_for_extension",
    "get_importer",
    "get_importers_for_extension",
    "import_filaments",
    "import_palette",
    "list_filament_import_formats",
    "list_import_formats",
    "register_filament_importer",
    "register_importer",
]

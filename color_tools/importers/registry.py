"""
Palette importer registry.

Importers register themselves through @register_importer. The registry stores
importer classes rather than instances so each request receives a fresh,
stateless importer.

The registry also provides extension-based candidate lookup and file-content
detection. This is necessary because some palette formats share extensions.

For example:

    JASC PAL -> .pal
    RIFF PAL -> .pal

Those importers can both register the ``pal`` extension while implementing
different can_import() signature checks.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from color_tools.exporters.palette_export_data import PaletteExportData
    from color_tools.importers.base import PaletteImporter


_IMPORTERS: dict[
    str,
    type[PaletteImporter],
] = {}


def register_importer(
    cls: type[PaletteImporter],
) -> type[PaletteImporter]:
    """
    Register a palette importer class.

    The importer is instantiated once during registration to retrieve its
    metadata. The class itself is stored and fresh instances are created on
    demand.

    Args:
        cls:
            PaletteImporter subclass.

    Returns:
        The original class, allowing use as a decorator.

    Raises:
        ValueError:
            If another importer already uses the same metadata name.

    Example:
        >>> @register_importer
        ... class ExampleImporter(PaletteImporter):
        ...     ...
    """
    instance = cls()
    name = instance.metadata.name

    if name in _IMPORTERS:
        raise ValueError(
            f"Importer '{name}' is already registered. "
            "Each importer must have a unique name."
        )

    _IMPORTERS[name] = cls

    return cls


def get_importer(
    format_name: str,
) -> PaletteImporter:
    """
    Create an importer by registered format name.

    Args:
        format_name:
            Importer metadata name.

    Returns:
        Fresh importer instance.

    Raises:
        ValueError:
            If the format is not registered.
    """
    if format_name not in _IMPORTERS:
        available = ", ".join(
            sorted(
                _IMPORTERS
            )
        )

        raise ValueError(
            f"Unknown import format: '{format_name}'. "
            f"Available formats: {available}"
        )

    return _IMPORTERS[
        format_name
    ]()


def list_import_formats(
    *,
    available_only: bool = True,
) -> dict[str, str]:
    """
    List registered palette import formats.

    Args:
        available_only:
            Exclude importers whose optional dependencies are unavailable.

    Returns:
        Mapping of importer name to human-readable description.
    """
    result: dict[str, str] = {}

    for name, importer_class in _IMPORTERS.items():
        importer = importer_class()

        if (
            available_only
            and not importer.is_available
        ):
            continue

        result[name] = (
            importer.metadata.description
        )

    return result


def get_importers_for_extension(
    extension: str,
    *,
    available_only: bool = True,
) -> list[PaletteImporter]:
    """
    Return importers registered for a file extension.

    More than one importer may be returned because extensions are not unique.

    Args:
        extension:
            Extension with or without a leading dot.

        available_only:
            Exclude importers with unavailable dependencies.

    Returns:
        Fresh importer instances matching the extension.
    """
    normalized = (
        extension
        .removeprefix(".")
        .lower()
    )

    result: list[PaletteImporter] = []

    for importer_class in _IMPORTERS.values():
        importer = importer_class()

        if (
            available_only
            and not importer.is_available
        ):
            continue

        extensions = {
            item.lower()
            for item
            in importer.metadata.file_extensions
        }

        if normalized in extensions:
            result.append(
                importer
            )

    return result


def detect_importer(
    input_path: Path | str,
) -> PaletteImporter:
    """
    Detect the importer for a palette file.

    Detection proceeds in two stages:

        1. Select importers registered for the file extension.
        2. Ask each candidate to inspect the file using can_import().

    This allows formats that share extensions to distinguish themselves using
    file signatures or headers.

    Args:
        input_path:
            Palette file to inspect.

    Returns:
        Matching importer.

    Raises:
        FileNotFoundError:
            If the file does not exist.

        ValueError:
            If there are no candidate importers, no candidate recognizes the
            file, or multiple candidates recognize it.
    """
    path = Path(
        input_path
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Palette file does not exist: {path}"
        )

    candidates = get_importers_for_extension(
        path.suffix,
    )

    if not candidates:
        extension = (
            path.suffix
            or "<none>"
        )

        raise ValueError(
            "No palette importer is registered for "
            f"extension '{extension}'"
        )

    matches = [
        importer
        for importer in candidates
        if importer.can_import(
            path
        )
    ]

    if len(matches) == 1:
        return matches[0]

    candidate_names = ", ".join(
        importer.metadata.name
        for importer in candidates
    )

    if not matches:
        raise ValueError(
            f"Unable to determine palette format for '{path}'. "
            f"Candidate importers: {candidate_names}"
        )

    match_names = ", ".join(
        importer.metadata.name
        for importer in matches
    )

    raise ValueError(
        f"Palette format for '{path}' is ambiguous. "
        f"Matching importers: {match_names}"
    )


def import_palette(
    input_path: Path | str,
    *,
    format_name: str | None = None,
) -> PaletteExportData:
    """
    Import a palette using explicit or automatic format selection.

    Args:
        input_path:
            Palette file to import.

        format_name:
            Optional explicit importer name. If omitted, the registry attempts
            to detect the format from extension and file contents.

    Returns:
        Imported PaletteExportData.

    Example:
        Automatic detection:

        >>> palette = import_palette("palette.gpl")

        Explicit format:

        >>> palette = import_palette(
        ...     "palette.pal",
        ...     format_name="jasc_pal",
        ... )
    """
    if format_name is None:
        importer = detect_importer(
            input_path
        )

    else:
        importer = get_importer(
            format_name
        )

    return importer.import_palette(
        input_path
    )
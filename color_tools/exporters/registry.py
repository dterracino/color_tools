"""
Exporter registry and discovery utilities.

This module owns the global exporter registry used by the palette exporter
plugin system.

Concrete exporters register themselves with the @register_exporter decorator.
The registry stores exporter classes rather than instances and creates fresh
instances on demand.

Keeping registry behavior in this module avoids circular imports between
``color_tools.exporters`` and individual exporter modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from color_tools.exporters.base import PaletteExporter


# Maps exporter metadata.name -> exporter class.
_EXPORTERS: dict[str, type[PaletteExporter]] = {}

# Legacy or ambiguous identifiers mapped to their canonical registry names.
_EXPORTER_ALIASES = {
    "pal": "jasc_pal",
}


def register_exporter(
    cls: type[PaletteExporter],
) -> type[PaletteExporter]:
    """
    Register an exporter class.

    The exporter is instantiated once during registration so its metadata can
    be inspected. The class itself is stored in the registry and fresh exporter
    instances are created when requested with :func:`get_exporter`.

    Args:
        cls:
            Exporter class to register.

    Returns:
        The same exporter class, unchanged, allowing this function to be used
        as a class decorator.

    Raises:
        ValueError:
            If another exporter is already registered with the same metadata
            name.

    Example:
        >>> from color_tools.exporters.base import (
        ...     ExporterMetadata,
        ...     PaletteExporter,
        ... )
        >>> from color_tools.exporters.registry import register_exporter
        >>>
        >>> @register_exporter
        ... class MyExporter(PaletteExporter):
        ...     @property
        ...     def metadata(self) -> ExporterMetadata:
        ...         return ExporterMetadata(
        ...             name="myformat",
        ...             description="My custom format",
        ...             file_extension="txt",
        ...             supports_colors=True,
        ...             supports_filaments=False,
        ...         )
    """
    instance = cls()
    name = instance.metadata.name

    if name in _EXPORTERS:
        raise ValueError(
            f"Exporter '{name}' is already registered. "
            "Each exporter must have a unique name."
        )

    _EXPORTERS[name] = cls

    return cls


def get_exporter(format_name: str) -> PaletteExporter:
    """
    Create an exporter instance by format name.

    Args:
        format_name:
            Exporter identifier from ``ExporterMetadata.name``.

    Returns:
        A fresh instance of the requested exporter.

    Raises:
        ValueError:
            If the requested format is not registered.

    Example:
        >>> exporter = get_exporter("json")
        >>> print(exporter.metadata.description)
        JSON format (raw data, backup/restore)
    """
    canonical_name = _EXPORTER_ALIASES.get(
        format_name,
        format_name,
    )

    try:
        exporter_class = _EXPORTERS[canonical_name]
    except KeyError:
        available = ", ".join(sorted(_EXPORTERS))

        raise ValueError(
            f"Unknown export format: '{format_name}'. "
            f"Available formats: {available}"
        ) from None

    return exporter_class()


def list_export_formats(
    data_type: str = "both",
    *,
    available_only: bool = True,
) -> dict[str, str]:
    """
    List registered export formats.

    Formats may be filtered by the type of data they support and, optionally,
    by whether all of their required dependencies are currently installed.

    Args:
        data_type:
            Data type to filter by:

            - ``"colors"``
            - ``"filaments"``
            - ``"both"``

            ``"both"`` means exporters supporting either type, preserving the
            behavior of the previous exporter registry.

        available_only:
            When True, omit exporters whose optional dependencies are missing.
            When False, include all registered exporters that match
            ``data_type``.

    Returns:
        Dictionary mapping exporter name to human-readable description.

    Raises:
        ValueError:
            If ``data_type`` is not one of the supported values.
    """
    if data_type not in {"colors", "filaments", "both"}:
        raise ValueError(
            "data_type must be 'colors', 'filaments', or 'both'"
        )

    result: dict[str, str] = {}

    for name, exporter_class in _EXPORTERS.items():
        exporter = exporter_class()
        metadata = exporter.metadata

        if data_type == "colors":
            applies = metadata.supports_colors
        elif data_type == "filaments":
            applies = metadata.supports_filaments
        else:
            applies = (
                metadata.supports_colors
                or metadata.supports_filaments
            )

        if not applies:
            continue

        if available_only and not exporter.is_available:
            continue

        result[name] = metadata.description

    return result


def get_export_formats_dict() -> dict[str, dict[str, str | bool]]:
    """
    Return export format metadata in the legacy EXPORT_FORMATS structure.

    This preserves compatibility with code that previously consumed the
    dictionary maintained by ``export.py``.

    Returns:
        Dictionary mapping exporter name to metadata containing:

        - ``description``
        - ``file_extension``
        - ``applies_to``
        - ``available``

    Example:
        >>> formats = get_export_formats_dict()
        >>> formats["json"]["applies_to"]
        'both'
    """
    result: dict[str, dict[str, str | bool]] = {}

    for name, exporter_class in _EXPORTERS.items():
        exporter = exporter_class()
        metadata = exporter.metadata

        if metadata.supports_colors and metadata.supports_filaments:
            applies_to = "both"
        elif metadata.supports_colors:
            applies_to = "colors"
        elif metadata.supports_filaments:
            applies_to = "filaments"
        else:
            applies_to = "none"

        result[name] = {
            "description": metadata.description,
            "file_extension": metadata.file_extension,
            "applies_to": applies_to,
            "available": exporter.is_available,
        }

    return result
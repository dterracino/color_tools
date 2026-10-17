"""Metadata-bearing filament transfer model."""

from __future__ import annotations

from dataclasses import dataclass, field

from color_tools.exporters.filament_metadata import FilamentMetadata
from color_tools.filament_palette import FilamentRecord


@dataclass(slots=True)
class FilamentExportData:
    """Ordered filaments and metadata shared by importers and exporters.

    The model is format-neutral. Importers can return it for inspection or
    format conversion, while exporters that do not use collection metadata
    can consume its :attr:`filaments` list through the standard fallback.

    Attributes:
        filaments: Ordered filament records.
        metadata: Metadata applying to the complete filament collection.
    """

    filaments: list[FilamentRecord]
    metadata: FilamentMetadata = field(default_factory=FilamentMetadata)

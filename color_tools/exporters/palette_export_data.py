"""
Palette export data model.

PaletteExportData provides exporters with both palette colors and optional
palette-level metadata while remaining independent from the full Palette
implementation.

This keeps exporters coupled only to the data they require rather than to the
complete palette model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from color_tools.exporters.palette_metadata import PaletteMetadata

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord


@dataclass(slots=True)
class PaletteExportData:
    """
    Palette data supplied to palette-aware exporters.

    Attributes:
        colors:
            Ordered palette colors.

        metadata:
            Metadata applying to the entire palette.

    Example:
        >>> from color_tools.exporters.palette_metadata import PaletteMetadata
        >>>
        >>> data = PaletteExportData(
        ...     colors=colors,
        ...     metadata=PaletteMetadata(
        ...         name="Warm Autumn",
        ...         author="Dave",
        ...     ),
        ... )
    """

    colors: list[ColorRecord]
    metadata: PaletteMetadata = field(
        default_factory=PaletteMetadata
    )
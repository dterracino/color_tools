"""
Palette-level metadata.

PaletteMetadata stores descriptive information that applies to an entire
palette rather than to individual colors.

The model intentionally contains only broadly useful metadata. Format-specific
features such as swatch groups, ICC profiles, spot colors, and color-space
information should be modeled separately when those capabilities are added.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PaletteMetadata:
    """
    Descriptive metadata associated with a palette.

    Attributes:
        name:
            Human-readable palette name.

        author:
            Palette creator or author.

        description:
            Optional longer description of the palette.

        columns:
            Preferred display column count when supported by the target
            format. A value of None means no preference is specified.

            A value of 0 may have format-specific meaning, such as allowing
            the consuming application to determine the layout.

        tags:
            Searchable or descriptive palette tags.

        properties:
            Additional application-specific metadata that does not yet warrant
            a dedicated field.

    Example:
        >>> metadata = PaletteMetadata(
        ...     name="Warm Autumn",
        ...     author="Dave",
        ...     description="Muted warm colors for autumn artwork.",
        ...     columns=5,
        ...     tags=("warm", "autumn", "muted"),
        ... )
    """

    name: str = ""
    author: str = ""
    description: str = ""
    columns: int | None = None
    tags: tuple[str, ...] = ()
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize and validate metadata."""
        self.name = self.name.strip()
        self.author = self.author.strip()
        self.description = self.description.strip()

        if self.columns is not None and self.columns < 0:
            raise ValueError(
                "Palette column count must be zero or greater"
            )

        self.tags = tuple(
            tag.strip()
            for tag in self.tags
            if tag.strip()
        )

    @property
    def has_metadata(self) -> bool:
        """
        Return whether any meaningful palette metadata is present.

        Returns:
            True when at least one metadata field contains information.
        """
        return bool(
            self.name
            or self.author
            or self.description
            or self.columns is not None
            or self.tags
            or self.properties
        )
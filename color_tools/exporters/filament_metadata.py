"""Collection-level metadata for filament import and export."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _empty_properties() -> dict[str, Any]:
    """Create an explicitly typed empty metadata property mapping."""
    return {}


@dataclass(slots=True)
class FilamentMetadata:
    """Descriptive and inventory metadata for a filament collection.

    Ownership and external-format identifiers belong to collection metadata,
    not to :class:`~color_tools.filament_palette.FilamentRecord`, because they
    describe user state or an interchange format rather than the filament
    product itself.

    Attributes:
        name: Human-readable collection name.
        author: Collection creator or author.
        description: Optional longer collection description.
        tags: Searchable or descriptive collection tags.
        owned_filament_ids: Color Tools filament IDs marked as owned.
        properties: Additional format-specific metadata needed for a
            loss-aware round trip, such as external identifier mappings.
    """

    name: str = ""
    author: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()
    owned_filament_ids: tuple[str, ...] = ()
    properties: dict[str, Any] = field(default_factory=_empty_properties)

    def __post_init__(self) -> None:
        """Normalize collection metadata text and identifiers."""
        self.name = self.name.strip()
        self.author = self.author.strip()
        self.description = self.description.strip()
        self.tags = tuple(tag.strip() for tag in self.tags if tag.strip())
        self.owned_filament_ids = tuple(
            filament_id.strip()
            for filament_id in self.owned_filament_ids
            if filament_id.strip()
        )

    @property
    def has_metadata(self) -> bool:
        """Return whether the collection contains meaningful metadata."""
        return bool(
            self.name
            or self.author
            or self.description
            or self.tags
            or self.owned_filament_ids
            or self.properties
        )

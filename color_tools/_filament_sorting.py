"""Shared deterministic ordering for filament records."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from color_tools.filament_palette import FilamentRecord


def filament_sort_key(
    record: FilamentRecord,
) -> tuple[str, str, str, str, str]:
    """Return the canonical case-insensitive filament display order."""
    return (
        record.maker.casefold(),
        record.type.casefold(),
        (record.finish or "").casefold(),
        record.color.casefold(),
        record.id.casefold(),
    )


__all__ = ["filament_sort_key"]

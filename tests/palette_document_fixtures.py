"""Shared builders for palette-document test fixtures."""

from __future__ import annotations

from collections.abc import Sequence


def palette_document(
    palette_id: str,
    colors: Sequence[object],
    *,
    name: str = "Test Palette",
    description: str = "A palette used by automated tests.",
) -> dict[str, object]:
    """Build a minimal schema-version-1 indexed palette document."""
    return {
        "schema_version": 1,
        "metadata": {
            "id": palette_id,
            "name": name,
            "description": description,
        },
        "palette": {
            "type": "indexed",
            "colors": list(colors),
        },
    }

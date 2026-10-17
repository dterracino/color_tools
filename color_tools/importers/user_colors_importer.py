"""Importer for Color Tools ``user-colors.json`` files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.importers.base import ImporterMetadata, PaletteImporter
from color_tools.importers.registry import register_importer
from color_tools.user_color_data import parse_user_color_records


@register_importer
class UserColorsImporter(PaletteImporter):
    """Import the strict, minimal Color Tools user-color schema."""

    @property
    def metadata(self) -> ImporterMetadata:
        """Return importer format metadata."""
        return ImporterMetadata(
            name="user_colors",
            description="Color Tools user color data",
            file_extensions=("json",),
        )

    def _can_import_impl(self, input_path: Path) -> bool:
        """Recognize a root array containing only name/hex objects."""
        try:
            data: object = json.loads(input_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return False

        if not isinstance(data, list):
            return False
        items = cast(list[object], data)
        return all(
            isinstance(item, dict)
            and {"name", "hex"}.issubset(
                set(cast(dict[object, object], item))
            )
            for item in items
        )

    def _import_palette_impl(self, input_path: Path) -> PaletteExportData:
        """Parse user colors and calculate every derived color value."""
        try:
            data: object = json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON in user color file {input_path}: {error}") from error

        if not isinstance(data, list):
            raise ValueError(
                f"Expected array of colors at root level in {input_path}"
            )

        return PaletteExportData(
            colors=parse_user_color_records(cast(list[object], data), input_path),
        )


__all__ = ["UserColorsImporter"]

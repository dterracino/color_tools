"""Importer for Color Tools ``user-filaments.json`` files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from color_tools._filament_data import parse_filament_records
from color_tools.exporters.filament_export_data import FilamentExportData
from color_tools.importers.base import ImporterMetadata
from color_tools.importers.filament_importer import FilamentImporter
from color_tools.importers.registry import register_filament_importer


@register_filament_importer
class UserFilamentsImporter(FilamentImporter):
    """Import the strict Color Tools user-filament schema."""

    @property
    def metadata(self) -> ImporterMetadata:
        """Return importer format metadata."""
        return ImporterMetadata(
            name="user_filaments",
            description="Color Tools user filament data",
            file_extensions=("json",),
        )

    def _can_import_impl(self, input_path: Path) -> bool:
        """Recognize a root array containing required filament fields."""
        try:
            data: object = json.loads(input_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return False
        if not isinstance(data, list):
            return False
        required = {"id", "maker", "type", "color", "hex"}
        return all(
            isinstance(item, dict)
            and required.issubset(set(cast(dict[object, object], item)))
            for item in cast(list[object], data)
        )

    def _import_filaments_impl(self, input_path: Path) -> FilamentExportData:
        """Parse a user-filament collection into transfer data."""
        try:
            data: object = json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid JSON in user filament file {input_path}: {error}"
            ) from error
        if not isinstance(data, list):
            raise ValueError(
                f"Expected array of filaments at root level in {input_path}"
            )
        return FilamentExportData(
            filaments=parse_filament_records(
                cast(list[object], data),
                input_path,
            )
        )


__all__ = ["UserFilamentsImporter"]

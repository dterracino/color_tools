"""Importer for HueForge filament-library JSON files."""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import cast
from uuid import UUID

from color_tools._color_utils import parse_hex_colors
from color_tools.conversions import rgb_to_hex
from color_tools.exporters.filament_export_data import FilamentExportData
from color_tools.exporters.filament_metadata import FilamentMetadata
from color_tools.filament_id import generate_filament_id, next_available_filament_id
from color_tools.filament_palette import FilamentRecord
from color_tools.importers.base import ImporterMetadata
from color_tools.importers.filament_importer import FilamentImporter
from color_tools.importers.registry import register_filament_importer


_REQUIRED_FIELDS = frozenset(
    {"Brand", "Color", "Name", "Owned", "Transmissivity", "Type", "uuid"}
)
_OPTIONAL_FIELDS = frozenset(
    {"Secondary_Color", "Secondary_Strength", "Secondary_Type", "Tags"}
)
_PERSONAL_FIELDS = frozenset({"exported_at", "format", "version"})


def _required_text(record: dict[str, object], field_name: str) -> str:
    """Return one non-empty HueForge text field."""
    value = record.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _transmissivity(record: dict[str, object]) -> float:
    """Return a finite, non-negative HueForge transmissivity value."""
    value = record.get("Transmissivity")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Transmissivity must be a non-negative finite number")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError("Transmissivity must be a non-negative finite number")
    return result


def _validate_uuid(value: object) -> str:
    """Validate and normalize a HueForge UUID without persisting it."""
    if not isinstance(value, str):
        raise ValueError("uuid must be a braced UUID string")
    if not value.startswith("{") or not value.endswith("}"):
        raise ValueError("uuid must be a braced UUID string")
    try:
        parsed = UUID(value[1:-1])
    except ValueError as error:
        raise ValueError("uuid must be a valid braced UUID string") from error
    return str(parsed)


def _personal_properties(document: dict[str, object]) -> dict[str, object]:
    """Validate and return HueForge personal-library envelope metadata."""
    present = _PERSONAL_FIELDS & document.keys()
    if not present:
        return {"hueforge_format": "filament_library"}
    missing = _PERSONAL_FIELDS - document.keys()
    if missing:
        raise ValueError(
            "HueForge personal library is missing top-level field(s): "
            + ", ".join(sorted(missing))
        )
    if document["format"] != "hueforge_personal_library":
        raise ValueError("Unsupported HueForge personal-library format")
    version = document["version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        raise ValueError("Unsupported HueForge personal-library version")
    exported_at = document["exported_at"]
    if not isinstance(exported_at, str):
        raise ValueError("exported_at must be an ISO 8601 string")
    try:
        datetime.fromisoformat(exported_at)
    except ValueError as error:
        raise ValueError("exported_at must be an ISO 8601 string") from error
    return {
        "hueforge_format": "hueforge_personal_library",
        "hueforge_version": version,
        "hueforge_exported_at": exported_at,
    }


@register_filament_importer
class HueForgeImporter(FilamentImporter):
    """Import HueForge filament and personal-library JSON files.

    HueForge secondary-color fields and tags are intentionally ignored because
    their semantics do not map reliably to a Color Tools filament record.
    Unconfigured ``IMAGE`` entries are skipped. Ownership is retained in
    :class:`~color_tools.exporters.filament_metadata.FilamentMetadata` for a
    later, independent owned-filament operation.
    """

    @property
    def metadata(self) -> ImporterMetadata:
        """Return importer format metadata."""
        return ImporterMetadata(
            name="hueforge",
            description="HueForge filament or personal library",
            file_extensions=("json",),
        )

    def _can_import_impl(self, input_path: Path) -> bool:
        """Recognize a HueForge object containing a ``Filaments`` array."""
        try:
            document: object = json.loads(input_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return False
        return isinstance(document, dict) and isinstance(
            cast(dict[object, object], document).get("Filaments"), list
        )

    def _import_filaments_impl(self, input_path: Path) -> FilamentExportData:
        """Parse and validate a HueForge library into transfer data."""
        try:
            document_value: object = json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON in HueForge file {input_path}: {error}") from error
        if not isinstance(document_value, dict):
            raise ValueError(f"Expected HueForge object at root level in {input_path}")
        document = cast(dict[str, object], document_value)
        unknown_top_level = document.keys() - ({"Filaments"} | _PERSONAL_FIELDS)
        if unknown_top_level:
            raise ValueError(
                "Unknown HueForge top-level field(s): "
                + ", ".join(sorted(unknown_top_level))
            )
        properties = _personal_properties(document)
        raw_filaments = document.get("Filaments")
        if not isinstance(raw_filaments, list):
            raise ValueError("HueForge Filaments must be an array")

        records: list[FilamentRecord] = []
        owned_ids: list[str] = []
        reserved_ids: set[str] = set()
        seen_uuids: set[str] = set()
        skipped_indices: list[int] = []
        for index, item in enumerate(cast(list[object], raw_filaments)):
            try:
                record, owned, external_uuid = self._parse_record(
                    item,
                    input_path,
                    reserved_ids,
                )
            except _SkipHueForgeRecord:
                skipped_indices.append(index)
                continue
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid HueForge filament at index {index} in {input_path}: {error}"
                ) from error
            records.append(record)
            reserved_ids.add(record.id)
            if external_uuid in seen_uuids:
                raise ValueError(
                    f"Invalid HueForge filament at index {index} in {input_path}: "
                    f"duplicate uuid {{{external_uuid}}}"
                )
            seen_uuids.add(external_uuid)
            if owned:
                owned_ids.append(record.id)

        properties["skipped_error_filament_indices"] = tuple(skipped_indices)
        return FilamentExportData(
            filaments=records,
            metadata=FilamentMetadata(
                name=input_path.stem,
                owned_filament_ids=tuple(owned_ids),
                properties=properties,
            ),
        )

    @staticmethod
    def _parse_record(
        value: object,
        input_path: Path,
        reserved_ids: set[str],
    ) -> tuple[FilamentRecord, bool, str]:
        """Parse one HueForge filament or identify its error placeholder."""
        if not isinstance(value, dict):
            raise ValueError("record must be an object")
        record = cast(dict[str, object], value)
        if record.get("Brand") == "" and record.get("Type") == "IMAGE":
            raise _SkipHueForgeRecord
        missing = _REQUIRED_FIELDS - record.keys()
        if missing:
            raise ValueError(f"missing required field(s): {', '.join(sorted(missing))}")
        unknown = record.keys() - (_REQUIRED_FIELDS | _OPTIONAL_FIELDS)
        if unknown:
            raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")

        maker = _required_text(record, "Brand")
        type_name = _required_text(record, "Type")
        color = _required_text(record, "Name")
        hex_text = _required_text(record, "Color")
        components = parse_hex_colors(hex_text)
        if len(components) != 1:
            raise ValueError("Color must contain exactly one hex color")
        owned = record.get("Owned")
        if not isinstance(owned, bool):
            raise ValueError("Owned must be a boolean")
        external_uuid = _validate_uuid(record.get("uuid"))
        base_id = generate_filament_id(maker, type_name, None, color)
        filament_id = next_available_filament_id(base_id, reserved_ids)
        return (
            FilamentRecord(
                id=filament_id,
                maker=maker,
                type=type_name,
                finish=None,
                color=color,
                hex=rgb_to_hex(components[0]),
                td_value=_transmissivity(record),
                source=input_path.name,
            ),
            owned,
            external_uuid,
        )


class _SkipHueForgeRecord(Exception):
    """Signal that a HueForge error placeholder must be omitted."""


__all__ = ["HueForgeImporter"]

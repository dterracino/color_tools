"""Canonical JSON schema handling shared by filament loaders and exporters."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, cast

from color_tools.conversions import rgb_to_hex
from color_tools.filament_id import validate_filament_id
from color_tools.filament_load_report import FilamentLoadEvent

if TYPE_CHECKING:
    from color_tools.filament_palette import FilamentRecord


_FILAMENT_REQUIRED_FIELDS = frozenset({"id", "maker", "type", "color", "hex"})
_FILAMENT_OPTIONAL_FIELDS = frozenset({"finish", "td_value", "other_names"})


def _required_record_text(record: dict[str, object], field_name: str) -> str:
    """Return a required non-empty field without surrounding whitespace."""
    value = record.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{field_name} must not have surrounding whitespace")
    return value


def _optional_record_text(
    record: dict[str, object],
    field_name: str,
) -> str | None:
    """Return an optional non-empty field without surrounding whitespace."""
    value = record.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be null or a non-empty string")
    if value != value.strip():
        raise ValueError(f"{field_name} must not have surrounding whitespace")
    return value


def _optional_td_value(record: dict[str, object]) -> float | None:
    """Return a validated optional transmission-distance value."""
    value = record.get("td_value")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("td_value must be null or a non-negative finite number")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError("td_value must be null or a non-negative finite number")
    return result


def _optional_other_names(record: dict[str, object]) -> list[str] | None:
    """Return validated, case-insensitively unique alternative names."""
    value = record.get("other_names")
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("other_names must be null or an array of non-empty strings")
    names: list[str] = []
    seen: set[str] = set()
    for name in cast(list[object], value):
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ValueError(
                "other_names must contain non-empty strings without "
                "surrounding whitespace"
            )
        key = name.casefold()
        if key in seen:
            raise ValueError(f"other_names contains duplicate value {name!r}")
        seen.add(key)
        names.append(name)
    return names


def parse_filament_records(
    data: Sequence[object],
    source_file: str | Path,
) -> list[FilamentRecord]:
    """Validate filament JSON objects and build records with unique IDs."""
    from color_tools.filament_palette import FilamentRecord

    records: list[FilamentRecord] = []
    source = str(source_file)
    source_filename = Path(source).name
    seen_ids: set[str] = set()
    allowed_fields = _FILAMENT_REQUIRED_FIELDS | _FILAMENT_OPTIONAL_FIELDS
    for index, value in enumerate(data):
        try:
            if not isinstance(value, dict):
                raise ValueError("record must be an object")
            record = cast(dict[str, object], value)
            if "hex2" in record:
                raise ValueError("hex2 was removed; put all components in hex")
            missing = _FILAMENT_REQUIRED_FIELDS - record.keys()
            if missing:
                raise ValueError(
                    f"missing required field(s): {', '.join(sorted(missing))}"
                )
            unknown = record.keys() - allowed_fields
            if unknown:
                raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")
            record_id = validate_filament_id(_required_record_text(record, "id"))
            if record_id in seen_ids:
                raise ValueError(f"duplicate id {record_id!r}")
            seen_ids.add(record_id)
            parsed = FilamentRecord(
                id=record_id,
                maker=_required_record_text(record, "maker"),
                type=_required_record_text(record, "type"),
                finish=_optional_record_text(record, "finish"),
                color=_required_record_text(record, "color"),
                hex=_required_record_text(record, "hex"),
                td_value=_optional_td_value(record),
                other_names=_optional_other_names(record),
                source=source_filename,
            )
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Invalid filament data at index {index} in {source}: {error}"
            ) from error
        records.append(parsed)
    return records


def load_filament_records_file(path: Path | str) -> list[FilamentRecord]:
    """Load and validate one core- or user-schema filament JSON file."""
    source_path = Path(path)
    with source_path.open("r", encoding="utf-8") as file:
        data = cast(object, json.load(file))
    if not isinstance(data, list):
        raise ValueError(
            f"Expected array of filaments at root level in {source_path}"
        )
    return parse_filament_records(cast(list[object], data), source_path)


def merge_user_filaments(
    system_records: list[FilamentRecord],
    user_records: list[FilamentRecord],
) -> tuple[list[FilamentRecord], tuple[FilamentLoadEvent, ...]]:
    """Merge user records by stable ID, preserving replacement positions."""
    merged = list(system_records)
    indices = {record.id: index for index, record in enumerate(merged)}
    events: list[FilamentLoadEvent] = []
    for record in user_records:
        replacement_index = indices.get(record.id)
        if replacement_index is None:
            indices[record.id] = len(merged)
            merged.append(record)
            events.append(FilamentLoadEvent("added", record))
        else:
            replaced = merged[replacement_index]
            merged[replacement_index] = record
            events.append(FilamentLoadEvent("overridden", record, replaced))
    return merged, tuple(events)


def serialize_filament_record(record: FilamentRecord) -> dict[str, object]:
    """Serialize authoritative filament fields with canonical compound hex."""
    normalized_hex = "-".join(
        rgb_to_hex(component) for component in record.rgb_components
    )
    return {
        "id": record.id,
        "maker": record.maker,
        "type": record.type,
        "finish": record.finish,
        "color": record.color,
        "hex": normalized_hex,
        "td_value": record.td_value,
        "other_names": (
            list(record.other_names) if record.other_names is not None else None
        ),
    }


def serialize_filament_records(
    records: Sequence[FilamentRecord],
) -> list[dict[str, object]]:
    """Serialize an ordered collection using only user-data source fields."""
    return [serialize_filament_record(record) for record in records]


__all__ = [
    "load_filament_records_file",
    "merge_user_filaments",
    "parse_filament_records",
    "serialize_filament_record",
    "serialize_filament_records",
]

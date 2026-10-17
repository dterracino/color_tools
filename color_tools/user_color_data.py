"""Canonical parsing, merging, and serialization for user color records."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from color_tools._palette_utils import normalize_color_name
from color_tools.color_load_report import ColorLoadEvent
from color_tools.conversions import rgb_to_hex

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord


def parse_user_color_records(
    data: Sequence[object],
    source_file: str | Path,
) -> list[ColorRecord]:
    """Parse the strict ``name``/``hex`` user-color schema.

    Derived color-space values are always recalculated by :class:`ColorRecord`.
    Extra fields are rejected so user files cannot supply stale derived data.
    """
    from color_tools.palette import ColorRecord

    records: list[ColorRecord] = []
    expected_fields = {"name", "hex"}
    source = str(source_file)

    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(
                f"Invalid color data at index {index} in {source}: "
                "expected an object"
            )

        fields = cast(dict[object, object], item)
        if not all(isinstance(key, str) for key in fields):
            raise ValueError(
                f"Invalid color data at index {index} in {source}: "
                "field names must be strings"
            )

        actual_fields = cast(set[str], set(fields))
        unexpected_fields = actual_fields - expected_fields
        if unexpected_fields:
            formatted = ", ".join(sorted(unexpected_fields))
            raise ValueError(
                f"Invalid color data at index {index} in {source}: "
                f"unexpected field(s): {formatted}; user colors accept only "
                "'name' and 'hex' because derived values are calculated"
            )

        name = fields.get("name")
        hex_code = fields.get("hex")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"Missing or invalid 'name' in color at index {index} in {source}"
            )
        if not isinstance(hex_code, str):
            raise ValueError(
                f"Missing or invalid 'hex' in color at index {index} in {source}"
            )

        try:
            records.append(
                ColorRecord.from_hex(
                    hex_code,
                    name=name.strip(),
                    source=Path(source).name,
                )
            )
        except ValueError as error:
            raise ValueError(
                f"Invalid color data at index {index} in {source}: {error}"
            ) from error

    return records


def merge_user_color_records(
    system_records: list[ColorRecord],
    user_records: list[ColorRecord],
) -> tuple[list[ColorRecord], tuple[ColorLoadEvent, ...]]:
    """Merge user colors sequentially by name while preserving RGB uniqueness."""
    merged = list(system_records)
    events: list[ColorLoadEvent] = []
    seen_user_names: set[str] = set()

    for index, user_record in enumerate(user_records):
        name_key = normalize_color_name(user_record.name)
        if name_key in seen_user_names:
            raise ValueError(
                f"Duplicate user color name '{user_record.name}' at index {index} "
                f"in {user_record.source}"
            )
        seen_user_names.add(name_key)

        replacement_index = next(
            (
                record_index
                for record_index, record in enumerate(merged)
                if normalize_color_name(record.name) == name_key
            ),
            None,
        )
        conflicting_record = next(
            (
                record
                for record_index, record in enumerate(merged)
                if record.rgb == user_record.rgb
                and record_index != replacement_index
            ),
            None,
        )
        if conflicting_record is not None:
            raise ValueError(
                f"User color '{user_record.name}' ({user_record.hex}) in "
                f"{user_record.source} conflicts with existing color "
                f"'{conflicting_record.name}' ({conflicting_record.hex}) from "
                f"{conflicting_record.source}"
            )

        if replacement_index is None:
            merged.append(user_record)
            events.append(ColorLoadEvent("added", user_record))
        else:
            replaced_record = merged[replacement_index]
            merged[replacement_index] = user_record
            events.append(ColorLoadEvent("overridden", user_record, replaced_record))

    return merged, tuple(events)


def serialize_user_color_records(
    records: Sequence[ColorRecord],
) -> list[dict[str, str]]:
    """Serialize only authoritative user fields using canonical hex output."""
    return [
        {"name": record.name.strip(), "hex": rgb_to_hex(record.rgb)}
        for record in records
    ]


__all__ = [
    "merge_user_color_records",
    "parse_user_color_records",
    "serialize_user_color_records",
]

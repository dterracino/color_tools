"""Validation helpers for versioned palette data documents."""

from __future__ import annotations

from typing import cast


PALETTE_SCHEMA_VERSION = 1


def parse_indexed_palette_document(
    data: object,
    *,
    expected_id: str,
    source_file: str,
) -> list[object]:
    """Validate a palette document and return its indexed color records."""
    document = _require_object(data, "palette document", source_file)

    schema_version = document.get("schema_version")
    if type(schema_version) is not int:
        raise ValueError(
            f"Missing or invalid 'schema_version' in {source_file}: expected integer"
        )
    if schema_version != PALETTE_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported palette schema version {schema_version} in {source_file}; "
            f"expected {PALETTE_SCHEMA_VERSION}"
        )

    metadata = _require_object(document.get("metadata"), "metadata", source_file)
    _validate_metadata(metadata, expected_id=expected_id, source_file=source_file)

    palette = _require_object(document.get("palette"), "palette", source_file)
    palette_type = palette.get("type")
    if palette_type != "indexed":
        raise ValueError(
            f"Unsupported palette type {palette_type!r} in {source_file}; "
            "expected 'indexed'"
        )

    colors = palette.get("colors")
    if not isinstance(colors, list):
        raise ValueError(
            f"Missing or invalid 'palette.colors' in {source_file}: expected array"
        )
    return cast(list[object], colors)


def _require_object(
    value: object,
    field_name: str,
    source_file: str,
) -> dict[str, object]:
    """Return a string-keyed JSON object or raise a focused schema error."""
    if not isinstance(value, dict):
        raise ValueError(
            f"Missing or invalid '{field_name}' in {source_file}: expected object"
        )
    raw_object = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in raw_object):
        raise ValueError(
            f"Missing or invalid '{field_name}' in {source_file}: expected object"
        )
    return cast(dict[str, object], raw_object)


def _validate_metadata(
    metadata: dict[str, object],
    *,
    expected_id: str,
    source_file: str,
) -> None:
    """Validate identity and descriptive metadata for a palette document."""
    palette_id = metadata.get("id")
    if not isinstance(palette_id, str) or not palette_id:
        raise ValueError(
            f"Missing or invalid 'metadata.id' in {source_file}: "
            "expected non-empty string"
        )
    if palette_id != expected_id:
        raise ValueError(
            f"Palette ID {palette_id!r} in {source_file} must match filename "
            f"stem {expected_id!r}"
        )

    name = metadata.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            f"Missing or invalid 'metadata.name' in {source_file}: "
            "expected non-empty string"
        )

    description = metadata.get("description")
    if description is not None and (
        not isinstance(description, str) or not description.strip()
    ):
        raise ValueError(
            f"Invalid 'metadata.description' in {source_file}: "
            "expected non-empty string"
        )

    release_year = metadata.get("release_year")
    if release_year is not None and type(release_year) is not int:
        raise ValueError(
            f"Invalid 'metadata.release_year' in {source_file}: expected integer"
        )

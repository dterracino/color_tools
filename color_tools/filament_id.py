"""Canonical stable identifiers for filament records."""

from __future__ import annotations

from collections.abc import Iterable
import re


_FILAMENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _require_text(value: object, field_name: str) -> str:
    """Return a non-empty string or raise a field-specific error."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _slugify(value: str, field_name: str) -> str:
    """Convert one product-identity component to database slug form."""
    text = _require_text(value, field_name).casefold().replace("+", " plus ")
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    slug = re.sub(r"[\s-]+", "-", text).strip("-")
    if not slug:
        raise ValueError(f"{field_name} must contain at least one ASCII letter or digit")
    return slug


def generate_filament_id(
    maker: str,
    type_name: str,
    finish: str | None,
    color: str,
) -> str:
    """Generate a stable filament ID from its product identity.

    Maker, material type, optional finish, and color name participate in the
    identifier. Color values and TD values intentionally do not, so those
    attributes can be corrected without changing references to the filament.
    """
    parts = [
        _slugify(maker, "maker"),
        _slugify(type_name, "type_name"),
    ]
    if finish is not None:
        parts.append(_slugify(finish, "finish"))
    parts.append(_slugify(color, "color"))
    return "-".join(parts)


def validate_filament_id(value: str) -> str:
    """Validate and return a canonical lowercase hyphenated filament ID."""
    if not _FILAMENT_ID_PATTERN.fullmatch(value):
        raise ValueError(
            "id must contain only lowercase ASCII letters, digits, and single hyphens"
        )
    return value


def next_available_filament_id(base_id: str, existing_ids: Iterable[str]) -> str:
    """Return the base ID or its first available numeric suffix."""
    validate_filament_id(base_id)
    occupied = set(existing_ids)
    if base_id not in occupied:
        return base_id
    suffix = 2
    while f"{base_id}-{suffix}" in occupied:
        suffix += 1
    return f"{base_id}-{suffix}"

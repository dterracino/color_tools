"""
Internal utilities shared across palette modules.

This module contains helper functions used by both Palette and FilamentPalette
classes. This module is private and its helpers are not part of the public API.
"""

from pathlib import Path
from typing import Protocol, TypeVar


class _SourcedRecord(Protocol):
    """Structural type for records participating in source tie-breaking."""

    @property
    def source(self) -> str:
        """Return the record's source filename."""
        ...


_RecordT = TypeVar("_RecordT", bound=_SourcedRecord)


def get_palette_files(palette_dir: Path, pattern: str) -> list[Path]:
    """Return discoverable palette files, excluding copyable examples."""
    if not palette_dir.exists():
        return []
    return [
        path
        for path in palette_dir.glob(pattern)
        if not path.name.endswith("example.json")
    ]


def should_prefer_source(new_source: str, current_source: str) -> bool:
    """
    Determine if new_source should be preferred over current_source for ties.
    
    User files always win over core files when distances are equal.
    This ensures consistent behavior between index lookups and distance-based searches.
    
    Args:
        new_source: Source filename of the candidate record
        current_source: Source filename of the current best record
    
    Returns:
        True if new_source should be preferred over current_source
    """
    new_is_user = Path(new_source).name.startswith("user-")
    current_is_user = Path(current_source).name.startswith("user-")
    return new_is_user and not current_is_user


def compare_distance_matches(
    left: tuple[_RecordT, float],
    right: tuple[_RecordT, float],
) -> int:
    """Order distance matches, preferring user sources for exact ties."""
    if left[1] < right[1]:
        return -1
    if left[1] > right[1]:
        return 1
    if should_prefer_source(left[0].source, right[0].source):
        return -1
    if should_prefer_source(right[0].source, left[0].source):
        return 1
    return 0


def rounded_key(nums: tuple[float, ...], ndigits: int = 2) -> str:
    """
    Create a string key from rounded numeric values.
    
    Used for fuzzy matching in dictionaries. Instead of looking for
    EXACTLY (50.0, 25.0, 100.0), we round to (50.00, 25.00, 100.00)
    so nearby values will match.
    
    Args:
        nums: Tuple of numeric values to round
        ndigits: Number of decimal places for rounding (default: 2)
    
    Returns:
        Comma-separated string of rounded values
    """
    return ",".join(str(round(x, ndigits)) for x in nums)


def ensure_list(value: str | list[str]) -> list[str]:
    """
    Ensures the input is a list of strings, wrapping if it's a single string.
    
    Utility for functions that accept either a single string or a list of strings.
    
    Args:
        value: A single string or list of strings
    
    Returns:
        List of strings
    """
    if isinstance(value, str):
        return [value]
    return value


def normalize_color_name(name: str) -> str:
    """Normalize a color name for matching and uniqueness checks."""
    return name.strip().casefold()

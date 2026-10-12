"""Canonical strict RGB validation, hex parsing, and hex formatting.

Library code that uses these contracts must delegate to this module instead of
reimplementing them. Format-specific boundary adapters may still parse transport
syntax or present errors differently; output clipping, array processing, and
color-space conversion are separate responsibilities.
"""

from __future__ import annotations

import re
from typing import cast

RGB = tuple[int, int, int]
_COMPONENT_SEPARATOR = re.compile(r" *[-,_/:;] *| +")


def validate_rgb(rgb: object) -> None:
    """Check that RGB contains exactly three built-in integers in 0-255.

    Channels are interpreted as red, green, and blue, in that order. Both
    endpoints are allowed. Booleans, floats (including integral floats), and
    subclasses of int are rejected because each channel must have type int.
    Values are not converted, rounded, or clamped, and the input is not modified.
    Only tuple and list containers are accepted.

    Args:
        rgb: Three 8-bit RGB channels to validate.

    Returns:
        None when all checks pass.

    Raises:
        ValueError: If the channel count is not three, a channel is not a
            built-in integer, or a channel is outside the inclusive 0-255 range.

    Example:
        >>> validate_rgb((255, 127, 0))
    """
    if not isinstance(rgb, (tuple, list)):
        raise ValueError("RGB must be a tuple or list of three integer channels")
    channels = cast(tuple[object, ...] | list[object], rgb)
    if len(channels) != 3 or any(type(channel) is not int for channel in channels):
        raise ValueError("RGB must contain exactly three integer channels")
    if any(not 0 <= channel <= 255 for channel in cast(tuple[int, ...], tuple(channels))):
        raise ValueError("RGB channels must be between 0 and 255")


def parse_hex(hex_code: object) -> RGB:
    """Validate an RGB hex string and return its three 8-bit integer channels.

    Accepts three, four, six, or eight ASCII hexadecimal digits, optionally preceded
    by one #. Digits are case-insensitive. Short form repeats each digit, so
    #24c becomes #2244cc. Four/eight-digit forms use CSS/PNG RGBA order,
    not Windows/Android ARGB. Alpha is validated but dropped for now.
    Whitespace, multiple # prefixes, and non-ASCII hex digits are rejected.

    Args:
        hex_code: RGB/RGBA/RRGGBB/RRGGBBAA, with an optional leading #.

    Returns:
        A (red, green, blue) tuple of integers in the inclusive 0-255 range.

    Raises:
        ValueError: If the input type or syntax is invalid.

    Example:
        >>> parse_hex("#24c")
        (34, 68, 204)
    """
    if not isinstance(hex_code, str):
        raise ValueError("RGB hex color must be a string")
    value = hex_code.removeprefix("#")
    if len(value) not in (3, 4, 6, 8) or any(
        character not in "0123456789abcdefABCDEF" for character in value
    ):
        raise ValueError(f"Invalid RGB hex color: {hex_code!r}")
    if len(value) in (3, 4):
        value = "".join(character * 2 for character in value)
    return (int(value[:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def parse_hex_colors(hex_code: object) -> tuple[RGB, ...]:
    """Parse ordered components separated by -, spaces, comma, _, /, :, or ;.

    ASCII spaces may surround punctuation and the complete compound value. Repeated
    punctuation and empty components are errors, not discarded colors. All
    components are validated, including alpha, and duplicates are retained.
    Any positive number of components is supported. Each uses the single-color
    RGB/RGBA/RRGGBB/RRGGBBAA grammar; alpha is validated then dropped.

    Args:
        hex_code: Original single or compound hex string.

    Returns:
        An immutable ordered tuple of RGB triples.

    Raises:
        ValueError: If the input type or any component is invalid.

    Example:
        >>> parse_hex_colors("#f00 / #00f")
        ((255, 0, 0), (0, 0, 255))
    """
    if not isinstance(hex_code, str):
        raise ValueError("Compound hex color must be a string")
    return tuple(parse_hex(component) for component in _COMPONENT_SEPARATOR.split(hex_code.strip(" ")))


def format_hex(rgb: tuple[int, int, int] | list[int]) -> str:
    """Return normalized #RRGGBB after strict validation, without clipping."""
    validate_rgb(rgb)
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def normalize_hex(hex_code: str) -> str:
    """Return a validated single color in canonical uppercase ``#RRGGBB`` form.

    Short forms are expanded and valid CSS/PNG alpha-last components are
    discarded according to :func:`parse_hex`'s contract.

    Args:
        hex_code: RGB, RGBA, RRGGBB, or RRGGBBAA with an optional leading ``#``.

    Returns:
        The parsed RGB color formatted as uppercase ``#RRGGBB``.

    Raises:
        ValueError: If the input type or syntax is invalid.

    Example:
        >>> normalize_hex("#a1c8")
        '#AA11CC'
    """
    return format_hex(parse_hex(hex_code))

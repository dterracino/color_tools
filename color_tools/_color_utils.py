"""Private helpers for strict RGB validation and hex parsing."""

from __future__ import annotations

from color_tools.conversions import hex_to_rgb

# TODO: Consolidate RGB validation and hex parsing across the library here in a
# future refactor, accounting for existing callers' differing input/error behavior.


def validate_rgb(rgb: tuple[int, int, int]) -> None:
    """Check that RGB contains exactly three built-in integers in 0-255.

    Channels are interpreted as red, green, and blue, in that order. Both
    endpoints are allowed. Booleans, floats (including integral floats), and
    subclasses of int are rejected because each channel must have type int.
    Values are not converted, rounded, or clamped, and the input is not modified.
    The container's length is checked, but its type is not checked at runtime.

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
    if len(rgb) != 3 or any(type(channel) is not int for channel in rgb):
        raise ValueError("RGB must contain exactly three integer channels")
    if any(not 0 <= channel <= 255 for channel in rgb):
        raise ValueError("RGB channels must be between 0 and 255")


def _parse_hex(hex_code: str) -> tuple[int, int, int]:
    """Validate an RGB hex string and return its three 8-bit integer channels.

    Accepts exactly three or six ASCII hexadecimal digits, optionally preceded
    by one #. Digits are case-insensitive. Short form repeats each digit, so
    #24c becomes #2244cc. After syntax validation, conversion delegates to
    hex_to_rgb(). Whitespace is not stripped; multiple # prefixes, alpha
    channels, and non-hexadecimal characters are rejected.

    Args:
        hex_code: RGB/RRGGBB hex text, with an optional leading #.

    Returns:
        A (red, green, blue) tuple of integers in the inclusive 0-255 range.

    Raises:
        ValueError: If the syntax is invalid or hex_to_rgb() cannot parse it.

    Example:
        >>> _parse_hex("#24c")
        (34, 68, 204)
    """
    value = hex_code.removeprefix("#")
    if len(value) not in (3, 6) or any(
        character not in "0123456789abcdefABCDEF" for character in value
    ):
        raise ValueError(f"Invalid RGB hex color: {hex_code!r}")
    rgb = hex_to_rgb(hex_code)
    if rgb is None:
        raise ValueError(f"Invalid RGB hex color: {hex_code!r}")
    return rgb

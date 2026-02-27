"""
Internal utilities shared across palette modules.

This module contains helper functions used by both Palette and FilamentPalette
classes. These functions are private (prefixed with _) and not part of the
public API.
"""

from typing import Tuple, Union, List


def _should_prefer_source(new_source: str, current_source: str) -> bool:
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
    # Core filenames (these are overridden by user files)
    core_files = {"colors.json", "filaments.json"}
    
    new_is_core = new_source in core_files
    current_is_core = current_source in core_files
    
    # If current is core and new is user, prefer new (user override)
    if current_is_core and not new_is_core:
        return True
    
    # If current is user and new is core, keep current (user wins)
    if not current_is_core and new_is_core:
        return False
    
    # Both are same type (core or user), don't prefer either
    return False


def _rounded_key(nums: Tuple[float, ...], ndigits: int = 2) -> str:
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


def _ensure_list(value: Union[str, List[str]]) -> List[str]:
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

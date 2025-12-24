"""
Utility functions for CLI argument parsing and validation.

Helper functions used across CLI command handlers to reduce duplication.
"""

from __future__ import annotations
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

from .constants import ColorConstants


def validate_color_input_exclusivity(args: argparse.Namespace) -> None:
    """
    Validate that --value and --hex are mutually exclusive.
    
    Args:
        args: Parsed command-line arguments
        
    Raises:
        SystemExit: If both --value and --hex are specified
    """
    if hasattr(args, 'value') and hasattr(args, 'hex'):
        if args.value is not None and args.hex is not None:
            print("Error: Cannot specify both --value and --hex", file=sys.stderr)
            sys.exit(2)


def get_rgb_from_args(args: argparse.Namespace) -> tuple[int, int, int]:
    """
    Extract RGB tuple from either --value or --hex arguments.
    
    Args:
        args: Parsed command-line arguments with either 'value' or 'hex' attribute
        
    Returns:
        RGB tuple (r, g, b) with values 0-255
        
    Raises:
        SystemExit: If neither --value nor --hex is provided, or if hex is invalid
    """
    from .conversions import hex_to_rgb
    
    # Check mutual exclusivity first
    validate_color_input_exclusivity(args)
    
    # Check that at least one is provided
    if args.value is None and args.hex is None:
        print("Error: Either --value or --hex is required", file=sys.stderr)
        sys.exit(2)
    
    # Handle hex input
    if args.hex is not None:
        result = hex_to_rgb(args.hex)
        if result is None:
            print(f"Error: Invalid hex color code: '{args.hex}'", file=sys.stderr)
            print("Expected format: #RGB, RGB, #RRGGBB, or RRGGBB", file=sys.stderr)
            sys.exit(2)
        return result
    
    # Handle --value input (RGB values)
    return tuple(args.value)  # type: ignore[return-value]


def parse_hex_or_exit(hex_string: str) -> tuple[int, int, int]:
    """
    Parse a hex color string into RGB values, exiting on error.
    
    Args:
        hex_string: Hex color string ("#FF0000", "FF0000", "#24c", "24c")
        
    Returns:
        RGB tuple (r, g, b) with values 0-255
        
    Raises:
        SystemExit: If hex string is invalid
    """
    from .conversions import hex_to_rgb
    
    result = hex_to_rgb(hex_string)
    if result is None:
        print(f"Error: Invalid hex color code: '{hex_string}'", file=sys.stderr)
        print("Expected format: #RGB, RGB, #RRGGBB, or RRGGBB", file=sys.stderr)
        sys.exit(2)
    
    return result


def is_valid_lab(lab_tuple) -> bool:
    """
    Validate if a Lab tuple is within the standard 8-bit Lab range.
    Lab tuple format: (L*, a*, b*)
    
    Args:
        lab_tuple: Tuple or list of 3 numeric values
        
    Returns:
        True if valid Lab values, False otherwise
    """
    if not isinstance(lab_tuple, (tuple, list)) or len(lab_tuple) != 3:
        return False

    L, a, b = lab_tuple

    # Type check
    if not all(isinstance(v, (int, float)) for v in (L, a, b)):
        return False

    return (ColorConstants.NORMALIZED_MIN <= L <= ColorConstants.XYZ_SCALE_FACTOR) and \
           (ColorConstants.AB_MIN <= a <= ColorConstants.AB_MAX) and \
           (ColorConstants.AB_MIN <= b <= ColorConstants.AB_MAX)


def is_valid_lch(lch_tuple) -> bool:
    """
    Validate if an LCh(ab) tuple is within the standard range.
    LCh tuple format: (L*, C*, h°)
    
    Args:
        lch_tuple: Tuple or list of 3 numeric values
        
    Returns:
        True if valid LCh values, False otherwise
    """
    if not isinstance(lch_tuple, (tuple, list)) or len(lch_tuple) != 3:
        return False

    L, C, h = lch_tuple

    # Type check
    if not all(isinstance(v, (int, float)) for v in (L, C, h)):
        return False

    return (ColorConstants.NORMALIZED_MIN <= L <= ColorConstants.XYZ_SCALE_FACTOR) and \
           (ColorConstants.CHROMA_MIN <= C <= ColorConstants.CHROMA_MAX) and \
           (ColorConstants.NORMALIZED_MIN <= h < ColorConstants.HUE_CIRCLE_DEGREES)


def get_program_name() -> str:
    """
    Determine the proper program name based on how we were invoked.
    
    Returns:
        Program name to display in help text
    """
    from pathlib import Path
    
    try:
        # If we're running as a module, show that
        if sys.argv[0].endswith("__main__.py") or sys.argv[0].endswith("-m"):
            return "python -m color_tools"
        # If we have an installed command name, use that
        return Path(sys.argv[0]).name
    except (IndexError, AttributeError):
        # Fallback
        return "color-tools"

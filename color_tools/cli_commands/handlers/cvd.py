"""CVD command handler - Color vision deficiency simulation and correction."""

import sys
from argparse import Namespace

from ..utils import get_rgb_from_args
from ...color_deficiency import simulate_cvd, correct_cvd


def handle_cvd_command(args: Namespace) -> None:
    """
    Handle the 'cvd' command - simulate or correct color vision deficiency.
    
    Args:
        args: Parsed command-line arguments
        
    Exits:
        0: Success
        2: Invalid input
    """
    value = args.value
    hex_value = args.hex

    # Validate mutual exclusivity of --value and --hex
    if value is not None and hex_value is not None:
        print("Error: Cannot specify both --value and --hex", file=sys.stderr)
        sys.exit(2)
    
    if value is None and hex_value is None:
        print("Error: CVD command requires either --value or --hex", file=sys.stderr)
        sys.exit(2)
    
    rgb = get_rgb_from_args(args)
    r, g, b = rgb
    
    # Apply transformation based on mode
    if args.mode == "simulate":
        result = simulate_cvd(rgb, args.type)
    else:  # correct
        result = correct_cvd(rgb, args.type)
    
    # Format deficiency type name
    deficiency_names = {
        "protanopia": "protanopia (red-blind)",
        "protan": "protanopia (red-blind)",
        "deuteranopia": "deuteranopia (green-blind)",
        "deutan": "deuteranopia (green-blind)",
        "tritanopia": "tritanopia (blue-blind)",
        "tritan": "tritanopia (blue-blind)",
        "all": "all types (protanopia + deuteranopia + tritanopia)"
    }
    deficiency = deficiency_names[args.type.lower()]
    
    # Output result
    print(f"Input RGB:  ({r}, {g}, {b})")
    print(f"Output RGB: ({result[0]}, {result[1]}, {result[2]})")
    print(f"Mode: {args.mode}")
    print(f"Type: {deficiency}")
    
    sys.exit(0)

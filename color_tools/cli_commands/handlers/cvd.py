"""CVD command handler - Color vision deficiency simulation and correction."""

import sys
from argparse import Namespace

from ..utils import parse_hex_or_exit
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
    # Validate mutual exclusivity of --value and --hex
    if args.value is not None and args.hex is not None:
        print("Error: Cannot specify both --value and --hex", file=sys.stderr)
        sys.exit(2)
    
    if args.value is None and args.hex is None:
        print("Error: CVD command requires either --value or --hex", file=sys.stderr)
        sys.exit(2)
    
    # Handle hex input
    if args.hex is not None:
        try:
            r, g, b = parse_hex_or_exit(args.hex)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(2)
    else:
        # Handle --value input
        r, g, b = args.value
        # Validate RGB values
        if not all(0 <= v <= 255 for v in [r, g, b]):
            print("Error: RGB values must be in range 0-255")
            sys.exit(2)
    
    rgb = (r, g, b)
    
    # Apply transformation based on mode
    if args.mode == "simulate":
        result = simulate_cvd(rgb, args.type)
        action = "simulated for"
    else:  # correct
        result = correct_cvd(rgb, args.type)
        action = "corrected for"
    
    # Format deficiency type name
    deficiency_names = {
        "protanopia": "protanopia (red-blind)",
        "protan": "protanopia (red-blind)",
        "deuteranopia": "deuteranopia (green-blind)",
        "deutan": "deuteranopia (green-blind)",
        "tritanopia": "tritanopia (blue-blind)",
        "tritan": "tritanopia (blue-blind)"
    }
    deficiency = deficiency_names[args.type.lower()]
    
    # Output result
    print(f"Input RGB:  ({r}, {g}, {b})")
    print(f"Output RGB: ({result[0]}, {result[1]}, {result[2]})")
    print(f"Mode: {args.mode}")
    print(f"Type: {deficiency}")
    
    sys.exit(0)

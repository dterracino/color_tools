"""Name command handler - Generate descriptive color names from RGB values."""

import sys
from argparse import Namespace

from ..utils import parse_hex_or_exit
from ...naming import generate_color_name


def handle_name_command(args: Namespace) -> None:
    """
    Handle the 'name' command - generate descriptive color names.
    
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
        print("Error: Name command requires either --value or --hex", file=sys.stderr)
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
    name, match_type = generate_color_name(rgb, near_threshold=args.threshold)
    
    if args.show_type:
        print(f"{name} ({match_type})")
    else:
        print(name)
    
    sys.exit(0)

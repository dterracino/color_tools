"""Convert command handler - Convert between color spaces and check gamut."""

import sys
from argparse import Namespace

from ..utils import parse_hex_or_exit
from ...conversions import rgb_to_lab, lab_to_rgb, rgb_to_hsl, hsl_to_rgb, rgb_to_lch, lch_to_rgb, lch_to_lab
from ...gamut import is_in_srgb_gamut, find_nearest_in_gamut


def handle_convert_command(args: Namespace) -> None:
    """
    Handle the 'convert' command - convert between color spaces and check gamut.
    
    Args:
        args: Parsed command-line arguments
        
    Exits:
        0: Success
        2: Invalid input
    """
    if args.check_gamut:
        # Validate mutual exclusivity of --value and --hex
        if args.value is not None and args.hex is not None:
            print("Error: Cannot specify both --value and --hex", file=sys.stderr)
            sys.exit(2)
        
        if args.value is None and args.hex is None:
            print("Error: --check-gamut requires either --value or --hex", file=sys.stderr)
            sys.exit(2)
        
        # Handle hex input (convert to LAB for gamut checking)
        if args.hex is not None:
            try:
                rgb_val = parse_hex_or_exit(args.hex)
                lab = rgb_to_lab(rgb_val)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(2)
        else:
            # Handle --value input
            val = (float(args.value[0]), float(args.value[1]), float(args.value[2]))
            
            # Assume LAB unless otherwise specified
            if args.from_space == "lch":
                lab = lch_to_lab(val)
            else:
                lab = val
        
        in_gamut = is_in_srgb_gamut(lab)
        print(f"LAB({lab[0]:.2f}, {lab[1]:.2f}, {lab[2]:.2f}) is {'IN' if in_gamut else 'OUT OF'} sRGB gamut")
        
        if not in_gamut:
            nearest = find_nearest_in_gamut(lab)
            nearest_rgb = lab_to_rgb(nearest)
            print(f"Nearest in-gamut color:")
            print(f"  LAB: ({nearest[0]:.2f}, {nearest[1]:.2f}, {nearest[2]:.2f})")
            print(f"  RGB: {nearest_rgb}")
        
        sys.exit(0)
    
    # Color space conversion
    if args.to_space:
        # Validate mutual exclusivity of --value and --hex
        if args.value is not None and args.hex is not None:
            print("Error: Cannot specify both --value and --hex", file=sys.stderr)
            sys.exit(2)
        
        if args.value is None and args.hex is None:
            print("Error: Color conversion requires either --value or --hex", file=sys.stderr)
            sys.exit(2)
        
        # Determine the color value and space
        val: tuple[float, float, float]
        from_space: str
        
        # Handle hex input
        if args.hex is not None:
            try:
                rgb_val = parse_hex_or_exit(args.hex)
                val = (float(rgb_val[0]), float(rgb_val[1]), float(rgb_val[2]))
                from_space = "rgb"  # --hex always implies RGB space
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(2)
        else:
            # Handle --value input - --from is required
            if args.from_space is None:
                print("Error: --from is required when using --value", file=sys.stderr)
                sys.exit(2)
            val = (float(args.value[0]), float(args.value[1]), float(args.value[2]))
            from_space = args.from_space
        
        to_space = args.to_space
        
        # Convert to RGB as intermediate (everything goes through RGB)
        if from_space == "rgb":
            rgb = (int(val[0]), int(val[1]), int(val[2]))
        elif from_space == "hsl":
            rgb = hsl_to_rgb(val)
        elif from_space == "lab":
            rgb = lab_to_rgb(val)
        elif from_space == "lch":
            rgb = lch_to_rgb(val)
        
        # Convert from RGB to target
        if to_space == "rgb":
            result = rgb
        elif to_space == "hsl":
            result = rgb_to_hsl(rgb)
        elif to_space == "lab":
            result = rgb_to_lab(rgb)
        elif to_space == "lch":
            result = rgb_to_lch(rgb)
        
        print(f"Converted {from_space.upper()}{val} -> {to_space.upper()}{result}")
        sys.exit(0)
    
    # If we get here, no valid convert operation was specified
    print("Error: No operation specified. Use --check-gamut or --to with --from", file=sys.stderr)
    sys.exit(2)

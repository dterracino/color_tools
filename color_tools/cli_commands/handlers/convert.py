"""Convert command handler - Convert between color spaces and check gamut."""

import sys
from argparse import Namespace
from typing import cast

from ..utils import parse_hex_or_exit
from ...conversions import (
    rgb_to_lab, lab_to_rgb,
    rgb_to_hsl, hsl_to_rgb,
    rgb_to_lch, lch_to_rgb, lch_to_lab,
    rgb_to_cmy, cmy_to_rgb,
    rgb_to_cmyk, cmyk_to_rgb,
)
from ...gamut import is_in_srgb_gamut, find_nearest_in_gamut

# Color spaces that require exactly 4 input components
_FOUR_COMPONENT_SPACES = {"cmyk"}
# Color spaces that require exactly 3 input components
_THREE_COMPONENT_SPACES = {"rgb", "hsl", "lab", "lch", "cmy"}


def handle_convert_command(args: Namespace) -> None:
    """
    Handle the 'convert' command - convert between color spaces and check gamut.
    
    Args:
        args: Parsed command-line arguments
        
    Exits:
        0: Success
        2: Invalid input
    """
    value = cast(list[float] | None, args.value)
    hex_value = cast(str | None, args.hex)

    if args.check_gamut:
        # Validate mutual exclusivity of --value and --hex
        if value is not None and hex_value is not None:
            print("Error: Cannot specify both --value and --hex", file=sys.stderr)
            sys.exit(2)
        
        if value is None and hex_value is None:
            print("Error: --check-gamut requires either --value or --hex", file=sys.stderr)
            sys.exit(2)
        
        # Handle hex input (convert to LAB for gamut checking)
        if hex_value is not None:
            try:
                rgb_val = parse_hex_or_exit(hex_value)
                lab = rgb_to_lab(rgb_val)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(2)
        else:
            # Handle --value input
            assert value is not None
            if len(value) != 3:
                print("Error: --check-gamut requires exactly 3 values", file=sys.stderr)
                sys.exit(2)
            gamut_value: tuple[float, float, float] = (
                float(value[0]),
                float(value[1]),
                float(value[2]),
            )
            
            # Assume LAB unless otherwise specified
            if args.from_space == "lch":
                lab = lch_to_lab(gamut_value)
            else:
                lab = gamut_value
        
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
        if value is not None and hex_value is not None:
            print("Error: Cannot specify both --value and --hex", file=sys.stderr)
            sys.exit(2)
        
        if value is None and hex_value is None:
            print("Error: Color conversion requires either --value or --hex", file=sys.stderr)
            sys.exit(2)
        
        to_space = args.to_space
        val: tuple[float, ...]

        # Handle hex input
        if hex_value is not None:
            try:
                rgb_val = parse_hex_or_exit(hex_value)
                val = (
                    float(rgb_val[0]),
                    float(rgb_val[1]),
                    float(rgb_val[2]),
                )
                from_space = "rgb"  # --hex always implies RGB space
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(2)
        else:
            # Handle --value input - --from is required
            assert value is not None
            if args.from_space is None:
                print("Error: --from is required when using --value", file=sys.stderr)
                sys.exit(2)
            from_space = args.from_space

            # Validate component count for the source space
            expected = 4 if from_space in _FOUR_COMPONENT_SPACES else 3
            if len(value) != expected:
                print(
                    f"Error: --from {from_space} requires exactly {expected} values, "
                    f"got {len(value)}",
                    file=sys.stderr,
                )
                sys.exit(2)

            val = tuple(float(v) for v in value)

        # ------ Convert source space → RGB (intermediate) ------
        triple = (val[0], val[1], val[2])
        if from_space == "rgb":
            rgb = (int(val[0]), int(val[1]), int(val[2]))
        elif from_space == "hsl":
            rgb = hsl_to_rgb(triple)
        elif from_space == "lab":
            rgb = lab_to_rgb(triple)
        elif from_space == "lch":
            rgb = lch_to_rgb(triple)
        elif from_space == "cmy":
            rgb = cmy_to_rgb(triple)
        elif from_space == "cmyk":
            cmyk = tuple(val)
            if len(cmyk) != 4:
                raise ValueError("CMYK input requires four components")
            rgb = cmyk_to_rgb((cmyk[0], cmyk[1], cmyk[2], cmyk[3]))
        else:
            print(f"Error: Unsupported source space '{from_space}'", file=sys.stderr)
            sys.exit(2)

        # ------ Convert RGB → target space ------
        if to_space == "rgb":
            result = rgb
        elif to_space == "hsl":
            result = rgb_to_hsl(rgb)
        elif to_space == "lab":
            result = rgb_to_lab(rgb)
        elif to_space == "lch":
            result = rgb_to_lch(rgb)
        elif to_space == "cmy":
            result = rgb_to_cmy(rgb)
        elif to_space == "cmyk":
            result = rgb_to_cmyk(rgb)
        else:
            print(f"Error: Unsupported target space '{to_space}'", file=sys.stderr)
            sys.exit(2)

        print(f"Converted {from_space.upper()}{val} -> {to_space.upper()}{result}")
        sys.exit(0)
    
    # If we get here, no valid convert operation was specified
    print("Error: No operation specified. Use --check-gamut or --to with --from", file=sys.stderr)
    sys.exit(2)

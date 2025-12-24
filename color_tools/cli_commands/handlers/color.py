"""Color command handler - Search and query CSS colors."""

import sys
from argparse import Namespace
from pathlib import Path

from ..utils import parse_hex_or_exit, is_valid_lab, is_valid_lch
from ...constants import ColorConstants
from ...palette import Palette, load_colors, load_palette
from ...export import export_colors, list_export_formats
from ..reporting import get_available_palettes


def handle_color_command(args: Namespace, json_path: "Path | str | None" = None) -> None:
    """
    Handle the 'color' command - search and query CSS colors.
    
    Args:
        args: Parsed command-line arguments
        json_path: Optional custom data directory
        
    Exits:
        0: Success
        1: Color not found or error
        2: Invalid input
    """
    # Validate mutual exclusivity of --value and --hex
    if args.value is not None and args.hex is not None:
        print("Error: Cannot specify both --value and --hex", file=sys.stderr)
        sys.exit(2)
    
    # Load color palette (either custom retro palette or default CSS colors)
    if args.palette:
        # Special case: list available palettes
        if args.palette.lower() == "list":
            available_palettes = get_available_palettes(json_path)
            if available_palettes:
                print("Available palettes:")
                for palette_name in available_palettes:
                    print(f"  {palette_name}")
            else:
                print("No palettes found")
            sys.exit(0)
        
        # Load the specified palette
        try:
            palette = load_palette(args.palette, json_path)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            available_palettes = get_available_palettes(json_path)
            if available_palettes:
                print(f"Available palettes: {', '.join(available_palettes)}", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f"Error loading palette: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        palette = Palette(load_colors(json_path))
    
    # Handle --list-export-formats
    if args.list_export_formats:
        formats = list_export_formats('colors')
        print("Available export formats for colors:")
        for name, description in formats.items():
            print(f"  {name:12s} - {description}")
        sys.exit(0)
    
    # Handle export if specified (no other operations needed)
    if args.export:
        try:
            output_path = export_colors(palette.records, args.export, args.output)
            print(f"✓ Exported {len(palette.records)} color(s) to {output_path}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    
    if args.name:
        rec = palette.find_by_name(args.name)
        if not rec:
            print(f"Color '{args.name}' not found")
            sys.exit(1)
        print(f"Name: {rec.name} [from {rec.source}]")
        print(f"Hex:  {rec.hex}")
        print(f"RGB:  {rec.rgb}")
        print(f"HSL:  ({rec.hsl[0]:.1f}°, {rec.hsl[1]:.1f}%, {rec.hsl[2]:.1f}%)")
        print(f"LAB:  ({rec.lab[0]:.2f}, {rec.lab[1]:.2f}, {rec.lab[2]:.2f})")
        print(f"LCH:  ({rec.lch[0]:.2f}, {rec.lch[1]:.2f}, {rec.lch[2]:.1f}°)")
        sys.exit(0)
    
    if args.nearest:
        if args.value is None and args.hex is None:
            print("Error: --nearest requires either --value or --hex", file=sys.stderr)
            sys.exit(2)
        
        # Determine the color value and space
        val: tuple[float, float, float]
        space: str
        
        # Handle hex input
        if args.hex is not None:
            try:
                rgb_val = parse_hex_or_exit(args.hex)
                val = (float(rgb_val[0]), float(rgb_val[1]), float(rgb_val[2]))
                space = "rgb"  # --hex always implies RGB space
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(2)
        else:
            # Handle --value input
            val = (float(args.value[0]), float(args.value[1]), float(args.value[2]))
            space = args.space
            
            # Validate LAB/LCH ranges if applicable
            if space == "lab" and not is_valid_lab(val):
                print(f"Error: LAB values appear out of range: {val}", file=sys.stderr)
                print(f"Expected: L* (0-{ColorConstants.XYZ_SCALE_FACTOR}), a* ({ColorConstants.AB_MIN}-{ColorConstants.AB_MAX}), b* ({ColorConstants.AB_MIN}-{ColorConstants.AB_MAX})", file=sys.stderr)
                print("Tip: Use --space rgb or --hex for RGB input", file=sys.stderr)
                sys.exit(2)
            elif space == "lch" and not is_valid_lch(val):
                print(f"Error: LCH values appear out of range: {val}", file=sys.stderr)
                print(f"Expected: L* (0-{ColorConstants.XYZ_SCALE_FACTOR}), C* ({ColorConstants.CHROMA_MIN}-{ColorConstants.CHROMA_MAX}), h° (0-{ColorConstants.HUE_CIRCLE_DEGREES})", file=sys.stderr)
                print("Tip: Use --space rgb or --hex for RGB input", file=sys.stderr)
                sys.exit(2)
        
        # Use the determined color space
        if args.count > 1:
            # Multiple results
            results = palette.nearest_colors(
                val,
                space=space,
                metric=args.metric,
                count=args.count,
                cmc_l=args.cmc_l,
                cmc_c=args.cmc_c,
            )
            print(f"Top {len(results)} nearest colors:")
            for i, (rec, d) in enumerate(results, 1):
                print(f"\n{i}. {rec.name} (distance={d:.2f})")
                print(f"   Hex:  {rec.hex}")
                print(f"   RGB:  {rec.rgb}")
                print(f"   HSL:  ({rec.hsl[0]:.1f}°, {rec.hsl[1]:.1f}%, {rec.hsl[2]:.1f}%)")
                print(f"   LAB:  ({rec.lab[0]:.2f}, {rec.lab[1]:.2f}, {rec.lab[2]:.2f})")
                print(f"   LCH:  ({rec.lch[0]:.2f}, {rec.lch[1]:.2f}, {rec.lch[2]:.1f}°)")
        else:
            # Single result (backward compatibility)
            rec, d = palette.nearest_color(
                val,
                space=space,
                metric=args.metric,
                cmc_l=args.cmc_l,
                cmc_c=args.cmc_c,
            )
            print(f"Nearest color: {rec.name} (distance={d:.2f}) [from {rec.source}]")
            print(f"Hex:  {rec.hex}")
            print(f"RGB:  {rec.rgb}")
            print(f"HSL:  ({rec.hsl[0]:.1f}°, {rec.hsl[1]:.1f}%, {rec.hsl[2]:.1f}%)")
            print(f"LAB:  ({rec.lab[0]:.2f}, {rec.lab[1]:.2f}, {rec.lab[2]:.2f})")
            print(f"LCH:  ({rec.lch[0]:.2f}, {rec.lch[1]:.2f}, {rec.lch[2]:.1f}°)")
        sys.exit(0)
    
    # If we get here, no valid color operation was specified
    print("Error: No operation specified. Use --name, --nearest, --export, or --list-export-formats", file=sys.stderr)
    sys.exit(2)

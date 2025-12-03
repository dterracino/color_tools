"""
Command-line interface for color_tools.

Provides main commands:
- color: Search and query CSS colors
- filament: Search and query 3D printing filaments
- convert: Convert between color spaces and check gamut
- name: Generate descriptive color names
- cvd: Color vision deficiency simulation/correction
- image: Image color analysis and manipulation

This is the "top" of the dependency tree - it imports from everywhere
but nothing imports from it (except __main__.py).
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

from . import __version__
from .constants import ColorConstants
from .config import set_dual_color_mode
from .conversions import rgb_to_lab, lab_to_rgb, rgb_to_hsl, hsl_to_rgb, rgb_to_lch, lch_to_lab, lch_to_rgb
from .gamut import is_in_srgb_gamut, find_nearest_in_gamut
from .palette import Palette, FilamentPalette, load_colors, load_filaments, load_maker_synonyms, load_palette
from .color_deficiency import simulate_cvd, correct_cvd

# Image analysis is optional (requires Pillow)
try:
    from .image import extract_unique_colors, redistribute_luminance, format_color_change_report, simulate_cvd_image, correct_cvd_image, quantize_image_to_palette
    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False

def _parse_hex(hex_string: str) -> tuple[int, int, int]:
    """
    Parse a hex color string into RGB values using existing conversion function.
    
    Args:
        hex_string: Hex color string ("#FF0000", "FF0000", "#24c", "24c")
        
    Returns:
        RGB tuple (r, g, b) with values 0-255
        
    Raises:
        ValueError: If hex string is invalid
    """
    from .conversions import hex_to_rgb
    
    result = hex_to_rgb(hex_string)
    if result is None:
        raise ValueError(f"Invalid hex color code: '{hex_string}'. Expected format: #RGB, RGB, #RRGGBB, or RRGGBB")
    
    return result

def _is_valid_lab(lab_tuple) -> bool:
    """
    Validate if a Lab tuple is within the standard 8-bit Lab range.
    Lab tuple format: (L*, a*, b*)
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

def _is_valid_lch(lch_tuple) -> bool:
    """
    Validate if an LCh(ab) tuple is within the standard range.
    LCh tuple format: (L*, C*, h°)
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

def handle_image_command(args):
    """Handle all image processing commands."""
    if not IMAGE_AVAILABLE:
        print("Error: Image processing requires Pillow", file=sys.stderr)
        print("Install with: pip install color-match-tools[image]", file=sys.stderr)
        sys.exit(1)
    
    # Handle --list-palettes first (doesn not require file)
    if args.list_palettes:
        try:
            palettes_dir = Path(__file__).parent / "data" / "palettes"
            available = sorted([p.stem for p in palettes_dir.glob("*.json")])
            print("Available retro palettes:")
            for palette_name in available:
                try:
                    pal = load_palette(palette_name)
                    print(f"  {palette_name:<15} - {len(pal.records)} colors")
                except Exception:
                    print(f"  {palette_name:<15} - (error loading)")
        except Exception as e:
            print(f"Error listing palettes: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    
    # Check if file is provided and exists for operations that need it
    if not args.file:
        print("Error: --file is required for this operation", file=sys.stderr)
        sys.exit(1)
    
    image_path = Path(args.file)
    if not image_path.exists():
        print(f"Error: Image file not found: {image_path}", file=sys.stderr)
        sys.exit(1)
    
    # Determine output path
    output_path = args.output
    
    # Count active operations
    operations = [
        args.redistribute_luminance,
        args.cvd_simulate is not None,
        args.cvd_correct is not None,
        args.quantize_palette is not None
    ]
    active_count = sum(operations)
    
    if active_count == 0:
        print("Error: No operation specified. Choose one of:", file=sys.stderr)
        print("  --redistribute-luminance    (HueForge color analysis)", file=sys.stderr)
        print("  --cvd-simulate TYPE         (colorblindness simulation)", file=sys.stderr)
        print("  --cvd-correct TYPE          (colorblindness correction)", file=sys.stderr)
        print("  --quantize-palette NAME     (convert to retro palette)", file=sys.stderr)
        print("  --list-palettes             (show available palettes)", file=sys.stderr)
        sys.exit(1)
    elif active_count > 1:
        print("Error: Only one operation allowed at a time", file=sys.stderr)
        sys.exit(1)
    
    # Execute the requested operation
    try:
        if args.redistribute_luminance:
            # HueForge luminance redistribution (existing functionality)
            print(f"Extracting {args.colors} unique colors from {image_path.name}...")
            colors = extract_unique_colors(str(image_path), n_colors=args.colors)
            print(f"Extracted {len(colors)} colors")
            
            # Redistribute luminance
            changes = redistribute_luminance(colors)
            
            # Display report
            report = format_color_change_report(changes)
            print(report)
        
        elif args.cvd_simulate:
            # CVD simulation
            print(f"Simulating {args.cvd_simulate} for {image_path.name}...")
            sim_image = simulate_cvd_image(str(image_path), args.cvd_simulate, output_path)
            
            if output_path:
                print(f"CVD simulation saved to: {output_path}")
            else:
                # Generate default output name
                default_output = image_path.with_name(f"{image_path.stem}_{args.cvd_simulate}_sim{image_path.suffix}")
                sim_image.save(default_output)
                print(f"CVD simulation saved to: {default_output}")
        
        elif args.cvd_correct:
            # CVD correction
            print(f"Applying {args.cvd_correct} correction to {image_path.name}...")
            corrected_image = correct_cvd_image(str(image_path), args.cvd_correct, output_path)
            
            if output_path:
                print(f"CVD correction saved to: {output_path}")
            else:
                # Generate default output name
                default_output = image_path.with_name(f"{image_path.stem}_{args.cvd_correct}_corrected{image_path.suffix}")
                corrected_image.save(default_output)
                print(f"CVD correction saved to: {default_output}")
        
        elif args.quantize_palette:
            # Palette quantization
            dither_text = " with dithering" if args.dither else ""
            print(f"Converting {image_path.name} to {args.quantize_palette} palette{dither_text}...")
            print(f"Using {args.metric} distance metric")
            
            # Load palette info for reporting
            try:
                palette_info = load_palette(args.quantize_palette)
                print(f"Target palette: {len(palette_info.records)} colors")
            except Exception as e:
                print(f"Warning: Could not load palette info: {e}", file=sys.stderr)
            
            quantized_image = quantize_image_to_palette(
                str(image_path), 
                args.quantize_palette,
                metric=args.metric,
                dither=args.dither,
                output_path=output_path
            )
            
            if output_path:
                print(f"Quantized image saved to: {output_path}")
            else:
                # Generate default output name
                dither_suffix = "_dithered" if args.dither else ""
                default_output = image_path.with_name(f"{image_path.stem}_{args.quantize_palette}{dither_suffix}{image_path.suffix}")
                quantized_image.save(default_output)
                print(f"Quantized image saved to: {default_output}")
            
    except Exception as e:
        print(f"Error processing image: {e}", file=sys.stderr)
        sys.exit(1)


def _get_program_name() -> str:
    """Determine the proper program name based on how we were invoked."""
    try:
        # If we're running as a module, show that
        if sys.argv[0].endswith("__main__.py") or sys.argv[0].endswith("-m"):
            return "python -m color_tools"
        # If we have an installed command name, use that
        return Path(sys.argv[0]).name
    except (IndexError, AttributeError):
        # Fallback
        return "color-tools"


def main():
    """
    Main entry point for the CLI.
    
    Note: No `if __name__ == "__main__":` here! That's __main__.py's job.
    This function is just the CLI logic - pure and testable.
    """
    # Determine the proper program name based on how we were invoked
    prog_name = _get_program_name()
    
    parser = argparse.ArgumentParser(
        prog=prog_name,
        description="Color search and conversion tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Find nearest CSS color to an RGB value
  {prog_name} color --nearest --value 128 64 200 --space rgb
  {prog_name} color --nearest --hex "#8040C8"
  
  # Find color by name
  {prog_name} color --name "coral"
  
  # Generate descriptive name for an RGB color
  {prog_name} name --value 255 128 64
  {prog_name} name --hex "#FF8040"
  
  # Simulate color blindness
  {prog_name} cvd --value 255 0 0 --type protanopia --mode simulate
  {prog_name} cvd --hex "#FF0000" --type deutan --mode correct
  
  # Extract and redistribute luminance from image
  {prog_name} image --file photo.jpg --redistribute-luminance --colors 8
  
  # Find nearest filament to an RGB color
  {prog_name} filament --nearest --value 255 0 0
  {prog_name} filament --nearest --hex "#FF0000"
  
  # Find all PLA filaments from two different makers
  {prog_name} filament --type PLA --maker "Bambu Lab" "Sunlu"

  # List all filament makers
  {prog_name} filament --list-makers
  
  # Convert between color spaces
  {prog_name} convert --from rgb --to lab --value 255 128 0
  
  # Check if LAB color is in sRGB gamut
  {prog_name} convert --check-gamut --value 50 100 50
        """
    )
    
    # Global arguments (apply to all subcommands)
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show version number and exit"
    )
    parser.add_argument(
        "--json", 
        type=str, 
        metavar="DIR",
        default=None,  # Will use default package data if None
        help="Path to directory containing JSON data files (colors.json, filaments.json, maker_synonyms.json). Default: uses package data directory"
    )
    parser.add_argument(
        "--verify-constants",
        action="store_true",
        help="Verify integrity of color science constants before proceeding"
    )
    parser.add_argument(
        "--verify-data",
        action="store_true",
        help="Verify integrity of core data files (colors.json, filaments.json, maker_synonyms.json) before proceeding"
    )
    parser.add_argument(
        "--verify-matrices",
        action="store_true",
        help="Verify integrity of transformation matrices before proceeding"
    )
    parser.add_argument(
        "--verify-all",
        action="store_true",
        help="Verify integrity of constants, data files, and matrices before proceeding"
    )
    
    # Create subparsers for the three main commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # ==================== COLOR SUBCOMMAND ====================
    color_parser = subparsers.add_parser(
        "color",
        help="Work with CSS colors",
        description="Search and query CSS color database"
    )
    
    color_parser.add_argument(
        "--nearest", 
        action="store_true", 
        help="Find nearest color to the given value"
    )
    color_parser.add_argument(
        "--name", 
        type=str, 
        help="Find an exact color by name"
    )
    color_parser.add_argument(
        "--value", 
        nargs=3, 
        type=float, 
        metavar=("V1", "V2", "V3"),
        help="Color value tuple (RGB: r g b | HSL: h s l | LAB: L a b | LCH: L C h)"
    )
    color_parser.add_argument(
        "--hex",
        type=str,
        metavar="COLOR",
        help="Hex color value (e.g., '#FF8040' or 'FF8040') - shortcut for RGB input"
    )
    color_parser.add_argument(
        "--space", 
        choices=["rgb", "hsl", "lab", "lch"], 
        default="lab",
        help="Color space of the input value (default: lab)"
    )
    color_parser.add_argument(
        "--metric",
        choices=["euclidean", "de76", "de94", "de2000", "cmc", "cmc21", "cmc11"],
        default="de2000",
        help="Distance metric for LAB space (default: de2000). 'cmc21'=CMC(2:1), 'cmc11'=CMC(1:1)"
    )
    color_parser.add_argument(
        "--cmc-l", 
        type=float, 
        default=ColorConstants.CMC_L_DEFAULT, 
        help="CMC lightness parameter (default: 2.0)"
    )
    color_parser.add_argument(
        "--cmc-c", 
        type=float, 
        default=ColorConstants.CMC_C_DEFAULT, 
        help="CMC chroma parameter (default: 1.0)"
    )
    color_parser.add_argument(
        "--palette",
        type=str,
        choices=["cga4", "cga16", "commodore64", "ega16", "ega64", "gameboy", "gameboy_dmg", "gameboy_gbl", "gameboy_mgb", "nes", "sms", "vga", "virtualboy", "web"],
        help="Use a retro palette instead of CSS colors. Available: cga4, cga16, commodore64, ega16, ega64, gameboy, gameboy_dmg, gameboy_gbl, gameboy_mgb, nes, sms, vga, virtualboy, web"
    )
    color_parser.add_argument(
        "--count",
        type=int,
        default=1,
        metavar="N",
        help="Number of nearest colors to return (default: 1, max: 50)"
    )
    
    # ==================== FILAMENT SUBCOMMAND ====================
    filament_parser = subparsers.add_parser(
        "filament",
        help="Work with 3D printing filaments",
        description="Search and query 3D printing filament database"
    )
    
    filament_parser.add_argument(
        "--nearest", 
        action="store_true", 
        help="Find nearest filament to the given RGB color"
    )
    filament_parser.add_argument(
        "--value", 
        nargs=3, 
        type=int, 
        metavar=("R", "G", "B"),
        help="RGB color value (0-255 for each component)"
    )
    filament_parser.add_argument(
        "--hex",
        type=str,
        metavar="COLOR",
        help="Hex color value (e.g., '#FF8040' or 'FF8040') - shortcut for RGB input"
    )
    filament_parser.add_argument(
        "--metric",
        choices=["euclidean", "de76", "de94", "de2000", "cmc"],
        default="de2000",
        help="Distance metric (default: de2000)"
    )
    filament_parser.add_argument(
        "--cmc-l", 
        type=float, 
        default=ColorConstants.CMC_L_DEFAULT, 
        help="CMC lightness parameter (default: 2.0)"
    )
    filament_parser.add_argument(
        "--cmc-c", 
        type=float, 
        default=ColorConstants.CMC_C_DEFAULT, 
        help="CMC chroma parameter (default: 1.0)"
    )
    filament_parser.add_argument(
        "--count",
        type=int,
        default=1,
        metavar="N",
        help="Number of nearest filaments to return (default: 1, max: 50)"
    )
    
    # List operations
    filament_parser.add_argument(
        "--list-makers", 
        action="store_true", 
        help="List all filament makers"
    )
    filament_parser.add_argument(
        "--list-types", 
        action="store_true", 
        help="List all filament types"
    )
    filament_parser.add_argument(
        "--list-finishes", 
        action="store_true", 
        help="List all filament finishes"
    )
    
    # Filter operations
    filament_parser.add_argument(
        "--maker", 
        nargs='+',
        type=str, 
        help="Filter by one or more makers (e.g., --maker \"Bambu Lab\" \"Polymaker\")"
    )
    filament_parser.add_argument(
        "--type", 
        nargs='+',
        type=str, 
        help="Filter by one or more types (e.g., --type PLA \"PLA+\")"
    )
    filament_parser.add_argument(
        "--finish", 
        nargs='+',
        type=str, 
        help="Filter by one or more finishes (e.g., --finish Matte \"Silk+\")"
    )
    filament_parser.add_argument(
        "--color", 
        type=str, 
        help="Filter by color name"
    )
    filament_parser.add_argument(
        "--dual-color-mode",
        choices=["first", "last", "mix"],
        default="first",
        help="How to handle dual-color filaments: 'first' (default), 'last', or 'mix' (perceptual blend)"
    )
    
    # ==================== CONVERT SUBCOMMAND ====================
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert between color spaces",
        description="Convert colors between RGB, HSL, LAB, and LCH spaces"
    )
    
    convert_parser.add_argument(
        "--from",
        dest="from_space",
        choices=["rgb", "hsl", "lab", "lch"],
        help="Source color space"
    )
    convert_parser.add_argument(
        "--to",
        dest="to_space",
        choices=["rgb", "hsl", "lab", "lch"],
        help="Target color space"
    )
    convert_parser.add_argument(
        "--value", 
        nargs=3, 
        type=float, 
        metavar=("V1", "V2", "V3"),
        help="Color value tuple (mutually exclusive with --hex)"
    )
    convert_parser.add_argument(
        "--hex",
        type=str,
        metavar="COLOR",
        help="Hex color code (e.g., FF5733 or #FF5733) - automatically uses RGB space (mutually exclusive with --value)"
    )
    convert_parser.add_argument(
        "--check-gamut", 
        action="store_true", 
        help="Check if LAB/LCH color is in sRGB gamut (requires --value or --hex)"
    )
    
    # ==================== NAME SUBCOMMAND ====================
    name_parser = subparsers.add_parser(
        "name",
        help="Generate descriptive color names from RGB values",
        description="Generate intelligent, descriptive names for colors using perceptual analysis"
    )
    
    name_parser.add_argument(
        "--value",
        nargs=3,
        type=int,
        metavar=("R", "G", "B"),
        help="RGB color value (0-255 for each component)"
    )
    name_parser.add_argument(
        "--hex",
        type=str,
        metavar="COLOR",
        help="Hex color value (e.g., '#FF8040' or 'FF8040') - shortcut for RGB input"
    )
    name_parser.add_argument(
        "--threshold",
        type=float,
        default=5.0,
        metavar="DELTA_E",
        help="Delta E threshold for 'near' CSS color matches (default: 5.0)"
    )
    name_parser.add_argument(
        "--show-type",
        action="store_true",
        help="Show match type (exact/near/generated) in output"
    )
    
    # ==================== CVD SUBCOMMAND ====================
    cvd_parser = subparsers.add_parser(
        "cvd",
        help="Color vision deficiency simulation and correction",
        description="Simulate how colors appear with color blindness or apply corrections"
    )
    
    cvd_parser.add_argument(
        "--value",
        nargs=3,
        type=int,
        metavar=("R", "G", "B"),
        help="RGB color value (0-255 for each component)"
    )
    cvd_parser.add_argument(
        "--hex",
        type=str,
        metavar="COLOR",
        help="Hex color value (e.g., '#FF8040' or 'FF8040') - shortcut for RGB input"
    )
    cvd_parser.add_argument(
        "--type",
        choices=["protanopia", "protan", "deuteranopia", "deutan", "tritanopia", "tritan"],
        required=True,
        help="Type of color vision deficiency (protanopia=red-blind, deuteranopia=green-blind, tritanopia=blue-blind)"
    )
    cvd_parser.add_argument(
        "--mode",
        choices=["simulate", "correct"],
        default="simulate",
        help="Mode: 'simulate' shows how colors appear to CVD individuals, 'correct' applies daltonization (default: simulate)"
    )
    
    # ==================== IMAGE SUBCOMMAND ====================
    if IMAGE_AVAILABLE:
        image_parser = subparsers.add_parser(
            "image",
            help="Image color analysis and manipulation",
            description="Extract colors, redistribute luminance, simulate colorblindness, and convert to retro palettes"
        )
        
        image_parser.add_argument(
            "--file",
            type=str,
            required=False,
            help="Path to input image file"
        )
        image_parser.add_argument(
            "--output",
            type=str,
            help="Path to save output image (optional)"
        )
        
        # HueForge operations
        image_parser.add_argument(
            "--redistribute-luminance",
            action="store_true",
            help="Extract colors and redistribute their luminance values evenly for HueForge"
        )
        image_parser.add_argument(
            "--colors",
            type=int,
            default=10,
            help="Number of unique colors to extract (default: 10)"
        )
        
        # CVD operations
        image_parser.add_argument(
            "--cvd-simulate",
            type=str,
            choices=["protanopia", "protan", "deuteranopia", "deutan", "tritanopia", "tritan"],
            help="Simulate color vision deficiency (protanopia, deuteranopia, or tritanopia)"
        )
        image_parser.add_argument(
            "--cvd-correct",
            type=str,
            choices=["protanopia", "protan", "deuteranopia", "deutan", "tritanopia", "tritan"],
            help="Apply CVD correction to improve discriminability for specified deficiency"
        )
        
        # Palette quantization
        image_parser.add_argument(
            "--quantize-palette",
            type=str,
            help="Convert image to specified retro palette (e.g., cga4, ega16, vga, gameboy, commodore64)"
        )
        image_parser.add_argument(
            "--metric",
            type=str,
            choices=["de2000", "de94", "de76", "cmc", "euclidean", "hsl_euclidean"],
            default="de2000",
            help="Color distance metric for palette quantization (default: de2000)"
        )
        image_parser.add_argument(
            "--dither",
            action="store_true",
            help="Apply Floyd-Steinberg dithering for palette quantization (reduces banding)"
        )
        
        # List available palettes
        image_parser.add_argument(
            "--list-palettes",
            action="store_true",
            help="List all available retro palettes"
        )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle --verify-all flag
    if args.verify_all:
        args.verify_constants = True
        args.verify_data = True
        args.verify_matrices = True
    
    # Verify constants integrity if requested
    if args.verify_constants:
        if not ColorConstants.verify_integrity():
            print("ERROR: ColorConstants integrity check FAILED!", file=sys.stderr)
            print("The color science constants have been modified.", file=sys.stderr)
            print(f"Expected hash: {ColorConstants._EXPECTED_HASH}", file=sys.stderr)
            print(f"Current hash:  {ColorConstants._compute_hash()}", file=sys.stderr)
            sys.exit(1)
        print("✓ ColorConstants integrity verified")
    
    # Verify matrices integrity if requested
    if args.verify_matrices:
        if not ColorConstants.verify_matrices_integrity():
            print("ERROR: Transformation matrices integrity check FAILED!", file=sys.stderr)
            print("The CVD transformation matrices have been modified.", file=sys.stderr)
            print(f"Expected hash: {ColorConstants.MATRICES_EXPECTED_HASH}", file=sys.stderr)
            print(f"Current hash:  {ColorConstants._compute_matrices_hash()}", file=sys.stderr)
            sys.exit(1)
        print("✓ Transformation matrices integrity verified")
    
    # Verify data files integrity if requested
    if args.verify_data:
        # Determine data directory (use args.json if provided, otherwise None for default)
        data_dir = Path(args.json) if args.json else None
        all_valid, errors = ColorConstants.verify_all_data_files(data_dir)
        
        if not all_valid:
            print("ERROR: Data file integrity check FAILED!", file=sys.stderr)
            for error in errors:
                print(f"  {error}", file=sys.stderr)
            sys.exit(1)
        print("✓ Data files integrity verified (colors.json, filaments.json, maker_synonyms.json, 14 palettes)")
    
    # If only verifying (no other command), exit after success
    if (args.verify_constants or args.verify_data or args.verify_matrices) and not args.command:
        sys.exit(0)
    
    # Handle no subcommand
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    # Validate and convert json_path to Path if provided
    json_path = None
    if args.json:
        json_path = Path(args.json)
        if not json_path.exists():
            print(f"Error: JSON directory does not exist: {json_path}")
            sys.exit(1)
        if not json_path.is_dir():
            print(f"Error: --json must be a directory containing colors.json, filaments.json, and maker_synonyms.json")
            print(f"Provided path is not a directory: {json_path}")
            sys.exit(1)
    
    # ==================== COLOR COMMAND HANDLER ====================
    if args.command == "color":
        # Validate mutual exclusivity of --value and --hex
        if args.value is not None and args.hex is not None:
            print("Error: Cannot specify both --value and --hex", file=sys.stderr)
            sys.exit(2)
        
        # Load color palette (either custom retro palette or default CSS colors)
        if args.palette:
            palette = load_palette(args.palette)
        else:
            palette = Palette(load_colors(json_path))
        
        if args.name:
            rec = palette.find_by_name(args.name)
            if not rec:
                print(f"Color '{args.name}' not found")
                sys.exit(1)
            print(f"Name: {rec.name}")
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
                    rgb_val = _parse_hex(args.hex)
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
                if space == "lab" and not _is_valid_lab(val):
                    print(f"Error: LAB values appear out of range: {val}", file=sys.stderr)
                    print(f"Expected: L* (0-{ColorConstants.XYZ_SCALE_FACTOR}), a* ({ColorConstants.AB_MIN}-{ColorConstants.AB_MAX}), b* ({ColorConstants.AB_MIN}-{ColorConstants.AB_MAX})", file=sys.stderr)
                    print("Tip: Use --space rgb or --hex for RGB input", file=sys.stderr)
                    sys.exit(2)
                elif space == "lch" and not _is_valid_lch(val):
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
                print(f"Nearest color: {rec.name} (distance={d:.2f})")
                print(f"Hex:  {rec.hex}")
                print(f"RGB:  {rec.rgb}")
                print(f"HSL:  ({rec.hsl[0]:.1f}°, {rec.hsl[1]:.1f}%, {rec.hsl[2]:.1f}%)")
                print(f"LAB:  ({rec.lab[0]:.2f}, {rec.lab[1]:.2f}, {rec.lab[2]:.2f})")
                print(f"LCH:  ({rec.lch[0]:.2f}, {rec.lch[1]:.2f}, {rec.lch[2]:.1f}°)")
            sys.exit(0)
        
        # If we get here, no valid color operation was specified
        color_parser.print_help()
        sys.exit(0)
    
    # ==================== FILAMENT COMMAND HANDLER ====================
    elif args.command == "filament":
        # Set dual-color mode BEFORE loading any filaments
        # This is CRITICAL - the mode affects how FilamentRecord.rgb works!
        if hasattr(args, 'dual_color_mode'):
            set_dual_color_mode(args.dual_color_mode)
        
        # Load filament palette with maker synonyms
        filament_palette = FilamentPalette(load_filaments(json_path), load_maker_synonyms(json_path))
        
        if args.list_makers:
            print("Available makers:")
            for maker in filament_palette.makers:
                count = len(filament_palette.find_by_maker(maker))
                print(f"  {maker} ({count} filaments)")
            sys.exit(0)
        
        if args.list_types:
            print("Available types:")
            for type_name in filament_palette.types:
                count = len(filament_palette.find_by_type(type_name))
                print(f"  {type_name} ({count} filaments)")
            sys.exit(0)
        
        if args.list_finishes:
            print("Available finishes:")
            for finish in filament_palette.finishes:
                count = len(filament_palette.find_by_finish(finish))
                print(f"  {finish} ({count} filaments)")
            sys.exit(0)
        
        if args.nearest:
            # Validate mutual exclusivity of --value and --hex
            if args.value is not None and args.hex is not None:
                print("Error: Cannot specify both --value and --hex", file=sys.stderr)
                sys.exit(2)
            
            if args.value is None and args.hex is None:
                print("Error: --nearest requires either --value or --hex", file=sys.stderr)
                sys.exit(2)
            
            # Handle hex input
            if args.hex is not None:
                try:
                    rgb_val = _parse_hex(args.hex)
                except ValueError as e:
                    print(f"Error: {e}", file=sys.stderr)
                    sys.exit(2)
            else:
                # Handle --value input (RGB values)
                rgb_val = tuple(args.value)
            
            try:
                # Handle "*" wildcard filters (convert ["*"] to "*" for the API)
                maker_filter = "*" if args.maker == ["*"] else args.maker
                type_filter = "*" if args.type == ["*"] else args.type  
                finish_filter = "*" if args.finish == ["*"] else args.finish
                
                if args.count > 1:
                    # Multiple results
                    results = filament_palette.nearest_filaments(
                        rgb_val,
                        metric=args.metric,
                        count=args.count,
                        maker=maker_filter,
                        type_name=type_filter,
                        finish=finish_filter,
                        cmc_l=args.cmc_l,
                        cmc_c=args.cmc_c,
                    )
                    print(f"Top {len(results)} nearest filaments:")
                    for i, (rec, d) in enumerate(results, 1):
                        print(f"\n{i}. (distance={d:.2f})")
                        print(f"   {rec}")
                else:
                    # Single result (backward compatibility)
                    rec, d = filament_palette.nearest_filament(
                        rgb_val,
                        metric=args.metric,
                        maker=maker_filter,
                        type_name=type_filter,
                        finish=finish_filter,
                        cmc_l=args.cmc_l,
                        cmc_c=args.cmc_c,
                    )
                    print(f"Nearest filament: (distance={d:.2f})")
                    print(f"  {rec}")
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)
            sys.exit(0)

        if args.maker or args.type or args.finish or args.color:
            # Filter and display filaments
            results = filament_palette.filter(
                maker=args.maker,
                type_name=args.type,
                finish=args.finish,
                color=args.color
            )
            
            if not results:
                print("No filaments found matching the criteria")
                sys.exit(1)
            
            print(f"Found {len(results)} filament(s):")
            for rec in results:
                print(f"  {rec}")
            sys.exit(0)
        
        # If we get here, no valid filament operation was specified
        filament_parser.print_help()
        sys.exit(0)
    
    # ==================== CONVERT COMMAND HANDLER ====================
    elif args.command == "convert":
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
                    rgb_val = _parse_hex(args.hex)
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
                    rgb_val = _parse_hex(args.hex)
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
        convert_parser.print_help()
        sys.exit(0)
    
    # ==================== NAME COMMAND HANDLER ====================
    elif args.command == "name":
        from .naming import generate_color_name
        
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
                r, g, b = _parse_hex(args.hex)
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
    
    # ==================== CVD COMMAND HANDLER ====================
    elif args.command == "cvd":
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
                r, g, b = _parse_hex(args.hex)
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
    
    # ==================== IMAGE COMMAND HANDLER ====================
    elif args.command == "image":
        handle_image_command(args)
        sys.exit(0)

"""
Command-line interface for color_tools.

Provides main commands:
- color: Search and query CSS colors
- filament: Search and query 3D printing filaments
- convert: Convert between color spaces and check gamut
- name: Generate descriptive color names
- validate: Validate if hex codes match color names
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
from .validation import validate_color
from .export import export_filaments, export_colors, list_export_formats
from .cli_commands.handlers import (
    handle_name_command,
    handle_validate_command,
    handle_cvd_command,
    handle_color_command,
    handle_filament_command,
    handle_convert_command,
)
from .cli_commands.utils import (
    validate_color_input_exclusivity,
    get_rgb_from_args,
    parse_hex_or_exit,
    is_valid_lab,
    is_valid_lch,
    get_program_name
)
from .cli_commands.reporting import show_override_report, generate_user_hashes, get_available_palettes

# Image analysis is optional (requires Pillow)
try:
    from .image import extract_unique_colors, redistribute_luminance, format_color_change_report, simulate_cvd_image, correct_cvd_image, quantize_image_to_palette
    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False


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
        args.quantize_palette is not None,
        args.watermark
    ]
    active_count = sum(operations)
    
    if active_count == 0:
        print("Error: No operation specified. Choose one of:", file=sys.stderr)
        print("  --redistribute-luminance    (HueForge color analysis)", file=sys.stderr)
        print("  --cvd-simulate TYPE         (colorblindness simulation)", file=sys.stderr)
        print("  --cvd-correct TYPE          (colorblindness correction)", file=sys.stderr)
        print("  --quantize-palette NAME     (convert to retro palette)", file=sys.stderr)
        print("  --watermark                 (add text/image/SVG watermark with --watermark-text/--watermark-image/--watermark-svg)", file=sys.stderr)
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
        
        elif args.watermark:
            # Watermarking
            from PIL import Image
            from color_tools.image import add_text_watermark, add_image_watermark, add_svg_watermark
            
            # Check that at least one watermark source is specified
            watermark_sources = [args.watermark_text, args.watermark_image, args.watermark_svg]
            if not any(watermark_sources):
                print("Error: Watermark requires one of: --watermark-text, --watermark-image, or --watermark-svg", file=sys.stderr)
                sys.exit(1)
            
            # Check for conflicting watermark sources
            source_count = sum(bool(s) for s in watermark_sources)
            if source_count > 1:
                print("Error: Only one watermark source allowed (--watermark-text, --watermark-image, or --watermark-svg)", file=sys.stderr)
                sys.exit(1)
            
            # Load input image
            print(f"Loading image: {image_path.name}...")
            img = Image.open(str(image_path))
            
            # Apply appropriate watermark type
            if args.watermark_text:
                # Parse color arguments
                try:
                    color_parts = args.watermark_color.split(',')
                    color = tuple(int(c.strip()) for c in color_parts)
                    if len(color) != 3:
                        raise ValueError("Color must have 3 components (R,G,B)")
                except Exception as e:
                    print(f"Error: Invalid --watermark-color format: {e}", file=sys.stderr)
                    print("Use format: R,G,B (e.g., 255,255,255)", file=sys.stderr)
                    sys.exit(1)
                
                stroke_color = None
                if args.watermark_stroke_color:
                    try:
                        stroke_parts = args.watermark_stroke_color.split(',')
                        stroke_color = tuple(int(c.strip()) for c in stroke_parts)
                        if len(stroke_color) != 3:
                            raise ValueError("Stroke color must have 3 components (R,G,B)")
                    except Exception as e:
                        print(f"Error: Invalid --watermark-stroke-color format: {e}", file=sys.stderr)
                        print("Use format: R,G,B (e.g., 0,0,0)", file=sys.stderr)
                        sys.exit(1)
                
                print(f"Adding text watermark: '{args.watermark_text}'")
                watermarked = add_text_watermark(
                    img,
                    text=args.watermark_text,
                    position=args.watermark_position,
                    font_name=args.watermark_font_name,
                    font_file=args.watermark_font_file,
                    font_size=args.watermark_font_size,
                    color=color,
                    opacity=args.watermark_opacity,
                    stroke_color=stroke_color,
                    stroke_width=args.watermark_stroke_width,
                    margin=args.watermark_margin
                )
            
            elif args.watermark_image:
                print(f"Adding image watermark: {Path(args.watermark_image).name}")
                watermarked = add_image_watermark(
                    img,
                    watermark_path=args.watermark_image,
                    position=args.watermark_position,
                    scale=args.watermark_scale,
                    opacity=args.watermark_opacity,
                    margin=args.watermark_margin
                )
            
            elif args.watermark_svg:
                print(f"Adding SVG watermark: {Path(args.watermark_svg).name}")
                try:
                    watermarked = add_svg_watermark(
                        img,
                        svg_path=args.watermark_svg,
                        position=args.watermark_position,
                        scale=args.watermark_scale,
                        opacity=args.watermark_opacity,
                        margin=args.watermark_margin
                    )
                except ImportError as e:
                    print(f"Error: {e}", file=sys.stderr)
                    sys.exit(1)
            
            # Save watermarked image
            if output_path:
                # Convert RGBA to RGB if saving as JPEG
                if output_path.lower().endswith(('.jpg', '.jpeg')) and watermarked.mode == 'RGBA':
                    # Create white background
                    rgb_img = Image.new('RGB', watermarked.size, (255, 255, 255))
                    rgb_img.paste(watermarked, mask=watermarked.split()[3])  # Use alpha channel as mask
                    watermarked = rgb_img
                
                watermarked.save(output_path)
                print(f"Watermarked image saved to: {output_path}")
            else:
                # Generate default output name
                default_output = image_path.with_name(f"{image_path.stem}_watermarked{image_path.suffix}")
                
                # Convert RGBA to RGB if saving as JPEG
                if default_output.suffix.lower() in ['.jpg', '.jpeg'] and watermarked.mode == 'RGBA':
                    rgb_img = Image.new('RGB', watermarked.size, (255, 255, 255))
                    rgb_img.paste(watermarked, mask=watermarked.split()[3])
                    watermarked = rgb_img
                
                watermarked.save(default_output)
                print(f"Watermarked image saved to: {default_output}")
            
    except Exception as e:
        print(f"Error processing image: {e}", file=sys.stderr)
        sys.exit(1)




def main():
    """
    Main entry point for the CLI.
    
    Note: No `if __name__ == "__main__":` here! That's __main__.py's job.
    This function is just the CLI logic - pure and testable.
    """
    # Determine the proper program name based on how we were invoked
    prog_name = get_program_name()
    
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
  
  # Show user file overrides
  {prog_name} --check-overrides
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
        help="Verify integrity of constants, data files, matrices, and user data before proceeding"
    )
    parser.add_argument(
        "--verify-user-data",
        action="store_true",
        help="Verify integrity of user data files (user/user-colors.json, user/user-filaments.json) against .sha256 files"
    )
    parser.add_argument(
        "--generate-user-hashes",
        action="store_true",
        help="Generate .sha256 files for all user data files and exit"
    )
    parser.add_argument(
        "--check-overrides",
        action="store_true",
        help="Show report of user overrides (user/user-colors.json, user/user-filaments.json) and exit"
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
        help="Use a retro palette instead of CSS colors. Common palettes include: cga4, cga16, ega16, ega64, vga, web, gameboy. Use '--palette list' to see all available palettes including user-created ones."
    )
    color_parser.add_argument(
        "--count",
        type=int,
        default=1,
        metavar="N",
        help="Number of nearest colors to return (default: 1, max: 50)"
    )
    
    # Export operations
    color_parser.add_argument(
        "--export",
        type=str,
        metavar="FORMAT",
        help="Export colors to file (formats: csv, json)"
    )
    color_parser.add_argument(
        "--output",
        type=str,
        metavar="FILE",
        help="Output filename (auto-generated with timestamp if not specified)"
    )
    color_parser.add_argument(
        "--list-export-formats",
        action="store_true",
        help="List available export formats and exit"
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
    
    # Export operations
    filament_parser.add_argument(
        "--export",
        type=str,
        metavar="FORMAT",
        help="Export filtered filaments to file (formats: autoforge, csv, json)"
    )
    filament_parser.add_argument(
        "--output",
        type=str,
        metavar="FILE",
        help="Output filename (auto-generated with timestamp if not specified)"
    )
    filament_parser.add_argument(
        "--list-export-formats",
        action="store_true",
        help="List available export formats and exit"
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
    
    # ==================== VALIDATE SUBCOMMAND ====================
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate if a hex code matches a color name",
        description="""Validate color name/hex pairings using fuzzy matching and perceptual color distance (Delta E 2000).
        
        Note: For best fuzzy matching results, install the optional [fuzzy] extra:
        pip install color-match-tools[fuzzy]
        
        Without [fuzzy], uses a hybrid matcher (exact/substring/Levenshtein)."""
    )
    
    validate_parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="Color name to validate (e.g., 'light blue', 'red', 'dark slate gray')"
    )
    validate_parser.add_argument(
        "--hex",
        type=str,
        required=True,
        help="Hex color code to validate (e.g., '#ADD8E6', 'ADD8E6')"
    )
    validate_parser.add_argument(
        "--threshold",
        type=float,
        default=20.0,
        help="Delta E threshold for color match (default: 20.0, lower = stricter)"
    )
    validate_parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output results in JSON format"
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
            description="Extract colors, redistribute luminance, simulate colorblindness, convert to retro palettes, and add watermarks"
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
            help="Convert image to specified retro palette. Built-in: cga4, ega16, vga, gameboy, commodore64. Custom user palettes must use 'user-' prefix (e.g., user-mycustom)."
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
        
        # Watermarking operations
        image_parser.add_argument(
            "--watermark",
            action="store_true",
            help="Add a watermark to the image (use with --watermark-text, --watermark-image, or --watermark-svg)"
        )
        image_parser.add_argument(
            "--watermark-text",
            type=str,
            help="Text to use for watermark (e.g., '© 2025 My Brand')"
        )
        image_parser.add_argument(
            "--watermark-image",
            type=str,
            help="Path to image file to use as watermark (PNG recommended)"
        )
        image_parser.add_argument(
            "--watermark-svg",
            type=str,
            help="Path to SVG file to use as watermark (requires cairosvg)"
        )
        image_parser.add_argument(
            "--watermark-position",
            type=str,
            choices=["top-left", "top-center", "top-right", "center-left", "center", "center-right", "bottom-left", "bottom-center", "bottom-right"],
            default="bottom-right",
            help="Position for watermark (default: bottom-right)"
        )
        image_parser.add_argument(
            "--watermark-font-name",
            type=str,
            help="System font name for text watermark (e.g., 'Arial', 'Times New Roman')"
        )
        image_parser.add_argument(
            "--watermark-font-file",
            type=str,
            help="Custom font file for text watermark (path or filename in fonts/ directory)"
        )
        image_parser.add_argument(
            "--watermark-font-size",
            type=int,
            default=24,
            help="Font size for text watermark in points (default: 24)"
        )
        image_parser.add_argument(
            "--watermark-color",
            type=str,
            default="255,255,255",
            help="Text color as R,G,B (default: 255,255,255 white)"
        )
        image_parser.add_argument(
            "--watermark-stroke-color",
            type=str,
            help="Text outline color as R,G,B (e.g., 0,0,0 for black outline)"
        )
        image_parser.add_argument(
            "--watermark-stroke-width",
            type=int,
            default=0,
            help="Text outline width in pixels (default: 0, no outline)"
        )
        image_parser.add_argument(
            "--watermark-opacity",
            type=float,
            default=0.8,
            help="Watermark opacity from 0.0 (transparent) to 1.0 (opaque) (default: 0.8)"
        )
        image_parser.add_argument(
            "--watermark-scale",
            type=float,
            default=1.0,
            help="Scale factor for image/SVG watermark (default: 1.0)"
        )
        image_parser.add_argument(
            "--watermark-margin",
            type=int,
            default=10,
            help="Margin from edges in pixels for preset positions (default: 10)"
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
        args.verify_user_data = True
    
    # Handle --generate-user-hashes flag (early exit)
    if args.generate_user_hashes:
        generate_user_hashes(args.json)
        sys.exit(0)
    
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
        print("✓ Data files integrity verified (colors.json, filaments.json, maker_synonyms.json, 19 palettes)")
    
    # Verify user data files integrity if requested
    if args.verify_user_data:
        # Determine data directory (use args.json if provided, otherwise None for default)
        data_dir = Path(args.json) if args.json else None
        all_valid, errors = ColorConstants.verify_all_user_data(data_dir)
        
        if not all_valid:
            print("ERROR: User data file integrity check FAILED!", file=sys.stderr)
            for error in errors:
                print(f"  {error}", file=sys.stderr)
            sys.exit(1)
        
        # Count files checked
        user_dir = (data_dir or (Path(__file__).parent / "data")) / "user"
        if user_dir.exists():
            hash_files = list(user_dir.glob("*.sha256"))
            if hash_files:
                print(f"✓ User data files integrity verified ({len(hash_files)} files checked)")
            else:
                print("✓ No user data hash files found to verify")
    
    # Handle --check-overrides flag
    if args.check_overrides:
        show_override_report(args.json)
        sys.exit(0)
    
    # If only verifying (no other command), exit after success
    if (args.verify_constants or args.verify_data or args.verify_matrices or args.verify_user_data) and not args.command:
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
        handle_color_command(args, json_path)
    
    # ==================== FILAMENT COMMAND HANDLER ====================
    elif args.command == "filament":
        handle_filament_command(args, json_path)
    
    # ==================== CONVERT COMMAND HANDLER ====================
    elif args.command == "convert":
        handle_convert_command(args)
    
    # ==================== NAME COMMAND HANDLER ====================
    elif args.command == "name":
        handle_name_command(args)
    
    # ==================== VALIDATE COMMAND HANDLER ====================
    elif args.command == "validate":
        handle_validate_command(args)
    
    # ==================== CVD COMMAND HANDLER ====================
    elif args.command == "cvd":
        handle_cvd_command(args)
    
    # ==================== IMAGE COMMAND HANDLER ====================
    elif args.command == "image":
        handle_image_command(args)
        sys.exit(0)

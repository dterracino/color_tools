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
    handle_image_command,
)
from .cli_commands.utils import (
    validate_color_input_exclusivity,
    get_rgb_from_args,
    parse_hex_or_exit,
    is_valid_lab,
    is_valid_lch,
    get_program_name
)
from .cli_commands.reporting import handle_verification_flags


def main():
    """
    Main entry point for the CLI.
    
    Note: No `if __name__ == "__main__":` here! That's __main__.py's job.
    This function is just the CLI logic - pure and testable.
    """
    # Configure stdout/stderr for UTF-8 on Windows (for Unicode checkmarks, etc.)
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
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
  
  # Convert image formats (WebP, PNG, JPEG, HEIC, AVIF, etc.)
  {prog_name} image --file photo.webp --convert png
  {prog_name} image --file photo.jpg --convert webp --quality 80 --lossy
  
  # Add watermarks to images
  {prog_name} image --file photo.jpg --watermark --watermark-text "© 2025 MyBrand"
  {prog_name} image --file photo.jpg --watermark --watermark-image logo.png --watermark-position top-right
  
  # Simulate colorblindness and convert to retro palettes
  {prog_name} image --file chart.png --cvd-simulate deuteranopia --output colorblind_view.png
  {prog_name} image --file photo.jpg --quantize-palette cga4 --dither --output retro.png
  
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
    image_parser = subparsers.add_parser(
        "image",
        help="Image color analysis and manipulation",
        description="""Image processing operations:
        
- Format Conversion: Convert between PNG, JPEG, WebP, HEIC, AVIF, etc.
- Watermarking: Add text, image, or SVG watermarks with customizable positioning
- Color Analysis: Extract dominant colors with K-means clustering
- Luminance Redistribution: Redistribute luminance values for HueForge 3D printing
- CVD Simulation/Correction: Simulate or correct for color vision deficiencies
- Palette Quantization: Convert to retro palettes (CGA, EGA, VGA, etc.) with dithering
        """
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
    
    # Image format conversion
    image_parser.add_argument(
        "--convert",
        type=str,
        metavar="FORMAT",
        help="Convert image to specified format (png, jpg, webp, heic, avif, etc.). Auto-detects input format from file extension. Defaults to PNG if not specified."
    )
    image_parser.add_argument(
        "--quality",
        type=int,
        metavar="1-100",
        help="Output quality for lossy formats (1-100). Defaults: JPEG=67, WebP=lossless, AVIF=80"
    )
    image_parser.add_argument(
        "--lossy",
        action="store_true",
        help="Use lossy compression for WebP/AVIF instead of lossless (only with --convert)"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle all verification flags (may exit early)
    if handle_verification_flags(args):
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

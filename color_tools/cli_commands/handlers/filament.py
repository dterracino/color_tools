"""Filament command handler - Search and query 3D printing filaments."""

import sys
from argparse import Namespace
from pathlib import Path

from ..utils import parse_hex_or_exit
from ...config import set_dual_color_mode
from ...palette import FilamentPalette, load_filaments, load_maker_synonyms
from ...export import export_filaments, list_export_formats


def handle_filament_command(args: Namespace, json_path: "Path | str | None" = None) -> None:
    """
    Handle the 'filament' command - search and query 3D printing filaments.
    
    Args:
        args: Parsed command-line arguments
        json_path: Optional custom data directory
        
    Exits:
        0: Success
        1: Filament not found or error
        2: Invalid input
    """
    # Set dual-color mode BEFORE loading any filaments
    # This is CRITICAL - the mode affects how FilamentRecord.rgb works!
    if hasattr(args, 'dual_color_mode'):
        set_dual_color_mode(args.dual_color_mode)
    
    # Load filament palette with maker synonyms
    filament_palette = FilamentPalette(load_filaments(json_path), load_maker_synonyms(json_path))
    
    # Handle --list-export-formats
    if args.list_export_formats:
        formats = list_export_formats('filaments')
        print("Available export formats for filaments:")
        for name, description in formats.items():
            print(f"  {name:12s} - {description}")
        sys.exit(0)
    
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
                rgb_val = parse_hex_or_exit(args.hex)
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
                print(f"Nearest filament: (distance={d:.2f}) [from {rec.source}]")
                print(f"  {rec}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.maker or args.type or args.finish or args.color or args.export:
        # Filter filaments (or get all if no filters and exporting)
        if args.maker or args.type or args.finish or args.color:
            results = filament_palette.filter(
                maker=args.maker,
                type_name=args.type,
                finish=args.finish,
                color=args.color
            )
        elif args.export:
            # Export all filaments if --export specified without filters
            results = filament_palette.records
        else:
            results = filament_palette.filter(
                maker=args.maker,
                type_name=args.type,
                finish=args.finish,
                color=args.color
            )
        
        if not results:
            print("No filaments found matching the criteria")
            sys.exit(1)
        
        # Export if requested
        if args.export:
            try:
                output_path = export_filaments(results, args.export, args.output)
                print(f"✓ Exported {len(results)} filament(s) to {output_path}")
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
            sys.exit(0)
        
        # Display results if not exporting
        print(f"Found {len(results)} filament(s):")
        for rec in results:
            print(f"  {rec}")
        sys.exit(0)
    
    # If we get here, no valid filament operation was specified
    print("Error: No operation specified. Use --list-makers, --list-types, --list-finishes, --nearest, or filters", file=sys.stderr)
    sys.exit(2)

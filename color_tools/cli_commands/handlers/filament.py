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
    
    # Load filament palette with maker synonyms and owned filaments
    filament_palette = FilamentPalette.load_default()
    
    # Handle --list-owned
    if hasattr(args, 'list_owned') and args.list_owned:
        owned = filament_palette.list_owned()
        if not owned:
            print("No owned filaments configured")
            print(f"Add filaments with: color-tools filament --add-owned <ID>")
            sys.exit(0)
        
        print(f"Owned filaments ({len(owned)}):")
        for rec in owned:
            print(f"  ID: {rec.id}")
            print(f"      {rec}")
            print()
        sys.exit(0)
    
    # Handle --add-owned
    if hasattr(args, 'add_owned') and args.add_owned:
        try:
            filament_palette.add_owned(args.add_owned, json_path)
            filament = filament_palette.get_filament_by_id(args.add_owned)
            print(f"✓ Added to owned list: {filament}")
            print(f"  ID: {args.add_owned}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    
    # Handle --remove-owned
    if hasattr(args, 'remove_owned') and args.remove_owned:
        try:
            filament = filament_palette.get_filament_by_id(args.remove_owned)
            filament_palette.remove_owned(args.remove_owned, json_path)
            print(f"✓ Removed from owned list: {filament}")
            print(f"  ID: {args.remove_owned}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    
    # Determine owned filtering mode
    # --all-filaments forces owned=False (search all)
    # Otherwise auto-detect (None) or use owned=True if file exists
    owned_filter = False if hasattr(args, 'all_filaments') and args.all_filaments else None
    
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
                    owned=owned_filter,
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
                    owned=owned_filter,
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
                color=args.color,
                owned=owned_filter
            )
        elif args.export:
            # Export: respect owned filtering unless --all-filaments
            if owned_filter is False:
                results = filament_palette.records  # All filaments
            else:
                results = filament_palette.filter(owned=owned_filter)  # Owned or auto-detect
        else:
            results = filament_palette.filter(
                maker=args.maker,
                type_name=args.type,
                finish=args.finish,
                color=args.color,
                owned=owned_filter
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

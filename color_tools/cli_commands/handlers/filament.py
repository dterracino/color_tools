"""Filament command handler - Search and query 3D printing filaments."""

import sys
from argparse import Namespace
from pathlib import Path

from ..utils import get_rgb_from_args
from ...config import config_context
from ...filament_filter_criteria import FilamentFilterCriteria
from ...filament_id import generate_filament_id, next_available_filament_id
from ...filament_palette import FilamentPalette, load_filaments
from ...export import export_filaments, list_export_formats


def handle_filament_command(args: Namespace, json_path: "Path | str | None" = None) -> None:
    """Run a filament command with a scoped multi-color configuration."""
    with config_context(multi_color_mode=getattr(args, "multi_color_mode", None)):
        _handle_filament_command(args, json_path)


def _handle_filament_command(args: Namespace, json_path: "Path | str | None" = None) -> None:
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
    if getattr(args, "filament_action", None) == "import":
        from .filament_import import handle_filament_import_command

        data_dir = Path(json_path) if json_path is not None else None
        handle_filament_import_command(args, data_dir)
        return

    if getattr(args, "generate_id", False):
        _handle_generate_id(args, json_path)

    has_exclusions = any(
        value is not None
        for value in (
            args.exclude_maker,
            args.exclude_type,
            args.exclude_finish,
            args.exclude_color,
        )
    )
    if has_exclusions and not args.nearest:
        print("Error: exclusion filters require --nearest", file=sys.stderr)
        sys.exit(2)

    count_conflicts = any(
        (
            args.nearest,
            args.limit is not None,
            args.export is not None,
            args.list_makers,
            args.list_types,
            args.list_finishes,
            args.list_export_formats,
            getattr(args, "list_owned", False),
            getattr(args, "add_owned", None) is not None,
            getattr(args, "remove_owned", None) is not None,
            getattr(args, "manage", False),
            getattr(args, "gui", False),
        )
    )
    if args.count and count_conflicts:
        print(
            "Error: --count cannot be combined with another filament operation",
            file=sys.stderr,
        )
        sys.exit(2)

    if args.limit is not None and not args.nearest:
        print("Error: --limit requires --nearest", file=sys.stderr)
        sys.exit(2)

    if getattr(args, 'gui', False):
        from ...filament_manager_gui import run_filament_manager_gui
        run_filament_manager_gui(json_dir=json_path)
        return

    # Handle --manage (interactive mode) early - doesn't need palette loaded yet
    if hasattr(args, 'manage') and args.manage:
        from ...interactive_manager import run_interactive_manager
        run_interactive_manager(json_dir=json_path)
        return  # run_interactive_manager handles exit
    
    # Load filament palette with maker synonyms and owned filaments
    filament_palette = FilamentPalette.load_default(json_path)
    
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
        value = args.value
        hex_value = args.hex

        # Validate mutual exclusivity of --value and --hex
        if value is not None and hex_value is not None:
            print("Error: Cannot specify both --value and --hex", file=sys.stderr)
            sys.exit(2)
        
        if value is None and hex_value is None:
            print("Error: --nearest requires either --value or --hex", file=sys.stderr)
            sys.exit(2)
        
        rgb_val = get_rgb_from_args(args)
        
        try:
            # Omitted fields and the established "*" wildcard are unconstrained.
            include = FilamentFilterCriteria(
                maker=None if args.maker == ["*"] else args.maker,
                type_name=None if args.type == ["*"] else args.type,
                finish=None if args.finish == ["*"] else args.finish,
                color=args.color,
                has_td=getattr(args, "has_td", False) or None,
            )
            exclude = FilamentFilterCriteria(
                maker=args.exclude_maker,
                type_name=args.exclude_type,
                finish=args.exclude_finish,
                color=args.exclude_color,
            )
            
            limit = 1 if args.limit is None else args.limit
            if limit > 1:
                # Multiple results
                results = filament_palette.nearest_filaments_by_criteria(
                    rgb_val,
                    metric=args.metric,
                    count=limit,
                    include=include,
                    exclude=exclude,
                    owned=owned_filter,
                    cmc_l=args.cmc_l,
                    cmc_c=args.cmc_c,
                    max_hue_delta=getattr(args, 'max_hue_delta', None),
                )
                print(f"Top {len(results)} nearest filaments:")
                for i, (rec, d) in enumerate(results, 1):
                    print(f"\n{i}. (distance={d:.2f})")
                    print(f"   {rec}")
            else:
                # Single result (backward compatibility)
                rec, d = filament_palette.nearest_filament_by_criteria(
                    rgb_val,
                    metric=args.metric,
                    include=include,
                    exclude=exclude,
                    owned=owned_filter,
                    cmc_l=args.cmc_l,
                    cmc_c=args.cmc_c,
                    max_hue_delta=getattr(args, 'max_hue_delta', None),
                )
                print(f"Nearest filament: (distance={d:.2f}) [from {rec.source}]")
                print(f"  {rec}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        sys.exit(0)

    has_td = getattr(args, "has_td", False)
    if (
        args.maker
        or args.type
        or args.finish
        or args.color
        or has_td
        or args.export
        or args.count
    ):
        # Filter filaments (or get all if no filters and exporting)
        if args.maker or args.type or args.finish or args.color or has_td:
            results = filament_palette.filter(
                maker=args.maker,
                type_name=args.type,
                finish=args.finish,
                color=args.color,
                owned=owned_filter,
                has_td=has_td or None,
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
                owned=owned_filter,
                has_td=has_td or None,
            )
        
        if args.count:
            print(len(results))
            sys.exit(0)

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


def _one_value(values: list[str] | None, option: str, *, required: bool) -> str | None:
    """Read exactly one value from an argparse multi-value option."""
    if not values:
        if required:
            raise ValueError(f"--generate-id requires {option}")
        return None
    if len(values) != 1:
        raise ValueError(f"{option} must contain exactly one value with --generate-id")
    return values[0]


def _handle_generate_id(args: Namespace, json_path: "Path | str | None") -> None:
    """Generate an ID, report collisions, and exit without changing data."""
    conflicting_operations = any(
        (
            args.nearest,
            args.value is not None,
            args.hex is not None,
            args.count,
            args.limit is not None,
            args.list_makers,
            args.list_types,
            args.list_finishes,
            args.list_export_formats,
            args.export is not None,
            getattr(args, "has_td", False),
            args.exclude_maker is not None,
            args.exclude_type is not None,
            args.exclude_finish is not None,
            args.exclude_color is not None,
            getattr(args, "all_filaments", False),
            getattr(args, "list_owned", False),
            getattr(args, "add_owned", None) is not None,
            getattr(args, "remove_owned", None) is not None,
            getattr(args, "manage", False),
            getattr(args, "gui", False),
        )
    )
    if conflicting_operations:
        print("Error: --generate-id cannot be combined with another filament operation", file=sys.stderr)
        sys.exit(2)
    try:
        maker = _one_value(args.maker, "--maker", required=True)
        type_name = _one_value(args.type, "--type", required=True)
        finish = _one_value(args.finish, "--finish", required=False)
        if not args.color:
            raise ValueError("--generate-id requires --color")
        if maker is None or type_name is None:
            raise RuntimeError("required generator values were not returned")
        generated = generate_filament_id(maker, type_name, finish, args.color)
        records = load_filaments(json_path)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(2)

    existing = next((record for record in records if record.id == generated), None)
    print(generated)
    if existing is None:
        print("Status: available")
    else:
        print(f"Status: overrides existing record from {existing.source}")
        suggestion = next_available_filament_id(
            generated,
            (record.id for record in records),
        )
        print(f"Alternative: {suggestion}")
    sys.exit(0)

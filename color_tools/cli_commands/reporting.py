"""
Reporting and diagnostic utilities for user data and overrides.

Functions for generating override reports and managing hash files for user data integrity.
"""

from __future__ import annotations
import sys
import logging
from pathlib import Path

from ..constants import ColorConstants
from ..palette import Palette, FilamentPalette, load_colors, load_filaments, load_maker_synonyms


def show_override_report(json_dir: str | None = None) -> None:
    """
    Show detailed report of user overrides and exit.
    
    Analyzes user-colors.json and user-filaments.json to show what core data
    is being overridden, including conflicts by name and RGB values.
    
    Args:
        json_dir: Optional directory containing JSON files. If None, uses package default.
    """
    # Set up logging to capture override messages
    log_messages = []
    
    class ListHandler(logging.Handler):
        def emit(self, record):
            log_messages.append(self.format(record))
    
    # Configure logging to capture override info
    logger = logging.getLogger('color_tools.palette')
    logger.setLevel(logging.INFO)
    handler = ListHandler()
    logger.addHandler(handler)
    
    print("User Override Report")
    print("=" * 50)
    
    try:
        # Load colors and capture override messages
        palette = Palette.load_default() if json_dir is None else None
        if palette is None and json_dir:
            colors = load_colors(json_dir)
            palette = Palette(colors)
        elif palette is None:
            colors = load_colors()
            palette = Palette(colors)
        
        # Load filaments and capture override messages  
        filament_palette = FilamentPalette.load_default() if json_dir is None else None
        if filament_palette is None and json_dir:
            filaments = load_filaments(json_dir)
            synonyms = load_maker_synonyms(json_dir)
            filament_palette = FilamentPalette(filaments, synonyms)
        elif filament_palette is None:
            filaments = load_filaments()
            synonyms = load_maker_synonyms()  
            filament_palette = FilamentPalette(filaments, synonyms)
        
        # Display captured log messages
        if log_messages:
            print("\nOverride Details:")
            for msg in log_messages:
                if "User colors override" in msg:
                    print(f"  Colors: {msg}")
                elif "User filaments override" in msg:
                    print(f"  Filaments: {msg}")
                elif "User synonyms override" in msg:
                    print(f"  Synonyms: {msg}")
                elif "User synonyms extend" in msg:
                    print(f"  Synonyms: {msg}")
        else:
            print("\nNo user overrides detected.")
        
        # Count sources
        color_sources = {}
        for record in palette.records:
            source = record.source
            color_sources[source] = color_sources.get(source, 0) + 1
        
        filament_sources = {}
        for record in filament_palette.records:
            source = record.source
            filament_sources[source] = filament_sources.get(source, 0) + 1
        
        # Summary
        print(f"\nSummary:")
        print(f"  Total colors: {len(palette.records)}")
        print(f"  Total filaments: {len(filament_palette.records)}")
        
        print(f"\nActive Sources:")
        print("  Colors:")
        for source, count in sorted(color_sources.items()):
            print(f"    {source}: {count} records")
        
        print("  Filaments:")
        for source, count in sorted(filament_sources.items()):
            print(f"    {source}: {count} records")
        
    except Exception as e:
        print(f"\nError loading data: {e}")
        sys.exit(1)
    finally:
        # Clean up logging
        logger.removeHandler(handler)


def generate_user_hashes(json_dir: str | None = None) -> None:
    """
    Generate .sha256 files for all user data files and exit.
    
    Creates hash files for user/user-colors.json, user/user-filaments.json, and 
    user/user-synonyms.json if they exist.
    
    Args:
        json_dir: Optional directory containing data files. If None, uses package default.
    """
    # Determine data directory
    if json_dir:
        data_dir = Path(json_dir)
        if not data_dir.exists():
            print(f"Error: Data directory does not exist: {data_dir}", file=sys.stderr)
            sys.exit(1)
        if not data_dir.is_dir():
            print(f"Error: --json must be a directory: {data_dir}", file=sys.stderr)
            sys.exit(1)
    else:
        data_dir = Path(__file__).parent / "data"
    
    user_dir = data_dir / "user"
    
    if not user_dir.exists():
        print(f"No user data directory found at: {user_dir}")
        print("Create user data files first, then run this command to generate hashes.")
        sys.exit(0)
    
    print("Generating SHA-256 hash files for user data...")
    print("=" * 50)
    
    # Files to check for hash generation
    user_files = [
        (ColorConstants.USER_COLORS_JSON_FILENAME, "colors"),
        (ColorConstants.USER_FILAMENTS_JSON_FILENAME, "filaments"),
        (ColorConstants.USER_SYNONYMS_JSON_FILENAME, "synonyms")
    ]
    
    generated_count = 0
    
    for filename, display_name in user_files:
        file_path = data_dir / filename
        
        if file_path.exists():
            try:
                hash_file = ColorConstants.save_user_data_hash(file_path)
                hash_value = ColorConstants.generate_user_data_hash(file_path)
                print(f"✓ Generated {hash_file.name}")
                print(f"  File: {file_path.name}")
                print(f"  Hash: {hash_value}")
                generated_count += 1
            except Exception as e:
                print(f"✗ Failed to generate hash for {file_path.name}: {e}", file=sys.stderr)
        else:
            print(f"  Skipped {display_name}: {file_path.name} not found")
    
    if generated_count > 0:
        print(f"\nGenerated {generated_count} hash file(s) successfully.")
        print("\nTo verify integrity later, use: --verify-user-data")
    else:
        print("\nNo user data files found to generate hashes for.")
        print("Create user data files (user/user-colors.json, etc.) first.")


def get_available_palettes(json_path: Path | str | None = None) -> list[str]:
    """
    Get list of available palette names from both core and user palettes.
    
    Args:
        json_path: Optional custom data directory. If None, uses package default.
    
    Returns:
        Sorted list of available palette names
    """
    # Determine data directory
    if json_path is None:
        data_dir = Path(__file__).parent / "data"
    else:
        data_dir = Path(json_path)
    
    available = []
    
    # Core palettes
    core_palettes_dir = data_dir / "palettes"
    if core_palettes_dir.exists():
        available.extend([p.stem for p in core_palettes_dir.glob("*.json")])
    
    # User palettes (only user-*.json files)
    user_palettes_dir = data_dir / "user" / "palettes"
    if user_palettes_dir.exists():
        user_palettes = [p.stem for p in user_palettes_dir.glob("user-*.json")]
        available.extend(user_palettes)
    
    # No need to remove duplicates since user palettes have user- prefix
    return sorted(available)


def handle_verification_flags(args) -> bool:
    """
    Handle all verification flags and early-exit conditions.
    
    Returns True if the program should exit after verification, False otherwise.
    
    Args:
        args: Parsed command-line arguments from argparse
        
    Returns:
        bool: True if program should exit (verification-only mode or early exit flag)
    """
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
        user_dir = (data_dir or (Path(__file__).parent.parent / "data")) / "user"
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
        return True
    
    return False

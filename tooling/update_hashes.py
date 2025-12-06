#!/usr/bin/env python3
"""
Update hash values for color_tools data integrity system.

This script generates new SHA-256 hashes for all protected data files and 
provides the values you need to update in constants.py.

Run: python tooling/update_hashes.py
     python tooling/update_hashes.py --autoupdate
     python tooling/update_hashes.py --filaments-only
     python tooling/update_hashes.py --palettes-only

Requirements: rich
"""

import argparse
import hashlib
from pathlib import Path
import sys
import re
import subprocess

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def print_section(title: str) -> None:
    """Print a section header."""
    console.print(f"\n[bold cyan]{title}[/bold cyan]")


def print_hash(const_name: str, hash_value: str) -> None:
    """Print a hash constant assignment."""
    console.print(f'[green]{const_name}[/green] = "[yellow]{hash_value}[/yellow]"')


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]ERROR:[/bold red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[bold yellow]⚠️  Warning:[/bold yellow] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]✓[/bold green] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[dim]{message}[/dim]")


def compute_file_hash(filepath: Path) -> str | None:
    """
    Compute SHA-256 hash of a file.
    Uses the same method as ColorConstants.verify_data_file().
    
    Args:
        filepath: Path to file to hash
        
    Returns:
        Hex digest of SHA-256 hash, or None if file doesn't exist
    """
    if not filepath.exists():
        return None
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


# Palette files mapping (single source of truth)
PALETTE_FILES = {
    'cga4.json': 'CGA4_PALETTE_HASH',
    'cga16.json': 'CGA16_PALETTE_HASH', 
    'ega16.json': 'EGA16_PALETTE_HASH',
    'ega64.json': 'EGA64_PALETTE_HASH',
    'vga.json': 'VGA_PALETTE_HASH',
    'web.json': 'WEB_PALETTE_HASH',
    'gameboy.json': 'GAMEBOY_PALETTE_HASH',
    'gameboy_dmg.json': 'GAMEBOY_DMG_PALETTE_HASH',
    'gameboy_pocket.json': 'GAMEBOY_POCKET_PALETTE_HASH',
    'nes.json': 'NES_PALETTE_HASH',
    'c64.json': 'C64_PALETTE_HASH',
    'amstrad.json': 'AMSTRAD_PALETTE_HASH',
    'virtualboy.json': 'VIRTUALBOY_PALETTE_HASH',
    'zxspectrum.json': 'ZXSPECTRUM_PALETTE_HASH',
}


def generate_data_file_hashes():
    """Generate hashes for main data files."""
    print_section("MAIN DATA FILE HASHES")
    
    data_files = {
        'colors.json': 'COLORS_JSON_HASH',
        'filaments.json': 'FILAMENTS_JSON_HASH', 
        'maker_synonyms.json': 'MAKER_SYNONYMS_JSON_HASH',
    }
    
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "color_tools" / "data"
    
    hashes = {}
    for filename, const_name in data_files.items():
        filepath = data_dir / filename
        hash_val = compute_file_hash(filepath)
        if hash_val:
            print_hash(const_name, hash_val)
            hashes[const_name] = hash_val
        else:
            print_error(f'{filename} not found!')
    
    return hashes


def generate_palette_file_hashes():
    """Generate hashes for all palette files."""
    print_section("PALETTE FILE HASHES")
    
    script_dir = Path(__file__).parent
    palettes_dir = script_dir.parent / "color_tools" / "data" / "palettes"
    
    hashes = {}
    found_files = 0
    
    if palettes_dir.exists():
        for filename, const_name in PALETTE_FILES.items():
            filepath = palettes_dir / filename
            hash_val = compute_file_hash(filepath)
            if hash_val:
                print_hash(const_name, hash_val)
                hashes[const_name] = hash_val
                found_files += 1
            else:
                print_info(f'{const_name} = "" # File not found: {filename}')
        
        # Check for any unexpected palette files
        actual_files = set(f.name for f in palettes_dir.glob("*.json"))
        expected_files = set(PALETTE_FILES.keys())
        unexpected = actual_files - expected_files
        
        if unexpected:
            print_warning(f"Found unexpected palette files: {', '.join(unexpected)}")
            print_info("Add constants for these files and update PALETTE_FILES!")
    else:
        print_error("Palettes directory not found!")
    
    print_info(f"Found {found_files} palette files")
    
    return hashes


def generate_matrices_hash():
    """
    Generate transformation matrices hash.
    Uses ColorConstants._compute_matrices_hash() from constants.py.
    """
    print_section("TRANSFORMATION MATRICES HASH")
    
    try:
        # Add the parent directory to path to import color_tools
        script_dir = Path(__file__).parent
        sys.path.insert(0, str(script_dir.parent))
        
        from color_tools.constants import ColorConstants
        matrices_hash = ColorConstants._compute_matrices_hash()
        print_hash('MATRICES_EXPECTED_HASH', matrices_hash)
        return {'MATRICES_EXPECTED_HASH': matrices_hash}
    except ImportError as e:
        print_error(f"Could not import color_tools: {e}")
        print_info("Make sure you're running from the project root directory")
        return {}


def generate_constants_hash():
    """
    Generate ColorConstants hash.
    Uses ColorConstants._compute_hash() from constants.py.
    """
    print_section("COLOR CONSTANTS HASH (FINAL STEP)")
    print_info("IMPORTANT: Run this AFTER updating all the above hashes in constants.py!")
    
    try:
        # Add the parent directory to path to import color_tools
        script_dir = Path(__file__).parent
        sys.path.insert(0, str(script_dir.parent))
        
        from color_tools.constants import ColorConstants
        constants_hash = ColorConstants._compute_hash()
        print_hash('_EXPECTED_HASH', constants_hash)
        return {'_EXPECTED_HASH': constants_hash}
    except ImportError as e:
        print_error(f"Could not import color_tools: {e}")
        print_info("Make sure you're running from the project root directory")
        return {}


def update_constants_file(new_hashes):
    """Update constants.py with new hash values."""
    script_dir = Path(__file__).parent
    constants_file = script_dir.parent / "color_tools" / "constants.py"
    
    if not constants_file.exists():
        print_error(f"{constants_file} not found!")
        return False
    
    # Read current file content with UTF-8 encoding
    try:
        content = constants_file.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # Fallback to other encodings if UTF-8 fails
        for encoding in ['utf-8-sig', 'latin1', 'cp1252']:
            try:
                content = constants_file.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            print_error(f"Could not read {constants_file} with any encoding!")
            return False
    
    # Update each hash value
    updated_content = content
    for const_name, new_hash in new_hashes.items():
        # Pattern to match hash constant declarations with more flexible whitespace
        pattern = rf'^(\s*{re.escape(const_name)}\s*=\s*)"[a-f0-9]+"'
        replacement = rf'\1"{new_hash}"'
        
        old_content = updated_content
        updated_content = re.sub(pattern, replacement, updated_content, flags=re.MULTILINE)
        
        # Check if replacement actually happened
        if updated_content == old_content:
            print_warning(f"{const_name} was not found or updated")
        else:
            print_success(f"Updated {const_name}")
    
    # Write back to file with UTF-8 encoding
    constants_file.write_text(updated_content, encoding='utf-8')
    print_success(f"Updated {constants_file}")
    return True


def collect_all_hashes():
    """
    Collect all hash values without printing them.
    Reuses the compute_file_hash() function and ColorConstants methods.
    """
    hashes = {}
    
    # Data file hashes
    data_files = {
        'colors.json': 'COLORS_JSON_HASH',
        'filaments.json': 'FILAMENTS_JSON_HASH', 
        'maker_synonyms.json': 'MAKER_SYNONYMS_JSON_HASH',
    }
    
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "color_tools" / "data"
    
    for filename, const_name in data_files.items():
        filepath = data_dir / filename
        hash_val = compute_file_hash(filepath)
        if hash_val:
            hashes[const_name] = hash_val
    
    # Palette file hashes (using PALETTE_FILES constant)
    palettes_dir = data_dir / "palettes"
    for filename, const_name in PALETTE_FILES.items():
        filepath = palettes_dir / filename
        hash_val = compute_file_hash(filepath)
        if hash_val:
            hashes[const_name] = hash_val
    
    # Matrices hash (using ColorConstants method)
    try:
        sys.path.insert(0, str(script_dir.parent))
        from color_tools.constants import ColorConstants
        matrices_hash = ColorConstants._compute_matrices_hash()
        hashes['MATRICES_EXPECTED_HASH'] = matrices_hash
    except ImportError as e:
        print_warning(f"Could not generate matrices hash: {e}")
    
    return hashes


def main():
    """Generate all hash values for the integrity system."""
    parser = argparse.ArgumentParser(
        description="Update hash values for color_tools data integrity system"
    )
    parser.add_argument(
        "--autoupdate", 
        action="store_true",
        help="Automatically update constants.py with new hash values (requires confirmation)"
    )
    parser.add_argument(
        "--constants-only",
        action="store_true", 
        help="Only generate and show the ColorConstants hash (final step)"
    )
    parser.add_argument(
        "--filaments-only",
        action="store_true",
        help="Only generate filaments.json hash"
    )
    parser.add_argument(
        "--palettes-only",
        action="store_true",
        help="Only generate palette file hashes"
    )
    
    args = parser.parse_args()
    
    console.print("[bold blue]Color Tools - Hash Update Utility[/bold blue]")
    console.print("=" * 40)
    
    # Handle specific-only flags
    if args.constants_only:
        generate_constants_hash()
        return
    
    if args.filaments_only:
        script_dir = Path(__file__).parent
        data_dir = script_dir.parent / "color_tools" / "data"
        filepath = data_dir / "filaments.json"
        hash_val = compute_file_hash(filepath)
        if hash_val:
            print_section("FILAMENTS.JSON HASH")
            print_hash('FILAMENTS_JSON_HASH', hash_val)
        else:
            print_error("filaments.json not found!")
        return
    
    if args.palettes_only:
        generate_palette_file_hashes()
        return
    
    # Normal operation: show all hashes
    if not args.autoupdate:
        print_info("This script generates new SHA-256 hashes for all protected data.")
        print_info("Copy the values below into constants.py, then regenerate the")
        print_info("ColorConstants hash as the final step.")
    
    # Generate all the individual hashes
    data_hashes = generate_data_file_hashes()
    palette_hashes = generate_palette_file_hashes() 
    matrices_hashes = generate_matrices_hash()
    
    if args.autoupdate:
        console.print("\n[bold yellow]AUTOUPDATE MODE[/bold yellow]")
        
        # Confirm with user
        response = input("Do you want to automatically update constants.py with these hash values? (y/N): ")
        if response.lower() not in ('y', 'yes'):
            console.print("[bold red]❌ Cancelled.[/bold red] No files were modified.")
            print_info("To manually update, copy the hash values above into constants.py")
            return
        
        print()
        console.print("[bold cyan]🔄 Step 1/2:[/bold cyan] Updating individual hash values...")
        
        # Collect all hashes and update the file
        all_hashes = collect_all_hashes()
        if update_constants_file(all_hashes):
            console.print("[bold green]✅ Individual hash values updated successfully![/bold green]")
            console.print("\n[bold cyan]🔄 Step 2/2:[/bold cyan] Generating final ColorConstants hash...")
            
            # Generate the ColorConstants hash and update it too
            try:
                script_dir = Path(__file__).parent
                parent_dir = script_dir.parent
                
                cmd = [
                    sys.executable, 
                    '-c',
                    'import sys; sys.path.insert(0, "."); from color_tools.constants import ColorConstants; print(ColorConstants._compute_hash())'
                ]
                
                print_info("Calculating ColorConstants hash in fresh process...")
                result = subprocess.run(cmd, cwd=str(parent_dir), capture_output=True, text=True, encoding='utf-8')
                
                if result.returncode == 0:
                    constants_hash = result.stdout.strip()
                    console.print(f"[dim]🔄 Generated new ColorConstants hash: {constants_hash}[/dim]")
                    console.print(f"[dim]🔄 Updating _EXPECTED_HASH with: {constants_hash}[/dim]")
                    
                    # Update the _EXPECTED_HASH value in the file
                    final_hash = {"_EXPECTED_HASH": constants_hash}
                    
                    if update_constants_file(final_hash):
                        console.print("[bold green]✅ ColorConstants hash updated successfully![/bold green]")
                        console.print("\n[bold green]🎉 COMPLETE![/bold green] All hash values have been updated automatically.")
                        console.print("\n[bold cyan]Final verification:[/bold cyan]")
                        console.print("   [yellow]python -m color_tools --verify-all[/yellow]")
                    else:
                        print_warning("Could not update ColorConstants hash automatically.")
                        print_info(f'   Manually update _EXPECTED_HASH = "{constants_hash}" in constants.py')
                else:
                    print_warning(f"Error calculating ColorConstants hash: {result.stderr}")
                    print_info("   Run script again with --constants-only to get the final hash.")
                    
            except Exception as e:
                print_warning(f"Could not generate ColorConstants hash: {e}")
                print_info("Run the script again with --constants-only to get the final hash.")
        else:
            console.print("[bold red]❌ Failed to update constants.py[/bold red]")
    else:
        console.print("\n[bold yellow]NEXT STEPS:[/bold yellow]")
        console.print("[dim]1. Copy the hash values above into constants.py[/dim]")
        console.print("[dim]2. Run this script again to get the new ColorConstants hash:[/dim]")
        console.print("   [yellow]python tooling/update_hashes.py --constants-only[/yellow]")
        console.print("[dim]3. Update _EXPECTED_HASH in constants.py with that value[/dim]")
        console.print("[dim]4. Verify everything works:[/dim]")
        console.print("   [yellow]python -m color_tools --verify-all[/yellow]")
        console.print("\n[bold blue]🚀 Quick option:[/bold blue] Run with --autoupdate flag to do everything automatically:")
        console.print("   [yellow]python tooling/update_hashes.py --autoupdate[/yellow]")


if __name__ == "__main__":
    main()

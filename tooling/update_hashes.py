#!/usr/bin/env python3
"""
Update hash values for color_tools data integrity system.

This script generates new SHA-256 hashes for all protected data files and 
provides the values you need to update in constants.py.

Run: python tooling/update_hashes.py
     python tooling/update_hashes.py --autoupdate
"""

import argparse
import hashlib
from pathlib import Path
import sys
import re
import subprocess

def generate_data_file_hashes():
    """Generate hashes for main data files."""
    print("=== MAIN DATA FILE HASHES ===")
    
    data_files = {
        'colors.json': 'COLORS_JSON_HASH',
        'filaments.json': 'FILAMENTS_JSON_HASH', 
        'maker_synonyms.json': 'MAKER_SYNONYMS_JSON_HASH',
    }
    
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "color_tools" / "data"
    
    for filename, const_name in data_files.items():
        filepath = data_dir / filename
        if filepath.exists():
            hash_val = hashlib.sha256(filepath.read_bytes()).hexdigest()
            print(f'{const_name} = "{hash_val}"')
        else:
            print(f'# ERROR: {filename} not found!')
    print()

def generate_palette_file_hashes():
    """Generate hashes for all palette files."""
    print("=== PALETTE FILE HASHES ===")
    
    # Known palette files and their constant names
    palette_files = {
        'cga4.json': 'CGA4_PALETTE_HASH',
        'cga16.json': 'CGA16_PALETTE_HASH', 
        'ega16.json': 'EGA16_PALETTE_HASH',
        'ega64.json': 'EGA64_PALETTE_HASH',
        'vga.json': 'VGA_PALETTE_HASH',
        'web.json': 'WEB_PALETTE_HASH',
        'gameboy.json': 'GAMEBOY_PALETTE_HASH',
        'gameboy_dmg.json': 'GAMEBOY_DMG_PALETTE_HASH',
        'gameboy_gbl.json': 'GAMEBOY_GBL_PALETTE_HASH',
        'gameboy_mgb.json': 'GAMEBOY_MGB_PALETTE_HASH',
        'nes.json': 'NES_PALETTE_HASH',
        'sms.json': 'SMS_PALETTE_HASH',
        'commodore64.json': 'COMMODORE64_PALETTE_HASH',
        'virtualboy.json': 'VIRTUALBOY_PALETTE_HASH',
    }
    
    script_dir = Path(__file__).parent
    palettes_dir = script_dir.parent / "color_tools" / "data" / "palettes"
    
    found_files = 0
    if palettes_dir.exists():
        for filename, const_name in palette_files.items():
            filepath = palettes_dir / filename
            if filepath.exists():
                hash_val = hashlib.sha256(filepath.read_bytes()).hexdigest()
                print(f'{const_name} = "{hash_val}"')
                found_files += 1
            else:
                print(f'# {const_name} = "" # File not found: {filename}')
        
        # Check for any unexpected palette files
        actual_files = set(f.name for f in palettes_dir.glob("*.json"))
        expected_files = set(palette_files.keys())
        unexpected = actual_files - expected_files
        
        if unexpected:
            print(f"# WARNING: Found unexpected palette files: {', '.join(unexpected)}")
            print(f"# Add constants for these files and update this script!")
    else:
        print("# ERROR: Palettes directory not found!")
    
    print(f"# Found {found_files} palette files")
    print()

def generate_matrices_hash():
    """Generate transformation matrices hash."""
    print("=== TRANSFORMATION MATRICES HASH ===")
    
    try:
        # Add the parent directory to path to import color_tools
        script_dir = Path(__file__).parent
        sys.path.insert(0, str(script_dir.parent))
        
        from color_tools.constants import ColorConstants
        matrices_hash = ColorConstants._compute_matrices_hash()
        print(f'MATRICES_EXPECTED_HASH = "{matrices_hash}"')
    except ImportError as e:
        print(f"# ERROR: Could not import color_tools: {e}")
        print("# Make sure you're running from the project root directory")
    print()

def generate_constants_hash():
    """Generate ColorConstants hash."""
    print("=== COLOR CONSTANTS HASH ===")
    print("# IMPORTANT: Run this AFTER updating all the above hashes in constants.py!")
    
    try:
        # Add the parent directory to path to import color_tools
        script_dir = Path(__file__).parent
        sys.path.insert(0, str(script_dir.parent))
        
        from color_tools.constants import ColorConstants
        constants_hash = ColorConstants._compute_hash()
        print(f'_EXPECTED_HASH = "{constants_hash}"')
    except ImportError as e:
        print(f"# ERROR: Could not import color_tools: {e}")
        print("# Make sure you're running from the project root directory")
    print()

def update_constants_file(new_hashes):
    """Update constants.py with new hash values."""
    script_dir = Path(__file__).parent
    constants_file = script_dir.parent / "color_tools" / "constants.py"
    
    if not constants_file.exists():
        print(f"ERROR: {constants_file} not found!")
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
            print(f"ERROR: Could not read {constants_file} with any encoding!")
            return False
    
    # Update each hash value
    updated_content = content
    for const_name, new_hash in new_hashes.items():
        # Pattern to match hash constant declarations with more flexible whitespace
        pattern = rf'^(\s*{re.escape(const_name)}\s*=\s*)"[a-f0-9]+"'
        replacement = rf'\1"{new_hash}"'
        
        old_content = updated_content
        updated_content = re.sub(pattern, replacement, updated_content, flags=re.MULTILINE)
        
        # Debug: Check if replacement actually happened
        if updated_content == old_content:
            print(f"⚠️  Warning: {const_name} was not found or updated")
        else:
            print(f"✓ Updated {const_name}")
    
    # Write back to file with UTF-8 encoding
    constants_file.write_text(updated_content, encoding='utf-8')
    print(f"✅ Updated {constants_file}")
    return True

def collect_all_hashes():
    """Collect all hash values without printing them."""
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
        if filepath.exists():
            hash_val = hashlib.sha256(filepath.read_bytes()).hexdigest()
            hashes[const_name] = hash_val
    
    # Palette file hashes
    palette_files = {
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
    
    palettes_dir = data_dir / "palettes"
    for filename, const_name in palette_files.items():
        filepath = palettes_dir / filename
        if filepath.exists():
            hash_val = hashlib.sha256(filepath.read_bytes()).hexdigest()
            hashes[const_name] = hash_val
    
    # Matrices hash
    try:
        sys.path.insert(0, str(script_dir.parent))
        from color_tools.constants import ColorConstants
        matrices_hash = ColorConstants._compute_matrices_hash()
        hashes['MATRICES_EXPECTED_HASH'] = matrices_hash
    except ImportError as e:
        print(f"Warning: Could not generate matrices hash: {e}")
    
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
        help="Only generate and show the ColorConstants hash"
    )
    
    args = parser.parse_args()
    
    print("Color Tools - Hash Update Utility")
    print("=" * 40)
    print()
    
    # If --constants-only flag, just show the constants hash
    if args.constants_only:
        print("=== COLORCONST_CONSTANTS HASH (FINAL STEP) ===")
        generate_constants_hash()
        return
    
    print("This script generates new SHA-256 hashes for all protected data.")
    if not args.autoupdate:
        print("Copy the values below into constants.py, then regenerate the")
        print("ColorConstants hash as the final step.")
    print()
    
    # Generate all the individual hashes
    generate_data_file_hashes()
    generate_palette_file_hashes() 
    generate_matrices_hash()
    
    if args.autoupdate:
        print("=" * 40)
        print("AUTOUPDATE MODE")
        print()
        
        # Confirm with user
        response = input("Do you want to automatically update constants.py with these hash values? (y/N): ")
        if response.lower() not in ('y', 'yes'):
            print("❌ Cancelled. No files were modified.")
            print()
            print("To manually update, copy the hash values above into constants.py")
            return
        
        print()
        print("🔄 Step 1/2: Updating individual hash values...")
        
        # Collect all hashes and update the file
        all_hashes = collect_all_hashes()
        if update_constants_file(all_hashes):
            print("✅ Individual hash values updated successfully!")
            print()
            print("🔄 Step 2/2: Generating final ColorConstants hash...")
            
            # Generate the ColorConstants hash and update it too
            try:
                # Use subprocess to calculate hash in fresh Python process
                # This avoids any module caching issues completely
                import subprocess
                
                script_dir = Path(__file__).parent
                parent_dir = script_dir.parent
                
                cmd = [
                    sys.executable, 
                    '-c',
                    'import sys; sys.path.insert(0, "."); from color_tools.constants import ColorConstants; print(ColorConstants._compute_hash())'
                ]
                
                print("🔄 Calculating ColorConstants hash in fresh process...")
                result = subprocess.run(cmd, cwd=str(parent_dir), capture_output=True, text=True, encoding='utf-8')
                
                if result.returncode == 0:
                    constants_hash = result.stdout.strip()
                    print(f"🔄 Generated new ColorConstants hash: {constants_hash}")
                    
                    # Update the _EXPECTED_HASH value in the file
                    final_hash = {"_EXPECTED_HASH": constants_hash}
                    print(f"🔄 Updating _EXPECTED_HASH with: {constants_hash}")
                    
                    if update_constants_file(final_hash):
                        print("✅ ColorConstants hash updated successfully!")
                        print()
                        print("🎉 COMPLETE! All hash values have been updated automatically.")
                        print()
                        print("Final verification:")
                        print("   python -m color_tools --verify-all")
                    else:
                        print("⚠️  Could not update ColorConstants hash automatically.")
                        print(f"   Manually update _EXPECTED_HASH = \"{constants_hash}\" in constants.py")
                else:
                    print(f"⚠️  Error calculating ColorConstants hash: {result.stderr}")
                    print("   Run script again with --constants-only to get the final hash.")
                    
            except Exception as e:
                print(f"⚠️  Could not generate ColorConstants hash: {e}")
                print("Run the script again with --constants-only to get the final hash.")
        else:
            print("❌ Failed to update constants.py")
    else:
        print("=" * 40)
        print("NEXT STEPS:")
        print("1. Copy the hash values above into constants.py")
        print("2. Run this script again to get the new ColorConstants hash:")
        print("   python tooling/update_hashes.py --constants-only")
        print("3. Update _EXPECTED_HASH in constants.py with that value")
        print("4. Verify everything works:")
        print("   python -m color_tools --verify-all")
        print()
        print("🚀 To automatically update all hashes, run this script again with the --autoupdate flag.")
        print("   python tooling/update_hashes.py --autoupdate")

if __name__ == "__main__":
    main()
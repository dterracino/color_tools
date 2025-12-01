#!/usr/bin/env python3
"""
Compact color arrays in JSON files for better readability.

Reformats JSON files so that color value arrays (rgb, hsl, lab, lch) 
are displayed on single lines instead of multi-line format.

Processes:
- Main data files: colors.json, filaments.json  
- Palette files: all JSON files in palettes/ directory

Convert from:
    "rgb": [
      85,
      255,
      255
    ]
To:
    "rgb": [85, 255, 255]

IMPORTANT: After running this script, you must regenerate ALL data file 
hashes in constants.py since the file contents will change!

Run: python tooling/compact_color_arrays.py
"""

import json
import re
import os
from pathlib import Path

def compact_json_arrays(input_path: str):
    """Load JSON and reformat with compact arrays."""
    
    # Read the entire file as text
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match multi-line arrays like:
    # "rgb": [
    #   85,
    #   255,
    #   255
    # ]
    
    pattern = r'("(?:rgb|hsl|lab|lch)": \[)\s*\n\s*([^\]]+?)\n\s*(\])'
    
    def compact_array(match):
        key_part = match.group(1)  # "rgb": [
        values_part = match.group(2)  # the values with whitespace
        closing_part = match.group(3)  # ]
        
        # Extract just the numbers, handling both integers and floats
        values = []
        for line in values_part.split('\n'):
            line = line.strip()
            if line.endswith(','):
                line = line[:-1]  # Remove trailing comma
            if line:
                try:
                    # Try to parse as number
                    if '.' in line:
                        values.append(float(line))
                    else:
                        values.append(int(line))
                except ValueError:
                    # If parsing fails, keep as string (shouldn't happen with our data)
                    values.append(line)
        
        # Format compactly
        values_str = ', '.join(str(v) for v in values)
        return f'{key_part}{values_str}{closing_part}'
    
    # Apply the transformation
    compacted = re.sub(pattern, compact_array, content, flags=re.MULTILINE | re.DOTALL)
    
    # Write back to file
    with open(input_path, 'w', encoding='utf-8') as f:
        f.write(compacted)
    
    return compacted

def show_sample_before_after(input_path: str):
    """Show a sample of the format before and after."""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find first occurrence of verbose array
    match = re.search(r'("(?:rgb|hsl|lab|lch)": \[)\s*\n\s*([^\]]+?)\n\s*(\])', content, re.MULTILINE | re.DOTALL)
    if match:
        print("BEFORE (verbose format):")
        print(match.group(0))
        print()

def main():
    """Process all JSON files with color arrays (main data files + palette files)."""
    
    # Find data directory
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "color_tools" / "data"
    palettes_dir = data_dir / "palettes"
    
    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        return
    
    # Find main data files that contain color arrays
    main_files = []
    for filename in ["colors.json", "filaments.json"]:
        filepath = data_dir / filename
        if filepath.exists():
            main_files.append(filepath)
    
    # Find all JSON files in palettes directory
    palette_files = []
    if palettes_dir.exists():
        palette_files = list(palettes_dir.glob("*.json"))
    
    all_files = main_files + palette_files
    
    if not all_files:
        print(f"No JSON files found in {data_dir} or {palettes_dir}")
        return
    
    print("Found files to process:")
    if main_files:
        print("  Main data files:")
        for f in main_files:
            print(f"    - {f.name}")
    if palette_files:
        print("  Palette files:")
        for f in palette_files:
            print(f"    - {f.name}")
    print()
    
    # Prompt for confirmation
    print("⚠️  WARNING: This will modify all color data files and requires updating")
    print("   ALL hash values in constants.py afterwards!")
    print()
    response = input("Are you sure you want to proceed? [y/N]: ").strip().lower()
    
    if response not in ['y', 'yes']:
        print("Operation cancelled.")
        return
    print()
    
    total_saved = 0
    
    for json_file in all_files:
        print(f"Processing {json_file.name}...")
        
        # Show sample before (only for first file)
        if json_file == all_files[0]:
            show_sample_before_after(str(json_file))
        
        # Get original size
        original_size = os.path.getsize(json_file)
        
        # Compact the arrays
        compact_json_arrays(str(json_file))
        
        # Show after (only for first file)  
        if json_file == all_files[0]:
            print("AFTER (compact format):")
            with open(json_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find first compact array to show
            match = re.search(r'"(?:rgb|hsl|lab|lch)": \[[^\]]+\]', content)
            if match:
                print(f'    {match.group(0)}')
            print()
        
        # Calculate savings
        new_size = os.path.getsize(json_file)
        saved = original_size - new_size
        total_saved += saved
        
        print(f"  {original_size:,} → {new_size:,} bytes (saved {saved:,} bytes)")
        print()
    
    print(f"✓ Processed {len(all_files)} JSON files")
    print(f"✓ Total space saved: {total_saved:,} bytes")
    print()
    print("⚠️  IMPORTANT: You must now regenerate ALL data file hashes in constants.py!")
    print("   The file contents have changed, so the SHA-256 hashes are now invalid.")
    print()
    print("   Files that need hash updates:")
    if main_files:
        print("   - Main data files (colors.json, filaments.json)")
    if palette_files:
        print("   - All palette files")
    print()
    print("   Run verification to see which hashes need updating:")
    print("   python -m color_tools --verify-all")

if __name__ == "__main__":
    main()
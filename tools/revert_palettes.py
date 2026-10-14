#!/usr/bin/env python3
"""Revert palette files back to simple array format"""

import json
from pathlib import Path
from typing import cast

def revert_palette_file(filepath: Path) -> None:
    """Convert a metadata format palette back to simple array format"""
    with open(filepath, 'r') as f:
        data: object = json.load(f)
    
    # Extract just the palette array
    if isinstance(data, dict) and 'palette' in data:
        palette = cast(dict[str, object], data)['palette']
        if not isinstance(palette, dict):
            print(f"Unknown palette definition in {filepath}")
            return
        palette_array = cast(dict[str, object], palette).get('colors')
        if not isinstance(palette_array, list):
            print(f"No indexed colors in {filepath}")
            return
    elif isinstance(data, list):
        # Already in simple format
        return
    else:
        print(f"Unknown format in {filepath}")
        return
    
    # Write back as simple array
    with open(filepath, 'w') as f:
        json.dump(palette_array, f, indent=2)
    
    print(f"✓ Reverted {filepath.name}")

def main() -> None:
    """Revert all palette files to simple format"""
    palettes_dir = Path("color_tools/data/palettes")
    
    if not palettes_dir.exists():
        print("Palettes directory not found!")
        return
    
    for palette_file in palettes_dir.glob("*.json"):
        revert_palette_file(palette_file)
    
    print("All palette files reverted to simple array format")

if __name__ == "__main__":
    main()

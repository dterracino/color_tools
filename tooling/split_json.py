#!/usr/bin/env python3
"""
One-time script to split color_tools.json into colors.json and filaments.json.

Run this once to migrate from the old single-file format to the new split format.
"""

import json
from pathlib import Path


def main():
    # Paths
    data_dir = Path(__file__).parent / "data"
    old_file = data_dir / "color_tools.json"
    colors_file = data_dir / "colors.json"
    filaments_file = data_dir / "filaments.json"
    
    # Load the old combined file
    print(f"Reading {old_file}...")
    with open(old_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Extract colors and filaments
    colors = data.get("colors", [])
    filaments = data.get("filaments", [])
    
    print(f"Found {len(colors)} colors and {len(filaments)} filaments")
    
    # Write colors.json (just the array, no wrapper object)
    print(f"Writing {colors_file}...")
    with open(colors_file, "w", encoding="utf-8") as f:
        json.dump(colors, f, indent=2, ensure_ascii=False)
    
    # Write filaments.json (just the array, no wrapper object)
    print(f"Writing {filaments_file}...")
    with open(filaments_file, "w", encoding="utf-8") as f:
        json.dump(filaments, f, indent=2, ensure_ascii=False)
    
    print("\n✅ Done! Created:")
    print(f"  - {colors_file}")
    print(f"  - {filaments_file}")
    print(f"\nThe old {old_file} has been left intact for backup.")
    print("You can rename it to color_tools.json.backup when you're ready.")


if __name__ == "__main__":
    main()

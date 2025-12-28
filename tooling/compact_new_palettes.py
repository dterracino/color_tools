#!/usr/bin/env python3
"""Compact the new palette files to match existing format."""

import json
from pathlib import Path

def compact_palette(filepath: Path) -> None:
    """Compact a palette file to use single-line arrays."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Write with compact arrays
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('[\n')
        for i, color in enumerate(data):
            f.write('  {\n')
            f.write(f'    "name": "{color["name"]}",\n')
            f.write(f'    "hex": "{color["hex"]}",\n')
            f.write(f'    "rgb": {json.dumps(color["rgb"])},\n')
            f.write(f'    "hsl": {json.dumps(color["hsl"])},\n')
            f.write(f'    "lab": {json.dumps(color["lab"])},\n')
            f.write(f'    "lch": {json.dumps(color["lch"])}\n')
            if i < len(data) - 1:
                f.write('  },\n')
            else:
                f.write('  }\n')
        f.write(']\n')
    
    print(f"✓ Compacted {filepath.name}")

def main():
    palettes_dir = Path('color_tools/data/palettes')
    new_palettes = ['apple2.json', 'macintosh.json', 'gameboy-color.json', 'tandy16.json']
    
    for palette_file in new_palettes:
        compact_palette(palettes_dir / palette_file)
    
    print("\n✨ All palettes compacted!")

if __name__ == '__main__':
    main()

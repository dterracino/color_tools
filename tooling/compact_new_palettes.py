#!/usr/bin/env python3
"""Compact the new palette files to match existing format."""

import json
from pathlib import Path
from typing import cast

from tools.convert_palettes import serialize_palette_document

def compact_palette(filepath: Path) -> None:
    """Compact a palette file to use single-line arrays."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    if not isinstance(data, dict):
        raise ValueError(f"Expected palette document in {filepath}")
    document = cast(dict[str, object], data)
    filepath.write_text(
        serialize_palette_document(document),
        encoding="utf-8",
        newline="\n",
    )
    
    print(f"✓ Compacted {filepath.name}")

def main():
    palettes_dir = Path('color_tools/data/palettes')
    new_palettes = ['apple2.json', 'macintosh.json', 'tandy16.json']
    
    for palette_file in new_palettes:
        compact_palette(palettes_dir / palette_file)
    
    print("\n✨ All palettes compacted!")

if __name__ == '__main__':
    main()

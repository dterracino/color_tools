#!/usr/bin/env python3
"""
Compare current Polymaker data vs newly extracted data from PDF.

Shows what would be added, removed, and changed.
"""

import json
from pathlib import Path
from collections import defaultdict


def main():
    """Compare and preview changes."""
    
    # Load current filaments
    current_path = Path(__file__).parent.parent / 'color_tools' / 'data' / 'filaments.json'
    with open(current_path, 'r', encoding='utf-8') as f:
        all_filaments = json.load(f)
    
    current_polymaker = [f for f in all_filaments if f['maker'] == 'Polymaker']
    
    # Load extracted filaments
    extracted_path = Path(__file__).parent / 'polymaker_extracted.json'
    with open(extracted_path, 'r', encoding='utf-8') as f:
        new_polymaker = json.load(f)
    
    print("=" * 100)
    print("POLYMAKER DATA COMPARISON")
    print("=" * 100)
    print(f"\nCurrent Polymaker filaments in database: {len(current_polymaker)}")
    print(f"Newly extracted from PDF: {len(new_polymaker)}")
    print(f"Difference: {len(new_polymaker) - len(current_polymaker):+d}")
    
    # Compare types
    print(f"\n{'=' * 100}")
    print("FILAMENT TYPES COMPARISON")
    print("=" * 100)
    
    current_types = defaultdict(int)
    for f in current_polymaker:
        current_types[f['type']] += 1
    
    new_types = defaultdict(int)
    for f in new_polymaker:
        new_types[f['type']] += 1
    
    all_types = sorted(set(current_types.keys()) | set(new_types.keys()))
    
    print(f"\n{'Type':<20} {'Current':<10} {'New':<10} {'Change':<10}")
    print("-" * 60)
    for ftype in all_types:
        curr = current_types.get(ftype, 0)
        new = new_types.get(ftype, 0)
        diff = new - curr
        status = "NEW" if curr == 0 else "REMOVED" if new == 0 else f"{diff:+d}"
        print(f"{ftype:<20} {curr:<10} {new:<10} {status:<10}")
    
    # Save preview files
    output_dir = Path(__file__).parent
    
    # Preview of what would be added/changed
    preview_file = output_dir / 'polymaker_update_preview.txt'
    with open(preview_file, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("POLYMAKER DATA UPDATE PREVIEW\n")
        f.write("=" * 100 + "\n\n")
        
        f.write(f"Current count: {len(current_polymaker)}\n")
        f.write(f"New count: {len(new_polymaker)}\n")
        f.write(f"Net change: {len(new_polymaker) - len(current_polymaker):+d}\n\n")
        
        f.write("NEW FILAMENTS (sample of first 20):\n")
        f.write("-" * 100 + "\n")
        for i, filament in enumerate(new_polymaker[:20], 1):
            finish_str = f" {filament['finish']}" if filament['finish'] else ""
            f.write(f"{i:3d}. {filament['type']}{finish_str} - {filament['color']} ({filament['hex']})\n")
        
        if len(new_polymaker) > 20:
            f.write(f"\n... and {len(new_polymaker) - 20} more\n")
    
    print(f"\n📝 Preview saved to: {preview_file}")
    print(f"\n✅ Ready to update! Review the preview and extracted JSON before proceeding.")
    
    return 0


if __name__ == '__main__':
    exit(main())

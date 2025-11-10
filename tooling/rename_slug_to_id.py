#!/usr/bin/env python3
"""
Rename 'slug' field to 'id' and move it to first position in filaments.json.
"""

import json
from pathlib import Path


def main():
    data_file = Path('color_tools/data/filaments.json')
    
    print("=" * 100)
    print("RENAME slug → id AND REORDER FIELDS")
    print("=" * 100)
    print()
    
    # Load data
    print(f"📖 Loading: {data_file}")
    filaments = json.load(open(data_file, encoding='utf-8'))
    print(f"   Total filaments: {len(filaments)}")
    print()
    
    # Rename and reorder
    print("🔧 Renaming 'slug' to 'id' and reordering fields...")
    reordered = []
    for f in filaments:
        # Create new dict with desired field order: id first, then rest
        new_filament = {
            'id': f['slug'],  # Rename slug → id
            'maker': f['maker'],
            'type': f['type'],
            'finish': f.get('finish'),
            'color': f['color'],
            'hex': f['hex'],
            'td_value': f.get('td_value')
        }
        reordered.append(new_filament)
    
    print()
    print("Sample (first filament):")
    print(json.dumps(reordered[0], indent=2))
    print()
    
    # Save
    print(f"💾 Saving: {data_file}")
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(reordered, f, indent=2, ensure_ascii=False)
    
    print()
    print("=" * 100)
    print("✅ COMPLETE!")
    print("=" * 100)
    print()
    print("Next steps:")
    print("  1. Regenerate data integrity hash")
    print("  2. Test that loading works with 'id' field")


if __name__ == '__main__':
    main()

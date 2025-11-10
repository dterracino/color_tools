#!/usr/bin/env python3
"""
Merge the new Bambu Lab filament data into filaments.json.
"""

import json
from pathlib import Path


def main():
    """Merge new filaments into main filaments.json file."""
    
    # Paths
    tooling_dir = Path(__file__).parent
    new_filaments_path = tooling_dir / 'bambu_new_filaments.json'
    main_filaments_path = tooling_dir.parent / 'color_tools' / 'data' / 'filaments.json'
    
    # Load both files
    print(f"📖 Loading new filaments from: {new_filaments_path}")
    with open(new_filaments_path, 'r', encoding='utf-8') as f:
        new_filaments = json.load(f)
    print(f"   Found {len(new_filaments)} new entries")
    
    print(f"\n📖 Loading existing filaments from: {main_filaments_path}")
    with open(main_filaments_path, 'r', encoding='utf-8') as f:
        existing_filaments = json.load(f)
    print(f"   Found {len(existing_filaments)} existing entries")
    
    # Merge
    print(f"\n🔀 Merging filaments...")
    merged_filaments = existing_filaments + new_filaments
    print(f"   Total after merge: {len(merged_filaments)}")
    
    # Create backup
    backup_path = main_filaments_path.with_suffix('.json.backup')
    print(f"\n💾 Creating backup: {backup_path}")
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(existing_filaments, f, indent=2, ensure_ascii=False)
    
    # Write merged data
    print(f"\n✍️  Writing merged data to: {main_filaments_path}")
    with open(main_filaments_path, 'w', encoding='utf-8') as f:
        json.dump(merged_filaments, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Merge complete!")
    print(f"\nSummary:")
    print(f"  - Previous count: {len(existing_filaments)}")
    print(f"  - New entries: {len(new_filaments)}")
    print(f"  - Total count: {len(merged_filaments)}")
    print(f"  - Backup saved: {backup_path.name}")
    
    print(f"\n⚠️  IMPORTANT: You need to regenerate data file hashes!")
    print(f"   Run: python -m color_tools --verify-data")
    print(f"   This will fail, then update constants.py with new hash")


if __name__ == '__main__':
    main()

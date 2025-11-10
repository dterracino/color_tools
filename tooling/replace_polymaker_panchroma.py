#!/usr/bin/env python3
"""
Replace Polymaker and Panchroma data in filaments.json with corrected extracts.

This script:
1. Loads the current filaments.json
2. Removes all existing Polymaker entries (213)
3. Removes all existing Panchroma entries (143)
4. Adds corrected Polymaker entries (198)
5. Adds corrected Panchroma entries (154)
6. Sorts by maker, type, finish, color
7. Saves the updated database
"""

import json
import shutil
from pathlib import Path
from datetime import datetime


def main():
    # Paths
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    data_dir = project_dir / 'color_tools' / 'data'
    
    current_db_file = data_dir / 'filaments.json'
    backup_file = data_dir / f'filaments.json.backup-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
    
    polymaker_extract = script_dir / 'polymaker_extracted.json'
    panchroma_extract = script_dir / 'panchroma_extracted.json'
    
    print("=" * 100)
    print("REPLACE POLYMAKER & PANCHROMA DATA")
    print("=" * 100)
    print()
    
    # Load current database
    print(f"📖 Loading current database: {current_db_file}")
    current_filaments = json.load(open(current_db_file, encoding='utf-8'))
    print(f"   Total filaments: {len(current_filaments)}")
    
    # Count by maker
    polymaker_current = [f for f in current_filaments if f['maker'] == 'Polymaker']
    panchroma_current = [f for f in current_filaments if f['maker'] == 'Panchroma']
    other_filaments = [f for f in current_filaments if f['maker'] not in ['Polymaker', 'Panchroma']]
    
    print(f"   Polymaker: {len(polymaker_current)}")
    print(f"   Panchroma: {len(panchroma_current)}")
    print(f"   Other makers: {len(other_filaments)}")
    print()
    
    # Load extracted data
    print(f"📖 Loading extracted Polymaker: {polymaker_extract}")
    polymaker_new = json.load(open(polymaker_extract, encoding='utf-8'))
    print(f"   New Polymaker: {len(polymaker_new)}")
    print()
    
    print(f"📖 Loading extracted Panchroma: {panchroma_extract}")
    panchroma_new = json.load(open(panchroma_extract, encoding='utf-8'))
    print(f"   New Panchroma: {len(panchroma_new)}")
    print()
    
    # Create backup
    print(f"💾 Creating backup: {backup_file}")
    shutil.copy2(current_db_file, backup_file)
    print()
    
    # Combine data
    print("🔧 Combining data...")
    print(f"   Keeping {len(other_filaments)} filaments from other makers")
    print(f"   Removing {len(polymaker_current)} old Polymaker filaments")
    print(f"   Adding {len(polymaker_new)} new Polymaker filaments")
    print(f"   Removing {len(panchroma_current)} old Panchroma filaments")
    print(f"   Adding {len(panchroma_new)} new Panchroma filaments")
    print()
    
    new_filaments = other_filaments + polymaker_new + panchroma_new
    
    # Sort by maker, type, finish, color
    print("📋 Sorting filaments...")
    new_filaments.sort(key=lambda f: (
        f['maker'],
        f['type'],
        f.get('finish') or '',  # Put null finishes first
        f['color']
    ))
    print()
    
    # Calculate statistics
    old_total = len(current_filaments)
    new_total = len(new_filaments)
    diff = new_total - old_total
    
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Old total: {old_total}")
    print(f"New total: {new_total}")
    print(f"Change: {diff:+d}")
    print()
    
    # Breakdown by maker
    from collections import Counter
    maker_counts = Counter(f['maker'] for f in new_filaments)
    print("New database by maker:")
    for maker in sorted(maker_counts.keys()):
        print(f"  {maker}: {maker_counts[maker]}")
    print()
    
    # Save
    print(f"💾 Saving updated database: {current_db_file}")
    with open(current_db_file, 'w', encoding='utf-8') as f:
        json.dump(new_filaments, f, indent=2, ensure_ascii=False)
    print()
    
    print("=" * 100)
    print("✅ COMPLETE!")
    print("=" * 100)
    print()
    print("Next steps:")
    print("  1. Regenerate data integrity hash in constants.py")
    print("  2. Run tests to verify everything still works")
    print("  3. Test CLI commands with updated data")
    print()
    print(f"Backup saved to: {backup_file}")


if __name__ == '__main__':
    main()

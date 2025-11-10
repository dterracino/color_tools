#!/usr/bin/env python3
"""
Check for duplicate entries in filaments.json.

A duplicate is defined as having the same combination of:
- maker
- type
- finish
- color

This script will report any duplicates found and optionally show
near-duplicates (same maker/type/color but different finish).
"""

import json
from pathlib import Path
from collections import defaultdict


def check_duplicates(filaments_path: Path) -> None:
    """
    Check for duplicate filament entries.
    
    Args:
        filaments_path: Path to filaments.json file
    """
    print(f"📖 Loading filaments from: {filaments_path}")
    with open(filaments_path, 'r', encoding='utf-8') as f:
        filaments = json.load(f)
    
    print(f"   Total filaments: {len(filaments)}\n")
    
    # Track exact duplicates (maker + type + finish + color)
    exact_duplicates = defaultdict(list)
    
    # Track near-duplicates (maker + type + color, different finish)
    near_duplicates = defaultdict(list)
    
    for idx, filament in enumerate(filaments):
        maker = filament['maker']
        ftype = filament['type']
        finish = filament.get('finish')
        color = filament['color']
        hex_code = filament['hex']
        
        # Check exact duplicates (all fields match)
        exact_key = (maker, ftype, finish, color)
        exact_duplicates[exact_key].append({
            'index': idx,
            'hex': hex_code,
            'filament': filament
        })
        
        # Check near-duplicates (same maker/type/color, different finish)
        near_key = (maker, ftype, color)
        near_duplicates[near_key].append({
            'index': idx,
            'finish': finish,
            'hex': hex_code,
            'filament': filament
        })
    
    # Report exact duplicates
    print("=" * 80)
    print("EXACT DUPLICATES (same maker, type, finish, and color)")
    print("=" * 80)
    
    exact_found = False
    for key, entries in exact_duplicates.items():
        if len(entries) > 1:
            exact_found = True
            maker, ftype, finish, color = key
            print(f"\n❌ DUPLICATE: {maker} - {ftype} {finish or ''} - {color}")
            for entry in entries:
                print(f"   Index {entry['index']:4d}: Hex {entry['hex']}")
    
    if not exact_found:
        print("\n✅ No exact duplicates found!")
    
    # Report near-duplicates (informational)
    print(f"\n{'=' * 80}")
    print("NEAR-DUPLICATES (same maker, type, color - different finish)")
    print("=" * 80)
    print("(These may be intentional - e.g., Matte vs Silk finish)\n")
    
    near_found = False
    for key, entries in near_duplicates.items():
        if len(entries) > 1:
            # Only show if finishes are actually different
            finishes = set(e['finish'] for e in entries)
            if len(finishes) > 1:
                near_found = True
                maker, ftype, color = key
                print(f"\n⚠️  {maker} - {ftype} - {color}")
                for entry in entries:
                    finish_str = entry['finish'] or 'None'
                    print(f"   Index {entry['index']:4d}: Finish={finish_str:15s} Hex={entry['hex']}")
    
    if not near_found:
        print("✅ No near-duplicates found!")
    
    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print("=" * 80)
    
    exact_count = sum(1 for entries in exact_duplicates.values() if len(entries) > 1)
    near_count = sum(1 for entries in near_duplicates.values() 
                     if len(entries) > 1 and len(set(e['finish'] for e in entries)) > 1)
    
    print(f"Total filaments analyzed: {len(filaments)}")
    print(f"Exact duplicate groups: {exact_count}")
    print(f"Near-duplicate groups: {near_count}")
    
    if exact_count > 0:
        print(f"\n⚠️  WARNING: Found {exact_count} exact duplicate group(s)!")
        print("   These should likely be removed from filaments.json")
    else:
        print("\n✅ No exact duplicates - database is clean!")


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    filaments_path = script_dir.parent / 'color_tools' / 'data' / 'filaments.json'
    
    if not filaments_path.exists():
        print(f"❌ Error: filaments.json not found at {filaments_path}")
        return 1
    
    check_duplicates(filaments_path)
    return 0


if __name__ == '__main__':
    exit(main())

#!/usr/bin/env python3
"""Compare current Panchroma filaments vs newly extracted from PDF."""

import json
from pathlib import Path
from collections import Counter


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    
    # Load current database
    current_db = json.load(open(project_dir / 'color_tools' / 'data' / 'filaments.json'))
    current_panchroma = [f for f in current_db if f['maker'] == 'Panchroma']
    
    # Load extracted data
    extracted = json.load(open(script_dir / 'panchroma_extracted.json'))
    
    print("=" * 100)
    print("PANCHROMA DATA COMPARISON")
    print("=" * 100)
    print(f"\nCurrent Panchroma filaments in database: {len(current_panchroma)}")
    print(f"Newly extracted from PDF: {len(extracted)}")
    print(f"Difference: {len(extracted) - len(current_panchroma):+d}")
    
    # Compare types
    print("\n" + "=" * 100)
    print("FILAMENT TYPES COMPARISON")
    print("=" * 100)
    
    current_types = Counter(f['type'] for f in current_panchroma)
    new_types = Counter(f['type'] for f in extracted)
    
    all_types = sorted(set(list(current_types.keys()) + list(new_types.keys())))
    
    print(f"\n{'Type':<20} {'Current':<10} {'New':<10} {'Change'}")
    print("-" * 60)
    
    for ftype in all_types:
        curr = current_types.get(ftype, 0)
        new = new_types.get(ftype, 0)
        diff = new - curr
        
        if curr == 0:
            change = "NEW"
        elif new == 0:
            change = "REMOVED"
        else:
            change = f"{diff:+d}"
        
        print(f"{ftype:<20} {curr:<10} {new:<10} {change}")
    
    # Compare finishes
    print("\n" + "=" * 100)
    print("FINISH COMPARISON")
    print("=" * 100)
    
    current_finishes = Counter(f.get('finish') for f in current_panchroma)
    new_finishes = Counter(f.get('finish') for f in extracted)
    
    all_finishes = sorted(set(list(current_finishes.keys()) + list(new_finishes.keys())), key=lambda x: (x is None, x))
    
    print(f"\n{'Finish':<20} {'Current':<10} {'New':<10} {'Change'}")
    print("-" * 60)
    
    for finish in all_finishes:
        curr = current_finishes.get(finish, 0)
        new = new_finishes.get(finish, 0)
        diff = new - curr
        
        if curr == 0:
            change = "NEW"
        elif new == 0:
            change = "REMOVED"
        else:
            change = f"{diff:+d}"
        
        print(f"{str(finish):<20} {curr:<10} {new:<10} {change}")
    
    # Show sample extracted entries
    print("\n" + "=" * 100)
    print("SAMPLE EXTRACTED ENTRIES")
    print("=" * 100)
    
    import pprint
    pprint.pprint(extracted[:5], width=100)
    
    print("\n✅ Review complete!")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Check for duplicates in extracted Polymaker and Panchroma data."""

import json
from collections import Counter
from pathlib import Path


def main():
    script_dir = Path(__file__).parent
    
    # Load extracted data
    poly = json.load(open(script_dir / 'polymaker_extracted.json'))
    pan = json.load(open(script_dir / 'panchroma_extracted.json'))
    
    print("=" * 100)
    print("POLYMAKER DUPLICATE CHECK")
    print("=" * 100)
    
    # Check for duplicates based on maker/type/finish/color
    poly_keys = [(f['maker'], f['type'], f.get('finish'), f['color']) for f in poly]
    poly_counts = Counter(poly_keys)
    poly_dups = {k: v for k, v in poly_counts.items() if v > 1}
    
    print(f"\nTotal Polymaker filaments: {len(poly)}")
    print(f"Unique combinations: {len(poly_counts)}")
    print(f"Duplicates found: {len(poly_dups)}")
    
    if poly_dups:
        print("\nDuplicate entries:")
        for key, count in sorted(poly_dups.items()):
            finish_str = key[2] if key[2] else "(no finish)"
            print(f"  {count}x: {key[0]} {key[1]} {finish_str} - {key[3]}")
    else:
        print("\n✅ No duplicates found!")
    
    print("\n" + "=" * 100)
    print("PANCHROMA DUPLICATE CHECK")
    print("=" * 100)
    
    # Check for duplicates based on maker/type/finish/color
    pan_keys = [(f['maker'], f['type'], f.get('finish'), f['color']) for f in pan]
    pan_counts = Counter(pan_keys)
    pan_dups = {k: v for k, v in pan_counts.items() if v > 1}
    
    print(f"\nTotal Panchroma filaments: {len(pan)}")
    print(f"Unique combinations: {len(pan_counts)}")
    print(f"Duplicates found: {len(pan_dups)}")
    
    if pan_dups:
        print("\nDuplicate entries:")
        for key, count in sorted(pan_dups.items()):
            finish_str = key[2] if key[2] else "(no finish)"
            print(f"  {count}x: {key[0]} {key[1]} {finish_str} - {key[3]}")
    else:
        print("\n✅ No duplicates found!")


if __name__ == '__main__':
    main()

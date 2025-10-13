#!/usr/bin/env python3
"""
Simple viewer for the extracted Prusament validation data.

Usage:
    python3 view_validation_data.py [--type TYPE] [--finish FINISH] [--color COLOR]
"""

import json
import argparse
from collections import Counter


def main():
    parser = argparse.ArgumentParser(description='View Prusament validation data')
    parser.add_argument('--type', help='Filter by filament type (e.g., PLA, PETG)')
    parser.add_argument('--finish', help='Filter by finish (e.g., Blend, Galaxy)')
    parser.add_argument('--color', help='Filter by color name')
    parser.add_argument('--stats', action='store_true', help='Show statistics only')
    args = parser.parse_args()
    
    # Load data
    with open('prusament_validation_extracted.json', 'r') as f:
        records = json.load(f)
    
    # Apply filters
    filtered = records
    if args.type:
        filtered = [r for r in filtered if r['type'].lower() == args.type.lower()]
    if args.finish:
        filtered = [r for r in filtered if r['finish'] and r['finish'].lower() == args.finish.lower()]
    if args.color:
        filtered = [r for r in filtered if args.color.lower() in r['color'].lower()]
    
    if args.stats:
        # Show statistics
        print(f"Total records: {len(filtered)}")
        print()
        
        types = Counter(r['type'] for r in filtered)
        print("Types:")
        for t, count in sorted(types.items()):
            print(f"  {t}: {count}")
        print()
        
        finishes = Counter(r['finish'] for r in filtered if r['finish'])
        print("Finishes:")
        print(f"  None: {sum(1 for r in filtered if r['finish'] is None)}")
        for f, count in sorted(finishes.items()):
            print(f"  {f}: {count}")
    else:
        # Show records
        print(f"Found {len(filtered)} record(s):\n")
        
        for i, rec in enumerate(filtered, 1):
            finish_str = rec['finish'] if rec['finish'] else 'None'
            td_str = str(rec['td_value']) if rec['td_value'] is not None else 'N/A'
            
            print(f"{i}. {rec['color']}")
            print(f"   Type: {rec['type']} | Finish: {finish_str}")
            print(f"   Hex: {rec['hex']} | TD: {td_str}")
            print(f"   Product: {rec['product']}")
            print()


if __name__ == '__main__':
    main()

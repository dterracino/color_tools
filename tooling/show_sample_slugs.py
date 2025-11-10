#!/usr/bin/env python3
"""Display sample slugs from extracted data."""

import json
import random
from pathlib import Path


def main():
    script_dir = Path(__file__).parent
    
    poly = json.load(open(script_dir / 'polymaker_extracted.json'))
    pan = json.load(open(script_dir / 'panchroma_extracted.json'))
    
    print("=" * 100)
    print("POLYMAKER - 5 Random Samples with Slugs")
    print("=" * 100)
    
    for f in random.sample(poly, 5):
        print(f"\n🏷️  {f['slug']}")
        print(f"   Type: {f['type']} | Finish: {f.get('finish') or '(none)'} | Color: {f['color']}")
        print(f"   Hex: {f['hex']}")
    
    print("\n" + "=" * 100)
    print("PANCHROMA - 5 Random Samples with Slugs")
    print("=" * 100)
    
    for f in random.sample(pan, 5):
        print(f"\n🏷️  {f['slug']}")
        print(f"   Type: {f['type']} | Finish: {f.get('finish') or '(none)'} | Color: {f['color']}")
        print(f"   Hex: {f['hex']}")


if __name__ == '__main__':
    main()

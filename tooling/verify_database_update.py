#!/usr/bin/env python3
"""Verify the corrected Polymaker data is in the database."""

import json
from collections import Counter

d = json.load(open('color_tools/data/filaments.json'))
poly = [f for f in d if f['maker'] == 'Polymaker']

types = Counter(f['type'] for f in poly)

print("Polymaker types in database:")
for t, c in sorted(types.items()):
    print(f"  {t}: {c}")

print("\nVerifying specialized types from extraction:")
print(f"  ✓ PC-ABS: {types.get('PC-ABS', 0)}")
print(f"  ✓ PA6-CF20: {types.get('PA6-CF20', 0)}")
print(f"  ✓ LW-PLA: {types.get('LW-PLA', 0)}")
print(f"  ✓ PC-PBT: {types.get('PC-PBT', 0)}")
print(f"  ✓ CoPA: {types.get('CoPA', 0)}")

print("\nPanchroma verification:")
pan = [f for f in d if f['maker'] == 'Panchroma']
print(f"Total Panchroma: {len(pan)}")
dual_silk = [f for f in pan if f.get('finish') == 'Dual Silk']
print(f"Dual Silk filaments: {len(dual_silk)}")
if dual_silk:
    print(f"Sample dual-color hex: {dual_silk[0]['hex']}")
    print(f"Sample dual-color name: {dual_silk[0]['color']}")

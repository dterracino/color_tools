#!/usr/bin/env python3
"""Show collision examples from slugged database."""

import json

d = json.load(open('tooling/filaments_with_slugs.json'))

# Find all Black Polymaker PLA with no finish (the biggest collision)
black_poly = [f for f in d if f['maker'] == 'Polymaker' 
              and f['type'] == 'PLA' 
              and f.get('finish') is None 
              and f['color'] == 'Black']

print("=" * 100)
print("COLLISION EXAMPLE: Polymaker PLA (no finish) Black")
print("=" * 100)
print()
for i, f in enumerate(black_poly, 1):
    print(f"{i}. {f['slug']}")
    print(f"   hex: {f['hex']}, td: {f.get('td_value')}")
print()

# Show some Silk+ examples
silk_plus = [f for f in d if f.get('finish') == 'Silk+'][:3]
print("=" * 100)
print("SILK+ SLUG EXAMPLES")
print("=" * 100)
print()
for f in silk_plus:
    print(f"{f['slug']}")
    print(f"  {f['maker']} {f['type']} {f['finish']} - {f['color']}")
print()

# Show some PLA+ examples
pla_plus = [f for f in d if f.get('type') == 'PLA+'][:3]
print("=" * 100)
print("PLA+ SLUG EXAMPLES")
print("=" * 100)
print()
for f in pla_plus:
    finish_str = f.get('finish') or '(none)'
    print(f"{f['slug']}")
    print(f"  {f['maker']} {f['type']} {finish_str} - {f['color']}")
print()

# Random sample
import random
print("=" * 100)
print("RANDOM SAMPLE (5 filaments)")
print("=" * 100)
print()
for f in random.sample(d, 5):
    print(f"{f['slug']}")
    finish_str = f.get('finish') or '(none)'
    print(f"  {f['maker']} | {f['type']} | {finish_str} | {f['color']}")
    print()

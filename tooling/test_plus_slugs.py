#!/usr/bin/env python3
"""Test that + is converted to -plus in slugs."""

import json
import re


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    # Replace + with -plus (e.g., "PLA+" -> "pla-plus", "Silk+" -> "silk-plus")
    text = text.replace('+', '-plus')
    # Remove other special chars
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


print("Testing slugify with + character:")
print()
print(f"  'PLA+' -> '{slugify('PLA+')}'")
print(f"  'Silk+' -> '{slugify('Silk+')}'")
print(f"  'PETG+' -> '{slugify('PETG+')}'")
print()

# Test with actual filament data
d = json.load(open('color_tools/data/filaments.json'))
silk_plus = [f for f in d if f.get('finish') == 'Silk+']
pla_plus = [f for f in d if f.get('type') == 'PLA+']

if silk_plus:
    f = silk_plus[0]
    print("Sample Silk+ filament:")
    print(f"  Maker: {f['maker']}")
    print(f"  Type: {f['type']}")
    print(f"  Finish: {f['finish']}")
    print(f"  Color: {f['color']}")
    slug = f"{slugify(f['maker'])}-{slugify(f['type'])}-{slugify(f['finish'])}-{slugify(f['color'])}"
    print(f"  Generated slug: {slug}")
    print()

if pla_plus:
    f = pla_plus[0]
    print("Sample PLA+ filament:")
    print(f"  Maker: {f['maker']}")
    print(f"  Type: {f['type']}")
    print(f"  Finish: {f.get('finish', '(none)')}")
    print(f"  Color: {f['color']}")
    parts = [slugify(f['maker']), slugify(f['type'])]
    if f.get('finish'):
        parts.append(slugify(f['finish']))
    parts.append(slugify(f['color']))
    slug = '-'.join(parts)
    print(f"  Generated slug: {slug}")

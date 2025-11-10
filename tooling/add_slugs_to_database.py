#!/usr/bin/env python3
"""
Add slug IDs to all filaments in filaments.json.

This script reads the current filaments database and adds a unique slug
to each filament using the format: maker-type-finish-color
"""

import json
import re
from pathlib import Path
from collections import defaultdict


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    # Replace + with -plus (e.g., "PLA+" -> "pla-plus", "Silk+" -> "silk-plus")
    text = text.replace('+', '-plus')
    # Remove other special chars
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def generate_slug(filament: dict) -> str:
    """Generate a slug ID for a filament."""
    parts = [slugify(filament['maker']), slugify(filament['type'])]
    if filament.get('finish'):
        parts.append(slugify(filament['finish']))
    parts.append(slugify(filament['color']))
    return '-'.join(parts)


def main():
    # Paths
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    data_file = project_dir / 'color_tools' / 'data' / 'filaments.json'
    backup_file = project_dir / 'color_tools' / 'data' / 'filaments.json.backup'
    output_file = script_dir / 'filaments_with_slugs.json'
    
    print("=" * 100)
    print("ADDING SLUGS TO FILAMENTS DATABASE")
    print("=" * 100)
    print()
    
    # Load current database
    print(f"📖 Loading: {data_file}")
    filaments = json.load(open(data_file, encoding='utf-8'))
    print(f"   Total filaments: {len(filaments)}")
    print()
    
    # Generate slugs with collision detection
    print("🏷️  Generating slugs...")
    slug_counts = defaultdict(int)
    slugs_by_maker = defaultdict(int)
    
    for filament in filaments:
        base_slug = generate_slug(filament)
        slug_counts[base_slug] += 1
        slugs_by_maker[filament['maker']] += 1
        
        if slug_counts[base_slug] > 1:
            filament['slug'] = f"{base_slug}-{slug_counts[base_slug]}"
        else:
            filament['slug'] = base_slug
    
    # Statistics
    total_slugs = len(filaments)
    unique_base_slugs = len(slug_counts)
    collisions = sum(1 for count in slug_counts.values() if count > 1)
    total_collision_instances = sum(count - 1 for count in slug_counts.values() if count > 1)
    
    print()
    print("=" * 100)
    print("SLUG GENERATION STATISTICS")
    print("=" * 100)
    print(f"Total filaments: {total_slugs}")
    print(f"Unique base slugs: {unique_base_slugs}")
    print(f"Collision patterns: {collisions}")
    print(f"Filaments with -2, -3, etc. suffix: {total_collision_instances}")
    print()
    
    print("Slugs by maker:")
    for maker in sorted(slugs_by_maker.keys()):
        print(f"  {maker}: {slugs_by_maker[maker]}")
    print()
    
    # Show collision examples if any
    if collisions > 0:
        print("Sample collision patterns:")
        collision_examples = [(slug, count) for slug, count in slug_counts.items() if count > 1]
        for slug, count in sorted(collision_examples[:5]):
            print(f"  {slug}: {count} instances")
        print()
    
    # Save to temporary file for review
    print(f"💾 Saving to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filaments, f, indent=2, ensure_ascii=False)
    
    print()
    print("=" * 100)
    print("✅ COMPLETE - Review the output file before updating the main database")
    print("=" * 100)
    print()
    print("Next steps:")
    print("  1. Review: tooling/filaments_with_slugs.json")
    print("  2. If satisfied, update color_tools/data/filaments.json with the slugged version")
    print("  3. Regenerate data integrity hash in constants.py")


if __name__ == '__main__':
    main()

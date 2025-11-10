#!/usr/bin/env python3
"""
Generate slug IDs for all filaments and output them for review.

This script creates potential slug IDs using the format:
{maker-slug}-{type-slug}-{finish-slug}-{color-slug}

Finish is omitted if null. Collisions are handled with -2, -3 suffixes.
"""

import json
import re
from pathlib import Path
from collections import defaultdict


def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug.
    
    Args:
        text: Input text to slugify
    
    Returns:
        Lowercase slug with hyphens
    """
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and special chars with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text


def generate_slug(filament: dict, include_finish: bool = True) -> str:
    """
    Generate a slug ID for a filament.
    
    Args:
        filament: Filament dictionary
        include_finish: Whether to include finish in slug (if it exists)
    
    Returns:
        Slug string
    """
    parts = [
        slugify(filament['maker']),
        slugify(filament['type']),
    ]
    
    # Add finish if it exists and we want to include it
    if include_finish and filament.get('finish'):
        parts.append(slugify(filament['finish']))
    
    # Add color
    parts.append(slugify(filament['color']))
    
    return '-'.join(parts)


def generate_all_slugs(filaments: list) -> list[dict]:
    """
    Generate slugs for all filaments with collision detection.
    
    Args:
        filaments: List of filament dictionaries
    
    Returns:
        List of dicts with original data + slug
    """
    results = []
    slug_counts = defaultdict(int)
    
    for idx, filament in enumerate(filaments):
        # Generate base slug
        base_slug = generate_slug(filament, include_finish=True)
        
        # Handle collisions
        if slug_counts[base_slug] == 0:
            # First occurrence
            final_slug = base_slug
        else:
            # Collision - add numeric suffix
            final_slug = f"{base_slug}-{slug_counts[base_slug] + 1}"
        
        slug_counts[base_slug] += 1
        
        results.append({
            'index': idx,
            'slug': final_slug,
            'maker': filament['maker'],
            'type': filament['type'],
            'finish': filament.get('finish'),
            'color': filament['color'],
            'hex': filament['hex']
        })
    
    return results


def main():
    """Generate and output slug preview."""
    
    # Load filaments
    filaments_path = Path(__file__).parent.parent / 'color_tools' / 'data' / 'filaments.json'
    print(f"📖 Loading filaments from: {filaments_path}")
    
    with open(filaments_path, 'r', encoding='utf-8') as f:
        filaments = json.load(f)
    
    print(f"   Total filaments: {len(filaments)}\n")
    
    # Generate slugs
    print("🔨 Generating slugs...")
    results = generate_all_slugs(filaments)
    
    # Write to output file (human-readable format)
    output_txt = Path(__file__).parent / 'filament_slugs_preview.txt'
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("FILAMENT SLUG PREVIEW\n")
        f.write("=" * 100 + "\n\n")
        
        for item in results:
            finish_str = item['finish'] if item['finish'] else 'None'
            f.write(f"[{item['index']:3d}] {item['slug']}\n")
            f.write(f"      {item['maker']} | {item['type']} | {finish_str} | {item['color']} | {item['hex']}\n")
            f.write("\n")
    
    # Also write JSON version for programmatic use
    output_json = Path(__file__).parent / 'filament_slugs_preview.json'
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Generated {len(results)} slugs\n")
    print(f"📝 Text preview saved to: {output_txt}")
    print(f"📝 JSON data saved to: {output_json}")
    
    # Show statistics
    slug_counts = defaultdict(int)
    for item in results:
        base_slug = item['slug'].rsplit('-', 1)[0] if item['slug'][-1].isdigit() and '-' in item['slug'][-3:] else item['slug']
        slug_counts[base_slug] += 1
    
    collisions = {slug: count for slug, count in slug_counts.items() if count > 1}
    
    print(f"\n📊 Statistics:")
    print(f"   Total slugs: {len(results)}")
    print(f"   Unique base slugs: {len(slug_counts)}")
    print(f"   Slugs with collisions: {len(collisions)}")
    
    if collisions:
        print(f"\n⚠️  Top 10 collisions:")
        sorted_collisions = sorted(collisions.items(), key=lambda x: x[1], reverse=True)
        for slug, count in sorted_collisions[:10]:
            print(f"   {slug}: {count} entries")


if __name__ == '__main__':
    main()

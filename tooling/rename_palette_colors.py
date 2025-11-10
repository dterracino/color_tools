"""
Rename palette colors using intelligent color naming.

This script updates all palette JSON files with better descriptive names
generated from RGB values.
"""

import json
from pathlib import Path
from color_tools.naming import generate_color_name


def rename_palette_colors(palette_path: Path) -> dict:
    """
    Rename all colors in a palette file using intelligent naming.
    
    Args:
        palette_path: Path to palette JSON file
        
    Returns:
        Dictionary with stats: exact_matches, near_matches, generated_names
    """
    print(f"\nProcessing {palette_path.name}...")
    
    # Load palette
    with open(palette_path, 'r', encoding='utf-8') as f:
        colors = json.load(f)
    
    # Collect all RGB values for near-match uniqueness checking
    all_rgbs = [tuple(c['rgb']) for c in colors]
    
    # Stats tracking
    stats = {
        'exact': 0,
        'near': 0,
        'generated': 0,
        'renamed': 0
    }
    
    # Rename each color
    for color in colors:
        old_name = color['name']
        rgb = tuple(color['rgb'])
        
        # Generate new name
        new_name, match_type = generate_color_name(rgb, palette_colors=all_rgbs)
        
        # Update stats
        stats[match_type] += 1
        if new_name != old_name:
            stats['renamed'] += 1
            print(f"  {old_name:30} → {new_name}")
        
        # Update color name
        color['name'] = new_name
    
    # Save updated palette
    with open(palette_path, 'w', encoding='utf-8') as f:
        json.dump(colors, f, indent=2, ensure_ascii=False)
    
    print(f"  Stats: {stats['exact']} exact, {stats['near']} near, {stats['generated']} generated")
    print(f"  Renamed: {stats['renamed']}/{len(colors)} colors")
    
    return stats


def main():
    """Rename colors in all palette files."""
    palettes_dir = Path('color_tools/data/palettes')
    
    if not palettes_dir.exists():
        print(f"Error: Palettes directory not found: {palettes_dir}")
        return
    
    total_stats = {
        'exact': 0,
        'near': 0,
        'generated': 0,
        'renamed': 0,
        'total_colors': 0
    }
    
    # Process each palette file
    palette_files = sorted(palettes_dir.glob('*.json'))
    
    for palette_file in palette_files:
        stats = rename_palette_colors(palette_file)
        
        # Accumulate stats
        for key in ['exact', 'near', 'generated', 'renamed']:
            total_stats[key] += stats[key]
        total_stats['total_colors'] += stats['exact'] + stats['near'] + stats['generated']
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total colors processed: {total_stats['total_colors']}")
    print(f"  Exact CSS matches: {total_stats['exact']}")
    print(f"  Near CSS matches: {total_stats['near']}")
    print(f"  Generated names: {total_stats['generated']}")
    print(f"  Total renamed: {total_stats['renamed']}")
    print(f"Processed {len(palette_files)} palette files")


if __name__ == '__main__':
    main()

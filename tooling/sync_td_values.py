#!/usr/bin/env python3
"""
Sync TD (transmissivity) values from HueForge personal library to color_tools database.

This script reads the HueForge personal filament library and updates any missing
td_value fields in the color_tools.json database. It uses fuzzywuzzy for
intelligent fuzzy matching to handle naming differences between the databases.

Usage:
    python sync_td_values.py [--hueforge-path PATH] [--dry-run] [--verbose]
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from fuzzywuzzy import fuzz, process
except ImportError:
    print("Error: fuzzywuzzy is required for this script.")
    print("Install it with: pip install fuzzywuzzy")
    exit(1)


def calculate_similarity(target_filament: Dict, source_filament: Dict) -> float:
    """
    Calculate overall similarity between two filaments using fuzzywuzzy.
    
    Returns a score from 0.0 to 1.0 where 1.0 is a perfect match.
    Uses weighted combination of brand, type, and color similarities.
    """
    # Normalize strings for comparison
    target_brand = normalize_brand_name(target_filament['maker'])
    target_type = normalize_type_name(target_filament['type'])
    target_color = normalize_color_name(target_filament['color'])
    
    source_brand = normalize_brand_name(source_filament['Brand'])
    source_type = normalize_type_name(source_filament['Type'])
    source_color = normalize_color_name(source_filament['Name'])
    
    # Calculate individual similarities using fuzzywuzzy
    brand_sim = fuzz.ratio(target_brand, source_brand) / 100.0
    type_sim = fuzz.ratio(target_type, source_type) / 100.0
    color_sim = fuzz.ratio(target_color, source_color) / 100.0
    
    # Weighted average: brand and color are most important
    # Brand: 40%, Color: 40%, Type: 20%
    overall_similarity = (brand_sim * 0.4) + (color_sim * 0.4) + (type_sim * 0.2)
    
    return overall_similarity


def normalize_brand_name(brand: str) -> str:
    """Normalize brand names for better matching."""
    # Handle common variations
    brand_lower = brand.lower()
    
    # Map common variations
    brand_mappings = {
        'bambulab': 'bambu lab',
        'bambu lab basic': 'bambu lab',
        'bambulab basic': 'bambu lab',
        'bambulab matte': 'bambu lab',
        'bbl (gs)': 'bambu lab',
        'bbL (gs)': 'bambu lab',
        'polylite': 'polymaker',
        'polylite pro': 'polymaker',
        'polyterra': 'polymaker',
        'esun': 'esun',
        'elegoo rapid': 'elegoo',
        'elegoo (gs)': 'elegoo',
        'creality': 'creality',
        'creality hyper': 'creality',
        'creality ender': 'creality',
        'crealtiy': 'creality',  # Handle typo
        'sunlu elite': 'sunlu',
        'sun (gs)': 'sunlu',
        'anycubic': 'anycubic',
        'iemai': 'iemai',
        'flashforge': 'flashforge',
        'gryddle': 'gryddle',
        'hatchbox': 'hatchbox',
        'paramount3d': 'paramount 3d',
        'paramount 3d': 'paramount 3d',
        'basf ultrafuse': 'basf',
        'voxelab': 'voxelab',
        'hp3df': 'hp3df',
        'kingroon': 'kingroon',
    }
    
    for pattern, replacement in brand_mappings.items():
        if pattern in brand_lower:
            return replacement
    
    return brand_lower


def normalize_color_name(color: str) -> str:
    """Normalize color names for better matching."""
    color_lower = color.lower()
    
    # Handle common variations
    color_mappings = {
        'jade white': 'white',
        'ivory white': 'white',
        'matte white': 'white',
        'meta white': 'white',
        'basic white': 'white',
        'dark gray': 'dark grey',
        'light gray': 'light grey',
        'ash gray': 'ash grey',
        'blue gray': 'blue grey',
        'nardo gray': 'nardo grey',
        'lt gray': 'light grey',
        'dk gray': 'dark grey',
        'space gray': 'space grey',
        'sunflower yellow': 'yellow',
        'bambulab green': 'green',
        'mistletoe green': 'green',
        'bright green': 'green',
        'sea green': 'green',
        'mint green': 'green',
        'grass green': 'green',
        'apple green': 'green',
        'pine green': 'green',
        'maroon red': 'red',
        'dark red': 'red',
        'scarlet red': 'red',
        'army red': 'red',
        'muted red': 'red',
        'basic red': 'red',
        'hot pink': 'pink',
        'cobalt blue': 'blue',
        'marine blue': 'blue',
        'ice blue': 'blue',
        'sky blue': 'blue',
        'basic blue': 'blue',
        'dark blue': 'blue',
        'indigo purple': 'purple',
        'pumpkin orange': 'orange',
        'mandarin orange': 'orange',
        'clear orange': 'orange',
        'burnt titanium': 'titanium',
        'polymaker teal': 'teal',
        'meta cream white': 'white',
        'latte brown': 'brown',
        'dark chocolate': 'brown',
        'desert tan': 'tan',
        'lemon yellow': 'yellow',
        'basic yellow': 'yellow',
        'skin-deep complexion': 'skin',
        'black sparkle': 'black',
        'white sparkle': 'white',
        'metallic silver': 'silver',
    }
    
    for pattern, replacement in color_mappings.items():
        if pattern in color_lower:
            return replacement
    
    return color_lower


def normalize_type_name(type_name: str) -> str:
    """Normalize filament type names."""
    type_lower = type_name.lower()
    
    # Handle variations
    if 'pla' in type_lower:
        if '+' in type_lower or 'plus' in type_lower:
            return 'pla+'
        elif 'meta' in type_lower:
            return 'pla meta'
        else:
            return 'pla'
    elif 'petg' in type_lower:
        return 'petg'
    elif 'abs' in type_lower:
        return 'abs'
    elif 'tpu' in type_lower:
        return 'tpu'
    
    return type_lower


def find_best_match(
    target_filament: Dict,
    hueforge_filaments: List[Dict],
    min_similarity: float = 0.6
) -> Optional[Tuple[Dict, float]]:
    """
    Find the best matching filament from HueForge library.
    
    Returns:
        (matching_filament, similarity_score) or None if no good match
    """
    best_match = None
    best_score = 0.0
    
    for hf_filament in hueforge_filaments:
        # Use the new fuzzywuzzy-based similarity calculation
        score = calculate_similarity(target_filament, hf_filament)
        
        if score > best_score and score >= min_similarity:
            best_score = score
            best_match = hf_filament
    
    return (best_match, best_score) if best_match else None


def load_hueforge_library(hueforge_path: Path) -> List[Dict]:
    """Load the HueForge personal filament library."""
    try:
        with open(hueforge_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('Filaments', [])
    except FileNotFoundError:
        print(f"Error: HueForge library not found at {hueforge_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in HueForge library: {e}")
        return []


def load_color_tools_data(color_tools_path: Path) -> Dict:
    """Load the color_tools.json database."""
    try:
        with open(color_tools_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: color_tools.json not found at {color_tools_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in color_tools.json: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(description="Sync TD values from HueForge library to color_tools database")
    parser.add_argument(
        '--hueforge-path',
        type=Path,
        default=Path(r'P:\HueforgeConfig\Filaments\personal_library.json'),
        help='Path to HueForge personal library JSON file'
    )
    parser.add_argument(
        '--color-tools-path',
        type=Path,
        default=Path('data/color_tools.json'),
        help='Path to color_tools.json file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed matching information'
    )
    parser.add_argument(
        '--min-similarity',
        type=float,
        default=0.6,
        help='Minimum similarity score for matching (0.0-1.0, default: 0.6)'
    )
    
    args = parser.parse_args()
    
    print("TD Value Sync Tool")
    print("=" * 50)
    print(f"HueForge library: {args.hueforge_path}")
    print(f"Color tools database: {args.color_tools_path}")
    print(f"Minimum similarity: {args.min_similarity}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE UPDATE'}")
    print()
    
    # Load data files
    print("Loading data files...")
    hueforge_filaments = load_hueforge_library(args.hueforge_path)
    color_tools_data = load_color_tools_data(args.color_tools_path)
    
    if not hueforge_filaments:
        print("X No HueForge filaments loaded. Exiting.")
        return
    
    if not color_tools_data or 'filaments' not in color_tools_data:
        print("X No color_tools filaments loaded. Exiting.")
        return
    
    print(f"+ Loaded {len(hueforge_filaments)} HueForge filaments")
    print(f"+ Loaded {len(color_tools_data['filaments'])} color_tools filaments")
    
    # Find filaments missing TD values
    missing_td_filaments = [
        f for f in color_tools_data['filaments'] 
        if f.get('td_value') is None
    ]
    
    # Show TD value status
    total_filaments = len(color_tools_data['filaments'])
    existing_td_count = total_filaments - len(missing_td_filaments)
    
    print(f"+ Found {existing_td_count} filaments already have TD values")
    print(f"+ Found {len(missing_td_filaments)} filaments missing TD values")
    print(f"+ Processing {len(missing_td_filaments)} filaments for TD value sync...")
    print()
    
    # Process each missing TD filament
    updates = []
    no_matches = []
    
    for i, filament in enumerate(missing_td_filaments, 1):
        if args.verbose:
            print(f"[{i}/{len(missing_td_filaments)}] Processing: {filament['maker']} {filament['type']} - {filament['color']}")
        elif i % 50 == 0 or i == len(missing_td_filaments):
            print(f"Progress: {i}/{len(missing_td_filaments)} filaments processed...")
        
        match_result = find_best_match(filament, hueforge_filaments, args.min_similarity)
        
        if match_result:
            hf_filament, score = match_result
            td_value = hf_filament.get('Transmissivity')
            
            if td_value is not None:
                if args.verbose:
                    print(f"  + Match found (score: {score:.2f}): {hf_filament['Brand']} {hf_filament['Type']} - {hf_filament['Name']}")
                    print(f"     TD value: {td_value}")
                    print(f"     Target: {normalize_brand_name(filament['maker'])} | {normalize_type_name(filament['type'])} | {normalize_color_name(filament['color'])}")
                    print(f"     Source: {normalize_brand_name(hf_filament['Brand'])} | {normalize_type_name(hf_filament['Type'])} | {normalize_color_name(hf_filament['Name'])}")
                
                updates.append((filament, td_value))
            else:
                if args.verbose:
                    print(f"  ! Match found but no TD value: {hf_filament['Brand']} {hf_filament['Type']} - {hf_filament['Name']}")
        else:
            if args.verbose:
                print(f"  - No suitable match found")
            no_matches.append(filament)
        
        if args.verbose:
            print()
    
    # Summary
    print("SUMMARY")
    print("=" * 50)
    print(f"Filaments missing TD values: {len(missing_td_filaments)}")
    print(f"Successful matches: {len(updates)}")
    print(f"No matches found: {len(no_matches)}")
    print()
    
    if updates:
        print("UPDATES TO APPLY:")
        for filament, td_value in updates:
            print(f"  - {filament['maker']} {filament['type']} - {filament['color']} -> TD: {td_value}")
        print()
    
    if no_matches:
        print("NO MATCHES FOUND:")
        for filament in no_matches:
            print(f"  - {filament['maker']} {filament['type']} - {filament['color']}")
        print()
    
    # Apply updates
    if updates and not args.dry_run:
        print("Applying updates to color_tools.json...")
        
        for filament, td_value in updates:
            filament['td_value'] = td_value
        
        # Write updated data back to file
        try:
            with open(args.color_tools_path, 'w', encoding='utf-8') as f:
                json.dump(color_tools_data, f, indent=2, separators=(',', ': '))
            print(f"+ Successfully updated {len(updates)} filaments!")
        except Exception as e:
            print(f"X Error writing file: {e}")
    elif args.dry_run:
        print("DRY RUN: No changes were made. Use --dry-run=false to apply updates.")
    else:
        print("No updates to apply.")


if __name__ == "__main__":
    main()
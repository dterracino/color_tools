#!/usr/bin/env python3
"""
Extract Prusament filament data from validation JSON files.

This script reads prusament_vallidation_data_page1.json and page2.json,
extracts the relevant information, and generates a JSON file with the format:
{
    "maker": "Prusament",
    "type": "{filament type}",
    "finish": "{filament finish}",
    "color": "{color name}",
    "hex": "#{hex color code}",
    "td_value": {td_value},
    "product": "{complete product name}"
}
"""

import json
import re
from typing import Optional


def extract_type_and_finish(filament_type_name: str) -> tuple[str, Optional[str]]:
    """
    Extract base type and finish from filament_type.name.
    
    Examples:
        "PLA" -> ("PLA", None)
        "PLA Blend" -> ("PLA", "Blend")
        "PC Carbon Fiber Blend" -> ("PC", "Carbon Fiber")
        "PETG Tungsten" -> ("PETG", "Tungsten")
        "PETG V0" -> ("PETG", "V0")
    """
    # Special cases first
    if filament_type_name == "PC Carbon Fiber Blend":
        return ("PC", "Carbon Fiber")
    
    if filament_type_name == "PETG Carbon Fiber":
        return ("PETG", "Carbon Fiber")
    
    # Pattern: "TYPE" or "TYPE Finish"
    parts = filament_type_name.split(maxsplit=1)
    base_type = parts[0]
    finish = parts[1] if len(parts) > 1 else None
    
    return (base_type, finish)


def extract_finish_from_color_name(color_name: str) -> tuple[str, Optional[str]]:
    """
    Extract finish from color name if it starts with a finish keyword.
    
    Examples:
        "Galaxy Purple" -> ("Purple", "Galaxy")
        "Pearl White" -> ("White", "Pearl")
        "Jet Black" -> ("Jet Black", None)  # Jet is part of color name
    """
    finish_keywords = ["Galaxy", "Pearl", "Marble"]
    
    for keyword in finish_keywords:
        if color_name.startswith(keyword + " "):
            remaining = color_name[len(keyword) + 1:]
            return (remaining, keyword)
    
    return (color_name, None)


def extract_product_name(url: str, color_name: str, filament_type_name: str) -> str:
    """
    Extract product name from purchase URL or construct from available data.
    
    Examples:
        URL: "https://www.prusa3d.com/en/product/prusament-pc-blend-jet-black-970g/"
        Returns: "PC Blend Jet Black 970g"
    """
    if not url:
        # Construct from available data
        return f"{filament_type_name} {color_name}"
    
    # Extract the product slug from URL
    parts = url.split('/')
    for part in parts:
        if 'prusament' in part.lower():
            # Remove query params
            slug = part.split('?')[0]
            # Remove 'prusament-' prefix
            slug = slug.replace('prusament-', '')
            # Replace hyphens with spaces and title case
            product = slug.replace('-', ' ').title()
            # Fix known patterns
            product = product.replace(' 1Kg', ' 1kg')
            product = product.replace(' 970G', ' 970g')
            product = product.replace(' 850G', ' 850g')
            product = product.replace(' 800G', ' 800g')
            return product
    
    # Fallback
    return f"{filament_type_name} {color_name}"


def normalize_hex(hex_color: str) -> str:
    """Ensure hex color has # prefix and is uppercase."""
    hex_color = hex_color.strip().upper()
    if not hex_color.startswith('#'):
        hex_color = '#' + hex_color
    return hex_color


def process_record(rec: dict) -> dict:
    """Process a single record from the validation data."""
    filament_type_name = rec['filament_type']['name']
    color_name = rec['color_name']
    hex_color = normalize_hex(rec['hex_color'])
    mfr_link = rec.get('mfr_purchase_link', '')
    
    # Extract type and potential finish from filament type
    base_type, type_finish = extract_type_and_finish(filament_type_name)
    
    # Check if color name contains finish info
    color_clean, color_finish = extract_finish_from_color_name(color_name)
    
    # Determine final finish (prefer color-based finish, then type-based)
    final_finish = color_finish if color_finish else type_finish
    final_color = color_clean if color_finish else color_name
    
    # Extract product name
    product = extract_product_name(mfr_link, color_name, filament_type_name)
    
    return {
        "maker": "Prusament",
        "type": base_type,
        "finish": final_finish,
        "color": final_color,
        "hex": hex_color,
        "td_value": None,  # Not available in validation data
        "product": product
    }


def main():
    # Load both pages
    with open('prusament_vallidation_data_page1.json', 'r') as f:
        page1 = json.load(f)
    
    with open('prusament_vallidation_data_page2.json', 'r') as f:
        page2 = json.load(f)
    
    # Combine results
    all_records = page1['results'] + page2['results']
    
    print(f"Processing {len(all_records)} records...")
    
    # Process each record
    output_records = []
    for rec in all_records:
        try:
            processed = process_record(rec)
            output_records.append(processed)
        except Exception as e:
            print(f"Error processing record {rec.get('id')}: {e}")
            print(f"  Color: {rec.get('color_name')}, Type: {rec.get('filament_type', {}).get('name')}")
    
    # Write output
    output_file = 'prusament_validation_extracted.json'
    with open(output_file, 'w') as f:
        json.dump(output_records, f, indent=2, ensure_ascii=False)
    
    print(f"\nGenerated {len(output_records)} records")
    print(f"Output written to: {output_file}")
    
    # Show statistics
    from collections import Counter
    types = Counter(rec['type'] for rec in output_records)
    finishes = Counter(rec['finish'] for rec in output_records if rec['finish'])
    
    print("\n=== Type Distribution ===")
    for t, count in sorted(types.items()):
        print(f"  {t}: {count}")
    
    print("\n=== Finish Distribution ===")
    print(f"  None: {sum(1 for rec in output_records if rec['finish'] is None)}")
    for f, count in sorted(finishes.items()):
        print(f"  {f}: {count}")
    
    # Show a few examples
    print("\n=== Sample Records ===")
    for i in range(min(3, len(output_records))):
        print(f"\n{i+1}. {json.dumps(output_records[i], indent=2)}")


if __name__ == '__main__':
    main()

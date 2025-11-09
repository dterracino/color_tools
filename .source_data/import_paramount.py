#!/usr/bin/env python3
"""
Import Paramount3D PLA filament data from FilamentColors.xyz API response.

Extracts relevant fields and converts to our filament JSON format.
"""

import json
from pathlib import Path


def convert_filamentcolors_to_our_format(api_data):
    """
    Convert FilamentColors.xyz API format to our filament format.
    
    API format has:
        - manufacturer: {id, name, website}
        - color_name: string
        - filament_type: {name, parent_type: {name}}
        - closest_pantone_1: {hex_color}
        - notes: string (sometimes contains finish info)
    
    Our format needs:
        - maker: string
        - type: string
        - finish: string | null
        - color: string
        - hex: string
        - td_value: number | null
    """
    filaments = []
    
    for item in api_data.get("results", []):
        # Extract manufacturer name
        maker = item["manufacturer"]["name"]
        
        # Extract filament type (use parent type for consistency)
        filament_type = item["filament_type"]["parent_type"]["name"]
        
        # Extract color name
        color = item["color_name"]
        
        # Extract hex color (use closest Pantone match)
        hex_color = item["closest_pantone_1"]["hex_color"] if item.get("closest_pantone_1") else None
        
        # Try to determine finish from notes or color name
        finish = None
        notes = item.get("notes", "").lower()
        color_lower = color.lower()
        
        # Common finish keywords
        if "galaxy" in notes or "galaxy" in color_lower:
            finish = "Galaxy"
        elif "silk" in notes or "silk" in color_lower:
            finish = "Silk"
        elif "matte" in notes or "matte" in color_lower:
            finish = "Matte"
        elif "metallic" in notes or "metallic" in color_lower:
            finish = "Metallic"
        elif "sparkle" in notes or "sparkle" in color_lower:
            finish = "Sparkle"
        elif "glow" in notes or "glow" in color_lower:
            finish = "Glow"
        elif "translucent" in notes or "translucent" in color_lower:
            finish = "Translucent"
        elif "transparent" in notes or "transparent" in color_lower:
            finish = "Transparent"
        
        # Create filament record
        filament = {
            "maker": maker,
            "type": filament_type,
            "finish": finish,
            "color": color,
            "hex": hex_color,
            "td_value": None  # Not available in API data
        }
        
        filaments.append(filament)
    
    return filaments


def main():
    # Paths
    source_data_dir = Path(__file__).parent
    data_dir = source_data_dir.parent / "data"
    
    paramount_file = source_data_dir / "Paramount3D PLA.json"
    filaments_file = data_dir / "filaments.json"
    
    # Load Paramount3D data
    print(f"Reading {paramount_file}...")
    with open(paramount_file, "r", encoding="utf-8") as f:
        paramount_data = json.load(f)
    
    # Convert to our format
    print("Converting to our format...")
    new_filaments = convert_filamentcolors_to_our_format(paramount_data)
    print(f"Converted {len(new_filaments)} filaments")
    
    # Load existing filaments
    print(f"Reading existing {filaments_file}...")
    with open(filaments_file, "r", encoding="utf-8") as f:
        existing_filaments = json.load(f)
    
    print(f"Found {len(existing_filaments)} existing filaments")
    
    # Create a set of existing filaments for duplicate detection
    # Use (maker, type, color) as the key
    existing_keys = {
        (f["maker"], f["type"], f["color"])
        for f in existing_filaments
    }
    
    # Filter out duplicates
    unique_new = []
    duplicates = 0
    for filament in new_filaments:
        key = (filament["maker"], filament["type"], filament["color"])
        if key not in existing_keys:
            unique_new.append(filament)
            existing_keys.add(key)  # Prevent duplicates within new data too
        else:
            duplicates += 1
    
    print(f"Found {duplicates} duplicates (skipped)")
    print(f"Adding {len(unique_new)} new filaments")
    
    # Combine and sort
    all_filaments = existing_filaments + unique_new
    
    # Sort by maker, then type, then color
    all_filaments.sort(key=lambda f: (f["maker"], f["type"], f.get("finish") or "", f["color"]))
    
    # Write back to filaments.json
    print(f"Writing {len(all_filaments)} total filaments to {filaments_file}...")
    with open(filaments_file, "w", encoding="utf-8") as f:
        json.dump(all_filaments, f, indent=2, ensure_ascii=False)
    
    print("\n✅ Done!")
    print(f"   Total filaments: {len(all_filaments)}")
    print(f"   Added from Paramount3D: {len(unique_new)}")
    
    # Show a sample of what was added
    if unique_new:
        print("\nSample of added filaments:")
        for filament in unique_new[:5]:
            finish_str = filament["finish"] if filament["finish"] else "None"
            print(f"  - {filament['maker']} {filament['type']} {finish_str}: {filament['color']} ({filament['hex']})")
        if len(unique_new) > 5:
            print(f"  ... and {len(unique_new) - 5} more")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Convert color_tools.json to use tuple format instead of named objects
for RGB, HSL, and LAB values.

Current format:
  "rgb": {"r": 240, "g": 248, "b": 255}
  "hsl": {"h": 208.0, "s": 100.0, "l": 97.0588}
  "lab": {"L": 97.1786, "a": -1.3486, "b": -4.2629}

New format:
  "rgb": [240, 248, 255]
  "hsl": [208.0, 100.0, 97.0588]
  "lab": [97.1786, -1.3486, -4.2629]
"""

import json
import sys
from pathlib import Path

def convert_color_format(data):
    """Convert color objects to tuple format"""
    converted_data = {"colors": [], "filaments": data["filaments"]}
    
    for color in data["colors"]:
        # Convert RGB object to array
        rgb_obj = color["rgb"]
        rgb_array = [rgb_obj["r"], rgb_obj["g"], rgb_obj["b"]]
        
        # Convert HSL object to array  
        hsl_obj = color["hsl"]
        hsl_array = [hsl_obj["h"], hsl_obj["s"], hsl_obj["l"]]
        
        # Convert LAB object to array
        lab_obj = color["lab"]
        lab_array = [lab_obj["L"], lab_obj["a"], lab_obj["b"]]
        
        # Create new color record with arrays
        new_color = {
            "name": color["name"],
            "hex": color["hex"],
            "rgb": rgb_array,
            "hsl": hsl_array,
            "lab": lab_array
        }
        
        converted_data["colors"].append(new_color)
    
    return converted_data

def main():
    script_dir = Path(__file__).parent
    input_path = script_dir / "data" / "color_tools.json"
    output_path = script_dir / "data" / "color_tools_tuples.json"
    
    if not input_path.exists():
        print(f"Error: color_tools.json not found at {input_path}")
        sys.exit(1)
    
    try:
        # Load the current data
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Loaded {len(data['colors'])} colors and {len(data['filaments'])} filaments")
        
        # Convert to new format
        converted_data = convert_color_format(data)
        
        # Write to new file first (as backup)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, indent=2, ensure_ascii=False)
        
        print(f"Converted data written to {output_path}")
        
        # Show a sample of the conversion
        print("\nSample conversion:")
        original_color = data["colors"][0]
        converted_color = converted_data["colors"][0]
        
        print(f"Original format for '{original_color['name']}':")
        print(f"  rgb: {original_color['rgb']}")
        print(f"  hsl: {original_color['hsl']}")
        print(f"  lab: {original_color['lab']}")
        
        print(f"\nNew format for '{converted_color['name']}':")
        print(f"  rgb: {converted_color['rgb']}")
        print(f"  hsl: {converted_color['hsl']}")
        print(f"  lab: {converted_color['lab']}")
        
        # Ask user if they want to replace the original
        print(f"\nWould you like to replace the original {input_path} with the converted version? (y/N): ", end="")
        response = input().strip().lower()
        
        if response in ['y', 'yes']:
            # Replace the original file
            with open(input_path, 'w', encoding='utf-8') as f:
                json.dump(converted_data, f, indent=2, ensure_ascii=False)
            print(f"Original file {input_path} has been updated")
            
            # Remove the backup since we replaced the original
            output_path.unlink()
            print(f"Temporary file {output_path} removed")
        else:
            print(f"Original file unchanged. Converted version saved as {output_path}")
            
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
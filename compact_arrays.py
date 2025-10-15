#!/usr/bin/env python3
"""
Compact JSON arrays to single lines for better readability.
Convert from:
      "rgb": [
        240,
        255,
        255
      ]
To:
      "rgb": [240, 255, 255]
"""

import json
import re
import os

def compact_json_arrays(input_path: str):
    """Load JSON and reformat with compact arrays."""
    
    # Read the entire file as text
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match multi-line arrays like:
    # "rgb": [
    #   240,
    #   255,
    #   255
    # ]
    
    pattern = r'("(?:rgb|hsl|lab)": \[)\s*\n\s*([^\]]+?)\n\s*(\])'
    
    def compact_array(match):
        key_part = match.group(1)  # "rgb": [
        values_part = match.group(2)  # the values with whitespace
        closing_part = match.group(3)  # ]
        
        # Extract just the numbers, handling both integers and floats
        values = []
        for line in values_part.split('\n'):
            line = line.strip()
            if line.endswith(','):
                line = line[:-1]  # Remove trailing comma
            if line:
                try:
                    # Try to parse as number
                    if '.' in line:
                        values.append(float(line))
                    else:
                        values.append(int(line))
                except ValueError:
                    # If parsing fails, keep as string (shouldn't happen with our data)
                    values.append(line)
        
        # Format compactly
        values_str = ', '.join(str(v) for v in values)
        return f'{key_part}{values_str}{closing_part}'
    
    # Apply the transformation
    compacted = re.sub(pattern, compact_array, content, flags=re.MULTILINE | re.DOTALL)
    
    # Write back to file
    with open(input_path, 'w', encoding='utf-8') as f:
        f.write(compacted)
    
    return compacted

def show_sample_before_after(input_path: str):
    """Show a sample of the format before and after."""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find first occurrence of verbose array
    match = re.search(r'("(?:rgb|hsl|lab)": \[)\s*\n\s*([^\]]+?)\n\s*(\])', content, re.MULTILINE | re.DOTALL)
    if match:
        print("BEFORE (verbose format):")
        print(match.group(0))
        print()

if __name__ == "__main__":
    input_file = "data/color_tools.json"
    
    if os.path.exists(input_file):
        print(f"Compacting arrays in {input_file}...")
        
        # Show before
        show_sample_before_after(input_file)
        
        # Get original size
        original_size = os.path.getsize(input_file)
        
        # Compact the arrays
        compact_json_arrays(input_file)
        
        # Show after
        new_size = os.path.getsize(input_file)
        
        print("AFTER (compact format):")
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find first compact array to show
        match = re.search(r'"(?:rgb|hsl|lab)": \[[^\]]+\]', content)
        if match:
            print(f'      {match.group(0)}')
        
        print(f"\nFile size: {original_size:,} → {new_size:,} bytes")
        print(f"Saved: {original_size - new_size:,} bytes ({((original_size - new_size) / original_size * 100):.1f}%)")
        
    else:
        print(f"Could not find {input_file}")
#!/usr/bin/env python3
"""
Add LCH values to all colors in color_tools.json.
LCH is computed from LAB using:
  L = L
  C = sqrt(a^2 + b^2)
  H = atan2(b, a) in degrees, normalized to 0-360
"""
import json
import math
import os

def lab_to_lch(lab):
    L, a, b = lab
    C = math.sqrt(a * a + b * b)
    h = math.degrees(math.atan2(b, a))
    if h < 0:
        h += 360.0
    return [round(L, 4), round(C, 4), round(h, 4)]

def add_lch_to_colors(input_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    changed = False
    for color in data["colors"]:
        if "lch" not in color:
            lch = lab_to_lch(color["lab"])
            color["lch"] = lch
            changed = True
    if changed:
        # Write with compact arrays
        json_str = json.dumps(data, indent=2, separators=(',', ': '))
        import re
        pattern = r'(\s*"(?:rgb|hsl|lab|lch)": \[)\s*\n\s*([^\]]+?)\n\s*(\])'
        def compact_array_match(match):
            prefix = match.group(1)
            content = match.group(2)
            suffix = match.group(3)
            values = [v.strip() for v in content.split(',') if v.strip()]
            compact_content = ', '.join(values)
            return f"{prefix}{compact_content}{suffix}"
        compacted_json = re.sub(pattern, compact_array_match, json_str, flags=re.MULTILINE | re.DOTALL)
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(compacted_json)
        print("Added LCH to all colors.")
    else:
        print("All colors already have LCH.")

if __name__ == "__main__":
    input_file = "data/color_tools.json"
    if os.path.exists(input_file):
        add_lch_to_colors(input_file)
    else:
        print(f"Could not find {input_file}")

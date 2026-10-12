import json
from typing import TypedDict

from color_tools.conversions import lab_to_lch, rgb_to_hex, rgb_to_hsl, rgb_to_lab


class _TG16ColorData(TypedDict):
    name: str
    hex: str
    rgb: list[int]
    hsl: list[float]
    lab: list[float]
    lch: list[float]


def generate_palette() -> list[_TG16ColorData]:
    """
    Generates the full TurboGrafx-16 palette in the requested JSON format.
    """
    levels = [0, 36, 72, 108, 144, 180, 216, 252]
    palette_data: list[_TG16ColorData] = []
    
    index = 0
    for r in levels:
        for g in levels:
            for b in levels:
                # 1. Hex
                hex_val = rgb_to_hex((r, g, b))
                
                # 2. RGB
                rgb_val = [r, g, b]
                
                # 3. HSL
                hsl_val = [round(value, 1) for value in rgb_to_hsl((r, g, b))]
                
                # 4. LAB
                lab_val = [round(value, 1) for value in rgb_to_lab((r, g, b))]
                
                # 5. LCH
                rounded_lab = (lab_val[0], lab_val[1], lab_val[2])
                lch_val = [round(value, 1) for value in lab_to_lch(rounded_lab)]
                
                # Construct Object
                color_obj = {
                    "name": f"tg16_{index:03d}", # e.g. tg16_000, tg16_001
                    "hex": hex_val,
                    "rgb": rgb_val,
                    "hsl": hsl_val,
                    "lab": lab_val,
                    "lch": lch_val
                }
                
                palette_data.append(color_obj)
                index += 1
                
    return palette_data

if __name__ == "__main__":
    full_palette = generate_palette()
    
    # Save to file
    filename = "tg16_complete_palette.json"
    with open(filename, "w") as f:
        json.dump(full_palette, f, indent=2)
        
    print(f"Successfully generated {len(full_palette)} colors into '{filename}'.")

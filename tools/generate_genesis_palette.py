#!/usr/bin/env python3
"""
Sega Genesis/Mega Drive palette generator.

Generates the full 512-color 9-bit RGB palette used by the Sega Genesis VDP.
The Genesis uses 3 bits per color channel (RGB), giving 8 levels per channel.
"""

import json
from pathlib import Path


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex string."""
    return f"#{r:02x}{g:02x}{b:02x}"


def rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert RGB to HSL."""
    r_norm, g_norm, b_norm = r/255.0, g/255.0, b/255.0
    
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    diff = max_val - min_val
    
    # Lightness
    l = (max_val + min_val) / 2.0
    
    if diff == 0:
        h = s = 0  # Achromatic
    else:
        # Saturation
        s = diff / (2 - max_val - min_val) if l > 0.5 else diff / (max_val + min_val)
        
        # Hue
        if max_val == r_norm:
            h = (g_norm - b_norm) / diff + (6 if g_norm < b_norm else 0)
        elif max_val == g_norm:
            h = (b_norm - r_norm) / diff + 2
        else:
            h = (r_norm - g_norm) / diff + 4
        h /= 6
    
    return round(h * 360, 1), round(s * 100, 1), round(l * 100, 1)


def rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert RGB to LAB (simplified conversion)."""
    # Normalize RGB
    r_norm, g_norm, b_norm = r/255.0, g/255.0, b/255.0
    
    # Apply gamma correction
    r_linear = ((r_norm + 0.055) / 1.055) ** 2.4 if r_norm > 0.04045 else r_norm / 12.92
    g_linear = ((g_norm + 0.055) / 1.055) ** 2.4 if g_norm > 0.04045 else g_norm / 12.92
    b_linear = ((b_norm + 0.055) / 1.055) ** 2.4 if b_norm > 0.04045 else b_norm / 12.92
    
    # Convert to XYZ (sRGB D65)
    x = r_linear * 0.4124564 + g_linear * 0.3575761 + b_linear * 0.1804375
    y = r_linear * 0.2126729 + g_linear * 0.7151522 + b_linear * 0.0721750
    z = r_linear * 0.0193339 + g_linear * 0.1191920 + b_linear * 0.9503041
    
    # Normalize for D65 illuminant
    x /= 0.95047
    y /= 1.00000
    z /= 1.08883
    
    # Convert to LAB
    fx = x**(1/3) if x > 0.008856 else (7.787 * x + 16/116)
    fy = y**(1/3) if y > 0.008856 else (7.787 * y + 16/116)
    fz = z**(1/3) if z > 0.008856 else (7.787 * z + 16/116)
    
    l = 116 * fy - 16
    a = 500 * (fx - fy)
    b_val = 200 * (fy - fz)
    
    return round(l, 1), round(a, 1), round(b_val, 1)


def lab_to_lch(l: float, a: float, b: float) -> tuple[float, float, float]:
    """Convert LAB to LCH."""
    import math
    
    c = math.sqrt(a*a + b*b)
    h = math.atan2(b, a) * 180 / math.pi
    if h < 0:
        h += 360
    
    return round(l, 1), round(c, 1), round(h, 1)


def generate_genesis_palette() -> list[dict]:
    """
    Generate the full 512-color Genesis palette.
    
    Genesis uses 9-bit color (3 bits per channel):
    - Red: 0-7 (3 bits)
    - Green: 0-7 (3 bits) 
    - Blue: 0-7 (3 bits)
    
    Each 3-bit value is mapped to 8-bit RGB by multiplying by 36.428571...
    This gives us the range: 0, 36, 73, 109, 146, 182, 219, 255
    """
    colors = []
    
    # 3-bit to 8-bit conversion table
    # Genesis uses even spacing across the 0-255 range
    bit3_to_bit8 = [0, 36, 73, 109, 146, 182, 219, 255]
    
    for r3 in range(8):  # 3-bit red (0-7)
        for g3 in range(8):  # 3-bit green (0-7)
            for b3 in range(8):  # 3-bit blue (0-7)
                # Convert 3-bit values to 8-bit RGB
                r8 = bit3_to_bit8[r3]
                g8 = bit3_to_bit8[g3]
                b8 = bit3_to_bit8[b3]
                
                # Convert to other color spaces
                hex_color = rgb_to_hex(r8, g8, b8)
                hsl = rgb_to_hsl(r8, g8, b8)
                lab = rgb_to_lab(r8, g8, b8)
                lch = lab_to_lch(lab[0], lab[1], lab[2])
                
                # Create descriptive name
                color_index = (r3 << 6) | (g3 << 3) | b3  # 9-bit color value
                color_name = f"genesis_{color_index:03d}"
                
                # Add more descriptive names for special colors
                if r8 == 0 and g8 == 0 and b8 == 0:
                    color_name = "genesis_black"
                elif r8 == 255 and g8 == 255 and b8 == 255:
                    color_name = "genesis_white"
                elif r8 == 255 and g8 == 0 and b8 == 0:
                    color_name = "genesis_red"
                elif r8 == 0 and g8 == 255 and b8 == 0:
                    color_name = "genesis_green"
                elif r8 == 0 and g8 == 0 and b8 == 255:
                    color_name = "genesis_blue"
                elif r8 == 255 and g8 == 255 and b8 == 0:
                    color_name = "genesis_yellow"
                elif r8 == 255 and g8 == 0 and b8 == 255:
                    color_name = "genesis_magenta"
                elif r8 == 0 and g8 == 255 and b8 == 255:
                    color_name = "genesis_cyan"
                
                color_data = {
                    "name": color_name,
                    "hex": hex_color,
                    "rgb": [r8, g8, b8],
                    "hsl": list(hsl),
                    "lab": list(lab),
                    "lch": list(lch)
                }
                
                colors.append(color_data)
    
    return colors


def save_genesis_palette(colors: list[dict], output_path: Path) -> None:
    """Save the Genesis palette to a JSON file."""
    with open(output_path, 'w') as f:
        json.dump(colors, f, indent=2)
    
    print(f"Generated {len(colors)} colors for Sega Genesis palette")
    print(f"Saved to: {output_path}")
    
    # Print some statistics
    unique_reds = set(color['rgb'][0] for color in colors)
    unique_greens = set(color['rgb'][1] for color in colors)
    unique_blues = set(color['rgb'][2] for color in colors)
    
    print(f"Unique red values: {sorted(unique_reds)}")
    print(f"Unique green values: {sorted(unique_greens)}")
    print(f"Unique blue values: {sorted(unique_blues)}")
    print(f"Total combinations: {len(unique_reds)} × {len(unique_greens)} × {len(unique_blues)} = {len(colors)}")


def main():
    """Generate the Sega Genesis palette file."""
    colors = generate_genesis_palette()
    
    # Create output directory
    script_dir = Path(__file__).parent
    palettes_dir = script_dir.parent / "color_tools" / "data" / "palettes"
    palettes_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the palette
    output_path = palettes_dir / "genesis.json"
    save_genesis_palette(colors, output_path)


if __name__ == "__main__":
    main()
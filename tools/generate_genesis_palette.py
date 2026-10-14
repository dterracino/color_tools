#!/usr/bin/env python3
"""
Sega Genesis/Mega Drive palette generator.

Generates the full 512-color 9-bit RGB palette used by the Sega Genesis VDP.
The Genesis uses 3 bits per color channel (RGB), giving 8 levels per channel.
"""

import json
from pathlib import Path
from typing import TypedDict
from color_tools.conversions import (
    lab_to_lch,
    rgb_to_hex as _rgb_to_hex,
    rgb_to_hsl,
    rgb_to_lab,
)


class _GenesisColorData(TypedDict):
    name: str
    hex: str
    rgb: list[int]
    hsl: list[float]
    lab: list[float]
    lch: list[float]


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex string."""
    return _rgb_to_hex((r, g, b)).lower()


def generate_genesis_palette() -> list[_GenesisColorData]:
    """
    Generate the full 512-color Genesis palette.
    
    Genesis uses 9-bit color (3 bits per channel):
    - Red: 0-7 (3 bits)
    - Green: 0-7 (3 bits) 
    - Blue: 0-7 (3 bits)
    
    Each 3-bit value is mapped to 8-bit RGB by multiplying by 36.428571...
    This gives us the range: 0, 36, 73, 109, 146, 182, 219, 255
    """
    colors: list[_GenesisColorData] = []
    
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
                rgb = (r8, g8, b8)
                raw_hsl = rgb_to_hsl(rgb)
                hsl = (
                    round(raw_hsl[0], 1),
                    round(raw_hsl[1], 1),
                    round(raw_hsl[2], 1),
                )
                raw_lab = rgb_to_lab(rgb)
                lab = (
                    round(raw_lab[0], 1),
                    round(raw_lab[1], 1),
                    round(raw_lab[2], 1),
                )
                raw_lch = lab_to_lch(lab)
                lch = (
                    round(raw_lch[0], 1),
                    round(raw_lch[1], 1),
                    round(raw_lch[2], 1),
                )
                
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
                
                color_data: _GenesisColorData = {
                    "name": color_name,
                    "hex": hex_color,
                    "rgb": [r8, g8, b8],
                    "hsl": list(hsl),
                    "lab": list(lab),
                    "lch": list(lch)
                }
                
                colors.append(color_data)
    
    return colors


def save_genesis_palette(colors: list[_GenesisColorData], output_path: Path) -> None:
    """Save the Genesis palette to a JSON file."""
    document: dict[str, object] = {
        "schema_version": 1,
        "metadata": {
            "id": "genesis",
            "name": "Sega Genesis",
            "description": "A home video game console released by Sega.",
            "release_year": 1988,
        },
        "palette": {
            "type": "indexed",
            "colors": colors,
        },
    }
    with open(output_path, 'w') as f:
        json.dump(document, f, indent=2)
    
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


def main() -> None:
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

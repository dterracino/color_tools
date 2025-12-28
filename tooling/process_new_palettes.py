#!/usr/bin/env python3
"""
Process new retro palette files from .source_data to proper system format.

Converts various input formats to the standard palette format with LAB/LCH/HSL values.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path so we can import color_tools
sys.path.insert(0, str(Path(__file__).parent.parent))

from color_tools.conversions import rgb_to_hsl, rgb_to_lab, rgb_to_lch


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color (#RRGGBB) to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))  # type: ignore


def create_color_record(name: str, rgb: tuple[int, int, int]) -> dict[str, Any]:
    """
    Create a ColorRecord-compatible dictionary with all color space values.
    
    Args:
        name: Color name
        rgb: RGB tuple (0-255 for each channel)
    
    Returns:
        Dictionary with name, hex, rgb, hsl, lab, lch values
    """
    # Convert to hex
    hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    # Compute other color spaces using color_tools
    hsl = rgb_to_hsl(rgb)
    lab = rgb_to_lab(rgb)
    lch = rgb_to_lch(rgb)
    
    # Round to 1 decimal place for consistency
    return {
        "name": name,
        "hex": hex_color,
        "rgb": list(rgb),
        "hsl": [round(h, 1) for h in hsl],
        "lab": [round(l, 1) for l in lab],
        "lch": [round(l, 1) for l in lch]
    }


def process_hex_array(filename: str, palette_name: str, color_names: list[str] | None = None) -> list[dict[str, Any]]:
    """Process a simple hex array palette."""
    source_file = Path(__file__).parent.parent / '.source_data' / filename
    
    with open(source_file, 'r') as f:
        hex_colors = json.load(f)
    
    colors = []
    for idx, hex_color in enumerate(hex_colors):
        rgb = hex_to_rgb(hex_color)
        # Use provided name or generate indexed name
        if color_names and idx < len(color_names):
            name = color_names[idx]
        else:
            name = f"color_{idx:02d}"
        colors.append(create_color_record(name, rgb))
    
    return colors


def process_tandy16() -> list[dict[str, Any]]:
    """Process the Tandy 16-color palette with structured data."""
    source_file = Path(__file__).parent.parent / '.source_data' / 'tandy16-retro-palette.json'
    
    with open(source_file, 'r') as f:
        data = json.load(f)
    
    colors = []
    for color_obj in data['colors']:
        name = color_obj['name'].lower().replace(' ', '_')
        rgb_obj = color_obj['rgb']
        rgb = (rgb_obj['r'], rgb_obj['g'], rgb_obj['b'])
        colors.append(create_color_record(name, rgb))
    
    return colors


def process_sega_master_system() -> list[dict[str, Any]]:
    """Process the Sega Master System 64-color palette."""
    source_file = Path(__file__).parent.parent / '.source_data' / 'sega-master-system-retro-palette.json'
    
    with open(source_file, 'r') as f:
        data = json.load(f)
    
    colors = []
    for color_obj in data:
        # Use hex code as name (e.g., "0x00", "0x1F")
        name = color_obj['name'].lower()
        rgb_obj = color_obj['rgb']
        rgb = (rgb_obj['r'], rgb_obj['g'], rgb_obj['b'])
        colors.append(create_color_record(name, rgb))
    
    return colors


def save_palette(palette_name: str, colors: list[dict[str, Any]]) -> None:
    """Save palette to data/palettes directory."""
    output_dir = Path(__file__).parent.parent / 'color_tools' / 'data' / 'palettes'
    output_file = output_dir / f'{palette_name}.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(colors, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Generated {palette_name}.json ({len(colors)} colors)")


def main():
    """Process all new palette files."""
    print("Processing new retro palettes...\n")
    
    # Apple II - 6 colors
    apple2_names = ['black', 'red', 'purple', 'green', 'cyan', 'light_gray']
    colors = process_hex_array('apple-ii-retro-palette.json', 'apple2', apple2_names)
    save_palette('apple2', colors)
    
    # Macintosh - 8 grayscale shades
    mac_names = ['black', 'dark_gray_1', 'dark_gray_2', 'gray', 'light_gray_1', 'light_gray_2', 'light_gray_3', 'white']
    colors = process_hex_array('macintosh-retro-palette.json', 'macintosh', mac_names)
    save_palette('macintosh', colors)
    
    # Game Boy Color - 14 colors
    gbc_names = [
        'dark_blue_green', 'medium_green', 'light_green', 'lightest_green',
        'dark_purple', 'dark_pink', 'light_pink',
        'dark_blue', 'medium_blue', 'light_blue',
        'dark_brown', 'medium_brown', 'orange', 'yellow'
    ]
    colors = process_hex_array('gameboy-color-retro-palette.json', 'gameboy-color', gbc_names)
    save_palette('gameboy-color', colors)
    
    # Tandy 16
    tandy_colors = process_tandy16()
    save_palette('tandy16', tandy_colors)
    
    # Sega Master System - 64 colors
    sega_colors = process_sega_master_system()
    save_palette('sega-master-system', sega_colors)
    
    print(f"\n✨ All 5 palettes generated successfully!")


if __name__ == '__main__':
    main()

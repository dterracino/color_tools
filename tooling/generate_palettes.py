#!/usr/bin/env python3
"""
Generate palette JSON files for classic retro palettes (CGA, EGA, VGA, Web Safe).

This script uses the color_tools library to compute accurate LAB/LCH/HSL values
from RGB/hex color definitions, then outputs properly formatted JSON files
compatible with the Palette class.
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
    
    # Round to 1 decimal place for consistency with colors.json
    return {
        "name": name,
        "hex": hex_color,
        "rgb": list(rgb),
        "hsl": [round(h, 1) for h in hsl],
        "lab": [round(l, 1) for l in lab],
        "lch": [round(l, 1) for l in lch]
    }


def generate_cga4() -> list[dict[str, Any]]:
    """
    Generate CGA 4-color palette (Palette 1, high intensity).
    The classic gaming palette: Black, Light Cyan, Light Magenta, Bright White.
    """
    colors = [
        ("Black", (0, 0, 0)),
        ("Light Cyan", (85, 255, 255)),
        ("Light Magenta", (255, 85, 255)),
        ("Bright White", (255, 255, 255))
    ]
    return [create_color_record(name, rgb) for name, rgb in colors]


def generate_cga16() -> list[dict[str, Any]]:
    """
    Generate CGA 16-color palette (full RGBI palette).
    Used in text mode and some graphics modes.
    """
    colors = [
        ("Black", (0, 0, 0)),
        ("Blue", (0, 0, 170)),
        ("Green", (0, 170, 0)),
        ("Cyan", (0, 170, 170)),
        ("Red", (170, 0, 0)),
        ("Magenta", (170, 0, 170)),
        ("Brown", (170, 85, 0)),
        ("Light Gray", (170, 170, 170)),
        ("Dark Gray", (85, 85, 85)),
        ("Light Blue", (85, 85, 255)),
        ("Light Green", (85, 255, 85)),
        ("Light Cyan", (85, 255, 255)),
        ("Light Red", (255, 85, 85)),
        ("Light Magenta", (255, 85, 255)),
        ("Yellow", (255, 255, 85)),
        ("White", (255, 255, 255))
    ]
    return [create_color_record(name, rgb) for name, rgb in colors]


def generate_ega16() -> list[dict[str, Any]]:
    """
    Generate EGA 16-color palette (standard/default EGA palette).
    This is the most commonly used EGA palette in games.
    """
    colors = [
        ("Black", (0, 0, 0)),
        ("Blue", (0, 0, 170)),
        ("Green", (0, 170, 0)),
        ("Cyan", (0, 170, 170)),
        ("Red", (170, 0, 0)),
        ("Magenta", (170, 0, 170)),
        ("Brown", (170, 85, 0)),
        ("Light Gray", (170, 170, 170)),
        ("Dark Gray", (85, 85, 85)),
        ("Bright Blue", (85, 85, 255)),
        ("Bright Green", (85, 255, 85)),
        ("Bright Cyan", (85, 255, 255)),
        ("Bright Red", (255, 85, 85)),
        ("Bright Magenta", (255, 85, 255)),
        ("Bright Yellow", (255, 255, 85)),
        ("Bright White", (255, 255, 255))
    ]
    return [create_color_record(name, rgb) for name, rgb in colors]


def generate_ega64() -> list[dict[str, Any]]:
    """
    Generate EGA 64-color palette (full 6-bit RGB).
    2 bits per channel: 00, 55, AA, FF (0, 85, 170, 255)
    """
    colors = []
    values = [0x00, 0x55, 0xAA, 0xFF]  # 2-bit values expanded to 8-bit
    
    for r in values:
        for g in values:
            for b in values:
                # Create descriptive name based on RGB values
                rgb = (r, g, b)
                name = f"EGA {r:02X}{g:02X}{b:02X}"
                colors.append(create_color_record(name, rgb))
    
    return colors


def generate_vga() -> list[dict[str, Any]]:
    """
    Generate VGA 256-color palette from the source data file.
    """
    vga_csv_path = Path(__file__).parent.parent / ".source_data" / "vga-palette.csv"
    
    colors = []
    with open(vga_csv_path, 'r') as f:
        for i, line in enumerate(f):
            parts = line.strip().split(',')
            if len(parts) >= 3:
                r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                name = f"VGA {i:03d}"
                colors.append(create_color_record(name, (r, g, b)))
    
    return colors


def generate_websafe() -> list[dict[str, Any]]:
    """
    Generate Web Safe 216-color palette (6x6x6 RGB cube).
    Values: 00, 33, 66, 99, CC, FF (0, 51, 102, 153, 204, 255)
    """
    colors = []
    values = [0x00, 0x33, 0x66, 0x99, 0xCC, 0xFF]
    
    for r in values:
        for g in values:
            for b in values:
                rgb = (r, g, b)
                name = f"Web {r:02X}{g:02X}{b:02X}"
                colors.append(create_color_record(name, rgb))
    
    return colors


def save_palette(palette_name: str, colors: list[dict[str, Any]]) -> None:
    """Save palette to JSON file in data/palettes/ directory."""
    output_dir = Path(__file__).parent.parent / "color_tools" / "data" / "palettes"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{palette_name}.json"
    
    with open(output_file, 'w') as f:
        json.dump(colors, f, indent=2)
    
    print(f"✓ Generated {palette_name}.json ({len(colors)} colors)")


def main():
    """Generate all palette files."""
    print("Generating retro palette files...\n")
    
    palettes = {
        "cga4": generate_cga4(),
        "cga16": generate_cga16(),
        "ega16": generate_ega16(),
        "ega64": generate_ega64(),
        "vga": generate_vga(),
        "web": generate_websafe()
    }
    
    for name, colors in palettes.items():
        save_palette(name, colors)
    
    print(f"\n✨ All {len(palettes)} palettes generated successfully!")


if __name__ == "__main__":
    main()

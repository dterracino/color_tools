#!/usr/bin/env python3
"""
Generate Crayola crayon colors palette JSON file.

This script processes the Crayola source data and computes LAB/LCH/HSL values
from the RGB color definitions, then outputs a properly formatted JSON file
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


def process_crayola_colors() -> list[dict[str, Any]]:
    """
    Load Crayola source data and convert to full palette format.
    
    Returns:
        List of color records with name, hex, rgb, hsl, lab, lch values
    """
    # Load source data
    source_file = Path(__file__).parent.parent / ".source_data" / "crayola_crayon_colors.json"
    
    with open(source_file, 'r') as f:
        source_colors = json.load(f)
    
    palette_colors = []
    
    for color in source_colors:
        name = color["name"]
        rgb = tuple(color["rgb"])
        hex_color = color["hex"]
        
        # Compute color spaces using color_tools
        hsl = rgb_to_hsl(rgb)
        lab = rgb_to_lab(rgb)
        lch = rgb_to_lch(rgb)
        
        # Create palette record (round to 1 decimal place for consistency)
        palette_colors.append({
            "name": name,
            "hex": hex_color.lower(),  # Normalize to lowercase
            "rgb": list(rgb),
            "hsl": [round(h, 1) for h in hsl],
            "lab": [round(l, 1) for l in lab],
            "lch": [round(l, 1) for l in lch]
        })
    
    return palette_colors


def save_palette(colors: list[dict[str, Any]]) -> None:
    """Save Crayola palette to JSON file in data/palettes/ directory."""
    output_dir = Path(__file__).parent.parent / "color_tools" / "data" / "palettes"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "crayola.json"
    
    with open(output_file, 'w') as f:
        json.dump(colors, f, indent=2)
    
    print(f"✓ Generated crayola.json ({len(colors)} colors)")


def main():
    """Generate Crayola palette file."""
    print("Generating Crayola crayon colors palette...\n")
    
    colors = process_crayola_colors()
    save_palette(colors)
    
    print(f"\n✨ Crayola palette generated successfully!")
    print(f"   Location: color_tools/data/palettes/crayola.json")
    print(f"   Colors: {len(colors)}")


if __name__ == "__main__":
    main()

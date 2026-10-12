#!/usr/bin/env python3
"""Test script to verify palette loading functionality"""

from pathlib import Path
from color_tools.palette import Palette, load_colors

def test_genesis_palette(genesis_file: Path = Path('color_tools/data/palettes/genesis.json')) -> bool:
    """Test loading and displaying Genesis palette information"""
    if not genesis_file.exists():
        print("❌ Genesis palette file not found!")
        return False
        
    try:
        colors = load_colors(genesis_file)
        
        print("Genesis palette information:")
        print(f"  Total colors: {len(colors)}")
        print(f"  First few colors: {[c.hex for c in colors[:8]]}")
        print("✓ Genesis palette loaded successfully!")
        return True
        
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"❌ Error loading Genesis palette: {e}")
        return False

def test_palette_creation(genesis_file: Path = Path('color_tools/data/palettes/genesis.json')) -> bool:
    """Test creating a Palette object from the Genesis data"""
    try:
        palette = Palette(load_colors(genesis_file))
        if not palette.records:
            raise ValueError("Genesis palette contains no colors")
        print(f"✓ Palette object created with {len(palette.records)} colors")
        
        # Test nearest color search
        test_color = (128, 64, 192)  # Purple-ish color
        nearest, distance = palette.nearest_color(test_color)
        print(f"✓ Nearest color to RGB{test_color}: {nearest.name} ({nearest.hex}) - distance: {distance:.2f}")
        
        # Test a few more colors
        test_colors = [
            ((255, 0, 0), "Red"),
            ((0, 255, 0), "Green"), 
            ((0, 0, 255), "Blue"),
            ((255, 255, 255), "White"),
            ((0, 0, 0), "Black")
        ]
        
        print("\nTesting color matching:")
        for rgb, name in test_colors:
            nearest, distance = palette.nearest_color(rgb)
            print(f"  {name} RGB{rgb} → {nearest.name} ({nearest.hex}) - distance: {distance:.2f}")
        
        return True
        
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"❌ Error creating palette: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Testing Genesis Palette ===")
    success = test_genesis_palette()
    
    if success:
        print("\n=== Testing Palette Object Creation ===")
        test_palette_creation()
    
    print("\n=== Testing Complete ===")
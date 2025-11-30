#!/usr/bin/env python3
"""Test script to verify palette loading and image quantization functionality"""

from color_tools.image import extract_color_clusters
from color_tools.palette import Palette
import json
from pathlib import Path

def test_genesis_palette():
    """Test loading and displaying Genesis palette information"""
    genesis_file = Path('color_tools/data/palettes/genesis.json')
    
    if not genesis_file.exists():
        print("❌ Genesis palette file not found!")
        return False
        
    try:
        with open(genesis_file) as f:
            data = json.load(f)
        
        print("Genesis palette metadata:")
        print(f"  Name: {data['metadata']['name']}")
        print(f"  Total colors: {data['metadata']['total_colors']}")
        print(f"  Simultaneous colors: {data['metadata']['simultaneous_colors']}")
        print(f"  Bit depth: {data['metadata']['bit_depth']}")
        print(f"  Tags: {', '.join(data['metadata']['tags'])}")
        print(f"  First few colors: {[c['hex'] for c in data['palette'][:8]]}")
        print("✓ Genesis palette loaded successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error loading Genesis palette: {e}")
        return False

def test_palette_creation():
    """Test creating a Palette object from the Genesis data"""
    try:
        # Load Genesis palette
        genesis_file = Path('color_tools/data/palettes/genesis.json')
        with open(genesis_file) as f:
            data = json.load(f)
        
        # Extract just the color data (convert from new format to old format for testing)
        colors = []
        for color_entry in data['palette']:
            colors.append({
                'name': color_entry['name'],
                'hex': color_entry['hex'],
                'rgb': color_entry['rgb'],
                'hsl': color_entry['hsl'], 
                'lab': color_entry['lab'],
                'lch': color_entry['lch']
            })
        
        # Create Palette object
        palette = Palette(colors)
        print(f"✓ Palette object created with {len(palette.colors)} colors")
        
        # Test nearest color search
        test_color = (128, 64, 192)  # Purple-ish color
        nearest, distance = palette.nearest_color(test_color)
        print(f"✓ Nearest color to RGB{test_color}: {nearest.name} ({nearest.hex}) - distance: {distance:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating palette: {e}")
        return False

if __name__ == "__main__":
    print("=== Testing Genesis Palette ===")
    success = test_genesis_palette()
    
    if success:
        print("\n=== Testing Palette Object Creation ===")
        test_palette_creation()
    
    print("\n=== Testing Complete ===")
#!/usr/bin/env python3
"""
Palette conversion tool for color_tools.

Converts existing palette files to new metadata format with compact formatting.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Palette metadata definitions
PALETTE_METADATA = {
    "cga4": {
        "name": "CGA 4-Color",
        "description": "4-color palette from IBM Color Graphics Adapter (2-bit)",
        "native_resolution": [320, 200],
        "display_aspect_ratio": "4:3",  # Standard TV display
        "pixel_aspect_ratio": "1.2:1",  # Non-square pixels
        "creator": "IBM",
        "year": 1981,
        "bit_depth": 2,
        "total_colors": 4,
        "simultaneous_colors": 4,
        "tags": ["vintage", "cga", "low-res", "ibm"]
    },
    "cga16": {
        "name": "CGA 16-Color", 
        "description": "16-color palette from IBM Color Graphics Adapter (4-bit)",
        "native_resolution": [160, 100],  # Corrected resolution
        "display_aspect_ratio": "4:3",
        "pixel_aspect_ratio": "2.4:1",  # Very wide pixels
        "creator": "IBM",
        "year": 1981,
        "bit_depth": 4,
        "total_colors": 16,
        "simultaneous_colors": 16,
        "tags": ["vintage", "cga", "low-res", "ibm"]
    },
    "ega16": {
        "name": "EGA 16-Color",
        "description": "16-color palette from IBM Enhanced Graphics Adapter (4-bit)",
        "native_resolution": [640, 350],
        "display_aspect_ratio": "4:3",
        "pixel_aspect_ratio": "1.37:1",  # Slightly wide pixels
        "creator": "IBM", 
        "year": 1984,
        "bit_depth": 4,
        "total_colors": 16,
        "simultaneous_colors": 16,
        "tags": ["vintage", "ega", "ibm"]
    },
    "ega64": {
        "name": "EGA 64-Color",
        "description": "64-color palette from IBM Enhanced Graphics Adapter (6-bit)",
        "native_resolution": [640, 350], 
        "display_aspect_ratio": "4:3",
        "pixel_aspect_ratio": "1.37:1",
        "creator": "IBM",
        "year": 1984,
        "bit_depth": 6,
        "total_colors": 64,
        "simultaneous_colors": 16,  # Could select 16 from 64
        "tags": ["vintage", "ega", "ibm"]
    },
    "vga": {
        "name": "VGA 256-Color",
        "description": "256-color palette from IBM Video Graphics Array (8-bit)",
        "native_resolution": [640, 480],
        "display_aspect_ratio": "4:3",
        "pixel_aspect_ratio": "1:1",  # Square pixels
        "creator": "IBM",
        "year": 1987, 
        "bit_depth": 8,
        "total_colors": 256,
        "simultaneous_colors": 256,
        "tags": ["vintage", "vga", "ibm"]
    },
    "web": {
        "name": "Web Safe Colors",
        "description": "216-color web-safe palette for early internet browsers",
        "native_resolution": None,
        "display_aspect_ratio": None,
        "pixel_aspect_ratio": None,
        "creator": "W3C",
        "year": 1996,
        "bit_depth": 8,
        "total_colors": 216,
        "simultaneous_colors": 216,
        "tags": ["web", "browser", "safe", "internet"]
    },
    "nes": {
        "name": "NES System Palette",
        "description": "Nintendo Entertainment System full color palette",
        "native_resolution": [256, 240],
        "display_aspect_ratio": "4:3",  # NTSC TV
        "pixel_aspect_ratio": "8:7",    # Slightly wide pixels
        "creator": "Nintendo",
        "year": 1983,
        "bit_depth": 6,  # 2 bits per color channel (RGB)
        "total_colors": 64,  # Actually 54 unique colors
        "simultaneous_colors": 25,  # 4 palettes × 4 colors each + universal background
        "tags": ["vintage", "nintendo", "nes", "console", "gaming"]
    },
    "gameboy": {
        "name": "Game Boy Original",
        "description": "Original Game Boy 4-shade monochrome palette",
        "native_resolution": [160, 144], 
        "display_aspect_ratio": "10:9",  # LCD screen ratio
        "pixel_aspect_ratio": "1:1",     # Square pixels
        "creator": "Nintendo",
        "year": 1989,
        "bit_depth": 2,
        "total_colors": 4,
        "simultaneous_colors": 4,
        "tags": ["vintage", "nintendo", "gameboy", "handheld", "monochrome"]
    },
    "gameboy_dmg": {
        "name": "Game Boy DMG-01",
        "description": "Game Boy DMG-01 original hardware palette variations",
        "native_resolution": [160, 144],
        "display_aspect_ratio": "10:9",
        "pixel_aspect_ratio": "1:1", 
        "creator": "Nintendo",
        "year": 1989,
        "bit_depth": 2,
        "total_colors": 4,
        "simultaneous_colors": 4,
        "tags": ["vintage", "nintendo", "gameboy", "dmg", "handheld"]
    },
    "gameboy_gbl": {
        "name": "Game Boy Light",
        "description": "Game Boy Light backlit screen palette (Japan exclusive)",
        "native_resolution": [160, 144],
        "display_aspect_ratio": "10:9",
        "pixel_aspect_ratio": "1:1",
        "creator": "Nintendo", 
        "year": 1998,
        "bit_depth": 2,
        "total_colors": 4,
        "simultaneous_colors": 4,
        "tags": ["vintage", "nintendo", "gameboy", "light", "handheld", "backlit"]
    },
    "gameboy_mgb": {
        "name": "Game Boy Pocket",
        "description": "Game Boy Pocket (MGB-001) palette variations",
        "native_resolution": [160, 144],
        "display_aspect_ratio": "10:9",
        "pixel_aspect_ratio": "1:1",
        "creator": "Nintendo",
        "year": 1996,
        "bit_depth": 2,
        "total_colors": 4,
        "simultaneous_colors": 4,
        "tags": ["vintage", "nintendo", "gameboy", "pocket", "handheld"]
    },
    "commodore64": {
        "name": "Commodore 64",
        "description": "Commodore 64 VIC-II chip 16-color palette (4-bit)",
        "native_resolution": [320, 200],
        "display_aspect_ratio": "4:3",  # PAL/NTSC TV
        "pixel_aspect_ratio": "1.2:1",  # Non-square pixels like CGA
        "creator": "Commodore",
        "year": 1982,
        "bit_depth": 4,
        "total_colors": 16,
        "simultaneous_colors": 16,
        "tags": ["vintage", "commodore", "c64", "vic-ii"]
    },
    "sms": {
        "name": "Sega Master System",
        "description": "Sega Master System VDP color palette (6-bit)",
        "native_resolution": [256, 192],
        "display_aspect_ratio": "4:3",
        "pixel_aspect_ratio": "1.33:1",  # Slightly wide pixels
        "creator": "Sega",
        "year": 1986,
        "bit_depth": 6,  # 2 bits per RGB channel
        "total_colors": 64,
        "simultaneous_colors": 32,  # As you mentioned - key limitation!
        "tags": ["vintage", "sega", "sms", "console", "gaming"]
    },
    "turbografx16": {
        "name": "TurboGrafx-16",
        "description": "TurboGrafx-16/PC Engine 512-color palette (9-bit)",
        "native_resolution": [256, 224],  # NTSC resolution
        "display_aspect_ratio": "4:3",
        "pixel_aspect_ratio": "8:7",     # Similar to NES
        "creator": "NEC",
        "year": 1987,
        "bit_depth": 9,  # 3 bits per RGB channel
        "total_colors": 512,
        "simultaneous_colors": 256,  # Could display 256 from 512 palette
        "tags": ["vintage", "nec", "turbografx", "pcengine", "console"]
    },
    "virtualboy": {
        "name": "Virtual Boy",
        "description": "Nintendo Virtual Boy red monochrome LED display palette",
        "native_resolution": [384, 224],
        "display_aspect_ratio": "12:7",  # Wide aspect ratio for stereoscopic display
        "pixel_aspect_ratio": "1:1",     # Square pixels
        "creator": "Nintendo",
        "year": 1995,
        "bit_depth": 2,  # 4 shades of red
        "total_colors": 4,
        "simultaneous_colors": 4,
        "tags": ["vintage", "nintendo", "virtualboy", "handheld", "stereoscopic", "monochrome", "red"]
    }
}


def convert_palette_file(input_path: Path, output_path: Path | None = None) -> None:
    """Convert a palette file to the new metadata format."""
    if output_path is None:
        output_path = input_path
    
    print(f"Converting {input_path.name}...")
    
    # Load existing palette
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    # Handle both old format (array) and already converted format (dict)
    if isinstance(data, list):
        colors = data
    elif isinstance(data, dict) and 'palette' in data:
        print(f"  ⚠ File already converted, skipping...")
        return
    else:
        print(f"  ❌ Unknown format in {input_path}")
        return
    
    # Get palette name from filename
    palette_name = input_path.stem
    metadata = PALETTE_METADATA.get(palette_name, {
        "name": palette_name.title(),
        "description": f"{palette_name.title()} color palette",
        "native_resolution": None,
        "display_aspect_ratio": None,
        "pixel_aspect_ratio": None,
        "creator": "Unknown",
        "year": None,
        "bit_depth": None,
        "total_colors": len(colors),
        "simultaneous_colors": len(colors),
        "tags": ["palette"]
    })
    
    # Create new structure
    new_format = {
        "format_version": "1.0",
        "metadata": metadata,
        "palette": colors
    }
    
    # Write with compact formatting for colors, expanded for metadata
    with open(output_path, 'w') as f:
        # Custom formatting: metadata expanded, palette colors compact
        f.write('{\n')
        f.write('  "format_version": "1.0",\n')
        f.write('  "metadata": {\n')
        
        for i, (key, value) in enumerate(metadata.items()):
            comma = ',' if i < len(metadata) - 1 else ''
            if isinstance(value, list):
                if value and isinstance(value[0], str):
                    # Tags array - compact format
                    f.write(f'    "{key}": {json.dumps(value)}{comma}\n')
                else:
                    # Resolution array - compact format  
                    f.write(f'    "{key}": {json.dumps(value)}{comma}\n')
            else:
                f.write(f'    "{key}": {json.dumps(value)}{comma}\n')
        
        f.write('  },\n')
        f.write('  "palette": [\n')
        
        for i, color in enumerate(colors):
            comma = ',' if i < len(colors) - 1 else ''
            # Write each color on a single line
            f.write(f'    {json.dumps(color, separators=(",", ": "))}{comma}\n')
        
        f.write('  ]\n')
        f.write('}\n')
    
    print(f"  ✓ Converted {len(colors)} colors")
    print(f"  ✓ Saved to {output_path}")


def main():
    """Convert all palette files or specific ones."""
    if len(sys.argv) > 1:
        # Convert specific files
        for arg in sys.argv[1:]:
            path = Path(arg)
            if path.exists():
                convert_palette_file(path)
            else:
                print(f"File not found: {path}")
    else:
        # Convert all palette files
        script_dir = Path(__file__).parent
        palettes_dir = script_dir.parent / "color_tools" / "data" / "palettes"
        
        if not palettes_dir.exists():
            print(f"Palettes directory not found: {palettes_dir}")
            return
        
        for palette_file in sorted(palettes_dir.glob("*.json")):
            convert_palette_file(palette_file)


if __name__ == "__main__":
    main()
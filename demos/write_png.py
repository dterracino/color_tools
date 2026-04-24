import zlib
import struct
import json
import argparse
from enum import IntEnum

# The 16-color palette data (with some transparency added to show off!)
COLORS_DATA = """
[
    {"r": 255, "g": 0, "b": 128, "a": 255}, {"r": 238, "g": 17, "b": 138, "a": 240}, 
    {"r": 221, "g": 34, "b": 148, "a": 220}, {"r": 204, "g": 51, "b": 158, "a": 200},
    {"r": 187, "g": 68, "b": 168, "a": 180}, {"r": 170, "g": 85, "b": 178, "a": 160},
    {"r": 153, "g": 102, "b": 188, "a": 140}, {"r": 136, "g": 119, "b": 198, "a": 120},
    {"r": 119, "g": 136, "b": 208, "a": 100}, {"r": 102, "g": 153, "b": 218, "a": 80},
    {"r": 85, "g": 170, "b": 228, "a": 60}, {"r": 68, "g": 187, "b": 238, "a": 40},
    {"r": 51, "g": 204, "b": 248, "a": 30}, {"r": 34, "g": 221, "b": 255, "a": 20},
    {"r": 17, "g": 238, "b": 255, "a": 10}, {"r": 0, "g": 255, "b": 255, "a": 0}
]
"""

class PNGColorType(IntEnum):
    GRAYSCALE = 0
    RGB = 2
    PALETTE = 3
    GRAYSCALE_ALPHA = 4
    RGBA = 6

class SimplePNGWriter:
    # PNG constants based on the official specification
    BIT_DEPTH_8 = 8
    COMPRESSION_DEFLATE = 0
    FILTER_NONE = 0
    INTERLACE_NONE = 0
    PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'

    def __init__(self, colors_json, px_width=1, px_height=1):
        self.colors = json.loads(colors_json)
        self.px_per_color_width = px_width
        self.px_per_color_height = px_height
        
        # Determine if we need an Alpha channel by checking the first color entry
        # This keeps the code DRY and adaptive!
        has_alpha = "a" in self.colors[0] if self.colors else False
        self.color_type = PNGColorType.RGBA if has_alpha else PNGColorType.RGB
        
        # Calculate total dimensions
        self.width = len(self.colors) * self.px_per_color_width
        self.height = self.px_per_color_height

    def _make_chunk(self, chunk_type, data):
        """Internal helper to package data into PNG chunks: length + type + data + crc"""
        length = struct.pack('>I', len(data))
        crc = struct.pack('>I', zlib.crc32(chunk_type + data) & 0xffffffff)
        return length + chunk_type + data + crc

    def _build_ihdr(self):
        """Builds the Image Header (IHDR) chunk."""
        ihdr_data = struct.pack(
            '>IIBBBBB', 
            self.width, 
            self.height, 
            self.BIT_DEPTH_8, 
            self.color_type, 
            self.COMPRESSION_DEFLATE, 
            self.FILTER_NONE, 
            self.INTERLACE_NONE
        )
        return self._make_chunk(b'IHDR', ihdr_data)

    def _build_idat(self):
        """Builds the Image Data (IDAT) chunk with scaled pixels."""
        row_data = bytearray()
        for color in self.colors:
            # Build the pixel components
            pixel_bytes = [color['r'], color['g'], color['b']]
            if self.color_type == PNGColorType.RGBA:
                pixel_bytes.append(color.get('a', 255)) # Default to opaque if missing
            
            pixel = bytes(pixel_bytes)
            row_data.extend(pixel * self.px_per_color_width)
        
        full_image_data = bytearray()
        for _ in range(self.height):
            full_image_data.append(self.FILTER_NONE)
            full_image_data.extend(row_data)
            
        compressed_data = zlib.compress(full_image_data)
        return self._make_chunk(b'IDAT', compressed_data)

    def _build_iend(self):
        """Builds the Image End (IEND) chunk."""
        return self._make_chunk(b'IEND', b'')

    def save(self, filename):
        """Assembles the chunks and writes the PNG file."""
        with open(filename, 'wb') as f:
            f.write(self.PNG_SIGNATURE)
            f.write(self._build_ihdr())
            f.write(self._build_idat())
            f.write(self._build_iend())
        print(f"Success! {filename} saved ({self.width}x{self.height}) using {self.color_type.name} mode. 🚀")

def run_generator():
    """Handles argument parsing and triggers the PNG generation."""
    parser = argparse.ArgumentParser(description="Generate a PNG color strip from JSON data.")
    
    parser.add_argument(
        "--width", 
        type=int, 
        default=20, 
        help="Pixels per color width (default: 20)"
    )
    parser.add_argument(
        "--height", 
        type=int, 
        default=50, 
        help="Total image height in pixels (default: 50)"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="color_swatch.png", 
        help="Output filename (default: color_swatch.png)"
    )

    args = parser.parse_args()

    # Create and save the PNG
    writer = SimplePNGWriter(COLORS_DATA, px_width=args.width, px_height=args.height)
    writer.save(args.output)

if __name__ == "__main__":
    run_generator()
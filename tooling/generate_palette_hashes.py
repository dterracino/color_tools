#!/usr/bin/env python3
"""Generate SHA-256 hashes for all palette JSON files."""

import hashlib
from pathlib import Path

def generate_hash(file_path):
    """Generate SHA-256 hash for a file."""
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

# Define palette files and their constant names
palettes = [
    ("cga4.json", "CGA4_PALETTE_HASH"),
    ("cga16.json", "CGA16_PALETTE_HASH"),
    ("ega16.json", "EGA16_PALETTE_HASH"),
    ("ega64.json", "EGA64_PALETTE_HASH"),
    ("vga.json", "VGA_PALETTE_HASH"),
    ("web.json", "WEB_PALETTE_HASH"),
]

# Calculate and print hashes
palette_dir = Path("color_tools/data/palettes")
for filename, constant_name in palettes:
    file_path = palette_dir / filename
    file_hash = generate_hash(file_path)
    print(f'{constant_name} = "{file_hash}"')

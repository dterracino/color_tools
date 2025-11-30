#!/usr/bin/env python3
"""Regenerate all palette file hashes for constants.py"""

import hashlib
from pathlib import Path

files = {
    'cga4.json': 'CGA4_PALETTE_HASH',
    'cga16.json': 'CGA16_PALETTE_HASH',
    'commodore64.json': 'COMMODORE64_PALETTE_HASH', 
    'ega16.json': 'EGA16_PALETTE_HASH',
    'ega64.json': 'EGA64_PALETTE_HASH',
    'gameboy.json': 'GAMEBOY_PALETTE_HASH',
    'gameboy_dmg.json': 'GAMEBOY_DMG_PALETTE_HASH',
    'gameboy_gbl.json': 'GAMEBOY_GBL_PALETTE_HASH',
    'gameboy_mgb.json': 'GAMEBOY_MGB_PALETTE_HASH',
    'genesis.json': 'GENESIS_PALETTE_HASH',
    'nes.json': 'NES_PALETTE_HASH',
    'sms.json': 'SMS_PALETTE_HASH',
    'turbografx16.json': 'TURBOGRAFX16_PALETTE_HASH',
    'vga.json': 'VGA_PALETTE_HASH',
    'web.json': 'WEB_PALETTE_HASH',
}

# Script is in tools/ directory, palettes are in ../color_tools/data/palettes/
script_dir = Path(__file__).parent
palettes_dir = script_dir.parent / "color_tools" / "data" / "palettes"

print("# Palette file hashes for constants.py")
print("# Copy these to update the constants file:")
print()

for filepath, const_name in files.items():
    full_path = palettes_dir / filepath
    if full_path.exists():
        hash_val = hashlib.sha256(full_path.read_bytes()).hexdigest()
        print(f'    {const_name} = "{hash_val}"')
    else:
        print(f'    {const_name} = "FILE_NOT_FOUND"')
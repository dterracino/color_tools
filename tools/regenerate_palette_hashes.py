#!/usr/bin/env python3
"""Regenerate all palette file hashes for constants.py"""

import hashlib
from pathlib import Path

files = {
    'amstrad-cpc.json': 'AMSTRAD_CPC_PALETTE_HASH',
    'apple2.json': 'APPLE2_PALETTE_HASH',
    'bbc-micro.json': 'BBC_MICRO_PALETTE_HASH',
    'cga4.json': 'CGA4_PALETTE_HASH',
    'cga16.json': 'CGA16_PALETTE_HASH',
    'colecovision.json': 'COLECOVISION_PALETTE_HASH',
    'commodore64.json': 'COMMODORE64_PALETTE_HASH',
    'crayola.json': 'CRAYOLA_PALETTE_HASH',
    'ega16.json': 'EGA16_PALETTE_HASH',
    'ega64.json': 'EGA64_PALETTE_HASH',
    'gameboy.json': 'GAMEBOY_PALETTE_HASH',
    'gameboy-dmg.json': 'GAMEBOY_DMG_PALETTE_HASH',
    'gameboy-light.json': 'GAMEBOY_LIGHT_PALETTE_HASH',
    'gameboy-pocket.json': 'GAMEBOY_POCKET_PALETTE_HASH',
    'intellivision.json': 'INTELLIVISION_PALETTE_HASH',
    'macintosh.json': 'MACINTOSH_PALETTE_HASH',
    'msx1.json': 'MSX1_PALETTE_HASH',
    'nes.json': 'NES_PALETTE_HASH',
    'pico8.json': 'PICO8_PALETTE_HASH',
    'sg-1000.json': 'SG_1000_PALETTE_HASH',
    'sms.json': 'SMS_PALETTE_HASH',
    'tandy16.json': 'TANDY16_PALETTE_HASH',
    'ti-99-4a.json': 'TI_99_4A_PALETTE_HASH',
    'tic80.json': 'TIC80_PALETTE_HASH',
    'vga.json': 'VGA_PALETTE_HASH',
    'vic-20.json': 'VIC_20_PALETTE_HASH',
    'virtualboy.json': 'VIRTUALBOY_PALETTE_HASH',
    'web.json': 'WEB_PALETTE_HASH',
    'zx-spectrum.json': 'ZX_SPECTRUM_PALETTE_HASH',
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
        hash_val = hashlib.sha256(full_path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        print(f'    {const_name} = "{hash_val}"')
    else:
        print(f'    {const_name} = "FILE_NOT_FOUND"')

import hashlib
from pathlib import Path

palette_dir = Path('color_tools/data/palettes')
new_palettes = ['apple2.json', 'macintosh.json', 'gameboy-color.json', 'tandy16.json']

for palette_file in new_palettes:
    file_path = palette_dir / palette_file
    hash_val = hashlib.sha256(file_path.read_bytes()).hexdigest()
    const_name = palette_file.replace('.json', '').replace('-', '_').upper() + '_PALETTE_HASH'
    print(f'{const_name} = "{hash_val}"')

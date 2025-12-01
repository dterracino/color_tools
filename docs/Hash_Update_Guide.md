# Hash Integrity System - Update Guide

This document explains how to update SHA-256 hashes when data files or constants change in the color_tools project.

## Overview

The color_tools project uses SHA-256 hashes to protect critical data from accidental or malicious modification. Three types of integrity verification are provided:

1. **ColorConstants Hash** - Protects color science constants
2. **Data File Hashes** - Protects core JSON data files  
3. **Transformation Matrices Hash** - Protects CVD transformation matrices

## When to Update Hashes

### Palette Files Changed

**Files affected:** `color_tools/data/palettes/*.json`

**Steps:**

1. Regenerate individual palette hashes in `constants.py`
2. Update `ColorConstants._EXPECTED_HASH` (since you added new constants)
3. Verify with `--verify-all`

### Main Data Files Changed

**Files affected:**

- `color_tools/data/colors.json`
- `color_tools/data/filaments.json`
- `color_tools/data/maker_synonyms.json`

**Steps:**

1. Regenerate individual data file hashes in `constants.py`
2. Update `ColorConstants._EXPECTED_HASH` (since you modified constants)
3. Verify with `--verify-all`

### Color Science Constants Changed

**Files affected:** `color_tools/constants.py` (ColorConstants class values)

**⚠️ IMPORTANT: TO BE CLEAR, THE CONSTANTS FILE SHOULD NOT CHANGE. THESE ARE DEFINED COLOR SCIENCE CONSTANTS.**

The color science constants (D65 white point, transformation matrices, Delta E coefficients, etc.) are from international standards (CIE, sRGB spec) and should never be modified unless there's an error in the implementation or a standards update.

**The main reason the ColorConstants hash changes is because the constants.py file contains hash values for other files (data files, palette files). When those file hashes are updated, the constants.py file content changes, requiring a new hash.**

**Steps:**

1. Regenerate `ColorConstants._EXPECTED_HASH`
2. Verify with `--verify-constants`

### Transformation Matrices Changed

**Files affected:** `color_tools/matrices.py` (matrix constant values)

**Steps:**

1. Regenerate `MATRICES_EXPECTED_HASH` in `constants.py`
2. Update `ColorConstants._EXPECTED_HASH` (since you modified constants)
3. Verify with `--verify-matrices`

## Hash Generation Commands

### Individual Palette File Hashes

```bash
# Generate hash for a specific palette file
python -c "
import hashlib
from pathlib import Path
palette_file = Path('color_tools/data/palettes/cga4.json')
hash_val = hashlib.sha256(palette_file.read_bytes()).hexdigest()
print(f'CGA4_PALETTE_HASH = \"{hash_val}\"')
"
```

### All Palette File Hashes

```bash
# Generate hashes for all palette files
python -c "
import hashlib
from pathlib import Path

palette_files = {
    'cga4.json': 'CGA4_PALETTE_HASH',
    'cga16.json': 'CGA16_PALETTE_HASH',
    'ega16.json': 'EGA16_PALETTE_HASH',
    'ega64.json': 'EGA64_PALETTE_HASH',
    'vga.json': 'VGA_PALETTE_HASH',
    'web.json': 'WEB_PALETTE_HASH',
    'gameboy.json': 'GAMEBOY_PALETTE_HASH',
    'gameboy_dmg.json': 'GAMEBOY_DMG_PALETTE_HASH',
    'gameboy_gbl.json': 'GAMEBOY_GBL_PALETTE_HASH',
    'gameboy_mgb.json': 'GAMEBOY_MGB_PALETTE_HASH',
    'nes.json': 'NES_PALETTE_HASH',
    'sms.json': 'SMS_PALETTE_HASH',
    'commodore64.json': 'COMMODORE64_PALETTE_HASH',
    'virtualboy.json': 'VIRTUALBOY_PALETTE_HASH',
}

palettes_dir = Path('color_tools/data/palettes')
for filename, const_name in palette_files.items():
    filepath = palettes_dir / filename
    if filepath.exists():
        hash_val = hashlib.sha256(filepath.read_bytes()).hexdigest()
        print(f'{const_name} = \"{hash_val}\"')
    else:
        print(f'# {const_name} = \"\" # File not found: {filename}')
"
```

### All Main Data File Hashes

```bash
# Generate hashes for main data files
python -c "
import hashlib
from pathlib import Path

data_files = {
    'colors.json': 'COLORS_JSON_HASH',
    'filaments.json': 'FILAMENTS_JSON_HASH', 
    'maker_synonyms.json': 'MAKER_SYNONYMS_JSON_HASH',
}

data_dir = Path('color_tools/data')
for filename, const_name in data_files.items():
    filepath = data_dir / filename
    hash_val = hashlib.sha256(filepath.read_bytes()).hexdigest()
    print(f'{const_name} = \"{hash_val}\"')
"
```

### Transformation Matrices Hash

```bash
# Generate transformation matrices hash
python -c "
from color_tools.constants import ColorConstants
print(f'MATRICES_EXPECTED_HASH = \"{ColorConstants._compute_matrices_hash()}\"')
"
```

### ColorConstants Hash

```bash
# Generate ColorConstants hash (do this AFTER updating other hashes)
python -c "
from color_tools.constants import ColorConstants
print(f'_EXPECTED_HASH = \"{ColorConstants._compute_hash()}\"')
"
```

## Update Process Workflow

### When Multiple Files Change (e.g., after running compact_color_arrays.py)

1. **Update individual file hashes** - Run commands above for changed files
2. **Update constants.py** - Copy the new hash values into the file
3. **Regenerate ColorConstants hash** - Run the ColorConstants hash command
4. **Update _EXPECTED_HASH** - Copy the new ColorConstants hash into the file
5. **Verify everything** - Run `python -m color_tools --verify-all`

### Hash Update Script

A helper script `tooling/update_hashes.py` is available to automate hash generation:

#### Manual Mode (Default)
```bash
# Generate all hashes and show values to copy
python tooling/update_hashes.py
```

This will display all hash values that you need to copy into `constants.py` manually.

#### Automatic Update Mode
```bash
# Automatically update constants.py with new hashes
python tooling/update_hashes.py --autoupdate
```

This will:
- Generate all hash values
- Ask for confirmation before modifying files
- Automatically update `constants.py` with new hash values  
- Generate the final ColorConstants hash
- Provide verification commands

**Safety features:**
- Requires explicit confirmation before modifying files
- Can be cancelled at any time (no files modified)
- Shows exactly what will be updated before proceeding

#### Constants-Only Mode
```bash
# Only generate the final ColorConstants hash
python tooling/update_hashes.py --constants-only
```

Use this for the final step after manually updating hash values in `constants.py`.

#### Script Capabilities

The script will:
- Scan for all data files and generate their hashes
- Generate transformation matrices hash  
- Generate ColorConstants hash
- Display the values you need to copy into constants.py
- Provide verification commands to run
- Optionally update files automatically with confirmation

## Important Notes

### What Gets Hashed in ColorConstants

The `ColorConstants._compute_hash()` method hashes:

- All UPPERCASE constant values in the ColorConstants class
- This includes color science constants AND file hash constants
- Utility methods and private variables are NOT included

### Adding New Constants

When adding new constants to `ColorConstants`:

1. Add your new constant (e.g., `NEW_PALETTE_HASH = "..."`)
2. Regenerate `_EXPECTED_HASH` using the ColorConstants hash command above
3. The new constant will automatically be included in future hash calculations

### Matrix Hash Details

The transformation matrices hash includes only:

- The 6 main transformation matrices in `matrices.py`
- Adding utility functions to `matrices.py` does NOT require hash updates
- Only changes to matrix constant values require hash regeneration

## Verification Commands

```bash
# Verify specific components
python -m color_tools --verify-constants
python -m color_tools --verify-data  
python -m color_tools --verify-matrices

# Verify everything
python -m color_tools --verify-all
```

## Troubleshooting

**Hash verification fails after file changes:**

- Make sure you updated the correct hash constant in `constants.py`
- Regenerate ColorConstants hash AFTER updating individual file hashes
- Check that file paths are correct in hash generation commands

**New palette files not recognized:**

- Add the new palette file to the palette_files dictionary in the commands above
- Add the corresponding hash constant to `constants.py`
- Regenerate ColorConstants hash to include the new constant

**Script fails to find files:**

- Make sure you're running commands from the project root directory
- Check that file paths in the commands match your actual file structure

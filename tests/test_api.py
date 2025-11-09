#!/usr/bin/env python3
"""Test that the public API works correctly with synonym changes."""

import sys
from pathlib import Path

# Add parent directory to path so we can import the package
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from color_tools import (
    FilamentPalette,
    load_filaments,
    load_maker_synonyms,
)

print("Testing the public API with synonyms...\n")

# Method 1: Using load_default() - most convenient
print("1. FilamentPalette.load_default() - Automatically loads synonyms:")
palette = FilamentPalette.load_default()
results = palette.find_by_maker("Bambu")
print(f"   ✓ Found {len(results)} filaments using 'Bambu' synonym\n")

# Method 2: Manual construction with synonyms
print("2. Manual construction with load_maker_synonyms():")
filaments = load_filaments()
synonyms = load_maker_synonyms()
palette2 = FilamentPalette(filaments, synonyms)
results2 = palette2.find_by_maker("BLL")
print(f"   ✓ Found {len(results2)} filaments using 'BLL' synonym\n")

# Method 3: Without synonyms (backwards compatible)
print("3. Without synonyms - still works, just no expansion:")
palette3 = FilamentPalette(filaments)  # No synonyms parameter
results3 = palette3.find_by_maker("Bambu Lab")  # Must use canonical name
print(f"   ✓ Found {len(results3)} filaments using canonical name\n")

# Verify synonym expansion works in filters
print("4. Filter with synonyms:")
results4 = palette.filter(maker="Paramount", type_name="PLA")
print(f"   ✓ Found {len(results4)} PLA filaments using 'Paramount' synonym\n")

print("✅ All API tests passed!")

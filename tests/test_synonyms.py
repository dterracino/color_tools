#!/usr/bin/env python3
"""Test maker synonyms functionality."""

import sys
from pathlib import Path

# Add parent directory to path so we can import the package
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Now import from the package
from color_tools.palette import FilamentPalette

# Test synonym expansion
palette = FilamentPalette.load_default()

print("Testing maker synonym 'Bambu' (should find 'Bambu Lab'):")
results = palette.find_by_maker("Bambu")
print(f"  Found {len(results)} filaments")
if results:
    print(f"  First result: {results[0].maker} - {results[0].color}")

print("\nTesting maker synonym 'BLL' (should find 'Bambu Lab'):")
results = palette.find_by_maker("BLL")
print(f"  Found {len(results)} filaments")
if results:
    print(f"  First result: {results[0].maker} - {results[0].color}")

print("\nTesting canonical name 'Bambu Lab':")
results = palette.find_by_maker("Bambu Lab")
print(f"  Found {len(results)} filaments")
if results:
    print(f"  First result: {results[0].maker} - {results[0].color}")

print("\nTesting Paramount synonym:")
results = palette.find_by_maker("Paramount")
print(f"  Found {len(results)} filaments")
if results:
    print(f"  First result: {results[0].maker} - {results[0].color}")

print("\nTesting filter with synonym:")
results = palette.filter(maker="Bambu", type_name="PLA")
print(f"  Found {len(results)} PLA filaments from 'Bambu' (Bambu Lab)")

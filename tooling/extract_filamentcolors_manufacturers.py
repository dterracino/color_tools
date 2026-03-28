"""
Extract unique manufacturers from FilamentColors.xyz data.

This script reads the downloaded swatches.json and extracts all unique manufacturers
to a manufacturers.json file. You can then copy this to manufacturers-import.json
and edit it to select which manufacturers you want to process.

Usage:
    python extract_filamentcolors_manufacturers.py
"""

import json
from pathlib import Path

# Paths
SOURCE_DIR = Path(__file__).parent.parent / ".source_data" / "filamentcolors.xyz"
SWATCHES_FILE = SOURCE_DIR / "swatches.json"
MANUFACTURERS_FILE = SOURCE_DIR / "manufacturers.json"
MANUFACTURERS_IMPORT_FILE = SOURCE_DIR / "manufacturers-import.json"


def extract_manufacturers():
    """Extract unique manufacturers from swatches data."""
    
    # Check if swatches file exists
    if not SWATCHES_FILE.exists():
        print(f"Error: Swatches file not found: {SWATCHES_FILE}")
        print("Run 'python filamentcolors_library.py' first to download the data.")
        return
    
    # Load swatches data
    print(f"Loading swatches from: {SWATCHES_FILE}")
    with open(SWATCHES_FILE, "r", encoding="utf-8") as f:
        swatches = json.load(f)
    
    print(f"Found {len(swatches)} total swatches")
    
    # Extract unique manufacturers (keyed by ID to avoid duplicates)
    manufacturers_dict = {}
    for swatch in swatches:
        mfr = swatch.get("manufacturer", {})
        mfr_id = mfr.get("id")
        if mfr_id and mfr_id not in manufacturers_dict:
            manufacturers_dict[mfr_id] = {
                "id": mfr_id,
                "name": mfr.get("name", ""),
                "website": mfr.get("website", "")
            }
    
    # Convert to sorted list (by name)
    manufacturers_list = sorted(
        manufacturers_dict.values(),
        key=lambda x: x["name"].lower()
    )
    
    # Save to manufacturers.json
    with open(MANUFACTURERS_FILE, "w", encoding="utf-8") as f:
        json.dump(manufacturers_list, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Extracted {len(manufacturers_list)} unique manufacturers")
    print(f"✓ Saved to: {MANUFACTURERS_FILE}")
    
    # Check if import file exists
    if MANUFACTURERS_IMPORT_FILE.exists():
        with open(MANUFACTURERS_IMPORT_FILE, "r", encoding="utf-8") as f:
            import_list = json.load(f)
        enabled_count = sum(1 for m in import_list if m.get("enabled", True))
        print(f"\n✓ Found existing import configuration: {MANUFACTURERS_IMPORT_FILE}")
        print(f"  - {len(import_list)} manufacturers selected for import")
    else:
        print(f"\nNext steps:")
        print(f"1. Copy {MANUFACTURERS_FILE.name} to {MANUFACTURERS_IMPORT_FILE.name}")
        print(f"2. Delete manufacturers you don't want from {MANUFACTURERS_IMPORT_FILE.name}")
        print(f"3. Run the import/analysis script (to be created next)")
    
    # Show sample of manufacturers
    print(f"\nSample manufacturers (first 10):")
    for mfr in manufacturers_list[:10]:
        print(f"  - {mfr['name']}")
    
    if len(manufacturers_list) > 10:
        print(f"  ... and {len(manufacturers_list) - 10} more")


if __name__ == "__main__":
    extract_manufacturers()

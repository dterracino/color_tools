# Managing Owned Filaments

This guide explains how to track and filter filaments you own using the owned filaments system.

## Overview

The owned filaments feature allows you to:
- Track which filaments from the database you actually own
- Filter searches to show only owned filaments
- Find the best color match from your personal inventory

## Important Distinction

**owned-filaments.json vs user-filaments.json:**

- **`owned-filaments.json`** (this guide) - References filaments **by ID** from the database
  - Tracks which existing filaments you own
  - Uses filament IDs to reference core or user-defined filaments
  - Located at `color_tools/data/user/owned-filaments.json`

- **`user-filaments.json`** (different purpose) - Adds **new custom filaments** to the database
  - For filaments NOT in the core database
  - Extends the database with your own filament definitions
  - See [Customization Guide](Customization.md) for details

## Setup

### 1. Find Filament IDs

First, find the IDs of filaments you want to mark as owned. Every filament in the database has a unique ID.

**View filaments with their IDs:**
```bash
# List all Bambu Lab PLA filaments
python -m color_tools filament --maker "Bambu Lab" --type PLA

# The ID is the unique identifier like: bambu-lab-pla-basic-black
```

**ID Format:**
- Generated from: `maker-type-finish-color`
- Lowercase, hyphen-separated
- Example: `"bambu-lab-pla-silk-plus-red"`

### 2. Create owned-filaments.json

Create the file at `color_tools/data/user/owned-filaments.json`:

```json
{
  "owned_ids": [
    "bambu-lab-pla-basic-black",
    "bambu-lab-pla-basic-white",
    "polymaker-pla-matte-red"
  ]
}
```

**Alternative format** (simple list):
```json
[
  "bambu-lab-pla-basic-black",
  "bambu-lab-pla-basic-white",
  "polymaker-pla-matte-red"
]
```

## Command-Line Usage

### List Owned Filaments

```bash
# List all owned filaments
color-tools filament --owned-only

# List owned filaments by maker
color-tools filament --maker "Bambu Lab" --owned-only

# List owned PLA filaments
color-tools filament --type PLA --owned-only

# Combine filters
color-tools filament --maker "Bambu Lab" --type PLA --finish Silk --owned-only
```

### Find Nearest Owned Filament

```bash
# Find closest owned filament to a color (RGB)
color-tools filament --nearest --value 255 128 64 --owned-only

# Find closest owned filament to a color (hex)
color-tools filament --nearest --hex "#FF8040" --owned-only

# Find top 5 closest owned filaments
color-tools filament --nearest --value 255 128 64 --count 5 --owned-only

# Find closest owned filament with specific material
color-tools filament --nearest --value 255 128 64 --type PLA --owned-only
```

### Combine Filters

```bash
# Find closest owned Bambu Lab PLA
color-tools filament --nearest --value 255 128 64 \
  --maker "Bambu Lab" --type PLA --owned-only

# Export owned filaments to CSV
color-tools filament --owned-only --export csv --output my-inventory.csv
```

## Library Usage

### Basic Filtering

```python
from color_tools import FilamentPalette

# Load palette with owned IDs
palette = FilamentPalette.load_default()

# Check how many you own
owned_count = len([f for f in palette.records if f.id in palette.owned_ids])
print(f"You own {owned_count} filaments")

# Get only owned filaments
owned = palette.filter(owned_only=True)
print(f"Owned filaments: {len(owned)}")

# List owned filaments
for filament in owned:
    print(f"- {filament.maker} {filament.type} {filament.color}")
```

### Finding Nearest Owned Filament

```python
from color_tools import FilamentPalette

palette = FilamentPalette.load_default()

# Find closest owned filament to a color
target_rgb = (255, 128, 64)  # Orange
filament, distance = palette.nearest_filament(
    target_rgb,
    owned_only=True
)

print(f"Best match: {filament.maker} {filament.color}")
print(f"Distance: ΔE {distance:.2f}")
print(f"Hex: {filament.hex}")
print(f"ID: {filament.id}")
```

### Finding Multiple Matches

```python
from color_tools import FilamentPalette

palette = FilamentPalette.load_default()

# Get top 5 closest owned filaments
target_rgb = (128, 64, 200)  # Purple
results = palette.nearest_filaments(
    target_rgb,
    count=5,
    owned_only=True
)

print("Top 5 matches from your inventory:")
for i, (filament, distance) in enumerate(results, 1):
    print(f"{i}. {filament.maker} {filament.color} (ΔE: {distance:.2f})")
```

### Manual Loading

```python
from color_tools import FilamentPalette, load_filaments, load_maker_synonyms, load_owned_filaments

# Load everything manually
filaments = load_filaments()
synonyms = load_maker_synonyms()
owned_ids = load_owned_filaments()

# Create palette
palette = FilamentPalette(filaments, synonyms, owned_ids)

print(f"Total filaments in database: {len(filaments)}")
print(f"Filaments you own: {len(owned_ids)}")
```

## Tips and Best Practices

### 1. Finding Filament IDs

The easiest way to find filament IDs is to search for them:

```bash
# Search for a specific maker/type
color-tools filament --maker "Bambu Lab" --type PLA

# The output shows each filament in format:
# Maker Type Finish - Color (#hex)
# The ID follows the pattern: maker-type-finish-color (lowercase, hyphens)
```

### 2. Tracking Custom Filaments

If you've added custom filaments via `user-filaments.json`, you can track those as owned too:

1. Add your custom filament to `user-filaments.json` with an ID
2. Add that same ID to `owned-filaments.json`

Example custom filament in `user-filaments.json`:
```json
[
  {
    "id": "my-local-shop-pla-basic-red",
    "maker": "My Local Shop",
    "type": "PLA",
    "finish": "Basic",
    "color": "Red",
    "hex": "#CC0000"
  }
]
```

Then reference it in `owned-filaments.json`:
```json
{
  "owned_ids": [
    "my-local-shop-pla-basic-red"
  ]
}
```

### 3. Maintaining Your Inventory

```bash
# Periodically review your owned list
color-tools filament --owned-only

# Export for spreadsheet tracking
color-tools filament --owned-only --export csv --output inventory.csv
```

### 4. Workflow Example

```bash
# 1. Find filament ID you want to add
color-tools filament --maker "Bambu Lab" --color "Black"

# 2. Add the ID to owned-filaments.json
# Edit: color_tools/data/user/owned-filaments.json

# 3. Verify it's tracked
color-tools filament --owned-only | grep "Black"

# 4. Use it for color matching
color-tools filament --nearest --hex "#FF6B35" --owned-only
```

## Error Handling

### No Owned Filaments Found

If you get "No filaments match the specified filters":
- Check that `owned-filaments.json` exists
- Verify the IDs in the file are correct
- Make sure the filaments exist in the database

### Invalid ID

If a filament ID doesn't match any filament:
- The ID is silently ignored (no error)
- Only valid IDs are used for filtering

### File Format Error

If the JSON file is invalid:
- A warning is logged
- The function returns an empty set
- Check JSON syntax with a validator

## See Also

- [Customization Guide](Customization.md) - Using user-filaments.json to add custom filaments
- [Usage Guide](Usage.md) - Full API reference
- [FAQ](FAQ.md) - Common questions

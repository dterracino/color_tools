# Managing Owned Filaments

This guide explains how to track and manage your personal filament inventory in color_tools.

## Overview

The owned filaments feature allows you to:
- Mark which filaments you own
- Filter searches to only show owned filaments
- Find the best match from your personal inventory
- Maintain a separate list from the core database

## Setup

### 1. Create Your User Filament File

Create or edit `color_tools/data/user/user-filaments.json`:

```json
[
  {
    "maker": "Bambu Lab",
    "type": "PLA",
    "finish": "Basic",
    "color": "Black",
    "hex": "#1A1A1A",
    "owned": true
  },
  {
    "maker": "Bambu Lab",
    "type": "PLA",
    "finish": "Silk",
    "color": "Red",
    "hex": "#C41E3A",
    "owned": true
  }
]
```

### 2. Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `maker` | ✅ Yes | Manufacturer name (e.g., "Bambu Lab") |
| `type` | ✅ Yes | Filament material (e.g., "PLA", "PETG") |
| `finish` | ❌ No | Surface finish (e.g., "Matte", "Silk") |
| `color` | ✅ Yes | Color name as labeled by manufacturer |
| `hex` | ✅ Yes | Hex color code (e.g., "#FF0000") |
| `owned` | ❌ No | Set to `true` for owned filaments (default: `false`) |
| `id` | ❌ No | Unique identifier (auto-generated if omitted) |
| `td_value` | ❌ No | Translucency depth for HueForge printing |
| `other_names` | ❌ No | Alternative color names |

**Important**: The `owned` field is what enables filtering. Set it to `true` for filaments you own.

## Command-Line Usage

### List Owned Filaments

```bash
# List all owned filaments
color-tools filament --owned-only

# List owned filaments by maker
color-tools filament --maker "Bambu Lab" --owned-only

# List owned PLA filaments
color-tools filament --type PLA --owned-only

# List owned filaments with specific finish
color-tools filament --finish Silk --owned-only
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
color-tools filament --owned-only --export csv --output my-filaments.csv
```

## Library Usage

### Basic Filtering

```python
from color_tools import FilamentPalette

# Load palette with all filaments
palette = FilamentPalette.load_default()

# Get only owned filaments
owned = palette.filter(owned_only=True)
print(f"You own {len(owned)} filaments")

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

### Combined Filtering

```python
from color_tools import FilamentPalette

palette = FilamentPalette.load_default()

# Find closest owned Bambu Lab PLA
filament, distance = palette.nearest_filament(
    (255, 0, 0),  # Red
    maker="Bambu Lab",
    type_name="PLA",
    owned_only=True
)

# Or filter first, then search
owned_bambu_pla = palette.filter(
    maker="Bambu Lab",
    type_name="PLA",
    owned_only=True
)
print(f"You own {len(owned_bambu_pla)} Bambu Lab PLA filaments")
```

## Tips and Best Practices

### 1. Start Simple

Begin by adding just your most-used filaments with `"owned": true`. You can expand over time.

### 2. Use Accurate Colors

Use the actual hex color from the manufacturer or measure it yourself. Accurate colors lead to better matching.

### 3. Reference Existing Filaments

Check `color_tools/data/filaments.json` for examples of how manufacturers name their filaments and finishes.

### 4. Combine with Other Filters

The `owned_only` filter works seamlessly with maker, type, and finish filters:

```bash
# Find owned Bambu Lab Silk filaments only
color-tools filament --maker "Bambu Lab" --finish Silk --owned-only
```

### 5. Export for Tracking

Export your owned filaments to CSV for inventory management:

```bash
color-tools filament --owned-only --export csv --output inventory.csv
```

### 6. Mix Owned and Reference Filaments

Your `user-filaments.json` can contain both owned and non-owned filaments. This is useful for:
- Filaments you're considering purchasing (`"owned": false`)
- Custom or experimental filaments
- Filaments not in the core database

## Error Handling

### No Owned Filaments Found

If you get "No filaments match the specified filters" when using `--owned-only`, it means:
1. You haven't set `"owned": true` for any filaments
2. Your filters are too restrictive (e.g., searching for a maker you don't own)

Solution: Check your `user-filaments.json` and ensure you have filaments marked with `"owned": true`.

### Filament Not Loading

If your filaments don't appear:
1. Verify JSON syntax is valid (use a JSON validator)
2. Check that required fields (maker, type, color, hex) are present
3. Ensure the file is at `color_tools/data/user/user-filaments.json`

## Example Workflow

Here's a complete workflow for managing owned filaments:

```bash
# 1. Create your inventory (edit user-filaments.json)
# 2. Verify it loads correctly
color-tools filament --owned-only

# 3. Find what you can use for a project color
color-tools filament --nearest --hex "#FF6B35" --owned-only --count 3

# 4. Filter by material type for your printer
color-tools filament --nearest --hex "#FF6B35" --type PLA --owned-only

# 5. Export your inventory for reference
color-tools filament --owned-only --export csv --output my-filaments.csv
```

## Advanced: Using IDs

For the most precise matching, reference core database filaments by ID:

```json
[
  {
    "id": "bambu-lab-pla-basic-black",
    "maker": "Bambu Lab",
    "type": "PLA",
    "finish": "Basic",
    "color": "Black",
    "hex": "#1A1A1A",
    "owned": true
  }
]
```

This ensures your owned filament exactly matches the core database entry, including color values and metadata.

## See Also

- [Customization Guide](Customization.md) - User data files in general
- [Example Owned Filaments](../docs/example-owned-filaments.json) - Complete example file
- [Usage Guide](Usage.md) - Full API reference

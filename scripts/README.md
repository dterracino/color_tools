# Scripts Directory

PowerShell scripts for common color_tools operations.

## Available Scripts

### `find-nearest-filament.ps1`

Find the nearest filaments to a given color.

**Usage:**

```powershell
# Basic usage - find 5 nearest filaments
.\find-nearest-filament.ps1 "#7f0b00"

# Find 10 nearest filaments
.\find-nearest-filament.ps1 "#7f0b00" -Count 10

# Filter by maker
.\find-nearest-filament.ps1 "#7f0b00" -Maker "Bambu Lab"

# Filter by type
.\find-nearest-filament.ps1 "#7f0b00" -Type "PLA" -Count 3

# Combine filters
.\find-nearest-filament.ps1 "#FF0000" -Maker "Polymaker" -Type "PETG" -Count 5

# Use different distance metric
.\find-nearest-filament.ps1 "#7f0b00" -Metric de94
```

**Parameters:**

- `-Hex` (required): Hex color code (e.g., "#7f0b00" or "7f0b00")
- `-Count`: Number of results to return (default: 5, max: 50)
- `-Maker`: Filter by filament maker (supports synonyms)
- `-Type`: Filter by filament type (PLA, PETG, TPU, etc.)
- `-Metric`: Distance metric (euclidean, de76, de94, de2000, cmc)

## Naming Convention

Scripts use **kebab-case** with **verb-noun** pattern:

- `find-nearest-filament.ps1` - Search operations
- `get-color-info.ps1` - Retrieval operations
- `convert-color-space.ps1` - Transformation operations

This makes them:

- Easy to remember and type
- Consistent with PowerShell conventions
- Self-documenting (name describes what it does)

## Adding New Scripts

When adding new scripts:

1. Use kebab-case naming
2. Follow verb-noun pattern
3. Add comprehensive help comments (`.SYNOPSIS`, `.DESCRIPTION`, `.EXAMPLE`)
4. Include parameter validation where appropriate
5. Update this README with usage examples

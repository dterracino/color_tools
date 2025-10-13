# GitHub Copilot Instructions for color_tools

## Project Overview

This is a color science library for Python 3.7+ that provides:
- Accurate color space conversions (RGB, LAB, LCH, HSL, XYZ)
- Perceptual color distance metrics (Delta E formulas)
- CSS color and 3D printing filament databases
- Gamut checking and color matching

## Code Style and Standards

### General Python Guidelines
- Use Python 3.7+ compatible syntax
- Follow PEP 8 style conventions
- Use `from __future__ import annotations` for forward references
- Use type hints for all function signatures: `Tuple[int, int, int]`, `Optional[str]`, etc.
- Write comprehensive docstrings for all public functions and classes
- Use descriptive variable names that reflect color science terminology

### Data Classes and Immutability
- Use `@dataclass(frozen=True)` for immutable color and filament records
- Color data should be immutable once created (colors ARE what they ARE)
- Use tuple types for color values: `Tuple[int, int, int]` for RGB, `Tuple[float, float, float]` for LAB/HSL

### Documentation Style
- Write clear, educational docstrings with examples
- Explain the "why" behind color science choices
- Use friendly emoji occasionally to make documentation engaging (🎨, 📇, etc.)
- Include mathematical formulas where relevant (e.g., "√((x₁-x₂)² + (y₁-y₂)² + (z₁-z₂)²)")

### Module Organization
```
conversions.py  # Color space conversion functions
distance.py     # Distance metrics (Delta E formulas)
gamut.py        # sRGB gamut operations
palette.py      # Color/filament databases and search
constants.py    # Immutable color science constants
config.py       # Thread-safe runtime configuration
cli.py          # Command-line interface (imports from everywhere)
```

## Critical Requirements

### Color Science Integrity
- **NEVER modify values in `ColorConstants` class** - these are from international standards (CIE, sRGB spec)
- Constants include: D65 white point, transformation matrices, gamma correction values
- Always verify constants integrity after changes: `python color_tools.py --verify-constants`
- Constants are protected by SHA-256 hash verification

### Library Dependencies
- **Use ONLY Python standard library** - no external dependencies (except type hints)
- Available modules: `math`, `colorsys`, `json`, `hashlib`, `threading`, `argparse`, `dataclasses`, `typing`
- If you need functionality, implement it from scratch using standard library

### Thread Safety
- Runtime configuration uses `threading.local()` for thread-safe per-thread settings
- Example: dual-color mode for filaments must be thread-local

### Performance Considerations
- Use indexed lookups (O(1)) for name/RGB searches in palettes
- Nearest neighbor search is O(n) but optimized with early filtering
- Encourage filtering by maker/type before nearest neighbor searches

## Testing and Verification

### Running the Tool
```bash
# Test CLI commands
python color_tools.py color --name coral
python color_tools.py filament --list-makers
python color_tools.py convert --from rgb --to lab --value 255 128 64

# Verify color science constants
python color_tools.py --verify-constants
```

### Testing Requirements
- Test color conversions with known reference values
- Verify Delta E calculations match published examples
- Test gamut boundary cases (colors outside sRGB)
- Test thread safety of configuration
- Validate JSON data loading and palette indexing

### Error Handling
- Validate color values are in expected ranges (RGB: 0-255, LAB: specific bounds)
- Provide helpful error messages for invalid input
- Handle edge cases: out-of-gamut colors, division by zero in distance formulas

## CLI Architecture

### Command Structure
The CLI has three main commands:
1. **color**: Search CSS colors by name or find nearest color
2. **filament**: Search 3D printing filaments with filtering (maker, type, finish)
3. **convert**: Convert between color spaces and check gamut

### Global Arguments
- `--json PATH`: Custom JSON data file path
- `--verify-constants`: Verify integrity of color science constants

### Dual-Color Mode
- Some filaments have two colors (hex and hex2)
- Mode determines which color to use: "first" (default), "second", or "mix"
- Must be set BEFORE loading FilamentPalette

## Data Files

### color_tools.json Structure
```json
{
  "colors": [
    {
      "name": "coral",
      "hex": "#FF7F50",
      "rgb": {"r": 255, "g": 127, "b": 80},
      "hsl": [16.1, 100.0, 65.7],
      "lab": [67.3, 44.6, 49.7]
    }
  ],
  "filaments": [
    {
      "maker": "Prusament",
      "type": "PLA",
      "finish": "Matte",
      "color": "Jet Black",
      "hex": "#000000",
      "td_value": 0.1
    }
  ]
}
```

## Security and Best Practices

### Data Validation
- Validate all external input (JSON files, CLI arguments)
- Check color values are in valid ranges before processing
- Handle malformed JSON gracefully with informative errors

### Code Quality
- Keep functions focused and single-purpose
- Avoid deep nesting (max 3-4 levels)
- Use early returns to reduce complexity
- Comment only when explaining non-obvious color science concepts

### Import Organization
- Group imports: standard library, then internal modules
- Use explicit imports: `from color_tools.conversions import rgb_to_lab`
- Avoid circular imports (cli.py is the "top" that imports everything)

## Common Patterns

### Color Conversion Chain
```python
# RGB → XYZ → LAB (forward)
rgb = (255, 128, 64)
xyz = rgb_to_xyz(rgb)
lab = xyz_to_lab(xyz)

# LAB → XYZ → RGB (reverse)
lab = (65.2, 25.8, -15.4)
xyz = lab_to_xyz(lab)
rgb = xyz_to_rgb(xyz)
```

### Distance Metric Selection
- **CIEDE2000** (de2000): Current gold standard, most perceptually accurate
- **CIE94** (de94): Good balance of accuracy and performance
- **CIE76** (de76): Simple Euclidean in LAB space
- **CMC**: Textile industry standard
- **Euclidean**: Simple RGB distance (not perceptually uniform)
- **HSL Euclidean**: Distance in HSL space with hue wraparound

### Palette Usage
```python
# Load and search palettes
from color_tools.palette import Palette, FilamentPalette, load_colors, load_filaments

palette = Palette(load_colors())
color, distance = palette.nearest_color((255, 128, 64))

filament_palette = FilamentPalette(load_filaments())
filament, distance = filament_palette.nearest_filament(
    (180, 100, 200),
    maker="Prusament",
    type_name="PLA"
)
```

## When Adding New Features

### Adding Color Spaces
1. Add conversion functions in `conversions.py`
2. Update `__init__.py` exports
3. Add CLI support in `cli.py` if needed
4. Test with known reference values

### Adding Distance Metrics
1. Implement in `distance.py` with proper docstring
2. Explain the use case (when to use this metric)
3. Export in `__init__.py`
4. Add CLI support with appropriate flag

### Adding Database Fields
1. Update JSON structure documentation
2. Modify ColorRecord or FilamentRecord dataclass
3. Update load_colors() or load_filaments() parsing
4. Update palette indices if field should be searchable
5. Test with existing and new JSON files

## Maintenance Notes

- README.md contains comprehensive usage examples - keep it updated
- The package works as library, CLI tool, or installed command
- Constants hash must be regenerated if constants are modified (but they shouldn't be!)
- JSON data file contains ~150 CSS colors and hundreds of filaments

## Development Setup

### Getting Started

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd color_tools
   ```

2. **Verify Python version**:
   ```bash
   python --version  # Should be 3.7+
   ```

3. **Test the installation**:
   ```bash
   # Run from parent directory of color_tools package
   cd ..
   python -m color_tools --help
   python -m color_tools color --name coral
   python -m color_tools --verify-constants
   ```

### Project Structure

```
color_tools/
├── __init__.py           # Public API exports
├── __main__.py           # Entry point for -m execution
├── cli.py                # Command-line interface (top of import tree)
├── conversions.py        # Color space conversions (RGB↔LAB↔HSL↔XYZ↔LCH)
├── distance.py           # Perceptual distance metrics (Delta E formulas)
├── gamut.py              # sRGB gamut checking and clamping
├── palette.py            # Color/filament databases and search
├── constants.py          # Immutable color science constants (NEVER modify)
├── config.py             # Thread-safe runtime configuration
├── validation.py         # Color name validation utilities
├── validation_test.py    # Tests for validation module
├── data/                 # JSON data files
│   └── color_tools.json  # CSS colors + filament database
├── .source_data/         # Source data and extraction scripts
└── .github/
    └── copilot-instructions.md  # This file
```

### Running Tests

```bash
# The project has minimal test infrastructure currently
# Validation tests (requires fuzzywuzzy):
pip install fuzzywuzzy python-Levenshtein
cd color_tools
python -m validation_test

# Manual verification tests:
python -m color_tools --verify-constants
python -m color_tools color --name coral
python -m color_tools filament --list-makers
python -m color_tools convert --from rgb --to lab --value 255 128 64
```

### Development Workflow

#### Making Changes to Color Conversions

1. Edit `conversions.py` with your changes
2. Test the conversion:
   ```bash
   python -m color_tools convert --from rgb --to lab --value 255 0 0
   ```
3. Verify constants haven't been accidentally modified:
   ```bash
   python -m color_tools --verify-constants
   ```
4. Update exports in `__init__.py` if adding new functions

#### Adding New Distance Metrics

1. Add function to `distance.py` with comprehensive docstring
2. Export in `__init__.py`
3. Add CLI support in `cli.py` (update `--metric` choices)
4. Test with known values:
   ```bash
   python -m color_tools color --nearest --value 255 0 0 --metric your_new_metric
   ```

#### Modifying JSON Data

1. Edit `data/color_tools.json` directly, or
2. Use extraction scripts in `.source_data/` for bulk changes
3. Validate structure is correct:
   ```bash
   python -c "import json; json.load(open('data/color_tools.json'))"
   ```
4. Test loading:
   ```bash
   python -m color_tools color --name coral
   python -m color_tools filament --list-makers
   ```

## Troubleshooting

### Import Errors

**Problem**: `ImportError: attempted relative import with no known parent package`

**Solution**: The package must be run from the parent directory:
```bash
# Wrong:
cd color_tools
python __main__.py

# Correct:
cd ..  # Parent directory containing color_tools/
python -m color_tools
```

### Constants Verification Fails

**Problem**: `ColorConstants integrity check FAILED!`

**Solution**: 
- If you didn't modify `constants.py`, this may be a pre-existing issue
- If you did modify constants (you shouldn't!), revert your changes
- Constants are from international standards and should never change

### Color Not Found

**Problem**: `Error: Color 'xyz' not found in database`

**Solution**:
- Check spelling and capitalization (use lowercase, e.g., "steelblue" not "SteelBlue")
- List available colors: see `data/color_tools.json`
- Use `--nearest` to find similar colors instead

### No Filaments Match Criteria

**Problem**: `No filaments found matching criteria`

**Solution**:
- Verify manufacturer names with `--list-makers`
- Verify types with `--list-types`
- Check finish options with `--list-finishes`
- Manufacturer and type names are case-sensitive

## Best Practices Summary

✅ **DO:**
- Use type hints on all functions
- Follow PEP 8 style conventions
- Write comprehensive docstrings with examples
- Use `from __future__ import annotations` for forward references
- Keep functions single-purpose and focused
- Use early returns to reduce nesting
- Test color conversions with known reference values
- Verify constants integrity after any changes

❌ **DON'T:**
- Modify `ColorConstants` class values
- Add external dependencies (Python stdlib only)
- Remove or modify working tests
- Use deep nesting (max 3-4 levels)
- Create circular imports (cli.py is at the top)
- Modify JSON structure without updating dataclasses

## Quick Reference

### Running the Tool

```bash
# From parent directory of color_tools package:
python -m color_tools [command] [options]

# Commands:
#   color      - Search CSS colors
#   filament   - Search 3D printing filaments  
#   convert    - Convert between color spaces
```

### Testing Changes

```bash
# Verify constants integrity
python -m color_tools --verify-constants

# Test color lookup
python -m color_tools color --name coral

# Test filament search
python -m color_tools filament --nearest --value 255 0 0

# Test color conversion
python -m color_tools convert --from rgb --to lab --value 128 64 200
```

### Import as Library

```python
from color_tools import (
    rgb_to_lab,           # Convert RGB to LAB
    delta_e_2000,         # Calculate perceptual distance
    Palette,              # Search CSS colors
    FilamentPalette,      # Search filaments
    load_colors,          # Load color database
    load_filaments,       # Load filament database
)

# Convert color
lab = rgb_to_lab((255, 128, 64))

# Find nearest color
palette = Palette(load_colors())
nearest, distance = palette.nearest_color((255, 128, 64))
print(f"Nearest: {nearest.name} (ΔE={distance:.2f})")
```

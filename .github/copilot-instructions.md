# GitHub Copilot Instructions for color_tools

## Project Overview

This is a color science library for Python 3.10+ that provides:
- Accurate color space conversions (RGB, LAB, LCH, HSL, XYZ)
- Perceptual color distance metrics (Delta E formulas)
- CSS color and 3D printing filament databases
- Gamut checking and color matching

## Code Style and Standards

### General Python Guidelines
- Use Python 3.10+ syntax (union types with `|`, modern type hints)
- Follow PEP 8 style conventions
- Use `from __future__ import annotations` for forward references
- Use type hints for all function signatures: `Path | str | None`, `tuple[int, int, int]`, etc.
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
- `--json DIR`: Path to directory containing all JSON data files (colors.json, filaments.json, maker_synonyms.json). Must be a directory. Default: package data directory
- `--verify-constants`: Verify integrity of color science constants before proceeding
- `--verify-data`: Verify integrity of core data files before proceeding
- `--verify-all`: Verify integrity of both constants and data files before proceeding
- `--version`: Show version number and exit

### Dual-Color Mode
- Some filaments have two colors (hex and hex2)
- Mode determines which color to use: "first" (default), "second", or "mix"
- Must be set BEFORE loading FilamentPalette

### Maker Synonyms
- Filament searches support maker synonyms (e.g., "Bambu" finds "Bambu Lab")
- Synonyms defined in `data/maker_synonyms.json`

### User Data Files (Optional Extensions)
Users can extend core databases with custom data:
- `user-colors.json` - Add custom colors (same format as colors.json)
- `user-filaments.json` - Add custom filaments (same format as filaments.json)
- `user-synonyms.json` - Add or extend maker synonyms (same format as maker_synonyms.json)
- User files are optional, automatically loaded/merged if present
- User files are NOT verified for integrity (user-managed)
- Users responsible for avoiding duplicate entries with core data

### Data Integrity
- Core data files protected by SHA-256 hashes stored in constants.py
- Use `--verify-data` to check core data integrity
- User data files are not verified
- Data verification is optional (opt-in via CLI flags)
- Automatically loaded by `FilamentPalette.load_default()`

## Data Files

### JSON Data Structure

Data is split into three separate JSON files in the `data/` directory:

#### `colors.json` - CSS Color Database
```json
[
  {
    "name": "coral",
    "hex": "#FF7F50",
    "rgb": [255, 127, 80],
    "hsl": [16.1, 100.0, 65.7],
    "lab": [67.3, 44.6, 49.7],
    "lch": [67.3, 66.9, 48.1]
  }
]
```

#### `filaments.json` - 3D Printing Filament Database
```json
[
  {
    "maker": "Bambu Lab",
    "type": "PLA",
    "finish": "Matte",
    "color": "Jet Black",
    "hex": "#000000",
    "td_value": 0.1
  }
]
```

#### `maker_synonyms.json` - Maker Name Synonyms
```json
{
  "Bambu Lab": ["Bambu", "BLL"],
  "Paramount 3D": ["Paramount", "Paramount3D"]
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
from color_tools.palette import Palette, FilamentPalette, load_colors, load_filaments, load_maker_synonyms

# CSS colors
palette = Palette.load_default()  # Loads from data/colors.json
color, distance = palette.nearest_color((255, 128, 64))

# Filaments with maker synonyms
filament_palette = FilamentPalette.load_default()  # Loads filaments + synonyms
filament, distance = filament_palette.nearest_filament(
    (180, 100, 200),
    maker="Bambu",  # Can use synonym instead of "Bambu Lab"
    type_name="PLA"
)

# Manual loading (advanced)
colors = load_colors()  # From data/colors.json
filaments = load_filaments()  # From data/filaments.json
synonyms = load_maker_synonyms()  # From data/maker_synonyms.json
palette = Palette(colors)
filament_palette = FilamentPalette(filaments, synonyms)
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
- JSON data is now split into separate files: `colors.json` and `filaments.json`

## Available Custom Agents

Use these specialized agents for specific tasks:
- **@test-specialist**: Expert in creating comprehensive unit tests with unittest framework. Use for creating/improving tests, test coverage analysis, or test design patterns.
  - Example: `@test-specialist add tests for the new distance metric`
  - Example: `@test-specialist review test coverage for palette.py`

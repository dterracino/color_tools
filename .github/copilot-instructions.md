# GitHub Copilot Instructions for color_tools

## Project Overview

This is a color science library for Python 3.10+ that provides:
- Accurate color space conversions (RGB, LAB, LCH, HSL, XYZ)
- Perceptual color distance metrics (Delta E formulas)
- CSS color and 3D printing filament databases
- Gamut checking and color matching

## Code Style and Standards

### Core Architectural Principles
- **Separation of Concerns**: Each module has a single, well-defined responsibility
  - `conversions.py`: Color space transformations ONLY
  - `distance.py`: Distance metrics ONLY
  - `palette.py`: Data loading and search ONLY
  - `constants.py`: Immutable constants ONLY
  - `config.py`: Runtime configuration ONLY
  - `cli.py`: User interface ONLY (orchestrates, doesn't implement logic)
- **DRY (Don't Repeat Yourself)**: Never duplicate logic
  - Shared functionality goes in the appropriate module
  - Reuse existing functions rather than reimplementing
  - If you find yourself copying code, create a shared function instead
  - Common patterns should be abstracted into utilities

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
conversions.py      # Color space conversion functions
distance.py         # Distance metrics (Delta E formulas)
gamut.py            # sRGB gamut operations
palette.py          # Color/filament databases and search
constants.py        # Immutable color science constants
config.py           # Thread-safe runtime configuration
matrices.py         # Transformation matrices (CVD, etc.)
color_deficiency.py # Color vision deficiency simulation/correction
naming.py           # Color name generation
validation.py       # Color validation utilities
cli.py              # Command-line interface (imports from everywhere)
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

## Hash Integrity System

The project uses SHA-256 hashes to protect critical data from accidental or malicious modification.
Three types of integrity verification are provided:

### 1. ColorConstants Hash (constants.py)
Protects color science constants (D65 white point, transformation matrices, Delta E coefficients, etc.)

**When to regenerate:**
- After adding new constants to `ColorConstants` class
- After modifying any UPPERCASE constant value
- After adding hash constants (like `MATRICES_EXPECTED_HASH`)

**How to regenerate:**
```bash
# Generate new hash
python -c "from color_tools.constants import ColorConstants; print(ColorConstants._compute_hash())"

# Update _EXPECTED_HASH in constants.py with the output
# Update the comment to note what changed
```

**Verification:**
```bash
python -m color_tools --verify-constants
```

### 2. Transformation Matrices Hash (matrices.py)
Protects CVD transformation matrices (protanopia, deuteranopia, tritanopia simulation/correction)

**When to regenerate:**
- After modifying any of the 6 matrix values
- When adding new transformation matrices to the verified set

**How to regenerate:**
```bash
# Generate new hash
python -c "from color_tools.constants import ColorConstants; print(ColorConstants._compute_matrices_hash())"

# Update MATRICES_EXPECTED_HASH in constants.py with the output
```

**⚠️ Important:** Adding utility functions to matrices.py does NOT require hash regeneration - only matrix constant values are hashed.

**When adding NEW matrices to matrices.py:**
1. Define the matrix constant in `matrices.py` (e.g., `NEW_MATRIX_NAME: Matrix3x3 = (...)`)
2. Add it to the import list in `ColorConstants._compute_matrices_hash()` in `constants.py`
3. Add it to the `matrices_dict` dictionary in that function
4. Regenerate `MATRICES_EXPECTED_HASH` using the command above
5. Update `_EXPECTED_HASH` for ColorConstants (you added a new constant to the file)
6. Run tests to verify everything works

**Verification:**
```bash
python -m color_tools --verify-matrices
```

### 3. Data File Hashes (JSON files)
Protects core data files: colors.json, filaments.json, maker_synonyms.json, and palette files

**When to regenerate:**
- After modifying any core data file
- After adding/updating palette files in data/palettes/
- After fixing typos or updating color values in databases

**How to regenerate:**
```bash
# For a single file
python -c "import hashlib; print(hashlib.sha256(open('color_tools/data/colors.json', 'rb').read()).hexdigest())"

# For all data files at once (recommended)
cd color_tools/data
python -c "
import hashlib
from pathlib import Path

files = {
    'colors.json': 'COLORS_JSON_HASH',
    'filaments.json': 'FILAMENTS_JSON_HASH', 
    'maker_synonyms.json': 'MAKER_SYNONYMS_JSON_HASH',
    'palettes/cga4.json': 'CGA4_PALETTE_HASH',
    'palettes/cga16.json': 'CGA16_PALETTE_HASH',
    'palettes/ega16.json': 'EGA16_PALETTE_HASH',
    'palettes/ega64.json': 'EGA64_PALETTE_HASH',
    'palettes/vga.json': 'VGA_PALETTE_HASH',
    'palettes/web.json': 'WEB_PALETTE_HASH',
}

for filepath, const_name in files.items():
    hash_val = hashlib.sha256(Path(filepath).read_bytes()).hexdigest()
    print(f'{const_name} = \"{hash_val}\"')
"

# Update the hash constants in constants.py with the output
```

**Verification:**
```bash
python -m color_tools --verify-data
```

### 4. Verify Everything
```bash
# Verify constants + matrices + data files
python -m color_tools --verify-all
```

### Hash Regeneration Checklist
When you modify protected data, follow this checklist:

1. **Modify the data** (constants, matrices, or JSON files)
2. **Regenerate hash(es)** using commands above
3. **Update hash constant(s)** in `constants.py`
4. **Update comment** explaining what changed
5. **Run verification** to confirm it passes
6. **Run all tests** to ensure nothing broke
7. **Document in CHANGELOG** what was modified and why

### Why Hash Verification?
- **Prevents accidents**: Catches unintentional modifications
- **Ensures correctness**: Color science constants are from international standards
- **Debugging aid**: Quickly verify data integrity when investigating issues
- **Quality assurance**: Data files match known-good versions

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
The CLI has five main commands:
1. **color**: Search CSS colors by name or find nearest color
2. **filament**: Search 3D printing filaments with filtering (maker, type, finish)
3. **convert**: Convert between color spaces and check gamut
4. **name**: Generate descriptive names for RGB colors
5. **cvd**: Color vision deficiency simulation and correction

### Global Arguments
- `--json DIR`: Path to directory containing all JSON data files (colors.json, filaments.json, maker_synonyms.json). Must be a directory. Default: package data directory
- `--verify-constants`: Verify integrity of color science constants before proceeding
- `--verify-data`: Verify integrity of core data files before proceeding
- `--verify-matrices`: Verify integrity of transformation matrices before proceeding
- `--verify-all`: Verify integrity of constants, data files, and matrices before proceeding
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
    "hex": "{the color's hex code}",
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
    "hex": "{the filament's hex code}",
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

### General Feature Addition Checklist

When adding any new feature to the project, follow this comprehensive checklist:

#### 1. **Implementation Phase**
- [ ] Implement the core functionality in the appropriate module
- [ ] Write comprehensive docstrings with examples
- [ ] Add type hints for all function signatures
- [ ] Follow code style guidelines (PEP 8, separation of concerns, DRY)
- [ ] Handle edge cases and validate inputs
- [ ] Use appropriate data structures (immutable where needed)

#### 2. **API Exposure**
- [ ] Export new functions/classes in `__init__.py` (if public API)
- [ ] Organize exports in appropriate sections (conversions, distance, palette, etc.)
- [ ] Add docstring examples to module `__doc__` if significant feature
- [ ] Update type hints and ensure Pyright passes without errors

#### 3. **CLI Integration** (if applicable)
- [ ] Add command-line arguments in `cli.py`
- [ ] Update help text and command descriptions
- [ ] Add examples to argparse help strings
- [ ] Test CLI with various input combinations

#### 4. **Testing**
- [ ] Create comprehensive unit tests in appropriate `test_*.py` file
- [ ] Test with known reference values where applicable
- [ ] Test edge cases and error conditions
- [ ] Run all existing tests to ensure no regressions: `python -m unittest discover tests`
- [ ] Verify test coverage for new code
- [ ] Consider using `@test-specialist` agent for test design

#### 5. **Documentation**
- [ ] Update `README.md` with usage examples if user-facing feature
- [ ] **VERIFY:** Check all relative links in README.md - PyPI needs full GitHub URLs
  - Bad: Relative links like `CHANGELOG.md` ❌
  - Good: Full URLs like `https://github.com/dterracino/color_tools/blob/main/CHANGELOG.md` ✅
- [ ] Update `CHANGELOG.md` in "Unreleased" section:
  - Use appropriate category: Added, Changed, Deprecated, Removed, Fixed, Security
  - Include clear description of what changed and why
  - Add code examples for significant features
- [ ] Update docstrings in relevant modules
- [ ] Update this copilot-instructions.md if feature affects development practices

#### 6. **Data Files** (if applicable)
- [ ] Update JSON structure documentation in copilot-instructions.md
- [ ] Modify dataclasses (ColorRecord, FilamentRecord) if needed
- [ ] Update parsing functions (load_colors, load_filaments, etc.)
- [ ] Update palette indices if field should be searchable
- [ ] **Regenerate data file hashes** in `constants.py` if core data modified
- [ ] Run `--verify-data` to confirm hash integrity

#### 7. **Versioning** ⚠️ CRITICAL - Update ALL three locations
- [ ] Decide if version bump needed (follow Semantic Versioning):
  - **Major** (X.0.0): Breaking changes, incompatible API changes
  - **Minor** (x.X.0): New features, backward-compatible additions
  - **Patch** (x.x.X): Bug fixes, backward-compatible fixes
- [ ] **REQUIRED:** Update version in `pyproject.toml`
- [ ] **REQUIRED:** Update version in `color_tools/__init__.py` (`__version__`)
- [ ] **REQUIRED:** Update version in `README.md` (line 5, Version badge)
- [ ] **VERIFY:** Search entire codebase for old version number to catch any missed locations

#### 8. **Package Metadata** (for significant changes)
- [ ] Update `pyproject.toml` keywords if feature expands scope
- [ ] Update classifiers if changing development status or adding topics
- [ ] Verify all URLs are still valid (homepage, repository, changelog)

#### 9. **Constants Integrity** (for color science changes)
- [ ] **NEVER modify ColorConstants unless absolutely necessary**
- [ ] If constants modified, regenerate hash verification
- [ ] Run `python color_tools.py --verify-constants` to confirm
- [ ] Document why constants were changed (should be rare!)

#### 10. **Final Verification**
- [ ] Run all unit tests: `python -m unittest discover tests`
- [ ] Test CLI commands manually with new feature
- [ ] Verify package can be imported: `python -c "import color_tools"`
- [ ] Check for any Pyright errors: Review pyrightconfig.json settings
- [ ] Test as library, CLI tool, and installed command if possible
- [ ] Review changes for backward compatibility

#### 11. **Pre-Release** (when ready to publish)
- [ ] Move unreleased changes in CHANGELOG.md to new version section
- [ ] Add release date to CHANGELOG.md
- [ ] Tag release in git with version number
- [ ] Build package: `python -m build`
- [ ] Test installation from built package
- [ ] Upload to PyPI (if appropriate): `twine upload dist/*`

---

### Feature-Specific Guides

#### Adding Color Spaces
1. Add conversion functions in `conversions.py`
2. Follow the conversion chain pattern (RGB ↔ XYZ ↔ LAB ↔ LCH)
3. Update `__init__.py` exports
4. Add CLI support in `cli.py` if needed
5. Test with known reference values from color science literature
6. Update README with examples
7. Follow general checklist above

#### Adding Distance Metrics
1. Implement in `distance.py` with proper docstring
2. Explain the use case (when to use this metric)
3. Include mathematical formula in docstring
4. Export in `__init__.py` in Distance Metrics section
5. Add CLI support with appropriate flag (`--metric new-metric`)
6. Test with published reference examples if available
7. Follow general checklist above

#### Adding Database Fields
1. Update JSON structure documentation in this file
2. Modify ColorRecord or FilamentRecord dataclass
3. Update load_colors() or load_filaments() parsing
4. Update palette indices if field should be searchable
5. **Regenerate data file hashes in constants.py**
6. Test with existing and new JSON files
7. Update user-facing documentation about data format
8. Follow general checklist above

#### Adding CLI Commands
1. Add command/subcommand in `cli.py`
2. Follow existing patterns (color, filament, convert)
3. Add comprehensive help text with examples
4. Support JSON output mode if applicable (`--json` flag)
5. Update README CLI section with new command examples
6. Test all argument combinations
7. Follow general checklist above

#### Adding Palette Types
1. Create new palette JSON file in `color_tools/data/palettes/`
2. Follow existing JSON format (array of color objects)
3. Add loading function or extend existing Palette class
4. Consider whether to add to integrity verification
5. Update README with new palette documentation
6. Add examples of using the new palette
7. Follow general checklist above

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

<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Multiple Result Support** - Both color and filament commands now support finding multiple nearest matches:
  - **`--count N` argument** - Returns top N closest matches (default: 1, max: 50) for both colors and filaments
  - **Enhanced output format** - Numbered list with distances and full details for easy comparison
  - **Backward compatibility** - Single result behavior preserved when `--count` is omitted or equals 1
  - **Consistent interface** - Same parameter works for both `color` and `filament` commands

  ```bash
  # Find top 5 CSS colors closest to purple
  python -m color_tools color --nearest --hex 8040C0 --count 5
  
  # Find top 3 filaments for custom blue, including alternatives
  python -m color_tools filament --nearest --hex 2121ff --count 3
  ```

- **Wildcard Filter Support** - Filament searches now support ignoring specific filters using `*` wildcard:
  - **`*` wildcard syntax** - Use `*` as special value to disable individual filters completely  
  - **Flexible filtering** - Ignore maker (`--maker "*"`), type (`--type "*"`), or finish (`--finish "*"`) constraints individually
  - **Mixed filtering** - Combine wildcard and specific filters (e.g., `--maker "*" --type PLA` searches all makers but only PLA)
  - **Complete bypass** - Use all wildcards to search entire filament database without restrictions
  - **Exploration friendly** - Perfect for discovering alternatives when preferred brand is unavailable

  ```bash
  # Search all makers for closest blue filament
  python -m color_tools filament --nearest --hex 2121ff --maker "*"
  
  # Find top 3 PLA filaments from any maker, any finish
  python -m color_tools filament --nearest --hex FF4500 --count 3 --maker "*" --finish "*"
  
  # Search all types but only from Bambu Lab
  python -m color_tools filament --nearest --hex 00FF00 --type "*" --maker "Bambu Lab"
  ```

### Changed

- **Simplified palette architecture** - Reverted to clean, simple JSON array format for better maintainability:
  - **Removed metadata complexity** - Eliminated unnecessary metadata fields that created technical debt
  - **Focused on fixed palettes** - Removed problematic dynamic palette systems (Genesis, TurboGrafx-16) that don't map to fixed color quantization
  - **Retained working palettes** - Kept all functional fixed palettes: CGA, EGA, VGA, Game Boy variants, Commodore 64, NES, SMS, VirtualBoy, Web Safe
  - **Maintained compatibility** - No breaking changes to palette loading or color matching APIs
  - **Performance optimized** - Simpler format improves loading speed and reduces memory usage

- **Enhanced error handling** - Improved validation and error messages for multiple result parameters
- **Updated CLI help** - Added examples and clarifications for new `--count` and wildcard features

## [3.5.0] - 2025-11-30

### Added

- **Universal Hex Color Support** - Complete hex color input support across all CLI commands for improved real-world usability:
  - **`--hex` argument** - Added to `color`, `filament`, `name`, `cvd`, and `convert` commands as convenient alternative to `--value`
  - **Enhanced format support** - Accepts 6-digit hex (`#FF5733`, `FF5733`) and 3-digit shortcuts (`#24c`, `24c`) using existing robust `hex_to_rgb()` function  
  - **Smart defaults** - When using `--hex`, automatically implies RGB color space (no need to specify `--from rgb` in convert command)
  - **Mutual exclusivity validation** - Prevents conflicting `--hex` and `--value` usage with clear error messages
  - **DRY implementation** - Leverages existing `conversions.hex_to_rgb()` function to avoid code duplication
  - **LAB/LCH validation** - Added bounds checking with helpful error messages for LAB/LCH input values
  - **Examples across help** - Updated CLI help and examples to showcase hex usage patterns

### Added

- **Unified Image Transformation System** - Complete image processing architecture leveraging all existing color_tools infrastructure:
  - **`transform_image(image_path, transform_func, preserve_alpha=True, output_path=None)`** - Universal function for applying color transformations to entire images
  - **`simulate_cvd_image(image_path, deficiency_type, output_path=None)`** - Simulate color vision deficiency (protanopia, deuteranopia, tritanopia) for entire images using scientifically-validated matrices
  - **`correct_cvd_image(image_path, deficiency_type, output_path=None)`** - Apply CVD correction to improve discriminability for colorblind viewers using Daltonization algorithm  
  - **`quantize_image_to_palette(image_path, palette_name, metric='de2000', dither=False, output_path=None)`** - Convert images to retro palettes (CGA, EGA, VGA, Game Boy, Web Safe) with all 6 distance metrics and optional Floyd-Steinberg dithering
  - **Infrastructure Integration** - All functions reuse existing color deficiency matrices, palette system, and distance metrics
  - **Comprehensive format support** - RGB, RGBA, grayscale, palette mode images with alpha preservation
  - **Performance optimized** - Numpy-based processing with memory efficiency for large images

  ```python
  from color_tools.image import simulate_cvd_image, quantize_image_to_palette
  
  # Test accessibility - see how deuteranopes view your chart
  sim_image = simulate_cvd_image("infographic.png", "deuteranopia") 
  sim_image.save("colorblind_view.png")
  
  # Create retro CGA-style artwork with dithering
  retro = quantize_image_to_palette("photo.jpg", "cga4", dither=True)
  retro.save("retro_cga.png")
  
  # Convert to Game Boy aesthetic using perceptually accurate CIEDE2000
  gameboy = quantize_image_to_palette("artwork.png", "gameboy", metric="de2000")
  gameboy.save("gameboy_style.png")
  ```

- **Complete documentation** for the transformation system in `image/README.md` with usage examples, supported palettes, distance metrics, and architecture details
- **Comprehensive CLI support** - Full command-line interface for all image transformations:
  - `python -m color_tools image --list-palettes` - List all available retro palettes including custom additions
  - `python -m color_tools image --cvd-simulate TYPE --file image.jpg` - Simulate colorblindness (protanopia, deuteranopia, tritanopia)
  - `python -m color_tools image --cvd-correct TYPE --file image.jpg` - Apply CVD correction for improved discriminability
  - `python -m color_tools image --quantize-palette NAME --file image.jpg` - Convert to retro palette with 6 distance metrics and optional dithering
  - Dynamic palette discovery automatically supports new JSON palettes in data/palettes/
  - Smart output naming with optional `--output` parameter for custom paths
  - Comprehensive error handling and operation validation

## [3.4.0] - 2025-11-28

### Added

- **General-purpose image analysis functions** in `image/basic.py` module:
  - `count_unique_colors(image_path)` - Count total unique RGB colors in an image using numpy
  - `get_color_histogram(image_path)` - Get histogram mapping RGB colors to pixel counts
  - `get_dominant_color(image_path)` - Get the most common color in an image
  - All functions work with any image format (PNG, JPEG, GIF, etc.)
  - Efficient numpy-based implementation for large images
  - Clean Python types returned (int tuples, not numpy types)

  ```python
  from color_tools.image import count_unique_colors, get_dominant_color
  
  # Count colors
  total = count_unique_colors("photo.jpg")
  print(f"Found {total} unique colors")
  
  # Get dominant color and match to CSS color
  from color_tools import Palette
  dominant = get_dominant_color("photo.jpg")
  palette = Palette.load_default()
  nearest, distance = palette.nearest_color(dominant)
  print(f"Dominant color matches CSS '{nearest.name}'")
  ```

- **Image quality analysis functions** in `image/basic.py` module:
  - `analyze_brightness(image_path)` - Analyze image brightness with dark/normal/bright assessment
  - `analyze_contrast(image_path)` - Analyze image contrast using standard deviation with low/normal assessment
  - `analyze_noise_level(image_path)` - Estimate noise level using scikit-image with clean/noisy assessment
  - `analyze_dynamic_range(image_path)` - Analyze dynamic range and provide gamma correction suggestions
  - All functions return structured dictionaries with raw values and human-readable assessments
  - Based on proven thresholds from image processing applications

  ```python
  from color_tools.image import analyze_brightness, analyze_contrast, analyze_noise_level
  
  # Analyze image quality
  brightness = analyze_brightness("photo.jpg")
  print(f"Brightness: {brightness['mean_brightness']:.1f} ({brightness['assessment']})")
  
  contrast = analyze_contrast("photo.jpg") 
  print(f"Contrast: {contrast['contrast_std']:.1f} ({contrast['assessment']})")
  
  noise = analyze_noise_level("photo.jpg")
  print(f"Noise: {noise['noise_sigma']:.2f} ({noise['assessment']})")
  ```

- **Image module architecture improvements**:
  - Separated general-purpose functions (`basic.py`) from HueForge-specific tools (`analysis.py`)
  - Clear separation of concerns following project architectural principles
  - Updated module docstrings to document both categories of functions
- **numpy dependency**: Added to `[image]` extra and `requirements-image.txt`
  - Required for efficient color counting and histogram operations
  - Minimum version: numpy>=1.24.0
- **scikit-image dependency**: Added to `[image]` extra and `requirements-image.txt`
  - Required for advanced noise analysis using `restoration.estimate_sigma()`
  - Minimum version: scikit-image>=0.20.0
  - Graceful fallback if not available

### Changed

- **Image extra now includes numpy and scikit-image**: `pip install color-match-tools[image]` now installs Pillow, numpy, and scikit-image
- **Image module documentation**: Updated `image/__init__.py` to show examples of both general and HueForge-specific functions

## [3.3.0] - 2025-11-10

### Added

- **Intelligent color naming system** (`naming.py` module)
  - `generate_color_name(rgb, palette_colors, near_threshold)` function generates descriptive color names
  - Three-tier naming strategy:
    1. Exact CSS color matches (e.g., "red", "blue", "papayawhip")
    2. Near CSS matches with Delta E < 5 (e.g., "near darkgray")
    3. Generated descriptive names based on HSL properties
  - **Lightness modifiers** (5 levels): very light, light, medium, dark, very dark
  - **Saturation modifiers** (6 levels):
    - pale (light colors, S<35%), muted (dark colors, S<35%)
    - dull (35% ≤ S < 50%)
    - (no modifier for medium saturation 50-70%)
    - bright (70% ≤ S < 85%)
    - deep (85% ≤ S < 95%)
    - vivid (S ≥ 95% - maximum saturation)
  - **Hue boundary transitions** ("-ish" variants):
    - Colors within ±8° of major hue boundaries get descriptive variants
    - Examples: "reddish orange", "orangeish yellow", "yellowish green", "blueish purple"
    - Only applied to colors with S ≥ 40% for meaningful descriptions
  - **Special case colors**:
    - Brown family: beige (light), tan (medium light), brown (darker)
    - Gold: desaturated yellow with moderate saturation (30-50%)
    - Pink: light reds with saturation
    - Olive: dark muted yellow-green
    - Navy: very dark blue
    - Maroon: very dark red
    - Teal: cyan-green range
    - Lime: bright yellow-green
  - Returns tuple of (name, match_type) where match_type is "exact", "near", or "generated"
  - Collision avoidance: Falls back to generic hue names if generated name conflicts with CSS
  - Exported as public API function for standalone use
  - **New CLI command**: `name --value R G B` generates descriptive names from RGB values
    - Examples: `name --value 255 128 64` → "light vivid orangeish red"
    - `--show-type` flag shows match type (exact/near/generated)
    - `--threshold` sets Delta E threshold for near matches (default: 5.0)

- **Improved palette color names**: All 6 palette files renamed with intelligent descriptive names
  - 110 colors improved across CGA, EGA, VGA, and Web palettes
  - Examples: "very light vivid greenish teal", "medium dull gold", "dark deep teal"
  - More variety and precision than generic numbering (e.g., "VGA 042" → "light vivid orange")

- **Comprehensive test suite for naming**: 53 new unit tests in `tests/test_naming.py`
  - Tests for lightness modifiers (5 levels)
  - Tests for saturation modifiers (6 levels including dull and deep)
  - Tests for "-ish" hue boundary transitions (8 boundaries)
  - Tests for special case colors (brown family, gold, olive, navy, maroon, teal, lime, pink)
  - Tests for complete name generation with collision avoidance
  - All 211 tests passing (158 existing + 53 new)

- **Unique filament IDs**: All filament records now include a unique `id` field
  - Generated from maker-type-finish-color using semantic slugification
  - IDs are stable, human-readable identifiers (e.g., "bambu-lab-pla-silk-plus-red")
  - Special character handling: `+` converted to `-plus` for URL-safe slugs
  - Zero ID collisions across entire database (584 unique IDs)
  - `id` field positioned as first field in FilamentRecord for clarity

- **Alternative filament names**: New optional `other_names` field for filament records
  - Supports regional variations (e.g., US vs EU names)
  - Tracks historical names when manufacturers rebrand products
  - Handles marketing variations and common misspellings
  - Field is optional - only populated when alternatives exist
  - Format: array of strings (e.g., `["Classic Red", "Premium PLA Red (EU)"]`)

- **Palette file integrity protection**: Added SHA-256 hash verification for all 6 palette files
  - CGA (4-color and 16-color), EGA (16-color and 64-color), VGA (256-color), Web (216-color)
  - `--verify-data` now checks all 9 core files (3 data + 6 palettes)
  - Updated CLI verification message to mention palettes

### Changed

- **Database restructuring and data corrections** (reduced from 588 to 584 filaments)
  - Removed 6 exact duplicate groups from database
  - **Polymaker data corrected**: 213 → 198 entries (-15)
    - Fixed incorrectly imported filament types (now includes specialized types like PC-ABS, PA6-CF20, LW-PLA, PC-PBT, CoPA)
    - Re-extracted from source PDF with improved parsing
    - Eliminated duplicate entries with wrong type labels
  - **Panchroma data corrected**: 143 → 154 entries (+11)
    - Fixed dual-color hex format from comma-separated to dash-separated (e.g., `#ABC, #DEF` → `#ABC-#DEF`)
    - Re-extracted from source PDF with improved parsing
    - Added missing filament colors
    - Fixed color name spacing issues in parentheses
  - **Bambu Lab expansion**: Added 38 new filament colors
    - 14 PETG HF colors (Yellow, Orange, Green, Red, Blue, Black, White, Cream, Lime Green, Forest Green, Lake Blue, Peanut Brown, Gray, Dark Gray)
    - 6 PETG-CF colors (Brick Red, Violet Purple, Indigo Blue, Malachite Green, Black, Titan Gray)
    - 10 PLA Translucent colors (Teal, Light Jade, Blue, Mellow Yellow, Purple, Cherry Pink, Orange, Ice Blue, Red, Lavender)
    - 8 PETG Translucent colors (Translucent Gray, Light Blue, Olive, Brown, Teal, Orange, Purple, Pink)

### Technical

- Updated `FilamentRecord` dataclass to include `id` as first field and optional `other_names` field
- Regenerated filaments.json integrity hash after data corrections and field additions
- Created PDF extraction tooling with improved parsing for Polymaker and Panchroma data sources
- Enhanced slug generation with collision detection and special character handling
- Added comprehensive database integrity tests (158 total tests, up from 142)
- **Enhanced data integrity protection**: Added SHA-256 hash verification for all 6 palette files (CGA4, CGA16, EGA16, EGA64, VGA, Web)
  - Palette files now protected against tampering alongside core data files
  - `--verify-all` flag now validates 9 core files total (3 data + 6 palettes)

## [3.2.1] - 2025-11-09

### Fixed

- Fixed README.md displaying correct version on PyPI package page
- Fixed changelog link to use full GitHub URL (relative links don't work on PyPI)

## [3.2.0] - 2025-11-09

### Added

- **3-character hex code support**: `hex_to_rgb()` now accepts shorthand hex format
  - Supports `#RGB` format (e.g., `#F00` → `#FF0000`, `#24c` → `#2244cc`)
  - Works with or without `#` prefix (e.g., `F00` or `#F00`)
  - Automatic expansion to 6-character format for processing
  - Fully integrated with validation, CLI, and all color operations

- **Hybrid fuzzy matching fallback** for validation module when fuzzywuzzy not installed
  - Pure Python implementation using Levenshtein distance algorithm
  - Three-strategy matching approach:
    1. Exact match after normalization (100% confidence)
    2. Substring matching (90-95% confidence based on coverage)
    3. Levenshtein distance calculation (variable confidence)
  - No external dependencies required for color name validation
  - Optional `fuzzywuzzy` package still recommended for best results

### Improved

- **Enhanced RGB parsing error handling**: Better validation and error messages
  - Added explicit type coercion for RGB values to catch non-numeric data
  - Improved error messages in `_parse_color_records()` helper function
  - Better handling of malformed color data in JSON files

## [3.1.0] - 2025-11-09

### Added

- **Custom palette support**: Load and use retro/classic color palettes
  - New `load_palette()` function to load named palettes
  - Six built-in palettes: `cga4`, `cga16`, `ega16`, `ega64`, `vga`, `web`
  - CGA 4-color: Classic gaming palette (Palette 1, high intensity)
  - CGA 16-color: Full RGBI palette
  - EGA 16-color: Standard/default EGA palette
  - EGA 64-color: Full 6-bit RGB palette
  - VGA 256-color: Classic Mode 13h palette
  - Web Safe: 216-color web-safe palette (6×6×6 RGB cube)
  - CLI support: `--palette <name>` flag for `color` command
  - All palettes work with existing distance metrics (de2000, de94, etc.)
  - Perfect for retro graphics, pixel art, and color quantization projects

- **Palette generation tooling**:
  - New `tooling/generate_palettes.py` script
  - Uses `color_tools` library to compute accurate LAB/LCH/HSL values
  - Pre-computes all color space conversions for fast loading
  - Palettes stored in `color_tools/data/palettes/` directory

- **Comprehensive unit tests for custom palettes**:
  - Tests for all 6 built-in palettes (cga4, cga16, ega16, ega64, vga, web)
  - Error handling tests for invalid palette names
  - Malformed JSON detection tests
  - Edge case coverage for empty names, case sensitivity, etc.

### Improved

- **Enhanced error handling in palette loading**:
  - `load_palette()` now provides helpful error messages listing available palettes
  - Better validation of palette JSON structure with specific error messages
  - Added `_parse_color_records()` helper function to avoid code duplication
  - Improved error messages include file names and problematic data indices
  - JSON decode errors are caught and re-raised with context

### Examples

```python
# Library usage
from color_tools import load_palette

cga = load_palette('cga4')
color, distance = cga.nearest_color((128, 64, 200), space='rgb')
print(f"{color.name}: {color.hex}")  # Light Magenta: #ff55ff
```

```bash
# CLI usage
python -m color_tools color --palette cga4 --nearest --value 128 64 200
python -m color_tools color --palette ega16 --nearest --value 255 0 0 --space rgb
```

## [3.0.0] - 2025-11-09

### Changed - BREAKING

- **Package restructuring**: Reorganized project into proper Python package structure
  - All Python modules moved to nested `color_tools/color_tools/` directory
  - Data files moved to `color_tools/color_tools/data/`
  - Import paths remain `from color_tools import ...` (no change for users)
  - CLI usage unchanged: `python -m color_tools` works the same way
- **Added pyproject.toml**: Modern Python packaging with full metadata
  - Package now installable with `pip install -e .` for development
  - Defines `color-tools` console script entry point
  - Declares Python 3.10+ requirement explicitly
  - No external dependencies (pure stdlib)

### Added

- Created `pyproject.toml` for modern Python packaging standards
- Package can now be installed and used as a proper Python library
- Console script `color-tools` available after installation

### Notes

This is a major version bump due to package restructuring. While the public API and CLI remain unchanged, the internal file structure has been reorganized. If you were importing modules directly from the file system (not recommended), you'll need to update those references.

## [2.1.1] - 2025-11-09

### Fixed

- Fixed type hint errors in `constants.py` by adding proper imports for type checking
- Added `from __future__ import annotations` for better type hint support
- Removed string quotes from `Path` type hints using `TYPE_CHECKING` conditional import

## [2.1.0] - 2025-11-09

### Added

- **Data file integrity verification** with SHA-256 hashes
  - Core data files (colors.json, filaments.json, maker_synonyms.json) are now protected with SHA-256 hashes
  - New `--verify-data` flag to verify data file integrity
  - New `--verify-all` flag to verify both constants and data files
  - `ColorConstants.verify_data_file()` and `verify_all_data_files()` methods
- **User data extension system** for custom colors, filaments, and synonyms
  - `data/user-colors.json` - Add custom CSS colors (optional)
  - `data/user-filaments.json` - Add custom filaments (optional)
  - `data/user-synonyms.json` - Add or extend maker synonyms (optional)
  - User files automatically loaded and merged with core data
  - User files are not verified (user-managed, full flexibility)
- Documentation for user data files and integrity verification

### Changed

- `load_colors()` now loads and merges user-colors.json if present
- `load_filaments()` now loads and merges user-filaments.json if present
- `load_maker_synonyms()` now loads and merges user-synonyms.json if present
- Updated ColorConstants hash to include new data file hash constants

## [2.0.1] - 2025-11-09

### Fixed

- `--json` argument now properly validates that the provided path is a directory
- Clear error messages when `--json` points to a file or non-existent path
- Enforces that `--json` must be a directory containing all three JSON data files

### Changed

- Updated help text to clarify `--json` requires a directory, not a file

## [2.0.0] - 2025-11-09

### Breaking Changes

- **Removed backwards compatibility** with old `color_tools.json` format
- Data files must now be split into three separate JSON files:
  - `colors.json` - CSS color database (array format)
  - `filaments.json` - 3D printing filament database (array format)
  - `maker_synonyms.json` - Maker name synonym mappings
- Old combined format `{"colors": [...], "filaments": [...]}` is no longer supported
- Migration tool available in `tooling/split_json.py` for converting old format

### Added

- **Maker synonym support** for flexible filament searches
  - Search for "Bambu" automatically finds "Bambu Lab" filaments
  - Search for "BLL" or "Paramount" uses synonym expansion
  - Synonyms defined in `data/maker_synonyms.json`
- `--version` flag to CLI to display version number
- `load_maker_synonyms()` function in public API
- `_expand_maker_names()` method in `FilamentPalette` class
- Support for `--json` argument to accept directory or specific file path

### Changed

- Imported 58 new Paramount 3D filaments from API data
- Reorganized project structure:
  - Created `docs/` folder for documentation files
  - Created `tests/` folder for test scripts
  - Created `tooling/` folder for utility scripts
- Updated all documentation for split file format
- `find_by_maker()` and `filter()` methods now support synonym expansion

### Fixed

- Eliminated duplicate hex parsing code by using `hex_to_rgb()` utility in `FilamentRecord.rgb`

## [1.0.0] - 2025-11-08

### Initial Release

- Initial stable release
- Complete CSS color database with 140+ named colors
- 3D printing filament database with 490+ filaments
- Multiple color space conversions (RGB, HSL, LAB, LCH, XYZ)
- Delta E distance metrics (CIE76, CIE94, CIEDE2000, CMC)
- Gamut checking for sRGB color space
- Thread-safe configuration for dual-color filament handling
- Command-line interface with three main commands:
  - `color` - Search and query CSS colors
  - `filament` - Search and query 3D printing filaments
  - `convert` - Convert between color spaces
- SHA-256 hash verification for color science constants
- Comprehensive documentation and examples

### Technical Details

- Python 3.10+ required (uses union type syntax `X | Y` and modern type hints)
- No external dependencies (standard library only)
- Portable package structure using relative imports
- Immutable dataclasses for color and filament records

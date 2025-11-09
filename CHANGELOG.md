# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

- Python 3.7+ compatible
- No external dependencies (standard library only)
- Portable package structure using relative imports
- Immutable dataclasses for color and filament records

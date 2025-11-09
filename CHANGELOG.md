# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

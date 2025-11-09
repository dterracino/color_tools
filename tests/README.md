# Color Tools Test Suite

This directory contains comprehensive unit tests for the color_tools library.

## Test Files

### Unit Tests (unittest framework)

The following files contain proper unit tests that can be run with Python's unittest module:

- **test_conversions.py** (23 tests) - Tests for all color space conversions (RGB, LAB, LCH, HSL, XYZ)
- **test_distance.py** (26 tests) - Tests for Delta E formulas and distance metrics (CIE76, CIE94, CIEDE2000, CMC)
- **test_palette.py** (26 tests) - Tests for Palette and FilamentPalette classes
- **test_gamut.py** (9 tests) - Tests for sRGB gamut checking and clamping
- **test_config.py** (8 tests) - Tests for thread-safe configuration
- **test_constants.py** (13 tests) - Tests for color science constants

**Total: 105 unit tests**

### Running the Tests

Run all unit tests:
```bash
python3 -m unittest discover -s color_tools/tests -p "test_*.py"
```

Run a specific test file:
```bash
python3 -m unittest color_tools.tests.test_conversions
```

Run tests with verbose output:
```bash
python3 -m unittest discover -s color_tools/tests -p "test_*.py" -v
```

### Example/Demo Scripts

The following files are demonstration scripts, not unit tests:

- **test_api.py** - Demonstrates public API usage with synonym support
- **test_synonyms.py** - Demonstrates maker synonym functionality
- **validation_test.py** - Demonstrates color validation with fuzzy matching (requires fuzzywuzzy)

Run these as standalone scripts:
```bash
python3 -m color_tools.tests.test_api
python3 -m color_tools.tests.test_synonyms
```

## Test Coverage

The unit tests cover:

✅ **Color Space Conversions**
- Hex ↔ RGB
- RGB ↔ LAB
- RGB ↔ LCH  
- LAB ↔ LCH
- RGB ↔ XYZ
- XYZ ↔ LAB
- RGB ↔ HSL
- RGB → Windows HSL

✅ **Distance Metrics**
- Delta E 76 (CIE76)
- Delta E 94 (CIE94)
- Delta E 2000 (CIEDE2000)
- Delta E CMC (textile industry)
- Euclidean RGB distance
- HSL distance with hue wraparound

✅ **Palette Operations**
- Loading CSS colors
- Loading 3D printing filaments
- Exact color/filament lookup
- Nearest color/filament search
- Maker synonym expansion
- Filtering by multiple criteria

✅ **sRGB Gamut**
- Gamut checking (LAB → is in sRGB gamut?)
- Gamut clamping (LAB → nearest in-gamut LAB)
- Find nearest in-gamut color

✅ **Configuration**
- Thread-safe dual-color mode setting
- Thread-local configuration isolation

✅ **Color Science Constants**
- D65 white point values
- sRGB ↔ XYZ transformation matrices
- Gamma correction constants
- LAB/LCH formula constants
- Delta E formula constants

## Notes

- All tests use Python's built-in `unittest` framework (no external dependencies)
- Tests are designed to be comprehensive but fast
- Some tests verify mathematical relationships (e.g., roundtrip conversions)
- Edge cases and error conditions are tested where appropriate
- Tests follow the naming convention: test_<module>.py for module testing

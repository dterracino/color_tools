# Tooling Scripts

This directory contains various development and data conversion scripts used during the creation and maintenance of this project.

**⚠️ Warning:** These scripts are for internal development purposes only. They should **not** be run or used by end users or contributors.

These tools were used for tasks such as:

- Converting data formats
- Generating or transforming color data files
- One-time data migration scripts
- Development utilities

The scripts may have hardcoded paths, expect specific input formats, or modify data files in ways that could break the package if run incorrectly.

## Current Scripts

### `generate_palettes.py` ✨

**Purpose:** Generate retro palette JSON files (CGA, EGA, VGA, Web Safe) for use with custom palettes.

Generates palette files in `color_tools/data/palettes/` with full color space conversions:

- `cga4.json` - CGA 4-color (Palette 1, high intensity)
- `cga16.json` - CGA 16-color (full RGBI)
- `ega16.json` - EGA 16-color (standard/default)
- `ega64.json` - EGA 64-color (full 6-bit RGB)
- `vga.json` - VGA 256-color (Mode 13h)
- `web.json` - Web Safe 216-color (6x6x6 RGB cube)

Uses the `color_tools` library itself to compute accurate LAB/LCH/HSL values from RGB definitions.

**Usage:**

```bash
python tooling/generate_palettes.py
```

**Safe to re-run:** Yes - regenerates all palette files from source definitions.

### `demo_api.py`

**Purpose:** Demonstration script showing how to use the public API with maker synonyms.

Shows three different ways to work with the FilamentPalette and maker synonyms:

1. Using `FilamentPalette.load_default()` (most convenient)
2. Manual construction with `load_maker_synonyms()`
3. Without synonyms for comparison

**Usage:**

```bash
python tooling/demo_api.py
```

**Safe to re-run:** Yes - read-only demonstration.

### `validation_test.py`

**Purpose:** Manual test/demo script for the color validation module.

Tests the `validation.validate_color()` function with various test cases including:

- Exact color matches
- Fuzzy name matching
- Incorrect color matches
- Invalid input handling

**Usage:**

```bash
python tooling/validation_test.py
```

**Safe to re-run:** Yes - read-only demonstration.

## Historical Scripts

The following scripts were used for one-time data conversions and are kept for reference:

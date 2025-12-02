# Development Tools Reference

This document catalogs all scripts in the `tools/` and `tooling/` directories, providing descriptions and recommendations for each.

---

## Status Legend

| Status | Description |
|--------|-------------|
| ✅ **KEEP** | Actively useful for ongoing development/maintenance |
| 🔄 **KEEP (Occasional)** | Useful but only needed occasionally |
| ⚠️ **REVIEW** | May still be useful but needs evaluation |
| 🗑️ **RETIRE** | One-time use completed, can be safely removed |
| 📚 **REFERENCE** | Keep for historical/educational purposes only |

---

## `tools/` Directory

This directory contains palette-related utilities.

### convert_palettes.py
**Status:** 🔄 **KEEP (Occasional)**

**Purpose:** Converts existing palette files to a new metadata format with compact formatting. Adds metadata like `name`, `description`, `native_resolution`, `display_aspect_ratio`, `pixel_aspect_ratio`, `creator`, `year`, `bit_depth`, etc.

**Usage:** Run when adding new palettes or converting palette format.
```bash
python tools/convert_palettes.py
python tools/convert_palettes.py path/to/palette.json
```

**Notes:** Has comprehensive metadata definitions for CGA, EGA, VGA, Web, NES, GameBoy variants, Commodore 64, SMS, TurboGrafx-16, and Virtual Boy.

---

### generate_genesis_palette.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Generates the Sega Genesis/Mega Drive 512-color 9-bit RGB palette JSON file.

**Notes:** One-time generation script. The `genesis.json` palette file should already exist in `color_tools/data/palettes/`. Only needed if the palette file needs to be regenerated from scratch.

---

### regenerate_palette_hashes.py
**Status:** 🗑️ **RETIRE** (Superseded)

**Purpose:** Generates SHA-256 hashes for palette files to update `constants.py`.

**Notes:** Functionality duplicated and improved in `tooling/update_hashes.py`. The newer script handles all hash types (data files, palettes, matrices, constants) and supports `--autoupdate` mode.

---

### revert_palettes.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Reverts palette files from metadata format back to simple array format.

**Notes:** One-time utility created during format transition. No longer needed unless the metadata format decision is reversed.

---

### test_basic_palettes.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Test script to verify palette loading functionality. Tests loading Genesis palette and creating Palette objects.

**Notes:** Ad-hoc test script, not part of the formal test suite. Similar tests should exist in `tests/` directory. If not, consider moving relevant tests there.

---

### test_palettes.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Test script to verify palette loading and image quantization functionality.

**Notes:** Nearly identical to `test_basic_palettes.py` with additional image import. Ad-hoc test script. Functionality should be in formal test suite.

---

## `tooling/` Directory

This directory contains development and data conversion utilities.

### README.md
**Status:** ✅ **KEEP**

**Purpose:** Documentation for the tooling directory. Explains purpose and usage of key scripts.

**Notes:** Keep updated as scripts are added/removed.

---

### add_lch.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Adds LCH values to all colors in `color_tools.json` (old data format).

**Notes:** One-time data migration script. References old `data/color_tools.json` file which no longer exists (data split into `colors.json` and `filaments.json`).

---

### add_slugs_to_database.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Adds slug IDs to all filaments in `filaments.json`.

**Notes:** One-time script. Slugs have already been added and renamed to `id` field. See `rename_slug_to_id.py`.

---

### bambu_new_filaments.json
**Status:** 🗑️ **RETIRE**

**Purpose:** Output/temporary data file from `import_bambu_new.py`.

**Notes:** Intermediate data file, not a script. Should be deleted after merge completed.

---

### check_duplicates.py
**Status:** 🔄 **KEEP (Occasional)**

**Purpose:** Checks for duplicate entries in `filaments.json`. Reports exact duplicates and near-duplicates (same maker/type/color with different finish).

**Usage:** Run periodically to validate data integrity:
```bash
python tooling/check_duplicates.py
```

**Notes:** Useful for data quality assurance after adding new filaments.

---

### check_extracted_duplicates.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Checks for duplicates in extracted Polymaker and Panchroma data files.

**Notes:** One-time validation script for a specific data import operation. Depends on `polymaker_extracted.json` and `panchroma_extracted.json`.

---

### check_plus_sign.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Finds filaments with `+` character in type or finish fields.

**Notes:** One-time diagnostic script to identify data for slug generation fixes.

---

### compact_arrays.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Compacts JSON arrays to single lines (older version).

**Notes:** References old `data/color_tools.json` file. Superseded by `compact_color_arrays.py`.

---

### compact_color_arrays.py
**Status:** 🔄 **KEEP (Occasional)**

**Purpose:** Reformats JSON files so color value arrays (rgb, hsl, lab, lch) display on single lines instead of multi-line format.

**Usage:** Run after data file modifications:
```bash
python tooling/compact_color_arrays.py
```

**Notes:** Interactive script with confirmation prompt. Remember to regenerate hashes after running.

---

### compare_panchroma.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Compares current Panchroma filaments vs newly extracted from PDF.

**Notes:** One-time comparison script for a specific data import. Depends on `panchroma_extracted.json`.

---

### compare_polymaker.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Compares current Polymaker data vs newly extracted data from PDF.

**Notes:** One-time comparison script for a specific data import. Depends on `polymaker_extracted.json`.

---

### convert_to_tuples.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Converts `color_tools.json` to use tuple format instead of named objects for RGB, HSL, LAB values.

**Notes:** One-time data format migration. References old `data/color_tools.json` file.

---

### demo_api.py
**Status:** ✅ **KEEP**

**Purpose:** Demonstration script showing how to use the public API with maker synonyms. Shows three different ways to work with FilamentPalette.

**Usage:** Run to verify API works correctly:
```bash
python tooling/demo_api.py
```

**Notes:** Useful for API documentation and testing. Referenced in `tooling/README.md`.

---

### extract_panchroma.py
**Status:** 📚 **REFERENCE**

**Purpose:** Extracts Panchroma filament data from Polymaker PDF using pdfplumber.

**Notes:** One-time extraction script. Keep for reference if data needs to be re-extracted from source PDF. Requires `pdfplumber` dependency.

---

### extract_polymaker.py
**Status:** 📚 **REFERENCE**

**Purpose:** Extracts Polymaker filament data from PDF.

**Notes:** One-time extraction script. Keep for reference if data needs to be re-extracted. Requires `pdfplumber` dependency.

---

### filament_slugs_preview.json
**Status:** 🗑️ **RETIRE**

**Purpose:** Output data file from `generate_slugs.py`.

**Notes:** Intermediate data file, not a script.

---

### filament_slugs_preview.txt
**Status:** 🗑️ **RETIRE**

**Purpose:** Human-readable output from `generate_slugs.py`.

**Notes:** Intermediate data file, not a script.

---

### filaments_with_slugs.json
**Status:** 🗑️ **RETIRE**

**Purpose:** Output data file from `add_slugs_to_database.py`.

**Notes:** Intermediate data file, not a script.

---

### generate_palette_hashes.py
**Status:** 🗑️ **RETIRE** (Superseded)

**Purpose:** Generates SHA-256 hashes for palette JSON files.

**Notes:** Only covers 6 original palettes. Superseded by `update_hashes.py` which handles all palettes and data files.

---

### generate_palettes.py
**Status:** ✅ **KEEP**

**Purpose:** Generates retro palette JSON files (CGA, EGA, VGA, Web Safe) using the color_tools library for accurate color space conversions.

**Usage:** Regenerate all standard palettes:
```bash
python tooling/generate_palettes.py
```

**Notes:** Safe to re-run. Uses color_tools library itself. Referenced in `tooling/README.md` and CHANGELOG.

---

### generate_slugs.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Generates slug IDs for all filaments and outputs for review.

**Notes:** One-time script. Slug generation has been completed.

---

### import_bambu_new.py
**Status:** 📚 **REFERENCE**

**Purpose:** Parses new Bambu Lab filament data files from `.source_data` folder.

**Notes:** One-time import script. Keep for reference if new Bambu Lab data needs to be imported.

---

### merge_bambu_filaments.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Merges new Bambu Lab filament data into `filaments.json`.

**Notes:** One-time merge script. Operation completed.

---

### panchroma_extracted.json
**Status:** 🗑️ **RETIRE**

**Purpose:** Output data file from `extract_panchroma.py`.

**Notes:** Intermediate data file, not a script.

---

### polymaker_extracted.json
**Status:** 🗑️ **RETIRE**

**Purpose:** Output data file from `extract_polymaker.py`.

**Notes:** Intermediate data file, not a script.

---

### polymaker_update_preview.txt
**Status:** 🗑️ **RETIRE**

**Purpose:** Preview output from `compare_polymaker.py`.

**Notes:** Intermediate data file, not a script.

---

### rename_palette_colors.py
**Status:** 🔄 **KEEP (Occasional)**

**Purpose:** Renames palette colors using intelligent color naming from the `color_tools.naming` module.

**Usage:** Run after adding new palettes:
```bash
python tooling/rename_palette_colors.py
```

**Notes:** Updates all palette files with descriptive color names based on RGB values.

---

### rename_slug_to_id.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Renames `slug` field to `id` and moves it to first position in `filaments.json`.

**Notes:** One-time field rename. Operation completed.

---

### replace_polymaker_panchroma.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Replaces Polymaker and Panchroma data in `filaments.json` with corrected extracts.

**Notes:** One-time data replacement operation. Completed.

---

### show_sample_slugs.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Displays sample slugs from extracted data.

**Notes:** One-time debugging script. Depends on extracted JSON files.

---

### show_slug_examples.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Shows collision examples from slugged database.

**Notes:** One-time debugging script. Depends on `filaments_with_slugs.json`.

---

### split_json.py
**Status:** 📚 **REFERENCE**

**Purpose:** Splits `color_tools.json` into `colors.json` and `filaments.json`.

**Notes:** One-time migration script. Referenced in CHANGELOG. Keep for historical reference.

---

### sync_td_values.py
**Status:** 📚 **REFERENCE**

**Purpose:** Syncs TD (transmissivity) values from HueForge personal library to color_tools database using fuzzy matching.

**Notes:** Specialized utility for syncing data from HueForge. Requires `fuzzywuzzy` dependency and access to HueForge personal library file. Keep for reference if TD values need updating.

---

### test_plus_slugs.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Tests that `+` character is converted to `-plus` in slugs.

**Notes:** One-time verification script for slug generation.

---

### tg16_palette_generator.html
**Status:** 📚 **REFERENCE**

**Purpose:** HTML/JavaScript version of TurboGrafx-16 palette generator with visual preview.

**Notes:** Standalone HTML tool for generating TG-16 palette. Keep for reference or potential web documentation.

---

### tg16_palette_generator.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Python script to generate TurboGrafx-16 512-color palette JSON.

**Notes:** One-time generation script. Palette should already exist. Note: outputs to current directory, not to palettes folder.

---

### update_hashes.py
**Status:** ✅ **KEEP**

**Purpose:** Generates and optionally auto-updates all SHA-256 hashes for the data integrity system (data files, palettes, matrices, constants).

**Usage:**
```bash
# View all hashes
python tooling/update_hashes.py

# Auto-update constants.py
python tooling/update_hashes.py --autoupdate

# Generate only ColorConstants hash (final step)
python tooling/update_hashes.py --constants-only
```

**Notes:** Primary hash management tool. Referenced in README and documentation.

---

### verify_database_update.py
**Status:** 🗑️ **RETIRE**

**Purpose:** Verifies corrected Polymaker data is in the database.

**Notes:** One-time verification script for a specific data import operation.

---

## Summary

### Scripts to Keep (✅ KEEP)
- `tooling/README.md` - Documentation
- `tooling/demo_api.py` - API demonstration
- `tooling/generate_palettes.py` - Palette generation
- `tooling/update_hashes.py` - Hash management (primary tool)

### Scripts to Keep for Occasional Use (🔄 KEEP Occasional)
- `tools/convert_palettes.py` - Palette format conversion
- `tooling/check_duplicates.py` - Data quality assurance
- `tooling/compact_color_arrays.py` - JSON formatting
- `tooling/rename_palette_colors.py` - Color naming

### Scripts to Keep as Reference (📚 REFERENCE)
- `tooling/extract_panchroma.py` - PDF extraction reference
- `tooling/extract_polymaker.py` - PDF extraction reference
- `tooling/import_bambu_new.py` - Bambu data import reference
- `tooling/split_json.py` - Historical migration reference
- `tooling/sync_td_values.py` - HueForge sync reference
- `tooling/tg16_palette_generator.html` - Web tool reference

### Scripts to Retire (🗑️ RETIRE)

**tools/ directory:**
- `generate_genesis_palette.py`
- `regenerate_palette_hashes.py`
- `revert_palettes.py`
- `test_basic_palettes.py`
- `test_palettes.py`

**tooling/ directory (scripts):**
- `add_lch.py`
- `add_slugs_to_database.py`
- `check_extracted_duplicates.py`
- `check_plus_sign.py`
- `compact_arrays.py`
- `compare_panchroma.py`
- `compare_polymaker.py`
- `convert_to_tuples.py`
- `generate_palette_hashes.py`
- `generate_slugs.py`
- `merge_bambu_filaments.py`
- `rename_slug_to_id.py`
- `replace_polymaker_panchroma.py`
- `show_sample_slugs.py`
- `show_slug_examples.py`
- `test_plus_slugs.py`
- `tg16_palette_generator.py`
- `verify_database_update.py`

**tooling/ directory (data files):**
- `bambu_new_filaments.json`
- `filament_slugs_preview.json`
- `filament_slugs_preview.txt`
- `filaments_with_slugs.json`
- `panchroma_extracted.json`
- `polymaker_extracted.json`
- `polymaker_update_preview.txt`

---

## Recommendations

1. **Consolidate tools/** - Consider moving the useful scripts from `tools/` to `tooling/` and retiring the rest. Having two similar directories is confusing.

2. **Clean up data files** - Remove all intermediate JSON/TXT data files from `tooling/` that were outputs of one-time operations.

3. **Archive retired scripts** - Consider moving retired scripts to a `tooling/archive/` subdirectory rather than deleting them, in case they're needed for reference.

4. **Update tooling/README.md** - The README references a `validation_test.py` script that doesn't exist. Update to reflect current state.

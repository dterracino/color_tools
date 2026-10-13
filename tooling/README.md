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

### `import_bambu_filaments.py`

**Purpose:** Reconcile the approved Bambu Lab PDF color tables with the bundled
filament database and add missing product identities.

The script is read-only by default. It reports additions, unchanged records,
and conflicts without changing the database. Existing records with a different
hex value are reported as conflicts and are never overwritten automatically.
Writing requires the explicit `--apply` option, and an apply is refused while
any conflict remains.

Install the tooling dependencies, then preview or apply:

```bash
python -m pip install -r tooling/requirements.txt
python tooling/import_bambu_filaments.py
python tooling/import_bambu_filaments.py --apply
```

**Safe to re-run:** Yes. A successful apply is atomic and a subsequent dry run
reports every source row as unchanged.

### `preview_iemai_filaments.py`

**Purpose:** Reconcile the paired IEMAI CSV and grouped-text sources and print
every proposed normalized record for review. The script never writes files or
changes the filament database.

Source `CF` and `GF` qualifiers become compound filament types such as `ASA-CF`
and `PA12-GF`; all other qualifiers remain finishes. Ordered multi-color hex
components are preserved. Each line includes the normalized identity/color,
confidence label, and source URL. The unsupported alpha-bearing `PC Transparent`
row is printed as an explicit exclusion and is not an import candidate.

```bash
python tooling/preview_iemai_filaments.py
```

**Safe to re-run:** Yes - console output only.

### `import_iemai_filaments.py`

**Purpose:** Import the 187 approved IEMAI candidates after reconciling the CSV
and grouped-text sources. The importer preserves `PLA+/Pro`, promotes only `CF`
and `GF` to compound material types, supports ordered multi-color values, and
explicitly excludes `IEMAI PC Transparent`.

The default mode is a read-only dry run. Writing requires `--apply`:

```bash
python tooling/import_iemai_filaments.py
python tooling/import_iemai_filaments.py --apply
```

**Safe to re-run:** Yes. A successful apply is atomic and a subsequent run
reports all 187 candidates as unchanged.

### `extract_overture_pdf.py`

**Purpose:** Reconstruct the Overture PDF's two-column product tables from
positioned text and write an editable, pipe-delimited review file. The script
does not modify the filament database.

It writes all explicit single- and multi-color hex rows in visual page order,
records no-hex gradient entries as non-importable audit comments, corrects four
verified text-layer column fusions, and flags malformed source hex values for
manual correction.

```bash
python tooling/extract_overture_pdf.py
python tooling/extract_overture_pdf.py --output path/to/review.txt
```

The default output is `.source_data/overture_filaments_review.txt`. Hand-edit
and approve that file before building or running the database importer.

**Safe to re-run:** Yes, but rerunning overwrites the review file. Use a separate
output path after manual edits if the original extracted version is still needed.

### `prepare_overture_import_review.py`

**Purpose:** Convert the hand-reviewed Overture extraction into a separate
database-shaped review file with `maker`, `type`, `finish`, `color`, canonical
`hex`, and `td_value` columns. It does not modify the reviewed extraction or the
filament database.

`Matte PLA`, `Silk PLA`, and `Rock PLA` map to `PLA` with an appearance finish.
Functional formulations and product grades such as `Super PLA+`, `Easy PLA`,
`Air PLA`, `PLA Professional`, `High Speed TPU`, `Easy Nylon`, and
`PC Professional` remain distinct types.

```bash
python tooling/prepare_overture_import_review.py
```

The default output is
`.source_data/overture_filaments_import_review.txt`. Compound colors are written
in the database's canonical ordered hex representation. The script rejects
unresolved statuses, unknown products, invalid hex, unexpected row counts, and
type/finish mappings that create duplicate identities.

**Safe to re-run:** Yes. It deterministically recreates the derived import-review
file without changing the hand-reviewed extraction.

### `import_overture_filaments.py`

**Purpose:** Reconcile and import the approved database-shaped Overture review.
The importer adds missing identities, applies reviewed hex corrections while
preserving existing IDs and TD values, and retains existing Overture records
that are absent from the PDF.

The default mode is a read-only dry run. Writing requires `--apply`:

```bash
python tooling/import_overture_filaments.py
python tooling/import_overture_filaments.py --apply
```

**Safe to re-run:** Yes. The approved import added 293 records, corrected seven
hex values, retained 11 unmatched existing records, and the immediate rerun
reported all 300 reviewed rows unchanged.

### `generate_palettes.py` ✨

**Purpose:** Generate retro palette JSON files (CGA, EGA, VGA, Web Safe) for use with custom palettes.

Generates palette files in `color_tools/data/palettes/` with full color space conversions:

- `cga4.json` - CGA 4-color (Palette 1, high intensity)
- `cga16.json` - CGA 16-color (full RGBI)
- `crayola.json` - Crayola 120-color crayon palette (see `generate_crayola_palette.py`)
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

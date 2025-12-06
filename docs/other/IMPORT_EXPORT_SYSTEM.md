# Import/Export System Design

## Overview

Design for a flexible import/export system for filaments and colors, driven by JSON format definitions. Enables integration with external tools like AutoForge, HueForge, Cura, PrusaSlicer, etc.

**Status:** Design phase - no implementation yet

---

## Use Cases

### Primary Use Cases

1. **Export to AutoForge** - Generate CSV for AutoForge filament library import
2. **Import from HueForge** - Bulk import filaments from HueForge JSON exports
3. **Export to other slicers** - Support Cura, PrusaSlicer, OrcaSlicer formats
4. **User filament library management** - Easy bulk import/export of custom filaments
5. **Backup/restore** - Export entire filament database, import to new system

### Secondary Use Cases

- Color palette exports for design tools
- Integration with inventory management systems
- Sharing filament databases between users
- Migration from other color management tools

---

## Architecture

### File Structure

```text
color_tools/data/
  ├── import-formats.json          # Built-in import format definitions
  ├── export-formats.json          # Built-in export format definitions
  ├── user-import-formats.json     # User custom import formats (optional)
  ├── user-export-formats.json     # User custom export formats (optional)
  ├── filaments.json               # Core filament database
  ├── user-filaments.json          # User custom filaments (optional)
  ├── colors.json                  # Core color database
  └── user-colors.json             # User custom colors (optional)
```

**Note:** Export operations must include both core data and user data files. When exporting filaments, the system merges `filaments.json` and `user-filaments.json` (if present) before applying filters and format definitions. Similarly for colors.

### Module Structure

```text
color_tools/
  ├── import_export.py             # Core import/export logic
  │   ├── load_import_formats()
  │   ├── load_export_formats()
  │   ├── import_filaments()
  │   ├── export_filaments()
  │   └── list_formats()
  └── cli.py                        # CLI integration
```

---

## Export System

### Export Format Definition (export-formats.json)

```json
{
  "autoforge": {
    "description": "AutoForge filament library CSV format",
    "file_extension": "csv",
    "applies_to": "filaments",
    "columns": [
      {
        "header": "Brand",
        "fields": ["maker", "finish"],
        "separator": " "
      },
      {
        "header": "Name",
        "fields": ["color"]
      },
      {
        "header": "TD",
        "fields": ["td_value"]
      },
      {
        "header": "Color",
        "fields": ["hex"]
      },
      {
        "header": "Owned",
        "literal": "TRUE"
      }
    ]
  },
  "csv_all": {
    "description": "Export all filament fields as CSV",
    "file_extension": "csv",
    "applies_to": "filaments",
    "columns": "all"
  }
}
```

### CLI Usage

```bash
# Export with auto-generated filename (includes user-filaments.json if present)
python -m color_tools filament --maker "Bambu Lab" --type "PLA" --finish "Basic Matte" \
    --export autoforge
# Output: filaments_autoforge_20250305_143022.csv
# Note: Exports from both filaments.json AND user-filaments.json

# Export with specific filename
python -m color_tools filament --maker "Bambu Lab" --export autoforge \
    --output bambu_filaments.csv

# Export only core filaments (exclude user data)
python -m color_tools filament --export autoforge --core-only
# Note: --core-only flag skips user-filaments.json

# List available export formats
python -m color_tools filament --list-export-formats
# Output:
#   autoforge       - AutoForge filament library CSV format
#   csv_all         - Export all filament fields as CSV
#   hueforge        - HueForge filament JSON format
#   cura            - Cura material library XML format

# Export all filaments (no filters, includes user data)
python -m color_tools filament --export csv_all
```

### Example AutoForge Output

**Input:** Bambu Lab Basic Matte filaments
**Output:** `filaments_autoforge_20250305_143022.csv`

```csv
Brand,Name,TD,Color,Owned
Bambu Lab Basic Matte,Jet Black,0.1,#000000,TRUE
Bambu Lab Basic Matte,Charcoal,0.2,#3C3C3C,TRUE
Bambu Lab Basic Matte,Cool Grey,0.5,#7D8388,TRUE
```

### Auto-Generated Filenames

**Pattern:** `{type}_{format}_{YYYYMMDD}_{HHMMSS}.{ext}`

Examples:

- `filaments_autoforge_20250305_143022.csv`
- `filaments_hueforge_20250305_143542.json`
- `colors_css_20250305_144011.json`

---

## Import System

### Import Format Definition (import-formats.json)

```json
{
  "hueforge": {
    "description": "HueForge filament library JSON export",
    "file_extension": "json",
    "applies_to": "filaments",
    "format_type": "json",
    "field_mapping": {
      "maker": "brand",
      "type": "material_type",
      "finish": "finish",
      "color": "name",
      "hex": "color_hex",
      "td_value": "transmittance"
    },
    "defaults": {
      "type": "PLA",
      "td_value": 1.0
    },
    "transformations": {
      "hex": "ensure_hash_prefix",
      "td_value": "normalize_0_to_10"
    }
  },
  "autoforge_csv": {
    "description": "AutoForge filament library CSV format",
    "file_extension": "csv",
    "applies_to": "filaments",
    "format_type": "csv",
    "columns": [
      {
        "source": "Brand",
        "target": ["maker", "finish"],
        "split_pattern": "(.+?)\\s+(Basic|Matte|Basic Matte|Metallic|Silk)$",
        "groups": [1, 2]
      },
      {
        "source": "Name",
        "target": "color"
      },
      {
        "source": "TD",
        "target": "td_value"
      },
      {
        "source": "Color",
        "target": "hex"
      }
    ]
  }
}
```

### CLI Usage

```bash
# Import from HueForge JSON (adds to user-filaments.json by default)
python -m color_tools filament --import hueforge --file my_filaments.json
# Output: Imported 47 filaments to user-filaments.json, 3 duplicates skipped, 2 errors
# Note: Imports go to user-filaments.json to preserve core database integrity

# Import with merge strategy
python -m color_tools filament --import hueforge --file my_filaments.json \
    --merge-strategy update
# Options: skip (default), update, replace

# Import to core database (requires confirmation for safety)
python -m color_tools filament --import hueforge --file my_filaments.json \
    --target core
# Warning: Modifying core database! Continue? (y/N)

# Dry run (preview without importing)
python -m color_tools filament --import hueforge --file my_filaments.json --dry-run
# Output: Preview of what would be imported

# List available import formats
python -m color_tools filament --list-import-formats
```

**Import Targets:**

- `user` (default): Imports to `user-filaments.json` (creates if doesn't exist)
- `core`: Imports to `filaments.json` (requires confirmation, regenerates hash)

**Import Behavior:**

- Default target is user database to preserve core data integrity
- Duplicate detection checks against BOTH core and user databases
- Core imports trigger hash regeneration automatically

### Import Strategies

**Duplicate Handling:**

- `skip` (default): Skip duplicates, keep existing
- `update`: Update existing records with new data
- `replace`: Replace entire record

**Validation:**

- Required fields present
- Color values in valid ranges
- TD values 0.0 to 10.0
- Hex codes valid format

---

## Format Features

### Literal Values (Export)

```json
"header": "Owned",
"literal": "TRUE"
```

Result: Column contains literal value "TRUE" for all rows (not derived from data)

**Use cases:**

- Status flags (Owned, Active, Verified)
- Default categories
- Format-specific metadata

### Field Combining (Export)

```json
"fields": ["maker", "finish"],
"separator": " "
```

Result: "Bambu Lab Basic Matte"

### Field Splitting (Import)

```json
"split_pattern": "(.+?)\\s+(Basic|Matte|Basic Matte)$",
"groups": [1, 2]
```

Input: "Bambu Lab Basic Matte" → ["Bambu Lab", "Basic Matte"]

### Value Transformations

```json
"transformations": {
  "hex": "ensure_hash_prefix",      // "#FF0000" if missing #
  "td_value": "normalize_0_to_10",  // Scale to 0-10 range
  "color": "title_case"              // "Cool Grey" not "cool grey"
}
```

### Default Values

```json
"defaults": {
  "type": "PLA",
  "td_value": 1.0,
  "finish": "Basic"
}
```

---

## Integration Points

### Hash Verification

- Add `IMPORT_FORMATS_JSON_HASH` to constants.py
- Add `EXPORT_FORMATS_JSON_HASH` to constants.py
- Verify integrity like other data files
- User formats skipped from verification

### Color Space Computation

- Import hex → compute RGB, LAB, HSL, LCH automatically
- Validate colors are in sRGB gamut
- Warn on out-of-gamut colors

### Maker Synonyms

- Apply maker synonyms during import
- "Bambu" → "Bambu Lab" automatically
- Configurable per format

---

## Error Handling

### Import Errors

- Invalid file format
- Missing required fields
- Invalid color values
- Duplicate detection
- Validation failures

**Error Reporting:**

```text
Import Summary:
  ✓ 47 filaments imported successfully
  ⚠ 3 duplicates skipped
  ✗ 2 errors encountered

Errors:
  Line 15: Invalid hex color '#GGGGGG'
  Line 23: Missing required field 'color'
```

### Export Errors

- No matching filaments found
- Output file write permissions
- Invalid format name

---

## Implementation Plan

### Phase 1: Export System

1. Create `export-formats.json` with AutoForge format
2. Implement `import_export.py` module with export functions
3. **Implement merged data loading (core + user files)**
4. Add `--export`, `--output`, `--core-only`, `--list-export-formats` CLI flags
5. Add auto-generated filename logic
6. Write unit tests for export formats (with and without user data)
7. Update documentation

### Phase 2: Import System

1. Create `import-formats.json` with HueForge format
2. Implement import functions in `import_export.py`
3. Add field splitting, transformations, validation
4. **Implement user database import (default target)**
5. **Implement duplicate detection across core + user databases**
6. Add `--import`, `--target`, `--merge-strategy`, `--dry-run` CLI flags
7. Implement duplicate detection and merge strategies
8. **Add hash regeneration for core database imports**
9. Write unit tests for import formats (user and core targets)
10. Update documentation

### Phase 3: Additional Formats

1. Add Cura XML format (export/import)
2. Add PrusaSlicer format (export/import)
3. Add generic JSON format (export/import)
4. Add generic CSV format with column mapping
5. Document format creation for users

---

## Open Questions

### Export System

1. ✅ Auto-generate filename if not specified (timestamp-based)
2. Should output go to stdout by default, or require explicit flag?
3. Do we need `--dry-run` for exports (preview before writing)?
4. Should we support multiple export formats simultaneously?
5. **Should `--core-only` flag exist, or always export merged data?** (User may want to export only official filaments without their custom additions)

### Import System

1. How to handle LAB/HSL/LCH computation from hex imports?
2. Should duplicate detection be by color name, hex, or both?
3. What happens if imported filament has same name but different hex?
4. Should we support batch import from directory (multiple files)?
5. Do we need import validation reports saved to file?
6. **Default import target should be user database (safe) or require explicit flag?**
7. **Should core database imports require hash regeneration?** (Yes - maintain integrity verification)
8. **How to handle duplicate detection across core + user databases?** (Check both, report source of duplicate)

### Format Definitions

1. Should transformations be Python functions or declarative?
2. Do we need conditional logic in format definitions?
3. How to handle format versioning (AutoForge v1 vs v2)?
4. Should formats support custom validation rules?

### User Experience

1. Progress bars for large imports/exports?
2. Interactive mode for resolving conflicts?
3. Rollback capability for failed imports?
4. Import/export history tracking?

---

## Future Enhancements

### Advanced Features

- **Format auto-detection**: Detect format from file content
- **Batch operations**: Import/export multiple files
- **Format conversion**: Import one format, export to another
- **Template system**: User-defined format templates
- **Web API**: REST API for import/export operations

### Integration Opportunities

- **Git integration**: Track filament database changes
- **Cloud sync**: Sync filament libraries across devices
- **QR code generation**: Export filaments as QR codes for scanning
- **Barcode integration**: Import from barcode scans

---

## References

### External Format Documentation

- AutoForge CSV format (analyzed from user example)
- HueForge JSON format (to be researched)
- Cura material XML format (to be researched)
- PrusaSlicer material format (to be researched)

### Related Design Documents

- COLOR_COMPARISON_REDESIGN.md - ColorDiff and match percentage work
- colordeficiency_update.md - CVD expansion plan
- PALETTE_COLOR_HARMONY.md - Color harmony relationships

---

**Last Updated:** 2025-12-05
**Status:** Design phase - awaiting user feedback and prioritization
**Next Steps:** Research HueForge JSON format, design import validation system

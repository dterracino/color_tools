# Import/Export System Design

## Overview

Design for a flexible import/export system for filaments and colors, driven by format definitions. Enables integration with external tools like AutoForge, HueForge, Cura, PrusaSlicer, etc.

**Status:**

- ✅ **v1.0 Export System IMPLEMENTED** (December 2025)
- 📋 **Import System: Design phase** - awaiting prioritization

---

## What's Implemented (v1.0)

### Export System ✅

**Implemented Features:**

- Three hardcoded export formats (AutoForge CSV, generic CSV, JSON)
- CLI integration with existing filter flags
- Auto-generated timestamped filenames
- Merged data exports (core + user files)
- Full test coverage (18 unit tests)

**CLI Usage:**

```bash
# Export filaments with filters
python -m color_tools filament --maker "Bambu Lab" --finish Basic Matte --export autoforge

# Export with custom filename
python -m color_tools filament --export csv --output my_filaments.csv

# Export all colors (auto-generated filename)
python -m color_tools color --export json

# List available export formats
python -m color_tools filament --list-export-formats
python -m color_tools color --list-export-formats
```

**Library Usage:**

```python
from color_tools import export_filaments, export_colors, FilamentPalette

# Export filaments
palette = FilamentPalette.load_default()
bambu = [f for f in palette.records if f.maker == 'Bambu Lab']
export_filaments(bambu, 'autoforge', 'bambu.csv')

# Export colors  
from color_tools import Palette
palette = Palette.load_default()
export_colors(palette.records, 'json', 'colors.json')
```

**Available Formats:**

- `autoforge` - AutoForge filament library CSV (filaments only)
- `csv` - Generic CSV with all fields (both)
- `json` - JSON format for backup/restore (both)

**Implementation Details:**

- Formats defined in `color_tools/export.py` as `EXPORT_FORMATS` dict
- Auto-merge of core + user data files (matching search behavior)
- Auto-generated filenames: `{type}_{format}_{YYYYMMDD}_{HHMMSS}.{ext}`
- Users can temporarily rename user files for core-only exports

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

### ✅ Phase 1: Export System (COMPLETED - v1.0)

**What we implemented:**

1. ✅ Created `export.py` module with export functions
2. ✅ Implemented three formats: AutoForge CSV, generic CSV, JSON
3. ✅ Hardcoded format definitions (no JSON config files needed for v1.0)
4. ✅ Merged data loading (core + user files automatically combined)
5. ✅ Added `--export`, `--output`, `--list-export-formats` CLI flags
6. ✅ Auto-generated timestamped filename logic
7. ✅ Comprehensive unit tests (18 tests covering all formats)
8. ✅ Updated documentation

**What we simplified from original plan:**

- **No JSON format definition files** - Formats are hardcoded in Python for simplicity
- **No --core-only flag** - Users can rename user files if needed (keeps it simple)
- **No hash verification for export formats** - Not needed without JSON config files
- **Limited to 3 essential formats** - Can expand later based on demand

**Why this approach:**

- Faster to ship and iterate
- Simpler codebase (less abstraction)
- Easy to add more formats as Python code
- Can refactor to JSON-driven system later if needed

### 📋 Phase 2: Import System (FUTURE)

**When needed:**

- User requests for importing from HueForge, other tools
- Need to bulk import filament collections
- Migration from other color management tools

**Proposed implementation:**

1. Create `import-formats.json` with HueForge format (or hardcode like exports)
2. Implement import functions in `export.py` (or new `import_export.py`)
3. Add field splitting, transformations, validation
4. Implement user database import (default target for safety)
5. Implement duplicate detection across core + user databases
6. Add `--import`, `--target`, `--merge-strategy`, `--dry-run` CLI flags
7. Add hash regeneration for core database imports
8. Write unit tests for import formats (user and core targets)
9. Update documentation

### 📋 Phase 3: Additional Formats (FUTURE)

**Potential additions based on demand:**

1. Cura XML format (export/import)
2. PrusaSlicer format (export/import)
3. HueForge JSON format (import)
4. Generic column-mapped CSV (configurable)
5. User-defined format templates

---

## v1.0 vs. Original Design: What Changed?

### Simplifications Made

#### 1. Hardcoded vs. JSON-Driven Formats

- **Original:** `export-formats.json` and `import-formats.json` config files
- **v1.0:** Formats defined as Python dictionaries in `export.py`
- **Why:** Simpler, faster to ship, easier to maintain for small number of formats
- **Future:** Can refactor to JSON if we need user-customizable formats

#### 2. Data Merging Approach

- **Original:** `--core-only` flag to skip user data
- **v1.0:** Always merge core + user data (users can rename files if needed)
- **Why:** Consistent with search behavior, simpler UX
- **Future:** Add flag if users frequently need core-only exports

#### 3. Format Count

- **Original:** Planned support for AutoForge, HueForge, Cura, PrusaSlicer, generic CSV/JSON
- **v1.0:** Implemented AutoForge CSV, generic CSV, JSON (3 formats)
- **Why:** Focus on immediate needs (AutoForge), add others as requested
- **Future:** Add formats incrementally based on user feedback

### What Stayed the Same

✅ **Auto-generated filenames** - Timestamped to prevent overwrites
✅ **CLI filter integration** - Reuses existing `--maker`, `--type`, `--finish` filters  
✅ **Merged data exports** - Includes user overrides automatically  
✅ **Format listing** - `--list-export-formats` to show what's available  
✅ **Library API** - Functions exportable for programmatic use

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

**Last Updated:** 2025-12-23  
**Status:** v1.0 Export System LIVE! 🚀  
**Next Steps:**

- Gather user feedback on export formats
- Add more formats based on demand (Cura, PrusaSlicer, HueForge)
- Consider import system if users request bulk import capabilities

# Code Metrics Refactoring Report

## Scope and configuration

- Target: `color_tools`
- Configuration: `E:/color_tools/tools/code_metrics.json`
- Default exclusions enabled: `true`
- Custom exclusions: none
- Thresholds: lines 500, code lines 500, classes 1, definition lines 100
- Reproduce: `python tools/code_metrics.py color_tools --report`

## Executive summary

- Files scanned: 81
- Files with unresolved findings: 28
- Line findings: 19
- Class findings: 12
- Long-definition findings: 23
- Analysis errors: 0

## Refactoring candidates

### `color_tools/image/dominance.py`

- Physical lines: 2709 (limit 500, over by 2209)
- Code lines: 1815 (limit 500, over by 1315)
- Classes: 4 (limit 1, over by 3); DominantColor (line 67), DominantColorDiagnostic (line 127), DominanceAnalysis (line 174), _DominantColorCandidate (line 246)
- Long definition: 127 (limit 100, over by 27); function _merge_perceptual_clusters, lines 678-804
- Long definition: 109 (limit 100, over by 9); function _calculate_focal_region, lines 1137-1245
- Long definition: 1126 (limit 100, over by 1026); function analyze_dominant_colors, lines 1398-2523
- Long definition: 137 (limit 100, over by 37); function format_dominance_diagnostics, lines 2526-2662

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/image/basic.py`

- Physical lines: 1221 (limit 500, over by 721)
- Long definition: 103 (limit 100, over by 3); function transform_image, lines 636-738
- Long definition: 315 (limit 100, over by 215); function quantize_image_to_palette, lines 907-1221

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/interactive_manager.py`

- Physical lines: 587 (limit 500, over by 87)
- Long definition: 233 (limit 100, over by 133); method InteractiveFilamentManager._build_ui, lines 124-356
- Long definition: 152 (limit 100, over by 52); method InteractiveFilamentManager._get_display_text, lines 358-509

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/exporters/swatch_image_exporter.py`

- Physical lines: 1107 (limit 500, over by 607)
- Code lines: 796 (limit 500, over by 296)
- Classes: 2 (limit 1, over by 1); SwatchImageOptions (line 77), SwatchImageExporter (line 110)
- Long definition: 221 (limit 100, over by 121); method SwatchImageExporter._write_image, lines 299-519
- Long definition: 196 (limit 100, over by 96); method SwatchImageExporter._draw_card, lines 521-716

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/distance.py`

- Physical lines: 596 (limit 500, over by 96)
- Long definition: 115 (limit 100, over by 15); function delta_e_2000, lines 218-332
- Long definition: 114 (limit 100, over by 14); function delta_e_2000_array, lines 335-448

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/cli.py`

- Physical lines: 942 (limit 500, over by 442)
- Code lines: 825 (limit 500, over by 325)
- Long definition: 793 (limit 100, over by 693); function build_parser, lines 55-847

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/cli_commands/handlers/image.py`

- Long definition: 296 (limit 100, over by 196); function handle_image_command, lines 39-334

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/cli_commands/handlers/filament.py`

- Long definition: 217 (limit 100, over by 117); function handle_filament_command, lines 13-229

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/importers/gpl_importer.py`

- Long definition: 176 (limit 100, over by 76); method GPLImporter._import_palette_impl, lines 116-291

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/image/analysis.py`

- Physical lines: 533 (limit 500, over by 33)
- Classes: 2 (limit 1, over by 1); ColorCluster (line 25), ColorChange (line 90)
- Long definition: 172 (limit 100, over by 72); function extract_color_clusters, lines 138-309

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/cli_commands/handlers/color.py`

- Long definition: 158 (limit 100, over by 58); function handle_color_command, lines 13-170

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/cli_commands/handlers/convert.py`

- Long definition: 140 (limit 100, over by 40); function handle_convert_command, lines 22-161

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/importers/jascpal_importer.py`

- Long definition: 135 (limit 100, over by 35); method JascPalImporter._import_palette_impl, lines 109-243

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/image/conversion.py`

- Long definition: 127 (limit 100, over by 27); function convert_image, lines 34-160

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/validation.py`

- Long definition: 106 (limit 100, over by 6); function validate_color, lines 177-282

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/image/watermark.py`

- Long definition: 101 (limit 100, over by 1); function add_text_watermark, lines 176-276

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/filament_palette.py`

- Physical lines: 1096 (limit 500, over by 596)
- Code lines: 522 (limit 500, over by 22)
- Classes: 2 (limit 1, over by 1); FilamentRecord (line 34), FilamentPalette (line 487)

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.

### `color_tools/exporters/python_exporter.py`

- Physical lines: 847 (limit 500, over by 347)
- Code lines: 546 (limit 500, over by 46)
- Classes: 2 (limit 1, over by 1); PythonExportOptions (line 86), PythonExporter (line 229)

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.

### `color_tools/exporters/base.py`

- Physical lines: 711 (limit 500, over by 211)
- Classes: 4 (limit 1, over by 3); ExporterDependency (line 85), ExporterMetadata (line 116), MissingExporterDependencyError (line 223), PaletteExporter (line 286)

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.

### `color_tools/palette.py`

- Physical lines: 669 (limit 500, over by 169)
- Classes: 2 (limit 1, over by 1); ColorRecord (line 59), Palette (line 361)

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.

### `color_tools/conversions.py`

- Physical lines: 630 (limit 500, over by 130)

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.

### `color_tools/interactive_wizard.py`

- Physical lines: 599 (limit 500, over by 99)

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.

### `color_tools/constants.py`

- Physical lines: 533 (limit 500, over by 33)

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.

### `color_tools/mcp/models.py`

- Classes: 13 (limit 1, over by 12); MCPModel (line 23), ColorCoordinates (line 29), NamedColorMatch (line 44), FilamentMatch (line 57), ColorAnalysis (line 75), ConversionResult (line 86), ColorComparison (line 99), NamedColorSearchResult (line 112), FilamentSearchResult (line 121), FilamentCatalog (line 130), CVDResult (line 140), GamutMappingResult (line 150), ColorNameValidation (line 161)

Suggested investigation:

- Check whether the classes are cohesive and intentionally colocated.

### `color_tools/importers/base.py`

- Classes: 4 (limit 1, over by 3); ImporterDependency (line 44), ImporterMetadata (line 66), MissingImporterDependencyError (line 127), PaletteImporter (line 190)

Suggested investigation:

- Check whether the classes are cohesive and intentionally colocated.

### `color_tools/exporters/paintnet_exporter.py`

- Classes: 2 (limit 1, over by 1); PaintNetExportOptions (line 23), PaintNetExporter (line 30)

Suggested investigation:

- Check whether the classes are cohesive and intentionally colocated.

### `color_tools/filament_collections.py`

- Classes: 2 (limit 1, over by 1); _CollectionDescriptor (line 38), FilamentCollections (line 60)

Suggested investigation:

- Check whether the classes are cohesive and intentionally colocated.

### `color_tools/harmony.py`

- Classes: 2 (limit 1, over by 1); HarmonyColor (line 57), HarmonyResult (line 70)

Suggested investigation:

- Check whether the classes are cohesive and intentionally colocated.

## Analysis errors

None.

## Accepted findings

None included.

## Agent handoff constraints

- Inspect existing behavior and tests before modifying a candidate.
- Preserve public APIs and observable behavior unless separately authorized.
- Treat these metrics as signals, not automatic proof of poor design.
- Apply separation of concerns and DRY without introducing needless abstractions.
- Run relevant tests and static checks after each coherent refactor.

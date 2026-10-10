# Code Metrics Refactoring Report

## Scope and configuration

- Target: `color_tools`
- Configuration: `E:/color_tools/tools/code_metrics.json`
- Default exclusions enabled: `true`
- Custom exclusions: none
- Thresholds: lines 500, code lines 500, classes 1, definition lines 100
- Reproduce: `python tools/code_metrics.py color_tools --report`

## Executive summary

- Files scanned: 87
- Files with unresolved findings: 33
- Line findings: 22
- Class findings: 17
- Long-definition findings: 25
- Analysis errors: 0

## Refactoring candidates

### `color_tools/image/dominance.py`

- Physical lines: 2676 (limit 500, over by 2176)
- Code lines: 1774 (limit 500, over by 1274)
- Classes: 5 (limit 1, over by 4); _KMeansModel (line 58), DominantColor (line 77), DominantColorDiagnostic (line 137), DominanceAnalysis (line 184), _DominantColorCandidate (line 252)
- Long definition: 129 (limit 100, over by 29); function _merge_perceptual_clusters, lines 685-813
- Long definition: 109 (limit 100, over by 9); function _calculate_focal_region, lines 1142-1250
- Long definition: 1088 (limit 100, over by 988); function analyze_dominant_colors, lines 1403-2490
- Long definition: 137 (limit 100, over by 37); function format_dominance_diagnostics, lines 2493-2629

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/image/basic.py`

- Physical lines: 1279 (limit 500, over by 779)
- Code lines: 553 (limit 500, over by 53)
- Long definition: 102 (limit 100, over by 2); function transform_image, lines 666-767
- Long definition: 115 (limit 100, over by 15); function _apply_cvd_matrix_vectorized, lines 770-884
- Long definition: 322 (limit 100, over by 222); function quantize_image_to_palette, lines 958-1279

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/interactive_manager.py`

- Physical lines: 599 (limit 500, over by 99)
- Long definition: 235 (limit 100, over by 135); method InteractiveFilamentManager._build_ui, lines 134-368
- Long definition: 152 (limit 100, over by 52); method InteractiveFilamentManager._get_display_text, lines 370-521

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/exporters/swatch_image_exporter.py`

- Physical lines: 1105 (limit 500, over by 605)
- Code lines: 793 (limit 500, over by 293)
- Classes: 2 (limit 1, over by 1); SwatchImageOptions (line 80), SwatchImageExporter (line 113)
- Long definition: 221 (limit 100, over by 121); method SwatchImageExporter._write_image, lines 302-522
- Long definition: 196 (limit 100, over by 96); method SwatchImageExporter._draw_card, lines 524-719

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/distance.py`

- Physical lines: 601 (limit 500, over by 101)
- Long definition: 115 (limit 100, over by 15); function delta_e_2000, lines 223-337
- Long definition: 114 (limit 100, over by 14); function delta_e_2000_array, lines 340-453

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/cli.py`

- Physical lines: 956 (limit 500, over by 456)
- Code lines: 839 (limit 500, over by 339)
- Long definition: 822 (limit 100, over by 722); function build_parser, lines 40-861

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/cli_commands/handlers/image.py`

- Long definition: 298 (limit 100, over by 198); function handle_image_command, lines 60-357

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/cli_commands/handlers/filament.py`

- Long definition: 242 (limit 100, over by 142); function handle_filament_command, lines 14-255

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/image/analysis.py`

- Physical lines: 556 (limit 500, over by 56)
- Classes: 2 (limit 1, over by 1); ColorCluster (line 34), ColorChange (line 99)
- Long definition: 183 (limit 100, over by 83); function extract_color_clusters, lines 147-329

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/importers/gpl_importer.py`

- Long definition: 176 (limit 100, over by 76); method GPLImporter._import_palette_impl, lines 120-295

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/cli_commands/handlers/color.py`

- Long definition: 158 (limit 100, over by 58); function handle_color_command, lines 13-170

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/cli_commands/handlers/convert.py`

- Long definition: 153 (limit 100, over by 53); function handle_convert_command, lines 23-175

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/importers/jascpal_importer.py`

- Long definition: 135 (limit 100, over by 35); method JascPalImporter._import_palette_impl, lines 113-247

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/image/conversion.py`

- Long definition: 127 (limit 100, over by 27); function convert_image, lines 40-166

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/validation.py`

- Long definition: 106 (limit 100, over by 6); function validate_color, lines 182-287

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/palette.py`

- Physical lines: 830 (limit 500, over by 330)
- Classes: 3 (limit 1, over by 2); _ColorRecordData (line 59), ColorRecord (line 75), Palette (line 449)
- Long definition: 103 (limit 100, over by 3); function load_palette, lines 335-437

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.
- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/image/watermark.py`

- Long definition: 101 (limit 100, over by 1); function add_text_watermark, lines 189-289

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `color_tools/filament_palette.py`

- Physical lines: 1217 (limit 500, over by 717)
- Code lines: 647 (limit 500, over by 147)
- Classes: 4 (limit 1, over by 3); _RequiredFilamentData (line 39), _FilamentData (line 48), FilamentRecord (line 59), FilamentPalette (line 556)

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.

### `color_tools/exporters/python_exporter.py`

- Physical lines: 888 (limit 500, over by 388)
- Code lines: 583 (limit 500, over by 83)
- Classes: 2 (limit 1, over by 1); PythonExportOptions (line 86), PythonExporter (line 229)

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.

### `color_tools/exporters/base.py`

- Physical lines: 713 (limit 500, over by 213)
- Classes: 4 (limit 1, over by 3); ExporterDependency (line 90), ExporterMetadata (line 121), MissingExporterDependencyError (line 225), PaletteExporter (line 288)

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.

### `color_tools/conversions.py`

- Physical lines: 689 (limit 500, over by 189)

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.

### `color_tools/filament_export_dialog.py`

- Physical lines: 616 (limit 500, over by 116)
- Code lines: 544 (limit 500, over by 44)
- Classes: 4 (limit 1, over by 3); ExportTemplate (line 42), TemplateEditor (line 139), TemplateTagHighlighter (line 166), FilamentExportDialog (line 453)

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.
- Check whether the classes are cohesive and intentionally colocated.

### `color_tools/interactive_wizard.py`

- Physical lines: 603 (limit 500, over by 103)

Suggested investigation:

- Examine whether the file contains separable responsibilities before splitting it.

### `color_tools/constants.py`

- Physical lines: 548 (limit 500, over by 48)

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

### `color_tools/exporters/ase_exporter.py`

- Classes: 2 (limit 1, over by 1); _SwatchWriter (line 35), ASEExporter (line 44)

Suggested investigation:

- Check whether the classes are cohesive and intentionally colocated.

### `color_tools/exporters/aseprite_exporter.py`

- Classes: 2 (limit 1, over by 1); AsepriteExportOptions (line 27), AsepriteExporter (line 44)

Suggested investigation:

- Check whether the classes are cohesive and intentionally colocated.

### `color_tools/exporters/glsl_exporter.py`

- Classes: 2 (limit 1, over by 1); GLSLExportOptions (line 89), GLSLExporter (line 180)

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

### `color_tools/filament_manager_gui.py`

- Classes: 2 (limit 1, over by 1); _QMainWindow (line 52), FilamentManagerWindow (line 106)

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

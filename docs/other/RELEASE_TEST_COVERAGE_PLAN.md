# Color Tools 7.0.0 test coverage completion plan

Status: complete; awaiting the user-owned release process
Captured: 2026-10-15  
Scope: final local test-coverage work before the 7.0.0 release review

This document records the actionable gaps found in the final branch-coverage
review. It is a checklist for the next implementation pass, not authorization
to commit, push, tag, publish, or release.

The goal is meaningful behavioral coverage of public contracts and likely
failure modes. Reaching 100% as a number is not a goal. Abstract method bodies,
unreachable parser states, and platform-owned behavior should not receive
artificial tests merely to change the percentage.

## Baseline

The suite was rerun from a fresh temporary coverage database so older or
third-party coverage records could not affect the result:

```powershell
$env:COVERAGE_FILE = Join-Path $env:TEMP 'color-tools-release-review.coverage'
.\.venv\Scripts\python.exe -m pytest --cov=color_tools --cov-branch --cov-report= -q
.\.venv\Scripts\python.exe -m coverage report --include='color_tools/*' --show-missing --skip-covered --skip-empty
```

Results:

- 1,549 tests passed and 2 skipped.
- 14,607 subtests passed.
- 8,576 statements were measured; 1,280 were not covered.
- 2,578 branches were measured; 372 were not covered.
- Combined statement and branch coverage was 82%.
- Twenty source files were completely covered and omitted from the detailed
  report by `--skip-covered`.

The repository's ordinary `.coverage` file was not replaced during this
review. Project reports should remain scoped to `color_tools/*`, because
optional GUI dependencies can contribute synthetic or third-party filenames to
a raw coverage database.

## Completion rules

- [x] Test observable behavior through public entry points where practical.
- [x] Use small deterministic fixtures instead of the complete bundled data set
  when exercising individual branches.
- [x] Assert returned values, output, error type, and relevant error text; do
  not use execution-only tests where a stronger assertion is available.
- [x] Do not calculate expected conversion values with the helper under test.
- [x] Keep parameterized/subtest matrices readable and identify the failed case.
- [x] If a branch is genuinely unreachable, remove or simplify it when safe.
- [x] Exclude a line from coverage only when it is necessarily abstract,
  interpreter/platform-owned, or otherwise impossible to exercise in supported
  use, and record the reason in the code.
- [x] Run focused tests after each area, then the complete suite with branch
  coverage.
- [x] Run strict Pyright and the existing documentation checks after any source
  cleanup prompted by the tests.

## Priority 0: complete before release

### 1. Palette document schema failures

Target: `color_tools/_palette_document.py`

Valid checked-in palette documents are covered, but most negative schema
branches are not. Add a compact invalid-document matrix covering:

- [x] Missing, non-integer, and unsupported `schema_version`.
- [x] Missing or non-object `metadata`.
- [x] Missing, non-string, empty, and whitespace-only `metadata.id` values.
- [x] A metadata ID that does not match the filename stem.
- [x] Missing, non-string, empty, and whitespace-only `metadata.name` values.
- [x] Invalid optional `metadata.description` values, including empty strings.
- [x] Invalid optional `metadata.release_year` values; explicitly reject a
  Boolean as well as strings and floats.
- [x] Missing or non-object `palette`.
- [x] Missing, unknown, or non-string `palette.type`.
- [x] Missing or non-array `palette.colors`.
- [x] Non-string object keys when the parser is called directly with a Python
  mapping. JSON files cannot express this case, but the helper accepts an
  `object` and validates it.
- [x] Error messages include the source filename and the relevant field.

Suggested home: `tests/test_palette_documents.py`.

### 2. Core and user data loading failures

Targets: `color_tools/palette.py`, `color_tools/filament_palette.py`

- [x] Reject a non-array core colors document.
- [x] Reject a non-array user colors document.
- [x] Reject a non-array core filaments document.
- [x] Reject a non-array user filaments document.
- [x] Cover color records with missing required fields, short coordinate arrays,
  invalid RGB values, and invalid hex values with source and index context.
- [x] Cover filament records with each required field missing.
- [x] Cover invalid filament field types and values with source and index
  context.
- [x] Reject the removed `hex2` field with the migration-oriented error.
- [x] Reject a non-object owned-filament document.
- [x] Reject a non-list `owned_filaments` value.
- [x] Reject owned-filament lists containing non-string IDs.
- [x] Cover an exact user-filament override by stable ID.
- [x] Cover different filaments with the same effective RGB.
- [x] Cover sequential user-color replacement by normalized name, unique
  additions, cumulative RGB collision rejection, strict authored fields, and
  structured load events without log-message capture.
- [x] Confirm input files remain unchanged after both successful and failed
  loads.

Suggested homes: `tests/test_palette.py`, `tests/test_user_overrides.py`, and
`tests/test_owned_filaments.py`.

### 3. Maker-synonym merging

Target: `color_tools/filament_palette.py`

- [x] Missing core synonym file produces an empty base mapping.
- [x] Existing aliases repeated with different casing leave the canonical
  entry unchanged.
- [x] Disjoint user aliases extend the canonical entry without removing system
  aliases.
- [x] A maker introduced by `user-filaments.json` can receive aliases.
- [x] Unknown maker keys are rejected.
- [x] Aliases are globally unique case-insensitively and cannot shadow a
  canonical maker name.
- [x] Canonical names and synonyms match case-insensitively.

Suggested home: `tests/test_synonyms.py`.

### 4. Palette matching behavior

Target: `color_tools/palette.py`

- [x] `nearest_color()` in LCH, including hue wraparound.
- [x] `nearest_colors()` in HSL, including hue wraparound.
- [x] `nearest_colors()` in LCH, including hue wraparound.
- [x] Both single- and multiple-result APIs with DE76 aliases.
- [x] Both APIs with DE94 aliases.
- [x] Both APIs with CMC/default and `decmc` aliases.
- [x] Both APIs with CMC 2:1 and CMC 1:1 shorthands.
- [x] Custom CMC lightness/chroma parameters are passed through.
- [x] HyAB remains covered in both APIs.
- [x] An unknown metric raises the documented `ValueError`.
- [x] Count is bounded to 1 through 50.
- [x] Exact-distance ties prefer a user source consistently.

Expected results should be independently pinned or assembled from lower-level
reference functions rather than duplicating the selection implementation.

Suggested homes: `tests/test_palette.py` and `tests/test_hyab.py`.

### 5. Filament matching and hue filtering

Targets: `color_tools/filament_palette.py`,
`color_tools/filament_filter_criteria.py`

- [x] Hue distance wraps correctly across zero degrees.
- [x] An achromatic target bypasses hue filtering.
- [x] Achromatic candidates remain eligible for chromatic targets.
- [x] Chromatic candidates inside and outside the maximum hue delta are
  selected correctly.
- [x] An empty result after hue filtering raises the focused guidance message.
- [x] DE2000/CIEDE2000, DE94/CIE94, DE76/CIE76, Euclidean, CMC/DECMC, and HyAB
  aliases resolve correctly.
- [x] Custom CMC parameters affect the distance function.
- [x] An unknown metric raises the documented `ValueError`.
- [x] A distance failure for one candidate does not discard valid candidates.
- [x] All failed candidate calculations raise `No valid filaments found`.
- [x] Equal-distance results prefer user data; otherwise stable ordering is
  preserved.
- [x] Count is bounded to 1 through 50.
- [x] Scalar, list, and `None` filter inputs are normalized correctly.
- [x] Include/exclude criteria, owned state, TD presence, maker aliases, and
  multi-color mode interact correctly in a small combined fixture.

Suggested homes: `tests/test_filament_filter_criteria.py` and
`tests/test_filament_collections.py`.

### 6. Integrity and user-hash failure behavior

Targets: `color_tools/constants.py`, `color_tools/cli_commands/reporting.py`

- [x] `verify_data_file()` returns false for a missing file.
- [x] Each missing or modified core file produces its own focused error:
  colors, filaments, maker synonyms, and a registered system palette.
- [x] Multiple failed core files accumulate errors instead of stopping at the
  first failure.
- [x] Generating a hash for a missing user file raises `FileNotFoundError`.
- [x] Saving a hash for a missing user file raises `FileNotFoundError`.
- [x] Saving with a supplied hash does not recalculate it.
- [x] A user file without a sidecar is accepted as unverified.
- [x] Missing user files, hash mismatches, empty sidecars, malformed sidecars,
  and unreadable sidecars return focused verification errors.
- [x] User data files and user palettes are both included in aggregate
  verification.
- [x] Example user palettes remain excluded.
- [x] A missing user directory is a successful no-op.
- [x] Hash generation reports an individual failure and continues processing
  other files.
- [x] `--verify-constants`, `--verify-matrices`, `--verify-data`, and
  `--verify-user-data` failure paths print to stderr and exit with status 1.
- [x] Successful user verification uses correct singular and plural labels for
  both data files and palettes.
- [x] `--verify-all` enables every intended verification category.

Suggested homes: `tests/test_constants.py` and `tests/test_cli_reporting.py`.

### 7. Importer framework contracts

Targets: `color_tools/importers/base.py`,
`color_tools/importers/registry.py`

- [x] Reject importer metadata with an empty name, description, extension list,
  empty extension, or extension beginning with a dot.
- [x] Missing-dependency errors cover no extra, one extra, and multiple extras,
  with correct singular/plural wording and public attributes.
- [x] `import_palette()` rejects a missing path and a directory.
- [x] `can_import()` returns false for the wrong extension, a missing/non-file
  path, and an unavailable importer.
- [x] The default format detector accepts a valid matching file.
- [x] `_ensure_dependencies()` raises the documented exception.
- [x] Duplicate importer registration is rejected.
- [x] Unknown explicit format names list available formats.
- [x] Available-only format and extension listings exclude unavailable
  importers; unfiltered listings retain them.
- [x] Detection rejects a missing input file.
- [x] Detection reports an extension with no registered importer.
- [x] Detection reports no recognizing candidate.
- [x] Detection reports ambiguous recognizing candidates.
- [x] Explicit format selection and automatic detection both delegate to the
  selected importer.

Use temporary registry state or patching that is restored after every test so
the global registry cannot leak between cases.

Suggested home: `tests/test_importers.py`.

### 8. Individual importer malformed-file matrices

Targets: GPL, HEX, JASC PAL, and RIFF PAL importers

- [x] Cover case-insensitive supported extensions.
- [x] Cover empty input where the format permits or rejects it.
- [x] Reject invalid or missing format signatures/headers.
- [x] Reject malformed component counts and nonnumeric channels.
- [x] Reject RGB channels outside 0-255.
- [x] Cover comments, blank lines, and optional names where supported.
- [x] Cover declared-count mismatches and premature EOF.
- [x] Cover trailing bytes/records according to each format's contract.
- [x] Cover shared-extension detection between JASC PAL and RIFF PAL.
- [x] Assert imported names, RGB values, source metadata, and palette metadata,
  not merely the number of records.

Suggested home: `tests/test_importers.py`, split by format if that file becomes
too large.

### 9. Exporter framework contracts

Target: `color_tools/exporters/base.py`

- [x] Reject exporter metadata with an empty name, description, or extension.
- [x] Reject an extension beginning with a dot.
- [x] Reject an `options_type` that does not inherit `ExportOptionsBase`.
- [x] Missing-dependency errors cover no extra, one extra, and multiple extras,
  with correct wording and public attributes.
- [x] Unsupported color, palette, and filament operations raise focused
  `NotImplementedError` exceptions.
- [x] Export options are rejected when the exporter accepts none.
- [x] Options of the wrong class identify expected and actual types.
- [x] Palette export falls back to color export when metadata is unsupported.
- [x] Options-aware palette export falls back to options-aware color export.
- [x] An exporter declaring support without implementing the corresponding hook
  fails clearly for colors, filaments, and options-aware variants.
- [x] Missing dependencies are checked before any output is written.
- [x] Generated filenames contain the data type, format, timestamp shape, and
  extension.

Suggested home: `tests/test_export.py` or a focused exporter-base test module.

### 10. 7.0 CLI behavior

Targets: `color_tools/cli_commands/handlers/filament.py`,
`color_tools/cli_commands/handlers/convert.py`

Filament CLI:

- [x] `--limit` without `--nearest` exits with status 2.
- [x] Empty and populated `--list-owned` output and exit successfully.
- [x] Add-owned and remove-owned success paths show the selected filament.
- [x] Add-owned and remove-owned failures print to stderr and exit with status
  1.
- [x] Export without filters respects automatic owned filtering.
- [x] Export with `--all-filaments` uses all records.
- [x] Export with maker/type/finish/color/TD filters uses only matching records.
- [x] Exporter validation failures print to stderr and exit with status 1.
- [x] `--has-td` works for listing, counting, nearest matching, and exporting.
- [x] `--count` remains mutually exclusive with every other operation.
- [x] The manager and GUI dispatch branches forward the selected data path.

Conversion CLI:

- [x] Gamut checking rejects simultaneous or missing `--value`/`--hex` input.
- [x] Gamut checking rejects a non-three-component value.
- [x] Invalid hex errors reach the CLI error boundary.
- [x] LCH gamut input is converted to LAB.
- [x] Out-of-gamut output includes the nearest LAB and RGB values.
- [x] RGB, HSL, LAB, LCH, CMY, and CMYK source routes are exercised through the
  handler.
- [x] RGB, HSL, LAB, LCH, CMY, and CMYK target routes are exercised through the
  handler.
- [x] Invalid CMY/CMYK ranges print the conversion error and exit with status 2.
- [x] `--value` without `--from`, missing conversion input, and incorrect
  component counts exit with status 2.
- [x] Successful output identifies both spaces and the result.

Do not force coverage of unsupported-space branches that `argparse` makes
unreachable. Confirm that they are unreachable and remove redundant checks if
doing so improves the handler.

Suggested home: `tests/test_cli_handlers.py`.

## Priority 1: valuable before release

### 11. MCP conversion matrix

Target: `color_tools/mcp/server.py`

- [x] Wrong component counts for RGB, XYZ, LAB, LCH, HSL, CMY, and CMYK.
- [x] Fractional RGB components are rejected.
- [x] Every supported source space reaches its conversion branch.
- [x] Every supported target space reaches its conversion branch.
- [x] Same-space conversions still validate the supplied value.
- [x] Clamp behavior is passed through for RGB-producing conversions.
- [x] Invalid CMY/CMYK percentages return the public MCP error contract.
- [x] Tool-level conversion results contain the expected source, target, input,
  and output fields.

Suggested home: `tests/test_mcp_server.py`.

### 12. Format-specific exporters

Targets: KPL, Python, swatch-image, and HueForge exporters

- [x] KPL validation and optional-value branches, including both accepted
  metadata shapes and malformed values.
- [x] Python exporter naming, quoting, optional metadata, duplicate handling,
  empty input, and each supported output structure.
- [x] Swatch-image layout boundaries, label/no-label modes, font fallback,
  multi-row layout/wrapping, empty input, narrow-width handling, and file-write
  errors.
- [x] HueForge error previews append an ellipsis when more than three duplicate
  IDs are present.
- [x] HueForge error previews append an ellipsis when more than three records
  lack TD values.
- [x] Plain HEX export remains lowercase by default and uppercase only through
  `HexExportOptions(uppercase=True)`.

Suggested homes: the existing format-specific exporter tests.

### 13. Override reporting

Target: `color_tools/cli_commands/reporting.py`

- [x] Display typed color name-replacement and addition events.
- [x] Display typed filament ID-replacement and addition events.
- [x] Display typed synonym addition and extension events.
- [x] Report no overrides when no loader events are returned.
- [x] Summarize records by source for both colors and filaments.
- [x] A loader failure prints one focused error and exits with status 1.
- [x] Override reporting does not modify logging levels or handlers.

The implementation currently contains fallback branches after selecting the
default palettes that appear unreachable. Confirm this during implementation;
remove them rather than constructing artificial tests if they cannot occur.

Suggested home: `tests/test_cli_reporting.py`.

### 14. Supported image APIs

Targets: `color_tools/image/__init__.py`, `image/conversion.py`,
`image/basic.py`, `image/dominance.py`, and the supported exporters that use
them

- [x] Lazy image exports load only their owning modules.
- [x] A missing optional dependency preserves its precise import cause.
- [x] An unrelated import failure is not disguised as a missing dependency.
- [x] Unsupported image modes and invalid dimensions fail clearly.
- [x] Alpha/transparency branches retain the documented behavior.
- [x] Conversion mode and output-mode branches use small known pixel fixtures.
- [x] Dominance filters cover threshold boundaries, empty selections, fallback
  selection, ordering, and invalid arguments.
- [x] Multi-color block and gradient swatches cover minimum dimensions and
  single-color fallback.

The dominance module is large. Select behavioral boundaries and known
regressions; do not mirror its implementation merely to cover every numerical
line.

Suggested homes: the existing `tests/test_image_*.py` modules.

## Priority 2: focused smoke coverage, not exhaustive interaction coverage

### 15. Interactive terminal workflows

Current baseline:

- `interactive_manager.py`: approximately 22%.
- `interactive_wizard.py`: approximately 35%.

Minimum useful coverage:

- [x] Initial menu dispatch.
- [x] Quit and cancel paths.
- [x] Invalid input followed by retry.
- [x] Empty search/selection handling.
- [x] Add and remove owned-filament operations.
- [x] Wizard completion returns the expected criteria/options.
- [x] User-visible messages describe the selected operation and failure.

The terminal manager does not provide an export operation. Export confirmation,
success, cancellation, and failure therefore belong to the desktop workflow
below rather than the terminal coverage target.

Prefer testing focused decision helpers. If substantial terminal input/output
logic cannot be isolated without fragile mocks, first extract a small cohesive
helper rather than building a monolithic scripted-session test.

Suggested homes: `tests/test_interactive_manager.py` and
`tests/test_interactive_wizard.py`.

### 16. Optional Qt workflows

Current baseline:

- `filament_export_dialog.py`: approximately 74%.
- `filament_manager_gui.py`: approximately 80%.

Minimum useful coverage where the supported Qt environment permits:

- [x] Dialog initialization from current filters and export formats.
- [x] Option collection and validation.
- [x] Empty selection and invalid destination handling.
- [x] Save-path cancellation.
- [x] Export success and failure reporting.
- [x] Owned-filament mutations refresh the visible model.
- [x] Closing/canceling does not modify user data.

Platform-owned paint, event-loop, and native-dialog internals are not coverage
targets. Keep these tests deterministic and headless-compatible.

## Low-value gaps and cleanup decisions

- [x] Review uncovered abstract method bodies. Exercise the concrete contract
  through minimal test subclasses; do not directly call abstract placeholders
  solely for coverage. The remaining uncovered `raise NotImplementedError`
  lines are abstract interface sentinels; concrete importer and exporter
  delegation is covered.
- [x] Remove the redundant CMYK length check in the conversion handler if the
  earlier source-space validation makes it impossible to reach.
- [x] Remove unreachable fallback branches in override reporting after
  confirming they cannot occur.
- [x] Decide whether tiny `__main__.py` wrappers need subprocess smoke tests.
  They remain intentionally uncovered: each only delegates to an already
  tested `main()` function, and subprocess coverage would test Python's module
  launcher rather than additional project behavior.
- [x] Narrow broad exception handling discovered during coverage work where a
  focused exception contract is possible. Add a regression test for the
  intended failure, not for silently swallowing arbitrary exceptions. The
  remaining broad catches are deliberate application boundaries, per-file
  continuation behavior, optional third-party fallbacks, or best-effort
  interactive completion; their observable failure behavior is covered.
- [x] Do not spend release time covering disabled work-in-progress image
  prototypes that are explicitly excluded from supported coverage.

## Remaining-gap review

The phase 11 review used a fresh branch-coverage run and included the deployed
root-level `api/` badge endpoints as well as the `color_tools` package.

- The supported source set measured 90% combined statement and branch coverage
  before the final small additions in this phase. Core matching, loading,
  conversion, import/export, integrity, MCP, and supported image modules are
  predominantly in the 90% range.
- `api/color_of_day.py` had only incidental helper coverage and
  `api/filament_of_day.py` was absent because coverage previously declared only
  `color_tools` as a source. Both public badge endpoints are now explicit
  coverage sources and have complete focused coverage.
- The dominance diagnostic formatter was a sizeable uncovered supported helper.
  Its report header, image-level summary, candidate rows, and selected versus
  unselected values now have behavioral coverage.
- The terminal manager's remaining uncovered code is primarily formatted-screen
  construction and individual navigation bindings. Its ownership, filtering,
  save/revert, cancellation, and exit decisions have focused workflow coverage;
  fragile terminal-render scripting is intentionally deferred.
- The desktop dialog's remaining gaps are Qt paint, cursor, syntax-highlighting,
  and native-widget paths. Export options, validation, success, failure,
  cancellation, ownership mutation, reload, and close behavior are covered.
- Lazy optional-dependency import failures and platform-specific formatting
  paths are covered where they can be simulated deterministically. Environment-
  owned import and native event-loop behavior is intentionally not exhaustively
  exercised.
- Remaining isolated branches in otherwise well-covered modules are defensive
  fallbacks, format micro-variants, or parser-precluded CLI states. No further
  release-blocking test gap was identified.

## Execution sequence

Work in bounded batches so failures identify the responsible area:

1. [x] Palette schema and core/user loader failures.
2. [x] Integrity and hash verification failures.
3. [x] Palette and filament matching matrices.
4. [x] Importer base, registry, and malformed formats.
5. [x] Exporter base and format-specific edge cases.
6. [x] Filament and conversion CLI routes.
7. [x] MCP conversion routes.
8. [x] Override reporting.
9. [x] Supported image edge cases.
10. [x] Focused terminal and Qt workflow coverage.
11. [x] Review remaining uncovered branches and classify each as required,
    unreachable/dead, abstract, platform-dependent, or intentionally deferred.
12. [x] Perform a complete FAQ content audit. Review existing questions for
    accuracy and clarity; reconcile answers with the README, Usage,
    Customization, Installation, and Troubleshooting guides; and add useful
    questions exposed by the 7.0 changes. Include user data and validation,
    maker synonyms, filament IDs and overrides, multi-color behavior, TD and
    HueForge export, palette intent and user palettes, CLI count/limit changes,
    optional dependencies, integrity hashes, and breaking-upgrade guidance.
    Remove duplication where another guide should remain authoritative and
    link to that guide from the concise FAQ answer.
13. [x] Run the complete release validation suite.

## Final validation record

Validation was performed locally on 2026-10-16. Build products, coverage data,
documentation output, and clean virtual environments were written under the
system temporary directory rather than the repository.

- Focused test results: all phase-specific suites passed during their
  respective implementation batches.
- Full pytest result: 1,802 passed, 2 skipped, and 16,424 subtests passed in
  145.33 seconds.
- Final statement/branch coverage: 90% combined across `color_tools` and the
  two root-level badge API modules; both badge API modules are fully covered.
- Strict Pyright: zero errors and zero warnings for the repository. The base
  and `[all]` strict installed-wheel consumers also passed with zero errors and
  zero warnings; installed-package `--verifytypes` reported 100% completeness.
- Sphinx coverage and warning-as-error HTML build: both fresh builds passed
  with `-W -E -a`; Sphinx reported 100% documentation coverage and no
  undocumented objects.
- Integrity and installed-package smoke tests: constants, matrices, three core
  data files, 29 registered system palettes, three user data files, and one
  user palette passed verification from the clean wheel installation. The
  released 7.0.0 package loaded 141 colors and 1,545 filaments. The current
  post-release source catalog contains 1,609 filaments.
- Distribution validation: the 7.0.0 wheel and source archive built
  successfully and passed `twine check`. Metadata declares Python 3.12 or
  newer, all intended extras and console entry points are present, required
  data plus `py.typed` are packaged, and repository-only development
  directories are excluded.
- `git diff --check`: passed.
- Remaining uncovered release risks: no local release blocker was identified.
  The hosted Python 3.12, 3.13, and 3.14 CI matrix remains pending until the
  user pushes the repository.
- Deferred platform/optional-feature paths: terminal rendering and navigation
  internals, Qt paint/native-widget/event-loop behavior, optional native
  integration behavior that cannot be exercised deterministically, trivial
  `__main__` delegates, and explicitly disabled image prototypes.
- Commit, push, tag, publish, and release: user-owned; not performed by the
  assistant.

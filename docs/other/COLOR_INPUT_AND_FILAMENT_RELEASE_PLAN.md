# Color Input and Filament Release Plan

## Status and next-session entry point

- Created: 2026-10-10.
- Status: planning only; implementation and data imports have not started.
- Target: the upcoming breaking release, currently prepared as 7.0.0.
- Read this document before the next color-input, filament, or release work.
- Preserve the existing user-palette work and unrelated worktree changes.
- Do not publish the release until the gates below are satisfied.

This plan covers shared RGB/hex validation and parsing, restoration of filament
color handling, possible arbitrary-length multi-color support, configuration
design, critical regression coverage, new filament data imports, and alignment
on a Python 3.12 minimum. The
previously completed user-palette changes remain part of the release.

## Verified baseline

### Filament regressions

The old filament RGB property split a hyphenated `hex` string into components.
It parsed only the first two components, selected `first` or `last`, or averaged
their LAB coordinates and converted that average back to RGB. It did not assign
the second component to a persistent `hex2` field.

The historical parser is visible in
[commit 2e9584a](https://github.com/dterracino/color_tools/commit/2e9584a0fd917dda7c55c868fd4598364abd57c0).
The later module extraction,
[commit c4fb0ec](https://github.com/dterracino/color_tools/commit/c4fb0ec24c3a6610b3fa39e4c635b3a3d9a9a2cf),
introduced the current record initialization model.

Current [filament loading and record initialization](../../color_tools/filament_palette.py):

- Passes JSON `hex` unchanged into `FilamentRecord`.
- Does not populate the record's optional `hex2` from JSON or compound `hex`.
- Sends hyphenated strings to the single-color `hex_to_rgb` parser.
- Silently substitutes black when that conversion returns `None`.
- Checks mode `second`, although the public setter accepts `first`, `last`, `mix`.
- Averages encoded RGB channels in the separate-field `mix` branch, not LAB.
- Computes RGB/LAB once at construction; changing mode later does not update
  those values or rebuild palette RGB indexes.

At review time, loading the database produced 1,050 records. Twenty bundled
records had hyphenated hex strings, and all twenty received black RGB/LAB.
These counts are observations, not permanent test expectations.

Observed red/blue example:

| Input and mode | Current RGB | Historical LAB-average RGB |
| --- | --- | --- |
| `#FF0000-#0000FF`, any accepted mode | `(0, 0, 0)` | Depends on mode |
| Separate `hex`/`hex2`, `last` | `(255, 0, 0)` | `(0, 0, 255)` |
| Separate `hex`/`hex2`, `mix` | `(127, 0, 127)` | `(202, 0, 136)` |

### Why existing tests missed this

- [Database integrity tests](../../tests/test_database_integrity.py) check RGB
  tuple shape and channel range. A fabricated black tuple passes those checks.
- Their dual-color format test rejects commas but does not parse components or
  check expected RGB/LAB.
- [Configuration tests](../../tests/test_config.py) check setting/getting modes
  and thread isolation, not the resulting filament color.
- No discovered dual-color test verifies the full JSON-to-record-to-match path.

The old [review](CODE_REVIEW.md) and [refactoring notes](REFACTOR.md) already
mention silent black fallback and the `last`/`second` mismatch. Those findings
were not converted into behavioral regression gates.

## Workstream 1: consolidate color-input handling

### Inventory to complete before editing

Start with these verified locations; trace their callers and expand the list
before declaring consolidation complete.

| Location | Current responsibility or difference |
| --- | --- |
| [_color_utils.py](../../color_tools/_color_utils.py) | Strict `validate_rgb`, strict `parse_hex`, and an explicit consolidation TODO |
| [conversions.py](../../color_tools/conversions.py) | `hex_to_rgb` returns `None`; uses `lstrip`, unlike the strict parser; `rgb_to_hex` clamps |
| [harmony.py](../../color_tools/harmony.py) | Separate RGB validator requires a tuple, rejects booleans, accepts integer subclasses |
| [importers/base.py](../../color_tools/importers/base.py) | Separate validator uses `isinstance(int)` and consequently accepts booleans |
| [importers/hex_importer.py](../../color_tools/importers/hex_importer.py) | Format-specific regex followed by its own hex-to-integer conversion |
| [cli_commands/utils.py](../../color_tools/cli_commands/utils.py) | Hex adapters print/exit; RGB argument extraction does not itself validate channel bounds |
| [interactive_wizard.py](../../color_tools/interactive_wizard.py) | Interactive RGB channel checks |
| [name handler](../../color_tools/cli_commands/handlers/name.py) and [CVD handler](../../color_tools/cli_commands/handlers/cvd.py) | Repeated RGB range checks |
| [palette.py](../../color_tools/palette.py) | Uses strict shared helpers for factories and user palettes; audit legacy loaders too |
| [validation.py](../../color_tools/validation.py) and [MCP server](../../color_tools/mcp/server.py) | Additional calls/checks around `hex_to_rgb` |
| [filament_palette.py](../../color_tools/filament_palette.py) | Parsing/validation gaps and invalid-input fallback |
| [tooling](../../tooling/) and [tools](../../tools/) | Standalone conversion code and source-format normalization to audit |

Not every range check is duplication: clipping calculated output, gamut checks,
alpha validation, and format-specific syntax are different responsibilities.
Do not mechanically replace them with an 8-bit input validator.

### Contract decisions

- Choose the canonical module and dependency direction. Avoid a cycle in which
  conversions import utilities that already import conversions.
- Decide public versus private exposure and migration for existing imports.
- Define a single strict, single-color hex grammar: digit lengths, ASCII-only
  syntax, prefix count, whitespace, case, alpha, invalid types, and error contract.
- Define RGB container acceptance, length, built-in integers versus subclasses,
  booleans, float acceptance, bounds, and mutation/coercion policy.
- Separate strict 8-bit palette inputs from conversion APIs that intentionally
  accept numeric/floating coordinates. Audit scalar and array APIs before
  changing acceptance rules; do not silently narrow legitimate inputs.
- Decide whether public `hex_to_rgb` retains an Optional-return compatibility
  wrapper or moves to exceptions in this breaking release.
- Keep CLI notification/exit behavior in adapters, not core parsing.
- Keep importer-specific envelopes such as alpha prefixes or whitespace handling
  outside the canonical RGB hex parser.
- Parse compound filament syntax in one focused helper that calls the
  single-color parser for every component. General color APIs must not silently
  interpret a multi-color string as one color.
- Invalid data must yield actionable errors, including file and entry context
  where applicable. Never substitute black or silently drop malformed components.

A wrapper that changes error presentation is not inherently a DRY violation.
The goal is one validation/conversion implementation per contract, with small
boundary adapters where the input format or error presentation differs.

## Workstream 2: filament color model and blending

### Decisions requiring user approval

| Question | Options to evaluate | Initial recommendation, not an approved decision |
| --- | --- | --- |
| Rename `dual_color_mode`? | Keep the name; introduce `multi_color_mode` with aliases; rename/remove old entry points | If arbitrary counts are supported, use multi-color terminology consistently and explicitly decide alias/removal policy |
| Support more than two colors? | Restore two only; support all hyphen-separated components; migrate JSON to an array | Prefer arbitrary component counts over adding `hex3`, `hex4`, etc.; decide the persisted format separately |
| What does `last` mean? | Second component; final component; explicit index selection | Define `last` as the final component; for two colors this preserves historical intent |
| How does `mix` work? | Equal LAB average; other blend model; weighted colors | Restore equal LAB-coordinate averaging as the documented historical behavior; evaluate extension to all components |
| What happens to `hex2`? | Retain compatibility input; expose a derived secondary value; remove it | Decide after reviewing direct constructors and export schemas; do not assume it is a real JSON field |
| Matching representation? | One selected/blended color; nearest individual component | Keep a representative-color contract unless component-wise matching is explicitly requested |

Do not introduce weighted mixtures, indexes, or extra modes merely for hypothetical
uses. LAB averaging is a representative-color approximation, not a physical
prediction of multicolor extrusion, angle-dependent silk, or transmission.

### Implementation requirements after decisions

- Support existing hyphenated database values without losing component order.
- Define single-color behavior for every supported mode.
- Decide empty components, trailing separators, surrounding whitespace, invalid
  components, short-form colors, and practical component-count constraints.
- Validate all components, not just whichever one the mode selects.
- Define how separate `hex2` and compound `hex` interact if both are accepted;
  ambiguous combinations must have an explicit rule, not accidental precedence.
- Place blend calculations in the appropriate shared color-science module;
  filament parsing/selection should orchestrate rather than duplicate conversion.
- Specify rounding, gamut/clamping policy, and whether stored LAB is the average
  or the LAB of the final rounded/clamped RGB. Historical behavior and RGB/LAB
  consistency must both be considered before choosing.
- Preserve stable filament IDs and owned references.
- Review duplicate/override signatures, exact RGB indexes, hue filtering, nearest
  matching, and cache/index consistency under mode selection.
- Wire library loaders, CLI, MCP, GUI swatches/tooltips, generic CSV/JSON exports,
  export-template tags, and AutoForge's single-color representation.
- Decide export schema changes explicitly: dataclass-based exports automatically
  reflect added fields; other outputs use fixed fields.
- Update API exports, docstrings, CLI help, usage/customization/FAQ docs, and
  instruction examples together; remove conflicting `second`/`last` language.

## Workstream 3: configuration lifetime and scope

[config.py](../../color_tools/config.py) currently has three thread-local settings:
`dual_color_mode`, `gamut_tolerance`, and `gamut_max_iterations`.
[gamut.py](../../color_tools/gamut.py) also exposes relevant per-call parameters.

Evaluate each setting separately rather than assuming one design fits all:

- Explicit function/constructor arguments: discoverable, reproducible, no hidden
  mutable state; consider argument propagation and compatibility costs.
- An immutable configuration object: useful if several related values travel
  together; avoid creating infrastructure for only hypothetical settings.
- Existing thread-local defaults: assess worker-thread initialization, cleanup,
  test isolation, and synchronous usage.
- Context-local configuration: assess async task isolation only if current
  supported callers need it.
- Environment variables: assess startup defaults and deployment convenience;
  they should not silently override explicit per-call values.

Record chosen precedence, defaults, validation, scope, and compatibility policy.
Specify whether a palette captures its mode at construction or supports later
reselection. Do not introduce dynamic RGB properties while retaining stale
construction-time indexes. Prefer explicit lifetime semantics over hidden changes.
Reject invalid tolerance/iteration values with a defined error contract.

## Workstream 4: critical regression coverage

Write tests reproducing current failures first; demonstrate they fail on the
unfixed code, then implement. Expected values must not be calculated by the exact
helper under test. Use pinned reference cases plus independently assembled
conversion chains and documented tolerances.

| Area | Required behavioral coverage |
| --- | --- |
| Strict hex grammar | Valid short/long forms, prefix/no prefix, case, wrong lengths, repeated prefixes, whitespace policy, alpha, non-ASCII, invalid types and characters |
| RGB validation | Endpoints, each out-of-range channel, wrong lengths/containers, booleans, floats, NaN/infinity, subclasses, unchanged input |
| Contract consistency | Every public route obeys its approved contract; format adapters retain intentional differences |
| Compound syntax | Two, three, four and larger approved counts; order; malformed and empty components; validation of unselected components |
| Mode selection | Exact first/final RGB, single-color behavior, approved aliases, invalid modes; no `second`/`last` mismatch |
| LAB mixing | Red/blue historical `(202, 0, 136)` reference, asymmetric colors, identical colors, order invariance, multiple components, rounding and gamut policy |
| Stored coordinates | Exact/tolerant RGB/LAB expectations and explicit post-clamp consistency policy, not just tuple shape |
| JSON loading | Core and user files, real hyphenated records, approved separate-field compatibility, contextual failures, unchanged source files |
| Database-wide correctness | Independently parse every component and compare expected selected/blended colors; validate syntax even when mode would not use a component |
| Search/index behavior | Exact RGB lookup, nearest distance/ranking, hue filters, overrides, owned filtering, mode/config lifetime |
| Entry points | Actual CLI modes and error exits, library API, MCP outputs, GUI swatches/tooltips, export and supported round trips |
| Configuration | Default/override precedence, thread/task scope if retained, isolation, mode changes before/after loading, gamut parameters |
| Importers | Format parsing, compound fields, duplicate/conflict detection, ID preservation, deterministic and idempotent updates |

Never assert that all black results are invalid: genuine black is valid. Compare
each result to its source-derived expected value instead. Ensure at least one
real bundled compound record is exercised, alongside stable miniature fixtures.

As a test-quality check, deliberately simulate the old mistakes locally:
remove compound splitting, replace LAB blending with RGB averaging, ignore `last`,
or substitute black for invalid input. The targeted tests must fail for each
mistake. Revert those deliberate mutations before final validation; no new
mutation-testing dependency is required.

## Workstream 5: new filament data imports

### Inputs and intended actions

| Maker | Source files | Requested action |
| --- | --- | --- |
| Bambu Lab | [.source_data/Bambu_PETG_Matte_Hex_Code_Table.pdf](../../.source_data/Bambu_PETG_Matte_Hex_Code_Table.pdf) | Add missing PETG Matte entries and correct existing hex values |
| Bambu Lab | [.source_data/Bambu_PETG_Translucent_Hex_Code_Table.pdf](../../.source_data/Bambu_PETG_Translucent_Hex_Code_Table.pdf) | Add missing PETG Translucent entries and correct existing hex values |
| Bambu Lab | [.source_data/Bambu_PLA_Tough_Hex_Code_Table.pdf](../../.source_data/Bambu_PLA_Tough_Hex_Code_Table.pdf) | Add missing PLA Tough entries and correct existing hex values |
| Overture | [Overture_Hex_Code_List.pdf](../../.source_data/Overture_Hex_Code_List.pdf), [OvertureHexCodes.htm](../../.source_data/OvertureHexCodes.htm) | Reconcile the two sources, correct existing records, add missing records |
| IEMAI | [iemai_filament_colors.csv](../../.source_data/iemai_filament_colors.csv), [iemai_filament_colors_by_material.txt](../../.source_data/iemai_filament_colors_by_material.txt) | Reconcile both inputs and import the new maker's records |

Do not automatically include other Bambu PDFs simply because they are present.
Inspect PDF contents during the import phase; extraction quality and coverage
have not been verified in this planning pass.

The IEMAI files explicitly say no manufacturer-published HEX table was found,
and label values as third-party approximations with confidence/source URLs.
Confirm inclusion criteria and how provenance will be retained before importing.
Do not present these values as manufacturer-certified or invent measured data.
Verify the reported absence of existing IEMAI records before applying the import.

### Extraction and reconciliation process

1. Inventory source dates, materials, product lines, colors, compound entries,
   confidence labels, and duplicate/conflicting rows. Determine whether paired
   files are complementary or repeat the same data.
2. Review existing scripts such as [import_bambu_new.py](../../tooling/import_bambu_new.py),
   [extract_panchroma.py](../../tooling/extract_panchroma.py), and
   [merge_bambu_filaments.py](../../tooling/merge_bambu_filaments.py). Reuse sound
   extraction/normalization patterns, not blind append behavior.
3. Build bounded, testable extraction/import scripts when needed. Keep extraction,
   normalization, comparison, and application separate; do not require PDF/HTML
   extraction dependencies in the runtime library.
4. Normalize maker/material/finish/color names deliberately. Identify existing
   records by ID or approved product identity, not hex, since hex is being corrected.
5. Emit a dry-run report: additions, old/new hex corrections, unchanged records,
   duplicates, unresolved conflicts, rejected rows, and source references.
6. Resolve disagreements explicitly. Do not guess whether different product lines
   or similarly named colors represent the same filament.
7. Preserve IDs, owned references, unrelated metadata, and records absent from the
   new sources. No deletions or TD estimates without explicit approval.
8. Parse all colors with the approved shared helpers, including multi-color
   components. Apply the reviewed changes deterministically and atomically.
9. Run the importer again: it must produce no additional changes.
10. Regenerate protected hashes with [update_hashes.py](../../tooling/update_hashes.py),
    verify integrity, and document actual additions/corrections in the changelog.

Do not modify scientific constants to make imported data fit. Retain original
source files and a reviewable provenance trail.

## Workstream 6: Python 3.12 minimum and reproducible type checking

### Agreed direction and verified baseline

The user approves raising the published 7.0.0 minimum from Python 3.10 to
Python 3.12. Drop support for 3.10 and 3.11; declare `>=3.12` without an upper
bound. Standardize the development baseline and analysis target on 3.12.
This work is scheduled for the next implementation pass, not completed here.

| Surface | Current declaration or observed state | Required alignment |
| --- | --- | --- |
| [pyproject.toml](../../pyproject.toml) | `requires-python = ">=3.10"`; classifiers for 3.10, 3.11, 3.12 | Raise the floor to 3.12; remove dropped classifiers |
| [pyrightconfig.json](../../pyrightconfig.json) | Strict mode, Python 3.10 target, repository `.venv` | Keep strict checking and target Python 3.12 |
| [.venv/pyvenv.cfg](../../.venv/pyvenv.cfg) | Python 3.12.9, no system site packages | Already meets the new floor; recreation is conditional |
| [.vscode/settings.json](../../.vscode/settings.json) | Test discovery configured, no repository interpreter default | Provide a portable repository-venv default and document explicit interpreter selection |
| [CI workflow](../../.github/workflows/ci.yml) | Tests on 3.10, 3.11, 3.12; installed-wheel typing checks on 3.12 | Change the test matrix to 3.12, 3.13, 3.14; retain 3.12 as the minimum-version baseline |
| [Docs workflow](../../.github/workflows/docs.yml) | Builds on 3.11 | Build on 3.12 or a validated retained runtime |
| [Exporter tests](../../tests/test_exporters_extended_formats.py) | Generated Pyright configuration targets 3.10 | Target 3.12, including generated-code compatibility tests |

Editor environment discovery currently reports the repository `.venv` selected.
The settings tool reports a basic/open-files editor analysis setting, while the
repository Pyright file declares strict mode. These observations do not prove
which final configuration the language server applies to every file. Investigate
configuration discovery, overrides, interpreter selection, and analyzer versions
before attributing inconsistent diagnostics solely to Python version differences.

Using a 3.12 interpreter with a 3.10 analysis target is not inherently invalid:
the target can intentionally enforce an older library compatibility floor.
However, for the approved 3.12 floor those declarations should agree. Raising
the floor alone does not guarantee deterministic strict diagnostics.

### Implementation checklist

- [ ] Inventory all active Python constraints, CI/build/deployment pins, tool
  targets, classifiers, generated test configurations, and environment setup docs.
- [ ] Update package metadata and Pyright's target to 3.12; retain strict mode.
- [ ] Align VS Code/Pylance and command-line Pyright on the repository
  configuration, environment, dependencies, and known analyzer versions.
  Verify configuration-loading logs and actual diagnostics, not just settings.
- [ ] Use a portable workspace-relative interpreter default, not an absolute
  developer-machine path. Confirm the selected interpreter separately because
  changing the default may not replace a previously saved editor selection.
- [ ] Keep the existing 3.12 venv if healthy. If a runtime update or recreation is
  necessary, inventory required extras, recreate safely with an approved 3.12
  runtime, reinstall from repository manifests, and reselect it in VS Code.
  Do not merely edit `pyvenv.cfg` or mutate system Python.
- [ ] Update the GitHub Actions test matrix to quoted versions `"3.12"`,
  `"3.13"`, and `"3.14"`, removing 3.10 and 3.11. Run tests and applicable
  optional-feature coverage on all three versions; explicitly report dependency
  incompatibilities rather than silently skipping coverage. Keep development
  and Pyright's compatibility target at 3.12. Preserve or deliberately revise
  version-conditional coverage upload and installed-wheel typing jobs.
- [ ] Update the GitHub Actions docs build from 3.11 to 3.12; review other
  build/release workflows and hosted API/deployment runtime support.
  Report any platform unable to run 3.12 rather than assuming compatibility.
- [ ] Update current support statements in README badges/text,
  [Installation](../Installation.md), [CONTRIBUTING](../../CONTRIBUTING.md),
  [SUPPORT](../../SUPPORT.md), [docs README](../README.md), repository
  instructions, and tooling guidance where it shares this package's floor.
  Preserve historical changelog entries and clearly historical review documents.
- [ ] Record the 3.10/3.11 support removal in breaking-change release notes and
  migration instructions; older runtimes must use an appropriate earlier release.
- [ ] Review optional extras and dependency minimums for 3.12 compatibility.
  Validate base, image, GUI, interactive, MCP, and docs environments as applicable.
  Review `typing_extensions` uses/declarations before replacing them; do not
  assume every backport is obsolete just because the floor increased.
- [ ] Read the official
  [Python 3.11 changes](https://docs.python.org/3.11/whatsnew/3.11.html) and
  [Python 3.12 changes](https://docs.python.org/3.12/whatsnew/3.12.html).
  Adopt newly guaranteed typing/stdlib features only where useful, preserving
  behavior rather than performing unrelated syntax modernization.
- [ ] Distinguish the 3.12 development baseline from the supported newer-version
  range. Select and validate retained newer runtimes before adding classifiers
  or claiming tested support; do not require all environments to use 3.12 forever.
- [ ] Run full tests, strict repository Pyright, installed-wheel consumer checks,
  `--verifytypes`, and package/docs builds on 3.12. Test the highest explicitly
  supported runtime too; report unavailable environments and skipped extras.
- [ ] Inspect built metadata for the correct `Requires-Python` and confirm no
  source or generated output inadvertently requires a version above 3.12.
- [ ] Check for accidental residual active 3.10/3.11 declarations and reproduce
  consistent diagnostics after reopening the workspace.

The known compatibility cost is intentional: 7.0.0 will no longer install on
Python 3.10 or 3.11. No intrinsic library blocker was established in this planning
pass; deployment compatibility, optional dependencies, and the exact source of
editor/CLI diagnostic disagreement still require validation.

## Execution order and release gates

1. Re-read this plan and current worktree; capture baseline tests and diagnostics.
2. Finish caller/contract inventory and resolve the decision tables with the user.
   Align the Python 3.12 baseline, metadata, and analysis configuration before
   judging refactor typing results; retain pre-change validation evidence.
3. Add failing regression tests for compound loading, `last`, and LAB mixing.
4. Consolidate validation/parsing and restore filament behavior; migrate adapters.
5. Implement only the approved multi-color/config changes and migration policy.
6. Complete behavioral, database-wide, and route-level coverage.
7. Extract/reconcile/import new datasets using the now-tested color contracts.
8. Update hashes, release notes, migration docs, CLI/API examples, and version
   references. Existing 7.0.0 version preparation is not release approval.
9. Run focused tests, then the full suite, strict Pyright, Problems-panel checks,
   integrity verification, and diff checks. Record exact commands and results.
10. Review the complete release diff with the user before their commit/release.

Run Python using the configured project virtual environment. Expected final
commands, to confirm against current repository tooling at implementation time:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
.\.venv\Scripts\python.exe -m pyright
.\.venv\Scripts\python.exe -m color_tools --verify-all
git diff --check
```

Run applicable CLI/stdio integration tests and optional-feature tests with their
required extras present. Skips must be explained; a skipped route is not verified.
Use existing Markdown linting if available. No unrelated dependency or framework
additions are required by this plan.

### Definition of done

- [ ] User-approved parsing, mode, blending, and configuration contracts recorded.
- [ ] One canonical implementation per RGB/hex contract; boundary adapters tested.
- [ ] Existing compound data loads and selects/mixes correctly.
- [ ] No silent black fallback or discarded invalid component.
- [ ] Arbitrary-color support and `hex2` compatibility follow approved decisions.
- [ ] All relevant consumers and serializers use a consistent representation.
- [ ] Regression tests catch each known failure, including actual database loading.
- [ ] Imports have reviewed provenance, preserved identities, and idempotent results.
- [ ] Documentation, migration notes, hashes, and version metadata are synchronized.
- [ ] Python 3.12 package floor, analysis target, development environment, CI,
  deployment/build runtimes, and current support documentation agree.
- [ ] Editor and command-line strict checking are reproducible; installed-wheel
  metadata and consumer typing checks pass on the declared minimum.
- [ ] Full validation passes; no outstanding source/type/Markdown diagnostics.
- [ ] No commit, push, or release performed by the assistant.

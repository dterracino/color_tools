# Color Input and Filament Release Plan

## Status and next-session entry point

- Created: 2026-10-10.
- Updated: 2026-10-12.
- Status: configuration, canonical color inputs, multi-color records, and
  gamut precision are implemented. Swatches and additional modes remain
  planned. Python 3.12 migration is locally validated on 3.12, 3.13, and 3.14;
  confirmation from the next GitHub CI run remains pending.
- Target: the upcoming breaking release, currently prepared as 7.0.0.
- Read this document before the next color-input, filament, or release work.
- Preserve the existing user-palette work and unrelated worktree changes.
- Do not publish the release until the gates below are satisfied.

This plan covers shared RGB/hex validation and parsing, restoration of filament
color handling, possible arbitrary-length multi-color support, configuration
design, critical regression coverage, new filament data imports, and alignment
on a Python 3.12 minimum. The
previously completed user-palette changes remain part of the release.

## Current implementation checklist

### Approved configuration-first sequence

Replace configuration first, then consolidate RGB validation/hex parsing and
change filament representation. Remove the old system completely; no aliases
or backwards-compatibility implementation. Implement only `first`, `last`,
and `srgb_mean` now, defaulting to `first`. Describe other modes as future work
in docstrings and reject them until implemented.

`get_config()` returns the current frozen `ColorConfig` instance itself, with
no copy/live mutable view. `reset_config()` restores defaults in the current
context; context exit still restores the enclosing snapshot.

The implemented record step preserves original `hex`, stores ordered immutable
`rgb_components`, removes `hex2`, and exposes computed `effective_hex` for
single-color consumers. Audit all source/effective hex consumers before edits.
Compound JSON parsing is now implemented through the shared parser.

### Approved input contracts and current implementation

- Strict RGB: tuple/list of exactly three built-in integers in 0-255.
  Reject booleans, floats, integer subclasses, and coercion. Palette factories
  store immutable tuples; scientific float/array conversions retain their contracts.
- Single hex: 3/4/6/8 ASCII digits, optionally one `#`. Four/eight-digit forms
  are CSS/PNG RGBA, not Windows/Android ARGB. Validate alpha then drop it for now.
  Reject whitespace around a single color. `hex_to_rgb` now raises `ValueError`;
  `rgb_to_hex` validates rather than clipping.
- Compound hex: any positive number of components, with -, ASCII space,
  comma, _, /, :, or ; separators. Permit surrounding spaces and spaces around
  punctuation; reject empty components/repeated punctuation. Keep duplicates.
- `hex2` is removed, including from templates/exports; loader errors direct
  callers to move all components into `hex`. Preserve source hex for identity.
- `srgb_mean` uses equal weights and nearest-even rounding once per channel.
  Final LAB is derived from effective RGB. Other modes remain unimplemented.
- Generic CSV/JSON and MCP include source hex, components, and effective hex.
  AutoForge, filament-of-day SVG, and GUI swatches use the effective color.
- `_color_utils.py` owns validation/parsing/formatting without importing conversions.
  Palette factories/JSON loaders, CLI adapters, harmony, importers, PNG output, semantic
  validation, MCP, image result formatting, and generator tooling reuse it.
  Keep PDF-source text extraction and format-specific ARGB/packed output as
  adapters; keep independent test references and scientific array pipelines.
- `validation.py` remains semantic name plausibility checking. Its narrow
  invalid-hex adapter preserves structured reporting; no name-matching redesign.
- Gamut checks share unrounded `xyz_to_rgb_float`; chroma mapping explicitly
  rejects invalid LAB and infeasible neutral lightness. It is not a globally
  nearest-color optimizer.

### Current-stage validation

The configuration/input/record/gamut stage is complete locally. This does not
complete the swatch, additional-mode, data-import, or remote-CI release gates.

- `.\.venv\Scripts\python.exe -m unittest discover tests`: passed, 1,431 tests,
  three skipped. Two skips exercise missing-`swatch` branches when that package
  is installed; the third is the existing unavailable-Pillow placeholder.
  GUI/template, interactive, image, importer/exporter, and MCP stdio tests ran.
- `.\.venv\Scripts\python.exe -m pyright`: zero errors/warnings, also verified
  against the existing fresh-dependency environment. Pylance has zero errors/
  warnings, the Problems panel is clear, and all 35 `hex_to_rgb` call sites
  passed signature compatibility checking.
- `.\.venv\Scripts\python.exe -m color_tools --verify-all`: passed. No protected
  data/constants changed, so no hashes were regenerated.
- `.\.venv\Scripts\python.exe -m build --wheel --no-isolation --outdir <session-dist>`:
  passed. Installed the wheel without dependency changes into an isolated
  environment; strict consumer checking and runtime contract checks passed.
- Installed-wheel `python -m pyright --verifytypes color_tools --ignoreexternal`:
  passed, 100% completeness. This caught and prompted an explicit annotation
  for the PNG writer's copied `colors` list.
- `.\.venv\Scripts\python.exe -m sphinx -b html docs\sphinx <session-docs>`:
  passed. Build products and logs stay outside the repository.
- `git diff --check`: passed. No commit, push, or release performed.

### Follow-up repository-wide input audit

A second audit on 2026-10-12 searched tracked files independently of ignore
rules, as well as library/API, tooling, source-data scripts, demos, samples,
and documentation. It checked channel bounds/types/counts, integer hex
decoding, regex grammars, prefix handling, compound splitting, and formatting.

- Replaced watermark CLI text/stroke length checks with canonical RGB
  validation, retaining comma-separated integer-text parsing and exit code 1.
- Routed Panchroma, Polymaker, and Bambu source fields through
  `parse_hex_colors` and `rgb_to_hex`. Malformed fields are errors with source
  context; Polymaker no longer accepts a valid six-digit substring inside an
  invalid field. PDF newline cleanup remains a source-format adapter.
- Crayola generation now validates source RGB and normalizes source hex
  through the canonical single-color helpers.
- Python hex exports and color-of-the-day SVG fills use `rgb_to_hex` rather
  than source hex, preserving solid RGB semantics when source text has alpha.
- Remaining format grammars, numeric CLI/MCP adapters, scientific float/array
  operations, alpha checks, output clipping, hash decoding, and name/comment
  formatting are intentional, not duplicate strict RGB/hex implementations.
  The standalone HTML TG16 generator formats browser-generated colors in
  JavaScript; it cannot directly call Python helpers. Historical review and
  proposal documents retain their original illustrative snippets.
- `.\.venv\Scripts\python.exe -m unittest discover tests`: passed, 1,438 tests,
  three skipped. Added seven regression tests covering watermark bounds,
  source adapters, solid SVG output, and Python hex exports. PDF extraction
  tests use mocked table transport because `pdfplumber` is not installed;
  the actual field parsing and validation run through the production scripts.
- `.\.venv\Scripts\python.exe -m pyright`: zero errors/warnings. The Problems
  panel is clear. No protected data or constants were modified.

This section consolidates the subsequent design discussion and is the working
execution checklist. It supersedes conflicting initial recommendations later
in this document. The verified baseline and import-source inventory below remain
useful evidence, not proof that the proposed implementation already exists.

No configuration, mixing, gamut, or swatch implementation is authorized merely
by a proposal appearing here. Resolve the marked decisions before implementing
the affected contract.

### Phase 1: inventory and contract decisions

- [x] Capture the current worktree, diagnostics, and relevant regression baseline.
- [x] Trace configuration consumers, object construction, caches, async callers,
  and worker boundaries. Record where settings are read versus captured.
- [x] Locate **all RGB input validation and hex conversion code throughout the
  repository**, including library modules, CLI, MCP, GUI/TUI, exporters,
  importers, tests, demos, scripts, tooling, and tools.
- [x] Build a caller/contract inventory rather than searching only for known
  helper names. Include channel checks, regexes, integer parsing, prefix removal,
  short-hex expansion, formatting, coercion, and invalid-input fallbacks.
- [x] Route applicable production and internal-consumer code through the new
  canonical helpers. Retain small format/error-presentation adapters, not
  duplicate conversion implementations. Tests may retain independent reference
  calculations and intentionally malformed inputs.
- [x] Distinguish input validation from output clipping, alpha handling,
  floating-coordinate conversions, and gamut checks. Do not narrow legitimate
  scalar or array conversion inputs to strict 8-bit palette inputs.
- [x] Choose a canonical helper location and dependency direction without
  creating a conversions/utilities import cycle.
- [x] Approve hex grammar: prefixes, lengths, ASCII characters, whitespace,
  alpha policy, invalid types, and error contract.
- [x] Approve strict RGB input types, containers, bounds, booleans, integer
  subclasses, floats, and coercion/mutation policy.
- [x] Decide whether public `hex_to_rgb` keeps its optional-return contract or
  changes to exceptions in 7.0.0.
- [x] Decide compound syntax, compatibility for separate `hex2`, and handling
  when both compound `hex` and `hex2` are supplied.
- [x] Decide whether component counts are arbitrary or limited to four.
  Two, three, and four must be supported without adding `hex3`/`hex4` fields.
- [x] Decide deprecation aliases versus removal for old dual-color API names,
  CLI options, and `mix` (historically intended to mean LAB averaging).

#### Inspect the purpose of validation.py

[validation.py](../../color_tools/validation.py) is currently **color-name
plausibility checking**, not the canonical low-level RGB/hex validator.
It matches a supplied name against the loaded CSS palette using optional
RapidFuzz or a standard-library fallback, compares the supplied hex color with
the matched palette color using CIEDE2000, and returns a structured
`ColorValidationRecord`. Its default distance threshold is 20.0.

- [x] Trace its public exports, CLI/MCP routes, import-tool usage, and tests.
- [ ] Review name-match confidence versus color-distance acceptance, threshold
  validation, invalid-hex reporting, optional-dependency parity, and its
  import-time palette snapshot.
- [x] Preserve the distinction between semantic name plausibility and strict
  input validity. Thread its hex parsing through the canonical implementation
  without silently changing its structured reporting contract.
- [ ] Record any independently discovered behavior issues; obtain scope
  approval before broadening this work into a name-matching redesign.

### Phase 2: configuration interface and scope

Preferred design: familiar inspection/set/context APIs, immutable internal
settings, and `ContextVar` storage. Most callers continue using defaults.
This is not a claim that pandas or scikit-learn use the same storage mechanism.

- [x] Finalize typed `get_config`, keyword-based `set_config`, and
  `config_context` signatures and public exports.
- [x] Implement nested overrides with exception-safe restoration.
- [x] Validate updates atomically; invalid updates must not partially change
  settings. Return an immutable value or detached snapshot from `get_config`.
- [x] Define `set_config` as changing the current execution context, not all
  application threads. Document async context inheritance and explicitly
  verify propagation or isolation at actual worker boundaries.
- [x] Filament records capture their effective mode at construction. Later
  overrides must not mutate existing RGB/LAB or invalidate palette indexes.
- [x] Gamut operations capture effective settings once and use that snapshot
  consistently for all internal checks.
- [x] Retain useful explicit per-call overrides with defined precedence:
  explicit argument, effective context configuration, built-in default.
- [x] Make caches whose contents depend on mode respect that mode; review the
  MCP cached filament palette specifically.
- [x] Update CLI, GUI/TUI, and MCP boundaries to use the chosen scope without
  settings leaking into subsequent unrelated work.

### Phase 3: gamut precision and shared validation

- [x] Add regression tests showing that current gamut checks round RGB before
  applying tolerance. Preserve public integer-returning conversion APIs.
- [x] Extract/reuse a floating-point conversion path for gamut calculations;
  do not duplicate transfer curves or scientific matrices.
- [x] Reuse and correct
  [find_nearest_in_gamut](../../color_tools/gamut.py), rather than introducing a
  second mapper for filament blending.
- [x] Validate tolerance as a finite number >= 0, excluding booleans; retain
  default 0.01 in RGB channel units on the 0-255 scale.
- [x] Validate iterations as an integer >= 1, excluding booleans; retain
  default 20. Proposed policy has no arbitrary upper cap.
- [x] Terminate binary search when floating-point progress stops.
- [x] Verify boundary handling, attainable neutral endpoints, invalid LAB
  inputs, and mapped-output guarantees. Define explicit failures where
  preserving lightness cannot produce an in-gamut result.
- [x] Describe the mapper as chroma reduction at constant LCH hue/lightness,
  not a guarantee of the globally nearest color.
- [x] Consolidate parsing/validation using the inventory from Phase 1.
  Remove silent black substitution and discarded malformed components.
- [x] Preserve contextual loader errors identifying the source and entry.

### Phase 4: multi-color representation and modes

- [x] Rename configuration terminology to `multi_color_mode`.
- [x] Retain an immutable ordered tuple of validated source components in each
  filament record, separately from its resolved RGB/LAB.
- [x] Preserve component repetition, source order, stable IDs, owned
  references, and original source information.
- [x] Validate every component even when only one will be selected.
- [x] Keep `first` as the default. Single-component inputs should resolve to
  that component under every mode.
- [x] Implement approved color selection/blending outside CLI/UI adapters.

| Mode | Definition | Decision status |
| --- | --- | --- |
| `first` | First defined component | Implemented |
| `last` | Final defined component | Implemented |
| `representative` | Centrality, then chroma, then source order | User-defined algorithm |
| `lightest` | Highest LAB L* | Proposed; confirm |
| `darkest` | Lowest LAB L* | Proposed; confirm |
| `most_chromatic` | Highest LAB C* | Proposed; confirm |
| `least_chromatic` | Lowest LAB C* | Proposed; confirm |
| `srgb_mean` | Equal arithmetic mean of encoded sRGB channels | Implemented |
| `linear_rgb_mean` | Decode sRGB, mean linear channels, encode to sRGB | Planned |
| `lab_mean` | Equal arithmetic mean of D65 LAB coordinates | Planned |

For `representative`:

1. Convert all components to CIELAB with D65.
2. Sum each component's CIEDE2000 distances to every other component.
3. Retain totals <= minimum total + distance-score tolerance.
4. Among survivors, compute `C* = sqrt(a* squared + b* squared)`.
5. Retain chroma >= surviving maximum chroma - chroma tolerance.
6. Select the earliest surviving component unchanged.

Use independently named internal constants, initially 1.0 each. Both bands
compare against the best score, not pairwise candidate chains. They are
practical tie bands, not merely floating-point protection or proof that the
candidates are visually indistinguishable. Two-component distance totals tie;
identical inputs choose the first. Similar grays choose the first only when
the score/chroma bands admit them.

- [ ] Confirm exact-score/source-order ties for the four proposed extrema
  modes; do not automatically reuse representative-mode tolerance bands.
- [x] Keep implemented mean calculations floating-point until final RGB output.
- [ ] Reuse corrected gamut mapping for out-of-gamut LAB means.
- [ ] Clamp residual numerical overshoot and round once to integer RGB.
  Approved rounding is Python nearest-even, not floor, ceiling, or ties-up.
- [x] Derive stored LAB from final RGB so matching, indexes, and swatches
  describe the same resolved color.
- [x] Document means as alternative empirical models for printed/melted
  co-extruded filament. Users may test and choose a mode; none predicts
  pigment mixing from RGB alone. Equal component weights are the assumption.

### Phase 5: dependency-free record swatches

- [ ] Add consistent swatch conveniences to color and filament records.
- [ ] Return complete PNG `bytes`, never a type conditional on Pillow being
  installed. Add an explicit save convenience returning a `Path`.
- [ ] Reuse [SimplePNGWriter](../../color_tools/image/png_writer.py) and shared
  rendering logic; do not add another PNG encoder or a new image abstraction.
- [ ] Validate RGB without bit-mask wrapping and validate positive integer
  dimensions excluding booleans.
- [ ] Decide method names, default dimensions, output-size/resource limits,
  and undersized-image behavior before implementation.

| Swatch mode | Rendering |
| --- | --- |
| `solid` (default) | Record's already-resolved RGB |
| `blocks` | All original components in source-order vertical sections |
| `gradient` | Equally spaced original component stops, sRGB interpolation |

- [ ] Single-color records render solid under every swatch mode.
- [ ] Partition block pixels deterministically with widths differing by at
  most one pixel; do not silently omit components when width is insufficient.
- [ ] Four-color gradient stops are 0%, 33 1/3%, 66 2/3%, 100%.
  Preserve first/last endpoint pixels and define narrow-gradient behavior.
- [ ] Use encoded sRGB interpolation only; no interpolation-space setting.
- [ ] Do not reread ambient mixing configuration during rendering.
- [ ] Document blocks/gradients as component illustrations, not extrusion
  geometry or additional physical blending predictions.
- [ ] Keep the Pillow-based labeled swatch-sheet exporter distinct.

### Phase 6: integration and regression gates

- [ ] Wire library loaders/direct constructors, public exports, CLI modes and
  errors, MCP schemas/caches, GUI/TUI swatches/tooltips, search/hue filters,
  CSV/JSON exports, template tags, and AutoForge's single-color output.
- [ ] Decide serialized component fields and compatibility explicitly;
  dataclass serialization must not accidentally change the export schema.
- [ ] Add failing tests for compound parsing, `last`, LAB blending, early
  rounding, and invalid-input black fallback before fixing each behavior.
- [ ] Test all supported component counts/modes, order, repetition, invalid
  unselected components, and RGB/LAB/index consistency.
- [ ] Test representative band boundaries, two-color ties, chroma selection,
  and first-in-order tie resolution using independent expectations.
- [ ] Test nested configuration contexts, exception restoration, invalid
  updates, task/thread scope, existing-record lifetime, and cache behavior.
- [ ] Validate decoded PNG dimensions and exact pixels for solid/blocks/
  gradients, deterministic remainders, endpoints, and invalid dimensions.
- [ ] Verify swatches in an isolated base-only installation without Pillow.
- [ ] Exercise real bundled compounds and independently audit every database
  component/result. Retain the mutation checks specified in Workstream 4.

### Phase 7: imports and release completion

- [ ] Execute the Bambu, Overture, and IEMAI reconciliation described in
  Workstream 5 only after shared color contracts are tested.
- [ ] Obtain approval for approximate IEMAI values and provenance policy.
- [ ] Review dry-run reports; preserve IDs/owned references and demonstrate
  deterministic, idempotent imports.
- [ ] Regenerate protected hashes after data changes.
- [ ] Update API/CLI examples, configuration instructions, migration notes,
  optional-dependency guidance, and changelog.
- [ ] Run focused tests, full regression suites, strict repository typing,
  installed-wheel consumers/completeness, integrity checks, Problems-panel
  checks, package/docs builds, and whitespace checks.
- [ ] Preserve all five internal-directory distribution exclusions.
- [ ] Confirm GitHub CI after the user's push and review the complete release
  diff before publication. Do not commit, push, or release automatically.

Python support migration is already locally validated: 1,401 tests with three
skips on each of Python 3.12, 3.13, and 3.14; zero repository strict errors/
warnings in existing and fresh dependency environments; installed-wheel
completeness 100%; consumer and package/docs builds passed. This evidence does
not replace validation after the changes above, nor establish a remote CI pass.

## Historical verified baseline (before the fixes)

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

At the original review, [filament loading and record initialization](../../color_tools/filament_palette.py):

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

| Input and mode | Pre-fix RGB | Historical LAB-average RGB |
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

### Historical initial inventory

These observations describe the pre-change code. The current implementation
inventory and contracts above supersede them.

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

### Historical decisions requiring user approval

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
Implemented: package and analysis floor 3.12, runtime CI
3.12/3.13/3.14, docs builds on 3.12, generated-code checks on 3.12, and
`.python-version` selecting 3.12. Local suites passed on all three runtimes;
fresh-dependency strict validation passed on 3.12. GitHub's Ubuntu validation
still needs the next pushed run. The table and checklist below preserve the
original planning baseline; unrelated color/filament work remains deferred.

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

- [x] User-approved parsing, mode, blending, and configuration contracts recorded.
- [x] One canonical implementation per RGB/hex contract; boundary adapters tested.
- [x] Existing compound data loads and approved modes select/mix correctly.
- [x] No silent black fallback or discarded invalid component.
- [x] Arbitrary-color support and `hex2` removal follow approved decisions.
- [x] All relevant consumers and serializers use a consistent representation.
- [x] Regression tests catch each current-stage failure, including actual database loading.
- [ ] Imports have reviewed provenance, preserved identities, and idempotent results.
- [ ] Documentation, migration notes, hashes, and version metadata are synchronized.
- [ ] Python 3.12 package floor, analysis target, development environment, CI,
  deployment/build runtimes, and current support documentation agree.
- [ ] Editor and command-line strict checking are reproducible; installed-wheel
  metadata and consumer typing checks pass on the declared minimum.
- [ ] Full validation passes; no outstanding source/type/Markdown diagnostics.
- [ ] No commit, push, or release performed by the assistant.

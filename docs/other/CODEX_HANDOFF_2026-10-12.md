# Codex handoff: Color Tools 7.0.0

Prepared on 2026-10-12 after completing the base-package PNG writer replacement.
This is a continuation handoff, not release approval.

## Start here

1. Read repository instructions, including `AGENTS.md` and
   `.github/copilot-instructions.md`, and applicable user instructions.
2. Read the current contracts/status at the top of
   [the release plan](COLOR_INPUT_AND_FILAMENT_RELEASE_PLAN.md).
3. Inspect the current worktree. Preserve existing changes; do not assume a
   clean checkout or discard files supplied by the user.
4. The next requested work is to review
   [the image initialization issues document](../image_init_cleanup_issues.md)
   and continue that cleanup. The previous assistant deliberately did not start
   it while completing the PNG task.
5. Reconcile that document with current source before implementing: its
   `SimplePNGWriter` references are now obsolete.

**Do not commit, push, tag, publish, or release.** The user owns those actions.
Use the project virtual environment; do not install into system Python.
Read actual project source before using attributes/signatures.

Every changed Python file requires strict Pyright checking, including files
excluded from the repository-wide configuration. New modules/classes and public
APIs need Sphinx coverage, not just Markdown documentation. Do not use typing
suppression comments to hide errors. Update the changelog for code changes.

## Repository and revision

- Repository: `dterracino/color_tools`.
- Checkout: `E:\color_tools`.
- Current HEAD at handoff: `1609999` (`DRY refactor of rgb validation and hex parsing`).
- Earlier commits: `4ebcf1a` (configuration refactor), `e4b0ddc` (Python floor).
- Prepared package version: **7.0.0**; this is a breaking release.
- Project interpreter: `E:\color_tools\.venv\Scripts\python.exe`, Python 3.12.9.
- Supported runtime declarations: Python 3.12, 3.13, 3.14; minimum `>=3.12`.
- Base package has no required third-party dependencies.

These revision/worktree facts are a snapshot. Recheck them on arrival.

## Where we are in the release plan

The release plan contains both a current checklist and preserved historical
inventories/proposals. Some later checkboxes remain unchecked despite completed
implementation. Do not treat every unchecked historical item as missing code,
or reapply superseded proposals.

| Plan area | Actual status at handoff | Remaining work |
| --- | --- | --- |
| Phase 1: inventory and contracts | Canonical RGB/hex consolidation and second repository-wide audit complete | Broader semantic `validation.py` review is deferred, not implemented |
| Phase 2: configuration | Complete locally, including context scope, record lifetime, caches, and boundary tests | Revalidate as future modes/routes change |
| Phase 3: gamut/shared validation | Complete locally | Reuse this implementation for future LAB blending |
| Phase 4: multi-color records/modes | Records, `first`, `last`, `srgb_mean` complete | Additional modes and their decisions/tests remain |
| Phase 5: record swatches | Not implemented | PNG encoder prerequisite is now complete; record rendering/API decisions remain |
| Phase 6: integration/regressions | Complete for implemented contracts and current modes | Future mode/swatch integration and associated tests remain |
| Phase 7: imports/release | Not complete | Data reconciliation, approvals, final validation, remote CI and release review |
| Workstream 6: Python minimum | Implemented and previously validated locally on 3.12/3.13/3.14 | Next remote CI confirmation and final post-change release validation |
| Image initialization cleanup | Not started | Review supplied findings, correct stale expectations, implement approved scope |

The latest PNG test total supersedes earlier totals recorded in the plan.
Earlier 3.13/3.14 runs are evidence for the floor migration, not a claim that the
latest PNG changes were rerun on all three runtimes.

## Implemented contracts: do not accidentally undo

### Configuration

- Frozen `ColorConfig` snapshots held in a `ContextVar`.
- Public `get_config`, `set_config`, `reset_config`, `config_context`.
- `get_config()` returns the current frozen instance itself, without copying.
- Updates validate atomically; context exit restores the enclosing snapshot,
  including after exceptions.
- Configuration applies to the current execution context, not all threads.
- Records capture effective RGB/LAB at construction; subsequent configuration
  changes do not mutate records or leave their indexes stale.
- Old configuration/dual-color APIs were removed completely. No aliases or
  backward-compatibility layer.

### Canonical inputs and multi-color records

- Strict RGB: tuple/list of exactly three built-in integers, 0 through 255.
  Reject booleans, floats, integer subclasses, clipping and coercion.
- Scientific float/array conversion APIs retain their distinct contracts.
- Single hex: 3/4/6/8 ASCII digits, optional one `#`.
  Four/eight digits are alpha-last RGBA; validate alpha and discard it.
- Single-color parsing rejects surrounding whitespace.
- Compound hex supports arbitrary positive component counts and separators
  `-`, ASCII space, comma, `_`, `/`, `:`, `;`.
  Preserve order and duplicates; reject empty/malformed components.
- `hex_to_rgb` raises `ValueError`; `rgb_to_hex` validates rather than clipping.
- Filaments retain original `hex` and immutable ordered `rgb_components`.
  `effective_hex` describes their resolved RGB. `hex2` is removed.
- Implemented modes: `first` (default), `last`, `srgb_mean`.
  Means use equal weights, nearest-even rounding once per channel, and derive
  final LAB from resolved RGB.
- Generic CSV/JSON and MCP include source/components/effective representation.
  Single-color outputs use the effective color.
- `_color_utils.py` is the canonical low-level implementation.
- `validation.py` is semantic color-name plausibility checking, not a competing
  low-level validator. Its structured invalid-input reporting was preserved.
- Gamut checks use unrounded `xyz_to_rgb_float`; chroma reduction preserves
  LCH hue/lightness and fails explicitly when the neutral endpoint is infeasible.

### Input audit

The second audit covered tracked files independently of ignore rules, including
tooling/source-data scripts, demos, samples, adapters, and documentation.
Missed watermark, Panchroma/Polymaker/Bambu, Crayola, Python hex export, and
color-of-day SVG paths were migrated and tested.

Intentional exceptions include scientific float/array calculations, alpha
validation, output clipping, binary/format grammars, numeric text adapters,
browser JavaScript generation, and historical illustrative snippets. Do not
mechanically replace these with strict palette-input validation.

## Latest completed task: PNG writer replacement

Canonical import:

```python
from color_tools.png_writer import SimplePNGWriter
```

- [Base writer](../../color_tools/png_writer.py) is the user's supplied replacement,
  reviewed and updated for strict typing and canonical validation.
- Constructor accepts RGB tuple/list sequences and copies both outer/nested
  storage into `tuple[RGB, ...]`. Invalid colors report their index.
- Dimensions require positive built-in integers; PNG limit is `2**31 - 1`.
  No arbitrary allocation/resource cap was added.
- PNG contains IHDR, sRGB intent 0, IDAT, IEND, valid CRCs, 8-bit RGB,
  filter-none scanlines, and zlib level 9 compression.
- `to_bytes()` returns a complete PNG. `save(str | Path)` returns `None`,
  creates parent directories, overwrites, and propagates filesystem failures.
- Restored directory creation was the missing behavior found in the old class.
- LUT exporter now imports the base writer, not the optional image package.
- Old `color_tools/image/png_writer.py` and image-package export are removed,
  without a compatibility alias. Do not reintroduce either.
- Both suites were consolidated into
  [test_png_writer.py](../../tests/test_png_writer.py); the supplied
  `test_png_writer_new.py` no longer exists separately.
- Broader image initialization behavior was intentionally left unchanged.

Sphinx registration was updated for the writer, canonical input module, and
public helper re-exports. Configuration, records, and float conversion API
coverage from the prior refactor was checked in rendered documentation.

## Uncommitted worktree at handoff

| State | Path |
| --- | --- |
| Modified | `CHANGELOG.md` |
| Modified | `color_tools/exporters/palette_lut_exporter.py` |
| Modified | `color_tools/image/__init__.py` |
| Deleted | `color_tools/image/png_writer.py` |
| Modified | `docs/Usage.md` |
| Modified | `docs/other/COLOR_INPUT_AND_FILAMENT_RELEASE_PLAN.md` |
| Modified | `docs/sphinx/index.rst` |
| Modified | `tests/test_png_writer.py` |
| Untracked | `color_tools/png_writer.py` |
| Newly added by this handoff | `docs/other/CODEX_HANDOFF_2026-10-12.md` |

**The untracked base writer is required implementation, not a temporary file.**
Do not omit it from the eventual user-managed commit.

No protected constants or core data changed during the PNG task, so hashes
were not regenerated. Version remains the already-prepared 7.0.0.

## Latest validation evidence

All commands used the project venv unless an isolated installation is noted.

| Validation | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe -m unittest tests.test_png_writer` | 38 tests passed, including optional Pillow cross-checks |
| `.\.venv\Scripts\python.exe -m unittest discover tests` | 1,432 tests passed, three expected skips |
| `.\.venv\Scripts\python.exe -m pyright` | Zero errors/warnings |
| Explicit changed-file strict check below | Zero errors/warnings |
| `.\.venv\Scripts\python.exe -m sphinx -W --keep-going -b html docs\sphinx <session-output>` | Passed |
| `.\.venv\Scripts\python.exe -m build --wheel --no-isolation --outdir <session-dist>` | Passed; corrected wheel inspected and installed |
| Installed `--verifytypes color_tools.png_writer --ignoreexternal` | 100% completeness, 10 known public symbols |
| Installed PNG/LUT runtime checks without Pillow/NumPy | Passed; old module absent from wheel and installation |
| `git diff --check` and Problems panel | Clean |

Explicit changed-file command:

```powershell
.\.venv\Scripts\python.exe -m pyright color_tools\png_writer.py color_tools\exporters\palette_lut_exporter.py color_tools\image\__init__.py tests\test_png_writer.py
```

The three suite skips are existing optional-feature branches: two unavailable-
`swatch` branches when that dependency is installed and an unavailable-Pillow
placeholder. Actual PNG Pillow cross-checks ran.

Packaging pitfall: the first incremental wheel contained a deleted source module
from stale `build\lib\color_tools\image\png_writer.py`. Only that exact generated
file was removed, then the wheel rebuilt, reinstalled, and checked. Watch for
stale build output during later removals. Do not delete broad directories.

Pyright `--verifytypes` initially selected a global Python 3.14 installation.
Successful verification ran outside the checkout with isolated venv
`VIRTUAL_ENV`, its Scripts directory first on PATH, and explicit `--pythonpath`.
Do not report completeness against a different installed package.

## Immediate next task: image initialization cleanup

The user's [issues document](../image_init_cleanup_issues.md) is a static review,
not verified runtime evidence. Read current source and reproduce findings.

Its obsolete requirements must be adjusted:

- `SimplePNGWriter` must not be in the image name table, `__all__`, or
  `TYPE_CHECKING` exports.
- Base-writer dependency-free checks should use `color_tools.png_writer`;
  they already have coverage.
- Do not restore an image-package alias for convenience.

Remaining proposed work includes precise optional-dependency errors, removal
of success-shaped placeholders, lazy imports, honest availability semantics,
type/export-table consistency, and correction of broken docstring examples.
Related watermark findings include Cairo native-load errors, exception
chaining, duplicated compositing, validation, and example correctness.

Verify which dependencies each export actually needs. The image extra includes
more than Pillow/NumPy; do not blindly restrict missing-dependency handling to
two names. Preserve strict public typing and test both installed/missing-extra
paths. Some availability/error behavior is a design decision; confirm meaningful
behavior changes rather than guessing from the review.

## Outstanding work and decisions after cleanup

- Record swatches: not implemented. Decide public method names, default
  dimensions, save-return contract, size/resource policy, insufficient block
  widths, and narrow gradient behavior with the user.
- Planned rendering: solid uses captured effective RGB; blocks use source-order
  components; gradients use equally spaced encoded-sRGB stops. Do not reread
  ambient mixing configuration at render time.
- The current writer has equal-width strips; shared rendering must account for
  variable block remainders/gradient pixels without creating another PNG encoder.
- Additional modes: `representative`, extrema, `linear_rgb_mean`, `lab_mean`
  remain unimplemented. The user explicitly limited the initial stage to the
  three implemented modes.
- The representative algorithm/tie bands are recorded in Phase 4. Confirm
  extrema tie policy separately. LAB means must reuse corrected gamut mapping.
- Broader `validation.py` semantic review remains deferred; do not redesign it
  as part of input consolidation without approval.
- Bambu/Overture/IEMAI data reconciliation/imports have not been applied.
  Follow Workstream 5: reviewed provenance, dry runs, stable IDs/owned references,
  deterministic idempotent updates, no unapproved deletions/TD estimates.
  Approximate IEMAI values require approval.
- Final hashes, migration/release documentation, wheel consumers, integrity
  checks, optional-feature validation and release-diff review remain release gates.
- Remote GitHub CI confirmation remains pending. No remote CI pass was claimed.
- Preserve all five internal-directory distribution exclusions described in
  the release plan; inspect built distributions rather than assuming.
- The user's reminder to enforce strict checking of every changed file has
  been followed, but was not yet persisted into global/project instruction and
  memory files. If continuing that persistence task, follow user requirements
  and available memory facilities; do not claim it was done.

## Local artifacts and resuming validation

Logs/builds are session artifacts, not repository deliverables:

```text
C:\Users\dterr\.copilot\session-state\071dc0ec-60f4-48f9-a1f2-c75ae4aff467\files\png-writer-validation\unittest.log
C:\Users\dterr\.copilot\session-state\071dc0ec-60f4-48f9-a1f2-c75ae4aff467\files\png-writer-validation\build.log
C:\Users\dterr\.copilot\session-state\071dc0ec-60f4-48f9-a1f2-c75ae4aff467\files\png-writer-validation\dist\color_match_tools-7.0.0-py3-none-any.whl
C:\Users\dterr\.copilot\session-state\071dc0ec-60f4-48f9-a1f2-c75ae4aff467\files\png-writer-validation\.venv
C:\Users\dterr\.copilot\session-state\071dc0ec-60f4-48f9-a1f2-c75ae4aff467\files\png-writer-docs.log
C:\Users\dterr\.copilot\session-state\071dc0ec-60f4-48f9-a1f2-c75ae4aff467\files\png-writer-docs
```

Generated Sphinx API/build files are ignored; persistent registrations belong
in `docs/sphinx/index.rst`. Do not commit generated pages or session artifacts.

If artifacts are unavailable in the new environment, rerun validation rather
than treating their absence as a reason to recreate implementation. After new
code changes, earlier passing results do not replace fresh targeted checks.

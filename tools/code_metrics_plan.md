# Generalizing `code_metrics.py`

## Goal

Turn `tools/code_metrics.py` into a portable, standard-library-first Python
codebase metrics tool that can be copied into the `tools/` directory of a
repository and used immediately.

The intended scope is **any Python codebase**, not arbitrary programming
languages. Python's `ast` and `tokenize` modules remain the source of truth for
the language-aware metrics.

## Correctness and usability contract

The finished script should satisfy these rules:

1. Running it with no target scans the repository containing the script.
2. Relative target paths are always resolved from that repository root, not
   from the caller's current working directory.
3. A root scan skips common generated, dependency, cache, editor, and deployment
   directories by default.
4. Users can add exclusions without editing the script and can disable the
   built-in exclusions when necessary.
5. Existing `--path` invocations continue to work while a shorter positional
   target becomes the preferred interface.
6. Metrics and threshold behavior remain deterministic and testable without
   Rich installed. Rich remains an optional presentation enhancement.
7. Valid Python source encodings are handled according to Python's own encoding
   rules.
8. A bad or unreadable file is reported as a problem without aborting the
   remainder of the scan.

## Command-line interface

Preferred usage:

```text
python tools/code_metrics.py
python tools/code_metrics.py color_tools
python tools/code_metrics.py color_tools/api
python tools/code_metrics.py tests
python tools/code_metrics.py color_tools --exclude "color_tools/generated/**"
```

Paths such as `color_tools` and `color_tools/api` are interpreted relative to
the repository root inferred from the script location. Absolute paths remain
supported for deliberately scanning a different tree.

The interface will be:

```text
code_metrics.py [TARGET]
                [--path TARGET]
                [--exclude PATTERN ...]
                [--no-default-excludes]
                [--sort COLUMN]
                [--line-limit N]
                [--class-limit N]
                [--function-line-limit N]
                [--problems-only]
                [--fail-on-problems]
                [--no-color]
```

- `TARGET` defaults to `.` (the repository root).
- `--path` is retained as a compatibility alias for the positional target.
- Supplying both `TARGET` and `--path` is a usage error.
- A target may be one Python file or one directory. Multiple targets are out of
  scope for this pass; one common root keeps display paths and exclusions easy
  to understand.
- `--exclude` is repeatable and additive to the built-in exclusions.
- `--no-default-excludes` disables only the built-in list; explicit
  `--exclude` patterns still apply.
- `--fail-on-problems` returns a nonzero status when any unaccepted threshold
  violation or file error is found. Without it, findings remain informational
  and the command returns zero as it does today.
- Positive integers remain required for the line and function-length limits.
  `--class-limit` permits zero because "no classes in this file" can be a valid
  policy.

## Repository-root behavior

The default repository root will be the parent of the directory containing the
script:

```text
repo/
  tools/
    code_metrics.py
```

This preserves the intended portable workflow: copy the file into another
repository's `tools/` folder and use the same commands there. It also makes the
result independent of the shell's current directory.

The script should keep a single root concept, named generically (for example,
`REPO_ROOT`), for:

- resolving relative targets;
- resolving repository-relative exclusion patterns; and
- displaying paths.

For an absolute target outside the repository, display paths should be relative
to the scan target when possible rather than printing long absolute paths for
every row. The scan/display root should be computed once and passed into the
metrics and rendering layers instead of read through a global helper.

No automatic `git` command or `.gitignore` parser will be introduced. The tool
should remain usable outside Git repositories, and partial reimplementation of
`.gitignore` matching would be error-prone. Explicit built-ins plus repeatable
custom exclusions provide predictable behavior.

## Default exclusions

Traversal must prune excluded directories before inspecting their contents.
Filtering only the final `*.py` list would still walk large environments and
dependency trees.

The built-in directory exclusions should cover common repository noise:

```text
# Version control
.git, .hg, .svn

# Python environments and dependencies
.venv, venv, env, ENV, __pypackages__, site-packages

# Python/test/type-check caches
__pycache__, .pytest_cache, .mypy_cache, .ruff_cache, .pyright,
.hypothesis, .tox, .nox, .cache

# Packaging, builds, generated reports
build, dist, .eggs, eggs, htmlcov

# Editors and deployment metadata
.vscode, .idea, .vercel

# Common non-Python dependency trees
node_modules
```

Directories matching `*.egg-info` must also be excluded. This is the only
built-in wildcard initially required; ordinary entries are exact directory
names and match at any depth.

Broad names that are often legitimate source directories—such as `lib`,
`target`, `site`, `output`, or `temp`—must not be excluded by default. A project
can add those with `--exclude`.

Custom exclusion patterns use repository-relative POSIX-style paths regardless
of platform, so the same command works on Windows and Unix. A directory pattern
excludes that directory and its descendants. The implementation and help text
must include examples and clearly state whether matching is root-relative.

Default exclusions apply even when an excluded directory is supplied as the
explicit target. A user who intentionally wants that content can pass
`--no-default-excludes`. This keeps exclusion behavior consistent and avoids a
special-case traversal rule.

## Threshold policy

Remove the `pymvgen`/`CLAUDE.md` policy wording from the module documentation.
Keep the current defaults as neutral tool defaults:

- line limit: 500;
- classes per file: 1; and
- function or method span: 100 lines.

All three become runtime configuration owned by an immutable `Thresholds`
dataclass. `FileMetrics` methods receive that configuration rather than reading
module-level policy constants. Acceptance markers remain:

```text
# code-metrics: accept lines
# code-metrics: accept classes
# code-metrics: accept monoliths
```

The marker names stay stable so repositories already using them do not need
source changes. "Monoliths" remains the output/marker name for compatibility,
while help text explains it as a function/method length finding.

## Source discovery and decoding

Replace `Path.rglob("*.py")` with an explicit directory walk that can prune
excluded directories early. Discovery responsibilities should be separate from
metric collection:

1. Resolve and validate the target.
2. Walk directories while pruning default and custom exclusions.
3. Yield sorted `.py` paths for deterministic output.
4. Analyze each yielded file independently.

Use `tokenize.open()` or `tokenize.detect_encoding()` so encoding cookies and
UTF-8 BOMs follow Python's own source-decoding behavior. Preserve byte size from
the raw file. If decoding fails, compute the physical line count from the bytes
when possible and record a structured error instead of substituting misleading
zero values.

`FileMetrics` should gain an `error: str | None` field rather than using
`class_count is None` as the implicit parse-error signal. This distinguishes
decoding, syntax, and read failures and gives the output a useful diagnostic.
Language-aware fields remain `None` for errored files.

## Separation of concerns and DRY cleanup

Keep the tool as one portable file, but separate its internal responsibilities:

- `ScanOptions`: repository root, target, and exclusion configuration.
- `Thresholds`: all threshold values.
- discovery functions: path resolution, exclusion matching, and file walking.
- analysis functions: decoding, AST/token metrics, and acceptance markers.
- evaluation functions: convert metrics plus thresholds into finding states.
- summary builder: calculate totals and finding counts once.
- Rich renderer and plain renderer: presentation only.
- CLI parser/main: argument validation, orchestration, and exit status.

Currently the Rich and plain renderers independently calculate totals and
finding states. Introduce a shared report/summary model so both presentations
cannot drift. Do not split the implementation into a package in this pass; a
single copyable script is an explicit usability requirement.

## Output changes

Preserve the current columns, sorting choices, acceptance colors/markers, and
`--problems-only` behavior.

Add concise error reporting for files that cannot be read, decoded, tokenized,
or parsed. The table can continue to show `?` for unavailable metrics, followed
by an error list containing repository-relative path and reason.

When `--problems-only` filters all rows, retain the short "none flagged"
message. Summary counts must distinguish:

- files scanned;
- files displayed;
- unresolved line findings;
- unresolved class findings;
- unresolved monolith findings; and
- file-analysis errors.

Rich and plain output must report the same values.

Machine-readable JSON/CSV output is not part of this pass. The shared report
model will make that straightforward later without complicating the initial
generalization.

## Tests

Add focused tests in `tests/test_code_metrics.py`. Because `tools` is not a
package, tests can load the script through `importlib.util` without changing the
published package layout.

Required coverage:

- no target resolves to the inferred repository root;
- `color_tools` and `color_tools/api` resolve from the repository root even
  when the process working directory differs;
- absolute targets remain absolute;
- positional target and `--path` compatibility behavior;
- supplying both target forms is rejected;
- a single `.py` file can be scanned;
- built-in excluded directory names are pruned at different depths;
- `*.egg-info` is pruned;
- `.vercel`, `.vscode`, `.pytest_cache`, virtual environments, build output,
  and `node_modules` do not contribute files during a root scan;
- repeatable custom exclusions are additive;
- `--no-default-excludes` exposes otherwise excluded Python files;
- sorting remains deterministic;
- UTF-8, UTF-8 BOM, and a valid encoding-cookie source file are analyzed;
- syntax, decoding, and read failures do not stop other files;
- code, comment/docstring, class, function, method, and monolith counts retain
  their current semantics;
- each acceptance marker suppresses only its matching finding;
- each configurable threshold is respected;
- Rich and plain reports use the same summary values;
- `--problems-only` includes file errors;
- default exit status remains zero for findings; and
- `--fail-on-problems` returns nonzero for unresolved findings or file errors.

Tests should use temporary directory trees and must not depend on the live
contents of this repository or on Rich being installed.

## Validation after implementation

Run the following checks from the `color_tools` repository root:

```text
python -m pytest tests/test_code_metrics.py
python -m pytest
python -m pyright
python tools/code_metrics.py --no-color
python tools/code_metrics.py color_tools --no-color
python tools/code_metrics.py color_tools/api --no-color
python tools/code_metrics.py . --problems-only --no-color
git diff --check
```

Also perform one smoke run from a different working directory while invoking
this repository's script by absolute path. That verifies that relative targets
are genuinely repository-root-relative.

After copying the finished script back to `pymvgen/tools/`, verify at least:

```text
python tools/code_metrics.py --no-color
python tools/code_metrics.py core/dfs_core --no-color
python tools/code_metrics.py --path core/dfs_core --no-color
```

The last command specifically proves compatibility with the old invocation
style. Expected output may include more files for the no-target command because
its meaning intentionally changes from `core/dfs_core` to the whole repository.

## Implementation checklist

- [ ] Replace project-specific module documentation and examples.
- [ ] Make the default target the repository root.
- [ ] Add positional `TARGET` while retaining compatible `--path` behavior.
- [ ] Support both directory and single-file targets.
- [ ] Implement early-pruned default directory exclusions.
- [ ] Implement `*.egg-info` exclusion.
- [ ] Add repeatable repository-relative `--exclude` patterns.
- [ ] Add `--no-default-excludes`.
- [ ] Add configurable class and function-length thresholds.
- [ ] Preserve existing acceptance marker names and behavior.
- [ ] Use Python-compatible source encoding detection.
- [ ] Represent per-file failures explicitly and preserve useful basic counts.
- [ ] Move finding evaluation and totals into one shared report model.
- [ ] Make both renderers consume the shared model.
- [ ] Add `--fail-on-problems` without changing the default informational exit
      status.
- [ ] Add the focused test module and all cases listed above.
- [ ] Run focused, full-suite, type-check, smoke, and whitespace validation.
- [ ] Copy to `pymvgen` and run the three compatibility smoke commands there.

## Explicitly deferred

- Metrics for languages other than Python.
- Full `.gitignore` parsing.
- Reading configuration from `pyproject.toml` or another config file.
- Multiple simultaneous scan targets.
- JSON, CSV, or other machine-readable output.
- Packaging or installing the script as a console command.

These can be added later if actual usage shows a need; none is necessary for a
simple, safe root-scan workflow.

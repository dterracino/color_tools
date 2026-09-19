# Markdown Refactoring Report Addendum

This addendum extends `tools/code_metrics_plan.md`. It is intended to be merged
into that implementation plan when `code_metrics.py` is changed.

## Interface

Add a `--report [PATH]` option. `--report` is preferred over `--document`, which
is vague, and `--plan`, which would imply that source metrics alone are enough
to prescribe a safe redesign.

Examples:

```text
python tools/code_metrics.py color_tools --report
python tools/code_metrics.py color_tools --report docs/code_metrics_report.md
```

The option prints the normal terminal table first and then writes a Markdown
refactoring handoff:

- With no path, the destination is `code_metrics_report.md` in the repository
  root.
- A relative path is resolved from the repository root.
- An absolute path remains absolute.
- `--problems-only` controls terminal visibility only. The document always
  represents the complete scan.
- Report generation does not otherwise change threshold handling or exit-code
  behavior.

## Content contract

The Markdown should clearly separate measured evidence from suggested
investigation. It should contain:

1. **Scope and configuration**
   - scanned target;
   - thresholds;
   - default-exclusion state;
   - custom exclusions; and
   - a portable command that reproduces the scan.
2. **Executive summary**
   - files scanned and files with unresolved findings;
   - totals by finding category; and
   - candidates in a compact priority order.
3. **Refactoring candidates**
   - one subsection per file with unresolved findings;
   - exact measurements, thresholds, and amounts over each threshold;
   - class names and source lines for class-count findings;
   - qualified function or method name, kind, start/end lines, and span for
     every over-limit definition; and
   - bounded suggestions such as examining responsibility boundaries,
     extracting cohesive helpers, or separating unrelated classes.
4. **Analysis errors**
   - path, error category, and diagnostic for every file that was not fully
     analyzed.
5. **Accepted findings**
   - accepted overages as context, not as refactoring assignments.
6. **Agent handoff constraints**
   - inspect behavior and tests before modifying a candidate;
   - preserve public APIs and observable behavior unless separately authorized;
   - treat metrics as signals, not automatic proof of poor design;
   - apply separation of concerns and DRY without needless abstraction; and
   - run relevant tests and static checks after each coherent refactor.

When no unresolved findings exist, the report should contain the scope,
configuration, clean summary, and any accepted findings. It must not invent
refactoring work.

## Priority and determinism

The same inputs and configuration should produce the same Markdown. Do not add
a live timestamp. Sort candidate files using this documented tuple:

1. analysis errors;
2. number of over-limit functions or methods;
3. largest definition overage;
4. line-count overage;
5. class-count overage; and
6. repository-relative path as a stable tie-breaker.

Do not introduce an opaque combined severity score.

## Analysis-model changes

The current aggregate counts are insufficient for an actionable handoff.
Retain structural details during the existing AST traversal:

- `ClassMetric`: qualified name and source line;
- `DefinitionMetric`: qualified name, function/method kind, start line, end
  line, and span; and
- `Finding`: category, threshold, measured value, overage, acceptance state,
  and relevant source location when available.

The table counts, summary, and Markdown must all derive from these shared
records. The Markdown renderer must not reparse source files or independently
reimplement threshold logic.

## File-writing behavior

Write the report atomically using a temporary sibling followed by replacement.
Create missing parent directories for an explicitly requested output path. If
writing fails:

- preserve any existing destination;
- print a concise error;
- return a nonzero status; and
- do not suppress the terminal results already printed.

Repeated use of the default path intentionally replaces the previous generated
snapshot.

## Tests to add

- `--report` with no path writes the repository-root default.
- A relative path resolves from the repository root even when the shell's
  working directory differs.
- An absolute path remains absolute.
- Structural records preserve nested qualified names and correct source spans.
- Every unresolved finding appears with measured evidence.
- Accepted findings appear only in the accepted-context section.
- Candidate order follows the documented severity tuple.
- `--problems-only` does not filter the Markdown document.
- A clean scan produces no invented work items.
- Output is deterministic for identical inputs.
- Atomic replacement succeeds normally.
- A failed write preserves an existing report and returns nonzero.
- Rich and plain terminal modes produce the same Markdown because they share
  the same report model.

## Implementation checklist additions

- [ ] Add `--report [PATH]` and repository-root path resolution.
- [ ] Capture class and definition names, kinds, qualified names, and spans in
      the existing AST pass.
- [ ] Normalize threshold results into shared finding records.
- [ ] Generate the six Markdown sections from the shared report model.
- [ ] Implement deterministic priority ordering.
- [ ] Write the output atomically with safe error handling.
- [ ] Add all report-specific tests listed above.
- [ ] Validate both the default and an explicit report destination manually.


"""Per-file source metrics for a package tree (2026-08-14; rich output +
threshold checks added same day).

Dave: a quick way to see, file by file, how big a package has gotten --
filesize, total/code/comment line counts, class count, function count,
character count -- with function count split so module-level functions
(outside any class) don't get lumped in with methods. Comment is an
informational, uncolored column: docstring and comment-only lines count
as Comment, lines containing Python syntax count as Code (including lines
with inline comments), and blank lines count in neither. Together with
blank lines, those mutually exclusive categories reconcile to Lines.

Three checks, colored in the output. The first two are taken directly
from this repo's own CLAUDE.md conventions rather than invented
thresholds:
  - line_count or code_line_count > the configurable line limit (500 by
    default) -- "Large monolithic files should be avoided ... if a file
    is >500 lines, consider splitting it." Lines and Code are colored
    independently, making both the physical size and executable-source
    size visible; set another limit with `--line-limit`.
  - class_count > CLASS_COUNT_ALERT_THRESHOLD (1) -- "Classes should
    generally be one per file."
The third, Dave (2026-08-14, same session): a per-file count of
individual functions/methods that are themselves over
MONOLITH_LINE_THRESHOLD (100) lines long -- "potential refactor
targets down the road." Unlike the first two, this isn't a CLAUDE.md
convention already on the books, just a useful signal on its own.
A file over any of the three thresholds can carry its own inline
marker comment saying the overage is deliberate (see ACCEPT_MARKER_RE
below) -- same spirit as a linter's `# noqa`, and just as
visible/auditable rather than silently suppressing the check.

Rich (`rich.table`/`rich.console`) is used for colored output when it's
importable; falls back to the original plain `print()`-based table
(with a `!`/`~` suffix marking flagged/accepted cells instead of color)
when it isn't -- `rich` is a `requirements-web.txt`-only dependency, so
someone who only ran `pip install -r requirements.txt` for CLI +
dfs_core work shouldn't hit an ImportError just for running this.

Run from the repo root:

    python scripts/code_metrics.py                  # core/dfs_core, file/folder order
    python scripts/code_metrics.py --path app        # the web app's own .py tree
    python scripts/code_metrics.py --path core       # all of core/, including core/tests
    python scripts/code_metrics.py --sort lines      # sort by a metric column instead
    python scripts/code_metrics.py --line-limit 600  # change the Lines/Code warning limit
    python scripts/code_metrics.py --no-color        # force the plain fallback table
    python scripts/code_metrics.py --problems-only   # only list files with an unaccepted flag

Code/Comment and Classes/Functions/Methods/Monoliths are counted with
Python's `tokenize` and `ast` modules, not regex or ad hoc prefix checks,
so docstrings, inline comments, nested classes, decorated/async defs, and
each def's real start/end line are classified correctly.
"Functions" means any `def`/`async def` that is not a direct child of
a class body -- module-level functions, and also a helper function
nested inside another function -- while "Methods" means a `def`/
`async def` that is a direct child of a class body, regardless of
decorator (`@staticmethod`, `@property`, etc. still count). "Monoliths"
counts however many of a file's functions and methods combined (not a
separate function-vs-method split -- either kind of >100-line def is
the same kind of refactor target) exceed MONOLITH_LINE_THRESHOLD lines
of their own, measured start-to-end via `ast`'s `lineno`/`end_lineno`,
not by counting blank lines or comments as code. A file that fails to
parse (a real syntax error, or a non-UTF-8-encoded file) is still
listed with its size/total-line/char counts, just with code/comment/class/
function/method/monolith columns shown as "?" rather than silently
skipping it or crashing the whole run.
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import shutil
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

try:
    __import__("rich")
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCAN_PATH = REPO_ROOT / "core" / "dfs_core"


def _relative_display(path: Path) -> str:
    """`path` relative to REPO_ROOT for display, or the path as-is if
    it isn't under REPO_ROOT at all -- `--path` accepts any absolute
    path (its own --help text says so), and Path.relative_to() raises
    rather than returning something sensible when the two don't share a
    root, so every place this script prints a scanned path needs this
    instead of calling relative_to() directly."""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()

SORT_KEYS = (
    "path",
    "size",
    "lines",
    "code",
    "comment",
    "classes",
    "functions",
    "methods",
    "monoliths",
    "chars",
)

DEFAULT_LINE_LIMIT = 500
CLASS_COUNT_ALERT_THRESHOLD = 1
MONOLITH_LINE_THRESHOLD = 100

# The "we know, and it's on purpose" escape hatch -- e.g., in a file with
# several small, deliberately-grouped dataclasses:
#     # code-metrics: accept classes -- SongConfig's sub-dataclasses are
#     # split for clarity, not accidental bloat.
# One marker per line; `lines`, `classes`, and `monoliths` are the only
# three check names right now (matching the three checks above). `lines`
# accepts both the total and code-line presentation of the same file-size
# check; each check remains independently acceptable so a file can accept
# one overage while still being flagged for the others. The reason text
# after "--" is optional and not parsed -- it's there for the next person
# reading the file, not for this script.
ACCEPT_MARKER_RE = re.compile(r"#\s*code-metrics:\s*accept\s+(lines|classes|monoliths)\b", re.IGNORECASE)


@dataclass
class FileMetrics:
    path: Path
    size_bytes: int
    line_count: int
    code_line_count: int | None  # None means "failed to parse"
    comment_line_count: int | None
    char_count: int
    class_count: int | None  # None means "failed to parse"
    function_count: int | None
    method_count: int | None
    monolith_count: int | None  # functions/methods individually over MONOLITH_LINE_THRESHOLD lines
    accepted_checks: frozenset[str]

    @property
    def display_path(self) -> str:
        return _relative_display(self.path)

    def total_lines_flagged(self, line_limit: int) -> bool:
        return self.line_count > line_limit

    def code_lines_flagged(self, line_limit: int) -> bool:
        return self.code_line_count is not None and self.code_line_count > line_limit

    def line_check_accepted(self, line_limit: int) -> bool:
        return (
            self.total_lines_flagged(line_limit)
            or self.code_lines_flagged(line_limit)
        ) and "lines" in self.accepted_checks

    @property
    def classes_flagged(self) -> bool:
        return self.class_count is not None and self.class_count > CLASS_COUNT_ALERT_THRESHOLD

    @property
    def classes_accepted(self) -> bool:
        return self.classes_flagged and "classes" in self.accepted_checks

    @property
    def monoliths_flagged(self) -> bool:
        return self.monolith_count is not None and self.monolith_count > 0

    @property
    def monoliths_accepted(self) -> bool:
        return self.monoliths_flagged and "monoliths" in self.accepted_checks

    def has_unresolved_problem(self, line_limit: int) -> bool:
        """True if this file has at least one check flagged and not
        accepted, or failed to parse at all. Parse failures count as a
        problem in their own right (worth someone's attention) even
        though there's no lines/classes/monoliths overage to point at --
        --problems-only should surface those too, not hide them."""
        return (
            self.class_count is None
            or (
                (
                    self.total_lines_flagged(line_limit)
                    or self.code_lines_flagged(line_limit)
                )
                and not self.line_check_accepted(line_limit)
            )
            or (self.classes_flagged and not self.classes_accepted)
            or (self.monoliths_flagged and not self.monoliths_accepted)
        )


def _def_line_span(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """A def's own length in lines, `ast`-measured (real `lineno`/
    `end_lineno`, both stdlib-guaranteed since Python 3.8) rather than
    counted by hand -- includes the `def` line itself through its last
    body line. Decorators are intentionally excluded: they affect the
    declaration but are outside the function body's own logic span."""
    assert node.end_lineno is not None  # populated by ast.parse() on Python 3.8+
    return node.end_lineno - node.lineno + 1


def _docstring_lines(tree: ast.Module) -> set[int]:
    """Return physical lines occupied by module/class/function docstrings."""
    lines: set[int] = set()
    containers = (
        ast.Module,
        ast.ClassDef,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
    )
    for node in ast.walk(tree):
        if not isinstance(node, containers) or not node.body:
            continue
        first = node.body[0]
        if not (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            continue
        end_lineno = first.end_lineno
        assert end_lineno is not None  # populated by ast.parse() on Python 3.8+
        lines.update(range(first.lineno, end_lineno + 1))
    return lines


def _source_line_counts(text: str, tree: ast.Module) -> tuple[int, int]:
    """Return mutually exclusive code and comment/docstring line counts.

    A line with both Python syntax and an inline comment is Code. A line
    occupied by a docstring is Comment, as are comment-only lines. Blank
    lines are intentionally in neither category.
    """
    docstring_lines = _docstring_lines(tree)
    code_lines: set[int] = set()
    comment_lines = set(docstring_lines)
    ignored_token_types = {
        tokenize.ENCODING,
        tokenize.ENDMARKER,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.NEWLINE,
        tokenize.NL,
    }

    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            comment_lines.add(token.start[0])
            continue
        if token.type in ignored_token_types:
            continue
        for line_number in range(token.start[0], token.end[0] + 1):
            if line_number not in docstring_lines:
                code_lines.add(line_number)

    # Inline comments share a physical line with code and are classified as
    # Code so the two informational columns never double-count a line.
    comment_lines.difference_update(code_lines)
    return len(code_lines), len(comment_lines)


class _DefCounter(ast.NodeVisitor):
    """Walks a module's AST once, counting classes, a functions/methods
    split, and "monoliths" (individual defs over MONOLITH_LINE_THRESHOLD
    lines). Deliberately hand-rolled rather than `ast.walk()` +
    `isinstance` counts, since a flat walk can't tell a module-level
    function apart from a method -- both are just `FunctionDef` nodes
    with no parent pointer in the stdlib AST. This visitor tracks that
    distinction itself: `visit_ClassDef` inspects its own body directly
    (tallying `methods`) instead of delegating to `generic_visit`, so
    any `FunctionDef`/`AsyncFunctionDef` reached through the default
    `functions`-counting path is, by construction, not a direct class
    member. `monoliths` doesn't need that same functions-vs-methods
    split -- a >100-line method is exactly as much of a refactor target
    as a >100-line module-level function, so both paths feed the same
    counter."""

    def __init__(self) -> None:
        self.classes = 0
        self.functions = 0
        self.methods = 0
        self.monoliths = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes += 1
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.methods += 1
                if _def_line_span(child) > MONOLITH_LINE_THRESHOLD:
                    self.monoliths += 1
                self.generic_visit(child)  # nested defs inside a method body are still "functions"
            else:
                self.visit(child)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        self.functions += 1
        if _def_line_span(node) > MONOLITH_LINE_THRESHOLD:
            self.monoliths += 1
        self.generic_visit(node)


def _human_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024**2:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / 1024**2:.1f} MB"


def collect_metrics(scan_path: Path) -> list[FileMetrics]:
    results: list[FileMetrics] = []
    for path in sorted(scan_path.rglob("*.py")):
        raw_bytes = path.read_bytes()
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            results.append(
                FileMetrics(
                    path=path,
                    size_bytes=len(raw_bytes),
                    line_count=0,
                    code_line_count=None,
                    comment_line_count=None,
                    char_count=0,
                    class_count=None,
                    function_count=None,
                    method_count=None,
                    monolith_count=None,
                    accepted_checks=frozenset(),
                )
            )
            continue

        counter = _DefCounter()
        try:
            tree = ast.parse(text, filename=str(path))
            counter.visit(tree)
            code_lines, comment_lines = _source_line_counts(text, tree)
            classes, functions, methods, monoliths = counter.classes, counter.functions, counter.methods, counter.monoliths
        except SyntaxError:
            code_lines = comment_lines = None
            classes = functions = methods = monoliths = None

        accepted = frozenset(m.group(1).lower() for m in ACCEPT_MARKER_RE.finditer(text))

        results.append(
            FileMetrics(
                path=path,
                size_bytes=len(raw_bytes),
                line_count=len(text.splitlines()),
                code_line_count=code_lines,
                comment_line_count=comment_lines,
                char_count=len(text),
                class_count=classes,
                function_count=functions,
                method_count=methods,
                monolith_count=monoliths,
                accepted_checks=accepted,
            )
        )
    return results


def _sort_value(metrics: FileMetrics, key: str) -> int:
    value = {
        "size": metrics.size_bytes,
        "lines": metrics.line_count,
        "code": metrics.code_line_count,
        "comment": metrics.comment_line_count,
        "classes": metrics.class_count,
        "functions": metrics.function_count,
        "methods": metrics.method_count,
        "monoliths": metrics.monolith_count,
        "chars": metrics.char_count,
    }[key]
    return value if value is not None else -1


def _ordered_rows(rows: list[FileMetrics], sort_key: str) -> list[FileMetrics]:
    # "path" means "leave it alone" -- collect_metrics() already hands
    # back rows in sorted(rglob()) order, i.e. real file/folder order, so
    # there's nothing to re-sort. Every other key re-sorts descending by
    # that metric instead.
    if sort_key == "path":
        return rows
    return sorted(rows, key=lambda m: _sort_value(m, sort_key), reverse=True)


def _print_rich_table(
    rows: list[FileMetrics],
    sort_key: str,
    line_limit: int,
) -> None:
    # Kept local so the optional dependency has no import-time symbols for
    # Pylance to treat as possibly unbound on the plain fallback path.
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    rows = _ordered_rows(rows, sort_key)
    # rich's own terminal-width fallback (80 cols) is too narrow for this
    # table's file paths -- wraps every single row across two lines when
    # stdout isn't a real tty (e.g. piped, or this repo's own sandboxed
    # shell). shutil.get_terminal_size() already implements the right
    # detection order (COLUMNS env var, then the real terminal size), we
    # just give it a wider fallback (120, not 80) for the non-tty case.
    console = Console(width=shutil.get_terminal_size(fallback=(120, 25)).columns)

    table = Table(title=None, header_style="bold")
    table.add_column("File", no_wrap=True, overflow="ellipsis")
    table.add_column("Lines", justify="right")
    table.add_column("Code", justify="right")
    table.add_column("Comment", justify="right")
    table.add_column("Classes", justify="right")
    table.add_column("Methods", justify="right")
    table.add_column("Functions", justify="right")
    table.add_column("Monoliths", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Chars", justify="right")

    total_size = total_lines = total_code = total_comment = total_chars = 0
    total_classes = total_functions = total_methods = total_monoliths = 0
    parse_errors = 0
    flagged_lines = flagged_classes = flagged_monoliths = 0

    for m in rows:
        total_size += m.size_bytes
        total_lines += m.line_count
        total_chars += m.char_count

        total_lines_flagged = m.total_lines_flagged(line_limit)
        code_lines_flagged = m.code_lines_flagged(line_limit)
        line_check_accepted = m.line_check_accepted(line_limit)
        lines_style = (
            "red bold"
            if total_lines_flagged and not line_check_accepted
            else "green"
            if total_lines_flagged
            else None
        )
        if (total_lines_flagged or code_lines_flagged) and not line_check_accepted:
            flagged_lines += 1
        lines_cell = Text(str(m.line_count))
        if lines_style is not None:
            lines_cell.stylize(lines_style)

        if m.code_line_count is None or m.comment_line_count is None:
            code_cell = Text("?", style="dim")
            comment_cell = Text("?", style="dim")
        else:
            total_code += m.code_line_count
            total_comment += m.comment_line_count
            code_cell = Text(str(m.code_line_count))
            code_style = (
                "red bold"
                if code_lines_flagged and not line_check_accepted
                else "green"
                if code_lines_flagged
                else None
            )
            if code_style is not None:
                code_cell.stylize(code_style)
            comment_cell = Text(str(m.comment_line_count))

        if m.class_count is None:
            parse_errors += 1
            classes_cell = Text("?", style="dim")
            functions_cell = Text("?", style="dim")
            methods_cell = Text("?", style="dim")
            monoliths_cell = Text("?", style="dim")
        else:
            assert m.function_count is not None
            assert m.method_count is not None
            assert m.monolith_count is not None
            total_classes += m.class_count
            total_functions += m.function_count
            total_methods += m.method_count
            total_monoliths += m.monolith_count
            classes_style = (
                "yellow bold" if m.classes_flagged and not m.classes_accepted else "green" if m.classes_accepted else None
            )
            if m.classes_flagged and not m.classes_accepted:
                flagged_classes += 1
            classes_cell = Text(str(m.class_count))
            if classes_style is not None:
                classes_cell.stylize(classes_style)
            functions_cell = Text(str(m.function_count))
            methods_cell = Text(str(m.method_count))

            monoliths_style = (
                "magenta bold"
                if m.monoliths_flagged and not m.monoliths_accepted
                else "green"
                if m.monoliths_accepted
                else None
            )
            if m.monoliths_flagged and not m.monoliths_accepted:
                flagged_monoliths += 1
            monoliths_cell = Text(str(m.monolith_count))
            if monoliths_style is not None:
                monoliths_cell.stylize(monoliths_style)

        table.add_row(
            m.display_path,
            lines_cell,
            code_cell,
            comment_cell,
            classes_cell,
            methods_cell,
            functions_cell,
            monoliths_cell,
            _human_size(m.size_bytes),
            str(m.char_count),
        )

    table.add_section()
    table.add_row(
        f"TOTAL ({len(rows)} files)",
        str(total_lines),
        str(total_code),
        str(total_comment),
        str(total_classes),
        str(total_methods),
        str(total_functions),
        str(total_monoliths),
        _human_size(total_size),
        str(total_chars),
        style="bold",
    )

    console.print(table)

    legend = Text()
    legend.append("red", style="red bold")
    legend.append(f" = Lines or Code over {line_limit}, ")
    legend.append("yellow", style="yellow bold")
    legend.append(f" = more than {CLASS_COUNT_ALERT_THRESHOLD} class, ")
    legend.append("magenta", style="magenta bold")
    legend.append(f" = 1+ function/method over {MONOLITH_LINE_THRESHOLD} lines, ")
    legend.append("green", style="green")
    legend.append(" = over a threshold but accepted via a ")
    legend.append("# code-metrics: accept lines|classes|monoliths", style="italic")
    legend.append(" comment in the file.")
    console.print(legend)
    console.print(
        f"{flagged_lines} file(s) over the Lines/Code threshold, {flagged_classes} over the class "
        f"threshold, {flagged_monoliths} with an unaccepted monolith -- not yet marked as accepted."
    )
    if parse_errors:
        console.print(
            f"{parse_errors} file(s) failed to parse -- code/comment/class/"
            'function/method/monolith counts shown as "?".'
        )


def _print_plain_table(
    rows: list[FileMetrics],
    sort_key: str,
    line_limit: int,
) -> None:
    rows = _ordered_rows(rows, sort_key)

    # No color available -- a trailing "!" marks a flagged-and-unaccepted
    # cell, "~" marks a flagged-but-accepted one, matching the red/yellow
    # vs. green split the rich table uses.
    def _mark(value: int, flagged: bool, accepted: bool) -> str:
        suffix = "~" if accepted else "!" if flagged else ""
        return f"{value}{suffix}"

    headers = (
        "File",
        "Lines",
        "Code",
        "Comment",
        "Classes",
        "Methods",
        "Functions",
        "Monoliths",
        "Size",
        "Chars",
    )
    path_col_width = max((len(r.display_path) for r in rows), default=len(headers[0]))
    path_col_width = max(path_col_width, len(headers[0]))

    def fmt_row(
        display_path: str,
        lines: str,
        code: str,
        comment: str,
        classes: str,
        methods: str,
        functions: str,
        monoliths: str,
        size: str,
        chars: str,
    ) -> str:
        return (
            f"{display_path:<{path_col_width}}  {lines:>8}  {code:>8}  "
            f"{comment:>8}  {classes:>8}  {methods:>7}  "
            f"{functions:>9}  {monoliths:>10}  {size:>9}  {chars:>10}"
        )

    table_width = path_col_width + 8 + 8 + 8 + 8 + 7 + 9 + 10 + 9 + 10 + 18
    print(fmt_row(*headers))
    print("-" * table_width)

    total_size = total_lines = total_code = total_comment = total_chars = 0
    total_classes = total_functions = total_methods = total_monoliths = 0
    parse_errors = 0

    for m in rows:
        total_size += m.size_bytes
        total_lines += m.line_count
        total_chars += m.char_count
        total_lines_flagged = m.total_lines_flagged(line_limit)
        code_lines_flagged = m.code_lines_flagged(line_limit)
        line_check_accepted = m.line_check_accepted(line_limit)
        lines_s = _mark(
            m.line_count,
            total_lines_flagged,
            total_lines_flagged and line_check_accepted,
        )

        if m.code_line_count is None or m.comment_line_count is None:
            code_s = comment_s = "?"
        else:
            total_code += m.code_line_count
            total_comment += m.comment_line_count
            code_s = _mark(
                m.code_line_count,
                code_lines_flagged,
                code_lines_flagged and line_check_accepted,
            )
            comment_s = str(m.comment_line_count)

        if m.class_count is None:
            parse_errors += 1
            classes_s = functions_s = methods_s = monoliths_s = "?"
        else:
            assert m.function_count is not None
            assert m.method_count is not None
            assert m.monolith_count is not None
            total_classes += m.class_count
            total_functions += m.function_count
            total_methods += m.method_count
            total_monoliths += m.monolith_count
            classes_s = _mark(m.class_count, m.classes_flagged, m.classes_accepted)
            functions_s = str(m.function_count)
            methods_s = str(m.method_count)
            monoliths_s = _mark(m.monolith_count, m.monoliths_flagged, m.monoliths_accepted)

        print(
            fmt_row(
                m.display_path,
                lines_s,
                code_s,
                comment_s,
                classes_s,
                methods_s,
                functions_s,
                monoliths_s,
                _human_size(m.size_bytes),
                str(m.char_count),
            )
        )

    print("-" * table_width)
    print(
        fmt_row(
            f"TOTAL ({len(rows)} files)",
            str(total_lines),
            str(total_code),
            str(total_comment),
            str(total_classes),
            str(total_methods),
            str(total_functions),
            str(total_monoliths),
            _human_size(total_size),
            str(total_chars),
        )
    )
    print(
        f"\n! = over threshold, unaccepted ({line_limit} Lines or Code / "
        f"{CLASS_COUNT_ALERT_THRESHOLD} class / 1+ def over {MONOLITH_LINE_THRESHOLD} lines)   "
        f"~ = over threshold, accepted via a \"# code-metrics: accept lines|classes|monoliths\" comment"
    )
    if parse_errors:
        print(
            f"{parse_errors} file(s) failed to parse -- code/comment/class/"
            'function/method/monolith counts shown as "?" for those.'
        )


def _positive_int(value: str) -> int:
    """Parse a command-line value that must be greater than zero."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def main() -> int:
    module_description = __doc__ or "Per-file source metrics for a package tree."
    parser = argparse.ArgumentParser(description=module_description.splitlines()[0])
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_SCAN_PATH,
        help="Directory to scan, relative to the repo root or absolute (default: core/dfs_core)",
    )
    parser.add_argument(
        "--sort",
        choices=SORT_KEYS,
        default="path",
        help="Column to sort by, descending -- or \"path\" for real file/folder order (default: path)",
    )
    parser.add_argument(
        "--line-limit",
        type=_positive_int,
        default=DEFAULT_LINE_LIMIT,
        help="Flag both Lines and Code values above this limit (default: 500)",
    )
    parser.add_argument("--no-color", action="store_true", help="Force the plain fallback table even if rich is installed")
    parser.add_argument(
        "--problems-only",
        action="store_true",
        help="Only list files with an unaccepted lines/classes/monoliths flag (or a parse error)",
    )
    args = parser.parse_args()

    scan_path = args.path if args.path.is_absolute() else REPO_ROOT / args.path
    if not scan_path.is_dir():
        print(f"Not a directory: {scan_path}", file=sys.stderr)
        return 1

    rows = collect_metrics(scan_path)
    if not rows:
        print(f"No .py files found under {_relative_display(scan_path)}")
        return 0

    scanned_count = len(rows)
    if args.problems_only:
        rows = [m for m in rows if m.has_unresolved_problem(args.line_limit)]
        if not rows:
            print(
                f"Scanned {scanned_count} .py file(s) under {_relative_display(scan_path)} -- "
                "none flagged. Nothing to show for --problems-only."
            )
            return 0

    print(f"Scanning {_relative_display(scan_path)} ({scanned_count} .py files", end="")
    if args.problems_only:
        print(f", {len(rows)} flagged)...\n")
    else:
        print(")...\n")
    if _RICH_AVAILABLE and not args.no_color:
        _print_rich_table(rows, args.sort, args.line_limit)
    else:
        if not _RICH_AVAILABLE:
            print("(rich not installed -- pip install rich for colored output; falling back to plain text)\n")
        _print_plain_table(rows, args.sort, args.line_limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())

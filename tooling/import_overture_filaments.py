"""Import the approved, database-shaped Overture review file.

The command is a dry run unless ``--apply`` is supplied. Reviewed hex
corrections preserve existing IDs, TD values, and unrelated metadata. Records
absent from the reviewed source are retained.

Usage:
    python tooling/import_overture_filaments.py
    python tooling/import_overture_filaments.py --apply
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tooling._filament_import_utils import (
    _AdditiveImportPlan,
    _build_reconciling_import_plan,
    _filament_id,
    _identity,
    _load_database,
    _merge_maker_records,
    _normalize_hex,
    _required_text,
    _write_database,
)

_DEFAULT_REVIEW = (
    _ROOT / ".source_data" / "overture_filaments_import_review.txt"
)
_DEFAULT_DATABASE = _ROOT / "color_tools" / "data" / "filaments.json"
_EXPECTED_ROWS = 300
_EXPECTED_OMISSIONS = 44
_MAKER = "Overture"
_NULL = "null"


@dataclass(frozen=True, slots=True)
class _Candidate:
    source_page: int
    type_name: str
    finish: str | None
    color: str
    hex_value: str

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return _identity(_MAKER, self.type_name, self.finish, self.color)

    @property
    def record_id(self) -> str:
        return _filament_id(_MAKER, self.type_name, self.finish, self.color)

    @property
    def source_description(self) -> str:
        return f"review page {self.source_page}"

    def to_record(self) -> dict[str, object]:
        return {
            "id": self.record_id,
            "maker": _MAKER,
            "type": self.type_name,
            "finish": self.finish,
            "color": self.color,
            "hex": self.hex_value,
            "td_value": None,
        }


def _parse_candidate(line: str, line_number: int) -> _Candidate:
    """Parse one approved database-shaped review row."""
    fields = [field.strip() for field in line.split(" | ")]
    if len(fields) != 8:
        raise ValueError(f"Review line {line_number}: expected 8 fields")
    page, maker, type_name, finish_value, color, hex_value, td_value, status = fields
    if maker != _MAKER:
        raise ValueError(f"Review line {line_number}: unexpected maker {maker!r}")
    if not type_name or not color:
        raise ValueError(f"Review line {line_number}: type and color are required")
    if status != "OK":
        raise ValueError(f"Review line {line_number}: unresolved status {status!r}")
    if td_value != _NULL:
        raise ValueError(
            f"Review line {line_number}: unexpected TD value {td_value!r}"
        )
    canonical_hex = _normalize_hex(hex_value)
    if canonical_hex != hex_value:
        raise ValueError(
            f"Review line {line_number}: hex is not canonical: {hex_value!r}"
        )
    finish = None if finish_value == _NULL else finish_value
    return _Candidate(int(page), type_name, finish, color, canonical_hex)


def _load_candidates(path: Path) -> list[_Candidate]:
    """Load and validate the approved Overture import-review file."""
    candidates: list[_Candidate] = []
    omission_count = 0
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if line.startswith("# OMITTED_NO_HEX | "):
            omission_count += 1
        elif line and line[0].isdigit():
            candidates.append(_parse_candidate(line, line_number))
    if len(candidates) != _EXPECTED_ROWS:
        raise ValueError(
            f"{path}: expected {_EXPECTED_ROWS} candidates; found {len(candidates)}"
        )
    if omission_count != _EXPECTED_OMISSIONS:
        raise ValueError(
            f"{path}: expected {_EXPECTED_OMISSIONS} omissions; "
            f"found {omission_count}"
        )
    return candidates


def _print_plan(
    plan: _AdditiveImportPlan[_Candidate],
    *,
    apply: bool,
    retained_unmatched: int,
) -> None:
    """Print every proposed Overture database action."""
    print("Overture filament import")
    print(f"Mode: {'APPLY' if apply else 'DRY RUN'}")
    print("Source: approved database-shaped review file")
    print()
    for candidate in plan.additions:
        finish = candidate.finish if candidate.finish is not None else "(none)"
        print(
            f"[ADD] {candidate.type_name} | {finish} | {candidate.color} "
            f"({candidate.hex_value}) [PDF page {candidate.source_page}]"
        )
    for correction in plan.corrections:
        candidate = correction.candidate
        print(
            f"[CORRECT HEX] {correction.existing_id}: "
            f"{correction.existing_hex} -> {candidate.hex_value}"
        )
    for candidate in plan.unchanged:
        print(f"[UNCHANGED] {candidate.record_id} ({candidate.hex_value})")
    for conflict in plan.conflicts:
        print(f"[CONFLICT] {conflict.candidate.record_id}: {conflict.reason}")
    print()
    print("Summary:")
    print(f"  Additions: {len(plan.additions)}")
    print(f"  Hex corrections: {len(plan.corrections)}")
    print(f"  Unchanged reviewed rows: {len(plan.unchanged)}")
    print(f"  Retained existing rows absent from review: {retained_unmatched}")
    print(f"  Audited no-hex omissions: {_EXPECTED_OMISSIONS}")
    print(f"  Conflicts: {len(plan.conflicts)}")


def _build_replacements(
    plan: _AdditiveImportPlan[_Candidate],
    database: Sequence[dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Build hex-only replacements while preserving existing metadata."""
    by_id = {_required_text(record, "id"): record for record in database}
    replacements: dict[str, dict[str, object]] = {}
    for correction in plan.corrections:
        existing = by_id[correction.existing_id]
        replacement = dict(existing)
        replacement["hex"] = correction.candidate.hex_value
        replacements[correction.existing_id] = replacement
    return replacements


def _execute(review_path: Path, database_path: Path, *, apply: bool) -> int:
    """Plan, report, and optionally apply the reviewed Overture import."""
    candidates = _load_candidates(review_path)
    database = _load_database(database_path)
    plan = _build_reconciling_import_plan(candidates, database)
    existing_maker_count = sum(
        _required_text(record, "maker") == _MAKER for record in database
    )
    matched_count = len(plan.corrections) + len(plan.unchanged)
    retained_unmatched = existing_maker_count - matched_count
    _print_plan(plan, apply=apply, retained_unmatched=retained_unmatched)

    if retained_unmatched < 0:
        raise ValueError("Reviewed matches exceed existing Overture record count")
    if plan.conflicts:
        print("\nNo changes written because conflicts require review.")
        return 1
    if not apply:
        print("\nNo changes written. Re-run with --apply to update the database.")
        return 0
    if not plan.additions and not plan.corrections:
        print("\nNo changes needed.")
        return 0

    additions = [candidate.to_record() for candidate in plan.additions]
    replacements = _build_replacements(plan, database)
    records = _merge_maker_records(database, _MAKER, additions, replacements)
    _write_database(database_path, records)
    print(
        f"\nApplied {len(plan.additions)} additions and "
        f"{len(plan.corrections)} hex corrections to {database_path}"
    )
    print("Run tooling/update_hashes.py --autoupdate next.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Import approved Overture filament review data."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write reviewed changes; the default is a read-only dry run.",
    )
    parser.add_argument("--review", type=Path, default=_DEFAULT_REVIEW)
    parser.add_argument("--database", type=Path, default=_DEFAULT_DATABASE)
    return parser


def main() -> int:
    """Run the Overture import command."""
    args = _build_parser().parse_args()
    return _execute(args.review, args.database, apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())

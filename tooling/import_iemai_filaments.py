"""Import approved IEMAI filament records from the reconciled source files.

The command is a dry run unless ``--apply`` is supplied. Existing records are
never changed or deleted; source mismatches, identity conflicts, and ID
collisions prevent application.

Usage:
    python tooling/import_iemai_filaments.py
    python tooling/import_iemai_filaments.py --apply
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tooling._filament_import_utils import (
    _AdditiveImportPlan,
    _build_additive_import_plan,
    _load_database,
    _merge_maker_records,
    _write_database,
)
from tooling.preview_iemai_filaments import (
    _Candidate,
    _DEFAULT_CSV,
    _DEFAULT_TEXT,
    _build_preview,
    _read_csv,
    _read_grouped_text,
)

_DEFAULT_DATABASE = _ROOT / "color_tools" / "data" / "filaments.json"
_MAKER = "IEMAI"


def _load_candidates(csv_path: Path, grouped_text_path: Path) -> list[_Candidate]:
    """Load approved candidates after complete paired-source reconciliation."""
    preview = _build_preview(_read_csv(csv_path), _read_grouped_text(grouped_text_path))
    if preview.conflicts:
        details = "\n".join(f"- {conflict}" for conflict in preview.conflicts)
        raise ValueError(f"IEMAI source reconciliation failed:\n{details}")
    if len(preview.excluded) != 1:
        raise ValueError(
            "Expected exactly one approved exclusion (IEMAI PC Transparent); "
            f"found {len(preview.excluded)}"
        )
    if preview.alpha_inputs:
        raise ValueError("Unexpected alpha-bearing IEMAI import candidate")
    return preview.candidates


def _print_plan(plan: _AdditiveImportPlan[_Candidate], *, apply: bool) -> None:
    """Print every proposed IEMAI database action."""
    print("IEMAI filament import")
    print(f"Mode: {'APPLY' if apply else 'DRY RUN'}")
    print("Excluded: IEMAI PC Transparent (#00000000)")
    print()
    for candidate in plan.additions:
        finish = candidate.finish if candidate.finish is not None else "(none)"
        print(
            f"[ADD] {candidate.type_name} | {finish} | {candidate.color} "
            f"({candidate.hex_value}) [CSV row {candidate.source_row}]"
        )
    for candidate in plan.unchanged:
        finish = candidate.finish if candidate.finish is not None else "(none)"
        print(
            f"[UNCHANGED] {candidate.type_name} | {finish} | "
            f"{candidate.color} ({candidate.hex_value})"
        )
    for conflict in plan.conflicts:
        print(f"[CONFLICT] {conflict.candidate.record_id}: {conflict.reason}")
    print()
    print("Summary:")
    print(f"  Additions: {len(plan.additions)}")
    print(f"  Unchanged: {len(plan.unchanged)}")
    print(f"  Excluded: 1")
    print(f"  Conflicts: {len(plan.conflicts)}")


def _execute(
    csv_path: Path,
    grouped_text_path: Path,
    database_path: Path,
    *,
    apply: bool,
) -> int:
    """Plan, report, and optionally apply the IEMAI import."""
    candidates = _load_candidates(csv_path, grouped_text_path)
    database = _load_database(database_path)
    plan = _build_additive_import_plan(candidates, database)
    _print_plan(plan, apply=apply)

    if plan.conflicts:
        print("\nNo changes written because conflicts require review.")
        return 1
    if not apply:
        print("\nNo changes written. Re-run with --apply to update the database.")
        return 0
    if not plan.additions:
        print("\nNo changes needed.")
        return 0

    additions = [candidate.to_record() for candidate in plan.additions]
    records = _merge_maker_records(database, _MAKER, additions)
    _write_database(database_path, records)
    print(f"\nApplied {len(plan.additions)} additions to {database_path}")
    print("Run tooling/update_hashes.py --autoupdate next.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Import approved IEMAI filaments from reconciled source files."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the reviewed additions; the default is a read-only dry run.",
    )
    parser.add_argument("--csv", type=Path, default=_DEFAULT_CSV)
    parser.add_argument("--grouped-text", type=Path, default=_DEFAULT_TEXT)
    parser.add_argument("--database", type=Path, default=_DEFAULT_DATABASE)
    return parser


def main() -> int:
    """Run the IEMAI import command."""
    args = _build_parser().parse_args()
    return _execute(
        args.csv,
        args.grouped_text,
        args.database,
        apply=args.apply,
    )


if __name__ == "__main__":
    raise SystemExit(main())

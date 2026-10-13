"""Import missing Bambu Lab filaments from the approved PDF tables.

The command is a dry run unless ``--apply`` is supplied. Existing records are
never changed or deleted; identity or ID conflicts prevent application.

Usage:
    python tooling/import_bambu_filaments.py
    python tooling/import_bambu_filaments.py --apply
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
import re
import sys
from typing import Protocol, cast

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tooling._filament_import_utils import (
    _AdditiveImportPlan,
    _build_additive_import_plan,
    _filament_id,
    _identity,
    _load_database,
    _merge_maker_records,
    _normalize_hex,
    _write_database,
)


_DEFAULT_SOURCE_DIR = _ROOT / ".source_data"
_DEFAULT_DATABASE = _ROOT / "color_tools" / "data" / "filaments.json"
_MAKER = "Bambu Lab"


class _PdfPage(Protocol):
    def extract_text(self) -> str | None: ...


class _PdfReader(Protocol):
    pages: Sequence[_PdfPage]


@dataclass(frozen=True, slots=True)
class _SourceSpec:
    filename: str
    type_name: str
    finish: str
    product_label: str
    expected_count: int


@dataclass(frozen=True, slots=True)
class _Candidate:
    source: str
    type_name: str
    finish: str
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
        return self.source

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


_SOURCES = (
    _SourceSpec(
        "Bambu_PETG_Matte_Hex_Code_Table.pdf",
        "PETG",
        "Matte",
        "PETG Matte",
        8,
    ),
    _SourceSpec(
        "Bambu_PETG_Translucent_Hex_Code_Table.pdf",
        "PETG",
        "Translucent",
        "PETG Translucent",
        8,
    ),
    _SourceSpec(
        "Bambu_PLA_Tough_Hex_Code_Table.pdf",
        "PLA",
        "Tough+",
        "PLA Tough+",
        7,
    ),
)

_COLOR_PAIR = re.compile(
    r"(?m)^(?P<color>[^\r\n]+?)\s*\r?\nHex:\s*(?P<hex>#[^\s\r\n]+)\s*$",
    re.IGNORECASE,
)


def _extract_pdf_text(path: Path) -> str:
    """Extract text with the tooling-only pypdf dependency."""
    try:
        module = import_module("pypdf")
        reader_type = cast(type[_PdfReader], getattr(module, "PdfReader"))
    except (ImportError, AttributeError) as error:
        raise RuntimeError(
            "Bambu PDF import requires the tooling dependencies. "
            "Run: python -m pip install -r tooling/requirements.txt"
        ) from error

    reader = reader_type(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _parse_source_text(text: str, spec: _SourceSpec) -> list[_Candidate]:
    """Parse and validate one extracted Bambu table."""
    if spec.product_label.casefold() not in text.casefold():
        raise ValueError(
            f"{spec.filename}: expected product label {spec.product_label!r} not found"
        )

    candidates: list[_Candidate] = []
    for match in _COLOR_PAIR.finditer(text):
        color = " ".join(match.group("color").split())
        raw_hex = match.group("hex")
        try:
            hex_value = _normalize_hex(raw_hex)
        except ValueError as error:
            raise ValueError(
                f"{spec.filename}: invalid hex for {color!r}: {raw_hex!r}"
            ) from error
        candidates.append(
            _Candidate(spec.filename, spec.type_name, spec.finish, color, hex_value)
        )

    if len(candidates) != spec.expected_count:
        raise ValueError(
            f"{spec.filename}: extracted {len(candidates)} colors; "
            f"expected {spec.expected_count}"
        )
    return candidates


def _extract_sources(source_dir: Path) -> list[_Candidate]:
    """Extract all approved Bambu sources in deterministic order."""
    candidates: list[_Candidate] = []
    for spec in _SOURCES:
        path = source_dir / spec.filename
        if not path.is_file():
            raise FileNotFoundError(f"Required Bambu source not found: {path}")
        candidates.extend(_parse_source_text(_extract_pdf_text(path), spec))
    return candidates


def _build_plan(
    candidates: Sequence[_Candidate],
    database: Sequence[dict[str, object]],
) -> _AdditiveImportPlan[_Candidate]:
    """Compare source candidates with the database without changing either."""
    return _build_additive_import_plan(candidates, database)


def _print_plan(plan: _AdditiveImportPlan[_Candidate], *, apply: bool) -> None:
    """Print a complete, stable import report."""
    print("Bambu Lab filament import")
    print(f"Mode: {'APPLY' if apply else 'DRY RUN'}")
    print()
    for candidate in plan.additions:
        print(
            f"[ADD] {candidate.type_name} {candidate.finish} - "
            f"{candidate.color} ({candidate.hex_value}) [{candidate.source}]"
        )
    for candidate in plan.unchanged:
        print(
            f"[UNCHANGED] {candidate.type_name} {candidate.finish} - "
            f"{candidate.color} ({candidate.hex_value})"
        )
    for conflict in plan.conflicts:
        print(
            f"[CONFLICT] {conflict.candidate.type_name} "
            f"{conflict.candidate.finish} - {conflict.candidate.color}: "
            f"{conflict.reason}"
        )
    print()
    print("Summary:")
    print(f"  Additions: {len(plan.additions)}")
    print(f"  Unchanged: {len(plan.unchanged)}")
    print(f"  Conflicts: {len(plan.conflicts)}")


def _merged_database(
    database: Sequence[dict[str, object]],
    additions: Sequence[_Candidate],
) -> list[dict[str, object]]:
    """Insert additions into the existing contiguous Bambu Lab block."""
    new_records = [candidate.to_record() for candidate in additions]
    return _merge_maker_records(database, _MAKER, new_records)


def _execute(source_dir: Path, database_path: Path, *, apply: bool) -> int:
    """Plan, report, and optionally apply the Bambu import."""
    candidates = _extract_sources(source_dir)
    database = _load_database(database_path)
    plan = _build_plan(candidates, database)
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

    records = _merged_database(database, plan.additions)
    _write_database(database_path, records)
    print(f"\nApplied {len(plan.additions)} additions to {database_path}")
    print("Run tooling/update_hashes.py --autoupdate next.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Import missing Bambu Lab filaments from approved PDF tables."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the reviewed additions; the default is a read-only dry run.",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=_DEFAULT_SOURCE_DIR,
        help="Directory containing the approved Bambu PDF files.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=_DEFAULT_DATABASE,
        help="Filament database to inspect or update.",
    )
    return parser


def main() -> int:
    """Run the Bambu import command."""
    args = _build_parser().parse_args()
    return _execute(args.source_dir, args.database, apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())

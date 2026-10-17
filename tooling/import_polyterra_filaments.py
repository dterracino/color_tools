"""Import PolyTerra filaments from the Polymaker color and TD table.

The command is a dry run unless ``--apply`` is supplied. It imports only
PolyTerra products, collapses duplicate SKU rows, and excludes source rows
without a hex value. Existing records are never changed automatically.

Usage:
    python tooling/import_polyterra_filaments.py
    python tooling/import_polyterra_filaments.py --apply
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Sequence
import csv
from dataclasses import dataclass
import math
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tooling._filament_import_utils import (
    _AdditiveImportPlan,
    _ImportConflict,
    _build_additive_import_plan,
    _filament_id,
    _identity,
    _load_database,
    _merge_maker_records,
    _normalize_hex,
    _write_database,
)


_DEFAULT_SOURCE = _ROOT / ".source_data" / "Polymaker Hex and TD Info.csv"
_DEFAULT_DATABASE = _ROOT / "color_tools" / "data" / "filaments.json"
_MAKER = "Polymaker"
_FINISH = "PolyTerra"
_EXPECTED_SOURCE_ROWS = 98
_EXPECTED_CANDIDATES = 64
_EXPECTED_EXCLUSIONS = 9
_REQUIRED_COLUMNS = ("SKU", "Product Name", "Color Name", "HEX Code", "TD")
_PRODUCT_TYPES = {
    "PolyTerra PLA": "PLA",
    "PolyTerra PLA Marble": "PLA",
    "PolyTerra Gradient Matte PLA": "PLA",
    "PolyTerra PLA+": "PLA+",
}


@dataclass(frozen=True, slots=True)
class _Candidate:
    """One unique, importable PolyTerra filament identity."""

    product_name: str
    skus: tuple[str, ...]
    type_name: str
    color: str
    hex_value: str
    td_value: float | None

    @property
    def finish(self) -> str:
        """Return the catalog finish used for the PolyTerra product line."""
        return _FINISH

    @property
    def identity(self) -> tuple[str, str, str, str]:
        """Return the normalized database identity."""
        return _identity(_MAKER, self.type_name, self.finish, self.color)

    @property
    def record_id(self) -> str:
        """Return the canonical filament ID."""
        return _filament_id(_MAKER, self.type_name, self.finish, self.color)

    @property
    def source_description(self) -> str:
        """Describe all source SKUs represented by this candidate."""
        return f"{self.product_name}: {', '.join(self.skus)}"

    def to_record(self) -> dict[str, object]:
        """Build the database record for this candidate."""
        return {
            "id": self.record_id,
            "maker": _MAKER,
            "type": self.type_name,
            "finish": self.finish,
            "color": self.color,
            "hex": self.hex_value,
            "td_value": self.td_value,
        }


@dataclass(frozen=True, slots=True)
class _Exclusion:
    """One PolyTerra row excluded because it lacks color data."""

    sku: str
    product_name: str
    color: str
    reason: str


@dataclass(frozen=True, slots=True)
class _SourceResult:
    """Validated and deduplicated PolyTerra source data."""

    source_rows: int
    duplicate_rows: int
    candidates: tuple[_Candidate, ...]
    exclusions: tuple[_Exclusion, ...]


def _clean_text(value: str) -> str:
    """Normalize source whitespace without changing source wording."""
    return " ".join(value.split())


def _normalize_color(value: str) -> str:
    """Return the spool-label color without PolyTerra's redundant style prefix."""
    color = _clean_text(value)
    return color.removeprefix("Matte ")


def _parse_td(value: str, *, sku: str) -> float | None:
    """Parse an optional positive HueForge transmission-distance value."""
    text = value.strip()
    if not text:
        return None
    try:
        td_value = float(text)
    except ValueError as error:
        raise ValueError(f"{sku}: invalid TD value {value!r}") from error
    if not math.isfinite(td_value) or td_value <= 0:
        raise ValueError(f"{sku}: TD must be a finite positive number")
    return td_value


def _merge_candidate(previous: _Candidate, current: _Candidate) -> _Candidate:
    """Combine duplicate SKU rows or reject conflicting source data."""
    if previous.hex_value != current.hex_value:
        raise ValueError(
            f"{current.source_description}: duplicate identity has conflicting hex "
            f"values {previous.hex_value} and {current.hex_value}"
        )
    if (
        previous.td_value is not None
        and current.td_value is not None
        and previous.td_value != current.td_value
    ):
        raise ValueError(
            f"{current.source_description}: duplicate identity has conflicting TD "
            f"values {previous.td_value} and {current.td_value}"
        )
    return _Candidate(
        previous.product_name,
        previous.skus + current.skus,
        previous.type_name,
        previous.color,
        previous.hex_value,
        previous.td_value if previous.td_value is not None else current.td_value,
    )


def _parse_rows(rows: Iterable[dict[str, str]]) -> _SourceResult:
    """Select, validate, and deduplicate PolyTerra source rows."""
    candidates_by_identity: dict[tuple[str, str, str, str], _Candidate] = {}
    exclusions: list[_Exclusion] = []
    source_rows = 0
    importable_rows = 0

    for row_number, row in enumerate(rows, start=2):
        product_name = _clean_text(row.get("Product Name", ""))
        if not product_name.startswith("PolyTerra"):
            continue
        source_rows += 1
        sku = _clean_text(row.get("SKU", ""))
        color = _normalize_color(row.get("Color Name", ""))
        if not sku or not color:
            raise ValueError(f"CSV row {row_number}: PolyTerra SKU and color are required")
        type_name = _PRODUCT_TYPES.get(product_name)
        if type_name is None:
            raise ValueError(
                f"CSV row {row_number}: unsupported PolyTerra product {product_name!r}"
            )

        raw_hex = row.get("HEX Code", "").strip()
        if not raw_hex:
            exclusions.append(
                _Exclusion(sku, product_name, color, "source row has no hex value")
            )
            continue
        try:
            hex_value = _normalize_hex(raw_hex)
        except ValueError as error:
            raise ValueError(
                f"CSV row {row_number}: invalid hex for {sku} {color!r}: {raw_hex!r}"
            ) from error

        importable_rows += 1
        candidate = _Candidate(
            product_name,
            (sku,),
            type_name,
            color,
            hex_value,
            _parse_td(row.get("TD", ""), sku=sku),
        )
        previous = candidates_by_identity.get(candidate.identity)
        candidates_by_identity[candidate.identity] = (
            candidate if previous is None else _merge_candidate(previous, candidate)
        )

    return _SourceResult(
        source_rows,
        importable_rows - len(candidates_by_identity),
        tuple(candidates_by_identity.values()),
        tuple(exclusions),
    )


def _load_source(path: Path) -> _SourceResult:
    """Load the approved CSV and enforce its expected PolyTerra shape."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(_REQUIRED_COLUMNS):
            raise ValueError(
                f"{path}: expected columns {list(_REQUIRED_COLUMNS)!r}; "
                f"found {reader.fieldnames!r}"
            )
        result = _parse_rows(reader)

    if result.source_rows != _EXPECTED_SOURCE_ROWS:
        raise ValueError(
            f"{path}: found {result.source_rows} PolyTerra rows; "
            f"expected {_EXPECTED_SOURCE_ROWS}"
        )
    if len(result.candidates) != _EXPECTED_CANDIDATES:
        raise ValueError(
            f"{path}: produced {len(result.candidates)} unique candidates; "
            f"expected {_EXPECTED_CANDIDATES}"
        )
    if len(result.exclusions) != _EXPECTED_EXCLUSIONS:
        raise ValueError(
            f"{path}: excluded {len(result.exclusions)} rows; "
            f"expected {_EXPECTED_EXCLUSIONS}"
        )
    return result


def _database_td(record: dict[str, object]) -> float | None:
    """Read and validate an existing database TD value."""
    value = record.get("td_value")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Database record has invalid 'td_value': {value!r}")
    return float(value)


def _build_plan(
    candidates: Sequence[_Candidate],
    database: Sequence[dict[str, object]],
) -> _AdditiveImportPlan[_Candidate]:
    """Build an additive plan that also guards existing TD values."""
    plan = _build_additive_import_plan(candidates, database)
    existing_by_id = {
        record_id: record
        for record in database
        if isinstance((record_id := record.get("id")), str)
    }
    unchanged: list[_Candidate] = []
    for candidate in plan.unchanged:
        existing = existing_by_id.get(candidate.record_id)
        if existing is None:
            plan.conflicts.append(
                _ImportConflict(candidate, "matching identity uses a different record ID")
            )
            continue
        existing_td = _database_td(existing)
        if existing_td != candidate.td_value:
            plan.conflicts.append(
                _ImportConflict(
                    candidate,
                    f"existing {candidate.record_id} has TD {existing_td!r}, "
                    f"source has {candidate.td_value!r}",
                )
            )
            continue
        unchanged.append(candidate)
    plan.unchanged = unchanged
    return plan


def _print_plan(
    source: _SourceResult,
    plan: _AdditiveImportPlan[_Candidate],
    *,
    apply: bool,
) -> None:
    """Print exclusions and every proposed database action."""
    print("Polymaker PolyTerra filament import")
    print(f"Mode: {'APPLY' if apply else 'DRY RUN'}")
    print()
    for exclusion in source.exclusions:
        print(
            f"[EXCLUDED] {exclusion.sku} | {exclusion.product_name} | "
            f"{exclusion.color}: {exclusion.reason}"
        )
    for candidate in plan.additions:
        td_text = "none" if candidate.td_value is None else str(candidate.td_value)
        print(
            f"[ADD] {candidate.type_name} | {candidate.finish} | "
            f"{candidate.color} ({candidate.hex_value}, TD {td_text}) "
            f"[{', '.join(candidate.skus)}]"
        )
    for candidate in plan.unchanged:
        print(f"[UNCHANGED] {candidate.record_id}")
    for conflict in plan.conflicts:
        print(f"[CONFLICT] {conflict.candidate.record_id}: {conflict.reason}")
    print()
    print("Summary:")
    print(f"  PolyTerra source rows: {source.source_rows}")
    print(f"  Duplicate SKU rows collapsed: {source.duplicate_rows}")
    print(f"  Additions: {len(plan.additions)}")
    print(f"  Unchanged: {len(plan.unchanged)}")
    print(f"  Excluded without hex: {len(source.exclusions)}")
    print(f"  Conflicts: {len(plan.conflicts)}")


def _execute(source_path: Path, database_path: Path, *, apply: bool) -> int:
    """Plan, report, and optionally apply the PolyTerra import."""
    source = _load_source(source_path)
    database = _load_database(database_path)
    plan = _build_plan(source.candidates, database)
    _print_plan(source, plan, apply=apply)

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
        description="Import PolyTerra filaments from the Polymaker color and TD CSV."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the reviewed additions; the default is a read-only dry run.",
    )
    parser.add_argument("--source", type=Path, default=_DEFAULT_SOURCE)
    parser.add_argument("--database", type=Path, default=_DEFAULT_DATABASE)
    return parser


def main() -> int:
    """Run the PolyTerra import command."""
    args = _build_parser().parse_args()
    return _execute(args.source, args.database, apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())

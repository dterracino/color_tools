"""Convert the hand-reviewed Overture extraction to database-shaped columns.

The reviewed extraction remains untouched. This script writes a separate file
with explicit maker, type, finish, color, canonical hex, and TD columns.

Usage:
    python tooling/prepare_overture_import_review.py
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

from tooling._filament_import_utils import _identity, _normalize_hex

_DEFAULT_INPUT = _ROOT / ".source_data" / "overture_filaments_review.txt"
_DEFAULT_OUTPUT = (
    _ROOT / ".source_data" / "overture_filaments_import_review.txt"
)
_EXPECTED_ROWS = 300
_EXPECTED_OMITTED = 44
_MAKER = "Overture"
_NULL = "null"

# Only appearance variants become finishes. Product grades and functional
# formulations remain distinct filament types.
_PRODUCT_MAPPING: dict[str, tuple[str, str | None]] = {
    "PLA": ("PLA", None),
    "Matte PLA": ("PLA", "Matte"),
    "Rock PLA": ("PLA", "Rock"),
    "PLA Professional": ("PLA Professional", None),
    "Super PLA+": ("Super PLA+", None),
    "Easy PLA": ("Easy PLA", None),
    "Silk PLA": ("PLA", "Silk"),
    "Air PLA": ("Air PLA", None),
    "PETG": ("PETG", None),
    "TPU": ("TPU", None),
    "High Speed TPU": ("High Speed TPU", None),
    "ABS": ("ABS", None),
    "ASA": ("ASA", None),
    "Easy Nylon": ("Easy Nylon", None),
    "PC Professional": ("PC Professional", None),
}


@dataclass(frozen=True, slots=True)
class _ReviewedRow:
    page: int
    product: str
    color: str
    hex_value: str
    status: str


@dataclass(frozen=True, slots=True)
class _OmittedRow:
    page: int
    product: str
    color: str
    source_value: str


@dataclass(frozen=True, slots=True)
class _PreparedRow:
    page: int
    type_name: str
    finish: str | None
    color: str
    hex_value: str
    status: str

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return _identity(_MAKER, self.type_name, self.finish, self.color)


@dataclass(frozen=True, slots=True)
class _PreparedOmission:
    page: int
    type_name: str
    finish: str | None
    color: str
    source_value: str


def _parse_review(path: Path) -> tuple[list[_ReviewedRow], list[_OmittedRow]]:
    """Read and validate the hand-reviewed positioned extraction."""
    rows: list[_ReviewedRow] = []
    omitted: list[_OmittedRow] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# OMITTED_NO_HEX | "):
            fields = [field.strip() for field in line.split(" | ")]
            if len(fields) != 5:
                raise ValueError(f"{path}:{line_number}: invalid omission row")
            omitted.append(
                _OmittedRow(int(fields[1]), fields[2], fields[3], fields[4])
            )
            continue
        if not line[0].isdigit():
            continue
        fields = [field.strip() for field in line.split(" | ")]
        if len(fields) != 5:
            raise ValueError(f"{path}:{line_number}: expected 5 fields")
        row = _ReviewedRow(int(fields[0]), fields[1], fields[2], fields[3], fields[4])
        if row.status != "OK":
            raise ValueError(
                f"{path}:{line_number}: unresolved status {row.status!r}"
            )
        rows.append(row)

    if len(rows) != _EXPECTED_ROWS:
        raise ValueError(f"{path}: expected {_EXPECTED_ROWS} rows; found {len(rows)}")
    if len(omitted) != _EXPECTED_OMITTED:
        raise ValueError(
            f"{path}: expected {_EXPECTED_OMITTED} omissions; found {len(omitted)}"
        )
    return rows, omitted


def _map_product(product: str) -> tuple[str, str | None]:
    """Map one reviewed PDF product heading to type and finish."""
    try:
        return _PRODUCT_MAPPING[product]
    except KeyError as error:
        raise ValueError(f"Unmapped Overture product: {product!r}") from error


def _prepare_rows(rows: Sequence[_ReviewedRow]) -> list[_PreparedRow]:
    """Create validated, database-shaped candidate rows."""
    prepared: list[_PreparedRow] = []
    identities: set[tuple[str, str, str, str]] = set()
    for row in rows:
        type_name, finish = _map_product(row.product)
        candidate = _PreparedRow(
            row.page,
            type_name,
            finish,
            row.color,
            _normalize_hex(row.hex_value),
            row.status,
        )
        if candidate.identity in identities:
            raise ValueError(
                "Product mapping creates duplicate identity: "
                f"{type_name!r}, {finish!r}, {row.color!r}"
            )
        identities.add(candidate.identity)
        prepared.append(candidate)
    return prepared


def _prepare_omissions(
    rows: Sequence[_OmittedRow],
) -> list[_PreparedOmission]:
    """Map audit-only no-hex entries to the same type/finish taxonomy."""
    prepared: list[_PreparedOmission] = []
    for row in rows:
        type_name, finish = _map_product(row.product)
        prepared.append(
            _PreparedOmission(
                row.page,
                type_name,
                finish,
                row.color,
                row.source_value,
            )
        )
    return prepared


def _render_review(
    rows: Sequence[_PreparedRow], omissions: Sequence[_PreparedOmission]
) -> str:
    """Render the schema-shaped review file deterministically."""
    lines = [
        "# Overture filament import review - DATABASE COLUMNS",
        "# Derived from the hand-reviewed overture_filaments_review.txt file.",
        f"# Import candidates: {len(rows)}",
        f"# Omitted no-hex rows: {len(omissions)}",
        "# Maker is Overture; finish and td_value use JSON-style null.",
        "# Columns: page | maker | type | finish | color | hex | td_value | status",
        "page | maker | type | finish | color | hex | td_value | status",
    ]
    for row in rows:
        finish = row.finish if row.finish is not None else _NULL
        lines.append(
            f"{row.page} | {_MAKER} | {row.type_name} | {finish} | "
            f"{row.color} | {row.hex_value} | {_NULL} | {row.status}"
        )

    lines.extend(
        (
            "",
            "# Omitted entries without explicit hex values (not import candidates)",
            "# page | maker | type | finish | color | source value",
        )
    )
    for row in omissions:
        finish = row.finish if row.finish is not None else _NULL
        lines.append(
            f"# OMITTED_NO_HEX | {row.page} | {_MAKER} | {row.type_name} | "
            f"{finish} | {row.color} | {row.source_value}"
        )
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Prepare reviewed Overture rows for database import."
    )
    parser.add_argument("--input", type=Path, default=_DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    return parser


def main() -> int:
    """Write the database-shaped Overture review file."""
    args = _build_parser().parse_args()
    reviewed, omitted = _parse_review(args.input)
    prepared = _prepare_rows(reviewed)
    prepared_omissions = _prepare_omissions(omitted)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        _render_review(prepared, prepared_omissions),
        encoding="utf-8",
        newline="\n",
    )
    finish_count = sum(row.finish is not None for row in prepared)
    print("Overture import review preparation")
    print(f"Reviewed input: {args.input}")
    print(f"Prepared output: {args.output}")
    print(f"Import candidates: {len(prepared)}")
    print(f"Rows with a finish: {finish_count}")
    print(f"Omitted no-hex rows: {len(prepared_omissions)}")
    print("No filament database changes were made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

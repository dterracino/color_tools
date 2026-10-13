"""Preview normalized IEMAI filament records without writing any files.

The CSV is the machine-readable source. The grouped text copy is reconciled
against it so omissions or transcription drift are reported before import.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
import csv
from dataclasses import dataclass, field
from pathlib import Path
import re
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tooling._filament_import_utils import _filament_id, _identity, _normalize_hex

_DEFAULT_CSV = _ROOT / ".source_data" / "iemai_filament_colors.csv"
_DEFAULT_TEXT = _ROOT / ".source_data" / "iemai_filament_colors_by_material.txt"
_EXPECTED_HEADERS = (
    "Manufacturer",
    "Material",
    "Color Name",
    "HEX",
    "Confidence",
    "Source URL",
)
_EXPECTED_ROWS = 188
_COMPOUND_TYPE_QUALIFIERS = frozenset({"CF", "GF"})
_EXCLUDED_PC_TRANSPARENT = (
    "PC — Basic",
    "IEMAI PC Transparent",
    "#00000000",
)
_HEX_COMPONENT = re.compile(r"#?[0-9A-Fa-f]{3,8}")


@dataclass(frozen=True, slots=True)
class _SourceRow:
    manufacturer: str
    material: str
    color: str
    hex_value: str
    confidence: str
    source_url: str
    source_row: int

    @property
    def comparison_key(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.manufacturer,
            self.material,
            self.color,
            self.hex_value,
            self.confidence,
            self.source_url,
        )


@dataclass(frozen=True, slots=True)
class _Candidate:
    type_name: str
    finish: str | None
    color: str
    hex_value: str
    source_hex: str
    confidence: str
    source_url: str
    source_row: int

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return _identity("IEMAI", self.type_name, self.finish, self.color)

    @property
    def record_id(self) -> str:
        return _filament_id("IEMAI", self.type_name, self.finish, self.color)

    @property
    def source_description(self) -> str:
        return f"CSV row {self.source_row}"

    @property
    def component_count(self) -> int:
        return self.hex_value.count("-") + 1

    def to_record(self) -> dict[str, object]:
        """Return the bundled-database representation."""
        return {
            "id": self.record_id,
            "maker": "IEMAI",
            "type": self.type_name,
            "finish": self.finish,
            "color": self.color,
            "hex": self.hex_value,
            "td_value": None,
        }


@dataclass(slots=True)
class _Preview:
    candidates: list[_Candidate] = field(default_factory=list)
    promoted: list[_Candidate] = field(default_factory=list)
    excluded: list[_SourceRow] = field(default_factory=list)
    alpha_inputs: list[_Candidate] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


def _required(row: dict[str, str | None], field_name: str, row_number: int) -> str:
    """Read and trim one required CSV field."""
    value = row.get(field_name)
    if value is None or not value.strip():
        raise ValueError(f"CSV row {row_number}: missing {field_name!r}")
    return value.strip()


def _read_csv(path: Path) -> list[_SourceRow]:
    """Read and structurally validate the IEMAI CSV."""
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != _EXPECTED_HEADERS:
            raise ValueError(
                f"{path}: expected headers {_EXPECTED_HEADERS}; found {reader.fieldnames}"
            )
        rows = [
            _SourceRow(
                _required(row, "Manufacturer", row_number),
                _required(row, "Material", row_number),
                _required(row, "Color Name", row_number),
                _required(row, "HEX", row_number),
                _required(row, "Confidence", row_number),
                _required(row, "Source URL", row_number),
                row_number,
            )
            for row_number, row in enumerate(reader, start=2)
        ]
    if len(rows) != _EXPECTED_ROWS:
        raise ValueError(f"{path}: expected {_EXPECTED_ROWS} rows; found {len(rows)}")
    return rows


def _read_grouped_text(path: Path) -> list[_SourceRow]:
    """Read the human-oriented material-grouped copy for reconciliation."""
    rows: list[_SourceRow] = []
    material: str | None = None
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        if not raw_line.strip() or raw_line.startswith("IEMAI FILAMENT"):
            continue
        if raw_line.startswith("No manufacturer") or raw_line.startswith("marked "):
            continue
        if not raw_line.startswith("  "):
            material = raw_line.strip()
            continue
        if material is None:
            raise ValueError(f"{path}: row before material heading at line {line_number}")
        fields = [field.strip() for field in raw_line.strip().split(" | ")]
        if len(fields) != 5:
            raise ValueError(f"{path}: expected 5 fields at line {line_number}")
        qualifier, color, hex_value, confidence, source_url = fields
        rows.append(
            _SourceRow(
                "IEMAI",
                f"{material} — {qualifier}",
                color,
                hex_value,
                confidence,
                source_url,
                line_number,
            )
        )
    return rows


def _reconcile_sources(csv_rows: Sequence[_SourceRow], text_rows: Sequence[_SourceRow]) -> list[str]:
    """Return every count difference between the paired source presentations."""
    csv_counts = Counter(row.comparison_key for row in csv_rows)
    text_counts = Counter(row.comparison_key for row in text_rows)
    differences: list[str] = []
    for key in sorted(csv_counts.keys() | text_counts.keys()):
        csv_count = csv_counts[key]
        text_count = text_counts[key]
        if csv_count != text_count:
            differences.append(
                f"source mismatch {key!r}: CSV={csv_count}, grouped text={text_count}"
            )
    return differences


def _split_material(value: str) -> tuple[str, str | None]:
    """Split the parent material and source qualifier."""
    parts = [part.strip() for part in value.split(" — ")]
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"invalid material/product-line value: {value!r}")
    parent_type, qualifier = parts
    if qualifier in _COMPOUND_TYPE_QUALIFIERS:
        return f"{parent_type}-{qualifier}", None
    return parent_type, qualifier


def _contains_alpha_hex(value: str) -> bool:
    """Return whether any source component includes an alpha channel."""
    return any(len(token.removeprefix("#")) in {4, 8} for token in _HEX_COMPONENT.findall(value))


def _is_excluded_row(row: _SourceRow) -> bool:
    """Return whether a source row is deliberately omitted from import."""
    return (row.material, row.color, row.hex_value) == _EXCLUDED_PC_TRANSPARENT


def _normalize_row(row: _SourceRow) -> _Candidate:
    """Normalize one source row into the proposed database representation."""
    if row.manufacturer != "IEMAI":
        raise ValueError(
            f"CSV row {row.source_row}: expected manufacturer 'IEMAI'; "
            f"found {row.manufacturer!r}"
        )
    type_name, finish = _split_material(row.material)
    hex_value = _normalize_hex(row.hex_value)
    return _Candidate(
        type_name,
        finish,
        " ".join(row.color.split()),
        hex_value,
        row.hex_value,
        row.confidence,
        row.source_url,
        row.source_row,
    )


def _build_preview(
    csv_rows: Sequence[_SourceRow], text_rows: Sequence[_SourceRow]
) -> _Preview:
    """Normalize all rows and collect review warnings without writing."""
    preview = _Preview(conflicts=_reconcile_sources(csv_rows, text_rows))
    seen: dict[tuple[str, str, str, str], _Candidate] = {}
    for row in csv_rows:
        if _is_excluded_row(row):
            preview.excluded.append(row)
            continue
        candidate = _normalize_row(row)
        previous = seen.get(candidate.identity)
        if previous is not None:
            preview.conflicts.append(
                f"duplicate identity {candidate.record_id}: CSV rows "
                f"{previous.source_row} and {candidate.source_row}"
            )
        else:
            seen[candidate.identity] = candidate
        preview.candidates.append(candidate)
        qualifier = row.material.rsplit(" — ", maxsplit=1)[-1]
        if qualifier in _COMPOUND_TYPE_QUALIFIERS:
            preview.promoted.append(candidate)
        if _contains_alpha_hex(candidate.source_hex):
            preview.alpha_inputs.append(candidate)
    return preview


def _print_preview(preview: _Preview) -> None:
    """Print every normalized record followed by reconciliation summaries."""
    print("IEMAI filament normalization preview")
    print("Mode: CONSOLE PREVIEW ONLY (no files are written)\n")
    for row in preview.excluded:
        material = row.material.replace(" — ", " - ")
        print(
            f"[ROW {row.source_row:03}] EXCLUDED | material={material} | "
            f"color={row.color} | hex={row.hex_value} | "
            "reason=transparent alpha color is not representable"
        )
    for candidate in preview.candidates:
        finish = candidate.finish if candidate.finish is not None else "(none)"
        suffix = " [ALPHA DROPPED]" if candidate in preview.alpha_inputs else ""
        confidence = candidate.confidence.replace(" — ", " - ")
        print(
            f"[ROW {candidate.source_row:03}] id={candidate.record_id} | "
            f"type={candidate.type_name} | finish={finish} | "
            f"color={candidate.color} | hex={candidate.hex_value}{suffix} | "
            f"confidence={confidence} | source={candidate.source_url}"
        )
    print("\nSummary:")
    print(f"  Source rows: {len(preview.candidates) + len(preview.excluded)}")
    print(f"  Import candidates: {len(preview.candidates)}")
    print(f"  Explicitly excluded rows: {len(preview.excluded)}")
    print(f"  CF/GF qualifiers promoted to types: {len(preview.promoted)}")
    print(
        "  Multi-color rows: "
        f"{sum(candidate.component_count > 1 for candidate in preview.candidates)}"
    )
    print(f"  Alpha-bearing inputs: {len(preview.alpha_inputs)}")
    print(f"  Conflicts/source mismatches: {len(preview.conflicts)}")
    type_counts = Counter(candidate.type_name for candidate in preview.candidates)
    print("\nCounts by normalized type:")
    for type_name, count in sorted(type_counts.items()):
        print(f"  {type_name}: {count}")
    if preview.conflicts:
        print("\nConflicts/source mismatches:")
        for conflict in preview.conflicts:
            print(f"  [CONFLICT] {conflict}")


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Preview normalized IEMAI filament data without writing files."
    )
    parser.add_argument("--csv", type=Path, default=_DEFAULT_CSV)
    parser.add_argument("--grouped-text", type=Path, default=_DEFAULT_TEXT)
    return parser


def main() -> int:
    """Run the console-only IEMAI normalization preview."""
    args = _build_parser().parse_args()
    preview = _build_preview(_read_csv(args.csv), _read_grouped_text(args.grouped_text))
    _print_preview(preview)
    return 1 if preview.conflicts else 0


if __name__ == "__main__":
    raise SystemExit(main())

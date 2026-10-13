"""Extract Overture's positioned PDF data into an editable review file.

This script never modifies the filament database. It pairs product names and
values by page coordinates, writes every explicit hex row in visual reading
order, and records no-hex entries as omitted audit comments.

Usage:
    python tooling/extract_overture_pdf.py
    python tooling/extract_overture_pdf.py --output path/to/review.txt
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
import re
import sys
from typing import Protocol, cast

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_PDF = _ROOT / ".source_data" / "Overture_Hex_Code_List.pdf"
_DEFAULT_OUTPUT = _ROOT / ".source_data" / "overture_filaments_review.txt"
_HEX_TOKEN = re.compile(r"#[0-9A-Fa-f]+")
_VALID_HEX_LENGTHS = frozenset({3, 4, 6, 8})
_COLUMN_BOUNDARY = 330.0
_ITEM_X_MINIMUM = 150.0


class _PdfPage(Protocol):
    def extract_text(
        self,
        *,
        visitor_text: Callable[
            [str, Sequence[float], Sequence[float], object, float], None
        ],
    ) -> str: ...


class _PdfReader(Protocol):
    pages: Sequence[_PdfPage]


@dataclass(frozen=True, slots=True)
class _SectionSpec:
    page: int
    product: str
    minimum_y: float
    maximum_y: float


@dataclass(frozen=True, slots=True)
class _Fragment:
    page: int
    x: float
    y: float
    text: str


@dataclass(frozen=True, slots=True)
class _ExtractedRow:
    page: int
    product: str
    color: str
    hex_value: str
    status: str
    y: float
    x: float


@dataclass(frozen=True, slots=True)
class _OmittedRow:
    page: int
    product: str
    color: str
    source_value: str


@dataclass(frozen=True, slots=True)
class _Extraction:
    rows: list[_ExtractedRow]
    omitted: list[_OmittedRow]


_SECTIONS = (
    _SectionSpec(3, "PLA", 55.0, 728.2),
    _SectionSpec(4, "PLA", 398.9, 728.2),
    _SectionSpec(4, "Matte PLA", 55.0, 398.9),
    _SectionSpec(5, "Matte PLA", 55.0, 728.2),
    _SectionSpec(6, "Rock PLA", 55.0, 728.2),
    _SectionSpec(7, "PLA Professional", 55.0, 735.0),
    _SectionSpec(8, "Super PLA+", 379.3, 728.2),
    _SectionSpec(8, "Easy PLA", 55.0, 379.3),
    _SectionSpec(9, "Easy PLA", 55.0, 728.0),
    _SectionSpec(10, "Silk PLA", 55.0, 728.4),
    _SectionSpec(11, "Silk PLA", 424.5, 728.4),
    _SectionSpec(11, "Air PLA", 55.0, 424.5),
    _SectionSpec(12, "PETG", 55.0, 654.0),
    _SectionSpec(13, "TPU", 55.0, 728.7),
    _SectionSpec(14, "High Speed TPU", 55.0, 728.7),
    _SectionSpec(15, "ABS", 55.0, 669.0),
    _SectionSpec(16, "ASA", 234.3, 672.2),
    _SectionSpec(16, "Easy Nylon", 55.0, 234.3),
    _SectionSpec(17, "PC Professional", 500.0, 665.1),
)

# The PDF text layer fuses these visually separate columns into one fragment.
# Replacements were verified against the positioned layout extraction.
_FUSED_FRAGMENT_REPLACEMENTS: dict[
    tuple[int, str], tuple[tuple[float, str], ...]
] = {
    (8, "Easy Digital BlueEasy Cement Grey"): (
        (191.3, "Easy Cement Grey"),
        (432.3, "Easy Digital Blue"),
    ),
    (8, "#0696EF#697272"): ((191.3, "#697272"), (432.3, "#0696EF")),
    (11, "Air Neon GreenAir White"): (
        (191.3, "Air White"),
        (432.2, "Air Neon Green"),
    ),
    (11, "#C0D904#EDD5B7"): ((191.3, "#EDD5B7"), (432.2, "#C0D904")),
    (14, "Gray Grass Green"): ((191.3, "Gray"), (432.2, "Grass Green")),
    (14, "#CDCFD5 #B1FF0A"): ((191.3, "#CDCFD5"), (432.2, "#B1FF0A")),
    (16, "Orange Purple"): ((190.8, "Orange"), (431.9, "Purple")),
    (16, "#FF9A40 #7959B6"): ((190.8, "#FF9A40"), (431.9, "#7959B6")),
}


def _load_pages(path: Path) -> list[list[_Fragment]]:
    """Read positioned text fragments from every PDF page."""
    try:
        module = import_module("pypdf")
        reader_type = cast(type[_PdfReader], getattr(module, "PdfReader"))
    except (ImportError, AttributeError) as error:
        raise RuntimeError(
            "Overture extraction requires the tooling dependencies. "
            "Run: python -m pip install -r tooling/requirements.txt"
        ) from error

    reader = reader_type(path)
    if len(reader.pages) != 17:
        raise ValueError(f"{path}: expected 17 pages; found {len(reader.pages)}")

    pages: list[list[_Fragment]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        fragments: list[_Fragment] = []

        def _visit_text(
            text: str,
            _current_matrix: Sequence[float],
            text_matrix: Sequence[float],
            _font: object,
            _font_size: float,
        ) -> None:
            clean_text = text.strip()
            if clean_text:
                fragments.append(
                    _Fragment(
                        page_number,
                        float(text_matrix[4]),
                        float(text_matrix[5]),
                        clean_text,
                    )
                )

        page.extract_text(visitor_text=_visit_text)
        pages.append(_apply_fused_fragment_replacements(page_number, fragments))
    return pages


def _apply_fused_fragment_replacements(
    page_number: int, fragments: Sequence[_Fragment]
) -> list[_Fragment]:
    """Split the PDF's known fused two-column text fragments."""
    corrected: list[_Fragment] = []
    matched: set[tuple[int, str]] = set()
    for fragment in fragments:
        key = (page_number, fragment.text)
        replacements = _FUSED_FRAGMENT_REPLACEMENTS.get(key)
        if replacements is None:
            corrected.append(fragment)
            continue
        matched.add(key)
        corrected.extend(
            _Fragment(page_number, x, fragment.y, text)
            for x, text in replacements
        )

    expected = {
        key for key in _FUSED_FRAGMENT_REPLACEMENTS if key[0] == page_number
    }
    if matched != expected:
        missing = sorted(text for _, text in expected - matched)
        raise ValueError(
            f"PDF page {page_number}: expected fused fragments not found: {missing}"
        )
    return corrected


def _section_fragments(
    pages: Sequence[Sequence[_Fragment]], spec: _SectionSpec
) -> list[_Fragment]:
    """Select positioned item fragments for one product section."""
    return [
        fragment
        for fragment in pages[spec.page - 1]
        if fragment.x >= _ITEM_X_MINIMUM
        and spec.minimum_y < fragment.y < spec.maximum_y
    ]


def _pair_column(
    fragments: Sequence[_Fragment], spec: _SectionSpec
) -> list[tuple[_Fragment, _Fragment]]:
    """Pair alternating color/value fragments within one visual column."""
    ordered = sorted(fragments, key=lambda fragment: -fragment.y)
    if len(ordered) % 2:
        details = [(fragment.text, fragment.x, fragment.y) for fragment in ordered]
        raise ValueError(
            f"PDF page {spec.page} {spec.product}: odd fragment count: {details}"
        )

    pairs: list[tuple[_Fragment, _Fragment]] = []
    for index in range(0, len(ordered), 2):
        name = ordered[index]
        value = ordered[index + 1]
        if name.text.startswith("#") or name.text == "/":
            raise ValueError(
                f"PDF page {spec.page} {spec.product}: expected color name, "
                f"found {name.text!r}"
            )
        if name.y <= value.y:
            raise ValueError(
                f"PDF page {spec.page} {spec.product}: value is not below "
                f"{name.text!r}"
            )
        pairs.append((name, value))
    return pairs


def _visual_pair_order(
    pairs: Sequence[tuple[_Fragment, _Fragment]],
) -> list[tuple[_Fragment, _Fragment]]:
    """Order pairs by visual row, then from the left column to the right."""
    by_height = sorted(pairs, key=lambda pair: -pair[0].y)
    rows: list[list[tuple[_Fragment, _Fragment]]] = []
    for pair in by_height:
        if not rows or abs(rows[-1][0][0].y - pair[0].y) > 5.0:
            rows.append([pair])
        else:
            rows[-1].append(pair)
    return [pair for row in rows for pair in sorted(row, key=lambda item: item[0].x)]


def _extract_section(
    pages: Sequence[Sequence[_Fragment]], spec: _SectionSpec
) -> _Extraction:
    """Extract one product section in visual row order."""
    fragments = _section_fragments(pages, spec)
    left = [fragment for fragment in fragments if fragment.x < _COLUMN_BOUNDARY]
    right = [fragment for fragment in fragments if fragment.x >= _COLUMN_BOUNDARY]
    pairs = _visual_pair_order(_pair_column(left, spec) + _pair_column(right, spec))

    rows: list[_ExtractedRow] = []
    omitted: list[_OmittedRow] = []
    for name, value in pairs:
        tokens = _HEX_TOKEN.findall(value.text)
        if not tokens:
            omitted.append(
                _OmittedRow(spec.page, spec.product, name.text, value.text)
            )
            continue
        invalid = [
            token
            for token in tokens
            if len(token.removeprefix("#")) not in _VALID_HEX_LENGTHS
        ]
        status = "REVIEW_INVALID_HEX" if invalid else "OK"
        rows.append(
            _ExtractedRow(
                spec.page,
                spec.product,
                name.text,
                " / ".join(tokens),
                status,
                name.y,
                name.x,
            )
        )
    return _Extraction(rows, omitted)


def _extract(path: Path) -> _Extraction:
    """Extract all configured product sections from the Overture PDF."""
    pages = _load_pages(path)
    rows: list[_ExtractedRow] = []
    omitted: list[_OmittedRow] = []
    for spec in _SECTIONS:
        extraction = _extract_section(pages, spec)
        rows.extend(extraction.rows)
        omitted.extend(extraction.omitted)
    return _Extraction(rows, omitted)


def _render_review(extraction: _Extraction, source_path: Path) -> str:
    """Render deterministic pipe-delimited text for manual review."""
    invalid_count = sum(row.status != "OK" for row in extraction.rows)
    lines = [
        "# Overture PDF filament extraction - MANUAL REVIEW REQUIRED",
        f"# Source: {source_path.name}",
        f"# Explicit-hex rows: {len(extraction.rows)}",
        f"# Omitted no-hex rows: {len(extraction.omitted)}",
        f"# Rows requiring correction: {invalid_count}",
        "# Edit this file before it is used as import data.",
        "# Columns: page | product | color | hex | status",
        "page | product | color | hex | status",
    ]
    for row in extraction.rows:
        lines.append(
            f"{row.page} | {row.product} | {row.color} | "
            f"{row.hex_value} | {row.status}"
        )
    lines.extend(
        (
            "",
            "# Omitted entries without explicit hex values (not import candidates)",
            "# page | product | color | source value",
        )
    )
    for row in extraction.omitted:
        lines.append(
            f"# OMITTED_NO_HEX | {row.page} | {row.product} | "
            f"{row.color} | {row.source_value}"
        )
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Extract positioned Overture PDF data for manual review."
    )
    parser.add_argument("--pdf", type=Path, default=_DEFAULT_PDF)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    return parser


def main() -> int:
    """Extract the PDF and write the editable review file."""
    args = _build_parser().parse_args()
    extraction = _extract(args.pdf)
    content = _render_review(extraction, args.pdf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8", newline="\n")
    print("Overture positioned PDF extraction")
    print(f"Source: {args.pdf}")
    print(f"Review file: {args.output}")
    print(f"Explicit-hex rows: {len(extraction.rows)}")
    print(f"Omitted no-hex rows: {len(extraction.omitted)}")
    print(
        "Rows requiring correction: "
        f"{sum(row.status != 'OK' for row in extraction.rows)}"
    )
    print("No filament database changes were made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

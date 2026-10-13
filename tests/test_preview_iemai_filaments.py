"""Tests for the console-only IEMAI normalization preview."""

from __future__ import annotations

import contextlib
import io
import unittest

from tooling import preview_iemai_filaments as previewer


def _row(material: str, color: str, hex_value: str, row_number: int) -> previewer._SourceRow:
    return previewer._SourceRow(
        "IEMAI",
        material,
        color,
        hex_value,
        "Approximation - test",
        "https://example.com/source",
        row_number,
    )


class TestIemaiPreview(unittest.TestCase):
    """Normalization must preserve real finishes and promote CF/GF only."""

    def test_cf_and_gf_become_compound_types(self) -> None:
        cf = previewer._normalize_row(_row("ASA — CF", "Black", "#000000", 2))
        gf = previewer._normalize_row(_row("PPS — GF", "White", "#FFFFFF", 3))

        self.assertEqual((cf.type_name, cf.finish), ("ASA-CF", None))
        self.assertEqual((gf.type_name, gf.finish), ("PPS-GF", None))

    def test_other_qualifiers_remain_finishes(self) -> None:
        basic = previewer._normalize_row(_row("ASA — Basic", "Blue", "#123456", 2))
        esd = previewer._normalize_row(_row("ABS — ESD", "Black", "#000000", 3))

        self.assertEqual((basic.type_name, basic.finish), ("ASA", "Basic"))
        self.assertEqual((esd.type_name, esd.finish), ("ABS", "ESD"))

    def test_pla_plus_pro_is_preserved_as_the_parent_type(self) -> None:
        candidate = previewer._normalize_row(
            _row("PLA+/Pro — Basic", "Blue", "#123456", 2)
        )

        self.assertEqual((candidate.type_name, candidate.finish), ("PLA+/Pro", "Basic"))

    def test_multicolor_components_retain_source_order(self) -> None:
        candidate = previewer._normalize_row(
            _row("PLA — Rainbow", "Rainbow", "#79FB0E / #72A6DA / #D282F7", 2)
        )

        self.assertEqual(candidate.hex_value, "#79FB0E-#72A6DA-#D282F7")
        self.assertEqual(candidate.component_count, 3)

    def test_pc_transparent_is_explicitly_excluded(self) -> None:
        source = _row("PC — Basic", "IEMAI PC Transparent", "#00000000", 2)
        preview = previewer._build_preview([source], [source])

        self.assertEqual(preview.candidates, [])
        self.assertEqual(preview.excluded, [source])

    def test_source_reconciliation_compares_complete_rows(self) -> None:
        row = _row("ASA — Basic", "Blue", "#123456", 2)
        changed = _row("ASA — Basic", "Blue", "#654321", 3)

        self.assertEqual(previewer._reconcile_sources([row], [row]), [])
        differences = previewer._reconcile_sources([row], [changed])
        self.assertEqual(len(differences), 2)

    def test_console_output_includes_source_metadata(self) -> None:
        candidate = previewer._normalize_row(
            _row("ASA — Basic", "Blue", "#123456", 2)
        )
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            previewer._print_preview(previewer._Preview(candidates=[candidate]))

        rendered = output.getvalue()
        self.assertIn("confidence=Approximation - test", rendered)
        self.assertIn("source=https://example.com/source", rendered)


if __name__ == "__main__":
    unittest.main()

"""Tests for the positioned Overture PDF review extractor."""

from __future__ import annotations

import unittest

from tooling import extract_overture_pdf as extractor


class TestOverturePdfExtraction(unittest.TestCase):
    """Positioned extraction must preserve visual order and audit omissions."""

    def test_pairing_uses_each_column_independently(self) -> None:
        spec = extractor._SectionSpec(1, "PLA", 0.0, 100.0)
        fragments = [
            extractor._Fragment(1, 190.0, 80.0, "Left One"),
            extractor._Fragment(1, 190.0, 70.0, "#111111"),
            extractor._Fragment(1, 190.0, 50.0, "Left Two"),
            extractor._Fragment(1, 190.0, 40.0, "#222222"),
        ]

        pairs = extractor._pair_column(fragments, spec)

        self.assertEqual(
            [(name.text, value.text) for name, value in pairs],
            [("Left One", "#111111"), ("Left Two", "#222222")],
        )

    def test_known_fused_columns_are_split_into_visual_positions(self) -> None:
        fragments = [
            extractor._Fragment(
                8, 432.3, 299.6, "Easy Digital BlueEasy Cement Grey"
            ),
            extractor._Fragment(8, 432.3, 287.8, "#0696EF#697272"),
        ]

        corrected = extractor._apply_fused_fragment_replacements(8, fragments)

        self.assertEqual(
            [(item.x, item.text) for item in corrected],
            [
                (191.3, "Easy Cement Grey"),
                (432.3, "Easy Digital Blue"),
                (191.3, "#697272"),
                (432.3, "#0696EF"),
            ],
        )

    def test_section_preserves_compound_hex_and_omits_slash(self) -> None:
        spec = extractor._SectionSpec(1, "Matte PLA", 0.0, 100.0)
        pages = [[
            extractor._Fragment(1, 190.0, 80.0, "Blue-Red"),
            extractor._Fragment(1, 190.0, 70.0, "#0074BD & #F00024"),
            extractor._Fragment(1, 430.0, 80.0, "Rainbow"),
            extractor._Fragment(1, 430.0, 70.0, "/"),
        ]]

        result = extractor._extract_section(pages, spec)

        self.assertEqual(result.rows[0].hex_value, "#0074BD / #F00024")
        self.assertEqual(result.rows[0].status, "OK")
        self.assertEqual(result.omitted[0].color, "Rainbow")

    def test_visual_order_groups_small_baseline_differences(self) -> None:
        pairs = [
            (
                extractor._Fragment(1, 430.0, 81.0, "Right"),
                extractor._Fragment(1, 430.0, 70.0, "#222222"),
            ),
            (
                extractor._Fragment(1, 190.0, 80.0, "Left"),
                extractor._Fragment(1, 190.0, 69.0, "#111111"),
            ),
        ]

        ordered = extractor._visual_pair_order(pairs)

        self.assertEqual([name.text for name, _ in ordered], ["Left", "Right"])

    def test_invalid_hex_is_retained_for_manual_correction(self) -> None:
        spec = extractor._SectionSpec(1, "PC Professional", 0.0, 100.0)
        pages = [[
            extractor._Fragment(1, 190.0, 80.0, "White"),
            extractor._Fragment(1, 190.0, 70.0, "#FFFFF"),
        ]]

        result = extractor._extract_section(pages, spec)

        self.assertEqual(result.rows[0].hex_value, "#FFFFF")
        self.assertEqual(result.rows[0].status, "REVIEW_INVALID_HEX")


if __name__ == "__main__":
    unittest.main()

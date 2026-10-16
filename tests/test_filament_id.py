"""Canonical filament ID generation and validation tests."""

from __future__ import annotations

import unittest

from color_tools import generate_filament_id, validate_filament_id
from color_tools.filament_id import next_available_filament_id


class TestFilamentId(unittest.TestCase):
    """Verify stable slug generation and collision suggestions."""

    def test_generates_id_from_product_identity(self) -> None:
        self.assertEqual(
            generate_filament_id("Bambu Lab", "PLA+", "Silk", "Jade White"),
            "bambu-lab-pla-plus-silk-jade-white",
        )

    def test_omits_absent_finish(self) -> None:
        self.assertEqual(
            generate_filament_id("Maker", "PETG", None, "Ocean Blue"),
            "maker-petg-ocean-blue",
        )

    def test_removes_punctuation_without_adding_word_boundaries(self) -> None:
        """Legacy database IDs remove punctuation other than hyphens and plus."""
        cases = (
            ("Red/Green", "maker-pla-redgreen"),
            ("Bobbi's Purple Iris", "maker-pla-bobbis-purple-iris"),
            ("Gentleman's Gray", "maker-pla-gentlemans-gray"),
        )
        for color, expected in cases:
            with self.subTest(color=color):
                self.assertEqual(
                    generate_filament_id("Maker", "PLA", None, color),
                    expected,
                )

    def test_rejects_components_without_ascii_slug_content(self) -> None:
        with self.assertRaisesRegex(ValueError, "ASCII letter or digit"):
            generate_filament_id("Maker", "PLA", None, "💙")

    def test_validation_requires_canonical_slug(self) -> None:
        for invalid in ("", "Uppercase", "two--hyphens", " leading", "trailing-"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_filament_id(invalid)

    def test_next_available_id_uses_first_free_suffix(self) -> None:
        self.assertEqual(
            next_available_filament_id("maker-pla-red", {"maker-pla-red", "maker-pla-red-2"}),
            "maker-pla-red-3",
        )


if __name__ == "__main__":
    unittest.main()

"""Tests for criteria-based filament filtering and nearest searches."""

from __future__ import annotations

import unittest

from color_tools.filament_filter_criteria import FilamentFilterCriteria
from color_tools.filament_palette import FilamentPalette, FilamentRecord


class TestFilamentFilterCriteria(unittest.TestCase):
    """Exercise normalized criteria independently and through a palette."""

    def setUp(self) -> None:
        """Create a small deterministic filament palette."""
        self.core_red = FilamentRecord(
            id="acme-pla-matte-red",
            maker="Acme",
            type="PLA",
            finish="Matte",
            color="Red",
            hex="#FF0000",
            source="filaments.json",
        )
        self.user_red = FilamentRecord(
            id="acme-pla-silk-red",
            maker="Acme",
            type="PLA",
            finish="Silk",
            color="Custom Red",
            hex="#FF0000",
            source="user-filaments.json",
        )
        self.blue = FilamentRecord(
            id="other-petg-glossy-blue",
            maker="Other Maker",
            type="PETG",
            finish="Glossy",
            color="Blue",
            hex="#0000FF",
            source="filaments.json",
        )
        self.palette = FilamentPalette(
            [self.core_red, self.user_red, self.blue],
            maker_synonyms={"Acme": ["AC"]},
        )

    def test_matches_case_insensitively(self):
        """Whitespace and case do not affect any criteria field."""
        criteria = FilamentFilterCriteria(
            maker=" acme ",
            type_name=["pla"],
            finish=("MATTE",),
            color=" red ",
        )
        self.assertTrue(criteria.matches("ACME", "PLA", "matte", "RED"))
        equivalent = FilamentFilterCriteria("ACME", "PLA", "matte", "RED")
        self.assertEqual(criteria, equivalent)
        self.assertEqual(hash(criteria), hash(equivalent))

    def test_color_accepts_multiple_case_insensitive_values(self):
        """Color criteria accept one value or an iterable like other fields."""
        results = self.palette.filter_by_criteria(
            include=FilamentFilterCriteria(color=[" custom red ", "BLUE"]),
            owned=False,
        )
        self.assertEqual(results, [self.user_red, self.blue])

    def test_filter_by_criteria_includes_and_excludes(self):
        """Inclusion and exclusion criteria are applied in one operation."""
        results = self.palette.filter_by_criteria(
            include=FilamentFilterCriteria(maker="ac", type_name="pla"),
            exclude=FilamentFilterCriteria(finish="silk"),
            owned=False,
        )
        self.assertEqual(results, [self.core_red])

    def test_exclusion_fields_use_and_semantics(self):
        """A multi-field exclusion removes only complete matches."""
        results = self.palette.filter_by_criteria(
            exclude=FilamentFilterCriteria(maker="acme", finish="matte"),
            owned=False,
        )
        self.assertEqual(results, [self.user_red, self.blue])

    def test_empty_exclusion_excludes_nothing(self):
        """An empty exclusion criterion is a no-op."""
        results = self.palette.filter_by_criteria(
            exclude=FilamentFilterCriteria(),
            owned=False,
        )
        self.assertEqual(results, self.palette.records)

    def test_empty_iterables_are_inactive(self):
        """Empty values preserve legacy no-filter behavior."""
        criteria = FilamentFilterCriteria(maker=[], type_name=(), finish=[], color=[])
        self.assertTrue(criteria.is_empty)
        self.assertEqual(
            self.palette.filter(maker=[], type_name=[], finish=[], owned=False),
            self.palette.records,
        )

    def test_legacy_filter_is_case_insensitive(self):
        """The existing filter API gains consistent case-insensitive matching."""
        results = self.palette.filter(
            maker="ac",
            type_name="pla",
            finish="matte",
            owned=False,
        )
        self.assertEqual(results, [self.core_red])

    def test_legacy_color_filter_delegates_to_criteria(self):
        """The scalar legacy color argument preserves its public behavior."""
        results = self.palette.filter(color=" custom RED ", owned=False)
        self.assertEqual(results, [self.user_red])

    def test_color_exclusion_uses_complete_criteria(self):
        """Color participates in the same AND semantics as other fields."""
        results = self.palette.filter_by_criteria(
            exclude=FilamentFilterCriteria(maker="acme", color="red"),
            owned=False,
        )
        self.assertEqual(results, [self.user_red, self.blue])

    def test_nearest_criteria_excludes_closest_record(self):
        """Nearest criteria searches honor exclusions."""
        record, distance = self.palette.nearest_filament_by_criteria(
            (255, 0, 0),
            exclude=FilamentFilterCriteria(finish="silk"),
            owned=False,
        )
        self.assertEqual(record, self.core_red)
        self.assertEqual(distance, 0.0)

    def test_equal_distance_prefers_user_source(self):
        """Single and plural searches consistently prioritize user records."""
        results = self.palette.nearest_filaments_by_criteria(
            (255, 0, 0),
            count=2,
            include=FilamentFilterCriteria(maker="acme"),
            owned=False,
        )
        self.assertEqual(results[0][0], self.user_red)
        self.assertEqual(
            self.palette.nearest_filament((255, 0, 0), maker="acme", owned=False)[0],
            self.user_red,
        )


if __name__ == "__main__":
    unittest.main()

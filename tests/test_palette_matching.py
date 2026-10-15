"""Focused coverage for color-palette matching contracts."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from color_tools.constants import ColorConstants
from color_tools.palette import ColorRecord, Palette


def _record(
    name: str,
    *,
    lab: tuple[float, float, float] = (50.0, 0.0, 0.0),
    hsl: tuple[float, float, float] = (0.0, 50.0, 50.0),
    lch: tuple[float, float, float] = (50.0, 40.0, 0.0),
    rgb: tuple[int, int, int] = (128, 128, 128),
    source: str = "colors.json",
) -> ColorRecord:
    """Build a small record whose coordinates are controlled by the test."""
    return ColorRecord(name, "#808080", rgb, hsl, lab, lch, source)


class TestPaletteMatching(unittest.TestCase):
    """Exercise metric dispatch, circular hues, bounds, and tie ordering."""

    def setUp(self) -> None:
        self.exact = _record("exact", lab=(50.0, 10.0, -5.0))
        self.other = _record("other", lab=(70.0, -20.0, 30.0))
        self.palette = Palette([self.exact, self.other])

    def test_hsl_plural_matching_wraps_hue(self) -> None:
        near_wrap = _record("near-wrap", hsl=(1.0, 50.0, 50.0))
        farther = _record("farther", hsl=(300.0, 50.0, 50.0))

        results = Palette([farther, near_wrap]).nearest_colors(
            (359.0, 50.0, 50.0), space="hsl", count=2
        )

        self.assertEqual([record.name for record, _ in results], ["near-wrap", "farther"])
        self.assertEqual(results[0][1], 2.0)

    def test_lch_single_and_plural_matching_wrap_hue_at_index_two(self) -> None:
        near_wrap = _record("near-wrap", lch=(50.0, 40.0, 1.0))
        farther = _record("farther", lch=(50.0, 40.0, 300.0))
        palette = Palette([farther, near_wrap])

        nearest, distance = palette.nearest_color(
            (50.0, 40.0, 359.0), space="lch"
        )
        results = palette.nearest_colors(
            (50.0, 40.0, 359.0), space="lch", count=2
        )

        self.assertEqual(nearest, near_wrap)
        self.assertEqual(distance, 2.0)
        self.assertEqual([record.name for record, _ in results], ["near-wrap", "farther"])

    def test_lab_metric_aliases_work_for_single_and_plural_searches(self) -> None:
        aliases = (
            "de76",
            "cie76",
            "euclidean",
            "de94",
            "cie94",
            "de2000",
            "ciede2000",
            "cmc",
            "decmc",
            "cmc21",
            "cmc11",
            "hyab",
        )
        target = self.exact.lab

        for metric in aliases:
            with self.subTest(metric=metric, api="single"):
                record, distance = self.palette.nearest_color(target, metric=metric)
                self.assertEqual(record, self.exact)
                self.assertEqual(distance, 0.0)
            with self.subTest(metric=metric, api="plural"):
                results = self.palette.nearest_colors(target, metric=metric, count=1)
                self.assertEqual(results, [(self.exact, 0.0)])

    def test_custom_cmc_parameters_are_passed_through_both_apis(self) -> None:
        with patch("color_tools.palette.delta_e_cmc", return_value=7.5) as distance:
            self.palette.nearest_color(self.exact.lab, metric="cmc", cmc_l=3.0, cmc_c=4.0)
            self.palette.nearest_colors(
                self.exact.lab, metric="decmc", count=1, cmc_l=3.0, cmc_c=4.0
            )

        self.assertEqual(distance.call_count, 4)
        for call in distance.call_args_list:
            self.assertEqual(call.kwargs, {"l": 3.0, "c": 4.0})

    def test_cmc_shorthands_use_their_documented_ratios(self) -> None:
        with patch("color_tools.palette.delta_e_cmc", return_value=1.0) as distance:
            self.palette.nearest_color(self.exact.lab, metric="cmc21")
            cmc21_calls = list(distance.call_args_list)
            distance.reset_mock()
            self.palette.nearest_colors(self.exact.lab, metric="cmc11", count=1)
            cmc11_calls = list(distance.call_args_list)

        self.assertTrue(cmc21_calls)
        self.assertTrue(cmc11_calls)
        for call in cmc21_calls:
            self.assertEqual(
                call.kwargs,
                {"l": ColorConstants.CMC_L_DEFAULT, "c": ColorConstants.CMC_C_DEFAULT},
            )
        for call in cmc11_calls:
            self.assertEqual(
                call.kwargs,
                {"l": ColorConstants.CMC_C_DEFAULT, "c": ColorConstants.CMC_C_DEFAULT},
            )

    def test_unknown_metric_fails_for_both_apis(self) -> None:
        for search in (self.palette.nearest_color, self.palette.nearest_colors):
            with self.subTest(search=search.__name__):
                with self.assertRaisesRegex(ValueError, "Unknown metric"):
                    search(self.exact.lab, metric="unknown")

    def test_plural_count_is_bounded_to_one_through_fifty(self) -> None:
        records = [
            _record(f"color-{index}", lab=(float(index), 0.0, 0.0))
            for index in range(60)
        ]
        palette = Palette(records)

        self.assertEqual(len(palette.nearest_colors((0.0, 0.0, 0.0), count=0)), 1)
        self.assertEqual(len(palette.nearest_colors((0.0, 0.0, 0.0), count=100)), 50)

    def test_exact_ties_prefer_user_source_in_both_apis(self) -> None:
        core = _record("core", rgb=(10, 20, 30), source="colors.json")
        user = _record("user", rgb=(10, 20, 30), source="user-colors.json")
        palette = Palette([core, user])

        nearest, distance = palette.nearest_color((10.0, 20.0, 30.0), space="rgb")
        results = palette.nearest_colors((10.0, 20.0, 30.0), space="rgb", count=2)

        self.assertEqual(nearest, user)
        self.assertEqual(distance, 0.0)
        self.assertEqual([record for record, _ in results], [user, core])


if __name__ == "__main__":
    unittest.main()

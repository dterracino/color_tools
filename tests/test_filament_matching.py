"""Focused coverage for filament matching and hue-filter contracts."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from color_tools.config import config_context
from color_tools.filament_filter_criteria import FilamentFilterCriteria
from color_tools.filament_palette import FilamentPalette, FilamentRecord


def _filament(
    identifier: str,
    hex_code: str,
    *,
    maker: str = "Acme",
    type_name: str = "PLA",
    finish: str | None = "Matte",
    color: str | None = None,
    td_value: float | None = None,
    source: str = "filaments.json",
) -> FilamentRecord:
    """Build a deterministic filament record for matching tests."""
    return FilamentRecord(
        id=identifier,
        maker=maker,
        type=type_name,
        finish=finish,
        color=color or identifier,
        hex=hex_code,
        td_value=td_value,
        source=source,
    )


def _zero_distance(
    _left: tuple[float, float, float],
    _right: tuple[float, float, float],
) -> float:
    """Return a tied distance for tests that isolate candidate filtering."""
    return 0.0


class TestFilamentMatching(unittest.TestCase):
    """Exercise metric dispatch, failure isolation, ordering, and filters."""

    def setUp(self) -> None:
        self.exact = _filament("exact", "#804020")
        self.other = _filament("other", "#2080C0")
        self.palette = FilamentPalette([self.exact, self.other])

    def test_metric_aliases_work_for_single_and_plural_searches(self) -> None:
        aliases = (
            "de2000",
            "ciede2000",
            "de94",
            "cie94",
            "de76",
            "cie76",
            "euclidean",
            "cmc",
            "decmc",
            "hyab",
        )

        for metric in aliases:
            with self.subTest(metric=metric, api="single"):
                record, distance = self.palette.nearest_filament(
                    self.exact.rgb, metric=metric, owned=False
                )
                self.assertEqual(record, self.exact)
                self.assertAlmostEqual(distance, 0.0)
            with self.subTest(metric=metric, api="plural"):
                results = self.palette.nearest_filaments(
                    self.exact.rgb, metric=metric, count=1, owned=False
                )
                self.assertEqual(results[0][0], self.exact)
                self.assertAlmostEqual(results[0][1], 0.0)

    def test_custom_cmc_parameters_are_passed_to_distance_function(self) -> None:
        with patch("color_tools.filament_palette.delta_e_cmc", return_value=4.0) as distance:
            self.palette.nearest_filaments(
                self.exact.rgb,
                metric="decmc",
                count=1,
                owned=False,
                cmc_l=3.0,
                cmc_c=4.0,
            )

        self.assertEqual(distance.call_count, 2)
        for call in distance.call_args_list:
            self.assertEqual(call.kwargs, {"l": 3.0, "c": 4.0})

    def test_unknown_metric_fails_for_both_apis(self) -> None:
        for search in (self.palette.nearest_filament, self.palette.nearest_filaments):
            with self.subTest(search=search.__name__):
                with self.assertRaisesRegex(ValueError, "Unknown metric"):
                    search(self.exact.rgb, metric="unknown", owned=False)

    def test_hue_filter_wraps_and_keeps_achromatic_candidates(self) -> None:
        near_wrap = _filament("near-wrap", "#BB2266")
        achromatic = _filament("gray", "#808080")
        outside = _filament("outside", "#FF0000")
        palette = FilamentPalette([near_wrap, achromatic, outside])

        with patch(
            "color_tools.filament_palette._resolve_distance_function",
            return_value=_zero_distance,
        ):
            results = palette.nearest_filaments(
                (221, 85, 136), count=3, owned=False, max_hue_delta=1.0
            )

        self.assertEqual([record.id for record, _ in results], ["near-wrap", "gray"])

    def test_achromatic_target_bypasses_hue_filtering(self) -> None:
        red = _filament("red", "#FF0000")
        blue = _filament("blue", "#0000FF")
        palette = FilamentPalette([red, blue])

        with patch(
            "color_tools.filament_palette._resolve_distance_function",
            return_value=_zero_distance,
        ):
            results = palette.nearest_filaments(
                (128, 128, 128), count=2, owned=False, max_hue_delta=0.0
            )

        self.assertEqual([record.id for record, _ in results], ["red", "blue"])

    def test_empty_hue_filter_raises_focused_guidance(self) -> None:
        palette = FilamentPalette([_filament("red", "#FF0000")])

        with self.assertRaisesRegex(
            ValueError,
            r"No filaments found within 1\.0° hue.*larger --max-hue-delta",
        ):
            palette.nearest_filaments(
                (221, 85, 136), owned=False, max_hue_delta=1.0
            )

    def test_one_distance_failure_does_not_discard_valid_candidates(self) -> None:
        def distance(_target: tuple[float, float, float], candidate: tuple[float, float, float]) -> float:
            if candidate == self.exact.lab:
                raise ValueError("bad candidate")
            return 2.5

        with patch(
            "color_tools.filament_palette._resolve_distance_function",
            return_value=distance,
        ):
            results = self.palette.nearest_filaments(
                self.exact.rgb, count=2, owned=False
            )

        self.assertEqual(results, [(self.other, 2.5)])

    def test_all_distance_failures_raise_public_error(self) -> None:
        def fail(
            _target: tuple[float, float, float],
            _candidate: tuple[float, float, float],
        ) -> float:
            raise ArithmeticError("cannot calculate")

        with patch(
            "color_tools.filament_palette._resolve_distance_function",
            return_value=fail,
        ):
            with self.assertRaisesRegex(ValueError, "^No valid filaments found$"):
                self.palette.nearest_filaments(self.exact.rgb, owned=False)

    def test_equal_distances_prefer_user_then_preserve_stable_order(self) -> None:
        first = _filament("first", "#112233")
        second = _filament("second", "#112233")
        user = _filament("user", "#112233", source="user-filaments.json")
        palette = FilamentPalette([first, second, user])

        results = palette.nearest_filaments((17, 34, 51), count=3, owned=False)

        self.assertEqual([record.id for record, _ in results], ["user", "first", "second"])

    def test_plural_count_is_bounded_to_one_through_fifty(self) -> None:
        records = [
            _filament(f"filament-{index}", f"#{index:02X}0000")
            for index in range(60)
        ]
        palette = FilamentPalette(records)

        self.assertEqual(len(palette.nearest_filaments((0, 0, 0), count=0, owned=False)), 1)
        self.assertEqual(len(palette.nearest_filaments((0, 0, 0), count=100, owned=False)), 50)

    def test_combined_filters_owned_state_synonyms_and_multicolor_mode(self) -> None:
        with config_context(multi_color_mode="last"):
            split = _filament(
                "split",
                "#FF0000-#0000FF",
                maker="Acme Lab",
                color="Split",
                td_value=2.0,
            )
            no_td = _filament(
                "no-td", "#0000FF", maker="Acme Lab", color="No TD"
            )
            unowned = _filament(
                "unowned", "#0000FF", maker="Acme Lab", color="Unowned", td_value=2.0
            )
        palette = FilamentPalette(
            [split, no_td, unowned],
            maker_synonyms={"Acme Lab": ["ACME"]},
            owned_filaments={"split", "no-td"},
        )
        include = FilamentFilterCriteria(
            maker=" acme ", type_name=["PLA"], finish=None, has_td=True
        )
        exclude = FilamentFilterCriteria(color=["No TD"])

        filtered = palette.filter_by_criteria(include, exclude, owned=None)
        nearest, distance = palette.nearest_filament_by_criteria(
            (0, 0, 255), include=include, exclude=exclude, owned=None
        )

        self.assertEqual(split.rgb, (0, 0, 255))
        self.assertEqual(filtered, [split])
        self.assertEqual(nearest, split)
        self.assertAlmostEqual(distance, 0.0)


if __name__ == "__main__":
    unittest.main()

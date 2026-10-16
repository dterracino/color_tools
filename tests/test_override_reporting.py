"""Focused override-report capture, summary, and cleanup tests."""

from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from color_tools.cli_commands.reporting import show_override_report
from color_tools.color_load_report import ColorLoadEvent, ColorLoadReport
from color_tools.filament_palette import FilamentRecord
from color_tools.filament_load_report import FilamentLoadEvent, FilamentLoadReport
from color_tools.palette import ColorRecord
from color_tools.synonym_load_report import SynonymLoadEvent, SynonymLoadReport


def _color(name: str, rgb: tuple[int, int, int], source: str) -> ColorRecord:
    """Build a reportable color record with an explicit source."""
    return ColorRecord.from_rgb(rgb, name=name, source=source)


def _filament(identifier: str, source: str) -> FilamentRecord:
    """Build a reportable filament record with an explicit source."""
    return FilamentRecord(
        id=identifier,
        maker="Maker",
        type="PLA",
        finish=None,
        color=identifier,
        hex="#123456",
        source=source,
    )


class TestOverrideReporting(unittest.TestCase):
    """Verify structured override categories, summaries, and failures."""

    def _run_with_loaders(
        self,
        *,
        color_result: tuple[list[ColorRecord], ColorLoadReport],
        filament_result: tuple[list[FilamentRecord], FilamentLoadReport],
        synonym_result: tuple[dict[str, list[str]], SynonymLoadReport],
    ) -> tuple[str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch(
                "color_tools.cli_commands.reporting.load_colors",
                return_value=color_result,
            ),
            patch(
                "color_tools.cli_commands.reporting.load_filaments",
                return_value=filament_result,
            ),
            patch(
                "color_tools.cli_commands.reporting.load_maker_synonyms",
                return_value=synonym_result,
            ),
            patch("sys.stdout", stdout),
            patch("sys.stderr", stderr),
        ):
            show_override_report("test-data")
        return stdout.getvalue(), stderr.getvalue()

    def test_every_structured_change_is_labeled(self) -> None:
        original_color = _color("red", (255, 0, 0), "colors.json")
        replacement_color = _color("red", (220, 20, 60), "user-colors.json")
        original_filament = _filament("red", "filaments.json")
        replacement_filament = _filament("red", "user-filaments.json")

        stdout, stderr = self._run_with_loaders(
            color_result=([replacement_color], ColorLoadReport(
                1, 1, 1,
                (ColorLoadEvent("overridden", replacement_color, original_color),),
            )),
            filament_result=([replacement_filament], FilamentLoadReport(
                1, 1, 1,
                (FilamentLoadEvent("overridden", replacement_filament, original_filament),),
            )),
            synonym_result=({"Maker": ["Alias"]}, SynonymLoadReport(
                1, 1, 1,
                (SynonymLoadEvent("extended", "Maker", ("Alias",), ("Old",), ("Old", "Alias")),),
            )),
        )

        self.assertEqual(stderr, "")
        self.assertIn("Colors overridden by name: 1", stdout)
        self.assertIn("Overrode red (#FF0000, colors.json)", stdout)
        self.assertIn(
            "Overrode red (filaments.json -> user-filaments.json)", stdout,
        )
        self.assertIn("Extended Maker: ['Old', 'Alias']", stdout)

    def test_report_states_when_no_overrides_are_emitted(self) -> None:
        stdout, stderr = self._run_with_loaders(
            color_result=(
                [_color("red", (255, 0, 0), "colors.json")],
                ColorLoadReport(1, 0, 1),
            ),
            filament_result=([_filament("red", "filaments.json")], FilamentLoadReport(1, 0, 1)),
            synonym_result=({}, SynonymLoadReport(0, 0, 0)),
        )

        self.assertEqual(stderr, "")
        self.assertIn("No user overrides detected.", stdout)
        self.assertNotIn("Override Details:", stdout)

    def test_summary_counts_color_and_filament_sources(self) -> None:
        stdout, _stderr = self._run_with_loaders(
            color_result=(
                [
                    _color("red", (255, 0, 0), "colors.json"),
                    _color("green", (0, 255, 0), "colors.json"),
                    _color("blue", (0, 0, 255), "user-colors.json"),
                ],
                ColorLoadReport(2, 1, 3),
            ),
            filament_result=(
                [
                    _filament("first", "filaments.json"),
                    _filament("second", "user-filaments.json"),
                    _filament("third", "user-filaments.json"),
                ],
                FilamentLoadReport(1, 2, 3),
            ),
            synonym_result=({}, SynonymLoadReport(0, 0, 0)),
        )

        self.assertIn("Total colors: 3", stdout)
        self.assertIn("Total filaments: 3", stdout)
        self.assertIn("colors.json: 2 records", stdout)
        self.assertIn("user-colors.json: 1 records", stdout)
        self.assertIn("filaments.json: 1 records", stdout)
        self.assertIn("user-filaments.json: 2 records", stdout)

    def test_loader_failure_prints_one_error_and_exits_one(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch(
                "color_tools.cli_commands.reporting.load_colors",
                side_effect=ValueError("invalid user colors"),
            ),
            patch("sys.stdout", stdout),
            patch("sys.stderr", stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            show_override_report("test-data")

        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(
            stderr.getvalue(),
            "Error loading override report data: invalid user colors\n",
        )

    def test_unexpected_programming_errors_are_not_hidden(self) -> None:
        with (
            patch(
                "color_tools.cli_commands.reporting.load_colors",
                side_effect=RuntimeError("bug"),
            ),
            patch("sys.stdout", io.StringIO()),
            patch("sys.stderr", io.StringIO()),
            self.assertRaisesRegex(RuntimeError, "bug"),
        ):
            show_override_report("test-data")


if __name__ == "__main__":
    unittest.main()

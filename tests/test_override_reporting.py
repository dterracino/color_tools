"""Focused override-report capture, summary, and cleanup tests."""

from __future__ import annotations

import io
import logging
import unittest
from collections.abc import Callable
from unittest.mock import patch

from color_tools.cli_commands.reporting import show_override_report
from color_tools.filament_palette import FilamentRecord
from color_tools.palette import ColorRecord


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
    """Verify override categories, summaries, failures, and logger cleanup."""

    def _run_with_loaders(
        self,
        *,
        color_loader: Callable[[str], list[ColorRecord]],
        filament_loader: Callable[[str], list[FilamentRecord]],
        synonym_loader: Callable[[str], dict[str, list[str]]],
    ) -> tuple[str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch(
                "color_tools.cli_commands.reporting.load_colors",
                side_effect=color_loader,
            ),
            patch(
                "color_tools.cli_commands.reporting.load_filaments",
                side_effect=filament_loader,
            ),
            patch(
                "color_tools.cli_commands.reporting.load_maker_synonyms",
                side_effect=synonym_loader,
            ),
            patch("sys.stdout", stdout),
            patch("sys.stderr", stderr),
        ):
            show_override_report("test-data")
        return stdout.getvalue(), stderr.getvalue()

    def test_every_override_message_is_captured_and_labeled(self) -> None:
        def _load_colors(_path: str) -> list[ColorRecord]:
            logger = logging.getLogger("color_tools.palette")
            logger.info("User colors override 1 core colors by name: red")
            logger.info("User colors override 1 core colors by RGB: crimson")
            return [_color("red", (255, 0, 0), "user-colors.json")]

        def _load_filaments(_path: str) -> list[FilamentRecord]:
            logger = logging.getLogger("color_tools.filament_palette")
            logger.info("User filaments override 1 core filaments exactly: exact")
            logger.info("User filaments override 1 core filaments by RGB: rgb")
            return [_filament("red", "user-filaments.json")]

        def _load_synonyms(_path: str) -> dict[str, list[str]]:
            logger = logging.getLogger("color_tools.filament_palette")
            logger.info("User synonyms override 1 core makers: replacement")
            logger.info("User synonyms extend 1 core makers: extension")
            return {}

        stdout, stderr = self._run_with_loaders(
            color_loader=_load_colors,
            filament_loader=_load_filaments,
            synonym_loader=_load_synonyms,
        )

        self.assertEqual(stderr, "")
        self.assertIn("Colors: User colors override 1 core colors by name", stdout)
        self.assertIn("Colors: User colors override 1 core colors by RGB", stdout)
        self.assertIn(
            "Filaments: User filaments override 1 core filaments exactly",
            stdout,
        )
        self.assertIn(
            "Filaments: User filaments override 1 core filaments by RGB",
            stdout,
        )
        self.assertIn("Synonyms: User synonyms override 1 core makers", stdout)
        self.assertIn("Synonyms: User synonyms extend 1 core makers", stdout)

    def test_report_states_when_no_overrides_are_emitted(self) -> None:
        stdout, stderr = self._run_with_loaders(
            color_loader=lambda _path: [_color("red", (255, 0, 0), "colors.json")],
            filament_loader=lambda _path: [_filament("red", "filaments.json")],
            synonym_loader=lambda _path: {},
        )

        self.assertEqual(stderr, "")
        self.assertIn("No user overrides detected.", stdout)
        self.assertNotIn("Override Details:", stdout)

    def test_summary_counts_color_and_filament_sources(self) -> None:
        stdout, _stderr = self._run_with_loaders(
            color_loader=lambda _path: [
                _color("red", (255, 0, 0), "colors.json"),
                _color("green", (0, 255, 0), "colors.json"),
                _color("blue", (0, 0, 255), "user-colors.json"),
            ],
            filament_loader=lambda _path: [
                _filament("first", "filaments.json"),
                _filament("second", "user-filaments.json"),
                _filament("third", "user-filaments.json"),
            ],
            synonym_loader=lambda _path: {},
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

    def test_logger_levels_and_handlers_are_restored_after_failure(self) -> None:
        palette_logger = logging.getLogger("color_tools.palette")
        filament_logger = logging.getLogger("color_tools.filament_palette")
        sentinel = logging.NullHandler()
        original_palette_level = palette_logger.level
        original_filament_level = filament_logger.level
        palette_logger.setLevel(logging.WARNING)
        filament_logger.setLevel(logging.ERROR)
        filament_logger.addHandler(sentinel)

        try:
            before_palette_handlers = list(palette_logger.handlers)
            before_filament_handlers = list(filament_logger.handlers)
            with (
                patch(
                    "color_tools.cli_commands.reporting.load_colors",
                    side_effect=OSError("unreadable"),
                ),
                patch("sys.stdout", io.StringIO()),
                patch("sys.stderr", io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                show_override_report("test-data")

            self.assertEqual(palette_logger.level, logging.WARNING)
            self.assertEqual(filament_logger.level, logging.ERROR)
            self.assertEqual(palette_logger.handlers, before_palette_handlers)
            self.assertEqual(filament_logger.handlers, before_filament_handlers)
        finally:
            filament_logger.removeHandler(sentinel)
            palette_logger.setLevel(original_palette_level)
            filament_logger.setLevel(original_filament_level)


if __name__ == "__main__":
    unittest.main()

"""Focused Phase 6 coverage for filament and conversion CLI handlers."""

from __future__ import annotations

import io
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from typing import cast
from unittest.mock import patch

from color_tools.filament_filter_criteria import FilamentFilterCriteria
from color_tools.filament_palette import FilamentPalette, FilamentRecord


def _filament(
    identifier: str = "maker_pla_red",
    *,
    td_value: float | None = 4.0,
) -> FilamentRecord:
    """Build a deterministic filament for handler output and filtering."""
    return FilamentRecord(
        id=identifier,
        maker="Maker",
        type="PLA",
        finish="Basic",
        color="Red",
        hex="#FF0000",
        td_value=td_value,
        source="test.json",
    )


class _FakeFilamentPalette:
    """Minimal observable substitute for the filament CLI's palette."""

    def __init__(self, records: list[FilamentRecord] | None = None) -> None:
        self.records = records if records is not None else [_filament()]
        self.owned = list(self.records)
        self.filter_calls: list[dict[str, object]] = []
        self.nearest_include: FilamentFilterCriteria | None = None
        self.add_error: ValueError | None = None
        self.remove_error: ValueError | None = None

    def list_owned(self) -> list[FilamentRecord]:
        return self.owned

    def add_owned(
        self,
        filament_id: str,
        json_path: Path | str | None = None,
    ) -> None:
        del filament_id, json_path
        if self.add_error is not None:
            raise self.add_error

    def remove_owned(
        self,
        filament_id: str,
        json_path: Path | str | None = None,
    ) -> None:
        del filament_id, json_path
        if self.remove_error is not None:
            raise self.remove_error

    def get_filament_by_id(self, filament_id: str) -> FilamentRecord:
        for record in self.records:
            if record.id == filament_id:
                return record
        raise ValueError(f"Unknown filament ID: {filament_id}")

    def filter(self, **criteria: object) -> list[FilamentRecord]:
        self.filter_calls.append(criteria)
        has_td = criteria.get("has_td")
        if has_td is True:
            return [record for record in self.records if record.td_value is not None]
        return list(self.records)

    def nearest_filament_by_criteria(
        self,
        _rgb: tuple[int, int, int],
        **criteria: object,
    ) -> tuple[FilamentRecord, float]:
        include = criteria["include"]
        self.nearest_include = cast(FilamentFilterCriteria, include)
        return self.records[0], 1.25

    def nearest_filaments_by_criteria(
        self,
        _rgb: tuple[int, int, int],
        **criteria: object,
    ) -> list[tuple[FilamentRecord, float]]:
        include = criteria["include"]
        self.nearest_include = cast(FilamentFilterCriteria, include)
        return [(record, float(index)) for index, record in enumerate(self.records)]


class TestFilamentCLIPhase6(unittest.TestCase):
    """Cover ownership, export selection, and operation validation."""

    def _args(self, **overrides: object) -> Namespace:
        values: dict[str, object] = {
            "value": None,
            "hex": None,
            "nearest": False,
            "maker": None,
            "type": None,
            "finish": None,
            "color": None,
            "has_td": False,
            "exclude_maker": None,
            "exclude_type": None,
            "exclude_finish": None,
            "exclude_color": None,
            "list_makers": False,
            "list_types": False,
            "list_finishes": False,
            "list_export_formats": False,
            "export": None,
            "output": None,
            "metric": "de2000",
            "limit": None,
            "count": False,
            "cmc_l": 2.0,
            "cmc_c": 1.0,
            "max_hue_delta": None,
            "all_filaments": False,
            "multi_color_mode": "first",
            "manage": False,
            "gui": False,
            "list_owned": False,
            "add_owned": None,
            "remove_owned": None,
        }
        values.update(overrides)
        return Namespace(**values)

    def _run(
        self,
        args: Namespace,
        palette: _FakeFilamentPalette | None = None,
        json_path: Path | str | None = None,
    ) -> tuple[object, str, str]:
        from color_tools.cli_commands.handlers.filament import (
            handle_filament_command,
        )

        active_palette = palette or _FakeFilamentPalette()
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch(
                "color_tools.cli_commands.handlers.filament."
                "FilamentPalette.load_default",
                return_value=cast(FilamentPalette, active_palette),
            ),
            patch("sys.stdout", stdout),
            patch("sys.stderr", stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            handle_filament_command(args, json_path)
        return raised.exception.code, stdout.getvalue(), stderr.getvalue()

    def test_limit_without_nearest_exits_two_before_loading_data(self) -> None:
        with patch(
            "color_tools.cli_commands.handlers.filament.FilamentPalette.load_default"
        ) as load:
            code, _stdout, stderr = self._run(self._args(limit=2))
        self.assertEqual(code, 2)
        self.assertIn("--limit requires --nearest", stderr)
        load.assert_not_called()

    def test_list_owned_handles_empty_and_populated_collections(self) -> None:
        for owned, expected in (([], "No owned filaments"), ([_filament()], "ID: maker_pla_red")):
            with self.subTest(populated=bool(owned)):
                palette = _FakeFilamentPalette()
                palette.owned = owned
                code, stdout, _stderr = self._run(
                    self._args(list_owned=True),
                    palette,
                )
                self.assertEqual(code, 0)
                self.assertIn(expected, stdout)

    def test_add_and_remove_owned_success_show_selected_filament(self) -> None:
        for operation in ("add_owned", "remove_owned"):
            with self.subTest(operation=operation):
                code, stdout, stderr = self._run(
                    self._args(**{operation: "maker_pla_red"})
                )
                self.assertEqual(code, 0)
                self.assertIn("Maker PLA Basic - Red", stdout)
                self.assertIn("maker_pla_red", stdout)
                self.assertEqual(stderr, "")

    def test_add_and_remove_owned_failures_use_stderr_and_exit_one(self) -> None:
        for operation in ("add_owned", "remove_owned"):
            with self.subTest(operation=operation):
                palette = _FakeFilamentPalette()
                error = ValueError(f"cannot {operation}")
                if operation == "add_owned":
                    palette.add_error = error
                else:
                    palette.remove_error = error
                code, stdout, stderr = self._run(
                    self._args(**{operation: "maker_pla_red"}),
                    palette,
                )
                self.assertEqual(code, 1)
                self.assertEqual(stdout, "")
                self.assertIn(str(error), stderr)

    def test_unfiltered_export_uses_automatic_owned_filtering(self) -> None:
        palette = _FakeFilamentPalette()
        exported: list[list[FilamentRecord]] = []

        def _export(
            filaments: list[FilamentRecord],
            _format_name: str,
            _output: Path | str | None,
        ) -> str:
            exported.append(filaments)
            return "owned.json"

        with patch(
            "color_tools.cli_commands.handlers.filament.export_filaments",
            side_effect=_export,
        ):
            code, stdout, _stderr = self._run(
                self._args(export="json"),
                palette,
            )

        self.assertEqual(code, 0)
        self.assertEqual(palette.filter_calls, [{"owned": None}])
        self.assertEqual(exported, [palette.records])
        self.assertIn("Exported 1 filament", stdout)

    def test_all_filaments_export_bypasses_owned_filter(self) -> None:
        palette = _FakeFilamentPalette([_filament("first"), _filament("second")])
        exported: list[list[FilamentRecord]] = []

        def _export(
            filaments: list[FilamentRecord],
            _format_name: str,
            _output: Path | str | None,
        ) -> str:
            exported.append(filaments)
            return "all.json"

        with patch(
            "color_tools.cli_commands.handlers.filament.export_filaments",
            side_effect=_export,
        ):
            code, _stdout, _stderr = self._run(
                self._args(export="json", all_filaments=True),
                palette,
            )

        self.assertEqual(code, 0)
        self.assertEqual(palette.filter_calls, [])
        self.assertEqual(exported, [palette.records])

    def test_filtered_export_forwards_every_supported_filter(self) -> None:
        palette = _FakeFilamentPalette()
        with patch(
            "color_tools.cli_commands.handlers.filament.export_filaments",
            return_value="filtered.json",
        ):
            code, _stdout, _stderr = self._run(
                self._args(
                    export="json",
                    maker=["Maker"],
                    type=["PLA"],
                    finish=["Basic"],
                    color="Red",
                    has_td=True,
                ),
                palette,
            )

        self.assertEqual(code, 0)
        self.assertEqual(
            palette.filter_calls,
            [{
                "maker": ["Maker"],
                "type_name": ["PLA"],
                "finish": ["Basic"],
                "color": "Red",
                "owned": None,
                "has_td": True,
            }],
        )

    def test_export_validation_failure_uses_stderr_and_exit_one(self) -> None:
        with patch(
            "color_tools.cli_commands.handlers.filament.export_filaments",
            side_effect=ValueError("format rejected these records"),
        ):
            code, stdout, stderr = self._run(self._args(export="hueforge"))
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("format rejected these records", stderr)

    def test_has_td_works_for_listing_counting_nearest_and_exporting(self) -> None:
        palette = _FakeFilamentPalette([
            _filament("with_td"),
            _filament("without_td", td_value=None),
        ])

        code, stdout, _stderr = self._run(self._args(has_td=True), palette)
        self.assertEqual(code, 0)
        self.assertIn("Found 1 filament", stdout)

        code, stdout, _stderr = self._run(
            self._args(has_td=True, count=True),
            palette,
        )
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "1\n")

        code, _stdout, _stderr = self._run(
            self._args(has_td=True, nearest=True, hex="#FF0000"),
            palette,
        )
        self.assertEqual(code, 0)
        assert palette.nearest_include is not None
        self.assertIs(palette.nearest_include.has_td, True)

        exported: list[list[FilamentRecord]] = []

        def _export(
            filaments: list[FilamentRecord],
            _format_name: str,
            _output: Path | str | None,
        ) -> str:
            exported.append(filaments)
            return "td.json"

        with patch(
            "color_tools.cli_commands.handlers.filament.export_filaments",
            side_effect=_export,
        ):
            code, _stdout, _stderr = self._run(
                self._args(has_td=True, export="hueforge"),
                palette,
            )
        self.assertEqual(code, 0)
        self.assertEqual([record.id for record in exported[0]], ["with_td"])

    def test_bare_count_uses_automatic_owned_filtering(self) -> None:
        palette = _FakeFilamentPalette([
            _filament("first"),
            _filament("second"),
        ])
        code, stdout, stderr = self._run(self._args(count=True), palette)

        self.assertEqual(code, 0)
        self.assertEqual(stdout, "2\n")
        self.assertEqual(stderr, "")
        self.assertEqual(
            palette.filter_calls,
            [{
                "maker": None,
                "type_name": None,
                "finish": None,
                "color": None,
                "owned": None,
                "has_td": None,
            }],
        )

    def test_count_conflicts_with_every_other_operation(self) -> None:
        conflicts: tuple[dict[str, object], ...] = (
            {"nearest": True, "hex": "#FF0000"},
            {"limit": 2},
            {"export": "json"},
            {"list_makers": True},
            {"list_types": True},
            {"list_finishes": True},
            {"list_export_formats": True},
            {"list_owned": True},
            {"add_owned": "maker_pla_red"},
            {"remove_owned": "maker_pla_red"},
            {"manage": True},
            {"gui": True},
        )
        for conflict in conflicts:
            with self.subTest(conflict=conflict):
                code, _stdout, stderr = self._run(
                    self._args(count=True, **conflict)
                )
                self.assertEqual(code, 2)
                self.assertIn("--count cannot be combined", stderr)

    def test_manager_and_gui_forward_custom_data_path(self) -> None:
        from color_tools.cli_commands.handlers.filament import (
            handle_filament_command,
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with patch(
                "color_tools.interactive_manager.run_interactive_manager"
            ) as manager:
                handle_filament_command(self._args(manage=True), path)
                manager.assert_called_once_with(json_dir=path)
            with patch(
                "color_tools.filament_manager_gui.run_filament_manager_gui"
            ) as gui:
                handle_filament_command(self._args(gui=True), path)
                gui.assert_called_once_with(json_dir=path)


if __name__ == "__main__":
    unittest.main()

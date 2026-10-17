"""Tests for standardized reconciled filament-import orchestration."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

from color_tools import FilamentImportWorkflow
from color_tools.cli_commands.handlers.filament_import import (
    handle_filament_import_command,
)
from color_tools.filament_palette import (
    FilamentRecord,
    load_filaments,
    load_owned_filaments,
)
from color_tools.importers import HueForgeImporter
from color_tools.reconcilers import (
    HueForgeFilamentReconciler,
    ImportNew,
    Skip,
    UseExisting,
)


def _system_record(
    filament_id: str = "maker-pla-basic-red",
    *,
    maker: str = "Maker",
    color: str = "Red",
) -> dict[str, object]:
    """Return one valid bundled filament fixture."""
    return {
        "id": filament_id,
        "maker": maker,
        "type": "PLA",
        "finish": "Basic",
        "color": color,
        "hex": "#ff0000",
    }


def _hueforge_record(
    *,
    brand: str = "Custom",
    name: str = "Ocean",
    owned: bool = True,
) -> dict[str, object]:
    """Return one complete HueForge filament fixture."""
    return {
        "Brand": brand,
        "Color": "#123456",
        "Name": name,
        "Owned": owned,
        "Transmissivity": 3,
        "Type": "PLA",
        "uuid": "{c4e33b80-6178-471a-bf00-6e21374ea6b4}",
    }


class _WorkflowFixture(unittest.TestCase):
    """Create an isolated effective filament database and HueForge source."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary_directory.name)
        (self.data_dir / "user").mkdir()
        (self.data_dir / "filaments.json").write_text(
            json.dumps([_system_record()]),
            encoding="utf-8",
        )
        (self.data_dir / "maker_synonyms.json").write_text(
            "{}",
            encoding="utf-8",
        )
        self.input_path = self.data_dir / "hueforge.json"
        self.input_path.write_text(
            json.dumps({"Filaments": [_hueforge_record()]}),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _workflow(self) -> FilamentImportWorkflow:
        catalog = load_filaments(self.data_dir)
        return FilamentImportWorkflow(
            HueForgeImporter(),
            HueForgeFilamentReconciler(catalog),
            data_dir=self.data_dir,
        )


class TestFilamentImportWorkflow(_WorkflowFixture):
    """Exercise the reusable importer/reconciler/exporter sequence."""

    def test_planning_is_read_only_and_apply_stages_are_independent(self) -> None:
        workflow = self._workflow()

        reconciliation = workflow.prepare(self.input_path)
        result = workflow.resolve(reconciliation)
        catalog_plan = workflow.plan_catalog(result)

        user_path = self.data_dir / "user" / "user-filaments.json"
        owned_path = self.data_dir / "user" / "owned-filaments.json"
        self.assertFalse(user_path.exists())
        self.assertFalse(owned_path.exists())
        self.assertEqual(catalog_plan.count("added"), 1)

        workflow.apply_catalog(catalog_plan)
        ownership_plan = workflow.plan_ownership(result)
        self.assertFalse(owned_path.exists())
        self.assertEqual(ownership_plan.count("added"), 1)

        workflow.apply_ownership(ownership_plan)

        self.assertTrue(user_path.exists())
        self.assertEqual(load_owned_filaments(self.data_dir), {"custom-pla-ocean"})


class TestFilamentImportCliWorkflow(_WorkflowFixture):
    """Exercise dry-run and explicitly applied CLI orchestration."""

    def _args(self, **changes: object) -> Namespace:
        values: dict[str, object] = {
            "import_format": "hueforge",
            "input_path": self.input_path,
            "resolve": None,
            "import_interactive": False,
            "problems_only": False,
            "apply_catalog": False,
            "apply_owned": False,
        }
        values.update(changes)
        return Namespace(**values)

    def test_default_is_read_only_and_prints_copyable_plan(self) -> None:
        output = io.StringIO()

        with patch("sys.stdout", output):
            handle_filament_import_command(self._args(), self.data_dir)

        self.assertIn("[0] new:custom-pla-ocean", output.getvalue())
        self.assertIn("Catalog dry run only", output.getvalue())
        self.assertFalse((self.data_dir / "user" / "user-filaments.json").exists())
        self.assertFalse((self.data_dir / "user" / "owned-filaments.json").exists())

    def test_problems_only_hides_records_that_need_no_resolution(self) -> None:
        output = io.StringIO()

        with patch("sys.stdout", output):
            handle_filament_import_command(
                self._args(problems_only=True),
                self.data_dir,
            )

        text = output.getvalue()
        self.assertIn("Reconciliation: 0 matched, 1 new, 0 ambiguous", text)
        self.assertNotIn("[0] new:custom-pla-ocean", text)

    def test_catalog_then_ownership_apply_in_one_invocation(self) -> None:
        output = io.StringIO()

        with patch("sys.stdout", output):
            handle_filament_import_command(
                self._args(apply_catalog=True, apply_owned=True),
                self.data_dir,
            )

        self.assertIn("Catalog applied: updated", output.getvalue())
        self.assertIn("Ownership applied: updated", output.getvalue())
        self.assertEqual(load_owned_filaments(self.data_dir), {"custom-pla-ocean"})

    def test_ambiguous_dry_run_prints_resolution_arguments(self) -> None:
        records = [
            _system_record("a-id", maker="Same", color="Red"),
            _system_record("b-id", maker="Same", color="Red"),
        ]
        (self.data_dir / "filaments.json").write_text(
            json.dumps(records),
            encoding="utf-8",
        )
        self.input_path.write_text(
            json.dumps(
                {
                    "Filaments": [
                        _hueforge_record(brand="Same Basic", name="Red")
                    ]
                }
            ),
            encoding="utf-8",
        )
        output = io.StringIO()

        with patch("sys.stdout", output):
            handle_filament_import_command(self._args(), self.data_dir)

        self.assertIn("--resolve 0=use:a-id", output.getvalue())
        self.assertIn("--resolve 0=use:b-id", output.getvalue())
        self.assertIn("No files were changed", output.getvalue())

    def test_problems_only_keeps_ambiguous_records_and_choices(self) -> None:
        records = [
            _system_record("a-id", maker="Same", color="Red"),
            _system_record("b-id", maker="Same", color="Red"),
        ]
        (self.data_dir / "filaments.json").write_text(
            json.dumps(records),
            encoding="utf-8",
        )
        self.input_path.write_text(
            json.dumps(
                {"Filaments": [_hueforge_record(brand="Same Basic", name="Red")]}
            ),
            encoding="utf-8",
        )
        output = io.StringIO()

        with patch("sys.stdout", output):
            handle_filament_import_command(
                self._args(problems_only=True),
                self.data_dir,
            )

        text = output.getvalue()
        self.assertIn("[0] ambiguous", text)
        self.assertIn("--resolve 0=use:a-id", text)
        self.assertIn("--resolve 0=use:b-id", text)

    def test_owned_apply_without_required_catalog_record_is_rejected(self) -> None:
        error = io.StringIO()

        with patch("sys.stdout", io.StringIO()), patch("sys.stderr", error):
            with self.assertRaises(SystemExit) as raised:
                handle_filament_import_command(
                    self._args(apply_owned=True),
                    self.data_dir,
                )

        self.assertEqual(raised.exception.code, 1)
        self.assertIn("apply the catalog first", error.getvalue())
        self.assertFalse((self.data_dir / "user" / "user-filaments.json").exists())
        self.assertFalse((self.data_dir / "user" / "owned-filaments.json").exists())

    def test_invalid_or_duplicate_resolution_is_rejected_without_writes(self) -> None:
        for resolutions in (["bad"], ["0=use:"], ["0=new", "0=skip"]):
            with self.subTest(resolutions=resolutions):
                with patch("sys.stdout", io.StringIO()), patch(
                    "sys.stderr",
                    io.StringIO(),
                ):
                    with self.assertRaises(SystemExit) as raised:
                        handle_filament_import_command(
                            self._args(
                                resolve=resolutions,
                                apply_catalog=True,
                            ),
                            self.data_dir,
                        )
                self.assertEqual(raised.exception.code, 1)
                self.assertFalse(
                    (self.data_dir / "user" / "user-filaments.json").exists()
                )

    def test_interactive_decisions_use_the_same_resolution_path(self) -> None:
        with patch(
            "color_tools.cli_commands.handlers.filament_import."
            "collect_filament_resolutions",
            return_value={},
        ) as collect, patch("sys.stdout", io.StringIO()):
            handle_filament_import_command(
                self._args(import_interactive=True),
                self.data_dir,
            )

        collect.assert_called_once()
        self.assertFalse((self.data_dir / "user" / "user-filaments.json").exists())

    def test_interactive_cancel_blocks_an_apply(self) -> None:
        with patch(
            "color_tools.cli_commands.handlers.filament_import."
            "collect_filament_resolutions",
            return_value=None,
        ), patch("sys.stdout", io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                handle_filament_import_command(
                    self._args(import_interactive=True, apply_catalog=True),
                    self.data_dir,
                )

        self.assertEqual(raised.exception.code, 1)
        self.assertFalse((self.data_dir / "user" / "user-filaments.json").exists())

    def test_interactive_cancelled_dry_run_returns_without_writing(self) -> None:
        with patch(
            "color_tools.cli_commands.handlers.filament_import."
            "collect_filament_resolutions",
            return_value=None,
        ), patch("sys.stdout", io.StringIO()):
            handle_filament_import_command(
                self._args(import_interactive=True),
                self.data_dir,
            )

        self.assertFalse((self.data_dir / "user" / "user-filaments.json").exists())

    def test_automatic_existing_match_is_reported(self) -> None:
        source = _hueforge_record(brand="Maker Basic", name="Red")
        source["Color"] = "#ff0000"
        self.input_path.write_text(
            json.dumps({"Filaments": [source]}),
            encoding="utf-8",
        )
        output = io.StringIO()

        with patch("sys.stdout", output):
            handle_filament_import_command(self._args(), self.data_dir)

        self.assertIn("use:maker-pla-basic-red", output.getvalue())
        self.assertIn("1 existing, 0 new", output.getvalue())

    def test_existing_resolution_can_update_ownership_without_catalog_write(self) -> None:
        records = [
            _system_record("a-id", maker="Same", color="Red"),
            _system_record("b-id", maker="Same", color="Red"),
        ]
        (self.data_dir / "filaments.json").write_text(
            json.dumps(records),
            encoding="utf-8",
        )
        self.input_path.write_text(
            json.dumps(
                {
                    "Filaments": [
                        _hueforge_record(brand="Same Basic", name="Red")
                    ]
                }
            ),
            encoding="utf-8",
        )

        with patch("sys.stdout", io.StringIO()):
            handle_filament_import_command(
                self._args(resolve=["0=use:a-id"], apply_owned=True),
                self.data_dir,
            )

        self.assertEqual(load_owned_filaments(self.data_dir), {"a-id"})
        self.assertFalse((self.data_dir / "user" / "user-filaments.json").exists())

    def test_unresolved_ambiguity_blocks_apply(self) -> None:
        records = [
            _system_record("a-id", maker="Same", color="Red"),
            _system_record("b-id", maker="Same", color="Red"),
        ]
        (self.data_dir / "filaments.json").write_text(
            json.dumps(records),
            encoding="utf-8",
        )
        self.input_path.write_text(
            json.dumps(
                {
                    "Filaments": [
                        _hueforge_record(brand="Same Basic", name="Red")
                    ]
                }
            ),
            encoding="utf-8",
        )

        with patch("sys.stdout", io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                handle_filament_import_command(
                    self._args(apply_catalog=True),
                    self.data_dir,
                )

        self.assertEqual(raised.exception.code, 1)


class TestFilamentReconciliationTui(unittest.TestCase):
    """Test prompt-toolkit choices independently from persistence."""

    def test_candidate_number_returns_use_existing_resolution(self) -> None:
        records = [
            FilamentRecord("a-id", "Same", "PLA", "Basic", "Red", "#ff0000"),
            FilamentRecord("b-id", "Same", "PLA", "Basic", "Red", "#ff0000"),
        ]
        source = self._source_record()
        reconciler = HueForgeFilamentReconciler(records)
        from color_tools.exporters import FilamentExportData
        from color_tools.filament_reconciliation_tui import (
            collect_filament_resolutions,
        )

        plan = reconciler.plan(FilamentExportData([source]))
        dialog = MagicMock()
        dialog.run.return_value = "use:b-id"
        with patch(
            "prompt_toolkit.shortcuts.radiolist_dialog",
            return_value=dialog,
        ) as show_dialog:
            resolutions = collect_filament_resolutions(plan)

        self.assertIsNotNone(resolutions)
        assert resolutions is not None
        self.assertEqual(resolutions[0], UseExisting("b-id"))
        values = show_dialog.call_args.kwargs["values"]
        self.assertEqual(
            values[-2:],
            [
                ("new", "Import new as same-basic-pla-red"),
                ("skip", "Skip this filament"),
            ],
        )

    def test_new_skip_and_cancel_choices(self) -> None:
        records = [
            FilamentRecord("a-id", "Same", "PLA", "Basic", "Red", "#ff0000"),
            FilamentRecord("b-id", "Same", "PLA", "Basic", "Red", "#ff0000"),
        ]
        reconciler = HueForgeFilamentReconciler(records)
        from color_tools.exporters import FilamentExportData
        from color_tools.filament_reconciliation_tui import (
            collect_filament_resolutions,
        )

        plan = reconciler.plan(FilamentExportData([self._source_record()]))
        expected = (("new", ImportNew()), ("skip", Skip()), (None, None))
        for selection, resolution in expected:
            dialog = MagicMock()
            dialog.run.return_value = selection
            with self.subTest(selection=selection), patch(
                "prompt_toolkit.shortcuts.radiolist_dialog",
                return_value=dialog,
            ), patch("sys.stdout", io.StringIO()):
                result = collect_filament_resolutions(plan)

            if resolution is None:
                self.assertIsNone(result)
            else:
                assert result is not None
                self.assertEqual(result[0], resolution)

    def test_unexpected_choice_raises_and_eof_cancels(self) -> None:
        records = [
            FilamentRecord("a-id", "Same", "PLA", "Basic", "Red", "#ff0000"),
            FilamentRecord("b-id", "Same", "PLA", "Basic", "Red", "#ff0000"),
        ]
        from color_tools.exporters import FilamentExportData
        from color_tools.filament_reconciliation_tui import (
            collect_filament_resolutions,
        )

        reconciler = HueForgeFilamentReconciler(records)
        plan = reconciler.plan(FilamentExportData([self._source_record()]))
        invalid_dialog = MagicMock()
        invalid_dialog.run.return_value = "invalid"
        with patch(
            "prompt_toolkit.shortcuts.radiolist_dialog",
            return_value=invalid_dialog,
        ), patch("sys.stdout", io.StringIO()), self.assertRaises(RuntimeError):
            collect_filament_resolutions(plan)

        cancelled_dialog = MagicMock()
        cancelled_dialog.run.side_effect = EOFError
        with patch(
            "prompt_toolkit.shortcuts.radiolist_dialog",
            return_value=cancelled_dialog,
        ), patch("sys.stdout", io.StringIO()):
            cancelled = collect_filament_resolutions(plan)
        self.assertIsNone(cancelled)

    def test_missing_dependency_and_already_resolved_paths(self) -> None:
        from color_tools.exporters import FilamentExportData
        from color_tools.filament_reconciliation_tui import (
            collect_filament_resolutions,
        )

        new_plan = HueForgeFilamentReconciler([]).plan(
            FilamentExportData([self._source_record()])
        )
        with patch(
            "color_tools.filament_reconciliation_tui.check_prompt_toolkit",
            return_value=False,
        ), patch(
            "color_tools.filament_reconciliation_tui.show_install_message"
        ) as install_message:
            self.assertIsNone(collect_filament_resolutions(new_plan))
        install_message.assert_called_once_with()

        with patch("sys.stdout", io.StringIO()):
            resolved = collect_filament_resolutions(new_plan)
        self.assertEqual(resolved, {})

    @staticmethod
    def _source_record() -> FilamentRecord:
        """Return a record producing two equally ranked candidates."""
        return FilamentRecord(
            "source",
            "Same Basic",
            "PLA",
            None,
            "Red",
            "#ff0000",
        )

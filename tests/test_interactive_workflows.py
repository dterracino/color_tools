"""Focused end-to-end logic tests for optional terminal workflows."""

from __future__ import annotations

import io
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from color_tools._interactive_utils import PROMPT_TOOLKIT_AVAILABLE
from color_tools.filament_palette import FilamentPalette, FilamentRecord
from color_tools.interactive_manager import InteractiveFilamentManager
import color_tools.interactive_wizard as wizard


class TestInteractiveWizardFlows(unittest.TestCase):
    """Exercise complete wizard decisions without requiring a terminal."""

    def test_main_menu_dispatches_every_workflow(self) -> None:
        runners = (
            "_run_color_wizard",
            "_run_filament_wizard",
            "_run_convert_wizard",
        )
        data_path = Path("test-data")
        for choice, expected_runner in enumerate(runners, 1):
            with self.subTest(choice=choice):
                with (
                    patch.object(wizard, "_ask_choice", return_value=choice),
                    patch.object(wizard, "_run_color_wizard") as color_runner,
                    patch.object(wizard, "_run_filament_wizard") as filament_runner,
                    patch.object(wizard, "_run_convert_wizard") as convert_runner,
                    patch("sys.stdout", io.StringIO()),
                ):
                    wizard.run_interactive_wizard(data_path)

            selected = {
                "_run_color_wizard": color_runner,
                "_run_filament_wizard": filament_runner,
                "_run_convert_wizard": convert_runner,
            }
            selected[expected_runner].assert_called_once_with(data_path)

    def test_main_menu_cancel_exits_successfully(self) -> None:
        with (
            patch.object(wizard, "_ask_choice", return_value=None),
            patch("sys.stdout", io.StringIO()),
            self.assertRaises(SystemExit) as raised,
        ):
            wizard.run_interactive_wizard()

        self.assertEqual(raised.exception.code, 0)

    def test_missing_prompt_toolkit_reports_install_and_exits(self) -> None:
        with (
            patch.object(wizard, "PROMPT_TOOLKIT_AVAILABLE", False),
            patch.object(wizard, "show_install_message") as show_install,
            self.assertRaises(SystemExit) as raised,
        ):
            wizard.run_interactive_wizard()

        self.assertEqual(raised.exception.code, 1)
        show_install.assert_called_once_with()

    def test_choice_retries_invalid_input(self) -> None:
        with (
            patch.object(wizard, "_pt", side_effect=["bad", "0", "2"]),
            patch("sys.stdout", io.StringIO()) as output,
        ):
            result = wizard._ask_choice("Choose", ["one", "two"])

        self.assertEqual(result, 2)
        self.assertEqual(output.getvalue().count("Please enter a number"), 2)

    def test_color_name_flow_builds_command(self) -> None:
        with (
            patch.object(wizard, "_ask_choice", return_value=1),
            patch.object(wizard, "_pt", return_value="coral"),
            patch.object(wizard, "_run_command") as run_command,
            patch("sys.stdout", io.StringIO()),
        ):
            wizard._run_color_wizard(Path("data"))

        run_command.assert_called_once_with(
            ["color", "--name", "coral"], Path("data")
        )

    def test_color_nearest_flow_returns_selected_options(self) -> None:
        def choices(_command: str, destination: str) -> list[str]:
            return {
                "space": ["rgb", "lab"],
                "metric": ["de2000", "de76"],
            }.get(destination, [])

        with (
            patch.object(wizard, "_ask_choice", side_effect=[2, 1, 2]),
            patch.object(
                wizard,
                "_ask_color_input",
                return_value=(["--value", "1", "2", "3"], "rgb(1, 2, 3)"),
            ),
            patch.object(wizard, "_get_choices", side_effect=choices),
            patch.object(wizard, "_ask_optional", return_value="cga16"),
            patch.object(wizard, "_run_command") as run_command,
            patch("sys.stdout", io.StringIO()),
        ):
            wizard._run_color_wizard()

        run_command.assert_called_once_with(
            [
                "color", "--nearest", "--value", "1", "2", "3",
                "--space", "rgb", "--metric", "de76", "--palette", "cga16",
            ],
            None,
        )

    def test_filament_flow_returns_filters_and_all_filaments(self) -> None:
        with (
            patch.object(
                wizard,
                "_ask_color_input",
                return_value=(["--hex", "#123456"], "#123456"),
            ),
            patch.object(wizard, "_get_choices", return_value=["de2000", "de94"]),
            patch.object(wizard, "_ask_choice", return_value=2),
            patch.object(
                wizard,
                "_ask_multi",
                side_effect=[["Maker"], ["PLA"], ["Matte"]],
            ),
            patch.object(wizard, "_pt", return_value="no"),
            patch.object(wizard, "_run_command") as run_command,
            patch("sys.stdout", io.StringIO()),
        ):
            wizard._run_filament_wizard(Path("data"))

        run_command.assert_called_once_with(
            [
                "filament", "--nearest", "--hex", "#123456",
                "--metric", "de94", "--maker", "Maker", "--type", "PLA",
                "--finish", "Matte", "--all-filaments",
            ],
            Path("data"),
        )

    def test_convert_flow_builds_hex_command(self) -> None:
        with (
            patch.object(wizard, "_get_choices", return_value=["rgb", "lab"]),
            patch.object(wizard, "_ask_choice", side_effect=[1, 2]),
            patch.object(
                wizard,
                "_ask_color_input",
                return_value=(["--hex", "#123456"], "#123456"),
            ),
            patch.object(wizard, "_run_command") as run_command,
            patch("sys.stdout", io.StringIO()),
        ):
            wizard._run_convert_wizard(Path("data"))

        run_command.assert_called_once_with(
            ["convert", "--to", "lab", "--hex", "#123456"],
            Path("data"),
        )


@unittest.skipUnless(PROMPT_TOOLKIT_AVAILABLE, "prompt_toolkit is not installed")
class TestInteractiveManagerWorkflows(unittest.TestCase):
    """Exercise ownership, filters, save, revert, and quit decisions."""

    def setUp(self) -> None:
        self.records = [
            FilamentRecord(
                id="maker-pla-matte-red", maker="Maker", type="PLA",
                finish="Matte", color="Red", hex="#FF0000",
            ),
            FilamentRecord(
                id="other-petg-blue", maker="Other", type="PETG",
                finish=None, color="Blue", hex="#0000FF",
            ),
        ]
        self.palette = FilamentPalette(
            self.records,
            owned_filaments={self.records[0].id},
        )
        self.application = MagicMock()
        with patch(
            "color_tools.interactive_manager.Application",
            return_value=self.application,
        ):
            self.manager = InteractiveFilamentManager(self.palette)
        self.manager._update_display = MagicMock()

    def _binding(self, key: str):
        return next(
            binding.handler
            for binding in self.manager.kb.bindings
            if binding.keys == (key,)
        )

    def _event(self) -> MagicMock:
        event = MagicMock()
        event.app = self.application
        return event

    def test_toggle_save_and_revert_owned_filaments(self) -> None:
        event = self._event()
        self._binding(" ")(event)
        self.assertNotIn(self.records[0].id, self.manager.owned_ids)
        self.assertTrue(self.manager.changes_made)

        self._binding("r")(event)
        self.assertEqual(self.manager.owned_ids, {self.records[0].id})
        self.assertFalse(self.manager.changes_made)

        self._binding(" ")(event)
        with patch.object(self.palette, "save_owned") as save_owned:
            self._binding("s")(event)
        save_owned.assert_called_once_with()
        self.assertEqual(self.palette.owned_filaments, set())
        self.assertFalse(self.manager.changes_made)

    def test_toggle_adds_an_unowned_filament(self) -> None:
        self.manager.current_index = 1

        self._binding(" ")(self._event())

        self.assertEqual(
            self.manager.owned_ids,
            {self.records[0].id, self.records[1].id},
        )
        self.assertTrue(self.manager.changes_made)

    def test_quit_confirmation_save_and_discard_paths(self) -> None:
        event = self._event()
        self.manager.changes_made = True
        self.manager.owned_ids = {self.records[1].id}

        self._binding("q")(event)
        self.assertTrue(self.manager.quit_confirm_mode)
        self.application.exit.assert_not_called()

        self._binding("escape")(event)
        self.assertFalse(self.manager.quit_confirm_mode)

        self._binding("q")(event)
        self._binding("n")(event)
        self.application.exit.assert_called_once_with()
        self.assertEqual(self.palette.owned_filaments, {self.records[0].id})

        self.application.reset_mock()
        self.manager.quit_confirm_mode = True
        with patch.object(self.palette, "save_owned") as save_owned:
            self._binding("y")(event)
        save_owned.assert_called_once_with()
        self.assertEqual(self.palette.owned_filaments, {self.records[1].id})
        self.application.exit.assert_called_once_with()

    def test_filters_support_matches_and_empty_results(self) -> None:
        self.manager.filter_maker = "other"
        self.manager._apply_filters()
        self.assertEqual(self.manager.filtered_filaments, [self.records[1]])

        self.manager.filter_color = "missing"
        self.manager._apply_filters()
        self.assertEqual(self.manager.filtered_filaments, [])
        self.assertEqual(self.manager.current_index, 0)
        self.assertEqual(self.manager.scroll_offset, 0)

        self._binding("c")(self._event())
        self.assertEqual(self.manager.filtered_filaments, self.records)

    def test_keyboard_interrupt_saves_pending_changes(self) -> None:
        self.manager.changes_made = True
        self.manager.owned_ids = {self.records[1].id}
        self.application.run.side_effect = KeyboardInterrupt

        with (
            patch.object(self.palette, "save_owned") as save_owned,
            patch.object(self.manager, "_show_exit_summary") as show_summary,
            patch("sys.stdout", io.StringIO()),
        ):
            self.manager.run()

        save_owned.assert_called_once_with()
        self.assertEqual(self.palette.owned_filaments, {self.records[1].id})
        show_summary.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()

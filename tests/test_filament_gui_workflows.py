"""Focused cancellation and failure tests for optional filament Qt workflows."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

if sys.platform != "win32":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from color_tools.filament_manager_gui import (
    PYSIDE6_AVAILABLE,
    FilamentManagerWindow,
)
from color_tools.filament_palette import FilamentPalette, FilamentRecord


@unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 is not installed")
class TestFilamentQtWorkflows(unittest.TestCase):
    """Verify dialog and manager failures without showing native UI."""

    @classmethod
    def setUpClass(cls) -> None:
        from PySide6.QtWidgets import QApplication

        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.record = FilamentRecord(
            id="maker-pla-red",
            maker="Maker",
            type="PLA",
            finish=None,
            color="Red",
            hex="#FF0000",
        )
        self.palette = FilamentPalette([self.record], owned_filaments=set())
        self.window = FilamentManagerWindow(self.palette)

    def tearDown(self) -> None:
        self.window._revert_changes()
        self.window.close()

    def test_export_dialog_cancel_and_validation_do_not_write(self) -> None:
        from color_tools.filament_export_dialog import FilamentExportDialog

        dialog = FilamentExportDialog([self.record])
        try:
            with patch(
                "color_tools.filament_export_dialog.QFileDialog.getSaveFileName",
                return_value=("", ""),
            ) as choose_file:
                dialog._export()
            choose_file.assert_called_once()
            self.assertIsNone(dialog.export_path)

            dialog.extension_input.setText("bad extension")
            with (
                patch(
                    "color_tools.filament_export_dialog.QMessageBox.warning"
                ) as warning,
                patch(
                    "color_tools.filament_export_dialog.QFileDialog.getSaveFileName"
                ) as choose_file,
            ):
                dialog._export()
            warning.assert_called_once()
            choose_file.assert_not_called()
            self.assertIsNone(dialog.export_path)
        finally:
            dialog.reject()

    def test_export_dialog_reports_invalid_template_and_write_failure(self) -> None:
        from color_tools.filament_export_dialog import FilamentExportDialog

        dialog = FilamentExportDialog([self.record])
        try:
            dialog.template_editor.setPlainText(
                "<%=loop_start%><%=unknown%><%=loop_end%>"
            )
            with patch(
                "color_tools.filament_export_dialog.QMessageBox.warning"
            ) as warning:
                dialog._export()
            self.assertEqual(warning.call_args.args[1], "Invalid export template")

            dialog.template_selector.setCurrentText("Generic JSON")
            with tempfile.TemporaryDirectory() as directory:
                destination = Path(directory) / "filaments.json"
                with (
                    patch(
                        "color_tools.filament_export_dialog.QFileDialog.getSaveFileName",
                        return_value=(str(destination), ""),
                    ),
                    patch.object(Path, "write_text", side_effect=OSError("disk full")),
                    patch(
                        "color_tools.filament_export_dialog.QMessageBox.critical"
                    ) as critical,
                ):
                    dialog._export()
            critical.assert_called_once()
            self.assertIn("disk full", critical.call_args.args[2])
            self.assertIsNone(dialog.export_path)
        finally:
            dialog.reject()

    def test_manager_export_cancel_and_missing_path_are_no_ops(self) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDialog

        item = self.window.table.item(0, 0)
        if item is None:
            self.fail("Missing owned checkbox")
        item.setCheckState(Qt.CheckState.Checked)

        with patch(
            "color_tools.filament_export_dialog.FilamentExportDialog"
        ) as dialog:
            dialog.return_value.exec.return_value = QDialog.DialogCode.Rejected
            self.window._export_owned()
            dialog.return_value.exec.return_value = QDialog.DialogCode.Accepted
            dialog.return_value.export_path = None
            self.window._export_owned()

        self.assertEqual(self.window.statusBar().currentMessage(), "")

    def test_manager_passes_empty_owned_selection_to_export_dialog(self) -> None:
        from PySide6.QtWidgets import QDialog

        with patch(
            "color_tools.filament_export_dialog.FilamentExportDialog"
        ) as dialog:
            dialog.return_value.exec.return_value = QDialog.DialogCode.Rejected
            self.window._export_owned()

        dialog.assert_called_once_with([], self.window)

    def test_save_failure_reports_error_and_keeps_pending_state(self) -> None:
        from PySide6.QtCore import Qt

        item = self.window.table.item(0, 0)
        if item is None:
            self.fail("Missing owned checkbox")
        item.setCheckState(Qt.CheckState.Checked)

        with (
            patch.object(
                self.palette, "save_owned", side_effect=OSError("read only")
            ),
            patch(
                "color_tools.filament_manager_gui.QMessageBox.critical"
            ) as critical,
        ):
            self.window._save_changes()

        critical.assert_called_once()
        self.assertNotEqual(self.window.owned_ids, self.window.original_owned_ids)
        self.assertEqual(self.palette.owned_filaments, set())
        self.assertTrue(self.window.save_button.isEnabled())

    def test_reload_cancel_and_failure_preserve_pending_changes(self) -> None:
        from PySide6.QtCore import Qt

        item = self.window.table.item(0, 0)
        if item is None:
            self.fail("Missing owned checkbox")
        item.setCheckState(Qt.CheckState.Checked)
        pending = self.window.owned_ids.copy()

        with patch.object(
            self.window, "_confirm_pending_changes", return_value=False
        ):
            self.window._reload_owned()
        self.assertEqual(self.window.owned_ids, pending)

        with (
            patch.object(
                self.window, "_confirm_pending_changes", return_value=True
            ),
            patch(
                "color_tools.filament_palette.load_owned_filaments",
                side_effect=ValueError("bad file"),
            ),
            patch(
                "color_tools.filament_manager_gui.QMessageBox.critical"
            ) as critical,
        ):
            self.window._reload_owned()
        critical.assert_called_once()
        self.assertEqual(self.window.owned_ids, pending)

    def test_close_cancel_ignores_event_without_saving(self) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QMessageBox

        item = self.window.table.item(0, 0)
        if item is None:
            self.fail("Missing owned checkbox")
        item.setCheckState(Qt.CheckState.Checked)
        event = MagicMock()

        with tempfile.TemporaryDirectory() as directory:
            self.window.save_path = Path(directory)
            with patch(
                "color_tools.filament_manager_gui.QMessageBox.question",
                return_value=QMessageBox.StandardButton.Cancel,
            ):
                self.window.closeEvent(event)

            self.assertFalse((Path(directory) / "owned-filaments.json").exists())

        event.ignore.assert_called_once_with()
        event.accept.assert_not_called()
        self.assertEqual(self.palette.owned_filaments, set())


if __name__ == "__main__":
    unittest.main()

"""Tests for the optional PySide6 filament manager."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from color_tools.filament_palette import FilamentPalette, FilamentRecord
from color_tools.filament_manager_gui import (
    PYSIDE6_AVAILABLE,
    FilamentManagerWindow,
)


@unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 is not installed")
class TestFilamentManagerWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not PYSIDE6_AVAILABLE:
            raise unittest.SkipTest("PySide6 is not installed")
        from PySide6.QtWidgets import QApplication

        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.records = [
            FilamentRecord(
                id="maker_pla-matte_basic",
                maker="Maker",
                type="PLA",
                finish="Matte",
                color="Basic",
                hex="#123456",
                td_value=0.1,
            ),
            FilamentRecord(
                id="other_petg_glossy_white",
                maker="Other",
                type="PETG",
                finish="Glossy",
                color="White",
                hex="#FFFFFF",
            ),
        ]
        self.palette = FilamentPalette(self.records, owned_filaments=set())
        self.window = FilamentManagerWindow(self.palette)

    def tearDown(self) -> None:
        self.window.close()

    def test_swatch_shows_filament_color(self) -> None:
        from PySide6.QtGui import QColor

        swatch = self.window.table.item(0, 1)
        if swatch is None:
            self.fail("The filament row has no color swatch.")
        self.assertEqual(swatch.background().color(), QColor(*self.records[0].rgb))

    def test_td_column_shows_value_or_blank(self) -> None:
        td_value = self.window.table.item(0, 6)
        missing_td = self.window.table.item(1, 6)

        if td_value is None or missing_td is None:
            self.fail("The filament table is missing a TD cell.")
        self.assertEqual(td_value.text(), "0.1")
        self.assertEqual(missing_td.text(), "")

    def test_filter_fields_hide_nonmatching_rows(self) -> None:
        self.window.filters["Maker"].setText("other")

        self.assertTrue(self.window.table.isRowHidden(0))
        self.assertFalse(self.window.table.isRowHidden(1))
        self.assertIn("1 shown of 2", self.window.summary.text())

    def test_owned_view_menu_filters_to_owned_filaments(self) -> None:
        from PySide6.QtCore import Qt

        item = self.window.table.item(0, 0)
        if item is None:
            self.fail("The filament row has no ownership checkbox.")
        item.setCheckState(Qt.CheckState.Checked)

        self.window.owned_view_action.trigger()

        self.assertFalse(self.window.table.isRowHidden(0))
        self.assertTrue(self.window.table.isRowHidden(1))
        self.assertIn("1 shown of 1", self.window.summary.text())

        self.window.all_view_action.trigger()

        self.assertFalse(self.window.table.isRowHidden(1))
        self.assertIn("2 shown of 2", self.window.summary.text())
        self.window._revert_changes()

    def test_checkbox_updates_owned_set_and_revert_restores_it(self) -> None:
        from PySide6.QtCore import Qt

        item = self.window.table.item(0, 0)
        if item is None:
            self.fail("The filament row has no ownership checkbox.")
        item.setCheckState(Qt.CheckState.Checked)
        self.assertIn(self.records[0].id, self.window.owned_ids)
        self.assertTrue(self.window.save_button.isEnabled())

        self.window.revert_button.click()

        self.assertNotIn(self.records[0].id, self.window.owned_ids)
        self.assertFalse(self.window.save_button.isEnabled())

    def test_save_writes_owned_filaments_file(self) -> None:
        from PySide6.QtCore import Qt

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "user").mkdir()
            self.window.save_path = data_dir
            item = self.window.table.item(0, 0)
            if item is None:
                self.fail("The filament row has no ownership checkbox.")
            item.setCheckState(Qt.CheckState.Checked)

            self.window.save_action.trigger()

            saved_file = data_dir / "user" / "owned-filaments.json"
            self.assertTrue(saved_file.exists())
            self.assertEqual(
                self.palette.owned_filaments,
                {self.records[0].id},
            )
            self.assertFalse(self.window.save_button.isEnabled())

    def test_reload_loads_owned_filaments_from_data_directory(self) -> None:
        from PySide6.QtCore import Qt

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            user_dir = data_dir / "user"
            user_dir.mkdir()
            owned_file = user_dir / "owned-filaments.json"
            owned_file.write_text(
                json.dumps({"owned_filaments": [self.records[0].id]}),
                encoding="utf-8",
            )
            self.window.save_path = data_dir

            self.window.reload_action.trigger()

            self.assertEqual(self.window.owned_ids, {self.records[0].id})
            self.assertEqual(
                self.palette.owned_filaments,
                {self.records[0].id},
            )
            item = self.window.table.item(0, 0)
            if item is None:
                self.fail("The filament row has no ownership checkbox.")
            self.assertEqual(item.checkState(), Qt.CheckState.Checked)
            self.assertFalse(self.window.save_action.isEnabled())

    def test_export_owned_exports_owned_records_not_filtered_rows(self) -> None:
        from PySide6.QtWidgets import QDialog
        from PySide6.QtCore import Qt

        item = self.window.table.item(0, 0)
        if item is None:
            self.fail("The filament row has no ownership checkbox.")
        item.setCheckState(Qt.CheckState.Checked)
        self.window.filters["Maker"].setText("no match")

        output_path = Path(tempfile.gettempdir()) / "owned-filaments-test.json"
        with patch(
            "color_tools.filament_export_dialog.FilamentExportDialog"
        ) as export_dialog:
            export_dialog.return_value.exec.return_value = (
                QDialog.DialogCode.Accepted
            )
            export_dialog.return_value.export_path = output_path
            self.window.export_action.trigger()

        export_dialog.assert_called_once_with([self.records[0]], self.window)
        self.assertIn(
            str(output_path),
            self.window.statusBar().currentMessage(),
        )
        self.window._revert_changes()


@unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 is not installed")
class TestFilamentExportTemplates(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from PySide6.QtWidgets import QApplication

        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.record = FilamentRecord(
            id="maker_pla-matte_basic",
            maker="Maker, Incorporated",
            type="PLA",
            finish="Matte",
            color="Basic",
            hex="#123456",
            td_value=0.1,
        )

    def test_csv_template_quotes_fields_and_repeats_records(self) -> None:
        from color_tools.filament_export_dialog import render_template

        template = (
            "maker,color,td\n"
            "<%=loop_start%>\n"
            "<%=maker%>,<%=color%>,<%=td_value%>\n"
            "<%=loop_end%>"
        )

        result = render_template(
            [self.record, self.record],
            template,
            "csv",
        )

        self.assertEqual(
            result,
            'maker,color,td\n"Maker, Incorporated",Basic,0.1\n'
            '"Maker, Incorporated",Basic,0.1',
        )

    def test_json_template_renders_valid_document(self) -> None:
        from color_tools.filament_export_dialog import render_template

        template = (
            "[\n<%=loop_start%>\n"
            "{\"maker\": <%=maker%>, \"td\": <%=td_value%>}\n"
            "<%=loop_end%>\n]"
        )

        result = render_template([self.record], template, "json")

        self.assertEqual(
            json.loads(result),
            [{"maker": "Maker, Incorporated", "td": 0.1}],
        )

    def test_template_rejects_unknown_field(self) -> None:
        from color_tools.filament_export_dialog import render_template

        with self.assertRaisesRegex(ValueError, "Unknown template field"):
            render_template(
                [self.record],
                "<%=loop_start%><%=not_a_field%><%=loop_end%>",
                "text",
            )

    def test_dialog_switches_between_editable_templates(self) -> None:
        from color_tools.filament_export_dialog import FilamentExportDialog
        from PySide6.QtGui import QFontDatabase
        from PySide6.QtWidgets import QLabel

        dialog = FilamentExportDialog([self.record])
        dialog.template_selector.setCurrentText("Generic JSON")

        fixed_font = QFontDatabase.systemFont(
            QFontDatabase.SystemFont.FixedFont
        )
        self.assertEqual(dialog.template_editor.font(), fixed_font)
        self.assertEqual(dialog.preview.font(), fixed_font)
        self.assertIn(
            "<%=loop_start%>",
            dialog.template_editor.toPlainText(),
        )
        self.assertEqual(dialog.template_editor.height(), 210)
        self.assertGreater(dialog.tag_selector.count(), 16)
        self.assertIn("<%=loop_start%>", dialog.tag_selector.itemText(0))
        self.assertIn(
            "<%=rgb[0]%>",
            [
                dialog.tag_selector.itemText(index)
                for index in range(dialog.tag_selector.count())
            ],
        )
        layout = dialog.layout()
        if layout is None:
            self.fail("The template dialog has no layout.")
        help_index = layout.indexOf(dialog.tag_help)
        editor_index = layout.indexOf(dialog.template_editor)
        preview_index = layout.indexOf(dialog.preview)
        self.assertLess(help_index, editor_index)
        self.assertLess(editor_index, preview_index)
        has_help_below_preview = False
        for index in range(preview_index + 1, layout.count()):
            item = layout.itemAt(index)
            if item is not None and isinstance(item.widget(), QLabel):
                has_help_below_preview = True
                break
        self.assertFalse(has_help_below_preview)
        self.assertEqual(dialog.extension_input.text(), "json")
        self.assertIn('"td_value"', dialog.preview.toPlainText())
        dialog.reject()

    def test_dialog_exports_valid_json_with_selected_extension(self) -> None:
        from color_tools.filament_export_dialog import FilamentExportDialog

        dialog = FilamentExportDialog([self.record])
        dialog.template_selector.setCurrentText("Generic JSON")
        with tempfile.TemporaryDirectory() as temp_dir:
            chosen_path = Path(temp_dir) / "filaments.csv"
            with patch(
                "color_tools.filament_export_dialog.QFileDialog.getSaveFileName",
                return_value=(str(chosen_path), ""),
            ):
                dialog._export()

            expected_path = chosen_path.with_suffix(".json")
            self.assertEqual(dialog.export_path, expected_path)
            with expected_path.open(encoding="utf-8") as file:
                exported = json.load(file)
        self.assertEqual(exported[0]["id"], self.record.id)

    def test_insert_tag_button_inserts_selected_tag_at_cursor(self) -> None:
        from color_tools.filament_export_dialog import FilamentExportDialog

        dialog = FilamentExportDialog([self.record])
        dialog.template_editor.setPlainText("record:")
        cursor = dialog.template_editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        dialog.template_editor.setTextCursor(cursor)
        dialog.tag_selector.setCurrentText("<%=maker%>")

        dialog.insert_tag_button.click()

        self.assertEqual(
            dialog.template_editor.toPlainText(),
            "record:<%=maker%>",
        )
        dialog.reject()

    def test_template_supports_nested_sequence_paths(self) -> None:
        from color_tools.filament_export_dialog import render_template

        rendered = render_template(
            [self.record],
            "<%=loop_start%><%=rgb[0]%>|<%=lab[1]%><%=loop_end%>",
            "text",
        )

        self.assertEqual(
            rendered,
            f"{self.record.rgb[0]}|{self.record.lab[1]}",
        )

    def test_template_applies_format_spec_to_nested_numeric_field(self) -> None:
        from color_tools.filament_export_dialog import render_template

        rendered = render_template(
            [self.record],
            "<%=loop_start%><%=lab[0]:.3f%>|<%=maker:>24%><%=loop_end%>",
            "text",
        )

        self.assertEqual(
            rendered,
            f"{self.record.lab[0]:.3f}|{'Maker, Incorporated':>24}",
        )

    def test_json_formatting_preserves_numbers_and_encodes_text(self) -> None:
        from color_tools.filament_export_dialog import render_template

        rendered = render_template(
            [self.record],
            (
                "[<%=loop_start%>{\"td\": <%=td_value:.3f%>, "
                "\"percent\": <%=td_value:.1%%>}"
                "<%=loop_end%>]"
            ),
            "json",
        )

        self.assertEqual(
            json.loads(rendered),
            [{"td": self.record.td_value, "percent": "10.0%"}],
        )

    def test_sequence_format_spec_applies_to_each_json_item(self) -> None:
        from color_tools.filament_export_dialog import render_template

        rendered = render_template(
            [self.record],
            (
                "[<%=loop_start%>{\"lab\": <%=lab:.3f%>}"
                "<%=loop_end%>]"
            ),
            "json",
        )

        result = json.loads(rendered)
        self.assertEqual(
            result[0]["lab"],
            [float(f"{component:.3f}") for component in self.record.lab],
        )
        self.assertEqual(
            rendered,
            (
                "[{\"lab\": ["
                + ", ".join(f"{component:.3f}" for component in self.record.lab)
                + "]}]"
            ),
        )

    def test_template_rejects_invalid_format_specifier(self) -> None:
        from color_tools.filament_export_dialog import render_template

        with self.assertRaisesRegex(ValueError, "Invalid format specifier"):
            render_template(
                [self.record],
                "<%=loop_start%><%=maker:.2f%><%=loop_end%>",
                "text",
            )

    def test_template_tag_highlighter_colors_tags(self) -> None:
        from PySide6.QtGui import QColor
        from color_tools.filament_export_dialog import (
            TemplateEditor,
            TemplateTagHighlighter,
        )

        editor = TemplateEditor()
        highlighter = TemplateTagHighlighter(editor.document())
        editor.setPlainText("before <%=maker%> after")
        self.application.processEvents()

        tag_ranges = editor.document().firstBlock().layout().formats()

        self.assertIsNotNone(highlighter)
        self.assertTrue(
            any(
                tag_range.format.foreground().color() == QColor("#8A2BE2")
                and tag_range.length == len("<%=maker%>")
                for tag_range in tag_ranges
            )
        )

    def test_template_editor_inserts_four_spaces_for_tab(self) -> None:
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent
        from color_tools.filament_export_dialog import TemplateEditor

        editor = TemplateEditor()
        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_Tab,
            Qt.KeyboardModifier.NoModifier,
        )

        editor.keyPressEvent(event)

        self.assertEqual(editor.toPlainText(), "    ")

    def test_template_editor_preserves_indentation_on_newline(self) -> None:
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent
        from color_tools.filament_export_dialog import TemplateEditor

        editor = TemplateEditor()
        editor.setPlainText('    {"maker": "Maker"}')
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_Return,
            Qt.KeyboardModifier.NoModifier,
            "\n",
        )

        editor.keyPressEvent(event)

        self.assertEqual(
            editor.toPlainText(),
            '    {"maker": "Maker"}\n    ',
        )


if __name__ == "__main__":
    unittest.main()

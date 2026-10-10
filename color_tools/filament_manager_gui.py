"""Optional PySide6 desktop UI for managing owned filaments."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

PYSIDE6_AVAILABLE: bool = True

if TYPE_CHECKING:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QAction, QActionGroup, QColor, QCloseEvent
    from PySide6.QtWidgets import (
        QApplication,
        QDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
    from PySide6.QtWidgets import QMainWindow as _QMainWindow
else:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QAction, QActionGroup, QColor, QCloseEvent
        from PySide6.QtWidgets import (
            QApplication,
            QDialog,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
        from PySide6.QtWidgets import QMainWindow as _QMainWindow
    except ImportError:
        PYSIDE6_AVAILABLE = False

        class _QMainWindow:
            """Fallback base used when the optional Qt bindings are absent."""

            def __init__(self) -> None:
                pass
    else:
        PYSIDE6_AVAILABLE = True

from .filament_palette import FilamentPalette

__all__ = ["PYSIDE6_AVAILABLE", "run_filament_manager_gui"]


def run_filament_manager_gui(json_dir: Path | str | None = None) -> None:
    """Open the desktop filament manager.

    Args:
        json_dir: Optional directory containing the filament JSON data files.

    Raises:
        SystemExit: If PySide6 is not installed.
    """
    if not PYSIDE6_AVAILABLE:
        print(
            "The desktop filament manager requires PySide6. "
            "Install it with: pip install color-match-tools[gui]",
            file=sys.stderr,
        )
        raise SystemExit(1)

    from .filament_palette import (
        load_filaments,
        load_maker_synonyms,
        load_owned_filaments,
    )

    if json_dir is None:
        palette = FilamentPalette.load_default()
        save_path: Path | None = None
    else:
        data_dir = Path(json_dir)
        palette = FilamentPalette(
            load_filaments(data_dir / "filaments.json"),
            load_maker_synonyms(data_dir / "maker_synonyms.json"),
            load_owned_filaments(data_dir / "user" / "owned-filaments.json"),
        )
        save_path = data_dir

    application = QApplication.instance() or QApplication(sys.argv)
    window = FilamentManagerWindow(palette, save_path)
    window.show()
    application.exec()


class FilamentManagerWindow(_QMainWindow):
    """Filter, mark, and save filaments in a color-aware desktop table."""

    def __init__(
        self,
        palette: FilamentPalette,
        save_path: Path | None = None,
    ) -> None:
        if not PYSIDE6_AVAILABLE:
            raise ImportError(
                "PySide6 is required; install color-match-tools[gui]."
            )
        super().__init__()
        self.filament_palette = palette
        self.save_path = save_path
        self.owned_ids = set(palette.owned_filaments)
        self.original_owned_ids = self.owned_ids.copy()
        self.records = sorted(
            palette.records,
            key=lambda record: (
                record.maker.casefold(),
                record.type.casefold(),
                record.color.casefold(),
            ),
        )
        self.filters: dict[str, QLineEdit] = {}
        self.table: QTableWidget
        self.summary: QLabel
        self.save_button: QPushButton
        self.revert_button: QPushButton
        self.save_action: QAction
        self.reload_action: QAction
        self.export_action: QAction
        self.owned_view_action: QAction
        self.all_view_action: QAction
        self._owned_view = False

        self.setWindowTitle("Color Tools — Owned Filament Library")
        self.resize(1100, 700)
        self._build_menus()
        self._build_ui()
        self._populate_table()
        self._apply_filters()

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self._save_changes)
        file_menu.addAction(self.save_action)

        self.reload_action = QAction("&Reload", self)
        self.reload_action.setShortcut("Ctrl+R")
        self.reload_action.triggered.connect(self._reload_owned)
        file_menu.addAction(self.reload_action)

        self.export_action = QAction("Export &Owned...", self)
        self.export_action.triggered.connect(self._export_owned)
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = self.menuBar().addMenu("&View")
        view_group = QActionGroup(self)
        view_group.setExclusive(True)

        self.owned_view_action = QAction("&Owned", self)
        self.owned_view_action.setCheckable(True)
        self.owned_view_action.toggled.connect(
            lambda checked: self._set_owned_view(True) if checked else None
        )
        view_group.addAction(self.owned_view_action)
        view_menu.addAction(self.owned_view_action)

        self.all_view_action = QAction("&All Filaments", self)
        self.all_view_action.setCheckable(True)
        self.all_view_action.setChecked(True)
        self.all_view_action.toggled.connect(
            lambda checked: self._set_owned_view(False) if checked else None
        )
        view_group.addAction(self.all_view_action)
        view_menu.addAction(self.all_view_action)

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)

        self.summary = QLabel(self)
        layout.addWidget(self.summary)

        filter_layout = QFormLayout()
        for field_name in ("Maker", "Type", "Finish", "Color"):
            field = QLineEdit(self)
            field.setClearButtonEnabled(True)
            field.textChanged.connect(self._apply_filters)
            self.filters[field_name] = field
            filter_layout.addRow(f"{field_name} contains:", field)
        layout.addLayout(filter_layout)

        self.table = QTableWidget(0, 8, self)
        self.table.setHorizontalHeaderLabels(
            [
                "Owned",
                "Swatch",
                "Maker",
                "Type",
                "Finish",
                "Color",
                "TD",
                "ID",
            ]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 65)
        self.table.setColumnWidth(1, 64)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(6, 75)
        self.table.itemChanged.connect(self._owned_state_changed)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.revert_button = QPushButton("Revert", self)
        self.revert_button.clicked.connect(self._revert_changes)
        buttons.addWidget(self.revert_button)
        clear_button = QPushButton("Clear filters", self)
        clear_button.clicked.connect(self._clear_filters)
        buttons.addWidget(clear_button)
        self.save_button = QPushButton("Save changes", self)
        self.save_button.clicked.connect(self._save_changes)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

        self.setCentralWidget(central)

    def _populate_table(self) -> None:
        self.table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            owned_item = QTableWidgetItem()
            owned_item.setFlags(
                owned_item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            owned_item.setCheckState(
                Qt.CheckState.Checked
                if record.id in self.owned_ids
                else Qt.CheckState.Unchecked
            )
            owned_item.setData(Qt.ItemDataRole.UserRole, record.id)
            self.table.setItem(row, 0, owned_item)

            swatch = QTableWidgetItem()
            swatch.setBackground(
                QColor(*record.rgb)
            )
            swatch.setToolTip(
                f"{record.color}: {record.hex}"
                + (f" / {record.hex2}" if record.hex2 else "")
            )
            self.table.setItem(row, 1, swatch)

            values = (
                record.maker,
                record.type,
                record.finish or "",
                record.color,
                "" if record.td_value is None else str(record.td_value),
                record.id,
            )
            for column, value in enumerate(values, start=2):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, record.id)
                self.table.setItem(row, column, item)
        self.table.resizeRowsToContents()

    def _owned_state_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        filament_id = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(filament_id, str):
            return
        if item.checkState() == Qt.CheckState.Checked:
            self.owned_ids.add(filament_id)
        else:
            self.owned_ids.discard(filament_id)
        self._update_summary()

    def _apply_filters(self) -> None:
        queries = {
            name: field.text().strip().casefold()
            for name, field in self.filters.items()
        }
        for row, record in enumerate(self.records):
            values = {
                "Maker": record.maker,
                "Type": record.type,
                "Finish": record.finish or "",
                "Color": record.color,
            }
            visible = all(
                not query or query in values[name].casefold()
                for name, query in queries.items()
            )
            if self._owned_view and record.id not in self.owned_ids:
                visible = False
            self.table.setRowHidden(row, not visible)
        self._update_summary()

    def _set_owned_view(self, owned_only: bool) -> None:
        self._owned_view = owned_only
        self._apply_filters()

    def _clear_filters(self) -> None:
        for field in self.filters.values():
            field.clear()

    def _update_summary(self) -> None:
        visible_count = sum(
            not self.table.isRowHidden(row)
            for row in range(self.table.rowCount())
        )
        scope_count = (
            sum(record.id in self.owned_ids for record in self.records)
            if self._owned_view
            else len(self.records)
        )
        self.summary.setText(
            f"{visible_count} shown of {scope_count} filaments"
            f"  |  {len(self.owned_ids)} owned"
        )
        changed = self.owned_ids != self.original_owned_ids
        self.save_button.setEnabled(changed)
        self.revert_button.setEnabled(changed)
        self.save_action.setEnabled(changed)

    def _save_changes(self) -> None:
        try:
            self.filament_palette.owned_filaments = self.owned_ids.copy()
            self.filament_palette.save_owned(self.save_path)
        except OSError as error:
            QMessageBox.critical(
                self,
                "Could not save owned filaments",
                str(error),
            )
            return
        self.original_owned_ids = self.owned_ids.copy()
        self._update_summary()
        self.statusBar().showMessage("Owned filaments saved.", 5000)

    def _reload_owned(self) -> None:
        if not self._confirm_pending_changes("reload"):
            return

        from .filament_palette import load_owned_filaments

        try:
            owned_ids = load_owned_filaments(self.save_path)
        except (OSError, ValueError) as error:
            QMessageBox.critical(
                self,
                "Could not reload owned filaments",
                str(error),
            )
            return

        self.owned_ids = owned_ids
        self.original_owned_ids = owned_ids.copy()
        self.filament_palette.owned_filaments = owned_ids.copy()
        self._sync_owned_checkboxes()
        self._apply_filters()
        self.statusBar().showMessage("Owned filaments reloaded.", 5000)

    def _export_owned(self) -> None:
        from .filament_export_dialog import FilamentExportDialog

        owned_records = [
            record for record in self.records
            if record.id in self.owned_ids
        ]
        dialog = FilamentExportDialog(owned_records, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.export_path is None:
            return
        self.statusBar().showMessage(
            f"Owned filaments exported to {dialog.export_path}.",
            8000,
        )

    def _revert_changes(self) -> None:
        self.owned_ids = self.original_owned_ids.copy()
        self._sync_owned_checkboxes()
        self._apply_filters()

    def _sync_owned_checkboxes(self) -> None:
        self.table.blockSignals(True)
        try:
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item is None:
                    continue
                filament_id = item.data(Qt.ItemDataRole.UserRole)
                item.setCheckState(
                    Qt.CheckState.Checked
                    if filament_id in self.owned_ids
                    else Qt.CheckState.Unchecked
                )
        finally:
            self.table.blockSignals(False)

    def _confirm_pending_changes(self, operation: str) -> bool:
        if self.owned_ids == self.original_owned_ids:
            return True

        choice = QMessageBox.question(
            self,
            "Unsaved changes",
            f"Save changes to your owned-filament list before {operation}?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if choice == QMessageBox.StandardButton.Cancel:
            return False
        if choice == QMessageBox.StandardButton.Save:
            self._save_changes()
            return self.owned_ids == self.original_owned_ids
        return True

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_pending_changes("closing"):
            event.accept()
        else:
            event.ignore()

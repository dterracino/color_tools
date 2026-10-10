"""Editable template dialog for exporting owned filament records."""

from __future__ import annotations

import csv
import io
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QFontDatabase,
    QKeyEvent,
    QSyntaxHighlighter,
    QTextDocument,
    QTextCharFormat,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .filament_palette import FilamentRecord


@dataclass(frozen=True)
class ExportTemplate:
    """A named whole-file template with its default extension and encoding."""

    name: str
    extension: str
    encoding: str
    template: str


_GENERIC_CSV = ExportTemplate(
    name="Generic CSV",
    extension="csv",
    encoding="csv",
    template=(
        "id,maker,type,finish,color,hex,hex2,td_value,owned\n"
        "<%=loop_start%>\n"
        "<%=id%>,<%=maker%>,<%=type%>,<%=finish%>,<%=color%>,<%=hex%>,"
        "<%=hex2%>,<%=td_value%>,<%=owned%>\n"
        "<%=loop_end%>"
    ),
)
_GENERIC_JSON = ExportTemplate(
    name="Generic JSON",
    extension="json",
    encoding="json",
    template=(
        "[\n"
        "<%=loop_start%>\n"
        "  {\"id\": <%=id%>, \"maker\": <%=maker%>, \"type\": <%=type%>, "
        "\"finish\": <%=finish%>, \"color\": <%=color%>, \"hex\": <%=hex%>, "
        "\"hex2\": <%=hex2%>, \"td_value\": <%=td_value%>, "
        "\"rgb\": <%=rgb%>, \"lab\": <%=lab%>, "
        "\"other_names\": <%=other_names%>, \"source\": <%=source%>, "
        "\"owned\": <%=owned%>}\n"
        "<%=loop_end%>\n"
        "]"
    ),
)
_AUTOFORGE_CSV = ExportTemplate(
    name="AutoForge CSV",
    extension="csv",
    encoding="csv",
    template=(
        "Brand,Name,TD,Color,Owned\n"
        "<%=loop_start%>\n"
        "<%=brand%>,<%=color%>,<%=td_value%>,<%=hex%>,<%=owned%>\n"
        "<%=loop_end%>"
    ),
)
_CUSTOM_TEXT = ExportTemplate(
    name="Custom text",
    extension="txt",
    encoding="text",
    template=(
        "<%=loop_start%>\n"
        "<%=maker%> <%=type%> <%=finish%> <%=color%> <%=hex%> <%=td_value%>\n"
        "<%=loop_end%>"
    ),
)
_TEMPLATES = (
    _GENERIC_CSV,
    _GENERIC_JSON,
    _AUTOFORGE_CSV,
    _CUSTOM_TEXT,
)
_FIELD_NAMES = (
    "id",
    "maker",
    "type",
    "finish",
    "color",
    "hex",
    "hex2",
    "td_value",
    "owned",
    "brand",
    "rgb",
    "lab",
    "other_names",
    "source",
)
_TEMPLATE_TAGS = ("loop_start", "loop_end", *_FIELD_NAMES)
_TAG_PATTERN = re.compile(r"<%=(.*?)%>")
_JSON_NUMBER_PATTERN = re.compile(
    r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?"
)
_PATH_ROOT_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PATH_PART_PATTERN = re.compile(
    r"\.([A-Za-z_][A-Za-z0-9_]*)|\[(\d+|\"(?:\\.|[^\"\\])*\")\]"
)
_TAG_HIGHLIGHT_PATTERN = re.compile(r"<%=(.*?)%>")
_LOOP_PATTERN = re.compile(
    r"<%=loop_start%>(.*?)<%=loop_end%>",
    re.S,
)


class TemplateEditor(QPlainTextEdit):
    """Plain-text editor with four-space tabs and automatic line indentation."""

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Tab:
            cursor = self.textCursor()
            cursor.insertText("    ")
            self.setTextCursor(cursor)
            return

        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            cursor = self.textCursor()
            cursor.removeSelectedText()
            line_prefix = cursor.block().text()[:cursor.positionInBlock()]
            indentation = re.match(r"[ \t]*", line_prefix)
            spaces = (
                indentation.group().replace("\t", "    ")
                if indentation is not None
                else ""
            )
            cursor.insertText(f"\n{spaces}")
            self.setTextCursor(cursor)
            return

        super().keyPressEvent(event)


class TemplateTagHighlighter(QSyntaxHighlighter):
    """Highlight template tags without coupling tag syntax to the editor widget."""

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self._tag_format = QTextCharFormat()
        self._tag_format.setForeground(QColor("#8A2BE2"))
        self._tag_format.setFontWeight(700)

    def highlightBlock(self, text: str) -> None:
        for match in _TAG_HIGHLIGHT_PATTERN.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self._tag_format)


def _field_values(record: FilamentRecord) -> dict[str, object]:
    """Return raw values available to template field tags."""
    return {
        "id": record.id,
        "maker": record.maker,
        "type": record.type,
        "finish": record.finish,
        "color": record.color,
        "hex": record.hex,
        "hex2": record.hex2,
        "td_value": record.td_value,
        "owned": True,
        "rgb": record.rgb,
        "lab": record.lab,
        "other_names": record.other_names,
        "source": record.source,
        "brand": " ".join(
            part for part in (record.maker, record.type, record.finish) if part
        ),
    }


def _nested_tag_names(value: object, path: str) -> set[str]:
    """Discover data-only child paths for the tag selector."""
    result: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in cast(
            Mapping[object, object],
            value,
        ).items():
            if isinstance(key, str):
                child_path = f"{path}[{json.dumps(key, ensure_ascii=False)}]"
                result.add(child_path)
                result.update(_nested_tag_names(child, child_path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, child in enumerate(cast(Sequence[object], value)):
            child_path = f"{path}[{index}]"
            result.add(child_path)
            result.update(_nested_tag_names(child, child_path))
    elif is_dataclass(value) and not isinstance(value, type):
        for item in fields(value):
            if not item.name.startswith("_"):
                child_path = f"{path}.{item.name}"
                result.add(child_path)
                result.update(
                    _nested_tag_names(
                        cast(object, getattr(value, item.name)),
                        child_path,
                    )
                )
    elif hasattr(value, "__dict__"):
        for name, child in cast(dict[str, object], vars(value)).items():
            if not name.startswith("_") and not callable(child):
                child_path = f"{path}.{name}"
                result.add(child_path)
                result.update(_nested_tag_names(child, child_path))
    return result


def _available_template_tags(
    records: list[FilamentRecord],
) -> tuple[str, ...]:
    """Return loop tags, top-level fields, and nested paths found in records."""
    names: set[str] = {str(name) for name in _TEMPLATE_TAGS}
    for record in records:
        for name, value in _field_values(record).items():
            names.update(_nested_tag_names(value, name))
    return tuple(
        [name for name in _TEMPLATE_TAGS]
        + sorted(names.difference(_TEMPLATE_TAGS))
    )


def _resolve_path(path: str, values: dict[str, object]) -> object:
    """Resolve a simple data path without evaluating arbitrary expressions."""
    root_match = _PATH_ROOT_PATTERN.match(path)
    if root_match is None:
        raise ValueError(f"Invalid template path: {path}")
    root = root_match.group()
    try:
        value = values[root]
    except KeyError:
        raise ValueError(f"Unknown template field: {root}") from None

    position = root_match.end()
    while position < len(path):
        part_match = _PATH_PART_PATTERN.match(path, position)
        if part_match is None:
            raise ValueError(f"Invalid template path: {path}")
        attribute, index_or_key = part_match.groups()
        if attribute is not None:
            if attribute.startswith("_"):
                raise ValueError("Template paths cannot access private fields.")
            if isinstance(value, Mapping):
                try:
                    value = cast(Mapping[str, object], value)[attribute]
                except KeyError:
                    raise ValueError(
                        f"Unknown template property: {path[:part_match.end()]}"
                    ) from None
            else:
                try:
                    value = cast(object, getattr(value, attribute))
                except AttributeError:
                    raise ValueError(
                        f"Unknown template property: {path[:part_match.end()]}"
                    ) from None
                if callable(value):
                    raise ValueError("Template paths cannot access methods.")
        elif index_or_key is not None:
            if index_or_key.startswith('"'):
                key = cast(str, json.loads(index_or_key))
                if not isinstance(value, Mapping):
                    raise ValueError(
                        f"Template path is not a mapping: {path[:part_match.end()]}"
                    )
                try:
                    value = cast(Mapping[str, object], value)[key]
                except KeyError:
                    raise ValueError(
                        f"Unknown template key: {path[:part_match.end()]}"
                    ) from None
            else:
                if not isinstance(value, Sequence) or isinstance(value, bytes):
                    raise ValueError(
                        f"Template path is not an indexable sequence: "
                        f"{path[:part_match.end()]}"
                    )
                index = int(index_or_key)
                try:
                    value = cast(Sequence[object], value)[index]
                except IndexError:
                    raise ValueError(
                        f"Template index is out of range: {path[:part_match.end()]}"
                    ) from None
        position = part_match.end()
    return value


def _encode_value(value: object, encoding: str) -> str:
    """Encode one resolved template value for its output format."""
    if encoding == "json":
        return json.dumps(value, ensure_ascii=False)
    if encoding == "csv":
        output = io.StringIO(newline="")
        csv.writer(output).writerow(["" if value is None else value])
        return output.getvalue().removesuffix("\r\n")
    return "" if value is None else str(value)


def _split_tag_format(expression: str) -> tuple[str, str | None]:
    """Split a tag path from its optional format spec outside quoted keys."""
    bracket_depth = 0
    in_string = False
    escaped = False
    for index, character in enumerate(expression):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"' and bracket_depth:
            in_string = True
        elif character == "[":
            bracket_depth += 1
        elif character == "]":
            bracket_depth -= 1
        elif character == ":" and bracket_depth == 0:
            return expression[:index], expression[index + 1:]
    return expression, None


def _render_tag(expression: str, values: dict[str, object], encoding: str) -> str:
    """Resolve and encode one path, optionally applying a Python format spec."""
    path, format_spec = _split_tag_format(expression)
    value = _resolve_path(path, values)
    if format_spec is None:
        return _encode_value(value, encoding)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        formatted_items: list[str] = []
        for item in cast(Sequence[object], value):
            try:
                formatted_item = format(item, format_spec)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid format specifier for {path}: {error}"
                ) from error
            if (
                encoding == "json"
                and isinstance(item, (int, float))
                and not isinstance(item, bool)
                and _JSON_NUMBER_PATTERN.fullmatch(formatted_item)
            ):
                formatted_items.append(formatted_item)
            else:
                formatted_items.append(
                    json.dumps(formatted_item, ensure_ascii=False)
                    if encoding == "json"
                    else formatted_item
                )
        if encoding == "json":
            return f"[{', '.join(formatted_items)}]"
        return _encode_value(
            ", ".join(formatted_items),
            encoding,
        )

    try:
        formatted = format(value, format_spec)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Invalid format specifier for {path}: {error}"
        ) from error

    if (
        encoding == "json"
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and _JSON_NUMBER_PATTERN.fullmatch(formatted)
    ):
        return formatted
    return _encode_value(formatted, encoding)


def render_template(
    records: list[FilamentRecord],
    template: str,
    encoding: str,
) -> str:
    """Render a whole-file template with a repeated-filament block."""
    matches = list(_LOOP_PATTERN.finditer(template))
    if len(matches) != 1:
        raise ValueError(
            "Template must contain exactly one "
            "<%=loop_start%>...<%=loop_end%> block."
        )

    match = matches[0]
    record_template = match.group(1).strip("\r\n")
    rendered_records: list[str] = []
    for record in records:
        values = _field_values(record)

        def replace(match: re.Match[str]) -> str:
            return _render_tag(
                match.group(1),
                values,
                encoding,
            )

        rendered_records.append(
            _TAG_PATTERN.sub(replace, record_template)
        )

    separator = ",\n" if encoding == "json" else "\n"
    output = (
        template[:match.start()]
        + separator.join(rendered_records)
        + template[match.end():]
    )
    if encoding == "json":
        try:
            json.loads(output)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Rendered template is not valid JSON: {error.msg}"
            ) from error
    return output


class FilamentExportDialog(QDialog):
    """Configure and write a custom export of owned filament records."""

    def __init__(
        self,
        records: list[FilamentRecord],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.records = records
        self.export_path: Path | None = None
        self.setWindowTitle("Export Owned Filaments")
        self.resize(760, 720)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.template_selector = QComboBox(self)
        self.template_selector.addItems(
            [template.name for template in _TEMPLATES]
        )
        self.extension_input = QLineEdit(self)
        form.addRow("Template:", self.template_selector)
        form.addRow("File extension:", self.extension_input)
        layout.addLayout(form)

        layout.addWidget(QLabel("Whole-file template:", self))
        layout.addWidget(
            QLabel(
                "Use <%=loop_start%> and <%=loop_end%> around repeated "
                "records. Insert a tag at the cursor with the selector.",
                self,
            )
        )
        self.tag_help = QLabel(
            "Field tags: "
            + ", ".join(f"<%={name}%>" for name in _FIELD_NAMES)
            + ". Nested fields can use .property, [index], or [\"key\"]. "
            "Add :format_spec to a tag, e.g. <%=lab[0]:.3f%>.",
            self,
        )
        self.tag_help.setWordWrap(True)
        layout.addWidget(self.tag_help)
        tag_controls = QHBoxLayout()
        self.tag_selector = QComboBox(self)
        self.tag_selector.setObjectName("templateTagSelector")
        self.tag_selector.addItems(
            [
                f"<%={name}%>"
                for name in _available_template_tags(records)
            ]
        )
        tag_controls.addWidget(self.tag_selector)
        self.insert_tag_button = QPushButton("Insert tag", self)
        self.insert_tag_button.setObjectName("insertTemplateTagButton")
        self.insert_tag_button.clicked.connect(self._insert_selected_tag)
        tag_controls.addWidget(self.insert_tag_button)
        tag_controls.addStretch()
        layout.addLayout(tag_controls)

        template_font = QFontDatabase.systemFont(
            QFontDatabase.SystemFont.FixedFont
        )
        self.template_editor = TemplateEditor(self)
        self.template_editor.setFont(template_font)
        self.template_editor.setTabChangesFocus(False)
        self.template_editor.setFixedHeight(210)
        self.template_highlighter = TemplateTagHighlighter(
            self.template_editor.document()
        )
        layout.addWidget(self.template_editor)
        self.preview = TemplateEditor(self)
        self.preview.setFont(template_font)
        self.preview.setReadOnly(True)
        self.preview.setTabChangesFocus(False)
        self.preview.setMaximumHeight(145)
        layout.addWidget(QLabel("Preview (first 3 owned filaments):", self))
        layout.addWidget(self.preview)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_button = QPushButton("Cancel", self)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button)
        export_button = QPushButton("Export...", self)
        export_button.clicked.connect(self._export)
        buttons.addWidget(export_button)
        layout.addLayout(buttons)

        self.template_selector.currentIndexChanged.connect(
            self._load_selected_template
        )
        self.template_editor.textChanged.connect(self._update_preview)
        self._load_selected_template()

    def _selected_template(self) -> ExportTemplate:
        return _TEMPLATES[self.template_selector.currentIndex()]

    def _insert_selected_tag(self) -> None:
        self.template_editor.insertPlainText(self.tag_selector.currentText())
        self.template_editor.setFocus()

    def _load_selected_template(self) -> None:
        template = self._selected_template()
        self.extension_input.setText(template.extension)
        self.template_editor.setPlainText(template.template)
        self._update_preview()

    def _update_preview(self) -> None:
        template = self._selected_template()
        try:
            preview = render_template(
                self.records[:3],
                self.template_editor.toPlainText(),
                template.encoding,
            )
        except ValueError as error:
            self.preview.setPlainText(str(error))
            return
        self.preview.setPlainText(preview)

    def _export(self) -> None:
        extension = self.extension_input.text().strip().lstrip(".")
        if not extension or not re.fullmatch(r"[A-Za-z0-9]+", extension):
            QMessageBox.warning(
                self,
                "Invalid file extension",
                "Enter a file extension using letters and numbers only.",
            )
            return

        template = self._selected_template()
        try:
            content = render_template(
                self.records,
                self.template_editor.toPlainText(),
                template.encoding,
            )
        except ValueError as error:
            QMessageBox.warning(self, "Invalid export template", str(error))
            return

        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Owned Filaments",
            f"owned-filaments.{extension}",
            f"{extension.upper()} files (*.{extension});;All files (*)",
        )
        if not selected_path:
            return

        output_path = Path(selected_path).with_suffix(f".{extension}")
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8", newline="\n")
        except OSError as error:
            QMessageBox.critical(
                self,
                "Could not export owned filaments",
                str(error),
            )
            return

        self.export_path = output_path
        self.accept()

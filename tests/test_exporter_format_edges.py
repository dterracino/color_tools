"""Edge-case coverage for structured palette and filament exporters."""

from __future__ import annotations

import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Protocol, cast

from color_tools.exporters.hueforge_exporter import HueForgeExporter
from color_tools.exporters.kpl_exporter import KPLExporter
from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.palette_metadata import PaletteMetadata
from color_tools.exporters.python_exporter import (
    PythonExporter,
    PythonExportOptions,
    Representation,
    ValueFormat,
)
from color_tools.filament_palette import FilamentRecord
from color_tools.palette import ColorRecord


class _KPLExporterProtocol(Protocol):
    DEFAULT_COLUMNS: int

    def export_colors(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None = None,
    ) -> str: ...

    def export_palette(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None = None,
    ) -> str: ...

    def _build_colorset_xml(
        self,
        *,
        colors: list[ColorRecord],
        name: str,
        description: str,
        columns: int,
    ) -> bytes: ...

    def _default_column_count(self, color_count: int) -> int: ...

    def _write_kpl(
        self,
        *,
        colors: list[ColorRecord],
        path: Path,
        name: str,
        description: str,
        columns: int,
    ) -> str: ...


class _PythonExporterProtocol(Protocol):
    def _build_palette(
        self,
        *,
        colors: list[ColorRecord],
        options: PythonExportOptions,
    ) -> str: ...

    def _build_module(
        self,
        *,
        colors: list[ColorRecord],
        metadata: PaletteMetadata | None,
        options: PythonExportOptions,
    ) -> str: ...

    def _format_rgb(
        self,
        *,
        rgb: tuple[int, int, int],
        options: PythonExportOptions,
    ) -> str: ...

    def _make_constant_identifiers(
        self,
        colors: list[ColorRecord],
    ) -> list[str]: ...


def _colors() -> list[ColorRecord]:
    """Return records with names that exercise escaping and deduplication."""
    return [
        ColorRecord.from_rgb((255, 0, 0), name="O'Red"),
        ColorRecord.from_rgb((0, 255, 0), name="O'Red"),
        ColorRecord.from_rgb((0, 0, 255), name=""),
    ]


class TestKPLExporterEdges(unittest.TestCase):
    """Cover KPL defaults, optional metadata, and malformed layout values."""

    def setUp(self) -> None:
        self.exporter = cast(_KPLExporterProtocol, KPLExporter())
        self.colors = _colors()

    def _read_root(self, path: Path) -> ET.Element:
        with zipfile.ZipFile(path) as archive:
            return ET.fromstring(archive.read("colorset.xml"))

    def test_color_export_derives_name_and_small_grid_from_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "derived-name.kpl"
            self.exporter.export_colors(self.colors, path)
            root = self._read_root(path)

        self.assertEqual(root.attrib["name"], "derived-name")
        self.assertEqual(root.attrib["columns"], "3")
        self.assertEqual(root.attrib["rows"], "1")
        self.assertEqual(root[2].attrib["name"], "Color 3")

    def test_palette_accepts_zero_or_none_as_unspecified_columns(self) -> None:
        for columns in (0, None):
            with self.subTest(columns=columns):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "fallback.kpl"
                    palette = PaletteExportData(
                        self.colors,
                        PaletteMetadata(columns=columns),
                    )
                    self.exporter.export_palette(palette, path)
                    root = self._read_root(path)

                self.assertEqual(root.attrib["name"], "fallback")
                self.assertEqual(root.attrib["comment"], "")
                self.assertEqual(root.attrib["columns"], "3")

    def test_palette_uses_positive_columns_and_metadata_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ignored.kpl"
            palette = PaletteExportData(
                self.colors,
                PaletteMetadata(
                    name="Named palette",
                    description="A description",
                    columns=2,
                ),
            )
            self.exporter.export_palette(palette, path)
            root = self._read_root(path)

        self.assertEqual(root.attrib["name"], "Named palette")
        self.assertEqual(root.attrib["comment"], "A description")
        self.assertEqual(root.attrib["columns"], "2")
        self.assertEqual(root.attrib["rows"], "2")

    def test_empty_palette_uses_one_column_and_zero_rows(self) -> None:
        xml = self.exporter._build_colorset_xml(
            colors=[],
            name="Empty",
            description="",
            columns=self.exporter._default_column_count(0),
        )
        root = ET.fromstring(xml)
        self.assertEqual(root.attrib["columns"], "1")
        self.assertEqual(root.attrib["rows"], "0")

    def test_large_palette_caps_default_columns(self) -> None:
        self.assertEqual(
            self.exporter._default_column_count(100),
            self.exporter.DEFAULT_COLUMNS,
        )

    def test_writer_rejects_nonpositive_columns_before_creating_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.kpl"
            with self.assertRaisesRegex(ValueError, "at least 1"):
                self.exporter._write_kpl(
                    colors=self.colors,
                    path=path,
                    name="Invalid",
                    description="",
                    columns=0,
                )
            self.assertFalse(path.exists())


class TestPythonExporterEdges(unittest.TestCase):
    """Cover validation and output branches not exercised by happy paths."""

    def setUp(self) -> None:
        self.exporter = cast(_PythonExporterProtocol, PythonExporter())
        self.colors = _colors()

    def test_options_reject_each_invalid_combination(self) -> None:
        cases = (
            (lambda: PythonExportOptions(
                representation=cast(Representation, "set")
            ), "representation"),
            (lambda: PythonExportOptions(
                value_format=cast(ValueFormat, "hsl")
            ), "value format"),
            (lambda: PythonExportOptions(variable_name=""), "must not be empty"),
            (lambda: PythonExportOptions(variable_name="not valid"), "Invalid"),
            (lambda: PythonExportOptions(variable_name="class"), "keyword"),
            (lambda: PythonExportOptions(precision=-1), "zero or greater"),
            (lambda: PythonExportOptions(
                value_format="hex", normalized=True
            ), "normalized"),
            (lambda: PythonExportOptions(
                value_format="hex", include_alpha=True
            ), "include_alpha"),
        )
        for factory, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    factory()

    def test_dict_quotes_names_deduplicates_and_falls_back_to_hex(self) -> None:
        source = self.exporter._build_palette(
            colors=self.colors,
            options=PythonExportOptions(),
        )
        self.assertIn('"O\'Red"', source)
        self.assertIn('"O\'Red 2"', source)
        self.assertIn("'#0000FF'", source)

    def test_sequence_can_omit_names_and_sanitize_multiline_comments(self) -> None:
        multiline = replace(self.colors[0], name="First\nSecond")
        with_comments = self.exporter._build_palette(
            colors=[multiline],
            options=PythonExportOptions(representation="list"),
        )
        without_comments = self.exporter._build_palette(
            colors=[multiline],
            options=PythonExportOptions(
                representation="tuple",
                include_names_as_comments=False,
            ),
        )
        self.assertIn("# First Second", with_comments)
        self.assertNotIn("#", without_comments)

    def test_integer_rgba_and_zero_precision_normalized_values(self) -> None:
        integer = self.exporter._format_rgb(
            rgb=(1, 2, 3),
            options=PythonExportOptions(include_alpha=True),
        )
        normalized = self.exporter._format_rgb(
            rgb=(255, 0, 128),
            options=PythonExportOptions(normalized=True, precision=0),
        )
        self.assertEqual(integer, "(1, 2, 3, 255)")
        self.assertEqual(normalized, "(1, 0, 1)")

    def test_palette_metadata_can_be_omitted(self) -> None:
        source = self.exporter._build_module(
            colors=self.colors,
            metadata=PaletteMetadata(name="Hidden"),
            options=PythonExportOptions(include_metadata=False),
        )
        self.assertNotIn("METADATA", source)
        self.assertNotIn("Hidden", source)

    def test_empty_metadata_is_not_emitted(self) -> None:
        source = self.exporter._build_module(
            colors=[],
            metadata=PaletteMetadata(),
            options=PythonExportOptions(),
        )
        self.assertNotIn("METADATA", source)
        self.assertIn("PALETTE: dict", source)

    def test_empty_constants_output_remains_valid_python(self) -> None:
        source = self.exporter._build_module(
            colors=[],
            metadata=None,
            options=PythonExportOptions(representation="constants"),
        )
        compile(source, "empty_palette.py", "exec")

    def test_constant_identifier_handles_empty_keyword_and_duplicates(self) -> None:
        colors = [
            replace(self.colors[0], name="!!!"),
            replace(self.colors[1], name="class"),
            replace(self.colors[2], name="class"),
        ]
        self.assertEqual(
            self.exporter._make_constant_identifiers(colors),
            ["COLOR", "_CLASS", "_CLASS_2"],
        )


class TestHueForgeErrorPreviews(unittest.TestCase):
    """Ensure long validation diagnostics are bounded but informative."""

    @staticmethod
    def _filament(identifier: str, *, td_value: float | None) -> FilamentRecord:
        return FilamentRecord(
            id=identifier,
            maker="Maker",
            type="PLA",
            finish=None,
            color=identifier,
            hex="#123456",
            td_value=td_value,
            source="test.json",
        )

    def test_more_than_three_duplicate_ids_append_ellipsis(self) -> None:
        filaments: list[FilamentRecord] = []
        for identifier in ("a", "b", "c", "d"):
            filaments.extend(
                [self._filament(identifier, td_value=1.0)] * 2
            )

        with self.assertRaisesRegex(
            ValueError,
            r"4 duplicate ID\(s\): a, b, c, \.\.\.",
        ):
            HueForgeExporter().export_filaments(filaments)

    def test_more_than_three_missing_td_records_append_ellipsis(self) -> None:
        filaments = [
            self._filament(identifier, td_value=None)
            for identifier in ("a", "b", "c", "d")
        ]

        with self.assertRaisesRegex(
            ValueError,
            r"4 selected filament\(s\).*a, b, c, \.\.\.",
        ):
            HueForgeExporter().export_filaments(filaments)


if __name__ == "__main__":
    unittest.main()

"""Tests for palette importer registration, detection, and parsing."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from color_tools.exporters import get_exporter
from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.palette_metadata import PaletteMetadata
from color_tools.importers import (
    detect_importer,
    get_importer,
    import_palette,
    list_import_formats,
)
from tests.test_exporters_palette_formats import _make_test_colors


class ImporterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.colors = _make_test_colors()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.output_directory = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def output_path(self, filename: str) -> Path:
        return self.output_directory / "nested" / filename


class TestImporterRegistry(ImporterTestCase):
    def test_import_formats_are_registered(self) -> None:
        formats = list_import_formats(available_only=False)

        self.assertTrue(
            {"gpl", "hex", "jasc_pal", "riff_pal"}.issubset(formats)
        )

    def test_detect_importer_distinguishes_jasc_pal(self) -> None:
        path = self.output_path("palette.pal")
        get_exporter("pal").export_colors(self.colors, path)

        importer = detect_importer(path)

        self.assertEqual(importer.metadata.name, "jasc_pal")

    def test_detect_importer_distinguishes_riff_pal(self) -> None:
        path = self.output_path("palette_riff.pal")
        get_exporter("riff_pal").export_colors(self.colors, path)

        importer = detect_importer(path)

        self.assertEqual(importer.metadata.name, "riff_pal")

    def test_explicit_importer_lookup_returns_gpl(self) -> None:
        importer = get_importer("gpl")
        self.assertEqual(importer.metadata.name, "gpl")

    def test_explicit_importer_lookup_returns_riff_pal(self) -> None:
        importer = get_importer("riff_pal")
        self.assertEqual(importer.metadata.name, "riff_pal")


class TestPaletteImporters(ImporterTestCase):
    def test_gpl_importer_recovers_exported_metadata(self) -> None:
        path = self.output_path("palette.gpl")
        palette = PaletteExportData(
            self.colors,
            PaletteMetadata(
                name="Primary Colors",
                author="Color Tools",
                description="Bright RGB primaries",
                columns=2,
                tags=("bright", "rgb"),
            ),
        )

        get_exporter("gpl").export_palette(palette, path)
        imported = import_palette(path)

        self.assertEqual(imported.metadata.name, "Primary Colors")
        self.assertEqual(imported.metadata.author, "Color Tools")
        self.assertEqual(
            imported.metadata.description,
            "Bright RGB primaries",
        )
        self.assertEqual(imported.metadata.columns, 2)
        self.assertEqual(imported.metadata.tags, ("bright", "rgb"))
        self.assertEqual(imported.colors[0].rgb, (255, 0, 0))

    def test_hex_importer_accepts_comments_and_hash_prefixed_colors(
        self,
    ) -> None:
        path = self.output_path("palette.hex")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "; exported palette\n"
            "# comment line\n"
            "FF0000\n"
            "#00FF00\n"
            "0000ff\n",
            encoding="utf-8",
        )

        imported = import_palette(path)

        self.assertEqual(
            [color.hex for color in imported.colors],
            ["#FF0000", "#00FF00", "#0000FF"],
        )
        self.assertEqual(
            [color.name for color in imported.colors],
            ["#FF0000", "#00FF00", "#0000FF"],
        )

    def test_jasc_pal_importer_round_trips_exported_palette(self) -> None:
        path = self.output_path("palette.pal")
        get_exporter("pal").export_colors(self.colors, path)

        imported = import_palette(path)

        self.assertEqual(len(imported.colors), 3)
        self.assertEqual(
            [color.rgb for color in imported.colors],
            [(255, 0, 0), (0, 255, 0), (0, 0, 255)],
        )
        self.assertEqual(imported.metadata.name, "")

    def test_riff_pal_importer_round_trips_exported_palette(self) -> None:
        path = self.output_path("palette_riff.pal")
        get_exporter("riff_pal").export_colors(self.colors, path)

        imported = import_palette(path)

        self.assertEqual(len(imported.colors), 3)
        self.assertEqual(
            [color.rgb for color in imported.colors],
            [(255, 0, 0), (0, 255, 0), (0, 0, 255)],
        )
        self.assertEqual(
            [color.name for color in imported.colors],
            ["#FF0000", "#00FF00", "#0000FF"],
        )

    def test_riff_pal_importer_rejects_jasc_content(self) -> None:
        path = self.output_path("not_riff.pal")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "JASC-PAL\n"
            "0100\n"
            "1\n"
            "255 0 0\n",
            encoding="ascii",
        )

        importer = get_importer("riff_pal")

        self.assertFalse(importer.can_import(path))


if __name__ == "__main__":
    unittest.main()

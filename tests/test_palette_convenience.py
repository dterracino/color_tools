"""Tests for palette construction and format-independent export."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from color_tools import (
    ColorRecord,
    Palette,
    PaletteExportData,
    PaletteMetadata,
    export_palette,
    lab_to_lch,
    rgb_to_hsl,
    rgb_to_lab,
)
from color_tools.exporters import PaintNetExportOptions, get_exporter


class TestPaletteFactories(unittest.TestCase):
    def test_record_derived_values(self) -> None:
        rgb = (255, 127, 80)
        record = ColorRecord.from_rgb(rgb)
        self.assertEqual(record.name, "Color 1")
        self.assertEqual(record.source, "custom")
        self.assertEqual(record.hex, "#FF7F50")
        self.assertEqual(record.hsl, rgb_to_hsl(rgb))
        self.assertEqual(record.lab, rgb_to_lab(rgb))
        self.assertEqual(record.lch, lab_to_lch(record.lab))

    def test_hex_forms(self) -> None:
        for value in ("#f00", "f00", "#FF0000", "ff0000"):
            with self.subTest(value=value):
                self.assertEqual(ColorRecord.from_hex(value).rgb, (255, 0, 0))
        for value in ("", "#", "##f00", "#ffff", "gg0000", " ff0000"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ColorRecord.from_hex(value)

    def test_invalid_rgb(self) -> None:
        for rgb in ((-1, 0, 0), (256, 0, 0), (True, 0, 0), (1.0, 0, 0),
                    (1, 2), (1, 2, 3, 4)):
            with self.subTest(rgb=rgb), self.assertRaises(ValueError):
                ColorRecord.from_rgb(rgb)  # type: ignore[arg-type]

    def test_order_duplicates_and_indexing(self) -> None:
        colors = [(255, 0, 0), (0, 0, 0), (255, 0, 0)]
        palette = Palette.from_rgb(iter(colors), source="example")
        self.assertEqual([record.rgb for record in palette.records], colors)
        self.assertEqual(
            [record.name for record in palette.records],
            ["Color 1", "Color 2", "Color 3"],
        )
        self.assertEqual(palette.find_by_name("Color 2"), palette.records[1])
        self.assertEqual(palette.find_by_rgb((0, 0, 0)), palette.records[1])
        self.assertTrue(all(record.source == "example" for record in palette.records))
        self.assertEqual(Palette.from_rgb([]).records, [])
        self.assertEqual(Palette.from_hex([]).records, [])

    def test_names_prefix_and_hex_palette(self) -> None:
        palette = Palette.from_hex(["#f00", "00f"], names=iter(["Accent", "Ink"]))
        self.assertEqual([record.name for record in palette.records], ["Accent", "Ink"])
        self.assertEqual(palette.records[1].hex, "#0000FF")
        self.assertEqual(
            Palette.from_rgb([(0, 0, 0)], name_prefix="Swatch").records[0].name,
            "Swatch 1",
        )
        with self.assertRaises(ValueError):
            Palette.from_rgb([(0, 0, 0)], names=[])
        with self.assertRaises(ValueError):
            Palette.from_hex(["#f00"], names=["A", "B"])

    def test_builtin_auto_naming(self) -> None:
        self.assertEqual(ColorRecord.from_rgb((255, 0, 0), auto_name=True).name, "red")
        self.assertEqual(ColorRecord.from_hex("#00f", auto_name=True).name, "blue")
        palette = Palette.from_hex(["#f00", "#00f"], auto_name=True)
        self.assertEqual([record.name for record in palette.records], ["red", "blue"])

    def test_naming_context_and_explicit_precedence(self) -> None:
        colors = [(255, 10, 10), (255, 20, 20)]
        with patch("color_tools.naming.generate_color_name", return_value=("warm", "generated")) as namer:
            palette = Palette.from_rgb(colors, auto_name=True)
            self.assertEqual([record.name for record in palette.records], ["warm", "warm"])
            self.assertEqual(namer.call_count, 2)
            for call in namer.call_args_list:
                self.assertEqual(call.kwargs["palette_colors"], colors)
            namer.reset_mock()
            Palette.from_rgb(colors, names=["A", "B"], auto_name=True)
            ColorRecord.from_rgb(colors[0], name="Explicit", auto_name=True)
            ColorRecord.from_hex("#f00", name="Explicit", auto_name=True)
            namer.assert_not_called()


class TestExportPalette(unittest.TestCase):
    def test_gpl_metadata_and_order(self) -> None:
        palette = Palette.from_rgb([(255, 0, 0), (0, 0, 255)])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.gpl"
            result = export_palette(
                palette, "GPL", path,
                metadata=PaletteMetadata(name="Custom", author="Dave", columns=2),
            )
            self.assertEqual(result, str(path))
            text = path.read_text(encoding="utf-8")
            self.assertIn("Name: Custom", text)
            self.assertIn("Columns: 2", text)
            self.assertLess(text.index("Color 1"), text.index("Color 2"))

    def test_wrapper_and_metadata_fallback(self) -> None:
        data = PaletteExportData(
            colors=Palette.from_hex(["#f00", "#00f"]).records,
            metadata=PaletteMetadata(name="Custom"),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.hex"
            export_palette(data, "hex", path)
            direct_path = Path(directory) / "direct.hex"
            get_exporter("hex").export_colors(data.colors, direct_path)
            self.assertEqual(path.read_bytes(), direct_path.read_bytes())

    def test_errors(self) -> None:
        palette = Palette.from_hex(["#f00"])
        with self.assertRaises(ValueError):
            export_palette(palette, "unknown")
        with self.assertRaises(ValueError):
            export_palette(palette, "autoforge")
        with self.assertRaises(ValueError):
            export_palette(PaletteExportData(palette.records), "gpl",
                           metadata=PaletteMetadata(name="Conflict"))
        with self.assertRaises(TypeError):
            export_palette(palette, "gpl", options=PaintNetExportOptions())

    def test_options_and_generated_path_are_forwarded(self) -> None:
        palette = Palette.from_hex(["#f00"])
        options = PaintNetExportOptions()
        with patch("color_tools.export.get_exporter") as lookup:
            exporter = lookup.return_value
            exporter.export_palette.return_value = "generated.txt"
            self.assertEqual(export_palette(palette, "paintnet", options=options),
                             "generated.txt")
            data, path, passed_options = exporter.export_palette.call_args.args
            self.assertIs(data.colors, palette.records)
            self.assertIsNone(path)
            self.assertIs(passed_options, options)


if __name__ == "__main__":
    unittest.main()

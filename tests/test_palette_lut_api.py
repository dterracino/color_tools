"""Tests for the Palette.save_lut_png convenience API."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from color_tools.palette import Palette
from color_tools.png_writer import SimplePNGWriter

RED = (255, 0, 0)
GREEN = (0, 255, 0)


class TestPaletteSaveLutPng(unittest.TestCase):
    def test_saves_exact_lut_in_palette_order_with_duplicates(self) -> None:
        palette = Palette.from_rgb([RED, GREEN, RED])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "palette.png"
            result = palette.save_lut_png(path)
            self.assertEqual(result, path)
            self.assertEqual(
                path.read_bytes(),
                SimplePNGWriter([RED, GREEN, RED]).to_bytes(),
            )

    def test_accepts_string_path_and_returns_path(self) -> None:
        palette = Palette.from_rgb([RED])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "palette.png"
            result = palette.save_lut_png(str(path))
            self.assertIsInstance(result, Path)
            self.assertEqual(result, path)
            self.assertTrue(path.is_file())

    def test_delegates_to_registered_palette_lut_exporter(self) -> None:
        palette = Palette.from_rgb([RED, GREEN])
        path = Path("palette.png")
        with patch("color_tools.exporters.get_exporter") as get_exporter:
            exporter = get_exporter.return_value
            exporter.export_colors.return_value = str(path)
            result = palette.save_lut_png(path)

        get_exporter.assert_called_once_with("palette_lut")
        exporter.export_colors.assert_called_once_with(palette.records, path)
        self.assertEqual(result, path)

    def test_empty_palette_preserves_exporter_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.png"
            with self.assertRaisesRegex(ValueError, "colors must not be empty"):
                Palette([]).save_lut_png(path)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()

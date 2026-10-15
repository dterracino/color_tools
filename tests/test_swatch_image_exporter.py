"""Layout and failure-path tests for PNG swatch-sheet export."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Protocol, cast
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

from color_tools.exporters.export_options_base import ExportOptionsBase
from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.palette_metadata import PaletteMetadata
from color_tools.exporters.swatch_image_exporter import (
    SwatchImageExporter,
    SwatchImageOptions,
)
from color_tools.palette import ColorRecord


class _SwatchExporterProtocol(Protocol):
    IMAGE_WIDTH: int
    OUTER_MARGIN: int
    CARD_WIDTH: int
    CARD_GAP: int

    def export_colors(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None = None,
        options: ExportOptionsBase | None = None,
    ) -> str: ...

    def export_palette(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None = None,
        options: ExportOptionsBase | None = None,
    ) -> str: ...

    def _build_value_lines(
        self,
        color: ColorRecord,
        options: SwatchImageOptions,
    ) -> list[tuple[str, str]]: ...

    def _value_line_count(self, options: SwatchImageOptions) -> int: ...

    def _calculate_card_height(self, value_line_count: int) -> int: ...

    def _calculate_columns(self) -> int: ...

    def _fit_text(
        self,
        *,
        draw: object,
        text: str,
        font: object,
        max_width: int,
    ) -> str: ...

    def _wrap_text(
        self,
        *,
        draw: object,
        text: str,
        font: object,
        max_width: int,
    ) -> list[str]: ...

    def _create_font(self, *, preferred: str, size: int) -> object: ...


def _color(index: int = 0, *, name: str | None = None) -> ColorRecord:
    """Create a stable test color with every derived color space populated."""
    return ColorRecord.from_rgb(
        ((index * 47) % 256, (index * 83) % 256, (index * 131) % 256),
        name=name or f"Color {index + 1}",
    )


class TestSwatchImageExporter(unittest.TestCase):
    """Exercise adaptive layout, labels, fonts, and I/O errors."""

    def setUp(self) -> None:
        self.exporter = cast(_SwatchExporterProtocol, SwatchImageExporter())

    def test_all_optional_value_labels_are_formatted(self) -> None:
        options = SwatchImageOptions(
            show_hex=True,
            show_rgb=True,
            show_hsl=True,
            show_lab=True,
            show_lch=True,
        )
        lines = self.exporter._build_value_lines(_color(1), options)

        self.assertEqual(
            [label for label, _value in lines],
            ["HEX", "RGB", "HSL", "Lab", "LCh"],
        )
        self.assertEqual(self.exporter._value_line_count(options), 5)
        self.assertGreater(
            self.exporter._calculate_card_height(5),
            self.exporter._calculate_card_height(0),
        )

    def test_no_value_labels_produces_no_value_rows(self) -> None:
        options = SwatchImageOptions(
            show_index=False,
            show_hex=False,
            show_rgb=False,
            show_hsl=False,
            show_lab=False,
            show_lch=False,
        )
        self.assertEqual(self.exporter._build_value_lines(_color(), options), [])
        self.assertEqual(self.exporter._value_line_count(options), 0)

    def test_label_and_no_label_modes_render_different_images(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            labeled_path = Path(directory) / "labeled.png"
            plain_path = Path(directory) / "plain.png"
            color = _color(2, name="A very long color name for fitting")

            self.exporter.export_colors([color], labeled_path)
            self.exporter.export_colors(
                [color],
                plain_path,
                SwatchImageOptions(show_index=False, show_hex=False),
            )

            with Image.open(labeled_path) as labeled_image:
                labeled_size = labeled_image.size
                labeled_bytes = labeled_image.tobytes()
            with Image.open(plain_path) as plain_image:
                plain_size = plain_image.size
                plain_bytes = plain_image.tobytes()

        self.assertGreater(labeled_size[1], plain_size[1])
        self.assertNotEqual(labeled_bytes, plain_bytes)

    def test_palette_header_wraps_and_multiple_rows_expand_height(self) -> None:
        colors = [_color(index) for index in range(6)]
        palette = PaletteExportData(
            colors,
            PaletteMetadata(
                name="Test Palette",
                description=" ".join(["long description"] * 80),
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "palette.png"
            result = self.exporter.export_palette(palette, path)
            with Image.open(path) as image:
                width, height = image.size

        self.assertEqual(result, str(path))
        self.assertEqual(width, self.exporter.IMAGE_WIDTH)
        self.assertGreater(height, self.exporter._calculate_card_height(1) * 2)

    def test_layout_never_calculates_fewer_than_one_column(self) -> None:
        exporter = cast(_SwatchExporterProtocol, SwatchImageExporter())
        original_width = exporter.IMAGE_WIDTH
        try:
            exporter.IMAGE_WIDTH = 1
            self.assertEqual(exporter._calculate_columns(), 1)
        finally:
            exporter.IMAGE_WIDTH = original_width

    def test_wrapping_and_ellipsis_respect_rendered_width(self) -> None:
        image = Image.new("RGB", (200, 100))
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=14)

        lines = self.exporter._wrap_text(
            draw=draw,
            text="alpha beta gamma",
            font=font,
            max_width=45,
        )
        fitted = self.exporter._fit_text(
            draw=draw,
            text="a name that is much too long",
            font=font,
            max_width=45,
        )

        self.assertGreater(len(lines), 1)
        self.assertTrue(fitted.endswith("…"))
        self.assertLess(len(fitted), len("a name that is much too long"))
        self.assertEqual(
            self.exporter._wrap_text(
                draw=draw,
                text="   ",
                font=font,
                max_width=45,
            ),
            [],
        )

    def test_font_loader_falls_back_when_preferred_font_is_missing(self) -> None:
        fallback = object()
        with (
            patch("PIL.ImageFont.truetype", side_effect=OSError),
            patch("PIL.ImageFont.load_default", return_value=fallback) as load_default,
        ):
            result = self.exporter._create_font(
                preferred="missing.ttf",
                size=23,
            )

        self.assertIs(result, fallback)
        load_default.assert_called_once_with(size=23)

    def test_empty_palette_fails_before_output_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.png"
            with self.assertRaisesRegex(ValueError, "at least one color"):
                self.exporter.export_colors([], path)
            self.assertFalse(path.exists())

    def test_file_write_errors_are_propagated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "failed.png"
            with patch("PIL.Image.Image.save", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    self.exporter.export_colors([_color()], path)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()

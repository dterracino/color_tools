"""Watermark helper, validation, and dependency-error tests."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from typing import TYPE_CHECKING, cast
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageFont

from color_tools.image import (
    IMAGE_AVAILABLE,
    add_image_watermark,
    add_svg_watermark,
    add_text_watermark,
)
from color_tools.image.watermark import (
    _calculate_position,
    _get_fonts_directory,
    _load_font,
)

if TYPE_CHECKING:
    from color_tools.image.watermark import Position


@unittest.skipUnless(IMAGE_AVAILABLE, "Watermarking requires Pillow")
class TestSVGWatermarkErrors(unittest.TestCase):
    """SVG validation and dependency errors do not require a working Cairo."""

    def setUp(self) -> None:
        self.test_image = Image.new("RGB", (40, 30), color="white")

    def test_invalid_svg_opacity_raises_before_import(self) -> None:
        for opacity in (-0.1, 1.1, float("nan"), float("inf")):
            with self.subTest(opacity=opacity):
                with self.assertRaisesRegex(ValueError, "opacity"):
                    add_svg_watermark(
                        self.test_image,
                        svg_path="unused.svg",
                        opacity=opacity,
                    )

    def test_nonpositive_svg_scale_raises_before_import(self) -> None:
        for scale in (0.0, -0.1, float("nan"), float("inf")):
            with self.subTest(scale=scale):
                with self.assertRaisesRegex(ValueError, "scale"):
                    add_svg_watermark(
                        self.test_image,
                        svg_path="unused.svg",
                        scale=scale,
                    )

    def test_missing_cairosvg_preserves_import_error(self) -> None:
        failure = ImportError("missing CairoSVG", name="cairosvg")
        with patch("builtins.__import__", side_effect=failure):
            with self.assertRaises(ImportError) as raised:
                add_svg_watermark(self.test_image, svg_path="unused.svg")

        self.assertIs(raised.exception.__cause__, failure)
        self.assertIn("native Cairo library", str(raised.exception))

    def test_missing_native_cairo_preserves_os_error(self) -> None:
        failure = OSError("native Cairo library not found")
        with patch("builtins.__import__", side_effect=failure):
            with self.assertRaises(ImportError) as raised:
                add_svg_watermark(self.test_image, svg_path="unused.svg")

        self.assertIs(raised.exception.__cause__, failure)
        self.assertIn("native Cairo library", str(raised.exception))

    def test_missing_svg_output_raises_runtime_error(self) -> None:
        fake_cairosvg = ModuleType("cairosvg")

        def _no_png(**_kwargs: object) -> None:
            return None

        setattr(fake_cairosvg, "svg2png", _no_png)
        with patch.dict(sys.modules, {"cairosvg": fake_cairosvg}):
            with self.assertRaisesRegex(RuntimeError, "no PNG data"):
                add_svg_watermark(self.test_image, svg_path="unused.svg")


@unittest.skipUnless(IMAGE_AVAILABLE, "Watermarking requires Pillow")
class TestCalculatePosition(unittest.TestCase):
    """Position presets and errors have stable, actionable behavior."""

    def test_custom_tuple_returned_directly(self) -> None:
        result = _calculate_position((400, 300), (100, 50), (25, 75))
        self.assertEqual(result, (25, 75))

    def test_position_presets(self) -> None:
        expected: dict[Position, tuple[int, int]] = {
            "top-left": (10, 10),
            "top-center": (150, 10),
            "top-right": (290, 10),
            "center-left": (10, 125),
            "center": (150, 125),
            "center-right": (290, 125),
            "bottom-left": (10, 240),
            "bottom-center": (150, 240),
            "bottom-right": (290, 240),
        }
        for position, coordinates in expected.items():
            with self.subTest(position=position):
                self.assertEqual(
                    _calculate_position((400, 300), (100, 50), position),
                    coordinates,
                )

    def test_custom_margin(self) -> None:
        self.assertEqual(
            _calculate_position(
                (400, 300),
                (100, 50),
                "bottom-center",
                margin=5,
            ),
            (150, 245),
        )

    def test_invalid_position_raises(self) -> None:
        invalid_position = cast("Position", "invalid-position")
        with self.assertRaisesRegex(ValueError, "Expected one of"):
            _calculate_position((400, 300), (100, 50), invalid_position)


@unittest.skipUnless(IMAGE_AVAILABLE, "Watermarking requires Pillow")
class TestLoadFont(unittest.TestCase):
    """Font selection errors retain useful context."""

    def test_both_font_name_and_file_raises(self) -> None:
        with self.assertRaises(ValueError):
            _load_font(font_name="Arial", font_file="somefont.ttf")

    def test_missing_font_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            _load_font(font_file="/nonexistent/path/font.ttf")

    def test_invalid_font_file_preserves_cause(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            font_path = Path(directory) / "invalid.ttf"
            font_path.write_bytes(b"not a font")
            with self.assertRaises(ValueError) as raised:
                _load_font(font_file=str(font_path))
        self.assertIsNotNone(raised.exception.__cause__)

    def test_default_fallback_returns_font(self) -> None:
        font = _load_font()
        self.assertIsInstance(
            font,
            (ImageFont.FreeTypeFont, ImageFont.ImageFont),
        )

    def test_font_file_in_fonts_directory(self) -> None:
        font_files = list(_get_fonts_directory().glob("*.ttf"))
        font_files.extend(_get_fonts_directory().glob("*.otf"))
        if not font_files:
            self.skipTest("No bundled fonts available")
        font = _load_font(font_file=font_files[0].name, size=12)
        self.assertIsInstance(font, ImageFont.FreeTypeFont)


@unittest.skipUnless(IMAGE_AVAILABLE, "Watermarking requires Pillow")
class TestWatermarkPixelEffects(unittest.TestCase):
    """Watermark functions preserve image-level output contracts."""

    def setUp(self) -> None:
        self.base = Image.new("RGBA", (200, 100), (200, 200, 200, 255))

    def test_opacity_zero_leaves_pixels_unchanged(self) -> None:
        result = add_text_watermark(
            self.base,
            text="INVISIBLE",
            position="center",
            opacity=0.0,
        )
        self.assertTrue(
            np.array_equal(
                np.asarray(self.base.convert("RGBA")),
                np.asarray(result),
            )
        )

    def test_output_preserves_base_size(self) -> None:
        result = add_text_watermark(self.base, text="SIZE")
        self.assertEqual(result.size, self.base.size)

    def test_output_is_always_rgba(self) -> None:
        for mode in ("RGB", "RGBA", "L"):
            image = Image.new(mode, (100, 80), 128)
            result = add_text_watermark(image, text="M")
            self.assertEqual(result.mode, "RGBA")

    def test_watermark_path_accepts_path_and_string(self) -> None:
        watermark = Image.new("RGBA", (20, 20), (255, 0, 0, 128))
        descriptor, path_text = tempfile.mkstemp(suffix=".png")
        os.close(descriptor)
        path = Path(path_text)
        try:
            watermark.save(path)
            for target in (path, str(path)):
                with self.subTest(target_type=type(target).__name__):
                    result = add_image_watermark(
                        self.base,
                        watermark_path=target,
                    )
                    self.assertIsInstance(result, Image.Image)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

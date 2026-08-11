"""Tests for the swatch image generation tool."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.generate_swatch_image import (
    create_hue_wheel_palette,
    generate_swatch_image,
)


class TestGenerateSwatchImage(unittest.TestCase):
    """Verify generated palettes and rendered swatch images."""

    def test_create_eight_color_palette(self) -> None:
        """Create eight complete, distinct palette records."""
        colors = create_hue_wheel_palette((224, 90, 71))

        self.assertEqual(len(colors), 8)
        self.assertEqual(len({color.rgb for color in colors}), 8)
        self.assertTrue(all(color.hex.startswith("#") for color in colors))
        self.assertTrue(all(not color.name[:1].isdigit() for color in colors))
        self.assertTrue(all(color.source == "generated-swatch" for color in colors))

    def test_generate_swatch_png(self) -> None:
        """Render a generated palette through the swatch image exporter."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "swatch.png"

            result = generate_swatch_image(
                base_rgb=(224, 90, 71),
                color_count=8,
                palette_name="Test LCH Wheel",
                output_path=output_path,
            )

            self.assertEqual(result, output_path)
            self.assertTrue(result.is_file())
            self.assertEqual(result.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()

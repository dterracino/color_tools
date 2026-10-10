"""Tests for the static-image naive NES baseline."""

from __future__ import annotations

from io import StringIO
import unittest

import numpy as np
from color_tools import load_palette
from numpy.typing import NDArray
from rich.console import Console

from demos.naive_nes_processor import process_naive_nes
from demos.shader_demo_layout import fit_integer_viewport, initial_window_size


class TestNaiveNesProcessor(unittest.TestCase):
    """Verify palette, framebuffer, dithering, and progress contracts."""

    @staticmethod
    def _gradient() -> NDArray[np.uint8]:
        """Build a colorful non-4:3 source image."""
        x = np.linspace(0, 255, 320, dtype=np.uint8)
        y = np.linspace(0, 255, 180, dtype=np.uint8)
        frame = np.empty((180, 320, 3), dtype=np.uint8)
        frame[:, :, 0] = x[np.newaxis, :]
        frame[:, :, 1] = y[:, np.newaxis]
        frame[:, :, 2] = 255 - frame[:, :, 0] // 2
        return frame

    @staticmethod
    def _console() -> tuple[Console, StringIO]:
        """Create a deterministic non-terminal Rich console."""
        output = StringIO()
        return Console(file=output, force_terminal=False, width=120), output

    def test_output_is_exact_nes_frame_with_at_most_25_colors(self) -> None:
        """Every output pixel should be one of the bundled NES colors."""
        console, output = self._console()
        result = process_naive_nes(self._gradient(), 0.75, console=console)

        self.assertEqual(result.frame.shape, (240, 256, 3))
        self.assertEqual(result.source_color_count, 25)
        self.assertEqual(result.allowed_color_count, 25)
        self.assertLessEqual(result.nes_color_count, 25)

        output_colors = {
            tuple(int(channel) for channel in color)
            for color in np.unique(np.reshape(result.frame, (-1, 3)), axis=0)
        }
        nes_colors = {record.rgb for record in load_palette("nes").records}
        self.assertTrue(output_colors.issubset(nes_colors))
        self.assertIn("Mapped source into an exact 256x240 framebuffer", output.getvalue())
        self.assertIn("Applying two-candidate grid-aligned dithering", output.getvalue())

    def test_dither_argument_changes_only_nes_palette_pixels(self) -> None:
        """Full dithering should differ from nearest-only quantization."""
        console, _ = self._console()
        plain = process_naive_nes(self._gradient(), 0.0, console=console)
        dithered = process_naive_nes(self._gradient(), 1.0, console=console)

        self.assertFalse(np.array_equal(plain.frame, dithered.frame))
        self.assertLessEqual(dithered.nes_color_count, 25)

    def test_integer_viewport_uses_uniform_texel_blocks(self) -> None:
        """The default naive viewport should map every texel to 5×4 pixels."""
        window = initial_window_size(1.0, naive_nes=True)
        viewport = fit_integer_viewport(window)

        self.assertEqual(window, (1280, 960))
        self.assertEqual(viewport, (0, 0, 1280, 960))
        self.assertEqual(viewport[2] % 256, 0)
        self.assertEqual(viewport[3] % 240, 0)


if __name__ == "__main__":
    unittest.main()

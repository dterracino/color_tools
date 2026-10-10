"""Integration tests for the palette texture batch-export utility."""

from __future__ import annotations

import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "demos"
    / "generate_palette_textures.py"
)


class TestGeneratePaletteTextures(unittest.TestCase):
    """Exercise the utility through its public command-line boundary."""

    def test_exports_shader_ready_png_and_glsl(self) -> None:
        """The batch wrapper should create canonical exporter artifacts."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--palette",
                    "gameboy",
                    "--output",
                    str(output_dir),
                    "--glsl",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            png_path = output_dir / "gameboy.png"
            glsl_path = output_dir / "gameboy.glsl"
            self.assertTrue(png_path.is_file())
            self.assertTrue(glsl_path.is_file())

            png_data = png_path.read_bytes()
            self.assertEqual(png_data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", png_data[16:24]), (4, 1))
            self.assertIn(
                "const vec3 PALETTE[4]",
                glsl_path.read_text(encoding="utf-8"),
            )

    def test_lists_every_bundled_palette(self) -> None:
        """List mode should expose palettes beyond the original short list."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--list"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("apple2", result.stdout)
        self.assertIn("nes", result.stdout)
        self.assertIn("vga", result.stdout)


if __name__ == "__main__":
    unittest.main()

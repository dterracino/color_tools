"""Tests for dependency-free ColorRecord and FilamentRecord swatches."""

from __future__ import annotations

from dataclasses import asdict, fields
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Literal, cast
import unittest

from color_tools import config_context
from color_tools.filament_palette import FilamentRecord
from color_tools.palette import ColorRecord
from color_tools.png_writer import SimplePNGWriter

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
type _Mode = Literal["solid", "blocks", "gradient"]


def _filament(hex_code: str = "#f00-#0f0-#00f") -> FilamentRecord:
    """Create a focused filament fixture."""
    return FilamentRecord(
        id="probe",
        maker="Example",
        type="PLA",
        finish=None,
        color="Probe",
        hex=hex_code,
    )


class TestColorRecordSwatches(unittest.TestCase):
    def setUp(self) -> None:
        self.record = ColorRecord.from_rgb((12, 34, 56), name="Probe")

    def test_default_is_64_pixel_solid_png(self) -> None:
        expected = SimplePNGWriter.from_solid(
            self.record.rgb, width=64, height=64
        ).to_bytes()
        self.assertEqual(self.record.to_swatch_png(), expected)

    def test_every_mode_is_solid(self) -> None:
        expected = SimplePNGWriter.from_solid(
            self.record.rgb, width=5, height=3
        ).to_bytes()
        for mode in ("solid", "blocks", "gradient"):
            with self.subTest(mode=mode):
                self.assertEqual(
                    self.record.to_swatch_png(width=5, height=3, mode=mode),
                    expected,
                )

    def test_save_returns_path_and_creates_parents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "color.png"
            result = self.record.save_swatch_png(path, width=7, height=4)
            self.assertEqual(result, path)
            self.assertEqual(
                path.read_bytes(),
                self.record.to_swatch_png(width=7, height=4),
            )


class TestFilamentRecordSwatches(unittest.TestCase):
    def test_solid_uses_captured_effective_rgb(self) -> None:
        with config_context(multi_color_mode="last"):
            record = _filament()
        with config_context(multi_color_mode="first"):
            actual = record.to_swatch_png(width=5, height=3)
        expected = SimplePNGWriter.from_solid(BLUE, width=5, height=3).to_bytes()
        self.assertEqual(actual, expected)

    def test_blocks_use_original_component_order(self) -> None:
        with config_context(multi_color_mode="last"):
            record = _filament()
        expected = SimplePNGWriter.from_blocks(
            [RED, GREEN, BLUE], width=8, height=2
        ).to_bytes()
        self.assertEqual(
            record.to_swatch_png(width=8, height=2, mode="blocks"),
            expected,
        )

    def test_gradient_uses_original_component_order(self) -> None:
        with config_context(multi_color_mode="last"):
            record = _filament()
        expected = SimplePNGWriter.from_gradient(
            [RED, GREEN, BLUE], width=7, height=2
        ).to_bytes()
        self.assertEqual(
            record.to_swatch_png(width=7, height=2, mode="gradient"),
            expected,
        )

    def test_single_component_is_solid_in_every_mode(self) -> None:
        record = _filament("#123456")
        expected = SimplePNGWriter.from_solid(
            record.rgb, width=3, height=2
        ).to_bytes()
        for mode in ("solid", "blocks", "gradient"):
            with self.subTest(mode=mode):
                self.assertEqual(
                    record.to_swatch_png(width=3, height=2, mode=mode),
                    expected,
                )

    def test_save_returns_path_and_exact_mode_output(self) -> None:
        record = _filament()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "filament.png"
            result = record.save_swatch_png(
                str(path), width=7, height=3, mode="gradient"
            )
            self.assertEqual(result, path)
            self.assertEqual(
                path.read_bytes(),
                record.to_swatch_png(width=7, height=3, mode="gradient"),
            )


class TestRecordSwatchValidation(unittest.TestCase):
    def test_unknown_modes_are_rejected(self) -> None:
        records = (ColorRecord.from_rgb(RED), _filament())
        for record in records:
            with self.subTest(record=type(record).__name__):
                with self.assertRaisesRegex(ValueError, "solid.*blocks.*gradient"):
                    record.to_swatch_png(mode=cast(_Mode, "unknown"))

    def test_dimensions_reuse_writer_validation(self) -> None:
        record = _filament()
        for name, value in (("width", True), ("height", 0)):
            with self.subTest(name=name, value=value):
                arguments = {"width": 2, "height": 2, name: value}
                with self.assertRaisesRegex(ValueError, name):
                    record.to_swatch_png(
                        width=cast(int, arguments["width"]),
                        height=cast(int, arguments["height"]),
                    )

    def test_blocks_reject_width_that_would_omit_components(self) -> None:
        with self.assertRaisesRegex(ValueError, "number of colors"):
            _filament().to_swatch_png(width=2, height=1, mode="blocks")

    def test_narrow_multi_color_gradient_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "width of at least 2"):
            _filament().to_swatch_png(width=1, height=1, mode="gradient")

    def test_methods_do_not_change_dataclass_serialization(self) -> None:
        color = ColorRecord.from_rgb(RED)
        filament = _filament()
        for record in (color, filament):
            with self.subTest(record=type(record).__name__):
                names = {item.name for item in fields(record)}
                serialized = asdict(record)
                self.assertNotIn("swatch", names)
                self.assertNotIn("swatch", serialized)
                self.assertNotIn("to_swatch_png", serialized)
                self.assertNotIn("save_swatch_png", serialized)

    def test_record_swatches_work_without_optional_image_dependencies(self) -> None:
        code = """
import importlib.abc
import importlib.util
import sys

class BlockOptionalImages(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {'PIL', 'numpy'}:
            return importlib.util.spec_from_loader(fullname, self)
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        raise ImportError(module.__name__)

sys.meta_path.insert(0, BlockOptionalImages())
from color_tools.filament_palette import FilamentRecord
from color_tools.palette import ColorRecord

color = ColorRecord.from_rgb((1, 2, 3))
filament = FilamentRecord(
    id='probe', maker='Example', type='PLA', finish=None,
    color='Probe', hex='#f00-#00f',
)
assert color.to_swatch_png().startswith(b'\\x89PNG')
assert filament.to_swatch_png(mode='blocks').startswith(b'\\x89PNG')
assert 'PIL' not in sys.modules
assert 'numpy' not in sys.modules
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

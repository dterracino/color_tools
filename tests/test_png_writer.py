"""
Tests for color_tools.png_writer.SimplePNGWriter.

Standard-library only (unittest), apart from an optional cross-check against
Pillow that is skipped when Pillow is not installed. Includes a tiny independent
PNG decoder so the round trip does not rely on the writer's own code paths.
"""

from __future__ import annotations

import io
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

from color_tools.png_writer import RGB, SimplePNGWriter

if TYPE_CHECKING:
    from PIL import Image

    _have_pillow = True
else:
    try:
        from PIL import Image
    except ImportError:
        _have_pillow = False
    else:
        _have_pillow = True
HAVE_PILLOW = _have_pillow

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def parse_chunks(png: bytes) -> list[tuple[bytes, bytes]]:
    """Split a PNG into (type, data) chunks, verifying every CRC along the way."""
    assert png[:8] == SIGNATURE, "bad signature"
    chunks: list[tuple[bytes, bytes]] = []
    pos = 8
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos : pos + 4])
        chunk_type = png[pos + 4 : pos + 8]
        data = png[pos + 8 : pos + 8 + length]
        (crc,) = struct.unpack(">I", png[pos + 8 + length : pos + 12 + length])
        assert crc == zlib.crc32(chunk_type + data), f"bad CRC in {chunk_type!r}"
        chunks.append((chunk_type, data))
        pos += 12 + length
    assert pos == len(png), "trailing bytes after last chunk"
    return chunks


def decode_pixels(png: bytes) -> list[list[tuple[int, int, int]]]:
    """Decode an 8-bit RGB, non-interlaced, filter-type-0 PNG into rows of pixels."""
    chunks = parse_chunks(png)
    ihdr = dict(chunks)[b"IHDR"]
    width, height, depth, color_type, comp, filt, interlace = struct.unpack(
        ">IIBBBBB", ihdr
    )
    assert (depth, color_type, comp, filt, interlace) == (8, 2, 0, 0, 0)
    raw = zlib.decompress(b"".join(d for t, d in chunks if t == b"IDAT"))
    stride = 1 + width * 3
    assert len(raw) == stride * height, "unexpected decompressed size"
    rows: list[list[RGB]] = []
    for y in range(height):
        row = raw[y * stride : (y + 1) * stride]
        assert row[0] == 0, "expected scanline filter type None"
        rows.append([
            (row[1 + x * 3], row[2 + x * 3], row[3 + x * 3])
            for x in range(width)
        ])
    return rows


RED, GREEN, BLUE = (255, 0, 0), (0, 255, 0), (0, 0, 255)


class TestStructure(unittest.TestCase):
    def setUp(self) -> None:
        self.png = SimplePNGWriter([RED, GREEN, BLUE], 4, 2).to_bytes()

    def test_signature(self) -> None:
        self.assertEqual(self.png[:8], SIGNATURE)

    def test_chunk_order(self) -> None:
        types = [t for t, _ in parse_chunks(self.png)]
        self.assertEqual(types, [b"IHDR", b"sRGB", b"IDAT", b"IEND"])

    def test_crcs_valid(self) -> None:
        parse_chunks(self.png)  # asserts on any bad CRC

    def test_ihdr_fields(self) -> None:
        ihdr = dict(parse_chunks(self.png))[b"IHDR"]
        self.assertEqual(struct.unpack(">IIBBBBB", ihdr), (12, 2, 8, 2, 0, 0, 0))

    def test_srgb_intent_is_perceptual(self) -> None:
        self.assertEqual(dict(parse_chunks(self.png))[b"sRGB"], b"\x00")

    def test_iend_is_empty(self) -> None:
        self.assertEqual(dict(parse_chunks(self.png))[b"IEND"], b"")

    def test_deterministic(self) -> None:
        w = SimplePNGWriter([RED, GREEN], 3, 3)
        self.assertEqual(w.to_bytes(), w.to_bytes())


class TestPixels(unittest.TestCase):
    def test_default_1x1_swatches(self) -> None:
        rows = decode_pixels(SimplePNGWriter([RED, GREEN, BLUE]).to_bytes())
        self.assertEqual(rows, [[RED, GREEN, BLUE]])

    def test_wide_and_tall_swatches(self) -> None:
        writer = SimplePNGWriter([RED, GREEN, BLUE], swatch_width=3, swatch_height=2)
        rows = decode_pixels(writer.to_bytes())
        expected_row = [RED] * 3 + [GREEN] * 3 + [BLUE] * 3
        self.assertEqual(rows, [expected_row, expected_row])

    def test_single_color(self) -> None:
        rows = decode_pixels(SimplePNGWriter([(12, 34, 56)], 2, 2).to_bytes())
        self.assertEqual(rows, [[(12, 34, 56)] * 2] * 2)

    def test_channel_extremes(self) -> None:
        colors = [(0, 0, 0), (255, 255, 255), (0, 128, 255)]
        rows = decode_pixels(SimplePNGWriter(colors).to_bytes())
        self.assertEqual(rows, [colors])

    def test_dimensions_attributes(self) -> None:
        writer = SimplePNGWriter([RED, GREEN, BLUE], swatch_width=5, swatch_height=7)
        self.assertEqual((writer.width, writer.height), (15, 7))

    def test_accepts_lists_as_colors(self) -> None:
        rows = decode_pixels(SimplePNGWriter([[1, 2, 3], [4, 5, 6]]).to_bytes())
        self.assertEqual(rows, [[(1, 2, 3), (4, 5, 6)]])

    def test_constructor_attributes(self) -> None:
        writer = SimplePNGWriter([RED])
        self.assertEqual(writer.colors, (RED,))
        self.assertEqual((writer.swatch_width, writer.swatch_height), (1, 1))
        self.assertEqual((writer.width, writer.height), (1, 1))

    def test_large_palette(self) -> None:
        colors = [(i * 4, i * 3, i * 2) for i in range(54)]
        self.assertEqual(decode_pixels(SimplePNGWriter(colors).to_bytes()), [colors])


class TestGeneratedRows(unittest.TestCase):
    def test_solid_exact_pixels(self) -> None:
        writer = SimplePNGWriter.from_solid((12, 34, 56), width=4, height=3)
        self.assertEqual(writer.colors, ((12, 34, 56),))
        self.assertEqual((writer.width, writer.height), (4, 3))
        self.assertEqual(decode_pixels(writer.to_bytes()), [[(12, 34, 56)] * 4] * 3)

    def test_blocks_divide_evenly(self) -> None:
        writer = SimplePNGWriter.from_blocks(
            [RED, GREEN, BLUE], width=9, height=2
        )
        expected = [RED] * 3 + [GREEN] * 3 + [BLUE] * 3
        self.assertEqual(decode_pixels(writer.to_bytes()), [expected, expected])

    def test_blocks_assign_remainder_to_earliest_colors(self) -> None:
        writer = SimplePNGWriter.from_blocks(
            [RED, GREEN, BLUE], width=8, height=1
        )
        self.assertEqual(
            decode_pixels(writer.to_bytes()),
            [[RED] * 3 + [GREEN] * 3 + [BLUE] * 2],
        )

    def test_blocks_reject_width_that_would_omit_a_color(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least the number of colors"):
            SimplePNGWriter.from_blocks([RED, GREEN, BLUE], width=2, height=1)

    def test_gradient_preserves_endpoints(self) -> None:
        writer = SimplePNGWriter.from_gradient([RED, BLUE], width=4, height=1)
        self.assertEqual(
            decode_pixels(writer.to_bytes()),
            [[RED, (170, 0, 85), (85, 0, 170), BLUE]],
        )

    def test_gradient_uses_equally_spaced_stops(self) -> None:
        colors = [RED, GREEN, BLUE, (255, 255, 255)]
        writer = SimplePNGWriter.from_gradient(colors, width=4, height=1)
        self.assertEqual(decode_pixels(writer.to_bytes()), [colors])

    def test_gradient_uses_nearest_even_rounding(self) -> None:
        writer = SimplePNGWriter.from_gradient(
            [(0, 0, 0), (1, 3, 255)], width=3, height=1
        )
        self.assertEqual(
            decode_pixels(writer.to_bytes()),
            [[(0, 0, 0), (0, 2, 128), (1, 3, 255)]],
        )

    def test_narrow_gradient_preserves_first_and_last(self) -> None:
        writer = SimplePNGWriter.from_gradient(
            [RED, GREEN, BLUE], width=2, height=1
        )
        self.assertEqual(decode_pixels(writer.to_bytes()), [[RED, BLUE]])

    def test_multi_color_gradient_rejects_width_one(self) -> None:
        with self.assertRaisesRegex(ValueError, "width of at least 2"):
            SimplePNGWriter.from_gradient([RED, BLUE], width=1, height=1)

    def test_single_color_is_solid_in_every_mode(self) -> None:
        for writer in (
            SimplePNGWriter.from_solid(RED, width=3, height=2),
            SimplePNGWriter.from_blocks([RED], width=3, height=2),
            SimplePNGWriter.from_gradient([RED], width=3, height=2),
        ):
            with self.subTest(writer=writer):
                self.assertEqual(decode_pixels(writer.to_bytes()), [[RED] * 3] * 2)

    def test_encoding_does_not_use_whole_image_zlib_compress(self) -> None:
        writer = SimplePNGWriter.from_solid(RED, width=3, height=4)
        with patch("color_tools.png_writer.zlib.compress", side_effect=AssertionError):
            self.assertEqual(decode_pixels(writer.to_bytes()), [[RED] * 3] * 4)


class TestInputIsolation(unittest.TestCase):
    def test_mutating_input_after_init_has_no_effect(self) -> None:
        colors = [RED, GREEN]
        writer = SimplePNGWriter(colors)
        before = writer.to_bytes()
        colors.append(BLUE)
        colors[0] = (1, 1, 1)
        self.assertEqual(writer.to_bytes(), before)
        self.assertEqual(writer.colors, (RED, GREEN))

    def test_nested_input_mutation_has_no_effect(self) -> None:
        colors = [[1, 2, 3], [4, 5, 6]]
        writer = SimplePNGWriter(colors)
        before = writer.to_bytes()
        colors[0][0] = 256
        colors.append([7, 8, 9])
        self.assertEqual(writer.to_bytes(), before)
        self.assertEqual(writer.colors, ((1, 2, 3), (4, 5, 6)))

    def test_color_storage_is_immutable(self) -> None:
        writer = SimplePNGWriter([RED])
        with self.assertRaises(TypeError):
            cast(list[RGB], writer.colors)[0] = BLUE


class TestSave(unittest.TestCase):
    def test_save_writes_exact_bytes(self) -> None:
        writer = SimplePNGWriter([RED, GREEN, BLUE], 2, 2)
        with tempfile.TemporaryDirectory() as tmp:
            for target in (Path(tmp) / "a.png", str(Path(tmp) / "b.png")):
                writer.save(target)
                self.assertEqual(Path(target).read_bytes(), writer.to_bytes())

    def test_save_creates_parent_directories(self) -> None:
        writer = SimplePNGWriter([BLUE])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "subdir" / "nested" / "out.png"
            writer.save(path)
            self.assertEqual(path.read_bytes(), writer.to_bytes())

    def test_save_overwrites_existing_file(self) -> None:
        writer = SimplePNGWriter([GREEN, BLUE])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "out.png"
            path.write_bytes(b"old content" * 100)
            writer.save(path)
            self.assertEqual(path.read_bytes(), writer.to_bytes())

    def test_save_propagates_io_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(OSError):
                SimplePNGWriter([RED]).save(Path(directory))


class TestValidation(unittest.TestCase):
    def test_empty_colors(self) -> None:
        with self.assertRaisesRegex(ValueError, "colors must not be empty"):
            SimplePNGWriter([])

    def test_bad_swatch_width(self) -> None:
        for bad in (0, -1):
            with self.assertRaisesRegex(ValueError, "swatch_width"):
                SimplePNGWriter([RED], swatch_width=bad)

    def test_bad_swatch_height(self) -> None:
        for bad in (0, -1):
            with self.assertRaisesRegex(ValueError, "swatch_height"):
                SimplePNGWriter([RED], swatch_height=bad)

    def test_bad_color_shapes(self) -> None:
        for bad in [(1, 2), (1, 2, 3, 4), (), 5, None, "red"]:
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, r"colors\[1\]"):
                    SimplePNGWriter([RED, cast(RGB, bad)])

    def test_bad_channel_values(self) -> None:
        for bad in [(256, 0, 0), (0, -1, 0), (0, 0, 1.0), (0, 0, "9"), (True, 0, 0)]:
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, r"colors\[2\]"):
                    SimplePNGWriter([RED, GREEN, cast(RGB, bad)])

    def test_rejects_integer_subclass_channels(self) -> None:
        class Integer(int):
            pass

        with self.assertRaisesRegex(ValueError, r"colors\[0\]"):
            SimplePNGWriter([(Integer(1), 2, 3)])

    def test_dimension_types_are_strict(self) -> None:
        class Integer(int):
            pass

        for bad in (True, False, 1.0, 1.5, "1", None, Integer(1)):
            for dimension in ("swatch_width", "swatch_height"):
                with self.subTest(value=bad, dimension=dimension):
                    with self.assertRaisesRegex(ValueError, dimension):
                        SimplePNGWriter([RED], **{dimension: cast(int, bad)})

    def test_error_reports_offending_index(self) -> None:
        with self.assertRaisesRegex(ValueError, r"colors\[3\]"):
            SimplePNGWriter([RED, GREEN, BLUE, (0, 0, 300)])

    def test_width_over_png_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "width"):
            SimplePNGWriter([RED], swatch_width=2**31)

    def test_height_over_png_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "height"):
            SimplePNGWriter([RED], swatch_height=2**31)

    def test_combined_width_over_png_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "width"):
            SimplePNGWriter([RED, BLUE], swatch_width=2**30)

    def test_largest_allowed_pixel_count_accepted_by_validation(self) -> None:
        writer = SimplePNGWriter([RED], swatch_width=4096, swatch_height=4096)
        self.assertEqual((writer.width, writer.height), (4096, 4096))

    def test_rejects_images_above_pixel_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "maximum is 16777216"):
            SimplePNGWriter([RED], swatch_width=4096, swatch_height=4097)

    def test_generated_dimension_types_are_strict(self) -> None:
        class Integer(int):
            pass

        for bad in (True, False, 1.0, "1", None, Integer(1)):
            for dimension in ("width", "height"):
                with self.subTest(value=bad, dimension=dimension):
                    arguments = {"width": 1, "height": 1, dimension: bad}
                    with self.assertRaisesRegex(ValueError, dimension):
                        SimplePNGWriter.from_solid(
                            RED,
                            width=cast(int, arguments["width"]),
                            height=cast(int, arguments["height"]),
                        )

    def test_generated_colors_use_canonical_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, r"colors\[1\]"):
            SimplePNGWriter.from_gradient(
                [RED, cast(RGB, (0, 0, 1.0))], width=2, height=1
            )


class TestImport(unittest.TestCase):
    """PNG writing and LUT exporting do not load optional image dependencies."""

    def test_base_import_and_lut_export_without_optional_dependencies(self) -> None:
        code = """
import importlib.abc
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

class BlockOptionalImages(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'color_tools.image' or fullname.startswith('color_tools.image.'):
            raise ImportError(fullname)
        return None

sys.modules['PIL'] = None
sys.modules['numpy'] = None
sys.meta_path.insert(0, BlockOptionalImages())
from color_tools.png_writer import SimplePNGWriter
from color_tools.exporters import get_exporter
from color_tools.palette import ColorRecord

with TemporaryDirectory() as directory:
    path = Path(directory) / 'lut.png'
    get_exporter('palette_lut').export_colors([ColorRecord.from_rgb((1, 2, 3))], path)
    assert path.read_bytes() == SimplePNGWriter([(1, 2, 3)]).to_bytes()
assert sys.modules['PIL'] is None
assert sys.modules['numpy'] is None
assert 'color_tools.image' not in sys.modules
"""
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True,
            cwd=Path(__file__).resolve().parents[1], timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_removed_from_image_exports(self) -> None:
        import color_tools.image as image

        self.assertNotIn("SimplePNGWriter", image.__all__)
        self.assertFalse(hasattr(image, "SimplePNGWriter"))


@unittest.skipUnless(HAVE_PILLOW, "Pillow not installed")
class TestPillowCrossCheck(unittest.TestCase):
    """An independent, widely used decoder must agree with our output."""

    def test_pillow_opens_and_reads_pixels(self) -> None:
        colors = [RED, GREEN, BLUE, (12, 34, 56)]
        png = SimplePNGWriter(colors, swatch_width=3, swatch_height=2).to_bytes()
        img = Image.open(io.BytesIO(png))
        img.load()
        self.assertEqual(img.format, "PNG")
        self.assertEqual(img.mode, "RGB")
        self.assertEqual(img.size, (12, 2))
        for i, color in enumerate(colors):
            for x in range(i * 3, i * 3 + 3):
                for y in range(2):
                    self.assertEqual(img.getpixel((x, y)), color)

    def test_pillow_verify_and_srgb_flag(self) -> None:
        png = SimplePNGWriter([RED, GREEN]).to_bytes()
        Image.open(io.BytesIO(png)).verify()
        img = Image.open(io.BytesIO(png))
        self.assertEqual(img.info.get("srgb"), 0)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for color_tools.image.png_writer.SimplePNGWriter.

Verifies that the pure-stdlib PNG writer produces valid, correctly-structured
PNG files without requiring Pillow or any other external dependency.

Test strategy:
- Parse the raw PNG bytes directly using struct/zlib rather than relying on
  Pillow to read them back, so the tests remain dependency-free.
- Cover: constructor validation, dimension calculations, PNG signature,
  IHDR/IDAT/IEND chunks, pixel data correctness, swatch sizing,
  save()-to-file, to_bytes(), parent directory creation.
"""

import io
import os
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from color_tools.image.png_writer import SimplePNGWriter


# ---------------------------------------------------------------------------
# Minimal PNG parser (stdlib only)
# ---------------------------------------------------------------------------

def _read_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    """Parse PNG bytes into a list of (chunk_type, chunk_data) tuples.

    Skips the 8-byte PNG signature.  Raises AssertionError on CRC mismatch.
    """
    assert data[:8] == b'\x89PNG\r\n\x1a\n', "Missing PNG signature"
    pos = 8
    chunks = []
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8]
        chunk_data = data[pos + 8:pos + 8 + length]
        stored_crc = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])[0]
        computed_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        assert stored_crc == computed_crc, (
            f"CRC mismatch in chunk {chunk_type}: "
            f"stored={stored_crc:#010x}, computed={computed_crc:#010x}"
        )
        chunks.append((chunk_type, chunk_data))
        pos += 12 + length
    return chunks


def _parse_ihdr(ihdr_data: bytes) -> dict:
    """Unpack IHDR chunk data into a dict."""
    w, h, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
        ">IIBBBBB", ihdr_data
    )
    return {
        "width": w,
        "height": h,
        "bit_depth": bit_depth,
        "color_type": color_type,
        "compression": compression,
        "filter_method": filter_method,
        "interlace": interlace,
    }


def _decompress_idat(idat_data: bytes) -> bytes:
    """Decompress raw IDAT chunk data."""
    return zlib.decompress(idat_data)


def _scanlines_to_pixels(raw: bytes, width: int, height: int) -> list[tuple[int, int, int]]:
    """Convert decompressed PNG scanline bytes to a flat list of (R,G,B) tuples.

    Assumes filter byte 0 (None) per row and 3-channel RGB.
    """
    row_bytes = 1 + width * 3  # 1 filter byte + 3 bytes per pixel
    pixels = []
    for row_idx in range(height):
        start = row_idx * row_bytes
        assert raw[start] == 0, f"Expected filter byte 0 at row {row_idx}, got {raw[start]}"
        for col in range(width):
            offset = start + 1 + col * 3
            pixels.append((raw[offset], raw[offset + 1], raw[offset + 2]))
    return pixels


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSimplePNGWriterConstructor(unittest.TestCase):
    """Constructor validation and computed properties."""

    def test_basic_construction(self):
        w = SimplePNGWriter([(255, 0, 0)])
        self.assertEqual(w.colors, [(255, 0, 0)])
        self.assertEqual(w.swatch_width, 1)
        self.assertEqual(w.swatch_height, 1)

    def test_computed_dimensions_single_color(self):
        w = SimplePNGWriter([(0, 0, 0)], swatch_width=1, swatch_height=1)
        self.assertEqual(w.width, 1)
        self.assertEqual(w.height, 1)

    def test_computed_dimensions_multiple_colors(self):
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        w = SimplePNGWriter(colors, swatch_width=1, swatch_height=1)
        self.assertEqual(w.width, 3)
        self.assertEqual(w.height, 1)

    def test_computed_dimensions_with_swatch_size(self):
        colors = [(255, 0, 0), (0, 255, 0)]  # 2 colors
        w = SimplePNGWriter(colors, swatch_width=16, swatch_height=32)
        self.assertEqual(w.width, 32)   # 2 × 16
        self.assertEqual(w.height, 32)  # swatch_height

    def test_empty_colors_raises(self):
        with self.assertRaises(ValueError):
            SimplePNGWriter([])

    def test_swatch_width_zero_raises(self):
        with self.assertRaises(ValueError):
            SimplePNGWriter([(0, 0, 0)], swatch_width=0)

    def test_swatch_height_zero_raises(self):
        with self.assertRaises(ValueError):
            SimplePNGWriter([(0, 0, 0)], swatch_height=0)

    def test_swatch_width_negative_raises(self):
        with self.assertRaises(ValueError):
            SimplePNGWriter([(0, 0, 0)], swatch_width=-1)

    def test_swatch_height_negative_raises(self):
        with self.assertRaises(ValueError):
            SimplePNGWriter([(0, 0, 0)], swatch_height=-1)


class TestPNGStructure(unittest.TestCase):
    """Verify the raw PNG bytes conform to the PNG specification."""

    def _bytes(self, colors, **kwargs):
        return SimplePNGWriter(colors, **kwargs).to_bytes()

    def test_signature(self):
        data = self._bytes([(255, 0, 0)])
        self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')

    def test_chunk_order(self):
        data = self._bytes([(255, 0, 0)])
        chunks = _read_chunks(data)
        types = [t for t, _ in chunks]
        self.assertEqual(types[0], b"IHDR")
        self.assertEqual(types[-1], b"IEND")
        self.assertIn(b"IDAT", types)

    def test_chunk_crcs_are_valid(self):
        # _read_chunks asserts on bad CRC; if it doesn't raise, all CRCs are good
        data = self._bytes([(10, 20, 30), (40, 50, 60), (70, 80, 90)])
        _read_chunks(data)  # will raise AssertionError on any bad CRC

    def test_ihdr_width(self):
        colors = [(0, 0, 0)] * 5
        data = self._bytes(colors, swatch_width=1, swatch_height=1)
        ihdr = _parse_ihdr(dict(_read_chunks(data))[b"IHDR"])
        self.assertEqual(ihdr["width"], 5)

    def test_ihdr_height_lut(self):
        data = self._bytes([(0, 0, 0)], swatch_width=1, swatch_height=1)
        ihdr = _parse_ihdr(dict(_read_chunks(data))[b"IHDR"])
        self.assertEqual(ihdr["height"], 1)

    def test_ihdr_height_swatch(self):
        data = self._bytes([(0, 0, 0)], swatch_width=4, swatch_height=8)
        ihdr = _parse_ihdr(dict(_read_chunks(data))[b"IHDR"])
        self.assertEqual(ihdr["height"], 8)

    def test_ihdr_bit_depth_is_8(self):
        data = self._bytes([(0, 0, 0)])
        ihdr = _parse_ihdr(dict(_read_chunks(data))[b"IHDR"])
        self.assertEqual(ihdr["bit_depth"], 8)

    def test_ihdr_color_type_is_rgb(self):
        data = self._bytes([(0, 0, 0)])
        ihdr = _parse_ihdr(dict(_read_chunks(data))[b"IHDR"])
        self.assertEqual(ihdr["color_type"], 2)  # 2 = RGB

    def test_ihdr_no_interlace(self):
        data = self._bytes([(0, 0, 0)])
        ihdr = _parse_ihdr(dict(_read_chunks(data))[b"IHDR"])
        self.assertEqual(ihdr["interlace"], 0)

    def test_iend_is_empty(self):
        data = self._bytes([(0, 0, 0)])
        chunks = dict(_read_chunks(data))
        self.assertEqual(chunks[b"IEND"], b"")


class TestPixelData(unittest.TestCase):
    """Verify the decompressed pixel data matches the input colors."""

    def _pixels(self, colors, swatch_width=1, swatch_height=1):
        data = SimplePNGWriter(colors, swatch_width=swatch_width, swatch_height=swatch_height).to_bytes()
        chunks = dict(_read_chunks(data))
        ihdr = _parse_ihdr(chunks[b"IHDR"])
        raw = _decompress_idat(chunks[b"IDAT"])
        return _scanlines_to_pixels(raw, ihdr["width"], ihdr["height"])

    def test_single_red_pixel(self):
        pixels = self._pixels([(255, 0, 0)])
        self.assertEqual(pixels, [(255, 0, 0)])

    def test_single_green_pixel(self):
        pixels = self._pixels([(0, 255, 0)])
        self.assertEqual(pixels, [(0, 255, 0)])

    def test_single_blue_pixel(self):
        pixels = self._pixels([(0, 0, 255)])
        self.assertEqual(pixels, [(0, 0, 255)])

    def test_black_and_white(self):
        pixels = self._pixels([(0, 0, 0), (255, 255, 255)])
        self.assertEqual(pixels, [(0, 0, 0), (255, 255, 255)])

    def test_color_order_preserved(self):
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        pixels = self._pixels(colors)
        self.assertEqual(pixels, colors)

    def test_arbitrary_color_values(self):
        colors = [(10, 20, 30), (100, 150, 200), (55, 128, 77)]
        pixels = self._pixels(colors)
        self.assertEqual(pixels, colors)

    def test_swatch_width_repeats_pixels(self):
        # swatch_width=3 → each color appears 3 times per row
        colors = [(255, 0, 0), (0, 0, 255)]
        pixels = self._pixels(colors, swatch_width=3, swatch_height=1)
        self.assertEqual(pixels, [
            (255, 0, 0), (255, 0, 0), (255, 0, 0),
            (0, 0, 255), (0, 0, 255), (0, 0, 255),
        ])

    def test_swatch_height_repeats_rows(self):
        # swatch_height=3 → all 3 rows must be identical
        colors = [(10, 20, 30), (40, 50, 60)]
        pixels = self._pixels(colors, swatch_width=1, swatch_height=3)
        row = [(10, 20, 30), (40, 50, 60)]
        self.assertEqual(pixels, row * 3)

    def test_large_palette(self):
        # 54-color NES-like palette
        colors = [(i * 4, i * 3, i * 2) for i in range(54)]
        pixels = self._pixels(colors)
        self.assertEqual(pixels, colors)

    def test_channel_clamping_255(self):
        # Values at max boundary
        pixels = self._pixels([(255, 255, 255)])
        self.assertEqual(pixels, [(255, 255, 255)])

    def test_channel_clamping_0(self):
        pixels = self._pixels([(0, 0, 0)])
        self.assertEqual(pixels, [(0, 0, 0)])


class TestToBytes(unittest.TestCase):
    """to_bytes() returns the same bytes as save() writes to disk."""

    def test_to_bytes_returns_bytes(self):
        result = SimplePNGWriter([(255, 0, 0)]).to_bytes()
        self.assertIsInstance(result, bytes)

    def test_to_bytes_starts_with_png_signature(self):
        result = SimplePNGWriter([(0, 128, 255)]).to_bytes()
        self.assertEqual(result[:8], b'\x89PNG\r\n\x1a\n')

    def test_to_bytes_matches_save(self):
        colors = [(10, 20, 30), (40, 50, 60)]
        writer = SimplePNGWriter(colors)
        in_memory = writer.to_bytes()

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            tmp = f.name
        try:
            writer.save(tmp)
            with open(tmp, 'rb') as f:
                from_file = f.read()
        finally:
            os.unlink(tmp)

        self.assertEqual(in_memory, from_file)

    def test_to_bytes_is_idempotent(self):
        writer = SimplePNGWriter([(1, 2, 3)])
        self.assertEqual(writer.to_bytes(), writer.to_bytes())


class TestSave(unittest.TestCase):
    """save() writes a valid file to disk."""

    def test_save_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.png"
            SimplePNGWriter([(255, 0, 0)]).save(path)
            self.assertTrue(path.exists())

    def test_save_file_is_nonzero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.png"
            SimplePNGWriter([(0, 0, 0)]).save(path)
            self.assertGreater(path.stat().st_size, 0)

    def test_save_accepts_string_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "out.png")
            SimplePNGWriter([(0, 255, 0)]).save(path)
            self.assertTrue(Path(path).exists())

    def test_save_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir" / "nested" / "out.png"
            SimplePNGWriter([(0, 0, 255)]).save(path)
            self.assertTrue(path.exists())

    def test_save_overwrites_existing_file(self):
        colors_a = [(255, 0, 0)]
        colors_b = [(0, 255, 0), (0, 0, 255)]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.png"
            SimplePNGWriter(colors_a).save(path)
            size_a = path.stat().st_size
            SimplePNGWriter(colors_b).save(path)
            size_b = path.stat().st_size
            # Two-color file must be larger than one-color file
            self.assertGreater(size_b, size_a)


class TestImport(unittest.TestCase):
    """SimplePNGWriter is importable from the public image package."""

    def test_importable_from_image_package(self):
        from color_tools.image import SimplePNGWriter as SPW
        self.assertIs(SPW, SimplePNGWriter)

    def test_in_image_all(self):
        import color_tools.image as img
        self.assertIn('SimplePNGWriter', img.__all__)


if __name__ == '__main__':
    unittest.main()

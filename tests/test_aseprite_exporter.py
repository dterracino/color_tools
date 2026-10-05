"""Independent binary-structure checks for native Aseprite palette export."""

from __future__ import annotations

import struct
import tempfile
import unittest
import zlib
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from color_tools import Palette, PaletteMetadata, export_palette
from color_tools.exporters import AsepriteExporter, get_exporter, list_export_formats


class TestAsepriteExporter(unittest.TestCase):
    def test_registry_and_adobe_separation(self) -> None:
        self.assertIsInstance(get_exporter("aseprite"), AsepriteExporter)
        self.assertIn("aseprite", list_export_formats("colors"))
        self.assertNotIn("aseprite", list_export_formats("filaments"))
        self.assertEqual(get_exporter("ase").metadata.file_extension, "ase")
        self.assertEqual(get_exporter("aseprite").metadata.file_extension, "aseprite")
        self.assertTrue(get_exporter("aseprite").is_available)
        with self.assertRaises(NotImplementedError):
            get_exporter("aseprite").export_filaments([])

    def test_binary_document_and_pixel_boundaries(self) -> None:
        for count in (1, 5, 252, 256, 257):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as directory:
                colors = [(index % 256, (index * 3) % 256, (index * 7) % 256)
                          for index in range(count)]
                palette = Palette.from_rgb(colors)
                path = Path(directory) / "nested" / "palette.aseprite"
                self.assertEqual(
                    export_palette(palette, "aseprite", path,
                                   metadata=PaletteMetadata(name="Swatches", columns=16)),
                    str(path),
                )
                data = path.read_bytes()
                self.assertEqual(struct.unpack_from("<I", data)[0], len(data))
                self.assertEqual(struct.unpack_from("<HH", data, 4), (0xA5E0, 1))
                width, height, depth = struct.unpack_from("<HHH", data, 8)
                self.assertEqual(width, min(16, count))
                self.assertEqual(height, (count + width - 1) // width)
                self.assertEqual(depth, 8 if count <= 256 else 32)
                self.assertEqual(struct.unpack_from("<I", data, 14)[0], 1)
                self.assertEqual(data[28:32], bytes(4))
                self.assertEqual(struct.unpack_from("<H", data, 32)[0], count)
                self.assertEqual(data[34:36], b"\x01\x01")
                self.assertEqual(data[44:128], bytes(84))
                self.assertEqual(struct.unpack_from("<I", data, 128)[0], len(data) - 128)
                self.assertEqual(struct.unpack_from("<HHH", data, 132), (0xF1FA, 4, 100))
                self.assertEqual(struct.unpack_from("<I", data, 140)[0], 4)
                chunks: dict[int, bytes] = {}
                position = 144
                kinds = []
                for _ in range(4):
                    length, kind = struct.unpack_from("<IH", data, position)
                    self.assertGreaterEqual(length, 6)
                    self.assertLessEqual(position + length, len(data))
                    kinds.append(kind)
                    chunks[kind] = data[position + 6:position + length]
                    position += length
                self.assertEqual(position, len(data))
                self.assertEqual(kinds, [0x2007, 0x2019, 0x2004, 0x2005])
                self.assertEqual(chunks[0x2007], struct.pack("<HHI8x", 1, 0, 0))
                entries = chunks[0x2019]
                self.assertEqual(struct.unpack_from("<III", entries), (count, 0, count - 1))
                self.assertEqual(entries[12:20], bytes(8))
                cursor = 20
                for record in palette.records:
                    self.assertEqual(struct.unpack_from("<H", entries, cursor)[0], 1)
                    self.assertEqual(entries[cursor + 2:cursor + 6], bytes((*record.rgb, 255)))
                    size = struct.unpack_from("<H", entries, cursor + 6)[0]
                    self.assertEqual(entries[cursor + 8:cursor + 8 + size].decode("utf-8"),
                                     record.name)
                    cursor += 8 + size
                self.assertEqual(cursor, len(entries))
                layer = chunks[0x2004]
                self.assertEqual(struct.unpack_from("<6HB", layer), (15, 0, 0, 0, 0, 0, 255))
                self.assertEqual(layer[18:].decode("utf-8"), "Swatches")
                cel = chunks[0x2005]
                self.assertEqual(struct.unpack_from("<HhhBHh", cel), (0, 0, 0, 255, 2, 0))
                self.assertEqual(struct.unpack_from("<HH", cel, 16), (width, height))
                pixels = zlib.decompress(cel[20:])
                padding = width * height - count
                expected = (bytes(range(count)) + bytes(padding) if depth == 8 else
                            b"".join(bytes((*rgb, 255)) for rgb in colors)
                            + bytes((*colors[0], 255)) * padding)
                self.assertEqual(pixels, expected)

    def test_unicode_names_duplicates_and_default_layout(self) -> None:
        palette = Palette.from_hex(["#f00", "#f00"], names=["Rouge \u00e9", ""])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fallback.aseprite"
            get_exporter("aseprite").export_colors(palette.records, path)
            data = path.read_bytes()
            self.assertEqual(struct.unpack_from("<HH", data, 8), (2, 1))
            self.assertIn("Rouge \u00e9".encode("utf-8"), data)
            self.assertIn(b"fallback", data)
            self.assertIn(struct.pack("<HBBBB", 0, 255, 0, 0, 255), data)
            for columns in (None, 0, 100):
                export_palette(palette, "aseprite", path,
                               metadata=PaletteMetadata(columns=columns))
                self.assertEqual(struct.unpack_from("<HH", path.read_bytes(), 8), (2, 1))

    def test_validation_precedes_file_creation(self) -> None:
        palette = Palette.from_hex(["#f00"])
        invalid = [
            Palette([]),
            Palette([replace(palette.records[0], rgb=(256, 0, 0))]),
            Palette([replace(palette.records[0], name="\u00e9" * 32768)]),
            Palette(palette.records * 65536),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.aseprite"
            for value in invalid:
                with self.assertRaises(ValueError):
                    export_palette(value, "aseprite", path)
                self.assertFalse(path.exists())
            with self.assertRaises(ValueError):
                export_palette(palette, "aseprite", path,
                               metadata=PaletteMetadata(name="x" * 65536))
            self.assertFalse(path.exists())
            with self.assertRaises(ValueError):
                export_palette(palette, "aseprite", Path(directory) / "wrong.ase")

    def test_generated_extension(self) -> None:
        palette = Palette.from_hex(["#f00"])
        exporter = get_exporter("aseprite")
        self.assertTrue(exporter.generate_filename("colors").endswith(".aseprite"))
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "generated.aseprite")
            with patch.object(exporter, "generate_filename", return_value=path):
                self.assertEqual(exporter.export_colors(palette.records), path)
            self.assertTrue(Path(path).is_file())


if __name__ == "__main__":
    unittest.main()

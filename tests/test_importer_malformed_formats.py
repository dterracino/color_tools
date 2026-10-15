"""Malformed-file matrices for the built-in palette importers."""

from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from color_tools.exporters.palette_metadata import PaletteMetadata
from color_tools.importers import get_importer


def _riff_palette(
    entries: list[tuple[int, int, int]],
    *,
    version: int = 0x0300,
    declared_count: int | None = None,
    extra_data: bytes = b"",
    trailing: bytes = b"",
) -> bytes:
    """Build a small RIFF PAL document with optional malformed dimensions."""
    count = len(entries) if declared_count is None else declared_count
    payload = struct.pack("<HH", version, count)
    payload += b"".join(bytes((red, green, blue, 0)) for red, green, blue in entries)
    payload += extra_data
    chunk = b"data" + struct.pack("<I", len(payload)) + payload
    body = b"PAL " + chunk
    return b"RIFF" + struct.pack("<I", len(body)) + body + trailing


class ImporterFormatTestCase(unittest.TestCase):
    """Provide temporary text and binary palette files."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_text(self, filename: str, content: str, *, encoding: str = "utf-8") -> Path:
        path = self.directory / filename
        path.write_text(content, encoding=encoding)
        return path

    def write_bytes(self, filename: str, content: bytes) -> Path:
        path = self.directory / filename
        path.write_bytes(content)
        return path


class TestGPLMalformedFiles(ImporterFormatTestCase):
    """Cover GPL signatures, entries, channels, and optional metadata."""

    def test_case_insensitive_extension_and_complete_import(self) -> None:
        path = self.write_text(
            "sample.GPL",
            "GIMP Palette\n"
            "Name: Example\n"
            "Columns: 2\n"
            "# Author: Ada\n"
            "# Description: Demonstration\n"
            "# Tags: warm, sample\n"
            "# ordinary comment\n"
            "\n"
            "255 0 0 Named Red\n"
            "0 255 0\n",
        )
        importer = get_importer("gpl")

        self.assertTrue(importer.can_import(path))
        imported = importer.import_palette(path)

        self.assertEqual([color.rgb for color in imported.colors], [(255, 0, 0), (0, 255, 0)])
        self.assertEqual([color.name for color in imported.colors], ["Named Red", "#00FF00"])
        self.assertEqual({color.source for color in imported.colors}, {"sample.GPL"})
        self.assertEqual(imported.metadata.name, "Example")
        self.assertEqual(imported.metadata.author, "Ada")
        self.assertEqual(imported.metadata.description, "Demonstration")
        self.assertEqual(imported.metadata.columns, 2)
        self.assertEqual(imported.metadata.tags, ("warm", "sample"))

    def test_rejects_empty_and_invalid_signature(self) -> None:
        importer = get_importer("gpl")
        cases = (("empty.gpl", "", "empty"), ("header.gpl", "Not GPL\n", "expected 'GIMP Palette'"))

        for filename, content, message in cases:
            with self.subTest(filename=filename):
                with self.assertRaisesRegex(ValueError, message):
                    importer.import_palette(self.write_text(filename, content))

    def test_rejects_non_utf8_input_and_detection_returns_false(self) -> None:
        path = self.write_bytes("encoded.gpl", b"GIMP Palette\n\xff")
        importer = get_importer("gpl")

        self.assertFalse(importer.can_import(path))
        with self.assertRaisesRegex(ValueError, "Unable to decode GPL palette"):
            importer.import_palette(path)

    def test_rejects_malformed_and_out_of_range_entries(self) -> None:
        importer = get_importer("gpl")
        cases = (
            ("255 0\n", "Invalid GPL palette entry"),
            ("red 0 0\n", "Invalid GPL palette entry"),
            ("256 0 0\n", "between 0 and 255"),
        )

        for entry, message in cases:
            with self.subTest(entry=entry):
                path = self.write_text("invalid.gpl", "GIMP Palette\n" + entry)
                with self.assertRaisesRegex(ValueError, message):
                    importer.import_palette(path)

    def test_rejects_invalid_columns(self) -> None:
        importer = get_importer("gpl")
        for value, message in (("many", "Invalid GPL Columns"), ("256", "between 0 and 255")):
            with self.subTest(value=value):
                path = self.write_text("columns.gpl", f"GIMP Palette\nColumns: {value}\n")
                with self.assertRaisesRegex(ValueError, message):
                    importer.import_palette(path)


class TestHexMalformedFiles(ImporterFormatTestCase):
    """Cover HEX comments, empty input, and malformed values."""

    def test_case_insensitive_extension_comments_and_metadata(self) -> None:
        path = self.write_text(
            "sample.HEX",
            "; comment\n# another comment\n\nFF0000\n#00ff00\n",
        )
        importer = get_importer("hex")

        self.assertTrue(importer.can_import(path))
        imported = importer.import_palette(path)

        self.assertEqual([color.rgb for color in imported.colors], [(255, 0, 0), (0, 255, 0)])
        self.assertEqual([color.name for color in imported.colors], ["#FF0000", "#00FF00"])
        self.assertEqual({color.source for color in imported.colors}, {"sample.HEX"})
        self.assertEqual(imported.metadata, PaletteMetadata())

    def test_empty_or_comment_only_input_contains_no_colors(self) -> None:
        importer = get_importer("hex")
        for content in ("", "; comment\n# comment\n"):
            with self.subTest(content=content):
                with self.assertRaisesRegex(ValueError, "contains no colors"):
                    importer.import_palette(self.write_text("empty.hex", content))

    def test_rejects_non_utf8_input_and_detection_returns_false(self) -> None:
        path = self.write_bytes("encoded.hex", b"FF0000\n\xff")
        importer = get_importer("hex")

        self.assertFalse(importer.can_import(path))
        with self.assertRaisesRegex(ValueError, "Unable to decode HEX palette"):
            importer.import_palette(path)

    def test_rejects_wrong_length_and_nonnumeric_values(self) -> None:
        importer = get_importer("hex")
        for value in ("FFF", "00000000", "GG0000"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "Invalid HEX palette entry"):
                    importer.import_palette(self.write_text("invalid.hex", value + "\n"))


class TestJascPalMalformedFiles(ImporterFormatTestCase):
    """Cover JASC headers, counts, entries, and strict trailing records."""

    def test_case_insensitive_extension_and_complete_import(self) -> None:
        path = self.write_text("sample.PAL", "JASC-PAL\n0100\n2\n255 0 0\n0 255 0\n", encoding="ascii")
        importer = get_importer("jasc_pal")

        self.assertTrue(importer.can_import(path))
        imported = importer.import_palette(path)

        self.assertEqual([color.rgb for color in imported.colors], [(255, 0, 0), (0, 255, 0)])
        self.assertEqual([color.name for color in imported.colors], ["#FF0000", "#00FF00"])
        self.assertEqual({color.source for color in imported.colors}, {"sample.PAL"})
        self.assertEqual(imported.metadata, PaletteMetadata())

    def test_rejects_short_header_signature_and_version(self) -> None:
        importer = get_importer("jasc_pal")
        cases = (
            ("", "file is too short"),
            ("WRONG\n0100\n0\n", "expected 'JASC-PAL'"),
            ("JASC-PAL\n0200\n0\n", "Unsupported JASC PAL version"),
        )
        for content, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    importer.import_palette(self.write_text("invalid.pal", content, encoding="ascii"))

    def test_rejects_non_ascii_input_and_detection_returns_false(self) -> None:
        path = self.write_bytes("encoded.pal", b"JASC-PAL\n0100\n1\n\xff 0 0\n")
        importer = get_importer("jasc_pal")

        self.assertFalse(importer.can_import(path))
        with self.assertRaisesRegex(ValueError, "Unable to decode JASC PAL palette"):
            importer.import_palette(path)

    def test_rejects_invalid_negative_and_mismatched_counts(self) -> None:
        importer = get_importer("jasc_pal")
        cases = (
            ("many", "Invalid JASC PAL color count"),
            ("-1", "must not be negative"),
            ("2\n255 0 0", "declared 2, found 1"),
            ("1\n255 0 0\n0 0 0", "declared 1, found 2"),
        )
        for body, message in cases:
            with self.subTest(body=body):
                content = "JASC-PAL\n0100\n" + body + "\n"
                with self.assertRaisesRegex(ValueError, message):
                    importer.import_palette(self.write_text("count.pal", content, encoding="ascii"))

    def test_rejects_empty_malformed_nonnumeric_and_out_of_range_entries(self) -> None:
        importer = get_importer("jasc_pal")
        cases = (
            ("2\n255 0 0\n\n", "empty JASC PAL color entry"),
            ("1\n255 0\n", "Invalid JASC PAL color entry"),
            ("1\nred 0 0\n", "Invalid JASC PAL RGB value"),
            ("1\n256 0 0\n", "between 0 and 255"),
        )
        for body, message in cases:
            with self.subTest(body=body):
                content = "JASC-PAL\n0100\n" + body
                with self.assertRaisesRegex(ValueError, message):
                    importer.import_palette(self.write_text("entry.pal", content, encoding="ascii"))


class TestRiffPalMalformedFiles(ImporterFormatTestCase):
    """Cover RIFF container, chunk, and LOGPALETTE failures."""

    def test_case_insensitive_extension_and_complete_import(self) -> None:
        path = self.write_bytes("sample.PAL", _riff_palette([(255, 0, 0), (0, 255, 0)]))
        importer = get_importer("riff_pal")

        self.assertTrue(importer.can_import(path))
        imported = importer.import_palette(path)

        self.assertEqual([color.rgb for color in imported.colors], [(255, 0, 0), (0, 255, 0)])
        self.assertEqual([color.name for color in imported.colors], ["#FF0000", "#00FF00"])
        self.assertEqual({color.source for color in imported.colors}, {"sample.PAL"})
        self.assertEqual(imported.metadata, PaletteMetadata())

    def test_rejects_short_header_invalid_signature_and_form(self) -> None:
        importer = get_importer("riff_pal")
        cases = (
            (b"", "file is too short"),
            (b"NOPE" + b"\x00" * 8, "expected 'RIFF'"),
            (b"RIFF\x04\x00\x00\x00NOPE", "expected 'PAL '"),
        )
        for data, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    importer.import_palette(self.write_bytes("invalid.pal", data))

    def test_rejects_oversized_riff_and_missing_or_oversized_chunks(self) -> None:
        importer = get_importer("riff_pal")
        oversized_riff = b"RIFF" + struct.pack("<I", 100) + b"PAL "
        missing_data = b"RIFF" + struct.pack("<I", 4) + b"PAL "
        oversized_chunk_body = b"PAL " + b"JUNK" + struct.pack("<I", 50)
        oversized_chunk = b"RIFF" + struct.pack("<I", len(oversized_chunk_body)) + oversized_chunk_body
        cases = (
            (oversized_riff, "RIFF size exceeds file length"),
            (missing_data, "missing 'data' chunk"),
            (oversized_chunk, "chunk extends beyond file size"),
        )
        for data, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    importer.import_palette(self.write_bytes("chunk.pal", data))

    def test_rejects_short_data_version_and_premature_entries(self) -> None:
        importer = get_importer("riff_pal")
        short_body = b"PAL " + b"data" + struct.pack("<I", 2) + b"\x00\x03"
        short_data = b"RIFF" + struct.pack("<I", len(short_body)) + short_body
        cases = (
            (short_data, "data chunk is too short"),
            (_riff_palette([], version=0x0200), "Unsupported RIFF PAL version"),
            (_riff_palette([(255, 0, 0)], declared_count=2), "shorter than the declared palette size"),
        )
        for data, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    importer.import_palette(self.write_bytes("data.pal", data))

    def test_accepts_extra_data_bytes_and_ignores_bytes_after_riff_container(self) -> None:
        importer = get_importer("riff_pal")
        data = _riff_palette(
            [(255, 0, 0)],
            extra_data=b"EXTRA",
            trailing=b"TRAILING",
        )

        imported = importer.import_palette(self.write_bytes("trailing.pal", data))

        self.assertEqual([color.rgb for color in imported.colors], [(255, 0, 0)])

    def test_does_not_search_for_data_chunks_after_declared_riff_container(self) -> None:
        outside_chunk = _riff_palette([(255, 0, 0)])[12:]
        data = b"RIFF" + struct.pack("<I", 4) + b"PAL " + outside_chunk

        with self.assertRaisesRegex(ValueError, "missing 'data' chunk"):
            get_importer("riff_pal").import_palette(
                self.write_bytes("outside-data.pal", data)
            )

    def test_skips_padded_odd_sized_chunks_before_palette_data(self) -> None:
        palette_chunk = _riff_palette([(255, 0, 0)])[12:]
        odd_chunk = b"JUNK" + struct.pack("<I", 1) + b"X" + b"\x00"
        body = b"PAL " + odd_chunk + palette_chunk
        data = b"RIFF" + struct.pack("<I", len(body)) + body

        imported = get_importer("riff_pal").import_palette(
            self.write_bytes("padded.pal", data)
        )

        self.assertEqual([color.rgb for color in imported.colors], [(255, 0, 0)])


if __name__ == "__main__":
    unittest.main()

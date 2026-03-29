"""
Tests for palette-format exporters: gpl, hex, pal, paintnet, lospec.

These exporters support colors only (not filaments) and write specific
text/JSON file formats used by various graphics applications.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from color_tools.exporters import get_exporter
from color_tools.palette import ColorRecord


# Shared test fixtures — three simple colors used across all exporter tests.
def _make_test_colors() -> list[ColorRecord]:
    return [
        ColorRecord(
            name="red",
            hex="#FF0000",
            rgb=(255, 0, 0),
            hsl=(0.0, 100.0, 50.0),
            lab=(53.23, 80.1, 67.2),
            lch=(53.23, 104.55, 40.0),
            source="test",
        ),
        ColorRecord(
            name="lime",
            hex="#00FF00",
            rgb=(0, 255, 0),
            hsl=(120.0, 100.0, 50.0),
            lab=(87.74, -86.18, 83.18),
            lch=(87.74, 119.78, 136.0),
            source="test",
        ),
        ColorRecord(
            name="blue",
            hex="#0000FF",
            rgb=(0, 0, 255),
            hsl=(240.0, 100.0, 50.0),
            lab=(32.3, 79.19, -107.86),
            lch=(32.3, 133.81, 306.3),
            source="test",
        ),
    ]


class TestGPLExporter(unittest.TestCase):
    """Tests for the GIMP Palette (.gpl) exporter."""

    def setUp(self):
        self.exporter = get_exporter('gpl')
        self.colors = _make_test_colors()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_metadata_name(self):
        """Exporter name is 'gpl'."""
        self.assertEqual(self.exporter.metadata.name, 'gpl')

    def test_metadata_supports_colors(self):
        """Exporter supports colors."""
        self.assertTrue(self.exporter.metadata.supports_colors)

    def test_metadata_does_not_support_filaments(self):
        """Exporter does not support filaments."""
        self.assertFalse(self.exporter.metadata.supports_filaments)

    def test_file_extension(self):
        """File extension is 'gpl'."""
        self.assertEqual(self.exporter.metadata.file_extension, 'gpl')

    def test_export_creates_file(self):
        """export_colors creates the output file."""
        output = os.path.join(self.tmp.name, "test.gpl")
        result = self.exporter.export_colors(self.colors, output)
        self.assertTrue(Path(result).exists())

    def test_export_returns_path_string(self):
        """export_colors returns a path string."""
        output = os.path.join(self.tmp.name, "out.gpl")
        result = self.exporter.export_colors(self.colors, output)
        self.assertIsInstance(result, str)

    def test_file_starts_with_gimp_palette_header(self):
        """GPL file starts with 'GIMP Palette' header."""
        output = os.path.join(self.tmp.name, "palette.gpl")
        self.exporter.export_colors(self.colors, output)
        content = Path(output).read_text(encoding='utf-8')
        self.assertTrue(content.startswith("GIMP Palette\n"))

    def test_file_contains_name_line(self):
        """GPL file contains 'Name: <stem>' line."""
        output = os.path.join(self.tmp.name, "mypalette.gpl")
        self.exporter.export_colors(self.colors, output)
        content = Path(output).read_text(encoding='utf-8')
        self.assertIn("Name: mypalette\n", content)

    def test_file_contains_columns_line(self):
        """GPL file contains 'Columns: 0' line."""
        output = os.path.join(self.tmp.name, "test.gpl")
        self.exporter.export_colors(self.colors, output)
        content = Path(output).read_text(encoding='utf-8')
        self.assertIn("Columns: 0\n", content)

    def test_file_contains_separator(self):
        """GPL file contains '#' separator."""
        output = os.path.join(self.tmp.name, "test.gpl")
        self.exporter.export_colors(self.colors, output)
        content = Path(output).read_text(encoding='utf-8')
        self.assertIn("#\n", content)

    def test_file_contains_red_color_line(self):
        """GPL file contains correctly formatted entry for red."""
        output = os.path.join(self.tmp.name, "test.gpl")
        self.exporter.export_colors(self.colors, output)
        content = Path(output).read_text(encoding='utf-8')
        # Format: "255   0   0\tred\n"
        self.assertIn("255   0   0\tred\n", content)

    def test_file_contains_blue_color_line(self):
        """GPL file contains correctly formatted entry for blue."""
        output = os.path.join(self.tmp.name, "test.gpl")
        self.exporter.export_colors(self.colors, output)
        content = Path(output).read_text(encoding='utf-8')
        self.assertIn("  0   0 255\tblue\n", content)

    def test_export_filaments_not_implemented(self):
        """export_filaments raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.exporter.export_filaments([])

    def test_auto_filename_when_none(self):
        """Auto-generates a filename when output_path is None."""
        orig_dir = os.getcwd()
        try:
            os.chdir(self.tmp.name)
            result = self.exporter.export_colors(self.colors, None)
            self.assertTrue(Path(result).exists())
            self.assertTrue(result.endswith('.gpl'))
        finally:
            os.chdir(orig_dir)


class TestHexExporter(unittest.TestCase):
    """Tests for the hex format exporter."""

    def setUp(self):
        self.exporter = get_exporter('hex')
        self.colors = _make_test_colors()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_metadata_name(self):
        """Exporter name is 'hex'."""
        self.assertEqual(self.exporter.metadata.name, 'hex')

    def test_metadata_supports_colors(self):
        """Exporter supports colors."""
        self.assertTrue(self.exporter.metadata.supports_colors)

    def test_metadata_does_not_support_filaments(self):
        """Exporter does not support filaments."""
        self.assertFalse(self.exporter.metadata.supports_filaments)

    def test_file_extension(self):
        """File extension is 'hex'."""
        self.assertEqual(self.exporter.metadata.file_extension, 'hex')

    def test_export_creates_file(self):
        """export_colors creates the output file."""
        output = os.path.join(self.tmp.name, "colors.hex")
        result = self.exporter.export_colors(self.colors, output)
        self.assertTrue(Path(result).exists())

    def test_file_content_uppercase_no_hash(self):
        """Each line is uppercase hex without # prefix."""
        output = os.path.join(self.tmp.name, "colors.hex")
        self.exporter.export_colors(self.colors, output)
        lines = Path(output).read_text(encoding='utf-8').splitlines()
        self.assertEqual(lines[0], "FF0000")
        self.assertEqual(lines[1], "00FF00")
        self.assertEqual(lines[2], "0000FF")

    def test_file_line_count_matches_colors(self):
        """File has exactly one line per color."""
        output = os.path.join(self.tmp.name, "colors.hex")
        self.exporter.export_colors(self.colors, output)
        lines = Path(output).read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(lines), len(self.colors))

    def test_no_hash_prefix(self):
        """Output lines do not start with #."""
        output = os.path.join(self.tmp.name, "colors.hex")
        self.exporter.export_colors(self.colors, output)
        for line in Path(output).read_text(encoding='utf-8').splitlines():
            self.assertFalse(line.startswith('#'))

    def test_export_filaments_not_implemented(self):
        """export_filaments raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.exporter.export_filaments([])


class TestJascPalExporter(unittest.TestCase):
    """Tests for the JASC-PAL format exporter."""

    def setUp(self):
        self.exporter = get_exporter('pal')
        self.colors = _make_test_colors()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_metadata_name(self):
        """Exporter name is 'pal'."""
        self.assertEqual(self.exporter.metadata.name, 'pal')

    def test_metadata_supports_colors(self):
        """Exporter supports colors."""
        self.assertTrue(self.exporter.metadata.supports_colors)

    def test_metadata_does_not_support_filaments(self):
        """Exporter does not support filaments."""
        self.assertFalse(self.exporter.metadata.supports_filaments)

    def test_file_extension(self):
        """File extension is 'pal'."""
        self.assertEqual(self.exporter.metadata.file_extension, 'pal')

    def test_export_creates_file(self):
        """export_colors creates the output file."""
        output = os.path.join(self.tmp.name, "colors.pal")
        result = self.exporter.export_colors(self.colors, output)
        self.assertTrue(Path(result).exists())

    def test_file_header_line1(self):
        """First line is 'JASC-PAL'."""
        output = os.path.join(self.tmp.name, "colors.pal")
        self.exporter.export_colors(self.colors, output)
        lines = Path(output).read_text(encoding='utf-8').splitlines()
        self.assertEqual(lines[0], "JASC-PAL")

    def test_file_header_line2(self):
        """Second line is '0100'."""
        output = os.path.join(self.tmp.name, "colors.pal")
        self.exporter.export_colors(self.colors, output)
        lines = Path(output).read_text(encoding='utf-8').splitlines()
        self.assertEqual(lines[1], "0100")

    def test_file_header_line3_is_color_count(self):
        """Third line is the count of colors."""
        output = os.path.join(self.tmp.name, "colors.pal")
        self.exporter.export_colors(self.colors, output)
        lines = Path(output).read_text(encoding='utf-8').splitlines()
        self.assertEqual(lines[2], str(len(self.colors)))

    def test_file_color_entries_are_r_g_b(self):
        """Color entries are space-separated R G B values."""
        output = os.path.join(self.tmp.name, "colors.pal")
        self.exporter.export_colors(self.colors, output)
        lines = Path(output).read_text(encoding='utf-8').splitlines()
        self.assertEqual(lines[3], "255 0 0")    # red
        self.assertEqual(lines[4], "0 255 0")    # lime
        self.assertEqual(lines[5], "0 0 255")    # blue

    def test_export_filaments_not_implemented(self):
        """export_filaments raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.exporter.export_filaments([])


class TestPaintNetExporter(unittest.TestCase):
    """Tests for the PAINT.NET palette format exporter."""

    def setUp(self):
        self.exporter = get_exporter('paintnet')
        self.colors = _make_test_colors()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_metadata_name(self):
        """Exporter name is 'paintnet'."""
        self.assertEqual(self.exporter.metadata.name, 'paintnet')

    def test_metadata_supports_colors(self):
        """Exporter supports colors."""
        self.assertTrue(self.exporter.metadata.supports_colors)

    def test_metadata_does_not_support_filaments(self):
        """Exporter does not support filaments."""
        self.assertFalse(self.exporter.metadata.supports_filaments)

    def test_file_extension(self):
        """File extension is 'txt'."""
        self.assertEqual(self.exporter.metadata.file_extension, 'txt')

    def test_export_creates_file(self):
        """export_colors creates the output file."""
        output = os.path.join(self.tmp.name, "colors.txt")
        result = self.exporter.export_colors(self.colors, output)
        self.assertTrue(Path(result).exists())

    def test_first_line_is_header(self):
        """First line is ';paint.net Palette File'."""
        output = os.path.join(self.tmp.name, "colors.txt")
        self.exporter.export_colors(self.colors, output)
        lines = Path(output).read_text(encoding='utf-8').splitlines()
        self.assertEqual(lines[0], ";paint.net Palette File")

    def test_second_line_has_color_count(self):
        """Second line contains the color count."""
        output = os.path.join(self.tmp.name, "colors.txt")
        self.exporter.export_colors(self.colors, output)
        lines = Path(output).read_text(encoding='utf-8').splitlines()
        self.assertIn(str(len(self.colors)), lines[1])

    def test_colors_in_aarrggbb_format(self):
        """Color entries are in AARRGGBB format with FF alpha."""
        output = os.path.join(self.tmp.name, "colors.txt")
        self.exporter.export_colors(self.colors, output)
        lines = Path(output).read_text(encoding='utf-8').splitlines()
        # Skip comment lines (start with ;)
        color_lines = [l for l in lines if not l.startswith(';')]
        self.assertEqual(color_lines[0], "FFFF0000")  # red
        self.assertEqual(color_lines[1], "FF00FF00")  # lime
        self.assertEqual(color_lines[2], "FF0000FF")  # blue

    def test_all_entries_start_with_ff_alpha(self):
        """All color entries start with 'FF' (full opacity)."""
        output = os.path.join(self.tmp.name, "colors.txt")
        self.exporter.export_colors(self.colors, output)
        lines = Path(output).read_text(encoding='utf-8').splitlines()
        color_lines = [l for l in lines if not l.startswith(';')]
        for line in color_lines:
            self.assertTrue(line.startswith('FF'))

    def test_export_filaments_not_implemented(self):
        """export_filaments raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.exporter.export_filaments([])


class TestLospecExporter(unittest.TestCase):
    """Tests for the Lospec JSON palette format exporter."""

    def setUp(self):
        self.exporter = get_exporter('lospec')
        self.colors = _make_test_colors()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_metadata_name(self):
        """Exporter name is 'lospec'."""
        self.assertEqual(self.exporter.metadata.name, 'lospec')

    def test_metadata_supports_colors(self):
        """Exporter supports colors."""
        self.assertTrue(self.exporter.metadata.supports_colors)

    def test_metadata_does_not_support_filaments(self):
        """Exporter does not support filaments."""
        self.assertFalse(self.exporter.metadata.supports_filaments)

    def test_file_extension(self):
        """File extension is 'json'."""
        self.assertEqual(self.exporter.metadata.file_extension, 'json')

    def test_export_creates_file(self):
        """export_colors creates the output file."""
        output = os.path.join(self.tmp.name, "palette.json")
        result = self.exporter.export_colors(self.colors, output)
        self.assertTrue(Path(result).exists())

    def test_output_is_valid_json(self):
        """Output file is valid JSON."""
        output = os.path.join(self.tmp.name, "palette.json")
        self.exporter.export_colors(self.colors, output)
        content = Path(output).read_text(encoding='utf-8')
        data = json.loads(content)  # Should not raise
        self.assertIsInstance(data, dict)

    def test_json_has_name_field(self):
        """JSON output has 'name' field."""
        output = os.path.join(self.tmp.name, "mypalette.json")
        self.exporter.export_colors(self.colors, output)
        data = json.loads(Path(output).read_text(encoding='utf-8'))
        self.assertIn('name', data)

    def test_json_name_is_stem(self):
        """JSON 'name' field equals the filename stem."""
        output = os.path.join(self.tmp.name, "mypalette.json")
        self.exporter.export_colors(self.colors, output)
        data = json.loads(Path(output).read_text(encoding='utf-8'))
        self.assertEqual(data['name'], 'mypalette')

    def test_json_has_author_field(self):
        """JSON output has 'author' field (empty string)."""
        output = os.path.join(self.tmp.name, "palette.json")
        self.exporter.export_colors(self.colors, output)
        data = json.loads(Path(output).read_text(encoding='utf-8'))
        self.assertIn('author', data)

    def test_json_has_colors_array(self):
        """JSON output has 'colors' array."""
        output = os.path.join(self.tmp.name, "palette.json")
        self.exporter.export_colors(self.colors, output)
        data = json.loads(Path(output).read_text(encoding='utf-8'))
        self.assertIn('colors', data)
        self.assertIsInstance(data['colors'], list)

    def test_colors_are_lowercase_hex_no_hash(self):
        """Colors array contains lowercase hex codes without # prefix."""
        output = os.path.join(self.tmp.name, "palette.json")
        self.exporter.export_colors(self.colors, output)
        data = json.loads(Path(output).read_text(encoding='utf-8'))
        self.assertEqual(data['colors'][0], 'ff0000')
        self.assertEqual(data['colors'][1], '00ff00')
        self.assertEqual(data['colors'][2], '0000ff')

    def test_colors_count_matches_input(self):
        """Colors array length matches input colors count."""
        output = os.path.join(self.tmp.name, "palette.json")
        self.exporter.export_colors(self.colors, output)
        data = json.loads(Path(output).read_text(encoding='utf-8'))
        self.assertEqual(len(data['colors']), len(self.colors))

    def test_export_filaments_not_implemented(self):
        """export_filaments raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.exporter.export_filaments([])


if __name__ == '__main__':
    unittest.main()

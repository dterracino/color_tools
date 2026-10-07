"""Structural and API tests for the extended palette exporter set."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from ast import literal_eval
from dataclasses import replace
from pathlib import Path
from typing import Any

from color_tools.exporters import (
    GLSLExportOptions,
    MissingExporterDependencyError,
    PaintNetExportOptions,
    get_exporter,
    list_export_formats,
)
from color_tools.exporters.python_exporter import PythonExportOptions
from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.palette_metadata import PaletteMetadata
from color_tools.exporters.swatch_image_exporter import SwatchImageOptions
from tests.test_exporters_palette_formats import _make_test_colors


class ExtendedExporterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.colors = _make_test_colors()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.output_directory = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def output_path(self, filename: str) -> Path:
        return self.output_directory / "nested" / filename


class TestExporterRegistry(ExtendedExporterTestCase):
    def test_all_extended_formats_are_registered(self) -> None:
        formats = list_export_formats("colors", available_only=False)

        self.assertTrue(
            {
                "ase",
                "css",
                "glsl",
                "kpl",
                "python",
                "riff_pal",
                "scribus",
                "sketchpalette",
                "soc",
                "swatch_image",
            }.issubset(formats)
        )

    def test_available_only_filters_missing_ase_dependency(self) -> None:
        if importlib.util.find_spec("swatch") is not None:
            self.skipTest("swatch is installed")

        self.assertNotIn("ase", list_export_formats("colors"))
        self.assertIn(
            "ase",
            list_export_formats("colors", available_only=False),
        )

    def test_wrong_options_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "PaintNetExportOptions",
        ):
            get_exporter("paintnet").export_colors(
                self.colors,
                self.output_path("palette.txt"),
                options=SwatchImageOptions(),
            )


class TestPaletteAwareLegacyExporters(ExtendedExporterTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.palette = PaletteExportData(
            self.colors,
            PaletteMetadata(
                name="Primary Colors",
                author="Color Tools",
                description="Bright RGB primaries",
                columns=2,
                tags=(" bright ", "rgb"),
            ),
        )

    def test_gpl_preserves_supported_metadata(self) -> None:
        path = self.output_path("palette.gpl")
        get_exporter("gpl").export_palette(self.palette, path)
        content = path.read_text(encoding="utf-8")

        self.assertIn("Name: Primary Colors\n", content)
        self.assertIn("Columns: 2\n", content)
        self.assertIn("# Author: Color Tools\n", content)
        self.assertIn("# Description: Bright RGB primaries\n", content)
        self.assertIn("# Tags: bright, rgb\n", content)

    def test_json_preserves_complete_palette_metadata(self) -> None:
        path = self.output_path("palette.json")
        get_exporter("json").export_palette(self.palette, path)
        data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(data["metadata"]["name"], "Primary Colors")
        self.assertEqual(data["metadata"]["columns"], 2)
        self.assertEqual(data["metadata"]["tags"], ["bright", "rgb"])
        self.assertEqual(len(data["colors"]), 3)

    def test_lospec_preserves_name_and_author(self) -> None:
        path = self.output_path("palette.json")
        get_exporter("lospec").export_palette(self.palette, path)
        data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(data["name"], "Primary Colors")
        self.assertEqual(data["author"], "Color Tools")
        self.assertEqual(data["colors"], ["ff0000", "00ff00", "0000ff"])


class TestPaintNetExtendedBehavior(ExtendedExporterTestCase):
    def test_palette_can_be_padded_to_exactly_96_entries(self) -> None:
        path = self.output_path("palette.txt")

        get_exporter("paintnet").export_colors(
            self.colors,
            path,
            options=PaintNetExportOptions(pad_to_96=True),
        )

        color_lines = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith(";")
        ]

        self.assertEqual(len(color_lines), 96)
        self.assertEqual(color_lines[:3], [
            "FFFF0000",
            "FF00FF00",
            "FF0000FF",
        ])
        self.assertEqual(color_lines[-1], "FFFFFFFF")

    def test_more_than_96_entries_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at most 96"):
            get_exporter("paintnet").export_colors(
                [self.colors[0]] * 97,
                self.output_path("too-many.txt"),
            )


class TestCSSExporter(ExtendedExporterTestCase):
    def test_css_names_are_sanitized_and_deduplicated(self) -> None:
        colors = [
            replace(self.colors[0], name="Warm Red!"),
            replace(self.colors[0], name="Warm Red!"),
            replace(self.colors[1], name="123 Lime"),
        ]
        path = self.output_path("palette.css")

        get_exporter("css").export_colors(colors, path)

        content = path.read_text(encoding="utf-8")
        self.assertIn("--warm-red: #FF0000;", content)
        self.assertIn("--warm-red-2: #FF0000;", content)
        self.assertIn("--color-123-lime: #00FF00;", content)


class TestPythonExporter(ExtendedExporterTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.palette = PaletteExportData(
            self.colors,
            PaletteMetadata(
                name="Primary Colors",
                author="Color Tools",
                description="Bright RGB primaries",
                columns=2,
                tags=("bright", "rgb"),
                properties={"role": "demo"},
            ),
        )

    def test_palette_dict_includes_metadata_block(self) -> None:
        path = self.output_path("palette.py")

        get_exporter("python").export_palette(
            self.palette,
            path,
        )

        content = path.read_text(encoding="utf-8")
        self.assertIn('"""Palette generated by color_tools."""', content)
        self.assertIn(
            "PALETTE_METADATA: dict[str, object] = {",
            content,
        )
        self.assertIn('"name": \'Primary Colors\'', content)
        self.assertIn('"properties": {\'role\': \'demo\'}', content)
        self.assertIn(
            "PALETTE: dict[str, tuple[int, int, int]] = {",
            content,
        )
        self.assertIn("'red': (255, 0, 0),", content)

    def test_constants_representation_sanitizes_and_deduplicates_names(
        self,
    ) -> None:
        colors = [
            replace(self.colors[0], name="80's Neon!"),
            replace(self.colors[1], name="80's Neon!"),
            replace(self.colors[2], name=""),
        ]
        path = self.output_path("palette_constants.py")

        get_exporter("python").export_colors(
            colors,
            path,
            options=PythonExportOptions(
                representation="constants",
            ),
        )

        content = path.read_text(encoding="utf-8")
        annotation = ": tuple[int, int, int] = "
        self.assertIn(f"_80_S_NEON{annotation}(255, 0, 0)", content)
        self.assertIn(f"_80_S_NEON_2{annotation}(0, 255, 0)", content)
        self.assertIn(f"_0000FF{annotation}(0, 0, 255)", content)

    def test_list_representation_supports_normalized_rgba(self) -> None:
        path = self.output_path("palette_list.py")

        get_exporter("python").export_colors(
            self.colors,
            path,
            options=PythonExportOptions(
                representation="list",
                normalized=True,
                include_alpha=True,
                precision=3,
            ),
        )

        content = path.read_text(encoding="utf-8")
        self.assertIn(
            "PALETTE: list[tuple[float, float, float, float]] = [",
            content,
        )
        self.assertIn("(1.000, 0.000, 0.000, 1.000),  # red", content)
        self.assertIn("(0.000, 1.000, 0.000, 1.000),  # lime", content)

    def test_hex_dict_representation_is_parseable_python(self) -> None:
        path = self.output_path("palette_hex.py")

        get_exporter("python").export_colors(
            self.colors,
            path,
            options=PythonExportOptions(
                value_format="hex",
                variable_name="GAME_COLORS",
            ),
        )

        content = path.read_text(encoding="utf-8")
        palette_source = content.partition(
            "GAME_COLORS: dict[str, str] = "
        )[2].strip()
        parsed = literal_eval(palette_source)

        self.assertEqual(
            parsed,
            {
                "red": "#FF0000",
                "lime": "#00FF00",
                "blue": "#0000FF",
            },
        )

    def test_all_palette_shapes_have_complete_type_annotations(self) -> None:
        cases = (
            (
                PythonExportOptions(representation="dict"),
                "PALETTE: dict[str, tuple[int, int, int]] = {",
            ),
            (
                PythonExportOptions(
                    representation="list",
                    include_alpha=True,
                ),
                "PALETTE: list[tuple[int, int, int, int]] = [",
            ),
            (
                PythonExportOptions(
                    representation="tuple",
                    normalized=True,
                ),
                "PALETTE: tuple[tuple[float, float, float], ...] = (",
            ),
            (
                PythonExportOptions(
                    representation="tuple",
                    normalized=True,
                    include_alpha=True,
                ),
                "PALETTE: tuple[tuple[float, float, float, float], ...] = (",
            ),
            (
                PythonExportOptions(
                    representation="list",
                    value_format="hex",
                ),
                "PALETTE: list[str] = [",
            ),
        )

        for index, (options, expected) in enumerate(cases):
            with self.subTest(options=options):
                path = self.output_path(f"typed_palette_{index}.py")
                get_exporter("python").export_colors(
                    [],
                    path,
                    options=options,
                )

                self.assertIn(
                    expected,
                    path.read_text(encoding="utf-8"),
                )

    def test_all_generated_code_passes_strict_pyright(self) -> None:
        strict_directory = self.output_directory / "strict_python"
        strict_directory.mkdir()

        cases = (
            PythonExportOptions(representation="dict"),
            PythonExportOptions(
                representation="list",
                include_alpha=True,
            ),
            PythonExportOptions(
                representation="tuple",
                normalized=True,
            ),
            PythonExportOptions(
                representation="constants",
                normalized=True,
                include_alpha=True,
            ),
            PythonExportOptions(
                representation="dict",
                value_format="hex",
            ),
        )
        exporter = get_exporter("python")

        for index, options in enumerate(cases):
            exporter.export_colors(
                self.colors,
                strict_directory / f"palette_{index}.py",
                options=options,
            )

            if options.representation != "constants":
                exporter.export_colors(
                    [],
                    strict_directory / f"empty_palette_{index}.py",
                    options=options,
                )

        exporter.export_palette(
            PaletteExportData(
                self.colors,
                PaletteMetadata(
                    name="Strict Metadata",
                    properties={
                        "empty_dict": {},
                        "empty_list": [],
                    },
                ),
            ),
            strict_directory / "palette_with_metadata.py",
        )

        config_path = strict_directory / "pyrightconfig.json"
        config_path.write_text(
            json.dumps(
                {
                    "include": ["*.py"],
                    "typeCheckingMode": "strict",
                    "pythonVersion": "3.10",
                }
            ),
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pyright",
                "--project",
                str(config_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=(
                "Generated Python palettes failed strict Pyright checking:\n"
                f"{result.stdout}\n{result.stderr}"
            ),
        )


class TestGLSLExporter(ExtendedExporterTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.palette = PaletteExportData(
            self.colors,
            PaletteMetadata(
                name="Primary Colors",
                author="Color Tools",
                description="Bright\nRGB primaries",
                tags=("shader", "rgb"),
            ),
        )

    def test_default_array_uses_normalized_vec3_values(self) -> None:
        path = self.output_path("palette.glsl")

        get_exporter("glsl").export_colors(self.colors, path)

        content = path.read_text(encoding="utf-8")
        self.assertIn("const int PALETTE_SIZE = 3;", content)
        self.assertIn("const vec3 PALETTE[3] = vec3[3](", content)
        self.assertIn(
            "vec3(1.000000, 0.000000, 0.000000),  // red",
            content,
        )
        self.assertIn(
            "vec3(0.000000, 0.000000, 1.000000)  // blue",
            content,
        )

    def test_defines_support_raw_rgba_and_unique_identifiers(self) -> None:
        colors = [
            replace(self.colors[0], name="80's Neon!"),
            replace(self.colors[1], name="80's Neon!"),
            replace(self.colors[2], name=""),
        ]
        path = self.output_path("palette_defines.glsl")

        get_exporter("glsl").export_colors(
            colors,
            path,
            options=GLSLExportOptions(
                representation="defines",
                normalized=False,
                include_alpha=True,
                identifier_prefix="GAME_",
            ),
        )

        content = path.read_text(encoding="utf-8")
        self.assertIn("#define PALETTE_SIZE 3", content)
        self.assertIn(
            "#define GAME_80_S_NEON vec4(255.0, 0.0, 0.0, 255.0)",
            content,
        )
        self.assertIn(
            "#define GAME_80_S_NEON_2 vec4(0.0, 255.0, 0.0, 255.0)",
            content,
        )
        self.assertIn(
            "#define GAME_0000FF vec4(0.0, 0.0, 255.0, 255.0)",
            content,
        )

    def test_constants_can_include_version_and_palette_metadata(self) -> None:
        path = self.output_path("palette_constants.glsl")

        get_exporter("glsl").export_palette(
            self.palette,
            path,
            options=GLSLExportOptions(
                representation="constants",
                include_version=True,
                version="330 core",
                identifier_prefix="DEMO_",
                precision=3,
            ),
        )

        content = path.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("#version 330 core\n"))
        self.assertIn("// Name: Primary Colors", content)
        self.assertIn("// Author: Color Tools", content)
        self.assertIn("// Description: Bright RGB primaries", content)
        self.assertIn("// Tags: shader, rgb", content)
        self.assertIn(
            "const vec3 DEMO_RED = vec3(1.000, 0.000, 0.000);",
            content,
        )

    def test_options_reject_invalid_values(self) -> None:
        invalid_cases = (
            ({"representation": "tuple"}, "representation"),
            ({"variable_name": "3_PALETTE"}, "variable_name"),
            ({"variable_name": "gl_palette"}, "reserved 'gl_'"),
            ({"identifier_prefix": "bad-prefix"}, "identifier_prefix"),
            ({"precision": 0}, "precision"),
            ({"version": "latest"}, "version"),
        )

        for values, message in invalid_cases:
            with self.subTest(values=values):
                with self.assertRaisesRegex(ValueError, message):
                    GLSLExportOptions(**values)  # type: ignore[arg-type]

    def test_empty_palette_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one color"):
            get_exporter("glsl").export_colors(
                [],
                self.output_path("empty.glsl"),
            )

    @unittest.skipUnless(
        shutil.which("glslangValidator"),
        "glslangValidator is not installed",
    )
    def test_generated_representations_compile_as_fragment_shaders(self) -> None:
        cases = (
            (
                "array",
                GLSLExportOptions(
                    representation="array",
                    include_version=True,
                ),
                "vec4(PALETTE[0], 1.0)",
            ),
            (
                "constants",
                GLSLExportOptions(
                    representation="constants",
                    include_version=True,
                ),
                "vec4(RED, 1.0)",
            ),
            (
                "defines",
                GLSLExportOptions(
                    representation="defines",
                    normalized=False,
                    include_alpha=True,
                    include_version=True,
                ),
                "RED",
            ),
        )

        for name, options, expression in cases:
            with self.subTest(representation=name):
                path = self.output_path(f"compiled_{name}.frag")
                get_exporter("glsl").export_colors(
                    self.colors,
                    path,
                    options=options,
                )
                with path.open("a", encoding="utf-8", newline="\n") as shader:
                    shader.write(
                        "\nlayout(location = 0) out vec4 fragment_color;\n"
                        "void main() {\n"
                        f"    fragment_color = {expression};\n"
                        "}\n"
                    )

                result = subprocess.run(
                    ["glslangValidator", "-S", "frag", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    msg=(
                        "Generated GLSL failed to compile:\n"
                        f"{result.stdout}\n{result.stderr}"
                    ),
                )


class TestRiffPalExporter(ExtendedExporterTestCase):
    def test_riff_header_sizes_and_entries_are_valid(self) -> None:
        path = self.output_path("palette.pal")
        get_exporter("riff_pal").export_colors(self.colors, path)
        payload = path.read_bytes()

        self.assertEqual(payload[:4], b"RIFF")
        self.assertEqual(struct.unpack_from("<I", payload, 4)[0], len(payload) - 8)
        self.assertEqual(payload[8:12], b"PAL ")
        self.assertEqual(payload[12:16], b"data")
        self.assertEqual(struct.unpack_from("<I", payload, 16)[0], 16)
        self.assertEqual(struct.unpack_from("<HH", payload, 20), (0x0300, 3))
        self.assertEqual(payload[24:28], bytes((255, 0, 0, 0)))


class TestSketchPaletteExporter(ExtendedExporterTestCase):
    def test_sketchpalette_contains_normalized_rgba_colors(self) -> None:
        path = self.output_path("palette.sketchpalette")
        get_exporter("sketchpalette").export_colors(self.colors, path)
        data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(data["compatibleVersion"], "1.4")
        self.assertEqual(
            data["colors"][0],
            {"red": 1.0, "green": 0.0, "blue": 0.0, "alpha": 1.0},
        )


class TestXMLExporters(ExtendedExporterTestCase):
    def test_scribus_palette_preserves_name_and_rgb(self) -> None:
        path = self.output_path("palette.xml")
        palette = PaletteExportData(
            self.colors,
            PaletteMetadata(name="Primary & Bright"),
        )

        get_exporter("scribus").export_palette(palette, path)
        root = ET.parse(path).getroot()

        self.assertEqual(root.tag, "SCRIBUSCOLORS")
        self.assertEqual(root.attrib["Name"], "Primary & Bright")
        self.assertEqual(root[0].attrib["RGB"], "#FF0000")

    def test_soc_palette_uses_expected_namespaces_and_values(self) -> None:
        path = self.output_path("palette.soc")
        get_exporter("soc").export_colors(self.colors, path)
        root = ET.parse(path).getroot()
        office_namespace = "http://openoffice.org/2004/office"
        draw_namespace = (
            "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
        )

        self.assertEqual(root.tag, f"{{{office_namespace}}}color-table")
        self.assertEqual(root[0].tag, f"{{{draw_namespace}}}color")
        self.assertEqual(root[0].attrib[f"{{{draw_namespace}}}name"], "red")
        self.assertEqual(root[0].attrib[f"{{{draw_namespace}}}color"], "#ff0000")


class TestKPLExporter(ExtendedExporterTestCase):
    def test_kpl_archive_contains_metadata_grid_and_srgb_entries(self) -> None:
        path = self.output_path("palette.kpl")
        palette = PaletteExportData(
            self.colors,
            PaletteMetadata(
                name="Primary Colors",
                description="RGB test palette",
                columns=2,
            ),
        )

        get_exporter("kpl").export_palette(palette, path)

        with zipfile.ZipFile(path) as archive:
            self.assertEqual(
                archive.namelist(),
                ["mimetype", "colorset.xml", "profiles.xml"],
            )
            self.assertEqual(
                archive.read("mimetype"),
                b"application/x-krita-palette",
            )
            self.assertEqual(
                archive.getinfo("mimetype").compress_type,
                zipfile.ZIP_STORED,
            )
            root = ET.fromstring(archive.read("colorset.xml"))

        self.assertEqual(root.attrib["name"], "Primary Colors")
        self.assertEqual(root.attrib["comment"], "RGB test palette")
        self.assertEqual(root.attrib["columns"], "2")
        self.assertEqual(root.attrib["rows"], "2")
        first_position = root[0].find("Position")
        third_position = root[2].find("Position")
        assert first_position is not None
        assert third_position is not None
        self.assertEqual(first_position.attrib, {"row": "0", "column": "0"})
        self.assertEqual(third_position.attrib, {"row": "1", "column": "0"})


class TestASEExporterDependency(ExtendedExporterTestCase):
    def test_available_dependency_writes_parseable_grouped_ase(self) -> None:
        if importlib.util.find_spec("swatch") is None:
            self.skipTest("swatch is not installed")

        import swatch

        path = self.output_path("palette.ase")
        palette = PaletteExportData(
            self.colors,
            PaletteMetadata(name="Primary Colors"),
        )

        get_exporter("ase").export_palette(palette, path)
        parsed: Any = swatch.parse(str(path))

        self.assertEqual(parsed[0]["name"], "Primary Colors")
        self.assertEqual(parsed[0]["type"], "Color Group")
        self.assertEqual(len(parsed[0]["swatches"]), 3)
        self.assertEqual(
            parsed[0]["swatches"][0]["data"]["values"],
            [1.0, 0.0, 0.0],
        )

    def test_missing_dependency_has_actionable_error(self) -> None:
        exporter = get_exporter("ase")

        if exporter.is_available:
            self.skipTest("swatch is installed")

        with self.assertRaises(MissingExporterDependencyError) as context:
            exporter.export_colors(
                self.colors,
                self.output_path("palette.ase"),
            )

        self.assertIn("swatch", str(context.exception))
        self.assertIn("image", str(context.exception))


if __name__ == "__main__":
    unittest.main()

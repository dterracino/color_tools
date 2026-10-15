"""Protocol-level tests for the Color Tools MCP server."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from mcp.client import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

from color_tools.config import config_context
from color_tools.conversions import rgb_to_xyz
from color_tools.filament_palette import FilamentPalette, FilamentRecord
from color_tools.mcp.server import (
    _filament_palette,
    _filament_palette_for_mode,
    convert_color,
    mcp,
)
from color_tools.mcp.models import ColorSpace


class TestMCPServer(unittest.IsolatedAsyncioTestCase):
    """Exercise tools through the MCP client rather than direct function calls."""

    def test_filament_cache_distinguishes_modes(self) -> None:
        def load() -> FilamentPalette:
            return FilamentPalette([
                FilamentRecord(
                    id="probe", maker="probe", type="PLA", finish=None,
                    color="probe", hex="#FF0000-#0000FF",
                )
            ])

        _filament_palette_for_mode.cache_clear()
        try:
            with patch.object(FilamentPalette, "load_default", side_effect=load) as loader:
                with config_context(multi_color_mode="first"):
                    first = _filament_palette()
                with config_context(multi_color_mode="last"):
                    last = _filament_palette()
                self.assertEqual(first.records[0].rgb, (255, 0, 0))
                self.assertEqual(last.records[0].rgb, (0, 0, 255))
                with config_context(multi_color_mode="first"):
                    self.assertIs(_filament_palette(), first)
                self.assertEqual(loader.call_count, 2)
        finally:
            _filament_palette_for_mode.cache_clear()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call one tool and return its validated structured content."""
        async with Client(mcp, raise_exceptions=True) as client:
            result = await client.call_tool(name, arguments)
        self.assertFalse(result.is_error)
        self.assertIsNotNone(result.structured_content)
        return result.structured_content or {}

    async def test_tool_catalog_has_structured_schemas(self) -> None:
        """All public tools should advertise input and output schemas."""
        async with Client(mcp, raise_exceptions=True) as client:
            result = await client.list_tools()

        tools = {tool.name: tool for tool in result.tools}
        self.assertEqual(
            set(tools),
            {
                "analyze_color",
                "convert_color",
                "compare_colors",
                "find_named_colors",
                "find_filaments",
                "get_filament_catalog",
                "transform_color_vision",
                "map_to_srgb_gamut",
                "validate_color_name",
            },
        )
        self.assertTrue(all(tool.output_schema for tool in tools.values()))
        self.assertTrue(all(not self._contains_array(tool.input_schema) for tool in tools.values()))

    async def test_stdio_tool_schemas_are_array_free(self) -> None:
        """The actual stdio wire schemas should avoid arrays that VS Code's adapter corrupts."""
        project_root = Path(__file__).resolve().parents[1]
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "color_tools.mcp"],
            cwd=project_root,
        )
        async with Client(stdio_client(parameters), mode="legacy", raise_exceptions=True) as client:
            result = await client.list_tools()

        self.assertEqual(len(result.tools), 9)
        self.assertTrue(all(not self._contains_array(tool.input_schema) for tool in result.tools))

    @classmethod
    def _contains_array(cls, schema: object) -> bool:
        """Return whether a schema contains an array input unsupported by the VS Code adapter."""
        if isinstance(schema, dict):
            fields = cast(dict[object, object], schema)
            if fields.get("type") == "array":
                return True
            return any(cls._contains_array(value) for value in fields.values())
        if isinstance(schema, list):
            elements = cast(list[object], schema)
            return any(cls._contains_array(value) for value in elements)
        return False

    async def test_analyze_color_returns_matches_and_coordinates(self) -> None:
        """Comprehensive analysis should combine color and filament knowledge."""
        result = await self.call_tool(
            "analyze_color",
            {"red": 255, "green": 128, "blue": 64, "named_color_count": 2, "filament_count": 2},
        )
        self.assertEqual(result["coordinates"]["hex"], "#FF8040")
        self.assertEqual(len(result["nearest_named_colors"]), 2)
        self.assertEqual(len(result["nearest_filaments"]), 2)

    async def test_convert_color_reports_out_of_gamut_clamping(self) -> None:
        """LAB conversion should preserve explicit gamut and clipping information."""
        result = await self.call_tool(
            "convert_color",
            {
                "source_space": "lab",
                "target_space": "rgb",
                "component_1": 50.0,
                "component_2": 150.0,
                "component_3": 100.0,
            },
        )
        self.assertFalse(result["in_srgb_gamut"])
        self.assertTrue(result["rgb_was_clamped"])
        self.assertTrue(all(0 <= channel <= 255 for channel in result["target_value"]))

        direct = await self.call_tool(
            "convert_color",
            {
                "source_space": "lab",
                "target_space": "lch",
                "component_1": 50.0,
                "component_2": 150.0,
                "component_3": 100.0,
                "clamp_rgb": False,
            },
        )
        self.assertEqual(direct["target_value"][0], 50.0)
        self.assertAlmostEqual(direct["target_value"][1], 180.27756377319946)

        rgb = await self.call_tool(
            "convert_color",
            {
                "source_space": "rgb",
                "target_space": "lab",
                "component_1": 255,
                "component_2": 128,
                "component_3": 64,
            },
        )
        self.assertEqual(rgb["source_value"], [255.0, 128.0, 64.0])
        self.assertEqual(len(rgb["target_value"]), 3)

    def test_convert_color_rejects_invalid_cmy_percentages(self) -> None:
        """MCP conversion should share the strict CMY/CMYK input contract."""
        with self.assertRaisesRegex(ValueError, "CMY component 1"):
            convert_color("cmy", "rgb", -0.1, 0.0, 0.0)
        with self.assertRaisesRegex(ValueError, "CMYK component 4"):
            convert_color("cmyk", "rgb", 0.0, 0.0, 0.0, 100.1)

    def test_convert_color_rejects_wrong_component_count_for_every_space(
        self,
    ) -> None:
        """Every source space enforces its three- or four-component shape."""
        for source in ("rgb", "xyz", "lab", "lch", "hsl", "cmy"):
            with self.subTest(source=source):
                with self.assertRaisesRegex(
                    ValueError,
                    f"{source.upper()} requires 3 components",
                ):
                    convert_color(
                        cast(ColorSpace, source),
                        "rgb",
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                    )

        with self.assertRaisesRegex(ValueError, "CMYK requires 4 components"):
            convert_color("cmyk", "rgb", 0.0, 0.0, 0.0)

    def test_convert_color_rejects_fractional_rgb_components(self) -> None:
        """RGB input remains integer-only even though MCP numbers are floats."""
        with self.assertRaisesRegex(ValueError, "RGB components must be integers"):
            convert_color("rgb", "lab", 12.5, 34.0, 56.0)

    def test_convert_color_exercises_every_source_space(self) -> None:
        """Each declared source reaches a successful conversion branch."""
        cases: tuple[tuple[ColorSpace, tuple[float, ...]], ...] = (
            ("rgb", (51.0, 102.0, 153.0)),
            ("xyz", (11.866, 12.506, 31.925)),
            ("lab", (42.0, 0.0, 0.0)),
            ("lch", (42.0, 0.0, 0.0)),
            ("hsl", (210.0, 50.0, 40.0)),
            ("cmy", (80.0, 60.0, 40.0)),
            ("cmyk", (66.7, 33.3, 0.0, 40.0)),
        )
        for source, components in cases:
            with self.subTest(source=source):
                fourth = components[3] if len(components) == 4 else None
                result = convert_color(
                    source,
                    "rgb",
                    components[0],
                    components[1],
                    components[2],
                    fourth,
                )
                self.assertEqual(result.source_space, source)
                self.assertEqual(result.target_space, "rgb")
                self.assertEqual(len(result.target_value), 3)

    def test_convert_color_exercises_every_target_space(self) -> None:
        """Each declared target reaches a successful conversion branch."""
        targets: tuple[ColorSpace, ...] = (
            "rgb",
            "xyz",
            "lab",
            "lch",
            "hsl",
            "cmy",
            "cmyk",
        )
        for target in targets:
            with self.subTest(target=target):
                result = convert_color("rgb", target, 51.0, 102.0, 153.0)
                self.assertEqual(result.target_space, target)
                self.assertEqual(len(result.target_value), 4 if target == "cmyk" else 3)

    def test_same_space_conversion_still_validates_input(self) -> None:
        """The identity shortcut must not bypass source validation."""
        with self.assertRaisesRegex(ValueError, "RGB components must be integers"):
            convert_color("rgb", "rgb", 1.5, 2.0, 3.0)
        with self.assertRaisesRegex(ValueError, "CMY component 1"):
            convert_color("cmy", "cmy", 101.0, 0.0, 0.0)

    def test_clamp_option_reaches_rgb_producing_converters(self) -> None:
        """XYZ, LAB, and LCH RGB conversion receives the caller's clamp flag."""
        with patch(
            "color_tools.mcp.server.xyz_to_rgb",
            return_value=(1, 2, 3),
        ) as xyz_converter:
            convert_color("xyz", "rgb", 10.0, 20.0, 30.0, clamp_rgb=False)
            xyz_converter.assert_called_once_with((10.0, 20.0, 30.0), clamp=False)

        for source, components in (
            ("lab", (50.0, 0.0, 0.0)),
            ("lch", (50.0, 0.0, 0.0)),
        ):
            with self.subTest(source=source):
                with patch(
                    "color_tools.mcp.server.lab_to_rgb",
                    return_value=(1, 2, 3),
                ) as lab_converter:
                    convert_color(
                        cast(ColorSpace, source),
                        "rgb",
                        components[0],
                        components[1],
                        components[2],
                        clamp_rgb=False,
                    )
                    lab_converter.assert_called_once_with(
                        (50.0, 0.0, 0.0),
                        clamp=False,
                    )

    def test_unclamped_out_of_gamut_source_rejects_rgb_dependent_target(
        self,
    ) -> None:
        """Non-RGB derived targets cannot consume unclamped out-of-gamut RGB."""
        with self.assertRaisesRegex(
            ValueError,
            "Out-of-gamut source requires clamp_rgb=true",
        ):
            convert_color(
                "lab",
                "hsl",
                50.0,
                150.0,
                100.0,
                clamp_rgb=False,
            )

    async def test_invalid_percentages_use_public_mcp_error_contract(self) -> None:
        """Validation failures become MCP tool errors without structured output."""
        cases = (
            ("cmy", (-0.1, 0.0, 0.0, None), "CMY component 1"),
            ("cmyk", (0.0, 0.0, 0.0, 100.1), "CMYK component 4"),
        )
        async with Client(mcp, raise_exceptions=False) as client:
            for source, components, expected in cases:
                with self.subTest(source=source):
                    arguments: dict[str, object] = {
                        "source_space": source,
                        "target_space": "rgb",
                        "component_1": components[0],
                        "component_2": components[1],
                        "component_3": components[2],
                    }
                    if components[3] is not None:
                        arguments["component_4"] = components[3]
                    result = await client.call_tool("convert_color", arguments)
                    self.assertTrue(result.is_error)
                    self.assertIsNone(result.structured_content)
                    self.assertIn(expected, str(result.content[0]))

    async def test_conversion_tool_returns_complete_public_result(self) -> None:
        """The wire result identifies its source, target, input, and output."""
        result = await self.call_tool(
            "convert_color",
            {
                "source_space": "hsl",
                "target_space": "cmyk",
                "component_1": 210.0,
                "component_2": 50.0,
                "component_3": 40.0,
            },
        )
        self.assertEqual(result["source_space"], "hsl")
        self.assertEqual(result["source_value"], [210.0, 50.0, 40.0])
        self.assertEqual(result["target_space"], "cmyk")
        self.assertEqual(len(result["target_value"]), 4)
        self.assertIn("in_srgb_gamut", result)
        self.assertIn("rgb_was_clamped", result)

    async def test_compare_colors_returns_all_metrics(self) -> None:
        """Identical colors should have zero distance in every metric."""
        result = await self.call_tool(
            "compare_colors",
            {
                "first_red": 12,
                "first_green": 34,
                "first_blue": 56,
                "second_red": 12,
                "second_green": 34,
                "second_blue": 56,
            },
        )
        for key in (
            "delta_e_2000",
            "delta_e_94",
            "delta_e_76",
            "delta_e_cmc_2_1",
            "hyab",
            "rgb_euclidean",
        ):
            self.assertAlmostEqual(result[key], 0.0)

    async def test_xyz_clamping_detects_sub_integer_boundary_deviation(self) -> None:
        xyz = rgb_to_xyz((-0.25, 128.0, 128.0))
        result = await self.call_tool(
            "convert_color",
            {
                "source_space": "xyz", "target_space": "rgb",
                "component_1": xyz[0], "component_2": xyz[1], "component_3": xyz[2],
            },
        )
        self.assertFalse(result["in_srgb_gamut"])
        self.assertTrue(result["rgb_was_clamped"])
        self.assertEqual(result["target_value"][0], 0)

    async def test_named_color_search_supports_bundled_palettes(self) -> None:
        """Named-color matching should load non-CSS palettes by name."""
        result = await self.call_tool(
            "find_named_colors",
            {"red": 255, "green": 0, "blue": 0, "palette": "cga4", "count": 3},
        )
        self.assertEqual(result["palette"], "cga4")
        self.assertEqual(len(result["matches"]), 3)

    async def test_filament_search_and_catalog(self) -> None:
        """Filament tools should expose searchable records and valid facets."""
        catalog = await self.call_tool("get_filament_catalog", {})
        self.assertGreater(catalog["record_count"], 0)
        self.assertIn("Bambu Lab", catalog["makers"])

        result = await self.call_tool(
            "find_filaments",
            {
                "red": 255,
                "green": 0,
                "blue": 0,
                "makers": "Bambu",
                "materials": "PLA",
                "count": 3,
            },
        )
        self.assertTrue(result["matches"])
        self.assertTrue(all(match["maker"] == "Bambu Lab" for match in result["matches"]))

    async def test_compound_filament_wire_output_retains_source_components(self) -> None:
        with config_context(multi_color_mode="last"):
            record = FilamentRecord(
                id="probe", maker="probe", type="PLA", finish=None,
                color="probe", hex="#f00 / #00f",
            )
        palette = FilamentPalette([record])
        with patch("color_tools.mcp.server._filament_palette", return_value=palette):
            result = await self.call_tool(
                "find_filaments", {"red": 0, "green": 0, "blue": 255, "count": 1},
            )
        match = result["matches"][0]
        self.assertEqual(match["hex"], "#f00 / #00f")
        self.assertEqual(match["effective_hex"], "#0000FF")
        self.assertEqual(match["rgb_components"], [[255, 0, 0], [0, 0, 255]])
        self.assertEqual(match["rgb"], [0, 0, 255])
        self.assertNotIn("hex2", match)

    async def test_cvd_gamut_and_validation_tools(self) -> None:
        """Specialist tools should return typed transforms and validation evidence."""
        cvd = await self.call_tool(
            "transform_color_vision",
            {"red": 255, "green": 0, "blue": 0, "deficiency": "deuteranopia"},
        )
        self.assertNotEqual(cvd["original"]["rgb"], cvd["transformed"]["rgb"])

        gamut = await self.call_tool(
            "map_to_srgb_gamut",
            {"lightness": 50.0, "a": 150.0, "b": 100.0},
        )
        self.assertFalse(gamut["was_in_gamut"])
        self.assertGreater(gamut["delta_e_2000"], 0.0)

        validation = await self.call_tool(
            "validate_color_name",
            {"color_name": "light blue", "hex_code": "#ADD8E6"},
        )
        self.assertTrue(validation["is_match"])
        self.assertEqual(validation["suggested_hex"], "#ADD8E6")


if __name__ == "__main__":
    unittest.main()

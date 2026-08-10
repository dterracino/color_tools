"""Protocol-level tests for the Color Tools MCP server."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

from mcp.client import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

from color_tools.mcp.server import mcp


class TestMCPServer(unittest.IsolatedAsyncioTestCase):
    """Exercise tools through the MCP client rather than direct function calls."""

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
    def _contains_array(cls, schema: Any) -> bool:
        """Return whether a schema contains an array input unsupported by the VS Code adapter."""
        if isinstance(schema, dict):
            if schema.get("type") == "array":
                return True
            return any(cls._contains_array(value) for value in schema.values())
        if isinstance(schema, list):
            return any(cls._contains_array(value) for value in schema)
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
"""Protocol-level tests for the Color Tools MCP server."""

from __future__ import annotations

import unittest
from typing import Any

from mcp.client import Client

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
        self.assertTrue(all(self._arrays_have_items(tool.input_schema) for tool in tools.values()))

    @classmethod
    def _arrays_have_items(cls, schema: Any) -> bool:
        """Return whether every array schema includes VS Code-compatible item metadata."""
        if isinstance(schema, dict):
            if schema.get("type") == "array" and "items" not in schema:
                return False
            return all(cls._arrays_have_items(value) for value in schema.values())
        if isinstance(schema, list):
            return all(cls._arrays_have_items(value) for value in schema)
        return True

    async def test_analyze_color_returns_matches_and_coordinates(self) -> None:
        """Comprehensive analysis should combine color and filament knowledge."""
        result = await self.call_tool(
            "analyze_color",
            {"rgb": [255, 128, 64], "named_color_count": 2, "filament_count": 2},
        )
        self.assertEqual(result["coordinates"]["hex"], "#FF8040")
        self.assertEqual(len(result["nearest_named_colors"]), 2)
        self.assertEqual(len(result["nearest_filaments"]), 2)

    async def test_convert_color_reports_out_of_gamut_clamping(self) -> None:
        """LAB conversion should preserve explicit gamut and clipping information."""
        result = await self.call_tool(
            "convert_color",
            {
                "value": [50.0, 150.0, 100.0],
                "source_space": "lab",
                "target_space": "rgb",
            },
        )
        self.assertFalse(result["in_srgb_gamut"])
        self.assertTrue(result["rgb_was_clamped"])
        self.assertTrue(all(0 <= channel <= 255 for channel in result["target_value"]))

        direct = await self.call_tool(
            "convert_color",
            {
                "value": [50.0, 150.0, 100.0],
                "source_space": "lab",
                "target_space": "lch",
                "clamp_rgb": False,
            },
        )
        self.assertEqual(direct["target_value"][0], 50.0)
        self.assertAlmostEqual(direct["target_value"][1], 180.27756377319946)

    async def test_compare_colors_returns_all_metrics(self) -> None:
        """Identical colors should have zero distance in every metric."""
        result = await self.call_tool(
            "compare_colors",
            {"first_rgb": [12, 34, 56], "second_rgb": [12, 34, 56]},
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
            {"rgb": [255, 0, 0], "palette": "cga4", "count": 3},
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
                "rgb": [255, 0, 0],
                "makers": ["Bambu"],
                "materials": ["PLA"],
                "count": 3,
            },
        )
        self.assertTrue(result["matches"])
        self.assertTrue(all(match["maker"] == "Bambu Lab" for match in result["matches"]))

    async def test_cvd_gamut_and_validation_tools(self) -> None:
        """Specialist tools should return typed transforms and validation evidence."""
        cvd = await self.call_tool(
            "transform_color_vision",
            {"rgb": [255, 0, 0], "deficiency": "deuteranopia"},
        )
        self.assertNotEqual(cvd["original"]["rgb"], cvd["transformed"]["rgb"])

        gamut = await self.call_tool(
            "map_to_srgb_gamut",
            {"lab": [50.0, 150.0, 100.0]},
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
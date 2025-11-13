"""
MCP Server for color_tools - exposes color analysis functionality to LLMs.

This server provides tools for:
- Color space conversions
- Color distance calculations
- CSS color matching
- 3D printing filament matching
- Gamut checking

Run with: python -m color_tools.mcp
"""
from __future__ import annotations

import sys
import json
import traceback
from typing import Any, Sequence

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    import mcp.server.stdio
except ImportError:
    print("Error: MCP SDK not installed. Install with: pip install color-match-tools[mcp]", file=sys.stderr)
    sys.exit(1)

# Import color_tools functions
from ..conversions import (
    rgb_to_lab, rgb_to_lch, rgb_to_hsl, rgb_to_hex,
    lab_to_rgb, lch_to_rgb, hsl_to_rgb, hex_to_rgb
)
from ..distance import delta_e_2000, delta_e_94, delta_e_76, delta_e_cmc
from ..palette import Palette, FilamentPalette
from ..gamut import is_in_srgb_gamut, find_nearest_in_gamut


# Initialize server
server = Server("color-tools")

# Load palettes once at startup
_css_palette: Palette | None = None
_filament_palette: FilamentPalette | None = None


def get_css_palette() -> Palette:
    """Lazy load CSS color palette."""
    global _css_palette
    if _css_palette is None:
        _css_palette = Palette.load_default()
    return _css_palette


def get_filament_palette() -> FilamentPalette:
    """Lazy load filament palette."""
    global _filament_palette
    if _filament_palette is None:
        _filament_palette = FilamentPalette.load_default()
    return _filament_palette


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="analyze_color",
            description="Analyze an RGB color and get all color space conversions, nearest CSS color, and gamut status",
            inputSchema={
                "type": "object",
                "properties": {
                    "rgb": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 0, "maximum": 255},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "RGB color values [R, G, B] (0-255)"
                    },
                    "show_nearest_css": {
                        "type": "boolean",
                        "description": "Include nearest CSS color match (default: true)"
                    },
                    "show_nearest_filament": {
                        "type": "boolean",
                        "description": "Include nearest 3D printing filament match (default: false)"
                    },
                },
                "required": ["rgb"]
            }
        ),
        Tool(
            name="find_nearest_css_color",
            description="Find the nearest CSS color to a given RGB color using a specified distance metric",
            inputSchema={
                "type": "object",
                "properties": {
                    "rgb": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 0, "maximum": 255},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "RGB color values [R, G, B] (0-255)"
                    },
                    "metric": {
                        "type": "string",
                        "enum": ["de2000", "de94", "de76", "cmc"],
                        "description": "Distance metric to use (default: de2000)"
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "description": "Maximum number of results to return (default: 1)"
                    }
                },
                "required": ["rgb"]
            }
        ),
        Tool(
            name="find_nearest_filament",
            description="Find the nearest 3D printing filament color to a given RGB color",
            inputSchema={
                "type": "object",
                "properties": {
                    "rgb": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 0, "maximum": 255},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "RGB color values [R, G, B] (0-255)"
                    },
                    "maker": {
                        "type": "string",
                        "description": "Filter by manufacturer name (optional, supports synonyms)"
                    },
                    "type": {
                        "type": "string",
                        "description": "Filter by filament type like PLA, PETG, ABS (optional)"
                    },
                    "finish": {
                        "type": "string",
                        "description": "Filter by finish like Matte, Silk, Basic (optional)"
                    },
                    "metric": {
                        "type": "string",
                        "enum": ["de2000", "de94", "de76", "cmc"],
                        "description": "Distance metric to use (default: de2000)"
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "description": "Maximum number of results to return (default: 5)"
                    }
                },
                "required": ["rgb"]
            }
        ),
        Tool(
            name="convert_color_space",
            description="Convert a color between different color spaces (RGB, LAB, LCH, HSL)",
            inputSchema={
                "type": "object",
                "properties": {
                    "value": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Color value as 3-element array"
                    },
                    "from_space": {
                        "type": "string",
                        "enum": ["rgb", "lab", "lch", "hsl", "hex"],
                        "description": "Source color space"
                    },
                    "to_space": {
                        "type": "string",
                        "enum": ["rgb", "lab", "lch", "hsl", "hex"],
                        "description": "Target color space"
                    },
                    "check_gamut": {
                        "type": "boolean",
                        "description": "Check if LAB/LCH color is in sRGB gamut (default: false)"
                    }
                },
                "required": ["value", "from_space", "to_space"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls from the LLM."""
    try:
        if name == "analyze_color":
            return await analyze_color_tool(arguments)
        elif name == "find_nearest_css_color":
            return await find_nearest_css_color_tool(arguments)
        elif name == "find_nearest_filament":
            return await find_nearest_filament_tool(arguments)
        elif name == "convert_color_space":
            return await convert_color_space_tool(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}\n{traceback.format_exc()}"
        return [TextContent(type="text", text=error_msg)]


async def analyze_color_tool(args: dict[str, Any]) -> Sequence[TextContent]:
    """Analyze an RGB color comprehensively."""
    rgb = tuple(args["rgb"])
    show_css = args.get("show_nearest_css", True)
    show_filament = args.get("show_nearest_filament", False)
    
    # Convert to all color spaces
    lab = rgb_to_lab(rgb)
    lch = rgb_to_lch(rgb)
    hsl = rgb_to_hsl(rgb)
    hex_code = rgb_to_hex(rgb)
    
    # Check gamut
    in_gamut = is_in_srgb_gamut(lab)
    
    # Build result
    result = [
        f"🎨 **Color Analysis**",
        f"",
        f"**Input:** RGB{rgb}",
        f"**Hex:** {hex_code}",
        f"",
        f"**Color Space Conversions:**",
        f"- LAB: L*={lab[0]:.1f}, a*={lab[1]:.1f}, b*={lab[2]:.1f}",
        f"- LCH: L*={lch[0]:.1f}, C*={lch[1]:.1f}, h°={lch[2]:.1f}",
        f"- HSL: H={hsl[0]:.1f}°, S={hsl[1]:.1f}%, L={hsl[2]:.1f}%",
        f"",
        f"**Gamut Status:** {'✓ In sRGB gamut' if in_gamut else '⚠ Out of sRGB gamut'}",
    ]
    
    # Add nearest CSS color
    if show_css:
        palette = get_css_palette()
        color, distance = palette.nearest_color(rgb, space="rgb")
        result.extend([
            f"",
            f"**Nearest CSS Color:**",
            f"- Name: **{color.name}**",
            f"- RGB: {color.rgb}",
            f"- Hex: {color.hex}",
            f"- Delta E (ΔE): {distance:.2f}",
        ])
    
    # Add nearest filament
    if show_filament:
        palette = get_filament_palette()
        filament, distance = palette.nearest_filament(rgb)
        result.extend([
            f"",
            f"**Nearest 3D Printing Filament:**",
            f"- Maker: {filament.maker}",
            f"- Type: {filament.type}",
            f"- Finish: {filament.finish or 'N/A'}",
            f"- Color: **{filament.color}**",
            f"- Hex: {filament.hex}",
            f"- Delta E (ΔE): {distance:.2f}",
        ])
    
    return [TextContent(type="text", text="\n".join(result))]


async def find_nearest_css_color_tool(args: dict[str, Any]) -> Sequence[TextContent]:
    """Find nearest CSS color(s)."""
    rgb = tuple(args["rgb"])
    metric = args.get("metric", "de2000")
    max_results = args.get("max_results", 1)
    
    # Get metric function
    metric_funcs = {
        "de2000": delta_e_2000,
        "de94": delta_e_94,
        "de76": delta_e_76,
        "cmc": delta_e_cmc,
    }
    metric_func = metric_funcs[metric]
    
    # Get palette and find nearest
    palette = get_css_palette()
    lab = rgb_to_lab(rgb)
    
    # Calculate distances to all colors
    distances = []
    for color in palette.records:
        dist = metric_func(lab, color.lab)
        distances.append((color, dist))
    
    # Sort and get top N
    distances.sort(key=lambda x: x[1])
    top_matches = distances[:max_results]
    
    # Build result
    result = [
        f"🎨 **Nearest CSS Colors to RGB{rgb}**",
        f"Using metric: {metric.upper()}",
        f"",
    ]
    
    for i, (color, distance) in enumerate(top_matches, 1):
        result.extend([
            f"**{i}. {color.name}**",
            f"   - RGB: {color.rgb}",
            f"   - Hex: {color.hex}",
            f"   - Delta E (ΔE): {distance:.2f}",
            f"",
        ])
    
    return [TextContent(type="text", text="\n".join(result))]


async def find_nearest_filament_tool(args: dict[str, Any]) -> Sequence[TextContent]:
    """Find nearest filament(s) with optional filters."""
    rgb = tuple(args["rgb"])
    maker = args.get("maker")
    filament_type = args.get("type")
    finish = args.get("finish")
    metric = args.get("metric", "de2000")
    max_results = args.get("max_results", 5)
    
    # Get metric function
    metric_funcs = {
        "de2000": delta_e_2000,
        "de94": delta_e_94,
        "de76": delta_e_76,
        "cmc": delta_e_cmc,
    }
    metric_func = metric_funcs[metric]
    
    # Get palette
    palette = get_filament_palette()
    
    # Apply filters
    filaments = palette.filter(
        maker=maker,
        type_name=filament_type,
        finish=finish
    )
    
    if not filaments:
        return [TextContent(type="text", text=f"No filaments found matching filters: maker={maker}, type={filament_type}, finish={finish}")]
    
    # Calculate distances
    lab = rgb_to_lab(rgb)
    distances = []
    for filament in filaments:
        dist = metric_func(lab, filament.lab)
        distances.append((filament, dist))
    
    # Sort and get top N
    distances.sort(key=lambda x: x[1])
    top_matches = distances[:max_results]
    
    # Build result
    filters_applied = []
    if maker:
        filters_applied.append(f"Maker: {maker}")
    if filament_type:
        filters_applied.append(f"Type: {filament_type}")
    if finish:
        filters_applied.append(f"Finish: {finish}")
    
    result = [
        f"🧵 **Nearest 3D Printing Filaments to RGB{rgb}**",
        f"Using metric: {metric.upper()}",
    ]
    
    if filters_applied:
        result.append(f"Filters: {', '.join(filters_applied)}")
    
    result.append("")
    
    for i, (filament, distance) in enumerate(top_matches, 1):
        result.extend([
            f"**{i}. {filament.maker} - {filament.color}**",
            f"   - Type: {filament.type}",
            f"   - Finish: {filament.finish or 'N/A'}",
            f"   - Hex: {filament.hex}",
            f"   - RGB: {filament.rgb}",
            f"   - Delta E (ΔE): {distance:.2f}",
            f"",
        ])
    
    return [TextContent(type="text", text="\n".join(result))]


async def convert_color_space_tool(args: dict[str, Any]) -> Sequence[TextContent]:
    """Convert between color spaces."""
    value = args["value"]
    from_space = args["from_space"]
    to_space = args["to_space"]
    check_gamut = args.get("check_gamut", False)
    
    # Special handling for hex
    if from_space == "hex":
        # Expect a single string, not array
        if isinstance(value, str):
            rgb_result = hex_to_rgb(value)
            if rgb_result is None:
                return [TextContent(type="text", text=f"Invalid hex color: {value}")]
            value = list(rgb_result)
            from_space = "rgb"
    
    # Ensure value is a 3-element tuple/list
    if len(value) != 3:
        return [TextContent(type="text", text=f"Color value must have exactly 3 components, got {len(value)}")]
    
    # Convert to RGB first if needed
    rgb: tuple[int, int, int] | tuple[float, float, float]
    if from_space == "rgb":
        rgb = (int(value[0]), int(value[1]), int(value[2]))
    elif from_space == "lab":
        lab_val = (float(value[0]), float(value[1]), float(value[2]))
        rgb = lab_to_rgb(lab_val)
    elif from_space == "lch":
        lch_val = (float(value[0]), float(value[1]), float(value[2]))
        rgb = lch_to_rgb(lch_val)
    elif from_space == "hsl":
        hsl_val = (float(value[0]), float(value[1]), float(value[2]))
        rgb = hsl_to_rgb(hsl_val)
    else:
        return [TextContent(type="text", text=f"Unknown source color space: {from_space}")]
    
    # Ensure RGB is integers
    rgb_int = (int(round(rgb[0])), int(round(rgb[1])), int(round(rgb[2])))
    
    # Convert from RGB to target
    result_value: tuple[int, int, int] | tuple[float, float, float] | str
    if to_space == "rgb":
        result_value = rgb_int
    elif to_space == "lab":
        result_value = rgb_to_lab(rgb_int)
    elif to_space == "lch":
        result_value = rgb_to_lch(rgb_int)
    elif to_space == "hsl":
        result_value = rgb_to_hsl(rgb_int)
    elif to_space == "hex":
        result_value = rgb_to_hex(rgb_int)
    else:
        return [TextContent(type="text", text=f"Unknown target color space: {to_space}")]
    
    # Build response
    response = [
        f"🔄 **Color Space Conversion**",
        f"",
        f"**From:** {from_space.upper()}{tuple(value)}",
        f"**To:** {to_space.upper()}",
    ]
    
    if to_space == "hex":
        response.append(f"**Result:** {result_value}")
    else:
        response.append(f"**Result:** {result_value}")
    
    # Gamut check if requested and converting from LAB/LCH
    if check_gamut and from_space in ("lab", "lch"):
        lab_check: tuple[float, float, float]
        if from_space == "lab":
            lab_check = (float(value[0]), float(value[1]), float(value[2]))
        else:
            lab_check = rgb_to_lab(rgb_int)
        
        in_gamut = is_in_srgb_gamut(lab_check)
        
        response.extend([
            f"",
            f"**Gamut Status:** {'✓ In sRGB gamut' if in_gamut else '⚠ Out of sRGB gamut'}",
        ])
        
        if not in_gamut:
            nearest_rgb_float = find_nearest_in_gamut(lab_check)
            nearest_rgb_int = (int(round(nearest_rgb_float[0])), int(round(nearest_rgb_float[1])), int(round(nearest_rgb_float[2])))
            nearest_hex = rgb_to_hex(nearest_rgb_int)
            response.extend([
                f"**Nearest in-gamut color:**",
                f"   - RGB: {nearest_rgb_int}",
                f"   - Hex: {nearest_hex}",
            ])
    
    return [TextContent(type="text", text="\n".join(response))]


async def run_server():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Entry point for the MCP server."""
    import asyncio
    asyncio.run(run_server())


if __name__ == "__main__":
    main()

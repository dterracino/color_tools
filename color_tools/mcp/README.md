# Color Tools MCP Server

The Color Tools MCP server gives MCP-compatible agents structured access to the library's
color science calculations, named palettes, and 3D printing filament database.

The server is named `color-tools`. The Python distribution remains `color-match-tools` because
the preferred PyPI name was unavailable.

## Installation

```bash
pip install "color-match-tools[mcp]"
```

Run the local stdio server with either entry point:

```bash
color-tools-mcp
python -m color_tools.mcp
```

MCP clients normally start the process automatically. Do not manually run a second instance for
the same client connection.

## Tools

| Tool | Purpose |
| --- | --- |
| `analyze_color` | Return all supported coordinates, a generated name, gamut status, named colors, and filament matches |
| `convert_color` | Convert among RGB, XYZ, LAB, LCH, HSL, CMY, and CMYK |
| `compare_colors` | Compare two colors with CIEDE2000, CIE94, CIE76, CMC 2:1, HyAB, and RGB Euclidean distance |
| `find_named_colors` | Search CSS colors or a bundled named palette |
| `find_filaments` | Match filament colors with maker, material, finish, owned, and hue filters |
| `get_filament_catalog` | Discover valid filament makers, materials, finishes, and record counts |
| `transform_color_vision` | Simulate or correct protanopia, deuteranopia, tritanopia, or the combined diagnostic |
| `map_to_srgb_gamut` | Check LAB gamut and reduce chroma while preserving lightness and hue |
| `validate_color_name` | Evaluate whether a supplied color name describes a hex color |

Every tool returns typed structured output. Agents should use CIEDE2000 for ordinary perceptual
matching unless the user requests a different metric.

## VS Code

This repository includes `.vscode/mcp.json`, which launches the server from the project virtual
environment. For another workspace, add an equivalent configuration:

```json
{
  "servers": {
    "color-tools": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "color_tools.mcp"]
    }
  }
}
```

The selected interpreter must have `color-match-tools[mcp]` installed.

## Data Interpretation

Color conversions and distance values come directly from Color Tools. Filament matches use the
bundled manufacturer reference colors. A printed result can differ because of material batch,
printer settings, layer thickness, background, lighting, and display calibration.

The first release is intentionally read-only and does not expose image file processing, exports,
or owned-filament mutations. Those operations require explicit file-access and write policies.

# MCP Server Quick Start (VS Code)

This guide shows how to use the color_tools MCP server with GitHub Copilot in VS Code.

## Important: How MCP Works in VS Code

**You do NOT need to manually start the server.** 

The MCP server is configured in `.vscode/settings.json` and will be **automatically launched by GitHub Copilot** when you use Copilot Chat. The server runs in the background and communicates with Copilot via JSON-RPC over stdin/stdout.

## What You Get

Four powerful tools for color analysis that Copilot can use automatically:

- **analyze_color** - Complete color analysis (all color spaces, nearest CSS/filament, gamut)
- **find_nearest_css_color** - Find matching CSS colors with customizable metrics
- **find_nearest_filament** - Match 3D printing filaments (with maker/type/finish filters)
- **convert_color_space** - Convert between RGB/LAB/LCH/HSL/Hex with gamut checking

## Quick Start

### 1. Configuration (Already Done)

The MCP server is configured in `.vscode/settings.json`:

```json
{
    "github.copilot.mcp.servers": {
        "color-tools": {
            "command": "C:/Scripts/color_tools/.venv/Scripts/python.exe",
            "args": ["-m", "color_tools.mcp"],
            "cwd": "C:/Scripts/color_tools"
        }
    }
}
```

GitHub Copilot will automatically launch this server when needed.

### 2. Use with GitHub Copilot

Open Copilot Chat and ask questions. Copilot will automatically invoke the MCP tools:

**Example questions:**
  - "What's the nearest CSS color to RGB(180, 100, 200)?"
  - "Find Bambu Lab PLA filaments matching RGB(255, 0, 0)"
  - "Analyze RGB(200, 100, 50) and show all color space conversions"
  - "Convert LAB(50, 100, 50) to RGB and check if it's in gamut"

Copilot will automatically call the appropriate MCP tool to answer.

## Troubleshooting

**Tools not appearing in Copilot:**

- Reload VS Code window (`Ctrl+Shift+P` → "Developer: Reload Window")
- Make sure you're using Copilot Chat (not just inline completions)
- Check that the venv Python path in `.vscode/settings.json` is correct
- Ensure MCP SDK is installed: `pip install color-match-tools[mcp]`

**Server errors:**

- The server runs automatically - **don't start it manually in a terminal**
- If you see JSON-RPC errors, close any terminals running the server
- Check VS Code's Output panel (View → Output → select "MCP" or "GitHub Copilot")

## Manual Tool Testing

You can test tools directly without Copilot:

```powershell
# Test analyze_color
& .venv/Scripts/python.exe -c "
import asyncio
from color_tools.mcp.server import analyze_color_tool

async def test():
    result = await analyze_color_tool({
        'rgb': [180, 100, 200],
        'show_nearest_css': True,
        'show_nearest_filament': True
    })
    print(result[0].text)

asyncio.run(test())
"
```

## Available Tools Reference

### analyze_color

```json
{
  "rgb": [255, 128, 64],
  "show_nearest_css": true,
  "show_nearest_filament": false
}
```

### find_nearest_css_color

```json
{
  "rgb": [180, 100, 200],
  "metric": "de2000",
  "max_results": 3
}
```

### find_nearest_filament

```json
{
  "rgb": [255, 0, 0],
  "maker": "Bambu",
  "type": "PLA",
  "metric": "de2000",
  "max_results": 5
}
```

### convert_color_space

```json
{
  "value": [200, 100, 50],
  "from_space": "rgb",
  "to_space": "lab",
  "check_gamut": false
}
```

## Next Steps

See `color_tools/mcp/README.md` for:

- Complete tool documentation
- Claude Desktop configuration
- Planned features (image optimization, CVD tools)
- Implementation details

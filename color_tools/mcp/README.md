# MCP Server Module

**Location:** `color_tools/mcp/`  
**Package Extra:** `pip install color-match-tools[mcp]`  
**Dependencies:** mcp >= 1.0.0

## Overview

This module provides a **Model Context Protocol (MCP) server** that exposes color_tools functionality to Large Language Models (LLMs) like Claude, GPT, and GitHub Copilot.

## Module Organization

```text
color_tools/mcp/
├── __init__.py       # Public API exports
├── __main__.py       # Entry point (python -m color_tools.mcp)
├── README.md         # This file
├── server.py         # MCP server implementation (planned)
└── tools.py          # Tool definitions (planned)
```

### Runnable Module

This IS a **runnable module** with `__main__.py`.

**Run with:**

```bash
python -m color_tools.mcp
```

**Not accessed via:**

- ❌ CLI subcommand
- ❌ Direct Python import (use color_tools functions directly instead)

## What is MCP?

**Model Context Protocol** is a standard for exposing tools and data to LLMs in a structured way.

**Key Concepts:**

- **Server:** Exposes tools (functions) that LLMs can call
- **Client:** LLM interface (Claude Desktop, VS Code, etc.)
- **Tools:** Functions with typed parameters and descriptions
- **Resources:** Data sources (files, databases, APIs)

**Benefits:**

- LLMs can directly analyze colors, images, palettes
- Multi-step workflows in natural language
- No copy-paste of RGB values or file paths
- Visual feedback (images, color swatches)

## Current Status

🚧 **NOT YET IMPLEMENTED** - This is a planning document.

## Planned Features

### Tools to Expose

#### 1. Color Analysis Tools

**`analyze_color`**

```python
{
  "rgb": [255, 128, 64],
  "show_conversions": true,
  "show_nearest_css": true,
  "show_nearest_filament": true
}
```

Returns:

- RGB, LAB, LCH, HSL, XYZ values
- Nearest CSS color + Delta E
- Nearest filament + Delta E
- Gamut status

**`find_color_palette`**

```python
{
  "base_color": [255, 0, 0],
  "palette_type": "triadic",
  "return_as": "css_names"  # or "rgb", "hex"
}
```

Returns:

- Generated palette colors
- Harmony type explanation
- Visual preview (if supported)

#### 2. Image Processing Tools

**`optimize_image_for_hueforge`**

```python
{
  "image_path": "sunset.jpg",
  "n_colors": 10,
  "quantize": 256,
  "denoise": true,
  "output_path": "optimized.jpg"
}
```

Returns:

- Extracted colors with layer assignments
- Delta E report
- Preview image (base64)
- Hueforge layer distribution chart

**`extract_image_palette`**

```python
{
  "image_path": "photo.jpg",
  "n_colors": 8,
  "focal_region": "auto"
}
```

Returns:

- Dominant colors (RGB + names)
- Pixel counts
- LAB values

#### 3. Color Vision Deficiency Tools

**`simulate_cvd`**

```python
{
  "color": [255, 0, 0],
  "cvd_type": "protanopia"
}
```

Returns:

- Simulated color
- Difference from original
- Accessibility notes

#### 4. Filament Search Tools

**`find_filament`**

```python
{
  "color": [180, 100, 200],
  "maker": "Bambu Lab",
  "type": "PLA",
  "max_results": 5
}
```

Returns:

- Matching filaments
- Delta E for each
- Availability info (if known)

### Resources to Expose

#### 1. Color Databases

- CSS colors (147 named colors)
- 3D printing filaments (searchable by maker, type, finish)
- Retro palettes (CGA, EGA, VGA, Web)

#### 2. Image Analysis Results

- Recently analyzed images (cache)
- Extracted palettes
- Hueforge optimizations

## Configuration

### For Claude Desktop

**Location:**

- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%/Claude/claude_desktop_config.json`

**Configuration:**

```json
{
  "mcpServers": {
    "color-tools": {
      "command": "python",
      "args": ["-m", "color_tools.mcp"],
      "cwd": "C:/Scripts/color_tools",
      "env": {
        "PYTHONPATH": "C:/Scripts/color_tools"
      }
    }
  }
}
```

### For VS Code Copilot

**Configuration** in `.vscode/settings.json`:

```json
{
  "github.copilot.mcp.servers": {
    "color-tools": {
      "command": "python",
      "args": ["-m", "color_tools.mcp"]
    }
  }
}
```

## Example Interactions

### Example 1: Color Analysis

```text
User: "What's the nearest CSS color to RGB(200, 100, 50)?"

LLM: [calls analyze_color tool]
     "The nearest CSS color is 'sienna' (RGB 160, 82, 45) with a 
      Delta E of 12.4. Here's the full analysis:
      
      Input: RGB(200, 100, 50)
      LAB: (50.2, 34.1, 45.3)
      Nearest: sienna - ΔE = 12.4
      In sRGB gamut: Yes"
```

### Example 2: Image Optimization

```text
User: "Optimize sunset.jpg for Hueforge with 12 colors"

LLM: [calls optimize_image_for_hueforge tool]
     "I've optimized sunset.jpg for Hueforge. Extracted 12 colors 
      distributed across layers 1-27:
      
      - Layer 2: Deep purple #1a0a3c (sky)
      - Layer 8: Orange #ff7f2a (sun)
      - Layer 15: Pink #ff9ec4 (clouds)
      ...
      
      Average Delta E: 6.8 (minimal perceptual change)
      Saved to: hueforge_sunset.jpg"
```

### Example 3: Multi-Step Workflow

```text
User: "Find me 5 Bambu Lab PLA filaments that match the dominant 
       colors in nature.jpg"

LLM: [calls extract_image_palette]
     "Extracted 5 dominant colors from nature.jpg"
     
     [calls find_filament for each color]
     "Here are matching Bambu Lab PLA filaments:
     
     1. Sky blue → Bambu PLA Blue (ΔE = 3.2)
     2. Grass green → Bambu PLA Mint (ΔE = 5.1)
     3. Earth brown → Bambu PLA Coffee (ΔE = 4.8)
     ..."
```

## Implementation Plan

### Phase 1: Basic Server Setup ✅ (Planned)

- [ ] Create MCP server boilerplate
- [ ] Implement basic color analysis tools
- [ ] Test with Claude Desktop
- [ ] Add error handling and validation

### Phase 2: Image Processing Tools (Planned)

- [ ] Add image optimization tools
- [ ] Support image upload/base64
- [ ] Return visual previews
- [ ] Add caching for performance

### Phase 3: Advanced Features (Future)

- [ ] Batch operations
- [ ] Streaming results for long operations
- [ ] State management (remember recent operations)
- [ ] Image comparison tools

### Phase 4: Resources & Context (Future)

- [ ] Expose color databases as resources
- [ ] Recent analysis cache
- [ ] Project-level color schemes

## Technical Details

### Server Implementation

**Using MCP Python SDK:**

```python
# mcp/server.py
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent
from ..conversions import rgb_to_lab
from ..palette import Palette

server = Server("color-tools")

@server.tool()
async def analyze_color(rgb: list[int]) -> dict:
    """Analyze a color and find nearest matches."""
    # Implementation here
    pass

if __name__ == "__main__":
    server.run()
```

### Tool Definitions

**Each tool needs:**

- Name (identifier)
- Description (for LLM to understand purpose)
- Input schema (typed parameters)
- Output schema (structured response)

**Example:**

```python
Tool(
    name="analyze_color",
    description="Analyze RGB color and find nearest CSS/filament matches",
    input_schema={
        "type": "object",
        "properties": {
            "rgb": {
                "type": "array",
                "items": {"type": "integer", "minimum": 0, "maximum": 255},
                "minItems": 3,
                "maxItems": 3
            }
        },
        "required": ["rgb"]
    }
)
```

### Response Format

**Text responses:**

```python
return TextContent(
    type="text",
    text="Nearest color: coral (ΔE = 5.2)"
)
```

**Image responses:**

```python
return ImageContent(
    type="image",
    data=base64_encoded_image,
    mimeType="image/png"
)
```

## Dependencies

### Required (when using `[mcp]` extra)

- **mcp >= 1.0.0** - MCP Python SDK

### Optional

- **Pillow >= 10.0.0** - For image tools (requires `[image]` extra as well)

### Internal Dependencies

- All `color_tools` modules (conversions, distance, palette, etc.)

## Testing

Tests should be added to `tests/test_mcp_server.py` (not yet created).

**Test Coverage Needed:**

- Server startup/shutdown
- Tool registration
- Input validation
- Output formatting
- Error handling
- Image handling (if Pillow available)

## Error Handling

**Graceful degradation:**

- If Pillow not available → image tools return error with installation instructions
- If invalid input → return clear error message
- If file not found → return helpful error with path info

## Security Considerations

**File Access:**

- Validate file paths (no directory traversal)
- Limit to specific directories if needed
- Check file sizes before processing

**Resource Limits:**

- Set max image dimensions
- Timeout long operations
- Limit concurrent requests

## Hosting Options

### Local (Development/Personal Use)

- Run on your machine
- Configured in Claude Desktop/VS Code
- No network access needed

### Remote (Team/Production)

- Deploy to Railway, Render, Fly.io
- Accessible via HTTP/WebSocket
- Requires authentication

### Docker Container

```dockerfile
FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install color-match-tools[mcp,image]
CMD ["python", "-m", "color_tools.mcp"]
```

## Related Documentation

- **Main README:** `../../README.md` - Overall project documentation
- **Image Module:** `../image/README.md` - Image processing features
- **MCP Specification:** <https://modelcontextprotocol.io/>
- **Claude Desktop:** <https://claude.ai/desktop>

## Future Enhancements

- **Interactive color picker:** Visual interface for color selection
- **Real-time preview:** See color changes as you adjust values
- **Palette generation from descriptions:** "ocean sunset colors"
- **Color trend analysis:** Analyze multiple images for common palettes
- **Integration with design tools:** Export to Figma, Adobe, etc.

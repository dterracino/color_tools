"""
MCP (Model Context Protocol) server for color_tools.

This module provides an MCP server that exposes color_tools functionality
to Large Language Models (LLMs) like Claude, GPT, and GitHub Copilot.

Requires MCP SDK: pip install color-match-tools[mcp]

🚧 NOT YET IMPLEMENTED - See README.md for planned features.

Usage:
------
    # Run the MCP server
    python -m color_tools.mcp
    
    # Or from Python
    from color_tools.mcp import run_server
    run_server()

Configuration:
--------------
See mcp/README.md for configuration instructions for:
- Claude Desktop
- VS Code Copilot
- Other MCP-compatible clients
"""

from __future__ import annotations

# Check if MCP SDK is available
try:
    import mcp  # type: ignore
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def run_server():
    """
    Run the MCP server.
    
    Raises:
        ImportError: If MCP SDK is not installed
        NotImplementedError: Server not yet implemented
    """
    if not MCP_AVAILABLE:
        raise ImportError(
            "MCP server requires the MCP SDK. "
            "Install with: pip install color-match-tools[mcp]"
        )
    
    raise NotImplementedError(
        "MCP server is not yet implemented. "
        "See color_tools/mcp/README.md for planned features."
    )


__all__ = [
    'MCP_AVAILABLE',
    'run_server',
]

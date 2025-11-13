"""
Entry point for running the MCP server.

Usage:
    python -m color_tools.mcp
"""

from __future__ import annotations
import sys

from . import run_server, MCP_AVAILABLE


def main():
    """Main entry point for MCP server."""
    if not MCP_AVAILABLE:
        print("Error: MCP server requires the MCP SDK", file=sys.stderr)
        print("Install with: pip install color-match-tools[mcp]", file=sys.stderr)
        sys.exit(1)
    
    try:
        print("Starting color_tools MCP server...", file=sys.stderr)
        run_server()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Test script to demonstrate MCP server tools working.

This directly tests the tool implementations without running the MCP server.
"""
import asyncio


async def test_analyze_color():
    """Test the analyze_color tool."""
    # Import here to avoid triggering server startup
    from color_tools.mcp.server import analyze_color_tool
    
    print("=" * 60)
    print("TEST 1: Analyze Color - RGB(255, 128, 64)")
    print("=" * 60)
    
    args = {
        "rgb": [255, 128, 64],
        "show_nearest_css": True,
        "show_nearest_filament": True
    }
    
    result = await analyze_color_tool(args)
    print(result[0].text)
    print()


async def test_find_css_color():
    """Test the find_nearest_css_color tool."""
    from color_tools.mcp.server import find_nearest_css_color_tool
    
    print("=" * 60)
    print("TEST 2: Find Nearest CSS Colors - RGB(180, 100, 200)")
    print("=" * 60)
    
    args = {
        "rgb": [180, 100, 200],
        "metric": "de2000",
        "max_results": 3
    }
    
    result = await find_nearest_css_color_tool(args)
    print(result[0].text)
    print()


async def test_find_filament():
    """Test the find_nearest_filament tool."""
    from color_tools.mcp.server import find_nearest_filament_tool
    
    print("=" * 60)
    print("TEST 3: Find Nearest Filaments - RGB(255, 0, 0), PLA only")
    print("=" * 60)
    
    args = {
        "rgb": [255, 0, 0],
        "type": "PLA",
        "metric": "de2000",
        "max_results": 5
    }
    
    result = await find_nearest_filament_tool(args)
    print(result[0].text)
    print()


async def test_convert_color():
    """Test the convert_color_space tool."""
    from color_tools.mcp.server import convert_color_space_tool
    
    print("=" * 60)
    print("TEST 4: Convert RGB(200, 100, 50) to LAB")
    print("=" * 60)
    
    args = {
        "value": [200, 100, 50],
        "from_space": "rgb",
        "to_space": "lab",
        "check_gamut": False
    }
    
    result = await convert_color_space_tool(args)
    print(result[0].text)
    print()


async def test_gamut_check():
    """Test gamut checking."""
    from color_tools.mcp.server import convert_color_space_tool
    
    print("=" * 60)
    print("TEST 5: Convert LAB(50, 100, 50) to RGB with gamut check")
    print("=" * 60)
    
    args = {
        "value": [50, 100, 50],
        "from_space": "lab",
        "to_space": "rgb",
        "check_gamut": True
    }
    
    result = await convert_color_space_tool(args)
    print(result[0].text)
    print()


async def main():
    """Run all tests."""
    print("\n🎨 COLOR TOOLS MCP SERVER - TOOL DEMONSTRATIONS\n")
    
    await test_analyze_color()
    await test_find_css_color()
    await test_find_filament()
    await test_convert_color()
    await test_gamut_check()
    
    print("=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

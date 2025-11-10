#!/usr/bin/env python3
"""Manual test/demo for color validation functionality."""

import sys
from pathlib import Path

# Add parent directory to path so we can import the package
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from color_tools.validation import validate_color

def run_tests():
    """Runs a series of tests for the color validation function."""
    print("Running Color Validation Tests...\n")

    test_cases = [
        # --- Good Matches ---
        ("red", "#FF0000", "Exact match for red"),
        ("dark red", "#8B0000", "Exact match for darkred"),
        ("light blue", "#ADD8E6", "Exact match for lightblue"),
        ("fuzzy green", "#008000", "Fuzzy name, exact hex for green"),
        ("very light sky blue", "#87CEFA", "Fuzzy name for lightskyblue"),

        # --- Close, but maybe not a match (depends on threshold) ---
        ("pink", "#FFC0CB", "Exact pink"),
        ("hot pink", "#FF69B4", "A different shade of pink"),
        ("red", "#A52A2A", "This is brown, not red"),

        # --- Bad Matches ---
        ("blue", "#FF0000", "Completely wrong color (red hex for blue)"),
        ("yellow", "#0000FF", "Completely wrong color (blue hex for yellow)"),

        # --- Invalid Input ---
        ("green", "not a hex", "Invalid hex code"),
        ("purple", "#123", "Invalid hex code length"),
    ]

    for name, hex_code, description in test_cases:
        print(f"--- Testing: '{name}' ({hex_code}) - {description} ---")
        result = validate_color(name, hex_code)
        print(f"  Match Found?    : {result.is_match}")
        print(f"  Input Name      : '{name}'")
        print(f"  Matched Name    : '{result.name_match}' (Confidence: {result.name_confidence:.2f})")
        print(f"  Input Hex       : {result.hex_value}")
        print(f"  Suggested Hex   : {result.suggested_hex}")
        print(f"  Color Distance (Delta E): {result.delta_e:.2f}")
        print(f"  Message         : {result.message}\n")

if __name__ == "__main__":
    run_tests()

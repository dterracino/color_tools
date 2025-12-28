"""Validate command handler - Verify color name/hex pairings."""

import json
import sys
from argparse import Namespace

from ...validation import validate_color


def handle_validate_command(args: Namespace) -> None:
    """
    Handle the 'validate' command - verify color name matches hex code.
    
    Args:
        args: Parsed command-line arguments
        
    Exits:
        0: Color is a match
        1: Color is not a match
    """
    # Validate the color name/hex pairing
    result = validate_color(args.name, args.hex, de_threshold=args.threshold)
    
    if args.json_output:
        # JSON output
        output = {
            "is_match": result.is_match,
            "name_match": result.name_match,
            "name_confidence": result.name_confidence,
            "hex_value": result.hex_value,
            "suggested_hex": result.suggested_hex,
            "delta_e": result.delta_e,
            "message": result.message
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        if result.is_match:
            print(f"✓ MATCH")
            print(f"Name:       '{args.name}' → matched to '{result.name_match}'")
            print(f"Hex:        {result.hex_value}")
            print(f"Confidence: {result.name_confidence:.0%}")
            print(f"Delta E:    {result.delta_e:.2f} (threshold: {args.threshold})")
            if result.suggested_hex and result.suggested_hex != result.hex_value:
                print(f"Note:       Exact match for '{result.name_match}' would be {result.suggested_hex}")
        else:
            print(f"✗ NO MATCH")
            print(f"Name:       '{args.name}' → matched to '{result.name_match}'")
            print(f"Hex:        {result.hex_value}")
            print(f"Suggested:  {result.suggested_hex}")
            print(f"Confidence: {result.name_confidence:.0%}")
            print(f"Delta E:    {result.delta_e:.2f} (threshold: {args.threshold})")
            print(f"Reason:     {result.message}")
    
    # Exit with code 0 for match, 1 for no match
    sys.exit(0 if result.is_match else 1)

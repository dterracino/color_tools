#!/usr/bin/env python3
"""
Import new Bambu Lab filament data from .source_data folder.

This script parses the four new Bambu Lab filament files and generates
JSON entries ready to merge into filaments.json.
"""

import re
import json
from pathlib import Path


def parse_bambu_file(filepath: Path, maker: str, filament_type: str, finish: str | None) -> list[dict]:
    """
    Parse a Bambu Lab filament data file.
    
    Handles two formats:
    1. "Color Name\tHex:#XXXXXX\t" (tab-separated with "Hex:" prefix)
    2. "Color Name\nHex:#XXXXXX" (newline-separated with "Hex:" prefix)
    
    Args:
        filepath: Path to the source data file
        maker: Manufacturer name (e.g., "Bambu Lab")
        filament_type: Type of filament (e.g., "PETG", "PLA", "PETG-CF")
        finish: Finish type or None (e.g., "HF", "Translucent", None)
    
    Returns:
        List of filament dictionaries ready for JSON
    """
    content = filepath.read_text(encoding='utf-8')
    lines = content.strip().split('\n')
    
    # Skip the header line (first line is the title)
    lines = [line.strip() for line in lines[1:] if line.strip()]
    
    filaments = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this line contains both color and hex (tab-separated format)
        if '\t' in line:
            parts = [p.strip() for p in line.split('\t') if p.strip()]
            if len(parts) >= 2:
                color_name = parts[0]
                hex_code = parts[1].replace('Hex:', '').strip()
                
                # Clean up hex code
                if not hex_code.startswith('#'):
                    hex_code = '#' + hex_code
                
                filaments.append({
                    "maker": maker,
                    "type": filament_type,
                    "finish": finish,
                    "color": color_name,
                    "hex": hex_code.upper(),
                    "td_value": None
                })
                i += 1
                continue
        
        # Check if this is a color name line (no Hex: prefix)
        if not line.startswith('Hex:'):
            color_name = line
            # Next line should be the hex code
            if i + 1 < len(lines):
                hex_line = lines[i + 1]
                if hex_line.startswith('Hex:'):
                    hex_code = hex_line.replace('Hex:', '').strip()
                    
                    # Clean up hex code
                    if not hex_code.startswith('#'):
                        hex_code = '#' + hex_code
                    
                    filaments.append({
                        "maker": maker,
                        "type": filament_type,
                        "finish": finish,
                        "color": color_name,
                        "hex": hex_code.upper(),
                        "td_value": None
                    })
                    i += 2  # Skip both lines
                    continue
        
        # If we get here, skip this line
        i += 1
    
    return filaments


def main():
    """Parse all four new Bambu Lab filament files and output JSON."""
    
    source_dir = Path(__file__).parent.parent / '.source_data'
    
    # Define the files to parse
    files_to_parse = [
        ("Bambu Lab PETG HF.txt", "Bambu Lab", "PETG", "HF"),
        ("Bambu Lab PETG-CF.txt", "Bambu Lab", "PETG-CF", None),
        ("Bambu Lab PLA Translucent.txt", "Bambu Lab", "PLA", "Translucent"),
        ("Bambu Lab PETG Translucent.txt", "Bambu Lab", "PETG", "Translucent"),
    ]
    
    all_filaments = []
    
    for filename, maker, filament_type, finish in files_to_parse:
        filepath = source_dir / filename
        
        if not filepath.exists():
            print(f"❌ File not found: {filepath}")
            continue
        
        print(f"📄 Parsing: {filename}")
        filaments = parse_bambu_file(filepath, maker, filament_type, finish)
        print(f"   Found {len(filaments)} colors")
        
        all_filaments.extend(filaments)
    
    # Output results
    print(f"\n✅ Total filaments parsed: {len(all_filaments)}")
    print(f"\nBreakdown:")
    print(f"  - PETG HF: {sum(1 for f in all_filaments if f['type'] == 'PETG' and f['finish'] == 'HF')}")
    print(f"  - PETG-CF: {sum(1 for f in all_filaments if f['type'] == 'PETG-CF')}")
    print(f"  - PLA Translucent: {sum(1 for f in all_filaments if f['type'] == 'PLA' and f['finish'] == 'Translucent')}")
    print(f"  - PETG Translucent: {sum(1 for f in all_filaments if f['type'] == 'PETG' and f['finish'] == 'Translucent')}")
    
    # Write to temporary output file for review
    output_file = Path(__file__).parent / 'bambu_new_filaments.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_filaments, f, indent=2, ensure_ascii=False)
    
    print(f"\n📝 Output written to: {output_file}")
    print(f"\nPlease review the output before merging into filaments.json!")
    
    # Show a sample
    print(f"\nSample entries:")
    for i, filament in enumerate(all_filaments[:3]):
        print(f"\n{i+1}. {filament['color']} ({filament['type']} {filament['finish'] or ''})")
        print(f"   Hex: {filament['hex']}")


if __name__ == '__main__':
    main()

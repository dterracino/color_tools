#!/usr/bin/env python3
"""
Export Bambu Lab filaments (Basic and Matte finishes) to CSV format.

Outputs to: tooling/filaments_export.csv
Format: Brand, Name, TD, Color
"""

import csv
import json
from pathlib import Path
from color_tools.filament_palette import FilamentRecord


def export_bambu_filaments() -> None:
    """Export Bambu Lab Basic and Matte filaments to CSV."""
    
    # Load filaments database
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    filaments_path = project_root / "color_tools" / "data" / "filaments.json"
    output_path = script_dir / "filaments_export.csv"
    
    print(f"Loading filaments from: {filaments_path}")
    with filaments_path.open(encoding="utf-8") as stream:
        filaments = json.load(stream)
    
    # Filter for Bambu Lab with Basic or Matte finish
    bambu_filaments = [
        f for f in filaments
        if f.get('maker') == 'Bambu Lab' and f.get('finish') in ['Basic', 'Matte']
    ]
    
    print(f"Found {len(bambu_filaments)} Bambu Lab Basic/Matte filaments")
    
    # Sort by type, finish, color for better organization
    bambu_filaments.sort(key=lambda x: (x.get('type', ''), x.get('finish', ''), x.get('color', '')))
    
    # Write to CSV
    print(f"Writing to: {output_path}")
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['Brand', 'Name', 'TD', 'Color'])
        
        # Write data rows
        for filament in bambu_filaments:
            type_name = filament.get('type', '')
            finish = filament.get('finish', '')
            brand = f"Bambu Lab {type_name} {finish}".strip()
            name = filament.get('color', '')
            td = filament.get('td_value', '')
            # Convert None to empty string, keep 0 as 0
            if td is None:
                td = ''
            record = FilamentRecord(
                id=filament.get("id", ""),
                maker=filament["maker"],
                type=type_name,
                finish=finish,
                color=name,
                hex=filament["hex"],
                source=filaments_path.name,
            )
            color = record.effective_hex
            
            writer.writerow([brand, name, td, color])
    
    print(f"✓ Exported {len(bambu_filaments)} filaments to {output_path}")
    
    # Show first few rows as preview
    print("\nPreview (first 10 rows):")
    print("=" * 80)
    with open(output_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i < 10:
                print(line.rstrip())
            else:
                break
    print("=" * 80)


if __name__ == '__main__':
    export_bambu_filaments()

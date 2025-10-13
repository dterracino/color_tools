# Prusament Filaments Data

This file contains the extracted filament data from Prusa Research's HueForge filament transparency values and HexCodes documentation.

## Data Source

- **Source Document**: `Prusa Filaments.pdf`
- **Extraction Date**: 2025-10-13
- **Total Records**: 79

## Data Format

Each record contains:
- `maker`: Always "Prusament"
- `type`: Filament type (PLA, PETG, ASA, PC, etc.)
- `finish`: Surface finish (Blend, Galaxy, Matte, Transparent, etc.) or `null`
- `color`: Color name
- `hex`: Hex color code (format: #RRGGBB)
- `td_value`: HueForge Transmission Distance value (0.1-100.0)
- `product`: Full product name including weight

## Type Distribution

- PLA: 28 records
- PETG: 21 records (including PETG Special)
- ASA: 7 records
- PVB: 6 records
- PC: 5 records (including PC CF)
- rPLA: 4 records
- Other: 8 records (PA11 CF, PEI 1010, Woodfill)

## Finish Distribution

- None (plain): 54 records
- Blend: 12 records
- Galaxy: 6 records
- Carbon Fiber: 3 records
- Premium: 2 records
- Matte: 1 record
- Marble: 1 record

## Notes

- The `product` field preserves the full product name from the source document, allowing for reprocessing if needed
- Some finish extractions may need manual review (e.g., "Jet" in "Jet Black" is kept as part of the color name, not as a finish)
- Hex codes and TD values are directly from the HueForge measurements by Prusa Research
- All TD values are in the valid range of 0.1 to 100.0, where:
  - 0.1 = least transparent (opaque)
  - 100.0 = fully transparent/clear

## Example Records

```json
{
  "maker": "Prusament",
  "type": "PLA",
  "finish": "Blend",
  "color": "Lime Green",
  "hex": "#FFFFBC",
  "td_value": 3.5,
  "product": "Blend Lime Green"
}
```

```json
{
  "maker": "Prusament",
  "type": "PETG",
  "finish": null,
  "color": "Jet Black",
  "hex": "#0A1E0B",
  "td_value": 0.3,
  "product": "Jet Black 1Kg"
}
```

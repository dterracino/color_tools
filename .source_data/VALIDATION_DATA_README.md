r# Prusament Validation Data Extraction

This directory contains extracted Prusament filament data from the validation JSON files.

## Source Files

- `prusament_vallidation_data_page1.json` - API data from filamentcolors.xyz (page 1, 50 records)
- `prusament_vallidation_data_page2.json` - API data from filamentcolors.xyz (page 2, 18 records)

Total: 68 records from filamentcolors.xyz API

## Extraction Process

The `extract_validation_data.py` script processes the validation JSON files and extracts:

1. **Manufacturer**: Always "Prusament"
2. **Type**: Base filament type (PLA, PETG, ASA, PC, rPLA)
3. **Finish**: Surface finish extracted from filament_type.name or color_name (Blend, Galaxy, Pearl, Marble, Carbon Fiber, etc.)
4. **Color**: Color name from color_name field
5. **Hex**: Hex color code (normalized with # prefix)
6. **TD Value**: Set to null (not available in validation source data)
7. **Product**: Full product name extracted from purchase link

## Output File

`prusament_validation_extracted.json` - 68 records in the format:

```json
{
  "maker": "Prusament",
  "type": "PC",
  "finish": "Blend",
  "color": "Jet Black",
  "hex": "#24292A",
  "td_value": null,
  "product": "Pc Blend Jet Black 970g"
}
```

## Type Distribution

- PLA: 28 records
- PETG: 24 records
- ASA: 7 records
- PC: 5 records
- rPLA: 4 records

## Finish Distribution

- None (plain): 49 records
- Blend: 7 records
- Galaxy: 4 records
- Pearl: 2 records
- V0: 2 records
- Carbon Fiber: 2 records
- Marble: 1 record
- Tungsten: 1 record

## Notes

### TD Values

The validation source data does not include HueForge Transmission Distance (td_value) measurements. All td_value fields are set to `null` in the output. If td_value data is needed, it must be obtained from other sources (e.g., Prusa's HueForge documentation).

### Hex Colors

The hex colors in this validation data come from filamentcolors.xyz's photographed samples and may differ from Prusa's official color specifications. These are community-measured colors under specific lighting conditions.

### Comparison with Official Data

The existing `prusament_filaments.json` file (79 records) contains data from Prusa's official HueForge document with:
- Official hex color codes
- Measured TD values (0.1-100.0 range)

The validation data provides:
- Community-measured colors from actual prints
- Different color measurement methodology
- 23 unique products not in the official data

## Usage

To regenerate the output file:

```bash
cd .source_data
python3 extract_validation_data.py
```

This will create/overwrite `prusament_validation_extracted.json`.

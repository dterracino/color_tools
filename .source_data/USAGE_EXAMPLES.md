# Usage Examples for Prusament Validation Data

## Quick Start

### View All Data Statistics

```bash
python3 view_validation_data.py --stats
```

Output:
```
Total records: 68

Types:
  ASA: 7
  PC: 5
  PETG: 24
  PLA: 28
  rPLA: 4

Finishes:
  None: 49
  Blend: 7
  Carbon Fiber: 2
  Galaxy: 4
  Marble: 1
  Pearl: 2
  Tungsten: 1
  V0: 2
```

### Filter by Type

```bash
python3 view_validation_data.py --type PLA
```

### Filter by Finish

```bash
python3 view_validation_data.py --finish Galaxy
```

### Combine Filters

```bash
python3 view_validation_data.py --type PLA --finish Galaxy
```

Output:
```
Found 4 record(s):

1. Purple
   Type: PLA | Finish: Galaxy
   Hex: #453A72 | TD: N/A
   Product: Pla Galaxy Purple 1kg

2. Silver
   Type: PLA | Finish: Galaxy
   Hex: #999AA0 | TD: N/A
   Product: Pla Galaxy Silver 1kg
...
```

### Search by Color Name

```bash
python3 view_validation_data.py --color Black
```

## Regenerating the Data

If the source validation files are updated:

```bash
python3 extract_validation_data.py
```

This will regenerate `prusament_validation_extracted.json`.

## Data Format

Each record in `prusament_validation_extracted.json` follows this structure:

```json
{
  "maker": "Prusament",
  "type": "PLA",
  "finish": "Galaxy",
  "color": "Purple",
  "hex": "#453A72",
  "td_value": null,
  "product": "Pla Galaxy Purple 1kg"
}
```

## Integration with color_tools

The extracted data can be used with the color_tools library by:

1. Loading the JSON file manually:
```python
import json
with open('.source_data/prusament_validation_extracted.json', 'r') as f:
    prusament_data = json.load(f)
```

2. Note: The main `color_tools.json` uses a simpler format without `td_value` and `product` fields. These additional fields are specific to Prusament data tracking.

## Fields Explained

- **maker**: Always "Prusament" for this dataset
- **type**: Base filament material (PLA, PETG, ASA, PC, rPLA)
- **finish**: Surface finish or special variant (Blend, Galaxy, Pearl, etc.) or `null`
- **color**: Color name
- **hex**: Hex color code in #RRGGBB format (uppercase)
- **td_value**: HueForge Transmission Distance (null in validation data - not measured)
- **product**: Complete product name with weight

## Notes

- The hex colors are from filamentcolors.xyz community measurements
- They may differ from Prusa's official specifications
- td_value is null because validation data doesn't include transparency measurements
- For official td_value data, see `prusament_filaments.json` (from Prusa's HueForge document)

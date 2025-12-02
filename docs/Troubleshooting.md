# Troubleshooting

[← Back to README](https://github.com/dterracino/color_tools/blob/main/README.md) | [Customization](https://github.com/dterracino/color_tools/blob/main/docs/Customization.md) | [FAQ →](https://github.com/dterracino/color_tools/blob/main/docs/FAQ.md)

---

This document covers common errors, data integrity verification, performance optimization, and technical notes about Color Tools.

## Table of Contents

- [Error Handling](#error-handling)
- [Data Integrity Verification](#data-integrity-verification)
- [Performance Notes](#performance-notes)
- [Technical Notes](#technical-notes)
  - [Color Science Constants](#color-science-constants)
  - [Thread Safety](#thread-safety)
  - [Gamut Handling](#gamut-handling)

---

## Error Handling

Common errors and solutions:

### "Color not found"

**Cause:** The color name doesn't exist in the database.

**Solutions:**

- Check spelling and case of color names (searches are case-insensitive)
- Use `--nearest` to find the closest match instead of exact match
- Verify the color exists in CSS color names or your custom palette

### "No filaments match criteria"

**Cause:** Your filter combination doesn't match any entries in the database.

**Solutions:**

- Verify manufacturer names with `python -m color_tools filament --list-makers`
- Verify filament types with `python -m color_tools filament --list-types`
- Check finishes with `python -m color_tools filament --list-finishes`
- Use wildcards (`"*"`) to broaden your search
- Try using maker synonyms (e.g., "Bambu" for "Bambu Lab")

### "Unknown metric"

**Cause:** Invalid distance metric specified.

**Solutions:**

Use one of the supported metrics:

- `euclidean` - Simple RGB Euclidean distance
- `de76` - CIE76 Delta E
- `de94` - CIE94 Delta E
- `de2000` - CIEDE2000 Delta E (recommended)
- `cmc` - CMC color difference

### Out of Gamut Warnings

**Cause:** The LAB/LCH color cannot be accurately displayed in sRGB.

**Solutions:**

- Use `--check-gamut` to verify color representability before conversion
- The tool will automatically find the nearest in-gamut color
- Consider using `clamp_to_gamut()` in Python API for automatic correction

### Import Errors (Image Module)

**Cause:** Pillow is not installed.

**Solution:**

```bash
pip install color-match-tools[image]
# OR
pip install Pillow
```

### Fuzzy Matching Not Working Optimally

**Cause:** fuzzywuzzy is not installed.

**Solution:**

```bash
pip install color-match-tools[fuzzy]
# OR
pip install fuzzywuzzy
```

Note: The validation module will fall back to built-in Levenshtein matching if fuzzywuzzy is not available.

---

## Data Integrity Verification

Core data files are protected with SHA-256 hashes to ensure integrity.

### Verification Commands

```bash
# Verify data files only
python -m color_tools --verify-data

# Verify color science constants only
python -m color_tools --verify-constants

# Verify transformation matrices only
python -m color_tools --verify-matrices

# Verify everything (constants, data files, and matrices)
python -m color_tools --verify-all
```

### If Verification Fails

**For Data Files:**

1. **Accidental modification** - Restore from git: `git checkout color_tools/data/`
2. **Intentional update** - Regenerate hashes using tooling (see [Hash_Update_Guide.md](https://github.com/dterracino/color_tools/blob/main/docs/Hash_Update_Guide.md))

**For Constants:**

1. **Accidental modification** - Restore from git: `git checkout color_tools/constants.py`
2. **Malicious tampering** - Investigate and restore from a known good backup
3. **Development changes** - If you're a maintainer, use: `python tooling/update_hashes.py --autoupdate`

**For Matrices:**

1. **Accidental modification** - Restore from git: `git checkout color_tools/matrices.py`
2. **Intentional update** - Regenerate hash: `python tooling/update_hashes.py --autoupdate`

### User Data Files

User data files (`user-colors.json`, `user-filaments.json`, `user-synonyms.json`) are **not** verified - you have full control over their contents.

---

## Performance Notes

The tool uses indexed lookups for fast color matching:

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Color name lookup | O(1) | Hash-based index |
| RGB exact match | O(1) | Hash-based index |
| LAB/LCH lookup | O(1) | Hash-based with rounding |
| Nearest neighbor | O(n) | Optimized distance calculations |

### Optimization Tips

**For large datasets:**

- Filter by manufacturer or type before performing nearest neighbor searches
- Use `--count` to limit results when you only need top matches
- Consider pre-filtering with `filament_palette.filter()` in Python API

**For batch operations:**

```python
# Efficient: Pre-filter, then search
palette = FilamentPalette.load_default()
pla_filaments = palette.filter(type_name="PLA")  # Filter once
for color in colors_to_match:
    nearest, dist = pla_filaments.nearest_filament(color)  # Search smaller set
```

**For repeated searches:**

```python
# Load palettes once, reuse for multiple operations
palette = Palette.load_default()
filament_palette = FilamentPalette.load_default()

# Multiple searches with pre-loaded data
for rgb in colors:
    css_match, _ = palette.nearest_color(rgb, space='rgb')
    filament_match, _ = filament_palette.nearest_filament(rgb)
```

---

## Technical Notes

### Color Science Constants

The tool includes comprehensive color science constants from international standards:

- **CIE illuminants and observers** (D65 white point, 2° standard observer)
- **sRGB transformation matrices** (RGB ↔ XYZ)
- **Gamma correction parameters** (sRGB companding)
- **Delta E formula coefficients** (CIEDE2000, CIE94, CMC)

All constants include integrity verification via SHA-256 hashing.

**CRITICAL**: The color science constants in `constants.py` should **NEVER** be modified. They represent fundamental values from international standards (CIE, sRGB specification) and changing them would break color accuracy.

### Thread Safety

Runtime configuration (like dual-color mode) uses `threading.local()` for thread-safe operation in multi-threaded applications.

```python
import threading
from color_tools import set_dual_color_mode, get_dual_color_mode, FilamentPalette

def worker_thread(mode):
    set_dual_color_mode(mode)  # Thread-local setting
    palette = FilamentPalette.load_default()
    # Each thread can have its own configuration
    filament, _ = palette.nearest_filament((255, 100, 100))
    print(f"Thread ({mode}): {filament.color}")

# Different threads can use different configurations
t1 = threading.Thread(target=worker_thread, args=('first',))
t2 = threading.Thread(target=worker_thread, args=('mix',))
t1.start()
t2.start()
```

### Gamut Handling

The tool can detect when LAB colors fall outside the sRGB gamut and automatically find the nearest representable color.

**How it works:**

1. LAB colors are converted to RGB
2. If any RGB component is outside 0-255 range, the color is out of gamut
3. The tool finds the nearest in-gamut color by reducing chroma while preserving hue and lightness

**Python API:**

```python
from color_tools import is_in_srgb_gamut, find_nearest_in_gamut, clamp_to_gamut

# Check if a color is displayable
lab_color = (90, 50, 100)  # Very saturated yellow-ish
if not is_in_srgb_gamut(lab_color):
    print("Color is out of gamut!")
    
    # Find nearest displayable color
    nearest = find_nearest_in_gamut(lab_color)
    print(f"Nearest in-gamut: {nearest}")
    
    # Or simply clamp to gamut
    clamped = clamp_to_gamut(lab_color)
    print(f"Clamped: {clamped}")
```

**CLI:**

```bash
# Check gamut status
python -m color_tools convert --check-gamut --value 90 50 100

# Check LCH color gamut
python -m color_tools convert --check-gamut --from lch --value 70 80 120
```

---

[← Back to README](https://github.com/dterracino/color_tools/blob/main/README.md) | [Customization](https://github.com/dterracino/color_tools/blob/main/docs/Customization.md) | [FAQ →](https://github.com/dterracino/color_tools/blob/main/docs/FAQ.md)

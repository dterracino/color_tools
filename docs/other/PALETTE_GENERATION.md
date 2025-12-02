# Palette Generation Implementation Plan

## Overview

Add color harmony/palette generation functionality to allow users to generate complementary, triadic, tetradic, and other color schemes from a base color. This applies to both CSS colors and 3D printing filaments.

## Design Decision: `--palette` Flag in Existing Commands

After discussion, we decided to add `--palette` as a flag to existing `color` and `filament` commands rather than creating a new top-level command.

### Rationale

The existing CLI structure uses:

- **Top-level command** = "what domain am I working in?" (colors vs filaments)
- **Flags** = "what operation am I doing?" (lookup, search, generate, list)

Examples of current pattern:

```bash
# color command - not inherently about searching
python -m color_tools color --name "coral"           # lookup by name
python -m color_tools color --nearest --value ...    # find nearest

# filament command - not inherently about searching  
python -m color_tools filament --nearest --value ... # find nearest
python -m color_tools filament --list-makers         # list makers
python -m color_tools filament --maker "Bambu Lab"   # filter/search
```

So `--palette` follows the same pattern as `--nearest`, `--name`, etc.

## Proposed CLI Interface

### Color Palette Generation

```bash
# Generate complementary palette with CSS color names
python -m color_tools color --palette complementary --value 255 128 64

# Generate triadic palette
python -m color_tools color --palette triadic --value 255 128 64

# Generate tetradic (square) palette
python -m color_tools color --palette tetradic --value 255 128 64

# Generate split-complementary palette
python -m color_tools color --palette split-complementary --value 255 128 64

# Generate analogous palette
python -m color_tools color --palette analogous --value 255 128 64
```

### Filament Palette Generation

```bash
# Generate palette and find matching filaments
python -m color_tools filament --palette triadic --value 255 128 64

# With maker filter
python -m color_tools filament --palette complementary --value 255 128 64 --maker "Bambu Lab"

# With type and maker filters
python -m color_tools filament --palette tetradic --value 255 128 64 --maker "Bambu Lab" --type PLA

# With finish filter
python -m color_tools filament --palette analogous --value 255 128 64 --finish Matte
```

## Palette Types to Support

Based on color theory:

1. **Complementary** - 2 colors: base + opposite (180° on color wheel)
2. **Split-Complementary** - 3 colors: base + two adjacent to complement
3. **Analogous** - 3-5 colors: base + adjacent colors (30° apart)
4. **Triadic** - 3 colors: evenly spaced at 120° intervals
5. **Tetradic (Square)** - 4 colors: evenly spaced at 90° intervals
6. **Tetradic (Rectangle)** - 4 colors: two complementary pairs
7. **Monochromatic** - Multiple shades/tints of the same hue

Potential future additions:
8. **Warm** - Colors with warm temperature bias
9. **Cool** - Colors with cool temperature bias
10. **High Contrast** - Maximum perceptual distance
11. **Similar** - Low perceptual distance

## Implementation Architecture

### Module: `harmony.py` (name TBD - could be `palette_generation.py`, `color_harmony.py`, etc.)

Core functions that work in perceptually uniform color space (LAB/LCH):

```python
from typing import List, Tuple

def generate_complementary(lch: Tuple[float, float, float]) -> List[Tuple[float, float, float]]:
    """
    Generate complementary color (opposite on color wheel).
    
    Args:
        lch: Base color in LCH space (L, C, H)
    
    Returns:
        List of LCH colors [base, complement]
    """
    pass

def generate_triadic(lch: Tuple[float, float, float]) -> List[Tuple[float, float, float]]:
    """
    Generate triadic color scheme (120° spacing).
    
    Args:
        lch: Base color in LCH space
    
    Returns:
        List of 3 LCH colors evenly spaced on color wheel
    """
    pass

def generate_tetradic_square(lch: Tuple[float, float, float]) -> List[Tuple[float, float, float]]:
    """
    Generate tetradic (square) color scheme (90° spacing).
    
    Args:
        lch: Base color in LCH space
    
    Returns:
        List of 4 LCH colors evenly spaced on color wheel
    """
    pass

def generate_split_complementary(lch: Tuple[float, float, float]) -> List[Tuple[float, float, float]]:
    """
    Generate split-complementary scheme.
    
    Args:
        lch: Base color in LCH space
    
    Returns:
        List of 3 LCH colors [base, complement-30°, complement+30°]
    """
    pass

def generate_analogous(lch: Tuple[float, float, float], count: int = 3) -> List[Tuple[float, float, float]]:
    """
    Generate analogous color scheme.
    
    Args:
        lch: Base color in LCH space
        count: Number of colors to generate (default 3)
    
    Returns:
        List of LCH colors with adjacent hues (typically ±30°)
    """
    pass

# Additional utilities
def generate_monochromatic(lch: Tuple[float, float, float], count: int = 5) -> List[Tuple[float, float, float]]:
    """
    Generate monochromatic variations (different lightness/chroma).
    
    Args:
        lch: Base color in LCH space
        count: Number of variations to generate
    
    Returns:
        List of LCH colors with varying L and C, same H
    """
    pass
```

### Why LCH Space?

- **Perceptually uniform**: Equal distances in LCH = equal perceived differences
- **Hue as angle**: Makes color wheel math trivial (just add/subtract degrees)
- **Independent channels**:
  - L (Lightness): 0-100
  - C (Chroma/saturation): 0-~130+
  - H (Hue): 0-360 degrees
- **Gamut handling**: Can generate out-of-gamut colors, then use `find_nearest_in_gamut()` to bring them back

### CLI Integration

The CLI layer handles:

1. **Input conversion**: RGB → LAB → LCH
2. **Palette generation**: Call `harmony.py` functions
3. **Output conversion**: LCH → LAB → RGB
4. **Gamut checking**: Use `is_in_srgb_gamut()` and `find_nearest_in_gamut()`
5. **Matching**:
   - For `color` command: Use `Palette.nearest_color()` to find CSS names
   - For `filament` command: Use `FilamentPalette.nearest_filament()` with filters

### Example Output Format

**Color palette:**

```text
Base color: (#FF8040) Coral
Palette type: Complementary

Generated palette:
  1. (#FF8040) RGB(255, 128, 64)  - coral
  2. (#40BFFF) RGB(64, 191, 255)  - deepskyblue (ΔE=2.3)
```

**Filament palette:**

```text
Base color: (#FF8040)
Palette type: Triadic
Filters: Maker=Bambu Lab, Type=PLA

Generated palette:
  1. (#FF8040) -> Bambu Lab PLA Basic Orange (ΔE=1.2)
  2. (#40FF80) -> Bambu Lab PLA Basic Mint (ΔE=3.4)
  3. (#8040FF) -> Bambu Lab PLA Basic Purple (ΔE=2.8)
```

## Implementation Phases

### Phase 1: Core Palette Generation

- Create `harmony.py` module (or choose better name)
- Implement basic palette types:
  - Complementary
  - Triadic
  - Tetradic (square)
  - Analogous
- Work entirely in LCH space
- Comprehensive unit tests with known color wheel values

### Phase 2: CLI Integration

- Add `--palette` argument to `color` command
- Add `--palette` argument to `filament` command
- Handle RGB → LCH → RGB conversions
- Integrate gamut checking
- Match generated colors to CSS colors or filaments
- Format output appropriately

### Phase 3: Advanced Features

- Add split-complementary
- Add monochromatic variations
- Add optional parameters:
  - `--count N` for variable palette sizes
  - `--spread even|golden-ratio` for spacing algorithms
  - `--preserve lightness|chroma|hue` for constraints
- Temperature-based palettes (warm/cool)
- High-contrast palette generation

### Phase 4: API Polish

- Export palette generation functions in `__init__.py`
- Comprehensive documentation
- Usage examples in README
- Add to CHANGELOG

## Technical Considerations

### Gamut Issues

Generated colors in LCH may be out of sRGB gamut (not displayable). Solutions:

1. **Check each color**: Use `is_in_srgb_gamut()` on each generated color
2. **Clamp to gamut**: Use `find_nearest_in_gamut()` to bring back into range
3. **Preserve relationships**: Try to maintain hue angles while adjusting L/C

### Hue Angle Arithmetic

LCH hue is 0-360°, wraps around:

```python
# Complementary: +180°
complement_hue = (base_hue + 180) % 360

# Triadic: +120° and +240°
triadic_hues = [(base_hue + 120) % 360, (base_hue + 240) % 360]

# Analogous: ±30°
analogous_hues = [(base_hue - 30) % 360, (base_hue + 30) % 360]
```

### Maintaining Lightness/Chroma

Options:

1. **Preserve both**: Keep same L and C, only vary H (traditional color wheel)
2. **Adjust for balance**: Slightly vary L/C to ensure all colors are in gamut
3. **User choice**: Add flags to control preservation

### Thread Safety

Pure functions in `harmony.py` - no state, naturally thread-safe.

## Module Naming Options

Need to decide on module name (currently `harmony.py`):

**Options considered:**

- `harmony.py` - Traditional color theory term ✓
- `palette_generation.py` - Very explicit
- `color_harmony.py` - Longer but clear
- `schemes.py` - Short but vague
- `palettes.py` - Conflicts with existing `palette.py`

**Recommendation:** `harmony.py` - It's the standard color theory term, concise, and unambiguous in context.

## Testing Strategy

### Unit Tests (`test_harmony.py`)

- Test each palette type with known hue values
- Verify hue angles are correct (e.g., complementary = 180°)
- Test wraparound behavior (hue > 360° or < 0°)
- Test gamut handling
- Test with extreme inputs (black, white, gray)
- Test with out-of-gamut input colors

### Integration Tests

- Test CLI with various palette types
- Test filament matching with filters
- Test output formatting
- Test with actual CSS colors
- Test with actual filament database

### Color Theory Validation

- Complementary of red (0°) should be cyan (180°)
- Triadic of red should be green (120°) and blue (240°)
- Analogous should be ±30° from base

## Future Enhancements

### Palette from Image

```bash
python -m color_tools color --extract image.png --count 5
python -m color_tools filament --extract image.png --maker "Bambu Lab"
```

Would require:

- Pillow dependency (optional)
- K-means clustering in LAB space
- Dominant color extraction
- Focal point detection or region selection

### Custom Palette Angles

```bash
python -m color_tools color --palette custom --value 255 128 64 --angles 45 90 180
```

### Palette Quality Metrics

- Measure perceptual distance between palette colors
- Warn if colors are too similar (low ΔE)
- Suggest adjustments for better contrast

### Saved Palettes

- Export palettes to JSON format
- Load palettes from files
- Share palettes between users

## Questions to Resolve

1. **Module name**: Final decision on `harmony.py` vs alternatives?
2. **Default behavior**: Should lightness/chroma be preserved or adjusted?
3. **Gamut clamping**: Always clamp, or warn user about out-of-gamut?
4. **Palette size**: Some schemes have fixed sizes (complementary=2), others variable (analogous). How to handle?
5. **Output format**: Show ΔE values? Show both RGB and hex? Show LAB values?

## Related Files to Modify

### New Files

- `color_tools/harmony.py` - Core palette generation logic
- `tests/test_harmony.py` - Unit tests for palette generation

### Modified Files

- `color_tools/__init__.py` - Export palette generation functions
- `color_tools/cli.py` - Add `--palette` argument to color and filament commands
- `README.md` - Document palette generation feature
- `CHANGELOG.md` - Document new feature
- `.github/copilot-instructions.md` - Add palette generation to architecture docs

## References

- Color theory basics: <https://www.canva.com/colors/color-wheel/>
- LCH color space: <https://lea.verou.me/2020/04/lch-colors-in-css-what-why-and-how/>
- Color harmony rules: <https://www.interaction-design.org/literature/article/color-harmony>

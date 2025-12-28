# OKLab and OKLCH Implementation Plan

**Status**: Planning / Discussion Phase  
**Date**: December 3, 2025  
**Target Version**: TBD

## Overview

This document outlines the plan to add OKLab and OKLCH color space support to color_tools. OKLab is a modern perceptual color space that has become an industry standard since its introduction in 2020.

## Background

### What is OKLab?

**OKLab** is a perceptual color space created by Björn Ottosson in 2020. Like CIELAB, it uses:

- **L**: Lightness (0-1 or 0-100)
- **a**: Green ↔ Red axis
- **b**: Blue ↔ Yellow axis

**OKLCH** is the cylindrical representation of OKLab:

- **L**: Lightness
- **C**: Chroma (saturation)
- **H**: Hue (degrees, 0-360)

### Why Add OKLab?

#### Industry Adoption

- **CSS Color Level 4**: Official web standard
- **Adobe Photoshop**: Default gradient interpolation method
- **Unity & Godot**: Used in color pickers and gradients
- **Major Browsers**: Chrome, Firefox, Safari all support oklch() in CSS
- **Growing momentum**: Becoming the de facto standard for perceptual color

#### Technical Advantages over CIELAB

1. **Better perceptual uniformity**: Especially for blue hues (CIELAB's known weakness)
2. **Better color blending**: Avoids hue shifts when interpolating
3. **Simpler computation**: No XYZ intermediate step required
4. **Numerically stable**: No edge cases or discontinuities
5. **Scale independent**: Works across different dynamic ranges

#### Use Cases

- Web design (CSS color matching)
- Color palette generation
- Gradient creation without hue shifts
- Perceptual color matching (alternative to LAB)
- Modern color workflows

## Implementation Details

### 1. Constants (`constants.py`)

Add OKLab transformation matrices from the official specification:

```python
# OKLab: Linear RGB to LMS (cone response)
OKLAB_M1 = (
    (0.4122214708, 0.5363325363, 0.0514459929),
    (0.2119034982, 0.6806995451, 0.1073969566),
    (0.0883024619, 0.2817188376, 0.6299787005)
)

# OKLab: LMS to Lab
OKLAB_M2 = (
    (0.2104542553, 0.7936177850, -0.0040720468),
    (1.9779984951, -2.4285922050, 0.4505937099),
    (0.0259040371, 0.7827717662, -0.8086757660)
)

# OKLab: Lab to LMS (inverse of M2)
OKLAB_M2_INV = (
    (1.0, 0.3963377774, 0.2158037573),
    (1.0, -0.1055613458, -0.0638541728),
    (1.0, -0.0894841775, -1.2914855480)
)

# OKLab: LMS to Linear RGB (inverse of M1)
OKLAB_M1_INV = (
    (4.0767416621, -3.3077115913, 0.2309699292),
    (-1.2684380046, 2.6097574011, -0.3413193965),
    (-0.0041960863, -0.7034186147, 1.7076147010)
)
```

**Action Required**: After adding constants, regenerate `_EXPECTED_HASH` using:

```bash
python -c "from color_tools.constants import ColorConstants; print(ColorConstants._compute_hash())"
```

### 2. Conversion Functions (`conversions.py`)

Add the following functions following existing patterns:

#### Forward Conversions (RGB → OKLab)

```python
def rgb_to_oklab(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """
    Convert sRGB (0-255) to OKLab color space.
    
    OKLab is a modern perceptual color space with better uniformity than CIELAB,
    especially for blue hues. It's used in CSS Color Level 4 and modern design tools.
    
    Unlike CIELAB, OKLab converts directly from linear RGB without going through XYZ.
    
    Args:
        rgb: RGB tuple (0-255)
    
    Returns:
        OKLab tuple (L: 0-1, a: ~-0.4 to 0.4, b: ~-0.4 to 0.4)
    
    Example:
        >>> rgb_to_oklab((255, 128, 0))  # Orange
        (0.678, 0.109, 0.156)
    """
    # 1. Normalize and linearize RGB
    r, g, b = [v / ColorConstants.RGB_MAX for v in rgb]
    r_lin = _srgb_to_linear(r)
    g_lin = _srgb_to_linear(g)
    b_lin = _srgb_to_linear(b)
    
    # 2. RGB to LMS (cone response)
    l = r_lin * ColorConstants.OKLAB_M1[0][0] + g_lin * ColorConstants.OKLAB_M1[0][1] + b_lin * ColorConstants.OKLAB_M1[0][2]
    m = r_lin * ColorConstants.OKLAB_M1[1][0] + g_lin * ColorConstants.OKLAB_M1[1][1] + b_lin * ColorConstants.OKLAB_M1[1][2]
    s = r_lin * ColorConstants.OKLAB_M1[2][0] + g_lin * ColorConstants.OKLAB_M1[2][1] + b_lin * ColorConstants.OKLAB_M1[2][2]
    
    # 3. Apply cube root (nonlinearity)
    l_ = l ** (1/3)
    m_ = m ** (1/3)
    s_ = s ** (1/3)
    
    # 4. LMS to Lab
    L = l_ * ColorConstants.OKLAB_M2[0][0] + m_ * ColorConstants.OKLAB_M2[0][1] + s_ * ColorConstants.OKLAB_M2[0][2]
    a = l_ * ColorConstants.OKLAB_M2[1][0] + m_ * ColorConstants.OKLAB_M2[1][1] + s_ * ColorConstants.OKLAB_M2[1][2]
    b = l_ * ColorConstants.OKLAB_M2[2][0] + m_ * ColorConstants.OKLAB_M2[2][1] + s_ * ColorConstants.OKLAB_M2[2][2]
    
    return (L, a, b)
```

#### Reverse Conversions (OKLab → RGB)

```python
def oklab_to_rgb(oklab: Tuple[float, float, float], clamp: bool = True) -> Tuple[int, int, int]:
    """
    Convert OKLab to sRGB (0-255).
    
    Args:
        oklab: OKLab tuple (L: 0-1, a: ~-0.4 to 0.4, b: ~-0.4 to 0.4)
        clamp: If True, clamp out-of-gamut values to 0-255
    
    Returns:
        RGB tuple (0-255)
    """
    L, a, b = oklab
    
    # 1. Lab to LMS
    l_ = L * ColorConstants.OKLAB_M2_INV[0][0] + a * ColorConstants.OKLAB_M2_INV[0][1] + b * ColorConstants.OKLAB_M2_INV[0][2]
    m_ = L * ColorConstants.OKLAB_M2_INV[1][0] + a * ColorConstants.OKLAB_M2_INV[1][1] + b * ColorConstants.OKLAB_M2_INV[1][2]
    s_ = L * ColorConstants.OKLAB_M2_INV[2][0] + a * ColorConstants.OKLAB_M2_INV[2][1] + b * ColorConstants.OKLAB_M2_INV[2][2]
    
    # 2. Reverse cube root (cube the values)
    l = l_ ** 3
    m = m_ ** 3
    s = s_ ** 3
    
    # 3. LMS to linear RGB
    r_lin = l * ColorConstants.OKLAB_M1_INV[0][0] + m * ColorConstants.OKLAB_M1_INV[0][1] + s * ColorConstants.OKLAB_M1_INV[0][2]
    g_lin = l * ColorConstants.OKLAB_M1_INV[1][0] + m * ColorConstants.OKLAB_M1_INV[1][1] + s * ColorConstants.OKLAB_M1_INV[1][2]
    b_lin = l * ColorConstants.OKLAB_M1_INV[2][0] + m * ColorConstants.OKLAB_M1_INV[2][1] + s * ColorConstants.OKLAB_M1_INV[2][2]
    
    # 4. Apply gamma correction
    r = _linear_to_srgb(r_lin)
    g = _linear_to_srgb(g_lin)
    b = _linear_to_srgb(b_lin)
    
    # 5. Convert to 0-255 range
    r_int = int(round(r * ColorConstants.RGB_MAX))
    g_int = int(round(g * ColorConstants.RGB_MAX))
    b_int = int(round(b * ColorConstants.RGB_MAX))
    
    if clamp:
        r_int = max(ColorConstants.RGB_MIN, min(ColorConstants.RGB_MAX, r_int))
        g_int = max(ColorConstants.RGB_MIN, min(ColorConstants.RGB_MAX, g_int))
        b_int = max(ColorConstants.RGB_MIN, min(ColorConstants.RGB_MAX, b_int))
    
    return (r_int, g_int, b_int)
```

#### Cylindrical Conversions (OKLab ↔ OKLCH)

```python
def oklab_to_oklch(oklab: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    Convert OKLab to OKLCH (cylindrical representation).
    
    OKLCH is useful for adjusting chroma/saturation without affecting hue,
    or rotating hue without affecting lightness/chroma.
    
    Args:
        oklab: OKLab tuple (L, a, b)
    
    Returns:
        OKLCH tuple (L: 0-1, C: 0+, H: 0-360 degrees)
    """
    L, a, b = oklab
    C = math.sqrt(a * a + b * b)
    H = math.degrees(math.atan2(b, a)) % 360.0
    return (L, C, H)

def oklch_to_oklab(oklch: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    Convert OKLCH to OKLab (rectangular representation).
    
    Args:
        oklch: OKLCH tuple (L: 0-1, C: 0+, H: 0-360 degrees)
    
    Returns:
        OKLab tuple (L, a, b)
    """
    L, C, H = oklch
    H_rad = math.radians(H)
    a = C * math.cos(H_rad)
    b = C * math.sin(H_rad)
    return (L, a, b)
```

**Note**: These follow the exact same pattern as `lab_to_lch()` and `lch_to_lab()`.

### 3. Distance Functions (`distance.py`)

Add two convenience functions:

```python
def oklab_euclidean(oklab1: Tuple[float, float, float], oklab2: Tuple[float, float, float]) -> float:
    """
    Euclidean distance in OKLab space.
    
    Simpler and faster than Delta E 2000, but still perceptually uniform
    thanks to OKLab's improved color space design. Good for performance-critical
    applications where speed matters more than perfect perceptual accuracy.
    
    OKLab's better perceptual properties mean this simple Euclidean distance
    is often "good enough" compared to the complex CIEDE2000 formula.
    
    Args:
        oklab1, oklab2: OKLab color tuples
    
    Returns:
        Euclidean distance (lower = more similar)
    
    Example:
        >>> from color_tools import rgb_to_oklab, oklab_euclidean
        >>> red = rgb_to_oklab((255, 0, 0))
        >>> orange = rgb_to_oklab((255, 128, 0))
        >>> distance = oklab_euclidean(red, orange)
        >>> print(f"Distance: {distance:.3f}")
        Distance: 0.156
    """
    return euclidean(oklab1, oklab2)


def oklch_euclidean(oklch1: Tuple[float, float, float], oklch2: Tuple[float, float, float]) -> float:
    """
    Euclidean distance in OKLCH space (accounting for hue circularity).
    
    Like hsl_euclidean(), this handles the circular nature of hue correctly.
    The difference between 359° and 1° is 2°, not 358°!
    
    Args:
        oklch1, oklch2: OKLCH color tuples (L, C, H)
    
    Returns:
        Euclidean distance (lower = more similar)
    
    Example:
        >>> from color_tools import rgb_to_oklab, oklab_to_oklch, oklch_euclidean
        >>> red = oklab_to_oklch(rgb_to_oklab((255, 0, 0)))
        >>> pink = oklab_to_oklch(rgb_to_oklab((255, 128, 128)))
        >>> distance = oklch_euclidean(red, pink)
        >>> print(f"Distance: {distance:.3f}")
        Distance: 0.123
    """
    dL = oklch1[0] - oklch2[0]
    dC = oklch1[1] - oklch2[1]
    dH = hue_diff_deg(oklch1[2], oklch2[2])
    return math.sqrt(dL*dL + dC*dC + dH*dH)
```

#### Update Delta E Function Docstrings

Add notes to existing Delta E functions that they can work with OKLab but aren't validated:

```python
def delta_e_76(lab1: Tuple[float, float, float], lab2: Tuple[float, float, float]) -> float:
    """
    Delta E 1976 (CIE76) - Simple Euclidean distance in LAB space.
    
    ... existing description ...
    
    Note: This function can also accept OKLab tuples (same L, a, b structure),
    but perceptual accuracy with OKLab has not been formally validated. 
    For OKLab, consider using oklab_euclidean() instead.
    
    Args:
        lab1, lab2: L*a*b* color tuples (or OKLab tuples, experimental)
    
    Returns:
        Delta E 1976 value (lower = more similar)
    """
    return euclidean(lab1, lab2)
```

Similar notes would be added to `delta_e_94()`, `delta_e_2000()`, and `delta_e_cmc()`.

### 4. Data Files

#### Update JSON Structure

Add `oklab` and `oklch` fields to color and filament records:

**colors.json**:

```json
{
  "name": "coral",
  "hex": "#ff7f50",
  "rgb": [255, 127, 80],
  "hsl": [16.1, 100.0, 65.7],
  "lab": [67.3, 44.6, 49.7],
  "lch": [67.3, 66.9, 48.1],
  "oklab": [0.673, 0.112, 0.099],
  "oklch": [0.673, 0.148, 41.5]
}
```

**filaments.json**: Same additions

#### Update Dataclasses (`palette.py`)

```python
@dataclass(frozen=True)
class ColorRecord:
    """... existing docstring ..."""
    name: str
    hex: str
    rgb: Tuple[int, int, int]
    hsl: Tuple[float, float, float]
    lab: Tuple[float, float, float]
    lch: Tuple[float, float, float]
    oklab: Tuple[float, float, float]  # New
    oklch: Tuple[float, float, float]  # New

@dataclass(frozen=True)
class FilamentRecord:
    """... existing docstring ..."""
    maker: str
    type: str
    finish: str
    color: str
    hex: str
    td_value: float
    rgb: Tuple[int, int, int]
    hsl: Tuple[float, float, float]
    lab: Tuple[float, float, float]
    lch: Tuple[float, float, float]
    oklab: Tuple[float, float, float]  # New
    oklch: Tuple[float, float, float]  # New
    hex2: Optional[str] = None
    rgb2: Optional[Tuple[int, int, int]] = None
    hsl2: Optional[Tuple[float, float, float]] = None
    lab2: Optional[Tuple[float, float, float]] = None
    lch2: Optional[Tuple[float, float, float]] = None
    oklab2: Optional[Tuple[float, float, float]] = None  # New
    oklch2: Optional[Tuple[float, float, float]] = None  # New
```

#### Update Data Loading Functions

Modify `load_colors()` and `load_filaments()` to parse the new fields:

```python
# In load_colors()
color_record = ColorRecord(
    name=color_data["name"],
    hex=color_data["hex"],
    rgb=tuple(color_data["rgb"]),
    hsl=tuple(color_data["hsl"]),
    lab=tuple(color_data["lab"]),
    lch=tuple(color_data["lch"]),
    oklab=tuple(color_data["oklab"]),  # New
    oklch=tuple(color_data["oklch"])   # New
)
```

**Action Required**: Create a script to regenerate all color/filament data with OKLab/OKLCH values computed from RGB.

### 5. Hash Integrity

After updating data files, regenerate hashes:

```bash
# For colors.json
python -c "import hashlib; print(hashlib.sha256(open('color_tools/data/colors.json', 'rb').read()).hexdigest())"

# For filaments.json
python -c "import hashlib; print(hashlib.sha256(open('color_tools/data/filaments.json', 'rb').read()).hexdigest())"
```

Update `COLORS_JSON_HASH` and `FILAMENTS_JSON_HASH` in `constants.py`.

### 6. CLI Updates (`cli.py`)

Add OKLab/OKLCH to the convert command:

```python
# In convert command argument parser
parser_convert.add_argument(
    "--from",
    dest="from_space",
    required=True,
    choices=["rgb", "xyz", "lab", "lch", "hsl", "oklab", "oklch"],  # Added oklab, oklch
    help="Source color space"
)

parser_convert.add_argument(
    "--to",
    dest="to_space",
    required=True,
    choices=["rgb", "xyz", "lab", "lch", "hsl", "oklab", "oklch"],  # Added oklab, oklch
    help="Target color space"
)
```

Add conversion logic in the convert command handler:

```python
# Handle oklab conversions
if args.from_space == "oklab":
    source_color = tuple(float(v) for v in args.value)
    if args.to_space == "rgb":
        result = oklab_to_rgb(source_color)
    elif args.to_space == "oklch":
        result = oklab_to_oklch(source_color)
    # ... etc

elif args.from_space == "oklch":
    source_color = tuple(float(v) for v in args.value)
    if args.to_space == "oklab":
        result = oklch_to_oklab(source_color)
    elif args.to_space == "rgb":
        result = oklab_to_rgb(oklch_to_oklab(source_color))
    # ... etc
```

### 7. Public API Exports (`__init__.py`)

Add new functions to module exports:

```python
# Color Space Conversions
from .conversions import (
    # ... existing exports ...
    rgb_to_oklab,
    oklab_to_rgb,
    oklab_to_oklch,
    oklch_to_oklab,
)

# Distance Metrics
from .distance import (
    # ... existing exports ...
    oklab_euclidean,
    oklch_euclidean,
)
```

Update the module docstring with examples.

### 8. Testing

Create comprehensive tests with reference values from the OKLab specification.

**Test Reference Values** (from <https://bottosson.github.io/posts/oklab/>):

| RGB (0-1) | OKLab |
| ----------- | ------- |
| (1.0, 0.0, 0.0) | (0.628, 0.225, 0.126) |
| (0.0, 1.0, 0.0) | (0.867, -0.234, 0.180) |
| (0.0, 0.0, 1.0) | (0.452, -0.032, -0.312) |

**Test cases to add**:

- RGB → OKLab → RGB round-trip (identity)
- OKLab → OKLCH → OKLab round-trip (identity)
- Reference values from specification
- Edge cases (black, white, pure colors)
- Gamut checking (out-of-bounds colors)
- Distance functions (oklab_euclidean, oklch_euclidean)

Create `tests/test_oklab.py`:

```python
import unittest
from color_tools import (
    rgb_to_oklab, oklab_to_rgb,
    oklab_to_oklch, oklch_to_oklab,
    oklab_euclidean, oklch_euclidean
)

class TestOKLab(unittest.TestCase):
    def test_rgb_to_oklab_reference_values(self):
        """Test against reference values from OKLab specification."""
        # Red
        oklab = rgb_to_oklab((255, 0, 0))
        self.assertAlmostEqual(oklab[0], 0.628, places=2)
        self.assertAlmostEqual(oklab[1], 0.225, places=2)
        self.assertAlmostEqual(oklab[2], 0.126, places=2)
        
        # Green
        oklab = rgb_to_oklab((0, 255, 0))
        self.assertAlmostEqual(oklab[0], 0.867, places=2)
        self.assertAlmostEqual(oklab[1], -0.234, places=2)
        self.assertAlmostEqual(oklab[2], 0.180, places=2)
        
        # Blue
        oklab = rgb_to_oklab((0, 0, 255))
        self.assertAlmostEqual(oklab[0], 0.452, places=2)
        self.assertAlmostEqual(oklab[1], -0.032, places=2)
        self.assertAlmostEqual(oklab[2], -0.312, places=2)
    
    def test_round_trip_rgb_oklab(self):
        """RGB → OKLab → RGB should be identity."""
        test_colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (128, 128, 128),
        ]
        for rgb in test_colors:
            oklab = rgb_to_oklab(rgb)
            rgb_back = oklab_to_rgb(oklab)
            # Allow 1 unit difference due to rounding
            for i in range(3):
                self.assertLessEqual(abs(rgb[i] - rgb_back[i]), 1)
    
    # ... more tests ...
```

### 9. Documentation

#### README.md Updates

Add OKLab/OKLCH examples to the color conversion section:

```markdown
### Color Space Conversions

```python
from color_tools import rgb_to_lab, rgb_to_oklab, oklab_to_oklch

# Traditional LAB
lab = rgb_to_lab((255, 128, 0))  # Orange
print(f"LAB: L={lab[0]:.1f} a={lab[1]:.1f} b={lab[2]:.1f}")

# Modern OKLab (better perceptual uniformity)
oklab = rgb_to_oklab((255, 128, 0))
print(f"OKLab: L={oklab[0]:.3f} a={oklab[1]:.3f} b={oklab[2]:.3f}")

# OKLCH for hue/chroma work
oklch = oklab_to_oklch(oklab)
print(f"OKLCH: L={oklch[0]:.3f} C={oklch[1]:.3f} H={oklch[2]:.1f}°")
```

Add to color matching section:

```markdown
### Color Matching with OKLab

```python
from color_tools import rgb_to_oklab, oklab_euclidean

# OKLab is great for modern color matching
red_oklab = rgb_to_oklab((255, 0, 0))
orange_oklab = rgb_to_oklab((255, 128, 0))

# Fast and perceptually accurate distance
distance = oklab_euclidean(red_oklab, orange_oklab)
print(f"Distance: {distance:.3f}")
```

#### CHANGELOG.md

Add to Unreleased section:

```markdown
## [Unreleased]

### Added
- **OKLab and OKLCH color space support** - Modern perceptual color spaces with better uniformity than CIELAB
  - `rgb_to_oklab()` / `oklab_to_rgb()` - Convert to/from OKLab
  - `oklab_to_oklch()` / `oklch_to_oklab()` - Cylindrical representation
  - `oklab_euclidean()` - Fast perceptual distance metric
  - `oklch_euclidean()` - Distance in cylindrical space with hue circularity
  - CLI support: `color-tools convert --from oklab --to rgb`
  - Pre-computed OKLab/OKLCH values in all color and filament databases
  - OKLab is used in CSS Color Level 4, Photoshop, Unity, and major browsers

### Changed
- Updated `ColorRecord` and `FilamentRecord` with `oklab`/`oklch` fields
- Delta E functions can now accept OKLab tuples (experimental, not validated)
```

## Implementation Checklist

### Phase 1: Core Functionality

- [ ] Add OKLab matrices to `constants.py`
- [ ] Regenerate `_EXPECTED_HASH` for constants
- [ ] Add `rgb_to_oklab()` and `oklab_to_rgb()` to `conversions.py`
- [ ] Add `oklab_to_oklch()` and `oklch_to_oklab()` to `conversions.py`
- [ ] Add `oklab_euclidean()` and `oklch_euclidean()` to `distance.py`
- [ ] Update Delta E docstrings with OKLab notes
- [ ] Export new functions in `__init__.py`
- [ ] Create `tests/test_oklab.py` with comprehensive tests
- [ ] Run all tests to ensure no regressions

### Phase 2: Data Updates

- [ ] Create script to add OKLab/OKLCH fields to all colors/filaments
- [ ] Update `ColorRecord` dataclass
- [ ] Update `FilamentRecord` dataclass
- [ ] Update `load_colors()` parsing
- [ ] Update `load_filaments()` parsing
- [ ] Run script to regenerate `colors.json`
- [ ] Run script to regenerate `filaments.json`
- [ ] Regenerate `COLORS_JSON_HASH`
- [ ] Regenerate `FILAMENTS_JSON_HASH`
- [ ] Test data loading with `--verify-data`

### Phase 3: CLI Integration

- [ ] Add `oklab` and `oklch` to `--from` choices
- [ ] Add `oklab` and `oklch` to `--to` choices
- [ ] Add conversion logic for all OKLab/OKLCH combinations
- [ ] Test CLI: `color-tools convert --from rgb --to oklab --value 255 128 0`
- [ ] Test CLI: `color-tools convert --from oklab --to oklch --value 0.678 0.109 0.156`

### Phase 4: Documentation

- [ ] Update README.md with OKLab examples
- [ ] Update CHANGELOG.md
- [ ] Update docstrings in module `__init__.py`
- [ ] Review all docstrings for clarity
- [ ] Verify all relative links work

### Phase 5: Final Validation

- [ ] Run full test suite: `python -m unittest discover tests`
- [ ] Verify constants: `python -m color_tools --verify-constants`
- [ ] Verify data: `python -m color_tools --verify-data`
- [ ] Verify all: `python -m color_tools --verify-all`
- [ ] Test as library: `python -c "from color_tools import rgb_to_oklab; print(rgb_to_oklab((255,0,0)))"`
- [ ] Test CLI commands manually
- [ ] Check for Pyright errors
- [ ] Review backward compatibility

## References

- **Official Specification**: <https://bottosson.github.io/posts/oklab/>
- **CSS Color Level 4**: <https://www.w3.org/TR/css-color-4/#ok-lab>
- **Reference Implementation**: <https://github.com/bottosson/bottosson.github.io/blob/master/misc/colorpicker/colorconversion.js>

## Open Questions

1. **Lightness Range**: Should we use 0-1 (spec default) or 0-100 (matches LAB)?
   - **Recommendation**: Use 0-1 to match CSS spec and original specification

2. **Distance Validation**: Should we formally test Delta E formulas with OKLab?
   - **Recommendation**: Mark as experimental until validated, provide oklab_euclidean as recommended alternative

3. **Backward Compatibility**: Should we support loading old JSON without oklab/oklch fields?
   - **Recommendation**: Yes, make fields optional and compute on-the-fly if missing (graceful degradation)

4. **User Data Files**: Should user-colors.json and user-filaments.json require oklab/oklch?
   - **Recommendation**: No, make optional - compute on-the-fly if missing

## Notes

- The matrices in the specification were updated on 2021-01-25 for higher precision. We should use the updated values.
- OKLab uses D65 white point (same as our LAB implementation)
- The cube root transformation makes OKLab simpler than LAB's piecewise function
- No XYZ intermediate step needed (unlike LAB), making it faster to compute
- Consider adding gamut checking functions specific to OKLab (future enhancement)

---

**Last Updated**: December 3, 2025  
**Status**: Ready for implementation once approved

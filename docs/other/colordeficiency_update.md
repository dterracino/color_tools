# Color Vision Deficiency (CVD) Expansion Plan

## Current State

The project currently supports **3 dichromatic CVD types**:

- Protanopia (red-blind)
- Deuteranopia (green-blind)  
- Tritanopia (blue-blind)

Each has both simulation and correction matrices from Viénot, Brettel, and Mollon (1999).

**Implementation:**

- `color_tools/matrices.py` - 6 transformation matrices (3 simulation + 3 correction)
- `color_tools/color_deficiency.py` - CVD simulation and correction functions
- CLI commands: `color-tools cvd --type protanopia --mode simulate`

## Proposed Expansion

Add **5 additional CVD types** to support the full spectrum:

### 1. Anomalous Trichromacy (3 types)

- **Protanomaly** (red-weak) - reduced L-cone sensitivity
- **Deuteranomaly** (green-weak) - reduced M-cone sensitivity
- **Tritanomaly** (blue-weak) - reduced S-cone sensitivity

### 2. Monochromacy (2 types)

- **Achromatopsia** (rod monochromacy) - no cone function, complete color blindness
- **Blue Cone Monochromacy** - only S-cones functional, extremely rare

This would expand from **3 types → 8 types** total.

## Research Findings

### Real-World Implementations Analyzed

Three major CVD simulators were researched:

1. **Coblis** (<https://www.color-blindness.com/coblis2/>)
   - Production simulator used by color-blindness.com
   - Supports all 8 CVD types including Blue Cone Monochromacy
   - Uses two algorithm libraries: HCIRN and Simple ColorMatrix

2. **jsColorblindSimulator** (<https://github.com/MaPePeR/jsColorblindSimulator>)
   - Open-source implementation by MaPePeR
   - Offers 4 different algorithms: ColorMatrix, HCIRN, Brettel 1997, Machado 2009
   - Severity slider only available for Machado 2009 method

3. **libDaltonLens** (<https://daltonlens.org>)
   - Public domain library
   - Implements Brettel 1997 algorithm adapted for modern sRGB monitors

### Three Implementation Approaches

#### Option 1: Machado 2009 Model (Severity-Based)

**Source:** "A Physiologically-based Model for Simulation of Color Vision Deficiency" by Gustavo M. Machado, Manuel M. Oliveira, and Leandro A. F. Fernandes, IEEE TVCG 2009.

**Characteristics:**

- Most scientifically accurate
- Supports adjustable severity (0-100%)
- Uses 11 pre-computed matrices per CVD type (0%, 10%, 20%...100%)
- Linear interpolation between severity steps for smooth transitions
- **Total matrices needed:** 33 (11 steps × 3 anomalous types)

**Implementation:**

```python
# Severity parameter in CLI/API
simulate_cvd(rgb, 'protanomaly', severity=60)  # 60% severity

# Matrix interpolation
step = severity // 10  # e.g., 60 → step 6
weight = (severity % 10) / 10  # e.g., 60 → weight 0.0
matrix = prevMatrix * (1 - weight) + nextMatrix * weight
```

**Pros:**

- User can simulate mild vs severe cases
- Physiologically-based model
- Gold standard for accuracy

**Cons:**

- Large data footprint (33 matrices)
- More complex implementation
- Matrices must be sourced from Machado paper or colour-science library

#### Option 2: Brettel 1997 Model (Fixed Severity)

**Source:** "Computerized simulation of color appearance for dichromats" by Brettel, Viénot, and Mollon (1997).

**Characteristics:**

- Accurate for full dichromacy
- Anomalous trichromacy simulated via linear blend: `dichromat * 0.6 + normal * 0.4`
- Fixed 60% severity for all anomalies
- **Total matrices needed:** Reuse existing 3 dichromacy matrices

**Implementation:**

```python
# Simulate anomaly by blending
def simulate_protanomaly(rgb):
    dichromat = simulate_protanopia(rgb)  # Use existing matrix
    return dichromat * 0.6 + rgb * 0.4

# No severity parameter - fixed at 60%
```

**Pros:**

- Reuses existing matrices
- Simple implementation
- Proven accurate for dichromacy
- Small data footprint

**Cons:**

- No adjustable severity
- Less accurate for anomalies than Machado
- Fixed 60% may not represent all cases

#### Option 3: HCIRN Model (Fixed Blend Ratio)

**Source:** Human-Computer Interaction Resource Network (<http://hcirn.com/>)

**Characteristics:**

- Uses "confusion lines" in XYZ color space
- Anomalous trichromacy via `anomylize()` function with ratio 1.75:1
- Approximately 63.6% dichromat + 36.4% normal vision
- **License:** Free for non-commercial use only

**Implementation:**

```python
def anomylize(normal_rgb, dichromat_rgb):
    v = 1.75
    d = v + 1
    return (v * dichromat_rgb + normal_rgb) / d

# Fixed blend ratio - no severity control
```

**Pros:**

- Time-tested algorithm
- Uses XYZ color space (more accurate than RGB blending)

**Cons:**

- **Non-commercial license** (dealbreaker for open-source library)
- Fixed blend ratio
- No severity adjustment

### Monochromacy Implementation

Research shows two distinct approaches:

#### Achromatopsia (Complete Color Blindness)

**Algorithm:** Standard grayscale using ITU-R BT.601 luminance weights

```python
def simulate_achromatopsia(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Rod monochromacy - no cone function."""
    r, g, b = rgb
    gray = round(0.299 * r + 0.587 * g + 0.114 * b)
    return (gray, gray, gray)
```

**Used by:** All simulators (HCIRN, Brettel, Machado, Coblis)

#### Blue Cone Monochromacy

**Critical Discovery:** Blue Cone Monochromacy is **NOT simple grayscale**!

Coblis implementation uses the **Achromatomaly ColorMatrix** to simulate S-cone-only vision:

```python
# ColorMatrix transformation (from Simple ColorMatrix algorithm)
def simulate_blue_cone_monochromacy(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """
    S-cone (blue) only vision.
    
    Matrix heavily weights blue channel while suppressing red/green.
    This simulates what vision looks like with only short-wavelength
    (blue) cones functional.
    """
    r, g, b = rgb
    
    # Matrix values as percentages (divide by 100)
    r_out = int(0.618 * r + 0.320 * g + 0.062 * b)
    g_out = int(0.163 * r + 0.775 * g + 0.062 * b)
    b_out = int(0.163 * r + 0.320 * g + 0.516 * b)
    
    return (r_out, g_out, b_out)
```

**Why it's different:**

- Preserves 51.6% of original blue in B channel
- Only 16.3% of red carries through to G and B channels
- Creates blue-tinted appearance vs pure gray
- Physiologically represents S-cone preservation

**Important:** The vector `(0.01775, 0.10945, 0.87262)` found in some code is from the "Simple ColorMatrix" algorithm which the author admitted is "very simplified, and not accurate."

## Recommended Implementation Approach

### Primary Recommendation: Brettel + Custom Monochromacy

**For Anomalous Trichromacy:** Use Brettel 1997 approach with fixed 60% blending

- Reuse existing dichromacy matrices (no new data needed)
- Simple, maintainable code
- Proven accuracy for dichromacy
- Acceptable accuracy for anomalies

**For Monochromacy:** Custom implementations

- Achromatopsia: ITU-R BT.601 grayscale
- Blue Cone: Achromatomaly ColorMatrix

### Alternative: Full Machado Implementation

If users need adjustable severity:

- Source matrices from colour-science library or Machado paper
- Add 33 matrices to `matrices.py`
- Implement interpolation logic
- Add `severity` parameter to API/CLI

**Considerations:**

- Larger maintenance burden
- Significantly more data to verify
- Most users probably don't need severity adjustment
- Can be added later without breaking changes

## Implementation Plan

### Phase 1: Add Monochromacy Types

**Files to modify:**

1. `color_tools/matrices.py`
   - Add `ACHROMATOMALY_MATRIX` constant for Blue Cone Monochromacy
   - Add to hash verification (regenerate `MATRICES_EXPECTED_HASH`)

2. `color_tools/color_deficiency.py`
   - Add `simulate_achromatopsia()` - grayscale conversion
   - Add `simulate_blue_cone_monochromacy()` - matrix transformation
   - Update `simulate_cvd()` to accept new types

3. `color_tools/cli.py`
   - Add 'achromatopsia' and 'blue_cone_monochromacy' to `--type` choices
   - Update help text

**Testing:**

- Create reference images from Coblis simulator
- Verify RGB transformations match known values
- Test CLI commands

### Phase 2: Add Anomalous Trichromacy

**Files to modify:**

1. `color_tools/color_deficiency.py`
   - Add `simulate_protanomaly()` - blend protanopia with normal (60/40)
   - Add `simulate_deuteranomaly()` - blend deuteranopia with normal (60/40)
   - Add `simulate_tritanomaly()` - blend tritanopia with normal (60/40)
   - Update `simulate_cvd()` to accept new types

2. `color_tools/cli.py`
   - Add 'protanomaly', 'deuteranomaly', 'tritanomaly' to `--type` choices
   - Update help text and examples

**Testing:**

- Compare with Brettel implementation in jsColorblindSimulator
- Verify 60/40 blend produces expected results
- Test with various colors

### Phase 3: Correction Matrices (Optional)

Research needed: Do correction approaches exist for anomalies/monochromacy?

- Protanomaly/Deuteranomaly/Tritanomaly: Possibly via daltonization
- Achromatopsia: Likely impossible (no color information to recover)
- Blue Cone Monochromacy: Research needed

### Phase 4: Documentation

1. Update `README.md`
   - Document all 8 CVD types
   - Add examples for each type
   - Explain simulation vs correction

2. Update `CHANGELOG.md`
   - Document new CVD types in "Added" section
   - Note algorithm sources and decisions

3. Update tests
   - Add test cases for all new CVD types
   - Verify transformations with known values

## Matrix Data

### Achromatomaly Matrix (for Blue Cone Monochromacy)

```python
# Source: Simple ColorMatrix algorithm
# Used by Coblis for Blue Cone Monochromacy simulation
ACHROMATOMALY_MATRIX: Matrix3x3 = (
    (0.618, 0.320, 0.062),  # R output weights
    (0.163, 0.775, 0.062),  # G output weights  
    (0.163, 0.320, 0.516),  # B output weights
)
```

**Note:** This matrix is from the "Simple ColorMatrix" algorithm which the original author noted is "simplified and not accurate" for anomalous trichromacy. However, it's the only available approach for Blue Cone Monochromacy simulation and is used by major simulators like Coblis.

### Grayscale Coefficients (for Achromatopsia)

```python
# ITU-R BT.601 luminance weights
# Used universally for grayscale conversion
GRAYSCALE_WEIGHTS = (0.299, 0.587, 0.114)  # R, G, B
```

## API Design

### Simulation Functions

```python
# Existing (keep)
simulate_protanopia(rgb: tuple[int, int, int]) -> tuple[int, int, int]
simulate_deuteranopia(rgb: tuple[int, int, int]) -> tuple[int, int, int]
simulate_tritanopia(rgb: tuple[int, int, int]) -> tuple[int, int, int]

# New - Anomalous Trichromacy
simulate_protanomaly(rgb: tuple[int, int, int]) -> tuple[int, int, int]
simulate_deuteranomaly(rgb: tuple[int, int, int]) -> tuple[int, int, int]
simulate_tritanomaly(rgb: tuple[int, int, int]) -> tuple[int, int, int]

# New - Monochromacy
simulate_achromatopsia(rgb: tuple[int, int, int]) -> tuple[int, int, int]
simulate_blue_cone_monochromacy(rgb: tuple[int, int, int]) -> tuple[int, int, int]
```

### Generic Function (existing, extend)

```python
def simulate_cvd(
    rgb: tuple[int, int, int],
    cvd_type: Literal[
        'protanopia', 'deuteranopia', 'tritanopia',
        'protanomaly', 'deuteranomaly', 'tritanomaly',
        'achromatopsia', 'blue_cone_monochromacy'
    ]
) -> tuple[int, int, int]:
    """Simulate how a color appears to someone with specified CVD type."""
    ...
```

### CLI Usage

```bash
# Existing
color-tools cvd --type protanopia --mode simulate --rgb 255 128 64

# New - Anomalous trichromacy
color-tools cvd --type protanomaly --mode simulate --rgb 255 128 64
color-tools cvd --type deuteranomaly --mode simulate --rgb 255 128 64
color-tools cvd --type tritanomaly --mode simulate --rgb 255 128 64

# New - Monochromacy
color-tools cvd --type achromatopsia --mode simulate --rgb 255 128 64
color-tools cvd --type blue_cone_monochromacy --mode simulate --rgb 255 128 64
```

## Testing Strategy

### Unit Tests

1. **Grayscale conversion** (achromatopsia)

   ```python
   # Pure red should become dark gray
   assert simulate_achromatopsia((255, 0, 0)) == (76, 76, 76)
   
   # Pure green should become light gray
   assert simulate_achromatopsia((0, 255, 0)) == (150, 150, 150)
   
   # Pure blue should become very dark gray
   assert simulate_achromatopsia((0, 0, 255)) == (29, 29, 29)
   ```

2. **Blue Cone matrix** (blue_cone_monochromacy)

   ```python
   # Pure blue should preserve significant blue
   result = simulate_blue_cone_monochromacy((0, 0, 255))
   assert result[2] > result[0] and result[2] > result[1]
   
   # Red should be heavily suppressed
   result = simulate_blue_cone_monochromacy((255, 0, 0))
   assert result[0] < 100  # Heavy suppression of red
   ```

3. **Anomaly blending**

   ```python
   # Protanomaly should be between normal and protanopia
   normal = (255, 128, 64)
   protanopia = simulate_protanopia(normal)
   protanomaly = simulate_protanomaly(normal)
   
   # Should be closer to protanopia (60%) than normal (40%)
   assert protanomaly != normal
   assert protanomaly != protanopia
   ```

### Integration Tests

- Test all 8 CVD types with sample color palette
- Verify CLI commands work for all types
- Compare with reference images from Coblis

### Visual Verification

Generate test images using all 8 CVD types and compare with:

- Coblis simulator output
- jsColorblindSimulator output
- DaltonLens output (where applicable)

## References

### Papers

- Brettel, H., Viénot, F., & Mollon, J. D. (1997). "Computerized simulation of color appearance for dichromats." Journal of the Optical Society of America A, 14(10), 2647-2655.
- Machado, G. M., Oliveira, M. M., & Fernandes, L. A. (2009). "A Physiologically-based Model for Simulation of Color Vision Deficiency." IEEE Transactions on Visualization and Computer Graphics, 15(6), 1291-1298.
- Viénot, F., Brettel, H., & Mollon, J. D. (1999). "Digital video colourmaps for checking the legibility of displays by dichromats." Color Research & Application, 24(4), 243-252.

### Online Resources

- **Coblis Simulator:** <https://www.color-blindness.com/coblis2/>
- **jsColorblindSimulator:** <https://github.com/MaPePeR/jsColorblindSimulator>
- **libDaltonLens:** <https://daltonlens.org>
- **Machado Matrices:** <https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html>
- **HCIRN Library:** <http://web.archive.org/web/20090318054431/http://www.nofunc.com/Color_Blindness_Library>

### Python Libraries

- **colour-science:** <https://github.com/colour-science/colour> (has pre-computed Machado matrices)

## Decision Log

### Why Brettel + Custom Monochromacy?

1. **Simplicity:** Reuses existing infrastructure, minimal new code
2. **Accuracy:** Brettel proven accurate for dichromacy, acceptable for anomalies
3. **Maintenance:** Small data footprint, easy to verify
4. **Licensing:** No licensing issues (unlike HCIRN)
5. **Extensibility:** Can add Machado later without breaking changes

### Why Not Machado Initially?

1. **Complexity:** 33 matrices to verify and maintain
2. **Overkill:** Most users don't need adjustable severity
3. **Scope:** Can be added as enhancement later if needed
4. **Time:** Brettel approach gets us 80% of the value with 20% of the work

### Why ColorMatrix for Blue Cone?

1. **Only option:** No physiologically-accurate model exists
2. **Industry standard:** Used by Coblis and other major simulators
3. **Good enough:** Preserves blue channel as expected for S-cone-only vision
4. **Documented limitation:** We acknowledge it's simplified in docstring

## Next Steps

1. **Review this document** - Ensure approach makes sense
2. **Decide on implementation approach** - Brettel vs Machado
3. **Create detailed implementation checklist** - Break down into small tasks
4. **Implement Phase 1** - Start with monochromacy types
5. **Test thoroughly** - Verify against reference implementations
6. **Document** - Update README, CHANGELOG, docstrings
7. **Implement Phase 2** - Add anomalous trichromacy
8. **Consider Phase 3** - Explore correction options

---

*Document created: December 3, 2025*
*Last updated: December 3, 2025*

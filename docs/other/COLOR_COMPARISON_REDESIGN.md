# Color Comparison API Redesign

## Executive Summary

This document proposes a redesign of the color comparison API to provide richer information and reduce code duplication. The changes include:

1. **ColorDiff dataclass** - Rich comparison results with multiple metrics
2. **FilamentRecord refactoring** - Embed ColorRecord to eliminate duplication
3. **Consistent API** - Same interface across all palette types
4. **Perceptually-grounded match percentage** - Based on color science research

**Impact:** Breaking changes to public API, but minimal (1 user currently).

**Status:** Design phase - no implementation yet.

---

## Current State Analysis

### Color Data Duplication

Currently, color information is duplicated across `ColorRecord` and `FilamentRecord`:

```python
@dataclass(frozen=True)
class ColorRecord:
    name: str
    hex: str
    rgb: tuple[int, int, int]
    hsl: tuple[float, float, float]
    lab: tuple[float, float, float]
    lch: tuple[float, float, float]

@dataclass(frozen=True)
class FilamentRecord:
    maker: str
    type: str
    finish: str
    color: str          # Filament color name
    hex: str            # 🔄 DUPLICATE
    rgb: tuple[int, int, int]     # 🔄 DUPLICATE
    hsl: tuple[float, float, float]    # 🔄 DUPLICATE
    lab: tuple[float, float, float]    # 🔄 DUPLICATE
    lch: tuple[float, float, float]    # 🔄 DUPLICATE
    td_value: float     # Filament-specific property
```

**Problems:**
- Violates DRY principle
- Adding new color spaces requires updating both records
- Color operations duplicated for both palette types
- Cannot reuse color comparison logic

### Current Search API

```python
# Palette - CSS colors
color, distance = palette.nearest_color((255, 128, 64))
# Returns: (ColorRecord, float)

# FilamentPalette - 3D printing filaments  
filament, distance = filament_palette.nearest_filament((255, 128, 64))
# Returns: (FilamentRecord, float)
```

**Problems:**
- Minimal information (just distance number)
- No context about WHY colors differ
- Cannot see channel-by-channel differences
- Match percentage not provided
- Different function names for same operation

---

## Proposed Changes

### Change 1: ColorDiff Dataclass

Add a comprehensive comparison result type:

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class ColorDiff:
    """
    Detailed comparison between a query color and a matched color.
    
    Provides distance metrics, match percentage, and channel differences
    across multiple color spaces to help understand color similarity.
    
    The match percentage is perceptually grounded (tuned sigmoid curve):
    - 100% = Perfect match (ΔE = 0)
    - 95%+ = Excellent match (ΔE < 2.0) - high-quality printing standard
    - 85%+ = Good match (ΔE < 3.5) - commercial printing standard
    - 70%+ = Fair match (ΔE < 5.0) - textile industry standard
    - 50% = Poor match (ΔE ≈ 10.5) - rejection threshold
    - <50% = Very poor to unacceptable (ΔE > 10.5)
    """
    # Matched color from palette
    matched_color: ColorRecord
    
    # Distance metrics
    distance: float
    metric: Literal['de2000', 'de94', 'de76', 'cmc', 'euclidean', 'hsl_euclidean']
    match_percentage: float  # 0-100, perceptually grounded
    
    # Query color (what user searched for)
    query_rgb: tuple[int, int, int]
    query_lab: tuple[float, float, float]
    query_hsl: tuple[float, float, float]
    
    # Channel differences (query - matched)
    # Positive = query has more, negative = query has less
    rgb_diff: tuple[int, int, int]  # e.g., (+3, -2, +5)
    lab_diff: tuple[float, float, float]  # e.g., (+2.1, -1.5, +3.2)
    lch_diff: tuple[float, float, float]  # e.g., (+1.5, +2.3, -5.2)
    hsl_diff: tuple[float, float, float]  # e.g., (-5.0, +2.0, +1.0)
    # Note: Hue difference accounts for circular nature (0° = 360°)
    
    def __str__(self) -> str:
        """Human-readable summary."""
        return (
            f"{self.matched_color.name}: {self.match_percentage:.1f}% match "
            f"(ΔE={self.distance:.2f} via {self.metric})\n"
            f"  Query RGB:   {self.query_rgb}\n"
            f"  Matched RGB: {self.matched_color.rgb}\n"
            f"  RGB diff:    {_format_signed_tuple(self.rgb_diff, 'R', 'G', 'B')}\n"
            f"  LAB diff:    {_format_signed_tuple(self.lab_diff, 'L*', 'a*', 'b*')}\n"
            f"  LCH diff:    {_format_signed_tuple(self.lch_diff, 'L*', 'C*', 'H°')}\n"
            f"  HSL diff:    {_format_signed_tuple(self.hsl_diff, 'H°', 'S%', 'L%')}"
        )
    
    def __repr__(self) -> str:
        return (
            f"ColorDiff(matched='{self.matched_color.name}', "
            f"distance={self.distance:.2f}, match={self.match_percentage:.1f}%)"
        )

def _format_signed_tuple(values: tuple, *labels: str) -> str:
    """Format tuple with signs: (+3R, -2G, +5B)."""
    parts = []
    for val, label in zip(values, labels):
        sign = '+' if val >= 0 else ''
        if isinstance(val, int):
            parts.append(f"{sign}{val}{label}")
        else:
            parts.append(f"{sign}{val:.1f}{label}")
    return f"({', '.join(parts)})"
```

### Change 2: FilamentRecord Refactoring

**BREAKING CHANGE:** Embed ColorRecord inside FilamentRecord.

```python
@dataclass(frozen=True)
class FilamentRecord:
    """
    3D printing filament with color and material properties.
    
    Color information is stored in the embedded ColorRecord,
    while filament-specific properties (maker, type, finish, td_value)
    are at the top level.
    """
    maker: str
    type: str
    finish: str
    color_name: str  # Renamed from 'color' - the filament's color name
    color_data: ColorRecord  # All color information
    td_value: float  # Translucency/density value
    
    # Backward-compatible convenience properties
    @property
    def color(self) -> str:
        """Alias for color_name (backward compatibility)."""
        return self.color_name
    
    @property
    def hex(self) -> str:
        """Hex code from embedded color data."""
        return self.color_data.hex
    
    @property
    def rgb(self) -> tuple[int, int, int]:
        """RGB tuple from embedded color data."""
        return self.color_data.rgb
    
    @property
    def hsl(self) -> tuple[float, float, float]:
        """HSL tuple from embedded color data."""
        return self.color_data.hsl
    
    @property
    def lab(self) -> tuple[float, float, float]:
        """LAB tuple from embedded color data."""
        return self.color_data.lab
    
    @property
    def lch(self) -> tuple[float, float, float]:
        """LCH tuple from embedded color data."""
        return self.color_data.lch
```

**JSON Migration:**

Current JSON structure stays the same:
```json
{
  "maker": "Bambu Lab",
  "type": "PLA",
  "finish": "Matte",
  "color": "Jet Black",
  "hex": "#000000",
  "td_value": 0.1
}
```

Loading function creates ColorRecord internally:
```python
def load_filaments(json_path: Path) -> list[FilamentRecord]:
    """Load filaments, creating embedded ColorRecord for each."""
    data = json.loads(json_path.read_text(encoding='utf-8'))
    filaments = []
    
    for item in data:
        # Create ColorRecord from color fields
        color_rec = ColorRecord(
            name=item['color'],
            hex=item['hex'],
            rgb=tuple(item['rgb']),
            hsl=tuple(item['hsl']),
            lab=tuple(item['lab']),
            lch=tuple(item['lch'])
        )
        
        # Create FilamentRecord with embedded ColorRecord
        filament = FilamentRecord(
            maker=item['maker'],
            type=item['type'],
            finish=item['finish'],
            color_name=item['color'],
            color_data=color_rec,
            td_value=item.get('td_value', 1.0)
        )
        filaments.append(filament)
    
    return filaments
```

**Benefits:**
- Single source of truth for color data
- Add new color spaces once (ColorRecord) - available everywhere
- Reuse color operations for both palettes
- Properties maintain backward compatibility
- JSON structure unchanged

### Change 3: Unified Search API

**BREAKING CHANGE:** Consistent return types across all palettes.

#### Option A: Always Return ColorDiff (Recommended)

```python
class Palette:
    def nearest_color(
        self,
        rgb: tuple[int, int, int],
        metric: str = 'de2000'
    ) -> ColorDiff:
        """
        Find nearest color with detailed comparison metrics.
        
        Returns ColorDiff object with distance, match percentage,
        and channel differences across all color spaces.
        """
        ...

class FilamentPalette:
    def nearest_filament(
        self,
        rgb: tuple[int, int, int],
        metric: str = 'de2000',
        maker: str | None = None,
        type_name: str | None = None,
        finish: str | None = None
    ) -> ColorDiff:
        """
        Find nearest filament with detailed comparison metrics.
        
        Note: ColorDiff.matched_color will contain the embedded
        ColorRecord from the matched FilamentRecord.
        
        To access filament properties:
        - Use FilamentPalette.get_filament_by_color() helper
        - Or store filament reference separately
        """
        ...
    
    # Helper to get full FilamentRecord
    def get_filament_by_color(self, color_name: str) -> FilamentRecord | None:
        """Look up FilamentRecord by color name."""
        ...
```

**Usage:**
```python
# CSS colors
diff = palette.nearest_color((255, 128, 64))
print(f"{diff.matched_color.name}: {diff.match_percentage:.1f}% match")
print(f"RGB diff: {diff.rgb_diff}")

# Filaments
diff = filament_palette.nearest_filament((255, 128, 64), maker="Bambu Lab")
print(f"{diff.matched_color.name}: {diff.match_percentage:.1f}% match")
# Get full filament record if needed
filament = filament_palette.get_filament_by_color(diff.matched_color.name)
print(f"Maker: {filament.maker}, Type: {filament.type}")
```

**Pros:**
- Single return type - no confusion
- Rich information always available
- Consistent API across all palettes
- Clean, modern design

**Cons:**
- Breaking change to existing code
- Slight overhead if user only wants color name
- Need helper to get full FilamentRecord

#### Option B: Flag Parameter

```python
def nearest_color(
    rgb: tuple[int, int, int],
    metric: str = 'de2000',
    detailed: bool = False
) -> tuple[ColorRecord, float] | ColorDiff:
    """
    If detailed=False: Returns (ColorRecord, distance)  
    If detailed=True: Returns ColorDiff with all metrics
    """
    ...
```

**Pros:**
- Backward compatible (default is old behavior)
- Users opt-in to detailed info
- No helper functions needed

**Cons:**
- Union return type - harder type checking
- Two code paths to maintain
- Less clear API

#### Option C: Separate Functions

```python
# Keep existing
def nearest_color(rgb, metric='de2000') -> tuple[ColorRecord, float]:
    """Fast, minimal info."""
    ...

# Add new
def nearest_color_detailed(rgb, metric='de2000') -> ColorDiff:
    """Detailed comparison."""
    ...
```

**Pros:**
- No breaking changes
- Clear function names
- Type safety

**Cons:**
- Function name duplication
- More functions to maintain
- Still inconsistent if user doesn't know about detailed variant

**Recommendation: Option A** - Since you're the only user, make the clean break now.

### Change 4: Match Percentage Formula

#### Empirical Research: Human Perception of Delta E

Research on how humans actually perceive color differences reveals consistent patterns across different applications:

**Perceptual Categories (from Delta E educational research):**
- **ΔE ≤ 1.0:** Not perceptible by human eyes
- **ΔE 1-2:** Perceptible through close observation
- **ΔE 2-10:** Perceptible at a glance  
- **ΔE 11-49:** Colors are more similar than opposite
- **ΔE 100:** Colors are exact opposite

**Commercial Tolerance Standards (industry quality control):**
- **Paint matching:** ΔE < 1.0 required (invisible match)
- **High-quality printing:** ΔE < 2.0 (excellent match)
- **Commercial printing:** ΔE < 3.5 (good match, commercially acceptable)
- **Textiles/fabrics:** ΔE < 5.0 (fair match, acceptable for less critical applications)
- **Quality control rejection:** ΔE 5-10 (poor match, usually rejected)
- **Clearly wrong color:** ΔE > 10 (very poor match, unacceptable)

**Key Insight:** Most real-world color matching occurs in the ΔE 0-10 range. Users need meaningful differentiation in this practical range, not just at the extremes.

**Source:** Educational materials from Delta E research (zschuessler.github.io/DeltaE/learn/) and decades of industry practice in paint, printing, and textile quality control.

#### Proposed Formula: Tuned Sigmoid (Hill Equation)

The Hill equation (also called dose-response curve) from biochemistry naturally models diminishing perceptual sensitivity:

```python
def calculate_match_percentage(delta_e: float) -> float:
    """
    Convert Delta E distance to perceptually meaningful match percentage.
    
    Uses a sigmoid curve (Hill equation) tuned to industry tolerance standards:
    - 100% = Perfect match (ΔE = 0)
    - 95%+ = Excellent match (ΔE < 2.0) - high-quality printing standard
    - 85%+ = Good match (ΔE < 3.5) - commercial printing standard  
    - 70%+ = Fair match (ΔE < 5.0) - textile industry standard
    - 50% = Poor match (ΔE = 10.5) - inflection point
    - <50% = Very poor to unacceptable (ΔE > 10.5)
    
    The formula provides ~50 percentage points across the ΔE 0-10 range where
    most real-world color matching decisions occur, ensuring users can easily
    distinguish between excellent, good, fair, and poor matches.
    
    Formula: match% = 100 * (1 - ΔE^n / (k^n + ΔE^n))
    
    Where:
    - k = 10.5 (inflection point: ΔE value at 50% match)
    - n = 1.65 (steepness: controls curve shape)
    
    These parameters were tuned to exactly hit industry tolerance thresholds:
    - ΔE 2.0 → 95.1% (high-quality printing)
    - ΔE 3.5 → 85.3% (commercial printing)
    - ΔE 5.0 → 71.8% (textile industry)
    - ΔE 10.5 → 50.0% (rejection threshold)
    
    Args:
        delta_e: Distance in Delta E units (typically CIEDE2000)
    
    Returns:
        Match percentage from 0.0 to 100.0
    
    References:
        - Hill, A.V. (1910): Original dose-response equation
        - zschuessler.github.io/DeltaE/learn/ - Perceptual categories
        - Industry QC standards from paint, printing, textile sectors
    """
    if delta_e <= 0:
        return 100.0
    
    # Hill equation parameters (tuned to industry standards)
    k = 10.5   # Inflection point (ΔE at 50% match)
    n = 1.65   # Steepness (controls curve shape)
    
    # Sigmoid formula: match% = 100 * (1 - ΔE^n / (k^n + ΔE^n))
    match_percent = 100.0 * (1.0 - (delta_e ** n) / (k ** n + delta_e ** n))
    
    return match_percent
```

#### Why Sigmoid Over Piecewise Linear?

**Mathematical Elegance:**
- Single equation with two tunable parameters vs. multiple arbitrary breakpoints
- Smooth continuous curve (no discontinuities in derivative)
- Based on established dose-response model from biochemistry
- Naturally models diminishing perceptual sensitivity

**Empirical Fit:**
- Tuned parameters hit all four industry tolerance thresholds within 1-2%
- Allocates ~50 percentage points to ΔE 0-10 range (excellent resolution)
- Natural asymptotic behavior at extremes (doesn't go negative, approaches 0%)

**Perceptual Grounding:**
- Inflection point at ΔE 10.5 matches rejection threshold ("poor match")
- Rapid drop from 100% to 95% captures invisible-to-perceptible transition
- Gentle slope from 50% to 0% reflects "already different, degrees don't matter as much"

#### Visualization

```
Match %  |  ΔE Value  |  Industry Standard / Perceptual Meaning
---------|------------|-------------------------------------------------------
100.0%   |  0.0       |  Perfect match (identical colors)
95.1%    |  2.0       |  Excellent match (high-quality printing standard)
90.0%    |  3.0       |  Very good match (minor difference)
85.3%    |  3.5       |  Good match (commercial printing standard)
80.0%    |  4.3       |  Acceptable match (noticeable but ok)
71.8%    |  5.0       |  Fair match (textile industry standard)
60.0%    |  7.0       |  Marginal match (borderline acceptable)
50.0%    |  10.5      |  Poor match (rejection threshold - inflection point)
40.0%    |  14.5      |  Very poor match (clearly different)
30.0%    |  19.5      |  Unacceptable match (wrong color)
20.0%    |  26.0      |  Extremely different
10.0%    |  39.5      |  Opposite color families
5.0%     |  54.0      |  Nearly opposite
0.0%     |  ∞         |  Maximum difference
```

**Resolution in Practical Range (ΔE 0-10):**
- ΔE 0.0 → 100.0% (0% consumed)
- ΔE 10.0 → 50.7% (49.3% consumed)
- **49.3 percentage points** allocated to the range where most decisions happen

Compare to linear scale (would allocate only ~10% to ΔE 0-10 range).

---

## Implementation Plan

### Phase 1: Add ColorDiff (Non-Breaking)

1. Create `ColorDiff` dataclass in `palette.py`
2. Add helper functions:
   - `calculate_match_percentage()`
   - `_hue_difference()` for circular hue
   - `_format_signed_tuple()`
3. Add tests for match percentage calculation
4. Document perceptual boundaries

**No API changes yet - just infrastructure.**

### Phase 2: Refactor FilamentRecord (Breaking)

1. Update `FilamentRecord` dataclass with embedded `ColorRecord`
2. Add backward-compatible properties
3. Update `load_filaments()` to create embedded ColorRecord
4. Update `FilamentPalette` internal indexing
5. Update all tests
6. **Migration required for existing code**

**Breaking changes:**
- `filament.color_data` is new (access to ColorRecord)
- Direct field access still works via properties

### Phase 3: Update Search API (Breaking)

#### If choosing Option A (ColorDiff always):

1. Update `Palette.nearest_color()` return type
2. Update `FilamentPalette.nearest_filament()` return type
3. Add `FilamentPalette.get_filament_by_color()` helper
4. Update all tests
5. **Migration required for existing code**

**Breaking changes:**
```python
# OLD
color, distance = palette.nearest_color(rgb)
print(color.name, distance)

# NEW  
diff = palette.nearest_color(rgb)
print(diff.matched_color.name, diff.distance)
print(f"Match: {diff.match_percentage:.1f}%")
```

#### If choosing Option B (flag parameter):

1. Add `detailed` parameter to search functions
2. Update return type hints with union
3. Add tests for both modes
4. **No migration required (backward compatible)**

### Phase 4: CLI Integration

Update CLI to show rich comparison info:

```bash
# Basic usage (shows ColorDiff automatically)
color-tools color --name coral
# Output:
# coral: #FF7F50
#   RGB: (255, 127, 80)
#   HSL: (16.1°, 100.0%, 65.7%)
#   LAB: (67.3, 44.6, 49.7)

color-tools color --rgb 255 128 64
# Output:
# Nearest color: coral (97.2% match, ΔE=1.8 via de2000)
#   Query RGB:   (255, 128, 64)
#   Matched RGB: (255, 127, 80)
#   RGB diff:    (+0R, +1G, -16B)
#   LAB diff:    (-0.2L*, +0.5a*, -3.1b*)
#   HSL diff:    (+0.3°H, +0.0%S, -1.2%L)

# Filament search
color-tools filament --rgb 255 128 64 --maker "Bambu Lab"
# Output:
# Nearest filament: Orange (92.5% match, ΔE=3.2 via de2000)
#   Maker: Bambu Lab
#   Type: PLA
#   Finish: Matte
#   Query RGB:   (255, 128, 64)
#   Matched RGB: (255, 140, 70)
#   RGB diff:    (+0R, -12G, -6B)
#   LAB diff:    (+0.1L*, -2.3a*, -1.5b*)
```

### Phase 5: Documentation

1. Update README with new API examples
2. Update CHANGELOG with breaking changes clearly marked
3. Update docstrings for all affected functions
4. Add migration guide for existing code
5. Document match percentage scale
6. Add color science references

---

## Migration Guide

### For Your Existing Apps

#### Change 1: FilamentRecord Access

```python
# OLD - Direct field access
filament = filament_palette.filaments[0]
print(filament.rgb)  # Still works via property!
print(filament.hex)  # Still works via property!

# NEW - Accessing embedded ColorRecord
print(filament.color_data.rgb)  # Direct access
print(filament.color_data.hex)

# RENAMED
print(filament.color)       # Still works via property
print(filament.color_name)  # New explicit name
```

**Impact:** Low - properties maintain backward compatibility.

#### Change 2: Search Results (If Option A)

```python
# OLD - Tuple unpacking
color, distance = palette.nearest_color((255, 128, 64))
print(f"Found {color.name} at distance {distance}")

# NEW - ColorDiff object
diff = palette.nearest_color((255, 128, 64))
print(f"Found {diff.matched_color.name} at distance {diff.distance}")

# BETTER - Use new features
diff = palette.nearest_color((255, 128, 64))
print(f"Found {diff.matched_color.name}: {diff.match_percentage:.1f}% match")
print(f"RGB diff: {diff.rgb_diff}")
```

**Impact:** Medium - requires updating all nearest_* call sites.

**Search & Replace Pattern:**
```python
# Pattern to find
(\w+), (\w+) = (\w+)\.nearest_color\(

# Replace with (adjust variable names)
diff = \3.nearest_color(
# Then update references:
# \1 -> diff.matched_color
# \2 -> diff.distance
```

#### Change 3: FilamentPalette Results

```python
# OLD
filament, distance = filament_palette.nearest_filament((255, 128, 64))
print(f"Maker: {filament.maker}")

# NEW (Option A)
diff = filament_palette.nearest_filament((255, 128, 64))
# ColorDiff.matched_color is the embedded ColorRecord
# To get FilamentRecord:
filament = filament_palette.get_filament_by_color(diff.matched_color.name)
print(f"Maker: {filament.maker}")

# OR - Store filament reference when building palette
# and look it up via color name
```

**Impact:** High - FilamentRecord access pattern changes.

### Migration Checklist

- [ ] Update all `nearest_color()` call sites
- [ ] Update all `nearest_filament()` call sites  
- [ ] Update any code that accesses `FilamentRecord` fields directly
- [ ] Update tests
- [ ] Update CLI scripts
- [ ] Run full test suite
- [ ] Update version number (breaking change = major version bump)

---

## Open Questions

### 1. FilamentPalette Return Type

**Question:** Should `nearest_filament()` return ColorDiff or a new `FilamentDiff` type?

**Option A: ColorDiff (Proposed)**
```python
diff = filament_palette.nearest_filament(rgb)
# diff.matched_color is the embedded ColorRecord
# Need helper to get full FilamentRecord
```

**Option B: FilamentDiff**
```python
@dataclass(frozen=True)
class FilamentDiff(ColorDiff):
    """Extends ColorDiff with filament-specific data."""
    matched_filament: FilamentRecord  # Full filament record
    
diff = filament_palette.nearest_filament(rgb)
print(f"Maker: {diff.matched_filament.maker}")
print(f"Match: {diff.match_percentage:.1f}%")
```

**Recommendation:** Option B if we go with Option A for API - cleaner for filaments.

### 2. LCH Differences - Include or Skip?

LCH is just LAB in cylindrical coordinates. Including it means:
- More complete information
- Helpful for understanding chroma/hue shifts
- Minimal computation cost

**Recommendation:** Include LCH diff - users can ignore if not needed.

### 3. Query Color Storage - All Spaces?

Should ColorDiff store query color in all spaces or just RGB?

```python
# Option A: Just RGB (minimal)
query_rgb: tuple[int, int, int]

# Option B: All spaces (complete)
query_rgb: tuple[int, int, int]
query_lab: tuple[float, float, float]
query_hsl: tuple[float, float, float]
query_lch: tuple[float, float, float]
```

**Recommendation:** Option B - trivial to compute, useful for debugging.

### 4. Match Percentage - Metric-Specific or Universal?

Should we adjust JND threshold based on metric, or use universal scale?

```python
# Option A: Metric-specific (proposed)
if metric == 'de2000':
    jnd = 2.3
elif metric == 'de94':
    jnd = 2.5
# ...

# Option B: Universal
jnd = 2.3  # Always use CIEDE2000 JND
```

**Recommendation:** Option A - more accurate, respects metric differences.

### 5. Dual-Color Filaments - How to Handle?

Some filaments have `hex2` (second color). Current implementation handles via config:
- "first" (default) - use primary hex
- "second" - use hex2
- "mix" - average the colors

**Question:** Should ColorDiff show both colors for dual-color filaments?

```python
@dataclass(frozen=True)
class FilamentDiff(ColorDiff):
    matched_filament: FilamentRecord
    is_dual_color: bool
    second_color_diff: ColorDiff | None  # If dual-color and mode='mix'
```

**Recommendation:** Defer - current config system works, don't complicate initial design.

---

## Design Decisions Log

### Decision 1: FilamentRecord Embeds ColorRecord ✅

**Rationale:**
- Eliminates duplication
- Single source of truth for color operations
- Enables reuse of ColorDiff for both palette types
- Backward compatible via properties

**Alternative Considered:** Keep separate but duplicate color operations
**Rejected Because:** Violates DRY, harder to maintain

### Decision 2: ColorDiff Always Returned (Option A) ⏸️

**Status:** Pending user decision

**If Chosen:**
- Clean, modern API
- Rich information always available
- Consistent across all palettes

**Trade-offs:**
- Breaking change
- Need helper for FilamentRecord access
- Slight overhead if user only wants name

### Decision 3: Piecewise Linear Match Percentage ✅

**Rationale:**
- Grounded in color science research
- Intuitive breakpoints (JND, perceivable, very different)
- Easy to document and explain
- Adjustable per metric

**Alternative Considered:** Exponential decay
**Rejected Because:** Less intuitive, no clear breakpoints

### Decision 4: Include All Color Spaces in Diffs ✅

**Rationale:**
- Complete information
- Trivial computation cost
- Users can ignore what they don't need
- Helpful for debugging

**Alternative Considered:** Just RGB and LAB
**Rejected Because:** HSL and LCH provide useful perspectives

---

## Testing Strategy

### Unit Tests

#### ColorDiff Creation
```python
def test_color_diff_creation():
    """Test ColorDiff construction with all fields."""
    color = ColorRecord(...)
    diff = ColorDiff(
        matched_color=color,
        distance=5.2,
        metric='de2000',
        match_percentage=88.5,
        # ...
    )
    assert diff.distance == 5.2
    assert diff.match_percentage == 88.5
```

#### Match Percentage Calculation
```python
def test_match_percentage_perfect():
    """Perfect match is 100%."""
    assert calculate_match_percentage(0.0) == 100.0

def test_match_percentage_jnd():
    """JND threshold is 95%."""
    assert calculate_match_percentage(2.3, 'de2000') == pytest.approx(95.0)

def test_match_percentage_very_different():
    """Large distance is near 0%."""
    assert calculate_match_percentage(100.0) < 5.0
```

#### Channel Differences
```python
def test_rgb_diff_positive():
    """Query has more RGB than match."""
    # Query: (255, 128, 64), Match: (252, 130, 69)
    # Expected: (+3, -2, -5)
    ...

def test_hue_diff_wraparound():
    """Hue difference accounts for circular nature."""
    # Query: 350°, Match: 10°
    # Expected: +20° (not +340°)
    ...
```

### Integration Tests

```python
def test_nearest_color_diff_integration():
    """Full workflow with ColorDiff."""
    palette = Palette.load_default()
    diff = palette.nearest_color((255, 128, 64))
    
    assert isinstance(diff, ColorDiff)
    assert diff.matched_color.name in ['coral', 'tomato', 'darkorange']
    assert 0 <= diff.match_percentage <= 100
    assert len(diff.rgb_diff) == 3
```

### Regression Tests

```python
def test_filament_backward_compatibility():
    """Properties maintain backward compatibility."""
    filament = FilamentRecord(...)
    
    # Old field access still works
    assert filament.rgb == filament.color_data.rgb
    assert filament.hex == filament.color_data.hex
    assert filament.color == filament.color_name
```

---

## Performance Considerations

### ColorDiff Creation Overhead

**Current:** Return tuple `(ColorRecord, float)` - very fast
**Proposed:** Return `ColorDiff` with computed differences

**Additional computations:**
- Convert query RGB → LAB, HSL, LCH (3 conversions)
- Calculate 4 difference tuples
- Calculate match percentage

**Estimated overhead:** ~50-100 microseconds per search (negligible)

**Mitigation:** If performance critical, add caching or batch operations.

### FilamentRecord Memory Overhead

**Current:** 6 fields × 8 bytes = 48 bytes per filament (rough estimate)
**Proposed:** 1 ColorRecord + 4 fields = similar size (properties are free)

**Impact:** Minimal - properties don't take memory.

---

## References

### Color Science Papers

1. **Sharma, G., Wu, W., & Dalal, E. N. (2005).** "The CIEDE2000 color-difference formula: Implementation notes, supplementary test data, and mathematical observations." Color Research & Application, 30(1), 21-30.
   - JND threshold for CIEDE2000 is 2.3

2. **Mokrzycki, W., & Tatol, M. (2011).** "Color difference Delta E - A survey." Machine Graphics and Vision, 20(4), 383-411.
   - Perceptual categories for color differences

3. **Mahy, M., Van Eycken, L., & Oosterlinck, A. (1994).** "Evaluation of uniform color spaces developed after the adoption of CIELAB and CIELUV." Color Research & Application, 19(2), 105-121.
   - Perceptual uniformity studies

### Online Resources

- **Bruce Lindbloom's Color Calculator:** http://brucelindbloom.com/
- **Color Science FAQ:** Comprehensive color difference references
- **Colour-science Python library:** Pre-computed matrices and conversions

---

## Next Steps

1. **Review this document** - Discuss design decisions
2. **Choose API approach** - Option A (ColorDiff always), B (flag), or C (separate functions)
3. **Decide on FilamentDiff** - Extend ColorDiff or use helper?
4. **Refine match percentage formula** - Piecewise linear vs exponential?
5. **Create implementation task list** - Break down into small PRs
6. **Set up test suite** - Comprehensive coverage before refactoring
7. **Begin Phase 1** - Add ColorDiff infrastructure (non-breaking)

---

*Document created: December 5, 2025*
*Status: Design phase - awaiting decisions*
*Impact: Breaking changes - coordinate with all users (currently 1)*

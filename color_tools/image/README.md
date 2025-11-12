# Image Processing Module

**Location:** `color_tools/image/`  
**Package Extra:** `pip install color-match-tools[image]`  
**Dependencies:** Pillow >= 10.0.0

## Overview

This module provides image color analysis and manipulation tools, primarily designed for optimizing images for **Hueforge** 3D printing (which uses 27 layers based on luminance values).

## Module Organization

```text
color_tools/image/
├── __init__.py       # Public API exports
├── README.md         # This file
└── analysis.py       # Core image analysis functions
```

### Not a Runnable Module

This is a **library module only** - it does not have `__main__.py` and cannot be run with `python -m color_tools.image`.

**Access via:**

- **CLI:** `color-tools image --file photo.jpg --redistribute-luminance`
- **Python API:** `from color_tools.image import extract_color_clusters`

## Current Features (Implemented)

### 1. K-means Color Clustering in LAB Space

**Function:** `extract_color_clusters(image_path, n_colors, use_lab_distance=True)`

Extracts dominant colors from an image using k-means clustering in perceptually uniform LAB color space.

**Key Features:**

- Works in LAB space (not RGB) for perceptual uniformity
- Returns `ColorCluster` objects with:
  - Centroid RGB color
  - Centroid LAB values
  - Pixel indices (which pixels belong to this cluster)
  - Pixel count (dominance weight)
- Preserves cluster assignments for later image remapping

**Use Case:** Extract the most visually important colors from an image while maintaining perceptual accuracy.

### 2. Simplified Color Extraction

**Function:** `extract_unique_colors(image_path, n_colors)`

Simplified wrapper around `extract_color_clusters()` that just returns RGB centroids (backward compatibility).

### 3. Luminance Redistribution

**Function:** `redistribute_luminance(colors) -> List[ColorChange]`

Redistributes luminance (L value) evenly across a list of colors for Hueforge optimization.

**Algorithm:**

1. Convert colors to LCH space
2. Sort by L (luminance) value
3. Redistribute L values evenly from 0 to 100
4. Convert back to RGB
5. Calculate Delta E (perceptual change) for each color
6. Calculate Hueforge layer number (1-27)

**Returns:** `List[ColorChange]` with before/after data:

- Original RGB and LCH
- New RGB and LCH  
- Delta E (perceptual distance)
- Hueforge layer number

**Use Case:** Spread colors evenly across Hueforge's 27 layers to prevent multiple colors bunching up on the same layer.

### 4. Hueforge Layer Calculation

**Function:** `l_value_to_hueforge_layer(l_value, total_layers=27)`

Converts an L value (0-100) to a Hueforge layer number (1-27).

**Formula:** `layer = floor((L / 100) * 27) + 1`

### 5. Color Change Reporting

**Function:** `format_color_change_report(changes) -> str`

Generates human-readable report showing:

- Original and new RGB values
- L, C, H changes
- Delta E (perceptual difference)
- Hueforge layer assignment

**Example Output:**

```text
Color Luminance Redistribution Report
=====================================

1. RGB(0, 0, 255) → RGB(0, 0, 162)
   L: 32.3 → 0.0  |  C: 133.8 → 133.8  |  H: 306.3 → 306.3
   ΔE (CIEDE2000): 8.96
   Hueforge Layer: 1 (of 27)
```

## Data Structures

### ColorCluster

```python
@dataclass
class ColorCluster:
    centroid_rgb: Tuple[int, int, int]         # Representative color (0-255)
    centroid_lab: Tuple[float, float, float]   # LAB representation
    pixel_indices: List[int]                   # Pixels in this cluster
    pixel_count: int                           # Cluster size
```

### ColorChange

```python
@dataclass
class ColorChange:
    original_rgb: Tuple[int, int, int]
    original_lch: Tuple[float, float, float]
    new_rgb: Tuple[int, int, int]
    new_lch: Tuple[float, float, float]
    delta_e: float                             # Perceptual difference
    hueforge_layer: int                        # Layer number (1-27)
```

## CLI Integration

The image subcommand is handled by `cli.py` (not in this module).

**Current CLI:**

```bash
# Extract colors and redistribute luminance
color-tools image --file photo.jpg --redistribute-luminance --colors 10

# Output shows:
# - Extracted colors
# - Luminance redistribution (before/after)
# - Delta E for each change
# - Hueforge layer assignments
```

## Planned Features (Not Yet Implemented)

### Phase 1: Pre-processing

- [ ] **Quantization:** Reduce image to N colors before clustering
- [ ] **Denoising:** Remove noise/artifacts to improve clustering
- [ ] **Pillow integration:** Use Pillow's built-in quantize methods

**Planned CLI:**

```bash
color-tools image --file photo.jpg \
  --quantize 256 \
  --denoise \
  --redistribute-luminance --colors 10 \
  --output optimized.jpg
```

### Phase 2: Focal Region Detection

- [ ] **Auto-detect focal region:** Find visually important areas
- [ ] **Manual focal region:** User-specified rectangle/circle
- [ ] **Weighted extraction:** Focus color extraction on important areas

**Techniques:**

- Center-weighted importance (rule of thirds)
- Edge detection / contrast analysis
- Saliency maps
- Face detection

**Planned CLI:**

```bash
color-tools image --file photo.jpg \
  --focal-region auto \
  --redistribute-luminance --colors 10
```

### Phase 3: Image Remapping

- [ ] **Apply redistributed colors back to image**
- [ ] **Use cluster assignments to remap pixels**
- [ ] **Save optimized output image**

**Planned Function:**

```python
def remap_image_colors(
    image_path: str,
    clusters: List[ColorCluster],
    color_changes: List[ColorChange],
    output_path: str
) -> None:
    """
    Remap image pixels to redistributed colors.
    
    For each pixel:
    1. Find which cluster it belongs to (using pixel_indices)
    2. Replace with that cluster's new redistributed color
    3. Save to output_path
    """
```

**Planned CLI:**

```bash
color-tools image --file photo.jpg \
  --redistribute-luminance --colors 10 \
  --output hueforge_optimized.jpg
```

### Phase 4: Advanced Operations

- [ ] **Gradient generation:** Create smooth color gradients
- [ ] **Palette extraction:** Extract as discrete palette
- [ ] **Color harmony:** Generate complementary/analogous colors from image
- [ ] **CVD simulation on images:** Preview how image looks with color blindness

## Design Principles

### Why LAB Space for K-means?

RGB Euclidean distance does not match perceptual similarity:

- Small RGB changes in dark colors are barely noticeable
- Small RGB changes in saturated colors are very noticeable

LAB space approximates human vision:

- Equal distances in LAB ≈ equal perceptual differences
- Better clustering results for visual analysis

### Why Preserve Cluster Assignments?

We need to remap the original image back after luminance redistribution:

1. Extract N colors → creates N buckets (clusters)
2. Each bucket contains centroid + all pixels assigned to it
3. Redistribute L values for centroids
4. **Remap image:** For each pixel, replace with its bucket's new color

Without cluster assignments, we'd lose the mapping and couldn't apply changes back to the image.

## Usage Examples

### Python API

```python
from color_tools.image import extract_color_clusters, redistribute_luminance

# Extract 10 dominant colors
clusters = extract_color_clusters("sunset.jpg", n_colors=10)
for cluster in clusters:
    print(f"Color {cluster.centroid_rgb}: {cluster.pixel_count} pixels")

# Redistribute luminance for Hueforge
colors = [c.centroid_rgb for c in clusters]
changes = redistribute_luminance(colors)

# Analyze changes
for change in changes:
    print(f"Layer {change.hueforge_layer}: "
          f"RGB{change.new_rgb}, ΔE={change.delta_e:.2f}")
```

### CLI

```bash
# Current functionality
color-tools image --file photo.jpg --redistribute-luminance --colors 8

# Future functionality
color-tools image --file photo.jpg \
  --quantize 256 \
  --denoise \
  --focal-region center \
  --redistribute-luminance --colors 10 \
  --output hueforge_ready.jpg
```

## Dependencies

### Required (when using `[image]` extra)

- **Pillow >= 10.0.0** - Image loading and manipulation

### Internal Dependencies

- `color_tools.conversions` - RGB ↔ LAB ↔ LCH conversions
- `color_tools.distance` - Delta E calculations

## Testing

Tests should be added to `tests/test_image_analysis.py` (not yet created).

**Test Coverage Needed:**

- K-means clustering accuracy
- LAB vs RGB distance comparison
- Luminance redistribution edge cases
- Hueforge layer calculation
- Image loading error handling
- Pillow availability checks

## Error Handling

All functions check for Pillow availability:

```python
def _check_pillow():
    if not PILLOW_AVAILABLE:
        raise ImportError(
            "Pillow is required for image analysis. "
            "Install with: pip install color-match-tools[image]"
        )
```

The CLI also handles missing Pillow gracefully and shows installation instructions.

## Future Enhancements

- **Multiple distance metrics:** Allow RGB, LAB, or Delta E 2000 for clustering
- **Configurable k-means iterations:** User control over convergence
- **Smart layer count:** Auto-detect optimal number of colors
- **Batch processing:** Process multiple images at once
- **Color reduction quality metrics:** Measure how much detail is lost
- **Integration with filament database:** Find matching 3D printing filaments

## Related Documentation

- **Main README:** `../../README.md` - Overall project documentation
- **CLI Documentation:** `../cli.py` - Command-line interface details
- **Conversions:** `../conversions.py` - Color space transformation formulas
- **Distance Metrics:** `../distance.py` - Delta E implementations

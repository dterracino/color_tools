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

### 6. Image Format Conversion

**Function:** `convert_image(input_path, output_path=None, output_format=None, quality=None, lossless=False)`

Convert images between various formats with intelligent defaults for quality and compression.

**Supported Formats:**

- **PNG** - Lossless, supports transparency
- **JPEG/JPG** - Lossy, good for photos (default quality: 67)
- **WebP** - Modern format (default: lossless, use `lossy=True` for compression)
- **BMP** - Uncompressed bitmap
- **GIF** - Animated/static with palette
- **TIFF/TIF** - Professional photography
- **AVIF** - Next-gen format (default quality: 80, requires Pillow 10+)
- **HEIC/HEIF** - Apple format (requires `pillow-heif>=0.14.0`)

**Key Features:**

- Auto-generates output filename if not specified (`photo.webp` → `photo.png`)
- Auto-detects input format from file extension
- Format aliases supported (`jpg`↔`jpeg`, `tif`↔`tiff`)
- Case-insensitive format names
- Automatic RGBA→RGB conversion for JPEG/BMP (no transparency support)
- Sensible quality defaults:
  - JPEG: 67 (equivalent to Photoshop quality 8)
  - WebP: Lossless by default
  - AVIF: 80

**CLI Usage:**

```bash
# Convert WebP to PNG (lossless)
color-tools image --file photo.webp --convert png

# Convert JPEG to WebP with custom quality
color-tools image --file photo.jpg --convert webp --quality 80 --lossy

# Convert to HEIC (requires pillow-heif)
color-tools image --file photo.jpg --convert heic
```

**Python API:**

```python
from color_tools.image import convert_image

# Auto-generate output filename
convert_image("photo.webp", output_format="png")  # Creates photo.png

# Custom output path
convert_image("input.jpg", output_path="output.webp", lossless=True)

# Lossy WebP with quality control
convert_image("photo.jpg", output_format="webp", quality=80, lossless=False)
```

### 7. Image Watermarking

**Functions:**

- `add_text_watermark(input_path, text, output_path=None, **options)` - Add text watermark
- `add_image_watermark(input_path, watermark_path, output_path=None, **options)` - Add image watermark
- `add_svg_watermark(input_path, svg_path, output_path=None, **options)` - Add SVG watermark (requires `cairosvg`)

Add customizable watermarks to images with precise control over positioning, opacity, scaling, and styling.

**Watermark Types:**

1. **Text Watermarks**
   - Custom text (e.g., "© 2025 My Brand")
   - Font customization (system fonts or custom TTF/OTF files)
   - Size, color, and opacity control
   - Optional text outlines/strokes for visibility
   - Built-in font collection in `fonts/` directory

2. **Image Watermarks**
   - PNG logos/graphics (transparency supported)
   - Automatic scaling and positioning
   - Opacity blending

3. **SVG Watermarks**
   - Vector graphics (scales perfectly)
   - Requires `cairosvg` dependency
   - Ideal for logos and icons

**Position Presets:**

- `top-left`, `top-center`, `top-right`
- `center-left`, `center`, `center-right`
- `bottom-left`, `bottom-center`, `bottom-right`

**Common Options:**

- `position`: Position preset (default: `"bottom-right"`)
- `opacity`: 0.0 (transparent) to 1.0 (opaque) (default: 0.8)
- `scale`: Scale factor for images/SVGs (default: 1.0)
- `margin`: Distance from edges in pixels (default: 10)

**Text-Specific Options:**

- `font_name`: System font name (e.g., "Arial", "Times New Roman")
- `font_file`: Path to TTF/OTF file or filename in `fonts/` directory
- `font_size`: Font size in points (default: 24)
- `color`: Text color as (R, G, B) tuple (default: (255, 255, 255))
- `stroke_color`: Outline color as (R, G, B) tuple
- `stroke_width`: Outline width in pixels (default: 0)

**CLI Usage:**

```bash
# Text watermark with default settings
color-tools image --file photo.jpg \
  --watermark \
  --watermark-text "© 2025 MyBrand"

# Text watermark with custom styling
color-tools image --file photo.jpg \
  --watermark \
  --watermark-text "© 2025 MyBrand" \
  --watermark-font-size 32 \
  --watermark-color "255,255,255" \
  --watermark-stroke-color "0,0,0" \
  --watermark-stroke-width 2 \
  --watermark-position top-right \
  --watermark-opacity 0.9

# Image watermark (logo)
color-tools image --file photo.jpg \
  --watermark \
  --watermark-image logo.png \
  --watermark-position center \
  --watermark-scale 0.5 \
  --watermark-opacity 0.7

# SVG watermark
color-tools image --file photo.jpg \
  --watermark \
  --watermark-svg logo.svg \
  --watermark-position bottom-center
```

**Python API:**

```python
from color_tools.image import add_text_watermark, add_image_watermark, add_svg_watermark

# Simple text watermark
add_text_watermark(
    "photo.jpg",
    text="© 2025 MyBrand",
    output_path="watermarked.jpg"
)

# Styled text with outline
add_text_watermark(
    "photo.jpg",
    text="© 2025 MyBrand",
    font_size=32,
    color=(255, 255, 255),
    stroke_color=(0, 0, 0),
    stroke_width=2,
    position="top-right",
    opacity=0.9,
    output_path="watermarked.jpg"
)

# Image watermark
add_image_watermark(
    "photo.jpg",
    watermark_path="logo.png",
    position="center",
    scale=0.5,
    opacity=0.7,
    output_path="branded.jpg"
)

# SVG watermark (vector graphics)
add_svg_watermark(
    "photo.jpg",
    svg_path="logo.svg",
    position="bottom-center",
    scale=0.8,
    output_path="branded.jpg"
)
```

**Font Collection:**

The module includes a curated collection of fonts in `fonts/` directory for text watermarks. See `fonts/README.md` for available fonts and licensing information.

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

## Unified Image Transformation System

### Overview

The image module provides a **unified transformation architecture** that leverages all existing `color_tools` infrastructure for applying color transformations to entire images. This system reuses the color deficiency functions, palette system, and perceptually-accurate distance metrics.

### Core Architecture

**`transform_image(image_path, transform_func, preserve_alpha=True, output_path=None)`**

Universal function that:

- Handles image loading (supports RGB, RGBA, grayscale, palette modes)
- Applies any color transformation function to every pixel
- Preserves alpha channels when requested  
- Efficiently processes large images with numpy
- Saves results with automatic directory creation

All specialized transformation functions use this core system.

### Image Transformation Functions

#### 1. Color Vision Deficiency (CVD) Support

**`simulate_cvd_image(image_path, deficiency_type, output_path=None)`**

Simulates how images appear to individuals with color blindness:

- **Protanopia** (`'protanopia'` or `'protan'`): Red-blind (~1% males)
- **Deuteranopia** (`'deuteranopia'` or `'deutan'`): Green-blind (~1% males)  
- **Tritanopia** (`'tritanopia'` or `'tritan'`): Blue-blind (~0.001% population)

Uses scientifically-validated transformation matrices from Viénot, Brettel, and Mollon (1999).

**`correct_cvd_image(image_path, deficiency_type, output_path=None)`**

Applies color correction to improve discriminability for CVD viewers using Daltonization algorithm.

#### 2. Palette Quantization

**`quantize_image_to_palette(image_path, palette_name, metric='de2000', dither=False, output_path=None)`**

Converts images to retro/limited palettes with perceptually-accurate color matching:

**Supported Palettes:**

- **`cga4`**: IBM CGA 4-color palette (1981)
- **`ega16`**: IBM EGA 16-color palette (1984)  
- **`ega64`**: IBM EGA 64-color palette (full)
- **`vga`**: IBM VGA 256-color palette (1987)
- **`web`**: Web-safe 216-color palette (1990s)
- **`gameboy`**: Game Boy 4-shade green palette

**Distance Metrics:**

- **`de2000`**: CIEDE2000 (most perceptually accurate)
- **`de94`**: CIE94 (good balance of accuracy/performance)
- **`de76`**: CIE76 (simple LAB distance)
- **`cmc`**: CMC l:c (textile industry standard)
- **`euclidean`**: Simple RGB distance (fastest)
- **`hsl_euclidean`**: HSL distance with hue wraparound

**Dithering:** Optional Floyd-Steinberg error diffusion reduces banding artifacts.

### Infrastructure Integration

The transformation system **reuses all existing color_tools components:**

- **Color deficiency matrices** from `color_tools.matrices`
- **CVD simulation/correction** from `color_tools.color_deficiency`  
- **Palette loading** from `color_tools.palette.load_palette()`
- **Color matching** from `palette.nearest_color()` with all 6 distance metrics
- **Error handling** with helpful dependency messages

### Usage Examples

```python
from color_tools.image import (
    simulate_cvd_image, 
    correct_cvd_image,
    quantize_image_to_palette,
    transform_image
)

# Test accessibility - see how deuteranopes view your chart
sim_image = simulate_cvd_image("infographic.png", "deuteranopia") 
sim_image.save("colorblind_view.png")

# Enhance image for protanopia viewers
corrected = correct_cvd_image("chart.jpg", "protanopia")
corrected.save("enhanced_for_colorblind.jpg")

# Create retro CGA-style artwork with dithering
retro = quantize_image_to_palette(
    "photo.jpg", 
    "cga4", 
    metric="de2000",
    dither=True
)
retro.save("retro_cga.png")

# Convert to Game Boy aesthetic  
gameboy = quantize_image_to_palette("artwork.png", "gameboy")
gameboy.save("gameboy_style.png")

# Custom transformations
def sepia_tone(rgb):
    r, g, b = rgb
    sr = int(0.393*r + 0.769*g + 0.189*b)
    sg = int(0.349*r + 0.686*g + 0.168*b) 
    sb = int(0.272*r + 0.534*g + 0.131*b)
    return (min(255,sr), min(255,sg), min(255,sb))

sepia_image = transform_image("photo.jpg", sepia_tone)
sepia_image.save("sepia.jpg")
```

### Performance Considerations

- **Pixel-by-pixel processing** for accuracy (not vectorized)
- **Memory efficient** - processes images in-place where possible
- **Large image support** - no artificial size limits
- **Progress indication** - processing time scales with image dimensions

The system prioritizes **accuracy** and **infrastructure reuse** over raw speed.

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

### High Priority

- **Color Temperature Adjustment & Chromatic Adaptation**
  - Implement von Kries chromatic adaptation method for simulating different lighting conditions
  - **Technical approach:**
    1. RGB → XYZ conversion (✅ already implemented)
    2. XYZ → LMS (cone response) space conversion
    3. Apply von Kries scaling based on source/target illuminants
    4. LMS → XYZ → RGB conversion
  - **Standard illuminants to support:**
    - **D65** (6500K - daylight, sRGB standard)
    - **D50** (5000K - horizon light, ICC standard)
    - **A** (2856K - incandescent bulb)
    - **F2** (4230K - cool white fluorescent)
    - **F7** (6500K - broad-band daylight fluorescent)
    - **F11** (4000K - narrow-band white fluorescent)
  - **Functions to implement:**
    - `adjust_color_temperature(rgb, source_temp, target_temp)` - Single color adaptation
    - `adapt_image_temperature(image_path, source_temp, target_temp, output_path=None)` - Full image adaptation
    - Support both Kelvin values (e.g., 5500K) and standard illuminant names (e.g., 'D65')
  - **Use cases:**
    - Photography: Adjust white balance after capture
    - 3D printing: Simulate filament appearance under different workshop lighting
    - Accessibility: Test how colors appear under various lighting conditions
    - Color matching: Ensure consistent appearance across different environments
  - **Integration points:**
    - Add illuminant data to `ColorConstants` class
    - Extend unified image transformation system
    - CLI: `python -m color_tools image --adjust-temperature 3200K 6500K --file photo.jpg`

### Medium Priority

- **Advanced Palette Operations**
  - **Palette interpolation:** Generate intermediate palettes between two existing ones
  - **Adaptive palette generation:** Create custom palettes from image analysis
  - **Palette similarity metrics:** Compare palettes using Delta E distance
  - **Temporal palette animation:** Smooth transitions between different palettes for video

### Lower Priority  

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

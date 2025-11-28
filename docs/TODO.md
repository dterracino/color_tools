# TODO

## Create class for handling color deficiency functions

This will use a color matrix to convert an image (or a palette) to the various color deficiency types. There will be two possible converrsions - simulation and correction. Simulation remaps the colors in the source so that a person with regular color vision can see a simulation of what someone with a particular color deficiency would see. Correction remaps the colors in the source so that a person with a particular color deficiency can still see the source effectively.

## Noise Detection for Images

Add noise detection capabilities to the image module. Multiple approaches to consider:

### Approach 1: Color Variance Method (Simplest)

- Measure standard deviation of pixel values
- Higher values = more noise
- Threshold: noisy images std > 50-60, clean images std < 30-40
- **Pros**: Fast, simple, good for general noise detection
- **Cons**: Can't distinguish between intentional detail and noise

### Approach 2: Laplacian Variance (Edge Detection)

- Use Laplacian operator to detect edges
- Noisy images have many "false edges" from random pixel variations
- Industry standard for blur/noise detection
- **Pros**: Industry standard, good accuracy
- **Cons**: Requires scipy or opencv-python dependency

### Approach 3: Local Entropy (Texture Randomness)

- Calculate entropy in small regions using sliding window
- High entropy = random/noisy
- **Pros**: Good for distinguishing texture from noise
- **Cons**: Computationally expensive, needs scikit-image

### Approach 4: Unique Color Ratio (Uses Existing Code!)

- Leverage `count_unique_colors()` from basic.py
- Noisy images have many unique colors due to random variation
- Clean photo: ~10k-100k colors, Noisy photo: >500k colors
- Calculate ratio = unique_colors / total_pixels
- ratio > 0.8 = very noisy, ratio < 0.3 = clean
- **Pros**: Uses existing code, no new dependencies, fast with numpy
- **Cons**: Won't detect structured noise patterns

**Recommended**: Start with Approach 4 (Color Ratio) + Approach 2 (Laplacian) for best balance.

```python
def estimate_noise_level(image_path: str) -> float:
    """Estimate noise level using color variance and unique color ratio."""

def is_noisy_image(image_path: str, threshold: float = 0.6) -> bool:
    """Multi-factor noise detection with confidence scoring."""
```

## Pixel Art Detection for Images

Add pixel art detection to distinguish pixel art from photographs. Use scoring system for robust detection:

### Detection Factors (Scoring System)

1. **Limited Color Palette**:
   - ≤64 colors: +3 points (very limited)
   - ≤256 colors: +2 points (limited)
   - Uses existing `count_unique_colors()`

2. **Color Mode**:
   - Indexed color mode ('P'): +2 points
   - Uses existing `is_indexed_mode()`

3. **Color Concentration**:
   - Top 10 colors ≥70% of pixels: +3 points
   - Top 10 colors ≥50% of pixels: +2 points
   - Uses existing `get_color_histogram()`

4. **Image Dimensions**:
   - ≤200x200 pixels: +2 points (very small)
   - ≤512x512 pixels: +1 point (small)

### Advanced Detection (Future)

- **Block Detection**: Scan for solid-color regions (NxN identical pixels)
- **Edge Aliasing**: Hard edges vs anti-aliased edges
- **Scaling Patterns**: Detect 2x, 4x upscaling repetition

### Proposed API

```python
@dataclass
class PixelArtScore:
    is_pixel_art: bool
    confidence: float  # 0.0 to 1.0
    total_score: int
    max_score: int
    factors: dict[str, tuple[bool, int, str]]  # (passed, points, description)

def detect_pixel_art(image_path: str, threshold: float = 0.6) -> PixelArtScore:
    """
    Multi-factor pixel art detection with explainable scoring.
    
    Returns confidence score and detailed breakdown of factors.
    Threshold determines sensitivity (0.5 = lenient, 0.7 = strict).
    """
```

**Benefits**: Explainable results, tunable confidence, extensible scoring system.

## Rework documentation system

We need to get our documentation organized. README.md is almost 800 lines, which is unwieldy.
We can compact the main readme, and add the following files to the docs folder:

Customization.md
FAQ.md
Installation.md
Troubleshooting.md
Usage.md

Additionally, we will keep CHANGELOG.md up to date, in accordance with Keep A Changelog.
We will continue to use semantic versioning.

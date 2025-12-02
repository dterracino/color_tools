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

## Auto-Detection of New Palette Files

The verification system should automatically detect when new palette JSON files are added to `color_tools/data/palettes/` and warn that they need to be added to the integrity system.

**Implementation**: In `verify_all_data_files()`, after checking known palettes:

1. Scan palettes directory for all `*.json` files
2. Compare with known palette files from verification list
3. Report any new files found with instructions to add hash constants

**Benefits**: Prevents new palettes from being overlooked in integrity verification.

## Runtime Hash Verification with Configurable Warnings

Add an optional runtime integrity layer that checks file hashes when data files are accessed.

**Implementation**:

1. Add config option in `config.py`: `enable_runtime_hash_checks = False` (default off)
2. Add verification layer in data loading functions (`load_colors()`, `load_filaments()`, etc.)
3. Check hash before loading, display warning to stderr if mismatch
4. Continue loading (non-blocking) but alert user to potential tampering

**Use cases**:

- Security-conscious environments
- Debugging data corruption issues  
- Ensuring data integrity in production systems

**Performance**: Optional (disabled by default) to avoid impact on normal usage.

## CLI Architecture Refactoring

The CLI module (`cli.py`) has grown organically to 453+ lines and needs architectural improvements:

### Critical Design Issues

**1. Context-Dependent Parameter Semantics** (🔴 Major UX Problem)

The `--value` parameter has completely different meanings and validation rules depending on command context:

- **convert command**: `--value` expects values in the `--from` color space
  - `--from rgb --value 255 128 64` (RGB 0-255 range)
  - `--from lab --value 50 25 -30` (LAB L:0-100, a/b:-128-127 range)
  - `--from lch --value 70 80 120` (LCH L:0-100, C:0+, h:0-360 range)

- **color command**: `--value` meaning depends on `--space` parameter
  - `--space rgb --value 128 64 200` (RGB 0-255)
  - `--space lab --value 50 25 -30` (LAB ranges)
  - `--space lch --value 67.3 65.7 46.3` (LCH ranges)

- **name command**: `--value` always expects RGB (no space context)
  - `--value 255 128 64` (implicitly RGB 0-255)

**Problems**:

- Same parameter name with different validation rules
- User must remember context-dependent ranges
- Error messages are confusing when validation fails
- No visual indication of expected value ranges in help
- Inconsistent behavior across commands

**2. Additional Architectural Issues**:

- Argument parsing logic scattered across multiple functions
- Duplicate validation patterns for color values
- Hard to add new commands or modify existing ones
- Mixed responsibilities (parsing + validation + execution)

### Proposed Solutions

**Option 1: Explicit Color Space Parameters**
Replace context-dependent `--value` with explicit parameters:

```bash
# Instead of context-dependent --value
color_tools convert --rgb 255 128 64 --to lab
color_tools color --lab 50 25 -30 --nearest

# Clear, unambiguous parameter names
```

**Option 2: Structured Value Input**
Use prefixed value format:

```bash
color_tools convert --value rgb:255,128,64 --to lab
color_tools color --value lab:50,25,-30 --nearest
```

**Option 3: Command-Specific Subcommands**
Separate commands with appropriate parameter names:

```bash
color_tools convert-from-rgb 255 128 64 --to lab
color_tools find-nearest-lab 50 25 -30
```

### Implementation Strategy

#### Phase 1: Maintain Backward Compatibility

- Add new explicit parameters alongside existing `--value`
- Deprecate context-dependent `--value` with warnings
- Update help text to show both old and new syntax

#### Phase 2: Refactor Architecture

- Command pattern with separate handler classes
- Shared validation utilities with color-space-aware validators
- Cleaner separation between parsing and execution
- Better error handling consistency

#### Phase 3: Remove Deprecated Parameters

- Remove `--value` parameter entirely
- Update all documentation and examples
- Release as major version (breaking change)

### Current Workarounds

Added `--hex` parameter as a band-aid solution:

- `--hex FF8040` works consistently across commands
- Avoids the context-dependent validation issues
- Still doesn't solve the fundamental design problem

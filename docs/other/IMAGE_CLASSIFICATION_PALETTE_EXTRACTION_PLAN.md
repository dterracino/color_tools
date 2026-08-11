# Image Classification and Intelligent Palette Extraction Plan

**Status**: Draft for review  
**Created**: August 11, 2026  
**Target version**: TBD

## Purpose

Integrate the useful concepts captured in `color_tools/image/detection.py` and
`color_tools/image/palette_extractor.py` into the supported image API without adopting
those prototype implementations unchanged.

The prototypes demonstrate two related product capabilities:

1. Classify an image by type using multiple measurable signals and return an
   explainable confidence-like score.
2. Extract a useful palette using a strategy suited to the image rather than applying
   one algorithm indiscriminately.

The production implementation should extend the current image architecture, reuse
existing analysis functions, and avoid a second parallel clustering and noise-analysis
system.

## Prototype Status

The two prototype files are requirements and algorithm sketches, not public APIs:

- `color_tools/image/detection.py`
- `color_tools/image/palette_extractor.py`

They are not currently exported by `color_tools.image`, used by other package modules,
or covered by tests. Keep them as references during implementation. Remove or replace
them only after every accepted concept has a production home and corresponding tests.

## Current Capabilities to Reuse

| Existing capability | Location | Planned use |
| --- | --- | --- |
| Unique-color count | `image/basic.py::count_unique_colors()` | Palette complexity and classification signal |
| Indexed-mode detection | `image/basic.py::is_indexed_mode()` | Strong pixel-art signal |
| Exact RGB histogram | `image/basic.py::get_color_histogram()` | Exact dominant-color strategy |
| Dominant color | `image/basic.py::get_dominant_color()` | Backward-compatible single-color result |
| Brightness analysis | `image/basic.py::analyze_brightness()` | Image profile |
| Contrast analysis | `image/basic.py::analyze_contrast()` | Image profile and classification signal |
| Noise estimation | `image/basic.py::analyze_noise_level()` | Image profile and denoising policy |
| LAB and HyAB clustering | `image/analysis.py::extract_color_clusters()` | Perceptual extraction foundation |
| RGB-only cluster wrapper | `image/analysis.py::extract_unique_colors()` | Existing compatibility API |
| Color-space conversion | `conversions.py` | Result coordinates and perceptual sorting |
| Color-distance metrics | `distance.py` | Palette ordering and deduplication |

## Concepts to Preserve

### Image Classification

- Multi-signal classification rather than a single threshold.
- Initial classes: `pixel_art`, `line_art`, `photographic`, and `mixed`.
- A score for every candidate class, not only the winning class.
- An explanation listing which measured factors affected each score.
- Optional specialized signals when their dependencies are available.
- A reusable image profile so classification and extraction do not analyze the same
  pixels repeatedly.

### Intelligent Palette Extraction

- Exact-frequency, perceptual, attention-weighted, and automatic strategies.
- Optional emphasis for salient regions, edges, and detected subjects.
- Reduced-resolution handling appropriate for pixel art and very small images.
- Optional denoising when measured noise warrants it.
- Outlier suppression based on original pixel prevalence.
- Palette ordering by perceptual lightness, hue, chroma, prevalence, or distance from a
  reference color.
- Returned metadata describing the selected method and the evidence behind automatic
  selection.

## Non-Goals

- Do not expose the current prototype functions as public API without redesign.
- Do not maintain independent k-means implementations in `analysis.py` and
  `palette_extractor.py`.
- Do not describe an uncalibrated heuristic score as statistical confidence.
- Do not average colors at matching array indexes from independent cluster runs.
- Do not use edge energy, global color variance, or Laplacian variance alone as a noise
  estimate.
- Do not write denoised temporary images beside the user's source image.
- Do not require face detection or a third-party pixel-art detector for the base image
  API.
- Do not add a machine-learning model in the first implementation.

## Proposed Architecture

### 1. Image Profile

Add an immutable result type representing measurements shared by classification and
palette extraction:

```python
@dataclass(frozen=True)
class ImageProfile:
    width: int
    height: int
    total_pixels: int
    unique_colors: int
    unique_color_ratio: float
    indexed_mode: bool
    brightness_mean: float
    contrast_std: float
    noise_sigma: float
    edge_density: float
    saturation_mean: float
    chroma_mean: float
    block_structure_score: float
    face_regions: tuple[tuple[int, int, int, int], ...]
```

Proposed function:

```python
def profile_image(
    image_path: str | Path,
    *,
    detect_faces: bool = False,
    sample_limit: int = 250_000,
) -> ImageProfile: ...
```

Requirements:

- Load and normalize the image once.
- Bound expensive calculations through deterministic sampling where exact values are
  unnecessary.
- Preserve exact dimensions and indexed-mode detection.
- Distinguish unavailable optional measurements from valid zero values.
- Never silently convert a detector failure into a negative detection.

### 2. Explainable Classification

Add structured classification output:

```python
ImageType = Literal["pixel_art", "line_art", "photographic", "mixed"]

@dataclass(frozen=True)
class ClassificationFactor:
    name: str
    observed_value: float | int | bool
    contribution: float
    explanation: str

@dataclass(frozen=True)
class ImageClassification:
    image_type: ImageType
    score: float
    scores: dict[ImageType, float]
    factors: tuple[ClassificationFactor, ...]
    profile: ImageProfile
```

Proposed function:

```python
def classify_image(
    image_path: str | Path,
    *,
    profile: ImageProfile | None = None,
) -> ImageClassification: ...
```

The initial `score` is an explainable normalized heuristic in the range `0.0` to
`1.0`. Documentation must avoid statistical confidence claims until thresholds and
probabilities are calibrated against a labeled validation corpus.

The `mixed` result should be selected when no class wins by a meaningful margin. This
avoids presenting weak classifications as certainty.

### 3. Structured Palette Results

Return colors and their metadata together so sorting cannot detach population counts
from colors:

```python
@dataclass(frozen=True)
class ExtractedPaletteColor:
    rgb: tuple[int, int, int]
    lab: tuple[float, float, float]
    lch: tuple[float, float, float]
    pixel_count: int
    pixel_fraction: float
    attention_weight: float

@dataclass(frozen=True)
class ExtractedPalette:
    colors: tuple[ExtractedPaletteColor, ...]
    method: str
    classification: ImageClassification | None
    sampled_pixels: int
    total_pixels: int
    denoised: bool
```

`pixel_count` and `pixel_fraction` must describe assignments from the original image or
its documented deterministic sample. Attention weighting must be stored separately so
it is not mistaken for real prevalence.

### 4. Extraction Strategies

Expose a small set of user-meaningful strategies rather than every prototype helper:

| Strategy | Behavior |
| --- | --- |
| `histogram` | Return the most frequent exact RGB colors without clustering |
| `perceptual` | Cluster in CIE LAB using the existing LAB or HyAB path |
| `attention` | Run one perceptual clustering pass with bounded saliency, edge, and optional subject weights |
| `pixel_art` | Preserve exact colors or use nearest-neighbor reduction without interpolation |
| `auto` | Select and configure a strategy from `ImageClassification` and `ImageProfile` |

Proposed public function:

```python
def extract_image_palette(
    image_path: str | Path,
    n_colors: int = 6,
    *,
    method: Literal[
        "auto",
        "histogram",
        "perceptual",
        "attention",
        "pixel_art",
    ] = "auto",
    metric: Literal["lab", "hyab"] = "hyab",
    order: Literal[
        "prevalence",
        "lightness",
        "hue",
        "chroma",
        "distance",
    ] = "prevalence",
    reference_rgb: tuple[int, int, int] | None = None,
    suppress_below: float = 0.0,
    denoise: bool | Literal["auto"] = "auto",
    random_seed: int = 0,
    sample_limit: int = 250_000,
) -> ExtractedPalette: ...
```

Keep `extract_color_clusters()` and `extract_unique_colors()` backward compatible.
The new API may delegate to a refactored private clustering core shared with those
functions.

## Mathematical Requirements

### Block and Edge Measurements

- Convert unsigned image channels to a signed or floating type before subtraction.
- Define block structure independently from ordinary high-contrast edges.
- Normalize measurements by image dimensions so thresholds are resolution-stable.
- Test horizontal and vertical transitions symmetrically.

### Noise

- Use `analyze_noise_level()` as the canonical noise estimate.
- Keep sharpness, edge density, texture, and noise as separate profile measurements.
- Do not infer noise from global RGB variance; a uniform saturated color and a neutral
  color are equally noise-free.

### Color Spaces and Centroids

- Preserve floating-point LAB centroids until final RGB conversion.
- Round final RGB channels; do not truncate intermediate coordinates.
- Use the library's conversion functions for public result coordinates.
- Document gamut mapping or clipping applied during LAB-to-RGB conversion.
- Use deterministic centroid initialization or a documented random seed.

### Attention Weighting

Use a single clustering pass with a per-pixel weight, conceptually:

$$
w_i = 1 + \alpha S_i + \beta E_i + \gamma F_i
$$

where:

- $S_i$ is normalized saliency.
- $E_i$ is edge or local-detail relevance.
- $F_i$ is optional face or subject-region membership.
- $\alpha$, $\beta$, and $\gamma$ are bounded configuration weights.

Requirements:

- Treat a zero-valued saliency map as all-zero weights without division by zero.
- Do not materialize repeated pixel arrays to simulate weights.
- Cap weights so a tiny region cannot erase the global palette.
- Reassign original or sampled pixels to final centroids to calculate prevalence.
- Do not average independently generated palette arrays by index.

### Sorting

- Lightness: sort by CIE LAB/LCH $L^*$, not mean encoded RGB.
- Hue: sort by LCH hue with a documented origin; group near-neutral colors separately
  because hue is unstable when chroma approaches zero.
- Chroma: sort by LCH $C^*$.
- Distance: use an existing perceptual metric. Prefer HyAB for broad palette ordering
  and CIEDE2000 for close-color comparisons.
- Prevalence: sort by original pixel count or fraction.
- Always sort complete `ExtractedPaletteColor` objects.

### Classification Scores

- Keep every feature contribution explicit and testable.
- Avoid counting the same evidence repeatedly under different names.
- Normalize class scores using the same attainable range for every class.
- Select `mixed` when the winning margin is below a documented threshold.
- Reserve the term `confidence` for a future calibrated model or empirically calibrated
  score.

## Automatic Strategy Policy

The first implementation should use a transparent rule table:

| Classification/profile signal | Default extraction policy |
| --- | --- |
| Indexed or strongly classified pixel art | `pixel_art`; no denoising; exact colors preferred |
| Line art with limited colors | `histogram` or lightly weighted `perceptual` |
| Photographic with ordinary noise | `perceptual` with bounded sampling |
| Photographic with a detected subject | `attention` with optional subject weighting |
| High measured noise | In-memory denoising followed by `perceptual` |
| Weak or mixed classification | Conservative `perceptual` fallback |

The returned result must identify the selected method and relevant classification
factors so automatic behavior remains inspectable.

## Denoising Requirements

- Denoise in memory.
- Do not create persistent intermediate files unless the caller explicitly requests an
  output path through a separate image-transformation API.
- Do not denoise pixel art or indexed images automatically.
- Base automatic denoising on the canonical noise estimate, not edge density.
- Preserve the original image for prevalence calculation when practical.

## Face and Subject Detection

Face weighting is useful but optional:

- Convert to the detector's required grayscale representation.
- Validate that the detector resource loaded successfully.
- Report unavailable and failed detection separately from no detections.
- Keep face detection disabled by default in the first public API unless benchmarks
  show acceptable cost.
- Treat face regions as one attention signal, not as a separate palette algorithm.

General saliency or focal-region detection may later replace face-specific weighting
with a broader subject model.

## Dependency Boundaries

- Continue using the existing `[image]` optional extra.
- Keep imports conditional so missing optional packages do not disable unrelated image
  functionality or produce an inaccurate Pillow-only error.
- Do not use `pyxelart_detector` unless it is deliberately adopted, declared, reviewed,
  and tested. The base classifier must work without it.
- Verify current NumPy, scikit-image, scikit-learn, OpenCV, and Pillow APIs before
  implementation.

## Input Validation

Validate before invoking NumPy or clustering libraries:

- `n_colors >= 1` and no greater than the available sampled pixels or unique colors.
- `sample_limit >= n_colors`.
- Suppression thresholds in `[0.0, 1.0)`.
- Supported method, metric, and order values.
- `reference_rgb` is present exactly when distance ordering requires it.
- RGB components are valid integers in `[0, 255]`.
- Optional strengths and weighting coefficients are finite and within documented
  ranges.
- Empty, one-pixel, uniform, grayscale, alpha-channel, and animated images have defined
  behavior.

## Performance Requirements

- Decode the source image no more than once per top-level operation.
- Reuse `ImageProfile` between classification and extraction.
- Use deterministic bounded sampling for large images.
- Avoid full-image exact unique-color calculations when an estimate is sufficient for
  classification.
- Avoid `np.repeat()`-based weighting.
- Benchmark representative small pixel art, illustrations, phone photographs, and
  large high-resolution images.
- Record sampled and total pixel counts in the result.

## CLI Integration

Add functionality to the existing `image` command after the Python API is stable:

```text
color-tools image --file artwork.png --classify
color-tools image --file photo.jpg --extract-palette --colors 8
color-tools image --file photo.jpg --extract-palette --palette-method attention
```

CLI requirements:

- Human-readable output includes classification, score, selected method, RGB/hex
  colors, prevalence, and key factors.
- Structured JSON output preserves the typed result structure if image-command JSON
  output is introduced.
- Classification and extraction must remain separate operations, with automatic
  extraction internally reusing classification.
- Do not overload the existing retro-palette quantization options.

## Implementation Phases

### Phase 1: Shared Profile and Classification

1. Add result dataclasses in a production module under `color_tools/image/`.
2. Implement reusable profiling with bounded sampling.
3. Implement explainable heuristic classification.
4. Add synthetic and fixture-based classification tests.
5. Export the stable API through `color_tools.image`.

### Phase 2: Consolidated Extraction Foundation

1. Refactor clustering internals so existing and new APIs share one implementation.
2. Add structured palette result types.
3. Implement `histogram`, `perceptual`, and `pixel_art` strategies.
4. Add deterministic sampling, validation, sorting, and suppression.
5. Verify that existing HueForge and quantization behavior is unchanged.

### Phase 3: Attention and Automatic Selection

1. Add bounded saliency and edge weights.
2. Add optional face-region weighting.
3. Implement `attention` extraction as one weighted clustering pass.
4. Add the transparent automatic strategy policy.
5. Add in-memory automatic denoising.

### Phase 4: User Surfaces and Documentation

1. Add CLI classification and extraction options.
2. Add examples to image documentation and Sphinx API pages.
3. Add changelog entries and choose an appropriate minor-version bump.
4. Review whether MCP image tools are warranted as a separate feature.
5. Remove or replace the prototype modules after all accepted concepts are covered.

## Testing Strategy

### Numeric and Edge-Case Tests

- Reversed black/white edges produce equal block measurements.
- Uniform images produce finite saliency and valid palettes.
- Uniform saturated and neutral images both have near-zero estimated noise.
- Sorting preserves every color's population metadata.
- LAB centroids retain floating-point precision until final RGB conversion.
- Fixed seeds produce repeatable palettes.
- Every result contains finite coordinates and weights.

### Synthetic Classification Fixtures

- One-pixel and uniform images.
- Indexed 8-bit pixel art with a limited palette.
- Upscaled pixel art with nearest-neighbor blocks.
- Antialiased line art.
- Smooth gradients.
- High-frequency clean checkerboards.
- Clean and noise-injected photographic crops.
- Grayscale photographs with small saturated accents.

Synthetic tests should validate signals and invariants. They should not be the sole
basis for tuning classification quality.

### Validation Corpus

Create a small, redistributable labeled corpus covering each image class and ambiguous
examples. Keep licensing and provenance with each fixture.

Use the corpus to measure:

- Classification confusion matrix.
- Winning-score margin.
- Stability under resizing and compression.
- Palette repeatability.
- Palette coverage in LAB/HyAB distance.
- Runtime and peak memory.

Do not call heuristic scores calibrated confidence until validation demonstrates a
meaningful relationship between score and observed accuracy.

### Regression Tests

- Existing `extract_color_clusters()` results remain compatible within documented
  tolerances.
- `extract_unique_colors()` and HueForge luminance redistribution remain functional.
- Existing image analysis, quantization, CVD, watermark, conversion, and blend tests
  continue to pass.
- Importing `color_tools.image` behaves correctly with optional dependency subsets.

## Acceptance Criteria

- One supported image-profile implementation is shared by classification and automatic
  extraction.
- Classification returns a winning type, scores for every type, and explainable
  factors.
- Palette extraction returns structured colors with prevalence metadata that remains
  correct after sorting and suppression.
- Automatic extraction identifies the strategy it selected and why.
- Uniform, one-pixel, grayscale, noisy, indexed, and large images have tested behavior.
- No extraction path writes an intermediate file without explicit caller instruction.
- Large-image processing has documented sampling and memory bounds.
- Existing public image APIs remain backward compatible.
- Prototype-only algorithms are not exported as production APIs.

## Decisions Needed Before Implementation

1. Should `mixed` be a public classification type or only an internal low-margin
   fallback?
2. Should the first release include face weighting, or defer it until the non-subject
   attention path is established?
3. Should exact histogram extraction return fewer than `n_colors` when the image has
   fewer unique colors? The recommended answer is yes.
4. Should automatic extraction expose its selected configuration for replay? The
   recommended answer is yes through result metadata.
5. Should palette prevalence be exact for all images or sampled above a size threshold?
   The recommended answer is deterministic sampling with explicit result metadata.
6. Should `ImageProfile` live in `analysis.py` or a new `profiling.py` module? The
   recommended answer is a new module to keep clustering and profiling responsibilities
   separate.
7. Should classification and extraction be included in the existing `[image]` extra or
   split into a heavier `[vision]` extra? The recommended initial answer is `[image]`,
   because its current dependency set already includes the required libraries.

## Estimated Effort

- Phase 1, profile and classification: 2-3 days.
- Phase 2, consolidated extraction: 3-4 days.
- Phase 3, attention and automatic policy: 3-5 days.
- Phase 4, CLI and documentation: 1-2 days.
- Validation-corpus tuning: ongoing and separate from core implementation.

The smallest useful release is Phase 1 plus the Phase 2 `histogram`, `perceptual`, and
`pixel_art` strategies. Attention weighting and face-aware extraction can follow after
the foundational contracts are stable.

## Related Documents

- `docs/other/TODO.md`
- `docs/other/NEXTSTEPS.md`
- `docs/other/PALETTE_GENERATION.md`
- `docs/other/PALETTE_SYSTEM_ARCH_NOTES.md`
- `docs/other/HyAB_Implementation_Plan.md`

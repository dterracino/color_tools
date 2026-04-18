# HyAB Color Distance — Benefits & Implementation Plan

> **Status:** Planning  
> **Relates to:** `distance.py`, `image/analysis.py`, `image/basic.py`, CLI `image` command  
> **Dependencies:** None (pure Python stdlib; no new packages required)

---

## 1. What Is HyAB?

HyAB is a perceptual color-difference metric introduced by Saeedeh Abasi, Mohammad Amani Tehran, and Mark D. Fairchild (2020) in *"Distance metrics for very large color differences"* (Color Research & Application, DOI: 10.1002/col.22451). It was designed to outperform standard Euclidean CIELAB distance (CIE76) and even CIEDE2000 when color differences are **large** — the regime where those formulas are known to fail perceptually.

### 1.1 The Formula

Given two CIELAB colors `(L₁, a₁, b₁)` and `(L₂, a₂, b₂)`:

```text
d_HyAB = |L₁ − L₂|  +  √((a₁ − a₂)² + (b₁ − b₂)²)
         ──────────     ─────────────────────────────
         City-block       Euclidean in chroma plane
         (lightness)           (a*, b*)
```

The name **HyAB** stands for **Hy**brid (**Ab**solute + Euclidean) operating in **LAB** space. It treats:

- **Lightness** differences using **absolute (city-block / Manhattan)** distance
- **Chromaticity** (a\*, b\*) differences using **Euclidean** distance

This reflects the psychological *separability* of lightness from hue/chroma in human perception — people evaluate brightness changes and color shifts somewhat independently.

### 1.2 Optional L-Weight Extension (for k-means Quantization)

When used in k-means clustering, multiplying the lightness term by a weight factor (`l_weight`) improves palette balance:

```text
d_HyAB_weighted = l_weight × |L₁ − L₂|  +  √((a₁ − a₂)² + (b₁ − b₂)²)
```

- `l_weight = 1.0` → pure HyAB (original formula)  
- `l_weight = 2.0` → recommended for color quantization (better light/dark separation in palette)
- Values of 1.5–2.5 are the practical useful range

### 1.3 L-Median Centroid Update (k-means Enhancement)

In standard k-means, centroids are updated by taking the **mean** of all assigned pixels. An important variation for HyAB-based clustering uses:

- `centroid.L = median(cluster L values)` — robust against luminance outliers
- `centroid.a = mean(cluster a values)` — standard mean for chromaticity
- `centroid.b = mean(cluster b values)` — standard mean for chromaticity

The median for L makes the algorithm resistant to a few very bright or very dark pixels dragging the representative cluster color away from the perceptual center. This produces more visually balanced palettes, especially for images with strong highlights or shadows.

---

## 2. Why HyAB Outperforms Standard Metrics for Large Differences

### 2.1 Comparison Table

| Scenario | CIE76 (Euclidean LAB) | CIEDE2000 | HyAB |
| --- | --- | --- | --- |
| Small differences (< ΔE 5) | Good | Excellent | Good |
| Large differences (> ΔE 20) | Poor | Moderate | Excellent |
| Black → White transition | Underestimates | Moderate | Accurate |
| Deep saturated color shifts | Moderate | Good | Excellent |
| k-means clustering quality | Mediocre | N/A (too slow) | Excellent |
| Computational cost | ⚡ O(1) fast | 🐢 O(1) complex | ⚡ O(1) fast |

### 2.2 Key Advantages

**Faster than CIEDE2000**  
No trigonometric functions, no rotation term, no G-factor adjustment. Just `abs()` + `sqrt()`. This makes it practical as a k-means distance function where millions of distance calculations are performed per iteration.

**Better than CIE76 for image work**  
CIE76's uniform Euclidean structure over-blends lightness and chroma contributions, causing washed-out or tonally unbalanced palettes in color quantization. HyAB's separate treatment of lightness avoids this.

**Psychologically grounded**  
The separability of L\* from a\*/b\* matches how observers actually judge large color differences. The city-block distance for lightness better models the perceptual weight of light/dark steps, while Euclidean distance in the chroma plane handles hue and saturation changes.

**Better handling of extremes**  
Deep saturated colors (particularly blues), and transitions spanning the full lightness range, are more accurately ranked by HyAB than by CIE76 or even CIEDE2000.

### 2.3 When to Use HyAB vs. Other Metrics

| Use Case | Recommended Metric |
| --- | --- |
| "Just noticeable difference" (JND) color matching | CIEDE2000 |
| Industrial/textile color acceptance | CMC(2:1) |
| Nearest-neighbor search across a small palette | CIEDE2000 or CIE94 |
| Large-difference ranking (very different colors) | **HyAB** |
| Image color quantization (k-means palette) | **HyAB (l_weight=2.0)** |
| Dominant color extraction from images | **HyAB (l_weight=2.0, l_median=True)** |
| Fast approximate matching | CIE76 |

---

## 3. Where HyAB Fits in color_tools

### 3.1 `distance.py` — Core Metric Function

**New function: `delta_e_hyab()`**

This is the primary addition. HyAB becomes a first-class distance metric alongside CIE76, CIE94, CIEDE2000, and CMC. It requires zero new dependencies — pure Python using only `abs()` and `math.sqrt()`.

```python
def delta_e_hyab(
    lab1: tuple[float, float, float],
    lab2: tuple[float, float, float],
    l_weight: float = 1.0,
) -> float:
    """
    HyAB color difference — hybrid absolute/Euclidean in LAB space.

    d_HyAB = l_weight × |L₁ − L₂|  +  √((a₁ − a₂)² + (b₁ − b₂)²)

    Args:
        lab1, lab2: L*a*b* color tuples
        l_weight: Lightness emphasis factor (1.0 = pure HyAB, 2.0 = recommended for k-means)

    Returns:
        HyAB distance value (lower = more similar)
    """
```

The optional `l_weight` parameter defaults to `1.0` (pure HyAB) but enables the weighted variant used in quantization applications.

### 3.2 `image/analysis.py` — HyAB K-Means Clustering

**Enhanced `extract_color_clusters()` with HyAB distance option**

The existing k-means in `analysis.py` uses squared Euclidean distance in LAB space (CIE76-style). Upgrades:

- Add `distance_metric: str = "lab"` parameter — accepts `"lab"`, `"hyab"`, `"rgb"`
- Add `l_weight: float = 1.0` parameter — only used when `distance_metric="hyab"`
- Add `use_l_median: bool = False` parameter — when `True`, updates centroid L with median instead of mean

**New function: `quantize_image_hyab()`**

A dedicated convenience function for HyAB-based image quantization:

```python
def quantize_image_hyab(
    image_path: str,
    n_colors: int = 16,
    n_iter: int = 10,
    l_weight: float = 2.0,
    use_l_median: bool = True,
) -> PIL.Image.Image:
    """
    Quantize an image to n_colors using HyAB k-means clustering.
    
    Produces a perceptually balanced reduced-color image using the HyAB
    distance metric with recommended defaults for quantization quality.
    """
```

This mirrors the reference `run_hyab_kmeans()` from the pekkavaa/HyAB-kmeans repository but integrates cleanly with the existing color_tools architecture.

### 3.3 `image/basic.py` — Existing Quantization Function

The existing `quantize_image_to_palette()` uses PIL's built-in quantization engine. For custom k-means paths, expose an optional `distance_metric` parameter so callers can opt into HyAB-based clustering.

### 3.4 `palette.py` and `filament_palette.py` — Nearest Color Search

The `nearest_color()` and `nearest_filament()` methods currently use CIEDE2000. For scenarios where large color differences are involved (e.g., finding the "least wrong" filament match when no close match exists), offer HyAB as an alternative via a `metric` keyword argument.

---

## 4. Implementation Plan

### Phase 1 — Core Metric in `distance.py`

- [ ] Add `delta_e_hyab(lab1, lab2, l_weight=1.0)` function
- [ ] Write comprehensive docstring: formula, derivation, use cases, when to choose over CIE76/CIEDE2000
- [ ] Export from `__init__.py` alongside existing Delta E functions
- [ ] Add `"hyab"` as valid `--metric` option in the `color` and `filament` CLI commands
- [ ] Add unit tests with reference values computed analytically from the simple formula
- [ ] Update `CHANGELOG.md`

### Phase 2 — Enhanced K-Means in `image/analysis.py`

- [ ] Refactor `extract_color_clusters()` to accept `distance_metric`, `l_weight`, `use_l_median` parameters
- [ ] Add internal `_hyab_distance(lab1, lab2, l_weight)` helper (or import from `distance.py`)
- [ ] Apply HyAB distance in the assignment step when `distance_metric="hyab"`
- [ ] Apply median-L centroid update when `use_l_median=True`
- [ ] Add `quantize_image_hyab()` convenience function
- [ ] Export new function from `image/__init__.py`
- [ ] Add tests: HyAB k-means with `l_weight=1.0`, `l_weight=2.0`, and `use_l_median=True`
- [ ] Update `CHANGELOG.md`

### Phase 3 — CLI Integration for `image` command

- [ ] Add `--distance-metric {lab,hyab,rgb}` option to `color-tools image --extract-colors` (default: `lab`)
- [ ] Add `--hyab-l-weight FLOAT` option (default: `1.0`; docs note `2.0` as recommended for quantization)
- [ ] Add `--hyab-l-median` flag to enable median-L centroid updates
- [ ] Add `--quantize-hyab N` flag/option to run full HyAB pipeline, outputting quantized image
- [ ] Display the active distance metric in output headers
- [ ] Update `image/README.md` with new options and examples
- [ ] Update `CHANGELOG.md`

### Phase 4 — Palette/Filament Search Integration *(optional)*

- [ ] Add `metric` keyword to `Palette.nearest_color()` and `FilamentPalette.nearest_filament()`
- [ ] Accept `"hyab"` as a valid value alongside existing options
- [ ] Document when HyAB is preferable over CIEDE2000 for palette searches
- [ ] Update `CHANGELOG.md`

### Phase 5 — Version Bump

- [ ] Bump version `6.1.x → 6.2.0` (new feature, backward-compatible)
- [ ] Update `pyproject.toml`, `color_tools/__init__.py`, `README.md` version badge

---

## 5. Use Cases in color_tools

### 5.1 Dominant Color Extraction (Image → Palette)

**Current behavior:** `extract_color_clusters("photo.jpg", n_colors=8)` uses Euclidean LAB distance. Cluster centroids tend to bunch around mid-tones, with luminance extremes underrepresented.

**With HyAB:** `distance_metric="hyab", l_weight=2.0, use_l_median=True` produces a more visually balanced palette where darks and lights are better separated, and saturated colors are preserved without collapsing toward neutral gray. The improvement is most visible with 8–16 color palettes.

### 5.2 Image Color Quantization (Reduce to N Colors)

```python
from color_tools.image import quantize_image_hyab

result = quantize_image_hyab("photo.jpg", n_colors=16, l_weight=2.0, use_l_median=True)
result.save("quantized.png")
```

This produces results visually comparable to or better than PIL's `MAXCOVERAGE` algorithm, with perceptually uniform color separation and natural preservation of both highlights and shadows.

### 5.3 HueForge 3D Printing Workflow

The existing HueForge pipeline (`extract_color_clusters` → `redistribute_luminance`) benefits directly from HyAB clustering. HyAB's better lightness separation means extracted dominant colors are naturally more evenly distributed across the luminance axis, requiring less aggressive redistribution and producing smaller ΔE color shifts.

**Recommended pipeline:**

```python
from color_tools.image import extract_color_clusters, redistribute_luminance

# HyAB gives better luminance spread, reducing work for redistribute_luminance
clusters = extract_color_clusters(
    "model_reference.jpg",
    n_colors=10,
    distance_metric="hyab",
    l_weight=2.0,
    use_l_median=True,
)
colors = [c.centroid_rgb for c in clusters]
changes = redistribute_luminance(colors)  # Smaller deltas needed
```

### 5.4 Filament Color Matching (Large-Difference Regime)

When a target color has no nearby filament match — e.g., finding the "least wrong" filament for a vivid cyan target when only earth tones are in the library — HyAB ranks options more perceptually accurately than CIE76. CIEDE2000 is still ideal for near-match JND scenarios, but HyAB is better when the question is "which is the least bad option?"

```bash
# Find nearest filament using HyAB (better for dissimilar colors)
color-tools filament --nearest 255 0 128 --metric hyab
```

### 5.5 Palette Distance Comparisons

When comparing entire palettes (e.g., measuring how different CGA and EGA color sets are), HyAB provides a better aggregate distance measure than CIE76 because inter-palette differences are typically large.

### 5.6 Out-of-Gamut Color Mapping

When mapping an out-of-gamut LAB color back to the nearest in-gamut point, HyAB can be used as the distance criterion instead of Euclidean — giving a perceptually closer result for colors far outside sRGB gamut boundaries.

---

## 6. Implementation Notes

### 6.1 Pure Python — No New Dependencies

`delta_e_hyab()` needs only `abs()` and `math.sqrt()` — no numpy, no new imports. It fits within the library's zero-dependency philosophy.

The enhanced k-means in `analysis.py` uses the same pure Python loops as the current implementation. If/when numpy is available (via the `[image]` extra), the inner distance loop can be vectorized for performance.

### 6.2 Hash Integrity

Adding `delta_e_hyab` to `distance.py` does **not** require hash updates — it doesn't touch `constants.py`, `matrices.py`, or any data files.

### 6.3 Backward Compatibility

All new parameters have defaults that preserve current behavior:

- `extract_color_clusters()` default remains `distance_metric="lab"` — no output change
- New CLI flags are purely additive
- `delta_e_hyab` is a new export; nothing is renamed or removed

### 6.4 Performance Considerations

Per distance calculation, HyAB is roughly:

| Metric | Operations per comparison |
| --- | --- |
| CIE76 (Euclidean LAB) | 3 subtractions, 3 squares, 2 additions, 1 sqrt |
| HyAB | 3 subtractions, 1 abs, 2 squares, 2 additions, 1 sqrt |
| CIEDE2000 | ~40+ floating-point ops including trig |

HyAB is essentially the same cost as CIE76 but far cheaper than CIEDE2000, making it practical as a k-means inner loop metric at scale.

### 6.5 Versioning

Adding HyAB as a new distance metric and new image analysis capabilities constitutes a **minor version bump** following semantic versioning:

```text
6.2.0 - 6.3.0
```

---

## 7. Suggested CLI Examples (After Implementation)

```bash
# Find nearest filament using HyAB (better when colors are very different)
color-tools filament --nearest 255 0 128 --metric hyab

# Extract dominant colors using HyAB k-means
color-tools image --file photo.jpg --extract-colors --n-colors 8 \
    --distance-metric hyab --hyab-l-weight 2.0 --hyab-l-median

# Full HyAB quantization (reduce image to N colors, output quantized image)
color-tools image --file photo.jpg --quantize-hyab 16 \
    --hyab-l-weight 2.0 --hyab-l-median --output quantized.png

# HueForge workflow with HyAB clustering
color-tools image --file model_reference.jpg --extract-colors --n-colors 10 \
    --distance-metric hyab --hyab-l-weight 2.0 --hyab-l-median \
    --redistribute-luminance
```

---

## 8. Reference Implementation

The reference Python implementation by Pekka Väänänen demonstrates the algorithm with numpy and scikit-learn:

- **Article with visual comparisons:** <https://30fps.net/pages/hyab-kmeans/>
- **Reference code:** <https://github.com/pekkavaa/HyAB-kmeans/blob/main/hyab_kmeans.py>

Key differences between the reference and our planned implementation:

| Aspect | Reference (`hyab_kmeans.py`) | color_tools implementation |
| --- | --- | --- |
| Dependencies | numpy, sklearn, scikit-image, Pillow | Pure Python stdlib (+ optional Pillow) |
| k-means init | `sklearn.cluster.kmeans_plusplus` | Even-spacing (current) or k-means++ future |
| Distance calc | Vectorized numpy | Pure Python loops (vectorizable later) |
| API style | Script / standalone | Library function + CLI command |
| Integration | Standalone | Integrated with existing `ColorCluster` / `ColorChange` dataclasses |

---

## 9. Academic Reference

> Abasi, S., Tehran, M. A., & Fairchild, M. D. (2020).  
> *Distance metrics for very large color differences.*  
> Color Research & Application, 46(2), 356–372.  
> DOI: [10.1002/col.22451](https://doi.org/10.1002/col.22451)
>
> Abasi, S., Tehran, M. A., & Fairchild, M. D. (2020).  
> *Colour metrics for image edge detection.*  
> Color Research & Application.  
> DOI: [10.1002/col.22494](https://doi.org/10.1002/col.22494)

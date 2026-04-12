# Next Steps

Planned features and work items. This is a living document — items here are
candidates for future releases, not commitments.

---

## HyAB — Phase 4: `Palette` / `FilamentPalette` integration (deferred)

The `hyab` metric is already supported by:

- `delta_e_hyab()` in `distance.py`
- `--metric hyab` in all three CLI commands
- `Palette.nearest_color()` / `nearest_colors()` in `palette.py`
- `FilamentPalette.nearest_filament()` / `nearest_filaments()` in `filament_palette.py`

**Deferred**: Direct `hyab` support in palette *constructor-level* helpers (e.g. a dedicated
`nearest_color_hyab()` convenience wrapper, or `hyab_weight` parameter on `Palette`) was
considered but not implemented.  CIEDE2000 is the better choice for small colour differences in the
CSS/filament palette database use-case.  HyAB is most useful for image quantization, which is
covered by `quantize_image_hyab()`.

Re-evaluate if a real user need emerges.

---

## `image/basic.py` — `get_dominant_colors(count)` + refactor `get_dominant_color`

- Add `get_dominant_colors(image_path, count: int) -> list[tuple[int, int, int]]` that returns the
  top N most-frequent colors from an image (simple histogram approach, no clustering).
- Refactor `get_dominant_color` to delegate: `return get_dominant_colors(image_path, 1)[0]`.
- Export `get_dominant_colors` from `image/__init__.py`.

---

## `image/analysis.py` — Perceptual / focal-weighted color dominance

- Implement **focal point detection** (`get_focal_point(image_path) -> tuple[int, int]`) — returns
  the (x, y) pixel coordinate of the image's visual center of interest (sharpness-weighted centroid
  or saliency map approach).
- Implement **focal radius** (`get_focal_radius(image_path) -> float`) — the approximate radius (in
  pixels) around the focal point that covers the primary region of interest.
- Implement **focal circle** (`get_focal_circle(image_path) -> tuple[int, int, float]`) — convenience
  wrapper returning `(cx, cy, radius)` for easy downstream use.
- Implement **perceptually-weighted dominant colors** — when an image is primarily grayscale/neutral
  but contains vivid accent colors, those accents should surface as dominant. Strategy:
  - Score each color cluster by chroma (LCH C*) and focal proximity, not just pixel count.
  - A cluster that is highly chromatic AND concentrated near the focal point is amplified even if
    numerically small (e.g., a teal accent in a black-and-white portrait).
  - Expose as an optional `perceptual=True` parameter on an updated `extract_color_clusters`.
- Implement **saturation threshold filtering** for "color pop" style images — pixels below a
  configurable HSL/HSV saturation threshold are treated as grayscale background and excluded (or
  heavily down-weighted) before dominance scoring. This means a color-pop image where 90% of pixels
  are desaturated will still return the vivid "pop" colors as dominant rather than the gray mass.
  - `saturation_threshold: float = 0.0` parameter (0.0 = off, suggested default ~0.15–0.20 when
    enabled) on both `get_dominant_colors` and the perceptual cluster path.
  - Pairs naturally with the chroma/focal weighting above — together they handle the full spectrum
    from subtle accents to explicit color-pop photography.

---

## `image/analysis.py` — Canny edge detection utilities (TBD)

- `opencv-python>=4.8.0` would be added as part of a new optional extra (e.g. `[vision]`).
  Functions that require it will use conditional imports (`try: import cv2`) consistent with the
  project's existing pattern — the module stays importable without OpenCV, but Canny-based
  functions will raise `ImportError` with a helpful message if it's missing.
- Likely candidates (confirm scope before implementing):
  - **Edge-density focal estimation** — high edge-density regions are usually the sharpest / most
    in-focus area; fast focal point proxy without a full saliency model.
  - **Edge-aware color weighting** — colors near detected edges belong to object surfaces (not
    diffuse background fill); upweight them in dominance calculations.
  - **Sharpness / focus score** — count edge pixels in a bounding box to produce a focus quality
    metric useful for selecting the "best" frame from a burst.
  - **Region segmentation via edges** — use edges as region boundaries, then analyze dominant
    color per region. Significantly more complex (watershed/flood-fill on top of edge detection);
    defer until the simpler Canny utilities are proven out.

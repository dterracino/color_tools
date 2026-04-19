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

---

## `conversions.py` — HSB/HSV color space

HSB (Hue / Saturation / Brightness, also called HSV) is the dominant model in professional design
tools (Photoshop, Figma, Sketch, Illustrator).  The library already handles HSL and winHSL variants
but is missing this closely related space.

Python's `colorsys` module provides `rgb_to_hsv` / `hsv_to_rgb`, so the implementation is a thin
scaling wrapper — similar to how `rgb_to_hsl` wraps `colorsys.rgb_to_hls`.

**Planned API:**

| Function | Signature | Output range |
| --- | --- | --- |
| `rgb_to_hsb(rgb)` | `tuple[int,int,int]` → `tuple[float,float,float]` | H 0–360°, S 0–100%, B 0–100% |
| `hsb_to_rgb(hsb)` | `tuple[float,float,float]` → `tuple[int,int,int]` | R/G/B 0–255 |

- `rgb_to_hsb` / `hsb_to_rgb` are the primary names; `rgb_to_hsv` / `hsv_to_rgb` aliases are
  desirable for users who know the space as HSV.
- Export from `color_tools` top-level and add to `__all__`.
- Add `--to hsb` / `--from hsb` support to the `convert` CLI command.
- Unit tests with known reference values (red → H=0, S=100, B=100; green → H=120, S=100, B=100).

---

## Logging — Deeper Module Integration

The centralized logging infrastructure (`logging_config.py`) is in place as of v6.6.0, but only
four hot-path calls exist today.  The following areas would benefit from richer instrumentation:

### `conversions.py`

- `logger.debug` on entry to `rgb_to_lab`, `lab_to_rgb`, `rgb_to_xyz`, `xyz_to_rgb` — capture
  input/output pairs so a debug log tells the full conversion story.
- `logger.warning` when clamping occurs in `xyz_to_rgb` (out-of-gamut values silently clamp to
  0–255 today; a warning would surface unexpected gamut overflows).

### `distance.py`

- `logger.debug` on `delta_e_2000` / `delta_e_hyab` entry with both LAB inputs — makes it easy
  to reproduce a distance calculation from a log file alone.

### `cli_commands/` handlers

Each handler module (`color.py`, `filament.py`, `convert.py`, `name.py`, `cvd.py`) currently
has no logging.  Candidates:

- `logger.info` at the start of each handler with the resolved CLI args — instant audit trail.
- `logger.debug` after palette/filament loads confirming record count and data source.
- `logger.warning` on fallback conditions (e.g., no filaments matched filters, fell back to
  full search).
- `logger.error` when a handler catches and re-raises a user-facing error.

### `image/` module

- `logger.info` in `extract_color_clusters` with cluster count, image size, and elapsed time.
- `logger.debug` in `quantize_image_hyab` with iteration count and convergence delta.
- `logger.warning` when Pillow is not installed and the image module raises `ImportError` to
  a caller that hasn't explicitly opted in to `[image]`.

### `interactive_manager.py` / `interactive_wizard.py`

- `logger.debug` on wizard step transitions — useful for tracing unexpected exits.
- `logger.info` when the user selects a command and when the wizard hands off to the handler.

### `--console-log-level` CLI flag (deferred)

A companion `--console-log-level` global flag would let users independently control what
appears on the console vs. in the log file (e.g., `WARNING` on console, `DEBUG` in file).
Currently `console_level` defaults to `INFO` and can only be changed via the Python API.

---

## `conversions.py` — CMYK color space

CMYK (Cyan / Magenta / Yellow / Key-Black) is the standard model for print production and is
directly relevant to the project's physical-color focus (filaments, physical media).  No stdlib
support exists; math is straightforward.

**Formula** (RGB 0–255 → CMYK 0–100%):

```text
R' = R/255,  G' = G/255,  B' = B/255
K  = 1 − max(R', G', B')
C  = (1 − R' − K) / (1 − K)   [undefined when K=1, i.e. pure black → C=M=Y=0]
M  = (1 − G' − K) / (1 − K)
Y  = (1 − B' − K) / (1 − K)
```

**Planned API:**

| Function | Signature | Output range |
| --- | --- | --- |
| `rgb_to_cmyk(rgb)` | `tuple[int,int,int]` → `tuple[float,float,float,float]` | C/M/Y/K 0–100% |
| `cmyk_to_rgb(cmyk)` | `tuple[float,float,float,float]` → `tuple[int,int,int]` | R/G/B 0–255 |

- Note: this is the only planned 4-tuple conversion in the library.
- Export from `color_tools` top-level and add to `__all__`.
- Add `--to cmyk` / `--from cmyk` support to the `convert` CLI command.
- Unit tests: black → (0, 0, 0, 100); white → (0, 0, 0, 0); red → (0, 100, 100, 0).
- Caveat: this is *device-independent* CMYK (no ICC profile).  Document clearly so users don't
  expect print-accurate ink percentages — those require ICC profile transformation.

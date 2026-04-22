# CVD Correction Algorithm Bug

## Status

Deferred — identified April 2026, not yet fixed.

## Summary

The `correct_cvd()` function in `color_deficiency.py` produces incorrect results because it
applies the Fidaner daltonization correction matrices **directly to the input RGB**, instead of
applying them to the **error signal** (difference between original and simulated). This causes
neutral colors like white and gray to be tinted.

## Observed Symptom

When running `correct_cvd_image()` with `deficiency_type="protanopia"`:

- A white background `(255, 255, 255)` is transformed to cyan/teal instead of staying white.
- The correction is visually wrong for any color that has a significant red component.

## Root Cause

### What the code currently does

```python
# _apply_cvd_transform in color_deficiency.py (operation='correct')
matrix = get_correction_matrix(deficiency_type)  # e.g. PROTANOPIA_CORRECTION
r_new, g_new, b_new = multiply_matrix_vector(matrix, (r, g, b))
```

It multiplies the correction matrix directly by the original RGB.

### What the Fidaner daltonization algorithm actually specifies

The correction matrices are designed to operate on the **error signal**, not the original image:

1. `sim = simulate(original)`  — apply simulation matrix to get CVD appearance
2. `error = original − sim`  — compute the color difference
3. `shifted = correction_matrix × error`  — redistribute the error
4. `corrected = clamp(original + shifted)`  — add shifted error back

Applying the correction matrix to `original` instead of `error` is fundamentally wrong.

### Concrete example — white `(255, 255, 255)`

`PROTANOPIA_CORRECTION`:

```text
R_new = 0*R + 0*G + 0*B  →  0
G_new = 0.7*R + 1*G + 0*B  →  1.7  (clamped to 1.0)
B_new = 0.7*R + 0*G + 1*B  →  1.7  (clamped to 1.0)
```

Result: `(0, 255, 255)` = **cyan** instead of white.

With the correct algorithm:

- `sim(white) ≈ white` (white maps to white under any linear simulation matrix)
- `error = white − white = (0, 0, 0)`
- `shifted = matrix × (0, 0, 0) = (0, 0, 0)`
- `corrected = white + (0, 0, 0) = white` ✓

## Files to Change

| File | Change needed |
| --- | --- |
| `color_tools/color_deficiency.py` | `_apply_cvd_transform()` — implement the 4-step daltonization pipeline for `operation='correct'` |
| `color_tools/matrices.py` | No matrix values need to change; the matrices are correct for the error-signal use |
| `tests/test_color_deficiency.py` | Add regression test: `correct_cvd((255,255,255), 'protanopia') == (255,255,255)` and same for deuteranopia/tritanopia |

## Fix Sketch

```python
def _apply_cvd_transform(rgb, deficiency_type, operation='simulate'):
    r, g, b = [v / 255.0 for v in rgb]

    sim_matrix = get_simulation_matrix(deficiency_type)
    r_sim, g_sim, b_sim = multiply_matrix_vector(sim_matrix, (r, g, b))

    if operation == 'simulate':
        r_out, g_out, b_out = r_sim, g_sim, b_sim
    elif operation == 'correct':
        # Fidaner daltonization: apply correction to the error signal
        err = (r - r_sim, g - g_sim, b - b_sim)
        corr_matrix = get_correction_matrix(deficiency_type)
        dr, dg, db = multiply_matrix_vector(corr_matrix, err)
        r_out = r + dr
        g_out = g + dg
        b_out = b + db
    else:
        raise ValueError(f"Invalid operation: {operation}")

    def to_uint8(v):
        return max(0, min(255, round(v * 255.0)))

    return (to_uint8(r_out), to_uint8(g_out), to_uint8(b_out))
```

---

## Issue 2 — Alpha Channel: Transparent Backgrounds Become Black

### Status

Deferred — identified April 2026, not yet fixed.

### Observed Symptom

Running `make_cvd_demo.py` on a PNG with a transparent background produces an APNG
where all frames have a solid **black** background instead of transparency.

### Root Cause

`make_cvd_demo.py` calls `.convert("RGB")` on every frame:

```python
original  = Image.open(input_path).convert("RGB")
simulated = simulate_cvd_image(input_path, deficiency).convert("RGB")
corrected = correct_cvd_image(input_path, deficiency).convert("RGB")
```

Pillow's `.convert("RGB")` composites the alpha channel against **black** (the default
background color). Transparent pixels become `(0, 0, 0)`.

### Notes

- `transform_image()` in `image/basic.py` correctly preserves the alpha channel when
  `preserve_alpha=True` (the default). It returns an RGBA image for RGBA inputs.
  The library itself is fine; the issue is entirely in the demo script.
- The fix in `make_cvd_demo.py` is to keep the RGBA mode when the source image has alpha,
  and pass `format="PNG"` with RGBA frames directly to Pillow's APNG writer.
  Alternatively, composite against a white (or checkerboard) background before saving
  if a flat background is acceptable.

### Files to Change

| File | Change needed |
| --- | --- |
| `tooling/make_cvd_demo.py` | Detect source mode; if RGBA, skip `.convert("RGB")` and save APNG in RGBA mode (or composite against white) |

---

## Issue 3 — Performance: Per-Pixel Python Loop in `transform_image`

### Status

Deferred — identified April 2026, not yet fixed.

### Observed Symptom

Processing a typical photograph (e.g., 800×600 = 480 000 pixels) with `simulate_cvd_image`
or `correct_cvd_image` is noticeably slow — several seconds — even though numpy is
already a dependency.

### Root Cause

`transform_image()` in `image/basic.py` loads the image into a numpy array, but then
iterates every pixel individually in Python:

```python
for y in range(np_image.shape[0]):
    for x in range(np_image.shape[1]):
        r, g, b, a = np_image[y, x]
        new_r, new_g, new_b = transform_func((r, g, b))
        np_image[y, x] = [new_r, new_g, new_b, a]
```

For a 1920×1080 image that is **over 2 million Python function calls**. The numpy array
provides no speedup if every element is read/written individually via Python.

### Correct Approach

The CVD transforms are **linear matrix multiplications** on the normalized `[0, 1]` RGB
values. Numpy can apply a 3×3 matrix to an entire image in a single vectorized operation:

```python
# Reshape (H, W, 3) → (H*W, 3), apply matrix, reshape back
pixels = np_image[..., :3].astype(np.float32) / 255.0  # normalize
result = pixels @ matrix.T                               # broadcast dot-product
result = np.clip(result * 255.0, 0, 255).astype(np.uint8)
np_image[..., :3] = result
```

This replaces millions of Python calls with a single BLAS-backed matrix multiply — 
typically 100–1000× faster.

### Caveat

The `transform_func` parameter of `transform_image` is a generic per-pixel callable,
so it cannot be vectorized automatically. The CVD simulation/correction functions are
the common path and should bypass the generic loop, calling numpy directly with the
known matrix.

### Files to Change

| File | Change needed |
| --- | --- |
| `color_tools/image/basic.py` | Add a fast path in `transform_image` (or in `simulate_cvd_image` / `correct_cvd_image` directly) that applies the 3×3 matrix via numpy broadcasting instead of a Python pixel loop |
| `color_tools/matrices.py` | Expose matrices as `np.ndarray` (or convert on first use) to avoid per-call conversion overhead |

---

## References

- Fidaner, Ozgur, Onur Fidaner, and Mehmet A. Fidaner. "Analysis of Color Blindness."
  Stanford CS221 project, 2005.
  <http://scien.stanford.edu/pages/labsite/2005/psych221/projects/05/ofidaner/>
- Viénot, Brettel, and Mollon (1999). "Digital video colourmaps for checking the legibility
  of displays by dichromats."

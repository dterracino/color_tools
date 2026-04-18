"""
Photoshop-compatible blend mode operations for image layers.

This module provides all 27 standard Photoshop blend modes for compositing
two images together, using numpy for efficient per-pixel math and Pillow
for image I/O.

Requires: pip install color-match-tools[image]

Blend Mode Categories::

    Normal:      normal, dissolve
    Darken:      darken, multiply, color_burn, linear_burn, darker_color
    Lighten:     lighten, screen, color_dodge, linear_dodge, lighter_color
    Contrast:    overlay, soft_light, hard_light, vivid_light, linear_light,
                 pin_light, hard_mix
    Comparative: difference, exclusion, subtract, divide
    Component:   hue, saturation, color, luminosity

Primary API:
------------
For most users, the only two names you need are:

- ``blend_images(base_path, blend_path, mode, opacity, output_path)`` —
  loads two images, applies a blend mode, and returns a PIL ``Image``.
- ``BLEND_MODES`` — dict mapping every mode name to its numpy function,
  useful for listing or validating available modes.

The 27 individual mode functions (``multiply``, ``screen``, etc.) are also
exposed for advanced use. They operate directly on normalized float32 numpy
arrays with shape ``(H, W, 3)`` in the ``[0.0, 1.0]`` range. If you call
them directly you are responsible for array preparation, clipping, and
reconverting back to uint8. Use ``blend_images()`` unless you are managing
your own image pipeline.

Example:
--------
    >>> from color_tools.image import blend_images, BLEND_MODES
    >>>
    >>> # Blend two images using multiply mode at 80% opacity
    >>> result = blend_images("base.png", "layer.png", mode="multiply", opacity=0.8)
    >>> result.save("output.png")
    >>>
    >>> # List all available blend modes
    >>> print(sorted(BLEND_MODES.keys()))
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    import PIL.Image

try:
    import numpy as np  # type: ignore
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from PIL import Image  # type: ignore
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


def _check_dependencies() -> None:
    """Raise ImportError if Pillow or numpy are not available."""
    if not PILLOW_AVAILABLE:
        raise ImportError(
            "Pillow is required for image blending. "
            "Install with: pip install color-match-tools[image]"
        )
    if not NUMPY_AVAILABLE:
        raise ImportError(
            "numpy is required for image blending. "
            "Install with: pip install color-match-tools[image]"
        )


# ---------------------------------------------------------------------------
# Internal helpers (operate on float32 RGB arrays shaped H×W×3, range [0,1])
# ---------------------------------------------------------------------------

def _clip01(x: np.ndarray) -> np.ndarray:
    """Clip float array to [0, 1]."""
    return np.clip(x, 0.0, 1.0)


def _lum(c: np.ndarray) -> np.ndarray:
    """
    BT.601 luminance from an RGB float array (shape: H×W×3).

    Coefficients: R=0.299, G=0.587, B=0.114 — correct for RGB channel order.
    """
    return 0.299 * c[..., 0] + 0.587 * c[..., 1] + 0.114 * c[..., 2]


def _set_lum(c: np.ndarray, lum_target: np.ndarray) -> np.ndarray:
    """Return c with luminance replaced by lum_target, clipped to [0, 1]."""
    delta = lum_target - _lum(c)
    return _clip01(c + np.stack([delta, delta, delta], axis=-1))


def _sat(c: np.ndarray) -> np.ndarray:
    """Per-pixel saturation: max channel minus min channel (shape: H×W)."""
    return np.max(c, axis=-1) - np.min(c, axis=-1)


def _set_sat(c: np.ndarray, s: np.ndarray) -> np.ndarray:
    """
    Set per-pixel saturation to s while preserving hue order.

    Fully vectorized: sorts channels ascending per pixel, scales to the new
    saturation value, then scatters back to original channel positions.

    Args:
        c: RGB float array, shape (H, W, 3), values in [0, 1].
        s: Target saturation per pixel, shape (H, W), values in [0, 1].
    """
    sorted_idx = np.argsort(c, axis=-1)                    # (H, W, 3)
    c_sorted = np.take_along_axis(c, sorted_idx, axis=-1)  # ascending per pixel

    c_min = c_sorted[..., 0]  # (H, W)
    c_mid = c_sorted[..., 1]
    c_max = c_sorted[..., 2]
    span = c_max - c_min
    has_span = span > 0

    # Avoid division by zero in pixels where all channels are equal
    safe_span = np.where(has_span, span, 1.0)

    mid_new = np.where(has_span, (c_mid - c_min) / safe_span * s, 0.0)
    max_new = np.where(has_span, s, 0.0)

    result_sorted = np.stack([np.zeros_like(s), mid_new, max_new], axis=-1)
    out = np.zeros_like(c)
    np.put_along_axis(out, sorted_idx, result_sorted, axis=-1)
    return _clip01(out)


# ---------------------------------------------------------------------------
# Blend mode functions
#
# All accept float32 numpy arrays shaped (H, W, 3) with values in [0, 1].
# Alpha channels are separated before these calls — do NOT pass 4-channel arrays.
# a = base layer, b = blend (top) layer.
# ---------------------------------------------------------------------------

def normal(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Normal: blend layer fully replaces base."""
    return b


def dissolve(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Dissolve: random 50/50 pixel selection from base or blend.

    For opacity-controlled dissolve, use blend_images() which uses the
    opacity value as the random selection threshold.
    """
    mask = np.random.rand(*a.shape[:2], 1) < 0.5
    return np.where(mask, b, a)


def darken(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Darken: keep the darker value per channel."""
    return np.minimum(a, b)


def multiply(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Multiply: darkens by multiplying both layers (like overlapping transparencies)."""
    return a * b


def color_burn(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Color Burn: darkens base by increasing contrast toward blend color."""
    return 1.0 - _clip01((1.0 - a) / (b + 1e-7))


def linear_burn(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Linear Burn: darkens base by decreasing brightness."""
    return _clip01(a + b - 1.0)


def darker_color(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Darker Color: keep whichever full pixel has lower overall luminance."""
    mask = _lum(a) <= _lum(b)
    return np.where(mask[..., np.newaxis], a, b)


def lighten(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Lighten: keep the lighter value per channel."""
    return np.maximum(a, b)


def screen(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Screen: lightens by inverting, multiplying, then inverting again."""
    return 1.0 - (1.0 - a) * (1.0 - b)


def color_dodge(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Color Dodge: lightens base by decreasing contrast toward blend color."""
    return _clip01(a / (1.0 - b + 1e-7))


def linear_dodge(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Linear Dodge (Add): lightens base by adding blend brightness."""
    return _clip01(a + b)


def lighter_color(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Lighter Color: keep whichever full pixel has higher overall luminance."""
    mask = _lum(a) >= _lum(b)
    return np.where(mask[..., np.newaxis], a, b)


def overlay(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Overlay: multiply where base is dark, screen where base is light."""
    return np.where(a < 0.5, 2.0 * a * b, 1.0 - 2.0 * (1.0 - a) * (1.0 - b))


def soft_light(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Soft Light: subtle lighten/darken using the W3C/Photoshop piecewise formula.

    Matches Photoshop output (not the simpler Pegtop approximation):

        if b <= 0.5:  a - (1 - 2b) × a × (1 - a)
        else:         a + (2b - 1) × (D(a) - a)

            where D(a) = ((16a - 12)a + 4)a   if a <= 0.25
                       = √a                    if a >  0.25
    """
    d = np.where(
        a <= 0.25,
        ((16.0 * a - 12.0) * a + 4.0) * a,
        np.sqrt(np.maximum(a, 0.0)),
    )
    return np.where(
        b <= 0.5,
        a - (1.0 - 2.0 * b) * a * (1.0 - a),
        a + (2.0 * b - 1.0) * (d - a),
    )


def hard_light(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Hard Light: overlay with base and blend roles swapped."""
    return np.where(b < 0.5, 2.0 * a * b, 1.0 - 2.0 * (1.0 - a) * (1.0 - b))


def vivid_light(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Vivid Light: color burn where blend is dark, color dodge where blend is light."""
    return np.where(
        b < 0.5,
        1.0 - _clip01((1.0 - a) / (2.0 * b + 1e-7)),
        _clip01(a / (2.0 * (1.0 - b) + 1e-7)),
    )


def linear_light(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Linear Light: linear burn or linear dodge depending on blend brightness."""
    return _clip01(a + 2.0 * b - 1.0)


def pin_light(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Pin Light: darken or lighten depending on blend layer value."""
    return np.where(b < 0.5, np.minimum(a, 2.0 * b), np.maximum(a, 2.0 * b - 1.0))


def hard_mix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Hard Mix: extreme posterization — each channel becomes 0 or 1."""
    return np.where(a + b < 1.0, 0.0, 1.0)


def difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Difference: absolute difference between layers."""
    return np.abs(a - b)


def exclusion(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Exclusion: lower-contrast alternative to Difference."""
    return a + b - 2.0 * a * b


def subtract(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Subtract: subtracts blend from base, clamped to black."""
    return _clip01(a - b)


def divide(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Divide: divides base by blend, lightening the result."""
    return _clip01(a / (b + 1e-7))


def hue(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Hue: hue from blend layer, saturation and luminosity from base."""
    return _set_lum(_set_sat(b, _sat(a)), _lum(a))


def saturation(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Saturation: saturation from blend layer, hue and luminosity from base."""
    return _set_lum(_set_sat(a, _sat(b)), _lum(a))


def color(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Color: hue and saturation from blend layer, luminosity from base."""
    return _set_lum(b, _lum(a))


def luminosity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Luminosity: luminosity from blend layer, hue and saturation from base."""
    return _set_lum(a, _lum(b))


# ---------------------------------------------------------------------------
# Mode registry
# ---------------------------------------------------------------------------

BLEND_MODES: dict[str, Callable[..., np.ndarray]] = {
    "normal":        normal,
    "dissolve":      dissolve,
    "darken":        darken,
    "multiply":      multiply,
    "color_burn":    color_burn,
    "linear_burn":   linear_burn,
    "darker_color":  darker_color,
    "lighten":       lighten,
    "screen":        screen,
    "color_dodge":   color_dodge,
    "linear_dodge":  linear_dodge,
    "lighter_color": lighter_color,
    "overlay":       overlay,
    "soft_light":    soft_light,
    "hard_light":    hard_light,
    "vivid_light":   vivid_light,
    "linear_light":  linear_light,
    "pin_light":     pin_light,
    "hard_mix":      hard_mix,
    "difference":    difference,
    "exclusion":     exclusion,
    "subtract":      subtract,
    "divide":        divide,
    "hue":           hue,
    "saturation":    saturation,
    "color":         color,
    "luminosity":    luminosity,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def blend_images(
    base_path: str | Path,
    blend_path: str | Path,
    mode: str = "normal",
    opacity: float = 1.0,
    output_path: str | Path | None = None,
) -> PIL.Image.Image:
    """
    Blend two images using a Photoshop-compatible blend mode.

    Both images are converted to RGBA before blending. The blend mode is
    applied only to the RGB channels; alpha is composited separately using
    standard src-over with opacity. The blend layer is resized to match the
    base image if their sizes differ.

    Args:
        base_path:   Path to the base (background) image.
        blend_path:  Path to the blend (top) layer image.
        mode:        Blend mode name. See BLEND_MODES for all options.
        opacity:     Blend layer opacity in [0.0, 1.0]. Default 1.0.
        output_path: If provided, the result is saved to this path.

    Returns:
        Composited PIL Image in RGBA mode.

    Raises:
        ValueError:  If mode is not in BLEND_MODES or opacity is out of range.
        ImportError: If Pillow or numpy are not installed.

    Example:
        >>> result = blend_images("base.png", "layer.png", mode="multiply", opacity=0.8)
        >>> result.save("output.png")
    """
    _check_dependencies()

    if mode not in BLEND_MODES:
        raise ValueError(
            f"Unsupported blend mode '{mode}'. "
            f"Available: {sorted(BLEND_MODES.keys())}"
        )
    if not 0.0 <= opacity <= 1.0:
        raise ValueError(f"opacity must be in [0.0, 1.0], got {opacity}")

    # Load both images as RGBA float32 in [0, 1]
    base_img = Image.open(base_path).convert("RGBA")
    blend_img = Image.open(blend_path).convert("RGBA")

    # Resize blend layer to match base if needed
    if blend_img.size != base_img.size:
        blend_img = blend_img.resize(base_img.size, Image.Resampling.LANCZOS)

    base_arr  = np.asarray(base_img,  dtype=np.float32) / 255.0  # (H, W, 4)
    blend_arr = np.asarray(blend_img, dtype=np.float32) / 255.0  # (H, W, 4)

    base_rgb  = base_arr[..., :3]
    base_alpha  = base_arr[..., 3:4]
    blend_rgb = blend_arr[..., :3]
    blend_alpha = blend_arr[..., 3:4]

    # Dissolve uses opacity as the random selection threshold
    if mode == "dissolve":
        mask = np.random.rand(*base_rgb.shape[:2], 1) < opacity
        out_rgb = np.where(mask, blend_rgb, base_rgb)
    else:
        blended_rgb = BLEND_MODES[mode](base_rgb, blend_rgb)
        # Apply opacity: lerp between base and blended result
        out_rgb = base_rgb * (1.0 - opacity) + blended_rgb * opacity

    # Src-over alpha compositing with opacity applied to blend layer
    out_alpha = blend_alpha * opacity + base_alpha * (1.0 - blend_alpha * opacity)

    out_arr = np.concatenate([_clip01(out_rgb), _clip01(out_alpha)], axis=-1)
    result = Image.fromarray((out_arr * 255.0).astype(np.uint8), mode="RGBA")

    if output_path is not None:
        result.save(output_path)

    return result
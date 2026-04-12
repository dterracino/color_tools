"""
Photoshop 27 Blend Modes in Python
Requires: pip install opencv-python pillow numpy
"""

import cv2
import numpy as np
import sys

# ---------------------------
# Helper functions
# ---------------------------

def clip01(x):
    """Clip values to [0, 1] range."""
    return np.clip(x, 0, 1)

def lum(c):
    """Calculate luminance."""
    return 0.3 * c[..., 2] + 0.59 * c[..., 1] + 0.11 * c[..., 0]

def set_lum(c, l):
    """Set luminance while preserving color."""
    d = l - lum(c)
    c = c + np.stack([d, d, d], axis=-1)
    return clip01(c)

def sat(c):
    """Calculate saturation."""
    return np.max(c, axis=-1) - np.min(c, axis=-1)

def set_sat(c, s):
    """Set saturation while preserving luminance."""
    out = np.zeros_like(c)
    for i in range(c.shape[0]):
        for j in range(c.shape[1]):
            min_c = np.min(c[i, j])
            mid_c = np.median(c[i, j])
            max_c = np.max(c[i, j])
            if max_c > min_c:
                scale = s[i, j] / (max_c - min_c)
                out[i, j] = (c[i, j] - min_c) * scale + min_c
            else:
                out[i, j] = c[i, j]
    return clip01(out)

# ---------------------------
# Blend mode formulas
# ---------------------------

def normal(a, b): return b
def dissolve(a, b): return np.where(np.random.rand(*a.shape) < 0.5, a, b)
def darken(a, b): return np.minimum(a, b)
def multiply(a, b): return a * b
def color_burn(a, b): return 1 - clip01((1 - a) / (b + 1e-6))
def linear_burn(a, b): return clip01(a + b - 1)
def darker_color(a, b): return np.where(lum(a[..., :3]) < lum(b[..., :3]), a, b)
def lighten(a, b): return np.maximum(a, b)
def screen(a, b): return 1 - (1 - a) * (1 - b)
def color_dodge(a, b): return clip01(a / (1 - b + 1e-6))
def linear_dodge(a, b): return clip01(a + b)
def lighter_color(a, b): return np.where(lum(a[..., :3]) > lum(b[..., :3]), a, b)

def overlay(a, b):
    mask = a < 0.5
    return np.where(mask, 2 * a * b, 1 - 2 * (1 - a) * (1 - b))

def soft_light(a, b):
    return (1 - 2 * b) * (a ** 2) + 2 * b * a

def hard_light(a, b):
    mask = b < 0.5
    return np.where(mask, 2 * a * b, 1 - 2 * (1 - a) * (1 - b))

def vivid_light(a, b):
    return np.where(b < 0.5,
                    1 - clip01((1 - a) / (2 * b + 1e-6)),
                    clip01(a / (2 * (1 - b) + 1e-6)))

def linear_light(a, b):
    return clip01(a + 2 * b - 1)

def pin_light(a, b):
    return np.where(b < 0.5, np.minimum(a, 2 * b), np.maximum(a, 2 * b - 1))

def hard_mix(a, b):
    return np.where(a + b < 1, 0, 1)

def difference(a, b): return np.abs(a - b)
def exclusion(a, b): return a + b - 2 * a * b
def subtract(a, b): return clip01(a - b)
def divide(a, b): return clip01(a / (b + 1e-6))

def hue(a, b):
    return set_lum(set_sat(b, sat(a)), lum(a))

def saturation(a, b):
    return set_lum(set_sat(a, sat(b)), lum(a))

def color(a, b):
    return set_lum(b, lum(a))

def luminosity(a, b):
    return set_lum(a, lum(b))

# ---------------------------
# Mode dictionary
# ---------------------------

BLEND_MODES = {
    "normal": normal,
    "dissolve": dissolve,
    "darken": darken,
    "multiply": multiply,
    "color_burn": color_burn,
    "linear_burn": linear_burn,
    "darker_color": darker_color,
    "lighten": lighten,
    "screen": screen,
    "color_dodge": color_dodge,
    "linear_dodge": linear_dodge,
    "lighter_color": lighter_color,
    "overlay": overlay,
    "soft_light": soft_light,
    "hard_light": hard_light,
    "vivid_light": vivid_light,
    "linear_light": linear_light,
    "pin_light": pin_light,
    "hard_mix": hard_mix,
    "difference": difference,
    "exclusion": exclusion,
    "subtract": subtract,
    "divide": divide,
    "hue": hue,
    "saturation": saturation,
    "color": color,
    "luminosity": luminosity
}

# ---------------------------
# Main blending function
# ---------------------------

def blend_images(img1_path, img2_path, mode="overlay", output_path="blended.png"):
    if mode not in BLEND_MODES:
        raise ValueError(f"Unsupported mode '{mode}'. Supported: {list(BLEND_MODES.keys())}")

    img1 = cv2.imread(img1_path, cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0
    img2 = cv2.imread(img2_path, cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0

    if img1.shape != img2.shape:
        img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

    blended = BLEND_MODES[mode](img1, img2)
    cv2.imwrite(output_path, (clip01(blended) * 255).astype(np.uint8))
    print(f"✅ Saved '{output_path}' using mode '{mode}'.")

# ---------------------------
# CLI usage
# ---------------------------

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(f"Usage: python {sys.argv[0]} <image1> <image2> <mode> [output_path]")
        print(f"Available modes: {list(BLEND_MODES.keys())}")
        sys.exit(1)

    img1_path = sys.argv[1]
    img2_path = sys.argv[2]
    mode = sys.argv[3]
    output_path = sys.argv[4] if len(sys.argv) > 4 else f"blended_{mode}.png"

    try:
        blend_images(img1_path, img2_path, mode, output_path)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
"""
Gamut checking and mapping for sRGB color space.

Not all LAB colors can be represented in sRGB! Some theoretical colors
that humans can perceive simply can't be displayed on a monitor. This
module helps you:
1. Check if a LAB color is displayable (in gamut)
2. Find the nearest displayable color if it's not

The key insight: sRGB is a cube (R, G, B all 0-255), but LAB describes
a much larger volume. The intersection is the "sRGB gamut."
"""

from __future__ import annotations
import math
from typing import Tuple, cast

from .constants import ColorConstants
from .conversions import lab_to_rgb, lab_to_lch, lch_to_lab, lab_to_xyz, xyz_to_rgb_float
from .config import ColorConfig, get_config


def _validate_lab(lab: object) -> None:
    if not isinstance(lab, (tuple, list)):
        raise ValueError("LAB must contain three finite numeric components")
    components = cast(tuple[object, ...] | list[object], lab)
    if len(components) != 3:
        raise ValueError("LAB must contain three finite numeric components")
    for component in components:
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise ValueError("LAB must contain three finite numeric components")
        try:
            finite = math.isfinite(component)
        except OverflowError as error:
            raise ValueError("LAB components exceed the supported numeric range") from error
        if not finite:
            raise ValueError("LAB must contain three finite numeric components")


def is_in_srgb_gamut(lab: Tuple[float, float, float], tolerance: float | None = None) -> bool:
    """
    Check if a LAB color can be represented in sRGB without clipping.
    
    This is the fundamental question of color reproduction: "Can my monitor
    actually show this color, or will it have to fake it by clamping?"
    
    **How it works:** Convert LAB → RGB *without* clamping. If all RGB
    components are naturally in the 0-255 range (with a small tolerance),
    the color is in gamut!
    
    **Why tolerance?** Floating point math is imprecise. A value of
    255.0000001 should be considered "in gamut" even though it's technically
    over 255.
    
    **Examples of out-of-gamut colors:**
    - Super saturated colors at mid-lightness (like "laser red")
    - Colors that would need negative RGB values
    - Colors that would need RGB values > 255
    
    Args:
        lab: L*a*b* color tuple
        tolerance: How close to 0/255 boundaries before considering out-of-gamut.
                   If None, uses the current context value (default 0.01).
    
    Returns:
        True if the color can be represented in sRGB, False if it would clip

    Raises:
        ValueError: If LAB is malformed, non-finite, or exceeds the supported
            conversion range, or tolerance is negative/non-finite.
        TypeError: If tolerance is not numeric or is a boolean.
    
    Example:
        >>> is_in_srgb_gamut((50, 0, 0))  # Mid gray
        True
        >>> is_in_srgb_gamut((50, 150, 100))  # Super saturated - impossible!
        False
    """
    if tolerance is None:
        tolerance = get_config().gamut_tolerance
    ColorConfig(gamut_tolerance=tolerance)
    _validate_lab(lab)
    try:
        rgb = xyz_to_rgb_float(lab_to_xyz(lab))
    except OverflowError as error:
        raise ValueError("LAB conversion exceeds the supported numeric range") from error
    min_val = ColorConstants.RGB_MIN - tolerance
    max_val = ColorConstants.RGB_MAX + tolerance
    return all(math.isfinite(channel) and min_val <= channel <= max_val for channel in rgb)


def find_nearest_in_gamut(lab: Tuple[float, float, float], 
                          max_iterations: int | None = None) -> Tuple[float, float, float]:
    """
    Reduce chroma to find an in-gamut LAB color at constant lightness and hue.

    This is not a globally nearest-color optimization. Invalid coordinates or
    lightness with no feasible neutral endpoint raise ValueError.
    
    **The Strategy:** When a color is out of gamut, it's usually because it's
    too *saturated* (high chroma). So we convert to LCH, then use binary search
    to find the maximum chroma that still fits in sRGB. This preserves:
    - ✅ Lightness (L) - stays the same
    - ✅ Hue (h) - stays the same  
    - ❌ Chroma (C) - reduced until it fits
    
    **Why this works:** Think of it like turning down the "saturation" slider
    in Photoshop until the color becomes displayable. The hue doesn't change
    (red stays red), it just becomes less "punchy."
    
    **Binary search magic:** Instead of trying every possible chroma value
    (0.0, 0.01, 0.02, ...), we do a binary search. Each iteration cuts the
    search space in half. After 20 iterations, we've checked 2^20 = 1 million
    possible values! 🚀
    
    Args:
        lab: Potentially out-of-gamut L*a*b* color
        max_iterations: Maximum desaturation steps (binary search iterations).
                       If None, uses current context value (default 20).
    
    Returns:
        Desaturated in-gamut L*a*b* at the same LCH lightness and hue.

    Raises:
        ValueError: If LAB is invalid, iterations is less than one, or no
            in-gamut neutral exists at the requested lightness.
        TypeError: If iterations is not an integer or is a boolean.
    
    Example:
        >>> # Super saturated red - can't be displayed!
        >>> out_of_gamut = (50, 100, 80)
        >>> displayable = find_nearest_in_gamut(out_of_gamut)
        >>> # Result: same lightness and hue, but less saturated
        >>> is_in_srgb_gamut(displayable)
        True
    """
    config = get_config()
    if max_iterations is None:
        max_iterations = config.gamut_max_iterations
    ColorConfig(gamut_max_iterations=max_iterations)
        
    # If already in gamut, we're done!
    if is_in_srgb_gamut(lab, tolerance=config.gamut_tolerance):
        return lab
    
    # Convert to LCH for easier chroma manipulation
    # LCH = cylindrical LAB (Lightness, Chroma, Hue)
    L, C, h = lab_to_lch(lab)
    neutral = lch_to_lab((L, 0.0, h))
    if not is_in_srgb_gamut(neutral, tolerance=config.gamut_tolerance):
        raise ValueError("No in-gamut neutral exists at the requested LAB lightness")
    
    # Binary search for the maximum chroma that fits in gamut
    # Start with search bounds: [0, current_chroma]
    min_c = ColorConstants.NORMALIZED_MIN  # Minimum possible chroma (gray)
    max_c = C  # Maximum possible chroma (current, which we know is too high)
    
    # Binary search: keep splitting the range in half
    for _ in range(max_iterations):
        # Try the midpoint
        test_c = (min_c + max_c) / 2.0
        if test_c == min_c or test_c == max_c:
            break
        test_lab = lch_to_lab((L, test_c, h))
        
        if is_in_srgb_gamut(test_lab, tolerance=config.gamut_tolerance):
            # This chroma works! Can we go higher?
            min_c = test_c  # New lower bound
        else:
            # Too saturated, need to reduce
            max_c = test_c  # New upper bound
    
    # After max_iterations, min_c is the highest in-gamut chroma
    return lch_to_lab((L, min_c, h))


def clamp_to_gamut(lab: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    Convert LAB to RGB and back to LAB (with clamping).
    
    This is the "quick and dirty" approach to gamut mapping. Instead of
    carefully desaturating, we just let lab_to_rgb() clamp the RGB values
    to 0-255, then convert back to LAB to see what we got.
    
    **Pros:** Fast!
    
    **Cons:** Can change hue (not just chroma). A pure red might become
    a slightly orange-red after clamping.
    
    For most applications, `find_nearest_in_gamut()` is better because it
    preserves hue. This function exists for when you need speed over accuracy.
    
    Args:
        lab: Any L*a*b* color (in-gamut or not)
    
    Returns:
        In-gamut L*a*b* color (clamped)
    """
    from .conversions import rgb_to_lab
    _validate_lab(lab)
    # Convert to RGB (with clamping), then back to LAB
    rgb = lab_to_rgb(lab, clamp=True)
    return rgb_to_lab(rgb)
"""
Color space conversion functions.

Handles conversions between:
- sRGB (0-255) ↔ XYZ ↔ LAB ↔ LCH
- sRGB ↔ HSL (various formats)
- Gamma correction (sRGB companding)

All conversions use D65 illuminant and proper color science math.
"""

from __future__ import annotations
from typing import Tuple
import math
import colorsys

from color_tools.constants import ColorConstants


# ============================================================================
# Forward Conversions (RGB → LAB)
# ============================================================================

def srgb_to_linear(c: float) -> float:
    """
    Convert sRGB value to linear RGB (gamma correction removal).
    
    sRGB uses a piecewise function to approximate gamma 2.2 encoding.
    This function reverses that to get linear light values.
    """
    if c <= ColorConstants.SRGB_GAMMA_THRESHOLD:
        return c / ColorConstants.SRGB_GAMMA_LINEAR_SCALE
    return ((c + ColorConstants.SRGB_GAMMA_OFFSET) / ColorConstants.SRGB_GAMMA_DIVISOR) ** ColorConstants.SRGB_GAMMA_POWER


def rgb_to_xyz(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """
    Convert sRGB (0-255) to CIE XYZ using D65 illuminant.
    
    XYZ is a device-independent color space that represents how the human
    eye responds to light. It's the bridge between RGB and LAB.
    """
    # Normalize to 0-1 range
    r, g, b = [v / ColorConstants.RGB_MAX for v in rgb]
    
    # Remove gamma correction (linearize)
    r_lin, g_lin, b_lin = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    
    # Matrix multiplication using sRGB → XYZ coefficients
    X = r_lin * ColorConstants.SRGB_TO_XYZ_R[0] + g_lin * ColorConstants.SRGB_TO_XYZ_R[1] + b_lin * ColorConstants.SRGB_TO_XYZ_R[2]
    Y = r_lin * ColorConstants.SRGB_TO_XYZ_G[0] + g_lin * ColorConstants.SRGB_TO_XYZ_G[1] + b_lin * ColorConstants.SRGB_TO_XYZ_G[2]
    Z = r_lin * ColorConstants.SRGB_TO_XYZ_B[0] + g_lin * ColorConstants.SRGB_TO_XYZ_B[1] + b_lin * ColorConstants.SRGB_TO_XYZ_B[2]
    
    # Scale to 0-100 range (standard for XYZ)
    return (X * ColorConstants.XYZ_SCALE_FACTOR, Y * ColorConstants.XYZ_SCALE_FACTOR, Z * ColorConstants.XYZ_SCALE_FACTOR)


def _f_lab(t: float) -> float:
    """
    LAB conversion helper function.
    
    This piecewise function handles the nonlinear transformation from XYZ to LAB.
    The cube root section makes LAB perceptually uniform.
    """
    if t > ColorConstants.LAB_DELTA_CUBED:
        return t ** (1.0 / 3.0)
    return t / ColorConstants.LAB_F_SCALE + ColorConstants.LAB_F_OFFSET


def xyz_to_lab(xyz: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    Convert CIE XYZ to L*a*b* using D65 illuminant.
    
    LAB is perceptually uniform - equal distances in LAB space correspond
    to roughly equal perceived color differences. Perfect for color matching!
    
    - L*: Lightness (0=black, 100=white)
    - a*: Green←→Red axis
    - b*: Blue←→Yellow axis
    """
    X, Y, Z = xyz
    
    # Normalize by D65 white point and apply nonlinear transformation
    fx = _f_lab(X / ColorConstants.D65_WHITE_X)
    fy = _f_lab(Y / ColorConstants.D65_WHITE_Y)
    fz = _f_lab(Z / ColorConstants.D65_WHITE_Z)
    
    # Calculate LAB components
    L = ColorConstants.LAB_KAPPA * fy - ColorConstants.LAB_OFFSET
    a = ColorConstants.LAB_A_SCALE * (fx - fy)
    b = ColorConstants.LAB_B_SCALE * (fy - fz)
    return (L, a, b)


def rgb_to_lab(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """
    Convert sRGB (0-255) to CIE L*a*b*.
    
    This is the main conversion you'll use for color matching!
    Goes RGB → XYZ → LAB in one shot.
    """
    return xyz_to_lab(rgb_to_xyz(rgb))


# ============================================================================
# Reverse Conversions (LAB → RGB)
# ============================================================================

def _f_lab_inverse(t: float) -> float:
    """
    Inverse of the f function used in LAB conversion.
    
    This reverses the nonlinear transformation to go from LAB back to XYZ.
    """
    if t > ColorConstants.LAB_DELTA:
        return t ** 3
    return ColorConstants.LAB_F_SCALE * (t - ColorConstants.LAB_F_OFFSET)


def lab_to_xyz(lab: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    Convert CIE L*a*b* to XYZ using D65 illuminant.
    
    Reverses the LAB → XYZ transformation.
    """
    L, a, b = lab
    
    # Calculate intermediate values
    fy = (L + ColorConstants.LAB_OFFSET) / ColorConstants.LAB_KAPPA
    fx = a / ColorConstants.LAB_A_SCALE + fy
    fz = fy - b / ColorConstants.LAB_B_SCALE
    
    # Apply inverse transformation and scale by D65 white point
    X = ColorConstants.D65_WHITE_X * _f_lab_inverse(fx)
    Y = ColorConstants.D65_WHITE_Y * _f_lab_inverse(fy)
    Z = ColorConstants.D65_WHITE_Z * _f_lab_inverse(fz)
    
    return (X, Y, Z)


def linear_to_srgb(c: float) -> float:
    """
    Convert linear RGB to sRGB (inverse gamma correction).
    
    This applies the sRGB gamma curve to convert from linear light
    back to the nonlinear sRGB encoding.
    """
    if c <= ColorConstants.SRGB_INV_GAMMA_THRESHOLD:
        return ColorConstants.SRGB_GAMMA_LINEAR_SCALE * c
    return ColorConstants.SRGB_GAMMA_DIVISOR * (c ** (1.0 / ColorConstants.SRGB_GAMMA_POWER)) - ColorConstants.SRGB_GAMMA_OFFSET


def xyz_to_rgb(xyz: Tuple[float, float, float], clamp: bool = True) -> Tuple[int, int, int]:
    """
    Convert CIE XYZ to sRGB (0-255).
    
    Args:
        xyz: XYZ color tuple
        clamp: If True, clamp out-of-gamut values to 0-255. If False, may return
               values outside valid range (useful for gamut checking).
    
    Returns:
        RGB tuple (0-255)
    """
    # Scale from 0-100 to 0-1 range
    X, Y, Z = [v / ColorConstants.XYZ_SCALE_FACTOR for v in xyz]
    
    # Matrix multiplication using XYZ → sRGB coefficients
    r_lin = X * ColorConstants.XYZ_TO_SRGB_X[0] + Y * ColorConstants.XYZ_TO_SRGB_X[1] + Z * ColorConstants.XYZ_TO_SRGB_X[2]
    g_lin = X * ColorConstants.XYZ_TO_SRGB_Y[0] + Y * ColorConstants.XYZ_TO_SRGB_Y[1] + Z * ColorConstants.XYZ_TO_SRGB_Y[2]
    b_lin = X * ColorConstants.XYZ_TO_SRGB_Z[0] + Y * ColorConstants.XYZ_TO_SRGB_Z[1] + Z * ColorConstants.XYZ_TO_SRGB_Z[2]
    
    # Apply gamma correction
    r = linear_to_srgb(r_lin)
    g = linear_to_srgb(g_lin)
    b = linear_to_srgb(b_lin)
    
    # Convert to 0-255 range
    r_255 = r * ColorConstants.RGB_MAX
    g_255 = g * ColorConstants.RGB_MAX
    b_255 = b * ColorConstants.RGB_MAX
    
    if clamp:
        # Clamp to valid range
        r_255 = max(ColorConstants.RGB_MIN, min(ColorConstants.RGB_MAX, r_255))
        g_255 = max(ColorConstants.RGB_MIN, min(ColorConstants.RGB_MAX, g_255))
        b_255 = max(ColorConstants.RGB_MIN, min(ColorConstants.RGB_MAX, b_255))
    
    return (int(round(r_255)), int(round(g_255)), int(round(b_255)))


def lab_to_rgb(lab: Tuple[float, float, float], clamp: bool = True) -> Tuple[int, int, int]:
    """
    Convert CIE L*a*b* to sRGB (0-255).
    
    Args:
        lab: L*a*b* color tuple
        clamp: If True, clamp out-of-gamut colors to valid RGB range
    
    Returns:
        RGB tuple (0-255)
    """
    return xyz_to_rgb(lab_to_xyz(lab), clamp=clamp)


# ============================================================================
# LCH Color Space (Cylindrical LAB)
# ============================================================================

def lab_to_lch(lab: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    Convert L*a*b* to L*C*h° (cylindrical LAB).
    
    LCH is more intuitive than LAB for certain operations:
    - L* (Lightness): Same as LAB, 0-100
    - C* (Chroma): Color intensity/saturation, sqrt(a² + b²)
    - h° (Hue): Hue angle in degrees, 0-360
    
    Returns:
        (L*, C*, h°) tuple
    """
    L, a, b = lab
    C = math.sqrt(a*a + b*b)  # Chroma (color intensity)
    h = math.degrees(math.atan2(b, a))  # Hue angle
    if h < 0:
        h += ColorConstants.HUE_CIRCLE_DEGREES  # Normalize to 0-360
    return (L, C, h)


def lch_to_lab(lch: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    Convert L*C*h° to L*a*b*.
    
    Args:
        lch: (L*, C*, h°) tuple
    
    Returns:
        (L*, a*, b*) tuple
    """
    L, C, h = lch
    h_rad = math.radians(h)
    a = C * math.cos(h_rad)
    b = C * math.sin(h_rad)
    return (L, a, b)


def lch_to_rgb(lch: Tuple[float, float, float], clamp: bool = True) -> Tuple[int, int, int]:
    """Convert L*C*h° directly to sRGB (0-255)."""
    return lab_to_rgb(lch_to_lab(lch), clamp=clamp)


def rgb_to_lch(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """Convert sRGB (0-255) directly to L*C*h°."""
    return lab_to_lch(rgb_to_lab(rgb))


# ============================================================================
# HSL Conversions
# ============================================================================

def rgb_to_rawhsl(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """
    Convert RGB to raw HSL (all values 0-1).
    
    Uses Python's colorsys module for the conversion.
    """
    r, g, b = [v / ColorConstants.RGB_MAX for v in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return (h, s, l)


def rgb_to_hsl(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """
    Convert RGB (0-255) to HSL (H: 0-360, S: 0-100, L: 0-100).
    
    This is the standard HSL representation:
    - H: Hue in degrees (0° = red, 120° = green, 240° = blue)
    - S: Saturation as percentage (0% = gray, 100% = pure color)
    - L: Lightness as percentage (0% = black, 50% = pure color, 100% = white)
    """
    h, s, l = rgb_to_rawhsl(rgb)
    return (h * ColorConstants.HUE_CIRCLE_DEGREES, s * ColorConstants.XYZ_SCALE_FACTOR, l * ColorConstants.XYZ_SCALE_FACTOR)


def rgb_to_winhsl(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """
    Convert RGB (0-255) to Windows HSL (all components 0-240).
    
    Windows HSL is used in Win32 COLORREF and some GDI APIs.
    Each component is scaled to the 0-240 range instead of the usual
    H:0-360, S:0-100, L:0-100 representation.
    """
    h, s, l = rgb_to_rawhsl(rgb)
    win_h = int(round(h * ColorConstants.WIN_HSL_MAX))
    win_s = int(round(s * ColorConstants.WIN_HSL_MAX))
    win_l = int(round(l * ColorConstants.WIN_HSL_MAX))
    return (win_h, win_s, win_l)
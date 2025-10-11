from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Dict, List, Optional
import json
import math
import colorsys
import argparse
import sys
import threading
import hashlib
from pathlib import Path

JSON_PATH = Path(__file__).with_name("color_tools.json")

# ============================================================================
# COLOR SCIENCE CONSTANTS (Immutable)
# ============================================================================

class ColorConstants:
    """
    Immutable color science constants from international standards.
    
    These values are defined by CIE (International Commission on Illumination),
    sRGB specification, and various color difference formulas. They should
    never be modified as they represent fundamental color science.
    """
    
    # ===== D65 Standard Illuminant (CIE XYZ Reference White Point) =====
    # D65 represents average daylight with correlated color temperature of 6504K
    D65_WHITE_X = 95.047
    D65_WHITE_Y = 100.000
    D65_WHITE_Z = 108.883
    
    # ===== sRGB to XYZ Transformation Matrix (D65 Illuminant) =====
    # Linear RGB to XYZ conversion coefficients
    SRGB_TO_XYZ_R = (0.4124564, 0.3575761, 0.1804375)
    SRGB_TO_XYZ_G = (0.2126729, 0.7151522, 0.0721750)
    SRGB_TO_XYZ_B = (0.0193339, 0.1191920, 0.9503041)
    
    # ===== XYZ to sRGB Transformation Matrix (Inverse) =====
    XYZ_TO_SRGB_X = (3.2404542, -1.5371385, -0.4985314)
    XYZ_TO_SRGB_Y = (-0.9692660, 1.8760108, 0.0415560)
    XYZ_TO_SRGB_Z = (0.0556434, -0.2040259, 1.0572252)
    
    # ===== sRGB Gamma Correction (Companding) =====
    # sRGB uses a piecewise function for gamma encoding/decoding
    SRGB_GAMMA_THRESHOLD = 0.04045      # Crossover point for piecewise function
    SRGB_GAMMA_LINEAR_SCALE = 12.92     # Scale factor for linear segment
    SRGB_GAMMA_OFFSET = 0.055           # Offset for power function
    SRGB_GAMMA_DIVISOR = 1.055          # Divisor for power function
    SRGB_GAMMA_POWER = 2.4              # Gamma exponent
    
    # ===== Inverse sRGB Gamma (Linearization) =====
    SRGB_INV_GAMMA_THRESHOLD = 0.0031308  # Different threshold for inverse
    # Other constants same as forward direction
    
    # ===== CIE L*a*b* Color Space Constants =====
    LAB_DELTA = 6.0 / 29.0              # Delta constant (≈ 0.206897)
    LAB_KAPPA = 116.0                   # L* scale factor
    LAB_OFFSET = 16.0                   # L* offset
    LAB_A_SCALE = 500.0                 # a* scale factor
    LAB_B_SCALE = 200.0                 # b* scale factor
    
    # ===== Delta E 1994 (CIE94) Constants =====
    DE94_K1 = 0.045                     # Chroma weighting
    DE94_K2 = 0.015                     # Hue weighting
    
    # ===== Delta E 2000 (CIEDE2000) Constants =====
    # These are empirically derived for perceptual uniformity
    DE2000_POW7_BASE = 25.0             # Base for 25^7 calculation
    DE2000_HUE_OFFSET_1 = 30.0
    DE2000_HUE_WEIGHT_1 = 0.17
    DE2000_HUE_MULT_2 = 2.0
    DE2000_HUE_WEIGHT_2 = 0.24
    DE2000_HUE_MULT_3 = 3.0
    DE2000_HUE_OFFSET_3 = 6.0
    DE2000_HUE_WEIGHT_3 = 0.32
    DE2000_HUE_MULT_4 = 4.0
    DE2000_HUE_OFFSET_4 = 63.0
    DE2000_HUE_WEIGHT_4 = 0.20
    DE2000_DRO_MULT = 30.0
    DE2000_DRO_CENTER = 275.0
    DE2000_DRO_DIVISOR = 25.0
    DE2000_L_WEIGHT = 0.015
    DE2000_L_OFFSET = 50.0
    DE2000_L_DIVISOR = 20.0
    DE2000_C_WEIGHT = 0.045
    DE2000_H_WEIGHT = 0.015
    
    # ===== Delta E CMC Constants =====
    # Used in textile industry for color difference
    CMC_L_THRESHOLD = 16.0
    CMC_L_LOW = 0.511
    CMC_L_SCALE = 0.040975
    CMC_L_DIVISOR = 0.01765
    CMC_C_SCALE = 0.0638
    CMC_C_DIVISOR = 0.0131
    CMC_C_OFFSET = 0.638
    CMC_HUE_MIN = 164.0
    CMC_HUE_MAX = 345.0
    CMC_T_IN_RANGE = 0.56
    CMC_T_COS_MULT_IN = 0.2
    CMC_T_HUE_OFFSET_IN = 168.0
    CMC_T_OUT_RANGE = 0.36
    CMC_T_COS_MULT_OUT = 0.4
    CMC_T_HUE_OFFSET_OUT = 35.0
    CMC_F_POWER = 4.0
    CMC_F_DIVISOR = 1900.0
    
    # ===== Angle and Range Constants =====
    HUE_CIRCLE_DEGREES = 360.0          # Full circle for hue
    HUE_HALF_CIRCLE_DEGREES = 180.0     # Half circle
    RGB_MIN = 0                         # Minimum RGB value
    RGB_MAX = 255                       # Maximum RGB value (8-bit)
    NORMALIZED_MIN = 0.0                # Minimum normalized value
    NORMALIZED_MAX = 1.0                # Maximum normalized value
    XYZ_SCALE_FACTOR = 100.0            # XYZ typically scaled 0-100
    WIN_HSL_MAX = 240.0                 # Windows uses 0-240 for HSL
    
    # Computed values (derived from above constants)
    LAB_DELTA_CUBED = LAB_DELTA ** 3
    LAB_F_SCALE = 3.0 * (LAB_DELTA ** 2)
    LAB_F_OFFSET = 4.0 / 29.0
    
    @classmethod
    def _compute_hash(cls) -> str:
        """
        Compute SHA-256 hash of all constant values for integrity checking.
        
        This creates a fingerprint of all the color science constants. If any
        constant is accidentally (or maliciously) modified, the hash won't match.
        """
        # Collect all UPPERCASE attributes (our constant naming convention)
        constants = {}
        for name in dir(cls):
            if name.isupper() and not name.startswith('_'):
                value = getattr(cls, name)
                # Convert tuples to lists for JSON serialization
                if isinstance(value, tuple):
                    value = list(value)
                constants[name] = value
        
        # Create stable JSON representation (sorted keys for consistency)
        data = json.dumps(constants, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()
    
    @classmethod
    def verify_integrity(cls) -> bool:
        """
        Verify that constants haven't been modified.
        
        Returns:
            True if all constants match expected values, False if tampered with.
        """
        return cls._compute_hash() == cls._EXPECTED_HASH
    
    # This hash is computed once when the constants are known to be correct
    # Computed hash of all color science constants (SHA-256)
    _EXPECTED_HASH = "d54cf8dd2f7b92bbb83e43c3b636d55d7d973d12a31cb911d35216ed0f370f5b"

# ============================================================================
# RUNTIME CONFIGURATION (Mutable, Thread-Safe)
# ============================================================================

class ColorConfig(threading.local):
    """
    Thread-safe runtime configuration for color processing behavior.
    
    Unlike ColorConstants (which are immutable scientific values), these are
    user preferences that can be changed and may differ per thread. Uses
    threading.local() so each thread gets its own independent config.
    """
    
    def __init__(self):
        # Dual-color filament handling
        self.dual_color_mode = "first"  # Options: "first", "last", "mix"
        
        # Gamut checking parameters
        self.gamut_tolerance = 0.01           # Floating point tolerance
        self.gamut_max_iterations = 20        # Binary search iterations

# Global config instance (thread-local)
_config = ColorConfig()

def set_dual_color_mode(mode: str) -> None:
    """
    Set the global dual-color handling mode for filaments with multiple hex colors.
    
    Args:
        mode: One of "first", "last", or "mix"
            - "first": Use the first color (default)
            - "last": Use the second color
            - "mix": Perceptually blend both colors in LAB space
    
    Raises:
        ValueError: If mode is not one of the valid options
    """
    if mode not in ("first", "last", "mix"):
        raise ValueError(f"Invalid mode '{mode}'. Must be 'first', 'last', or 'mix'")
    _config.dual_color_mode = mode

def get_dual_color_mode() -> str:
    """Get the current dual-color handling mode."""
    return _config.dual_color_mode

def set_gamut_tolerance(tolerance: float) -> None:
    """Set the tolerance for gamut boundary checking."""
    _config.gamut_tolerance = tolerance

def set_gamut_max_iterations(iterations: int) -> None:
    """Set the maximum iterations for gamut mapping binary search."""
    _config.gamut_max_iterations = iterations

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass(frozen=True)
class ColorRecord:
    name: str
    hex: str
    rgb: Tuple[int, int, int]
    hsl: Tuple[float, float, float]   # (H°, S%, L%)
    lab: Tuple[float, float, float]   # (L*, a*, b*)

@dataclass(frozen=True)
class FilamentRecord:
    maker: str
    type: str
    finish: Optional[str]
    color: str
    hex: str
    td_value: Optional[float] = None
    
    @property
    def rgb(self) -> Tuple[int, int, int]:
        """Convert hex to RGB tuple, handling dual-color filaments."""
        hex_clean = self.hex.lstrip('#')
        
        # Check for dual-color format (e.g., "#333333-#666666")
        if '-' in hex_clean:
            # Split into individual colors
            hex_parts = [h.strip().lstrip('#') for h in hex_clean.split('-')]
            
            # Parse both colors
            rgb_colors = []
            for hex_part in hex_parts[:2]:  # Only take first 2 if more exist
                if len(hex_part) == 6:
                    try:
                        rgb_colors.append((
                            int(hex_part[0:2], 16),
                            int(hex_part[2:4], 16),
                            int(hex_part[4:6], 16)
                        ))
                    except ValueError:
                        rgb_colors.append((0, 0, 0))
                else:
                    rgb_colors.append((0, 0, 0))
            
            # If we didn't get 2 valid colors, fall back to first
            if len(rgb_colors) < 2:
                return rgb_colors[0] if rgb_colors else (0, 0, 0)
            
            # Apply dual-color mode
            mode = get_dual_color_mode()
            if mode == "last":
                return rgb_colors[1]
            elif mode == "mix":
                # Perceptual blend in LAB space
                lab1 = rgb_to_lab(rgb_colors[0])
                lab2 = rgb_to_lab(rgb_colors[1])
                # Average in LAB space (perceptually uniform)
                lab_avg = (
                    (lab1[0] + lab2[0]) / 2.0,
                    (lab1[1] + lab2[1]) / 2.0,
                    (lab1[2] + lab2[2]) / 2.0
                )
                return lab_to_rgb(lab_avg)
            else:  # "first" (default)
                return rgb_colors[0]
        
        # Single color - original logic
        # Handle potential multi-color hex values with commas or newlines
        if ',' in hex_clean or '\n' in hex_clean:
            hex_clean = hex_clean.split(',')[0].split('\n')[0].strip()
        
        if len(hex_clean) == 6:
            try:
                return (
                    int(hex_clean[0:2], 16),
                    int(hex_clean[2:4], 16),
                    int(hex_clean[4:6], 16)
                )
            except ValueError:
                return (0, 0, 0)
        return (0, 0, 0)
    
    @property
    def lab(self) -> Tuple[float, float, float]:
        """Convert to LAB color space."""
        return rgb_to_lab(self.rgb)
    
    @property
    def hsl(self) -> Tuple[float, float, float]:
        """Convert to HSL color space."""
        return rgb_to_hsl(self.rgb)
    
    def __str__(self) -> str:
        finish_str = f" {self.finish}" if self.finish else ""
        td_str = f" (TD: {self.td_value})" if self.td_value is not None else ""
        return f"{self.maker} {self.type}{finish_str} - {self.color} {self.hex}{td_str}"

# ---------------------- Forward Conversions (RGB → LAB) ----------------------

def srgb_to_linear(c: float) -> float:
    """Convert sRGB value to linear RGB (gamma correction removal)."""
    if c <= ColorConstants.SRGB_GAMMA_THRESHOLD:
        return c / ColorConstants.SRGB_GAMMA_LINEAR_SCALE
    return ((c + ColorConstants.SRGB_GAMMA_OFFSET) / ColorConstants.SRGB_GAMMA_DIVISOR) ** ColorConstants.SRGB_GAMMA_POWER

def rgb_to_xyz(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """Convert sRGB (0-255) to CIE XYZ using D65 illuminant."""
    r, g, b = [v / ColorConstants.RGB_MAX for v in rgb]
    r_lin, g_lin, b_lin = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    
    # Matrix multiplication using sRGB → XYZ coefficients
    X = r_lin * ColorConstants.SRGB_TO_XYZ_R[0] + g_lin * ColorConstants.SRGB_TO_XYZ_R[1] + b_lin * ColorConstants.SRGB_TO_XYZ_R[2]
    Y = r_lin * ColorConstants.SRGB_TO_XYZ_G[0] + g_lin * ColorConstants.SRGB_TO_XYZ_G[1] + b_lin * ColorConstants.SRGB_TO_XYZ_G[2]
    Z = r_lin * ColorConstants.SRGB_TO_XYZ_B[0] + g_lin * ColorConstants.SRGB_TO_XYZ_B[1] + b_lin * ColorConstants.SRGB_TO_XYZ_B[2]
    
    return (X * ColorConstants.XYZ_SCALE_FACTOR, Y * ColorConstants.XYZ_SCALE_FACTOR, Z * ColorConstants.XYZ_SCALE_FACTOR)

def _f_lab(t: float) -> float:
    """LAB conversion helper function."""
    if t > ColorConstants.LAB_DELTA_CUBED:
        return t ** (1.0 / 3.0)
    return t / ColorConstants.LAB_F_SCALE + ColorConstants.LAB_F_OFFSET

def xyz_to_lab(xyz: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Convert CIE XYZ to L*a*b* using D65 illuminant."""
    X, Y, Z = xyz
    fx = _f_lab(X / ColorConstants.D65_WHITE_X)
    fy = _f_lab(Y / ColorConstants.D65_WHITE_Y)
    fz = _f_lab(Z / ColorConstants.D65_WHITE_Z)
    
    L = ColorConstants.LAB_KAPPA * fy - ColorConstants.LAB_OFFSET
    a = ColorConstants.LAB_A_SCALE * (fx - fy)
    b = ColorConstants.LAB_B_SCALE * (fy - fz)
    return (L, a, b)

def rgb_to_lab(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """Convert sRGB (0-255) to CIE L*a*b*."""
    return xyz_to_lab(rgb_to_xyz(rgb))

# ---------------------- Reverse Conversions (LAB → RGB) ----------------------

def _f_lab_inverse(t: float) -> float:
    """Inverse of the f function used in LAB conversion."""
    if t > ColorConstants.LAB_DELTA:
        return t ** 3
    return ColorConstants.LAB_F_SCALE * (t - ColorConstants.LAB_F_OFFSET)

def lab_to_xyz(lab: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Convert CIE L*a*b* to XYZ using D65 illuminant."""
    L, a, b = lab
    
    fy = (L + ColorConstants.LAB_OFFSET) / ColorConstants.LAB_KAPPA
    fx = a / ColorConstants.LAB_A_SCALE + fy
    fz = fy - b / ColorConstants.LAB_B_SCALE
    
    X = ColorConstants.D65_WHITE_X * _f_lab_inverse(fx)
    Y = ColorConstants.D65_WHITE_Y * _f_lab_inverse(fy)
    Z = ColorConstants.D65_WHITE_Z * _f_lab_inverse(fz)
    
    return (X, Y, Z)

def linear_to_srgb(c: float) -> float:
    """Convert linear RGB to sRGB (inverse gamma correction)."""
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

# ---------------------- LCH Color Space (Cylindrical LAB) ----------------------

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

# ---------------------- Gamut Checking ----------------------

def is_in_srgb_gamut(lab: Tuple[float, float, float], tolerance: float | None = None) -> bool:
    """
    Check if a LAB color can be represented in sRGB without clipping.
    
    Not all LAB colors are representable in sRGB! For example, highly saturated
    colors at certain lightness levels might require RGB values outside 0-255.
    
    Args:
        lab: L*a*b* color tuple
        tolerance: How close to 0/255 boundaries before considering out-of-gamut.
                   If None, uses the global config value.
    
    Returns:
        True if the color can be represented in sRGB, False if it would clip
    """
    if tolerance is None:
        tolerance = _config.gamut_tolerance
        
    try:
        # Convert without clamping to see the "true" values
        rgb = lab_to_rgb(lab, clamp=False)
        r, g, b = rgb
        
        # Check if all components are within valid range (with small tolerance)
        min_val = ColorConstants.RGB_MIN - tolerance
        max_val = ColorConstants.RGB_MAX + tolerance
        
        return (min_val <= r <= max_val and 
                min_val <= g <= max_val and 
                min_val <= b <= max_val)
    except:
        return False

def find_nearest_in_gamut(lab: Tuple[float, float, float], 
                          max_iterations: int | None = None) -> Tuple[float, float, float]:
    """
    Find the nearest in-gamut LAB color to a given (possibly out-of-gamut) LAB color.
    
    Uses a simple approach: gradually reduce chroma until the color fits in sRGB gamut.
    This preserves hue and lightness while desaturating just enough to be valid.
    
    Args:
        lab: Potentially out-of-gamut L*a*b* color
        max_iterations: Maximum desaturation steps. If None, uses global config value.
    
    Returns:
        In-gamut L*a*b* color
    """
    if max_iterations is None:
        max_iterations = _config.gamut_max_iterations
        
    if is_in_srgb_gamut(lab):
        return lab
    
    # Convert to LCH for easier chroma manipulation
    L, C, h = lab_to_lch(lab)
    
    # Binary search for the maximum chroma that fits in gamut
    min_c = ColorConstants.NORMALIZED_MIN
    max_c = C
    
    for _ in range(max_iterations):
        test_c = (min_c + max_c) / 2.0
        test_lab = lch_to_lab((L, test_c, h))
        
        if is_in_srgb_gamut(test_lab):
            min_c = test_c  # Can increase chroma more
        else:
            max_c = test_c  # Need to reduce chroma
    
    # Return the in-gamut version
    return lch_to_lab((L, min_c, h))

# ---------------------- HSL Conversions ----------------------

def rgb_to_rawhsl(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """Convert RGB to raw HSL (all values 0-1)."""
    r, g, b = [v / ColorConstants.RGB_MAX for v in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return (h, s, l)

def rgb_to_hsl(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """Convert RGB (0-255) to HSL (H: 0-360, S: 0-100, L: 0-100)."""
    h, s, l = rgb_to_rawhsl(rgb)
    return (h * ColorConstants.HUE_CIRCLE_DEGREES, s * ColorConstants.XYZ_SCALE_FACTOR, l * ColorConstants.XYZ_SCALE_FACTOR)

def rgb_to_winhsl(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """
    Convert RGB (0-255) to Windows HSL (all components 0-240).
    Windows HSL is used in Win32 COLORREF and some GDI APIs.
    """
    h, s, l = rgb_to_rawhsl(rgb)
    win_h = int(round(h * ColorConstants.WIN_HSL_MAX))
    win_s = int(round(s * ColorConstants.WIN_HSL_MAX))
    win_l = int(round(l * ColorConstants.WIN_HSL_MAX))
    return (win_h, win_s, win_l)

# ---------------------- Distance Metrics ----------------------

def euclidean(v1: Tuple[float, ...], v2: Tuple[float, ...]) -> float:
    """Simple Euclidean distance between two vectors."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

def hue_diff_deg(h1: float, h2: float) -> float:
    """
    Calculate hue difference accounting for circular nature (0° = 360°).
    Returns the smallest angular difference.
    """
    d = abs(h1 - h2) % ColorConstants.HUE_CIRCLE_DEGREES
    return min(d, ColorConstants.HUE_CIRCLE_DEGREES - d)

def hsl_euclidean(hsl1: Tuple[float, float, float], hsl2: Tuple[float, float, float]) -> float:
    """Euclidean distance in HSL space (accounting for hue circularity)."""
    dh = hue_diff_deg(hsl1[0], hsl2[0])
    ds = hsl1[1] - hsl2[1]
    dl = hsl1[2] - hsl2[2]
    return math.sqrt(dh*dh + ds*ds + dl*dl)

# --- Delta E Formulas ---

def delta_e_76(lab1: Tuple[float, float, float], lab2: Tuple[float, float, float]) -> float:
    """
    Delta E 1976 (CIE76) - Simple Euclidean distance in LAB space.
    Fast but doesn't match human perception well.
    """
    return euclidean(lab1, lab2)

def delta_e_94(
    lab1: Tuple[float, float, float],
    lab2: Tuple[float, float, float],
    kL: float = 1.0,
    kC: float = 1.0,
    kH: float = 1.0,
    K1: float | None = None,
    K2: float | None = None,
) -> float:
    """
    Delta E 1994 (CIE94) - Improved perceptual uniformity.
    Better than E76 but still has issues with saturated colors.
    """
    if K1 is None:
        K1 = ColorConstants.DE94_K1
    if K2 is None:
        K2 = ColorConstants.DE94_K2
        
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    dL = L1 - L2
    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    dC = C1 - C2
    da = a1 - a2
    db = b1 - b2
    dH_sq = da*da + db*db - dC*dC
    SL = ColorConstants.NORMALIZED_MAX
    SC = ColorConstants.NORMALIZED_MAX + K1 * C1
    SH = ColorConstants.NORMALIZED_MAX + K2 * C1
    return math.sqrt((dL/(kL*SL))**2 + (dC/(kC*SC))**2 + (dH_sq/((kH*SH)**2)))

def _atan2_deg(y: float, x: float) -> float:
    """atan2 in degrees mapped to [0,360)."""
    if x == 0.0 and y == 0.0:
        return 0.0
    ang = math.degrees(math.atan2(y, x))
    return ang + ColorConstants.HUE_CIRCLE_DEGREES if ang < 0.0 else ang

def _hp(ap: float, b: float) -> float:
    """Helper for CIEDE2000 hue prime calculation."""
    return _atan2_deg(b, ap)

def _mean_hue(h1: float, h2: float, C1p: float, C2p: float) -> float:
    """Helper for CIEDE2000 mean hue calculation."""
    if C1p * C2p == 0:
        return h1 + h2
    dh = abs(h1 - h2)
    if dh > ColorConstants.HUE_HALF_CIRCLE_DEGREES:
        sum_h = h1 + h2
        if sum_h < ColorConstants.HUE_CIRCLE_DEGREES:
            return (sum_h + ColorConstants.HUE_CIRCLE_DEGREES) / 2.0
        else:
            return (sum_h - ColorConstants.HUE_CIRCLE_DEGREES) / 2.0
    return (h1 + h2) / 2.0

def delta_e_2000(
    lab1: Tuple[float, float, float],
    lab2: Tuple[float, float, float],
    kL: float = 1.0,
    kC: float = 1.0,
    kH: float = 1.0,
) -> float:
    """
    Delta E 2000 (CIEDE2000) - Current gold standard for color difference.
    
    Most perceptually uniform, handles edge cases like neutral colors and blue hues.
    This is the recommended metric for most applications.
    
    Parameters:
        kL, kC, kH: Weighting factors (usually all 1.0)
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    # Step 1: Chroma and a' compensation
    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    C_bar = (C1 + C2) / 2.0
    C_bar7 = C_bar ** 7
    pow7_term = ColorConstants.DE2000_POW7_BASE ** 7
    G = 0.5 * (1.0 - math.sqrt(C_bar7 / (C_bar7 + pow7_term)))
    a1p = (1.0 + G) * a1
    a2p = (1.0 + G) * a2
    C1p = math.hypot(a1p, b1)
    C2p = math.hypot(a2p, b2)

    # Step 2: Hue angles
    h1p = _hp(a1p, b1)
    h2p = _hp(a2p, b2)

    # Step 3: Differences
    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    else:
        dh = h2p - h1p
        if dh > ColorConstants.HUE_HALF_CIRCLE_DEGREES:
            dh -= ColorConstants.HUE_CIRCLE_DEGREES
        elif dh < -ColorConstants.HUE_HALF_CIRCLE_DEGREES:
            dh += ColorConstants.HUE_CIRCLE_DEGREES
        dhp = dh
    dHp = 2.0 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp * 0.5))

    # Step 4: Means
    Lp_bar = (L1 + L2) / 2.0
    Cp_bar = (C1p + C2p) / 2.0
    hp_bar = _mean_hue(h1p, h2p, C1p, C2p)

    # Step 5: Weighting functions
    T = (
        ColorConstants.NORMALIZED_MAX
        - ColorConstants.DE2000_HUE_WEIGHT_1 * math.cos(math.radians(hp_bar - ColorConstants.DE2000_HUE_OFFSET_1))
        + ColorConstants.DE2000_HUE_WEIGHT_2 * math.cos(math.radians(ColorConstants.DE2000_HUE_MULT_2 * hp_bar))
        + ColorConstants.DE2000_HUE_WEIGHT_3 * math.cos(math.radians(ColorConstants.DE2000_HUE_MULT_3 * hp_bar + ColorConstants.DE2000_HUE_OFFSET_3))
        - ColorConstants.DE2000_HUE_WEIGHT_4 * math.cos(math.radians(ColorConstants.DE2000_HUE_MULT_4 * hp_bar - ColorConstants.DE2000_HUE_OFFSET_4))
    )
    d_ro = ColorConstants.DE2000_DRO_MULT * math.exp(-(((hp_bar - ColorConstants.DE2000_DRO_CENTER) / ColorConstants.DE2000_DRO_DIVISOR) ** 2))
    Cp_bar7 = Cp_bar ** 7
    RC = 2.0 * math.sqrt(Cp_bar7 / (Cp_bar7 + pow7_term))
    L_diff = Lp_bar - ColorConstants.DE2000_L_OFFSET
    SL = ColorConstants.NORMALIZED_MAX + (ColorConstants.DE2000_L_WEIGHT * (L_diff ** 2)) / math.sqrt(ColorConstants.DE2000_L_DIVISOR + (L_diff ** 2))
    SC = ColorConstants.NORMALIZED_MAX + ColorConstants.DE2000_C_WEIGHT * Cp_bar
    SH = ColorConstants.NORMALIZED_MAX + ColorConstants.DE2000_H_WEIGHT * Cp_bar * T
    RT = -math.sin(math.radians(2.0 * d_ro)) * RC

    # Step 6: Final formula
    dE = math.sqrt(
        (dLp / (kL * SL)) ** 2
        + (dCp / (kC * SC)) ** 2
        + (dHp / (kH * SH)) ** 2
        + RT * (dCp / (kC * SC)) * (dHp / (kH * SH))
    )
    return dE

def delta_e_cmc(
    lab1: Tuple[float, float, float],
    lab2: Tuple[float, float, float],
    l: float = 2.0,
    c: float = 1.0,
) -> float:
    """
    Delta E CMC(l:c) - Color difference formula used in textile industry.
    
    Common choices:
        l:c = 2:1 → "acceptability" (default)
        l:c = 1:1 → "perceptibility"
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    # Chroma
    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)

    # Differences
    dL = L1 - L2
    da = a1 - a2
    db = b1 - b2
    dC = C1 - C2
    dH_sq = da * da + db * db - dC * dC
    if dH_sq < 0.0:
        dH_sq = 0.0  # numerical safety

    # Weights
    if L1 < ColorConstants.CMC_L_THRESHOLD:
        SL = ColorConstants.CMC_L_LOW
    else:
        SL = (ColorConstants.CMC_L_SCALE * L1) / (ColorConstants.NORMALIZED_MAX + ColorConstants.CMC_L_DIVISOR * L1)
    
    SC = ColorConstants.CMC_C_SCALE * C1 / (ColorConstants.NORMALIZED_MAX + ColorConstants.CMC_C_DIVISOR * C1) + ColorConstants.CMC_C_OFFSET

    # Hue angle and related terms
    h1 = _atan2_deg(b1, a1)
    if ColorConstants.CMC_HUE_MIN <= h1 <= ColorConstants.CMC_HUE_MAX:
        T = ColorConstants.CMC_T_IN_RANGE + abs(ColorConstants.CMC_T_COS_MULT_IN * math.cos(math.radians(h1 + ColorConstants.CMC_T_HUE_OFFSET_IN)))
    else:
        T = ColorConstants.CMC_T_OUT_RANGE + abs(ColorConstants.CMC_T_COS_MULT_OUT * math.cos(math.radians(h1 + ColorConstants.CMC_T_HUE_OFFSET_OUT)))

    F = math.sqrt((C1 ** ColorConstants.CMC_F_POWER) / (C1 ** ColorConstants.CMC_F_POWER + ColorConstants.CMC_F_DIVISOR)) if C1 != 0 else 0.0
    SH = SC * (F * T + (ColorConstants.NORMALIZED_MAX - F))

    # Assemble
    term_L = (dL / (l * SL)) ** 2
    term_C = (dC / (c * SC)) ** 2
    term_H = (math.sqrt(dH_sq) / SH) ** 2 if SH != 0 else 0.0

    return math.sqrt(term_L + term_C + term_H)

# ---------------------- Palette Management ----------------------

def load_colors(json_path: Path | str = JSON_PATH) -> List[ColorRecord]:
    """Load CSS color database from JSON file (colors section only)."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    recs: List[ColorRecord] = []
    # Only load from the "colors" section
    for c in data.get("colors", []):
        recs.append(ColorRecord(
            name=c["name"],
            hex=c["hex"],
            rgb=(c["rgb"]["r"], c["rgb"]["g"], c["rgb"]["b"]),
            hsl=(float(c["hsl"]["h"]), float(c["hsl"]["s"]), float(c["hsl"]["l"])),
            lab=(float(c["lab"]["L"]), float(c["lab"]["a"]), float(c["lab"]["b"])),
        ))
    return recs

def load_filaments(json_path: Path | str = JSON_PATH) -> List[FilamentRecord]:
    """Load filament database from JSON file (filaments section only)."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    recs: List[FilamentRecord] = []
    # Only load from the "filaments" section
    for f in data.get("filaments", []):
        recs.append(FilamentRecord(
            maker=f["maker"],
            type=f["type"],
            finish=f.get("finish"),  # finish can be None
            color=f["color"],
            hex=f["hex"],
            td_value=f.get("td_value"),  # td_value can be None
        ))
    return recs

def _rounded_key(nums: Tuple[float, ...], ndigits: int = 2) -> str:
    """Create a string key from rounded numeric values."""
    return ",".join(str(round(x, ndigits)) for x in nums)

class Palette:
    """
    Color palette with multiple indexing strategies for fast lookup.
    """
    def __init__(self, records: List[ColorRecord]) -> None:
        self.records = records
        self._by_name: Dict[str, ColorRecord] = {r.name.lower(): r for r in records}
        self._by_rgb: Dict[Tuple[int, int, int], ColorRecord] = {r.rgb: r for r in records}
        self._by_hsl: Dict[str, ColorRecord] = {_rounded_key(r.hsl): r for r in records}
        self._by_lab: Dict[str, ColorRecord] = {_rounded_key(r.lab): r for r in records}

    def find_by_name(self, name: str) -> Optional[ColorRecord]:
        """Find color by exact name match (case-insensitive)."""
        return self._by_name.get(name.lower())

    def find_by_rgb(self, rgb: Tuple[int, int, int]) -> Optional[ColorRecord]:
        """Find color by exact RGB match."""
        return self._by_rgb.get(rgb)

    def find_by_hsl(self, hsl: Tuple[float, float, float], rounding: int = 2) -> Optional[ColorRecord]:
        """Find color by HSL match (with rounding)."""
        return self._by_hsl.get(_rounded_key(hsl, rounding))

    def find_by_lab(self, lab: Tuple[float, float, float], rounding: int = 2) -> Optional[ColorRecord]:
        """Find color by LAB match (with rounding)."""
        return self._by_lab.get(_rounded_key(lab, rounding))

    def nearest_color(
        self,
        value: Tuple[float, float, float],
        space: str = "lab",
        metric: str = "de2000",
        *,
        cmc_l: float = 2.0,
        cmc_c: float = 1.0,
    ) -> Tuple[ColorRecord, float]:
        """
        Find nearest color by space/metric.
        
        Args:
            value: Color in the specified space (RGB, HSL, or LAB)
            space: Color space - 'rgb', 'hsl', or 'lab' (default: 'lab')
            metric: Distance metric - 'euclidean', 'de76', 'de94', 'de2000', 'cmc'
            cmc_l, cmc_c: Parameters for CMC metric (default 2:1 for acceptability)
        
        Returns:
            (nearest_color_record, distance) tuple
        """
        best_rec: Optional[ColorRecord] = None
        best_d = float("inf")

        if space.lower() == "rgb":
            for r in self.records:
                d = euclidean(tuple(map(float, value)), tuple(map(float, r.rgb)))
                if d < best_d:
                    best_rec, best_d = r, d
            return best_rec, best_d  # type: ignore

        if space.lower() == "hsl":
            for r in self.records:
                d = hsl_euclidean(value, r.hsl)
                if d < best_d:
                    best_rec, best_d = r, d
            return best_rec, best_d  # type: ignore

        metric_l = metric.lower()
        if metric_l in ("de2000", "ciede2000"):
            fn = delta_e_2000
            args = ()
        elif metric_l in ("de94", "cie94"):
            fn = delta_e_94
            args = ()
        elif metric_l in ("de76", "cie76", "euclidean"):
            fn = delta_e_76
            args = ()
        elif metric_l in ("cmc", "decmc", "cmc21", "cmc11"):
            fn = None
            args = ()
        else:
            raise ValueError("Unknown metric. Use 'euclidean'/'de76'/'de94'/'de2000'/'cmc'.")

        for r in self.records:
            if metric_l in ("cmc", "decmc", "cmc21", "cmc11"):
                # Allow shorthands
                l, c = cmc_l, cmc_c
                if metric_l == "cmc21":
                    l, c = 2.0, 1.0
                elif metric_l == "cmc11":
                    l, c = 1.0, 1.0
                d = delta_e_cmc(value, r.lab, l=l, c=c)
            else:
                d = fn(value, r.lab)  # type: ignore
            if d < best_d:
                best_rec, best_d = r, d
        return best_rec, best_d  # type: ignore

class FilamentPalette:
    """
    Filament palette with multiple indexing strategies for fast lookup.
    """
    def __init__(self, records: List[FilamentRecord]) -> None:
        self.records = records
        # Create various lookup indices
        self._by_maker: Dict[str, List[FilamentRecord]] = {}
        self._by_type: Dict[str, List[FilamentRecord]] = {}
        self._by_color: Dict[str, List[FilamentRecord]] = {}
        self._by_rgb: Dict[Tuple[int, int, int], List[FilamentRecord]] = {}
        self._by_finish: Dict[str, List[FilamentRecord]] = {}
        
        # Build indices
        for rec in records:
            # By maker
            if rec.maker not in self._by_maker:
                self._by_maker[rec.maker] = []
            self._by_maker[rec.maker].append(rec)
            
            # By type
            if rec.type not in self._by_type:
                self._by_type[rec.type] = []
            self._by_type[rec.type].append(rec)
            
            # By color (case-insensitive)
            color_key = rec.color.lower()
            if color_key not in self._by_color:
                self._by_color[color_key] = []
            self._by_color[color_key].append(rec)
            
            # By RGB
            rgb = rec.rgb
            if rgb not in self._by_rgb:
                self._by_rgb[rgb] = []
            self._by_rgb[rgb].append(rec)
            
            # By finish (if present)
            if rec.finish:
                if rec.finish not in self._by_finish:
                    self._by_finish[rec.finish] = []
                self._by_finish[rec.finish].append(rec)

    def find_by_maker(self, maker: str) -> List[FilamentRecord]:
        """Find all filaments by maker."""
        return self._by_maker.get(maker, [])

    def find_by_type(self, type_name: str) -> List[FilamentRecord]:
        """Find all filaments by type."""
        return self._by_type.get(type_name, [])

    def find_by_color(self, color: str) -> List[FilamentRecord]:
        """Find all filaments by color name (case-insensitive)."""
        return self._by_color.get(color.lower(), [])

    def find_by_rgb(self, rgb: Tuple[int, int, int]) -> List[FilamentRecord]:
        """Find all filaments by exact RGB match."""
        return self._by_rgb.get(rgb, [])

    def find_by_finish(self, finish: str) -> List[FilamentRecord]:
        """Find all filaments by finish."""
        return self._by_finish.get(finish, [])

    def filter(self, maker: Optional[str] = None, type_name: Optional[str] = None, 
               finish: Optional[str] = None, color: Optional[str] = None) -> List[FilamentRecord]:
        """Filter filaments by multiple criteria."""
        results = self.records
        
        if maker:
            results = [r for r in results if r.maker == maker]
        if type_name:
            results = [r for r in results if r.type == type_name]
        if finish:
            results = [r for r in results if r.finish == finish]
        if color:
            results = [r for r in results if r.color.lower() == color.lower()]
            
        return results

    def nearest_filament(
        self,
        target_rgb: Tuple[int, int, int],
        metric: str = "de2000",
        *,
        maker_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        cmc_l: float = 2.0,
        cmc_c: float = 1.0,
    ) -> Tuple[FilamentRecord, float]:
        """
        Find nearest filament by color similarity.
        
        Args:
            target_rgb: Target RGB color tuple
            metric: Distance metric - 'euclidean', 'de76', 'de94', 'de2000', 'cmc'
            maker_filter: Optional maker filter
            type_filter: Optional type filter
            cmc_l, cmc_c: Parameters for CMC metric
        
        Returns:
            (nearest_filament_record, distance) tuple
        """
        target_lab = rgb_to_lab(target_rgb)
        
        # Apply filters
        candidates = self.records
        if maker_filter:
            candidates = [r for r in candidates if r.maker == maker_filter]
        if type_filter:
            candidates = [r for r in candidates if r.type == type_filter]
        
        if not candidates:
            raise ValueError("No filaments match the specified filters")
        
        best_rec: Optional[FilamentRecord] = None
        best_d = float("inf")

        # Choose distance function
        metric_l = metric.lower()
        if metric_l in ("de2000", "ciede2000"):
            distance_fn = delta_e_2000
        elif metric_l in ("de94", "cie94"):
            distance_fn = delta_e_94
        elif metric_l in ("de76", "cie76"):
            distance_fn = delta_e_76
        elif metric_l == "euclidean":
            distance_fn = lambda lab1, lab2: euclidean(lab1, lab2)
        elif metric_l in ("cmc", "decmc"):
            distance_fn = lambda lab1, lab2: delta_e_cmc(lab1, lab2, l=cmc_l, c=cmc_c)
        else:
            raise ValueError("Unknown metric. Use 'euclidean'/'de76'/'de94'/'de2000'/'cmc'.")

        for rec in candidates:
            try:
                d = distance_fn(target_lab, rec.lab)
                if d < best_d:
                    best_rec, best_d = rec, d
            except:
                # Skip filaments with invalid colors
                continue
        
        if best_rec is None:
            raise ValueError("No valid filaments found")
            
        return best_rec, best_d

    @property
    def makers(self) -> List[str]:
        """Get list of all makers."""
        return sorted(self._by_maker.keys())

    @property
    def types(self) -> List[str]:
        """Get list of all types."""
        return sorted(self._by_type.keys())

    @property
    def finishes(self) -> List[str]:
        """Get list of all finishes."""
        return sorted(self._by_finish.keys())

# ---------------------- CLI ----------------------

def _cli():
    parser = argparse.ArgumentParser(
        description="Color search and conversion tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find nearest CSS color to an RGB value
  %(prog)s color --nearest --value 128 64 200
  
  # Find color by name
  %(prog)s color --name "coral"
  
  # Find nearest filament to an RGB color
  %(prog)s filament --nearest --value 255 0 0
  
  # List all filament makers
  %(prog)s filament --list-makers
  
  # Convert between color spaces
  %(prog)s convert --from rgb --to lab --value 255 128 0
  
  # Check if LAB color is in sRGB gamut
  %(prog)s convert --check-gamut --value 50 100 50
        """
    )
    
    # Global argument (applies to all subcommands)
    parser.add_argument(
        "--json", 
        type=str, 
        default=str(JSON_PATH), 
        help="Path to JSON data file (default: color_tools.json)"
    )
    parser.add_argument(
        "--verify-constants",
        action="store_true",
        help="Verify integrity of color science constants before proceeding"
    )
    
    # Create subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # ==================== COLOR SUBCOMMAND ====================
    color_parser = subparsers.add_parser(
        "color",
        help="Work with CSS colors",
        description="Search and query CSS color database"
    )
    
    color_parser.add_argument(
        "--nearest", 
        action="store_true", 
        help="Find nearest color to the given value"
    )
    color_parser.add_argument(
        "--name", 
        type=str, 
        help="Find an exact color by name"
    )
    color_parser.add_argument(
        "--value", 
        nargs=3, 
        type=float, 
        metavar=("V1", "V2", "V3"),
        help="Color value tuple (RGB: r g b | HSL: h s l | LAB: L a b)"
    )
    color_parser.add_argument(
        "--space", 
        choices=["rgb", "hsl", "lab"], 
        default="lab",
        help="Color space of the input value (default: lab)"
    )
    color_parser.add_argument(
        "--metric",
        choices=["euclidean", "de76", "de94", "de2000", "cmc", "cmc21", "cmc11"],
        default="de2000",
        help="Distance metric for LAB space (default: de2000). 'cmc21'=CMC(2:1), 'cmc11'=CMC(1:1)"
    )
    color_parser.add_argument(
        "--cmc-l", 
        type=float, 
        default=2.0, 
        help="CMC lightness parameter (default: 2.0)"
    )
    color_parser.add_argument(
        "--cmc-c", 
        type=float, 
        default=1.0, 
        help="CMC chroma parameter (default: 1.0)"
    )
    
    # ==================== FILAMENT SUBCOMMAND ====================
    filament_parser = subparsers.add_parser(
        "filament",
        help="Work with 3D printing filaments",
        description="Search and query 3D printing filament database"
    )
    
    filament_parser.add_argument(
        "--nearest", 
        action="store_true", 
        help="Find nearest filament to the given RGB color"
    )
    filament_parser.add_argument(
        "--value", 
        nargs=3, 
        type=int, 
        metavar=("R", "G", "B"),
        help="RGB color value (0-255 for each component)"
    )
    filament_parser.add_argument(
        "--metric",
        choices=["euclidean", "de76", "de94", "de2000", "cmc"],
        default="de2000",
        help="Distance metric (default: de2000)"
    )
    filament_parser.add_argument(
        "--cmc-l", 
        type=float, 
        default=2.0, 
        help="CMC lightness parameter (default: 2.0)"
    )
    filament_parser.add_argument(
        "--cmc-c", 
        type=float, 
        default=1.0, 
        help="CMC chroma parameter (default: 1.0)"
    )
    
    # List operations
    filament_parser.add_argument(
        "--list-makers", 
        action="store_true", 
        help="List all filament makers"
    )
    filament_parser.add_argument(
        "--list-types", 
        action="store_true", 
        help="List all filament types"
    )
    filament_parser.add_argument(
        "--list-finishes", 
        action="store_true", 
        help="List all filament finishes"
    )
    
    # Filter operations
    filament_parser.add_argument(
        "--maker", 
        type=str, 
        help="Filter by maker"
    )
    filament_parser.add_argument(
        "--type", 
        type=str, 
        help="Filter by type"
    )
    filament_parser.add_argument(
        "--finish", 
        type=str, 
        help="Filter by finish"
    )
    filament_parser.add_argument(
        "--color", 
        type=str, 
        help="Filter by color name"
    )
    filament_parser.add_argument(
        "--filter", 
        action="store_true", 
        help="Display filaments matching filter criteria"
    )
    filament_parser.add_argument(
        "--dual-color-mode",
        choices=["first", "last", "mix"],
        default="first",
        help="How to handle dual-color filaments: 'first' (default), 'last', or 'mix' (perceptual blend)"
    )
    
    # ==================== CONVERT SUBCOMMAND ====================
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert between color spaces",
        description="Convert colors between RGB, HSL, LAB, and LCH spaces"
    )
    
    convert_parser.add_argument(
        "--from",
        dest="from_space",
        choices=["rgb", "hsl", "lab", "lch"],
        help="Source color space"
    )
    convert_parser.add_argument(
        "--to",
        dest="to_space",
        choices=["rgb", "hsl", "lab", "lch"],
        help="Target color space"
    )
    convert_parser.add_argument(
        "--value", 
        nargs=3, 
        type=float, 
        metavar=("V1", "V2", "V3"),
        help="Color value tuple"
    )
    convert_parser.add_argument(
        "--check-gamut", 
        action="store_true", 
        help="Check if LAB/LCH color is in sRGB gamut (requires --value)"
    )
    
    args = parser.parse_args()
    
    # Verify constants integrity if requested
    if args.verify_constants:
        if not ColorConstants.verify_integrity():
            print("ERROR: ColorConstants integrity check FAILED!", file=sys.stderr)
            print("The color science constants have been modified.", file=sys.stderr)
            print(f"Expected hash: {ColorConstants._EXPECTED_HASH}", file=sys.stderr)
            print(f"Current hash:  {ColorConstants._compute_hash()}", file=sys.stderr)
            sys.exit(1)
        print("✓ ColorConstants integrity verified")
    
    # Handle no subcommand
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    # The --json argument is processed here at the top level, before any command logic
    json_path = args.json
    
    # ==================== COLOR COMMAND HANDLER ====================
    if args.command == "color":
        # Load color palette
        palette = Palette(load_colors(json_path))
        
        if args.name:
            rec = palette.find_by_name(args.name)
            if not rec:
                print(f"Color '{args.name}' not found")
                sys.exit(1)
            print(f"Name: {rec.name}")
            print(f"Hex:  {rec.hex}")
            print(f"RGB:  {rec.rgb}")
            print(f"HSL:  ({rec.hsl[0]:.1f}°, {rec.hsl[1]:.1f}%, {rec.hsl[2]:.1f}%)")
            print(f"LAB:  ({rec.lab[0]:.2f}, {rec.lab[1]:.2f}, {rec.lab[2]:.2f})")
            sys.exit(0)
        
        if args.nearest:
            if not args.value:
                print("Error: --nearest requires --value")
                sys.exit(2)
            
            val = tuple(args.value)
            
            # Convert to LAB if needed for distance calculation
            if args.space == "rgb":
                rgb_val: Tuple[int, int, int] = (int(val[0]), int(val[1]), int(val[2]))
                lab_val = rgb_to_lab(rgb_val)
            elif args.space == "hsl":
                print("Error: HSL search not yet implemented")
                sys.exit(1)
            else:  # lab
                lab_val = val
            
            rec, d = palette.nearest_color(
                lab_val,
                space="lab",
                metric=args.metric,
                cmc_l=args.cmc_l,
                cmc_c=args.cmc_c,
            )
            print(f"Nearest color: {rec.name} (distance={d:.2f})")
            print(f"Hex:  {rec.hex}")
            print(f"RGB:  {rec.rgb}")
            print(f"HSL:  ({rec.hsl[0]:.1f}°, {rec.hsl[1]:.1f}%, {rec.hsl[2]:.1f}%)")
            print(f"LAB:  ({rec.lab[0]:.2f}, {rec.lab[1]:.2f}, {rec.lab[2]:.2f})")
            sys.exit(0)
        
        # If we get here, no valid color operation was specified
        color_parser.print_help()
        sys.exit(0)
    
    # ==================== FILAMENT COMMAND HANDLER ====================
    elif args.command == "filament":
        # Set dual-color mode BEFORE loading any filaments
        if hasattr(args, 'dual_color_mode'):
            set_dual_color_mode(args.dual_color_mode)
        
        # Load filament palette
        filament_palette = FilamentPalette(load_filaments(json_path))
        
        if args.list_makers:
            print("Available makers:")
            for maker in filament_palette.makers:
                count = len(filament_palette.find_by_maker(maker))
                print(f"  {maker} ({count} filaments)")
            sys.exit(0)
        
        if args.list_types:
            print("Available types:")
            for type_name in filament_palette.types:
                count = len(filament_palette.find_by_type(type_name))
                print(f"  {type_name} ({count} filaments)")
            sys.exit(0)
        
        if args.list_finishes:
            print("Available finishes:")
            for finish in filament_palette.finishes:
                count = len(filament_palette.find_by_finish(finish))
                print(f"  {finish} ({count} filaments)")
            sys.exit(0)
        
        if args.filter or (args.maker or args.type or args.finish or args.color):
            # Filter and display filaments
            results = filament_palette.filter(
                maker=args.maker,
                type_name=args.type,
                finish=args.finish,
                color=args.color
            )
            
            if not results:
                print("No filaments found matching the criteria")
                sys.exit(1)
            
            print(f"Found {len(results)} filament(s):")
            for rec in results:
                print(f"  {rec}")
            sys.exit(0)
        
        if args.nearest:
            if not args.value:
                print("Error: --nearest requires --value with RGB components")
                sys.exit(2)
            
            rgb_val = tuple(args.value)
            
            try:
                rec, d = filament_palette.nearest_filament(
                    rgb_val,
                    metric=args.metric,
                    maker_filter=args.maker,
                    type_filter=args.type,
                    cmc_l=args.cmc_l,
                    cmc_c=args.cmc_c,
                )
                print(f"Nearest filament: (distance={d:.2f})")
                print(f"  {rec}")
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)
            sys.exit(0)
        
        # If we get here, no valid filament operation was specified
        filament_parser.print_help()
        sys.exit(0)
    
    # ==================== CONVERT COMMAND HANDLER ====================
    elif args.command == "convert":
        if args.check_gamut:
            if not args.value:
                print("Error: --check-gamut requires --value")
                sys.exit(2)
            
            val = tuple(args.value)
            
            # Assume LAB unless otherwise specified
            if args.from_space == "lch":
                lab = lch_to_lab(val)
            else:
                lab = val
            
            in_gamut = is_in_srgb_gamut(lab)
            print(f"LAB({lab[0]:.2f}, {lab[1]:.2f}, {lab[2]:.2f}) is {'IN' if in_gamut else 'OUT OF'} sRGB gamut")
            
            if not in_gamut:
                nearest = find_nearest_in_gamut(lab)
                nearest_rgb = lab_to_rgb(nearest)
                print(f"Nearest in-gamut color:")
                print(f"  LAB: ({nearest[0]:.2f}, {nearest[1]:.2f}, {nearest[2]:.2f})")
                print(f"  RGB: {nearest_rgb}")
            
            sys.exit(0)
        
        if args.from_space and args.to_space and args.value:
            val = tuple(args.value)
            from_space = args.from_space
            to_space = args.to_space
            
            # Convert to RGB as intermediate (everything goes through RGB)
            if from_space == "rgb":
                rgb: Tuple[int, int, int] = (int(val[0]), int(val[1]), int(val[2]))
            elif from_space == "hsl":
                print("Error: HSL to RGB conversion not yet implemented")
                sys.exit(1)
            elif from_space == "lab":
                rgb = lab_to_rgb(val)
            elif from_space == "lch":
                rgb = lch_to_rgb(val)
            
            # Convert from RGB to target
            if to_space == "rgb":
                result = rgb
            elif to_space == "hsl":
                result = rgb_to_hsl(rgb)
            elif to_space == "lab":
                result = rgb_to_lab(rgb)
            elif to_space == "lch":
                result = rgb_to_lch(rgb)
            
            print(f"Converted {from_space.upper()}{val} -> {to_space.upper()}{result}")
            sys.exit(0)
        
        # If we get here, no valid convert operation was specified
        convert_parser.print_help()
        sys.exit(0)

if __name__ == "__main__":
    _cli()
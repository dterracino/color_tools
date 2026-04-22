"""
Color vision deficiency simulation and correction.

This module provides functions to simulate how colors appear to individuals with
various types of color blindness (color vision deficiency, CVD) and to apply
corrections that can improve color discriminability for CVD individuals.

Supported deficiency types:
- **Protanopia**: Red-blind (missing L-cones, ~1% of males)
- **Deuteranopia**: Green-blind (missing M-cones, ~1% of males)  
- **Tritanopia**: Blue-blind (missing S-cones, ~0.001% of population)

Example usage:
    >>> # Simulate how red appears to someone with protanopia
    >>> simulated = simulate_protanopia((255, 0, 0))
    >>> # Result will be darker, yellowish
    
    >>> # Correct colors to improve discriminability for deuteranopia
    >>> corrected = correct_deuteranopia((0, 255, 0))
    >>> # Result shifts green to be more distinguishable
"""

from __future__ import annotations
from typing import Tuple
from color_tools.matrices import (
    multiply_matrix_vector,
    get_simulation_matrix,
    get_correction_matrix
)
from color_tools.constants import ColorConstants


def _apply_cvd_transform(
    rgb: Tuple[int, int, int],
    deficiency_type: str,
    operation: str = 'simulate'
) -> Tuple[int, int, int]:
    """
    Internal helper to apply color vision deficiency transformation.
    
    Args:
        rgb: RGB color tuple (0-255)
        deficiency_type: Type of CVD ('protanopia', 'deuteranopia', 'tritanopia')
        operation: Either 'simulate' or 'correct'
    
    Returns:
        Transformed RGB color tuple (0-255)
    """
    # Normalize RGB to 0-1 range
    r, g, b = [v / ColorConstants.RGB_MAX for v in rgb]

    # Simulation is always needed (both for 'simulate' and as the first step of 'correct')
    sim_matrix = get_simulation_matrix(deficiency_type)
    r_sim, g_sim, b_sim = multiply_matrix_vector(sim_matrix, (r, g, b))

    if operation == 'simulate':
        r_out, g_out, b_out = r_sim, g_sim, b_sim
    elif operation == 'correct':
        # Fidaner daltonization: apply correction matrix to the *error signal*
        # (the difference between original and simulated), then add it back.
        # This ensures neutral colors (white, grey) are never tinted.
        #   1. sim    = simulate(original)
        #   2. error  = original − sim
        #   3. shift  = correction_matrix × error
        #   4. out    = clamp(original + shift)
        error = (r - r_sim, g - g_sim, b - b_sim)
        corr_matrix = get_correction_matrix(deficiency_type)
        dr, dg, db = multiply_matrix_vector(corr_matrix, error)
        r_out = r + dr
        g_out = g + dg
        b_out = b + db
    else:
        raise ValueError(f"Invalid operation: {operation}. Must be 'simulate' or 'correct'")

    # Clamp to valid range and convert back to 0-255
    r_out = max(0, min(ColorConstants.RGB_MAX, round(r_out * ColorConstants.RGB_MAX)))
    g_out = max(0, min(ColorConstants.RGB_MAX, round(g_out * ColorConstants.RGB_MAX)))
    b_out = max(0, min(ColorConstants.RGB_MAX, round(b_out * ColorConstants.RGB_MAX)))

    return (r_out, g_out, b_out)


# =============================================================================
# Simulation Functions
# =============================================================================

def simulate_cvd(rgb: Tuple[int, int, int], deficiency_type: str) -> Tuple[int, int, int]:
    """
    Simulate how a color appears to someone with color vision deficiency.
    
    This transforms colors to show how they would appear to individuals with
    various types of color blindness. Useful for testing color schemes for
    accessibility.
    
    Args:
        rgb: RGB color tuple (0-255)
        deficiency_type: Type of CVD to simulate
            - 'protanopia' or 'protan': Red-blind
            - 'deuteranopia' or 'deutan': Green-blind
            - 'tritanopia' or 'tritan': Blue-blind
    
    Returns:
        RGB color as it would appear to someone with the deficiency (0-255)
    
    Example:
        >>> # See how red appears to someone with protanopia
        >>> simulate_cvd((255, 0, 0), 'protanopia')
        (145, 110, 0)  # Appears darker, yellowish-brown
        
        >>> # Test if two colors are distinguishable for deuteranopia
        >>> red_sim = simulate_cvd((255, 0, 0), 'deuteranopia')
        >>> green_sim = simulate_cvd((0, 255, 0), 'deuteranopia')
        >>> # If these are too similar, the colors may be confusing
    """
    return _apply_cvd_transform(rgb, deficiency_type, 'simulate')


def simulate_protanopia(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """
    Simulate protanopia (red-blindness).
    
    Protanopia is the absence of red cones (L-cones), affecting ~1% of males.
    Individuals with protanopia have difficulty distinguishing red from green,
    and red colors appear significantly darker.
    
    Args:
        rgb: RGB color tuple (0-255)
    
    Returns:
        RGB color as it appears to someone with protanopia (0-255)
    
    Example:
        >>> simulate_protanopia((255, 0, 0))  # Pure red
        (145, 110, 0)  # Appears dark yellow-brown
    """
    return simulate_cvd(rgb, 'protanopia')


def simulate_deuteranopia(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """
    Simulate deuteranopia (green-blindness).
    
    Deuteranopia is the absence of green cones (M-cones), affecting ~1% of males.
    This is the most common form of color blindness. Individuals have difficulty
    distinguishing red from green, but unlike protanopia, reds don't appear darker.
    
    Args:
        rgb: RGB color tuple (0-255)
    
    Returns:
        RGB color as it appears to someone with deuteranopia (0-255)
    
    Example:
        >>> simulate_deuteranopia((0, 255, 0))  # Pure green
        (159, 178, 0)  # Appears yellowish
    """
    return simulate_cvd(rgb, 'deuteranopia')


def simulate_tritanopia(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """
    Simulate tritanopia (blue-blindness).
    
    Tritanopia is the absence of blue cones (S-cones), affecting ~0.001% of
    the population. This is very rare. Individuals have difficulty distinguishing
    blue from yellow/green.
    
    Args:
        rgb: RGB color tuple (0-255)
    
    Returns:
        RGB color as it appears to someone with tritanopia (0-255)
    
    Example:
        >>> simulate_tritanopia((0, 0, 255))  # Pure blue
        (0, 172, 133)  # Appears cyan/turquoise
    """
    return simulate_cvd(rgb, 'tritanopia')


# =============================================================================
# Correction Functions
# =============================================================================

def correct_cvd(rgb: Tuple[int, int, int], deficiency_type: str) -> Tuple[int, int, int]:
    """
    Apply color correction for color vision deficiency.
    
    This transforms colors to improve discriminability for individuals with
    color blindness. The correction cannot restore missing color information,
    but can shift colors to utilize the remaining functional cone types more
    effectively.
    
    Note: Corrected images should be viewed by individuals with the specific
    deficiency - they will not look "correct" to people with normal color vision.
    
    Args:
        rgb: RGB color tuple (0-255)
        deficiency_type: Type of CVD to correct for
            - 'protanopia' or 'protan': Red-blind
            - 'deuteranopia' or 'deutan': Green-blind
            - 'tritanopia' or 'tritan': Blue-blind
    
    Returns:
        RGB color corrected for the deficiency (0-255)
    
    Example:
        >>> # Correct red for protanopia viewers
        >>> correct_cvd((255, 0, 0), 'protanopia')
        (255, 0, 77)  # Error shifted toward blue for contrast
        
        >>> # Improve green discriminability for deuteranopia
        >>> correct_cvd((0, 255, 0), 'deuteranopia')
        (29, 255, 48)  # Error shifted to add blue contrast
    """
    return _apply_cvd_transform(rgb, deficiency_type, 'correct')


def correct_protanopia(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """
    Correct colors for protanopia (red-blindness).
    
    Shifts reds toward orange/yellow to increase visibility and improve
    discrimination between red and green for red-blind individuals.
    
    Args:
        rgb: RGB color tuple (0-255)
    
    Returns:
        RGB color corrected for protanopia (0-255)
    
    Example:
        >>> correct_protanopia((255, 0, 0))  # Pure red
        (255, 0, 77)  # Error shifted toward blue for contrast
    """
    return correct_cvd(rgb, 'protanopia')


def correct_deuteranopia(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """
    Correct colors for deuteranopia (green-blindness).
    
    Adjusts greens and reds to be more distinguishable for green-blind
    individuals by utilizing blue channel contrast.
    
    Args:
        rgb: RGB color tuple (0-255)
    
    Returns:
        RGB color corrected for deuteranopia (0-255)
    
    Example:
        >>> correct_deuteranopia((0, 255, 0))  # Pure green
        (29, 255, 48)  # Error shifted to add blue contrast
    """
    return correct_cvd(rgb, 'deuteranopia')


def correct_tritanopia(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """
    Correct colors for tritanopia (blue-blindness).
    
    Modifies blues and yellows to increase contrast for blue-blind individuals
    by enhancing red/green channel differences.
    
    Args:
        rgb: RGB color tuple (0-255)
    
    Returns:
        RGB color corrected for tritanopia (0-255)
    
    Example:
        >>> correct_tritanopia((0, 0, 255))  # Pure blue
        (85, 0, 255)  # Error shifted toward red for contrast
    """
    return correct_cvd(rgb, 'tritanopia')

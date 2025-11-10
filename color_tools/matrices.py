"""
Color transformation matrices for various operations.

This module contains transformation matrices used throughout the color_tools package
for operations like color deficiency simulation/correction, chromatic adaptation, etc.

All matrices are documented with their sources and intended use.

⚠️  WARNING: These matrices are from peer-reviewed scientific research and should
    NOT be modified. Integrity verification is available via ColorConstants class.
"""

from __future__ import annotations
from typing import Tuple

# Type alias for 3x3 transformation matrices
Matrix3x3 = Tuple[Tuple[float, float, float], 
                  Tuple[float, float, float], 
                  Tuple[float, float, float]]


# =============================================================================
# Color Deficiency Simulation Matrices
# =============================================================================
# These matrices simulate how colors appear to individuals with various types
# of color vision deficiency (CVD). They transform RGB values from normal vision
# to the appearance for someone with the specified deficiency.
#
# Source: Viénot, Brettel, and Mollon (1999)
# "Digital video colourmaps for checking the legibility of displays by dichromats"
# http://vision.psychol.cam.ac.uk/jdmollon/papers/colourmaps.pdf
#
# Additional validation from:
# - Machado, Oliveira, and Fernandes (2009) - physiologically-based model
# - Colorspace R package by Ross Ihaka
# =============================================================================

# Protanopia - Red-blind (missing L-cones, ~1% of males)
# Difficulty distinguishing red from green, red appears darker
PROTANOPIA_SIMULATION: Matrix3x3 = (
    (0.56667, 0.43333, 0.00000),
    (0.55833, 0.44167, 0.00000),
    (0.00000, 0.24167, 0.75833)
)

# Deuteranopia - Green-blind (missing M-cones, ~1% of males)
# Difficulty distinguishing red from green, most common form
DEUTERANOPIA_SIMULATION: Matrix3x3 = (
    (0.62500, 0.37500, 0.00000),
    (0.70000, 0.30000, 0.00000),
    (0.00000, 0.30000, 0.70000)
)

# Tritanopia - Blue-blind (missing S-cones, ~0.001% of population)
# Difficulty distinguishing blue from yellow, very rare
TRITANOPIA_SIMULATION: Matrix3x3 = (
    (0.95000, 0.05000, 0.00000),
    (0.00000, 0.43333, 0.56667),
    (0.00000, 0.47500, 0.52500)
)


# =============================================================================
# Color Deficiency Correction Matrices
# =============================================================================
# These matrices attempt to shift colors so that individuals with color vision
# deficiency can better distinguish between colors that would otherwise appear
# similar. They work by enhancing contrast along the confusion axes.
#
# Note: Correction is inherently limited - it cannot restore missing color
# information, but can improve discriminability by shifting colors to utilize
# the remaining functional cone types.
#
# Source: Daltonization algorithm by Fidaner et al. (2005)
# "Analysis of Color Blindness" 
# http://scien.stanford.edu/pages/labsite/2005/psych221/projects/05/ofidaner/
#
# Correction approach:
# 1. Simulate the CVD appearance
# 2. Calculate the error (difference from original)
# 3. Shift colors in a direction that enhances discriminability
# =============================================================================

# Protanopia Correction
# Shifts reds toward orange/yellow to increase visibility for red-blind individuals
PROTANOPIA_CORRECTION: Matrix3x3 = (
    (0.00000, 0.00000, 0.00000),
    (0.70000, 1.00000, 0.00000),
    (0.70000, 0.00000, 1.00000)
)

# Deuteranopia Correction  
# Adjusts greens to be more distinguishable for green-blind individuals
DEUTERANOPIA_CORRECTION: Matrix3x3 = (
    (1.00000, 0.70000, 0.00000),
    (0.00000, 0.00000, 0.00000),
    (0.00000, 0.70000, 1.00000)
)

# Tritanopia Correction
# Modifies blues and yellows to increase contrast for blue-blind individuals
TRITANOPIA_CORRECTION: Matrix3x3 = (
    (1.00000, 0.00000, 0.70000),
    (0.00000, 1.00000, 0.70000),
    (0.00000, 0.00000, 0.00000)
)


# =============================================================================
# Matrix Utility Functions
# =============================================================================

def multiply_matrix_vector(matrix: Matrix3x3, vector: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    Multiply a 3x3 matrix by a 3D vector.
    
    This is a helper function for applying transformation matrices to RGB values.
    
    Args:
        matrix: 3x3 transformation matrix
        vector: 3D vector (e.g., normalized RGB values)
    
    Returns:
        Transformed 3D vector
    
    Example:
        >>> matrix = ((1, 0, 0), (0, 1, 0), (0, 0, 1))  # Identity matrix
        >>> vector = (0.5, 0.3, 0.8)
        >>> multiply_matrix_vector(matrix, vector)
        (0.5, 0.3, 0.8)
    """
    r, g, b = vector
    return (
        matrix[0][0] * r + matrix[0][1] * g + matrix[0][2] * b,
        matrix[1][0] * r + matrix[1][1] * g + matrix[1][2] * b,
        matrix[2][0] * r + matrix[2][1] * g + matrix[2][2] * b
    )


def get_simulation_matrix(deficiency_type: str) -> Matrix3x3:
    """
    Get the simulation matrix for a specific color deficiency type.
    
    Args:
        deficiency_type: Type of color deficiency
            - 'protanopia' or 'protan': Red-blind
            - 'deuteranopia' or 'deutan': Green-blind  
            - 'tritanopia' or 'tritan': Blue-blind
    
    Returns:
        3x3 transformation matrix for simulating the deficiency
    
    Raises:
        ValueError: If deficiency_type is not recognized
    
    Example:
        >>> matrix = get_simulation_matrix('protanopia')
        >>> # Use matrix to transform colors
    """
    deficiency = deficiency_type.lower()
    
    if deficiency in ('protanopia', 'protan'):
        return PROTANOPIA_SIMULATION
    elif deficiency in ('deuteranopia', 'deutan'):
        return DEUTERANOPIA_SIMULATION
    elif deficiency in ('tritanopia', 'tritan'):
        return TRITANOPIA_SIMULATION
    else:
        raise ValueError(
            f"Unknown deficiency type: {deficiency_type}. "
            f"Must be one of: protanopia, deuteranopia, tritanopia"
        )


def get_correction_matrix(deficiency_type: str) -> Matrix3x3:
    """
    Get the correction matrix for a specific color deficiency type.
    
    Args:
        deficiency_type: Type of color deficiency
            - 'protanopia' or 'protan': Red-blind
            - 'deuteranopia' or 'deutan': Green-blind
            - 'tritanopia' or 'tritan': Blue-blind
    
    Returns:
        3x3 transformation matrix for correcting colors for the deficiency
    
    Raises:
        ValueError: If deficiency_type is not recognized
    
    Example:
        >>> matrix = get_correction_matrix('deuteranopia')
        >>> # Use matrix to transform colors for better discriminability
    """
    deficiency = deficiency_type.lower()
    
    if deficiency in ('protanopia', 'protan'):
        return PROTANOPIA_CORRECTION
    elif deficiency in ('deuteranopia', 'deutan'):
        return DEUTERANOPIA_CORRECTION
    elif deficiency in ('tritanopia', 'tritan'):
        return TRITANOPIA_CORRECTION
    else:
        raise ValueError(
            f"Unknown deficiency type: {deficiency_type}. "
            f"Must be one of: protanopia, deuteranopia, tritanopia"
        )

"""
Color transformation matrices for various operations.

This module contains transformation matrices used throughout the color_tools package
for operations like color deficiency simulation/correction, chromatic adaptation, etc.

All matrices are documented with their sources and intended use.

⚠️  WARNING: These matrices are from peer-reviewed scientific research and should
    NOT be modified. Integrity verification is available via ColorConstants class.
"""

from __future__ import annotations
from typing import Tuple, TypeAlias

# Type alias for 3x3 transformation matrices
Matrix3x3: TypeAlias = Tuple[Tuple[float, float, float],
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

#: Protanopia simulation matrix — Red-blind (missing L-cones, ~1% of males).
#: Difficulty distinguishing red from green; red appears darker.
#: Source: Viénot, Brettel, and Mollon (1999)
PROTANOPIA_SIMULATION: Matrix3x3 = (
    (0.56667, 0.43333, 0.00000),
    (0.55833, 0.44167, 0.00000),
    (0.00000, 0.24167, 0.75833)
)

#: Deuteranopia simulation matrix — Green-blind (missing M-cones, ~1% of males).
#: Most common form of color vision deficiency.
#: Source: Viénot, Brettel, and Mollon (1999)
DEUTERANOPIA_SIMULATION: Matrix3x3 = (
    (0.62500, 0.37500, 0.00000),
    (0.70000, 0.30000, 0.00000),
    (0.00000, 0.30000, 0.70000)
)

#: Tritanopia simulation matrix — Blue-blind (missing S-cones, ~0.001% of population).
#: Difficulty distinguishing blue from yellow; very rare.
#: Source: Viénot, Brettel, and Mollon (1999)
TRITANOPIA_SIMULATION: Matrix3x3 = (
    (0.95000, 0.05000, 0.00000),
    (0.00000, 0.43333, 0.56667),
    (0.00000, 0.47500, 0.52500)
)

#: Combined (all-types) simulation matrix — element-wise average of the three
#: deficiency simulation matrices.  Each row still sums to 1.0, so it remains
#: a valid colour projection.  Useful as a "worst-case" accessibility diagnostic:
#: colours that appear similar after this transform are confusable to at least
#: one of the three major CVD types simultaneously.
#: Computed as: (PROTANOPIA_SIMULATION + DEUTERANOPIA_SIMULATION + TRITANOPIA_SIMULATION) / 3
ALL_SIMULATION: Matrix3x3 = (
    (0.71389, 0.28611, 0.00000),
    (0.41944, 0.39167, 0.18889),
    (0.00000, 0.33889, 0.66111)
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

#: Protanopia correction matrix — shifts reds toward orange/yellow to increase
#: visibility for red-blind individuals.
#: Source: Fidaner et al. (2005) daltonization algorithm
PROTANOPIA_CORRECTION: Matrix3x3 = (
    (0.00000, 0.00000, 0.00000),
    (0.70000, 1.00000, 0.00000),
    (0.70000, 0.00000, 1.00000)
)

#: Deuteranopia correction matrix — adjusts greens to be more distinguishable
#: for green-blind individuals.
#: Source: Fidaner et al. (2005) daltonization algorithm
DEUTERANOPIA_CORRECTION: Matrix3x3 = (
    (1.00000, 0.70000, 0.00000),
    (0.00000, 0.00000, 0.00000),
    (0.00000, 0.70000, 1.00000)
)

#: Tritanopia correction matrix — modifies blues and yellows to increase contrast
#: for blue-blind individuals.
#: Source: Fidaner et al. (2005) daltonization algorithm
TRITANOPIA_CORRECTION: Matrix3x3 = (
    (1.00000, 0.00000, 0.70000),
    (0.00000, 1.00000, 0.70000),
    (0.00000, 0.00000, 0.00000)
)

#: Combined (all-types) correction matrix — element-wise average of the three
#: deficiency correction matrices.  Redistributes the error signal equally across
#: all three channels, improving discriminability for all CVD types simultaneously.
#: Neutral colours (white, grey, black) are always preserved because the correction
#: is applied to the error signal (original − simulated), not to the original.
#: Computed as: (PROTANOPIA_CORRECTION + DEUTERANOPIA_CORRECTION + TRITANOPIA_CORRECTION) / 3
ALL_CORRECTION: Matrix3x3 = (
    (0.66667, 0.23333, 0.23333),
    (0.23333, 0.66667, 0.23333),
    (0.23333, 0.23333, 0.66667)
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
            - 'all': Combined average of all three deficiency types
    
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
    elif deficiency == 'all':
        return ALL_SIMULATION
    else:
        raise ValueError(
            f"Unknown deficiency type: {deficiency_type}. "
            f"Must be one of: protanopia, deuteranopia, tritanopia, all"
        )


def get_correction_matrix(deficiency_type: str) -> Matrix3x3:
    """
    Get the correction matrix for a specific color deficiency type.
    
    Args:
        deficiency_type: Type of color deficiency
            - 'protanopia' or 'protan': Red-blind
            - 'deuteranopia' or 'deutan': Green-blind
            - 'tritanopia' or 'tritan': Blue-blind
            - 'all': Combined average of all three deficiency types
    
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
    elif deficiency == 'all':
        return ALL_CORRECTION
    else:
        raise ValueError(
            f"Unknown deficiency type: {deficiency_type}. "
            f"Must be one of: protanopia, deuteranopia, tritanopia, all"
        )

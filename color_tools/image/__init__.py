"""
Image processing module for color_tools.

This module provides image color analysis and manipulation tools,
primarily designed for optimizing images for Hueforge 3D printing.

Requires Pillow: pip install color-match-tools[image]

Public API:
-----------
Functions:
    extract_unique_colors - Extract dominant colors using k-means (simplified API)
    extract_color_clusters - Extract color clusters with full data (pixel assignments)
    redistribute_luminance - Redistribute L values evenly for Hueforge
    format_color_change_report - Generate human-readable color change report
    l_value_to_hueforge_layer - Convert L value to Hueforge layer number

Data Classes:
    ColorCluster - Cluster with centroid and pixel assignments
    ColorChange - Before/after color change with Delta E

Example:
--------
    >>> from color_tools.image import extract_color_clusters, redistribute_luminance
    >>> 
    >>> # Extract 10 dominant colors from image
    >>> clusters = extract_color_clusters("photo.jpg", n_colors=10)
    >>> 
    >>> # Redistribute luminance for Hueforge
    >>> colors = [c.centroid_rgb for c in clusters]
    >>> changes = redistribute_luminance(colors)
    >>> 
    >>> # Show layer assignments
    >>> for change in changes:
    ...     print(f"Layer {change.hueforge_layer}: RGB{change.new_rgb}")
"""

from __future__ import annotations

# Check if Pillow is available
try:
    from .analysis import (
        ColorCluster,
        ColorChange,
        extract_unique_colors,
        extract_color_clusters,
        redistribute_luminance,
        format_color_change_report,
        l_value_to_hueforge_layer,
    )
    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False
    
    # Provide helpful error messages
    def _not_available(*args, **kwargs):
        raise ImportError(
            "Image processing requires Pillow. "
            "Install with: pip install color-match-tools[image]"
        )
    
    extract_unique_colors = _not_available
    extract_color_clusters = _not_available
    redistribute_luminance = _not_available
    format_color_change_report = _not_available
    l_value_to_hueforge_layer = _not_available
    
    # Dummy classes for type hints
    class ColorCluster:  # type: ignore
        pass
    
    class ColorChange:  # type: ignore
        pass


__all__ = [
    'IMAGE_AVAILABLE',
    'ColorCluster',
    'ColorChange',
    'extract_unique_colors',
    'extract_color_clusters',
    'redistribute_luminance',
    'format_color_change_report',
    'l_value_to_hueforge_layer',
]

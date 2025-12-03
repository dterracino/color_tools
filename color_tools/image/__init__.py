"""
Image processing module for color_tools.

This module provides image color analysis and manipulation tools:
- General image analysis (basic.py)  
- HueForge 3D printing optimization (analysis.py)

Requires Pillow: pip install color-match-tools[image]

Example:
--------
    >>> from color_tools.image import (
    ...     count_unique_colors, analyze_brightness,
    ...     simulate_cvd_image, quantize_image_to_palette
    ... )
    >>> 
    >>> # Count colors in an image
    >>> total = count_unique_colors("photo.jpg")
    >>> print(f"Found {total} unique colors")
    Found 42387 unique colors
    >>> 
    >>> # Analyze image quality
    >>> brightness = analyze_brightness("photo.jpg")
    >>> print(f"Brightness: {brightness['mean_brightness']:.1f} ({brightness['assessment']})")
    Brightness: 127.3 (normal)
    >>> 
    >>> # Test accessibility with CVD simulation
    >>> sim_image = simulate_cvd_image("chart.png", "deuteranopia")
    >>> sim_image.save("chart_colorblind_view.png")
    >>> 
    >>> # Create retro-style artwork
    >>> retro = quantize_image_to_palette("photo.jpg", "cga4", dither=True)
    >>> retro.save("retro_cga.png")
    >>> 
    >>> # Extract dominant colors for Hueforge
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
    from .basic import (
        count_unique_colors,
        get_color_histogram,
        get_dominant_color,
        is_indexed_mode,
        analyze_brightness,
        analyze_contrast,
        analyze_noise_level,
        analyze_dynamic_range,
        transform_image,
        simulate_cvd_image,
        correct_cvd_image,
        quantize_image_to_palette,
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
    
    # HueForge functions
    extract_unique_colors = _not_available
    extract_color_clusters = _not_available
    redistribute_luminance = _not_available
    format_color_change_report = _not_available
    l_value_to_hueforge_layer = _not_available
    
    # Basic analysis functions
    count_unique_colors = _not_available
    get_color_histogram = _not_available
    get_dominant_color = _not_available
    is_indexed_mode = _not_available
    analyze_brightness = _not_available
    analyze_contrast = _not_available
    analyze_noise_level = _not_available
    analyze_dynamic_range = _not_available
    
    # Image transformation functions
    transform_image = _not_available
    simulate_cvd_image = _not_available
    correct_cvd_image = _not_available
    quantize_image_to_palette = _not_available
    
    # Dummy classes for type hints - use Any to avoid type conflicts
    from typing import Any
    ColorCluster: type[Any] = type('ColorCluster', (), {})
    ColorChange: type[Any] = type('ColorChange', (), {})

__all__ = [
    'IMAGE_AVAILABLE',
    # Data classes
    'ColorCluster',
    'ColorChange',
    # HueForge functions
    'extract_unique_colors',
    'extract_color_clusters',
    'redistribute_luminance',
    'format_color_change_report',
    'l_value_to_hueforge_layer',
    # Basic analysis functions
    'count_unique_colors',
    'get_color_histogram',
    'get_dominant_color',
    'is_indexed_mode',
    'analyze_brightness',
    'analyze_contrast', 
    'analyze_noise_level',
    'analyze_dynamic_range',
    # Image transformation functions
    'transform_image',
    'simulate_cvd_image',
    'correct_cvd_image',
    'quantize_image_to_palette',
]

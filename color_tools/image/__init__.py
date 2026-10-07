"""
Image processing module for color_tools.

This module provides image color analysis and manipulation tools:
- Format Conversion: Convert between PNG, JPEG, WebP, HEIC, AVIF, etc. (conversion.py)
- Watermarking: Add text, image, or SVG watermarks (watermark.py)
- Color Analysis: Extract dominant colors with K-means clustering (analysis.py)
- Perceptual Dominance: Find visually dominant colors with saliency-aware analysis (dominance.py)
- HueForge 3D printing: Luminance redistribution for multi-color printing (analysis.py)
- CVD Operations: Simulate/correct color vision deficiencies (basic.py)
- Palette Quantization: Convert to retro palettes with dithering (basic.py)
- General Analysis: Count colors, brightness, contrast, noise (basic.py)

Requires Pillow: pip install color-match-tools[image]

Example:
--------
    >>> from color_tools.image import (
    ...     convert_image, add_watermark,
    ...     count_unique_colors, analyze_brightness,
    ...     simulate_cvd_image, quantize_image_to_palette
    ... )
    >>> 
    >>> # Convert image formats (auto-generates output filename)
    >>> convert_image("photo.webp", output_format="png")  # Creates photo.png
    >>> convert_image("photo.jpg", output_format="webp", lossless=True)
    PosixPath('photo.webp')
    >>> 
    >>> # Add watermark
    >>> add_text_watermark(
    ...     "photo.jpg",
    ...     text="© 2025 MyBrand",
    ...     position="bottom-right",
    ...     output_path="watermarked.jpg"
    ... )
    PosixPath('watermarked.jpg')
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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .analysis import (
        ColorChange,
        ColorCluster,
        extract_color_clusters,
        extract_unique_colors,
        format_color_change_report,
        l_value_to_hueforge_layer,
        quantize_image_hyab,
        redistribute_luminance,
    )
    from .basic import (
        analyze_brightness,
        analyze_contrast,
        analyze_dynamic_range,
        analyze_noise_level,
        correct_cvd_image,
        count_unique_colors,
        get_color_histogram,
        get_dominant_color,
        is_indexed_mode,
        quantize_image_to_palette,
        simulate_cvd_image,
        transform_image,
    )
    from .blend import BLEND_MODES, blend_images
    from .conversion import convert_image, get_supported_formats
    from .dominance import (
        DominanceAnalysis,
        DominantColor,
        analyze_dominant_colors,
        dominant_colors,
        dominant_colors_to_palette,
    )
    from .watermark import (
        add_image_watermark,
        add_svg_watermark,
        add_text_watermark,
    )

    IMAGE_AVAILABLE: bool
else:
    try:
        from .analysis import (
            ColorChange,
            ColorCluster,
            extract_color_clusters,
            extract_unique_colors,
            format_color_change_report,
            l_value_to_hueforge_layer,
            quantize_image_hyab,
            redistribute_luminance,
        )
        from .basic import (
            analyze_brightness,
            analyze_contrast,
            analyze_dynamic_range,
            analyze_noise_level,
            correct_cvd_image,
            count_unique_colors,
            get_color_histogram,
            get_dominant_color,
            is_indexed_mode,
            quantize_image_to_palette,
            simulate_cvd_image,
            transform_image,
        )
        from .blend import BLEND_MODES, blend_images
        from .conversion import convert_image, get_supported_formats
        from .dominance import (
            DominanceAnalysis,
            DominantColor,
            analyze_dominant_colors,
            dominant_colors,
            dominant_colors_to_palette,
        )
        from .watermark import (
            add_image_watermark,
            add_svg_watermark,
            add_text_watermark,
        )

        IMAGE_AVAILABLE = True
    except ImportError:
        from typing import Any

        IMAGE_AVAILABLE = False

        def _not_available(*args: object, **kwargs: object) -> None:
            raise ImportError(
                "Image processing requires Pillow. "
                "Install with: pip install color-match-tools[image]"
            )

        extract_unique_colors = _not_available
        extract_color_clusters = _not_available
        quantize_image_hyab = _not_available
        redistribute_luminance = _not_available
        format_color_change_report = _not_available
        l_value_to_hueforge_layer = _not_available
        analyze_dominant_colors = _not_available
        dominant_colors = _not_available
        dominant_colors_to_palette = _not_available
        count_unique_colors = _not_available
        get_color_histogram = _not_available
        get_dominant_color = _not_available
        is_indexed_mode = _not_available
        analyze_brightness = _not_available
        analyze_contrast = _not_available
        analyze_noise_level = _not_available
        analyze_dynamic_range = _not_available
        transform_image = _not_available
        simulate_cvd_image = _not_available
        correct_cvd_image = _not_available
        quantize_image_to_palette = _not_available
        add_text_watermark = _not_available
        add_image_watermark = _not_available
        add_svg_watermark = _not_available
        convert_image = _not_available
        get_supported_formats = _not_available
        blend_images = _not_available
        BLEND_MODES: dict[str, Any] = {}
        ColorCluster: type[Any] = type("ColorCluster", (), {})
        ColorChange: type[Any] = type("ColorChange", (), {})
        DominantColor: type[Any] = type("DominantColor", (), {})
        DominanceAnalysis: type[Any] = type("DominanceAnalysis", (), {})

# SimplePNGWriter is always available — no Pillow required
from .png_writer import SimplePNGWriter

__all__ = [
    'IMAGE_AVAILABLE',
    # Stdlib-only PNG writer (no Pillow required)
    'SimplePNGWriter',
    # Data classes
    'ColorCluster',
    'ColorChange',
    'DominantColor',
    'DominanceAnalysis',
    # HueForge functions
    'extract_unique_colors',
    'extract_color_clusters',
    'quantize_image_hyab',
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
    'analyze_dominant_colors',
    'dominant_colors',
    'dominant_colors_to_palette',
    # Image transformation functions
    'transform_image',
    'simulate_cvd_image',
    'correct_cvd_image',
    'quantize_image_to_palette',
    # Watermarking functions
    'add_text_watermark',
    'add_image_watermark',
    'add_svg_watermark',
    # Conversion functions
    'convert_image',
    'get_supported_formats',
    # Blend functions
    'blend_images',
    'BLEND_MODES',
]

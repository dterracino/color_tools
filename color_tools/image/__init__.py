"""
Image processing tools for color analysis and manipulation.

The optional ``image`` extra provides format conversion, watermarking, color
analysis, perceptual dominance, CVD operations, palette quantization, and image
blending. Install the complete feature set with::

    pip install color-match-tools[image]

The extra includes Pillow, NumPy, scikit-image, pillow-heif, CairoSVG, OpenCV,
and scikit-learn. Individual operations import only their owning submodule and
may require only part of that set.

Examples:
---------
    >>> from color_tools.image import (  # doctest: +SKIP
    ...     add_image_watermark,
    ...     add_svg_watermark,
    ...     add_text_watermark,
    ...     analyze_brightness,
    ...     convert_image,
    ...     count_unique_colors,
    ...     extract_color_clusters,
    ...     quantize_image_to_palette,
    ...     redistribute_luminance,
    ...     simulate_cvd_image,
    ... )
    >>> from PIL import Image  # doctest: +SKIP

    Convert an image and retain the returned output path:

    >>> converted = convert_image(  # doctest: +SKIP
    ...     "photo.jpg", output_format="webp", lossless=True
    ... )
    >>> print(converted)  # doctest: +SKIP
    photo.webp

    Watermark functions accept and return Pillow images:

    >>> image = Image.open("photo.jpg")  # doctest: +SKIP
    >>> watermarked = add_text_watermark(  # doctest: +SKIP
    ...     image,
    ...     text="© 2026 MyBrand",
    ...     position="bottom-right",
    ... )
    >>> watermarked.save("watermarked.png")  # doctest: +SKIP

    Analyze, transform, and quantize images:

    >>> total = count_unique_colors("photo.jpg")  # doctest: +SKIP
    >>> brightness = analyze_brightness("photo.jpg")  # doctest: +SKIP
    >>> simulated = simulate_cvd_image(  # doctest: +SKIP
    ...     "chart.png", "deuteranopia"
    ... )
    >>> retro = quantize_image_to_palette(  # doctest: +SKIP
    ...     "photo.jpg", "cga4", dither=True
    ... )

    Extract colors and prepare HueForge layer assignments:

    >>> clusters = extract_color_clusters(  # doctest: +SKIP
    ...     "photo.jpg", n_colors=10
    ... )
    >>> changes = redistribute_luminance(  # doctest: +SKIP
    ...     [cluster.centroid_rgb for cluster in clusters]
    ... )
"""

from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .analysis import (
        ColorChange as ColorChange,
        ColorCluster as ColorCluster,
        extract_color_clusters as extract_color_clusters,
        extract_unique_colors as extract_unique_colors,
        format_color_change_report as format_color_change_report,
        l_value_to_hueforge_layer as l_value_to_hueforge_layer,
        quantize_image_hyab as quantize_image_hyab,
        redistribute_luminance as redistribute_luminance,
    )
    from .basic import (
        analyze_brightness as analyze_brightness,
        analyze_contrast as analyze_contrast,
        analyze_dynamic_range as analyze_dynamic_range,
        analyze_noise_level as analyze_noise_level,
        correct_cvd_image as correct_cvd_image,
        count_unique_colors as count_unique_colors,
        get_color_histogram as get_color_histogram,
        get_dominant_color as get_dominant_color,
        is_indexed_mode as is_indexed_mode,
        quantize_image_to_palette as quantize_image_to_palette,
        simulate_cvd_image as simulate_cvd_image,
        transform_image as transform_image,
    )
    from .blend import BLEND_MODES as BLEND_MODES
    from .blend import blend_images as blend_images
    from .conversion import convert_image as convert_image
    from .conversion import get_supported_formats as get_supported_formats
    from .dominance import (
        DominanceAnalysis as DominanceAnalysis,
        DominantColor as DominantColor,
        analyze_dominant_colors as analyze_dominant_colors,
        dominant_colors as dominant_colors,
        dominant_colors_to_palette as dominant_colors_to_palette,
    )
    from .watermark import (
        add_image_watermark as add_image_watermark,
        add_svg_watermark as add_svg_watermark,
        add_text_watermark as add_text_watermark,
    )


_EXPORTS: dict[str, str] = {
    # Data classes
    "ColorCluster": "analysis",
    "ColorChange": "analysis",
    "DominantColor": "dominance",
    "DominanceAnalysis": "dominance",
    # HueForge functions
    "extract_unique_colors": "analysis",
    "extract_color_clusters": "analysis",
    "quantize_image_hyab": "analysis",
    "redistribute_luminance": "analysis",
    "format_color_change_report": "analysis",
    "l_value_to_hueforge_layer": "analysis",
    # Basic analysis functions
    "count_unique_colors": "basic",
    "get_color_histogram": "basic",
    "get_dominant_color": "basic",
    "is_indexed_mode": "basic",
    "analyze_brightness": "basic",
    "analyze_contrast": "basic",
    "analyze_noise_level": "basic",
    "analyze_dynamic_range": "basic",
    "analyze_dominant_colors": "dominance",
    "dominant_colors": "dominance",
    "dominant_colors_to_palette": "dominance",
    # Image transformation functions
    "transform_image": "basic",
    "simulate_cvd_image": "basic",
    "correct_cvd_image": "basic",
    "quantize_image_to_palette": "basic",
    # Watermarking functions
    "add_text_watermark": "watermark",
    "add_image_watermark": "watermark",
    "add_svg_watermark": "watermark",
    # Conversion functions
    "convert_image": "conversion",
    "get_supported_formats": "conversion",
    # Blend functions
    "blend_images": "blend",
    "BLEND_MODES": "blend",
}

_OPTIONAL_DEPENDENCIES: dict[str, str] = {
    "PIL": "Pillow",
    "numpy": "NumPy",
    "skimage": "scikit-image",
    "pillow_heif": "pillow-heif",
    "cairosvg": "CairoSVG",
    "cv2": "OpenCV",
    "sklearn": "scikit-learn",
}


def _module_available(module_name: str) -> bool:
    """Return whether an optional top-level module can be discovered."""
    try:
        return find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


# Compatibility flag with deliberately narrow semantics: Pillow is discoverable.
IMAGE_AVAILABLE = _module_available("PIL")

__all__ = [
    "IMAGE_AVAILABLE",
    "ColorCluster",
    "ColorChange",
    "DominantColor",
    "DominanceAnalysis",
    "extract_unique_colors",
    "extract_color_clusters",
    "quantize_image_hyab",
    "redistribute_luminance",
    "format_color_change_report",
    "l_value_to_hueforge_layer",
    "count_unique_colors",
    "get_color_histogram",
    "get_dominant_color",
    "is_indexed_mode",
    "analyze_brightness",
    "analyze_contrast",
    "analyze_noise_level",
    "analyze_dynamic_range",
    "analyze_dominant_colors",
    "dominant_colors",
    "dominant_colors_to_palette",
    "transform_image",
    "simulate_cvd_image",
    "correct_cvd_image",
    "quantize_image_to_palette",
    "add_text_watermark",
    "add_image_watermark",
    "add_svg_watermark",
    "convert_image",
    "get_supported_formats",
    "blend_images",
    "BLEND_MODES",
]


def __getattr__(name: str) -> object:
    """Load a public image export from its owning submodule on first access."""
    submodule_name = _EXPORTS.get(name)
    if submodule_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    try:
        submodule = import_module(f".{submodule_name}", __name__)
    except ImportError as exc:
        dependency_name = _OPTIONAL_DEPENDENCIES.get(exc.name or "")
        if dependency_name is None:
            raise
        raise ImportError(
            f"{dependency_name} is required to access "
            f"{__name__}.{name}. Install with: "
            "pip install color-match-tools[image]"
        ) from exc

    value = cast(object, getattr(submodule, name))
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return module globals and lazy public exports for interactive tools."""
    return sorted(set(globals()) | set(__all__))

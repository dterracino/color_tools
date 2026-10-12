"""
Watermarking functionality for images.

This module provides tools for adding text, image, and SVG watermarks to images
with support for positioning, transparency, custom fonts, and text styling.

Functions:
----------
    add_text_watermark: Add text watermark with custom fonts and styling
    add_image_watermark: Add image (PNG) watermark with transparency
    add_svg_watermark: Add SVG watermark (requires cairosvg)
    
Example:
--------
    >>> from color_tools.image import add_text_watermark  # doctest: +SKIP
    >>> from PIL import Image  # doctest: +SKIP

    >>> # Add simple text watermark
    >>> img = Image.open("photo.jpg")  # doctest: +SKIP
    >>> result = add_text_watermark(  # doctest: +SKIP
    ...     img, 
    ...     text="© 2025 My Brand",
    ...     position="bottom-right",
    ...     font_size=24,
    ...     color=(255, 255, 255),
    ...     opacity=0.8
    ... )
    >>> result.save("watermarked.png")  # doctest: +SKIP

    >>> # Add text with stroke outline
    >>> result = add_text_watermark(  # doctest: +SKIP
    ...     img,
    ...     text="SAMPLE",
    ...     position="center",
    ...     font_size=72,
    ...     color=(255, 255, 255),
    ...     stroke_color=(0, 0, 0),
    ...     stroke_width=3,
    ...     opacity=0.5
    ... )

    >>> # Add logo watermark from SVG
    >>> from color_tools.image import add_svg_watermark  # doctest: +SKIP
    >>> result = add_svg_watermark(  # doctest: +SKIP
    ...     img,
    ...     svg_path="logo.svg",
    ...     position="top-left",
    ...     scale=0.2,
    ...     opacity=0.7
    ... )
"""

from __future__ import annotations

import io
import math
from pathlib import Path
from typing import Literal, Protocol, cast

from PIL import Image, ImageDraw, ImageFont

# Position type for watermark placement
Position = Literal[
    "top-left", "top-center", "top-right",
    "center-left", "center", "center-right",
    "bottom-left", "bottom-center", "bottom-right"
]


class _SVGToPNG(Protocol):
    """Typed portion of CairoSVG used by SVG watermark conversion."""

    def __call__(
        self,
        *,
        url: str,
        output_width: int | None,
        output_height: int | None,
        scale: float,
    ) -> bytes | None: ...



def _get_fonts_directory() -> Path:
    """Get the path to the fonts directory in the package."""
    return Path(__file__).parent / "fonts"


def _load_font(
    font_name: str | None = None,
    font_file: str | None = None,
    size: int = 20
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """
    Load a font for text rendering.
    
    Args:
        font_name: System font name (e.g., "Arial", "Times New Roman")
        font_file: Custom font file path or filename (looks in fonts/ if no path)
        size: Font size in points
        
    Returns:
        Loaded font object
        
    Raises:
        ValueError: If both font_name and font_file are specified
        FileNotFoundError: If specified font file cannot be found
    """
    if font_name and font_file:
        raise ValueError("Cannot specify both font_name and font_file")
    
    # Load custom font file
    if font_file:
        font_path = Path(font_file)
        
        # If just a filename (no path separators), look in fonts directory
        if not font_path.is_absolute() and str(font_path) == font_path.name:
            font_path = _get_fonts_directory() / font_path
        
        if not font_path.exists():
            raise FileNotFoundError(f"Font file not found: {font_path}")
        
        try:
            return ImageFont.truetype(str(font_path), size)
        except Exception as exc:
            raise ValueError(
                f"Failed to load font file {font_path}: {exc}"
            ) from exc
    
    # Load system font by name
    if font_name:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception as initial_error:
            # Try with common font file extensions
            for ext in ['.ttf', '.otf', '.TTF', '.OTF']:
                try:
                    return ImageFont.truetype(font_name + ext, size)
                except Exception:
                    continue
            raise ValueError(
                f"Could not find system font: {font_name}"
            ) from initial_error
    
    return ImageFont.load_default()


def _calculate_position(
    image_size: tuple[int, int],
    watermark_size: tuple[int, int],
    position: Position | tuple[int, int],
    margin: int = 10
) -> tuple[int, int]:
    """
    Calculate the pixel coordinates for watermark placement.
    
    Args:
        image_size: (width, height) of base image
        watermark_size: (width, height) of watermark
        position: Position name or (x, y) coordinates
        margin: Margin from edges in pixels (for preset positions)
        
    Returns:
        (x, y) coordinates for top-left corner of watermark

    Raises:
        ValueError: If a named position is not one of the supported presets
    """
    img_w, img_h = image_size
    mark_w, mark_h = watermark_size
    
    # If position is a tuple, use it directly
    if isinstance(position, tuple):
        return position
    
    # Calculate preset positions with margins
    positions_map = {
        "top-left": (margin, margin),
        "top-center": ((img_w - mark_w) // 2, margin),
        "top-right": (img_w - mark_w - margin, margin),
        "center-left": (margin, (img_h - mark_h) // 2),
        "center": ((img_w - mark_w) // 2, (img_h - mark_h) // 2),
        "center-right": (img_w - mark_w - margin, (img_h - mark_h) // 2),
        "bottom-left": (margin, img_h - mark_h - margin),
        "bottom-center": ((img_w - mark_w) // 2, img_h - mark_h - margin),
        "bottom-right": (img_w - mark_w - margin, img_h - mark_h - margin),
    }
    
    if position not in positions_map:
        valid_positions = ", ".join(positions_map)
        raise ValueError(
            f"Unknown watermark position {position!r}. "
            f"Expected one of: {valid_positions}"
        )

    return positions_map[position]


def _validate_opacity(opacity: float) -> None:
    """Validate a watermark opacity on the inclusive unit interval."""
    if not math.isfinite(opacity) or not 0.0 <= opacity <= 1.0:
        raise ValueError(f"opacity must be between 0.0 and 1.0, got {opacity}")


def _validate_scale(scale: float) -> None:
    """Validate a positive watermark scale factor."""
    if not math.isfinite(scale) or not scale > 0.0:
        raise ValueError(f"scale must be greater than 0.0, got {scale}")


def _apply_opacity(watermark: Image.Image, opacity: float) -> Image.Image:
    """Return an RGBA watermark with its alpha channel scaled by opacity."""
    if opacity == 1.0:
        return watermark

    red, green, blue, alpha = watermark.split()
    scaled_alpha = alpha.point(lambda value: int(value * opacity))
    return Image.merge("RGBA", (red, green, blue, scaled_alpha))


def _composite_at(
    image: Image.Image,
    watermark: Image.Image,
    position: Position | tuple[int, int],
    margin: int,
) -> Image.Image:
    """Composite an RGBA watermark onto an RGBA image at a chosen position."""
    coordinates = _calculate_position(
        image.size,
        watermark.size,
        position,
        margin,
    )
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay.paste(watermark, coordinates, watermark)
    return Image.alpha_composite(image, overlay)


def add_text_watermark(
    image: Image.Image,
    text: str,
    position: Position | tuple[int, int] = "bottom-right",
    font_name: str | None = None,
    font_file: str | None = None,
    font_size: int = 24,
    color: tuple[int, int, int] = (255, 255, 255),
    opacity: float = 0.8,
    stroke_color: tuple[int, int, int] | None = None,
    stroke_width: int = 0,
    margin: int = 10
) -> Image.Image:
    """
    Add a text watermark to an image.
    
    Args:
        image: PIL Image to watermark
        text: Text to display
        position: Position preset or (x, y) coordinates
        font_name: System font name (e.g., "Arial")
        font_file: Custom font file (path or filename in fonts/)
        font_size: Font size in points
        color: Text color as (R, G, B)
        opacity: Opacity from 0.0 (transparent) to 1.0 (opaque)
        stroke_color: Outline color as (R, G, B), or None for no stroke
        stroke_width: Outline width in pixels (0 for no stroke)
        margin: Margin from edges for preset positions
        
    Returns:
        New image with watermark applied

    Raises:
        ValueError: If opacity is outside 0.0 through 1.0, the named position
            is invalid, or the requested font cannot be loaded
        
    Example:
        >>> img = Image.open("photo.jpg")  # doctest: +SKIP
        >>> result = add_text_watermark(  # doctest: +SKIP
        ...     img,
        ...     text="© 2025",
        ...     position="bottom-right",
        ...     font_file="Roboto-Bold.ttf",
        ...     font_size=32,
        ...     color=(255, 255, 255),
        ...     stroke_color=(0, 0, 0),
        ...     stroke_width=2,
        ...     opacity=0.7
        ... )
    """
    _validate_opacity(opacity)

    # Ensure image is in RGBA mode for transparency
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Create transparent overlay for watermark
    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Load font
    font = _load_font(font_name=font_name, font_file=font_file, size=font_size)
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate position
    x, y = _calculate_position(
        image.size,
        (int(text_width), int(text_height)),
        position,
        margin
    )
    
    # Adjust for bbox offset
    x -= bbox[0]
    y -= bbox[1]
    
    # Apply opacity to colors
    alpha = int(255 * opacity)
    text_color = (*color, alpha)
    
    # Draw text with optional stroke
    if stroke_color and stroke_width > 0:
        stroke_rgba = (*stroke_color, alpha)
        draw.text(
            (x, y),
            text,
            font=font,
            fill=text_color,
            stroke_width=stroke_width,
            stroke_fill=stroke_rgba
        )
    else:
        draw.text(
            (x, y),
            text,
            font=font,
            fill=text_color
        )
    
    # Composite overlay onto original image
    watermarked = Image.alpha_composite(image, overlay)
    
    return watermarked


def add_image_watermark(
    image: Image.Image,
    watermark_path: str | Path,
    position: Position | tuple[int, int] = "bottom-right",
    scale: float = 1.0,
    opacity: float = 0.8,
    margin: int = 10
) -> Image.Image:
    """
    Add an image watermark (e.g., logo PNG) to an image.
    
    Args:
        image: PIL Image to watermark
        watermark_path: Path to watermark image file (PNG recommended)
        position: Position preset or (x, y) coordinates
        scale: Scale factor for watermark (1.0 = original size)
        opacity: Opacity from 0.0 (transparent) to 1.0 (opaque)
        margin: Margin from edges for preset positions
        
    Returns:
        New image with watermark applied

    Raises:
        ValueError: If opacity or scale is outside its accepted range, scale
            produces an empty raster size, or the named position is invalid
        
    Example:
        >>> img = Image.open("photo.jpg")  # doctest: +SKIP
        >>> result = add_image_watermark(  # doctest: +SKIP
        ...     img,
        ...     watermark_path="logo.png",
        ...     position="top-left",
        ...     scale=0.2,
        ...     opacity=0.7
        ... )
    """
    _validate_opacity(opacity)
    _validate_scale(scale)

    # Ensure image is in RGBA mode
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Load a detached RGBA copy so the source file is closed immediately.
    with Image.open(watermark_path) as source:
        watermark = source.convert("RGBA").copy()
    
    # Scale watermark if needed
    if scale != 1.0:
        new_size = (
            int(watermark.width * scale),
            int(watermark.height * scale)
        )
        if new_size[0] < 1 or new_size[1] < 1:
            raise ValueError(
                f"scale {scale} produces an empty watermark size {new_size}"
            )
        watermark = watermark.resize(new_size, Image.Resampling.LANCZOS)
    
    watermark = _apply_opacity(watermark, opacity)
    return _composite_at(image, watermark, position, margin)


def add_svg_watermark(
    image: Image.Image,
    svg_path: str | Path,
    position: Position | tuple[int, int] = "bottom-right",
    scale: float = 1.0,
    opacity: float = 0.8,
    margin: int = 10,
    width: int | None = None,
    height: int | None = None
) -> Image.Image:
    """
    Add an SVG watermark (e.g., vector logo) to an image.
    
    Requires cairosvg to be installed:
        pip install color-match-tools[image]
    
    Args:
        image: PIL Image to watermark
        svg_path: Path to SVG file
        position: Position preset or (x, y) coordinates
        scale: Scale factor for watermark (1.0 = original size)
        opacity: Opacity from 0.0 (transparent) to 1.0 (opaque)
        margin: Margin from edges for preset positions
        width: Explicit width in pixels (overrides scale)
        height: Explicit height in pixels (overrides scale)
        
    Returns:
        New image with watermark applied
        
    Raises:
        ImportError: If CairoSVG or its native Cairo library is unavailable
        ValueError: If opacity or scale is outside its accepted range
        
    Example:
        >>> img = Image.open("photo.jpg")  # doctest: +SKIP
        >>> result = add_svg_watermark(  # doctest: +SKIP
        ...     img,
        ...     svg_path="logo.svg",
        ...     position="top-right",
        ...     width=200,
        ...     opacity=0.6
        ... )
    """
    _validate_opacity(opacity)
    _validate_scale(scale)

    try:
        import cairosvg
    except (ImportError, OSError) as exc:
        raise ImportError(
            "CairoSVG and its native Cairo library are required for SVG "
            "watermarks. "
            "Install with: pip install color-match-tools[image]"
        ) from exc
    
    # Convert SVG to PNG in memory
    svg_to_png = cast(_SVGToPNG, getattr(cairosvg, "svg2png"))
    png_data = svg_to_png(
        url=str(svg_path),
        output_width=width,
        output_height=height,
        scale=scale if (width is None and height is None) else 1.0,
    )
    
    if png_data is None:
        raise RuntimeError("cairosvg.svg2png returned no PNG data")

    with Image.open(io.BytesIO(png_data)) as source:
        watermark = source.convert("RGBA").copy()

    watermark = _apply_opacity(watermark, opacity)
    
    # Ensure base image is in RGBA mode
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    return _composite_at(image, watermark, position, margin)



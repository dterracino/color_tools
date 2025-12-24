"""
Image format conversion utilities.

Provides simple, high-quality image format conversion with sensible defaults
for lossless and lossy formats.
"""

from __future__ import annotations
from pathlib import Path
from typing import Literal

try:
    from PIL import Image
    # Try to import pillow-heif for HEIC support
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
        _HEIF_AVAILABLE = True
    except ImportError:
        _HEIF_AVAILABLE = False
except ImportError:
    raise ImportError(
        "Image conversion requires Pillow. Install with: pip install color-match-tools[image]"
    )


# Common image formats supported by Pillow
ImageFormat = Literal[
    "png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif",
    "heic", "heif", "avif", "ico", "pcx", "ppm", "sgi", "tga"
]


def convert_image(
    input_path: str | Path,
    output_path: str | Path | None = None,
    output_format: str | None = None,
    quality: int | None = None,
    lossless: bool | None = None,
) -> Path:
    """
    Convert an image from one format to another with sensible quality defaults.
    
    Args:
        input_path: Path to input image file
        output_path: Path for output file. If None, auto-generates from input_path
                     using output_format extension
        output_format: Output format (png, jpg, webp, etc.). Case-insensitive.
                      If None, defaults to PNG. If output_path is provided with 
                      extension, infers from that.
        quality: JPEG/WebP quality (1-100). If None, uses format-specific defaults:
                 - JPEG: 67 (Photoshop quality 8/12 equivalent)
                 - WebP: Lossless by default (no quality needed)
                 - AVIF: 80 for lossy compression
        lossless: Force lossless compression for formats that support it (WebP, AVIF).
                  If None, WebP uses lossless by default.
    
    Returns:
        Path object pointing to the created output file
    
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If output format is not supported
        ImportError: If pillow-heif not installed for HEIC files
    
    Examples:
        >>> # WebP to PNG (lossless)
        >>> convert_image("photo.webp")  # Creates photo.png
        
        >>> # JPEG to WebP (lossless)
        >>> convert_image("photo.jpg", output_format="webp")  # Creates photo.webp
        
        >>> # Custom output path
        >>> convert_image("input.webp", "output.png")
        
        >>> # JPEG with custom quality
        >>> convert_image("photo.png", output_format="jpg", quality=85)
        
        >>> # WebP with lossy compression
        >>> convert_image("photo.png", output_format="webp", lossless=False, quality=80)
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Determine output format
    if output_path:
        output_path = Path(output_path)
        # Infer format from output extension if not explicitly provided
        if output_format is None and output_path.suffix:
            output_format = output_path.suffix.lstrip('.').lower()
    else:
        # Auto-generate output path
        if output_format is None:
            output_format = "png"  # Default to PNG
        output_path = input_path.with_suffix(f".{output_format}")
    
    # Normalize format string (lowercase and handle aliases)
    if output_format:
        output_format = output_format.lower()
        # Handle JPEG aliases
        if output_format == "jpg":
            output_format = "jpeg"
        elif output_format == "tif":
            output_format = "tiff"
    
    # Check HEIC support
    if output_format in ("heic", "heif") or input_path.suffix.lower() in (".heic", ".heif"):
        if not _HEIF_AVAILABLE:
            raise ImportError(
                "HEIC/HEIF support requires pillow-heif. "
                "Install with: pip install pillow-heif\n"
                "Or reinstall with: pip install color-match-tools[image]"
            )
    
    # Open and convert image
    with Image.open(input_path) as img:
        # Convert RGBA to RGB for formats that don't support transparency
        if img.mode == "RGBA" and output_format in ("jpeg", "bmp"):
            # Create white background
            rgb_img = Image.new("RGB", img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = rgb_img
        
        # Prepare save options
        save_kwargs = {}
        
        # Format-specific quality/compression settings
        if output_format == "jpeg":
            # JPEG quality: 67 is Photoshop quality 8/12 equivalent
            save_kwargs["quality"] = quality if quality is not None else 67
            save_kwargs["optimize"] = True
        
        elif output_format == "webp":
            # WebP: Default to lossless unless explicitly set to lossy
            if lossless is None:
                lossless = True
            
            if lossless:
                save_kwargs["lossless"] = True
            else:
                save_kwargs["quality"] = quality if quality is not None else 80
        
        elif output_format == "avif":
            # AVIF: Can be lossless or lossy
            if lossless:
                save_kwargs["quality"] = 100  # Quality 100 = lossless for AVIF
            else:
                save_kwargs["quality"] = quality if quality is not None else 80
        
        elif output_format == "png":
            # PNG is always lossless, optimize compression
            save_kwargs["optimize"] = True
        
        # Save converted image (output_format is guaranteed non-None at this point)
        assert output_format is not None, "output_format should be set by now"
        img.save(output_path, format=output_format.upper(), **save_kwargs)
    
    return output_path


def get_supported_formats() -> dict[str, list[str]]:
    """
    Get lists of supported input and output formats.
    
    Returns:
        Dictionary with 'input' and 'output' keys containing lists of format strings
    
    Examples:
        >>> formats = get_supported_formats()
        >>> print("Input formats:", formats['input'])
        >>> print("Output formats:", formats['output'])
    """
    # Pillow supported formats (common ones)
    base_formats = {
        "input": ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif", 
                  "avif", "ico", "pcx", "ppm", "sgi", "tga"],
        "output": ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif",
                   "avif", "ico", "pcx", "ppm", "sgi", "tga"],
    }
    
    # Add HEIC/HEIF if available
    if _HEIF_AVAILABLE:
        base_formats["input"].extend(["heic", "heif"])
        base_formats["output"].extend(["heic", "heif"])
    
    return base_formats

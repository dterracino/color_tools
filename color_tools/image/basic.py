"""
Basic image analysis functions for color_tools.

This module provides general-purpose image analysis utilities,
separate from the HueForge-specific tools in analysis.py.

Functions in this module require Pillow and numpy:
    pip install color-match-tools[image]

Public API:
-----------
    count_unique_colors - Count total unique RGB colors in an image
    get_color_histogram - Get histogram mapping RGB colors to pixel counts
    get_dominant_color - Get the most common color in an image
    is_indexed_mode - Check if image uses indexed color mode (palette-based)
    analyze_brightness - Analyze image brightness with assessment
    analyze_contrast - Analyze image contrast using standard deviation
    analyze_noise_level - Estimate noise level using scikit-image
    analyze_dynamic_range - Analyze dynamic range and gamma suggestions

Example:
--------
    >>> from color_tools.image import count_unique_colors, get_color_histogram, get_dominant_color
    >>> 
    >>> # Count colors in an image
    >>> total = count_unique_colors("photo.jpg")
    >>> print(f"Image contains {total} unique colors")
    Image contains 42,387 unique colors
    >>> 
    >>> # Get color histogram
    >>> histogram = get_color_histogram("photo.jpg")
    >>> print(f"Red pixels: {histogram.get((255, 0, 0), 0)}")
    Red pixels: 1523
    >>> 
    >>> # Get dominant color
    >>> dominant = get_dominant_color("photo.jpg")
    >>> print(f"Most common color: RGB{dominant}")
    Most common color: RGB(240, 235, 230)
    >>> 
    >>> # Check if image is indexed
    >>> if is_indexed_mode("icon.png"):
    ...     print("Image uses a color palette")
    Image uses a color palette
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from pathlib import Path

# --- Analysis Thresholds ---
THRESHOLD_LOW_CONTRAST = 40.0      # Standard Deviation of pixel brightness
THRESHOLD_DARK_IMAGE = 60.0        # Mean brightness (0-255)
THRESHOLD_BRIGHT_IMAGE = 195.0     # Mean brightness (0-255)
THRESHOLD_NOISE_SIGMA = 2.0        # Estimated noise sigma
THRESHOLD_FULL_DYNAMIC_RANGE = 216 # 85% of 0-255 spectrum (216/255)
GAMMA_DARK_THRESHOLD = 100.0       # Mean brightness for gamma suggestions
GAMMA_BRIGHT_THRESHOLD = 200.0     # Mean brightness for gamma suggestions

# Check for required dependencies
try:
    import numpy as np # type: ignore
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from PIL import Image # type: ignore
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    from skimage import restoration # type: ignore
    SCIKIT_IMAGE_AVAILABLE = True
except ImportError:
    SCIKIT_IMAGE_AVAILABLE = False


def _check_dependencies():
    """Raise ImportError if required dependencies are not available."""
    if not PILLOW_AVAILABLE:
        raise ImportError(
            "Pillow is required for image analysis. "
            "Install with: pip install color-match-tools[image]"
        )
    if not NUMPY_AVAILABLE:
        raise ImportError(
            "numpy is required for efficient color counting. "
            "Install with: pip install color-match-tools[image]"
        )


def _check_basic_dependencies():
    """Check only Pillow and numpy (for functions that don't need scikit-image)."""
    if not PILLOW_AVAILABLE:
        raise ImportError(
            "Pillow is required for image analysis. "
            "Install with: pip install color-match-tools[image]"
        )
    if not NUMPY_AVAILABLE:
        raise ImportError(
            "numpy is required for image analysis. "
            "Install with: pip install color-match-tools[image]"
        )


def _check_noise_dependencies():
    """Check all dependencies including scikit-image for noise analysis."""
    _check_basic_dependencies()
    if not SCIKIT_IMAGE_AVAILABLE:
        raise ImportError(
            "scikit-image is required for noise analysis. "
            "Install with: pip install color-match-tools[image]"
        )


def count_unique_colors(image_path: str | Path) -> int:
    """
    Count the total number of unique RGB colors in an image.
    
    Uses numpy for efficient counting of unique color combinations.
    The image is converted to RGB mode before counting (alpha channel ignored).
    
    Args:
        image_path: Path to the image file
    
    Returns:
        Number of unique RGB colors (integer)
    
    Raises:
        ImportError: If Pillow or numpy is not installed
        FileNotFoundError: If image file doesn't exist
        IOError: If image file cannot be opened
    
    Example:
        >>> count_unique_colors("photo.jpg")
        42387
        
        >>> # Indexed images (GIF, PNG with palette) show palette size
        >>> count_unique_colors("icon.gif")
        256
        
        >>> # Solid color image
        >>> count_unique_colors("red_square.png")
        1
    
    Note:
        For indexed color images (mode 'P'), this counts unique colors in the
        converted RGB image, not the palette size. Use is_indexed_mode() to
        check if an image uses a palette.
    """
    _check_dependencies()
    
    # Load image and convert to RGB
    with Image.open(image_path) as img:
        img_rgb = img.convert('RGB')
        
        # Convert to numpy array (H x W x 3)
        pixels = np.array(img_rgb)
        
        # Reshape to 2D array where each row is an RGB tuple
        # (H*W) rows, 3 columns
        pixels_flat = pixels.reshape(-1, 3)
        
        # Find unique rows (unique RGB combinations)
        # np.unique returns sorted unique rows when axis=0
        unique_colors = np.unique(pixels_flat, axis=0)
        
        return len(unique_colors)


def is_indexed_mode(image_path: str | Path) -> bool:
    """
    Check if an image uses indexed color mode (palette-based).
    
    Indexed color images (mode 'P') store pixel values as indices into
    a color palette, rather than direct RGB values. This is common for:
    - GIF images (max 256 colors)
    - PNG images with palettes
    - Some BMP images
    
    Args:
        image_path: Path to the image file
    
    Returns:
        True if image is in indexed mode ('P'), False otherwise
    
    Raises:
        ImportError: If Pillow is not installed
        FileNotFoundError: If image file doesn't exist
        IOError: If image file cannot be opened
    
    Example:
        >>> is_indexed_mode("photo.jpg")
        False
        
        >>> is_indexed_mode("icon.gif")
        True
        
        >>> is_indexed_mode("logo.png")  # Depends on PNG type
        True  # If PNG uses palette
    
    Note:
        PIL/Pillow mode codes:
        - 'P': Palette-based (indexed color)
        - 'RGB': Direct RGB color
        - 'RGBA': RGB with alpha channel
        - 'L': Grayscale
        - '1': Binary (black and white)
    """
    if not PILLOW_AVAILABLE:
        raise ImportError(
            "Pillow is required for image analysis. "
            "Install with: pip install color-match-tools[image]"
        )
    
    with Image.open(image_path) as img:
        return img.mode == 'P'


def get_color_histogram(image_path: str | Path) -> dict[tuple[int, int, int], int]:
    """
    Get histogram mapping RGB colors to their pixel counts.
    
    Returns a dictionary where keys are RGB tuples and values are the number
    of pixels with that color. Uses numpy for efficient histogram calculation.
    
    Args:
        image_path: Path to the image file
    
    Returns:
        Dictionary mapping (R, G, B) tuples to pixel counts
    
    Raises:
        ImportError: If Pillow or numpy is not installed
        FileNotFoundError: If image file doesn't exist
        IOError: If image file cannot be opened
    
    Example:
        >>> histogram = get_color_histogram("photo.jpg")
        >>> histogram[(255, 0, 0)]  # Count of pure red pixels
        1523
        
        >>> # Find most common color
        >>> most_common = max(histogram.items(), key=lambda x: x[1])
        >>> print(f"Color: {most_common[0]}, Count: {most_common[1]}")
        Color: (240, 235, 230), Count: 15042
        
        >>> # Get all colors sorted by frequency
        >>> sorted_colors = sorted(histogram.items(), key=lambda x: x[1], reverse=True)
        >>> for color, count in sorted_colors[:5]:
        ...     print(f"RGB{color}: {count} pixels")
        RGB(240, 235, 230): 15042 pixels
        RGB(235, 230, 225): 12834 pixels
        ...
    
    Note:
        For images with many colors, the histogram can be large.
        Consider using count_unique_colors() if you only need the count.
    """
    _check_dependencies()
    
    # Load image and convert to RGB
    with Image.open(image_path) as img:
        img_rgb = img.convert('RGB')
        
        # Convert to numpy array (H x W x 3)
        pixels = np.array(img_rgb)
        
        # Reshape to 2D array where each row is an RGB tuple
        pixels_flat = pixels.reshape(-1, 3)
        
        # Convert each RGB tuple to a hashable key and count occurrences
        # Use numpy's unique with return_counts for efficiency
        unique_colors, counts = np.unique(pixels_flat, axis=0, return_counts=True)
        
        # Build dictionary mapping RGB tuples to counts
        # Convert numpy types to native Python int for cleaner output
        histogram = {
            (int(color[0]), int(color[1]), int(color[2])): int(count)
            for color, count in zip(unique_colors, counts)
        }
        
        return histogram


def get_dominant_color(image_path: str | Path) -> tuple[int, int, int]:
    """
    Get the most common (dominant) color in an image.
    
    Returns the single RGB color that appears most frequently in the image.
    This is equivalent to finding the mode of the color distribution.
    
    Args:
        image_path: Path to the image file
    
    Returns:
        RGB tuple (R, G, B) of the most common color
    
    Raises:
        ImportError: If Pillow or numpy is not installed
        FileNotFoundError: If image file doesn't exist
        IOError: If image file cannot be opened
    
    Example:
        >>> dominant = get_dominant_color("photo.jpg")
        >>> print(f"Dominant color: RGB{dominant}")
        Dominant color: RGB(240, 235, 230)
        
        >>> # Use with nearest color matching
        >>> from color_tools import Palette
        >>> palette = Palette.load_default()
        >>> color_record, distance = palette.nearest_color(dominant)
        >>> print(f"Closest CSS color: {color_record.name}")
        Closest CSS color: seashell
    
    Note:
        For images with many unique colors, this uses the histogram
        approach which may be memory-intensive. For very large images,
        consider downsampling first using Pillow's thumbnail() method.
    """
    _check_dependencies()
    
    # Load image and convert to RGB
    with Image.open(image_path) as img:
        img_rgb = img.convert('RGB')
        
        # Convert to numpy array (H x W x 3)
        pixels = np.array(img_rgb)
        
        # Reshape to 2D array where each row is an RGB tuple
        pixels_flat = pixels.reshape(-1, 3)
        
        # Find unique colors and their counts
        unique_colors, counts = np.unique(pixels_flat, axis=0, return_counts=True)
        
        # Find index of maximum count
        max_idx = np.argmax(counts)
        
        # Return the color with maximum count
        dominant_rgb = unique_colors[max_idx]
        return (int(dominant_rgb[0]), int(dominant_rgb[1]), int(dominant_rgb[2]))


def analyze_brightness(image_path: str | Path) -> dict[str, Union[float, str]]:
    """
    Analyze image brightness characteristics.
    
    Calculates the mean brightness of the image in grayscale and provides
    an assessment based on standard thresholds.
    
    Args:
        image_path: Path to the image file
    
    Returns:
        Dictionary with:
        - 'mean_brightness': Mean brightness value (0-255 scale)
        - 'assessment': Human-readable assessment ('dark'|'normal'|'bright')
    
    Raises:
        ImportError: If Pillow or numpy is not installed
        FileNotFoundError: If image file doesn't exist
        IOError: If image file cannot be opened
    
    Example:
        >>> result = analyze_brightness("photo.jpg")
        >>> print(f"Brightness: {result['mean_brightness']:.1f} ({result['assessment']})")
        Brightness: 127.3 (normal)
        
        >>> # Dark image
        >>> result = analyze_brightness("dark_photo.jpg")
        >>> print(result)
        {'mean_brightness': 45.2, 'assessment': 'dark'}
    
    Note:
        Brightness thresholds:
        - Dark: mean < THRESHOLD_DARK_IMAGE (60)
        - Bright: mean > THRESHOLD_BRIGHT_IMAGE (195)
        - Normal: THRESHOLD_DARK_IMAGE ≤ mean ≤ THRESHOLD_BRIGHT_IMAGE
    """
    _check_basic_dependencies()
    
    with Image.open(image_path) as img:
        # Convert to grayscale for brightness analysis
        gray_img = img.convert('L')
        np_gray = np.array(gray_img)
        
        # Calculate mean brightness
        mean_brightness = float(np.mean(np_gray))
        
        # Determine assessment based on thresholds
        if mean_brightness < THRESHOLD_DARK_IMAGE:
            assessment = 'dark'
        elif mean_brightness > THRESHOLD_BRIGHT_IMAGE:
            assessment = 'bright'
        else:
            assessment = 'normal'
        
        return {
            'mean_brightness': mean_brightness,
            'assessment': assessment
        }


def analyze_contrast(image_path: str | Path) -> dict[str, Union[float, str]]:
    """
    Analyze image contrast using standard deviation of pixel values.
    
    Higher standard deviation indicates more contrast (wider range of brightness values).
    Lower standard deviation indicates less contrast (more uniform brightness).
    
    Args:
        image_path: Path to the image file
    
    Returns:
        Dictionary with:
        - 'contrast_std': Standard deviation of brightness values
        - 'assessment': Human-readable assessment ('low'|'normal')
    
    Raises:
        ImportError: If Pillow or numpy is not installed
        FileNotFoundError: If image file doesn't exist
        IOError: If image file cannot be opened
    
    Example:
        >>> result = analyze_contrast("photo.jpg")
        >>> print(f"Contrast: {result['contrast_std']:.1f} ({result['assessment']})")
        Contrast: 62.4 (normal)
        
        >>> # Low contrast image
        >>> result = analyze_contrast("flat_image.jpg")
        >>> print(result)
        {'contrast_std': 25.3, 'assessment': 'low'}
    
    Note:
        Contrast threshold:
        - Low contrast: std < THRESHOLD_LOW_CONTRAST (40)
        - Normal contrast: std ≥ THRESHOLD_LOW_CONTRAST
    """
    _check_basic_dependencies()
    
    with Image.open(image_path) as img:
        # Convert to grayscale for contrast analysis
        gray_img = img.convert('L')
        np_gray = np.array(gray_img)
        
        # Calculate standard deviation as contrast measure
        contrast_std = float(np.std(np_gray))
        
        # Determine assessment based on threshold
        if contrast_std < THRESHOLD_LOW_CONTRAST:
            assessment = 'low'
        else:
            assessment = 'normal'
        
        return {
            'contrast_std': contrast_std,
            'assessment': assessment
        }


def analyze_noise_level(
    image_path: str | Path, 
    crop_size: int = 512,
    noise_threshold: float = THRESHOLD_NOISE_SIGMA
) -> dict[str, Union[float, str]]:
    """
    Estimate noise level using scikit-image restoration.estimate_sigma().
    
    Analyzes a center crop of the image to estimate noise sigma. This method
    is effective for detecting sensor noise, compression artifacts, and other
    forms of image degradation.
    
    Args:
        image_path: Path to the image file
        crop_size: Size of center crop to analyze (default: 512px)
        noise_threshold: Threshold for noise assessment (default: THRESHOLD_NOISE_SIGMA)
    
    Returns:
        Dictionary with:
        - 'noise_sigma': Estimated noise standard deviation
        - 'assessment': Human-readable assessment ('clean'|'noisy')
    
    Raises:
        ImportError: If Pillow, numpy, or scikit-image is not installed
        FileNotFoundError: If image file doesn't exist
        IOError: If image file cannot be opened
    
    Example:
        >>> result = analyze_noise_level("photo.jpg")
        >>> print(f"Noise: {result['noise_sigma']:.2f} ({result['assessment']})")
        Noise: 1.23 (clean)
        
        >>> # Noisy image
        >>> result = analyze_noise_level("noisy_photo.jpg")
        >>> print(result)
        {'noise_sigma': 3.45, 'assessment': 'noisy'}
    
    Note:
        - Uses center crop to avoid edge effects
        - Estimates noise in RGB channels and averages
        - Noise threshold: sigma > THRESHOLD_NOISE_SIGMA (2.0) = noisy
        - Fallback: Returns 0.0 if estimation fails
    """
    _check_noise_dependencies()
    
    with Image.open(image_path) as img:
        # Convert to RGB for noise analysis
        img_rgb = img.convert('RGB')
        np_rgb = np.array(img_rgb)
        
        # Get center crop for noise estimation
        h, w, _ = np_rgb.shape
        cy, cx = h // 2, w // 2
        
        # Calculate crop boundaries
        half_crop = crop_size // 2
        y_start = max(0, cy - half_crop)
        y_end = min(h, cy + half_crop)
        x_start = max(0, cx - half_crop)
        x_end = min(w, cx + half_crop)
        
        # Extract center crop
        crop = np_rgb[y_start:y_end, x_start:x_end]
        
        try:
            # Estimate noise sigma using scikit-image
            sigma_est = restoration.estimate_sigma(
                crop, 
                channel_axis=-1, 
                average_sigmas=True
            )
            # Ensure we have a scalar float value
            if hasattr(sigma_est, '__iter__') and not isinstance(sigma_est, str):
                # If it's an array or list, take the mean
                sigma_value = float(np.mean(sigma_est))
            else:
                # If it's already a scalar, convert to float
                sigma_value = float(sigma_est)
        except Exception:
            # Fallback if estimation fails
            sigma_value = 0.0
        
        # Determine assessment based on threshold
        if sigma_value > noise_threshold:
            assessment = 'noisy'
        else:
            assessment = 'clean'
        
        return {
            'noise_sigma': sigma_value,
            'assessment': assessment
        }


def analyze_dynamic_range(image_path: str | Path) -> dict[str, Union[int, float, str]]:
    """
    Analyze dynamic range and tonal distribution of an image.
    
    Examines the full range of brightness values used and provides suggestions
    for gamma correction based on the tonal distribution.
    
    Args:
        image_path: Path to the image file
    
    Returns:
        Dictionary with:
        - 'min_value': Minimum brightness value (0-255)
        - 'max_value': Maximum brightness value (0-255)  
        - 'range': Dynamic range (max - min)
        - 'mean_brightness': Mean brightness for gamma assessment
        - 'range_assessment': Assessment of dynamic range usage ('full'|'limited')
        - 'gamma_suggestion': Suggested gamma adjustment for tonal balance
    
    Raises:
        ImportError: If Pillow or numpy is not installed
        FileNotFoundError: If image file doesn't exist
        IOError: If image file cannot be opened
    
    Example:
        >>> result = analyze_dynamic_range("photo.jpg")
        >>> print(f"Range: {result['range']} ({result['range_assessment']})")
        >>> print(f"Gamma suggestion: {result['gamma_suggestion']}")
        Range: 248 (full)
        Gamma suggestion: Normal (mean balanced)
        
        >>> # Limited range image
        >>> result = analyze_dynamic_range("flat_image.jpg") 
        >>> print(result)
        {'min_value': 45, 'max_value': 198, 'range': 153, 'mean_brightness': 89.2,
         'range_assessment': 'limited', 'gamma_suggestion': 'Decrease (<1.0) to boost midtones'}
    
    Note:
        - Full range threshold: range ≥ THRESHOLD_FULL_DYNAMIC_RANGE (216, 85% of 0-255 spectrum)
        - Gamma suggestions based on mean brightness:
          - Mean < GAMMA_DARK_THRESHOLD (100): Decrease gamma to boost midtones
          - Mean > GAMMA_BRIGHT_THRESHOLD (200): Increase gamma to suppress midtones
          - GAMMA_DARK_THRESHOLD ≤ mean ≤ GAMMA_BRIGHT_THRESHOLD: Normal/balanced
    """
    _check_basic_dependencies()
    
    with Image.open(image_path) as img:
        # Convert to grayscale for dynamic range analysis
        gray_img = img.convert('L')
        np_gray = np.array(gray_img)
        
        # Calculate range statistics
        min_value = int(np.min(np_gray))
        max_value = int(np.max(np_gray))
        range_value = max_value - min_value
        mean_brightness = float(np.mean(np_gray))
        
        # Assess dynamic range usage
        if range_value >= THRESHOLD_FULL_DYNAMIC_RANGE:
            range_assessment = 'full'
        else:
            range_assessment = 'limited'
        
        # Generate gamma suggestion based on mean brightness
        if mean_brightness < GAMMA_DARK_THRESHOLD:
            gamma_suggestion = 'Decrease (<1.0) to boost midtones'
        elif mean_brightness > GAMMA_BRIGHT_THRESHOLD:
            gamma_suggestion = 'Increase (>1.0) to suppress midtones'
        else:
            gamma_suggestion = 'Normal (mean balanced)'
        
        return {
            'min_value': min_value,
            'max_value': max_value,
            'range': range_value,
            'mean_brightness': mean_brightness,
            'range_assessment': range_assessment,
            'gamma_suggestion': gamma_suggestion
        }

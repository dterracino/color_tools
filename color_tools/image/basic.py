"""
Basic image analysis functions for color_tools.

This module provides general-purpose image analysis utilities,
separate from the HueForge-specific tools in analysis.py.

Functions in this module require Pillow and numpy:
    pip install color-match-tools[image]

TODO - Dominant Color Enhancements:
1. Refactor get_dominant_color() -> get_dominant_colors(n_colors=5) 
   - Return list of N most dominant colors in frequency order
   - get_dominant_color() becomes wrapper for get_dominant_colors(1)[0]
2. Add accent color detection for perceptual dominance:
   - Problem: Images with gray background + colorful accent (accent is perceptually 
     dominant but statistically minor)
   - Solutions: Saturation weighting, exclude neutrals, dual analysis
   - Proposed: get_accent_colors() function with saturation filtering

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

from pathlib import Path
from typing import TYPE_CHECKING, Union, Callable

if TYPE_CHECKING:
    import PIL.Image

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


# =============================================================================
# Image Transformation Functions
# =============================================================================
# These functions apply color transformations to entire images, leveraging
# existing color_tools infrastructure for CVD simulation and palette quantization.

def transform_image(
    image_path: Path | str,
    transform_func: Callable[[tuple[int, int, int]], tuple[int, int, int]],
    preserve_alpha: bool = True,
    output_path: Path | str | None = None
) -> 'PIL.Image.Image':
    """
    Apply a color transformation function to every pixel of an image.
    
    This is the core function that handles image loading, pixel iteration,
    transformation application, and optional saving. It's used by both
    CVD simulation and palette quantization functions.
    
    Args:
        image_path: Path to input image file
        transform_func: Function that takes RGB tuple (r, g, b) and returns RGB tuple
        preserve_alpha: If True, preserve alpha channel in RGBA images
        output_path: Optional path to save transformed image
    
    Returns:
        PIL Image with transformed colors
    
    Raises:
        ImportError: If Pillow is not installed
        FileNotFoundError: If input image doesn't exist
        ValueError: If image format is unsupported
    
    Example:
        >>> # Define a transformation (invert colors)
        >>> def invert_rgb(rgb):
        ...     r, g, b = rgb
        ...     return (255-r, 255-g, 255-b)
        >>> 
        >>> # Apply to image
        >>> transformed = transform_image("photo.jpg", invert_rgb)
        >>> transformed.save("inverted.jpg")
    """
    try:
        import PIL.Image
        import numpy as np
    except ImportError:
        raise ImportError(
            "transform_image requires Pillow and numpy. "
            "Install with: pip install color-match-tools[image]"
        )
    
    # Load and prepare image
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    original = PIL.Image.open(image_path)
    
    # Handle different image modes
    has_alpha = original.mode in ('RGBA', 'LA') or 'transparency' in original.info
    
    if original.mode == 'P':  # Palette mode
        # Convert palette to RGB for processing
        if has_alpha and preserve_alpha:
            working_image = original.convert('RGBA')
        else:
            working_image = original.convert('RGB')
    elif original.mode in ('L', 'LA'):  # Grayscale
        if has_alpha and preserve_alpha:
            working_image = original.convert('RGBA')
        else:
            working_image = original.convert('RGB')
    elif original.mode == 'RGBA':
        working_image = original
    elif original.mode == 'RGB':
        working_image = original
    else:
        # Convert other modes to RGB
        working_image = original.convert('RGB')
    
    # Convert to numpy array for efficient processing
    np_image = np.array(working_image)
    
    # Apply transformation to each pixel
    if working_image.mode == 'RGBA' and preserve_alpha:
        # Process RGB, preserve alpha
        for y in range(np_image.shape[0]):
            for x in range(np_image.shape[1]):
                r, g, b, a = np_image[y, x]
                new_r, new_g, new_b = transform_func((r, g, b))
                np_image[y, x] = [new_r, new_g, new_b, a]
    else:
        # Process RGB only
        for y in range(np_image.shape[0]):
            for x in range(np_image.shape[1]):
                r, g, b = np_image[y, x][:3]  # Handle both RGB and RGBA
                new_r, new_g, new_b = transform_func((r, g, b))
                np_image[y, x][:3] = [new_r, new_g, new_b]
    
    # Convert back to PIL Image
    transformed = PIL.Image.fromarray(np_image, mode=working_image.mode)
    
    # Save if output path provided
    if output_path is not None:
        output_path = Path(output_path) if not isinstance(output_path, Path) else output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        transformed.save(output_path)
    
    return transformed


def simulate_cvd_image(
    image_path: Path | str,
    deficiency_type: str,
    output_path: Path | str | None = None
) -> 'PIL.Image.Image':
    """
    Simulate color vision deficiency for an entire image.
    
    This shows how an image would appear to someone with a specific type
    of color blindness. Useful for testing image accessibility.
    
    Args:
        image_path: Path to input image
        deficiency_type: Type of CVD to simulate
            - 'protanopia' or 'protan': Red-blind
            - 'deuteranopia' or 'deutan': Green-blind  
            - 'tritanopia' or 'tritan': Blue-blind
        output_path: Optional path to save simulated image
    
    Returns:
        PIL Image showing CVD simulation
    
    Example:
        >>> # See how image appears to someone with deuteranopia
        >>> sim_image = simulate_cvd_image("colorful.jpg", "deuteranopia")
        >>> sim_image.save("deuteranopia_sim.jpg")
        >>> 
        >>> # Test accessibility of an infographic
        >>> simulate_cvd_image("chart.png", "protanopia", "chart_protan.png")
    """
    from color_tools.color_deficiency import simulate_cvd
    
    def cvd_transform(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        return simulate_cvd(rgb, deficiency_type)
    
    return transform_image(image_path, cvd_transform, output_path=output_path)


def correct_cvd_image(
    image_path: Path | str,
    deficiency_type: str,
    output_path: Path | str | None = None
) -> 'PIL.Image.Image':
    """
    Apply color vision deficiency correction to an entire image.
    
    This shifts colors to improve discriminability for individuals with
    color blindness. The corrected image should be viewed by people with
    the specified deficiency type.
    
    Args:
        image_path: Path to input image
        deficiency_type: Type of CVD to correct for
            - 'protanopia' or 'protan': Red-blind
            - 'deuteranopia' or 'deutan': Green-blind  
            - 'tritanopia' or 'tritan': Blue-blind
        output_path: Optional path to save corrected image
    
    Returns:
        PIL Image with CVD correction applied
    
    Example:
        >>> # Enhance image for deuteranopia viewers
        >>> corrected = correct_cvd_image("chart.jpg", "deuteranopia")
        >>> corrected.save("chart_deutan_enhanced.jpg")
    """
    from color_tools.color_deficiency import correct_cvd
    
    def cvd_correction(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        return correct_cvd(rgb, deficiency_type)
    
    return transform_image(image_path, cvd_correction, output_path=output_path)


def quantize_image_to_palette(
    image_path: Path | str,
    palette_name: str,
    metric: str = 'de2000',
    dither: bool = False,
    output_path: Path | str | None = None
) -> 'PIL.Image.Image':
    """
    Convert an image to use only colors from a specified palette.
    
    This maps each pixel to the nearest color in the target palette using
    perceptually-accurate color distance metrics. Perfect for creating
    retro-style graphics or testing designs with limited color sets.
    
    Args:
        image_path: Path to input image
        palette_name: Name of palette to use:
            - Built-in palettes: 'cga4', 'ega16', 'ega64', 'vga', 'web', 'gameboy'
            - User palettes: 'user-mycustom' (files in data/user/palettes/ must have 'user-' prefix)
            - User palettes do not override built-in palettes (separate namespaces)
        metric: Color distance metric for matching:
            - 'de2000': CIEDE2000 (most perceptually accurate)
            - 'de94': CIE94 (good balance)
            - 'de76': CIE76 (simple LAB distance)
            - 'cmc': CMC l:c (textile industry standard)
            - 'euclidean': Simple RGB distance (fastest)
            - 'hsl_euclidean': HSL distance with hue wraparound
        dither: Apply Floyd-Steinberg dithering to reduce banding
        output_path: Optional path to save quantized image
    
    Returns:
        PIL Image using only palette colors
    
    Example:
        >>> # Convert photo to CGA 4-color palette
        >>> retro = quantize_image_to_palette("photo.jpg", "cga4")
        >>> retro.save("retro_cga.png")
        >>> 
        >>> # Create EGA-style artwork with dithering
        >>> quantize_image_to_palette(
        ...     "artwork.png", 
        ...     "ega16", 
        ...     metric="de2000",
        ...     dither=True,
        ...     output_path="ega_dithered.png"
        ... )
    """
    from color_tools.palette import load_palette
    from ..conversions import rgb_to_lab
    from ..distance import (
        euclidean, delta_e_76, delta_e_94, delta_e_2000,
        delta_e_cmc, hsl_euclidean
    )
    
    # Load target palette
    try:
        palette = load_palette(palette_name)
    except FileNotFoundError as e:
        raise ValueError(str(e)) from e
    
    try:
        import PIL.Image
        import numpy as np
    except ImportError:
        raise ImportError(
            "Palette quantization requires Pillow and numpy. "
            "Install with: pip install color-match-tools[image]"
        )
    
    from pathlib import Path
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Load image
    original = PIL.Image.open(image_path).convert('RGB')
    pixels_rgb: list[tuple[int, int, int]] = list(original.getdata())  # type: ignore[arg-type]
    
    # Get unique colors from source image
    unique_colors = {}  # {rgb: count}
    for pixel in pixels_rgb:
        unique_colors[pixel] = unique_colors.get(pixel, 0) + 1
    
    num_unique = len(unique_colors)
    palette_size = len(palette.records)
    
    # Strategy depends on source color count vs palette size:
    # - High-color image: Quantize to palette_size colors first, then remap
    # - Low-color image: Direct 1:1 remapping
    
    if num_unique > palette_size:
        # High-color image: Use fast k-means to reduce to palette_size colors
        # This preserves image detail by finding representative colors
        
        # Convert pixels to numpy array for vectorized operations
        pixels_array = np.array(pixels_rgb, dtype=np.float32)
        
        # Sample pixels for large images (max 10k samples for speed)
        max_samples = 10000
        if len(pixels_array) > max_samples:
            sample_indices = np.random.choice(len(pixels_array), max_samples, replace=False)
            samples = pixels_array[sample_indices]
        else:
            samples = pixels_array
        
        # Initialize centroids using k-means++ approach (better than random)
        # Start with random first centroid
        centroids = [samples[np.random.randint(len(samples))]]
        
        for _ in range(palette_size - 1):
            # Calculate distances from each sample to nearest centroid
            distances = np.min([
                np.sum((samples - centroid) ** 2, axis=1)
                for centroid in centroids
            ], axis=0)
            
            # Choose next centroid with probability proportional to distance^2
            probabilities = distances / distances.sum()
            next_idx = np.random.choice(len(samples), p=probabilities)
            centroids.append(samples[next_idx])
        
        centroids = np.array(centroids, dtype=np.float32)
        
        # Run k-means on samples (fewer iterations, vectorized)
        for _ in range(5):  # Reduced from 10 iterations
            # Assign samples to nearest centroid (vectorized)
            distances = np.array([
                np.sum((samples - centroid) ** 2, axis=1)
                for centroid in centroids
            ])
            assignments = np.argmin(distances, axis=0)
            
            # Update centroids
            for i in range(palette_size):
                mask = assignments == i
                if mask.any():
                    centroids[i] = samples[mask].mean(axis=0)
        
        # Assign ALL pixels to nearest centroid (vectorized, fast)
        distances = np.array([
            np.sum((pixels_array - centroid) ** 2, axis=1)
            for centroid in centroids
        ])
        pixel_assignments = np.argmin(distances, axis=0)
        
        # Build quantized colors and pixel mapping
        quantized_colors = [tuple(int(round(c)) for c in centroid) for centroid in centroids]
        pixels_to_cluster = {i: quantized_colors[pixel_assignments[i]] for i in range(len(pixels_rgb))}
        
        # Sort quantized colors by L-value for better palette matching
        quantized_with_lab = [(rgb, rgb_to_lab(rgb)) for rgb in quantized_colors]
        colors_to_map = sorted(quantized_with_lab, key=lambda x: x[1][0])
    else:
        # Low-color image: Direct mapping of unique colors
        unique_with_lab = [(rgb, rgb_to_lab(rgb)) for rgb in unique_colors.keys()]
        colors_to_map = sorted(unique_with_lab, key=lambda x: x[1][0])
        pixels_to_cluster = None  # Not needed for low-color images
    
    # Select distance function
    distance_funcs = {
        'euclidean': euclidean,
        'de76': delta_e_76,
        'de94': delta_e_94,
        'de2000': delta_e_2000,
        'cmc': delta_e_cmc,
        'hsl_euclidean': hsl_euclidean
    }
    distance_func = distance_funcs.get(metric, delta_e_2000)
    
    # Map quantized/unique colors to palette colors (collision-free)
    color_map = {}
    used_palette_colors = set()
    
    for source_rgb, source_lab in colors_to_map:
        # Find nearest UNUSED palette color
        best_match = None
        best_distance = float('inf')
        
        for palette_record in palette.records:
            if palette_record.rgb in used_palette_colors:
                continue  # Skip already-used colors
            
            # Calculate distance using selected metric
            dist = distance_func(source_rgb, palette_record.rgb)
            
            if dist < best_distance:
                best_distance = dist
                best_match = palette_record.rgb
        
        # If all palette colors are used, reuse nearest one
        if best_match is None:
            color_record, _ = palette.nearest_color(source_rgb, metric=metric)
            best_match = color_record.rgb
        
        color_map[source_rgb] = best_match
        used_palette_colors.add(best_match)
    
    # Apply mapping without dithering
    if not dither:
        if pixels_to_cluster is not None:
            # High-color: Map through k-means clusters
            quantized_pixels = [
                color_map[pixels_to_cluster[i]] 
                for i in range(len(pixels_rgb))
            ]
        else:
            # Low-color: Direct mapping
            quantized_pixels = [color_map[pixel] for pixel in pixels_rgb]
        
        quantized = PIL.Image.new('RGB', original.size)
        quantized.putdata(quantized_pixels)
        
        if output_path is not None:
            output_path = Path(output_path) if not isinstance(output_path, Path) else output_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            quantized.save(output_path)
        
        return quantized
    
    # Apply with Floyd-Steinberg dithering
    np_image = np.array(original, dtype=np.float32)
    height, width = np_image.shape[:2]
    
    # Floyd-Steinberg error diffusion matrix
    error_weights = [
        (1, 0, 7/16),   # Right
        (-1, 1, 3/16),  # Down-left  
        (0, 1, 5/16),   # Down
        (1, 1, 1/16)    # Down-right
    ]
    
    # Process each pixel with error diffusion
    for y in range(height):
        for x in range(width):
            pixel_idx = y * width + x
            
            # Get current pixel color
            old_rgb = tuple(np.clip(np_image[y, x], 0, 255).astype(int))
            
            # Map to palette color (through k-means cluster if high-color image)
            if pixels_to_cluster is not None:
                # High-color: Map through cluster
                cluster_rgb = pixels_to_cluster[pixel_idx]
                new_rgb = color_map[cluster_rgb]
            else:
                # Low-color: Direct mapping
                new_rgb = color_map.get(old_rgb, old_rgb)
            
            # Set new color
            np_image[y, x] = new_rgb
            
            # Calculate and diffuse quantization error
            error = np_image[y, x] - np.array(old_rgb, dtype=np.float32)
            
            for dx, dy, weight in error_weights:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    np_image[ny, nx] += error * weight
    
    # Convert back to PIL Image
    np_image = np.clip(np_image, 0, 255).astype(np.uint8)
    dithered = PIL.Image.fromarray(np_image, mode='RGB')
    
    # Save if requested
    if output_path is not None:
        output_path = Path(output_path) if not isinstance(output_path, Path) else output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dithered.save(output_path)
    
    return dithered

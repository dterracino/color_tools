"""
Image analysis functions for color extraction and manipulation.

This module provides functions for extracting colors from images and
redistributing their luminance values for perceptual uniformity.

Requires Pillow (PIL) - install with: pip install -r requirements-image.txt
"""

from __future__ import annotations
from typing import Tuple, List
from dataclasses import dataclass

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from ..conversions import rgb_to_lch, lch_to_rgb, rgb_to_lab, lab_to_rgb
from ..distance import delta_e_2000


@dataclass
class ColorCluster:
    """
    A cluster of similar colors from k-means clustering in LAB color space.
    
    Represents a group of perceptually similar pixels extracted from an image.
    The centroid is the representative color for the cluster, and pixel assignments
    enable remapping the original image to use only the dominant colors.
    
    Attributes:
        centroid_rgb: Representative RGB color for this cluster (0-255 each)
        centroid_lab: Representative color in CIE LAB space (L: 0-100, a/b: ~-128 to +127)
        pixel_indices: List of pixel indices (flat array positions) belonging to this cluster
        pixel_count: Number of pixels in this cluster (dominance weight)
    
    Example:
        >>> from color_tools.image import extract_color_clusters
        >>> clusters = extract_color_clusters("photo.jpg", n_colors=5)
        >>> for i, cluster in enumerate(clusters, 1):
        ...     print(f"Color {i}: RGB{cluster.centroid_rgb} ({cluster.pixel_count} pixels)")
        Color 1: RGB(45, 52, 71) (15234 pixels)
        Color 2: RGB(189, 147, 128) (8921 pixels)
    """
    centroid_rgb: Tuple[int, int, int]  # Representative color
    centroid_lab: Tuple[float, float, float]  # LAB representation
    pixel_indices: List[int]  # Which pixels belong to this cluster
    pixel_count: int  # How many pixels in this cluster
    
    def __str__(self) -> str:
        """Human-readable cluster representation: RGB color with pixel count."""
        r, g, b = self.centroid_rgb
        return f"RGB({r}, {g}, {b}) - {self.pixel_count} pixels"


def l_value_to_hueforge_layer(l_value: float, total_layers: int = 27) -> int:
    """
    Convert an L value (0-100) to a Hueforge layer number.
    
    Args:
        l_value: Luminance value (0-100)
        total_layers: Total layers in Hueforge (default: 27)
    
    Returns:
        Layer number (1-based, from 1 to total_layers)
    
    Example:
        >>> l_value_to_hueforge_layer(0.0)    # Darkest
        1
        >>> l_value_to_hueforge_layer(33.3)   # 1/3 up
        10
        >>> l_value_to_hueforge_layer(100.0)  # Brightest
        27
    """
    # Clamp L value to 0-100
    l_clamped = max(0.0, min(100.0, l_value))
    
    # Calculate layer (1-based)
    # Add small epsilon to handle edge case where L=100.0
    layer = int((l_clamped / 100.0) * total_layers) + 1
    
    # Clamp to valid layer range
    return max(1, min(total_layers, layer))


@dataclass
class ColorChange:
    """
    Represents a color transformation from luminance redistribution for HueForge optimization.
    
    Tracks the before/after state when redistributing luminance values evenly across
    a set of colors. This is used for HueForge 3D printing to spread colors across
    the 27 available layers and prevent multiple colors from bunching on the same layer.
    
    Attributes:
        original_rgb: Original RGB color before redistribution (0-255 each)
        original_lch: Original LCH color (L: 0-100, C: 0-100+, H: 0-360°)
        new_rgb: New RGB color after luminance redistribution (0-255 each)
        new_lch: New LCH color with redistributed L value (L: 0-100, C: 0-100+, H: 0-360°)
        delta_e: Perceptual color difference (Delta E 2000) between original and new
        hueforge_layer: Target HueForge layer number (1-27) based on new L value
    
    Example:
        >>> from color_tools.image import extract_color_clusters, redistribute_luminance
        >>> clusters = extract_color_clusters("image.jpg", n_colors=10)
        >>> colors = [c.centroid_rgb for c in clusters]
        >>> changes = redistribute_luminance(colors)
        >>> for change in changes:
        ...     print(f"Layer {change.hueforge_layer}: RGB{change.new_rgb} (ΔE: {change.delta_e:.1f})")
        Layer 3: RGB(45, 52, 71) (ΔE: 12.3)
        Layer 7: RGB(89, 95, 102) (ΔE: 18.7)
    """
    original_rgb: Tuple[int, int, int]
    original_lch: Tuple[float, float, float]
    new_rgb: Tuple[int, int, int]
    new_lch: Tuple[float, float, float]
    delta_e: float
    hueforge_layer: int  # Which Hueforge layer this color maps to
    
    def __str__(self) -> str:
        """Human-readable color change: layer assignment with delta E."""
        r, g, b = self.new_rgb
        return f"Layer {self.hueforge_layer}: RGB({r}, {g}, {b}) (ΔE {self.delta_e:.1f})"


def _check_pillow():
    """Raise ImportError if Pillow is not available."""
    if not PILLOW_AVAILABLE:
        raise ImportError(
            "Pillow is required for image analysis. "
            "Install it with: pip install -r requirements-image.txt"
        )


def extract_color_clusters(
    image_path: str, 
    n_colors: int = 10,
    use_lab_distance: bool = True
) -> List[ColorCluster]:
    """
    Extract color clusters from an image using k-means clustering.
    
    This uses k-means in LAB color space for perceptually uniform clustering.
    Returns full cluster data including pixel assignments for later remapping.
    
    Args:
        image_path: Path to the image file
        n_colors: Number of clusters to extract (default: 10)
        use_lab_distance: Use LAB space for perceptual distance (default: True)
    
    Returns:
        List of ColorCluster objects with centroids and pixel assignments
    
    Raises:
        ImportError: If Pillow is not installed
        FileNotFoundError: If image file doesn't exist
    
    Example:
        >>> clusters = extract_color_clusters("photo.jpg", n_colors=8)
        >>> for cluster in clusters:
        ...     print(f"Color: {cluster.centroid_rgb}, Pixels: {cluster.pixel_count}")
        Color: (255, 0, 0), Pixels: 1523
        Color: (0, 128, 255), Pixels: 892
        ...
    """
    _check_pillow()
    
    # Load image and convert to RGB
    img = Image.open(image_path)
    img = img.convert('RGB')
    
    # Get all pixels as a list of RGB tuples
    pixels_rgb = list(img.getdata())  # type: ignore
    
    # Convert to LAB if using perceptual distance
    if use_lab_distance:
        pixels_lab = [rgb_to_lab(p) for p in pixels_rgb]
        pixels_working = pixels_lab
    else:
        pixels_working = pixels_rgb
    
    # Initialize centroids (evenly spaced through pixel list)
    step = len(pixels_working) // n_colors
    centroids = [pixels_working[i * step] for i in range(n_colors)]
    
    # Run k-means for a fixed number of iterations
    cluster_assignments = [0] * len(pixels_working)
    
    for iteration in range(10):
        # Assign each pixel to nearest centroid
        for pixel_idx, pixel in enumerate(pixels_working):
            min_dist = float('inf')
            min_idx = 0
            
            for centroid_idx, centroid in enumerate(centroids):
                # Calculate distance (euclidean in current space)
                dist = sum((p - c) ** 2 for p, c in zip(pixel, centroid))
                if dist < min_dist:
                    min_dist = dist
                    min_idx = centroid_idx
            
            cluster_assignments[pixel_idx] = min_idx
        
        # Update centroids to mean of assigned pixels
        new_centroids = []
        for cluster_idx in range(n_colors):
            # Get all pixels assigned to this cluster
            cluster_pixels = [
                pixels_working[i] for i in range(len(pixels_working))
                if cluster_assignments[i] == cluster_idx
            ]
            
            if cluster_pixels:
                # Calculate mean
                n_components = len(cluster_pixels[0])
                avg = tuple(
                    sum(p[i] for p in cluster_pixels) / len(cluster_pixels)
                    for i in range(n_components)
                )
                new_centroids.append(avg)
            else:
                # Keep old centroid if cluster is empty
                new_centroids.append(centroids[cluster_idx])
        
        centroids = new_centroids
    
    # Build ColorCluster objects
    results = []
    for cluster_idx in range(n_colors):
        # Get pixel indices for this cluster
        pixel_indices = [
            i for i in range(len(cluster_assignments))
            if cluster_assignments[i] == cluster_idx
        ]
        
        # Convert centroid back to RGB if needed
        centroid = centroids[cluster_idx]
        if use_lab_distance:
            centroid_rgb_tuple = lab_to_rgb(centroid)  # type: ignore
            centroid_lab = centroid  # type: ignore
        else:
            centroid_rgb_tuple = tuple(int(round(c)) for c in centroid)  # type: ignore
            centroid_lab = rgb_to_lab(centroid_rgb_tuple)  # type: ignore
        
        results.append(ColorCluster(
            centroid_rgb=centroid_rgb_tuple,  # type: ignore
            centroid_lab=centroid_lab,  # type: ignore
            pixel_indices=pixel_indices,
            pixel_count=len(pixel_indices)
        ))
    
    return results


def extract_unique_colors(image_path: str, n_colors: int = 10) -> List[Tuple[int, int, int]]:
    """
    Extract unique colors from an image using k-means clustering.
    
    This is a simplified wrapper around extract_color_clusters that just
    returns the centroid RGB values for backward compatibility.
    
    Args:
        image_path: Path to the image file
        n_colors: Number of unique colors to extract (default: 10)
    
    Returns:
        List of RGB tuples (0-255 for each component)
    
    Raises:
        ImportError: If Pillow is not installed
        FileNotFoundError: If image file doesn't exist
    
    Example:
        >>> colors = extract_unique_colors("photo.jpg", n_colors=8)
        >>> print(colors)
        [(255, 0, 0), (0, 128, 255), ...]
    """
    clusters = extract_color_clusters(image_path, n_colors, use_lab_distance=True)
    return [cluster.centroid_rgb for cluster in clusters]


def redistribute_luminance(colors: List[Tuple[int, int, int]]) -> List[ColorChange]:
    """
    Redistribute luminance values evenly across a list of colors.
    
    This function:
    1. Converts colors to LCH space
    2. Sorts by L (luminance) value
    3. Redistributes L values evenly between 0 and 100
    4. Converts back to RGB
    5. Calculates Delta E for each change
    
    Args:
        colors: List of RGB tuples to redistribute
    
    Returns:
        List of ColorChange objects showing before/after for each color
    
    Example:
        >>> colors = [(100, 50, 30), (200, 180, 160), (50, 50, 50)]
        >>> changes = redistribute_luminance(colors)
        >>> for change in changes:
        ...     print(f"L: {change.original_lch[0]:.1f} -> {change.new_lch[0]:.1f}, ΔE={change.delta_e:.2f}")
        L: 24.3 -> 0.0, ΔE=12.45
        L: 53.2 -> 50.0, ΔE=3.21
        L: 76.8 -> 100.0, ΔE=23.14
    """
    # Convert all colors to LCH
    colors_lch = [(rgb, rgb_to_lch(rgb)) for rgb in colors]
    
    # Sort by L value
    colors_lch.sort(key=lambda x: x[1][0])
    
    # Redistribute L values evenly
    n_colors = len(colors_lch)
    results = []
    
    for i, (original_rgb, original_lch) in enumerate(colors_lch):
        # Calculate new L value evenly spaced from 0 to 100
        if n_colors == 1:
            new_l = 50.0  # Single color goes to middle
        else:
            new_l = (i / (n_colors - 1)) * 100.0
        
        # Create new LCH with redistributed L, keeping C and H the same
        new_lch = (new_l, original_lch[1], original_lch[2])
        
        # Convert back to RGB
        new_rgb = lch_to_rgb(new_lch)
        
        # Calculate Delta E between original and new
        delta_e = delta_e_2000(original_rgb, new_rgb)
        
        # Calculate Hueforge layer
        layer = l_value_to_hueforge_layer(new_l)
        
        results.append(ColorChange(
            original_rgb=original_rgb,
            original_lch=original_lch,
            new_rgb=new_rgb,
            new_lch=new_lch,
            delta_e=delta_e,
            hueforge_layer=layer
        ))
    
    return results


def format_color_change_report(changes: List[ColorChange]) -> str:
    """
    Format a human-readable report of color changes.
    
    Args:
        changes: List of ColorChange objects
    
    Returns:
        Formatted string showing before/after for each color
    
    Example:
        >>> changes = redistribute_luminance([(100, 50, 30), (200, 180, 160)])
        >>> print(format_color_change_report(changes))
        Color Luminance Redistribution Report
        =====================================
        
        1. RGB(100, 50, 30) → RGB(98, 48, 28)
           L: 24.3 → 33.3  |  C: 28.5 → 28.5  |  H: 31.2 → 31.2
           ΔE (CIEDE2000): 9.12
        
        ...
    """
    lines = [
        "Color Luminance Redistribution Report",
        "=" * 37,
        ""
    ]
    
    for i, change in enumerate(changes, 1):
        orig_l, orig_c, orig_h = change.original_lch
        new_l, new_c, new_h = change.new_lch
        
        lines.append(f"{i}. RGB{change.original_rgb} → RGB{change.new_rgb}")
        lines.append(f"   L: {orig_l:.1f} → {new_l:.1f}  |  "
                    f"C: {orig_c:.1f} → {new_c:.1f}  |  "
                    f"H: {orig_h:.1f} → {new_h:.1f}")
        lines.append(f"   ΔE (CIEDE2000): {change.delta_e:.2f}")
        lines.append(f"   Hueforge Layer: {change.hueforge_layer} (of 27)")
        lines.append("")
    
    return "\n".join(lines)

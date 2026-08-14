"""
Perceptual dominant-color analysis for images.

The algorithm identifies colors that contribute most strongly to an image's
visual identity rather than merely returning the most common RGB values.

Pipeline:

    image
      -> downsample
      -> RGB to CIELAB
      -> provisional k-means clustering
      -> CIEDE2000 perceptual cluster merging
      -> spatial analysis and OpenCV saliency detection
      -> diagnostic multiscale nearest-neighbor support
      -> perceptual dominance scoring
      -> CIEDE2000 diversity selection
      -> requested number of dominant colors

The provisional k-means stage is purely a computational reduction step.
Perceptual similarity and final palette selection use CIEDE2000.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image
from sklearn.cluster import KMeans

from color_tools.conversions import (
    lab_to_rgb,
    rgb_to_hex,
    rgb_to_hsl,
    rgb_to_lab,
    rgb_to_lch,
)
from color_tools.distance import delta_e_2000_array
from color_tools.palette import ColorRecord


RGB: TypeAlias = tuple[int, int, int]
Lab: TypeAlias = tuple[float, float, float]

FloatArray: TypeAlias = NDArray[np.float64]
IntArray: TypeAlias = NDArray[np.int32]
BoolArray: TypeAlias = NDArray[np.bool_]
UInt8Array: TypeAlias = NDArray[np.uint8]

SaliencyBackend: TypeAlias = Literal[
    "opencv_fine_grained",
    "opencv_spectral",
]


# ============================================================================
# Public result types
# ============================================================================


@dataclass(frozen=True)
class DominantColor:
    """
    A perceptually dominant color discovered in an image.

    Attributes:
        rgb:
            Representative sRGB color.

        lab:
            Representative CIELAB color.

        population:
            Fraction of analyzed image pixels belonging to this color cluster.

        dominance:
            Final perceptual-dominance score.

        global_salience:
            Perceptual distinctiveness from the image's other major colors.

        local_contrast:
            Average CIEDE2000 contrast against neighboring pixels.

        spatial_distribution:
            How broadly the color appears across the image.

        spatial_coherence:
            How strongly the color forms contiguous regions rather than
            scattered pixels.

        lightness_contrast:
            Difference in lightness from the image's population-weighted
            average lightness.

        focal_importance:
            Population-independent visual attention associated with the cluster,
            based on mean saliency per cluster pixel and normalized against the
            strongest cluster.
    """

    rgb: RGB
    lab: Lab

    population: float
    dominance: float

    global_salience: float
    local_contrast: float
    spatial_distribution: float
    spatial_coherence: float
    lightness_contrast: float
    focal_importance: float

    @property
    def hex(self) -> str:
        """Return the representative color as #RRGGBB."""
        return "#{:02X}{:02X}{:02X}".format(*self.rgb)


@dataclass(frozen=True)
class DominantColorDiagnostic:
    """Compact diagnostics for one surviving perceptual cluster."""

    rgb: RGB
    lab: Lab

    population: float
    population_score: float

    coarse_support: tuple[float, ...]
    coarse_support_mean: float
    coarse_support_ratio: float
    coarse_scale_persistence: float
    structural_support: float
    structural_penalty: float

    global_salience: float
    local_contrast: float
    spatial_coherence: float
    lightness_contrast: float

    chroma: float
    chromatic_prominence: float

    neutrality: float
    neutral_penalty: float

    focal_saliency_share: float
    mean_saliency: float
    normalized_mean_saliency: float
    focal_importance: float

    base_dominance: float
    dominance: float

    selected_rank: int | None
    selection_score: float | None
    nearest_selected_distance: float | None
    diversity_multiplier: float | None

    @property
    def hex(self) -> str:
        """Return the representative color as #RRGGBB."""
        return "#{:02X}{:02X}{:02X}".format(*self.rgb)


@dataclass(frozen=True)
class DominanceAnalysis:
    """
    Complete perceptual-dominance analysis.

    The diagnostics intentionally stay compact. They retain the image-level
    color-pop measurements, the candidate signals still used by the algorithm,
    and multiscale nearest-neighbor support used for the current experiment.
    """

    colors: tuple[DominantColor, ...]

    focal_center: tuple[float, float]
    focal_radius: float

    neutral_pixel_fraction: float
    neutral_cluster_fraction: float
    population_weighted_mean_chroma: float
    high_chroma_pixel_fraction: float
    accent_chroma_separation: float
    color_pop_strength: float

    coarse_dimensions: tuple[int, ...]

    saliency_map: FloatArray
    diagnostics: tuple[DominantColorDiagnostic, ...] = ()


def dominant_colors_to_palette(
    colors: list[DominantColor] | tuple[DominantColor, ...],
    *,
    source: str = "dominance",
    name_prefix: str = "Dominant",
) -> list[ColorRecord]:
    """
    Convert dominant-color results into palette-ready ColorRecord objects.

    Args:
        colors:
            Dominant colors returned by dominant_colors() or
            analyze_dominant_colors().colors.

        source:
            Source label recorded on each ColorRecord.

        name_prefix:
            Prefix used when generating color names such as "Dominant 1".
    """
    records: list[ColorRecord] = []

    for index, color in enumerate(colors, start=1):
        rgb = color.rgb
        records.append(
            ColorRecord(
                name=f"{name_prefix} {index}",
                hex=rgb_to_hex(rgb),
                rgb=rgb,
                hsl=rgb_to_hsl(rgb),
                lab=rgb_to_lab(rgb),
                lch=rgb_to_lch(rgb),
                source=source,
            )
        )

    return records


# ============================================================================
# Internal result types
# ============================================================================


@dataclass
class _DominantColorCandidate:
    """Internal mutable representation of a candidate perceptual color."""

    lab: FloatArray

    population: float
    population_score: float

    coarse_support: tuple[float, ...]
    coarse_support_mean: float
    coarse_support_ratio: float
    coarse_scale_persistence: float
    structural_support: float
    structural_penalty: float

    global_salience: float
    local_contrast: float
    spatial_distribution: float
    spatial_coherence: float
    lightness_contrast: float

    chroma: float
    normalized_chroma: float
    chroma_ratio_to_mean: float
    chromatic_distinctiveness: float
    chromatic_prominence: float

    neutrality: float
    population_protection: float
    neutral_penalty: float = 0.0

    focal_saliency_share: float = 0.0
    mean_saliency: float = 0.0
    normalized_mean_saliency: float = 0.0
    focal_importance: float = 0.0

    base_dominance: float = 0.0
    dominance: float = 0.0

    selected_rank: int | None = None
    selection_score: float | None = None
    nearest_selected_distance: float | None = None
    diversity_multiplier: float | None = None


def _lab_array_to_rgb(
    lab_array: FloatArray,
) -> RGB:
    """Convert a Lab ndarray representative to clamped integer RGB."""

    lab: Lab = (
        float(lab_array[0]),
        float(lab_array[1]),
        float(lab_array[2]),
    )

    rgb_result = lab_to_rgb(
        lab
    )

    return (
        int(np.clip(round(rgb_result[0]), 0, 255)),
        int(np.clip(round(rgb_result[1]), 0, 255)),
        int(np.clip(round(rgb_result[2]), 0, 255)),
    )


# ============================================================================
# Image preparation
# ============================================================================


def _load_image(
    image: Image.Image | str | Path,
) -> Image.Image:
    if isinstance(image, Image.Image):
        return image

    return Image.open(image)


def _resize_for_analysis(
    image: Image.Image,
    max_dimension: int,
) -> Image.Image:
    """
    Downsample an image while preserving aspect ratio.

    Analysis does not require full-resolution input and benefits substantially
    from bounded image dimensions.
    """

    width, height = image.size
    largest = max(width, height)

    if largest <= max_dimension:
        return image.copy()

    scale = max_dimension / largest

    size = (
        max(1, round(width * scale)),
        max(1, round(height * scale)),
    )

    return image.resize(
        size,
        Image.Resampling.NEAREST,
    )


def _prepare_image(
    image: Image.Image | str | Path,
    *,
    max_dimension: int,
    alpha_threshold: int,
) -> tuple[UInt8Array, BoolArray]:
    """
    Prepare image data for analysis.

    Returns:
        rgb_image:
            H x W x 3 uint8 RGB image.

        valid_mask:
            H x W boolean mask identifying pixels included in analysis.
    """

    source = _load_image(image)
    source = _resize_for_analysis(
        source,
        max_dimension,
    )
    source = source.convert("RGBA")

    rgba = np.asarray(
        source,
        dtype=np.uint8,
    )

    rgb_image = np.asarray(
        rgba[..., :3],
        dtype=np.uint8,
    )

    alpha = rgba[..., 3]

    valid_mask = np.asarray(
        alpha >= alpha_threshold,
        dtype=np.bool_,
    )

    if not np.any(valid_mask):
        raise ValueError(
            "Image contains no pixels meeting the alpha threshold."
        )

    return rgb_image, valid_mask


def _resize_nearest_short_side(
    image: Image.Image,
    target_dimension: int,
) -> Image.Image:
    """Resize so the short side matches target_dimension using nearest-neighbor."""

    width, height = image.size
    smallest = min(width, height)

    if smallest <= target_dimension:
        return image.copy()

    scale = target_dimension / smallest

    size = (
        max(1, round(width * scale)),
        max(1, round(height * scale)),
    )

    return image.resize(
        size,
        Image.Resampling.NEAREST,
    )


def _convert_rgb_values_to_lab(
    rgb_values: UInt8Array,
) -> FloatArray:
    """Convert an N x 3 RGB array to Lab while converting unique RGBs once."""

    if len(rgb_values) == 0:
        return np.empty(
            (0, 3),
            dtype=np.float64,
        )

    unique_rgb, inverse = np.unique(
        rgb_values,
        axis=0,
        return_inverse=True,
    )

    unique_lab = np.asarray(
        [
            rgb_to_lab(
                (
                    int(rgb[0]),
                    int(rgb[1]),
                    int(rgb[2]),
                )
            )
            for rgb in unique_rgb
        ],
        dtype=np.float64,
    )

    return np.asarray(
        unique_lab[inverse],
        dtype=np.float64,
    )


def _calculate_multiscale_coarse_support(
    image: Image.Image | str | Path,
    centroids: FloatArray,
    *,
    dimensions: tuple[int, ...],
    alpha_threshold: int,
) -> FloatArray:
    """
    Measure candidate occupancy on coarse nearest-neighbor views of the source.

    Each coarse pixel is assigned to the nearest surviving full-analysis
    candidate using CIEDE2000. This intentionally reuses the same candidate
    colors rather than reclustering each scale independently.

    Returns:
        Array shaped (candidate_count, scale_count), where each value is the
        fraction of valid pixels at that scale assigned to the candidate.
    """

    candidate_count = len(centroids)

    if candidate_count == 0:
        return np.empty(
            (0, len(dimensions)),
            dtype=np.float64,
        )

    source = _load_image(
        image
    ).convert("RGBA")

    support = np.zeros(
        (candidate_count, len(dimensions)),
        dtype=np.float64,
    )

    for scale_index, dimension in enumerate(dimensions):
        coarse = _resize_nearest_short_side(
            source,
            dimension,
        )

        rgba = np.asarray(
            coarse,
            dtype=np.uint8,
        )

        valid_mask = np.asarray(
            rgba[..., 3] >= alpha_threshold,
            dtype=np.bool_,
        )

        if not np.any(valid_mask):
            continue

        rgb_values = np.asarray(
            rgba[..., :3][valid_mask],
            dtype=np.uint8,
        )

        coarse_lab = _convert_rgb_values_to_lab(
            rgb_values
        )

        distances = np.asarray(
            delta_e_2000_array(
                coarse_lab[:, None, :],
                centroids[None, :, :],
            ),
            dtype=np.float64,
        )

        nearest = np.argmin(
            distances,
            axis=1,
        )

        counts = np.bincount(
            nearest,
            minlength=candidate_count,
        ).astype(np.float64)

        support[:, scale_index] = (
            counts / len(nearest)
        )

    return support


# ============================================================================
# Color conversion
# ============================================================================


def _convert_rgb_to_lab(
    rgb_image: UInt8Array,
    valid_mask: BoolArray,
) -> FloatArray:
    """
    Convert valid image pixels to CIELAB using color_tools.

    Unique RGB values are converted only once. This can drastically reduce
    conversion overhead for illustrations, screenshots, and other images
    containing repeated colors.
    """

    height, width, _ = rgb_image.shape

    valid_rgb = rgb_image[valid_mask]

    unique_rgb, inverse = np.unique(
        valid_rgb,
        axis=0,
        return_inverse=True,
    )

    unique_lab = np.asarray(
        [
            rgb_to_lab(
                (
                    int(rgb[0]),
                    int(rgb[1]),
                    int(rgb[2]),
                )
            )
            for rgb in unique_rgb
        ],
        dtype=np.float64,
    )

    valid_lab = unique_lab[inverse]

    lab_image = np.zeros(
        (height, width, 3),
        dtype=np.float64,
    )

    lab_image[valid_mask] = valid_lab

    return lab_image


# ============================================================================
# Provisional clustering
# ============================================================================


def _provisional_cluster(
    lab: FloatArray,
    *,
    cluster_count: int,
    iterations: int,
    seed: int,
) -> tuple[IntArray, FloatArray, NDArray[np.int64]]:
    """
    Perform provisional Euclidean clustering in CIELAB space.

    This is intentionally not the perceptual clustering stage. Its purpose is
    to reduce tens of thousands of pixels to a manageable set of candidate
    color regions.

    CIEDE2000 merging is applied afterward.
    """

    cluster_count = min(
        cluster_count,
        len(lab),
    )

    model = KMeans(
        n_clusters=cluster_count,
        init="k-means++",
        n_init="auto",
        max_iter=iterations,
        random_state=seed,
        algorithm="lloyd",
    )

    labels_raw = model.fit_predict(lab)

    labels = np.asarray(
        labels_raw,
        dtype=np.int32,
    )

    centroids = np.asarray(
        model.cluster_centers_,
        dtype=np.float64,
    )

    populations = np.asarray(
        np.bincount(
            labels,
            minlength=cluster_count,
        ),
        dtype=np.int64,
    )

    return (
        labels,
        centroids,
        populations,
    )


# ============================================================================
# Perceptual cluster merging
# ============================================================================


def _merge_perceptual_clusters(
    centroids: FloatArray,
    populations: NDArray[np.int64],
    *,
    merge_threshold: float,
) -> tuple[
    FloatArray,
    FloatArray,
    list[list[int]],
]:
    """
    Merge provisional clusters according to CIEDE2000 similarity.

    The closest pair is repeatedly merged until no pair remains within
    merge_threshold.

    Merged representatives are population-weighted Lab averages.
    """

    active_indices = [
        index
        for index, population in enumerate(populations)
        if int(population) > 0
    ]

    if not active_indices:
        raise ValueError(
            "Perceptual cluster merge requires at least one populated cluster."
        )

    merged_centroids = np.asarray(
        centroids[active_indices],
        dtype=np.float64,
    ).copy()

    merged_populations = np.asarray(
        populations[active_indices],
        dtype=np.float64,
    ).copy()

    groups: list[list[int]] = [
        [index]
        for index in active_indices
    ]

    while len(merged_centroids) > 1:
        distances = np.asarray(
            delta_e_2000_array(
                merged_centroids[:, None, :],
                merged_centroids[None, :, :],
            ),
            dtype=np.float64,
        )

        np.fill_diagonal(
            distances,
            np.inf,
        )

        flat_index = int(
            np.argmin(distances)
        )

        first, second = np.unravel_index(
            flat_index,
            distances.shape,
        )

        distance = float(
            distances[first, second]
        )

        if distance > merge_threshold:
            break

        if second < first:
            first, second = second, first

        first_population = float(
            merged_populations[first]
        )

        second_population = float(
            merged_populations[second]
        )

        merged_population = (
            first_population
            + second_population
        )

        merged_centroid = (
            merged_centroids[first] * first_population
            + merged_centroids[second] * second_population
        ) / merged_population

        merged_centroids[first] = merged_centroid
        merged_populations[first] = merged_population

        groups[first].extend(
            groups[second]
        )

        merged_centroids = np.delete(
            merged_centroids,
            second,
            axis=0,
        )

        merged_populations = np.delete(
            merged_populations,
            second,
        )

        del groups[second]

    return (
        np.asarray(
            merged_centroids,
            dtype=np.float64,
        ),
        np.asarray(
            merged_populations,
            dtype=np.float64,
        ),
        groups,
    )


def _remap_cluster_labels(
    provisional_labels: IntArray,
    groups: list[list[int]],
) -> IntArray:
    """Map provisional k-means labels onto merged perceptual clusters."""

    max_label = max(
        member
        for group in groups
        for member in group
    )

    remap = np.empty(
        max_label + 1,
        dtype=np.int32,
    )

    for merged_index, members in enumerate(groups):
        remap[members] = merged_index

    return np.asarray(
        remap[provisional_labels],
        dtype=np.int32,
    )


# ============================================================================
# Map normalization
# ============================================================================


def _normalize_map(
    values: FloatArray,
    valid_mask: BoolArray,
    *,
    percentile: float = 99.0,
) -> FloatArray:
    """
    Normalize spatial values into the range 0..1.

    Percentile normalization prevents isolated extreme values from flattening
    the useful range of the rest of the image.
    """

    result = np.zeros_like(
        values,
        dtype=np.float64,
    )

    valid_values = values[valid_mask]

    if len(valid_values) == 0:
        return result

    ceiling = float(
        np.percentile(
            valid_values,
            percentile,
        )
    )

    if ceiling <= 0.0:
        return result

    result[valid_mask] = np.clip(
        values[valid_mask] / ceiling,
        0.0,
        1.0,
    )

    return result


# ============================================================================
# Local contrast
# ============================================================================


def _calculate_local_contrast(
    lab_image: FloatArray,
    valid_mask: BoolArray,
) -> FloatArray:
    """
    Calculate local perceptual contrast using four-connected CIEDE2000
    neighbor distances.
    """

    height, width, _ = lab_image.shape

    total = np.zeros(
        (height, width),
        dtype=np.float64,
    )

    samples = np.zeros(
        (height, width),
        dtype=np.float64,
    )

    # Horizontal neighbors.

    horizontal_valid = (
        valid_mask[:, :-1]
        & valid_mask[:, 1:]
    )

    horizontal_distance = np.asarray(
        delta_e_2000_array(
            lab_image[:, :-1, :],
            lab_image[:, 1:, :],
        ),
        dtype=np.float64,
    )

    horizontal_distance = np.where(
        horizontal_valid,
        horizontal_distance,
        0.0,
    )

    total[:, :-1] += horizontal_distance
    total[:, 1:] += horizontal_distance

    samples[:, :-1] += horizontal_valid
    samples[:, 1:] += horizontal_valid

    # Vertical neighbors.

    vertical_valid = (
        valid_mask[:-1, :]
        & valid_mask[1:, :]
    )

    vertical_distance = np.asarray(
        delta_e_2000_array(
            lab_image[:-1, :, :],
            lab_image[1:, :, :],
        ),
        dtype=np.float64,
    )

    vertical_distance = np.where(
        vertical_valid,
        vertical_distance,
        0.0,
    )

    total[:-1, :] += vertical_distance
    total[1:, :] += vertical_distance

    samples[:-1, :] += vertical_valid
    samples[1:, :] += vertical_valid

    contrast = np.divide(
        total,
        samples,
        out=np.zeros_like(total),
        where=samples > 0,
    )

    return _normalize_map(
        np.asarray(
            contrast,
            dtype=np.float64,
        ),
        valid_mask,
    )


# ============================================================================
# Saliency / focal analysis
# ============================================================================


def _apply_center_bias(
    saliency: FloatArray,
    valid_mask: BoolArray,
    *,
    center_bias: float,
) -> FloatArray:
    """
    Optionally blend a weak center prior into an existing saliency map.

    The center prior is intentionally weak and optional. It should guide
    attention estimates rather than replace evidence from the image.
    """

    result = np.asarray(
        saliency,
        dtype=np.float64,
    ).copy()

    if center_bias <= 0.0:
        result[~valid_mask] = 0.0
        return result

    height, width = valid_mask.shape

    yy, xx = np.mgrid[
        0:height,
        0:width,
    ]

    nx = (
        xx - (width - 1) / 2
    ) / max(width / 2, 1)

    ny = (
        yy - (height - 1) / 2
    ) / max(height / 2, 1)

    distance = np.sqrt(
        nx * nx
        + ny * ny
    )

    center = np.clip(
        1.0 - distance,
        0.0,
        1.0,
    )

    result = (
        result * (1.0 - center_bias)
        + center * center_bias
    )

    result[~valid_mask] = 0.0

    return np.asarray(
        result,
        dtype=np.float64,
    )


def _calculate_opencv_saliency_map(
    rgb_image: UInt8Array,
    valid_mask: BoolArray,
    *,
    backend: Literal[
        "opencv_fine_grained",
        "opencv_spectral",
    ],
    center_bias: float,
) -> FloatArray:
    """
    Calculate static image saliency with OpenCV contrib.

    Fine Grained is the default because it produces a spatially detailed
    saliency map that is useful for assigning visual-attention importance to
    perceptual color clusters.
    """

    bgr_image = cv2.cvtColor(
        rgb_image,
        cv2.COLOR_RGB2BGR,
    )

    if backend == "opencv_fine_grained":
        detector = (
            cv2.saliency.StaticSaliencyFineGrained.create()
        )
    else:
        detector = (
            cv2.saliency.StaticSaliencySpectralResidual.create()
        )

    success, saliency_map = detector.computeSaliency(
        bgr_image
    )

    if not success:
        raise RuntimeError(
            f"OpenCV saliency computation failed for backend {backend!r}."
        )

    saliency = np.asarray(
        saliency_map,
        dtype=np.float64,
    )

    if saliency.ndim == 3:
        saliency = saliency[..., 0]

    if saliency.shape != valid_mask.shape:
        saliency = cv2.resize(
            saliency,
            (
                valid_mask.shape[1],
                valid_mask.shape[0],
            ),
            interpolation=cv2.INTER_LINEAR,
        )
        saliency = np.asarray(
            saliency,
            dtype=np.float64,
        )

    saliency[~valid_mask] = 0.0

    saliency = _apply_center_bias(
        saliency,
        valid_mask,
        center_bias=center_bias,
    )

    return _normalize_map(
        saliency,
        valid_mask,
        percentile=100.0,
    )


def _calculate_saliency_map(
    rgb_image: UInt8Array,
    valid_mask: BoolArray,
    *,
    saliency_backend: SaliencyBackend,
    center_bias: float,
) -> FloatArray:
    """Calculate saliency using the configured OpenCV static saliency backend."""

    return _calculate_opencv_saliency_map(
        rgb_image,
        valid_mask,
        backend=saliency_backend,
        center_bias=center_bias,
    )


def _calculate_focal_region(
    saliency: FloatArray,
    valid_mask: BoolArray,
    *,
    contained_saliency: float,
) -> tuple[
    tuple[float, float],
    float,
]:
    """
    Calculate a saliency-weighted focal center and focal radius.

    focal_center:
        Normalized x/y coordinates in the range 0..1.

    focal_radius:
        Normalized Euclidean image-space radius containing the requested
        fraction of accumulated saliency.
    """

    height, width = saliency.shape

    total_saliency = float(
        saliency.sum()
    )

    if total_saliency <= 0.0:
        return (
            (0.5, 0.5),
            1.0,
        )

    yy, xx = np.mgrid[
        0:height,
        0:width,
    ]

    x_normalized = (
        xx / max(width - 1, 1)
    )

    y_normalized = (
        yy / max(height - 1, 1)
    )

    focal_x = float(
        np.sum(
            x_normalized * saliency
        )
        / total_saliency
    )

    focal_y = float(
        np.sum(
            y_normalized * saliency
        )
        / total_saliency
    )

    distance = np.sqrt(
        (x_normalized - focal_x) ** 2
        + (y_normalized - focal_y) ** 2
    )

    valid_distance = np.asarray(
        distance[valid_mask],
        dtype=np.float64,
    )

    valid_saliency = np.asarray(
        saliency[valid_mask],
        dtype=np.float64,
    )

    order = np.argsort(
        valid_distance
    )

    cumulative = np.cumsum(
        valid_saliency[order]
    )

    target = (
        total_saliency
        * contained_saliency
    )

    index = int(
        np.searchsorted(
            cumulative,
            target,
        )
    )

    index = min(
        index,
        len(order) - 1,
    )

    focal_radius = float(
        valid_distance[
            order[index]
        ]
    )

    return (
        (focal_x, focal_y),
        focal_radius,
    )


# ============================================================================
# Spatial metrics
# ============================================================================


def _calculate_spatial_distribution(
    mask: BoolArray,
    valid_mask: BoolArray,
    *,
    grid_size: int,
    minimum_cell_coverage: float,
) -> float:
    """
    Measure how broadly a cluster occurs throughout the image.

    Each grid cell is considered occupied when the cluster represents at
    least minimum_cell_coverage of the valid pixels in that cell.
    """

    height, width = mask.shape

    occupied = 0
    total = 0

    for gy in range(grid_size):
        y0 = gy * height // grid_size
        y1 = (gy + 1) * height // grid_size

        for gx in range(grid_size):
            x0 = gx * width // grid_size
            x1 = (gx + 1) * width // grid_size

            cell_mask = mask[
                y0:y1,
                x0:x1,
            ]

            cell_valid = valid_mask[
                y0:y1,
                x0:x1,
            ]

            valid_count = int(
                np.count_nonzero(cell_valid)
            )

            if valid_count == 0:
                continue

            total += 1

            cluster_count = int(
                np.count_nonzero(
                    cell_mask & cell_valid
                )
            )

            coverage = (
                cluster_count
                / valid_count
            )

            if coverage >= minimum_cell_coverage:
                occupied += 1

    if total == 0:
        return 0.0

    return occupied / total


def _calculate_coherence_map(
    labels: IntArray,
    valid_mask: BoolArray,
) -> FloatArray:
    """
    Estimate local spatial coherence from same-cluster neighbor agreement.

    Pixels surrounded by the same perceptual cluster approach 1.0.
    Highly fragmented regions approach 0.0.
    """

    height, width = labels.shape

    matches = np.zeros(
        (height, width),
        dtype=np.float64,
    )

    samples = np.zeros(
        (height, width),
        dtype=np.float64,
    )

    # Horizontal neighbors.

    horizontal_valid = (
        valid_mask[:, :-1]
        & valid_mask[:, 1:]
    )

    horizontal_same = (
        labels[:, :-1]
        == labels[:, 1:]
    ) & horizontal_valid

    matches[:, :-1] += horizontal_same
    matches[:, 1:] += horizontal_same

    samples[:, :-1] += horizontal_valid
    samples[:, 1:] += horizontal_valid

    # Vertical neighbors.

    vertical_valid = (
        valid_mask[:-1, :]
        & valid_mask[1:, :]
    )

    vertical_same = (
        labels[:-1, :]
        == labels[1:, :]
    ) & vertical_valid

    matches[:-1, :] += vertical_same
    matches[1:, :] += vertical_same

    samples[:-1, :] += vertical_valid
    samples[1:, :] += vertical_valid

    coherence = np.divide(
        matches,
        samples,
        out=np.zeros_like(matches),
        where=samples > 0,
    )

    coherence[~valid_mask] = 0.0

    return np.asarray(
        coherence,
        dtype=np.float64,
    )


# ============================================================================
# Public analysis
# ============================================================================


def analyze_dominant_colors(
    image: Image.Image | str | Path,
    count: int = 8,
    *,
    provisional_clusters: int | None = None,
    merge_threshold: float = 5.0,
    focal_weight: float = 0.25,
    center_bias: float = 0.10,
    focal_saliency: float = 0.80,
    diversity_distance: float = 15.0,
    diversity_floor: float = 0.35,
    max_dimension: int = 256,
    coarse_dimensions: tuple[int, ...] = (32, 64, 96),
    alpha_threshold: int = 16,
    grid_size: int = 4,
    minimum_cell_coverage: float = 0.02,
    kmeans_iterations: int = 100,
    seed: int = 42,
    saliency_backend: SaliencyBackend = "opencv_fine_grained",
) -> DominanceAnalysis:
    """
    Analyze the perceptually dominant colors in an image.

    Args:
        image:
            PIL Image or filesystem path.

        count:
            Number of final colors to return. This does not determine the
            number of internal perceptual clusters.

        provisional_clusters:
            Number of initial k-means clusters used for computational
            reduction. Defaults to max(count * 8, 48), capped at 128.

        merge_threshold:
            Maximum CIEDE2000 distance at which provisional clusters are
            considered perceptually similar enough to merge.

        focal_weight:
            Influence of visual saliency on final color dominance.
            0 disables focal weighting.

        center_bias:
            Strength of the optional center prior used by the saliency model.

        focal_saliency:
            Fraction of accumulated saliency enclosed by focal_radius.

        diversity_distance:
            CIEDE2000 distance considered fully distinct during final palette
            selection.

        diversity_floor:
            Minimum score multiplier applied to a color that is perceptually
            redundant with an already-selected color.

        max_dimension:
            Maximum image dimension used during the normal analysis path.

        coarse_dimensions:
            Long-side dimensions used for diagnostic nearest-neighbor structural
            support. These coarse views do not affect scoring or selection.

        alpha_threshold:
            Pixels with lower alpha values are excluded.

        grid_size:
            Grid resolution used for spatial-distribution analysis.

        minimum_cell_coverage:
            Minimum cluster coverage required for a grid cell to count as
            spatially occupied.

        kmeans_iterations:
            Maximum iterations for provisional k-means clustering.

        seed:
            Deterministic random seed used by k-means.

        saliency_backend:
            OpenCV static saliency detector used for focal weighting.
            Fine Grained is the default; Spectral Residual is also available.

    Returns:
        DominanceAnalysis containing selected colors and focal information.
    """

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    if count < 1:
        raise ValueError(
            "count must be at least 1."
        )

    if provisional_clusters is not None and provisional_clusters < 1:
        raise ValueError(
            "provisional_clusters must be at least 1."
        )

    if merge_threshold < 0.0:
        raise ValueError(
            "merge_threshold cannot be negative."
        )

    if not 0.0 <= focal_weight <= 1.0:
        raise ValueError(
            "focal_weight must be between 0 and 1."
        )

    if not 0.0 <= center_bias <= 1.0:
        raise ValueError(
            "center_bias must be between 0 and 1."
        )

    if not 0.0 < focal_saliency <= 1.0:
        raise ValueError(
            "focal_saliency must be greater than 0 and at most 1."
        )

    if diversity_distance <= 0.0:
        raise ValueError(
            "diversity_distance must be greater than 0."
        )

    if not 0.0 <= diversity_floor <= 1.0:
        raise ValueError(
            "diversity_floor must be between 0 and 1."
        )

    if max_dimension < 1:
        raise ValueError(
            "max_dimension must be at least 1."
        )

    if not coarse_dimensions:
        raise ValueError(
            "coarse_dimensions must contain at least one dimension."
        )

    if any(dimension < 1 for dimension in coarse_dimensions):
        raise ValueError(
            "Every coarse dimension must be at least 1."
        )

    coarse_dimensions = tuple(
        sorted(
            set(
                int(dimension)
                for dimension in coarse_dimensions
            )
        )
    )

    if not 0 <= alpha_threshold <= 255:
        raise ValueError(
            "alpha_threshold must be between 0 and 255."
        )

    if grid_size < 1:
        raise ValueError(
            "grid_size must be at least 1."
        )

    if not 0.0 <= minimum_cell_coverage <= 1.0:
        raise ValueError(
            "minimum_cell_coverage must be between 0 and 1."
        )

    if kmeans_iterations < 1:
        raise ValueError(
            "kmeans_iterations must be at least 1."
        )

    if saliency_backend not in (
        "opencv_fine_grained",
        "opencv_spectral",
    ):
        raise ValueError(
            "saliency_backend must be one of "
            "'opencv_fine_grained' or 'opencv_spectral'."
        )

    # ------------------------------------------------------------------
    # Prepare image
    # ------------------------------------------------------------------

    rgb_image, valid_mask = _prepare_image(
        image,
        max_dimension=max_dimension,
        alpha_threshold=alpha_threshold,
    )

    lab_image = _convert_rgb_to_lab(
        rgb_image,
        valid_mask,
    )

    valid_lab = np.asarray(
        lab_image[valid_mask],
        dtype=np.float64,
    )

    total_pixels = len(
        valid_lab
    )

    distinct_color_count = len(
        np.unique(
            valid_lab,
            axis=0,
        )
    )

    # ------------------------------------------------------------------
    # Provisional clustering
    # ------------------------------------------------------------------

    if provisional_clusters is None:
        provisional_clusters = min(
            max(
                count * 8,
                48,
            ),
            128,
        )

    provisional_clusters = min(
        provisional_clusters,
        total_pixels,
    )

    provisional_clusters = min(
        provisional_clusters,
        distinct_color_count,
    )

    (
        provisional_labels,
        provisional_centroids,
        provisional_populations,
    ) = _provisional_cluster(
        valid_lab,
        cluster_count=provisional_clusters,
        iterations=kmeans_iterations,
        seed=seed,
    )

    # ------------------------------------------------------------------
    # Perceptual merging
    # ------------------------------------------------------------------

    (
        centroids,
        populations,
        groups,
    ) = _merge_perceptual_clusters(
        provisional_centroids,
        provisional_populations,
        merge_threshold=merge_threshold,
    )

    merged_valid_labels = (
        _remap_cluster_labels(
            provisional_labels,
            groups,
        )
    )

    label_image = np.full(
        valid_mask.shape,
        -1,
        dtype=np.int32,
    )

    label_image[
        valid_mask
    ] = merged_valid_labels

    cluster_count = len(
        centroids
    )

    population_fraction = np.asarray(
        populations / total_pixels,
        dtype=np.float64,
    )

    coarse_support_matrix = _calculate_multiscale_coarse_support(
        image,
        centroids,
        dimensions=coarse_dimensions,
        alpha_threshold=alpha_threshold,
    )

    # ------------------------------------------------------------------
    # Spatial analysis
    # ------------------------------------------------------------------

    local_contrast_map = (
        _calculate_local_contrast(
            lab_image,
            valid_mask,
        )
    )

    saliency_map = (
        _calculate_saliency_map(
            rgb_image,
            valid_mask,
            saliency_backend=saliency_backend,
            center_bias=center_bias,
        )
    )

    focal_center, focal_radius = (
        _calculate_focal_region(
            saliency_map,
            valid_mask,
            contained_saliency=focal_saliency,
        )
    )

    coherence_map = (
        _calculate_coherence_map(
            label_image,
            valid_mask,
        )
    )

    # ------------------------------------------------------------------
    # Global perceptual relationships
    # ------------------------------------------------------------------

    cluster_distances = np.asarray(
        delta_e_2000_array(
            centroids[:, None, :],
            centroids[None, :, :],
        ),
        dtype=np.float64,
    )

    global_salience = np.asarray(
        (
            cluster_distances
            * population_fraction[None, :]
        ).sum(axis=1),
        dtype=np.float64,
    )

    max_global_salience = float(
        global_salience.max()
    )

    if max_global_salience > 0.0:
        global_salience /= (
            max_global_salience
        )

    # ------------------------------------------------------------------
    # Reference statistics
    # ------------------------------------------------------------------

    global_mean_lightness = float(
        np.average(
            centroids[:, 0],
            weights=populations,
        )
    )

    # ------------------------------------------------------------------
    # Chromatic prominence diagnostics
    # ------------------------------------------------------------------
    #
    # Chroma measures distance from the neutral axis in the Lab a*/b* plane.
    # It is kept image-relative rather than treated as an absolute virtue.
    #
    # Chromatic distinctiveness measures how far each cluster's chromatic
    # vector is from the other surviving clusters, weighted by their image
    # populations. L* is intentionally excluded here so tonal contrast does
    # not masquerade as chromatic identity.
    #
    # Chromatic prominence is an experimental diagnostic only. The geometric
    # mean requires a color to be both chromatic and chromatically distinct;
    # a neutral cluster cannot score highly merely because it is far from a
    # vivid cluster.
    # ------------------------------------------------------------------

    cluster_chroma = np.sqrt(
        centroids[:, 1] ** 2
        + centroids[:, 2] ** 2
    )

    max_cluster_chroma = float(
        cluster_chroma.max()
    )

    mean_cluster_chroma = float(
        np.average(
            cluster_chroma,
            weights=populations,
        )
    )

    chromatic_vectors = np.asarray(
        centroids[:, 1:3],
        dtype=np.float64,
    )

    chromatic_distances = np.linalg.norm(
        chromatic_vectors[:, None, :]
        - chromatic_vectors[None, :, :],
        axis=2,
    )

    chromatic_distinctiveness = np.asarray(
        (
            chromatic_distances
            * population_fraction[None, :]
        ).sum(axis=1),
        dtype=np.float64,
    )

    max_chromatic_distinctiveness = float(
        chromatic_distinctiveness.max()
    )

    if max_chromatic_distinctiveness > 0.0:
        chromatic_distinctiveness /= max_chromatic_distinctiveness

    # ------------------------------------------------------------------
    # Image-level color-pop diagnostics
    # ------------------------------------------------------------------
    #
    # These metrics intentionally do not modify ranking yet. They test whether
    # mostly-neutral images with a relatively small set of strong chromatic
    # accents can be detected reliably enough to justify a conditional neutral
    # de-weighting stage later.
    #
    # Neutrality uses absolute Lab chroma because the neutral axis is meaningful.
    # Accent detection is image-relative so naturally muted images are not
    # mislabeled merely because a few colors are slightly stronger.
    # ------------------------------------------------------------------

    neutral_chroma_threshold = 12.0

    neutral_clusters = np.asarray(
        cluster_chroma <= neutral_chroma_threshold,
        dtype=np.bool_,
    )

    neutral_pixel_fraction = float(
        population_fraction[neutral_clusters].sum()
    )

    neutral_cluster_fraction = float(
        np.count_nonzero(neutral_clusters)
        / max(cluster_count, 1)
    )

    population_weighted_mean_chroma = mean_cluster_chroma

    if mean_cluster_chroma > 0.0:
        high_chroma_clusters = np.asarray(
            cluster_chroma >= mean_cluster_chroma * 2.0,
            dtype=np.bool_,
        )
    else:
        high_chroma_clusters = np.zeros(
            cluster_count,
            dtype=np.bool_,
        )

    high_chroma_pixel_fraction = float(
        population_fraction[high_chroma_clusters].sum()
    )

    sorted_chroma = np.sort(
        np.asarray(
            cluster_chroma,
            dtype=np.float64,
        )
    )

    accent_count = min(
        3,
        len(sorted_chroma),
    )

    strongest_accent_chroma = float(
        sorted_chroma[-accent_count:].mean()
    )

    if mean_cluster_chroma > 0.0:
        accent_ratio = (
            strongest_accent_chroma
            / mean_cluster_chroma
        )
    else:
        accent_ratio = 0.0

    # Ratios around 1.5 are not especially accent-like; 4.0+ is treated as
    # strongly separated. This is diagnostic normalization, not a scoring rule.
    accent_chroma_separation = float(
        np.clip(
            (accent_ratio - 1.5)
            / 2.5,
            0.0,
            1.0,
        )
    )

    # A color-pop composition should have substantial neutral coverage plus
    # strong accents. Sparse high-chroma coverage reinforces the diagnosis but
    # does not act as a hard gate.
    neutral_strength = float(
        np.clip(
            (neutral_pixel_fraction - 0.50)
            / 0.35,
            0.0,
            1.0,
        )
    )

    accent_sparsity = float(
        np.clip(
            (0.35 - high_chroma_pixel_fraction)
            / 0.30,
            0.0,
            1.0,
        )
    )

    color_pop_strength = float(
        neutral_strength
        * accent_chroma_separation
        * (
            0.75
            + accent_sparsity * 0.25
        )
    )

    total_saliency = float(
        saliency_map.sum()
    )

    max_population = float(
        population_fraction.max()
    )

    # ------------------------------------------------------------------
    # Candidate measurements
    # ------------------------------------------------------------------

    candidates: list[
        _DominantColorCandidate
    ] = []

    for index in range(
        cluster_count
    ):
        mask = np.asarray(
            label_image == index,
            dtype=np.bool_,
        )

        population = float(
            population_fraction[index]
        )

        population_score = float(
            np.sqrt(
                population
                / max_population
            )
        )

        coarse_support_array = np.asarray(
            coarse_support_matrix[index],
            dtype=np.float64,
        )

        coarse_support = tuple(
            float(value)
            for value in coarse_support_array
        )

        coarse_support_mean = float(
            coarse_support_array.mean()
        )

        coarse_support_ratio = (
            coarse_support_mean / population
            if population > 0.0
            else 0.0
        )

        coarse_scale_persistence = float(
            np.count_nonzero(
                coarse_support_array > 0.0
            )
            / len(coarse_support_array)
        )

        local_contrast = float(
            local_contrast_map[
                mask
            ].mean()
        )

        spatial_distribution = (
            _calculate_spatial_distribution(
                mask,
                valid_mask,
                grid_size=grid_size,
                minimum_cell_coverage=minimum_cell_coverage,
            )
        )

        spatial_coherence = float(
            coherence_map[
                mask
            ].mean()
        )

        lightness_contrast = min(
            abs(
                float(
                    centroids[index, 0]
                )
                - global_mean_lightness
            )
            / 100.0,
            1.0,
        )

        chroma = float(
            cluster_chroma[index]
        )

        normalized_chroma = (
            chroma / max_cluster_chroma
            if max_cluster_chroma > 0.0
            else 0.0
        )

        chroma_ratio_to_mean = (
            chroma / mean_cluster_chroma
            if mean_cluster_chroma > 0.0
            else 0.0
        )

        cluster_chromatic_distinctiveness = float(
            chromatic_distinctiveness[index]
        )

        chromatic_prominence = float(
            np.sqrt(
                normalized_chroma
                * cluster_chromatic_distinctiveness
            )
        )

        # ------------------------------------------------------------------
        # Proposed color-pop neutral handling diagnostics
        # ------------------------------------------------------------------
        #
        # Neutrality is a smooth function of absolute Lab chroma:
        #   C <= 5   -> fully neutral
        #   C >= 20  -> fully chromatic for this modifier
        #
        # This is intentionally diagnostic only for now.
        neutrality = float(
            np.clip(
                (20.0 - chroma)
                / 15.0,
                0.0,
                1.0,
            )
        )

        # Extremely high-coverage colors receive protection from any future
        # neutral penalty so a genuine background/field color is not discarded
        # merely because it is neutral.
        #
        # Protection ramps from zero at 10% coverage to full at 50% coverage.
        population_protection = float(
            np.clip(
                (population - 0.10)
                / 0.40,
                0.0,
                1.0,
            )
        )

        cluster_saliency = saliency_map[mask]

        if total_saliency > 0.0:
            focal_saliency_share = float(
                cluster_saliency.sum()
                / total_saliency
            )
        else:
            focal_saliency_share = population

        mean_saliency = float(
            cluster_saliency.mean()
        )

        candidates.append(
            _DominantColorCandidate(
                lab=np.asarray(
                    centroids[index],
                    dtype=np.float64,
                ),
                population=population,
                population_score=population_score,
                coarse_support=coarse_support,
                coarse_support_mean=coarse_support_mean,
                coarse_support_ratio=coarse_support_ratio,
                coarse_scale_persistence=coarse_scale_persistence,
                structural_support=1.0,
                structural_penalty=0.0,
                global_salience=float(
                    global_salience[index]
                ),
                local_contrast=local_contrast,
                spatial_distribution=spatial_distribution,
                spatial_coherence=spatial_coherence,
                lightness_contrast=lightness_contrast,
                chroma=chroma,
                normalized_chroma=normalized_chroma,
                chroma_ratio_to_mean=chroma_ratio_to_mean,
                chromatic_distinctiveness=cluster_chromatic_distinctiveness,
                chromatic_prominence=chromatic_prominence,
                neutrality=neutrality,
                population_protection=population_protection,
                neutral_penalty=0.0,
                focal_saliency_share=focal_saliency_share,
                mean_saliency=mean_saliency,
                focal_importance=mean_saliency,
            )
        )

    # ------------------------------------------------------------------
    # Normalize focal diagnostics
    # ------------------------------------------------------------------
    #
    # focal_saliency_share remains available as a diagnostic showing the
    # fraction of total saliency mass owned by a cluster. It is intentionally
    # NOT used for focal weighting because it is strongly correlated with
    # cluster population.
    #
    # focal_importance instead uses mean saliency per cluster pixel, normalized
    # against the strongest cluster. This measures how attention-worthy the
    # cluster is independently of how much image area it occupies.
    # ------------------------------------------------------------------

    max_mean_saliency = max(
        candidate.mean_saliency
        for candidate in candidates
    )

    if max_mean_saliency > 0.0:
        for candidate in candidates:
            normalized_mean_saliency = (
                candidate.mean_saliency
                / max_mean_saliency
            )
            candidate.normalized_mean_saliency = normalized_mean_saliency
            candidate.focal_importance = normalized_mean_saliency
    else:
        for candidate in candidates:
            candidate.normalized_mean_saliency = 0.0
            candidate.focal_importance = 0.0

    # ------------------------------------------------------------------
    # Dominance
    # ------------------------------------------------------------------
    #
    # Structural score:
    #
    #   30% coverage
    #   35% global perceptual salience
    #   15% local perceptual contrast
    #   15% spatial coherence
    #    5% relative lightness
    #
    # Intrinsic dominance:
    #
    #   80% structural score
    #   20% chromatic prominence
    #
    # Spatial distribution is retained as diagnostic metadata but is not
    # rewarded in the base score. Broad image coverage is already represented
    # by population, and distribution otherwise biases the ranking toward
    # structural/background colors that appear across many regions.
    #
    # Visual attention is deliberately applied as a separate blend using
    # population-independent mean saliency.
    # ------------------------------------------------------------------

    for candidate in candidates:
        structural_dominance = (
            candidate.population_score * 0.30
            + candidate.global_salience * 0.35
            + candidate.local_contrast * 0.15
            + candidate.spatial_coherence * 0.15
            + candidate.lightness_contrast * 0.05
        )

        # Chromatic prominence contributes 20% of intrinsic dominance.
        #
        # The remaining 80% preserves the existing structural/perceptual
        # dominance model. This is intentionally a conservative first blend so
        # chromatic identity can influence ranking without making vivid colors
        # universally dominant.
        candidate.base_dominance = (
            structural_dominance * 0.80
            + candidate.chromatic_prominence * 0.20
        )

        candidate.dominance = (
            candidate.base_dominance
            * (1.0 - focal_weight)
            + candidate.focal_importance
            * focal_weight
        )

    # ------------------------------------------------------------------
    # Color-pop neutral adjustment
    # ------------------------------------------------------------------

    maximum_neutral_penalty = 0.35

    for candidate in candidates:
        candidate.neutral_penalty = float(
            color_pop_strength
            * candidate.neutrality
            * (1.0 - candidate.population_protection)
            * maximum_neutral_penalty
        )

        candidate.dominance = float(
            candidate.dominance
            * (1.0 - candidate.neutral_penalty)
        )

    # ------------------------------------------------------------------
    # Multiscale structural-support adjustment
    # ------------------------------------------------------------------
    #
    # Coarse nearest-neighbor views provide evidence that a candidate occupies a
    # compositionally meaningful region rather than existing mainly as a
    # high-frequency fringe/antialiasing artifact.
    #
    # A candidate that survives at every coarse scale is not penalized.
    # Partial persistence can be rescued by meaningful absolute coarse coverage.
    # Population protection prevents coarse sampling from suppressing genuinely
    # large image regions.
    #
    # This modifier is deliberately conservative and does not reward candidates;
    # it only reduces dominance when structural support is weak.
    # ------------------------------------------------------------------

    maximum_structural_penalty = 0.50
    coarse_rescue_coverage = 0.005
    population_protection_start = 0.001
    population_protection_full = 0.020

    for candidate in candidates:
        coarse_coverage_support = float(
            np.clip(
                candidate.coarse_support_mean
                / coarse_rescue_coverage,
                0.0,
                1.0,
            )
        )

        candidate.structural_support = max(
            candidate.coarse_scale_persistence,
            coarse_coverage_support,
        )

        structural_population_protection = float(
            np.clip(
                (
                    candidate.population
                    - population_protection_start
                )
                / (
                    population_protection_full
                    - population_protection_start
                ),
                0.0,
                1.0,
            )
        )

        candidate.structural_penalty = float(
            maximum_structural_penalty
            * (1.0 - candidate.structural_support)
            * (1.0 - structural_population_protection)
        )

        candidate.dominance = float(
            candidate.dominance
            * (1.0 - candidate.structural_penalty)
        )

    # ------------------------------------------------------------------
    # Final perceptual-diversity selection
    # ------------------------------------------------------------------

    selected: list[
        _DominantColorCandidate
    ] = []

    remaining = list(
        candidates
    )

    while (
        remaining
        and len(selected) < count
    ):
        best_selection_score: float
        best_nearest_distance: float | None
        best_diversity_multiplier: float

        if not selected:
            best = max(
                remaining,
                key=lambda candidate: candidate.dominance,
            )

            best_selection_score = best.dominance
            best_nearest_distance = None
            best_diversity_multiplier = 1.0

        else:
            selected_lab = np.asarray(
                [
                    candidate.lab
                    for candidate in selected
                ],
                dtype=np.float64,
            )

            best: _DominantColorCandidate | None = None
            best_score = -np.inf
            best_distance: float | None = None
            best_multiplier = 1.0

            for candidate in remaining:
                distances = np.asarray(
                    delta_e_2000_array(
                        selected_lab,
                        candidate.lab,
                    ),
                    dtype=np.float64,
                )

                nearest_distance = float(
                    np.min(
                        distances
                    )
                )

                diversity = min(
                    nearest_distance
                    / diversity_distance,
                    1.0,
                )

                diversity_multiplier = (
                    diversity_floor
                    + diversity
                    * (
                        1.0
                        - diversity_floor
                    )
                )

                score = (
                    candidate.dominance
                    * diversity_multiplier
                )

                if score > best_score:
                    best = candidate
                    best_score = score
                    best_distance = nearest_distance
                    best_multiplier = diversity_multiplier

            if best is None:
                break

            best_selection_score = float(
                best_score
            )
            best_nearest_distance = best_distance
            best_diversity_multiplier = best_multiplier

        best.selected_rank = len(selected) + 1
        best.selection_score = best_selection_score
        best.nearest_selected_distance = best_nearest_distance
        best.diversity_multiplier = best_diversity_multiplier

        selected.append(
            best
        )

        best_index = next(
            index
            for index, candidate in enumerate(remaining)
            if candidate is best
        )

        remaining.pop(
            best_index
        )

    # ------------------------------------------------------------------
    # Public results
    # ------------------------------------------------------------------

    colors: list[
        DominantColor
    ] = []

    for candidate in selected:
        lab_array = candidate.lab

        lab: Lab = (
            float(lab_array[0]),
            float(lab_array[1]),
            float(lab_array[2]),
        )

        rgb: RGB = _lab_array_to_rgb(
            lab_array
        )

        colors.append(
            DominantColor(
                rgb=rgb,
                lab=lab,
                population=candidate.population,
                dominance=candidate.dominance,
                global_salience=candidate.global_salience,
                local_contrast=candidate.local_contrast,
                spatial_distribution=candidate.spatial_distribution,
                spatial_coherence=candidate.spatial_coherence,
                lightness_contrast=candidate.lightness_contrast,
                focal_importance=candidate.focal_importance,
            )
        )

    diagnostics: list[DominantColorDiagnostic] = []

    for candidate in sorted(
        candidates,
        key=lambda item: item.dominance,
        reverse=True,
    ):
        diagnostic_rgb = _lab_array_to_rgb(
            candidate.lab
        )

        diagnostic_lab: Lab = (
            float(candidate.lab[0]),
            float(candidate.lab[1]),
            float(candidate.lab[2]),
        )

        diagnostics.append(
            DominantColorDiagnostic(
                rgb=diagnostic_rgb,
                lab=diagnostic_lab,
                population=candidate.population,
                population_score=candidate.population_score,
                coarse_support=candidate.coarse_support,
                coarse_support_mean=candidate.coarse_support_mean,
                coarse_support_ratio=candidate.coarse_support_ratio,
                coarse_scale_persistence=candidate.coarse_scale_persistence,
                structural_support=candidate.structural_support,
                structural_penalty=candidate.structural_penalty,
                global_salience=candidate.global_salience,
                local_contrast=candidate.local_contrast,
                spatial_coherence=candidate.spatial_coherence,
                lightness_contrast=candidate.lightness_contrast,
                chroma=candidate.chroma,
                chromatic_prominence=candidate.chromatic_prominence,
                neutrality=candidate.neutrality,
                neutral_penalty=candidate.neutral_penalty,
                focal_saliency_share=candidate.focal_saliency_share,
                mean_saliency=candidate.mean_saliency,
                normalized_mean_saliency=candidate.normalized_mean_saliency,
                focal_importance=candidate.focal_importance,
                base_dominance=candidate.base_dominance,
                dominance=candidate.dominance,
                selected_rank=candidate.selected_rank,
                selection_score=candidate.selection_score,
                nearest_selected_distance=candidate.nearest_selected_distance,
                diversity_multiplier=candidate.diversity_multiplier,
            )
        )

    return DominanceAnalysis(
        colors=tuple(colors),
        focal_center=focal_center,
        focal_radius=focal_radius,
        neutral_pixel_fraction=neutral_pixel_fraction,
        neutral_cluster_fraction=neutral_cluster_fraction,
        population_weighted_mean_chroma=population_weighted_mean_chroma,
        high_chroma_pixel_fraction=high_chroma_pixel_fraction,
        accent_chroma_separation=accent_chroma_separation,
        color_pop_strength=color_pop_strength,
        coarse_dimensions=coarse_dimensions,
        saliency_map=saliency_map,
        diagnostics=tuple(diagnostics),
    )


def format_dominance_diagnostics(
    analysis: DominanceAnalysis,
) -> str:
    """
    Format compact candidate diagnostics as tab-separated text.

    The report intentionally omits superseded shadow-selection instrumentation.
    It focuses on the current image-level classifier, active scoring signals, and
    diagnostic multiscale nearest-neighbor structural support.
    """

    coarse_headers = [
        f"coarse_{dimension}"
        for dimension in analysis.coarse_dimensions
    ]

    header_columns = [
        "selected",
        "hex",
        "population",
        "population_score",
        *coarse_headers,
        "coarse_mean",
        "coarse_ratio",
        "scale_persistence",
        "structural_support",
        "structural_penalty",
        "global_salience",
        "local_contrast",
        "spatial_coherence",
        "lightness",
        "lightness_contrast",
        "chroma",
        "chromatic_prominence",
        "neutrality",
        "neutral_penalty",
        "focal_saliency_share",
        "mean_saliency",
        "normalized_mean_saliency",
        "focal_importance",
        "base_dominance",
        "dominance",
        "selection_score",
        "nearest_selected_de00",
        "diversity_multiplier",
    ]

    lines = [
        (
            f"focal_center=({analysis.focal_center[0]:.6f},"
            f" {analysis.focal_center[1]:.6f})\t"
            f"focal_radius={analysis.focal_radius:.6f}"
        ),
        (
            f"neutral_pixel_fraction={analysis.neutral_pixel_fraction:.6f}\t"
            f"neutral_cluster_fraction={analysis.neutral_cluster_fraction:.6f}\t"
            f"population_weighted_mean_chroma="
            f"{analysis.population_weighted_mean_chroma:.6f}\t"
            f"high_chroma_pixel_fraction="
            f"{analysis.high_chroma_pixel_fraction:.6f}\t"
            f"accent_chroma_separation="
            f"{analysis.accent_chroma_separation:.6f}\t"
            f"color_pop_strength={analysis.color_pop_strength:.6f}"
        ),
        "\t".join(
            header_columns
        ),
    ]

    for diagnostic in analysis.diagnostics:
        selected = (
            str(diagnostic.selected_rank)
            if diagnostic.selected_rank is not None
            else "-"
        )

        selection_score = (
            f"{diagnostic.selection_score:.6f}"
            if diagnostic.selection_score is not None
            else "-"
        )

        nearest_distance = (
            f"{diagnostic.nearest_selected_distance:.6f}"
            if diagnostic.nearest_selected_distance is not None
            else "-"
        )

        diversity_multiplier = (
            f"{diagnostic.diversity_multiplier:.6f}"
            if diagnostic.diversity_multiplier is not None
            else "-"
        )

        row = [
            selected,
            diagnostic.hex,
            f"{diagnostic.population:.6f}",
            f"{diagnostic.population_score:.6f}",
            *[
                f"{value:.6f}"
                for value in diagnostic.coarse_support
            ],
            f"{diagnostic.coarse_support_mean:.6f}",
            f"{diagnostic.coarse_support_ratio:.6f}",
            f"{diagnostic.coarse_scale_persistence:.6f}",
            f"{diagnostic.structural_support:.6f}",
            f"{diagnostic.structural_penalty:.6f}",
            f"{diagnostic.global_salience:.6f}",
            f"{diagnostic.local_contrast:.6f}",
            f"{diagnostic.spatial_coherence:.6f}",
            f"{diagnostic.lab[0]:.6f}",
            f"{diagnostic.lightness_contrast:.6f}",
            f"{diagnostic.chroma:.6f}",
            f"{diagnostic.chromatic_prominence:.6f}",
            f"{diagnostic.neutrality:.6f}",
            f"{diagnostic.neutral_penalty:.6f}",
            f"{diagnostic.focal_saliency_share:.6f}",
            f"{diagnostic.mean_saliency:.6f}",
            f"{diagnostic.normalized_mean_saliency:.6f}",
            f"{diagnostic.focal_importance:.6f}",
            f"{diagnostic.base_dominance:.6f}",
            f"{diagnostic.dominance:.6f}",
            selection_score,
            nearest_distance,
            diversity_multiplier,
        ]

        lines.append(
            "\t".join(
                row
            )
        )

    return "\n".join(
        lines
    )


def dominant_colors(
    image: Image.Image | str | Path,
    count: int = 8,
    *,
    provisional_clusters: int | None = None,
    merge_threshold: float = 5.0,
    focal_weight: float = 0.25,
    center_bias: float = 0.10,
    focal_saliency: float = 0.80,
    diversity_distance: float = 15.0,
    diversity_floor: float = 0.35,
    max_dimension: int = 256,
    coarse_dimensions: tuple[int, ...] = (32, 64, 96),
    alpha_threshold: int = 16,
    grid_size: int = 4,
    minimum_cell_coverage: float = 0.02,
    kmeans_iterations: int = 100,
    seed: int = 42,
    saliency_backend: SaliencyBackend = "opencv_fine_grained",
) -> tuple[DominantColor, ...]:
    """
    Return perceptually dominant colors without the additional analysis data.

    This is the convenience API intended for normal library consumers.
    """

    return analyze_dominant_colors(
        image,
        count=count,
        provisional_clusters=provisional_clusters,
        merge_threshold=merge_threshold,
        focal_weight=focal_weight,
        center_bias=center_bias,
        focal_saliency=focal_saliency,
        diversity_distance=diversity_distance,
        diversity_floor=diversity_floor,
        max_dimension=max_dimension,
        coarse_dimensions=coarse_dimensions,
        alpha_threshold=alpha_threshold,
        grid_size=grid_size,
        minimum_cell_coverage=minimum_cell_coverage,
        kmeans_iterations=kmeans_iterations,
        seed=seed,
        saliency_backend=saliency_backend,
    ).colors

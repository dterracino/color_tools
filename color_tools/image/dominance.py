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
      -> spatial and saliency analysis
      -> perceptual dominance scoring
      -> CIEDE2000 diversity selection
      -> requested number of dominant colors

The provisional k-means stage is purely a computational reduction step.
Perceptual similarity and final palette selection use CIEDE2000.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray
from PIL import Image
from sklearn.cluster import KMeans

from color_tools.conversions import lab_to_rgb, rgb_to_lab
from color_tools.distance import delta_e_2000_array


RGB: TypeAlias = tuple[int, int, int]
Lab: TypeAlias = tuple[float, float, float]

FloatArray: TypeAlias = NDArray[np.float64]
IntArray: TypeAlias = NDArray[np.int32]
BoolArray: TypeAlias = NDArray[np.bool_]
UInt8Array: TypeAlias = NDArray[np.uint8]


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
            Relative amount of visual attention associated with the cluster.
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
class DominanceAnalysis:
    """
    Complete perceptual-dominance analysis.

    Attributes:
        colors:
            Selected dominant colors in selection order.

        focal_center:
            Saliency-weighted focal point as normalized (x, y) coordinates.

        focal_radius:
            Normalized radius around focal_center containing the configured
            fraction of accumulated saliency.

        saliency_map:
            Two-dimensional normalized visual-attention map in the range
            0..1.
    """

    colors: tuple[DominantColor, ...]

    focal_center: tuple[float, float]
    focal_radius: float

    saliency_map: FloatArray


# ============================================================================
# Internal result types
# ============================================================================


@dataclass
class _DominantColorCandidate:
    """Internal mutable representation of a candidate perceptual color."""

    lab: FloatArray

    population: float
    population_score: float

    global_salience: float
    local_contrast: float
    spatial_distribution: float
    spatial_coherence: float
    lightness_contrast: float
    focal_importance: float

    dominance: float = 0.0


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
        Image.Resampling.LANCZOS,
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

    merged_centroids = np.asarray(
        centroids,
        dtype=np.float64,
    ).copy()

    merged_populations = np.asarray(
        populations,
        dtype=np.float64,
    ).copy()

    groups: list[list[int]] = [
        [index]
        for index in range(len(merged_centroids))
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


def _calculate_saliency_map(
    lab_image: FloatArray,
    valid_mask: BoolArray,
    local_contrast: FloatArray,
    *,
    center_bias: float,
) -> FloatArray:
    """
    Estimate visual attention using image-derived characteristics.

    Saliency components:
        45% local perceptual contrast
        35% global perceptual uniqueness
        20% relative lightness contrast

    An optional center prior is blended afterward.
    """

    valid_lab = lab_image[valid_mask]

    global_mean_lab = np.asarray(
        valid_lab.mean(axis=0),
        dtype=np.float64,
    )

    # ------------------------------------------------------------------
    # Global perceptual uniqueness
    # ------------------------------------------------------------------

    uniqueness = np.zeros(
        valid_mask.shape,
        dtype=np.float64,
    )

    uniqueness[valid_mask] = np.asarray(
        delta_e_2000_array(
            valid_lab,
            global_mean_lab,
        ),
        dtype=np.float64,
    )

    uniqueness = _normalize_map(
        uniqueness,
        valid_mask,
    )

    # ------------------------------------------------------------------
    # Lightness contrast
    # ------------------------------------------------------------------

    mean_lightness = float(
        valid_lab[:, 0].mean()
    )

    lightness = np.zeros(
        valid_mask.shape,
        dtype=np.float64,
    )

    lightness[valid_mask] = np.abs(
        lab_image[..., 0][valid_mask]
        - mean_lightness
    )

    lightness = _normalize_map(
        lightness,
        valid_mask,
    )

    # ------------------------------------------------------------------
    # Base saliency
    # ------------------------------------------------------------------

    saliency = (
        local_contrast * 0.45
        + uniqueness * 0.35
        + lightness * 0.20
    )

    # ------------------------------------------------------------------
    # Optional compositional center prior
    # ------------------------------------------------------------------

    if center_bias > 0.0:
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

        saliency = (
            saliency * (1.0 - center_bias)
            + center * center_bias
        )

    saliency[~valid_mask] = 0.0

    return _normalize_map(
        np.asarray(
            saliency,
            dtype=np.float64,
        ),
        valid_mask,
        percentile=100.0,
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
    alpha_threshold: int = 16,
    grid_size: int = 4,
    minimum_cell_coverage: float = 0.02,
    kmeans_iterations: int = 100,
    seed: int = 42,
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
            Maximum image dimension used during analysis.

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
            lab_image,
            valid_mask,
            local_contrast_map,
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

        if total_saliency > 0.0:
            focal_importance = float(
                saliency_map[
                    mask
                ].sum()
                / total_saliency
            )
        else:
            focal_importance = population

        candidates.append(
            _DominantColorCandidate(
                lab=np.asarray(
                    centroids[index],
                    dtype=np.float64,
                ),
                population=population,
                population_score=population_score,
                global_salience=float(
                    global_salience[index]
                ),
                local_contrast=local_contrast,
                spatial_distribution=spatial_distribution,
                spatial_coherence=spatial_coherence,
                lightness_contrast=lightness_contrast,
                focal_importance=focal_importance,
            )
        )

    # ------------------------------------------------------------------
    # Normalize focal importance against the strongest cluster
    # ------------------------------------------------------------------

    max_focal = max(
        candidate.focal_importance
        for candidate in candidates
    )

    if max_focal > 0.0:
        for candidate in candidates:
            candidate.focal_importance /= max_focal

    # ------------------------------------------------------------------
    # Dominance
    # ------------------------------------------------------------------
    #
    # Base score:
    #
    #   35% coverage
    #   20% global perceptual salience
    #   15% local perceptual contrast
    #   10% spatial distribution
    #   15% spatial coherence
    #    5% relative lightness
    #
    # Visual attention is deliberately applied as a separate blend rather
    # than being part of intrinsic perceptual dominance.
    # ------------------------------------------------------------------

    for candidate in candidates:
        base_dominance = (
            candidate.population_score * 0.35
            + candidate.global_salience * 0.20
            + candidate.local_contrast * 0.15
            + candidate.spatial_distribution * 0.10
            + candidate.spatial_coherence * 0.15
            + candidate.lightness_contrast * 0.05
        )

        candidate.dominance = (
            base_dominance
            * (1.0 - focal_weight)
            + candidate.focal_importance
            * focal_weight
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
        if not selected:
            best = max(
                remaining,
                key=lambda candidate: candidate.dominance,
            )

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

            if best is None:
                break

        selected.append(
            best
        )

        remaining.remove(
            best
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

        rgb_result = lab_to_rgb(
            lab
        )

        rgb: RGB = (
            int(
                np.clip(
                    round(rgb_result[0]),
                    0,
                    255,
                )
            ),
            int(
                np.clip(
                    round(rgb_result[1]),
                    0,
                    255,
                )
            ),
            int(
                np.clip(
                    round(rgb_result[2]),
                    0,
                    255,
                )
            ),
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

    return DominanceAnalysis(
        colors=tuple(colors),
        focal_center=focal_center,
        focal_radius=focal_radius,
        saliency_map=saliency_map,
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
    alpha_threshold: int = 16,
    grid_size: int = 4,
    minimum_cell_coverage: float = 0.02,
    kmeans_iterations: int = 100,
    seed: int = 42,
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
        alpha_threshold=alpha_threshold,
        grid_size=grid_size,
        minimum_cell_coverage=minimum_cell_coverage,
        kmeans_iterations=kmeans_iterations,
        seed=seed,
    ).colors
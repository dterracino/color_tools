"""
dominant.py
-----------
Perceptual dominant color extraction with focal-point awareness.

Enhancements:
    1. White-balance normalization (Gray-World)
    2. Palette clustering stability improvements (Balanced)
"""

import os
from typing import Tuple, List

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
from skimage import color, filters
import cv2


# ------------------------------------------------------------
# Haar Cascade Loader (Pylance-safe)
# ------------------------------------------------------------

def get_haar_cascade(name: str) -> str:
    cv2_dir = os.path.dirname(cv2.__file__)
    data_dir = os.path.join(cv2_dir, "data")
    path = os.path.join(data_dir, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Haar cascade not found: {path}")
    return path


# ------------------------------------------------------------
# Enhancement #1: White-Balance Normalization (Gray-World)
# ------------------------------------------------------------

def white_balance_grayworld(arr: np.ndarray) -> np.ndarray:
    arr_float = arr.astype(np.float32)
    means = arr_float.mean(axis=(0, 1))
    mean_gray = float(means.mean())
    scale = mean_gray / (means + 1e-6)
    balanced = arr_float * scale
    balanced = np.clip(balanced, 0, 255)
    return balanced.astype(np.uint8)


# ------------------------------------------------------------
# Enhancement #2: Stability Helpers
# ------------------------------------------------------------

def lab_smooth(lab: np.ndarray) -> np.ndarray:
    """Gaussian smoothing in Lab space."""
    smoothed = np.zeros_like(lab)
    for i in range(3):
        smoothed[:, :, i] = cv2.GaussianBlur(lab[:, :, i], (5, 5), 1.0)
    return smoothed


def suppress_outliers(lab: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Down-weight extreme luminance/chroma outliers."""
    L = lab[:, :, 0]
    a = lab[:, :, 1]
    b = lab[:, :, 2]

    chroma = np.sqrt(a * a + b * b)
    lum = L

    # Rare extremes
    low_lum = lum < np.percentile(lum, 2)
    high_lum = lum > np.percentile(lum, 98)
    low_chroma = chroma < np.percentile(chroma, 2)

    mask = low_lum | high_lum | low_chroma
    weights[mask] *= 0.3

    return weights


def delta_e(c1: np.ndarray, c2: np.ndarray) -> float:
    """ΔE distance between two Lab colors."""
    return float(np.linalg.norm(c1 - c2))


def refine_clusters(centers_lab: np.ndarray) -> np.ndarray:
    """Balanced cluster refinement: merge near-duplicates, split unstable clusters."""
    refined = centers_lab.copy()

    # Merge clusters that are too close
    merged = []
    skip = set()

    for i in range(len(refined)):
        if i in skip:
            continue
        base = refined[i]
        group = [base]

        for j in range(i + 1, len(refined)):
            if delta_e(base, refined[j]) < 10.0:
                group.append(refined[j])
                skip.add(j)

        merged.append(np.mean(group, axis=0))

    refined = np.array(merged)

    # Split clusters with high variance (rare but important)
    final = []
    for c in refined:
        if np.std(c) > 20.0:
            # Split into two slight variations
            final.append(c + np.array([5, 0, 0]))
            final.append(c - np.array([5, 0, 0]))
        else:
            final.append(c)

    return np.array(final)


# ------------------------------------------------------------
# Core dominant color extractor
# ------------------------------------------------------------

def extract_dominant_colors(
    image_path: str,
    n_colors: int = 6,
    face_boost: float = 4.0,
    saliency_boost: float = 3.0,
    edge_boost: float = 2.0,
    center_bias_boost: float = 2.0,
) -> np.ndarray:

    img = Image.open(image_path).convert("RGB")
    arr = np.array(img)

    # Enhancement #1
    arr = white_balance_grayworld(arr)

    h, w = arr.shape[:2]

    # Convert to Lab
    lab = color.rgb2lab(arr)

    # Enhancement #2: Lab smoothing
    lab = lab_smooth(lab)

    lab_pixels = lab.reshape(-1, 3)

    # Saliency
    saliency_obj = cv2.saliency.StaticSaliencySpectralResidual.create()
    success, sal_map = saliency_obj.computeSaliency(arr)
    if not success:
        sal_map = np.zeros((h, w), dtype=np.float32)
    sal_map = cv2.GaussianBlur(sal_map, (9, 9), 0)
    sal_map = sal_map / sal_map.max() if sal_map.max() > 0 else np.zeros_like(sal_map)

    # Edges
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = filters.sobel(gray)
    edges = edges / edges.max() if edges.max() > 0 else np.zeros_like(edges)

    # Center bias
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2.0, h / 2.0
    dist = np.sqrt((xx - cx)**2 + (yy - cy)**2)
    center_bias = 1.0 - (dist / dist.max()) if dist.max() > 0 else np.ones((h, w))

    # Face detection
    face_map = np.zeros((h, w), dtype=np.float32)
    try:
        cascade_path = get_haar_cascade("haarcascade_frontalface_default.xml")
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        for (x, y, fw, fh) in faces:
            face_map[y:y+fh, x:x+fw] = 1.0
        if face_map.max() > 0:
            face_map = cv2.GaussianBlur(face_map, (31, 31), 0)
            face_map = face_map / face_map.max()
    except Exception:
        face_map = np.zeros_like(face_map)

    # Combine weights
    weights = (
        1.0
        + saliency_boost * sal_map
        + edge_boost * edges
        + center_bias_boost * center_bias
        + face_boost * face_map
    )

    # Enhancement #2: Outlier suppression
    weights = suppress_outliers(lab, weights)

    weights_flat = weights.reshape(-1)
    weights_flat /= float(weights_flat.mean())

    repeat_counts = np.clip((weights_flat * 10.0).astype(int), 1, None)
    weighted_lab = np.repeat(lab_pixels, repeat_counts, axis=0)

    # Enhancement #2: Stable k-means
    kmeans = KMeans(
        n_clusters=n_colors,
        init="k-means++",
        n_init=10,
        max_iter=300,
    )
    kmeans.fit(weighted_lab)
    centers_lab = kmeans.cluster_centers_

    # Enhancement #2: Cluster refinement
    centers_lab = refine_clusters(centers_lab)

    # Convert back to RGB
    centers_rgb = color.lab2rgb(centers_lab.reshape(1, -1, 3))[0] * 255.0
    return centers_rgb.astype(np.uint8)


# ------------------------------------------------------------
# Convenience wrapper
# ------------------------------------------------------------

def dominant_colors(image_path: str, n_colors: int = 6) -> List[Tuple[int, int, int]]:
    arr = extract_dominant_colors(image_path, n_colors=n_colors)
    result: List[Tuple[int, int, int]] = [
        (int(c[0]), int(c[1]), int(c[2])) for c in arr
    ]
    return result

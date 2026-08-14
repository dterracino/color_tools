"""
dominant.py
-----------
Perceptual dominant color extraction with focal-point awareness.

Features:
    - Lab-space clustering (perceptual)
    - Saliency weighting (spectral residual)
    - Edge weighting (Sobel)
    - Center-bias weighting (focal point heuristic)
    - Face detection weighting (Haar cascade)
    - Clean, Pylance-safe Haar cascade loader
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
    """
    Returns a fully-qualified path to a Haar cascade file
    without touching cv2.data (Pylance-safe).
    """
    cv2_dir = os.path.dirname(cv2.__file__)
    data_dir = os.path.join(cv2_dir, "data")
    path = os.path.join(data_dir, name)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Haar cascade not found: {path}")

    return path


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
    """
    Extract perceptual dominant colors with focal-point awareness.

    Returns:
        np.ndarray of shape (n_colors, 3) in RGB 0–255
    """

    # ------------------------------------------------------------
    # Load image
    # ------------------------------------------------------------
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img)
    h, w = arr.shape[:2]

    # ------------------------------------------------------------
    # Convert to Lab (perceptual)
    # ------------------------------------------------------------
    lab = color.rgb2lab(arr)
    lab_pixels = lab.reshape(-1, 3)

    # ------------------------------------------------------------
    # Saliency map (spectral residual)
    # ------------------------------------------------------------
    # Pylance-friendly API: StaticSaliencySpectralResidual.create()
    saliency_obj = cv2.saliency.StaticSaliencySpectralResidual.create()
    success, sal_map = saliency_obj.computeSaliency(arr)
    if not success:
        sal_map = np.zeros((h, w), dtype=np.float32)

    sal_map = cv2.GaussianBlur(sal_map, (9, 9), 0)
    if sal_map.max() > 0:
        sal_map = sal_map / sal_map.max()
    else:
        sal_map = np.zeros_like(sal_map)

    # ------------------------------------------------------------
    # Edge map (Sobel)
    # ------------------------------------------------------------
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = filters.sobel(gray)
    if edges.max() > 0:
        edges = edges / edges.max()
    else:
        edges = np.zeros_like(edges)

    # ------------------------------------------------------------
    # Center bias (focal point heuristic)
    # ------------------------------------------------------------
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2.0, h / 2.0
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    if dist.max() > 0:
        center_bias = 1.0 - (dist / dist.max())
    else:
        center_bias = np.ones((h, w), dtype=np.float32)

    # ------------------------------------------------------------
    # Face detection
    # ------------------------------------------------------------
    face_map = np.zeros((h, w), dtype=np.float32)

    try:
        cascade_path = get_haar_cascade("haarcascade_frontalface_default.xml")
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)

        for (x, y, fw, fh) in faces:
            face_map[y:y + fh, x:x + fw] = 1.0

        if face_map.max() > 0:
            face_map = cv2.GaussianBlur(face_map, (31, 31), 0)
            face_map = face_map / face_map.max()

    except Exception:
        # No face cascade available or detection failed
        face_map = np.zeros_like(face_map)

    # ------------------------------------------------------------
    # Combine weights
    # ------------------------------------------------------------
    weights = (
        1.0
        + saliency_boost * sal_map
        + edge_boost * edges
        + center_bias_boost * center_bias
        + face_boost * face_map
    )

    weights_flat = weights.reshape(-1)
    mean_weight = float(weights_flat.mean()) if weights_flat.size > 0 else 1.0
    weights_flat = weights_flat / mean_weight

    # ------------------------------------------------------------
    # Weighted pixel sampling
    # ------------------------------------------------------------
    repeat_counts = np.clip((weights_flat * 10.0).astype(int), 1, None)
    weighted_lab = np.repeat(lab_pixels, repeat_counts, axis=0)

    # ------------------------------------------------------------
    # KMeans clustering
    # ------------------------------------------------------------
    kmeans = KMeans(n_clusters=n_colors, n_init="auto")
    kmeans.fit(weighted_lab)
    centers_lab = kmeans.cluster_centers_

    # ------------------------------------------------------------
    # Convert back to RGB
    # ------------------------------------------------------------
    centers_rgb = color.lab2rgb(centers_lab.reshape(1, -1, 3))[0] * 255.0
    return centers_rgb.astype(np.uint8)


# ------------------------------------------------------------
# Convenience wrapper
# ------------------------------------------------------------

def dominant_colors(image_path: str, n_colors: int = 6) -> List[Tuple[int, int, int]]:
    """
    Returns a Python list of RGB tuples.
    """
    arr = extract_dominant_colors(image_path, n_colors=n_colors)

    result: List[Tuple[int, int, int]] = [
        (int(c[0]), int(c[1]), int(c[2]))
        for c in arr
    ]
    return result

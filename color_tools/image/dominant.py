"""
dominant.py
-----------
Modular perceptual dominant color extraction with focal-point awareness.

Enhancements included:
    1. White-balance normalization (Gray-World)
    2. Palette clustering stability improvements (Balanced)
    3. Contrast-aware palette sorting
    4. Skin-tone preservation rules
    5. Depth-estimation weighting
    6. Semantic segmentation weighting
"""

import os
from typing import Tuple, List

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
from skimage import color, filters
import cv2


# ------------------------------------------------------------
# Haar Cascade Loader
# ------------------------------------------------------------

def get_haar_cascade(name: str) -> str:
    cv2_dir = os.path.dirname(cv2.__file__)
    data_dir = os.path.join(cv2_dir, "data")
    path = os.path.join(data_dir, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Haar cascade not found: {path}")
    return path


# ------------------------------------------------------------
# Enhancement #1: White Balance
# ------------------------------------------------------------

def white_balance_grayworld(arr: np.ndarray) -> np.ndarray:
    arr_f = arr.astype(np.float32)
    means = arr_f.mean(axis=(0, 1))
    mean_gray = float(means.mean())
    scale = mean_gray / (means + 1e-6)
    balanced = arr_f * scale
    return np.clip(balanced, 0, 255).astype(np.uint8)


# ------------------------------------------------------------
# Enhancement #4: Skin-Tone Preservation
# ------------------------------------------------------------

def skin_mask_lab(lab: np.ndarray) -> np.ndarray:
    L = lab[:, :, 0]
    a = lab[:, :, 1]
    b = lab[:, :, 2]

    mask = (
        (L > 20) & (L < 85) &
        (a > 5) & (a < 30) &
        (b > 5) & (b < 40)
    )

    return mask.astype(np.float32)


def preserve_skin_tones(
    centers_lab: np.ndarray,
    skin_mask: np.ndarray,
    lab_pixels: np.ndarray
) -> np.ndarray:

    if skin_mask.sum() == 0:
        return centers_lab

    skin_pixels = lab_pixels[skin_mask.reshape(-1) > 0]
    if len(skin_pixels) == 0:
        return centers_lab

    skin_mean = np.mean(skin_pixels, axis=0)

    refined = []
    for c in centers_lab:
        if delta_e(c, skin_mean) < 15.0:
            refined.append((c * 0.7) + (skin_mean * 0.3))
        else:
            refined.append(c)

    return np.array(refined)


# ------------------------------------------------------------
# Enhancement #2: Stability Helpers
# ------------------------------------------------------------

def lab_smooth(lab: np.ndarray) -> np.ndarray:
    smoothed = np.zeros_like(lab)
    for i in range(3):
        smoothed[:, :, i] = cv2.GaussianBlur(lab[:, :, i], (5, 5), 1.0)
    return smoothed


def suppress_outliers(lab: np.ndarray, weights: np.ndarray) -> np.ndarray:
    L = lab[:, :, 0]
    a = lab[:, :, 1]
    b = lab[:, :, 2]

    chroma = np.sqrt(a * a + b * b)
    lum = L

    low_lum = lum < np.percentile(lum, 2)
    high_lum = lum > np.percentile(lum, 98)
    low_chroma = chroma < np.percentile(chroma, 2)

    mask = low_lum | high_lum | low_chroma
    weights[mask] *= 0.3

    return weights


def delta_e(c1: np.ndarray, c2: np.ndarray) -> float:
    return float(np.linalg.norm(c1 - c2))


def refine_clusters(centers_lab: np.ndarray) -> np.ndarray:
    refined = centers_lab.copy()
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

    final = []
    for c in refined:
        if np.std(c) > 20.0:
            final.append(c + np.array([5, 0, 0]))
            final.append(c - np.array([5, 0, 0]))
        else:
            final.append(c)

    return np.array(final)


# ------------------------------------------------------------
# Enhancement #3: Contrast-Aware Palette Sorting
# ------------------------------------------------------------

def sort_palette_by_contrast(centers_lab: np.ndarray) -> np.ndarray:
    L = centers_lab[:, 0]
    a = centers_lab[:, 1]
    b = centers_lab[:, 2]

    chroma = np.sqrt(a * a + b * b)
    hue = np.arctan2(b, a)

    order = np.lexsort((hue, -chroma, -L))
    return centers_lab[order]


# ------------------------------------------------------------
# Enhancement #5: Depth Estimation Weighting
# ------------------------------------------------------------

def compute_depth_map(arr: np.ndarray) -> np.ndarray:
    h, w = arr.shape[:2]

    model_path = os.path.join(os.path.dirname(cv2.__file__), "model-small.onnx")
    if not os.path.exists(model_path):
        return np.ones((h, w), dtype=np.float32)

    net = cv2.dnn.readNet(model_path)

    blob = cv2.dnn.blobFromImage(arr, 1/255.0, (256, 256), swapRB=True, crop=False)
    net.setInput(blob)
    depth = net.forward()[0, 0]

    depth = cv2.resize(depth, (w, h))
    depth = depth.astype(np.float32)

    depth -= depth.min()
    if depth.max() > 0:
        depth /= depth.max()

    return depth


def depth_weighting(depth_map: np.ndarray) -> np.ndarray:
    return 1.0 - depth_map


# ------------------------------------------------------------
# Enhancement #6: Semantic Segmentation Weighting
# ------------------------------------------------------------

def compute_segmentation_map(arr: np.ndarray) -> np.ndarray:
    """
    Lightweight semantic segmentation using DeepLabv3-small via OpenCV DNN.
    """

    h, w = arr.shape[:2]

    model_path = os.path.join(os.path.dirname(cv2.__file__), "deeplab-small.onnx")
    if not os.path.exists(model_path):
        return np.ones((h, w), dtype=np.float32)

    net = cv2.dnn.readNet(model_path)

    blob = cv2.dnn.blobFromImage(arr, 1/255.0, (256, 256), swapRB=True, crop=False)
    net.setInput(blob)
    seg = net.forward()[0]

    seg = np.argmax(seg, axis=0)
    seg = cv2.resize(seg.astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)

    return seg


def segmentation_weighting(seg_map: np.ndarray) -> np.ndarray:
    """
    Boost meaningful classes.
    Down-weight background.
    """

    weights = np.ones_like(seg_map, dtype=np.float32)

    # Example class boosts (DeepLabv3 standard labels)
    boosts = {
        15: 2.0,  # person
        2: 1.5,   # sky
        17: 1.5,  # clothing
        18: 1.5,  # hair
        4: 1.3,   # vegetation
    }

    for cls, factor in boosts.items():
        weights[seg_map == cls] *= factor

    weights[seg_map == 0] *= 0.7  # background

    return weights


# ------------------------------------------------------------
# Pipeline Stages
# ------------------------------------------------------------

def load_image(path: str) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"))


def compute_saliency(arr: np.ndarray) -> np.ndarray:
    h, w = arr.shape[:2]
    saliency_obj = cv2.saliency.StaticSaliencySpectralResidual.create()
    success, sal_map = saliency_obj.computeSaliency(arr)
    if not success:
        return np.zeros((h, w), dtype=np.float32)
    sal_map = cv2.GaussianBlur(sal_map, (9, 9), 0)
    return sal_map / sal_map.max() if sal_map.max() > 0 else np.zeros_like(sal_map)


def compute_edges(arr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = filters.sobel(gray)
    return edges / edges.max() if edges.max() > 0 else np.zeros_like(edges)


def compute_center_bias(h: int, w: int) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2.0, h / 2.0
    dist = np.sqrt((xx - cx)**2 + (yy - cy)**2)
    return 1.0 - (dist / dist.max()) if dist.max() > 0 else np.ones((h, w))


def compute_face_map(arr: np.ndarray) -> np.ndarray:
    h, w = arr.shape[:2]
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
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
        pass

    return face_map


def compute_weights(
    sal: np.ndarray,
    edges: np.ndarray,
    center: np.ndarray,
    face: np.ndarray,
    depth: np.ndarray,
    seg: np.ndarray,
    lab: np.ndarray,
    face_boost: float,
    saliency_boost: float,
    edge_boost: float,
    center_bias_boost: float,
) -> np.ndarray:

    seg_w = segmentation_weighting(seg)

    weights = (
        1.0
        + saliency_boost * sal
        + edge_boost * edges
        + center_bias_boost * center
        + face_boost * face
        + 2.0 * depth_weighting(depth)
        + seg_w
    )

    weights = suppress_outliers(lab, weights)

    skin_mask = skin_mask_lab(lab)
    weights[skin_mask] *= 1.5

    weights_flat = weights.reshape(-1)
    weights_flat /= float(weights_flat.mean())
    return weights_flat


def cluster_colors(
    lab_pixels: np.ndarray,
    weights_flat: np.ndarray,
    n_colors: int,
    skin_mask: np.ndarray
) -> np.ndarray:

    repeat_counts = np.clip((weights_flat * 10.0).astype(int), 1, None)
    weighted_lab = np.repeat(lab_pixels, repeat_counts, axis=0)

    kmeans = KMeans(
        n_clusters=n_colors,
        init="k-means++",
        n_init=10,
        max_iter=300,
    )
    kmeans.fit(weighted_lab)
    centers_lab = kmeans.cluster_centers_

    centers_lab = refine_clusters(centers_lab)
    centers_lab = preserve_skin_tones(centers_lab, skin_mask, lab_pixels)
    centers_lab = sort_palette_by_contrast(centers_lab)

    return centers_lab


def lab_to_rgb(centers_lab: np.ndarray) -> np.ndarray:
    rgb = color.lab2rgb(centers_lab.reshape(1, -1, 3))[0] * 255.0
    return rgb.astype(np.uint8)


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

def extract_dominant_colors(
    image_path: str,
    n_colors: int = 6,
    face_boost: float = 4.0,
    saliency_boost: float = 3.0,
    edge_boost: float = 2.0,
    center_bias_boost: float = 2.0,
) -> np.ndarray:

    arr = load_image(image_path)
    arr = white_balance_grayworld(arr)

    h, w = arr.shape[:2]

    sal = compute_saliency(arr)
    edges = compute_edges(arr)
    center = compute_center_bias(h, w)
    face = compute_face_map(arr)
    depth = compute_depth_map(arr)
    seg = compute_segmentation_map(arr)

    lab = color.rgb2lab(arr)
    lab = lab_smooth(lab)
    lab_pixels = lab.reshape(-1, 3)

    skin_mask = skin_mask_lab(lab)

    weights_flat = compute_weights(
        sal, edges, center, face, depth, seg, lab,
        face_boost, saliency_boost, edge_boost, center_bias_boost
    )

    centers_lab = cluster_colors(lab_pixels, weights_flat, n_colors, skin_mask)
    return lab_to_rgb(centers_lab)


def dominant_colors(image_path: str, n_colors: int = 6) -> List[Tuple[int, int, int]]:
    arr = extract_dominant_colors(image_path, n_colors=n_colors)
    result: List[Tuple[int, int, int]] = [(int(c[0]), int(c[1]), int(c[2])) for c in arr]
    return result

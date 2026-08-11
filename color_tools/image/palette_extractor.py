# """
# palette_extractor.py
# Modular palette extraction toolkit with:
# - Multiple extraction algorithms
# - Palette sorting utilities
# - Outlier suppression
# - Image-type detection
# - Noise detection
# - Optional denoising
# - Auto-selection logic
# """

# import os
# import numpy as np
# from PIL import Image
# from sklearn.cluster import KMeans
# from skimage import color, filters, feature, restoration
# import cv2


# # ============================================================
# # INTERNAL UTILITIES
# # ============================================================

# def _cluster_with_sizes(pixels, n_colors):
#     """Return cluster centers AND cluster sizes."""
#     kmeans = KMeans(n_clusters=n_colors, n_init="auto")
#     kmeans.fit(pixels)
#     centers = kmeans.cluster_centers_.astype(int)
#     labels = kmeans.labels_
#     sizes = np.bincount(labels, minlength=n_colors)
#     return centers, sizes


# def _lab_to_rgb(lab_centers):
#     rgb = (color.lab2rgb(lab_centers.reshape(1, -1, 3))[0] * 255)
#     return rgb.astype(int)


# def _get_haar_face_cascade():
#     """Load Haar cascade in a Pylance-safe way."""
#     base = os.path.dirname(cv2.__file__)
#     haar_dir = os.path.join(base, "data")
#     xml_path = os.path.join(haar_dir, "haarcascade_frontalface_default.xml")
#     return cv2.CascadeClassifier(xml_path)


# # ============================================================
# # OPTIONAL DENOISING
# # ============================================================

# def denoise_image(arr, strength=0.15):
#     """
#     Apply gentle denoising using bilateral filtering.
#     Preserves edges while reducing noise.

#     Parameters
#     ----------
#     arr : ndarray
#         RGB image array.

#     strength : float
#         Denoising strength (0.0–1.0). Higher = smoother.

#     Returns
#     -------
#     ndarray
#         Denoised RGB image.
#     """
#     # Convert to float [0,1]
#     img = arr / 255.0

#     # Bilateral filter (edge-preserving)
#     denoised = restoration.denoise_bilateral(
#         img,
#         sigma_color=strength,
#         sigma_spatial=3,
#         channel_axis=-1
#     )

#     return (denoised * 255).astype(np.uint8)


# # ============================================================
# # PALETTE EXTRACTION METHODS
# # ============================================================

# def extract_palette_dominant(image_path, n_colors=6):
#     img = Image.open(image_path).convert("RGB")
#     pixels = np.array(img).reshape(-1, 3)
#     return _cluster_with_sizes(pixels, n_colors)


# def extract_palette_perceptual(image_path, n_colors=6):
#     img = Image.open(image_path).convert("RGB")
#     lab = color.rgb2lab(np.array(img))
#     lab_pixels = lab.reshape(-1, 3)
#     centers_lab, sizes = _cluster_with_sizes(lab_pixels, n_colors)
#     return _lab_to_rgb(centers_lab), sizes


# def extract_palette_saliency(image_path, n_colors=6, boost=5):
#     img = Image.open(image_path).convert("RGB")
#     arr = np.array(img)
#     gray = color.rgb2gray(arr)

#     sal = np.abs(filters.laplace(gray))
#     sal = sal / sal.max()

#     weights = (sal.reshape(-1) * boost).astype(int) + 1
#     pixels = arr.reshape(-1, 3)
#     weighted = np.repeat(pixels, weights, axis=0)

#     return _cluster_with_sizes(weighted, n_colors)


# def extract_palette_edges(image_path, n_colors=6, boost=4):
#     img = Image.open(image_path).convert("RGB")
#     arr = np.array(img)
#     gray = color.rgb2gray(arr)

#     edges = feature.canny(gray, sigma=1.4).astype(float)
#     if edges.max() > 0:
#         edges /= edges.max()

#     weights = (edges.reshape(-1) * boost).astype(int) + 1
#     pixels = arr.reshape(-1, 3)
#     weighted = np.repeat(pixels, weights, axis=0)

#     return _cluster_with_sizes(weighted, n_colors)


# def extract_palette_faces(image_path, n_colors=6, boost=6):
#     img = Image.open(image_path).convert("RGB")
#     arr = np.array(img)
#     h, w, _ = arr.shape

#     face_map = np.zeros((h, w), dtype=float)
#     face_cascade = _get_haar_face_cascade()

#     try:
#         cv_img = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
#         faces = face_cascade.detectMultiScale(cv_img, 1.2, 5)

#         for (x, y, fw, fh) in faces:
#             face_map[y:y+fh, x:x+fw] = 1.0

#         if face_map.max() > 0:
#             face_map /= face_map.max()

#     except Exception:
#         pass

#     weights = (face_map.reshape(-1) * boost).astype(int) + 1
#     pixels = arr.reshape(-1, 3)
#     weighted = np.repeat(pixels, weights, axis=0)

#     return _cluster_with_sizes(weighted, n_colors)


# def extract_palette_tiny(image_path, n_colors=6, tiny_size=32):
#     img = Image.open(image_path).convert("RGB")
#     tiny = img.resize((tiny_size, tiny_size), Image.Resampling.LANCZOS)
#     pixels = np.array(tiny).reshape(-1, 3)
#     return _cluster_with_sizes(pixels, n_colors)


# def extract_palette_hybrid(image_path, n_colors=6):
#     sal, _ = extract_palette_saliency(image_path, n_colors)
#     edg, _ = extract_palette_edges(image_path, n_colors)
#     fac, _ = extract_palette_faces(image_path, n_colors)
#     per, _ = extract_palette_perceptual(image_path, n_colors)

#     combined = np.mean([sal, edg, fac, per], axis=0).astype(int)
#     sizes = np.ones(n_colors)
#     return combined, sizes


# # ============================================================
# # OUTLIER SUPPRESSION
# # ============================================================

# def suppress_outliers(palette, sizes, threshold=0.02):
#     total = np.sum(sizes)
#     keep = sizes / total >= threshold
#     return palette[keep], sizes[keep]


# # ============================================================
# # SORTING METHODS
# # ============================================================

# def sort_by_luminance(palette, reverse=False):
#     idx = np.argsort(np.mean(palette, axis=1))
#     return palette[idx[::-1] if reverse else idx]


# def sort_by_hue(palette, reverse=False):
#     hsv = color.rgb2hsv(palette.reshape(1, -1, 3) / 255)[0]
#     idx = np.argsort(hsv[:, 0])
#     return palette[idx[::-1] if reverse else idx]


# def sort_by_saturation(palette, reverse=False):
#     hsv = color.rgb2hsv(palette.reshape(1, -1, 3) / 255)[0]
#     idx = np.argsort(hsv[:, 1])
#     return palette[idx[::-1] if reverse else idx]


# def sort_by_warmth(palette, reverse=False):
#     warmth = palette[:, 0] - palette[:, 2]
#     idx = np.argsort(warmth)
#     return palette[idx[::-1] if reverse else idx]


# def sort_by_distance(palette, ref_color, reverse=False):
#     ref = np.array(ref_color)
#     dist = np.linalg.norm(palette - ref, axis=1)
#     idx = np.argsort(dist)
#     return palette[idx[::-1] if reverse else idx]


# SORT_METHODS = {
#     "luminance": sort_by_luminance,
#     "hue": sort_by_hue,
#     "saturation": sort_by_saturation,
#     "warmth": sort_by_warmth,
#     "distance": sort_by_distance,
# }


# # ============================================================
# # IMAGE TYPE DETECTION
# # ============================================================

# def detect_faces(arr):
#     face_cascade = _get_haar_face_cascade()
#     try:
#         cv_img = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
#         faces = face_cascade.detectMultiScale(cv_img, 1.2, 5)
#         return len(faces) > 0
#     except Exception:
#         return False


# def edge_density(arr):
#     gray = color.rgb2gray(arr)
#     edges = feature.canny(gray, sigma=1.4)
#     return edges.mean()


# def color_variance(arr):
#     return np.var(arr.reshape(-1, 3)) / (255**2)


# def saturation_level(arr):
#     hsv = color.rgb2hsv(arr / 255.0)
#     return hsv[..., 1].mean()


# def is_small_image(arr, threshold=64*64):
#     return arr.shape[0] * arr.shape[1] <= threshold


# # ============================================================
# # NOISE DETECTION
# # ============================================================

# def detect_noise(arr):
#     gray = color.rgb2gray(arr)

#     lap = filters.laplace(gray)
#     lap_var = np.var(lap)
#     lap_score = min(lap_var / 0.01, 1.0)

#     edges = feature.canny(gray, sigma=1.0)
#     edge_score = min(edges.mean() * 2.0, 1.0)

#     small = arr[::8, ::8]
#     color_var = np.var(small.reshape(-1, 3)) / (255**2)
#     color_score = min(color_var * 8.0, 1.0)

#     return (lap_score + edge_score + color_score) / 3.0


# # ============================================================
# # AUTO-SELECTION LOGIC
# # ============================================================

# def auto_select_method(arr):
#     if is_small_image(arr):
#         return "tiny"

#     if detect_faces(arr):
#         return "faces"

#     noise = detect_noise(arr)
#     if noise > 0.35:
#         return "dominant"

#     ed = edge_density(arr)
#     if ed > 0.12:
#         return "edges"

#     sat = saturation_level(arr)
#     if sat > 0.45:
#         return "perceptual"

#     var = color_variance(arr)
#     if var < 0.015:
#         return "dominant"

#     return "hybrid"


# # ============================================================
# # DISPATCHER
# # ============================================================

# EXTRACTION_METHODS = {
#     "dominant": extract_palette_dominant,
#     "perceptual": extract_palette_perceptual,
#     "saliency": extract_palette_saliency,
#     "edges": extract_palette_edges,
#     "faces": extract_palette_faces,
#     "tiny": extract_palette_tiny,
#     "hybrid": extract_palette_hybrid,
# }


# def extract_palette(image_path, n_colors=6, method="perceptual",
#                     order=None, direction="asc", ref_color=None,
#                     suppress_threshold=None, denoise=False):
#     """
#     Extract a color palette from an image using a selectable algorithm,
#     optionally suppress outlier colors, optionally denoise the image,
#     and sort the resulting palette.

#     (Use the full docstring you approved earlier.)
#     """

#     img = Image.open(image_path).convert("RGB")
#     arr = np.array(img)

#     if denoise:
#         arr = denoise_image(arr)

#         # Save denoised temp image for extraction
#         img = Image.fromarray(arr)
#         img.save(image_path + ".denoised.png")
#         image_path = image_path + ".denoised.png"

#     palette, sizes = EXTRACTION_METHODS[method](image_path, n_colors)

#     if suppress_threshold is not None:
#         palette, sizes = suppress_outliers(palette, sizes, suppress_threshold)

#     if order is not None:
#         reverse = (direction == "desc")
#         if order == "distance":
#             palette = SORT_METHODS[order](palette, ref_color, reverse)
#         else:
#             palette = SORT_METHODS[order](palette, reverse)

#     return palette, sizes


# def extract_palette_auto(image_path, n_colors=6, denoise=False, **kwargs):
#     img = Image.open(image_path).convert("RGB")
#     arr = np.array(img)

#     method = auto_select_method(arr)

#     # Auto-denoise if noise is high
#     noise = detect_noise(arr)
#     if noise > 0.45:
#         denoise = True

#     return extract_palette(image_path, n_colors, method=method,
#                            denoise=denoise, **kwargs)
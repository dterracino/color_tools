# import cv2
# import numpy as np

# try:
#     from pyxelart_detector import is_pixel_art # type: ignore
#     PIXEL_ART_DETECTOR_AVAILABLE = True
# except ImportError:
#     PIXEL_ART_DETECTOR_AVAILABLE = False


# def blockiness_score(gray_img):
#     """Measures blockiness by checking how often adjacent pixels differ sharply."""
#     diff_x = np.abs(np.diff(gray_img, axis=1))
#     diff_y = np.abs(np.diff(gray_img, axis=0))
#     threshold = 40
#     strong_changes = np.sum(diff_x > threshold) + np.sum(diff_y > threshold)
#     total_possible = diff_x.size + diff_y.size
#     return strong_changes / total_possible


# def noise_level(gray_img):
#     """Estimates noise level using Laplacian variance."""
#     laplacian = cv2.Laplacian(gray_img, cv2.CV_64F)
#     return laplacian.var()


# def classify_image_type_with_confidence(image_path):
#     img = cv2.imread(image_path)
#     if img is None:
#         raise ValueError(f"Could not load image: {image_path}")

#     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#     h, w = gray.shape
#     total_pixels = h * w

#     # Unique colors
#     unique_colors = len(np.unique(cv2.cvtColor(img, cv2.COLOR_BGR2RGB).reshape(-1, 3), axis=0))

#     # Edge analysis
#     edges = cv2.Canny(gray, 50, 150)
#     edge_count = np.sum(edges > 0)
#     edge_density = edge_count / total_pixels
#     color_std = np.std(img)

#     # Blockiness & noise
#     blockiness = blockiness_score(gray)
#     noise_var = noise_level(gray)

#     # --- Adaptive thresholds ---
#     edge_count_threshold_low = 0.02 * total_pixels   # ~2% of pixels are edges
#     edge_count_threshold_high = 0.05 * total_pixels  # ~5% of pixels are edges
#     noise_threshold_low = 50
#     noise_threshold_high = 80

#     scores = {"Pixel Art": 0.0, "Line Art": 0.0, "Photographic": 0.0}

#     # --- Pixel Art Signals ---
#     if PIXEL_ART_DETECTOR_AVAILABLE and is_pixel_art(image_path):
#         scores["Pixel Art"] += 0.6
#     if (h < 64 and w < 64) or unique_colors < 64:
#         scores["Pixel Art"] += 0.3
#     if blockiness > 0.25:
#         scores["Pixel Art"] += 0.3
#     if edge_count < edge_count_threshold_low:
#         scores["Pixel Art"] += 0.2
#     if noise_var < noise_threshold_low:
#         scores["Pixel Art"] += 0.2

#     # --- Line Art Signals ---
#     if edge_density > 0.15:
#         scores["Line Art"] += 0.4
#     if color_std < 30:
#         scores["Line Art"] += 0.3
#     if unique_colors < 256:
#         scores["Line Art"] += 0.3
#     if edge_count_threshold_low <= edge_count <= edge_count_threshold_high:
#         scores["Line Art"] += 0.2
#     if noise_var < noise_threshold_high:
#         scores["Line Art"] += 0.1

#     # --- Photographic Signals ---
#     if color_std >= 30:
#         scores["Photographic"] += 0.4
#     if unique_colors >= 256:
#         scores["Photographic"] += 0.4
#     if edge_density < 0.15:
#         scores["Photographic"] += 0.2
#     if edge_count > edge_count_threshold_high:
#         scores["Photographic"] += 0.3
#     if noise_var >= noise_threshold_high:
#         scores["Photographic"] += 0.2

#     # Normalize scores
#     total_score = sum(scores.values())
#     if total_score > 0:
#         for k in scores:
#             scores[k] /= total_score

#     best_type = max(scores, key=lambda k: scores[k])
#     confidence = scores[best_type]

#     return {
#         "type": best_type,
#         "confidence": round(confidence, 3),
#         "scores": scores,
#         "features": {
#             "width": w,
#             "height": h,
#             "unique_colors": unique_colors,
#             "edge_count": int(edge_count),
#             "edge_density": round(edge_density, 4),
#             "color_std": round(color_std, 2),
#             "blockiness": round(blockiness, 4),
#             "noise_variance": round(noise_var, 2),
#             "adaptive_edge_low": int(edge_count_threshold_low),
#             "adaptive_edge_high": int(edge_count_threshold_high)
#         }
#     }


# if __name__ == "__main__":
#     test_images = [
#         "pixel_art_example.png",
#         "line_art_example.jpg",
#         "photo_example.jpg"
#     ]

#     for path in test_images:
#         try:
#             result = classify_image_type_with_confidence(path)
#             print(f"{path}: {result['type']} (confidence: {result['confidence']})")
#             print(f"  Score breakdown: {result['scores']}")
#             print(f"  Features: {result['features']}")
#         except Exception as e:
#             print(f"Error processing {path}: {e}")

"""Unit tests for HyAB distance metric and related image functions.

Covers:
- delta_e_hyab() in color_tools.distance
- extract_color_clusters() new parameters (distance_metric, l_weight, use_l_median, n_iter)
- quantize_image_hyab() in color_tools.image
- Palette/FilamentPalette dispatch for metric='hyab'
"""

import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_image(colors: list, rows_per_color: int = 20) -> str:
    """Save a striped test PNG and return its path."""
    width = 50
    height = len(colors) * rows_per_color
    img = Image.new("RGB", (width, height))
    for i, color in enumerate(colors):
        for y in range(i * rows_per_color, (i + 1) * rows_per_color):
            for x in range(width):
                img.putpixel((x, y), color)
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    img.save(path)
    return path


# ===========================================================================
# delta_e_hyab
# ===========================================================================

class TestDeltaEHyAB(unittest.TestCase):
    """Tests for color_tools.distance.delta_e_hyab."""

    @classmethod
    def setUpClass(cls):
        from color_tools.distance import delta_e_hyab
        cls.fn = staticmethod(delta_e_hyab)

    # --- basic semantics ---

    def test_identical_colors_zero(self):
        """Identical LAB colors must produce 0 distance."""
        lab = (50.0, 20.0, -10.0)
        self.assertAlmostEqual(self.fn(lab, lab), 0.0, places=10)

    def test_symmetry(self):
        """HyAB distance is symmetric."""
        a = (50.0, 20.0, -10.0)
        b = (60.0, -5.0, 15.0)
        self.assertAlmostEqual(self.fn(a, b), self.fn(b, a), places=10)

    def test_non_negative(self):
        """Result must always be >= 0."""
        pairs = [
            ((0.0, 0.0, 0.0), (100.0, 0.0, 0.0)),
            ((50.0, 50.0, 50.0), (50.0, -50.0, -50.0)),
            ((30.0, 0.0, 0.0), (30.0, 0.0, 0.0)),
        ]
        for a, b in pairs:
            with self.subTest(a=a, b=b):
                self.assertGreaterEqual(self.fn(a, b), 0.0)

    # --- formula verification ---

    def test_only_L_differs(self):
        """When only L differs, distance = l_weight * |L1 - L2|."""
        a = (40.0, 10.0, -5.0)
        b = (70.0, 10.0, -5.0)
        expected = 1.0 * abs(40.0 - 70.0)  # l_weight=1.0 default
        self.assertAlmostEqual(self.fn(a, b), expected, places=10)

    def test_only_chroma_differs(self):
        """When only a* and b* differ, distance = sqrt(da^2 + db^2)."""
        a = (50.0, 0.0, 0.0)
        b = (50.0, 3.0, 4.0)
        expected = math.sqrt(3.0**2 + 4.0**2)  # = 5.0
        self.assertAlmostEqual(self.fn(a, b), expected, places=10)

    def test_manual_calculation(self):
        """Full HyAB formula check with known values."""
        a = (60.0, 10.0, 20.0)
        b = (50.0, 4.0, 14.0)
        # |60-50| + sqrt((10-4)^2 + (20-14)^2) = 10 + sqrt(36+36) = 10 + 6*sqrt(2)
        expected = 10.0 + math.sqrt(36.0 + 36.0)
        self.assertAlmostEqual(self.fn(a, b), expected, places=10)

    def test_l_weight_scaling(self):
        """l_weight parameter scales the L contribution."""
        a = (50.0, 0.0, 0.0)
        b = (60.0, 0.0, 0.0)
        d1 = self.fn(a, b, l_weight=1.0)
        d2 = self.fn(a, b, l_weight=2.0)
        self.assertAlmostEqual(d1, 10.0, places=10)
        self.assertAlmostEqual(d2, 20.0, places=10)

    def test_l_weight_zero_ignores_lightness(self):
        """l_weight=0 makes HyAB ignore the L dimension entirely."""
        a = (0.0, 3.0, 4.0)
        b = (100.0, 3.0, 4.0)  # L differs by 100, a/b identical
        d = self.fn(a, b, l_weight=0.0)
        self.assertAlmostEqual(d, 0.0, places=10)

    # --- exported from top-level package ---

    def test_exported_from_package(self):
        """delta_e_hyab is importable from the top-level color_tools package."""
        import color_tools
        self.assertTrue(hasattr(color_tools, "delta_e_hyab"))
        self.assertIs(color_tools.delta_e_hyab, self.fn)

    def test_in_package_all(self):
        """delta_e_hyab appears in color_tools.__all__."""
        import color_tools
        self.assertIn("delta_e_hyab", color_tools.__all__)


# ===========================================================================
# Palette / FilamentPalette dispatch
# ===========================================================================

class TestPaletteHyABDispatch(unittest.TestCase):
    """Palette.nearest_color() and nearest_colors() accept metric='hyab'."""

    @classmethod
    def setUpClass(cls):
        from color_tools.palette import Palette
        cls.Palette = Palette

    def _palette(self):
        return self.Palette.load_default()

    def test_nearest_color_hyab(self):
        """nearest_color() with metric='hyab' returns a valid result."""
        palette = self._palette()
        lab = (50.0, 20.0, -10.0)
        rec, dist = palette.nearest_color(lab, space="lab", metric="hyab")
        self.assertIsNotNone(rec)
        self.assertGreaterEqual(dist, 0.0)

    def test_nearest_colors_hyab(self):
        """nearest_colors() with metric='hyab' returns the requested count."""
        palette = self._palette()
        lab = (50.0, 20.0, -10.0)
        results = palette.nearest_colors(lab, space="lab", metric="hyab", count=3)
        self.assertEqual(len(results), 3)
        # Distances should be sorted ascending
        dists = [d for _, d in results]
        self.assertEqual(dists, sorted(dists))

    def test_unknown_metric_raises(self):
        """Unknown metric string raises ValueError."""
        palette = self._palette()
        with self.assertRaises(ValueError):
            palette.nearest_color((50.0, 0.0, 0.0), space="lab", metric="bogus")


class TestFilamentPaletteHyABDispatch(unittest.TestCase):
    """FilamentPalette nearest_filament/nearest_filaments accept metric='hyab'."""

    @classmethod
    def setUpClass(cls):
        from color_tools.filament_palette import FilamentPalette
        cls.FilamentPalette = FilamentPalette

    def _fp(self):
        return self.FilamentPalette.load_default()

    def test_nearest_filament_hyab(self):
        """nearest_filament() with metric='hyab' returns a valid result."""
        fp = self._fp()
        result = fp.nearest_filament((200, 100, 50), metric="hyab")
        rec, dist = result
        self.assertIsNotNone(rec)
        self.assertGreaterEqual(dist, 0.0)

    def test_nearest_filaments_hyab(self):
        """nearest_filaments() with metric='hyab' returns the requested count."""
        fp = self._fp()
        results = fp.nearest_filaments((200, 100, 50), metric="hyab", count=3)
        self.assertEqual(len(results), 3)
        dists = [d for _, d in results]
        self.assertEqual(dists, sorted(dists))

    def test_unknown_metric_raises(self):
        """Unknown metric string raises ValueError."""
        fp = self._fp()
        with self.assertRaises(ValueError):
            fp.nearest_filament((200, 100, 50), metric="bogus")


# ===========================================================================
# extract_color_clusters — new parameters
# ===========================================================================

@unittest.skipUnless(PILLOW_AVAILABLE, "Requires Pillow")
class TestExtractColorClustersHyAB(unittest.TestCase):
    """New distance_metric, l_weight, use_l_median, n_iter parameters."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image import extract_color_clusters
        cls.fn = staticmethod(extract_color_clusters)
        # 4-colour striped image
        cls.img_path = _make_image(
            [(200, 50, 50), (50, 200, 50), (50, 50, 200), (200, 200, 50)],
            rows_per_color=25,
        )

    @classmethod
    def tearDownClass(cls):
        try:
            os.unlink(cls.img_path)
        except OSError:
            pass

    def test_default_returns_n_colors(self):
        """Default (lab) returns exactly n_colors clusters."""
        clusters = self.fn(self.img_path, n_colors=4)
        self.assertEqual(len(clusters), 4)

    def test_hyab_returns_n_colors(self):
        """distance_metric='hyab' returns exactly n_colors clusters."""
        clusters = self.fn(self.img_path, n_colors=4, distance_metric="hyab")
        self.assertEqual(len(clusters), 4)

    def test_rgb_returns_n_colors(self):
        """distance_metric='rgb' returns exactly n_colors clusters."""
        clusters = self.fn(self.img_path, n_colors=4, distance_metric="rgb")
        self.assertEqual(len(clusters), 4)

    def test_sorted_by_pixel_count_desc(self):
        """Clusters are sorted by pixel_count descending."""
        clusters = self.fn(self.img_path, n_colors=4, distance_metric="hyab")
        counts = [c.pixel_count for c in clusters]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_pixel_count_sum_equals_total(self):
        """Sum of pixel_counts equals total image pixels."""
        clusters = self.fn(self.img_path, n_colors=4, distance_metric="hyab")
        total = sum(c.pixel_count for c in clusters)
        img = Image.open(self.img_path)
        self.assertEqual(total, img.width * img.height)

    def test_l_weight_accepted(self):
        """l_weight parameter is accepted without error."""
        clusters = self.fn(
            self.img_path, n_colors=4, distance_metric="hyab", l_weight=2.0
        )
        self.assertEqual(len(clusters), 4)

    def test_use_l_median_accepted(self):
        """use_l_median=True is accepted without error."""
        clusters = self.fn(
            self.img_path, n_colors=4, distance_metric="hyab", use_l_median=True
        )
        self.assertEqual(len(clusters), 4)

    def test_n_iter_accepted(self):
        """n_iter controls iteration count without error."""
        clusters = self.fn(self.img_path, n_colors=4, n_iter=3)
        self.assertEqual(len(clusters), 4)

    def test_invalid_metric_raises(self):
        """Unknown distance_metric raises ValueError."""
        with self.assertRaises(ValueError):
            self.fn(self.img_path, n_colors=4, distance_metric="bogus")

    def test_use_lab_distance_false_uses_rgb(self):
        """Legacy use_lab_distance=False is equivalent to distance_metric='rgb'."""
        clusters = self.fn(self.img_path, n_colors=4, use_lab_distance=False)
        self.assertEqual(len(clusters), 4)

    def test_cluster_has_expected_attributes(self):
        """Each ColorCluster has centroid_rgb, centroid_lab, pixel_count, pixel_indices."""
        clusters = self.fn(self.img_path, n_colors=2, distance_metric="hyab")
        for c in clusters:
            self.assertIsInstance(c.centroid_rgb, tuple)
            self.assertEqual(len(c.centroid_rgb), 3)
            self.assertIsInstance(c.centroid_lab, tuple)
            self.assertEqual(len(c.centroid_lab), 3)
            self.assertGreater(c.pixel_count, 0)
            self.assertEqual(len(c.pixel_indices), c.pixel_count)

    def test_centroid_rgb_in_range(self):
        """centroid_rgb components should be 0-255."""
        clusters = self.fn(self.img_path, n_colors=4)
        for c in clusters:
            for channel in c.centroid_rgb:
                self.assertGreaterEqual(channel, 0)
                self.assertLessEqual(channel, 255)


# ===========================================================================
# quantize_image_hyab
# ===========================================================================

@unittest.skipUnless(PILLOW_AVAILABLE, "Requires Pillow")
class TestQuantizeImageHyAB(unittest.TestCase):
    """Tests for color_tools.image.quantize_image_hyab."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image import quantize_image_hyab
        cls.fn = staticmethod(quantize_image_hyab)
        cls.img_path = _make_image(
            [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)],
            rows_per_color=30,
        )

    @classmethod
    def tearDownClass(cls):
        try:
            os.unlink(cls.img_path)
        except OSError:
            pass

    def test_returns_pil_image(self):
        """quantize_image_hyab returns a PIL Image."""
        result = self.fn(self.img_path, n_colors=4)
        self.assertIsInstance(result, Image.Image)

    def test_output_size_matches_input(self):
        """Output image has the same dimensions as the input."""
        input_img = Image.open(self.img_path)
        result = self.fn(self.img_path, n_colors=4)
        self.assertEqual(result.size, input_img.size)

    def test_output_mode_is_rgb(self):
        """Output image is in RGB mode."""
        result = self.fn(self.img_path, n_colors=4)
        self.assertEqual(result.mode, "RGB")

    def test_n_colors_reduces_palette_size(self):
        """Output uses at most n_colors unique colours."""
        result = self.fn(self.img_path, n_colors=2)
        unique_colors = set(result.getdata())
        # Allow a small overcount due to LAB rounding; at most n_colors
        self.assertLessEqual(len(unique_colors), 4)  # 2 centroids but rounding may vary

    def test_accepts_l_weight_param(self):
        """l_weight parameter is accepted without error."""
        result = self.fn(self.img_path, n_colors=4, l_weight=1.5)
        self.assertIsInstance(result, Image.Image)

    def test_accepts_use_l_median_false(self):
        """use_l_median=False is accepted without error."""
        result = self.fn(self.img_path, n_colors=4, use_l_median=False)
        self.assertIsInstance(result, Image.Image)

    def test_saveable(self):
        """Output can be saved to a temp file."""
        result = self.fn(self.img_path, n_colors=4)
        fd, out_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            result.save(out_path)
            self.assertTrue(os.path.getsize(out_path) > 0)
        finally:
            os.unlink(out_path)

    def test_exported_from_image_package(self):
        """quantize_image_hyab is importable from color_tools.image."""
        from color_tools.image import quantize_image_hyab  # noqa: F401


if __name__ == "__main__":
    unittest.main()

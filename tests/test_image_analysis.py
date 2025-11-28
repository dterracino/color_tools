"""Unit tests for color_tools.image.analysis module.

Tests the HueForge-specific image analysis functions for color extraction
and luminance redistribution.
"""

import unittest
import sys
import tempfile
import os
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Check for dependencies before running tests
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


def create_test_image(width: int, height: int, color: tuple[int, int, int]) -> str:
    """Create a solid color test image and return its path."""
    img = Image.new('RGB', (width, height), color)
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    img.save(path)
    return path


def create_multicolor_test_image(colors: list[tuple[int, int, int]], rows_per_color: int = 10) -> str:
    """Create a test image with horizontal stripes of different colors."""
    height = len(colors) * rows_per_color
    width = 100
    img = Image.new('RGB', (width, height))
    
    for i, color in enumerate(colors):
        for y in range(i * rows_per_color, (i + 1) * rows_per_color):
            for x in range(width):
                img.putpixel((x, y), color)
    
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    img.save(path)
    return path


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestLValueToHueforgeLayer(unittest.TestCase):
    """Test l_value_to_hueforge_layer function."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import l_value_to_hueforge_layer
        cls.l_value_to_hueforge_layer = staticmethod(l_value_to_hueforge_layer)
    
    def test_l_value_zero_returns_layer_1(self):
        """Test that L=0 (darkest) maps to layer 1."""
        result = self.l_value_to_hueforge_layer(0.0)
        self.assertEqual(result, 1)
    
    def test_l_value_100_returns_max_layer(self):
        """Test that L=100 (brightest) maps to layer 27."""
        result = self.l_value_to_hueforge_layer(100.0)
        self.assertEqual(result, 27)
    
    def test_l_value_50_returns_middle_layer(self):
        """Test that L=50 maps to middle layer."""
        result = self.l_value_to_hueforge_layer(50.0)
        # 50% of 27 layers = 13.5, so layer 14
        self.assertIn(result, [13, 14, 15])  # Allow some variation
    
    def test_custom_total_layers(self):
        """Test with custom number of layers."""
        result = self.l_value_to_hueforge_layer(0.0, total_layers=10)
        self.assertEqual(result, 1)
        
        result = self.l_value_to_hueforge_layer(100.0, total_layers=10)
        self.assertEqual(result, 10)
    
    def test_l_value_clamped_below_zero(self):
        """Test that negative L values are clamped to 0."""
        result = self.l_value_to_hueforge_layer(-10.0)
        self.assertEqual(result, 1)
    
    def test_l_value_clamped_above_100(self):
        """Test that L values above 100 are clamped."""
        result = self.l_value_to_hueforge_layer(110.0)
        self.assertEqual(result, 27)
    
    def test_layer_range_is_correct(self):
        """Test that layers are in valid range for various L values."""
        for l_val in range(0, 101, 10):
            layer = self.l_value_to_hueforge_layer(float(l_val))
            self.assertGreaterEqual(layer, 1)
            self.assertLessEqual(layer, 27)


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestColorClusterDataclass(unittest.TestCase):
    """Test ColorCluster dataclass."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import ColorCluster
        cls.ColorCluster = ColorCluster
    
    def test_color_cluster_creation(self):
        """Test creating a ColorCluster instance."""
        cluster = self.ColorCluster(
            centroid_rgb=(255, 0, 0),
            centroid_lab=(53.24, 80.09, 67.20),
            pixel_indices=[0, 1, 2, 3],
            pixel_count=4
        )
        self.assertEqual(cluster.centroid_rgb, (255, 0, 0))
        self.assertEqual(cluster.centroid_lab, (53.24, 80.09, 67.20))
        self.assertEqual(cluster.pixel_indices, [0, 1, 2, 3])
        self.assertEqual(cluster.pixel_count, 4)
    
    def test_color_cluster_with_empty_indices(self):
        """Test ColorCluster with no pixel indices."""
        cluster = self.ColorCluster(
            centroid_rgb=(0, 0, 0),
            centroid_lab=(0.0, 0.0, 0.0),
            pixel_indices=[],
            pixel_count=0
        )
        self.assertEqual(cluster.pixel_count, 0)
        self.assertEqual(len(cluster.pixel_indices), 0)


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestColorChangeDataclass(unittest.TestCase):
    """Test ColorChange dataclass."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import ColorChange
        cls.ColorChange = ColorChange
    
    def test_color_change_creation(self):
        """Test creating a ColorChange instance."""
        change = self.ColorChange(
            original_rgb=(100, 50, 30),
            original_lch=(30.0, 40.0, 25.0),
            new_rgb=(90, 45, 28),
            new_lch=(0.0, 40.0, 25.0),
            delta_e=15.5,
            hueforge_layer=1
        )
        self.assertEqual(change.original_rgb, (100, 50, 30))
        self.assertEqual(change.new_rgb, (90, 45, 28))
        self.assertEqual(change.delta_e, 15.5)
        self.assertEqual(change.hueforge_layer, 1)


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestExtractColorClusters(unittest.TestCase):
    """Test extract_color_clusters function."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import extract_color_clusters
        cls.extract_color_clusters = staticmethod(extract_color_clusters)
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_files = []
    
    def tearDown(self):
        """Clean up test files."""
        for filepath in self.test_files:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_extract_from_solid_color_image(self):
        """Test extracting clusters from a solid color image."""
        img_path = create_test_image(50, 50, (255, 0, 0))
        self.test_files.append(img_path)
        
        clusters = self.extract_color_clusters(img_path, n_colors=3)
        
        self.assertEqual(len(clusters), 3)
        # All pixels should be in clusters
        total_pixels = sum(c.pixel_count for c in clusters)
        self.assertEqual(total_pixels, 50 * 50)
    
    def test_extract_from_multicolor_image(self):
        """Test extracting clusters from a multi-color image."""
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        img_path = create_multicolor_test_image(colors, rows_per_color=20)
        self.test_files.append(img_path)
        
        clusters = self.extract_color_clusters(img_path, n_colors=3)
        
        self.assertEqual(len(clusters), 3)
        # Check that we extracted colors similar to the input colors
        centroids = [c.centroid_rgb for c in clusters]
        for color in colors:
            # At least one centroid should be close to each input color
            closest = min(centroids, key=lambda c: sum((a-b)**2 for a, b in zip(c, color)))
            distance = sum((a-b)**2 for a, b in zip(closest, color))
            self.assertLess(distance, 5000)  # Allow some tolerance
    
    def test_extract_with_lab_distance(self):
        """Test extracting with LAB distance (default)."""
        img_path = create_test_image(20, 20, (128, 64, 192))
        self.test_files.append(img_path)
        
        clusters = self.extract_color_clusters(img_path, n_colors=2, use_lab_distance=True)
        
        self.assertEqual(len(clusters), 2)
    
    def test_extract_without_lab_distance(self):
        """Test extracting with RGB distance."""
        img_path = create_test_image(20, 20, (128, 64, 192))
        self.test_files.append(img_path)
        
        clusters = self.extract_color_clusters(img_path, n_colors=2, use_lab_distance=False)
        
        self.assertEqual(len(clusters), 2)
    
    def test_file_not_found_raises_error(self):
        """Test that nonexistent file raises error."""
        with self.assertRaises(FileNotFoundError):
            self.extract_color_clusters("/nonexistent/path/image.png")
    
    def test_cluster_has_correct_attributes(self):
        """Test that returned clusters have all required attributes."""
        img_path = create_test_image(30, 30, (100, 150, 200))
        self.test_files.append(img_path)
        
        clusters = self.extract_color_clusters(img_path, n_colors=1)
        
        self.assertEqual(len(clusters), 1)
        cluster = clusters[0]
        
        # Check attributes exist and have correct types
        self.assertIsInstance(cluster.centroid_rgb, tuple)
        self.assertEqual(len(cluster.centroid_rgb), 3)
        self.assertIsInstance(cluster.centroid_lab, tuple)
        self.assertEqual(len(cluster.centroid_lab), 3)
        self.assertIsInstance(cluster.pixel_indices, list)
        self.assertIsInstance(cluster.pixel_count, int)


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestExtractUniqueColors(unittest.TestCase):
    """Test extract_unique_colors function."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import extract_unique_colors
        cls.extract_unique_colors = staticmethod(extract_unique_colors)
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_files = []
    
    def tearDown(self):
        """Clean up test files."""
        for filepath in self.test_files:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_extract_from_solid_color(self):
        """Test extracting colors from a solid color image."""
        img_path = create_test_image(40, 40, (0, 255, 0))
        self.test_files.append(img_path)
        
        colors = self.extract_unique_colors(img_path, n_colors=3)
        
        self.assertEqual(len(colors), 3)
        self.assertTrue(all(isinstance(c, tuple) for c in colors))
        self.assertTrue(all(len(c) == 3 for c in colors))
    
    def test_returns_rgb_tuples(self):
        """Test that function returns RGB tuples."""
        img_path = create_test_image(20, 20, (128, 64, 32))
        self.test_files.append(img_path)
        
        colors = self.extract_unique_colors(img_path, n_colors=2)
        
        for color in colors:
            self.assertIsInstance(color, tuple)
            self.assertEqual(len(color), 3)
            for component in color:
                self.assertIsInstance(component, int)
                self.assertGreaterEqual(component, 0)
                self.assertLessEqual(component, 255)


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestRedistributeLuminance(unittest.TestCase):
    """Test redistribute_luminance function."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import redistribute_luminance
        cls.redistribute_luminance = staticmethod(redistribute_luminance)
    
    def test_single_color_goes_to_middle(self):
        """Test that a single color is assigned L=50."""
        colors = [(128, 128, 128)]
        changes = self.redistribute_luminance(colors)
        
        self.assertEqual(len(changes), 1)
        # Single color should go to L=50
        self.assertAlmostEqual(changes[0].new_lch[0], 50.0, places=1)
    
    def test_two_colors_get_extremes(self):
        """Test that two colors get L=0 and L=100."""
        colors = [(50, 50, 50), (200, 200, 200)]
        changes = self.redistribute_luminance(colors)
        
        self.assertEqual(len(changes), 2)
        # Sorted by original L, so darker should have L=0, lighter L=100
        l_values = [c.new_lch[0] for c in changes]
        self.assertAlmostEqual(min(l_values), 0.0, places=1)
        self.assertAlmostEqual(max(l_values), 100.0, places=1)
    
    def test_multiple_colors_evenly_distributed(self):
        """Test that multiple colors are evenly distributed."""
        colors = [(30, 30, 30), (100, 100, 100), (200, 200, 200)]
        changes = self.redistribute_luminance(colors)
        
        self.assertEqual(len(changes), 3)
        l_values = [c.new_lch[0] for c in changes]
        # Should be 0, 50, 100
        self.assertAlmostEqual(l_values[0], 0.0, places=1)
        self.assertAlmostEqual(l_values[1], 50.0, places=1)
        self.assertAlmostEqual(l_values[2], 100.0, places=1)
    
    def test_returns_color_change_objects(self):
        """Test that function returns ColorChange objects."""
        colors = [(100, 50, 30), (200, 180, 160)]
        changes = self.redistribute_luminance(colors)
        
        for change in changes:
            # Check all attributes exist
            self.assertIsNotNone(change.original_rgb)
            self.assertIsNotNone(change.original_lch)
            self.assertIsNotNone(change.new_rgb)
            self.assertIsNotNone(change.new_lch)
            self.assertIsNotNone(change.delta_e)
            self.assertIsNotNone(change.hueforge_layer)
    
    def test_delta_e_is_positive(self):
        """Test that delta_e values are non-negative."""
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        changes = self.redistribute_luminance(colors)
        
        for change in changes:
            self.assertGreaterEqual(change.delta_e, 0.0)
    
    def test_hueforge_layers_are_assigned(self):
        """Test that Hueforge layers are assigned correctly."""
        colors = [(0, 0, 0), (255, 255, 255)]
        changes = self.redistribute_luminance(colors)
        
        for change in changes:
            self.assertGreaterEqual(change.hueforge_layer, 1)
            self.assertLessEqual(change.hueforge_layer, 27)
    
    def test_colors_sorted_by_original_luminance(self):
        """Test that output is sorted by original luminance."""
        colors = [(200, 200, 200), (50, 50, 50), (128, 128, 128)]
        changes = self.redistribute_luminance(colors)
        
        # Original luminances should be in ascending order
        original_l = [c.original_lch[0] for c in changes]
        self.assertEqual(original_l, sorted(original_l))


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestFormatColorChangeReport(unittest.TestCase):
    """Test format_color_change_report function."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import format_color_change_report, redistribute_luminance
        cls.format_color_change_report = staticmethod(format_color_change_report)
        cls.redistribute_luminance = staticmethod(redistribute_luminance)
    
    def test_report_contains_header(self):
        """Test that report contains the expected header."""
        colors = [(100, 50, 30)]
        changes = self.redistribute_luminance(colors)
        report = self.format_color_change_report(changes)
        
        self.assertIn("Color Luminance Redistribution Report", report)
    
    def test_report_contains_rgb_values(self):
        """Test that report contains RGB values."""
        colors = [(255, 128, 64)]
        changes = self.redistribute_luminance(colors)
        report = self.format_color_change_report(changes)
        
        self.assertIn("RGB", report)
    
    def test_report_contains_delta_e(self):
        """Test that report contains Delta E values."""
        colors = [(100, 50, 30), (200, 180, 160)]
        changes = self.redistribute_luminance(colors)
        report = self.format_color_change_report(changes)
        
        self.assertIn("ΔE", report)
    
    def test_report_contains_hueforge_layer(self):
        """Test that report contains Hueforge layer info."""
        colors = [(100, 50, 30)]
        changes = self.redistribute_luminance(colors)
        report = self.format_color_change_report(changes)
        
        self.assertIn("Hueforge Layer", report)
    
    def test_empty_changes_produces_header_only(self):
        """Test that empty changes list produces just header."""
        report = self.format_color_change_report([])
        
        self.assertIn("Color Luminance Redistribution Report", report)
    
    def test_report_contains_numbered_entries(self):
        """Test that entries are numbered."""
        colors = [(100, 50, 30), (200, 180, 160)]
        changes = self.redistribute_luminance(colors)
        report = self.format_color_change_report(changes)
        
        self.assertIn("1.", report)
        self.assertIn("2.", report)


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestAnalysisIntegration(unittest.TestCase):
    """Integration tests for the analysis module."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import (
            extract_color_clusters,
            redistribute_luminance,
            format_color_change_report
        )
        cls.extract_color_clusters = staticmethod(extract_color_clusters)
        cls.redistribute_luminance = staticmethod(redistribute_luminance)
        cls.format_color_change_report = staticmethod(format_color_change_report)
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_files = []
    
    def tearDown(self):
        """Clean up test files."""
        for filepath in self.test_files:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_full_pipeline(self):
        """Test the complete color extraction and redistribution pipeline."""
        # Create a multi-color test image
        colors = [(50, 50, 50), (150, 150, 150), (250, 250, 250)]
        img_path = create_multicolor_test_image(colors, rows_per_color=20)
        self.test_files.append(img_path)
        
        # Extract clusters
        clusters = self.extract_color_clusters(img_path, n_colors=3)
        self.assertEqual(len(clusters), 3)
        
        # Redistribute luminance
        extracted_colors = [c.centroid_rgb for c in clusters]
        changes = self.redistribute_luminance(extracted_colors)
        self.assertEqual(len(changes), 3)
        
        # Format report
        report = self.format_color_change_report(changes)
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)


if __name__ == '__main__':
    unittest.main()

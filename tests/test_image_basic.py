"""Unit tests for color_tools.image.basic module.

Tests the general-purpose image analysis functions for color counting,
histogram generation, brightness/contrast analysis, and more.
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

try:
    from skimage import restoration
    SCIKIT_IMAGE_AVAILABLE = True
except ImportError:
    SCIKIT_IMAGE_AVAILABLE = False


def create_solid_image(width: int, height: int, color: tuple[int, int, int]) -> str:
    """Create a solid color test image and return its path."""
    img = Image.new('RGB', (width, height), color)
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    img.save(path)
    return path


def create_indexed_image(width: int, height: int, color: tuple[int, int, int]) -> str:
    """Create an indexed (palette) mode test image and return its path."""
    # Create RGB image first
    img = Image.new('RGB', (width, height), color)
    # Convert to palette mode
    img_indexed = img.convert('P')
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    img_indexed.save(path)
    return path


def create_gradient_image(width: int, height: int) -> str:
    """Create a horizontal gradient image and return its path."""
    img = Image.new('RGB', (width, height))
    for x in range(width):
        gray_val = int(255 * x / (width - 1)) if width > 1 else 128
        for y in range(height):
            img.putpixel((x, y), (gray_val, gray_val, gray_val))
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    img.save(path)
    return path


def create_checkerboard_image(width: int, height: int, cell_size: int = 10) -> str:
    """Create a checkerboard pattern image and return its path."""
    img = Image.new('RGB', (width, height))
    for x in range(width):
        for y in range(height):
            if ((x // cell_size) + (y // cell_size)) % 2 == 0:
                img.putpixel((x, y), (255, 255, 255))
            else:
                img.putpixel((x, y), (0, 0, 0))
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    img.save(path)
    return path


def create_multicolor_image(colors: list[tuple[int, int, int]]) -> str:
    """Create an image with each pixel having a different color from the list."""
    # Calculate size to fit all colors
    width = len(colors)
    height = 1
    img = Image.new('RGB', (width, height))
    for i, color in enumerate(colors):
        img.putpixel((i, 0), color)
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    img.save(path)
    return path


def create_dark_image(width: int, height: int) -> str:
    """Create a dark image (low brightness)."""
    img = Image.new('RGB', (width, height), (20, 20, 20))
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    img.save(path)
    return path


def create_bright_image(width: int, height: int) -> str:
    """Create a bright image (high brightness)."""
    img = Image.new('RGB', (width, height), (240, 240, 240))
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    img.save(path)
    return path


def create_low_contrast_image(width: int, height: int) -> str:
    """Create a low contrast image (uniform brightness)."""
    # All pixels have similar brightness
    img = Image.new('RGB', (width, height), (128, 128, 128))
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    img.save(path)
    return path


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestCountUniqueColors(unittest.TestCase):
    """Test count_unique_colors function."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import count_unique_colors
        cls.count_unique_colors = staticmethod(count_unique_colors)
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_files = []
    
    def tearDown(self):
        """Clean up test files."""
        for filepath in self.test_files:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_solid_color_image_returns_one(self):
        """Test that a solid color image has 1 unique color."""
        img_path = create_solid_image(50, 50, (255, 0, 0))
        self.test_files.append(img_path)
        
        count = self.count_unique_colors(img_path)
        self.assertEqual(count, 1)
    
    def test_two_color_checkerboard(self):
        """Test that a checkerboard has 2 unique colors."""
        img_path = create_checkerboard_image(100, 100, cell_size=10)
        self.test_files.append(img_path)
        
        count = self.count_unique_colors(img_path)
        self.assertEqual(count, 2)
    
    def test_gradient_has_many_colors(self):
        """Test that a gradient has many unique colors."""
        img_path = create_gradient_image(256, 10)
        self.test_files.append(img_path)
        
        count = self.count_unique_colors(img_path)
        self.assertEqual(count, 256)  # Each gray level from 0 to 255
    
    def test_multicolor_image(self):
        """Test counting colors in a multi-color image."""
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (128, 64, 32)]
        img_path = create_multicolor_image(colors)
        self.test_files.append(img_path)
        
        count = self.count_unique_colors(img_path)
        self.assertEqual(count, len(colors))
    
    def test_nonexistent_file_raises_error(self):
        """Test that nonexistent file raises error."""
        with self.assertRaises(FileNotFoundError):
            self.count_unique_colors("/nonexistent/path/image.png")
    
    def test_returns_integer(self):
        """Test that function returns an integer."""
        img_path = create_solid_image(10, 10, (100, 100, 100))
        self.test_files.append(img_path)
        
        count = self.count_unique_colors(img_path)
        self.assertIsInstance(count, int)
    
    def test_accepts_path_object(self):
        """Test that function accepts Path objects."""
        img_path = create_solid_image(10, 10, (50, 50, 50))
        self.test_files.append(img_path)
        
        count = self.count_unique_colors(Path(img_path))
        self.assertEqual(count, 1)


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestIsIndexedMode(unittest.TestCase):
    """Test is_indexed_mode function."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import is_indexed_mode
        cls.is_indexed_mode = staticmethod(is_indexed_mode)
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_files = []
    
    def tearDown(self):
        """Clean up test files."""
        for filepath in self.test_files:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_rgb_image_returns_false(self):
        """Test that an RGB image is not indexed."""
        img_path = create_solid_image(50, 50, (255, 0, 0))
        self.test_files.append(img_path)
        
        result = self.is_indexed_mode(img_path)
        self.assertFalse(result)
    
    def test_indexed_image_returns_true(self):
        """Test that an indexed image returns True."""
        img_path = create_indexed_image(50, 50, (255, 0, 0))
        self.test_files.append(img_path)
        
        result = self.is_indexed_mode(img_path)
        self.assertTrue(result)
    
    def test_nonexistent_file_raises_error(self):
        """Test that nonexistent file raises error."""
        with self.assertRaises(FileNotFoundError):
            self.is_indexed_mode("/nonexistent/path/image.png")
    
    def test_returns_boolean(self):
        """Test that function returns a boolean."""
        img_path = create_solid_image(10, 10, (100, 100, 100))
        self.test_files.append(img_path)
        
        result = self.is_indexed_mode(img_path)
        self.assertIsInstance(result, bool)


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestGetColorHistogram(unittest.TestCase):
    """Test get_color_histogram function."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import get_color_histogram
        cls.get_color_histogram = staticmethod(get_color_histogram)
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_files = []
    
    def tearDown(self):
        """Clean up test files."""
        for filepath in self.test_files:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_solid_color_histogram(self):
        """Test histogram of a solid color image."""
        color = (128, 64, 32)
        img_path = create_solid_image(10, 10, color)
        self.test_files.append(img_path)
        
        histogram = self.get_color_histogram(img_path)
        
        self.assertEqual(len(histogram), 1)
        self.assertIn(color, histogram)
        self.assertEqual(histogram[color], 100)  # 10x10 = 100 pixels
    
    def test_checkerboard_histogram(self):
        """Test histogram of a checkerboard image."""
        img_path = create_checkerboard_image(100, 100, cell_size=10)
        self.test_files.append(img_path)
        
        histogram = self.get_color_histogram(img_path)
        
        self.assertEqual(len(histogram), 2)
        self.assertIn((255, 255, 255), histogram)
        self.assertIn((0, 0, 0), histogram)
        # Each color should have roughly half the pixels
        self.assertEqual(histogram[(255, 255, 255)] + histogram[(0, 0, 0)], 10000)
    
    def test_histogram_keys_are_rgb_tuples(self):
        """Test that histogram keys are RGB tuples."""
        img_path = create_solid_image(5, 5, (200, 150, 100))
        self.test_files.append(img_path)
        
        histogram = self.get_color_histogram(img_path)
        
        for color in histogram.keys():
            self.assertIsInstance(color, tuple)
            self.assertEqual(len(color), 3)
            for component in color:
                self.assertIsInstance(component, int)
    
    def test_histogram_values_are_integers(self):
        """Test that histogram values are integers."""
        img_path = create_gradient_image(10, 1)
        self.test_files.append(img_path)
        
        histogram = self.get_color_histogram(img_path)
        
        for count in histogram.values():
            self.assertIsInstance(count, int)
            self.assertGreater(count, 0)
    
    def test_nonexistent_file_raises_error(self):
        """Test that nonexistent file raises error."""
        with self.assertRaises(FileNotFoundError):
            self.get_color_histogram("/nonexistent/path/image.png")


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestGetDominantColor(unittest.TestCase):
    """Test get_dominant_color function."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import get_dominant_color
        cls.get_dominant_color = staticmethod(get_dominant_color)
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_files = []
    
    def tearDown(self):
        """Clean up test files."""
        for filepath in self.test_files:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_solid_color_returns_that_color(self):
        """Test that a solid color image returns its color."""
        color = (255, 128, 64)
        img_path = create_solid_image(50, 50, color)
        self.test_files.append(img_path)
        
        dominant = self.get_dominant_color(img_path)
        self.assertEqual(dominant, color)
    
    def test_returns_rgb_tuple(self):
        """Test that function returns an RGB tuple."""
        img_path = create_gradient_image(20, 20)
        self.test_files.append(img_path)
        
        dominant = self.get_dominant_color(img_path)
        
        self.assertIsInstance(dominant, tuple)
        self.assertEqual(len(dominant), 3)
        for component in dominant:
            self.assertIsInstance(component, int)
            self.assertGreaterEqual(component, 0)
            self.assertLessEqual(component, 255)
    
    def test_nonexistent_file_raises_error(self):
        """Test that nonexistent file raises error."""
        with self.assertRaises(FileNotFoundError):
            self.get_dominant_color("/nonexistent/path/image.png")
    
    def test_majority_color_is_dominant(self):
        """Test that the color with most pixels is returned."""
        # Create image with 75% red, 25% blue
        width, height = 100, 100
        img = Image.new('RGB', (width, height))
        for x in range(width):
            for y in range(height):
                if x < 75:
                    img.putpixel((x, y), (255, 0, 0))  # Red
                else:
                    img.putpixel((x, y), (0, 0, 255))  # Blue
        
        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        img.save(path)
        self.test_files.append(path)
        
        dominant = self.get_dominant_color(path)
        self.assertEqual(dominant, (255, 0, 0))


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestAnalyzeBrightness(unittest.TestCase):
    """Test analyze_brightness function."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import analyze_brightness
        cls.analyze_brightness = staticmethod(analyze_brightness)
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_files = []
    
    def tearDown(self):
        """Clean up test files."""
        for filepath in self.test_files:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_dark_image_assessment(self):
        """Test that a dark image is assessed as 'dark'."""
        img_path = create_dark_image(50, 50)
        self.test_files.append(img_path)
        
        result = self.analyze_brightness(img_path)
        
        self.assertEqual(result['assessment'], 'dark')
        self.assertLess(result['mean_brightness'], 60)
    
    def test_bright_image_assessment(self):
        """Test that a bright image is assessed as 'bright'."""
        img_path = create_bright_image(50, 50)
        self.test_files.append(img_path)
        
        result = self.analyze_brightness(img_path)
        
        self.assertEqual(result['assessment'], 'bright')
        self.assertGreater(result['mean_brightness'], 195)
    
    def test_normal_image_assessment(self):
        """Test that a mid-tone image is assessed as 'normal'."""
        img_path = create_solid_image(50, 50, (128, 128, 128))
        self.test_files.append(img_path)
        
        result = self.analyze_brightness(img_path)
        
        self.assertEqual(result['assessment'], 'normal')
    
    def test_returns_expected_keys(self):
        """Test that function returns expected keys."""
        img_path = create_solid_image(10, 10, (100, 100, 100))
        self.test_files.append(img_path)
        
        result = self.analyze_brightness(img_path)
        
        self.assertIn('mean_brightness', result)
        self.assertIn('assessment', result)
    
    def test_mean_brightness_is_float(self):
        """Test that mean_brightness is a float."""
        img_path = create_gradient_image(50, 50)
        self.test_files.append(img_path)
        
        result = self.analyze_brightness(img_path)
        
        self.assertIsInstance(result['mean_brightness'], float)
    
    def test_nonexistent_file_raises_error(self):
        """Test that nonexistent file raises error."""
        with self.assertRaises(FileNotFoundError):
            self.analyze_brightness("/nonexistent/path/image.png")


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestAnalyzeContrast(unittest.TestCase):
    """Test analyze_contrast function."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import analyze_contrast
        cls.analyze_contrast = staticmethod(analyze_contrast)
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_files = []
    
    def tearDown(self):
        """Clean up test files."""
        for filepath in self.test_files:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_low_contrast_image_assessment(self):
        """Test that a uniform image has low contrast."""
        img_path = create_low_contrast_image(50, 50)
        self.test_files.append(img_path)
        
        result = self.analyze_contrast(img_path)
        
        self.assertEqual(result['assessment'], 'low')
        self.assertLess(result['contrast_std'], 40)
    
    def test_high_contrast_image_assessment(self):
        """Test that a high contrast image is assessed as 'normal'."""
        img_path = create_checkerboard_image(100, 100, cell_size=5)
        self.test_files.append(img_path)
        
        result = self.analyze_contrast(img_path)
        
        self.assertEqual(result['assessment'], 'normal')
        self.assertGreater(result['contrast_std'], 40)
    
    def test_returns_expected_keys(self):
        """Test that function returns expected keys."""
        img_path = create_solid_image(10, 10, (100, 100, 100))
        self.test_files.append(img_path)
        
        result = self.analyze_contrast(img_path)
        
        self.assertIn('contrast_std', result)
        self.assertIn('assessment', result)
    
    def test_contrast_std_is_float(self):
        """Test that contrast_std is a float."""
        img_path = create_gradient_image(50, 50)
        self.test_files.append(img_path)
        
        result = self.analyze_contrast(img_path)
        
        self.assertIsInstance(result['contrast_std'], float)
    
    def test_solid_color_has_zero_contrast(self):
        """Test that a solid color image has zero contrast."""
        img_path = create_solid_image(50, 50, (150, 150, 150))
        self.test_files.append(img_path)
        
        result = self.analyze_contrast(img_path)
        
        self.assertAlmostEqual(result['contrast_std'], 0.0, places=2)


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE and SCIKIT_IMAGE_AVAILABLE, 
                      "Requires Pillow, numpy, and scikit-image")
class TestAnalyzeNoiseLevel(unittest.TestCase):
    """Test analyze_noise_level function."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import analyze_noise_level
        cls.analyze_noise_level = staticmethod(analyze_noise_level)
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_files = []
    
    def tearDown(self):
        """Clean up test files."""
        for filepath in self.test_files:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_clean_image_assessment(self):
        """Test that a solid color image is assessed as 'clean'."""
        img_path = create_solid_image(100, 100, (128, 128, 128))
        self.test_files.append(img_path)
        
        result = self.analyze_noise_level(img_path)
        
        self.assertEqual(result['assessment'], 'clean')
    
    def test_returns_expected_keys(self):
        """Test that function returns expected keys."""
        img_path = create_solid_image(100, 100, (100, 100, 100))
        self.test_files.append(img_path)
        
        result = self.analyze_noise_level(img_path)
        
        self.assertIn('noise_sigma', result)
        self.assertIn('assessment', result)
    
    def test_noise_sigma_is_float(self):
        """Test that noise_sigma is a float."""
        img_path = create_gradient_image(100, 100)
        self.test_files.append(img_path)
        
        result = self.analyze_noise_level(img_path)
        
        self.assertIsInstance(result['noise_sigma'], float)
    
    def test_noise_sigma_is_non_negative(self):
        """Test that noise_sigma is non-negative."""
        img_path = create_checkerboard_image(100, 100)
        self.test_files.append(img_path)
        
        result = self.analyze_noise_level(img_path)
        
        self.assertGreaterEqual(result['noise_sigma'], 0.0)
    
    def test_custom_crop_size(self):
        """Test that custom crop_size is respected."""
        img_path = create_solid_image(200, 200, (100, 100, 100))
        self.test_files.append(img_path)
        
        result = self.analyze_noise_level(img_path, crop_size=64)
        
        self.assertIn('noise_sigma', result)
    
    def test_small_image_handled(self):
        """Test that small images (smaller than crop_size) are handled."""
        img_path = create_solid_image(50, 50, (100, 100, 100))
        self.test_files.append(img_path)
        
        # Should not raise error even though image is smaller than default crop_size
        result = self.analyze_noise_level(img_path)
        
        self.assertIn('noise_sigma', result)


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestAnalyzeDynamicRange(unittest.TestCase):
    """Test analyze_dynamic_range function."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import analyze_dynamic_range
        cls.analyze_dynamic_range = staticmethod(analyze_dynamic_range)
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_files = []
    
    def tearDown(self):
        """Clean up test files."""
        for filepath in self.test_files:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_full_range_gradient(self):
        """Test that a full range gradient has 'full' assessment."""
        img_path = create_gradient_image(256, 10)
        self.test_files.append(img_path)
        
        result = self.analyze_dynamic_range(img_path)
        
        self.assertEqual(result['min_value'], 0)
        self.assertEqual(result['max_value'], 255)
        self.assertEqual(result['range'], 255)
        self.assertEqual(result['range_assessment'], 'full')
    
    def test_limited_range_image(self):
        """Test that a limited range image has 'limited' assessment."""
        img_path = create_solid_image(50, 50, (128, 128, 128))
        self.test_files.append(img_path)
        
        result = self.analyze_dynamic_range(img_path)
        
        self.assertEqual(result['range'], 0)
        self.assertEqual(result['range_assessment'], 'limited')
    
    def test_returns_expected_keys(self):
        """Test that function returns expected keys."""
        img_path = create_solid_image(10, 10, (100, 100, 100))
        self.test_files.append(img_path)
        
        result = self.analyze_dynamic_range(img_path)
        
        expected_keys = ['min_value', 'max_value', 'range', 'mean_brightness',
                         'range_assessment', 'gamma_suggestion']
        for key in expected_keys:
            self.assertIn(key, result)
    
    def test_dark_image_gamma_suggestion(self):
        """Test gamma suggestion for dark image."""
        img_path = create_dark_image(50, 50)
        self.test_files.append(img_path)
        
        result = self.analyze_dynamic_range(img_path)
        
        self.assertIn('Decrease', result['gamma_suggestion'])
    
    def test_bright_image_gamma_suggestion(self):
        """Test gamma suggestion for bright image."""
        img_path = create_bright_image(50, 50)
        self.test_files.append(img_path)
        
        result = self.analyze_dynamic_range(img_path)
        
        self.assertIn('Increase', result['gamma_suggestion'])
    
    def test_normal_image_gamma_suggestion(self):
        """Test gamma suggestion for normal brightness image."""
        img_path = create_solid_image(50, 50, (128, 128, 128))
        self.test_files.append(img_path)
        
        result = self.analyze_dynamic_range(img_path)
        
        self.assertIn('Normal', result['gamma_suggestion'])
    
    def test_min_max_values_are_integers(self):
        """Test that min and max values are integers."""
        img_path = create_gradient_image(100, 100)
        self.test_files.append(img_path)
        
        result = self.analyze_dynamic_range(img_path)
        
        self.assertIsInstance(result['min_value'], int)
        self.assertIsInstance(result['max_value'], int)
        self.assertIsInstance(result['range'], int)


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestBasicIntegration(unittest.TestCase):
    """Integration tests for the basic analysis module."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import (
            count_unique_colors,
            get_color_histogram,
            get_dominant_color,
            analyze_brightness,
            analyze_contrast,
            analyze_dynamic_range
        )
        cls.count_unique_colors = staticmethod(count_unique_colors)
        cls.get_color_histogram = staticmethod(get_color_histogram)
        cls.get_dominant_color = staticmethod(get_dominant_color)
        cls.analyze_brightness = staticmethod(analyze_brightness)
        cls.analyze_contrast = staticmethod(analyze_contrast)
        cls.analyze_dynamic_range = staticmethod(analyze_dynamic_range)
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_files = []
    
    def tearDown(self):
        """Clean up test files."""
        for filepath in self.test_files:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_all_functions_on_same_image(self):
        """Test all analysis functions on the same image."""
        img_path = create_gradient_image(100, 100)
        self.test_files.append(img_path)
        
        # Count unique colors
        count = self.count_unique_colors(img_path)
        self.assertIsInstance(count, int)
        self.assertGreater(count, 0)
        
        # Get histogram
        histogram = self.get_color_histogram(img_path)
        self.assertIsInstance(histogram, dict)
        self.assertEqual(len(histogram), count)
        
        # Get dominant color
        dominant = self.get_dominant_color(img_path)
        self.assertIsInstance(dominant, tuple)
        
        # Analyze brightness
        brightness = self.analyze_brightness(img_path)
        self.assertIn('mean_brightness', brightness)
        
        # Analyze contrast
        contrast = self.analyze_contrast(img_path)
        self.assertIn('contrast_std', contrast)
        
        # Analyze dynamic range
        dynamic_range = self.analyze_dynamic_range(img_path)
        self.assertIn('range', dynamic_range)


@unittest.skipUnless(PILLOW_AVAILABLE and NUMPY_AVAILABLE, "Requires Pillow and numpy")
class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    @classmethod
    def setUpClass(cls):
        from color_tools.image import (
            count_unique_colors,
            get_color_histogram,
            get_dominant_color
        )
        cls.count_unique_colors = staticmethod(count_unique_colors)
        cls.get_color_histogram = staticmethod(get_color_histogram)
        cls.get_dominant_color = staticmethod(get_dominant_color)
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_files = []
    
    def tearDown(self):
        """Clean up test files."""
        for filepath in self.test_files:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_single_pixel_image(self):
        """Test handling of a 1x1 image."""
        img_path = create_solid_image(1, 1, (255, 128, 64))
        self.test_files.append(img_path)
        
        count = self.count_unique_colors(img_path)
        self.assertEqual(count, 1)
        
        histogram = self.get_color_histogram(img_path)
        self.assertEqual(len(histogram), 1)
        self.assertEqual(histogram[(255, 128, 64)], 1)
        
        dominant = self.get_dominant_color(img_path)
        self.assertEqual(dominant, (255, 128, 64))
    
    def test_rgba_image_alpha_ignored(self):
        """Test that RGBA images have alpha channel ignored."""
        # Create RGBA image
        img = Image.new('RGBA', (10, 10), (255, 0, 0, 128))
        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        img.save(path)
        self.test_files.append(path)
        
        count = self.count_unique_colors(path)
        self.assertEqual(count, 1)
        
        dominant = self.get_dominant_color(path)
        self.assertEqual(dominant, (255, 0, 0))
    
    def test_grayscale_image_converted_to_rgb(self):
        """Test that grayscale images are handled correctly."""
        # Create grayscale image
        img = Image.new('L', (10, 10), 128)
        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        img.save(path)
        self.test_files.append(path)
        
        count = self.count_unique_colors(path)
        self.assertEqual(count, 1)
        
        dominant = self.get_dominant_color(path)
        self.assertEqual(dominant, (128, 128, 128))


if __name__ == '__main__':
    unittest.main()

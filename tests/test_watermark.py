"""
Tests for image watermarking functionality.

Tests text, image, and SVG watermarking with various options including:
- Text watermarks with fonts, colors, stroke
- Image watermarks (PNG)
- SVG watermarks
- Position presets and custom coordinates
- Opacity and scaling
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from PIL import Image, ImageDraw

# Try importing watermark functions
try:
    from color_tools.image import (
        add_text_watermark,
        add_image_watermark,
        add_svg_watermark,
        IMAGE_AVAILABLE
    )
    WATERMARK_AVAILABLE = IMAGE_AVAILABLE
except ImportError:
    WATERMARK_AVAILABLE = False

# Try importing cairosvg for SVG tests
# Note: On Windows, cairosvg requires GTK+ runtime libraries
# If this fails, SVG tests will be skipped automatically
SVG_AVAILABLE = False
try:
    import cairosvg
    SVG_AVAILABLE = True
except (ImportError, OSError):
    # OSError is raised when Cairo C libraries are not installed
    pass


@unittest.skipUnless(WATERMARK_AVAILABLE, "Watermarking requires Pillow")
class TestTextWatermark(unittest.TestCase):
    """Test text watermarking functionality."""
    
    def setUp(self):
        """Create a temporary test image."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_image = Image.new('RGB', (400, 300), color='white')
        
    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir)
    
    def test_basic_text_watermark(self):
        """Test basic text watermark with default settings."""
        result = add_text_watermark(
            self.test_image,
            text="© 2025 Test"
        )
        
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.mode, 'RGBA')
        self.assertEqual(result.size, self.test_image.size)
    
    def test_text_positions(self):
        """Test all position presets."""
        positions = [
            "top-left", "top-center", "top-right",
            "center-left", "center", "center-right",
            "bottom-left", "bottom-center", "bottom-right"
        ]
        
        for position in positions:
            with self.subTest(position=position):
                result = add_text_watermark(
                    self.test_image,
                    text="TEST",
                    position=position  # type: ignore[arg-type]
                )
                self.assertIsInstance(result, Image.Image)
    
    def test_custom_position(self):
        """Test custom x,y position coordinates."""
        result = add_text_watermark(
            self.test_image,
            text="CUSTOM",
            position=(50, 75)
        )
        self.assertIsInstance(result, Image.Image)
    
    def test_text_color(self):
        """Test custom text color."""
        result = add_text_watermark(
            self.test_image,
            text="COLORED",
            color=(255, 0, 0)  # Red
        )
        self.assertIsInstance(result, Image.Image)
    
    def test_text_opacity(self):
        """Test text opacity variations."""
        for opacity in [0.0, 0.5, 1.0]:
            with self.subTest(opacity=opacity):
                result = add_text_watermark(
                    self.test_image,
                    text="OPACITY",
                    opacity=opacity
                )
                self.assertIsInstance(result, Image.Image)
    
    def test_text_stroke(self):
        """Test text with outline stroke."""
        result = add_text_watermark(
            self.test_image,
            text="OUTLINED",
            color=(255, 255, 255),
            stroke_color=(0, 0, 0),
            stroke_width=2
        )
        self.assertIsInstance(result, Image.Image)
    
    def test_font_size(self):
        """Test various font sizes."""
        for size in [12, 24, 48, 72]:
            with self.subTest(size=size):
                result = add_text_watermark(
                    self.test_image,
                    text="SIZE",
                    font_size=size
                )
                self.assertIsInstance(result, Image.Image)
    
    def test_margin_setting(self):
        """Test custom margin values."""
        for margin in [5, 10, 20, 50]:
            with self.subTest(margin=margin):
                result = add_text_watermark(
                    self.test_image,
                    text="MARGIN",
                    position="bottom-right",
                    margin=margin
                )
                self.assertIsInstance(result, Image.Image)
    
    def test_font_name_conflict(self):
        """Test that specifying both font_name and font_file raises error."""
        with self.assertRaises(ValueError):
            add_text_watermark(
                self.test_image,
                text="ERROR",
                font_name="Arial",
                font_file="somefont.ttf"
            )


@unittest.skipUnless(WATERMARK_AVAILABLE, "Watermarking requires Pillow")
class TestImageWatermark(unittest.TestCase):
    """Test image watermarking functionality."""
    
    def setUp(self):
        """Create temporary test images."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create base image
        self.test_image = Image.new('RGB', (400, 300), color='white')
        
        # Create watermark image with transparency
        self.watermark_img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        draw = ImageDraw.Draw(self.watermark_img)
        draw.ellipse([25, 25, 75, 75], fill=(0, 0, 255, 200))
        
        # Save watermark
        self.watermark_path = Path(self.temp_dir) / "watermark.png"
        self.watermark_img.save(self.watermark_path)
    
    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir)
    
    def test_basic_image_watermark(self):
        """Test basic image watermark."""
        result = add_image_watermark(
            self.test_image,
            watermark_path=self.watermark_path
        )
        
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.mode, 'RGBA')
        self.assertEqual(result.size, self.test_image.size)
    
    def test_image_positions(self):
        """Test all position presets for image watermark."""
        positions = ["top-left", "center", "bottom-right"]
        
        for position in positions:
            with self.subTest(position=position):
                result = add_image_watermark(
                    self.test_image,
                    watermark_path=self.watermark_path,
                    position=position  # type: ignore[arg-type]
                )
                self.assertIsInstance(result, Image.Image)
    
    def test_image_scale(self):
        """Test scaling image watermark."""
        for scale in [0.5, 1.0, 2.0]:
            with self.subTest(scale=scale):
                result = add_image_watermark(
                    self.test_image,
                    watermark_path=self.watermark_path,
                    scale=scale
                )
                self.assertIsInstance(result, Image.Image)
    
    def test_image_opacity(self):
        """Test image watermark opacity."""
        for opacity in [0.3, 0.7, 1.0]:
            with self.subTest(opacity=opacity):
                result = add_image_watermark(
                    self.test_image,
                    watermark_path=self.watermark_path,
                    opacity=opacity
                )
                self.assertIsInstance(result, Image.Image)
    
    def test_image_without_alpha(self):
        """Test image watermark with RGB image (no alpha)."""
        # Create RGB watermark
        rgb_watermark = Image.new('RGB', (80, 80), color=(0, 255, 0))
        rgb_path = Path(self.temp_dir) / "rgb_watermark.png"
        rgb_watermark.save(rgb_path)
        
        result = add_image_watermark(
            self.test_image,
            watermark_path=rgb_path
        )
        self.assertIsInstance(result, Image.Image)


@unittest.skipUnless(WATERMARK_AVAILABLE and SVG_AVAILABLE, 
                     "SVG watermarking requires Pillow and cairosvg")
class TestSVGWatermark(unittest.TestCase):
    """Test SVG watermarking functionality."""
    
    def setUp(self):
        """Create temporary test files."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create base image
        self.test_image = Image.new('RGB', (400, 300), color='white')
        
        # Create simple SVG file
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="40" fill="blue" opacity="0.8"/>
  <text x="50" y="55" font-size="20" text-anchor="middle" fill="white">SVG</text>
</svg>'''
        
        self.svg_path = Path(self.temp_dir) / "logo.svg"
        self.svg_path.write_text(svg_content, encoding='utf-8')
    
    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir)
    
    def test_basic_svg_watermark(self):
        """Test basic SVG watermark."""
        result = add_svg_watermark(
            self.test_image,
            svg_path=self.svg_path
        )
        
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.mode, 'RGBA')
        self.assertEqual(result.size, self.test_image.size)
    
    def test_svg_positions(self):
        """Test SVG watermark positions."""
        positions = ["top-left", "center", "bottom-right"]
        
        for position in positions:
            with self.subTest(position=position):
                result = add_svg_watermark(
                    self.test_image,
                    svg_path=self.svg_path,
                    position=position  # type: ignore[arg-type]
                )
                self.assertIsInstance(result, Image.Image)
    
    def test_svg_scale(self):
        """Test scaling SVG watermark."""
        for scale in [0.5, 1.0, 1.5]:
            with self.subTest(scale=scale):
                result = add_svg_watermark(
                    self.test_image,
                    svg_path=self.svg_path,
                    scale=scale
                )
                self.assertIsInstance(result, Image.Image)
    
    def test_svg_opacity(self):
        """Test SVG watermark opacity."""
        for opacity in [0.4, 0.8]:
            with self.subTest(opacity=opacity):
                result = add_svg_watermark(
                    self.test_image,
                    svg_path=self.svg_path,
                    opacity=opacity
                )
                self.assertIsInstance(result, Image.Image)
    
    def test_svg_explicit_size(self):
        """Test SVG watermark with explicit width/height."""
        result = add_svg_watermark(
            self.test_image,
            svg_path=self.svg_path,
            width=150,
            height=150
        )
        self.assertIsInstance(result, Image.Image)


@unittest.skipUnless(WATERMARK_AVAILABLE, "Watermarking requires Pillow")
class TestWatermarkIntegration(unittest.TestCase):
    """Integration tests for watermarking."""
    
    def setUp(self):
        """Create test images with various modes."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create images in different modes
        self.rgb_image = Image.new('RGB', (300, 200), color='lightblue')
        self.rgba_image = Image.new('RGBA', (300, 200), color=(200, 200, 255, 255))
        self.gray_image = Image.new('L', (300, 200), color=128)
    
    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir)
    
    def test_watermark_on_rgb_image(self):
        """Test watermarking RGB image."""
        result = add_text_watermark(
            self.rgb_image,
            text="RGB TEST"
        )
        # Should convert to RGBA
        self.assertEqual(result.mode, 'RGBA')
    
    def test_watermark_on_rgba_image(self):
        """Test watermarking RGBA image."""
        result = add_text_watermark(
            self.rgba_image,
            text="RGBA TEST"
        )
        self.assertEqual(result.mode, 'RGBA')
    
    def test_watermark_on_grayscale_image(self):
        """Test watermarking grayscale image."""
        result = add_text_watermark(
            self.gray_image,
            text="GRAY TEST"
        )
        # Should convert to RGBA
        self.assertEqual(result.mode, 'RGBA')
    
    def test_save_watermarked_image(self):
        """Test saving watermarked image to file."""
        result = add_text_watermark(
            self.rgb_image,
            text="SAVE TEST",
            opacity=0.7
        )
        
        # Save as PNG (supports transparency)
        output_path = Path(self.temp_dir) / "watermarked.png"
        result.save(output_path)
        self.assertTrue(output_path.exists())
        
        # Verify saved image can be loaded
        with Image.open(output_path) as loaded:
            self.assertEqual(loaded.size, result.size)
    
    def test_multiple_watermarks_sequential(self):
        """Test applying multiple watermarks sequentially."""
        # First watermark
        result1 = add_text_watermark(
            self.rgb_image,
            text="FIRST",
            position="top-left"
        )
        
        # Second watermark on result
        result2 = add_text_watermark(
            result1,
            text="SECOND",
            position="bottom-right"
        )
        
        self.assertIsInstance(result2, Image.Image)
        self.assertEqual(result2.size, self.rgb_image.size)


@unittest.skipUnless(WATERMARK_AVAILABLE, "Watermarking requires Pillow")
class TestCalculatePosition(unittest.TestCase):
    """Tests for the _calculate_position internal helper."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image.watermark import _calculate_position
        cls._calculate_position = staticmethod(_calculate_position)

    def test_custom_tuple_returned_directly(self):
        """Custom (x, y) tuple is passed through unchanged."""
        result = self._calculate_position((400, 300), (100, 50), (25, 75))
        self.assertEqual(result, (25, 75))

    def test_top_left_uses_margin(self):
        result = self._calculate_position((400, 300), (100, 50), "top-left", margin=10)
        self.assertEqual(result, (10, 10))

    def test_top_right_uses_margin(self):
        result = self._calculate_position((400, 300), (100, 50), "top-right", margin=10)
        self.assertEqual(result, (290, 10))   # 400 - 100 - 10

    def test_bottom_left_uses_margin(self):
        result = self._calculate_position((400, 300), (100, 50), "bottom-left", margin=10)
        self.assertEqual(result, (10, 240))   # 300 - 50 - 10

    def test_bottom_right_uses_margin(self):
        result = self._calculate_position((400, 300), (100, 50), "bottom-right", margin=10)
        self.assertEqual(result, (290, 240))

    def test_center(self):
        result = self._calculate_position((400, 300), (100, 50), "center")
        self.assertEqual(result, (150, 125))  # (400-100)//2, (300-50)//2

    def test_top_center(self):
        result = self._calculate_position((400, 300), (100, 50), "top-center", margin=5)
        self.assertEqual(result, (150, 5))

    def test_bottom_center(self):
        result = self._calculate_position((400, 300), (100, 50), "bottom-center", margin=5)
        self.assertEqual(result, (150, 245))  # 300 - 50 - 5

    def test_center_left(self):
        result = self._calculate_position((400, 300), (100, 50), "center-left", margin=8)
        self.assertEqual(result, (8, 125))

    def test_center_right(self):
        result = self._calculate_position((400, 300), (100, 50), "center-right", margin=8)
        self.assertEqual(result, (292, 125))  # 400 - 100 - 8

    def test_margin_zero(self):
        result = self._calculate_position((400, 300), (100, 50), "top-left", margin=0)
        self.assertEqual(result, (0, 0))

    def test_invalid_position_raises(self):
        """An unknown string position should raise KeyError."""
        with self.assertRaises(KeyError):
            self._calculate_position((400, 300), (100, 50), "invalid-position")  # type: ignore[arg-type]


@unittest.skipUnless(WATERMARK_AVAILABLE, "Watermarking requires Pillow")
class TestLoadFont(unittest.TestCase):
    """Tests for the _load_font internal helper."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image.watermark import _load_font
        cls._load_font = staticmethod(_load_font)

    def test_both_font_name_and_file_raises(self):
        with self.assertRaises(ValueError):
            self._load_font(font_name="Arial", font_file="somefont.ttf")

    def test_missing_font_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            self._load_font(font_file="/nonexistent/path/font.ttf")

    def test_default_fallback_returns_font(self):
        """No arguments → falls back to PIL default font without error."""
        from PIL import ImageFont
        font = self._load_font()
        self.assertIsInstance(font, (ImageFont.FreeTypeFont, ImageFont.ImageFont))

    def test_font_file_in_fonts_directory(self):
        """A bare filename is looked up in the bundled fonts/ directory."""
        from color_tools.image.watermark import _get_fonts_directory
        from PIL import ImageFont
        fonts_dir = _get_fonts_directory()
        ttf_files = list(fonts_dir.glob("*.ttf")) + list(fonts_dir.glob("*.otf"))
        if not ttf_files:
            self.skipTest("No bundled fonts available")
        font = self._load_font(font_file=ttf_files[0].name, size=12)
        self.assertIsInstance(font, ImageFont.FreeTypeFont)


@unittest.skipUnless(WATERMARK_AVAILABLE, "Watermarking requires Pillow")
class TestTextWatermarkPixelEffects(unittest.TestCase):
    """Verify actual pixel-level effects of text watermarking."""

    def setUp(self):
        self.base = Image.new('RGBA', (200, 100), (200, 200, 200, 255))

    def test_opacity_zero_leaves_pixels_unchanged(self):
        """opacity=0.0 draws fully transparent text — composite is identical to base."""
        result = add_text_watermark(
            self.base,
            text="INVISIBLE",
            position="center",
            opacity=0.0,
        )
        import numpy as np
        base_arr   = np.asarray(self.base.convert('RGBA'))
        result_arr = np.asarray(result)
        self.assertTrue(
            np.array_equal(base_arr, result_arr),
            "opacity=0.0 should produce a result identical to the base image",
        )

    def test_output_preserves_base_size(self):
        result = add_text_watermark(self.base, text="SIZE")
        self.assertEqual(result.size, self.base.size)

    def test_output_is_always_rgba(self):
        for mode in ('RGB', 'RGBA', 'L'):
            img = Image.new(mode, (100, 80), 128)
            result = add_text_watermark(img, text="M")
            self.assertEqual(result.mode, 'RGBA', f"Expected RGBA output for {mode} input")

    def test_watermark_path_accepts_path_object(self):
        """add_image_watermark accepts a pathlib.Path, not just a string."""
        import tempfile, os
        wm = Image.new('RGBA', (20, 20), (255, 0, 0, 128))
        fd, path_str = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        try:
            wm.save(path_str)
            result = add_image_watermark(self.base, watermark_path=Path(path_str))
            self.assertIsInstance(result, Image.Image)
        finally:
            if os.path.exists(path_str):
                os.remove(path_str)

    def test_watermark_path_accepts_string(self):
        """add_image_watermark accepts a plain string path."""
        import tempfile, os
        wm = Image.new('RGBA', (20, 20), (0, 255, 0, 200))
        fd, path_str = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        try:
            wm.save(path_str)
            result = add_image_watermark(self.base, watermark_path=path_str)
            self.assertIsInstance(result, Image.Image)
        finally:
            if os.path.exists(path_str):
                os.remove(path_str)


@unittest.skipIf(WATERMARK_AVAILABLE, "Test error handling when Pillow not available")
class TestWatermarkUnavailable(unittest.TestCase):
    """Test behavior when watermarking is not available."""

    def test_import_error_message(self):
        """Test that helpful error is raised when imports fail."""
        # This test only runs when IMAGE_AVAILABLE is False
        # We can't actually test the error message without mocking
        pass


if __name__ == '__main__':
    unittest.main()

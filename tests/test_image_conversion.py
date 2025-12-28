"""
Unit tests for image format conversion functionality.

Tests convert_image() and get_supported_formats() from color_tools.image.conversion.
"""

import unittest
from pathlib import Path
import tempfile
import shutil

try:
    from PIL import Image
    from color_tools.image import convert_image, get_supported_formats
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


@unittest.skipUnless(PILLOW_AVAILABLE, "Pillow not installed")
class TestConvertImage(unittest.TestCase):
    """Test image format conversion."""
    
    def setUp(self):
        """Create temporary directory and test images."""
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Create test images
        self.red_jpg = self.test_dir / "red.jpg"
        self.blue_png = self.test_dir / "blue.png"
        self.green_webp = self.test_dir / "green.webp"
        
        # Red JPEG
        img = Image.new("RGB", (100, 100), color="red")
        img.save(self.red_jpg, "JPEG", quality=85)
        
        # Blue PNG
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(self.blue_png, "PNG")
        
        # Green WebP (lossless)
        img = Image.new("RGB", (100, 100), color="green")
        img.save(self.green_webp, "WEBP", lossless=True)
    
    def tearDown(self):
        """Remove temporary directory."""
        shutil.rmtree(self.test_dir)
    
    def test_jpeg_to_png(self):
        """Test converting JPEG to PNG."""
        output = convert_image(self.red_jpg, output_format="png")
        
        self.assertTrue(output.exists())
        self.assertEqual(output.suffix, ".png")
        
        # Verify it's a valid PNG
        with Image.open(output) as img:
            self.assertEqual(img.format, "PNG")
            self.assertEqual(img.size, (100, 100))
    
    def test_png_to_jpeg(self):
        """Test converting PNG to JPEG."""
        output = convert_image(self.blue_png, output_format="jpeg")
        
        self.assertTrue(output.exists())
        self.assertEqual(output.suffix, ".jpeg")
        
        # Verify it's a valid JPEG
        with Image.open(output) as img:
            self.assertEqual(img.format, "JPEG")
    
    def test_webp_to_png(self):
        """Test converting WebP to PNG."""
        output = convert_image(self.green_webp, output_format="png")
        
        self.assertTrue(output.exists())
        self.assertEqual(output.suffix, ".png")
        
        with Image.open(output) as img:
            self.assertEqual(img.format, "PNG")
    
    def test_auto_output_filename(self):
        """Test auto-generated output filename."""
        output = convert_image(self.red_jpg, output_format="png")
        
        # Should be red.png (same stem, new extension)
        self.assertEqual(output.name, "red.png")
        self.assertEqual(output.parent, self.red_jpg.parent)
    
    def test_custom_output_path(self):
        """Test custom output path."""
        custom_path = self.test_dir / "custom_name.png"
        output = convert_image(self.red_jpg, output_path=custom_path)
        
        self.assertEqual(output, custom_path)
        self.assertTrue(custom_path.exists())
    
    def test_format_from_output_extension(self):
        """Test inferring format from output file extension."""
        output_path = self.test_dir / "output.webp"
        output = convert_image(self.red_jpg, output_path=output_path)
        
        with Image.open(output) as img:
            self.assertEqual(img.format, "WEBP")
    
    def test_default_format_is_png(self):
        """Test that default format is PNG when not specified."""
        output = convert_image(self.red_jpg)
        
        self.assertEqual(output.suffix, ".png")
    
    def test_jpeg_quality_default(self):
        """Test JPEG quality default (67)."""
        output = convert_image(self.blue_png, output_format="jpeg")
        
        # Just verify it was created successfully with default quality
        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 0)
    
    def test_jpeg_custom_quality(self):
        """Test JPEG with custom quality."""
        high_quality = convert_image(
            self.blue_png,
            output_path=self.test_dir / "high.jpg",
            output_format="jpeg",
            quality=95
        )
        
        low_quality = convert_image(
            self.blue_png,
            output_path=self.test_dir / "low.jpg",
            output_format="jpeg",
            quality=10
        )
        
        # High quality should produce larger file
        self.assertGreater(
            high_quality.stat().st_size,
            low_quality.stat().st_size
        )
    
    def test_webp_lossless_default(self):
        """Test that WebP uses lossless compression by default."""
        output = convert_image(self.red_jpg, output_format="webp")
        
        # Lossless WebP should be used (can't verify directly, just check it works)
        self.assertTrue(output.exists())
        self.assertEqual(output.suffix, ".webp")
    
    def test_webp_lossy_with_quality(self):
        """Test WebP with lossy compression and custom quality."""
        output = convert_image(
            self.red_jpg,
            output_format="webp",
            lossless=False,
            quality=50
        )
        
        self.assertTrue(output.exists())
    
    def test_rgba_to_jpeg_converts_to_rgb(self):
        """Test that RGBA images are converted to RGB for JPEG."""
        # Create RGBA image
        rgba_png = self.test_dir / "rgba.png"
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))  # Semi-transparent red
        img.save(rgba_png, "PNG")
        
        # Convert to JPEG (should handle alpha channel)
        output = convert_image(rgba_png, output_format="jpeg")
        
        with Image.open(output) as result:
            self.assertEqual(result.mode, "RGB")
    
    def test_jpg_alias_normalized_to_jpeg(self):
        """Test that 'jpg' is normalized to 'jpeg'."""
        output = convert_image(self.blue_png, output_format="jpg")
        
        # Should work and create JPEG
        with Image.open(output) as img:
            self.assertEqual(img.format, "JPEG")
    
    def test_file_not_found_raises_error(self):
        """Test that nonexistent input file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            convert_image("nonexistent.jpg")
    
    def test_preserves_image_content(self):
        """Test that conversion preserves image content (for lossless formats)."""
        # Create test image with specific pixel
        test_img = self.test_dir / "test.png"
        img = Image.new("RGB", (2, 2))
        img.putpixel((0, 0), (255, 0, 0))  # Red
        img.putpixel((1, 1), (0, 0, 255))  # Blue
        img.save(test_img, "PNG")
        
        # Convert PNG -> WebP (lossless) -> PNG
        webp_out = convert_image(test_img, output_format="webp")
        png_out = convert_image(webp_out, output_format="png")
        
        # Verify pixels are preserved
        with Image.open(png_out) as result:
            self.assertEqual(result.getpixel((0, 0)), (255, 0, 0))
            self.assertEqual(result.getpixel((1, 1)), (0, 0, 255))


@unittest.skipUnless(PILLOW_AVAILABLE, "Pillow not installed")
class TestGetSupportedFormats(unittest.TestCase):
    """Test get_supported_formats() function."""
    
    def test_returns_dict_with_input_output_keys(self):
        """Test that function returns dict with 'input' and 'output' keys."""
        formats = get_supported_formats()
        
        self.assertIsInstance(formats, dict)
        self.assertIn("input", formats)
        self.assertIn("output", formats)
    
    def test_input_output_are_lists(self):
        """Test that input and output values are lists."""
        formats = get_supported_formats()
        
        self.assertIsInstance(formats["input"], list)
        self.assertIsInstance(formats["output"], list)
    
    def test_common_formats_included(self):
        """Test that common formats are in the lists."""
        formats = get_supported_formats()
        
        common = ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff"]
        
        for fmt in common:
            self.assertIn(fmt, formats["input"])
            self.assertIn(fmt, formats["output"])
    
    def test_avif_included(self):
        """Test that AVIF is included (supported in Pillow 10+)."""
        formats = get_supported_formats()
        
        self.assertIn("avif", formats["input"])
        self.assertIn("avif", formats["output"])


@unittest.skipUnless(PILLOW_AVAILABLE, "Pillow not installed")
class TestConversionEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def setUp(self):
        """Create temporary directory and test image."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_img = self.test_dir / "test.png"
        
        img = Image.new("RGB", (50, 50), color="purple")
        img.save(self.test_img, "PNG")
    
    def tearDown(self):
        """Remove temporary directory."""
        shutil.rmtree(self.test_dir)
    
    def test_format_case_insensitive(self):
        """Test that format is case-insensitive."""
        output1 = convert_image(self.test_img, output_format="PNG")
        output2 = convert_image(self.test_img, 
                               output_path=self.test_dir / "test2.png",
                               output_format="png")
        
        with Image.open(output1) as img1, Image.open(output2) as img2:
            self.assertEqual(img1.format, img2.format)
    
    def test_tif_alias_normalized_to_tiff(self):
        """Test that 'tif' is normalized to 'tiff'."""
        output = convert_image(self.test_img, output_format="tif")
        
        with Image.open(output) as img:
            self.assertEqual(img.format, "TIFF")


if __name__ == "__main__":
    unittest.main()

"""Unit tests for color_tools.conversions module."""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from color_tools.conversions import (
    hex_to_rgb, rgb_to_hex,
    rgb_to_lab, lab_to_rgb,
    rgb_to_lch, lch_to_rgb,
    lab_to_lch, lch_to_lab,
    rgb_to_xyz, xyz_to_rgb,
    xyz_to_lab, lab_to_xyz,
    rgb_to_hsl, hsl_to_rgb,
    rgb_to_winhsl,
)


class TestHexRGBConversions(unittest.TestCase):
    """Test hex to RGB and RGB to hex conversions."""
    
    def test_hex_to_rgb_basic(self):
        """Test basic hex to RGB conversion."""
        self.assertEqual(hex_to_rgb("#FF0000"), (255, 0, 0))
        self.assertEqual(hex_to_rgb("#00FF00"), (0, 255, 0))
        self.assertEqual(hex_to_rgb("#0000FF"), (0, 0, 255))
        self.assertEqual(hex_to_rgb("#FFFFFF"), (255, 255, 255))
        self.assertEqual(hex_to_rgb("#000000"), (0, 0, 0))
    
    def test_hex_to_rgb_without_hash(self):
        """Test hex to RGB conversion without # prefix."""
        self.assertEqual(hex_to_rgb("FF0000"), (255, 0, 0))
        self.assertEqual(hex_to_rgb("00FF00"), (0, 255, 0))
    
    def test_hex_to_rgb_lowercase(self):
        """Test hex to RGB conversion with lowercase."""
        self.assertEqual(hex_to_rgb("#ff0000"), (255, 0, 0))
        self.assertEqual(hex_to_rgb("ff0000"), (255, 0, 0))
    
    def test_rgb_to_hex_basic(self):
        """Test basic RGB to hex conversion."""
        self.assertEqual(rgb_to_hex((255, 0, 0)), "#FF0000")
        self.assertEqual(rgb_to_hex((0, 255, 0)), "#00FF00")
        self.assertEqual(rgb_to_hex((0, 0, 255)), "#0000FF")
        self.assertEqual(rgb_to_hex((255, 255, 255)), "#FFFFFF")
        self.assertEqual(rgb_to_hex((0, 0, 0)), "#000000")
    
    def test_hex_rgb_roundtrip(self):
        """Test hex to RGB and back."""
        colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFFFF", "#123456", "#ABCDEF"]
        for hex_color in colors:
            rgb = hex_to_rgb(hex_color)
            result = rgb_to_hex(rgb)
            self.assertEqual(result, hex_color.upper())


class TestRGBLABConversions(unittest.TestCase):
    """Test RGB to LAB and LAB to RGB conversions."""
    
    def test_rgb_to_lab_primary_colors(self):
        """Test RGB to LAB conversion for primary colors."""
        # Red
        lab = rgb_to_lab((255, 0, 0))
        self.assertAlmostEqual(lab[0], 53.24, places=1)  # L*
        self.assertAlmostEqual(lab[1], 80.09, places=1)  # a*
        self.assertAlmostEqual(lab[2], 67.20, places=1)  # b*
        
        # Green
        lab = rgb_to_lab((0, 255, 0))
        self.assertAlmostEqual(lab[0], 87.74, places=1)  # L*
        self.assertAlmostEqual(lab[1], -86.18, places=1)  # a*
        self.assertAlmostEqual(lab[2], 83.18, places=1)  # b*
        
        # Blue
        lab = rgb_to_lab((0, 0, 255))
        self.assertAlmostEqual(lab[0], 32.30, places=1)  # L*
        self.assertAlmostEqual(lab[1], 79.19, places=1)  # a*
        self.assertAlmostEqual(lab[2], -107.86, places=1)  # b*
    
    def test_rgb_to_lab_white_black(self):
        """Test RGB to LAB conversion for white and black."""
        # White
        lab = rgb_to_lab((255, 255, 255))
        self.assertAlmostEqual(lab[0], 100.0, places=1)
        self.assertAlmostEqual(lab[1], 0.0, places=1)
        self.assertAlmostEqual(lab[2], 0.0, places=1)
        
        # Black
        lab = rgb_to_lab((0, 0, 0))
        self.assertAlmostEqual(lab[0], 0.0, places=1)
        self.assertAlmostEqual(lab[1], 0.0, places=1)
        self.assertAlmostEqual(lab[2], 0.0, places=1)
    
    def test_lab_to_rgb_roundtrip(self):
        """Test LAB to RGB and back (with clamping for out-of-gamut)."""
        test_colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (128, 128, 128),
            (255, 255, 0),
        ]
        for rgb_in in test_colors:
            lab = rgb_to_lab(rgb_in)
            rgb_out = lab_to_rgb(lab)
            # Allow small rounding errors
            for i in range(3):
                self.assertAlmostEqual(rgb_in[i], rgb_out[i], delta=1)


class TestRGBLCHConversions(unittest.TestCase):
    """Test RGB to LCH and LCH to RGB conversions."""
    
    def test_rgb_to_lch_basic(self):
        """Test RGB to LCH conversion."""
        # Red
        lch = rgb_to_lch((255, 0, 0))
        self.assertAlmostEqual(lch[0], 53.24, places=1)  # L*
        self.assertGreater(lch[1], 100)  # C* (chroma)
        self.assertAlmostEqual(lch[2], 40.0, delta=5)  # h* (hue)
    
    def test_lch_to_rgb_roundtrip(self):
        """Test LCH to RGB and back."""
        test_colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
        ]
        for rgb_in in test_colors:
            lch = rgb_to_lch(rgb_in)
            rgb_out = lch_to_rgb(lch)
            for i in range(3):
                self.assertAlmostEqual(rgb_in[i], rgb_out[i], delta=1)


class TestLABLCHConversions(unittest.TestCase):
    """Test LAB to LCH and LCH to LAB conversions."""
    
    def test_lab_to_lch_basic(self):
        """Test LAB to LCH conversion."""
        # Neutral gray (no chroma)
        lch = lab_to_lch((50, 0, 0))
        self.assertAlmostEqual(lch[0], 50.0, places=1)
        self.assertAlmostEqual(lch[1], 0.0, places=1)
        
        # Color with positive a and b
        lch = lab_to_lch((50, 25, 30))
        self.assertAlmostEqual(lch[0], 50.0, places=1)
        self.assertAlmostEqual(lch[1], 39.05, places=1)  # sqrt(25^2 + 30^2)
    
    def test_lch_to_lab_basic(self):
        """Test LCH to LAB conversion."""
        # Zero chroma
        lab = lch_to_lab((50, 0, 0))
        self.assertAlmostEqual(lab[0], 50.0, places=1)
        self.assertAlmostEqual(lab[1], 0.0, places=1)
        self.assertAlmostEqual(lab[2], 0.0, places=1)
    
    def test_lab_lch_roundtrip(self):
        """Test LAB to LCH and back."""
        test_colors = [
            (50, 25, 30),
            (75, -20, 40),
            (25, 10, -15),
        ]
        for lab_in in test_colors:
            lch = lab_to_lch(lab_in)
            lab_out = lch_to_lab(lch)
            for i in range(3):
                self.assertAlmostEqual(lab_in[i], lab_out[i], places=1)


class TestRGBXYZConversions(unittest.TestCase):
    """Test RGB to XYZ and XYZ to RGB conversions."""
    
    def test_rgb_to_xyz_white(self):
        """Test RGB to XYZ conversion for white."""
        xyz = rgb_to_xyz((255, 255, 255))
        # D65 white point in XYZ (0-100 scale)
        self.assertAlmostEqual(xyz[0], 95.047, places=1)
        self.assertAlmostEqual(xyz[1], 100.0, places=1)
        self.assertAlmostEqual(xyz[2], 108.883, places=1)
    
    def test_rgb_to_xyz_black(self):
        """Test RGB to XYZ conversion for black."""
        xyz = rgb_to_xyz((0, 0, 0))
        self.assertAlmostEqual(xyz[0], 0.0, places=2)
        self.assertAlmostEqual(xyz[1], 0.0, places=2)
        self.assertAlmostEqual(xyz[2], 0.0, places=2)
    
    def test_rgb_xyz_roundtrip(self):
        """Test RGB to XYZ and back."""
        test_colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (128, 128, 128),
        ]
        for rgb_in in test_colors:
            xyz = rgb_to_xyz(rgb_in)
            rgb_out = xyz_to_rgb(xyz)
            for i in range(3):
                self.assertAlmostEqual(rgb_in[i], rgb_out[i], delta=1)


class TestXYZLABConversions(unittest.TestCase):
    """Test XYZ to LAB and LAB to XYZ conversions."""
    
    def test_xyz_to_lab_white(self):
        """Test XYZ to LAB conversion for D65 white."""
        # D65 white point in XYZ (0-100 scale)
        xyz = (95.047, 100.000, 108.883)
        lab = xyz_to_lab(xyz)
        self.assertAlmostEqual(lab[0], 100.0, places=1)
        self.assertAlmostEqual(lab[1], 0.0, places=1)
        self.assertAlmostEqual(lab[2], 0.0, places=1)
    
    def test_xyz_lab_roundtrip(self):
        """Test XYZ to LAB and back."""
        test_xyz = [
            (50.0, 50.0, 50.0),
            (20.0, 30.0, 40.0),
            (80.0, 90.0, 100.0),
        ]
        for xyz_in in test_xyz:
            lab = xyz_to_lab(xyz_in)
            xyz_out = lab_to_xyz(lab)
            for i in range(3):
                self.assertAlmostEqual(xyz_in[i], xyz_out[i], places=1)


class TestRGBHSLConversions(unittest.TestCase):
    """Test RGB to HSL and HSL to RGB conversions."""
    
    def test_rgb_to_hsl_primary_colors(self):
        """Test RGB to HSL conversion for primary colors."""
        # Red
        hsl = rgb_to_hsl((255, 0, 0))
        self.assertAlmostEqual(hsl[0], 0.0, places=1)
        self.assertAlmostEqual(hsl[1], 100.0, places=1)
        self.assertAlmostEqual(hsl[2], 50.0, places=1)
        
        # Green
        hsl = rgb_to_hsl((0, 255, 0))
        self.assertAlmostEqual(hsl[0], 120.0, places=1)
        self.assertAlmostEqual(hsl[1], 100.0, places=1)
        self.assertAlmostEqual(hsl[2], 50.0, places=1)
        
        # Blue
        hsl = rgb_to_hsl((0, 0, 255))
        self.assertAlmostEqual(hsl[0], 240.0, places=1)
        self.assertAlmostEqual(hsl[1], 100.0, places=1)
        self.assertAlmostEqual(hsl[2], 50.0, places=1)
    
    def test_rgb_to_hsl_gray(self):
        """Test RGB to HSL conversion for gray."""
        hsl = rgb_to_hsl((128, 128, 128))
        self.assertAlmostEqual(hsl[1], 0.0, places=1)  # No saturation
        self.assertAlmostEqual(hsl[2], 50.2, places=0)  # ~50% lightness
    
    def test_hsl_to_rgb_basic(self):
        """Test HSL to RGB conversion."""
        # Red
        rgb = hsl_to_rgb((0, 100, 50))
        self.assertEqual(rgb, (255, 0, 0))
        
        # Green
        rgb = hsl_to_rgb((120, 100, 50))
        self.assertEqual(rgb, (0, 255, 0))
        
        # Blue
        rgb = hsl_to_rgb((240, 100, 50))
        self.assertEqual(rgb, (0, 0, 255))
    
    def test_rgb_hsl_roundtrip(self):
        """Test RGB to HSL and back."""
        test_colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (128, 64, 192),
        ]
        for rgb_in in test_colors:
            hsl = rgb_to_hsl(rgb_in)
            rgb_out = hsl_to_rgb(hsl)
            for i in range(3):
                self.assertAlmostEqual(rgb_in[i], rgb_out[i], delta=1)


class TestRGBWinHSLConversion(unittest.TestCase):
    """Test RGB to Windows HSL conversion."""
    
    def test_rgb_to_winhsl_primary_colors(self):
        """Test RGB to Windows HSL conversion for primary colors."""
        # Red
        winhsl = rgb_to_winhsl((255, 0, 0))
        self.assertAlmostEqual(winhsl[0], 0.0, places=1)
        self.assertAlmostEqual(winhsl[1], 240.0, places=1)
        self.assertAlmostEqual(winhsl[2], 120.0, places=1)
        
        # Green
        winhsl = rgb_to_winhsl((0, 255, 0))
        self.assertAlmostEqual(winhsl[0], 80.0, places=1)
        self.assertAlmostEqual(winhsl[1], 240.0, places=1)
        self.assertAlmostEqual(winhsl[2], 120.0, places=1)
        
        # Blue
        winhsl = rgb_to_winhsl((0, 0, 255))
        self.assertAlmostEqual(winhsl[0], 160.0, places=1)
        self.assertAlmostEqual(winhsl[1], 240.0, places=1)
        self.assertAlmostEqual(winhsl[2], 120.0, places=1)


if __name__ == '__main__':
    unittest.main()

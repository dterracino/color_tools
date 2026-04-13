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
    rgb_to_winhsl240,
    rgb_to_winhsl255,
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
    
    def test_hex_to_rgb_3char(self):
        """Test 3-character hex to RGB conversion."""
        # Basic 3-character hex codes
        self.assertEqual(hex_to_rgb("#F00"), (255, 0, 0))
        self.assertEqual(hex_to_rgb("#0F0"), (0, 255, 0))
        self.assertEqual(hex_to_rgb("#00F"), (0, 0, 255))
        self.assertEqual(hex_to_rgb("#FFF"), (255, 255, 255))
        self.assertEqual(hex_to_rgb("#000"), (0, 0, 0))
        
        # 3-character hex without # prefix
        self.assertEqual(hex_to_rgb("F00"), (255, 0, 0))
        self.assertEqual(hex_to_rgb("0F0"), (0, 255, 0))
        
        # Lowercase 3-character hex
        self.assertEqual(hex_to_rgb("#f00"), (255, 0, 0))
        self.assertEqual(hex_to_rgb("abc"), (170, 187, 204))
        
        # Mixed case
        self.assertEqual(hex_to_rgb("#AbC"), (170, 187, 204))
        
        # Specific example from issue: #24c -> #2244cc
        self.assertEqual(hex_to_rgb("#24c"), (34, 68, 204))
        self.assertEqual(hex_to_rgb("#24C"), (34, 68, 204))
        self.assertEqual(hex_to_rgb("24c"), (34, 68, 204))
        
        # Verify expansion logic: each character is duplicated
        # #rgb -> #rrggbb
        self.assertEqual(hex_to_rgb("#123"), (17, 34, 51))  # 0x11, 0x22, 0x33
        self.assertEqual(hex_to_rgb("#456"), (68, 85, 102))  # 0x44, 0x55, 0x66
    
    def test_hex_to_rgb_invalid(self):
        """Test invalid hex codes return None."""
        # Wrong length
        self.assertIsNone(hex_to_rgb("#12"))
        self.assertIsNone(hex_to_rgb("#12345"))
        self.assertIsNone(hex_to_rgb("#1234567"))
        
        # Invalid characters
        self.assertIsNone(hex_to_rgb("#GGG"))
        self.assertIsNone(hex_to_rgb("#GGGGGG"))
        self.assertIsNone(hex_to_rgb("#XYZ"))
    
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


class TestRGBWinHSL240Conversion(unittest.TestCase):
    """Test RGB to winHSL240 conversion (Windows Paint / Win32 GDI variant)."""
    
    def test_winhsl240_primary_colors(self):
        """Test winHSL240 for primary colors."""
        # Red  — H=0, S=240, L=120
        result = rgb_to_winhsl240((255, 0, 0))
        self.assertEqual(result[0], 0)
        self.assertEqual(result[1], 240)
        self.assertEqual(result[2], 120)
        
        # Green — H=80, S=240, L=120
        result = rgb_to_winhsl240((0, 255, 0))
        self.assertEqual(result[0], 80)
        self.assertEqual(result[1], 240)
        self.assertEqual(result[2], 120)
        
        # Blue — H=160, S=240, L=120
        result = rgb_to_winhsl240((0, 0, 255))
        self.assertEqual(result[0], 160)
        self.assertEqual(result[1], 240)
        self.assertEqual(result[2], 120)
    
    def test_winhsl240_white_and_black(self):
        """Test winHSL240 for white and black."""
        # White — S=0, L=240
        result = rgb_to_winhsl240((255, 255, 255))
        self.assertEqual(result[1], 0)
        self.assertEqual(result[2], 240)
        
        # Black — S=0, L=0
        result = rgb_to_winhsl240((0, 0, 0))
        self.assertEqual(result[1], 0)
        self.assertEqual(result[2], 0)
    
    def test_winhsl240_hue_never_exceeds_239(self):
        """H must always be ≤ 239 regardless of input — hue 240 = 0° (red), which is out-of-spec."""
        # Test all 256^3 is impractical, so test a broad sweep of hues
        import colorsys
        for hue_frac in [0.0, 0.25, 0.5, 0.75, 0.9979, 0.9999, 1.0 - 1e-9]:
            r, g, b = colorsys.hls_to_rgb(hue_frac, 0.5, 1.0)
            rgb = (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))
            result = rgb_to_winhsl240(rgb)
            self.assertLessEqual(result[0], 239, msg=f"H={result[0]} for hue_frac={hue_frac}")
    
    def test_winhsl240_sl_components_in_range(self):
        """S and L must be in 0–240."""
        for rgb in [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255), (0, 0, 0), (128, 64, 192)]:
            h, s, l = rgb_to_winhsl240(rgb)
            self.assertGreaterEqual(s, 0)
            self.assertLessEqual(s, 240)
            self.assertGreaterEqual(l, 0)
            self.assertLessEqual(l, 240)


class TestRGBWinHSL255Conversion(unittest.TestCase):
    """Test RGB to winHSL255 conversion (Microsoft Office variant)."""
    
    def test_winhsl255_primary_colors(self):
        """Test winHSL255 for primary colors."""
        # Red — H=0, S=255, L=128ish
        result = rgb_to_winhsl255((255, 0, 0))
        self.assertEqual(result[0], 0)
        self.assertEqual(result[1], 255)
        self.assertAlmostEqual(result[2], 128, delta=1)
        
        # Green — H≈85, S=255, L=128ish
        result = rgb_to_winhsl255((0, 255, 0))
        self.assertAlmostEqual(result[0], 85, delta=1)
        self.assertEqual(result[1], 255)
        self.assertAlmostEqual(result[2], 128, delta=1)
        
        # Blue — H≈170, S=255, L=128ish
        result = rgb_to_winhsl255((0, 0, 255))
        self.assertAlmostEqual(result[0], 170, delta=1)
        self.assertEqual(result[1], 255)
        self.assertAlmostEqual(result[2], 128, delta=1)
    
    def test_winhsl255_white_and_black(self):
        """Test winHSL255 for white and black."""
        # White — S=0, L=255
        result = rgb_to_winhsl255((255, 255, 255))
        self.assertEqual(result[1], 0)
        self.assertEqual(result[2], 255)
        
        # Black — S=0, L=0
        result = rgb_to_winhsl255((0, 0, 0))
        self.assertEqual(result[1], 0)
        self.assertEqual(result[2], 0)
    
    def test_winhsl255_hue_never_exceeds_254(self):
        """H must always be ≤ 254 — hue 255 = 0° (red) which is out-of-spec."""
        import colorsys
        for hue_frac in [0.0, 0.25, 0.5, 0.75, 0.998, 0.9999, 1.0 - 1e-9]:
            r, g, b = colorsys.hls_to_rgb(hue_frac, 0.5, 1.0)
            rgb = (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))
            result = rgb_to_winhsl255(rgb)
            self.assertLessEqual(result[0], 254, msg=f"H={result[0]} for hue_frac={hue_frac}")
    
    def test_winhsl255_sl_components_in_range(self):
        """S and L must be in 0–255."""
        for rgb in [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255), (0, 0, 0), (128, 64, 192)]:
            h, s, l = rgb_to_winhsl255(rgb)
            self.assertGreaterEqual(s, 0)
            self.assertLessEqual(s, 255)
            self.assertGreaterEqual(l, 0)
            self.assertLessEqual(l, 255)
    
    def test_winhsl255_differs_from_winhsl240(self):
        """winHSL255 and winHSL240 should produce different S and L for coloured pixels."""
        rgb = (128, 64, 192)
        r240 = rgb_to_winhsl240(rgb)
        r255 = rgb_to_winhsl255(rgb)
        # S and L should differ between the two variants
        self.assertNotEqual(r240[1], r255[1])
        self.assertNotEqual(r240[2], r255[2])


class TestWinHSLBackwardCompatAlias(unittest.TestCase):
    """Test that rgb_to_winhsl is a backward-compat alias for rgb_to_winhsl240."""
    
    def test_alias_returns_same_result(self):
        """rgb_to_winhsl must return identical results to rgb_to_winhsl240."""
        test_colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 255), (0, 0, 0), (128, 64, 192), (200, 100, 50),
        ]
        for rgb in test_colors:
            self.assertEqual(rgb_to_winhsl(rgb), rgb_to_winhsl240(rgb),
                             msg=f"Alias mismatch for {rgb}")
    
    def test_alias_is_same_function(self):
        """The alias should point to the same underlying function object."""
        self.assertIs(rgb_to_winhsl, rgb_to_winhsl240)


if __name__ == '__main__':
    unittest.main()

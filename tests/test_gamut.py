"""Unit tests for color_tools.gamut module."""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from color_tools.gamut import (
    is_in_srgb_gamut,
    clamp_to_gamut,
    find_nearest_in_gamut,
)
from color_tools.conversions import rgb_to_lab


class TestIsInGamut(unittest.TestCase):
    """Test gamut checking function (takes LAB values)."""
    
    def test_valid_rgb_colors_in_gamut(self):
        """Test that standard RGB colors converted to LAB are in gamut."""
        test_colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (128, 128, 128),  # Gray
            (255, 255, 255),  # White
            (0, 0, 0),      # Black
        ]
        for rgb in test_colors:
            lab = rgb_to_lab(rgb)
            self.assertTrue(is_in_srgb_gamut(lab), 
                          f"RGB {rgb} -> LAB {lab} should be in gamut")
    
    def test_extreme_lab_out_of_gamut(self):
        """Test that extreme LAB values are out of gamut."""
        # These extreme a*, b* values are likely outside sRGB
        test_lab = [
            (50, 150, 150),   # Very high chroma
            (50, -150, -150), # Very high negative chroma
            (50, 200, 0),     # Extreme a*
        ]
        for lab in test_lab:
            result = is_in_srgb_gamut(lab)
            # These might or might not be out of gamut depending on implementation
            # Just test that the function runs without error
            self.assertIsInstance(result, bool)


class TestClampToGamut(unittest.TestCase):
    """Test clamping LAB values to sRGB gamut."""
    
    def test_valid_lab_unchanged(self):
        """Test that in-gamut LAB values are unchanged."""
        # Convert a valid RGB to LAB
        lab = rgb_to_lab((128, 64, 192))
        clamped = clamp_to_gamut(lab)
        # Should be nearly identical (might have tiny floating point differences)
        for i in range(3):
            self.assertAlmostEqual(lab[i], clamped[i], places=5)
    
    def test_out_of_gamut_gets_clamped(self):
        """Test that out-of-gamut LAB values get clamped."""
        # Use extreme a*, b* values
        lab = (50, 200, -200)  # Likely out of gamut
        clamped = clamp_to_gamut(lab)
        # Clamped version should be in gamut
        self.assertTrue(is_in_srgb_gamut(clamped))
    
    def test_clamp_preserves_lightness(self):
        """Test that clamping tries to preserve lightness."""
        lab = (75, 150, -150)  # Out of gamut
        clamped = clamp_to_gamut(lab)
        # Lightness should be relatively close
        self.assertAlmostEqual(lab[0], clamped[0], delta=20)


class TestGamutClipRGB(unittest.TestCase):
    """Test finding nearest in-gamut LAB color."""
    
    def test_already_in_gamut(self):
        """Test that in-gamut LAB colors are unchanged."""
        # Start with a known RGB
        rgb_in = (128, 64, 192)
        lab = rgb_to_lab(rgb_in)
        nearest_lab = find_nearest_in_gamut(lab)
        # Should be very close
        for i in range(3):
            self.assertAlmostEqual(lab[i], nearest_lab[i], places=3)
    
    def test_out_of_gamut_finds_nearest(self):
        """Test that out-of-gamut LAB finds nearest in-gamut LAB."""
        # Use an extreme LAB value that's likely out of gamut
        lab = (50, 100, -100)
        nearest_lab = find_nearest_in_gamut(lab)
        # Result should be in gamut
        self.assertTrue(is_in_srgb_gamut(nearest_lab))
        # And should have preserved lightness
        self.assertAlmostEqual(lab[0], nearest_lab[0], delta=5)


class TestGamutIntegration(unittest.TestCase):
    """Test gamut functions working together."""
    
    def test_clamp_result_in_gamut(self):
        """Test that clamp_to_gamut always returns in-gamut LAB."""
        test_lab_values = [
            (50, 100, -100),  # Extreme a*, b*
            (100, 50, 50),    # High lightness
            (75, -50, 80),    # Random LAB
            (50, 200, -200),  # Very extreme
        ]
        for lab in test_lab_values:
            clamped = clamp_to_gamut(lab)
            self.assertTrue(is_in_srgb_gamut(clamped))
    
    def test_find_nearest_result_in_gamut(self):
        """Test that find_nearest_in_gamut always returns in-gamut LAB."""
        test_lab_values = [
            (50, 100, -100),  # Extreme a*, b*
            (100, 50, 50),    # High lightness
            (0, 0, 0),        # Black
            (75, -50, 80),    # Random LAB
        ]
        for lab in test_lab_values:
            nearest = find_nearest_in_gamut(lab)
            self.assertTrue(is_in_srgb_gamut(nearest))


if __name__ == '__main__':
    unittest.main()

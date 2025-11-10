"""Unit tests for color_tools.constants module."""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from color_tools.constants import ColorConstants


class TestColorConstants(unittest.TestCase):
    """Test ColorConstants class."""
    
    def test_d65_white_point(self):
        """Test D65 white point values are set."""
        self.assertIsNotNone(ColorConstants.D65_WHITE_X)
        self.assertIsNotNone(ColorConstants.D65_WHITE_Y)
        self.assertIsNotNone(ColorConstants.D65_WHITE_Z)
        # D65 white point should be close to (0.95, 1.0, 1.09) in 0-1 scale when divided by 100
        self.assertAlmostEqual(ColorConstants.D65_WHITE_X, 95.047, delta=1)
        self.assertAlmostEqual(ColorConstants.D65_WHITE_Y, 100.0, delta=1)
        self.assertAlmostEqual(ColorConstants.D65_WHITE_Z, 108.883, delta=1)
    
    def test_rgb_to_xyz_matrix_components(self):
        """Test RGB to XYZ transformation matrix components exist."""
        # Stored as separate vectors
        self.assertIsNotNone(ColorConstants.SRGB_TO_XYZ_R)
        self.assertIsNotNone(ColorConstants.SRGB_TO_XYZ_G)
        self.assertIsNotNone(ColorConstants.SRGB_TO_XYZ_B)
        # Each should have 3 values
        self.assertEqual(len(ColorConstants.SRGB_TO_XYZ_R), 3)
        self.assertEqual(len(ColorConstants.SRGB_TO_XYZ_G), 3)
        self.assertEqual(len(ColorConstants.SRGB_TO_XYZ_B), 3)
    
    def test_xyz_to_rgb_matrix_components(self):
        """Test XYZ to RGB transformation matrix components exist."""
        # Stored as separate vectors
        self.assertIsNotNone(ColorConstants.XYZ_TO_SRGB_X)
        self.assertIsNotNone(ColorConstants.XYZ_TO_SRGB_Y)
        self.assertIsNotNone(ColorConstants.XYZ_TO_SRGB_Z)
        # Each should have 3 values
        self.assertEqual(len(ColorConstants.XYZ_TO_SRGB_X), 3)
        self.assertEqual(len(ColorConstants.XYZ_TO_SRGB_Y), 3)
        self.assertEqual(len(ColorConstants.XYZ_TO_SRGB_Z), 3)
    
    def test_gamma_values(self):
        """Test gamma correction values."""
        self.assertIsNotNone(ColorConstants.SRGB_GAMMA_POWER)
        self.assertIsNotNone(ColorConstants.SRGB_GAMMA_THRESHOLD)
        self.assertIsNotNone(ColorConstants.SRGB_GAMMA_LINEAR_SCALE)
        # Standard sRGB gamma power is 2.4
        self.assertAlmostEqual(ColorConstants.SRGB_GAMMA_POWER, 2.4, places=1)
    
    def test_lab_constants(self):
        """Test LAB color space constants."""
        # CIE LAB constants
        self.assertIsNotNone(ColorConstants.LAB_KAPPA)
        self.assertIsNotNone(ColorConstants.LAB_DELTA)
        # Just verify they have reasonable values
        self.assertGreater(ColorConstants.LAB_KAPPA, 0)
        self.assertGreater(ColorConstants.LAB_DELTA, 0)
    
    def test_delta_e_constants(self):
        """Test Delta E formula constants."""
        # Delta E 94 constants
        self.assertIsNotNone(ColorConstants.DE94_K1)
        self.assertIsNotNone(ColorConstants.DE94_K2)
        
        # Delta E 2000 constants
        self.assertIsNotNone(ColorConstants.DE2000_L_WEIGHT)
        self.assertIsNotNone(ColorConstants.DE2000_C_WEIGHT)
        self.assertIsNotNone(ColorConstants.DE2000_H_WEIGHT)
    
    def test_hue_circle_degrees(self):
        """Test hue circle constant."""
        self.assertEqual(ColorConstants.HUE_CIRCLE_DEGREES, 360.0)
        self.assertEqual(ColorConstants.HUE_HALF_CIRCLE_DEGREES, 180.0)
    
    def test_normalized_max(self):
        """Test normalized max constant."""
        self.assertEqual(ColorConstants.NORMALIZED_MAX, 1.0)
    
    def test_json_filenames(self):
        """Test JSON filename constants."""
        self.assertEqual(ColorConstants.COLORS_JSON_FILENAME, "colors.json")
        self.assertEqual(ColorConstants.FILAMENTS_JSON_FILENAME, "filaments.json")
        self.assertEqual(ColorConstants.MAKER_SYNONYMS_JSON_FILENAME, "maker_synonyms.json")
    
    def test_user_json_filenames(self):
        """Test user JSON filename constants."""
        self.assertEqual(ColorConstants.USER_COLORS_JSON_FILENAME, "user-colors.json")
        self.assertEqual(ColorConstants.USER_FILAMENTS_JSON_FILENAME, "user-filaments.json")
        self.assertEqual(ColorConstants.USER_SYNONYMS_JSON_FILENAME, "user-synonyms.json")


class TestConstantsImmutability(unittest.TestCase):
    """Test that constants are truly constant (class-level, not instance)."""
    
    def test_constants_are_class_attributes(self):
        """Test that constants are accessed from class, not instance."""
        # Should be able to access without instance
        d65_x = ColorConstants.D65_WHITE_X
        self.assertIsNotNone(d65_x)
    
    def test_cannot_create_instance(self):
        """Test that ColorConstants cannot be instantiated."""
        # This is a class with only class attributes, no __init__
        # Creating instance should work but serves no purpose
        instance = ColorConstants()
        # Class attributes should still be accessible
        self.assertIsNotNone(instance.D65_WHITE_X)
        # But they're the same as class attributes
        self.assertEqual(instance.D65_WHITE_X, ColorConstants.D65_WHITE_X)


class TestConstantsIntegrity(unittest.TestCase):
    """Test mathematical relationships between constants."""
    
    def test_d65_normalization(self):
        """Test D65 white point Y value."""
        # Y value of D65 should be 100 (normalized)
        self.assertAlmostEqual(ColorConstants.D65_WHITE_Y, 100.0, places=2)


class TestHashVerification(unittest.TestCase):
    """Test hash-based integrity verification."""
    
    def test_constants_integrity(self):
        """Test that ColorConstants haven't been tampered with."""
        self.assertTrue(ColorConstants.verify_integrity())
    
    def test_matrices_integrity(self):
        """Test that transformation matrices haven't been tampered with."""
        self.assertTrue(ColorConstants.verify_matrices_integrity())
    
    def test_matrices_hash_generation(self):
        """Test that matrices hash can be computed."""
        hash_value = ColorConstants._compute_matrices_hash()
        self.assertIsInstance(hash_value, str)
        self.assertEqual(len(hash_value), 64)  # SHA-256 produces 64 hex chars
    
    def test_matrices_hash_matches_expected(self):
        """Test that computed hash matches stored hash."""
        computed = ColorConstants._compute_matrices_hash()
        expected = ColorConstants.MATRICES_EXPECTED_HASH
        self.assertEqual(computed, expected)


if __name__ == '__main__':
    unittest.main()

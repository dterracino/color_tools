"""Unit tests for color_tools.distance module."""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from color_tools.distance import (
    delta_e_76,
    delta_e_94,
    delta_e_2000,
    delta_e_cmc,
    euclidean,
    hsl_euclidean,
)


class TestDeltaE76(unittest.TestCase):
    """Test CIE76 Delta E (simple Euclidean distance in LAB)."""
    
    def test_identical_colors(self):
        """Test that identical colors have zero distance."""
        lab1 = (50, 25, -30)
        lab2 = (50, 25, -30)
        distance = delta_e_76(lab1, lab2)
        self.assertAlmostEqual(distance, 0.0, places=5)
    
    def test_known_distance(self):
        """Test known distance calculation."""
        # Simple case: difference only in L*
        lab1 = (50, 0, 0)
        lab2 = (60, 0, 0)
        distance = delta_e_76(lab1, lab2)
        self.assertAlmostEqual(distance, 10.0, places=1)
    
    def test_3d_distance(self):
        """Test 3D distance calculation."""
        lab1 = (50, 25, 30)
        lab2 = (55, 20, 25)
        # Manual calculation: sqrt((55-50)^2 + (20-25)^2 + (25-30)^2)
        # = sqrt(25 + 25 + 25) = sqrt(75) ≈ 8.66
        distance = delta_e_76(lab1, lab2)
        self.assertAlmostEqual(distance, 8.66, places=1)
    
    def test_symmetry(self):
        """Test that distance is symmetric."""
        lab1 = (50, 25, -30)
        lab2 = (55, 20, -25)
        distance1 = delta_e_76(lab1, lab2)
        distance2 = delta_e_76(lab2, lab1)
        self.assertAlmostEqual(distance1, distance2, places=5)


class TestDeltaE94(unittest.TestCase):
    """Test CIE94 Delta E formula."""
    
    def test_identical_colors(self):
        """Test that identical colors have zero distance."""
        lab1 = (50, 25, -30)
        lab2 = (50, 25, -30)
        distance = delta_e_94(lab1, lab2)
        self.assertAlmostEqual(distance, 0.0, places=5)
    
    def test_graphic_arts_default(self):
        """Test with default parameters (graphic arts)."""
        lab1 = (50, 25, 30)
        lab2 = (55, 20, 25)
        # Graphic arts: kL=1, kC=1, kH=1
        distance = delta_e_94(lab1, lab2, kL=1, kC=1, kH=1)
        self.assertGreater(distance, 0)
    
    def test_textiles_application(self):
        """Test textiles application parameters (kL=2)."""
        lab1 = (50, 25, 30)
        lab2 = (55, 20, 25)
        # Textiles: kL=2, kC=1, kH=1
        distance = delta_e_94(lab1, lab2, kL=2, kC=1, kH=1)
        self.assertGreater(distance, 0)
    
    def test_asymmetric_formula(self):
        """Test that delta_e_94 is asymmetric (uses reference color)."""
        lab1 = (50, 25, -30)
        lab2 = (55, 20, -25)
        distance1 = delta_e_94(lab1, lab2)
        distance2 = delta_e_94(lab2, lab1)
        # Delta E 94 is asymmetric - uses first color's chroma in weighting
        # So we just test they're both positive
        self.assertGreater(distance1, 0)
        self.assertGreater(distance2, 0)


class TestDeltaE2000(unittest.TestCase):
    """Test CIEDE2000 Delta E formula (current gold standard)."""
    
    def test_identical_colors(self):
        """Test that identical colors have zero distance."""
        lab1 = (50, 25, -30)
        lab2 = (50, 25, -30)
        distance = delta_e_2000(lab1, lab2)
        self.assertAlmostEqual(distance, 0.0, places=5)
    
    def test_known_reference_case(self):
        """Test with known reference values from literature."""
        # These are reference test cases from the CIEDE2000 paper
        lab1 = (50.0, 2.6772, -79.7751)
        lab2 = (50.0, 0.0, -82.7485)
        distance = delta_e_2000(lab1, lab2)
        # Expected: approximately 2.0425
        self.assertAlmostEqual(distance, 2.04, delta=0.1)
    
    def test_another_reference_case(self):
        """Test another known reference case."""
        lab1 = (50.0, 3.1571, -77.2803)
        lab2 = (50.0, 0.0, -82.7485)
        distance = delta_e_2000(lab1, lab2)
        # Expected: approximately 2.8615
        self.assertAlmostEqual(distance, 2.86, delta=0.1)
    
    def test_symmetry(self):
        """Test that distance is symmetric."""
        lab1 = (50, 25, -30)
        lab2 = (55, 20, -25)
        distance1 = delta_e_2000(lab1, lab2)
        distance2 = delta_e_2000(lab2, lab1)
        self.assertAlmostEqual(distance1, distance2, places=5)


class TestDeltaECMC(unittest.TestCase):
    """Test CMC l:c Delta E formula (textile industry standard)."""
    
    def test_identical_colors(self):
        """Test that identical colors have zero distance."""
        lab1 = (50, 25, -30)
        lab2 = (50, 25, -30)
        distance = delta_e_cmc(lab1, lab2)
        self.assertAlmostEqual(distance, 0.0, places=5)
    
    def test_default_ratio(self):
        """Test default 2:1 ratio (perceptibility)."""
        lab1 = (50, 25, 30)
        lab2 = (55, 20, 25)
        distance = delta_e_cmc(lab1, lab2, l=2, c=1)
        self.assertGreater(distance, 0)
    
    def test_acceptability_ratio(self):
        """Test 1:1 ratio (acceptability)."""
        lab1 = (50, 25, 30)
        lab2 = (55, 20, 25)
        distance = delta_e_cmc(lab1, lab2, l=1, c=1)
        self.assertGreater(distance, 0)
    
    def test_asymmetric_formula(self):
        """Test that CMC is asymmetric (uses reference color)."""
        lab1 = (50, 25, -30)
        lab2 = (55, 20, -25)
        distance1 = delta_e_cmc(lab1, lab2)
        distance2 = delta_e_cmc(lab2, lab1)
        # Delta E CMC is asymmetric - uses first color in weighting
        # So we just test they're both positive
        self.assertGreater(distance1, 0)
        self.assertGreater(distance2, 0)


class TestEuclideanDistance(unittest.TestCase):
    """Test simple Euclidean distance in RGB space."""
    
    def test_identical_colors(self):
        """Test that identical colors have zero distance."""
        rgb1 = (255, 128, 64)
        rgb2 = (255, 128, 64)
        distance = euclidean(rgb1, rgb2)
        self.assertAlmostEqual(distance, 0.0, places=5)
    
    def test_known_distance(self):
        """Test known distance calculation."""
        rgb1 = (0, 0, 0)
        rgb2 = (255, 0, 0)
        distance = euclidean(rgb1, rgb2)
        self.assertAlmostEqual(distance, 255.0, places=1)
    
    def test_3d_distance(self):
        """Test 3D distance in RGB space."""
        rgb1 = (100, 150, 200)
        rgb2 = (110, 160, 210)
        # sqrt(10^2 + 10^2 + 10^2) = sqrt(300) ≈ 17.32
        distance = euclidean(rgb1, rgb2)
        self.assertAlmostEqual(distance, 17.32, places=1)
    
    def test_symmetry(self):
        """Test that distance is symmetric."""
        rgb1 = (100, 150, 200)
        rgb2 = (110, 160, 210)
        distance1 = euclidean(rgb1, rgb2)
        distance2 = euclidean(rgb2, rgb1)
        self.assertAlmostEqual(distance1, distance2, places=5)


class TestHSLEuclideanDistance(unittest.TestCase):
    """Test Euclidean distance in HSL space with hue wraparound."""
    
    def test_identical_colors(self):
        """Test that identical colors have zero distance."""
        hsl1 = (180, 50, 50)
        hsl2 = (180, 50, 50)
        distance = hsl_euclidean(hsl1, hsl2)
        self.assertAlmostEqual(distance, 0.0, places=5)
    
    def test_hue_wraparound(self):
        """Test that hue wraps around correctly (0 and 360 are adjacent)."""
        hsl1 = (0, 50, 50)
        hsl2 = (359, 50, 50)
        distance = hsl_euclidean(hsl1, hsl2)
        # Hue difference should be 1, not 359
        self.assertLess(distance, 10)
    
    def test_opposite_hues(self):
        """Test distance for opposite hues."""
        hsl1 = (0, 50, 50)
        hsl2 = (180, 50, 50)
        distance = hsl_euclidean(hsl1, hsl2)
        # Hue difference is 180, max possible
        self.assertGreater(distance, 100)
    
    def test_symmetry(self):
        """Test that distance is symmetric."""
        hsl1 = (45, 60, 70)
        hsl2 = (90, 50, 60)
        distance1 = hsl_euclidean(hsl1, hsl2)
        distance2 = hsl_euclidean(hsl2, hsl1)
        self.assertAlmostEqual(distance1, distance2, places=5)


class TestDistanceComparisons(unittest.TestCase):
    """Test comparisons between different distance metrics."""
    
    def test_all_metrics_zero_for_identical(self):
        """Test all metrics return 0 for identical colors."""
        lab = (50, 25, -30)
        rgb = (128, 64, 192)
        hsl = (270, 50, 50)
        
        self.assertAlmostEqual(delta_e_76(lab, lab), 0.0, places=5)
        self.assertAlmostEqual(delta_e_94(lab, lab), 0.0, places=5)
        self.assertAlmostEqual(delta_e_2000(lab, lab), 0.0, places=5)
        self.assertAlmostEqual(delta_e_cmc(lab, lab), 0.0, places=5)
        self.assertAlmostEqual(euclidean(rgb, rgb), 0.0, places=5)
        self.assertAlmostEqual(hsl_euclidean(hsl, hsl), 0.0, places=5)
    
    def test_all_metrics_positive_for_different(self):
        """Test all metrics return positive values for different colors."""
        lab1 = (50, 25, -30)
        lab2 = (55, 20, -25)
        rgb1 = (128, 64, 192)
        rgb2 = (140, 70, 200)
        hsl1 = (270, 50, 50)
        hsl2 = (280, 55, 55)
        
        self.assertGreater(delta_e_76(lab1, lab2), 0)
        self.assertGreater(delta_e_94(lab1, lab2), 0)
        self.assertGreater(delta_e_2000(lab1, lab2), 0)
        self.assertGreater(delta_e_cmc(lab1, lab2), 0)
        self.assertGreater(euclidean(rgb1, rgb2), 0)
        self.assertGreater(hsl_euclidean(hsl1, hsl2), 0)


if __name__ == '__main__':
    unittest.main()

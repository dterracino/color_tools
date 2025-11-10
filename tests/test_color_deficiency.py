"""
Unit tests for color vision deficiency simulation and correction.

Tests the color_deficiency and matrices modules.
"""

from __future__ import annotations
import unittest
from color_tools.color_deficiency import (
    simulate_cvd,
    simulate_protanopia,
    simulate_deuteranopia,
    simulate_tritanopia,
    correct_cvd,
    correct_protanopia,
    correct_deuteranopia,
    correct_tritanopia
)
from color_tools.matrices import (
    multiply_matrix_vector,
    get_simulation_matrix,
    get_correction_matrix,
    PROTANOPIA_SIMULATION,
    DEUTERANOPIA_SIMULATION,
    TRITANOPIA_SIMULATION,
    PROTANOPIA_CORRECTION,
    DEUTERANOPIA_CORRECTION,
    TRITANOPIA_CORRECTION
)


class TestMatrixUtilities(unittest.TestCase):
    """Test matrix utility functions."""
    
    def test_multiply_identity_matrix(self):
        """Test multiplication by identity matrix returns same vector."""
        identity = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
        vector = (0.5, 0.3, 0.8)
        result = multiply_matrix_vector(identity, vector)
        self.assertAlmostEqual(result[0], 0.5, places=5)
        self.assertAlmostEqual(result[1], 0.3, places=5)
        self.assertAlmostEqual(result[2], 0.8, places=5)
    
    def test_multiply_zero_matrix(self):
        """Test multiplication by zero matrix returns zero vector."""
        zero = ((0, 0, 0), (0, 0, 0), (0, 0, 0))
        vector = (1.0, 1.0, 1.0)
        result = multiply_matrix_vector(zero, vector)
        self.assertAlmostEqual(result[0], 0.0, places=5)
        self.assertAlmostEqual(result[1], 0.0, places=5)
        self.assertAlmostEqual(result[2], 0.0, places=5)
    
    def test_get_simulation_matrix_protanopia(self):
        """Test getting protanopia simulation matrix."""
        matrix = get_simulation_matrix('protanopia')
        self.assertEqual(matrix, PROTANOPIA_SIMULATION)
        
        # Test alternate name
        matrix_alt = get_simulation_matrix('protan')
        self.assertEqual(matrix_alt, PROTANOPIA_SIMULATION)
    
    def test_get_simulation_matrix_deuteranopia(self):
        """Test getting deuteranopia simulation matrix."""
        matrix = get_simulation_matrix('deuteranopia')
        self.assertEqual(matrix, DEUTERANOPIA_SIMULATION)
        
        matrix_alt = get_simulation_matrix('deutan')
        self.assertEqual(matrix_alt, DEUTERANOPIA_SIMULATION)
    
    def test_get_simulation_matrix_tritanopia(self):
        """Test getting tritanopia simulation matrix."""
        matrix = get_simulation_matrix('tritanopia')
        self.assertEqual(matrix, TRITANOPIA_SIMULATION)
        
        matrix_alt = get_simulation_matrix('tritan')
        self.assertEqual(matrix_alt, TRITANOPIA_SIMULATION)
    
    def test_get_simulation_matrix_invalid(self):
        """Test getting simulation matrix with invalid type raises error."""
        with self.assertRaises(ValueError):
            get_simulation_matrix('invalid')
    
    def test_get_correction_matrix_protanopia(self):
        """Test getting protanopia correction matrix."""
        matrix = get_correction_matrix('protanopia')
        self.assertEqual(matrix, PROTANOPIA_CORRECTION)
        
        matrix_alt = get_correction_matrix('protan')
        self.assertEqual(matrix_alt, PROTANOPIA_CORRECTION)
    
    def test_get_correction_matrix_deuteranopia(self):
        """Test getting deuteranopia correction matrix."""
        matrix = get_correction_matrix('deuteranopia')
        self.assertEqual(matrix, DEUTERANOPIA_CORRECTION)
        
        matrix_alt = get_correction_matrix('deutan')
        self.assertEqual(matrix_alt, DEUTERANOPIA_CORRECTION)
    
    def test_get_correction_matrix_tritanopia(self):
        """Test getting tritanopia correction matrix."""
        matrix = get_correction_matrix('tritanopia')
        self.assertEqual(matrix, TRITANOPIA_CORRECTION)
        
        matrix_alt = get_correction_matrix('tritan')
        self.assertEqual(matrix_alt, TRITANOPIA_CORRECTION)
    
    def test_get_correction_matrix_invalid(self):
        """Test getting correction matrix with invalid type raises error."""
        with self.assertRaises(ValueError):
            get_correction_matrix('invalid')


class TestProtanopiaSimulation(unittest.TestCase):
    """Test protanopia (red-blind) simulation."""
    
    def test_simulate_pure_red(self):
        """Test simulating pure red for protanopia."""
        result = simulate_protanopia((255, 0, 0))
        # Red should appear darker, yellowish-brown
        self.assertLess(result[0], 200)  # Red channel reduced
        self.assertGreater(result[1], 50)  # Green channel present
        self.assertEqual(result[2], 0)  # Blue channel zero
    
    def test_simulate_pure_green(self):
        """Test simulating pure green for protanopia."""
        result = simulate_protanopia((0, 255, 0))
        # Green should shift but remain visible
        self.assertGreater(result[0], 0)  # Some red added
        self.assertGreater(result[1], 100)  # Green still dominant
        self.assertGreater(result[2], 0)  # Some blue added from transformation
    
    def test_simulate_pure_blue(self):
        """Test simulating pure blue for protanopia."""
        result = simulate_protanopia((0, 0, 255))
        # Blue should remain mostly blue
        self.assertEqual(result[0], 0)  # No red
        self.assertEqual(result[1], 0)  # Blue channel preserved, no green
        self.assertGreater(result[2], 150)  # Blue mostly preserved
    
    def test_simulate_black(self):
        """Test simulating black for protanopia."""
        result = simulate_protanopia((0, 0, 0))
        self.assertEqual(result, (0, 0, 0))
    
    def test_simulate_white(self):
        """Test simulating white for protanopia."""
        result = simulate_protanopia((255, 255, 255))
        # White should remain close to white
        self.assertGreater(result[0], 200)
        self.assertGreater(result[1], 200)
        self.assertGreater(result[2], 150)
    
    def test_simulate_via_generic_function(self):
        """Test using generic simulate_cvd function."""
        result1 = simulate_protanopia((255, 0, 0))
        result2 = simulate_cvd((255, 0, 0), 'protanopia')
        self.assertEqual(result1, result2)


class TestDeuteranopiaSimulation(unittest.TestCase):
    """Test deuteranopia (green-blind) simulation."""
    
    def test_simulate_pure_red(self):
        """Test simulating pure red for deuteranopia."""
        result = simulate_deuteranopia((255, 0, 0))
        # Red should shift yellowish
        self.assertGreater(result[0], 150)  # Red channel high
        self.assertGreater(result[1], 50)  # Green channel added
        self.assertEqual(result[2], 0)  # Blue channel zero
    
    def test_simulate_pure_green(self):
        """Test simulating pure green for deuteranopia."""
        result = simulate_deuteranopia((0, 255, 0))
        # Green appears yellowish/grayish
        self.assertGreater(result[0], 50)  # Some red added
        self.assertGreater(result[1], 50)  # Green reduced
        self.assertGreater(result[2], 0)  # Some blue added from transformation
    
    def test_simulate_pure_blue(self):
        """Test simulating pure blue for deuteranopia."""
        result = simulate_deuteranopia((0, 0, 255))
        # Blue should remain mostly blue
        self.assertEqual(result[0], 0)  # No red
        self.assertEqual(result[1], 0)  # Blue channel preserved, no green
        self.assertGreater(result[2], 150)  # Blue dominant
    
    def test_simulate_black(self):
        """Test simulating black for deuteranopia."""
        result = simulate_deuteranopia((0, 0, 0))
        self.assertEqual(result, (0, 0, 0))
    
    def test_simulate_white(self):
        """Test simulating white for deuteranopia."""
        result = simulate_deuteranopia((255, 255, 255))
        # White should remain close to white
        self.assertGreater(result[0], 200)
        self.assertGreater(result[1], 200)
        self.assertGreater(result[2], 150)
    
    def test_simulate_via_generic_function(self):
        """Test using generic simulate_cvd function."""
        result1 = simulate_deuteranopia((0, 255, 0))
        result2 = simulate_cvd((0, 255, 0), 'deuteranopia')
        self.assertEqual(result1, result2)


class TestTritanopiaSimulation(unittest.TestCase):
    """Test tritanopia (blue-blind) simulation."""
    
    def test_simulate_pure_red(self):
        """Test simulating pure red for tritanopia."""
        result = simulate_tritanopia((255, 0, 0))
        # Red should remain mostly red
        self.assertGreater(result[0], 200)  # Red dominant
        self.assertLess(result[1], 50)  # Little green
        self.assertEqual(result[2], 0)  # No blue
    
    def test_simulate_pure_green(self):
        """Test simulating pure green for tritanopia."""
        result = simulate_tritanopia((0, 255, 0))
        # Green shifts toward cyan/teal
        self.assertGreaterEqual(result[0], 0)  # Minimal red (may be small amount)
        self.assertGreater(result[1], 100)  # Green reduced
        self.assertGreater(result[2], 100)  # Blue added
    
    def test_simulate_pure_blue(self):
        """Test simulating pure blue for tritanopia."""
        result = simulate_tritanopia((0, 0, 255))
        # Blue appears cyan/turquoise
        self.assertEqual(result[0], 0)  # No red
        self.assertGreater(result[1], 100)  # Green added
        self.assertGreater(result[2], 100)  # Blue reduced
    
    def test_simulate_black(self):
        """Test simulating black for tritanopia."""
        result = simulate_tritanopia((0, 0, 0))
        self.assertEqual(result, (0, 0, 0))
    
    def test_simulate_white(self):
        """Test simulating white for tritanopia."""
        result = simulate_tritanopia((255, 255, 255))
        # White should remain close to white
        self.assertGreater(result[0], 200)
        self.assertGreater(result[1], 200)
        self.assertGreater(result[2], 100)
    
    def test_simulate_via_generic_function(self):
        """Test using generic simulate_cvd function."""
        result1 = simulate_tritanopia((0, 0, 255))
        result2 = simulate_cvd((0, 0, 255), 'tritanopia')
        self.assertEqual(result1, result2)


class TestProtanopiaCorrection(unittest.TestCase):
    """Test protanopia (red-blind) correction."""
    
    def test_correct_pure_red(self):
        """Test correcting pure red for protanopia."""
        result = correct_protanopia((255, 0, 0))
        # Should shift to be more distinguishable
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        # All values should be in valid range
        for val in result:
            self.assertGreaterEqual(val, 0)
            self.assertLessEqual(val, 255)
    
    def test_correct_pure_green(self):
        """Test correcting pure green for protanopia."""
        result = correct_protanopia((0, 255, 0))
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        for val in result:
            self.assertGreaterEqual(val, 0)
            self.assertLessEqual(val, 255)
    
    def test_correct_black(self):
        """Test correcting black for protanopia."""
        result = correct_protanopia((0, 0, 0))
        self.assertEqual(result, (0, 0, 0))
    
    def test_correct_via_generic_function(self):
        """Test using generic correct_cvd function."""
        result1 = correct_protanopia((255, 0, 0))
        result2 = correct_cvd((255, 0, 0), 'protanopia')
        self.assertEqual(result1, result2)


class TestDeuteranopiaCorrection(unittest.TestCase):
    """Test deuteranopia (green-blind) correction."""
    
    def test_correct_pure_red(self):
        """Test correcting pure red for deuteranopia."""
        result = correct_deuteranopia((255, 0, 0))
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        for val in result:
            self.assertGreaterEqual(val, 0)
            self.assertLessEqual(val, 255)
    
    def test_correct_pure_green(self):
        """Test correcting pure green for deuteranopia."""
        result = correct_deuteranopia((0, 255, 0))
        # Green correction should shift significantly
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        for val in result:
            self.assertGreaterEqual(val, 0)
            self.assertLessEqual(val, 255)
    
    def test_correct_black(self):
        """Test correcting black for deuteranopia."""
        result = correct_deuteranopia((0, 0, 0))
        self.assertEqual(result, (0, 0, 0))
    
    def test_correct_via_generic_function(self):
        """Test using generic correct_cvd function."""
        result1 = correct_deuteranopia((0, 255, 0))
        result2 = correct_cvd((0, 255, 0), 'deuteranopia')
        self.assertEqual(result1, result2)


class TestTritanopiaCorrection(unittest.TestCase):
    """Test tritanopia (blue-blind) correction."""
    
    def test_correct_pure_blue(self):
        """Test correcting pure blue for tritanopia."""
        result = correct_tritanopia((0, 0, 255))
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        for val in result:
            self.assertGreaterEqual(val, 0)
            self.assertLessEqual(val, 255)
    
    def test_correct_pure_yellow(self):
        """Test correcting yellow for tritanopia."""
        result = correct_tritanopia((255, 255, 0))
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        for val in result:
            self.assertGreaterEqual(val, 0)
            self.assertLessEqual(val, 255)
    
    def test_correct_black(self):
        """Test correcting black for tritanopia."""
        result = correct_tritanopia((0, 0, 0))
        self.assertEqual(result, (0, 0, 0))
    
    def test_correct_via_generic_function(self):
        """Test using generic correct_cvd function."""
        result1 = correct_tritanopia((0, 0, 255))
        result2 = correct_cvd((0, 0, 255), 'tritanopia')
        self.assertEqual(result1, result2)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def test_invalid_deficiency_type_simulation(self):
        """Test that invalid deficiency type raises ValueError."""
        with self.assertRaises(ValueError):
            simulate_cvd((255, 0, 0), 'invalid_type')
    
    def test_invalid_deficiency_type_correction(self):
        """Test that invalid deficiency type raises ValueError."""
        with self.assertRaises(ValueError):
            correct_cvd((255, 0, 0), 'invalid_type')
    
    def test_case_insensitive_deficiency_names(self):
        """Test that deficiency names are case-insensitive."""
        result1 = simulate_cvd((255, 0, 0), 'PROTANOPIA')
        result2 = simulate_cvd((255, 0, 0), 'protanopia')
        result3 = simulate_cvd((255, 0, 0), 'Protanopia')
        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)
    
    def test_boundary_values(self):
        """Test with boundary RGB values."""
        # Min values
        result = simulate_protanopia((0, 0, 0))
        self.assertEqual(result, (0, 0, 0))
        
        # Max values
        result = simulate_protanopia((255, 255, 255))
        for val in result:
            self.assertGreaterEqual(val, 0)
            self.assertLessEqual(val, 255)
    
    def test_output_range_clamping(self):
        """Test that outputs are always clamped to 0-255."""
        # Test various colors to ensure no overflow/underflow
        test_colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (128, 128, 128),
            (255, 255, 0),
            (255, 0, 255),
            (0, 255, 255)
        ]
        
        for color in test_colors:
            for func in [simulate_protanopia, simulate_deuteranopia, simulate_tritanopia,
                        correct_protanopia, correct_deuteranopia, correct_tritanopia]:
                result = func(color)
                for val in result:
                    self.assertGreaterEqual(val, 0, f"Negative value in {func.__name__}({color})")
                    self.assertLessEqual(val, 255, f"Value > 255 in {func.__name__}({color})")


class TestConsistency(unittest.TestCase):
    """Test consistency and determinism of transformations."""
    
    def test_simulation_is_deterministic(self):
        """Test that simulation produces consistent results."""
        color = (128, 64, 192)
        result1 = simulate_protanopia(color)
        result2 = simulate_protanopia(color)
        self.assertEqual(result1, result2)
    
    def test_correction_is_deterministic(self):
        """Test that correction produces consistent results."""
        color = (128, 64, 192)
        result1 = correct_deuteranopia(color)
        result2 = correct_deuteranopia(color)
        self.assertEqual(result1, result2)
    
    def test_different_deficiencies_produce_different_results(self):
        """Test that different deficiency types produce different results."""
        color = (255, 128, 64)
        
        protan = simulate_protanopia(color)
        deutan = simulate_deuteranopia(color)
        tritan = simulate_tritanopia(color)
        
        # They should all be different
        self.assertNotEqual(protan, deutan)
        self.assertNotEqual(deutan, tritan)
        self.assertNotEqual(protan, tritan)


if __name__ == '__main__':
    unittest.main()

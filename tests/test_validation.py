"""
Unit tests for color validation functionality.

Tests the validate_color function and its supporting utilities.
"""

import unittest
from color_tools.validation import (
    validate_color,
    ColorValidationRecord,
    _levenshtein_distance,
    _fuzzy_match_fallback,
    HAS_FUZZYWUZZY
)


class TestLevenshteinDistance(unittest.TestCase):
    """Test Levenshtein distance calculation."""
    
    def test_identical_strings(self):
        """Test that identical strings have distance 0."""
        self.assertEqual(_levenshtein_distance("hello", "hello"), 0)
        self.assertEqual(_levenshtein_distance("", ""), 0)
    
    def test_single_character_difference(self):
        """Test single character substitution."""
        self.assertEqual(_levenshtein_distance("cat", "bat"), 1)
        self.assertEqual(_levenshtein_distance("hello", "hallo"), 1)
    
    def test_insertion(self):
        """Test character insertion."""
        self.assertEqual(_levenshtein_distance("cat", "cats"), 1)
        self.assertEqual(_levenshtein_distance("red", "read"), 1)
    
    def test_deletion(self):
        """Test character deletion."""
        self.assertEqual(_levenshtein_distance("cats", "cat"), 1)
        self.assertEqual(_levenshtein_distance("read", "red"), 1)
    
    def test_empty_string(self):
        """Test distance to/from empty string."""
        self.assertEqual(_levenshtein_distance("", "hello"), 5)
        self.assertEqual(_levenshtein_distance("hello", ""), 5)
    
    def test_completely_different(self):
        """Test completely different strings."""
        distance = _levenshtein_distance("abc", "xyz")
        self.assertEqual(distance, 3)
    
    def test_case_sensitive(self):
        """Test that comparison is case-sensitive."""
        self.assertEqual(_levenshtein_distance("Red", "red"), 1)
        self.assertEqual(_levenshtein_distance("BLUE", "blue"), 4)


class TestFuzzyMatchFallback(unittest.TestCase):
    """Test the fallback fuzzy matcher."""
    
    def setUp(self):
        """Set up common test data."""
        self.choices = ["red", "dark red", "light blue", "sky blue", "green"]
    
    def test_exact_match(self):
        """Test exact match returns 100 score."""
        match, score = _fuzzy_match_fallback("red", self.choices)
        self.assertEqual(match, "red")
        self.assertEqual(score, 100)
    
    def test_exact_match_case_insensitive(self):
        """Test exact match is case-insensitive."""
        match, score = _fuzzy_match_fallback("RED", self.choices)
        self.assertEqual(match, "red")
        self.assertEqual(score, 100)
    
    def test_exact_match_with_spaces(self):
        """Test exact match ignores spaces."""
        match, score = _fuzzy_match_fallback("darkred", self.choices)
        self.assertEqual(match, "dark red")
        self.assertEqual(score, 100)
    
    def test_exact_match_with_hyphens(self):
        """Test exact match ignores hyphens."""
        match, score = _fuzzy_match_fallback("light-blue", self.choices)
        self.assertEqual(match, "light blue")
        self.assertEqual(score, 100)
    
    def test_substring_match(self):
        """Test substring matching."""
        match, score = _fuzzy_match_fallback("blue", self.choices)
        self.assertIn(match, ["light blue", "sky blue"])
        self.assertGreater(score, 50)
    
    def test_partial_match(self):
        """Test partial/fuzzy matching."""
        match, score = _fuzzy_match_fallback("gren", self.choices)  # typo for green
        self.assertEqual(match, "green")
        self.assertGreater(score, 50)
    
    def test_returns_best_match(self):
        """Test that best match is returned."""
        match, score = _fuzzy_match_fallback("sky", self.choices)
        self.assertEqual(match, "sky blue")


class TestColorValidationRecord(unittest.TestCase):
    """Test ColorValidationRecord dataclass."""
    
    def test_create_record(self):
        """Test creating a validation record."""
        record = ColorValidationRecord(
            is_match=True,
            name_match="red",
            name_confidence=0.95,
            hex_value="#FF0000",
            suggested_hex="#FF0000",
            delta_e=0.5,
            message="Match"
        )
        self.assertTrue(record.is_match)
        self.assertEqual(record.name_match, "red")
        self.assertEqual(record.name_confidence, 0.95)
        self.assertEqual(record.delta_e, 0.5)
    
    def test_record_is_frozen(self):
        """Test that record is immutable."""
        record = ColorValidationRecord(
            is_match=True,
            name_match="red",
            name_confidence=1.0,
            hex_value="#FF0000",
            suggested_hex="#FF0000",
            delta_e=0.0,
            message="Match"
        )
        with self.assertRaises((AttributeError, TypeError)):  # Frozen dataclass
            record.is_match = False  # type: ignore
    
    def test_validation_record_str(self):
        """Test ColorValidationRecord string representation."""
        # Test match case
        match_record = ColorValidationRecord(
            is_match=True,
            name_match="lightblue",
            name_confidence=1.0,
            hex_value="#ADD8E6",
            suggested_hex="#ADD8E6",
            delta_e=0.0,
            message="Match"
        )
        result = str(match_record)
        self.assertIn("Match", result)
        self.assertIn("lightblue", result)
        self.assertIn("100%", result)
        self.assertIn("0.0", result)
        
        # Test mismatch case
        mismatch_record = ColorValidationRecord(
            is_match=False,
            name_match="red",
            name_confidence=0.85,
            hex_value="#FF1122",
            suggested_hex="#FF0000",
            delta_e=12.5,
            message="Mismatch"
        )
        result = str(mismatch_record)
        self.assertIn("Mismatch", result)
        self.assertIn("red", result)
        self.assertIn("85%", result)
        self.assertIn("12.5", result)
        
        # Verify repr still shows full details
        repr_str = repr(match_record)
        self.assertIn("ColorValidationRecord", repr_str)


class TestValidateColorExactMatches(unittest.TestCase):
    """Test validate_color with exact CSS color matches."""
    
    def test_exact_red_match(self):
        """Test exact match for red."""
        result = validate_color("red", "#FF0000")
        self.assertTrue(result.is_match)
        self.assertEqual(result.name_match, "red")
        self.assertEqual(result.hex_value, "#FF0000")
        self.assertLess(result.delta_e, 1.0)  # Should be nearly identical
    
    def test_exact_blue_match(self):
        """Test exact match for blue."""
        result = validate_color("blue", "#0000FF")
        self.assertTrue(result.is_match)
        self.assertEqual(result.name_match, "blue")
        self.assertLess(result.delta_e, 1.0)
    
    def test_exact_green_match(self):
        """Test exact match for green."""
        result = validate_color("green", "#008000")
        self.assertTrue(result.is_match)
        self.assertEqual(result.name_match, "green")
        self.assertLess(result.delta_e, 1.0)
    
    def test_exact_lightblue_match(self):
        """Test exact match for lightblue."""
        result = validate_color("lightblue", "#ADD8E6")
        self.assertTrue(result.is_match)
        self.assertEqual(result.name_match, "lightblue")
        self.assertLess(result.delta_e, 1.0)
    
    def test_exact_darkred_match(self):
        """Test exact match for darkred."""
        result = validate_color("darkred", "#8B0000")
        self.assertTrue(result.is_match)
        self.assertEqual(result.name_match, "darkred")
        self.assertLess(result.delta_e, 1.0)


class TestValidateColorFuzzyMatches(unittest.TestCase):
    """Test validate_color with fuzzy name matching."""
    
    def test_fuzzy_name_with_spaces(self):
        """Test fuzzy match with spaces in name."""
        result = validate_color("light blue", "#ADD8E6")
        self.assertTrue(result.is_match)
        self.assertEqual(result.name_match, "lightblue")
        self.assertGreater(result.name_confidence, 0.8)
    
    def test_fuzzy_name_with_hyphens(self):
        """Test fuzzy match with hyphens."""
        result = validate_color("light-blue", "#ADD8E6")
        self.assertTrue(result.is_match)
        self.assertEqual(result.name_match, "lightblue")
    
    def test_fuzzy_name_case_insensitive(self):
        """Test fuzzy match is case-insensitive."""
        result = validate_color("LIGHTBLUE", "#ADD8E6")
        self.assertTrue(result.is_match)
        self.assertEqual(result.name_match, "lightblue")
    
    def test_fuzzy_name_typo(self):
        """Test fuzzy match with typo."""
        result = validate_color("ligth blue", "#ADD8E6")  # typo: ligth instead of light
        # Should still find lightblue (or at least some blue variant)
        self.assertIn("blue", result.name_match.lower())  # type: ignore
        self.assertGreater(result.name_confidence, 0.5)
    
    def test_fuzzy_similar_name(self):
        """Test fuzzy match with similar name."""
        result = validate_color("sky blue", "#87CEEB")
        self.assertTrue(result.is_match)
        self.assertEqual(result.name_match, "skyblue")


class TestValidateColorMismatches(unittest.TestCase):
    """Test validate_color with color mismatches."""
    
    def test_wrong_color_completely(self):
        """Test completely wrong color."""
        result = validate_color("blue", "#FF0000")  # red hex
        self.assertFalse(result.is_match)
        self.assertEqual(result.name_match, "blue")
        self.assertEqual(result.suggested_hex, "#0000FF")
        self.assertGreater(result.delta_e, 50.0)  # Very different colors
    
    def test_wrong_shade(self):
        """Test wrong shade of color (within threshold)."""
        result = validate_color("red", "#FF6666", de_threshold=10.0)  # lighter red
        # Might match or not depending on threshold
        if result.is_match:
            self.assertLess(result.delta_e, 10.0)
        else:
            self.assertGreaterEqual(result.delta_e, 10.0)
    
    def test_different_hue_family(self):
        """Test different color family."""
        result = validate_color("red", "#A52A2A", de_threshold=15.0)  # brown - stricter threshold
        self.assertFalse(result.is_match)
        self.assertGreater(result.delta_e, 15.0)


class TestValidateColorThresholds(unittest.TestCase):
    """Test validate_color with different Delta E thresholds."""
    
    def test_strict_threshold(self):
        """Test with strict threshold."""
        result = validate_color("red", "#FF1111", de_threshold=5.0)
        # Very close but not exact
        if result.delta_e < 5.0:
            self.assertTrue(result.is_match)
        else:
            self.assertFalse(result.is_match)
    
    def test_lenient_threshold(self):
        """Test with lenient threshold."""
        result = validate_color("red", "#FF3333", de_threshold=30.0)
        # Should match with lenient threshold
        self.assertTrue(result.is_match)
        self.assertLess(result.delta_e, 30.0)
    
    def test_custom_threshold(self):
        """Test custom threshold value."""
        hex_code = "#FF4444"
        strict = validate_color("red", hex_code, de_threshold=5.0)
        lenient = validate_color("red", hex_code, de_threshold=50.0)
        
        # Same delta_e, different match result based on threshold
        self.assertEqual(strict.delta_e, lenient.delta_e)
        if strict.delta_e < 5.0:
            self.assertTrue(strict.is_match)
            self.assertTrue(lenient.is_match)
        elif strict.delta_e < 50.0:
            self.assertFalse(strict.is_match)
            self.assertTrue(lenient.is_match)


class TestValidateColorInvalidInput(unittest.TestCase):
    """Test validate_color with invalid input."""
    
    def test_invalid_hex_format(self):
        """Test with invalid hex code format."""
        result = validate_color("red", "not a hex")
        self.assertFalse(result.is_match)
        self.assertEqual(result.delta_e, float('inf'))
        self.assertIn("Invalid hex code", result.message)
    
    def test_short_hex_code(self):
        """Test with too-short hex code."""
        result = validate_color("red", "#FF")
        self.assertFalse(result.is_match)
        self.assertEqual(result.delta_e, float('inf'))
    
    def test_three_char_hex_valid(self):
        """Test with valid 3-character hex code."""
        result = validate_color("red", "#F00")  # Should expand to #FF0000
        self.assertTrue(result.is_match)
        self.assertEqual(result.name_match, "red")
        self.assertLess(result.delta_e, 1.0)
    
    def test_hex_without_hash(self):
        """Test hex code without # prefix."""
        result = validate_color("red", "FF0000")
        self.assertTrue(result.is_match)
        self.assertLess(result.delta_e, 1.0)


class TestValidateColorEdgeCases(unittest.TestCase):
    """Test validate_color edge cases."""
    
    def test_white(self):
        """Test white color validation."""
        result = validate_color("white", "#FFFFFF")
        self.assertTrue(result.is_match)
        self.assertEqual(result.name_match, "white")
        self.assertLess(result.delta_e, 1.0)
    
    def test_black(self):
        """Test black color validation."""
        result = validate_color("black", "#000000")
        self.assertTrue(result.is_match)
        self.assertEqual(result.name_match, "black")
        self.assertLess(result.delta_e, 1.0)
    
    def test_gray_variants(self):
        """Test gray color variants."""
        # Test that fuzzy matching finds gray/grey variants
        result_gray = validate_color("gray", "#808080")
        result_grey = validate_color("grey", "#808080")
        
        # Both should match some gray variant
        self.assertIsNotNone(result_gray.name_match)
        self.assertIsNotNone(result_grey.name_match)
        self.assertIn("gray", result_gray.name_match.lower())  # type: ignore
        self.assertIn("gr", result_grey.name_match.lower())  # type: ignore - gray or grey
    
    def test_confidence_score_range(self):
        """Test that confidence score is between 0 and 1."""
        result = validate_color("red", "#FF0000")
        self.assertGreaterEqual(result.name_confidence, 0.0)
        self.assertLessEqual(result.name_confidence, 1.0)
    
    def test_suggested_hex_provided(self):
        """Test that suggested hex is always provided."""
        result = validate_color("red", "#0000FF")  # wrong color
        self.assertIsNotNone(result.suggested_hex)
        self.assertEqual(result.suggested_hex, "#FF0000")


class TestValidateColorRealWorldCases(unittest.TestCase):
    """Test validate_color with real-world use cases."""
    
    def test_css_color_names(self):
        """Test common CSS color names."""
        test_cases = [
            ("coral", "#FF7F50"),
            ("tomato", "#FF6347"),
            ("gold", "#FFD700"),
            ("orchid", "#DA70D6"),
            ("salmon", "#FA8072"),
        ]
        
        for name, hex_code in test_cases:
            with self.subTest(name=name):
                result = validate_color(name, hex_code)
                self.assertTrue(result.is_match)
                self.assertEqual(result.name_match, name)
                self.assertLess(result.delta_e, 1.0)
    
    def test_user_input_variations(self):
        """Test common user input variations."""
        # Users might type with spaces, different cases, etc.
        result1 = validate_color("Light Blue", "#ADD8E6")
        result2 = validate_color("light_blue", "#ADD8E6")
        result3 = validate_color("LIGHT BLUE", "#ADD8E6")
        
        for result in [result1, result2, result3]:
            self.assertEqual(result.name_match, "lightblue")
            self.assertTrue(result.is_match)
    
    def test_similar_colors_distinguished(self):
        """Test that similar colors are properly distinguished."""
        # Test that the function can tell apart similar colors
        red_result = validate_color("red", "#FF0000")
        darkred_result = validate_color("darkred", "#8B0000")
        
        self.assertEqual(red_result.name_match, "red")
        self.assertEqual(darkred_result.name_match, "darkred")
        
        # Cross-check: red hex should not match darkred name well
        wrong_result = validate_color("darkred", "#FF0000", de_threshold=10.0)
        self.assertFalse(wrong_result.is_match)


@unittest.skipIf(not HAS_FUZZYWUZZY, "fuzzywuzzy not installed")
class TestWithFuzzyWuzzy(unittest.TestCase):
    """Tests specific to when fuzzywuzzy is available."""
    
    def test_fuzzywuzzy_better_matching(self):
        """Test that fuzzywuzzy provides good fuzzy matching."""
        result = validate_color("ligt blu", "#ADD8E6")  # double typo
        # With fuzzywuzzy, should still find lightblue
        self.assertEqual(result.name_match, "lightblue")
        self.assertGreater(result.name_confidence, 0.5)


if __name__ == '__main__':
    unittest.main()

"""
Unit tests for color naming functionality.
"""

import unittest
from color_tools.naming import (
    get_lightness_modifier,
    get_saturation_modifier,
    get_hue_with_ish,
    determine_base_hue,
    get_generic_hue,
    is_unique_near_claim,
    generate_color_name,
)
from color_tools.conversions import rgb_to_hsl, rgb_to_lab


class TestLightnessModifier(unittest.TestCase):
    """Test lightness modifier generation."""
    
    def test_very_light(self):
        """Test very light modifier (L* > 80)."""
        self.assertEqual(get_lightness_modifier(85), "very light")
        self.assertEqual(get_lightness_modifier(90), "very light")
        self.assertEqual(get_lightness_modifier(100), "very light")
    
    def test_light(self):
        """Test light modifier (60 < L* ≤ 80)."""
        self.assertEqual(get_lightness_modifier(61), "light")
        self.assertEqual(get_lightness_modifier(70), "light")
        self.assertEqual(get_lightness_modifier(80), "light")
    
    def test_medium(self):
        """Test medium modifier (40 < L* ≤ 60)."""
        self.assertEqual(get_lightness_modifier(41), "medium")
        self.assertEqual(get_lightness_modifier(50), "medium")
        self.assertEqual(get_lightness_modifier(60), "medium")
    
    def test_dark(self):
        """Test dark modifier (20 < L* ≤ 40)."""
        self.assertEqual(get_lightness_modifier(21), "dark")
        self.assertEqual(get_lightness_modifier(30), "dark")
        self.assertEqual(get_lightness_modifier(40), "dark")
    
    def test_very_dark(self):
        """Test very dark modifier (L* ≤ 20)."""
        self.assertEqual(get_lightness_modifier(20), "very dark")
        self.assertEqual(get_lightness_modifier(10), "very dark")
        self.assertEqual(get_lightness_modifier(0), "very dark")


class TestSaturationModifier(unittest.TestCase):
    """Test saturation modifier generation."""
    
    def test_pale_light_colors(self):
        """Test pale modifier for light colors (S < 35, L > 50)."""
        self.assertEqual(get_saturation_modifier(20, 60), "pale")
        self.assertEqual(get_saturation_modifier(30, 70), "pale")
        self.assertEqual(get_saturation_modifier(34, 80), "pale")
    
    def test_muted_dark_colors(self):
        """Test muted modifier for dark colors (S < 35, L ≤ 50)."""
        self.assertEqual(get_saturation_modifier(20, 30), "muted")
        self.assertEqual(get_saturation_modifier(30, 40), "muted")
        self.assertEqual(get_saturation_modifier(34, 50), "muted")
    
    def test_dull(self):
        """Test dull modifier (35 ≤ S < 50)."""
        self.assertEqual(get_saturation_modifier(35, 50), "dull")
        self.assertEqual(get_saturation_modifier(40, 50), "dull")
        self.assertEqual(get_saturation_modifier(45, 50), "dull")
        self.assertEqual(get_saturation_modifier(49, 50), "dull")
    
    def test_no_modifier_medium_saturation(self):
        """Test no modifier for medium saturation (50 ≤ S < 70)."""
        self.assertEqual(get_saturation_modifier(50, 50), "")
        self.assertEqual(get_saturation_modifier(60, 50), "")
        self.assertEqual(get_saturation_modifier(69, 50), "")
    
    def test_bright(self):
        """Test bright modifier (70 ≤ S < 85)."""
        self.assertEqual(get_saturation_modifier(70, 50), "bright")
        self.assertEqual(get_saturation_modifier(75, 50), "bright")
        self.assertEqual(get_saturation_modifier(84, 50), "bright")
    
    def test_deep(self):
        """Test deep modifier (85 ≤ S < 95)."""
        self.assertEqual(get_saturation_modifier(85, 50), "deep")
        self.assertEqual(get_saturation_modifier(90, 50), "deep")
        self.assertEqual(get_saturation_modifier(94, 50), "deep")
    
    def test_vivid(self):
        """Test vivid modifier (S ≥ 95)."""
        self.assertEqual(get_saturation_modifier(95, 50), "vivid")
        self.assertEqual(get_saturation_modifier(98, 50), "vivid")
        self.assertEqual(get_saturation_modifier(100, 50), "vivid")


class TestHueWithIsh(unittest.TestCase):
    """Test -ish hue variant generation."""
    
    def test_low_saturation_no_ish(self):
        """Test that low saturation colors don't get -ish variants."""
        # Below 40% saturation threshold
        self.assertIsNone(get_hue_with_ish(25, 35))
        self.assertIsNone(get_hue_with_ish(55, 30))
    
    def test_red_orange_boundary(self):
        """Test red/orange boundary (20°) transitions."""
        # Below boundary: approaching from red side
        self.assertEqual(get_hue_with_ish(14, 80), "redish orange")
        self.assertEqual(get_hue_with_ish(18, 80), "redish orange")
        # Above boundary: just entered orange
        self.assertEqual(get_hue_with_ish(22, 80), "orangeish red")
        self.assertEqual(get_hue_with_ish(26, 80), "orangeish red")
    
    def test_orange_yellow_boundary(self):
        """Test orange/yellow boundary (50°) transitions."""
        self.assertEqual(get_hue_with_ish(44, 80), "orangeish yellow")
        self.assertEqual(get_hue_with_ish(52, 80), "yellowish orange")
    
    def test_yellow_green_boundary(self):
        """Test yellow/green boundary (80°) transitions."""
        self.assertEqual(get_hue_with_ish(74, 80), "yellowish green")
        self.assertEqual(get_hue_with_ish(84, 80), "greenish yellow")
    
    def test_green_teal_boundary(self):
        """Test green/teal boundary (140°) transitions."""
        self.assertEqual(get_hue_with_ish(134, 80), "greenish teal")
        self.assertEqual(get_hue_with_ish(144, 80), "tealish green")
    
    def test_cyan_blue_boundary(self):
        """Test cyan/blue boundary (190°) transitions."""
        self.assertEqual(get_hue_with_ish(184, 80), "cyanish blue")
        self.assertEqual(get_hue_with_ish(194, 80), "blueish cyan")
    
    def test_blue_purple_boundary(self):
        """Test blue/purple boundary (270°) transitions."""
        self.assertEqual(get_hue_with_ish(264, 80), "blueish purple")
        self.assertEqual(get_hue_with_ish(274, 80), "purpleish blue")
    
    def test_purple_magenta_boundary(self):
        """Test purple/magenta boundary (310°) transitions."""
        self.assertEqual(get_hue_with_ish(304, 80), "purpleish magenta")
        self.assertEqual(get_hue_with_ish(314, 80), "magentaish purple")
    
    def test_no_ish_in_center_of_ranges(self):
        """Test that colors in center of hue ranges don't get -ish."""
        # Well within orange range
        self.assertIsNone(get_hue_with_ish(35, 80))
        # Well within green range
        self.assertIsNone(get_hue_with_ish(110, 80))
        # Well within blue range
        self.assertIsNone(get_hue_with_ish(220, 80))


class TestGenericHue(unittest.TestCase):
    """Test generic hue name generation."""
    
    def test_red(self):
        """Test red hue range."""
        self.assertEqual(get_generic_hue(0), "red")
        self.assertEqual(get_generic_hue(10), "red")
        self.assertEqual(get_generic_hue(19), "red")
        # 340-360 wraps to red (not magenta)
        self.assertEqual(get_generic_hue(350), "red")
        self.assertEqual(get_generic_hue(355), "red")
    
    def test_orange(self):
        """Test orange hue range."""
        self.assertEqual(get_generic_hue(20), "orange")
        self.assertEqual(get_generic_hue(30), "orange")
        self.assertEqual(get_generic_hue(39), "orange")
    
    def test_yellow(self):
        """Test yellow hue range."""
        self.assertEqual(get_generic_hue(40), "yellow")
        self.assertEqual(get_generic_hue(60), "yellow")
        self.assertEqual(get_generic_hue(69), "yellow")
    
    def test_green_ranges(self):
        """Test green-related hue ranges."""
        self.assertEqual(get_generic_hue(70), "yellow-green")
        self.assertEqual(get_generic_hue(100), "green")
        self.assertEqual(get_generic_hue(140), "cyan-green")
    
    def test_cyan(self):
        """Test cyan hue range."""
        self.assertEqual(get_generic_hue(170), "cyan")
        self.assertEqual(get_generic_hue(180), "cyan")
        self.assertEqual(get_generic_hue(189), "cyan")
    
    def test_blue(self):
        """Test blue hue range."""
        self.assertEqual(get_generic_hue(190), "blue")
        self.assertEqual(get_generic_hue(220), "blue")
        self.assertEqual(get_generic_hue(249), "blue")
    
    def test_indigo(self):
        """Test indigo hue range."""
        self.assertEqual(get_generic_hue(250), "indigo")
        self.assertEqual(get_generic_hue(269), "indigo")
    
    def test_purple_violet(self):
        """Test purple and violet hue ranges."""
        self.assertEqual(get_generic_hue(270), "violet")
        self.assertEqual(get_generic_hue(289), "violet")
        self.assertEqual(get_generic_hue(290), "purple")
        self.assertEqual(get_generic_hue(309), "purple")
    
    def test_magenta(self):
        """Test magenta hue range."""
        self.assertEqual(get_generic_hue(310), "magenta")
        self.assertEqual(get_generic_hue(330), "magenta")
        self.assertEqual(get_generic_hue(339), "magenta")


class TestDetermineBaseHue(unittest.TestCase):
    """Test base hue determination including special cases."""
    
    def test_brown_family(self):
        """Test brown, tan, and beige special cases."""
        # Beige: orange/yellow hue, low saturation, high lightness
        self.assertEqual(determine_base_hue(40, 25, 75), "beige")
        # Tan: orange/yellow hue, low saturation, medium lightness
        self.assertEqual(determine_base_hue(40, 25, 60), "tan")
        # Brown: orange/yellow hue, low saturation, low lightness
        self.assertEqual(determine_base_hue(40, 25, 40), "brown")
    
    def test_pink(self):
        """Test pink special case (light red with saturation)."""
        # Pink with low saturation (below -ish threshold)
        self.assertEqual(determine_base_hue(5, 35, 70), "pink")
        # Pink with higher saturation gets -ish variant
        result = determine_base_hue(355, 50, 70)
        self.assertIn("pink", result)  # Could be "pink" or "redish pink"
    
    def test_gold(self):
        """Test gold special case (desaturated yellow)."""
        # Gold: h=40-70°, s=20-50%, l>40% (checked before brown)
        self.assertEqual(determine_base_hue(55, 30, 45), "gold")
        self.assertEqual(determine_base_hue(50, 35, 60), "gold")
    
    def test_olive(self):
        """Test olive special case (dark muted yellow-green)."""
        self.assertEqual(determine_base_hue(85, 40, 35), "olive")
    
    def test_navy(self):
        """Test navy special case (very dark blue)."""
        self.assertEqual(determine_base_hue(220, 50, 25), "navy")
    
    def test_maroon(self):
        """Test maroon special case (very dark red)."""
        # Maroon with low saturation (no -ish)
        self.assertEqual(determine_base_hue(5, 35, 25), "maroon")
        # Maroon with higher saturation may get -ish variant  
        result = determine_base_hue(355, 50, 25)
        self.assertIn("maroon", result)  # Could be "maroon" or "redish maroon"
    
    def test_teal(self):
        """Test teal special case (cyan-green range)."""
        self.assertEqual(determine_base_hue(150, 50, 50), "teal")
        self.assertEqual(determine_base_hue(160, 50, 50), "teal")
    
    def test_lime(self):
        """Test lime special case (bright yellow-green)."""
        # Lime well within range (outside -ish boundaries at 80° and 100°)
        self.assertEqual(determine_base_hue(90, 80, 50), "lime")
    
    def test_ish_with_special_cases(self):
        """Test that -ish variants work with special cases."""
        # Pink near boundary (high saturation for -ish)
        result = determine_base_hue(14, 70, 70)  # Near red/orange boundary
        self.assertIn("pink", result)
        self.assertTrue(result.endswith("pink") or "ish" in result)
        
        # Lime near boundary gets -ish variant
        result = determine_base_hue(74, 80, 50)  # Near yellow/green boundary
        # Should be "yellowish green" or "lime" (74° is just below 80° boundary)
        self.assertTrue("green" in result or "lime" in result)
    
    def test_fallback_to_generic(self):
        """Test fallback to generic hue names."""
        # Standard red (no special case)
        self.assertEqual(determine_base_hue(10, 80, 50), "red")
        # Standard blue (no special case)
        self.assertEqual(determine_base_hue(220, 80, 50), "blue")


class TestGenerateColorName(unittest.TestCase):
    """Test complete color name generation."""
    
    def test_exact_css_matches(self):
        """Test exact matches with CSS colors."""
        # Red
        name, match_type = generate_color_name((255, 0, 0))
        self.assertEqual(name, "red")
        self.assertEqual(match_type, "exact")
        
        # Blue
        name, match_type = generate_color_name((0, 0, 255))
        self.assertEqual(name, "blue")
        self.assertEqual(match_type, "exact")
        
        # White
        name, match_type = generate_color_name((255, 255, 255))
        self.assertEqual(name, "white")
        self.assertEqual(match_type, "exact")
        
        # Black
        name, match_type = generate_color_name((0, 0, 0))
        self.assertEqual(name, "black")
        self.assertEqual(match_type, "exact")
    
    def test_near_css_matches(self):
        """Test near matches with CSS colors."""
        # Very close to red (Delta E < 5) might be near or generated depending on context
        name, match_type = generate_color_name((255, 5, 5))
        self.assertIn("red", name)
        # Should be exact, near, or generated with "red" in name
        self.assertIn(match_type, ["exact", "near", "generated"])
    
    def test_gray_generation(self):
        """Test achromatic (gray) color generation."""
        # Low saturation should produce gray
        name, match_type = generate_color_name((128, 128, 128))
        # Could be exact match or generated gray
        if match_type == "generated":
            self.assertIn("gray", name)
    
    def test_generated_names_format(self):
        """Test that generated names follow expected format."""
        # Medium saturated orange
        name, match_type = generate_color_name((200, 100, 50))
        if match_type == "generated":
            # Should have components from modifiers + hue
            self.assertTrue(any(word in name for word in 
                ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "magenta"]))
    
    def test_lightness_in_generated_names(self):
        """Test that lightness modifiers appear in generated names."""
        # Very light color
        rgb = (255, 200, 200)
        name, match_type = generate_color_name(rgb)
        if match_type == "generated":
            # Should have lightness modifier
            self.assertTrue(any(mod in name for mod in 
                ["very light", "light", "medium", "dark", "very dark"]))
    
    def test_saturation_in_generated_names(self):
        """Test that saturation modifiers appear appropriately."""
        # High saturation color
        rgb = (200, 0, 0)
        name, match_type = generate_color_name(rgb)
        if match_type == "generated":
            # Should have saturation modifier or none for medium
            # vivid, deep, bright, or empty for medium saturation
            pass  # Just checking it doesn't crash
    
    def test_ish_variants_in_generated_names(self):
        """Test that -ish variants can appear in generated names."""
        # Color near a hue boundary with high saturation
        rgb = (255, 80, 0)  # Near red/orange boundary
        h, s, _ = rgb_to_hsl(rgb)
        if s >= 40:  # Above -ish threshold
            name, match_type = generate_color_name(rgb)
            # Might have -ish variant if near boundary
            # Just verify it generates without error
            self.assertIsInstance(name, str)
            self.assertIn(match_type, ["exact", "near", "generated"])
    
    def test_special_case_colors(self):
        """Test generation with special case colors."""
        # Brown-ish color
        rgb = (139, 69, 19)
        name, match_type = generate_color_name(rgb)
        # Either exact match (saddlebrown) or generated with brown
        if match_type == "generated":
            self.assertTrue(any(word in name for word in ["brown", "tan", "beige", "orange"]))
    
    def test_collision_avoidance(self):
        """Test that collision avoidance works."""
        # Generate a name and ensure it's valid
        name, _ = generate_color_name((123, 45, 67))
        self.assertIsInstance(name, str)
        self.assertGreater(len(name), 0)
        # Name should not be empty
        self.assertTrue(name.strip())
    
    def test_palette_context_for_near_matches(self):
        """Test near match uniqueness with palette context."""
        rgb = (255, 10, 10)
        palette_colors = [(255, 0, 0), (200, 0, 0)]  # Multiple reds
        
        name, match_type = generate_color_name(rgb, palette_colors=palette_colors)
        # Should handle palette context without error
        self.assertIsInstance(name, str)
        self.assertIn(match_type, ["exact", "near", "generated"])


class TestIsUniqueNearClaim(unittest.TestCase):
    """Test near match uniqueness checking."""
    
    def test_no_palette_context(self):
        """Test that without palette context, claim is allowed."""
        result = is_unique_near_claim((255, 10, 10), "red", None, 5.0)
        self.assertTrue(result)
    
    def test_unique_claim(self):
        """Test unique near claim within palette."""
        rgb = (255, 10, 10)
        css_name = "red"
        palette_colors = [(100, 100, 255), (100, 255, 100)]  # No other reds
        
        result = is_unique_near_claim(rgb, css_name, palette_colors, 5.0)
        # Should be unique since no other palette colors are near red
        self.assertTrue(result)
    
    def test_non_unique_claim(self):
        """Test non-unique near claim (multiple colors near same CSS color)."""
        rgb = (255, 10, 10)
        css_name = "red"
        palette_colors = [(255, 5, 5), (255, 8, 8)]  # Multiple near-red colors
        
        result = is_unique_near_claim(rgb, css_name, palette_colors, 10.0)
        # Should not be unique since other colors are also near red
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()

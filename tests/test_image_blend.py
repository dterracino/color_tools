"""Unit tests for color_tools.image.blend module.

Tests all 27 Photoshop-compatible blend modes, the public blend_images()
API, internal helper functions, alpha compositing, and validation logic.
"""

import unittest
import sys
import tempfile
import os
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

DEPS_AVAILABLE = PILLOW_AVAILABLE and NUMPY_AVAILABLE


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def create_solid_image(w: int, h: int, color: tuple, mode: str = "RGB") -> str:
    """Create a solid-color PNG at a temp path and return that path."""
    img = Image.new(mode, (w, h), color)
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    img.save(path)
    return path


def _ones(h: int = 4, w: int = 4) -> "np.ndarray":
    """Return float32 array of ones, shape (H, W, 3)."""
    return np.ones((h, w, 3), dtype=np.float32)


def _scalar(v: float, h: int = 4, w: int = 4) -> "np.ndarray":
    """Return float32 array filled with scalar v, shape (H, W, 3)."""
    return np.full((h, w, 3), v, dtype=np.float32)


def _img_to_float(img: "Image.Image") -> "np.ndarray":
    """Convert PIL RGBA image to float32 numpy array in [0,1]."""
    return np.asarray(img, dtype=np.float32) / 255.0


# ---------------------------------------------------------------------------
# TestBlendModeRegistry
# ---------------------------------------------------------------------------

@unittest.skipUnless(DEPS_AVAILABLE, "Requires Pillow and numpy")
class TestBlendModeRegistry(unittest.TestCase):
    """Verify the BLEND_MODES registry contains all 27 expected entries."""

    EXPECTED_MODES = {
        "normal", "dissolve",
        "darken", "multiply", "color_burn", "linear_burn", "darker_color",
        "lighten", "screen", "color_dodge", "linear_dodge", "lighter_color",
        "overlay", "soft_light", "hard_light", "vivid_light", "linear_light",
        "pin_light", "hard_mix",
        "difference", "exclusion", "subtract", "divide",
        "hue", "saturation", "color", "luminosity",
    }

    @classmethod
    def setUpClass(cls):
        from color_tools.image.blend import BLEND_MODES
        cls.BLEND_MODES = BLEND_MODES

    def test_registry_has_all_27_modes(self):
        """BLEND_MODES contains exactly 27 entries."""
        self.assertEqual(len(self.BLEND_MODES), 27)

    def test_all_expected_names_present(self):
        """Every expected mode name is a key in BLEND_MODES."""
        for name in self.EXPECTED_MODES:
            with self.subTest(mode=name):
                self.assertIn(name, self.BLEND_MODES)

    def test_no_unexpected_names(self):
        """BLEND_MODES has no extra keys beyond the expected 27."""
        extra = set(self.BLEND_MODES.keys()) - self.EXPECTED_MODES
        self.assertEqual(extra, set(), f"Unexpected mode(s) found: {extra}")

    def test_all_values_are_callable(self):
        """Every value in BLEND_MODES is callable."""
        for name, fn in self.BLEND_MODES.items():
            with self.subTest(mode=name):
                self.assertTrue(callable(fn), f"{name!r} value is not callable")


# ---------------------------------------------------------------------------
# TestBlendMathNormal
# ---------------------------------------------------------------------------

@unittest.skipUnless(DEPS_AVAILABLE, "Requires Pillow and numpy")
class TestBlendMathNormal(unittest.TestCase):
    """Tests for the normal() blend mode."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image.blend import normal
        cls.normal = staticmethod(normal)

    def test_normal_returns_b(self):
        """normal(a, b) always returns b regardless of a."""
        a = _scalar(0.3)
        b = _scalar(0.7)
        result = self.normal(a, b)
        np.testing.assert_array_equal(result, b)

    def test_normal_returns_b_with_arbitrary_values(self):
        """normal passes any b array straight through."""
        a = np.random.rand(8, 8, 3).astype(np.float32)
        b = np.random.rand(8, 8, 3).astype(np.float32)
        result = self.normal(a, b)
        np.testing.assert_array_equal(result, b)

    def test_normal_ignores_a_completely(self):
        """Changing a does not change normal's output."""
        b = _scalar(0.5)
        result1 = self.normal(_scalar(0.0), b)
        result2 = self.normal(_scalar(1.0), b)
        np.testing.assert_array_equal(result1, result2)


# ---------------------------------------------------------------------------
# TestBlendMathDarkenGroup
# ---------------------------------------------------------------------------

@unittest.skipUnless(DEPS_AVAILABLE, "Requires Pillow and numpy")
class TestBlendMathDarkenGroup(unittest.TestCase):
    """Tests for the darken group: darken, multiply, color_burn, linear_burn, darker_color."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image.blend import (
            darken, multiply, color_burn, linear_burn, darker_color,
        )
        cls.darken = staticmethod(darken)
        cls.multiply = staticmethod(multiply)
        cls.color_burn = staticmethod(color_burn)
        cls.linear_burn = staticmethod(linear_burn)
        cls.darker_color = staticmethod(darker_color)

    # --- darken ---

    def test_darken_picks_minimum_per_channel(self):
        """darken(a, b) == np.minimum(a, b) channel-wise."""
        a = _scalar(0.6)
        b = _scalar(0.4)
        result = self.darken(a, b)
        np.testing.assert_allclose(result, _scalar(0.4), atol=1e-6)

    def test_darken_white_white_is_white(self):
        """darken of white on white stays white."""
        white = _ones()
        np.testing.assert_allclose(self.darken(white, white), white, atol=1e-6)

    def test_darken_black_base_stays_black(self):
        """darken with black base always stays black."""
        black = _scalar(0.0)
        np.testing.assert_allclose(self.darken(black, _scalar(0.8)), black, atol=1e-6)

    def test_darken_output_in_01(self):
        """darken output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.darken(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- multiply ---

    def test_multiply_half_half_gives_quarter(self):
        """multiply(0.5, 0.5) == 0.25."""
        a = _scalar(0.5)
        b = _scalar(0.5)
        np.testing.assert_allclose(self.multiply(a, b), _scalar(0.25), atol=1e-6)

    def test_multiply_white_identity(self):
        """multiply(a, 1) == a (white blend is identity)."""
        a = _scalar(0.7)
        np.testing.assert_allclose(self.multiply(a, _ones()), a, atol=1e-6)

    def test_multiply_black_stays_black(self):
        """multiply with black base gives black."""
        np.testing.assert_allclose(
            self.multiply(_scalar(0.0), _scalar(0.8)), _scalar(0.0), atol=1e-6
        )

    def test_multiply_output_in_01(self):
        """multiply output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.multiply(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- color_burn ---

    def test_color_burn_white_base_is_white(self):
        """color_burn(1, b) == 1 for any non-zero b."""
        a = _ones()
        b = _scalar(0.5)
        result = self.color_burn(a, b)
        np.testing.assert_allclose(result, _ones(), atol=1e-5)

    def test_color_burn_black_blend_gives_black(self):
        """color_burn with very dark blend layer darkens strongly toward black."""
        a = _scalar(0.5)
        b = _scalar(0.0)
        result = self.color_burn(a, b)
        np.testing.assert_allclose(result, _scalar(0.0), atol=1e-5)

    def test_color_burn_output_in_01(self):
        """color_burn output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.color_burn(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- linear_burn ---

    def test_linear_burn_adds_to_minus_one(self):
        """linear_burn(0.8, 0.8) == clip(0.8+0.8-1) == 0.6."""
        a = _scalar(0.8)
        b = _scalar(0.8)
        np.testing.assert_allclose(self.linear_burn(a, b), _scalar(0.6), atol=1e-5)

    def test_linear_burn_dark_values_clamp_to_black(self):
        """linear_burn(0.2, 0.2) == clip(-0.6) == 0."""
        np.testing.assert_allclose(
            self.linear_burn(_scalar(0.2), _scalar(0.2)), _scalar(0.0), atol=1e-5
        )

    def test_linear_burn_output_in_01(self):
        """linear_burn output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.linear_burn(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- darker_color ---

    def test_darker_color_picks_lower_luminance_pixel(self):
        """darker_color picks the whole pixel with lower BT.601 luminance."""
        # Pure red: lum ~ 0.299; pure blue: lum ~ 0.114
        a = np.zeros((1, 1, 3), dtype=np.float32)  # black (lum=0)
        b = np.ones((1, 1, 3), dtype=np.float32)   # white (lum=1)
        result = self.darker_color(a, b)
        np.testing.assert_allclose(result, a, atol=1e-6)

    def test_darker_color_same_luminance_keeps_a(self):
        """darker_color keeps a when lum(a) == lum(b)."""
        a = _scalar(0.5)
        result = self.darker_color(a, a)
        np.testing.assert_allclose(result, a, atol=1e-6)

    def test_darker_color_output_in_01(self):
        """darker_color output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.darker_color(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))


# ---------------------------------------------------------------------------
# TestBlendMathLightenGroup
# ---------------------------------------------------------------------------

@unittest.skipUnless(DEPS_AVAILABLE, "Requires Pillow and numpy")
class TestBlendMathLightenGroup(unittest.TestCase):
    """Tests for the lighten group: lighten, screen, color_dodge, linear_dodge, lighter_color."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image.blend import (
            lighten, screen, color_dodge, linear_dodge, lighter_color,
        )
        cls.lighten = staticmethod(lighten)
        cls.screen = staticmethod(screen)
        cls.color_dodge = staticmethod(color_dodge)
        cls.linear_dodge = staticmethod(linear_dodge)
        cls.lighter_color = staticmethod(lighter_color)

    # --- lighten ---

    def test_lighten_picks_maximum_per_channel(self):
        """lighten(a, b) == np.maximum(a, b) channel-wise."""
        a = _scalar(0.3)
        b = _scalar(0.7)
        np.testing.assert_allclose(self.lighten(a, b), _scalar(0.7), atol=1e-6)

    def test_lighten_white_blend_gives_white(self):
        """lighten(a, white) == white."""
        np.testing.assert_allclose(self.lighten(_scalar(0.4), _ones()), _ones(), atol=1e-6)

    def test_lighten_black_blend_is_identity(self):
        """lighten(a, black) == a (black blend has no effect)."""
        a = _scalar(0.6)
        np.testing.assert_allclose(self.lighten(a, _scalar(0.0)), a, atol=1e-6)

    def test_lighten_output_in_01(self):
        """lighten output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.lighten(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- screen ---

    def test_screen_half_half_is_three_quarters(self):
        """screen(0.5, 0.5) == 1-(0.5*0.5) == 0.75."""
        np.testing.assert_allclose(
            self.screen(_scalar(0.5), _scalar(0.5)), _scalar(0.75), atol=1e-5
        )

    def test_screen_white_gives_white(self):
        """screen(white, anything) == white."""
        np.testing.assert_allclose(self.screen(_ones(), _scalar(0.5)), _ones(), atol=1e-5)

    def test_screen_black_is_identity(self):
        """screen(a, black) == a."""
        a = _scalar(0.6)
        np.testing.assert_allclose(self.screen(a, _scalar(0.0)), a, atol=1e-5)

    def test_screen_output_in_01(self):
        """screen output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.screen(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- linear_dodge ---

    def test_linear_dodge_adds_values(self):
        """linear_dodge(0.4, 0.4) == clip(0.8) == 0.8."""
        np.testing.assert_allclose(
            self.linear_dodge(_scalar(0.4), _scalar(0.4)), _scalar(0.8), atol=1e-5
        )

    def test_linear_dodge_clamps_above_one(self):
        """linear_dodge(0.8, 0.8) == clip(1.6) == 1.0."""
        np.testing.assert_allclose(
            self.linear_dodge(_scalar(0.8), _scalar(0.8)), _ones(), atol=1e-5
        )

    def test_linear_dodge_black_is_identity(self):
        """linear_dodge(a, black) == a."""
        a = _scalar(0.5)
        np.testing.assert_allclose(self.linear_dodge(a, _scalar(0.0)), a, atol=1e-5)

    def test_linear_dodge_output_in_01(self):
        """linear_dodge output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.linear_dodge(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- color_dodge ---

    def test_color_dodge_divide_by_near_one_gives_base(self):
        """color_dodge(a, ~0) ≈ a (dividing by near-1 doesn't change much)."""
        a = _scalar(0.5)
        b = _scalar(0.0)  # 1-b≈1 → a/1 = a
        result = self.color_dodge(a, b)
        np.testing.assert_allclose(result, a, atol=1e-3)

    def test_color_dodge_output_in_01(self):
        """color_dodge output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.color_dodge(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- lighter_color ---

    def test_lighter_color_picks_higher_luminance_pixel(self):
        """lighter_color picks the whole pixel with higher BT.601 luminance."""
        a = _scalar(0.0)   # black: lum=0
        b = _scalar(1.0)   # white: lum=1
        result = self.lighter_color(a, b)
        np.testing.assert_allclose(result, b, atol=1e-6)

    def test_lighter_color_same_luminance_keeps_a(self):
        """lighter_color keeps a when lum(a) == lum(b)."""
        a = _scalar(0.5)
        result = self.lighter_color(a, a)
        np.testing.assert_allclose(result, a, atol=1e-6)

    def test_lighter_color_output_in_01(self):
        """lighter_color output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.lighter_color(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))


# ---------------------------------------------------------------------------
# TestBlendMathContrastGroup
# ---------------------------------------------------------------------------

@unittest.skipUnless(DEPS_AVAILABLE, "Requires Pillow and numpy")
class TestBlendMathContrastGroup(unittest.TestCase):
    """Tests for overlay, hard_light, soft_light, vivid_light, linear_light, pin_light, hard_mix."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image.blend import (
            overlay, hard_light, soft_light, vivid_light,
            linear_light, pin_light, hard_mix,
        )
        cls.overlay = staticmethod(overlay)
        cls.hard_light = staticmethod(hard_light)
        cls.soft_light = staticmethod(soft_light)
        cls.vivid_light = staticmethod(vivid_light)
        cls.linear_light = staticmethod(linear_light)
        cls.pin_light = staticmethod(pin_light)
        cls.hard_mix = staticmethod(hard_mix)

    # --- overlay ---

    def test_overlay_dark_base_uses_multiply_branch(self):
        """overlay(0.0, b) == 2*0*b == 0 (multiply branch)."""
        b = _scalar(0.6)
        result = self.overlay(_scalar(0.0), b)
        np.testing.assert_allclose(result, _scalar(0.0), atol=1e-5)

    def test_overlay_light_base_uses_screen_branch(self):
        """overlay(1.0, b) == 1 - 2*(0)*(1-b) == 1 (screen branch)."""
        b = _scalar(0.6)
        result = self.overlay(_scalar(1.0), b)
        np.testing.assert_allclose(result, _ones(), atol=1e-5)

    def test_overlay_midtone_base_both_branches_agree(self):
        """At a=0.5, both branches give 2*0.5*b == b (multiply) or 1-2*0.5*(1-b) == b (screen)."""
        # Both branches yield b when a=0.5: multiply gives 2*0.5*b = b; screen gives 1-2*0.5*(1-b) = b
        b = _scalar(0.4)
        result = self.overlay(_scalar(0.5), b)
        np.testing.assert_allclose(result, b, atol=1e-5)

    def test_overlay_output_in_01(self):
        """overlay output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.overlay(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- hard_light ---

    def test_hard_light_is_overlay_with_swapped_roles(self):
        """hard_light(a, b) == overlay(b, a) for arbitrary inputs."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        np.testing.assert_allclose(self.hard_light(a, b), self.overlay(b, a), atol=1e-5)

    def test_hard_light_output_in_01(self):
        """hard_light output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.hard_light(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- soft_light ---

    def test_soft_light_neutral_blend_is_identity(self):
        """soft_light(a, 0.5) == a for any a (b=0.5 is neutral)."""
        # When b=0.5: branch1 gives a - (1-1)*... = a; branch2 gives a + 0*... = a
        a = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.soft_light(a, _scalar(0.5))
        np.testing.assert_allclose(result, a, atol=1e-5)

    def test_soft_light_output_in_01(self):
        """soft_light output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.soft_light(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- vivid_light ---

    def test_vivid_light_output_in_01(self):
        """vivid_light output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.vivid_light(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    def test_vivid_light_white_base_light_blend(self):
        """vivid_light with white base and light blend gives white (color_dodge branch)."""
        result = self.vivid_light(_ones(), _scalar(0.8))
        np.testing.assert_allclose(result, _ones(), atol=1e-4)

    # --- linear_light ---

    def test_linear_light_known_value(self):
        """linear_light(0.5, 0.75) == clip(0.5 + 2*0.75 - 1) == clip(1.0) == 1."""
        result = self.linear_light(_scalar(0.5), _scalar(0.75))
        np.testing.assert_allclose(result, _ones(), atol=1e-5)

    def test_linear_light_midpoint_is_identity(self):
        """linear_light(a, 0.5) == clip(a + 2*0.5 - 1) == clip(a) == a."""
        a = _scalar(0.4)
        result = self.linear_light(a, _scalar(0.5))
        np.testing.assert_allclose(result, a, atol=1e-5)

    def test_linear_light_output_in_01(self):
        """linear_light output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.linear_light(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- pin_light ---

    def test_pin_light_output_in_01(self):
        """pin_light output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.pin_light(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    def test_pin_light_dark_blend_uses_darken(self):
        """pin_light(1.0, 0.3) uses darken branch: min(1.0, 2*0.3) == 0.6."""
        result = self.pin_light(_ones(), _scalar(0.3))
        np.testing.assert_allclose(result, _scalar(0.6), atol=1e-5)

    def test_pin_light_light_blend_uses_lighten(self):
        """pin_light(0.0, 0.8) uses lighten branch: max(0, 2*0.8-1) == 0.6."""
        result = self.pin_light(_scalar(0.0), _scalar(0.8))
        np.testing.assert_allclose(result, _scalar(0.6), atol=1e-5)

    # --- hard_mix ---

    def test_hard_mix_output_is_binary(self):
        """hard_mix output is exactly 0 or 1 — no intermediate values."""
        a = np.random.rand(8, 8, 3).astype(np.float32)
        b = np.random.rand(8, 8, 3).astype(np.float32)
        result = self.hard_mix(a, b)
        unique = np.unique(result)
        for v in unique:
            self.assertIn(v, (0.0, 1.0), f"Unexpected value {v} in hard_mix output")

    def test_hard_mix_known_values(self):
        """hard_mix(0.3, 0.3) == 0 (sum < 1); hard_mix(0.6, 0.6) == 1 (sum > 1)."""
        np.testing.assert_allclose(self.hard_mix(_scalar(0.3), _scalar(0.3)), _scalar(0.0), atol=1e-6)
        np.testing.assert_allclose(self.hard_mix(_scalar(0.6), _scalar(0.6)), _scalar(1.0), atol=1e-6)


# ---------------------------------------------------------------------------
# TestBlendMathComparativeGroup
# ---------------------------------------------------------------------------

@unittest.skipUnless(DEPS_AVAILABLE, "Requires Pillow and numpy")
class TestBlendMathComparativeGroup(unittest.TestCase):
    """Tests for difference, exclusion, subtract, divide."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image.blend import difference, exclusion, subtract, divide
        cls.difference = staticmethod(difference)
        cls.exclusion = staticmethod(exclusion)
        cls.subtract = staticmethod(subtract)
        cls.divide = staticmethod(divide)

    # --- difference ---

    def test_difference_identical_layers_cancel(self):
        """difference(x, x) == 0 for any x."""
        x = np.random.rand(4, 4, 3).astype(np.float32)
        np.testing.assert_allclose(self.difference(x, x), _scalar(0.0), atol=1e-6)

    def test_difference_is_symmetric(self):
        """difference(a, b) == difference(b, a)."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        np.testing.assert_allclose(self.difference(a, b), self.difference(b, a), atol=1e-6)

    def test_difference_known_value(self):
        """difference(0.8, 0.3) == abs(0.8-0.3) == 0.5."""
        np.testing.assert_allclose(
            self.difference(_scalar(0.8), _scalar(0.3)), _scalar(0.5), atol=1e-5
        )

    def test_difference_output_in_01(self):
        """difference output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.difference(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- exclusion ---

    def test_exclusion_black_base_gives_blend(self):
        """exclusion(0, b) == 0 + b - 0 == b."""
        b = _scalar(0.6)
        np.testing.assert_allclose(self.exclusion(_scalar(0.0), b), b, atol=1e-6)

    def test_exclusion_white_base_gives_inverse(self):
        """exclusion(1, b) == 1 + b - 2b == 1 - b."""
        b = _scalar(0.6)
        np.testing.assert_allclose(
            self.exclusion(_ones(), b), _scalar(0.4), atol=1e-5
        )

    def test_exclusion_identical_layers(self):
        """exclusion(x, x) == x + x - 2x^2 == 2x(1-x)."""
        x = _scalar(0.5)
        expected = _scalar(0.5)  # 2*0.5*0.5 = 0.5
        np.testing.assert_allclose(self.exclusion(x, x), expected, atol=1e-5)

    def test_exclusion_output_in_01(self):
        """exclusion output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.exclusion(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- subtract ---

    def test_subtract_same_layer_gives_black(self):
        """subtract(a, a) == 0."""
        a = _scalar(0.7)
        np.testing.assert_allclose(self.subtract(a, a), _scalar(0.0), atol=1e-6)

    def test_subtract_known_value(self):
        """subtract(0.8, 0.3) == clip(0.5) == 0.5."""
        np.testing.assert_allclose(
            self.subtract(_scalar(0.8), _scalar(0.3)), _scalar(0.5), atol=1e-5
        )

    def test_subtract_clamps_to_black(self):
        """subtract(0.2, 0.8) == clip(-0.6) == 0."""
        np.testing.assert_allclose(
            self.subtract(_scalar(0.2), _scalar(0.8)), _scalar(0.0), atol=1e-5
        )

    def test_subtract_output_in_01(self):
        """subtract output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.subtract(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- divide ---

    def test_divide_by_white_is_identity(self):
        """divide(a, 1.0) == a (dividing by white = no change)."""
        a = _scalar(0.6)
        np.testing.assert_allclose(self.divide(a, _ones()), a, atol=1e-4)

    def test_divide_identical_layers_approx_white(self):
        """divide(a, a) ≈ 1 for non-zero a (a/a==1)."""
        a = _scalar(0.5)
        result = self.divide(a, a)
        np.testing.assert_allclose(result, _ones(), atol=1e-4)

    def test_divide_output_in_01(self):
        """divide output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.divide(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))


# ---------------------------------------------------------------------------
# TestBlendMathComponentGroup
# ---------------------------------------------------------------------------

@unittest.skipUnless(DEPS_AVAILABLE, "Requires Pillow and numpy")
class TestBlendMathComponentGroup(unittest.TestCase):
    """Tests for hue, saturation, color, luminosity blend modes."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image.blend import hue, saturation, color, luminosity, _lum
        cls.hue = staticmethod(hue)
        cls.saturation = staticmethod(saturation)
        cls.color = staticmethod(color)
        cls.luminosity = staticmethod(luminosity)
        cls._lum = staticmethod(_lum)

    # --- color ---

    def test_color_result_has_base_luminance(self):
        """color(a, b): luminance of result equals luminance of a (no clipping case)."""
        # Use a gray base and moderate blend so _set_lum won't clip.
        # color(a, b) = _set_lum(b, lum(a))
        # Gray base lum=0.4; blend with matching range ensures no channel clips.
        a = _scalar(0.4)  # gray, lum=0.4
        b = np.array([[[0.3, 0.4, 0.5]]], dtype=np.float32).repeat(4, 0).repeat(4, 1)
        # lum(b) ≈ 0.3815, target=0.4, delta≈+0.019 → no clipping
        result = self.color(a, b)
        result_lum = self._lum(result)
        base_lum = self._lum(a)
        np.testing.assert_allclose(result_lum, base_lum, atol=1e-4)

    def test_color_output_in_01(self):
        """color output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.color(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    # --- luminosity ---

    def test_luminosity_result_has_blend_luminance(self):
        """luminosity(a, b): luminance of result equals luminance of b (no clipping case)."""
        # luminosity(a, b) = _set_lum(a, lum(b))
        # Use a=(0.3,0.4,0.5) lum≈0.3815 and b=gray(0.4) lum=0.4; delta≈+0.019 → no clipping
        a = np.array([[[0.3, 0.4, 0.5]]], dtype=np.float32).repeat(4, 0).repeat(4, 1)
        b = _scalar(0.4)
        result = self.luminosity(a, b)
        result_lum = self._lum(result)
        blend_lum = self._lum(b)
        np.testing.assert_allclose(result_lum, blend_lum, atol=1e-4)

    def test_luminosity_output_in_01(self):
        """luminosity output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.luminosity(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    def test_luminosity_grayscale_base_preserves_base_structure(self):
        """luminosity on a grayscale base with colored blend has blend luminance."""
        gray = _scalar(0.3)  # uniform gray: lum=0.3
        colored = np.zeros((4, 4, 3), dtype=np.float32)
        colored[..., 1] = 1.0  # pure green: lum≈0.587
        result = self.luminosity(gray, colored)
        result_lum = self._lum(result)
        expected_lum = self._lum(colored)
        np.testing.assert_allclose(result_lum, expected_lum, atol=1e-4)

    # --- hue ---

    def test_hue_output_in_01(self):
        """hue output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.hue(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    def test_hue_with_gray_base_gives_gray(self):
        """hue(gray, b): gray base has sat=0, so result stays gray (sat=0 → achromatic)."""
        gray = _scalar(0.5)
        b = np.zeros((4, 4, 3), dtype=np.float32)
        b[..., 0] = 1.0  # pure red blend
        result = self.hue(gray, b)
        # All channels should be equal (gray) since set_sat with s=0 gives gray
        np.testing.assert_allclose(result[..., 0], result[..., 1], atol=1e-4)
        np.testing.assert_allclose(result[..., 1], result[..., 2], atol=1e-4)

    # --- saturation ---

    def test_saturation_output_in_01(self):
        """saturation output is always in [0, 1]."""
        a = np.random.rand(4, 4, 3).astype(np.float32)
        b = np.random.rand(4, 4, 3).astype(np.float32)
        result = self.saturation(a, b)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    def test_saturation_with_gray_blend_gives_gray_result(self):
        """saturation(a, gray): gray blend has sat=0, so result has sat=0 (achromatic)."""
        a = np.zeros((4, 4, 3), dtype=np.float32)
        a[..., 0] = 1.0  # pure red base
        gray = _scalar(0.5)  # sat=0
        result = self.saturation(a, gray)
        # All channels equal → achromatic
        np.testing.assert_allclose(result[..., 0], result[..., 1], atol=1e-4)
        np.testing.assert_allclose(result[..., 1], result[..., 2], atol=1e-4)


# ---------------------------------------------------------------------------
# TestHelpers
# ---------------------------------------------------------------------------

@unittest.skipUnless(DEPS_AVAILABLE, "Requires Pillow and numpy")
class TestHelpers(unittest.TestCase):
    """Tests for internal helper functions: _clip01, _lum, _sat, _set_lum, _set_sat."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image.blend import _clip01, _lum, _sat, _set_lum, _set_sat
        cls._clip01 = staticmethod(_clip01)
        cls._lum = staticmethod(_lum)
        cls._sat = staticmethod(_sat)
        cls._set_lum = staticmethod(_set_lum)
        cls._set_sat = staticmethod(_set_sat)

    # --- _clip01 ---

    def test_clip01_values_above_one_become_one(self):
        """Values > 1 are clipped to 1."""
        x = np.array([[[1.5, 2.0, 100.0]]], dtype=np.float32)
        result = self._clip01(x)
        np.testing.assert_allclose(result, np.array([[[1.0, 1.0, 1.0]]]), atol=1e-6)

    def test_clip01_values_below_zero_become_zero(self):
        """Values < 0 are clipped to 0."""
        x = np.array([[[-0.1, -1.0, -50.0]]], dtype=np.float32)
        result = self._clip01(x)
        np.testing.assert_allclose(result, np.array([[[0.0, 0.0, 0.0]]]), atol=1e-6)

    def test_clip01_values_inside_range_unchanged(self):
        """Values in [0, 1] are unchanged."""
        x = np.array([[[0.0, 0.5, 1.0]]], dtype=np.float32)
        result = self._clip01(x)
        np.testing.assert_allclose(result, x, atol=1e-6)

    # --- _lum ---

    def test_lum_pure_red(self):
        """BT.601 luminance of pure red (1,0,0) == 0.299."""
        red = np.array([[[1.0, 0.0, 0.0]]], dtype=np.float32)
        np.testing.assert_allclose(self._lum(red), np.array([[0.299]]), atol=1e-4)

    def test_lum_pure_green(self):
        """BT.601 luminance of pure green (0,1,0) == 0.587."""
        green = np.array([[[0.0, 1.0, 0.0]]], dtype=np.float32)
        np.testing.assert_allclose(self._lum(green), np.array([[0.587]]), atol=1e-4)

    def test_lum_pure_blue(self):
        """BT.601 luminance of pure blue (0,0,1) == 0.114."""
        blue = np.array([[[0.0, 0.0, 1.0]]], dtype=np.float32)
        np.testing.assert_allclose(self._lum(blue), np.array([[0.114]]), atol=1e-4)

    def test_lum_gray_equals_itself(self):
        """Luminance of a gray (v, v, v) equals v."""
        for v in [0.0, 0.25, 0.5, 0.75, 1.0]:
            with self.subTest(v=v):
                gray = np.array([[[v, v, v]]], dtype=np.float32)
                np.testing.assert_allclose(self._lum(gray), np.array([[v]]), atol=1e-5)

    def test_lum_white_is_one(self):
        """Luminance of pure white (1,1,1) == 1."""
        white = np.array([[[1.0, 1.0, 1.0]]], dtype=np.float32)
        np.testing.assert_allclose(self._lum(white), np.array([[1.0]]), atol=1e-5)

    def test_lum_black_is_zero(self):
        """Luminance of pure black (0,0,0) == 0."""
        black = np.array([[[0.0, 0.0, 0.0]]], dtype=np.float32)
        np.testing.assert_allclose(self._lum(black), np.array([[0.0]]), atol=1e-5)

    # --- _sat ---

    def test_sat_pure_red_is_one(self):
        """Saturation of pure red (1,0,0) == max-min == 1.0."""
        red = np.array([[[1.0, 0.0, 0.0]]], dtype=np.float32)
        np.testing.assert_allclose(self._sat(red), np.array([[1.0]]), atol=1e-5)

    def test_sat_gray_is_zero(self):
        """Saturation of a neutral gray (v, v, v) == 0."""
        for v in [0.0, 0.5, 1.0]:
            with self.subTest(v=v):
                gray = np.array([[[v, v, v]]], dtype=np.float32)
                np.testing.assert_allclose(self._sat(gray), np.array([[0.0]]), atol=1e-5)

    def test_sat_known_value(self):
        """Saturation of (0.2, 0.5, 0.8) == 0.8 - 0.2 == 0.6."""
        c = np.array([[[0.2, 0.5, 0.8]]], dtype=np.float32)
        np.testing.assert_allclose(self._sat(c), np.array([[0.6]]), atol=1e-5)

    # --- _set_lum ---

    def test_set_lum_gray_to_same_gives_gray(self):
        """Setting luminance of (v,v,v) to v gives back (v,v,v)."""
        gray = np.array([[[0.5, 0.5, 0.5]]], dtype=np.float32)
        target = np.array([[0.5]], dtype=np.float32)
        result = self._set_lum(gray, target)
        np.testing.assert_allclose(result, gray, atol=1e-5)

    def test_set_lum_output_in_01(self):
        """_set_lum result is always clipped to [0, 1]."""
        c = np.random.rand(4, 4, 3).astype(np.float32)
        target = np.random.rand(4, 4).astype(np.float32)
        result = self._set_lum(c, target)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))

    def test_set_lum_changes_luminance(self):
        """_set_lum achieves target luminance when no channel clipping occurs."""
        from color_tools.image.blend import _lum
        # Use (0.3, 0.3, 0.5): lum≈0.3228; target=0.35; delta≈+0.027 → no clipping
        c = np.array([[[0.3, 0.3, 0.5]]], dtype=np.float32)
        target = np.array([[0.35]], dtype=np.float32)
        result = self._set_lum(c, target)
        result_lum = _lum(result)
        np.testing.assert_allclose(result_lum, target, atol=1e-4)

    # --- _set_sat ---

    def test_set_sat_gray_to_zero_stays_gray(self):
        """Setting saturation of a gray pixel to 0 keeps it gray (all channels equal)."""
        gray = np.array([[[0.5, 0.5, 0.5]]], dtype=np.float32)
        target = np.array([[0.0]], dtype=np.float32)
        result = self._set_sat(gray, target)
        np.testing.assert_allclose(result[..., 0], result[..., 1], atol=1e-5)
        np.testing.assert_allclose(result[..., 1], result[..., 2], atol=1e-5)

    def test_set_sat_colored_pixel_to_zero_gives_gray(self):
        """Setting saturation to 0 on a colored pixel gives an achromatic result."""
        red = np.zeros((1, 1, 3), dtype=np.float32)
        red[..., 0] = 1.0  # pure red, sat=1
        target = np.array([[0.0]], dtype=np.float32)
        result = self._set_sat(red, target)
        np.testing.assert_allclose(result[..., 0], result[..., 1], atol=1e-5)
        np.testing.assert_allclose(result[..., 1], result[..., 2], atol=1e-5)

    def test_set_sat_changes_saturation_on_colored_pixel(self):
        """_set_sat correctly sets saturation on a pixel with existing hue."""
        # _set_sat on a gray (span=0) cannot add saturation (no hue direction).
        # Use a clearly non-gray pixel: (0.1, 0.5, 0.9), sat=0.8; target=0.5
        # sorted: [0.1, 0.5, 0.9], span=0.8; mid_new=(0.5-0.1)/0.8*0.5=0.25; max_new=0.5
        # result=[0, 0.25, 0.5], _sat=0.5 ✓
        from color_tools.image.blend import _sat
        c = np.array([[[0.1, 0.5, 0.9]]], dtype=np.float32)
        target = np.array([[0.5]], dtype=np.float32)
        result = self._set_sat(c, target)
        result_sat = _sat(result)
        np.testing.assert_allclose(result_sat, target, atol=1e-5)

    def test_set_sat_output_in_01(self):
        """_set_sat result is always in [0, 1]."""
        c = np.random.rand(4, 4, 3).astype(np.float32)
        target = np.random.rand(4, 4).astype(np.float32)
        result = self._set_sat(c, target)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 1.0))


# ---------------------------------------------------------------------------
# TestBlendImagesIO
# ---------------------------------------------------------------------------

@unittest.skipUnless(DEPS_AVAILABLE, "Requires Pillow and numpy")
class TestBlendImagesIO(unittest.TestCase):
    """Tests for blend_images() I/O behavior using actual image files."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image.blend import blend_images, BLEND_MODES
        cls.blend_images = staticmethod(blend_images)
        cls.BLEND_MODES = BLEND_MODES

    def setUp(self):
        self.test_files = []

    def tearDown(self):
        for f in self.test_files:
            if os.path.exists(f):
                os.remove(f)

    def _make(self, w, h, color, mode="RGB"):
        path = create_solid_image(w, h, color, mode)
        self.test_files.append(path)
        return path

    def test_returns_pil_image(self):
        """blend_images() returns a PIL Image object."""
        base = self._make(8, 8, (100, 150, 200))
        blend = self._make(8, 8, (200, 100, 50))
        result = self.blend_images(base, blend)
        self.assertIsInstance(result, Image.Image)

    def test_returns_rgba_mode(self):
        """blend_images() always returns an image in RGBA mode."""
        base = self._make(8, 8, (100, 150, 200))
        blend = self._make(8, 8, (50, 100, 150))
        result = self.blend_images(base, blend)
        self.assertEqual(result.mode, "RGBA")

    def test_normal_full_opacity_result_equals_blend_layer(self):
        """normal mode + opacity=1.0: output RGB matches the blend layer colors."""
        base = self._make(8, 8, (255, 0, 0))     # red
        blend = self._make(8, 8, (0, 255, 0))    # green
        result = self.blend_images(base, blend, mode="normal", opacity=1.0)
        arr = np.asarray(result, dtype=np.uint8)
        # All pixels should be green (RGB: 0, 255, 0)
        np.testing.assert_allclose(arr[..., 0], 0,   atol=2)
        np.testing.assert_allclose(arr[..., 1], 255, atol=2)
        np.testing.assert_allclose(arr[..., 2], 0,   atol=2)

    def test_normal_zero_opacity_result_equals_base_layer(self):
        """normal mode + opacity=0.0: output RGB matches the base layer colors."""
        base = self._make(8, 8, (255, 0, 0))   # red
        blend = self._make(8, 8, (0, 255, 0))  # green
        result = self.blend_images(base, blend, mode="normal", opacity=0.0)
        arr = np.asarray(result, dtype=np.uint8)
        np.testing.assert_allclose(arr[..., 0], 255, atol=2)
        np.testing.assert_allclose(arr[..., 1], 0,   atol=2)
        np.testing.assert_allclose(arr[..., 2], 0,   atol=2)

    def test_multiply_black_base_gives_black(self):
        """multiply mode: black base × anything == black."""
        base = self._make(8, 8, (0, 0, 0))          # black
        blend = self._make(8, 8, (200, 150, 100))
        result = self.blend_images(base, blend, mode="multiply", opacity=1.0)
        arr = np.asarray(result, dtype=np.uint8)
        np.testing.assert_allclose(arr[..., :3], 0, atol=2)

    def test_multiply_white_white_gives_white(self):
        """multiply mode: white × white == white."""
        base = self._make(8, 8, (255, 255, 255))
        blend = self._make(8, 8, (255, 255, 255))
        result = self.blend_images(base, blend, mode="multiply", opacity=1.0)
        arr = np.asarray(result, dtype=np.uint8)
        np.testing.assert_allclose(arr[..., :3], 255, atol=2)

    def test_result_size_matches_base_image(self):
        """Output image has same dimensions as base image."""
        base = self._make(20, 30, (100, 100, 100))
        blend = self._make(20, 30, (200, 200, 200))
        result = self.blend_images(base, blend)
        self.assertEqual(result.size, (20, 30))

    def test_blend_layer_resized_when_sizes_differ(self):
        """Blend layer is resized to match base; output matches base dimensions."""
        base = self._make(32, 32, (100, 100, 100))
        blend = self._make(16, 16, (200, 200, 200))  # different size
        result = self.blend_images(base, blend)
        self.assertEqual(result.size, (32, 32))

    def test_output_path_saves_file_to_disk(self):
        """blend_images saves result to output_path when provided."""
        base = self._make(8, 8, (100, 100, 100))
        blend = self._make(8, 8, (200, 200, 200))
        fd, out_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        self.test_files.append(out_path)
        self.blend_images(base, blend, output_path=out_path)
        self.assertTrue(os.path.exists(out_path))
        saved = Image.open(out_path)
        self.assertEqual(saved.mode, "RGBA")

    def test_all_27_modes_run_without_error(self):
        """Smoke test: every blend mode runs without raising an exception."""
        base = self._make(8, 8, (120, 80, 160))
        blend = self._make(8, 8, (200, 120, 40))
        for mode_name in self.BLEND_MODES:
            with self.subTest(mode=mode_name):
                result = self.blend_images(base, blend, mode=mode_name, opacity=0.7)
                self.assertIsInstance(result, Image.Image)
                self.assertEqual(result.mode, "RGBA")

    def test_accepts_path_objects(self):
        """blend_images accepts pathlib.Path objects as input paths."""
        base = self._make(8, 8, (100, 150, 100))
        blend = self._make(8, 8, (50, 100, 200))
        result = self.blend_images(Path(base), Path(blend))
        self.assertIsInstance(result, Image.Image)


# ---------------------------------------------------------------------------
# TestBlendImagesValidation
# ---------------------------------------------------------------------------

@unittest.skipUnless(DEPS_AVAILABLE, "Requires Pillow and numpy")
class TestBlendImagesValidation(unittest.TestCase):
    """Tests for blend_images() input validation."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image.blend import blend_images
        cls.blend_images = staticmethod(blend_images)

    def setUp(self):
        self.test_files = []

    def tearDown(self):
        for f in self.test_files:
            if os.path.exists(f):
                os.remove(f)

    def _make(self, w=8, h=8, color=(128, 128, 128)):
        path = create_solid_image(w, h, color)
        self.test_files.append(path)
        return path

    def test_unknown_mode_raises_value_error(self):
        """blend_images raises ValueError for an unknown blend mode."""
        base = self._make()
        blend = self._make()
        with self.assertRaises(ValueError) as ctx:
            self.blend_images(base, blend, mode="not_a_real_mode")
        self.assertIn("not_a_real_mode", str(ctx.exception))

    def test_opacity_below_zero_raises_value_error(self):
        """blend_images raises ValueError for opacity < 0."""
        base = self._make()
        blend = self._make()
        with self.assertRaises(ValueError):
            self.blend_images(base, blend, opacity=-0.01)

    def test_opacity_above_one_raises_value_error(self):
        """blend_images raises ValueError for opacity > 1."""
        base = self._make()
        blend = self._make()
        with self.assertRaises(ValueError):
            self.blend_images(base, blend, opacity=1.01)

    def test_opacity_at_boundaries_does_not_raise(self):
        """blend_images accepts opacity=0.0 and opacity=1.0 without error."""
        base = self._make()
        blend = self._make()
        for opacity in [0.0, 1.0]:
            with self.subTest(opacity=opacity):
                result = self.blend_images(base, blend, opacity=opacity)
                self.assertIsInstance(result, Image.Image)

    def test_half_opacity_produces_intermediate_result(self):
        """opacity=0.5 with normal mode produces RGB between base and blend."""
        base = self._make(8, 8, (0, 0, 0))       # black
        blend = self._make(8, 8, (200, 200, 200))  # near-white
        result = self.blend_images(base, blend, mode="normal", opacity=0.5)
        arr = np.asarray(result, dtype=np.uint8)
        # Channel values should be between 0 and 200
        self.assertTrue(np.all(arr[..., :3] > 0))
        self.assertTrue(np.all(arr[..., :3] < 200))


# ---------------------------------------------------------------------------
# TestBlendImagesAlpha
# ---------------------------------------------------------------------------

@unittest.skipUnless(DEPS_AVAILABLE, "Requires Pillow and numpy")
class TestBlendImagesAlpha(unittest.TestCase):
    """Tests for alpha compositing behavior in blend_images()."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image.blend import blend_images
        cls.blend_images = staticmethod(blend_images)

    def setUp(self):
        self.test_files = []

    def tearDown(self):
        for f in self.test_files:
            if os.path.exists(f):
                os.remove(f)

    def _make_rgba(self, w, h, color_rgba: tuple):
        path = create_solid_image(w, h, color_rgba, mode="RGBA")
        self.test_files.append(path)
        return path

    def _make_rgb(self, w, h, color_rgb: tuple):
        path = create_solid_image(w, h, color_rgb, mode="RGB")
        self.test_files.append(path)
        return path

    def test_transparent_blend_layer_alpha_preserves_base_alpha(self):
        """Fully transparent blend (alpha=0) at opacity=1.0: out_alpha == base_alpha via src-over."""
        # out_alpha = blend_alpha * opacity + base_alpha * (1 - blend_alpha * opacity)
        #           = 0 * 1.0 + base_alpha * (1 - 0) = base_alpha
        base = self._make_rgba(8, 8, (200, 100, 50, 200))   # alpha ≈ 0.784
        blend = self._make_rgba(8, 8, (100, 200, 150, 0))    # fully transparent blend
        result = self.blend_images(base, blend, mode="normal", opacity=1.0)
        arr = _img_to_float(result)
        expected_alpha = 200 / 255.0
        np.testing.assert_allclose(arr[..., 3], expected_alpha, atol=0.01)

    def test_opaque_blend_at_full_opacity_alpha_driven_by_blend(self):
        """Fully opaque blend (alpha=255) at opacity=1 → out_alpha = blend_alpha."""
        base = self._make_rgba(8, 8, (100, 100, 100, 128))    # semi-transparent base
        blend = self._make_rgba(8, 8, (200, 200, 200, 255))   # opaque blend
        result = self.blend_images(base, blend, mode="normal", opacity=1.0)
        arr = _img_to_float(result)
        # out_alpha = blend_alpha*1 + base_alpha*(1 - blend_alpha*1) = 1 + 0.5*0 = 1
        np.testing.assert_allclose(arr[..., 3], 1.0, atol=0.01)

    def test_opacity_scales_blend_alpha_contribution(self):
        """Reducing opacity reduces the blend layer's alpha contribution."""
        base = self._make_rgba(8, 8, (0, 0, 0, 255))         # opaque black base
        blend = self._make_rgba(8, 8, (255, 255, 255, 255))  # opaque white blend
        result_full = self.blend_images(base, blend, mode="normal", opacity=1.0)
        result_half = self.blend_images(base, blend, mode="normal", opacity=0.5)

        arr_full = _img_to_float(result_full)
        arr_half = _img_to_float(result_half)

        # The half-opacity result should have lower RGB than full-opacity normal blend
        self.assertTrue(np.mean(arr_half[..., :3]) < np.mean(arr_full[..., :3]))

    def test_rgba_base_and_rgba_blend_composited_correctly(self):
        """RGBA base + RGBA blend: src-over formula applies with opacity=1."""
        # base_alpha = 0.5, blend_alpha = 0.8, opacity = 1.0
        # out_alpha = 0.8*1 + 0.5*(1 - 0.8*1) = 0.8 + 0.5*0.2 = 0.9
        base = self._make_rgba(8, 8, (50, 50, 50, 128))     # alpha ≈ 0.502
        blend = self._make_rgba(8, 8, (200, 200, 200, 204)) # alpha ≈ 0.800
        result = self.blend_images(base, blend, mode="normal", opacity=1.0)
        arr = _img_to_float(result)
        # Expected: 0.800*1 + 0.502*(1 - 0.800) ≈ 0.800 + 0.100 ≈ 0.900
        expected_alpha = 0.800 + 0.502 * (1.0 - 0.800)
        np.testing.assert_allclose(arr[..., 3], expected_alpha, atol=0.01)


# ---------------------------------------------------------------------------
# TestDissolveMode
# ---------------------------------------------------------------------------

@unittest.skipUnless(DEPS_AVAILABLE, "Requires Pillow and numpy")
class TestDissolveMode(unittest.TestCase):
    """Tests for the dissolve blend mode's opacity-as-threshold behavior."""

    @classmethod
    def setUpClass(cls):
        from color_tools.image.blend import blend_images, dissolve
        cls.blend_images = staticmethod(blend_images)
        cls.dissolve = staticmethod(dissolve)

    def setUp(self):
        self.test_files = []

    def tearDown(self):
        for f in self.test_files:
            if os.path.exists(f):
                os.remove(f)

    def _make(self, color, w=32, h=32):
        path = create_solid_image(w, h, color)
        self.test_files.append(path)
        return path

    def test_dissolve_full_opacity_all_pixels_from_blend(self):
        """dissolve at opacity=1.0: all pixels come from blend layer."""
        base = self._make((0, 0, 0))         # black
        blend = self._make((255, 255, 255))  # white
        result = self.blend_images(base, blend, mode="dissolve", opacity=1.0)
        arr = np.asarray(result, dtype=np.uint8)
        # All pixels should be white (from blend)
        np.testing.assert_allclose(arr[..., :3], 255, atol=2)

    def test_dissolve_zero_opacity_all_pixels_from_base(self):
        """dissolve at opacity=0.0: all pixels come from base layer."""
        base = self._make((0, 0, 0))         # black
        blend = self._make((255, 255, 255))  # white
        result = self.blend_images(base, blend, mode="dissolve", opacity=0.0)
        arr = np.asarray(result, dtype=np.uint8)
        # All pixels should be black (from base)
        np.testing.assert_allclose(arr[..., :3], 0, atol=2)

    def test_dissolve_intermediate_opacity_is_stochastic_mix(self):
        """dissolve at 0.5 opacity: each pixel is either from base or blend."""
        base_color = (0, 0, 0)
        blend_color = (255, 255, 255)
        base = self._make(base_color, w=64, h=64)
        blend = self._make(blend_color, w=64, h=64)
        result = self.blend_images(base, blend, mode="dissolve", opacity=0.5)
        arr = np.asarray(result, dtype=np.uint8)[..., :3]
        # Each pixel must be exactly one of the two colors (not a blend)
        for r, g, b in arr.reshape(-1, 3):
            is_base = (int(r), int(g), int(b)) == base_color
            is_blend = (int(r), int(g), int(b)) == blend_color
            self.assertTrue(is_base or is_blend, f"Unexpected pixel color: ({r},{g},{b})")

    def test_dissolve_function_returns_either_a_or_b(self):
        """Low-level dissolve(): each pixel is exactly a or b, nothing in between."""
        a = np.zeros((8, 8, 3), dtype=np.float32)   # black
        b = np.ones((8, 8, 3), dtype=np.float32)    # white
        result = self.dissolve(a, b)
        flat = result.reshape(-1, 3)
        for pixel in flat:
            is_a = np.allclose(pixel, 0.0, atol=1e-6)
            is_b = np.allclose(pixel, 1.0, atol=1e-6)
            self.assertTrue(is_a or is_b, f"Pixel {pixel} is neither a nor b")


if __name__ == "__main__":
    unittest.main()

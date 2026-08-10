"""Unit tests for LCH-based color harmony generation."""

from __future__ import annotations

import unittest

from color_tools.conversions import rgb_to_lch
from color_tools.harmony import generate_harmony, generate_harmony_lch


class TestGenerateHarmonyLCH(unittest.TestCase):
    """Test the direct LCH harmony API."""

    def test_fixed_scheme_offsets(self) -> None:
        cases = {
            "analogous": (0.0, -30.0, 30.0, 60.0),
            "complementary": (0.0, 180.0),
            "full-spectrum": tuple(float(offset) for offset in range(0, 360, 60)),
            "rainbow": tuple(float(offset) for offset in range(0, 360, 60)),
            "split-complementary": (0.0, 150.0, 210.0),
            "triadic": (0.0, 120.0, 240.0),
            "square": (0.0, 90.0, 180.0, 270.0),
            "tetradic": (0.0, 60.0, 180.0, 240.0),
        }

        for scheme, expected_offsets in cases.items():
            with self.subTest(scheme=scheme):
                result = generate_harmony_lch((50.0, 40.0, 10.0), scheme)  # type: ignore[arg-type]
                self.assertEqual(
                    tuple(color.hue_offset for color in result.colors),
                    expected_offsets,
                )

    def test_scheme_color_counts(self) -> None:
        expected_counts = {
            "analogous": 4,
            "complementary": 2,
            "full-spectrum": 6,
            "monochromatic": 5,
            "rainbow": 6,
            "split-complementary": 3,
            "triadic": 3,
            "square": 4,
            "tetradic": 4,
        }

        for scheme, expected_count in expected_counts.items():
            with self.subTest(scheme=scheme):
                result = generate_harmony_lch((50.0, 40.0, 10.0), scheme)  # type: ignore[arg-type]
                self.assertEqual(len(result.colors), expected_count)

    def test_analogous_hues_wrap_around(self) -> None:
        result = generate_harmony_lch((50.0, 40.0, 10.0), "analogous")

        self.assertEqual(
            tuple(color.ideal_lch[2] for color in result.colors),
            (10.0, 340.0, 40.0, 70.0),
        )

    def test_full_spectrum_is_rainbow_alias(self) -> None:
        rainbow = generate_harmony_lch((50.0, 40.0, 10.0), "rainbow")
        full_spectrum = generate_harmony_lch((50.0, 40.0, 10.0), "full-spectrum")

        self.assertEqual(rainbow.colors, full_spectrum.colors)

    def test_monochromatic_varies_lightness_and_chroma_only(self) -> None:
        result = generate_harmony_lch((40.0, 80.0, 25.0), "monochromatic")

        self.assertEqual(
            tuple(color.ideal_lch for color in result.colors),
            (
                (40.0, 80.0, 25.0),
                (70.0, 60.0, 25.0),
                (85.0, 40.0, 25.0),
                (20.0, 60.0, 25.0),
                (40.0, 40.0, 25.0),
            ),
        )
        self.assertEqual(
            tuple(color.hue_offset for color in result.colors),
            (0.0, 0.0, 0.0, 0.0, 0.0),
        )

    def test_hue_offsets_wrap_around(self) -> None:
        result = generate_harmony_lch((50.0, 40.0, 350.0), "triadic")

        self.assertEqual(
            tuple(color.ideal_lch[2] for color in result.colors),
            (350.0, 110.0, 230.0),
        )

    def test_preserves_ideal_lightness_and_chroma(self) -> None:
        result = generate_harmony_lch((48.0, 70.0, 15.0), "square")

        for color in result.colors:
            self.assertEqual(color.ideal_lch[:2], (48.0, 70.0))

    def test_maps_out_of_gamut_color_by_default(self) -> None:
        result = generate_harmony_lch((50.0, 150.0, 20.0), "complementary")
        mapped = [color for color in result.colors if not color.was_in_gamut]

        self.assertGreater(len(mapped), 0)
        for color in mapped:
            self.assertIsNotNone(color.mapped_lch)
            self.assertIsNotNone(color.rgb)
            self.assertIsNotNone(color.hex)
            self.assertIsNotNone(color.gamut_delta_e)
            self.assertAlmostEqual(color.mapped_lch[0], color.ideal_lch[0])  # type: ignore[index]
            self.assertAlmostEqual(color.mapped_lch[2], color.ideal_lch[2])  # type: ignore[index]

    def test_can_leave_out_of_gamut_color_unrealized(self) -> None:
        result = generate_harmony_lch(
            (50.0, 150.0, 20.0),
            "complementary",
            map_to_gamut=False,
        )
        unrealized = [color for color in result.colors if not color.was_in_gamut]

        self.assertGreater(len(unrealized), 0)
        for color in unrealized:
            self.assertIsNone(color.mapped_lch)
            self.assertIsNone(color.rgb)
            self.assertIsNone(color.hex)
            self.assertIsNone(color.gamut_delta_e)

    def test_rejects_achromatic_color(self) -> None:
        with self.assertRaisesRegex(ValueError, "chroma of at least 5"):
            generate_harmony_lch((50.0, 0.0, 0.0), "triadic")

    def test_rejects_unknown_scheme(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown harmony scheme"):
            generate_harmony_lch((50.0, 40.0, 0.0), "unknown")  # type: ignore[arg-type]

    def test_rejects_invalid_lch_components(self) -> None:
        invalid_values = (
            (-1.0, 40.0, 0.0),
            (101.0, 40.0, 0.0),
            (50.0, 182.0, 0.0),
            (50.0, 40.0, 360.0),
            (50.0, 40.0, float("nan")),
        )

        for lch in invalid_values:
            with self.subTest(lch=lch), self.assertRaises(ValueError):
                generate_harmony_lch(lch, "triadic")


class TestGenerateHarmonyRGB(unittest.TestCase):
    """Test the primary sRGB harmony API."""

    def test_matches_direct_lch_generation(self) -> None:
        rgb = (224, 0, 107)

        from_rgb = generate_harmony(rgb, "triadic")
        from_lch = generate_harmony_lch(rgb_to_lch(rgb), "triadic")

        self.assertEqual(from_rgb, from_lch)

    def test_base_color_is_first(self) -> None:
        result = generate_harmony((224, 0, 107), "triadic")

        self.assertEqual(result.colors[0].hue_offset, 0.0)
        self.assertEqual(result.colors[0].rgb, (224, 0, 107))
        self.assertEqual(result.colors[0].hex, "#E0006B")

    def test_rejects_invalid_rgb(self) -> None:
        invalid_values = (
            (-1, 0, 0),
            (256, 0, 0),
            (1.0, 2, 3),
            (True, 0, 0),
        )

        for rgb in invalid_values:
            with self.subTest(rgb=rgb), self.assertRaises(ValueError):
                generate_harmony(rgb, "triadic")  # type: ignore[arg-type]

    def test_rejects_neutral_rgb(self) -> None:
        with self.assertRaisesRegex(ValueError, "chroma of at least 5"):
            generate_harmony((128, 128, 128), "triadic")


class TestHarmonyMoodAndTone(unittest.TestCase):
    """Test opinionated mood profiles and independent tone grading."""

    def test_accepts_all_mood_profiles(self) -> None:
        moods = ("warm", "cool", "happy", "calm", "intense", "sad", "energetic")

        for mood in moods:
            with self.subTest(mood=mood):
                result = generate_harmony_lch((50.0, 40.0, 50.0), "complementary", mood=mood)  # type: ignore[arg-type]
                self.assertEqual(result.mood, mood)
                self.assertNotEqual(result.colors[1].ideal_lch, (50.0, 40.0, 230.0))

    def test_preserves_base_color_by_default(self) -> None:
        result = generate_harmony_lch(
            (50.0, 40.0, 50.0),
            "triadic",
            mood="happy",
            tone="light",
        )

        self.assertEqual(result.colors[0].ideal_lch, (50.0, 40.0, 50.0))
        self.assertFalse(result.grade_base)

    def test_can_grade_base_color(self) -> None:
        result = generate_harmony_lch(
            (50.0, 40.0, 50.0),
            "triadic",
            mood="happy",
            tone="light",
            grade_base=True,
        )

        self.assertGreater(result.colors[0].ideal_lch[0], 50.0)
        self.assertGreater(result.colors[0].ideal_lch[1], 40.0)
        self.assertTrue(result.grade_base)

    def test_dark_and_light_tones_use_proportional_shifts(self) -> None:
        dark = generate_harmony_lch((50.0, 40.0, 50.0), "complementary", tone="dark")
        light = generate_harmony_lch((50.0, 40.0, 50.0), "complementary", tone="light")

        self.assertEqual(dark.colors[1].ideal_lch[0], 40.0)
        self.assertEqual(light.colors[1].ideal_lch[0], 60.0)
        self.assertEqual(dark.colors[1].ideal_lch[1:], (40.0, 230.0))
        self.assertEqual(light.colors[1].ideal_lch[1:], (40.0, 230.0))

    def test_warm_and_cool_emphasize_matching_temperatures(self) -> None:
        warm = generate_harmony_lch((50.0, 40.0, 50.0), "complementary", mood="warm")
        cool = generate_harmony_lch((50.0, 40.0, 50.0), "complementary", mood="cool")

        self.assertLess(warm.colors[1].ideal_lch[1], 40.0)
        self.assertGreater(cool.colors[1].ideal_lch[1], 40.0)
        self.assertEqual(warm.colors[1].ideal_lch[2], 230.0)
        self.assertEqual(cool.colors[1].ideal_lch[2], 230.0)

    def test_mood_profiles_follow_documented_directions(self) -> None:
        happy = generate_harmony_lch((50.0, 40.0, 50.0), "complementary", mood="happy")
        calm = generate_harmony_lch((50.0, 40.0, 50.0), "complementary", mood="calm")
        intense = generate_harmony_lch((50.0, 40.0, 50.0), "complementary", mood="intense")
        sad = generate_harmony_lch((50.0, 40.0, 50.0), "complementary", mood="sad")

        self.assertGreater(happy.colors[1].ideal_lch[0], 50.0)
        self.assertGreater(happy.colors[1].ideal_lch[1], 40.0)
        self.assertGreater(calm.colors[1].ideal_lch[0], 50.0)
        self.assertLess(calm.colors[1].ideal_lch[1], 40.0)
        self.assertGreater(intense.colors[1].ideal_lch[1], 40.0)
        self.assertLess(sad.colors[1].ideal_lch[0], 50.0)
        self.assertLess(sad.colors[1].ideal_lch[1], 40.0)

    def test_energetic_mood_varies_lightness_across_palette(self) -> None:
        result = generate_harmony_lch((50.0, 40.0, 50.0), "triadic", mood="energetic")

        self.assertGreater(result.colors[1].ideal_lch[0], 50.0)
        self.assertLess(result.colors[2].ideal_lch[0], 50.0)
        self.assertEqual(result.colors[1].ideal_lch[1], 50.0)
        self.assertEqual(result.colors[2].ideal_lch[1], 50.0)

    def test_mood_is_applied_before_tone(self) -> None:
        result = generate_harmony_lch(
            (50.0, 40.0, 50.0),
            "complementary",
            mood="happy",
            tone="dark",
        )

        self.assertAlmostEqual(result.colors[1].ideal_lch[0], 44.8)

    def test_rejects_unknown_mood_and_tone(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown mood"):
            generate_harmony_lch((50.0, 40.0, 50.0), "triadic", mood="angry")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "Unknown tone"):
            generate_harmony_lch((50.0, 40.0, 50.0), "triadic", tone="medium")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
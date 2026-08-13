"""Unit tests for color_tools.image.dominance."""

from __future__ import annotations

import unittest

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

try:
    import sklearn  # noqa: F401
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


DEPENDENCIES_AVAILABLE = (
    PILLOW_AVAILABLE
    and NUMPY_AVAILABLE
    and SKLEARN_AVAILABLE
)


def _make_solid_image(
    color: tuple[int, int, int],
    *,
    size: tuple[int, int] = (16, 16),
) -> Image.Image:
    """Create a solid RGB test image."""
    return Image.new("RGB", size, color)


def _make_split_image() -> Image.Image:
    """Create a deterministic two-color image with equal coverage."""
    image = Image.new("RGB", (8, 4))

    for x in range(8):
        for y in range(4):
            if x < 4:
                image.putpixel((x, y), (255, 0, 0))
            else:
                image.putpixel((x, y), (0, 0, 255))

    return image


def _make_transparent_image() -> Image.Image:
    """Create an RGBA image with no pixels above the alpha threshold."""
    return Image.new("RGBA", (4, 4), (255, 0, 0, 0))


@unittest.skipUnless(
    DEPENDENCIES_AVAILABLE,
    "Requires Pillow, numpy, and scikit-learn",
)
class TestDominantColorDataclass(unittest.TestCase):
    """Verify public DominantColor conveniences."""

    @classmethod
    def setUpClass(cls) -> None:
        from color_tools.image.dominance import DominantColor

        cls.DominantColor = DominantColor

    def test_hex_property_formats_uppercase_hex(self) -> None:
        """hex returns a #RRGGBB string."""
        color = self.DominantColor(
            rgb=(12, 34, 56),
            lab=(0.0, 0.0, 0.0),
            population=1.0,
            dominance=1.0,
            global_salience=0.0,
            local_contrast=0.0,
            spatial_distribution=0.0,
            spatial_coherence=1.0,
            lightness_contrast=0.0,
            focal_importance=1.0,
        )

        self.assertEqual(color.hex, "#0C2238")


@unittest.skipUnless(
    DEPENDENCIES_AVAILABLE,
    "Requires Pillow, numpy, and scikit-learn",
)
class TestDominantColorsToPalette(unittest.TestCase):
    """Verify conversion of dominant colors to palette records."""

    @classmethod
    def setUpClass(cls) -> None:
        from color_tools.image.dominance import (
            DominantColor,
            dominant_colors_to_palette,
        )

        cls.DominantColor = DominantColor
        cls.dominant_colors_to_palette = staticmethod(dominant_colors_to_palette)

    def test_empty_colors_returns_empty_palette(self) -> None:
        """An empty dominant-color list converts cleanly."""
        result = self.dominant_colors_to_palette([])
        self.assertEqual(result, [])

    def test_conversion_preserves_order_and_builds_color_records(self) -> None:
        """Converted palette records keep order, names, and source metadata."""
        colors = (
            self.DominantColor(
                rgb=(255, 0, 0),
                lab=(53.2, 80.1, 67.2),
                population=0.6,
                dominance=1.0,
                global_salience=1.0,
                local_contrast=0.5,
                spatial_distribution=1.0,
                spatial_coherence=1.0,
                lightness_contrast=0.2,
                focal_importance=1.0,
            ),
            self.DominantColor(
                rgb=(0, 0, 255),
                lab=(32.3, 79.2, -107.9),
                population=0.4,
                dominance=0.8,
                global_salience=0.9,
                local_contrast=0.5,
                spatial_distribution=1.0,
                spatial_coherence=1.0,
                lightness_contrast=0.1,
                focal_importance=0.8,
            ),
        )

        result = self.dominant_colors_to_palette(
            colors,
            source="fixture.png",
            name_prefix="Focus",
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "Focus 1")
        self.assertEqual(result[1].name, "Focus 2")
        self.assertEqual(result[0].source, "fixture.png")
        self.assertEqual(result[0].rgb, (255, 0, 0))
        self.assertEqual(result[1].rgb, (0, 0, 255))
        self.assertEqual(result[0].hex, "#FF0000")
        self.assertEqual(result[1].hex, "#0000FF")


@unittest.skipUnless(
    DEPENDENCIES_AVAILABLE,
    "Requires Pillow, numpy, and scikit-learn",
)
class TestDominanceAnalysis(unittest.TestCase):
    """Verify dominant-color analysis behavior on simple images."""

    @classmethod
    def setUpClass(cls) -> None:
        from color_tools.image import (
            DominanceAnalysis,
            analyze_dominant_colors,
            dominant_colors,
            dominant_colors_to_palette,
        )

        cls.DominanceAnalysis = DominanceAnalysis
        cls.analyze_dominant_colors = staticmethod(analyze_dominant_colors)
        cls.dominant_colors = staticmethod(dominant_colors)
        cls.dominant_colors_to_palette = staticmethod(dominant_colors_to_palette)

    def test_dominant_colors_on_solid_image_returns_single_exact_color(self) -> None:
        """A solid-color image collapses to one exact dominant color."""
        colors = self.dominant_colors(
            _make_solid_image((255, 0, 0)),
            count=8,
        )

        self.assertEqual(len(colors), 1)
        self.assertEqual(colors[0].rgb, (255, 0, 0))
        self.assertEqual(colors[0].hex, "#FF0000")
        self.assertAlmostEqual(colors[0].population, 1.0, places=6)

    def test_dominant_colors_on_split_image_returns_both_colors(self) -> None:
        """A two-color split image returns both source colors."""
        colors = self.dominant_colors(
            _make_split_image(),
            count=2,
        )

        self.assertEqual(len(colors), 2)
        self.assertEqual(
            {color.rgb for color in colors},
            {(255, 0, 0), (0, 0, 255)},
        )
        self.assertTrue(
            all(
                abs(color.population - 0.5) < 1e-6
                for color in colors
            )
        )

    def test_analyze_dominant_colors_returns_complete_analysis(self) -> None:
        """Full analysis exposes color results and saliency metadata."""
        analysis = self.analyze_dominant_colors(
            _make_split_image(),
            count=2,
        )

        self.assertIsInstance(analysis, self.DominanceAnalysis)
        self.assertEqual(len(analysis.colors), 2)
        self.assertEqual(analysis.saliency_map.shape, (4, 8))
        self.assertGreaterEqual(analysis.focal_center[0], 0.0)
        self.assertLessEqual(analysis.focal_center[0], 1.0)
        self.assertGreaterEqual(analysis.focal_center[1], 0.0)
        self.assertLessEqual(analysis.focal_center[1], 1.0)
        self.assertGreaterEqual(analysis.focal_radius, 0.0)

    def test_helper_converts_real_analysis_output(self) -> None:
        """Palette conversion works with real dominant-color analysis output."""
        colors = self.dominant_colors(
            _make_split_image(),
            count=2,
        )

        palette = self.dominant_colors_to_palette(
            colors,
            source="in-memory",
        )

        self.assertEqual(len(palette), 2)
        self.assertEqual(
            {record.rgb for record in palette},
            {(255, 0, 0), (0, 0, 255)},
        )
        self.assertTrue(
            all(record.source == "in-memory" for record in palette)
        )

    def test_all_transparent_image_raises_value_error(self) -> None:
        """Images without any opaque-enough pixels are rejected."""
        with self.assertRaises(ValueError):
            self.dominant_colors(_make_transparent_image())

    def test_invalid_count_raises_value_error(self) -> None:
        """count must be at least one."""
        with self.assertRaises(ValueError):
            self.dominant_colors(_make_split_image(), count=0)

    def test_invalid_provisional_clusters_raises_value_error(self) -> None:
        """provisional_clusters must be at least one when provided."""
        with self.assertRaises(ValueError):
            self.analyze_dominant_colors(
                _make_split_image(),
                provisional_clusters=0,
            )

    def test_analysis_is_deterministic_for_simple_image(self) -> None:
        """Repeated analysis on the same image yields the same ordered colors."""
        first = self.dominant_colors(
            _make_split_image(),
            count=2,
        )
        second = self.dominant_colors(
            _make_split_image(),
            count=2,
        )

        self.assertEqual(
            [color.rgb for color in first],
            [color.rgb for color in second],
        )
        self.assertEqual(
            [round(color.dominance, 8) for color in first],
            [round(color.dominance, 8) for color in second],
        )


if __name__ == "__main__":
    unittest.main()

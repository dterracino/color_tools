"""Tests for the additional small built-in retro-system palettes."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from color_tools import load_palette
from color_tools.cli_commands.reporting import get_available_palettes
from color_tools.conversions import lab_to_lch, rgb_to_hex, rgb_to_hsl, rgb_to_lab
from tooling.generate_additional_retro_palettes import write_palettes


_TMS9918_EXPECTED: tuple[str, ...] = (
    "#000000", "#0aad1e", "#34c84c", "#2b2de3", "#514bfb",
    "#bd2925", "#1ee2ef", "#fb2c2b", "#ff5f4c", "#bda22b",
    "#d7b454", "#0a8c18", "#af329a", "#b2b2b2", "#ffffff",
)


_EXPECTED_HEX: dict[str, tuple[str, ...]] = {
    "amstrad-cpc": (
        "#000000", "#000080", "#0000ff", "#800000", "#800080", "#8000ff",
        "#ff0000", "#ff0080", "#ff00ff", "#008000", "#008080", "#0080ff",
        "#808000", "#808080", "#8080ff", "#ff8000", "#ff8080", "#ff80ff",
        "#00ff00", "#00ff80", "#00ffff", "#80ff00", "#80ff80", "#80ffff",
        "#ffff00", "#ffff80", "#ffffff",
    ),
    "bbc-micro": (
        "#000000", "#ff0000", "#00ff00", "#ffff00",
        "#0000ff", "#ff00ff", "#00ffff", "#ffffff",
    ),
    "colecovision": _TMS9918_EXPECTED,
    "gameboy": (
        "#071821", "#306850", "#86c06c", "#e0f8cf",
    ),
    "gameboy-dmg": (
        "#081810", "#396139", "#84a563", "#c6de8c",
    ),
    "gameboy-light": (
        "#0a1c15", "#357862", "#56b495", "#7fe2c3",
    ),
    "gameboy-pocket": (
        "#000000", "#555555", "#aaaaaa", "#ffffff",
    ),
    "intellivision": (
        "#0c0005", "#002dff", "#ff3e00", "#c9d464",
        "#00780f", "#00a720", "#faea27", "#fffcff",
        "#a7a8a8", "#5acbff", "#ffa600", "#3c5800",
        "#ff3276", "#bd95ff", "#6ccd30", "#c81a7d",
    ),
    "msx1": _TMS9918_EXPECTED,
    "sg-1000": _TMS9918_EXPECTED,
    "ti-99-4a": _TMS9918_EXPECTED,
    "tic80": (
        "#1a1c2c", "#5d275d", "#b13e53", "#ef7d57",
        "#ffcd75", "#a7f070", "#38b764", "#257179",
        "#29366f", "#3b5dc9", "#41a6f6", "#73eff7",
        "#f4f4f4", "#94b0c2", "#566c86", "#333c57",
    ),
    "vic-20": (
        "#000000", "#ffffff", "#772d26", "#85d4dc",
        "#a85fb4", "#559e4a", "#42348b", "#bdcc71",
        "#a8734a", "#e9b287", "#b66862", "#c5ffff",
        "#e99df5", "#92df87", "#7e70ca", "#ffffb0",
    ),
    "zx-spectrum": (
        "#000000", "#0000d7", "#d70000", "#d700d7",
        "#00d700", "#00d7d7", "#d7d700", "#d7d7d7",
        "#0000ff", "#ff0000", "#ff00ff", "#00ff00",
        "#00ffff", "#ffff00", "#ffffff",
    ),
}


class TestAdditionalRetroPalettes(unittest.TestCase):
    """Validate source order, derived values, discovery, and reproducibility."""

    def test_palettes_have_expected_source_colors_in_order(self) -> None:
        """Every palette should exactly match its independently recorded hex table."""
        for palette_name, expected_hex in _EXPECTED_HEX.items():
            with self.subTest(palette=palette_name):
                palette = load_palette(palette_name)
                self.assertEqual(
                    tuple(record.hex for record in palette.records),
                    expected_hex,
                )
                self.assertEqual(len({record.rgb for record in palette.records}), len(expected_hex))

    def test_serialized_derived_values_match_production_conversions(self) -> None:
        """Stored hex, HSL, LAB, and LCH should agree with each stored RGB value."""
        for palette_name in _EXPECTED_HEX:
            for record in load_palette(palette_name).records:
                with self.subTest(palette=palette_name, color=record.name):
                    lab = rgb_to_lab(record.rgb)
                    self.assertEqual(record.hex, rgb_to_hex(record.rgb).lower())
                    self.assertEqual(record.hsl, tuple(round(v, 1) for v in rgb_to_hsl(record.rgb)))
                    self.assertEqual(record.lab, tuple(round(v, 1) for v in lab))
                    self.assertEqual(record.lch, tuple(round(v, 1) for v in lab_to_lch(lab)))

    def test_palettes_are_discoverable_with_correct_counts(self) -> None:
        """CLI palette discovery should expose every generated name and count."""
        available = dict(get_available_palettes())
        for palette_name, expected_hex in _EXPECTED_HEX.items():
            self.assertEqual(available.get(palette_name), len(expected_hex))

    def test_generator_reproduces_bundled_files_exactly(self) -> None:
        """The checked-in files should be deterministic generator output."""
        bundled_dir = Path(__file__).parents[1] / "color_tools" / "data" / "palettes"
        with tempfile.TemporaryDirectory() as temporary_directory:
            generated_paths = write_palettes(Path(temporary_directory))
            self.assertEqual(len(generated_paths), len(_EXPECTED_HEX))
            for generated_path in generated_paths:
                bundled_path = bundled_dir / generated_path.name
                self.assertEqual(generated_path.read_bytes(), bundled_path.read_bytes())


if __name__ == "__main__":
    unittest.main()

"""Strict type-checking contract for a base-only wheel installation."""

# pyright: strict

from typing_extensions import assert_type

from color_tools import (
    ColorRecord,
    FilamentPalette,
    FilamentRecord,
    Palette,
    delta_e_2000,
    rgb_to_lab,
)


lab = rgb_to_lab((255, 128, 64))
assert_type(lab, tuple[float, float, float])
assert_type(delta_e_2000(lab, lab), float)

palette = Palette.load_default()
color, color_distance = palette.nearest_color(lab)
assert_type(color, ColorRecord)
assert_type(color_distance, float)

filaments = FilamentPalette.load_default()
filament, filament_distance = filaments.nearest_filament(
    (255, 128, 64), owned=False
)
assert_type(filament, FilamentRecord)
assert_type(filament_distance, float)
assert_type(filaments.owned_filaments, set[str])

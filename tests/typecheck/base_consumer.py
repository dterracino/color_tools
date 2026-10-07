"""Strict type-checking contract for a base-only wheel installation."""

# pyright: strict

from collections.abc import Iterator

from typing_extensions import assert_type

from color_tools import (
    ColorRecord,
    FilamentFilterCriteria,
    FilamentPalette,
    FilamentRecord,
    Palette,
    delta_e_2000,
    generate_color_names,
    iter_color_names,
    rgb_to_lab,
)
from color_tools.naming import MatchType


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

criteria = FilamentFilterCriteria(type_name="PLA", finish=["Matte", "Silk"])
filtered = filaments.filter_by_criteria(criteria, owned=False)
assert_type(filtered, list[FilamentRecord])
criteria_filament, criteria_distance = filaments.nearest_filament_by_criteria(
    (255, 128, 64),
    include=criteria,
    exclude=FilamentFilterCriteria(maker="Example"),
    owned=False,
)
assert_type(criteria_filament, FilamentRecord)
assert_type(criteria_distance, float)

names = generate_color_names([(255, 0, 0), (0, 0, 255)])
assert_type(names, list[tuple[str, MatchType]])
name_iterator = iter_color_names([(255, 0, 0)])
assert_type(name_iterator, Iterator[tuple[str, MatchType]])

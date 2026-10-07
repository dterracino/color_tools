"""Strict type-checking contract for the installed color_tools wheel."""

# pyright: strict

from typing_extensions import assert_type

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from color_tools import (
    ColorRecord,
    FilamentPalette,
    FilamentRecord,
    Palette,
    delta_e_2000,
    delta_e_2000_array,
    rgb_to_lab,
    rgb_to_lab_array,
)
from color_tools.image import simulate_cvd_image
from color_tools.mcp.models import ColorCoordinates


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

array_distances = delta_e_2000_array(
    np.array([[50.0, 0.0, 0.0]], dtype=np.float64),
    np.array([[51.0, 0.0, 0.0]], dtype=np.float64),
)
assert_type(array_distances, NDArray[np.float64])

lab_array = rgb_to_lab_array(
    np.array([[255, 128, 64], [0, 0, 0]], dtype=np.uint8)
)
assert_type(lab_array, NDArray[np.float64])
assert_type(delta_e_2000_array(lab_array, lab_array[0]), NDArray[np.float64])

assert_type(simulate_cvd_image("sample.png", "protanopia"), Image.Image)

coordinates = ColorCoordinates(
    rgb=(255, 128, 64),
    hex="#FF8040",
    xyz=(1.0, 2.0, 3.0),
    lab=lab,
    lch=(1.0, 2.0, 3.0),
    hsl=(1.0, 2.0, 3.0),
    cmy=(1.0, 2.0, 3.0),
    cmyk=(1.0, 2.0, 3.0, 4.0),
    winhsl240=(1, 2, 3),
    winhsl255=(1, 2, 3),
)
assert_type(coordinates.rgb, tuple[int, int, int])

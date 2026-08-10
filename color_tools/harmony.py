"""Generate color harmonies in CIE LCH space."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

from .constants import ColorConstants
from .conversions import (
    lab_to_lch,
    lab_to_rgb,
    lch_to_lab,
    rgb_to_hex,
    rgb_to_lch,
)
from .distance import delta_e_2000
from .gamut import find_nearest_in_gamut, is_in_srgb_gamut


HarmonyType = Literal[
    "analogous",
    "complementary",
    "full-spectrum",
    "monochromatic",
    "rainbow",
    "split-complementary",
    "triadic",
    "square",
    "tetradic",
]
MoodType = Literal[
    "warm",
    "cool",
    "happy",
    "calm",
    "intense",
    "sad",
    "energetic",
]
ToneType = Literal["normal", "dark", "light"]

_ACHROMATIC_CHROMA_THRESHOLD = 5.0
_HARMONY_OFFSETS: dict[HarmonyType, tuple[float, ...]] = {
    "analogous": (0.0, -30.0, 30.0, 60.0),
    "complementary": (0.0, 180.0),
    "full-spectrum": tuple(float(offset) for offset in range(0, 360, 60)),
    "rainbow": tuple(float(offset) for offset in range(0, 360, 60)),
    "split-complementary": (0.0, 150.0, 210.0),
    "triadic": (0.0, 120.0, 240.0),
    "square": (0.0, 90.0, 180.0, 270.0),
    "tetradic": (0.0, 60.0, 180.0, 240.0),
}


@dataclass(frozen=True)
class HarmonyColor:
    """One ideal harmony color and its optional displayable sRGB realization."""

    hue_offset: float
    ideal_lch: tuple[float, float, float]
    was_in_gamut: bool
    mapped_lch: tuple[float, float, float] | None
    rgb: tuple[int, int, int] | None
    hex: str | None
    gamut_delta_e: float | None


@dataclass(frozen=True)
class HarmonyResult:
    """Immutable result of generating an LCH harmony."""

    scheme: HarmonyType
    base_lch: tuple[float, float, float]
    colors: tuple[HarmonyColor, ...]
    mood: MoodType | None = None
    tone: ToneType = "normal"
    grade_base: bool = False


def _validate_style(
    mood: MoodType | None,
    tone: ToneType,
) -> None:
    valid_moods = ("warm", "cool", "happy", "calm", "intense", "sad", "energetic")
    if mood is not None and mood not in valid_moods:
        choices = ", ".join(valid_moods)
        raise ValueError(f"Unknown mood '{mood}'. Use one of: {choices}")
    if tone not in ("normal", "dark", "light"):
        raise ValueError("Unknown tone. Use one of: normal, dark, light")


def _temperature_affinity(hue: float, center: float) -> float:
    distance = math.radians(hue - center)
    return (math.cos(distance) + 1.0) / 2.0


def _apply_mood(
    lch: tuple[float, float, float],
    mood: MoodType | None,
    color_index: int,
) -> tuple[float, float, float]:
    if mood is None:
        return lch

    lightness, chroma, hue = lch
    warm_affinity = _temperature_affinity(hue, 50.0)
    cool_affinity = _temperature_affinity(hue, 230.0)

    if mood == "warm":
        chroma *= 0.85 + 0.30 * warm_affinity
    elif mood == "cool":
        chroma *= 0.85 + 0.30 * cool_affinity
    elif mood == "happy":
        lightness += (100.0 - lightness) * 0.12
        chroma *= 1.05 + 0.15 * warm_affinity
    elif mood == "calm":
        lightness += (100.0 - lightness) * 0.08
        chroma *= 0.65 + 0.10 * cool_affinity
    elif mood == "intense":
        lightness = 50.0 + (lightness - 50.0) * 1.15
        chroma *= 1.30
    elif mood == "sad":
        lightness *= 0.78
        chroma *= 0.60 + 0.10 * cool_affinity
    elif mood == "energetic":
        direction = 1.0 if color_index % 2 else -1.0
        lightness += direction * min(lightness, 100.0 - lightness) * 0.10
        chroma *= 1.25

    return (
        min(100.0, max(0.0, lightness)),
        min(ColorConstants.CHROMA_MAX, max(0.0, chroma)),
        hue,
    )


def _apply_tone(
    lch: tuple[float, float, float],
    tone: ToneType,
) -> tuple[float, float, float]:
    lightness, chroma, hue = lch
    if tone == "dark":
        lightness *= 0.80
    elif tone == "light":
        lightness += (100.0 - lightness) * 0.20
    return (lightness, chroma, hue)


def _validate_rgb(rgb: tuple[int, int, int]) -> None:
    if not isinstance(rgb, tuple) or len(rgb) != 3:
        raise ValueError("RGB must be a tuple of three integer channels")
    if any(isinstance(channel, bool) or not isinstance(channel, int) for channel in rgb):
        raise ValueError("RGB channels must be integers")
    if any(
        channel < ColorConstants.RGB_MIN or channel > ColorConstants.RGB_MAX
        for channel in rgb
    ):
        raise ValueError("RGB channels must be between 0 and 255")


def _validate_lch(lch: tuple[float, float, float]) -> tuple[float, float, float]:
    if not isinstance(lch, tuple) or len(lch) != 3:
        raise ValueError("LCH must be a tuple of three numeric components")
    if any(isinstance(component, bool) or not isinstance(component, (int, float)) for component in lch):
        raise ValueError("LCH components must be numeric")

    lightness, chroma, hue = (float(component) for component in lch)
    if not all(math.isfinite(component) for component in (lightness, chroma, hue)):
        raise ValueError("LCH components must be finite")
    if not ColorConstants.NORMALIZED_MIN <= lightness <= ColorConstants.XYZ_SCALE_FACTOR:
        raise ValueError("LCH lightness must be between 0 and 100")
    if not ColorConstants.CHROMA_MIN <= chroma <= ColorConstants.CHROMA_MAX:
        raise ValueError(f"LCH chroma must be between 0 and {ColorConstants.CHROMA_MAX:g}")
    if not ColorConstants.NORMALIZED_MIN <= hue < ColorConstants.HUE_CIRCLE_DEGREES:
        raise ValueError("LCH hue must be between 0 (inclusive) and 360 (exclusive)")
    if chroma < _ACHROMATIC_CHROMA_THRESHOLD:
        raise ValueError("Hue-based harmonies require LCH chroma of at least 5")
    return (lightness, chroma, hue)


def _realize_color(
    ideal_lch: tuple[float, float, float],
    hue_offset: float,
    map_to_gamut: bool,
) -> HarmonyColor:
    ideal_lab = lch_to_lab(ideal_lch)
    was_in_gamut = is_in_srgb_gamut(ideal_lab)
    if not was_in_gamut and not map_to_gamut:
        return HarmonyColor(
            hue_offset=hue_offset,
            ideal_lch=ideal_lch,
            was_in_gamut=False,
            mapped_lch=None,
            rgb=None,
            hex=None,
            gamut_delta_e=None,
        )

    mapped_lab = ideal_lab if was_in_gamut else find_nearest_in_gamut(ideal_lab)
    mapped_lch = lab_to_lch(mapped_lab)
    rgb = lab_to_rgb(mapped_lab)
    return HarmonyColor(
        hue_offset=hue_offset,
        ideal_lch=ideal_lch,
        was_in_gamut=was_in_gamut,
        mapped_lch=mapped_lch,
        rgb=rgb,
        hex=rgb_to_hex(rgb),
        gamut_delta_e=delta_e_2000(ideal_lab, mapped_lab),
    )


def _generate_monochromatic_colors(
    base_lch: tuple[float, float, float],
) -> tuple[tuple[float, tuple[float, float, float]], ...]:
    lightness, chroma, hue = base_lch
    return (
        (0.0, base_lch),
        (0.0, (lightness + (100.0 - lightness) * 0.5, chroma * 0.75, hue)),
        (0.0, (lightness + (100.0 - lightness) * 0.75, chroma * 0.5, hue)),
        (0.0, (lightness * 0.5, chroma * 0.75, hue)),
        (0.0, (lightness, chroma * 0.5, hue)),
    )


def generate_harmony_lch(
    lch: tuple[float, float, float],
    scheme: HarmonyType,
    *,
    map_to_gamut: bool = True,
    mood: MoodType | None = None,
    tone: ToneType = "normal",
    grade_base: bool = False,
) -> HarmonyResult:
    """Generate a styled harmony directly from CIE LCH coordinates.

    Hue-based schemes preserve the base lightness and chroma while rotating hue.
    Monochromatic harmonies preserve hue while varying lightness and chroma.
    Opinionated mood profiles adjust lightness and chroma without changing hue,
    while tone independently produces a darker or lighter variation. The base
    color remains unchanged unless ``grade_base`` is true.
    Displayable colors reduce chroma as needed while preserving lightness and hue.
    Set ``map_to_gamut=False`` to leave out-of-gamut colors without RGB values.

    Args:
        lch: Base color as ``(lightness, chroma, hue_degrees)``.
        scheme: Harmony relationship to generate.
        map_to_gamut: Map out-of-gamut colors into sRGB when true.
        mood: Optional opinionated mood profile applied before gamut mapping.
        tone: Independent normal, dark, or light palette variation.
        grade_base: Apply mood and tone to the base color when true.

    Returns:
        The ideal and displayable colors in the requested harmony.

    Raises:
        ValueError: If the color or scheme is invalid, or the color is achromatic.
    """
    base_lch = _validate_lch(lch)
    _validate_style(mood, tone)
    if scheme == "monochromatic":
        ideal_colors = _generate_monochromatic_colors(base_lch)
    else:
        try:
            offsets = _HARMONY_OFFSETS[scheme]
        except KeyError as error:
            choices = ", ".join((*_HARMONY_OFFSETS, "monochromatic"))
            raise ValueError(f"Unknown harmony scheme '{scheme}'. Use one of: {choices}") from error

        lightness, chroma, base_hue = base_lch
        ideal_colors = tuple(
            (
                offset,
                (
                    lightness,
                    chroma,
                    (base_hue + offset) % ColorConstants.HUE_CIRCLE_DEGREES,
                ),
            )
            for offset in offsets
        )

    styled_colors = tuple(
        (
            offset,
            ideal_lch
            if color_index == 0 and not grade_base
            else _apply_tone(_apply_mood(ideal_lch, mood, color_index), tone),
        )
        for color_index, (offset, ideal_lch) in enumerate(ideal_colors)
    )
    colors = tuple(
        _realize_color(ideal_lch, offset, map_to_gamut)
        for offset, ideal_lch in styled_colors
    )
    return HarmonyResult(
        scheme=scheme,
        base_lch=base_lch,
        colors=colors,
        mood=mood,
        tone=tone,
        grade_base=grade_base,
    )


def generate_harmony(
    rgb: tuple[int, int, int],
    scheme: HarmonyType,
    *,
    map_to_gamut: bool = True,
    mood: MoodType | None = None,
    tone: ToneType = "normal",
    grade_base: bool = False,
) -> HarmonyResult:
    """Generate a styled LCH-based harmony from an sRGB color.

    Args:
        rgb: Base color as integer sRGB channels from 0 through 255.
        scheme: Harmony relationship to generate.
        map_to_gamut: Map out-of-gamut colors into sRGB when true.
        mood: Optional opinionated mood profile applied before gamut mapping.
        tone: Independent normal, dark, or light palette variation.
        grade_base: Apply mood and tone to the base color when true.

    Returns:
        The ideal and displayable colors in the requested harmony.

    Raises:
        ValueError: If the color or scheme is invalid, or the color is achromatic.
    """
    _validate_rgb(rgb)
    return generate_harmony_lch(
        rgb_to_lch(rgb),
        scheme,
        map_to_gamut=map_to_gamut,
        mood=mood,
        tone=tone,
        grade_base=grade_base,
    )
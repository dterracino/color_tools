"""MCP server exposing Color Tools color science and filament expertise."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field
from typing_extensions import Annotated

from color_tools import __version__
from color_tools.color_deficiency import correct_cvd, simulate_cvd
from color_tools.conversions import (
    cmy_to_rgb,
    cmyk_to_rgb,
    hex_to_rgb,
    hsl_to_rgb,
    lab_to_lch,
    lab_to_rgb,
    lab_to_xyz,
    lch_to_lab,
    rgb_to_cmy,
    rgb_to_cmyk,
    rgb_to_hex,
    rgb_to_hsl,
    rgb_to_lab,
    rgb_to_lch,
    rgb_to_winhsl240,
    rgb_to_winhsl255,
    rgb_to_xyz,
    xyz_to_lab,
    xyz_to_rgb,
)
from color_tools.distance import (
    delta_e_76,
    delta_e_94,
    delta_e_2000,
    delta_e_cmc,
    delta_e_hyab,
    euclidean,
)
from color_tools.filament_palette import FilamentPalette, FilamentRecord
from color_tools.gamut import find_nearest_in_gamut, is_in_srgb_gamut
from color_tools.naming import generate_color_name
from color_tools.palette import ColorRecord, Palette, load_palette
from color_tools.validation import validate_color

from .models import (
    CVDResult,
    CVDType,
    ColorAnalysis,
    ColorComparison,
    ColorCoordinates,
    ColorNameValidation,
    ColorSpace,
    ConversionResult,
    DistanceMetric,
    FilamentCatalog,
    FilamentMatch,
    FilamentSearchResult,
    GamutMappingResult,
    NamedColorMatch,
    NamedColorSearchResult,
)


RGBChannel = Annotated[int, Field(ge=0, le=255)]
Count = Annotated[int, Field(ge=1, le=50)]
Percentage = Annotated[float, Field(ge=0.0, le=100.0)]


mcp = MCPServer(
    "color-tools",
    title="Color Tools",
    description="Authoritative color science calculations and 3D printing filament color matching.",
    instructions=(
        "Use these tools instead of estimating color conversions, Delta E values, gamut behavior, "
        "named colors, or filament matches. Prefer CIEDE2000 for perceptual matching unless the "
        "user requests another metric. Filament colors are manufacturer reference values and may "
        "vary with print settings, lighting, material batch, and display calibration."
    ),
    version=__version__,
)


def _rgb(red: RGBChannel, green: RGBChannel, blue: RGBChannel) -> tuple[int, int, int]:
    return (red, green, blue)


def _components(
    component_1: float,
    component_2: float,
    component_3: float,
    component_4: float | None,
) -> list[float]:
    values = [component_1, component_2, component_3]
    if component_4 is not None:
        values.append(component_4)
    return values


def _split_filter(value: str | None) -> list[str] | None:
    if value is None:
        return None
    values = [item.strip() for item in value.split(",") if item.strip()]
    return values or None


def _coordinates(rgb: tuple[int, int, int]) -> ColorCoordinates:
    return ColorCoordinates(
        rgb=rgb,
        hex=rgb_to_hex(rgb),
        xyz=rgb_to_xyz(rgb),
        lab=rgb_to_lab(rgb),
        lch=rgb_to_lch(rgb),
        hsl=rgb_to_hsl(rgb),
        cmy=rgb_to_cmy(rgb),
        cmyk=rgb_to_cmyk(rgb),
        winhsl240=rgb_to_winhsl240(rgb),
        winhsl255=rgb_to_winhsl255(rgb),
    )


@lru_cache(maxsize=1)
def _css_palette() -> Palette:
    return Palette.load_default()


@lru_cache(maxsize=1)
def _filament_palette() -> FilamentPalette:
    return FilamentPalette.load_default()


def _named_match(record: ColorRecord, distance: float, metric: str) -> NamedColorMatch:
    return NamedColorMatch(
        name=record.name,
        hex=record.hex,
        rgb=record.rgb,
        lab=record.lab,
        lch=record.lch,
        distance=distance,
        metric=metric,
        source=record.source,
    )


def _filament_match(record: FilamentRecord, distance: float, metric: str) -> FilamentMatch:
    return FilamentMatch(
        id=record.id,
        maker=record.maker,
        material=record.type,
        finish=record.finish,
        color=record.color,
        hex=record.hex,
        rgb=record.rgb,
        lab=record.lab,
        td_value=record.td_value,
        other_names=record.other_names or [],
        distance=distance,
        metric=metric,
        source=record.source,
    )


def _rgb_from_space(value: list[float], space: ColorSpace, clamp: bool) -> tuple[int, int, int]:
    expected_lengths = {"rgb": 3, "xyz": 3, "lab": 3, "lch": 3, "hsl": 3, "cmy": 3, "cmyk": 4}
    expected = expected_lengths[space]
    if len(value) != expected:
        raise ValueError(f"{space.upper()} requires {expected} components")

    if space == "rgb":
        if any(not component.is_integer() for component in value):
            raise ValueError("RGB components must be integers")
        return _rgb(int(value[0]), int(value[1]), int(value[2]))
    if space == "xyz":
        return xyz_to_rgb(tuple(value), clamp=clamp)  # type: ignore[arg-type]
    if space == "lab":
        return lab_to_rgb(tuple(value), clamp=clamp)  # type: ignore[arg-type]
    if space == "lch":
        return lab_to_rgb(lch_to_lab(tuple(value)), clamp=clamp)  # type: ignore[arg-type]
    if space == "hsl":
        return hsl_to_rgb(tuple(value))  # type: ignore[arg-type]
    if space == "cmy":
        return cmy_to_rgb(tuple(value))  # type: ignore[arg-type]
    return cmyk_to_rgb(tuple(value))  # type: ignore[arg-type]


def _lab_from_space(value: list[float], space: ColorSpace) -> tuple[float, float, float]:
    if space == "lab":
        if len(value) != 3:
            raise ValueError("LAB requires 3 components")
        return tuple(value)  # type: ignore[return-value]
    if space == "lch":
        if len(value) != 3:
            raise ValueError("LCH requires 3 components")
        return lch_to_lab(tuple(value))  # type: ignore[arg-type]
    if space == "xyz":
        if len(value) != 3:
            raise ValueError("XYZ requires 3 components")
        return xyz_to_lab(tuple(value))  # type: ignore[arg-type]
    return rgb_to_lab(_rgb_from_space(value, space, clamp=True))


def _convert_value(
    value: list[float],
    source: ColorSpace,
    target: ColorSpace,
    clamp_rgb: bool,
) -> list[float | int]:
    if source == target:
        _rgb_from_space(value, source, clamp=clamp_rgb)
        return list(value)

    lab = _lab_from_space(value, source)
    if target == "lab":
        return list(lab)
    if target == "lch":
        return list(lab_to_lch(lab))
    if target == "xyz":
        return list(lab_to_xyz(lab))

    rgb = _rgb_from_space(value, source, clamp=clamp_rgb)
    if target == "rgb":
        return list(rgb)
    if target == "hsl":
        return list(rgb_to_hsl(rgb))
    if target == "cmy":
        return list(rgb_to_cmy(rgb))
    return list(rgb_to_cmyk(rgb))


@mcp.tool()
def analyze_color(
    red: RGBChannel,
    green: RGBChannel,
    blue: RGBChannel,
    named_color_count: Count = 3,
    filament_count: Count = 5,
) -> ColorAnalysis:
    """Analyze an sRGB color in all spaces and find named-color and filament matches."""
    rgb_value = _rgb(red, green, blue)
    coordinates = _coordinates(rgb_value)
    generated_name, match_type = generate_color_name(rgb_value)
    named = _css_palette().nearest_colors(coordinates.lab, metric="de2000", count=named_color_count)
    filaments = _filament_palette().nearest_filaments(
        rgb_value,
        metric="de2000",
        count=filament_count,
        owned=False,
    )
    return ColorAnalysis(
        coordinates=coordinates,
        generated_name=generated_name,
        name_match_type=match_type,
        in_srgb_gamut=is_in_srgb_gamut(coordinates.lab),
        nearest_named_colors=[_named_match(record, distance, "de2000") for record, distance in named],
        nearest_filaments=[_filament_match(record, distance, "de2000") for record, distance in filaments],
    )


@mcp.tool()
def convert_color(
    source_space: ColorSpace,
    target_space: ColorSpace,
    component_1: float,
    component_2: float,
    component_3: float,
    component_4: float | None = None,
    clamp_rgb: bool = True,
) -> ConversionResult:
    """Convert scalar components between RGB, XYZ, LAB, LCH, HSL, CMY, and CMYK using D65 sRGB."""
    value = _components(component_1, component_2, component_3, component_4)
    lab = _lab_from_space(value, source_space)
    gamut_status = is_in_srgb_gamut(lab) if source_space in {"xyz", "lab", "lch"} else None
    unclamped_rgb = _rgb_from_space(value, source_space, clamp=False)
    rgb_was_clamped = any(channel < 0 or channel > 255 for channel in unclamped_rgb)
    rgb_dependent_target = target_space in {"rgb", "hsl", "cmy", "cmyk"}
    if not clamp_rgb and rgb_was_clamped and rgb_dependent_target and target_space != "rgb":
        raise ValueError("Out-of-gamut source requires clamp_rgb=true for this target space")
    return ConversionResult(
        source_space=source_space,
        source_value=value,
        target_space=target_space,
        target_value=_convert_value(value, source_space, target_space, clamp_rgb),
        in_srgb_gamut=gamut_status,
        rgb_was_clamped=rgb_was_clamped,
    )


@mcp.tool()
def compare_colors(
    first_red: RGBChannel,
    first_green: RGBChannel,
    first_blue: RGBChannel,
    second_red: RGBChannel,
    second_green: RGBChannel,
    second_blue: RGBChannel,
) -> ColorComparison:
    """Compare two sRGB colors with every Color Tools perceptual distance metric."""
    first = _coordinates(_rgb(first_red, first_green, first_blue))
    second = _coordinates(_rgb(second_red, second_green, second_blue))
    return ColorComparison(
        first=first,
        second=second,
        delta_e_2000=delta_e_2000(first.lab, second.lab),
        delta_e_94=delta_e_94(first.lab, second.lab),
        delta_e_76=delta_e_76(first.lab, second.lab),
        delta_e_cmc_2_1=delta_e_cmc(first.lab, second.lab),
        hyab=delta_e_hyab(first.lab, second.lab),
        rgb_euclidean=euclidean(first.rgb, second.rgb),
    )


@mcp.tool()
def find_named_colors(
    red: RGBChannel,
    green: RGBChannel,
    blue: RGBChannel,
    palette: str = "css",
    metric: DistanceMetric = "de2000",
    count: Count = 5,
) -> NamedColorSearchResult:
    """Find nearest named colors in the CSS database or a bundled retro palette."""
    target = _coordinates(_rgb(red, green, blue))
    selected_palette = _css_palette() if palette.lower() == "css" else load_palette(palette)
    matches = selected_palette.nearest_colors(target.lab, metric=metric, count=count)
    return NamedColorSearchResult(
        target=target,
        palette=palette,
        metric=metric,
        matches=[_named_match(record, distance, metric) for record, distance in matches],
    )


@mcp.tool()
def find_filaments(
    red: RGBChannel,
    green: RGBChannel,
    blue: RGBChannel,
    metric: DistanceMetric = "de2000",
    count: Count = 5,
    makers: str | None = None,
    materials: str | None = None,
    finishes: str | None = None,
    owned_only: bool = False,
    max_hue_delta: Annotated[float | None, Field(ge=0.0, le=180.0)] = None,
) -> FilamentSearchResult:
    """Find filament colors; maker, material, and finish filters accept comma-separated values."""
    rgb_value = _rgb(red, green, blue)
    target = _coordinates(rgb_value)
    matches = _filament_palette().nearest_filaments(
        rgb_value,
        metric=metric,
        count=count,
        maker=_split_filter(makers),
        type_name=_split_filter(materials),
        finish=_split_filter(finishes),
        owned=owned_only,
        max_hue_delta=max_hue_delta,
    )
    return FilamentSearchResult(
        target=target,
        metric=metric,
        searched_owned_only=owned_only,
        matches=[_filament_match(record, distance, metric) for record, distance in matches],
    )


@mcp.tool()
def get_filament_catalog() -> FilamentCatalog:
    """List valid makers, materials, and finishes for filtering filament searches."""
    palette = _filament_palette()
    return FilamentCatalog(
        record_count=len(palette.records),
        owned_record_count=len(palette.list_owned()),
        makers=palette.makers,
        materials=palette.types,
        finishes=palette.finishes,
    )


@mcp.tool()
def transform_color_vision(
    red: RGBChannel,
    green: RGBChannel,
    blue: RGBChannel,
    deficiency: CVDType,
    operation: Literal["simulate", "correct"] = "simulate",
) -> CVDResult:
    """Simulate a color vision deficiency or apply a discriminability correction."""
    rgb_value = _rgb(red, green, blue)
    original = _coordinates(rgb_value)
    transformed_rgb = (
        simulate_cvd(rgb_value, deficiency)
        if operation == "simulate"
        else correct_cvd(rgb_value, deficiency)
    )
    transformed = _coordinates(transformed_rgb)
    return CVDResult(
        operation=operation,
        deficiency=deficiency,
        original=original,
        transformed=transformed,
        delta_e_2000=delta_e_2000(original.lab, transformed.lab),
    )


@mcp.tool()
def map_to_srgb_gamut(lightness: float, a: float, b: float) -> GamutMappingResult:
    """Check a LAB color and map it into sRGB by preserving lightness and hue while reducing chroma."""
    lab_value = (lightness, a, b)
    was_in_gamut = is_in_srgb_gamut(lab_value)
    mapped_lab = lab_value if was_in_gamut else find_nearest_in_gamut(lab_value)
    mapped_rgb = lab_to_rgb(mapped_lab)
    return GamutMappingResult(
        original_lab=lab_value,
        was_in_gamut=was_in_gamut,
        mapped_lab=mapped_lab,
        mapped_rgb=mapped_rgb,
        mapped_hex=rgb_to_hex(mapped_rgb),
        delta_e_2000=delta_e_2000(lab_value, mapped_lab),
    )


@mcp.tool()
def validate_color_name(
    color_name: str,
    hex_code: str,
    delta_e_threshold: Percentage = 20.0,
) -> ColorNameValidation:
    """Validate whether a color name plausibly describes a hex color."""
    if hex_to_rgb(hex_code) is None:
        raise ValueError("hex_code must be a three- or six-digit hexadecimal color")
    result = validate_color(color_name, hex_code, de_threshold=delta_e_threshold)
    return ColorNameValidation(
        is_match=result.is_match,
        name_match=result.name_match,
        name_confidence=result.name_confidence,
        hex_value=result.hex_value,
        suggested_hex=result.suggested_hex,
        delta_e_2000=result.delta_e,
        message=result.message,
    )


def main() -> None:
    """Run the Color Tools MCP server over stdio."""
    mcp.run(transport="stdio")
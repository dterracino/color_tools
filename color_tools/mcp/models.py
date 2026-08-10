"""Structured input and output models for the Color Tools MCP server."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ColorSpace = Literal["rgb", "xyz", "lab", "lch", "hsl", "cmy", "cmyk"]
DistanceMetric = Literal["de2000", "de94", "de76", "cmc", "hyab"]
CVDType = Literal[
    "protanopia",
    "protan",
    "deuteranopia",
    "deutan",
    "tritanopia",
    "tritan",
    "all",
]


class MCPModel(BaseModel):
    """Base model with immutable values and strict unknown-field handling."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ColorCoordinates(MCPModel):
    """A color represented in every space supported by Color Tools."""

    rgb: tuple[int, int, int]
    hex: str
    xyz: tuple[float, float, float]
    lab: tuple[float, float, float]
    lch: tuple[float, float, float]
    hsl: tuple[float, float, float]
    cmy: tuple[float, float, float]
    cmyk: tuple[float, float, float, float]
    winhsl240: tuple[int, int, int]
    winhsl255: tuple[int, int, int]


class NamedColorMatch(MCPModel):
    """A named palette color and its distance from the requested color."""

    name: str
    hex: str
    rgb: tuple[int, int, int]
    lab: tuple[float, float, float]
    lch: tuple[float, float, float]
    distance: float
    metric: str
    source: str


class FilamentMatch(MCPModel):
    """A filament record and its perceptual distance from a target color."""

    id: str
    maker: str
    material: str
    finish: str | None
    color: str
    hex: str
    rgb: tuple[int, int, int]
    lab: tuple[float, float, float]
    td_value: float | None
    other_names: list[str]
    distance: float
    metric: str
    source: str


class ColorAnalysis(MCPModel):
    """Comprehensive analysis of one sRGB color."""

    coordinates: ColorCoordinates
    generated_name: str
    name_match_type: Literal["exact", "near", "generated"]
    in_srgb_gamut: bool
    nearest_named_colors: list[NamedColorMatch]
    nearest_filaments: list[FilamentMatch]


class ConversionResult(MCPModel):
    """Result of converting a color between supported color spaces."""

    source_space: ColorSpace
    source_value: list[float]
    target_space: ColorSpace
    target_value: list[float | int]
    in_srgb_gamut: bool | None = Field(
        description="Gamut status for source XYZ, LAB, or LCH values."
    )
    rgb_was_clamped: bool


class ColorComparison(MCPModel):
    """Color differences computed with all library distance metrics."""

    first: ColorCoordinates
    second: ColorCoordinates
    delta_e_2000: float
    delta_e_94: float
    delta_e_76: float
    delta_e_cmc_2_1: float
    hyab: float
    rgb_euclidean: float


class NamedColorSearchResult(MCPModel):
    """Nearest named colors from a requested palette."""

    target: ColorCoordinates
    palette: str
    metric: DistanceMetric
    matches: list[NamedColorMatch]


class FilamentSearchResult(MCPModel):
    """Nearest filament colors after applying catalog filters."""

    target: ColorCoordinates
    metric: DistanceMetric
    searched_owned_only: bool
    matches: list[FilamentMatch]


class FilamentCatalog(MCPModel):
    """Discoverable facets of the bundled filament database."""

    record_count: int
    owned_record_count: int
    makers: list[str]
    materials: list[str]
    finishes: list[str]


class CVDResult(MCPModel):
    """A color vision deficiency simulation or correction."""

    operation: Literal["simulate", "correct"]
    deficiency: CVDType
    original: ColorCoordinates
    transformed: ColorCoordinates
    delta_e_2000: float


class GamutMappingResult(MCPModel):
    """An sRGB gamut check and optional chroma-preserving mapping."""

    original_lab: tuple[float, float, float]
    was_in_gamut: bool
    mapped_lab: tuple[float, float, float]
    mapped_rgb: tuple[int, int, int]
    mapped_hex: str
    delta_e_2000: float


class ColorNameValidation(MCPModel):
    """Validation of whether a supplied name describes a hex color."""

    is_match: bool
    name_match: str | None
    name_confidence: float
    hex_value: str
    suggested_hex: str | None
    delta_e_2000: float
    message: str
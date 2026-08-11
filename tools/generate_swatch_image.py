#!/usr/bin/env python3
"""Generate a color palette and render it with the swatch image exporter.

Examples:
    python tools/generate_swatch_image.py
    python tools/generate_swatch_image.py --base "#E05A47" --colors 8
    python tools/generate_swatch_image.py --output demos/swatch_sheet.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from color_tools.conversions import (
    hex_to_rgb,
    lab_to_rgb,
    lch_to_lab,
    rgb_to_hex,
    rgb_to_hsl,
    rgb_to_lab,
    rgb_to_lch,
)
from color_tools.exporters import get_exporter
from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.palette_metadata import PaletteMetadata
from color_tools.exporters.swatch_image_exporter import SwatchImageOptions
from color_tools.gamut import find_nearest_in_gamut
from color_tools.naming import generate_color_name
from color_tools.palette import ColorRecord


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = SCRIPT_DIR / "output" / "eight_color_swatch.png"


def create_hue_wheel_palette(
    base_rgb: tuple[int, int, int],
    color_count: int = 8,
) -> list[ColorRecord]:
    """Create evenly spaced, displayable LCH hue rotations of a base color."""
    if color_count < 1:
        raise ValueError("color_count must be at least 1")

    lightness, chroma, base_hue = rgb_to_lch(base_rgb)
    hue_step = 360.0 / color_count
    rgb_colors: list[tuple[int, int, int]] = []

    for index in range(color_count):
        hue = (base_hue + index * hue_step) % 360.0
        ideal_lab = lch_to_lab((lightness, chroma, hue))
        mapped_lab = find_nearest_in_gamut(ideal_lab)
        rgb_colors.append(lab_to_rgb(mapped_lab))

    records: list[ColorRecord] = []
    for rgb in rgb_colors:
        generated_name, _match_type = generate_color_name(
            rgb,
            palette_colors=rgb_colors,
        )
        records.append(
            ColorRecord(
                name=generated_name.title(),
                hex=rgb_to_hex(rgb),
                rgb=rgb,
                hsl=rgb_to_hsl(rgb),
                lab=rgb_to_lab(rgb),
                lch=rgb_to_lch(rgb),
                source="generated-swatch",
            )
        )

    return records


def generate_swatch_image(
    base_rgb: tuple[int, int, int],
    color_count: int,
    palette_name: str,
    output_path: Path,
    *,
    show_index: bool = True,
    show_hex: bool = True,
    show_rgb: bool = True,
    show_hsl: bool = True,
    show_lab: bool = True,
    show_lch: bool = True,
) -> Path:
    """Generate a palette and export it as a presentation PNG swatch sheet."""
    colors = create_hue_wheel_palette(base_rgb, color_count)
    palette = PaletteExportData(
        colors=colors,
        metadata=PaletteMetadata(
            name=palette_name,
            description=(
                f"{color_count} evenly spaced CIE LCH hues generated from "
                f"{rgb_to_hex(base_rgb)}."
            ),
            columns=4,
            tags=("generated", "lch", "hue-wheel"),
        ),
    )

    options = SwatchImageOptions(
        show_index=show_index,
        show_hex=show_hex,
        show_rgb=show_rgb,
        show_hsl=show_hsl,
        show_lab=show_lab,
        show_lch=show_lch,
    )
    exporter = get_exporter("swatch_image")
    exported_path = exporter.export_palette(
        palette,
        output_path,
        options=options,
    )
    return Path(exported_path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an LCH hue-wheel palette and export a PNG swatch sheet."
    )
    parser.add_argument(
        "--base",
        default="#E05A47",
        metavar="HEX",
        help="Base sRGB color in HEX notation (default: #E05A47)",
    )
    parser.add_argument(
        "--colors",
        type=int,
        default=8,
        metavar="COUNT",
        help="Number of palette colors to generate (default: 8)",
    )
    parser.add_argument(
        "--name",
        default="Eight-Color LCH Wheel",
        help="Palette title displayed in the swatch image",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        metavar="PNG",
        help=f"Output PNG path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--index",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show palette index badges (default: enabled)",
    )
    parser.add_argument(
        "--hex",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show HEX values (default: enabled)",
    )
    parser.add_argument(
        "--rgb",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show RGB values (default: enabled)",
    )
    parser.add_argument(
        "--hsl",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show HSL values (default: enabled)",
    )
    parser.add_argument(
        "--lab",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show CIE Lab values (default: enabled)",
    )
    parser.add_argument(
        "--lch",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show CIE LCh values (default: enabled)",
    )
    return parser.parse_args()


def main() -> None:
    """Run the swatch image generation tool."""
    args = _parse_args()
    base_rgb = hex_to_rgb(args.base)
    if base_rgb is None:
        raise SystemExit(f"Invalid HEX base color: {args.base!r}")

    try:
        output_path = generate_swatch_image(
            base_rgb=base_rgb,
            color_count=args.colors,
            palette_name=args.name,
            output_path=args.output,
            show_index=args.index,
            show_hex=args.hex,
            show_rgb=args.rgb,
            show_hsl=args.hsl,
            show_lab=args.lab,
            show_lch=args.lch,
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error

    print(f"Generated {args.colors}-color swatch image: {output_path.resolve()}")


if __name__ == "__main__":
    main()

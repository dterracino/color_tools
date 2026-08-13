#!/usr/bin/env python3
"""Extract dominant colors from an image and export a swatch sheet."""

from __future__ import annotations

import argparse
from pathlib import Path

from color_tools.exporters import get_exporter
from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.palette_metadata import PaletteMetadata
from color_tools.image.dominance import (
    dominant_colors,
    dominant_colors_to_palette,
)


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "output"


def export_dominant_swatch(
    image_path: Path,
    output_path: Path,
    *,
    count: int,
) -> Path:
    """Export a swatch image for the dominant colors in an input image."""
    records = dominant_colors_to_palette(
        dominant_colors(
            image_path,
            count=count,
        ),
        source=image_path.name,
    )
    palette = PaletteExportData(
        colors=records,
        metadata=PaletteMetadata(
            name=f"Dominant Colors: {image_path.stem}",
            description=(
                "Dominant colors extracted with "
                "color_tools.image.dominance.dominant_colors()."
            ),
        ),
    )

    exporter = get_exporter("swatch_image")
    exported_path = exporter.export_palette(
        palette,
        output_path,
    )
    return Path(exported_path)


def _default_output_path(
    image_path: Path,
) -> Path:
    return DEFAULT_OUTPUT_DIR / f"{image_path.stem}_dominant_swatch.png"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract dominant colors from an image and export a PNG swatch sheet."
        )
    )
    parser.add_argument(
        "image",
        type=Path,
        help="Input image to analyze",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=8,
        metavar="N",
        help="Number of dominant colors to extract (default: 8)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        metavar="PNG",
        help="Output PNG path",
    )
    return parser.parse_args()


def main() -> None:
    """Run the dominant-color swatch export tool."""
    args = _parse_args()
    image_path = args.image.expanduser().resolve()

    if not image_path.is_file():
        raise SystemExit(f"Input image not found: {image_path}")

    if args.count < 1:
        raise SystemExit("--count must be at least 1")

    output_path = args.output or _default_output_path(image_path)

    try:
        exported_path = export_dominant_swatch(
            image_path=image_path,
            output_path=output_path,
            count=args.count,
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error

    print(f"Generated dominant-color swatch image: {exported_path.resolve()}")


if __name__ == "__main__":
    main()

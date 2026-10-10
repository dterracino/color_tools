#!/usr/bin/env python3
"""Batch-export bundled palettes as shader-ready PNG lookup textures.

This utility is intentionally a thin wrapper around the registered
``palette_lut`` and ``glsl`` exporters. It contains no image encoding or GLSL
generation logic of its own.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from color_tools import load_palette
from color_tools.exporters import get_exporter
from color_tools.exporters.glsl_exporter import GLSLExportOptions


DEMO_DIR = Path(__file__).resolve().parent
PALETTE_DIR = DEMO_DIR.parent / "color_tools" / "data" / "palettes"
DEFAULT_OUTPUT_DIR = DEMO_DIR / "palette_textures"


def _available_palette_names() -> list[str]:
    """Return bundled palette names in deterministic order."""
    return sorted(path.stem for path in PALETTE_DIR.glob("*.json"))


def _export_palette(
    name: str,
    output_dir: Path,
    *,
    include_glsl: bool,
) -> tuple[Path, Path | None]:
    """Export one palette through the canonical LUT and GLSL exporters."""
    palette = load_palette(name)
    output_dir.mkdir(parents=True, exist_ok=True)

    lut_path = Path(
        get_exporter("palette_lut").export_colors(
            palette.records,
            output_dir / f"{name}.png",
        )
    )

    glsl_path: Path | None = None
    if include_glsl:
        glsl_path = Path(
            get_exporter("glsl").export_colors(
                palette.records,
                output_dir / f"{name}.glsl",
                options=GLSLExportOptions(
                    include_metadata=False,
                    variable_name="PALETTE",
                    precision=4,
                ),
            )
        )

    return lut_path, glsl_path


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Export bundled color_tools palettes as Nx1 RGB PNG textures"
        )
    )
    parser.add_argument(
        "--palette",
        nargs="+",
        metavar="NAME",
        help="One or more palette names; defaults to every bundled palette",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        metavar="DIR",
        help="Output directory (default: demos/palette_textures)",
    )
    parser.add_argument(
        "--glsl",
        action="store_true",
        help="Also export each palette through the registered GLSL exporter",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List bundled palettes and exit",
    )
    return parser


def main() -> None:
    """Parse arguments and batch-export the selected palettes."""
    parser = _build_parser()
    args = parser.parse_args()
    available_names = _available_palette_names()

    if bool(args.list):
        print("Available palettes:")
        for name in available_names:
            palette = load_palette(name)
            print(f"  {name:25s} ({len(palette.records)} colors)")
        return

    requested_names = cast(list[str] | None, args.palette)
    names = list(dict.fromkeys(requested_names or available_names))
    output_dir = cast(Path, args.output)
    include_glsl = bool(args.glsl)

    print(f"Exporting {len(names)} palette texture(s) to {output_dir}")
    failures: list[str] = []
    for name in names:
        try:
            lut_path, glsl_path = _export_palette(
                name,
                output_dir,
                include_glsl=include_glsl,
            )
            extra = f" and {glsl_path.name}" if glsl_path is not None else ""
            print(f"  {name:25s} -> {lut_path.name}{extra}")
        except (FileNotFoundError, OSError, TypeError, ValueError) as exc:
            failures.append(name)
            print(f"  ERROR {name}: {exc}")

    if failures:
        parser.exit(
            1,
            f"Failed to export {len(failures)} palette(s): "
            f"{', '.join(failures)}\n",
        )


if __name__ == "__main__":
    main()

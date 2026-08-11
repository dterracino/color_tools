"""
SketchPalette exporter.

Exports palette colors to the JSON-based .sketchpalette format used by the
Sketch Palettes plugin.

Each color is represented using normalized RGBA channel values in the
0.0-1.0 range.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import (
    ExporterMetadata,
    PaletteExporter,
)
from color_tools.exporters.registry import register_exporter

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord


@register_exporter
class SketchPaletteExporter(PaletteExporter):
    """Export color palettes in SketchPalette JSON format."""

    COMPATIBLE_VERSION = "1.4"
    PLUGIN_VERSION = "1.4"

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the SketchPalette exporter."""
        return ExporterMetadata(
            name="sketchpalette",
            description="Sketch Palettes plugin format",
            file_extension="sketchpalette",
            supports_colors=True,
            supports_filaments=False,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors to SketchPalette format.

        Args:
            colors:
                Color records to export.

            output_path:
                Destination .sketchpalette file. If None, a timestamped
                filename is generated in the current working directory.

        Returns:
            Path to the exported SketchPalette file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "compatibleVersion": self.COMPATIBLE_VERSION,
            "pluginVersion": self.PLUGIN_VERSION,
            "colors": [
                self._to_sketch_color(color)
                for color in colors
            ],
        }

        with path.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as file:
            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False,
            )
            file.write("\n")

        return str(path)

    @staticmethod
    def _to_sketch_color(
        color: ColorRecord,
    ) -> dict[str, float]:
        """
        Convert a ColorRecord to normalized Sketch RGBA values.

        Args:
            color:
                Color record to convert.

        Returns:
            SketchPalette color dictionary.
        """
        r, g, b = color.rgb

        return {
            "red": r / 255.0,
            "green": g / 255.0,
            "blue": b / 255.0,
            "alpha": 1.0,
        }
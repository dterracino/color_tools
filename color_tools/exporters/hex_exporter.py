"""
HEX palette exporter.

Exports colors as one uppercase six-digit hexadecimal RGB value per line.

Format example:

    FF0000
    00FF00
    0000FF

The leading ``#`` is omitted to match the common Lospec-style HEX palette
representation.
"""

from __future__ import annotations

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
class HexExporter(PaletteExporter):
    """
    Export color palettes as plain-text hexadecimal RGB values.

    Each color is written as uppercase ``RRGGBB`` on its own line with no
    leading ``#``.

    This representation matches the HEX palette format commonly exported by
    Lospec and other palette-oriented tools.
    """

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the HEX exporter."""
        return ExporterMetadata(
            name="hex",
            description="Plain-text HEX palette (RRGGBB per line)",
            file_extension="hex",
            supports_colors=True,
            supports_filaments=False,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors to plain-text HEX format.

        Args:
            colors:
                Color records to export.

            output_path:
                Destination HEX file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported HEX file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as file:
            for color in colors:
                hex_code = color.hex.removeprefix("#").upper()
                file.write(f"{hex_code}\n")

        return str(path)
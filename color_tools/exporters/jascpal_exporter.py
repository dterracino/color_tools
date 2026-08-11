"""
JASC-PAL palette exporter.

Exports colors to the JASC Paint Shop Pro palette format.

Format:

    JASC-PAL
    0100
    <color_count>
    R G B
    R G B
    ...

JASC-PAL is a plain-text RGB palette format commonly used by Paint Shop Pro,
pixel-art tools, retro graphics utilities, and palette conversion software.

The ``.pal`` extension is shared by multiple palette formats, so the exporter
registry uses the explicit identifier ``jasc_pal``.
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
class JascPalExporter(PaletteExporter):
    """
    Export color palettes in JASC-PAL format.

    JASC-PAL stores 8-bit RGB values as plain text. Color names and alpha
    values are not supported by the format.
    """

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the JASC-PAL exporter."""
        return ExporterMetadata(
            name="jasc_pal",
            description="JASC Paint Shop Pro palette format",
            file_extension="pal",
            supports_colors=True,
            supports_filaments=False,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors to JASC-PAL format.

        Args:
            colors:
                Color records to export.

            output_path:
                Destination PAL file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported PAL file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open(
            "w",
            encoding="ascii",
            newline="\n",
        ) as file:
            file.write("JASC-PAL\n")
            file.write("0100\n")
            file.write(f"{len(colors)}\n")

            for color in colors:
                r, g, b = color.rgb
                file.write(f"{r} {g} {b}\n")

        return str(path)
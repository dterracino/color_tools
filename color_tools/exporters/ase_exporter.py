"""
Adobe Swatch Exchange (ASE) palette exporter.

This exporter writes color palettes in Adobe Swatch Exchange format using the
optional ``swatch`` package.

ASE is a binary palette format commonly used by Adobe applications including
Photoshop, Illustrator, and InDesign.

The ``swatch`` dependency is part of the ``image`` optional extra and is
imported lazily so the exporter package remains usable when that extra is not
installed.

Palette-aware export preserves the palette name by writing the colors inside
an ASE Color Group.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from color_tools.exporters.base import (
    ExporterDependency,
    ExporterMetadata,
    PaletteExporter,
)
from color_tools.exporters.registry import register_exporter

if TYPE_CHECKING:
    from color_tools.exporters.palette_export_data import PaletteExportData
    from color_tools.palette import ColorRecord


@register_exporter
class ASEExporter(PaletteExporter):
    """
    Export color palettes as Adobe Swatch Exchange (ASE) files.

    Colors are written as RGB Process swatches. RGB channel values are
    normalized from 8-bit integer values (0-255) to the 0.0-1.0 range expected
    by the ``swatch`` package.

    Color names are preserved when available.

    When export_palette() is used with a palette name, all swatches are
    contained in a named ASE Color Group.
    """

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the ASE exporter."""
        return ExporterMetadata(
            name="ase",
            description="Adobe Swatch Exchange palette",
            file_extension="ase",
            supports_colors=True,
            supports_filaments=False,
            supports_palette_metadata=True,
            is_binary=True,
            dependencies=(
                ExporterDependency(
                    package="swatch",
                    import_name="swatch",
                    extra="image",
                ),
            ),
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors to an Adobe Swatch Exchange file.

        Colors are written as ungrouped ASE Process swatches.

        Args:
            colors:
                Color records to export.

            output_path:
                Destination ASE file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported ASE file as a string.
        """
        swatches = [
            self._to_swatch(color)
            for color in colors
        ]

        return self._write_ase(
            swatches,
            output_path,
        )

    def _export_palette_impl(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors and palette metadata to ASE.

        The palette name is represented as an Adobe Color Group name.

        Other PaletteMetadata fields do not have direct equivalents in this
        exporter and are intentionally ignored.

        Args:
            palette:
                Palette colors and metadata.

            output_path:
                Destination ASE file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported ASE file as a string.
        """
        swatches = [
            self._to_swatch(color)
            for color in palette.colors
        ]

        palette_name = palette.metadata.name.strip()

        if palette_name:
            data: list[dict[str, Any]] = [
                {
                    "name": palette_name,
                    "type": "Color Group",
                    "swatches": swatches,
                }
            ]
        else:
            data = swatches

        return self._write_ase(
            data,
            output_path,
        )

    def _write_ase(
        self,
        data: list[dict[str, Any]],
        output_path: Path | str | None,
    ) -> str:
        """
        Write ASE data to disk using the optional swatch package.

        Args:
            data:
                Swatch/color-group structures expected by ``swatch.write``.

            output_path:
                Destination ASE file.

        Returns:
            Path to the exported ASE file as a string.
        """
        import swatch

        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        swatch.write(
            data,
            str(path),
        )

        return str(path)

    @staticmethod
    def _to_swatch(
        color: ColorRecord,
    ) -> dict[str, Any]:
        """
        Convert a ColorRecord to the structure expected by ``swatch.write``.

        Args:
            color:
                Color record to convert.

        Returns:
            ASE Process swatch dictionary.
        """
        r, g, b = color.rgb

        return {
            "name": color.name or color.hex,
            "type": "Process",
            "data": {
                "mode": "RGB",
                "values": [
                    r / 255.0,
                    g / 255.0,
                    b / 255.0,
                ],
            },
        }
"""
Scribus XML palette exporter.

Exports colors to Scribus' XML palette format.

Basic RGB structure::

    <?xml version="1.0" encoding="UTF-8"?>
    <SCRIBUSCOLORS Name="Palette Name">
        <COLOR
            NAME="Coral"
            RGB="#FF7F50"
            Spot="0"
            Register="0"
        />
    </SCRIBUSCOLORS>

Scribus palettes may contain RGB, CMYK, spot, and registration colors.
This exporter currently writes RGB process colors because ColorRecord does
not yet model spot/register semantics or native CMYK swatches.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import (
    ExporterMetadata,
    PaletteExporter,
)
from color_tools.exporters.registry import register_exporter

if TYPE_CHECKING:
    from color_tools.exporters.palette_export_data import PaletteExportData
    from color_tools.palette import ColorRecord


@register_exporter
class ScribusExporter(PaletteExporter):
    """
    Export color palettes in Scribus XML palette format.

    Colors are written as RGB process swatches.

    Palette-aware export preserves the palette name using the
    ``SCRIBUSCOLORS`` root ``Name`` attribute.
    """

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the Scribus exporter."""
        return ExporterMetadata(
            name="scribus",
            description="Scribus XML color palette",
            file_extension="xml",
            supports_colors=True,
            supports_filaments=False,
            supports_palette_metadata=True,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors to Scribus XML format.

        Without palette metadata, the palette name is derived from the output
        filename.

        Args:
            colors:
                Color records to export.

            output_path:
                Destination XML file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported XML file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)

        return self._write_palette(
            colors=colors,
            path=path,
            name=path.stem,
        )

    def _export_palette_impl(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors and palette-level metadata to Scribus XML format.

        Supported metadata:

        - name

        Scribus' palette XML does not provide standard fields for author,
        description, tags, or preferred column count, so those values are not
        serialized.

        Args:
            palette:
                Palette colors and metadata.

            output_path:
                Destination XML file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported XML file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)

        return self._write_palette(
            colors=palette.colors,
            path=path,
            name=palette.metadata.name or path.stem,
        )

    def _write_palette(
        self,
        *,
        colors: list[ColorRecord],
        path: Path,
        name: str,
    ) -> str:
        """
        Serialize a Scribus XML palette.

        Args:
            colors:
                Ordered palette colors.

            path:
                Destination XML path.

            name:
                Palette name.

        Returns:
            Path to the exported XML file as a string.
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        root = ET.Element(
            "SCRIBUSCOLORS",
            {
                "Name": name,
            },
        )

        for index, color in enumerate(colors, start=1):
            color_name = (
                color.name
                or f"Color {index}"
            )

            hex_code = (
                "#"
                + color.hex.removeprefix("#").upper()
            )

            ET.SubElement(
                root,
                "COLOR",
                {
                    "NAME": color_name,
                    "RGB": hex_code,
                    "Spot": "0",
                    "Register": "0",
                },
            )

        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ")

        with path.open("wb") as file:
            tree.write(
                file,
                encoding="UTF-8",
                xml_declaration=True,
            )

        return str(path)

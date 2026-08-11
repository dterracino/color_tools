"""
LibreOffice/OpenOffice SOC palette exporter.

Exports named RGB colors to the StarOffice Color (.soc) XML format used by
LibreOffice and OpenOffice.

SOC files contain a color-table root element and one draw:color element per
palette entry.
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
    from color_tools.palette import ColorRecord


@register_exporter
class SOCExporter(PaletteExporter):
    """Export color palettes in LibreOffice/OpenOffice SOC format."""

    OFFICE_NS = (
        "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
    )
    DRAW_NS = (
        "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
    )
    XLINK_NS = "http://www.w3.org/1999/xlink"
    SVG_NS = "http://www.w3.org/2000/svg"
    OOO_NS = "http://openoffice.org/2004/office"

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the SOC exporter."""
        return ExporterMetadata(
            name="soc",
            description="LibreOffice/OpenOffice color palette",
            file_extension="soc",
            supports_colors=True,
            supports_filaments=False,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors to LibreOffice/OpenOffice SOC format.

        Args:
            colors:
                Color records to export.

            output_path:
                Destination SOC file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported SOC file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        self._register_namespaces()

        root = ET.Element(
            f"{{{self.OOO_NS}}}color-table"
        )

        for index, color in enumerate(colors, start=1):
            name = color.name or f"Color {index}"
            hex_code = (
                "#"
                + color.hex.removeprefix("#").lower()
            )

            ET.SubElement(
                root,
                f"{{{self.DRAW_NS}}}color",
                {
                    f"{{{self.DRAW_NS}}}name": name,
                    f"{{{self.DRAW_NS}}}color": hex_code,
                },
            )

        tree = ET.ElementTree(root)

        ET.indent(tree, space="    ")

        with path.open(
            "wb",
        ) as file:
            tree.write(
                file,
                encoding="utf-8",
                xml_declaration=True,
            )

        return str(path)

    @classmethod
    def _register_namespaces(cls) -> None:
        """Register the namespace prefixes used by SOC files."""
        ET.register_namespace("office", cls.OFFICE_NS)
        ET.register_namespace("draw", cls.DRAW_NS)
        ET.register_namespace("xlink", cls.XLINK_NS)
        ET.register_namespace("svg", cls.SVG_NS)
        ET.register_namespace("ooo", cls.OOO_NS)
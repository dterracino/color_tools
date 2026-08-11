"""
Krita Palette (.kpl) exporter.

Exports color palettes to Krita's native KPL palette format.

KPL is a ZIP-based palette container containing:

    mimetype
    colorset.xml
    profiles.xml
    [optional ICC profiles]

The mimetype file contains:

    application/x-krita-palette

This exporter currently writes built-in sRGB swatches using 8-bit source
values. Because built-in sRGB does not require an embedded ICC profile,
profiles.xml is written as an empty profile manifest.

Palette-aware export preserves:

    - name
    - description
    - preferred column count

Author, tags, and arbitrary properties are not currently represented because
the KPL Colorset structure does not define standard fields for them.

Colors are placed sequentially into the KPL grid in row-major order.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
import zipfile
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
class KPLExporter(PaletteExporter):
    """
    Export color palettes in Krita Palette (.kpl) format.

    Krita's native palette format supports color-managed swatches, groups,
    arbitrary grid positioning, multiple color spaces, spot colors, and
    embedded ICC profiles.

    This exporter currently targets the subset represented by ColorRecord:

        - ungrouped colors
        - built-in sRGB
        - U8 bit depth
        - non-spot colors
        - sequential grid positioning

    Palette metadata is used for the KPL palette name, description, and grid
    column count.
    """

    MIMETYPE = "application/x-krita-palette"
    FORMAT_VERSION = "1.0"

    # Used only when no meaningful column preference is supplied.
    DEFAULT_COLUMNS = 16

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the KPL exporter."""
        return ExporterMetadata(
            name="kpl",
            description="Krita native palette format",
            file_extension="kpl",
            supports_colors=True,
            supports_filaments=False,
            supports_palette_metadata=True,
            is_binary=True,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors to KPL without explicit palette metadata.

        The palette name is derived from the output filename and a reasonable
        default grid width is selected automatically.

        Args:
            colors:
                Color records to export.

            output_path:
                Destination KPL file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported KPL file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)

        columns = self._default_column_count(
            len(colors)
        )

        return self._write_kpl(
            colors=colors,
            path=path,
            name=path.stem,
            description="",
            columns=columns,
        )

    def _export_palette_impl(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors and palette metadata to KPL.

        Supported metadata:

            - name
            - description
            - columns

        A metadata column value of None or 0 is treated as unspecified for KPL
        because the KPL grid requires a concrete column count.

        Args:
            palette:
                Palette colors and metadata.

            output_path:
                Destination KPL file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported KPL file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        metadata = palette.metadata

        columns = (
            metadata.columns
            if metadata.columns is not None and metadata.columns > 0
            else self._default_column_count(len(palette.colors))
        )

        return self._write_kpl(
            colors=palette.colors,
            path=path,
            name=metadata.name or path.stem,
            description=metadata.description,
            columns=columns,
        )

    def _write_kpl(
        self,
        *,
        colors: list[ColorRecord],
        path: Path,
        name: str,
        description: str,
        columns: int,
    ) -> str:
        """
        Build and write a complete KPL archive.

        Args:
            colors:
                Ordered palette colors.

            path:
                Destination KPL path.

            name:
                Human-readable palette name.

            description:
                Palette description stored in the Colorset comment attribute.

            columns:
                Number of columns in the Krita palette grid.

        Returns:
            Path to the exported KPL file as a string.

        Raises:
            ValueError:
                If columns is less than one.
        """
        if columns < 1:
            raise ValueError(
                "KPL palette column count must be at least 1"
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        colorset_xml = self._build_colorset_xml(
            colors=colors,
            name=name,
            description=description,
            columns=columns,
        )

        profiles_xml = self._build_profiles_xml()

        with zipfile.ZipFile(
            path,
            mode="w",
        ) as archive:
            # Store the mimetype entry without compression. This keeps it
            # immediately readable as the archive's identifying payload.
            archive.writestr(
                "mimetype",
                self.MIMETYPE,
                compress_type=zipfile.ZIP_STORED,
            )

            archive.writestr(
                "colorset.xml",
                colorset_xml,
                compress_type=zipfile.ZIP_DEFLATED,
            )

            archive.writestr(
                "profiles.xml",
                profiles_xml,
                compress_type=zipfile.ZIP_DEFLATED,
            )

        return str(path)

    def _build_colorset_xml(
        self,
        *,
        colors: list[ColorRecord],
        name: str,
        description: str,
        columns: int,
    ) -> bytes:
        """
        Build the KPL colorset.xml document.

        Colors are written directly under the Colorset element, which places
        them in Krita's default/ungrouped color group.

        Args:
            colors:
                Ordered palette colors.

            name:
                Palette name.

            description:
                Palette description.

            columns:
                Grid column count.

        Returns:
            UTF-8 XML document as bytes.
        """
        rows = (
            math.ceil(len(colors) / columns)
            if colors
            else 0
        )

        root = ET.Element(
            "Colorset",
            {
                "name": name,
                "comment": description,
                "columns": str(columns),
                "rows": str(rows),
                "readonly": "false",
                "version": self.FORMAT_VERSION,
            },
        )

        for index, color in enumerate(colors):
            row, column = divmod(
                index,
                columns,
            )

            entry = ET.SubElement(
                root,
                "ColorSetEntry",
                {
                    "name": color.name or f"Color {index + 1}",
                    "id": f"color-{index + 1:04d}",
                    "bitdepth": "U8",
                    "spot": "false",
                },
            )

            r, g, b = color.rgb

            ET.SubElement(
                entry,
                "sRGB",
                {
                    "r": self._normalize_channel(r),
                    "g": self._normalize_channel(g),
                    "b": self._normalize_channel(b),
                },
            )

            ET.SubElement(
                entry,
                "Position",
                {
                    "row": str(row),
                    "column": str(column),
                },
            )

        tree = ET.ElementTree(root)
        ET.indent(
            tree,
            space="    ",
        )

        return ET.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        )

    @staticmethod
    def _build_profiles_xml() -> bytes:
        """
        Build the KPL profiles.xml manifest.

        Built-in sRGB swatches do not require an embedded ICC profile, so the
        manifest contains no Profile entries.

        Returns:
            UTF-8 XML document as bytes.
        """
        root = ET.Element("Profiles")

        return ET.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        )

    @classmethod
    def _default_column_count(
        cls,
        color_count: int,
    ) -> int:
        """
        Choose a reasonable default KPL grid width.

        Palettes smaller than DEFAULT_COLUMNS use one column per color so the
        initial grid does not contain unnecessary empty cells. Larger palettes
        use DEFAULT_COLUMNS columns.

        Empty palettes use a single column because KPL requires a concrete
        grid width.

        Args:
            color_count:
                Number of palette colors.

        Returns:
            Positive KPL column count.
        """
        if color_count <= 0:
            return 1

        return min(
            color_count,
            cls.DEFAULT_COLUMNS,
        )

    @staticmethod
    def _normalize_channel(
        value: int,
    ) -> str:
        """
        Convert an 8-bit RGB channel to KPL's normalized sRGB representation.

        Args:
            value:
                RGB channel in the range 0-255.

        Returns:
            Decimal value in the range 0.0-1.0.
        """
        return format(
            value / 255.0,
            ".9g",
        )
"""
GIMP Palette (.gpl) exporter.

Exports colors to the GIMP Palette text format used by GIMP, Inkscape,
Krita, MyPaint, and other graphics applications.

Format:

    GIMP Palette
    Name: palette_name
    Columns: 0
    #
    R   G   B   Color Name
    255 127  80  Coral

GPL stores 8-bit sRGB values and optional human-readable color names.

Palette-aware export preserves the palette name and preferred column count
using native GPL header fields. Additional descriptive metadata may be retained
as comments.
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
    from color_tools.exporters.palette_export_data import PaletteExportData
    from color_tools.palette import ColorRecord


@register_exporter
class GPLExporter(PaletteExporter):
    """
    Export color palettes in GIMP Palette (.gpl) format.

    GPL is a plain-text RGB palette format supported by a broad range of
    graphics applications.

    Palette and color names are sanitized to prevent embedded line breaks
    from corrupting the file structure.

    Palette-aware export preserves:

        - name
        - columns

    Author, description, and tags are written as GPL comments when present.
    """

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the GPL exporter."""
        return ExporterMetadata(
            name="gpl",
            description="GIMP Palette format (.gpl) for graphics applications",
            file_extension="gpl",
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
        Export colors to GIMP Palette format.

        Without palette metadata, the palette name is derived from the output
        filename and the column count defaults to zero.

        Args:
            colors:
                Color records to export.

            output_path:
                Destination GPL file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported GPL file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)

        return self._write_palette(
            colors=colors,
            path=path,
            name=path.stem,
            columns=0,
        )

    def _export_palette_impl(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors and palette metadata to GIMP Palette format.

        Args:
            palette:
                Palette colors and metadata.

            output_path:
                Destination GPL file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported GPL file as a string.

        Raises:
            ValueError:
                If the preferred GPL column count exceeds 255.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        metadata = palette.metadata

        columns = (
            metadata.columns
            if metadata.columns is not None
            else 0
        )

        if columns > 255:
            raise ValueError(
                "GPL palette columns must be between 0 and 255"
            )

        return self._write_palette(
            colors=palette.colors,
            path=path,
            name=metadata.name or path.stem,
            columns=columns,
            author=metadata.author,
            description=metadata.description,
            tags=metadata.tags,
        )

    def _write_palette(
        self,
        *,
        colors: list[ColorRecord],
        path: Path,
        name: str,
        columns: int,
        author: str = "",
        description: str = "",
        tags: tuple[str, ...] = (),
    ) -> str:
        """
        Serialize a GPL palette to disk.

        Args:
            colors:
                Ordered palette colors.

            path:
                Destination GPL path.

            name:
                Palette name.

            columns:
                Preferred display column count.

            author:
                Optional palette author written as a comment.

            description:
                Optional description written as a comment.

            tags:
                Optional tags written as a comment.

        Returns:
            Path to the exported GPL file as a string.
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as file:
            file.write("GIMP Palette\n")
            file.write(
                f"Name: {self._sanitize_line(name)}\n"
            )
            file.write(f"Columns: {columns}\n")
            file.write("#\n")

            if author:
                file.write(
                    f"# Author: {self._sanitize_line(author)}\n"
                )

            if description:
                file.write(
                    f"# Description: "
                    f"{self._sanitize_line(description)}\n"
                )

            if tags:
                file.write(
                    "# Tags: "
                    + ", ".join(
                        self._sanitize_line(tag)
                        for tag in tags
                    )
                    + "\n"
                )

            if author or description or tags:
                file.write("#\n")

            for color in colors:
                r, g, b = color.rgb
                color_name = self._sanitize_line(color.name)

                if color_name:
                    file.write(
                        f"{r:3d} {g:3d} {b:3d}\t"
                        f"{color_name}\n"
                    )
                else:
                    file.write(
                        f"{r:3d} {g:3d} {b:3d}\n"
                    )

        return str(path)

    @staticmethod
    def _sanitize_line(
        value: str | None,
    ) -> str:
        """
        Sanitize text stored in a line-oriented GPL field.

        Args:
            value:
                Text to sanitize.

        Returns:
            Single-line sanitized text.
        """
        if not value:
            return ""

        return (
            value
            .replace("\r", " ")
            .replace("\n", " ")
            .strip()
        )
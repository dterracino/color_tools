"""
Lospec JSON palette exporter.

Exports colors using Lospec's JSON palette representation::

    {
        "name": "Palette Name",
        "author": "Author Name",
        "colors": [
            "FF0000",
            "00FF00",
            "0000FF"
        ]
    }

Colors are serialized as six-digit hexadecimal RGB strings without a leading
``#``.

The exporter supports palette-level metadata through PaletteExportData. When
metadata is unavailable, the palette name falls back to the output filename and
the author field is left empty.

These files should be shareable on the Lospec palette list (https://lospec.com/palette-list)
and compatible with Lospec's palette viewer (https://lospec.com/palette-viewer).
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
    from color_tools.exporters.palette_export_data import PaletteExportData
    from color_tools.palette import ColorRecord


@register_exporter
class LospecExporter(PaletteExporter):
    """
    Export color palettes using Lospec's JSON palette representation.

    Lospec palettes contain:

    - name
    - author
    - colors

    Each color is represented as an ``RRGGBB`` hexadecimal string without a
    leading ``#``.

    Palette-level metadata is preserved when export_palette() is used.
    """

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the Lospec exporter."""
        return ExporterMetadata(
            name="lospec",
            description="Lospec-compatible JSON palette",
            file_extension="json",
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
        Export colors to Lospec-compatible JSON.

        This lightweight export path does not have palette-level metadata, so
        the palette name is derived from the destination filename and the
        author field is empty.

        Args:
            colors:
                Color records to export.

            output_path:
                Destination JSON file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported JSON file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)

        return self._write_palette(
            colors=colors,
            name=path.stem,
            author="",
            path=path,
        )

    def _export_palette_impl(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors and palette-level metadata to Lospec-compatible JSON.

        Supported palette metadata:

        - name
        - author

        Other PaletteMetadata fields are not represented by the Lospec JSON
        format and are intentionally ignored.

        Args:
            palette:
                Palette colors and metadata.

            output_path:
                Destination JSON file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported JSON file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        metadata = palette.metadata

        name = metadata.name or path.stem

        return self._write_palette(
            colors=palette.colors,
            name=name,
            author=metadata.author,
            path=path,
        )

    @staticmethod
    def _write_palette(
        *,
        colors: list[ColorRecord],
        name: str,
        author: str,
        path: Path,
    ) -> str:
        """
        Serialize a Lospec palette to disk.

        Args:
            colors:
                Ordered palette colors.

            name:
                Palette name.

            author:
                Palette author.

            path:
                Destination JSON path.

        Returns:
            Path to the exported JSON file as a string.
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "name": name,
            "author": author,
            "colors": [
                color.hex.removeprefix("#").lower()
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

"""
Generic JSON exporter for colors and filaments.

Exports palette data as structured JSON using the dataclass fields from
ColorRecord and FilamentRecord.

The lightweight export_colors() path serializes a raw list of color records.

The palette-aware export_palette() path serializes both palette metadata and
color records, providing a richer application/data interchange representation.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import (
    ExporterMetadata,
    PaletteExporter,
)
from color_tools.exporters.registry import register_exporter

if TYPE_CHECKING:
    from color_tools.exporters.palette_export_data import PaletteExportData
    from color_tools.filament_palette import FilamentRecord
    from color_tools.palette import ColorRecord


@register_exporter
class JSONExporter(PaletteExporter):
    """
    Export colors and filaments as generic JSON.

    Records are serialized directly from their dataclass representation,
    preserving the available application-level fields without adapting them
    to a third-party palette specification.

    Palette-aware export additionally preserves the complete PaletteMetadata
    dataclass.
    """

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the generic JSON exporter."""
        return ExporterMetadata(
            name="json",
            description="Generic JSON format with all record fields",
            file_extension="json",
            supports_colors=True,
            supports_filaments=True,
            supports_palette_metadata=True,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors to generic JSON format.

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
        path.parent.mkdir(parents=True, exist_ok=True)

        data = [
            asdict(color)
            for color in colors
        ]

        self._write_json(path, data)

        return str(path)

    def _export_palette_impl(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors and palette metadata to generic JSON.

        The resulting document contains:

            {
                "metadata": {...},
                "colors": [...]
            }

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
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metadata": asdict(palette.metadata),
            "colors": [
                asdict(color)
                for color in palette.colors
            ],
        }

        self._write_json(path, data)

        return str(path)

    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export filaments to generic JSON format.

        Args:
            filaments:
                Filament records to export.

            output_path:
                Destination JSON file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported JSON file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("filaments")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = [
            asdict(filament)
            for filament in filaments
        ]

        self._write_json(path, data)

        return str(path)

    @staticmethod
    def _write_json(
        path: Path,
        data: object,
    ) -> None:
        """
        Write JSON data using the standard exporter formatting.

        Args:
            path:
                Destination file path.

            data:
                JSON-serializable object to write.
        """
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
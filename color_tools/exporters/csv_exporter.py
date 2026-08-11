"""
Generic CSV exporter for colors and filaments.

Exports palette data to standard CSV files with column headers and all
available record fields.

Color tuple values are serialized as comma-separated strings within their
respective CSV fields.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, fields
from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import (
    ExporterMetadata,
    PaletteExporter,
)
from color_tools.exporters.registry import register_exporter
from color_tools.filament_palette import FilamentRecord

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord


@register_exporter
class CSVExporter(PaletteExporter):
    """
    Export colors and filaments to generic CSV format.

    Color columns:

        name, hex, rgb, hsl, lab, lch

    Filament columns are derived from the FilamentRecord dataclass fields.

    Tuple-based color values are stored as comma-separated values inside
    individual CSV cells.
    """

    COLOR_FIELDS = (
        "name",
        "hex",
        "rgb",
        "hsl",
        "lab",
        "lch",
    )

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the generic CSV exporter."""
        return ExporterMetadata(
            name="csv",
            description="Generic CSV with all fields",
            file_extension="csv",
            supports_colors=True,
            supports_filaments=True,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors to generic CSV format.

        Args:
            colors:
                Color records to export.

            output_path:
                Destination CSV file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported CSV file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)

            writer.writerow(self.COLOR_FIELDS)

            for color in colors:
                writer.writerow([
                    color.name,
                    color.hex,
                    self._format_tuple(color.rgb),
                    self._format_tuple(color.hsl, precision=1),
                    self._format_tuple(color.lab, precision=1),
                    self._format_tuple(color.lch, precision=1),
                ])

        return str(path)

    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export filaments to generic CSV format.

        Args:
            filaments:
                Filament records to export.

            output_path:
                Destination CSV file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported CSV file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("filaments")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            field.name
            for field in fields(FilamentRecord)
        ]

        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            for filament in filaments:
                writer.writerow(asdict(filament))

        return str(path)

    @staticmethod
    def _format_tuple(
        values: tuple,
        precision: int | None = None,
    ) -> str:
        """
        Serialize tuple values for storage in a CSV field.

        Args:
            values:
                Tuple values to serialize.

            precision:
                Optional number of decimal places for numeric values.

        Returns:
            Comma-separated tuple representation.
        """
        if precision is None:
            return ",".join(str(value) for value in values)

        return ",".join(
            f"{value:.{precision}f}"
            for value in values
        )
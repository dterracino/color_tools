"""
AutoForge filament library CSV exporter.

AutoForge is a companion tool for HueForge that manages filament libraries
with transmission distance (TD) values for multi-layer color and transparency
planning.

This exporter converts color_tools filament data to AutoForge's CSV import
format.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import (
    ExporterMetadata,
    PaletteExporter,
)
from color_tools.exporters.registry import register_exporter

if TYPE_CHECKING:
    from color_tools.filament_palette import FilamentRecord


@register_exporter
class AutoForgeExporter(PaletteExporter):
    """
    Export filament palettes to AutoForge CSV format.

    AutoForge expects the following columns:

        Brand,Name,TD,Color,Owned

    Example:

        Bambu Lab PLA Basic,Jet Black,0.1,#000000,TRUE

    The Brand field is assembled from the filament maker, material type,
    and finish. All exported filaments are marked as owned.
    """

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the AutoForge exporter."""
        return ExporterMetadata(
            name="autoforge",
            description="AutoForge filament library CSV format",
            file_extension="csv",
            supports_colors=False,
            supports_filaments=True,
        )

    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export filaments to AutoForge CSV format.

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

        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)

            writer.writerow([
                "Brand",
                "Name",
                "TD",
                "Color",
                "Owned",
            ])

            for filament in filaments:
                writer.writerow([
                    self._build_brand(filament),
                    filament.color,
                    filament.td_value
                    if filament.td_value is not None
                    else "",
                    filament.hex,
                    "TRUE",
                ])

        return str(path)

    @staticmethod
    def _build_brand(filament: FilamentRecord) -> str:
        """
        Build the AutoForge Brand field from filament metadata.

        The field consists of the maker followed by the material type and
        finish when those values are present.

        Args:
            filament:
                Filament record whose brand description should be generated.

        Returns:
            Combined AutoForge Brand field.
        """
        parts = [filament.maker]

        if filament.type:
            parts.append(filament.type)

        if filament.finish:
            parts.append(filament.finish)

        return " ".join(parts)